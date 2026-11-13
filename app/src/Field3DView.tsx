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
import { MIN_MEDIAN_FPS, type QualityTier, historyOnlyKey, pickQuality } from "./field3d/growth";
import { isHistoryOnly } from "./seasons";
import { Explain } from "./Explain";
import { SIM3D_EXPLAINERS, explainer } from "./explainers";
import { loadSim3D } from "./data";
import { type StringKey, cropName, getLocale, t } from "./strings";
import { TagBadge } from "./tags";
import { CHART_COLOURS } from "./theme";
import type { FieldPack, FieldSim3D, Sim3DOption, Sim3DScenario } from "./types";
import { emitTour } from "./tourEvents";
import { useTheme } from "./useTheme";

function sim3dWeatherLabel(label: string, year: number): string {
  if (getLocale() !== "ar") return label;
  if (/^Weather of \d{4} \(median-rain year\)$/i.test(label)) {
    return `طقس ${year} (سنة أمطار متوسطة)`;
  }
  return label;
}

function sim3dOptionLabel(opt: Pick<Sim3DOption, "option_id" | "label" | "sequence">): string {
  if (getLocale() !== "ar") return opt.label;
  if (opt.option_id === "current") return t("sim3d.current");
  const seq = opt.sequence.map((c) => cropName(c)).join(" → ");
  const m = /^Alternative\s+(\d+):/i.exec(opt.label);
  if (m) return `${t("card.alt", { n: m[1] })}: ${seq}`;
  return seq || opt.label;
}

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

const KNOWN_STAGES = new Set(["fallow", "initial", "development", "mid", "late"]);
const KNOWN_SCENARIOS = new Set([
  "t+0_p+0",
  "t+0_p-20",
  "t+0_p-10",
  "t+0_p+10",
  "t+1_p+0",
  "t+1_p-20",
  "t+1_p-10",
  "t+1_p+10",
  "t+2_p+0",
  "t+2_p-20",
  "t+2_p-10",
  "t+2_p+10",
]);

function scenarioLabel(sid: string): string {
  return KNOWN_SCENARIOS.has(sid) ? t(`sim3d.scen.${sid}` as StringKey) : sid;
}

function stageLabel(stage: string): string {
  return KNOWN_STAGES.has(stage) ? t(`sim3d.stage.${stage}` as StringKey) : stage;
}

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
  /** Cover-crop week (`isCoverWeek` in `field3d/farm.ts`); set by both the farm and the glass view. */
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
        title={t("sim3d.metric.cropStageTip")}
        data-tooltip={t("sim3d.metric.cropStageTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.cropStage")} {!hist && !m?.cover && m?.crop === "fallow" && <Explain id="fallow_bare_soil" />}
        </span>
        <span className="sim3d-metric-val">
          {hist ? (
            t("season.historyOnly", { crop: cropName(hist) })
          ) : m?.crop === "fallow" ? (
            m.cover ? (
              <>
                {cropName("cover_crop")} {d}
              </>
            ) : (
              t("sim3d.bareFallow")
            )
          ) : (
            <>
              {m ? cropName(m.crop) : "—"} ({m ? stageLabel(m.stage) : "—"}) {d}
            </>
          )}
        </span>
      </div>
      <div
        className="sim3d-metric-item"
        title={t("sim3d.metric.soilWaterTip")}
        data-tooltip={t("sim3d.metric.soilWaterTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.soilWater")} <Explain id="root_zone_soil_water" /> <Explain id="available_water_capacity" />
        </span>
        <span className="sim3d-metric-val">
          {hist ? ns : (
            <>
              {t("sim3d.metric.soilWaterOf", {
                water: m?.soilWater.toFixed(1) ?? "—",
                taw: m?.taw.toFixed(0) ?? "—",
              })}{" "}
              {d}
            </>
          )}
        </span>
      </div>
      <div
        className="sim3d-metric-item"
        title={t("sim3d.metric.canopyTip")}
        data-tooltip={t("sim3d.metric.canopyTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.canopy")} <Explain id="canopy_proxy" />
        </span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.canopyCover.toFixed(2)} {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title={t("sim3d.metric.ksTip")}
        data-tooltip={t("sim3d.metric.ksTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.ks")} <Explain id="water_stress_ks" />
        </span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.ks.toFixed(2)} {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title={t("sim3d.metric.rootDepthTip")}
        data-tooltip={t("sim3d.metric.rootDepthTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.rootDepth")} <Explain id="root_depth" />
        </span>
        <span className="sim3d-metric-val">{hist ? ns : <>{m?.rootDepth.toFixed(2)} {t("unit.m")} {d}</>}</span>
      </div>
      <div
        className="sim3d-metric-item"
        title={t("sim3d.metric.rainIrrTip")}
        data-tooltip={t("sim3d.metric.rainIrrTip")}
      >
        <span className="sim3d-metric-label">
          {t("sim3d.metric.rainIrr")} <Explain id="evapotranspiration" />
        </span>
        <span className="sim3d-metric-val">
          {m?.rain.toFixed(1)} {t("unit.mm")} / {hist ? ns : <>{m?.irrigation.toFixed(1)} {t("unit.mm")}</>} {d}
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
  const labels = [t("sim3d.current"), otherLabel];
  return (
    <section className="farm-stage" aria-label={t("farm.label")}>
      <div className="farm-labels">
        {plots.map((p, i) => (
          <div key={i} className="farm-label">
            <strong>{labels[i]}</strong>
            <span className="sim3d-seq-tag">{p.option.sequence.map((c) => cropName(c)).join(" → ")}</span>
            {m[i].historyOnly && <span className="farm-ns">{t("season.notSimulated")}</span>}
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
      <p className="farm-scenery-note">{t("farm.scenery")}</p>
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
  const chart = CHART_COLOURS[effective];

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
        <p>{t("error.load", { what: t("error.what.sim3d"), message: error ?? t("error.noData") })}</p>
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
    <section className="sim3d-view" aria-label={t("sim3d.ariaLabel")}>
      {/* Honesty & Baseline Weather Badges */}
      <header className="sim3d-header">
        <div className="sim3d-banner-row">
          <span className="sim3d-honesty-pill">
            <span aria-hidden="true">ℹ️</span> {t("sim3d.honesty")}
          </span>
          <span className="sim3d-weather-pill">
            <span aria-hidden="true">🌦️</span> {sim3dWeatherLabel(sim3d.weather_label, sim3d.weather_year)} <TagBadge tag="D" />
          </span>
          <span className="sim3d-disclaimer-pill">
            {t("sim3d.disclaimer", { year: sim3d.weather_year })}
          </span>
        </div>
        <p className="sim3d-subtitle">{t("sim3d.subtitle")}</p>
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
      <nav className="sim3d-toolbar" aria-label={t("sim3d.controlsAria")}>
        <div className="sim3d-control-group">
          <label htmlFor="sim3d-scenario-select">
            <strong>{t("sim3d.scenario")}:</strong>
          </label>{" "}
          <Explain id="weather_whatif" />
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
                {scenarioLabel(sid)}
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
                {sim3dOptionLabel(alt)}
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
              title={t("farm.xrayTitle")}
            >
              {t("farm.xray")}
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
            title={t("sim3d.toggleTitle")}
          >
            {useFallback ? t("sim3d.view3d") : t("sim3d.view2d")}
          </button>
        </div>
      </nav>

      {/* Default Ranking Notice */}
      {activeAlternative && (
        <div className="sim3d-alt-notice" role="note">
          <p>
            {builtOption ? bt("sim3d.builderNotice") : t("sim3d.defaultNotice", { name: sim3dOptionLabel(activeAlternative) })}
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
            otherLabel={sim3dOptionLabel(activeAlternative)}
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
                <h3>{t("sim3d.current")}</h3>
                <span className="sim3d-seq-tag">
                  {sim3d.current.sequence.map((c) => cropName(c)).join(" → ")}
                </span>
              </header>

              <div
                className="sim3d-canvas-wrap"
                title={t("sim3d.canvasTitle")}
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
                <h3>{sim3dOptionLabel(activeAlternative)}</h3>
                <span className="sim3d-seq-tag">
                  {activeAlternative.sequence.map((c) => cropName(c)).join(" → ")}
                </span>
              </header>

              <div
                className="sim3d-canvas-wrap"
                title={t("sim3d.canvasTitle")}
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
        <div className="sim3d-fallback-section" role="region" aria-label={t("sim3d.fallbackAria")}>
          <div className="sim3d-fallback-banner">
            <p>
              <strong>{t("sim3d.fallbackTitle")}:</strong>{" "}
              {slowFps !== null ? t("sim3d.slowFallback", { fps: slowFps }) : t("sim3d.fallbackNotice")}
            </p>
          </div>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart data={fallbackChartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                <XAxis dataKey="week" interval={12} stroke={chart.axis} tick={{ fill: chart.axis, fontSize: 11 }} />
                <YAxis unit={` ${t("unit.mm")}`} stroke={chart.axis} tick={{ fill: chart.axis, fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chart.tooltipBg,
                    borderColor: chart.tooltipBorder,
                    color: chart.tooltipText,
                  }}
                />
                <Legend wrapperStyle={{ color: chart.axis }} />
                <ReferenceLine
                  x={activeWeekInfo.label}
                  stroke={chart.marks}
                  strokeWidth={2}
                  label={{ value: t("sim3d.selectedWeek"), fill: chart.marks, fontSize: 11 }}
                />
                <Line
                  type="monotone"
                  dataKey="curSoilWater"
                  name={t("sim3d.curSoilSeries")}
                  stroke={chart.pred}
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="altSoilWater"
                  name={t("sim3d.altSoilSeries")}
                  stroke={chart.obs}
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
            {t("sim3d.current")}
          </button>
          <button
            type="button"
            className={`sim3d-toggle-pill ${toggleActive === "alt" ? "active" : ""}`}
            onClick={() => setToggleActive("alt")}
          >
            {activeAlternative ? sim3dOptionLabel(activeAlternative) : ""}
          </button>
        </div>
      )}

      {/* Timeline Scrubber & Playback Controls */}
      <footer className="sim3d-timeline-tray" aria-label={t("sim3d.timelineAria")}>
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
            {isPlaying ? t("sim3d.pauseBtn") : t("sim3d.playBtn")}
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
              <span>{t("sim3d.yearLabel", { year: 2022, n: 1 })}</span>
              <span>{t("sim3d.yearLabel", { year: 2023, n: 2 })}</span>
              <span>{t("sim3d.yearLabel", { year: 2024, n: 3 })}</span>
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
                    title={t("sim3d.glossaryTitle", { title: e.title })}
                  >
                    {t("sim3d.glossaryLink")}
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
