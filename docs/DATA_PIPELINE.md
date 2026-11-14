# MarsTrail – Veri hattı

Ham NASA/USGS verisinden tarayıcıdaki haritaya kadar her adım: ne aldık, neyi neden attık, nasıl temizledik ve normalize ettik.

- Sayılar elle yazılmadı. Kaynak `scripts/pipeline_stats.py` → [figures/pipeline_stats.json](figures/pipeline_stats.json). E7 sayıları `scripts/build_regions.py` → [figures/e7_stats.json](figures/e7_stats.json).
- Kaynak linkleri ve tarihler: [veri_envanteri.md](veri_envanteri.md).

**Ortak hedef sistem:** Mars 2000 küresi (R = 3396,19 km) üzerinde coğrafi koordinat. Birim derece, doğu pozitif. Üç rasterin projeksiyonu farklıydı:

| Veri | Kaynak projeksiyon |
| --- | --- |
| D4 THEMIS | SimpleCylindrical |
| D5 CTX DEM | Jezero_Crater_Projection |
| D6 jeoloji | MTM_clon77_5E |

**Çalışma alanı (v2):** 77,28–77,60°D, 18,293–18,597°K, yaklaşık 18 × 18 km.

- Üs, delta önü, Three Forks ve Cheyava Falls içinde.
- Alan metre cinsinden kare seçildi, 256² grid hücreleri kare (70 m) olsun diye: 0,32° boylam × cos(18,445°) ≈ 0,304° enlem.
- Enlem üsse ortalı. Üsten doğu kenarına 8,4 km, kuzey ve güney kenarlarına ~9 km var.
- **Neden genişletildi:** İlk sürüm (77,28–77,48°D, 18,365–18,555°K, 44 m hücre) üssü doğu kenarına 1,6 km uzakta bırakıyordu. O₂ tam doluyken (480 dk) yeşil bölgenin yarıçapı ~6,2 km, sarının ~7,8 km; bölgeler harita kenarında kesiliyordu. Ara bir deneme (doğu 77,56°) yetmedi: test, doğu kenarında 64 yeşil hücre buldu.
- **Bedeli:** Hücreler 44 m'den 70 m'ye büyüdü.
- **E5 karolama alanı ilk sürümde sabit kaldı** (`tile_for_yolo.TILE_BBOX`), çünkü etiketlenen karoların adları o ızgaraya göre.

**Çıktı ızgaraları:**

| Izgara | Çözünürlük | Kullanım |
| --- | --- | --- |
| 1024² | ~17,6 m/piksel | Harita katmanları (PNG) |
| 256² | 70,4 m/hücre | Rota ve O₂ hesabı (`grid.json`) |

---

## E1 · Sahte veri (geçici)

- **Neden:** Arayüz gerçek veriyi beklemeden kurulabilsin. Veri sözleşmesi ilk gün sabitlendi.
- **İçerik:** Sentetik arazi ve yaklaşık koordinatlar. Her kayıtta `"dummy": true`.
- **Durum:**
  - `layers.json`, PNG'ler, `grid.json`: E3'te gerçeğiyle değişti.
  - `regions.json`, `poi.geojson`, `stories.json`: E7'de değişiyor.
  - `astronauts.json` ve `conditions.json`: varsayım olarak kalıyor (gerçek astronot yok; MEDA örneği sonra).

## D1 · Perseverance konumları (M20_waypoints.json)

- **Neden bu veri:** Her noktanın tarihçesindeki "Perseverance buraya Sol X'te geldi" bilgisi ve pinlerin gerçek koordinatı buradan geliyor. Uydurma koordinat yerine rover'ın ölçülmüş konumu.
- **Ham içerik:** 0,6 MB, 708 nokta (Sol 13–2022), nokta başına 23 alan.
- **Atılanlar:**
  - 23 alanın 19'u atıldı. Kalanlar: `sol`, `lon`, `lat`, `elev_geoid`. Atılanlar araç duruşu (roll, pitch, yaw), RMC/SCLK sayaçları ve mesafe toplamları; ürün bunları kullanmıyor.
  - Kayıt atılmadı. 708 noktanın 516'sı çalışma alanında; kalan 192'si (krater kenarı tırmanışı) Sol araması için tutuluyor.
- **Temizleme ve eşleme:** Bir olayın tarihindeki rover konumu, o Sol'e eşit ya da ondan önceki son kayıt olarak alınır ("o gün rover nerede duruyordu"). Ayrıntı ve sayılar E7 bölümünde.

## D2 · Perseverance sürüş izi (M20_traverse.json)

- **Neden bu veri:** Tehlike haritamızı bağımsız bir gerçekle sınamak için. Rover'ın fiilen geçtiği yer "geçilebilir" olmalı.
- **Ham içerik:** 1,7 MB, 559 sürüş çizgisi, 36.661 köşe noktası, toplam 46,0 km.
- **Atılanlar:** Çalışma alanı dışındaki 11.430 köşe. Alan içinde 25.231 köşe kaldı.
- **İşlem:** Köşeler 256² grid hücrelerine düşürüldü, rover yolundan 397 benzersiz hücre çıktı (70 m hücre; hücre indeksi `floor`, walkback.js ile aynı yöntem. İlk 44 m'lik alanda 679 hücreydi).
- **Sonuç (E3):** 397 hücrenin %100'ü geçilebilir. Tam doğrulama E10'da yapılacak, rastgele hücrelerle kıyas da eklenecek. Geçilmez oranı düşük (%0,2) olduğundan %100 tek başına güçlü bir kanıt değil.

## D3 · Ingenuity uçuşları (m20_heli_flight_path.json)

- **Neden bu veri:** Başka bir gezegende ilk motorlu uçuşun yeri tarih pini olur. Hayatta Kal modundaki İHA taramasına da gerçekçi ölçek veriyor (uçuş uzunlukları).
- **Ham içerik:** 2,3 MB, 72 uçuş (Uçuş 1, Sol 58 → Uçuş 72, Sol 1036). 72'sinin de başlangıcı çalışma alanında.
- **Kullanılan:** Uçuş 1'in kalkış noktası (Wright Brothers Field pini). Diğer uçuşlar E13'te İHA senaryosunda kullanılabilir.

## D4 · THEMIS termal eylemsizlik (Jezero_Thermal_Inertia_v1.tiff)

- **Neden bu veri:** Spirit'i kaybettiren tuzak, sert kabuğun altındaki gevşek kumdu. Gevşek malzeme gündüz çabuk ısınıp gece çabuk soğur, yani termal eylemsizliği düşüktür. Bu katman batma riskini yörüngeden görmemizi sağlıyor. JPL'nin SPOC çalışması termal eylemsizliğin kayma ile ilişkili olduğunu gösteriyor.
- **Ham içerik:** 1,7 MB, 890 × 890 = 792.100 piksel, 100 m/piksel, float32, birim TIU (J m⁻² K⁻¹ s⁻½).
- **Atılanlar:**
  - 298.150 NoData pikseli (değer 0, %37,6): mozaiğin THEMIS kapsamı dışındaki köşeleri.
  - Toplam 757.900 piksel çalışma alanı dışında (NoData'nın tamamı dahil).
  - Alan içinde 34.200 piksel kaldı, hiçbiri NoData değil.
- **Temizleme:** NoData `0` → NaN, böylece yeniden örneklemede ortalamaya karışmıyor.
- **Normalizasyon:**
  - `termal_norm = clip((TI − p2) / (p98 − p2), 0, 1)`
  - p2 = 155,5 TIU, p98 = 326,8 TIU (alan içi ham aralık 132,8–400,6).
  - Uç değerler kırpıldı: alt uçta 684, üst uçta 684 piksel. Min-max yerine yüzdelik kullanıldı, çünkü birkaç aykırı piksel bütün ölçeği bastırırdı.
  - 0 = en gevşek zemin, 1 = en sert kaya.
- **Yeniden örnekleme:** Bilinear. Not: 100 m → 17,6 m, yani PNG'de görünen incelik interpolasyondan geliyor, yeni bilgi değil.
- **Görsel:** [figures/d4_thermal_normalize.png](figures/d4_thermal_normalize.png)

## D5 · CTX sayısal yükseklik modeli (M20_JezeroCrater_CTXDEM_20m.tif)

- **Neden bu veri:** Yürüyüş süresi ve geçilmezlik eğime bağlı. Tobler hız formülü ve 25° sınırı doğrudan eğim istiyor. Alanı kapsayan en ince açık DEM bu (20 m).
- **Ham içerik:** 90,3 MB, 4456 × 5067 = 22.578.552 piksel, float32, metre.
- **Atılanlar:**
  - 13.977 NoData pikseli (−3,4·10³⁸, mozaik kenarları).
  - Toplam 21.767.652 piksel çalışma alanı dışında (%96,4). Alan içinde 810.900 piksel kaldı, hiçbiri NoData değil.
- **Temizleme:** −9000 m altı ve 30.000 m üstü değerler NoData sayılıp NaN yapıldı. Alanda yükseklik −2684 ile −1733 m arası.
- **Eğim:** Yeniden örneklemeden önce, DEM'in kendi 20 m metrik ızgarasında hesaplandı. Önce örnekleseydik eğim yumuşardı.
  - Formül: `eğim = atan(√((∂z/∂x)² + (∂z/∂y)²))`
  - 20 m'de alan içinde 2652 piksel 25°'nin üstünde.
- **Yeniden örnekleme:** Yükseklik ve eğim için average (alan ortalaması). 70 m grid hücresinde ortalama eğim kullanılıyor, çünkü yürüyüş maliyeti için hücrenin genel eğimi önemli. Bu yüzden 20 m'deki dar dik şeritlerin bir kısmı hücre ortalamasında 25°'nin altına iniyor (bilinçli ödün).
- **Normalizasyon:** `eğim_risk = clip(eğim / 25°, 0, 1)`
- **Çıktı:** `hillshade.png` (ışık KB'dan, 45°), `slope.png`, `grid.json` elev ve eğim.
- **Görsel:** [figures/d5_dem_crop.png](figures/d5_dem_crop.png)

## D6 · USGS SIM 3464 jeoloji haritası (sim3464_database.zip)

- **Neden bu veri:** Eğim ve termal fiziği verir, jeoloji ise "ne üzerinde yürüdüğünü" söyler. Eolyen birim kum dalgalarının (Opportunity'nin tuzağı) haritalanmış yeri. Delta birimleri bilim değeri en yüksek hedefler.
- **Ham içerik:** 349 MB zip, 181 dosya. Shapefile değil, ArcGIS dosya veritabanı (`Nili.gdb`), 13 katman. Birim katmanı `GeoUnits_v1`: 1304 poligon, 14 birim, MTM_clon77_5E projeksiyonu.
- **Atılanlar:**
  - 19 sistem dosyası (`__MACOSX`, `.DS_Store`, `.lock`).
  - Zip'teki rasterler ve ArcMap dosyaları (DEM'i D5'ten zaten alıyoruz).
  - 13 katmanın 12'si (kontaklar, isimler, şekil katmanları vb.). Sadece `GeoUnits_v1` kullanılıyor.
  - Çalışma alanına değmeyen 1186 poligon. Alanda 118 poligon kaldı.
- **Temizleme (kaynaktaki hatalar):**
  - "Crater riim unit" yazım hatası (1 poligon) → "Crater rim unit".
  - Birim kodu 5 (Nili Planum 2) olup adı "Upper etched unit" olan 1 poligon var. Kod ile ad çelişiyor; eşlemede kod yerine ad kullanıldığı için bu poligon ada göre sınıflandı.
- **Rasterize:** 1024² ve 256² ızgaraya. Önce büyük, sonra küçük poligonlar yazıldı ki küçük birimler büyüklerin altında kaybolmasın.
- **Alan içindeki birimler (km²):**

| Birim | km² |
| --- | --- |
| Jezero floor | 121,4 |
| Upper etched | 47,9 |
| Lower etched | 37,5 |
| Eolian bedform (kum) | 37,2 |
| Crater rim | 33,7 |
| Jezero fan 2 (delta) | 26,6 |
| Smooth | 13,1 |
| Jezero fan 1 (delta) | 6,3 |
| Nili Planum 1 | 0,5 |
| Nili Planum 2 | 0,1 |

- **Normalizasyon (birim → sayı):** Her birime yürünebilirlik, kaya vekili (0–1) ve bilim değeri (1–5) atandı. Tablo `scripts/prep_layers.py` içinde `GEO_UNITS`. Varsayım: birim tanımlarından takdirle seçildi, EVA verisiyle kalibre edilmedi.
  - Kum = eolyen birim (0/1).
  - Kaya vekili = birimin pürüzlülüğü. Eolyen birimde 0, çünkü cezası kum teriminden geliyor; iki kez sayılmıyor.
- **Görsel:** [figures/d6_geology_crop.png](figures/d6_geology_crop.png)

## Füzyon · Geçilebilirlik skoru ve grid (E3)

- **Formül (PLAN.md §5):** `skor = 0,4·eğim_risk + 0,25·kum + 0,15·kaya + 0,2·(1 − termal_norm)`. Sonuç 0–1 arasına kırpılır.
- **Eksik değer kuralı:** Kaya bilinmiyorsa 0,3, termal bilinmiyorsa 0,5 kullanılır. Bu alanda kullanılmadı, çünkü üç kaynak da alanı tam kapsıyor.
- **Geçilmez hücre:** eğim > 25° veya skor > 0,8.
  - 65.536 hücrenin 150'si (%0,2) geçilmez. Hepsi eğim yüzünden; skor eşiğini aşan hücre yok. Ortalama skor 0,26.
- **Yürüme hızı ve maliyet:**
  - Hız (Tobler): `v = 6·exp(−3,5·|tanθ + 0,05|) km/sa × 0,6`. 0,6 çarpanı Mars ve giysi düzeltmesi (varsayım).
  - Hücre maliyeti: `70,4 m / v × (1 + 2·skor)` dakika. Geçilmez hücrelere 999 yazılır.
- **Kontrol:** `walkback.js` Dijkstra, yönlü eğim, yük 0 kg, tek yön, üsten (`web/tests/e8.html`):

| Hedef | Süre |
| --- | --- |
| Three Forks | 73 dk (dönüş 6 kg yükle 74 dk) |
| Delta önü | 75 dk |
| Cheyava Falls | 278 dk (9,5 km) |

- **Görsel:** [figures/fusion.png](figures/fusion.png). Dört terim ve skor yan yana.
- **grid.json'a `score` eklendi (E8):** `walkback.js` kenar süresini yönlü eğimle (komşu hücrelerin yükseklik farkı) yeniden hesaplıyor; yokuş yukarı ve aşağı farklı sürüyor. Eğimden bağımsız arazi cezası için hücre skoru ayrıca gerekiyor. Görsel: [figures/e8_zones.png](figures/e8_zones.png) (O₂ bölgeleri; nabız 85 ve 150).
- **grid.json'a `sand` eklendi (E11):** Hücrenin yarısından fazlası eolyen birimse 1. Toplam 7531 hücre = 37,3 km², jeolojideki eolyen alanla (37,2 km²) tutarlı. `eva.js` Go/No-Go'daki "rotada kum tuzağı var mı?" kontrolü bunu kullanıyor.
- **YOLO (E10):** Gelince "kaya" terimi jeoloji vekili yerine model tespit yoğunluğundan gelecek.

## E7 · Nokta kartları: D1 + D3 + D7 (scripts/build_regions.py)

### Konum (D1, D3)

- **Neden:** Pinler uydurma koordinatta değil, olay günü rover'ın ölçülmüş konumunda olsun.
- **Kural:** Sol'ü olayın Sol'üne eşit ya da daha küçük olan son D1 kaydı. Rover numune alırken günlerce park ettiği için "o gün rover nerede duruyordu" sorusunun cevabı bu.

| Nokta | Olay Sol'ü | Kullanılan D1 kaydı | Not |
| --- | --- | --- | --- |
| Üs | 0 | Sol 13 | İlk kayıt, "no motion": iniş noktası |
| Rochette | 190 | Sol 180 | |
| Delta önü | 415 | Sol 415 | Bu Sol'den sonra yükseklik −2545 → −2520 m: tırmanış |
| Three Forks | 653 | Sol 652 | |
| Cheyava Falls | 1212 | Sol 1210 | |

- **Ingenuity uçuş alanı:** D3 Uçuş 1'in kalkış noktası. D1'de rover'ın Sol 34 konumuyla birebir aynı (77,45102°D, 18,44486°K); rover helikopteri burada bıraktı. İki bağımsız kaynak birbirini doğruluyor.
- **Jezero (bütün krater):** Rover konumu yok. Yayınlanmış krater merkezi kullanıldı (18,38°K, 77,58°D).

### Nokta başına arazi (D5, D6, E3 katmanları)

- Her nokta için DEM yüksekliği, jeoloji birimi ve 300 m içindeki şu değerler hesaplanıyor: en yüksek eğim, kum oranı, termal_norm ve skor. Sonuç `terrain` alanında.
- `hazards[]` metni bu sayılardan kuralla üretiliyor, elle yazılmıyor:

| Tehlike | Koşul |
| --- | --- |
| Dik yamaç | 300 m içinde eğim > 25° |
| Eğimli arazi | 300 m içinde eğim > 15° |
| Eolyen kum | 300 m içinde kum oranı ≥ %10 |
| Gevşek zemin | termal_norm < 0,25 |

- Sonuç: Demo rotasındaki noktalarda tehlike çıkmıyor (en yüksek eğim 11°). Cheyava Falls'ta 2 tehlike var: 29,3° yamaç ve %24 kum.

### Kum alanı pini (D6)

- 475 eolyen poligondan, üs → delta önü hattına en yakın olanı seçildi (235 m).
- Poligon 16,9 km² olduğu için pin merkeze değil, poligonun rotaya en yakın kısmına konuldu: poligon ∩ (hat + 300 m tamponu).
- Sonuç: delta önünün ~700 m güneydoğusu. Demodaki "yolda bir kum alanı var" ve Opportunity/Spirit bilgi kartı bu pine bağlı.

### D7 · Perseverance ham görüntüleri (API)

- **Neden bu veri:** Nokta kartında "oraya varınca bunu göreceksin". Astronotun yürüyeceği yerin, rover'ın o gün çektiği gerçek fotoğrafı.
- **Ham içerik:** 7 Sol için API'den 1795 görüntü kaydı. Sol başına bir JSON; görüntü başına kamera, boyut, direk açısı (`mastEl`), yerel saat ve 4 boy bağlantı. Not: API `num`/`page` parametrelerini yok sayıp Sol'ün bütün görüntülerini döndürüyor.
- **Eleme hunisi (sayılar 7 Sol'ün toplamı):**

| Adım | Kalan | Neden |
| --- | --- | --- |
| API kaydı | 1795 | |
| Tam kare (`sample_type = Full`) | 1795 | Bu Sol'lerde küçük önizleme yok |
| Sol göz Navcam / Mastcam-Z / ön Hazcam | 699 | Sağ göz stereo tekrarı; arka Hazcam, SkyCam, iç kameralar atıldı |
| Genişlik ≥ 1000 px | 632 | Alt kareler (ör. 128×128) atıldı |
| Renkli/gri ikizden tekilleştirme | 493 | Aynı kare `EBY` (renkli) ve `ECM` (gri) olarak iki kez geliyor; renkli kaldı |
| Direk açısı −25° … +5° | 195 | Daha aşağısı rover güvertesi/kol, yukarısı gökyüzü |
| Doku eşiği: ortalama kenar şiddeti ≥ 3,5 | | 5 kare atıldı (düz gökyüzü). Eşik ölçümden: gökyüzü 1,4 ve 3,1; en düşük iyi kare 4,2 |
| İnsan kontrolü | | 1 kare atıldı: rover donanımı, manzara yok. `EXCLUDE` listesinde gerekçesiyle |
| Seçilen | 10 | 7 noktaya |

- **Seçim kuralı:** Kamera başına, direk açısı −10°'ye (ufka yakın, zemini de gösteren) en yakın kare.
- **Yedekler:**
  - Three Forks: Sol 653'te uygun kamera yok, Sol 654 kullanıldı. Yakın Sol'ler ±3'e kadar deneniyor.
  - Üs (Sol 0) ve Cheyava Falls (Sol 1212): direk kamerası o gün manzaraya bakmıyordu, ön Hazcam kullanıldı.
- **Çıktı:** `web/data/photos/*.jpg` (800 px yerel kopya, toplam ~580 KB, çevrimdışı demo için). Kaynak sayfa, büyük boy bağlantısı, `imageid`, UTC tarih, yerel Mars saati ve kredi (NASA/JPL-Caltech[/ASU]) `regions.json` içinde.
- **İstatistik:** [figures/e7_stats.json](figures/e7_stats.json)

## D8 · HiRISE ortogörüntü mozaiği → YOLO karoları (E5, scripts/tile_for_yolo.py)

- **Neden bu veri:** Opportunity'yi 5 hafta tutan kum dalgası 10–15 cm yüksekliğindeydi. Kayalar da metre ölçeğinde. 20 m'lik DEM ve 100 m'lik termal veri bunları göremez; 25 cm/piksel HiRISE görebilir. Kendi tespit modelimizin (YOLOv8) eğitim verisi bu.
- **Ham içerik:**
  - Zip 5,47 GB, 17 dosya.
  - Ortogörüntü: 76.576 × 107.264 piksel, uint8, 0,25 m, NoData = 0, Equirectangular_MARS projeksiyonu. Kapsam 77,058–77,381°D, 18,136–18,588°K. Dosya 4,68 GB (LZW).
- **Atılanlar (zip):**
  - DTM 1 m (712 MB): rota grid'i için 20 m CTX yeterli, 70 m hücreye zaten ortalanıyor.
  - Renkli güven haritası (1,5 GB) ve README/PDF dışındaki yardımcı dosyalar.
  - Güven haritası (FOM, 66 MB) çıkarıldı ama kullanılmadı. Görüntünün değil DTM eşleştirmesinin kalitesini gösteriyor; karo kalitesini doğrudan görüntüden ölçtük.
- **Kapsam sınırı:** Mozaik, E5 karolama alanının (ilk çalışma alanı, 77,28–77,48°D) yalnızca güneybatı çeyreğini kapsıyor (~%23); genişletilmiş alanın daha da küçük bir kısmını. Üs, delta önü, Three Forks ve Cheyava Falls kapsam dışında. E10'da model kapsam dışı bölgeye Mars Trek'in HiRISE Jezero mozaiğiyle uygulanacak ya da YOLO katmanı kapsanan bölgeyle sınırlı kalacak.

### Karolama ve eleme

| Adım | Karo | Neden |
| --- | --- | --- |
| E5 karolama alanı (ilk çalışma alanı, sabit), 640 × 640 px (160 × 160 m), örtüşmesiz | 2590 (37 × 70) | 640 = YOLOv8 giriş boyu, yeniden boyutlandırma yok |
| NoData içeren karolar atıldı | −1444 (%55,8) | Mozaik eğik bir şerit; köşeler ve şerit arası boşluklar boş |
| Dokusuz karolar atıldı | −58 | 1/16 ön görünümde std < 8,56 (kullanılabilir karoların alt %5'i). Düz toz ya da gölge, etiketlenecek nesne yok |
| Kullanılabilir | 1088 | |
| Aday: kum | 338 | Eolyen birim ≥ %60 (D6) |
| Aday: kaya | 261 | Eolyen < %20 ve kaya vekili yüksek birimler ≥ %60 (krater kenarı, pürüzlü, delta, aşınmış, ejekta) ve doku medyanın üstünde |
| Aday: negatif | 37 | Düz taban ya da smooth birim ≥ %90 ve doku medyanın altında |
| Seçilen | 150 = 70 kum + 65 kaya + 15 negatif | |
| Tam çözünürlükte NoData yeniden kontrolü | 0 atıldı | |

- **Mekânsal yayılım:** Her gruptan en uzak nokta örneklemesiyle seçim yapıldı. Böylece aynı yerin komşu karoları eğitimde tekrar etmiyor, val kümesi train'e sızmıyor. Seed = 42, sonuç tekrarlanabilir.
- **Normalizasyon:**
  - Formül: `piksel' = clip((piksel − 60) / (219 − 60) · 255, 0, 255)`
  - 60 ve 219 değerleri, karolama alanının (NoData hariç) %0,5 ve %99,5 yüzdelikleri.
  - Karo başına değil, alan genelinde tek doğrusal germe: aynı zemin her karoda aynı parlaklıkta görünür. Çıkarımda (E10) da aynı parametreler kullanılacak; `ml/tiles_meta.json` içinde saklı.
- **Çıktı:**
  - `ml/roboflow_upload.zip`: 150 PNG, 28,2 MB.
  - `ml/tiles_manifest.csv`: karo → piksel konumu, derece sınırları, birim oranları, seçim nedeni.
- **Etiketleme:** Roboflow'da; ayrıntı ve sayılar aşağıda (E6).
- **Görseller:** [figures/d8_tile_selection.png](figures/d8_tile_selection.png) (karo haritası ve atılanlar), [figures/d8_tile_samples.png](figures/d8_tile_samples.png) (örnek karolar). Sayılar: [figures/e5_stats.json](figures/e5_stats.json).

## E6 · Etiketler ve YOLOv8 eğitimi (ml/dataset_stats.py, ml/train.py)

- **Veri seti:** Roboflow `marstrail-jezero` v1 "v1-150karo", YOLOv8 formatı. E5'in 150 karosu, 640 × 640, 0,25 m/piksel.
- **Neden:** Kum dalgası ve kaya, DEM'in (20 m) ve termal verinin (100 m) göremediği tehlikeler. Model bunları 25 cm'lik görüntüde bulup E10'da grid maliyetine ekleyecek.

### Etiket tanımı ve sınırlamalar

- **Ön etiketleme:** Roboflow Auto Label (GPT-6.1 Terra). 150 karonun hepsi elle kontrol edilip düzeltildi (YZ beyanında, TESLIM.md bölüm 4).
- **Sınıflar:**

| İndis | Sınıf | Tanım | Kutu boyu (p10 / medyan / p90) |
| --- | --- | --- | --- |
| 0 | `kaya` | Küçük yüzey engeli, metre ölçeğinde: kaya ya da küçük çukur. Gölgenin hangi yanda olduğuna bakmadan ayırt edilemiyor; astronot için ikisi de engel, bu yüzden tek sınıf. | 2,5 / 5,0 / 9,4 m |
| 1 | `kaya_alani` | Yoğun kaya bölgesi. Grid hücresi 70 m olduğu için bölge ölçeği seçildi. | 10,8 / 23,9 / 65,1 m |
| 2 | `kum_dalgasi` | Kum dalgası sırtları ya da sırtlarla dolu kum alanı. | 26,1 / 60,9 / 159,8 m |

- **Etiketlenmeyenler:**
  - Büyük çöküntü yamaçları ve gölgeleri: eğim DEM'den (D5) geliyor, aynı tehlike iki kez sayılmasın.
  - Mozaik dikiş yerleri: arazi değil görüntüleme izi.
- **Sınırlamalar** (ölçülen):
  - 237 `kum_dalgasi` kutusunun 74'ü karonun ≥ %80'ini kaplıyor. Bu karolarda kum "nesne" değil "karo türü" olarak etiketli; kum için model kısmen karo sınıflandırıcısı gibi öğrenir. E10'da çıktı zaten yoğunluk olarak grid'e gittiği için kabul edildi.
  - 15 negatif karonun 14'ünde etiketleme sırasında nesne bulundu. Tamamen boş karo 7 (train 6, valid 1). Yanlış pozitif riski E10'da kontrol edilecek.
  - `kaya_alani` en az örnekli sınıf (82 kutu). Valid kümesinde 17 kutu var; bu sınıfın mAP'i birkaç kutuyla değişebilir.
  - Hepsi HiRISE mozaiğinin kapsadığı güneybatı bölümden. Başka aydınlatma/çözünürlükte genellemesi denenmedi.

### Etiket sayıları

| Bölüm | Karo | Boş karo | `kaya` | `kaya_alani` | `kum_dalgasi` | Toplam kutu |
| --- | --- | --- | --- | --- | --- | --- |
| train | 120 | 6 | 199 | 65 | 193 | 457 |
| valid | 30 | 1 | 56 | 17 | 44 | 117 |

- **Temizlik kontrolü:** Geçersiz satır (koordinat 0–1 dışında, bilinmeyen sınıf) 0. Manifest'teki 150 karonun 150'si dışa aktarımda var. Bütün görüntüler 640 × 640.
- **Bölme:** 80/20 Roboflow'da rastgele. Karolar E5'te en uzak nokta örneklemesiyle seçildiği için komşu karo yok; val kümesi train'e sızmıyor.
- **Normalizasyon:** Piksel germesi E5'te yapıldı (60–219 → 0–255). Roboflow karoları JPG'ye çevirdi (kayıplı sıkıştırma; 2 m'lik kaya ~8 piksel, etkisi küçük ama not edildi). Ultralytics girişte 0–1'e böler.
- **Artırma (sadece eğitimde, Roboflow'da yok):** yatay+dikey çevirme (yukarıdan çekimde "yukarı" yok), parlaklık ±%30 (güneş açısı ve mozaik şeritleri arası ton farkı), renk tonu/doygunluk 0 (görüntü gri), döndürme 0 (ince kum sırtlarında kutuyu şişirir), ölçek ±%25 (sınıflar fiziksel boyuta bağlı; varsayılan ±%50 kaya ile kaya_alani'yi karıştırır), mozaik (son 10 epoch kapalı). Gerekçeler `ml/train.py` yorumlarında.
- **Öğrenme yöntemi:** YOLOv8m, COCO ön-eğitimli ağırlıktan transfer öğrenme. 640 px, 100 epoch, erken durdurma 20 epoch, batch 16, seed 0. RTX 5090 Laptop, CUDA 12.8.
- **Sonuç:** [eğitim bitince doldurulacak: sınıf bazında P, R, mAP50, mAP50-95]
- **Görseller:** [figures/e6_dataset.png](figures/e6_dataset.png) (sınıf sayıları ve kutu boyu dağılımı). Sayılar: [figures/e6_dataset_stats.json](figures/e6_dataset_stats.json).

---

## Özet tablo (sunumdaki veri hattı slaytı)

| # | Veri seti | Ham | Atılan | Son | Yöntem |
| --- | --- | --- | --- | --- | --- |
| D1 | Perseverance konumları | 0,6 MB · 708 nokta × 23 alan | 19 alan (duruş, sayaçlar) | 5 pin konumu (+ D3'ten 1) | Sol eşleme: o Sol'e eşit ya da önceki son kayıt |
| D2 | Sürüş izi | 1,7 MB · 559 çizgi, 36.661 köşe | 11.430 köşe (alan dışı) | 397 grid hücresi (70 m) | Rasterize → doğrulama |
| D3 | Ingenuity uçuşları | 2,3 MB · 72 uçuş | 71 uçuş (pin için) | 1 tarih pini | Seçim |
| D4 | THEMIS termal eylemsizlik | 1,7 MB · 792.100 px, 100 m | 757.900 px (alan dışı; 298.150 NoData dahil), 1368 px kırpıldı | 1024² + 256², 0–1 | Reprojeksiyon, bilinear, %2–98 normalizasyon |
| D5 | CTX DEM | 90,3 MB · 22,6 M px, 20 m | 21,77 M px (alan dışı), 13.977 NoData | 1024² (×2 PNG) + 256² grid | 20 m'de eğim, average, hillshade |
| D6 | SIM 3464 jeoloji | 349 MB · 181 dosya, 13 katman, 1304 poligon | 19 sistem dosyası, 12 katman, 1186 poligon; 2 kaynak hatası düzeltildi | 118 poligon, 10 birim → 1024² | Reprojeksiyon, rasterize, katsayı tablosu |
| D7 | Perseverance ham görüntüleri | 7 Sol · 1795 görüntü kaydı | 1785: kamera, alt kare, renkli/gri ikiz, açı, doku eşiği, 1 insan kontrolü | 10 fotoğraf (800 px, ~580 KB) | Kural tabanlı eleme hunisi + kenar şiddeti eşiği |
| D8 | HiRISE 25 cm mozaiği | 5,47 GB zip · 76.576 × 107.264 px | Zip'te ortogörüntü dışındaki her şey (DTM, güven haritaları); 2590 karonun 1444'ü NoData, 58'i dokusuz | 150 karo (640², 28 MB) → etiket: E5 | Karolama, birim tabanlı aday seçimi, en uzak nokta örneklemesi, %0,5–99,5 germe |
| Füzyon | Geçilebilirlik + grid | D4 + D5 + D6 | – | 65.536 hücre (70 m), 150 geçilmez | Ağırlıklı toplam, Tobler, Dijkstra |
