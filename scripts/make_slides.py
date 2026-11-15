"""E15 – Sunum: docs/SLAYTLAR.md → docs/sunum/MarsTrail.pptx (+ PDF, + PNG kontrol görüntüleri).

Çalıştır (proje kökünden):
    venv\\Scripts\\python scripts\\make_slides.py          # PPTX + taşma kontrolü + önizleme PNG'leri
    venv\\Scripts\\python scripts\\make_slides.py --pdf    # + LibreOffice ile PDF, PDF'ten slayt PNG'leri

Çıktı:
    docs/sunum/MarsTrail.pptx        16:9, koyu tema (uygulamanın renkleri), konuşma metinleri slayt notlarında
    docs/sunum/MarsTrail.pdf         --pdf ile (LibreOffice: soffice --headless --convert-to pdf)
    docs/sunum/png/slayt_N.png       --pdf ile, PDF'ten (PyMuPDF) → LibreOffice'in gerçek çizimi
    docs/sunum/onizleme/slayt_N.png  aynı yerleşimin PIL ile çizimi (LibreOffice yokken hızlı göz kontrolü)

Taşma kontrolü: her metin kutusu, PowerPoint'te kullanılan yazı tipiyle (Segoe UI, C:\\Windows\\Fonts) PIL'de
ölçülüp kelime kelime satırlara bölünür; satır yüksekliği 1,33 × punto (Segoe UI'nin ascent+descent'i).
Kutuya sığmayan metin varsa betik hata verip durur → slayt elle sayı ya da metin kısaltılarak düzeltilir.
Kural: NASA logosu, bayrağı ya da görev arması yok; kaynaklar alt bilgide metin olarak.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
OUT = ROOT / "docs" / "sunum"
W_IN, H_IN = 13.333, 7.5
FONT = "Segoe UI"
FONT_FILES = {False: "C:/Windows/Fonts/segoeui.ttf", True: "C:/Windows/Fonts/segoeuib.ttf"}
LH = 1.33            # Segoe UI tek satır aralığı ≈ 1,33 em (PowerPoint "tek")
INSET_X, INSET_Y = 0.08, 0.04   # metin kutusu iç boşlukları (inç)

# Uygulamanın renkleri (web/style.css :root)
BG, PANEL, BORDER = "0d0b0a", "16120f", "3a2c24"
TEXT, MUTED, ACCENT = "f1e9e4", "b39c90", "ff7a2f"
GREEN, RED = "2ecc71", "e74c3c"

SRC = "Veri: NASA/JPL-Caltech, USGS, ASU (THEMIS), University of Arizona (HiRISE)"


# ---------------------------------------------------------------- yerleşim öğeleri
def P(text, size, color=TEXT, bold=False, gap=0):
    """Paragraf: metin, punto, renk, kalın, sonrasında boşluk (pt)."""
    return {"text": text, "size": size, "color": color, "bold": bold, "gap": gap}


def T(x, y, w, h, paras, align="l", valign="t"):
    return {"k": "text", "x": x, "y": y, "w": w, "h": h, "paras": paras if isinstance(paras, list) else [paras],
            "align": align, "valign": valign}


def R(x, y, w, h, fill=PANEL, line=None, round_=True):
    return {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line, "round": round_}


def TRI(x, y, w, h, fill=ACCENT):
    """Oynat simgesi: sağa bakan üçgen (▶ karakteri Segoe UI'da yok, şekil olarak çizilir)."""
    return {"k": "tri", "x": x, "y": y, "w": w, "h": h, "fill": fill}


def I(path, x, y, w, h, crop=None):
    """Görsel kutuya oran korunarak sığdırılır ve ortalanır. crop: (sol, üst, sağ, alt) piksel."""
    return {"k": "img", "path": Path(path), "x": x, "y": y, "w": w, "h": h, "crop": crop}


# ---------------------------------------------------------------- ölçüm
_fonts = {}


def font(size_pt, bold, dpi):
    key = (size_pt, bold, dpi)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_FILES[bold], max(1, round(size_pt * dpi / 72)))
    return _fonts[key]


def wrap(text, size, bold, width_in, dpi=144):
    f = font(size, bold, dpi)
    maxw = width_in * dpi
    lines = []
    for raw in text.split("\n"):
        words, cur = raw.split(" "), ""
        for wd in words:
            cand = wd if not cur else cur + " " + wd
            if f.getlength(cand) <= maxw:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                if f.getlength(wd) > maxw:
                    raise ValueError(f"tek kelime kutudan geniş: {wd!r} ({size} pt)")
                cur = wd
        lines.append(cur)
    return lines


def text_height(el):
    inner_w = el["w"] - 2 * INSET_X
    hpt = 0
    for p in el["paras"]:
        n = len(wrap(p["text"], p["size"], p["bold"], inner_w))
        hpt += n * p["size"] * LH + p["gap"]
    return hpt / 72 + 2 * INSET_Y


def check(slides):
    bad = []
    for si, s in enumerate(slides, 1):
        for el in s["els"]:
            if el["x"] < -0.001 or el["y"] < -0.001 or el["x"] + el["w"] > W_IN + 0.001 or el["y"] + el["h"] > H_IN + 0.001:
                bad.append(f"slayt {si}: öğe sayfa dışına taşıyor ({el['k']} @ {el['x']:.2f},{el['y']:.2f})")
            if el["k"] == "text":
                try:
                    need = text_height(el)
                except ValueError as e:
                    bad.append(f"slayt {si}: {e}")
                    continue
                if need > el["h"] + 0.005:
                    bad.append(f"slayt {si}: metin taşıyor ({need:.2f} > {el['h']:.2f} inç): {el['paras'][0]['text'][:50]!r}")
    return bad


# ---------------------------------------------------------------- görseller
def prepared_image(el):
    """Kırpma gerekiyorsa docs/sunum/img/ altına kırpılmış kopyayı yazar; (yol, piksel boyutu) döndürür."""
    src = el["path"]
    if not el["crop"]:
        return src, Image.open(src).size
    dst = OUT / "img" / f"{src.stem}_kirp{src.suffix}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).crop(el["crop"])
    im.save(dst)
    return dst, im.size


def fit(el, size):
    iw, ih = size
    s = min(el["w"] / iw, el["h"] / ih)
    w, h = iw * s, ih * s
    return el["x"] + (el["w"] - w) / 2, el["y"] + (el["h"] - h) / 2, w, h


# ---------------------------------------------------------------- PPTX
def rgb(h):
    return RGBColor.from_string(h)


def build_pptx(slides, path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W_IN), Inches(H_IN)
    blank = prs.slide_layouts[6]
    for s in slides:
        sl = prs.slides.add_slide(blank)
        bg = sl.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(BG)
        for el in s["els"]:
            if el["k"] == "rect":
                shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if el["round"] else MSO_SHAPE.RECTANGLE,
                                          Inches(el["x"]), Inches(el["y"]), Inches(el["w"]), Inches(el["h"]))
                if el["round"]:
                    shp.adjustments[0] = min(0.5, 0.08 / min(el["w"], el["h"]))
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(el["fill"])
                if el["line"]:
                    shp.line.color.rgb = rgb(el["line"])
                    shp.line.width = Pt(1.25)
                else:
                    shp.line.fill.background()
                shp.shadow.inherit = False
                shp.text_frame.text = ""
            elif el["k"] == "tri":
                # ikizkenar üçgen tepe yukarıda çizilir; 90° döndürünce sağa bakar (döndürme kutunun merkezinde)
                cx, cy = el["x"] + el["w"] / 2, el["y"] + el["h"] / 2
                shp = sl.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(cx - el["h"] / 2), Inches(cy - el["w"] / 2),
                                          Inches(el["h"]), Inches(el["w"]))
                shp.rotation = 90
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(el["fill"])
                shp.line.fill.background()
                shp.shadow.inherit = False
            elif el["k"] == "img":
                p, size = prepared_image(el)
                x, y, w, h = fit(el, size)
                sl.shapes.add_picture(str(p), Inches(x), Inches(y), Inches(w), Inches(h))
            else:
                tb = sl.shapes.add_textbox(Inches(el["x"]), Inches(el["y"]), Inches(el["w"]), Inches(el["h"]))
                tf = tb.text_frame
                tf.word_wrap = True
                tf.auto_size = None
                tf.margin_left = tf.margin_right = Inches(INSET_X)
                tf.margin_top = tf.margin_bottom = Inches(INSET_Y)
                tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[el["valign"]]
                for i, p in enumerate(el["paras"]):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[el["align"]]
                    para.space_after = Pt(p["gap"])
                    para.space_before = Pt(0)
                    para.line_spacing = 1.0
                    r = para.add_run()
                    r.text = p["text"]
                    r.font.name = FONT
                    r.font.size = Pt(p["size"])
                    r.font.bold = p["bold"]
                    r.font.color.rgb = rgb(p["color"])
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = s["notes"]
    prs.save(path)


# ---------------------------------------------------------------- önizleme (PIL)
def render_preview(slides, outdir, dpi=110):
    outdir.mkdir(parents=True, exist_ok=True)
    hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))   # noqa: E731
    for si, s in enumerate(slides, 1):
        im = Image.new("RGB", (round(W_IN * dpi), round(H_IN * dpi)), hexc(BG))
        d = ImageDraw.Draw(im)
        px = lambda v: round(v * dpi)   # noqa: E731
        for el in s["els"]:
            if el["k"] == "rect":
                d.rounded_rectangle([px(el["x"]), px(el["y"]), px(el["x"] + el["w"]), px(el["y"] + el["h"])],
                                    radius=px(0.08) if el["round"] else 0, fill=hexc(el["fill"]),
                                    outline=hexc(el["line"]) if el["line"] else None, width=2 if el["line"] else 0)
            elif el["k"] == "tri":
                d.polygon([(px(el["x"]), px(el["y"])), (px(el["x"] + el["w"]), px(el["y"] + el["h"] / 2)),
                           (px(el["x"]), px(el["y"] + el["h"]))], fill=hexc(el["fill"]))
            elif el["k"] == "img":
                p, size = prepared_image(el)
                x, y, w, h = fit(el, size)
                pic = Image.open(p).convert("RGB").resize((px(w), px(h)), Image.LANCZOS)
                im.paste(pic, (px(x), px(y)))
            else:
                inner_w = el["w"] - 2 * INSET_X
                blocks, total = [], 0
                for p in el["paras"]:
                    lines = wrap(p["text"], p["size"], p["bold"], inner_w)
                    blocks.append((p, lines))
                    total += (len(lines) * p["size"] * LH + p["gap"]) / 72
                y = el["y"] + INSET_Y
                if el["valign"] == "m":
                    y = el["y"] + (el["h"] - total) / 2
                elif el["valign"] == "b":
                    y = el["y"] + el["h"] - INSET_Y - total
                for p, lines in blocks:
                    f = font(p["size"], p["bold"], dpi)
                    for ln in lines:
                        lw = f.getlength(ln) / dpi
                        x = el["x"] + INSET_X
                        if el["align"] == "c":
                            x = el["x"] + (el["w"] - lw) / 2
                        elif el["align"] == "r":
                            x = el["x"] + el["w"] - INSET_X - lw
                        d.text((px(x), px(y + p["size"] * (LH - 1) / 2 / 72)), ln, font=f, fill=hexc(p["color"]))
                        y += p["size"] * LH / 72
                    y += p["gap"] / 72
        im.save(outdir / f"slayt_{si}.png")


# ---------------------------------------------------------------- içerik
def notes_from_md():
    """docs/SLAYTLAR.md'deki her slaytın "Konuşma metni" alıntısı → slayt notu."""
    md = (ROOT / "docs" / "SLAYTLAR.md").read_text(encoding="utf-8")
    parts = re.split(r"^## Slayt (\d)", md, flags=re.M)
    notes = {}
    for i in range(1, len(parts), 2):
        body = parts[i + 1].split("## Jüri")[0]
        q = [l[1:].strip() for l in body.splitlines() if l.startswith(">")]
        notes[int(parts[i])] = "\n".join(l for l in q if l)
    return notes


def chrome(n, kicker, title, source=SRC):
    """Her slaytta: üst bilgi (bölüm), başlık, alt bilgi (kaynak + sayfa)."""
    return [
        T(0.6, 0.32, 9.0, 0.36, P(kicker.upper(), 12, ACCENT, True)),
        T(0.6, 0.62, 12.1, 0.78, P(title, 30, TEXT, True)),
        R(0.6, 7.0, 12.13, 0.012, BORDER, round_=False),
        T(0.6, 7.04, 10.4, 0.34, P(source, 10, MUTED)),
        T(11.0, 7.04, 1.73, 0.34, P(f"MarsTrail · {n}/7", 10, MUTED), align="r"),
    ]


def stat(x, y, w, big, label, big_size=40, color=ACCENT, h_big=None, h_lab=0.62, lab_size=13):
    h_big = h_big or round(big_size * LH / 72 + 2 * INSET_Y + 0.03, 2)   # tek satır büyük sayı + iç boşluk
    return [T(x, y, w, h_big, P(big, big_size, color, True)),
            T(x, y + h_big, w, h_lab, P(label, lab_size, MUTED))]


def slides_content():
    notes = notes_from_md()
    S = []

    # 1 · Hikâye
    els = chrome(1, "Hikâye", "21 metre kalmıştı", "Kaynaklar: Apollo 14 görev raporu; NASA/JPL-Caltech (Opportunity, Spirit)")
    cards = [("1971", "Apollo 14 · Ay", "Krater kenarını bulamadılar. Nabız 150, oksijen azalıyor; Houston geri çağırdı. Kenara ~21 m kalmıştı."),
             ("2005", "Opportunity · Mars", "15 cm'lik bir kum dalgasında 5 haftadan fazla mahsur kaldı."),
             ("2009", "Spirit · Mars", "Sert kabuğun altındaki yumuşak kuma gömüldü; bir daha hareket edemedi.")]
    for k, (yr, who, txt) in enumerate(cards):
        x = 0.6 + k * 4.14
        els += [R(x, 1.7, 3.85, 3.05),
                T(x + 0.25, 1.85, 3.4, 0.9, P(yr, 44, ACCENT, True)),
                T(x + 0.25, 2.8, 3.4, 0.45, P(who, 18, TEXT, True)),
                T(x + 0.25, 3.3, 3.4, 1.35, P(txt, 15, MUTED))]
    els += [T(0.6, 5.05, 12.1, 0.62, P("Mars'ta Houston 3–22 dakika uzakta.", 26, TEXT)),
            T(0.6, 5.7, 12.1, 0.95, P("Kim “geri dön” diyecek?", 44, ACCENT, True))]
    S.append({"els": els, "notes": notes.get(1)})

    # 2 · MarsTrail
    els = chrome(2, "MarsTrail nedir", "Hazırlan · Planla · Yürü · Hayatta kal")
    els += [T(0.6, 1.65, 5.5, 1.25, [P("Sorun", 13, ACCENT, True),
                                     P("Apollo'nun dönüş kuralı sabit hızla hesaplanıyordu; saha testinde gerçek yürüyüş tahminden uzun sürdü.", 16, TEXT)]),
            T(0.6, 2.95, 5.5, 1.0, [P("Çözüm", 13, ACCENT, True),
                                    P("Nabız, yük, O₂ ve araziye göre canlı hesaplanan dönüş sınırı.", 16, TEXT)])]
    stages = [("1", "Hazırlık", "profil, sarf malzemesi"), ("2", "Planlama", "rota, Go/No-Go"),
              ("3", "Yürüyüş", "canlı O₂, dönüş noktası"), ("4", "Acil durum", "arama alanı, İHA")]
    for k, (num, name, sub) in enumerate(stages):
        y = 4.15 + k * 0.68
        els += [R(0.6, y, 5.5, 0.58),
                T(0.72, y + 0.04, 0.5, 0.5, P(num, 20, ACCENT, True), valign="m"),
                T(1.2, y + 0.04, 1.9, 0.5, P(name, 16, TEXT, True), valign="m"),
                T(3.05, y + 0.04, 3.0, 0.5, P(sub, 13, MUTED), valign="m")]
    els += stat(6.6, 1.6, 6.1, "130 → 47 km²", "Ayşe'nin nabzı 85 → 150: güvenli (yeşil) bölge daralıyor", 40, h_lab=0.4)
    els += [R(6.6, 2.92, 6.13, 2.55, PANEL),
            I(FIG / "e8_zones.png", 6.7, 3.0, 5.93, 2.0, crop=(0, 245, 1590, 775)),
            T(6.7, 5.05, 5.93, 0.36, P("Yeşil: %25 payla dönüş · Sarı: pay yok · Kırmızı: dönüş yok", 12, MUTED), align="c")]
    els += stat(6.6, 5.62, 6.1, "≤ O₂ / 1,25", "yeşil bölge: gidiş + dönüş süresi, kalan O₂'nin %80'ini aşmaz", 32, h_lab=0.4)
    S.append({"els": els, "notes": notes.get(2)})

    # 3 · Veri hattı
    els = chrome(3, "Veri hattı", "~6 GB ham veri → 1,3 MB'lık grid")
    tiles = [("8", "açık veri seti"), ("3 → 1", "projeksiyon → tek 70 m grid"),
             ("1444", "boş HiRISE karosu atıldı (2590'dan)"), ("%2–98", "termal normalizasyon → 0–1")]
    for k, (big, lab) in enumerate(tiles):
        x = 0.6 + k * 3.07
        els += [R(x, 1.6, 2.9, 1.3)] + stat(x + 0.18, 1.62, 2.6, big, lab, 34, h_lab=0.52, lab_size=12)
    chips = ["D1 Perseverance konumları", "D2 Sürüş izi", "D3 Ingenuity uçuşları", "D4 THEMIS termal",
             "D5 CTX DEM 20 m", "D6 USGS jeoloji", "D7 Ham fotoğraflar", "D8 HiRISE 25 cm"]
    for k, c in enumerate(chips):
        x, y = 0.6 + (k % 4) * 3.07, 3.08 + (k // 4) * 0.46
        els += [R(x, y, 2.9, 0.38, "1f1915"), T(x + 0.05, y, 2.8, 0.38, P(c, 12, TEXT), valign="m")]
    els += [R(0.6, 4.1, 6.0, 2.78, PANEL), R(6.73, 4.1, 6.0, 2.78, PANEL),
            I(FIG / "d4_thermal_normalize.png", 0.7, 4.15, 5.8, 2.28),
            T(0.7, 6.45, 5.8, 0.38, P("Önce/sonra: termal eylemsizlik, %2–98 kırpma + 0–1", 12, MUTED), align="c"),
            I(FIG / "d6_geology_crop.png", 6.83, 4.15, 5.8, 2.28),
            T(6.83, 6.45, 5.8, 0.38, P("Önce/sonra: jeoloji 1304 → 118 poligon; 2 kaynak hatası düzeltildi", 12, MUTED), align="c")]
    S.append({"els": els, "notes": notes.get(3)})

    # 4 · Yöntemler
    els = chrome(4, "Yöntemler", "Füzyon skoru + kendi YOLO modelimiz")
    els += [T(0.6, 1.45, 12.1, 0.45, P("skor = 0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)     eğim > 25° ya da skor > 0,8 → geçilmez", 16, TEXT, True)),
            R(0.6, 1.95, 12.13, 2.05, PANEL),
            I(FIG / "fusion.png", 0.7, 2.0, 11.93, 1.95),
            T(0.6, 4.1, 2.45, 0.32, P("Örnek tespitler (val)", 11, MUTED)),
            I(FIG / "e6v2_s2_val_batch0_pred.jpg", 0.6, 4.42, 2.5, 2.5),
            T(3.3, 4.1, 5.5, 0.32, P("v1 → v2 model, aynı 51 karoluk val", 11, MUTED)),
            I(FIG / "e6v2_compare.png", 3.3, 4.42, 5.3, 2.5),
            T(8.8, 4.1, 2.2, 0.32, P("Sızıntısız bölme", 11, MUTED)),
            I(FIG / "e6v2_split.png", 8.8, 4.42, 2.14, 2.5)]
    els += stat(11.0, 4.1, 1.75, "0,78", "hücre doğruluğu (v1: 0,69)", 32, h_lab=0.55, lab_size=12)
    els += stat(11.0, 5.55, 1.75, "250", "elle kontrol edilen karo", 32, h_lab=0.55, lab_size=12)
    S.append({"els": els, "notes": notes.get(4)})

    # 5 · Demo
    els = chrome(5, "Demo", "Sol 34, Jezero: Ayşe deltaya yürüyor", "Ekran: MarsTrail uygulaması · taban harita: NASA Mars Trek (Viking mozaiği)")
    els += [R(0.6, 1.6, 7.6, 4.28, "120e0c", line=ACCENT),
            TRI(4.05, 2.85, 0.75, 0.9),
            T(0.6, 3.95, 7.6, 0.5, P("MarsTrail_Demo.mp4 · 30 sn", 20, TEXT, True), align="c"),
            T(0.6, 4.45, 7.6, 0.4, P("Video buraya: Ekle → Video → MarsTrail_Demo.mp4", 13, MUTED), align="c")]
    steps = [("0–5 sn", "Küre → Jezero"), ("5–10 sn", "Profil, O₂ bölgeleri"), ("10–16 sn", "YOLO katmanı, plan GO"),
             ("16–24 sn", "Nabız 150 → daralma"), ("24–30 sn", "Telsiz koptu, İHA")]
    for k, (t, lab) in enumerate(steps):
        x = 0.6 + k * 1.538
        els += [R(x, 6.02, 1.47, 0.86, "1f1915"),
                T(x + 0.02, 6.04, 1.43, 0.32, P(t, 11, ACCENT, True)),
                T(x + 0.02, 6.33, 1.43, 0.53, P(lab, 11, TEXT))]
    els += [I(FIG / "ui_1_plan_go.png", 8.5, 1.6, 4.23, 2.38)]
    facts = [("GO", "5,52 km · 243 dk; dönüşte 249 dk O₂", GREEN),
             ("NO-GO", "O₂ 220 + nabız 150: dönüş noktası T+67 dk", RED),
             ("İHA", "telsiz koptu: olasılığın %50'si 11,6 dk'da taranır", ACCENT)]
    for k, (tag, txt, col) in enumerate(facts):
        y = 4.15 + k * 0.92
        els += [R(8.5, y, 4.23, 0.8),
                T(8.6, y + 0.05, 1.15, 0.7, P(tag, 17, col, True), valign="m"),
                T(9.7, y + 0.05, 2.95, 0.7, P(txt, 12, TEXT), valign="m")]
    S.append({"els": els, "notes": notes.get(5)})

    # 6 · Doğrulama
    els = chrome(6, "Doğrulama", "Rover, kum dediğimiz yerden geçmemiş")
    els += [R(0.6, 1.6, 8.1, 5.28, "fcfcfb"),
            I(FIG / "e10_validation.png", 0.65, 1.65, 8.0, 5.18)]
    els += stat(9.0, 1.55, 3.75, "0,50 → 0,65", "AUC: skor Perseverance rotasını ayırt ediyor mu? (YOLO'suz → YOLO'lu, 52 rota hücresi)", 40, h_lab=0.85)
    els += stat(9.0, 3.3, 3.75, "%0 · %49", "kumlu hücre: rotada · çevrede", 40, h_lab=0.45)
    els += stat(9.0, 4.6, 3.75, "%100", "rota bizim haritada geçilebilir", 40, color=GREEN, h_lab=0.45)
    els += [T(9.0, 5.95, 3.75, 0.95, P("Sınır: kaya rotayı ayırt etmiyor (0,51); rotanın 52/397 hücresi HiRISE kapsamında. Rota verisi modele verilmedi.", 11, MUTED))]
    S.append({"els": els, "notes": notes.get(6)})

    # 7 · Etki + YZ beyanı
    els = chrome(7, "Etki · YZ beyanı", "Nerede olduklarını bilecekler", "Kod: github.com/tayancelifnur/marstrail · Veri: NASA/JPL-Caltech, USGS, ASU, University of Arizona")
    impact = [("Artemis ve Mars", "Gecikmeli iletişimde “geri dön” kararını sistem veriyor; telefon görünümü hazır, kask içi ekrana uyarlanabilir."),
              ("Dünya'da afet", "Aynı arama mantığı: kayıp kişi + kalan süre + arazi → arama alanı ve İHA rotası."),
              ("Açık", "Açık veri, açık kod; tarayıcıda çalışır, sunucu gerekmez.")]
    for k, (h, t) in enumerate(impact):
        y = 1.65 + k * 1.3
        els += [R(0.6, y, 6.0, 1.15),
                T(0.8, y + 0.08, 5.6, 0.42, P(h, 17, ACCENT, True)),
                T(0.8, y + 0.48, 5.6, 0.64, P(t, 13, TEXT))]
    els += [R(6.9, 1.65, 5.83, 3.75, PANEL, line=BORDER),
            T(7.1, 1.75, 5.45, 0.45, P("Yapay zekâ kullanım beyanı", 17, ACCENT, True)),
            T(7.1, 2.25, 5.45, 3.1, [P("• Kod ve veri işleme betikleri ekibin denetiminde Claude Code (Anthropic) ile yazıldı.", 15, TEXT, gap=9),
                                     P("• Etiketlerin ön taslağı Roboflow Auto Label'dan; 250 karonun hepsi Elif tarafından elle kontrol edilip düzeltildi.", 15, TEXT, gap=9),
                                     P("• Fikir, hikâye, veri seçimi, formül ve eşik kararları, etiket tanımları ve doğrulama ekibe ait.", 15, TEXT, gap=9),
                                     P("• Sayılar elle yazılmadı; betiklerle ölçüldü.", 15, TEXT)]),
            T(0.6, 5.65, 12.1, 0.6, P("Elif — veri, model, algoritmalar   ·   Gözde — arayüz", 18, TEXT, True)),
            T(0.6, 6.2, 12.1, 0.6, P("Teşekkürler.", 22, ACCENT, True))]
    S.append({"els": els, "notes": notes.get(7)})
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="LibreOffice ile PDF ve PDF'ten PNG")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    slides = slides_content()
    bad = check(slides)
    if bad:
        print("TAŞMA / YERLEŞİM HATASI:\n  " + "\n  ".join(bad))
        sys.exit(1)
    pptx = OUT / "MarsTrail.pptx"
    build_pptx(slides, pptx)
    render_preview(slides, OUT / "onizleme")
    print(f"{pptx.relative_to(ROOT)}: {len(slides)} slayt, taşma yok; önizleme docs/sunum/onizleme/")
    if args.pdf:
        soffice = shutil.which("soffice") or next((p for p in [r"C:\Program Files\LibreOffice\program\soffice.exe",
                                                                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
                                                   if Path(p).exists()), None)
        if not soffice:
            sys.exit("LibreOffice bulunamadı: winget install TheDocumentFoundation.LibreOffice")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(pptx)], check=True)
        import pymupdf
        doc = pymupdf.open(OUT / "MarsTrail.pdf")
        (OUT / "png").mkdir(exist_ok=True)
        for i, page in enumerate(doc, 1):
            page.get_pixmap(dpi=110).save(OUT / "png" / f"slayt_{i}.png")
        print(f"docs/sunum/MarsTrail.pdf: {len(doc)} sayfa → docs/sunum/png/")


if __name__ == "__main__":
    main()
