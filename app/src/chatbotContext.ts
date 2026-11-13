import { fieldNumber } from "./fields";
import { cropName, optionName } from "./strings";
import type { FieldPack, RegionIndex } from "./types";

export interface ChatContextSnapshot {
  page: string;
  regionId: string;
  fieldId?: string;
  fieldNumberLabel?: string | null;
  fieldPack?: FieldPack | null;
}

export interface ChatAnswer {
  text: string;
  sourceLabel: string;
  followUps: string[];
}

interface KnowledgeEntry {
  id: string;
  title: string;
  keywords: string[];
  answer: string;
  sourceLabel: string;
  followUps: string[];
}

// Lightweight pub/sub so FieldPage can publish the active FieldPack to the chatbot.
type PackListener = (pack: FieldPack | null) => void;
let currentFieldPack: FieldPack | null = null;
const packListeners = new Set<PackListener>();

export function setActiveFieldPack(pack: FieldPack | null): void {
  currentFieldPack = pack;
  for (const listener of packListeners) {
    listener(pack);
  }
}

export function getActiveFieldPack(): FieldPack | null {
  return currentFieldPack;
}

export function subscribeActiveFieldPack(listener: PackListener): () => void {
  packListeners.add(listener);
  return () => {
    packListeners.delete(listener);
  };
}

export const KNOWLEDGE_BASE: KnowledgeEntry[] = [
  {
    id: "overview",
    title: "What is FieldWitness?",
    keywords: ["what is", "fieldwitness", "about", "project", "nasa", "space apps", "overview", "purpose", "help"],
    answer:
      "FieldWitness is a crop-rotation decision-support tool built for NASA Space Apps Challenge 2026 ('Field Shift: Adapting Farms with NASA Data'). For each of 200 pilot fields in western Kansas (MGRS tile T14SLH), it reconstructs 12 years of NASA HLS 30 m satellite history [O/D], runs a FAO-56 soil-water balance calibrated to the field's own past (ABC) [D], evaluates 3-season rotations, and grades the evidence A–D.",
    sourceLabel: "Project Overview [O/D/E]",
    followUps: ["How do the three witnesses work?", "How are evidence grades A–D assigned?", "What are the project's honest limits?"],
  },
  {
    id: "witnesses",
    title: "The Three Witnesses",
    keywords: ["witness", "witnesses", "three", "physics", "own past", "abc", "neighbour", "neighbor", "doubleml", "trials", "k-state", "colby", "circuit breaker"],
    answer:
      "Every rotation option is evaluated by three independent witnesses:\n1) Physics (Witness 1): FAO-56 dual crop coefficient root-zone water balance forced by NASA POWER daily meteorology [D].\n2) Field's Own Past (Witness 2): Approximate Bayesian Computation (ABC) calibrating physics against 12 years of NASA HLS 30 m NDVI [D].\n3) Neighbours / Trials (Witness 3): Observational DoubleML contrasts across 200 fields failed balance/placebo checks (0/92 and 0/32 passed), so the observational witness is kept OFF by our safety circuit breaker. Where rotations match 30-year K-State Colby Research Center trials (Schlegel et al. 2018; Stone & Schlegel 2006) [E], those empirical trials serve as independent Witness 3 validation.",
    sourceLabel: "Three Witnesses Framework [D/E]",
    followUps: ["Why is the observational neighbour witness OFF?", "How does Grade A work?", "What soil data is used?"],
  },
  {
    id: "grades",
    title: "Evidence Grades A–D",
    keywords: ["grade", "grades", "a-d", "grade a", "grade b", "grade c", "grade d", "evidence", "credibility", "threshold"],
    answer:
      "Evidence grades summarize witness agreement and input quality:\n• Grade A: Physics and external validation (neighbours or K-State agronomic trials [E]) agree on sign with overlapping 90% intervals, ABC credibility ≥ 0.60, and 0 key inputs tagged [A].\n• Grade B: At least two witnesses agree (e.g., Physics + Own Past credibility ≥ 0.60).\n• Grade C: Only one witness supports the option, or witnesses disagree.\n• Grade D: More than half of key inputs are unverified assumptions [A].\nNote: Empirical hindcast testing showed Grade B vs Grade D CRPS difference was not statistically significant (95% CI [−3.28, +14.32]), so intervals should be read conservatively.",
    sourceLabel: "Grading Rules [A/D/E]",
    followUps: ["What do tags [O], [D], [E], [A] mean?", "What is ABC credibility?", "Why does FieldWitness not predict profit or tonnes/ha?"],
  },
  {
    id: "tags",
    title: "Data Source Tags [O, D, E, A]",
    keywords: ["tag", "tags", "[o]", "[d]", "[e]", "[a]", "badge", "source", "provenance", "legend"],
    answer:
      "Every number in FieldWitness carries a provenance tag:\n• [O] Observed: Direct satellite or ground measurements (e.g., NASA HLS 30 m interior pixels).\n• [D] Derived: Outputs of our models, ABC calibration, or water balance.\n• [E] External: Published third-party datasets or peer-reviewed parameters (NASA POWER, USDA CSB, USDA-NRCS SSURGO, FAO-56, K-State trials).\n• [A] Assumption: Team choices or unverified placeholders (e.g., priority weights, sowing-date offsets).",
    sourceLabel: "Data Provenance Standard",
    followUps: ["What soil data is used?", "How accurate is season detection?", "How are evidence grades A–D assigned?"],
  },
  {
    id: "soil",
    title: "Soil Water Capacity (SSURGO & SoilGrids)",
    keywords: ["soil", "taw", "ssurgo", "soilgrids", "aws", "water holding", "silt loam", "texture", "clay", "sand"],
    answer:
      "FieldWitness integrates two soil sources:\n• USDA-NRCS SSURGO [E]: Empirical Available Water Storage (AWS) across 198 surveyed Kansas pilot fields (Keith, Richfield, Ulysses silt loams) has a median of 282.1 mm (vs. the 150 mm baseline prior, which had a −119 mm mean bias). Available via `ssurgo_taw.py` and `--taw-source ssurgo`.\n• ISRIC SoilGrids 2.0 (250 m) [E]: Provides clay, sand, and organic carbon context.",
    sourceLabel: "USDA-NRCS SSURGO & SoilGrids [E]",
    followUps: ["How does winter wheat phenology work?", "What is the global climate lookup?"],
  },
  {
    id: "wheat",
    title: "Winter Wheat & Cross-Calendar Phenology",
    keywords: ["wheat", "winter wheat", "phenology", "heading", "doy", "baseline", "b1", "b2", "sorghum", "maize", "corn"],
    answer:
      "Winter wheat covers 31.4% of the Kansas pilot tile (`T14SLH`). Uncalibrated FAO-56 Idaho defaults caused a +36.0 d median heading lag (58.9 d MAE). We calibrated a Kansas High Plains profile (`ks_calibrated_kstate`: `[160, 70, 40, 25]` days, DOY 140–150 heading) from K-State Extension MF587 & Kansas Mesonet GDD priors [E], and updated `t73_baselines.py` to concatenate 730 days of cross-calendar NASA POWER weather (Oct t−1 to Jul t) across all 197 winter wheat seasons.",
    sourceLabel: "K-State Phenology & Hindcast Baselines [E/D]",
    followUps: ["What are the project's honest limits?", "What is the 3D farm view?"],
  },
  {
    id: "honesty",
    title: "Honest Limits & Hindcast Skill",
    keywords: ["limit", "limits", "honest", "hindcast", "accuracy", "spearman", "coverage", "season detection", "error", "skill", "caveat"],
    answer:
      "FieldWitness reports all negative and mixed validation results openly:\n• Season detection: 78.3% accuracy (188 of 240 held-out field-seasons) vs. a 90.0% target.\n• Hindcast skill (cut-off 2021-12-31, 2022–2024 seasons): Canopy integral Spearman ρ = 0.264; 90% interval coverage is 35.0% for canopy integral and 9.0% for cover days—uncertainty intervals are wide.\n• Observational neighbours: 0 of 32 matched contrasts passed diagnostic checks (kept OFF).\n• No yield mass or profit claims: We do not predict tonnes/ha, bu/acre, or dollar profit.",
    sourceLabel: "Pre-Registered Hindcast & Audit [D/E]",
    followUps: ["Why does FieldWitness not predict profit or tonnes/ha?", "How do the three witnesses work?"],
  },
  {
    id: "scope",
    title: "Why No Dollar Profit or Yield Mass Claims",
    keywords: ["profit", "dollar", "money", "price", "income", "tonnes", "bushel", "yield"],
    answer:
      "FieldWitness deliberately does not predict dollar profit, commodity prices, or absolute yield in tonnes/ha or bu/acre. A 30 m satellite pixel cannot observe local grain prices, fertilizer costs, or harvest moisture. Instead, we report Relative Yield Index (RYI, 0–1 dimensionless water-stress index) [D], water use (mm), bad-year tail water (CVaR10, mm), and bare-soil exposure months [D].",
    sourceLabel: "Scientific Scope & Guardrails",
    followUps: ["What are the project's honest limits?", "What do tags [O], [D], [E], [A] mean?"],
  },
  {
    id: "global",
    title: "Global Live Climate Assessment (Add My Field)",
    keywords: ["global", "add field", "add my field", "world", "outside kansas", "coordinates", "lat", "lon", "power api", "eto", "aridity"],
    answer:
      "On the 'Add My Field' page, any global latitude/longitude can be assessed on demand using the live NASA POWER Daily Meteorology API (`PRECTOTCORR`, `T2M_MAX`, `T2M_MIN`) [E] and astronomical Hargreaves ETo [D]. It computes annual precipitation, ETo, water deficit, and aridity index, and suggests climate-adapted 3-season rotations alongside USDA SSURGO (US) or ISRIC SoilGrids 2.0 (global) soil context.",
    sourceLabel: "Global Live Climate Connector [D/E]",
    followUps: ["What soil data is used?", "How do I print a field dossier?"],
  },
  {
    id: "print",
    title: "Printable 1-Page Field Dossier & 3D View",
    keywords: ["print", "pdf", "dossier", "report", "export", "3d", "farm view", "what-if", "slider", "scenario"],
    answer:
      "Every field page includes:\n• Print Field Dossier: Formats a clean 1-page A4 summary (field metadata, top 3 rotations, Three Witnesses status, 7-year NASA HLS trajectory, and mandatory attributions) via `@media print`.\n• Interactive 3D Farm & Soil View: Lets you replay weekly canopy growth, root-zone water depletion, and temperature/precipitation what-if scenarios.",
    sourceLabel: "Frontend Deliverables [D]",
    followUps: ["What is FieldWitness?", "What are the three witnesses?"],
  },
];

function summarizeFieldPack(pack: FieldPack, label?: string | null): string {
  const numLabel = label ? `Field ${label}` : `Field ${pack.field.field_id.slice(0, 8)}`;
  const cred = pack.credibility.value != null ? `${(pack.credibility.value * 100).toFixed(0)}%` : "not assessable";
  const currentOpt = pack.options.find((o) => o.option_id === "current");
  const topAlts = pack.options
    .filter((o) => o.option_id !== "current")
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 3);
  const recentHistory = pack.story
    .slice(-5)
    .map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : "Fallow"}`)
    .join(" → ");

  const altLines = topAlts
    .map((o, idx) => {
      const w = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} mm` : "—";
      const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "—";
      return `  #${idx + 1}: ${optionName(o)} (Grade ${o.grade}, Water ${w}, RYI ${ryi})`;
    })
    .join("\n");

  return (
    `Active Field Context — ${numLabel} (${pack.field.area_ha.toFixed(1)} ha, ${pack.field.interior_pixels} interior 30 m pixels [O], data as of ${pack.data_as_of}):\n` +
    `• Recent Crop History: ${recentHistory || "N/A"}\n` +
    `• ABC Own-Past Credibility: ${cred} [D]\n` +
    (currentOpt ? `• Current Rotation: ${optionName(currentOpt)} (Grade ${currentOpt.grade})\n` : "") +
    `• Top Ranked Alternatives:\n${altLines}\n` +
    `• Sensitivity & Next Step: ${pack.advice.measure_next}`
  );
}

export function buildSystemPrompt(ctx: ChatContextSnapshot): string {
  const baseFacts = KNOWLEDGE_BASE.map((k) => `- ${k.title}: ${k.answer}`).join("\n");
  const fieldSection = ctx.fieldPack
    ? `\n\nCURRENTLY VIEWED FIELD:\n${summarizeFieldPack(ctx.fieldPack, ctx.fieldNumberLabel)}`
    : `\n\nCURRENT PAGE: ${ctx.page} (Region: ${ctx.regionId}). No specific field is currently open.`;

  return (
    "You are the FieldWitness Scientific Assistant for NASA Space Apps Challenge 2026 ('Field Shift: Adapting Farms with NASA Data').\n" +
    "Rules:\n" +
    "1. Answer concisely and honestly using ONLY the project facts and active field data below.\n" +
    "2. Preserve data provenance tags ([O] observed, [D] derived, [E] external, [A] assumption) when quoting metrics.\n" +
    "3. NEVER invent yields in tonnes/ha or bu/acre, dollar profit, or claim certainty/guaranteed outcomes.\n\n" +
    "PROJECT KNOWLEDGE:\n" +
    baseFacts +
    fieldSection
  );
}

export function resolveFieldLabel(pack: FieldPack | null | undefined, index: RegionIndex | null): string | null {
  if (!pack || !index) return null;
  return String(fieldNumber(pack.field.field_id, index.fields));
}

export function answerQuestion(query: string, ctx: ChatContextSnapshot): ChatAnswer {
  const q = query.trim().toLowerCase();
  if (!q) {
    return {
      text: "Ask me anything about FieldWitness—how the Three Witnesses work, evidence grades A–D, soil TAW, winter wheat calibration, or the field you are currently viewing.",
      sourceLabel: "FieldWitness Assistant",
      followUps: ctx.fieldPack
        ? ["Summarize this field", "What is the top rotation for this field?", "What should I measure next?"]
        : ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
    };
  }

  // 1. Check scope guardrails (no profit / tonnes / certainty claims)
  if (/(profit|dollar|\$|income|price|tonnes|bushel|bu\/ac|guarant)/.test(q)) {
    const scope = KNOWLEDGE_BASE.find((e) => e.id === "scope")!;
    return {
      text: scope.answer,
      sourceLabel: scope.sourceLabel,
      followUps: scope.followUps,
    };
  }

  // 2. Check active field-specific queries when a FieldPack is loaded
  const pack = ctx.fieldPack;
  const asksAboutThisField =
    pack &&
    /(this field|my field|current field|summarize|summary|top option|best option|top rotation|best rotation|recommend|rank|grade|credibility|history|story|water|bare|flip|measure|sensitive|alternative)/.test(
      q,
    );

  if (pack && asksAboutThisField) {
    const label = ctx.fieldNumberLabel ? `Field ${ctx.fieldNumberLabel}` : `Field ${pack.field.field_id.slice(0, 8)}`;
    const topAlts = pack.options
      .filter((o) => o.option_id !== "current")
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 3);
    const currentOpt = pack.options.find((o) => o.option_id === "current");

    if (/(measure|flip|sensitive|next)/.test(q)) {
      return {
        text:
          `For ${label}:\n` +
          `• Recommended next measurement: ${pack.advice.measure_next}\n` +
          `• Counterfactual flip sensitivity: ${pack.advice.counterfactual_flip}\n` +
          `• Flip probability across posterior worlds: ${pack.advice.flip_probability.value != null ? `${(pack.advice.flip_probability.value * 100).toFixed(0)}% [D]` : "N/A"}`,
        sourceLabel: `${label} Advice [D]`,
        followUps: ["What is the top rotation for this field?", "What is this field's crop history?"],
      };
    }

    if (/(history|story|past|previous)/.test(q)) {
      const hist = pack.story
        .slice(-8)
        .map((s) => `${s.year}: ${s.crop ? cropName(s.crop) : "Fallow"} (clear obs: ${s.clear_obs} [O])`)
        .join("\n• ");
      return {
        text: `Observed NASA HLS 30 m history for ${label} (${pack.field.interior_pixels} interior pixels [O]):\n• ${hist}`,
        sourceLabel: `${label} Satellite Story [O/E]`,
        followUps: ["What is the top rotation for this field?", "What should I measure next?"],
      };
    }

    if (/(top|best|recommend|alternative|option|rank|water|ryi)/.test(q) && topAlts.length > 0) {
      const lines = topAlts.map((o, i) => {
        const water = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} mm` : "—";
        const badWater =
          o.metrics.bad_year_water_mm?.value != null ? `${o.metrics.bad_year_water_mm.value.toFixed(0)} mm` : "—";
        const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "—";
        const bare =
          o.metrics.cover_days?.value != null
            ? `${Math.max(0, (365 * 3 - o.metrics.cover_days.value) / 30.4375).toFixed(1)} mo`
            : "—";
        return `${i + 1}. ${optionName(o)} — Grade ${o.grade} | Water ${water} [D] | Bad-year ${badWater} [D] | Bare soil ${bare} [D] | RYI ${ryi} [D]`;
      });
      return {
        text:
          `Top 3 balanced rotation alternatives for ${label}` +
          (currentOpt ? ` (vs. Current: ${optionName(currentOpt)})` : "") +
          `:\n${lines.join("\n")}\n\nNote: ${pack.advice.measure_next}`,
        sourceLabel: `${label} Rotation Ranking [D]`,
        followUps: ["Why is the observational neighbour witness OFF?", "What should I measure next?"],
      };
    }

    // General summary of the active field
    return {
      text: summarizeFieldPack(pack, ctx.fieldNumberLabel),
      sourceLabel: `${label} Live Pack [O/D/E]`,
      followUps: ["What is the top rotation for this field?", "What should I measure next?", "What is this field's crop history?"],
    };
  }

  // 3. Score against KNOWLEDGE_BASE
  let bestEntry: KnowledgeEntry | null = null;
  let bestScore = 0;

  for (const entry of KNOWLEDGE_BASE) {
    let score = 0;
    for (const kw of entry.keywords) {
      if (q.includes(kw)) {
        score += kw.includes(" ") ? 3 : 2;
      }
    }
    if (score > bestScore) {
      bestScore = score;
      bestEntry = entry;
    }
  }

  if (bestEntry && bestScore > 0) {
    return {
      text: bestEntry.answer,
      sourceLabel: bestEntry.sourceLabel,
      followUps: bestEntry.followUps,
    };
  }

  // 4. Fallback contextual response
  const pageHint = pack
    ? `You are currently viewing ${ctx.fieldNumberLabel ? `Field ${ctx.fieldNumberLabel}` : "a field"}. You can ask me to summarize this field, list its top rotations, or explain its sensitivity.`
    : `You are on the '${ctx.page}' page. You can ask about the Three Witnesses, Evidence Grades A–D, SSURGO soil TAW, winter wheat calibration, or global climate assessment.`;

  return {
    text: `I did not find an exact topic match for "${query.trim()}". ${pageHint}`,
    sourceLabel: "FieldWitness Context Assistant",
    followUps: pack
      ? ["Summarize this field", "What is the top rotation for this field?", "How do the three witnesses work?"]
      : ["What is FieldWitness?", "How do the three witnesses work?", "What soil data is used?"],
  };
}
