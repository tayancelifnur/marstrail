"""
MarsTrail – YOLO etiketleme karoları (E5).

Girdi:  data/raw/D8_hirise/MSR_hirise_soc_003_Orthomosaic_0.25m_..._First_NoBlend.tif  (D8, HiRISE 25 cm)
        data/raw/D6_geology/Jezero_GeoUnits.shp  (karo seçimi için birim bilgisi)
Çıktı:  ml/roboflow_upload/*.png         Roboflow'a yüklenecek 640×640 karolar (git dışı)
        ml/roboflow_upload.zip            aynı karolar tek zip (git dışı)
        ml/tiles_manifest.csv             karo → konum, birim, seçim nedeni (E10 çıkarımında geri eşleme için)
        ml/tiles_meta.json                ızgara kökeni, CRS, kontrast germe parametreleri
        docs/figures/d8_tile_selection.png, d8_tile_samples.png, e5_stats.json

Çalıştır:  venv\\Scripts\\python scripts\\tile_for_yolo.py

Yöntem (ayrıntı ve sayılar: docs/DATA_PIPELINE.md, D8):
 1. Çalışma alanı (E3 ile aynı) ortogörüntü üzerinde 640×640 piksellik (160×160 m) örtüşmesiz karolara bölünür.
 2. Eleme ön görünümde (1/16 ölçek) yapılır: NoData içeren karolar ve dokusuz (düz) karolar atılır.
 3. Her karoya jeoloji birimi oranları atanır. Seçim:
      kum adayı  : eolyen birim ≥ %60
      kaya adayı : kaya vekili yüksek birimler (krater kenarı, pürüzlü, delta, aşınmış) ve doku üst yarıda
      negatif    : düz krater tabanı (model "her şeyi tehlike" sanmasın diye boş örnek)
    Her gruptan mekânsal olarak yayılmış örnek seçilir (en uzak nokta örneklemesi), aynı yerin
    komşu karoları tekrar etmesin.
 4. Seçilen karolar tam çözünürlükte okunur, NoData yeniden kontrol edilir, alan genelinde tek bir
    doğrusal kontrast germe uygulanır (karo başına değil: model çıkarımda da aynı germeyi görecek).
"""
import csv
import json
import math
import shutil
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
from PIL import Image
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.warp import transform_bounds
from rasterio.windows import Window

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402

ORTHO = ROOT / "data/raw/D8_hirise/MSR_hirise_soc_003_Orthomosaic_0.25m_Eqc_latTs0_lon0_First_NoBlend.tif"
GEOLOGY = ROOT / "data/raw/D6_geology/Jezero_GeoUnits.shp"
UPLOAD = ROOT / "ml/roboflow_upload"
FIG = ROOT / "docs/figures"

TILE = 640           # YOLOv8 varsayılan giriş boyu; 640 px × 0,25 m = 160 m
DEC = 16             # ön görünüm ölçeği: karo = 40×40 ön görünüm pikseli
N_SAND, N_ROCK, N_NEG = 70, 65, 15   # toplam 150 (kart: 150 karo; ~%10 negatif örnek)
SAND_MIN = 0.60      # karonun en az %60'ı eolyen birim → kum dalgası adayı
ROCK_UNITS = {"Crater rim unit", "Rugged bright unit", "Jezero fan 1 unit", "Jezero fan 2 unit",
              "Upper etched unit", "Lower etched unit", "Crater ejecta unit"}
NEG_UNITS = {"Jezero floor unit", "Smooth unit, undivided"}
SEED = 42


def study_window(src):
    """E3 çalışma alanının ortogörüntüdeki piksel penceresi, karo katına yuvarlanmış."""
    l, b, r, t = transform_bounds(P.target_crs(), src.crs, *P.BBOX)
    c0, r0 = ~src.transform * (l, t)
    c1, r1 = ~src.transform * (r, b)
    c0, r0 = max(0, int(c0)), max(0, int(r0))
    c1, r1 = min(src.width, int(c1)), min(src.height, int(r1))
    nx, ny = (c1 - c0) // TILE, (r1 - r0) // TILE
    return c0, r0, nx, ny


def preview(src, c0, r0, nx, ny):
    """Çalışma alanını 1/DEC ölçekte okur (her karo = TILE/DEC kare piksel)."""
    w = Window(c0, r0, nx * TILE, ny * TILE)
    k = TILE // DEC
    return src.read(1, window=w, out_shape=(ny * k, nx * k), resampling=Resampling.nearest), k


def geology_fractions(src, c0, r0, nx, ny, k):
    g = gpd.read_file(GEOLOGY)
    g["name"] = g["name"].replace(P.GEO_FIX)
    g = g.to_crs(src.crs)
    names = sorted(set(g["name"]))
    x0, y0 = src.transform * (c0, r0)
    px = src.transform.a * DEC
    tr = rasterio.transform.from_origin(x0, y0, px, px)
    shapes = ((geom, names.index(n) + 1) for geom, n in zip(g.geometry, g["name"]))
    lab = rasterize(shapes, out_shape=(ny * k, nx * k), transform=tr, fill=0, dtype="int16")
    frac = {}
    for i, n in enumerate(names, start=1):
        frac[n] = (lab == i).reshape(ny, k, nx, k).mean(axis=(1, 3))
    return frac


def tile_stats(prev, k, nodata):
    ny, nx = prev.shape[0] // k, prev.shape[1] // k
    t = prev.reshape(ny, k, nx, k).transpose(0, 2, 1, 3).reshape(ny, nx, k * k).astype(np.float32)
    nod = (t == nodata).mean(axis=2) if nodata is not None else np.zeros((ny, nx))
    std = t.std(axis=2)
    return nod, std


def farthest_point_sample(cands, n, rng):
    """Mekânsal yayılım: her adımda seçilenlere en uzak adayı ekler (aynı yerin komşuları tekrar etmesin)."""
    if len(cands) <= n:
        return list(cands)
    cands = np.array(cands)
    first = rng.integers(len(cands))
    chosen = [first]
    d = np.hypot(*(cands - cands[first]).T)
    for _ in range(n - 1):
        j = int(np.argmax(d))
        chosen.append(j)
        d = np.minimum(d, np.hypot(*(cands - cands[j]).T))
    return [tuple(cands[j]) for j in chosen]


def main():
    rng = np.random.default_rng(SEED)
    stats = {}
    with rasterio.open(ORTHO) as src:
        nodata = src.nodata if src.nodata is not None else 0
        stats["ortho"] = {"width": src.width, "height": src.height, "dtype": src.dtypes[0], "res_m": src.res[0],
                          "nodata": nodata, "crs": CRS(src.crs).name, "file_gb": round(ORTHO.stat().st_size / 1e9, 2)}
        c0, r0, nx, ny = study_window(src)
        print(f"Çalışma alanı: {nx}×{ny} = {nx * ny} karo ({TILE}px = {TILE * src.res[0]:.0f} m)")
        prev, k = preview(src, c0, r0, nx, ny)
        nod, std = tile_stats(prev, k, nodata)
        frac = geology_fractions(src, c0, r0, nx, ny, k)

        # Kontrast germe: alan genelinde %0,5–99,5 (NoData hariç), tek doğrusal dönüşüm
        valid = prev[prev != nodata]
        lo, hi = (float(v) for v in np.percentile(valid, [0.5, 99.5]))

        # --- Eleme ---
        total = nx * ny
        has_nod = nod > 0
        # Dokusuz karo: ön görünüm std'si, NoData'sız karoların alt %5'inin altında (düz toz/gölge, etiketlenecek bir şey yok)
        flat_thr = float(np.percentile(std[~has_nod], 5)) if (~has_nod).any() else 0.0
        flat = (~has_nod) & (std < flat_thr)
        ok = (~has_nod) & (~flat)
        sand = sum(frac[n] for n in frac if n == "Eolian bedform unit")
        rockf = sum(frac[n] for n in frac if n in ROCK_UNITS)
        negf = sum(frac[n] for n in frac if n in NEG_UNITS)
        std_med = float(np.median(std[ok]))
        sand_c = [(r, c) for r, c in zip(*np.where(ok & (sand >= SAND_MIN)))]
        rock_c = [(r, c) for r, c in zip(*np.where(ok & (sand < 0.2) & (rockf >= 0.6) & (std >= std_med)))]
        neg_c = [(r, c) for r, c in zip(*np.where(ok & (sand < 0.05) & (negf >= 0.9) & (std < std_med)))]
        stats["screen"] = {"tiles_total": total, "dropped_nodata": int(has_nod.sum()), "dropped_flat": int(flat.sum()),
                           "flat_std_threshold": round(flat_thr, 2), "usable": int(ok.sum()),
                           "cand_sand": len(sand_c), "cand_rock": len(rock_c), "cand_neg": len(neg_c),
                           "stretch_p0_5": lo, "stretch_p99_5": hi}
        print(json.dumps(stats["screen"], ensure_ascii=False))

        picks = ([(rc, "kum_adayi") for rc in farthest_point_sample(sand_c, N_SAND, rng)]
                 + [(rc, "kaya_adayi") for rc in farthest_point_sample(rock_c, N_ROCK, rng)]
                 + [(rc, "negatif") for rc in farthest_point_sample(neg_c, N_NEG, rng)])

        # --- Tam çözünürlükte oku, yeniden kontrol et, ger, kaydet ---
        if UPLOAD.exists():
            shutil.rmtree(UPLOAD)
        UPLOAD.mkdir(parents=True)
        geo_crs = P.target_crs()
        rows, dropped_full = [], 0
        for (r, c), cat in picks:
            col, row = c0 + int(c) * TILE, r0 + int(r) * TILE
            a = src.read(1, window=Window(col, row, TILE, TILE))
            if (a == nodata).any():
                dropped_full += 1
                continue
            img = np.clip((a.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            name = f"jz_r{int(r):03d}_c{int(c):03d}.png"
            Image.fromarray(img, "L").save(UPLOAD / name, optimize=True)
            x0, y0 = src.transform * (col, row)
            x1, y1 = src.transform * (col + TILE, row + TILE)
            w, s, e, n = transform_bounds(src.crs, geo_crs, x0, y1, x1, y0)
            units = {u: round(float(frac[u][r, c]), 2) for u in frac if frac[u][r, c] > 0.05}
            rows.append({"file": name, "category": cat, "tile_row": int(r), "tile_col": int(c),
                         "px_col": col, "px_row": row, "west": round(w, 6), "south": round(s, 6),
                         "east": round(e, 6), "north": round(n, 6), "sand_frac": round(float(sand[r, c]), 2),
                         "preview_std": round(float(std[r, c]), 1), "units": json.dumps(units, ensure_ascii=False)})
        stats["selected"] = {"kum_adayi": sum(x["category"] == "kum_adayi" for x in rows),
                             "kaya_adayi": sum(x["category"] == "kaya_adayi" for x in rows),
                             "negatif": sum(x["category"] == "negatif" for x in rows),
                             "dropped_nodata_fullres": dropped_full, "total": len(rows)}
        print(json.dumps(stats["selected"], ensure_ascii=False))

        with open(ROOT / "ml/tiles_manifest.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        meta = {"ortho": ORTHO.name, "crs_wkt": src.crs.to_wkt(), "transform": list(src.transform)[:6],
                "study_origin_px": [c0, r0], "tiles_x": nx, "tiles_y": ny, "tile_px": TILE, "res_m": src.res[0],
                "stretch": {"method": "linear, study-area percentiles 0.5–99.5 (NoData excluded)", "lo": lo, "hi": hi},
                "nodata": nodata, "classes": ["kaya", "kum_dalgasi"]}
        (ROOT / "ml/tiles_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        zpath = ROOT / "ml/roboflow_upload.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:  # PNG zaten sıkıştırılmış
            for p in sorted(UPLOAD.glob("*.png")):
                z.write(p, p.name)
        stats["upload"] = {"zip_mb": round(zpath.stat().st_size / 1e6, 1), "files": len(rows)}

        figures(prev, k, nod, flat, rows, lo, hi, nodata)
    FIG.mkdir(parents=True, exist_ok=True)
    (FIG / "e5_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Hazır: {zpath}  ({stats['upload']['zip_mb']} MB, {len(rows)} karo)")


def figures(prev, k, nod, flat, rows, lo, hi, nodata):
    FIG.mkdir(parents=True, exist_ok=True)
    show = np.clip((prev.astype(np.float32) - lo) / (hi - lo), 0, 1)
    show = np.where(prev == nodata, np.nan, show)
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(show, cmap="gray")
    col = {"kum_adayi": "#f1c40f", "kaya_adayi": "#e74c3c", "negatif": "#3498db"}
    for r, c in zip(*np.where(nod > 0)):
        ax.add_patch(plt.Rectangle((c * k, r * k), k, k, color="#ff00ff", alpha=0.25, lw=0))
    for r, c in zip(*np.where(flat)):
        ax.add_patch(plt.Rectangle((c * k, r * k), k, k, color="#00ffff", alpha=0.25, lw=0))
    for x in rows:
        ax.add_patch(plt.Rectangle((x["tile_col"] * k, x["tile_row"] * k), k, k, fill=False, ec=col[x["category"]], lw=1.5))
    handles = [plt.Line2D([], [], color=v, lw=3, label=f"{kk} ({sum(x['category'] == kk for x in rows)})") for kk, v in col.items()]
    handles += [plt.Line2D([], [], color="#ff00ff", lw=6, alpha=0.4, label="atıldı: NoData"),
                plt.Line2D([], [], color="#00ffff", lw=6, alpha=0.4, label="atıldı: dokusuz")]
    ax.legend(handles=handles, loc="lower left", fontsize=9)
    ax.set_title("D8 HiRISE 25 cm – çalışma alanı karoları (160 m) ve seçim")
    ax.set_axis_off()
    fig.tight_layout(), fig.savefig(FIG / "d8_tile_selection.png", dpi=110), plt.close(fig)

    samp = [x for cat in ("kum_adayi", "kaya_adayi", "negatif") for x in [y for y in rows if y["category"] == cat][:3]]
    fig, axs = plt.subplots(3, 3, figsize=(10, 10))
    for a, x in zip(axs.ravel(), samp):
        a.imshow(Image.open(UPLOAD / x["file"]), cmap="gray", vmin=0, vmax=255)
        a.set_title(f"{x['category']} · {x['file']}", fontsize=9)
        a.set_axis_off()
    fig.tight_layout(), fig.savefig(FIG / "d8_tile_samples.png", dpi=90), plt.close(fig)


if __name__ == "__main__":
    main()
