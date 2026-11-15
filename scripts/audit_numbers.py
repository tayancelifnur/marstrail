"""Sayı denetimi: sunumda, videoda ve teslim belgelerinde geçen her sayı kaynağından yeniden hesaplanır.

Çalıştır (proje kökünden, PowerShell ya da cmd'den):  venv\\Scripts\\python scripts\\audit_numbers.py  → docs/SAYI_DENETIMI.md
  Not: Git Bash'ten çalıştırılınca headless Edge sessizce boş çıktı veriyor (ortam değişkenleri); test sayıları ölçülemez.
Kaynaklar:
  - docs/figures/*.json (betiklerin ölçtüğü değerler: pipeline_stats, e5_stats, e6v2_compare, e6v2_split,
    e10_infer_stats, e10_validation)
  - uygulama testleri web/tests/e8, e11, e13 (headless Edge ile çalıştırılır, <pre id="out"> çıktısı okunur):
    demo planı, O₂ bölgeleri, arama alanı sayıları uygulamanın kendi hesabıdır
  - dış kaynaklar (tarihî olaylar): URL ile; bu betik ölçemez, yalnızca kaynağı listeler
Her sayı için: gösterilen metin, ölçülen değer, eşleşiyor mu, hangi dosyalarda geçtiği. Ayrıca eski (güncellenmiş)
sayıların sunum dosyalarında etiketsiz kalıp kalmadığı taranır. Uyuşmayan sayı varsa çıkış kodu 1.
"""
import html
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
OUT = ROOT / "docs" / "SAYI_DENETIMI.md"
# Sunumda/teslimde sayı taşıyan dosyalar (geçtiği yerler bu listeden aranır)
FILES = ["docs/SLAYTLAR.md", "scripts/make_slides.py", "scripts/make_video.py", "docs/TESLIM.md",
         "docs/JURI_SORULARI.md", "README.md"]
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def J(name):
    return json.loads((FIG / f"{name}.json").read_text(encoding="utf-8"))


def tr(v, d=0):
    """Türkçe ondalık: 0.649 → '0,65' (d=2)."""
    return f"{v:.{d}f}".replace(".", ",")


# ---------------------------------------------------------------- uygulama testleri
def run_app_tests():
    """web/ klasörünü yerel sunucuyla açıp E8/E11/E13 test sayfalarını headless Edge'de çalıştırır."""
    edge = next((p for p in EDGE if Path(p).exists()), shutil.which("msedge"))
    if not edge:
        return None
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(ROOT / "web")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    out = {}
    try:
        for t in ("e8", "e11", "e13"):
            with tempfile.TemporaryDirectory() as prof:
                r = subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}",
                                    "--virtual-time-budget=20000", "--dump-dom", f"http://127.0.0.1:{port}/tests/{t}.html"],
                                   capture_output=True, timeout=120)
            dom = r.stdout.decode("utf-8", "replace")
            m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
            out[t] = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else ""
    finally:
        srv.terminate()
    if not any(out.values()):
        print("UYARI: Edge test sayfalarından çıktı alınamadı (Git Bash'te bilinen sorun) → PowerShell ya da cmd'den çalıştırın.")
        return None
    return out


def grab(text, pattern, cast=float):
    m = re.search(pattern, text or "")
    return cast(m.group(1)) if m else None


# ---------------------------------------------------------------- iddialar
def claims(tests):
    V, C, S, I, P, E5 = J("e10_validation"), J("e6v2_compare"), J("e6v2_split"), J("e10_infer_stats"), J("pipeline_stats"), J("e5_stats")
    hi = V["hirise_kapsami"]
    raw_gb = sum(P[k].get("file_mb", P[k].get("zip_mb", 0)) for k in P if re.fullmatch(r"D\d", k)) / 1000
    grid_mb = (ROOT / "web" / "data" / "grid.json").stat().st_size / 1e6
    e8, e11, e13 = (tests or {}).get("e8"), (tests or {}).get("e11"), (tests or {}).get("e13")
    L = []

    def add(shown, what, measured, source, ok=None):
        if ok is None:
            ok = measured is not None and str(measured) == shown
        L.append({"shown": shown, "what": what, "measured": "—" if measured is None else str(measured), "source": source, "ok": ok})

    # Doğrulama (E10)
    add("0,50", "AUC, HiRISE kapsamı, YOLO'suz (slayt 6)", tr(hi["once_yolo_yok"]["auc_route_lower"], 2), "e10_validation.json · hirise_kapsami.once_yolo_yok.auc_route_lower")
    add("0,65", "AUC, HiRISE kapsamı, YOLO'lu (slayt 6)", tr(hi["sonra_yolo"]["auc_route_lower"], 2), "e10_validation.json · hirise_kapsami.sonra_yolo.auc_route_lower")
    add("0,498", "AUC YOLO'suz, 3 hane (TESLIM, jüri)", tr(hi["once_yolo_yok"]["auc_route_lower"], 3), "e10_validation.json")
    add("0,649", "AUC YOLO'lu, 3 hane", tr(hi["sonra_yolo"]["auc_route_lower"], 3), "e10_validation.json")
    f = V["bootstrap_95"]["fark"]
    add("+0,12…+0,18", "AUC farkı, bootstrap %95 aralığı", f"+{tr(f[0], 2)}…+{tr(f[1], 2)}", "e10_validation.json · bootstrap_95.fark")
    add("%0", "kumlu (kum_ml ≥ 0,5) rota hücresi", f"%{tr(V['yolo_dogrudan']['kum_ml']['pct_route_ge_0_5'])}", "e10_validation.json · yolo_dogrudan.kum_ml.pct_route_ge_0_5")
    add("%49", "kumlu rota dışı hücre (yuvarlak)", f"%{tr(V['yolo_dogrudan']['kum_ml']['pct_other_ge_0_5'])}", "e10_validation.json · yolo_dogrudan.kum_ml.pct_other_ge_0_5")
    add("%49,3", "kumlu rota dışı hücre", f"%{tr(V['yolo_dogrudan']['kum_ml']['pct_other_ge_0_5'], 1)}", "e10_validation.json")
    add("0,51", "kaya AUC", tr(V["yolo_dogrudan"]["kaya_ml"]["auc_route_lower"], 2), "e10_validation.json · yolo_dogrudan.kaya_ml.auc_route_lower")
    add("%100", "rotanın geçilebilir oranı", f"%{tr(hi['sonra_yolo']['route_passable_pct'])}", "e10_validation.json · route_passable_pct")
    add("52", "HiRISE kapsamındaki rota hücresi", str(V["route_cells_in_hirise"]), "e10_validation.json · route_cells_in_hirise")
    add("397", "toplam rota hücresi", str(V["route_cells_total"]), "e10_validation.json · route_cells_total")
    add("0,562 → 0,571", "AUC tüm alan", f"{tr(V['tum_alan']['once_yolo_yok']['auc_route_lower'], 3)} → {tr(V['tum_alan']['sonra_yolo']['auc_route_lower'], 3)}", "e10_validation.json · tum_alan")
    # Model (E6 v2)
    d = C["decision"]
    add("0,31", "mAP50 v1, ortak val", tr(d["mAP50"][0], 2), "e6v2_compare.json · decision.mAP50[0]")
    add("0,33", "mAP50 v2, ortak val", tr(d["mAP50"][1], 2), "e6v2_compare.json · decision.mAP50[1]")
    add("0,69", "hücre dengeli doğruluk v1", tr(d["cell_balanced_accuracy"][0], 2), "e6v2_compare.json · decision.cell_balanced_accuracy[0]")
    add("0,78", "hücre dengeli doğruluk v2", tr(d["cell_balanced_accuracy"][1], 2), "e6v2_compare.json · decision.cell_balanced_accuracy[1]")
    add("250", "etiketli karo", str(S["tiles"]), "e6v2_split.json · tiles")
    add("51", "ortak val karosu", str(sum(v for k, v in S["split_tiles"].items() if k.startswith("valid"))), "e6v2_split.json · split_tiles valid_*")
    add("8", "v1 val'inde train'e bitişik karo", str(len(S["v1_valid_adjacent_to_v1_train"])), "e6v2_split.json · v1_valid_adjacent_to_v1_train")
    kr = [C[r]["tum"]["cell"]["per_class"]["kayalik"]["R"] for r in (d["old"], d["new"])]
    add("0,36'dan 0,56'ya", "kayalık hücre recall v1 → v2", f"{tr(kr[0], 2)}'dan {tr(kr[1], 2)}'ya", "e6v2_compare.json · <run>.tum.cell.per_class.kayalik.R")
    import csv
    src = {r["tile"]: r["source"] for r in csv.DictReader(open(ROOT / "ml" / "split_merged.csv", encoding="utf-8"))}
    aud = [src[r["tile"]] for r in csv.DictReader(open(ROOT / "ml" / "audit_missed_labels.csv", encoding="utf-8"))]
    old_n = sum(1 for v in src.values() if v == "eski")
    ratio = (aud.count("eski") / old_n) / (aud.count("yeni") / (len(src) - old_n))
    add("2,5 kat", "etiketsiz engel / karo: 1. parti ÷ 2. parti", f"{tr(ratio, 1)} kat", "ml/audit_missed_labels.csv + ml/split_merged.csv")
    add("1146", "çıkarım yapılan karo", str(I["tiles_inferred"]), "e10_infer_stats.json · tiles_inferred")
    add("17 sn", "çıkarım toplam süresi", f"{round(I['seconds']['total'])} sn", "e10_infer_stats.json · seconds.total")
    add("~29 km²", "HiRISE (YOLO) kapsamı = karo × 160 m × 160 m", f"~{round(I['tiles_inferred'] * 0.16 * 0.16)} km²", "e10_infer_stats.json · tiles_inferred × 0,0256 km²")
    # Veri hattı
    add("2590", "HiRISE karo ızgarası", str(E5["screen"]["tiles_total"]), "e5_stats.json · screen.tiles_total")
    add("1444", "NoData yüzünden atılan karo", str(E5["screen"]["dropped_nodata"]), "e5_stats.json · screen.dropped_nodata")
    add("58 karo", "dokusuz (etiketlemeye girmeyen) karo", f"{E5['screen']['dropped_flat']} karo", "e5_stats.json · screen.dropped_flat")
    add("23 alanın yalnızca 4'ü", "D1 konum dosyasında kullanılan alan", f"{P['D1']['fields_total']} alanın yalnızca {len(P['D1']['fields_used'])}'ü",
        "pipeline_stats.json · D1.fields_total, D1.fields_used")
    add("~6 GB","ham veri toplamı (D1–D8 dosya boyutları)", f"~{round(raw_gb)} GB", f"pipeline_stats.json · D*.file_mb/zip_mb toplamı = {tr(raw_gb, 2)} GB")
    add("1,3 MB", "grid.json boyutu", f"{tr(grid_mb, 1)} MB", "web/data/grid.json dosya boyutu")
    add("70 m", "grid hücresi", f"{round(P['grid']['cell_m'])} m", "pipeline_stats.json · grid.cell_m")
    add("1304 → 118", "jeoloji poligonu (kaynak → alan içi)", f"{P['D6']['polygons']} → {P['D6']['polygons_in_area']}", "pipeline_stats.json · D6.polygons, D6.polygons_in_area")
    add("2 kaynak hatası", "jeoloji haritasında düzeltilen", f"{P['D6']['typo_fixed'] + P['D6']['unit_code_mismatch']} kaynak hatası", "pipeline_stats.json · D6.typo_fixed + unit_code_mismatch")
    add("%2–98", "termal normalizasyon dilimleri", "%2–98" if "p2" in P["D4"] and "p98" in P["D4"] else None, "pipeline_stats.json · D4.p2, D4.p98")
    add("150", "geçilmez hücre", str(P["grid"]["blocked"]), "pipeline_stats.json · grid.blocked")
    # Uygulama (testler)
    tsrc = "web/tests/{} (headless Edge)"
    g85 = grab(e8, r"nabız 85, yük 6 kg: .*?yeşil ([\d.]+) km²")
    g150 = grab(e8, r"nabız 150 \(Apollo 14\): .*?yeşil ([\d.]+) km²")
    add("130 → 47 km²", "yeşil bölge, nabız 85 → 150 (Ayşe, O₂ 480)", None if g85 is None else f"{round(g85)} → {round(g150)} km²", tsrc.format("e8.html"))
    add("279 dk", "üs → Cheyava Falls tek yön", None if not e8 else f"{grab(e8, r'Cheyava Falls (\d+) dk', int)} dk", tsrc.format("e8.html"))
    add("73 dk", "üs → Three Forks tek yön (yük 0)", None if not e8 else f"{grab(e8, r'Three Forks (\d+) dk,', int)} dk", tsrc.format("e8.html"))
    km, tot = grab(e11, r"([\d.]+) km, toplam \d+ dk"), grab(e11, r"toplam (\d+) dk", int)
    add("5,52 km", "demo planı mesafe", None if km is None else f"{tr(km, 2)} km", tsrc.format("e11.html"))
    add("243 dk", "demo planı toplam süre", None if tot is None else f"{tot} dk", tsrc.format("e11.html"))
    add("249 dk", "demo planı dönüşte kalan O₂", None if not e11 else f"{grab(e11, r'Dönüşte (\d+) dk O₂', int)} dk", tsrc.format("e11.html"))
    add("T+67", "O₂ 220 + nabız 150: dönüş noktası", None if not e11 else f"T+{grab(e11, r'Dönüş noktası: T\+(\d+) dk', int)}", tsrc.format("e11.html"))
    add("11,6 dk", "İHA, olasılığın %50'si", None if not e13 else f"{tr(grab(e13, r'%50.si ([\d.]+) dk'), 1)} dk", tsrc.format("e13.html"))
    add("1,07 km²", "arama alanı (20 dk sonra)", None if not e13 else f"{tr(grab(e13, r'ulaşılabilir ([\d.]+) km²'), 2)} km²", tsrc.format("e13.html"))
    add("116 / 480", "Ali'nin O₂ ihtiyacı / kapasitesi", None if not e13 else "{} / {}".format(*re.search(r"O₂ ihtiyacı (\d+) / (\d+)", e13).groups()), tsrc.format("e13.html"))
    return L


EXTERNAL = [
    ("1971 · ~30 m", "Apollo 14: Cone Krateri kenarına kalan mesafe", "https://science.nasa.gov/photojournal/trail-of-discovery-at-fra-mauro (NASA PIA12897; LROC, NASA/GSFC/Arizona State University, 19 Ağu 2009)",
     "15 Kas 2026'da sayfadan doğrulandı: \"the astronauts just barely missed (30 meters) the rim of Cone crater\"; \"Saddle Rock … can be discerned in the LROC image\". Eski metindeki ~21 m düzeltildi."),
    ("~30 cm · 2,5 m", "Opportunity'yi tutan kum dalgası: yükseklik ve genişlik", "https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune (PIA07999)",
     "15 Kas 2026'da sayfadan doğrulandı: \"about one-third meter (one foot) tall and 2.5 meters (8 feet) wide\". Eski metindeki 10–15 cm düzeltildi."),
    ("5 haftadan fazla", "Opportunity'nin mahsur kalma süresi (26 Nis – Haz 2005)", "PIA07999 aynı sayfa", "\"Getting the rover out of the dunes took more than five weeks\""),
    ("2009", "Spirit'in yumuşak kuma gömülmesi", "https://www.space.com/18766-spirit-rover.html", "kaynak metni"),
    ("3–22 dk", "Dünya–Mars tek yön ışık süresi", "Mars uzaklığı 0,37–2,68 AU / ışık hızı", "fizik; uygulamadaki marstime.js aynı aralığı veriyor"),
    ("nabız 150", "Apollo 14'te Shepard'ın nabzı", "https://ntrs.nasa.gov/api/citations/19710012245/downloads/19710012245.pdf", "kaynak metni"),
]
# Güncellenmiş eski sayılar: sunum dosyalarında yalnızca "v1 / ilk taslak / 1. parti modeli" bağlamında kalabilir
STALE = {"0,626": "AUC (v1 modeli)", "%3,8": "kumlu rota hücresi (v1)", "%52,6": "kumlu çevre (v1)",
         "15 cm": "Opportunity kum dalgası (yanlış)", "21 m": "Apollo 14 kenar mesafesi (yanlış)", "21 metre": "Apollo 14 kenar mesafesi (yanlış)", "afet": "Etki kartı (kaldırıldı)", "15 santim": "Opportunity kum dalgası (yanlış)", "278 dk": "Cheyava (E10 öncesi)"}
STALE_OK = re.compile(r"v1|ilk taslak|1\. parti model|önceki|eski", re.I)


def where(token):
    hits = []
    for f in FILES:
        p = ROOT / f
        if p.exists() and token in p.read_text(encoding="utf-8"):
            hits.append(Path(f).name)
    return ", ".join(hits) or "—"


def stale_scan():
    rows = []
    for f in FILES:
        p = ROOT / f
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for tok, what in STALE.items():
                if tok in line and not STALE_OK.search(line):
                    rows.append((f, n, tok, what))
    return rows


def main():
    tests = run_app_tests()
    L = claims(tests)
    bad = [c for c in L if not c["ok"]]
    stale = stale_scan()
    md = ["# Sayı denetimi", "",
          "Bu dosya `scripts/audit_numbers.py` ile üretilir; elle düzenlenmez. Sunumdaki (PPTX, video), teslim formundaki",
          "ve jüri cevaplarındaki her sayı kaynağından yeniden hesaplanır.", "",
          "- **Betik ölçümü:** `docs/figures/*.json` (veri hattı, model ve doğrulama betiklerinin çıktısı).",
          "- **Uygulama testi:** `web/tests/e8, e11, e13`. Betik bunları headless Edge'de çalıştırır; demo planı, O₂ bölgeleri ve arama alanı sayıları uygulamanın kendi hesabıdır." +
          ("" if tests else " **Bu koşuda Edge bulunamadı, test sayıları ölçülmedi.**"),
          "- **Dış kaynak:** Tarihî olaylar URL ile listelenir.", "",
          f"**Sonuç:** {len(L)} sayı denetlendi; eşleşen {len(L) - len(bad)}" + (f", **uyuşmayan {len(bad)}**." if bad else ", uyuşmayan yok.") +
          f" Eski sayı taraması: {'temiz' if not stale else f'{len(stale)} yerde eski sayı'}.", "",
          "## Betik ve test ile ölçülen sayılar", "",
          "| Gösterilen | Ne | Ölçülen | Durum | Kaynak | Geçtiği dosyalar |", "| --- | --- | --- | --- | --- | --- |"]
    for c in L:
        md.append(f"| {c['shown']} | {c['what']} | {c['measured']} | {'✔' if c['ok'] else '✘'} | {c['source']} | {where(c['shown'])} |")
    md += ["", "## Dış kaynaklı sayılar (tarihî olaylar)", "", "| Gösterilen | Ne | Kaynak | Not |", "| --- | --- | --- | --- |"]
    md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in EXTERNAL]
    md += ["", "## Eski sayı taraması", "",
           "Güncellenen değerler (v1 modeli, eski Opportunity yüksekliği, E10 öncesi süre) sunum dosyalarında yalnızca "
           "\"v1 / ilk taslak / eski\" bağlamında kalabilir.", ""]
    if stale:
        md += ["| Dosya | Satır | Eski sayı | Ne |", "| --- | --- | --- | --- |"] + [f"| {f} | {n} | {t} | {w} |" for f, n, t, w in stale]
    else:
        md.append(f"Taranan dosyalar: {', '.join(FILES)}. Etiketsiz eski sayı yok.")
    md += ["", "Sayıların güncelliği: model ya da veri değişirse önce ilgili betik (`ml/infer.py`, `scripts/prep_layers.py`, "
           "`scripts/validate.py`, `ml/eval_merged.py`), sonra bu denetim yeniden çalıştırılır. ✘ çıkan sayı sunumda ve "
           "belgelerde düzeltilir.", ""]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(L)} sayı, {len(bad)} uyuşmazlık, {len(stale)} eski sayı")
    for c in bad:
        print(f"  ✘ {c['shown']} ({c['what']}): ölçülen {c['measured']}")
    for f, n, t, w in stale:
        print(f"  eski: {f}:{n} {t} ({w})")
    sys.exit(1 if bad or stale else 0)


if __name__ == "__main__":
    main()
