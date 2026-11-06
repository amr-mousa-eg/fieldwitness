import { useEffect, useRef, useState } from "react";
import { DemoBanner } from "./DemoBanner";
import { FieldPage } from "./FieldPage";
import { MapPage } from "./MapPage";
import { MethodsPage } from "./MethodsPage";
import { cacheRegionForOffline, loadIndex, loadRegions } from "./data";
import { PAGES, pageHref, useRoute } from "./route";
import { Scoreboard } from "./Scoreboard";
import { t } from "./strings";
import type { RegionIndex, RegionList } from "./types";

/** Every page renders exactly one <main id="main" tabIndex={-1}>. */
function focusMain(): void {
  document.getElementById("main")?.focus();
}

export function App() {
  const route = useRoute();
  const [regions, setRegions] = useState<RegionList | null>(null);
  const [index, setIndex] = useState<RegionIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const regionId = route.regionId ?? regions?.regions[0]?.region_id ?? null;

  useEffect(() => {
    loadRegions()
      .then(setRegions)
      .catch((e: Error) => setError(t("error.load", { what: "the region list", message: e.message })));
  }, []);

  useEffect(() => {
    if (!regionId) return;
    setIndex(null);
    loadIndex(regionId)
      .then((idx) => {
        setIndex(idx);
        cacheRegionForOffline(idx);
      })
      .catch((e: Error) => setError(t("error.load", { what: "the region", message: e.message })));
  }, [regionId]);

  // T9.7: after moving to another page or field, put keyboard focus at the start of the new
  // content (the clicked link may no longer exist). Tab switches inside a field keep focus.
  const pageKey = `${regionId}/${route.page}/${route.fieldId}`;
  const lastPage = useRef<string | null>(null);
  useEffect(() => {
    // compare keys, not a "first run" flag: StrictMode runs effects twice in development;
    // wait for the region (the default region is only known once regions.json has loaded)
    if (!regionId) return;
    if (lastPage.current !== null && lastPage.current !== pageKey) focusMain();
    lastPage.current = pageKey;
  }, [pageKey]);

  return (
    <div className="app">
      <a
        className="skip-link"
        href="#main"
        onClick={(e) => {
          e.preventDefault(); // the hash is the router; do not navigate
          focusMain();
        }}
      >
        {t("skip.main")}
      </a>
      <DemoBanner />
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <p className="tagline">{t("app.tagline")}</p>
        {regions && regionId && (
          <label className="region-switch">
            {t("region.label")}
            <select
              value={regionId}
              onChange={(e) => (window.location.hash = pageHref(e.target.value, route.page))}
            >
              {regions.regions.map((r) => (
                <option key={r.region_id} value={r.region_id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {regionId && (
          <nav className="app-nav" aria-label={t("nav.label")}>
            {PAGES.map((p) => (
              <a
                key={p}
                href={pageHref(regionId, p)}
                aria-current={!route.fieldId && route.page === p ? "page" : undefined}
              >
                {t(`nav.${p}`)}
              </a>
            ))}
          </nav>
        )}
      </header>
      {index && route.fieldId ? (
        <main id="main" tabIndex={-1} className="app-field">
          <FieldPage regionId={index.region_id} fieldId={route.fieldId} tab={route.tab} />
        </main>
      ) : index && route.page === "scoreboard" ? (
        <main id="main" tabIndex={-1} className="app-field">
          <Scoreboard index={index} />
        </main>
      ) : route.page === "methods" ? (
        <main id="main" tabIndex={-1} className="app-field">
          <MethodsPage />
        </main>
      ) : index ? (
        <MapPage index={index} />
      ) : (
        <main id="main" tabIndex={-1} className="app-main">
          <aside className="rail">
            {error ? <p role="alert">{error}</p> : <p>{t("region.loading")}</p>}
          </aside>
        </main>
      )}
      <footer className="app-footer">{t("fixed.judgment")}</footer>
    </div>
  );
}
