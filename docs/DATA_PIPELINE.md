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
- **Görseller:** [figures/e6_dataset.png](figures/e6_dataset.png) (sınıf sayıları ve kutu boyu dağılımı). Sayılar: [figures/e6_dataset_stats.json](figures/e6_dataset_stats.json).

### 1. eğitim (v1): ısınmada ıraksadı

Ayarlar yukarıdaki gibi, optimizer `auto` (Ultralytics 800 adımdan kısa eğitimde AdamW seçiyor, lr 0,0014), AMP (fp16) açık. 81 epoch koştu (erken durdu), en iyi epoch 61, süre 3 dk 10 sn. Değerler en iyi ağırlıkla, valid kümesinde (30 karo):

| Sınıf | P | R | mAP50 | mAP50-95 |
| --- | --- | --- | --- | --- |
| `kaya` | 0,413 | 0,063 | 0,169 | 0,072 |
| `kaya_alani` | 0,000 | 0,000 | 0,027 | 0,008 |
| `kum_dalgasi` | 0,346 | 0,295 | 0,292 | 0,257 |
| **Hepsi** | 0,253 | 0,120 | **0,162** | 0,112 |

**Eğri yorumu (results.png):**
- Epoch 1–2 normal: val mAP50 0,07.
- **Epoch 3–4'te eğitim patladı.** cls_loss 4,1 → 16,7 ve box_loss 1,7 → 3,5. Doğrulama kayıpları epoch 3–15 arasında NaN, metrikler epoch 4–11 arasında sıfır. Model önceden öğrendiklerini kaybetti ve epoch 12'den sonra neredeyse sıfırdan yeniden öğrendi.
- Sonrasında eğitim kayıpları düzenli düşüyor ama val mAP 0,05 ile 0,19 arasında sıçrıyor. 30 karoluk val kümesi küçük; 2–3 karonun doğru ya da yanlış olması eğriyi oynatıyor.
- Train kaybı düşerken val kaybı epoch 50–57'de yeniden yükseliyor. Bu, aşırı öğrenmenin başladığını gösteriyor.

**Confusion matrix yorumu:** Köşegen iyi görünüyor (kaya 0,61, kaya_alani 0,71, kum_dalgasi 0,77) ama yanıltıcı. Ultralytics bu matrisi doğrulamanın güven eşiğiyle (0,001) çiziyor, yani çok düşük güvenli tahminler de sayılıyor. 0,25 eşiğindeki örnek tahmin görselinde (`e6v1_val_batch0_pred.jpg`) 16 karoda hiç kutu yok. Model doğru yeri buluyor ama emin değil.

- **Karışma:** Gerçek kayaların %18'i `kaya_alani` diye tahmin ediliyor. İki sınıf aynı dokunun iki ölçeği, bu beklenen bir karışma.
- **Yanlış pozitifler:** Arka planda (etiketsiz yerlerde) çıkan yanlış tahminlerin %56'sı `kum_dalgasi`, %33'ü `kaya_alani`. Bölge ölçekli iki sınıfın kutu sınırı belirsiz olduğu için model "kum alanı" kutusunu farklı boyutta çizince eşleşmiyor ve yanlış pozitif sayılıyor.
- **Sınıf başına:** `kum_dalgasi` en iyi sınıf (mAP50 0,29). `kaya` küçük nesne olduğu için recall çok düşük (0,06). `kaya_alani` öğrenilemedi (17 val kutusu, mAP50 0,03).

**Sonuç:** Bu modelle E10'a geçilmez. Asıl sorun epoch 3'teki ıraksama: en iyi epoch'a kadar geçen sürenin 12 epoch'u kurtarma ile geçti. Ayarlar düzeltilip yeniden eğitilecek (aşağıda, ablation).

Şekiller: [e6v1_results.png](figures/e6v1_results.png), [e6v1_confusion_matrix_normalized.png](figures/e6v1_confusion_matrix_normalized.png), [e6v1_BoxPR_curve.png](figures/e6v1_BoxPR_curve.png). Sayılar: [e6v1_metrics.json](figures/e6v1_metrics.json).

### Ablation deneyi

**Ortak kararlı ayar:** v1'in ıraksamasında iki olası neden vardı: AdamW ile fp16 (AMP). İkisi de kaldırıldı. Bütün koşular SGD (lr0 0,01) ve fp32 ile, aynı tohumla (seed 0) eğitiliyor; böylece fark şanstan değil ayardan geliyor. Her epoch sonunda doğrulama kaybı NaN mı diye kontrol ediliyor. Gerekçe `ml/train.py` içinde.

| Koşu | Model | Veri | Ne ölçülüyor |
| --- | --- | --- | --- |
| 0) `e6_m3` | YOLOv8m | 3 sınıf | v1 ile aynı kurulum, kararlı ayarla. A–C bununla karşılaştırılır. |
| A) `e6_s3` | YOLOv8s | 3 sınıf | Küçük model 150 karoda daha mı iyi genelleşir? (11 M parametre, yolov8m 26 M) |
| B) `e6_m2` | YOLOv8m | 2 sınıf | kaya_alani kutuları kaya'ya birleşir. Aynı dokunun iki ölçeğini ayırmaya çalışmak zarar mı veriyor? |
| C) `e6_s2` | YOLOv8s | 2 sınıf | A ve B birlikte |
| D) `e6_cls_s` | YOLOv8s-cls | 600 alt karo, 3 sınıf | Kutu yerine 80 m'lik parçayı sınıflandırmak (aşağıda) |

**D · Karo sınıflandırma veri seti** (`ml/make_cls_dataset.py`):
- 150 karonun her biri 2 × 2'ye bölündü: 600 alt karo, 320 px = 80 m. Bu, grid hücresine (70,4 m) yakın bir boyut.
- Etiket mevcut kutulardan otomatik türetiliyor; öncelik sırası kum, kayalık, düz:

| Sınıf | Kural | Eşiğin gerekçesi (600 alt karonun dağılımı) |
| --- | --- | --- |
| `kum` | kum_dalgasi kutularının birleşimi alt karonun ≥ %50'sini kaplıyor | Kaplama iki uçta toplanıyor: 115 alt karoda 0, 313'ünde ≥ 0,9. Ara değerler düz dağılmış, belirgin bir vadi yok. Bu yüzden "hücrenin çoğunluğu" kuralı seçildi. 0,3 ile 0,5 arası yalnızca 36 alt karoyu etkiliyor. |
| `kayalik` | kaya_alani kaplaması ≥ 0,1 ya da alt karoda ≥ 2 kaya | 533 alt karoda kaya_alani 0, 518'inde kaya 0. Tek kaya etrafından dolaşılan bir engel, "kayalık arazi" değil. Etiketlemede çok kayalı karolarda kayaların yalnızca en belirgin 30–40'ı işaretlendiği için kaya sayısı bir alt sınır; eşik bu yüzden düşük tutuldu. |
| `duz` | İkisi de değil | |

- **Sayılar:** train kum 290, kayalık 50, düz 140; val kum 71, kayalık 14, düz 35.
- **Bölme karo bazında:** Bir karonun 4 alt karosu Roboflow'daki tarafına gidiyor. Komşu alt karolar aynı sahneyi paylaştığı için alt karo bazında rastgele bölme val kümesine sızıntı yapardı.
- **Sınırlamalar:**
  - Sınıflar dengesiz: kayalık %11. Bu yüzden düz doğruluğun yanında sınıf dengeli doğruluk ve "her şeye kum de" taban çizgisi de raporlanıyor.
  - Etiketler kutulardan türedi; kutuların hatası etiketlere de geçiyor.
- Sayılar: [figures/e6_cls_dataset_stats.json](figures/e6_cls_dataset_stats.json).

### Ablation sonuçları

Bütün değerler valid kümesinde: 30 karo, ya da D için o karolardan çıkan 120 alt karo. Kaynak dosyalar: `docs/figures/<koşu>_metrics.json` (Ultralytics'in kendi doğrulaması) ve [e6_merged_eval.json](figures/e6_merged_eval.json) (`ml/eval_merged.py`, adil karşılaştırma). Tablolar `ml/compare_runs.py` ile üretildi.

**1) Her koşunun kendi doğrulaması** (Ultralytics val, sınıf sayısı koşudan koşuya farklı):

| Deney | mAP50 | mAP50-95 | kaya mAP50 (R) | kaya_alani mAP50 | kum_dalgasi mAP50 (R) | Eğitim | Çıkarım | Epoch (en iyi) | NaN epoch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 (AdamW + fp16) | 0,162 | 0,112 | 0,169 (0,06) | 0,027 | 0,292 (0,30) | 3,2 dk | 5,2 ms | 81 (61) | 13 |
| 0) m, 3 sınıf | 0,273 | 0,173 | 0,153 (0,20) | 0,154 | 0,512 (0,59) | 1,6 dk | 5,0 ms | 37 (17) | 0 |
| A) s, 3 sınıf | 0,269 | 0,166 | 0,126 (0,14) | 0,197 | 0,483 (0,48) | 1,2 dk | 2,3 ms | 57 (37) | 0 |
| B) m, 2 sınıf | 0,341 | 0,227 | 0,153 (0,18) | – | 0,528 (0,52) | 1,8 dk | 5,0 ms | 40 (20) | 0 |
| C) s, 2 sınıf | 0,328 | 0,221 | 0,134 (0,08) | – | 0,522 (0,57) | 1,7 dk | 2,3 ms | 79 (59) | 0 |

- **Kararlı ayar en büyük kazanç:** Aynı model ve veriyle v1 → 0) geçişinde mAP50 0,162'den 0,273'e çıktı, kum_dalgasi 0,29'dan 0,51'e. Hiçbir koşuda NaN yok.
- **2 sınıflı koşuların genel mAP'i bu tabloda karşılaştırılamaz:** B/C'nin genel mAP'i 0,33–0,34 görünüyor, ama bunun sebebi en zor sınıf kaya_alani'nin ortalamadan çıkması. Kaya ve kum sınıflarının kendi değerleri neredeyse aynı. Bu yüzden 2. tabloya bakılır.

**2) Adil karşılaştırma: herkes aynı 2 sınıflı görevde** (`eval_merged.py`). 3 sınıflı modellerin kaya_alani tahminleri kaya sayıldı; dört model de `dataset_2cls/valid` üzerinde aynı kodla ölçüldü:

| Deney | mAP50 | mAP50-95 | kaya mAP50 | kum_dalgasi mAP50 |
| --- | --- | --- | --- | --- |
| 0) m, 3 sınıf | 0,322 | 0,225 | 0,147 | 0,496 |
| A) s, 3 sınıf | 0,311 | 0,217 | 0,131 | 0,491 |
| B) m, 2 sınıf | 0,323 | 0,229 | 0,145 | 0,501 |
| C) s, 2 sınıf | **0,327** | **0,229** | 0,136 | **0,518** |

Dört model arasındaki fark 0,016 mAP50, yani 30 karoluk val kümesinde gürültü düzeyinde. **Model boyutu (m ya da s) ve sınıf sayısı (2 ya da 3) sonucu belirgin biçimde değiştirmiyor.** Darboğaz veri: kaya mAP50'si her modelde ~0,14.

**3) E10'daki kullanımın ölçüsü: 80 m'lik hücre sınıfı** (`eval_merged.py`, `cell_level`):
- Tespitler, D'nin etiket kuralıyla aynı biçimde kum / kayalık / düz sınıfına çevrildi. Güven eşiği 0,25 (Ultralytics varsayılanı); val'e göre ayarlanmadı.
- 2 sınıflı modellerde kenarı ≥ 10 m olan kaya kutusu kaya_alani sayıldı. Eşik ölçümden: etiketlerde kaya p90 = 9,4 m, kaya_alani p10 = 10,8 m.
- Bu sayede beş model de aynı 120 alt karoda, aynı soruda karşılaştırılıyor:

| Deney | Doğruluk | Dengeli doğruluk | düz P / R | kayalık P / R (n=14) | kum P / R |
| --- | --- | --- | --- | --- | --- |
| Hep "kum" (taban çizgisi) | 0,592 | 0,333 | – | – | – |
| 0) m, 3 sınıf | 0,742 | 0,601 | 0,65 / 0,63 | 0,36 / 0,29 | 0,84 / 0,89 |
| A) s, 3 sınıf | **0,833** | 0,643 | 0,70 / 0,80 | 0,50 / 0,14 | 0,92 / 0,99 |
| B) m, 2 sınıf | 0,792 | 0,633 | 0,79 / 0,54 | 0,63 / 0,36 | 0,81 / 1,00 |
| C) s, 2 sınıf | 0,808 | **0,657** | 0,71 / 0,63 | 0,63 / 0,36 | 0,86 / 0,99 |
| D) s-cls, karo | 0,800 | 0,643 | 0,71 / 0,57 | 0,56 / 0,36 | 0,86 / 1,00 |

- **Kum hücre ölçeğinde çözülmüş:** Bütün modellerde kum recall'u 0,89–1,00.
- **Asıl zorluk kayalık:** En iyi modeller 14 kayalık hücreden yalnızca 5'ini buluyor; kaçanlar düz sanılıyor. Düz hücrelerin bir kısmı da kum sanılıyor (C'de 35'ten 10'u).
- **D, tespit modellerini geçemedi:** Kutu yerine doğrudan sınıflandırma C ile aynı düzeyde kaldı (0,800 / 0,643). Üstelik en iyi epoch'u 2'ydi; 480 alt karoda hemen ezberliyor. Tespit modeli aynı sonucu verip hücre başına kaya sayısı ve kum kaplaması gibi sürekli bir yoğunluk da veriyor. D yalnızca 3 sınıf etiketi veriyor.

### Model seçimi

**Seçilen: C) YOLOv8s, 2 sınıf (`e6_s2`) → `ml/models/yolo_marstrail.pt`.** Seçim kaydı `ml/models/yolo_marstrail.json` dosyasında.

Gerekçe:
1. **E10'un sorusunda en iyisi:** Hücre düzeyinde dengeli doğruluk 0,657 ile en yüksek. Kayalık recall'u 0,36 ile en iyilerle eşit. Adil karşılaştırmada mAP50 0,327 ve kum_dalgasi mAP50 0,518 ile en yüksek. A'nın düz doğruluğu daha yüksek (0,833), ama kayalık hücrelerin 14'ünden yalnızca 2'sini buluyor. Astronot güvenliği için kayalığı kaçırmak, düzü yanlışlıkla kayalık saymaktan daha pahalı.
2. **Eşitlikte küçük model:**
   - Fark gürültü düzeyinde olduğu için daha basit model seçildi.
   - yolov8s'in parametresi 11,1 M, yolov8m'in 25,9 M. Çıkarım 2,3 ms, m'nin yarısı.
   - Eğitim eğrisi en düzgün olan da C: en iyi epoch 59. m modelleri epoch 17–20'de zirve yapıp ezberlemeye başladı; 150 karoda küçük model daha az aşırı öğreniyor.
3. **2 sınıf haritanın ihtiyacıyla aynı:** E10'a giden bilgi "kayalık" ve "kum". kaya_alani'yi ayrı öğrenmek ölçülebilir bir fayda getirmedi (2. tablo); 2 sınıflı modelde de büyük kaya kutuları boyut eşiğiyle kaya alanı olarak ayrılabiliyor.

**Sınırlar (sunumda söylenecek):**
- Val kümesi küçük: 30 karo, 14 kayalık hücre. Farkların çoğu tek tek karolarla oynar.
- Kaya tespiti zayıf: kaya mAP50 ~0,14.
- Bu sonuç 2. parti etiketlerle (100 karo, ağırlıklı düz ve kayalık) yeniden doğrulanacak. Etiketler gelince aynı ablation ile en azından B ve C yeniden koşulacak; train/val bölmesi bitişik karo grupları korunarak yapılacak.

Şekiller: [e6_s2_results.png](figures/e6_s2_results.png), [e6_s2_confusion_matrix_normalized.png](figures/e6_s2_confusion_matrix_normalized.png), [e6_s2_BoxPR_curve.png](figures/e6_s2_BoxPR_curve.png), [e6_s2_val_batch0_pred.jpg](figures/e6_s2_val_batch0_pred.jpg).

### E10'da modelin kullanımı (not)

- **Kutu değil yoğunluk:** Model haritada kutu çizmek için kullanılmayacak. E10'da tüm karolarda çalışacak; tespitler (ya da D'de sınıf olasılıkları) 70 m'lik grid hücresine **yoğunluk** olarak toplanacak: hücredeki kaya sayısı, kum kaplama oranı. Sonuç `hazard_ml.png` olacak. Kutu sınırının tam tutması (mAP50-95) bu kullanımda ikincil; asıl önemli olan, hücre ölçeğinde kumu ve kayayı doğru yerde bulmak (recall ve yanlış pozitif oranı).
- **Füzyonda tek girdi değil:** YOLO katmanı, geçilebilirlik skorundaki girdilerden yalnızca biri. Diğerleri eğim (D5), termal eylemsizlik (D4) ve jeoloji birimi (D6). Model zayıf kalsa da rota hesabı onlarla çalışmaya devam eder. ML katmanı yalnızca, 20 m DEM'in ve 100 m termal verinin göremediği metre ölçeğindeki engeli ekliyor.
- **Kapsam:** HiRISE mozaiğinin kapsadığı güneybatı bölümle sınırlı (D8). Kapsam dışındaki hücrelerde ML girdisi yok sayılır; ağırlık diğer girdilere dağıtılır.

### Ek etiketleme: 2. parti (scripts/tile_batch2.py)

- **Neden:** v1'de boş karo 7, kaya_alani kutusu 82 taneydi; model etiketsiz yerlerde kutu uyduruyordu.
- **Seçim:**
  - 100 yeni karo: kayalık 40, düz 53 (3'ü dokusuz), kum 7.
  - Izgara ve kontrast germe E5 ile aynı (60–219).
  - Eski 150 karo ve 8 komşusu aday dışı; bu, 893 karoyu dışarıda bırakıyor.
  - En uzak nokta örneklemesi eski karolardan başlatıldı. 75 karo birbirine de bitişik değil. Alan dolduğu için kalan 25 karo eski karolara bitişik değil, ama birbirine bitişik olabilir. Yeniden eğitimde bitişik karolar train/val'de aynı tarafa konacak.
- **Eşikler:**
  - Düz: doku < kullanılabilir karoların %35'lik dilimi (18,3) ve eolyen < %10.
  - Kayalık: kaya vekili birim ≥ %50 ve doku ≥ %60'lık dilim (24,2). Eksik kalan karolar için gevşek kriter: ≥ %40 ve medyan.
  - Kum: eolyen ≥ %60.
- **Çıktı:** `ml/roboflow_upload_2.zip` (18 MB), `ml/tiles_manifest_2.csv`. Görsel: [figures/e6_batch2_selection.png](figures/e6_batch2_selection.png). Sayılar: [figures/e6_batch2_stats.json](figures/e6_batch2_stats.json).

## E10 · YOLO çıkarımı, füzyon ve D2 doğrulaması (ml/infer.py, scripts/prep_layers.py, scripts/validate.py)

- **Neden:** Model bu adımda haritaya giriyor. E6'daki mAP modelin etiketlere ne kadar benzediğini ölçüyordu. Burada ürünün kendisi ölçülüyor: YOLO eklenince skor, gerçek bir gezginin seçtiği rotayı daha iyi açıklıyor mu?
- **Model:** `e6_s2` (YOLOv8s, 2 sınıf). Model değişince yalnız `ml/models/yolo_marstrail.pt` değişir ve üç betik tekrar çalıştırılır; bütün sayılar bu dosyalardan yeniden üretilir.

### Çıkarım

- **Karolar:** E5 ızgarasında NoData içermeyen bütün karolar: 1088 temiz + 58 dokusuz = **1146 karo** (1146 × 160 m × 160 m ≈ 29 km²). Tam çözünürlükte NoData yüzünden atılan karo 0.
- **Ön işleme:** E5 ile aynı germe (60–219). Gri görüntü 3 kanala kopyalanıyor.
  - Fark: eğitim karoları Roboflow'dan JPG olarak geldi, çıkarım kayıpsız diziyle yapılıyor. Küçük bir alan kayması var; ölçülmedi.
- **Süre:** RTX 5090'da 13,5 sn çıkarım, toplam 17 sn.
- **Tespitler (güven ≥ 0,25):** 1551 kaya, 625 kaya alanı, 1986 kum dalgası. 1146 karonun 1078'inde en az bir tespit var.
  - Kaya alanı = kenarı ≥ 10 m olan kaya kutusu. Eşik ölçümden: etiketlerde kaya p90 9,4 m, kaya_alani p10 10,8 m.
- **Dokusuz karolar:** 58 karonun 41'inde tespit var. Karo başına medyan 1 (dokulu karolarda 2). Çoğu karo boyu kum kutusu.
  - Görsel kontrol ([e10_plain_examples.png](figures/e10_plain_examples.png)): E5'teki "dokusuz" ölçüsü 1/16 ön görünümde alınmıştı. Tam çözünürlükte bu karoların çoğunda ince kum dalgacıkları ya da koyu, düz kum örtüsü görünüyor.
  - Yani bunlar büyük olasılıkla yanlış pozitif değil. Yine de yer-gerçeği yok.

### Hücre yoğunluğu (256² grid, 70 m hücre; 1024² katman için de aynısı)

- **Örnekleme:** Her karo 2,5 m aralıklı 64 × 64 noktayla örneklendi. Noktalar coğrafi grid hücresine taşındı; kutu birleşimi kullanıldı, üst üste binen kutular iki kez sayılmadı.
- **Formüller** (E6'daki hücre kuralıyla aynı ölçek):
  - `kum_ml = kum_dalgası kutularının hücrede kapladığı oran`. E6'da "kum hücresi" eşiği 0,5.
  - `kaya_ml = clip(max(kaya_alanı_oranı / 0,2 , kaya_sayısı_ha / 6,25), 0, 1)`. E6'nın kayalık eşikleri (kaya alanı ≥ 0,1 ya da 80 m'de ≥ 2 kaya = 3,1/ha) tam 0,5'e denk geliyor.
- **Kapsama:** HiRISE karoları hücrenin %50'sinden azını kaplıyorsa ML değeri yok sayılıyor (NaN). Bu kurala göre **5666 hücrede** ML var; bunların 2953'ünde kum_ml ≥ 0,5, 599'unda kaya_ml ≥ 0,5.
- **Görsel:** [e10_density.png](figures/e10_density.png). Kum, ortadaki eolyen bandı (77,31–77,34°D) izliyor; kapsamdaki beyaz şeritler HiRISE görüntü şeritleri arasındaki boşluklar.

### Füzyon (prep_layers.py)

- **Formül:**
  - Ağırlıklar değişmedi: `skor = 0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1−termal)`.
  - YOLO kapsamındaki hücrelerde: `kum = 0,5·eolyen_birim + 0,5·kum_ml`, `kaya = 0,5·jeoloji_vekili + 0,5·kaya_ml`. Kapsam dışında E3 aynen kalıyor.
- **Neden ortalama:**
  - Jeoloji 1:75.000 ölçekli poligon; birim içindeki düz alanı göremez.
  - YOLO 25 cm'de bakıyor ama mAP50'si 0,33.
  - İkisini kalibre edecek yer-gerçeği yok; eşit ağırlık en az varsayım gerektiren seçim.
  - YOLO yeni bir terim değil; aynı iki terimin daha ince ölçekli ikinci kaynağı. Füzyonun tek girdisi değil.
- **Etkisi:**
  - HiRISE kapsamında skor ortalama +0,013 değişti; ortalama mutlak değişim 0,034.
  - Geçilmez hücre sayısı 150'de kaldı; YOLO hiçbir hücreyi 0,8 eşiğinin üstüne itmedi.
  - grid.json'daki `sand` alanı (Go/No-Go kum tuzağı) artık birleşik kum terimi ≥ 0,5 olan hücreler.
- **Uygulamaya etkisi:** Üs, delta önü ve Three Forks kapsam dışında. E8, E11 ve E13 testleri yeni grid ile geçti; demo sayıları aynı. Yalnız üsten Cheyava Falls'a tek yön süre 278 dk'dan 279 dk'ya çıktı.
- **Yeni katman:** `hazard_ml.png` ve layers.json'da `hazard_ml`: turuncu kum, kırmızı kaya; düşük yoğunluk (< 0,15) ve kapsam dışı saydam. `traversability.png` güncellendi.

### Doğrulama: Perseverance'ın gerçek rotası (D2)

- **Mantık:** Rover ekibi rotayı tehlikeden kaçınarak seçti. Skor araziyi doğru okuyorsa rotanın geçtiği hücreler rota dışındakilerden daha düşük skorlu olmalı.
- **Ölçü:** `AUC = P(rota hücresinin skoru < rota dışı hücrenin skoru)`. 0,5 hiç ayırt etmemek demek.
- **Rasterleştirme:** D2 çizgisi 10 m'de bir örneklendi; **397 rota hücresi** çıktı, 52'si HiRISE kapsamında.

| Bölge | | Rota medyanı | Rota dışı medyanı | AUC (rota daha kolay) | Rotanın geçilebilir oranı |
| --- | --- | --- | --- | --- | --- |
| Tüm alan (397 rota hücresi) | YOLO'suz | 0,216 | 0,224 | 0,562 | %100 |
| | YOLO'lu | 0,217 | 0,224 | 0,569 | %100 |
| HiRISE kapsamı (52 rota hücresi) | YOLO'suz | 0,397 | 0,395 | **0,498** | %100 |
| | YOLO'lu | 0,360 | 0,404 | **0,626** | %100 |

- **Bootstrap** (rota hücreleri 1000 kez yeniden örneklendi):
  - HiRISE kapsamında AUC önce [0,427 – 0,569], sonra [0,571 – 0,678].
  - **Fark [+0,099 – +0,156]**; 1000 örneğin hiçbirinde fark ≤ 0 değil.
  - Komşu rota hücreleri birbirine benzediği için gerçek belirsizlik bundan biraz daha geniş; aralık alt sınır olarak okunmalı.
- **Doğrudan test, YOLO yoğunlukları (HiRISE kapsamı):**

| | Rota | Rota dışı | AUC |
| --- | --- | --- | --- |
| kum_ml ≥ 0,5 olan hücre | %3,8 | %52,6 | **0,781** [0,746 – 0,818] |
| kaya_ml ≥ 0,5 olan hücre | %5,8 | %10,6 | 0,508 |

- **Yorum:**
  - HiRISE kapsamında jeoloji, termal ve eğimle kurulan skor rotayı rota dışından **hiç ayırt edemiyordu** (0,498).
  - YOLO eklenince ayırt etmeye başladı (0,626). Rover, YOLO'nun kum dediği hücrelerden belirgin biçimde kaçınmış: rotanın %3,8'i, çevrenin %52,6'sı kum. Kendi modelimizin ölçülebilir katkısı bu.
  - Kaya yoğunluğu rotayı ayırmıyor (0,508). Bu, E6'daki zayıf kaya tespitiyle tutarlı (kaya mAP50 ~0,14). Bir başka olasılık: rover ekibi metre ölçeğindeki kayaları rota üstünde hiç önemsemiyor olabilir.
  - Tüm alanda etki küçük (0,562 → 0,569), çünkü rotanın yalnızca 52/397 hücresi HiRISE kapsamında.
  - Kartın sorusu: rotanın %100'ü bizim grid'imizde geçilebilir, YOLO'dan önce de sonra da.
- **Sınırlar:**
  - 52 hücre az ve hepsi kapsamın kuzey kenarında.
  - Rover bir astronot değil: tekerlek kuma insandan daha duyarlı. Rota bilim hedeflerine de gidiyor.
  - Rotanın "kolay" arazi olması bir varsayım.
- **Görsel ve sayılar:** [e10_validation.png](figures/e10_validation.png), [e10_validation.json](figures/e10_validation.json).

### Etiket denetimi (model, etiketlenmiş 150 karoda)

- **Yöntem:** Model, Elif'in etiketlediği görüntülerin aynısında güven ≥ 0,5 ile çalıştırıldı. Aynı gruptaki (kaya + kaya alanı | kum) bir etiketle IoU < 0,1 olan ve merkezi hiçbir etiket kutusunun içine düşmeyen tespitler "olası kaçırılan etiket" sayıldı.
- **Sonuç:** **40 tespit, 24 karoda.** 33'ü train, 7'si valid. Gruplara göre: 13 kaya, 16 kaya alanı, 11 kum.
- **Görsel kontrol** ([e10_audit_examples.png](figures/e10_audit_examples.png), en güvenli 8 örnek):
  - Gerçek eksik etiket gibi görünenler: jz_r066_c015 ve jz_r065_c013'teki koyu kaya ya da çukurlar, jz_r036_c017'deki küçük kaya, jz_r031_c009'daki kaya kümesi.
  - Model hatası gibi görünenler: jz_r029_c021'de kırıklı parlak kaya "kum" sanılmış, jz_r047_c026'da pürüzlü yüzey "kum" sanılmış.
- **Liste:** `ml/audit_missed_labels.csv`. 2. partiyle birlikte Roboflow'da gözden geçirilecek.
- **Sayılar:** [e10_infer_stats.json](figures/e10_infer_stats.json).

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
| E10 | YOLO çıkarımı + doğrulama | 1146 karo (1088 temiz + 58 dokusuz), 4162 tespit (güven ≥ 0,25) | Güven < 0,25; HiRISE kapsamı < %50 olan hücreler | 5666 hücrede kum_ml ve kaya_ml → füzyon; hazard_ml.png | Hücre yoğunluğu, jeoloji ile eşit ağırlık, D2 rotasıyla AUC (HiRISE: 0,498 → 0,626) |
| E6 | YOLO etiketleri + model | 150 karo (D8), Roboflow ön etiket + elle düzeltme · 574 kutu | Geçersiz etiket 0; 2 sınıf için kaya_alani → kaya birleştirildi | YOLOv8s 2 sınıf: mAP50 0,327 (adil karşılaştırma), hücre dengeli doğruluk 0,657 | Transfer öğrenme, kararlı ayar (SGD, fp32), 5 koşuluk ablation, hücre düzeyi doğrulama |
| Füzyon | Geçilebilirlik + grid | D4 + D5 + D6 | – | 65.536 hücre (70 m), 150 geçilmez | Ağırlıklı toplam, Tobler, Dijkstra |
