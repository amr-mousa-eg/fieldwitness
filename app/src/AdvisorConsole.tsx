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
import { Explain, MetricLabel } from "./Explain";
import {
  type BacktestRow,
  WITNESSES,
  backtestMetrics,
  backtestOffsets,
  backtestRows,
  inside,
  ledgerModes,
  missingWitnesses,
  witnessRows,
} from "./advisor";
import {
  formatDate,
  formatTagged,
  harvestDayToDate,
  localizeCounterfactualFlip,
  localizeGradeReason,
  localizeMeasureNext,
} from "./format";
import { cropName, metricName, optionName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import { CHART_COLOURS } from "./theme";
import type { FieldPack, LedgerEntry, Option, Tagged, WitnessResult } from "./types";
import { useTheme } from "./useTheme";

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

/** `place` = 1-based place among the alternatives; null for Current (the reference, not ranked). */
function OptionWitnesses({ option, place }: { option: Option; place: number | null }) {
  const rows = witnessRows(option);
  const missing = missingWitnesses(option);
  return (
    <details className="witness-option" open={place === 1}>
      <summary>
        <span className="witness-option-name">
          {place === null
            ? t("advisor.currentHead", { name: optionName(option) })
            : t("advisor.optionHead", { rank: place, name: optionName(option) })}{" "}
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
                  {w === "physics" && <Explain id="water_balance" />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.metric}>
                <th scope="row">
                  <MetricLabel metric={r.metric} />
                </th>
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
          <li key={i}>{localizeGradeReason(s)}</li>
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
export function Backtest({ pack, mode: fixedMode }: { pack: FieldPack; mode?: LedgerEntry["mode"] }) {
  const { effective } = useTheme();
  const chart = CHART_COLOURS[effective];
  const metrics = useMemo(() => backtestMetrics(pack.ledger), [pack.ledger]);
  const modes = useMemo(() => ledgerModes(pack.ledger), [pack.ledger]);
  const [metric, setMetric] = useState(metrics[0] ?? "");
  const [ownMode, setOwnMode] = useState<LedgerEntry["mode"]>(modes[0] ?? "forecast");
  const mode = fixedMode ?? ownMode; // the scoreboard sets the mode; the advisor offers a choice
  const rows = useMemo(() => backtestRows(pack.ledger, metric, mode), [pack.ledger, metric, mode]);
  if (metrics.length === 0 || rows.length === 0) {
    return (
      <section aria-labelledby="backtest-h">
        <h3 id="backtest-h">
          {t("advisor.backtest")} <Explain id="hindcast" />
        </h3>
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
      <h3 id="backtest-h">
        {t("advisor.backtest")} <Explain id="hindcast" />
      </h3>
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
        {!fixedMode && modes.length > 1 && (
          <label>
            {t("score.mode")}{" "}
            <select value={mode} onChange={(e) => setOwnMode(e.target.value as LedgerEntry["mode"])}>
              {modes.map((m) => (
                <option key={m} value={m}>
                  {t(`score.mode.${m}`)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <ul className="chart-key">
        <li>
          <span className="key-dot" style={{ background: chart.pred }} /> {t("advisor.predicted")}{" "}
          <TagBadge tag={rows[0].predicted.tag} source={rows[0].predicted.source} />
        </li>
        <li>
          <span className="key-diamond" style={{ background: chart.obs }} /> {t("advisor.observed")}{" "}
          <TagBadge tag={rows[0].observed.tag} source={rows[0].observed.source} />
        </li>
        <li className="muted">{t("advisor.backtest.unit", { unit: unitShort })}</li>
      </ul>
      <div className="chart" role="img" aria-label={t("advisor.backtest.alt")}>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={chart.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="label"
              type="category"
              padding={{ left: 60, right: 60 }}
              stroke={chart.axis}
              tick={{ fill: chart.axis, fontSize: 12 }}
            />
            <YAxis width={48} domain={["auto", "auto"]} stroke={chart.axis} tick={{ fill: chart.axis, fontSize: 12 }} />
            <ReferenceLine y={0} stroke={chart.pred} />
            <Tooltip
              contentStyle={{ backgroundColor: chart.tooltipBg, borderColor: chart.tooltipBorder, color: chart.tooltipText }}
              formatter={(v) => (Array.isArray(v) ? null : Number(v).toFixed(1))}
            />
            <Scatter dataKey="pred" name={t("advisor.predicted")} fill={chart.pred} isAnimationActive={false}>
              <ErrorBar dataKey="err" direction="y" width={8} stroke={chart.pred} />
            </Scatter>
            <Scatter dataKey="obs" name={t("advisor.observed")} fill={chart.obs} shape="diamond" isAnimationActive={false} />
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
  // Current first as the reference; then the alternatives in the pack's rank order, numbered 1, 2, …
  // (pipeline packs give Current rank 0 and number alternatives from 0; fixtures from 1).
  const current = pack.options.filter((o) => o.option_id === "current");
  const alternatives = pack.options.filter((o) => o.option_id !== "current").sort((a, b) => a.rank - b.rank);
  return (
    <div className="advisor">
      <section className="advisor-limits-callout" aria-label={t("advisor.caveats.aria")}>
        <p className="fixed-line">{t("fixed.judgment")}</p>
        <div className="callout-grid">
          <div className="callout-item">
            <strong>{t("advisor.caveats.hindcast.title")}</strong> {t("advisor.caveats.hindcast.body")}
          </div>
          <div className="callout-item">
            <strong>{t("advisor.caveats.neighbour.title")}</strong> {t("advisor.caveats.neighbour.body")}
          </div>
          <div className="callout-item">
            <strong>{t("advisor.caveats.season.title")}</strong> {t("advisor.caveats.season.body")}
          </div>
        </div>
      </section>
      <section className="advisor-top" aria-labelledby="cred-h">
        <div>
          <h3 id="cred-h">
            {t("advisor.credibility")} <Explain id="credibility" />
          </h3>
          <p className="big-number">
            <TaggedValue v={pack.credibility} />
          </p>
          <Range v={pack.credibility} level={90} />
          <p className="muted">{t("advisor.credibility.note")}</p>
        </div>
        <div>
          <h3>{t("advisor.next")}</h3>
          <p>{localizeMeasureNext(pack.advice.measure_next)}</p>
          <h3>
            {t("advisor.flip")} <Explain id="flip_probability" />
          </h3>
          <p>{localizeCounterfactualFlip(pack.advice.counterfactual_flip)}</p>
          <p>
            {t("advisor.flipProb")} <TaggedValue v={pack.advice.flip_probability} />
          </p>
        </div>
      </section>
      <section aria-labelledby="witness-h">
        <h3 id="witness-h">
          {t("advisor.witnesses")} <Explain id="witness" />
        </h3>
        <p className="muted">{t("advisor.witnesses.note")}</p>
        {current.map((o) => (
          <OptionWitnesses key={o.option_id} option={o} place={null} />
        ))}
        {alternatives.map((o, i) => (
          <OptionWitnesses key={o.option_id} option={o} place={i + 1} />
        ))}
      </section>
      <Backtest pack={pack} />
    </div>
  );
}
