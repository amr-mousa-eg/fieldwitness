import { useEffect, useState } from "react";
import { Backtest } from "./AdvisorConsole";
import { CQR_EVALUATION } from "./cqrEvaluation";
import { DiagnosisSection } from "./DiagnosisSection";
import { UkraineNeighboursSection } from "./UkraineNeighboursSection";
import { Explain } from "./Explain";
import { setActiveHindcast } from "./chatbotContext";
import { loadHindcast, loadPack } from "./data";
import { formatDate } from "./format";
import { GRADE_VALIDITY } from "./gradeValidity";
import { type ScoreKey, bestMethods, methodsNotRun, metricsOf, modesOf, rowsFor, scoreKeysOf } from "./hindcast";
import { routeHref } from "./route";
import { cropName, metricName, t } from "./strings";
import { TagLegend } from "./tags";
import { useTourSeen } from "./tourEvents";
import type { FieldPack, HindcastRow, RegionHindcast, RegionIndex } from "./types";

const date = (iso: string) => formatDate(new Date(`${iso}T00:00:00Z`));

function fmt(key: ScoreKey, v: number): string {
  if (key === "covered50" || key === "covered90") return `${Math.round(v * 100)} %`;
  return v.toLocaleString("en", { maximumFractionDigits: key === "crps" ? 2 : 1 });
}

function ScoreTable({ rows, metric }: { rows: HindcastRow[]; metric: string }) {
  const keys = scoreKeysOf(rows, metric);
  const best = Object.fromEntries(keys.map((k) => [k, bestMethods(rows, k)])) as Record<ScoreKey, Set<string>>;
  const id = `score-${metric}`;
  return (
    <section className="score-block" aria-labelledby={id}>
      <h4 id={id}>{metricName(metric)}</h4>
      <div className="table-wrap">
        <table className="scores">
          <thead>
            <tr>
              <th scope="col">{t("score.method")}</th>
              {keys.map((k) => (
                <th key={k} scope="col">
                  {t(`score.${k}`)}
                  <span className="th-note">{t(`score.${k}.note`)}</span>
                </th>
              ))}
              <th scope="col">{t("score.n")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.method} className={r.method === "fieldwitness" ? "row-current" : undefined}>
                <th scope="row">
                  <span className="method-name">{t(`method.${r.method}`)}</span>
                  <span className="method-desc">{t(`method.${r.method}.desc`)}</span>
                </th>
                {keys.map((k) => {
                  const v = r.scores[k];
                  if (typeof v !== "number") return <td key={k} className="muted">{t("value.none")}</td>;
                  const isBest = best[k].has(r.method);
                  return (
                    <td key={k} className={isBest ? "best" : undefined}>
                      {fmt(k, v)}
                      {isBest && <span className="best-label"> {t("score.best")}</span>}
                    </td>
                  );
                })}
                <td>{r.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function GradeValiditySection() {
  const g = GRADE_VALIDITY.grades;
  const verdictRef = useTourSeen("limits");
  return (
    <section className="score-block grade-validity" aria-labelledby="score-gv">
      <h4 id="score-gv">
        {t("score.gradeValidity.heading")} <Explain id="evidence_grade" />
      </h4>
      <p className="muted">{t("score.gradeValidity.intro")}</p>

      <div
        ref={verdictRef}
        className="notice grade-validity-verdict"
        style={{ marginTop: "0.5rem", marginBottom: "0.75rem" }}
      >
        <strong>{t("score.gradeValidity.verdict")}</strong>
        <p style={{ marginTop: "0.25rem", marginBottom: 0 }}>
          {t("score.gradeValidity.verdictDetail")}
        </p>
      </div>

      <div className="table-wrap">
        <table className="scores">
          <thead>
            <tr>
              <th scope="col">{t("score.gradeValidity.thGrade")}</th>
              <th scope="col">{t("score.gradeValidity.thN")}</th>
              <th scope="col">
                {t("score.gradeValidity.thCrps")} <Explain id="crps" />
              </th>
              <th scope="col">{t("score.gradeValidity.thTiming")}</th>
              <th scope="col">{t("score.gradeValidity.thCoverage")}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">
                <span className="method-name">{t("score.gradeLabel", { grade: "B" })}</span>
                <span className="method-desc">{t("score.gradeValidity.bDesc")}</span>
              </th>
              <td>{g.B.n}</td>
              <td>{g.B.forecast_ci_crps_mean.toFixed(2)} [{g.B.forecast_ci_crps_ci95[0].toFixed(2)}, {g.B.forecast_ci_crps_ci95[1].toFixed(2)}]</td>
              <td>{t("score.daysShort", { v: g.B.forecast_peak_abs_err_mean.toFixed(1) })}</td>
              <td>{Math.round(g.B.forecast_ci_covered90_share * 100)} %</td>
            </tr>
            <tr>
              <th scope="row">
                <span className="method-name">{t("score.gradeLabel", { grade: "C" })}</span>
                <span className="method-desc">{t("score.gradeValidity.cDesc")}</span>
              </th>
              <td>{g.C.n}</td>
              <td>{g.C.forecast_ci_crps_mean.toFixed(2)} [{g.C.forecast_ci_crps_ci95[0].toFixed(2)}, {g.C.forecast_ci_crps_ci95[1].toFixed(2)}]</td>
              <td>{t("score.daysShort", { v: g.C.forecast_peak_abs_err_mean.toFixed(1) })}</td>
              <td>{Math.round(g.C.forecast_ci_covered90_share * 100)} %</td>
            </tr>
            <tr>
              <th scope="row">
                <span className="method-name">{t("score.gradeLabel", { grade: "D" })}</span>
                <span className="method-desc">{t("score.gradeValidity.dDesc")}</span>
              </th>
              <td>{g.D.n}</td>
              <td>{g.D.forecast_ci_crps_mean.toFixed(2)} [{g.D.forecast_ci_crps_ci95[0].toFixed(2)}, {g.D.forecast_ci_crps_ci95[1].toFixed(2)}]</td>
              <td>{t("score.daysShort", { v: g.D.forecast_peak_abs_err_mean.toFixed(1) })}</td>
              <td>{Math.round(g.D.forecast_ci_covered90_share * 100)} %</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="muted" style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
        {t("score.gradeValidity.primaryRule")}
      </p>
      <p className="muted" style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
        {t("score.gradeValidity.credNote")}
      </p>
    </section>
  );
}

export function CqrScoreSection() {
  return (
    <section className="score-block" aria-labelledby="score-cqr-h">
      <h4 id="score-cqr-h">
        {t("score.cqr.heading")} <Explain id="hindcast" />
      </h4>
      <p className="muted">
        {t("score.cqr.intro", {
          blocks: CQR_EVALUATION.nSpatialBlocks,
          calRows: CQR_EVALUATION.nCalRows,
          testRows: CQR_EVALUATION.nTestRows,
        })}
      </p>
      <div className="table-wrap">
        <table className="scores">
          <thead>
            <tr>
              <th scope="col">{t("score.cqr.thCrop")}</th>
              <th scope="col">{t("score.cqr.thMetric")}</th>
              <th scope="col">{t("score.n")}</th>
              <th scope="col">{t("score.cqr.thRaw")}</th>
              <th scope="col">{t("score.cqr.thSym")}</th>
              <th scope="col">{t("score.cqr.thAsym")}</th>
              <th scope="col">{t("score.cqr.thGate")}</th>
            </tr>
          </thead>
          <tbody>
            {CQR_EVALUATION.rows.map((r) => (
              <tr key={`${r.crop}-${r.metric}`} className={r.gate8595 === "pass" ? "row-current" : undefined}>
                <th scope="row">{cropName(r.crop)}</th>
                <td>{metricName(r.metric)}</td>
                <td>{r.n}</td>
                <td>
                  {(r.storedCov90 * 100).toFixed(1)} % ({r.storedWinkler90.toFixed(1)})
                </td>
                <td className={r.cqrSymCov90 >= 0.85 && r.cqrSymCov90 <= 0.95 ? "best" : undefined}>
                  {(r.cqrSymCov90 * 100).toFixed(1)} % ({r.cqrSymWinkler90.toFixed(1)})
                </td>
                <td className={r.cqrAsymCov90 >= 0.85 && r.cqrAsymCov90 <= 0.95 ? "best" : undefined}>
                  {(r.cqrAsymCov90 * 100).toFixed(1)} % ({r.cqrAsymWinkler90.toFixed(1)})
                </td>
                <td>
                  <span className={r.gate8595 === "pass" ? "yes-badge" : "no-badge"}>
                    {t(r.gate8595 === "pass" ? "score.cqr.pass" : "score.cqr.fail")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
        {t("score.cqr.note")}
      </p>
    </section>
  );
}

export function RegionGradeSummary({ index }: { index: RegionIndex }) {
  const counts = { A: 0, B: 0, C: 0, D: 0 };
  for (const f of index.fields) {
    if (f.top_grade in counts) counts[f.top_grade]++;
  }
  const isKansas = index.region_id === "ks_t14slh";
  return (
    <section className="score-block" aria-labelledby="score-grade-dist">
      <h4 id="score-grade-dist">
        {t("score.gradeDist.heading", { region: index.name, n: index.fields.length })}{" "}
        <Explain id="evidence_grade" />
      </h4>
      <div className="grade-distribution-row">
        {(["A", "B", "C", "D"] as const).map((g) => (
          <div key={g} className="grade-stat-pill">
            <span className={`grade grade-${g}`} aria-hidden="true">
              {g}
            </span>
            <strong>{counts[g]}</strong>
            <span className="muted">{t("score.gradeDist.fields")}</span>
          </div>
        ))}
      </div>
      <p className="muted" style={{ fontSize: "0.86rem", marginTop: "0.25rem", marginBottom: "0.25rem" }}>
        <strong>{t(isKansas ? "score.gradeDist.metaKansas" : "score.gradeDist.metaUkraine")}</strong>
      </p>
      <p className="muted" style={{ fontSize: "0.86rem", marginTop: "0.25rem" }}>
        {t(isKansas ? "score.gradeDist.kansasNote" : "score.gradeDist.ukraineNote")}
      </p>
    </section>
  );
}

export function Scoreboard({ index }: { index: RegionIndex }) {
  const [h, setH] = useState<RegionHindcast | null>(null);
  const [story, setStory] = useState<FieldPack | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<HindcastRow["mode"]>("forecast");
  const region = index.region_id;

  useEffect(() => {
    setH(null);
    setActiveHindcast(null);
    setStory(null);
    setError(null);
    loadHindcast(region)
      .then((x) => {
        setH(x);
        setActiveHindcast(x);
        setMode(modesOf(x)[0] ?? "forecast");
        return loadPack(region, x.story_field_id).then(setStory);
      })
      .catch((e: Error) => setError(e.message));
  }, [region]);

  if (error) return <p className="muted">{t("score.missing")}</p>;
  if (!h) return <p>{t("region.loading")}</p>;
  const modes = modesOf(h);
  const years = h.scored_years;
  const notRun = methodsNotRun(h);
  const otherMethodsCount = new Set(h.rows.map((r) => r.method).filter((m) => m !== "fieldwitness")).size;

  return (
    <article className="scoreboard" aria-labelledby="score-h">
      <h2 id="score-h">
        {t("score.heading", { region: index.name })} <Explain id="hindcast" />
      </h2>
      <p>
        {otherMethodsCount > 0
          ? t("score.intro", {
              cutoff: date(h.cutoff),
              first: years[0] ?? "",
              last: years[years.length - 1] ?? "",
              n: otherMethodsCount,
            })
          : t("score.introSingle", {
              cutoff: date(h.cutoff),
              first: years[0] ?? "",
              last: years[years.length - 1] ?? "",
            })}
      </p>
      {notRun.length > 0 && <p className="muted">{t("score.notRun", { methods: notRun.join(", ") })}</p>}
      <p className="muted">{t("score.honest")}</p>
      {h.crop_observed_source === "classifier" && (
        <p className="notice">{t("score.classifier")}</p>
      )}
      <RegionGradeSummary index={index} />
      {modes.length > 1 && (
        <fieldset className="radio-row">
          <legend>{t("score.mode")}</legend>
          {modes.map((m) => (
            <label key={m}>
              <input type="radio" name="hindcast-mode" checked={mode === m} onChange={() => setMode(m)} />{" "}
              {t(`score.mode.${m}`)}
            </label>
          ))}
        </fieldset>
      )}
      <p className="muted">{t(`score.mode.${mode}.note`)}</p>
      {metricsOf(h, mode).map((m) => (
        <ScoreTable key={m} metric={m} rows={rowsFor(h, mode, m)} />
      ))}
      {region === "ks_t14slh" && (
        <>
          <CqrScoreSection />
          <GradeValiditySection />
          <DiagnosisSection />
        </>
      )}
      <UkraineNeighboursSection />
      <div className="score-story">
        {story ? <Backtest pack={story} mode={mode} /> : <p>{t("field.loading")}</p>}
        <p>
          {t("score.story")}{" "}
          <a href={routeHref(region, h.story_field_id)}>
            {t("field.heading", { id: h.story_field_id.slice(0, 8) })}
          </a>
        </p>
      </div>
      <TagLegend />
    </article>
  );
}
