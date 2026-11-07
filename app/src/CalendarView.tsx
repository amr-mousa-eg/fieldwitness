import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import { CropChips } from "./CropChips";
import { HAZARDS, MONTHS, monthValue, shadeLevel, vulnerabilityFor } from "./calendar";
import { loadCalendar, loadLayers } from "./data";
import { formatTagged } from "./format";
import { cropName, optionName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import { Explain } from "./Explain";
import type { ExplainerId } from "./explainers";
import type { FieldCalendar, FieldPack, Hazard, RegionLayers, RegionalLayer, Tag } from "./types";

const MONTH_NAMES = MONTHS.map((m) => new Date(Date.UTC(2001, m - 1, 1)).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" }));

function Head() {
  return (
    <thead>
      <tr>
        <th scope="col">
          <span className="sr-only">{t("cal.row")}</span>
        </th>
        {MONTH_NAMES.map((m) => (
          <th key={m} scope="col">
            {m}
          </th>
        ))}
      </tr>
    </thead>
  );
}

function ShareCell({ share, kind }: { share: number | null; kind: "bare" | "risk" }) {
  const lvl = shadeLevel(share);
  if (lvl === null) return <td className="cal-cell muted">{t("value.none")}</td>;
  return <td className={`cal-cell ${kind}-${lvl}`}>{Math.round(share! * 100)}%</td>;
}

const HAZARD_EXPLAINER: Partial<Record<Hazard, ExplainerId>> = { frost: "frost", water_stress: "water_balance" };

function RowHead({ label, tag, source, explain }: { label: string; tag: Tag; source: string; explain?: ExplainerId }) {
  return (
    <th scope="row">
      {label} <TagBadge tag={tag} source={source} />
      {explain && <Explain id={explain} />}
    </th>
  );
}

function BareCalendar({ cal, optionId, label }: { cal: FieldCalendar; optionId: string; label: string }) {
  const sim = cal.bare_by_option[optionId];
  const obsTag = cal.bare_observed.find((b) => b.bare_share)?.bare_share;
  const [first, last] = cal.bare_observed_years;
  return (
    <section aria-labelledby="bare-h">
      <h3 id="bare-h">{t("cal.bare")}</h3>
      <p className="muted">{t("cal.bare.note")}</p>
      <div className="table-wrap">
        <table className="cal">
          <Head />
          <tbody>
            {obsTag && (
              <tr>
                <RowHead label={t("cal.bare.observed", { first, last })} tag={obsTag.tag} source={obsTag.source} />
                {MONTHS.map((m) => {
                  const b = cal.bare_observed.find((x) => x.month === m);
                  if (!b || b.insufficient || !b.bare_share) {
                    return (
                      <td key={m} className="cal-cell insufficient" title={t("story.clear", { n: b?.clear_obs ?? 0 })}>
                        {t("cal.insufficient")}
                      </td>
                    );
                  }
                  return <ShareCell key={m} share={b.bare_share.value} kind="bare" />;
                })}
              </tr>
            )}
            {sim && (
              <tr>
                <RowHead label={t("cal.bare.simulated", { option: label })} tag={sim.tag} source={sim.source} />
                {MONTHS.map((m) => (
                  <ShareCell key={m} share={monthValue(sim.x, sim.values, m)} kind="bare" />
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {!sim && <p className="muted">{t("cal.bare.noSim")}</p>}
    </section>
  );
}

function VulnerabilityCalendar({ cal, sequence }: { cal: FieldCalendar; sequence: string[] }) {
  const { found, missing } = vulnerabilityFor(cal, { sequence });
  return (
    <section aria-labelledby="vuln-h">
      <h3 id="vuln-h">{t("cal.vuln")}</h3>
      <p className="muted">{t("cal.vuln.note")}</p>
      {found.map((v) => (
        <div key={v.crop} className="cal-crop">
          <h4>
            {cropName(v.crop)} <span className="muted">{t("cal.vuln.years", { first: v.years[0], last: v.years[1] })}</span>
          </h4>
          <div className="table-wrap">
            <table className="cal">
              <Head />
              <tbody>
                {HAZARDS.map((hz) => {
                  const s = v.shares[hz];
                  if (!s) return null;
                  return (
                    <tr key={hz}>
                      <RowHead label={t(`hazard.${hz}`)} tag={s.tag} source={s.source} explain={HAZARD_EXPLAINER[hz]} />
                      {MONTHS.map((m) => (
                        <ShareCell key={m} share={monthValue(s.x, s.values, m)} kind="risk" />
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <details className="thresholds">
            <summary>{t("cal.thresholds")}</summary>
            <ul>
              {HAZARDS.filter((hz) => v.thresholds[hz]).map((hz) => (
                <li key={hz}>
                  {t(`hazard.${hz}`)}: <TaggedValue v={v.thresholds[hz]} />
                  {v.threshold_notes[hz] && <span className="muted"> — {v.threshold_notes[hz]}</span>}
                </li>
              ))}
            </ul>
          </details>
        </div>
      ))}
      {missing.length > 0 && (
        <p className="muted">{t("cal.vuln.missing", { crops: missing.map(cropName).join(", ") })}</p>
      )}
    </section>
  );
}

function Sparkline({ layer }: { layer: RegionalLayer }) {
  const data = (layer.region_mean.x as number[]).map((x, i) => ({ x, y: layer.region_mean.values[i] }));
  return (
    <div className="spark" aria-hidden="true">
      <ResponsiveContainer width="100%" height={48}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          <YAxis hide domain={["auto", "auto"]} />
          <Line dataKey="y" stroke="#56646b" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Regional context strip (T9.9): every layer is coarse context, so each shows its scale flag. */
export function ContextStrip({ layers }: { layers: RegionLayers }) {
  return (
    <section className="context-strip" aria-labelledby="ctx-h">
      <h3 id="ctx-h">{t("ctx.heading")}</h3>
      <ul>
        {layers.layers.map((l) => {
          const m = l.region_mean;
          const years = m.x as number[];
          const lastI = m.values.length - 1;
          const last = m.values[lastI];
          return (
            <li key={l.layer_id} className="ctx-item">
              <h4>
                {t(`layer.${l.layer_id}`)}
                {l.layer_id === "smap_anomaly" && <Explain id="soil_moisture_anomaly" />}
              </h4>
              <Sparkline layer={l} />
              <p>
                {t("ctx.latest", { year: years[lastI] ?? "" })}{" "}
                <TaggedValue v={{ value: last ?? null, unit: m.unit, tag: m.tag, source: m.source }} />
              </p>
              <p>
                {t("ctx.trend")} <TaggedValue v={l.trend} />
              </p>
              <p className="muted">
                {t("ctx.range", { first: years[0] ?? "", last: years[lastI] ?? "" })}
                {l.trend.lo90 != null && l.trend.hi90 != null && (
                  <>
                    {" "}
                    {t("value.range90", {
                      lo: formatTagged({ ...l.trend, value: l.trend.lo90 }),
                      hi: formatTagged({ ...l.trend, value: l.trend.hi90 }),
                    })}
                  </>
                )}
              </p>
              <p className={l.scale_flag ? "flag flag-coarse" : "flag flag-fine"}>
                <span aria-hidden="true">{l.scale_flag ? "◌" : "●"}</span>{" "}
                {t(l.scale_flag ? "ctx.coarse" : "ctx.fine", { km: l.resolution_km })}
              </p>
              <p className="muted ctx-source">{l.resolution_source}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function CalendarView({ pack, regionId }: { pack: FieldPack; regionId: string }) {
  const fid = pack.field.field_id;
  const [cal, setCal] = useState<FieldCalendar | null>(null);
  const [layers, setLayers] = useState<RegionLayers | null>(null);
  const [error, setError] = useState(false);
  const [optionId, setOptionId] = useState("current");
  const options = [...pack.options].sort((a, b) =>
    a.option_id === "current" ? -1 : b.option_id === "current" ? 1 : a.option_id.localeCompare(b.option_id),
  );
  const option = options.find((o) => o.option_id === optionId) ?? options[0];

  useEffect(() => {
    setCal(null);
    setError(false);
    loadCalendar(regionId, fid)
      .then(setCal)
      .catch(() => setError(true));
  }, [regionId, fid]);
  useEffect(() => {
    setLayers(null);
    loadLayers(regionId)
      .then(setLayers)
      .catch(() => setLayers(null));
  }, [regionId]);

  return (
    <div className="calendar-view">
      <div className="chart-controls">
        <label>
          {t("cal.show")}{" "}
          <select value={option.option_id} onChange={(e) => setOptionId(e.target.value)}>
            {options.map((o) => (
              <option key={o.option_id} value={o.option_id}>
                {optionName(o)}
              </option>
            ))}
          </select>
        </label>
        <CropChips sequence={option.sequence} />
      </div>
      {error && <p className="muted">{t("cal.missing")}</p>}
      {cal && (
        <>
          <BareCalendar cal={cal} optionId={option.option_id} label={optionName(option)} />
          <VulnerabilityCalendar cal={cal} sequence={option.sequence} />
        </>
      )}
      {layers && <ContextStrip layers={layers} />}
    </div>
  );
}
