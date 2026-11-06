import { useEffect, useMemo, useState } from "react";
import { FieldList } from "./FieldList";
import { type LayerChoice, LayerPanel, fieldColourDomain } from "./LayerPanel";
import { MapView } from "./MapView";
import { loadLayers } from "./data";
import { DIVERGING, RAMPS, fieldValues, gridDomain, gridGeoJSON } from "./mapLayers";
import { routeHref } from "./route";
import { metricName } from "./strings";
import type { RegionIndex, RegionLayers } from "./types";

const NO_LAYERS: LayerChoice = { colourBy: null, layerId: null, year: null };

/** Region map with the field list and the map layers (T9.1, T9.11). */
export function MapPage({ index }: { index: RegionIndex }) {
  const [layers, setLayers] = useState<RegionLayers | null>(null);
  const [choice, setChoice] = useState<LayerChoice>(NO_LAYERS);

  useEffect(() => {
    setLayers(null);
    setChoice(NO_LAYERS);
    loadLayers(index.region_id)
      .then(setLayers)
      .catch(() => setLayers(null)); // a region without layers.json still shows its fields
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
    <main className="app-main">
      <aside className="rail">
        {layers && <LayerPanel layers={layers} choice={choice} set={setChoice} />}
        <FieldList
          index={index}
          selectedId={null}
          values={sample}
          valueLabel={choice.colourBy ? metricName(choice.colourBy) : ""}
        />
      </aside>
      <MapView
        index={index}
        selectedId={null}
        onSelect={(fid) => (window.location.hash = routeHref(index.region_id, fid))}
        colouring={colouring}
        grid={grid}
      />
    </main>
  );
}
