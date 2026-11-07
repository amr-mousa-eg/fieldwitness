import type { FieldColourMetric, RegionLayers, RegionalLayer } from "./types";

export const COLOUR_METRICS: FieldColourMetric[] = ["erosion_exposure", "water_stress_share", "frost_share"];

/** Anomalies are centred on 0 (diverging scale); counts start at their minimum (sequential). */
export const DIVERGING = new Set<RegionalLayer["layer_id"]>(["grace_tws", "smap_anomaly"]);

/** Low-to-high ramps. Diverging: dry/negative brown, 0 near white, wet/positive blue. */
export const RAMPS = {
  sequential: ["#fbeee0", "#f2c49b", "#e08f5a", "#bf5b2c", "#8a3412"],
  diverging: ["#8c510a", "#d8b365", "#f5f5f5", "#5ab4ac", "#01665e"],
} as const;

export type Domain = [number, number];

/** Min and max of the non-null values; a flat or empty set gets a unit-wide domain. */
export function domainOf(values: (number | null | undefined)[], centreOnZero = false): Domain {
  const v = values.filter((x): x is number => typeof x === "number" && Number.isFinite(x));
  if (v.length === 0) return [0, 1];
  if (centreOnZero) {
    const m = Math.max(...v.map(Math.abs));
    return m === 0 ? [-1, 1] : [-m, m];
  }
  const lo = Math.min(...v);
  const hi = Math.max(...v);
  return lo === hi ? [lo, lo + 1] : [lo, hi];
}

/** Field id -> colouring value (Current option, Q5); null when the field has no value. */
export function fieldValues(layers: RegionLayers, metric: FieldColourMetric): Record<string, number | null> {
  const src = layers.field_colouring[metric] ?? {};
  return Object.fromEntries(Object.entries(src).map(([fid, v]) => [fid, v.value]));
}

/**
 * One polygon per grid cell with `v` = the value for `year`. The colour domain is taken over
 * all years, so the colours of different years can be compared.
 */
export function gridGeoJSON(layer: RegionalLayer, year: number): GeoJSON.FeatureCollection {
  const i = layer.grid.years.indexOf(year);
  return {
    type: "FeatureCollection",
    features: layer.grid.cells.map((c) => {
      const [w, s, e, n] = c.bbox_lonlat;
      return {
        type: "Feature",
        properties: { v: i < 0 ? null : (c.values[i] ?? null) },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [w, s],
              [e, s],
              [e, n],
              [w, n],
              [w, s],
            ],
          ],
        },
      };
    }),
  };
}

export function gridDomain(layer: RegionalLayer): Domain {
  return domainOf(
    layer.grid.cells.flatMap((c) => c.values),
    DIVERGING.has(layer.layer_id),
  );
}

/** MapLibre colour expression for property `prop` over `domain`; `fallback` when null. */
export function rampExpression(prop: string, [lo, hi]: Domain, ramp: readonly string[], fallback: string): unknown[] {
  const stops = ramp.flatMap((c, k) => [lo + ((hi - lo) * k) / (ramp.length - 1), c]);
  return ["case", ["==", ["get", prop], null], fallback, ["interpolate", ["linear"], ["get", prop], ...stops]];
}
