import { useEffect, useState } from "react";
import { DemoBanner } from "./DemoBanner";
import { FieldList } from "./FieldList";
import { FieldPage } from "./FieldPage";
import { MapView } from "./MapView";
import { cacheRegionForOffline, loadIndex, loadRegions } from "./data";
import { routeHref, useRoute } from "./route";
import { t } from "./strings";
import type { RegionIndex, RegionList } from "./types";

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

  return (
    <div className="app">
      <DemoBanner />
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <p className="tagline">{t("app.tagline")}</p>
        {regions && regionId && (
          <label className="region-switch">
            {t("region.label")}
            <select value={regionId} onChange={(e) => (window.location.hash = routeHref(e.target.value))}>
              {regions.regions.map((r) => (
                <option key={r.region_id} value={r.region_id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>
      <main className="app-main">
        <aside className="rail">
          {error && <p role="alert">{error}</p>}
          {!error && !index && <p>{t("region.loading")}</p>}
          {index &&
            (route.fieldId ? (
              <FieldPage regionId={index.region_id} fieldId={route.fieldId} />
            ) : (
              <FieldList index={index} selectedId={null} />
            ))}
        </aside>
        {index && (
          <MapView
            index={index}
            selectedId={route.fieldId}
            onSelect={(fid) => (window.location.hash = routeHref(index.region_id, fid))}
          />
        )}
      </main>
      <footer className="app-footer">{t("fixed.judgment")}</footer>
    </div>
  );
}
