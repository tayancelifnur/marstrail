/*
 * MarsTrail – O₂ bölgeleri ve güvenli rota (E8)
 *
 * Apollo'nun "walkback" kuralının araziye bağlı hali: astronot nereye kadar gidip
 * üsse yürüyerek dönebilir? Daire değil; eğim, kum ve zemine göre şekil alır.
 *
 * Veri: web/data/grid.json (256×256, ~44 m hücre; elev, score, blocked, bounds) – scripts/prep_layers.py
 * Formüller: docs/PLAN.md §5. Katsayılar VARSAYIMDIR (gerçek EVA verisiyle kalibre edilmedi).
 *
 * Kullanım:
 *   await Walkback.load("data/grid.json");
 *   const z = Walkback.zones({lon: 77.4509, lat: 18.4446}, 480, 85, 6);   // konum, O₂ dk, nabız, yük kg
 *   z.here            → "green" | "yellow" | "red"   (astronotun şu anki bölgesi: kart etiketi)
 *   z.canvas()        → 256×256 RGBA canvas (yeşil/sarı/kırmızı); Cesium'da bbox üstüne serilir
 *   z.outlines.green  → [[ [lon,lat], ... ], ...]   bölge sınır çizgileri (Cesium polyline)
 *   z.outlines.yellow → aynı, sarı bölgenin dış sınırı
 *   z.availableMin, z.multiplier, z.stats, z.ms
 *   const r = Walkback.path({lon:77.4509, lat:18.4446}, {lon:77.4078, lat:18.4526}, {loadKg: 6});
 *   r.coords → [[lon,lat,elev], ...], r.minutes, r.distanceM, r.ok
 *   Walkback.timeHome({lon, lat}, {loadKg}) → bu noktadan üsse yürüme süresi (dk)
 */
(function (root) {
  "use strict";

  // ---- Varsayımlar (PLAN.md §5) -------------------------------------------------------------
  const MARS_SUIT_FACTOR = 0.6;   // Tobler hızı × 0,6: Mars yerçekimi + basınçlı giysi (varsayım)
  const SCORE_WEIGHT = 2;         // maliyet × (1 + 2·skor): zor zemin süreyi en fazla 3 katına çıkarır
  const SLOPE_MAX_DEG = 25;       // kenar eğimi bunu aşarsa geçilmez (giysili astronot için güvenli üst sınır)
  const GREEN_MARGIN = 1.25;      // yeşil: gidiş + dönüş ≤ kalan O₂ / 1,25 (%25 güvenlik payı)
  const HR_REF = 90;              // O₂ tüketim çarpanının referans nabzı (atım/dk)
  const BASE = { lon: 77.45089, lat: 18.44463 }; // üs = iniş noktası (regions.json "base")

  let G = null; // yüklenen grid

  function init(grid) {
    const n = grid.width * grid.height;
    G = {
      w: grid.width, h: grid.height, b: grid.bounds, cell: grid.cell_size_m,
      elev: Float32Array.from(grid.elev),
      score: grid.score ? Float32Array.from(grid.score) : new Float32Array(n).fill(0.3),
      blocked: Uint8Array.from(grid.blocked),
      sand: grid.sand ? Uint8Array.from(grid.sand) : new Uint8Array(n), // eolyen kum (eva.js Go/No-Go)
      backCache: new Map(),
    };
    return G;
  }

  async function load(url) {
    const r = await fetch(url || "data/grid.json");
    return init(await r.json());
  }

  // ---- Koordinat ↔ hücre --------------------------------------------------------------------
  function cellOf(p) {
    const { w, h, b } = G;
    const c = Math.floor(((p.lon - b.west) / (b.east - b.west)) * w);
    const r = Math.floor(((b.north - p.lat) / (b.north - b.south)) * h);
    if (r < 0 || r >= h || c < 0 || c >= w) return -1;
    return r * w + c;
  }
  function lonLatOf(i) {
    const { w, h, b } = G;
    const r = Math.floor(i / w), c = i % w;
    return [b.west + ((c + 0.5) / w) * (b.east - b.west), b.north - ((r + 0.5) / h) * (b.north - b.south)];
  }
  /** Geçilmez hücreye düşen noktayı en yakın geçilebilir hücreye taşır (halka halka arama). */
  function nearestOpen(i) {
    if (i < 0 || !G.blocked[i]) return i;
    const r0 = Math.floor(i / G.w), c0 = i % G.w;
    for (let rad = 1; rad < 20; rad++)
      for (let dr = -rad; dr <= rad; dr++)
        for (let dc = -rad; dc <= rad; dc++) {
          const r = r0 + dr, c = c0 + dc;
          if (r >= 0 && r < G.h && c >= 0 && c < G.w && !G.blocked[r * G.w + c]) return r * G.w + c;
        }
    return -1;
  }

  // ---- Kenar süresi (dk) --------------------------------------------------------------------
  /*
   * u → v komşu hücre geçişi:
   *   d      = hücre boyu (çapraz komşuda × √2)
   *   tanθ   = (elev_v − elev_u) / d                         yönlü eğim (+ yokuş yukarı)
   *   v_kmh  = 6 · exp(−3,5 · |tanθ + 0,05|)                 Tobler yürüme hızı (km/sa); en hızlı hafif yokuş aşağıda
   *            × 0,6                                         Mars + giysi düzeltmesi (varsayım)
   *            × (1 − yük_kg / 100)                          yük hızı düşürür (6 kg → ×0,94)
   *   t      = d / v · (1 + 2 · skor_ort)                    PLAN.md §5 hücre maliyeti; skor = eğim+kum+kaya+termal füzyonu
   *   |θ| > 25° ya da hücrelerden biri geçilmez → kenar yok
   */
  const SQRT2 = Math.SQRT2;
  const TAN_MAX = Math.tan((SLOPE_MAX_DEG * Math.PI) / 180);
  function edgeMinutes(u, v, diag, loadFactor) {
    if (G.blocked[u] || G.blocked[v]) return Infinity;
    const d = diag ? G.cell * SQRT2 : G.cell;
    const tan = (G.elev[v] - G.elev[u]) / d;
    if (Math.abs(tan) > TAN_MAX) return Infinity;
    const vKmh = 6 * Math.exp(-3.5 * Math.abs(tan + 0.05)) * MARS_SUIT_FACTOR * loadFactor;
    const tMin = (d / 1000 / vKmh) * 60;
    return tMin * (1 + SCORE_WEIGHT * 0.5 * (G.score[u] + G.score[v]));
  }
  const loadFactorOf = (kg) => Math.max(0.2, 1 - (kg || 0) / 100);

  // ---- İkili yığın (öncelik kuyruğu) --------------------------------------------------------
  function Heap(cap) {
    const ids = new Int32Array(cap * 8), keys = new Float64Array(cap * 8); // hücre başına en fazla 8 ekleme (8 komşu)
    let n = 0;
    return {
      get size() { return n; },
      push(id, k) {
        let i = n++;
        while (i > 0) {
          const p = (i - 1) >> 1;
          if (keys[p] <= k) break;
          ids[i] = ids[p]; keys[i] = keys[p]; i = p;
        }
        ids[i] = id; keys[i] = k;
      },
      pop() {
        const top = ids[0], topK = keys[0];
        const id = ids[--n], k = keys[n];
        let i = 0;
        for (;;) {
          let c = 2 * i + 1;
          if (c >= n) break;
          if (c + 1 < n && keys[c + 1] < keys[c]) c++;
          if (keys[c] >= k) break;
          ids[i] = ids[c]; keys[i] = keys[c]; i = c;
        }
        ids[i] = id; keys[i] = k;
        this.lastKey = topK;
        return top;
      },
    };
  }

  const NB = [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0], [-1, -1, 1], [-1, 1, 1], [1, -1, 1], [1, 1, 1]];

  /*
   * Dijkstra: kaynaktan her hücreye en kısa SÜRE (dk).
   *   reverse = false → dist[x] = kaynaktan x'e gitme süresi        (gidiş)
   *   reverse = true  → dist[x] = x'ten kaynağa gelme süresi         (dönüş; kenar yönü ters çevrilir,
   *                     çünkü yokuş yukarı/aşağı süresi farklı: x→üs süresi, üs→x süresi değildir)
   *   target verilirse oraya varınca durur (rota için).
   * Adımlar: tüm süreler ∞, kaynak 0 → kuyruktan en küçük süreli hücreyi al (artık kesin) →
   * 8 komşusu için "bu hücre üzerinden daha kısa mı?" bak, kısaysa güncelle ve kuyruğa ekle → tekrarla.
   */
  function dijkstra(src, loadKg, reverse, target) {
    const N = G.w * G.h, w = G.w, h = G.h;
    const dist = new Float64Array(N).fill(Infinity);
    const prev = new Int32Array(N).fill(-1);
    const done = new Uint8Array(N);
    const lf = loadFactorOf(loadKg);
    const heap = Heap(N);
    dist[src] = 0;
    heap.push(src, 0);
    while (heap.size) {
      const u = heap.pop();
      if (done[u]) continue;
      done[u] = 1;
      if (u === target) break;
      const r = (u / w) | 0, c = u - r * w;
      for (let k = 0; k < 8; k++) {
        const rr = r + NB[k][0], cc = c + NB[k][1];
        if (rr < 0 || rr >= h || cc < 0 || cc >= w) continue;
        const v = rr * w + cc;
        if (done[v]) continue;
        const t = reverse ? edgeMinutes(v, u, NB[k][2], lf) : edgeMinutes(u, v, NB[k][2], lf);
        if (t === Infinity) continue;
        const nd = dist[u] + t;
        if (nd < dist[v]) { dist[v] = nd; prev[v] = u; heap.push(v, nd); }
      }
    }
    return { dist, prev };
  }

  /** Her hücreden üsse dönüş süresi; yalnızca yüke bağlı olduğu için önbelleğe alınır. */
  function homeTimes(base, loadKg) {
    const key = cellOf(base) + "|" + (loadKg || 0);
    if (!G.backCache.has(key)) G.backCache.set(key, dijkstra(nearestOpen(cellOf(base)), loadKg, true).dist);
    return G.backCache.get(key);
  }

  /*
   * O₂ çarpanı: tüketim = taban × (1 + (nabız − 90) / 100)       PLAN.md §5; nabız 150 → ×1,6
   * Kullanılabilir yürüme süresi = kalan O₂ (dk, taban tüketimde) / çarpan
   */
  const o2Multiplier = (hr) => Math.max(0.5, 1 + ((hr ?? HR_REF) - HR_REF) / 100);

  /*
   * O₂ bölgeleri: astronotun konumu S, üs B.
   *   gidiş[x] = Dijkstra(S → x)        dönüş[x] = Dijkstra(x → B)   (ters kenarlarla)
   *   toplam[x] = gidiş[x] + dönüş[x]   "x'e git, oradan üsse dön"
   *   YEŞİL : toplam ≤ kullanılabilir / 1,25   (%25 pay)
   *   SARI  : toplam ≤ kullanılabilir           (dönülür, pay yok)
   *   KIRMIZI: toplam > kullanılabilir ya da ulaşılamaz
   *   here (astronotun kendi bölgesi): dönüş[S] aynı eşiklerle
   * Not: Durakta çalışma süresi burada yok; planlayıcı (E11) ekler.
   */
  function zones(start, o2Min, hr, loadKg, opts) {
    const t0 = (typeof performance !== "undefined" ? performance : Date).now();
    const base = (opts && opts.base) || BASE;
    const s = nearestOpen(cellOf(start));
    if (s < 0) throw new Error("Başlangıç noktası grid dışında");
    const mult = o2Multiplier(hr);
    const avail = o2Min / mult;
    const out = dijkstra(s, loadKg, false).dist;
    const home = homeTimes(base, loadKg);
    const N = G.w * G.h;
    const cls = new Uint8Array(N); // 1 yeşil, 2 sarı, 3 kırmızı, 4 geçilmez
    const total = new Float32Array(N);
    let nG = 0, nY = 0;
    for (let i = 0; i < N; i++) {
      const t = out[i] + home[i];
      total[i] = t;
      if (G.blocked[i]) cls[i] = 4;
      else if (t <= avail / GREEN_MARGIN) { cls[i] = 1; nG++; }
      else if (t <= avail) { cls[i] = 2; nY++; }
      else cls[i] = 3;
    }
    const hb = home[s];
    const here = hb <= avail / GREEN_MARGIN ? "green" : hb <= avail ? "yellow" : "red";
    const km2 = (G.cell * G.cell) / 1e6;
    const ms = (typeof performance !== "undefined" ? performance : Date).now() - t0;
    return {
      here, classes: cls, totalMin: total, availableMin: avail, multiplier: mult, homeMin: hb, ms,
      stats: { greenKm2: +(nG * km2).toFixed(2), yellowKm2: +(nY * km2).toFixed(2) },
      outlines: { green: outline(cls, 1), yellow: outline(cls, 2) },
      canvas: (alpha) => toCanvas(cls, alpha),
    };
  }

  /** Bölge sınırları: maskenin (sınıf ≤ k) hücre kenarlarını zincirleyip çizgi dizisi yapar. */
  function outline(cls, k) {
    const { w, h, b } = G;
    const inside = (r, c) => r >= 0 && r < h && c >= 0 && c < w && cls[r * w + c] >= 1 && cls[r * w + c] <= k;
    const segs = new Map(); // "x,y" köşe → komşu köşeler
    const add = (x1, y1, x2, y2) => {
      const a = x1 + "," + y1, bb = x2 + "," + y2;
      if (!segs.has(a)) segs.set(a, []);
      if (!segs.has(bb)) segs.set(bb, []);
      segs.get(a).push(bb); segs.get(bb).push(a);
    };
    for (let r = 0; r < h; r++)
      for (let c = 0; c < w; c++) {
        if (!inside(r, c)) continue;
        if (!inside(r - 1, c)) add(c, r, c + 1, r);
        if (!inside(r + 1, c)) add(c, r + 1, c + 1, r + 1);
        if (!inside(r, c - 1)) add(c, r, c, r + 1);
        if (!inside(r, c + 1)) add(c + 1, r, c + 1, r + 1);
      }
    const toLL = (key) => {
      const [x, y] = key.split(",").map(Number);
      return [b.west + (x / w) * (b.east - b.west), b.north - (y / h) * (b.north - b.south)];
    };
    const lines = [];
    for (const startKey of segs.keys()) {
      while (segs.get(startKey).length) {
        const line = [toLL(startKey)];
        let cur = startKey;
        while (segs.get(cur).length) {
          const nxt = segs.get(cur).pop();
          const back = segs.get(nxt);
          back.splice(back.indexOf(cur), 1);
          line.push(toLL(nxt));
          cur = nxt;
          if (cur === startKey) break;
        }
        if (line.length > 4) lines.push(line); // tek hücrelik kırıntıları atla
      }
    }
    return lines;
  }

  const COLORS = { 1: [46, 204, 113], 2: [241, 196, 15], 3: [231, 76, 60], 4: [40, 0, 0] };
  function toCanvas(cls, alpha) {
    const a = Math.round((alpha ?? 0.45) * 255);
    const cv = document.createElement("canvas");
    cv.width = G.w; cv.height = G.h;
    const ctx = cv.getContext("2d");
    const img = ctx.createImageData(G.w, G.h);
    for (let i = 0; i < cls.length; i++) {
      const col = COLORS[cls[i]] || [0, 0, 0];
      img.data[i * 4] = col[0]; img.data[i * 4 + 1] = col[1]; img.data[i * 4 + 2] = col[2];
      img.data[i * 4 + 3] = cls[i] === 3 ? Math.round(a * 0.6) : a;
    }
    ctx.putImageData(img, 0, 0);
    return cv;
  }

  /** a → b en hızlı güvenli rota (geçilmez hücre ve >25° kenar yok). */
  function path(a, b, opts) {
    const loadKg = opts && opts.loadKg;
    const s = nearestOpen(cellOf(a)), t = nearestOpen(cellOf(b));
    if (s < 0 || t < 0) return { ok: false, coords: [], minutes: Infinity, distanceM: 0 };
    const { dist, prev } = dijkstra(s, loadKg, false, t);
    if (dist[t] === Infinity) return { ok: false, coords: [], minutes: Infinity, distanceM: 0 };
    const cells = [];
    for (let i = t; i !== -1; i = prev[i]) cells.push(i);
    cells.reverse();
    let distanceM = 0;
    for (let k = 1; k < cells.length; k++) {
      const dr = Math.abs(((cells[k] / G.w) | 0) - ((cells[k - 1] / G.w) | 0));
      const dc = Math.abs((cells[k] % G.w) - (cells[k - 1] % G.w));
      distanceM += dr && dc ? G.cell * SQRT2 : G.cell;
    }
    const coords = cells.map((i) => [...lonLatOf(i), G.elev[i]]);
    // Hücre başına varış süresi: canlı yürüyüşte (G7) konum ↔ zaman eşlemesi için
    const minutesAt = cells.map((i) => dist[i]);
    return { ok: true, coords, minutesAt, minutes: dist[t], distanceM, cells };
  }

  /** Bir noktadan üsse yürüme süresi (dk). */
  function timeHome(p, opts) {
    const i = nearestOpen(cellOf(p));
    return i < 0 ? Infinity : homeTimes((opts && opts.base) || BASE, opts && opts.loadKg)[i];
  }

  root.Walkback = {
    load, init, zones, path, timeHome, o2Multiplier, cellOf, lonLatOf,
    BASE, GREEN_MARGIN, SLOPE_MAX_DEG, get grid() { return G; },
  };
  if (typeof module !== "undefined") module.exports = root.Walkback;
})(typeof window !== "undefined" ? window : globalThis);
