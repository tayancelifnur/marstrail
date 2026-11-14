"""
MarsTrail – veri hattı istatistikleri ve önce/sonra görselleri.

docs/DATA_PIPELINE.md'deki sayılar buradan gelir (elle yazılmaz).
Çıktı: docs/figures/pipeline_stats.json + docs/figures/*.png

Çalıştır:  venv\\Scripts\\python scripts\\pipeline_stats.py
"""
import json
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
from pyproj import CRS
from rasterio.warp import transform_bounds
from shapely.geometry import box

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402  (aynı sınırlar, katsayılar)

RAW = ROOT / "data" / "raw"
FIG = ROOT / "docs" / "figures"
BBOX = P.BBOX
stats = {}


def inside(lon, lat):
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


def mb(p):
    return round(p.stat().st_size / 1e6, 2)


def raster_window_mask(src):
    """Kaynak rasterde çalışma alanına düşen piksellerin maskesi."""
    l, b, r, t = transform_bounds(CRS(src.crs).geodetic_crs, src.crs, *BBOX)
    rows, cols = np.mgrid[0:src.height, 0:src.width]
    xs = src.transform.c + (cols + 0.5) * src.transform.a
    ys = src.transform.f + (rows + 0.5) * src.transform.e
    return (xs >= l) & (xs <= r) & (ys >= b) & (ys <= t), (l, b, r, t)


def d1_d3():
    w = json.load(open(RAW / "M20_waypoints.json", encoding="utf-8"))["features"]
    props = set().union(*(f["properties"].keys() for f in w))
    stats["D1"] = {"file_mb": mb(RAW / "M20_waypoints.json"), "features": len(w),
                   "inside_area": sum(inside(*f["geometry"]["coordinates"][:2]) for f in w),
                   "fields_total": len(props), "fields_used": ["sol", "lon", "lat", "elev_geoid"],
                   "sol_range": [w[0]["properties"]["sol"], w[-1]["properties"]["sol"]]}
    t = json.load(open(RAW / "M20_traverse.json", encoding="utf-8"))["features"]
    pts = [p for f in t for p in f["geometry"]["coordinates"]]
    stats["D2"] = {"file_mb": mb(RAW / "M20_traverse.json"), "features": len(t), "vertices": len(pts),
                   "vertices_inside": sum(inside(p[0], p[1]) for p in pts),
                   "length_km": round(sum(f["properties"].get("length", 0) for f in t) / 1000, 1)}
    h = json.load(open(RAW / "m20_heli_flight_path.json", encoding="utf-8"))["features"]
    stats["D3"] = {"file_mb": mb(RAW / "m20_heli_flight_path.json"), "features": len(h),
                   "inside_area": sum(inside(*f["geometry"]["coordinates"][0][:2]) for f in h)}


def d4():
    with rasterio.open(P.THERMAL) as src:
        a = src.read(1)
        m, _ = raster_window_mask(src)
    nod = a == 0
    vals = a[m & ~nod]
    lo, hi = np.percentile(vals, [2, 98])
    stats["D4"] = {"file_mb": mb(P.THERMAL), "pixels": int(a.size), "nodata": int(nod.sum()),
                   "inside_area": int(m.sum()), "inside_nodata": int((m & nod).sum()),
                   "dropped_outside": int(a.size - m.sum()),
                   "ti_min": float(vals.min()), "ti_max": float(vals.max()),
                   "p2": float(lo), "p98": float(hi),
                   "clipped_low": int((vals < lo).sum()), "clipped_high": int((vals > hi).sum())}
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].hist(vals, bins=80, color="#e67e22")
    ax[0].axvline(lo, color="k", ls="--"), ax[0].axvline(hi, color="k", ls="--")
    ax[0].set_title(f"Önce: ham termal eylemsizlik (TIU), alan içi {vals.size} piksel")
    ax[0].set_xlabel("TIU  (kesikli: %2 ve %98)")
    norm = np.clip((vals - lo) / (hi - lo), 0, 1)
    ax[1].hist(norm, bins=80, color="#34495e")
    ax[1].set_title("Sonra: termal_norm = clip((TI − p2) / (p98 − p2), 0, 1)")
    fig.tight_layout(), fig.savefig(FIG / "d4_thermal_normalize.png", dpi=110), plt.close(fig)


def d5():
    with rasterio.open(P.DEM) as src:
        a = src.read(1)
        m, (l, b, r, t) = raster_window_mask(src)
        ext = (src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top)
    nod = (a < -9000) | (a > 30000)
    with rasterio.open(P.PROC / "slope_20m.tif") as s:
        sl = s.read(1)
    inside_valid = m & ~nod
    stats["D5"] = {"file_mb": mb(P.DEM), "pixels": int(a.size), "nodata": int(nod.sum()),
                   "inside_area": int(m.sum()), "inside_nodata": int((m & nod).sum()),
                   "dropped_outside": int(a.size - m.sum()),
                   "elev_min": float(a[inside_valid].min()), "elev_max": float(a[inside_valid].max()),
                   "slope_gt25_20m": int((sl[inside_valid] > 25).sum())}
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.2))
    show = np.where(nod, np.nan, a)[::8, ::8]
    ax[0].imshow(show, cmap="terrain", extent=ext)
    ax[0].imshow(np.where(nod[::8, ::8], 1, np.nan), cmap="spring", extent=ext, vmin=0, vmax=1)
    ax[0].add_patch(plt.Rectangle((l, b), r - l, t - b, fill=False, ec="red", lw=2))
    ax[0].set_title(f"Önce: CTX DEM 20 m, {a.shape[1]}×{a.shape[0]}\npembe = NoData ({nod.sum():,} px), kırmızı = çalışma alanı")
    ax[0].set_xticks([]), ax[0].set_yticks([])
    ax[1].imshow(plt.imread(ROOT / "web/data/layers/hillshade.png"))
    ax[1].set_title("Sonra: kırpıldı, Mars 2000 coğrafi, 1024² gölgeli kabartma")
    ax[1].set_xticks([]), ax[1].set_yticks([])
    fig.tight_layout(), fig.savefig(FIG / "d5_dem_crop.png", dpi=110), plt.close(fig)


def d6():
    z = zipfile.ZipFile(RAW / "sim3464_database.zip").namelist()
    gdb = RAW / "D6_geology" / "Nili.gdb"
    import pyogrio
    layers = [n for n, _ in pyogrio.list_layers(gdb)]
    g = gpd.read_file(RAW / "D6_geology" / "Jezero_GeoUnits.shp")
    typo = int((g["name"] == "Crater riim unit").sum())
    mislabeled = int(((g["unit"].astype(str) == "5") & (g["name"] == "Upper etched unit")).sum())
    area = gpd.GeoSeries([box(*BBOX)], crs=P.target_crs()).to_crs(g.crs).iloc[0]
    hit = g[g.intersects(area)]
    clipped = hit.copy()
    clipped["geometry"] = hit.intersection(area)
    clipped["name"] = clipped["name"].replace(P.GEO_FIX)
    by_unit = (clipped.assign(km2=clipped.area / 1e6).groupby("name")["km2"].sum().sort_values(ascending=False))
    stats["D6"] = {"zip_mb": mb(RAW / "sim3464_database.zip"), "zip_files": len(z),
                   "zip_dropped_macosx_lock": sum(1 for n in z if "__MACOSX" in n or n.endswith((".lock", ".DS_Store"))),
                   "gdb_layers": layers, "layers_used": ["GeoUnits_v1"],
                   "polygons": len(g), "units": int(g["name"].replace(P.GEO_FIX).nunique()),
                   "typo_fixed": typo, "unit_code_mismatch": mislabeled,
                   "polygons_in_area": len(hit), "polygons_dropped_outside": len(g) - len(hit),
                   "unit_km2_in_area": {k: round(v, 2) for k, v in by_unit.items()}}
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.2))
    g.plot(ax=ax[0], column="name", cmap="tab20", linewidth=0)
    gpd.GeoSeries([area], crs=g.crs).boundary.plot(ax=ax[0], color="red", lw=2)
    ax[0].set_title(f"Önce: SIM 3464, {len(g)} poligon, 14 birim\nkırmızı = çalışma alanı")
    ax[0].set_axis_off()
    ax[1].imshow(plt.imread(ROOT / "web/data/layers/geology.png"))
    ax[1].set_title(f"Sonra: {len(hit)} poligon kırpıldı, 1024² ızgaraya rasterize")
    ax[1].set_axis_off()
    fig.tight_layout(), fig.savefig(FIG / "d6_geology_crop.png", dpi=110), plt.close(fig)


def fusion():
    L = np.load(P.PROC / "layers_1024.npz")
    G = np.load(P.PROC / "grid_256.npz")
    slope_risk = np.clip(L["slope"] / P.SLOPE_MAX_DEG, 0, 1)
    rock = np.where(np.isnan(L["rock"]), 0.3, L["rock"])
    th = np.where(np.isnan(L["thermal"]), 0.5, L["thermal"])
    panels = [("0,4 · eğim/25°", slope_risk), ("0,25 · kum (eolyen)", L["sand"]),
              ("0,15 · kaya (jeoloji vekili)", rock), ("0,2 · (1 − termal_norm)", 1 - th), ("= skor", L["score"])]
    fig, ax = plt.subplots(1, 5, figsize=(17, 3.8))
    for a, (t, v) in zip(ax, panels):
        a.imshow(v, cmap="RdYlGn_r", vmin=0, vmax=1), a.set_title(t), a.set_axis_off()
    fig.tight_layout(), fig.savefig(FIG / "fusion.png", dpi=100), plt.close(fig)
    blk = G["blocked"]
    stats["grid"] = {"cells": int(blk.size), "blocked": int(blk.sum()), "nodata": int(G["nodata"].sum()),
                     "blocked_slope": int((G["slope"] > P.SLOPE_MAX_DEG).sum()),
                     "blocked_score": int((G["score"] > P.SCORE_MAX).sum()),
                     "cell_m": round((P.BOUNDS["north"] - P.BOUNDS["south"]) * P.M_PER_DEG / 256, 1),
                     "score_mean": round(float(np.nanmean(G["score"])), 3)}


def d8():
    p = RAW / "MSR_TRN_HiRISE_mosaics.zip"
    stats["D8"] = {"zip_mb": mb(p) if p.exists() else None, "status": "indi" if p.exists() else "iniyor"}


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (d1_d3, d4, d5, d6, fusion, d8):
        f()
    (FIG / "pipeline_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
