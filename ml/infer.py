"""E10 – YOLO çıkarımı: HiRISE karoları → tespitler → hücre yoğunlukları (+ etiket denetimi).

Çalıştır (proje kökünden):
    venv\\Scripts\\python ml\\infer.py                 # çıkarım + yoğunluk + etiket denetimi
    venv\\Scripts\\python scripts\\prep_layers.py      # yoğunluğu füzyona kat → grid.json, traversability.png, hazard_ml.png
    venv\\Scripts\\python scripts\\validate.py         # D2 ile doğrulama (önce/sonra YOLO)
Model değişince (2. parti etiketlerle yeniden eğitim): yalnızca ml/models/yolo_marstrail.pt'yi değiştir
(ml/compare_runs.py --select <run>) ve bu üç komutu tekrar çalıştır. Betik sınıf sayısını modelden okur (2 ya da 3).

Girdi : D8 ortogörüntü (data/raw/D8_hirise), ml/tiles_meta.json (ızgara + germe), ml/models/yolo_marstrail.pt
Çıktı : data/processed/yolo_detections.json      karo → tespitler (conf ≥ 0,10; yoğunluk 0,25 ile)
        data/processed/ml_density_{256,1024}.npz  hücre başına kum / kaya yoğunluğu + kapsama
        ml/audit_missed_labels.csv, docs/figures/e10_audit_examples.png  olası kaçırılan etiketler
        docs/figures/e10_infer_stats.json, e10_density.png

Yoğunluk tanımları (E6 hücre düzeyi kuralıyla aynı ölçek; DATA_PIPELINE.md E10):
  kum_ml  = hücrede kum_dalgasi kutularının birleşiminin kapladığı oran (0–1). E6'da "kum hücresi" eşiği 0,5.
  kaya_ml = clip(max(kaya_alani_oranı / 0,2 , kaya_sayısı_ha / 6,25), 0, 1).
            E6'da "kayalık hücre" eşikleri (kaya alanı ≥ 0,1 ya da 80 m'de ≥ 2 kaya = 3,1 kaya/ha) 0,5'e denk gelir.
  Kaya alanı = kaya_alani sınıfı ya da kenarı ≥ 40 px (10 m) olan kaya kutusu (etiketlerde kaya p90 9,4 m,
  kaya_alani p10 10,8 m; e6_dataset_stats.json). 2 sınıflı modelde kaya_alani sınıfı olmadığı için bu kural şart.
"""
import csv
import json
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np
import rasterio
from PIL import Image, ImageDraw
from pyproj import Transformer
from rasterio.windows import Window
from ultralytics import YOLO

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402
import tile_for_yolo as T  # noqa: E402

MODEL = ROOT / "ml" / "models" / "yolo_marstrail.pt"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "docs" / "figures"
DS = ROOT / "ml" / "dataset"
CONF_STORE = 0.10   # saklanan en düşük güven (eşik sonradan değiştirilebilsin diye)
CONF = 0.25         # yoğunlukta kullanılan eşik: Ultralytics varsayılanı; E6 hücre düzeyi doğrulaması bu eşikle yapıldı
CONF_AUDIT = 0.50   # etiket denetimi: "yüksek güven"
BIG_PX = 40         # 10 m: kaya → kaya alanı sınırı (yukarıda)
STEP = 10           # yoğunluk örnekleme aralığı: 10 px = 2,5 m (2 m'lik kaya kutusu bile en az bir örnek alır)
ROCK_AREA_REF, ROCK_HA_REF = 0.2, 6.25   # E6 kayalık eşiklerinin 2 katı → 1,0 (eşik 0,5'e denk)
MIN_COV = 0.5       # hücrenin en az yarısı HiRISE karosuyla kaplı değilse ML değeri yok (NaN)


def classify_box(name, w_px, h_px):
    """Model sınıfını yoğunluk grubuna çevirir: 'kum', 'kaya_alani' (bölge) ya da 'kaya' (tek engel)."""
    if name == "kum_dalgasi":
        return "kum"
    if name == "kaya_alani" or (w_px * h_px) ** 0.5 >= BIG_PX:
        return "kaya_alani"
    return "kaya"


def run_tiles(model, stretch):
    """E5 ızgarasındaki NoData'sız bütün karolar (temiz + dokusuz) üzerinde çıkarım."""
    lo, hi = stretch
    tiles, dropped = [], 0
    with rasterio.open(T.ORTHO) as src:
        nodata = src.nodata if src.nodata is not None else 0
        c0, r0, nx, ny = T.study_window(src)
        prev, k = T.preview(src, c0, r0, nx, ny)
        nod, std = T.tile_stats(prev, k, nodata)
        clean = nod == 0
        flat_thr = float(np.percentile(std[clean], 5))   # E5 ile aynı "dokusuz" tanımı (yalnız sayım için)
        rc = list(zip(*np.where(clean)))
        batch, meta = [], []

        def flush():
            for r, m in zip(model.predict(batch, imgsz=640, conf=CONF_STORE, device=0, verbose=False), meta):
                b = r.boxes
                m["dets"] = [[int(c), round(float(s), 3), *[round(float(v), 1) for v in xywh]]
                             for c, s, xywh in zip(b.cls.cpu(), b.conf.cpu(), b.xywh.cpu())]
                tiles.append(m)
            batch.clear(), meta.clear()

        for r, c in rc:
            col, row = c0 + int(c) * T.TILE, r0 + int(r) * T.TILE
            a = src.read(1, window=Window(col, row, T.TILE, T.TILE))
            if (a == nodata).mean() > 0.01:   # ön görünümde temiz ama tam çözünürlükte NoData şeridi var
                dropped += 1
                continue
            img = np.clip((a.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            batch.append(np.repeat(img[..., None], 3, axis=2))   # gri → 3 kanal (eğitimdeki JPG'ler de 3 kanal gri)
            meta.append({"name": f"jz_r{int(r):03d}_c{int(c):03d}", "row": int(r), "col": int(c), "px_col": col, "px_row": row,
                         "plain": bool(std[r, c] < flat_thr)})
            if len(batch) == 32:
                flush()
        if batch:
            flush()
        crs, tr = src.crs, src.transform
    return tiles, dropped, crs, tr


def densities(tiles, names, crs, tr, n):
    """Karo içi örnek noktaları (2,5 m) ve kaya merkezleri n×n coğrafi ızgaraya toplanır."""
    to_geo = Transformer.from_crs(crs, P.target_crs(), always_xy=True)
    B = P.BOUNDS
    samples = np.zeros(n * n)
    hit = {"kum": np.zeros(n * n), "kaya_alani": np.zeros(n * n)}
    rocks = np.zeros(n * n)
    g = np.arange(STEP // 2, T.TILE, STEP)
    gx, gy = np.meshgrid(g, g)

    def cell(px, py):
        x, y = tr * (px, py)
        lon, lat = to_geo.transform(x, y)
        cc = np.floor((np.asarray(lon) - B["west"]) / (B["east"] - B["west"]) * n).astype(int)
        rr = np.floor((B["north"] - np.asarray(lat)) / (B["north"] - B["south"]) * n).astype(int)
        ok = (cc >= 0) & (cc < n) & (rr >= 0) & (rr < n)
        return rr * n + cc, ok

    for t in tiles:
        idx, ok = cell(t["px_col"] + gx.ravel(), t["px_row"] + gy.ravel())
        np.add.at(samples, idx[ok], 1)
        masks = {"kum": np.zeros(gx.shape, bool), "kaya_alani": np.zeros(gx.shape, bool)}
        cx_r = []
        for c, s, x, y, w, h in t["dets"]:
            if s < CONF:
                continue
            grp = classify_box(names[c], w, h)
            if grp == "kaya":
                cx_r.append((x, y))
            else:   # birleşim maskesi: üst üste binen kutular iki kez sayılmaz
                masks[grp] |= (np.abs(gx - x) <= w / 2) & (np.abs(gy - y) <= h / 2)
        for grp, mk in masks.items():
            sel = ok & mk.ravel()
            np.add.at(hit[grp], idx[sel], 1)
        if cx_r:
            xr, yr = np.array(cx_r).T
            ridx, rok = cell(t["px_col"] + xr, t["px_row"] + yr)
            np.add.at(rocks, ridx[rok], 1)

    # Hücre alanı (m²): boylam aralığı enlemle daralır (cos φ)
    lat_c = B["north"] - (np.arange(n) + 0.5) * (B["north"] - B["south"]) / n
    cell_m2 = ((B["east"] - B["west"]) / n * P.M_PER_DEG * np.cos(np.radians(lat_c))
               * (B["north"] - B["south"]) / n * P.M_PER_DEG)
    sample_m2 = (STEP * 0.25) ** 2
    cov = (samples.reshape(n, n) * sample_m2) / cell_m2[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        s = samples.reshape(n, n)
        kum = hit["kum"].reshape(n, n) / s
        rock_area = hit["kaya_alani"].reshape(n, n) / s
        rocks_ha = rocks.reshape(n, n) / (s * sample_m2 / 1e4)
    valid = cov >= MIN_COV
    kum_ml = np.where(valid, np.clip(kum, 0, 1), np.nan)
    kaya_ml = np.where(valid, np.clip(np.maximum(rock_area / ROCK_AREA_REF, rocks_ha / ROCK_HA_REF), 0, 1), np.nan)
    return dict(kum_ml=kum_ml.astype(np.float32), kaya_ml=kaya_ml.astype(np.float32), coverage=np.clip(cov, 0, 1).astype(np.float32),
                rock_area=np.where(valid, rock_area, np.nan).astype(np.float32),
                rocks_per_ha=np.where(valid, rocks_ha, np.nan).astype(np.float32))


def audit(model, names):
    """Etiketlenmiş 150 karoda (Elif'in gördüğü JPG'lerin aynısı) yüksek güvenli ama etiketle eşleşmeyen tespitler.
    Eşleşme: aynı gruptaki (kaya+kaya_alani | kum) bir etiketle IoU ≥ 0,1 ya da tespit merkezi etiket kutusunun içinde
    (bölge ölçekli etiketler küçük tespitleri içerebilir)."""
    group = lambda nm: "kum" if nm == "kum_dalgasi" else "kaya"   # noqa: E731
    lab_names = ["kaya", "kaya_alani", "kum_dalgasi"]
    rows = []
    for split in ("train", "valid"):
        imgs = sorted((DS / split / "images").glob("*.*"))
        for r in model.predict([str(p) for p in imgs], imgsz=640, conf=CONF_AUDIT, device=0, verbose=False, batch=16):
            stem = Path(r.path).stem
            lab = DS / split / "labels" / (stem + ".txt")
            L = [l.split() for l in lab.read_text().splitlines() if l.strip()] if lab.exists() else []
            L = [(group(lab_names[int(v[0])]), *[float(z) * 640 for z in v[1:5]]) for v in L]
            for c, s, (x, y, w, h) in zip(r.boxes.cls.cpu(), r.boxes.conf.cpu(), r.boxes.xywh.cpu().tolist()):
                gname = group(names[int(c)])
                best, inside = 0.0, False
                for lg, lx, ly, lw, lh in L:
                    if lg != gname:
                        continue
                    ix = max(0, min(x + w / 2, lx + lw / 2) - max(x - w / 2, lx - lw / 2))
                    iy = max(0, min(y + h / 2, ly + lh / 2) - max(y - h / 2, ly - lh / 2))
                    inter = ix * iy
                    best = max(best, inter / (w * h + lw * lh - inter))
                    inside |= abs(x - lx) <= lw / 2 and abs(y - ly) <= lh / 2
                if best < 0.1 and not inside:
                    rows.append({"tile": stem.split("_png")[0], "split": split, "image": f"{split}/images/{Path(r.path).name}",
                                 "class": names[int(c)], "group": classify_box(names[int(c)], w, h), "conf": round(float(s), 3),
                                 "x": round(x), "y": round(y), "w": round(w), "h": round(h), "max_iou": round(best, 3),
                                 "tile_labels": len(L)})
    rows.sort(key=lambda d: -d["conf"])
    with open(ROOT / "ml" / "audit_missed_labels.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["tile"])
        wr.writeheader()
        wr.writerows(rows)
    return rows


def audit_figure(rows, k=8):
    """En yüksek güvenli k örnek (her karodan en fazla bir tane): kırmızı = model, yeşil = mevcut etiket."""
    seen, pick = set(), []
    for d in rows:
        if d["tile"] not in seen:
            seen.add(d["tile"]), pick.append(d)
        if len(pick) == k:
            break
    if not pick:
        return
    fig, axs = plt.subplots(2, (len(pick) + 1) // 2, figsize=(4 * ((len(pick) + 1) // 2), 8.4))
    for a, d in zip(np.ravel(axs), pick):
        im = Image.open(DS / d["image"]).convert("RGB")
        dr = ImageDraw.Draw(im)
        lab = DS / d["split"] / "labels" / (Path(d["image"]).stem + ".txt")
        for v in (l.split() for l in lab.read_text().splitlines() if l.strip()):
            x, y, w, h = (float(z) * 640 for z in v[1:5])
            dr.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], outline=(46, 204, 113), width=2)
        x, y, w, h = d["x"], d["y"], d["w"], d["h"]
        dr.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], outline=(255, 40, 40), width=3)
        half = max(80, int(max(w, h) * 0.9))   # tespitin çevresini kırp: bağlam + ayrıntı
        cx, cy = min(max(x, half), 640 - half), min(max(y, half), 640 - half)
        a.imshow(im.crop((cx - half, cy - half, cx + half, cy + half)))
        a.set_title(f"{d['tile']} ({d['split']})\n{d['class']} {d['conf']:.2f} · {d['w']}×{d['h']} px", fontsize=9)
        a.set_axis_off()
    for a in np.ravel(axs)[len(pick):]:
        a.set_axis_off()
    fig.suptitle("Olası kaçırılan etiketler: model (kırmızı, güven ≥ 0,5) etiketsiz yerde; yeşil = mevcut etiket", fontsize=11)
    fig.tight_layout(), fig.savefig(FIG / "e10_audit_examples.png", dpi=100), plt.close(fig)


def density_figure(D, tiles):
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.4))
    ext = [P.BOUNDS["west"], P.BOUNDS["east"], P.BOUNDS["south"], P.BOUNDS["north"]]
    for a, (key, title, cmap) in zip(axs, [("coverage", "HiRISE kapsaması (karo oranı)", "Greys"),
                                           ("kum_ml", "kum_ml: kum dalgası kaplaması", "YlOrBr"),
                                           ("kaya_ml", "kaya_ml: kaya yoğunluğu (0,5 = E6 kayalık eşiği)", "Reds")]):
        im = a.imshow(D[key], extent=ext, cmap=cmap, vmin=0, vmax=1)
        a.set_title(title, fontsize=10)
        a.plot(77.45089, 18.44463, "c^", ms=8)   # üs (walkback.js BASE)
        fig.colorbar(im, ax=a, fraction=0.046)
    fig.suptitle(f"E10 · YOLO yoğunlukları, 256² grid (70 m hücre), {len(tiles)} karo", fontsize=11)
    fig.tight_layout(), fig.savefig(FIG / "e10_density.png", dpi=100), plt.close(fig)


def main():
    t0 = time.time()
    meta = json.loads((ROOT / "ml" / "tiles_meta.json").read_text())
    model = YOLO(str(MODEL))
    names = model.names
    sel = json.loads((ROOT / "ml" / "models" / "yolo_marstrail.json").read_text(encoding="utf-8")) \
        if (ROOT / "ml" / "models" / "yolo_marstrail.json").exists() else {}
    tiles, dropped, crs, tr = run_tiles(model, (meta["stretch"]["lo"], meta["stretch"]["hi"]))
    t_inf = time.time() - t0
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "yolo_detections.json").write_text(json.dumps(
        {"model": sel.get("run", MODEL.name), "names": names, "conf_store": CONF_STORE, "tiles": tiles}), encoding="utf-8")
    out = {}
    for n in (P.N_GRID, P.N_IMG):
        D = densities(tiles, names, crs, tr, n)
        np.savez_compressed(PROC / f"ml_density_{n}.npz", **D, model=sel.get("run", MODEL.name))
        out[n] = D
    D = out[P.N_GRID]
    density_figure(D, tiles)
    rows = audit(model, names)
    audit_figure(rows)

    dets = [d for t in tiles for d in t["dets"] if d[1] >= CONF]
    grp = [classify_box(names[d[0]], d[4], d[5]) for d in dets]
    v = ~np.isnan(D["kum_ml"])
    stats = {
        "model": sel.get("run", MODEL.name), "classes": list(names.values()),
        "tiles_inferred": len(tiles), "tiles_plain": sum(t["plain"] for t in tiles), "tiles_dropped_fullres_nodata": dropped,
        "detections_conf_ge_0_25": {g: grp.count(g) for g in ("kaya", "kaya_alani", "kum")},
        "tiles_with_any_detection": sum(any(d[1] >= CONF for d in t["dets"]) for t in tiles),
        "plain_tiles_with_detection": sum(t["plain"] and any(d[1] >= CONF for d in t["dets"]) for t in tiles),
        "grid_cells_with_ml": int(v.sum()),
        "grid_cells_kum_ge_0_5": int((D["kum_ml"][v] >= 0.5).sum()),
        "grid_cells_kaya_ge_0_5": int((D["kaya_ml"][v] >= 0.5).sum()),
        "kum_ml_mean": round(float(np.nanmean(D["kum_ml"])), 3), "kaya_ml_mean": round(float(np.nanmean(D["kaya_ml"])), 3),
        "audit": {"conf_min": CONF_AUDIT, "unmatched": len(rows),
                  "by_split": {s: sum(r["split"] == s for r in rows) for s in ("train", "valid")},
                  "by_group": {g: sum(r["group"] == g for r in rows) for g in ("kaya", "kaya_alani", "kum")},
                  "tiles": len({r["tile"] for r in rows})},
        "seconds": {"inference": round(t_inf, 1), "total": round(time.time() - t0, 1)},
    }
    (FIG / "e10_infer_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("Sonraki: venv\\Scripts\\python scripts\\prep_layers.py  →  venv\\Scripts\\python scripts\\validate.py")


if __name__ == "__main__":
    main()
