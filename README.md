# MarsTrail

Mars'ta yüzeyde yürüyen astronotun yürüyüşünü hazırlıktan acil duruma kadar yöneten, tarayıcıda çalışan görev aracı. NASA Space Apps Konya 2026.

**Canlı:** https://tayancelifnur.github.io/marstrail/ (telefonda da çalışır, sunucu gerekmez)

## Ne yapar?

| Aşama | Ekranda |
| --- | --- |
| Hazırlık | İki astronot (Ayşe, Ali): O₂, nabız, yük, batarya, su, radyasyon |
| Planlama | Araziyi ve kumu bilen rota, zaman çizelgesi, dönüş noktası, Go/No-Go listesi |
| Yürüyüş | Canlı O₂ takibi. Yeşil/sarı/kırmızı **O₂ bölgeleri** her zaman açık ve araziye göre şekil alıyor |
| Acil durum | Telsiz koparsa olasılıklı arama alanı, İHA zikzak rotası, arkadaşın kurtarma rotası |

Apollo'nun "yürüyerek dönebileceğin mesafe" kuralı sabit hızla hesaplanıyordu. MarsTrail bu sınırı nabza, yüke, kalan O₂'ye ve araziye göre canlı hesaplıyor. Ayşe'nin nabzı 85'ten 150'ye çıkınca güvenli bölge 130 → 47 km² oluyor.

## Veri ve model

- **Açık veri:** 8 veri seti (CTX DEM, THEMIS termal eylemsizlik, USGS SIM 3464 jeolojisi, HiRISE 25 cm mozaiği, Perseverance konumları, sürüş izi ve ham fotoğrafları, Ingenuity uçuşları). Ayrıntı: [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md).
- **Geçilebilirlik skoru:** `0,4·eğim + 0,25·kum + 0,15·kaya + 0,2·(1 − termal)`, 256 × 256 grid, 70 m hücre.
- **Kendi YOLOv8 modelimiz:** HiRISE'ta kum dalgası ve kaya buluyor. 250 karo elle kontrol edilerek etiketlendi; komşu karolar train ve val'de aynı tarafa kondu, yani sızıntı yok. Hücre düzeyi dengeli doğruluk 0,78.
- **Doğrulama:** Perseverance'ın gerçekten sürdüğü yol modele verilmedi.
  - HiRISE kapsamında skorun rotayı ayırt etme gücü (AUC) YOLO'suz 0,50, YOLO'lu 0,65.
  - Rotadaki hücrelerin %0'ı, çevredekilerin %49'u kumlu.
- **Sayı denetimi:** Sunumdaki her sayı kaynağıyla eşleştirildi: [docs/SAYI_DENETIMI.md](docs/SAYI_DENETIMI.md).

## Çalıştırma

```
python -m http.server 8000 --directory web
```

Ardından tarayıcıda `http://localhost:8000` adresini aç. Algoritma testleri `http://localhost:8000/tests/e8.html`, `e11.html` ve `e13.html` adreslerinde.

Veri hattını, modeli ve sunumu yeniden üretmek için:

```
py -3.12 -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python scripts\download_data.py D1 D2 D3 D4 D5 D6
venv\Scripts\python scripts\prep_layers.py
venv\Scripts\python scripts\pipeline_stats.py
venv\Scripts\python scripts\audit_numbers.py      # PowerShell/cmd'den
venv\Scripts\python scripts\make_slides.py
venv\Scripts\python scripts\make_video.py
```

Hangi dosyanın ne yaptığı: [docs/KOD_REHBERI.md](docs/KOD_REHBERI.md).

## Belgeler

| Belge | İçerik |
| --- | --- |
| [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) | Ham veriden haritaya her adım: atılanlar, temizleme, normalizasyon, model, doğrulama |
| [docs/TEKNIK_ANLATIM.md](docs/TEKNIK_ANLATIM.md) | Projenin baştan sona öğretici anlatımı: kod parçaları, örnek hesaplar, ölçüler, sözlük |
| [docs/VERI_ORNEKLERI.html](docs/VERI_ORNEKLERI.html) | Her veri setinin ham hali: tüm alanlar ve ilk 5 satır (kullanılan yeşil), ham/işlenmiş görüntü, histogramlar (tarayıcıda aç) |
| [docs/KOD_REHBERI.md](docs/KOD_REHBERI.md) | Dosyalar, veri akışı, çalıştırma |
| [docs/SAYI_DENETIMI.md](docs/SAYI_DENETIMI.md) | Sunumdaki sayıların kaynakları (betikle üretilir) |
| [docs/JURI_SORULARI.md](docs/JURI_SORULARI.md) | Olası jüri soruları ve cevapları |
| [docs/SLAYTLAR.md](docs/SLAYTLAR.md) | 7 slayt, konuşma metinleri |
| [docs/TESLIM.md](docs/TESLIM.md) | Form cevapları, NASA verileri, kaynaklar, YZ beyanı, Drive listesi |
| [docs/veri_envanteri.md](docs/veri_envanteri.md) | Veri kaynakları, tarihler, çözünürlükler |
| `docs/sunum/` | `MarsTrail.pptx` (hareketli, demo gömülü), `MarsTrail_sunum.mp4` (2:24, sessiz), `demo.mp4` (30 sn) |

Veri: NASA/JPL-Caltech, USGS, ASU (THEMIS), University of Arizona (HiRISE). Uygulamada ve sunumda NASA logosu, bayrağı ya da görev arması kullanılmaz; kaynaklar metin olarak belirtilir.

## Yapay zekâ kullanımı

- Kod ve veri işleme betikleri, ekibin denetiminde **Claude Code** (Anthropic) ile yazıldı.
- YOLO etiketlerinin ön taslağı Roboflow Auto Label'dan geldi. 250 karonun hepsi elle kontrol edilip düzeltildi.
- Fikir, hikâye, veri seçimi, formül ve eşik kararları, etiket tanımları, arayüz tasarımı ve doğrulama ekibe ait.
- Sayılar elle yazılmadı; betiklerle ölçüldü.
- Ayrıntılı beyan: [docs/TESLIM.md](docs/TESLIM.md#4-yapay-zekâ-kullanım-beyanı).

## Ekip

- Elif: veri, YOLO modeli, algoritmalar
- Gözde: arayüz
