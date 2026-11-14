"""
MarsTrail – ham veri indirici (E2).

Kullanım (proje kökünden):
    venv\\Scripts\\python scripts\\download_data.py D1 D2 D3 D4      # küçükler
    venv\\Scripts\\python scripts\\download_data.py D5 D6            # orta
    venv\\Scripts\\python scripts\\download_data.py D8               # 5,5 GB
    venv\\Scripts\\python scripts\\download_data.py --report         # tablo

- Dosyalar data/raw/ altına iner (git'e girmez).
- Yarıda kalan indirme kaldığı yerden devam eder (.part + HTTP Range).
- İlerleme: "PROGRESS D8  35%  1914/5468 MB  9.8 MB/s" satırları (%5 adımlarla).
- D6: zip indikten sonra içinden sadece Jezero_GeoUnits shapefile parçaları çıkarılır.
- D7 burada yok (E7'de, Sol bazında).
"""
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "MarsTrail-downloader (NASA Space Apps)"}

SOURCES = {
    "D1": ("M20_waypoints.json", "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json"),
    "D2": ("M20_traverse.json", "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_traverse.json"),
    "D3": ("m20_heli_flight_path.json", "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json"),
    "D4": ("Jezero_Thermal_Inertia_v1.tiff", "https://zenodo.org/api/records/4931348/files/Jezero_Thermal_Inertia_v1.tiff/content"),
    "D5": ("M20_JezeroCrater_CTXDEM_20m.tif", "https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif"),
    "D6": ("sim3464_database.zip", "https://pubs.usgs.gov/sim/3464/sim3464_database.zip"),
    "D8": ("MSR_TRN_HiRISE_mosaics.zip", "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024_mosaics.zip"),
}


def log(msg):
    print(msg, flush=True)


def remote_size(url):
    try:
        r = requests.head(url, headers=UA, allow_redirects=True, timeout=60)
        n = int(r.headers.get("Content-Length", 0))
        return n or None
    except requests.RequestException:
        return None


def download(did, retries=5):
    name, url = SOURCES[did]
    dest = RAW / name
    part = dest.with_suffix(dest.suffix + ".part")
    total = remote_size(url)
    if dest.exists() and (total is None or dest.stat().st_size == total):
        log(f"SKIP {did} zaten var ({dest.stat().st_size / 1e6:.1f} MB)")
        return dest

    for attempt in range(1, retries + 1):
        have = part.stat().st_size if part.exists() else 0
        headers = dict(UA)
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(60, 120)) as r:
                if have and r.status_code != 206:  # sunucu devam etmeyi desteklemiyor
                    have = 0
                r.raise_for_status()
                if total is None:
                    cl = int(r.headers.get("Content-Length", 0))
                    total = (cl + have) if cl else None
                log(f"START {did} {name} {'%.1f MB' % (total / 1e6) if total else 'boyut bilinmiyor'}"
                    + (f" (devam: {have / 1e6:.0f} MB)" if have else ""))
                t0, got, next_pct = time.time(), have, 0
                if total:
                    next_pct = (have * 100 // total) // 5 * 5 + 5
                with open(part, "ab" if have else "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        got += len(chunk)
                        if total and got * 100 / total >= next_pct:
                            speed = (got - have) / max(time.time() - t0, 1e-3) / 1e6
                            log(f"PROGRESS {did} {next_pct:3d}%  {got / 1e6:.0f}/{total / 1e6:.0f} MB  {speed:.1f} MB/s")
                            next_pct += 5
            if total and part.stat().st_size != total:
                raise IOError(f"eksik: {part.stat().st_size} / {total}")
            part.replace(dest)
            log(f"DONE {did} {dest.stat().st_size / 1e6:.1f} MB")
            return dest
        except (requests.RequestException, IOError) as e:
            log(f"RETRY {did} deneme {attempt}/{retries}: {e}")
            time.sleep(min(10 * attempt, 60))
    log(f"FAIL {did} {retries} denemede inmedi")
    return None


def extract_d6(zpath):
    """SIM 3464 zip'i shapefile değil, ArcGIS dosya veritabanı (Nili.gdb) içeriyor.
    Sadece Nili.gdb'yi data/raw/D6_geology/ altına çıkarır, GeologicUnits katmanını
    kartta beklenen adla Jezero_GeoUnits.shp olarak yazar."""
    import geopandas as gpd
    import pyogrio

    out = RAW / "D6_geology"
    gdb = out / "Nili.gdb"
    gdb.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        members = [m for m in z.namelist()
                   if "/Nili.gdb/" in m and not m.endswith("/") and "__MACOSX" not in m and not m.endswith(".lock")]
        for m in members:  # yol kaçışına karşı sadece dosya adıyla yaz
            (gdb / Path(m).name).write_bytes(z.read(m))
    layers = [name for name, _ in pyogrio.list_layers(gdb)]
    log(f"EXTRACT D6 Nili.gdb ({len(members)} dosya), katmanlar: {layers}")
    # Jeolojik birim poligonları katmanı: zip'teki adı "GeoUnits_v1"
    cand = [n for n in layers if n.lower().startswith(("geounits", "geologicunits")) and "anno" not in n.lower()]
    if not cand:
        log("WARN D6 jeolojik birim katmanı bulunamadı; E3'te katman adını elle seç.")
        return None
    units = gpd.read_file(gdb, layer=cand[0])
    shp = out / "Jezero_GeoUnits.shp"
    units.to_file(shp, encoding="utf-8")
    log(f"EXTRACT D6 {cand[0]} -> {shp.relative_to(ROOT)} ({len(units)} poligon)")
    return shp


def check(did):
    """Dosya açılıyor mu? (ok, açıklama)"""
    name, _ = SOURCES[did]
    p = RAW / name
    if not p.exists():
        return False, "inmedi" + (" (.part var, sürüyor/yarım)" if p.with_suffix(p.suffix + ".part").exists() else "")
    try:
        if name.endswith(".json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            n = len(d.get("features", [])) if isinstance(d, dict) else len(d)
            return True, f"JSON, {n} kayıt/feature"
        if name.endswith((".tif", ".tiff")):
            import rasterio
            with rasterio.open(p) as src:
                return True, f"{src.width}x{src.height}, {src.count} bant, {src.dtypes[0]}, çözünürlük {abs(src.res[0]):.1f}, {src.crs.to_string()[:40] if src.crs else 'CRS yok'}"
        if name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
            info = f"zip, {len(names)} dosya"
            if did == "D6":
                shp = RAW / "D6_geology" / "Jezero_GeoUnits.shp"
                if shp.exists():
                    import geopandas as gpd
                    g = gpd.read_file(shp)
                    info += f"; Jezero_GeoUnits: {len(g)} poligon"
            return True, info
    except Exception as e:  # noqa: BLE001
        return False, f"açılmadı: {e}"
    return True, "?"


def report():
    log("\n| # | Dosya | Boyut | Açılıyor mu | Not |\n| --- | --- | --- | --- | --- |")
    for did, (name, _) in SOURCES.items():
        p = RAW / name
        size = f"{p.stat().st_size / 1e6:.1f} MB" if p.exists() else "-"
        ok, info = check(did)
        log(f"| {did} | {name} | {size} | {'evet' if ok else 'HAYIR'} | {info} |")


def main(args):
    RAW.mkdir(parents=True, exist_ok=True)
    if not args or args == ["--report"]:
        report()
        return
    for did in args:
        p = download(did)
        if did == "D6" and p:
            extract_d6(p)
        ok, info = check(did)
        log(f"CHECK {did} {'OK' if ok else 'HATA'} {info}")


if __name__ == "__main__":
    main(sys.argv[1:])
