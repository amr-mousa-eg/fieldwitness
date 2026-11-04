import { useEffect, useState } from "react";
import { DemoBanner } from "./DemoBanner";
import { loadIndex, loadRegions } from "./data";
import { t } from "./strings";
import type { RegionIndex, RegionList } from "./types";

/** Step-1 shell: proves the data path. The Map, Field story and Field Card views replace the list. */
export function App() {
  const [regions, setRegions] = useState<RegionList | null>(null);
  const [regionId, setRegionId] = useState<string>("");
  const [index, setIndex] = useState<RegionIndex | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRegions()
      .then((r) => {
        setRegions(r);
        setRegionId(r.regions[0]?.region_id ?? "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!regionId) return;
    setIndex(null);
    loadIndex(regionId)
      .then(setIndex)
      .catch((e: Error) => setError(e.message));
  }, [regionId]);

  return (
    <>
      <DemoBanner />
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <p>{t("app.tagline")}</p>
        {regions && (
          <label>
            {t("region.label")}{" "}
            <select value={regionId} onChange={(e) => setRegionId(e.target.value)}>
              {regions.regions.map((r) => (
                <option key={r.region_id} value={r.region_id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>
      <main>
        {error && <p role="alert">{t("error.load", { message: error })}</p>}
        {!error && !index && <p>{t("region.loading")}</p>}
        {index && (
          <section>
            <h2>{t("fields.heading")}</h2>
            <ul className="field-list">
              {index.fields.map((f) => (
                <li key={f.field_id}>
                  <code>{f.field_id.slice(0, 8)}</code> · {t("fields.area", { area: f.area_ha })}{" "}
                  · {t("fields.current")}: {f.current_sequence.join(" → ")} ·{" "}
                  {t("fields.top", { grade: f.top_grade })}
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
      <footer className="app-footer">{t("fixed.judgment")}</footer>
    </>
  );
}
