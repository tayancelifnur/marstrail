"""E6 – Roboflow YOLOv8 dışa aktarımını ölçer (eğitimden önce).

Çalıştır:  venv\\Scripts\\python ml\\dataset_stats.py
Çıktı:     docs/figures/e6_dataset_stats.json, docs/figures/e6_dataset.png

Sayılar elle yazılmaz (CLAUDE.md veri hattı kuralı); DATA_PIPELINE.md'deki E6 tablosu bu dosyadan gelir.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ultralytics.utils import YAML  # ultralytics 8.4 kendi YAML okuyucusunu taşıyor (pyyaml kurulu değil)
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "ml" / "dataset"
FIG = ROOT / "docs" / "figures"
RES_M = 0.25  # HiRISE ortomozaik çözünürlüğü (ml/tiles_meta.json → res_m)


def tile_name(img: Path) -> str:
    # Roboflow adı: jz_r023_c023_png.rf.<hash>.jpg  →  özgün karo adı jz_r023_c023.png
    m = re.match(r"(jz_r\d+_c\d+)_png\.rf\.", img.name)
    return (m.group(1) + ".png") if m else img.name


def main():
    cfg = YAML.load(DS / "data.yaml")
    names = cfg["names"]
    manifest = {r["file"]: r for r in csv.DictReader(open(ROOT / "ml" / "tiles_manifest.csv", encoding="utf-8"))}

    out = {"names": names, "splits": {}, "res_m": RES_M}
    sizes = defaultdict(list)          # sınıf → kutu kenarı (m, sqrt(w·h))
    per_cat = defaultdict(Counter)     # manifest kategorisi → sınıf sayıları
    seen = set()
    bad = []
    full_tile = Counter()
    for split in ("train", "valid", "test"):
        idir = DS / split / "images"
        if not idir.exists():
            continue
        imgs = sorted(idir.glob("*.*"))
        boxes, empty, img_sizes = Counter(), 0, Counter()
        n_box_img = []
        for im in imgs:
            W, H = Image.open(im).size
            img_sizes[f"{W}x{H}"] += 1
            t = tile_name(im)
            seen.add(t)
            cat = manifest.get(t, {}).get("category", "bilinmiyor")
            lab = DS / split / "labels" / (im.stem + ".txt")
            rows = [l.split() for l in lab.read_text().splitlines() if l.strip()] if lab.exists() else []
            if not rows:
                empty += 1
                per_cat[cat]["(boş)"] += 1
            n_box_img.append(len(rows))
            for r in rows:
                c, x, y, w, h = int(r[0]), *map(float, r[1:5])
                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1) or c >= len(names):
                    bad.append(f"{split}/{lab.name}: {' '.join(r)}")
                    continue
                boxes[names[c]] += 1
                if w * h >= 0.8:  # karonun ≥%80'ini kaplayan kutu = nesne değil "bütün karo bu türden" etiketi
                    full_tile[names[c]] += 1
                per_cat[cat][names[c]] += 1
                sizes[names[c]].append(float(np.sqrt(w * W * h * H)) * RES_M)
        out["splits"][split] = {
            "images": len(imgs), "empty_images": empty, "image_sizes": dict(img_sizes),
            "boxes": {n: boxes.get(n, 0) for n in names}, "boxes_total": sum(boxes.values()),
            "boxes_per_image_median": float(np.median(n_box_img)) if n_box_img else 0,
            "boxes_per_image_max": int(max(n_box_img)) if n_box_img else 0,
        }

    out["box_size_m"] = {n: {"count": len(v), "p10": round(float(np.percentile(v, 10)), 1),
                             "median": round(float(np.median(v)), 1), "p90": round(float(np.percentile(v, 90)), 1)}
                         for n, v in sizes.items() if v}
    out["full_tile_boxes"] = {n: full_tile.get(n, 0) for n in names}
    out["by_tile_category"] = {k: dict(v) for k, v in sorted(per_cat.items())}
    out["tiles_in_manifest"] = len(manifest)
    out["tiles_exported"] = len(seen)
    out["tiles_missing_from_export"] = sorted(set(manifest) - seen)
    out["invalid_label_rows"] = bad
    (FIG / "e6_dataset_stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Şekil: sınıf başına kutu sayısı (train/valid) + kutu boyu dağılımı ---
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    xs = np.arange(len(names))
    for i, split in enumerate(s for s in ("train", "valid") if s in out["splits"]):
        v = [out["splits"][split]["boxes"][n] for n in names]
        b = ax[0].bar(xs + (i - 0.5) * 0.38, v, 0.38, label=split)
        ax[0].bar_label(b, fontsize=8)
    ax[0].set_xticks(xs, names); ax[0].set_ylabel("kutu sayısı"); ax[0].set_title("Sınıf başına etiket"); ax[0].legend()
    bins = np.logspace(np.log10(0.5), np.log10(160), 30)
    for n in names:
        if sizes[n]:
            ax[1].hist(sizes[n], bins=bins, alpha=0.6, label=f"{n} (medyan {np.median(sizes[n]):.1f} m)")
    ax[1].set_xscale("log"); ax[1].set_xlabel("kutu boyu √(w·h), metre (0,25 m/px)"); ax[1].set_ylabel("kutu")
    ax[1].set_title("Kutu boyu dağılımı"); ax[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "e6_dataset.png", dpi=120)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
