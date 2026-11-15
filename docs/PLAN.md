# MarsTrail – Final Proje ve 24 Saat Planı

MarsTrail, Mars'taki astronotun yürüyüşünü hazırlıktan acil duruma kadar yöneten bir görev sistemi: astronot profilini ve sarf malzemelerini izler, araziyi ve kumu bilen rotalar planlar, dönüş sınırını canlı hesaplar ve bir şey ters giderse arama-kurtarmayı başlatır.

> Not: Güncel kararlar ve adım adım görevler için docs/GOREV_KARTLARI.md esastır (v2). Bu belge proje tanımı, hikâye, veri ve formüller içindir.

## 1. Benzer çalışmalar: ne yapılmış, bizim farkımız ne?

Sistemin parçaları NASA ve üniversitelerde tek tek var; hepsini açık veriyle, tarayıcıda çalışan tek bir araçta birleştiren ve **canlı sarf malzemesi + kayıp astronot** senaryosunu ekleyen bir çalışma bulamadık.

| Çalışma | Ne yapıyor | Eksik bıraktığı / bizim farkımız |
| --- | --- | --- |
| [SEXTANT (MIT)](https://dspace.mit.edu/handle/1721.1/59560) | Astronot için en verimli rotayı metabolik maliyet, süre ve mesafeye göre hesaplıyor; Güneş konumu ve gölgeyi de hesaba katıyor | Mars çölü istasyonundaki saha testinde **gerçek yürüyüş süresi tahminden anlamlı ölçüde uzun çıktı** ([Gilkey vd.](https://core.ac.uk/download/17204791.pdf)). Bizim farkımız: astronot değerlerini güncelledikçe plan **canlı yeniden hesaplanıyor** |
| [Minerva / xGDS / Playbook (NASA Ames)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6442304) | BASALT analog görevlerinde yürüyüş planlama, zaman çizelgesi ve gecikmeli iletişim desteği | Kapalı NASA iç araçları; tehlike tespiti ve acil durum modu yok |
| [SPOC (JPL)](https://arxiv.org/pdf/1805.05451) ve [NOAH-H (ESA/Open Univ.)](https://oro.open.ac.uk/84535) | HiRISE görüntülerinde derin öğrenmeyle arazi sınıflandırma; NOAH-H Jezero'ya da uygulandı | Rover için; astronot sarf malzemeleri ve dönüş sınırıyla birleştirilmemiş. Biz aynı fikri hafif bir YOLO ile tekrar üretip insana uyguluyoruz |
| [Apollo walkback kuralı](https://ttu-ir.tdl.org/handle/2346/74208) | Astronot her an yürüyerek dönebileceği mesafede kalır | Apollo'da sabit hız ve ortalama tüketimle hesaplandı; araziye bağlı dinamik hesap önerilmiş ama yaygın değil. **Bizim ana katkımız bu** |
| [AstroMind / MarswalkAI](https://dev.to/walsal201/astromind-4ji4) | Aynı göreve yapılmış katmanlı harita + yapay zekâ rota planı | En yakın rakip türü. Bizde canlı profil, dinamik dönüş sınırı, kendi eğitilmiş model, doğrulama ve kurtarma modu var |
| [NASA SUITS öğrenci projeleri](https://spencer-l.github.io/assets/pdf/NASA_SUITS_Retrospective.pdf) | Kask içi arayüz ve A* ile rota | Sarf malzemesi ve kayıp astronot senaryosu yok |

**Destekleyici bulgu:** JPL'nin çalışmasına göre termal eylemsizliği etkileyen fiziksel faktörler, kumlu zeminde yaşanan kayma miktarını da belirliyor ([JPL](https://arxiv.org/pdf/1805.05451)). Termal katmanı "batma riski"ne katmamızın bilimsel dayanağı bu.

## 2. Hikâye

Hikâye üç gerçek olay ve bir eski kural üzerine kurulu. Soyuz 11, Apollo 1 ve Columbia sunumda kullanılmaz: sistemimizin önleyebileceği kazalar değiller.

### Gerçek olaylar

| Olay | Ne oldu | Bizim katmanımız |
| --- | --- | --- |
| [Apollo 14, 1971](https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/), [LROC · PIA12897](https://science.nasa.gov/photojournal/trail-of-discovery-at-fra-mauro) | Shepard ve Mitchell Cone Krateri'nde konumlarını kaybetti; Shepard'ın nabzı 150'ye çıktı, oksijen ve dönüş yolu nedeniyle arama durduruldu. LRO uydusunun 2009 görüntüsü, kenara yaklaşık 30 m kala döndüklerini gösterdi (LROC/ASU, Saddle Rock) | Konum, nabız ve dönüş sınırı |
| [Opportunity, 2005](https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune) | ~30 cm yüksekliğinde (2,5 m genişliğinde) bir kum dalgasında beş haftadan fazla mahsur kaldı | YOLO kum dalgası tespiti |
| [Spirit, 2009](https://www.space.com/18766-spirit-rover.html) | Sert kabuğun altındaki yumuşak kuma gömüldü, görevini kaybetti | Termal eylemsizlik + batma riski |
| [Walkback kuralı](https://ttu-ir.tdl.org/handle/2346/74208) | Apollo'da dönüş mesafesi sabit hız ve ortalama tüketim varsayımıyla hesaplandı | Dinamik dönüş bölgeleri |

Mars'ta bir mesaj tek yönde 3–22 dakika sürüyor; Apollo 14'teki gibi kararları Dünya veremez, sistem vermeli.

### Sunum açılışı (45 sn)

> "1971. Ay. İki astronot bir krateri arıyor. Haritadaki işaretleri bulamıyorlar, kalpleri dakikada 150 atıyor, oksijen azalıyor. Houston 'geri dönün' diyor. Dönüyorlar. Yıllar sonra uydu fotoğrafları gösterdi ki hedeflerine yaklaşık 30 metre kalmıştı.
>
> 2005. Mars. Opportunity otuz santimlik bir kum dalgasına takılıyor, beş hafta çıkamıyor. 2009'da Spirit kuma gömülüyor ve bir daha hiç hareket edemiyor.
>
> Şimdi bunları Mars'ta bir insanın başına getirin. Houston 14 dakika uzakta. Kim 'geri dön' diyecek?"

### Senaryo karakteri

**Sol 34. Astronot Ayşe ve Ali, Jezero Krateri.** Ayşe deltadan numune alacak; yolda bir kum alanı var. Sistem onları hazırlar, yürütür ve bir şey ters gittiğinde Ayşe'yi buldurur. Demo bu iki astronot üzerinden ilerler.

### Kapanış (15 sn)

> "Apollo 14 astronotları nerede olduklarını bilmedikleri için döndü. MarsTrail ile bilecekler. Ve aynı sistem Artemis ile Ay'ın güney kutbundaki yürüyüşlere de uyarlanabilir."

## 3. Proje: MarsTrail modülleri

Uygulama gerçek bir uzay yürüyüşünün dört aşamasını izliyor: **Hazırlık → Planlama → Yürüyüş → Acil durum.** Tek sayfalık web uygulaması (PWA), backend yok, veriler tarayıcıda. Sadece astronot (rover modu yok).

### 3.1 Üst bar (her ekranda)

- **Mars saati:** Jezero yerel saati (LMST) ve Sol numarası, NASA Mars24 algoritmasıyla
- **Dünya saati:** UTC ve Türkiye saati
- **Dünya–Mars gecikmesi:** günün gerçek gezegen konumlarından hesaplanan tek yönlü sinyal süresi
- **Gün batımına kalan süre**
- **Hava:** sıcaklık ve toz (Perseverance MEDA örnek verisi)
- **Bağlantı:** "Habitat ağı: bağlı / kopuk"

### 3.2 Astronot profili (Hazırlık)

İki kişilik ekip (NASA'nın "asla yalnız yürüme" kuralı). Her astronot kartında:

| Alan | Birim | Neyi etkiler |
| --- | --- | --- |
| Ad, kilo, giysi modeli | kg | Metabolik yük |
| Oksijen | dakika ya da % | O₂ bölgeleri, dönüş noktası |
| Batarya, su | % | Go/No-Go kontrolü |
| Nabız | atım/dk | O₂ tüketim çarpanı |
| Taşınan yük | kg | Yürüme hızı |
| Radyasyon dozu | mSv | Uyarı eşiği |

Astronot değerleri yürüyüş sırasında günceller; her güncellemede O₂ bölgeleri, rota ve zaman çizelgesi yeniden hesaplanır.

### 3.3 O₂ bölgeleri (her zaman açık)

| Bölge | Anlamı | Hesap |
| --- | --- | --- |
| Yeşil | Rahat: git, çalış, %25 pay ile dön | Gidiş + dönüş süresi ≤ kalan O₂ / 1,25 |
| Sarı | Sınır: dönebilirsin ama pay yok | Gidiş + dönüş süresi ≤ kalan O₂ |
| Kırmızı | Dönüşü olmayan bölge | Gidiş + dönüş süresi > kalan O₂ |

Bölgeler daire değil; araziye ve kuma göre şekil alır. Astronot kartında "Şu an YEŞİL bölgedesin" etiketi görünür.

### 3.4 Keşfet

3D Mars küresi döner, "Jezero'ya git" ile uçulur. Nokta pinlerinde: ilk ne zaman tanımlandı, hangi görev ne zaman ne buldu, bilimsel değer, tehlikeler ve Perseverance'ın o noktaya geldiği Sol ile o gün çektiği gerçek fotoğraf ("Oraya vardığında bunu göreceksin"). Opportunity ve Spirit'in mahsur kaldığı yerler bilgi kartı olarak gösterilir.

### 3.5 Planla

1. Üs ve bilim durakları seçilir; her durakta kalma süresi girilir.
2. Sistem **gidiş ve dönüş rotasını ayrı** hesaplar (dönüşte yük artışı ve yorgunluk).
3. **Zaman çizelgesi:** çıkış, her durağa varış, dönüş ve dönüşte kalan O₂.
4. Rotada **dönüş noktası** işaretlenir: "Burayı geçersen O₂ dönüşe yetmez."
5. **Go/No-Go kontrolü:** O₂ yeterli mi, gün batımından önce dönülüyor mu, rotada kum tuzağı ya da geçilmez eğim var mı, telsizin koptuğu nokta var mı?
6. Katmanlar: eğim, termal (zemin gevşekliği), jeoloji, **YOLO kaya ve kum dalgası**, birleşik geçilebilirlik skoru.

### 3.6 Canlı yürüyüş

Astronot simgesi rota boyunca hızlandırılmış (×60) ilerler. O₂ sayacı akar, **O₂ bölgeleri canlı daralır.** Nabız kaydırıcısı yükselince daha hızlı daralır. Uyarılar: "Kum alanına 50 m", "Dönüş noktasına 5 dk", "Kırmızı bölgeye giriyorsun". Durakta fotoğraf/not pini eklenebilir; bitişte özet kartı çıkar.

### 3.7 Hayatta Kal (acil durum)

"Telsiz koptu" butonu:

- Son bilinen konum ve kalan O₂ ile **ulaşılabilir alan** hesaplanır; kolay arazi daha olası ağırlıklandırılır.
- İHA için **zikzak tarama rotası** çizilir ve animasyonla oynatılır.
- İkinci astronota **"arkadaşını kurtar" rotası** verilir; kendi O₂'siyle dönebileceği kontrol edilir.

## 4. Veri

Resmi kaynakların hepsi üründe iş yapıyor. İndirilecek dosyaların tam listesi ve linkleri docs/GOREV_KARTLARI.md bölüm 2'de (D1–D8).

| Kaynak | Ne alıyoruz | Üründeki görevi | Veri türü |
| --- | --- | --- | --- |
| [Mars Trek](https://trek.nasa.gov/mars/) | Taban görüntü, CTX/MOLA yükseklik, THEMIS termal eylemsizlik | Küre, eğim, zemin gevşekliği | Optik, topografik, termal |
| [USGS jeolojik harita](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) | Jeolojik birimler (SIM 3464) | Birim başına yürünebilirlik katsayısı ve bilim değeri | Jeolojik |
| [Perseverance ham görüntüleri](https://mars.nasa.gov/mars2020/multimedia/raw-images/) + konum dosyaları | Durak fotoğrafları, rover ve Ingenuity yolları | "Ne göreceksin" kartları, tarihçe, tehlike haritası doğrulaması | Yer görüntüsü, hareket izi |
| [Curiosity rota görseli](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) | Rota sunum dili | Rota tasarımı; bonus: Gale'de ikinci bölge testi | — |
| [NASA Worldview](https://worldview.earthdata.nasa.gov/) | Bir afet bölgesinin uydu görüntüsü | Kapanış: kurtarma modu Dünya'da | Optik (Dünya) |
| [USGS Jezero HiRISE mozaiği](https://astrogeology.usgs.gov/search/map/mars-2020-jezero-crater-landing-site-products) | 25 cm/piksel ortogörüntü + DTM | YOLO eğitimi | Optik, topografik |

### Veri sözleşmesi (Elif üretir, Gözde okur)

Koordinatlar derece, doğu pozitif, boylam −180 ile 180 arası.

| Dosya | İçerik |
| --- | --- |
| `regions.json` | id, name, lat, lon, elevation_m, science_value, summary, hazards[], missions[], history[{date, event, source}], sol, photos[] |
| `poi.geojson` | Habitat, bilim hedefleri, tarihi kaza bilgi kartları (type: habitat, science, hazard, history) |
| `stories.json` | Opportunity, Spirit, Apollo 14 hikâye kartları |
| `layers.json` + `layers/*.png` | eğim, termal, jeoloji, YOLO, birleşik geçilebilirlik; her biri için bbox ve lejant |
| `grid.json` | 256×256 yükseklik, maliyet ve geçilmezlik dizileri + sınırlar |
| `astronauts.json` | İki varsayılan astronot profili |
| `conditions.json` | Sol bazında sıcaklık, toz, rüzgâr (MEDA örneği) |

## 5. Mühendislik ve formüller

| Parça | Dosya |
| --- | --- |
| YOLO kaya + kum dalgası tespiti | `ml/train.py`, `ml/infer.py` |
| Geçilebilirlik füzyonu | `scripts/prep_layers.py` |
| O₂ bölgeleri + güvenli rota + dönüş noktası | `web/walkback.js` |
| Sarf malzemesi modeli + EVA planlayıcı + Go/No-Go | `web/eva.js` |
| Mars saati + Dünya–Mars gecikmesi | `web/marstime.js` |
| Kayıp astronot + İHA tarama rotası | `web/rescue.js` |

### Formüller (sunumda "varsayımlarımız" denir)

- **Yürüme hızı (Tobler):** v = 6 · exp(−3,5 · |tanθ + 0,05|) km/sa × 0,6 (Mars + giysi) × (1 − yük_kg / 100)
- **Geçilebilirlik skoru (0–1):** 0,4 · eğim_risk + 0,25 · kum_yoğunluğu + 0,15 · kaya_yoğunluğu + 0,2 · (1 − termal_norm). Eğim > 25° veya skor > 0,8 ise geçilmez.
- **Hücre maliyeti (dk):** hücre_boyu / v × (1 + 2 · skor)
- **O₂ tüketimi:** taban_hız × (1 + (nabız − 90) / 100). Nabız 150 iken ×1,6.
- **O₂ bölgeleri:** üsten ve astronotun konumundan Dijkstra ile varış süreleri; yeşil / sarı / kırmızı eşikleri bölüm 3.3'te. Tarayıcıda 256×256 grid, 100 ms altı.
- **Dönüş noktası:** rotada "bu noktaya kadar harcanan + üsse dönüş" süresinin kalan O₂'ye eşit olduğu ilk nokta.
- **Arama alanı:** son konumdan kalan O₂ ile ulaşılabilir hücreler; olasılık ∝ 1 / maliyet. İHA rotası: alanı çevreleyen dikdörtgen üzerinde zikzak, şerit aralığı = kamera görüş genişliği.
- **Mars saati:** Mars24 (Allison ve McEwen 2000): Mars Sol Tarihi → Koordineli Mars Saati → Jezero yerel saati (boylam/15).
- **Gecikme:** basit Kepler yörünge elemanlarıyla Dünya ve Mars konumu → mesafe / ışık hızı.

### YOLO planı

- 640×640 karolar, 150–200 karo, 2 sınıf: `kaya`, `kum_dalgasi`
- `yolov8n` ya da `yolov8s`, 50–80 epoch, arka planda
- Çıktı: karo başına yoğunluk → `hazard_ml.png` ve grid maliyetine eklenir
- Sunuma: mAP, örnek tespit görselleri, "NOAH-H ve SPOC'un hafif, açık kaynak eşdeğeri"
- **Doğrulama:** Perseverance'ın gerçek güzergâhındaki hücrelerin yüzde kaçı bizim haritamızda "geçilebilir"?

## 6. Öncelikler

| Katman | İçerik |
| --- | --- |
| **Mutlaka** | Küre + Jezero uçuşu, eğim/termal/jeoloji katmanları, astronot profili (2 kişi), üst bar saatleri ve gecikme, nokta tarihçeleri, rota çizme + istatistik, her zaman açık O₂ bölgeleri |
| **Olmalı** | YOLO katmanı + füzyon skoru, EVA planlayıcı (duraklar, zaman çizelgesi, dönüş noktası, Go/No-Go), canlı yürüyüş + nabız, Hayatta Kal modu |
| **Bonus** | Perseverance güzergâhıyla doğrulama, telsiz görüş analizi, Gale ikinci bölge testi, Worldview kapanış sahnesi, internetsiz mod, rota uçuşu |

Saatlik plan, kontrol noktaları ve kesme sırası: docs/GOREV_KARTLARI.md.

## 7. Demo ve sunum

**Organizatör kuralları:**
- 7 slayt, 5 dk sunum + 2 dk soru-cevap.
- Video en fazla 30 sn. Canlı demo yok, demo video ile gösterilir.
- Jüri veri hakimiyetini ölçüyor: temizleme, gereksiz verinin atılması, normalizasyon, öğrenme yöntemleri. Bu yüzden veri hattı ve yöntemler iki ayrı slayt.
- Slaytlarda ve uygulamada NASA logosu, bayrağı veya görev arması yok. Kaynaklar metin olarak yazılır.

**Konuşmacılar:** Hikâye ve kapanışı Elif, veri ve yöntemleri Elif, demo ve doğrulamayı Gözde anlatır.

### Slayt akışı (toplam 5:00)

1. **Hikâye (0:45):**
   - Apollo 14, Opportunity, Spirit.
   - Kapanış sorusu: "Houston 14 dakika uzakta. Kim 'geri dön' diyecek?"
2. **MarsTrail (0:30):**
   - Problem: Veri onlarca göreve dağınık. Dönüş kuralı hâlâ sabit hızla hesaplanıyor. NASA'nın kendi saha testinde gerçek süre tahminden uzun çıktı.
   - Çözüm: "Hazırlan, planla, yürü, hayatta kal." Dört aşama tek ekranda.
3. **Veri hattı (0:50):**
   - DATA_PIPELINE.md'deki özet tablo: 8 veri seti, ham boyut → atılan → son boyut → yöntem.
   - Önce/sonra görselleri (figures/).
   - Vurgular: 3 projeksiyonun birleştirilmesi, NoData temizliği, %2–98 normalizasyon, kaynak haritadaki hataların düzeltilmesi.
4. **Yöntemler (0:50):**
   - Füzyon formülü ve fusion.png.
   - YOLOv8: veri seti, sınıflar, mAP, örnek tespitler.
   - Tobler hız modeli, Dijkstra ile O₂ bölgeleri, dönüş noktası.
   - Varsayımlar açıkça yazılır.
5. **Demo videosu (0:40):**
   - 30 sn video ve 10 sn giriş/çıkış cümlesi.
   - Video senaryosu aşağıda.
6. **Doğrulama (0:35):**
   - Perseverance'ın gerçek yolu (D2) haritamızda yüzde kaç geçilebilir? Rastgele hücrelerle kıyas.
   - YOLO val sonuçları.
   - Grid'deki süreler (üs → Three Forks 73 dk, Cheyava Falls 278 dk: kırmızı bölge).
7. **Etki ve YZ beyanı (0:30):**
   - Kask içi ekran, Artemis'e uyarlama.
   - Ay · Artemis: aynı sistem Ay güney kutbu yürüyüşlerine uyarlanabilir.
   - YZ kullanım beyanı: Claude Code, insan denetiminde kod ve veri işleme. Ekip adları.

### Demo videosu senaryosu (en fazla 30 sn)

| Süre | Ekranda |
| --- | --- |
| 0–5 sn | Küre → "Jezero'ya git". Üst barda Sol, Jezero saati, "Dünya X dk uzakta". |
| 5–10 sn | Ayşe'nin profili; O₂ bölgeleri zaten açık. Delta pinine tıklanır: tarihçe ve Perseverance'ın o Sol'deki fotoğrafı. |
| 10–16 sn | YOLO katmanı açılır. Plan: üs → delta → Three Forks → üs. Zaman çizelgesi, dönüş noktası, Go/No-Go yeşil. |
| 16–24 sn | Yürüyüş ×60. Nabız 150'ye çekilir, **bölgeler gözle görülür şekilde daralır**, dönüş noktası uyarısı çıkar. |
| 24–30 sn | "Telsiz koptu": arama alanı, İHA zikzak rotası, Ali'ye kurtarma rotası. |

### Hazır cevaplar

| Soru | Cevap |
| --- | --- |
| Mars'ta GPS yok, konumu nasıl biliyorsunuz? | Giysi IMU'su, habitat ve rover radyo sinyali, yer şekli eşleştirme. Demoda konum simüle ediliyor. |
| Bu NASA'da zaten var mı? | SEXTANT ve Minerva gibi araçlar var; biz canlı sarf malzemesi güncellemesi, dinamik dönüş sınırı, kendi tehlike modelimiz ve kurtarma modunu açık veriyle tek araçta birleştirdik. |
| Formüllerin kaynağı? | Tobler yürüyüş formülü, Mars ve giysi için düzeltildi; varsayımlar açık, gerçek EVA verisiyle kalibre edilebilir. |
| Model ne kadar iyi? | mAP ve örnek görseller; (varsa) Perseverance güzergâhı doğrulama yüzdesi. |
| İnternet yokken? | Veri cihazda; habitat ağı varken ekip senkronize olur. |

## 8. Kaynaklar

- Benzer çalışmalar: [SEXTANT tezi](https://dspace.mit.edu/handle/1721.1/59560) · [SEXTANT saha testi](https://core.ac.uk/download/17204791.pdf) · [SEXTANT + xGDS](https://dspace.mit.edu/handle/1721.1/119309) · [Minerva / BASALT](https://pmc.ncbi.nlm.nih.gov/articles/PMC6442304) · [SPOC ve termal eylemsizlik](https://arxiv.org/pdf/1805.05451) · [NOAH-H Jezero](https://oro.open.ac.uk/84535) · [AstroMind](https://dev.to/walsal201/astromind-4ji4) · [NASA SUITS](https://spencer-l.github.io/assets/pdf/NASA_SUITS_Retrospective.pdf)
- Hikâye: [Apollo 14 – Astronomy](https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/) · [Apollo 14 – NASA raporu](https://ntrs.nasa.gov/api/citations/19710012245/downloads/19710012245.pdf) · [Opportunity Purgatory](https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune) · [Spirit](https://www.space.com/18766-spirit-rover.html) · [Walkback limiti (TUM)](https://ttu-ir.tdl.org/handle/2346/74208) · [Apollo 15 EVA kısıtları](https://www.nasa.gov/wp-content/uploads/static/history/alsj/19790073512_1979073512.pdf) · [Mars iletişim gecikmesi](https://internetinspace.pages.dev/space/mars)
- Veri: [Mars Trek](https://trek.nasa.gov/mars/) · [Mars Trek WMTS](https://api.nasa.gov/mars-wmts/catalog) · [USGS jeoloji](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) · [USGS Jezero mozaiği](https://astrogeology.usgs.gov/search/map/mars-2020-jezero-crater-landing-site-products) · [Perseverance ham görüntüleri](https://mars.nasa.gov/mars2020/multimedia/raw-images/) · [Curiosity rotası](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) · [Worldview](https://worldview.earthdata.nasa.gov/)
