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

## Takılırsan

Kartın B planı: **80 karo + tek sınıf (`kum_dalgasi`)**. Kum karoları hem daha hızlı etiketlenir hem demoda (Opportunity hikâyesi) daha önemli.
