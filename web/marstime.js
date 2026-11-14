/*
 * MarsTrail – Mars saati ve Dünya–Mars gecikmesi (E8)
 *
 * Kaynak: NASA GISS Mars24 algoritması (Allison ve McEwen 2000; Allison 1997)
 *   https://www.giss.nasa.gov/tools/mars24/help/algorithm.html
 * Gezegen konumları: JPL "Keplerian Elements for Approximate Positions of the Major Planets"
 *   (Standish), Tablo 1, 1800–2050 için geçerli. https://ssd.jpl.nasa.gov/planets/approx_pos.html
 *
 * Kullanım (tarayıcı):
 *   const t = MarsTime.now();               // şimdi, Jezero (üs) için
 *   t.lmst          → "13:10"               // Jezero yerel ortalama güneş saati (LMST)
 *   t.sol           → 2085                  // Perseverance görev Sol'ü (iniş = Sol 0)
 *   t.delayMin      → 12.4                  // Dünya–Mars tek yön ışık gecikmesi, dakika
 *   t.minutesToSunset → 215                 // gün batımına kalan DÜNYA dakikası (gün battıysa 0)
 *   MarsTime.at(new Date("2022-12-20T16:07:19Z"))  // herhangi bir an
 *   MarsTime.at(date, { lonE: 77.40, latN: 18.45 }) // başka bir nokta
 *
 * Doğrulama (web/tests/e8.html): D7 fotoğraf kaydı 2022-12-20T16:07:19Z = Sol 652, LMST 13:10:20;
 * Ingenuity Uçuş 1, 2021-04-19T07:34Z = LMST 12:33.
 */
(function (root) {
  "use strict";

  const D2R = Math.PI / 180;
  const sinD = (x) => Math.sin(x * D2R);
  const cosD = (x) => Math.cos(x * D2R);
  const mod = (x, m) => ((x % m) + m) % m;

  // Jezero / Octavia E. Butler iniş noktası (D1, Sol 13 kaydı = iniş yeri)
  const JEZERO = { lonE: 77.4509, latN: 18.4446 };
  // Perseverance inişi: 18 Şubat 2021 20:55 UTC → Sol 0
  const M2020_LANDING = Date.UTC(2021, 1, 18, 20, 55, 0);

  const SOL_SECONDS = 88775.244;            // 1 Mars günü (sol) = 88775,244 Dünya saniyesi
  const EARTH_MIN_PER_MARS_HOUR = SOL_SECONDS / 24 / 60; // ≈ 61,65 Dünya dakikası
  // TT − UTC = 32,184 s + artık saniyeler (2017'den beri 37) = 69,184 s
  const TT_MINUS_UTC = 69.184;
  const AU_KM = 149597870.7;
  const C_KM_S = 299792.458;

  /** Mars24 çekirdeği: bir UTC anı için Mars güneş zamanı büyüklükleri. */
  function mars24(ms) {
    // A-1/A-2: Julian tarihi (UT) ve Karasal Zaman (TT)
    const jdUT = 2440587.5 + ms / 86400000;
    const jdTT = jdUT + TT_MINUS_UTC / 86400;
    // A-3: J2000'den bu yana geçen gün (TT)
    const dt = jdTT - 2451545.0;

    // B-1: Mars'ın ortalama anomalisi M (derece)
    const M = 19.3871 + 0.52402073 * dt;
    // B-2: Kurgusal ortalama güneşin açısı αFMS (derece)
    const alphaFMS = 270.3871 + 0.524038496 * dt;
    // B-3: Gezegen pertürbasyonları PBS = Σ A·cos(0,985626°·Δt/τ + φ)
    const A = [0.0071, 0.0057, 0.0039, 0.0037, 0.0021, 0.0020, 0.0018];
    const tau = [2.2353, 2.7543, 1.1177, 15.7866, 2.1354, 2.4694, 32.8493];
    const phi = [49.409, 168.173, 191.837, 21.736, 15.704, 95.528, 49.095];
    let PBS = 0;
    for (let i = 0; i < 7; i++) PBS += A[i] * cosD((0.985626 * dt) / tau[i] + phi[i]);
    // B-4: Merkez denklemi (ν − M) = gerçek anomali − ortalama anomali
    const nuM = (10.691 + 3.0e-7 * dt) * sinD(M) + 0.623 * sinD(2 * M) + 0.050 * sinD(3 * M)
      + 0.005 * sinD(4 * M) + 0.0005 * sinD(5 * M) + PBS;
    // B-5: Güneş merkezli boylam Ls (mevsim; 0° = kuzey ilkbaharı)
    const Ls = mod(alphaFMS + nuM, 360);

    // C-1: Zaman denklemi EOT (derece) = gerçek − ortalama güneş saati farkı
    const EOT = 2.861 * sinD(2 * Ls) - 0.071 * sinD(4 * Ls) + 0.002 * sinD(6 * Ls) - nuM;
    // C-2: Mars Sol Tarihi MSD (Mars'ın "Julian günü")
    const MSD = (dt - 4.5) / 1.0274912517 + 44796.0 - 0.0009626;
    // C-3: Koordineli Mars Saati MTC (0° boylamın ortalama güneş saati, saat)
    const MTC = mod(24 * MSD, 24);
    // D-1: Güneşin dik açısı (deklinasyon) δs
    const decl = Math.asin(0.42565 * sinD(Ls)) / D2R + 0.25 * sinD(Ls);
    return { jdTT, dt, M, Ls, EOT, MSD, MTC, decl };
  }

  /** Yörünge elemanlarından güneş merkezli ekliptik konum (AU). */
  function helio(el, T) {
    const a = el[0] + el[6] * T, e = el[1] + el[7] * T, I = el[2] + el[8] * T;
    const L = el[3] + el[9] * T, wbar = el[4] + el[10] * T, Om = el[5] + el[11] * T;
    const w = wbar - Om;                   // günberi argümanı
    const Mdeg = mod(L - wbar + 180, 360) - 180; // ortalama anomali, −180..180
    // Kepler denklemi M = E − e·sinE (Newton yinelemesi, derece cinsinden)
    const eDeg = e / D2R;
    let E = Mdeg + eDeg * sinD(Mdeg);
    for (let k = 0; k < 8; k++) E += (Mdeg - (E - eDeg * sinD(E))) / (1 - e * cosD(E));
    // Yörünge düzleminde konum
    const xp = a * (cosD(E) - e), yp = a * Math.sqrt(1 - e * e) * sinD(E);
    // Ekliptik düzleme döndürme (ω, Ω, I)
    const cw = cosD(w), sw = sinD(w), cO = cosD(Om), sO = sinD(Om), cI = cosD(I), sI = sinD(I);
    return [
      (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp,
      (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp,
      sw * sI * xp + cw * sI * yp,
    ];
  }
  // [a, e, I, L, ϖ, Ω] ve yüzyıllık değişimleri (JPL Tablo 1, J2000)
  const EARTH = [1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0,
    0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0];
  const MARS = [1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891,
    0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343];

  /** Dünya–Mars uzaklığı (AU): iki gezegenin güneş merkezli konum farkı. */
  function earthMarsAU(jdTT) {
    const T = (jdTT - 2451545.0) / 36525; // J2000'den bu yana yüzyıl
    const e = helio(EARTH, T), m = helio(MARS, T);
    return Math.hypot(m[0] - e[0], m[1] - e[1], m[2] - e[2]);
  }

  const hhmm = (h) => {
    const m = Math.floor(mod(h, 24) * 60 + 1e-9);
    return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
  };
  const hhmmss = (h) => {
    const s = Math.floor(mod(h, 24) * 3600 + 1e-6);
    return hhmm(h) + ":" + String(s % 60).padStart(2, "0");
  };

  const landingLocalMSD = (() => {
    const m = mars24(M2020_LANDING);
    return m.MSD + JEZERO.lonE / 360;
  })();

  /** Verilen an ve nokta için Mars saati, Sol, gün doğumu/batımı ve gecikme. */
  function at(date, place) {
    const p = Object.assign({}, JEZERO, place || {});
    const ms = date instanceof Date ? date.getTime() : (date ?? Date.now());
    const m = mars24(ms);

    // C-4: Yerel ortalama güneş saati LMST = MTC + doğu boylamı/15 (saat)
    const lmstH = mod(m.MTC + p.lonE / 15, 24);
    // C-5: Yerel gerçek güneş saati LTST = LMST + EOT/15 (EOT dereceden saate: /15)
    const ltstH = mod(lmstH + m.EOT / 15, 24);
    // Perseverance Sol'ü: yerel MSD (= MSD + boylam/360) iniş anındaki yerel MSD'den kaç tam gün ileride
    const localMSD = m.MSD + p.lonE / 360;
    const sol = Math.floor(localMSD) - Math.floor(landingLocalMSD);

    // Gün doğumu/batımı: Güneş merkezi ufukta, cos H0 = −tan φ · tan δs (kırılma ve disk yarıçapı ihmal)
    const cosH0 = -Math.tan(p.latN * D2R) * Math.tan(m.decl * D2R);
    const H0 = Math.acos(Math.max(-1, Math.min(1, cosH0))) / D2R; // derece
    const sunriseLTST = 12 - H0 / 15, sunsetLTST = 12 + H0 / 15;
    // LTST → LMST: LMST = LTST − EOT/15
    const sunriseLMST = mod(sunriseLTST - m.EOT / 15, 24), sunsetLMST = mod(sunsetLTST - m.EOT / 15, 24);
    // Kalan süre Mars saatinden Dünya dakikasına: 1 Mars saati ≈ 61,65 Dünya dakikası
    const leftH = sunsetLTST - ltstH;
    const minutesToSunset = Math.max(0, leftH * EARTH_MIN_PER_MARS_HOUR);

    // Gecikme = uzaklık / ışık hızı
    const distAU = earthMarsAU(m.jdTT);
    const delayMin = (distAU * AU_KM) / C_KM_S / 60;

    return {
      utc: new Date(ms).toISOString(),
      sol,
      lmst: hhmm(lmstH), lmstFull: hhmmss(lmstH), lmstHours: lmstH,
      ltst: hhmm(ltstH), ltstHours: ltstH,
      mtc: hhmm(m.MTC), msd: m.MSD, ls: m.Ls,
      sunriseLMST: hhmm(sunriseLMST), sunsetLMST: hhmm(sunsetLMST),
      minutesToSunset: Math.round(minutesToSunset),
      isDay: ltstH > sunriseLTST && ltstH < sunsetLTST,
      earthMarsAU: distAU, earthMarsKm: distAU * AU_KM, delayMin,
    };
  }

  /** Senaryo Sol'ü: gerçek saati korur, Sol numarasını belirli bir senaryo başlangıcına göre sayar. */
  function scenario(startSol, startDate, date) {
    const now = at(date);
    const start = at(startDate);
    return Object.assign(now, { sol: startSol + (now.sol - start.sol), m2020Sol: now.sol });
  }

  const MarsTime = {
    at, now: (place) => at(Date.now(), place), scenario,
    JEZERO, SOL_SECONDS, EARTH_MIN_PER_MARS_HOUR,
    _mars24: mars24, _earthMarsAU: earthMarsAU,
  };
  root.MarsTime = MarsTime;
  if (typeof module !== "undefined") module.exports = MarsTime;
})(typeof window !== "undefined" ? window : globalThis);
