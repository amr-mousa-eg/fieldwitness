import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { DemoBanner } from "./DemoBanner";
import { MapPage } from "./MapPage";
import { loadIndex, loadRegions } from "./data";
import { PAGES, pageHref, useRoute } from "./route";
import { ThemeToggle } from "./ThemeToggle";
import { t } from "./strings";
import type { RegionIndex, RegionList } from "./types";

const FieldPage = lazy(() => import("./FieldPage").then((m) => ({ default: m.FieldPage })));
const Scoreboard = lazy(() => import("./Scoreboard").then((m) => ({ default: m.Scoreboard })));
const MethodsPage = lazy(() => import("./MethodsPage").then((m) => ({ default: m.MethodsPage })));

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

  const isMap = !route.fieldId && (route.page === "map" || !route.page);

  return (
    <div className={`app ${isMap ? "app--map" : "app--scroll"}`}>
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
        <div className="header-actions">
          {regions && regionId ? (
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
          ) : (
            <div className="region-switch-placeholder" aria-hidden="true" />
          )}
          <ThemeToggle />
        </div>
        <nav className="app-nav" aria-label={t("nav.label")}>
          {PAGES.map((p) => (
            <a
              key={p}
              href={pageHref(regionId ?? "kansas", p)}
              aria-current={!route.fieldId && route.page === p ? "page" : undefined}
            >
              {t(`nav.${p}`)}
            </a>
          ))}
        </nav>
      </header>
      <Suspense fallback={<main id="main" tabIndex={-1} className="app-field"><p>{t("region.loading")}</p></main>}>
        {index && route.fieldId ? (
          <main id="main" tabIndex={-1} className="app-field">
            <FieldPage index={index} regionId={index.region_id} fieldId={route.fieldId} tab={route.tab} />
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
              {error ? (
                <p role="alert">{error}</p>
              ) : (
                <div className="rail-loading-placeholder">
                  <h2>{t("fields.heading")}</h2>
                  <p className="muted">{t("region.loading")}</p>
                </div>
              )}
            </aside>
            <div className="map-container">
              <div className="map-loading" />
            </div>
          </main>
        )}
      </Suspense>
      <footer className="app-footer">{t("fixed.judgment")}</footer>
    </div>
  );
}
