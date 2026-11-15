"""E6 – YOLOv8 tespit eğitimi: Jezero HiRISE karolarında kaya / kaya_alani / kum_dalgasi.

Çalıştır (proje kökünden, Elif terminalde):
    venv\\Scripts\\python ml\\train.py --name e6_m3                         # yolov8m, 3 sınıf
    venv\\Scripts\\python ml\\train.py --name e6_s3 --model yolov8s.pt      # yolov8s, 3 sınıf
    venv\\Scripts\\python ml\\train.py --name e6_m2 --classes2              # kaya_alani → kaya
    venv\\Scripts\\python ml\\train.py --name e6_s2 --classes2 --model yolov8s.pt
    venv\\Scripts\\python ml\\train.py --name e6v2_s2 --classes2 --model yolov8s.pt --data ml/dataset_merged   # 2. parti (merge_v2.py)

Girdi : ml/dataset/ (Roboflow "marstrail-jezero v1-150karo", YOLOv8 export, 120 train / 30 valid)
        --data ile başka bir export (ör. ml/dataset_merged, 250 karo) seçilir
        --classes2 ile <data>_2cls/ otomatik üretilir (aynı görüntüler, kaya_alani kutuları kaya'ya birleşir)
Çıktı : ml/runs/<name>/ (Ultralytics: results.png, confusion_matrix*.png, weights/best.pt)
        docs/figures/<name>_metrics.json + <name>_*.png → ml/compare_runs.py karşılaştırır ve en iyi modeli
        ml/models/yolo_marstrail.pt yapar (E10 bunu kullanır).
"""
import argparse
import json
import math
import shutil
from pathlib import Path

from ultralytics import YOLO
from ultralytics.utils import YAML

ROOT = Path(__file__).resolve().parents[1]
DS_DEFAULT = ROOT / "ml" / "dataset"
FIG = ROOT / "docs" / "figures"
EXPECTED = ["kaya", "kaya_alani", "kum_dalgasi"]


def clean_data_yaml(DS: Path) -> Path:
    """Roboflow'un data.yaml'ı '../train/images' gibi göreli yollar yazıyor ve olmayan 'test' bölümünü gösteriyor.
    Mutlak 'path' ile temiz bir kopya üretiyoruz. Sınıf sırası Roboflow'unkiyle aynı (etiket indisleri buna göre)."""
    src = YAML.load(DS / "data.yaml")
    assert list(src["names"]) == EXPECTED, f"Beklenmeyen sınıflar/sıra: {src['names']}"
    for split in ("train", "valid"):
        assert (DS / split / "images").is_dir(), f"{split}/images yok – Roboflow zip'i ml/dataset/ içine açıldı mı?"
    dst = DS / "data_marstrail.yaml"
    YAML.save(dst, {"path": str(DS), "train": "train/images", "val": "valid/images", "nc": 3, "names": EXPECTED})
    return dst


def two_class_yaml(DS: Path) -> Path:
    """Ablation B/C: kaya_alani (1) kutuları kaya'ya (0) birleşir, kum_dalgasi 2 → 1.
    Neden: kaya ile kaya_alani aynı dokunun iki ölçeği; v1 confusion matrix'te gerçek kayaların %18'i kaya_alani
    tahmin edildi ve kaya_alani'nin valid'de yalnızca 17 kutusu var. Haritaya giden bilgi ikisinde de "kayalık"."""
    remap = {0: 0, 1: 0, 2: 1}
    DS2 = DS.parent / (DS.name + "_2cls")   # ml/dataset → ml/dataset_2cls (E6 ile aynı yol)
    if DS2.exists():
        shutil.rmtree(DS2)
    for split in ("train", "valid"):
        (DS2 / split / "labels").mkdir(parents=True)
        shutil.copytree(DS / split / "images", DS2 / split / "images")
        for lab in (DS / split / "labels").glob("*.txt"):
            rows = [l.split() for l in lab.read_text().splitlines() if l.strip()]
            out = [" ".join([str(remap[int(r[0])])] + r[1:]) for r in rows]
            (DS2 / split / "labels" / lab.name).write_text("\n".join(out) + ("\n" if out else ""))
    dst = DS2 / "data.yaml"
    YAML.save(dst, {"path": str(DS2), "train": "train/images", "val": "valid/images", "nc": 2,
                    "names": ["kaya", "kum_dalgasi"]})
    return dst


def nan_watch(trainer):
    """v1'de epoch 3'te ıraksama oldu ve ancak sonradan fark edildi. Artık her epoch sonunda kontrol edilip uyarılıyor."""
    v = trainer.metrics.get("val/box_loss")
    if v is not None and isinstance(v, float) and math.isnan(v):
        print(f"\n!!! UYARI: epoch {trainer.epoch + 1} doğrulama kaybı NaN – eğitim ıraksıyor !!!\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="run adı, ör. e6_m3")
    ap.add_argument("--model", default="yolov8m.pt")
    ap.add_argument("--classes2", action="store_true", help="kaya_alani'yi kaya'ya birleştir (2 sınıf)")
    # 100 epoch + patience 20: 120 karoluk küçük veri setinde 20 epoch iyileşme yoksa erken durur.
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--batch", type=int, default=16)   # yolov8m @640, batch 16 ≈ 10–12 GB VRAM; RTX 5090 Laptop (24 GB) rahat
    ap.add_argument("--imgsz", type=int, default=640)  # karolar zaten 640×640 (0,25 m/px → 160 m); yeniden örnekleme yok
    # v1 (optimizer auto → AdamW lr 0,0014, AMP fp16 açık) epoch 3'te ıraksadı: cls_loss 4 → 17, val kaybı 13 epoch NaN.
    # İki olası nedeni de kaldırıyoruz: YOLO'nun klasik tarifi SGD lr0 0,01 (ısınma ayarları SGD için tasarlandı)
    # ve fp32 eğitim (RTX 5090'da evrişimler TF32 ile hızlı; süre ~1,5× uzar, 3 dk → ~5 dk).
    ap.add_argument("--optimizer", default="SGD")
    ap.add_argument("--lr0", type=float, default=0.01)
    ap.add_argument("--amp", action="store_true", help="fp16 karışık hassasiyet (v1'de ıraksadı; varsayılan kapalı)")
    ap.add_argument("--data", default=str(DS_DEFAULT), help="Roboflow YOLOv8 export klasörü (train/, valid/, data.yaml)")
    ap.add_argument("--diag", action="store_true", help="sadece eğit; docs/figures'a yazma")
    args = ap.parse_args()

    ds = Path(args.data) if Path(args.data).is_absolute() else ROOT / args.data
    data = two_class_yaml(ds) if args.classes2 else clean_data_yaml(ds)
    (ROOT / "ml" / "weights").mkdir(exist_ok=True)
    model = YOLO(str(ROOT / "ml" / "weights" / args.model))  # COCO ön-eğitimli ağırlık; yoksa buraya indirilir
    model.add_callback("on_fit_epoch_end", nan_watch)

    model.train(
        data=str(data), epochs=args.epochs, patience=args.patience, batch=args.batch, imgsz=args.imgsz,
        device=0, workers=4,              # Windows'ta çok sayıda dataloader işçisi yavaş başlıyor; 4 yeterli
        project=str(ROOT / "ml" / "runs"), name=args.name, exist_ok=True,
        seed=0, deterministic=True,       # ablation koşuları aynı tohumla: fark ayardan gelsin, şanstan değil
        optimizer=args.optimizer, lr0=args.lr0, amp=args.amp,
        cache="ram",                      # 150–250 karo × 640² küçük; diskten okuma darboğazı olmasın
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
    if args.diag:
        return
    best = run / "weights" / "best.pt"

    # --- En iyi ağırlıkla doğrulama: sınıf bazında P, R, mAP50, mAP50-95 ---
    m = YOLO(str(best)).val(data=str(data), imgsz=args.imgsz, batch=args.batch, device=0, plots=False, half=False,
                            project=str(ROOT / "ml" / "runs"), name=args.name + "_val", exist_ok=True)
    names = m.names
    per_class = {}
    for i, c in enumerate(m.box.ap_class_index):
        p, r, ap50, ap = m.box.class_result(i)
        per_class[names[int(c)]] = {"P": round(float(p), 3), "R": round(float(r), 3),
                                    "mAP50": round(float(ap50), 3), "mAP50_95": round(float(ap), 3)}
    res = {
        "task": "detect", "run": args.name, "model": args.model, "data": ds.name, "classes": list(names.values()),
        "optimizer": args.optimizer, "lr0": args.lr0, "amp": args.amp,
        "epochs_requested": args.epochs, "imgsz": args.imgsz, "batch": args.batch, "patience": args.patience,
        "all": {"P": round(float(m.box.mp), 3), "R": round(float(m.box.mr), 3),
                "mAP50": round(float(m.box.map50), 3), "mAP50_95": round(float(m.box.map), 3)},
        "per_class": per_class,
        "speed_ms_per_img": {k: round(float(v), 2) for k, v in m.speed.items()},
        "params_M": round(sum(p.numel() for p in YOLO(str(best)).model.parameters()) / 1e6, 1),
        "weights_mb": round(best.stat().st_size / 1e6, 1),
    }
    csv = (run / "results.csv").read_text().splitlines()
    hdr = [h.strip() for h in csv[0].split(",")]
    rows = [dict(zip(hdr, map(str.strip, l.split(",")))) for l in csv[1:] if l.strip()]
    best_row = max(rows, key=lambda r: float(r["metrics/mAP50-95(B)"]))
    res["epochs_run"] = len(rows)
    res["best_epoch"] = int(float(best_row["epoch"]))
    res["train_minutes"] = round(float(rows[-1]["time"]) / 60, 1)
    res["nan_val_epochs"] = [int(float(r["epoch"])) for r in rows if r.get("val/box_loss", "") == "nan"]
    (FIG / f"{args.name}_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    # Sunum/belge için önemli şekilleri docs/figures'a kopyala (ml/runs git'e girmez)
    for src in ["results.png", "confusion_matrix_normalized.png", "BoxPR_curve.png", "val_batch0_pred.jpg"]:
        if (run / src).exists():
            shutil.copy2(run / src, FIG / f"{args.name}_{src}")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if res["nan_val_epochs"]:
        print(f"UYARI: doğrulama kaybı şu epoch'larda NaN: {res['nan_val_epochs']}")


if __name__ == "__main__":  # Windows: dataloader çok işlemli çalıştığı için koruma şart
    main()
