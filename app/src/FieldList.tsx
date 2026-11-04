import { CropChips } from "./CropChips";
import { routeHref } from "./route";
import { t } from "./strings";
import type { RegionIndex } from "./types";

/** Keyboard-reachable list of the same fields the map shows. */
export function FieldList({ index, selectedId }: { index: RegionIndex; selectedId: string | null }) {
  return (
    <section className="field-list" aria-labelledby="fields-heading">
      <h2 id="fields-heading">{t("fields.heading")}</h2>
      <p className="muted">{t("fields.count", { n: index.fields.length })}</p>
      <ul>
        {index.fields.map((f) => (
          <li key={f.field_id}>
            <a
              className="field-item"
              href={routeHref(index.region_id, f.field_id)}
              aria-current={f.field_id === selectedId ? "true" : undefined}
            >
              <span className="field-item-head">
                <span className="field-id">{f.field_id.slice(0, 8)}</span>
                <span>{t("fields.area", { area: f.area_ha })}</span>
                <span className={`grade grade-${f.top_grade}`} title={t("fields.top", { grade: f.top_grade })}>
                  {f.top_grade}
                </span>
              </span>
              <span className="sr-only">{t("fields.current")}: </span>
              <CropChips sequence={f.current_sequence} />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
