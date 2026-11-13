import { useEffect } from "react";
import { DiagnosisSection } from "./DiagnosisSection";
import { Explain } from "./Explain";
import { MethodsDiagram } from "./MethodsDiagram";
import { IS_DEMO_DATA } from "./data";
import { EXPLAINERS, explainer } from "./explainers";
import { type StringKey, t } from "./strings";
import { TagBadge, TagLegend } from "./tags";

/** Datasets as listed in DATA.md; text in strings/en.json (methods.ds.<id>.*). */
/** Datasets as listed in DATA.md; text in strings/en.json (methods.ds.<id>.*). */
export const DATASETS = [
  "hls",
  "power",
  "smap",
  "gpm",
  "nasadem",
  "viirs",
  "ecostress",
  "grace",
  "soilgrids",
  "ssurgo",
  "csb",
  "prism",
  "naip",
  "nlcd",
  "ldas",
  "gaez",
  "cocorahs",
  "nwis",
  "quickstats",
  "agdatacommons",
  "landfire",
  "era5",
  "openet",
  "gedi",
  "ams",
  "ftw",
  "rpg",
  "hcat",
  "fao56",
  "faostat",
  "taxonomy",
] as const;

const REPO_URL = "https://github.com/amr-mousa-eg/fieldwitness";

const list = (prefix: string, n: number) =>
  Array.from({ length: n }, (_, i) => t(`${prefix}.${i + 1}` as StringKey));

/**
 * Links such as #/kansas/methods#glossary-hindcast carry a second "#" inside the hash route, so
 * the browser cannot scroll to the target by itself. Scroll there and move keyboard focus to it
 * on load and whenever the hash changes (diagram boxes, "Open in glossary" links).
 */
function useAnchorJump(): void {
  useEffect(() => {
    let timer = 0;
    const jump = () => {
      const hash = window.location.hash;
      const at = hash.indexOf("#", 1);
      if (at < 0) return;
      const el = document.getElementById(decodeURIComponent(hash.slice(at + 1)));
      if (!el) return;
      // after App moves focus to <main> on a page change
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

export function MethodsPage() {
  useAnchorJump();
  return (
    <article className="methods" aria-labelledby="methods-h">
      <h2 id="methods-h">{t("methods.heading")}</h2>
      <p className="fixed-line">{t("fixed.judgment")}</p>
      {IS_DEMO_DATA && <p className="notice">{t("methods.demo")}</p>}

      <MethodsDiagram />

      <section aria-labelledby="m-how">
        <h3 id="m-how">
          {t("methods.how")} <Explain id="witness" /> <Explain id="credibility" />
        </h3>
        <ol>
          {list("methods.how", 5).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="m-not">
        <h3 id="m-not">{t("methods.not")}</h3>
        <ul>
          {list("methods.not", 5).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="m-limits">
        <h3 id="m-limits">
          {t("methods.limits")} <Explain id="hindcast" />
        </h3>
        <ul>
          {list("methods.limits", 8).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="m-enhancements">
        <h3 id="m-enhancements">{t("methods.enhancements.heading")}</h3>
        <p className="muted">{t("methods.enhancements.intro")}</p>
        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">{t("methods.enhancements.thAlgo")}</th>
                <th scope="col">{t("methods.enhancements.thMatch")}</th>
                <th scope="col">{t("methods.enhancements.thMultiClass")}</th>
                <th scope="col">{t("methods.enhancements.thFallow")}</th>
                <th scope="col">{t("methods.enhancements.thLatency")}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="row-current">
                <th scope="row">{t("methods.enhancements.algo.twdtw")}</th>
                <td className="best">86.7 %</td>
                <td>72.5 %</td>
                <td>90.0 %</td>
                <td>5.08 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.dtw")}</th>
                <td className="best">88.7 %</td>
                <td>56.2 %</td>
                <td>83.3 %</td>
                <td>4.76 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.wddtw")}</th>
                <td>82.9 %</td>
                <td className="best">75.4 %</td>
                <td className="best">93.3 %</td>
                <td>5.23 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.vdtw")}</th>
                <td>70.8 %</td>
                <td>56.7 %</td>
                <td>61.7 %</td>
                <td>5.14 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.cropformer")}</th>
                <td>78.7 %</td>
                <td>45.0 %</td>
                <td>66.7 %</td>
                <td className="best">1.07 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.sg")}</th>
                <td>{t("methods.enhancements.baselineTag")}</td>
                <td>—</td>
                <td>80.0 %</td>
                <td>12.40 ms</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          {t("methods.enhancements.cqrSummary")}
        </p>
      </section>

      <DiagnosisSection />

      <section aria-labelledby="m-soil">
        <h3 id="m-soil">
          {t("methods.soil.heading")} <Explain id="available_water_capacity" />{" "}
          <TagBadge tag="E" source={t("methods.soil.source")} />
        </h3>
        <p>{t("methods.soil.intro")}</p>
        <ul>
          {list("methods.soil", 4).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
        <p className="muted">{t("methods.soil.source")}</p>
      </section>

      <section aria-labelledby="m-builder">
        <h3 id="m-builder">
          {t("methods.builder.heading")} <Explain id="pareto_ranking" />
        </h3>
        <p>{t("methods.builder.intro")}</p>
        <ul>
          {list("methods.builder", 4).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="m-wrong">
        <h3 id="m-wrong">{t("methods.wrong.heading")}</h3>
        <ul>
          {list("methods.wrong", 9).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="m-roadmap">
        <h3 id="m-roadmap">{t("methods.roadmap")}</h3>
        <p>{t("methods.roadmap.gates")}</p>
        <ul>
          {list("methods.roadmap.gate", 3).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
        <p>{t("methods.roadmap.future_intro")}</p>
        <ul>
          {list("methods.roadmap.future", 5).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
        <p>{t("methods.roadmap.privacy")}</p>
      </section>

      <section aria-labelledby="m-data">
        <h3 id="m-data">{t("methods.data")}</h3>
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

      <section aria-labelledby="m-terms" id="glossary">
        <h3 id="m-terms">{t("methods.terms")}</h3>
        <dl className="glossary">
          {EXPLAINERS.map((id) => {
            const e = explainer(id);
            return (
              <div key={id} id={`glossary-${id}`} className="glossary-entry">
                <dt>{e.title}</dt>
                <dd>
                  {e.body}{" "}
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
            );
          })}
        </dl>
      </section>

      <TagLegend />

      <section aria-labelledby="m-repo">
        <h3 id="m-repo">{t("methods.repo")}</h3>
        <p>
          {t("methods.repo.text")} <a href={REPO_URL}>{REPO_URL}</a>
        </p>
      </section>
    </article>
  );
}
