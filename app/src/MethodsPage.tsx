import { DiagnosisSection } from "./DiagnosisSection";
import { MethodsDiagram } from "./MethodsDiagram";
import { IS_DEMO_DATA } from "./data";
import { EXPLAINERS, explainer } from "./explainers";
import { type StringKey, t } from "./strings";
import { TagLegend } from "./tags";

/** Datasets as listed in DATA.md; text in strings/en.json (methods.ds.<id>.*). */
export const DATASETS = [
  "hls",
  "power",
  "smap",
  "grace",
  "nasadem",
  "soilgrids",
  "csb",
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

export function MethodsPage() {
  return (
    <article className="methods" aria-labelledby="methods-h">
      <h2 id="methods-h">{t("methods.heading")}</h2>
      <p className="fixed-line">{t("fixed.judgment")}</p>
      {IS_DEMO_DATA && <p className="notice">{t("methods.demo")}</p>}

      <MethodsDiagram />

      <section aria-labelledby="m-how">
        <h3 id="m-how">{t("methods.how")}</h3>
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
        <h3 id="m-limits">{t("methods.limits")}</h3>
        <ul>
          {list("methods.limits", 8).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <DiagnosisSection />

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

      <section aria-labelledby="m-terms">
        <h3 id="m-terms">{t("methods.terms")}</h3>
        <dl className="glossary">
          {EXPLAINERS.map((id) => {
            const e = explainer(id);
            return (
              <div key={id}>
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
