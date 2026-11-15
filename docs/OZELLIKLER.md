# MarsTrail · özellik envanteri

`web/` kodundan (index.html, app.js, walkback.js, eva.js, rescue.js, marstime.js) çıkarıldı. Burada yalnızca uygulamada **gerçekten çalışan** özellikler var; olmayanlar en altta ayrı listede.

- ★ işareti, karşılaştırdığımız araçlarda (SEXTANT, xGDS/Minerva, SPOC, NOAH-H, NASA Mars Trek; bkz. KONUSMA_METNI.md bölüm 9) bulamadığımız ya da bizim farklı yaptığımız özelliği gösteriyor.
- Testler: `web/tests/e8, e11, e13.html`, 24/24 ✔.

## 1. Harita ve küre

| Özellik | Ne yapıyor | Kod |
| --- | --- | --- |
| Mars küresi | CesiumJS, Mars elipsoidi (3396,19 / 3376,2 km); gerçek Mars Güneşi'yle gece-gündüz; otomatik dönüş | app.js |
| Taban harita | NASA Mars Trek: Viking renkli ya da MOLA gölgeli kabartma; Jezero'da CTX 6 m ve HiRISE 25 cm ayrıntı katmanları | app.js `BASE_LAYERS`, `DETAIL_LAYERS` |
| 3B arazi | Bizim grid'imizin (CTX DEM) yükseklikleriyle Jezero kabartması | app.js |
| Veri katmanları | Arazi gölgesi, eğim, termal eylemsizlik, jeoloji, birleşik geçilebilirlik, **YOLO kum/kaya** (★ kendi modelimiz) | `web/data/layers.json` |
| Jezero'ya git / Küreye dön | Kamera uçuşu | app.js |

## 2. Üst bar (her ekranda)

- Jezero yerel saati (LMST).
- Sol: senaryo Sol'ü; üstüne gelince Perseverance'ın gerçek Sol'ü görünüyor.
- UTC ve Türkiye saati.
- Dünya–Mars gecikmesi, canlı. Bugün ~10,9 dk; Mars24 ve Kepler hesabı.
- Gün batımına kalan süre.
- Hava ve toz değeri: örnek veri.
- Habitat ağı: bağlı / kopuk.

## 3. Hazırlan: astronot profili

| Özellik | Ne yapıyor |
| --- | --- |
| Profil formu | Ad, kilo, giysi, O₂, batarya, su, nabız, yük, radyasyon. Sınır kontrolü var: O₂ giysi kapasitesini aşamaz; nabız ve yük yükselince uyarı rengi. Tarayıcıda kaydediliyor (localStorage). |
| Astronot ekle / çıkar | Ekibe yeni kişi; 3 ve daha fazla kişide kurtarıcı, O₂'si en yüksek olan |
| Bölge rozeti | Her astronot kartında o anki bölgesi (YEŞİL / SARI / KIRMIZI) |

## 4. O₂ bölgeleri, her zaman açık ★

- Bütün grid için iki Dijkstra çalışıyor: "Oraya git" ve "oradan üsse dön".
  - Yeşil: toplam süre ≤ O₂ / 1,25.
  - Sarı: toplam süre ≤ O₂.
  - Kırmızı: dönülemez.
- Nabız, yük ve kalan O₂ değişince ~30 ms'de yeniden çiziliyor. Örnek: Ayşe'nin nabzı 85'ten 150'ye çıkınca yeşil alan 130'dan 47 km²'ye iniyor.
- Bölge sınırı daire değil, araziye göre şekil alıyor: yönlü eğim, Tobler hızı, zemin skoru.

## 5. Keşfet: noktalar ve tarihçe

| Özellik | Ne yapıyor |
| --- | --- |
| Nokta pinleri | Üs, Rochette, Delta önü, Three Forks, Cheyava Falls, Ingenuity uçuş alanı, Jezero. Konumlar Perseverance'ın ölçülmüş konumundan (D1) |
| Nokta kartı | Açıklama; bilim değeri; Perseverance'ın oraya geldiği Sol; **o gün çektiği gerçek fotoğraf** (Navcam / Mastcam-Z, kaynak bağlantısıyla) |
| Tarihçe ★ | Her noktada zaman çizelgesi: keşif tarihi, hangi görev ne zaman inceledi, kaynak bağlantısı |
| Arazi bilgisi | Yükseklik, 300 m içindeki en büyük eğim, kum oranı, jeoloji birimi, geçilebilirlik skoru, tehlikeler |
| Kum alanı pini | Eolyen kum tehlikesi ve Opportunity/Spirit hikâye kartları |
| Tarihi olaylar | Apollo 14, Opportunity, Spirit kartları (kaynaklarıyla) |

## 6. Planla: rota ve GO/NO-GO

| Özellik | Ne yapıyor |
| --- | --- |
| Rota çiz | Haritaya tıklayarak serbest rota. Kartta mesafe, Tobler süresi (yükle), O₂ ihtiyacı, tırmanış/iniş, bitiş noktasının bölgesi |
| Engeller ve zorluk ★ | Çizgi boyunca kum alanı, geçilmez hücre, en dik eğim, en zor kesim; ortalama zorluk skoru |
| Test edilmemiş rota uyarısı | Rota bilinen güvenli durakların dışındaysa uyarıyor ve güvenli durakları listeliyor |
| Yükseklik profili | Rota boyunca grafik |
| Bu rotada yürü | Çizilen rota plana çevrilip yürünebiliyor; yürüyüş çizgiyi izliyor |
| EVA planlayıcı | Durak ekle, sırala, sil; kalış süresi; çıkış zamanı (sonraki güvenli pencere: yerel 09:00) |
| Güvenli rota | Duraklar arasında Dijkstra; yönlü eğim (yokuş yukarı/aşağı farklı), yük, toplanan numune, yorgunluk (%5/saat) |
| Zaman çizelgesi | Her adımda LMST saati ve kalan O₂ |
| Dönüş noktası ★ | "Bunu geçersen O₂ dönüşe yetmez" noktası ve %25 pay noktası, haritada işaretli |
| GO/NO-GO ★ | 7 kontrol: O₂ (%25 pay), gün batımından önce dönüş, kum tuzağı, eğim, telsiz görüş hattı, batarya, su |
| Radyasyon | Bu EVA'nın ek dozu ve toplam |
| Telsiz gölgesi | Habitat anteniyle görüş hattının kesildiği yerler (Mars eğriliği dahil) |

## 7. Yürü: canlı yürüyüş

| Özellik | Ne yapıyor |
| --- | --- |
| Canlı panel | Geçen süre, LMST, aşama (yürüyor / durakta), O₂ (sayı + çubuk + çarpan), üsse dönüş süresi |
| Nabız kaydırıcısı ★ | Yürürken nabız değişince O₂ tüketimi ve bölgeler anında değişiyor |
| Not pini | Konuma yazılı not bırakma ("📍 Pin"), olay listesine düşüyor |
| Uyarılar ★ | Yürüyüş başladı; test edilmemiş rota; kum alanına yaklaşma / kum alanında; dönüş noktasına yaklaşma / DÖNÜŞ NOKTASI; sarı / kırmızı bölgeye giriş; yeniden yeşil; O₂ %25 altı; telsiz gölgesi |
| Hız, duraklat, bitir | ×60 / ×300 / ×900 simülasyon hızı |
| Üsse dön | O anki konumdan güvenli dönüş rotası ve varışta kalacak O₂ |

## 8. Hayatta kal: telsiz koptu ★

| Özellik | Ne yapıyor |
| --- | --- |
| Arama alanı | Son konum, geçen süre ve kalan O₂ (nabızla) → yürünebilecek hücreler. Olasılık ısı haritası; en olası %50 ve %90 alanları. Planlanan rotaya yakın yerler ×2 |
| İHA zikzak rotası | Alanın uzun ekseni boyunca biçerdöver taraması. Şerit genişliği kameradan (100 m, 60°). Kapsama eğrisi, %50 ve %90 süreleri, batarya sayısı. Demo: %50 → 11,6 dk |
| İHA bulunca bekler | Kayıp astronotu görünce taramayı bırakıp üstünde bekliyor; olay özetinde "İHA gördü" |
| Kurtarma rotası | Kurtarıcının (ekipte O₂'si en yüksek kişi) rotası ve kendi O₂ kontrolü: YEŞİL / SARI / KIRMIZI. Demo: Ali 116 / 480 dk |
| Kurtarılabilir mi? | Buluşma = max(İHA'nın bulma süresi, kurtarıcının varışı); buluşmada ve üste varışta kalan O₂; gerekirse 60 dk yedek tüp. Geç fark edilirse "yetişilemez" diyebiliyor |
| Yürüyüş yoksa demo | Plandaki astronot çıkıştan 60 dk sonra, nabız 150'de kayboluyor |

## 9. Diğer

- Telefonda çalışıyor: mobil çekmece paneli; dikey ekranda kamera ayarı.
- Sunucu yok. Bütün hesaplar tarayıcıda.
- Taban harita görüntüleri internetten geliyor (Mars Trek); Cesium, GitHub Pages yayınında yerel kopyadan.
- "Demo'yu sıfırla": profiller, eklenen astronotlar, plan ve yürüyüş varsayılana dönüyor.

## Uygulamada OLMAYANLAR (sunumda "var" denmeyecek)

| İstenen | Durum |
| --- | --- |
| Çizilen rotayı kalıcı kaydetme, rota kütüphanesi | Yok. Rota yalnızca açık oturumda; sayfa yenilenince gidiyor |
| Fotoğraf / ses notu yükleme | Yok. Pin yalnızca yazılı not ("Not / fotoğraf…" yalnızca yer tutucu metin) |
| Rotanın incelenip onaylanması | Yok. Yol haritasında: "onaylanan rotalar ve notlar kütüphanesi" |
| Gerçek sensör verisi (IMU, nabız bandı, GPS) | Yok. Konum ve nabız simüle |
| İnternetsiz harita | Yok. Hesaplar cihazda ama taban harita görüntüleri internetten |
| Gerçek hava durumu | Yok. Üst bardaki hava ve toz değeri örnek |
