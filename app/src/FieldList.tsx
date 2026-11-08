import { useEffect, useMemo, useState } from "react";
import { CropChips } from "./CropChips";
import { getFieldNumberMap, gradeRank } from "./fields";
import { routeHref } from "./route";
import { t } from "./strings";
import { TaggedValue } from "./tags";
import type { RegionIndex, Tagged } from "./types";

type SortKey = "number" | "area" | "grade";

/** Keyboard-reachable list of the same fields the map shows. */
export function FieldList({
  index,
  selectedId,
  values,
  valueLabel = "",
}: {
  index: RegionIndex;
  selectedId: string | null;
  /** Map colouring values (T9.11a), printed per field so colour never carries meaning alone. */
  values?: Record<string, Tagged>;
  valueLabel?: string;
}) {
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const numberMap = useMemo(() => getFieldNumberMap(index.fields), [index.fields]);

  const fieldsWithNum = useMemo(() => {
    return index.fields.map((f) => ({
      field: f,
      num: numberMap.get(f.field_id) ?? 1,
    }));
  }, [index.fields, numberMap]);

  const filteredAndSorted = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = fieldsWithNum.filter(({ field, num }) => {
      if (!q) return true;
      const numStr = String(num);
      const nameStr = `field ${num}`.toLowerCase();
      const hashStr = field.field_id.toLowerCase();
      return nameStr.includes(q) || numStr === q || hashStr.includes(q);
    });

    return filtered.sort((a, b) => {
      let cmp = 0;
      if (sortBy === "number") {
        cmp = a.num - b.num;
      } else if (sortBy === "area") {
        cmp = a.field.area_ha - b.field.area_ha;
      } else if (sortBy === "grade") {
        cmp = gradeRank(a.field.top_grade) - gradeRank(b.field.top_grade);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [fieldsWithNum, search, sortBy, sortDir]);

  // Progressive batch rendering (TBT optimization): render initial 25 items on first paint,
  // then load remaining items when idle so no main-thread tasks exceed 50 ms during startup.
  const [renderLimit, setRenderLimit] = useState(25);

  useEffect(() => {
    setRenderLimit(25);
  }, [search, sortBy, sortDir]);

  useEffect(() => {
    if (renderLimit >= filteredAndSorted.length) return;
    const schedule = typeof window !== "undefined" && "requestIdleCallback" in window
      ? (cb: () => void) => window.requestIdleCallback(cb, { timeout: 1200 })
      : (cb: () => void) => setTimeout(cb, 400);
    const cancel = typeof window !== "undefined" && "cancelIdleCallback" in window
      ? (id: number) => window.cancelIdleCallback(id)
      : (id: number) => clearTimeout(id);

    const timerId = schedule(() => {
      setRenderLimit((prev) => Math.min(prev + 50, filteredAndSorted.length));
    });
    return () => cancel(timerId);
  }, [renderLimit, filteredAndSorted.length]);

  const visibleFields = useMemo(() => {
    return filteredAndSorted.slice(0, renderLimit);
  }, [filteredAndSorted, renderLimit]);

  return (
    <section className="field-list" aria-labelledby="fields-heading">
      <h2 id="fields-heading">{t("fields.heading")}</h2>
      <p className="muted">{t("fields.count", { n: index.fields.length })}</p>

      <div className="field-list-controls">
        <div className="field-search-wrap">
          <label htmlFor="field-search" className="sr-only">
            {t("fields.search")}
          </label>
          <input
            id="field-search"
            type="search"
            className="field-search-input"
            placeholder={t("fields.search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="field-sort-wrap">
          <label htmlFor="field-sort" className="field-sort-label">
            {t("fields.sortBy")}
          </label>
          <select
            id="field-sort"
            className="field-sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortKey)}
          >
            <option value="number">{t("fields.sort.number")}</option>
            <option value="area">{t("fields.sort.area")}</option>
            <option value="grade">{t("fields.sort.grade")}</option>
          </select>
          <button
            type="button"
            className="field-sort-dir"
            onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
            title={sortDir === "asc" ? "Ascending" : "Descending"}
            aria-label={sortDir === "asc" ? "Ascending" : "Descending"}
          >
            {sortDir === "asc" ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <p className="muted field-no-matches">{t("fields.noMatches")}</p>
      ) : (
        <ul className="field-items-list">
          {visibleFields.map(({ field: f, num }) => (
            <li key={f.field_id}>
              <a
                className="field-item"
                href={routeHref(index.region_id, f.field_id)}
                aria-current={f.field_id === selectedId ? "true" : undefined}
              >
                <span className="field-item-head">
                  <span className="field-ident">
                    <strong className="field-name">Field {num}</strong>
                    <span className="field-id-hash">{f.field_id.slice(0, 8)}</span>
                  </span>
                  <span className="field-area">{t("fields.area", { area: f.area_ha })}</span>
                  <span
                    className={`grade grade-${f.top_grade}`}
                    title={t("fields.top", { grade: f.top_grade })}
                  >
                    {f.top_grade}
                  </span>
                </span>
                <span className="sr-only">{t("fields.current")}: </span>
                <CropChips sequence={f.current_sequence} />
                {values && (
                  <span className="field-value">
                    {valueLabel}:{" "}
                    {values[f.field_id] ? <TaggedValue v={values[f.field_id]} /> : t("value.none")}
                  </span>
                )}
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
