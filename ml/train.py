"""E6 – YOLOv8 eğitimi: Jezero HiRISE karolarında kaya / kaya_alani / kum_dalgasi.

Çalıştır (proje kökünden, Elif terminalde):
    venv\\Scripts\\python ml\\train.py
Kısa deneme (pipeline çalışıyor mu, ~1 dk):
    venv\\Scripts\\python ml\\train.py --epochs 1 --name smoke

Girdi : ml/dataset/ (Roboflow "marstrail-jezero v1-150karo", YOLOv8 export, 120 train / 30 valid)
Çıktı : ml/runs/<name>/ (Ultralytics: results.png, confusion_matrix*.png, weights/best.pt)
        ml/models/yolo_marstrail.pt          → E10 çıkarımı bunu kullanır (git'e girmez, *.pt)
        docs/figures/e6_*.png, e6_metrics.json → sınıf bazında mAP, DATA_PIPELINE.md ve LOG.md buradan yazılır
"""
import argparse
import json
import shutil
from pathlib import Path

from ultralytics import YOLO
from ultralytics.utils import YAML

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "ml" / "dataset"
FIG = ROOT / "docs" / "figures"
EXPECTED = {"kaya", "kaya_alani", "kum_dalgasi"}


def clean_data_yaml() -> Path:
    """Roboflow'un data.yaml'ı '../train/images' gibi göreli yollar yazıyor ve olmayan 'test' bölümünü gösteriyor.
    Ultralytics bunu çoğu zaman tolere ediyor ama emin olmak için mutlak 'path' ile temiz bir kopya üretiyoruz.
    Sınıf sırası Roboflow'unkiyle aynı kalmalı (etiket dosyalarındaki indisler buna göre)."""
    src = YAML.load(DS / "data.yaml")
    names = src["names"]
    assert set(names) == EXPECTED, f"Beklenmeyen sınıflar: {names}"
    for split in ("train", "valid"):
        assert (DS / split / "images").is_dir(), f"{split}/images yok – Roboflow zip'i ml/dataset/ içine açıldı mı?"
    dst = DS / "data_marstrail.yaml"
    YAML.save(dst, {"path": str(DS), "train": "train/images", "val": "valid/images",
                    "nc": len(names), "names": names})
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolov8m.pt")
    # 100 epoch + patience 20: 120 karoluk küçük veri setinde mAP genelde 40–70. epoch arası doyuyor;
    # 20 epoch iyileşme yoksa erken durur (aşırı öğrenmeyi ve boşa GPU süresini keser).
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--batch", type=int, default=16)   # yolov8m @640, batch 16 ≈ 10–12 GB VRAM; RTX 5090 Laptop (24 GB) rahat
    ap.add_argument("--imgsz", type=int, default=640)  # karolar zaten 640×640 (0,25 m/px → 160 m); yeniden örnekleme yok
    ap.add_argument("--name", default="e6_yolov8m")
    args = ap.parse_args()

    data = clean_data_yaml()
    (ROOT / "ml" / "weights").mkdir(exist_ok=True)
    model = YOLO(str(ROOT / "ml" / "weights" / args.model))  # COCO ön-eğitimli ağırlık; yoksa buraya indirilir

    model.train(
        data=str(data), epochs=args.epochs, patience=args.patience, batch=args.batch, imgsz=args.imgsz,
        device=0, workers=4,              # Windows'ta çok sayıda dataloader işçisi yavaş başlıyor; 4 yeterli
        project=str(ROOT / "ml" / "runs"), name=args.name, exist_ok=True,
        seed=0, deterministic=True,       # sunumdaki sayılar tekrar üretilebilsin
        cache="ram",                      # 150 karo × 640² küçük; diskten okuma darboğazı olmasın
        # --- Artırma (augmentation) seçimleri: Roboflow'da artırma YOK, hepsi burada ---
        hsv_h=0.0, hsv_s=0.0,             # görüntü gri (HiRISE pankromatik); renk tonu/doygunluk anlamsız
        hsv_v=0.3,                        # parlaklık ±%30: farklı güneş açısı / mozaik şeritleri arası ton farkı
        fliplr=0.5, flipud=0.5,           # yukarıdan çekim: "yukarı" yönü yok. Gölge yönü değişir ama kaya/çukur
                                          # zaten gölge yönüne bakmadan tek sınıf ("kaya") olarak etiketlendi
        degrees=0.0,                      # döndürme kutuları şişirir; ince kum sırtlarında kutu çok bozulur
        scale=0.25,                       # varsayılan 0.5 yerine 0.25: sınıflar fiziksel boyuta bağlı (kaya ~5 m,
                                          # kaya_alani ~24 m medyan); büyük ölçek oynaması ikisini karıştırır
        mosaic=1.0, close_mosaic=10,      # küçük veri setinde mozaik çeşitlilik sağlar; son 10 epoch kapalı
        plots=True,
    )

    run = ROOT / "ml" / "runs" / args.name
    best = run / "weights" / "best.pt"
    (ROOT / "ml" / "models").mkdir(exist_ok=True)
    shutil.copy2(best, ROOT / "ml" / "models" / "yolo_marstrail.pt")

    # --- En iyi ağırlıkla doğrulama: sınıf bazında P, R, mAP50, mAP50-95 ---
    m = YOLO(str(best)).val(data=str(data), imgsz=args.imgsz, batch=args.batch, device=0, plots=False,
                            project=str(ROOT / "ml" / "runs"), name=args.name + "_val", exist_ok=True)
    names = m.names
    per_class = {}
    for i, c in enumerate(m.box.ap_class_index):
        p, r, ap50, ap = m.box.class_result(i)
        per_class[names[int(c)]] = {"P": round(float(p), 3), "R": round(float(r), 3),
                                    "mAP50": round(float(ap50), 3), "mAP50_95": round(float(ap), 3)}
    res = {
        "run": str(run.relative_to(ROOT)), "model": args.model, "epochs_requested": args.epochs,
        "imgsz": args.imgsz, "batch": args.batch, "patience": args.patience,
        "all": {"P": round(float(m.box.mp), 3), "R": round(float(m.box.mr), 3),
                "mAP50": round(float(m.box.map50), 3), "mAP50_95": round(float(m.box.map), 3)},
        "per_class": per_class,
        "speed_ms_per_img": {k: round(float(v), 2) for k, v in m.speed.items()},
    }
    # Kaç epoch koştu, en iyi epoch hangisi (results.csv'den)
    csv = (run / "results.csv").read_text().splitlines()
    hdr = [h.strip() for h in csv[0].split(",")]
    rows = [dict(zip(hdr, map(str.strip, l.split(",")))) for l in csv[1:] if l.strip()]
    k = "metrics/mAP50-95(B)"
    best_row = max(rows, key=lambda r: float(r[k]))
    res["epochs_run"] = len(rows)
    res["best_epoch"] = int(float(best_row["epoch"]))
    (FIG / "e6_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    # Sunum/belge için önemli şekilleri docs/figures'a kopyala (ml/runs git'e girmez)
    for src in ["results.png", "confusion_matrix.png", "confusion_matrix_normalized.png",
                "BoxPR_curve.png", "PR_curve.png", "val_batch0_pred.jpg", "val_batch0_labels.jpg"]:
        if (run / src).exists():
            shutil.copy2(run / src, FIG / f"e6_{src}")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # Windows: dataloader çok işlemli çalıştığı için koruma şart
    main()
