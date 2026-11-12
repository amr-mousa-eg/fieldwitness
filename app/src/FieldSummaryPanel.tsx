import { Fragment } from "react";
import { type ComparisonSummary } from "./fieldSummary";
import { optionName, t } from "./strings";
import { TagBadge } from "./tags";

export function FieldSummaryPanel({ summary }: { summary: ComparisonSummary }) {
  const { currentOption, topAlternative, isCurrentBest, currentNotSimulated: ns, tokens, metrics } = summary;
  const target = topAlternative ?? currentOption;

  return (
    <div className="field-summary-card" aria-labelledby="field-summary-h">
      <h4 id="field-summary-h" className="field-summary-title">
        {t("summary.heading")}
      </h4>
      <p className="field-summary-sentence" data-testid="summary-sentence">
        {tokens.map((token, i) => {
          if (token.kind === "text") {
            return <Fragment key={i}>{token.text}</Fragment>;
          }
          if (token.kind === "grade") {
            return (
              <span key={i} className={`grade grade-${token.grade}`}>
                {token.grade}
              </span>
            );
          }
          if (token.kind === "tagged") {
            return (
              <span key={i} className="tagged-inline">
                <strong>
                  {token.value} {token.unit}
                </strong>{" "}
                <TagBadge tag={token.tag} source={token.source} />
              </span>
            );
          }
          return null;
        })}
      </p>

      <div className="summary-comparison-wrap">
        <table className="summary-comparison-table" aria-label={t("summary.comparisonLabel")}>
          <thead>
            <tr>
              <th scope="col">{t("summary.metric")}</th>
              <th scope="col">
                <span className="summary-col-title">{t("card.current")}</span>
                <span className="summary-col-sub">({currentOption.sequence.join(" → ")})</span>
              </th>
              <th scope="col">
                <span className="summary-col-title">
                  {isCurrentBest ? t("summary.topAlternative") : optionName(target)}
                </span>
                <span className="summary-col-sub">({target.sequence.join(" → ")})</span>
              </th>
              <th scope="col">{t("summary.difference")}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">
                {metrics.water_use.label}{" "}
                <TagBadge tag={metrics.water_use.tag} source={metrics.water_use.source} />
              </th>
              <td className={ns ? "muted" : undefined}>
                {ns ? t("season.notSimulated") : `${metrics.water_use.currentValue.toLocaleString()} ${metrics.water_use.unit}`}
              </td>
              <td>
                {metrics.water_use.topValue.toLocaleString()} {metrics.water_use.unit}
              </td>
              <td
                className={
                  ns || metrics.water_use.isAboutTheSame
                    ? "diff-same"
                    : metrics.water_use.diff < 0
                    ? "diff-pro"
                    : "diff-con"
                }
              >
                {ns
                  ? "—"
                  : metrics.water_use.isAboutTheSame
                  ? t("summary.aboutTheSame")
                  : `${metrics.water_use.diff > 0 ? "+" : ""}${metrics.water_use.diff} ${
                      metrics.water_use.unit
                    }`}
              </td>
            </tr>
            <tr>
              <th scope="row">
                {metrics.bad_year_water.label}{" "}
                <TagBadge tag={metrics.bad_year_water.tag} source={metrics.bad_year_water.source} />
              </th>
              <td className={ns ? "muted" : undefined}>
                {ns ? t("season.notSimulated") : `${metrics.bad_year_water.currentValue.toLocaleString()} ${metrics.bad_year_water.unit}`}
              </td>
              <td>
                {metrics.bad_year_water.topValue.toLocaleString()} {metrics.bad_year_water.unit}
              </td>
              <td
                className={
                  ns || metrics.bad_year_water.isAboutTheSame
                    ? "diff-same"
                    : metrics.bad_year_water.diff < 0
                    ? "diff-pro"
                    : "diff-con"
                }
              >
                {ns
                  ? "—"
                  : metrics.bad_year_water.isAboutTheSame
                  ? t("summary.aboutTheSame")
                  : `${metrics.bad_year_water.diff > 0 ? "+" : ""}${metrics.bad_year_water.diff} ${
                      metrics.bad_year_water.unit
                    }`}
              </td>
            </tr>
            <tr>
              <th scope="row">
                {metrics.bare_soil.label}{" "}
                <TagBadge tag={metrics.bare_soil.tag} source={metrics.bare_soil.source} />
              </th>
              <td className={ns ? "muted" : undefined}>
                {ns ? t("season.notSimulated") : `${metrics.bare_soil.currentValue.toFixed(1)} ${metrics.bare_soil.unit}`}
              </td>
              <td>
                {metrics.bare_soil.topValue.toFixed(1)} {metrics.bare_soil.unit}
              </td>
              <td
                className={
                  ns || metrics.bare_soil.isAboutTheSame
                    ? "diff-same"
                    : metrics.bare_soil.diff < 0
                    ? "diff-pro"
                    : "diff-con"
                }
              >
                {ns
                  ? "—"
                  : metrics.bare_soil.isAboutTheSame
                  ? t("summary.aboutTheSame")
                  : `${metrics.bare_soil.diff > 0 ? "+" : ""}${metrics.bare_soil.diff.toFixed(1)} ${
                      metrics.bare_soil.unit
                    }`}
              </td>
            </tr>
            <tr>
              <th scope="row">{t("card.grade")}</th>
              <td>
                <span className={`grade grade-${currentOption.grade}`}>{currentOption.grade}</span>
              </td>
              <td>
                <span className={`grade grade-${target.grade}`}>{target.grade}</span>
              </td>
              <td>
                {ns
                  ? "—"
                  : currentOption.grade === target.grade
                  ? t("summary.aboutTheSame")
                  : `${currentOption.grade} → ${target.grade}`}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
