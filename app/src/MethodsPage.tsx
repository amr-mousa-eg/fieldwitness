import { useEffect } from "react";
import { DiagnosisSection } from "./DiagnosisSection";
import { Explain } from "./Explain";
import { MethodsDiagram } from "./MethodsDiagram";
import { IS_DEMO_DATA } from "./data";
import { pageHref, useRoute } from "./route";
import { type StringKey, t } from "./strings";
import { TagBadge } from "./tags";
import { UkraineNeighboursSection } from "./UkraineNeighboursSection";

export { DATASETS } from "./datasets";

const list = (prefix: string, n: number) =>
  Array.from({ length: n }, (_, i) => t(`${prefix}.${i + 1}` as StringKey));

/**
 * Links such as #/kansas/methods#m-limits carry a second "#" inside the hash route, so
 * the browser cannot scroll to the target by itself. Scroll there and move keyboard focus to it
 * on load and whenever the hash changes.
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
  const regionId = useRoute().regionId ?? "ks_t14slh";

  return (
    <article className="methods" aria-labelledby="methods-h">
      <div className="ref-page-head">
        <div>
          <h2 id="methods-h">{t("methods.heading")}</h2>
          <p className="fixed-line">{t("fixed.judgment")}</p>
        </div>
        <div className="ref-page-links">
          <a className="secondary-btn" href={pageHref(regionId, "resources")}>
            {t("nav.resources")} →
          </a>
          <a className="secondary-btn" href={pageHref(regionId, "terms")}>
            {t("nav.terms")} →
          </a>
        </div>
      </div>

      {IS_DEMO_DATA && <p className="notice">{t("methods.demo")}</p>}

      <MethodsDiagram />

      <section id="m-regions" aria-labelledby="m-regions-h">
        <h3 id="m-regions-h">{t("methods.regions.heading")}</h3>
        <p className="muted">{t("methods.regions.intro")}</p>
        <div className="table-wrap">
          <table className="scores">
            <thead>
              <tr>
                <th scope="col">{t("methods.regions.thRegion")}</th>
                <th scope="col">{t("methods.regions.thFields")}</th>
                <th scope="col">{t("methods.regions.thSoil")}</th>
                <th scope="col">{t("methods.regions.thAbc")}</th>
                <th scope="col">{t("methods.regions.thNeighbours")}</th>
                <th scope="col">{t("methods.regions.thGrades")}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">
                  <span className="method-name">{t("methods.regions.ks.name")}</span>
                  <span className="method-desc">{t("methods.regions.ks.tier")}</span>
                </th>
                <td>{t("methods.regions.ks.fields")}</td>
                <td>{t("methods.regions.ks.soil")}</td>
                <td>{t("methods.regions.ks.abc")}</td>
                <td>{t("methods.regions.ks.neighbours")}</td>
                <td>{t("methods.regions.ks.grades")}</td>
              </tr>
              <tr className="row-current">
                <th scope="row">
                  <span className="method-name">{t("methods.regions.ua.name")}</span>
                  <span className="method-desc">{t("methods.regions.ua.tier")}</span>
                </th>
                <td>{t("methods.regions.ua.fields")}</td>
                <td>{t("methods.regions.ua.soil")}</td>
                <td>{t("methods.regions.ua.abc")}</td>
                <td className="best">{t("methods.regions.ua.neighbours")}</td>
                <td className="best">{t("methods.regions.ua.grades")}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="m-how" id="m-how-sec">
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
                <td>5.04 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.dtw")}</th>
                <td className="best">88.7 %</td>
                <td>56.2 %</td>
                <td>83.3 %</td>
                <td>4.84 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.wddtw")}</th>
                <td>82.9 %</td>
                <td>75.4 %</td>
                <td className="best">93.3 %</td>
                <td>4.84 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.vdtw")}</th>
                <td>70.8 %</td>
                <td>56.7 %</td>
                <td>61.7 %</td>
                <td>4.59 ms</td>
              </tr>
              <tr>
                <th scope="row">{t("methods.enhancements.algo.cropformer")}</th>
                <td className="best">86.7 %</td>
                <td className="best">75.8 %</td>
                <td>78.3 %</td>
                <td className="best">1.05 ms</td>
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

      <UkraineNeighboursSection />

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
    </article>
  );
}
