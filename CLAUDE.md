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
