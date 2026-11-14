"""
MarsTrail – E6 ek etiketleme: 100 yeni HiRISE karosu (2. parti).

Çalıştır:  venv\\Scripts\\python scripts\\tile_batch2.py
Çıktı:     ml/roboflow_upload_2/*.png, ml/roboflow_upload_2.zip   (git dışı)
           ml/tiles_manifest_2.csv, docs/figures/e6_batch2_selection.png, docs/figures/e6_batch2_stats.json

Neden: v1 eğitiminde (a) tamamen boş karo yalnızca 7 taneydi, model "burada bir şey yok" durumunu az gördü ve
etiketsiz yerlerde kum/kaya alanı uydurdu (confusion matrix arka plan sütunu); (b) kaya_alani yalnızca 82 kutuyla
en zayıf sınıftı. Bu yüzden 2. parti ağırlıklı olarak DÜZ ve KAYALIK karolardan oluşuyor.

Kurallar:
 - Izgara, eleme ve kontrast germe E5 ile AYNI (tile_for_yolo.py fonksiyonları, tiles_meta.json'daki lo/hi):
   karo adları aynı ızgaraya göre, model aynı parlaklık ölçeğini görür.
 - Mevcut 150 karo ve onların 8 komşusu aday dışı: aynı sahnenin bitişik parçası train/val arasında sızıntı yapmasın.
 - Mekânsal yayılım: en uzak nokta örneklemesi, mevcut 150 karo "zaten seçilmiş" sayılarak başlatılır; yeni karolar
   hem birbirinden hem eski karolardan uzak düşer.
"""
import csv
import json
import shutil
import sys
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import transform_bounds
from rasterio.windows import Window

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402
import tile_for_yolo as T  # noqa: E402

OUT = ROOT / "ml/roboflow_upload_2"
FIG = ROOT / "docs/figures"
# 100 karo: düz 45 (35 dokulu-düz + 10 dokusuz), kayalık 40, kum 15. Kum v1'de zaten en çok örnekli sınıf.
N_FLAT_TEX, N_FLAT_PLAIN, N_ROCK, N_SAND = 35, 10, 40, 15
SEED = 7


def fps_seeded(cands, n, taken, gap=True):
    """En uzak nokta örneklemesi; 'taken' (eski + bu partide seçilmiş) karolara uzaklıkla başlar.
    gap=True: seçilen karoların 8 komşusu da aday dışı (bitişik karo yok)."""
    if not cands or n <= 0:
        return []
    c = np.array(cands, float)
    t = np.array(list(taken), float)
    d = np.min(np.hypot(c[:, None, 0] - t[None, :, 0], c[:, None, 1] - t[None, :, 1]), axis=1)
    if gap:
        d[d < 1.5] = -1   # zaten seçilmiş bir karoya bitişik aday alınmaz
    out = []
    for _ in range(min(n, len(c))):
        j = int(np.argmax(d))
        out.append(tuple(int(v) for v in c[j]))
        taken.add(out[-1])
        d = np.minimum(d, np.hypot(*(c - c[j]).T))
        d[np.max(np.abs(c - c[j]), axis=1) <= (1 if gap else 0)] = -1   # gap: 8 komşu da çıkar
        if d.max() < 0:
            break
    return out


def main():
    meta = json.loads((ROOT / "ml/tiles_meta.json").read_text())
    lo, hi = meta["stretch"]["lo"], meta["stretch"]["hi"]
    old = list(csv.DictReader(open(ROOT / "ml/tiles_manifest.csv", encoding="utf-8")))
    old_rc = {(int(r["tile_row"]), int(r["tile_col"])) for r in old}

    with rasterio.open(T.ORTHO) as src:
        nodata = src.nodata if src.nodata is not None else 0
        c0, r0, nx, ny = T.study_window(src)
        assert [c0, r0] == meta["study_origin_px"], "Izgara E5 ile aynı olmalı"
        prev, k = T.preview(src, c0, r0, nx, ny)
        nod, std = T.tile_stats(prev, k, nodata)
        frac = T.geology_fractions(src, c0, r0, nx, ny, k)

        clean = nod == 0
        flat_thr = float(np.percentile(std[clean], 5))           # E5'teki "dokusuz" eşiğiyle aynı tanım
        plain = clean & (std < flat_thr)
        sand = frac.get("Eolian bedform unit", np.zeros_like(std))
        rockf = sum(frac[n] for n in frac if n in T.ROCK_UNITS)
        # Eski karolar + 8 komşusu dışarıda
        near_old = np.zeros_like(clean)
        for r, c in old_rc:
            near_old[max(0, r - 1):r + 2, max(0, c - 1):c + 2] = True
        free = clean & ~near_old
        tex = clean & ~plain
        p35 = float(np.percentile(std[tex], 35))   # düz: doku alt %35 (E5 negatifi "medyanın altı" idi; daha sıkı)
        p60 = float(np.percentile(std[tex], 60))   # kayalık: doku üst %40
        cand = {
            "duz": [tuple(x) for x in zip(*np.where(free & tex & (sand < 0.1) & (std < p35)))],
            "duz_dokusuz": [tuple(x) for x in zip(*np.where(free & plain & (sand < 0.1)))],
            "kayalik": [tuple(x) for x in zip(*np.where(free & tex & (sand < 0.2) & (rockf >= 0.5) & (std >= p60)))],
            "kum": [tuple(x) for x in zip(*np.where(free & tex & (sand >= T.SAND_MIN)))],
        }
        # Gevşek kayalık: eski karoların komşuları dışlanınca sıkı kayalık adayı az kalıyor (ilk denemede 32/40).
        # Eksik, kaya vekili birim ≥ %40 ve doku üst yarı (medyan) ile doldurulur.
        p50 = float(np.percentile(std[tex], 50))
        cand["kayalik_gevsek"] = [tuple(x) for x in zip(*np.where(free & tex & (sand < 0.2) & (rockf >= 0.4) & (std >= p50)))]
        taken = set(old_rc)
        picks = []
        for cat, n in (("kayalik", N_ROCK), ("duz", N_FLAT_TEX), ("duz_dokusuz", N_FLAT_PLAIN), ("kum", N_SAND)):
            got = fps_seeded([x for x in cand[cat] if x not in taken], n, taken)
            picks += [(rc, cat) for rc in got]
            if cat == "kayalik" and len(got) < n:   # eksik kayalığı gevşek kriterle tamamla
                picks += [(rc, "kayalik") for rc in fps_seeded([x for x in cand["kayalik_gevsek"] if x not in taken], n - len(got), taken)]
        # Bitişiksiz seçimle alan doluyor (~81 karo). Kalan, ESKİ karolara bitişik olmadan ama bu partide bitişik
        # olabilecek şekilde önce kayalık, sonra düz adaylardan tamamlanır. Bitişik karolar yeniden eğitimde
        # grup bazlı train/val bölmesiyle aynı tarafa konacak (sızıntı yok).
        n_gap = len(picks)
        old_adj = lambda x: any(abs(x[0] - a) <= 1 and abs(x[1] - b) <= 1 for a, b in old_rc)
        for cat, pool in (("kayalik", cand["kayalik"] + cand["kayalik_gevsek"]), ("duz", cand["duz"])):
            short = N_ROCK + N_FLAT_TEX + N_FLAT_PLAIN + N_SAND - len(picks)
            want = min(short, N_ROCK - sum(c == "kayalik" for _, c in picks)) if cat == "kayalik" else short
            pool = list(dict.fromkeys(x for x in pool if x not in taken and not old_adj(x)))
            picks += [(rc, cat) for rc in fps_seeded(pool, want, set(old_rc) | {p for p, _ in picks}, gap=False)]
            taken |= {p for p, _ in picks}

        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True)
        geo = P.target_crs()
        rows, dropped = [], 0
        for (r, c), cat in picks:
            col, row = c0 + c * T.TILE, r0 + r * T.TILE
            a = src.read(1, window=Window(col, row, T.TILE, T.TILE))
            if (a == nodata).any():
                dropped += 1
                continue
            img = np.clip((a.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            name = f"jz_r{r:03d}_c{c:03d}.png"
            Image.fromarray(img, "L").save(OUT / name, optimize=True)
            x0, y0 = src.transform * (col, row)
            x1, y1 = src.transform * (col + T.TILE, row + T.TILE)
            w, s, e, n = transform_bounds(src.crs, geo, x0, y1, x1, y0)
            units = {u: round(float(frac[u][r, c]), 2) for u in frac if frac[u][r, c] > 0.05}
            rows.append({"file": name, "category": cat, "tile_row": r, "tile_col": c, "px_col": col, "px_row": row,
                         "west": round(w, 6), "south": round(s, 6), "east": round(e, 6), "north": round(n, 6),
                         "sand_frac": round(float(sand[r, c]), 2), "preview_std": round(float(std[r, c]), 1),
                         "units": json.dumps(units, ensure_ascii=False)})

    assert not ({(x["tile_row"], x["tile_col"]) for x in rows} & old_rc), "eski karoyla çakışma"
    with open(ROOT / "ml/tiles_manifest_2.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    zpath = ROOT / "ml/roboflow_upload_2.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(OUT.glob("*.png")):
            z.write(p, p.name)

    # En yakın eski karoya uzaklık (karo cinsinden): yayılım ve sızıntı kontrolü
    oa = np.array(sorted(old_rc), float)
    dmin = [float(np.min(np.hypot(oa[:, 0] - x["tile_row"], oa[:, 1] - x["tile_col"]))) for x in rows]
    stats = {"spread_no_adjacent": n_gap, "filled_adjacent_ok": len(rows) - n_gap, "candidates": {k: len(v) for k, v in cand.items()}, "excluded_old_and_neighbors": int((clean & near_old).sum()),
             "std_thresholds": {"dokusuz": round(flat_thr, 2), "duz_p35": round(p35, 2), "kayalik_p60": round(p60, 2)},
             "selected": {cat: sum(x["category"] == cat for x in rows) for cat in ("kayalik", "duz", "duz_dokusuz", "kum")},
             "dropped_nodata_fullres": dropped, "total": len(rows),
             "min_dist_to_old_tiles": {"min": min(dmin), "median": float(np.median(dmin))},
             "zip_mb": round(zpath.stat().st_size / 1e6, 1), "stretch": [lo, hi]}
    (FIG / "e6_batch2_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    show = np.clip((prev.astype(np.float32) - lo) / (hi - lo), 0, 1)
    show = np.where(prev == nodata, np.nan, show)
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(show, cmap="gray")
    for r, c in old_rc:
        ax.add_patch(plt.Rectangle((c * k, r * k), k, k, fill=False, ec="#999999", lw=1))
    col = {"kayalik": "#e74c3c", "duz": "#3498db", "duz_dokusuz": "#00e5ff", "kum": "#f1c40f"}
    for x in rows:
        ax.add_patch(plt.Rectangle((x["tile_col"] * k, x["tile_row"] * k), k, k, fill=False, ec=col[x["category"]], lw=1.8))
    h = [plt.Line2D([], [], color="#999999", lw=3, label=f"1. parti ({len(old_rc)})")]
    h += [plt.Line2D([], [], color=v, lw=3, label=f"2. parti {kk} ({stats['selected'][kk]})") for kk, v in col.items()]
    ax.legend(handles=h, loc="lower left", fontsize=9)
    ax.set_title("E6 ek etiketleme: 100 yeni karo (eski karolar ve komşuları hariç)")
    ax.set_axis_off()
    fig.tight_layout(), fig.savefig(FIG / "e6_batch2_selection.png", dpi=110), plt.close(fig)
    print(f"Hazır: {zpath}")


if __name__ == "__main__":
    main()
