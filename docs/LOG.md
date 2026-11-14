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

## G5 · Nokta kartları + rota çizme · Cmt 14 Kas 2026, 18:10

- **Ne yapıldı:**
  - `poi.geojson`'daki 8 nokta haritada renkli pin (habitat turuncu, bilim mavi, tehlike kırmızı, tarihi mor); küreden bakınca gizli, Jezero'da görünür. Yakın pinlerin etiketleri elle ayrıldı.
  - Pine tıklayınca kart: tür, bilim değeri (yıldız), özet, "Perseverance buraya Sol X'te geldi", o Sol'ün fotoğrafı (Navcam / Mastcam-Z sekmeli, kaynak linki), tarihçe zaman çizgisi, arazi (yükseklik, eğim, kum, jeoloji, geçilebilirlik), tehlikeler, görevler.
  - Kum alanı pini Opportunity ve Spirit hikâye kartlarını açıyor. Sol panelde "Tarihi olaylar": Apollo 14, Opportunity, Spirit.
  - "Rota çiz": tıkla nokta ekle, çift tıkla / Bitir ile tamamla, Esc / İptal. Harita üstünde yüzen Bitir/İptal (mobilde çekmece kapalıyken).
  - Rota kartı: mesafe, tek yön süre, O₂ ihtiyacı (nabız çarpanıyla), tırmanış/iniş, rotanın sonunun seçili astronot için bölgesi, Chart.js yükseklik profili (imleçli). Profil güncellenince kart yeniden hesaplanıyor.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Formüller:** Süre = Σ mesafe / [6·exp(−3,5·|tanθ+0,05|)·0,6·(1−yük/100)], 25 m adımla, yükseklik `grid.json`'dan. O₂ ihtiyacı = süre × (1 + (nabız−90)/100). Rota düz çizgi; güvenli rota (Dijkstra) planlayıcıda.
- **Kontrol (headless Chrome, gerçek fare tıklamaları):** 4 noktalı rota çift tıklamayla bitti: 8,86 km, 218 dk, +370/−95 m, sonu KIRMIZI bölgede. Delta önü kartında Sol 415 fotoğrafı ve tarihçe görünüyor.

## Çalışma alanı v2 · Cmt 14 Kas 2026

- **Ne yapıldı:** Alan 77,28–77,48°D → **77,28–77,60°D**, 18,293–18,597°K (enlem üsse ortalı, ~18 × 18 km). Grid hücresi 44 → 70,4 m. E3, E7, istatistikler, önizlemeler ve e8_zones.png yeniden üretildi; DATA_PIPELINE, PLAN ve envanterdeki sayılar güncellendi.
- **Neden:** O₂ tam doluyken (480 dk, nabız 85) yeşil bölge doğu kenarında kesiliyordu. Ara deneme 77,56° yetmedi (doğu kenarında 64 yeşil hücre). 77,60'ta test geçiyor: 0 hücre.
- **Korunan:** E5 karolama alanı `tile_for_yolo.TILE_BBOX` ile ilk alanda sabit (ızgara başlangıcı doğrulandı: aynı). Etiketlenen karolar geçerli. Fotoğraf seçimi değişmedi.
- **Yeni sayılar:**
  - Geçilmez hücre 150 (%0,2). Rover yolu 397 hücre, %100 geçilebilir.
  - Üsten süreler (yük 0): Three Forks 73 dk, delta önü 75 dk, Cheyava Falls 278 dk.
  - Yeşil alan: nabız 85'te 130 km², nabız 150'de 47 km².

## E11 · EVA planlayıcı · Cmt 14 Kas 2026

- **Ne yapıldı:** `web/eva.js`:
  - `Eva.plan()`: duraklar ve kalma süreleri → bacak bacak rota (dönüş ayrı; yönlü eğim, numune yükü, yorgunluk), zaman çizelgesi (UTC + LMST + kalan O₂), dönüş noktası, %25 pay noktası ve Go/No-Go listesi.
  - Go/No-Go maddeleri: O₂, gün batımı, kum, eğim, telsiz görüş hattı, batarya, su.
  - `Eva.positionAt()`: canlı yürüyüş (G7) için. `Eva.nextWindow()`: Jezero'da LTST 09:00 çıkış penceresi.
  - `grid.json`'a `sand` eklendi. Test sayfası: `web/tests/e11.html`.
- **Varsayımlar (kodda gerekçeli):**
  - Yorgunluk: saat başına %5 yavaşlama. Durak başına 1 kg numune.
  - Batarya ve su: %12,5/sa. Alt sınırlar: batarya %20, su %10.
  - Gün batımı payı 30 dk.
  - Telsiz: anten 10 m, giysi 2 m, eğrilik düzeltmeli görüş hattı.
  - Dönüş noktası = harcanan + üsse dönüş > kalan O₂ olan ilk nokta (PLAN §5).
- **Kontrol:**
  - Üs → Delta önü (40 dk) → Three Forks (30 dk) → Üs: 5,52 km, 243 dk, dönüşte 249 dk O₂ (%52) → GO. Telsiz uyarısı: ~126 dk görüş yok.
  - Nabız 150 + O₂ 220: dönüş noktası T+67 dk → NO-GO.
  - Akşam çıkışı: gün batımı NO-GO.
  - Plan 67 ms'de çıkıyor. Görsel: `docs/figures/e11_plan.png`.

## E13 · Hayatta Kal (kayıp astronot) · Cmt 14 Kas 2026

- **Ne yapıldı:** `web/rescue.js`:
  - `Rescue.respond()` "Telsiz koptu" için hepsi bir arada.
  - `searchArea()`: son konumdan bütçe içinde ulaşılabilir hücreler, olasılık ∝ 1/(1+süre), plan rotasına yakınsa ×2; en olası %50 ve %90 alanları, ısı haritası canvas'ı.
  - `droneRoute()`: alanın uzun ekseni boyunca biçerdöver zikzak, şeritler %90 alanına kırpılı, %50/%90 tarama süreleri.
  - `buddyRoute()`: Ali'nin gidiş ve birlikte dönüş rotası, iki astronotun O₂ hesabı.
  - `walkback.js`'e `travelTimes()` ve `outlineMask()` eklendi. Test sayfası: `web/tests/e13.html`.
- **Varsayımlar (kodda gerekçeli):**
  - Bütçe = min(geçen süre, O₂/çarpan).
  - İHA: 100 m irtifa, 60° görüş → 115 m şerit, %20 örtüşme → 92 m aralık, 10 m/s, 20 dk batarya.
  - Ali: 10 dk giyinme, birlikte dönüş %20 yavaş, 60 dk yedek O₂ tüpü.
- **Kontrol (demo planı, çıkıştan 60 dk sonra kopma, nabız 150, 20 dk geçmiş):**
  - Alan 1,07 km² (%50 → 0,25 km², %90 → 0,79 km²). Geçen süreye göre büyüyor: 5 dk 0,07 → 40 dk 4,43 km².
  - İHA: 11 şerit, 14,5 km, 24 dk (2 batarya); olasılığın %50'si 11,6 dk'da, %90'ı 21,6 dk'da taranıyor.
  - Ali: 60 dk gidiş + 69 dk dönüş, O₂ 116/480 → YEŞİL; Ayşe üste 168 dk O₂ ile varıyor.
  - Zor durum (90 dk geç fark, O₂ 120): Ali varmadan O₂ bitiyor → "kurtarma mümkün değil".
  - Hesap 19 ms. Görsel: `docs/figures/e13_rescue.png`.

## G-ek · Çalışma alanı v2 kontrolü · Cmt 14 Kas 2026, 18:50

- **Ne yapıldı:** Elif'in genişlettiği alan (77.28–77.60°D) arayüzde denendi: arazi, katmanlar ve O₂ bölgeleri yeni `grid.json`/`layers.json`'dan kod değişmeden geldi; bölgeler artık kenarda kesilmiyor. Alan büyüyünce pinler ekranda sıkıştı; Ayşe adı sağa, Delta önü ve Kum alanı etiketleri sola alındı.
- **Dosyalar:** `web/app.js`
- **Kontrol:** Headless Chrome 1440×900, Jezero uçuşu sonrası ekran görüntüsü; etiketler çakışmıyor.

## G6 (2. kısım) · EVA planlayıcı arayüzü · Cmt 14 Kas 2026, 19:10

- **Ne yapıldı:** Elif'in `eva.js`'i (E11) arayüze bağlandı. Sol panelde "EVA planı": durak listesi (kalma süresi, sıra değiştir, çıkar), "Durak ekle" seçimi, çıkış saati (sonraki güvenli pencere 09:00 LTST / şimdi), Planla / Planı sil, kısa GO/NO-GO özeti. Nokta kartlarında "Plana ekle".
  - Haritada gidiş mavi, dönüş beyaz kesikli (Dijkstra rotası), durak numaraları, dönüş noktası (kırmızı), %25 pay sınırı (sarı), telsiz gölgesinin başladığı yer (mor). Planla'ya basınca kamera rotaya yaklaşıyor (telefonda rota kartın üstünde kalacak şekilde).
  - Plan kartı: büyük GO/NO-GO, çıkış/dönüş (LMST + UTC), süre, mesafe, O₂ (yetmezse "X dk EKSİK"), batarya/su, Go/No-Go listesi, O₂ çubuklu zaman çizelgesi, bacaklar (yük, yorgunluk), formül notu.
  - Profil, seçili astronot, durak ya da çıkış saati değişince plan anında yeniden hesaplanıyor. `marstrail:plan` olayı ve `MarsTrail.plan` G7 (canlı yürüyüş) için.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Varsayımlar:** Demo planı hazır yüklü (Delta önü 40 dk, Three Forks 30 dk). Yeni durak 30 dk. Kamera uzaklığı rota yarıçapı × 4,2 (en az 3 km), telefonda bakış noktası 0,45 × uzaklık güneye kaydırılıyor (göz kararı).
- **Kontrol (headless Chrome):** Demo planı 5,52 km, 243 dk, dönüşte 249 dk O₂ → GO, telsiz DİKKAT (E11 testiyle aynı). O₂ 220 + nabız 150 → dönüş noktası T+67 dk, pay sınırı T+51 dk, NO-GO. Rochette kartından "Plana ekle" → 3 durak, 307 dk, GO. 390×844 telefon görünümü denendi.

## G7 · Canlı yürüyüş · Cmt 14 Kas 2026, 19:40

- **Ne yapıldı:** "▶ Yürüyüşü başlat" (sol panel ve plan kartı). Plan zaman ekseninde oynuyor: astronot simgesi `Eva.positionAt()` ile rota boyunca ilerliyor (×60 / ×300 / ×900), etiketinde canlı O₂.
  - Yürüyüş paneli: T+ ve LMST, ne yaptığı (yürüyor / durakta), büyük O₂ sayacı + çubuk, "üsse dönüş X dk O₂ · pay Y dk", bölge etiketi, nabız kaydırıcısı (60–180), not/fotoğraf pini, Duraklat, Üsse dön, Bitir. Telefonda altta.
  - Bölgeler her 5 sim. dakikada o anki konum, kalan O₂ ve nabızla yeniden çiziliyor (nabız artınca daralma hızlanıyor). Eski çizim 1,5 sn tutuluyor, titreme yok.
  - Uyarılar: kum alanına yaklaşma/giriş, dönüş noktasına 5 dk, dönüş noktası, sarı/kırmızı bölgeye giriş, O₂ %25 altı, telsiz gölgesi (üst bar "kopuk" olur), durak varış/ayrılış.
  - "Üsse dön": bulunduğu yerden yeni Dijkstra dönüş rotası (sarı kesikli), kalan O₂ ile.
  - Bitişte özet kartı: GÜVENDE / ACİL, süre, yürünen mesafe, O₂ başlangıç → bitiş, ort./en yüksek nabız, pinler, olay kaydı, Tekrar oynat.
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Formül:** O₂(t+dt) = O₂(t) − dt × (1 + (nabız−90)/100), canlı nabızla. Konum plan hızında (nabız tüketimi değiştirir, hızı değil). Bölge: üsse dönüş × yorgunluk ≤ O₂/çarpan/1,25 yeşil, ≤ O₂/çarpan sarı, değilse kırmızı. Yürüyüş simülasyon: profil kaydedilmez, bitince eski değerler geri gelir.
- **Kontrol (headless Chrome):** Demo planı ×900 baştan sona: 245 dk, dönüşte 247 dk O₂ (plan 249) → "Yürüyüş tamamlandı". O₂ 220 + nabız 150: T+23 telsiz koptu, T+63 dönüş noktasına 5 dk + sarı bölge, T+67 dönüş noktası, T+71 kırmızı bölge; T+75 "Üsse dön" geç kaldı → T+140 "O₂ BİTTİ / ACİL". 390×844 telefon görünümü denendi.

## G8 · Hayatta Kal paneli · Cmt 14 Kas 2026, 20:05

- **Ne yapıldı:** Elif'in `rescue.js`'i (E13) arayüze bağlandı. "📡 Telsiz koptu" butonu: yürüyüş paneli (son konum, O₂, nabız, yük canlı yürüyüşten) ve sol panel (demo: plan T+60, nabız 150). O₂ biterse yürüyüş özetinde "Hayatta Kal" butonu.
  - Haritada olasılık ısı haritası, en olası %50 (kırmızı) ve %90 (turuncu) alan sınırları, son konum, İHA zikzak rotası, Ali'nin gidiş (düz) ve birlikte dönüş (kesikli) rotası. Acil durumda O₂ bölgeleri gizli, üst bar kırmızı, "Habitat ağı: kopuk".
  - Acil durum kartı: KURTARILABİLİR / MÜMKÜN DEĞİL, "geç fark etme" kaydırıcısı (0–120 dk, alan canlı büyür), arama alanı, İHA şerit/süre/%50–%90, Chart.js kapsama eğrisi, Ali'nin O₂ kontrolü ve mesajları.
  - "▶ Aramayı oynat": İHA ve Ali haritada hareket ediyor; arama süresi, Ayşe'nin akan O₂'si, İHA'nın taradığı olasılık; uyarılar (%50/%90 tarandı, Ali çıktı/ulaştı, yedek tüp, O₂ bitti, üste varış).
- **Dosyalar:** `web/index.html`, `web/app.js`, `web/style.css`
- **Varsayımlar:** İHA hemen kalkar, 10 m/s sabit hız; Ali 10 dk hazırlanır, rota boyunca eşit hızda yürür (animasyon için). Kayıp astronotun O₂'si = kopmadaki − (geçen + arama süresi) × çarpan.
- **Kontrol (headless Chrome):** Demo: alan 1,07 km² (%50 0,25, %90 0,79), İHA 11 şerit 24,2 dk, %50 11,6 dk, %90 21,6 dk; Ali 116/480 YEŞİL, Ayşe üste 168 dk ile → KURTARILABİLİR (E13 testiyle aynı). Hesap 47 ms. Yürüyüşte T+46'da kopma → alan ve rotalar o konumdan.

## G-ek · Harita yazılarının netliği · Cmt 14 Kas 2026, 20:30

- **Sorun:** Windows %125–150 ekran ölçeğinde harita yazıları bulanık ve tırtıklı; kalın siyah kenarlı uzun adlar birbirine giriyordu (Gözde'nin ekran görüntüsü).
- **Ne yapıldı:** Cesium artık ekranın gerçek pikselinde çiziyor (`useBrowserRecommendedResolution = false`, DPI > 2'de en fazla 2×). Bütün harita etiketleri (pinler, astronot, plan işaretleri, yürüyüş, İHA/Ali) koyu yarı saydam zeminli düz yazı (`LABEL_BG`). Haritada kısa adlar (Üs, Three Forks, Rochette, Jezero Krateri…), tam adlar kartta. Üs etiketi solda; plan işaretlerinin etiketleri noktanın altında; durak numaraları kaldırıldı (sıra sol panelde).
- **Dosyalar:** `web/app.js`
- **Kontrol:** Headless Chrome, cihaz ölçeği 1,5 (1280×720 → 1920×1080): genel görünüm ve NO-GO plan görünümünde yazılar net, çakışma yok.

## G9 (1. kısım) · Yayın hazırlığı: PWA + GitHub Pages · Cmt 14 Kas 2026, 21:50

- **Ne yapıldı:** `manifest.webmanifest` (ad, tam ekran/standalone, koyu tema, ikonlar) ve ikon seti (192/512, maskable, apple-touch, favicon; Pillow ile çizildi: Mars diski + kesikli yürüyüş izi, NASA logosu yok). index.html'e manifest/ikon/mobil meta etiketleri. `.github/workflows/pages.yml`: main'e her `web/**` push'unda `web/` klasörü GitHub Pages'e yayınlanır.
- **Dosyalar:** `web/index.html`, `web/manifest.webmanifest`, `web/icons/*`, `.github/workflows/pages.yml`
- **Nasıl çalıştırılır:** Bir kez repo Settings → Pages → Source: "GitHub Actions". Sonra adres: https://tayancelifnur.github.io/marstrail/ (Actions sekmesinde "Pages" iş akışı yeşil olmalı).
- **Varsayımlar:** Service worker yok (çevrimdışı çalışma hedef değil; Cesium zaten CDN'den yükleniyor, eski önbellek demo sırasında sorun çıkarmasın diye). Tüm yollar göreli, alt dizinde çalışır.
- **Kontrol:** Manifest geçerli JSON; yerel sunucuda index, manifest ve ikonlar 200. Telefon testi yayın açılınca yapılacak.

## G9 (2. kısım) · Telefon testi ve düzeltmeler · Cmt 14 Kas 2026, 22:10

- **Ne yapıldı:** Demo akışı 390×844 (telefon, dikey) ekranda baştan sona denendi: çekmece → Planla → Yürüyüşü başlat → Telsiz koptu → Aramayı oynat. Bulunan sorunlar düzeltildi:
  - Dikey ekranda kamera alanı kartın üstüne yerleştiriyor ve 1,4× uzaklaşıyor (`flyToFit`, plan ve acil durum ortak). Önceden acil durumda arama alanı kartın arkasında kalıyordu, soldaki durak adları kesiliyordu.
  - Yürüyüş paneli telefonda kapalı çekmecenin üstünde duruyor (çekmece kenarı altından taşıyordu).
  - Yürüyen astronotun etiketi noktanın üstünde ("Üs" ile çakışıyordu). İHA etiketi üstte, Ali altta. Acil durumda plan etiketleri gizli (Son konum ile çakışıyordu), kapatınca geri gelir.
  - Masaüstü acil durum kartında kaydırıcı küçülebiliyor, yatay kaydırma çubuğu çıkmıyor.
- **Dosyalar:** `web/app.js`, `web/style.css`
- **Kontrol:** Headless Chrome 390×844 (DPR 2) ve 1440×900: dört ekran temiz; acil durum kapat/aç tekrar çalışıyor; demo değerleri E13 ile aynı (İHA %50 11,6 dk, %90 21,6 dk).

## G-ek · Demo'yu sıfırla + harita çizim hatasından toparlanma · Cmt 14 Kas 2026, 22:30

- **Ne yapıldı:** Sol panelin sonuna "Demo" bölümü ve "↺ Demo'yu sıfırla" düğmesi: kayıtlı profilleri siler (localStorage), astronotları astronauts.json değerlerine, planı Delta önü 40 + Three Forks 30'a döndürür; yürüyüşü, acil durumu, rotayı ve pinleri temizler, Jezero'ya uçar.
- Cesium çizim hatası (CDN'den worker dosyası yüklenemeyince çizim duruyordu): hata paneli kapanır, 1,5 sn sonra çizim yeniden başlar; 3 denemede düzelmezse "Sayfayı yenile" mesajı. 60 sn hatasız geçerse sayaç sıfırlanır.
- **Dosyalar:** `web/index.html`, `web/app.js`
- **Kontrol:** Plan + yürüyüş + telsiz koptu sonrası sıfırla → yürüyüş/acil durum/plan kapalı, duraklar varsayılan, kayıt silinmiş. Yapay hata: tek hata → çizim kendiliğinden devam; sürekli hata → 3 denemeden sonra yenile mesajı.

## E6 (1. kısım) · YOLOv8m eğitimi, 1. deneme · Cmt 14 Kas 2026, 22:17

- **Ne yapıldı:** Roboflow v1-150karo dışa aktarımı ölçüldü (`ml/dataset_stats.py`): 120 train / 30 valid, kutular: kaya 255, kaya_alani 82, kum_dalgasi 237; geçersiz satır 0. `ml/train.py`: data.yaml'ın mutlak yollu temiz kopyası, YOLOv8m 640 px, 100 epoch, patience 20, batch 16, seed 0, gri görüntüye uygun artırma. Etiket tanımı ve sınırlamalar ETIKETLEME.md ve DATA_PIPELINE.md'ye, Roboflow Auto Label YZ beyanına yazıldı.
- **Sonuç (v1):** mAP50 0,162 (kaya 0,169 · kaya_alani 0,027 · kum_dalgasi 0,292), 81 epoch, en iyi epoch 61. Eğitim epoch 3'te ıraksadı (cls_loss 4 → 17, val kaybı epoch 3–15 NaN). Confusion matrix 0,001 güven eşiğiyle çizildiği için iyimser; 0,25 eşiğinde val görselinde tahmin yok. Ayrıntı DATA_PIPELINE.md E6.
- **Dosyalar:** `ml/train.py`, `ml/dataset_stats.py`, `ml/ETIKETLEME.md`, `docs/DATA_PIPELINE.md`, `docs/TESLIM.md`, `.gitignore`, `docs/figures/e6_dataset*`, `docs/figures/e6v1_*`
- **Nasıl çalıştırılır:** `venv\Scripts\python ml\dataset_stats.py` ve `venv\Scripts\python ml\train.py` (teşhis: `--epochs 8 --patience 100 --diag --name <ad>` ile `--no-amp` / `--optimizer SGD`)
- **Varsayımlar:** Ölçek artırması ±%25 (sınıflar fiziksel boyuta bağlı), döndürme yok, renk artırması yok. v1 modeli E10'da kullanılmayacak; ıraksamanın nedeni bulunup v2 eğitilecek.

## G-ek · Etiketlerin dağılması, yayında Cesium yerel kopya, slayt görüntüleri · Cmt 14 Kas 2026, 22:45

- **Sorun:** Bazı harita yazıları parçalanıyordu ("A … yşe", "Tel … siz g"). Neden: CLAMP_TO_GROUND etiketlerde Cesium her harfi ayrı ayrı araziye oturtuyor; karolar yüklenip netleşirken harfler farklı yüksekliklere düşüyor. Pinlerin arazi yüklenene kadar kayması da aynı nedenden.
- **Ne yapıldı:** Pin, astronot, plan işaretleri, yürüyen astronot, İHA ve Ali artık araziyi üreten aynı örnekleyiciden (`makeTerrainSampler`, grid.json) yükseklik × 3 abartı ile konumlanıyor (`groundPosition`/`groundCart`); CLAMP_TO_GROUND kalmadı. Cesium 1.127 ve 1.135 denendi: 1.135'te clamp değişikliği pinleri rotadan kaydırıyor, etiket sorunu iki sürümde de var → 1.123'te kalındı.
- Pages iş akışı Cesium'u npm'den indirip `web/cesium/` altına kopyalıyor, index.html'deki CDN yolu yayında yerel yola çevriliyor (git'e girmiyor). Yerel ağda npm/CDN ara sıra kopuyor (ECONNRESET); yayın jsdelivr'e bağlı kalmasın diye.
- Slayt görüntüleri: `docs/figures/ui_1_plan_go.png`, `ui_2_plan_nogo.png`, `ui_3_walk.png`, `ui_4_rescue.png` (1920×1080), `ui_5_phone_plan.png`, `ui_6_phone_rescue.png` (390×844, 2×).
- **Dosyalar:** `web/app.js`, `web/index.html`, `.github/workflows/pages.yml`, `docs/figures/ui_*.png`
- **Kontrol:** Headless Chrome NO-GO plan (2 kez), yürüyüş → telsiz koptu → arama animasyonu, telefon yürüyüşü: etiketler bütün, pinler rotayla örtüşüyor.

## E6 · Ablation ve model seçimi · Cmt 14 Kas 2026, 22:48

- **Ne yapıldı:**
  - v1 ıraksamasına karşı kararlı ayar: SGD lr0 0,01, fp32 ve her epoch NaN kontrolü.
  - 5 koşuluk ablation: 0) m/3 sınıf, A) s/3, B) m/2 (kaya_alani → kaya), C) s/2, D) yolov8s-cls ile 600 alt karoda (80 m) kum/kayalık/düz sınıflandırma. D'de bölme karo bazında.
  - Adil karşılaştırma (`ml/eval_merged.py`): hepsi aynı 2 sınıflı görevde, ayrıca D ile aynı 120 alt karoda hücre düzeyinde ölçüldü.
  - Seçilen model C (`e6_s2`) → `ml/models/yolo_marstrail.pt`.
  - Ek etiketleme için 100 karo hazırlandı (`ml/roboflow_upload_2.zip`).
- **Sonuç:**
  - Kararlı ayar tek başına mAP50'yi 0,162'den 0,273'e çıkardı.
  - Adil karşılaştırmada dört tespit modeli 0,311–0,327 aralığında (gürültü düzeyi).
  - C: mAP50 0,327, kum 0,518; hücre doğruluğu 0,808, dengeli doğruluğu 0,657 (en iyisi). Taban çizgisi 0,592.
  - D: 0,800 / 0,643, tespiti geçemedi. Kayalık hücre recall'u en fazla 0,36: darboğaz veri.
- **Dosyalar:** `ml/train.py`, `ml/train_cls.py`, `ml/make_cls_dataset.py`, `ml/eval_merged.py`, `ml/compare_runs.py`, `scripts/tile_batch2.py`, `ml/ETIKETLEME.md`, `docs/DATA_PIPELINE.md`, `docs/figures/e6_*`, `ml/tiles_manifest_2.csv`
- **Nasıl çalıştırılır:** `ml\train.py --name e6_s2 --classes2 --model yolov8s.pt`, ardından `ml\eval_merged.py` ve `ml\compare_runs.py --select e6_s2`
- **Varsayımlar:**
  - Hücre sınıfı eşikleri: kum kaplaması ≥ 0,5; kaya_alani ≥ 0,1 ya da ≥ 2 kaya.
  - 2 sınıflı modelde kenarı ≥ 10 m olan kaya kutusu kaya_alani sayıldı (kaya p90 9,4 m, kaya_alani p10 10,8 m).
  - Güven eşiği 0,25, val'e göre ayarlanmadı.
  - Eşitlikte küçük model seçildi.

## G1 (gözden geçirme) · Gerçek Mars Güneşi + zoom sınırları · Cmt 14 Kas 2026, 23:05

- **Eleştiri:** Güneş Jezero'da sabit KB/30° idi; küredeki gece-gündüz çizgisi üst bardaki LMST ile uyuşmuyordu. Zoom sınırı yoktu (tekerlek kazara Mars'ı nokta yapıyor ya da kamerayı araziye indiriyordu). Cesium'un kendi Güneş diski Dünya'ya göre çiziliyordu (yanlış yönde).
- **Ne yapıldı:** Işık yönü = Güneş altı noktanın tersi; enlem = δs, boylam = Jezero − (LTST − 12) × 15° (marstime.js, Mars24). 30 sn'de bir güncelleniyor. marstime.js yoksa eski KB/30° yedek. Cesium Güneş/Ay diskleri gizli. Zoom: en yakın 100 m, en uzak 30.000 km.
- **Dosyalar:** `web/app.js`, `web/index.html` (script yorumları düzeltildi)
- **Kontrol:** Jezero'da Güneş yüksekliği uygulamadan 67,04°, formülden (sin h = sin φ sin δ + cos φ cos δ cos H) 67,02°; isDay ile tutarlı. LTST 13:28 → Güneş altı boylam 55,2°D (Jezero'nun 22° batısı). Fare tekerleğiyle: dışarı 30.000 km'de, içeri 100 m'de duruyor.

## E10 · YOLO çıkarımı, füzyon ve D2 doğrulaması · Cmt 14 Kas 2026, 23:03

- **Ne yapıldı:**
  - `ml/infer.py`: E5 ızgarasındaki 1146 karoya çıkarım (1088 temiz + 58 dokusuz, 17 sn). 70 m hücre başına kum_ml ve kaya_ml yoğunlukları; 150 etiketli karoda etiket denetimi.
  - `prep_layers.py`: HiRISE kapsamında kum ve kaya terimleri jeoloji ile YOLO'nun ortalaması. Yeni `hazard_ml.png`; `traversability.png`, `grid.json` ve `layers.json` güncellendi.
  - `scripts/validate.py`: Perseverance rotasıyla (D2) önce/sonra karşılaştırması.
- **Sonuç:**
  - HiRISE kapsamında rota/rota dışı AUC 0,498 → 0,626 (fark %95 [+0,099, +0,156]).
  - Rover, YOLO'nun kum dediği hücreleri belirgin biçimde az kullanmış: rotada %3,8, çevrede %52,6 (AUC 0,781). Kaya rotayı ayırmıyor (0,508).
  - Rotanın %100'ü geçilebilir. Geçilmez hücre sayısı 150'de kaldı.
  - Denetim: 24 karoda 40 olası kaçırılan etiket.
- **Dosyalar:** `ml/infer.py`, `scripts/prep_layers.py`, `scripts/validate.py`, `web/data/grid.json`, `web/data/layers.json`, `web/data/layers/{traversability,hazard_ml}.png`, `ml/audit_missed_labels.csv`, `ml/ETIKETLEME.md`, `docs/DATA_PIPELINE.md`, `docs/figures/e10_*`
- **Nasıl çalıştırılır:** `venv\Scripts\python ml\infer.py`, sonra `scripts\prep_layers.py`, sonra `scripts\validate.py`. Model değişince yalnızca bu üçü tekrar çalıştırılır.
- **Varsayımlar:**
  - Formüller: `kum_ml` = kutu kaplama oranı; `kaya_ml = clip(max(alan/0,2, kaya_ha/6,25))`. E6 hücre eşikleri 0,5'e denk geliyor.
  - Güven eşiği 0,25. Hücrenin en az %50'si kapsanmalı.
  - Jeoloji ve YOLO'ya eşit ağırlık (kalibrasyon verisi yok).
  - Kontroller: E8, E11 ve E13 testleri yeni grid ile geçti.
