# MarsTrail – Sunum (E14)

7 slayt · 5:00 sunum + 2:00 soru-cevap · video en fazla 30 sn.

**Konuşmacılar:** Elif: 1, 2, 3, 4 ve 7. Gözde: 5 ve 6.

**Kurallar:**
- NASA logosu, bayrağı ya da görev arması kullanılmaz.
- Görsellerin altına kaynak metin olarak yazılır, ör. "Veri: NASA/JPL-Caltech, USGS, University of Arizona (HiRISE)".
- Sayıların hepsi betiklerden geliyor: `docs/DATA_PIPELINE.md` ve `docs/figures/*.json`. Slayta elle sayı yazılmaz; buradan kopyalanır. Denetim: [SAYI_DENETIMI.md](SAYI_DENETIMI.md) (`scripts/audit_numbers.py`).

**Dosyalar:**
- **`docs/sunum/MarsTrail.pptx`** (`scripts/make_slides.py`): Calibri yazı tipi, konuşma metinleri notlarda.
  - Her slaytta geçiş var: 3. ve 6. slaytta push, diğerlerinde fade.
  - Grafikler slayt açılınca yakınlaşarak gelir; büyük sayılar ve kartlar tıklamayla sırayla belirir.
  - Slayt 5'te `docs/sunum/demo.mp4` gömülü; ilk tıklamada baştan oynar, ikinci tıklama kartları getirir. Bu düzen Gözde'nin `MarsTrail_Elif_demo.pptx` dosyasıyla aynı.
  - Tıklama sayısı: slayt 1'de 2, slayt 2'de 3, slayt 3'te 1, slayt 4'te 1, slayt 5'te 2 (video + kartlar), slayt 6'da 3, slayt 7'de 3.
- **`docs/sunum/MarsTrail_sunum.mp4`** (`scripts/make_video.py`): 2:24, 1920x1080, sessiz, Türkçe altyazılı. Demo bölümü 20 sn. Seslendirme sonra eklenecek.

| # | Slayt | Süre | Konuşmacı | Birikimli |
| --- | --- | --- | --- | --- |
| 1 | Hikâye | 0:45 | Elif | 0:45 |
| 2 | MarsTrail nedir | 0:30 | Elif | 1:15 |
| 3 | Veri hattı | 0:50 | Elif | 2:05 |
| 4 | Yöntemler | 0:50 | Elif | 2:55 |
| 5 | Demo | 0:40 | Gözde | 3:35 |
| 6 | Doğrulama | 0:35 | Gözde | 4:10 |
| 7 | Etki + YZ beyanı | 0:30 | Elif | 4:40 |
| | Pay (geçiş, nefes) | 0:20 | | 5:00 |

---

## Slayt 1 · Hikâye: "21 metre" (0:45, Elif)

**Başlık:** 21 metre kalmıştı

- 1971, Apollo 14: Shepard ve Mitchell, Cone Krateri'nin kenarını bulamadı. Nabız 150, oksijen azalıyor, Houston geri çağırdı. Kenara yaklaşık 21 m kalmıştı.
- 2005, Opportunity: ~30 cm yüksekliğinde bir kum dalgasında 5 haftadan fazla mahsur kaldı.
- 2009, Spirit: Sert kabuğun altındaki yumuşak kuma gömüldü, bir daha hareket edemedi.
- Mars'ta Houston'a bir mesaj 3 ila 22 dakikada gidiyor (bugün 10,9 dk).

**Konuşma metni:**
> "1971. Ay. İki astronot bir krateri arıyor. Haritadaki işaretleri bulamıyorlar, kalpleri dakikada 150 atıyor, oksijen azalıyor. Houston 'geri dönün' diyor ve dönüyorlar. Yıllar sonra fotoğraflar gösterdi ki hedeflerine 21 metre kalmıştı.
> 2005. Mars. Opportunity otuz santimlik bir kum dalgasına takılıyor, beş hafta çıkamıyor. 2009'da Spirit kuma gömülüyor ve bir daha hiç hareket edemiyor.
> Şimdi bunları Mars'ta bir insanın başına getirin. Houston on dakika uzakta. Kim 'geri dön' diyecek?"

**Görsel:**
- Tam ekran koyu arka plan, üç tarih alt alta (1971 · 2005 · 2009).
- Son cümle büyük harfle: "Kim 'geri dön' diyecek?"
- İsteğe bağlı: uygulamadaki Apollo 14 hikâye kartının ekran görüntüsü (Gözde'den). Görev arması ya da logo yok.

**Not:** Gecikme sayısını sunum günü uygulamanın üst barından al. 15 Kasım 2026 için E8 testi 10,9 dk gösteriyor.

---

## Slayt 2 · MarsTrail nedir (0:30, Elif)

**Başlık:** Hazırlan · Planla · Yürü · Hayatta kal

- **Sorun:** Mars verisi onlarca göreve dağılmış durumda. Apollo'nun "yürüyerek dönebileceğin mesafe" kuralı sabit hız ve ortalama tüketimle hesaplanıyordu. MIT'nin SEXTANT saha testinde gerçek yürüyüş süresi tahminden uzun çıktı.
- **Çözüm:** Astronotun nabzına, yüküne, oksijenine ve araziye göre **canlı** hesaplanan dönüş sınırı.
- **Dört aşama tek ekranda:** profil ve sarf malzemesi → rota ve Go/No-Go → yürüyüş ve dönüş noktası → kayıp astronot ve İHA araması.
- Backend yok: tarayıcıda, açık veriyle çalışıyor. Odak bölge Jezero Krateri; iki astronot, Ayşe ve Ali.

**Konuşma metni:**
> "MarsTrail, Mars'ta bir yürüyüşü hazırlıktan acil duruma kadar yöneten bir görev sistemi. Apollo'da dönüş sınırı sabit bir hızla hesaplanıyordu. Biz onu canlı yapıyoruz: astronotun nabzı, taşıdığı yük, kalan oksijeni ve önündeki arazi değiştikçe 'buradan dönebilir miyim' sorusunun cevabı da değişiyor. Dört aşama tek ekranda: hazırlan, planla, yürü, hayatta kal."

**Görsel:**
- Solda dört aşamanın simge şeridi.
- Sağda uygulamanın ana ekranı: `docs/figures/ui_1_plan_go.png`.
- Telefon görünümü küçük ek olarak: `docs/figures/ui_5_phone_plan.png`.

---

## Slayt 3 · Veri hattı: 8 veri seti (0:50, Elif)

**Başlık:** ~6 GB ham veri → 1,3 MB'lık grid

| # | Veri seti | Ham | Attığımız | Son | Yöntem |
| --- | --- | --- | --- | --- | --- |
| D1 | Perseverance konumları | 708 nokta × 23 alan | 19 alan | 5 pin konumu | Sol eşleme |
| D2 | Sürüş izi | 559 çizgi, 36.661 köşe | 11.430 köşe (alan dışı) | 397 grid hücresi | Rasterize → doğrulama |
| D3 | Ingenuity uçuşları | 72 uçuş | 71 | 1 tarih pini | Seçim |
| D4 | THEMIS termal eylemsizlik, 100 m | 792.100 px | 757.900 px (298.150 NoData dahil) | 0–1 katman | Reprojeksiyon, %2–98 normalizasyon |
| D5 | CTX DEM, 20 m | 22,6 M px | 21,77 M px alan dışı, 13.977 NoData | eğim + gölgeli kabartma | 20 m'de eğim |
| D6 | SIM 3464 jeoloji haritası | 1304 poligon | 1186 poligon; kaynakta 2 hata düzeltildi | 10 birim | Rasterize, katsayı tablosu |
| D7 | Perseverance ham fotoğrafları | 1795 kayıt | 1785 | 10 fotoğraf | Eleme hunisi + doku eşiği |
| D8 | HiRISE 25 cm mozaiği | 5,47 GB | 1444 NoData karo, 58 dokusuz karo | 250 etiketli karo + 1146 karoda çıkarım | Karolama, birim tabanlı seçim |

- **Üç projeksiyon** (THEMIS, CTX, HiRISE) tek bir 256 × 256 grid'de birleşti (70 m hücre).
- **NoData temizliği:** HiRISE'ta 2590 karonun 1444'ü boştu ve atıldı.
- **Normalizasyon:** Termal katman %2–98 dilimleriyle 0–1 aralığına çekildi.
- **Kaynak hatası:** Jeoloji haritasında 2 kaynak hatası bulundu ve düzeltildi.

**Konuşma metni:**
> "Sekiz açık veri setiyle çalıştık. Toplam yaklaşık altı gigabayt ham veri. Her adımda neyi neden attığımızı betikle ölçtük, elle sayı yazmadık. Termal, yükseklik ve 25 santimlik görüntü üç farklı projeksiyonda geliyor; hepsini 70 metrelik tek bir grid'de birleştirdik. HiRISE mozaiğinde 2590 karonun 1444'ü boştu, onları attık. Termal veriyi aykırı uçları kırparak 0–1'e normalize ettik. Jeoloji haritasında iki kaynak hatası bulup düzelttik. Perseverance'ın gerçek sürüş izini ise modele vermedik, doğrulama için ayırdık."

**Görsel:**
- Tablo slaytın üst yarısı.
- Alt yarıda üç küçük önce/sonra görseli: `docs/figures/d4_thermal_normalize.png`, `docs/figures/d5_dem_crop.png`, `docs/figures/d6_geology_crop.png`.
- Kaynak satırı: "Veri: NASA/JPL-Caltech, USGS, ASU (THEMIS), University of Arizona (HiRISE)".

---

## Slayt 4 · Yöntemler (0:50, Elif)

**Başlık:** Füzyon skoru · kendi YOLO modelimiz · O₂ bölgeleri

- **Füzyon skoru:**
  - `skor = 0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)`.
  - Eğim > 25° ya da skor > 0,8 olan hücre geçilmez.
  - Hücre süresi Tobler yürüyüş formülünden: Mars ve giysi için × 0,6, yük kadar yavaşlama.
- **YOLOv8, 250 karoyu kendimiz etiketledik:**
  - 5 koşuluk ablation (m/s × 3/2 sınıf + karo sınıflandırıcı). Seçilen: YOLOv8s, 2 sınıf.
  - Train/val bölmesi bitişik karo gruplarıyla yapıldı (sızıntı yok).
  - 2. parti etiketlerle hücre dengeli doğruluğu 0,69 → 0,78. Karar kuralı sonuçlar görülmeden yazıldı.
  - Model kutu çizmek için değil, hücre başına kum ve kaya **yoğunluğu** için kullanılıyor.
- **O₂ bölgeleri:**
  - Dijkstra ile gidiş + dönüş süresi hesaplanıyor. Yeşil: süre ≤ O₂ / 1,25. Sarı: süre ≤ O₂. Kırmızı: dönüş yok.
  - O₂ tüketimi nabızla büyüyor (nabız 150'de × 1,6).
  - Ayşe'nin nabzı 85'ten 150'ye çıkınca yeşil bölge 130 km²'den 47 km²'ye küçülüyor.
- **Varsayımlar açık:** Katsayılar kalibre edilmedi, kodda ve belgede "varsayım" olarak işaretli.

**Konuşma metni:**
> "Her hücreye bir zorluk skoru veriyoruz: eğim, kum, kaya ve termal eylemsizlik. Termal eylemsizlik Spirit'i gömen yumuşak kumu gösteriyor. Kum ve kayayı 25 santimlik görüntüde kendi eğittiğimiz YOLO modeliyle buluyoruz. 250 karoyu kendimiz etiketledik, beş farklı kurulumu karşılaştırdık ve komşu karoları aynı tarafa koyarak veri sızıntısını engelledik. Modeli kutu çizmek için değil, 70 metrelik hücrede kum ve kaya yoğunluğu çıkarmak için kullanıyoruz. Bu skor ve Tobler yürüyüş formülüyle her hücrenin süresini, Dijkstra ile de oksijen bölgelerini hesaplıyoruz. Ayşe'nin nabzı 85'ten 150'ye çıkınca güvenli bölge 130 kilometrekareden 47'ye iniyor."

**Görsel (2 × 2 ızgara):**
1. Füzyon: `docs/figures/fusion.png`.
2. Model karşılaştırması: `docs/figures/e6v2_compare.png`.
3. Örnek tespitler: `docs/figures/e6v2_s2_val_batch0_pred.jpg`, gerekirse 4 karo kırpılır.
4. O₂ bölgeleri: `docs/figures/e8_zones.png`.

Formül slaytın altında tek satır olarak yazılır.

---

## Slayt 5 · Demo (0:40, Gözde)

**Başlık:** Sol 34, Jezero: Ayşe deltaya yürüyor

- Plan: üs → delta önü → Three Forks → üs. Toplam 5,52 km, 243 dk, dönüşte 249 dk O₂ kalıyor → **GO**.
- Aynı plan O₂ 220 dk ve nabız 150 ile: dönüş noktası T+67 dk'ya geliyor, plan **NO-GO** oluyor.
- Telsiz koptu (20 dk önce): en olası arama alanı %50 olasılıkla 0,25 km². İHA %50 olasılığı 11,6 dk'da tarıyor.
- Ali'nin kurtarma rotası 116/480 dk O₂ ile YEŞİL bölgede.

**Konuşma metni** (10 sn giriş + 30 sn video):
> Giriş: "Sol 34. Ayşe deltadan numune alacak, Ali üste. Şimdi göreceğiniz her sayı canlı hesaplanıyor."
>
> Video sırasında (kısa vurgular): "O₂ bölgeleri her zaman açık… plan yeşil, GO… nabız 150: bölgeler daralıyor, dönüş noktası öne geliyor… telsiz koptu: arama alanı, İHA rotası, Ali'nin kurtarma rotası."

**Görsel:** Video slayta gömülü (`docs/sunum/demo.mp4`, 29,9 sn, ilk tıklamada oynar). Senaryo `docs/PLAN.md` bölüm 7'de.

| Süre | Ekran |
| --- | --- |
| 0–5 sn | Küre → Jezero. Üst barda Sol, saat, gecikme. |
| 5–10 sn | Nokta kartı, O₂ bölgeleri: delta pininin tarihçesi ve Perseverance fotoğrafı. |
| 10–16 sn | YOLO katmanı (`hazard_ml`). Plan, zaman çizelgesi, GO. |
| 16–24 sn | Yürüyüş × 60. Nabız 150, bölgeler daralır, dönüş noktası uyarısı. |
| 24–30 sn | Telsiz koptu: arama alanı, İHA zikzak rotası, Ali'nin rotası. |

Yedek ekran görüntüleri (video açılmazsa): `docs/figures/ui_1_plan_go.png`, `ui_2_plan_nogo.png`, `ui_3_walk.png`, `ui_4_rescue.png`.

---

## Slayt 6 · Doğrulama: Perseverance'ın gerçek rotası (0:35, Gözde)

**Başlık:** Rover kum dediğimiz yerden geçmemiş

- **Soru:** Rover ekibi rotayı tehlikeden kaçınarak seçti. Skorumuz araziyi doğru okuyorsa, rotanın geçtiği hücreler daha kolay görünmeli.
- **Ölçü:** AUC = P(rota hücresi daha düşük skorlu). 0,5 hiç ayırt etmemek demek.
  - HiRISE kapsamında (52 rota hücresi) YOLO'suz skor **0,498**, yani yazı-tura.
  - YOLO eklenince **0,649**. Bootstrap ile farkın aralığı +0,12…+0,18; 1000 örneğin hiçbirinde fark ≤ 0 değil.
- **Kum:** Rotadaki 52 hücrenin **hiçbiri** kumlu değil; çevrede bu oran **%49**.
- **Model val sonuçları** (eğitimde hiç görülmemiş 51 karo): hücre dengeli doğruluğu 0,78, kum hücresi recall 0,91.
- **Dürüst sınırlar:**
  - Kaya rotayı ayırt etmiyor (AUC 0,51).
  - 397 rota hücresinin yalnızca 52'si HiRISE kapsamında; tüm alanda etki küçük (0,562 → 0,571).
  - Rover bir insan değil.

**Konuşma metni:**
> "Peki model doğru mu? Bunu Perseverance'ın gerçekten sürdüğü yolla test ettik; bu veriyi modele hiç vermedik. Mantık şu: rover ekibi tehlikeli yerden geçmez. 25 santimlik görüntünün olduğu bölgede, görüntü verisi olmadan skorumuz rotayı ayırt edemiyordu: AUC 0,50, yazı-tura. Kendi YOLO modelimizi ekleyince 0,65'e çıktı. Rotanın geçtiği 52 hücrenin hiçbirinde kum yok, çevredeki hücrelerin yarısı kumlu. Rover, modelimizin kum dediği yerden kaçınmış. Kayada aynı sinyali bulamadık, bunu açıkça söylüyoruz."

**Görsel:**
- Ana: `docs/figures/e10_validation.png`.
- Köşede rota üstünde YOLO yoğunluk katmanı: `docs/figures/e10_density.png`.
- Büyük iki sayı: "0,50 → 0,65" ve "%0 ↔ %49".

**Not:**
- İlk taslakta 0,626 ve %3,8 / %52,6 vardı. Bunlar 1. parti modelinin sayıları.
- 2. parti etiketlerle eğitilen güncel modelin sayıları 0,649 ve %0 / %49,3 (`docs/figures/e10_validation.json`).
- Sunumda güncel olanlar kullanılır.

---

## Slayt 7 · Etki + YZ beyanı (0:30, Elif)

**Başlık:** Nerede olduklarını bilecekler

- **Artemis ve Mars:** Telefon görünümü hazır, kask içi ekrana uyarlanabilir. Gecikmeli iletişimde kararı sistem veriyor.
- **Dünya'da:** Aynı arama ve kurtarma mantığı afet bölgesinde de çalışıyor: kayıp kişi + kalan süre + arazi → arama alanı ve İHA rotası.
- **Açık:** Açık veri, açık kod, backend gerekmiyor.
- **YZ beyanı:**
  - Kod ve veri işleme betikleri ekip denetiminde Claude Code ile yazıldı.
  - Etiketlerin ön taslağı Roboflow Auto Label ile çıkarıldı; 250 karonun hepsi Elif tarafından elle kontrol edildi.
  - Fikir, hikâye, veri seçimi, formül ve eşik kararları, etiket tanımları ve doğrulama ekibe ait.
- **Ekip:** Elif (veri, model, algoritmalar), Gözde (arayüz).

**Konuşma metni:**
> "Apollo 14 astronotları nerede olduklarını bilmedikleri için döndü. MarsTrail ile bilecekler: nerede olduklarını, ne kadar ileri gidebileceklerini ve ne zaman dönmeleri gerektiğini. Aynı sistem bugün Dünya'da bir afet bölgesinde de çalışabilir. Kodu ve betikleri yapay zekâ desteğiyle yazdık; etiketleri, kararları ve doğrulamayı biz yaptık. Teşekkürler."

**Görsel:**
- Telefon görünümünde kurtarma ekranı: `docs/figures/ui_6_phone_rescue.png`.
- Altta küçük YZ beyanı kutusu; tam metin `docs/TESLIM.md` bölüm 4'te.

---

## Jüri için olası 10 soru

| # | Soru | Kısa cevap |
| --- | --- | --- |
| 1 | Hangi veriyi neden attınız? | Alan dışı pikseller (D4'te 757.900 px), NoData karolar (D8'de 2590'dan 1444), doku içermeyen 58 karo (etiket için), kullanılmayan alanlar (D1'de 23 alanın 19'u). Her atılan sayı betikle ölçüldü, nedeniyle birlikte `DATA_PIPELINE.md`'de yazılı. |
| 2 | mAP50 0,33 düşük değil mi? | Kutu düzeyinde düşük, çünkü kum alanı gibi bölge ölçekli nesnelerin sınırı belirsiz. Biz modeli kutu için değil 70 m'lik hücre yoğunluğu için kullanıyoruz. O ölçekte dengeli doğruluk 0,78. Asıl ölçü de rota doğrulaması: AUC 0,50 → 0,65. |
| 3 | Veri sızıntısını nasıl önlediniz? | Komşu karolar aynı sahneyi paylaştığı için 8-komşulukla gruplayıp her grubu tek tarafa koyduk. İlk bölmemizde 30 val karosunun 8'inin train'deki bir karoya bitişik olduğunu bu sayede bulduk ve düzelttik. Rota verisi (D2) modele hiç verilmedi. |
| 4 | Neden 2 sınıf, neden yolov8s? | 5 kurulumu aynı val'de karşılaştırdık. kaya_alani'yi ayrı öğrenmek ölçülebilir fayda getirmedi. yolov8s, yolov8m ile aynı doğrulukta ama yarısından küçük ve iki kat hızlı. 150 karoda büyük model ezberlemeye başladı. |
| 5 | Füzyon ağırlıkları nereden geliyor? | Varsayım: eğim en büyük tehlike (0,4), ardından kum (0,25). Jeoloji ile YOLO'yu eşit ağırlıkla birleştirdik, çünkü ikisini kalibre edecek yer-gerçeği yok. Ağırlıklar kodda tek yerde tanımlı; gerçek EVA verisiyle kalibre edilebilir. |
| 6 | Rover rotası astronot için doğru bir referans mı? | Tam değil: tekerlek kuma insandan daha duyarlı ve rota bilim hedeflerine de gidiyor. Ama elimizdeki tek "gerçek tehlikeden kaçınma" verisi bu. Ayrıca ölçtüğümüz şey tam olarak kumdan kaçınma ve astronot için de geçerli (Opportunity, Spirit). |
| 7 | Kaya neden işe yaramadı? | Kaya tespiti zayıf (kaya mAP50 0,20). 2. partide model iki kat fazla kaya bulmasına rağmen rota sonucu değişmedi. Yani rover ekibi metre ölçeğindeki kayayı 70 m ölçeğinde önemsemiyor olabilir. Bunu bir sınırlama olarak raporluyoruz. |
| 8 | HiRISE'ın kapsamadığı yerde ne oluyor? | Model yalnızca 25 cm'lik mozaiğin kapsadığı ~29 km²'de çalışıyor. Kapsam dışında skor jeoloji, eğim ve termalden geliyor; o hücrelerde ML terimi yok sayılıyor, sahte değer üretilmiyor. |
| 9 | Etiketleri yapay zekâ mı yaptı? | Ön taslak Roboflow Auto Label'dan geldi. 250 karonun hepsini Elif tek tek düzeltti ve sınıf tanımlarını belirledi. Bir tutarsızlığı da kendimiz bulduk: 1. partide küçük çukur kümeleri tutarlı etiketlenmemişti. Model denetimi bunu ölçtü: etiketsiz engel 1. partide karo başına 2,5 kat daha sık. |
| 10 | Mars'ta GPS yok, konumu nasıl biliyorsunuz? Bu NASA'da zaten var mı? | Konum giysi IMU'su, habitat/rover radyo sinyali ve arazi eşleştirmeyle bulunur; demoda simüle ediliyor. SEXTANT ve Minerva gibi araçlar var. Biz canlı sarf malzemesi, dinamik dönüş sınırı, kendi tehlike modelimiz ve kurtarma modunu açık veriyle tek araçta birleştirdik. |

**Yedek sayılar** (soru gelirse):
- Çıkarım: 1146 karo 17 sn'de.
- Tarayıcıda O₂ bölgeleri 100 ms altında; arama alanı 47 ms.
- Rota süreleri: üs → Three Forks 73 dk, üs → Cheyava Falls 279 dk (480 dk O₂ ile kırmızı bölge).
