"""
MarsTrail – nokta kartları ve tarihçeler (E7).

Girdi:
  GOREV_KARTLARI.md bölüm 3 tablosu (aşağıda EVENTS olarak kodlandı)
  D1 M20_waypoints.json          → olayın Sol'ünde rover'ın konumu
  D3 m20_heli_flight_path.json   → Ingenuity Uçuş 1 kalkış noktası
  D5 CTX DEM, D6 jeoloji, E3 katmanları → yükseklik, birim, arazi tehlikeleri
  D7 Perseverance ham görüntü API'si → o Sol'ün fotoğrafları

Çıktı:
  web/data/regions.json, poi.geojson, stories.json
  web/data/photos/*.jpg  (800 px, çevrimdışı demo için yerel kopya)
  docs/figures/e7_stats.json  (DATA_PIPELINE için sayılar)

Çalıştır:  venv\\Scripts\\python scripts\\build_regions.py
"""
import json
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402  (aynı sınırlar, birim katsayıları)

RAW = ROOT / "data" / "raw"
OUT = ROOT / "web" / "data"
PHOTOS = OUT / "photos"
FIG = ROOT / "docs" / "figures"
API = "https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&sol={sol}"
UA = {"User-Agent": "MarsTrail (NASA Space Apps)"}

# ---------------------------------------------------------------------------
# Bölüm 3 tablosu. Konum kaynağı:
#   ("sol", S)       → D1'de Sol'ü S'ye eşit ya da küçük olan son kayıt
#                      ("o gün rover nerede duruyordu"; rover numune alırken günlerce park eder)
#   ("heli", n)      → D3'te Uçuş n'in ilk noktası
#   ("fixed", lon, lat, kaynak) → yayınlanmış koordinat
# ---------------------------------------------------------------------------
REGIONS = [
    {"id": "base", "name": "Üs – Octavia E. Butler iniş alanı", "type": "habitat", "pos": ("sol", 0), "sol": 0,
     "science_value": 2, "missions": ["Mars 2020 / Perseverance"],
     "summary": "Perseverance'ın 18 Şubat 2021'de indiği nokta. MarsTrail senaryosunda habitatın yeri; bütün yürüyüşler buradan başlar ve buraya döner.",
     "history": [("2021-02-18", "Perseverance Jezero Krateri'ne indi (Sol 0).",
                  "https://science.nasa.gov/mission/mars-2020-perseverance/location-map/")]},
    {"id": "jezero", "name": "Jezero Krateri – antik göl", "type": "history",
     "pos": ("fixed", 77.58, 18.38, "Krater merkezi, yayınlanmış koordinat (18,38°K, 77,58°D)"), "sol": None,
     "science_value": 5, "missions": ["Mars Global Surveyor", "Mars Reconnaissance Orbiter", "Mars 2020"],
     "summary": "45 km çaplı krater, yaklaşık 3,5 milyar yıl önce bir göldü. Batıdan giren nehir bir delta bıraktı; Perseverance'ın iniş yeri olarak bu yüzden seçildi.",
     "history": [("2005", "Antik göl yörünge görüntülerinden ilk kez tanımlandı (Caleb Fassett).", "https://www.astronomy.com/?p=40600"),
                 ("2020-11", "Mars 2020 bilim ekibi HiRISE üzerinde 1:5000 ölçekli fotojeolojik harita yayımladı (Stack vd.).",
                  "https://dspace.mit.edu/entities/publication/592b30f4-e0c9-4caa-8f9c-2bd12ebdffe9"),
                 ("2020-12-02", "USGS jeolojik haritası SIM 3464 yayımlandı (Jezero ve Nili Planum).",
                  "https://www.usgs.gov/maps/geologic-map-jezero-crater-and-nili-planum-region-mars")]},
    {"id": "airfield", "name": "Ingenuity uçuş alanı (Wright Brothers Field)", "type": "history", "pos": ("heli", 1), "sol": 58,
     "science_value": 3, "missions": ["Ingenuity", "Mars 2020"],
     "summary": "Başka bir gezegende ilk güçlü, kontrollü uçuşun yapıldığı alan. Ingenuity 72 uçuşla rover'a keşif yaptı; Hayatta Kal modundaki İHA taramasının ilham kaynağı.",
     "history": [("2021-04-19", "Ingenuity ilk uçuşunu yaptı: Mars'ta ilk motorlu, kontrollü uçuş (Sol 58).",
                  "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json")]},
    {"id": "rochette", "name": "Rochette kayası (Citadelle)", "type": "science", "pos": ("sol", 190), "sol": 190,
     "science_value": 4, "missions": ["Mars 2020"],
     "summary": "Perseverance'ın ilk başarılı kaya numunesini aldığı yer. Krater tabanının volkanik kayaları suyla değişime uğramış.",
     "history": [("2021-09-01", "İlk başarılı kaya numunesi alındı (Sol 190).",
                  "https://kaweah.freedombox.rocks/kiwix/wikipedia_en_all_maxi_2023-10/Timeline_of_Mars_2020")]},
    # Delta önü: D1'de yükseklik Sol 415'ten sonra −2545 m'den −2520 m'ye çıkıyor (delta önüne tırmanış başlıyor).
    {"id": "delta_front", "name": "Delta önü (Hawksbill Gap yönü)", "type": "science", "pos": ("sol", 415), "sol": 415,
     "science_value": 5, "missions": ["Mars Reconnaissance Orbiter", "Mars 2020"],
     "summary": "Antik nehrin göle döküldüğü yerde biriken tortul katmanlar. Kodiak tepesinin görüntüleri deltayı ve ani sel izlerini doğruladı. Demo rotasının ilk bilim durağı.",
     "history": [("2021-10-07", "Rover görüntüleri (Kodiak) göl deltasını ve ani sel izlerini doğruladı (Science).",
                  "https://earthsky.org/space/ancient-martian-lake-delta-floods-perseverance/"),
                 ("SOL", "Perseverance delta önüne ulaştı ve tırmanışa başladı (Sol 415).",
                  "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json")]},
    {"id": "three_forks", "name": "Three Forks numune deposu", "type": "science", "pos": ("sol", 653), "sol": 653,
     "science_value": 4, "missions": ["Mars 2020", "Mars Sample Return (plan)"],
     "summary": "Başka bir gezegendeki ilk numune deposu: 10 tüp, ileride Dünya'ya getirilmek üzere yüzeye bırakıldı. Demo rotasının ikinci durağı.",
     "history": [("2022-12-21", "Depoya ilk tüp bırakıldı (Sol 653).", "https://spaceodysseyhub.com/replays/perseverance"),
                 ("2023-01-28", "Depo tamamlandı: 10 tüp.", "https://spaceodysseyhub.com/replays/perseverance")]},
    {"id": "cheyava_falls", "name": "Cheyava Falls (Neretva Vallis)", "type": "science", "pos": ("sol", 1212), "sol": 1212,
     "science_value": 5, "missions": ["Mars 2020"],
     "summary": "\"Leopar benekli\" kaya: antik mikrobik yaşamın olası izi (biyoimza). Üsten ~15 km uzakta; tek EVA ile gidip dönülemez, O₂ haritasında kırmızı bölgede.",
     "history": [("2024-07-18", "\"Leopar benekli\" kaya bulundu; olası biyoimza (Sol 1212).",
                  "https://skyatnightmagazine.com/space-missions/perseverance-jezero-crater")]},
]

STORIES = [
    {"id": "apollo14", "title": "Apollo 14 – Cone Krateri", "date": "1971-02-06",
     "body": "Shepard ve Mitchell, Cone Krateri'nin kenarını ararken konumlarını kaybetti. Shepard'ın nabzı 150'ye çıktı; oksijen ve dönüş yolu nedeniyle Houston aramayı durdurdu. LRO uydusunun 2009 görüntüsü, kenara ~30 m kala döndüklerini gösterdi (LROC/ASU, Saddle Rock).",
     "location_text": "Ay, Fra Mauro", "lesson": "Konum, nabız ve dönüş sınırı: MarsTrail'in O₂ bölgeleri ve dönüş noktası", "layer": None,
     "source": "https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/"},
    {"id": "opportunity", "title": "Opportunity – Purgatory Kumulu", "date": "2005-04-26",
     "body": "Opportunity ~30 cm yüksekliğinde, 2,5 m genişliğinde bir kum dalgasına saplandı ve beş haftadan fazla çıkamadı.",
     "location_text": "Meridiani Planum (Jezero'da değil)", "lesson": "Küçük kum dalgaları bile tuzaktır: eolyen birim ve YOLO kum dalgası katmanı",
     "layer": "geology", "source": "https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune"},
    {"id": "spirit", "title": "Spirit – Troy", "date": "2009-05",
     "body": "Spirit sert bir kabuğun altındaki yumuşak kuma gömüldü; aylarca süren kurtarma denemeleri başarısız oldu ve görev sona erdi.",
     "location_text": "Gusev Krateri (Jezero'da değil)", "lesson": "Düşük termal eylemsizlik = gevşek zemin = batma riski",
     "layer": "thermal", "source": "https://www.space.com/18766-spirit-rover.html"},
]

# Fotoğraf seçimi (D7). Sıra = tercih. Sol göz yeterli; sağ göz stereo tekrarıdır.
CAMS = [("NAVCAM_LEFT", "Navcam"), ("MCZ_LEFT", "Mastcam-Z"), ("FRONT_HAZCAM_LEFT_A", "Ön Hazcam")]
MIN_WIDTH = 1000             # alt kare ve küçük önizlemeleri at
MAST_EL = (-25.0, 5.0)       # manzara: daha aşağısı rover/kol, yukarısı gökyüzü
TARGET_EL = -10.0            # ufka yakın, zemini de gösteren açı tercih edilir
SOL_SEARCH = [0, 1, -1, 2, -2, 3, -3]  # o Sol'de uygun kare yoksa yakın Sol'ler
# Gökyüzü / düz kare eleme: 400×300'e küçültülmüş gri görüntüde ortalama kenar şiddeti.
# Ölçüm (E7): gökyüzü kareleri 1,4 ve 3,1; en düşük iyi kare (Three Forks tepesi) 4,2 → eşik 3,5.
MIN_EDGE = 3.5
MAX_TRIES = 8  # kamera başına indirilip denenecek en fazla aday
# İnsan kontrolüyle elenen kareler (otomatik filtreden geçip manzara göstermeyenler)
EXCLUDE = {
    "ZL0_0190_0683810387_247EBY_N0070000ZCAM05070_0340LMJ": "rover donanımı (numune/alet tablası), manzara değil",
}


def load_waypoints():
    f = json.load(open(RAW / "M20_waypoints.json", encoding="utf-8"))["features"]
    return sorted(((x["properties"]["sol"], x["properties"]["lon"], x["properties"]["lat"]) for x in f), key=lambda t: t[0])


def position(spec, wps, heli):
    kind = spec[0]
    if kind == "sol":
        s = spec[1]
        before = [w for w in wps if w[0] <= s]
        # Sol 0: D1, Sol 13'teki "Site increment, no motion" kaydıyla başlıyor = iniş noktası
        w = before[-1] if before else wps[0]
        return w[1], w[2], f"D1 Sol {w[0]} kaydı (Sol ≤ {s} olan son konum)"
    if kind == "heli":
        f = next(x for x in heli if x["properties"]["Flight"] == spec[1])
        lon, lat = f["geometry"]["coordinates"][0][:2]
        return lon, lat, f"D3 Uçuş {spec[1]} kalkış noktası"
    return spec[1], spec[2], spec[3]


class Terrain:
    """Bir noktanın arazi özellikleri: DEM yüksekliği, jeoloji birimi, 300 m içi tehlikeler."""

    def __init__(self):
        self.dem = rasterio.open(P.DEM)
        geo_crs = CRS(self.dem.crs).geodetic_crs
        self.to_dem = Transformer.from_crs(geo_crs, self.dem.crs, always_xy=True)
        self.geo = gpd.read_file(RAW / "D6_geology" / "Jezero_GeoUnits.shp")
        self.geo["name"] = self.geo["name"].replace(P.GEO_FIX)
        self.to_geo = Transformer.from_crs(geo_crs, self.geo.crs, always_xy=True)
        self.L = np.load(P.PROC / "layers_1024.npz")
        self.n = self.L["slope"].shape[0]

    def at(self, lon, lat):
        x, y = self.to_dem.transform(lon, lat)
        elev = next(self.dem.sample([(x, y)]))[0]
        elev = None if elev < -9000 else int(round(float(elev)))
        gx, gy = self.to_geo.transform(lon, lat)
        hit = self.geo[self.geo.contains(Point(gx, gy))]
        unit = hit["name"].iloc[0] if len(hit) else None
        t = {"elevation_m": elev, "geology_unit": unit,
             "geology_walkability": P.GEO_UNITS[unit][0] if unit in P.GEO_UNITS else None}
        if not (P.BBOX[0] <= lon <= P.BBOX[2] and P.BBOX[1] <= lat <= P.BBOX[3]):
            return t, []
        r = (P.BOUNDS["north"] - lat) / (P.BOUNDS["north"] - P.BOUNDS["south"]) * (self.n - 1)
        c = (lon - P.BOUNDS["west"]) / (P.BOUNDS["east"] - P.BOUNDS["west"]) * (self.n - 1)
        px_m = (P.BOUNDS["north"] - P.BOUNDS["south"]) * P.M_PER_DEG / self.n
        rr, cc = np.mgrid[0:self.n, 0:self.n]
        near = np.hypot(rr - r, cc - c) * px_m <= 300  # 300 m: bir durakta çalışırken dolaşılan yarıçap (varsayım)
        ri, ci = int(round(r)), int(round(c))
        th = float(self.L["thermal"][ri, ci])
        t |= {"slope_deg": round(float(self.L["slope"][ri, ci]), 1),
              "max_slope_300m_deg": round(float(np.nanmax(self.L["slope"][near])), 1),
              "sand_pct_300m": round(float(self.L["sand"][near].mean()) * 100, 1),
              "thermal_norm": round(th, 2),
              "traversability_score": round(float(self.L["score"][ri, ci]), 2)}
        hz = []
        if t["max_slope_300m_deg"] > P.SLOPE_MAX_DEG:
            hz.append(f"Dik yamaç: 300 m içinde {t['max_slope_300m_deg']}° (sınır {P.SLOPE_MAX_DEG:.0f}°)")
        elif t["max_slope_300m_deg"] > 15:
            hz.append(f"Eğimli arazi: 300 m içinde {t['max_slope_300m_deg']}°")
        if t["sand_pct_300m"] >= 10:
            hz.append(f"Eolyen kum: 300 m çevrenin %{t['sand_pct_300m']:.0f}'i kum dalgası birimi")
        if th < 0.25:
            hz.append("Gevşek zemin: düşük termal eylemsizlik (batma riski)")
        return t, hz


def fetch_sol(sol, cache):
    if sol not in cache:
        for attempt in range(3):
            try:
                r = requests.get(API.format(sol=sol), headers=UA, timeout=90)
                r.raise_for_status()
                cache[sol] = r.json().get("images", [])
                break
            except requests.RequestException as e:
                print(f"  D7 Sol {sol} deneme {attempt + 1}: {e}")
                time.sleep(5)
        else:
            cache[sol] = []
    return cache[sol]


def width(im):
    try:
        return int(im["extended"]["dimension"].strip("()").split(",")[0])
    except (KeyError, ValueError):
        return 0


def mast_el(im):
    try:
        return float(im["extended"]["mastEl"])
    except (KeyError, ValueError, TypeError):
        return None


def choose_photos(region_id, sol, cache, stats):
    """Sol'den en fazla 2 fotoğraf: önce Navcam, sonra Mastcam-Z (ya da Hazcam)."""
    for ds in SOL_SEARCH:
        s = sol + ds
        if s < 0:
            continue
        ims = fetch_sol(s, cache)
        st = {"sol": s, "api_images": len(ims)}
        full = [i for i in ims if i.get("sample_type") == "Full"]
        st["after_full"] = len(full)
        left = [i for i in full if i["camera"]["instrument"] in dict(CAMS)]
        st["after_left_cams"] = len(left)
        big = [i for i in left if width(i) >= MIN_WIDTH]
        st["after_width"] = len(big)
        # Aynı kare iki işlemeyle geliyor: ...EBY... (renkli) ve ...ECM... (gri). Renkli kalır.
        frames = {}
        for i in sorted(big, key=lambda i: "ECM" in i["imageid"]):
            frames.setdefault(frame_key(i["imageid"]), i)
        big = list(frames.values())
        st["after_dedupe"] = len(big)
        land = [i for i in big if mast_el(i) is not None and MAST_EL[0] <= mast_el(i) <= MAST_EL[1]]
        # Hazcam'in direk açısı yok (sabit kamera); Navcam/Mastcam-Z yoksa yedek
        hz = [i for i in big if i["camera"]["instrument"] == "FRONT_HAZCAM_LEFT_A"]
        st["after_mast_el"] = len(land)
        st["rejected_flat"], st["rejected_manual"] = 0, 0
        picks = []
        groups = [sorted((i for i in land if i["camera"]["instrument"] == cam),
                         key=lambda i: (abs(mast_el(i) - TARGET_EL), i["imageid"])) for cam, _ in CAMS[:2]]
        for cands in groups:
            for im in cands[:MAX_TRIES]:
                if frame_key(im["imageid"]) in EXCLUDE:
                    st["rejected_manual"] += 1
                    continue
                data = requests.get(im["image_files"]["medium"], headers=UA, timeout=90).content
                if edge_mean(data) < MIN_EDGE:
                    st["rejected_flat"] += 1
                    continue
                picks.append((im, data))
                break
        if not picks and hz:
            im = hz[len(hz) // 2]
            picks = [(im, requests.get(im["image_files"]["medium"], headers=UA, timeout=90).content)]
        if picks:
            st["selected"] = len(picks)
            stats[region_id] = st
            return picks
        stats.setdefault(region_id + "_tried", []).append(st)
    stats[region_id] = {"sol": sol, "selected": 0}
    return []


def frame_key(imageid):
    return imageid.replace("_ECM_", "_EBY_").replace("ECM_N", "EBY_N")


def edge_mean(data):
    from io import BytesIO

    from PIL import Image, ImageFilter
    im = Image.open(BytesIO(data)).convert("L").resize((400, 300))
    return float(np.asarray(im.filter(ImageFilter.FIND_EDGES), dtype=float)[2:-2, 2:-2].mean())


def save_photo(pick, region_id):
    im, data = pick
    cam = im["camera"]["instrument"]
    path = PHOTOS / f"{region_id}_sol{im['sol']:04d}_{cam.lower()}.jpg"
    path.write_bytes(data)
    label = dict(CAMS)[cam]
    lmst = im.get("date_taken_mars", "").split("M")[-1][:5]
    return {"url": f"photos/{path.name}", "url_large": im["image_files"]["large"], "page": im["link"],
            "imageid": im["imageid"], "sol": im["sol"], "camera": label, "date_utc": im["date_taken_utc"][:10],
            "lmst": lmst, "credit": im.get("credit", "NASA/JPL-Caltech"),
            "caption": f"{label}, Sol {im['sol']} ({im['date_taken_utc'][:10]}), yerel saat {lmst}"}


def sand_poi(regions, terrain):
    """Üs → delta önü hattına en yakın eolyen kum alanı (≥ 0,02 km²): demodaki 'yolda bir kum alanı var'."""
    g = terrain.geo
    t = terrain.to_geo
    base = next(r for r in regions if r["id"] == "base")
    delta = next(r for r in regions if r["id"] == "delta_front")
    line = LineString([t.transform(base["lon"], base["lat"]), t.transform(delta["lon"], delta["lat"])])
    eol = g[(g["name"] == "Eolian bedform unit") & (g.area >= 0.02e6)].copy()
    eol["d"] = eol.distance(line)
    best = eol.sort_values("d").iloc[0]
    # Eolyen poligonlar çok büyük olabiliyor (km²'lerce); pin, poligonun rotaya en yakın
    # kısmına konur: poligon ∩ (rotanın d + 300 m tamponu) içindeki bir nokta.
    near = best.geometry.intersection(line.buffer(best["d"] + 300))
    p = near.representative_point()
    inv = Transformer.from_crs(g.crs, CRS(terrain.dem.crs).geodetic_crs, always_xy=True)
    lon, lat = inv.transform(p.x, p.y)
    return lon, lat, best.geometry.area / 1e6, best["d"], len(eol)


def main():
    PHOTOS.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    wps = load_waypoints()
    heli = json.load(open(RAW / "m20_heli_flight_path.json", encoding="utf-8"))["features"]
    terrain = Terrain()
    cache, pstats = {}, {}

    regions = []
    for spec in REGIONS:
        lon, lat, src = position(spec["pos"], wps, heli)
        t, hz = terrain.at(lon, lat)
        photos = []
        if spec["sol"] is not None:
            photos = [save_photo(im, spec["id"]) for im in choose_photos(spec["id"], spec["sol"], cache, pstats)]
        history = []
        for date, ev, srcurl in spec["history"]:
            if date == "SOL":  # tarihi D7 fotoğrafından al (o Sol'ün UTC tarihi)
                date = photos[0]["date_utc"] if photos else None
            history.append({"date": date, "event": ev, "source": srcurl})
        regions.append({
            "id": spec["id"], "name": spec["name"], "lat": round(lat, 6), "lon": round(lon, 6),
            "elevation_m": t["elevation_m"], "science_value": spec["science_value"], "summary": spec["summary"],
            "hazards": hz, "missions": spec["missions"], "history": history, "sol": spec["sol"], "photos": photos,
            "position_source": src, "terrain": t, "poi_type": spec["type"]})
        print(f"  {spec['id']:14s} {lat:.5f} {lon:.5f}  {t['elevation_m']} m  {t['geology_unit']}  "
              f"foto {len(photos)}  tehlike {len(hz)}")

    with open(OUT / "regions.json", "w", encoding="utf-8") as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)

    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
              "properties": {"id": r["id"], "name": r["name"], "type": r["poi_type"], "region_id": r["id"]}}
             for r in regions]
    slon, slat, sarea, sdist, n_eol = sand_poi(regions, terrain)
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(slon, 6), round(slat, 6)]},
                  "properties": {"id": "sand_field", "name": "Kum alanı (eolyen birim)", "type": "hazard",
                                 "story_ids": ["opportunity", "spirit"], "area_km2": round(sarea, 3),
                                 "note": "Opportunity buna benzer bir kum dalgasında 5 hafta kaldı. Spirit yumuşak kuma gömüldü.",
                                 "source": "USGS SIM 3464, Eolian bedform unit"}})
    with open(OUT / "poi.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False, indent=2)
    print(f"  sand_field     {slat:.5f} {slon:.5f}  {sarea:.3f} km², üs–delta hattına {sdist:.0f} m")

    with open(OUT / "stories.json", "w", encoding="utf-8") as f:
        json.dump(STORIES, f, ensure_ascii=False, indent=2)

    e7 = {"waypoints": len(wps), "regions": len(regions), "photos": sum(len(r["photos"]) for r in regions),
          "photo_filter": {"cams": [c for c, _ in CAMS], "min_width_px": MIN_WIDTH, "mast_el_deg": MAST_EL,
                           "target_el_deg": TARGET_EL},
          "per_region": pstats,
          "sand_poi": {"eolian_polygons_ge_0_02km2": n_eol, "area_km2": round(sarea, 3), "dist_to_route_m": round(float(sdist))}}
    (FIG / "e7_stats.json").write_text(json.dumps(e7, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Bitti:", e7["regions"], "nokta,", e7["photos"], "fotoğraf")


if __name__ == "__main__":
    main()
