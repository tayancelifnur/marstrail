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
    document.getElementById("leftPanel").classList.remove("open");
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

  // --- G3: Üst bar ---
  // Mars saati şimdilik SABİT (senaryo: Sol 34). E8'de Elif'in web/marstime.js'i gelince
  // marsClock() içi onunla değiştirilecek. Dünya saatleri gerçek.
  const SCENARIO_SOL = 34;
  function marsClock() {
    return {
      sol: SCENARIO_SOL,
      lmst: "14:20",      // Jezero yerel saati (sabit, E8'de hesaplanacak)
      delayMin: 12.5,     // Dünya–Mars tek yön ışık gecikmesi, dk (sabit, E8'de hesaplanacak)
    };
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
    $("tbUtc").textContent = fmtTime(now, "UTC");
    $("tbTr").textContent = fmtTime(now, "Europe/Istanbul");
    $("tbDelay").textContent = mc.delayMin.toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " dk uzakta";

    const c = todaysConditions(mc.sol);
    if (c) {
      const left = toMin(c.sunset_lmst) - toMin(mc.lmst);
      $("tbSunset").textContent = left > 0 ? Math.floor(left / 60) + " sa " + (left % 60) + " dk" : "gün battı";
      $("tbWeather").textContent =
        Math.round(c.temp_min_c) + "…" + Math.round(c.temp_max_c) + " °C · toz τ " + c.dust_tau.toFixed(2);
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

  // --- G3: Astronotlar (G4'te tam profil formu gelecek) ---
  let astronauts = [];
  let selectedAstroId = null;

  // Bölge etiketi için yer (G6'da Walkback.zones ile hesaplanacak). null = bilinmiyor.
  function zoneBadge(zone) {
    const labels = { green: "YEŞİL", yellow: "SARI", red: "KIRMIZI" };
    return el("span", { class: "zone " + (zone || "") }, zone ? labels[zone] : "BÖLGE –");
  }

  function astroDetail(a) {
    return el(
      "div",
      null,
      el("h3", null, a.name),
      el("p", { class: "muted" }, a.role),
      zoneBadge(a.zone),
      kvList([
        ["Giysi", a.suit],
        ["Kilo", a.mass_kg + " kg"],
        ["O₂", a.o2_min + " / " + a.o2_capacity_min + " dk"],
        ["Batarya", "%" + a.battery_pct],
        ["Su", "%" + a.water_pct],
        ["Nabız", a.heart_rate + " atım/dk"],
        ["Yük", a.load_kg + " kg"],
        ["Radyasyon", a.radiation_msv + " mSv"],
      ])
    );
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
            el("span", null, "O₂ " + a.o2_min + " dk"),
            el("span", null, "♥ " + a.heart_rate),
            el("span", null, "🔋 %" + a.battery_pct)
          )
        );
        card.addEventListener("click", () => selectAstronaut(a.id, true));
        return card;
      })
    );
  }

  function selectAstronaut(id, openDetail) {
    selectedAstroId = id;
    renderAstronauts();
    const a = astronauts.find((x) => x.id === id);
    if (a && openDetail) showDetail(astroDetail(a));
  }

  loadJSON("data/astronauts.json")
    .then((d) => {
      astronauts = d;
      selectAstronaut(d[0] && d[0].id, false);
    })
    .catch((err) => {
      console.error(err);
      document.getElementById("astroList").innerHTML = '<p class="muted">astronauts.json okunamadı.</p>';
    });

  // --- G3: Mobil çekmece ---
  const leftPanel = document.getElementById("leftPanel");
  function closeDrawer() {
    leftPanel.classList.remove("open");
  }
  document.getElementById("drawerHandle").addEventListener("click", () => leftPanel.classList.toggle("open"));

  // Sonraki kartlar için dışarı aç
  window.MarsTrail = {
    viewer, MARS, JEZERO, setBaseLayer, setAutoRotate, flyToJezero, overlays, loadJSON,
    showDetail, hideDetail, el, kvList, setLink, updateTopBar,
    get astronauts() { return astronauts; },
    get selectedAstronaut() { return astronauts.find((x) => x.id === selectedAstroId); },
    selectAstronaut, renderAstronauts,
  };
})();
