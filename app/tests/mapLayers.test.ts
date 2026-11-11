import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  BASEMAP_HANDOVER_ZOOM,
  COLOUR_METRICS,
  GIBS_BACKDROP_URL,
  domainOf,
  fieldValues,
  gridDomain,
  gridGeoJSON,
  rampExpression,
} from "../src/mapLayers";
import type { RegionIndex, RegionLayers } from "../src/types";

const DIR = join(import.meta.dirname, "../fixtures/ks_demo_synthetic");
const layers = JSON.parse(readFileSync(join(DIR, "layers.SYNTHETIC.json"), "utf8")) as RegionLayers;
const index = JSON.parse(readFileSync(join(DIR, "index.SYNTHETIC.json"), "utf8")) as RegionIndex;

describe("map layers (T9.11)", () => {
  it("domains: min-max, centred on zero for anomalies, safe when flat or empty", () => {
    expect(domainOf([3, null, 1, 2])).toEqual([1, 3]);
    expect(domainOf([-0.2, 0.5], true)).toEqual([-0.5, 0.5]);
    expect(domainOf([2, 2])).toEqual([2, 3]);
    expect(domainOf([null, undefined])).toEqual([0, 1]);
    expect(domainOf([0, 0], true)).toEqual([-1, 1]);
  });

  it("colours every field of the index for each metric", () => {
    for (const m of COLOUR_METRICS) {
      const v = fieldValues(layers, m);
      for (const f of index.fields) expect(f.field_id in v, `${m} ${f.field_id}`).toBe(true);
    }
  });

  it("grid: one closed polygon per cell, values of the chosen year, domain over all years", () => {
    for (const l of layers.layers) {
      const y = l.grid.years[2];
      const fc = gridGeoJSON(l, y);
      expect(fc.features).toHaveLength(l.grid.cells.length);
      fc.features.forEach((f, i) => {
        const ring = (f.geometry as GeoJSON.Polygon).coordinates[0];
        expect(ring[0]).toEqual(ring[4]);
        expect(f.properties?.v).toBe(l.grid.cells[i].values[2]);
      });
      const [lo, hi] = gridDomain(l);
      for (const c of l.grid.cells) for (const v of c.values) if (v !== null) expect(v >= lo && v <= hi).toBe(true);
      expect(gridGeoJSON(l, 1900).features.every((f) => f.properties?.v === null)).toBe(true);
    }
  });

  it("ramp expression maps the domain ends to the ramp ends", () => {
    const e = rampExpression("v", [0, 10], ["#000", "#888", "#fff"], "#f00") as unknown[];
    expect(e[2]).toBe("#f00");
    expect(e[3]).toEqual(["interpolate", ["linear"], ["get", "v"], 0, "#000", 5, "#888", 10, "#fff"]);
  });
});

describe("low-zoom NASA backdrop (MODIS) hands over to HLS at zoom 10", () => {
  const mapView = readFileSync(join(import.meta.dirname, "../src/MapView.tsx"), "utf8");

  it("uses the GIBS MODIS Terra true-colour Level9 template with a fixed date", () => {
    expect(GIBS_BACKDROP_URL).toBe(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2023-08-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpeg",
    );
    // credit line names GIBS (acknowledgement asked by the GIBS API docs) and both layers with dates
    const credit = JSON.parse(readFileSync(join(import.meta.dirname, "../src/strings/en.json"), "utf8"))["map.attribution.hls"];
    for (const s of ["NASA GIBS", "MODIS Terra", "2023-08-15", "HLS", "2023-07-04"]) expect(credit).toContain(s);
    expect(BASEMAP_HANDOVER_ZOOM).toBe(10);
  });

  it("backdrop layer stops and HLS source starts at the handover zoom; backdrop draws first", () => {
    expect(mapView).toContain('{ id: "backdrop", type: "raster", source: "backdrop", maxzoom: BASEMAP_HANDOVER_ZOOM }');
    expect(mapView).toMatch(/minzoom: BASEMAP_HANDOVER_ZOOM,\s*maxzoom: 12/);
    expect(mapView.indexOf('id: "backdrop"')).toBeLessThan(mapView.indexOf('{ id: "basemap"'));
  });
});
