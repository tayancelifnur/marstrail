"""E6 ablation – adil karşılaştırma: bütün tespit modelleri AYNI 2 sınıflı görevde (kaya+kaya_alani → kaya, kum_dalgasi).

Neden: 3 sınıflı modellerin mAP'i, en zor sınıf olan kaya_alani'yi de ortalamaya katıyor. 2 sınıflı modellerde bu sınıf
yok, bu yüzden genel mAP'ler doğrudan karşılaştırılamaz. Burada 3 sınıflı modellerin tahminlerinde kaya_alani → kaya
yapılır ve hepsi aynı val üzerinde aynı kodla ölçülür. E10'da haritaya giden bilgi de bu iki sınıf
("kayalık" ve "kum") olduğu için seçim bu tabloya göre yapılır.

Çalıştır:  venv\\Scripts\\python ml\\eval_merged.py                      (E6 ablation, ml/dataset/valid)
           venv\\Scripts\\python ml\\eval_merged.py --data ml/dataset_merged --runs e6_s2 e6v2_s2 ^
               --out docs/figures/e6v2_compare.json --decide                (2. parti: v1 C ile v2 C, AYNI 51 karoluk val)
Çıktı:     docs/figures/e6_merged_eval.json  (ya da --out)

2. parti karşılaştırmasında val = ml/dataset_merged/valid (merge_v2.py): v1 modelinin eğitim karolarından hiçbiri ve
onlara bitişik hiçbir karo burada yok, yani iki model de bu karoları ilk kez görüyor. Sonuçlar ayrıca "eski" (1. parti)
ve "yeni" (2. parti) karolar için ayrı verilir: yeni karolarda kaya_alani tanımı genişledi (sık çukur kümeleri de
dahil), eski karolardaki fark ise tanım değişikliğinden bağımsız iyileşmeyi gösterir.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionValidator
from ultralytics.utils.metrics import ap_per_class, box_iou

ROOT = Path(__file__).resolve().parents[1]
RUNS = ["e6_m3", "e6_s3", "e6_m2", "e6_s2"]
NAMES = ["kaya", "kum_dalgasi"]
REMAP3 = {0: 0, 1: 0, 2: 1}   # 3 sınıflı etiket/tahmin → 2 sınıf (kaya_alani → kaya); dataset_2cls ile aynı dönüşüm


def gt(lab: Path, W=640):
    """3 sınıflı Roboflow etiketini okuyup 2 sınıfa çevirir (ml/dataset_2cls'yi okumakla aynı sonuç)."""
    rows = [l.split() for l in lab.read_text().splitlines() if l.strip()] if lab.exists() else []
    if not rows:
        return torch.zeros(0), torch.zeros((0, 4))
    a = torch.tensor([[float(REMAP3[int(r[0])])] + [float(v) for v in r[1:5]] for r in rows])
    xy = a[:, 1:3] * W
    wh = a[:, 3:5] * W
    return a[:, 0], torch.cat([xy - wh / 2, xy + wh / 2], 1)


def det_eval(m, imgs, labdir, v):
    remap = REMAP3 if len(m.names) == 3 else {0: 0, 1: 1}
    stats = {"tp": [], "conf": [], "pred_cls": [], "target_cls": []}
    # conf 0,001 ve NMS IoU 0,7: Ultralytics'in doğrulama ayarları (mAP eğrisinin tamamı için düşük eşik)
    for r in m.predict([str(p) for p in imgs], imgsz=640, conf=0.001, iou=0.7, max_det=300,
                       device=0, half=False, verbose=False, batch=16):
        tcls, tbox = gt(labdir / (Path(r.path).stem + ".txt"))
        pcls = torch.tensor([remap[int(c)] for c in r.boxes.cls.cpu()], dtype=torch.float32)
        pbox, pconf = r.boxes.xyxy.cpu(), r.boxes.conf.cpu()
        if len(pcls) and len(tcls):
            tp = np.asarray(v.match_predictions(pcls, tcls, box_iou(tbox, pbox)).cpu()).astype(bool)
        else:
            tp = np.zeros((len(pcls), len(v.iouv)), bool)
        stats["tp"].append(tp)
        stats["conf"].append(pconf.numpy())
        stats["pred_cls"].append(pcls.numpy())
        stats["target_cls"].append(tcls.numpy())
    s = {k: np.concatenate(x, 0) for k, x in stats.items()}
    res = ap_per_class(s["tp"], s["conf"], s["pred_cls"], s["target_cls"], names={0: "kaya", 1: "kum_dalgasi"})
    p, rcl, ap, cls_idx = res[2], res[3], res[5], res[6]
    per = {NAMES[int(c)]: {"P": round(float(p[i]), 3), "R": round(float(rcl[i]), 3),
                           "mAP50": round(float(ap[i, 0]), 3), "mAP50_95": round(float(ap[i].mean()), 3)}
           for i, c in enumerate(cls_idx)}
    return {"classes_trained": len(m.names), "images": len(imgs), "per_class": per,
            "all": {"mAP50": round(float(ap[:, 0].mean()), 3), "mAP50_95": round(float(ap.mean()), 3)}}


def cell_eval(m, imgs, labdir, conf=0.25):
    """E10'daki kullanımın ölçüsü: tespitler 80 m'lik alt karoda kum/kayalik/duz sınıfına çevrilir (make_cls_dataset ile
    AYNI kural) ve etiketlerden türetilen alt karo sınıfıyla karşılaştırılır.
    conf 0,25: Ultralytics'in tahmin varsayılanı; val üzerinde ayarlanmadı (ayarlansaydı val'e uydurmuş olurduk).
    2 sınıflı modelde kaya_alani yok: kenarı ≥ 40 px (10 m) olan kaya kutusu kaya_alani sayılır. Eşik ölçümden:
    etiketlerde kaya p90 = 9,4 m, kaya_alani p10 = 10,8 m (e6_dataset_stats.json)."""
    import sys
    sys.path.insert(0, str(ROOT / "ml"))
    import make_cls_dataset as C
    truth = {}
    for im in imgs:
        for i, j, *_, cls in C.label_subtiles(C.boxes(labdir / (im.stem + ".txt"))):
            truth[(im.stem, i, j)] = cls
    classes = ["duz", "kayalik", "kum"]
    three = len(m.names) == 3
    cm = {t: {p: 0 for p in classes} for t in classes}
    for r in m.predict([str(p) for p in imgs], imgsz=640, conf=conf, device=0, half=False, verbose=False, batch=16):
        bx = []
        for c, (x, y, w, h) in zip(r.boxes.cls.cpu().tolist(), r.boxes.xywhn.cpu().tolist()):
            c = int(c)
            if not three:   # 2 sınıf → make_cls_dataset'in 3 sınıflı indislerine çevir
                c = 2 if c == 1 else (1 if (w * h) ** 0.5 * 640 >= 40 else 0)
            bx.append((c, x, y, w, h))
        for i, j, *_, cls in C.label_subtiles(bx):
            cm[truth[(Path(r.path).stem, i, j)]][cls] += 1
    n = sum(sum(v.values()) for v in cm.values())
    per = {}
    for c in classes:
        pred_c = sum(cm[t][c] for t in classes)
        true_c = sum(cm[c].values())
        per[c] = {"P": round(cm[c][c] / pred_c, 3) if pred_c else 0.0, "R": round(cm[c][c] / true_c, 3) if true_c else 0.0}
    present = [c for c in classes if sum(cm[c].values())]   # dengeli doğruluk: val'de örneği olan sınıflar üzerinden
    return {"subtiles": n, "accuracy": round(sum(cm[c][c] for c in classes) / n, 3),
            "balanced_accuracy": round(sum(per[c]["R"] for c in present) / len(present), 3),
            "per_class": per, "confusion": cm}


def decide(out, old, new):
    """Karar kuralı (sonuçlar görülmeden yazıldı): yeni model ancak tüm val'de HEM 2 sınıflı mAP50 HEM hücre düzeyi
    dengeli doğruluk eski modelinkinden yüksek ya da eşitse seçilir. Neden iki ölçüt: mAP50 kutu tespitini, hücre
    doğruluğu haritaya giden bilgiyi (E10) ölçer; val küçük (51 karo) olduğu için tek ölçütteki küçük artışa güvenmiyoruz."""
    a, b = out[old]["tum"], out[new]["tum"]
    ok_map = b["detect"]["all"]["mAP50"] >= a["detect"]["all"]["mAP50"]
    ok_cell = b["cell"]["balanced_accuracy"] >= a["cell"]["balanced_accuracy"]
    return {"rule": "mAP50 (2 sınıf) ve hücre dengeli doğruluk ikisi de >= eski", "old": old, "new": new,
            "mAP50": [a["detect"]["all"]["mAP50"], b["detect"]["all"]["mAP50"]],
            "cell_balanced_accuracy": [a["cell"]["balanced_accuracy"], b["cell"]["balanced_accuracy"]],
            "selected": new if (ok_map and ok_cell) else old}


def plot(out, old, new, path):
    """Sunum grafiği: iki ölçüt, iki panel (tek eksen kuralı); gruplar tüm / eski / yeni val karoları."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = [("tum", "Tüm val\n(51 karo)"), ("eski", "1. parti\n(22 karo)"), ("yeni", "2. parti\n(29 karo)")]
    metrics = [(lambda x: x["detect"]["all"]["mAP50"], "Kutu tespiti: mAP50 (2 sınıf)"),
               (lambda x: x["cell"]["balanced_accuracy"], "Hücre düzeyi dengeli doğruluk\n(haritaya giden bilgi)")]
    col = {old: "#2a78d6", new: "#eb6834"}          # kategorik 1–2 (mavi/turuncu), renk körlüğüne uygun çift
    lab = {old: "v1 modeli (150 karo)", new: "v2 modeli (250 karo)"}
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), facecolor="#fcfcfb")
    for ax, (get, title) in zip(axs, metrics):
        ax.set_facecolor("#fcfcfb")
        for k, run in enumerate((old, new)):
            xs = [i + (k - 0.5) * 0.36 for i in range(len(groups))]
            ys = [get(out[run][g]) for g, _ in groups]
            ax.bar(xs, ys, width=0.34, color=col[run], label=lab[run], edgecolor="#fcfcfb", linewidth=2)
            for x, y in zip(xs, ys):
                ax.text(x, y + 0.012, f"{y:.2f}".replace(".", ","), ha="center", va="bottom", fontsize=9, color="#0b0b0b")
        ax.set_xticks(range(len(groups)), [t for _, t in groups], color="#52514e")
        ax.set_ylim(0, 1)
        ax.set_title(title, fontsize=11, color="#0b0b0b", loc="left")
        ax.tick_params(colors="#52514e", length=0)
        ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
    axs[0].legend(frameon=False, fontsize=9, loc="upper right")
    fig.suptitle("Aynı val karolarında v1 ve v2 (val'deki hiçbir karo ya da komşusu eğitimde yok)", fontsize=10, color="#52514e")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#fcfcfb")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="ml/dataset", help="3 sınıflı Roboflow export (valid/ kullanılır)")
    ap.add_argument("--runs", nargs="+", default=RUNS)
    ap.add_argument("--out", default="docs/figures/e6_merged_eval.json")
    ap.add_argument("--decide", action="store_true", help="--runs <eski> <yeni>: karar kuralını uygula")
    args = ap.parse_args()
    ds = ROOT / args.data
    labdir = ds / "valid" / "labels"
    imgs = sorted((ds / "valid" / "images").glob("*.*"))
    groups = {"tum": imgs}
    split_csv = ROOT / "ml" / "split_merged.csv"
    if ds.name == "dataset_merged" and split_csv.exists():
        src = {r["tile"]: r["source"] for r in csv.DictReader(open(split_csv, encoding="utf-8"))}
        for g in ("eski", "yeni"):
            groups[g] = [p for p in imgs if src[p.stem.split("_png")[0]] == g]
    v = DetectionValidator()               # yalnızca Ultralytics'in eşleştirme fonksiyonu ve IoU eşikleri için
    load = lambda run: YOLO(str(ROOT / "ml" / "runs" / run / "weights" / "best.pt"))
    out = {}
    if len(groups) == 1:                   # E6 ablation çıktısının biçimi korunur (DATA_PIPELINE tabloları buna bağlı)
        for run in args.runs:
            out[run] = det_eval(load(run), imgs, labdir, v)
            print(run, json.dumps(out[run], ensure_ascii=False))
        out["cell_level"] = {run: cell_eval(load(run), imgs, labdir) for run in args.runs}
    else:
        out["data"] = args.data
        for run in args.runs:
            m = load(run)
            out[run] = {g: {"detect": det_eval(m, im, labdir, v), "cell": cell_eval(m, im, labdir)} for g, im in groups.items()}
            print(run, json.dumps({g: [x["detect"]["all"], x["cell"]["balanced_accuracy"]] for g, x in out[run].items()}))
        if args.decide:
            out["decision"] = decide(out, *args.runs)
            print("KARAR", json.dumps(out["decision"], ensure_ascii=False))
            plot(out, *args.runs, ROOT / args.out.replace(".json", ".png"))
    (ROOT / args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
