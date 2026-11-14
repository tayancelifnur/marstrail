/*
 * MarsTrail – EVA planlayıcı (E11)
 *
 * Duraklar ve kalma süreleri → gidiş/dönüş rotaları, zaman çizelgesi, dönüş noktası, Go/No-Go.
 * Gerekenler: walkback.js (Walkback.load çağrılmış olmalı), isteğe bağlı marstime.js (gün batımı, LMST).
 * Formüller docs/PLAN.md §3.5 ve §5. Bütün katsayılar VARSAYIMDIR; kodda gerekçesiyle yazıldı.
 *
 * Kullanım:
 *   await Walkback.load("data/grid.json");
 *   const plan = Eva.plan({
 *     astronaut: ayse,                                    // astronauts.json kaydı (o2_min, heart_rate, load_kg, battery_pct, water_pct …)
 *     stops: [ {id:"delta_front", name:"Delta önü", lon:77.40519, lat:18.44941, dwellMin:40, sampleKg:1},
 *              {id:"three_forks", name:"Three Forks", lon:77.40776, lat:18.45263, dwellMin:30, sampleKg:1} ],
 *     departUTC: Eva.nextWindow(new Date()),             // isteğe bağlı; yoksa şimdi
 *   });
 *   plan.legs[i].coords        → [[lon,lat,elev],…] her bacak (son bacak = dönüş, ayrı çizilebilir)
 *   plan.timeline              → [{t, type, name, utc, lmst, o2Left}]   zaman çizelgesi
 *   plan.turnaround            → {lon,lat,t,…} | null   "Burayı geçersen O₂ dönüşe yetmez"
 *   plan.marginPoint           → {lon,lat,t,…} | null   "Burayı geçersen %25 pay kalmaz"
 *   plan.goNoGo                → [{id,label,status:"ok"|"warn"|"fail",detail}]   plan.go → true/false
 *   plan.totals                → {minutes, walkMin, distanceM, o2UsedMin, o2LeftMin, o2LeftPct, batteryPct, waterPct}
 *   Eva.positionAt(plan, tMin) → {lon,lat,phase,leg,o2Left}   canlı yürüyüş (G7) için
 */
(function (root) {
  "use strict";

  // ---- Varsayımlar -------------------------------------------------------------------------
  const FATIGUE_PER_HOUR = 0.05;  // yürüme süresi her geçen saat için %5 uzar (yorgunluk). SEXTANT saha testinde
                                  // gerçek süre tahminden uzun çıktı; sabit hız varsayımını bu terimle gevşetiyoruz.
  const SAMPLE_KG = 1;            // durak başına toplanan numune (kg), dönüşte yük artar (PLAN §3.5)
  const GREEN_RESERVE = 0.25;     // dönüşte O₂'nin en az %25'i kalmalı (yeşil bölge kuralıyla aynı pay)
  const BATTERY_PER_H = 12.5;     // %/saat: giysi bataryası ~8 saat (xEMU sınıfı varsayım)
  const WATER_PER_H = 12.5;       // %/saat: içme suyu ~8 saat (varsayım)
  const BATTERY_MIN = 20, WATER_MIN = 10;   // dönüşte kalması gereken alt sınır (%)
  const SUNSET_MARGIN_MIN = 30;   // gün batımından en az 30 Dünya dakikası önce üste olunmalı
  const MAST_H = 10, SUIT_H = 2;  // telsiz: habitat anteni 10 m, giysi anteni 2 m (görüş hattı varsayımı)
  const MARS_R = 3389500;         // m, eğrilik düzeltmesi için ortalama yarıçap
  const STEEP_WARN_DEG = 15;      // rotada bu eğimi aşan kenar varsa uyarı (geçilmez sınır 25°, walkback.js)

  const W = () => root.Walkback;
  const MT = () => root.MarsTime;

  // O₂ çarpanı: tüketim = taban × (1 + (nabız − 90)/100)  (walkback.js ile aynı formül)
  const o2Mult = (hr) => W().o2Multiplier(hr);

  /** Yorgunluk çarpanı: bacak başladığında geçen saat kadar yavaşlama → 1 + 0,05 · saat */
  const fatigue = (tMin) => 1 + FATIGUE_PER_HOUR * (tMin / 60);

  // ---- Telsiz görüş hattı ------------------------------------------------------------------
  /*
   * Habitat anteni (üs + 10 m) ile astronot (zemin + 2 m) arasındaki doğru, aradaki arazinin
   * üstünde mi? Arazi örnekleri hücre aralıklarıyla alınır; Mars eğriliği için her örneğe
   * "tümsek" eklenir: h = d1 · d2 / (2R)  (d1, d2 = örneğin iki uca uzaklığı).
   */
  function lineOfSight(base, p) {
    const G = W().grid;
    const ib = W().cellOf(base), ip = W().cellOf(p);
    if (ib < 0 || ip < 0) return false;
    const zb = G.elev[ib] + MAST_H, zp = G.elev[ip] + SUIT_H;
    const dx = (p.lon - base.lon) * Math.cos((base.lat * Math.PI) / 180), dy = p.lat - base.lat;
    const D = Math.hypot(dx, dy) * 59274.7; // derece → m (Mars 2000 küresi, 2πR/360)
    const n = Math.max(2, Math.ceil(D / G.cell));
    for (let k = 1; k < n; k++) {
      const f = k / n;
      const q = { lon: base.lon + (p.lon - base.lon) * f, lat: base.lat + (p.lat - base.lat) * f };
      const i = W().cellOf(q);
      if (i < 0) continue;
      const bulge = (f * D * (1 - f) * D) / (2 * MARS_R);
      if (G.elev[i] + bulge > zb + (zp - zb) * f) return false;
    }
    return true;
  }

  // ---- Zaman yardımcıları ------------------------------------------------------------------
  const addMin = (date, m) => new Date(date.getTime() + m * 60000);
  function clock(date) {
    const mt = MT();
    const t = mt ? mt.at(date) : null;
    return { utc: date.toISOString(), lmst: t ? t.lmst : null, isDay: t ? t.isDay : null,
             minutesToSunset: t ? t.minutesToSunset : null, sunsetLMST: t ? t.sunsetLMST : null };
  }

  /** Jezero'da yerel gerçek güneş saati (LTST) 09:00'a denk gelen ilk an: güvenli çıkış penceresi. */
  function nextWindow(from, ltstHour) {
    const target = ltstHour ?? 9;
    const mt = MT();
    if (!mt) return from || new Date();
    let d = new Date((from || new Date()).getTime());
    for (let k = 0; k < 24 * 6 * 3; k++) {          // 10 dk adımlarla en fazla 3 gün
      const t = mt.at(d);
      if (t.isDay && Math.abs(t.ltstHours - target) < 0.1) return d;
      d = addMin(d, 10);
    }
    return from || new Date();
  }

  // ---- Plan --------------------------------------------------------------------------------
  function plan(input) {
    const a = input.astronaut;
    const base = input.base || W().BASE;
    const start = input.start || base;
    const stops = input.stops || [];
    const depart = input.departUTC ? new Date(input.departUTC) : new Date();
    const hr = a.heart_rate ?? 90;
    const m = o2Mult(hr);
    const o2 = a.o2_min;

    // Bacaklar: başlangıç → durak1 → … → durakN → üs. Son bacak dönüş; rotası ayrıca hesaplanır
    // (yönlü eğim: yokuşlar ters döner) ve toplanan numuneler kadar ağırdır.
    const points = [start, ...stops, base];
    const legs = [], timeline = [];
    let t = 0, load = a.load_kg || 0, dist = 0, walkMin = 0;
    const o2Left = (tm) => o2 - tm * m;
    const ev = (type, name, tm, extra) => timeline.push(Object.assign(
      { t: Math.round(tm), type, name, o2Left: Math.round(o2Left(tm)) }, clock(addMin(depart, tm)), extra || {}));

    ev("depart", input.startName || "Üs", 0);
    for (let k = 0; k < points.length - 1; k++) {
      const from = points[k], to = points[k + 1];
      const r = W().path(from, to, { loadKg: load });
      if (!r.ok) return { ok: false, error: `Rota bulunamadı: ${from.name || "başlangıç"} → ${to.name || "üs"}` };
      // Bacak süresi = Dijkstra süresi × yorgunluk(bacak başı)
      const fat = fatigue(t);
      const minutes = r.minutes * fat;
      const leg = {
        index: k, from: from.name || input.startName || "Üs", to: to.name || "Üs",
        isReturn: k === points.length - 2, loadKg: load, fatigue: +fat.toFixed(3),
        startMin: t, endMin: t + minutes, minutes, distanceM: r.distanceM,
        coords: r.coords, minutesAt: r.minutesAt.map((x) => t + x * fat), cells: r.cells,
        o2Used: minutes * m,
      };
      legs.push(leg);
      t += minutes; dist += r.distanceM; walkMin += minutes;
      if (k < stops.length) {
        const s = stops[k];
        ev("arrive", s.name, t, { stopId: s.id });
        t += s.dwellMin || 0;
        load += s.sampleKg ?? SAMPLE_KG;                 // numune toplandı → sonraki bacaklar daha ağır
        ev("leave", s.name, t, { stopId: s.id, dwellMin: s.dwellMin || 0 });
      }
    }
    ev("return", "Üs", t);

    const turn = findTurnaround(legs, base, o2, m, 1);
    const marginPt = findTurnaround(legs, base, o2, m, 1 - GREEN_RESERVE);
    const totals = {
      minutes: Math.round(t), walkMin: Math.round(walkMin), distanceM: Math.round(dist),
      o2UsedMin: Math.round(t * m), o2LeftMin: Math.round(o2Left(t)),
      o2LeftPct: Math.round((o2Left(t) / (a.o2_capacity_min || o2)) * 100),
      batteryPct: Math.round((a.battery_pct ?? 100) - (BATTERY_PER_H * t) / 60),
      waterPct: Math.round((a.water_pct ?? 100) - (WATER_PER_H * t) / 60),
      multiplier: m,
    };
    const goNoGo = checks({ a, legs, totals, timeline, depart, base, t, o2, turn });
    return {
      ok: true, depart: depart.toISOString(), legs, timeline, totals, goNoGo,
      go: goNoGo.every((c) => c.status !== "fail"),
      turnaround: turn, marginPoint: marginPt,
      coords: legs.flatMap((l, i) => (i ? l.coords.slice(1) : l.coords)),
    };
  }

  /*
   * Dönüş noktası (PLAN §5): rotada "o noktaya kadar harcanan O₂ + oradan üsse dönüş O₂'si"
   * kalan O₂'yi (ya da %75'ini: pay noktası) ilk aştığı yer. Dönüş süresi o anki yük ve
   * yorgunlukla hesaplanır:
   *   gerekli(p) = t(p)·çarpan + üsseSüre(p, yük)·yorgunluk(t)·çarpan
   *   gerekli(p) > O₂ · oran  →  bir önceki nokta dönüş noktasıdır
   * Plan baştan sona güvenliyse null döner (dönüş noktası yok: her yerden geri dönülebilir).
   */
  function findTurnaround(legs, base, o2, m, ratio) {
    let prev = null;
    for (const leg of legs) {
      for (let k = 0; k < leg.coords.length; k++) {
        const [lon, lat] = leg.coords[k];
        const tm = leg.minutesAt[k];
        const home = W().timeHome({ lon, lat }, { loadKg: leg.loadKg, base }) * fatigue(tm);
        const need = (tm + home) * m;
        if (need > o2 * ratio) {
          const p = prev || { lon, lat, t: tm, leg: leg.index };
          return Object.assign({}, p, { ratio, needMin: Math.round(need), limitMin: Math.round(o2 * ratio) });
        }
        prev = { lon, lat, t: Math.round(tm), leg: leg.index, homeMin: Math.round(home) };
      }
    }
    return null;
  }

  /** Go/No-Go listesi: ok = yeşil, warn = dikkat (plan sürer), fail = kırmızı (plan iptal). */
  function checks({ a, legs, totals, timeline, depart, base, t, o2, turn }) {
    const G = W().grid;
    const out = [];
    const add = (id, label, status, detail) => out.push({ id, label, status, detail });
    const fmt = (min) => `${Math.floor(min / 60)} sa ${Math.round(min % 60)} dk`;

    // 1) O₂: dönüşte en az %25 pay
    const reservePct = (totals.o2LeftMin / o2) * 100;
    add("o2", "O₂ yeterli (%25 pay)", turn ? "fail" : reservePct >= GREEN_RESERVE * 100 ? "ok" : "fail",
      turn ? `Dönüş noktası rotada: ${fmt(turn.t)} sonra O₂ dönüşe yetmiyor`
        : `Dönüşte ${totals.o2LeftMin} dk O₂ kalıyor (%${Math.round(reservePct)}; çarpan ×${totals.multiplier.toFixed(2)})`);

    // 2) Gün batımı: çıkış gündüz, dönüş gün batımından ≥ 30 dk önce
    const back = timeline[timeline.length - 1];
    if (back.minutesToSunset != null) {
      const d0 = clock(depart);
      const ok = d0.isDay && back.isDay && back.minutesToSunset >= SUNSET_MARGIN_MIN;
      add("sunset", "Gün batımından önce dönüş", ok ? "ok" : "fail",
        `Çıkış ${d0.lmst} LMST, dönüş ${back.lmst} LMST, gün batımı ${back.sunsetLMST} LMST` +
        (back.isDay ? ` (${fmt(back.minutesToSunset)} pay)` : " (dönüş karanlıkta)"));
    }

    // 3) Arazi: rotada kum ve dik kenar
    let sandM = 0, steep = 0, maxDeg = 0;
    for (const leg of legs) {
      for (let k = 1; k < leg.cells.length; k++) {
        const u = leg.cells[k - 1], v = leg.cells[k];
        const diag = (u % G.w !== v % G.w) && (((u / G.w) | 0) !== ((v / G.w) | 0));
        const d = diag ? G.cell * Math.SQRT2 : G.cell;
        if (G.sand[v]) sandM += d;
        const deg = (Math.atan(Math.abs(G.elev[v] - G.elev[u]) / d) * 180) / Math.PI;
        maxDeg = Math.max(maxDeg, deg);
        if (deg > STEEP_WARN_DEG) steep++;
      }
    }
    add("sand", "Kum tuzağı yok", sandM > 0 ? "warn" : "ok",
      sandM > 0 ? `Rotanın ~${Math.round(sandM)} m'si eolyen kum biriminde (Opportunity/Spirit riski; yavaş geç)` : "Rotada eolyen kum birimi yok");
    add("slope", "Geçilmez eğim yok", steep ? "warn" : "ok",
      `En dik geçiş ${maxDeg.toFixed(1)}° (sınır 25°, rota zaten geçilmezden kaçıyor)` + (steep ? `; ${steep} kenar >${STEEP_WARN_DEG}°` : ""));

    // 4) Telsiz: habitatla görüş hattı (her ~3 hücrede bir örnek)
    let shadowMin = 0, firstShadow = null, samples = 0;
    for (const leg of legs) {
      for (let k = 0; k < leg.coords.length; k += 3) {
        const [lon, lat] = leg.coords[k];
        samples++;
        if (!lineOfSight(base, { lon, lat })) {
          const next = leg.minutesAt[Math.min(k + 3, leg.minutesAt.length - 1)];
          shadowMin += next - leg.minutesAt[k];
          if (!firstShadow) firstShadow = { lon, lat, t: Math.round(leg.minutesAt[k]) };
        }
      }
    }
    add("radio", "Telsiz bağlantısı kesilmiyor", firstShadow ? "warn" : "ok",
      firstShadow ? `~${Math.round(shadowMin)} dk habitat anteniyle görüş yok (ilk: çıkıştan ${firstShadow.t} dk sonra); arkadaş röle olmalı`
        : `Rotanın tamamı habitat anteniyle görüş hattında (${samples} örnek)`);
    if (firstShadow) out[out.length - 1].firstShadow = firstShadow;

    // 5) Batarya ve su
    add("battery", "Batarya yeterli", totals.batteryPct >= BATTERY_MIN ? "ok" : "fail",
      `Dönüşte %${totals.batteryPct} (alt sınır %${BATTERY_MIN}; ${BATTERY_PER_H}%/sa varsayımı)`);
    add("water", "Su yeterli", totals.waterPct >= WATER_MIN ? "ok" : "fail",
      `Dönüşte %${totals.waterPct} (alt sınır %${WATER_MIN})`);
    return out;
  }

  /** Canlı yürüyüş için: plan başlangıcından tMin dakika sonra astronot nerede, ne yapıyor? */
  function positionAt(p, tMin) {
    const o2Left = Math.round(o2At(p, tMin));
    // 1) Bir bacakta yürüyor mu? Hücre varış süreleri arasında doğrusal ara değer.
    for (const leg of p.legs) {
      if (tMin >= leg.startMin && tMin <= leg.endMin) {
        const ts = leg.minutesAt;
        let k = 0;
        while (k < ts.length - 2 && ts[k + 1] < tMin) k++;
        const span = ts[k + 1] - ts[k];
        const f = span > 0 ? Math.min(1, Math.max(0, (tMin - ts[k]) / span)) : 0;
        const c0 = leg.coords[k], c1 = leg.coords[k + 1] || c0;
        return { lon: c0[0] + (c1[0] - c0[0]) * f, lat: c0[1] + (c1[1] - c0[1]) * f, elev: c0[2] + (c1[2] - c0[2]) * f,
                 phase: "walk", leg: leg.index, to: leg.to, o2Left };
      }
    }
    // 2) Yürümüyorsa: son biten bacağın sonunda (durakta bekliyor ya da plan bitti)
    const done = p.legs.filter((l) => l.endMin <= tMin).pop() || p.legs[0];
    const end = done.coords[done.coords.length - 1];
    const finished = tMin >= p.totals.minutes;
    return { lon: end[0], lat: end[1], elev: end[2], phase: finished ? "done" : "dwell",
             leg: done.index, at: done.to, o2Left };
  }
  const o2At = (p, tMin) => p.timeline[0].o2Left - tMin * p.totals.multiplier;

  root.Eva = {
    plan, positionAt, nextWindow, lineOfSight,
    ASSUMPTIONS: { FATIGUE_PER_HOUR, SAMPLE_KG, GREEN_RESERVE, BATTERY_PER_H, WATER_PER_H, BATTERY_MIN, WATER_MIN,
                   SUNSET_MARGIN_MIN, MAST_H, SUIT_H, STEEP_WARN_DEG },
  };
  if (typeof module !== "undefined") module.exports = root.Eva;
})(typeof window !== "undefined" ? window : globalThis);
