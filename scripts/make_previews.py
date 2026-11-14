"""
MarsTrail – veri seti önizlemeleri: her veri seti (D1–D8) için ham ve işlenmiş hal yan yana.

Çıktı: docs/figures/onizleme/d1.png … d8.png  (docs/veri_envanteri.md'de gösteriliyor)
Çalıştır:  venv\\Scripts\\python scripts\\make_previews.py
Gerekenler: data/raw (E2), web/data (E3, E7), ml/roboflow_upload (E5). D7 için internet (API'den 12 küçük görüntü).
"""
import csv
import json
import sys
from io import BytesIO
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
import requests
from PIL import Image
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402

RAW = ROOT / "data/raw"
WEB = ROOT / "web/data"
OUT = ROOT / "docs/figures/onizleme"
STATS = json.loads((ROOT / "docs/figures/pipeline_stats.json").read_text(encoding="utf-8"))
E5 = json.loads((ROOT / "docs/figures/e5_stats.json").read_text(encoding="utf-8"))
E7 = json.loads((ROOT / "docs/figures/e7_stats.json").read_text(encoding="utf-8"))
EXT = [P.BBOX[0], P.BBOX[2], P.BBOX[1], P.BBOX[3]]  # imshow extent (lon/lat)
HS = np.asarray(Image.open(WEB / "layers/hillshade.png").convert("L"))
REGIONS = json.loads((WEB / "regions.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "MarsTrail (NASA Space Apps)"}


def fig2(title, left_title, right_title, w=14, h=6.4):
    fig, ax = plt.subplots(1, 2, figsize=(w, h))
    fig.suptitle(title, fontsize=14, fontweight="bold")
    ax[0].set_title("HAM · " + left_title, fontsize=10, loc="left")
    ax[1].set_title("İŞLENMİŞ · " + right_title, fontsize=10, loc="left")
    return fig, ax


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=90, bbox_inches="tight")  # alttaki lejantlar kesilmesin
    plt.close(fig)
    print("  docs/figures/onizleme/" + name)


def bbox_rect(ax, **kw):
    w, s, e, n = P.BBOX
    ax.add_patch(plt.Rectangle((w, s), e - w, n - s, fill=False, ec=kw.get("ec", "red"), lw=2, label="çalışma alanı"))


def hillshade(ax):
    ax.imshow(HS, cmap="gray", extent=EXT, vmin=0, vmax=255)
    ax.set_xlim(EXT[0], EXT[1]), ax.set_ylim(EXT[2], EXT[3])
    ax.set_xlabel("boylam °D"), ax.set_ylabel("enlem °K")


def pins(ax, size=30):
    for r in REGIONS:
        if P.BBOX[0] <= r["lon"] <= P.BBOX[2] and P.BBOX[1] <= r["lat"] <= P.BBOX[3]:
            ax.scatter(r["lon"], r["lat"], s=size, c="#00e5ff", edgecolors="k", zorder=5)
            ax.annotate(r["id"], (r["lon"], r["lat"]), xytext=(4, 4), textcoords="offset points", color="#00e5ff",
                        fontsize=8, fontweight="bold")


def lines_of(geojson):
    for f in geojson["features"]:
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for p in parts:
            a = np.array([c[:2] for c in p])
            yield f["properties"], a


def d1():
    w = json.load(open(RAW / "M20_waypoints.json", encoding="utf-8"))["features"]
    lon = [f["properties"]["lon"] for f in w]
    lat = [f["properties"]["lat"] for f in w]
    sol = [f["properties"]["sol"] for f in w]
    s = STATS["D1"]
    fig, ax = fig2("D1 · Perseverance konumları (M20_waypoints.json)",
                   f"{s['features']} nokta × {s['fields_total']} alan, Sol {s['sol_range'][0]}–{s['sol_range'][1]}",
                   "Sol ≤ olay Sol'ü olan son kayıt → nokta kartı konumu")
    sc = ax[0].scatter(lon, lat, c=sol, s=6, cmap="viridis")
    fig.colorbar(sc, ax=ax[0], label="Sol")
    bbox_rect(ax[0])
    ax[0].legend(loc="lower right"), ax[0].set_aspect(1 / np.cos(np.radians(18.45)))
    ax[0].set_xlabel("boylam °D"), ax[0].set_ylabel("enlem °K")
    hillshade(ax[1])
    inside = [(a, b) for a, b in zip(lon, lat) if P.BBOX[0] <= a <= P.BBOX[2] and P.BBOX[1] <= b <= P.BBOX[3]]
    ax[1].scatter(*zip(*inside), s=2, c="#ffcc00", alpha=0.5, label=f"alan içi {len(inside)} nokta")
    pins(ax[1], 50)
    ax[1].legend(loc="lower right")
    save(fig, "d1.png")


def d2():
    t = json.load(open(RAW / "M20_traverse.json", encoding="utf-8"))
    s = STATS["D2"]
    fig, ax = fig2("D2 · Perseverance sürüş izi (M20_traverse.json)",
                   f"{s['features']} sürüş, {s['vertices']:,} köşe, {s['length_km']} km",
                   "Alan içi köşeler → 256² grid hücresi (doğrulama, E10)")
    cmap = plt.get_cmap("plasma")
    for props, a in lines_of(t):
        ax[0].plot(a[:, 0], a[:, 1], color=cmap(props.get("sol", 0) / 2100), lw=1)
    bbox_rect(ax[0]), ax[0].legend(loc="lower right")
    ax[0].set_aspect(1 / np.cos(np.radians(18.45))), ax[0].set_xlabel("boylam °D"), ax[0].set_ylabel("enlem °K")
    g = json.load(open(WEB / "grid.json"))
    n, B = g["width"], g["bounds"]
    blocked = np.array(g["blocked"]).reshape(n, n)
    cells = np.zeros((n, n), bool)
    for _, a in lines_of(t):
        for x, y in a:
            r = int((B["north"] - y) / (B["north"] - B["south"]) * n)
            c = int((x - B["west"]) / (B["east"] - B["west"]) * n)
            if 0 <= r < n and 0 <= c < n:
                cells[r, c] = True
    hillshade(ax[1])
    ov = np.zeros((n, n, 4))
    ov[blocked == 1] = (0.6, 0, 0, 0.9)
    ov[cells] = (0, 0.9, 1, 1)
    ax[1].imshow(ov, extent=EXT, interpolation="nearest")
    ok = (~blocked.astype(bool) & cells).sum()
    ax[1].plot([], [], color="#00e5ff", lw=4, label=f"rover hücresi: {cells.sum()} ({ok / cells.sum() * 100:.0f}% geçilebilir)")
    ax[1].plot([], [], color="#990000", lw=4, label=f"geçilmez hücre: {blocked.sum()}")
    ax[1].legend(loc="lower right")
    save(fig, "d2.png")


def d3():
    h = json.load(open(RAW / "m20_heli_flight_path.json", encoding="utf-8"))
    fig, ax = fig2("D3 · Ingenuity uçuşları (m20_heli_flight_path.json)",
                   f"{len(h['features'])} uçuş (Sol 58 – 1036)", "Uçuş 1 kalkış noktası → tarih pini (airfield)")
    cmap = plt.get_cmap("cool")
    for props, a in lines_of(h):
        ax[0].plot(a[:, 0], a[:, 1], color=cmap(props["Flight"] / 72), lw=1.2)
    bbox_rect(ax[0]), ax[0].legend(loc="lower right")
    ax[0].set_aspect(1 / np.cos(np.radians(18.45))), ax[0].set_xlabel("boylam °D"), ax[0].set_ylabel("enlem °K")
    hillshade(ax[1])
    for props, a in lines_of(h):
        ax[1].plot(a[:, 0], a[:, 1], color="#ff66ff", lw=0.6, alpha=0.5)
    pins(ax[1], 50)
    ax[1].plot([], [], color="#ff66ff", label="72 uçuşun izi (E13 İHA senaryosu için)")
    ax[1].legend(loc="lower right")
    save(fig, "d3.png")


def raster_full(path, step, nodata_fn):
    with rasterio.open(path) as src:
        a = src.read(1, out_shape=(src.height // step, src.width // step), resampling=Resampling.nearest).astype(np.float32)
        geo = CRS(src.crs).geodetic_crs
        ext = transform_bounds(src.crs, geo, *src.bounds)
    a[nodata_fn(a)] = np.nan
    return a, [ext[0], ext[2], ext[1], ext[3]]


def d4():
    a, ext = raster_full(RAW / "Jezero_Thermal_Inertia_v1.tiff", 1, lambda x: x == 0)
    s = STATS["D4"]
    fig, ax = fig2("D4 · THEMIS termal eylemsizlik (Jezero mozaiği)",
                   f"890×890 px, 100 m; NoData {s['nodata']:,} px (gri); TI {np.nanmin(a):.0f}–{np.nanmax(a):.0f} TIU",
                   f"Kırpıldı, %2–98 ({s['p2']:.0f}–{s['p98']:.0f} TIU) → 0–1, 1024²")
    ax[0].set_facecolor("#888")
    lo, hi = np.nanpercentile(a, [1, 99])  # birkaç aykırı piksel ölçeği ezmesin (yalnız gösterim)
    im = ax[0].imshow(a, cmap="inferno", extent=ext, vmin=lo, vmax=hi)
    fig.colorbar(im, ax=ax[0], label="TIU (renk %1–99)")
    bbox_rect(ax[0], ec="#00e5ff"), ax[0].legend(loc="lower right")
    hillshade(ax[1])
    ax[1].imshow(Image.open(WEB / "layers/thermal.png"), extent=EXT, alpha=0.85)
    pins(ax[1])
    save(fig, "d4.png")


def d5():
    a, ext = raster_full(P.DEM, 8, lambda x: (x < -9000) | (x > 30000))
    s = STATS["D5"]
    fig, ax = fig2("D5 · CTX sayısal yükseklik modeli (20 m)",
                   f"4456×5067 px; NoData {s['nodata']:,} px; yükseklik {np.nanmin(a):.0f} … {np.nanmax(a):.0f} m",
                   "Kırpıldı, 20 m'de eğim → gölgeli kabartma + eğim (≥25° kırmızı)")
    im = ax[0].imshow(a, cmap="terrain", extent=ext)
    fig.colorbar(im, ax=ax[0], label="m")
    bbox_rect(ax[0]), ax[0].legend(loc="lower right")
    hillshade(ax[1])
    ax[1].imshow(Image.open(WEB / "layers/slope.png"), extent=EXT, alpha=0.55)
    pins(ax[1])
    save(fig, "d5.png")


def d6():
    g = gpd.read_file(RAW / "D6_geology/Jezero_GeoUnits.shp")
    s = STATS["D6"]
    fig, ax = fig2("D6 · USGS SIM 3464 jeoloji haritası",
                   f"{s['polygons']} poligon, {s['units']} birim, 13 katmanlı GDB",
                   f"{s['polygons_in_area']} poligon kırpıldı, yazım hatası düzeltildi, 1024² raster", h=8.2)
    g.to_crs(P.target_crs()).plot(ax=ax[0], column="name", cmap="tab20", linewidth=0, legend=True,
                                  legend_kwds={"loc": "upper left", "bbox_to_anchor": (0, -0.1), "ncol": 3,
                                               "fontsize": 7, "title": "Kaynaktaki birimler (\"Crater riim\" = yazım hatası)"})
    bbox_rect(ax[0])
    ax[0].set_xlabel("boylam °D"), ax[0].set_ylabel("enlem °K")
    hillshade(ax[1])
    ax[1].imshow(Image.open(WEB / "layers/geology.png"), extent=EXT, alpha=0.8)
    pins(ax[1])
    save(fig, "d6.png")


def d7():
    sol = 415
    ims = requests.get(f"https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&sol={sol}",
                       headers=UA, timeout=90).json()["images"]
    pick = [ims[i] for i in np.linspace(0, len(ims) - 1, 12).astype(int)]
    fig = plt.figure(figsize=(16, 6.6))
    fig.suptitle("D7 · Perseverance ham görüntüleri (API)", fontsize=14, fontweight="bold")
    gs = fig.add_gridspec(3, 9, wspace=0.05, hspace=0.25)
    fig.text(0.13, 0.90, f"HAM · Sol {sol}: API'den {len(ims)} kayıt; eşit aralıklı 12 örnek\n"
             "(alt kare, gökyüzü, rover, stereo ikizler dahil)", fontsize=10)
    for k, im in enumerate(pick):
        a = fig.add_subplot(gs[k // 4, k % 4])
        a.imshow(Image.open(BytesIO(requests.get(im["image_files"]["small"], headers=UA, timeout=60).content)).convert("RGB"))
        a.set_title(f"{im['camera']['instrument'][:12]} {im['extended'].get('dimension', '')}", fontsize=6)
        a.set_axis_off()
    funnel = E7["per_region"]
    tot = sum(v.get("api_images", 0) for k, v in funnel.items() if not k.endswith("_tried"))
    tot += sum(x.get("api_images", 0) for k, v in funnel.items() if k.endswith("_tried") for x in v)
    fig.text(0.53, 0.90, f"İŞLENMİŞ · 7 Sol, {tot} kayıt → {E7['photos']} fotoğraf\n"
             "kamera, boyut, renkli/gri ikiz, direk açısı, doku eşiği, insan kontrolü", fontsize=10)
    photos = [(r["id"], p) for r in REGIONS for p in r["photos"]]
    for k, (rid, p) in enumerate(photos[:15]):
        a = fig.add_subplot(gs[k // 5, 4 + k % 5])
        a.imshow(Image.open(WEB / p["url"]).convert("RGB"))
        a.set_title(f"{rid} · {p['camera']} Sol {p['sol']}", fontsize=6)
        a.set_axis_off()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "d7.png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("  docs/figures/onizleme/d7.png")


def d8():
    ortho = RAW / "D8_hirise/MSR_hirise_soc_003_Orthomosaic_0.25m_Eqc_latTs0_lon0_First_NoBlend.tif"
    a, ext = raster_full(ortho, 64, lambda x: x == 0)
    sc = E5["screen"]
    fig = plt.figure(figsize=(15, 7.2))
    fig.suptitle("D8 · HiRISE ortogörüntü mozaiği (25 cm)", fontsize=14, fontweight="bold")
    gs = fig.add_gridspec(3, 6, wspace=0.05, hspace=0.2)
    a0 = fig.add_subplot(gs[:, :3])
    a0.imshow(a, cmap="gray", extent=ext, vmin=sc["stretch_p0_5"], vmax=sc["stretch_p99_5"])
    bbox_rect(a0)
    rows = list(csv.DictReader(open(ROOT / "ml/tiles_manifest.csv", encoding="utf-8")))
    col = {"kum_adayi": "#f1c40f", "kaya_adayi": "#e74c3c", "negatif": "#3498db"}
    for r in rows:
        a0.add_patch(plt.Rectangle((float(r["west"]), float(r["south"])), float(r["east"]) - float(r["west"]),
                                   float(r["north"]) - float(r["south"]), color=col[r["category"]], lw=0))
    a0.legend(handles=[plt.Line2D([], [], color="red", lw=2, label="çalışma alanı")]
              + [plt.Line2D([], [], color=v, lw=6, label=k) for k, v in col.items()], loc="lower right", fontsize=8)
    a0.set_title("HAM · 76.576×107.264 px, 4,7 GB (1/64 önizleme)\nseçilen karolar renkli", fontsize=10, loc="left")
    a0.set_xlabel("boylam °D"), a0.set_ylabel("enlem °K")
    samp = [r for cat in ("kum_adayi", "kaya_adayi", "negatif") for r in [x for x in rows if x["category"] == cat][3:6]]
    for k, r in enumerate(samp):
        ax = fig.add_subplot(gs[k // 3, 3 + k % 3])
        ax.imshow(Image.open(ROOT / "ml/roboflow_upload" / r["file"]), cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"{r['category']} · {r['file']}", fontsize=7)
        ax.set_axis_off()
    fig.text(0.50, 0.90, f"İŞLENMİŞ · {sc['tiles_total']} karo → NoData −{sc['dropped_nodata']}, dokusuz −{sc['dropped_flat']}\n"
             f"→ {E5['selected']['total']} karo (640², 160 m), %0,5–99,5 germe", fontsize=10)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "d8.png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("  docs/figures/onizleme/d8.png")


if __name__ == "__main__":
    for f in (d1, d2, d3, d4, d5, d6, d7, d8):
        f()
