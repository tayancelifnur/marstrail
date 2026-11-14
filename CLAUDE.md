# MarsTrail – NASA Space Apps Konya 2026

Mars'ta astronotun yürüyüşünü hazırlıktan acil duruma kadar yöneten web uygulaması.
Ayrıntılar: docs/PLAN.md (proje) ve docs/GOREV_KARTLARI.md (adım adım görevler).
Kullanıcı "E5 kartını yap" ya da "G3 kartını yap" dediğinde önce docs/GOREV_KARTLARI.md
içindeki o kartı oku, sonra "Yap" adımlarını uygula ve "Kontrol" satırını doğrula.

## Ekip
- Elif: veri, YOLO modeli, algoritmalar (scripts/, ml/, web/*.js algoritma dosyaları)
- Gözde: arayüz (web/index.html, web/app.js, web/style.css)
- Başkasının klasörüne dokunma; ortak nokta sadece web/data/ dosyaları.

## Kararlar
- Sadece astronot (rover modu yok). 2 astronot: Ayşe ve Ali.
- O₂ bölgeleri (yeşil/sarı/kırmızı) her zaman haritada açık, araziye göre şekil alır.
- Her noktanın tarihçesi var (keşif tarihi, hangi görev ne zaman inceledi, Perseverance Sol'ü, fotoğraf).
- Odak bölge: Jezero Krateri. Backend yok, her şey tarayıcıda.

## Veri sözleşmesi (web/data/)
regions.json, poi.geojson, stories.json, layers.json + layers/*.png,
grid.json (256x256: elev, cost, blocked, bounds), astronauts.json, conditions.json.
Koordinatlar derece, doğu pozitif, boylam -180..180. Dosya adları değişmez.

## Teknik
- Python: rasterio, numpy, geopandas, shapely, pillow, requests, ultralytics (YOLOv8)
- Web: CesiumJS (CDN), Chart.js, saf JS. Mars saati: Mars24 algoritması.
- Formüller docs/PLAN.md bölüm 5'te. Sayılar varsayımdır, kod yorumunda belirt.
- İndirilecek veri dosyaları ve linkleri docs/GOREV_KARTLARI.md bölüm 2'de (D1–D8).

## Kurallar
- Paz 08:30'dan sonra yeni özellik yok.
- 30 dakikadan uzun takılırsan dur, kartın "Takılırsan" satırını uygula.
- Büyük dosyaları (data/raw, data/processed, ml/dataset, *.tif, *.zip, *.pt) git'e ekleme; .gitignore'a yaz.
- Her kart bitince commit + push.
- Uygulamada ve slaytlarda NASA logosu, bayrağı veya görev arması kullanılmaz (Space Apps kuralı).
  Veriler için kaynak gösterilir ("Veri: NASA/JPL-Caltech, USGS" gibi metin olarak).

## Sunum ve teslim (organizatör cevapları)
- Sunum: 7 slayt, 5 dk + 2 dk soru-cevap; en fazla 30 sn video. Akış docs/PLAN.md bölüm 7'de.
- Jüri veri hakimiyetini ölçüyor: temizleme, gereksiz verinin atılması, normalizasyon, öğrenme yöntemleri.
- Teslim formu taslakları, kaynak listeleri, YZ beyanı ve Drive kontrol listesi: docs/TESLIM.md.

## Veri hattı kuralı
- Her veri adımında docs/DATA_PIPELINE.md'ye yaz: veri seti, neden bu veri / ürüne katkısı,
  ham içerik, atılanlar (sayı ve neden), temizleme, normalizasyon (formül), çıktı.
- Sayıları elle yazma; scripts/pipeline_stats.py (ya da adımın kendi scripti) ölçsün.
- Gerekirse önce/sonra PNG'yi docs/figures/'a kaydet. Sondaki özet tabloyu güncel tut.

## Takip ve açıklama kuralları
- Her kartın sonunda docs/LOG.md'ye şunu ekle: kart adı, saat, ne yapıldı,
  hangi dosyalar değişti, nasıl çalıştırılır, varsayımlar/formüller (3-8 satır).
- Uzun süren işleri (model eğitimi, büyük indirme) kendin çalıştırma;
  komutu yaz, Elif terminalde çalıştırsın.
- Bir formül veya eşik değeri seçtiğinde nedenini kodda yorum satırıyla yaz.
- Kartı bitirince bana 3 cümlelik özet ver ve commit mesajı öner.