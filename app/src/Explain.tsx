import { useId, useState } from "react";
import { type ExplainerId, METRIC_EXPLAINER, explainer } from "./explainers";
import { metricName, t } from "./strings";

/** A metric's display name, with its explainer when it has one. */
export function MetricLabel({ metric }: { metric: string }) {
  const id = METRIC_EXPLAINER[metric];
  return (
    <>
      {metricName(metric)}
      {id && <Explain id={id} />}
    </>
  );
}

/** A small "What is this?" button that opens a short, cited explanation in place (T9.10). */
export function Explain({ id }: { id: ExplainerId }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const e = explainer(id);
  return (
    <span className="explain">
      <button
        type="button"
        className="explain-btn"
        aria-expanded={open}
        aria-controls={panelId}
        title={t("explain.button")}
        onClick={() => setOpen(!open)}
        onKeyDown={(ev) => ev.key === "Escape" && setOpen(false)}
      >
        <span aria-hidden="true">?</span>
        <span className="sr-only">{t("explain.label", { title: e.title })}</span>
      </button>
      {open && (
        <span id={panelId} className="explain-pop" role="note">
          <span className="explain-title">{e.title}</span>
          <span className="explain-body">{e.body}</span>
          <span className="explain-source">
            {t("explain.source")}{" "}
            {e.url ? (
              <a href={e.url} target="_blank" rel="noreferrer">
                {e.source}
              </a>
            ) : (
              e.source
            )}
          </span>
        </span>
      )}
    </span>
  );
}
