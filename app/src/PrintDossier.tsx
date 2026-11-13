import { fieldNumber } from "./fields";
import { formatDate } from "./format";
import { generateFieldSummary } from "./fieldSummary";
import { explainRanking } from "./rankingExplainer";
import { DEFAULT_PRIORITIES, NO_CONSTRAINTS, rankOptions } from "./rank";
import { cropName, optionName, t } from "./strings";
import type { FieldPack, RegionIndex } from "./types";

export function PrintDossier({
  pack,
  regionId: _regionId,
  index,
}: {
  pack: FieldPack;
  regionId: string;
  index?: RegionIndex | null;
}) {
  const fieldId = pack.field.field_id;
  const num = index ? fieldNumber(fieldId, index.fields) : fieldId.slice(0, 8);
  const ranked = rankOptions(pack.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
  const rankingExpl = explainRanking(ranked, DEFAULT_PRIORITIES);
  const summary = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
  const currentOpt = pack.options.find((o) => o.option_id === "current");
  const topAlts = ranked.filter((r) => r.option.option_id !== "current").slice(0, 3);

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
              <td>{t("print.regionVal")}</td>
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
            {currentOpt && (
              <tr className="print-row-current">
                <td><strong>{t("print.currentRole")}</strong></td>
                <td>{optionName(currentOpt)}</td>
                <td><span className="print-grade">{currentOpt.grade}</span></td>
                <td>{currentOpt.metrics.water_use_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{currentOpt.metrics.bad_year_water_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{((currentOpt.metrics.cover_days?.value != null ? (365 * 3 - currentOpt.metrics.cover_days.value) / 30.4375 : 0)).toFixed(1)} [D]</td>
                <td>{currentOpt.metrics.ryi?.value?.toFixed(2) ?? "—"} [D]</td>
                <td>{currentOpt.regret.value?.toFixed(2) ?? "0.00"} [D]</td>
              </tr>
            )}
            {topAlts.map((r, i) => (
              <tr key={r.option.option_id} className={i === 0 ? "print-row-top" : undefined}>
                <td><strong>{t("print.altRole", { n: i + 1 })}</strong></td>
                <td>{optionName(r.option)}</td>
                <td><span className="print-grade">{r.option.grade}</span></td>
                <td>{r.option.metrics.water_use_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{r.option.metrics.bad_year_water_mm?.value?.toFixed(0) ?? "—"} [D]</td>
                <td>{((r.option.metrics.cover_days?.value != null ? (365 * 3 - r.option.metrics.cover_days.value) / 30.4375 : 0)).toFixed(1)} [D]</td>
                <td>{r.option.metrics.ryi?.value?.toFixed(2) ?? "—"} [D]</td>
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
              <strong>Witness 1 (Physics):</strong> FAO-56 dual crop water balance forced by NASA POWER daily surface meteorology. <span className="print-badge on">ACTIVE</span>
            </li>
            <li>
              <strong>Witness 2 (Field Past):</strong> Multi-year HLS 30 m calibration (ABC credibility: {((pack.credibility.value ?? 0) * 100).toFixed(0)}%). <span className="print-badge on">ACTIVE</span>
            </li>
            <li>
              <strong>Witness 3 (Neighbours / Trials):</strong> Observational satellite contrasts <span className="print-badge off">OFF (Circuit Breaker)</span>; grounded in 30-year K-State Colby agronomic trials (tag [E]) where matched.
              <p className="print-witness-note">
                Observational contrasts are turned OFF to guard against farmer selection bias. Rotations matching K-State Research &amp; Extension trials unlock independent [E] validation.
              </p>
            </li>
          </ul>
        </div>

        <div className="print-dossier-card">
          <h4>{t("print.advisoryHeading")}</h4>
          <ul className="print-advice-list">
            <li>
              <strong>Historical Rotation Track:</strong>{" "}
              {pack.story.slice(-6).map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : t("crop.fallow")}`).join(" → ")}
            </li>
            <li>
              <strong>Decision Flip Sensitivity:</strong> {pack.advice.counterfactual_flip}
            </li>
            <li>
              <strong>Recommended Next Measurement:</strong> {pack.advice.measure_next}
            </li>
            <li>
              <strong>Local Soil Context:</strong> USDA-NRCS SSURGO silt loam AWS (median 282.1 mm [E]) &amp; ISRIC SoilGrids 2.0 (250 m clay/sand/SOC).
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
                <td>{s.sos.value != null ? `DOY ${Math.round(s.sos.value)}` : "—"}</td>
                <td>{s.peak.value != null ? `DOY ${Math.round(s.peak.value)}` : "—"}</td>
                <td>{s.eos.value != null ? `DOY ${Math.round(s.eos.value)}` : "—"}</td>
                <td>{s.canopy_integral.value != null ? s.canopy_integral.value.toFixed(1) : "—"}</td>
                <td>{s.cover_days.value != null ? `${Math.round(s.cover_days.value)} d` : "—"}</td>
                <td>{s.clear_obs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer & Fixed Disclaimer */}
      <footer className="print-dossier-footer">
        <div className="print-tags-legend">
          <strong>{t("tag.legend")}:</strong> <code>[O]</code> {t("tag.O")} · <code>[D]</code> {t("tag.D")} · <code>[E]</code> {t("tag.E")} · <code>[A]</code> {t("tag.A")}.
        </div>
        <p className="print-attribution">
          Data Sources: NASA Harmonized Landsat Sentinel-2 (HLS 30 m) · NASA GIBS / LP DAAC · NASA POWER Daily Surface Meteorology · USDA NASS CSB 2017–2024 · ISRIC SoilGrids 2.0 · FAO-56.
        </p>
        <p className="print-disclaimer">
          <strong>{t("print.notice")}</strong> {t("fixed.judgment")}
        </p>
      </footer>
    </section>
  );
}
