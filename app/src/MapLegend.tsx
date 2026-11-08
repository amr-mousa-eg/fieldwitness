import { useState } from "react";
import { t } from "./strings";

/**
 * P0.3 Map Legend:
 * Explains marker/outline colours, grade badges, and scale-flag symbols.
 * Collapsible on mobile phones, accessible, supports both light and dark themes.
 */
export function MapLegend() {
  const isMobile = typeof window !== "undefined" && window.innerWidth <= 768;
  const [open, setOpen] = useState(!isMobile);

  return (
    <details
      className="map-legend"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
      aria-label={t("legend.title")}
    >
      <summary className="map-legend-summary">
        <span className="map-legend-heading">{t("legend.title")}</span>
      </summary>
      <div className="map-legend-content">
        <section className="map-legend-section">
          <h4 className="map-legend-subtitle">{t("legend.mapFeatures")}</h4>
          <ul className="map-legend-list">
            <li>
              <span className="legend-swatch-field" aria-hidden="true" />
              <span>{t("legend.fieldOutline")}</span>
            </li>
            <li>
              <span className="legend-swatch-selected" aria-hidden="true" />
              <span>{t("legend.fieldSelected")}</span>
            </li>
            <li>
              <span className="legend-swatch-tile" aria-hidden="true" />
              <span>{t("legend.tileBoundary")}</span>
            </li>
          </ul>
        </section>

        <section className="map-legend-section">
          <h4 className="map-legend-subtitle">{t("legend.evidenceGrades")}</h4>
          <ul className="map-legend-list">
            <li>
              <span className="grade grade-B" aria-hidden="true">
                B
              </span>
              <span>{t("legend.gradeB")}</span>
            </li>
            <li>
              <span className="grade grade-C" aria-hidden="true">
                C
              </span>
              <span>{t("legend.gradeC")}</span>
            </li>
            <li>
              <span className="grade grade-D" aria-hidden="true">
                D
              </span>
              <span>{t("legend.gradeD")}</span>
            </li>
            <li className="muted">
              <span className="grade grade-A grade-disabled" aria-hidden="true">
                A
              </span>
              <span>{t("legend.gradeA")}</span>
            </li>
          </ul>
        </section>

        <section className="map-legend-section">
          <h4 className="map-legend-subtitle">{t("scale.heading")}</h4>
          <ul className="map-legend-list">
            <li>
              <span className="flag-symbol flag-fine" aria-hidden="true">
                ●
              </span>
              <span>{t("legend.scaleFine")}</span>
            </li>
            <li>
              <span className="flag-symbol flag-coarse" aria-hidden="true">
                ◌
              </span>
              <span>{t("legend.scaleCoarse")}</span>
            </li>
          </ul>
        </section>
      </div>
    </details>
  );
}
