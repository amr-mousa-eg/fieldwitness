import { useEffect } from "react";
import { DATASETS } from "./datasets";
import { IS_DEMO_DATA } from "./data";
import { pageHref, useRoute } from "./route";
import { t } from "./strings";
import { TagLegend } from "./tags";
import { HOME_LINKS } from "./teamConfig";

function useResourcesAnchor(): void {
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

export function ResourcesPage() {
  useResourcesAnchor();
  const regionId = useRoute().regionId ?? "ks_t14slh";

  return (
    <article className="methods resources-page" aria-labelledby="resources-h">
      <div className="ref-page-head">
        <div>
          <h2 id="resources-h">{t("resources.heading")}</h2>
          <p className="muted">{t("resources.subtitle")}</p>
        </div>
        <div className="ref-page-links">
          <a className="secondary-btn" href={pageHref(regionId, "methods")}>
            {t("nav.methods")}
          </a>
          <a className="secondary-btn" href={pageHref(regionId, "terms")}>
            {t("nav.terms")}
          </a>
        </div>
      </div>

      {IS_DEMO_DATA && <p className="notice">{t("methods.demo")}</p>}

      <section aria-labelledby="m-data" id="m-data">
        <h3 id="m-data-h">{t("methods.data")}</h3>
        <div className="table-wrap">
          <table className="scores datasets">
            <thead>
              <tr>
                <th scope="col">{t("methods.ds.name")}</th>
                <th scope="col">{t("methods.ds.use")}</th>
                <th scope="col">{t("methods.ds.licence")}</th>
              </tr>
            </thead>
            <tbody>
              {DATASETS.map((d) => (
                <tr key={d}>
                  <th scope="row">{t(`methods.ds.${d}.name`)}</th>
                  <td>{t(`methods.ds.${d}.use`)}</td>
                  <td>{t(`methods.ds.${d}.licence`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">{t("methods.data.note")}</p>
      </section>

      <section aria-labelledby="m-pubs" id="m-pubs-section">
        <h3 id="m-pubs">{t("resources.pubs.heading")}</h3>
        <p>{t("resources.pubs.text")}</p>
        <div className="home-btn-group" style={{ marginTop: "0.75rem" }}>
          <a
            className="home-btn home-btn--primary"
            href={HOME_LINKS.paperPdfUrl}
            target="_blank"
            rel="noreferrer"
          >
            {t("home.paper.readPdf")}
          </a>
          <a className="home-btn home-btn--secondary" href={HOME_LINKS.paperDocxUrl} download>
            {t("home.paper.downloadDocx")}
          </a>
          <a className="home-btn home-btn--secondary" href={HOME_LINKS.presentationPptxUrl} download>
            {t("home.presentation.downloadPptx")} ↓
          </a>
        </div>
      </section>

      <TagLegend />
    </article>
  );
}
