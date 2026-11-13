/**
 * Live Climate, Soil & In-Browser FAO-56 Simulation Connector for Global Coordinates.
 *
 * Pulls multi-year daily meteorology (2021-2023) from NASA POWER, queries live soil
 * properties from USDA-NRCS SSURGO (US) or ISRIC SoilGrids 2.0 (global), and runs
 * an in-browser FAO-56 daily root-zone water balance (Dr, RAW, Ks, ETa, irrigation,
 * RYI) respecting farmer irrigation caps and crop constraints.
 */

import { t } from "./strings";

export interface GlobalEvaluationOptions {
  irrigationBudgetMm?: number;
  cantGrow?: string[];
  organicMatterPct?: number | null;
}

export interface GlobalRotationResult {
  sequence: string[];
  name: string;
  waterDemand: string;
  waterUseMm: number;
  badYearWaterMm: number;
  ryi: number;
  bareMonths: number;
  rationale: string;
}

export interface LiveClimateProfile {
  latitude: number;
  longitude: number;
  source: string;
  yearsEvaluated: number;
  tag: "[D] / [E]";
  annualPrecipitationMm: number;
  annualEtoMm: number;
  waterDeficitMm: number;
  aridityIndex: number;
  climateZone: string;
  simulationMode: string;
  recommendedRotations: GlobalRotationResult[];
  soilContext: {
    source: string;
    tag: "[E]" | "[A]";
    estimatedAweMm: number;
    textureClass: string;
  };
}

interface DailyCropSpec {
  sowDoy: number;
  stages: [number, number, number, number];
  kc: [number, number, number];
  p: number;
  zrMaxM: number;
}

const GLOBAL_CROP_SPECS: Record<string, DailyCropSpec> = {
  winter_wheat: { sowDoy: 280, stages: [160, 70, 40, 25], kc: [0.4, 1.15, 0.3], p: 0.55, zrMaxM: 1.5 },
  durum_wheat: { sowDoy: 300, stages: [110, 60, 40, 25], kc: [0.4, 1.15, 0.3], p: 0.55, zrMaxM: 1.4 },
  sorghum: { sowDoy: 145, stages: [20, 35, 40, 30], kc: [0.3, 1.05, 0.55], p: 0.55, zrMaxM: 1.4 },
  grain_sorghum: { sowDoy: 145, stages: [20, 35, 40, 30], kc: [0.3, 1.05, 0.55], p: 0.55, zrMaxM: 1.4 },
  maize: { sowDoy: 125, stages: [25, 40, 45, 30], kc: [0.3, 1.2, 0.35], p: 0.55, zrMaxM: 1.35 },
  soybean: { sowDoy: 140, stages: [20, 35, 60, 25], kc: [0.4, 1.15, 0.5], p: 0.5, zrMaxM: 1.0 },
  cover_crop: { sowDoy: 255, stages: [30, 45, 90, 25], kc: [0.35, 0.9, 0.45], p: 0.55, zrMaxM: 0.9 },
  chickpea: { sowDoy: 320, stages: [25, 35, 45, 25], kc: [0.4, 1.0, 0.35], p: 0.5, zrMaxM: 0.9 },
  rice: { sowDoy: 135, stages: [30, 30, 60, 30], kc: [1.05, 1.2, 0.7], p: 0.2, zrMaxM: 0.7 },
  pulses: { sowDoy: 150, stages: [20, 30, 40, 20], kc: [0.4, 1.05, 0.35], p: 0.45, zrMaxM: 0.8 },
  fallow: { sowDoy: 1, stages: [365, 0, 0, 0], kc: [0.25, 0.25, 0.25], p: 0.55, zrMaxM: 0.3 },
};

/** FAO-56 Hargreaves daily reference evapotranspiration (ETo, mm/day). */
function estimateDailyEto(lat: number, tmin: number, tmax: number, doy: number): number {
  const tmean = (tmax + tmin) / 2;
  const phi = (Math.max(-65, Math.min(65, lat)) * Math.PI) / 180;
  const delta = 0.409 * Math.sin(((2 * Math.PI) / 365) * doy - 1.39);
  const dr = 1 + 0.033 * Math.cos(((2 * Math.PI) / 365) * doy);
  const tanProd = Math.max(-0.99, Math.min(0.99, -Math.tan(phi) * Math.tan(delta)));
  const ws = Math.acos(tanProd);
  const gsc = 0.082;
  const ra =
    ((24 * 60) / Math.PI) *
    gsc *
    dr *
    (ws * Math.sin(phi) * Math.sin(delta) + Math.cos(phi) * Math.cos(delta) * Math.sin(ws));
  const raMm = Math.max(0, ra * 0.408);
  const td = Math.max(0, tmax - tmin);
  return 0.0023 * (tmean + 17.8) * Math.sqrt(td) * raMm;
}

function buildDailyKcCurve(spec: DailyCropSpec): { kc: number; isCrop: boolean; p: number }[] {
  const days: { kc: number; isCrop: boolean; p: number }[] = [];
  if (spec.stages[0] === 365) {
    for (let d = 0; d < 365; d++) days.push({ kc: 0.25, isCrop: false, p: 0.55 });
    return days;
  }
  const [lIni, lDev, lMid, lLate] = spec.stages;
  const [kcIni, kcMid, kcEnd] = spec.kc;
  for (let d = 0; d < lIni; d++) days.push({ kc: kcIni, isCrop: true, p: spec.p });
  for (let d = 0; d < lDev; d++) {
    const f = (d + 1) / Math.max(1, lDev);
    days.push({ kc: kcIni + f * (kcMid - kcIni), isCrop: true, p: spec.p });
  }
  for (let d = 0; d < lMid; d++) days.push({ kc: kcMid, isCrop: true, p: spec.p });
  for (let d = 0; d < lLate; d++) {
    const f = (d + 1) / Math.max(1, lLate);
    days.push({ kc: kcMid + f * (kcEnd - kcMid), isCrop: true, p: spec.p });
  }
  return days;
}

/** Runs an in-browser 3-year FAO-56 water balance over daily precipitation & ETo series. */
function simulateSequenceDaily(
  sequence: string[],
  yearlyWeather: { rain: number[]; eto: number[] }[],
  tawMm: number,
  irrigationBudgetMm: number,
): { waterUseMm: number; badYearWaterMm: number; ryi: number; bareMonths: number } {
  const nYears = Math.max(1, yearlyWeather.length);
  const totalDays = sequence.length * 365;
  const kcArr = new Float64Array(totalDays).fill(0.25);
  const pArr = new Float64Array(totalDays).fill(0.55);
  const cropFlag = new Uint8Array(totalDays);

  sequence.forEach((cropKey, slotIdx) => {
    const spec = GLOBAL_CROP_SPECS[cropKey] ?? GLOBAL_CROP_SPECS.fallow;
    if (cropKey === "fallow") return;
    const curve = buildDailyKcCurve(spec);
    let startDay = slotIdx * 365 + spec.sowDoy - 1;
    // Autumn-sown winter wheat starts in previous year slot when slotIdx > 0
    if (spec.sowDoy > 250 && slotIdx > 0) {
      startDay -= 365;
    }
    for (let i = 0; i < curve.length; i++) {
      const idx = startDay + i;
      if (idx >= 0 && idx < totalDays) {
        kcArr[idx] = curve[i].kc;
        pArr[idx] = curve[i].p;
        cropFlag[idx] = curve[i].isCrop ? 1 : 0;
      }
    }
  });

  const taw = Math.max(80, Math.min(400, tawMm));
  const yearWaterTotals: number[] = [];
  let sumEta = 0;
  let sumEtc = 0;
  let dr = taw * 0.25;

  for (let yRun = 0; yRun < nYears; yRun++) {
    let runEta = 0;
    for (let t = 0; t < totalDays; t++) {
      const wx = yearlyWeather[(yRun + Math.floor(t / 365)) % nYears];
      const doyIdx = t % 365;
      const rain = wx.rain[doyIdx] ?? 0;
      const eto = wx.eto[doyIdx] ?? 3.5;
      const raw = pArr[t] * taw;
      const isCrop = cropFlag[t] === 1;
      const seasonalDailyCap = isCrop ? irrigationBudgetMm / 120 : 0;
      const irr = isCrop && dr > raw ? Math.min(dr - raw, seasonalDailyCap) : 0;
      const ks = dr > raw ? Math.max(0, Math.min(1, (taw - dr) / Math.max(1, taw - raw))) : 1;
      const etc = kcArr[t] * eto;
      let eta = ks * etc;
      let nextDr = Math.max(0, dr - rain - irr + eta);
      if (nextDr > taw) {
        eta = Math.max(0, eta - (nextDr - taw));
        nextDr = taw;
      }
      dr = nextDr;
      runEta += eta;
      if (isCrop) {
        sumEta += eta;
        sumEtc += etc;
      }
    }
    yearWaterTotals.push(runEta);
  }

  let bareDays = 0;
  for (let t = 0; t < totalDays; t++) {
    if (!cropFlag[t]) bareDays++;
  }

  const avgWater = yearWaterTotals.reduce((a, b) => a + b, 0) / yearWaterTotals.length;
  const maxWater = Math.max(...yearWaterTotals);
  const ryi = sumEtc > 0 ? Math.max(0.05, Math.min(1.0, sumEta / sumEtc)) : 0.0;
  return {
    waterUseMm: Math.round(avgWater),
    badYearWaterMm: Math.round(maxWater),
    ryi: Number(ryi.toFixed(2)),
    bareMonths: Math.round(bareDays / 30.4),
  };
}

function classifyTexture(sandPct: number, clayPct: number): string {
  if (sandPct > 70 && clayPct < 15) return t("live.texture.sandyLoam");
  if (clayPct >= 35) return t("live.texture.clay");
  if (sandPct < 35 && clayPct < 27) return t("live.texture.siltLoam");
  return t("live.texture.loam");
}

async function fetchLiveSoilContext(
  lat: number,
  lon: number,
  organicMatterPct?: number | null,
): Promise<LiveClimateProfile["soilContext"]> {
  const omBonus = organicMatterPct && organicMatterPct > 0 ? Math.max(0, (organicMatterPct - 2.0) * 12) : 0;
  const inConus = lon >= -125 && lon <= -66 && lat >= 24 && lat <= 50;

  if (inConus) {
    try {
      const wkt = `POINT(${lon.toFixed(5)} ${lat.toFixed(5)})`;
      const query = `SELECT TOP 1 m.mukey, m.muname, a.aws0150wta FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('${wkt}') AS s JOIN mapunit AS m ON s.mukey = m.mukey JOIN muaggatt AS a ON m.mukey = a.mukey WHERE a.aws0150wta IS NOT NULL`;
      const res = await fetch("https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, format: "JSON" }),
        signal: AbortSignal.timeout(4500),
      });
      if (res.ok) {
        const data = await res.json();
        const row = data?.Table?.[0];
        const awsCm = Number(row?.[2]);
        if (Number.isFinite(awsCm) && awsCm > 1) {
          return {
            source: t("live.soilSrc.ssurgo", { name: String(row?.[1] || "Soil Survey").slice(0, 40) }),
            tag: "[E]",
            estimatedAweMm: Math.round(awsCm * 10 + omBonus),
            textureClass: String(row?.[1] || "SSURGO Surveyed Soil").slice(0, 42),
          };
        }
      }
    } catch {
      // Fall through to SoilGrids
    }
  }

  try {
    const sgUrl = `https://rest.isric.org/soilgrids/v2.0/properties/query?lon=${lon.toFixed(4)}&lat=${lat.toFixed(4)}&property=sand&property=clay&property=wv0033&property=wv1500&depth=30-60cm&value=mean`;
    const res = await fetch(sgUrl, { signal: AbortSignal.timeout(4500) });
    if (res.ok) {
      const data = await res.json();
      const layers = (data?.properties?.layers ?? []) as { name: string; depths?: { values?: { mean?: number } }[] }[];
      const val = (name: string): number | null => {
        const l = layers.find((x) => x.name === name);
        const m = l?.depths?.[0]?.values?.mean;
        return typeof m === "number" && Number.isFinite(m) ? m : null;
      };
      const sandRaw = val("sand");
      const clayRaw = val("clay");
      const fcRaw = val("wv0033");
      const wpRaw = val("wv1500");
      const sandPct = sandRaw != null ? sandRaw / 10 : 30;
      const clayPct = clayRaw != null ? clayRaw / 10 : 25;
      // SoilGrids volumetric water (10^-3 cm3/cm3) scaled over 1.35 m effective root depth
      let awsMm =
        fcRaw != null && wpRaw != null && fcRaw > wpRaw
          ? Math.round(((fcRaw - wpRaw) / 1000) * 1350)
          : Math.round(160 + (100 - sandPct) * 0.8);
      awsMm = Math.max(95, Math.min(340, awsMm + Math.round(omBonus)));
      if (sandRaw != null || fcRaw != null) {
        return {
          source: t("live.soilSrc.soilgrids"),
          tag: "[E]",
          estimatedAweMm: awsMm,
          textureClass: classifyTexture(sandPct, clayPct),
        };
      }
    }
  } catch {
    // Graceful fallback when offline/blocked
  }

  const inPilotKs = Math.abs(lon - -101) < 2 && Math.abs(lat - 38.5) < 2;
  return {
    source: inPilotKs ? t("live.soilSrc.ksMedian") : t("live.soilSrc.prior"),
    tag: inPilotKs ? "[E]" : "[A]",
    estimatedAweMm: (inPilotKs ? 282 : 180) + Math.round(omBonus),
    textureClass: inPilotKs ? t("live.texture.ksMedian") : t("live.texture.prior"),
  };
}

function selectCandidatePool(
  aridityIndex: number,
  lat: number,
  cantGrow: Set<string>,
): { sequence: string[]; name: string; waterDemand: string; rationale: string }[] {
  const isTropical = Math.abs(lat) < 23.5;
  const isMediterranean = Math.abs(lat) >= 30 && Math.abs(lat) <= 42;
  let pool: { sequence: string[]; name: string; waterDemand: string; rationale: string }[];

  if (aridityIndex < 0.35) {
    pool = [
      {
        sequence: ["winter_wheat", "sorghum", "fallow"],
        name: t("live.rot.wheatSorghumFallow"),
        waterDemand: "Low dryland",
        rationale: t("live.rat.aridWsf"),
      },
      {
        sequence: ["winter_wheat", "fallow", "winter_wheat"],
        name: t("live.rot.wheatFallow"),
        waterDemand: "Low dryland",
        rationale: t("live.rat.aridWf"),
      },
      {
        sequence: ["sorghum", "fallow", "cover_crop"],
        name: t("live.rot.sorghumFallowCover"),
        waterDemand: "Moderate",
        rationale: t("live.rat.aridSfc"),
      },
    ];
  } else if (aridityIndex < 0.65) {
    pool = [
      {
        sequence: ["winter_wheat", "maize", "soybean"],
        name: t("live.rot.wheatMaizeSoybean"),
        waterDemand: "Moderate",
        rationale: t("live.rat.subWms"),
      },
      {
        sequence: ["winter_wheat", "sorghum", "fallow"],
        name: t("live.rot.wheatSorghumFallow"),
        waterDemand: "Low-Moderate",
        rationale: t("live.rat.subWsf"),
      },
      {
        sequence: ["maize", "soybean", "cover_crop"],
        name: t("live.rot.maizeSoybeanCover"),
        waterDemand: "Moderate-High",
        rationale: t("live.rat.subMsc"),
      },
    ];
  } else {
    pool = [
      {
        sequence: ["maize", "soybean", "cover_crop"],
        name: t("live.rot.maizeSoybeanCover"),
        waterDemand: "High",
        rationale: t("live.rat.humMsc"),
      },
      {
        sequence: isTropical
          ? ["rice", "maize", "pulses"]
          : isMediterranean
            ? ["durum_wheat", "chickpea", "fallow"]
            : ["winter_wheat", "maize", "soybean"],
        name: isTropical
          ? t("live.rot.riceMaizePulses")
          : isMediterranean
            ? t("live.rot.medWheatChickpea")
            : t("live.rot.wheatMaizeSoybean"),
        waterDemand: "Moderate-High",
        rationale: t("live.rat.humRegion"),
      },
    ];
  }

  const filtered = pool.filter((c) => c.sequence.every((crop) => !cantGrow.has(crop)));
  return filtered.length > 0 ? filtered : pool;
}

function buildSynthesizedBaselineYear(lat: number): { rain: number[]; eto: number[]; annualP: number; annualEto: number } {
  const absLat = Math.abs(lat);
  const annualEtoTarget = Math.max(700, 1800 - absLat * 18);
  let annualPrecipTarget = 450;
  if (absLat < 10) annualPrecipTarget = 1600;
  else if (absLat < 20) annualPrecipTarget = 850;
  else if (absLat < 35) annualPrecipTarget = 420;
  else if (absLat < 50) annualPrecipTarget = 620;

  const rain: number[] = [];
  const eto: number[] = [];
  for (let d = 0; d < 365; d++) {
    const seasonal = 0.5 + 0.5 * Math.sin(((2 * Math.PI) / 365) * (d - 105) * (lat >= 0 ? 1 : -1));
    eto.push((annualEtoTarget / 365) * (0.45 + 1.1 * seasonal));
    rain.push((annualPrecipTarget / 365) * (0.5 + seasonal));
  }
  return { rain, eto, annualP: annualPrecipTarget, annualEto: annualEtoTarget };
}

/**
 * Fetches multi-year NASA POWER climate (2021-2023) + live soil context for any global
 * coordinate and simulates candidate 3-season rotations via the FAO-56 daily water balance.
 */
export async function fetchLiveClimateProfile(
  lat: number,
  lon: number,
  options: GlobalEvaluationOptions = {},
): Promise<LiveClimateProfile> {
  const url = `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG&longitude=${lon.toFixed(4)}&latitude=${lat.toFixed(4)}&start=20210101&end=20231231&format=JSON`;

  const soilPromise = fetchLiveSoilContext(lat, lon, options.organicMatterPct);
  let yearlyWeather: { rain: number[]; eto: number[] }[] = [];
  let annualPrecip = 0;
  let annualEto = 0;
  let usedApi = false;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(6500) });
    if (res.ok) {
      const data = await res.json();
      const pData = data?.properties?.parameter?.PRECTOTCORR;
      const tmaxData = data?.properties?.parameter?.T2M_MAX;
      const tminData = data?.properties?.parameter?.T2M_MIN;

      if (pData && tmaxData && tminData) {
        const byYear = new Map<string, { rain: number[]; eto: number[] }>();
        const keys = Object.keys(pData).sort();
        for (let i = 0; i < keys.length; i++) {
          const k = keys[i];
          const yr = k.slice(0, 4);
          const bucket = byYear.get(yr) ?? { rain: [], eto: [] };
          const p = Number(pData[k]);
          const tmax = Number(tmaxData[k]);
          const tmin = Number(tminData[k]);
          bucket.rain.push(Number.isFinite(p) && p >= 0 ? p : 0);
          const doy = (bucket.eto.length % 365) + 1;
          bucket.eto.push(
            Number.isFinite(tmax) && Number.isFinite(tmin) && tmax > -50 && tmin > -50
              ? estimateDailyEto(lat, tmin, tmax, doy)
              : 3.0,
          );
          byYear.set(yr, bucket);
        }
        const completeYears = [...byYear.values()].filter((y) => y.rain.length >= 300);
        if (completeYears.length > 0) {
          yearlyWeather = completeYears.map((y) => ({
            rain: y.rain.slice(0, 365),
            eto: y.eto.slice(0, 365),
          }));
          annualPrecip = Math.round(
            yearlyWeather.reduce((s, y) => s + y.rain.reduce((a, b) => a + b, 0), 0) / yearlyWeather.length,
          );
          annualEto = Math.round(
            yearlyWeather.reduce((s, y) => s + y.eto.reduce((a, b) => a + b, 0), 0) / yearlyWeather.length,
          );
          usedApi = true;
        }
      }
    }
  } catch {
    // Graceful offline fallback below
  }

  if (!usedApi) {
    const base = buildSynthesizedBaselineYear(lat);
    annualPrecip = base.annualP;
    annualEto = base.annualEto;
    yearlyWeather = [
      { rain: base.rain, eto: base.eto },
      { rain: base.rain.map((r) => r * 0.78), eto: base.eto.map((e) => e * 1.07) },
      { rain: base.rain.map((r) => r * 1.15), eto: base.eto.map((e) => e * 0.96) },
    ];
  }

  const soilContext = await soilPromise;
  const waterDeficit = Math.max(0, annualEto - annualPrecip);
  const aridityIndex = Math.round((annualPrecip / Math.max(1, annualEto)) * 100) / 100;

  let climateZone = t("live.zone.semiArid");
  if (aridityIndex < 0.2) climateZone = t("live.zone.hyperArid");
  else if (aridityIndex < 0.4) climateZone = t("live.zone.semiArid");
  else if (aridityIndex < 0.65) climateZone = t("live.zone.drySubHumid");
  else climateZone = t("live.zone.humid");

  const cantGrow = new Set(options.cantGrow ?? []);
  const irrBudget = Math.max(0, options.irrigationBudgetMm ?? 0);
  const candidates = selectCandidatePool(aridityIndex, lat, cantGrow);

  const recommendedRotations: GlobalRotationResult[] = candidates
    .map((c) => {
      const sim = simulateSequenceDaily(c.sequence, yearlyWeather, soilContext.estimatedAweMm, irrBudget);
      return {
        ...c,
        waterUseMm: sim.waterUseMm,
        badYearWaterMm: sim.badYearWaterMm,
        ryi: sim.ryi,
        bareMonths: sim.bareMonths,
      };
    })
    .sort((a, b) => b.ryi - a.ryi || a.waterUseMm - b.waterUseMm);

  return {
    latitude: lat,
    longitude: lon,
    source: usedApi ? t("live.source.api") : t("live.source.baseline"),
    yearsEvaluated: yearlyWeather.length,
    tag: "[D] / [E]",
    annualPrecipitationMm: annualPrecip,
    annualEtoMm: annualEto,
    waterDeficitMm: waterDeficit,
    aridityIndex,
    climateZone,
    simulationMode: usedApi ? t("live.mode.fao56") : t("live.mode.baseline"),
    recommendedRotations,
    soilContext,
  };
}
