import { useEffect, useState } from "react";
import { FieldCard } from "./FieldCard";
import { FieldStory } from "./FieldStory";
import { ScaleFlags } from "./ScaleFlags";
import { loadPack } from "./data";
import { formatDate } from "./format";
import { type FieldTab, routeHref } from "./route";
import { t } from "./strings";
import { TagLegend } from "./tags";
import type { FieldPack } from "./types";

const TABS: FieldTab[] = ["story", "options"];

export function FieldPage({ regionId, fieldId, tab }: { regionId: string; fieldId: string; tab: FieldTab }) {
  const [pack, setPack] = useState<FieldPack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPack(null);
    setError(null);
    loadPack(regionId, fieldId)
      .then(setPack)
      .catch((e: Error) => setError(e.message));
  }, [regionId, fieldId]);

  return (
    <article className="field-page">
      <a href={routeHref(regionId)}>{t("field.back")}</a>
      {error && <p role="alert">{t("error.load", { what: "the field", message: error })}</p>}
      {!error && !pack && <p>{t("field.loading")}</p>}
      {pack && (
        <>
          <header className="field-head">
            <h2>{t("field.heading", { id: fieldId.slice(0, 8) })}</h2>
            <dl className="field-facts">
              <div>
                <dt>{t("field.area")}</dt>
                <dd>{t("fields.area", { area: pack.field.area_ha })}</dd>
              </div>
              <div>
                <dt>{t("field.pixels")}</dt>
                <dd>{pack.field.interior_pixels}</dd>
              </div>
              <div>
                <dt>{t("field.boundary")}</dt>
                <dd>{pack.field.boundary_source}</dd>
              </div>
              <div>
                <dt>{t("field.asof")}</dt>
                <dd>{formatDate(new Date(`${pack.data_as_of}T00:00:00Z`))}</dd>
              </div>
            </dl>
          </header>
          <nav className="tabs" aria-label={t("field.tabs")}>
            {TABS.map((x) => (
              <a key={x} href={routeHref(regionId, fieldId, x)} aria-current={x === tab ? "page" : undefined}>
                {t(`tab.${x}`)}
              </a>
            ))}
          </nav>
          {tab === "story" && <FieldStory pack={pack} regionId={regionId} />}
          {tab === "options" && <FieldCard pack={pack} regionId={regionId} />}
          <div className="field-aside">
            <ScaleFlags flags={pack.field.scale_flags} />
            <TagLegend />
          </div>
        </>
      )}
    </article>
  );
}
