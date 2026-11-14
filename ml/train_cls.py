"""E6 ablation D – karo sınıflandırma: 320 px alt karo (≈ 80 m) → kum / kayalik / duz.

Çalıştır (önce ml\\make_cls_dataset.py):
    venv\\Scripts\\python ml\\train_cls.py --name e6_cls_s
Çıktı:  ml/runs/<name>/, docs/figures/e6_<name>_metrics.json (+ confusion matrix, results.png)
"""
import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "ml" / "dataset_cls"
FIG = ROOT / "docs" / "figures"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--model", default="yolov8s-cls.pt")  # ImageNet ön-eğitimli, 5 M parametre
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--imgsz", type=int, default=320)    # alt karo zaten 320 px: küçültme yok, 2 m'lik kaya ~8 px kalır
    args = ap.parse_args()
    assert (DS / "train").is_dir(), "Önce: venv\\Scripts\\python ml\\make_cls_dataset.py"

    (ROOT / "ml" / "weights").mkdir(exist_ok=True)
    model = YOLO(str(ROOT / "ml" / "weights" / args.model))
    model.train(
        data=str(DS), epochs=args.epochs, patience=args.patience, batch=args.batch, imgsz=args.imgsz,
        device=0, workers=4, project=str(ROOT / "ml" / "runs"), name=args.name, exist_ok=True,
        seed=0, deterministic=True,
        optimizer="SGD", lr0=0.01, amp=False,   # tespitteki kararlı ayarın aynısı (v1 ıraksaması: train.py)
        hsv_h=0.0, hsv_s=0.0, hsv_v=0.3,        # gri görüntü; yalnız parlaklık
        fliplr=0.5, flipud=0.5,                 # yukarıdan çekim, yön yok
        erasing=0.0,                            # rastgele silme kapalı: 80 m'lik parçadaki tek kaya kümesini silip
                                                # "kayalik" etiketini yanlış yapabilir
        plots=True,
    )
    run = ROOT / "ml" / "runs" / args.name
    best = run / "weights" / "best.pt"

    # --- Val kümesinde tahmin → confusion matrix, sınıf bazında P/R, doğruluk ---
    m = YOLO(str(best))
    classes = sorted(p.name for p in (DS / "val").iterdir() if p.is_dir())
    cm = {t: Counter() for t in classes}
    ms = []
    for t in classes:
        files = sorted((DS / "val" / t).glob("*.png"))
        for r in m.predict([str(f) for f in files], imgsz=args.imgsz, device=0, verbose=False, half=False, batch=32):
            cm[t][r.names[int(r.probs.top1)]] += 1
            ms.append(r.speed["inference"])
    n = sum(sum(v.values()) for v in cm.values())
    acc = sum(cm[t][t] for t in classes) / n
    per = {}
    for c in classes:
        tp = cm[c][c]
        pred_c = sum(cm[t][c] for t in classes)
        true_c = sum(cm[c].values())
        per[c] = {"P": round(tp / pred_c, 3) if pred_c else 0.0, "R": round(tp / true_c, 3) if true_c else 0.0,
                  "n_val": true_c}
    csv = (run / "results.csv").read_text().splitlines()
    hdr = [h.strip() for h in csv[0].split(",")]
    rows = [dict(zip(hdr, map(str.strip, l.split(",")))) for l in csv[1:] if l.strip()]
    res = {
        "task": "classify", "run": args.name, "model": args.model, "classes": classes, "imgsz": args.imgsz,
        "accuracy": round(acc, 3),
        "balanced_accuracy": round(sum(per[c]["R"] for c in classes) / len(classes), 3),  # sınıf dengesizliği için
        "majority_baseline": round(max(sum(cm[t].values()) for t in classes) / n, 3),     # hep "kum" deseydi
        "per_class": per,
        "confusion": {t: {p: cm[t][p] for p in classes} for t in classes},  # satır = gerçek, sütun = tahmin
        "speed_ms_per_img": {"inference": round(sum(ms) / len(ms), 2)},
        "epochs_run": len(rows),
        "best_epoch": int(float(max(rows, key=lambda r: float(r["metrics/accuracy_top1"]))["epoch"])),
        "train_minutes": round(float(rows[-1]["time"]) / 60, 1),
        "params_M": round(sum(p.numel() for p in m.model.parameters()) / 1e6, 1),
    }
    (FIG / f"e6_{args.name}_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for src in ["results.png", "confusion_matrix_normalized.png"]:
        if (run / src).exists():
            shutil.copy2(run / src, FIG / f"e6_{args.name}_{src}")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
