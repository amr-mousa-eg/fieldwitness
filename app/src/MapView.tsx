import { useEffect, useMemo, useRef, useState } from "react";
import {
  type AddLayerObject,
  type GeoJSONSource,
  Map as MapLibreMap,
  type MapOptions,
  NavigationControl,
  type RasterTileSource,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 finds its worker next to its own module; once bundled that file is not there,
// so hand it the bundled worker URL (same origin, cached by the service worker).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { formatNumber } from "./format";
import { getFieldNumberMap } from "./fields";
import {
  BACKDROP_OPTIONS,
  BASEMAP_HANDOVER_ZOOM,
  type BackdropId,
  type Domain,
  GIBS_BACKDROP_URL,
  RAMPS,
  rampExpression,
} from "./mapLayers";
import type { FieldOptionDelta } from "./optionDeltas";
import { cropName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import { getMapColours } from "./theme";
import type { RegionIndex, Tag, Tagged } from "./types";
import { useTheme } from "./useTheme";
import { wktToGeometry } from "./wkt";

setWorkerUrl(workerUrl);

/** MapLibre does not re-export the style-spec type; take it from MapOptions. */
type StyleSpecification = Exclude<MapOptions["style"], string | undefined>;

type Bbox = [number, number, number, number];

/** Inline style: background, optional NASA imagery (MODIS backdrop + HLS 30 m), no third-party tiles or fonts. */
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
      // One credit line for both layers: customAttribution (map.attribution.hls).
      // Coarse NASA backdrop below zoom 10, where the 30 m HLS layer has no tiles. If it fails
      // (offline), the neutral background shows through, as before.
      style.sources.backdrop = {
        type: "raster",
        tiles: [GIBS_BACKDROP_URL],
        tileSize: 256,
        maxzoom: 9,
      };
      style.layers.push({ id: "backdrop", type: "raster", source: "backdrop", maxzoom: BASEMAP_HANDOVER_ZOOM });
      style.sources.basemap = {
        type: "raster",
        tiles: [index.basemap],
        tileSize: 256,
        minzoom: BASEMAP_HANDOVER_ZOOM,
        maxzoom: 12,
        bounds: [w, s, e, n],
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

export interface MapHudInfo {
  activeLabel?: string;
  tagged?: Record<string, Tagged>;
  deltas?: Record<string, FieldOptionDelta>;
  gridLabel?: string;
  gridYear?: number;
  gridUnit?: string;
  gridTag?: Tag;
  gridSource?: string;
}

interface Props {
  index: RegionIndex;
  selectedId: string | null;
  onSelect: (fieldId: string) => void;
  /** T9.11a & S7: field colouring values (Current or Rank-1 delta), colour domain, and optional ramp. */
  colouring?: { values: Record<string, number | null>; domain: Domain; ramp?: readonly string[] } | null;
  /** T9.11b: one year of a regional grid layer, drawn under the fields. */
  grid?: { data: GeoJSON.FeatureCollection; domain: Domain; ramp: readonly string[] } | null;
  /** Phase P3: active NASA GIBS backdrop / overlay selection. */
  backdropId?: BackdropId;
  /** Phase P3: telemetry metadata for interactive field & grid hover HUD. */
  hudInfo?: MapHudInfo | null;
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

const fieldsCache = new Map<string, GeoJSON.FeatureCollection>();
function getCachedFields(index: RegionIndex): GeoJSON.FeatureCollection {
  let fc = fieldsCache.get(index.region_id);
  if (!fc) {
    fc = fieldsGeoJSON(index);
    fieldsCache.set(index.region_id, fc);
  }
  return fc;
}

const pointsCache = new Map<string, GeoJSON.FeatureCollection>();
function getCachedPoints(index: RegionIndex, fields: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  let pts = pointsCache.get(index.region_id);
  if (!pts) {
    pts = fieldPoints(fields);
    pointsCache.set(index.region_id, pts);
  }
  return pts;
}

export function mapAttributionText(basemap: string | null | undefined): string {
  const hlsDate = basemap?.match(/\/default\/(\d{4}-\d{2}-\d{2})\//)?.[1];
  return basemap
    ? hlsDate
      ? t("map.attribution.hls.date", { date: hlsDate })
      : t("map.attribution.hls")
    : t("map.attribution.none");
}

export function MapView({
  index,
  selectedId,
  onSelect,
  colouring = null,
  grid = null,
  backdropId = "modis",
  hudInfo = null,
}: Props) {
  const { effective } = useTheme();
  const dark = effective === "dark";
  const colours = getMapColours(dark);
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);
  const [hoveredGridVal, setHoveredGridVal] = useState<number | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;
  const fields = useMemo(() => getCachedFields(index), [index]);
  const fieldNumberMap = useMemo(() => getFieldNumberMap(index.fields), [index.fields]);

  // One map per region index.
  useEffect(() => {
    let m: MapLibreMap | null = null;
    let cancelled = false;
    setHoveredFieldId(null);
    setHoveredGridVal(null);

    const rafId = requestAnimationFrame(() => {
      if (cancelled || !container.current) return;
      const attributionText = mapAttributionText(index.basemap);
      m = new MapLibreMap({
        container: container.current,
        style: styleFor(index, dark),
        bounds: index.bbox_lonlat,
        fadeDuration: 0,
        renderWorldCopies: false,
        // extra bottom padding keeps fields clear of the attribution label
        fitBoundsOptions: { padding: { top: 48, right: 64, bottom: 72, left: 48 }, maxZoom: 14 },
        attributionControl: {
          compact: true,
          customAttribution: attributionText,
        },
      });
      m.addControl(new NavigationControl({ showCompass: false }), "top-right");
      m.on("error", (e) => {
        // Gracefully handle tile loading errors (e.g. offline fallback to neutral background)
        const srcId = (e as unknown as { sourceId?: string })?.sourceId;
        if (e?.error?.message?.includes("tile") || srcId === "basemap" || srcId === "backdrop" || srcId === "gibs-overlay-src") {
          return;
        }
      });
      m.on("load", () => {
        if (cancelled) return;
        m!.addSource("region", { type: "geojson", data: regionGeoJSON(index.bbox_lonlat) });
        m!.addSource("fields", { type: "geojson", data: fields });
        m!.addLayer({
          id: "region-outline",
          type: "line",
          source: "region",
          paint: { "line-color": colours.regionLine, "line-width": 1, "line-dasharray": [4, 3] },
        });
        m!.addLayer({
          id: "fields-fill",
          type: "fill",
          source: "fields",
          paint: { "fill-color": colours.fieldFill, "fill-opacity": 0.55 },
        });
        m!.addLayer({
          id: "fields-line",
          type: "line",
          source: "fields",
          paint: { "line-color": colours.fieldLine, "line-width": 1.5 },
        });
        m!.addLayer({
          id: "fields-selected",
          type: "line",
          source: "fields",
          filter: ["==", ["get", "field_id"], ""],
          paint: { "line-color": colours.selected, "line-width": 4 },
        });

        map.current = m;

        // Yield remaining layer compilation and interaction setup to keep main thread unblocked
        requestAnimationFrame(() => {
          if (cancelled || !map.current) return;
          // Regional grid (T9.11b) sits under the region outline and the fields.
          m!.addSource("grid", { type: "geojson", data: EMPTY });
          m!.addLayer(
            {
              id: "grid-fill",
              type: "fill",
              source: "grid",
              layout: { visibility: "none" },
              paint: { "fill-color": NO_VALUE, "fill-opacity": 0.6, "fill-outline-color": colours.regionLine },
            },
            "region-outline",
          );
          m!.addSource("field-points", { type: "geojson", data: getCachedPoints(index, fields) });
          m!.addLayer({
            id: "fields-marker",
            type: "circle",
            source: "field-points",
            maxzoom: MARKER_FADE[1],
            paint: {
              "circle-radius": 7,
              "circle-color": colours.fieldFill,
              "circle-stroke-color": colours.markerLine,
              "circle-stroke-width": 2,
              "circle-opacity": fadeOut(),
              "circle-stroke-opacity": fadeOut(),
            },
          });
          m!.addLayer({
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
            m!.on("click", layer, (e) => {
              const id = e.features?.[0]?.properties?.field_id;
              if (typeof id === "string") onSelectRef.current(id);
            });
            m!.on("mousemove", layer, (e) => {
              m!.getCanvas().style.cursor = "pointer";
              const id = e.features?.[0]?.properties?.field_id;
              if (typeof id === "string") setHoveredFieldId(id);
            });
            m!.on("mouseleave", layer, () => {
              m!.getCanvas().style.cursor = "";
              setHoveredFieldId(null);
            });
          }
          m!.on("mousemove", "grid-fill", (e) => {
            const v = e.features?.[0]?.properties?.v;
            setHoveredGridVal(typeof v === "number" && Number.isFinite(v) ? v : null);
          });
          m!.on("mouseleave", "grid-fill", () => {
            setHoveredGridVal(null);
          });
          showSelected(m!, selectedIdRef.current);
          setReady(true);
        });

        // Marker for the screenshot driver: fields are drawn once the map first goes idle.
        m!.once("idle", () => container.current?.setAttribute("data-state", "ready"));
      });
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      map.current = null;
      setReady(false);
      m?.remove();
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
        m.setPaintProperty("fields-marker", "circle-stroke-color", colours.markerLine);
      }
    } catch {
      // ignore during transitions
    }
  }, [ready, dark, colouring, colours]);

  useEffect(() => {
    if (map.current) showSelected(map.current, selectedId);
  }, [selectedId]);

  // T9.11a & S7: colour fields (fill and markers) by a Current-option value or Rank-1 delta; no colouring = default.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    const coloured = withValues(fields, colouring?.values);
    (m.getSource("fields") as GeoJSONSource).setData(coloured);
    (m.getSource("field-points") as GeoJSONSource).setData(fieldPoints(coloured));
    const ramp = colouring?.ramp ?? RAMPS.sequential;
    const colour = (
      colouring ? rampExpression("cv", colouring.domain, ramp, NO_VALUE) : colours.fieldFill
    ) as ColourValue;
    m.setPaintProperty("fields-fill", "fill-color", colour);
    m.setPaintProperty("fields-fill", "fill-opacity", colouring ? 0.85 : 0.55);
    m.setPaintProperty("fields-marker", "circle-color", colour);
    m.setPaintProperty("fields-marker-selected", "circle-color", colour);
  }, [ready, fields, colouring, colours]);

  // T9.11b: one year of a regional layer.
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    (m.getSource("grid") as GeoJSONSource).setData(grid?.data ?? EMPTY);
    m.setLayoutProperty("grid-fill", "visibility", grid ? "visible" : "none");
    if (grid) {
      m.setPaintProperty("grid-fill", "fill-color", rampExpression("v", grid.domain, grid.ramp, NO_VALUE) as ColourValue);
    } else {
      setHoveredGridVal(null);
    }
  }, [ready, grid]);

  // Phase P3: NASA GIBS imagery backdrop / overlay switcher (MODIS, VIIRS, GPM IMERG, SRTM).
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    const opt = BACKDROP_OPTIONS.find((o) => o.id === backdropId) ?? BACKDROP_OPTIONS[0];
    try {
      const backdropSrc = m.getSource("backdrop") as RasterTileSource | undefined;
      if (opt.overlayOnly) {
        if (backdropSrc?.setTiles) backdropSrc.setTiles([GIBS_BACKDROP_URL]);
        const overlaySrc = m.getSource("gibs-overlay-src") as RasterTileSource | undefined;
        if (overlaySrc) {
          overlaySrc.setTiles?.([opt.url]);
          if (m.getLayer("gibs-overlay")) m.setLayoutProperty("gibs-overlay", "visibility", "visible");
        } else {
          m.addSource("gibs-overlay-src", {
            type: "raster",
            tiles: [opt.url],
            tileSize: 256,
            maxzoom: opt.maxzoom,
          });
          m.addLayer(
            {
              id: "gibs-overlay",
              type: "raster",
              source: "gibs-overlay-src",
              paint: { "raster-opacity": 0.55 },
            },
            "grid-fill",
          );
        }
      } else {
        if (backdropSrc?.setTiles) backdropSrc.setTiles([opt.url]);
        if (m.getLayer("gibs-overlay")) m.setLayoutProperty("gibs-overlay", "visibility", "none");
      }
    } catch {
      // ignore if map is unmounting or region uses static imagery only
    }
  }, [ready, backdropId, index.basemap]);

  const hoveredSummary = hoveredFieldId ? index.fields.find((f) => f.field_id === hoveredFieldId) : undefined;
  const hoveredNum = hoveredFieldId ? fieldNumberMap.get(hoveredFieldId) : undefined;
  const hoveredDelta = hoveredFieldId ? hudInfo?.deltas?.[hoveredFieldId] : undefined;
  const hoveredTagged = hoveredFieldId ? hudInfo?.tagged?.[hoveredFieldId] : undefined;
  const showHud = Boolean(hoveredSummary || (hoveredGridVal !== null && hudInfo?.gridLabel));

  return (
    <div className="map-stage">
      <div ref={container} className="map" role="region" aria-label={t("map.label")} />
      {showHud && (
        <div className="map-hover-hud" role="status" aria-live="polite">
          {hoveredSummary && (
            <div className="map-hud-field">
              <div className="map-hud-title">
                <strong>{t("field.label", { num: hoveredNum ?? 1 })}</strong>{" "}
                <span className={`grade grade-${hoveredSummary.top_grade}`}>{hoveredSummary.top_grade}</span>{" "}
                <span className="muted">({t("fields.area", { area: hoveredSummary.area_ha })})</span>
              </div>
              {hudInfo?.activeLabel && hoveredTagged && (
                <div className="map-hud-metric">
                  <span>{hudInfo.activeLabel}:</span> <TaggedValue v={hoveredTagged} />
                </div>
              )}
              {hoveredDelta && (
                <div className="map-hud-seq">
                  <span className="muted">{t("map.hud.currentVsAlt")}</span>{" "}
                  <span>
                    {hoveredDelta.current_sequence.map((c) => cropName(c)).join(" → ")} ({hoveredDelta.current_grade}) →{" "}
                    <strong>
                      {hoveredDelta.alt_sequence.map((c) => cropName(c)).join(" → ")} ({hoveredDelta.alt_grade})
                    </strong>
                  </span>
                </div>
              )}
              <div className="map-hud-hint muted">{t("map.hud.clickToOpen")}</div>
            </div>
          )}
          {hoveredGridVal !== null && hudInfo?.gridLabel && (
            <div className="map-hud-grid">
              <span className="muted">{t("map.hud.gridCell")}</span>{" "}
              <strong>
                {hudInfo.gridLabel}
                {hudInfo.gridYear !== undefined ? ` (${hudInfo.gridYear})` : ""}:
              </strong>{" "}
              <span>
                {formatNumber(hoveredGridVal, hudInfo.gridUnit ?? "")}
                {hudInfo.gridUnit ? ` ${hudInfo.gridUnit}` : ""}
              </span>{" "}
              {hudInfo.gridTag && <TagBadge tag={hudInfo.gridTag} source={hudInfo.gridSource} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
