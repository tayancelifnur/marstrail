"""
MarsTrail – katmanlar ve grid (E3).

Girdi (data/raw/, E2 ile indi):
  D4  Jezero_Thermal_Inertia_v1.tiff     THEMIS termal eylemsizlik, 100 m, SimpleCylindrical
  D5  M20_JezeroCrater_CTXDEM_20m.tif    CTX DEM, 20 m, Jezero_Crater_Projection
  D6  D6_geology/Jezero_GeoUnits.shp     USGS SIM 3464 jeolojik birimleri, MTM_clon77_5E

Çıktı:
  web/data/layers/{hillshade,slope,thermal,geology,traversability}.png  (RGBA, şeffaf)
  web/data/layers.json   (bbox derece: [batı, güney, doğu, kuzey])
  web/data/grid.json     (256x256: elev, cost, blocked, bounds)
  data/processed/layers_1024.npz, grid_256.npz  (E8/E10 için ham diziler)

Çalıştır:  venv\\Scripts\\python scripts\\prep_layers.py

Hepsi aynı koordinat sistemine getirilir: Mars 2000 küresi üzerinde coğrafi
(derece, doğu pozitif). Cesium PNG'yi bbox dikdörtgenine yaydığı için
eşit-açılı (lon/lat) ızgara doğrudan doğru yere oturur.
"""
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from rasterio.warp import reproject

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "web" / "data"
LAYERS_DIR = OUT / "layers"

DEM = RAW / "M20_JezeroCrater_CTXDEM_20m.tif"
THERMAL = RAW / "Jezero_Thermal_Inertia_v1.tiff"
GEOLOGY = RAW / "D6_geology" / "Jezero_GeoUnits.shp"

# Çalışma alanı: üs (77.451, 18.445), delta önü / Three Forks (77.40-77.41, 18.45),
# Cheyava Falls (77.305, 18.498) hepsi içeride. Kenarlar metre cinsinden ~kare:
# 0.20° boylam × cos(18.46°) ≈ 0.19° enlem → ~11.2 × 11.2 km.
BOUNDS = {"west": 77.28, "south": 18.365, "east": 77.48, "north": 18.555}
BBOX = [BOUNDS["west"], BOUNDS["south"], BOUNDS["east"], BOUNDS["north"]]
N_IMG = 1024  # PNG çözünürlüğü (~11 m/piksel; DEM 20 m olduğu için yeterli)
N_GRID = 256  # veri sözleşmesi: 256x256

MARS_R = 3396190.0  # m, Mars 2000 küresi (girdilerin hepsi bu yarıçapı kullanıyor)
M_PER_DEG = 2 * math.pi * MARS_R / 360

# Yürüme/geçilmezlik eşikleri (PLAN.md §5, varsayım)
SLOPE_MAX_DEG = 25.0   # astronot için güvenli kabul edilen üst eğim
SCORE_MAX = 0.8        # birleşik skor bunun üstündeyse geçilmez

# Jeolojik birim → (yürünebilirlik 0-1, kaya/pürüz vekili 0-1, bilim değeri 1-5, renk)
# VARSAYIM: Katsayılar SIM 3464 birim tanımlarından takdirle seçildi, gerçek EVA verisiyle
# kalibre edilmedi. "Kaya vekili", YOLO kaya yoğunluğu gelene kadar (E10) formüldeki
# kaya_yoğunluğu teriminin yerini tutar. Eolyen birimin cezası kaya yerine "kum" teriminden
# gelir, iki kez sayılmasın diye kaya vekili 0.
GEO_UNITS = {
    "Jezero fan 1 unit":      (0.70, 0.30, 5, (93, 156, 236)),   # delta: katmanlı, basamaklı
    "Jezero fan 2 unit":      (0.70, 0.30, 5, (120, 175, 245)),
    "Jezero floor unit":      (0.85, 0.15, 4, (196, 160, 120)),  # Máaz: düz lav/tortu
    "Lower etched unit":      (0.75, 0.25, 3, (170, 120, 90)),
    "Upper etched unit":      (0.75, 0.25, 3, (150, 105, 80)),
    "Nili Planum fan unit":   (0.70, 0.30, 3, (110, 140, 200)),
    "Nili Planum 1 unit":     (0.70, 0.30, 2, (140, 130, 110)),
    "Nili Planum 2 unit":     (0.70, 0.30, 2, (125, 115, 100)),
    "Eolian bedform unit":    (0.30, 0.00, 2, (240, 200, 120)),  # kum dalgaları: batma riski
    "Smooth unit, undivided": (0.90, 0.10, 2, (185, 185, 175)),
    "Rugged bright unit":     (0.50, 0.50, 3, (230, 230, 210)),  # pürüzlü, kayalık
    "Crater rim unit":        (0.40, 0.60, 3, (120, 94, 74)),
    "Crater ejecta unit":     (0.60, 0.40, 2, (155, 120, 95)),
    "Crater interior unit":   (0.50, 0.50, 1, (100, 80, 65)),
}
GEO_FIX = {"Crater riim unit": "Crater rim unit"}  # kaynaktaki yazım hatası


def target_crs():
    with rasterio.open(DEM) as src:
        return CRS(src.crs).geodetic_crs  # Mars 2000 küresi, coğrafi


def warp(path, n, resampling, dst_crs, src_nodata=None):
    """Bir rasteri çalışma alanına, n×n coğrafi ızgaraya taşır. Veri yoksa NaN."""
    dst = np.full((n, n), np.nan, dtype=np.float32)
    transform = from_bounds(*BBOX, n, n)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, src_nodata=src_nodata if src_nodata is not None else src.nodata,
                  dst_transform=transform, dst_crs=dst_crs, dst_nodata=np.nan, resampling=resampling)
    return dst


def slope_native():
    """Eğimi DEM'in kendi 20 m metrik ızgarasında hesaplar (yeniden örnekleme eğimi yumuşatmasın).
    Sonuç geçici bir GeoTIFF'e yazılır ve oradan çalışma alanına taşınır."""
    out = PROC / "slope_20m.tif"
    if out.exists() and out.stat().st_mtime > DEM.stat().st_mtime:
        return out
    with rasterio.open(DEM) as src:
        z = src.read(1).astype(np.float32)
        z[(z < -9000) | (z > 30000)] = np.nan  # nodata (-3.4e38)
        gy, gx = np.gradient(z, abs(src.res[1]), src.res[0])
        slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)
        prof = src.profile | {"dtype": "float32", "nodata": np.nan, "compress": "deflate"}
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(np.nan_to_num(slope, nan=np.nan), 1)
    return out


def geology(n, dst_crs):
    """Birim adlarını n×n ızgaraya rasterize eder. Dönüş: birim indeksi (-1 = harita dışı) ve isim listesi."""
    g = gpd.read_file(GEOLOGY)
    g["name"] = g["name"].replace(GEO_FIX)
    names = list(GEO_UNITS)
    unknown = sorted(set(g["name"]) - set(names))
    if unknown:
        print("  UYARI: katsayısı olmayan birimler (yok sayıldı):", unknown)
    g = g[g["name"].isin(names)]
    g = g.assign(_a=g.geometry.area).to_crs(dst_crs)  # alan kaynak (metrik) projeksiyonda
    # Önce büyük poligonlar, sonra küçükler (küçük birimler üstte kalsın)
    g = g.sort_values("_a", ascending=False)
    shapes = ((geom, names.index(nm)) for geom, nm in zip(g.geometry, g["name"]))
    idx = rasterize(shapes, out_shape=(n, n), transform=from_bounds(*BBOX, n, n), fill=-1, dtype="int16")
    return idx, names


def unit_table(idx, names, col):
    lut = np.array([GEO_UNITS[nm][col] for nm in names] + [np.nan], dtype=np.float32)
    return lut[np.where(idx < 0, len(names), idx)]


def normalize_thermal(ti):
    """Termal eylemsizliği 0-1'e ölçekler (çalışma alanındaki %2-%98 aralığı).
    Düşük = gevşek kum/toz (batma riski), yüksek = sert kaya."""
    lo, hi = np.nanpercentile(ti, [2, 98])
    return np.clip((ti - lo) / (hi - lo), 0, 1), float(lo), float(hi)


def build(n, crs, slope_tif):
    elev = warp(DEM, n, Resampling.average, crs)
    slope = warp(slope_tif, n, Resampling.average, crs)  # ortalama eğim: yürüyüş maliyeti için
    ti = warp(THERMAL, n, Resampling.bilinear, crs, src_nodata=0)
    th_norm, lo, hi = normalize_thermal(ti)
    gidx, names = geology(n, crs)
    walk = unit_table(gidx, names, 0)
    rock = unit_table(gidx, names, 1)
    sand = (gidx == names.index("Eolian bedform unit")).astype(np.float32)

    # Birleşik geçilebilirlik skoru (PLAN.md §5; ağırlıklar varsayım):
    #   0,4·eğim_risk + 0,25·kum + 0,15·kaya + 0,2·(1 − termal_norm)
    # Jeoloji haritası dışında kalan hücrelerde kaya terimi 0,3 (bilinmiyor, orta) kabul edilir.
    slope_risk = np.clip(slope / SLOPE_MAX_DEG, 0, 1)
    rock_f = np.where(np.isnan(rock), 0.3, rock)
    th_f = np.where(np.isnan(th_norm), 0.5, th_norm)
    score = np.clip(0.4 * slope_risk + 0.25 * sand + 0.15 * rock_f + 0.2 * (1 - th_f), 0, 1)
    nodata = np.isnan(elev) | np.isnan(slope)
    return dict(elev=elev, slope=slope, ti=ti, thermal=th_norm, ti_range=(lo, hi), geo=gidx, geo_names=names,
                walk=walk, rock=rock, sand=sand, score=score, nodata=nodata)


# ---------------------------------------------------------------------------
# PNG'ler
# ---------------------------------------------------------------------------
def ramp(v, stops, alpha=180, mask=None):
    v = np.clip(np.nan_to_num(v, nan=0), 0, 1)
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    rgba = np.zeros(v.shape + (4,), dtype=np.uint8)
    for i in range(3):
        rgba[..., i] = np.interp(v, pos, cols[:, i])
    rgba[..., 3] = alpha
    if mask is not None:
        rgba[mask] = 0
    return rgba


def save_png(name, rgba):
    path = LAYERS_DIR / name
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)
    print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size / 1024:.0f} KB)")


def hillshade(elev, az=315, alt=45):
    cell = (BOUNDS["north"] - BOUNDS["south"]) * M_PER_DEG / elev.shape[0]
    z = np.where(np.isnan(elev), np.nanmean(elev), elev)
    gy, gx = np.gradient(z, cell)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, b = np.radians(az), np.radians(alt)
    hs = np.sin(b) * np.cos(slope) + np.cos(b) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1)


GREEN_RED = [(0, (46, 204, 113)), (0.5, (241, 196, 15)), (1, (231, 76, 60))]


def make_pngs(L):
    m = L["nodata"]
    hs = hillshade(L["elev"])
    rgba = np.zeros(hs.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = (hs * 255).astype(np.uint8)[..., None]
    rgba[..., 3] = 255
    rgba[m] = 0
    save_png("hillshade.png", rgba)

    save_png("slope.png", ramp(L["slope"] / SLOPE_MAX_DEG, GREEN_RED, mask=m))
    save_png("thermal.png", ramp(L["thermal"], [(0, (230, 126, 34)), (0.5, (190, 170, 140)), (1, (52, 73, 94))],
                                 mask=np.isnan(L["thermal"])))
    geo = np.zeros(L["geo"].shape + (4,), dtype=np.uint8)
    for i, nm in enumerate(L["geo_names"]):
        geo[L["geo"] == i] = (*GEO_UNITS[nm][3], 170)
    save_png("geology.png", geo)
    tr = ramp(L["score"], GREEN_RED, mask=m)
    tr[(L["slope"] > SLOPE_MAX_DEG) | (L["score"] > SCORE_MAX)] = (40, 0, 0, 220)  # geçilmez: koyu
    save_png("traversability.png", tr)


def make_layers_json(L):
    lo, hi = L["ti_range"]
    present = [nm for i, nm in enumerate(L["geo_names"]) if (L["geo"] == i).any()]
    hexc = lambda c: "#%02x%02x%02x" % c  # noqa: E731
    common = {"bbox": BBOX}
    layers = [
        {"id": "hillshade", "name": "Arazi gölgesi (CTX DEM)", "file": "layers/hillshade.png", "default_opacity": 0.5,
         "legend": [{"color": "#ffffff", "label": "Güneye bakan yamaç (ışık KB'dan)"}, {"color": "#000000", "label": "Gölgede kalan yamaç"}],
         "source": "CTX DEM 20 m, USGS Astrogeology / JPL (Mars 2020)", **common},
        {"id": "slope", "name": "Eğim", "file": "layers/slope.png", "default_opacity": 0.6,
         "legend": [{"color": "#2ecc71", "label": "0°"}, {"color": "#f1c40f", "label": "12,5°"},
                    {"color": "#e74c3c", "label": f"≥{SLOPE_MAX_DEG:.0f}° (geçilmez)"}],
         "source": "CTX DEM 20 m (USGS) → eğim, 20 m'de hesaplanıp ortalandı", **common},
        {"id": "thermal", "name": "Termal eylemsizlik (zemin gevşekliği)", "file": "layers/thermal.png", "default_opacity": 0.6,
         "legend": [{"color": "#e67e22", "label": f"Düşük (~{lo:.0f} TIU) – gevşek kum/toz"},
                    {"color": "#34495e", "label": f"Yüksek (~{hi:.0f} TIU) – sert kaya"}],
         "source": "THEMIS termal eylemsizlik, Jezero mozaiği (Zenodo 4931348), 100 m", **common},
        {"id": "geology", "name": "Jeoloji birimleri", "file": "layers/geology.png", "default_opacity": 0.5,
         "legend": [{"color": hexc(GEO_UNITS[nm][3]), "label": f"{nm} (yürünebilirlik {GEO_UNITS[nm][0]})"} for nm in present],
         "source": "USGS SIM 3464, Jezero Krateri ve Nili Planum jeolojik haritası (Sun ve Stack, 2020)", **common},
        {"id": "traversability", "name": "Birleşik geçilebilirlik", "file": "layers/traversability.png", "default_opacity": 0.6,
         "legend": [{"color": "#2ecc71", "label": "Kolay"}, {"color": "#f1c40f", "label": "Orta"},
                    {"color": "#e74c3c", "label": "Zor"}, {"color": "#280000", "label": f"Geçilmez (eğim >{SLOPE_MAX_DEG:.0f}° ya da skor >{SCORE_MAX})"}],
         "source": "0,4·eğim + 0,25·kum (eolyen birim) + 0,15·kaya (jeoloji vekili; YOLO E10'da) + 0,2·(1−termal)", **common},
    ]
    with open(OUT / "layers.json", "w", encoding="utf-8") as f:
        json.dump(layers, f, ensure_ascii=False, indent=2)
    print(f"  web/data/layers.json ({len(layers)} katman)")


def make_grid(G):
    cell_m = (BOUNDS["north"] - BOUNDS["south"]) * M_PER_DEG / N_GRID
    # Yürüme hızı (Tobler, PLAN.md §5): 6·exp(−3,5·|tanθ + 0,05|) km/sa × 0,6 (Mars + giysi), yük 0 kg.
    # Eğim yönsüz (ortalama büyüklük) kullanılıyor; yokuş yukarı/aşağı farkı walkback.js'te elev ile eklenebilir.
    tan = np.tan(np.radians(np.nan_to_num(G["slope"], nan=0)))
    v_m_min = 6 * np.exp(-3.5 * np.abs(tan + 0.05)) * 0.6 * 1000 / 60
    # Hücre maliyeti (dk) = hücre_boyu / v × (1 + 2·skor)
    cost = cell_m / v_m_min * (1 + 2 * G["score"])
    blocked = G["nodata"] | (G["slope"] > SLOPE_MAX_DEG) | (G["score"] > SCORE_MAX)
    cost = np.where(blocked, 999.0, cost)
    elev = np.where(np.isnan(G["elev"]), np.nanmean(G["elev"]), G["elev"])
    grid = {
        "width": N_GRID, "height": N_GRID, "bounds": BOUNDS, "cell_size_m": round(cell_m, 2),
        "order": "row-major; satır 0 = kuzey, sütun 0 = batı; indeks = satır*width + sütun",
        "units": {"elev": "m (Mars 2000 küresi/areoid, CTX DEM)", "cost": "dk/hücre, kenar yönünde (yük 0 kg, nabız 90); geçilmez = 999",
                  "blocked": "0/1"},
        "source": "prep_layers.py: CTX DEM + THEMIS TI + USGS SIM 3464",
        "elev": np.round(elev).astype(int).ravel().tolist(),
        "cost": np.round(cost, 2).ravel().tolist(),
        "blocked": blocked.astype(int).ravel().tolist(),
    }
    with open(OUT / "grid.json", "w", encoding="utf-8") as f:
        json.dump(grid, f, separators=(",", ":"))
    print(f"  web/data/grid.json  ({(OUT / 'grid.json').stat().st_size / 1024:.0f} KB), hücre {cell_m:.1f} m, "
          f"geçilmez %{blocked.mean() * 100:.1f}, maliyet medyan {np.median(cost[~blocked]):.2f} dk")
    return cost, blocked


def main():
    for d in (PROC, LAYERS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    crs = target_crs()
    print("Eğim (20 m) hesaplanıyor...")
    slope_tif = slope_native()
    print(f"Katmanlar {N_IMG}x{N_IMG}:")
    L = build(N_IMG, crs, slope_tif)
    make_pngs(L)
    make_layers_json(L)
    print(f"Grid {N_GRID}x{N_GRID}:")
    G = build(N_GRID, crs, slope_tif)
    cost, blocked = make_grid(G)
    np.savez_compressed(PROC / "layers_1024.npz", **{k: v for k, v in L.items() if isinstance(v, np.ndarray)})
    np.savez_compressed(PROC / "grid_256.npz", cost=cost, blocked=blocked,
                        **{k: v for k, v in G.items() if isinstance(v, np.ndarray)})
    stale = LAYERS_DIR / "hazard_ml.png"  # E1 sahte YOLO katmanı; gerçeği E10'da
    if stale.exists():
        stale.unlink()
    print("Bitti.")


if __name__ == "__main__":
    main()
