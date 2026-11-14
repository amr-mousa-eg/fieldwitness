import { UKRAINE_NEIGHBOURS_DATA } from "./ukraineNeighbours";
import { type StringKey, cropName, t } from "./strings";
import { TagBadge } from "./tags";

function fmtSigned(n: number): string {
  const s = n > 0 ? `+${n.toFixed(3)}` : n.toFixed(3);
  return s;
}

export function UkraineNeighboursSection() {
  const d = UKRAINE_NEIGHBOURS_DATA;

  return (
    <section
      id="m-ukraine"
      className="score-block ukraine-neighbours-section"
      aria-labelledby="ukraine-neighbours-h"
    >
      <h3 id="ukraine-neighbours-h">
        {t("ukraineNeighbours.heading")}{" "}
        <TagBadge tag="D" source="Sentinel-2 L2A + TWDTW (Tier 3)" />
      </h3>
      <p className="muted" style={{ fontSize: "0.88rem", marginBottom: "0.75rem" }}>
        {t("ukraineNeighbours.intro", {
          fields: d.pilotFields,
          blocks: d.spatialBlocks,
          seasons: d.fieldSeasons,
          outcomes: d.fieldSeasonsWithOutcomes,
          area: d.medianAreaHa.toFixed(1),
        })}
      </p>

      <div className="notice" style={{ marginBottom: "1rem" }}>
        <strong>{t("ukraineNeighbours.verdictTitle")}</strong>
        <p style={{ marginTop: "0.25rem", marginBottom: 0 }}>
          {t("ukraineNeighbours.verdictBody", {
            pre: d.preCutoffEvidenceTotal,
            full: d.fullPeriodEvidenceTotal,
          })}
        </p>
      </div>

      <div className="table-wrap" style={{ marginBottom: "1.25rem" }}>
        <table className="scores">
          <thead>
            <tr>
              <th scope="col">{t("ukraineNeighbours.thDesign")}</th>
              <th scope="col">{t("ukraineNeighbours.thRegion")}</th>
              <th scope="col">{t("ukraineNeighbours.thFitted")}</th>
              <th scope="col">{t("ukraineNeighbours.thOverlap")}</th>
              <th scope="col">{t("ukraineNeighbours.thBalance")}</th>
              <th scope="col">{t("ukraineNeighbours.thPlacebo")}</th>
              <th scope="col">{t("ukraineNeighbours.thNegCtrl")}</th>
              <th scope="col">{t("ukraineNeighbours.thEvidence")}</th>
            </tr>
          </thead>
          <tbody>
            {d.comparisonRows.map((row) => {
              const isUkraine = row.regionKey !== "kansas";
              return (
                <tr
                  key={`${row.design}-${row.regionKey}`}
                  className={row.evidencePass > 0 ? "row-current" : undefined}
                >
                  <th scope="row">
                    <span className="method-name">
                      {t(`ukraineNeighbours.design.${row.design}` as StringKey)}
                    </span>
                  </th>
                  <td>
                    <span className={isUkraine ? undefined : "muted"}>
                      {t(`ukraineNeighbours.region.${row.regionKey}` as StringKey)}
                    </span>
                  </td>
                  <td>{row.fitted}</td>
                  <td>
                    {row.overlapPass}/{row.fitted}
                  </td>
                  <td>
                    {row.balancePass}/{row.fitted}
                  </td>
                  <td>
                    {row.placeboTested > 0
                      ? `${row.placeboPass}/${row.placeboTested}`
                      : t("value.none")}
                  </td>
                  <td>
                    {row.negCtrlTested > 0
                      ? `${row.negCtrlPass}/${row.negCtrlTested}`
                      : t("value.none")}
                  </td>
                  <td className={row.evidencePass > 0 ? "best" : "muted"}>
                    <strong>{row.evidencePass}</strong>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h4 style={{ margin: "0 0 0.4rem 0", fontSize: "0.95rem" }}>
        {t("ukraineNeighbours.highlightsHeading")}
      </h4>
      <p className="muted" style={{ fontSize: "0.82rem", margin: "0 0 0.6rem 0" }}>
        {t("ukraineNeighbours.highlightsNote")}
      </p>
      <div className="table-wrap">
        <table className="scores">
          <thead>
            <tr>
              <th scope="col">{t("ukraineNeighbours.thDesign")}</th>
              <th scope="col">{t("ukraineNeighbours.thCrop")}</th>
              <th scope="col">{t("ukraineNeighbours.thContrast")}</th>
              <th scope="col">{t("ukraineNeighbours.thOutcome")}</th>
              <th scope="col">{t("ukraineNeighbours.thEstimate")}</th>
            </tr>
          </thead>
          <tbody>
            {d.preCutoffHighlights.map((h, i) => (
              <tr key={i}>
                <th scope="row">
                  <span className="method-name">
                    {t(`ukraineNeighbours.design.${h.design}` as StringKey)}
                  </span>
                  {h.prev2Crop && (
                    <span className="method-desc">
                      {t("ukraineNeighbours.prev2", { crop: cropName(h.prev2Crop) })}
                    </span>
                  )}
                </th>
                <td>{cropName(h.crop)}</td>
                <td>{h.contrast}</td>
                <td>{h.outcome}</td>
                <td>
                  <bdi dir="ltr">
                    <strong>{fmtSigned(h.estimate)}</strong> [{fmtSigned(h.ciLo)},{" "}
                    {fmtSigned(h.ciHi)}]
                  </bdi>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
