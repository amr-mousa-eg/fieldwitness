import { useState } from "react";
import { DIAGNOSIS_DATA, type ExploratoryCell } from "./diagnosis";

type DimensionKey = "by_crop" | "by_year" | "by_field_size" | "by_grade" | "by_hls_obs";

const DIMENSIONS: { key: DimensionKey; label: string }[] = [
  { key: "by_crop", label: "Crop" },
  { key: "by_year", label: "Season Year" },
  { key: "by_field_size", label: "Field Size" },
  { key: "by_grade", label: "Evidence Grade" },
  { key: "by_hls_obs", label: "Clear HLS Observations" },
];

export function DiagnosisSection() {
  const [activeDim, setActiveDim] = useState<DimensionKey>("by_crop");
  const data = DIAGNOSIS_DATA;
  const primary = data.primary_question.results;
  const exploratoryRows: ExploratoryCell[] = data.exploratory_breakdowns[activeDim];

  return (
    <section className="score-block diagnosis-section" aria-labelledby="diagnosis-h">
      <h3 id="diagnosis-h">Where it works and where it doesn't (exploratory)</h3>
      <p className="muted" style={{ fontSize: "0.88rem", marginBottom: "0.75rem" }}>
        Pre-registered diagnostic evaluation (commit <code>e021f3e</code>, cut-off 31 Dec 2021). All statistical
        inference uses 1,000 spatial block bootstrap resamples across 10 km grid cells (seed 42).
        Any group with <em>n &lt; 20</em> is reported as &ldquo;too few to judge&rdquo;.
      </p>

      {/* Primary Pre-Registered Test: Baseline Comparisons */}
      <div className="diagnosis-primary-box" style={{ marginBottom: "1.25rem" }}>
        <h4 style={{ margin: "0 0 0.4rem 0", fontSize: "0.95rem" }}>
          Primary Pre-Registered Question: Does FieldWitness beat Baselines B1 &amp; B2?
        </h4>
        <p className="muted" style={{ fontSize: "0.82rem", margin: "0 0 0.6rem 0" }}>
          Target: forecast-mode canopy-integral CRPS. Success rule: the 95% spatial block bootstrap CI of the paired
          difference strictly excludes 0 in FieldWitness&apos;s favour. Overall comparison excludes winter wheat (no baseline run) and fallow (not scored).
        </p>

        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">Subset</th>
                <th scope="col">n</th>
                <th scope="col">FieldWitness CRPS (95% CI)</th>
                <th scope="col">B1 (FAO Table)</th>
                <th scope="col">Diff vs B1 (95% CI)</th>
                <th scope="col">Beats B1?</th>
                <th scope="col">B2 (Prior)</th>
                <th scope="col">Diff vs B2 (95% CI)</th>
                <th scope="col">Beats B2?</th>
              </tr>
            </thead>
            <tbody>
              <tr className="row-current">
                <th scope="row">
                  <span className="method-name">Overall (paired sample)</span>
                  <span className="method-desc">Maize &amp; sorghum (B1/B2 available)</span>
                </th>
                <td>{primary.overall.n_paired_baselines}</td>
                <td>
                  <strong>{primary.overall.fw_crps_mean.toFixed(2)}</strong> [{primary.overall.fw_crps_ci95[0].toFixed(2)},{" "}
                  {primary.overall.fw_crps_ci95[1].toFixed(2)}]
                </td>
                <td>{primary.overall.b1_crps_mean?.toFixed(2)}</td>
                <td>
                  +{primary.overall.diff_vs_b1_mean?.toFixed(2)} [{primary.overall.diff_vs_b1_ci95?.[0].toFixed(2)},{" "}
                  {primary.overall.diff_vs_b1_ci95?.[1].toFixed(2)}]
                </td>
                <td>
                  <span className="best-label" style={{ fontWeight: 700 }}>
                    {primary.overall.beats_b1 ? "YES" : "NO"}
                  </span>
                </td>
                <td>{primary.overall.b2_crps_mean?.toFixed(2)}</td>
                <td>
                  +{primary.overall.diff_vs_b2_mean?.toFixed(2)} [{primary.overall.diff_vs_b2_ci95?.[0].toFixed(2)},{" "}
                  {primary.overall.diff_vs_b2_ci95?.[1].toFixed(2)}]
                </td>
                <td>
                  <span className="best-label" style={{ fontWeight: 700 }}>
                    {primary.overall.beats_b2 ? "YES" : "NO"}
                  </span>
                </td>
              </tr>
              {Object.entries(primary.by_crop).map(([crop, row]) => (
                <tr key={crop}>
                  <th scope="row">
                    <span className="method-name" style={{ textTransform: "capitalize" }}>
                      Crop: {crop.replace("_", " ")}
                    </span>
                  </th>
                  <td>{row.n}</td>
                  {row.status === "too few to judge" ? (
                    <td colSpan={7} className="muted">
                      <em>Too few to judge (n &lt; 20)</em>
                    </td>
                  ) : row.status === "baseline not computed in T7.3" ? (
                    <>
                      <td>
                        {row.fw_crps_mean.toFixed(2)} [{row.fw_crps_ci95[0].toFixed(2)}, {row.fw_crps_ci95[1].toFixed(2)}]
                      </td>
                      <td colSpan={6} className="muted">
                        <em>Baselines omitted for winter wheat in T7.3</em>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>
                        {row.fw_crps_mean.toFixed(2)} [{row.fw_crps_ci95[0].toFixed(2)}, {row.fw_crps_ci95[1].toFixed(2)}]
                      </td>
                      <td>{row.b1_crps_mean?.toFixed(2)}</td>
                      <td>
                        +{row.diff_vs_b1_mean?.toFixed(2)} [{row.diff_vs_b1_ci95?.[0].toFixed(2)},{" "}
                        {row.diff_vs_b1_ci95?.[1].toFixed(2)}]
                      </td>
                      <td>{row.beats_b1 ? "YES" : "NO"}</td>
                      <td>{row.b2_crps_mean?.toFixed(2)}</td>
                      <td>
                        +{row.diff_vs_b2_mean?.toFixed(2)} [{row.diff_vs_b2_ci95?.[0].toFixed(2)},{" "}
                        {row.diff_vs_b2_ci95?.[1].toFixed(2)}]
                      </td>
                      <td>{row.beats_b2 ? "YES" : "NO"}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Exploratory Dimension Breakdowns */}
      <div className="diagnosis-exploratory-box" style={{ marginBottom: "1.25rem" }}>
        <h4 style={{ margin: "0 0 0.4rem 0", fontSize: "0.95rem" }}>
          Exploratory Breakdowns by Dimension
        </h4>
        <p className="muted" style={{ fontSize: "0.82rem", margin: "0 0 0.6rem 0" }}>
          All comparisons below are exploratory. Cells with n &lt; 20 are labelled &ldquo;too few to judge&rdquo;.
        </p>

        <div className="sim3d-view-mode-toggle" style={{ marginBottom: "0.75rem", width: "fit-content" }}>
          {DIMENSIONS.map((dim) => (
            <button
              key={dim.key}
              type="button"
              className={`sim3d-toggle-btn ${activeDim === dim.key ? "active" : ""}`}
              onClick={() => setActiveDim(dim.key)}
            >
              {dim.label}
            </button>
          ))}
        </div>

        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col">n</th>
                <th scope="col">FW CRPS (95% CI)</th>
                <th scope="col">Peak Timing Abs Err</th>
                <th scope="col">90% Canopy Coverage</th>
                <th scope="col">Verdict vs B1 (FAO Table)</th>
                <th scope="col">Verdict vs B2 (Prior)</th>
              </tr>
            </thead>
            <tbody>
              {exploratoryRows.map((cell) => (
                <tr key={cell.category}>
                  <th scope="row">
                    <span className="method-name" style={{ textTransform: "capitalize" }}>
                      {cell.category.replace("_", " ")}
                    </span>
                  </th>
                  <td>{cell.n}</td>
                  {cell.status === "too few to judge" ? (
                    <td colSpan={5} className="muted">
                      <em>Too few to judge (n &lt; 20)</em>
                    </td>
                  ) : (
                    <>
                      <td>
                        {cell.fw_crps_mean?.toFixed(2)} [{cell.fw_crps_ci95?.[0].toFixed(2)},{" "}
                        {cell.fw_crps_ci95?.[1].toFixed(2)}]
                      </td>
                      <td>
                        {cell.fw_peak_err_mean?.toFixed(1)} d [{cell.fw_peak_err_ci95?.[0].toFixed(1)},{" "}
                        {cell.fw_peak_err_ci95?.[1].toFixed(1)}]
                      </td>
                      <td>
                        {cell.fw_cov90_mean !== undefined ? `${(cell.fw_cov90_mean * 100).toFixed(1)} %` : "—"} [
                        {cell.fw_cov90_ci95 !== undefined
                          ? `${(cell.fw_cov90_ci95[0] * 100).toFixed(1)} %, ${(cell.fw_cov90_ci95[1] * 100).toFixed(1)} %`
                          : "—"}
                        ]
                      </td>
                      <td>{cell.verdict_vs_b1}</td>
                      <td>{cell.verdict_vs_b2}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Honest Causal Findings */}
      <div className="diagnosis-findings-box">
        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem" }}>Key Findings &amp; Honest Causal Explanations</h4>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.85rem", lineHeight: 1.5 }}>
          {data.findings.map((f, i) => (
            <li key={i} style={{ marginBottom: "0.5rem" }}>
              <strong>{f.dimension.replace("_", " ").toUpperCase()}:</strong> {f.finding}
              <br />
              <span className="muted" style={{ fontStyle: "italic" }}>
                Evidence analysis: {f.cause}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
