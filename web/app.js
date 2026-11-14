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
  globe.baseColor = Cesium.Color.fromCssColorString("#5a2e1c");
  scene.backgroundColor = Cesium.Color.BLACK;

  // --- Güneş ışığı ---
  // Güneş Jezero'ya göre sabit: kuzeybatıdan (azimut 315°), ufkun 30° üstünden.
  // Neden: Elif'in hillshade.png katmanı da KB'dan aydınlatılıyor; gölgeler tutarlı olsun.
  // Bu bir sunum tercihi, gerçek Güneş konumu değil (Mars saati E8'de gelecek).
  const SUN = { azimuthDeg: 315, elevationDeg: 30 };
  function sunLightDirection() {
    const az = Cesium.Math.toRadians(SUN.azimuthDeg);
    const el = Cesium.Math.toRadians(SUN.elevationDeg);
    // Yerel doğu-kuzey-yukarı ekseninde Güneş'e doğru birim vektör
    const toSunLocal = new Cesium.Cartesian3(Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el));
    const enu = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(JEZERO.lon, JEZERO.lat, 0, MARS), MARS);
    const toSun = Cesium.Matrix4.multiplyByPointAsVector(enu, toSunLocal, new Cesium.Cartesian3());
    // Işığın yönü Güneş'ten sahneye doğrudur
    return Cesium.Cartesian3.normalize(Cesium.Cartesian3.negate(toSun, toSun), toSun);
  }
  scene.light = new Cesium.DirectionalLight({ direction: sunLightDirection(), intensity: 2.0 });
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

  function enableJezeroTerrain(g) {
    const sample = makeTerrainSampler(g);
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
      offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), diagM * 1.4),
      duration: 4,
    });
  }
  document.getElementById("jezeroBtn").addEventListener("click", flyToJezero);

  loadJSON("data/grid.json")
    .then(enableJezeroTerrain)
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

  function saveAll() {
    const data = {};
    astronauts.forEach((a) => {
      data[a.id] = {};
      PROFILE_FIELDS.forEach((f) => (data[a.id][f.key] = a[f.key]));
    });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
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
    const resetBtn = el("button", { type: "button" }, "Varsayılana dön");

    form.append(
      el("h3", null, a.name),
      el("p", { class: "muted" }, a.role),
      el("div", { class: "zone-line" }, zoneBadge(a.zone), el("span", { class: "muted small" }, zoneText(a.zone))),
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
      renderAstronauts();
      showDetail(astroDetail(a)); // uyarı renklerini tazele
      detailBody.querySelector(".pstatus").textContent = ok
        ? "Kaydedildi · " + new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })
        : "Güncellendi ama tarayıcı kaydetmeye izin vermedi.";
      emitAstronautChange(a);
    });

    resetBtn.addEventListener("click", () => {
      const def = defaultAstronauts.find((x) => x.id === a.id);
      if (!def) return;
      PROFILE_FIELDS.forEach((f) => (a[f.key] = def[f.key]));
      saveAll();
      renderAstronauts();
      showDetail(astroDetail(a));
      detailBody.querySelector(".pstatus").textContent = "astronauts.json değerlerine dönüldü.";
      emitAstronautChange(a);
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
      })
    );
  }

  function selectAstronaut(id, openDetail) {
    selectedAstroId = id;
    renderAstronauts();
    const a = astronauts.find((x) => x.id === id);
    if (a && openDetail) showDetail(astroDetail(a));
  }

  let defaultAstronauts = [];
  loadJSON("data/astronauts.json")
    .then((d) => {
      defaultAstronauts = JSON.parse(JSON.stringify(d));
      // Kayıtlı profil varsa onun alanları JSON'daki varsayılanın üstüne yazılır
      const saved = loadSaved();
      astronauts = d.map((a) => ({ ...a, ...(saved[a.id] || {}) }));
      selectAstronaut(astronauts[0] && astronauts[0].id, false);
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
    viewer, MARS, JEZERO, setBaseLayer, setAutoRotate, flyToJezero, flyHome, overlays, loadJSON,
    showDetail, hideDetail, el, kvList, setLink, updateTopBar,
    get astronauts() { return astronauts; },
    get selectedAstronaut() { return astronauts.find((x) => x.id === selectedAstroId); },
    selectAstronaut, renderAstronauts, saveAll, emitAstronautChange, PROFILE_FIELDS,
  };
})();
