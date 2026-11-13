import { fieldNumber } from "./fields";
import { formatDate } from "./format";
import { generateFieldSummary } from "./fieldSummary";
import { explainRanking } from "./rankingExplainer";
import { rankOptions } from "./rank";
import { cropName, optionName, t } from "./strings";
import type { FieldPack, RegionIndex } from "./types";

const DEFAULT_PRIORITIES = {
  water: 1,
  bare: 1,
  badYear: 1,
  erosion: 1,
  legume: 1,
  residue: 1,
};

const DEFAULT_CONSTRAINTS = {
  no_crops: [],
  irrigation_only: false,
  max_water_mm: null,
  must_market: false,
};

export function PrintDossier({
  pack,
  regionId,
  index,
}: {
  pack: FieldPack;
  regionId: string;
  index?: RegionIndex | null;
}) {
  const fieldId = pack.field.field_id;
  const num = index ? fieldNumber(fieldId, index.fields) : fieldId.slice(0, 8);
  const ranked = rankOptions(pack.options, DEFAULT_PRIORITIES, DEFAULT_CONSTRAINTS);
  const rankingExpl = explainRanking(ranked);
  const summary = generateFieldSummary(pack, DEFAULT_PRIORITIES, DEFAULT_CONSTRAINTS);
  const currentOpt = pack.options.find((o) => o.option_id === "current");
  const topAlts = ranked.filter((r) => r.option.option_id !== "current").slice(0, 3);

  return (
    <section className="print-dossier" aria-label="Printable Field Decision Dossier">
      <header className="print-dossier-head">
        <div className="print-brand-row">
          <div>
            <h1 className="print-app-title">FieldWitness</h1>
            <p className="print-app-tagline">NASA Space Apps Challenge 2026 — Crop Rotation Decision Dossier</p>
          </div>
          <div className="print-field-badge">
            <strong>Field {num}</strong>
            <span className="print-field-hash">({fieldId.slice(0, 8)})</span>
          </div>
        </div>

        <table className="print-meta-table">
          <tbody>
            <tr>
              <th>Region</th>
              <td>Kansas High Plains (Tile T14SLH)</td>
              <th>Field Area</th>
              <td>{pack.field.area_ha.toFixed(1)} ha</td>
              <th>30 m Interior Pixels</th>
              <td>{pack.field.interior_pixels} [O]</td>
            </tr>
            <tr>
              <th>Boundary Source</th>
              <td>{pack.field.boundary_source} [E]</td>
              <th>Data As-Of</th>
              <td>{formatDate(new Date(`${pack.data_as_of}T00:00:00Z`))}</td>
              <th>Hindcast Cut-Off</th>
              <td>2021-12-31 (Strict Freeze)</td>
            </tr>
          </tbody>
        </table>
      </header>

      {/* Summary Box */}
      <div className="print-summary-box">
        <h3>Executive Assessment</h3>
        <p className="print-summary-sentence">{summary.sentence}</p>
        <p className="print-ranking-sentence">{rankingExpl.sentence}</p>
      </div>

      {/* Top Rotation Options Table */}
      <div className="print-section">
        <h3>Evaluated 3-Season Crop Rotations</h3>
        <table className="print-data-table">
          <thead>
            <tr>
              <th>Role / Rank</th>
              <th>Crop Sequence</th>
              <th>Evidence Grade</th>
              <th>Water Use (mm)</th>
              <th>Dry-Year Water (mm)</th>
              <th>Bare-Soil Months</th>
              <th>RYI (0–1)</th>
              <th>Regret</th>
            </tr>
          </thead>
          <tbody>
            {currentOpt && (
              <tr className="print-row-current">
                <td><strong>Current Rotation</strong></td>
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
                <td><strong>Alternative #{i + 1}</strong></td>
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
          <h4>Three Witnesses Verification Framework</h4>
          <ul className="print-witness-list">
            <li>
              <strong>Witness 1 (Physics):</strong> FAO-56 dual crop water balance forced by NASA POWER daily surface meteorology. <span className="print-badge on">ACTIVE</span>
            </li>
            <li>
              <strong>Witness 2 (Field Past):</strong> Multi-year HLS 30 m calibration (ABC credibility: {((pack.credibility.value ?? 0) * 100).toFixed(0)}%). <span className="print-badge on">ACTIVE</span>
            </li>
            <li>
              <strong>Witness 3 (Neighbours):</strong> Double Machine Learning causal contrasts across similar fields. <span className="print-badge off">OFF (Circuit Breaker)</span>
              <p className="print-witness-note">
                Automatically turned OFF to guard against unobserved rotational confounding in observational farm data. Evidence grade ceiling: Grade B.
              </p>
            </li>
          </ul>
        </div>

        <div className="print-dossier-card">
          <h4>Field History & Decision Advisory</h4>
          <ul className="print-advice-list">
            <li>
              <strong>Historical Rotation Track:</strong>{" "}
              {pack.story.slice(-6).map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : "Fallow"}`).join(" → ")}
            </li>
            <li>
              <strong>Decision Flip Sensitivity:</strong> {pack.advice.counterfactual_flip}
            </li>
            <li>
              <strong>Recommended Next Measurement:</strong> {pack.advice.measure_next}
            </li>
            <li>
              <strong>Local Soil Context:</strong> ISRIC SoilGrids 2.0 (250 m context) clay, sand, SOC. Simulation root-zone baseline: calibrated 150 mm base.
            </li>
          </ul>
        </div>
      </div>

      {/* Satellite History Compact Table */}
      <div className="print-section">
        <h3>Recent Observed Satellite Trajectory (NASA HLS 30 m)</h3>
        <table className="print-data-table print-compact">
          <thead>
            <tr>
              <th>Harvest Year</th>
              <th>Crop [E]</th>
              <th>Green-up (SOS) [D]</th>
              <th>Peak Canopy (DOY) [D]</th>
              <th>Harvest (EOS) [D]</th>
              <th>Canopy Total [D]</th>
              <th>Cover Days [D]</th>
              <th>Clear HLS Obs [O]</th>
            </tr>
          </thead>
          <tbody>
            {pack.story.slice(-7).map((s) => (
              <tr key={s.year}>
                <td><strong>{s.year}</strong></td>
                <td>{s.crop ? cropName(s.crop) : "Fallow"}</td>
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
          <strong>Source Tags:</strong> <code>[O]</code> observed by satellite · <code>[D]</code> derived by biophysical model · <code>[E]</code> external non-NASA ground record · <code>[A]</code> human assumption.
        </div>
        <p className="print-attribution">
          Data Sources: NASA Harmonized Landsat Sentinel-2 (HLS 30 m) · NASA GIBS / LP DAAC · NASA POWER Daily Surface Meteorology · USDA NASS CSB 2017–2024 · ISRIC SoilGrids 2.0 · FAO-56.
        </p>
        <p className="print-disclaimer">
          <strong>Notice:</strong> {t("fixed.judgment")}
        </p>
      </footer>
    </section>
  );
}
