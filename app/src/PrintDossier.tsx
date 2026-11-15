import { fieldNumber } from "./fields";
import { formatDate, localizeCounterfactualFlip, localizeMeasureNext } from "./format";
import { generateFieldSummary } from "./fieldSummary";
import { QrCodeSvg } from "./qrCode";
import { explainRanking } from "./rankingExplainer";
import {
  type Constraints,
  DEFAULT_PRIORITIES,
  NO_CONSTRAINTS,
  type Priorities,
  findScenario,
  isDefault,
  rankOptions,
} from "./rank";
import { fieldStateHref } from "./route";
import { cropName, optionName, t } from "./strings";
import type { FieldPack, FieldScenarios, RegionIndex } from "./types";

function signedPrint(v: number, unit: "temp" | "rain"): string {
  const s = v > 0 ? `+${v}` : v < 0 ? `−${-v}` : "0";
  return t(unit === "temp" ? "whatif.tempValue" : "whatif.rainValue", { v: s });
}

export function PrintDossier({
  pack,
  regionId,
  index,
  priorities = DEFAULT_PRIORITIES,
  constraints = NO_CONSTRAINTS,
  dt = 0,
  dp = 0,
  scenarios = null,
  shareUrl,
}: {
  pack: FieldPack;
  regionId: string;
  index?: RegionIndex | null;
  priorities?: Priorities;
  constraints?: Constraints;
  dt?: number;
  dp?: number;
  scenarios?: FieldScenarios | null;
  shareUrl?: string;
}) {
  const fieldId = pack.field.field_id;
  const activeRegion = regionId || pack.field.region_id;
  const num = index ? fieldNumber(fieldId, index.fields) : fieldId.slice(0, 8);
  const scenario = dt === 0 && dp === 0 ? null : findScenario(scenarios, dt, dp);
  const ranked = rankOptions(pack.options, priorities, constraints, scenario);
  const rankingExpl = explainRanking(ranked, priorities);
  const summary = generateFieldSummary(pack, priorities, constraints, scenario);
  const currentRanked = ranked.find((r) => r.option.option_id === "current");
  const currentOpt = currentRanked?.option ?? pack.options.find((o) => o.option_id === "current");
  const currentMetrics = currentRanked?.metrics ?? currentOpt?.metrics;
  const keptAlts = ranked.filter((r) => r.kept && r.option.option_id !== "current");
  const topAlts = (keptAlts.length > 0 ? keptAlts : ranked.filter((r) => r.option.option_id !== "current")).slice(0, 3);
  const isUkraine = activeRegion === "ua_central_t36uvu";
  const hasActiveNeighbours = pack.options.some((o) => o.witnesses.some((w) => w.witness === "neighbours"));
  const regionLabel = index?.name ?? (isUkraine ? "Central Ukraine (T36UVU)" : t("print.regionVal"));

  const hasCustomPrefs =
    !isDefault(priorities) ||
    constraints.dontWant.length > 0 ||
    constraints.cantGrow.length > 0 ||
    constraints.canSell !== null ||
    constraints.irrigation !== "unset" ||
    constraints.waterCapMm !== null;
  const hasScenario = dt !== 0 || dp !== 0;

  const fallbackHash = fieldStateHref(activeRegion, fieldId, "options", priorities, constraints, dt, dp);
  const rawUrl =
    shareUrl ??
    (typeof window !== "undefined"
      ? `${window.location.origin}${window.location.pathname}${fallbackHash}`
      : `https://fieldwitness.org/${fallbackHash}`);
  const qrPayload = new TextEncoder().encode(rawUrl).length <= 270 ? rawUrl : fallbackHash;
  const canRenderQr = new TextEncoder().encode(qrPayload).length <= 270;

  return (
    <section className="print-dossier" aria-label={t("print.aria")}>
      <header className="print-dossier-head">
        <div className="print-brand-row">
          <div>
            <h1 className="print-app-title">{t("app.title")}</h1>
            <p className="print-app-tagline">{t("print.tagline")}</p>
          </div>
          <div className="print-field-badge">
            <strong>{t("field.heading", { id: num })}</strong>
            <span className="print-field-hash">({fieldId.slice(0, 8)})</span>
          </div>
        </div>

        <table className="print-meta-table">
          <tbody>
            <tr>
              <th>{t("print.region")}</th>
              <td>{regionLabel}</td>
              <th>{t("print.area")}</th>
              <td>{t("fields.area", { area: pack.field.area_ha.toFixed(1) })}</td>
              <th>{t("print.pixels")}</th>
              <td>{pack.field.interior_pixels} [O]</td>
            </tr>
            <tr>
              <th>{t("print.boundary")}</th>
              <td>{pack.field.boundary_source} [E]</td>
              <th>{t("print.asof")}</th>
              <td>{formatDate(new Date(`${pack.data_as_of}T00:00:00Z`))}</td>
              <th>{t("print.cutoff")}</th>
              <td>{t("print.cutoffVal")}</td>
            </tr>
          </tbody>
        </table>
      </header>

      {/* Summary Box */}
      <div className="print-summary-box">
        <h3>{t("print.execHeading")}</h3>
        <p className="print-summary-sentence">{summary.sentence}</p>
        <p className="print-ranking-sentence">{rankingExpl.sentence}</p>
        {(hasCustomPrefs || hasScenario) && (
          <div className="print-profile-banner">
            <strong>{t("print.profileHeading")}:</strong>
            <div className="print-profile-pills">
              {hasCustomPrefs && <span className="print-profile-pill">{t("print.profileCustomized")}</span>}
              {hasScenario && (
                <span className="print-profile-pill">
                  {t("print.profileScenario", { temp: signedPrint(dt, "temp"), rain: signedPrint(dp, "rain") })}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Top Rotation Options Table */}
      <div className="print-section">
        <h3>{t("print.rotHeading")}</h3>
        <table className="print-data-table">
          <thead>
            <tr>
              <th>{t("print.roleRank")}</th>
              <th>{t("print.sequence")}</th>
              <th>{t("print.grade")}</th>
              <th>{t("print.waterUse")}</th>
              <th>{t("print.dryWater")}</th>
              <th>{t("print.bareMonths")}</th>
              <th>{t("print.ryi")}</th>
              <th>{t("print.regret")}</th>
            </tr>
          </thead>
          <tbody>
            {currentOpt && currentMetrics && (
              <tr className="print-row-current">
                <td><strong>{t("print.currentRole")}</strong></td>
                <td>{optionName(currentOpt)}</td>
                <td><span className="print-grade">{currentOpt.grade}</span></td>
                <td>{currentMetrics.water_use_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{currentMetrics.bad_year_water_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{((currentMetrics.cover_days?.value != null ? (365 * 3 - currentMetrics.cover_days.value) / 30.4375 : 0)).toFixed(1)} [D]</td>
                <td>{currentMetrics.ryi?.value?.toFixed(2) ?? "—"} [D]</td>
                <td>{currentOpt.regret.value?.toFixed(2) ?? "0.00"} [D]</td>
              </tr>
            )}
            {topAlts.map((r, i) => (
              <tr key={r.option.option_id} className={i === 0 ? "print-row-top" : undefined}>
                <td><strong>{t("print.altRole", { n: i + 1 })}</strong></td>
                <td>{optionName(r.option)}</td>
                <td><span className="print-grade">{r.option.grade}</span></td>
                <td>{r.metrics.water_use_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{r.metrics.bad_year_water_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{((r.metrics.cover_days?.value != null ? (365 * 3 - r.metrics.cover_days.value) / 30.4375 : 0)).toFixed(1)} [D]</td>
                <td>{r.metrics.ryi?.value?.toFixed(2) ?? "—"} [D]</td>
                <td>{r.option.regret.value?.toFixed(2) ?? "0.00"} [D]</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Two-Column Status & Verification Cards */}
      <div className="print-dossier-grid">
        <div className="print-dossier-card">
          <h4>{t("print.witnessHeading")}</h4>
          <ul className="print-witness-list">
            <li>
              <strong>{t("print.w1Label")}</strong> {t("print.w1Desc")}{" "}
              <span className="print-badge on">{t("print.badgeActive")}</span>
            </li>
            <li>
              <strong>{t("print.w2Label")}</strong>{" "}
              {t("print.w2Desc", { cred: ((pack.credibility.value ?? 0) * 100).toFixed(0) })}{" "}
              <span className="print-badge on">{t("print.badgeActive")}</span>
            </li>
            <li>
              <strong>{t("print.w3Label")}</strong> {t("print.w3Desc")}{" "}
              <span className={hasActiveNeighbours ? "print-badge on" : "print-badge off"}>
                {t(hasActiveNeighbours ? "print.badgeActive" : "print.badgeOff")}
              </span>
              {!isUkraine && t("print.w3Trials")}
              <p className="print-witness-note">
                {t(isUkraine ? (hasActiveNeighbours ? "print.w3NoteUaActive" : "print.w3NoteUaPartial") : "print.w3Note")}
              </p>
            </li>
          </ul>
        </div>

        <div className="print-dossier-card">
          <h4>{t("print.advisoryHeading")}</h4>
          <ul className="print-advice-list">
            <li>
              <strong>{t("print.histTrack")}</strong>{" "}
              {pack.story.slice(-6).map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : t("crop.fallow")}`).join(" → ")}
            </li>
            <li>
              <strong>{t("print.flipSens")}</strong> {localizeCounterfactualFlip(pack.advice.counterfactual_flip)}
            </li>
            <li>
              <strong>{t("print.nextMeas")}</strong> {localizeMeasureNext(pack.advice.measure_next)}
            </li>
            <li>
              <strong>{t("print.soilCtxLabel")}</strong>{" "}
              {t(isUkraine ? "print.soilCtxValUa" : "print.soilCtxVal")}
            </li>
          </ul>
        </div>
      </div>

      {/* Satellite History Compact Table */}
      <div className="print-section">
        <h3>{t("print.satHeading")}</h3>
        <table className="print-data-table print-compact">
          <thead>
            <tr>
              <th>{t("print.year")}</th>
              <th>{t("print.crop")}</th>
              <th>{t("print.sos")}</th>
              <th>{t("print.peak")}</th>
              <th>{t("print.eos")}</th>
              <th>{t("print.canopyTotal")}</th>
              <th>{t("print.coverDays")}</th>
              <th>{t("print.clearObs")}</th>
            </tr>
          </thead>
          <tbody>
            {pack.story.slice(-7).map((s) => (
              <tr key={s.year}>
                <td><strong>{s.year}</strong></td>
                <td>{s.crop ? cropName(s.crop) : t("crop.fallow")}</td>
                <td>{s.sos.value != null ? t("print.doy", { doy: Math.round(s.sos.value) }) : "—"}</td>
                <td>{s.peak.value != null ? t("print.doy", { doy: Math.round(s.peak.value) }) : "—"}</td>
                <td>{s.eos.value != null ? t("print.doy", { doy: Math.round(s.eos.value) }) : "—"}</td>
                <td>{s.canopy_integral.value != null ? s.canopy_integral.value.toFixed(1) : "—"}</td>
                <td>{s.cover_days.value != null ? t("print.daysVal", { days: Math.round(s.cover_days.value) }) : "—"}</td>
                <td>{s.clear_obs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer, Deterministic QR Link & Fixed Disclaimer */}
      <footer className="print-dossier-footer">
        <div className="print-footer-row">
          <div className="print-footer-text">
            <div className="print-tags-legend">
              <strong>{t("tag.legend")}:</strong> <code>[O]</code> {t("tag.O")} · <code>[D]</code> {t("tag.D")} · <code>[E]</code> {t("tag.E")} · <code>[A]</code> {t("tag.A")}.
            </div>
            <p className="print-attribution">{t("print.attribution")}</p>
            <p className="print-disclaimer">
              <strong>{t("print.notice")}</strong> {t("fixed.judgment")}
            </p>
          </div>
          {canRenderQr && (
            <div className="print-qr-box">
              <QrCodeSvg value={qrPayload} size={76} label={t("print.qrCaption")} />
              <span className="print-qr-caption">{t("print.qrCaption")}</span>
            </div>
          )}
        </div>
      </footer>
    </section>
  );
}
