# E5 – Roboflow etiketleme rehberi

**Yüklenecek dosya:** `C:\Users\ASUS\marstrail\ml\roboflow_upload.zip`. 150 karo, 640×640, gri, PNG, 28 MB. Aynı karolar açık klasör olarak `ml\roboflow_upload\` içinde de var.

Karoları üreten script: `venv\Scripts\python scripts\tile_for_yolo.py`. Hangi karonun neden seçildiği ve nerede olduğu `ml/tiles_manifest.csv` dosyasında.

## Roboflow adımları

1. **Proje oluştur:** New Project → **Object Detection** → ad: `marstrail-jezero`.
2. **Sınıfları birebir bu adlarla ekle** (büyük/küçük harf ve alt çizgi önemli; `ml/train.py` bunları bekliyor):
   - `kaya`
   - `kum_dalgasi`
3. **Upload:** Zip'i sürükle. "Split images" sorulursa şimdilik hepsini **Train**'e koy; ayrımı dışa aktarırken yapacağız.
4. **Annotate:** Karolarda kutu çiz (kurallar aşağıda). Kontrol satırı: **en az 120 karo etiketli.** Kum ve kaya karolarını önce bitir; negatifler en sona.
5. **Generate → Version:**
   - Train/Valid/Test: **80 / 20 / 0**.
   - Preprocessing: Auto-Orient açık. Resize **640×640 (Stretch)**; karolar zaten 640, bu adım bir şey değiştirmez.
   - Augmentation: **yok.** Çoğaltmayı eğitimde Ultralytics yapacak; Roboflow'da da yapılırsa iki kez yapılmış olur.
6. **Export:** Format **YOLOv8** → "download zip to computer". Zip'i `C:\Users\ASUS\marstrail\ml\dataset\` içine aç. Klasörde `data.yaml`, `train/` ve `valid/` görünmeli.

## Etiketleme kuralları

Görüntü 25 cm/piksel. Bir karo 160 × 160 m.

| Sınıf | Ne etiketlenir | Ne etiketlenmez |
| --- | --- | --- |
| `kum_dalgasi` | Her bir kum dalgası **sırtı**: açık-koyu tekrar eden uzun şeritlerin her biri ayrı kutu. Sırt eğriyse uçtan uca tek kutu. Çok yoğun alanlarda yan yana 2–3 küçük sırtı tek kutuya alabilirsin; karo içinde tutarlı ol. | Tek tek seçilemeyen çok ince dokular (pürüzlü toz). Kum lekesi ama sırtı olmayan düz alanlar. |
| `kaya` | Tek tek seçilebilen kayalar: **en az ~8 piksel** (≈ 2 m). Parlak bir nokta ve bir yanında koyu gölge. Her kaya ayrı kutu, kutu gölgeyi de kapsasın. | 8 pikselden küçük noktalar (model zaten göremez). Ana kaya yüzeyleri, kırık kaya plakaları, krater kenarları (bunlar eğim katmanında zaten var). |

- **Kategoriye değil, gördüğüne göre etiketle.** Dosyadaki "kum_adayi" ya da "kaya_adayi" sadece karonun neden seçildiğini söyler. Kaya karosunda kum dalgası varsa onu da işaretle.
- **Negatif karolarda** (manifest'te `negatif`) bir şey görmüyorsan boş bırak. Boş karolar da modele "burada tehlike yok" öğretir. Roboflow'da "Mark Null" ile işaretle.
- Karo kenarında yarım kalan nesne en az yarısı görünüyorsa etiketlenir.
- **Hız hedefi:** karo başına ~1 dakika. Çok kayalı bir karoda en belirgin 30–40 kaya yeter; hepsini sayma.

## Etiket tanımı ve sınırlamalar (v1-150karo; `kaya_alani` tanımı v2'de güncellendi, aşağıda)

Roboflow sürümü: `marstrail-jezero` v1 "v1-150karo". 150 karo: 120 train, 30 valid. Sınıflar alfabetik sırada (etiket dosyalarındaki indisler bu sırayla): `0 kaya`, `1 kaya_alani`, `2 kum_dalgasi`. Yukarıdaki iki sınıflı plana etiketleme sırasında `kaya_alani` eklendi.

- **Ön etiketleme:** Roboflow Auto Label (GPT-6.1 Terra) ile yapıldı. Sonra 150 karonun hepsi elle kontrol edildi: yanlış, eksik ve fazla kutular düzeltildi. YZ beyanında yazılı (`docs/TESLIM.md` bölüm 4).
- **`kaya`:** Küçük yüzey engeli, metre ölçeğinde. Kaya da olabilir küçük çukur da. Tek görüntüde ikisini ayırmanın yolu gölgenin hangi yanda olduğuna bakmak (güneş yönüne göre). Bunu güvenilir yapamadık. Astronot için ikisi de takılıp düşme engeli, bu yüzden tek sınıf.
- **`kaya_alani`:** **Yoğun engel alanı:** sık kaya **ya da** sık küçük çukur kümesi (v2 tanımı; v1'de yalnızca "yoğun kaya bölgesi" yazıyordu). Tek tek engel saymak yerine bölge kutusu. Rota grid'inin hücresi 70 m olduğu için haritaya giden bilgi zaten bölge ölçeğinde; bu sınıf o ölçeğe doğrudan karşılık geliyor. Kaya ile çukurun aynı sınıfta olmasının nedeni `kaya` ile aynı: gölge yönüne bakmadan ayrılamıyorlar ve yürüyen astronot için ikisi de engel.
- **`kum_dalgasi`:** Kum dalgası sırtları ya da sırtlarla dolu kum alanı.
- **Etiketlenmeyenler:**
  - Tek büyük krater ya da çöküntü, yamaçları ve gölgeleri. Eğim zaten DEM'den (D5) geliyor; modelin aynı tehlikeyi ikinci kez saymasına gerek yok. Ayrım ölçekte: **çok sayıda küçük çukur** = `kaya_alani`; **tek büyük çukur/yamaç** = etiket yok.
  - Mozaik dikiş yerleri (görüntü şeritlerinin birleştiği düz çizgiler). Bunlar arazi değil, görüntüleme izi.
- **Ölçülen özellikler** (`ml/dataset_stats.py` → `docs/figures/e6_dataset_stats.json`):
  - Kutu boyları üç sınıfı ölçekle ayırıyor: `kaya` medyan 5 m, `kaya_alani` 24 m, `kum_dalgasi` 61 m.
  - 237 `kum_dalgasi` kutusunun 74'ü karonun %80'inden fazlasını kaplıyor. Bu karolarda sınıf "nesne" değil "bu karo kum alanı" anlamına geliyor. Kum için model kısmen karo sınıflandırıcısı gibi davranacak; haritaya yoğunluk olarak gittiği için (E10) bu sorun değil.
  - Negatif karoların çoğunda sonradan kum dalgası bulundu (15 karonun 14'ünde en az bir kutu var). Tamamen boş karo yalnızca 7 tane. Yani model "hiçbir şey yok" durumunu az görüyor; yanlış pozitif riskine E10'da bakılacak.
- **Kapsam:** Karoların hepsi HiRISE mozaiğinin kapsadığı güneybatı bölümden (DATA_PIPELINE.md, D8). Model başka aydınlatma ya da çözünürlükteki görüntüye (ör. Mars Trek mozaiği) genellenmeyebilir.

### Tanım güncellemesi (v2-250karo) ve tutarlılık sınırlaması

- **Ne değişti:** 2. partide (100 karo) `kaya_alani` "yoğun engel alanı" olarak etiketlendi: sık kaya kümeleri **ve** sık küçük çukur kümeleri. 1. partinin (150 karo) etiketleri değiştirilmedi.
- **Sınırlama:** 1. partide çukur kümeleri tutarlı etiketlenmedi; bazıları `kaya_alani`, bazıları hiç etiketlenmedi. Yani eski karolarda bazı yoğun çukur alanları "arka plan" olarak duruyor ve model orada doğru tespit yapınca yanlış pozitif sayılıyor.
- **Ölçülen fark** (`ml/merge_v2.py` → `docs/figures/e6v2_split.json`):
  - Karo başına `kaya_alani` kutusu: 1. parti 0,55, 2. parti 2,45.
  - `kaya_alani` içeren karo: 1. partide 150'de 25, 2. partide 100'de 66.
  - `kaya` kutularının p90 kenarı: 9,4 m → 15,6 m.
  - Farkın bir kısmı seçimden geliyor (2. partide 40 kayalık karo var), bir kısmı tanımdan.
- **Etkisi:** 2 sınıflı modelde `kaya_alani` zaten `kaya`'ya birleşiyor, yani haritaya giden "kayalık" bilgisi iki partide de aynı anlamda. Karşılaştırmada eski ve yeni karolar ayrı raporlanıyor (`ml/eval_merged.py`).
- **Düzeltme yolu (yapılmadı):** 1. partinin 150 karosuna çukur kümeleri için yeniden bakmak. E10 etiket denetimi listesi (`ml/audit_missed_labels.csv`) iyi bir başlangıç noktası.

## 2. parti: 100 ek karo (E6 sonrası)

**Yüklenecek dosya:** `C:\Users\ASUS\marstrail\ml\roboflow_upload_2.zip` (100 PNG, 18 MB). Karoları seçen script: `scripts/tile_batch2.py`. Karoların listesi ve seçilme nedenleri `ml/tiles_manifest_2.csv` dosyasında.

**Neden bu karolar?** v1'de tamamen boş karo yalnızca 7 taneydi. Model etiketsiz yerlerde kum ya da kaya alanı uyduruyordu. kaya_alani da en zayıf sınıftı. Bu yüzden partinin dağılımı şöyle:
- 40 kayalık karo
- 53 düz karo (3'ü dokusuz)
- 7 kum karosu

Karoların hiçbiri eski 150 karoyla ya da onlara bitişik bir karoyla aynı değil. 75'i birbirine de bitişik değil; kalan 25'i alan dolduğu için birbirine bitişik olabilir.

1. **Aynı projeye yükle:** `marstrail-jezero`. Karo adları aynı ızgaradan geliyor ve eskilerle çakışmıyor.
2. **Aynı kurallarla etiketle:** sınıflar kaya, kaya_alani ve kum_dalgasi; tanımları yukarıda. Auto Label kullanabilirsin ama her karoyu elle kontrol et.
3. **Boş karoyu boş bırak.** Düz karolarda gerçekten bir şey yoksa "Mark Null" işaretle. Bu partinin asıl amacı bu boş örnekler. Kutu uydurmak için zorlama.
4. **Yeni sürüm oluştur (v2):**
   - Ön işleme ve augmentation v1 ile aynı: yalnız Auto-Orient açık, augmentation yok.
   - Train/valid oranı 80/20 kalabilir. Bölmeyi zaten kendimiz yeniden yapacağız: bitişik karolar aynı tarafa gidecek ki sızıntı olmasın.
5. **Export:** YOLOv8 formatında indir ve `C:\Users\ASUS\marstrail\ml\dataset_v2\` klasörüne aç. **`ml\dataset\` klasörünün üzerine yazma**, v1 ablation koşuları ona bağlı.

## Etiket denetimi (E10)

Model, etiketlediğin 150 karoda yüksek güvenle (≥ 0,5) 40 tespit buldu; bunlar senin hiçbir etiketinle eşleşmiyor ve 24 karoya dağılıyor. Liste: `ml/audit_missed_labels.csv`. Her satırda karo, bölüm (train/valid), sınıf, güven ve piksel kutusu var. Örnekler: `docs/figures/e10_audit_examples.png`.

- 2. partiyi etiketlerken bu karolara da Roboflow'da bak. Model haklıysa etiketi ekle; haksızsa (ör. kırıklı parlak kayayı kum sanmışsa) dokunma.
- Gerçek eksik gibi görünenler: jz_r066_c015, jz_r065_c013, jz_r036_c017, jz_r031_c009.

**v2 modeliyle, 250 karoda (güncel `ml/audit_missed_labels.csv`):** 101 tespit, 57 karoda (79 kaya, 22 kaya alanı, 0 kum). 80'i 1. parti karolarında (39 karo), 21'i 2. partide (18 karo); karo başına 0,53'e karşı 0,21. En güvenli 8 örneğin hepsi 1. partiden ve 7'si küçük çukur/kaya. Yani 1. partiyi yeni tanımla gözden geçirmek için liste hazır; en çok bulgu: jz_r069_c012 (13), jz_r066_c015 (9), jz_r055_c003 (4).

## Takılırsan

Kartın B planı: **80 karo + tek sınıf (`kum_dalgasi`)**. Kum karoları hem daha hızlı etiketlenir hem demoda (Opportunity hikâyesi) daha önemli.
