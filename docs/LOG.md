# MarsTrail – Çalışma günlüğü

Her kartın sonunda: kart, saat, ne yapıldı, değişen dosyalar, nasıl çalıştırılır, varsayımlar.

## E1 · Repo ve sahte veri · Cmt 14 Kas 2026, bitiş 15:23 (commit 3145252)

- **Ne yapıldı:** Klasör yapısı, `.gitignore`, Python 3.12 venv + paketler; Gözde için veri sözleşmesine uygun sahte `web/data/` dosyaları.
- **Dosyalar:** `.gitignore`, `requirements.txt`, `scripts/make_dummies.py`, `web/data/*` (regions, poi, stories, layers + 5 PNG, grid, astronauts, conditions, photos/placeholder.jpg, README.md), `ml/.gitkeep`.
- **Çalıştır:** `py -3.12 -m venv venv` → `venv\Scripts\python -m pip install -r requirements.txt` → `venv\Scripts\python scripts\make_dummies.py`
- **Varsayımlar:** Çalışma alanı 77.36–77.51°D, 18.38–18.52°K; grid 256×256 (~32 m hücre). Arazi sentetik (taban −2600 m, delta tümseği, delta yamacı, 3 krater, Séítah benzeri sırtlar → %0,8 geçilmez, rota testi için). Maliyet PLAN.md §5 Tobler formülü (yük 0 kg). Nokta koordinatları ve Sol'ler yaklaşık; her kayıtta `"dummy": true`.
- **GPU (sonradan, E2 sırasında):** torch 2.11.0+cu128 kuruldu (`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`); RTX 5090 Laptop (sm_120) görünüyor, ultralytics CUDA:0 ile çalışıyor. requirements.txt'teki düz `torch` CPU sürümünü kurar, GPU için bu komut ayrıca çalıştırılmalı.

## E2 · Veri indirme · Cmt 14 Kas 2026 (D8 hâlâ iniyor)

- **Ne yapıldı:** `scripts/download_data.py` (devam edebilen indirme, %5 ilerleme, açılış kontrolü, rapor tablosu). D1–D6 indi ve açılıyor; D8 arka planda.
- **Çalıştır:** `venv\Scripts\python scripts\download_data.py D8` (arka planda, yarıda kalırsa aynı komut devam eder) · `... D1 D2 D3 D4` · `... D5 D6` · `... --report`
- **Sonuçlar:** D1 waypoints 708 · D2 traverse 559 · D3 Ingenuity 72 feature · D4 THEMIS 890×890, 100 m · D5 CTX DEM 4456×5067, 20 m, "Jezero_Crater_Projection" · D6 1304 poligon, 14 birim · D8 5,5 GB, iniyor.
- **D6 notu:** Zip shapefile değil, ArcGIS dosya veritabanı (`Nili.gdb`); birim katmanı `GeoUnits_v1`. Script onu `data/raw/D6_geology/Jezero_GeoUnits.shp` olarak yazıyor. Kaynakta iki hata var: "Crater riim unit" yazımı ve 5 numaralı birimdeki 1 "Upper etched" poligonu (E3'te birim adına göre düzeltilecek).
- **Dikkat (E3):** D4, D5 ve D6 üç farklı projeksiyonda (SimpleCylindrical, Jezero_Crater_Projection, MTM_clon77_5E). E3'te ortak bir sisteme getirilmeleri gerekiyor.
- **Açık:** Organizatör soruları (ham dosya kullanımı, sunum süresi, teslim içeriği) Elif'te.

## E3 · Katmanlar ve grid · Cmt 14 Kas 2026

- **Ne yapıldı:** `scripts/prep_layers.py`: D4 (THEMIS), D5 (CTX DEM) ve D6 (SIM 3464) aynı koordinat sistemine getirildi (Mars 2000 küresi, derece) ve çalışma alanına kırpıldı. E1'deki sahte `layers.json`, PNG'ler ve `grid.json` gerçekleriyle değişti.
- **Dosyalar:** `web/data/layers/{hillshade,slope,thermal,geology,traversability}.png` (1024², ~11 m/px), `layers.json`, `grid.json` (256², hücre 44 m); `data/processed/*.npz` (git dışı). Sahte `hazard_ml.png` silindi; gerçek YOLO katmanı E10'da gelecek.
- **Çalıştır:** `venv\Scripts\python scripts\prep_layers.py` (~10 sn)
- **Çalışma alanı:** 77.28–77.48°D, 18.365–18.555°K (~11×11 km). Üs, delta önü, Three Forks ve Cheyava Falls içeride (koordinatlar D1'den).
- **Formüller/varsayımlar:** Eğim 20 m DEM'de hesaplanıp ortalandı. Termal eylemsizlik alan içindeki %2–98 aralığıyla 0–1'e ölçeklendi. Skor = 0,4·eğim/25° + 0,25·kum + 0,15·kaya + 0,2·(1−termal). Kum = eolyen birim. Kaya = jeoloji birimi vekili (YOLO gelene kadar). Birim katsayıları takdirle seçildi. Geçilmez: eğim >25° ya da skor >0,8 (%0,3). Maliyet: Tobler ×0,6, yük 0.
- **Kontrol:** Krater kenarı, delta (Jezero fan), Belva krateri ve Neretva Vallis PNG'lerde net görünüyor. Grid'de üs → Three Forks 82 dk, delta önü 93 dk, Cheyava Falls 305 dk (tek yön). Perseverance yolunun (D2) %100'ü geçilebilir hücrelerde.

## E4 · Envanter · Cmt 14 Kas 2026

- **Ne yapıldı:** `docs/veri_envanteri.md`: D1–D8 için görev, alet, tarih, çözünürlük, projeksiyon, kaynak linki, üründeki rolü ve durumu; türetilen web/data dosyaları; 6 veri türü.
- **Kontrol:** D7 API'si test edildi (Sol 652 → Mastcam-Z görüntüleri ve 320/800/1200 px linkleri geliyor). D8 hâlâ iniyor.
