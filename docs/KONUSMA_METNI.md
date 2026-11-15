# Konuşma metni · MarsTrail_sunum_v2.mp4 (5:00)

Video sessiz akarken okunacak metin. Zaman kodları videonun kendisinden ölçüldü (`scripts/sunum_v2/edit_video.py` kare numaraları). Her bölümün yanında kelime sayısı ve saniyede düşen kelime var; rahat, net bir sunum için hedef saniyede 2,0–2,5 kelime.

**Okuma kuralları**
- **Kalın** yazılanlar vurgu. `/` kısa nefes, `//` ekrandaki değişikliği bekle.
- Sayıları ekranda görünmeden önce söyleme. Her bölümün ilk cümlesi, ekrandaki başlıkla aynı anda başlasın.
- Geride kalırsan önce *(kısaltılabilir)* işaretli cümleyi atla. Asıl sayıları atlama.

**Sayıların kaynağı**
- Hepsi [SAYI_DENETIMI.md](SAYI_DENETIMI.md)'de kaynağıyla eşleştirildi.
- Apollo 14 ~30 m: NASA PIA12897 (LROC/ASU, 2009).
- Houston 10,9 dk: bugünkü uzaklık (`marstime.js`).

---

## 0:00–0:14 · Apollo 14 (ekranda: Ay, nabız 150, "Geri dönün", ~30 m)

> **1971, Ay.** Shepard ve Mitchell, Cone Krateri'nin kenarını arıyor. Haritadaki işaretleri bulamıyorlar. / Shepard'ın nabzı **150**'ye çıkıyor. // Houston: "Geri dönün." Dönüyorlar. // Yıllar sonra uydu fotoğrafı gösterdi: kenara yalnızca **30 metre** kalmıştı.

*Not: "30 metre" sayaç ~0:12,6'da duruyor; tam o anda söyle.*

## 0:14–0:28 · Opportunity ve Spirit

> **2005, Mars.** Opportunity, **30 santimlik** bir kum dalgasına saplandı; beş haftadan fazla çıkamadı. / **2009**'da Spirit, sert kabuğun altındaki yumuşak kuma gömüldü ve bir daha hiç hareket edemedi.

## 0:28–0:45 · Soru (ekranda: "Mars'ta Houston 3–22 dakika uzakta. Kim 'geri dön' diyecek?")

> Senaryolar farklı, sonuç hep aynı. Sebep teknik yetersizlik değildi: **durum değişti, plan anında güncellenemedi.** / Rover saplanırsa yenisi gönderilir. Ama ya o bir astronotsa? // Mars'ta Houston **3 ile 22 dakika** uzakta; bugün 10,9 dakika. / O dakikalarda kim "geri dön" diyecek?

## 0:45–1:14 · MarsTrail (ekranda: logo, uygulama, 130 → 47 km², dört adım)

> Bizim cevabımız: **MarsTrail.** / Üslerin kuralı basit: "Dönebileceğin kadar uzaklaş." Biz bu kuralı sabit bir hızla değil; **araziye, yüke, kalan oksijene ve astronotun nabzına göre canlı** hesaplıyoruz. // Ayşe'nin nabzı 85'ten 150'ye çıktığında güvenli yeşil alanı **130 kilometrekareden 47'ye** iniyor. Bunu Dünya'yı beklemeden, o saniye görüyor. // Dört adım: **hazırlan, planla, yürü, ve beklenmedik anda hayatta kal.**

## 1:14–1:56 · Veri (ekranda: 8 veri seti tablosu; 1:24 "3 → 1", 1:26 "1444 / 2590", 1:30 normalizasyon)

> Bunu tahminle değil, **NASA'nın açık verisiyle** yaptık. Sekiz veri seti, yaklaşık **6 gigabayt**: Perseverance'ın 708 konum kaydı ve 46 kilometrelik sürüş izi, 72 Ingenuity uçuşu, THEMIS termal verisi, 20 metrelik yükseklik modeli, USGS jeoloji haritası, rover fotoğrafları ve 25 santimlik HiRISE görüntüleri. //
> **Üç farklı projeksiyonu** tek bir 70 metrelik ızgarada birleştirdik. // **2.590** HiRISE karosunun **1.444**'ü boştu, attık. // Termal veriyi aykırı uçları kırparak 0 ile 1 arasına çektik; jeoloji haritasında iki kaynak hatası bulup düzelttik. / Sonunda 6 gigabayttan, tarayıcıda çalışan **1,3 megabaytlık** bir harita kaldı. Hiçbir sayıyı elle yazmadık; hepsini betikle ölçtük.

## 1:56–2:46 · Yöntem (ekranda: katmanlar üst üste; 2:05 füzyon, 2:09 YOLOv8, 2:13 Tobler + Dijkstra, 2:17 varsayımlar)

> Gözle görünmeyeni görmek için katmanları üst üste koyduk: **eğim, kum, kaya ve termal.** Termal veri, Spirit'i gömen o yumuşak kumu yörüngeden gösteriyor. // Her hücreye 0 ile 1 arasında bir **zorluk skoru** veriyoruz. //
> Metre ölçeğindeki kumu ve kayayı görmek için **kendi YOLOv8 modelimizi** eğittik. 250 HiRISE karosunu ve **1.033 kutuyu** tek tek elle kontrol ettik. Beş farklı kurulumu karşılaştırdık. Komşu karoları hep aynı tarafa koyarak **veri sızıntısını** engelledik; ilk bölmemizde sekiz karonun sızdığını bu sayede yakaladık. Hücre düzeyinde dengeli doğruluk **yüzde 78.** //
> Son adım: **Tobler** yürüyüş formülü ve **Dijkstra** algoritmasıyla her hücre için gidiş-dönüş süresi. Nabız arttıkça oksijen tüketimi artıyor. / Sunucu yok; hesap tarayıcıda **100 milisaniyenin altında.** *(kısaltılabilir:)* Bütün katsayılar varsayım ve kodda tek yerde; gerçek veriyle kalibre edilebilir.

## 2:46–3:35 · Demo (ekranda: uygulama kaydı; alttaki altyazılarla eşleştir)

| Zaman | Ekranda | Söyle |
| --- | --- | --- |
| 2:46–2:52 | Mars saati, Sol 34, Dünya gecikmesi → Jezero, O₂ bölgeleri | "Sol 34, Jezero Krateri. Üstte Mars saati ve Dünya gecikmesi. **Yeşil, sarı, kırmızı oksijen bölgeleri** her an açık." |
| 2:52–2:56 | Nokta kartı: tarihçe + Perseverance fotoğrafı | "Her noktanın **tarihçesi** var: ne zaman keşfedildi, Perseverance oraya hangi Sol'de geldi, orada ne gördü." |
| 2:56–3:00 | YOLO katmanı: turuncu kum, kırmızı kaya | "Turuncu, modelimizin bulduğu kum; kırmızı, kaya." |
| 3:00–3:06 | **Rota çiz:** engeller, zorluk, yükseklik profili | "Ayşe **kendi rotasını çiziyor.** Sistem engelleri, zorluğu ve yükseklik profilini çıkarıyor; denenmemiş bir rotaysa uyarıyor." |
| 3:06–3:10 | Plan: Üs → Delta → Three Forks · GO | "Plan hazır: **GO.**" |
| 3:10–3:15 | Canlı yürüyüş → **not pini, bildirim** | "Yürüyüş başladı. Yolda bir kum dalgası görüyor, **not pini bırakıyor**; her olay anında bildirim olarak düşüyor." |
| 3:15–3:19 | Nabız 150 → güvenli bölge daralıyor | "Nabzı **150**'ye çıkıyor: güvenli alan daralıyor, dönüş noktası öne geliyor." |
| 3:19–3:21 | Telsiz koptu: arama alanı ve İHA | "Ve **telsiz kopuyor.** Son konumdan bir arama alanı çıkıyor; İHA zikzakla tarıyor." |
| 3:21–3:35 | Ali için kurtarma rotası: kendi O₂'si yetiyor mu? | "Ali için kurtarma rotası çiziliyor; **Ali'nin kendi oksijeni de yetiyor mu**, onu da hesaplıyor. // Geç fark edilirse sistem 'yetişilemez' demeyi de biliyor." |

*Not: 3:21–3:35 ekran uzun süre aynı kalıyor; acele etme, son cümleyi rahat söyle.*

## 3:36–4:10 · Doğrulama (ekranda: rota haritası; 3:38 AUC sayacı; 3:44 kumlu hücre; 3:48 %100)

> Peki haritamız doğru mu? / Perseverance'ın **gerçek sürüş izini** modele hiç vermedik; sonra karşılaştırdık. // YOLO olmadan skorumuz HiRISE bölgesinde rotayı ayırt edemiyordu: **0,498**, yani yazı tura. YOLO'yu ekleyince **0,649.** // Rover'ın geçtiği **52 hücrenin hiçbiri** bizim haritamızda kumlu değil; çevresinde bu oran **yüzde 49.** // Ve rotanın **yüzde 100**'ü bizim haritamızda geçilebilir. NASA ekibinin seçtiği yolu, bizim haritamız da güvenli buluyor.

## 4:10–4:40 · Etki (ekranda: Artemis ve Mars · Ay · Artemis · Açık; 4:20 "MarsTrail ile bilecekler" ve YZ beyanı)

> Hedefimiz burada kalmak değil. **Artemis**'le insanlar yeniden Ay'da, ardından Mars'ta yürüyecek. Aynı sistem **Ay'ın güney kutbundaki yürüyüşlere** uyarlanabilir. Bugün telefonda çalışıyor, yarın kask içi ekrana taşınabilir. // Sonraki adımlar: gerçek uzay yürüyüşü verisiyle kalibrasyon ve astronotların bıraktığı notlar onaylandıkça büyüyen bir **denenmiş rotalar** kütüphanesi. // Kodu yapay zekâ desteğiyle yazdık; etiketleri, kararları ve doğrulamayı biz yaptık.

## 4:40–5:00 · Kapanış (ekranda: MarsTrail, Teşekkürler, QR)

> Apollo 14 astronotları **nerede olduklarını bilmedikleri için** döndü. 2009'da uydu, ayak izlerinin kenardan 30 metre önce bittiğini gösterdi. / MarsTrail ile bilecekler. // Uygulama şu an canlı; **QR koddan** telefonunuzda deneyebilirsiniz. Teşekkür ederiz.

---

## Değişiklikler: ilk taslağa göre ne düzeltildi, neden

| Taslakta | Burada | Neden |
| --- | --- | --- |
| "Nabızları 150'ye çıkıyor" | "Shepard'ın nabzı 150" | Kaynak (Apollo 14 görev raporu) Shepard'ın nabzını veriyor. |
| "Sunucu yok, internet gerekmiyor" | "Sunucu yok" | Taban harita (Mars Trek) ve Cesium internetten geliyor; "internet gerekmiyor" jüri denerse yanlış çıkar. |
| "Hücre doğruluğumuz %78" | "Dengeli doğruluk %78" | Ölçülen değer dengeli doğruluk (0,778). Düz doğruluk 0,80. |
| "NASA'nın bilim insanları: bugünkü haritalarla ulaşırlardı" | "2009'da uydu, izlerin kenardan 30 m önce bittiğini gösterdi" | İlk cümlenin kaynağını bulamadık. İkincisi NASA PIA12897'de yazıyor. |
| "Yeni rotada her an kaydediliyor, not, fotoğraf, inceleniyor, onaylanıyor" | "Rota çiz + uyarı; not pini + bildirim"; inceleme/onay **sonraki adım** | Uygulamada inceleme ve onay yok. Fotoğraf yükleme yok, pin yalnızca metin. Çizilen rota kalıcı kaydedilmiyor. Jüri denerse görülür. |
| "Dünya'da afet" | "Ay · Artemis" | İstendiği gibi değiştirildi (video ve belgeler). |
