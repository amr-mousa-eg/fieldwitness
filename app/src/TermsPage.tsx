import { useEffect, useMemo, useState } from "react";
import { EXPLAINERS, explainer } from "./explainers";
import { pageHref, useRoute } from "./route";
import { t } from "./strings";
import { TagLegend } from "./tags";

function useTermsAnchor(): void {
  useEffect(() => {
    let timer = 0;
    const jump = () => {
      const hash = window.location.hash;
      const at = hash.indexOf("#", 1);
      if (at < 0) return;
      const el = document.getElementById(decodeURIComponent(hash.slice(at + 1)));
      if (!el) return;
      timer = window.setTimeout(() => {
        if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
        el.focus({ preventScroll: true });
        el.scrollIntoView({ block: "start" });
      }, 0);
    };
    jump();
    window.addEventListener("hashchange", jump);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("hashchange", jump);
    };
  }, []);
}

export function TermsPage() {
  useTermsAnchor();
  const regionId = useRoute().regionId ?? "ks_t14slh";
  const [query, setQuery] = useState("");

  const entries = useMemo(() => {
    const q = query.trim().toLowerCase();
    return EXPLAINERS.map((id) => ({ id, ...explainer(id) })).filter((item) => {
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.body.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q) ||
        item.id.toLowerCase().includes(q)
      );
    });
  }, [query]);

  return (
    <article className="methods terms-page" aria-labelledby="terms-h">
      <div className="ref-page-head">
        <div>
          <h2 id="terms-h">{t("terms.heading")}</h2>
          <p className="muted">{t("terms.subtitle")}</p>
        </div>
        <div className="ref-page-links">
          <a className="secondary-btn" href={pageHref(regionId, "methods")}>
            {t("nav.methods")}
          </a>
          <a className="secondary-btn" href={pageHref(regionId, "resources")}>
            {t("nav.resources")}
          </a>
        </div>
      </div>

      <TagLegend />

      <section aria-labelledby="m-terms" id="glossary">
        <div className="terms-filter-bar">
          <h3 id="m-terms">{t("methods.terms")}</h3>
          <label className="terms-search-label">
            <span className="sr-only">{t("terms.search.label")}</span>
            <input
              type="search"
              className="terms-search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("terms.search.placeholder")}
            />
          </label>
        </div>
        <dl className="glossary glossary-grid">
          {entries.map((e) => (
            <div key={e.id} id={`glossary-${e.id}`} className="glossary-entry glossary-card">
              <dt>{e.title}</dt>
              <dd>
                <p>{e.body}</p>
                <span className="muted">
                  {t("explain.source")}{" "}
                  {e.url ? (
                    <a href={e.url} target="_blank" rel="noreferrer">
                      {e.source}
                    </a>
                  ) : (
                    e.source
                  )}
                </span>
              </dd>
            </div>
          ))}
        </dl>
        {entries.length === 0 && <p className="muted">{t("terms.search.empty")}</p>}
      </section>
    </article>
  );
}
