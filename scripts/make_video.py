"""Sunum videosu: slaytlar kare kare çizilir → docs/sunum/MarsTrail_sunum.mp4 (1920x1080, 25 fps, H.264, sessiz).

Çalıştır (proje kökünden):  venv\\Scripts\\python scripts\\make_video.py  [--fps 25] [--out docs/sunum/MarsTrail_sunum.mp4]
Gerekenler: imageio-ffmpeg (ffmpeg ikilisi pip ile gelir), docs/sunum/demo.mp4.

Kurgu:
  - Yerleşim scripts/make_slides.py'den (aynı öğeler, aynı çizim fonksiyonu). Slayt 1728x972'ye ölçeklenir; alttaki
    108 px'lik bantta Türkçe altyazı (konuşma metninin kısaltılmışı) — slaydın alt bilgisi (kaynaklar) örtülmez.
  - Geçiş: slaytlar arası 0,6 sn çapraz geçiş.
  - Grafikler: slayt açılınca yakınlaşarak (0,85 → 1, 0,7 sn) gelir, sonra slayt boyunca yavaş Ken Burns
    yakınlaşması (1 → 1,05; daha fazlası grafiklerin eksen yazılarını kesiyor).
  - Kartlar ve büyük sayılar: PPTX'teki tıklama grupları sırayla, eşit aralıkla belirir; "count" işaretli büyük
    sayılar 1,2 sn'de 0'dan değerine sayarak artar.
  - Demo (slayt 5): slayt 2 sn görünür, sonra demo videosunun 7,5–27,5 sn aralığı (20 sn) 1600x900 oynar.
  - Ses yok (sonradan seslendirilecek). Kodlama: libx264 -preset veryfast -crf 20, yuv420p, faststart.
"""
import argparse
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_slides as M  # noqa: E402

W, H = 1920, 1080
SLIDE_H = 972                    # slayt alanı (altyazı bandı 108 px)
DPI = SLIDE_H / M.H_IN           # 129,6 px/inç → 1728 px genişlik
OX = round((W - M.W_IN * DPI) / 2)
XFADE = 0.6
KB_MAX = 0.05                    # Ken Burns: slayt boyunca %5 yakınlaşma (grafik eksen yazıları kesilmesin)
DEMO_START, DEMO_LEN, DEMO_INTRO = 7.5, 20.0, 2.0
DUR = {1: 20, 2: 19, 3: 22, 4: 22, 5: DEMO_INTRO + DEMO_LEN, 6: 22, 7: 17}   # toplam 144 sn

# Konuşma metninden (docs/SLAYTLAR.md) kısaltılmış altyazılar; slayt süresine eşit bölünür.
SUBS = {
    1: ["1971, Ay: iki astronot bir krateri arıyor. Nabız 150, oksijen azalıyor.",
        "Houston “geri dönün” diyor. Yıllar sonra anlaşıldı: hedefe 21 metre kalmıştı.",
        "2005'te Opportunity 30 santimlik bir kum dalgasında 5 haftadan fazla mahsur kaldı; 2009'da Spirit kuma gömüldü.",
        "Mars'ta Houston dakikalarca uzakta. Kim “geri dön” diyecek?"],
    2: ["MarsTrail, Mars'taki bir yürüyüşü hazırlıktan acil duruma kadar yönetiyor.",
        "Apollo'da dönüş sınırı sabit hızla hesaplanıyordu; biz onu nabza, yüke, oksijene ve araziye göre canlı hesaplıyoruz.",
        "Ayşe'nin nabzı 85'ten 150'ye çıkınca güvenli bölge 130 km²'den 47 km²'ye iniyor."],
    3: ["Sekiz açık veri seti, yaklaşık altı gigabayt ham veri. Her atılan veriyi betikle ölçtük.",
        "Üç projeksiyonu 70 metrelik tek bir grid'de birleştirdik; 2590 HiRISE karosunun 1444'ü boştu, atıldı.",
        "Termal veriyi %2–98 dilimleriyle 0–1'e normalize ettik; jeoloji haritasında iki kaynak hatasını düzelttik."],
    4: ["Her hücreye eğim, kum, kaya ve termal eylemsizlikten bir zorluk skoru veriyoruz.",
        "Kum ve kayayı, 250 karoyu kendimiz etiketleyerek eğittiğimiz YOLO modeliyle 25 santimde buluyoruz.",
        "Komşu karoları aynı tarafa koyarak sızıntıyı önledik; hücre doğruluğu 0,69'dan 0,78'e çıktı."],
    5: ["Sol 34, Jezero: Ayşe deltadan numune alacak; her sayı canlı hesaplanıyor.",
        "Nokta kartı, YOLO katmanı ve plan: Go/No-Go yeşil.",
        "Nabız 150'ye çıkınca bölgeler daralıyor, dönüş noktası öne geliyor.",
        "Telsiz koptu: arama alanı, İHA rotası ve Ali'nin kurtarma rotası."],
    6: ["Doğrulama: Perseverance'ın gerçekten sürdüğü yol. Bu veriyi modele hiç vermedik.",
        "Görüntü verisi olmadan skor rotayı ayırt edemiyordu: AUC 0,50. Kendi YOLO modelimizle 0,65.",
        "Rotadaki hücrelerin hiçbiri kumlu değil, çevredekilerin yarısı kumlu. Kayada aynı sinyali bulamadık."],
    7: ["Apollo 14 astronotları nerede olduklarını bilmedikleri için döndü.",
        "MarsTrail ile bilecekler. Aynı sistem Dünya'da bir afet bölgesinde de çalışabilir.",
        "Kodu yapay zekâ desteğiyle yazdık; etiketleri, kararları ve doğrulamayı biz yaptık. Teşekkürler."],
}
NUM = re.compile(r"\d+(?:,\d+)?")


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3          # yavaşlayarak dur (ease-out cubic)


def counted(text, p):
    """Metindeki bütün sayıları p (0–1) oranında göster: 0,65 → 0,00 … 0,65; ondalık hane sayısı korunur."""
    def rep(m):
        s = m.group(0)
        dec = len(s.split(",")[1]) if "," in s else 0
        v = float(s.replace(",", ".")) * p
        out = f"{v:.{dec}f}"
        return out.replace(".", ",")
    return NUM.sub(rep, text)


def schedule(slide, dur):
    """Her öğe için giriş zamanı: zoom → 0,3 sn + gecikme; tıklama grubu g → eşit aralıklarla."""
    groups = sorted({e["anim"]["group"] for e in slide["els"] if e.get("anim") and e["anim"]["kind"] == "fade"})
    span = max(1.0, dur - 5.0)
    gap = min(3.5, span / max(1, len(groups)))
    gstart = {g: 1.4 + i * gap for i, g in enumerate(groups)}
    for e in slide["els"]:
        a = e.get("anim")
        if not a:
            e["_t0"] = None
        elif a["kind"] == "zoom":
            e["_t0"] = 0.3 + a["delay"] / 1000
        else:
            e["_t0"] = gstart[a["group"]] + a["delay"] / 1000


def base_layer(slide):
    im = Image.new("RGBA", (W, H), M._hex(M.BG))
    for e in slide["els"]:
        if e.get("_t0") is None and not (e["k"] in ("img", "video")):
            M.draw_el(im, e, DPI, OX, 0)
    return im


def slide_frame(slide, base, t, dur, demo_frame=None):
    im = base.copy()
    for e in slide["els"]:
        t0 = e.get("_t0")
        is_pic = e["k"] in ("img", "video")
        if t0 is None and not is_pic:
            continue                                  # tabanda zaten var
        kb = 1 + KB_MAX * min(1.0, t / dur) if is_pic else 1.0
        frame = demo_frame if e["k"] == "video" else None
        if t0 is None:
            M.draw_el(im, e, DPI, OX, 0, kb=kb, frame=frame)
            continue
        if t < t0:
            continue
        a = e["anim"]
        if a["kind"] == "zoom":
            p = ease((t - t0) / 0.7)
            M.draw_el(im, e, DPI, OX, 0, alpha=p, scale=0.85 + 0.15 * p, kb=kb, frame=frame)
        else:
            p = min(1.0, (t - t0) / 0.5)
            txt = None
            if e["k"] == "text" and e.get("count"):
                txt = counted(e["paras"][0]["text"], ease((t - t0) / 1.2))
            M.draw_el(im, e, DPI, OX, 0, alpha=p, kb=kb, text0=txt, frame=frame)
    return im


def subtitle(im, text, alpha=1.0):
    """Altyazıyı RGBA tuvalin alt bandına saydamlıkla (giriş/çıkış 0,3 sn) çizer."""
    if not text or alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H - SLIDE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = M.font(23, False, 96)                        # ≈ 31 px
    lines = M.wrap(text, 23, False, (W - 240) / 96, dpi=96)[:2]
    lh = 23 * M.LH * 96 / 72
    y0 = (H - SLIDE_H - lh * len(lines)) / 2
    for i, ln in enumerate(lines):
        w = f.getlength(ln)
        d.text(((W - w) / 2, y0 + i * lh), ln, font=f, fill=M._hex(M.TEXT, round(255 * alpha)))
    im.alpha_composite(layer, (0, SLIDE_H))


def sub_at(n, t, dur):
    items = SUBS[n]
    k = min(len(items) - 1, int(t / (dur / len(items))))
    seg = dur / len(items)
    local = t - k * seg
    return items[k], max(0.0, min(1.0, local / 0.3, (seg - local) / 0.3))


class Demo:
    """Demo videosunun 20 sn'lik parçasını sırayla okuyan ffmpeg borusu (1600x900, aynı fps)."""
    def __init__(self, fps):
        self.w, self.h = 1600, 900
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-ss", str(DEMO_START), "-t", str(DEMO_LEN),
               "-i", str(M.DEMO), "-vf", f"fps={fps},scale={self.w}:{self.h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.idx, self.last = -1, None

    def frame(self, i):
        while self.idx < i:
            raw = self.p.stdout.read(self.w * self.h * 3)
            if len(raw) < self.w * self.h * 3:
                break                                   # video bitti: son kare kalır
            self.last = Image.frombuffer("RGB", (self.w, self.h), raw)
            self.idx += 1
        return self.last


def demo_frame_full(fr, t):
    im = Image.new("RGBA", (W, H), M._hex(M.BG))
    d = ImageDraw.Draw(im)
    d.text((160, 14), "DEMO  ·  Sol 34, Jezero: Ayşe deltaya yürüyor", font=M.font(17, True, 96), fill=M._hex(M.ACCENT))
    if fr is not None:
        im.paste(fr, (160, 56))
    d.text((W - 160 - M.font(13, False, 96).getlength("MarsTrail uygulaması · taban harita: NASA Mars Trek"), 958),
           "MarsTrail uygulaması · taban harita: NASA Mars Trek", font=M.font(13, False, 96), fill=M._hex(M.MUTED))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--out", default="docs/sunum/MarsTrail_sunum.mp4")
    ap.add_argument("--only", type=int, help="yalnızca bu slaytı üret (deneme)")
    args = ap.parse_args()
    fps = args.fps
    slides = M.slides_content()
    out = M.ROOT / args.out
    ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    order = [args.only] if args.only else list(range(1, 8))
    demo = Demo(fps) if 5 in order or 4 in order or 6 in order else None
    t_start, nframes = time.time(), 0

    def render(n, t):
        """Slayt n'in (ya da demo bölümünün) t anındaki karesi."""
        s, dur = slides[n - 1], DUR[n]
        if n == 5 and t >= DEMO_INTRO:
            fr = demo.frame(int((t - DEMO_INTRO) * fps))
            im = demo_frame_full(fr, t)
            if t < DEMO_INTRO + XFADE:                  # slayttan demoya geçiş
                a = (t - DEMO_INTRO) / XFADE
                im = Image.blend(slide_frame(s, s["_base"], DEMO_INTRO, DEMO_INTRO, demo.frame(0)), im, a)
            return im
        fr0 = demo.frame(0) if n == 5 else None
        return slide_frame(s, s["_base"], t, dur if n != 5 else DEMO_INTRO, fr0)

    for n in order:
        schedule(slides[n - 1], DUR[n] if n != 5 else DEMO_INTRO)
        slides[n - 1]["_base"] = base_layer(slides[n - 1])
    for oi, n in enumerate(order):
        dur = DUR[n]
        nxt = order[oi + 1] if oi + 1 < len(order) else None
        for fi in range(round(dur * fps)):
            t = fi / fps
            im = render(n, t)
            if nxt and t > dur - XFADE:               # sonraki slayta çapraz geçiş
                a = (t - (dur - XFADE)) / XFADE
                im = Image.blend(im, render(nxt, 0.0) if nxt != 5 else render(5, 0.0), a)
            text, sa = sub_at(n, t, dur)
            subtitle(im, text, sa)
            ff.stdin.write(im.convert("RGB").tobytes())
            nframes += 1
        print(f"slayt {n}: {dur} sn, toplam {nframes} kare, {time.time() - t_start:.0f} sn", flush=True)
    ff.stdin.close()
    ff.wait()
    if demo:
        demo.p.stdout.close()
        demo.p.kill()
    print(f"{out.relative_to(M.ROOT)}: {nframes / fps:.1f} sn, {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
