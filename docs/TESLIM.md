# MarsTrail – Teslim

Teslim formu için taslak cevaplar, kaynak listeleri, YZ beyanı ve Drive kontrol listesi. `[...]` ile işaretli yerler son gün doldurulacak (YOLO sonuçları, linkler).

## 1. Form cevapları (taslak)

### Proje ne yapıyor?

MarsTrail, Mars'ta yüzeyde yürüyen bir astronotun yürüyüşünü hazırlıktan acil duruma kadar yöneten, tarayıcıda çalışan bir görev aracı. Dört aşamada iş görüyor:

- **Hazırlık:** Astronot profili ve sarf malzemeleri.
- **Planlama:** Araziyi ve kumu bilen rota, zaman çizelgesi, dönüş noktası.
- **Yürüyüş:** Canlı O₂ takibi.
- **Acil durum:** Telsiz koparsa arama alanı ve İHA tarama rotası.

Haritada her zaman açık duran yeşil/sarı/kırmızı O₂ bölgeleri, astronotun nereye gidip güvenle dönebileceğini gösteriyor. Bölgeler daire değil; eğime, kuma ve zemine göre şekil alıyor. Nabız ya da yük değiştikçe canlı olarak daralıyor.

### Faydaları

- Apollo'daki "walkback" kuralını sabit hız varsayımından çıkarıp araziye ve astronotun anlık durumuna bağlı hale getiriyor.
- Dünya 3–22 dakika uzaktayken "geri dön" kararını yerinde, veriye dayanarak veriyor.
- Onlarca göreve dağılmış yörünge ve yüzey verisini (CTX, HiRISE, THEMIS, USGS jeoloji, Perseverance konumları ve fotoğrafları) tek ekranda birleştiriyor.
- Kum tuzaklarını önceden işaretliyor: termal eylemsizlik, eolyen birim ve kendi YOLO modelimiz. Opportunity ve Spirit'in başına gelen buydu.
- Her noktanın tarihçesi ve Perseverance'ın o noktadaki gerçek fotoğrafı, astronota "oraya varınca ne göreceğini" gösteriyor.

### Etkisi

- **Artemis ve gelecekteki Mars görevleri:** EVA planlama ve kask içi ekran için hafif, açık veriyle çalışan bir prototip.
- **Dünya:** Aynı mantık bir afet bölgesinde kayıp kişi araması için kullanılabilir. Son konum ve kalan süreden ulaşılabilir alan, arazi maliyetine göre olasılık, İHA tarama rotası.
- **Erişim:** Backend gerektirmiyor, telefonda açılıyor. Veri cihazda olduğu için bağlantı kopsa da çalışmaya devam ediyor.

### Kullanılan araçlar

- **Veri işleme:** Python, rasterio/GDAL, geopandas, shapely, pyproj, numpy, Pillow, matplotlib.
- **Öğrenme:** Ultralytics YOLOv8 ve PyTorch (CUDA, RTX 5090); etiketleme Roboflow'da.
- **Web:** CesiumJS (3D Mars küresi), Chart.js, saf JavaScript. Mars Trek WMTS karoları.
- **Algoritmalar:**
  - Tobler yürüme hızı (Mars ve giysi düzeltmesiyle)
  - Ağırlıklı geçilebilirlik füzyonu
  - Dijkstra ile O₂ bölgeleri ve dönüş noktası
  - Mars24 (Mars saati)
  - Kepler yörüngeleri (Dünya–Mars gecikmesi)
- **Geliştirme:** Git/GitHub, VS Code, Claude Code (YZ beyanına bakın).

### Yaratıcılık

- Gerçek kazalardan geriye doğru tasarlandı. Her katman bir olaya karşılık geliyor:
  - Apollo 14'te nabız ve dönüş sınırı
  - Opportunity'de kum dalgası (YOLO)
  - Spirit'te gevşek zemin (termal eylemsizlik)
- O₂ bölgeleri sabit bir yarıçap değil; arazi maliyetine göre şekillenen ve astronotun nabzıyla nefes alan bir harita.
- Kendi tehlike modelimiz, rover'ın gerçek yoluyla doğrulanıyor: Perseverance'ın geçtiği yer bizim haritamızda geçilebilir mi?
- Her pin bir zaman çizgisi: 2005'teki yörünge keşfinden Perseverance'ın o noktadaki Sol'üne ve fotoğrafına kadar.

### Dikkate alınan faktörler

- **Arazi:**
  - Eğim (20 m DEM, 25° üstü geçilmez)
  - Zemin gevşekliği (termal eylemsizlik)
  - Kum (eolyen birim, YOLO kum dalgası)
  - Kaya (jeoloji, YOLO)
- **Astronot:** Kalan O₂, nabız (O₂ tüketim çarpanı), taşınan yük (yürüme hızı), batarya, su, radyasyon dozu.
- **Görev kuralları:** %25 dönüş payı (yeşil bölge), "asla yalnız yürüme" kuralı için iki astronot, gün batımından önce dönüş, Go/No-Go listesi.
- **İletişim:** Dünya–Mars gecikmesi, habitat ağı bağlantısı.
- **Veri kalitesi:**
  - 3 farklı projeksiyon tek sisteme getirildi.
  - NoData temizliği, %2–98 normalizasyon.
  - Kaynak haritadaki 2 hata düzeltildi.
  - Ayrıntı: [DATA_PIPELINE.md](DATA_PIPELINE.md).
- **Sınırlar:** Formüllerdeki katsayılar varsayım; gerçek EVA verisiyle kalibre edilmedi. Demoda konum simüle ediliyor.

## 2. NASA verileri ve kaynakları

**Ham veri dosyaları (D1–D8):**

| # | Veri | URL |
| --- | --- | --- |
| D1 | Perseverance konumları (Mars 2020 MMGIS) | https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json |
| D2 | Perseverance sürüş izi | https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_traverse.json |
| D3 | Ingenuity uçuş yolları | https://mars.nasa.gov/mmgis-maps/M20/Layers/json/m20_heli_flight_path.json |
| D4 | THEMIS termal eylemsizlik, Jezero (Mars Odyssey THEMIS verisinden türetilmiş mozaik, Zenodo'da) | https://zenodo.org/record/4931348 |
| D5 | CTX DEM 20 m, Mars 2020 (USGS Astrogeology / JPL) | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif · sayfa: https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic |
| D6 | USGS SIM 3464, Jezero ve Nili Planum jeolojik haritası (USGS–NASA Planetary Geologic Mapping) | https://pubs.usgs.gov/publication/sim3464 · veri: https://pubs.usgs.gov/sim/3464/sim3464_database.zip |
| D7 | Perseverance ham görüntüleri | https://mars.nasa.gov/mars2020/multimedia/raw-images/ · API: https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&sol={sol} |
| D8 | HiRISE ortogörüntü + DTM mozaiği (MSR TRN, USGS) | https://astrogeology.usgs.gov/search/map/mars-sample-return-terrain-relative-navigation-hirise-dtm-mosaic · zip: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024/MSR_TRN_HiRISE_soc_003_USGS_release_aug2024_mosaics.zip |

**Uygulamada kullanılan Mars Trek WMTS karoları:**

| Katman | URL |
| --- | --- |
| Viking renkli mozaik | https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg |
| MOLA renkli gölgeli kabartma | https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg |
| CTX Jezero 6 m | https://trek.nasa.gov/tiles/Mars/EQ/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/1.0.0/default/default028mm/{z}/{y}/{x}.png |
| HiRISE Jezero 25 cm | https://trek.nasa.gov/tiles/Mars/EQ/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd/1.0.0/default/default028mm/{z}/{y}/{x}.png |
| Katalog | https://trek.nasa.gov/mars/ · https://api.nasa.gov/mars-wmts/catalog |

**Diğer NASA kaynakları:**

| Kaynak | URL |
| --- | --- |
| Mars24 algoritması (NASA GISS) | https://www.giss.nasa.gov/tools/mars24/ |
| Perseverance konum haritası | https://science.nasa.gov/mission/mars-2020-perseverance/location-map/ |
| Opportunity, Purgatory Kumulu | https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune |
| Apollo 14 görev raporu | https://ntrs.nasa.gov/api/citations/19710012245/downloads/19710012245.pdf |
| Apollo 15 EVA kısıtları | https://www.nasa.gov/wp-content/uploads/static/history/alsj/19790073512_1979073512.pdf |
| NASA Worldview (kapanış sahnesi, kesilmezse) | https://worldview.earthdata.nasa.gov/ |

## 3. Diğer kaynaklar

**Yazılım ve kütüphaneler:**

| Kaynak | Kullanım | URL |
| --- | --- | --- |
| CesiumJS 1.123.0 | 3D küre | https://cesium.com/platform/cesiumjs/ · CDN: https://cdn.jsdelivr.net/npm/cesium@1.123.0/ |
| Chart.js | Yükseklik profili, grafikler | https://www.chartjs.org/ |
| Ultralytics YOLOv8 | Kaya ve kum dalgası tespiti | https://github.com/ultralytics/ultralytics |
| PyTorch | Model eğitimi | https://pytorch.org/ |
| Roboflow | Etiketleme | https://roboflow.com/ |
| rasterio, GDAL, geopandas, shapely, pyproj, numpy, Pillow, matplotlib, requests | Veri işleme | https://rasterio.readthedocs.io/ · https://gdal.org/ · https://geopandas.org/ |
| Zenodo | D4'ün barındırıldığı açık veri deposu | https://zenodo.org/ |

**Literatür:**

| Kaynak | URL |
| --- | --- |
| Tobler (1993) yürüme fonksiyonu | Yöntem, PLAN.md §5 |
| SEXTANT (MIT) | https://dspace.mit.edu/handle/1721.1/59560 |
| SEXTANT saha testi | https://core.ac.uk/download/17204791.pdf |
| Minerva / BASALT | https://pmc.ncbi.nlm.nih.gov/articles/PMC6442304 |
| SPOC ve termal eylemsizlik (JPL) | https://arxiv.org/pdf/1805.05451 |
| NOAH-H Jezero | https://oro.open.ac.uk/84535 |
| Walkback limiti | https://ttu-ir.tdl.org/handle/2346/74208 |
| NASA SUITS retrospektifi | https://spencer-l.github.io/assets/pdf/NASA_SUITS_Retrospective.pdf |

**Hikâye ve tarihçe:**

| Kaynak | URL |
| --- | --- |
| Astronomy: Apollo 14 | https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/ |
| Astronomy: Jezero gölünün keşfi | https://www.astronomy.com/?p=40600 |
| Space.com: Spirit | https://www.space.com/18766-spirit-rover.html |
| EarthSky: Jezero deltası | https://earthsky.org/space/ancient-martian-lake-delta-floods-perseverance/ |
| Sky at Night: Cheyava Falls | https://skyatnightmagazine.com/space-missions/perseverance-jezero-crater |
| Space Odyssey Hub: Three Forks | https://spaceodysseyhub.com/replays/perseverance |
| Stack vd. 2020 (MIT DSpace) | https://dspace.mit.edu/entities/publication/592b30f4-e0c9-4caa-8f9c-2bd12ebdffe9 |
| USGS jeoloji haritası duyurusu | https://www.usgs.gov/maps/geologic-map-jezero-crater-and-nili-planum-region-mars |

## 4. Yapay zekâ kullanım beyanı

Bu projede **Claude Code** (Anthropic, Claude Opus 5.5) kodlama asistanı olarak, ekibin denetiminde kullanıldı.

- **YZ'nin yaptığı:** Veri indirme ve işleme scriptlerinin yazılması: `scripts/download_data.py`, `make_dummies.py`, `prep_layers.py`, `pipeline_stats.py`, `build_regions.py`, `tile_for_yolo.py`, `ml/train.py`, `ml/dataset_stats.py`. Algoritma dosyalarının taslakları. Belgelerin (DATA_PIPELINE, envanter, bu dosya) ilk taslakları.
- **İnsanların yaptığı:**
  - Proje fikri, hikâye ve senaryo.
  - Veri seçimi; formül, eşik ve katsayı kararları.
  - YOLO etiketleri. Ön etiketleme Roboflow Auto Label (GPT-6.1 Terra) ile yapıldı. 150 karonun hepsi Elif tarafından tek tek kontrol edildi; yanlış, eksik ve fazla kutular elle düzeltildi. Sınıf tanımları ve neyin etiketlenmeyeceği insan kararı (`ml/ETIKETLEME.md`).
  - Arayüz tasarımı.
  - Her çıktının kontrolü: haritaların gözle doğrulanması, sayıların scriptten üretilmesi.
  - Sunum.
- **Arayüz tarafında YZ kullanımı:** Arayüz kodu (`web/index.html`, `web/app.js`, `web/style.css`) Claude Code ile yazıldı. Gözde görev kartlarını verdi, sonuçları tarayıcıda denedi, sorunları bildirdi (ör. Jezero'nun bulanık görünmesi, küreye geri dönülememesi) ve hangi iyileştirmelerin yapılacağına karar verdi (3B arazi, ışık ve atmosfer). Her kart, Claude Code'un headless tarayıcıda aldığı ekran görüntüleriyle de kontrol edildi. [Gözde: kendi yaptığın tasarım kararlarını buraya ekle/düzelt]
- **Doğrulama:** YZ'nin ürettiği her veri adımının sayıları elle yazılmadı, scriptle ölçüldü ([figures/pipeline_stats.json](figures/pipeline_stats.json)). Önce/sonra görselleri insan tarafından kontrol edildi. Formüllerdeki katsayılar varsayım olarak açıkça işaretli.
- **Model eğitimi:** YOLO modeli kendi etiketlediğimiz HiRISE karolarıyla, kendi bilgisayarımızda eğitildi. Hazır bir tehlike modeli kullanılmadı.

## 5. Drive klasörü kontrol listesi

- [ ] Klasör paylaşımı: "Bağlantıya sahip herkes görüntüleyebilir". Gizli pencerede açılıp denendi.
- [ ] `MarsTrail_Sunum.pdf` ve düzenlenebilir kaynağı. 7 slayt.
- [ ] `MarsTrail_Demo.mp4`. **En fazla 30 sn**, süresi kontrol edildi. Sesli ya da altyazılı.
- [ ] Uygulama linki (GitHub Pages / Vercel). Telefonda açılıyor.
- [ ] GitHub repo linki. README güncel, YZ notu var.
- [ ] `TESLIM.md` (bu dosya) ya da PDF'i: form cevapları, NASA verileri, diğer kaynaklar, YZ beyanı.
- [ ] `DATA_PIPELINE.md` ve `figures/` görselleri: veri hakimiyeti kanıtı.
- [ ] Ekran görüntüleri: küre, O₂ bölgeleri, nokta kartı, planlayıcı, Hayatta Kal.
- [ ] Logo kontrolü: slaytlarda, videoda ve uygulamada NASA logosu, bayrağı veya görev arması **yok**. Kaynaklar metin olarak var.
- [ ] Ekip adları ve rolleri (Elif: veri, model, algoritmalar · Gözde: arayüz).
- [ ] Formdaki bütün alanlar dolduruldu. 13:30'da teslim edildi (son saat 14:00).
