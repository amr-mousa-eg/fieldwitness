import { useEffect, useState } from "react";
import { CropChips } from "./CropChips";
import { loadPack } from "./data";
import { routeHref } from "./route";
import { t } from "./strings";
import type { FieldPack } from "./types";

/** Placeholder field page; T9.2 (story), T9.3 (card) and T9.9 (calendar) fill it. */
export function FieldPage({ regionId, fieldId }: { regionId: string; fieldId: string }) {
  const [pack, setPack] = useState<FieldPack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPack(null);
    setError(null);
    loadPack(regionId, fieldId)
      .then(setPack)
      .catch((e: Error) => setError(e.message));
  }, [regionId, fieldId]);

  const current = pack?.options.find((o) => o.option_id === "current");
  return (
    <section className="field-page">
      <a href={routeHref(regionId)}>{t("field.back")}</a>
      {error && <p role="alert">{t("error.load", { what: "the field", message: error })}</p>}
      {!error && !pack && <p>{t("field.loading")}</p>}
      {pack && (
        <>
          <h2>{t("field.heading", { id: fieldId.slice(0, 8) })}</h2>
          <p>{t("fields.area", { area: pack.field.area_ha })}</p>
          {current && (
            <>
              <h3>{t("fields.current")}</h3>
              <CropChips sequence={current.sequence} />
            </>
          )}
          <p className="muted">{t("field.next")}</p>
        </>
      )}
    </section>
  );
}
