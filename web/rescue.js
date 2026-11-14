/*
 * MarsTrail – Hayatta Kal: kayıp astronot araması (E13)
 *
 * "Telsiz koptu" → (1) olasılıklı arama alanı, (2) İHA zikzak tarama rotası, (3) arkadaşın kurtarma rotası.
 * Gerekenler: walkback.js (Walkback.load çağrılmış olmalı). Formüller docs/PLAN.md §3.7 ve §5.
 * Bütün katsayılar VARSAYIMDIR; gerekçeleri yanlarında.
 *
 * Kullanım:
 *   const r = Rescue.respond({
 *     last: {lon, lat},          // son bilinen konum (telsiz koptuğu an; ör. Eva.positionAt(plan, t))
 *     elapsedMin: 20,            // telsiz koptuğundan bu yana geçen süre (canlı artar → alan büyür)
 *     lost: {o2LeftMin: 380, heart_rate: 150, load_kg: 6},   // kopma anındaki değerler
 *     rescuer: ali,              // astronauts.json kaydı (o2_min, heart_rate, load_kg, position)
 *   });
 *   r.area.canvas()            → 256×256 olasılık ısı haritası (Cesium'da bbox'a serilir)
 *   r.area.outlines.p50 / p90  → en olası %50 ve %90 alanların sınır çizgileri [[lon,lat],…]
 *   r.drone.waypoints          → [[lon,lat],…] İHA zikzak rotası (üsten kalkış ve dönüş dahil)
 *   r.drone.t50, r.drone.t90   → olasılığın %50'sini / %90'ını taramak için gereken dakika
 *   r.buddy                    → {to, back, status, messages…} Ali'nin kurtarma rotası ve O₂ kontrolü
 */
(function (root) {
  "use strict";

  // ---- Varsayımlar -------------------------------------------------------------------------
  const ROUTE_BONUS = 2;          // planlanan rotaya 150 m'den yakın hücreler ×2 olası (astronot genelde plana sadık)
  const ROUTE_NEAR_M = 150;
  const DRONE = {
    altitudeM: 100,               // uçuş irtifası. Ingenuity 24 m'ye kadar çıktı; arama İHA'sı için 100 m varsayım
    fovDeg: 60,                   // kamera yatay görüş açısı
    overlap: 0.2,                 // komşu şeritler %20 örtüşür (kaçırma payı)
    speedMs: 10,                  // yatay hız. Ingenuity'nin ulaştığı en yüksek hız ~10 m/s
    enduranceMin: 20,             // tek bataryayla uçuş süresi (varsayım); aşılırsa üste dönüp batarya değişir
  };
  const DISPATCH_MIN = 10;        // Ali'nin giysiyi hazırlayıp çıkması (dk)
  const CARRY_FACTOR = 1.2;       // dönüşte yorgun/yaralı arkadaşla birlikte yürüme %20 yavaş
  const SPARE_O2_MIN = 60;        // Ali'nin taşıdığı yedek O₂ (dk, taban tüketimde) – gerekirse arkadaşa bağlanır
  const GREEN_MARGIN = 1.25;      // Ali için yeşil: gerekli ≤ O₂/1,25 (walkback.js ile aynı pay)
  const M_PER_DEG = 59274.7;      // Mars 2000 küresi: 2πR/360

  const W = () => root.Walkback;

  // ---- 1) Arama alanı ----------------------------------------------------------------------
  /*
   * Kayıp astronot son konumdan en fazla "bütçe" kadar yürümüş olabilir:
   *   bütçe = min(geçen süre, kalan O₂ / çarpan)        çarpan = 1 + (nabız − 90)/100
   * Ulaşılabilir hücreler = Dijkstra süresi ≤ bütçe. Her hücrenin ağırlığı:
   *   w = 1 / (1 + t)                    t = son konumdan o hücreye yürüme süresi (dk)
   *       × 2  (planlanan rotaya ≤150 m ise)
   * Kolay arazi (kısa süre) daha olası: PLAN §5 "olasılık ∝ 1/maliyet". Ağırlıklar toplamı 1'e bölünür.
   * En olası hücrelerden başlayarak olasılığın %50'sini ve %90'ını toplayan en küçük alanlar (p50, p90).
   */
  function searchArea(input) {
    const G = W().grid, N = G.w * G.h;
    const hr = input.lost.heart_rate ?? 90;
    const mult = W().o2Multiplier(hr);
    const o2Budget = Math.max(0, input.lost.o2LeftMin / mult);
    const budget = Math.min(input.elapsedMin ?? o2Budget, o2Budget);
    const tt = W().travelTimes(input.last, { loadKg: input.lost.load_kg });
    if (!tt) throw new Error("Son konum grid dışında");

    let nearRoute = null;
    if (input.route && input.route.length) {
      nearRoute = new Uint8Array(N);
      const r = Math.ceil(ROUTE_NEAR_M / G.cell);
      for (const [lon, lat] of input.route) {
        const i = W().cellOf({ lon, lat });
        if (i < 0) continue;
        const r0 = (i / G.w) | 0, c0 = i % G.w;
        for (let dr = -r; dr <= r; dr++)
          for (let dc = -r; dc <= r; dc++) {
            const rr = r0 + dr, cc = c0 + dc;
            if (rr >= 0 && rr < G.h && cc >= 0 && cc < G.w && Math.hypot(dr, dc) * G.cell <= ROUTE_NEAR_M) nearRoute[rr * G.w + cc] = 1;
          }
      }
    }

    const prob = new Float32Array(N);
    const cells = [];
    let sum = 0;
    for (let i = 0; i < N; i++) {
      if (tt[i] <= budget) {
        const w = (1 / (1 + tt[i])) * (nearRoute && nearRoute[i] ? ROUTE_BONUS : 1);
        prob[i] = w; sum += w; cells.push(i);
      }
    }
    for (const i of cells) prob[i] /= sum;

    // p50 / p90: olasılığa göre sırala, birikimli toplam eşiği geçene kadar al
    const sorted = cells.slice().sort((a, b) => prob[b] - prob[a]);
    const mask50 = new Uint8Array(N), mask90 = new Uint8Array(N), maskAll = new Uint8Array(N);
    let cum = 0, n50 = 0, n90 = 0;
    for (const i of sorted) {
      maskAll[i] = 1;
      if (cum < 0.5) { mask50[i] = 1; n50++; }
      if (cum < 0.9) { mask90[i] = 1; n90++; }
      cum += prob[i];
    }
    const km2 = (G.cell * G.cell) / 1e6;
    const best = sorted[0];
    return {
      last: input.last, budgetMin: budget, o2BudgetMin: o2Budget, multiplier: mult, prob, cells, mask50, mask90,
      areaKm2: +(cells.length * km2).toFixed(2), area50Km2: +(n50 * km2).toFixed(2), area90Km2: +(n90 * km2).toFixed(2),
      maxCell: best !== undefined ? { lon: W().lonLatOf(best)[0], lat: W().lonLatOf(best)[1], p: prob[best] } : null,
      outlines: { all: W().outlineMask(maskAll), p90: W().outlineMask(mask90), p50: W().outlineMask(mask50) },
      canvas: (alpha) => probCanvas(prob, sorted.length ? prob[best] : 1, alpha),
    };
  }

  function probCanvas(prob, pmax, alpha) {
    const G = W().grid;
    const cv = document.createElement("canvas");
    cv.width = G.w; cv.height = G.h;
    const ctx = cv.getContext("2d"), img = ctx.createImageData(G.w, G.h);
    const a = Math.round((alpha ?? 0.7) * 255);
    for (let i = 0; i < prob.length; i++) {
      if (!prob[i]) continue;
      const v = Math.sqrt(prob[i] / pmax);   // karekök: düşük olasılıklar da görünsün (yalnız gösterim)
      img.data[i * 4] = 255; img.data[i * 4 + 1] = Math.round(220 * (1 - v)); img.data[i * 4 + 2] = 0;
      img.data[i * 4 + 3] = Math.round(a * (0.25 + 0.75 * v));
    }
    ctx.putImageData(img, 0, 0);
    return cv;
  }

  // ---- 2) İHA zikzak (biçerdöver) rotası ---------------------------------------------------
  /*
   * Şerit genişliği (kameranın yerde gördüğü):  s = 2 · h · tan(FOV/2)      100 m, 60° → 115 m
   * Şerit aralığı:                               d = s · (1 − örtüşme)       → 92 m
   * Yön: alanın uzun ekseni (ağırlıklı ana bileşen) boyunca uçulur → daha az dönüş.
   * Şeritler alanın %90 maskesine kırpılır (boş dikdörtgen uçulmaz). İki başlangıç ucu denenir;
   * olasılığın %50'sini daha erken tarayan seçilir. Süre = üsten uçuş + şeritler + üsse dönüş.
   */
  function droneRoute(area, opts) {
    const o = Object.assign({}, DRONE, opts || {});
    const G = W().grid;
    const base = o.base || W().BASE;
    const swath = 2 * o.altitudeM * Math.tan((o.fovDeg * Math.PI) / 360);
    const spacing = swath * (1 - o.overlap);
    const lat0 = area.last.lat, lon0 = area.last.lon, k = Math.cos((lat0 * Math.PI) / 180);
    const toXY = (lon, lat) => [(lon - lon0) * k * M_PER_DEG, (lat - lat0) * M_PER_DEG];
    const toLL = (x, y) => [lon0 + x / (k * M_PER_DEG), lat0 + y / M_PER_DEG];

    const pts = [];
    for (let i = 0; i < area.mask90.length; i++) if (area.mask90[i]) {
      const [lon, lat] = W().lonLatOf(i);
      pts.push({ i, xy: toXY(lon, lat), p: area.prob[i] });
    }
    if (!pts.length) return null;
    // Ağırlıklı ana eksen: kovaryans matrisinin en büyük özvektörünün açısı
    let sw = 0, mx = 0, my = 0;
    for (const q of pts) { sw += q.p; mx += q.p * q.xy[0]; my += q.p * q.xy[1]; }
    mx /= sw; my /= sw;
    let sxx = 0, syy = 0, sxy = 0;
    for (const q of pts) { const dx = q.xy[0] - mx, dy = q.xy[1] - my; sxx += q.p * dx * dx; syy += q.p * dy * dy; sxy += q.p * dx * dy; }
    const ang = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    const ca = Math.cos(ang), sa = Math.sin(ang);
    const rot = ([x, y]) => [x * ca + y * sa, -x * sa + y * ca];      // u: uzun eksen, v: dik eksen
    const unrot = (u, v) => [u * ca - v * sa, u * sa + v * ca];

    // Her hücre en yakın şeride atanır; şerit = o hücrelerin u aralığı (± yarım hücre)
    let vmin = Infinity, vmax = -Infinity;
    for (const q of pts) { q.uv = rot(q.xy); vmin = Math.min(vmin, q.uv[1]); vmax = Math.max(vmax, q.uv[1]); }
    const nLanes = Math.max(1, Math.ceil((vmax - vmin + G.cell) / spacing));
    const lanes = Array.from({ length: nLanes }, (_, j) => ({ v: vmin - G.cell / 2 + spacing * (j + 0.5), umin: Infinity, umax: -Infinity, cells: [] }));
    for (const q of pts) {
      const j = Math.min(nLanes - 1, Math.max(0, Math.floor((q.uv[1] - vmin + G.cell / 2) / spacing)));
      const L = lanes[j];
      L.umin = Math.min(L.umin, q.uv[0] - G.cell / 2); L.umax = Math.max(L.umax, q.uv[0] + G.cell / 2); L.cells.push(q);
    }
    const used = lanes.filter((L) => L.cells.length);

    const baseXY = toXY(base.lon, base.lat);
    const totalP = area.prob.reduce((s, x) => s + x, 0);
    function simulate(order) {
      // Biçerdöver: şeritler sırayla, yön her şeritte değişir
      const wps = [], events = [];
      let t = 0, pos = baseXY, firstDir = 1;
      const fly = (xy) => { t += Math.hypot(xy[0] - pos[0], xy[1] - pos[1]) / o.speedMs; pos = xy; };
      order.forEach((L, n) => {
        const dir = (n % 2 === 0 ? 1 : -1) * firstDir;
        const u0 = dir > 0 ? L.umin : L.umax, u1 = dir > 0 ? L.umax : L.umin;
        const a = unrot(u0, L.v), b = unrot(u1, L.v);
        fly(a); wps.push(a);
        const tStart = t;
        for (const q of L.cells) events.push({ t: tStart + Math.abs(q.uv[0] - u0) / o.speedMs, p: q.p });
        fly(b); wps.push(b);
      });
      const sweepEnd = t;
      fly(baseXY);
      events.sort((x, y) => x.t - y.t);
      let cum = 0, t50 = null, t90 = null;
      const curve = [];
      for (const e of events) {
        cum += e.p / totalP;
        if (t50 === null && cum >= 0.5) t50 = e.t;
        if (t90 === null && cum >= 0.9 - 1e-6) t90 = e.t;
        if (!curve.length || e.t - curve[curve.length - 1].t > 30) curve.push({ t: e.t / 60, p: cum });
      }
      return { wps, t, sweepEnd, t50, t90: t90 ?? sweepEnd, curve };
    }
    const A = simulate(used), B = simulate(used.slice().reverse());
    const best = (A.t50 ?? Infinity) <= (B.t50 ?? Infinity) ? A : B;
    const minutes = best.t / 60;
    let lengthM = 0, prev = baseXY;
    for (const w of [...best.wps, baseXY]) { lengthM += Math.hypot(w[0] - prev[0], w[1] - prev[1]); prev = w; }
    return {
      waypoints: [[base.lon, base.lat], ...best.wps.map((w) => toLL(w[0], w[1])), [base.lon, base.lat]],
      lanes: used.length, swathM: Math.round(swath), spacingM: Math.round(spacing), headingDeg: Math.round((90 - (ang * 180) / Math.PI + 360) % 180),
      lengthM: Math.round(lengthM), minutes: +minutes.toFixed(1), sorties: Math.ceil(minutes / o.enduranceMin),
      t50: best.t50 !== null ? +(best.t50 / 60).toFixed(1) : null, t90: +(best.t90 / 60).toFixed(1),
      coverage: best.curve, params: o,
    };
  }

  // ---- 3) Arkadaşın kurtarma rotası --------------------------------------------------------
  /*
   * Ali (kurtarıcı) üsten/konumundan hedefe (son bilinen konum) gider, ikisi birlikte üsse döner.
   *   Ali gerekli O₂ = (gidiş + dönüş·1,2) · çarpan_Ali      (giyinme süresi üste, O₂ harcamaz)
   *     YEŞİL ≤ O₂_Ali/1,25 · SARI ≤ O₂_Ali · KIRMIZI üstü  (yedek tüp hesaba katılmaz, o kayıp için)
   *   Kayıp astronotun varışta O₂'si = kalan − (geçen + giyinme + Ali'nin gidişi) · çarpan_kayıp
   *   Üsse varışta = varıştaki − dönüş·1,2 · çarpan_kayıp; yetmezse Ali'nin 60 dk yedek tüpü bağlanır
   */
  function buddyRoute(input) {
    const base = input.base || W().BASE;
    const res = input.rescuer;
    const from = input.from || (res.position ? { lon: res.position.lon, lat: res.position.lat } : base);
    const target = input.target;
    const to = W().path(from, target, { loadKg: res.load_kg });
    const back = W().path(target, base, { loadKg: res.load_kg });
    if (!to.ok || !back.ok) return { ok: false, status: "red", messages: ["Hedefe güvenli rota yok"] };
    const backMin = back.minutes * CARRY_FACTOR;
    const mR = W().o2Multiplier(res.heart_rate);
    const needR = (to.minutes + backMin) * mR;
    const status = needR <= res.o2_min / GREEN_MARGIN ? "green" : needR <= res.o2_min ? "yellow" : "red";

    const mL = W().o2Multiplier(input.lost.heart_rate);
    const arriveAfter = (input.elapsedMin || 0) + DISPATCH_MIN + to.minutes;   // kopmadan bu yana dk
    const lostAtArrival = input.lost.o2LeftMin - arriveAfter * mL;
    const lostAtBase = lostAtArrival - backMin * mL;
    const spareNeeded = lostAtBase < 0;
    const lostAtBaseWithSpare = lostAtBase + (spareNeeded ? SPARE_O2_MIN : 0);
    const messages = [];
    messages.push(`Ali: ${Math.round(to.minutes)} dk gidiş + ${Math.round(backMin)} dk birlikte dönüş; O₂ ihtiyacı ${Math.round(needR)} / ${res.o2_min} dk → ${status === "green" ? "YEŞİL" : status === "yellow" ? "SARI (pay yok)" : "KIRMIZI (Ali de dönemez)"}`);
    if (lostAtArrival <= 0) messages.push(`Ayşe'nin O₂'si Ali varmadan biter (${Math.round(lostAtArrival)} dk) → İHA bulsa bile yetişilemez`);
    else messages.push(`Ali vardığında Ayşe'nin O₂'si ${Math.round(lostAtArrival)} dk`);
    if (lostAtArrival > 0) messages.push(spareNeeded
      ? `Dönüşe yetmez (${Math.round(lostAtBase)} dk); yedek tüp (${SPARE_O2_MIN} dk) bağlanınca üste ${Math.round(lostAtBaseWithSpare)} dk ile varır`
      : `Birlikte üste vardıklarında Ayşe'de ${Math.round(lostAtBase)} dk O₂ kalır`);
    return {
      ok: true, status, from, target, to: to.coords, back: back.coords,
      toMin: Math.round(to.minutes), backMin: Math.round(backMin), distanceM: Math.round(to.distanceM + back.distanceM),
      rescuerNeedMin: Math.round(needR), rescuerO2: res.o2_min,
      arriveAfterMin: Math.round(arriveAfter), lostO2AtArrival: Math.round(lostAtArrival), lostO2AtBase: Math.round(lostAtBase),
      spareNeeded, survivable: lostAtArrival > 0 && lostAtBaseWithSpare >= 0 && status !== "red", messages,
    };
  }

  /** Hepsi bir arada: "Telsiz koptu" butonunun çağıracağı fonksiyon. */
  function respond(input) {
    const t0 = (typeof performance !== "undefined" ? performance : Date).now();
    const area = searchArea(input);
    const drone = droneRoute(area, input.drone);
    const buddy = input.rescuer ? buddyRoute({ rescuer: input.rescuer, lost: input.lost, elapsedMin: input.elapsedMin,
                                                target: input.last, base: input.base, from: input.rescuerFrom }) : null;
    return { area, drone, buddy, ms: (typeof performance !== "undefined" ? performance : Date).now() - t0 };
  }

  root.Rescue = {
    respond, searchArea, droneRoute, buddyRoute,
    ASSUMPTIONS: { ROUTE_BONUS, ROUTE_NEAR_M, DRONE, DISPATCH_MIN, CARRY_FACTOR, SPARE_O2_MIN, GREEN_MARGIN },
  };
  if (typeof module !== "undefined") module.exports = root.Rescue;
})(typeof window !== "undefined" ? window : globalThis);
