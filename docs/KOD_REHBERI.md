# Kod rehberi

Hangi dosya ne yapar, veri nereden nereye akar, bir sayı ya da katman değişince neyin yeniden çalıştırılacağı. Formüllerin gerekçeleri kodda yorum satırı olarak yazılı; burada yalnızca yerleri gösteriliyor.

## Genel akış

```
data/raw/ (D1–D8, indirilen ham veri; git'e girmez)
   │  scripts/download_data.py
   ▼
scripts/prep_layers.py ──► web/data/grid.json, layers.json, layers/*.png      (füzyon skoru, 256² grid, 70 m)
scripts/build_regions.py ─► web/data/regions.json, poi.geojson, stories.json   (noktalar, tarihçe, fotoğraflar)
   ▲
   │  data/processed/ml_density_*.npz  (YOLO yoğunlukları, varsa füzyona girer)
ml/ (etiket → eğitim → çıkarım)
   tile_for_yolo.py → Roboflow'da etiket → train.py → eval_merged.py → compare_runs.py --select → infer.py
   │
scripts/validate.py ──► docs/figures/e10_validation.*   (Perseverance rotasıyla doğrulama)
scripts/pipeline_stats.py ► docs/figures/pipeline_stats.json  (DATA_PIPELINE.md'deki sayılar)
scripts/audit_numbers.py ─► docs/SAYI_DENETIMI.md        (sunumdaki her sayının kaynağı)
scripts/make_slides.py ───► docs/sunum/MarsTrail.pptx    (+ --pdf)
scripts/make_video.py ────► docs/sunum/MarsTrail_sunum.mp4

web/ (tarayıcı, backend yok) ─ index.html + app.js (arayüz) + walkback.js, eva.js, rescue.js, marstime.js (algoritmalar)
```

## Python: veri hattı (`scripts/`)

| Dosya | Kart | Ne yapar | Girdi → çıktı |
| --- | --- | --- | --- |
| `download_data.py` | E2 | D1–D8'i indirir; dosya başına boyut ve özet yazar | URL'ler → `data/raw/` |
| `make_dummies.py` | E1 | Gerçek veri gelmeden önce arayüz için sahte `web/data/` dosyaları üretir | → `web/data/*` |
| `prep_layers.py` | E3, E10 | Reprojeksiyon, kırpma, eğim, termal normalizasyon, jeoloji rasterizasyonu, **geçilebilirlik füzyonu**, grid. YOLO yoğunluğu varsa kum ve kaya terimlerine eşit ağırlıkla katar | D4, D5, D6 + `ml_density` → `grid.json`, `layers/*.png` |
| `build_regions.py` | E7 | Nokta kartları: keşif tarihi, görevler, Perseverance Sol'ü (D1), fotoğraf (D7 eleme hunisi) | D1, D3, D7 → `regions.json`, `poi.geojson`, `stories.json`, `photos/` |
| `tile_for_yolo.py` | E5 | HiRISE mozaiğini 640 px karolara böler; NoData/dokusuz eleme; birim tabanlı aday seçimi | D8 → `ml/roboflow_upload/` |
| `tile_batch2.py` | E6 | 2. etiket partisi: eski karolara bitişik olmayan 100 düz/kayalık/kum karo | D8 → `ml/roboflow_upload_2/` |
| `validate.py` | E10 | D2 rotası hücrelerinin skor dağılımı ile rota dışını karşılaştırır (AUC, bootstrap) | grid + D2 → `e10_validation.png/json` |
| `pipeline_stats.py` | E3 | Her veri adımının ham/atılan/son sayıları ve önce/sonra görselleri | → `pipeline_stats.json`, `figures/d*.png` |
| `make_previews.py` | – | Veri seti önizlemeleri | → `figures/onizleme/` |
| `audit_numbers.py` | E15 | Sunum ve teslimdeki sayıları JSON'lardan ve uygulama testlerinden yeniden hesaplar | → `docs/SAYI_DENETIMI.md` |
| `make_slides.py` | E15 | 7 slaytlık PPTX: koyu tema, Calibri, hareket (OOXML), gömülü demo, taşma kontrolü | `SLAYTLAR.md`, `figures/` → `docs/sunum/MarsTrail.pptx` |
| `make_video.py` | E15 | Slaytları kare kare çizip sessiz sunum videosu yapar (ffmpeg, H.264) | aynı yerleşim + `demo.mp4` → `MarsTrail_sunum.mp4` |

## Python: model (`ml/`)

| Dosya | Ne yapar |
| --- | --- |
| `dataset_stats.py` | Roboflow dışa aktarımını eğitimden önce ölçer: kutu sayıları, boyutları, boş karolar |
| `train.py` | YOLOv8 eğitimi. Kararlı ayar: SGD lr0 0,01, fp32, NaN uyarısı. Artırma seçimleri yorumlarda. `--classes2` ile kaya_alani → kaya; `--data` ile başka bir dışa aktarım |
| `make_cls_dataset.py`, `train_cls.py` | Ablation D: 80 m alt karo sınıflandırıcısı (kum / kayalık / düz) |
| `eval_merged.py` | Adil karşılaştırma: bütün modeller aynı 2 sınıflı görevde. Hücre düzeyi doğruluk; `--decide` ile önceden yazılmış karar kuralı |
| `compare_runs.py` | Koşu tablosu; `--select <run>` seçilen modeli `ml/models/yolo_marstrail.pt` yapar |
| `merge_v2.py` | 150 + 100 karoyu birleştirir; bitişik karoları aynı tarafa koyan bölme (`split_merged.csv`) |
| `infer.py` | 1146 karoda çıkarım → 70 m hücre başına `kum_ml`, `kaya_ml`; etiket denetimi (`audit_missed_labels.csv`) |
| `ETIKETLEME.md` | Etiket tanımları, sınırlamalar, Roboflow adımları |

**Model değişince:** `ml\compare_runs.py --select <run>` → `ml\infer.py` → `scripts\prep_layers.py` → `scripts\validate.py` → `scripts\audit_numbers.py`.

## Web (`web/`)

| Dosya | Sahibi | Ne yapar | Dışa açık API |
| --- | --- | --- | --- |
| `index.html`, `app.js`, `style.css` | Gözde | Arayüz: CesiumJS Mars küresi, katmanlar, profil, planlayıcı, canlı yürüyüş, Hayatta Kal; localStorage | – |
| `walkback.js` | Elif | Grid yükleme, Tobler hızı, Dijkstra; **O₂ bölgeleri** (yeşil ≤ O₂/1,25, sarı ≤ O₂), güvenli rota, eve dönüş süresi | `Walkback.load, zones, path, timeHome, travelTimes, o2Multiplier, cellOf, lonLatOf` |
| `eva.js` | Elif | EVA planlayıcı: duraklar → bacaklar, zaman çizelgesi, sarf malzemesi, dönüş noktası, Go/No-Go, telsiz görüş hattı | `Eva.plan, positionAt, nextWindow, lineOfSight` |
| `rescue.js` | Elif | Telsiz koptu: olasılıklı arama alanı, İHA zikzak rotası, arkadaşın kurtarma rotası. Kurtarılabilirlik İHA'nın %90 bulma süresini içerir; adlar profilden | `Rescue.respond, searchArea, droneRoute, buddyRoute` |
| `marstime.js` | Elif | Mars24: Sol, LMST/LTST, güneş açısı, gün doğumu/batımı, Dünya–Mars ışık gecikmesi | `MarsTime` |
| `data/` | ortak | Veri sözleşmesi (CLAUDE.md): `grid.json`, `layers.json` + `layers/*.png`, `regions.json`, `poi.geojson`, `stories.json`, `astronauts.json`, `conditions.json` | – |
| `tests/e8, e11, e13.html` | Elif | Algoritma testleri: tarayıcıda açılır, ✔/✘ basar. Sunum sayılarının kaynağı | – |

Formüller (Tobler, O₂ çarpanı, füzyon, bölgeler, dönüş noktası, arama alanı) `docs/PLAN.md` bölüm 5'te; katsayılar ve gerekçeleri her dosyanın başındaki "Varsayımlar" bloğunda.

## Çalıştırma

```
# Uygulama (yerel)
python -m http.server 8000 --directory web          → http://localhost:8000
# Algoritma testleri
python -m http.server 8765 --directory web          → http://localhost:8765/tests/e8.html (e11, e13)

# Veri hattı (ham veri indirildikten sonra)
venv\Scripts\python scripts\prep_layers.py
venv\Scripts\python scripts\build_regions.py
venv\Scripts\python scripts\pipeline_stats.py

# Sunum
venv\Scripts\python scripts\audit_numbers.py        # sayı denetimi (Edge ile testleri de çalıştırır)
venv\Scripts\python scripts\make_slides.py [--pdf]  # PPTX (+ LibreOffice ile PDF)
venv\Scripts\python scripts\make_video.py           # ~2,5 dk sessiz sunum videosu
```

**Yayın:** `.github/workflows/pages.yml`, `web/**` değişince `main`'e her push'ta siteyi GitHub Pages'e koyar. Cesium yayın sırasında yerel olarak kopyalanır. Canlı adres: https://tayancelifnur.github.io/marstrail/

## Git'e girmeyenler

`data/raw`, `data/processed`, `ml/dataset*`, `ml/runs`, `ml/weights`, `ml/models`, `*.tif`, `*.zip`, `*.pt`, `docs/sunum/onizleme`, `docs/sunum/img`. Bunlar betiklerle yeniden üretilir ya da indirilir (`docs/GOREV_KARTLARI.md` bölüm 2, D1–D8).
