import { useEffect, useMemo, useState } from "react";
import { CropChips } from "./CropChips";
import { getFieldNumberMap, gradeRank } from "./fields";
import { routeHref } from "./route";
import { cropName, t } from "./strings";
import { TaggedValue } from "./tags";
import { emitTour } from "./tourEvents";
import type { Grade, RegionIndex, Tagged } from "./types";

type SortKey = "number" | "area" | "grade";
type GradeFilter = "ALL" | Grade;
const GRADES: readonly Grade[] = ["A", "B", "C", "D"];

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
  const [gradeFilter, setGradeFilter] = useState<GradeFilter>("ALL");
  const [sortBy, setSortBy] = useState<SortKey>("number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    setGradeFilter("ALL");
    setSearch("");
  }, [index.region_id]);

  const numberMap = useMemo(() => getFieldNumberMap(index.fields), [index.fields]);

  const gradeCounts = useMemo(() => {
    const counts: Record<Grade, number> = { A: 0, B: 0, C: 0, D: 0 };
    for (const f of index.fields) {
      if (f.top_grade in counts) counts[f.top_grade]++;
    }
    return counts;
  }, [index.fields]);

  const fieldsWithNum = useMemo(() => {
    return index.fields.map((f) => ({
      field: f,
      num: numberMap.get(f.field_id) ?? 1,
    }));
  }, [index.fields, numberMap]);

  const filteredAndSorted = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = fieldsWithNum.filter(({ field, num }) => {
      if (gradeFilter !== "ALL" && field.top_grade !== gradeFilter) return false;
      if (!q) return true;
      const numStr = String(num);
      const nameEn = `field ${num}`.toLowerCase();
      const nameLoc = t("field.label", { num }).toLowerCase();
      const hashStr = field.field_id.toLowerCase();
      const cropMatch = field.current_sequence.some(
        (c) => c.toLowerCase().includes(q) || cropName(c).toLowerCase().includes(q),
      );
      return nameEn.includes(q) || nameLoc.includes(q) || numStr === q || hashStr.includes(q) || cropMatch;
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
  }, [fieldsWithNum, search, gradeFilter, sortBy, sortDir]);

  // Progressive batch rendering (TBT optimization): render initial 25 items on first paint,
  // then load remaining items when idle so no main-thread tasks exceed 50 ms during startup.
  const [renderLimit, setRenderLimit] = useState(25);

  useEffect(() => {
    setRenderLimit(25);
  }, [index.region_id, search, gradeFilter, sortBy, sortDir]);

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
      <p className="muted">
        {gradeFilter === "ALL" && !search.trim()
          ? t("fields.count", { n: index.fields.length })
          : t("fields.filteredCount", { shown: filteredAndSorted.length, total: index.fields.length })}
      </p>

      <div className="grade-filter-bar" role="group" aria-label={t("fields.filterGrade")}>
        <button
          type="button"
          className={`grade-filter-btn${gradeFilter === "ALL" ? " active" : ""}`}
          aria-pressed={gradeFilter === "ALL"}
          onClick={() => setGradeFilter("ALL")}
        >
          <span>{t("fields.filterAll")}</span>
          <span className="grade-filter-count">{index.fields.length}</span>
        </button>
        {GRADES.map((g) => {
          const count = gradeCounts[g];
          const isActive = gradeFilter === g;
          return (
            <button
              key={g}
              type="button"
              className={`grade-filter-btn${isActive ? " active" : ""}`}
              aria-pressed={isActive}
              disabled={count === 0}
              title={t("fields.top", { grade: g })}
              onClick={() => setGradeFilter(isActive ? "ALL" : g)}
            >
              <span className={`grade-dot grade-dot-${g}`} aria-hidden="true" />
              <span>{g}</span>
              <span className="grade-filter-count">{count}</span>
            </button>
          );
        })}
      </div>

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
            title={sortDir === "asc" ? t("fields.sort.asc") : t("fields.sort.desc")}
            aria-label={sortDir === "asc" ? t("fields.sort.asc") : t("fields.sort.desc")}
          >
            {sortDir === "asc" ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <p className="muted field-no-matches">{t("fields.noMatches")}</p>
      ) : (
        <>
          <ul className="field-items-list">
            {visibleFields.map(({ field: f, num }) => (
              <li key={f.field_id}>
                <a
                  className="field-item"
                  href={routeHref(index.region_id, f.field_id)}
                  onClick={() => emitTour("field")}
                  aria-current={f.field_id === selectedId ? "true" : undefined}
                >
                  <span className="field-item-head">
                    <span className="field-ident">
                      <strong className="field-name">{t("field.label", { num })}</strong>
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
          {renderLimit < filteredAndSorted.length && (
            <button
              type="button"
              className="secondary-btn field-load-more"
              onClick={() => setRenderLimit(filteredAndSorted.length)}
            >
              {t("fields.showAll", { n: filteredAndSorted.length })}
            </button>
          )}
        </>
      )}
    </section>
  );
}
