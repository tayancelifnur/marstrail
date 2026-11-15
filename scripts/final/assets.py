"""
Final sunum (make_final.py) için görsel ve klipleri hazırlar → docs/sunum/img/final/ (git'e girmez, yeniden üretilir).

  clips/*.mp4  : docs/sunum/demo.mp4'ten 4–6 sn'lik parçalar (1280×720) + rec_scenes.py kayıtlarından rota çiz / not pini
  *_poster.png : her klibin poster karesi (PPTX'te videonun yerinde görünen kare)
  profil.png, nokta.png : uygulamadan ekran görüntüsü (headless Edge + CDP): astronot profili, delta önü nokta kartı
  ay.png, mars.png, qr.png : MarsTrail_sunum_v2.mp4 karelerinden (QR → https://tayancelifnur.github.io/marstrail/)
  etiket.png   : elle etiketlenmiş iki HiRISE karosu, kutularıyla (ml/dataset_merged)

Çalıştır (PowerShell/cmd):  venv\\Scripts\\python scripts\\final\\assets.py
"""
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "sunum_v2"))
OUT = ROOT / "docs" / "sunum" / "img" / "final"
CLIPS = OUT / "clips"
DEMO = ROOT / "docs" / "sunum" / "demo.mp4"
V2 = ROOT / "docs" / "sunum" / "MarsTrail_sunum_v2.mp4"
FF = imageio_ffmpeg.get_ffmpeg_exe()
CW, CH = 1280, 720

# demo.mp4 sahneleri (sn; videodaki alt yazılarla eşleştirildi)
DEMO_CLIPS = {
    "bolgeler": (2.0, 5.2),    # Jezero Krateri · O₂ bölgeleri her zaman açık
    "nokta": (5.4, 9.2),       # Nokta kartı · tarihçe + Perseverance fotoğrafı
    "yolo": (9.2, 13.0),       # YOLO · HiRISE 25 cm: turuncu kum dalgası, kırmızı kaya
    "plan": (13.1, 16.6),      # Plan: Üs → Delta → Three Forks · GO
    "nabiz": (16.8, 22.6),     # Canlı yürüyüş ×300 → Nabız 150, güvenli bölge daralıyor
    "telsiz": (22.6, 27.4),    # Telsiz koptu · arama alanı ve İHA → Ali'nin kurtarma rotası
}


def ffmpeg_clip(src, t0, t1, dst):
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", str(src), "-an",
                    "-vf", f"scale={CW}:{CH}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)], check=True)


def poster(src, t, dst, crop=None, size=None):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{t}", "-i", str(src), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    w, h = (1920, 1080)
    im = Image.fromarray(np.frombuffer(raw, np.uint8)[: w * h * 3].reshape(h, w, 3))
    if crop:
        im = im.crop(crop)
    if size:
        im = im.resize(size, Image.LANCZOS)
    im.save(dst)
    return im


def rec_clip(name, n, phase1, start, dst, pill=None):
    """rec_scenes.py kareleri → 25 fps klip (edit_video.scene_frames ile aynı zaman eşlemesi)."""
    import edit_video as E
    files = E.scene_frames(name, n, phase1, start=start)
    p = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}", "-r", "25", "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                          str(dst)], stdin=subprocess.PIPE)
    cache = {}
    for f in files:
        if f not in cache:
            im = Image.open(f).convert("RGB")
            if pill:
                E.pill(im, pill)
            cache[f] = im.resize((CW, CH), Image.LANCZOS).tobytes()
        p.stdin.write(cache[f])
    p.stdin.close()
    p.wait()
    Image.open(files[-1]).convert("RGB").resize((CW, CH), Image.LANCZOS).save(dst.with_name(dst.stem + "_poster.png"))


def app_stills():
    """Profil formu ve delta önü nokta kartı (uygulamanın kendisinden, 1920×1080)."""
    from cdp import Browser
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8812", "--directory", str(ROOT / "web")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    b = Browser(port=9334)
    try:
        b.cmd("Page.navigate", url="http://127.0.0.1:8812/index.html")
        b.wait("document.readyState === 'complete' && window.MarsTrail && MarsTrail.plan !== undefined", timeout=60)
        time.sleep(4)
        b.js("document.getElementById('jezeroBtn').click()")
        time.sleep(6)
        b.wait("MarsTrail.viewer.scene.globe.tilesLoaded", timeout=40)
        b.js("document.querySelector('button.astro').click()")
        time.sleep(1.5)
        (OUT / "profil.png").write_bytes(b.shot(fmt="png"))
        b.js("MarsTrail.hideDetail(); MarsTrail.openPoi('delta_front')")
        time.sleep(4)
        b.wait("MarsTrail.viewer.scene.globe.tilesLoaded", timeout=40)
        time.sleep(1.5)
        (OUT / "nokta.png").write_bytes(b.shot(fmt="png"))
    finally:
        b.close()
        srv.terminate()


def tiles_triptych():
    """Üç HiRISE karosu yan yana (koyu zemin): NoData yüzünden atılan, dokusuz atılan, kullanılan (E5 eleme kuralları)."""
    import rasterio
    from rasterio.windows import Window
    sys.path.insert(0, str(ROOT / "scripts"))
    import tile_for_yolo as T
    z = np.load(ROOT / "data" / "processed" / "d8_preview_dec16.npz")   # make_data_examples.py önbelleği
    prev, k, c0, r0 = z["prev"], int(z["k"]), int(z["c0"]), int(z["r0"])
    nod, std = T.tile_stats(prev, k, 0)
    has = nod > 0
    thr = float(np.percentile(std[~has], 5))
    flat = (~has) & (std < thr)
    ok = (~has) & (~flat)
    pick_nod = np.unravel_index(np.argmin(np.where(has, np.abs(nod - 0.5), 9)), nod.shape)
    fl = np.argwhere(flat)
    pick_flat = tuple(fl[np.argsort(std[flat])[len(fl) // 2]])
    oks = np.argwhere(ok)
    pick_ok = tuple(oks[np.argmax(std[ok])])
    lo, hi = 60.0, 219.0                         # E5 germesi (%0,5–99,5)
    out = Image.new("RGB", (3 * 520 + 2 * 20, 520), (13, 11, 10))
    with rasterio.open(T.ORTHO) as src:
        for i, (r, c) in enumerate((pick_nod, pick_flat, pick_ok)):
            a = src.read(1, window=Window(c0 + int(c) * T.TILE, r0 + int(r) * T.TILE, T.TILE, T.TILE)).astype(np.float32)
            b = np.clip((a - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            b[a == 0] = 0
            im = Image.fromarray(b).convert("RGB").resize((520, 520), Image.LANCZOS)
            col = [(231, 76, 60), (79, 160, 220), (46, 204, 113)][i]
            ImageDraw.Draw(im).rectangle([0, 0, 519, 519], outline=col, width=8)
            out.paste(im, (i * 540, 0))
    out.save(OUT / "karolar.png")


def labeled_tiles():
    """İki etiketli karo yan yana: biri kum dalgası, biri kaya + kaya alanı kutularıyla (ml/dataset_merged)."""
    ds = ROOT / "ml" / "dataset_merged"
    colors = {0: (255, 92, 92), 1: (255, 170, 60), 2: (255, 230, 80)}
    labs = []
    for split in ("valid", "train"):
        for lab in sorted((ds / split / "labels").glob("*.txt")):
            rows = [l.split() for l in lab.read_text().splitlines() if l.strip()]
            labs.append((split, lab, rows))
    kum = max((x for x in labs if x[2] and all(r[0] == "2" for r in x[2]) and all(float(r[3]) * float(r[4]) < 0.5 for r in x[2])),
              key=lambda x: len(x[2]))
    kaya = max((x for x in labs if any(r[0] == "0" for r in x[2]) and any(r[0] == "1" for r in x[2])
                and not any(r[0] == "2" for r in x[2])), key=lambda x: len(x[2]))
    tiles = []
    for split, lab, rows in (kum, kaya):
        im = Image.open(next((ds / split / "images").glob(lab.stem + ".*"))).convert("RGB")
        d = ImageDraw.Draw(im)
        for r in rows:
            c, cx, cy, bw, bh = int(r[0]), *map(float, r[1:5])
            W, H = im.size
            d.rectangle([(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H], outline=colors[c], width=4)
        tiles.append(im.resize((640, 640)))
    out = Image.new("RGB", (640 * 2 + 24, 640), (13, 11, 10))
    out.paste(tiles[0], (0, 0))
    out.paste(tiles[1], (664, 0))
    out.save(OUT / "etiket.png")


def main():
    CLIPS.mkdir(parents=True, exist_ok=True)
    for name, (a, b) in DEMO_CLIPS.items():
        ffmpeg_clip(DEMO, a, b, CLIPS / f"{name}.mp4")
        poster(DEMO, a + 0.6 * (b - a), CLIPS / f"{name}_poster.png", size=(CW, CH))
    rec_clip("A", 138, 2.5, 0.3, CLIPS / "rota.mp4", pill="Rota çiz · engeller, zorluk ve yükseklik profili")
    rec_clip("B", 87, 1.3, 0.2, CLIPS / "pin.mp4", pill="Yürürken not pini · anlık bildirim")
    # Yazıların henüz belirmediği anlar (sağdaki gezegen kırpılırken soldan metin girmesin)
    poster(V2, 4.0, OUT / "ay.png", crop=(1040, 95, 1920, 985))
    poster(V2, 30.5, OUT / "mars.png", crop=(1000, 60, 1920, 1060))
    tiles_triptych()
    q = poster(V2, 292.0, OUT / "_qr.png", crop=(1370, 300, 1770, 700))
    q.save(OUT / "qr.png")
    (OUT / "_qr.png").unlink()
    labeled_tiles()
    app_stills()
    print("hazır:", sorted(p.name for p in OUT.rglob("*") if p.is_file()))


if __name__ == "__main__":
    main()
