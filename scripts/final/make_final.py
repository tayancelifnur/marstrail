"""
MarsTrail final sunumu: 10 bölüm × 30 sn. Tek kaynaktan üç çıktı, hepsi aynı zamanlamayla:

  docs/sunum/MarsTrail_final.mp4   1920×1080, 25 fps, sessiz; her cümlenin görseli o cümlenin saniyesinde belirir
  docs/sunum/MarsTrail_final.pptx  10 slayt, Calibri, koyu tema; her cümle = bir tıklama (görsel/sayı/kart/klip),
                                   konuşma metni her slaytın notlarında
  docs/KONUSMA_METNI.md            cümle cümle numaralı metin, video zaman kodu ve ekranda ne olduğu + jüri soruları

Konuşma hızı (scripts/final/ ses taslağı ölçümü): docs/sunum/ses_taslak.mp4, faster-whisper small (tr, GPU):
1088 kelime, 518 sn konuşma → 2,10 kelime/sn (duraklamalar dahil bütün kayıt 1,71). Cümle süresi =
kelime / 2,10 + 0,45 sn nefes; her bölüm 0,8 sn sonra başlar ve 30 sn'ye sığmak zorunda (betik kontrol eder).

Önce:  venv\\Scripts\\python scripts\\final\\assets.py   (klipler, ekran görüntüleri)
Sonra: venv\\Scripts\\python scripts\\final\\make_final.py [--no-video]
"""
import argparse
import re
import subprocess
import sys
import time
from itertools import count
from pathlib import Path

import imageio_ffmpeg
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import make_slides as M  # noqa: E402
from make_slides import ACCENT, BG, BORDER, GREEN, MUTED, PANEL, RED, TEXT, P, R, T  # noqa: E402

FIN = ROOT / "docs" / "sunum" / "img" / "final"
CL = FIN / "clips"
FIG = ROOT / "docs" / "figures"
OUT_PPTX = ROOT / "docs" / "sunum" / "MarsTrail_final.pptx"
OUT_MP4 = ROOT / "docs" / "sunum" / "MarsTrail_final.mp4"
OUT_MD = ROOT / "docs" / "KONUSMA_METNI.md"

RATE, PAUSE, LEAD, SLOT, XFADE, FPS = 2.10, 0.45, 0.8, 30.0, 0.6, 25
DPI = 144                                        # 13,333 × 7,5 inç → 1920 × 1080
W, H = 1920, 1080
MEDIA = (0.6, 1.5, 8.4, 4.725)                   # uygulama slaytlarında görüntü alanı (16:9)


# ------------------------------------------------------------------ öğe yardımcıları
def I(path, x, y, w, h, crop=None):
    return M.I(path, x, y, w, h, crop)


def V(name, x, y, w, h):
    return M.V(CL / f"{name}.mp4", CL / f"{name}_poster.png", x, y, w, h)


def g(els, k):
    """Öğeleri k'inci cümleye (tıklamaya) bağla."""
    return M.anim(els if isinstance(els, list) else [els], "fade", k)


def z(els):
    """Slayt açılınca yakınlaşarak gelen öğe (görseller)."""
    return M.anim(els if isinstance(els, list) else [els], "zoom")


def chrome(n, kicker, title, source):
    return [T(0.6, 0.32, 9.0, 0.36, P(kicker.upper(), 12, ACCENT, True)),
            T(0.6, 0.62, 12.1, 0.78, P(title, 30, TEXT, True)),
            R(0.6, 7.0, 12.13, 0.012, BORDER, round_=False),
            T(0.6, 7.04, 10.4, 0.34, P(source, 10, MUTED)),
            T(11.0, 7.04, 1.73, 0.34, P(f"MarsTrail · {n}/10", 10, MUTED), align="r")]


def card(x, y, w, h, head, body, head_color=ACCENT, body_size=13, head_size=13, fill=PANEL, line=BORDER):
    return [R(x, y, w, h, fill, line),
            T(x + 0.12, y + 0.08, w - 0.24, 0.34, P(head, head_size, head_color, True)),
            T(x + 0.12, y + 0.4, w - 0.24, h - 0.46, P(body, body_size, TEXT))]


def stat(x, y, w, big, label, color=ACCENT, size=44, count_=True, h_lab=0.5, lab_size=13):
    hb = round(size * M.LH / 72 + 2 * M.INSET_Y + 0.03, 2)
    return [T(x, y, w, hb, P(big, size, color, True), count=count_), T(x, y + hb, w, h_lab, P(label, lab_size, MUTED))]


def side_item(k, n_items, head, body):
    """Uygulama slaytlarında sağ sütundaki adım kartı."""
    gap = (4.85 - 0.08 * (n_items - 1)) / n_items
    y = 1.5 + (k - 1) * (gap + 0.08)
    return card(9.25, y, 3.48, gap, f"{k} · {head}", body, body_size=12)


# ------------------------------------------------------------------ içerik: 10 bölüm, cümleler + ekran
def slides():
    S = []
    # 1 · Hikâye
    els = chrome(1, "Hikâye", "Üç görev, aynı son",
                 "Kaynaklar: Apollo 14 görev raporu; LROC/ASU, NASA PIA12897; NASA/JPL-Caltech PIA07999; Spirit (NASA)")
    els += z(I(FIN / "ay.png", 8.3, 1.4, 4.4, 4.4))
    els += g(I(FIN / "mars.png", 8.3, 1.4, 4.4, 4.4), 4)
    els += g(card(0.6, 1.5, 7.3, 0.95, "1971 · AY · APOLLO 14", "Shepard ve Mitchell, Cone Krateri'nin kenarını arıyor."), 1)
    els += g(stat(0.6, 2.6, 2.3, "150", "nabız (atım/dk)", RED, h_lab=0.4) + [T(3.0, 2.78, 4.9, 0.6, P("Houston: “Geri dönün.”", 24, TEXT, True))], 2)
    els += g(stat(0.6, 3.75, 7.3, "~30 m", "kenara kalan mesafe · LROC/ASU (NASA PIA12897)", ACCENT, h_lab=0.4), 3)
    els += g(card(0.6, 5.0, 3.55, 1.1, "2005 · OPPORTUNITY", "~30 cm kum dalgası, 5 haftadan fazla saplı"), 4)
    els += g(card(4.3, 5.0, 3.6, 1.1, "2009 · SPIRIT", "Yumuşak kuma gömüldü, bir daha kıpırdayamadı"), 5)
    S.append({"els": els, "say": [
        ("1971, Ay: Shepard ve Mitchell, Cone Krateri'nin kenarını arıyor.", "Ay görseli; “1971 · Apollo 14” kartı"),
        ("İşaretleri bulamıyorlar, Shepard'ın nabzı 150'ye çıkıyor ve Houston diyor ki: geri dönün.", "Kırmızı “150” ve “Houston: Geri dönün.”"),
        ("Dönüyorlar. Yıllar sonra uydu fotoğrafı gösterdi: kenara yalnızca 30 metre kalmış.", "“~30 m” (LROC/ASU kaynağıyla)"),
        ("2005'te Opportunity, 30 santimlik bir kum dalgasına saplanıp beş haftadan fazla kaldı.", "Mars görseli; “2005 · Opportunity” kartı"),
        ("2009'da Spirit yumuşak kuma gömüldü ve bir daha hiç kıpırdayamadı.", "“2009 · Spirit” kartı")]})

    # 2 · Sorun
    els = chrome(2, "Sorun", "Durum değişiyor, plan değişmiyor", "Dünya–Mars ışık süresi: 0,37–2,68 AU / ışık hızı · bugünkü değer: web/marstime.js (Mars24)")
    els += z(I(FIN / "mars.png", 8.6, 1.4, 4.1, 4.1))
    events = (("APOLLO 14", "~30 m kala döndü"), ("OPPORTUNITY", "5+ hafta saplı"), ("SPIRIT", "kuma gömüldü"))
    els += g([e for k, (h, b) in enumerate(events) for e in card(0.6 + k * 2.45, 1.5, 2.35, 0.95, h, b, head_size=12, body_size=12)]
             + [T(0.6, 2.55, 7.3, 0.5, P("Sonuç hep aynı: başarısız görev", 18, RED, True))], 1)
    els += g(T(0.6, 3.1, 7.6, 0.75, P("Sebep teknik yetersizlik değil: durum değişince plan anında güncellenemedi.", 17)), 2)
    els += g(T(0.6, 3.85, 7.6, 0.6, P("Rover saplanırsa yenisi gönderilir. Ya o bir astronotsa?", 20, ACCENT, True)), 3)
    els += g(stat(0.6, 4.6, 3.3, "3–22 dk", "Mars → Houston, tek yön · bugün 10,9 dk", ACCENT, h_lab=0.6), 4)
    els += g(card(4.1, 4.6, 4.2, 1.7, "ÜSSÜN SABİT KURALI", "“Dönebileceğin kadar uzaklaş.”\nArazi, nabız ve kalan O₂ hesaba girmiyor.", body_size=14), 5)
    S.append({"els": els, "say": [
        ("Senaryolar farklı, sonuç hep aynı: başarısız görev.", "Üç olay kartı, “Sonuç hep aynı: başarısız görev”"),
        ("Sebep teknik yetersizlik değil; durum değişince plan anında güncellenemedi.", "Sebep cümlesi"),
        ("Rover saplanırsa yenisi gönderilir. Peki ya o bir astronotsa?", "“Ya o bir astronotsa?”"),
        ("Mars'tan Houston'a bir mesaj 3 ile 22 dakika sürüyor; bugün 10,9 dakika.", "“3–22 dk · bugün 10,9 dk”"),
        ("Üssün kuralı ise sabit: dönebileceğin kadar uzaklaş; ama bu kural araziyi, nabzı, kalan oksijeni bilmiyor.",
         "“Üssün sabit kuralı” kartı")]})

    # 3 · Çözüm
    els = chrome(3, "Çözüm", "Dünya'yı beklemeden, canlı", "O₂ bölgeleri: web/walkback.js (Dijkstra) · web/tests/e8.html: nabız 85 → 150, yeşil alan 130,1 → 46,85 km²")
    els += g(T(0.6, 1.5, 6.5, 1.0, P("MarsTrail", 48, ACCENT, True)), 1)
    els += g(T(0.6, 2.45, 6.5, 1.2, P("Astronota, Dünya'yı beklemeden nereye kadar gidip güvenle dönebileceğini canlı söyleyen yürüyüş asistanı.", 18)), 2)
    els += g([e for k, s in enumerate(("arazi", "yük", "kalan O₂", "nabız")) for e in
              (R(0.6 + k * 1.62, 3.75, 1.52, 0.5, PANEL, ACCENT), T(0.6 + k * 1.62, 3.75, 1.52, 0.5, P(s, 15, TEXT, True), align="c", valign="m"))], 3)
    els += g(stat(0.6, 4.35, 6.5, "130 → 47 km²", "Ayşe'nin nabzı 85 → 150: güvenli yeşil alan", GREEN, h_lab=0.4)
             + [I(FIG / "e8_zones.png", 7.3, 1.5, 5.4, 3.9, crop=(0, 240, 1050, 780))], 4)
    els += g([e for k, (h, b) in enumerate((("1 · HAZIRLAN", "Profil: O₂, nabız, yük"), ("2 · PLANLA", "Rota ve GO / NO-GO"),
                                            ("3 · YÜRÜ", "Canlı O₂ ve bölgeler"), ("4 · HAYATTA KAL", "Telsiz koptu: arama, İHA, kurtarma")))
              for e in card(0.6 + k * 3.05, 5.7, 2.95, 1.12, h, b)], 5)
    S.append({"els": els, "say": [
        ("İşte biz MarsTrail'i tam bunun için geliştirdik.", "“MarsTrail”"),
        ("MarsTrail, astronota Dünya'yı beklemeden nereye kadar gidip güvenle dönebileceğini canlı söylüyor.", "Tek cümlelik tanım"),
        ("Dönüş sınırını sabit hızla değil; araziye, yüke, kalan oksijene ve nabza göre hesaplıyoruz.", "Dört etiket: arazi · yük · kalan O₂ · nabız"),
        ("Ayşe'nin nabzı 85'ten 150'ye çıkınca güvenli yeşil alanı 130 kilometrekareden 47'ye iniyor.", "“130 → 47 km²” ve iki O₂ bölgesi haritası (nabız 85 / 150)"),
        ("Dört adım: hazırlan, planla, yürü, hayatta kal.", "Dört adım kartı")]})

    # 4 · Uygulama: hazırlan, planla
    mx, my, mw, mh = MEDIA
    els = chrome(4, "Uygulama · hazırlan, planla", "Yola çıkmadan önce", "Uygulamanın kendisi: tayancelifnur.github.io/marstrail · taban harita: NASA Mars Trek")
    els += g([I(FIN / "profil.png", mx, my, mw, mh)] + side_item(1, 4, "PROFİL", "O₂, nabız, yük, batarya, su, radyasyon"), 1)
    els += g([I(FIN / "nokta.png", mx, my, mw, mh)] + side_item(2, 4, "NOKTA TARİHÇESİ", "Keşif tarihi, Perseverance Sol'ü, fotoğraf"), 2)
    els += g([V("rota", mx, my, mw, mh)] + side_item(3, 4, "ROTA ÇİZ", "Engel, zorluk, yükseklik profili; denenmemiş rota uyarısı"), 3)
    els += g([V("plan", mx, my, mw, mh)] + side_item(4, 4, "GO / NO-GO", "O₂, gün batımı, kum, eğim, telsiz, batarya, su"), 4)
    S.append({"els": els, "say": [
        ("Her astronotun profili var: oksijen, nabız, yük, batarya, su ve radyasyon.", "Uygulama: Ayşe'nin profil formu"),
        ("Her noktanın tarihçesi var: ne zaman keşfedildi, Perseverance oraya hangi Sol'de geldi, ne gördü.",
         "Uygulama: delta önü kartı (tarihçe, Sol 415 fotoğrafı)"),
        ("Kendi rotanı çizebiliyorsun; sistem engelleri, zorluğu ve yükseklik profilini gösteriyor, denenmemiş rotaysa uyarıyor.",
         "Klip: rota çiziliyor, “Çizilen rota” kartı açılıyor"),
        ("Planla dediğinde en güvenli yolu buluyor ve oksijenden gün batımına yedi maddelik GO/NO-GO listesi çıkarıyor.",
         "Klip: Üs → Delta → Three Forks planı, GO")]})

    # 5 · Uygulama: yürü, hayatta kal
    els = chrome(5, "Uygulama · yürü, hayatta kal", "Yolda bir şey ters giderse", "web/rescue.js · web/tests/e13.html: İHA %50 → 11,6 dk; Ali O₂ 116 / 480 dk")
    els += g([V("pin", mx, my, mw, mh)] + side_item(1, 5, "CANLI YÜRÜYÜŞ", "O₂ canlı düşer; not pini, anlık bildirim"), 1)
    els += g([V("nabiz", mx, my, mw, mh)] + side_item(2, 5, "NABIZ 150", "Bölge daralır, dönüş noktası öne gelir"), 2)
    els += g([V("telsiz", mx, my, mw, mh)] + side_item(3, 5, "TELSİZ KOPTU", "Son konum + kalan O₂ → arama alanı"), 3)
    els += g(side_item(4, 5, "İHA", "Olasılığın %50'si 11,6 dakikada taranır"), 4)
    els += g(side_item(5, 5, "KURTARMA", "Ali: O₂ ihtiyacı 116 / 480 dk → YEŞİL"), 5)
    S.append({"els": els, "say": [
        ("Yürüyüş başladı; oksijen canlı düşüyor, yolda not pini bırakabiliyorsun.", "Klip: canlı yürüyüş, not pini ve bildirim"),
        ("Ayşe'nin nabzı 150'ye çıkıyor: güvenli alan daralıyor, dönüş noktası öne geliyor.", "Klip: nabız 150, bölge daralıyor"),
        ("Ve telsiz kopuyor; son konumdan, kalan oksijenle bir arama alanı çıkıyor.", "Klip: telsiz koptu, arama alanı ve İHA rotası"),
        ("İHA bu alanı zikzakla tarıyor, olasılığın yarısını 11,6 dakikada kapsıyor.", "“İHA: %50'si 11,6 dk” kartı"),
        ("Ali için kurtarma rotası çiziliyor; Ali'nin kendi oksijeninin yetip yetmediğini de hesaplıyoruz.",
         "Klip sonu: Ali'nin kurtarma rotası; “116 / 480 dk” kartı")]})

    # 6 · Nasıl yaptık: veri
    els = chrome(6, "Nasıl yaptık · veri", "8 açık veri seti → 1,3 MB'lık harita", "docs/DATA_PIPELINE.md, docs/VERI_ORNEKLERI.html · sayılar betikle ölçüldü (SAYI_DENETIMI.md)")
    ds = ["Perseverance konumları · 708", "Sürüş izi · 46 km", "Ingenuity uçuşları · 72", "THEMIS termal · 100 m",
          "CTX yükseklik · 20 m", "USGS jeoloji · 1:75.000", "Rover fotoğrafları · 1.795 kayıt", "HiRISE · 25 cm, 4,7 GB"]
    els += g([T(0.6, 1.5, 6.8, 0.6, P("8 açık veri seti · ~6 GB", 26, ACCENT, True))]
             + [T(0.6 + (k // 4) * 3.45, 2.15 + (k % 4) * 0.4, 3.4, 0.38, P("• " + s, 13)) for k, s in enumerate(ds)], 1)
    els += g(stat(0.6, 3.9, 2.8, "3 → 1", "projeksiyon → tek 70 m ızgara", count_=False, h_lab=0.6), 2)
    els += g(stat(3.55, 3.9, 3.85, "1.444 / 2.590", "boş HiRISE karosu atıldı · jeolojide 2 kaynak hatası düzeltildi", count_=False, h_lab=0.6)
             + [I(FIN / "karolar.png", 7.6, 1.5, 5.1, 1.66),
                T(7.6, 3.2, 5.1, 0.62, P("Kırmızı: NoData, atıldı · mavi: dokusuz, atıldı · yeşil: kullanılır (her biri 160 × 160 m)", 11, MUTED))], 3)
    els += g([I(FIG / "fusion.png", 7.6, 4.3, 5.1, 1.15),
              T(7.6, 5.5, 5.1, 0.6, P("skor = 0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)", 12, MUTED))], 4)
    els += g(stat(0.6, 5.4, 6.8, "1,3 MB", "tarayıcıda çalışan harita (256 × 256 hücre, 70 m)", GREEN, h_lab=0.45), 5)
    S.append({"els": els, "say": [
        ("NASA ve USGS'nin açık verisini kullandık: sekiz veri seti, yaklaşık 6 gigabayt.", "“8 açık veri seti · ~6 GB” ve veri listesi"),
        ("Üç farklı projeksiyonu tek bir 70 metrelik ızgarada birleştirdik.", "“3 → 1”"),
        ("2.590 HiRISE karosunun 1.444'ü boştu, attık; jeoloji haritasında iki kaynak hatasını düzelttik.", "“1.444 / 2.590” ve üç örnek karo (NoData, dokusuz, kullanılır)"),
        ("Eğim, kum, kaya ve termali tek bir zorluk skorunda birleştirdik.", "Füzyon görseli ve formül"),
        ("Geriye tarayıcıda çalışan 1,3 megabaytlık bir harita kaldı.", "“1,3 MB”")]})

    # 7 · Nasıl yaptık: model
    els = chrome(7, "Nasıl yaptık · model", "Kendi YOLOv8 modelimiz", "ml/ · docs/figures/e6v2_compare.json · Tobler + Dijkstra: web/walkback.js")
    els += g(T(0.6, 1.5, 6.4, 0.9, P("YOLOv8 · HiRISE 25 cm · kum dalgası ve kaya", 22, TEXT, True)), 1)
    els += g(stat(0.6, 2.4, 6.4, "250 karo · 1.033 kutu", "hepsi elle kontrol edildi (kırmızı kaya, turuncu kaya alanı, sarı kum)", count_=False, h_lab=0.6)
             + [I(FIN / "etiket.png", 7.2, 1.5, 5.5, 2.7)], 2)
    els += g([T(0.6, 3.85, 6.4, 0.85, P("5 kurulum karşılaştırıldı · komşu karolar aynı tarafta → veri sızıntısı yok", 16)),
              I(FIG / "e6v2_compare.png", 7.2, 4.35, 5.5, 2.2)], 3)
    els += g(stat(0.6, 4.75, 6.4, "%78", "hücre düzeyinde dengeli doğruluk (ilk modelde %69)", GREEN, h_lab=0.45), 4)
    els += g(T(0.6, 6.12, 6.4, 0.75, P("Tobler + Dijkstra · sunucusuz · < 100 ms", 18, ACCENT, True)), 5)
    S.append({"els": els, "say": [
        ("Metre ölçeğindeki kumu ve kayayı görmek için kendi YOLOv8 modelimizi eğittik.", "“YOLOv8 · HiRISE 25 cm”"),
        ("250 HiRISE karosundaki 1.033 kutuyu tek tek elle kontrol ettik.", "“250 karo · 1.033 kutu” ve iki etiketli karo"),
        ("Beş kurulumu karşılaştırdık; komşu karoları aynı tarafa koyarak veri sızıntısını engelledik.", "Sızıntısız bölme cümlesi ve v1/v2 karşılaştırma grafiği"),
        ("Sonuç: hücre düzeyinde yüzde 78 dengeli doğruluk.", "“%78”"),
        ("Rotayı Tobler formülü ve Dijkstra ile buluyoruz; sunucu yok, hesap 100 milisaniyenin altında.", "“Tobler + Dijkstra · sunucusuz · < 100 ms”")]})

    # 8 · Doğrulama
    els = chrome(8, "Doğrulama", "Perseverance'ın gerçek rotasıyla sınadık", "scripts/validate.py → docs/figures/e10_validation.json · AUC: Mann–Whitney, bootstrap %95 [+0,12, +0,18]")
    els += g(T(0.6, 1.5, 7.0, 0.8, P("Haritamız doğru mu?", 30, TEXT, True)), 1)
    els += g([T(0.6, 2.3, 7.0, 0.95, P("Perseverance'ın gerçek sürüş izi (397 hücre) modele hiç verilmedi; sınav olarak saklandı.", 16)),
              I(FIG / "e10_validation.png", 8.0, 1.5, 4.7, 4.6, crop=(560, 530, 985, 940))], 2)
    els += g(stat(0.6, 3.3, 7.0, "0,498 → 0,649", "AUC, HiRISE bölgesi: YOLO'suz → YOLO'lu (0,5 = yazı tura)", h_lab=0.45), 3)
    els += g(stat(0.6, 4.65, 3.3, "%0", "rotadaki 52 hücrede kum", GREEN, h_lab=0.45) + stat(4.0, 4.65, 3.3, "%49", "çevredeki hücrelerde kum", RED, h_lab=0.45), 4)
    els += g(T(0.6, 6.12, 7.2, 0.7, P("Rotanın %100'ü haritamızda geçilebilir.", 18, GREEN, True)), 5)
    S.append({"els": els, "say": [
        ("Peki haritamız doğru mu?", "“Haritamız doğru mu?”"),
        ("Perseverance'ın gerçekten sürdüğü yolu modele hiç vermedik, sınav olarak sakladık.", "Rota haritası (mavi: Perseverance)"),
        ("YOLO olmadan skorumuz rotayı ayırt edemiyordu: 0,498, yani yazı tura. YOLO'yla 0,649.", "“0,498 → 0,649”"),
        ("Rover'ın geçtiği 52 hücrenin hiçbiri bizim haritamızda kumlu değil; çevresinde bu oran yüzde 49.", "“%0” ve “%49”"),
        ("Yani NASA ekibinin seçtiği yolu bizim haritamız da güvenli buluyor.", "“Rotanın %100'ü geçilebilir”")]})

    # 9 · Rakip analizi
    els = chrome(9, "Rakip analizi", "Herkes bir parçayı yapıyor",
                 "Kaynaklar: SEXTANT (MIT DSpace), xGDS/Minerva (NASA NTRS, software.nasa.gov), SPOC (NASA JPL), NOAH-H (Open University, Icarus 2022), Mars Trek (trek.nasa.gov)")
    cols = [(0.6, 2.0, "Araç"), (2.65, 1.95, "Kimden"), (4.65, 4.75, "Ne yapıyor"), (9.45, 3.28, "Nasıl çalışıyor")]
    rows = [("SEXTANT", "MIT · NASA BASALT", "EVA rotası; her noktadan eve en verimli dönüş (walkback) yolu", "Planlama aracı (MATLAB → Python)"),
            ("xGDS / Minerva", "NASA Ames", "Analog EVA'larda plan, not, fotoğraf ve veri senkronu", "Bilim ekibi için web araçları"),
            ("SPOC", "NASA JPL", "Rover görüntüsünde arazi sınıflandırma (kum, kaya…)", "Derin öğrenme · rover sürüşü"),
            ("NOAH-H", "Open University · ExoMars", "HiRISE'ta 14 sınıflı arazi dokusu haritası", "Derin öğrenme · iniş alanı analizi"),
            ("NASA Mars Trek", "NASA", "Mars verisini katmanlama, ölçüm, yükseklik profili", "Web portalı, kurulum yok"),
            ("MarsTrail", "Biz", "Canlı nabız ve O₂ ile değişen dönüş bölgeleri · GO/NO-GO · telsiz koptu → arama, İHA, kurtarma",
             "Açık veri · tarayıcıda · sunucusuz")]
    rh, y0 = 0.64, 1.5
    hdr = [R(0.6, y0, 12.13, 0.45, PANEL, None)] + [T(x, y0, w, 0.45, P(h, 12, MUTED, True), valign="m") for x, w, h in cols]
    els += g(hdr, 1)
    for i, row in enumerate(rows):
        y = y0 + 0.5 + i * (rh + 0.05)
        mine = row[0] == "MarsTrail"
        cells = [R(0.6, y, 12.13, rh, "2a1a10" if mine else PANEL, ACCENT if mine else BORDER)]
        cells += [T(x, y, w, rh, P(txt, 13 if j == 0 else 12, (ACCENT if mine else TEXT) if j == 0 else TEXT, j == 0), valign="m")
                  for j, ((x, w, _), txt) in enumerate(zip(cols, row))]
        els += g(cells, 2 if i < 2 else 3 if i < 5 else 4)
    els += g(T(0.6, 6.32, 12.13, 0.6, P("Farkımız: astronotun bedeni, arazi ve acil durum tek ekranda, canlı.", 17, ACCENT, True)), 4)
    S.append({"els": els, "say": [
        ("Bu alanda ciddi araçlar var, onları inceledik.", "Karşılaştırma tablosunun başlığı"),
        ("MIT'nin SEXTANT'ı ve NASA'nın xGDS/Minerva paketi, analog sahalarda yürüyüş rotası ve görev planlıyor.", "SEXTANT ve xGDS/Minerva satırları"),
        ("SPOC ve NOAH-H derin öğrenmeyle Mars arazisini sınıflandırıyor, Mars Trek verileri tarayıcıda gösteriyor.", "SPOC, NOAH-H, Mars Trek satırları"),
        ("Bizim farkımız: canlı nabız ve oksijenle değişen dönüş bölgeleri, telsiz koptuğunda kurtarma planı ve hepsi açık veriyle, sunucusuz, tek sayfada.",
         "Turuncu MarsTrail satırı ve “Farkımız” cümlesi")]})

    # 10 · Hedef ve kapanış
    els = chrome(10, "Hedef", "Nerede olduklarını bilecekler",
                 "Alıntı: Dr. James Rice, NASA Goddard, LRO proje bilim insanı yardımcısı (NASA/JPL haberi, 2011) · YZ beyanı: kod ve betikler Claude Code ile, ekip denetiminde")
    els += g(card(0.6, 1.5, 3.9, 1.0, "AY · ARTEMIS", "Ay güney kutbu yürüyüşlerine uyarlanabilir") + card(4.65, 1.5, 3.9, 1.0, "SONRA MARS", "İlk insanlı yürüyüşler"), 1)
    els += g([e for k, (h, b) in enumerate((("KASK İÇİ EKRAN", "Bugün telefonda çalışıyor"), ("KALİBRASYON", "Gerçek yürüyüş verisiyle katsayılar"),
                                            ("ROTA KÜTÜPHANESİ", "Onaylanan rotalar ve notlar (sıradaki adım)")))
              for e in card(0.6 + k * 2.68, 2.65, 2.6, 1.15, h, b, body_size=12)], 2)
    els += g(card(0.6, 3.95, 8.0, 1.25, "NASA'DAN BİR BİLİM İNSANI", "“Muhtemelen kenara ulaşırlardı; çünkü her adımda tam olarak nerede olduklarını bilirlerdi.” · Dr. James Rice, LRO",
                  body_size=14), 3)
    els += g([T(0.6, 5.3, 8.0, 0.75, P("Biz o haritayı Mars için yaptık. Teşekkürler!", 26, ACCENT, True)),
              T(0.6, 6.1, 8.0, 0.8, P("tayancelifnur.github.io/marstrail · Elif: veri, model, algoritmalar · Gözde: arayüz", 12, MUTED)),
              I(FIN / "qr.png", 9.7, 1.5, 3.0, 3.0), T(9.7, 4.55, 3.0, 0.4, P("Telefonunla dene", 13, MUTED), align="c")], 4)
    S.append({"els": els, "say": [
        ("Hedefimiz burada kalmak değil: Artemis'le Ay'ın güney kutbu, sonra Mars.", "“Ay · Artemis” ve “Sonra Mars” kartları"),
        ("Sıradaki adımlar kask içi ekran, gerçek yürüyüş verisiyle kalibrasyon ve onaylanan rotalardan bir kütüphane.", "Üç yol haritası kartı"),
        ("NASA Goddard'dan LRO bilim insanı James Rice, bugünkü haritalarla Shepard ve Mitchell'in kenara muhtemelen ulaşacağını söylüyor.", "Alıntı kartı"),
        ("Biz o haritayı Mars için yaptık; QR koddan hemen deneyebilirsiniz, teşekkür ederiz.", "QR kod ve “Teşekkürler!”")]})
    return S


# ------------------------------------------------------------------ zamanlama
def words(s):
    return len(re.findall(r"[\wçğıöşüÇĞİÖŞÜâ’'.,%~→/–-]+", s))


def timing(S):
    """Her cümlenin bölüm içindeki başlangıcı (sn): sırayla, kelime / RATE + PAUSE."""
    for n, s in enumerate(S, 1):
        t, s["t"] = LEAD, []
        for txt, _ in s["say"]:
            s["t"].append(t)
            t += words(txt) / RATE + PAUSE
        s["end"] = t
        assert t <= SLOT - 0.4, f"bölüm {n}: konuşma {t:.1f} sn, 30 sn'ye sığmıyor"
    return S


# ------------------------------------------------------------------ PPTX (çok klipli tıklama zamanlaması)
def media_call(ids, spid, dur_ms, node):
    return (f'<p:par><p:cTn id="{next(ids)}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" '
            f'nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="{next(ids)}" dur="{dur_ms}" fill="hold"/>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>')


def timing_xml(auto, clicks, videos):
    ids = count(3)
    pars, bld = "", []
    steps = ([("auto", auto)] if auto else []) + [("click", c) for c in clicks]
    for trig, effs in steps:
        outer, inner = next(ids), next(ids)
        cond = ('<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>' if trig == "auto"
                else '<p:cond delay="indefinite"/>')
        body = ""
        for k, (spid, kind, is_sp, dur) in enumerate(effs):
            node = ("afterEffect" if trig == "auto" else "clickEffect") if k == 0 else "withEffect"
            body += M._effect(ids, spid, kind, node, 0)
            if dur:
                body += media_call(ids, spid, dur, "withEffect")
            if is_sp and spid not in bld:
                bld.append(spid)
        pars += (f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst>{cond}</p:stCondLst><p:childTnLst>'
                 f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                 f'<p:childTnLst>{body}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    vnodes = "".join(f'<p:video><p:cMediaNode vol="0"><p:cTn id="{next(ids)}" fill="hold" display="0">'
                     f'<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn>'
                     f'<p:tgtEl><p:spTgt spid="{v}"/></p:tgtEl></p:cMediaNode></p:video>' for v in videos)
    main = (f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{pars}'
            f'</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
            f'</p:nextCondLst></p:seq>')
    bldx = "".join(f'<p:bldP spid="{s}" grpId="0" animBg="1"/>' for s in bld)
    return (f'<p:timing xmlns:p="{M.P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst>{main}{vnodes}</p:childTnLst></p:cTn></p:par></p:tnLst>'
            + (f'<p:bldLst>{bldx}</p:bldLst>' if bldx else "") + '</p:timing>')


def build_pptx(S, path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(M.W_IN), Inches(M.H_IN)
    for n, s in enumerate(S, 1):
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        sl.background.fill.solid()
        sl.background.fill.fore_color.rgb = RGBColor.from_string(BG)
        auto, groups, videos = [], {}, []
        for el in s["els"]:
            dur = 0
            if el["k"] == "rect":
                shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if el["round"] else MSO_SHAPE.RECTANGLE,
                                          Inches(el["x"]), Inches(el["y"]), Inches(el["w"]), Inches(el["h"]))
                if el["round"]:
                    shp.adjustments[0] = min(0.5, 0.08 / min(el["w"], el["h"]))
                shp.fill.solid()
                shp.fill.fore_color.rgb = RGBColor.from_string(el["fill"])
                if el["line"]:
                    shp.line.color.rgb = RGBColor.from_string(el["line"])
                    shp.line.width = Pt(1.25)
                else:
                    shp.line.fill.background()
                shp.shadow.inherit = False
                is_sp = True
            elif el["k"] == "img":
                p, size = M.prepared_image(el)
                x, y, w, h = M.fit(el, size)
                shp = sl.shapes.add_picture(str(p), Inches(x), Inches(y), Inches(w), Inches(h))
                is_sp = False
            elif el["k"] == "video":
                x, y, w, h = M.fit(el, Image.open(el["poster"]).size)
                shp = sl.shapes.add_movie(str(el["path"]), Inches(x), Inches(y), Inches(w), Inches(h),
                                          poster_frame_image=str(el["poster"]), mime_type="video/mp4")
                dur = M.video_ms(el["path"])
                videos.append(shp.shape_id)
                is_sp = False
            else:
                tb = sl.shapes.add_textbox(Inches(el["x"]), Inches(el["y"]), Inches(el["w"]), Inches(el["h"]))
                tf = tb.text_frame
                tf.word_wrap, tf.auto_size = True, None
                tf.margin_left = tf.margin_right = Inches(M.INSET_X)
                tf.margin_top = tf.margin_bottom = Inches(M.INSET_Y)
                tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[el["valign"]]
                for i, p in enumerate(el["paras"]):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[el["align"]]
                    para.space_after, para.space_before, para.line_spacing = Pt(p["gap"]), Pt(0), 1.0
                    r = para.add_run()
                    r.text = p["text"]
                    r.font.name, r.font.size, r.font.bold = M.FONT, Pt(p["size"]), p["bold"]
                    r.font.color.rgb = RGBColor.from_string(p["color"])
                shp, is_sp = tb, True
            a = el.get("anim")
            if a and a["kind"] == "zoom":
                auto.append((shp.shape_id, "zoom", is_sp, 0))
            elif a:
                groups.setdefault(a["group"], []).append((shp.shape_id, "fade", is_sp, dur))
        clicks = [groups[k] for k in sorted(groups)]
        assert len(clicks) == len(s["say"]), f"slayt {n}: {len(clicks)} tıklama, {len(s['say'])} cümle"
        el_ = sl._element
        anchor = el_.find(qn("p:clrMapOvr"))
        idx = list(el_).index(anchor) + 1 if anchor is not None else len(el_)
        el_.insert(idx, etree.fromstring(M.transition_xml("fade")))
        el_.insert(idx + 1, etree.fromstring(timing_xml(auto, clicks, videos)))
        sl.notes_slide.notes_text_frame.text = "\n".join(f"{n}.{k} {txt}" for k, (txt, _) in enumerate(s["say"], 1))
    prs.save(path)


# ------------------------------------------------------------------ video
class Clip:
    """Klibi sırayla okuyan ffmpeg borusu; bitince son kare kalır."""
    def __init__(self, path):
        self.w, self.h = 1280, 720
        self.p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(path), "-vf", f"fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx, self.last = -1, None

    def frame(self, i):
        while self.idx < i:
            raw = self.p.stdout.read(self.w * self.h * 3)
            if len(raw) < self.w * self.h * 3:
                break
            self.last = Image.frombuffer("RGB", (self.w, self.h), raw)
            self.idx += 1
        return self.last


def prepare(s):
    for e in s["els"]:
        a = e.get("anim")
        e["_t0"] = None if not a else 0.3 if a["kind"] == "zoom" else s["t"][a["group"] - 1]
    base = Image.new("RGBA", (W, H), M._hex(BG))
    for e in s["els"]:
        if e["_t0"] is None and e["k"] not in ("img", "video"):
            M.draw_el(base, e, DPI)
    s["_base"] = base
    s["_clips"] = {}


def render(s, t):
    im = s["_base"].copy()
    for e in s["els"]:
        t0 = e["_t0"]
        if t0 is None and e["k"] not in ("img", "video"):
            continue
        if t0 is not None and t < t0:
            continue
        frame = None
        if e["k"] == "video":
            key = str(e["path"])
            if key not in s["_clips"]:
                s["_clips"][key] = Clip(e["path"])
            frame = s["_clips"][key].frame(int((t - (t0 or 0)) * FPS))
        if t0 is None:
            M.draw_el(im, e, DPI, frame=frame)
        elif e["anim"]["kind"] == "zoom":
            p = M_ease((t - t0) / 0.7)
            M.draw_el(im, e, DPI, alpha=p, scale=0.9 + 0.1 * p, frame=frame)
        else:
            p = min(1.0, (t - t0) / 0.45)
            txt = None
            if e["k"] == "text" and e.get("count"):
                txt = counted(e["paras"][0]["text"], M_ease((t - t0) / 1.0))
            M.draw_el(im, e, DPI, alpha=p, text0=txt, frame=frame)
    return im


def M_ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


NUM = re.compile(r"\d+(?:,\d+)?")


def counted(text, p):
    def rep(m):
        s = m.group(0)
        dec = len(s.split(",")[1]) if "," in s else 0
        return f"{float(s.replace(',', '.')) * p:.{dec}f}".replace(".", ",")
    return NUM.sub(rep, text)


def build_video(S, path):
    ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
    t_start = time.time()
    for n, s in enumerate(S):
        nxt = S[n + 1] if n + 1 < len(S) else None
        for fi in range(int(SLOT * FPS)):
            t = fi / FPS
            im = render(s, t)
            if nxt and t > SLOT - XFADE:
                im = Image.blend(im, render(nxt, 0.0), (t - (SLOT - XFADE)) / XFADE)
            ff.stdin.write(im.convert("RGB").tobytes())
        for c in s["_clips"].values():
            c.p.kill()
        print(f"  bölüm {n + 1}: {time.time() - t_start:.0f} sn", flush=True)
    ff.stdin.close()
    ff.wait()


# ------------------------------------------------------------------ konuşma metni
QA = [
    ("Bu NASA'da zaten yok mu?",
     "Parçaları var: SEXTANT ve xGDS/Minerva analog sahalarda rota ve görev planlıyor, SPOC ve NOAH-H araziyi sınıflandırıyor, Mars Trek veriyi gösteriyor. "
     "Bizim farkımız astronotun nabzını ve kalan oksijenini araziyle birleştirip dönüş sınırını canlı çizmek ve telsiz koptuğunda kurtarma planını aynı ekranda vermek."),
    ("Modelin doğruluğu düşük değil mi? (mAP50 0,33)",
     "Kutu düzeyinde düşük, çünkü kum alanı gibi sınırı belirsiz nesnelerde kutunun tam tutması zor. Biz kutu değil 70 metrelik hücrede yoğunluk kullanıyoruz; orada dengeli doğruluk %78, "
     "ve asıl kanıt Perseverance rotası: AUC 0,50'den 0,65'e çıktı."),
    ("Haritanızın doğru olduğunu nereden biliyorsunuz?",
     "Perseverance'ın gerçekten sürdüğü yolu modele hiç vermeden sınav olarak kullandık. Rotadaki 52 hücrenin hiçbiri kumlu değil, çevrede %49; bootstrap farkının %95 aralığı +0,12 ile +0,18."),
    ("Formüllerdeki katsayılar nereden geliyor?",
     "Füzyon ağırlıkları, O₂ çarpanı ve yorgunluk payı bizim varsayımımız ve kodda gerekçesiyle tek yerde yazılı. Gerçek yürüyüş verisi gelince rota doğrulamasıyla kalibre edilebilecek şekilde tasarladık."),
    ("Mars'ta GPS yok, konumu nasıl biliyorsunuz?",
     "Demoda konum simüle; gerçekte giysi IMU'su, adım sayımı, habitat ve rover radyo sinyalleri ve arazi eşleştirmesiyle bulunur. Telsiz koparsa son konum ve kalan oksijenden arama alanını zaten çıkarıyoruz."),
    ("Veri sızıntısını nasıl önlediniz?",
     "Komşu HiRISE karoları aynı sahneyi paylaştığı için karoları komşulukla gruplayıp her grubu ya eğitime ya sınava koyduk. İlk bölmemizde 30 sınav karosunun 8'inin sızdığını bu kontrolle bulup düzelttik."),
    ("Etiketleri yapay zekâ mı yaptı?",
     "Roboflow'un otomatik etiketi yalnızca taslak verdi; 250 karodaki 1.033 kutunun hepsini Elif tek tek kontrol edip düzeltti. Kodu Claude Code desteğiyle yazdık; etiket tanımları, eşikler ve doğrulama ekibin kararı."),
    ("İnternet olmadan çalışır mı?",
     "Bütün hesaplar cihazda, sunucu yok; O₂ bölgeleri, rota ve kurtarma tarayıcıda hesaplanıyor. Taban harita görüntüleri şu an internetten geliyor; görev için harita paketini cihaza gömmek sıradaki adım."),
    ("Rover rotası astronot için doğru bir ölçüt mü?",
     "Tam değil: tekerlek kuma insandan daha duyarlı ve rota bilim hedeflerine de gidiyor. Ama elimizdeki tek gerçek “tehlikeden kaçınma” verisi bu, ve ölçtüğümüz kumdan kaçınma astronot için de geçerli."),
    ("Bunu gerçekten kim kullanır, sıradaki adım ne?",
     "Artemis yürüyüşlerinde ve ilk Mars görevlerinde astronot ve üs ekibi. Sıradaki adımlar kask içi ekran, gerçek yürüyüş verisiyle kalibrasyon ve astronotların onayladığı rotalardan büyüyen bir kütüphane."),
]


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}".replace(".", ",")


def write_md(S):
    titles = [s["els"][1]["paras"][0]["text"] for s in S]
    kick = ["Hikâye", "Sorun", "Çözüm", "Uygulama · hazırlan, planla", "Uygulama · yürü, hayatta kal", "Nasıl yaptık · veri",
            "Nasıl yaptık · model", "Doğrulama", "Rakip analizi", "Hedef"]
    total = sum(words(t) for s in S for t, _ in s["say"])
    L = ["# Konuşma metni · MarsTrail final sunumu (5:00)", "",
         "Bu dosya `scripts/final/make_final.py` ile üretilir. Metin, slaytlar ve video aynı kaynaktan geliyor; zamanlar birebir aynı.",
         "",
         "- **Video:** `docs/sunum/MarsTrail_final.mp4`. 10 bölüm × 30 sn, sessiz. Her cümlenin görseli, cümlenin başladığı saniyede belirir.",
         "- **PPTX:** `docs/sunum/MarsTrail_final.pptx`. Her cümle bir tıklama; metin slayt notlarında.",
         f"- **Hız:** Ses taslağından ölçüldü (faster-whisper): {RATE:.2f} kelime/sn, cümle arasında {PAUSE:.2f} sn nefes. Toplam {total} kelime.".replace("2.10", "2,10").replace("0.45", "0,45"),
         "- **Okurken:** Cümleye ekrandaki görsel belirince başla. Geride kalırsan bölümün son cümlesini kısalt; bölüm sınırını kaçırma.", ""]
    for n, s in enumerate(S, 1):
        a = (n - 1) * SLOT
        L += [f"## {n} · {kick[n - 1]}: {titles[n - 1]} ({mmss(a)}–{mmss(a + SLOT)})", "",
              "| # | Zaman | Söyle | Ekranda |", "| --- | --- | --- | --- |"]
        for k, ((txt, scr), t) in enumerate(zip(s["say"], s["t"]), 1):
            L.append(f"| {n}.{k} | {mmss(a + t)} | {txt} | {scr} |")
        L += ["", f"*Konuşma {s['end']:.1f} / 30 sn.*".replace(".", ",", 1), ""]
    L += ["---", "", "## Jüri soruları (en olası 10)", ""]
    for i, (q, ans) in enumerate(QA, 1):
        L += [f"**{i}. {q}**", "", ans, ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()
    S = timing(slides())
    bad = M.check(S)
    for b in bad:
        print("  TAŞMA:", b)
    assert not bad, "taşan öğe var"
    for n, s in enumerate(S, 1):
        print(f"  bölüm {n}: {len(s['say'])} cümle, {sum(words(t) for t, _ in s['say'])} kelime, konuşma {s['end']:.1f} sn")
    write_md(S)
    build_pptx(S, OUT_PPTX)
    print(f"{OUT_PPTX.relative_to(ROOT)} ({OUT_PPTX.stat().st_size / 1e6:.1f} MB), {OUT_MD.relative_to(ROOT)}")
    M.render_preview([{"els": s["els"]} for s in S], ROOT / "docs" / "sunum" / "img" / "final" / "onizleme")
    if not args.no_video:
        for s in S:
            prepare(s)
        build_video(S, OUT_MP4)
        print(f"{OUT_MP4.relative_to(ROOT)} ({OUT_MP4.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
