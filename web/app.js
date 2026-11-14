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
      skyAtmosphere: false,      // Dünya'nın mavi atmosferi Mars'a uymuyor
    });
  } catch (err) {
    console.error(err);
    showError("3B küre başlatılamadı (WebGL desteği gerekli). " + err.message);
    return;
  }

  const scene = viewer.scene;
  scene.globe.showGroundAtmosphere = false;
  scene.globe.baseColor = Cesium.Color.fromCssColorString("#5a2e1c");
  scene.backgroundColor = Cesium.Color.BLACK;

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

  // --- Başlangıç görünümü: Jezero yarımküresi ---
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(JEZERO.lon, JEZERO.lat, 11000000, MARS),
  });

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

  // Sonraki kartlar için dışarı aç
  window.MarsTrail = { viewer, MARS, JEZERO, setBaseLayer, setAutoRotate };
})();
