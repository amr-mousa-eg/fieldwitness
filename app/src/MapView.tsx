import { useEffect, useMemo, useRef } from "react";
import { Map as MapLibreMap, type MapOptions, NavigationControl, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 finds its worker next to its own module; once bundled that file is not there,
// so hand it the bundled worker URL (same origin, cached by the service worker).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { t } from "./strings";
import type { RegionIndex } from "./types";
import { boundsOf, wktToGeometry } from "./wkt";

setWorkerUrl(workerUrl);

/** MapLibre does not re-export the style-spec type; take it from MapOptions. */
type StyleSpecification = Exclude<MapOptions["style"], string | undefined>;

// Read once when the module loads; a theme change takes effect on the next page load.
const DARK = window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
const COLOURS = {
  background: DARK ? "#3b3d36" : "#d8d6cc", // neutral fallback when no HLS composite exists (T9.1)
  regionLine: DARK ? "#8f8c7c" : "#7d7a6c",
  fieldFill: "#c9a43a",
  fieldLine: "#5b4813",
  selected: DARK ? "#e4ebe8" : "#22313a", // matches --ink
};

type Bbox = [number, number, number, number];

/** Inline style: background, optional HLS true-colour composite, no third-party tiles or fonts. */
function styleFor(index: RegionIndex): StyleSpecification {
  const [w, s, e, n] = index.bbox_lonlat;
  const style: StyleSpecification = {
    version: 8,
    sources: {},
    layers: [{ id: "background", type: "background", paint: { "background-color": COLOURS.background } }],
  };
  if (index.basemap) {
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
      const [w, s, e, n] = boundsOf([f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon]);
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
}

export function MapView({ index, selectedId, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;
  const fields = useMemo(() => fieldsGeoJSON(index), [index]);

  // One map per region index.
  useEffect(() => {
    const fieldBounds = boundsOf(
      fields.features.map((f) => f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon),
    );
    const m = new MapLibreMap({
      container: container.current!,
      style: styleFor(index),
      bounds: fieldBounds,
      // extra bottom padding keeps fields clear of the attribution label
      fitBoundsOptions: { padding: { top: 48, right: 64, bottom: 72, left: 48 }, maxZoom: 14 },
      attributionControl: {
        compact: true,
        customAttribution: index.basemap ? t("map.attribution.hls") : t("map.attribution.none"),
      },
    });
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("region", { type: "geojson", data: regionGeoJSON(index.bbox_lonlat) });
      m.addSource("fields", { type: "geojson", data: fields });
      m.addLayer({
        id: "region-outline",
        type: "line",
        source: "region",
        paint: { "line-color": COLOURS.regionLine, "line-width": 1, "line-dasharray": [4, 3] },
      });
      m.addLayer({
        id: "fields-fill",
        type: "fill",
        source: "fields",
        paint: { "fill-color": COLOURS.fieldFill, "fill-opacity": 0.55 },
      });
      m.addLayer({
        id: "fields-line",
        type: "line",
        source: "fields",
        paint: { "line-color": COLOURS.fieldLine, "line-width": 1.5 },
      });
      m.addLayer({
        id: "fields-selected",
        type: "line",
        source: "fields",
        filter: ["==", ["get", "field_id"], ""],
        paint: { "line-color": COLOURS.selected, "line-width": 4 },
      });
      m.addSource("field-points", { type: "geojson", data: fieldPoints(fields) });
      m.addLayer({
        id: "fields-marker",
        type: "circle",
        source: "field-points",
        maxzoom: MARKER_FADE[1],
        paint: {
          "circle-radius": 7,
          "circle-color": COLOURS.fieldFill,
          "circle-stroke-color": COLOURS.fieldLine,
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
          "circle-color": COLOURS.fieldFill,
          "circle-stroke-color": COLOURS.selected,
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
    });
    return () => {
      map.current = null;
      m.remove();
    };
  }, [index, fields]);

  useEffect(() => {
    if (map.current) showSelected(map.current, selectedId);
  }, [selectedId]);

  return <div ref={container} className="map" role="region" aria-label={t("map.label")} />;
}
