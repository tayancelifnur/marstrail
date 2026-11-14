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

  // --- G2: Jezero'ya uçuş ---
  // Çalışma alanı layers.json bbox'ından gelir; yüklenene kadar varsayılan kullanılır.
  let studyBbox = [77.36, 18.38, 77.51, 18.52]; // [batı, güney, doğu, kuzey]

  function flyToJezero() {
    setAutoRotate(false);
    const [w, s, e, n] = studyBbox;
    const padLon = (e - w) * 0.6;
    const padLat = (n - s) * 0.6;
    viewer.camera.flyTo({
      destination: Cesium.Rectangle.fromDegrees(w - padLon, s - padLat, e + padLon, n + padLat),
      duration: 4,
    });
  }
  document.getElementById("jezeroBtn").addEventListener("click", flyToJezero);

  // --- G2: Katman menüsü (web/data/layers.json) ---
  const overlays = {}; // id -> { def, layer }

  async function loadJSON(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) throw new Error(path + " → HTTP " + res.status);
    return res.json();
  }

  async function addOverlay(def) {
    const [w, s, e, n] = def.bbox;
    const provider = await Cesium.SingleTileImageryProvider.fromUrl("data/" + def.file, {
      rectangle: Cesium.Rectangle.fromDegrees(w, s, e, n),
      ellipsoid: MARS,
      credit: def.source,
    });
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
    for (const def of defs) {
      try {
        const layer = await addOverlay(def);
        list.append(renderLayerRow(def, layer));
      } catch (err) {
        console.error("Katman yüklenemedi:", def.id, err);
        const p = document.createElement("p");
        p.className = "muted small";
        p.textContent = def.name + ": yüklenemedi";
        list.append(p);
      }
    }
  }
  initLayers();

  // Sonraki kartlar için dışarı aç
  window.MarsTrail = { viewer, MARS, JEZERO, setBaseLayer, setAutoRotate, flyToJezero, overlays, loadJSON };
})();
