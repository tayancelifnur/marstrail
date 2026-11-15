"""
MarsTrail – sahte veri üretici (E1).

Gözde gerçek veriyi beklemeden arayüzü kurabilsin diye web/data/ altına
veri sözleşmesine uygun SAHTE dosyalar yazar. Dosya adları ve alanlar
gerçek dosyalarla aynıdır; E3 (layers, grid) ve E7 (regions, stories, poi)
bu dosyaların üzerine gerçeklerini yazar.

Çalıştır:  venv\\Scripts\\python scripts\\make_dummies.py

Koordinatlar: derece, doğu pozitif, boylam -180..180.
UYARI: Buradaki bütün sayılar (koordinat, Sol, yükseklik, hava) yaklaşık /
varsayımdır, sadece arayüz geliştirmek içindir.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "data"
LAYERS_DIR = OUT / "layers"
PHOTOS_DIR = OUT / "photos"

# Jezero çalışma alanı (yaklaşık): iniş alanı, delta önü, Three Forks, Neretva Vallis
BOUNDS = {"west": 77.36, "south": 18.38, "east": 77.51, "north": 18.52}
BBOX = [BOUNDS["west"], BOUNDS["south"], BOUNDS["east"], BOUNDS["north"]]
N = 256  # grid boyutu (256x256)

MARS_KM_PER_DEG = 2 * math.pi * 3389.5 / 360  # ~59.16 km / derece (Mars yarıçapı 3389.5 km)

rng = np.random.default_rng(42)


def write_json(name, obj, compact=False):
    path = OUT / name
    # Koruma: gerçek veri (prep_layers.py, build_regions.py çıktısı) sahteyle ezilmesin.
    if path.exists() and '"dummy"' not in path.read_text(encoding="utf-8")[:20000]:
        print(f"  ATLANDI {path.relative_to(ROOT)} (gerçek veri var)")
        return
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size / 1024:.0f} KB)")


# ---------------------------------------------------------------------------
# 1) Sahte arazi: krater tabanı + batıda delta tümseği + kum alanı
# ---------------------------------------------------------------------------
def lonlat_axes():
    lons = np.linspace(BOUNDS["west"], BOUNDS["east"], N)
    lats = np.linspace(BOUNDS["north"], BOUNDS["south"], N)  # satır 0 = kuzey
    return np.meshgrid(lons, lats)


def smooth_noise(size, scale):
    """Kaba gürültüyü büyüterek yumuşak arazi dokusu üretir."""
    coarse = rng.standard_normal((size // scale + 2, size // scale + 2)).astype(np.float32)
    img = Image.fromarray(coarse).resize((size, size), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32)


def gauss(LON, LAT, lon0, lat0, sx, sy):
    return np.exp(-(((LON - lon0) / sx) ** 2 + ((LAT - lat0) / sy) ** 2))


def make_terrain():
    LON, LAT = lonlat_axes()
    elev = np.full((N, N), -2600.0, dtype=np.float32)  # krater tabanı ~ -2600 m (varsayım)
    elev += 120 * gauss(LON, LAT, 77.38, 18.47, 0.04, 0.05)  # delta tümseği (batı)
    elev += 60 * np.clip((77.40 - LON) / 0.04, 0, 1)  # batıya doğru yükselen kenar
    elev += 8 * smooth_noise(N, 16) + 2 * smooth_noise(N, 4)
    # birkaç küçük krater çukuru
    for lon0, lat0, r in [(77.47, 18.42, 0.004), (77.43, 18.49, 0.006), (77.49, 18.47, 0.003)]:
        d = np.hypot((LON - lon0) / r, (LAT - lat0) / r)
        elev -= 90 * np.clip(1 - d, 0, 1) ** 2  # derin çukur: iç duvarlar >25° (geçilmez test alanı)
        elev += 10 * np.exp(-((d - 1) ** 2) / 0.05)  # kenar sırtı
    # Delta önü yamacı: ~120 m'lik dik basamak (rota bunun etrafından dolanmalı)
    scarp_dist = (LON - (77.395 + 0.25 * (LAT - 18.45))) / 0.0004
    scarp_mask = gauss(LON, LAT, 77.395, 18.455, 0.03, 0.012)
    elev += 120 * scarp_mask * (1 / (1 + np.exp(scarp_dist)))
    # Séítah benzeri sırtlı alan (üssün GB'si): ~200 m dalga boylu, 30 m genlikli sırtlar, yamaçları >25°
    ridge_mask = np.clip(1.6 * gauss(LON, LAT, 77.435, 18.425, 0.010, 0.006), 0, 1)
    elev += 30 * ridge_mask * np.sin((LON * 0.95 + LAT * 0.3) * MARS_KM_PER_DEG * 1000 * 2 * np.pi / 200)

    cell_m = (BOUNDS["north"] - BOUNDS["south"]) * MARS_KM_PER_DEG * 1000 / N
    gy, gx = np.gradient(elev, cell_m)
    slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))

    # Termal eylemsizlik (0-1, düşük = gevşek kum). Kum alanı iniş alanının GB'sinde.
    sand = gauss(LON, LAT, 77.43, 18.43, 0.012, 0.008) + 0.6 * gauss(LON, LAT, 77.40, 18.50, 0.01, 0.006)
    sand = np.clip(sand, 0, 1)
    thermal = np.clip(0.65 + 0.12 * smooth_noise(N, 32) - 0.55 * sand, 0, 1)

    # Sahte kaya yoğunluğu (YOLO yerine)
    rock = np.clip(0.15 + 0.15 * smooth_noise(N, 8) + 0.5 * gauss(LON, LAT, 77.38, 18.47, 0.02, 0.02), 0, 1)

    # Sahte jeoloji birimi indeksi (0..4)
    geo = np.zeros((N, N), dtype=np.int32)          # 0: krater tabanı
    geo[gauss(LON, LAT, 77.38, 18.47, 0.04, 0.05) > 0.4] = 1  # 1: delta
    geo[LON < 77.37] = 2                            # 2: krater kenarı
    geo[sand > 0.4] = 3                             # 3: eolyen (kum)
    geo[(geo == 0) & (smooth_noise(N, 32) > 1.0)] = 4  # 4: Séítah benzeri kaya birimi

    return dict(elev=elev, slope=slope_deg, thermal=thermal, sand=sand, rock=rock, geo=geo, cell_m=cell_m)


def traversability(t):
    """PLAN.md bölüm 5 formülü (ağırlıklar varsayım)."""
    slope_risk = np.clip(t["slope"] / 25.0, 0, 1)
    score = 0.4 * slope_risk + 0.25 * t["sand"] + 0.15 * t["rock"] + 0.2 * (1 - t["thermal"])
    return np.clip(score, 0, 1)


def cell_cost_minutes(t, score):
    """Hücre maliyeti (dk) = hücre_boyu / v × (1 + 2·skor). Tobler, Mars+giysi ×0.6, yük 0 kg."""
    tan = np.tan(np.radians(t["slope"]))
    v_kmh = 6 * np.exp(-3.5 * np.abs(tan + 0.05)) * 0.6
    v_m_per_min = v_kmh * 1000 / 60
    return t["cell_m"] / v_m_per_min * (1 + 2 * score)


# ---------------------------------------------------------------------------
# 2) Katman PNG'leri (RGBA, şeffaf)
# ---------------------------------------------------------------------------
def ramp(values, stops, alpha=170):
    """values (0-1) -> RGBA; stops = [(konum, (r,g,b)), ...]"""
    v = np.clip(values, 0, 1)
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    rgb = np.stack([np.interp(v, pos, cols[:, i]) for i in range(3)], axis=-1)
    a = np.full(v.shape + (1,), alpha, dtype=np.float32)
    return np.concatenate([rgb, a], axis=-1).astype(np.uint8)


GREEN_RED = [(0, (46, 204, 113)), (0.5, (241, 196, 15)), (1, (231, 76, 60))]
GEO_COLORS = [(181, 137, 98), (93, 156, 236), (120, 94, 74), (240, 200, 120), (155, 89, 182)]
GEO_NAMES = ["Krater tabanı", "Delta", "Krater kenarı", "Eolyen birim (kum)", "Kayalık birim"]
GEO_WALK = [0.9, 0.7, 0.4, 0.3, 0.6]  # yürünebilirlik katsayısı (varsayım)


def save_png(name, rgba):
    path = LAYERS_DIR / name
    Image.fromarray(rgba, "RGBA").resize((512, 512), Image.NEAREST).save(path)
    print(f"  {path.relative_to(ROOT)}")


def make_layers(t, score):
    save_png("slope.png", ramp(t["slope"] / 25.0, GREEN_RED))
    save_png("thermal.png", ramp(t["thermal"], [(0, (230, 126, 34)), (1, (52, 73, 94))]))
    geo_rgba = np.zeros((N, N, 4), dtype=np.uint8)
    for i, c in enumerate(GEO_COLORS):
        geo_rgba[t["geo"] == i] = (*c, 150)
    save_png("geology.png", geo_rgba)
    hazard = np.clip(0.6 * t["sand"] + 0.6 * t["rock"] - 0.2, 0, 1)
    hz = ramp(hazard, [(0, (0, 0, 0)), (1, (255, 40, 40))], alpha=0)
    hz[..., 3] = (hazard * 220).astype(np.uint8)  # düşük tehlike şeffaf
    save_png("hazard_ml.png", hz)
    save_png("traversability.png", ramp(score, GREEN_RED))

    common = {"bbox": BBOX, "dummy": True}
    layers = [
        {"id": "slope", "name": "Eğim", "file": "layers/slope.png", "default_opacity": 0.6,
         "legend": [{"color": "#2ecc71", "label": "0°"}, {"color": "#f1c40f", "label": "12°"},
                    {"color": "#e74c3c", "label": "≥25° (geçilmez)"}],
         "source": "CTX DEM 20 m (USGS) – şimdilik sahte", **common},
        {"id": "thermal", "name": "Termal eylemsizlik (zemin gevşekliği)", "file": "layers/thermal.png",
         "default_opacity": 0.6,
         "legend": [{"color": "#e67e22", "label": "Düşük – gevşek kum/toz"}, {"color": "#34495e", "label": "Yüksek – sert kaya"}],
         "source": "THEMIS, Jezero mozaiği – şimdilik sahte", **common},
        {"id": "geology", "name": "Jeoloji birimleri", "file": "layers/geology.png", "default_opacity": 0.5,
         "legend": [{"color": "#%02x%02x%02x" % c, "label": f"{n} (yürünebilirlik {w})"}
                    for c, n, w in zip(GEO_COLORS, GEO_NAMES, GEO_WALK)],
         "source": "USGS SIM 3464 – şimdilik sahte", **common},
        {"id": "hazard_ml", "name": "YOLO: kaya ve kum dalgası", "file": "layers/hazard_ml.png",
         "default_opacity": 0.8,
         "legend": [{"color": "#ff2828", "label": "Yüksek kaya/kum yoğunluğu"}],
         "source": "Kendi YOLOv8 modelimiz (HiRISE) – şimdilik sahte", **common},
        {"id": "traversability", "name": "Birleşik geçilebilirlik", "file": "layers/traversability.png",
         "default_opacity": 0.6,
         "legend": [{"color": "#2ecc71", "label": "Kolay"}, {"color": "#f1c40f", "label": "Orta"},
                    {"color": "#e74c3c", "label": "Zor / geçilmez (>0,8)"}],
         "source": "0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1−termal) – şimdilik sahte", **common},
    ]
    write_json("layers.json", layers)


def make_grid(t, score):
    cost = cell_cost_minutes(t, score)
    blocked = (t["slope"] > 25) | (score > 0.8)
    grid = {
        "dummy": True,
        "width": N,
        "height": N,
        "bounds": BOUNDS,
        "cell_size_m": round(float(t["cell_m"]), 2),
        "order": "row-major; satır 0 = kuzey, sütun 0 = batı; indeks = satır*width + sütun",
        "units": {"elev": "m", "cost": "dk/hücre (yük 0 kg, nabız 90)", "blocked": "0/1"},
        "elev": np.round(t["elev"]).astype(int).ravel().tolist(),
        "cost": np.round(cost, 2).ravel().tolist(),
        "blocked": blocked.astype(int).ravel().tolist(),
    }
    write_json("grid.json", grid, compact=True)


# ---------------------------------------------------------------------------
# 3) Noktalar, hikâyeler, astronotlar, hava
# ---------------------------------------------------------------------------
PLACEHOLDER = "photos/placeholder.jpg"


def photo(sol, caption):
    return {"url": PLACEHOLDER, "sol": sol, "camera": "NAVCAM_LEFT", "caption": caption, "dummy": True}


REGIONS = [
    {"id": "base", "name": "Üs – Octavia E. Butler iniş alanı", "lat": 18.4447, "lon": 77.4508,
     "science_value": 2, "summary": "Perseverance'ın iniş noktası; MarsTrail habitatının yeri.",
     "hazards": [], "missions": ["Mars 2020 / Perseverance"], "sol": 0,
     "history": [{"date": "2021-02-18", "event": "Perseverance Jezero'ya indi", "source": "https://science.nasa.gov/mission/mars-2020-perseverance/location-map/"}]},
    {"id": "jezero_lake", "name": "Jezero antik gölü", "lat": 18.45, "lon": 77.42,
     "science_value": 5, "summary": "Yaklaşık 3,5 milyar yıl önce göl olan krater tabanı.",
     "hazards": ["gevşek toz"], "missions": ["MRO", "Mars 2020"], "sol": None,
     "history": [{"date": "2005", "event": "Antik göl yörünge görüntülerinden tanımlandı (Caleb Fassett)", "source": "https://www.astronomy.com/?p=40600"},
                 {"date": "2020-12-02", "event": "USGS jeolojik haritası (SIM 3464) yayımlandı", "source": "https://www.usgs.gov/maps/geologic-map-jezero-crater-and-nili-planum-region-mars"}]},
    {"id": "airfield", "name": "Ingenuity uçuş alanı (Wright Brothers Field)", "lat": 18.4446, "lon": 77.4512,
     "science_value": 3, "summary": "Başka bir gezegende ilk güçlü, kontrollü uçuşun yapıldığı alan.",
     "hazards": [], "missions": ["Ingenuity"], "sol": 58,
     "history": [{"date": "2021-04-19", "event": "Ingenuity ilk uçuşunu yaptı", "source": "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json"}]},
    {"id": "rochette", "name": "Rochette kayası", "lat": 18.4370, "lon": 77.4440,
     "science_value": 4, "summary": "İlk başarılı kaya numunesinin alındığı yer.",
     "hazards": ["kayalık zemin"], "missions": ["Mars 2020"], "sol": 190,
     "history": [{"date": "2021-09-01", "event": "İlk başarılı kaya numunesi", "source": "https://kaweah.freedombox.rocks/kiwix/wikipedia_en_all_maxi_2023-10/Timeline_of_Mars_2020"}]},
    {"id": "delta_front", "name": "Delta önü (Kodiak / Hawksbill Gap)", "lat": 18.4560, "lon": 77.4040,
     "science_value": 5, "summary": "Göl ve nehir deltası; ani sel izleri.",
     "hazards": ["eğim", "kum dalgası"], "missions": ["Mars 2020"], "sol": 223,
     "history": [{"date": "2021-10-07", "event": "Rover görüntüleri göl deltasını ve ani sel izlerini doğruladı (Science)", "source": "https://earthsky.org/space/ancient-martian-lake-delta-floods-perseverance/"}]},
    {"id": "three_forks", "name": "Three Forks numune deposu", "lat": 18.4530, "lon": 77.4150,
     "science_value": 4, "summary": "Başka bir gezegendeki ilk numune deposu; 10 tüp bırakıldı.",
     "hazards": [], "missions": ["Mars 2020", "Mars Sample Return (plan)"], "sol": 653,
     "history": [{"date": "2022-12-21", "event": "İlk tüp bırakıldı", "source": "https://spaceodysseyhub.com/replays/perseverance"},
                 {"date": "2023-01-28", "event": "Depo tamamlandı (10 tüp)", "source": "https://spaceodysseyhub.com/replays/perseverance"}]},
    {"id": "cheyava_falls", "name": "Cheyava Falls (Neretva Vallis)", "lat": 18.4880, "lon": 77.3820,
     "science_value": 5, "summary": "\"Leopar benekli\" kaya; olası biyoimza.",
     "hazards": ["dik kanal duvarı"], "missions": ["Mars 2020"], "sol": 1212,
     "history": [{"date": "2024-07-18", "event": "\"Leopar benekli\" kaya bulundu; olası biyoimza", "source": "https://skyatnightmagazine.com/space-missions/perseverance-jezero-crater"}]},
]


def make_regions(t):
    rows = []
    for r in REGIONS:
        col = int(round((r["lon"] - BOUNDS["west"]) / (BOUNDS["east"] - BOUNDS["west"]) * (N - 1)))
        row = int(round((BOUNDS["north"] - r["lat"]) / (BOUNDS["north"] - BOUNDS["south"]) * (N - 1)))
        out = {**r, "elevation_m": int(round(float(t["elev"][row, col]))),
               "photos": [photo(r["sol"], f"{r['name']} – Sol {r['sol']} (sahte)")] if r["sol"] is not None else [],
               "dummy": True}
        rows.append(out)
    write_json("regions.json", rows)
    return rows


def make_poi(regions):
    feats = []
    for r in regions:
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": {"id": r["id"], "name": r["name"],
                                     "type": "habitat" if r["id"] == "base" else "science",
                                     "region_id": r["id"]}})
    # Kum tehlikesi: haritadaki kum alanı, Opportunity/Spirit hikâyelerine bağlı
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [77.4300, 18.4300]},
                  "properties": {"id": "sand_field", "name": "Kum alanı (eolyen birim)", "type": "hazard",
                                 "story_ids": ["opportunity", "spirit"],
                                 "note": "Opportunity buna benzer bir kum dalgasında 5 hafta kaldı."}})
    write_json("poi.geojson", {"type": "FeatureCollection", "dummy": True, "features": feats})


STORIES = [
    {"id": "apollo14", "title": "Apollo 14 – Cone Krateri", "date": "1971-02-06", "body": "Shepard ve Mitchell Cone Krateri'nde konumlarını kaybetti; Shepard'ın nabzı 150'ye çıktı. Oksijen ve dönüş yolu nedeniyle arama durduruldu. LRO uydusunun 2009 görüntüsü, kenara ~30 m kala döndüklerini gösterdi (LROC/ASU).",
     "location_text": "Ay, Fra Mauro", "lesson": "Konum, nabız ve dönüş sınırı", "layer": None,
     "source": "https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/"},
    {"id": "opportunity", "title": "Opportunity – Purgatory Kumulu", "date": "2005-04-26", "body": "~30 cm yüksekliğinde bir kum dalgasında beş haftadan fazla mahsur kaldı.",
     "location_text": "Meridiani Planum (Jezero'da değil; ~2°K, 354°D)", "lesson": "Küçük kum dalgaları bile tuzak olabilir", "layer": "hazard_ml",
     "source": "https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune"},
    {"id": "spirit", "title": "Spirit – Troy", "date": "2009-05", "body": "Sert kabuğun altındaki yumuşak kuma gömüldü ve görevini kaybetti.",
     "location_text": "Gusev Krateri (Jezero'da değil; ~14,6°G, 175,5°D)", "lesson": "Düşük termal eylemsizlik = batma riski", "layer": "thermal",
     "source": "https://www.space.com/18766-spirit-rover.html"},
]


def make_stories():
    write_json("stories.json", [{**s, "dummy": True} for s in STORIES])


def make_astronauts():
    base = next(r for r in REGIONS if r["id"] == "base")
    common = {"suit": "xEMU (varsayım)", "o2_capacity_min": 480, "position": {"lat": base["lat"], "lon": base["lon"]}}
    astronauts = [
        {"id": "ayse", "name": "Ayşe", "mass_kg": 62, "o2_min": 480, "battery_pct": 100, "water_pct": 100,
         "heart_rate": 85, "load_kg": 6, "radiation_msv": 0.3, "role": "Jeolog – delta numunesi", **common},
        {"id": "ali", "name": "Ali", "mass_kg": 78, "o2_min": 480, "battery_pct": 100, "water_pct": 100,
         "heart_rate": 80, "load_kg": 4, "radiation_msv": 0.3, "role": "Mühendis – destek", **common},
    ]
    write_json("astronauts.json", astronauts)


def make_conditions():
    rows = []
    for sol in range(28, 41):  # demo Sol 34 çevresi
        tmin = -83 + rng.normal(0, 2)
        rows.append({"sol": sol, "temp_min_c": round(tmin, 1), "temp_max_c": round(tmin + 60 + rng.normal(0, 3), 1),
                     "pressure_pa": round(720 + rng.normal(0, 8)), "wind_ms": round(abs(rng.normal(5, 2)), 1),
                     "dust_tau": round(0.45 + abs(rng.normal(0, 0.08)), 2),
                     "sunrise_lmst": "05:52", "sunset_lmst": "18:08", "dummy": True})
    write_json("conditions.json", rows)


def make_placeholder_photo():
    img = Image.new("RGB", (640, 480), (150, 90, 60))
    d = ImageDraw.Draw(img)
    for y in range(300, 480, 6):
        d.line([(0, y), (640, y + 10)], fill=(170, 105, 70))
    d.text((240, 220), "SAHTE FOTOGRAF", fill=(255, 240, 220))
    path = PHOTOS_DIR / "placeholder.jpg"
    img.save(path, quality=80)
    print(f"  {path.relative_to(ROOT)}")


def is_real(name):
    path = OUT / name
    return path.exists() and '"dummy"' not in path.read_text(encoding="utf-8")[:20000]


def main():
    for d in (OUT, LAYERS_DIR, PHOTOS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    print("Sahte veri yazılıyor:")
    t = make_terrain()
    score = traversability(t)
    if is_real("layers.json"):
        print("  ATLANDI layers/*.png ve layers.json (gerçek veri var)")
    else:
        make_layers(t, score)
    make_grid(t, score)
    regions = make_regions(t)
    make_poi(regions)
    make_stories()
    make_astronauts()
    make_conditions()
    if not is_real("regions.json"):
        make_placeholder_photo()
    print("Bitti.")


if __name__ == "__main__":
    main()
