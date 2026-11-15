"""E6 ablation karşılaştırması: docs/figures/<run>_metrics.json dosyalarını tabloya döker, seçilen modeli kopyalar.

Çalıştır:
    venv\\Scripts\\python ml\\compare_runs.py                    # tablo (markdown) + docs/figures/e6_ablation.json
    venv\\Scripts\\python ml\\compare_runs.py --select e6_m2     # bu run'ın best.pt'si → ml/models/yolo_marstrail.pt
"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
RUNS = ["e6v1", "e6_m3", "e6_s3", "e6_m2", "e6_s2", "e6_cls_s", "e6v2_s2"]   # e6v2_s2: 250 karo (merge_v2.py), val farklı!
LABEL = {"e6v1": "v1 (ıraksadı)", "e6_m3": "0) m, 3 sınıf", "e6_s3": "A) s, 3 sınıf",
         "e6_m2": "B) m, 2 sınıf", "e6_s2": "C) s, 2 sınıf", "e6_cls_s": "D) s-cls, karo",
         "e6v2_s2": "C-v2) s, 2 sınıf, 250 karo (başka val)"}


def load(run):
    p = FIG / ("e6v1_metrics.json" if run == "e6v1" else f"{run}_metrics.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def f(x):
    return "–" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select")
    args = ap.parse_args()
    res = {r: load(r) for r in RUNS}
    print("| Deney | mAP50 | mAP50-95 | kaya mAP50 (R) | kaya_alani mAP50 | kum_dalgasi mAP50 (R) | Süre | Çıkarım ms | Epoch (en iyi) | NaN |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r, m in res.items():
        if not m or m.get("task", "detect") != "detect":
            continue
        pc = m["per_class"]
        g = lambda c, k: pc.get(c, {}).get(k)
        print(f"| {LABEL[r]} | {f(m['all']['mAP50'])} | {f(m['all']['mAP50_95'])} | {f(g('kaya', 'mAP50'))} ({f(g('kaya', 'R'))}) "
              f"| {f(g('kaya_alani', 'mAP50'))} | {f(g('kum_dalgasi', 'mAP50'))} ({f(g('kum_dalgasi', 'R'))}) "
              f"| {m.get('train_minutes', '3,2')} dk | {f(m['speed_ms_per_img']['inference'])} | {m['epochs_run']} ({m['best_epoch']}) "
              f"| {len(m.get('nan_val_epochs', [])) or ('13' if r == 'e6v1' else 0)} |")
    c = res.get("e6_cls_s")
    if c:
        print("\n| Deney | Doğruluk | Dengeli doğruluk | Hep-kum taban çizgisi | " + " | ".join(f"{k} P/R" for k in c["classes"]) + " | Süre | ms |")
        print("| --- | --- | --- | --- | " + " | ".join("---" for _ in c["classes"]) + " | --- | --- |")
        print(f"| {LABEL['e6_cls_s']} | {f(c['accuracy'])} | {f(c['balanced_accuracy'])} | {f(c['majority_baseline'])} | "
              + " | ".join(f"{f(c['per_class'][k]['P'])} / {f(c['per_class'][k]['R'])} (n={c['per_class'][k]['n_val']})" for k in c["classes"])
              + f" | {c['train_minutes']} dk | {f(c['speed_ms_per_img']['inference'])} |")
        print("Confusion (satır gerçek, sütun tahmin):", json.dumps(c["confusion"], ensure_ascii=False))
    (FIG / "e6_ablation.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.select:
        src = ROOT / "ml" / "runs" / args.select / "weights" / "best.pt"
        (ROOT / "ml" / "models").mkdir(exist_ok=True)
        shutil.copy2(src, ROOT / "ml" / "models" / "yolo_marstrail.pt")
        (ROOT / "ml" / "models" / "yolo_marstrail.json").write_text(
            json.dumps({"run": args.select, "metrics": res.get(args.select)}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSeçildi: {src} → ml/models/yolo_marstrail.pt")


if __name__ == "__main__":
    main()
