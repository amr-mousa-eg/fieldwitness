import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { FieldList } from "./FieldList";
import { GuidancePanel } from "./GuidancePanel";
import { type LayerChoice, LayerPanel, fieldColourDomain } from "./LayerPanel";
import { MapLegend } from "./MapLegend";
import { loadLayers } from "./data";
import { DIVERGING, RAMPS, fieldValues, gridDomain, gridGeoJSON } from "./mapLayers";
import { routeHref } from "./route";
import { emitTour } from "./tourEvents";
import { metricName } from "./strings";
import type { RegionIndex, RegionLayers } from "./types";

const MapView = lazy(() => import("./MapView").then((m) => ({ default: m.MapView })));

const NO_LAYERS: LayerChoice = { colourBy: null, layerId: null, year: null };

/** Region map with the field list and the map layers (T9.1, T9.11). */
export function MapPage({ index }: { index: RegionIndex }) {
  const [layers, setLayers] = useState<RegionLayers | null>(null);
  const [choice, setChoice] = useState<LayerChoice>(NO_LAYERS);

  useEffect(() => {
    setLayers(null);
    setChoice(NO_LAYERS);
    // Defer layers.json fetch slightly so it doesn't contend with initial map bundle & tiles
    const timer = setTimeout(() => {
      loadLayers(index.region_id)
        .then(setLayers)
        .catch(() => setLayers(null)); // a region without layers.json still shows its fields
    }, 200);
    return () => clearTimeout(timer);
  }, [index.region_id]);

  const colouring = useMemo(() => {
    if (!layers || !choice.colourBy) return null;
    return { values: fieldValues(layers, choice.colourBy), domain: fieldColourDomain(layers, choice.colourBy) };
  }, [layers, choice.colourBy]);

  const grid = useMemo(() => {
    const layer = layers?.layers.find((l) => l.layer_id === choice.layerId);
    if (!layer) return null;
    const years = layer.grid.years;
    const year = choice.year !== null && years.includes(choice.year) ? choice.year : years[years.length - 1];
    return {
      data: gridGeoJSON(layer, year),
      domain: gridDomain(layer),
      ramp: DIVERGING.has(layer.layer_id) ? RAMPS.diverging : RAMPS.sequential,
    };
  }, [layers, choice.layerId, choice.year]);

  const sample = layers && choice.colourBy ? layers.field_colouring[choice.colourBy] : undefined;

  return (
    <main id="main" tabIndex={-1} className="app-main">
      <aside className="rail">
        {layers ? (
          <LayerPanel layers={layers} choice={choice} set={setChoice} />
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
        <GuidancePanel />
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
          />
        </Suspense>
        <MapLegend />
      </div>
    </main>
  );
}
