"""E6 ablation D – karo sınıflandırma veri seti: 150 etiketli karo → 600 alt karo (320 px ≈ 80 m ≈ 1 grid hücresi).

Çalıştır:  venv\\Scripts\\python ml\\make_cls_dataset.py
Girdi :   ml/dataset/ (Roboflow YOLOv8 export, kutu etiketleri)
Çıktı :   ml/dataset_cls/{train,val}/{kum,kayalik,duz}/*.png   (Ultralytics sınıflandırma klasör düzeni)
          docs/figures/e6_cls_dataset_stats.json

Neden: E10'da model çıktısı zaten 70 m'lik grid hücresine yoğunluk olarak gidecek. Kutu sınırlarını öğrenmek yerine
"bu ~80 m'lik parça kum mu, kayalık mı, düz mü" sorusu doğrudan haritanın ihtiyacı. Bölge ölçekli kum kutuları
(237 kutunun 74'ü karonun ≥ %80'i) tespit için gürültü ama sınıflandırma etiketi için doğal.

Etiket kuralı (öncelik kum > kayalik > duz):
  kum     : kum_dalgasi kutularının birleşiminin alt karodaki kaplama oranı ≥ KUM_MIN
  kayalik : kaya_alani kaplaması ≥ KAYA_ALANI_MIN  ya da  merkezi alt karoda olan kaya kutusu sayısı ≥ KAYA_N
  duz     : ikisi de değil
Bölme KARO bazında: bir karonun 4 alt karosu Roboflow'daki bölümüyle aynı yere gider (train → train, valid → val).
Komşu alt karolar aynı sahneyi paylaştığı için alt karo bazında rastgele bölme val'e sızıntı yapardı.
"""
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "ml" / "dataset"
OUT = ROOT / "ml" / "dataset_cls"
FIG = ROOT / "docs" / "figures"
SUB = 320  # 320 px × 0,25 m = 80 m ≈ grid hücresi (70,4 m); 640'lık karo 2×2 alt karoya bölünür

# Eşikler veriden (600 alt karonun dağılımı, scriptin çıktısındaki histogramlar):
# - kum kaplaması iki tepeli: 115 alt karoda 0, 313'ünde ≥ 0,9; arası düz dağılmış, belirgin bir vadi yok.
#   Bu yüzden "hücrenin çoğunluğu kum" kuralı: ≥ 0,5. (0,3 ile 0,5 arası yalnızca 36 alt karoyu kaydırıyor.)
KUM_MIN = 0.5
# - kaya_alani kaplaması 533 alt karoda 0; geri kalanı 0–1 arası yayılmış. ≥ 0,1 = hücrenin en az ~640 m²'si yoğun kaya.
KAYA_ALANI_MIN = 0.1
# - kaya sayısı: 518 alt karoda 0, 28'inde 1. Tek kaya etrafından dolaşılan tek engel, "kayalık arazi" değil;
#   en az 2 kaya = engellerin kümelendiği yer. (Etiketlemede çok kayalı karolarda kayaların hepsi değil en belirgin
#   30–40'ı işaretlendi, yani sayı alt sınır; eşik bu yüzden düşük tutuldu.)
KAYA_N = 2
NAMES = ["kaya", "kaya_alani", "kum_dalgasi"]


def boxes(lab: Path):
    rows = [l.split() for l in lab.read_text().splitlines() if l.strip()] if lab.exists() else []
    return [(int(r[0]), *map(float, r[1:5])) for r in rows]


def label_subtiles(bx, W=640):
    """Her alt karo için (kum kaplaması, kaya_alani kaplaması, kaya sayısı) ve türetilmiş sınıf."""
    mask = {1: np.zeros((W, W), bool), 2: np.zeros((W, W), bool)}
    cents = []
    for c, x, y, w, h in bx:
        x0, x1 = int(max(0, (x - w / 2) * W)), int(min(W, (x + w / 2) * W))
        y0, y1 = int(max(0, (y - h / 2) * W)), int(min(W, (y + h / 2) * W))
        if c in mask:
            mask[c][y0:y1, x0:x1] = True   # birleşim maskesi: üst üste binen kutular iki kez sayılmaz
        else:
            cents.append((x * W, y * W))
    out = []
    for i in range(W // SUB):
        for j in range(W // SUB):
            sl = (slice(i * SUB, (i + 1) * SUB), slice(j * SUB, (j + 1) * SUB))
            kum = float(mask[2][sl].mean())
            ka = float(mask[1][sl].mean())
            nk = sum(1 for cx, cy in cents if j * SUB <= cx < (j + 1) * SUB and i * SUB <= cy < (i + 1) * SUB)
            cls = "kum" if kum >= KUM_MIN else ("kayalik" if (ka >= KAYA_ALANI_MIN or nk >= KAYA_N) else "duz")
            out.append((i, j, kum, ka, nk, cls))
    return out


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    counts = {"train": Counter(), "val": Counter()}
    allv = {"kum": [], "ka": [], "nk": []}
    for split, dst in (("train", "train"), ("valid", "val")):
        for im in sorted((DS / split / "images").glob("*.*")):
            img = Image.open(im).convert("L")
            for i, j, kum, ka, nk, cls in label_subtiles(boxes(DS / split / "labels" / (im.stem + ".txt")), img.width):
                d = OUT / dst / cls
                d.mkdir(parents=True, exist_ok=True)
                img.crop((j * SUB, i * SUB, (j + 1) * SUB, (i + 1) * SUB)).save(d / f"{im.stem.split('_png')[0]}_{i}{j}.png")
                counts[dst][cls] += 1
                allv["kum"].append(kum); allv["ka"].append(ka); allv["nk"].append(nk)
    kum, ka, nk = (np.array(allv[k]) for k in ("kum", "ka", "nk"))
    stats = {
        "subtile_px": SUB, "subtile_m": SUB * 0.25,
        "thresholds": {"KUM_MIN": KUM_MIN, "KAYA_ALANI_MIN": KAYA_ALANI_MIN, "KAYA_N": KAYA_N},
        "counts": {k: dict(v) for k, v in counts.items()},
        "total": int(sum(sum(v.values()) for v in counts.values())),
        "hist_kum_cov": {"bins": [0, 0.001, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.01],
                         "n": np.histogram(kum, [0, 0.001, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.01])[0].tolist()},
        "hist_kaya_alani_cov": {"bins": [0, 0.001, .05, .1, .2, .3, .5, 1.01],
                                "n": np.histogram(ka, [0, 0.001, .05, .1, .2, .3, .5, 1.01])[0].tolist()},
        "kaya_count_bincount": np.bincount(np.minimum(nk, 10)).tolist(),
    }
    (FIG / "e6_cls_dataset_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
