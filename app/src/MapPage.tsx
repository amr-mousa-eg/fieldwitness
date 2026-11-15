import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { FieldList } from "./FieldList";
import { GuidancePanel } from "./GuidancePanel";
import { type LayerChoice, LayerPanel, fieldColourDomain } from "./LayerPanel";
import { MapLegend } from "./MapLegend";
import { loadLayers, loadOptionDeltas } from "./data";
import { DIVERGING, RAMPS, fieldValues, gridDomain, gridGeoJSON } from "./mapLayers";
import {
  type RegionOptionDeltas,
  deltaDomain,
  deltaRampForMetric,
  deltaTaggedMap,
  deltaValuesMap,
  isDeltaMetric,
} from "./optionDeltas";
import { routeHref } from "./route";
import { metricName, t } from "./strings";
import { TaggedValue } from "./tags";
import { emitTour } from "./tourEvents";
import type { RegionIndex, RegionLayers } from "./types";

const MapView = lazy(() => import("./MapView").then((m) => ({ default: m.MapView })));

const NO_LAYERS: LayerChoice = { colourBy: null, layerId: null, year: null, backdrop: "modis" };

/** Region map with the field list and the map layers (T9.1, T9.11, S7). */
export function MapPage({ index }: { index: RegionIndex }) {
  const [layers, setLayers] = useState<RegionLayers | null>(null);
  const [optionDeltas, setOptionDeltas] = useState<RegionOptionDeltas | null>(null);
  const [choice, setChoice] = useState<LayerChoice>(NO_LAYERS);

  useEffect(() => {
    setLayers(null);
    setOptionDeltas(null);
    setChoice(NO_LAYERS);
    // Defer layers.json & option_deltas.json slightly so they don't contend with initial map bundle & tiles
    const timer = setTimeout(() => {
      loadLayers(index.region_id)
        .then(setLayers)
        .catch(() => setLayers(null)); // a region without layers.json still shows its fields
      loadOptionDeltas(index.region_id)
        .then(setOptionDeltas)
        .catch(() => setOptionDeltas(null));
    }, 200);
    return () => clearTimeout(timer);
  }, [index.region_id]);

  const colouring = useMemo(() => {
    if (!choice.colourBy) return null;
    if (isDeltaMetric(choice.colourBy)) {
      if (!optionDeltas) return null;
      return {
        values: deltaValuesMap(optionDeltas, choice.colourBy),
        domain: deltaDomain(optionDeltas, choice.colourBy),
        ramp: deltaRampForMetric(choice.colourBy),
      };
    }
    if (!layers) return null;
    return {
      values: fieldValues(layers, choice.colourBy),
      domain: fieldColourDomain(layers, choice.colourBy),
      ramp: RAMPS.sequential,
    };
  }, [layers, optionDeltas, choice.colourBy]);

  const activeLayer = useMemo(
    () => layers?.layers.find((l) => l.layer_id === choice.layerId) ?? null,
    [layers, choice.layerId],
  );
  const activeYear = useMemo(() => {
    if (!activeLayer) return undefined;
    const years = activeLayer.grid.years;
    return choice.year !== null && years.includes(choice.year) ? choice.year : years[years.length - 1];
  }, [activeLayer, choice.year]);

  const grid = useMemo(() => {
    if (!activeLayer || activeYear === undefined) return null;
    return {
      data: gridGeoJSON(activeLayer, activeYear),
      domain: gridDomain(activeLayer),
      ramp: DIVERGING.has(activeLayer.layer_id) ? RAMPS.diverging : RAMPS.sequential,
    };
  }, [activeLayer, activeYear]);

  const sample = useMemo(() => {
    if (!choice.colourBy) return undefined;
    if (isDeltaMetric(choice.colourBy)) {
      return optionDeltas ? deltaTaggedMap(optionDeltas, choice.colourBy) : undefined;
    }
    return layers ? layers.field_colouring[choice.colourBy] : undefined;
  }, [layers, optionDeltas, choice.colourBy]);

  const hudInfo = useMemo(() => {
    if (!sample && !optionDeltas && !activeLayer) return null;
    return {
      activeLabel: choice.colourBy ? metricName(choice.colourBy) : undefined,
      tagged: sample,
      deltas: isDeltaMetric(choice.colourBy) ? optionDeltas?.fields : undefined,
      gridLabel: activeLayer ? t(`layer.${activeLayer.layer_id}`) : undefined,
      gridYear: activeYear,
      gridUnit: activeLayer?.grid.unit,
      gridTag: activeLayer?.grid.tag,
      gridSource: activeLayer?.grid.source,
    };
  }, [sample, optionDeltas, choice.colourBy, activeLayer, activeYear]);

  const activeDeltaMetric = isDeltaMetric(choice.colourBy) ? choice.colourBy : null;
  const activeDeltaSummary = activeDeltaMetric && optionDeltas ? optionDeltas.summary[activeDeltaMetric] : null;
  const unsimulatedCount =
    activeDeltaSummary && optionDeltas ? Math.max(0, optionDeltas.n_fields - activeDeltaSummary.valid_count) : 0;

  return (
    <main id="main" tabIndex={-1} className="app-main">
      <aside className="rail">
        {layers ? (
          <LayerPanel
            layers={layers}
            choice={choice}
            set={setChoice}
            optionDeltas={optionDeltas}
            hasBasemap={Boolean(index.basemap)}
          />
        ) : (
          <div className="layer-panel-placeholder" aria-hidden="true" />
        )}
        <FieldList
          index={index}
          selectedId={null}
          values={sample}
          valueLabel={choice.colourBy ? metricName(choice.colourBy) : ""}
        />
      </aside>
      <div className="map-container">
        {activeDeltaMetric && activeDeltaSummary && (
          <div className="s7-summary-strip" role="status">
            <div className="s7-summary-main">
              <strong>{metricName(activeDeltaMetric)}</strong>
              <span className="s7-summary-stat">
                {t("layers.deltaSummary.mean")} <TaggedValue v={activeDeltaSummary.mean} />
              </span>
              <span className="s7-summary-stat">
                {t("layers.deltaSummary.improved", {
                  improved: activeDeltaSummary.improved_count,
                  valid: activeDeltaSummary.valid_count,
                })}
                {unsimulatedCount > 0 ? ` ${t("layers.deltaSummary.unsimulated", { unsim: unsimulatedCount })}` : ""}
              </span>
            </div>
            <button
              type="button"
              className="s7-clear-btn"
              onClick={() => setChoice((prev) => ({ ...prev, colourBy: null }))}
            >
              {t("layers.deltaSummary.clear")}
            </button>
          </div>
        )}
        <GuidancePanel regionName={index.name} fieldCount={index.fields.length} />
        <Suspense fallback={<div className="map-loading" />}>
          <MapView
            index={index}
            selectedId={null}
            onSelect={(fid) => {
              emitTour("field");
              window.location.hash = routeHref(index.region_id, fid);
            }}
            colouring={colouring}
            grid={grid}
            backdropId={choice.backdrop ?? "modis"}
            hudInfo={hudInfo}
          />
        </Suspense>
        <MapLegend allowGradeA={index.region_id !== "ks_t14slh"} />
      </div>
    </main>
  );
}
