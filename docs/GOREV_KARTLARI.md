# MarsTrail – Görev Kartları (v2)

Bu belge çalışırken açık duracak. Her kartı sırayla oku, "Yap" adımlarını uygula, "Kontrol" satırı tutuyorsa sonraki karta geç. Takılırsan kartın "Takılırsan" satırına bak. Proje tanımı, hikâye ve formüller için: docs/PLAN.md.

**Claude Code ile kullanım:** "E3 kartını yap" ya da "G2 kartını yap" demen yeterli. Claude Code kartı okur, gereken scripti yazar, çalıştırır ve "Kontrol" satırını doğrular.

## 1. Kararlar (v2)

1. **Sadece astronot.** Rover modu yok. Opportunity ve Spirit sadece "tarihi olay" bilgi kartı olarak var. İHA yalnızca Hayatta Kal modunda arama aracı olarak görünür.
2. **O₂ bölgeleri her zaman açık.** Harita açıldığı andan itibaren seçili astronotun etrafında üç bölge görünür. Astronot kartında "Şu an YEŞİL bölgedesin" gibi bir durum etiketi bulunur.

| Bölge | Anlamı | Hesap |
| --- | --- | --- |
| Yeşil | Rahat: git, çalış, %25 pay ile dön | Gidiş + dönüş süresi ≤ kalan O₂ / 1,25 |
| Sarı | Sınır: dönebilirsin ama pay yok | Gidiş + dönüş süresi ≤ kalan O₂ |
| Kırmızı | Dönüşü olmayan bölge | Gidiş + dönüş süresi > kalan O₂ |

Bölgeler daire değil; araziye ve kuma göre şekil alır. O₂ azaldıkça, nabız ya da yük arttıkça canlı daralır.

3. **Her noktanın tarihçesi var.** Pin kartında: ilk ne zaman görüldü/tanımlandı, hangi görev ne zaman inceledi, ne buldu, Perseverance oraya hangi Sol'de geldi ve o gün çektiği fotoğraf.
4. **Verilen kaynakların arkasındaki ham veri kullanılır.** Mars Trek, USGS ve Perseverance sayfalarının beslediği açık dosyalar (bölüm 2). Yeni bir kaynak eklenmez; gerekirse sonra bağlarız.
5. **Plan Cmt 14:15'te başlıyor**, her kontrol noktasından önce tampon var, aksaklıkta neyin kesileceği önceden belli (bölüm 4).

## 2. Veri: indirilecek dosyalar

Hepsi resmi kaynakların (Mars Trek, USGS-NASA Jeolojik Haritalama, Perseverance sayfaları) arkasındaki açık dosyalar. Sıra, küçükten büyüğe: önce hızlı inenler, en büyüğü arka planda.

| # | Dosya | Boyut | Kaynak | Ne çıkaracağız |
| --- | --- | --- | --- | --- |
| D1 | [M20_waypoints.json](https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json) | küçük | Perseverance konum haritası | Her Sol'ün konumu → "Perseverance buraya Sol X'te geldi", fotoğraf eşleştirme |
| D2 | [M20_traverse.json](https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_traverse.json) | küçük | Aynı | Rover'ın gerçek yolu → tehlike haritası doğrulaması |
| D3 | [m20_heli_flight_path.json](https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json) | küçük | Aynı | Ingenuity uçuş yolları → İHA arama senaryosuna ilham ve tarih pini |
| D4 | [THEMIS termal eylemsizlik, Jezero](https://zenodo.org/record/4931348) (dosya: `Jezero_Thermal_Inertia_v1.tiff`) | 1,7 MB | Mars Trek'teki THEMIS verisinin Jezero mozaiği | Zemin gevşekliği (düşük değer = gevşek kum/toz) |
| D5 | [CTX DEM 20 m](https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif) | 87 MB | [USGS Astrogeology](https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic) | Eğim, yükseklik profili, `grid.json` |
| D6 | [Jeolojik harita SIM 3464](https://pubs.usgs.gov/publication/sim3464) (shapefile: `Jezero_GeoUnits.shp`) | veritabanı zip 349 MB | USGS-NASA Jeolojik Haritalama | Birim → yürünebilirlik katsayısı + bilim değeri |
| D7 | Perseverance ham görüntü JSON'u ([galeri](https://mars.nasa.gov/mars2020/multimedia/raw-images/)) | durağa göre | Perseverance galerisi | Durakların Sol'üne ait Navcam/Mastcam-Z fotoğrafları |
| D8 | [HiRISE ortogörüntü + DTM mozaiği](https://astrogeology.usgs.gov/search/map/mars-sample-return-terrain-relative-navigation-hirise-dtm-mosaic) ([zip](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024_mosaics.zip)) | büyük (zip) | USGS Astrogeology | YOLO eğitimi (25 cm/piksel) |

**D6 için kısayol:** 349 MB'lık zip yavaş inerse yalnızca shapefile'ı alın ya da USGS'in interaktif haritasından Jezero içindeki birimleri dışa aktarın. Bize 6–8 birim yeterli (Jezero tabanı, delta birimleri, krater kenarı, eolyen birimler).

**D8 için kısayol:** Mozaik inmezse Mars Trek'ten Jezero'nun HiRISE/CTX görüntüsünü çalışma alanı kadar dışa aktarın.

**Veri türü sayısı:** optik (HiRISE, CTX), topografik (DEM), termal (THEMIS), jeolojik (SIM 3464), yer görüntüsü (Navcam/Mastcam-Z), hareket izi (rover ve Ingenuity yolları). Toplam 6 tür.

## 3. Nokta tarihçeleri

Bu tablo `regions.json` ve `stories.json` dosyalarının ham içeriği. Koordinatları D1 dosyasından (o Sol'deki rover konumu) alın; fotoğrafı D7'den aynı Sol için seçin.

| Nokta | Tarih | Olay | Kaynak |
| --- | --- | --- | --- |
| Jezero gölü | 2005 | Antik göl ilk kez yörünge görüntülerinden tanımlandı (Caleb Fassett) | [Astronomy](https://www.astronomy.com/?p=40600) |
| Jezero (tamamı) | Kasım 2020 | Mars 2020 bilim ekibi, HiRISE üzerinde 1:5000 ölçekli fotojeolojik harita yayımladı | [Stack vd. 2020](https://dspace.mit.edu/entities/publication/592b30f4-e0c9-4caa-8f9c-2bd12ebdffe9) |
| Jezero + Nili Planum | 2 Ara 2020 | USGS jeolojik haritası (SIM 3464) yayımlandı | [USGS](https://www.usgs.gov/maps/geologic-map-jezero-crater-and-nili-planum-region-mars) |
| Octavia E. Butler iniş alanı | 18 Şub 2021 | Perseverance Jezero'ya indi (üsümüzün yeri) | [NASA](https://science.nasa.gov/mission/mars-2020-perseverance/location-map/) |
| Ingenuity uçuş alanı | 19 Nis 2021 | Başka bir gezegende ilk güçlü, kontrollü uçuş | [uçuş yolu verisi](https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json) |
| Rochette kayası | 1 Eyl 2021 | İlk başarılı kaya numunesi | [Mars 2020 zaman çizelgesi](https://kaweah.freedombox.rocks/kiwix/wikipedia_en_all_maxi_2023-10/Timeline_of_Mars_2020) |
| Delta (Kodiak) | 7 Eki 2021 | Rover görüntüleri göl ve nehir deltasını ve ani sel izlerini doğruladı (Science) | [EarthSky](https://earthsky.org/space/ancient-martian-lake-delta-floods-perseverance/) |
| Three Forks depo | 21 Ara 2022 – 28 Oca 2023 | Başka bir gezegende ilk numune deposu; 10 tüp bırakıldı | [Space Odyssey Hub](https://spaceodysseyhub.com/replays/perseverance) |
| Cheyava Falls (Neretva Vallis) | 18 Tem 2024 | "Leopar benekli" kaya; olası biyoimza | [Sky at Night](https://skyatnightmagazine.com/space-missions/perseverance-jezero-crater) |
| Tarihi kart: Opportunity, Purgatory Kumulu | 26 Nis 2005 | 10–15 cm'lik kum dalgasında 5 haftadan fazla mahsur | [NASA](https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune) |
| Tarihi kart: Spirit, Troy | Mayıs 2009 | Yumuşak kuma gömüldü, görevini kaybetti | [Space.com](https://www.space.com/18766-spirit-rover.html) |

Opportunity ve Spirit Jezero'da değil. Haritada "bu kum türü buna benziyor" bilgi kartı olarak gösterilir; konumları Jezero'da bir pin olarak değil, kartın içinde verilir.

**Demo için seçilecek 3 durak:** Üs (Octavia E. Butler) → Delta önü (Hawksbill Gap / Kodiak yönü) → Three Forks depo → üs. Bunların hepsinin D1'de Sol'ü ve D7'de fotoğrafı var.

## 4. Kontrol noktaları, tamponlar, kesme sırası

| Saat | Bu saatte çalışıyor olmalı | Tutmazsa |
| --- | --- | --- |
| Cmt 15:15 | Repo, sahte veri; Gözde'nin küresi dönüyor | Küre yoksa Leaflet 2D'ye geç |
| Cmt 17:15 | Gerçek katmanlar haritada, üst bar saatleri | Jeoloji katmanı kesilir, eğim + termal yeter |
| Cmt 21:45 | **MVP:** 2 profil, katmanlar, nokta kartları, rota çizme, her zaman açık O₂ bölgeleri | Kesme sırasının 1–3. maddeleri kesilir |
| Paz 01:00 | YOLO katmanı, planlayıcı, dönüş noktası | 4–5. maddeler kesilir |
| Paz 05:30 | Canlı yürüyüş + Hayatta Kal | 6. madde kesilir |
| Paz 08:30 | **Kod donduruldu**, link telefonda açılıyor | Ne varsa onunla devam |
| Paz 12:00 | Slayt, video, 3 prova | — |
| Paz 13:30 | **Teslim edildi** (14:00'ten yarım saat önce) | — |

**Tamponlar:** Her blokta 15–30 dakikalık "tampon" kartı var. Tampona gerek kalmazsa bir sonraki karta erken geç. Gece uykuları çakışmıyor; biri hep uyanık.

### Kesme sırası (aksaklıkta yukarıdan aşağı kes)

1. Worldview "Dünya'da afet" kapanış sahnesi
2. Perseverance yolu ile doğrulama yüzdesi
3. "Arkadaşını kurtar" rotası
4. İHA tarama animasyonu (sadece arama alanı kalır)
5. Çok duraklı planlayıcı (tek durak + dönüş yeter)
6. YOLO (yerine eğim + termal + jeoloji füzyonu)

**Asla kesilmeyecekler:** her zaman açık O₂ bölgeleri, astronot profili, üst bar saatleri, nokta tarihçeleri. Bunlar projenin kimliği.

### Genel kurallar

- Bir işe **30 dakikadan fazla** takılırsan dur: hata mesajını Claude Code'a ver ya da kartın B planına geç.
- Her kart bitince `git push` ve takım sohbetine tek satır: "E3 bitti, katmanlar web/data'da."
- Paz 08:30'dan sonra yeni özellik yok.

## 5. Elif'in görev kartları (Claude Code ile)

### E1 · 14:15–14:45 · Repo ve sahte veri

- **Neden:** Gözde gerçek veriyi beklemeden çalışmaya başlasın.
- **Yap:** 1) Klasörler: `data/raw`, `data/processed`, `scripts`, `ml`, `web/data`. 2) `.gitignore`: `data/raw`, `data/processed`, `ml/dataset`, `*.tif`, `*.tiff`, `*.zip`, `*.pt`, `venv`. 3) Python sanal ortamı + paketler (rasterio, numpy, geopandas, shapely, pillow, requests, ultralytics). 4) `scripts/make_dummies.py` yaz ve çalıştır. 5) Commit + push.
- **Çıktı:** `web/data/` içinde `regions.json`, `poi.geojson`, `layers.json` (+ birkaç sahte PNG), `grid.json`, `astronauts.json`, `stories.json`, `conditions.json` (sahte, veri sözleşmesine uygun).
- **Kontrol:** Gözde dosyaları çekip okuyabiliyor.
- **Takılırsan:** Repo yerine ortak bir klasör (Drive) kullanın, sonra taşırsınız. Windows'ta rasterio/geopandas kurulmazsa conda ile kur.

### E2 · 14:45–15:30 · Veri indirme + organizatör sorusu

- **Neden:** Her şey bu dosyalara dayanıyor.
- **Yap:** 1) `scripts/download_data.py` yaz. 2) Önce D8'i (en büyük) arka planda başlat. 3) D1–D5'i `data/raw/` altına indir. 4) D6 shapefile'ını al. 5) D7'yi şimdilik indirme (E7'de). 6) İnen her dosyanın boyutunu ve açılıp açılmadığını tablo olarak raporla. 7) Bu arada Elif organizatöre sorar: "Listedeki kaynakların arkasındaki USGS ve NASA ham dosyalarını kullanabilir miyiz? Sunum kaç dakika? Teslimde ne isteniyor?"
- **Çıktı:** `data/raw/` dolu, cevaplar not edildi.
- **Kontrol:** D1–D5 açılıyor.
- **Takılırsan:** D6 inmezse jeoloji katmanını sonraya bırak. D8 inmezse bölüm 2'deki kısayol.

### E3 · 15:30–16:45 · Katmanlar ve grid

- **Neden:** Haritadaki bütün tehlike ve O₂ hesabı buradan besleniyor.
- **Yap:** `scripts/prep_layers.py`: 1) D5 ve D4'ü aynı koordinat sistemine getir, Jezero çalışma alanına kırp (iniş alanı, delta önü ve Three Forks'u kapsayacak şekilde). 2) Eğim. 3) Termal eylemsizliği 0–1'e ölçekle. 4) D6 jeoloji birimlerine yürünebilirlik katsayısı ver. 5) Füzyon skoru (formül PLAN.md bölüm 5). 6) Renkli, şeffaf PNG'ler + `layers.json` (bbox derece cinsinden). 7) 256×256 `grid.json` (elev, cost, blocked, bounds).
- **Çıktı:** `web/data/layers/*.png`, `layers.json`, `grid.json`.
- **Kontrol:** PNG'ler açılınca krater ve delta tanınabiliyor.
- **Takılırsan:** Koordinat sistemi sorunu çıkarsa önce `gdalinfo` çıktısını incele; yetişmezse jeolojiyi atla.

### E4 · 16:45–17:15 · Tampon + envanter + teslim

- **Yap:** 1) `veri_envanteri.md`: her dosya için görev, alet, tarih, çözünürlük, kaynak linki. 2) Push, Gözde'ye haber ver.
- **Kontrol:** 17:15 kontrol noktası tutuyor.

### E5 · 17:15–18:45 · YOLO etiketleme

- **Neden:** Kendi modelimiz, mühendislik vitrininin bir numarası.
- **Yap:** 1) `scripts/tile_for_yolo.py`: D8 ortogörüntüsünü 640×640 karolara böl; kayalık ve kumlu bölgelerden 150 karo seç. 2) Elif karoları Roboflow'a yükler. 3) İki sınıf: `kaya`, `kum_dalgasi`. 4) YOLOv8 formatında dışa aktar → `ml/dataset/`.
- **Çıktı:** `ml/dataset/` (train/val).
- **Kontrol:** En az 120 etiketli karo.
- **Takılırsan:** 80 karo + tek sınıf (`kum_dalgasi`).

### E6 · 18:45–19:15 · Eğitimi başlat + yemek

- **Yap:** `ml/train.py` (yolov8n/s, 60 epoch) yaz ve arka planda başlat. GPU'ya göre model boyutunu seç.
- **Kontrol:** Loss düşüyor.

### E7 · 19:15–20:45 · Nokta kartları ve tarihçeler

- **Neden:** "Bu nokta ne zaman keşfedildi, kim inceledi" özelliği.
- **Yap:** `scripts/build_regions.py`: 1) Bölüm 3 tablosunu kullan. 2) D1'den her olayın Sol'ündeki konumu çek. 3) D7 (Perseverance ham görüntü JSON'u) üzerinden o Sol'e ait 1–2 fotoğraf linki seç. 4) `regions.json`, `stories.json`, `poi.geojson` yaz.
- **Kontrol:** Gözde'nin kartında tarih, olay ve fotoğraf görünüyor.

### E8 · 20:45–21:45 · Saat ve O₂ bölgeleri

- **Yap:** 1) `web/marstime.js`: Mars24 ile Jezero yerel saati, Sol, Dünya–Mars ışık gecikmesi, gün batımına kalan süre. 2) `web/walkback.js`: `grid.json` üzerinde Dijkstra; `Walkback.zones(start, o2Min, hr, loadKg)` → yeşil/sarı/kırmızı poligonlar; `Walkback.path(a, b)` → güvenli rota. 3) Tarayıcı konsolunda test et. 4) Gözde'ye kullanım örneğiyle ver.
- **Kontrol:** Jezero saati makul; üç renkli bölge araziye göre şekil alıyor.

### E9 · 21:45–22:15 · Kontrol noktası (Gözde ile)

- MVP'yi baştan sona deneyin. Eksik varsa kesme sırasına bakın.

### E10 · 22:15–23:30 · YOLO çıkarımı ve doğrulama

- **Yap:** 1) `ml/infer.py`: model tüm karolarda çalışır → kaya/kum yoğunluğu → `hazard_ml.png`. 2) `grid.json` maliyetini güncelle. 3) `scripts/validate.py`: D2 ile doğrulama — rover yolunun yüzde kaçı "geçilebilir".
- **Kontrol:** Model katmanı haritada; doğrulama sayısı not edildi.

### E11 · 23:30–00:45 · Planlayıcı

- **Yap:** `web/eva.js`: duraklar + kalma süreleri → gidiş/dönüş rotası, zaman çizelgesi, dönüş noktası, Go/No-Go. Gözde'ye bağla.
- **Kontrol:** Üs → delta → Three Forks → üs planı çıkıyor.

### E12 · 00:45–01:15 · Tampon

### Uyku · 01:15–03:45

### E13 · 03:45–05:15 · Hayatta Kal verisi

- **Yap:** `web/rescue.js`: son konum + kalan O₂ → arama alanı; İHA zikzak rotası; arkadaş rotası. Gözde'ye bağla.
- **Kontrol:** "Telsiz koptu" tıklanınca alan ve rota çıkıyor.

### E14 · 05:15–06:30 · Mühendislik slaytlarının malzemesi

- **Yap:** YOLO mAP ve 4 örnek tespit görseli; doğrulama yüzdesi; veri katmanları görseli; formüller.

### E15 · 06:30–08:30 · Slaytlar

- **Yap:** 7 slayt (PLAN.md bölüm 7; veri hattı slaytı = DATA_PIPELINE.md özet tablosu). Gözde'den ekran görüntüleri al. NASA logosu, bayrağı, arması yok.
- **Kontrol:** Slaytlar okunuyor, hikâye 45 saniyede anlatılabiliyor.

## 6. Gözde'nin görev kartları

Tek sayfa: `web/index.html`, `web/app.js`, `web/style.css`. Harita CesiumJS (CDN), grafik Chart.js. Kayıtlar localStorage'da. Elif'in gerçek dosyaları gelene kadar sahte dosyalarla çalış; dosya adları aynı kalacağı için kod değişmez.

### G1 · 14:15–15:15 · Mars küresi

- **Yap:** Cesium ion token al. Mars elipsoidini kur. Mars Trek WMTS katmanını (Viking renkli mozaik ya da renkli MOLA) ekle.
- **Kontrol:** Küre dönüyor, zoom çalışıyor.
- **Takılırsan (15:15):** Leaflet 2D + aynı Mars Trek katmanı.

### G2 · 15:15–16:15 · Jezero uçuşu + katman menüsü

- **Yap:** "Jezero'ya git" butonu, `flyTo` animasyonu. `layers.json`'daki PNG'leri bbox ile ekle; aç/kapa, opaklık, lejant.
- **Kontrol:** Sahte katmanlar açılıp kapanıyor.

### G3 · 16:15–17:15 · Arayüz iskeleti + üst bar

- **Yap:** Üst bar: Mars saati, Sol, Dünya saati (UTC + TR), "Dünya X dk uzakta", gün batımına kalan, bağlantı durumu. Şimdilik sabit değerler; E8'de gerçek hesap gelecek. Sol panel: astronotlar, katmanlar. Sağ panel: detay kartı. Koyu tema, turuncu vurgu. Mobilde alttan açılan çekmece.
- **Kontrol:** Laptop ve telefonda düzgün.

### G4 · 17:15–18:45 · Astronot profili

- **Yap:** İki astronot (Ayşe, Ali). Form alanları: ad, kilo, giysi, O₂ (dk), batarya %, su %, nabız, yük kg, radyasyon dozu. "Güncelle" butonu. localStorage'a kaydet. Seçili astronotun kartında **bölge etiketi** (Yeşil/Sarı/Kırmızı) için yer aç.
- **Kontrol:** Sayfa yenilenince profil duruyor.

### Yemek · 18:45–19:15

### G5 · 19:15–21:45 · Nokta kartları + rota çizme

- **Yap:** 1) Pine tıklayınca kart: ad, tarihçe (zaman çizgisi), olay, Perseverance Sol'ü, fotoğraf. 2) Opportunity/Spirit bilgi kartları. 3) "Rota çiz" modu: tıkla nokta ekle, çift tıkla bitir. 4) Mesafe, süre, yükseklik profili grafiği.
- **Kontrol:** 21:45 kontrol noktası (her zaman açık bölgeler E8 ile birlikte geliyor).

### Kontrol noktası · 21:45–22:15 (Elif ile)

### G6 · 22:15–00:30 · O₂ bölgeleri + planlayıcı arayüzü

- **Yap:** 1) `Walkback.zones()` çıktısını üç renkli poligon olarak her zaman çiz; profil güncellenince yeniden çiz. 2) Bölge etiketini kartta göster. 3) Planlayıcı paneli: durak ekle, kalma süresi gir, zaman çizelgesi, dönüş noktası işareti, Go/No-Go listesi (E11 ile).
- **Kontrol:** Plan ekranı çalışıyor; O₂ değişince bölgeler anında değişiyor.

### G7 · 00:30–02:45 · Canlı yürüyüş

- **Yap:** "Başlat" ile astronot simgesi rota boyunca ×60 ilerler. O₂ sayacı akar, bölgeler daralır. Nabız kaydırıcısı. Uyarılar: kum alanı, dönüş noktası, kırmızı bölgeye giriş. Fotoğraf/not pini. Bitişte özet kartı.
- **Kontrol:** Yürüyüş baştan sona oynuyor.

### Uyku · 02:45–05:15

### G8 · 05:15–07:15 · Hayatta Kal paneli

- **Yap:** "Telsiz koptu" butonu → arama alanı (`rescue.js`), İHA zikzak rotası animasyonu, Ali için "arkadaşını kurtar" rotası ve onun kendi O₂ kontrolü.
- **Kontrol:** Acil durum demosu çalışıyor.

### G9 · 07:15–08:30 · Yayın ve dondurma

- **Yap:** Vercel veya GitHub Pages; PWA manifest ve ikon; telefonda test; demo akışını bir kez baştan sona dene.
- **Kontrol:** 08:30'da link telefonda açılıyor. Kod donduruldu.

## 7. Birlikte: demo, prova, teslim

| Saat | Görev | Bitti sayılır eğer… |
| --- | --- | --- |
| 08:30–09:30 | Demo senaryosu (PLAN.md bölüm 7) demo bilgisayarında birebir | Her tıklama çalışıyor |
| 09:30–10:00 | Demo videosu (en fazla 30 sn, OBS; senaryo PLAN.md bölüm 7) | Video kaydedildi, ≤30 sn |
| 10:00–12:00 | 3 tam prova (5 dk + 2 dk soru-cevap), kronometreyle; her provadan sonra tek düzeltme; birbirinize jüri soruları sorun | Süre tutuyor |
| 12:00–13:00 | Son düzeltmeler + 1 prova | — |
| 13:00–13:30 | Teslim: docs/TESLIM.md (form cevapları, kaynak listeleri, YZ beyanı, Drive kontrol listesi) | **13:30'da teslim edildi** |
