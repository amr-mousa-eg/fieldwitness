import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { DemoBanner } from "./DemoBanner";
import { LangToggle } from "./LangToggle";
import { MapPage } from "./MapPage";
import { loadIndex, loadRegions } from "./data";
import { DOCS_PAGES, PRIMARY_PAGES, pageHref, useRoute } from "./route";
import { ThemeToggle } from "./ThemeToggle";
import { t, useLocale } from "./strings";
import type { RegionIndex, RegionList } from "./types";

const HomePage = lazy(() => import("./HomePage").then((m) => ({ default: m.HomePage })));
const FieldPage = lazy(() => import("./FieldPage").then((m) => ({ default: m.FieldPage })));
const Scoreboard = lazy(() => import("./Scoreboard").then((m) => ({ default: m.Scoreboard })));
const ComparePage = lazy(() => import("./ComparePage").then((m) => ({ default: m.ComparePage })));
const MethodsPage = lazy(() => import("./MethodsPage").then((m) => ({ default: m.MethodsPage })));
const ResourcesPage = lazy(() => import("./ResourcesPage").then((m) => ({ default: m.ResourcesPage })));
const TermsPage = lazy(() => import("./TermsPage").then((m) => ({ default: m.TermsPage })));
const AddFieldPage = lazy(() => import("./AddFieldPage").then((m) => ({ default: m.AddFieldPage })));
const TourGuide = lazy(() => import("./TourGuide").then((m) => ({ default: m.TourGuide })));
const FieldChatbot = lazy(() => import("./FieldChatbot").then((m) => ({ default: m.FieldChatbot })));

/** Every page renders exactly one <main id="main" tabIndex={-1}>. */
function focusMain(): void {
  document.getElementById("main")?.focus();
}

export function App() {
  useLocale();
  const route = useRoute();
  const [regions, setRegions] = useState<RegionList | null>(null);
  const [index, setIndex] = useState<RegionIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [docsMenuOpen, setDocsMenuOpen] = useState(false);
  const docsMenuRef = useRef<HTMLDivElement | null>(null);
  const regionId = route.regionId ?? regions?.regions[0]?.region_id ?? null;

  useEffect(() => {
    loadRegions()
      .then(setRegions)
      .catch((e: Error) => setError(t("error.load", { what: t("error.what.regions"), message: e.message })));
  }, []);

  useEffect(() => {
    if (!regionId) return;
    setIndex(null);
    loadIndex(regionId)
      .then((idx) => {
        setIndex(idx);
      })
      .catch((e: Error) => setError(t("error.load", { what: t("error.what.region"), message: e.message })));
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

  // Close NASA-style dropdown on navigation, outside pointerdown, or Escape
  useEffect(() => {
    setDocsMenuOpen(false);
  }, [route.page, route.regionId, route.fieldId]);

  useEffect(() => {
    if (!docsMenuOpen) return;
    const onPointer = (e: PointerEvent) => {
      if (docsMenuRef.current && !docsMenuRef.current.contains(e.target as Node)) {
        setDocsMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDocsMenuOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [docsMenuOpen]);

  const isMap = !route.fieldId && route.page === "map";
  const isDocsActive = !route.fieldId && (DOCS_PAGES as readonly string[]).includes(route.page);

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
      <div className="app-top">
        <DemoBanner />
        <header className="app-header">
          <div className="brand-block">
            <a href="#/home" className="brand-link">
              <h1>{t("app.title")}</h1>
            </a>
            <p className="tagline">{t("app.tagline")}</p>
          </div>
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
            <button
              type="button"
              className="tour-btn"
              onClick={() => setIsTourOpen(true)}
              aria-label={t("tour.launch")}
            >
              {t("tour.launch")}
            </button>
            <LangToggle />
            <ThemeToggle />
          </div>
          <nav className="app-nav" aria-label={t("nav.label")}>
            {PRIMARY_PAGES.map((p) => (
              <a
                key={p}
                data-nav={p}
                href={pageHref(regionId ?? "ks_t14slh", p)}
                aria-current={!route.fieldId && route.page === p ? "page" : undefined}
              >
                {t(`nav.${p}`)}
              </a>
            ))}
            <div
              className={`nav-dropdown${docsMenuOpen ? " nav-dropdown--open" : ""}`}
              ref={docsMenuRef}
            >
              <button
                type="button"
                className="nav-dropdown-trigger"
                aria-haspopup="menu"
                aria-expanded={docsMenuOpen}
                aria-current={isDocsActive ? "page" : undefined}
                onClick={() => setDocsMenuOpen((v) => !v)}
              >
                <span>{t("nav.docsGroup")}</span>
                <span className="nav-dropdown-caret" aria-hidden="true">
                  ▾
                </span>
              </button>
              {docsMenuOpen && (
                <ul className="nav-dropdown-menu" role="menu" aria-label={t("nav.docsGroup")}>
                  {DOCS_PAGES.map((p) => (
                    <li key={p} role="none">
                      <a
                        role="menuitem"
                        data-nav={p}
                        href={pageHref(regionId ?? "ks_t14slh", p)}
                        aria-current={!route.fieldId && route.page === p ? "page" : undefined}
                        onClick={() => setDocsMenuOpen(false)}
                      >
                        <strong>{t(`nav.${p}`)}</strong>
                        <span>{t(`nav.desc.${p}`)}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </nav>
        </header>
      </div>
      <Suspense
        fallback={
          <main id="main" tabIndex={-1} className="app-field">
            <p>{t("region.loading")}</p>
          </main>
        }
      >
        {index && route.fieldId ? (
          <main id="main" tabIndex={-1} className="app-field">
            <FieldPage index={index} regionId={index.region_id} fieldId={route.fieldId} tab={route.tab} />
          </main>
        ) : route.page === "home" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <HomePage regionId={regionId ?? "ks_t14slh"} />
          </main>
        ) : index && route.page === "scoreboard" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <Scoreboard index={index} />
          </main>
        ) : index && route.page === "compare" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <ComparePage index={index} />
          </main>
        ) : route.page === "methods" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <MethodsPage />
          </main>
        ) : route.page === "resources" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <ResourcesPage />
          </main>
        ) : route.page === "terms" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <TermsPage />
          </main>
        ) : route.page === "add-field" ? (
          <main id="main" tabIndex={-1} className="app-field">
            <AddFieldPage index={index} regionId={regionId ?? "ks_t14slh"} />
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
      {isTourOpen && (
        <Suspense fallback={null}>
          <TourGuide isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
        </Suspense>
      )}
      <Suspense fallback={null}>
        <FieldChatbot
          page={route.page ?? "home"}
          regionId={regionId ?? "ks_t14slh"}
          fieldId={route.fieldId ?? undefined}
          index={index}
        />
      </Suspense>
    </div>
  );
}
