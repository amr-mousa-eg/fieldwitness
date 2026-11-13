import { Suspense, lazy, useEffect, useState } from "react";
import { AdvisorConsole } from "./AdvisorConsole";
import { CalendarView } from "./CalendarView";
import { setActiveFieldPack } from "./chatbotContext";
import { FieldCard } from "./FieldCard";
import { FieldStory } from "./FieldStory";
import { PrintDossier } from "./PrintDossier";
import { ScaleFlags } from "./ScaleFlags";
import { loadPack } from "./data";
import { formatDate } from "./format";
import { fieldNumber } from "./fields";
import { compareHref, type FieldTab, TABS, routeHref } from "./route";
import { t } from "./strings";
import { TagLegend } from "./tags";
import type { FieldPack, RegionIndex } from "./types";

const Field3DView = lazy(() => import("./Field3DView"));

export function FieldPage({
  regionId,
  fieldId,
  tab,
  index,
}: {
  regionId: string;
  fieldId: string;
  tab: FieldTab;
  index?: RegionIndex | null;
}) {
  const [pack, setPack] = useState<FieldPack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.getElementById("main")?.focus();
  }, []);

  useEffect(() => {
    setPack(null);
    setError(null);
    loadPack(regionId, fieldId)
      .then(setPack)
      .catch((e: Error) => setError(e.message));
  }, [regionId, fieldId]);

  useEffect(() => {
    setActiveFieldPack(pack);
    return () => setActiveFieldPack(null);
  }, [pack]);

  return (
    <article className="field-page">
      <a href={routeHref(regionId)}>{t("field.back")}</a>
      {error && <p role="alert">{t("error.load", { what: t("error.what.field"), message: error })}</p>}
      {!error && !pack && <p>{t("field.loading")}</p>}
      {pack && (
        <>
          <header className="field-head">
            <h2>
              {index ? t("field.label", { num: fieldNumber(fieldId, index.fields) }) : t("field.heading", { id: fieldId.slice(0, 8) })}{" "}
              <small className="field-id-hash">({fieldId.slice(0, 8)})</small>
            </h2>
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
            <div className="field-head-actions">
              <a className="secondary-btn" href={compareHref(regionId, fieldId)}>
                ⇄ {t("field.compare")}
              </a>
              <button
                type="button"
                className="print-btn"
                onClick={() => window.print()}
                title={t("field.print.title")}
              >
                🖨️ {t("field.print")}
              </button>
            </div>
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
          {tab === "calendar" && <CalendarView pack={pack} regionId={regionId} />}
          {tab === "advisor" && <AdvisorConsole pack={pack} />}
          {tab === "sim3d" && (
            <Suspense fallback={<div className="sim3d-loading-state">{t("sim3d.loading")}</div>}>
              <Field3DView pack={pack} regionId={regionId} />
            </Suspense>
          )}
          <div className="field-aside">
            <ScaleFlags flags={pack.field.scale_flags} />
            <TagLegend />
          </div>
          <PrintDossier pack={pack} regionId={regionId} index={index} />
        </>
      )}
    </article>
  );
}
