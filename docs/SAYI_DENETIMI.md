# Sayı denetimi

Bu dosya `scripts/audit_numbers.py` ile üretilir; elle düzenlenmez. Sunumdaki (PPTX, video), teslim formundaki
ve jüri cevaplarındaki her sayı kaynağından yeniden hesaplanır.

- **Betik ölçümü:** `docs/figures/*.json` (veri hattı, model ve doğrulama betiklerinin çıktısı).
- **Uygulama testi:** `web/tests/e8, e11, e13`. Betik bunları headless Edge'de çalıştırır; demo planı, O₂ bölgeleri ve arama alanı sayıları uygulamanın kendi hesabıdır.
- **Dış kaynak:** Tarihî olaylar URL ile listelenir.

**Sonuç:** 46 sayı denetlendi; eşleşen 46, uyuşmayan yok. Eski sayı taraması: temiz.

## Betik ve test ile ölçülen sayılar

| Gösterilen | Ne | Ölçülen | Durum | Kaynak | Geçtiği dosyalar |
| --- | --- | --- | --- | --- | --- |
| 0,50 | AUC, HiRISE kapsamı, YOLO'suz (slayt 6) | 0,50 | ✔ | e10_validation.json · hirise_kapsami.once_yolo_yok.auc_route_lower | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 0,65 | AUC, HiRISE kapsamı, YOLO'lu (slayt 6) | 0,65 | ✔ | e10_validation.json · hirise_kapsami.sonra_yolo.auc_route_lower | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 0,498 | AUC YOLO'suz, 3 hane (TESLIM, jüri) | 0,498 | ✔ | e10_validation.json | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| 0,649 | AUC YOLO'lu, 3 hane | 0,649 | ✔ | e10_validation.json | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| +0,12…+0,18 | AUC farkı, bootstrap %95 aralığı | +0,12…+0,18 | ✔ | e10_validation.json · bootstrap_95.fark | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| %0 | kumlu (kum_ml ≥ 0,5) rota hücresi | %0 | ✔ | e10_validation.json · yolo_dogrudan.kum_ml.pct_route_ge_0_5 | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md, README.md |
| %49 | kumlu rota dışı hücre (yuvarlak) | %49 | ✔ | e10_validation.json · yolo_dogrudan.kum_ml.pct_other_ge_0_5 | SLAYTLAR.md, make_slides.py, TESLIM.md, JURI_SORULARI.md, README.md |
| %49,3 | kumlu rota dışı hücre | %49,3 | ✔ | e10_validation.json | SLAYTLAR.md, JURI_SORULARI.md |
| 0,51 | kaya AUC | 0,51 | ✔ | e10_validation.json · yolo_dogrudan.kaya_ml.auc_route_lower | SLAYTLAR.md, make_slides.py, TESLIM.md, JURI_SORULARI.md |
| %100 | rotanın geçilebilir oranı | %100 | ✔ | e10_validation.json · route_passable_pct | make_slides.py, TESLIM.md |
| 52 | HiRISE kapsamındaki rota hücresi | 52 | ✔ | e10_validation.json · route_cells_in_hirise | SLAYTLAR.md, make_slides.py, TESLIM.md, JURI_SORULARI.md |
| 397 | toplam rota hücresi | 397 | ✔ | e10_validation.json · route_cells_total | SLAYTLAR.md, make_slides.py, TESLIM.md, JURI_SORULARI.md |
| 0,562 → 0,571 | AUC tüm alan | 0,562 → 0,571 | ✔ | e10_validation.json · tum_alan | SLAYTLAR.md, JURI_SORULARI.md |
| 0,31 | mAP50 v1, ortak val | 0,31 | ✔ | e6v2_compare.json · decision.mAP50[0] | TESLIM.md, JURI_SORULARI.md |
| 0,33 | mAP50 v2, ortak val | 0,33 | ✔ | e6v2_compare.json · decision.mAP50[1] | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| 0,69 | hücre dengeli doğruluk v1 | 0,69 | ✔ | e6v2_compare.json · decision.cell_balanced_accuracy[0] | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md |
| 0,78 | hücre dengeli doğruluk v2 | 0,78 | ✔ | e6v2_compare.json · decision.cell_balanced_accuracy[1] | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 250 | etiketli karo | 250 | ✔ | e6v2_split.json · tiles | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 51 | ortak val karosu | 51 | ✔ | e6v2_split.json · split_tiles valid_* | SLAYTLAR.md, make_slides.py, TESLIM.md, JURI_SORULARI.md |
| 8 | v1 val'inde train'e bitişik karo | 8 | ✔ | e6v2_split.json · v1_valid_adjacent_to_v1_train | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 0,36'dan 0,56'ya | kayalık hücre recall v1 → v2 | 0,36'dan 0,56'ya | ✔ | e6v2_compare.json · <run>.tum.cell.per_class.kayalik.R | JURI_SORULARI.md |
| 2,5 kat | etiketsiz engel / karo: 1. parti ÷ 2. parti | 2,5 kat | ✔ | ml/audit_missed_labels.csv + ml/split_merged.csv | SLAYTLAR.md, JURI_SORULARI.md |
| 1146 | çıkarım yapılan karo | 1146 | ✔ | e10_infer_stats.json · tiles_inferred | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| 17 sn | çıkarım toplam süresi | 17 sn | ✔ | e10_infer_stats.json · seconds.total | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| ~29 km² | HiRISE (YOLO) kapsamı = karo × 160 m × 160 m | ~29 km² | ✔ | e10_infer_stats.json · tiles_inferred × 0,0256 km² | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| 2590 | HiRISE karo ızgarası | 2590 | ✔ | e5_stats.json · screen.tiles_total | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md |
| 1444 | NoData yüzünden atılan karo | 1444 | ✔ | e5_stats.json · screen.dropped_nodata | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md |
| 58 karo | dokusuz (etiketlemeye girmeyen) karo | 58 karo | ✔ | e5_stats.json · screen.dropped_flat | SLAYTLAR.md, JURI_SORULARI.md |
| 23 alanın yalnızca 4'ü | D1 konum dosyasında kullanılan alan | 23 alanın yalnızca 4'ü | ✔ | pipeline_stats.json · D1.fields_total, D1.fields_used | JURI_SORULARI.md |
| ~6 GB | ham veri toplamı (D1–D8 dosya boyutları) | ~6 GB | ✔ | pipeline_stats.json · D*.file_mb/zip_mb toplamı = 5,91 GB | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 1,3 MB | grid.json boyutu | 1,3 MB | ✔ | web/data/grid.json dosya boyutu | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 70 m | grid hücresi | 70 m | ✔ | pipeline_stats.json · grid.cell_m | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 1304 → 118 | jeoloji poligonu (kaynak → alan içi) | 1304 → 118 | ✔ | pipeline_stats.json · D6.polygons, D6.polygons_in_area | make_slides.py |
| 2 kaynak hatası | jeoloji haritasında düzeltilen | 2 kaynak hatası | ✔ | pipeline_stats.json · D6.typo_fixed + unit_code_mismatch | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| %2–98 | termal normalizasyon dilimleri | %2–98 | ✔ | pipeline_stats.json · D4.p2, D4.p98 | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md |
| 150 | geçilmez hücre | 150 | ✔ | pipeline_stats.json · grid.blocked | SLAYTLAR.md, make_slides.py, make_video.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 130 → 47 km² | yeşil bölge, nabız 85 → 150 (Ayşe, O₂ 480) | 130 → 47 km² | ✔ | web/tests/e8.html (headless Edge) | make_slides.py, TESLIM.md, JURI_SORULARI.md, README.md |
| 279 dk | üs → Cheyava Falls tek yön | 279 dk | ✔ | web/tests/e8.html (headless Edge) | SLAYTLAR.md, TESLIM.md, JURI_SORULARI.md |
| 73 dk | üs → Three Forks tek yön (yük 0) | 73 dk | ✔ | web/tests/e8.html (headless Edge) | SLAYTLAR.md, JURI_SORULARI.md |
| 5,52 km | demo planı mesafe | 5,52 km | ✔ | web/tests/e11.html (headless Edge) | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 243 dk | demo planı toplam süre | 243 dk | ✔ | web/tests/e11.html (headless Edge) | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 249 dk | demo planı dönüşte kalan O₂ | 249 dk | ✔ | web/tests/e11.html (headless Edge) | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| T+67 | O₂ 220 + nabız 150: dönüş noktası | T+67 | ✔ | web/tests/e11.html (headless Edge) | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 11,6 dk | İHA, olasılığın %50'si | 11,6 dk | ✔ | web/tests/e13.html (headless Edge) | SLAYTLAR.md, make_slides.py, JURI_SORULARI.md |
| 1,07 km² | arama alanı (20 dk sonra) | 1,07 km² | ✔ | web/tests/e13.html (headless Edge) | JURI_SORULARI.md |
| 116 / 480 | Ali'nin O₂ ihtiyacı / kapasitesi | 116 / 480 | ✔ | web/tests/e13.html (headless Edge) | JURI_SORULARI.md |

## Dış kaynaklı sayılar (tarihî olaylar)

| Gösterilen | Ne | Kaynak | Not |
| --- | --- | --- | --- |
| 1971 · ~21 m | Apollo 14: Cone Krateri kenarına kalan mesafe | https://www.astronomy.com/space-exploration/50-years-since-apollo-14-mission-to-fra-mauro/ | kaynak metni (PLAN.md bölüm 2) |
| ~30 cm · 2,5 m | Opportunity'yi tutan kum dalgası: yükseklik ve genişlik | https://science.nasa.gov/photojournal/looking-back-at-purgatory-dune (PIA07999) | 15 Kas 2026'da sayfadan doğrulandı: "about one-third meter (one foot) tall and 2.5 meters (8 feet) wide". Eski metindeki 10–15 cm düzeltildi. |
| 5 haftadan fazla | Opportunity'nin mahsur kalma süresi (26 Nis – Haz 2005) | PIA07999 aynı sayfa | "Getting the rover out of the dunes took more than five weeks" |
| 2009 | Spirit'in yumuşak kuma gömülmesi | https://www.space.com/18766-spirit-rover.html | kaynak metni |
| 3–22 dk | Dünya–Mars tek yön ışık süresi | Mars uzaklığı 0,37–2,68 AU / ışık hızı | fizik; uygulamadaki marstime.js aynı aralığı veriyor |
| nabız 150 | Apollo 14'te Shepard'ın nabzı | https://ntrs.nasa.gov/api/citations/19710012245/downloads/19710012245.pdf | kaynak metni |

## Eski sayı taraması

Güncellenen değerler (v1 modeli, eski Opportunity yüksekliği, E10 öncesi süre) sunum dosyalarında yalnızca "v1 / ilk taslak / eski" bağlamında kalabilir.

Taranan dosyalar: docs/SLAYTLAR.md, scripts/make_slides.py, scripts/make_video.py, docs/TESLIM.md, docs/JURI_SORULARI.md, README.md. Etiketsiz eski sayı yok.

Sayıların güncelliği: model ya da veri değişirse önce ilgili betik (`ml/infer.py`, `scripts/prep_layers.py`, `scripts/validate.py`, `ml/eval_merged.py`), sonra bu denetim yeniden çalıştırılır. ✘ çıkan sayı sunumda ve belgelerde düzeltilir.
