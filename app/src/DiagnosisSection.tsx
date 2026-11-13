import { useState } from "react";
import { Explain } from "./Explain";
import { DIAGNOSIS_DATA, type ExploratoryCell } from "./diagnosis";
import { type StringKey, cropName, t } from "./strings";

type DimensionKey = "by_crop" | "by_year" | "by_field_size" | "by_grade" | "by_hls_obs";

const DIMENSIONS: DimensionKey[] = ["by_crop", "by_year", "by_field_size", "by_grade", "by_hls_obs"];

function formatCategory(dim: DimensionKey, cat: string): string {
  if (dim === "by_crop") return cropName(cat);
  if (dim === "by_grade") return t("score.gradeLabel", { grade: cat });
  if (dim === "by_field_size") return cat.replace(/\bha\b/g, t("unit.ha"));
  return cat;
}

function formatVerdict(v: string | undefined): string {
  if (!v) return t("value.none");
  if (v.startsWith("FieldWitness beats baseline")) return t("diagnosis.verdict.beats");
  if (v.startsWith("comparable within uncertainty")) return t("diagnosis.verdict.no_diff");
  if (v.startsWith("not evaluated")) return t("diagnosis.verdict.notEvaluated");
  return t("diagnosis.verdict.worse");
}

function YesNoBadge({ yes }: { yes: boolean | null | undefined }) {
  if (yes == null) return <span className="muted">{t("value.none")}</span>;
  return (
    <span className={yes ? "yes-badge" : "no-badge"}>
      {t(yes ? "diagnosis.yes" : "diagnosis.no")}
    </span>
  );
}

export function DiagnosisSection() {
  const [activeDim, setActiveDim] = useState<DimensionKey>("by_crop");
  const data = DIAGNOSIS_DATA;
  const primary = data.primary_question.results;
  const exploratoryRows: ExploratoryCell[] = data.exploratory_breakdowns[activeDim];

  return (
    <section className="score-block diagnosis-section" aria-labelledby="diagnosis-h">
      <h3 id="diagnosis-h">
        {t("diagnosis.heading")} <Explain id="diagnosis" />
      </h3>
      <p className="muted" style={{ fontSize: "0.88rem", marginBottom: "0.75rem" }}>
        {t("diagnosis.intro")}
      </p>

      {/* Primary Pre-Registered Test: Baseline Comparisons */}
      <div className="diagnosis-primary-box" style={{ marginBottom: "1.25rem" }}>
        <h4 style={{ margin: "0 0 0.4rem 0", fontSize: "0.95rem" }}>
          {t("diagnosis.primaryHeading")}
        </h4>
        <p className="muted" style={{ fontSize: "0.82rem", margin: "0 0 0.6rem 0" }}>
          {t("diagnosis.primaryNote")}
        </p>

        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">{t("diagnosis.thSubset")}</th>
                <th scope="col">{t("score.n")}</th>
                <th scope="col">{t("diagnosis.thFwCrps")}</th>
                <th scope="col">{t("diagnosis.thB1")}</th>
                <th scope="col">{t("diagnosis.thDiffB1")}</th>
                <th scope="col">{t("diagnosis.thBeatsB1")}</th>
                <th scope="col">{t("diagnosis.thB2")}</th>
                <th scope="col">{t("diagnosis.thDiffB2")}</th>
                <th scope="col">{t("diagnosis.thBeatsB2")}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="row-current">
                <th scope="row">
                  <span className="method-name">{t("diagnosis.overallTitle")}</span>
                  <span className="method-desc">{t("diagnosis.overallDesc")}</span>
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
                  <YesNoBadge yes={primary.overall.beats_b1} />
                </td>
                <td>{primary.overall.b2_crps_mean?.toFixed(2)}</td>
                <td>
                  +{primary.overall.diff_vs_b2_mean?.toFixed(2)} [{primary.overall.diff_vs_b2_ci95?.[0].toFixed(2)},{" "}
                  {primary.overall.diff_vs_b2_ci95?.[1].toFixed(2)}]
                </td>
                <td>
                  <YesNoBadge yes={primary.overall.beats_b2} />
                </td>
              </tr>
              {Object.entries(primary.by_crop).map(([crop, row]) => (
                <tr key={crop}>
                  <th scope="row">
                    <span className="method-name">{t("diagnosis.cropPrefix", { crop: cropName(crop) })}</span>
                  </th>
                  <td>{row.n}</td>
                  {row.status === "too few to judge" ? (
                    <td colSpan={7} className="muted">
                      <em>{t("diagnosis.tooFew")}</em>
                    </td>
                  ) : row.status === "baseline not computed in T7.3" ? (
                    <>
                      <td>
                        {row.fw_crps_mean.toFixed(2)} [{row.fw_crps_ci95[0].toFixed(2)}, {row.fw_crps_ci95[1].toFixed(2)}]
                      </td>
                      <td colSpan={6} className="muted">
                        <em>{t("diagnosis.wheatOmitted")}</em>
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
                      <td>
                        <YesNoBadge yes={row.beats_b1} />
                      </td>
                      <td>{row.b2_crps_mean?.toFixed(2)}</td>
                      <td>
                        +{row.diff_vs_b2_mean?.toFixed(2)} [{row.diff_vs_b2_ci95?.[0].toFixed(2)},{" "}
                        {row.diff_vs_b2_ci95?.[1].toFixed(2)}]
                      </td>
                      <td>
                        <YesNoBadge yes={row.beats_b2} />
                      </td>
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
          {t("diagnosis.expHeading")}
        </h4>
        <p className="muted" style={{ fontSize: "0.82rem", margin: "0 0 0.6rem 0" }}>
          {t("diagnosis.expNote")}
        </p>

        <div className="sim3d-view-mode-toggle" style={{ marginBottom: "0.75rem", width: "fit-content" }}>
          {DIMENSIONS.map((dim) => (
            <button
              key={dim}
              type="button"
              className={`sim3d-toggle-btn ${activeDim === dim ? "active" : ""}`}
              onClick={() => setActiveDim(dim)}
            >
              {t(`diagnosis.dim.${dim}` as StringKey)}
            </button>
          ))}
        </div>

        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">{t("diagnosis.thCategory")}</th>
                <th scope="col">{t("score.n")}</th>
                <th scope="col">{t("diagnosis.thFwCrpsShort")}</th>
                <th scope="col">{t("diagnosis.thPeakErr")}</th>
                <th scope="col">{t("diagnosis.thCov90")}</th>
                <th scope="col">{t("diagnosis.thVerdictB1")}</th>
                <th scope="col">{t("diagnosis.thVerdictB2")}</th>
              </tr>
            </thead>
            <tbody>
              {exploratoryRows.map((cell) => (
                <tr key={cell.category}>
                  <th scope="row">
                    <span className="method-name">{formatCategory(activeDim, cell.category)}</span>
                  </th>
                  <td>{cell.n}</td>
                  {cell.status === "too few to judge" ? (
                    <td colSpan={5} className="muted">
                      <em>{t("diagnosis.tooFew")}</em>
                    </td>
                  ) : (
                    <>
                      <td>
                        {cell.fw_crps_mean?.toFixed(2)} [{cell.fw_crps_ci95?.[0].toFixed(2)},{" "}
                        {cell.fw_crps_ci95?.[1].toFixed(2)}]
                      </td>
                      <td>
                        {t("score.daysShort", { v: cell.fw_peak_err_mean?.toFixed(1) ?? "—" })} [
                        {cell.fw_peak_err_ci95?.[0].toFixed(1)}, {cell.fw_peak_err_ci95?.[1].toFixed(1)}]
                      </td>
                      <td>
                        {cell.fw_cov90_mean !== undefined ? `${(cell.fw_cov90_mean * 100).toFixed(1)} %` : "—"} [
                        {cell.fw_cov90_ci95 !== undefined
                          ? `${(cell.fw_cov90_ci95[0] * 100).toFixed(1)} %, ${(cell.fw_cov90_ci95[1] * 100).toFixed(1)} %`
                          : "—"}
                        ]
                      </td>
                      <td>{formatVerdict(cell.verdict_vs_b1)}</td>
                      <td>{formatVerdict(cell.verdict_vs_b2)}</td>
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
        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem" }}>{t("diagnosis.findingsHeading")}</h4>
        <ul style={{ margin: 0, paddingInlineStart: "1.2rem", fontSize: "0.85rem", lineHeight: 1.5 }}>
          {data.findings.map((f, i) => {
            const dimLabel = t(`diagnosis.finding.${f.dimension}.dim` as StringKey);
            const findingText = t(`diagnosis.finding.${f.dimension}.text` as StringKey);
            const causeText =
              f.cause === "cause not established"
                ? t("diagnosis.cause.not_established")
                : t(`diagnosis.finding.${f.dimension}.cause` as StringKey);
            return (
              <li key={i} style={{ marginBottom: "0.5rem" }}>
                <strong>{dimLabel}:</strong> {findingText}
                <br />
                <span className="muted" style={{ fontStyle: "italic" }}>
                  {t("diagnosis.evidenceAnalysis")} {causeText}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
