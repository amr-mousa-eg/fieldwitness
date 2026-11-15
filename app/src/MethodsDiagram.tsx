import { useRoute } from "./route";
import { type StringKey, t } from "./strings";

/**
 * Methods diagram (Phase 12, Item 9; redesigned).
 *
 * Four numbered stages, read left to right on desktop and top to bottom on phones (the CSS in
 * styles.css switches the layout; text stays at full size). Every box is a real link to the
 * part of the Methods page that explains it. Every fact here comes from the Methods page
 * text (strings/en.json methods.limits.* and methods.how.*); add nothing that is not there.
 */

/** One dataset named in the "What we observe" box, tied to its row in the Methods data table. */
export interface DiagramSource {
  name: string;
  /** Id in MethodsPage DATASETS (the official source list). */
  dataset: "hls" | "power" | "smap" | "grace" | "nasadem" | "soilgrids" | "csb";
}

export interface DiagramBox {
  id: string;
  label: string;
  lines: string[];
  /** Element id on the Methods page that explains this box. */
  target: string;
  status?: "ON" | "OFF";
  /** Only for the data box: the datasets it lists. */
  sources?: DiagramSource[];
}

export interface DiagramStage {
  id: "observe" | "model" | "check" | "get";
  step: number;
  title: string;
  boxes: DiagramBox[];
}

export const DIAGRAM_SOURCES: DiagramSource[] = [
  { name: "HLS 30 m satellite history", dataset: "hls" },
  { name: "GIBS true-colour basemap (HLS, summer 2023)", dataset: "hls" },
  { name: "NASA POWER daily weather", dataset: "power" },
  { name: "SMAP soil moisture (9 km, context)", dataset: "smap" },
  { name: "GRACE water storage (context)", dataset: "grace" },
  { name: "NASADEM slope (30 m)", dataset: "nasadem" },
  { name: "ISRIC SoilGrids 2.0 soil (250 m)", dataset: "soilgrids" },
  { name: "USDA CSB field boundaries and crop labels", dataset: "csb" },
];

export const DIAGRAM_STAGES: DiagramStage[] = [
  {
    id: "observe",
    step: 1,
    title: "What we observe",
    boxes: [
      {
        id: "data",
        label: "Data",
        lines: [],
        target: "m-data",
        sources: DIAGRAM_SOURCES,
      },
    ],
  },
  {
    id: "model",
    step: 2,
    title: "What we model",
    boxes: [
      {
        id: "field_story",
        label: "Field story",
        lines: [
          "Seasons 2015–2024 from HLS (KS) & 2017–2024 S2 L2A (UA)",
          "86.7% TWDTW season match (88.7% DTW; target 90%)",
        ],
        target: "m-limits",
      },
      {
        id: "w1_physics",
        label: "Witness 1: Physics",
        lines: [
          "FAO-56 water balance, driven by NASA POWER weather",
          "KS SSURGO [E] TAW (med. 282.1 mm); UA SoilGrids 0–135 cm [E] (med. 206.5 mm)",
        ],
        target: "glossary-water_balance",
        status: "ON",
      },
      {
        id: "w2_past",
        label: "Witness 2: Own past",
        lines: [
          "HLS/S2 history calibrates the physics (ABC) and gives a credibility score",
          "UA: 120/120 calibrated (73 ≥ 0.60, med. 0.658); KS: 185/200 (med. 0.483)",
        ],
        target: "glossary-credibility",
        status: "ON",
      },
      {
        id: "w3_neighbours",
        label: "Witness 3: Neighbours",
        lines: [
          "Kansas: No neighbour contrast passed the diagnostic checks (0 of 32)",
          "Ukraine (T36UVU): 30 pre-cutoff Panel-OBDML/DAPSM contrasts ACTIVE [D]",
        ],
        target: "m-limits",
        status: "ON",
      },
    ],
  },
  {
    id: "check",
    step: 3,
    title: "What we check",
    boxes: [
      {
        id: "agreement",
        label: "Evidence grade",
        lines: [
          "Agreement between witnesses gives A–D",
          "Capped at B in Kansas; A–C unlocked in Ukraine (73 B / 47 C top · 44 A options)",
        ],
        target: "m-regions",
      },
      {
        id: "hindcast_check",
        label: "Hindcast check",
        lines: [
          "Data frozen at 31 Dec 2021, then 2022–2024 predicted",
          "Split-CQR lifted 90% coverage (SOS 86.3–91.1% sym; canopy 71.8–79.0%)",
          "Beats baselines B1/B2 overall & all 3 crops (KS)",
        ],
        target: "glossary-hindcast",
      },
    ],
  },
  {
    id: "get",
    step: 4,
    title: "What you get",
    boxes: [
      {
        id: "rotation_rank",
        label: "Rotation options",
        lines: ["Ranked by Pareto dominance and your priorities", "“Why this ranking?” breakdown"],
        target: "m-how",
      },
    ],
  },
];

/** All boxes in reading order. */
export const DIAGRAM_BOXES: DiagramBox[] = DIAGRAM_STAGES.flatMap((s) => s.boxes);

/** Re-export DATASETS reference helper cleanly while routing links across split tabs. */
export function methodsAnchorHref(regionId: string, target: string): string {
  const page =
    target === "m-data" ? "resources" : target.startsWith("glossary") ? "terms" : "methods";
  return `#/${encodeURIComponent(regionId)}/${page}#${target}`;
}

function Box({ box, regionId }: { box: DiagramBox; regionId: string }) {
  const off = box.status === "OFF";
  return (
    <a
      id={`box-${box.id}`}
      href={methodsAnchorHref(regionId, box.target)}
      className={`mdia-box${off ? " mdia-box--off" : ""}`}
      data-status={box.status}
    >
      <span className="mdia-box-head">
        <span className="mdia-box-label">{t(`methods.diagram.box.${box.id}.label` as StringKey)}</span>
        {box.status && (
          <span className={`mdia-status mdia-status--${box.status.toLowerCase()}`}>
            {t(`methods.diagram.status.${box.status.toLowerCase()}` as StringKey)}
          </span>
        )}
      </span>
      {box.sources && (
        <ul className="mdia-sources">
          {box.sources.map((s, idx) => (
            <li key={s.name}>{t(`methods.diagram.src.${idx}` as StringKey)}</li>
          ))}
        </ul>
      )}
      {box.lines.map((line, idx) => (
        <span key={line} className="mdia-line">
          {t(`methods.diagram.box.${box.id}.line${idx}` as StringKey)}
        </span>
      ))}
    </a>
  );
}

export function MethodsDiagram() {
  const regionId = useRoute().regionId ?? "ks_t14slh";
  return (
    <figure className="mdia" aria-labelledby="methods-diagram-caption">
      <figcaption id="methods-diagram-caption" className="mdia-caption">
        {t("methods.diagram.caption")}
      </figcaption>
      <ol className="mdia-stages">
        {DIAGRAM_STAGES.map((stage) => (
          <li key={stage.id} id={`stage-${stage.id}`} className="mdia-stage">
            <p className="mdia-stage-title">
              <span className="mdia-step" aria-hidden="true">
                {stage.step}
              </span>
              <span className="sr-only">{t("methods.diagram.stepSr", { step: stage.step })}</span>
              {t(`methods.diagram.stage.${stage.id}` as StringKey)}
            </p>
            <div className="mdia-boxes">
              {stage.boxes.map((box) => (
                <Box key={box.id} box={box} regionId={regionId} />
              ))}
            </div>
            {stage.step < DIAGRAM_STAGES.length && <span className="mdia-arrow" aria-hidden="true" />}
          </li>
        ))}
      </ol>
    </figure>
  );
}
