"""E6 · 2. parti – eski 150 + yeni 100 karoyu birleştir, BİTİŞİK karoları aynı tarafa koyan train/val bölmesi yap.

Çalıştır:  venv\\Scripts\\python ml\\merge_v2.py
Girdi :   ml/dataset_v2/ (Roboflow "marstrail-jezero v2-250karo", YOLOv8 export, 250 karo; eski 150'nin etiketleri v1 ile aynı)
          ml/dataset/ (v1 export: v1'in train/valid ayrımı), ml/tiles_manifest.csv, ml/tiles_manifest_2.csv (kategoriler)
Çıktı :   ml/dataset_merged/{train,valid}/{images,labels} + data.yaml   (git'e girmez)
          ml/split_merged.csv (karo → bölüm, bileşen; küçük, git'te)
          docs/figures/e6v2_split.json, docs/figures/e6v2_split.png

Neden bitişiklik grupları: 160 m'lik iki komşu karo aynı kum alanını / kaya sahasını paylaşır. Biri train'de diğeri
val'de olursa model val'de "gördüğü" sahneyi tekrar görür ve skor şişer (uzamsal sızıntı). Karolar 8-komşulukla
(kenar + köşe) bağlı bileşenlere ayrılır, bileşen bütün olarak tek tarafa gider.

Bölme kuralları (sırayla):
  1. v1'de train olan bir karo içeren bileşen → train. Böylece v1 modeli (e6_s2) yeni val'deki hiçbir karoyu
     eğitimde görmemiş olur ve v1 ile v2 AYNI val üzerinde adil karşılaştırılır.
  2. Yalnızca v1 valid karolarından oluşan bileşen → valid (v1'in val'i korunur).
  3. Yalnızca yeni karolardan oluşan bileşenler: val toplamı %20'ye (50 karo) ulaşana kadar kategoriye göre
     tabakalı (kayalik / duz / kum) ve sabit tohumla rastgele seçilir; gerisi train.
"""
import csv
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "ml" / "dataset"
V2 = ROOT / "ml" / "dataset_v2"
OUT = ROOT / "ml" / "dataset_merged"
FIG = ROOT / "docs" / "figures"
NAMES = ["kaya", "kaya_alani", "kum_dalgasi"]
VAL_FRAC = 0.20   # v1 ile aynı oran (120/30)
SEED = 0
KEY = re.compile(r"(jz_r(\d+)_c(\d+))")


def tiles_in(ds: Path):
    out = {}
    for split in ("train", "valid"):
        for im in (ds / split / "images").glob("*.*"):
            m = KEY.search(im.name)
            out[m.group(1)] = {"split": split, "img": im, "lab": ds / split / "labels" / (im.stem + ".txt"),
                               "r": int(m.group(2)), "c": int(m.group(3))}
    return out


def components(keys, pos):
    """8-komşuluk bağlı bileşenleri (birleşim-bul)."""
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    at = {pos[k]: k for k in keys}
    for k in keys:
        r, c = pos[k]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                n = at.get((r + dr, c + dc))
                if n and n != k:
                    parent[find(k)] = find(n)
    groups = defaultdict(list)
    for k in keys:
        groups[find(k)].append(k)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def main():
    v1, v2 = tiles_in(V1), tiles_in(V2)
    assert set(v1) <= set(v2), "v1 karolarının hepsi v2 export'unda olmalı"
    cat = {}
    for f in ("tiles_manifest.csv", "tiles_manifest_2.csv"):
        for r in csv.DictReader(open(ROOT / "ml" / f, encoding="utf-8")):
            cat[Path(r["file"]).stem] = r["category"]
    pos = {k: (t["r"], t["c"]) for k, t in v2.items()}
    comps = components(list(v2), pos)

    # --- Eski bölmenin komşuluk sızıntısı (bilgi için: v1 val skorları bundan etkilenmiş olabilir) ---
    v1_leak = sorted(k for k, t in v1.items() if t["split"] == "valid" and any(
        v1.get(n, {}).get("split") == "train" for n in v1 if max(abs(pos[n][0] - pos[k][0]), abs(pos[n][1] - pos[k][1])) == 1))

    split, reason = {}, {}
    new_only = []
    for g in comps:
        src = {v1[k]["split"] if k in v1 else "new" for k in g}
        if "train" in src:
            s, why = "train", "v1_train_iceriyor"
        elif "valid" in src:
            s, why = "valid", "v1_valid"
        else:
            new_only.append(g)
            continue
        for k in g:
            split[k], reason[k] = s, why

    n_val_target = round(VAL_FRAC * len(v2))
    need = n_val_target - sum(1 for s in split.values() if s == "valid")
    # Tabakalama: yeni karoların kategori payına göre kota (dokusuz karolar "duz" sayılır)
    def gcat(g):
        c = Counter("duz" if cat.get(k, "duz").startswith(("duz", "dokusuz")) else cat.get(k, "duz") for k in g)
        return c.most_common(1)[0][0]
    by_cat = defaultdict(list)
    for g in new_only:
        by_cat[gcat(g)].append(g)
    n_new = sum(len(g) for g in new_only)
    quota = {c: round(need * sum(len(g) for g in gs) / n_new) for c, gs in by_cat.items()}
    rng = random.Random(SEED)
    for c, gs in sorted(by_cat.items()):
        gs = gs[:]
        rng.shuffle(gs)
        taken = 0
        for g in gs:
            s = "valid" if taken + len(g) <= quota[c] else "train"
            taken += len(g) if s == "valid" else 0
            for k in g:
                split[k], reason[k] = s, f"yeni_{c}"

    # --- Yaz ---
    if OUT.exists():
        shutil.rmtree(OUT)
    for s in ("train", "valid"):
        (OUT / s / "images").mkdir(parents=True)
        (OUT / s / "labels").mkdir(parents=True)
    comp_of = {k: i for i, g in enumerate(comps) for k in g}
    rows, boxes = [], Counter()
    sizes, tiles_with = defaultdict(list), Counter()   # kutu kenarı (m) = sqrt(w·h) · 640 px · 0,25 m/px
    for k in sorted(v2):
        t, s = v2[k], split[k]
        shutil.copy2(t["img"], OUT / s / "images" / t["img"].name)
        lab = t["lab"].read_text() if t["lab"].exists() else ""
        (OUT / s / "labels" / (t["img"].stem + ".txt")).write_text(lab)
        src = "eski" if k in v1 else "yeni"
        seen = set()
        for l in lab.splitlines():
            if l.strip():
                c, _, _, w, h = l.split()[:5]
                boxes[(s, src, NAMES[int(c)])] += 1
                sizes[(src, NAMES[int(c)])].append((float(w) * float(h)) ** 0.5 * 640 * 0.25)
                seen.add(NAMES[int(c)])
        for c in seen:
            tiles_with[(src, c)] += 1
        rows.append({"tile": k, "source": src, "v1_split": v1[k]["split"] if k in v1 else "", "category": cat.get(k, ""),
                     "split": s, "component": comp_of[k], "component_size": len(comps[comp_of[k]]), "reason": reason[k]})
    with open(ROOT / "ml" / "split_merged.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from ultralytics.utils import YAML
    YAML.save(OUT / "data.yaml", {"path": str(OUT), "train": "train/images", "val": "valid/images", "nc": 3, "names": NAMES})

    # --- Kontrol: val'deki hiçbir karonun train'de komşusu yok ---
    cross = [(a, b) for a in v2 for b in v2 if split[a] == "valid" and split[b] == "train"
             and max(abs(pos[a][0] - pos[b][0]), abs(pos[a][1] - pos[b][1])) == 1]
    assert not cross, f"komşu sızıntısı: {cross[:5]}"

    cnt = Counter((r["split"], r["source"]) for r in rows)
    stats = {
        "tiles": len(rows), "components": len(comps),
        "component_sizes": dict(sorted(Counter(len(g) for g in comps).items())),
        "split_tiles": {f"{s}_{src}": n for (s, src), n in sorted(cnt.items())},
        "empty_label_tiles": {s: sum(1 for r in rows if r["split"] == s and not
                                     (OUT / s / "labels").glob(f"{r['tile']}_*.txt").__next__().read_text().strip())
                              for s in ("train", "valid")},
        "v1_valid_moved_to_train": sorted(k for k in v1 if v1[k]["split"] == "valid" and split[k] == "train"),
        "v1_valid_adjacent_to_v1_train": v1_leak,
        "boxes": {f"{s}|{src}|{c}": n for (s, src, c), n in sorted(boxes.items())},
        "box_side_m_p10_med_p90": {f"{src}|{c}": [round(float(q), 1) for q in __import__("numpy").percentile(v, [10, 50, 90])]
                                   for (src, c), v in sorted(sizes.items())},
        "boxes_per_tile": {f"{src}|{c}": round(len(v) / (150 if src == "eski" else 100), 2) for (src, c), v in sorted(sizes.items())},
        "tiles_with_class": {f"{src}|{c}": n for (src, c), n in sorted(tiles_with.items())},
        "val_new_by_category": dict(Counter(r["category"] for r in rows if r["split"] == "valid" and r["source"] == "yeni")),
        "cross_split_adjacent_pairs": 0,
    }
    (FIG / "e6v2_split.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    figure(rows, pos)


def figure(rows, pos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 7))
    sty = {("train", "eski"): ("#4C78A8", "s"), ("valid", "eski"): ("#E45756", "s"),
           ("train", "yeni"): ("#4C78A8", "o"), ("valid", "yeni"): ("#E45756", "o")}
    for (s, src), (col, mk) in sty.items():
        pts = [pos[r["tile"]] for r in rows if r["split"] == s and r["source"] == src]
        if pts:
            ax.scatter([c for _, c in pts], [r for r, _ in pts], c=col, marker=mk, s=28,
                       label=f"{s} · {src} ({len(pts)})", edgecolors="none")
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("karo sütunu (160 m)")
    ax.set_ylabel("karo satırı (160 m)")
    ax.set_title("Birleşik veri: bitişik karolar aynı tarafta\n(kare = 1. parti, daire = 2. parti)")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "e6v2_split.png", dpi=130)


if __name__ == "__main__":
    main()
