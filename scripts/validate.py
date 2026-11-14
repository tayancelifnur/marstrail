"""
MarsTrail – E10 doğrulama: Perseverance'ın gerçek rotası (D2) bizim geçilebilirlik skorumuzla uyumlu mu?

Çalıştır:  venv\\Scripts\\python scripts\\validate.py     (önce ml\\infer.py ve scripts\\prep_layers.py)
Girdi:     data/raw/M20_traverse.json (D2), data/processed/grid_256.npz (score_base = YOLO'suz, score = YOLO'lu)
Çıktı:     docs/figures/e10_validation.png, docs/figures/e10_validation.json

Mantık: Rover ekibi rotayı tehlikeden kaçınarak seçti. Skorumuz araziyi doğru okuyorsa rotanın geçtiği hücrelerin
skoru alanın geri kalanından DÜŞÜK olmalı. Ölçü:
  AUC = P(rastgele rota hücresinin skoru < rastgele rota dışı hücrenin skoru)   (Mann–Whitney; 0,5 = ayırt etmiyor)
  Geçilebilir oran = rota hücrelerinden geçilmez OLMAYANLARIN yüzdesi (kart E10'un sorusu)
YOLO'nun katkısı iki yerde ölçülür: (1) önce/sonra AUC, HiRISE kapsamıyla sınırlı (YOLO yalnızca orada skoru
değiştiriyor); (2) YOLO'nun kendi kum/kaya yoğunluğu rota hücrelerinde rota dışından düşük mü (doğrudan test).
Sınır: rover bir astronot değil (tekerlek kuma ve kayaya insandan duyarlı), rota bilim hedeflerine de gidiyor.
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prep_layers as P  # noqa: E402

FIG = ROOT / "docs" / "figures"
STEP_M = 10.0   # rota çizgisi 10 m'de bir örneklenir (hücre 70 m: hiçbir hücre atlanmaz)


def route_cells(n):
    B = P.BOUNDS
    feats = json.load(open(P.RAW / "M20_traverse.json", encoding="utf-8"))["features"]
    cells = set()
    for f in feats:
        g = f["geometry"]
        lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for line in lines:
            for (x0, y0, *_), (x1, y1, *_) in zip(line[:-1], line[1:]):
                d = math.hypot((x1 - x0) * math.cos(math.radians(y0)), y1 - y0) * P.M_PER_DEG
                k = max(1, int(d / STEP_M))
                for t in np.linspace(0, 1, k + 1):
                    lon, lat = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
                    if B["west"] <= lon < B["east"] and B["south"] < lat <= B["north"]:
                        c = int((lon - B["west"]) / (B["east"] - B["west"]) * n)
                        r = int((B["north"] - lat) / (B["north"] - B["south"]) * n)
                        cells.add(r * n + c)
    m = np.zeros(n * n, bool)
    m[list(cells)] = True
    return m.reshape(n, n)


def auc(route_vals, other_vals):
    """P(rota < diğer) + 0,5·P(eşit): Mann–Whitney U / (n1·n2), sıra toplamıyla (eşitlikler ortalama sıra)."""
    a, b = np.asarray(route_vals), np.asarray(other_vals)
    allv = np.concatenate([a, b])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):   # eşit değerlere ortalama sıra
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    u_a = ranks[:len(a)].sum() - len(a) * (len(a) + 1) / 2   # a'nın b'den BÜYÜK olduğu çift sayısı
    return 1 - u_a / (len(a) * len(b))


def summarize(score, blocked, route, region):
    r, o = route & region, ~route & region
    return {"route_cells": int(r.sum()), "other_cells": int(o.sum()),
            "median_route": round(float(np.median(score[r])), 3), "median_other": round(float(np.median(score[o])), 3),
            "mean_route": round(float(score[r].mean()), 3), "mean_other": round(float(score[o].mean()), 3),
            "auc_route_lower": round(float(auc(score[r], score[o])), 3),
            "route_passable_pct": round(100 * float((~blocked[r]).mean()), 1),
            "other_passable_pct": round(100 * float((~blocked[o]).mean()), 1)}


def main():
    G = np.load(P.PROC / "grid_256.npz")
    n = P.N_GRID
    valid = ~G["nodata"]
    route = route_cells(n) & valid
    block = lambda s: G["nodata"] | (G["slope"] > P.SLOPE_MAX_DEG) | (s > P.SCORE_MAX)   # noqa: E731
    before, after = G["score_base"], G["score"]
    has_ml = G["ml_has"] if "ml_has" in G.files else np.zeros_like(valid)
    out = {"route_cells_total": int(route.sum()), "route_cells_in_hirise": int((route & has_ml).sum())}
    for name, region in (("tum_alan", valid), ("hirise_kapsami", valid & has_ml)):
        if (route & region).sum() < 5:
            out[name] = {"note": "rota bu bölgede 5 hücreden az; karşılaştırma yapılmadı", "route_cells": int((route & region).sum())}
            continue
        out[name] = {"once_yolo_yok": summarize(before, block(before), route, region),
                     "sonra_yolo": summarize(after, block(after), route, region)}
    # Doğrudan test: YOLO yoğunlukları rota üstünde vs rota dışında (HiRISE kapsamında)
    if "kum_ml" in G.files and (route & has_ml).sum() >= 5:
        reg = valid & has_ml
        d = {}
        for k in ("kum_ml", "kaya_ml"):
            v = np.nan_to_num(G[k])
            d[k] = {"median_route": round(float(np.median(v[route & reg])), 3), "median_other": round(float(np.median(v[~route & reg])), 3),
                    "mean_route": round(float(v[route & reg].mean()), 3), "mean_other": round(float(v[~route & reg].mean()), 3),
                    "pct_route_ge_0_5": round(100 * float((v[route & reg] >= 0.5).mean()), 1),
                    "pct_other_ge_0_5": round(100 * float((v[~route & reg] >= 0.5).mean()), 1),
                    "auc_route_lower": round(float(auc(v[route & reg], v[~route & reg])), 3)}
        out["yolo_dogrudan"] = d
        # Güven aralığı: rota hücreleri yeniden örneklenir (1000 bootstrap, seed 0). Komşu rota hücreleri birbirine
        # benzediği için (uzamsal otokorelasyon) gerçek belirsizlik bundan biraz daha geniş; alt sınır olarak okunmalı.
        rng = np.random.default_rng(0)
        ri, oi = np.where((route & reg).ravel())[0], np.where((~route & reg).ravel())[0]
        oi = rng.choice(oi, size=min(len(oi), 2000), replace=False)   # rota dışı büyük; hız için 2000 hücre örneği
        sb, sa, kum = before.ravel(), after.ravel(), np.nan_to_num(G["kum_ml"]).ravel()
        bs = {"auc_once": [], "auc_sonra": [], "fark": [], "kum_auc": []}
        for _ in range(1000):
            r = rng.choice(ri, size=len(ri), replace=True)
            a0, a1 = auc(sb[r], sb[oi]), auc(sa[r], sa[oi])
            bs["auc_once"].append(a0), bs["auc_sonra"].append(a1), bs["fark"].append(a1 - a0), bs["kum_auc"].append(auc(kum[r], kum[oi]))
        out["bootstrap_95"] = {k: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)] for k, v in bs.items()}
        out["bootstrap_95"]["p_fark_le_0"] = round(float(np.mean(np.array(bs["fark"]) <= 0)), 3)
    out["blocked_cells"] = {"once": int(block(before).sum()), "sonra": int(block(after).sum())}
    out["score_change_in_hirise"] = {"mean_delta": round(float((after - before)[has_ml & valid].mean()), 3),
                                     "abs_mean_delta": round(float(np.abs(after - before)[has_ml & valid].mean()), 3)}
    (FIG / "e10_validation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    figure(G, route, valid, has_ml, before, after, out)


def figure(G, route, valid, has_ml, before, after, out):
    fig = plt.figure(figsize=(15, 9.5))
    ax = [fig.add_subplot(2, 3, i) for i in range(1, 6)]
    bins = np.linspace(0, 1, 41)
    for a, region, title in ((ax[0], valid, "Tüm alan"), (ax[1], valid & has_ml, "HiRISE kapsamı (YOLO'nun değiştirdiği yer)")):
        for s, ls, lab in ((before, "--", "önce (YOLO yok)"), (after, "-", "sonra (YOLO)")):
            for m, col, nm in ((route & region, "#1f77b4", "rota"), (~route & region, "#d62728", "rota dışı")):
                if m.sum() == 0:
                    continue
                v = np.sort(s[m])
                a.plot(v, np.arange(1, len(v) + 1) / len(v), ls=ls, color=col, lw=1.8, label=f"{nm}, {lab}")
        key = "tum_alan" if region is valid else "hirise_kapsami"
        o = out.get(key, {})
        if "sonra_yolo" in o:
            a.set_title(f"{title}\nAUC önce {o['once_yolo_yok']['auc_route_lower']:.3f} → sonra {o['sonra_yolo']['auc_route_lower']:.3f}"
                        f" (rota {o['sonra_yolo']['route_cells']} hücre)", fontsize=10)
        else:
            a.set_title(f"{title}\n{o.get('note', '')}", fontsize=10)
        a.set_xlabel("geçilebilirlik skoru (0 kolay – 1 zor)"), a.set_ylabel("birikimli oran"), a.legend(fontsize=7.5)
        a.axvline(P.SCORE_MAX, color="k", lw=0.8, ls=":")
    if "yolo_dogrudan" in out:
        reg = valid & has_ml
        for i, k in enumerate(("kum_ml", "kaya_ml")):
            v = np.nan_to_num(G[k])
            ax[2].boxplot([v[route & reg], v[~route & reg]], positions=[i * 3, i * 3 + 1], widths=0.7, showfliers=False,
                          patch_artist=True, boxprops=dict(facecolor="#cfe2f3"))
        ax[2].set_xticks([0, 1, 3, 4], ["kum\nrota", "kum\nrota dışı", "kaya\nrota", "kaya\nrota dışı"])
        d = out["yolo_dogrudan"]
        ax[2].set_title(f"YOLO yoğunlukları (HiRISE kapsamı)\nAUC kum {d['kum_ml']['auc_route_lower']:.3f}, kaya {d['kaya_ml']['auc_route_lower']:.3f}", fontsize=10)
    ext = [P.BOUNDS["west"], P.BOUNDS["east"], P.BOUNDS["south"], P.BOUNDS["north"]]
    for a, s, t in ((ax[3], before, "Skor önce (YOLO yok)"), (ax[4], after, "Skor sonra (YOLO)")):
        a.imshow(np.where(valid, s, np.nan), extent=ext, cmap="RdYlGn_r", vmin=0, vmax=0.8)
        rr, cc = np.where(route)
        B = P.BOUNDS
        a.scatter(B["west"] + (cc + 0.5) / 256 * (B["east"] - B["west"]), B["north"] - (rr + 0.5) / 256 * (B["north"] - B["south"]),
                  s=1.5, c="#0000ff", label="Perseverance (D2)")
        a.contour(np.linspace(B["west"], B["east"], 256), np.linspace(B["north"], B["south"], 256), has_ml.astype(float), [0.5],
                  colors="k", linewidths=0.8)
        a.set_title(t + " · siyah çizgi: HiRISE kapsamı", fontsize=10), a.legend(fontsize=7, loc="lower right")
    fig.suptitle("E10 doğrulama: Perseverance rotası (D2) bizim skorumuzda daha mı kolay arazide?", fontsize=12)
    fig.tight_layout(), fig.savefig(FIG / "e10_validation.png", dpi=100), plt.close(fig)


if __name__ == "__main__":
    main()
