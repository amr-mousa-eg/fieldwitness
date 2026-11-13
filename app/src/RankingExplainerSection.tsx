import { useMemo } from "react";
import { Explain } from "./Explain";
import { unitLabel } from "./format";
import { type Priorities, type Ranked } from "./rank";
import { explainTopRanking, type RankingExplanation } from "./rankingExplainer";
import { optionName, t } from "./strings";
import { TagBadge } from "./tags";
import { useTourSeen } from "./tourEvents";
import type { Tag } from "./types";

export function RankingExplainerSection({
  ranked,
  priorities,
}: {
  ranked: Ranked[];
  priorities: Priorities;
}) {
  const seenRef = useTourSeen("why-ranking");
  const kept = useMemo(() => ranked.filter((r) => r.kept), [ranked]);
  const explanation: RankingExplanation | null = useMemo(
    () => explainTopRanking(kept, priorities),
    [kept, priorities]
  );

  if (!explanation || !explanation.next) return null;

  const { top, next, sentence, dominantPriority } = explanation;

  return (
    <section ref={seenRef} className="ranking-explainer-card" aria-labelledby="ranking-explainer-h">
      <h4 id="ranking-explainer-h" className="ranking-explainer-title">
        {t("rankExplainer.heading")}
        <Explain id="pareto_ranking" />
      </h4>
      <p className="ranking-explainer-sentence" data-testid="ranking-explainer-sentence">
        {sentence}
      </p>

      <div className="ranking-explainer-table-wrap">
        <table className="ranking-explainer-table" aria-label={t("rankExplainer.tableAria")}>
          <thead>
            <tr>
              <th scope="col">{t("rankExplainer.thCriterion")}</th>
              <th scope="col">
                {t("rankExplainer.thWeight")} <TagBadge tag="A" source={t("rankExplainer.weightSource")} />
              </th>
              <th scope="col">
                {optionName(top.option)} <span className="rank-badge top-badge">#1</span>
              </th>
              <th scope="col">
                {optionName(next.option)} <span className="rank-badge next-badge">#2</span>
              </th>
              <th scope="col">{t("rankExplainer.thImpact")}</th>
            </tr>
          </thead>
          <tbody>
            {top.contributions.map((cTop, idx) => {
              const cNext = next.contributions[idx];
              const diff = cTop.contribution - cNext.contribution;
              const isDominant = cTop.key === dominantPriority;
              return (
                <tr
                  key={cTop.key}
                  className={isDominant ? "ranking-explainer-row-dominant" : undefined}
                >
                  <td className="ranking-explainer-crit-cell">
                    <span className="crit-label">{cTop.label}</span>
                    {isDominant && (
                      <span className="dominant-tag" title={t("rankExplainer.primaryTitle")}>
                        {t("rankExplainer.primary")}
                      </span>
                    )}
                  </td>
                  <td className="ranking-explainer-num-cell">
                    <span className="weight-val">{cTop.weight}×</span>
                  </td>
                  <td className="ranking-explainer-num-cell">
                    <div className="bar-and-num">
                      <div className="score-bar-bg" aria-hidden="true">
                        <div
                          className="score-bar-fill top-fill"
                          style={{ width: `${Math.round(cTop.scaledValue * 100)}%` }}
                        />
                      </div>
                      <span className="norm-val">{(cTop.scaledValue * 100).toFixed(0)}%</span>
                    </div>
                    <div className="raw-metrics-list">
                      {cTop.metrics.map((m) => (
                        <span key={m.metric} className="raw-metric-chip">
                          {m.value != null ? m.value.toFixed(1) : "—"} {unitLabel(m.unit)}{" "}
                          <TagBadge tag={m.tag as Tag} source={t("rankExplainer.metricSource")} />
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="ranking-explainer-num-cell">
                    <div className="bar-and-num">
                      <div className="score-bar-bg" aria-hidden="true">
                        <div
                          className="score-bar-fill next-fill"
                          style={{ width: `${Math.round(cNext.scaledValue * 100)}%` }}
                        />
                      </div>
                      <span className="norm-val">{(cNext.scaledValue * 100).toFixed(0)}%</span>
                    </div>
                    <div className="raw-metrics-list">
                      {cNext.metrics.map((m) => (
                        <span key={m.metric} className="raw-metric-chip">
                          {m.value != null ? m.value.toFixed(1) : "—"} {unitLabel(m.unit)}{" "}
                          <TagBadge tag={m.tag as Tag} source={t("rankExplainer.metricSource")} />
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="ranking-explainer-num-cell">
                    <span className={`diff-val ${diff > 0.001 ? "diff-pos" : diff < -0.001 ? "diff-neg" : ""}`}>
                      {diff > 0 ? `+${diff.toFixed(3)}` : diff.toFixed(3)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="ranking-explainer-total-row">
              <th scope="row">{t("rankExplainer.thTotal")}</th>
              <td>—</td>
              <td className="ranking-explainer-num-cell">
                <strong>{top.totalScore.toFixed(3)}</strong>
              </td>
              <td className="ranking-explainer-num-cell">
                <strong>{next.totalScore.toFixed(3)}</strong>
              </td>
              <td className="ranking-explainer-num-cell">
                <strong>+{(top.totalScore - next.totalScore).toFixed(3)}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <p className="ranking-explainer-caption">
        {t("rankExplainer.caption")}
      </p>
    </section>
  );
}

// Alias export for backwards compatibility
export const RankingExplainer = RankingExplainerSection;
