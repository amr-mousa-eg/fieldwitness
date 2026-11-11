import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./Field3DView.css";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Field3DScene, type FrameStats } from "./Field3DScene";
import { bt } from "./builder/strings";
import { FarmScene } from "./FarmScene";
import { builderEnabled, builderOpenAtStart, farmEnabled } from "./featureFlags";
import { weekTelemetry } from "./field3d/farm";
import { FARM_TEXT } from "./field3d/farmText";
import { MIN_MEDIAN_FPS, type QualityTier, historyOnlyKey, pickQuality } from "./field3d/growth";
import { isHistoryOnly } from "./seasons";
import { Explain } from "./Explain";
import { SIM3D_EXPLAINERS, explainer } from "./explainers";
import { loadSim3D } from "./data";
import { cropName, t } from "./strings";
import { TagBadge } from "./tags";
import { CHART_COLOURS } from "./theme";
import type { FieldPack, FieldSim3D, Sim3DOption, Sim3DScenario } from "./types";
import { emitTour } from "./tourEvents";
import { useTheme } from "./useTheme";

// Lazy: the builder (and its physics port) loads only when the feature flag is on.
const RotationBuilder = lazy(() => import("./builder/RotationBuilder"));

function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

const SCENARIO_LABELS: Record<string, string> = {
  "t+0_p+0": "Median weather (+0°C, 0% rain)",
  "t+0_p-20": "Dry year (+0°C, -20% rain)",
  "t+0_p-10": "Moderately dry (+0°C, -10% rain)",
  "t+0_p+10": "Wet year (+0°C, +10% rain)",
  "t+1_p+0": "Warming +1°C (0% rain)",
  "t+1_p-20": "Hot & dry (+1°C, -20% rain)",
  "t+1_p-10": "Hot & moderate dry (+1°C, -10% rain)",
  "t+1_p+10": "Hot & wet (+1°C, +10% rain)",
  "t+2_p+0": "Warming +2°C (0% rain)",
  "t+2_p-20": "Severe heat & drought (+2°C, -20% rain)",
  "t+2_p-10": "Heat & dry (+2°C, -10% rain)",
  "t+2_p+10": "Heat & high rain (+2°C, +10% rain)",
};

interface HoverMetric {
  week: number;
  crop: string;
  stage: string;
  soilWater: number;
  taw: number;
  canopyCover: number;
  ks: number;
  rain: number;
  irrigation: number;
  rootDepth: number;
  /** History-only season key (e.g. perennial_forage) owning this week: nothing is simulated. */
  historyOnly: string | null;
  /** Cover-crop week (farm view mapping, `field3d/farm.ts`); the glass view does not set it. */
  cover?: boolean;
}

/** Weekly telemetry under one 3D scene. History-only weeks show "not simulated", never values. */
function MetricStrip({ m, source }: { m: HoverMetric | null; source: string }) {
  const hist = m?.historyOnly ?? null;
  const ns = <span className="muted">{t("season.notSimulated")}</span>;
  const d = <TagBadge tag="D" source={source} />;
  return (
    <div className="sim3d-metric-strip">
      <div
        className="sim3d-metric-item"
        title="Crop type and phenological growth stage from FAO-56 dual crop coefficient model [D]"
        data-tooltip="Crop type and phenological growth stage from FAO-56 dual crop coefficient model [D]"
      >
        <span className="sim3d-metric-label">
          Crop & Stage {!hist && !m?.cover && m?.crop === "fallow" && <Explain id="fallow_bare_soil" />}
        </span>
        <span className="sim3d-metric-val">
          {hist ? (
            t("season.historyOnly", { crop: cropName(hist) })
          ) : m?.crop === "fallow" ? (
            m.cover ? (
              <>
                cover crop {d}
              </>
            ) : (
              "Bare fallow [D]"
            )
          ) : (
            <>
              {m?.crop.replace(/_/g, " ")} ({m?.stage}) {d}
            </>
          )}
        </span>
      </div>
      <div
        className="sim3d-metric-item"
        title="Root-zone soil water / total available water capacity in root zone (mm) [D]"
        data-tooltip="Root-zone soil water / total available water capacity in root zone (mm) [D]"
      >
        <span className="sim3d-metric-label">
          Available Soil Water <Explain id="root_zone_soil_water" /> <Explain id="available_water_capacity" />
        </span>
        <span className="sim3d-metric-val">
          {hist ? ns : (
            <>
              <strong>{m?.soilWater.toFixed(1)}</strong> of {m?.taw.toFixed(0)} mm {d}
            </>
          )}
        </span>
      </div>
      <div
        className="sim3d-metric-item"
        title="Canopy proxy (Kc / Kc max) from FAO-56 dual crop coefficient model (0.00–1.00) [D]"
        data-tooltip="Canopy proxy (Kc / Kc max) from FAO-56 dual crop coefficient model (0.00–1.00) [D]"
      >
        <span className="sim3d-metric-label">
          Canopy Proxy (Kc/Kc max) <Explain id="canopy_proxy" />
        </span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.canopyCover.toFixed(2)} {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title="FAO-56 water stress coefficient (0.00 = severe stress, 1.00 = no stress) [D]"
        data-tooltip="FAO-56 water stress coefficient (0.00 = severe stress, 1.00 = no stress) [D]"
      >
        <span className="sim3d-metric-label">
          Water Stress (Ks) <Explain id="water_stress_ks" />
        </span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.ks.toFixed(2)} {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title="Effective root-zone depth (m) [D]"
        data-tooltip="Effective root-zone depth (m) [D]"
      >
        <span className="sim3d-metric-label">Root Depth</span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.rootDepth.toFixed(2)} m {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title="Weekly precipitation and net irrigation applied (mm) [D]"
        data-tooltip="Weekly precipitation and net irrigation applied (mm) [D]"
      >
        <span className="sim3d-metric-label">
          Rain / Irrigation <Explain id="evapotranspiration" />
        </span>
        <span className="sim3d-metric-val">
          {m?.rain.toFixed(1)} mm / {hist ? ns : <>{m?.irrigation.toFixed(1)} mm</>} {d}
        </span>
      </div>
    </div>
  );
}

/** Farm view block: plot labels, the farm canvas, the scenery note and both metric strips. */
function FarmStage({
  current,
  other,
  otherLabel,
  week,
  month,
  isDark,
  quality,
  reducedMotion,
  onFrameStats,
  source,
}: {
  current: { option: Sim3DOption; scenario: Sim3DScenario };
  other: { option: Sim3DOption; scenario: Sim3DScenario };
  otherLabel: string;
  week: number;
  month: number;
  isDark: boolean;
  quality: QualityTier;
  reducedMotion: boolean;
  onFrameStats: (s: FrameStats) => void;
  source: string;
}) {
  const plots = useMemo(() => [current, other] as [typeof current, typeof other], [current, other]);
  const m = plots.map((p) => weekTelemetry(p.option, p.scenario, week));
  const labels = [FARM_TEXT.current, otherLabel];
  return (
    <section className="farm-stage" aria-label={FARM_TEXT.label}>
      <div className="farm-labels">
        {plots.map((p, i) => (
          <div key={i} className="farm-label">
            <strong>{labels[i]}</strong>
            <span className="sim3d-seq-tag">{p.option.sequence.map((c) => cropName(c)).join(" → ")}</span>
            {m[i].historyOnly && <span className="farm-ns">{FARM_TEXT.notSimulated}</span>}
          </div>
        ))}
      </div>
      <FarmScene
        plots={plots}
        weekIndex={week}
        month={month}
        isDark={isDark}
        quality={quality}
        reducedMotion={reducedMotion}
        onFrameStats={onFrameStats}
      />
      <p className="farm-scenery-note">{FARM_TEXT.scenery}</p>
      <div className="farm-strips">
        {plots.map((_, i) => (
          <div key={i} className="farm-strip">
            <h4>{labels[i]}</h4>
            <MetricStrip m={m[i]} source={source} />
          </div>
        ))}
      </div>
    </section>
  );
}

export default function Field3DView({
  pack,
  regionId,
}: {
  pack: FieldPack;
  regionId: string;
}) {
  const { effective } = useTheme();
  const isDark = effective === "dark";

  const [sim3d, setSim3d] = useState<FieldSim3D | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // View state
  const [week, setWeek] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [scenarioId, setScenarioId] = useState<string>("t+0_p+0");
  const [viewMode, setViewMode] = useState<"side-by-side" | "toggle">("side-by-side");
  const [toggleActive, setToggleActive] = useState<"current" | "alt">("current");
  const [selectedAltIdx, setSelectedAltIdx] = useState<number>(0);
  const showBuilder = useMemo(builderEnabled, []);
  // The builder panel opens from the "Build your own rotation" button (lazy: its code loads then).
  const [builderOpen, setBuilderOpen] = useState<boolean>(builderOpenAtStart);
  // Farm view (isometric farm with two plots) is the default where it is enabled; the Soil X-ray
  // toggle switches back to the glass soil view.
  const farmAvailable = useMemo(farmEnabled, []);
  const [farmMode, setFarmMode] = useState<boolean>(farmAvailable);
  // Which 3D panes have been shown: they are mounted on first show and then kept (only hidden).
  const visited = useRef({ farm: false, glass: false });
  // Rotation Builder result (simulated in the browser); replaces the alternative while set
  const [builtOption, setBuiltOption] = useState<Sim3DOption | null>(null);

  // Hover telemetry
  const [currentMetrics, setCurrentMetrics] = useState<HoverMetric | null>(null);
  const [altMetrics, setAltMetrics] = useState<HoverMetric | null>(null);

  // WebGL support
  const [useFallback, setUseFallback] = useState<boolean>(false);

  useEffect(() => {
    if (!isWebGLAvailable() || prefersReducedMotion()) {
      setUseFallback(true);
    }
  }, []);

  // Phones and low-core devices get fewer instances and a capped pixel ratio.
  const quality = useMemo(
    () => pickQuality(window.innerWidth, typeof navigator !== "undefined" ? navigator.hardwareConcurrency : undefined),
    [],
  );
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);

  // Switch to the 2D view once if the first ~2 s of 3D ran too slowly (median below MIN_MEDIAN_FPS).
  const [slowFps, setSlowFps] = useState<number | null>(null);
  const autoFallbackDone = useRef(false);
  const handleFrameStats = useCallback((s: FrameStats) => {
    if (autoFallbackDone.current || !(s.median < MIN_MEDIAN_FPS)) return;
    autoFallbackDone.current = true;
    setSlowFps(Math.floor(s.median));
    setUseFallback(true);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    loadSim3D(regionId, pack.field.field_id)
      .then((data) => {
        setSim3d(data);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [regionId, pack.field.field_id]);

  // Animation timeline playback
  useEffect(() => {
    if (!isPlaying || !sim3d) return;
    const interval = setInterval(() => {
      setWeek((w) => (w >= 155 ? 0 : w + 1));
    }, 180);
    return () => clearInterval(interval);
  }, [isPlaying, sim3d]);

  // Selected alternative option
  const activeAlternative: Sim3DOption | null = useMemo(() => {
    if (builtOption) return builtOption;
    if (!sim3d || sim3d.alternatives.length === 0) return null;
    return sim3d.alternatives[selectedAltIdx] ?? sim3d.alternatives[0];
  }, [sim3d, selectedAltIdx, builtOption]);

  // A built rotation is simulated for normal / dry / hot only: keep the weather on one of those.
  const scenarioIds = builtOption ? Object.keys(builtOption.scenarios) : Object.keys(sim3d?.current.scenarios ?? {});
  useEffect(() => {
    if (builtOption && !(scenarioId in builtOption.scenarios)) setScenarioId("t+0_p+0");
  }, [builtOption, scenarioId]);
  const handleGrow = useCallback((o: Sim3DOption) => {
    setBuiltOption(o);
    setWeek(0);
    setIsPlaying(true);
  }, []);
  const handleClear = useCallback(() => setBuiltOption(null), []);

  // Prepare chart data for 2D fallback or analytical comparison
  const fallbackChartData = useMemo(() => {
    if (!sim3d || !activeAlternative) return [];
    const curScen = sim3d.current.scenarios[scenarioId] ?? sim3d.current.scenarios["t+0_p+0"];
    const altScen = activeAlternative.scenarios[scenarioId] ?? activeAlternative.scenarios["t+0_p+0"];
    if (!curScen || !altScen) return [];

    // History-only weeks (e.g. perennial forage) are not simulated: a gap in the line, not a value.
    const sim = (o: Sim3DOption, i: number) => historyOnlyKey(o.sequence, o.crops, i) === null;
    return sim3d.weeks.map((wk, i) => ({
      week: wk.label,
      weekNum: i,
      curSoilWater: sim(sim3d.current, i) ? curScen.soil_water_mm[i] : null,
      altSoilWater: sim(activeAlternative, i) ? altScen.soil_water_mm[i] : null,
      taw: curScen.taw_mm[i],
      curCanopy: Math.round((curScen.canopy_cover[i] ?? 0) * 100),
      altCanopy: Math.round((altScen.canopy_cover[i] ?? 0) * 100),
    }));
  }, [sim3d, activeAlternative, scenarioId]);

  if (loading) {
    return (
      <div className="sim3d-loading-state" role="status">
        <p>{t("sim3d.loading")}</p>
      </div>
    );
  }

  if (error || !sim3d) {
    return (
      <div className="sim3d-error-state" role="alert">
        <p>{t("error.load", { what: "3D simulation", message: error ?? "no data" })}</p>
      </div>
    );
  }

  const curScen = sim3d.current.scenarios[scenarioId] ?? sim3d.current.scenarios["t+0_p+0"];
  const altScen = activeAlternative?.scenarios[scenarioId] ?? activeAlternative?.scenarios["t+0_p+0"];
  const activeWeekInfo = sim3d.weeks[week] ?? sim3d.weeks[0];
  if (!useFallback) {
    if (farmMode && farmAvailable) visited.current.farm = true;
    else visited.current.glass = true;
  }

  return (
    <section className="sim3d-view" aria-label="Field in 3D Simulation View">
      {/* Honesty & Baseline Weather Badges */}
      <header className="sim3d-header">
        <div className="sim3d-banner-row">
          <span className="sim3d-honesty-pill">
            <span aria-hidden="true">ℹ️</span> {t("sim3d.honesty")}
          </span>
          <span className="sim3d-weather-pill">
            <span aria-hidden="true">🌦️</span> {sim3d.weather_label} <TagBadge tag="D" />
          </span>
          <span className="sim3d-disclaimer-pill">
            {t("sim3d.disclaimer", { year: sim3d.weather_year })}
          </span>
        </div>
        <p className="sim3d-subtitle">
          Observe how the rotation and roots interact with soil moisture week by week over the 3-year timeline.
        </p>
      </header>

      {showBuilder && (
        <div className="builder-launch">
          <button
            type="button"
            className="builder-open-btn"
            aria-expanded={builderOpen}
            aria-controls="builder-panel"
            onClick={() => {
              if (builderOpen) handleClear();
              setBuilderOpen(!builderOpen);
            }}
          >
            {builderOpen ? bt("builder.close") : bt("builder.open")}
          </button>
          <span className="muted">{bt("builder.openHint")}</span>
        </div>
      )}
      {showBuilder && builderOpen && (
        <div id="builder-panel">
          <Suspense fallback={<p className="muted">{bt("builder.loading")}</p>}>
            <RotationBuilder pack={pack} regionId={regionId} onGrow={handleGrow} onClear={handleClear} />
          </Suspense>
        </div>
      )}

      {/* Control Toolbar */}
      <nav className="sim3d-toolbar" aria-label="Simulation Controls">
        <div className="sim3d-control-group">
          <label htmlFor="sim3d-scenario-select">
            <strong>{t("sim3d.scenario")}:</strong>
          </label>
          <select
            id="sim3d-scenario-select"
            className="sim3d-select"
            value={scenarioId}
            onChange={(e) => {
              setScenarioId(e.target.value);
              if (e.target.value.endsWith("_p-20")) emitTour("sim-drought");
            }}
          >
            {scenarioIds.map((sid) => (
              <option key={sid} value={sid}>
                {SCENARIO_LABELS[sid] ?? sid}
              </option>
            ))}
          </select>
        </div>

        <div className="sim3d-control-group">
          <label htmlFor="sim3d-alt-select">
            <strong>{t("sim3d.alternative")}:</strong>
          </label>
          <select
            id="sim3d-alt-select"
            className="sim3d-select"
            value={selectedAltIdx}
            disabled={!!builtOption}
            onChange={(e) => setSelectedAltIdx(Number(e.target.value))}
          >
            {sim3d.alternatives.map((alt, idx) => (
              <option key={alt.option_id} value={idx}>
                {alt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="sim3d-control-group sim3d-view-mode-toggle">
          {farmAvailable && (
            <button
              type="button"
              className={`sim3d-toggle-btn ${!farmMode && !useFallback ? "active" : ""}`}
              onClick={() => {
                setUseFallback(false);
                setFarmMode((f) => !f);
              }}
              aria-pressed={!farmMode && !useFallback}
              title={FARM_TEXT.xrayTitle}
            >
              {FARM_TEXT.xray}
            </button>
          )}
          <button
            type="button"
            className={`sim3d-toggle-btn ${viewMode === "side-by-side" && !useFallback && !farmMode ? "active" : ""}`}
            onClick={() => {
              setUseFallback(false);
              setFarmMode(false);
              setViewMode("side-by-side");
            }}
            aria-pressed={viewMode === "side-by-side" && !useFallback}
          >
            {t("sim3d.sideBySide")}
          </button>
          <button
            type="button"
            className={`sim3d-toggle-btn ${viewMode === "toggle" && !useFallback ? "active" : ""}`}
            onClick={() => {
              setUseFallback(false);
              setFarmMode(false);
              setViewMode("toggle");
            }}
            aria-pressed={viewMode === "toggle"}
          >
            {t("sim3d.toggle")}
          </button>
          <button
            type="button"
            className={`sim3d-toggle-btn ${useFallback ? "active" : ""}`}
            onClick={() => setUseFallback((f) => !f)}
            aria-pressed={useFallback}
            title="Toggle between 3D interactive view and accessible 2D time-series charts"
          >
            {useFallback ? "3D View" : "2D Fallback"}
          </button>
        </div>
      </nav>

      {/* Default Ranking Notice */}
      {activeAlternative && (
        <div className="sim3d-alt-notice" role="note">
          <p>
            {builtOption ? bt("sim3d.builderNotice") : t("sim3d.defaultNotice", { name: activeAlternative.label })}
          </p>
        </div>
      )}

      {/* View panes stay mounted once shown and are only hidden: switching Farm / Soil X-ray,
          Side by side / Toggle or 3D / 2D reuses each scene's renderer, geometries and materials. */}
      {visited.current.farm && activeAlternative && altScen && (
        <div className="sim3d-pane" hidden={useFallback || !farmMode}>
          <FarmStage
            current={{ option: sim3d.current, scenario: curScen }}
            other={{ option: activeAlternative, scenario: altScen }}
            otherLabel={activeAlternative.label}
            week={week}
            month={activeWeekInfo.month}
            isDark={isDark}
            quality={quality}
            reducedMotion={reducedMotion}
            onFrameStats={handleFrameStats}
            source={sim3d.source}
          />
        </div>
      )}
      {visited.current.glass && (
        <div
          className={`sim3d-stage ${viewMode === "side-by-side" ? "stage-side-by-side" : "stage-single"}`}
          hidden={useFallback || farmMode}
        >
          {/* Current Rotation Block */}
          {(
            <div className="sim3d-card" hidden={viewMode === "toggle" && toggleActive !== "current"}>
              <header className="sim3d-card-header">
                <h3>Current Rotation</h3>
                <span className="sim3d-seq-tag">
                  {sim3d.current.sequence.join(" → ").replace(/_/g, " ")}
                </span>
              </header>

              <div
                className="sim3d-canvas-wrap"
                title="Interactive 3D simulation block: drag to rotate, pinch or scroll to zoom. Amber structures represent crop canopy; downward meshes represent root depth; blue translucent volume represents available soil water."
              >
                <Field3DScene
                  option={sim3d.current}
                  scenario={curScen}
                  weekIndex={week}
                  isDark={isDark}
                  quality={quality}
                  reducedMotion={reducedMotion}
                  onFrameStats={handleFrameStats}
                  onHoverData={setCurrentMetrics}
                />
              </div>

              {/* Weekly Telemetry Metrics */}
              <MetricStrip m={currentMetrics} source={sim3d.source} />
            </div>
          )}

          {/* Alternative Rotation Block */}
          {activeAlternative && altScen && (
            <div className="sim3d-card" hidden={viewMode === "toggle" && toggleActive !== "alt"}>
              <header className="sim3d-card-header">
                <h3>{activeAlternative.label}</h3>
                <span className="sim3d-seq-tag">
                  {activeAlternative.sequence.join(" → ").replace(/_/g, " ")}
                </span>
              </header>

              <div
                className="sim3d-canvas-wrap"
                title="Interactive 3D simulation block: drag to rotate, pinch or scroll to zoom. Amber structures represent crop canopy; downward meshes represent root depth; blue translucent volume represents available soil water."
              >
                <Field3DScene
                  option={activeAlternative}
                  scenario={altScen}
                  weekIndex={week}
                  isDark={isDark}
                  quality={quality}
                  reducedMotion={reducedMotion}
                  onFrameStats={handleFrameStats}
                  onHoverData={setAltMetrics}
                />
              </div>

              {/* Weekly Telemetry Metrics */}
              <MetricStrip m={altMetrics} source={sim3d.source} />
            </div>
          )}
        </div>
      )}
      {useFallback && (
        /* Accessible 2D Fallback Chart */
        <div className="sim3d-fallback-section" role="region" aria-label="2D Simulation Fallback Chart">
          <div className="sim3d-fallback-banner">
            <p>
              <strong>{t("sim3d.fallbackTitle")}:</strong>{" "}
              {slowFps !== null ? t("sim3d.slowFallback", { fps: slowFps }) : t("sim3d.fallbackNotice")}
            </p>
          </div>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart data={fallbackChartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="week" interval={12} tick={{ fontSize: 11 }} />
                <YAxis unit="mm" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <ReferenceLine x={activeWeekInfo.label} stroke="#f59e0b" strokeWidth={2} label="Selected week" />
                <Line
                  type="monotone"
                  dataKey="curSoilWater"
                  name="Current: Soil Water (mm) [D]"
                  stroke={isDark ? CHART_COLOURS.dark.pred : CHART_COLOURS.light.pred}
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="altSoilWater"
                  name="Alternative: Soil Water (mm) [D]"
                  stroke={isDark ? CHART_COLOURS.dark.obs : CHART_COLOURS.light.obs}
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {[...new Set(sim3d.current.sequence.filter(isHistoryOnly))].map((c) => (
            <p key={c} className="muted">
              {t("sim3d.current")}: {t("season.historyOnly", { crop: cropName(c) })}
            </p>
          ))}
        </div>
      )}

      {/* Single Mode Toggle Pills */}
      {viewMode === "toggle" && !useFallback && (
        <div className="sim3d-toggle-bar">
          <button
            type="button"
            className={`sim3d-toggle-pill ${toggleActive === "current" ? "active" : ""}`}
            onClick={() => setToggleActive("current")}
          >
            Current Rotation
          </button>
          <button
            type="button"
            className={`sim3d-toggle-pill ${toggleActive === "alt" ? "active" : ""}`}
            onClick={() => setToggleActive("alt")}
          >
            {activeAlternative?.label}
          </button>
        </div>
      )}

      {/* Timeline Scrubber & Playback Controls */}
      <footer className="sim3d-timeline-tray" aria-label="Timeline Scrubber">
        <div className="sim3d-playback-row">
          <button
            type="button"
            className="sim3d-play-btn"
            onClick={() => {
              if (!isPlaying) emitTour("sim-play");
              setIsPlaying(!isPlaying);
            }}
            aria-label={isPlaying ? t("sim3d.pause") : t("sim3d.play")}
          >
            {isPlaying ? "⏸ Pause" : "▶ Play"}
          </button>

          <button
            type="button"
            className="sim3d-step-btn"
            onClick={() => setWeek((w) => Math.max(0, w - 1))}
            aria-label={t("sim3d.prevWeek")}
          >
            ◀
          </button>

          <div className="sim3d-scrubber-track">
            <input
              type="range"
              id="sim3d-scrubber"
              min={0}
              max={155}
              value={week}
              onChange={(e) => setWeek(Number(e.target.value))}
              aria-label={t("sim3d.scrubber")}
              className="sim3d-slider"
            />
            <div className="sim3d-scrubber-labels">
              <span>2022 (Year 1)</span>
              <span>2023 (Year 2)</span>
              <span>2024 (Year 3)</span>
            </div>
          </div>

          <button
            type="button"
            className="sim3d-step-btn"
            onClick={() => setWeek((w) => Math.min(155, w + 1))}
            aria-label={t("sim3d.nextWeek")}
          >
            ▶
          </button>

          <div className="sim3d-week-display">
            <strong>{activeWeekInfo.label}</strong>
          </div>
        </div>
      </footer>

      {/* 3D Simulation Guide and Glossary Notes (Item 8) */}
      <section className="sim3d-guide" aria-labelledby="sim3d-guide-heading">
        <header className="sim3d-guide-header">
          <div className="sim3d-guide-title-wrap">
            <h3 id="sim3d-guide-heading">{t("sim3d.explainers.heading")}</h3>
            <p className="sim3d-guide-intro">{t("sim3d.explainers.intro")}</p>
          </div>
          <a
            href={`#/${regionId}/methods#glossary`}
            className="sim3d-glossary-jump-btn"
          >
            {t("sim3d.explainers.viewGlossary")} →
          </a>
        </header>

        <div className="sim3d-guide-grid">
          {SIM3D_EXPLAINERS.map((id) => {
            const e = explainer(id);
            return (
              <article key={id} className="sim3d-guide-card" id={`sim3d-note-${id}`}>
                <div className="sim3d-guide-card-head">
                  <h4 className="sim3d-guide-card-title">{e.title}</h4>
                  <a
                    href={`#/${regionId}/methods#glossary-${id}`}
                    className="sim3d-guide-glossary-link"
                    title={`View ${e.title} in technical glossary`}
                  >
                    Glossary ↗
                  </a>
                </div>
                <p className="sim3d-guide-card-body">{e.body}</p>
                <footer className="sim3d-guide-card-foot">
                  <span className="sim3d-guide-source">
                    {t("explain.source")}{" "}
                    {e.url ? (
                      <a href={e.url} target="_blank" rel="noreferrer">
                        {e.source}
                      </a>
                    ) : (
                      e.source
                    )}
                  </span>
                </footer>
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}
