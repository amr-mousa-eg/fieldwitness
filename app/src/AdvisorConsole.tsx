import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  ErrorBar,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CropChips } from "./CropChips";
import {
  type BacktestRow,
  WITNESSES,
  backtestMetrics,
  backtestOffsets,
  backtestRows,
  inside,
  missingWitnesses,
  witnessRows,
} from "./advisor";
import { formatDate, formatTagged, harvestDayToDate } from "./format";
import { cropName, metricName, optionName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import type { FieldPack, Option, Tagged, WitnessResult } from "./types";

const CHART = { pred: "#3d6f8e", obs: "#8a6a1f" };
const SEASON_DAY_UNIT = "day of harvest year";

/** Season-date metrics print as calendar dates; everything else as a tagged number. */
function MetricValue({ v, year }: { v: Tagged; year: number }) {
  if (v.unit === SEASON_DAY_UNIT && v.value !== null) {
    return <TaggedValue v={v} text={formatDate(harvestDayToDate(year, v.value))} />;
  }
  return <TaggedValue v={v} />;
}

/** A 50 % or 90 % range; season-date ranges print as calendar dates when `year` is given. */
function Range({ v, level, year }: { v: Tagged; level: 50 | 90; year?: number }) {
  const lo = level === 50 ? v.lo50 : v.lo90;
  const hi = level === 50 ? v.hi50 : v.hi90;
  if (lo == null || hi == null) return null;
  const fmt = (x: number) =>
    year !== undefined && v.unit === SEASON_DAY_UNIT
      ? formatDate(harvestDayToDate(year, x))
      : formatTagged({ ...v, value: x });
  return (
    <span className="range">
      {t(level === 50 ? "advisor.range50" : "advisor.range90", { lo: fmt(lo), hi: fmt(hi) })}
    </span>
  );
}

function Diagnostics({ d }: { d: WitnessResult["diagnostics"] }) {
  const entries = Object.entries(d);
  if (entries.length === 0) return null;
  return (
    <ul className="diagnostics" aria-label={t("advisor.diagnostics")}>
      {entries.map(([k, v]) => (
        <li key={k}>
          <code>{k}</code> {String(v)}
        </li>
      ))}
    </ul>
  );
}

function WitnessCell({ w }: { w: WitnessResult | undefined }) {
  if (!w) return <td className="muted">{t("advisor.noEstimate")}</td>;
  return (
    <td>
      <TaggedValue v={w.estimate} />
      <Range v={w.estimate} level={50} />
      <Range v={w.estimate} level={90} />
      {w.n != null && <span className="witness-n">{t("advisor.n", { n: w.n })}</span>}
      <Diagnostics d={w.diagnostics} />
    </td>
  );
}

function OptionWitnesses({ option }: { option: Option }) {
  const rows = witnessRows(option);
  const missing = missingWitnesses(option);
  return (
    <details className="witness-option" open={option.rank === 1}>
      <summary>
        <span className="witness-option-name">
          {t("advisor.optionHead", { rank: option.rank, name: optionName(option) })}{" "}
          <span className={`grade grade-${option.grade}`}>
            <span className="sr-only">{t("card.grade")} </span>
            {option.grade}
          </span>
        </span>
      </summary>
      <CropChips sequence={option.sequence} />
      <div className="table-wrap">
        <table className="witness-table">
          <caption className="sr-only">{t("advisor.tableCaption", { name: optionName(option) })}</caption>
          <thead>
            <tr>
              <th scope="col">{t("detail.metric")}</th>
              {WITNESSES.map((w) => (
                <th key={w} scope="col">
                  {t(`witness.${w}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.metric}>
                <th scope="row">{metricName(r.metric)}</th>
                {WITNESSES.map((w) => (
                  <WitnessCell key={w} w={r.cells[w]} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {missing.length > 0 && (
        <p className="muted">
          {t("advisor.missing", { names: missing.map((w) => t(`witness.${w}`)).join(", ") })}
        </p>
      )}
      <ul className="grade-reasons">
        {option.grade_reasons.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </details>
  );
}

function seasonLabel(r: BacktestRow): string {
  return `${r.season_year}${r.season_index > 0 ? ` (${r.season_index + 1})` : ""} ${cropName(r.crop)}`;
}

function Hit({ v }: { v: boolean | null }) {
  if (v === null) return <span className="muted">{t("value.none")}</span>;
  // Text carries the meaning; the symbol only supports it (T9.7).
  return (
    <span className={v ? "hit" : "miss"}>
      <span aria-hidden="true">{v ? "✓ " : "✗ "}</span>
      {t(v ? "advisor.inside" : "advisor.outside")}
    </span>
  );
}

/** Predicted vs observed seasons from a pack's ledger; also the scoreboard's story chart (T9.5). */
export function Backtest({ pack }: { pack: FieldPack }) {
  const metrics = useMemo(() => backtestMetrics(pack.ledger), [pack.ledger]);
  const [metric, setMetric] = useState(metrics[0] ?? "");
  const rows = useMemo(() => backtestRows(pack.ledger, metric), [pack.ledger, metric]);
  if (metrics.length === 0) {
    return (
      <section aria-labelledby="backtest-h">
        <h3 id="backtest-h">{t("advisor.backtest")}</h3>
        <p className="muted">{t("advisor.backtest.none")}</p>
      </section>
    );
  }
  const unit = rows[0]?.predicted.unit ?? "";
  const unitShort = unit === SEASON_DAY_UNIT ? t("advisor.days") : unit;
  const data = backtestOffsets(rows).map((o, i) => ({ label: seasonLabel(rows[i]), ...o }));
  const asOf = [...new Set(pack.ledger.map((e) => e.as_of))].sort().map((d) => formatDate(new Date(`${d}T00:00:00Z`)));

  return (
    <section aria-labelledby="backtest-h">
      <h3 id="backtest-h">{t("advisor.backtest")}</h3>
      <p className="muted">{t("advisor.backtest.note", { asof: asOf.join(", ") })}</p>
      <div className="chart-controls">
        <label>
          {t("advisor.backtest.metric")}{" "}
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metrics.map((m) => (
              <option key={m} value={m}>
                {metricName(m)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ul className="chart-key">
        <li>
          <span className="key-dot" style={{ background: CHART.pred }} /> {t("advisor.predicted")}{" "}
          <TagBadge tag={rows[0].predicted.tag} source={rows[0].predicted.source} />
        </li>
        <li>
          <span className="key-diamond" style={{ background: CHART.obs }} /> {t("advisor.observed")}{" "}
          <TagBadge tag={rows[0].observed.tag} source={rows[0].observed.source} />
        </li>
        <li className="muted">{t("advisor.backtest.unit", { unit: unitShort })}</li>
      </ul>
      <div className="chart" role="img" aria-label={t("advisor.backtest.alt")}>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="label" type="category" padding={{ left: 60, right: 60 }} />
            <YAxis width={48} domain={["auto", "auto"]} />
            <ReferenceLine y={0} stroke={CHART.pred} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? null : Number(v).toFixed(1))} />
            <Scatter dataKey="pred" name={t("advisor.predicted")} fill={CHART.pred} isAnimationActive={false}>
              <ErrorBar dataKey="err" direction="y" width={8} stroke={CHART.pred} />
            </Scatter>
            <Scatter dataKey="obs" name={t("advisor.observed")} fill={CHART.obs} shape="diamond" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="table-wrap">
        <table className="mini">
          <thead>
            <tr>
              <th scope="col">{t("advisor.season")}</th>
              <th scope="col">{t("advisor.predicted")}</th>
              <th scope="col">{t("advisor.observed")}</th>
              <th scope="col">{t("advisor.in50")}</th>
              <th scope="col">{t("advisor.in90")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.season_year}-${r.season_index}`}>
                <th scope="row">{seasonLabel(r)}</th>
                <td>
                  <MetricValue v={r.predicted} year={r.season_year} />
                  <Range v={r.predicted} level={90} year={r.season_year} />
                </td>
                <td>
                  <MetricValue v={r.observed} year={r.season_year} />
                </td>
                <td>
                  <Hit v={inside(r.predicted, r.observed, 50)} />
                </td>
                <td>
                  <Hit v={inside(r.predicted, r.observed, 90)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function AdvisorConsole({ pack }: { pack: FieldPack }) {
  const options = [...pack.options].sort((a, b) => a.rank - b.rank);
  return (
    <div className="advisor">
      <section className="advisor-top" aria-labelledby="cred-h">
        <div>
          <h3 id="cred-h">{t("advisor.credibility")}</h3>
          <p className="big-number">
            <TaggedValue v={pack.credibility} />
          </p>
          <Range v={pack.credibility} level={90} />
          <p className="muted">{t("advisor.credibility.note")}</p>
        </div>
        <div>
          <h3>{t("advisor.next")}</h3>
          <p>{pack.advice.measure_next}</p>
          <h3>{t("advisor.flip")}</h3>
          <p>{pack.advice.counterfactual_flip}</p>
          <p>
            {t("advisor.flipProb")} <TaggedValue v={pack.advice.flip_probability} />
          </p>
        </div>
      </section>
      <section aria-labelledby="witness-h">
        <h3 id="witness-h">{t("advisor.witnesses")}</h3>
        <p className="muted">{t("advisor.witnesses.note")}</p>
        {options.map((o) => (
          <OptionWitnesses key={o.option_id} option={o} />
        ))}
      </section>
      <Backtest pack={pack} />
    </div>
  );
}
