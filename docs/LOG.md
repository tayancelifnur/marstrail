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

## Organizatör cevapları · Cmt 14 Kas 2026

- **Ne yapıldı:**
  - CLAUDE.md'ye eklendi: veri hattı kuralı, sunum/teslim kuralları, NASA logosu/bayrağı/arması yasağı.
  - `docs/DATA_PIPELINE.md`: E1–E4 geriye dönük dolduruldu, özet tablo eklendi.
  - `scripts/pipeline_stats.py` ve `docs/figures/` (önce/sonra görselleri, istatistik JSON'u).
  - PLAN.md bölüm 7: 7 slayt, 5 dk, ≤30 sn video.
  - `docs/TESLIM.md` (form taslakları, kaynaklar, YZ beyanı, Drive listesi).
  - README UTF-8 olarak yeniden yazıldı, YZ notu eklendi.
- **Çalıştır:** `venv\Scripts\python scripts\pipeline_stats.py`. Bu komut DATA_PIPELINE sayılarını ve figürlerini yeniden üretir.

## E7 · Nokta kartları ve tarihçeler · Cmt 14 Kas 2026

- **Ne yapıldı:** `scripts/build_regions.py` ile sahte `regions.json`, `poi.geojson` ve `stories.json` gerçekleriyle değişti. 7 nokta, 1 kum tehlikesi pini, 3 hikâye, 10 gerçek Perseverance fotoğrafı (`web/data/photos/`).
- **Çalıştır:** `venv\Scripts\python scripts\build_regions.py` (~1 dk, D7 API'sine bağlanıyor)
- **Kurallar/varsayımlar:**
  - Konum: olay Sol'üne eşit ya da önceki son D1 kaydı. Ingenuity için D3 Uçuş 1.
  - Tehlikeler 300 m içindeki eğim, kum ve termal değerlerinden kuralla üretiliyor.
  - Fotoğraf: eleme hunisi (kamera, boyut, renkli/gri ikiz, direk açısı, kenar şiddeti ≥ 3,5) ve 1 kare insan kontrolüyle elendi.
  - Ayrıntı: DATA_PIPELINE.md E7.
- **Ek:** `regions.json`'a `terrain`, `position_source` ve `poi_type` alanları eklendi; sözleşmedeki alanlar aynı. Fotoğraflarda `credit`, `page`, `url_large`, `lmst` var. `make_dummies.py` artık gerçek dosyaların üzerine yazmıyor.
- **Kontrol:** Gözde'nin kartında tarih, olay ve fotoğraf görünmesi G5'te test edilecek. Veri tarafında 10 fotoğrafın hepsi gözle kontrol edildi.

## E2 ek · D8 indi · Cmt 14 Kas 2026

- D8 HiRISE zip'i (5,47 GB) indi ve açılıyor. Ortogörüntü ve güven haritası `data/raw/D8_hirise/` altına çıkarıldı (~20 sn).

## E5 · YOLO karoları (etiketleme Elif'te) · Cmt 14 Kas 2026

- **Ne yapıldı:** `scripts/tile_for_yolo.py`: çalışma alanı 640×640 karolara (160 m) bölündü. NoData (1444) ve dokusuz (58) karolar atıldı. Jeoloji birimine göre 70 kum, 65 kaya ve 15 negatif karo, en uzak nokta örneklemesiyle seçildi.
- **Çıktı:** `ml/roboflow_upload.zip` (150 PNG, 28 MB; git dışı), `ml/tiles_manifest.csv`, `ml/tiles_meta.json` (germe parametreleri E10 için), `ml/ETIKETLEME.md` (Roboflow adımları ve kurallar), figürler.
- **Çalıştır:** `venv\Scripts\python scripts\tile_for_yolo.py` (~16 sn)
- **Varsayımlar:** Kaya alt sınırı ~8 px (2 m). Normalizasyon %0,5–99,5 (60 → 0, 219 → 255), alan genelinde tek germe.
- **Dikkat (E10):** HiRISE mozaiği çalışma alanının sadece GB çeyreğini kapsıyor (~%23). Demo noktalarının hepsi kapsam dışında.
- **Kalan:** Etiketleme (en az 120 karo) → Roboflow'dan YOLOv8 dışa aktarımı → `ml/dataset/`.

## E8 · Mars saati ve O₂ bölgeleri · Cmt 14 Kas 2026

- **Ne yapıldı:**
  - `web/marstime.js`: Mars24; LMST, LTST, Perseverance Sol'ü, Ls, gün doğumu/batımı, gün batımına kalan Dünya dakikası. Kepler elemanlarıyla Dünya–Mars uzaklığı ve ışık gecikmesi.
  - `web/walkback.js`: grid üzerinde 8 komşulu Dijkstra (gidiş ve ters kenarlı dönüş). `zones()` yeşil/sarı/kırmızı sınıf, canvas ve sınır çizgileri döndürüyor. `path()` güvenli rota, `timeHome()` üsse dönüş süresi.
  - `web/tests/e8.html`: test sayfası.
- **Çalıştır:** `venv\Scripts\python -m http.server 8765 --directory web` → `http://localhost:8765/tests/e8.html`
- **Formüller:**
  - Kenar süresi = d / [6·exp(−3,5·|tanθ+0,05|)·0,6·(1−yük/100)] · (1 + 2·skor). Kenar eğimi > 25° ise geçilmez.
  - O₂ çarpanı = 1 + (nabız − 90)/100. Kullanılabilir süre = O₂ / çarpan.
  - Yeşil: gidiş + dönüş ≤ kullanılabilir/1,25. Sarı: ≤ kullanılabilir.
  - `grid.json`'a `score` eklendi.
- **Kontrol (Edge headless):**
  - D7 kaydı Sol 652 13:10:16 (gerçek 13:10:20). Ingenuity Uçuş 1 LMST 12:33 ✔. 2025-01-12 uzaklığı 0,642 AU ✔.
  - Üs → Three Forks 79 dk, dönüş 75 dk.
  - Nabız 150'de yeşil alan 73 → 35 km². Hesap 14–31 ms.

## G1 · Mars küresi · Cmt 14 Kas 2026, bitiş 14:58 (commit 67b8106)

- **Ne yapıldı:** CesiumJS 1.123 (CDN) ile Mars elipsoidi (IAU 2000: 3396,19 / 3376,20 km), Mars Trek WMTS taban katmanı (Viking renkli mozaik / MOLA renkli gölgeli kabartma, seçilebilir), otomatik dönüş (tutunca/zoom yapınca durur).
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Çalıştır:** `python -m http.server 8000 --directory web` → `http://localhost:8000`
- **Varsayımlar:** Cesium ion token'ı alınmadı; ion görüntüsü/arazisi kullanılmadığı için gerekmiyor. Mars Trek küresel karoları seviye 0'da 2×1, en yüksek seviye 7 (denendi).

## G2 · Jezero uçuşu + katman menüsü · Cmt 14 Kas 2026, bitiş 15:38 (commit 8761652)

- **Ne yapıldı:** "Jezero'ya git" butonu (`flyTo`), `layers.json`'daki PNG'ler bbox ile haritada; her katman için aç/kapa, opaklık kaydırıcısı, lejant ve kaynak satırı.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Not:** Katmanlar `layers.json`'dan okunuyor; E3'te gerçek katmanlar gelince kod değişmeden çalıştı.

## G3 · Arayüz iskeleti + üst bar · Cmt 14 Kas 2026, bitiş 15:42 (commit a848e92)

- **Ne yapıldı:** Üst bar (Jezero saati, Sol, UTC, TR saati, Dünya gecikmesi, gün batımına kalan, hava, habitat ağı). Sol panel (astronotlar, harita, katmanlar), sağ detay kartı, koyu tema + turuncu vurgu, 768 px altında alttan açılan çekmece.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Varsayımlar:** Hava `conditions.json`'dan, senaryo Sol'üne göre. Mars saati ilk sürümde sabitti; E8 gelince bağlandı (aşağıda).

## G-ek · Jezero netliği ve görsel iyileştirme · Cmt 14 Kas 2026, 16:02 ve 16:55 (commit 4705b47, 52fbb8a)

- **Ne yapıldı:**
  - Küresel mozaik Jezero'da ~300 m/piksel kalıyordu. Mars Trek'in bölgesel mozaikleri eklendi: CTX 6 m (seviye ≤13) ve HiRISE 25 cm (seviye 15–17; yamalı göründüğü için sadece yakında).
  - "Küreye dön" butonu.
  - Jezero 3B: `grid.json` yükseklikleri `CustomHeightmapTerrainProvider` ile arazi oldu. Kenar ortalamasına göre göreli, kenarın %8'inde sıfıra yumuşatma, 3× dikey abartı.
  - Güneş ışığı (Jezero'ya göre azimut 315°, yükseklik 30°; hillshade ile aynı yön), ton kaydırılmış Mars atmosferi, siyah-beyaz CTX üstüne %38 turuncu örtü.
  - Jezero'ya 45° eğik uçuş; dikey ekranda 72°.
- **Dosyalar:** `web/index.html`, `web/app.js`
- **Varsayımlar:** Abartı, güneş yönü, örtü rengi ve atmosfer tonu sunum için göz kararı; bilimsel değer değil. Çalışma alanı dışı düz (küresel yükseklik verisi yok).

## G4 · Astronot profili · Cmt 14 Kas 2026, bitiş 17:12 (commit 5b8511b)

- **Ne yapıldı:** Astronot kartına tıklayınca form: ad, kilo, giysi, O₂, batarya, su, nabız, yük, radyasyon. "Güncelle" localStorage'a (`marstrail.astronauts.v1`) kaydediyor, "Varsayılana dön" `astronauts.json`'a döndürüyor. Kartta O₂ çubuğu ve bölge etiketi yeri. Değişince `marstrail:astronaut` olayı yayılıyor (G6 bölgeleri bunu dinleyecek).
- **Dosyalar:** `web/app.js`, `web/style.css`
- **Uyarı eşikleri (varsayım):** O₂ < kapasitenin %25'i (yeşil bölge payı), nabız ≥ 150 (Apollo 14), batarya/su < %20, yük > 30 kg (Tobler'de hız %30'dan fazla düşer), radyasyon > 1 mSv (~1,5 sol; RAD ~0,64 mSv/gün).
- **Kontrol:** Headless Chrome'da değerler değiştirildi, sayfa yenilendi, değerler duruyor.

## G-ek · Eksikler · Cmt 14 Kas 2026, 17:25

- **Ne yapıldı:**
  - Üst bar E8'e bağlandı: `marstime.js` ile gerçek Jezero LMST, Dünya–Mars gecikmesi ve gün batımına kalan süre. Sol, senaryo Sol'ü (sayfa açılışında 34, `MarsTime.scenario`); Perseverance'ın gerçek Sol'ü ipucu olarak.
  - Mobil düzeltme: detay kartı üst barın altına kayıyordu, artık alttan açılıyor.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Kontrol:** 390×844 telefon görünümünde çekmece aç/kapa, astronot formu ve Jezero uçuşu ekran görüntüsüyle denendi. Gerçek telefonda henüz denenmedi.

## Önizlemeler · Cmt 14 Kas 2026

- **Ne yapıldı:** `scripts/make_previews.py` → `docs/figures/onizleme/d1.png … d8.png`. Her veri seti için ham ve işlenmiş hal yan yana. `docs/veri_envanteri.md`'ye eklendi.
- **Düzeltme:** D2 rover hücre sayısı 675 değil, 679. E3'teki hızlı kontrolde yuvarlama hatası vardı; walkback.js ile aynı `floor` yöntemiyle 679. DATA_PIPELINE güncellendi.

## G6 (1. kısım) · O₂ bölgeleri her zaman açık · Cmt 14 Kas 2026, 17:45

- **Ne yapıldı:** Elif'in `walkback.js`'i (E8) arayüze bağlandı. Seçili astronotun yeşil/sarı/kırmızı bölgeleri haritada dolgu + araziye yapışık sınır çizgisi olarak her zaman çiziliyor; astronot simgesi ve adı haritada. Her iki astronotun kart etiketi (YEŞİL/SARI/KIRMIZI) ve formda "Şu an … bölgedesin" yazısı gerçek hesaptan. Sol panelde lejant + kullanılabilir O₂, üsse dönüş süresi, yeşil/sarı alan (km²). Profil "Güncelle" ile bölgeler anında yeniden hesaplanıyor.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Varsayımlar:** Bölge dolgusu %40 saydam. `grid.json` terrain için bir kez indiriliyor, Walkback'e aynı nesne veriliyor.
- **Kontrol (headless Chrome):** O₂ 480 dk, nabız 85 → yeşil 73,2 km², hesap ~45 ms. O₂ 84 dk, nabız 120 → kullanılabilir 65 dk (×1,30), yeşil 2,4 km², sarı 1,3 km².
- **Kalan (G6 2. kısım):** Planlayıcı paneli, dönüş noktası, Go/No-Go (E11 bekleniyor).
