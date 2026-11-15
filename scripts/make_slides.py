"""E15 – Sunum: docs/SLAYTLAR.md → docs/sunum/MarsTrail.pptx (+ PDF, + PNG kontrol görüntüleri).

Çalıştır (proje kökünden):
    venv\\Scripts\\python scripts\\make_slides.py          # PPTX + taşma kontrolü + önizleme PNG'leri
    venv\\Scripts\\python scripts\\make_slides.py --pdf    # + LibreOffice ile PDF, PDF'ten slayt PNG'leri

Çıktı:
    docs/sunum/MarsTrail.pptx        16:9, koyu tema (uygulamanın renkleri), Calibri; konuşma metinleri slayt notlarında
                                     Hareket: her slaytta geçiş (fade / push), grafikler slayt açılınca yakınlaşarak
                                     (zoom) gelir, büyük sayılar ve kartlar tıklamayla sırayla belirir (fade).
                                     Slayt 5: docs/sunum/demo.mp4 gömülü, ilk tıklamada baştan oynar (Gözde'nin düzeni).
    docs/sunum/MarsTrail.pdf         --pdf ile (LibreOffice: soffice --headless --convert-to pdf)
    docs/sunum/png/slayt_N.png       --pdf ile, PDF'ten (PyMuPDF) → LibreOffice'in gerçek çizimi
    docs/sunum/onizleme/slayt_N.png  aynı yerleşimin PIL ile çizimi (son hâl: bütün animasyonlar bitmiş)

Yazı tipi Calibri: her Windows/Office kurulumunda var, LibreOffice'te ölçüsü aynı Carlito'ya düşer. Arial'de "₂"
(O₂) karakteri yok, bu yüzden seçilmedi. Satır yüksekliği 1,22 em (Calibri hhea: ascent + descent + lineGap).
Taşma kontrolü: her metin kutusu calibri.ttf ile PIL'de ölçülüp kelime kelime satırlara bölünür; sığmayan metin
varsa betik durur. scripts/make_video.py aynı yerleşimi ve çizim fonksiyonunu kullanır.
Kural: NASA logosu, bayrağı ya da görev arması yok; kaynaklar alt bilgide metin olarak.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
OUT = ROOT / "docs" / "sunum"
DEMO = OUT / "demo.mp4"
W_IN, H_IN = 13.333, 7.5
FONT = "Calibri"
FONT_FILES = {False: "C:/Windows/Fonts/calibri.ttf", True: "C:/Windows/Fonts/calibrib.ttf"}
LH = 1.22            # Calibri tek satır aralığı (hhea 1536 + 512 + 452 / 2048)
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


def T(x, y, w, h, paras, align="l", valign="t", count=False):
    """Metin kutusu. count=True: videoda ilk paragraftaki sayılar 0'dan sayarak gelir."""
    return {"k": "text", "x": x, "y": y, "w": w, "h": h, "paras": paras if isinstance(paras, list) else [paras],
            "align": align, "valign": valign, "count": count}


def R(x, y, w, h, fill=PANEL, line=None, round_=True):
    return {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line, "round": round_}


def I(path, x, y, w, h, crop=None):
    """Görsel kutuya oran korunarak sığdırılır ve ortalanır. crop: (sol, üst, sağ, alt) piksel."""
    return {"k": "img", "path": Path(path), "x": x, "y": y, "w": w, "h": h, "crop": crop}


def V(path, poster, x, y, w, h):
    """Gömülü video (PPTX'te add_movie). Önizlemede ve PIL çiziminde poster karesi görünür."""
    return {"k": "video", "path": Path(path), "poster": Path(poster), "x": x, "y": y, "w": w, "h": h, "crop": None}


def anim(els, kind, group=None, delay=0):
    """Hareket ata: kind "zoom" (slayt açılınca, grafikler) ya da "fade" (tıklama grubu `group`, grup içinde `delay` ms)."""
    for e in els:
        e["anim"] = {"kind": kind, "group": group, "delay": delay}
    return els


# ---------------------------------------------------------------- ölçüm
_fonts = {}


def font(size_pt, bold, dpi):
    key = (size_pt, bold, round(dpi, 3))
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
    src = el["poster"] if el["k"] == "video" else el["path"]
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


def demo_poster(t=9.0):
    """Demo videosundan poster karesi (nokta kartı anı) → docs/sunum/img/demo_poster.png."""
    dst = OUT / "img" / "demo_poster.png"
    if not dst.exists() or dst.stat().st_mtime < DEMO.stat().st_mtime:
        import imageio_ffmpeg
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-ss", str(t), "-i", str(DEMO),
                        "-frames:v", "1", str(dst)], check=True)
    return dst


# ---------------------------------------------------------------- PPTX: hareket (OOXML)
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _effect(ids, spid, kind, node, delay):
    """Tek bir giriş efekti: fade (presetID 10) ya da zoom (presetID 53, alt tür 16 = PowerPoint "Yakınlaştır")."""
    i0 = next(ids)
    preset = ('presetID="53" presetClass="entr" presetSubtype="16"' if kind == "zoom"
              else 'presetID="10" presetClass="entr" presetSubtype="0"')
    tgt = f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
    x = (f'<p:par><p:cTn id="{i0}" {preset} fill="hold" grpId="0" nodeType="{node}">'
         f'<p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>'
         f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
         f'{tgt}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
         f'<p:to><p:strVal val="visible"/></p:to></p:set>')
    if kind == "zoom":
        for attr in ("ppt_w", "ppt_h"):
            x += (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{next(ids)}" dur="600" fill="hold"/>{tgt}'
                  f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>'
                  f'<p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav>'
                  f'<p:tav tm="100000"><p:val><p:strVal val="#{attr}"/></p:val></p:tav></p:tavLst></p:anim>')
    x += (f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{next(ids)}" dur="{600 if kind == "zoom" else 500}"/>'
          f'{tgt}</p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>')
    return x


def _media_call(ids, spid, dur_ms):
    return (f'<p:par><p:cTn id="{next(ids)}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" '
            f'nodeType="clickEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="{next(ids)}" dur="{dur_ms}" fill="hold"/>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>')


def timing_xml(steps, video=None):
    """steps: [(tetik, [(spid, tür, gecikme_ms, metin_mi)])], tetik "auto" (slayt açılınca) ya da "click".
    video: (spid, süre_ms) → ilk tıklamada baştan oynat + <p:video> düğümü."""
    from itertools import count
    ids = count(3)
    pars, bld = "", []
    for trig, effs in steps:
        outer, inner = next(ids), next(ids)
        cond = ('<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>' if trig == "auto"
                else '<p:cond delay="indefinite"/>')
        body = ""
        for k, eff in enumerate(effs):
            if eff[1] == "media":
                body += _media_call(ids, eff[0], eff[2])
                continue
            spid, kind, delay, is_sp = eff
            node = ("afterEffect" if trig == "auto" else "clickEffect") if k == 0 else "withEffect"
            body += _effect(ids, spid, kind, node, delay)
            if is_sp and spid not in bld:
                bld.append(spid)
        pars += (f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst>{cond}</p:stCondLst><p:childTnLst>'
                 f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                 f'<p:childTnLst>{body}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    vnode = ""
    if video:
        vnode = (f'<p:video><p:cMediaNode vol="80000"><p:cTn id="{next(ids)}" fill="hold" display="0">'
                 f'<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn>'
                 f'<p:tgtEl><p:spTgt spid="{video[0]}"/></p:tgtEl></p:cMediaNode></p:video>')
    main = (f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{pars}'
            f'</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:nextCondLst></p:seq>') if pars else ""
    bldx = "".join(f'<p:bldP spid="{s}" grpId="0" animBg="1"/>' for s in bld)
    return (f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst>{main}{vnode}</p:childTnLst></p:cTn></p:par></p:tnLst>'
            + (f'<p:bldLst>{bldx}</p:bldLst>' if bldx else "") + '</p:timing>')


def transition_xml(kind):
    inner = '<p:push dir="u"/>' if kind == "push" else '<p:fade/>'
    return f'<p:transition xmlns:p="{P_NS}" spd="med">{inner}</p:transition>'


def set_motion(slide, transition, steps, video):
    sld = slide._element
    for tag in ("p:transition", "p:timing"):
        for old in sld.findall(qn(tag)):
            sld.remove(old)
    anchor = sld.find(qn("p:clrMapOvr"))
    idx = list(sld).index(anchor) + 1 if anchor is not None else len(sld)
    sld.insert(idx, etree.fromstring(transition_xml(transition)))
    if steps or video:
        sld.insert(idx + 1, etree.fromstring(timing_xml(steps, video)))


# ---------------------------------------------------------------- PPTX
def rgb(h):
    return RGBColor.from_string(h)


def video_ms(path):
    import imageio_ffmpeg
    n, sec = imageio_ffmpeg.count_frames_and_secs(str(path))
    return int(sec * 1000)


def build_pptx(slides, path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W_IN), Inches(H_IN)
    blank = prs.slide_layouts[6]
    for s in slides:
        sl = prs.slides.add_slide(blank)
        bg = sl.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(BG)
        auto, clicks, video = [], {}, None
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
                is_sp = True
            elif el["k"] == "img":
                p, size = prepared_image(el)
                x, y, w, h = fit(el, size)
                shp = sl.shapes.add_picture(str(p), Inches(x), Inches(y), Inches(w), Inches(h))
                is_sp = False
            elif el["k"] == "video":
                shp = sl.shapes.add_movie(str(el["path"]), Inches(el["x"]), Inches(el["y"]), Inches(el["w"]), Inches(el["h"]),
                                          poster_frame_image=str(el["poster"]), mime_type="video/mp4")
                shp.name = el["path"].name
                video = (shp.shape_id, video_ms(el["path"]))
                is_sp = False
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
                shp, is_sp = tb, True
            a = el.get("anim")
            if a and a["kind"] == "zoom":
                auto.append((shp.shape_id, "zoom", a["delay"], is_sp))
            elif a:
                clicks.setdefault(a["group"], []).append((shp.shape_id, "fade", a["delay"], is_sp))
        steps = ([("auto", auto)] if auto else [])
        groups = sorted(clicks)
        if video:   # Gözde'nin düzeni: videonun oynaması slayttaki ilk tıklama
            steps.append(("click", [(video[0], "media", video[1])]))
        steps += [("click", clicks[g]) for g in groups]
        set_motion(sl, s.get("transition", "fade"), steps, video)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = s["notes"]
    prs.save(path)


# ---------------------------------------------------------------- çizim (önizleme ve video ortak)
_img_cache = {}


def _hex(h, a=255):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _src_image(el, w_px, h_px):
    """Kutuya sığan boyutun 1,15 katında önceden ölçeklenmiş kaynak (Ken Burns kırpması için pay)."""
    key = (str(el.get("poster") or el["path"]), el["crop"], w_px, h_px)
    if key not in _img_cache:
        p, _ = prepared_image(el)
        im = Image.open(p).convert("RGB")
        _img_cache[key] = im.resize((max(1, round(w_px * 1.15)), max(1, round(h_px * 1.15))), Image.LANCZOS)
    return _img_cache[key]


def draw_el(canvas, el, dpi, ox=0, oy=0, alpha=1.0, scale=1.0, kb=1.0, text0=None, frame=None):
    """Tek öğeyi RGBA tuvale çizer. alpha: saydamlık, scale: giriş yakınlaşması (merkezden), kb: Ken Burns (kutu içinde
    yakınlaşma, 1 = yok), text0: ilk paragraf metni yerine (sayarak artan sayılar), frame: video karesi (PIL)."""
    if alpha <= 0:
        return
    px = lambda v: round(v * dpi)   # noqa: E731
    a8 = round(255 * alpha)
    if el["k"] in ("img", "video"):
        _, size = prepared_image(el) if frame is None else (None, frame.size)
        x, y, w, h = fit(el, size)
        wp, hp = px(w), px(h)
        if frame is not None:
            src = frame.resize((round(wp * 1.15), round(hp * 1.15)), Image.BILINEAR)
        else:
            src = _src_image(el, wp, hp)
        # Kaynak kutunun 1,15 katı çözünürlükte (yakınlaşınca bulanıklaşmasın): kb = 1 tüm görsel, kb > 1 merkezden 1/kb'lik pencere
        sw, sh = src.size
        cw, ch = sw / max(1.0, kb), sh / max(1.0, kb)
        crop = src.crop((round((sw - cw) / 2), round((sh - ch) / 2), round((sw + cw) / 2), round((sh + ch) / 2)))
        tw, th = max(1, round(wp * scale)), max(1, round(hp * scale))
        pic = crop.resize((tw, th), Image.BILINEAR).convert("RGBA")
        if a8 < 255:
            pic.putalpha(a8)
        canvas.alpha_composite(pic, (ox + px(x) + (wp - tw) // 2, oy + px(y) + (hp - th) // 2))
        return
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0)) if a8 < 255 else None
    d = ImageDraw.Draw(layer if layer is not None else canvas)
    if el["k"] == "rect":
        d.rounded_rectangle([ox + px(el["x"]), oy + px(el["y"]), ox + px(el["x"] + el["w"]), oy + px(el["y"] + el["h"])],
                            radius=px(0.08) if el["round"] else 0, fill=_hex(el["fill"], a8),
                            outline=_hex(el["line"], a8) if el["line"] else None, width=max(1, px(0.017)) if el["line"] else 0)
    elif el["k"] == "tri":
        d.polygon([(ox + px(el["x"]), oy + px(el["y"])), (ox + px(el["x"] + el["w"]), oy + px(el["y"] + el["h"] / 2)),
                   (ox + px(el["x"]), oy + px(el["y"] + el["h"]))], fill=_hex(el["fill"], a8))
    else:
        inner_w = el["w"] - 2 * INSET_X
        blocks, total = [], 0
        for i, p in enumerate(el["paras"]):
            txt = text0 if (i == 0 and text0 is not None) else p["text"]
            lines = wrap(txt, p["size"], p["bold"], inner_w) if txt else [""]
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
                d.text((ox + px(x), oy + px(y + p["size"] * (LH - 1) / 2 / 72)), ln, font=f, fill=_hex(p["color"], a8))
                y += p["size"] * LH / 72
            y += p["gap"] / 72
    if layer is not None:
        canvas.alpha_composite(layer)


def render_preview(slides, outdir, dpi=110):
    outdir.mkdir(parents=True, exist_ok=True)
    for si, s in enumerate(slides, 1):
        im = Image.new("RGBA", (round(W_IN * dpi), round(H_IN * dpi)), _hex(BG))
        for el in s["els"]:
            draw_el(im, el, dpi)
        im.convert("RGB").save(outdir / f"slayt_{si}.png")


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
        T(0.6, 0.62, 12.1, 0.78, P(title, 32, TEXT, True)),
        R(0.6, 7.0, 12.13, 0.012, BORDER, round_=False),
        T(0.6, 7.04, 10.4, 0.34, P(source, 10, MUTED)),
        T(11.0, 7.04, 1.73, 0.34, P(f"MarsTrail · {n}/7", 10, MUTED), align="r"),
    ]


def stat(x, y, w, big, label, big_size=40, color=ACCENT, h_big=None, h_lab=0.62, lab_size=13, count=True):
    h_big = h_big or round(big_size * LH / 72 + 2 * INSET_Y + 0.03, 2)   # tek satır büyük sayı + iç boşluk
    return [T(x, y, w, h_big, P(big, big_size, color, True), count=count),
            T(x, y + h_big, w, h_lab, P(label, lab_size, MUTED))]


def slides_content():
    notes = notes_from_md()
    S = []

    # 1 · Hikâye
    els = chrome(1, "Hikâye", "~30 metre kalmıştı", "Kaynaklar: Apollo 14 görev raporu; LROC/ASU (PIA12897); NASA/JPL-Caltech, PIA07999 (Opportunity), Spirit")
    cards = [("1971", "Apollo 14 · Ay", "Krater kenarını bulamadılar. Nabız 150, oksijen azalıyor; Houston geri çağırdı. Kenara ~30 m kalmıştı (LROC/ASU)."),
             ("2005", "Opportunity · Mars", "~30 cm yüksekliğinde bir kum dalgasında 5 haftadan fazla mahsur kaldı."),
             ("2009", "Spirit · Mars", "Sert kabuğun altındaki yumuşak kuma gömüldü; bir daha hareket edemedi.")]
    for k, (yr, who, txt) in enumerate(cards):
        x = 0.6 + k * 4.14
        els += anim([R(x, 1.7, 3.85, 3.05),
                     T(x + 0.25, 1.85, 3.4, 0.9, P(yr, 46, ACCENT, True)),
                     T(x + 0.25, 2.8, 3.4, 0.45, P(who, 19, TEXT, True)),
                     T(x + 0.25, 3.3, 3.4, 1.35, P(txt, 16, MUTED))], "fade", 1, k * 450)
    els += anim([T(0.6, 5.05, 12.1, 0.62, P("Mars'ta Houston 3–22 dakika uzakta.", 26, TEXT))], "fade", 2)
    els += anim([T(0.6, 5.7, 12.1, 0.95, P("Kim “geri dön” diyecek?", 46, ACCENT, True))], "fade", 2, 600)
    S.append({"els": els, "notes": notes.get(1), "transition": "fade"})

    # 2 · MarsTrail
    els = chrome(2, "MarsTrail nedir", "Hazırlan · Planla · Yürü · Hayatta kal")
    els += [T(0.6, 1.65, 5.5, 1.25, [P("Sorun", 14, ACCENT, True),
                                     P("Apollo'nun dönüş kuralı sabit hızla hesaplanıyordu; saha testinde gerçek yürüyüş tahminden uzun sürdü.", 17, TEXT)]),
            T(0.6, 2.95, 5.5, 1.0, [P("Çözüm", 14, ACCENT, True),
                                    P("Nabız, yük, O₂ ve araziye göre canlı hesaplanan dönüş sınırı.", 17, TEXT)])]
    stages = [("1", "Hazırlık", "profil, sarf malzemesi"), ("2", "Planlama", "rota, Go/No-Go"),
              ("3", "Yürüyüş", "canlı O₂, dönüş noktası"), ("4", "Acil durum", "arama alanı, İHA")]
    for k, (num, name, sub) in enumerate(stages):
        y = 4.15 + k * 0.68
        els += anim([R(0.6, y, 5.5, 0.58),
                     T(0.72, y + 0.04, 0.5, 0.5, P(num, 21, ACCENT, True), valign="m"),
                     T(1.2, y + 0.04, 1.9, 0.5, P(name, 17, TEXT, True), valign="m"),
                     T(3.05, y + 0.04, 3.0, 0.5, P(sub, 14, MUTED), valign="m")], "fade", 1, k * 300)
    els += anim(stat(6.6, 1.6, 6.1, "130 → 47 km²", "Ayşe'nin nabzı 85 → 150: güvenli (yeşil) bölge daralıyor", 42, h_lab=0.42, lab_size=14), "fade", 2)
    els += [R(6.6, 2.97, 6.13, 2.5, PANEL)]
    els += anim([I(FIG / "e8_zones.png", 6.7, 3.05, 5.93, 1.98, crop=(0, 245, 1590, 775))], "zoom")
    els += [T(6.7, 5.06, 5.93, 0.36, P("Yeşil: %25 payla dönüş · Sarı: pay yok · Kırmızı: dönüş yok", 13, MUTED), align="c")]
    els += anim(stat(6.6, 5.62, 6.1, "≤ O₂ / 1,25", "yeşil bölge: gidiş + dönüş süresi, kalan O₂'nin %80'ini aşmaz", 34, h_lab=0.4,
                     lab_size=14, count=False), "fade", 3)
    S.append({"els": els, "notes": notes.get(2), "transition": "fade"})

    # 3 · Veri hattı
    els = chrome(3, "Veri hattı", "~6 GB ham veri → 1,3 MB'lık grid")
    tiles = [("8", "açık veri seti"), ("3 → 1", "projeksiyon → tek 70 m grid"),
             ("1444", "boş HiRISE karosu atıldı (2590'dan)"), ("%2–98", "termal normalizasyon → 0–1")]
    for k, (big, lab) in enumerate(tiles):
        x = 0.6 + k * 3.07
        els += anim([R(x, 1.6, 2.9, 1.3)] + stat(x + 0.18, 1.62, 2.6, big, lab, 36, h_lab=0.55, lab_size=13,
                                                    count=big in ("8", "1444")), "fade", 1, k * 400)
    chips = ["D1 Perseverance konumları", "D2 Sürüş izi", "D3 Ingenuity uçuşları", "D4 THEMIS termal",
             "D5 CTX DEM 20 m", "D6 USGS jeoloji", "D7 Ham fotoğraflar", "D8 HiRISE 25 cm"]
    for k, c in enumerate(chips):
        x, y = 0.6 + (k % 4) * 3.07, 3.08 + (k // 4) * 0.46
        els += [R(x, y, 2.9, 0.38, "1f1915"), T(x + 0.05, y, 2.8, 0.38, P(c, 13, TEXT), valign="m")]
    els += [R(0.6, 4.1, 6.0, 2.78, PANEL), R(6.73, 4.1, 6.0, 2.78, PANEL)]
    els += anim([I(FIG / "d4_thermal_normalize.png", 0.7, 4.15, 5.8, 2.28)], "zoom")
    els += anim([I(FIG / "d6_geology_crop.png", 6.83, 4.15, 5.8, 2.28)], "zoom", delay=300)
    els += [T(0.7, 6.45, 5.8, 0.38, P("Önce/sonra: termal eylemsizlik, %2–98 kırpma + 0–1", 13, MUTED), align="c"),
            T(6.83, 6.45, 5.8, 0.38, P("Önce/sonra: jeoloji 1304 → 118 poligon; 2 kaynak hatası düzeltildi", 13, MUTED), align="c")]
    S.append({"els": els, "notes": notes.get(3), "transition": "push"})

    # 4 · Yöntemler
    els = chrome(4, "Yöntemler", "Füzyon skoru + kendi YOLO modelimiz")
    els += [T(0.6, 1.45, 12.1, 0.45, P("skor = 0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)     eğim > 25° ya da skor > 0,8 → geçilmez", 17, TEXT, True)),
            R(0.6, 1.95, 12.13, 2.05, PANEL)]
    els += anim([I(FIG / "fusion.png", 0.7, 2.0, 11.93, 1.95)], "zoom")
    els += [T(0.6, 4.1, 2.45, 0.32, P("Örnek tespitler (val)", 12, MUTED)),
            T(3.3, 4.1, 5.5, 0.32, P("v1 → v2 model, aynı 51 karoluk val", 12, MUTED)),
            T(8.8, 4.1, 2.2, 0.32, P("Sızıntısız bölme", 12, MUTED))]
    els += anim([I(FIG / "e6v2_s2_val_batch0_pred.jpg", 0.6, 4.42, 2.5, 2.5)], "zoom", delay=250)
    els += anim([I(FIG / "e6v2_compare.png", 3.3, 4.42, 5.3, 2.5)], "zoom", delay=500)
    els += anim([I(FIG / "e6v2_split.png", 8.8, 4.42, 2.14, 2.5)], "zoom", delay=750)
    els += anim(stat(11.0, 4.1, 1.75, "0,78", "hücre doğruluğu (v1: 0,69)", 34, h_lab=0.55, lab_size=13), "fade", 1)
    els += anim(stat(11.0, 5.55, 1.75, "250", "elle kontrol edilen karo", 34, h_lab=0.55, lab_size=13), "fade", 1, 500)
    S.append({"els": els, "notes": notes.get(4), "transition": "fade"})

    # 5 · Demo  (Gözde'nin MarsTrail_Elif_demo.pptx düzeni: video yer tutucunun yerinde, 2. etiket "Nokta kartı")
    els = chrome(5, "Demo", "Sol 34, Jezero: Ayşe deltaya yürüyor", "Ekran: MarsTrail uygulaması · taban harita: NASA Mars Trek (Viking mozaiği)")
    els += [V(DEMO, demo_poster(), 0.6, 1.6, 7.6, 4.28)]
    steps = [("0–5 sn", "Küre → Jezero"), ("5–10 sn", "Nokta kartı, O₂ bölgeleri"), ("10–16 sn", "YOLO katmanı, plan GO"),
             ("16–24 sn", "Nabız 150 → daralma"), ("24–30 sn", "Telsiz koptu, İHA")]
    for k, (t, lab) in enumerate(steps):
        x = 0.6 + k * 1.538
        els += [R(x, 6.02, 1.47, 0.86, "1f1915"),
                T(x + 0.02, 6.04, 1.43, 0.32, P(t, 12, ACCENT, True)),
                T(x + 0.02, 6.33, 1.43, 0.53, P(lab, 12, TEXT))]
    els += anim([I(FIG / "ui_1_plan_go.png", 8.5, 1.6, 4.23, 2.38)], "zoom")
    facts = [("GO", "5,52 km · 243 dk; dönüşte 249 dk O₂", GREEN),
             ("NO-GO", "O₂ 220 + nabız 150: dönüş noktası T+67 dk", RED),
             ("İHA", "telsiz koptu: olasılığın %50'si 11,6 dk'da taranır", ACCENT)]
    for k, (tag, txt, col) in enumerate(facts):
        y = 4.15 + k * 0.92
        els += anim([R(8.5, y, 4.23, 0.8),
                     T(8.6, y + 0.05, 1.15, 0.7, P(tag, 18, col, True), valign="m"),
                     T(9.7, y + 0.05, 2.95, 0.7, P(txt, 13, TEXT), valign="m")], "fade", 1, k * 400)
    S.append({"els": els, "notes": notes.get(5), "transition": "fade"})

    # 6 · Doğrulama
    els = chrome(6, "Doğrulama", "Rover, kum dediğimiz yerden geçmemiş")
    els += [R(0.6, 1.6, 8.1, 5.28, "fcfcfb")]
    els += anim([I(FIG / "e10_validation.png", 0.65, 1.65, 8.0, 5.18)], "zoom")
    els += anim(stat(9.0, 1.55, 3.75, "0,50 → 0,65", "AUC: skor Perseverance rotasını ayırt ediyor mu? (YOLO'suz → YOLO'lu, 52 rota hücresi)", 42, h_lab=0.85, lab_size=14), "fade", 1)
    els += anim(stat(9.0, 3.3, 3.75, "%0 · %49", "kumlu hücre: rotada · çevrede", 42, h_lab=0.45, lab_size=14), "fade", 2)
    els += anim(stat(9.0, 4.6, 3.75, "%100", "rota bizim haritada geçilebilir", 42, color=GREEN, h_lab=0.45, lab_size=14), "fade", 3)
    els += anim([T(9.0, 5.95, 3.75, 0.95, P("Sınır: kaya rotayı ayırt etmiyor (0,51); rotanın 52/397 hücresi HiRISE kapsamında. Rota verisi modele verilmedi.", 12, MUTED))], "fade", 3, 500)
    S.append({"els": els, "notes": notes.get(6), "transition": "push"})

    # 7 · Etki + YZ beyanı
    els = chrome(7, "Etki · YZ beyanı", "Nerede olduklarını bilecekler", "Kod: github.com/tayancelifnur/marstrail · Veri: NASA/JPL-Caltech, USGS, ASU, University of Arizona")
    impact = [("Artemis ve Mars", "Gecikmeli iletişimde “geri dön” kararını sistem veriyor; telefon görünümü hazır, kask içi ekrana uyarlanabilir."),
              ("Ay · Artemis", "Aynı sistem Ay güney kutbu yürüyüşlerine uyarlanabilir."),
              ("Açık", "Açık veri, açık kod; tarayıcıda çalışır, sunucu gerekmez.")]
    for k, (h, t) in enumerate(impact):
        y = 1.65 + k * 1.3
        els += anim([R(0.6, y, 6.0, 1.15),
                     T(0.8, y + 0.08, 5.6, 0.42, P(h, 18, ACCENT, True)),
                     T(0.8, y + 0.48, 5.6, 0.64, P(t, 14, TEXT))], "fade", 1, k * 400)
    els += anim([R(6.9, 1.65, 5.83, 3.75, PANEL, line=BORDER),
                 T(7.1, 1.75, 5.45, 0.45, P("Yapay zekâ kullanım beyanı", 18, ACCENT, True)),
                 T(7.1, 2.25, 5.45, 3.1, [P("• Kod ve veri işleme betikleri ekibin denetiminde Claude Code (Anthropic) ile yazıldı.", 16, TEXT, gap=9),
                                          P("• Etiketlerin ön taslağı Roboflow Auto Label'dan; 250 karonun hepsi Elif tarafından elle kontrol edilip düzeltildi.", 16, TEXT, gap=9),
                                          P("• Fikir, hikâye, veri seçimi, formül ve eşik kararları, etiket tanımları ve doğrulama ekibe ait.", 16, TEXT, gap=9),
                                          P("• Sayılar elle yazılmadı; betiklerle ölçüldü.", 16, TEXT)])], "fade", 2)
    els += anim([T(0.6, 5.65, 12.1, 0.6, P("Elif — veri, model, algoritmalar   ·   Gözde — arayüz", 19, TEXT, True)),
                 T(0.6, 6.2, 12.1, 0.6, P("Teşekkürler.", 24, ACCENT, True))], "fade", 3)
    S.append({"els": els, "notes": notes.get(7), "transition": "fade"})
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
