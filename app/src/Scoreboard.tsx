import { useEffect, useState } from "react";
import { Backtest } from "./AdvisorConsole";
import { loadHindcast, loadPack } from "./data";
import { formatDate } from "./format";
import { type ScoreKey, TIMING_METRICS, bestMethods, metricsOf, modesOf, rowsFor } from "./hindcast";
import { routeHref } from "./route";
import { metricName, t } from "./strings";
import { TagLegend } from "./tags";
import type { FieldPack, HindcastRow, RegionHindcast, RegionIndex } from "./types";

const date = (iso: string) => formatDate(new Date(`${iso}T00:00:00Z`));

function fmt(key: ScoreKey, v: number): string {
  if (key === "covered50" || key === "covered90") return `${Math.round(v * 100)} %`;
  return v.toLocaleString("en", { maximumFractionDigits: key === "crps" ? 2 : 1 });
}

function ScoreTable({ rows, metric }: { rows: HindcastRow[]; metric: string }) {
  const keys: ScoreKey[] = ["crps", "covered50", "covered90"];
  if (TIMING_METRICS.has(metric)) keys.push("timing_err_days");
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

export function Scoreboard({ index }: { index: RegionIndex }) {
  const [h, setH] = useState<RegionHindcast | null>(null);
  const [story, setStory] = useState<FieldPack | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<HindcastRow["mode"]>("forecast");
  const region = index.region_id;

  useEffect(() => {
    setH(null);
    setStory(null);
    setError(null);
    loadHindcast(region)
      .then((x) => {
        setH(x);
        setMode(modesOf(x)[0] ?? "forecast");
        return loadPack(region, x.story_field_id).then(setStory);
      })
      .catch((e: Error) => setError(e.message));
  }, [region]);

  if (error) return <p className="muted">{t("score.missing")}</p>;
  if (!h) return <p>{t("region.loading")}</p>;
  const modes = modesOf(h);
  const years = h.scored_years;

  return (
    <article className="scoreboard" aria-labelledby="score-h">
      <h2 id="score-h">{t("score.heading", { region: index.name })}</h2>
      <p>
        {t("score.intro", {
          cutoff: date(h.cutoff),
          first: years[0] ?? "",
          last: years[years.length - 1] ?? "",
        })}
      </p>
      <p className="muted">{t("score.honest")}</p>
      {h.crop_observed_source === "classifier" && (
        <p className="notice">{t("score.classifier")}</p>
      )}
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
      <div className="score-story">
        {story ? <Backtest pack={story} /> : <p>{t("field.loading")}</p>}
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
