"""E6 ablation – adil karşılaştırma: bütün tespit modelleri AYNI 2 sınıflı görevde (kaya+kaya_alani → kaya, kum_dalgasi).

Neden: 3 sınıflı modellerin mAP'i, en zor sınıf olan kaya_alani'yi de ortalamaya katıyor. 2 sınıflı modellerde bu sınıf
yok, bu yüzden genel mAP'ler doğrudan karşılaştırılamaz. Burada 3 sınıflı modellerin tahminlerinde kaya_alani → kaya
yapılır ve hepsi ml/dataset_2cls/valid üzerinde aynı kodla ölçülür. E10'da haritaya giden bilgi de bu iki sınıf
("kayalık" ve "kum") olduğu için seçim bu tabloya göre yapılır.

Çalıştır:  venv\\Scripts\\python ml\\eval_merged.py      (önce train.py --classes2 bir kez çalışmış olmalı)
Çıktı:     docs/figures/e6_merged_eval.json
"""
import json
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionValidator
from ultralytics.utils.metrics import ap_per_class, box_iou

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "ml" / "dataset_2cls" / "valid"
RUNS = ["e6_m3", "e6_s3", "e6_m2", "e6_s2"]
NAMES = ["kaya", "kum_dalgasi"]


def gt(lab: Path, W=640):
    rows = [l.split() for l in lab.read_text().splitlines() if l.strip()] if lab.exists() else []
    if not rows:
        return torch.zeros(0), torch.zeros((0, 4))
    a = torch.tensor([[float(v) for v in r[:5]] for r in rows])
    xy = a[:, 1:3] * W
    wh = a[:, 3:5] * W
    return a[:, 0], torch.cat([xy - wh / 2, xy + wh / 2], 1)


def main():
    v = DetectionValidator()               # yalnızca Ultralytics'in eşleştirme fonksiyonu ve IoU eşikleri için
    iouv = v.iouv                          # 0,50 … 0,95 (10 eşik), resmi val ile aynı
    imgs = sorted(VAL.glob("images/*.*"))
    out = {}
    for run in RUNS:
        m = YOLO(str(ROOT / "ml" / "runs" / run / "weights" / "best.pt"))
        remap = {0: 0, 1: 0, 2: 1} if len(m.names) == 3 else {0: 0, 1: 1}
        stats = {"tp": [], "conf": [], "pred_cls": [], "target_cls": []}
        # conf 0,001 ve NMS IoU 0,7: Ultralytics'in doğrulama ayarları (mAP eğrisinin tamamı için düşük eşik)
        for r in m.predict([str(p) for p in imgs], imgsz=640, conf=0.001, iou=0.7, max_det=300,
                           device=0, half=False, verbose=False, batch=16):
            tcls, tbox = gt(VAL / "labels" / (Path(r.path).stem + ".txt"))
            pcls = torch.tensor([remap[int(c)] for c in r.boxes.cls.cpu()], dtype=torch.float32)
            pbox, pconf = r.boxes.xyxy.cpu(), r.boxes.conf.cpu()
            if len(pcls) and len(tcls):
                tp = np.asarray(v.match_predictions(pcls, tcls, box_iou(tbox, pbox)).cpu()).astype(bool)
            else:
                tp = np.zeros((len(pcls), len(iouv)), bool)
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
        out[run] = {"classes_trained": len(m.names), "per_class": per,
                    "all": {"mAP50": round(float(ap[:, 0].mean()), 3), "mAP50_95": round(float(ap.mean()), 3)}}
        print(run, json.dumps(out[run], ensure_ascii=False))
    out["cell_level"] = cell_level()
    (ROOT / "docs" / "figures" / "e6_merged_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def cell_level(conf=0.25):
    """E10'daki kullanımın ölçüsü: tespitler 80 m'lik alt karoda kum/kayalik/duz sınıfına çevrilir (make_cls_dataset ile
    AYNI kural) ve D'nin val alt karolarıyla karşılaştırılır. Böylece tespit modelleri ile sınıflandırıcı aynı soruda ölçülür.
    conf 0,25: Ultralytics'in tahmin varsayılanı; val üzerinde ayarlanmadı (ayarlansaydı val'e uydurmuş olurduk).
    2 sınıflı modelde kaya_alani yok: kenarı ≥ 40 px (10 m) olan kaya kutusu kaya_alani sayılır. Eşik ölçümden:
    etiketlerde kaya p90 = 9,4 m, kaya_alani p10 = 10,8 m (e6_dataset_stats.json)."""
    import sys
    sys.path.insert(0, str(ROOT / "ml"))
    import make_cls_dataset as C
    val_imgs = sorted((ROOT / "ml" / "dataset" / "valid" / "images").glob("*.*"))
    truth = {}
    for im in val_imgs:
        for i, j, *_, cls in C.label_subtiles(C.boxes(ROOT / "ml" / "dataset" / "valid" / "labels" / (im.stem + ".txt"))):
            truth[(im.stem, i, j)] = cls
    classes = ["duz", "kayalik", "kum"]
    res = {}
    for run in RUNS:
        m = YOLO(str(ROOT / "ml" / "runs" / run / "weights" / "best.pt"))
        three = len(m.names) == 3
        cm = {t: {p: 0 for p in classes} for t in classes}
        for r in m.predict([str(p) for p in val_imgs], imgsz=640, conf=conf, device=0, half=False, verbose=False, batch=16):
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
        res[run] = {"accuracy": round(sum(cm[c][c] for c in classes) / n, 3),
                    "balanced_accuracy": round(sum(per[c]["R"] for c in classes) / 3, 3), "per_class": per, "confusion": cm}
        print("hücre", run, json.dumps(res[run], ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
