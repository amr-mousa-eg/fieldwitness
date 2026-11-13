import { useEffect, useMemo, useState } from "react";
import { loadCalendar, loadPack } from "./data";
import { getFieldNumberMap } from "./fields";
import { computeBareSoilMonths } from "./fieldSummary";
import { DEFAULT_PRIORITIES, NO_CONSTRAINTS, rankOptions } from "./rank";
import { compareHref, parseCompareQuery, routeHref } from "./route";
import { cropName, optionName, t } from "./strings";
import { TagBadge } from "./tags";
import type { FieldCalendar, FieldPack, Option, RegionIndex, Tagged } from "./types";

function computeBareMonths(o: Option): number | null {
  const cd = o.metrics.cover_days?.value;
  return cd == null ? null : computeBareSoilMonths(cd);
}

function topOptionForPack(pack: FieldPack): Option | null {
  const ranked = rankOptions(pack.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
  return ranked[0]?.option ?? null;
}

function currentOptionForPack(pack: FieldPack): Option | null {
  return pack.options.find((o) => o.option_id === "current") ?? null;
}

function fmtTaggedNum(v: Tagged | undefined, digits = 0, suffix = "") {
  if (!v || v.value == null) return <span className="muted">—</span>;
  return (
    <>
      {v.value.toFixed(digits)}
      {suffix} <TagBadge tag={v.tag} source={v.source} />
    </>
  );
}

function fmtDelta(a: number | null | undefined, b: number | null | undefined, digits = 0, unit = ""): string {
  if (a == null || b == null) return "—";
  const d = b - a;
  const sign = d > 0 ? "+" : "";
  return `${sign}${d.toFixed(digits)}${unit}`;
}

function highBareMonthCount(cal: FieldCalendar | null): number | null {
  if (!cal) return null;
  return cal.bare_observed.filter((m) => !m.insufficient && m.bare_share?.value != null && m.bare_share.value >= 0.5).length;
}

export function ComparePage({ index }: { index: RegionIndex }) {
  const numberMap = useMemo(() => getFieldNumberMap(index.fields), [index.fields]);
  const sortedFields = useMemo(
    () => [...index.fields].sort((x, y) => (numberMap.get(x.field_id) ?? 0) - (numberMap.get(y.field_id) ?? 0)),
    [index.fields, numberMap],
  );

  const defaultA = sortedFields[0]?.field_id ?? "";
  const defaultB = sortedFields[1]?.field_id ?? defaultA;

  const initialQuery = useMemo(
    () => (typeof window !== "undefined" ? parseCompareQuery(window.location.hash) : { a: null, b: null }),
    [],
  );

  const [idA, setIdA] = useState<string>(initialQuery.a && numberMap.has(initialQuery.a) ? initialQuery.a : defaultA);
  const [idB, setIdB] = useState<string>(initialQuery.b && numberMap.has(initialQuery.b) ? initialQuery.b : defaultB);

  const [packA, setPackA] = useState<FieldPack | null>(null);
  const [packB, setPackB] = useState<FieldPack | null>(null);
  const [calA, setCalA] = useState<FieldCalendar | null>(null);
  const [calB, setCalB] = useState<FieldCalendar | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const onHash = () => {
      const q = parseCompareQuery(window.location.hash);
      if (q.a && numberMap.has(q.a)) setIdA(q.a);
      if (q.b && numberMap.has(q.b)) setIdB(q.b);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [numberMap]);

  useEffect(() => {
    if (!idA || !idB) return;
    let alive = true;
    setLoading(true);
    Promise.all([
      loadPack(index.region_id, idA),
      loadPack(index.region_id, idB),
      loadCalendar(index.region_id, idA).catch(() => null),
      loadCalendar(index.region_id, idB).catch(() => null),
    ])
      .then(([pA, pB, cA, cB]) => {
        if (!alive) return;
        setPackA(pA);
        setPackB(pB);
        setCalA(cA);
        setCalB(cB);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [index.region_id, idA, idB]);

  const updateSelection = (nextA: string, nextB: string) => {
    setIdA(nextA);
    setIdB(nextB);
    if (typeof window !== "undefined") {
      window.location.hash = compareHref(index.region_id, nextA, nextB);
    }
  };

  const numA = numberMap.get(idA) ?? 1;
  const numB = numberMap.get(idB) ?? 2;
  const labelA = `Field ${numA} (${idA.slice(0, 8)})`;
  const labelB = `Field ${numB} (${idB.slice(0, 8)})`;

  const curA = packA ? currentOptionForPack(packA) : null;
  const curB = packB ? currentOptionForPack(packB) : null;
  const topA = packA ? topOptionForPack(packA) : null;
  const topB = packB ? topOptionForPack(packB) : null;

  const bareHighA = highBareMonthCount(calA);
  const bareHighB = highBareMonthCount(calB);

  return (
    <article className="compare-page" aria-labelledby="compare-heading">
      <header className="compare-head">
        <h2 id="compare-heading">{t("compare.heading")}</h2>
        <p className="muted">{t("compare.intro")}</p>
      </header>

      <section className="card-box compare-controls">
        <label className="compare-select-wrap">
          <span>{t("compare.fieldA")}</span>
          <select value={idA} onChange={(e) => updateSelection(e.target.value, idB)}>
            {sortedFields.map((f) => {
              const n = numberMap.get(f.field_id) ?? 0;
              return (
                <option key={f.field_id} value={f.field_id}>
                  Field {n} · {f.area_ha.toFixed(1)} ha · {f.top_grade} ({f.field_id.slice(0, 8)})
                </option>
              );
            })}
          </select>
        </label>

        <button
          type="button"
          className="secondary-btn"
          onClick={() => updateSelection(idB, idA)}
        >
          ⇄ {t("compare.swap")}
        </button>

        <label className="compare-select-wrap">
          <span>{t("compare.fieldB")}</span>
          <select value={idB} onChange={(e) => updateSelection(idA, e.target.value)}>
            {sortedFields.map((f) => {
              const n = numberMap.get(f.field_id) ?? 0;
              return (
                <option key={f.field_id} value={f.field_id}>
                  Field {n} · {f.area_ha.toFixed(1)} ha · {f.top_grade} ({f.field_id.slice(0, 8)})
                </option>
              );
            })}
          </select>
        </label>
      </section>

      {idA === idB && (
        <p className="coverage-alert-box" role="status">
          {t("compare.sameWarn")}
        </p>
      )}

      {loading && (!packA || !packB) && <p className="muted">{t("compare.loading")}</p>}

      {packA && packB && (
        <div className="compare-tables">
          <section className="card-box">
            <h3>{t("compare.section.parcel")}</h3>
            <div className="table-scroll">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>{t("compare.metric")}</th>
                    <th>
                      <a href={routeHref(index.region_id, idA)}>{labelA}</a>
                    </th>
                    <th>
                      <a href={routeHref(index.region_id, idB)}>{labelB}</a>
                    </th>
                    <th>{t("compare.delta")}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{t("compare.area")}</td>
                    <td>{t("fields.area", { area: packA.field.area_ha.toFixed(1) })}</td>
                    <td>{t("fields.area", { area: packB.field.area_ha.toFixed(1) })}</td>
                    <td>{fmtDelta(packA.field.area_ha, packB.field.area_ha, 1, " ha")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.pixels")}</td>
                    <td>{packA.field.interior_pixels} [O]</td>
                    <td>{packB.field.interior_pixels} [O]</td>
                    <td>{fmtDelta(packA.field.interior_pixels, packB.field.interior_pixels, 0)}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.credibility")}</td>
                    <td>{fmtTaggedNum(packA.credibility, 2)}</td>
                    <td>{fmtTaggedNum(packB.credibility, 2)}</td>
                    <td>{fmtDelta(packA.credibility.value, packB.credibility.value, 2)}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.asof")}</td>
                    <td>{packA.data_as_of}</td>
                    <td>{packB.data_as_of}</td>
                    <td>—</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="card-box">
            <h3>{t("compare.section.rotations")}</h3>
            <div className="table-scroll">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>{t("compare.metric")}</th>
                    <th>{labelA}</th>
                    <th>{labelB}</th>
                    <th>{t("compare.delta")}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{t("compare.currentSeq")}</td>
                    <td>{curA ? optionName({ option_id: curA.sequence.join("|") }) : "—"}</td>
                    <td>{curB ? optionName({ option_id: curB.sequence.join("|") }) : "—"}</td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>{t("compare.currentGrade")}</td>
                    <td><span className={`grade grade-${curA?.grade ?? "D"}`}>{curA?.grade ?? "—"}</span></td>
                    <td><span className={`grade grade-${curB?.grade ?? "D"}`}>{curB?.grade ?? "—"}</span></td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>{t("compare.currentWater")}</td>
                    <td>{fmtTaggedNum(curA?.metrics.water_use_mm, 0, " mm")}</td>
                    <td>{fmtTaggedNum(curB?.metrics.water_use_mm, 0, " mm")}</td>
                    <td>{fmtDelta(curA?.metrics.water_use_mm?.value, curB?.metrics.water_use_mm?.value, 0, " mm")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.currentBadWater")}</td>
                    <td>{fmtTaggedNum(curA?.metrics.bad_year_water_mm, 0, " mm")}</td>
                    <td>{fmtTaggedNum(curB?.metrics.bad_year_water_mm, 0, " mm")}</td>
                    <td>{fmtDelta(curA?.metrics.bad_year_water_mm?.value, curB?.metrics.bad_year_water_mm?.value, 0, " mm")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.currentRyi")}</td>
                    <td>{fmtTaggedNum(curA?.metrics.ryi, 2)}</td>
                    <td>{fmtTaggedNum(curB?.metrics.ryi, 2)}</td>
                    <td>{fmtDelta(curA?.metrics.ryi?.value, curB?.metrics.ryi?.value, 2)}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topSeq")}</td>
                    <td><strong>{topA ? optionName(topA) : "—"}</strong></td>
                    <td><strong>{topB ? optionName(topB) : "—"}</strong></td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topGrade")}</td>
                    <td><span className={`grade grade-${topA?.grade ?? "D"}`}>{topA?.grade ?? "—"}</span></td>
                    <td><span className={`grade grade-${topB?.grade ?? "D"}`}>{topB?.grade ?? "—"}</span></td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topWater")}</td>
                    <td>{fmtTaggedNum(topA?.metrics.water_use_mm, 0, " mm")}</td>
                    <td>{fmtTaggedNum(topB?.metrics.water_use_mm, 0, " mm")}</td>
                    <td>{fmtDelta(topA?.metrics.water_use_mm?.value, topB?.metrics.water_use_mm?.value, 0, " mm")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topBadWater")}</td>
                    <td>{fmtTaggedNum(topA?.metrics.bad_year_water_mm, 0, " mm")}</td>
                    <td>{fmtTaggedNum(topB?.metrics.bad_year_water_mm, 0, " mm")}</td>
                    <td>{fmtDelta(topA?.metrics.bad_year_water_mm?.value, topB?.metrics.bad_year_water_mm?.value, 0, " mm")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topRyi")}</td>
                    <td>{fmtTaggedNum(topA?.metrics.ryi, 2)}</td>
                    <td>{fmtTaggedNum(topB?.metrics.ryi, 2)}</td>
                    <td>{fmtDelta(topA?.metrics.ryi?.value, topB?.metrics.ryi?.value, 2)}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.topBareMonths")}</td>
                    <td>
                      {topA ? `${computeBareMonths(topA)?.toFixed(1) ?? "—"} mo [D]` : "—"}
                    </td>
                    <td>
                      {topB ? `${computeBareMonths(topB)?.toFixed(1) ?? "—"} mo [D]` : "—"}
                    </td>
                    <td>
                      {topA && topB
                        ? fmtDelta(computeBareMonths(topA), computeBareMonths(topB), 1, " mo")
                        : "—"}
                    </td>
                  </tr>
                  <tr>
                    <td>{t("compare.legumeShare")}</td>
                    <td>{fmtTaggedNum(topA?.metrics.legume_share, 2)}</td>
                    <td>{fmtTaggedNum(topB?.metrics.legume_share, 2)}</td>
                    <td>{fmtDelta(topA?.metrics.legume_share?.value, topB?.metrics.legume_share?.value, 2)}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.familyBreaks")}</td>
                    <td>{fmtTaggedNum(topA?.metrics.family_breaks, 0)}</td>
                    <td>{fmtTaggedNum(topB?.metrics.family_breaks, 0)}</td>
                    <td>{fmtDelta(topA?.metrics.family_breaks?.value, topB?.metrics.family_breaks?.value, 0)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="card-box">
            <h3>{t("compare.section.calendar")}</h3>
            <div className="table-scroll">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>{t("compare.metric")}</th>
                    <th>{labelA}</th>
                    <th>{labelB}</th>
                    <th>{t("compare.delta")}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{t("compare.obsBareHighMonths")}</td>
                    <td>{bareHighA != null ? `${bareHighA} / 12 [O]` : "—"}</td>
                    <td>{bareHighB != null ? `${bareHighB} / 12 [O]` : "—"}</td>
                    <td>{fmtDelta(bareHighA, bareHighB, 0, " mo")}</td>
                  </tr>
                  <tr>
                    <td>{t("compare.recentHistory")}</td>
                    <td>
                      {packA.story
                        .slice(-5)
                        .map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : t("crop.fallow")}`)
                        .join(" → ")}
                    </td>
                    <td>
                      {packB.story
                        .slice(-5)
                        .map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : t("crop.fallow")}`)
                        .join(" → ")}
                    </td>
                    <td>—</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="compare-actions">
              <a className="action-btn" href={routeHref(index.region_id, idA)}>
                {t("compare.openField", { field: `Field ${numA}` })}
              </a>
              <a className="action-btn" href={routeHref(index.region_id, idB)}>
                {t("compare.openField", { field: `Field ${numB}` })}
              </a>
            </div>
          </section>
        </div>
      )}
    </article>
  );
}
