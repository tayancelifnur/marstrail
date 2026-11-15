// MarsTrail – arayüz (Gözde)
// G1: Mars küresi (CesiumJS + Mars Trek WMTS)

(function () {
  "use strict";

  // Jezero Krateri merkezi (derece, doğu pozitif)
  const JEZERO = { lat: 18.38, lon: 77.58 };

  // Mars elipsoidi (IAU 2000): ekvator yarıçapı 3396,19 km, kutup yarıçapı 3376,20 km
  const MARS_RADII = { equatorial: 3396190.0, polar: 3376200.0 };

  // Mars Trek WMTS katmanları. Seviye 0 = 2x1 karo (coğrafi), en yüksek seviye 7.
  // Cesium ion token'ı gerekmiyor: ion görüntüsü/arazisi kullanılmıyor.
  const TREK = "https://trek.nasa.gov/tiles/Mars/EQ/";
  const BASE_LAYERS = {
    viking: {
      name: "Viking renkli mozaik",
      url: TREK + "Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
      maxLevel: 7,
    },
    mola: {
      name: "MOLA renkli gölgeli kabartma",
      url: TREK + "Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
      maxLevel: 7,
    },
  };

  const ROTATE_RATE = 0.05; // rad/sn, otomatik dönüş hızı

  function showError(msg) {
    const el = document.getElementById("error");
    el.textContent = msg;
    el.hidden = false;
  }

  if (typeof Cesium === "undefined") {
    showError("CesiumJS yüklenemedi. İnternet bağlantısını kontrol edin.");
    return;
  }

  const MARS = new Cesium.Ellipsoid(MARS_RADII.equatorial, MARS_RADII.equatorial, MARS_RADII.polar);
  // Viewer oluşturulmadan önce varsayılan elipsoidi Mars yap
  Cesium.Ellipsoid.default = MARS;

  let viewer;
  try {
    viewer = new Cesium.Viewer("globe", {
      globe: new Cesium.Globe(MARS),
      baseLayer: false,          // Dünya görüntüsü (ion) yüklenmesin
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      skyAtmosphere: new Cesium.SkyAtmosphere(MARS), // aşağıda Mars rengine çevriliyor
    });
  } catch (err) {
    console.error(err);
    showError("3B küre başlatılamadı (WebGL desteği gerekli). " + err.message);
    return;
  }

  const scene = viewer.scene;
  const globe = scene.globe;

  // Çizim hatasında kendini toparla: CDN'den bir worker dosyası bazen yüklenemiyor
  // ("Failed to fetch dynamically imported module ... createGroundPolylineGeometry.js") ve Cesium
  // çizimi tamamen durduruyor. Hata panelini kapatıp 1,5 sn sonra çizimi yeniden başlatıyoruz;
  // 3 denemede düzelmezse (geçici ağ hatası değil demektir) sayfayı yenileme önerisi çıkıyor.
  // 60 sn hatasız geçerse sayaç sıfırlanır (ara sıra tek hata yenileme istemesin).
  let renderFails = 0;
  let renderFailReset = null;
  scene.renderError.addEventListener((_, err) => {
    console.error("Cesium çizim hatası:", err);
    renderFails += 1;
    clearTimeout(renderFailReset);
    setTimeout(() => {
      document.querySelectorAll(".cesium-widget-errorPanel").forEach((n) => n.remove());
      if (renderFails <= 3) {
        viewer.useDefaultRenderLoop = true;
        renderFailReset = setTimeout(() => (renderFails = 0), 60000);
      } else {
        const box = document.getElementById("error");
        box.replaceChildren("Harita çizimi durdu (internetten bir dosya yüklenemedi). ");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "primary";
        btn.textContent = "Sayfayı yenile";
        btn.addEventListener("click", () => location.reload());
        box.append(btn);
        box.hidden = false;
      }
    }, 1500);
  });

  // Netlik: Cesium varsayılanda CSS pikselinde çizer; Windows %125–150 ölçekte yazı ve harita bulanık
  // görünüyordu. Ekranın gerçek pikselinde çiz (çok yüksek DPI'da GPU yorulmasın diye en fazla 2×).
  viewer.useBrowserRecommendedResolution = false;
  if (window.devicePixelRatio > 2) viewer.resolutionScale = 2 / window.devicePixelRatio;

  // Harita etiketleri: kalın siyah kenar yerine koyu yarı saydam zemin (her arazi renginde okunur)
  const LABEL_BG = {
    style: Cesium.LabelStyle.FILL,
    showBackground: true,
    backgroundColor: Cesium.Color.fromCssColorString("#0d0b0a").withAlpha(0.72),
    backgroundPadding: new Cesium.Cartesian2(6, 3),
  };
  // Zoom sınırları: demoda fare tekerleği kazara Mars'ı nokta yapmasın ya da kamerayı araziye gömmesin.
  // En yakın 100 m (HiRISE 25 cm/piksel ayrıntısı bu mesafede okunuyor), en uzak 30.000 km
  // (açılış görünümü 11.000 km; Mars çapı ~6800 km, küre ekranı rahat dolduruyor).
  scene.screenSpaceCameraController.minimumZoomDistance = 100;
  scene.screenSpaceCameraController.maximumZoomDistance = 3.0e7;
  globe.baseColor = Cesium.Color.fromCssColorString("#5a2e1c");
  scene.backgroundColor = Cesium.Color.BLACK;

  // --- Güneş ışığı: gerçek Mars Güneşi (üst bardaki saatle aynı an) ---
  // Güneş altı nokta: enlem = Güneş'in sapması δs, boylam = Jezero boylamı − (LTST − 12) × 15°
  // (yerel gerçek güneş saati 12:00'de Güneş Jezero meridyeninde; Mars saatte 15° döner).
  // δs ve LTST Elif'in marstime.js'inden (Mars24, Allison & McEwen 2000). Güneş sonsuz uzakta:
  // ışık yönü = Güneş altı noktadaki yüzey normalinin tersi. Böylece küredeki gece-gündüz çizgisi
  // üst bardaki LMST ile tutarlı. Yakında (≤ 2500 km) aydınlatma zaten soluyor, arazi tam aydınlık
  // kalıyor; Elif'in hillshade.png katmanının KB ışığıyla çelişmiyor.
  // Yedek (marstime.js yüklenemezse): Jezero'da KB'dan, ufkun 30° üstünden (hillshade ile aynı yön).
  function sunLightDirection(date) {
    if (window.MarsTime) {
      const t = MarsTime.at(date);
      const decl = MarsTime._mars24(date.getTime()).decl; // derece
      const subLon = MarsTime.JEZERO.lonE - (t.ltstHours - 12) * 15;
      const n = MARS.geodeticSurfaceNormalCartographic(Cesium.Cartographic.fromDegrees(subLon, decl));
      return Cesium.Cartesian3.negate(n, n);
    }
    const az = Cesium.Math.toRadians(315), el = Cesium.Math.toRadians(30);
    // Yerel doğu-kuzey-yukarı ekseninde Güneş'e doğru birim vektör
    const toSunLocal = new Cesium.Cartesian3(Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el));
    const enu = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(JEZERO.lon, JEZERO.lat, 0, MARS), MARS);
    const toSun = Cesium.Matrix4.multiplyByPointAsVector(enu, toSunLocal, new Cesium.Cartesian3());
    return Cesium.Cartesian3.normalize(Cesium.Cartesian3.negate(toSun, toSun), toSun); // ışık Güneş'ten sahneye
  }
  scene.light = new Cesium.DirectionalLight({ direction: sunLightDirection(new Date()), intensity: 2.0 });
  // Cesium'un kendi Güneş/Ay diskleri Dünya'nın gökyüzüne göre çiziliyor (Güneş yanlış yönde, Ay Dünya'nın Ay'ı): gizle
  if (scene.sun) scene.sun.show = false;
  if (scene.moon) scene.moon.show = false;
  // Mars Güneşi saatte 15° ≈ Dünya dakikasında 0,24° kayar: 30 sn'de bir güncellemek yeterli
  setInterval(() => (scene.light.direction = sunLightDirection(new Date())), 30000);
  globe.enableLighting = true; // uzaktan bakınca gece-gündüz çizgisi görünür
  // Mars küçük (Dünya'nın ~yarısı) olduğu için solma mesafeleri küçültüldü:
  // kamera 2500 km'den yakınsa Jezero tam aydınlık, 6000 km'den uzaksa tam gölgeli küre.
  globe.lightingFadeOutDistance = 2.5e6;
  globe.lightingFadeInDistance = 6.0e6;
  globe.nightFadeOutDistance = 2.5e6;
  globe.nightFadeInDistance = 6.0e6;

  // --- Mars atmosferi ---
  // Cesium'un atmosferi Dünya için (mavi). Tonu ~180° çevirip (mavi → somon/turuncu),
  // doygunluğu ve parlaklığı düşürerek ince, tozlu Mars atmosferine benzetiyoruz. Değerler göz kararı.
  const ATMO = { hueShift: -0.5, saturationShift: -0.25, brightnessShift: -0.25 };
  Object.assign(scene.skyAtmosphere, ATMO);
  // Yer atmosferi kapalı: küreyi maviye boyuyordu. Sadece kenardaki parıltı (skyAtmosphere) kalıyor.
  globe.showGroundAtmosphere = false;
  globe.dynamicAtmosphereLighting = true;
  globe.dynamicAtmosphereLightingFromSun = false; // Dünya'nın güneşi değil, yukarıdaki ışığı kullan

  // --- Taban katman ---
  let baseLayer = null;
  function setBaseLayer(key) {
    const def = BASE_LAYERS[key];
    if (!def) return;
    if (baseLayer) viewer.imageryLayers.remove(baseLayer, true);
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: def.url,
      tilingScheme: new Cesium.GeographicTilingScheme({ ellipsoid: MARS }),
      maximumLevel: def.maxLevel,
      credit: "NASA/JPL-Caltech Mars Trek – " + def.name,
    });
    baseLayer = viewer.imageryLayers.addImageryProvider(provider, 0);
  }

  const baseSelect = document.getElementById("baseSelect");
  baseSelect.addEventListener("change", () => setBaseLayer(baseSelect.value));
  setBaseLayer(baseSelect.value);

  // --- Jezero yüksek çözünürlüklü mozaikler (Mars Trek, bölgesel) ---
  // Küresel mozaikler en fazla seviye 7 (~300 m/piksel) olduğu için Jezero'da bulanıktı.
  // Bu iki mozaik sadece kendi kutularında karo ister; dışı şeffaf.
  // Seviye sınırları Mars Trek'te denendi: CTX 13'e, HiRISE 17'ye kadar karo var.
  const DETAIL_LAYERS = [
    {
      name: "CTX Jezero mozaiği (6 m)",
      label: "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0",
      bbox: [77.1604655, 18.2110274, 77.6991776, 18.7211945],
      maxLevel: 13,
      alpha: 1,
    },
    {
      name: "HiRISE Jezero mozaiği (25 cm)",
      label: "JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd",
      bbox: [77.2229331, 18.3067994, 77.583964, 18.669315],
      maxLevel: 17,
      alpha: 1,
      // HiRISE parça parça (farklı tonlarda yamalar); genel bakışta CTX daha temiz.
      // Sadece iyice yakınlaşınca (arazi seviyesi 15+, ~birkaç km'lik görüş) devreye girsin.
      minLevel: 15,
    },
  ];
  DETAIL_LAYERS.forEach((d) => {
    const [w, s, e, n] = d.bbox;
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: TREK + d.label + "/1.0.0/default/default028mm/{z}/{y}/{x}.png",
      tilingScheme: new Cesium.GeographicTilingScheme({ ellipsoid: MARS }),
      rectangle: Cesium.Rectangle.fromDegrees(w, s, e, n),
      maximumLevel: d.maxLevel,
      credit: "NASA/JPL-Caltech/USGS Mars Trek – " + d.name,
    });
    viewer.imageryLayers.add(
      new Cesium.ImageryLayer(provider, { alpha: d.alpha, minimumTerrainLevel: d.minLevel })
    );
  });

  // CTX ve HiRISE siyah-beyaz. Üstlerine yarı saydam Mars rengi bir örtü koyup
  // Viking küresiyle aynı renk tonuna getiriyoruz (renk ve oran göz kararı).
  const TINT = { color: "#c4703f", alpha: 0.38 };
  (function addTint() {
    const c = document.createElement("canvas");
    c.width = c.height = 1;
    const ctx = c.getContext("2d");
    ctx.fillStyle = TINT.color;
    ctx.fillRect(0, 0, 1, 1);
    const [w, s, e, n] = DETAIL_LAYERS[0].bbox;
    const tint = viewer.imageryLayers.addImageryProvider(
      new Cesium.SingleTileImageryProvider({
        url: c.toDataURL(),
        rectangle: Cesium.Rectangle.fromDegrees(w, s, e, n),
        tileWidth: 1,
        tileHeight: 1,
      })
    );
    tint.alpha = TINT.alpha;
  })();

  // --- Jezero 3B arazi (Elif'in grid.json yükseklikleri, CTX DEM'den) ---
  // Küresel yükseklik verimiz yok; sadece çalışma alanı kabarık, dışı düz.
  // Yükseklikler kenar ortalamasına göre (göreli) verilir ve kenarlara doğru sıfıra
  // yumuşatılır; böylece alanın sınırında uçurum oluşmaz.
  const TERRAIN_EXAGGERATION = 3;  // varsayım: 11 km'de ~870 m fark; 3x abartı eğik bakışta kabartmayı belirgin yapıyor
  const TERRAIN_FEATHER = 0.08;    // kenarın %8'lik şeridinde yükseklik sıfıra iner
  const TERRAIN_TILE = 32;         // karo başına 32x32 yükseklik örneği

  function makeTerrainSampler(g) {
    const { width: W, height: H, elev } = g;
    const { west, south, east, north } = g.bounds;
    // Kenar ortalaması = taban yüksekliği (alan dışı bu seviyede kabul edilir)
    let sum = 0, cnt = 0;
    for (let i = 0; i < W; i++) { sum += elev[i] + elev[(H - 1) * W + i]; cnt += 2; }
    for (let r = 0; r < H; r++) { sum += elev[r * W] + elev[r * W + W - 1]; cnt += 2; }
    const base = sum / cnt;

    // lon/lat (derece) → göreli yükseklik (m). Alan dışında 0. Satır 0 = kuzey.
    return function sample(lon, lat) {
      const u = (lon - west) / (east - west);
      const v = (north - lat) / (north - south);
      if (u < 0 || u > 1 || v < 0 || v > 1) return 0;
      const x = u * (W - 1), y = v * (H - 1);
      const x0 = Math.floor(x), y0 = Math.floor(y);
      const x1 = Math.min(x0 + 1, W - 1), y1 = Math.min(y0 + 1, H - 1);
      const fx = x - x0, fy = y - y0;
      const h =
        elev[y0 * W + x0] * (1 - fx) * (1 - fy) + elev[y0 * W + x1] * fx * (1 - fy) +
        elev[y1 * W + x0] * (1 - fx) * fy + elev[y1 * W + x1] * fx * fy;
      const d = Math.min(u, 1 - u, v, 1 - v) / TERRAIN_FEATHER;
      const f = d >= 1 ? 1 : d * d * (3 - 2 * d); // yumuşak geçiş (smoothstep)
      return (h - base) * f;
    };
  }

  // Pin/etiket yüksekliği: CLAMP_TO_GROUND yerine araziyi kendimiz örnekliyoruz. Cesium yere oturtulan
  // etiketin her harfini ayrı ayrı oturtuyor; arazi karoları yüklenip netleşirken harfler farklı
  // yüksekliklere düşüp yazı dağılıyordu ("A … yşe"). Aynı örnekleyici araziyi de ürettiği için
  // nokta yüzeyle örtüşür. Yükseklik × abartı (verticalExaggerationRelativeHeight = 0).
  let terrainSample = null;
  const groundHeight = (lon, lat) => (terrainSample ? terrainSample(lon, lat) * TERRAIN_EXAGGERATION : 0);
  const groundCart = (lon, lat) => Cesium.Cartesian3.fromDegrees(lon, lat, groundHeight(lon, lat), MARS);
  // Sabit noktalar için: grid.json gelmeden eklenen pin de arazi gelince doğru yüksekliğe çıkar
  function groundPosition(lon, lat) {
    let cached = null;
    return new Cesium.CallbackProperty(() => {
      if (cached) return cached;
      const c = groundCart(lon, lat);
      if (terrainSample) cached = c;
      return c;
    }, false);
  }

  function enableJezeroTerrain(g) {
    const sample = makeTerrainSampler(g);
    terrainSample = sample;
    const { west, south, east, north } = g.bounds;
    const tiling = new Cesium.GeographicTilingScheme({ ellipsoid: MARS });
    const N = TERRAIN_TILE;
    viewer.terrainProvider = new Cesium.CustomHeightmapTerrainProvider({
      width: N,
      height: N,
      tilingScheme: tiling,
      callback: (x, y, level) => {
        const out = new Float32Array(N * N);
        const r = tiling.tileXYToRectangle(x, y, level);
        const w = Cesium.Math.toDegrees(r.west), e = Cesium.Math.toDegrees(r.east);
        const s = Cesium.Math.toDegrees(r.south), n = Cesium.Math.toDegrees(r.north);
        if (e < west || w > east || n < south || s > north) return out; // alanla kesişmiyor: düz
        for (let i = 0; i < N; i++) {
          const lat = n - (i / (N - 1)) * (n - s);
          for (let j = 0; j < N; j++) out[i * N + j] = sample(w + (j / (N - 1)) * (e - w), lat);
        }
        return out;
      },
    });
    scene.verticalExaggeration = TERRAIN_EXAGGERATION;
    scene.verticalExaggerationRelativeHeight = 0;
  }

  // --- Başlangıç görünümü: Jezero yarımküresi ---
  const HOME_VIEW = {
    destination: Cesium.Cartesian3.fromDegrees(JEZERO.lon, JEZERO.lat, 11000000, MARS),
    orientation: { heading: 0, pitch: -Cesium.Math.PI_OVER_TWO, roll: 0 },
  };
  viewer.camera.setView(HOME_VIEW);

  // --- Otomatik dönüş ---
  let autoRotate = true;
  let lastTime = performance.now();
  const rotateBtn = document.getElementById("rotateBtn");

  function setAutoRotate(on) {
    autoRotate = on;
    rotateBtn.textContent = on ? "Dönmeyi durdur" : "Döndür";
  }

  scene.preUpdate.addEventListener(() => {
    const now = performance.now();
    const dt = (now - lastTime) / 1000;
    lastTime = now;
    if (!autoRotate || scene.mode !== Cesium.SceneMode.SCENE3D) return;
    viewer.camera.rotate(Cesium.Cartesian3.UNIT_Z, -ROTATE_RATE * dt);
  });

  rotateBtn.addEventListener("click", () => setAutoRotate(!autoRotate));

  // Kullanıcı küreyi tutunca/zoom yapınca dönüş dursun
  const canvas = viewer.canvas;
  ["pointerdown", "wheel", "touchstart"].forEach((ev) =>
    canvas.addEventListener(ev, () => setAutoRotate(false), { passive: true })
  );

  // --- G2: Jezero'ya uçuş ---
  // Çalışma alanı layers.json bbox'ından gelir; yüklenene kadar varsayılan kullanılır.
  let studyBbox = [77.36, 18.38, 77.51, 18.52]; // [batı, güney, doğu, kuzey]

  const portrait = () => window.innerHeight > window.innerWidth;

  function flyToJezero() {
    setAutoRotate(false);
    document.getElementById("leftPanel").classList.remove("open");
    const [w, s, e, n] = studyBbox;
    // Tepeden değil, güneyden kuzeye 45° eğik bakış: 3B kabartma görünür, ufuktaki bulanık küre görünmez.
    // Mesafe alanın köşegeninin ~1,4 katı; alanın tamamı ekrana sığıyor.
    const center = Cesium.Cartesian3.fromDegrees((w + e) / 2, (s + n) / 2, 0, MARS);
    const diagM = Cesium.Cartesian3.distance(
      Cesium.Cartesian3.fromDegrees(w, s, 0, MARS),
      Cesium.Cartesian3.fromDegrees(e, n, 0, MARS)
    );
    viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(center, diagM / 2), {
      // Dikey (telefon) ekranda ufuk daha çok görünüyor; açıyı dikleştir ve biraz uzaklaş
      offset: portrait()
        ? new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-72), diagM * 1.7)
        : new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), diagM * 1.4),
      duration: 4,
    });
  }
  document.getElementById("jezeroBtn").addEventListener("click", flyToJezero);

  loadJSON("data/grid.json")
    .then((g) => {
      enableJezeroTerrain(g);
      initZones(g); // G6: aynı grid'i Walkback'e de ver (ikinci kez indirme)
    })
    .catch((err) => console.error("grid.json okunamadı, arazi düz kalacak:", err));

  // Tüm küreye geri dön ve dönmeye devam et
  function flyHome() {
    setAutoRotate(false);
    document.getElementById("leftPanel").classList.remove("open");
    viewer.camera.flyTo({ ...HOME_VIEW, duration: 3, complete: () => setAutoRotate(true) });
  }
  document.getElementById("homeBtn").addEventListener("click", flyHome);

  // --- G2: Katman menüsü (web/data/layers.json) ---
  const overlays = {}; // id -> { def, layer }

  async function loadJSON(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) throw new Error(path + " → HTTP " + res.status);
    return res.json();
  }

  function loadOverlayProvider(def) {
    const [w, s, e, n] = def.bbox;
    return Cesium.SingleTileImageryProvider.fromUrl("data/" + def.file, {
      rectangle: Cesium.Rectangle.fromDegrees(w, s, e, n),
      ellipsoid: MARS,
      credit: def.source,
    });
  }
  function addOverlay(def, provider) {
    const layer = viewer.imageryLayers.addImageryProvider(provider);
    layer.alpha = def.default_opacity ?? 0.6;
    layer.show = false;
    overlays[def.id] = { def, layer };
    return layer;
  }

  function renderLayerRow(def, layer) {
    const row = document.createElement("div");
    row.className = "layer-row";

    const head = document.createElement("label");
    head.className = "layer-head";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = layer.show;
    const name = document.createElement("span");
    name.textContent = def.name;
    head.append(cb, name);

    const body = document.createElement("div");
    body.className = "layer-body";
    body.hidden = !layer.show;

    const op = document.createElement("label");
    op.className = "opacity";
    const opText = document.createElement("span");
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.value = String(Math.round(layer.alpha * 100));
    const setOpText = () => (opText.textContent = "Opaklık %" + slider.value);
    setOpText();
    op.append(opText, slider);

    const legend = document.createElement("ul");
    legend.className = "legend";
    (def.legend || []).forEach((item) => {
      const li = document.createElement("li");
      const sw = document.createElement("i");
      sw.style.background = item.color;
      const lbl = document.createElement("span");
      lbl.textContent = item.label;
      li.append(sw, lbl);
      legend.append(li);
    });

    const src = document.createElement("p");
    src.className = "muted small";
    src.textContent = "Kaynak: " + (def.source || "—");

    body.append(op, legend, src);
    row.append(head, body);

    cb.addEventListener("change", () => {
      layer.show = cb.checked;
      body.hidden = !cb.checked;
      dimZonesForOverlays();
    });
    slider.addEventListener("input", () => {
      layer.alpha = Number(slider.value) / 100;
      setOpText();
    });
    return row;
  }

  async function initLayers() {
    const list = document.getElementById("layerList");
    let defs;
    try {
      defs = await loadJSON("data/layers.json");
    } catch (err) {
      console.error(err);
      list.innerHTML = '<p class="muted">layers.json okunamadı. Sayfayı bir sunucuyla açın (python -m http.server).</p>';
      return;
    }
    if (defs.length) studyBbox = defs[0].bbox;
    list.innerHTML = "";
    // PNG'ler aynı anda iner (sırayla beklemek yavaş ağda listeyi tek tek dolduruyordu);
    // haritaya ve listeye yine layers.json sırasıyla eklenir (üst üste binme sırası sabit kalsın)
    const results = await Promise.allSettled(defs.map(loadOverlayProvider));
    for (const [i, def] of defs.entries()) {
      const r = results[i];
      if (r.status === "fulfilled") {
        list.append(renderLayerRow(def, addOverlay(def, r.value)));
      } else {
        const err = r.reason;
        console.error("Katman yüklenemedi:", def.id, err);
        const p = document.createElement("p");
        p.className = "muted small";
        p.textContent = def.name + ": yüklenemedi";
        list.append(p);
      }
    }
  }
  initLayers();

  // --- G3: Üst bar ---
  // Mars saati ve gecikme gerçek: Elif'in web/marstime.js'i (E8, Mars24 + Kepler).
  // Sol numarası senaryo Sol'ü: sayfa açıldığında Sol 34 (PLAN.md §2), gerçek sol geçtikçe artar.
  // Perseverance'ın gerçek Sol'ü üzerine gelince ipucu olarak görünür.
  const SCENARIO_SOL = 34;
  const scenarioStart = new Date();
  function marsClock() {
    if (window.MarsTime) {
      const t = MarsTime.scenario(SCENARIO_SOL, scenarioStart, new Date());
      return { sol: t.sol, m2020Sol: t.m2020Sol, lmst: t.lmst, delayMin: t.delayMin, minutesToSunset: t.minutesToSunset };
    }
    // marstime.js yüklenemezse yedek sabit değerler
    return { sol: SCENARIO_SOL, lmst: "14:20", delayMin: 12.5, minutesToSunset: null };
  }

  let conditions = [];
  let linkUp = true; // G8 "Telsiz koptu" ile false olacak

  const fmtTime = (d, tz) =>
    d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: tz });

  const toMin = (hhmm) => {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
  };

  function todaysConditions(sol) {
    if (!conditions.length) return null;
    return conditions.find((c) => c.sol === sol) || conditions[conditions.length - 1];
  }

  function updateTopBar() {
    const now = new Date();
    const mc = marsClock();
    const $ = (id) => document.getElementById(id);

    $("tbMarsTime").textContent = mc.lmst + " LMST";
    $("tbSol").textContent = mc.sol;
    if (mc.m2020Sol != null) $("tbSol").title = "Senaryo Sol'ü · Perseverance bugün Sol " + mc.m2020Sol;
    $("tbUtc").textContent = fmtTime(now, "UTC");
    $("tbTr").textContent = fmtTime(now, "Europe/Istanbul");
    $("tbDelay").textContent = mc.delayMin.toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " dk uzakta";

    // Gün batımına kalan: marstime.js'ten (Dünya dakikası); yoksa conditions.json'daki saatten
    const c = todaysConditions(mc.sol);
    const left = mc.minutesToSunset != null ? mc.minutesToSunset : c ? toMin(c.sunset_lmst) - toMin(mc.lmst) : null;
    if (left != null) {
      $("tbSunset").textContent = left > 0 ? Math.floor(left / 60) + " sa " + (left % 60) + " dk" : "gün battı";
    }
    if (c) {
      $("tbWeather").textContent =
        Math.round(c.temp_min_c) + "…" + Math.round(c.temp_max_c) + " °C · toz τ " + c.dust_tau.toFixed(2);
      // conditions.json'da "dummy": true ise gerçek ölçüm değil: başlıkta açıkça "örnek" yazar
      // (jüri veri hakimiyetine bakıyor; varsayım verisini gerçekmiş gibi göstermeyelim)
      $("tbWeatherLabel").textContent = c.dummy ? "Hava · örnek" : "Hava · MEDA";
      $("tbWeather").title = c.dummy
        ? "Örnek değerler (conditions.json, Sol " + c.sol + "): Perseverance MEDA ölçümleri eklenince gerçek olacak."
        : "Perseverance MEDA, Sol " + c.sol;
    }

    const link = $("tbLink");
    link.textContent = linkUp ? "● bağlı" : "● kopuk";
    link.className = linkUp ? "link-ok" : "link-lost";
  }

  function setLink(up) {
    linkUp = up;
    updateTopBar();
  }

  loadJSON("data/conditions.json")
    .then((d) => { conditions = d; updateTopBar(); })
    .catch((err) => console.error(err));
  updateTopBar();
  setInterval(updateTopBar, 1000);

  // --- G3: Sağ panel (detay kartı) ---
  const detailPanel = document.getElementById("detailPanel");
  const detailBody = document.getElementById("detailBody");

  // content: DOM düğümü. Kartları G5'te pinler de buraya basacak.
  function showDetail(content) {
    detailBody.replaceChildren(content);
    detailPanel.hidden = false;
    closeDrawer();
  }
  function hideDetail() {
    detailPanel.hidden = true;
  }
  document.getElementById("detailClose").addEventListener("click", hideDetail);

  function el(tag, attrs, ...children) {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => (k === "class" ? (n.className = v) : n.setAttribute(k, v)));
    children.flat().forEach((c) => c != null && n.append(c));
    return n;
  }

  function kvList(pairs) {
    return el("dl", { class: "kv" }, pairs.flatMap(([k, v]) => [el("dt", null, k), el("dd", null, String(v))]));
  }

  // --- G3/G4: Astronotlar ---
  let astronauts = [];
  let selectedAstroId = null;

  // Bölge etiketi için yer (G6'da Walkback.zones ile hesaplanacak). null = bilinmiyor.
  function zoneBadge(zone) {
    const labels = { green: "YEŞİL", yellow: "SARI", red: "KIRMIZI" };
    return el("span", { class: "zone " + (zone || "") }, zone ? labels[zone] : "BÖLGE –");
  }

  // --- G4: Astronot profili ---
  // Form alanları. min/max tarayıcı doğrulaması için; değerler varsayım.
  // warn: değer bu sınırı geçince kartta kırmızı görünür (G6'daki Go/No-Go'ya da girecek).
  const PROFILE_FIELDS = [
    { key: "name", label: "Ad", type: "text" },
    { key: "mass_kg", label: "Kilo", unit: "kg", min: 40, max: 150, step: 1 },
    { key: "suit", label: "Giysi", type: "text" },
    // O₂ üst sınırı giysi kapasitesi (astronauts.json: o2_capacity_min; xEMU ~8 saat varsayımı)
    { key: "o2_min", label: "O₂", unit: "dk", min: 0, max: (a) => a.o2_capacity_min, step: 1,
      warn: (v, a) => v < a.o2_capacity_min * 0.25 },               // %25 altı: yeşil bölge payı kadar
    { key: "battery_pct", label: "Batarya", unit: "%", min: 0, max: 100, step: 1, warn: (v) => v < 20 },
    { key: "water_pct", label: "Su", unit: "%", min: 0, max: 100, step: 1, warn: (v) => v < 20 },
    // Nabız 150: Apollo 14'te Shepard'ın değeri; PLAN.md §5'te O₂ tüketimi bu noktada ×1,6
    { key: "heart_rate", label: "Nabız", unit: "atım/dk", min: 40, max: 200, step: 1, warn: (v) => v >= 150 },
    // Yük 30 kg üstü: Tobler düzeltmesinde hız %30'dan fazla düşüyor (1 − yük/100)
    { key: "load_kg", label: "Yük", unit: "kg", min: 0, max: 60, step: 0.5, warn: (v) => v > 30 },
    // 1 mSv: Mars yüzeyinde ~1,5 sol'lük doz (Curiosity RAD ~0,64 mSv/gün); EVA başına uyarı eşiği varsayımı
    { key: "radiation_msv", label: "Radyasyon", unit: "mSv", min: 0, max: 50, step: 0.01, warn: (v) => v > 1 },
  ];

  const STORAGE_KEY = "marstrail.astronauts.v1";

  function loadSaved() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      return {};
    }
  }

  // Sonradan eklenen astronotlar (astronauts.json'da olmayanlar) tüm alanlarıyla ayrı anahtarda saklanır;
  // varsayılan iki kişi (Ayşe, Ali) eskisi gibi yalnız profil alanlarıyla STORAGE_KEY'de.
  const EXTRA_KEY = "marstrail.extraAstronauts.v1";
  const isDefaultAstro = (a) => defaultAstronauts.some((d) => d.id === a.id);
  function loadExtras() {
    try {
      const x = JSON.parse(localStorage.getItem(EXTRA_KEY));
      return Array.isArray(x) ? x : [];
    } catch {
      return [];
    }
  }

  function saveAll() {
    const data = {};
    astronauts.forEach((a) => {
      data[a.id] = {};
      PROFILE_FIELDS.forEach((f) => (data[a.id][f.key] = a[f.key]));
    });
    const extras = astronauts.filter((a) => !isDefaultAstro(a)).map(({ zone, _z, ...rest }) => rest);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      localStorage.setItem(EXTRA_KEY, JSON.stringify(extras));
      return true;
    } catch {
      return false; // gizli pencere vb.: kaydedilemedi ama uygulama çalışmaya devam eder
    }
  }

  const fmtNum = (v) => Number(v).toLocaleString("tr-TR", { maximumFractionDigits: 2 });
  const isWarn = (f, a) => (f.warn ? f.warn(Number(a[f.key]), a) : false);

  // Profil değişince haber ver: G6'da O₂ bölgeleri bunu dinleyip yeniden çizecek.
  function emitAstronautChange(a) {
    window.dispatchEvent(new CustomEvent("marstrail:astronaut", { detail: a }));
  }

  function astroDetail(a) {
    const form = el("form", { class: "profile" });

    const rows = PROFILE_FIELDS.map((f) => {
      const input = el("input", { name: f.key, type: f.type || "number", required: "" });
      if (!f.type) {
        input.min = f.min;
        input.max = typeof f.max === "function" ? f.max(a) : f.max;
        input.step = f.step;
        input.inputMode = "decimal";
      }
      input.value = a[f.key];
      const row = el(
        "label",
        { class: "prow" + (isWarn(f, a) ? " warn" : "") },
        el("span", { class: "plabel" }, f.label),
        input,
        el("span", { class: "punit" }, f.unit || "")
      );
      return row;
    });

    const status = el("p", { class: "pstatus muted small" }, "");
    const saveBtn = el("button", { type: "submit", class: "primary" }, "Güncelle");
    // Varsayılan iki kişide "Varsayılana dön", sonradan eklenenlerde "Ekipten çıkar"
    const resetBtn = isDefaultAstro(a)
      ? el("button", { type: "button" }, "Varsayılana dön")
      : el("button", { type: "button", class: "danger-ghost" }, "Ekipten çıkar");

    form.append(
      el("h3", null, a.name),
      el("p", { class: "muted" }, a.role),
      el("div", { class: "zone-line" }, zoneBadge(a.zone), el("span", { class: "muted small" }, zoneText(a.zone))),
      zoneSummary(a),
      ...rows,
      el("div", { class: "controls" }, saveBtn, resetBtn),
      status
    );

    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      if (!form.reportValidity()) return;
      PROFILE_FIELDS.forEach((f) => {
        const v = form.elements[f.key].value;
        a[f.key] = f.type ? v.trim() : Number(v);
      });
      const ok = saveAll();
      emitAstronautChange(a); // önce bölgeler yeniden hesaplansın, sonra kart çizilsin
      renderAstronauts();
      showDetail(astroDetail(a)); // uyarı renklerini ve bölge etiketini tazele
      detailBody.querySelector(".pstatus").textContent = ok
        ? "Kaydedildi · " + new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })
        : "Güncellendi ama tarayıcı kaydetmeye izin vermedi.";
    });

    resetBtn.addEventListener("click", () => {
      const def = defaultAstronauts.find((x) => x.id === a.id);
      if (!def) { removeAstronaut(a); return; }
      PROFILE_FIELDS.forEach((f) => (a[f.key] = def[f.key]));
      saveAll();
      emitAstronautChange(a);
      renderAstronauts();
      showDetail(astroDetail(a));
      detailBody.querySelector(".pstatus").textContent = "astronauts.json değerlerine dönüldü.";
    });

    return form;
  }

  function zoneText(zone) {
    return {
      green: "Şu an YEŞİL bölgedesin: rahat dönüş",
      yellow: "Şu an SARI bölgedesin: dönüş payı yok",
      red: "Şu an KIRMIZI bölgedesin: dönüş O₂'ye yetmiyor",
    }[zone] || "Bölge hesabı O₂ bölgeleriyle gelecek";
  }

  function renderAstronauts() {
    const list = document.getElementById("astroList");
    list.replaceChildren(
      ...astronauts.map((a) => {
        const card = el(
          "button",
          { type: "button", class: "astro" + (a.id === selectedAstroId ? " selected" : "") },
          el("div", { class: "astro-top" }, el("span", { class: "astro-name" }, a.name), zoneBadge(a.zone)),
          el("div", { class: "astro-role" }, a.role),
          el(
            "div",
            { class: "astro-vitals" },
            ...[
              ["o2_min", "O₂ " + fmtNum(a.o2_min) + " dk"],
              ["heart_rate", "♥ " + fmtNum(a.heart_rate)],
              ["battery_pct", "🔋 %" + fmtNum(a.battery_pct)],
              ["water_pct", "💧 %" + fmtNum(a.water_pct)],
            ].map(([k, txt]) =>
              el("span", { class: isWarn(PROFILE_FIELDS.find((f) => f.key === k), a) ? "warn" : "" }, txt)
            )
          ),
          el("div", { class: "o2bar" }, el("i", {
            style: "width:" + Math.max(0, Math.min(100, (a.o2_min / a.o2_capacity_min) * 100)) + "%",
          }))
        );
        card.addEventListener("click", () => selectAstronaut(a.id, true));
        return card;
      }),
      (() => {
        const add = el("button", { type: "button", class: "astro-add" }, "+ Astronot ekle");
        add.addEventListener("click", addAstronaut);
        return add;
      })()
    );
  }

  // Yeni ekip üyesi: varsayılan değerler (xEMU, 480 dk O₂, nabız 80; Ali'ninkilerle aynı varsayım), konum üs.
  // Ad ve diğer alanlar hemen açılan profil formundan değiştirilir.
  function addAstronaut() {
    const base = defaultAstronauts[0] || {};
    const n = astronauts.length + 1;
    const a = {
      id: "astro_" + Date.now().toString(36),
      name: "Astronot " + n, role: "Ekip üyesi", suit: "xEMU (varsayım)",
      mass_kg: 70, o2_min: 480, o2_capacity_min: 480, battery_pct: 100, water_pct: 100,
      heart_rate: 80, load_kg: 4, radiation_msv: 0.3,
      position: { ...(base.position || { lat: 18.4447, lon: 77.4508 }) },
    };
    astronauts.push(a);
    saveAll();
    computeZones();
    selectAstronaut(a.id, true);
    showToast("info", "Ekip", a.name + " eklendi. Adını ve değerlerini profilden değiştirebilirsin.");
  }

  function removeAstronaut(a) {
    if ((walk.active && walk.astro && walk.astro.id === a.id) || rescue.active) {
      showToast("warn", "Ekip", "Yürüyüş ya da acil durum sürerken ekipten çıkarılamaz.");
      return;
    }
    if (evaPlan.result && evaPlan.result.astronautId === a.id) clearPlan();
    astronauts = astronauts.filter((x) => x.id !== a.id);
    saveAll();
    hideDetail();
    selectAstronaut(astronauts[0] && astronauts[0].id, false);
    showToast("info", "Ekip", a.name + " ekipten çıkarıldı.");
  }

  function selectAstronaut(id, openDetail) {
    selectedAstroId = id;
    drawZones(); // haritadaki bölgeler seçili astronotunkiler
    renderAstronauts();
    replanIfActive(); // G6: açık plan seçili astronota göre yeniden hesaplanır
    const a = astronauts.find((x) => x.id === id);
    if (a && openDetail) showDetail(astroDetail(a));
  }

  let defaultAstronauts = [];
  loadJSON("data/astronauts.json")
    .then((d) => {
      defaultAstronauts = JSON.parse(JSON.stringify(d));
      // Kayıtlı profil varsa onun alanları JSON'daki varsayılanın üstüne yazılır
      const saved = loadSaved();
      astronauts = d.map((a) => ({ ...a, ...(saved[a.id] || {}) }))
        .concat(loadExtras().filter((x) => x && x.id && !d.some((a) => a.id === x.id)).map((x) => ({ ...x, ...(saved[x.id] || {}) })));
      selectAstronaut(astronauts[0] && astronauts[0].id, false);
      computeZones(); // grid önce geldiyse bölgeler şimdi hesaplanır
    })
    .catch((err) => {
      console.error(err);
      document.getElementById("astroList").innerHTML = '<p class="muted">astronauts.json okunamadı.</p>';
    });

  // --- G6: O₂ bölgeleri (her zaman açık) ---
  // Hesap Elif'in web/walkback.js'inde (E8): Dijkstra ile gidiş + üsse dönüş süresi,
  // O₂ nabız çarpanıyla bölünür. Yeşil ≤ O₂/1,25, sarı ≤ O₂, kırmızı > O₂ (PLAN.md §3.3).
  // Burada sadece çizim ve arayüz var.
  const ZONE_ALPHA = 0.4;          // bölge dolgusunun saydamlığı (arazi görünsün diye)
  // Veri katmanı (eğim, termal…) açıkken bölge dolgusu bu oranda soluklaşır, sınır çizgileri kalır.
  // Neden: eğim ve geçilebilirlik de yeşil/sarı/kırmızı; dolgu üstte kalınca katman okunmuyordu.
  // 0,25: dolgu ~%10 görünür (0,4 × 0,25), renk ipucu kalır ama alttaki katmanı boyamaz (göz kararı).
  const ZONE_DIM_WITH_OVERLAY = 0.25;
  let zonesReady = false;
  let zoneLayer = null;            // dolgu (ImageryLayer)
  const zoneEntities = [];         // sınır çizgileri + astronot simgesi

  function initZones(grid) {
    if (!window.Walkback) {
      console.error("walkback.js yüklenemedi; O₂ bölgeleri çizilemiyor");
      return;
    }
    Walkback.init(grid);
    zonesReady = true;
    computeZones();
  }

  // Bütün astronotlar için bölgeyi hesapla (kart etiketleri), seçili olanı haritaya çiz
  function computeZones() {
    if (!zonesReady || !astronauts.length) return;
    astronauts.forEach((a) => {
      try {
        const z = Walkback.zones(a.position, Number(a.o2_min), Number(a.heart_rate), Number(a.load_kg));
        a.zone = z.here;
        a._z = z; // çizim için sakla (kaydedilmez: PROFILE_FIELDS'ta yok)
      } catch (err) {
        console.error("Bölge hesaplanamadı:", a.id, err);
        a.zone = null;
        a._z = null;
      }
    });
    renderAstronauts();
    drawZones();
  }

  // Eski çizim hemen silinmez: yenisinin dolgusu/çizgileri yüklenene kadar 1,5 sn kalır,
  // yoksa canlı yürüyüşte her güncellemede bölgeler bir an kaybolur (göz kararı süre).
  const ZONE_SWAP_MS = 1500;
  function clearZoneDrawing() {
    const oldLayer = zoneLayer, oldEntities = zoneEntities.splice(0);
    zoneLayer = null;
    const drop = () => {
      if (oldLayer) viewer.imageryLayers.remove(oldLayer, true);
      oldEntities.forEach((e) => viewer.entities.remove(e));
    };
    if (oldLayer || oldEntities.length) setTimeout(drop, ZONE_SWAP_MS);
  }

  // Herhangi bir veri katmanı açıksa O₂ bölge dolgusunu soluklaştır (çizgiler her zaman tam)
  function dimZonesForOverlays() {
    if (!zoneLayer) return;
    const anyOn = Object.values(overlays).some((o) => o.layer.show);
    zoneLayer.alpha = anyOn ? ZONE_DIM_WITH_OVERLAY : 1;
  }

  function drawZones() {
    if (!zonesReady) return;
    if (typeof rescue !== "undefined" && rescue.active) return; // G8: acil durumda ısı haritası okunsun
    const a = astronauts.find((x) => x.id === selectedAstroId);
    clearZoneDrawing();
    if (!a || !a._z) return;
    const z = a._z;
    const b = Walkback.grid.b;

    // 1) Dolgu: walkback'in 256×256 canvas'ı grid sınırlarına serilir
    zoneLayer = viewer.imageryLayers.addImageryProvider(
      new Cesium.SingleTileImageryProvider({
        url: z.canvas(ZONE_ALPHA).toDataURL(),
        rectangle: Cesium.Rectangle.fromDegrees(b.west, b.south, b.east, b.north),
        tileWidth: Walkback.grid.w,
        tileHeight: Walkback.grid.h,
      })
    );
    dimZonesForOverlays();

    // 2) Sınır çizgileri: araziye yapışık, net görünsün diye kalın
    const lines = [
      ["green", z.outlines.green, "#2ecc71"],
      ["yellow", z.outlines.yellow, "#f1c40f"],
    ];
    lines.forEach(([, polys, color]) =>
      polys.forEach((pts) =>
        zoneEntities.push(
          viewer.entities.add({
            polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray(pts.flat(), MARS),
              width: 2.5,
              material: Cesium.Color.fromCssColorString(color),
              clampToGround: true,
            },
          })
        )
      )
    );

    // 3) Astronot simgesi (canlı yürüyüşte hareketli simge var, sabit olan çizilmez)
    if (!walk.active || walk.astro !== a) zoneEntities.push(
      viewer.entities.add({
        position: groundPosition(a.position.lon, a.position.lat),
        point: {
          pixelSize: 12,
          color: Cesium.Color.fromCssColorString("#ff7a2f"),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY, // arazinin arkasında kaybolmasın
        },
        label: {
          text: a.name,
          font: "600 13px 'Segoe UI', system-ui, sans-serif",
          fillColor: Cesium.Color.WHITE,
          ...LABEL_BG,
          // Ad sağda: üstte Three Forks etiketi, altta üs etiketi var (alan v2'de pinler sıkıştı)
          pixelOffset: new Cesium.Cartesian2(10, 0),
          horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
    );

    updateZonePanel(a);
  }

  // Sol paneldeki "O₂ bölgeleri" kutusu: seçili astronotun özeti
  function updateZonePanel(a) {
    const box = document.getElementById("zoneStats");
    if (!box) return;
    box.replaceChildren(zoneSummary(a));
  }

  function zoneSummary(a) {
    const z = a && a._z;
    if (!z) return el("p", { class: "muted small" }, "Bölgeler hesaplanıyor…");
    const fmt = (v) => Math.round(v).toLocaleString("tr-TR");
    return el(
      "dl",
      { class: "kv zone-kv" },
      el("dt", null, "Kullanılabilir O₂"),
      el("dd", null, fmt(z.availableMin) + " dk (nabız ×" + z.multiplier.toFixed(2) + ")"),
      el("dt", null, "Üsse dönüş"),
      el("dd", null, fmt(z.homeMin) + " dk"),
      el("dt", null, "Yeşil / sarı alan"),
      el("dd", null, z.stats.greenKm2.toLocaleString("tr-TR") + " / " + z.stats.yellowKm2.toLocaleString("tr-TR") + " km²")
    );
  }

  // Profil "Güncelle" ya da "Varsayılana dön" → bölgeleri anında yeniden hesapla
  window.addEventListener("marstrail:astronaut", computeZones);

  // =====================================================================
  // --- G5: Nokta pinleri ve kartları (Elif'in E7 verisi) ---
  // =====================================================================
  const POI_STYLE = {
    habitat: { color: "#ff7a2f", label: "Habitat" },
    science: { color: "#5dade2", label: "Bilim hedefi" },
    hazard: { color: "#e74c3c", label: "Tehlike" },
    history: { color: "#bb8fce", label: "Tarihi nokta" },
  };
  // Birbirine çok yakın pinlerin etiketleri çakışıyor (üs–uçuş alanı 20 m, delta–Three Forks ~400 m).
  // Etiketin yönünü elle ayırıyoruz: [x, y] piksel kaydırma, yatay hiza ve görünme mesafesi (m).
  const LABEL_PLACE = {
    base: { off: [-12, 0], origin: "RIGHT", vOrigin: "CENTER" },                         // üs etiketi solda (Ayşe sağ üstte, Rochette altta)
    airfield: { off: [12, 0], origin: "LEFT", maxDist: 3000 },          // sadece çok yakında
    delta_front: { off: [-12, -7], origin: "RIGHT" },                   // sola, biraz yukarı
    three_forks: { off: [12, -2], origin: "LEFT" },                     // sağa
    sand_field: { off: [-12, 7], origin: "RIGHT" },                     // sola, biraz aşağı (alta koyunca üs etiketine değiyordu)
    rochette: { off: [0, 16], origin: "CENTER", vOrigin: "TOP" },       // alta (üs etiketiyle çakışmasın)
  };
  let regions = [];
  let stories = [];
  const poiById = {};

  const fmtDateTR = (s) => {
    // "2005", "2021-02-18" ya da "2022-12-21/2023-01-28" gibi tarihleri okunur yaz
    if (!s) return "";
    if (/^\d{4}$/.test(s)) return s;
    return s
      .split("/")
      .map((d) => {
        const t = new Date(d + "T00:00:00Z");
        return isNaN(t) ? d : t.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
      })
      .join(" – ");
  };

  function link(href, text) {
    const a = el("a", { href, target: "_blank", rel: "noopener" }, text);
    return a;
  }

  function regionCard(r, poi) {
    const style = POI_STYLE[(poi && poi.type) || r.poi_type] || POI_STYLE.science;
    const parts = [
      el("span", { class: "chip", style: "--chip:" + style.color }, style.label),
      el("h3", null, r.name),
    ];
    if (r.science_value) {
      parts.push(el("p", { class: "stars", title: "Bilim değeri " + r.science_value + "/5" },
        "★".repeat(r.science_value) + "☆".repeat(5 - r.science_value), el("span", { class: "muted small" }, " bilim değeri")));
    }
    if (r.summary) parts.push(el("p", null, r.summary));

    // Perseverance Sol'ü + fotoğraf: "Oraya vardığında bunu göreceksin"
    if (r.sol != null) {
      parts.push(el("p", { class: "sol-line" }, "Perseverance buraya ", el("b", null, "Sol " + r.sol), "'de geldi."));
    }
    const photos = r.photos || [];
    if (photos.length) {
      const fig = el("figure", { class: "photo" });
      const img = el("img", { alt: photos[0].caption || r.name, loading: "lazy" });
      const cap = el("figcaption", { class: "muted small" });
      const show = (p) => {
        img.src = "data/" + p.url;
        cap.replaceChildren(
          el("span", null, "Oraya vardığında bunu göreceksin · " + (p.caption || "")),
          el("br"),
          el("span", null, (p.credit || "NASA/JPL-Caltech") + " · "),
          p.page ? link(p.page, "kaynak") : ""
        );
      };
      show(photos[0]);
      fig.append(img, cap);
      if (photos.length > 1) {
        const tabs = el("div", { class: "photo-tabs" });
        photos.forEach((p, i) => {
          const b = el("button", { type: "button", class: i === 0 ? "on" : "" }, p.camera || "Foto " + (i + 1));
          b.addEventListener("click", () => {
            show(p);
            tabs.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
          });
          tabs.append(b);
        });
        fig.append(tabs);
      }
      parts.push(fig);
    }

    // Tarihçe zaman çizgisi
    if ((r.history || []).length) {
      parts.push(el("h4", null, "Tarihçe"));
      parts.push(
        el("ol", { class: "timeline" },
          r.history.map((h) =>
            el("li", null,
              el("time", null, fmtDateTR(h.date)),
              el("span", null, h.event, " "),
              h.source ? link(h.source, "↗") : ""
            )
          )
        )
      );
    }

    // Arazi (Elif'in grid'inden): yürüyüş için anlamı
    const t = r.terrain;
    if (t) {
      const pct = (v) => "%" + Math.round(v * 100);
      parts.push(el("h4", null, "Arazi"));
      parts.push(kvList([
        ["Yükseklik", t.elevation_m + " m"],
        ["Eğim", t.slope_deg + "° (300 m içinde en fazla " + t.max_slope_300m_deg + "°)"],
        ["Kum (300 m)", pct(t.sand_pct_300m)],
        ["Jeoloji", t.geology_unit],
        ["Geçilebilirlik skoru", t.traversability_score + " (0 kolay – 1 zor)"],
      ]));
    }
    if ((r.hazards || []).length) parts.push(el("p", { class: "warn-line" }, "⚠ " + r.hazards.join(", ")));
    if ((r.missions || []).length) parts.push(el("p", { class: "muted small" }, "Görevler: " + r.missions.join(", ")));

    // G6: noktayı EVA planına durak olarak ekle
    if (canBeStop(r)) {
      const inPlan = evaPlan.stops.some((s) => s.id === r.id);
      const btn = el("button", { type: "button", class: inPlan ? "" : "primary" }, inPlan ? "Planda ✓" : "Plana ekle");
      btn.disabled = inPlan;
      btn.addEventListener("click", () => {
        addPlanStop(r.id);
        btn.textContent = "Planda ✓";
        btn.disabled = true;
        btn.classList.remove("primary");
      });
      parts.push(el("div", { class: "controls card-actions" }, btn));
    }

    return el("div", { class: "card" }, parts);
  }

  function storyCard(s) {
    return el("div", { class: "story" },
      el("h4", null, s.title),
      el("p", { class: "muted small" }, fmtDateTR(s.date) + " · " + s.location_text),
      el("p", null, s.body),
      el("p", { class: "lesson" }, "MarsTrail'deki karşılığı: " + s.lesson),
      s.source ? link(s.source, "Kaynak ↗") : ""
    );
  }

  function hazardCard(props) {
    const style = POI_STYLE.hazard;
    const parts = [
      el("span", { class: "chip", style: "--chip:" + style.color }, style.label),
      el("h3", null, props.name),
    ];
    if (props.note) parts.push(el("p", null, props.note));
    if (props.area_km2) parts.push(el("p", { class: "muted small" }, "Alan: " + props.area_km2.toLocaleString("tr-TR") + " km² · " + (props.source || "")));
    const ss = (props.story_ids || []).map((id) => stories.find((s) => s.id === id)).filter(Boolean);
    if (ss.length) {
      parts.push(el("h4", null, "Bu kum türü neye benziyor?"));
      ss.forEach((s) => parts.push(storyCard(s)));
    }
    return el("div", { class: "card" }, parts);
  }

  function openPoi(id) {
    const f = poiById[id];
    if (!f) return;
    const p = f.properties;
    const r = regions.find((x) => x.id === (p.region_id || p.id));
    showDetail(r ? regionCard(r, p) : hazardCard(p));
  }

  // Haritada kısa ad (tam ad kartta): "Üs – Octavia E. Butler iniş alanı" → "Üs"
  const POI_SHORT = { base: "Üs", three_forks: "Three Forks", airfield: "Ingenuity alanı", jezero: "Jezero Krateri", cheyava_falls: "Cheyava Falls", rochette: "Rochette" };
  const poiLabel = (p) => POI_SHORT[p.region_id || p.id] || POI_SHORT[p.id] || p.name.split(/ [–(]/)[0];

  function addPoiEntities(geo) {
    geo.features.forEach((f) => {
      const p = f.properties;
      poiById[p.id] = f;
      const [lon, lat] = f.geometry.coordinates;
      const style = POI_STYLE[p.type] || POI_STYLE.science;
      const place = LABEL_PLACE[p.id] || {};
      viewer.entities.add({
        id: "poi:" + p.id,
        position: groundPosition(lon, lat),
        point: {
          pixelSize: p.type === "habitat" ? 14 : 11,
          color: Cesium.Color.fromCssColorString(style.color),
          outlineColor: Cesium.Color.fromCssColorString("#16120f"),
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          // Küre görünümünde (1500 km'den uzak) pinler gizli: kalabalık yapmasın
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1.5e6),
        },
        label: {
          text: poiLabel(p),
          font: "600 12px 'Segoe UI', system-ui, sans-serif",
          fillColor: Cesium.Color.WHITE,
          ...LABEL_BG,
          pixelOffset: new Cesium.Cartesian2(...(place.off || [0, -16])),
          horizontalOrigin: Cesium.HorizontalOrigin[place.origin || "CENTER"],
          verticalOrigin: Cesium.VerticalOrigin[place.vOrigin || "BOTTOM"],
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          // Etiketler sadece yakında (varsayılan 40 km)
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, place.maxDist || 4.0e4),
        },
      });
    });
  }

  function renderStories() {
    const box = document.getElementById("storyList");
    box.replaceChildren(
      ...stories.map((s) => {
        const b = el("button", { type: "button", class: "story-btn" },
          el("b", null, s.title), el("span", { class: "muted small" }, fmtDateTR(s.date)));
        b.addEventListener("click", () => showDetail(el("div", { class: "card" }, storyCard(s))));
        return b;
      })
    );
  }

  Promise.all([loadJSON("data/regions.json"), loadJSON("data/poi.geojson"), loadJSON("data/stories.json")])
    .then(([r, geo, s]) => {
      regions = r;
      stories = s;
      renderPlanStops(); // G6: durak listesi nokta adlarıyla
      addPoiEntities(geo);
      renderStories();
    })
    .catch((err) => {
      console.error("Nokta verileri okunamadı:", err);
      document.getElementById("storyList").innerHTML = '<p class="muted">Nokta verileri okunamadı.</p>';
    });

  // =====================================================================
  // --- G5: Rota çizme + istatistik + yükseklik profili ---
  // =====================================================================
  // Süre, PLAN.md §5'teki Tobler formülüyle (Elif'in walkback.js'iyle aynı varsayımlar):
  //   v = 6·exp(−3,5·|tanθ + 0,05|) km/sa × 0,6 (Mars + giysi) × (1 − yük/100)
  // Burası düz çizgi boyunca "çizdiğin rota"nın süresi; güvenli rota (Dijkstra) planlayıcıda (G6/E11).
  const ROUTE_STEP_M = 25;      // profil örnek aralığı (grid hücresi ~44 m'nin yarısı)
  const route = { drawing: false, pts: [], entities: [], line: null, chart: null };

  function gridElevation(lon, lat) {
    const g = window.Walkback && Walkback.grid;
    if (!g) return null;
    const { w, h, b, elev } = g;
    const u = (lon - b.west) / (b.east - b.west), v = (b.north - lat) / (b.north - b.south);
    if (u < 0 || u > 1 || v < 0 || v > 1) return null; // çalışma alanı dışı
    const x = u * (w - 1), y = v * (h - 1);
    const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(x0 + 1, w - 1), y1 = Math.min(y0 + 1, h - 1);
    const fx = x - x0, fy = y - y0;
    return elev[y0 * w + x0] * (1 - fx) * (1 - fy) + elev[y0 * w + x1] * fx * (1 - fy) +
      elev[y1 * w + x0] * (1 - fx) * fy + elev[y1 * w + x1] * fx * fy;
  }

  function toblerKmh(slope, loadKg) {
    return 6 * Math.exp(-3.5 * Math.abs(slope + 0.05)) * 0.6 * (1 - loadKg / 100);
  }

  // Rotayı ROUTE_STEP_M aralıkla örnekle → mesafe, yükseklik, süre
  function analyzeRoute(pts, loadKg) {
    const samples = []; // {d, lon, lat, elev}
    let total = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const a = Cesium.Cartographic.fromDegrees(pts[i][0], pts[i][1]);
      const b = Cesium.Cartographic.fromDegrees(pts[i + 1][0], pts[i + 1][1]);
      const geo = new Cesium.EllipsoidGeodesic(a, b, MARS);
      const len = geo.surfaceDistance;
      const n = Math.max(1, Math.ceil(len / ROUTE_STEP_M));
      for (let k = i === 0 ? 0 : 1; k <= n; k++) {
        const c = geo.interpolateUsingFraction(k / n);
        const lon = Cesium.Math.toDegrees(c.longitude), lat = Cesium.Math.toDegrees(c.latitude);
        samples.push({ d: total + (len * k) / n, lon, lat, elev: gridElevation(lon, lat) });
      }
      total += len;
    }
    let minutes = 0, up = 0, down = 0, outside = false;
    for (let i = 1; i < samples.length; i++) {
      const s0 = samples[i - 1], s1 = samples[i];
      const dd = s1.d - s0.d;
      if (s0.elev == null || s1.elev == null) {
        outside = true;
        minutes += (dd / 1000 / toblerKmh(0, loadKg)) * 60; // alan dışı: düz kabul
        continue;
      }
      const dh = s1.elev - s0.elev;
      if (dh > 0) up += dh; else down -= dh;
      minutes += (dd / 1000 / toblerKmh(dh / dd, loadKg)) * 60;
    }
    return { samples, distanceM: total, minutes, up, down, outside };
  }

  function pickLonLat(screenPos) {
    const ray = viewer.camera.getPickRay(screenPos);
    const cart = ray && scene.globe.pick(ray, scene);
    if (!cart) return null;
    const c = Cesium.Cartographic.fromCartesian(cart, MARS);
    return [Cesium.Math.toDegrees(c.longitude), Cesium.Math.toDegrees(c.latitude)];
  }

  function clearRoute() {
    route.entities.splice(0).forEach((e) => viewer.entities.remove(e));
    route.pts = [];
    if (route.chart) { route.chart.destroy(); route.chart = null; }
    document.getElementById("routeClearBtn").disabled = true;
  }

  function redrawRoute() {
    route.entities.splice(0).forEach((e) => viewer.entities.remove(e));
    route.pts.forEach((p, i) =>
      route.entities.push(viewer.entities.add({
        position: groundPosition(p[0], p[1]),
        point: {
          pixelSize: i === 0 ? 10 : 8,
          color: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.fromCssColorString("#ff7a2f"),
          outlineWidth: 3,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      }))
    );
    if (route.pts.length > 1) {
      route.entities.push(viewer.entities.add({
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(route.pts.flat(), MARS),
          width: 4,
          material: route.drawing
            ? new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.fromCssColorString("#ff7a2f"), dashLength: 12 })
            : Cesium.Color.fromCssColorString("#ff7a2f"),
          clampToGround: true,
        },
      }));
    }
    document.getElementById("routeClearBtn").disabled = route.pts.length === 0;
  }

  function setDrawing(on) {
    route.drawing = on;
    const btn = document.getElementById("routeBtn");
    btn.textContent = on ? "Bitir" : "Rota çiz";
    btn.classList.toggle("primary", on);
    document.getElementById("routeHint").hidden = !on;
    document.getElementById("routeFab").hidden = !on;
    viewer.canvas.style.cursor = on ? "crosshair" : "";
    if (on) {
      clearRoute();
      setAutoRotate(false);
    }
  }

  function finishRoute() {
    setDrawing(false);
    redrawRoute();
    if (route.pts.length < 2) {
      clearRoute();
      return;
    }
    showRouteCard();
  }

  function showRouteCard() {
    const a = astronauts.find((x) => x.id === selectedAstroId);
    const loadKg = a ? Number(a.load_kg) : 0;
    const r = analyzeRoute(route.pts, loadKg);
    const fmt = (v, d = 0) => v.toLocaleString("tr-TR", { maximumFractionDigits: d });

    // O₂: astronotun nabız çarpanıyla tüketim (walkback ile aynı formül)
    const mult = window.Walkback ? Walkback.o2Multiplier(a ? Number(a.heart_rate) : 90) : 1;
    const o2Used = r.minutes * mult;
    // Rotanın bittiği yerin bölgesi (seçili astronotun O₂ bölgelerinden)
    let endZone = null;
    if (a && a._z && window.Walkback) {
      const last = route.pts[route.pts.length - 1];
      const i = Walkback.cellOf({ lon: last[0], lat: last[1] });
      endZone = i >= 0 ? { 1: "green", 2: "yellow", 3: "red", 4: "red" }[a._z.classes[i]] : null;
    }

    const canvas = el("canvas", { "aria-label": "Yükseklik profili" });
    const parts = [
      el("span", { class: "chip", style: "--chip:#ff7a2f" }, "Rota"),
      el("h3", null, "Çizilen rota"),
      kvList([
        ["Mesafe", fmt(r.distanceM / 1000, 2) + " km"],
        ["Süre (tek yön)", fmt(r.minutes) + " dk" + (a ? " · " + a.name + ", yük " + fmt(loadKg, 1) + " kg" : "")],
        ["O₂ ihtiyacı", fmt(o2Used) + " dk (nabız ×" + mult.toFixed(2) + ")"],
        ["Tırmanış / iniş", "+" + fmt(r.up) + " m / −" + fmt(r.down) + " m"],
      ]),
    ];
    if (endZone) {
      parts.push(el("div", { class: "zone-line" }, zoneBadge(endZone),
        el("span", { class: "muted small" }, "Rotanın sonu " + a.name + " için " + { green: "YEŞİL", yellow: "SARI", red: "KIRMIZI" }[endZone] + " bölgede")));
    }
    if (r.outside) parts.push(el("p", { class: "warn-line" }, "⚠ Rotanın bir kısmı çalışma alanı dışında; orada arazi düz kabul edildi."));

    // Engeller ve zorluk: çizgi boyunca grid hücreleri (füzyon skoru, eolyen kum, geçilmez hücre, eğim)
    const h = routeHazards(r.samples);
    if (h) {
      parts.push(el("h4", null, "Engeller ve zorluk"));
      parts.push(el("div", { class: "zone-line" },
        el("span", { class: "difficulty " + h.level.cls }, h.level.text),
        el("span", { class: "muted small" }, "ortalama zorluk skoru " + h.meanScore.toFixed(2) + " (0 kolay – 1 zor)")));
      parts.push(kvList([
        ["Kum alanı", h.sandM > 0 ? fmt(h.sandM) + " m (rotanın %" + fmt((h.sandM / r.distanceM) * 100) + "'i)" : "yok"],
        ["Geçilmez hücre", h.blockedM > 0 ? fmt(h.blockedM) + " m (eğim > 25° ya da skor > 0,8)" : "yok"],
        ["En dik eğim", fmt(h.maxSlope, 1) + "°" + (h.maxSlope > 15 ? " (15° üstü: dikkat)" : "")],
        ["En zor kesim", h.worstAtKm != null ? fmt(h.worstAtKm, 2) + " km'de, skor " + h.worstScore.toFixed(2) : "–"],
      ]));
    }
    // Hazır güvenli durakların dışındaki nokta = test edilmemiş rota
    const conv = routeToStops(route.pts);
    if (conv.custom.length) {
      parts.push(el("p", { class: "warn-line" }, "⚠ Dikkat: daha önce test edilmemiş bir rotada yürümek istiyorsunuz. " +
        "Güvenli duraklarımız: " + regions.filter(canBeStop).map(shortName).join(", ") + "."));
    }
    const go = el("button", { type: "button", class: "primary" }, "▶ Bu rotada yürü");
    go.disabled = !conv.stops.length || walk.active;
    go.addEventListener("click", () => planFromRoute(conv));
    parts.push(el("div", { class: "controls" }, go));
    parts.push(el("p", { class: "muted small" }, "Plana çevrilince noktalar arasında güvenli yol (Dijkstra), dönüş noktası ve Go/No-Go hesaplanır; yürüyüş plan kartından başlar."));

    parts.push(el("h4", null, "Yükseklik profili (m)"));
    parts.push(el("div", { class: "chart-box" }, canvas));
    parts.push(el("p", { class: "muted small" }, "Süre: Tobler formülü × 0,6 (Mars + giysi) × (1 − yük/100). Düz çizgi boyunca; güvenli rota planlayıcıda."));
    showDetail(el("div", { class: "card" }, parts));
    drawProfile(canvas, r.samples);
  }

  // Zorluk sınıfı ortalama füzyon skorundan. Eşikler göz kararı: alanın tipik hücresi ~0,22 (E10 medyanı),
  // 0,8 geçilmez sınırı; < 0,30 tipik arazi = kolay, 0,30–0,45 orta, ≥ 0,45 zor.
  const DIFFICULTY = [
    { max: 0.30, text: "KOLAY", cls: "easy" },
    { max: 0.45, text: "ORTA", cls: "mid" },
    { max: Infinity, text: "ZOR", cls: "hard" },
  ];
  function routeHazards(samples) {
    const G = window.Walkback && Walkback.grid;
    if (!G) return null;
    let sandM = 0, blockedM = 0, scoreSum = 0, len = 0, maxSlope = 0, worst = -1, worstAt = null;
    for (let i = 1; i < samples.length; i++) {
      const s0 = samples[i - 1], s1 = samples[i], dd = s1.d - s0.d;
      const c = Walkback.cellOf({ lon: (s0.lon + s1.lon) / 2, lat: (s0.lat + s1.lat) / 2 });
      if (c < 0 || dd <= 0) continue;
      len += dd;
      scoreSum += G.score[c] * dd;
      if (G.sand[c]) sandM += dd;
      if (G.blocked[c]) blockedM += dd;
      if (G.score[c] > worst) { worst = G.score[c]; worstAt = s1.d / 1000; }
      if (s0.elev != null && s1.elev != null) maxSlope = Math.max(maxSlope, (Math.atan(Math.abs(s1.elev - s0.elev) / dd) * 180) / Math.PI);
    }
    if (!len) return null;
    const meanScore = scoreSum / len;
    return { sandM, blockedM, meanScore, maxSlope, worstScore: worst, worstAtKm: worstAt,
      level: DIFFICULTY.find((d) => meanScore < d.max) };
  }

  // Çizilen noktaları plan duraklarına çevir. Hazır bir durağa 150 m'den (~2 grid hücresi) yakın nokta o durak
  // sayılır; üsse 300 m'den yakın ilk/son nokta atlanır (plan zaten üsten çıkıp üsse döner).
  const M_PER_DEG_MARS = 59274.7; // Mars 2000 küresi: 2πR/360 (rescue.js ile aynı)
  const distM = (a, b) => Math.hypot((a.lon - b.lon) * Math.cos((a.lat * Math.PI) / 180), a.lat - b.lat) * M_PER_DEG_MARS;
  function routeToStops(pts) {
    const base = Walkback.BASE, stops = [], custom = [];
    pts.forEach(([lon, lat], i) => {
      const p = { lon, lat };
      if ((i === 0 || i === pts.length - 1) && distM(p, base) < 300) return;
      const safe = regions.filter(canBeStop).find((r) => distM(p, r) < 150);
      if (safe) { if (!stops.some((s) => s.id === safe.id)) stops.push({ id: safe.id, dwellMin: DEFAULT_DWELL_MIN }); return; }
      const s = { id: "pt_" + Date.now().toString(36) + "_" + i, custom: true, name: "Nokta " + (custom.length + 1), lon, lat, dwellMin: 0 };
      custom.push(s); stops.push(s);
    });
    return { stops, custom };
  }
  function planFromRoute(conv) {
    if (walk.active) return;
    evaPlan.stops = conv.stops.map((s) => ({ ...s }));
    renderPlanStops();
    setDrawing(false);
    clearRoute();
    runPlan(true); // plan kartı açılır: güvenli yol, dönüş noktası, Go/No-Go ve "Yürüyüşü başlat"
    if (conv.custom.length) showToast("warn", "Rota", "Dikkat: daha önce test edilmemiş bir rotada yürümek istiyorsunuz.");
  }

  function drawProfile(canvas, samples) {
    if (route.chart) { route.chart.destroy(); route.chart = null; }
    if (typeof Chart === "undefined") return;
    const css = getComputedStyle(document.documentElement);
    const ink = css.getPropertyValue("--muted").trim() || "#b39c90";
    const grid = "rgba(179,156,144,0.15)"; // sönük ızgara
    const accent = css.getPropertyValue("--accent").trim() || "#ff7a2f";
    const pts = samples.filter((s) => s.elev != null).map((s) => ({ x: s.d / 1000, y: Math.round(s.elev) }));
    route.chart = new Chart(canvas, {
      type: "line",
      data: {
        datasets: [{
          data: pts,
          borderColor: accent,
          borderWidth: 2,
          backgroundColor: accent + "26", // ~%15 dolgu
          fill: "start",
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: accent,
          pointHoverBorderColor: "#16120f",
          pointHoverBorderWidth: 2,
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        interaction: { mode: "index", intersect: false }, // imleç: en yakın mesafedeki değer
        plugins: {
          legend: { display: false }, // tek seri: başlık adlandırıyor
          tooltip: {
            displayColors: false,
            callbacks: {
              title: (it) => it[0].parsed.x.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " km",
              label: (it) => it.parsed.y.toLocaleString("tr-TR") + " m",
            },
          },
        },
        scales: {
          // Eksen rotanın sonunda bitsin (Chart.js yuvarlayınca 11,4 km'lik rotada eksen 15 km'ye uzuyordu)
          x: { type: "linear", min: 0, max: pts.length ? pts[pts.length - 1].x : undefined,
               ticks: { color: ink, callback: (v) => v.toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " km", maxTicksLimit: 6 }, grid: { color: grid } },
          y: { ticks: { color: ink, maxTicksLimit: 5 }, grid: { color: grid } },
        },
      },
    });
  }

  // =====================================================================
  // --- G6 (2. kısım): EVA planlayıcı arayüzü ---
  // =====================================================================
  // Hesap Elif'in web/eva.js'inde (E11): Dijkstra bacakları, yorgunluk, numune yükü, dönüş noktası,
  // Go/No-Go. Burada durak listesi, haritaya çizim ve plan kartı var.
  const DEFAULT_DWELL_MIN = 30;   // yeni durağın varsayılan kalma süresi (dk); kullanıcı değiştirir
  const PLAN_COLORS = {
    out: "#5dade2",               // gidiş: mavi (yeşil/sarı/kırmızı bölgelerle ve turuncu çizim rotasıyla karışmasın)
    back: "#ffffff",              // dönüş: beyaz kesikli
    turn: "#e74c3c",              // dönüş noktası
    margin: "#f1c40f",            // %25 pay sınırı
    radio: "#bb8fce",             // telsiz gölgesi
  };
  const STATUS_TEXT = { ok: "GO", warn: "DİKKAT", fail: "NO-GO" };
  const evaPlan = {
    // Demo planı: E11 testindeki senaryo (Üs → Delta önü 40 dk → Three Forks 30 dk → Üs)
    stops: [{ id: "delta_front", dwellMin: 40 }, { id: "three_forks", dwellMin: 30 }],
    result: null,
    entities: [],
  };

  const regionById = (id) => regions.find((r) => r.id === id);
  // Durak olamayanlar: üs (plan zaten üste döner) ve Jezero Krateri (45 km'lik kraterin tamamı, pini
  // merkezde; durak yapılınca 34 sa / 43 km'lik anlamsız plan çıkıyordu)
  const NOT_A_STOP = new Set(["base", "jezero"]);
  const canBeStop = (r) => r && !NOT_A_STOP.has(r.id);
  // Panelde ve kartta kısa ad: "Delta önü (Hawksbill…)" → "Delta önü"; ayırıcısı olmayan uzun adlar elle
  const SHORT_NAMES = { three_forks: "Three Forks", airfield: "Ingenuity alanı" };
  const shortName = (r) => (r ? SHORT_NAMES[r.id] || r.name.split(/ [–(]/)[0] : "?");
  // Haritadan seçilen serbest noktalar planda "custom" durak olarak durur (id, name, lon, lat kendisinde);
  // hazır duraklar regions.json'dan gelir. Serbest nokta = önceden test edilmemiş rota.
  const stopInfo = (s) => (s.custom ? s : regionById(s.id));
  const fmtMin = (m) => (m >= 60 ? Math.floor(m / 60) + " sa " + Math.round(m % 60) + " dk" : Math.round(m) + " dk");
  const hhmm = (iso) => iso.slice(11, 16);

  function renderPlanStops() {
    const list = document.getElementById("planStops");
    list.replaceChildren(
      ...evaPlan.stops.map((s, i) => {
        const dwell = el("input", { type: "number", min: "0", max: "240", step: "5", value: String(s.dwellMin), "aria-label": "Kalma süresi (dk)" });
        dwell.addEventListener("change", () => {
          s.dwellMin = Math.max(0, Number(dwell.value) || 0);
          replanIfActive();
        });
        const up = el("button", { type: "button", class: "icon", title: "Yukarı taşı" }, "↑");
        up.disabled = i === 0;
        up.addEventListener("click", () => {
          evaPlan.stops.splice(i - 1, 0, evaPlan.stops.splice(i, 1)[0]);
          renderPlanStops();
          replanIfActive();
        });
        const del = el("button", { type: "button", class: "icon", title: "Duraktan çıkar" }, "×");
        del.addEventListener("click", () => {
          evaPlan.stops.splice(i, 1);
          renderPlanStops();
          replanIfActive();
        });
        return el("li", s.custom ? { class: "custom", title: "Serbest nokta: test edilmemiş rota" } : null,
          el("span", { class: "pname" }, (s.custom ? "⚠ " : "") + shortName(stopInfo(s))), dwell, el("span", { class: "punit" }, "dk"), up, del);
      })
    );
    if (!evaPlan.stops.length) list.append(el("li", { class: "muted small empty" }, "Durak yok: aşağıdan ya da nokta kartından ekle."));
    // Seçim kutusu: henüz planda olmayan noktalar (üs hariç; plan zaten üste döner)
    const sel = document.getElementById("planAdd");
    sel.replaceChildren(el("option", { value: "" }, "Nokta seç…"),
      ...regions.filter((r) => canBeStop(r) && !evaPlan.stops.some((s) => s.id === r.id))
        .map((r) => el("option", { value: r.id }, shortName(r))));
  }

  function addPlanStop(id) {
    if (!canBeStop(regionById(id)) || evaPlan.stops.some((s) => s.id === id)) return;
    evaPlan.stops.push({ id, dwellMin: DEFAULT_DWELL_MIN });
    renderPlanStops();
    replanIfActive();
  }
  document.getElementById("planAdd").addEventListener("change", (e) => {
    addPlanStop(e.target.value);
    e.target.value = "";
  });

  function clearPlanDrawing() {
    evaPlan.entities.splice(0).forEach((e) => viewer.entities.remove(e));
  }

  function clearPlan() {
    clearPlanDrawing();
    evaPlan.result = null;
    document.getElementById("planSummary").replaceChildren();
    document.getElementById("planClearBtn").disabled = true;
    document.getElementById("walkBtn").disabled = true;
  }

  // Haritada işaret (nokta + etiket), arazinin önünde
  function planMarker(lon, lat, color, text, size) {
    return viewer.entities.add({
      position: groundPosition(lon, lat),
      point: {
        pixelSize: size || 11,
        color: Cesium.Color.fromCssColorString(color),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: text ? {
        text,
        font: "600 12px system-ui, sans-serif",
        fillColor: Cesium.Color.fromCssColorString(color),
        ...LABEL_BG,
        // Etiket noktanın altında: sağ/sol pin adlarına (Üs, Three Forks…) çakışmasın
        pixelOffset: new Cesium.Cartesian2(0, 10),
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      } : undefined,
    });
  }

  function drawPlan(p) {
    clearPlanDrawing();
    p.legs.forEach((leg) => {
      evaPlan.entities.push(viewer.entities.add({
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(leg.coords.flatMap((c) => [c[0], c[1]]), MARS),
          width: leg.isReturn ? 3 : 4,
          material: leg.isReturn
            ? new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.fromCssColorString(PLAN_COLORS.back), dashLength: 14 })
            : Cesium.Color.fromCssColorString(PLAN_COLORS.out),
          clampToGround: true,
        },
      }));
    });
    // Durak işaretleri (etiketsiz: adı pin yazıyor, sırası sol panelde)
    p.legs.filter((l) => !l.isReturn).forEach((leg) => {
      const end = leg.coords[leg.coords.length - 1];
      evaPlan.entities.push(planMarker(end[0], end[1], PLAN_COLORS.out, "", 9));
    });
    if (p.turnaround) evaPlan.entities.push(planMarker(p.turnaround.lon, p.turnaround.lat, PLAN_COLORS.turn, "Dönüş noktası · T+" + p.turnaround.t + " dk", 13));
    if (p.marginPoint) evaPlan.entities.push(planMarker(p.marginPoint.lon, p.marginPoint.lat, PLAN_COLORS.margin, "%25 pay sınırı · T+" + p.marginPoint.t + " dk", 11));
    const radio = p.goNoGo.find((c) => c.id === "radio");
    if (radio && radio.firstShadow) {
      const f = radio.firstShadow;
      evaPlan.entities.push(planMarker(f.lon, f.lat, PLAN_COLORS.radio, "Telsiz gölgesi · T+" + f.t + " dk", 9));
    }
  }

  // Kamerayı plan rotasına yaklaştır: bütün alan görünürken 5 km'lik rota çok küçük kalıyor
  function flyToPlan(p) {
    setAutoRotate(false);
    const pts = p.coords.map((c) => Cesium.Cartesian3.fromDegrees(c[0], c[1], 0, MARS)); // yükseklik 0: arazi göreli ve 3× abartılı (mutlak elev değil)
    const sphere = Cesium.BoundingSphere.fromPoints(pts);
    const range = Math.max(3000, sphere.radius * 4.2); // en az 3 km; yan paneller arasında rota tümüyle görünsün
    flyToFit(sphere, range, -50);
  }

  // Kamerayı bir alana yaklaştır. Telefonda (dikey) kart ekranın alt ~%60'ını kaplar:
  // - bakış noktası güneye kaydırılır, alan ekranın üst yarısında kalır (0,45 × uzaklık, 390×844'te denendi);
  // - dikey ekranda yatay görüş açısı dar, kenardaki etiketler kesilmesin diye 1,4× uzaklaşılır (göz kararı).
  function flyToFit(sphere, range, pitchDeg) {
    if (portrait()) {
      range *= 1.4;
      const c = Cesium.Cartographic.fromCartesian(sphere.center, MARS);
      const shiftM = range * 0.45;
      sphere = new Cesium.BoundingSphere(
        Cesium.Cartesian3.fromRadians(c.longitude, c.latitude - shiftM / 3389500, 0, MARS), sphere.radius); // m → rad (Mars yarıçapı)
    }
    viewer.camera.flyToBoundingSphere(sphere, {
      offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(portrait() ? -70 : pitchDeg), range),
      duration: 2,
    });
  }

  function runPlan(openCard) {
    const a = astronauts.find((x) => x.id === selectedAstroId);
    const box = document.getElementById("planSummary");
    if (!window.Eva || !zonesReady) {
      box.replaceChildren(el("p", { class: "muted small" }, "Planlayıcı hazır değil (eva.js ya da grid.json yüklenmedi)."));
      return;
    }
    if (!a) return;
    if (!evaPlan.stops.length) {
      clearPlan();
      box.replaceChildren(el("p", { class: "muted small" }, "Önce en az bir durak ekle."));
      return;
    }
    const stops = evaPlan.stops.map((s) => {
      const r = stopInfo(s);
      return { id: s.id, name: shortName(r), lon: r.lon, lat: r.lat, dwellMin: s.dwellMin };
    });
    const depart = document.getElementById("planDepart").value === "now" ? new Date() : Eva.nextWindow(new Date());
    // Profil formundaki değerler metin olabilir: sayıya çevir
    const astro = { ...a };
    ["o2_min", "o2_capacity_min", "heart_rate", "load_kg", "battery_pct", "water_pct"].forEach((k) => {
      if (astro[k] != null) astro[k] = Number(astro[k]);
    });
    let p;
    try {
      p = Eva.plan({ astronaut: astro, stops, departUTC: depart });
    } catch (err) {
      console.error(err);
      p = { ok: false, error: "Plan hesaplanamadı: " + err.message };
    }
    if (!p.ok) {
      clearPlan();
      box.replaceChildren(el("p", { class: "warn-line small" }, "⚠ " + p.error));
      return;
    }
    p.astronaut = a.name;
    p.astronautId = a.id;
    // Serbest nokta varsa Go/No-Go'nun başına DİKKAT satırı (plan yine yürünebilir; karar astronotun)
    const custom = evaPlan.stops.filter((s) => s.custom);
    p.untested = custom.length > 0;
    if (p.untested) {
      p.goNoGo.unshift({ id: "untested", label: "Test edilmemiş rota", status: "warn",
        detail: "Dikkat: daha önce test edilmemiş bir rotada yürümek istiyorsunuz (" + custom.map((s) => s.name).join(", ") +
          "). Güvenli duraklarımız: " + regions.filter(canBeStop).map(shortName).join(", ") + "." });
    }
    evaPlan.result = p;
    drawPlan(p);
    document.getElementById("planClearBtn").disabled = false;
    box.replaceChildren(planSummaryEl(p));
    if (openCard) {
      showDetail(planCard(p));
      flyToPlan(p);
    }
    else if (!detailPanel.hidden && detailBody.querySelector(".plan-card")) showDetail(planCard(p));
    window.dispatchEvent(new CustomEvent("marstrail:plan", { detail: p })); // G7 canlı yürüyüş dinleyecek
  }

  // Profil, seçili astronot, çıkış saati ya da duraklar değişince açık plan yeniden hesaplanır
  function replanIfActive() {
    if (walk.active) return; // yürüyüş sırasında plan sabit (canlı değerler yürüyüşü etkiler)
    if (evaPlan.result) runPlan(false);
  }

  // O₂ yetmiyorsa "−169 dk kalır" yerine "169 dk eksik"
  const o2LeftText = (t) => (t.o2LeftMin >= 0 ? t.o2LeftMin + " dk kalır (%" + t.o2LeftPct + ")" : -t.o2LeftMin + " dk EKSİK");

  // G7: plan kartından da canlı yürüyüş başlatılabilsin
  function startWalkButton() {
    const b = el("button", { type: "button", class: "primary walk-start" }, "▶ Yürüyüşü başlat (×60)");
    b.addEventListener("click", () => startWalk());
    return b;
  }

  function verdictEl(p) {
    return el("span", { class: "verdict " + (p.go ? "go" : "nogo") }, p.go ? "GO" : "NO-GO");
  }

  // Sol paneldeki kısa özet; tıklayınca plan kartı açılır
  function planSummaryEl(p) {
    const t = p.totals;
    const fails = p.goNoGo.filter((c) => c.status === "fail").length;
    const warns = p.goNoGo.filter((c) => c.status === "warn").length;
    const note = [fails ? fails + " NO-GO" : "", warns ? warns + " dikkat" : ""].filter(Boolean).join(", ") || "hepsi GO";
    const box = el("button", { type: "button", class: "plan-summary" },
      verdictEl(p),
      el("span", null,
        el("b", null, p.astronaut + " · " + fmtMin(t.minutes) + " · " + (t.distanceM / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " km"),
        el("br"),
        el("span", { class: "muted small" }, "Dönüşte O₂ " + o2LeftText(t) + " · " + note)
      )
    );
    box.addEventListener("click", () => showDetail(planCard(p)));
    return box;
  }

  // Radyasyon: yüzeyde doz eşdeğeri hızı 0,64 mSv/gün (Curiosity RAD, Gale; Hassler vd. 2014, Science 343).
  // EVA dozu = süre × 0,64/24 mSv/sa. Eşik: profildeki uyarıyla aynı 1 mSv (EVA başına varsayım).
  // Habitat içi kalkan ihmal; Jezero ile Gale benzer enlem/yükseklik kabulü.
  const RAD_MSV_PER_DAY = 0.64;
  const RAD_LIMIT_MSV = 1;
  function radiationText(p) {
    const a = astronauts.find((x) => x.id === p.astronautId);
    const eva = (p.totals.minutes / 60) * (RAD_MSV_PER_DAY / 24);
    const before = Number(a && a.radiation_msv) || 0;
    const total = before + eva;
    const f = (v) => v.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return "+" + f(eva) + " mSv bu EVA'da → toplam " + f(total) + " mSv" +
      (total > RAD_LIMIT_MSV ? " ⚠ eşik (" + RAD_LIMIT_MSV + " mSv) aşılıyor" : " (eşik " + RAD_LIMIT_MSV + " mSv)");
  }

  // eva.js kalan yüzdeyi doğrusal düşürüyor, uzun planda eksiye iniyor ("%-38"): kaynak yolda biter
  const pctLeft = (v) => (v < 0 ? "%0 (yolda biter)" : "%" + v);
  const fixNegPct = (txt) => String(txt).replace(/%-\d+(?:[.,]\d+)?/g, "%0 (yolda biter)");

  function planCard(p) {
    const t = p.totals;
    const first = p.timeline[0], last = p.timeline[p.timeline.length - 1];
    const parts = [
      el("span", { class: "chip", style: "--chip:" + PLAN_COLORS.out }, "EVA planı"),
      el("h3", null, p.astronaut + ": " + ["Üs", ...p.legs.filter((l) => !l.isReturn).map((l) => l.to), "Üs"].join(" → ")),
      el("div", { class: "verdict-row" }, verdictEl(p),
        el("span", { class: "small muted" }, p.go ? "Kırmızı madde yok; DİKKAT maddelerini oku." : "En az bir madde kırmızı: plan bu haliyle yapılmaz.")),
      startWalkButton(),
      kvList([
        ["Çıkış", first.lmst + " LMST · " + hhmm(first.utc) + " UTC"],
        ["Dönüş", last.lmst + " LMST · " + hhmm(last.utc) + " UTC"],
        ["Toplam süre", fmtMin(t.minutes) + " (yürüyüş " + fmtMin(t.walkMin) + ")"],
        ["Mesafe", (t.distanceM / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " km"],
        ["O₂", t.o2UsedMin + " dk harcanır, " + o2LeftText(t) + " (nabız ×" + t.multiplier.toFixed(2) + ")"],
        ["Batarya / su", "dönüşte " + pctLeft(t.batteryPct) + " / " + pctLeft(t.waterPct)],
        ["Radyasyon", radiationText(p)],
      ]),
    ];
    if (p.turnaround) {
      parts.push(el("p", { class: "warn-line" }, "⚠ Dönüş noktası: çıkıştan " + p.turnaround.t + " dk sonra. Bu noktayı geçersen O₂ üsse dönüşe yetmez (haritada kırmızı işaret)."));
    } else if (p.marginPoint) {
      parts.push(el("p", { class: "small", style: "color:var(--yellow)" }, "%25 pay sınırı: çıkıştan " + p.marginPoint.t + " dk sonra (haritada sarı işaret). Sonrasında dönülebilir ama pay kalmaz."));
    } else {
      parts.push(el("p", { class: "small muted" }, "Dönüş noktası yok: rotanın her yerinden %25 O₂ payıyla üsse dönülebiliyor."));
    }

    parts.push(el("h4", null, "Go / No-Go"));
    parts.push(el("ul", { class: "gonogo" }, p.goNoGo.map((c) =>
      el("li", { class: c.status },
        el("span", { class: "gstatus" }, STATUS_TEXT[c.status]),
        el("span", null, el("b", null, c.label), el("br"), el("span", { class: "muted small" }, fixNegPct(c.detail)))
      ))));

    parts.push(el("h4", null, "Zaman çizelgesi"));
    const EV = { depart: "Çıkış", arrive: "Varış", leave: "Ayrılış", return: "Üsse dönüş" };
    const cap = Number(p.timeline[0].o2Left) || 1;
    parts.push(el("ol", { class: "plan-timeline" }, p.timeline.map((e) => {
      const pct = Math.max(0, Math.min(100, (e.o2Left / cap) * 100));
      return el("li", { class: e.type },
        el("time", null, "T+" + e.t),
        el("span", null, el("b", null, EV[e.type] + " · " + e.name), el("br"),
          el("span", { class: "muted small" }, e.lmst + " LMST" + (e.dwellMin ? " · " + e.dwellMin + " dk çalışma" : ""))),
        // O₂ çubuğu: %25'in altı kırmızı (yeşil bölge payıyla aynı eşik)
        el("span", { class: "o2cell", title: "Kalan O₂" }, e.o2Left + " dk",
          el("i", { style: "width:" + pct.toFixed(0) + "%;background:" + (e.o2Left < cap * 0.25 ? "var(--red)" : "var(--green)") })));
    })));

    // Bacaklar: yorgunluk ve numune yükü görünsün (jüri formülü sorarsa)
    parts.push(el("h4", null, "Bacaklar"));
    parts.push(kvList(p.legs.map((l) => [
      l.from.replace(/ .*/, "") + " → " + l.to.replace(/ .*/, "") + (l.isReturn ? " (dönüş)" : ""),
      fmtMin(l.minutes) + " · " + (l.distanceM / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " km · yük " + l.loadKg + " kg · yorgunluk ×" + l.fatigue,
    ])));
    parts.push(el("p", { class: "muted small" },
      "Rota: Dijkstra, eğim ≥25° geçilmez (walkback.js). Süre: Tobler × 0,6 × (1 − yük/100) × yorgunluk (1 + 0,05·saat). " +
      "O₂ = süre × (1 + (nabız−90)/100). Durak başına 1 kg numune. Katsayılar varsayım (eva.js). " +
      "Radyasyon = süre × 0,64 mSv/gün (Curiosity RAD, Hassler vd. 2014)."));
    return el("div", { class: "card plan-card" }, parts);
  }

  document.getElementById("planBtn").addEventListener("click", () => runPlan(true));
  document.getElementById("planDepart").addEventListener("change", replanIfActive);
  document.getElementById("planClearBtn").addEventListener("click", () => {
    if (walk.active) return;
    clearPlan();
    if (detailBody.querySelector(".plan-card")) hideDetail();
  });
  window.addEventListener("marstrail:astronaut", replanIfActive);

  // =====================================================================
  // --- G7: Canlı yürüyüş ---
  // =====================================================================
  // Plan (eva.js) zaman ekseninde oynatılır: konum Eva.positionAt(plan, t), O₂ ise canlı nabızla akar:
  //   O₂(t + dt) = O₂(t) − dt × (1 + (nabız − 90)/100)       (PLAN.md §5, walkback.js ile aynı çarpan)
  // Konum planın hızında ilerler (nabız yürüme hızını değil tüketimi değiştirir). Bölgeler o anki konum,
  // kalan O₂ ve nabızla yeniden hesaplanır: nabız yükselince daha hızlı daralır.
  const WALK_TICK_MIN = 1;        // uyarı/telsiz kontrolü her 1 simülasyon dakikasında
  const WALK_ZONE_MIN = 5;        // bölgeler her 5 sim. dakikasında yeniden çizilir (~45 ms hesap; ×60'ta 5 sn'de bir)
  const WALK_ZONE_REAL_MS = 2000; // ama gerçek zamanda en fazla 2 sn'de bir (×900'de çizim yetişsin)
  const SAND_LOOKAHEAD_MIN = 3;   // "kum alanına yaklaşıyorsun": 3 sim. dk sonraki konum kumdaysa (~50–100 m)
  const TURN_WARN_MIN = 5;        // dönüş noktasından 5 dk önce uyar (PLAN §3.6)
  const walk = {
    active: false, paused: false, plan: null, astro: null, saved: null,
    t: 0, o2: 0, hr: 90, speed: 60, lastFrame: 0, nextTick: 0, nextZone: 0,
    pos: null, distM: 0, hrMax: 0, hrSum: 0, hrN: 0,
    zone: null, inSand: false, radioUp: true, flags: {}, alerts: [], notes: [], entities: [],
    returning: false, raf: 0,
  };

  const $ = (id) => document.getElementById(id);
  const fmtT = (t) => "T+" + Math.floor(t) + " dk";

  function walkLmst(t) {
    if (!window.MarsTime || !walk.plan) return "";
    const d = new Date(new Date(walk.plan.depart).getTime() + t * 60000);
    return MarsTime.at(d).lmst + " LMST";
  }

  // Uyarı: haritanın üstünde kısa süreli kutu + bitişte özet listesi
  function walkAlert(level, text) {
    walk.alerts.push({ t: Math.round(walk.t), level, text });
    const box = el("div", { class: "toast " + level }, el("b", null, fmtT(walk.t)), " ", text);
    $("walkToasts").prepend(box);
    setTimeout(() => box.classList.add("fade"), 6000);
    setTimeout(() => box.remove(), 6800);
  }

  function startWalk() {
    const p = evaPlan.result;
    const a = p && astronauts.find((x) => x.id === p.astronautId);
    if (!p || !a || walk.active) return;
    // Profil kaydedilmez: yürüyüş bitince astronotun formdaki değerleri geri gelir (demo tekrar oynatılabilsin)
    walk.saved = { position: { ...a.position }, o2_min: a.o2_min, heart_rate: a.heart_rate };
    Object.assign(walk, {
      active: true, paused: false, plan: p, astro: a, t: 0, o2: Number(a.o2_min), hr: Number(a.heart_rate) || 90,
      lastFrame: performance.now(), nextTick: 0, nextZone: WALK_ZONE_MIN, distM: 0, hrMax: 0, hrSum: 0, hrN: 0,
      zone: a.zone, inSand: false, radioUp: true, flags: {}, alerts: [], notes: [], returning: false,
    });
    walk.pos = Eva.positionAt(p, 0);
    clearWalkEntities();
    if (walk.walker) viewer.entities.remove(walk.walker);
    if (selectedAstroId !== a.id) selectAstronaut(a.id, false);
    drawZones(); // sabit astronot simgesi gizlenir, yerine hareketli simge
    walk.walker = viewer.entities.add({
      position: new Cesium.CallbackProperty(() => groundCart(walk.pos.lon, walk.pos.lat), false),
      point: {
        pixelSize: 14,
        color: Cesium.Color.fromCssColorString("#ff7a2f"),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: new Cesium.CallbackProperty(() => a.name + " · O₂ " + Math.max(0, Math.round(walk.o2)) + " dk", false),
        font: "700 13px system-ui, sans-serif",
        fillColor: Cesium.Color.WHITE,
        ...LABEL_BG,
        // Noktanın üstünde: sağ (pin adları) ve sol (Üs) dolu, yürüyüş başında "Üs" ile çakışıyordu
        pixelOffset: new Cesium.Cartesian2(0, -14),
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    $("walkHr").value = walk.hr;
    $("walkHrVal").textContent = walk.hr;
    $("walkSpeed").value = String(walk.speed);
    $("walkPause").textContent = "Duraklat";
    $("walkReturn").disabled = false;
    $("walkToasts").replaceChildren();
    $("walkHud").hidden = false;
    $("walkBtn").disabled = true;
    hideDetail();
    closeDrawer();
    flyToPlan(p);
    walkAlert("info", "Yürüyüş başladı: " + a.name + ", O₂ " + Math.round(walk.o2) + " dk" + (p.go ? "" : " · plan NO-GO!"));
    walk.raf = requestAnimationFrame(walkFrame);
  }

  function walkFrame(now) {
    if (!walk.active) return;
    const dtReal = Math.min(250, now - walk.lastFrame); // sekme arkadayken büyük sıçrama olmasın
    walk.lastFrame = now;
    if (!walk.paused) {
      const dt = (dtReal / 60000) * walk.speed; // ×60: 1 gerçek sn = 1 sim. dk
      const prev = walk.pos;
      walk.t += dt;
      walk.o2 -= dt * Walkback.o2Multiplier(walk.hr);
      walk.hrSum += walk.hr * dt;
      walk.hrN += dt;
      walk.hrMax = Math.max(walk.hrMax, walk.hr);
      walk.pos = Eva.positionAt(walk.plan, Math.min(walk.t, walk.plan.totals.minutes));
      walk.distM += Math.hypot((walk.pos.lon - prev.lon) * Math.cos((prev.lat * Math.PI) / 180), walk.pos.lat - prev.lat) * 59274.7; // derece → m
      if (walk.t >= walk.nextTick) {
        walk.nextTick = walk.t + WALK_TICK_MIN;
        walkChecks();
      }
      if (walk.t >= walk.nextZone && now - (walk.lastZoneReal || 0) >= WALK_ZONE_REAL_MS) {
        walk.nextZone = walk.t + WALK_ZONE_MIN;
        walk.lastZoneReal = now;
        walkZones();
      }
      if (walk.o2 <= 0) return endWalk("o2");
      if (walk.t >= walk.plan.totals.minutes) return endWalk(walk.returning ? "return" : "done");
    }
    renderWalkHud();
    walk.raf = requestAnimationFrame(walkFrame);
  }

  // Seçili astronotun bölgelerini o anki konum + kalan O₂ + nabızla yeniden çiz
  function walkZones() {
    const a = walk.astro;
    a.position = { lon: walk.pos.lon, lat: walk.pos.lat };
    a.o2_min = Math.max(0, Math.round(walk.o2));
    a.heart_rate = walk.hr;
    try {
      a._z = Walkback.zones(a.position, Math.max(1, walk.o2), walk.hr, currentLoad());
      a.zone = a._z.here;
    } catch (err) {
      console.error(err);
    }
    renderAstronauts();
    if (selectedAstroId === a.id) drawZones();
  }

  const currentLoad = () => {
    const leg = walk.plan.legs[walk.pos.leg] || walk.plan.legs[0];
    return leg.loadKg;
  };

  // Uyarılar: kum, dönüş noktası, bölge değişimi, telsiz, durak varış/ayrılış
  function walkChecks() {
    const p = walk.plan, pos = walk.pos, f = walk.flags;
    const G = Walkback.grid;
    // 1) Kum
    const i = Walkback.cellOf(pos);
    const sandNow = i >= 0 && G.sand[i] === 1;
    const ahead = Eva.positionAt(p, Math.min(walk.t + SAND_LOOKAHEAD_MIN, p.totals.minutes));
    const ia = Walkback.cellOf(ahead);
    if (!sandNow && ia >= 0 && G.sand[ia] === 1 && !f.sandAhead) {
      f.sandAhead = true;
      walkAlert("warn", "Kum alanına yaklaşıyorsun: yavaşla, adımlarını kontrol et (Opportunity/Spirit).");
    }
    if (sandNow && !walk.inSand) walkAlert("warn", "Kum alanındasın. Saplanma riski: yükü azalt, yavaş geç.");
    if (!sandNow && walk.inSand) f.sandAhead = false;
    walk.inSand = sandNow;

    // 2) Dönüş noktası (plandan) + canlı dönüş payı
    if (p.turnaround && !walk.returning) {
      if (!f.turnWarn && walk.t >= p.turnaround.t - TURN_WARN_MIN) {
        f.turnWarn = true;
        walkAlert("warn", "Dönüş noktasına " + TURN_WARN_MIN + " dk.");
      }
      if (!f.turn && walk.t >= p.turnaround.t) {
        f.turn = true;
        walkAlert("danger", "DÖNÜŞ NOKTASI! Şimdi dönmezsen O₂ üsse yetmez. → Üsse dön");
      }
    }
    // 3) Bölge: o anki konumdan üsse dönüş, kalan O₂'ye göre (walkback "here" kuralıyla aynı eşikler)
    const home = homeMinutes();
    const avail = walk.o2 / Walkback.o2Multiplier(walk.hr);
    const zone = home <= avail / Walkback.GREEN_MARGIN ? "green" : home <= avail ? "yellow" : "red";
    if (zone !== walk.zone) {
      if (zone === "yellow") walkAlert("warn", "Sarı bölgeye girdin: dönebilirsin ama %25 payın kalmadı.");
      if (zone === "red") walkAlert("danger", "Kırmızı bölgeye giriyorsun: O₂ dönüşe yetmiyor!");
      if (zone === "green" && walk.zone) walkAlert("ok", "Yeniden yeşil bölgedesin.");
      walk.zone = zone;
      walk.astro.zone = zone;
      renderAstronauts();
    }
    // 4) Telsiz: habitat anteniyle görüş hattı (eva.js); kopunca üst bar kırmızı
    const up = Eva.lineOfSight(Walkback.BASE, pos);
    if (up !== walk.radioUp) {
      walkAlert(up ? "ok" : "warn", up ? "Telsiz bağlantısı geri geldi." : "Telsiz gölgesi: habitatla bağlantı yok. Arkadaşın röle olmalı.");
      walk.radioUp = up;
      setLink(up);
    }
    // 5) Duraklar (zaman çizelgesinden)
    for (const e of p.timeline) {
      const key = e.type + ":" + e.t + ":" + e.name;
      if (f[key] || walk.t < e.t || e.type === "depart" || e.type === "return") continue;
      f[key] = true;
      if (e.type === "arrive") walkAlert("info", e.name + " durağına varıldı. Not ya da fotoğraf pini bırakabilirsin.");
      if (e.type === "leave") walkAlert("info", e.name + " durağından ayrılış (" + e.dwellMin + " dk çalışıldı).");
    }
    // 6) O₂ %25
    const cap = Number(walk.astro.o2_capacity_min) || walk.saved.o2_min;
    if (!f.o2low && walk.o2 < cap * 0.25) {
      f.o2low = true;
      walkAlert("danger", "O₂ kapasitenin %25'inin altında.");
    }
  }

  // Bulunduğun yerden üsse dönüş süresi (dk, nabız çarpanı hariç), o anki yük ve yorgunlukla
  function homeMinutes() {
    const fat = 1 + Eva.ASSUMPTIONS.FATIGUE_PER_HOUR * (walk.t / 60);
    return Walkback.timeHome(walk.pos, { loadKg: currentLoad() }) * fat;
  }

  function renderWalkHud() {
    const p = walk.plan, pos = walk.pos;
    const mult = Walkback.o2Multiplier(walk.hr);
    const homeO2 = homeMinutes() * mult;
    const reserve = walk.o2 - homeO2;
    const cap = Number(walk.astro.o2_capacity_min) || walk.saved.o2_min;
    $("walkTime").textContent = fmtT(walk.t) + " · " + walkLmst(walk.t);
    $("walkPhase").textContent =
      walk.returning ? "Üsse dönüyor (erken dönüş)" :
      pos.phase === "walk" ? "Yürüyor → " + pos.to :
      pos.phase === "dwell" ? "Durakta: " + pos.at : "Üste";
    $("walkO2").textContent = Math.max(0, Math.round(walk.o2)) + " dk";
    const bar = $("walkO2Bar");
    bar.style.width = Math.max(0, Math.min(100, (walk.o2 / cap) * 100)) + "%";
    bar.style.background = walk.zone === "red" ? "var(--red)" : walk.zone === "yellow" ? "var(--yellow)" : "var(--green)";
    $("walkHome").textContent = "Üsse dönüş " + Math.round(homeO2) + " dk O₂ · pay " + (reserve >= 0 ? Math.round(reserve) + " dk" : "YOK (" + Math.round(-reserve) + " dk eksik)");
    $("walkHome").className = "small " + (reserve < 0 ? "bad" : reserve < walk.o2 * 0.25 ? "mid" : "muted");
    $("walkMult").textContent = "×" + mult.toFixed(2);
    $("walkZone").replaceChildren(zoneBadge(walk.zone));
  }

  // Erken dönüş: bulunduğun yerden üsse yeni plan (durak yok), kalan O₂ ile; zaman ekseni devam eder
  function returnNow() {
    if (!walk.active || walk.returning) return;
    const a = walk.astro;
    const r = Eva.plan({
      astronaut: { ...a, o2_min: walk.o2, heart_rate: walk.hr, load_kg: currentLoad() },
      start: { lon: walk.pos.lon, lat: walk.pos.lat }, startName: "Bulunduğun yer", stops: [],
      departUTC: new Date(new Date(walk.plan.depart).getTime() + walk.t * 60000),
    });
    if (!r.ok) {
      walkAlert("danger", "Dönüş rotası bulunamadı: " + r.error);
      return;
    }
    // Yeni planı mevcut zamana kaydır: positionAt(t) = r'de (t − t0)
    const t0 = walk.t;
    const shifted = {
      ...r,
      legs: r.legs.map((l) => ({ ...l, startMin: l.startMin + t0, endMin: l.endMin + t0, minutesAt: l.minutesAt.map((x) => x + t0) })),
      timeline: r.timeline.map((e) => ({ ...e, t: e.t + t0 })),
      totals: { ...r.totals, minutes: r.totals.minutes + t0 },
      turnaround: null, depart: walk.plan.depart,
    };
    walk.plan = shifted;
    walk.returning = true;
    walk.flags = { ...walk.flags, turn: true, turnWarn: true };
    $("walkReturn").disabled = true;
    // Dönüş rotası (sarı kesikli)
    walk.entities.push(viewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArray(r.coords.flatMap((c) => [c[0], c[1]]), MARS),
        width: 4,
        material: new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.fromCssColorString("#f1c40f"), dashLength: 10 }),
        clampToGround: true,
      },
    }));
    walkAlert(r.totals.o2LeftMin >= 0 ? "ok" : "danger",
      "Üsse dönüş başladı: " + fmtMin(r.totals.minutes) + ", varışta O₂ " + (r.totals.o2LeftMin >= 0 ? r.totals.o2LeftMin + " dk" : "YETMİYOR (" + -r.totals.o2LeftMin + " dk eksik)"));
  }

  // Not / fotoğraf pini: o anki konuma
  function dropNote() {
    if (!walk.active) return;
    const input = $("walkNote");
    const text = input.value.trim() || (walk.pos.phase === "dwell" ? walk.pos.at + " – numune" : "Not");
    input.value = "";
    const n = { t: Math.round(walk.t), text, lon: walk.pos.lon, lat: walk.pos.lat };
    walk.notes.push(n);
    walk.entities.push(planMarker(n.lon, n.lat, "#ffffff", "📍 " + fmtT(n.t) + " " + text, 8));
    walkAlert("info", "Pin bırakıldı: " + text);
  }

  function endWalk(reason) {
    cancelAnimationFrame(walk.raf);
    walk.active = false;
    $("walkHud").hidden = true;
    $("walkBtn").disabled = !evaPlan.result;
    setLink(true);
    const a = walk.astro;
    const end = { o2: Math.round(walk.o2), t: Math.round(walk.t) };
    // Astronotun formdaki değerleri geri gelir (simülasyon; profil değişmez)
    Object.assign(a, walk.saved);
    computeZones();
    // Hareketli simgeyi kaldır; pinler ve dönüş rotası kalır
    if (walk.walker) viewer.entities.remove(walk.walker);
    walk.walker = null;
    showDetail(walkSummary(reason, end));
  }

  function walkSummary(reason, end) {
    const p = evaPlan.result;
    const title = { done: "Yürüyüş tamamlandı", return: "Erken dönüşle üste varıldı", o2: "O₂ BİTTİ", stop: "Yürüyüş durduruldu", lost: "Telsiz koptu" }[reason];
    const ok = reason === "done" || reason === "return";
    const avgHr = walk.hrN ? Math.round(walk.hrSum / walk.hrN) : walk.hr;
    const parts = [
      el("span", { class: "chip", style: "--chip:#ff7a2f" }, "Yürüyüş özeti"),
      el("h3", null, walk.astro.name + ": " + title),
      el("div", { class: "verdict-row" },
        el("span", { class: "verdict " + (ok ? "go" : "nogo") }, ok ? "GÜVENDE" : reason === "o2" ? "ACİL" : "DURDU"),
        el("span", { class: "small muted" }, ok ? "Astronot üste döndü." : reason === "o2" ? "Astronot üsse ulaşamadı: Hayatta Kal moduna geç." : "Simülasyon elle durduruldu.")),
      kvList([
        ["Süre", fmtMin(end.t) + (p ? " (plan " + fmtMin(p.totals.minutes) + ")" : "")],
        ["Yürünen mesafe", (walk.distM / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " km"],
        ["O₂", walk.saved.o2_min + " → " + Math.max(0, end.o2) + " dk" + (p && ok ? " (plan " + (p.totals.o2LeftMin < 0 ? Math.abs(p.totals.o2LeftMin) + " dk EKSİK" : p.totals.o2LeftMin + " dk") + ")" : "")],
        ["Nabız", "ort. " + avgHr + ", en yüksek " + walk.hrMax + " atım/dk"],
        ["Uyarı sayısı", walk.alerts.filter((x) => x.level === "warn" || x.level === "danger").length],
      ]),
    ];
    if (walk.notes.length) {
      parts.push(el("h4", null, "Pinler"));
      parts.push(el("ol", { class: "timeline" }, walk.notes.map((n) => el("li", null, el("time", null, fmtT(n.t)), el("span", null, n.text)))));
    }
    parts.push(el("h4", null, "Olay kaydı"));
    parts.push(el("ul", { class: "walk-log" }, walk.alerts.map((x) => el("li", { class: x.level }, el("time", null, fmtT(x.t)), el("span", null, x.text)))));
    const again = el("button", { type: "button", class: "primary" }, "Tekrar oynat");
    if (reason === "o2") {
      const sos = el("button", { type: "button", class: "danger" }, "📡 Hayatta Kal");
      sos.addEventListener("click", radioLost);
      parts.push(el("div", { class: "controls card-actions" }, sos));
    }
    again.addEventListener("click", () => { clearWalkEntities(); startWalk(); });
    const clear = el("button", { type: "button" }, "Pinleri temizle");
    clear.addEventListener("click", clearWalkEntities);
    parts.push(el("div", { class: "controls card-actions" }, again, clear));
    parts.push(el("p", { class: "muted small" }, "O₂ = Σ dt × (1 + (nabız − 90)/100), canlı nabızla. Konum plan hızında (eva.js positionAt). Simülasyon: profil kaydedilmez."));
    return el("div", { class: "card" }, parts);
  }

  function clearWalkEntities() {
    walk.entities.splice(0).forEach((e) => viewer.entities.remove(e));
  }

  $("walkBtn").addEventListener("click", startWalk);
  $("walkPause").addEventListener("click", () => {
    walk.paused = !walk.paused;
    $("walkPause").textContent = walk.paused ? "Devam" : "Duraklat";
    walk.lastFrame = performance.now();
  });
  $("walkReturn").addEventListener("click", returnNow);
  $("walkStop").addEventListener("click", () => walk.active && endWalk("stop"));
  $("walkNoteBtn").addEventListener("click", dropNote);
  $("walkNote").addEventListener("keydown", (e) => { if (e.key === "Enter") dropNote(); });
  $("walkSpeed").addEventListener("change", (e) => { walk.speed = Number(e.target.value); });
  $("walkHr").addEventListener("input", (e) => {
    walk.hr = Number(e.target.value);
    $("walkHrVal").textContent = walk.hr;
    $("walkHrVal").className = walk.hr >= 150 ? "bad" : "";
    walk.nextZone = Math.min(walk.nextZone, walk.t + 1); // nabız değişince bölgeler 1 sim. dk içinde güncellensin
  });
  window.addEventListener("marstrail:plan", () => { $("walkBtn").disabled = walk.active || !evaPlan.result; });

  // =====================================================================
  // --- G8: Hayatta Kal (telsiz koptu) ---
  // =====================================================================
  // Hesap Elif'in web/rescue.js'inde (E13): olasılıklı arama alanı, İHA zikzak rotası, Ali'nin kurtarma rotası.
  // Burada: tetikleme (yürüyüşten ya da demo), haritaya çizim, acil durum kartı ve arama animasyonu.
  const RESCUE_DEMO = { tLoss: 60, hr: 150, elapsed: 20 }; // E13 test senaryosu: deltaya yürürken kopma, panik (Apollo 14 nabzı)
  const DRONE_SPEED_MS = 10;      // rescue.js DRONE.speedMs ile aynı (animasyon konumu için)
  const DISPATCH_MIN = 10;        // rescue.js: Ali'nin giyinip çıkması (dk); İHA hemen kalkar (varsayım)
  const rescue = {
    active: false, input: null, result: null, elapsed: 20, entities: [], layer: null, chart: null,
    // ×180: 139 dk'lık demo kurtarma ~46 sn'de biter (×60'ta ~2,5 dk sürüyordu; 5 dk'lık sunuma sığmıyordu).
    // İHA taraması (~24 dk) ~8 sn: %50/%90 uyarıları hâlâ okunacak kadar ayrık.
    anim: { on: false, t: 0, speed: 180, last: 0, raf: 0, flags: {} },
    lostName: "", rescuerName: "",
  };

  function showToast(level, label, text) {
    const box = el("div", { class: "toast " + level }, el("b", null, label), " ", text);
    $("walkToasts").prepend(box);
    setTimeout(() => box.classList.add("fade"), 6000);
    setTimeout(() => box.remove(), 6800);
  }

  // Tetikleme. Yürüyüş sürüyorsa son konum/O₂/nabız oradan; yoksa plan (ya da demo planı) üstünde T+60
  function radioLost() {
    if (rescue.active) return;
    let lostAstro, last, lost, route, label;
    if (walk.active) {
      lostAstro = walk.astro;
      last = { lon: walk.pos.lon, lat: walk.pos.lat };
      lost = { name: lostAstro.name, o2LeftMin: walk.o2, heart_rate: walk.hr, load_kg: currentLoad() };
      route = walk.plan.coords;
      label = "Yürüyüşte " + fmtT(walk.t);
      endWalk("lost");
    } else {
      if (!evaPlan.result) runPlan(false);
      const p = evaPlan.result;
      if (!p) return;
      lostAstro = astronauts.find((x) => x.id === p.astronautId);
      const tLoss = Math.min(RESCUE_DEMO.tLoss, p.totals.minutes);
      const pos = Eva.positionAt(p, tLoss);
      last = { lon: pos.lon, lat: pos.lat };
      lost = { name: lostAstro.name, o2LeftMin: pos.o2Left, heart_rate: RESCUE_DEMO.hr, load_kg: Number(lostAstro.load_kg) };
      route = p.coords;
      label = "Demo: plan " + fmtT(tLoss) + ", nabız " + RESCUE_DEMO.hr;
    }
    // Kurtarıcı: kaybolan dışındaki ekipten O₂'si en yüksek olan (eşitlikte listede önce gelen; 2 kişide hep diğeri)
    const rescuer = astronauts.filter((x) => x.id !== lostAstro.id)
      .reduce((best, x) => (!best || Number(x.o2_min) > Number(best.o2_min) ? x : best), null);
    if (!rescuer) { showToast("warn", "Hayatta Kal", "Kurtarmaya gidecek ikinci bir astronot yok."); return; }
    const r = { ...rescuer };
    ["o2_min", "heart_rate", "load_kg"].forEach((k) => (r[k] = Number(r[k])));
    rescue.input = { last, lost, route, rescuer: r, label };
    rescue.lostName = lostAstro.name;
    rescue.rescuerName = rescuer.name;
    rescue.elapsed = RESCUE_DEMO.elapsed;
    rescue.active = true;
    rescue.anim.on = false;
    setLink(false);
    document.body.classList.add("emergency");
    clearZoneDrawing(); // ısı haritası okunsun diye O₂ bölgeleri acil durumda gizli
    setPlanLabels(false); // plan etiketleri (telsiz gölgesi, dönüş noktası) "Son konum" ile çakışmasın
    computeRescue();
    showToast("danger", "ACİL", rescue.lostName + " ile telsiz bağlantısı koptu. Arama başlatıldı.");
    // Kamerayı son konum + üs + Ali'nin rotasına yaklaştır
    const pts = [last, Walkback.BASE].map((q) => Cesium.Cartesian3.fromDegrees(q.lon, q.lat, 0, MARS));
    const sphere = Cesium.BoundingSphere.fromPoints(pts);
    sphere.radius = Math.max(sphere.radius, 1500);
    flyToFit(sphere, sphere.radius * 4.5, -55); // telefonda arama alanı kartın üstünde kalsın
  }

  function computeRescue() {
    const i = rescue.input;
    try {
      rescue.result = Rescue.respond({
        last: i.last, elapsedMin: rescue.elapsed, lost: i.lost, rescuer: i.rescuer, route: i.route,
      });
    } catch (err) {
      console.error(err);
      showToast("danger", "Hata", "Arama alanı hesaplanamadı: " + err.message);
      return;
    }
    drawRescue();
    showDetail(rescueCard());
  }

  function clearRescueDrawing() {
    if (rescue.layer) viewer.imageryLayers.remove(rescue.layer, true);
    rescue.layer = null;
    rescue.entities.splice(0).forEach((e) => viewer.entities.remove(e));
  }

  function rescueLine(coords, color, width, dashed) {
    return viewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArray(coords.flatMap((c) => [c[0], c[1]]), MARS),
        width,
        material: dashed
          ? new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.fromCssColorString(color), dashLength: 12 })
          : Cesium.Color.fromCssColorString(color),
        clampToGround: true,
      },
    });
  }

  function drawRescue() {
    const { area, drone, buddy } = rescue.result;
    const b = Walkback.grid.b;
    const old = rescue.layer, oldEnt = rescue.entities.splice(0);
    rescue.layer = viewer.imageryLayers.addImageryProvider(new Cesium.SingleTileImageryProvider({
      url: area.canvas(0.75).toDataURL(),
      rectangle: Cesium.Rectangle.fromDegrees(b.west, b.south, b.east, b.north),
      tileWidth: Walkback.grid.w, tileHeight: Walkback.grid.h,
    }));
    // Eski çizimi yenisi yüklenince kaldır (kaydırıcıyla sürüklerken titremesin)
    setTimeout(() => {
      if (old) viewer.imageryLayers.remove(old, true);
      oldEnt.forEach((e) => viewer.entities.remove(e));
    }, ZONE_SWAP_MS);
    area.outlines.p90.forEach((l) => rescue.entities.push(rescueLine(l, "#ff9800", 2)));
    area.outlines.p50.forEach((l) => rescue.entities.push(rescueLine(l, "#ff1744", 3)));
    if (drone) rescue.entities.push(rescueLine(drone.waypoints, "#e0e0ff", 1.5));
    if (buddy && buddy.ok) {
      rescue.entities.push(rescueLine(buddy.to, "#00e5ff", 4));
      rescue.entities.push(rescueLine(buddy.back, "#00e5ff", 3, true));
    }
    rescue.entities.push(planMarker(rescue.input.last.lon, rescue.input.last.lat, "#ff1744", "Son konum · " + rescue.lostName, 13));
    // Hareketli İHA ve Ali (animasyonda konumları değişir)
    rescue.droneEnt = viewer.entities.add({
      position: new Cesium.CallbackProperty(() => {
        const q = rescueDronePos();
        return groundCart(q[0], q[1]);
      }, false),
      point: { pixelSize: 10, color: Cesium.Color.WHITE, outlineColor: Cesium.Color.fromCssColorString("#5dade2"), outlineWidth: 3,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
      // İHA etiketi noktanın üstünde, Ali'ninki altında: ikisi de üsten çıkıyor, yan yana olunca çakışıyordu
      label: { text: "İHA", font: "700 12px system-ui, sans-serif", fillColor: Cesium.Color.WHITE, ...LABEL_BG, pixelOffset: new Cesium.Cartesian2(0, -12),
               horizontalOrigin: Cesium.HorizontalOrigin.CENTER, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
    });
    rescue.buddyEnt = viewer.entities.add({
      position: new Cesium.CallbackProperty(() => {
        const q = rescueBuddyPos();
        return groundCart(q[0], q[1]);
      }, false),
      point: { pixelSize: 12, color: Cesium.Color.fromCssColorString("#00e5ff"), outlineColor: Cesium.Color.WHITE, outlineWidth: 2,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
      label: { text: rescue.rescuerName, font: "700 13px system-ui, sans-serif", fillColor: Cesium.Color.fromCssColorString("#00e5ff"),
               ...LABEL_BG,
               pixelOffset: new Cesium.Cartesian2(0, 12), horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
               verticalOrigin: Cesium.VerticalOrigin.TOP,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
    });
    rescue.entities.push(rescue.droneEnt, rescue.buddyEnt);
  }

  // Bir çizgi boyunca, uzunluğun f (0–1) kesrindeki nokta (düz yaklaşım: kısa mesafede yeterli)
  function alongLine(coords, f) {
    if (!coords || !coords.length) return [Walkback.BASE.lon, Walkback.BASE.lat];
    const k = Math.cos((coords[0][1] * Math.PI) / 180);
    const seg = [];
    let total = 0;
    for (let i = 1; i < coords.length; i++) {
      const d = Math.hypot((coords[i][0] - coords[i - 1][0]) * k, coords[i][1] - coords[i - 1][1]);
      seg.push(d);
      total += d;
    }
    let want = Math.max(0, Math.min(1, f)) * total;
    for (let i = 0; i < seg.length; i++) {
      if (want <= seg[i] || i === seg.length - 1) {
        const g = seg[i] ? Math.min(1, want / seg[i]) : 0;
        return [coords[i][0] + (coords[i + 1][0] - coords[i][0]) * g, coords[i][1] + (coords[i + 1][1] - coords[i][1]) * g];
      }
      want -= seg[i];
    }
    return coords[coords.length - 1];
  }

  // İHA: 10 m/s sabit hızla zikzak (rescue.js droneRoute ile aynı varsayım); toplam süre drone.minutes
  function rescueDronePos() {
    const d = rescue.result && rescue.result.drone;
    if (!d) return [Walkback.BASE.lon, Walkback.BASE.lat];
    return alongLine(d.waypoints, rescue.anim.t / d.minutes);
  }

  // Ali: 10 dk giyinme, sonra gidiş rotası (toMin), sonra birlikte dönüş (backMin); rota boyunca eşit hız varsayımı
  function rescueBuddyPos() {
    const b = rescue.result && rescue.result.buddy;
    if (!b || !b.ok) return [Walkback.BASE.lon, Walkback.BASE.lat];
    const t = rescue.anim.t - DISPATCH_MIN;
    if (t <= 0) return b.to[0];
    if (t <= b.toMin) return alongLine(b.to, t / b.toMin);
    return alongLine(b.back, (t - b.toMin) / b.backMin);
  }

  // Kaybolan astronotun O₂'si: kopma anındaki değer − (fark edilene kadar geçen + arama süresi) × çarpan
  const rescueLostO2 = () => {
    const i = rescue.input;
    return i.lost.o2LeftMin - (rescue.elapsed + rescue.anim.t) * Walkback.o2Multiplier(i.lost.heart_rate);
  };

  // İHA kapsama eğrisinden (rescue.js) o andaki taranan olasılık
  function rescueCoverage(tMin) {
    const c = rescue.result.drone && rescue.result.drone.coverage;
    if (!c || !c.length) return 0;
    let p = 0;
    for (const q of c) if (q.t <= tMin) p = q.p;
    return p;
  }

  // rescue.js artık adları profilden alıyor (rescuer.name, lost.name; E13 düzeltmesi). Eski Ali/Ayşe takası
  // kaldırıldı: doğru adlı mesajı yeniden takas etmek, Ali kaybolunca adları ters çevirirdi.
  function rescueNames(msg) {
    return String(msg);
  }

  // İHA + arkadaş birlikte: rescue.js arkadaşın varışını "son bilinen konum biliniyor" kabulüyle hesaplıyor
  // (geçen + 10 dk hazırlık + gidiş). Geç fark edilince astronot alan içinde herhangi bir yerde olabilir:
  // önce İHA bulmalı. Buluşma = max(İHA'nın %90 olasılıkla bulduğu an, arkadaşın vardığı an), kopmadan itibaren.
  //   Kayıp O₂ (buluşmada) = kopmadaki O₂ − buluşma × çarpan; üste = − dönüş × çarpan (+60 dk yedek tüp).
  // %90: olasılığın %90'ı taranınca bulunmuş kabul (muhafazakâr; %50'de bulma şansı da var).
  // 120 dk geç fark etmede alan 42 km², İHA %90'ı 629 dk'da tarıyor; eski karar yine "KURTARILABİLİR" diyordu.
  const SPARE_TANK_MIN = 60; // rescue.js SPARE_O2_MIN ile aynı
  function rescueTimeline() {
    const { drone, buddy } = rescue.result;
    const i = rescue.input;
    if (!buddy || !buddy.ok) return null;
    const mL = Walkback.o2Multiplier(i.lost.heart_rate);
    const foundT = rescue.elapsed + (drone && drone.t90 != null ? drone.t90 : 0);
    const buddyT = buddy.arriveAfterMin;
    const meetT = Math.max(foundT, buddyT);
    const atMeet = i.lost.o2LeftMin - meetT * mL;
    const atBaseRaw = atMeet - buddy.backMin * mL;
    const spare = atBaseRaw < 0;
    const atBase = atBaseRaw + (spare ? SPARE_TANK_MIN : 0);
    const survivable = buddy.status !== "red" && atMeet > 0 && atBase >= 0;
    return { foundT, buddyT, meetT, atMeet, atBase, spare, survivable, droneLimits: foundT > buddyT };
  }

  function rescueCard() {
    const { area, drone, buddy } = rescue.result;
    const i = rescue.input;
    const tl = rescueTimeline();
    const ok = tl ? tl.survivable : false;
    const fmt1 = (v) => (v == null ? "–" : v.toLocaleString("tr-TR", { maximumFractionDigits: 1 }));
    const slider = el("input", { type: "range", min: "0", max: "120", step: "5", value: String(rescue.elapsed), "aria-label": "Fark edilene kadar geçen süre" });
    const sliderVal = el("b", null, rescue.elapsed + " dk");
    slider.addEventListener("input", () => (sliderVal.textContent = slider.value + " dk"));
    slider.addEventListener("change", () => {
      rescue.elapsed = Number(slider.value);
      stopRescueAnim();
      computeRescue();
    });
    const play = el("button", { type: "button", class: "primary", id: "rescuePlay" }, rescue.anim.on ? "Duraklat" : "▶ Aramayı oynat");
    play.addEventListener("click", toggleRescueAnim);
    const close = el("button", { type: "button" }, "Acil durumu kapat");
    close.addEventListener("click", closeRescue);
    const canvas = el("canvas", { "aria-label": "İHA kapsama eğrisi" });

    const parts = [
      el("span", { class: "chip", style: "--chip:#ff1744" }, "Hayatta Kal"),
      el("h3", null, "ACİL: " + rescue.lostName + " ile telsiz koptu"),
      el("div", { class: "verdict-row" },
        el("span", { class: "verdict " + (ok ? "go" : "nogo") }, ok ? "KURTARILABİLİR" : "MÜMKÜN DEĞİL"),
        el("span", { class: "small muted" }, ok ? rescue.rescuerName + " yeşil/sarı bölgede kalarak ulaşabiliyor." : "O₂ yetmiyor ya da " + rescue.rescuerName + " dönemez: daha erken fark etmek şart.")),
      el("label", { class: "wh-row rescue-slider" }, el("span", { class: "rs-label" }, "Geç fark etme"), slider, sliderVal),
      el("div", { class: "rescue-live" },
        el("span", null, el("small", null, "Arama süresi"), el("b", { id: "rsT" }, "T+0 dk")),
        el("span", null, el("small", null, rescue.lostName + " O₂"), el("b", { id: "rsO2" }, Math.round(rescueLostO2()) + " dk")),
        el("span", null, el("small", null, "İHA taradı"), el("b", { id: "rsCov" }, "%0"))),
      el("div", { class: "controls card-actions" }, play, close),
      el("h4", null, "Arama alanı"),
      kvList([
        ["Son konum", i.label],
        ["Kopma anında", "O₂ " + Math.round(i.lost.o2LeftMin) + " dk, nabız " + i.lost.heart_rate + " (×" + area.multiplier.toFixed(2) + ")"],
        ["Yürüyebileceği süre", Math.round(area.budgetMin) + " dk (O₂ sınırı " + Math.round(area.o2BudgetMin) + " dk)"],
        ["Ulaşılabilir alan", fmt1(area.areaKm2) + " km²"],
        ["En olası %50 / %90", fmt1(area.area50Km2) + " / " + fmt1(area.area90Km2) + " km² (kırmızı / turuncu çizgi)"],
      ]),
    ];
    if (drone) {
      parts.push(el("h4", null, "İHA zikzak taraması"));
      parts.push(kvList([
        ["Şerit", drone.swathM + " m geniş, " + drone.spacingM + " m aralık, " + drone.lanes + " şerit"],
        ["Rota", fmt1(drone.lengthM / 1000) + " km, " + fmt1(drone.minutes) + " dk (" + drone.sorties + " batarya)"],
        ["Olasılığın %50'si", fmt1(drone.t50) + " dk'da taranır"],
        ["Olasılığın %90'ı", fmt1(drone.t90) + " dk'da taranır"],
      ]));
      parts.push(el("div", { class: "chart-box" }, canvas));
    }
    if (buddy) {
      parts.push(el("h4", null, rescue.rescuerName + " kurtarmaya gidiyor"));
      if (buddy.ok) {
        parts.push(el("div", { class: "zone-line" }, zoneBadge(buddy.status),
          el("span", { class: "muted small" }, buddy.toMin + " dk gidiş + " + buddy.backMin + " dk birlikte dönüş · " + fmt1(buddy.distanceM / 1000) + " km")));
      }
      parts.push(el("ul", { class: "rescue-msgs" }, buddy.messages.map((m) => el("li", null, rescueNames(m)))));
      if (tl) {
        // Bulunma süresiyle birleşik zaman çizelgesi: kararın gerçek dayanağı
        const t = (v) => "T+" + Math.round(v) + " dk";
        parts.push(el("p", { class: tl.survivable ? "small" : "warn-line" },
          (tl.droneLimits
            ? "İHA " + rescue.lostName + "'yi %90 olasılıkla " + t(tl.foundT) + "'da bulur (" + rescue.rescuerName + " " + t(tl.buddyT) + "'da hazır bekler) → "
            : rescue.rescuerName + " " + t(tl.buddyT) + "'da varır (İHA " + t(tl.foundT) + "'da bulmuş olur) → ") +
          (tl.atMeet > 0
            ? "buluşmada O₂ " + Math.round(tl.atMeet) + " dk, üste " + Math.round(tl.atBase) + " dk" + (tl.spare ? " (yedek tüple)" : "") +
              (tl.survivable ? "." : ": dönüşe yetmiyor.")
            : "O₂ buluşmadan " + Math.round(-tl.atMeet / Walkback.o2Multiplier(i.lost.heart_rate)) + " dk önce biter.")));
      }
    }
    parts.push(el("p", { class: "muted small" },
      "Alan: son konumdan min(geçen süre, O₂/çarpan) içinde yürünebilen hücreler, olasılık ∝ 1/(1+süre), plan rotasına ≤150 m ise ×2. " +
      "İHA: 100 m irtifa, 60° görüş → 115 m şerit, %20 örtüşme, 10 m/s. " + rescue.rescuerName + ": 10 dk hazırlık, birlikte dönüş %20 yavaş, 60 dk yedek O₂. Katsayılar varsayım (rescue.js)."));
    const card = el("div", { class: "card rescue-card" }, parts);
    if (drone) setTimeout(() => drawCoverage(canvas, drone), 0);
    return card;
  }

  function drawCoverage(canvas, drone) {
    if (rescue.chart) { rescue.chart.destroy(); rescue.chart = null; }
    if (typeof Chart === "undefined" || !canvas.isConnected) return;
    const css = getComputedStyle(document.documentElement);
    const ink = css.getPropertyValue("--muted").trim() || "#b39c90";
    const grid = "rgba(179,156,144,0.15)";
    rescue.chart = new Chart(canvas, {
      type: "line",
      data: {
        datasets: [{
          data: [{ x: 0, y: 0 }, ...drone.coverage.map((c) => ({ x: c.t, y: Math.round(c.p * 100) }))],
          borderColor: "#e0e0ff", borderWidth: 2, backgroundColor: "rgba(224,224,255,0.12)", fill: "start",
          pointRadius: 0, pointHoverRadius: 4, stepped: false, tension: 0,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: { displayColors: false, callbacks: {
            title: (it) => it[0].parsed.x.toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " dk",
            label: (it) => "olasılığın %" + it.parsed.y + "'i tarandı",
          } },
        },
        scales: {
          x: { type: "linear", ticks: { color: ink, callback: (v) => v + " dk", maxTicksLimit: 6 }, grid: { color: grid } },
          y: { min: 0, max: 100, ticks: { color: ink, callback: (v) => "%" + v, maxTicksLimit: 5 }, grid: { color: grid } },
        },
      },
    });
  }

  function toggleRescueAnim() {
    const a = rescue.anim;
    if (!rescue.active) return;
    if (a.on) return stopRescueAnim();
    if (a.t >= rescueEndMin()) { a.t = 0; a.flags = {}; }
    a.on = true;
    a.last = performance.now();
    const b = $("rescuePlay");
    if (b) b.textContent = "Duraklat";
    a.raf = requestAnimationFrame(rescueFrame);
  }

  function stopRescueAnim() {
    rescue.anim.on = false;
    cancelAnimationFrame(rescue.anim.raf);
    const b = $("rescuePlay");
    if (b) b.textContent = "▶ Aramayı oynat";
  }

  // Animasyon, İHA ve Ali'nin ikisi de bitene kadar sürer
  function rescueEndMin() {
    const { drone, buddy } = rescue.result;
    return Math.max(drone ? drone.minutes : 0, buddy && buddy.ok ? DISPATCH_MIN + buddy.toMin + buddy.backMin : 0);
  }

  function rescueFrame(now) {
    const a = rescue.anim;
    if (!a.on || !rescue.active) return;
    const dt = (Math.min(250, now - a.last) / 60000) * a.speed;
    a.last = now;
    a.t += dt;
    const { drone, buddy } = rescue.result, f = a.flags;
    const o2 = rescueLostO2();
    const cov = drone ? rescueCoverage(a.t) : 0;
    if ($("rsT")) {
      $("rsT").textContent = fmtT(a.t);
      $("rsO2").textContent = Math.max(0, Math.round(o2)) + " dk";
      $("rsO2").className = o2 <= 0 ? "bad" : o2 < 60 ? "mid" : "";
      $("rsCov").textContent = "%" + Math.round(cov * 100);
    }
    const lab = fmtT(a.t);
    if (drone && !f.d50 && drone.t50 != null && a.t >= drone.t50) { f.d50 = true; showToast("info", lab, "İHA en olası %50 alanı taradı."); }
    if (drone && !f.d90 && a.t >= drone.t90) { f.d90 = true; showToast("info", lab, "İHA olasılığın %90'ını taradı."); }
    if (!f.go && a.t >= DISPATCH_MIN) { f.go = true; showToast("info", lab, rescue.rescuerName + " üsten çıktı."); }
    if (buddy && buddy.ok && !f.arr && a.t >= DISPATCH_MIN + buddy.toMin) {
      f.arr = true;
      showToast(o2 > 0 ? "ok" : "danger", lab, rescue.rescuerName + " " + rescue.lostName + "'ye ulaştı" + (o2 > 0 ? " (O₂ " + Math.round(o2) + " dk)." : " ama O₂ çoktan bitmişti."));
      if (o2 > 0 && buddy.spareNeeded) showToast("warn", lab, "Yedek O₂ tüpü bağlandı (+60 dk).");
    }
    if (!f.o2 && o2 <= 0 && !(buddy && buddy.spareNeeded && f.arr)) { f.o2 = true; showToast("danger", lab, rescue.lostName + "'nin O₂'si bitti."); }
    if (a.t >= rescueEndMin()) {
      a.t = rescueEndMin();
      stopRescueAnim();
      const tl = rescueTimeline();
      if (tl) showToast(tl.survivable ? "ok" : "danger", fmtT(a.t), tl.survivable
        ? "Üste varıldı: " + rescue.lostName + " güvende (" + Math.round(tl.atBase) + " dk O₂)."
        : "Kurtarma başarısız: " + rescue.lostName + " üste canlı ulaşamadı.");
      return;
    }
    a.raf = requestAnimationFrame(rescueFrame);
  }

  function closeRescue() {
    stopRescueAnim();
    rescue.anim.t = 0;
    rescue.anim.flags = {};
    rescue.active = false;
    clearRescueDrawing();
    if (rescue.chart) { rescue.chart.destroy(); rescue.chart = null; }
    document.body.classList.remove("emergency");
    setLink(true);
    setPlanLabels(true);
    hideDetail();
    drawZones();
  }

  // Demo'yu sıfırla: sunumdan önce tek tıkla temiz başlangıç (kayıtlı profil, plan, yürüyüş, acil durum, rota, pinler)
  function resetDemo() {
    if (rescue.active) closeRescue();
    if (walk.active) endWalk("stop");
    clearWalkEntities();
    setDrawing(false);
    clearRoute();
    try { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(EXTRA_KEY); } catch { /* gizli pencere: zaten kayıt yok */ }
    astronauts = JSON.parse(JSON.stringify(defaultAstronauts));
    evaPlan.stops = [{ id: "delta_front", dwellMin: 40 }, { id: "three_forks", dwellMin: 30 }]; // evaPlan'daki demo planıyla aynı
    $("planDepart").value = "window";
    clearPlan();
    renderPlanStops();
    selectAstronaut(astronauts[0] && astronauts[0].id, false);
    computeZones();
    hideDetail();
    closeDrawer();
    flyToJezero();
    showToast("info", "Demo", "Sıfırlandı: varsayılan profiller ve plan.");
  }
  $("resetDemoBtn").addEventListener("click", resetDemo);

  // Plan işaretlerinin yazılarını gizle/göster (çizgiler ve noktalar kalır)
  function setPlanLabels(show) {
    evaPlan.entities.forEach((e) => { if (e.label) e.label.show = show; });
  }

  $("radioLostBtn").addEventListener("click", radioLost);
  $("walkLost").addEventListener("click", radioLost);

  // --- Harita tıklamaları: rota modunda nokta ekle, değilse pin kartı aç ---
  const clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
  // Cesium'un varsayılan çift tıkla "varlığı takip et" davranışını kapat (rotayı bitirmek için kullanıyoruz)
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

  clickHandler.setInputAction((ev) => {
    if (route.drawing) {
      const ll = pickLonLat(ev.position);
      if (!ll) return;
      const last = route.pts[route.pts.length - 1];
      // Çift tıklama önce iki tek tıklama üretir: aynı yere ikinci noktayı ekleme
      if (last && Math.abs(last[0] - ll[0]) < 1e-5 && Math.abs(last[1] - ll[1]) < 1e-5) return;
      route.pts.push(ll);
      redrawRoute();
      return;
    }
    const picked = scene.pick(ev.position);
    const id = picked && picked.id && typeof picked.id.id === "string" ? picked.id.id : "";
    if (id.startsWith("poi:")) openPoi(id.slice(4));
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  clickHandler.setInputAction(() => {
    if (route.drawing) finishRoute();
  }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

  document.getElementById("routeBtn").addEventListener("click", () => {
    if (route.drawing) finishRoute();
    else {
      setDrawing(true);
      closeDrawer();
    }
  });
  document.getElementById("routeClearBtn").addEventListener("click", () => {
    setDrawing(false);
    clearRoute();
    hideDetail();
  });
  document.getElementById("routeFabDone").addEventListener("click", finishRoute);
  document.getElementById("routeFabCancel").addEventListener("click", () => {
    setDrawing(false);
    clearRoute();
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && route.drawing) {
      setDrawing(false);
      clearRoute();
    }
  });
  // Profil değişince (yük, nabız) açık rota kartının sayıları da güncellensin
  window.addEventListener("marstrail:astronaut", () => {
    if (!route.drawing && route.pts.length > 1 && !detailPanel.hidden && detailBody.querySelector(".chart-box")) showRouteCard();
  });

  // --- G3: Mobil çekmece ---
  const leftPanel = document.getElementById("leftPanel");
  function closeDrawer() {
    leftPanel.classList.remove("open");
  }
  document.getElementById("drawerHandle").addEventListener("click", () => leftPanel.classList.toggle("open"));

  // Sonraki kartlar için dışarı aç
  window.MarsTrail = {
    viewer, MARS, JEZERO, setBaseLayer, setAutoRotate, flyToJezero, flyHome, overlays, loadJSON,
    showDetail, hideDetail, el, kvList, setLink, updateTopBar, openPoi, analyzeRoute,
    get route() { return route; }, finishRoute, setDrawing, computeZones,
    get astronauts() { return astronauts; },
    get selectedAstronaut() { return astronauts.find((x) => x.id === selectedAstroId); },
    selectAstronaut, renderAstronauts, saveAll, emitAstronautChange, PROFILE_FIELDS,
    get plan() { return evaPlan.result; }, runPlan, addPlanStop, clearPlan,
    walk, startWalk, returnNow, endWalk,
    rescue, radioLost, closeRescue, toggleRescueAnim,
  };
})();
