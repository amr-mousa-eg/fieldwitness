import { type CSSProperties, useEffect, useId, useRef, useState } from "react";
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

const POP_WIDTH = 352; // px; must match .explain-pop max width (22rem)
const GUTTER = 8;

/**
 * A small "What is this?" button that opens a short, cited explanation (T9.10).
 * The panel is position: fixed so a scrolling table cannot clip it (T9.7); it closes on
 * Escape, on a click outside, and when the page scrolls or resizes.
 */
export function Explain({ id }: { id: ExplainerId }) {
  const [pos, setPos] = useState<CSSProperties | null>(null);
  const button = useRef<HTMLButtonElement>(null);
  const root = useRef<HTMLSpanElement>(null);
  const panelId = useId();
  const e = explainer(id);
  const open = pos !== null;

  const toggle = () => {
    if (open || !button.current) return setPos(null);
    const r = button.current.getBoundingClientRect();
    const width = Math.min(POP_WIDTH, window.innerWidth - 2 * GUTTER);
    const isRtl =
      typeof document !== "undefined" &&
      (document.documentElement.dir === "rtl" || getComputedStyle(button.current).direction === "rtl");
    const rawLeft = isRtl ? r.right - width : r.left;
    const left = Math.max(GUTTER, Math.min(rawLeft, window.innerWidth - width - GUTTER));
    const top = Math.min(r.bottom + 4, Math.max(GUTTER, window.innerHeight - 240));
    setPos({ top, left, width });
  };

  useEffect(() => {
    if (!open) return;
    const close = () => setPos(null);
    const outside = (ev: MouseEvent) => {
      if (!root.current?.contains(ev.target as Node)) close();
    };
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    document.addEventListener("mousedown", outside);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      document.removeEventListener("mousedown", outside);
    };
  }, [open]);

  return (
    <span
      className="explain"
      ref={root}
      onKeyDown={(ev) => {
        if (ev.key === "Escape" && open) {
          ev.preventDefault(); // handled here: the tour card must not also close
          setPos(null);
          button.current?.focus();
        }
      }}
    >
      <button
        ref={button}
        type="button"
        className="explain-btn"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        title={t("explain.button")}
        onClick={toggle}
      >
        <span aria-hidden="true">?</span>
        <span className="sr-only">{t("explain.label", { title: e.title })}</span>
      </button>
      {pos && (
        <span id={panelId} className="explain-pop" role="note" style={pos}>
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
          <span className="explain-glossary">
            <a
              href={`#/${(typeof window !== "undefined" && window.location.hash.replace(/^#\/?/, "").split("/")[0]) || "kansas"}/methods#glossary-${id}`}
              onClick={() => setPos(null)}
            >
              {t("explain.to_glossary")}
            </a>
          </span>
        </span>
      )}
    </span>
  );
}
