# MarsTrail teknik anlatım

Bu belge projeyi baştan sona anlatıyor: veri nereden geldi, onu nasıl temizledik, modeli nasıl eğittik, uygulama neyi nasıl hesaplıyor ve bunların doğru olduğunu nereden biliyoruz. Amaç, her adımı jüriye kendi cümlelerinle anlatabilmen.

**Sayılar hakkında:** Buradaki her sayı bir dosyadan geliyor:
- `docs/figures/*.json` dosyaları (veri hattı ve model betiklerinin çıktısı),
- `web/data/grid.json`,
- uygulama testleri `web/tests/e8.html`, `e11.html` ve `e13.html` (15 Kasım 2026'da çalıştırıldı, hepsi ✔).

Sunumdaki sayıların kaynak eşlemesi [SAYI_DENETIMI.md](SAYI_DENETIMI.md)'de. Örnek hesaplarda yuvarlama yüzünden son hanede ±1 fark görebilirsin.

**İçindekiler**
1. [Büyük resim](#1-büyük-resim)
2. [Veri hattı adım adım](#2-veri-hattı-adım-adım)
3. [Model: YOLO](#3-model-yolo)
4. [Web uygulaması](#4-web-uygulaması)
5. [Doğrulama: Perseverance rotası](#5-doğrulama-perseverance-rotası)
6. [Varsayımlar ve sınırlar](#6-varsayımlar-ve-sınırlar)
7. [Sözlük](#7-sözlük)

---

## 1. Büyük resim

### Tek cümlede proje

Astronot Mars'ta yürürken uygulama her an üç soruyu cevaplıyor:
- Nereye kadar gidip O₂'si bitmeden üsse dönebilir?
- Hangi yoldan gitmeli?
- Telsiz koparsa onu nasıl buluruz?

Bu soruları cevaplamak için önce Mars arazisini bir "yürüme maliyeti haritasına" çevirdik. Uygulama o haritanın üzerinde hesap yapıyor.

### Akış

```
 AÇIK VERİ (NASA/USGS, ~6 GB)                 PYTHON (bir kez çalışır, bilgisayarda)
 ─────────────────────────────                ─────────────────────────────────────────
 D5 CTX DEM (yükseklik, 20 m)   ──┐
 D4 THEMIS termal (100 m)       ──┼──► scripts/prep_layers.py ──► web/data/grid.json (256×256, 1,3 MB)
 D6 USGS jeoloji haritası       ──┘        ▲  (yeniden örnekle,       web/data/layers/*.png
                                           │   eğim, normalize et,    web/data/layers.json
                                           │   füzyon skoru)
 D8 HiRISE 25 cm görüntü ──► scripts/tile_for_yolo.py ──► Roboflow'da etiket (Elif)
                                           │                 │
                                           │      ml/merge_v2.py → ml/train.py → ml/eval_merged.py
                                           │                 │
                                           └── ml/infer.py ◄─┘  (YOLO: hücre başına kum ve kaya yoğunluğu)

 D1 rover konumları, D3 Ingenuity, D7 rover fotoğrafları ──► scripts/build_regions.py ──► regions.json, poi.geojson, stories.json
 D2 rover'ın sürüş izi ──► scripts/validate.py ──► "skorumuz doğru mu?" (AUC)

 TARAYICI (her şey burada, sunucu yok)
 ─────────────────────────────────────
 index.html + app.js (Gözde)   : Cesium Mars küresi, paneller, düğmeler
 walkback.js (Elif)            : Dijkstra, O₂ bölgeleri, güvenli rota
 eva.js (Elif)                 : yürüyüş planı, zaman çizelgesi, dönüş noktası, Go/No-Go
 marstime.js (Elif)            : Mars saati, Sol, gün batımı, Dünya–Mars gecikmesi
 rescue.js (Elif)              : arama alanı, İHA zikzak rotası, arkadaşın kurtarma rotası
```

### Klasörler

| Klasör | Ne iş yapıyor | Git'te mi? |
| --- | --- | --- |
| `data/raw/` | İndirilen ham veri (D1–D8) | Hayır, büyük. `scripts/download_data.py` indirir |
| `data/processed/` | Ara diziler (`grid_256.npz`, `ml_density_256.npz`) | Hayır |
| `scripts/` | Veri hattı: indirme, katmanlar, noktalar, karolar, doğrulama, sunum | Evet |
| `ml/` | Model: birleştirme, eğitim, değerlendirme, çıkarım | Kod evet; veri seti ve ağırlıklar hayır |
| `web/` | Uygulamanın kendisi. GitHub Pages bu klasörü yayınlar | Evet |
| `web/data/` | Python'un ürettiği, tarayıcının okuduğu dosyalar. Elif ile Gözde'nin ortak noktası | Evet |
| `web/tests/` | Algoritma testleri, tarayıcıda açılır | Evet |
| `docs/` | Belgeler, şekiller (`figures/`), sunum (`sunum/`) | Evet |

### Neden böyle böldük?

- **Ağır iş bir kez, Python'da:** 4,7 GB'lık bir görüntüyü ya da 90 MB'lık bir DEM'i tarayıcıda işleyemezsin. Bunları bir kez işleyip sonucu 1,3 MB'lık bir grid'e indirdik.
- **Hızlı iş her an, tarayıcıda:** Astronotun nabzı değişince O₂ bölgeleri yeniden çizilmeli. Bu hesap 65.536 hücrelik grid üzerinde Dijkstra ile tarayıcıda yapılıyor. Bu bilgisayarda Edge'de ölçtük: ilk hesap 69 ms, sonraki her güncelleme ~30 ms.
  - İlk hesap uzun, çünkü "her hücreden üsse dönüş" süresi bir kez hesaplanıp saklanıyor.
  - Test sayfaları "0 ms" yazıyor. Bu gerçek değil: otomatik test sanal zamanla koşuyor ve orada saat ilerlemiyor.
- **Sunucu yok:** Uygulama statik dosyalardan oluşuyor. GitHub Pages'te ücretsiz yayınlanıyor, telefonda da açılıyor, sunum günü sunucu çökmesi riski yok.

> **Jüri sorarsa:** *"Neden backend yok?"*
> Ağır veri işlemeyi bir kez Python'da yapıp sonucu 1,3 MB'lık bir dosyaya indirdik; canlı hesaplar o dosya üzerinde tarayıcıda ~30 ms'de bitiyor, sunucuya ihtiyaç yok. Gerçek bir görevde de hesabın astronotun yanında yapılması gerekir, çünkü Dünya'ya sormak tek yönde 3–22 dakika sürer.

---

## 2. Veri hattı adım adım

Her adımda şu kalıbı izledik: **ne aldık → neyi neden attık → nasıl temizledik → nasıl normalize ettik → ne ürettik.** Ayrıntılı tablo [DATA_PIPELINE.md](DATA_PIPELINE.md)'de; burada mantığı ve önemli kodu anlatıyorum.

### 2.1 Ortak koordinat sistemi: neden ilk iş bu?

Üç raster üç ayrı projeksiyonda geldi:

| Veri | Projeksiyon |
| --- | --- |
| THEMIS termal | SimpleCylindrical |
| CTX DEM | Jezero_Crater_Projection |
| USGS jeoloji | MTM_clon77_5E |

Aynı pikselin üç dosyada aynı yere denk gelmesi için hepsini tek bir sisteme taşıdık. Bu sistem Mars 2000 küresi (R = 3396,19 km) üzerinde derece cinsinden boylam/enlem; doğu pozitif.

**Çalışma alanı:**
- 77,28–77,60°D, 18,293–18,597°K, yaklaşık 18 × 18 km.
- Alanı metre cinsinden kare seçtik ki 256 × 256 grid'in hücreleri de kare olsun. Boylam derecesi enlemle kısalıyor: 0,32° × cos(18,445°) ≈ 0,304° enlem.
- Sonuç: hücre 70,4 m (`grid.json` → `cell_size_m: 70.39`).

### 2.2 `scripts/download_data.py`: indirme

D1–D8'i indirip boyutlarını yazıyor. Ham veri toplamı ~6 GB (5,91 GB). En büyükleri:
- HiRISE zip'i (5,47 GB),
- jeoloji zip'i (349 MB),
- DEM (90,3 MB).

### 2.3 `scripts/prep_layers.py`: katmanlar ve grid (en önemli betik)

Girdi D4, D5 ve D6. Çıktı `grid.json`, harita PNG'leri ve `layers.json`. Adımlar:

**a) Yeniden örnekleme (`warp`).** Her raster çalışma alanına, n × n'lik bir ızgaraya taşınıyor:

```python
def warp(path, n, resampling, dst_crs, src_nodata=None):
    dst = np.full((n, n), np.nan, dtype=np.float32)          # 1
    transform = from_bounds(*BBOX, n, n)                       # 2
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, src_nodata=..., # 3
                  dst_transform=transform, dst_crs=dst_crs, dst_nodata=np.nan, resampling=resampling)
    return dst
```

1. Boş bir n × n dizi açıyoruz. Varsayılan değer NaN, yani "veri yok".
2. `from_bounds` dizinin her pikselinin hangi boylam/enleme düştüğünü tanımlıyor.
3. `reproject` kaynak dosyayı bizim sistemimize çevirip diziye yazıyor. NoData pikselleri NaN oluyor, böylece ortalamaya karışmıyor.

`resampling` seçimi bilinçli:
- **DEM ve eğim için `average`:** 70 m'lik hücreye düşen bütün 20 m'lik piksellerin ortalaması. Yürüme maliyeti için hücrenin genel eğimi önemli.
- **Termal için `bilinear`:** Kaynak 100 m, hedef daha ince. Komşu dört pikselden yumuşak geçiş yapılıyor; yeni bilgi üretmiyor, sadece kademe kademe görünmesini engelliyor.

**b) Eğim, DEM'in kendi çözünürlüğünde (`slope_native`):**

```python
z = src.read(1).astype(np.float32)
z[(z < -9000) | (z > 30000)] = np.nan                  # NoData (-3,4·10³⁸) → NaN
gy, gx = np.gradient(z, abs(src.res[1]), src.res[0])   # metre başına yükseklik değişimi, iki yönde
slope = np.degrees(np.arctan(np.hypot(gx, gy)))        # eğim = atan(√(gx² + gy²)), dereceye
```

- **1. satır:** DEM'i okuyoruz.
- **2. satır:** Mars'ta −9000 m'nin altı ya da 30 km'nin üstü fiziksel olarak imkânsız. Bu değerler dosyanın "veri yok" işareti (−3,4·10³⁸), onları NaN yapıyoruz.
- **3. satır:** Her pikselde doğu–batı (gx) ve kuzey–güney (gy) yönündeki yükseklik değişimini metre başına hesaplıyoruz.
- **4. satır:** İki yöndeki değişimden toplam eğim açısını buluyoruz.

**Neden önce eğim, sonra yeniden örnekleme?** Önce 70 m'ye indirip sonra eğim alsaydık dik yamaçlar ortalamada kaybolurdu. 20 m'de alan içinde 2652 piksel 25°'nin üstünde.

**c) Termal normalizasyon:**

```python
def normalize_thermal(ti):
    lo, hi = np.nanpercentile(ti, [2, 98])                  # %2 ve %98 dilimleri
    return np.clip((ti - lo) / (hi - lo), 0, 1), float(lo), float(hi)
```

- Termal eylemsizlik birimi TIU. Değerler 132,8 ile 400,6 arasında.
- Min–max yerine %2–%98 dilimini kullandık. Sebep: birkaç aykırı piksel (ör. 400) bütün ölçeği bir uca sıkıştırırdı.
- Bu alanda p2 = 155,5 TIU, p98 = 326,8 TIU. Alt uçta 684, üst uçta 684 piksel kırpıldı (0'a ya da 1'e sabitlendi).
- Sonuç: 0 en gevşek zemin (kum/toz), 1 en sert kaya.

**d) Jeoloji: poligondan sayıya.**
- USGS haritası 1304 poligondan oluşuyor; alanımıza 118'i değiyor.
- Kaynaktaki 2 hatayı düzelttik:
  - "Crater riim unit" yazım hatası.
  - Kodu ile adı çelişen 1 poligon. Kod yerine ada güvendik.
- Her birime `GEO_UNITS` tablosunda üç sayı verdik: yürünebilirlik, kaya vekili (0–1) ve bilim değeri (1–5). Örnek:

```python
"Eolian bedform unit":    (0.30, 0.00, 2, ...),   # kum dalgaları: batma riski
"Crater rim unit":        (0.40, 0.60, 3, ...),
```

Eolyen (kum) birimin kaya vekili 0, çünkü cezası zaten "kum" teriminden geliyor; aynı tehlikeyi iki kez saymıyoruz.

**e) Füzyon: dört katmandan tek skor.**

```python
slope_risk = np.clip(slope / SLOPE_MAX_DEG, 0, 1)          # eğim / 25°
rock_f = np.where(np.isnan(rock), 0.3, rock)               # jeoloji yoksa "orta" (0,3)
th_f = np.where(np.isnan(th_norm), 0.5, th_norm)           # termal yoksa "orta" (0,5)
fuse = lambda s, r: np.clip(0.4 * slope_risk + 0.25 * s + 0.15 * r + 0.2 * (1 - th_f), 0, 1)
```

Formül:

**skor = 0,4·eğim_risk + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)**

- Dört terimin hepsi 0–1 arasında. Normalizasyon bu yüzden önemliydi: dereceyle TIU'yu toplayamazsın.
- **Ağırlıklar bizim varsayımımız.** En büyük tehlike eğim (0,4); ardından kum (0,25), çünkü Spirit ve Opportunity'nin başına gelen buydu.
- `1 − termal` kullanıyoruz, çünkü düşük termal = gevşek zemin = yüksek risk.
- Eksik veri kuralı (kaya 0,3, termal 0,5) bu alanda hiç devreye girmedi; üç kaynak da alanı tam kapsıyor.

**Örnek: üs hücresi** (satır 128, sütun 136; değerler `data/processed/grid_256.npz`'den). Ortalama eğim 1,78°, kum yok, Jezero floor birimi (kaya vekili 0,15), termal_norm 0,503:
- 0,4 · (1,78 / 25) = 0,028
- 0,25 · 0 = 0
- 0,15 · 0,15 = 0,023
- 0,2 · (1 − 0,503) = 0,099

Toplam 0,150. `grid.json`'da üs hücresinin skoru da 0,15, yani kolay arazi. Bütün grid'de ortalama skor 0,26.

**f) YOLO katkısı (E10'dan sonra eklendi):** HiRISE'ın kapsadığı hücrelerde kum ve kaya terimleri iki kaynağın ortalaması oluyor:

```python
sand_c = np.where(has, 0.5 * sand + 0.5 * np.nan_to_num(kum_ml), sand)
rock_c = np.where(has, 0.5 * rock_f + 0.5 * np.nan_to_num(kaya_ml), rock_f)
```

`has` "bu hücrede YOLO verisi var mı?" demek; yoksa eski değer aynen kalıyor. Neden yarı yarıya?
- Jeoloji haritası 1:75.000 ölçekli; bir birimin içindeki düz alanı göremez.
- YOLO 25 cm'de bakıyor ama mükemmel değil.
- İkisini kalibre edecek yer-gerçeğimiz yok. Eşit ağırlık en az varsayım gerektiren seçim.

**g) Grid ve geçilmezlik (`make_grid`):**

```python
blocked = G["nodata"] | (G["slope"] > SLOPE_MAX_DEG) | (G["score"] > SCORE_MAX)
cost = np.where(blocked, 999.0, cost)
```

- Bir hücre üç durumda geçilmez: verisi yoksa, eğimi 25°'den fazlaysa ya da skoru 0,8'den büyükse.
- 65.536 hücrenin 150'si geçilmez. Hepsi eğim yüzünden; skor eşiğini aşan hücre yok.
- Geçilmez hücreye maliyet olarak 999 yazılıyor, rota oradan geçmiyor.
- `grid.json`'a `elev`, `score`, `blocked` ve `sand` (kum tuzağı, 0/1) da yazılıyor. YOLO'dan sonra 8143 hücre kum tuzağı işaretli.

### 2.4 `scripts/build_regions.py`: nokta kartları

Haritadaki pinler (üs, Rochette, delta önü, Three Forks, Cheyava Falls, Ingenuity) uydurma koordinatta değil. Her biri, olayın yaşandığı Sol'de rover'ın ölçülmüş konumunda:

```python
def position(spec, wps, heli):
    if kind == "sol":
        s = spec[1]
        before = [w for w in wps if w[0] <= s]     # Sol'ü olayınkinden küçük ya da eşit kayıtlar
        w = before[-1] if before else wps[0]       # bunların sonuncusu = "o gün rover neredeydi"
        return w[1], w[2], f"D1 Sol {w[0]} kaydı (Sol ≤ {s} olan son konum)"
```

- D1'deki 708 kayıt Sol'e göre sıralı. Olay Sol'ünden önceki ya da o güne ait en son kaydı alıyoruz. Rover numune alırken günlerce park ettiği için "o gün nerede duruyordu" sorusunun cevabı bu. Örnek: Three Forks olayı Sol 653, kullanılan kayıt Sol 652.
- **Çapraz doğrulama:** Ingenuity pini D3'teki Uçuş 1'in kalkış noktasından geliyor. Bu nokta D1'de rover'ın Sol 34 konumuyla birebir aynı, çünkü rover helikopteri orada bırakmıştı. İki bağımsız kaynak birbirini doğruluyor.
- **Fotoğraflar (D7):** API'den 1795 görüntü kaydı geldi, kural tabanlı bir huniden geçti ve 10 fotoğraf seçildi. Huni sırası:
  1. kamera,
  2. genişlik,
  3. renkli/gri ikizlerin tekilleştirilmesi,
  4. direk açısı,
  5. doku eşiği,
  6. 1 insan kontrolü.

### 2.5 `scripts/tile_for_yolo.py`: HiRISE'ı karolara bölme

- HiRISE mozaiği 76.576 × 107.264 piksel; her piksel 25 cm.
- 640 × 640 piksellik karolara böldük. Her karo 160 × 160 m'lik bir alan; 640, YOLOv8'in giriş boyu.

| Adım | Karo |
| --- | --- |
| Izgara | 2590 |
| NoData içeren (mozaik eğik bir şerit, köşeler boş) | −1444 |
| Dokusuz (düz toz/gölge; std, kullanılabilir karoların alt %5'inin altında) | −58 |
| Kullanılabilir | 1088 |
| Etiketlemeye seçilen (70 kum + 65 kaya + 15 negatif) | 150 |

**En uzak nokta örneklemesi:** Aynı yerin komşu karolarını seçmemek için.

```python
first = rng.integers(len(cands))                     # rastgele bir başlangıç (seed 42)
chosen = [first]
d = np.hypot(*(cands - cands[first]).T)              # her adayın seçilenlere en kısa uzaklığı
for _ in range(n - 1):
    j = int(np.argmax(d))                            # en uzaktaki adayı seç
    chosen.append(j)
    d = np.minimum(d, np.hypot(*(cands - cands[j]).T))   # uzaklıkları güncelle
```

Her adımda o ana kadar seçilenlerden en uzak olan aday ekleniyor. Böylece karolar haritaya yayılıyor, birbirinin kopyası olmuyor.

**Parlaklık germe:**
- Formül: `piksel' = (piksel − 60) / (219 − 60) · 255`.
- 60 ve 219, bütün alanın %0,5 ve %99,5 dilimleri.
- Germe karo başına değil, alan genelinde tek. Böylece aynı zemin her karoda aynı parlaklıkta görünüyor.
- Çıkarımda da aynı sayılar kullanılıyor (`ml/tiles_meta.json`).

### 2.6 `scripts/tile_batch2.py`: ikinci etiket partisi

- **Neden:** v1 modeli kayalık hücreleri kaçırıyordu ve "boş/düz" örnek azdı.
- **Seçim:** 100 yeni karo: 40 kayalık, 53 düz, 7 kum.
- **Kural:** Eski karolara bitişik olmayanlar arasından seçildi.

### 2.7 `ml/` betikleri

Model bölümünde (3) ayrıntılı anlatıyorum. Sıra şöyle:
1. `merge_v2.py`: 250 karoyu birleştirip bitişik karoları aynı tarafa koyan bölmeyi yapar.
2. `train.py`: modeli eğitir.
3. `eval_merged.py`: eski ve yeni modeli aynı val'de karşılaştırır.
4. `compare_runs.py --select`: seçilen modeli `yolo_marstrail.pt` yapar.
5. `infer.py`: 1146 karoda çıkarım yapar, sonucu hücre yoğunluğuna çevirir.

### 2.8 `scripts/validate.py`, `pipeline_stats.py`, `audit_numbers.py`

- `validate.py`: Skoru Perseverance'ın gerçek rotasıyla sınıyor (bölüm 5).
- `pipeline_stats.py`: Her veri adımının ham, atılan ve kalan sayılarını ölçüp JSON'a yazıyor. DATA_PIPELINE.md'deki sayılar buradan.
- `audit_numbers.py`: Sunumdaki 46 sayıyı JSON'lardan ve uygulama testlerinden yeniden hesaplayıp karşılaştırıyor. Son sonuç 46/46 eşleşme.

> **Jüri sorarsa:** *"Hangi veriyi neden attınız?"*
> Attığımız her şeyi betik saydı: HiRISE'ta 2590 karonun 1444'ü boştu (NoData), 58'i dokusuzdu; jeoloji haritasında 1304 poligonun 118'i alanımıza değiyordu, rover konum dosyasında 23 alanın yalnızca 4'ü işimize yarıyordu. Sonunda ~6 GB ham veri, tarayıcıya giden 1,3 MB'lık bir grid'e indi.
>
> *"Normalizasyonu nasıl yaptınız?"*
> Termalde min–max yerine %2–98 dilimlerini kullandık, çünkü birkaç aykırı piksel bütün ölçeği bozardı; eğimi astronot sınırı olan 25°'ye böldük. Böylece dört farklı birimli katman aynı 0–1 ölçeğinde toplanabildi.

---

## 3. Model: YOLO

### 3.1 YOLO nedir? (basitçe)

YOLO ("You Only Look Once") bir nesne tespit modeli. Bir görüntüye bir kez bakıp "şurada bir kaya var, şurada kum dalgası" diye kutular çiziyor ve her kutuya bir güven puanı veriyor (0–1).

**Neden gerekli?**
- Opportunity'yi 5 haftadan uzun tutan kum dalgası yaklaşık 30 cm yüksekliğinde, 2,5 m genişliğindeydi.
- Elimizdeki DEM 20 m, termal veri 100 m çözünürlükte; böyle bir dalgayı göremezler.
- HiRISE'ın 25 cm'lik görüntüsü görebilir, ama 4,7 GB'lık görüntüye tek tek bakamayız. Modeli bunun için eğittik.

**Transfer öğrenme:** Modeli sıfırdan eğitmedik. COCO veri setinde (günlük nesneler) önceden eğitilmiş YOLOv8 ağırlıklarından başladık. Model kenar, doku ve gölge gibi temel şeyleri zaten biliyor; biz ona yalnızca "Mars'ta kaya ve kum neye benzer"i öğrettik. 250 karoluk küçük bir veri setiyle çalışabilmemizin sebebi bu.

### 3.2 Etiketleme

Roboflow'da üç sınıf tanımladık:

| Sınıf | Tanım | Kutu boyu (medyan, 1. parti) |
| --- | --- | --- |
| `kaya` | Metre ölçeğinde tek engel: kaya ya da küçük çukur | 5,0 m |
| `kaya_alani` | Yoğun engel alanı: sık kaya ya da sık küçük çukur kümesi | 23,9 m |
| `kum_dalgasi` | Kum dalgası sırtları ya da sırtlarla dolu kum alanı | 60,9 m |

**Bilinçli olarak etiketlemediklerimiz:**
- Tek büyük krater ve yamaçlar: eğim zaten DEM'den geliyor, aynı tehlikeyi iki kez saymak istemedik.
- Mozaik dikiş yerleri: bunlar arazi değil, görüntüleme izi.

**Ön etiket:** Roboflow Auto Label bir taslak çizdi. 250 karonun hepsini Elif tek tek kontrol edip düzeltti.

**Bulduğumuz tutarsızlık:**
- 1. partide (150 karo) küçük çukur kümeleri tutarlı etiketlenmemişti. 2. partide tanım "yoğun engel alanı" olarak netleşti.
- Bunu ölçtük. Karo başına `kaya_alani` kutusu 1. partide 0,55, 2. partide 2,45.
- Model denetimi de aynı şeyi gösterdi: etiketsiz kalmış engel 1. partide karo başına 0,53, 2. partide 0,21, yani 2,5 kat daha sık.

### 3.3 Bölme: train ve val, veri sızıntısı olmadan

Modeli eğittiğimiz karolar (train) ile sınadığımız karolar (val) ayrı olmalı. Bunu sınava benzetebilirsin: sınav soruları ders kitabından birebir gelirse öğrencinin konuyu anladığını ölçemezsin.

**Sorun:** 160 m'lik iki komşu karo aynı kum alanını paylaşır. Biri train'de, komşusu val'deyse model sınavda "gördüğü sahneyi" tekrar görür. Bu durumda val skoru şişer. Buna **uzamsal veri sızıntısı** diyoruz.

**Çözüm (`ml/merge_v2.py`):** Karoları 8-komşulukla (kenar ve köşe) gruplara ayırdık. Her grup bütün olarak tek tarafa gidiyor:

```python
for k in keys:
    r, c = pos[k]
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            n = at.get((r + dr, c + dc))       # 8 komşudan biri de etiketli karo mu?
            if n and n != k:
                parent[find(k)] = find(n)      # öyleyse ikisini aynı gruba bağla (birleşim-bul)
```

- Her karonun çevresindeki 8 kareye bakıyoruz. Komşu da etiketli bir karoysa ikisini aynı gruba bağlıyoruz.
- Komşunun komşusu da aynı gruba düşüyor. Böylece birbirine değen bütün karolar tek bir "bileşen" oluyor.
- Sonuç: 250 karo 203 bileşene ayrıldı (176'sı tek karo, en büyüğü 11 karo).

Bölme kuralları, sırayla:
1. v1'de train olan bir karoyu içeren bileşen train'e gider. Böylece eski model yeni val'deki hiçbir karoyu eğitimde görmemiş oluyor ve iki model adil karşılaştırılıyor.
2. Yalnızca v1 val karolarından oluşan bileşen val'e gider.
3. Yalnızca yeni karolardan oluşan bileşenlerden, val %20'ye ulaşana kadar kategoriye göre dengeli seçim yapılıyor (sabit tohum).

| | 1. parti | 2. parti | Toplam |
| --- | --- | --- | --- |
| train | 128 | 71 | 199 |
| val | 22 | 29 | 51 |

**Bulgu:** v1'in rastgele bölmesinde 30 val karosunun 8'i bir train karosuna bitişikti. Yani ilk skorlarımız biraz iyimserdi; bunu düzeltip raporladık. Betik sonunda `assert` ile "val ile train arasında bitişik çift 0" kontrolü yapıyor.

### 3.4 Eğitim ve v1'in ıraksaması

**v1 ne oldu?**
- İlk eğitimde Ultralytics'in otomatik ayarları kullanıldı: AdamW optimizer, öğrenme hızı 0,0014, fp16 (AMP) karışık hassasiyet.
- Epoch 1–2 normaldi (val mAP50 0,07).
- **Epoch 3–4'te eğitim patladı:** sınıf kaybı 4,1'den 16,7'ye, kutu kaybı 1,7'den 3,5'e fırladı.
- Doğrulama kaybı epoch 3–15 arasında NaN oldu. NaN "sayı değil" demek; hesap taştı.
- Model öğrendiklerini kaybetti, epoch 12'den sonra neredeyse sıfırdan yeniden öğrendi.
- Sonuç mAP50 0,162 oldu ve bu modeli kullanmadık.

**Günlük dil:** Bisiklet sürmeyi öğrenen birine ilk gün çok sert itme yaparsan düşer ve baştan başlaması gerekir. Öğrenme hızı ve fp16'nın düşük hassasiyeti bu "sert itme" gibi davrandı.

**Nasıl düzelttik?** Olası iki nedeni de kaldırdık (`ml/train.py`):

```python
ap.add_argument("--optimizer", default="SGD")       # YOLO'nun klasik tarifi; ısınma ayarları SGD için tasarlandı
ap.add_argument("--lr0", type=float, default=0.01)
ap.add_argument("--amp", action="store_true")       # fp16 varsayılan KAPALI → fp32 eğitim
...
def nan_watch(trainer):                              # her epoch sonunda: doğrulama kaybı NaN mı?
    v = trainer.metrics.get("val/box_loss")
    if v is not None and isinstance(v, float) and math.isnan(v):
        print(f"!!! UYARI: epoch {trainer.epoch + 1} doğrulama kaybı NaN – eğitim ıraksıyor !!!")
```

- Optimizer'ı SGD'ye (lr 0,01), hassasiyeti fp32'ye çevirdik.
- Her epoch sonunda NaN kontrolü ekledik. v1'de ıraksamayı ancak sonradan fark etmiştik; artık anında uyarı çıkıyor.
- Aynı model ve veriyle yalnızca bu değişiklik mAP50'yi 0,162'den 0,273'e çıkardı. Sonraki hiçbir koşuda NaN olmadı.

**Artırma (augmentation):** Eğitim sırasında görüntüyü yapay olarak değiştirip çeşitlilik ekledik. Her seçimin bir sebebi var:

| Ayar | Değer | Neden |
| --- | --- | --- |
| Yatay + dikey çevirme | %50 | Uydu görüntüsünde "yukarı" yok |
| Parlaklık | ±%30 | Farklı güneş açısı, mozaik şeritleri arası ton farkı |
| Renk tonu / doygunluk | 0 | HiRISE görüntüsü gri |
| Döndürme | 0 | İnce kum sırtlarında kutuyu şişirir |
| Ölçek | ±%25 (varsayılan ±%50) | Sınıflar fiziksel boyuta bağlı; büyük oynama kaya ile kaya_alani'yi karıştırır |

**Ablation (hangisi daha iyi?):** Aynı kararlı ayarla 5 kurulumu karşılaştırdık:
- YOLOv8m ve YOLOv8s,
- 3 ve 2 sınıf,
- bir de karo sınıflandırıcı.

Aynı 2 sınıflı görevde farklar 0,016 mAP50'ydi, yani gürültü düzeyinde. Bu yüzden basit olanı seçtik:
- YOLOv8s, 11,1 M parametre (yolov8m'nin yarısından küçük).
- 2 sınıf: kaya_alani, kaya'ya birleşti. Haritaya giden bilgi zaten "kayalık".

**v2 (250 karo):** Aynı kurulum, yalnızca veri değişti. 41 epoch (erken durdu), en iyi epoch 21, 1,4 dakika.

### 3.5 Değerlendirme ve karar kuralı

Sonuçları görmeden önce kuralı koda yazdık (`eval_merged.py --decide`): yeni model ancak **hem** mAP50 **hem** hücre dengeli doğruluk eskisinden kötü değilse seçilecekti. Böylece sonucu gördükten sonra işimize gelen ölçütü seçme şansımız olmadı.

| Model (aynı 51 val karosu) | mAP50 | Hücre dengeli doğruluk | Kayalık hücre recall |
| --- | --- | --- | --- |
| v1 (150 karo) | 0,308 | 0,692 | 0,36 |
| **v2 (250 karo)** | **0,330** | **0,778** | **0,56** |

İki ölçüt de arttığı için v2 seçildi.

**Not:** Ultralytics kendi doğrulamasında v2 için 0,355 diyor. Tablodaki 0,330, iki model için de aynı kodla (`eval_merged.py`) hesaplandı. İkisi de doğru; ölçüm kodu farklı.

### 3.6 Ölçüler günlük dille

Bir hazine avı düşün: haritada 10 gerçek kaya var, model 8 yere "kaya" dedi.

- **IoU (örtüşme):** Modelin kutusu ile gerçek kutunun ne kadar üst üste bindiği (kesişim ÷ birleşim). IoU ≥ 0,5 ise "buldu" sayılıyor.
- **Precision (kesinlik):** "Kaya dediklerinin yüzde kaçı gerçekten kaya?" 8 dediğinden 6'sı doğruysa 6/8 = 0,75. Yanlış alarm ölçüsü.
- **Recall (duyarlılık):** "Gerçek kayaların yüzde kaçını buldu?" 10 kayadan 6'sını bulduysa 6/10 = 0,6. Kaçırma ölçüsü. Astronot için en önemlisi bu: kaçırılan kaya, yanlış alarmdan pahalı. Kayalık hücre recall'u 0,36'dan 0,56'ya çıktı, yani her 100 kayalık hücreden 36 yerine 56'sını buluyoruz.
- **mAP50:** Güven eşiğini 0'dan 1'e kaydırınca oluşan precision–recall eğrisinin altındaki alan (IoU 0,5'te), sınıfların ortalaması. Tek sayıyla "kutular ne kadar doğru". Bizimki 0,33. Düşük görünüyor, ama kum alanı gibi sınırı belirsiz nesnelerde kutunun tam tutması zor: model "kum alanı"nı biraz farklı boyutta çizince eşleşme sayılmıyor.
- **Hücre dengeli doğruluk:** Asıl kullanım ölçüsü. Kutuyu bırakıp 80 m'lik parçaları "kum / kayalık / düz" diye sınıflandırıyoruz ve her sınıfın doğruluğunun ortalamasını alıyoruz.
  - Val'deki 204 alt karonun 78'i kum, 71'i düz, 55'i kayalık.
  - "Dengeli" olması önemli: "her şeye kum de" diyen tembel bir model düz doğrulukta 0,38 alırdı, dengeli doğrulukta ise 0,33.
  - Bizim modelimiz: doğruluk 0,80, dengeli doğruluk 0,78. 55 kayalık parçanın 31'ini buluyor; recall 0,56 buradan geliyor.
- **AUC:** Bölüm 5'te, doğrulamada.

### 3.7 Çıkarım: kutudan harita yoğunluğuna (`ml/infer.py`)

- Model 1146 karonun hepsinde çalıştı. Bunlar 1088 temiz ve 58 dokusuz karo; toplam ~29 km².
- Süre: RTX 5090'da 17 saniye.
- Kutular haritada çizilmiyor; 70 m'lik hücrelere yoğunluk olarak toplanıyor:

```python
kum_ml = np.where(valid, np.clip(kum, 0, 1), np.nan)
kaya_ml = np.where(valid, np.clip(np.maximum(rock_area / ROCK_AREA_REF, rocks_ha / ROCK_HA_REF), 0, 1), np.nan)
```

- **`kum_ml`:** Hücrenin yüzde kaçını kum kutuları kaplıyor (0–1). Her karo 2,5 m aralıklı noktalarla örnekleniyor; üst üste binen kutular iki kez sayılmıyor.
- **`kaya_ml`:** İki ölçünün büyüğü alınıyor. Biri kaya alanı kaplaması ÷ 0,2, diğeri hektar başına kaya sayısı ÷ 6,25. Bölenler hücre sınıflandırmasındaki "kayalık" eşiğinin iki katı, böylece eşik tam 0,5'e denk geliyor.
- **`valid`:** HiRISE hücrenin yarısından azını kaplıyorsa değer NaN. Yarım yamalak veriyle hücre hakkında karar vermiyoruz.
- Sonuç: 5666 hücrede ML değeri var; bunların 2768'inde kum_ml ≥ 0,5.

> **Jüri sorarsa:** *"mAP50 0,33 düşük değil mi?"*
> Kutu düzeyinde düşük, çünkü kum alanı gibi sınırı belirsiz nesnelerde kutunun tam tutması zor; ama biz kutu çizmiyoruz, 70 m'lik hücrede yoğunluk çıkarıyoruz ve o ölçekte dengeli doğruluk 0,78. Asıl kanıt da rota testi: model eklenince skor gerçek rover rotasını ayırt etmeye başladı (AUC 0,50 → 0,65).
>
> *"Veri sızıntısını nasıl önlediniz?"*
> Komşu karolar aynı sahneyi paylaştığı için karoları 8-komşulukla gruplayıp her grubu ya train'e ya val'e koyduk; bu kontrolle ilk bölmemizde 30 val karosunun 8'inin sızdığını bulup düzelttik. Doğrulamada kullandığımız Perseverance rotası ise modele hiç verilmedi.

---

## 4. Web uygulaması

Tarayıcıda dört algoritma dosyası (Elif) ve arayüz (Gözde) var. Algoritma dosyaları arayüzden bağımsız; tarayıcı konsolundan da çağrılabiliyor ve `web/tests/` sayfalarıyla sınanıyor.

### 4.1 Cesium küresi

- CesiumJS normalde Dünya'yı çizer. Biz varsayılan elipsoidi Mars yaptık: ekvator yarıçapı 3396,19 km, kutup 3376,2 km.

```javascript
const MARS = new Cesium.Ellipsoid(MARS_RADII.equatorial, MARS_RADII.equatorial, MARS_RADII.polar);
Cesium.Ellipsoid.default = MARS;               // Viewer kurulmadan önce: her şey Mars'ta çizilsin
```

- **Arka plan görüntüsü:** NASA/JPL Mars Trek'in karo servisinden geliyor.
- **Bizim katmanlarımız:** Eğim, termal, jeoloji, geçilebilirlik ve YOLO katmanları `SingleTileImageryProvider` ile çalışma alanının dikdörtgenine "yapıştırılıyor". PNG'lerimiz zaten derece ızgarasında üretildiği için doğrudan doğru yere oturuyor. Bölüm 2.1'deki ortak koordinat sisteminin karşılığı bu.
- **O₂ bölgeleri ve arama alanı:** `walkback.js` ve `rescue.js` bunları 256 × 256'lık bir canvas'a boyuyor; aynı yöntemle haritaya seriliyor.

### 4.2 `walkback.js`: Dijkstra ve O₂ bölgeleri

**Apollo'dan gelen fikir:** Apollo astronotları "walkback" kuralıyla çalışıyordu: araç bozulursa yürüyerek üsse dönebilecekleri mesafeden uzağa gitmiyorlardı. Bu kural sabit bir hızla hesaplanıyordu, yani haritada bir daireydi. Biz bu sınırı araziye, nabza, yüke ve kalan O₂'ye göre canlı hesaplıyoruz; sonuç daire değil, araziye göre şekil alan bir bölge.

**Adım 1: iki komşu hücre arasında yürüme süresi (`edgeMinutes`)**

```javascript
const tan = (G.elev[v] - G.elev[u]) / d;                       // yönlü eğim (+ yokuş yukarı)
if (Math.abs(tan) > TAN_MAX) return Infinity;                   // 25°'den dik: geçilmez
const vKmh = 6 * Math.exp(-3.5 * Math.abs(tan + 0.05)) * MARS_SUIT_FACTOR * loadFactor;
const tMin = (d / 1000 / vKmh) * 60;                           // mesafe / hız → dakika
return tMin * (1 + SCORE_WEIGHT * 0.5 * (G.score[u] + G.score[v]));   // zor zemin cezası
```

- **Satır 1:** Yükseklik farkını mesafeye bölüp eğimi buluyoruz. İşareti önemli: + yokuş yukarı, − yokuş aşağı.
- **Satır 2:** 25°'den dik kenarlar yok sayılıyor.
- **Satır 3:** Tobler'in yürüme formülü. İnsanın düz zeminde ~5 km/sa yürüdüğünü, en hızlı hafif yokuş aşağıda yürüdüğünü söyleyen deneysel bir formül. Üstüne iki çarpan ekledik:
  - ×0,6: Mars yerçekimi ve basınçlı giysi (varsayım).
  - ×(1 − yük/100): 6 kg yükle ×0,94.
- **Satır 4:** Mesafe ÷ hız = süre, dakikaya çeviriyoruz.
- **Satır 5:** İki hücrenin skor ortalamasıyla ceza ekliyoruz. Skor 0 ise süre aynı kalıyor, skor 1 ise 3 katına çıkıyor.

**Adım adım örnek: üs hücresinden doğu komşusuna**

Üs hücresi satır 128, sütun 136'da. Yükseklik −2567 m, doğu komşusu −2569 m, iki hücrenin skoru da 0,15. Ayşe 6 kg yük taşıyor, hücre 70,39 m.

| Adım | Doğuya (yokuş aşağı) | Geri, üsse (yokuş yukarı) |
| --- | --- | --- |
| tanθ = Δyükseklik / 70,39 | −2 / 70,39 = −0,0284 | +0,0284 |
| \|tanθ + 0,05\| | 0,0216 | 0,0784 |
| exp(−3,5 × …) | 0,927 | 0,760 |
| hız = 6 × … × 0,6 × 0,94 | 3,14 km/sa | 2,57 km/sa |
| süre = 0,07039 km / hız × 60 | 1,35 dk | 1,64 dk |
| × (1 + 2 × 0,15) = × 1,3 | **1,75 dk** | **2,13 dk** |

Aynı iki hücre arasında gidiş ile dönüş farklı sürüyor. Bu yüzden dönüş süresini ayrıca hesaplıyoruz. Testte de görülüyor: üs → Three Forks 77 dk, Three Forks → üs 74 dk.

**Adım 2: Dijkstra, yani en kısa süreyi bulmak**

Dijkstra bir haritada bir noktadan diğer bütün noktalara en kısa yolu bulan klasik algoritma. Bizde "kısa" mesafe değil, süre.

```javascript
dist[src] = 0; heap.push(src, 0);                   // başlangıç: 0 dk, diğer her yer ∞
while (heap.size) {
  const u = heap.pop();                             // kuyruktaki EN KISA süreli hücreyi al
  if (done[u]) continue;
  done[u] = 1;                                      // bu hücrenin süresi artık kesin
  for (let k = 0; k < 8; k++) {                     // 8 komşusuna bak
    ...
    const nd = dist[u] + t;                          // u üzerinden v'ye gitmek
    if (nd < dist[v]) { dist[v] = nd; prev[v] = u; heap.push(v, nd); }   // daha kısaysa güncelle
  }
}
```

Günlük dille: Göle taş attığını düşün. Dalga her yöne yayılıyor, ama çamurlu yerde yavaş, düz yerde hızlı ilerliyor. Dijkstra dalganın her hücreye ilk ne zaman vardığını kaydediyor. `heap` (öncelik kuyruğu) "sıradaki en erken varılan hücre hangisi?" sorusunu hızlı cevaplıyor. `prev` ise her hücreye nereden gelindiğini tutuyor; rotayı geriye doğru okumak için.

**Adım 3: O₂ bölgeleri**

```javascript
const mult = o2Multiplier(hr);                // çarpan = 1 + (nabız − 90) / 100
const avail = o2Min / mult;                   // kullanılabilir yürüme süresi
const out = dijkstra(s, loadKg, false).dist;  // astronottan her hücreye: gidiş
const home = homeTimes(base, loadKg);         // her hücreden üsse: dönüş (ters kenarlarla)
...
const t = out[i] + home[i];                   // "oraya git, oradan üsse dön"
if (G.blocked[i]) cls[i] = 4;
else if (t <= avail / GREEN_MARGIN) cls[i] = 1;   // YEŞİL: %25 pay kalıyor
else if (t <= avail) cls[i] = 2;                  // SARI: dönülür ama pay yok
else cls[i] = 3;                                  // KIRMIZI: dönülemez
```

- İki Dijkstra çalışıyor: astronottan her hücreye (gidiş) ve her hücreden üsse (dönüş). Dönüş Dijkstra'sında kenar yönleri ters çevriliyor, çünkü yokuşlar ters dönüyor.
- Bir hücrenin rengi "oraya gidip oradan üsse dönmek" için gereken toplam süreye bakıyor.
- O₂ çarpanı: nabız 90 referans; her +10 atım tüketimi %10 artırıyor.

**Adım adım örnek: Ayşe üste, O₂ 480 dk, 6 kg yük** (test e8)

| | Nabız 85 (sakin) | Nabız 150 (panik; Apollo 14'te Shepard'ın nabzı) |
| --- | --- | --- |
| Çarpan | 1 + (85 − 90)/100 = **0,95** | 1 + (150 − 90)/100 = **1,60** |
| Kullanılabilir süre | 480 / 0,95 = **505 dk** | 480 / 1,6 = **300 dk** |
| Yeşil eşiği (÷ 1,25) | **404 dk** | **240 dk** |
| Three Forks: 77 gidiş + 74 dönüş = 151 dk | yeşil | yeşil |
| Cheyava Falls: gidiş ≥ 279 + dönüş 260 dk | kırmızı (> 505) | kırmızı |
| Yeşil bölge alanı | **130,1 km²** | **46,85 km²** |

Ayşe panikleyince güvenli bölgesi 130'dan 47 km²'ye iniyor. Bütün harita ~30 ms'de yeniden hesaplanıyor (ilk seferde 69 ms; bölüm 1).

### 4.3 `eva.js`: plan, dönüş noktası, Go/No-Go

`Eva.plan` bir astronot ve durak listesi alıyor. Her bacak için `Walkback.path` ile rota bulup zaman çizelgesi kuruyor.

**Plana eklenen gerçekçilik:**

```javascript
const fatigue = (tMin) => 1 + FATIGUE_PER_HOUR * (tMin / 60);   // her saat %5 yavaşlama
...
const minutes = r.minutes * fat;                // bacak süresi = Dijkstra süresi × yorgunluk
...
load += s.sampleKg ?? SAMPLE_KG;                // durakta 1 kg numune → sonraki bacak daha ağır
```

- **Yorgunluk:** Bacak başladığında geçen her saat için süre %5 uzuyor. SEXTANT saha testlerinde gerçek süre tahminden uzun çıkmıştı.
- **Numune:** Her durakta 1 kg numune toplanıyor; dönüş daha ağır.

**Adım adım örnek: demo planı** (test e11). Ayşe O₂ 480 dk, nabız 85 → çarpan 0,95, yük 6 kg. Rota: Üs → Delta önü (40 dk kalış) → Three Forks (30 dk kalış) → Üs.

| Bacak | Başlangıç | Yorgunluk | Yük | Süre | Mesafe |
| --- | --- | --- | --- | --- | --- |
| Üs → Delta önü | T+0 | 1 + 0,05 × 0 = ×1,00 | 6 kg | 80 dk | 2,65 km |
| Delta önü → Three Forks | T+120 | 1 + 0,05 × 2 = ×1,10 | 7 kg | 8 dk | 0,27 km |
| Three Forks → Üs | T+158 | 1 + 0,05 × 158/60 = ×1,13 | 8 kg | 85 dk | 2,60 km |

- **Toplam:** 243 dk, 5,52 km; bunun 173 dk'sı yürüyüş.
- **Harcanan O₂:** 243 × 0,95 = 230,9 dk. Kalan: 480 − 230,9 = **249 dk** (%52).
- **Batarya:** 100 − 12,5 × 243/60 = **%49**. Su da aynı varsayımla %49.

**Dönüş noktası:** "Bu noktayı geçersen O₂ dönüşe yetmez."

```javascript
const home = W().timeHome({ lon, lat }, { loadKg: leg.loadKg, base }) * fatigue(tm);
const need = (tm + home) * m;              // buraya kadar harcanan + buradan üsse dönüş
if (need > o2 * ratio) { ... return prev; }   // ilk aştığı yerin bir öncesi = dönüş noktası
```

Rotanın her hücresinde şunu soruyoruz: "Buraya kadar geçen süre ile buradan üsse dönüş süresinin toplamı × çarpan, O₂'yi aşıyor mu?" İlk aştığı hücrenin bir öncesi dönüş noktası. `ratio` 1 ise dönüş noktası, 0,75 ise "%25 pay" noktası.

**Örnek (test e11, senaryo B):** Aynı plan, ama Ayşe'nin O₂'si 220 dk ve nabzı 150 (çarpan 1,6).
- Koşul: (t + dönüş) × 1,6 > 220, yani t + dönüş > 137,5 dk.
- Test bunun **T+67'de** olduğunu buldu. Delta önüne giderken 67. dakikada geri dönmesi gerekiyor.
- %25 pay noktası T+51.
- Plan tamamlansaydı dönüşte O₂ −169 dk olurdu. Karar NO-GO.

**Go/No-Go listesi:** 7 kontrol; her biri "GO", "DİKKAT" ya da "NO-GO". Demo planında:

| Kontrol | Kural | Demo sonucu |
| --- | --- | --- |
| O₂ | Dönüş noktası yok ve dönüşte ≥ %25 | GO (%52) |
| Gün batımı | Çıkış gündüz, dönüş gün batımından ≥ 30 dk önce | GO (dönüş 13:18 LMST, gün batımı 18:38) |
| Kum tuzağı | Rota `sand` hücresinden geçiyor mu? | GO (yok) |
| Eğim | Rotada > 15° kenar var mı? | GO (en dik 4,1°) |
| Telsiz | Habitat anteniyle görüş hattı | DİKKAT: ~126 dk görüş yok; arkadaş röle olmalı |
| Batarya | Dönüşte ≥ %20 | GO (%49) |
| Su | Dönüşte ≥ %10 | GO (%49) |

**Telsiz görüş hattı:** Habitat anteni 10 m, giysi anteni 2 m yükseklikte. Aradaki doğru arazinin üstünde kalıyor mu? Mars küre olduğu için her örneğe bir "tümsek" ekleniyor:

```javascript
const bulge = (f * D * (1 - f) * D) / (2 * MARS_R);              // eğrilik: h = d1·d2 / 2R
if (G.elev[i] + bulge > zb + (zp - zb) * f) return false;        // arazi doğrunun üstündeyse görüş yok
```

### 4.4 `marstime.js`: Mars saati

Mars'ta bir gün (sol) 88.775,244 saniye, yani 24 saat 39 dakika 35 saniye. Uygulamanın her yerinde Mars saatini gösteriyoruz. Gün batımı kontrolü de buna bağlı. Algoritma NASA GISS'in Mars24'ü; adımları koddaki harf–rakam etiketleriyle aynı (A-1, B-1, C-2...).

**Adım adım örnek:** Rover fotoğrafı kaydı 2022-12-20 16:07:19 UTC (D7). Yer: üs (77,4509°D).

| Adım | Formül | Değer |
| --- | --- | --- |
| A-1 Julian tarihi (UT) | 2440587,5 + ms / 86.400.000 | 2459934,1717 |
| A-2 Karasal Zaman (TT) | + 69,184 s (TT − UTC, artık saniyeler dahil) | 2459934,1725 |
| A-3 J2000'den bu yana gün | JD_TT − 2451545,0 | 8389,17 |
| C-2 Mars Sol Tarihi (MSD) | (Δt − 4,5) / 1,0274912517 + 44796 − 0,0009626 | 52956,334 |
| C-3 Mars ortalama saati (MTC, 0° boylamda) | (24 × MSD) mod 24 | 8,0105 sa (08:00) |
| C-4 Yerel ortalama güneş saati (LMST) | MTC + 77,4509 / 15 | 13,174 sa = **13:10** |
| Sol | ⌊yerel MSD⌋ − ⌊inişteki yerel MSD⌋ = 52956 − 52304 | **Sol 652** |

- **Ara kavramlar:** 1,0274912517, bir solün kaç Dünya günü olduğu. `/15` ise boylamı saate çeviriyor (360° = 24 saat → 15° = 1 saat).
- **Doğrulama:** Test, fotoğrafın çekildiği Three Forks konumu (77,4078°D) için LMST 13:10:16 hesaplıyor. Kayıttaki değer 13:10:20; fark 4 saniye. Sol 652 birebir tutuyor. İkinci kontrol Ingenuity Uçuş 1: Sol 58, 12:33 tutuyor.

**Gün batımı:** Güneşin dik açısından (δ) ve enlemden (φ):
- Formül: `cos H₀ = −tan φ · tan δ`, gün batımı = 12 + H₀/15 (yerel gerçek güneş saati).
- Kalan süre Mars saatinden Dünya dakikasına çevriliyor: 1 Mars saati = 61,65 Dünya dakikası.

**Dünya–Mars gecikmesi:**
- JPL'nin yörünge elemanlarıyla iki gezegenin Güneş'e göre konumu, Kepler denklemiyle hesaplanıyor.
- Aradaki uzaklık ışık hızına bölünüyor.
- Örnek: 12 Ocak 2025 en yakın geçişinde 0,642 AU, yani 5,34 dk. Bu yüzden acil durumda Dünya'ya sormak yerine kararı yerinde veren bir araç gerekiyor.

### 4.5 `rescue.js`: arama alanı, İHA, kurtarma

Senaryo: "Telsiz koptu." Üç soru var: Astronot nerede olabilir? İHA alanı nasıl tarar? Arkadaşı onu O₂'si bitmeden getirebilir mi?

**Adım adım örnek** (test e13):
- Ayşe planı yürüyor. Çıkıştan 60 dk sonra telsiz kopuyor.
- O anki O₂: 480 − 60 × 0,95 = 423 dk.
- Nabzı 150'ye çıkıyor (çarpan 1,6). Kopma 20 dk sonra fark ediliyor.

**1) Arama alanı**

```javascript
const o2Budget = Math.max(0, input.lost.o2LeftMin / mult);       // O₂'si ne kadar yürümeye yeter
const budget = Math.min(input.elapsedMin ?? o2Budget, o2Budget);  // ama en fazla geçen süre kadar yürümüş olabilir
...
if (tt[i] <= budget) {
  const w = (1 / (1 + tt[i])) * (nearRoute && nearRoute[i] ? ROUTE_BONUS : 1);
```

- **Bütçe:** min(20, 423 / 1,6 = 264) = **20 dk**. Ayşe en fazla 20 dakikalık yürüme mesafesinde.
- **Ulaşılabilir hücreler:** Son konumdan Dijkstra süresi ≤ 20 dk olanlar. Toplam **1,07 km²**.
- **Ağırlık:** w = 1 / (1 + yürüme süresi). Yakın ve kolay ulaşılan yer daha olası. Planlanan rotaya 150 m'den yakın hücreler ×2 (insan genelde plana sadık kalır). Ağırlıklar toplamı 1'e bölünüyor.
- **En olası alanlar:** Hücreler olasılığa göre sıralanıyor. Olasılığın %50'sini toplayan en küçük alan **0,25 km²**, %90'ını toplayan **0,79 km²**.
- **Süreye bağlılık:** Geçen süre arttıkça alan büyüyor: 5 dk'da 0,07, 20 dk'da 1,07, 40 dk'da 4,43 km².

**2) İHA zikzak (biçerdöver) rotası**

```javascript
const swath = 2 * o.altitudeM * Math.tan((o.fovDeg * Math.PI) / 360);   // kameranın yerde gördüğü genişlik
const spacing = swath * (1 - o.overlap);                                 // şeritler arası aralık
```

- **Şerit genişliği:** 2 × 100 m × tan(30°) = **115 m**.
- **Aralık:** %20 örtüşmeyle 115 × 0,8 = **92 m**.
- **Yön:** Alanın uzun ekseni boyunca uçuluyor, daha az dönüş için. Uzun eksen, olasılık ağırlıklı ana bileşenden bulunuyor. Sonuç: 11 şerit, yön 106°.
- **Uçuş:** Rota 14,5 km, 24,2 dk. Tek batarya 20 dk dayandığı için 2 batarya gerekiyor.
- **Tarama sırası:** İki başlangıç ucu deneniyor, olasılığı daha erken tarayan seçiliyor. Olasılığın %50'si **11,6 dk**'da, %90'ı **21,6 dk**'da taranıyor.

**3) Arkadaşın kurtarma rotası ve karar**

```javascript
const found = foundAfter == null ? arriveAfter : foundAfter;   // İHA'nın %90 bulma anı
const meet = Math.max(found, arriveAfter);                     // buluşma: ikisinden geç olanı
const atMeet = input.lost.o2LeftMin - meet * mL;               // kayıp astronotun buluşmadaki O₂'si
const atBase = atMeet - backMin * mL;                          // birlikte üsse dönünce kalan
const survivable = buddy.status !== "red" && atMeet > 0 && atBaseWithSpare >= 0;
```

| Adım | Hesap | Sonuç |
| --- | --- | --- |
| Ali'nin rotası | 60 dk gidiş + birlikte dönüş ~57,5 × 1,2 (yorgun arkadaşla %20 yavaş) | 60 + 69 dk |
| Ali'nin O₂ ihtiyacı (nabız 80 → çarpan 0,9) | (60 + 69) × 0,9 | 116 / 480 dk → **YEŞİL** |
| Ali'nin varışı (kopmadan itibaren) | 20 geçen + 10 giyinme + 60 yürüme | T+90 |
| İHA'nın bulması | 20 geçen + 21,6 (%90) | T+42 |
| Buluşma | max(42, 90) | **T+90** |
| Ayşe'nin buluşmadaki O₂'si | 423 − 90 × 1,6 | **279 dk** |
| Üsse varınca | 279 − 69 × 1,6 | **169 dk** → kurtarılabilir |

**Neden buluşma = max?** Konumu bilinmeyen birine gidemezsin; önce İHA bulmalı. Bu kuralı sonradan düzelttik: eski sürüm İHA'nın bulma süresini hesaba katmıyordu. Test bunun farkını gösteriyor:
- Kopma **120 dk** geç fark edilirse alan çok büyüyor. İHA %90'ı ancak 629 dk'da tarıyor, buluşma T+749.
- Ayşe'nin O₂'si buluşmadan çok önce bitiyor; doğru karar "MÜMKÜN DEĞİL".
- Eski kural yalnızca Ali'nin varışına (T+190) bakıp "kurtarılabilir" derdi.

**Adlar:** Mesajlar profildeki adlarla kuruluyor, ekler Türkçe ünlü uyumuyla (`genitive`): Ayşe'nin, Ali'nin, Oğuz'un, Ümit'in. Ali kaybolup Ayşe kurtarırsa mesajlar doğru isimlerle çıkıyor.

> **Jüri sorarsa:** *"O₂ bölgeleri nasıl hesaplanıyor, ne kadar hızlı?"*
> Her hücre için Dijkstra ile "oraya git, oradan üsse dön" süresini buluyoruz; bu süre O₂'nin 1/1,25'ine sığıyorsa yeşil, O₂'ye sığıyorsa sarı, sığmıyorsa kırmızı. Nabız arttıkça O₂ tüketimi artıyor ve hesap 65.536 hücrede tarayıcıda ~30 ms'de tekrarlanıyor: Ayşe'nin nabzı 85'ten 150'ye çıkınca yeşil bölge 130'dan 47 km²'ye iniyor.
>
> *"Mars'ta GPS yok, astronotu nasıl bulursunuz?"*
> Son bilinen konumdan, geçen süre ve kalan O₂ kadar yürünebilecek hücreleri Dijkstra ile bulup kolay ulaşılan yerlere daha yüksek olasılık veriyoruz; demoda 20 dk sonra alan 1,07 km². İHA bu alanı uzun ekseni boyunca zikzakla tarıyor ve olasılığın yarısını 11,6 dakikada kapsıyor.

---

## 5. Doğrulama: Perseverance rotası

### 5.1 Fikir

Elimizde "astronot şuradan güvenle geçti" diye bir yer-gerçeği yok; Mars'ta hiç astronot yürümedi. Ama Perseverance'ın gerçekten sürdüğü 46 km'lik yolu biliyoruz (D2). Rover ekibi her sürüşü tehlikeden kaçınarak planlıyor.

O halde test şu: **Skorumuz araziyi doğru okuyorsa, rover'ın geçtiği hücreler geçmediği hücrelerden daha kolay (daha düşük skorlu) görünmeli.**

Önemli: Rota modele ya da füzyona hiç verilmedi; yalnızca sınavda kullanıldı.

### 5.2 Nasıl yapıldı (`scripts/validate.py`)

1. **Rotayı hücreye çevir:** D2'deki çizgiler 10 m'de bir örneklendi; böylece 70 m'lik hiçbir hücre atlanmıyor. Sonuç **397 rota hücresi**, bunların **52**'si HiRISE kapsamında.
2. **İki skoru karşılaştır:** YOLO'suz skor (`score_base`) ile YOLO'lu skor (`score`).
3. **Ölçü olarak AUC:**

```python
def auc(route_vals, other_vals):
    """P(rota < diğer) + 0,5·P(eşit): Mann–Whitney U / (n1·n2)"""
    ...
    u_a = ranks[:len(a)].sum() - len(a) * (len(a) + 1) / 2   # rota hücresinin BÜYÜK olduğu çift sayısı
    return 1 - u_a / (len(a) * len(b))
```

**AUC'yi günlük dille:** Rota üstünden rastgele bir hücre, rota dışından rastgele bir hücre seç. "Rota hücresi daha kolay görünüyor" olasılığı AUC'dir.
- 0,5: yazı tura; skor rotayı hiç ayırt etmiyor.
- 1,0: her seferinde doğru.
- 0,649: 100 çiftin yaklaşık 65'inde rota hücresi daha kolay görünüyor.

Kod bunu bütün çiftleri tek tek denemeden, değerleri sıralayıp sıra toplamıyla hesaplıyor (Mann–Whitney yöntemi).

4. **Bootstrap:** 52 hücre az. Rota hücrelerinden 1000 kez yerine koyarak yeniden örnek çekip AUC farkının ne kadar oynadığına baktık. Sonuç %95 güven aralığı.

### 5.3 Sonuçlar ve anlamları

| Bölge | | Rota medyan skoru | Rota dışı medyan | AUC |
| --- | --- | --- | --- | --- |
| HiRISE kapsamı (52 rota hücresi) | YOLO'suz | 0,397 | 0,395 | **0,498** |
| | YOLO'lu | 0,360 | 0,409 | **0,649** |
| Tüm alan (397 rota hücresi) | YOLO'suz | 0,216 | 0,224 | 0,562 |
| | YOLO'lu | 0,216 | 0,224 | 0,571 |

- **0,498 → 0,649:** Jeoloji, eğim ve termalle kurduğumuz skor HiRISE kapsamında rotayı hiç ayırt edemiyordu. YOLO eklenince ayırt etmeye başladı. Bootstrap'ta farkın %95 aralığı **[+0,12, +0,18]**; 1000 örneğin hiçbirinde fark ≤ 0 değil. Kendi modelimizin ölçülebilir katkısı bu.
- **Kum en net sinyal:** Rotadaki 52 hücrenin **hiçbiri** kumlu değil (kum_ml ≥ 0,5 olan hücre %0). Çevredeki hücrelerin **%49,3**'ü kumlu. Kum yoğunluğunun tek başına AUC'si 0,790. Rover ekibi YOLO'nun kum dediği yerlerden belirgin biçimde kaçınmış.
- **Kaya sinyal vermiyor:** Kaya yoğunluğunun AUC'si 0,510, yani ayırt etmiyor. Model 2. partide iki kat fazla kaya bulmasına rağmen değişmedi. Olası açıklamalar:
  - Rover ekibi metre ölçeğindeki kayaları 70 m ölçeğinde önemsemiyor olabilir.
  - Rotanın geçtiği delta önü zaten kayalı olabilir.
  Bunu sınırlama olarak raporluyoruz.
- **Tüm alanda etki küçük (0,562 → 0,571):** Rotanın yalnızca 52/397 hücresi HiRISE kapsamında. Kapsam dışında model hiçbir şey değiştirmiyor.
- **Rotanın %100'ü geçilebilir:** Bizim grid'imizde rover'ın geçtiği hiçbir hücre "geçilmez" değil. Ama geçilmez hücreler zaten %0,2 olduğu için bu tek başına güçlü bir kanıt değil; asıl kanıt AUC.

> **Jüri sorarsa:** *"Modelin doğru olduğunu nereden biliyorsunuz?"*
> Perseverance'ın gerçekten sürdüğü yolu modele hiç göstermeden sınav olarak kullandık: rover ekibi tehlikeden kaçındığı için rota hücreleri daha kolay görünmeliydi. YOLO'suz skor HiRISE kapsamında rotayı ayırt edemiyordu (AUC 0,50), YOLO ile 0,65'e çıktı ve rotadaki hücrelerin hiçbiri kumlu değilken çevrenin yarısı kumlu.
>
> *"Rover rotası astronot için doğru bir referans mı?"*
> Tam değil: tekerlek kuma insandan daha duyarlı ve rota bilim hedeflerine de gidiyor. Ama elimizdeki tek gerçek "tehlikeden kaçınma" verisi bu; ölçtüğümüz kumdan kaçınma da astronot için geçerli, Opportunity ve Spirit'in başına gelen buydu.

---

## 6. Varsayımlar ve sınırlar

### 6.1 Bizim seçtiğimiz sayılar

Bu sayılar ölçülmedi, seçildi. Her birinin gerekçesi kodda yorum olarak yazılı. Gerçek EVA verisi gelirse kalibre edilebilirler.

| Sayı | Nerede | Neden bu değer |
| --- | --- | --- |
| Füzyon ağırlıkları 0,4 / 0,25 / 0,15 / 0,2 | `prep_layers.py` | En büyük tehlike eğim, sonra kum (Spirit, Opportunity). Toplam 1 |
| Jeoloji katsayıları (`GEO_UNITS`) | `prep_layers.py` | USGS birim tanımlarından takdirle; ör. eolyen birim yürünebilirlik 0,30 |
| Geçilmez eğim 25° | `prep_layers.py`, `walkback.js` | Giysili astronot için güvenli üst sınır |
| Geçilmez skor 0,8 | `prep_layers.py` | En kötü arazi; bu alanda hiçbir hücre aşmadı |
| Tobler × 0,6 | `walkback.js` | Mars yerçekimi + basınçlı giysi düzeltmesi |
| Yük çarpanı 1 − kg/100 | `walkback.js` | 6 kg → %6 yavaşlama; basit doğrusal varsayım |
| Zemin cezası × (1 + 2·skor) | `walkback.js` | Zor zemin süreyi en fazla 3 katına çıkarır |
| O₂ çarpanı 1 + (nabız − 90)/100 | `walkback.js` | Nabız 90 referans; nabız 150'de × 1,6 |
| Yeşil pay 1,25 | `walkback.js`, `eva.js`, `rescue.js` | %25 güvenlik payı; üç dosyada aynı |
| Yorgunluk %5/saat | `eva.js` | SEXTANT saha testinde gerçek süre tahminden uzun çıktı |
| Numune 1 kg/durak | `eva.js` | Dönüş daha ağır |
| Batarya ve su %12,5/saat (8 saat) | `eva.js` | xEMU sınıfı giysi varsayımı |
| Gün batımı payı 30 dk | `eva.js` | Karanlıkta yürümemek için |
| Anten 10 m (habitat), 2 m (giysi) | `eva.js` | Görüş hattı varsayımı |
| Rotaya yakınlık ×2 (150 m) | `rescue.js` | İnsan genelde plana sadık kalır |
| İHA: 100 m irtifa, 60° görüş, %20 örtüşme, 10 m/s, 20 dk | `rescue.js` | Ingenuity'nin hızına yakın; irtifa ve batarya varsayım |
| Giyinme 10 dk, birlikte dönüş × 1,2, yedek O₂ 60 dk | `rescue.js` | Kurtarma senaryosu varsayımı |
| YOLO–jeoloji ağırlığı 0,5 / 0,5 | `prep_layers.py` | Kalibre edecek yer-gerçeği yok; en az varsayım |
| Güven eşiği 0,25 | `infer.py` | Ultralytics varsayılanı; val'e göre ayarlanmadı (aşırı uydurmamak için) |
| Kaya → kaya alanı sınırı 10 m | `infer.py` | Etiketlerde kaya p90 9,4 m, kaya_alani p10 10,8 m (ölçümden) |
| kaya_ml bölenleri 0,2 ve 6,25/ha | `infer.py` | Hücre "kayalık" eşiğinin 2 katı; eşik 0,5'e denk gelsin |
| HiRISE kapsama alt sınırı %50 | `infer.py` | Yarım veriyle hücre hakkında karar vermemek için |
| Termal %2–98, HiRISE germe %0,5–99,5 | `prep_layers.py`, `tile_for_yolo.py` | Aykırı pikseller ölçeği bozmasın |
| Dokusuz karo eşiği: alt %5 | `tile_for_yolo.py` | Düz toz/gölge; etiketlenecek nesne yok |
| Val oranı %20, seed 0 / 42 | `merge_v2.py`, `tile_for_yolo.py` | Standart oran; sonuçlar tekrarlanabilsin |

### 6.2 Sınırlar (dürüstçe söyleyeceklerimiz)

- **Model:**
  - Val küçük: 51 karo. Sonuçlar tek tohumlu tek bir koşudan.
  - Kaya tespiti zayıf: kaya mAP50 0,20; kaya rotayı ayırt etmiyor (AUC 0,51).
  - 1. parti etiketlerinde çukur kümeleri tutarsız; ölçtük ama düzeltmedik.
- **Kapsam:** YOLO yalnızca HiRISE mozaiğinin kapsadığı ~29 km²'de çalışıyor. Üs, delta önü ve Three Forks kapsam dışında; orada skor jeoloji, eğim ve termalden geliyor.
- **Doğrulama:**
  - 52 rota hücresi az ve hepsi kapsamın kuzey kenarında.
  - Rover bir astronot değil.
  - Komşu rota hücreleri birbirine benzediği için bootstrap aralığı alt sınır olarak okunmalı.
- **Fizyoloji:** O₂, yorgunluk, batarya katsayıları varsayım. Gerçek EVA verisiyle kalibre edilmedi.
- **Çözünürlük:** 70 m'lik hücre, metre ölçeğindeki tek bir kayayı göstermez; rota "genel olarak kolay koridoru" bulur, astronot yerinde gözle karar verir.

> **Jüri sorarsa:** *"Füzyon ağırlıkları nereden geliyor?"*
> Bunlar bizim varsayımımız: en büyük tehlike eğim (0,4), sonra kum (0,25), çünkü Mars'ta kaybedilen iki rover kumda kaldı. Ağırlıklar kodda tek yerde tanımlı; gerçek EVA verisi gelirse rota doğrulamasındaki AUC'yi en yükseğe çıkaracak şekilde kalibre edilebilir.

---

## 7. Sözlük

**Veri ve harita**

- **Projeksiyon:** Kürenin yüzeyini düz bir haritaya çevirme kuralı. Her dosya farklı kural kullanınca aynı piksel farklı yere düşer; bu yüzden hepsini tek sisteme çevirdik.
- **Yeniden örnekleme (resampling):** Bir rasteri farklı bir piksel ızgarasına taşımak. `average` hücreye düşen piksellerin ortalamasını, `bilinear` dört komşudan yumuşak ara değeri alır.
- **Raster / vektör:** Raster piksellerden oluşan görüntüdür (DEM, termal). Vektör çizgi ve poligonlardan oluşur (jeoloji haritası, rover izi).
- **Rasterize:** Poligonları piksel ızgarasına boyamak.
- **NoData:** "Burada ölçüm yok" işareti (ör. 0 ya da −3,4·10³⁸). Gerçek bir değer gibi hesaba girmesin diye NaN'a çevrilir.
- **NaN:** "Sayı değil." Hesaplarda eksik veriyi taşır. Eğitimde kayıp NaN olursa hesap taşmış demektir.
- **Normalizasyon:** Farklı birimdeki değerleri (derece, TIU) ortak bir ölçeğe (0–1) çekmek, ki toplanabilsinler.
- **Yüzdelik dilim (percentile):** p2, değerlerin %2'sinin altında kaldığı sayı. Aykırı uçları kırpmak için kullandık.
- **DEM (sayısal yükseklik modeli):** Her pikselde yükseklik. Eğimi ondan hesaplıyoruz.
- **Hillshade:** DEM'den üretilen, ışık vurmuş gibi gölgeli arazi görüntüsü. Yalnızca görsel.
- **Termal eylemsizlik:** Zeminin ısınıp soğumaya direnci. Düşükse gevşek kum ya da toz, yüksekse sert kaya. Birimi TIU.
- **Eolyen:** Rüzgârın oluşturduğu (kum dalgaları, kumullar).
- **Grid / hücre:** Haritayı 256 × 256 kareye bölmek; her kare 70 m ve tek bir değer taşıyor.
- **Füzyon:** Birden fazla katmanı ağırlıklı toplamla tek skora birleştirmek.
- **Karo (tile):** Büyük görüntüden kesilen 640 × 640 piksellik parça.
- **En uzak nokta örneklemesi:** Her adımda seçilenlerden en uzak adayı ekleyerek örnekleri haritaya yaymak.

**Model**

- **YOLO:** Görüntüye bir kez bakıp nesnelerin etrafına kutu çizen tespit modeli.
- **Transfer öğrenme:** Başka bir veride önceden eğitilmiş modelden başlayıp kendi verinle ince ayar yapmak.
- **Epoch:** Eğitim verisinin bir kez baştan sona gösterilmesi.
- **Batch:** Modelin bir adımda gördüğü örnek sayısı (bizde 16).
- **Öğrenme hızı (learning rate):** Her adımda ağırlıkların ne kadar değiştiği. Çok büyükse eğitim ıraksar.
- **Optimizer (SGD, AdamW):** Ağırlıkları güncelleme yöntemi.
- **fp16 / fp32 (AMP):** Sayıların 16 ya da 32 bit hassasiyetle tutulması. fp16 hızlı ama taşmaya daha açık.
- **Iraksama:** Kaybın düşmek yerine fırlaması; model öğrendiğini kaybeder.
- **Artırma (augmentation):** Eğitimde görüntüyü çevirme, parlaklık oynatma gibi yapay değişikliklerle çeşitlilik eklemek.
- **Aşırı öğrenme (overfitting):** Modelin genel kuralı değil eğitim örneklerini ezberlemesi. Train kaybı düşerken val kaybı yükselir.
- **Erken durdurma:** 20 epoch boyunca iyileşme yoksa eğitimi kesmek.
- **Train / val:** Modelin öğrendiği ve sınandığı ayrı karo kümeleri.
- **Veri sızıntısı:** Sınav (val) bilgisinin eğitime karışması. Bizde komşu karoların aynı sahneyi paylaşmasıyla oluşuyordu.
- **8-komşuluk / bağlı bileşen:** Kenar ya da köşeden değen karolar komşudur. Birbirine zincirle bağlı karolar bir bileşendir. Birleşim-bul (union-find) bunu hızlı bulan yöntem.
- **Ablation:** Bir şeyi değiştirip diğer her şeyi sabit tutarak etkisini ölçmek.
- **IoU:** İki kutunun kesişimi ÷ birleşimi; ne kadar örtüştükleri.
- **Precision (kesinlik):** "Bulduklarımın ne kadarı doğru?"
- **Recall (duyarlılık):** "Gerçeklerin ne kadarını buldum?"
- **mAP50:** IoU 0,5'te precision–recall eğrisinin altındaki alanın sınıf ortalaması. mAP50-95 aynı şeyin 0,5–0,95 arası IoU'larda ortalaması (daha katı).
- **Confusion matrix:** Hangi sınıfın hangi sınıfla karıştırıldığını gösteren tablo.
- **Dengeli doğruluk:** Her sınıfın kendi doğruluğunun ortalaması. Kalabalık sınıfın sonucu şişirmesini önler.
- **Güven eşiği:** Modelin kutusunu ancak güveni bu değerin üstündeyse saymak (bizde 0,25).

**Algoritmalar ve doğrulama**

- **Tobler formülü:** Eğime göre insan yürüme hızını veren deneysel formül.
- **Dijkstra:** Bir noktadan her noktaya en kısa (bizde en hızlı) yolu bulan algoritma.
- **Öncelik kuyruğu (heap):** "Sıradaki en küçük değer hangisi?" sorusunu hızlı cevaplayan yapı. Dijkstra'yı hızlandırır.
- **Yönlü eğim:** Yokuş yukarı ile aşağının farklı sürmesi; gidiş ve dönüş süresi bu yüzden farklı.
- **Dönüş noktası:** Rotada, geçilirse O₂'nin dönüşe yetmediği ilk yer.
- **Go/No-Go:** Yürüyüşten önce tek tek kontrol edilen evet/hayır listesi.
- **Görüş hattı:** İki anten arasındaki doğrunun araziye çarpmaması; çarparsa telsiz kesilir.
- **Biçerdöver (lawnmower) taraması:** Alanı paralel şeritlerle, her şeritte yön değiştirerek taramak.
- **Ana bileşen (ana eksen):** Bir nokta bulutunun en uzun yayıldığı yön. İHA bu yönde uçar.
- **AUC (Mann–Whitney):** Rastgele bir rota hücresinin rastgele bir rota dışı hücreden daha kolay görünme olasılığı. 0,5 = ayırt etmiyor.
- **Bootstrap:** Örnekten yerine koyarak tekrar tekrar çekip sonucun ne kadar oynadığını görmek.
- **Güven aralığı (%95):** Bootstrap sonuçlarının ortadaki %95'i; gerçek değerin muhtemelen düştüğü aralık.
- **Yer-gerçeği (ground truth):** Sahada doğrudan ölçülmüş, doğruluğundan emin olunan bilgi.

**Mars zamanı**

- **Sol:** Bir Mars günü, 24 sa 39 dk 35 sn. Perseverance'ın inişi Sol 0.
- **MSD (Mars Sol Tarihi):** Mars'ın sürekli gün sayacı (Dünya'daki Julian gününün karşılığı).
- **LMST / LTST:** Yerel ortalama ve yerel gerçek güneş saati. Gerçek saat, Mars'ın eliptik yörüngesi yüzünden ortalamadan sapar; farka zaman denklemi (EOT) denir.
- **Ls (güneş boylamı):** Mars'ın mevsimi; 0° kuzey yarımkürede ilkbahar başı.
- **AU (astronomik birim):** Dünya–Güneş ortalama uzaklığı, ~149,6 milyon km.

> **Jüri sorarsa:** *"Bu terimleri neden bu kadar dikkatle ayırdınız (ör. dengeli doğruluk)?"*
> Çünkü yanlış ölçü yanlış karar verdirir: sınıflar dengesiz olduğunda "her şey kum" diyen tembel bir model bile düz doğrulukta puan toplar (ilk val kümemizde 0,59). Dengeli doğrulukta o model 0,33'te kalıyor, bizimki 0,78; ölçüyü seçerken modelin gerçekten öğrenip öğrenmediğini görebileceğimiz ölçüyü seçtik.
