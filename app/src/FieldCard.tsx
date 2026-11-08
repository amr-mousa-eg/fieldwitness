import { Fragment, useEffect, useMemo, useState } from "react";
import { CorrectionPanel } from "./CorrectionPanel";
import { CropChips } from "./CropChips";
import { Explain, MetricLabel } from "./Explain";
import { loadScenarios } from "./data";
import { formatDelta, formatTagged } from "./format";
import {
  type Constraints,
  DEFAULT_PRIORITIES,
  NO_CONSTRAINTS,
  NOT_SOLD,
  PRIORITY_KEYS,
  type Priorities,
  type Ranked,
  type Violation,
  findScenario,
  isDefault,
  rankOptions,
} from "./rank";
import { cropName, metricName, optionName, t } from "./strings";
import { TaggedValue } from "./tags";
import type { FieldPack, FieldScenarios, Tagged } from "./types";

const TABLE_METRICS = ["water_use_mm", "bad_year_water_mm", "cover_days", "ryi"] as const;
const TEMPS = [0, 1, 2];
const RAINS = [-20, -10, 0, 10];

/** Per-viewer convenience: survives reloads, never required (storage may be blocked). */
function useStored<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? { ...initial, ...JSON.parse(raw) } : initial;
    } catch {
      return initial;
    }
  });
  const set = (v: T) => {
    setValue(v);
    try {
      localStorage.setItem(key, JSON.stringify(v));
    } catch {
      /* storage blocked: keep the in-memory value */
    }
  };
  return [value, set];
}

function why(v: Violation): string {
  switch (v.kind) {
    case "dontWant":
    case "cantGrow":
    case "cantSell":
      return t(`why.${v.kind}`, { crop: cropName(v.crop) });
    case "irrigation":
      return t("why.irrigation", { value: formatTagged(v.value) });
    case "waterCap":
      return t("why.waterCap", { value: formatTagged(v.value), cap: v.cap });
  }
}

function signed(v: number, unit: "temp" | "rain"): string {
  const s = v > 0 ? `+${v}` : v < 0 ? `−${-v}` : "0";
  return t(unit === "temp" ? "whatif.tempValue" : "whatif.rainValue", { v: s });
}

function Cell({ v, current }: { v: Tagged | undefined; current: Tagged | undefined }) {
  if (!v) return <td className="muted">{t("value.none")}</td>;
  const delta = current && v !== current ? formatDelta(v, current) : null;
  return (
    <td>
      <TaggedValue v={v} />
      {delta && <span className="delta">{t("card.vsCurrent", { delta })}</span>}
    </td>
  );
}

function Detail({ row, current }: { row: Ranked; current: Ranked | undefined }) {
  const o = row.option;
  const parts = ["why", "evidence", "benefits", "gaps", "risks"] as const;
  return (
    <div className="detail">
      <div className="detail-explain">
        {parts.map((p) => (
          <section key={p}>
            <h4>{t(`detail.${p}`)}</h4>
            <ul>
              {o.explanation[p].map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </section>
        ))}
        <section>
          <h4>{t("detail.gradeReasons")}</h4>
          <ul>
            {o.grade_reasons.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      </div>
      <section>
        <h4>{t("detail.witnesses")}</h4>
        <table className="mini">
          <thead>
            <tr>
              <th>{t("detail.witness")}</th>
              <th>{t("detail.metric")}</th>
              <th>{t("detail.estimate")}</th>
              <th>{t("detail.n")}</th>
            </tr>
          </thead>
          <tbody>
            {o.witnesses.map((w, i) => (
              <tr key={i}>
                <td>{t(`witness.${w.witness}`)}</td>
                <td>{metricName(w.metric)}</td>
                <td>
                  <TaggedValue v={w.estimate} />
                </td>
                <td>{w.n ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h4>{t("detail.metrics")}</h4>
        <dl className="metric-list">
          {Object.entries(row.metrics).map(([k, v]) => {
            const delta = current && row !== current ? formatDelta(v, current.metrics[k] ?? v) : null;
            return (
              <div key={k}>
                <dt>
                  <MetricLabel metric={k} />
                </dt>
                <dd>
                  <TaggedValue v={v} />
                  {delta && <span className="delta">{t("card.vsCurrent", { delta })}</span>}
                </dd>
              </div>
            );
          })}
          <div>
            <dt>{t("detail.regret")}</dt>
            <dd>
              <TaggedValue v={o.regret} />
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function PriorityPanel({ p, set }: { p: Priorities; set: (p: Priorities) => void }) {
  return (
    <fieldset className="panel">
      <legend>{t("prio.heading")}</legend>
      {PRIORITY_KEYS.map((k) => (
        <label key={k} className="slider">
          <span>{t(`prio.${k}`)}</span>
          <input
            type="range"
            min={0}
            max={3}
            step={1}
            value={p[k]}
            aria-valuetext={t(`prio.level.${p[k]}` as "prio.level.0")}
            onChange={(e) => set({ ...p, [k]: Number(e.target.value) })}
          />
          <output>{t(`prio.level.${p[k]}` as "prio.level.0")}</output>
        </label>
      ))}
      <button type="button" onClick={() => set(DEFAULT_PRIORITIES)} disabled={isDefault(p)}>
        {t("prio.reset")}
      </button>
    </fieldset>
  );
}

function ConstraintPanel({ crops, c, set }: { crops: string[]; c: Constraints; set: (c: Constraints) => void }) {
  const toggle = (list: string[], crop: string, on: boolean) => (on ? [...list, crop] : list.filter((x) => x !== crop));
  const sellable = c.canSell ?? crops.filter((x) => !NOT_SOLD.has(x));
  return (
    <fieldset className="panel">
      <legend>{t("cons.heading")}</legend>
      <table className="mini constraints">
        <thead>
          <tr>
            <th>{t("cons.crop")}</th>
            <th>{t("cons.dontWant")}</th>
            <th>{t("cons.cantGrow")}</th>
            <th>{t("cons.canSell")}</th>
          </tr>
        </thead>
        <tbody>
          {crops.map((crop) => (
            <tr key={crop}>
              <th scope="row">{cropName(crop)}</th>
              <td>
                <input
                  type="checkbox"
                  aria-label={`${cropName(crop)}: ${t("cons.dontWant")}`}
                  checked={c.dontWant.includes(crop)}
                  onChange={(e) => set({ ...c, dontWant: toggle(c.dontWant, crop, e.target.checked) })}
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  aria-label={`${cropName(crop)}: ${t("cons.cantGrow")}`}
                  checked={c.cantGrow.includes(crop)}
                  onChange={(e) => set({ ...c, cantGrow: toggle(c.cantGrow, crop, e.target.checked) })}
                />
              </td>
              <td>
                {NOT_SOLD.has(crop) ? (
                  <span className="muted">{t("cons.notSold")}</span>
                ) : (
                  <input
                    type="checkbox"
                    aria-label={`${cropName(crop)}: ${t("cons.canSell")}`}
                    checked={sellable.includes(crop)}
                    onChange={(e) => set({ ...c, canSell: toggle(sellable, crop, e.target.checked) })}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="radio-row" role="radiogroup" aria-label={t("cons.irrigation")}>
        <span>{t("cons.irrigation")}</span>
        {(["unset", "yes", "no"] as const).map((v) => (
          <label key={v}>
            <input type="radio" name="irrigation" checked={c.irrigation === v} onChange={() => set({ ...c, irrigation: v })} />{" "}
            {t(`cons.irrigation.${v}`)}
          </label>
        ))}
      </div>
      <label className="cap">
        {t("cons.waterCap")}
        <input
          type="number"
          min={0}
          step={10}
          inputMode="numeric"
          value={c.waterCapMm ?? ""}
          onChange={(e) => set({ ...c, waterCapMm: e.target.value === "" ? null : Number(e.target.value) })}
        />
      </label>
    </fieldset>
  );
}

function WhatIfPanel({
  scenarios,
  dt,
  dp,
  set,
}: {
  scenarios: FieldScenarios | null;
  dt: number;
  dp: number;
  set: (dt: number, dp: number) => void;
}) {
  if (!scenarios) {
    return (
      <fieldset className="panel">
        <legend>{t("whatif.heading")}</legend>
        <p className="muted">{t("whatif.missing")}</p>
      </fieldset>
    );
  }
  return (
    <fieldset className="panel">
      <legend>{t("whatif.heading")}</legend>
      <p className="muted">{scenarios.note}</p>
      <label className="slider">
        <span>{t("whatif.temp")}</span>
        <input
          type="range"
          min={0}
          max={TEMPS.length - 1}
          step={1}
          value={TEMPS.indexOf(dt)}
          aria-valuetext={signed(dt, "temp")}
          onChange={(e) => set(TEMPS[Number(e.target.value)], dp)}
        />
        <output>{signed(dt, "temp")}</output>
      </label>
      <label className="slider">
        <span>{t("whatif.rain")}</span>
        <input
          type="range"
          min={0}
          max={RAINS.length - 1}
          step={1}
          value={RAINS.indexOf(dp)}
          aria-valuetext={signed(dp, "rain")}
          onChange={(e) => set(dt, RAINS[Number(e.target.value)])}
        />
        <output>{signed(dp, "rain")}</output>
      </label>
    </fieldset>
  );
}

export function FieldCard({ pack, regionId }: { pack: FieldPack; regionId: string }) {
  const fid = pack.field.field_id;
  const [scenarios, setScenarios] = useState<FieldScenarios | null>(null);
  const [priorities, setPriorities] = useStored<Priorities>(`fw:${fid}:priorities`, DEFAULT_PRIORITIES);
  const [constraints, setConstraints] = useStored<Constraints>(`fw:${fid}:constraints`, NO_CONSTRAINTS);
  const [[dt, dp], setWeather] = useState<[number, number]>([0, 0]);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    setScenarios(null);
    loadScenarios(regionId, fid)
      .then(setScenarios)
      .catch(() => setScenarios(null));
  }, [regionId, fid]);

  const scenario = dt === 0 && dp === 0 ? null : findScenario(scenarios, dt, dp);
  const rows = useMemo(
    () => rankOptions(pack.options, priorities, constraints, scenario),
    [pack.options, priorities, constraints, scenario],
  );
  const kept = rows.filter((r) => r.kept);
  const dropped = rows.filter((r) => !r.kept);
  const current = rows.find((r) => r.option.option_id === "current");
  const crops = useMemo(() => [...new Set(pack.options.flatMap((o) => o.sequence))].sort(), [pack.options]);

  return (
    <div className="card-layout">
      <section className="card-main" aria-labelledby="card-h">
        <h3 id="card-h">{t("card.heading")}</h3>
        <p className="muted">
          {t("card.intro")} {t(isDefault(priorities) ? "card.ranking.default" : "card.ranking.mine")}
        </p>
        {scenario && (
          <p className="notice" role="status">
            {t("whatif.active", { temp: signed(dt, "temp"), rain: signed(dp, "rain") })}
          </p>
        )}
        {current && current.violations.length > 0 && (
          <div className="notice">
            {t("card.excluded.current")}
            <ul>
              {current.violations.map((v, i) => (
                <li key={i}>{why(v)}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="table-wrap">
          <table className="options">
            <thead>
              <tr>
                <th scope="col">{t("card.rank")}</th>
                <th scope="col">{t("card.option")}</th>
                {TABLE_METRICS.map((m) => (
                  <th key={m} scope="col">
                    <MetricLabel metric={m} />
                  </th>
                ))}
                <th scope="col">
                  {t("card.grade")}
                  <Explain id="evidence_grade" />
                </th>
                <th scope="col">
                  <span className="sr-only">{t("card.details.show")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {kept.map((r) => {
                const id = r.option.option_id;
                const isOpen = open === id;
                return (
                  <Fragment key={id}>
                    <tr className={id === "current" ? "row-current" : undefined}>
                      <td className="rank">{r.rank}</td>
                      <th scope="row">
                        <span className="option-name">{optionName(r.option)}</span>
                        <CropChips sequence={r.option.sequence} />
                      </th>
                      {TABLE_METRICS.map((m) => (
                        <Cell key={m} v={r.metrics[m]} current={current?.metrics[m]} />
                      ))}
                      <td>
                        <span className={`grade grade-${r.option.grade}`}>{r.option.grade}</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          aria-expanded={isOpen}
                          aria-controls={`detail-${id}`}
                          onClick={() => setOpen(isOpen ? null : id)}
                        >
                          {t(isOpen ? "card.details.hide" : "card.details.show")}
                        </button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr id={`detail-${id}`} className="detail-row">
                        <td colSpan={TABLE_METRICS.length + 4}>
                          <Detail row={r} current={current} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        {dropped.length > 0 && (
          <details className="dropped">
            <summary>{t("card.excluded", { n: dropped.length })}</summary>
            <ul>
              {dropped.map((r) => (
                <li key={r.option.option_id}>
                  <strong>{optionName(r.option)}</strong> <CropChips sequence={r.option.sequence} />
                  <ul>
                    {r.violations.map((v, i) => (
                      <li key={i}>{why(v)}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </details>
        )}
        <p className="fixed-line">{t("fixed.judgment")}</p>
      </section>
      <aside className="card-controls">
        <PriorityPanel p={priorities} set={setPriorities} />
        <WhatIfPanel scenarios={scenarios} dt={dt} dp={dp} set={(a, b) => setWeather([a, b])} />
        <ConstraintPanel crops={crops} c={constraints} set={setConstraints} />
        <CorrectionPanel key={fid} pack={pack} />
        <p className="muted">{t("card.store")}</p>
      </aside>
    </div>
  );
}
