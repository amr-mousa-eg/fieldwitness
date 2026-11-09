import { useEffect, useMemo, useState } from "react";
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
import { Field3DScene } from "./Field3DScene";
import { loadSim3D } from "./data";
import { t } from "./strings";
import { TagBadge } from "./tags";
import { CHART_COLOURS } from "./theme";
import type { FieldPack, FieldSim3D, Sim3DOption } from "./types";
import { useTheme } from "./useTheme";

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
    if (!sim3d || sim3d.alternatives.length === 0) return null;
    return sim3d.alternatives[selectedAltIdx] ?? sim3d.alternatives[0];
  }, [sim3d, selectedAltIdx]);

  // Prepare chart data for 2D fallback or analytical comparison
  const fallbackChartData = useMemo(() => {
    if (!sim3d || !activeAlternative) return [];
    const curScen = sim3d.current.scenarios[scenarioId] ?? sim3d.current.scenarios["t+0_p+0"];
    const altScen = activeAlternative.scenarios[scenarioId] ?? activeAlternative.scenarios["t+0_p+0"];
    if (!curScen || !altScen) return [];

    return sim3d.weeks.map((wk, i) => ({
      week: wk.label,
      weekNum: i,
      curSoilWater: curScen.soil_water_mm[i],
      altSoilWater: altScen.soil_water_mm[i],
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
        </div>
        <p className="sim3d-subtitle">
          Observe how the rotation and roots interact with soil moisture week by week over the 3-year timeline.
        </p>
      </header>

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
            onChange={(e) => setScenarioId(e.target.value)}
          >
            {Object.keys(sim3d.current.scenarios).map((sid) => (
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
          <button
            type="button"
            className={`sim3d-toggle-btn ${viewMode === "side-by-side" ? "active" : ""}`}
            onClick={() => setViewMode("side-by-side")}
            aria-pressed={viewMode === "side-by-side"}
          >
            {t("sim3d.sideBySide")}
          </button>
          <button
            type="button"
            className={`sim3d-toggle-btn ${viewMode === "toggle" ? "active" : ""}`}
            onClick={() => setViewMode("toggle")}
            aria-pressed={viewMode === "toggle"}
          >
            {t("sim3d.toggle")}
          </button>
        </div>
      </nav>

      {/* Default Ranking Notice */}
      {activeAlternative && (
        <div className="sim3d-alt-notice" role="note">
          <p>
            {t("sim3d.defaultNotice", { name: activeAlternative.label })}
          </p>
        </div>
      )}

      {/* Main Interactive Stage */}
      {!useFallback ? (
        <div className={`sim3d-stage ${viewMode === "side-by-side" ? "stage-side-by-side" : "stage-single"}`}>
          {/* Current Rotation Block */}
          {(viewMode === "side-by-side" || toggleActive === "current") && (
            <div className="sim3d-card">
              <header className="sim3d-card-header">
                <h3>Current Rotation</h3>
                <span className="sim3d-seq-tag">
                  {sim3d.current.sequence.join(" → ").replace(/_/g, " ")}
                </span>
              </header>

              <div className="sim3d-canvas-wrap">
                <Field3DScene
                  option={sim3d.current}
                  scenario={curScen}
                  weekIndex={week}
                  isDark={isDark}
                  onHoverData={setCurrentMetrics}
                />
              </div>

              {/* Weekly Telemetry Metrics */}
              <div className="sim3d-metric-strip">
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Crop & Stage</span>
                  <span className="sim3d-metric-val">
                    {currentMetrics?.crop === "fallow" ? (
                      "Bare fallow [D]"
                    ) : (
                      <>
                        {currentMetrics?.crop.replace(/_/g, " ")} ({currentMetrics?.stage}) <TagBadge tag="D" />
                      </>
                    )}
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Available Soil Water</span>
                  <span className="sim3d-metric-val">
                    <strong>{currentMetrics?.soilWater.toFixed(1)}</strong> of {currentMetrics?.taw.toFixed(0)} mm <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Canopy Proxy (Kc/Kc max)</span>
                  <span className="sim3d-metric-val">
                    {currentMetrics?.canopyCover.toFixed(2)} <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Water Stress (Ks)</span>
                  <span className="sim3d-metric-val">
                    {currentMetrics?.ks.toFixed(2)} <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Root Depth</span>
                  <span className="sim3d-metric-val">
                    {currentMetrics?.rootDepth.toFixed(2)} m <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Rain / Irrigation</span>
                  <span className="sim3d-metric-val">
                    {currentMetrics?.rain.toFixed(1)} mm / {currentMetrics?.irrigation.toFixed(1)} mm <TagBadge tag="D" />
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Alternative Rotation Block */}
          {activeAlternative && altScen && (viewMode === "side-by-side" || toggleActive === "alt") && (
            <div className="sim3d-card">
              <header className="sim3d-card-header">
                <h3>{activeAlternative.label}</h3>
                <span className="sim3d-seq-tag">
                  {activeAlternative.sequence.join(" → ").replace(/_/g, " ")}
                </span>
              </header>

              <div className="sim3d-canvas-wrap">
                <Field3DScene
                  option={activeAlternative}
                  scenario={altScen}
                  weekIndex={week}
                  isDark={isDark}
                  onHoverData={setAltMetrics}
                />
              </div>

              {/* Weekly Telemetry Metrics */}
              <div className="sim3d-metric-strip">
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Crop & Stage</span>
                  <span className="sim3d-metric-val">
                    {altMetrics?.crop === "fallow" ? (
                      "Bare fallow [D]"
                    ) : (
                      <>
                        {altMetrics?.crop.replace(/_/g, " ")} ({altMetrics?.stage}) <TagBadge tag="D" />
                      </>
                    )}
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Available Soil Water</span>
                  <span className="sim3d-metric-val">
                    <strong>{altMetrics?.soilWater.toFixed(1)}</strong> of {altMetrics?.taw.toFixed(0)} mm <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Canopy Proxy (Kc/Kc max)</span>
                  <span className="sim3d-metric-val">
                    {altMetrics?.canopyCover.toFixed(2)} <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Water Stress (Ks)</span>
                  <span className="sim3d-metric-val">
                    {altMetrics?.ks.toFixed(2)} <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Root Depth</span>
                  <span className="sim3d-metric-val">
                    {altMetrics?.rootDepth.toFixed(2)} m <TagBadge tag="D" />
                  </span>
                </div>
                <div className="sim3d-metric-item">
                  <span className="sim3d-metric-label">Rain / Irrigation</span>
                  <span className="sim3d-metric-val">
                    {altMetrics?.rain.toFixed(1)} mm / {altMetrics?.irrigation.toFixed(1)} mm <TagBadge tag="D" />
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Accessible 2D Fallback Chart */
        <div className="sim3d-fallback-section" role="region" aria-label="2D Simulation Fallback Chart">
          <div className="sim3d-fallback-banner">
            <p>
              <strong>{t("sim3d.fallbackTitle")}:</strong> {t("sim3d.fallbackNotice")}
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
            onClick={() => setIsPlaying(!isPlaying)}
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
    </section>
  );
}
