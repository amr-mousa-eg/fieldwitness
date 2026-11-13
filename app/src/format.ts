import { getLocale, t } from "./strings";
import type { Tagged } from "./types";

const SHARE_UNITS = /^(share|probability)/;

function numberLocale(): string {
  return getLocale() === "ar" ? "ar-EG-u-nu-latn" : "en";
}

function dateLocale(): string {
  return getLocale() === "ar" ? "ar-EG-u-nu-latn" : "en-GB";
}

/** "0.33 share of seasons" -> "33 %"; other units keep their own name. */
export function formatNumber(value: number, unit: string, digits?: number): string {
  const loc = numberLocale();
  if (SHARE_UNITS.test(unit)) return `${Math.round(value * 100)} %`;
  // Below 1, keep two significant digits so small anomalies (0.002 m³/m³) do not print as 0.
  if (digits === undefined && value !== 0 && Math.abs(value) < 1) {
    return value.toLocaleString(loc, { maximumSignificantDigits: 2 });
  }
  const d = digits ?? (Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2);
  return value.toLocaleString(loc, { maximumFractionDigits: d, minimumFractionDigits: 0 });
}

/** Shares print as %, and 0–1 indices (RYI, scores) need no unit after the number. */
export function unitLabel(unit: string): string {
  if (SHARE_UNITS.test(unit) || unit.includes("0–1") || unit.includes("0-1")) return "";
  if (getLocale() !== "ar") return unit;
  const map: Record<string, string> = {
    mm: t("unit.mm"),
    "mm per rotation": t("unit.mm"),
    "mm per rotation (CVaR10, upper tail)": `${t("unit.mm")} (أسوأ 10٪)`,
    "mm/yr": t("unit.mmYr"),
    d: t("unit.days"),
    day: t("unit.days"),
    days: t("unit.days"),
    "day of harvest year": t("unit.days"),
    "days per rotation": t("unit.days"),
    "NDVI day": `يوم NDVI`,
    months: t("unit.months"),
    mo: t("unit.months"),
    m: t("unit.m"),
    ha: t("unit.ha"),
    "°C": "°C",
    count: "",
    "relative index per rotation year (CVaR10, lower tail)": "",
    "relative, within-field comparison only": "نسبي",
    "RYI regret": "",
    "RYI regret (mean over weather years)": "",
    "RYI change vs Current": "",
  };
  return map[unit] ?? unit;
}

export function formatTagged(v: Tagged, digits?: number): string {
  if (v.value === null) return t("value.none");
  const u = unitLabel(v.unit);
  return `${formatNumber(v.value, v.unit, digits)}${u ? ` ${u}` : ""}`;
}

/** Signed difference to a reference value, in the value's own unit. */
export function formatDelta(v: Tagged, ref: Tagged, digits?: number): string | null {
  if (v.value === null || ref.value === null) return null;
  const d = v.value - ref.value;
  const body = formatNumber(Math.abs(d), v.unit, digits);
  if (body === "0" || body === "0 %") return t("format.same");
  const raw = `${d > 0 ? "+" : "−"}${body}`;
  return getLocale() === "ar" ? `\u2066${raw}\u2069` : raw;
}

const PARAM_AR: Record<string, string> = {
  "soil water holding capacity (TAW)": "السعة التخزينية لمياه التربة (TAW)",
  "seasonal irrigation amount": "كمية الريّ الموسمي",
  "crop water-use scale (Kc)": "معامل استهلاك المحصول للمياه (Kc)",
};

export function localizeMeasureNext(raw: string): string {
  if (getLocale() !== "ar") return raw;
  if (raw === "No uncertain input changes rank 1 in the posterior worlds.") {
    return "لا يوجد مُدخل غير مؤكّد يغيّر الخيار الأول في العوالم الاحتمالية.";
  }
  const m = /^Measure the (.+?): it changes rank 1 in (\d+)% of worlds\.?$/.exec(raw);
  if (!m) return raw;
  const param = PARAM_AR[m[1]] ?? m[1];
  return `قِس ${param}: إذ يغيّر الخيار الأول في \u2066${m[2]}٪\u2069 من العوالم.`;
}

export function localizeCounterfactualFlip(raw: string): string {
  if (getLocale() !== "ar") return raw;
  if (raw === "No single tested change within the bounds turns rank 1 over.") {
    return "لا يوجد تغيير منفرد مُختبَر ضمن الحدود يقلب الخيار الأول.";
  }
  const parts = raw.split("; ").map((part) => {
    const mNo = /^(.+?): no flip in the tested range$/.exec(part);
    if (mNo) {
      const param = PARAM_AR[mNo[1]] ?? mNo[1];
      return `${param}: لا انقلاب ضمن النطاق المختبَر`;
    }
    const mFlip = /^(.+?): rank 1 changes at (.+)$/.exec(part);
    if (mFlip) {
      const param = PARAM_AR[mFlip[1]] ?? mFlip[1];
      return `${param}: يتغيّر الخيار الأول عند \u2066${mFlip[2]}\u2069`;
    }
    return part;
  });
  return parts.join("؛ ");
}

export function localizeGradeReason(raw: string): string {
  if (getLocale() !== "ar") return raw;
  if (raw === "Current rotation: reference option, not graded.") {
    return "الدورة الحالية: خيار مرجعي غير مُقيَّم.";
  }
  if (raw === "no neighbour estimate") return "لا يوجد تقدير من الحقول المجاورة";
  if (raw === "own past not supporting (credibility missing or below threshold)") {
    return "التاريخ الذاتي للحقل لا يدعم (المصداقية مفقودة أو دون الحد الأدنى)";
  }
  if (raw === "Field not graded: Current rotation cannot be simulated.") {
    return "الحقل غير مُقيَّم: لا يمكن محاكاة الدورة الحالية.";
  }
  const mOwn = /^own past agrees \(credibility ([0-9.]+) >= ([0-9.]+)\)$/.exec(raw);
  if (mOwn) return `التاريخ الذاتي للحقل يتفق (المصداقية \u2066${mOwn[1]} ≥ ${mOwn[2]}\u2069)`;
  const mAssump = /^(\d+) of (\d+) key inputs are assumptions \(tag A\)$/.exec(raw);
  if (mAssump) return `\u2066${mAssump[1]}\u2069 من أصل \u2066${mAssump[2]}\u2069 مدخلات رئيسية هي افتراضات (الوسم A)`;
  return raw;
}

/**
 * Season dates are days of the harvest year; 1 = 1 Jan, 0 = 31 Dec of the year before,
 * negative = earlier that autumn (schema decision Q1, 2026-11-04).
 */
export function harvestDayToDate(harvestYear: number, day: number): Date {
  return new Date(Date.UTC(harvestYear, 0, 1) + (day - 1) * 86_400_000);
}

export function formatDate(d: Date): string {
  return d.toLocaleDateString(dateLocale(), { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
