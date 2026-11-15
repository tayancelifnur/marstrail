"""
Sunum videosu v2: 5:00'lık sunum videosunda (WhatsApp Video 2026-11-15 at 13.24.45.mp4) dört düzeltme, süre yine 5:00.

  1) Apollo 14 sayacı 21 m → ~30 m, altına kaynak: "Kaynak · LROC/ASU: Saddle Rock, kenara ~30 m"
     (NASA PIA12897, LROC/NASA/GSFC/ASU 2009: "the astronauts just barely missed (30 meters) the rim of Cone crater")
  2) Veri tablosu bölümünden 9,0 sn kesilir (1:46–1:55; tablo bu aralıkta tamamen durağan, yalnız yıldızlar titreşiyor)
  3) Demoya 9,0 sn eklenir (rec_scenes.py kayıtları):
       A) 3:09,5'te, "Plan" sahnesinden önce 5,5 sn: "Rota çiz · engeller, zorluk ve yükseklik profili"
       B) "Canlı yürüyüş" ile "Nabız 150" arasına 3,5 sn: "Yürürken not pini · anlık bildirim"
     Ekleme ve kesme eşit (225 kare) olduğu için demo sonrası bütün zamanlar orijinaliyle aynı kalır.
  4) Etki bölümünde "Dünya'da afet" kartı → "Ay · Artemis: Aynı sistem Ay güney kutbu yürüyüşlerine uyarlanabilir."

Yaklaşım: orijinal kareler sırayla çözülür; değişen bölgeler orijinalin aynı yerinden alınmış temiz arka plan (yıldızlar)
üstüne Bahnschrift ile yeniden çizilir (videodaki DIN benzeri yazıya en yakın Windows yazı tipi). Görünme/kaybolma
saydamlığı orijinal yazının parlaklık eğrisinden ölçüldü, böylece yeni yazı eskisiyle aynı anda belirip kaybolur.

Çalıştır:  venv\\Scripts\\python scripts\\sunum_v2\\edit_video.py ["kaynak.mp4"]
Çıktı:     docs/sunum/MarsTrail_sunum_v2.mp4 (1920×1080, 25 fps, H.264, sessiz)
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Desktop" / "nasa" / "WhatsApp Video 2026-11-15 at 13.24.45.mp4"
REC = ROOT / "docs" / "sunum" / "img" / "v2_rec"
OUT = ROOT / "docs" / "sunum" / "MarsTrail_sunum_v2.mp4"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 25
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"

# ---- Kare numaraları (orijinal videonun sıralı çözümünden ölçüldü; t = kare / 25) ----
APOLLO = (255, 362)        # sayaç 10,42 sn'de belirir, 14,34 sn'de kaybolur
APOLLO_CLEAN = 250         # 10,0 sn: sayaç bölgesi boş (yalnız yıldızlar)
CUT = (2650, 2875)         # 1:46,00–1:55,00 → 225 kare
INS_A = 4738               # bu kareden önce: "Plan" sahnesi başlıyor (altyazı değişimi 4739)
INS_B = 4883               # bu kareden önce: "Nabız 150" altyazısı başlıyor
A_N, B_N = 138, 87         # 5,52 + 3,48 sn = 225 kare = kesilen süre
ETKI = (6250, 7000)        # etki bölümü (4:10–4:40); kart 6317–6340 arası belirir
ETKI_CLEAN = 6290          # kart görünmeden önce
APP_BOX = (240, 250, 1680, 1060)   # demo içindeki uygulama kaydı (1440×810)


def font(size, var):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(var)
    return f


def fit_size(text, var, target, dim):
    """Yazı tipini, metnin ölçülen kutusu (dim=1 yükseklik, 0 genişlik) hedefe eşit olacak boyda seçer."""
    lo, hi = 8, 400
    while hi - lo > 1:
        m = (lo + hi) // 2
        bb = font(m, var).getbbox(text)
        size = (bb[3] - bb[1]) if dim == 1 else (bb[2] - bb[0])
        lo, hi = (m, hi) if size <= target else (lo, m)
    return font(lo, var)


# Ölçüler orijinal karelerden (f 13,0 sn ve 4:20): "21" glif kutusu x 140–310, y 693–850; "m" 336–398 × 805–850;
# açıklama x 448, satır 1 "Yıllar sonra uydu fotoğrafları gösterdi:" 448–878; renkler (234,234,242) (140,148,167) (143,145,158)
F_NUM = fit_size("21", "Bold", 157, 1)
F_M = fit_size("m", "Regular", 45, 1)
F_TILDE = font(int(F_NUM.size * 0.5), "Bold")
F_CAP = fit_size("Yıllar sonra uydu fotoğrafları gösterdi:", "Regular", 430, 0)
F_SRC = font(int(F_CAP.size * 0.86), "SemiBold")
# Etki kartı: başlık "Artemis ve Mars" 149–442 (293 px), gövde (afet) 150–1013 (863 px)
F_TITLE = fit_size("Artemis ve Mars", "SemiBold", 293, 0)
# Kart gövdeleri videoda Segoe UI (Bahnschrift değil). Boy, komşu kartın satırından ölçüldü: "Açık veri, açık kod; …
# gerçek EVA" 149–1064 px ≈ Segoe UI 26 px (26 px'te 915 px genişlik).
F_BODY = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
F_PILL = fit_size("Plan: Üs → Delta → Three Forks · GO", "SemiBold", 362, 0)

# Orijinal sayaç değerleri (0,12 sn aralıkla okundu) → yeni sayaç aynı eğriyle 30'da durur: v' = 30 + (v − 21)
COUNT = [(10.40, 600), (10.50, 377), (10.62, 265), (10.74, 188), (10.86, 135), (10.98, 99), (11.10, 75), (11.22, 58),
         (11.34, 46), (11.46, 38), (11.58, 33), (11.70, 29), (11.82, 27), (11.94, 25), (12.06, 24), (12.18, 23),
         (12.30, 22), (12.66, 21)]
# Saydamlık: orijinal açıklama metninin parlaklığı / kararlı değer (belirme 10,40–10,82; kaybolma 13,54–14,34)
ALPHA = [(10.38, 0), (10.42, 0.09), (10.50, 0.37), (10.58, 0.63), (10.66, 0.72), (10.74, 0.78), (10.82, 1.0),
         (13.54, 1.0), (13.62, 0.98), (13.70, 0.97), (13.78, 0.91), (13.86, 0.84), (13.94, 0.76), (14.02, 0.65),
         (14.10, 0.50), (14.18, 0.30), (14.26, 0.07), (14.34, 0.0)]


def interp(table, t):
    xs, ys = zip(*table)
    return float(np.interp(t, xs, ys))


def count_text(t):
    if t >= 12.62:
        return "~30"
    xs, ys = zip(*COUNT)
    v = 21 + np.exp(np.interp(t, xs, np.log(np.array(ys, float) - 20.5)))   # log uzayında ara değer
    return str(int(round(30 + (v - 21))))


def apollo_layer(t):
    """Sayaç + "m" + açıklama + kaynak, şeffaf katman (tam ekran)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    txt = count_text(t)
    x, top, bottom = 140, 693, 850
    if txt.startswith("~"):
        # Bahnschrift'te "~" rakam boyunda çok iri; yarım boyda, rakamların düşey ortasına çizilir
        tb = F_TILDE.getbbox("~")
        d.text((x - tb[0], (top + bottom) // 2 + 8 - (tb[1] + tb[3]) // 2), "~", font=F_TILDE, fill=(234, 234, 242, 255))
        x += (tb[2] - tb[0]) + 10
        txt = txt[1:]
    bb = F_NUM.getbbox(txt)
    d.text((x - bb[0], bottom - bb[3]), txt, font=F_NUM, fill=(234, 234, 242, 255))
    nx = x + (bb[2] - bb[0])
    mb = F_M.getbbox("m")
    mx = nx + 26
    d.text((mx - mb[0], bottom - mb[3]), "m", font=F_M, fill=(140, 148, 167, 255))
    cx = mx + (mb[2] - mb[0]) + 50
    l1 = "Yıllar sonra uydu fotoğrafları gösterdi:"
    b1 = F_CAP.getbbox(l1)
    d.text((cx - b1[0], 832 - F_CAP.getbbox("Y")[1]), l1, font=F_CAP, fill=(143, 145, 158, 255))
    d.text((cx - b1[0], 868 - F_CAP.getbbox("k")[1]), "krater kenarına kalan mesafe", font=F_CAP, fill=(143, 145, 158, 255))
    d.text((cx - b1[0], 906 - F_SRC.getbbox("K")[1]), "Kaynak · LROC/ASU: Saddle Rock, kenara ~30 m", font=F_SRC,
           fill=(212, 121, 77, 255))
    return lay


def etki_layer():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([120, 322, 122, 408], fill=(212, 121, 77, 255))   # kartın turuncu çizgisi (orijinaldeki gibi)
    tb = F_TITLE.getbbox("A")
    d.text((150 - tb[0], 333 - tb[1]), "Ay · Artemis", font=F_TITLE, fill=(232, 231, 237, 255))
    bb = F_BODY.getbbox("A")
    d.text((150 - bb[0], 386 - bb[1]), "Aynı sistem Ay güney kutbu yürüyüşlerine uyarlanabilir.", font=F_BODY,
           fill=(193, 193, 200, 255))
    return lay


def blend(frame, clean, lay, alpha, box):
    """box bölgesinde: temiz arka plan + alfa × katman; dışı orijinal."""
    x0, y0, x1, y1 = box
    out = frame.copy()
    region = clean[y0:y1, x0:x1].astype(np.float32)
    L = np.asarray(lay)[y0:y1, x0:x1].astype(np.float32)
    a = (L[..., 3:4] / 255.0) * alpha
    out[y0:y1, x0:x1] = np.clip(region * (1 - a) + L[..., :3] * a, 0, 255).astype(np.uint8)
    return out


def pill(img, text):
    """Demo altyazı kapsülü (orijinaldeki gibi: koyu zemin, solda turuncu çizgi, ortalı)."""
    d = ImageDraw.Draw(img)
    bb = F_PILL.getbbox(text)
    tw = bb[2] - bb[0]
    w = tw + 2 * 24 + 4
    x0, y0, y1 = 960 - w // 2, 975, 1026
    d.rounded_rectangle([x0, y0, x0 + w, y1], radius=5, fill=(32, 34, 42))
    d.rectangle([x0, y0 + 1, x0 + 3, y1 - 1], fill=(213, 117, 77))
    cy = (y0 + y1) // 2
    d.text((x0 + 4 + 24 - bb[0], cy - (F_PILL.getbbox("P")[1] + F_PILL.getbbox("P")[3]) // 2), text, font=F_PILL,
           fill=(236, 236, 241))


def scene_frames(name, n, phase1_out, speed2=1.0, start=0.0):
    """Kayıt karelerini n çıktı karesine dağıtır: işarete kadar olan kısım phase1_out sn'ye sıkıştırılır, sonrası gerçek hızda."""
    meta = json.loads((REC / name / "frames.json").read_text())
    ts = np.array([f[0] for f in meta["frames"]])
    files = [REC / name / f[1] for f in meta["frames"]]
    mark = list(meta["marks"].values())[0]
    out = []
    for k in range(n):
        tau = k / FPS
        s = start + (tau / phase1_out) * (mark + 0.15 - start) if tau < phase1_out else mark + 0.15 + (tau - phase1_out) * speed2
        i = max(0, int(np.searchsorted(ts, s, side="right")) - 1)
        out.append(files[i])
    return out


def compose(bg, rec_file, caption):
    img = Image.fromarray(bg).copy()
    shot = Image.open(rec_file).convert("RGB").resize((APP_BOX[2] - APP_BOX[0], APP_BOX[3] - APP_BOX[1]), Image.LANCZOS)
    img.paste(shot, APP_BOX[:2])
    pill(img, caption)
    return np.asarray(img)


def frame_at(t):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", str(SRC), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)


ETKI_BOX = (70, 318, 1110, 416)   # soldan kayarak gelen eski kart (çizgi + harfler) tamamen örtülür; çizgi yeniden çizilir


def etki_reference():
    """Kart tam görünürken bölge ortalaması − kart yokken bölge ortalaması (saydamlık = anlık fark / bu değer)."""
    x0, y0, x1, y1 = ETKI_BOX
    full, empty = frame_at(6400 / FPS), frame_at(ETKI_CLEAN / FPS)
    return float(full[y0:y1, x0:x1].mean()) - float(empty[y0:y1, x0:x1].mean())


def main():
    a_files = scene_frames("A", A_N, 2.5, start=0.3)
    b_files = scene_frames("B", B_N, 1.3, start=0.2)
    a_cache, b_cache = {}, {}
    dec = subprocess.Popen([FF, "-v", "error", "-i", str(SRC), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            str(OUT)], stdin=subprocess.PIPE)
    lay_etki = etki_layer()
    etki_ref = etki_reference()
    print("etki saydamlık referansı", round(etki_ref, 2))
    clean_ap = clean_et = None
    bg_a = bg_b = None
    i = written = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        if i == APOLLO_CLEAN:
            clean_ap = fr.copy()
        if i == ETKI_CLEAN:
            clean_et = fr.copy()
        if i == INS_A - 1:
            bg_a = fr.copy()
        if i == INS_B - 1:
            bg_b = fr.copy()
        if i == INS_A:
            for f in a_files:
                if f not in a_cache:
                    a_cache[f] = compose(bg_a, f, "Rota çiz · engeller, zorluk ve yükseklik profili")
                enc.stdin.write(a_cache[f].tobytes()); written += 1
        if i == INS_B:
            for f in b_files:
                if f not in b_cache:
                    b_cache[f] = compose(bg_b, f, "Yürürken not pini · anlık bildirim")
                enc.stdin.write(b_cache[f].tobytes()); written += 1
        if CUT[0] <= i < CUT[1]:
            i += 1
            continue
        out = fr
        t = i / FPS
        if APOLLO[0] <= i < APOLLO[1]:
            al = interp(ALPHA, t)
            if al > 0:
                out = blend(fr, clean_ap, apollo_layer(t), al, (110, 660, 1150, 945))
            else:
                out = fr.copy()
                out[660:945, 110:1150] = clean_ap[660:945, 110:1150]
        if ETKI[0] <= i < ETKI[1] and clean_et is not None:
            x0, y0, x1, y1 = ETKI_BOX
            m = float(fr[y0:y1, x0:x1].mean()) - float(clean_et[y0:y1, x0:x1].mean())
            al = min(1.0, max(0.0, m / etki_ref))
            if al > 0.01:
                out = blend(fr, clean_et, lay_etki, al, ETKI_BOX)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        written += 1
        i += 1
    enc.stdin.close()
    enc.wait()
    print(f"kaynak {i} kare, çıktı {written} kare = {written / FPS:.2f} sn -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
