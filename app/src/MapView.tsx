import { useEffect, useMemo, useRef, useState } from "react";
import {
  type AddLayerObject,
  type GeoJSONSource,
  Map as MapLibreMap,
  type MapOptions,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 finds its worker next to its own module; once bundled that file is not there,
// so hand it the bundled worker URL (same origin, cached by the service worker).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { type Domain, RAMPS, rampExpression } from "./mapLayers";
import { t } from "./strings";
import { getMapColours } from "./theme";
import type { RegionIndex } from "./types";
import { useTheme } from "./useTheme";
import { wktToGeometry } from "./wkt";

setWorkerUrl(workerUrl);

/** MapLibre does not re-export the style-spec type; take it from MapOptions. */
type StyleSpecification = Exclude<MapOptions["style"], string | undefined>;

type Bbox = [number, number, number, number];

/** Inline style: background, optional HLS true-colour composite, no third-party tiles or fonts. */
function styleFor(index: RegionIndex, dark: boolean): StyleSpecification {
  const colours = getMapColours(dark);
  const [w, s, e, n] = index.bbox_lonlat;
  const style: StyleSpecification = {
    version: 8,
    sources: {},
    layers: [{ id: "background", type: "background", paint: { "background-color": colours.background } }],
  };
  if (index.basemap) {
    if (index.basemap.includes("{z}") || index.basemap.startsWith("http://") || index.basemap.startsWith("https://")) {
      style.sources.basemap = {
        type: "raster",
        tiles: [index.basemap],
        tileSize: 256,
        minzoom: 10,
        maxzoom: 12,
        bounds: [w, s, e, n],
        attribution: "NASA GIBS / LP DAAC (HLS S30, 2023-07-04)",
      };
      style.layers.push({ id: "basemap", type: "raster", source: "basemap" });
    } else {
      style.sources.basemap = {
        type: "image",
        url: `${import.meta.env.BASE_URL}${index.basemap}`,
        coordinates: [
          [w, n],
          [e, n],
          [e, s],
          [w, s],
        ],
      };
      style.layers.push({ id: "basemap", type: "raster", source: "basemap" });
    }
  }
  return style;
}

function fieldsGeoJSON(index: RegionIndex): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: index.fields.map((f) => ({
      type: "Feature",
      properties: { field_id: f.field_id },
      geometry: wktToGeometry(f.geometry_wkt),
    })),
  };
}

/**
 * One point per field (centre of its bounds). Fields are tiny at region zoom, so a marker
 * gives a visible, clickable target until the outlines are large enough.
 */
function fieldPoints(fields: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: fields.features.map((f) => {
      const geom = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
      const rings = geom.type === "Polygon" ? geom.coordinates : geom.coordinates.flat();
      for (const ring of rings) {
        for (const [x, y] of ring) {
          if (x < w) w = x;
          if (x > e) e = x;
          if (y < s) s = y;
          if (y > n) n = y;
        }
      }
      return {
        type: "Feature",
        properties: f.properties,
        geometry: { type: "Point", coordinates: [(w + e) / 2, (s + n) / 2] },
      };
    }),
  };
}

/** Markers fade out between these zooms while the outlines take over. */
const MARKER_FADE: [number, number] = [11, 13];
type ZoomFade = ["interpolate", ["linear"], ["zoom"], number, number, number, number];
const fadeOut = (): ZoomFade => ["interpolate", ["linear"], ["zoom"], MARKER_FADE[0], 1, MARKER_FADE[1], 0];

function regionGeoJSON([w, s, e, n]: Bbox): GeoJSON.Feature {
  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "LineString",
      coordinates: [
        [w, s],
        [e, s],
        [e, n],
        [w, n],
        [w, s],
      ],
    },
  };
}

function showSelected(m: MapLibreMap, fieldId: string | null): void {
  for (const layer of ["fields-selected", "fields-marker-selected"]) {
    m.setFilter(layer, ["==", ["get", "field_id"], fieldId ?? ""]);
  }
}

interface Props {
  index: RegionIndex;
  selectedId: string | null;
  onSelect: (fieldId: string) => void;
  /** T9.11a: field colouring values (Current option) and their colour domain. */
  colouring?: { values: Record<string, number | null>; domain: Domain } | null;
  /** T9.11b: one year of a regional grid layer, drawn under the fields. */
  grid?: { data: GeoJSON.FeatureCollection; domain: Domain; ramp: readonly string[] } | null;
}

/** MapLibre does not re-export its expression types either; take the colour type from a fill layer. */
type ColourValue = NonNullable<NonNullable<Extract<AddLayerObject, { type: "fill" }>["paint"]>["fill-color"]>;

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const NO_VALUE = "#9aa3a0"; // field or cell without a value: neutral grey, also named in the legend

/** Copy of a field collection with the colouring value as property `cv`. */
function withValues(fc: GeoJSON.FeatureCollection, values: Record<string, number | null> | undefined) {
  return {
    ...fc,
    features: fc.features.map((f) => ({
      ...f,
      properties: { ...f.properties, cv: values?.[f.properties?.field_id as string] ?? null },
    })),
  };
}

export function MapView({ index, selectedId, onSelect, colouring = null, grid = null }: Props) {
  const { effective } = useTheme();
  const dark = effective === "dark";
  const colours = getMapColours(dark);
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;
  const fields = useMemo(() => fieldsGeoJSON(index), [index]);

  // One map per region index.
  useEffect(() => {
    const m = new MapLibreMap({
      container: container.current!,
      style: styleFor(index, dark),
      bounds: index.bbox_lonlat,
      fadeDuration: 0,
      renderWorldCopies: false,
      // extra bottom padding keeps fields clear of the attribution label
      fitBoundsOptions: { padding: { top: 48, right: 64, bottom: 72, left: 48 }, maxZoom: 14 },
      attributionControl: {
        compact: true,
        customAttribution: index.basemap ? t("map.attribution.hls") : t("map.attribution.none"),
      },
    });
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    m.on("error", (e) => {
      // Gracefully handle tile loading errors (e.g. offline fallback to neutral background)
      const srcId = (e as unknown as { sourceId?: string })?.sourceId;
      if (e?.error?.message?.includes("tile") || srcId === "basemap") {
        return;
      }
    });
    m.on("load", () => {
      m.addSource("region", { type: "geojson", data: regionGeoJSON(index.bbox_lonlat) });
      m.addSource("fields", { type: "geojson", data: fields });
      // Regional grid (T9.11b) sits under the region outline and the fields.
      m.addSource("grid", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "grid-fill",
        type: "fill",
        source: "grid",
        layout: { visibility: "none" },
        paint: { "fill-color": NO_VALUE, "fill-opacity": 0.6, "fill-outline-color": colours.regionLine },
      });
      m.addLayer({
        id: "region-outline",
        type: "line",
        source: "region",
        paint: { "line-color": colours.regionLine, "line-width": 1, "line-dasharray": [4, 3] },
      });
      m.addLayer({
        id: "fields-fill",
        type: "fill",
        source: "fields",
        paint: { "fill-color": colours.fieldFill, "fill-opacity": 0.55 },
      });
      m.addLayer({
        id: "fields-line",
        type: "line",
        source: "fields",
        paint: { "line-color": colours.fieldLine, "line-width": 1.5 },
      });
      m.addLayer({
        id: "fields-selected",
        type: "line",
        source: "fields",
        filter: ["==", ["get", "field_id"], ""],
        paint: { "line-color": colours.selected, "line-width": 4 },
      });
      m.addSource("field-points", { type: "geojson", data: fieldPoints(fields) });
      m.addLayer({
        id: "fields-marker",
        type: "circle",
        source: "field-points",
        maxzoom: MARKER_FADE[1],
        paint: {
          "circle-radius": 7,
          "circle-color": colours.fieldFill,
          "circle-stroke-color": colours.fieldLine,
          "circle-stroke-width": 1.5,
          "circle-opacity": fadeOut(),
          "circle-stroke-opacity": fadeOut(),
        },
      });
      m.addLayer({
        id: "fields-marker-selected",
        type: "circle",
        source: "field-points",
        maxzoom: MARKER_FADE[1],
        filter: ["==", ["get", "field_id"], ""],
        paint: {
          "circle-radius": 9,
          "circle-color": colours.fieldFill,
          "circle-stroke-color": colours.selected,
          "circle-stroke-width": 3,
          "circle-opacity": fadeOut(),
          "circle-stroke-opacity": fadeOut(),
        },
      });
      for (const layer of ["fields-fill", "fields-marker"]) {
        m.on("click", layer, (e) => {
          const id = e.features?.[0]?.properties?.field_id;
          if (typeof id === "string") onSelectRef.current(id);
        });
        m.on("mouseenter", layer, () => (m.getCanvas().style.cursor = "pointer"));
        m.on("mouseleave", layer, () => (m.getCanvas().style.cursor = ""));
      }
      map.current = m;
      // Marker for the screenshot driver: fields are drawn once the map first goes idle.
      m.once("idle", () => container.current?.setAttribute("data-state", "ready"));
      showSelected(m, selectedIdRef.current);
      setReady(true);
    });
    return () => {
      map.current = null;
      setReady(false);
      m.remove();
    };
  }, [index, fields]);

  // Update paint properties live when theme toggles.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    try {
      m.setPaintProperty("background", "background-color", colours.background);
      m.setPaintProperty("region-outline", "line-color", colours.regionLine);
      m.setPaintProperty("fields-line", "line-color", colours.fieldLine);
      m.setPaintProperty("fields-selected", "line-color", colours.selected);
      m.setPaintProperty("fields-marker-selected", "circle-stroke-color", colours.selected);
      if (!colouring) {
        m.setPaintProperty("fields-fill", "fill-color", colours.fieldFill);
        m.setPaintProperty("fields-marker", "circle-color", colours.fieldFill);
        m.setPaintProperty("fields-marker", "circle-stroke-color", colours.fieldLine);
      }
    } catch {
      // ignore during transitions
    }
  }, [ready, dark, colouring, colours]);

  useEffect(() => {
    if (map.current) showSelected(map.current, selectedId);
  }, [selectedId]);

  // T9.11a: colour fields (fill and markers) by a Current-option value; no colouring = default.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    const coloured = withValues(fields, colouring?.values);
    (m.getSource("fields") as GeoJSONSource).setData(coloured);
    (m.getSource("field-points") as GeoJSONSource).setData(fieldPoints(coloured));
    const colour = (
      colouring ? rampExpression("cv", colouring.domain, RAMPS.sequential, NO_VALUE) : colours.fieldFill
    ) as ColourValue;
    m.setPaintProperty("fields-fill", "fill-color", colour);
    m.setPaintProperty("fields-fill", "fill-opacity", colouring ? 0.85 : 0.55);
    m.setPaintProperty("fields-marker", "circle-color", colour);
    m.setPaintProperty("fields-marker-selected", "circle-color", colour);
  }, [ready, fields, colouring]);

  // T9.11b: one year of a regional layer.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    (m.getSource("grid") as GeoJSONSource).setData(grid?.data ?? EMPTY);
    m.setLayoutProperty("grid-fill", "visibility", grid ? "visible" : "none");
    if (grid) {
      m.setPaintProperty("grid-fill", "fill-color", rampExpression("v", grid.domain, grid.ramp, NO_VALUE) as ColourValue);
    }
  }, [ready, grid]);

  return <div ref={container} className="map" role="region" aria-label={t("map.label")} />;
}
