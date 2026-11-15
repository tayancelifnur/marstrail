# Jüri soruları ve cevapları

2 dakikalık soru-cevap için. Her cevap 20–30 saniyede söylenecek uzunlukta. Sayıların hepsi [SAYI_DENETIMI.md](SAYI_DENETIMI.md)'de kaynağıyla eşleştirildi.

**Kim cevaplar:** Veri, model ve algoritma soruları Elif'e; arayüz ve demo soruları Gözde'ye.

## Veri

**1. Hangi veriyi neden attınız?**
Atılan her şeyi betik ölçtü ve gerekçesi [DATA_PIPELINE.md](DATA_PIPELINE.md)'de yazılı.
- Alan dışı pikseller atıldı.
- HiRISE mozaiğinde 2590 karonun 1444'ü boştu (NoData), atıldı.
- Doku içermeyen 58 karo etiketlemeye girmedi.
- Perseverance konum dosyasında 23 alanın yalnızca 4'ü kullanıldı.
- Ham veri ~6 GB, uygulamaya giden grid 1,3 MB.

**2. Normalizasyonu nasıl yaptınız?**
- **Termal eylemsizlik:** %2–98 dilimlerine kırpılıp 0–1'e çekildi. Aykırı uçlar ölçeği bozmasın diye bu yöntem seçildi; kırpılan piksel sayısı da ölçüldü.
- **Eğim:** 25°'ye bölünüyor, çünkü astronot için geçilmezlik sınırı bu.
- **Sonuç:** Dört girdi aynı 0–1 ölçeğinde füzyona giriyor.

**3. Farklı projeksiyonları nasıl birleştirdiniz?**
THEMIS, CTX DEM ve HiRISE üç ayrı projeksiyonda geliyordu. Hepsi tek bir hedef sisteme yeniden örneklenip 70 m'lik 256 × 256 grid'e indirildi. Jeoloji haritası (SIM 3464) 1304 poligondan 118'e kırpıldı; haritadaki 2 kaynak hatası düzeltildi.

## Model

**4. mAP50 0,33 düşük değil mi?**
Kutu düzeyinde düşük, çünkü kum alanı gibi bölge ölçekli nesnelerin sınırı belirsiz. Modeli kutu çizmek için kullanmıyoruz; 70 m'lik hücrede kum ve kaya yoğunluğu çıkarıyoruz. O ölçekte dengeli doğruluk 0,78. Asıl ölçü de rota doğrulaması: AUC 0,50'den 0,65'e çıktı.

**5. Veri sızıntısını nasıl önlediniz?**
Komşu karolar aynı sahneyi paylaştığı için karoları 8-komşulukla gruplayıp her grubu train ya da val'den yalnızca birine koyduk. Bu kontrolle ilk bölmede 30 val karosunun 8'inin bir train karosuna bitişik olduğunu bulup düzelttik. Perseverance rotası modele hiç verilmedi; yalnızca doğrulamada kullanıldı.

**6. Neden YOLOv8s ve 2 sınıf?**
5 kurulumu aynı val'de karşılaştırdık: yolov8m ve yolov8s, 3 ve 2 sınıf, bir de karo sınıflandırıcı. kaya_alani'yi ayrı sınıf olarak öğrenmek ölçülebilir bir fayda getirmedi. yolov8s, yolov8m ile aynı doğrulukta ama yarısından küçük ve iki kat hızlı. 150 karoda büyük model ezberlemeye başladı.

**7. İkinci etiket partisi neyi değiştirdi?**
250 karoyla yeniden eğittik. Karar kuralını sonuçları görmeden yazdık: yeni model ancak iki ölçütte de eskiden kötü değilse seçilecekti. Aynı 51 karoluk val'de mAP50 0,31'den 0,33'e, hücre doğruluğu 0,69'dan 0,78'e çıktı; kayalık hücre recall'u 0,36'dan 0,56'ya yükseldi.

**8. Etiketleri yapay zekâ mı yaptı?**
Ön taslak Roboflow Auto Label'dan geldi. 250 karonun hepsini Elif tek tek düzeltti; sınıf tanımları ekibin kararı. Bir tutarsızlığı da kendimiz bulduk: 1. partide küçük çukur kümeleri tutarlı etiketlenmemişti. Model denetimi bunu ölçtü: etiketsiz engel 1. partide karo başına 2,5 kat daha sık.

## Doğrulama

**9. Modelin doğru olduğunu nereden biliyorsunuz?**
Perseverance'ın gerçekten sürdüğü yolu kullandık. Rover ekibi tehlikeli yerden geçmez; skorumuz araziyi doğru okuyorsa rotanın geçtiği hücreler daha kolay görünmeli.
- HiRISE kapsamında görüntü verisi olmadan skor rotayı ayırt edemiyordu: AUC 0,498.
- YOLO ekleyince 0,649'a çıktı. Bootstrap'ta farkın %95 aralığı +0,12…+0,18.
- Rotadaki 52 hücrenin hiçbiri kumlu değil (%0); çevredeki hücrelerin %49,3'ü kumlu.

**10. Rover rotası astronot için doğru bir referans mı?**
Tam değil: tekerlek kuma insandan daha duyarlı ve rota bilim hedeflerine de gidiyor. Ama elimizdeki tek "gerçek tehlikeden kaçınma" verisi bu. Ölçtüğümüz şey de kumdan kaçınma ve bu astronot için de geçerli; Opportunity ve Spirit'in başına gelen buydu.

**11. Kaya neden işe yaramadı?**
Kaya tespiti zayıf ve kaya AUC'si 0,51, yani rotayı ayırt etmiyor. Model 2. partide iki kat fazla kaya bulmasına rağmen sonuç değişmedi. Rover ekibi metre ölçeğindeki kayayı 70 m ölçeğinde önemsemiyor olabilir. Bunu sınırlama olarak raporluyoruz.

**12. HiRISE'ın kapsamadığı yerde ne oluyor?**
Model yalnızca 25 cm'lik mozaiğin kapsadığı ~29 km²'de çalışıyor; 397 rota hücresinin 52'si bu kapsamda. Kapsam dışında skor jeoloji, eğim ve termalden geliyor. O hücrelerde ML terimi yok sayılıyor, sahte değer üretilmiyor. Tüm alanda etki bu yüzden küçük: 0,562 → 0,571.

## Ürün

**13. Füzyon ağırlıkları nereden geliyor?**
Varsayım: en büyük tehlike eğim (0,4), ardından kum (0,25). Jeoloji ile YOLO eşit ağırlıkla birleşiyor, çünkü ikisini kalibre edecek yer-gerçeği yok. Ağırlıklar kodda tek yerde tanımlı; gerçek EVA verisiyle kalibre edilebilir.

**14. O₂ bölgeleri nasıl hesaplanıyor, ne kadar hızlı?**
Dijkstra ile her hücreye gidiş + dönüş süresi hesaplanıyor. Yeşil bölge: bu süre ≤ O₂ / 1,25. Nabız arttıkça O₂ tüketimi büyüyor; nabız 150'de çarpan × 1,6. Ayşe'nin nabzı 85'ten 150'ye çıkınca yeşil bölge 130 → 47 km² oluyor. Hesap tarayıcıda 100 ms altında.

**15. Mars'ta GPS yok, konumu nasıl biliyorsunuz?**
Konum giysi IMU'su, habitat ve rover radyo sinyalleri ve arazi eşleştirmeyle bulunur; demoda simüle ediliyor. Telsiz koparsa son konum ve kalan O₂'den arama alanı çıkıyor. Demoda 20 dk sonra alan 1,07 km²; İHA olasılığın %50'sini 11,6 dk'da tarıyor.

**16. Bu NASA'da zaten var mı?**
SEXTANT ve Minerva gibi araçlar var. Biz şunları açık veriyle, tarayıcıda çalışan tek bir araçta birleştirdik:
- canlı sarf malzemesi takibi,
- dinamik dönüş sınırı,
- kendi tehlike modelimiz ve rota doğrulaması,
- kurtarma modu.

**17. Uygulama nerede, nasıl deneriz?**
https://tayancelifnur.github.io/marstrail/ adresinde; sunucu gerekmiyor, telefonda da açılıyor. Demo planı hazır yüklü: GO, 5,52 km, 243 dk ve dönüşte 249 dk O₂ kalıyor.

## Yedek sayılar

| Sayı | Ne |
| --- | --- |
| 1146 karo, 17 sn | YOLO çıkarımı (RTX 5090) |
| 150 | geçilmez hücre (eğim > 25°) |
| 73 dk · 279 dk | üs → Three Forks · üs → Cheyava Falls (480 dk O₂ ile kırmızı bölge) |
| T+67 | O₂ 220 + nabız 150: dönüş noktası |
| 116 / 480 | Ali'nin kurtarma rotası O₂ ihtiyacı / kapasitesi (YEŞİL) |
