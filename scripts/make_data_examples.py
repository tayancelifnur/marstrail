"""
MarsTrail – veri örnekleri sayfası: docs/VERI_ORNEKLERI.html (tek dosya, görseller base64 gömülü).

Jüriye her veri setinin ham halini göstermek için: tüm alanlar ve gerçek ilk 5 satır (kullanılan alanlar yeşil,
kullanılmayanlar gri, her biri için neden), rasterlerde ham önizleme ile işlenmiş hal yan yana, önce/sonra
histogram, NoData oranı ve min/maks/ortalama. Sayıların hepsi bu betik çalışırken dosyalardan ölçülür ya da
diğer betiklerin JSON çıktılarından okunur (pipeline_stats, e5_stats, e7_stats, e10_*). Bulunamayan değer "yok".

Çalıştır:  venv\\Scripts\\python scripts\\make_data_examples.py
Gerekenler: data/raw/ (D1–D6, D8), data/processed/layers_1024.npz (prep_layers.py), ml/dataset_merged (merge_v2.py),
            internet (D7 için Perseverance ham görüntü API'si, Mars Trek karoları).
Not: HiRISE önizlemesi (~1 GB okuma) ilk çalıştırmada data/processed/d8_preview_dec16.npz olarak saklanır.
"""
import base64
import csv
import html
import io
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
import requests
from PIL import Image, ImageDraw
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_regions as BR  # noqa: E402
import download_data as DL  # noqa: E402
import prep_layers as P  # noqa: E402
import tile_for_yolo as T  # noqa: E402

RAW, PROC, FIG = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "docs" / "figures"
OUT = ROOT / "docs" / "VERI_ORNEKLERI.html"
UA = {"User-Agent": "MarsTrail (NASA Space Apps)"}
D7_SOL = 415   # örnek Sol: delta önü (nokta kartı Sol'ü); ilk 5 kayıt bu Sol'ün API cevabından
TREK = "https://trek.nasa.gov/tiles/Mars/EQ/"
TREK_LAYERS = {   # web/app.js'teki katmanlarla aynı
    "viking": ("Viking renkli mozaik (232 m)", "Mars_Viking_MDIM21_ClrMosaic_global_232m", "jpg", 5),
    "ctx": ("CTX Jezero mozaiği (6 m)", "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0", "png", 10),
    "hirise": ("HiRISE Jezero mozaiği (25 cm)", "JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd", "png", 13),
}

# ---- Tema (koyu; slaytlarla aynı renkler) ----------------------------------------------------
BG, SURF, INK, MUTED, GRID, ACC = "#0d0b0a", "#17130f", "#f2ebe4", "#a89c90", "#2c2620", "#ff7a2f"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "text.color": INK,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID,
    "axes.titlecolor": INK, "axes.titlesize": 10.5, "font.size": 9, "axes.grid": False,
    "font.family": "DejaVu Sans",
})

STATS = json.load(open(FIG / "pipeline_stats.json", encoding="utf-8"))
E5 = json.load(open(FIG / "e5_stats.json", encoding="utf-8"))
E7 = json.load(open(FIG / "e7_stats.json", encoding="utf-8"))
E10V = json.load(open(FIG / "e10_validation.json", encoding="utf-8"))
E10I = json.load(open(FIG / "e10_infer_stats.json", encoding="utf-8"))
E6S = json.load(open(FIG / "e6v2_split.json", encoding="utf-8"))


# ---- Yardımcılar ----------------------------------------------------------------------------
def tr(x, d=0):
    """Türkçe sayı: binlik nokta, ondalık virgül."""
    if x is None:
        return "yok"
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def mb(p):
    return p.stat().st_size / 1e6


def size_txt(p):
    n = p.stat().st_size
    return f"{tr(n / 1e9, 2)} GB" if n >= 1e9 else f"{tr(n / 1e6, 1)} MB" if n >= 1e5 else f"{tr(n / 1e3, 1)} KB"


def uri_fig(fig, dpi=100):
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def uri_img(img, fmt="JPEG", q=82):
    b = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(b, format="JPEG", quality=q, optimize=True)
    else:
        img.save(b, format="PNG", optimize=True)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(b.getvalue()).decode()


esc = html.escape


def cell_txt(v, n=48):
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    s = "" if v is None else str(v)
    if s == "nan":
        s = "NaN"
    return esc(s if len(s) <= n else s[: n - 1] + "…"), esc(s)


def table(cols, rows, used):
    """Tüm sütunlar; kullanılanlar yeşil, kullanılmayanlar gri."""
    h = ['<div class="tw"><table class="data"><thead><tr>']
    for c in cols:
        h.append(f'<th class="{"u" if c in used else "n"}">{esc(c)}</th>')
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>")
        for c, v in zip(cols, r):
            short, full = cell_txt(v)
            h.append(f'<td class="{"u" if c in used else "n"}" title="{full}">{short}</td>')
        h.append("</tr>")
    h.append("</tbody></table></div>")
    return "".join(h)


def field_notes(cols, used, reasons):
    """Her alan için tek satır: kullanılan → nasıl (dosya/fonksiyon), kullanılmayan → neden."""
    u = [f'<li><code class="u">{esc(c)}</code> {used[c]}</li>' for c in cols if c in used]
    n = [f'<li><code class="n">{esc(c)}</code> {reasons[c]}</li>' for c in cols if c not in used]
    missing = [c for c in cols if c not in used and c not in reasons]
    assert not missing, f"gerekçesi yazılmamış alan: {missing}"
    return (f'<div class="notes"><div><h4>Kullandıklarımız: nasıl</h4><ul>{"".join(u)}</ul></div>'
            f'<div><h4>Kullanmadıklarımız: neden</h4><ul>{"".join(n)}</ul></div></div>')


def facts(d):
    items = "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in d.items())
    return f'<dl class="facts">{items}</dl>'


def link(u):
    return f'<a href="{esc(u)}">{esc(u)}</a>'


def stat_row(name, a):
    a = np.asarray(a, dtype=np.float64)
    return f"<tr><td>{name}</td><td>{tr(np.min(a), 2)}</td><td>{tr(np.max(a), 2)}</td><td>{tr(np.mean(a), 2)}</td><td>{tr(a.size)}</td></tr>"


def stat_table(rows, nodata_txt):
    return (f'<div class="tw"><table class="stat"><thead><tr><th></th><th>min</th><th>maks</th><th>ortalama</th>'
            f'<th>piksel</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="nod"><b>NoData oranı:</b> {nodata_txt}</p>')


def hist_pair(a, b, ta, tb, xa, xb, lines_a=(), lines_b=(), bins=60):
    """Önce/sonra histogramı: iki ayrı panel (birimler farklı; ortak eksen yok), tek renk, sade eksen."""
    fig, ax = plt.subplots(1, 2, figsize=(10, 2.9))
    for k, (v, t, xl, lines) in enumerate(((a, ta, xa, lines_a), (b, tb, xb, lines_b))):
        v = np.asarray(v).ravel()
        v = v[np.isfinite(v)]
        if v.size > 2_000_000:
            v = np.random.default_rng(0).choice(v, 2_000_000, replace=False)
        ax[k].hist(v, bins=bins, color=ACC, edgecolor=SURF, linewidth=0.6)
        for x, lab in lines:
            ax[k].axvline(x, color=INK, lw=1, ls="--")
            ax[k].text(x, ax[k].get_ylim()[1] * 0.92, " " + lab, color=INK, fontsize=8, va="top")
        ax[k].set_title(t, loc="left")
        ax[k].set_xlabel(xl)
        ax[k].set_ylabel("piksel sayısı")
        ax[k].grid(axis="y", color=GRID, lw=0.6)
        ax[k].set_axisbelow(True)
        for s in ("top", "right"):
            ax[k].spines[s].set_visible(False)
    fig.tight_layout()
    return uri_fig(fig)


def bbox_line(crs):
    """Çalışma alanı dikdörtgeni, kaynak projeksiyonda (sıklaştırılmış çizgi)."""
    W, S, E, N = P.BBOX
    xs = list(np.linspace(W, E, 30)) + [E] * 30 + list(np.linspace(E, W, 30)) + [W] * 30
    ys = [N] * 30 + list(np.linspace(N, S, 30)) + [S] * 30 + list(np.linspace(S, N, 30))
    return warp_transform(P.target_crs(), crs, xs, ys)


def tile_bbox_line(crs):
    W, S, E, N = T.TILE_BBOX
    xs = [W, E, E, W, W]
    ys = [N, N, S, S, N]
    return warp_transform(P.target_crs(), crs, xs, ys)


def crs_name(crs):
    w = crs.to_wkt()
    return w.split('"')[1] if '"' in w else str(crs)


def section(sid, title, head, body, dropped, cleaning, where, summary):
    return (f'<section id="{sid}"><h2>{title}</h2>{head}{body}'
            f'<div class="rows"><p><b>Ne attık:</b> {dropped}</p><p><b>Temizleme / normalizasyon:</b> {cleaning}</p>'
            f'<p><b>Projede nerede:</b> {where}</p></div><p class="sum">{summary}</p></section>')


def geom_txt(g):
    t = g["type"]
    c = g["coordinates"]
    if t == "Point":
        return f"Point ({c[0]:.5f}, {c[1]:.5f})"
    if t == "LineString":
        return f"LineString, {len(c)} köşe"
    if t == "MultiLineString":
        return f"MultiLineString, {sum(len(x) for x in c)} köşe"
    return t


# ---- D1–D3: GeoJSON -------------------------------------------------------------------------
def geojson_section(did):
    name = {"D1": "M20_waypoints.json", "D2": "M20_traverse.json", "D3": "m20_heli_flight_path.json"}[did]
    url = DL.SOURCES[did][1]
    d = json.load(open(RAW / name, encoding="utf-8"))
    fe = d["features"]
    props = list(fe[0]["properties"].keys())
    cols = props + ["geometry"]
    rows = [[f["properties"].get(c) for c in props] + [geom_txt(f["geometry"])] for f in fe[:5]]
    crs = d.get("crs", {}).get("properties", {}).get("name", "dosyada belirtilmemiş (derece, doğu pozitif)")
    s = STATS[did]
    if did == "D1":
        n_pins = sum(1 for r in BR.REGIONS if r["pos"][0] == "sol")
        final = sum(1 for f in fe if f["properties"].get("final") == "y")
        used = {
            "sol": "<code>build_regions.load_waypoints</code> → <code>position()</code>: olayın Sol'üne eşit ya da önceki son kayıt. "
                   f"{n_pins} pin (üs, Rochette, delta önü, Three Forks, Cheyava Falls) böyle konumlandı.",
            "lon": "Pin boylamı (<code>build_regions.position</code>); <code>pipeline_stats.d1_d3</code> alan içi sayımı.",
            "lat": "Pin enlemi; aynı yerler.",
            "elev_geoid": "Yalnızca veri hattı kontrolünde okundu (DATA_PIPELINE E7: delta önünde −2545 → −2520 m tırmanış). "
                          "Uygulamadaki nokta yüksekliği D5 DEM'den gelir.",
        }
        reasons = {
            "RMC": "Rover hareket sayacı (site_drive); konum için gerekmiyor.",
            "site": "RMC'nin ilk parçası; aynı neden.", "drive": "RMC'nin ikinci parçası; aynı neden.",
            "easting": "Projeksiyonlu metre koordinatı; ortak sistemimiz derece, lon/lat yeterli.",
            "northing": "Aynı neden (easting ile çift).",
            "elev_radii": "Farklı referansa göre yükseklik; yükseklik D5 DEM'den.",
            "radius": "Merkezden uzaklık; aynı neden.",
            "roll": "Rover gövdesinin yatışı; astronot rotasıyla ilgisi yok.", "pitch": "Gövde eğimi; aynı neden.",
            "yaw": "Gövde yönü; aynı neden.", "yaw_rad": "yaw'ın radyanı; aynı neden.", "tilt": "Toplam gövde eğikliği; aynı neden.",
            "dist_m": "Son sürüşün mesafesi; sürüş izi D2'den geliyor.", "dist_total_m": "Toplam sürüş; aynı neden.",
            "dist_km": "Aynı bilgi km cinsinden.", "dist_mi": "Aynı bilgi mil cinsinden.",
            "final": f"Kaydın kesinleşme işareti ({tr(final)}/{tr(len(fe))} kayıt 'y'); konuma etkisi yok.",
            "Note": "Serbest metin. Kodda okunmuyor; Sol 13 \"no motion\" kaydının iniş noktası olduğunu doğrulamak için elle okundu.",
            "images": "Panorama bağlantıları; nokta fotoğrafları D7 API'sinden seçildi.",
            "geometry": "lon/lat alanlarıyla aynı nokta; özellik alanları kullanıldı.",
        }
        head = facts({"Ad": "D1 · Perseverance konumları (waypoints)", "Kaynak": link(url), "Format": "GeoJSON (FeatureCollection, Point)",
                      "Boyut": size_txt(RAW / name), "Kayıt": f"{tr(len(fe))} nokta × {tr(len(props))} alan, Sol {s['sol_range'][0]}–{s['sol_range'][1]}",
                      "Çözünürlük": "yok (nokta verisi)", "Projeksiyon": esc(crs)})
        dropped = (f"{tr(len(props))} alanın {tr(len(props) - len(used))}'i (duruş, sayaçlar, mesafeler, bağlantılar). Kayıt atılmadı: "
                   f"{tr(s['inside_area'])} nokta çalışma alanında, kalan {tr(s['features'] - s['inside_area'])} nokta Sol araması için tutuldu.")
        clean = "Sol'e göre sıralama; eşleme kuralı <code>Sol(kayıt) ≤ Sol(olay)</code> olan son kayıt (\"o gün rover nerede duruyordu\")."
        where = "<code>scripts/build_regions.py</code> → <code>web/data/regions.json</code>, <code>poi.geojson</code>: pinlerin konumu. Füzyonda ağırlığı yok."
        summary = f"D1, {tr(len(fe))} rover konumundan 4 alanı kullanarak haritadaki {n_pins} pini ölçülmüş konumlarına oturtuyor."
        prev = FIG / "onizleme" / "d1.png"
    elif did == "D2":
        used = {
            "geometry": f"<code>validate.route_cells</code>: çizgi 10 m'de bir örneklenip 256² grid'e düşürüldü → {tr(E10V['route_cells_total'])} rota hücresi "
                        f"(doğrulama, AUC). <code>pipeline_stats.d1_d3</code>: köşe sayımı.",
            "length": f"<code>pipeline_stats.d1_d3</code>: toplam uzunluk {tr(s['length_km'], 1)} km (yalnızca raporlama).",
        }
        reasons = {
            "sol": "Doğrulama zamana bakmıyor; bütün sürüşler birlikte kullanıldı.",
            "fromRMC": "D1 kayıtlarına bağlanan sayaç; çizginin kendisi yeterli.", "toRMC": "Aynı neden.",
            "SCLK_START": "Uzay aracı saati; zamana ihtiyaç yok.", "SCLK_END": "Aynı neden.",
        }
        head = facts({"Ad": "D2 · Perseverance sürüş izi (traverse)", "Kaynak": link(url), "Format": "GeoJSON (FeatureCollection, LineString)",
                      "Boyut": size_txt(RAW / name), "Kayıt": f"{tr(len(fe))} sürüş çizgisi, {tr(s['vertices'])} köşe, {tr(s['length_km'], 1)} km",
                      "Çözünürlük": "yok (çizgi verisi)", "Projeksiyon": esc(crs) + " (coğrafi, derece)"})
        dropped = f"Çalışma alanı dışındaki {tr(s['vertices'] - s['vertices_inside'])} köşe; alan içinde {tr(s['vertices_inside'])} köşe kaldı."
        clean = ("Rasterize: ardışık köşeler arası 10 m'de bir örnek, hücre = <code>floor((lon − batı) / (doğu − batı) · 256)</code> "
                 "(walkback.js ile aynı indeks). Rota modele ve füzyona verilmedi.")
        where = (f"<code>scripts/validate.py</code>: rota hücreleri ({tr(E10V['route_cells_total'])}, {tr(E10V['route_cells_in_hirise'])}'si HiRISE kapsamında) "
                 f"skorun sınavı. HiRISE kapsamında AUC {tr(E10V['hirise_kapsami']['once_yolo_yok']['auc_route_lower'], 3)} → "
                 f"{tr(E10V['hirise_kapsami']['sonra_yolo']['auc_route_lower'], 3)}. Ağırlığı yok; yalnızca doğrulama.")
        summary = "D2, rover'ın gerçekten sürdüğü yol olarak geçilebilirlik skorumuzu modele hiç gösterilmeden sınayan bağımsız referans."
        prev = FIG / "onizleme" / "d2.png"
    else:
        used = {
            "Flight": "<code>build_regions.position(\"heli\", 1)</code>: Uçuş 1 seçildi.",
            "geometry": "Uçuş 1'in ilk köşesi = kalkış noktası → Ingenuity pini. D1'deki Sol 34 rover konumuyla birebir aynı (çapraz doğrulama).",
        }
        reasons = {
            "Sol": "Kodda okunmuyor; Uçuş 1'in Sol'ü (58) nokta kartı tanımında yazılı.",
            "Length_m": "Kodda okunmuyor; İHA parametreleri rescue.js'te varsayım olarak yazıldı.",
            "SCLK_START": "Uzay aracı saati; zamana ihtiyaç yok.", "SCLK_END": "Aynı neden.",
        }
        head = facts({"Ad": "D3 · Ingenuity uçuş izleri", "Kaynak": link(url), "Format": "GeoJSON (FeatureCollection, LineString)",
                      "Boyut": size_txt(RAW / name), "Kayıt": f"{tr(len(fe))} uçuş (Uçuş 1 Sol {fe[0]['properties']['Sol']} → Uçuş {fe[-1]['properties']['Flight']} Sol {fe[-1]['properties']['Sol']})",
                      "Çözünürlük": "yok (çizgi verisi)", "Projeksiyon": esc(crs)})
        n_unused = sum(1 for c in props if c not in used)
        dropped = (f"{tr(len(fe) - 1)} uçuş pin için kullanılmadı (hepsi alanda: {tr(s['inside_area'])}/{tr(len(fe))}). "
                   f"Kullanılmayan öznitelik: {n_unused}/{len(props)} (yalnızca Flight ve geometri).")
        clean = "Temizleme gerekmedi; yalnızca seçim (Uçuş 1, ilk köşe)."
        where = "<code>scripts/build_regions.py</code> → <code>regions.json</code>: Ingenuity tarih pini. Füzyonda ağırlığı yok."
        summary = "D3'ten tek bir nokta aldık: başka bir gezegendeki ilk motorlu uçuşun kalkış yeri, rover konumuyla da doğrulandı."
        prev = FIG / "onizleme" / "d3.png"
    body = (table(cols, rows, used) + f'<p class="cap">İlk 5 kayıt, dosyadaki sırayla. Uzun değerler kısaltıldı; tamamı için hücrenin üstüne gel.</p>'
            + field_notes(cols, used, reasons))
    if prev.exists():
        body += f'<figure><img src="{uri_img(Image.open(prev), q=78)}" alt="{did} haritası"><figcaption>Dosyanın haritadaki hali (<code>scripts/make_previews.py</code>).</figcaption></figure>'
    return section(did.lower(), head_title(did), head, body, dropped, clean, where, summary)


def head_title(did):
    return {"D1": "D1 · Perseverance konumları", "D2": "D2 · Perseverance sürüş izi", "D3": "D3 · Ingenuity uçuşları",
            "D4": "D4 · THEMIS termal eylemsizlik", "D5": "D5 · CTX sayısal yükseklik modeli", "D6": "D6 · USGS SIM 3464 jeoloji haritası",
            "D7": "D7 · Perseverance ham görüntüleri (API)", "D8": "D8 · HiRISE 25 cm ortomozaik", "TREK": "Mars Trek · Taban harita karoları"}[did]


# ---- D4 -------------------------------------------------------------------------------------
def d4_section(L):
    p = RAW / "Jezero_Thermal_Inertia_v1.tiff"
    s = STATS["D4"]
    with rasterio.open(p) as src:
        a = src.read(1).astype(np.float32)
        crs, ext = src.crs, [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        res, w, h = src.res, src.width, src.height
    nod = a == 0
    v = a[~nod]
    th = L["thermal"]
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6))
    im0 = ax[0].imshow(np.where(nod, np.nan, a), extent=ext, cmap="inferno")
    bx, by = bbox_line(crs)
    ax[0].plot(bx, by, color="#4fd1ff", lw=1.4)
    ax[0].set_title("Ham: TI (TIU), siyah = NoData, mavi = çalışma alanı", loc="left")
    fig.colorbar(im0, ax=ax[0], fraction=0.046)
    im1 = ax[1].imshow(th, extent=[P.BOUNDS["west"], P.BOUNDS["east"], P.BOUNDS["south"], P.BOUNDS["north"]], cmap="inferno", vmin=0, vmax=1)
    ax[1].set_title("İşlenmiş: termal_norm (0 gevşek – 1 sert), 1024²", loc="left")
    fig.colorbar(im1, ax=ax[1], fraction=0.046)
    for x in ax:
        x.set_xticks([]), x.set_yticks([])
    fig.tight_layout()
    img = uri_fig(fig)
    hist = hist_pair(v, th, "Önce: ham TI, bütün dosya (NoData hariç)", "Sonra: termal_norm, çalışma alanı",
                     "TIU", "0–1", lines_a=[(s["p2"], "p2"), (s["p98"], "p98")])
    head = facts({"Ad": "D4 · THEMIS termal eylemsizlik mozaiği", "Kaynak": link(DL.SOURCES["D4"][1]),
                  "Format": "GeoTIFF, float32, deflate", "Boyut": size_txt(p), "Piksel": f"{tr(w)} × {tr(h)} = {tr(w * h)}",
                  "Çözünürlük": f"{tr(res[0])} m/piksel", "Projeksiyon": esc(crs_name(crs))})
    body = (f'<figure><img src="{img}" alt="D4 ham ve işlenmiş"></figure><figure><img src="{hist}" alt="D4 histogram"></figure>'
            + stat_table([stat_row("Ham TI (NoData hariç)", v), stat_row("TI, çalışma alanı (1024², bilinear)", L["ti"][np.isfinite(L["ti"])]),
                          stat_row("termal_norm (1024²)", th[np.isfinite(th)])],
                         f"bütün dosyada {tr(nod.sum())} / {tr(nod.size)} = %{tr(100 * nod.mean(), 1)} (değer 0: THEMIS kapsamı dışındaki köşeler); "
                         f"çalışma alanı içinde {tr(s['inside_nodata'])}."))
    dropped = (f"{tr(s['dropped_outside'])} piksel çalışma alanı dışında ({tr(s['nodata'])} NoData dahil); alan içinde {tr(s['inside_area'])} piksel kaldı. "
               f"Uçlarda {tr(s['clipped_low'])} + {tr(s['clipped_high'])} piksel kırpıldı (0 ya da 1'e sabitlendi).")
    clean = (f"NoData 0 → NaN (ortalamaya karışmasın). Bilinear yeniden örnekleme. "
             f"<code>termal_norm = clip((TI − p2) / (p98 − p2), 0, 1)</code>, p2 = {tr(s['p2'], 1)}, p98 = {tr(s['p98'], 1)} TIU. "
             "Min–maks yerine yüzdelik: birkaç aykırı piksel ölçeği bozmasın.")
    where = "<code>scripts/prep_layers.py</code> (<code>normalize_thermal</code>, <code>build</code>): füzyonda <b>0,2 · (1 − termal_norm)</b>; <code>layers/thermal.png</code> katmanı."
    summary = "D4 zeminin gevşekliğini (Spirit'i gömen tuzak) yörüngeden ölçüyor; %2–98 dilimiyle 0–1'e çekilip skorun %20'sini oluşturuyor."
    return section("d4", head_title("D4"), head, body, dropped, clean, where, summary)


# ---- D5 -------------------------------------------------------------------------------------
def d5_section(L):
    p = RAW / "M20_JezeroCrater_CTXDEM_20m.tif"
    s = STATS["D5"]
    with rasterio.open(p) as src:
        z = src.read(1)
        crs, ext = src.crs, [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        res, w, h = src.res, src.width, src.height
    bad = (z < -9000) | (z > 30000)
    v = z[~bad]
    sl = L["slope"]
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6))
    zz = np.where(bad, np.nan, z)[::6, ::6]
    im0 = ax[0].imshow(zz, extent=ext, cmap="viridis")
    bx, by = bbox_line(crs)
    ax[0].plot(bx, by, color="#ff5c5c", lw=1.4)
    ax[0].set_title("Ham: yükseklik (m), 1/6 önizleme, kırmızı = alan", loc="left")
    fig.colorbar(im0, ax=ax[0], fraction=0.046)
    im1 = ax[1].imshow(sl, extent=[P.BOUNDS["west"], P.BOUNDS["east"], P.BOUNDS["south"], P.BOUNDS["north"]], cmap="magma", vmin=0, vmax=30)
    ax[1].set_title("İşlenmiş: eğim (°), 20 m'de hesaplanıp 1024²'ye ortalandı", loc="left")
    fig.colorbar(im1, ax=ax[1], fraction=0.046)
    for x in ax:
        x.set_xticks([]), x.set_yticks([])
    fig.tight_layout()
    img = uri_fig(fig)
    hist = hist_pair(v, sl, "Önce: ham yükseklik, bütün dosya", "Sonra: eğim, çalışma alanı (1024²)", "m", "derece",
                     lines_b=[(25, "25° geçilmez")])
    head = facts({"Ad": "D5 · CTX DEM, Jezero (Mars 2020 iniş bölgesi)", "Kaynak": link(DL.SOURCES["D5"][1]),
                  "Format": "GeoTIFF, float32, sıkıştırmasız", "Boyut": size_txt(p), "Piksel": f"{tr(w)} × {tr(h)} = {tr(w * h)}",
                  "Çözünürlük": f"{tr(res[0])} m/piksel", "Projeksiyon": esc(crs_name(crs))})
    body = (f'<figure><img src="{img}" alt="D5 ham ve işlenmiş"></figure><figure><img src="{hist}" alt="D5 histogram"></figure>'
            + stat_table([stat_row("Ham yükseklik (m, NoData hariç)", v), stat_row("Yükseklik, çalışma alanı (1024²)", L["elev"][np.isfinite(L["elev"])]),
                          stat_row("Eğim (°), çalışma alanı (1024²)", sl[np.isfinite(sl)])],
                         f"bütün dosyada {tr(bad.sum())} / {tr(bad.size)} = %{tr(100 * bad.mean(), 2)} (−3,4·10³⁸: mozaik kenarları); "
                         f"çalışma alanı içinde {tr(s['inside_nodata'])}."))
    dropped = (f"{tr(s['dropped_outside'])} piksel (%{tr(100 * s['dropped_outside'] / s['pixels'], 1)}) çalışma alanı dışında; "
               f"{tr(s['nodata'])} NoData. Alan içinde {tr(s['inside_area'])} piksel kaldı.")
    clean = ("−9000 m altı ve 30.000 m üstü NoData → NaN. Eğim yeniden örneklemeden önce 20 m'de: "
             "<code>eğim = atan(√((∂z/∂x)² + (∂z/∂y)²))</code>; sonra hücre ortalaması (average). "
             f"<code>eğim_risk = clip(eğim / 25°, 0, 1)</code>. 20 m'de alan içinde {tr(s['slope_gt25_20m'])} piksel 25°'nin üstünde.")
    where = ("<code>scripts/prep_layers.py</code> (<code>slope_native</code>, <code>warp</code>, <code>make_grid</code>): füzyonda <b>0,4 · eğim_risk</b> (en büyük ağırlık); "
             f"eğim > 25° hücre geçilmez ({tr(STATS['grid']['blocked_slope'])} hücre). <code>grid.json</code> <code>elev</code> → walkback.js yönlü eğim ve Tobler hızı; "
             "eva.js telsiz görüş hattı.")
    summary = "D5 hem yürüme süresini (Tobler) hem geçilmezliği belirleyen eğimi veriyor; skorun en ağır terimi ve rota hesabının temeli."
    return section("d5", head_title("D5"), head, body, dropped, clean, where, summary)


# ---- D6 -------------------------------------------------------------------------------------
def d6_section(L):
    shp = RAW / "D6_geology" / "Jezero_GeoUnits.shp"
    s = STATS["D6"]
    g = gpd.read_file(shp)
    cols = [c for c in g.columns if c != "geometry"] + ["geometry"]
    rows = []
    for _, r in g.head(5).iterrows():
        geom = r.geometry
        nv = sum(len(p.exterior.coords) for p in getattr(geom, "geoms", [geom]))
        rows.append([r[c] for c in cols[:-1]] + [f"{geom.geom_type}, {nv} köşe"])
    used = {
        "name": "<code>prep_layers.geology</code>: birim adı → <code>GEO_UNITS</code> katsayıları (yürünebilirlik, kaya vekili, bilim değeri); "
                "<code>GEO_FIX</code> ile yazım hatası düzeltildi. Eşlemede koda değil ada güvenildi.",
        "unit": f"<code>pipeline_stats.d6</code>: kod–ad tutarlılık kontrolü ({tr(s['unit_code_mismatch'])} poligonda kod 5 ama ad \"Upper etched unit\").",
        "geometry": f"<code>prep_layers.geology</code>: hedef sisteme çevrilip 1024² ve 256² ızgaraya rasterize (büyükten küçüğe). "
                    f"<code>pipeline_stats.d6</code>: alan içi {tr(s['polygons_in_area'])} poligon, birim alanları.",
    }
    reasons = {
        "symbol_noS": "Harita etiketi kısaltması; adla aynı bilgi.", "subscript": "Etiket alt simgesi; aynı neden.",
        "symbol": "Tam etiket (ör. Nnp2); aynı neden.", "ORIG_FID": "Kaynak veritabanındaki satır numarası; anlamı yok.",
        "SHAPE_Leng": "Poligon çevresi; tehlike için anlamsız.",
        "SHAPE_Area": "Kaynak projeksiyondaki alan; kırpınca değiştiği için alanları yeniden hesapladık.",
        "Color_ID": "USGS'in harita rengi; kendi renk tablomuz GEO_UNITS'te.",
    }
    gc = g.copy()
    gc["name"] = gc["name"].replace(P.GEO_FIX)
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.8))
    gc.plot(ax=ax[0], column="name", cmap="tab20", linewidth=0)
    bx, by = bbox_line(g.crs)
    ax[0].plot(bx, by, color="#ff5c5c", lw=1.4)
    ax[0].set_title(f"Ham: {tr(len(g))} poligon, {tr(s['units'])} birim (kırmızı = alan)", loc="left")
    ax[1].imshow(plt.imread(ROOT / "web/data/layers/geology.png"))
    ax[1].set_title(f"İşlenmiş: {tr(s['polygons_in_area'])} poligon → 1024² ızgara", loc="left")
    for x in ax:
        x.set_xticks([]), x.set_yticks([])
    fig.tight_layout()
    img = uri_fig(fig)
    km = "".join(f"<tr><td>{esc(k)}</td><td>{tr(v, 1)}</td><td>{', '.join(tr(x, 2) for x in P.GEO_UNITS[k][:2])}</td></tr>"
                 for k, v in s["unit_km2_in_area"].items())
    head = facts({"Ad": "D6 · USGS SIM 3464, Jezero Krateri ve Nili Planum jeoloji haritası", "Kaynak": link(DL.SOURCES["D6"][1]),
                  "Format": f"Zip ({tr(s['zip_files'])} dosya) → ArcGIS dosya veritabanı (Nili.gdb, {len(s['gdb_layers'])} katman) → GeoUnits_v1 shapefile'a çıkarıldı",
                  "Boyut": f"zip {size_txt(RAW / 'sim3464_database.zip')}; çıkarılan shapefile {size_txt(shp)}",
                  "Kayıt": f"{tr(len(g))} poligon × {tr(len(cols) - 1)} öznitelik", "Çözünürlük": "1:75.000 ölçekli vektör harita",
                  "Projeksiyon": esc(g.crs.name)})
    body = (table(cols, rows, used) + '<p class="cap">GeoUnits_v1 katmanının ilk 5 poligonu.</p>' + field_notes(cols, used, reasons)
            + f'<figure><img src="{img}" alt="D6 ham ve işlenmiş"></figure>'
            + f'<div class="tw"><table class="stat"><thead><tr><th>Alan içindeki birim</th><th>km²</th><th>yürünebilirlik, kaya vekili</th></tr></thead><tbody>{km}</tbody></table></div>')
    dropped = (f"Zip'te {tr(s['zip_dropped_macosx_lock'])} sistem dosyası; {len(s['gdb_layers'])} katmanın {len(s['gdb_layers']) - 1}'si "
               f"(kontaklar, isimler, şekiller…); alana değmeyen {tr(s['polygons_dropped_outside'])} poligon; 7 öznitelik sütunu.")
    clean = (f"Kaynak hataları: \"Crater riim unit\" yazımı ({tr(s['typo_fixed'])} poligon) düzeltildi; kodu ile adı çelişen {tr(s['unit_code_mismatch'])} poligon "
             "ada göre sınıflandı. Birim → sayı: <code>GEO_UNITS</code> tablosu (varsayım; birim tanımlarından). Kum = eolyen birim (0/1).")
    where = ("<code>scripts/prep_layers.py</code>: füzyonda <b>0,25 · kum</b> (eolyen birim) ve <b>0,15 · kaya</b> (kaya vekili); HiRISE kapsamında YOLO ile yarı yarıya. "
             "<code>grid.json</code> <code>sand</code> → eva.js \"kum tuzağı\" kontrolü; <code>build_regions.py</code> nokta kartı tehlikeleri ve kum alanı pini.")
    summary = "D6 \"ne üzerinde yürüdüğünü\" söylüyor: 118 poligon, birim başına katsayıyla kum ve kaya terimlerine çevrildi."
    return section("d6", head_title("D6"), head, body, dropped, clean, where, summary)


# ---- D7 -------------------------------------------------------------------------------------
def flatten(d, pre=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flatten(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out


def d7_section():
    url = BR.API.format(sol=D7_SOL)
    r = requests.get(url, headers=UA, timeout=90)
    r.raise_for_status()
    js = r.json()
    ims = js["images"]
    flat = [flatten(i) for i in ims[:5]]
    cols = list(flat[0].keys())
    for f in flat[1:]:
        cols += [k for k in f if k not in cols]
    rows = [[f.get(c) for c in cols] for f in flat]
    used = {
        "sol": "<code>save_photo</code>: fotoğraf etiketindeki Sol.",
        "sample_type": "<code>choose_photos</code>: yalnızca <code>Full</code> (tam kare).",
        "camera.instrument": "<code>choose_photos</code>: sol göz Navcam / Mastcam-Z / ön Hazcam (<code>CAMS</code>).",
        "extended.dimension": f"<code>width()</code>: genişlik ≥ {BR.MIN_WIDTH} px (alt kareleri atar).",
        "extended.mastEl": f"<code>mast_el()</code>: direk açısı {tr(BR.MAST_EL[0])}° … +{tr(BR.MAST_EL[1])}°, hedef {tr(BR.TARGET_EL)}°'ye en yakın.",
        "imageid": "<code>frame_key</code>: renkli/gri ikizleri tekilleştirme; <code>EXCLUDE</code> insan kontrolü listesi.",
        "image_files.medium": "800 px kopya indirildi (<code>web/data/photos/</code>, çevrimdışı demo).",
        "image_files.large": "Nokta kartında \"büyük boy\" bağlantısı.",
        "link": "Kaynak sayfa bağlantısı (kredi ile birlikte).",
        "date_taken_utc": "Kart başlığında tarih.", "date_taken_mars": "Kart başlığında yerel Mars saati (LMST).",
        "credit": "Kredi satırı (NASA/JPL-Caltech[/ASU]).",
    }
    reasons = {
        "extended.mastAz": "Direk yönü; seçim yalnızca eğim açısına bakıyor.", "extended.sclk": "Uzay aracı saati; UTC tarihi var.",
        "extended.scaleFactor": "Alt örnekleme çarpanı; genişlik filtresi yeterli.", "extended.xyz": "Rover çerçevesinde konum; konum D1'den.",
        "extended.subframeRect": "Alt kare dikdörtgeni; alt kareler genişlik filtresiyle atılıyor.",
        "attitude": "Rover duruşu (kuaterniyon); fotoğrafı yalnızca gösteriyoruz.",
        "image_files.small": "320 px; kartta 800 px kullanıldı.", "image_files.full_res": "Tam boy PNG; çevrimdışı demo için büyük.",
        "camera.filter_name": "Kamera geometrisi/filtre (fotogrametri için); biz ölçüm yapmıyoruz.",
        "camera.camera_vector": "Aynı neden.", "camera.camera_model_component_list": "Aynı neden.",
        "camera.camera_position": "Aynı neden.", "camera.camera_model_type": "Aynı neden.",
        "caption": "Uzun İngilizce açıklama; kendi Türkçe başlığımızı ürettik.", "title": "Aynı neden.",
        "json_link": "Tek kayıt API bağlantısı; Sol sorgusu yeterli.",
        "drive": "Rover sayacı; konum D1'den.", "site": "Aynı neden.", "date_received": "Dünya'ya ulaşma tarihi; çekim tarihi yeterli.",
    }
    for c in cols:
        if c not in used and c not in reasons:
            reasons[c] = "Seçim ve gösterim için gerekmedi."
    pr = E7["per_region"]
    tot_api = sum(v.get("api_images", 0) for k, v in pr.items() if not k.endswith("_tried")) + \
        sum(x.get("api_images", 0) for k, v in pr.items() if k.endswith("_tried") for x in v)
    sols = sum(1 for k in pr if not k.endswith("_tried") and pr[k].get("api_images")) + sum(len(v) for k, v in pr.items() if k.endswith("_tried"))
    photos = sorted((ROOT / "web/data/photos").glob("delta_front_*.jpg"))
    thumbs = "".join(f'<figure class="half"><img src="{uri_img(Image.open(p).resize((400, int(400 * Image.open(p).height / Image.open(p).width))), q=80)}" alt="{p.name}">'
                     f'<figcaption>Seçilen: <code>{p.name}</code></figcaption></figure>' for p in photos[:2])
    head = facts({"Ad": "D7 · Perseverance ham görüntüleri (raw images API)", "Kaynak": link(BR.API.replace("{sol}", "<Sol>")),
                  "Format": f"JSON (Sol başına bir cevap; üst alanlar: {', '.join(k for k in js if k != 'images')})",
                  "Boyut": f"Sol {D7_SOL} cevabı {tr(len(r.content) / 1e6, 2)} MB", "Kayıt": f"Sol {D7_SOL}: {tr(len(ims))} görüntü × {tr(len(cols))} alan (iç içe alanlar açıldı); "
                  f"projede {tr(sols)} Sol, {tr(tot_api)} görüntü kaydı", "Çözünürlük": "kameraya göre değişir (ör. 128×128 alt kare … 5120×3840)",
                  "Projeksiyon": "yok (kamera görüntüsü)"})
    body = (table(cols, rows, used) + f'<p class="cap">Sol {D7_SOL} cevabının ilk 5 kaydı (bugün API\'den çekildi). İç içe alanlar nokta ile açıldı (ör. <code>camera.instrument</code>).</p>'
            + field_notes(cols, used, reasons) + f'<div class="pair">{thumbs}</div>')
    dropped = (f"{tr(tot_api)} kayıttan 10 fotoğraf kaldı. Huni: kamera (sağ göz, arka Hazcam, SkyCam…), genişlik < {BR.MIN_WIDTH} px, renkli/gri ikiz, "
               f"direk açısı dışı, doku eşiği (düz gökyüzü) ve 1 insan kontrolü. Adım adım sayılar DATA_PIPELINE.md D7 tablosunda.")
    clean = (f"Doku eşiği: 400×300 gri görüntüde ortalama kenar şiddeti ≥ {tr(BR.MIN_EDGE, 1)} (ölçüm: gökyüzü 1,4 ve 3,1; en düşük iyi kare 4,2). "
             "Kamera başına direk açısı −10°'ye en yakın kare. 800 px yerel kopya.")
    where = "<code>scripts/build_regions.py</code> (<code>choose_photos</code>, <code>save_photo</code>) → <code>regions.json</code> fotoğrafları; nokta kartında \"oraya varınca bunu göreceksin\". Füzyonda ağırlığı yok."
    summary = f"D7, astronotun yürüyeceği yerin rover'ın o gün çektiği gerçek fotoğrafını kural tabanlı bir eleme hunisiyle seçiyor ({tr(tot_api)} kayıt → 10 fotoğraf)."
    return section("d7", head_title("D7"), head, body, dropped, clean, where, summary)


# ---- D8 -------------------------------------------------------------------------------------
def d8_section():
    p = T.ORTHO
    cache = PROC / "d8_preview_dec16.npz"
    with rasterio.open(p) as src:
        crs, w, h, res = src.crs, src.width, src.height, src.res
        if cache.exists():
            z = np.load(cache)
            prev, k, c0, r0, nx, ny = z["prev"], int(z["k"]), int(z["c0"]), int(z["r0"]), int(z["nx"]), int(z["ny"])
        else:
            c0, r0, nx, ny = T.study_window(src)
            prev, k = T.preview(src, c0, r0, nx, ny)
            np.savez_compressed(cache, prev=prev, k=k, c0=c0, r0=r0, nx=nx, ny=ny)
        nod_t, std_t = T.tile_stats(prev, k, 0)
        has_nod = nod_t > 0
        flat_thr = float(np.percentile(std_t[~has_nod], 5))
        flat = (~has_nod) & (std_t < flat_thr)
        # Örnek karolar: NoData oranı %50'ye en yakın karo; dokusuz karoların std'ye göre ortancası
        rn, cn = np.unravel_index(np.argmin(np.where(has_nod, np.abs(nod_t - 0.5), 9)), nod_t.shape)
        fr, fc = np.argwhere(flat)[np.argsort(std_t[flat])[flat.sum() // 2]]
        tile_nod = src.read(1, window=Window(c0 + cn * T.TILE, r0 + rn * T.TILE, T.TILE, T.TILE))
        tile_flat = src.read(1, window=Window(c0 + fc * T.TILE, r0 + fr * T.TILE, T.TILE, T.TILE))
    lo, hi = E5["screen"]["stretch_p0_5"], E5["screen"]["stretch_p99_5"]
    valid = prev[prev != 0]
    stretched = np.clip((valid.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255)
    # Ham ve işlenmiş önizleme
    raw_img = Image.fromarray(prev).convert("RGB")
    st = np.clip((prev.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    st_rgb = np.stack([st] * 3, -1)
    st_rgb[prev == 0] = (20, 16, 14)
    over = Image.fromarray(st_rgb).convert("RGBA")
    lay = Image.new("RGBA", over.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    sel = {(int(r["tile_row"]), int(r["tile_col"])) for r in csv.DictReader(open(ROOT / "ml/tiles_manifest.csv", encoding="utf-8"))}
    for r in range(ny):
        for c in range(nx):
            box = [c * k, r * k, (c + 1) * k - 1, (r + 1) * k - 1]
            if has_nod[r, c]:
                dr.rectangle(box, fill=(231, 76, 60, 70))
            elif flat[r, c]:
                dr.rectangle(box, fill=(79, 209, 255, 110))
            if (r, c) in sel:
                dr.rectangle(box, outline=(62, 207, 142, 255), width=3)
    proc_img = Image.alpha_composite(over, lay).convert("RGB")
    scale = 520 / raw_img.height
    raw_s = raw_img.resize((int(raw_img.width * scale), 520), Image.LANCZOS)
    proc_s = proc_img.resize((int(proc_img.width * scale), 520), Image.LANCZOS)
    hist = hist_pair(valid, stretched, "Önce: ham piksel (uint8), NoData hariç", "Sonra: germe (60–219 → 0–255)", "parlaklık", "parlaklık",
                     lines_a=[(lo, "%0,5"), (hi, "%99,5")], bins=64)

    def tile_fig(img, title, sub):
        img = img.convert("RGB").resize((320, 320), Image.LANCZOS)
        return f'<figure class="tile"><img src="{uri_img(img, q=85)}" alt="{esc(title)}"><figcaption><b>{title}</b><br>{sub}</figcaption></figure>'

    def stretch_img(a):
        """Ortogörüntüden okunan karoya E5 germesi (NoData siyah kalır)."""
        b = np.clip((a.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
        b[a == 0] = 0
        return Image.fromarray(b)

    # Etiketli iki karo (ml/dataset_merged): biri kum dalgası, biri kaya + kaya alanı kutularıyla
    ds = ROOT / "ml" / "dataset_merged"
    labs = []
    for split in ("valid", "train"):
        for lab in sorted((ds / split / "labels").glob("*.txt")):
            rows = [l.split() for l in lab.read_text().splitlines() if l.strip()]
            labs.append((split, lab, rows))
    names = ["kaya", "kaya_alani", "kum_dalgasi"]
    colors = {0: (255, 92, 92), 1: (255, 170, 60), 2: (255, 230, 80)}

    def best(pred):
        c = [x for x in labs if pred(x[2])]
        return max(c, key=lambda x: len(x[2])) if c else None
    kum = best(lambda rs: rs and all(r[0] == "2" for r in rs) and all(float(r[3]) * float(r[4]) < 0.5 for r in rs))
    kaya = best(lambda rs: any(r[0] == "0" for r in rs) and any(r[0] == "1" for r in rs) and not any(r[0] == "2" for r in rs))

    def labeled(x):
        split, lab, rows = x
        img_p = next((ds / split / "images").glob(lab.stem + ".*"))
        im = Image.open(img_p).convert("RGB")
        d = ImageDraw.Draw(im)
        for r in rows:
            c, cx, cy, bw, bh = int(r[0]), *map(float, r[1:5])
            W, H = im.size
            d.rectangle([(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H], outline=colors[c], width=3)
        cnt = {names[i]: sum(1 for r in rows if int(r[0]) == i) for i in range(3)}
        tid = lab.stem.split("_png")[0]
        return tile_fig(im, f"Etiketli: {tid} ({split})", ", ".join(f"{v} {k}" for k, v in cnt.items() if v) + " kutusu")
    tiles = [tile_fig(stretch_img(tile_nod), f"Atıldı · NoData: jz_r{rn:03d}_c{cn:03d}", f"önizlemede %{tr(100 * nod_t[rn, cn], 0)} NoData (siyah); mozaik şeridinin kenarı"),
             tile_fig(stretch_img(tile_flat), f"Atıldı · dokusuz: jz_r{fr:03d}_c{fc:03d}", f"önizleme std {tr(std_t[fr, fc], 2)} < eşik {tr(flat_thr, 2)} (alt %5)")]
    tiles += [labeled(x) for x in (kum, kaya) if x]
    s = E5["screen"]
    head = facts({"Ad": "D8 · HiRISE ortogörüntü mozaiği (MSR TRN, soc_003)", "Kaynak": link(DL.SOURCES["D8"][1]),
                  "Format": "Zip içinde GeoTIFF, uint8, LZW; NoData = 0", "Boyut": f"zip {size_txt(RAW / 'MSR_TRN_HiRISE_mosaics.zip')}; ortogörüntü {size_txt(p)}",
                  "Piksel": f"{tr(w)} × {tr(h)} = {tr(w * h)}", "Çözünürlük": f"{tr(res[0], 2)} m/piksel",
                  "Projeksiyon": esc(crs_name(crs))})
    nod_prev = (prev == 0).mean()
    body = (f'<div class="pair"><figure class="half"><img src="{uri_img(raw_s, q=80)}" alt="D8 ham"><figcaption>Ham: E5 karolama alanı, 1/16 önizleme '
            f'({tr(nx)} × {tr(ny)} karo; siyah = NoData)</figcaption></figure>'
            f'<figure class="half"><img src="{uri_img(proc_s, q=80)}" alt="D8 işlenmiş"><figcaption>İşlenmiş: germe 60–219; kırmızı = NoData yüzünden atılan, '
            f'mavi = dokusuz, yeşil çerçeve = etiketlenen 150 karo</figcaption></figure></div>'
            f'<figure><img src="{hist}" alt="D8 histogram"></figure>'
            + stat_table([stat_row("Ham, önizleme (NoData hariç)", valid), stat_row("Germeden sonra", stretched)],
                         f"karolama penceresinin 1/16 önizlemesinde %{tr(100 * nod_prev, 1)}; {tr(s['tiles_total'])} karonun {tr(s['dropped_nodata'])}'ü "
                         f"(%{tr(100 * s['dropped_nodata'] / s['tiles_total'], 1)}) NoData içeriyor. Bütün mozaik için ölçülmedi: yok.")
            + f'<h3>Dört örnek karo (640 × 640 px = 160 × 160 m)</h3><div class="tiles">{"".join(tiles)}</div>'
            '<p class="cap">Kutu renkleri: kırmızı = kaya, turuncu = kaya_alani, sarı = kum_dalgasi. Etiketli karolar Roboflow dışa aktarımından '
            '(JPG, germe uygulanmış); atılan karolar ortogörüntüden tam çözünürlükte okunup aynı germeyle gösterildi.</p>')
    dropped = (f"Zip'te ortogörüntü dışındaki her şey (1 m DTM, renkli güven haritası); FOM güven haritası çıkarıldı ama kullanılmadı. "
               f"{tr(s['tiles_total'])} karonun {tr(s['dropped_nodata'])}'ü NoData, {tr(s['dropped_flat'])}'i dokusuz; kalan {tr(s['usable'])} karodan "
               f"{tr(E5['selected']['total'])} etiketlemeye seçildi (+ 2. partide 100 → toplam {tr(E6S['tiles'])}).")
    clean = (f"Alan geneli tek doğrusal germe: <code>piksel' = clip((piksel − {tr(lo)}) / ({tr(hi)} − {tr(lo)}) · 255, 0, 255)</code> "
             f"(%0,5 ve %99,5 dilimleri). Dokusuz: önizleme std < {tr(flat_thr, 2)} (kullanılabilir karoların alt %5'i). "
             "Seçimde en uzak nokta örneklemesi (seed 42).")
    where = (f"<code>scripts/tile_for_yolo.py</code>, <code>tile_batch2.py</code> → etiket → <code>ml/train.py</code> (YOLOv8s). <code>ml/infer.py</code>: "
             f"{tr(E10I['tiles_inferred'])} karoda çıkarım → hücre başına <code>kum_ml</code>, <code>kaya_ml</code> ({tr(E10I['grid_cells_with_ml'])} hücre). "
             "Füzyonda HiRISE kapsamında kum ve kaya terimlerinin <b>yarısı</b> (0,5 · eolyen + 0,5 · kum_ml; 0,5 · kaya vekili + 0,5 · kaya_ml).")
    summary = (f"D8, 20 m DEM'in göremediği metre ölçeğindeki kum dalgası ve kayayı gösteren tek kaynak; kendi modelimizi bununla eğittik ve "
               f"rota doğrulamasında AUC'yi {tr(E10V['hirise_kapsami']['once_yolo_yok']['auc_route_lower'], 2)}'den "
               f"{tr(E10V['hirise_kapsami']['sonra_yolo']['auc_route_lower'], 2)}'e çıkardı.")
    return section("d8", head_title("D8"), head, body, dropped, clean, where, summary)


# ---- Mars Trek ------------------------------------------------------------------------------
def trek_tile(key, z, x, y):
    _, lab, ext, _ = TREK_LAYERS[key]
    u = f"{TREK}{lab}/1.0.0/default/default028mm/{z}/{y}/{x}.{ext}"
    r = requests.get(u, headers=UA, timeout=60)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGBA"), u, len(r.content)


def trek_section():
    lon, lat = 77.45089, 18.44463   # üs (walkback.js BASE)
    z = TREK_LAYERS["ctx"][3]
    d = 180 / 2 ** z
    x0, y0 = int((lon + 180) // d) - 1, int((90 - lat) // d) - 1
    mos = Image.new("RGBA", (768, 768))
    sizes, sample_url = [], None
    for j in range(3):
        for i in range(3):
            t, u, n = trek_tile("ctx", z, x0 + i, y0 + j)
            mos.paste(t, (i * 256, j * 256))
            sizes.append(n)
            sample_url = sample_url or u
    W0, N0 = x0 * d - 180, 90 - y0 * d
    px_deg = d / 256
    m_per_px = px_deg * P.M_PER_DEG
    arr = np.asarray(mos)
    alpha0 = arr[..., 3] == 0
    gray = np.asarray(mos.convert("L")).astype(np.float32)
    nodata = alpha0 | (gray == 0)
    # Uygulamadaki hali: aynı karolar + bizim geçilebilirlik katmanımız (layers.json bbox'ına serilir, saydamlık 0,6)
    tv = Image.open(ROOT / "web/data/layers/traversability.png").convert("RGBA")
    bx0, by0 = int((P.BOUNDS["west"] - W0) / px_deg), int((N0 - P.BOUNDS["north"]) / px_deg)
    bx1, by1 = int((P.BOUNDS["east"] - W0) / px_deg), int((N0 - P.BOUNDS["south"]) / px_deg)
    tv = tv.resize((bx1 - bx0, by1 - by0), Image.LANCZOS)
    a = np.asarray(tv).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * 0.6).astype(np.uint8)
    app = mos.copy()
    app.alpha_composite(Image.fromarray(a), (bx0, by0))
    ImageDraw.Draw(app).rectangle([bx0, by0, bx1, by1], outline=(255, 255, 255, 255), width=2)
    # Üç çözünürlük, aynı nokta (üs)
    thumbs = []
    for key in ("viking", "ctx", "hirise"):
        name, _, _, zz = TREK_LAYERS[key]
        dd = 180 / 2 ** zz
        t, u, n = trek_tile(key, zz, int((lon + 180) // dd), int((90 - lat) // dd))
        thumbs.append(f'<figure class="tile"><img src="{uri_img(t.resize((256, 256)), q=85)}" alt="{esc(name)}"><figcaption><b>{esc(name)}</b><br>'
                      f'seviye {zz}, karo {tr(dd, 4)}° ≈ {tr(dd * P.M_PER_DEG / 1000, 2)} km, {tr(n / 1000, 0)} KB</figcaption></figure>')
    fig, ax = plt.subplots(1, 1, figsize=(5.2, 2.9))
    v = gray[~nodata]
    ax.hist(v, bins=64, color=ACC, edgecolor=SURF, linewidth=0.6)
    ax.set_title("Ham: CTX karo parlaklığı (3×3 karo)", loc="left")
    ax.set_xlabel("parlaklık"), ax.set_ylabel("piksel sayısı")
    ax.grid(axis="y", color=GRID, lw=0.6), ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    fig.tight_layout()
    hist = uri_fig(fig)
    head = facts({"Ad": "NASA/JPL Mars Trek WMTS karoları (taban harita)", "Kaynak": link(TREK) + "<br>ör. " + link(sample_url),
                  "Format": "WMTS karosu, 256 × 256 PNG/JPG, coğrafi ızgara (seviye 0 = 2 × 1 karo)",
                  "Boyut": f"indirilmez, tarayıcı gerektikçe çeker; örnek CTX karosu ortalama {tr(np.mean(sizes) / 1000, 0)} KB",
                  "Kayıt": "yok (küresel karo servisi)", "Çözünürlük": "Viking 232 m, CTX 6 m, HiRISE 25 cm (katman adlarından); "
                  f"seviye {z}'da ekranda {tr(m_per_px, 1)} m/piksel", "Projeksiyon": "Equirectangular (Eqc_latTs0_lon0; katman adlarından)"})
    body = (f'<div class="pair"><figure class="half"><img src="{uri_img(mos.convert("RGB"), q=82)}" alt="Mars Trek ham"><figcaption>Ham: CTX Jezero mozaiği, '
            f'seviye {z}, 3 × 3 karo, üs ortada</figcaption></figure><figure class="half"><img src="{uri_img(app.convert("RGB"), q=82)}" alt="Uygulamada">'
            '<figcaption>Uygulamada: aynı karolar + bizim geçilebilirlik katmanımız (beyaz çerçeve = çalışma alanı, saydamlık 0,6)</figcaption></figure></div>'
            f'<div class="tiles">{"".join(thumbs)}</div>'
            f'<figure><img src="{hist}" alt="Mars Trek histogram" style="max-width:min(560px,100%)"></figure>'
            + stat_table([stat_row("CTX karoları, parlaklık (NoData hariç)", v)],
                         f"3 × 3 CTX karosunda %{tr(100 * nodata.mean(), 2)} (saydam ya da 0). "
                         "Sonra histogramı yok: karoların değerlerini değiştirmiyoruz, yalnızca gösteriyoruz."))
    dropped = "Hiçbir şey indirilmiyor ya da atılmıyor; yalnızca ekranda görünen karolar çekiliyor. HiRISE karoları uzak görünümde gizli (seviye 15'ten önce), çünkü yamalı tonlar genel bakışı bozuyor."
    clean = "Yok. Cesium <code>GeographicTilingScheme</code> Mars elipsoidiyle (3396,19 / 3376,2 km) karoları küreye seriyor."
    where = ("<code>web/app.js</code> (<code>BASE_LAYERS</code>, <code>DETAIL_LAYERS</code>, Gözde): Viking ya da MOLA taban, CTX ve HiRISE ayrıntı katmanı. "
             "Hesaplara girmiyor (ağırlık yok); bizim katmanlarımızın altındaki arka plan. Kredi metin olarak: \"NASA/JPL-Caltech/USGS Mars Trek\".")
    summary = "Mars Trek, hesaplara girmeyen ama astronotun haritayı tanımasını sağlayan gerçek Mars görüntüsü; bizim katmanlarımız bunun üstüne seriliyor."
    return section("trek", head_title("TREK"), head, body, dropped, clean, where, summary)


# ---- Özet tablo -----------------------------------------------------------------------------
def summary_table():
    s = STATS
    d7 = E7["per_region"]
    tot_api = sum(v.get("api_images", 0) for k, v in d7.items() if not k.endswith("_tried")) + \
        sum(x.get("api_images", 0) for k, v in d7.items() if k.endswith("_tried") for x in v)
    n_pins = sum(1 for r in BR.REGIONS if r["pos"][0] == "sol")
    rows = [
        ("d1", "D1 Perseverance konumları", f"{size_txt(RAW / 'M20_waypoints.json')} · {tr(s['D1']['features'])} nokta × {tr(s['D1']['fields_total'])} alan",
         f"{tr(s['D1']['fields_total'] - len(s['D1']['fields_used']))} alan", f"{n_pins} pin konumu", "Sol eşleme (≤ olay Sol'ü)", "build_regions → regions.json"),
        ("d2", "D2 Sürüş izi", f"{size_txt(RAW / 'M20_traverse.json')} · {tr(s['D2']['features'])} çizgi, {tr(s['D2']['vertices'])} köşe",
         f"{tr(s['D2']['vertices'] - s['D2']['vertices_inside'])} köşe (alan dışı)", f"{tr(E10V['route_cells_total'])} rota hücresi", "Rasterize (10 m adım)", "validate.py: doğrulama (AUC)"),
        ("d3", "D3 Ingenuity uçuşları", f"{size_txt(RAW / 'm20_heli_flight_path.json')} · {tr(s['D3']['features'])} uçuş", f"{tr(s['D3']['features'] - 1)} uçuş",
         "1 tarih pini", "Seçim (Uçuş 1 kalkışı)", "build_regions → regions.json"),
        ("d4", "D4 THEMIS termal", f"{size_txt(RAW / 'Jezero_Thermal_Inertia_v1.tiff')} · {tr(s['D4']['pixels'])} px, 100 m",
         f"{tr(s['D4']['dropped_outside'])} px (alan dışı, {tr(s['D4']['nodata'])} NoData dahil); {tr(s['D4']['clipped_low'] + s['D4']['clipped_high'])} px kırpıldı",
         "1024² + 256², 0–1", "Reprojeksiyon, bilinear, %2–98", "Füzyon 0,2 · (1 − termal)"),
        ("d5", "D5 CTX DEM", f"{size_txt(RAW / 'M20_JezeroCrater_CTXDEM_20m.tif')} · {tr(s['D5']['pixels'])} px, 20 m",
         f"{tr(s['D5']['dropped_outside'])} px (alan dışı), {tr(s['D5']['nodata'])} NoData", "1024² + 256² (yükseklik, eğim)", "20 m'de eğim, average",
         "Füzyon 0,4 · eğim; Tobler; geçilmez > 25°"),
        ("d6", "D6 SIM 3464 jeoloji", f"{size_txt(RAW / 'sim3464_database.zip')} · {tr(s['D6']['polygons'])} poligon, {len(s['D6']['gdb_layers'])} katman",
         f"{tr(s['D6']['zip_dropped_macosx_lock'])} sistem dosyası, {len(s['D6']['gdb_layers']) - 1} katman, {tr(s['D6']['polygons_dropped_outside'])} poligon; 2 kaynak hatası düzeltildi",
         f"{tr(s['D6']['polygons_in_area'])} poligon → 1024²", "Rasterize, katsayı tablosu", "Füzyon 0,25 · kum + 0,15 · kaya; kum tuzağı"),
        ("d7", "D7 Ham görüntüler (API)", f"{tr(tot_api)} görüntü kaydı (7 Sol)", f"{tr(tot_api - E7['photos'])} kayıt", f"{tr(E7['photos'])} fotoğraf (800 px)",
         "Kural tabanlı huni + kenar şiddeti", "build_regions → nokta kartı"),
        ("d8", "D8 HiRISE 25 cm", f"{size_txt(RAW / 'MSR_TRN_HiRISE_mosaics.zip')} zip · {tr(E5['ortho']['width'])} × {tr(E5['ortho']['height'])} px",
         f"zipte ortogörüntü dışı her şey; {tr(E5['screen']['dropped_nodata'])} NoData + {tr(E5['screen']['dropped_flat'])} dokusuz karo",
         f"{tr(E6S['tiles'])} etiketli karo; {tr(E10I['tiles_inferred'])} karoda çıkarım", "Karolama, germe %0,5–99,5, en uzak nokta",
         "YOLO → kum_ml, kaya_ml (füzyonda yarı ağırlık)"),
        ("trek", "Mars Trek karoları", "servis (indirilmez)", "yok", "ekranda taban harita", "yok (olduğu gibi)", "app.js arka plan"),
    ]
    h = ['<div class="tw"><table class="summary"><thead><tr><th>Veri seti</th><th>Ham boyut</th><th>Atılan</th><th>Son boyut</th>'
         '<th>Yöntem</th><th>Kullanıldığı yer</th></tr></thead><tbody>']
    for sid, *cells in rows:
        h.append(f'<tr><td><a href="#{sid}">{esc(cells[0])}</a></td>' + "".join(f"<td>{esc(c)}</td>" for c in cells[1:]) + "</tr>")
    h.append("</tbody></table></div>")
    return "".join(h)


CSS = f"""
:root {{ --bg:{BG}; --surf:{SURF}; --ink:{INK}; --muted:{MUTED}; --grid:{GRID}; --acc:{ACC};
  --used:#3ecf8e; --used-bg:rgba(62,207,142,.13); --unused:#7d756e; --unused-bg:rgba(255,255,255,.025); }}
* {{ box-sizing:border-box; }}
html {{ background:var(--bg); }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 "Segoe UI", system-ui, -apple-system, sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:24px 16px 80px; }}
h1 {{ font-size:28px; margin:8px 0 4px; }} h1 span {{ color:var(--acc); }}
h2 {{ font-size:22px; margin:0 0 14px; padding-top:8px; border-top:2px solid var(--acc); }}
h3 {{ font-size:16px; margin:22px 0 8px; }} h4 {{ margin:0 0 6px; font-size:14px; color:var(--muted); font-weight:600; }}
p {{ margin:8px 0; }} a {{ color:#ffb27f; word-break:break-all; }}
code {{ font:13px Consolas, monospace; background:#221c17; padding:1px 5px; border-radius:4px; }}
code.u {{ color:var(--used); background:var(--used-bg); }} code.n {{ color:#b7aea6; }}
.lead {{ color:var(--muted); max-width:820px; }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; margin:12px 0 20px; font-size:14px; }}
.legend span {{ padding:3px 10px; border-radius:6px; }}
.lg-u {{ background:var(--used-bg); color:var(--used); border:1px solid var(--used); }}
.lg-n {{ background:var(--unused-bg); color:var(--unused); border:1px solid #3b352f; }}
nav {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 28px; }}
nav a {{ text-decoration:none; color:var(--ink); background:var(--surf); border:1px solid var(--grid); padding:4px 10px; border-radius:16px; font-size:13px; }}
section {{ background:var(--surf); border-radius:12px; padding:20px 20px 16px; margin:0 0 28px; }}
.tw {{ overflow-x:auto; margin:10px 0; }}
table {{ border-collapse:collapse; font-size:13px; }}
th, td {{ padding:6px 9px; border-bottom:1px solid var(--grid); text-align:left; vertical-align:top; }}
table.summary {{ width:100%; background:var(--surf); border-radius:10px; }} table.summary th {{ color:var(--muted); font-weight:600; }}
table.summary td:first-child {{ min-width:150px; }} table.summary a {{ word-break:normal; }}
table.data td {{ white-space:nowrap; font-family:Consolas, monospace; font-size:12px; }}
table.data th.u {{ background:var(--used-bg); color:var(--used); border-bottom:2px solid var(--used); }}
table.data td.u {{ background:var(--used-bg); color:#c9f5df; }}
table.data th.n {{ color:var(--unused); }} table.data td.n {{ color:var(--unused); background:var(--unused-bg); }}
table.stat td:not(:first-child), table.stat th:not(:first-child) {{ text-align:right; font-variant-numeric:tabular-nums; }}
dl.facts {{ display:grid; grid-template-columns:max-content minmax(0,1fr); gap:4px 16px; margin:0 0 12px; font-size:14px; }}
dl.facts dt {{ color:var(--muted); }} dl.facts dd {{ margin:0; }}
.notes {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; font-size:13.5px; }}
.notes code, .rows code, .lead code, dd code {{ overflow-wrap:anywhere; }}
section, .tw {{ min-width:0; max-width:100%; }}
.notes ul {{ margin:0; padding-left:18px; }} .notes li {{ margin:3px 0; }}
figure {{ margin:14px 0; }} figure img {{ max-width:100%; height:auto; border-radius:8px; display:block; }}
figcaption, .cap {{ color:var(--muted); font-size:13px; margin-top:4px; }}
.pair {{ display:flex; gap:16px; flex-wrap:wrap; }} .pair .half {{ flex:1 1 300px; margin:8px 0; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:14px; }}
.tile img {{ width:100%; }}
.rows {{ border-left:3px solid var(--acc); padding:2px 0 2px 14px; margin:16px 0 8px; }}
.nod {{ font-size:14px; }}
.sum {{ font-size:16px; font-weight:600; color:#ffd2b3; margin-top:12px; }}
footer {{ color:var(--muted); font-size:13px; }}
@media (max-width:720px) {{ .notes {{ grid-template-columns:minmax(0,1fr); }} dl.facts {{ grid-template-columns:minmax(0,1fr); }} section {{ padding:16px 12px; }} dl.facts dt {{ margin-top:6px; }} }}
"""


def main():
    L = np.load(PROC / "layers_1024.npz")
    parts = []
    for name, fn in (("D1", lambda: geojson_section("D1")), ("D2", lambda: geojson_section("D2")), ("D3", lambda: geojson_section("D3")),
                     ("D4", lambda: d4_section(L)), ("D5", lambda: d5_section(L)), ("D6", lambda: d6_section(L)),
                     ("D7", d7_section), ("D8", d8_section), ("Mars Trek", trek_section)):
        print("  ", name, flush=True)
        parts.append(fn())
    nav = "".join(f'<a href="#{s}">{t}</a>' for s, t in (("d1", "D1"), ("d2", "D2"), ("d3", "D3"), ("d4", "D4"), ("d5", "D5"),
                                                          ("d6", "D6"), ("d7", "D7"), ("d8", "D8"), ("trek", "Mars Trek")))
    doc = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarsTrail Veri Örnekleri</title><style>{CSS}</style></head>
<body><main>
<h1>MarsTrail <span>·</span> Veri örnekleri</h1>
<p class="lead">Her veri setinin ham hali, neyi kullanıp neyi attığımız ve projede nereye gittiği. Sayılar bu sayfayı üreten betiğin
(<code>scripts/make_data_examples.py</code>) çalıştığı anda dosyalardan ölçüldü ya da veri hattı betiklerinin JSON çıktılarından okundu;
bulunamayan değer "yok" yazıldı. Ayrıntılı adımlar: <code>docs/DATA_PIPELINE.md</code>. Ortak hedef sistem: Mars 2000 küresi üzerinde derece,
doğu pozitif; çalışma alanı {tr(P.BOUNDS['west'], 2)}–{tr(P.BOUNDS['east'], 2)}°D, {tr(P.BOUNDS['south'], 3)}–{tr(P.BOUNDS['north'], 3)}°K.</p>
<div class="legend"><span class="lg-u">yeşil = kullandığımız alan</span><span class="lg-n">gri = kullanmadığımız alan</span></div>
<h2 style="border:0">Özet</h2>{summary_table()}
<nav>{nav}</nav>
{''.join(parts)}
<footer>Veri: NASA/JPL-Caltech, USGS, ASU (THEMIS), University of Arizona (HiRISE). MarsTrail · NASA Space Apps Konya 2026.</footer>
</main></body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
