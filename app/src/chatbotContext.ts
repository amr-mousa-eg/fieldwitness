import { fieldNumber } from "./fields";
import type { LiveClimateProfile } from "./liveClimateApi";
import { getLocale, type Locale } from "./locale";
import type { Priorities } from "./rank";
import { cropName, optionName } from "./strings";
import type { FieldCalendar, FieldPack, FieldScenarios, RegionHindcast, RegionIndex } from "./types";

export interface ChatContextSnapshot {
  page: string;
  regionId: string;
  fieldId?: string;
  fieldNumberLabel?: string | null;
  fieldPack?: FieldPack | null;
  fieldCalendar?: FieldCalendar | null;
  fieldScenarios?: FieldScenarios | null;
  priorities?: Priorities | null;
  hindcast?: RegionHindcast | null;
  liveProfile?: LiveClimateProfile | null;
  locale?: Locale;
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

// Pub/sub store publishing live active page/field state to the chatbot.
export interface LiveChatStoreState {
  fieldPack: FieldPack | null;
  fieldCalendar: FieldCalendar | null;
  fieldScenarios: FieldScenarios | null;
  priorities: Priorities | null;
  hindcast: RegionHindcast | null;
  liveProfile: LiveClimateProfile | null;
}

const liveState: LiveChatStoreState = {
  fieldPack: null,
  fieldCalendar: null,
  fieldScenarios: null,
  priorities: null,
  hindcast: null,
  liveProfile: null,
};

type StateListener = (s: LiveChatStoreState) => void;
const stateListeners = new Set<StateListener>();

function emitState(): void {
  const snapshot: LiveChatStoreState = { ...liveState };
  for (const listener of stateListeners) {
    listener(snapshot);
  }
}

export function setActiveFieldPack(pack: FieldPack | null): void {
  liveState.fieldPack = pack;
  if (!pack) {
    liveState.fieldCalendar = null;
    liveState.fieldScenarios = null;
  }
  emitState();
}

export function setActiveFieldCalendar(calendar: FieldCalendar | null): void {
  liveState.fieldCalendar = calendar;
  emitState();
}

export function setActiveFieldScenarios(scenarios: FieldScenarios | null): void {
  liveState.fieldScenarios = scenarios;
  emitState();
}

export function setActivePriorities(priorities: Priorities | null): void {
  liveState.priorities = priorities;
  emitState();
}

export function setActiveHindcast(hindcast: RegionHindcast | null): void {
  liveState.hindcast = hindcast;
  emitState();
}

export function setActiveLiveClimateProfile(profile: LiveClimateProfile | null): void {
  liveState.liveProfile = profile;
  emitState();
}

export function getActiveFieldPack(): FieldPack | null {
  return liveState.fieldPack;
}

export function getLiveChatState(): LiveChatStoreState {
  return { ...liveState };
}

export function subscribeActiveFieldPack(listener: (pack: FieldPack | null) => void): () => void {
  const wrapped: StateListener = (s) => listener(s.fieldPack);
  stateListeners.add(wrapped);
  return () => {
    stateListeners.delete(wrapped);
  };
}

export function subscribeLiveChatState(listener: StateListener): () => void {
  stateListeners.add(listener);
  return () => {
    stateListeners.delete(listener);
  };
}

export const KNOWLEDGE_BASE: KnowledgeEntry[] = [
  {
    id: "overview",
    title: "What is FieldWitness?",
    keywords: ["what is", "fieldwitness", "about", "project", "nasa", "space apps", "overview", "purpose", "help"],
    answer:
      "FieldWitness is a crop-rotation decision-support tool built for NASA Space Apps Challenge 2026 ('Field Shift: Adapting Farms with NASA Data'). For 200 pilot fields in western Kansas (MGRS tile `T14SLH`), it reconstructs 12 years of NASA HLS 30 m satellite history [O/D], runs a FAO-56 soil-water balance calibrated to the field's own past (ABC) [D], evaluates 3-season rotations, and grades the evidence A–D.",
    sourceLabel: "Project Overview [O/D/E]",
    followUps: ["How do the three witnesses work?", "How are evidence grades A–D assigned?", "What are the project's honest limits?"],
  },
  {
    id: "witnesses",
    title: "The Three Witnesses",
    keywords: ["witness", "witnesses", "three", "physics", "own past", "abc", "neighbour", "neighbor", "doubleml", "trials", "k-state", "colby", "circuit breaker"],
    answer:
      "Every rotation option is evaluated by three independent witnesses:\n1) **Physics (Witness 1)**: FAO-56 dual crop coefficient root-zone water balance forced by NASA POWER daily meteorology [D].\n2) **Field's Own Past (Witness 2)**: Approximate Bayesian Computation (ABC) calibrating physics against 12 years of NASA HLS 30 m NDVI [D].\n3) **Neighbours / Trials (Witness 3)**: Observational DoubleML contrasts failed balance/placebo checks (0/92 primary and 0/32 matched passed), so the observational witness stays **OFF** via our safety circuit breaker. In shipped Kansas demo packs grades top out at B; the pipeline now also supports 30-year K-State Colby trial benchmarks [E] to unlock Grade A on full pack rebuild.",
    sourceLabel: "Three Witnesses Framework [D/E]",
    followUps: ["Why is the observational neighbour witness OFF?", "How does Grade A work?", "What soil data is used?"],
  },
  {
    id: "grades",
    title: "Evidence Grades A–D",
    keywords: ["grade", "grades", "a-d", "grade a", "grade b", "grade c", "grade d", "evidence", "credibility", "threshold"],
    answer:
      "Evidence grades summarize witness agreement and input quality:\n• **Grade A**: Physics and external validation (neighbours or K-State agronomic trials [E]) agree on sign with overlapping 90% intervals, ABC credibility >= 0.60, and 0 key inputs tagged [A]. (Shipped demo packs currently top out at B pending full pack rebuild.)\n• **Grade B**: At least two witnesses agree (Physics + Own Past credibility >= 0.60).\n• **Grade C**: Only one witness supports the option, or witnesses disagree.\n• **Grade D**: More than half of key inputs are assumptions [A].\nNote: Empirical hindcast testing showed Grade B vs D CRPS difference did not reach significance (95% CI [-3.28, +14.32]).",
    sourceLabel: "Grading Rules [A/D/E]",
    followUps: ["What do tags [O], [D], [E], [A] mean?", "What is ABC credibility?", "Why does FieldWitness not predict profit?"],
  },
  {
    id: "tags",
    title: "Data Source Tags [O, D, E, A]",
    keywords: ["tag", "tags", "[o]", "[d]", "[e]", "[a]", "badge", "source", "provenance", "legend"],
    answer:
      "Every number in FieldWitness carries a provenance tag:\n• **[O] Observed**: Direct satellite or ground measurements (NASA HLS 30 m interior pixels).\n• **[D] Derived**: Outputs of our models, ABC calibration, or FAO-56 water balance.\n• **[E] External**: Published third-party datasets or peer-reviewed parameters (NASA POWER, USDA CSB, USDA-NRCS SSURGO, SoilGrids 2.0, FAO-56, K-State trials).\n• **[A] Assumption**: Team choices or placeholders (priority weights, sowing-date offsets, 150 mm baseline TAW prior).",
    sourceLabel: "Data Provenance Standard",
    followUps: ["What soil data is used?", "How accurate is season detection?", "How are evidence grades A–D assigned?"],
  },
  {
    id: "soil",
    title: "Soil Water Capacity (SSURGO & SoilGrids)",
    keywords: ["soil", "taw", "ssurgo", "soilgrids", "aws", "water holding", "silt loam", "texture", "clay", "sand"],
    answer:
      "FieldWitness integrates two soil sources:\n• **USDA-NRCS SSURGO [E]**: Empirical Available Water Storage (AWS) across 198 surveyed Kansas pilot fields (Keith/Richfield/Ulysses silt loams) has a median of **282.1 mm** (vs 142 mm simulated median / 150 mm [A] prior). The pipeline includes `ssurgo_taw.py` and `--taw-source ssurgo` for pack rebuilds.\n• **ISRIC SoilGrids 2.0 (250 m) [E]**: Used for global soil context, texture, and live non-US queries on `Add My Field`.",
    sourceLabel: "USDA-NRCS SSURGO & SoilGrids [E]",
    followUps: ["How does winter wheat phenology work?", "What is the global climate lookup?"],
  },
  {
    id: "wheat",
    title: "Winter Wheat & Cross-Calendar Phenology",
    keywords: ["wheat", "winter wheat", "phenology", "heading", "doy", "baseline", "b1", "b2", "sorghum", "maize", "corn"],
    answer:
      "Winter wheat covers **31.4%** of the Kansas pilot tile (`T14SLH`). Uncalibrated FAO-56 Idaho defaults caused a +36.0 d median heading lag (58.9 d MAE). We calibrated a Kansas High Plains profile (`ks_calibrated_kstate`: `[160, 70, 40, 25]` days, DOY 140–150 heading) from K-State Extension MF587 & Kansas Mesonet GDD priors [E], and extended `t73_baselines.py` to concatenate 730 days of cross-calendar NASA POWER weather across all 197 winter wheat seasons.",
    sourceLabel: "K-State Phenology & Hindcast Baselines [E/D]",
    followUps: ["What are the project's honest limits?", "What is the 3D farm view?"],
  },
  {
    id: "honesty",
    title: "Honest Limits & Hindcast Skill",
    keywords: ["limit", "limits", "honest", "hindcast", "accuracy", "spearman", "coverage", "season detection", "error", "skill", "caveat"],
    answer:
      "FieldWitness reports all negative and mixed validation results openly:\n• **Season detection**: 78.3% accuracy (188/240 held-out field-seasons vs 90.0% target).\n• **Hindcast skill** (cut-off 2021-12-31, 2022–2024): Paired canopy integral Spearman ρ = 0.264 (0.255 overall n=463); 90% interval coverage is 35.0% (30.9% n=463) for canopy integral and 9.0% for cover days.\n• **Observational neighbours**: 0 of 32 matched contrasts passed diagnostics (kept OFF).\n• **No yield mass or profit forecasts**: Only dimensionless RYI (0–1), water use (mm), and bare-soil risk.",
    sourceLabel: "Pre-Registered Hindcast & Audit [D/E]",
    followUps: ["Why does FieldWitness not predict profit?", "How do the three witnesses work?"],
  },
  {
    id: "scope",
    title: "Why No Dollar Profit or Yield Mass Claims",
    keywords: ["profit", "dollar", "$", "money", "price", "income", "yield"],
    answer:
      "FieldWitness deliberately does not predict dollar profit, commodity prices, or harvest mass per hectare. A 30 m satellite pixel cannot observe local grain prices, fertilizer bills, or harvest moisture. Instead, we report **Relative Yield Index (RYI, 0–1 dimensionless water-stress index) [D]**, **water use (mm)**, **bad-year tail water (CVaR10, mm)**, and **bare-soil exposure months [D]**.",
    sourceLabel: "Scientific Scope & Guardrails",
    followUps: ["What are the project's honest limits?", "What do tags [O], [D], [E], [A] mean?"],
  },
  {
    id: "global",
    title: "Global Live Climate & Physics (Add My Field)",
    keywords: ["global", "add field", "add my field", "world", "outside kansas", "coordinates", "lat", "lon", "power api", "eto", "aridity"],
    answer:
      "On **Add My Field**, any global coordinate runs an on-demand 3-year **NASA POWER Daily Meteorology API (2021–2023)** [E] + **live USDA SSURGO / ISRIC SoilGrids 2.0 soil AWC** [E] + **in-browser FAO-56 daily water balance [D]** across climate-adapted rotations, honoring your irrigation budget and excluded crops.",
    sourceLabel: "Global Live Climate & FAO-56 Connector [D/E]",
    followUps: ["What soil data is used?", "How do I print a field dossier?"],
  },
  {
    id: "print",
    title: "Printable 1-Page Field Dossier & 3D View",
    keywords: ["print", "pdf", "dossier", "report", "export", "3d", "farm view", "what-if", "slider", "scenario", "calendar", "hazard", "frost", "heat"],
    answer:
      "Every field page includes:\n• **Print Field Dossier**: Formats a 1-page A4 report via `@media print`.\n• **Crop & Vulnerability Calendar**: Monthly observed bare-soil share [O] and heat, frost, water-stress, and extreme-rain hazards [D].\n• **Interactive 3D Farm & Soil View**: Weekly canopy, root-zone water depletion, and temperature/rain scenarios.",
    sourceLabel: "Frontend Deliverables [D]",
    followUps: ["What is FieldWitness?", "How do the three witnesses work?"],
  },
];

const KNOWLEDGE_BASE_AR: KnowledgeEntry[] = [
  {
    id: "overview",
    title: "ما هو FieldWitness؟",
    keywords: ["ما هو", "نظرة", "المشروع", "تطبيق", "نبذة", "فكرة", "ناسا", "fieldwitness", "what is"],
    answer:
      "تطبيق FieldWitness هو أداة دعم قرار للدورات الزراعية طُوّرت لتحدي NASA Space Apps 2026. يغطي التطبيق 200 حقل تجريبي في غرب كانساس (الشريحة `T14SLH`)، ويعيد بناء 12 عامًا من صور NASA HLS بدقة 30 م [O/D]، ويشغّل موازنة المياه FAO-56 المعايَرة بتاريخ الحقل (ABC) [D] لتقييم دورات من 3 مواسم ومنح درجات الدليل A–D.",
    sourceLabel: "نظرة عامة على المشروع [O/D/E]",
    followUps: ["كيف يعمل الشهود الثلاثة؟", "كيف تُحدد درجات الدليل A–D؟", "ما هي الحدود الصريحة للمشروع؟"],
  },
  {
    id: "witnesses",
    title: "نظام الشهود الثلاثة",
    keywords: ["شاهد", "شهود", "الشهود", "فيزياء", "الماضي", "جيران", "الجيران", "كولبي", "معايرة"],
    answer:
      "يُقيَّم كل خيار دورة زراعية عبر ثلاثة شهود مستقلين:\n1) **الفيزياء (الشاهد 1)**: موازنة المياه اليومية FAO-56 في منطقة الجذور المدفوعة بطقس NASA POWER [D].\n2) **ماضي الحقل (الشاهد 2)**: معايرة بايزية تقريبية (ABC) تطابق الفيزياء مع 12 عامًا من صور NASA HLS 30 م [D].\n3) **الجيران / التجارب (الشاهد 3)**: مقارنات الجيران الملاحظية متوقفة **OFF** بقاطع أمان آلي بعد فشل فحوصات التوازن (0/92 و0/32)؛ لذا تتوقف الدرجات الحالية عند B، مع دعم تجارب محطة كولبي الممتدة 30 عامًا [E] لفتح الدرجة A عند إعادة بناء الحزم.",
    sourceLabel: "إطار الشهود الثلاثة [D/E]",
    followUps: ["لماذا شاهد الجيران متوقف؟", "كيف تُحدد درجات الدليل A–D؟", "ما بيانات التربة المستخدمة؟"],
  },
  {
    id: "grades",
    title: "درجات الدليل A–D",
    keywords: ["درجة", "درجات", "الدليل", "a-d", "مصداقية", "تقييم", "grade"],
    answer:
      "تلخص درجات الدليل مستوى اتفاق الشهود وجودة المدخلات:\n• **الدرجة A**: اتفاق الفيزياء مع التحقق الخارجي ومصداقية ABC ≥ 0.60 دون مدخلات افتراضية أساسية [A] (تتوقف الحزم الشحنية عند B حاليًا).\n• **الدرجة B**: اتفاق شاهدين على الأقل (الفيزياء + ماضي الحقل بمصداقية ≥ 0.60).\n• **الدرجة C**: دعم شاهد واحد فقط أو تعارض بين الشهود.\n• **الدرجة D**: اعتماد أكثر من نصف المدخلات على افتراضات [A].\nملاحظة: في الاختبار التراجعي لم يثبت إحصائيًا تفوق الدرجة B على D في الدقة (فاصل ثقة 95% [-3.28، +14.32]).",
    sourceLabel: "قواعد الدرجات [A/D/E]",
    followUps: ["ما معنى الحروف [O] و[D] و[E] و[A]؟", "ما هي الحدود الصريحة للمشروع؟"],
  },
  {
    id: "tags",
    title: "وسوم مصادر البيانات [O، D، E، A]",
    keywords: ["وسم", "وسوم", "حروف", "مصدر", "رموز", "tag", "provenance"],
    answer:
      "يحمل كل رقم في FieldWitness رمز مصدر يوضح طبيعته:\n• **[O] مرصود**: قياسات قمر صناعي أو أرضية مباشرة (بكسلات NASA HLS الداخلية بدقة 30 م).\n• **[D] مُشتق**: مخرجات نموذج الفيزياء FAO-56 ومعايرة ABC.\n• **[E] خارجي**: بيانات رسمية من خارج التطبيق (NASA POWER، USDA CSB، SSURGO، SoilGrids 2.0، وتجارب كولبي).\n• **[A] افتراض**: خيارات تصميمية أو قيم مبدئية (مثل أوزان الأولويات وافتراض 150 ملم للتربة).",
    sourceLabel: "معيار توثيق المصادر",
    followUps: ["ما بيانات التربة المستخدمة؟", "ما هي الحدود الصريحة للمشروع؟"],
  },
  {
    id: "soil",
    title: "السعة المائية للتربة (SSURGO وSoilGrids)",
    keywords: ["تربة", "التربة", "سعة", "ssurgo", "soilgrids", "طين", "رمل", "taw", "aws"],
    answer:
      "يدمج FieldWitness مصدرين رئيسيين للتربة:\n• **USDA-NRCS SSURGO [E]**: وسيط السعة المائية المتاحة عبر 198 حقلًا في كانساس يبلغ **282.1 ملم** (مقابل 142 ملم وسيط المحاكاة الأساسي المبني على افتراض 150 ملم [A]).\n• **ISRIC SoilGrids 2.0 (250 م) [E]**: يُستخدم للسياق العالمي والقوام والاستعلامات الحية في صفحة \"أضف حقلي\".",
    sourceLabel: "بيانات التربة SSURGO وSoilGrids [E]",
    followUps: ["كيف يعمل القمح الشتوي؟", "ما هو التقييم المناخي العالمي؟"],
  },
  {
    id: "wheat",
    title: "فينولوجيا القمح الشتوي عبر السنوات",
    keywords: ["قمح", "القمح", "شتوي", "ذرة", "فينولوجيا", "خط الأساس", "wheat"],
    answer:
      "يشكّل القمح الشتوي **31.4%** من حقول كانساس التجريبية. أظهرت معاملات أيداهو غير المعايَرة تأخرًا بنحو 36 يومًا في ذروة الخضرة، فجرى توثيق ملف كانساس المعاير من إرشاد K-State MF587 ومراصد Mesonet [E] وتمديد الاختبار التراجعي عبر سنتين تقويميتين ليشمل 197 موسم قمح شتوي.",
    sourceLabel: "فينولوجيا القمح وخطوط الأساس [E/D]",
    followUps: ["ما هي الحدود الصريحة للمشروع؟", "كيف يعمل الشهود الثلاثة؟"],
  },
  {
    id: "honesty",
    title: "الحدود الصريحة ومهارة الاختبار التراجعي",
    keywords: ["حدود", "الحدود", "صريحة", "دقة", "تراجعي", "خطأ", "عيوب", "سلبيات", "honest", "limits"],
    answer:
      "يعرض FieldWitness جميع النتائج السلبية والمحدودة بشفافية:\n• **كشف المواسم**: دقة 78.3% (188/240 موسمًا مقابل الهدف 90.0%).\n• **التقييم التراجعي** (تجميد 2021-12-31، اختبار 2022–2024): ارتباط سبيرمان ρ = 0.264، وتغطية نطاق 90% تبلغ 35.0% لمجموع الخضرة و9.0% لأيام الغطاء.\n• **شاهد الجيران الملاحظي**: اجتاز 0 من 32 مقارنة فحوصات التوازن فبقي موقَفًا.\n• **دون توقع أرباح أو أطنان**: يكتفي بمؤشر الإنتاجية النسبي RYI (0–1) واستهلاك المياه ومخاطر التربة العارية.",
    sourceLabel: "الاختبار التراجعي والمراجعة العلمية [D/E]",
    followUps: ["لماذا لا يتنبأ بالأرباح أو الأطنان؟", "كيف يعمل الشهود الثلاثة؟"],
  },
  {
    id: "scope",
    title: "لماذا لا توجد توقعات للربح المالي أو وزن المحصول؟",
    keywords: ["ربح", "أرباح", "مال", "سعر", "أسعار", "طن", "أطنان", "إنتاجية", "profit", "price"],
    answer:
      "يمتنع FieldWitness عمدًا عن التنبؤ بالأرباح المالية أو أسعار الحبوب أو الأوزان بالطن للهكتار، لأن صور الأقمار الصناعية لا ترى الأسعار المحلية أو تكاليف الأسمدة ورطوبة الحصاد. بدلًا من ذلك يعرض **مؤشر الإنتاجية النسبي (RYI من 0 إلى 1) [D]**، و**استهلاك المياه (ملم)**، و**مياه سنة الجفاف (CVaR10)**، و**أشهر التربة العارية [D]**.",
    sourceLabel: "نطاق المشروع العلمي",
    followUps: ["ما هي الحدود الصريحة للمشروع؟", "ما معنى الحروف [O] و[D] و[E] و[A]؟"],
  },
  {
    id: "global",
    title: "التقييم المناخي العالمي (أضف حقلي)",
    keywords: ["عالمي", "أضف حقلي", "احداثيات", "إحداثيات", "خارج كانساس", "مناخ", "مصر", "القاهرة"],
    answer:
      "في صفحة **أضف حقلي** يمكن لأي إحداثي في العالم تشغيل جلب آلي لبيانات **NASA POWER اليومية (2021–2023)** [E] مع **بيانات تربة SSURGO أو SoilGrids 2.0 الحية** [E] وتشغيل **موازنة المياه اليومية FAO-56 [D]** مباشرة في المتصفح مع مراعاة ميزانية الريّ والمحاصيل المستبعدة.",
    sourceLabel: "موصل المناخ العالمي FAO-56 [D/E]",
    followUps: ["ما بيانات التربة المستخدمة؟", "ما هو FieldWitness؟"],
  },
  {
    id: "print",
    title: "ملف الطباعة والعرض ثلاثي الأبعاد والتقويم",
    keywords: ["طباعة", "ملف", "تقرير", "ثلاثي", "3d", "تقويم", "مزرعة", "صقيع", "حرارة", "سيناريو"],
    answer:
      "تتضمن صفحة كل حقل:\n• **طباعة ملف الحقل**: تقرير قرار منسق في صفحة A4 واحدة.\n• **التقويم وحساسية الطقس**: التربة العارية الشهرية المرصودة [O] ومخاطر الحرارة والصقيع والإجهاد المائي والأمطار الشديدة [D].\n• **الحقل ثلاثي الأبعاد ومنشئ الدورات**: متابعة أسبوعية للغطاء النباتي ورطوبة التربة واختبارات تغيّر الطقس.",
    sourceLabel: "مزايا الواجهة التفاعلية [D]",
    followUps: ["ما هو FieldWitness؟", "كيف يعمل الشهود الثلاثة؟"],
  },
];

const MONTHS_SHORT_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_SHORT_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];

function summarizeFieldPack(ctx: ChatContextSnapshot, isAr = false): string {
  const pack = ctx.fieldPack!;
  const loc: Locale = isAr ? "ar" : "en";
  const months = isAr ? MONTHS_SHORT_AR : MONTHS_SHORT_EN;
  const numLabel = ctx.fieldNumberLabel
    ? isAr
      ? `الحقل ${ctx.fieldNumberLabel}`
      : `Field ${ctx.fieldNumberLabel}`
    : isAr
      ? `الحقل ${pack.field.field_id.slice(0, 8)}`
      : `Field ${pack.field.field_id.slice(0, 8)}`;
  const cred = pack.credibility.value != null
    ? `${(pack.credibility.value * 100).toFixed(0)}%`
    : isAr
      ? "غير قابل للتقييم"
      : "not assessable";
  const currentOpt = pack.options.find((o) => o.option_id === "current");
  const topAlts = pack.options
    .filter((o) => o.option_id !== "current")
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 3);
  const recentHistory = pack.story
    .slice(-5)
    .map((s) => `${s.year}: ${s.crop ? cropName(s.crop, loc) : isAr ? "بور" : "Fallow"}`)
    .join(" ← ");

  if (isAr) {
    const altLines = topAlts
      .map((o, idx) => {
        const w = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} ملم` : "غير متاح";
        const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "غير متاح";
        return `  #${idx + 1}: ${optionName(o, "ar")} (درجة ${o.grade}، المياه ${w}، RYI ${ryi})`;
      })
      .join("\n");

    let extra = "";
    if (ctx.fieldCalendar) {
      const bareMonths = ctx.fieldCalendar.bare_observed
        .filter((m) => !m.insufficient && (m.bare_share?.value ?? 0) >= 0.5)
        .map((m) => `${months[m.month - 1]} (${Math.round((m.bare_share?.value ?? 0) * 100)}%)`);
      if (bareMonths.length > 0) {
        extra += `\n• أشهر التربة العارية المرتفعة [O]: ${bareMonths.join("، ")}`;
      }
      const hazards = ctx.fieldCalendar.vulnerability
        .slice(0, 3)
        .map((v) => {
          const ws = Math.max(...(v.shares.water_stress?.values.map((x) => x ?? 0) ?? [0]));
          const hs = Math.max(...(v.shares.heat?.values.map((x) => x ?? 0) ?? [0]));
          return `${cropName(v.crop, "ar")} (ذروة الإجهاد المائي ${Math.round(ws * 100)}%، الحرارة ${Math.round(hs * 100)}%)`;
        });
      if (hazards.length > 0) {
        extra += `\n• ذروة حساسية المحاصيل [D]: ${hazards.join("؛ ")}`;
      }
    }

    if (ctx.fieldScenarios && ctx.fieldScenarios.scenarios.length > 0) {
      const baseTop = Object.entries(
        ctx.fieldScenarios.scenarios.find((s) => s.scenario_id === ctx.fieldScenarios!.baseline_id)?.ranks ?? {},
      ).find(([, r]) => r === 1)?.[0];
      const stress = ctx.fieldScenarios.scenarios.find((s) => s.dt_c >= 2 && s.dp_pct <= -20);
      const stressTop = stress ? Object.entries(stress.ranks).find(([, r]) => r === 1)?.[0] : undefined;
      if (baseTop && stressTop) {
        extra +=
          baseTop === stressTop
            ? `\n• حساسية الطقس (+2 °م، -20% مطر) [D]: الخيار الأول يبقى ثابتًا.`
            : `\n• حساسية الطقس (+2 °م، -20% مطر) [D]: يتحوّل الخيار الأول من ${baseTop} إلى ${stressTop}.`;
      }
    }

    return (
      `سياق الحقل النشط — ${numLabel} (${pack.field.area_ha.toFixed(1)} هكتار، ${pack.field.interior_pixels} بكسل داخلي 30 م [O]، حتى ${pack.data_as_of}):\n` +
      `• التاريخ المحصولي الأخير: ${recentHistory || "غير متاح"}\n` +
      `• مصداقية الشاهد 2 (ABC): ${cred} [D]\n` +
      (currentOpt ? `• الدورة الحالية: ${optionName(currentOpt, "ar")} (درجة ${currentOpt.grade})\n` : "") +
      `• أفضل البدائل المصنفة:\n${altLines}\n` +
      `• الخطوة الموصى بقياسها: ${pack.advice.measure_next}` +
      extra
    );
  }

  const altLines = topAlts
    .map((o, idx) => {
      const w = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} mm` : "N/A";
      const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "N/A";
      return `  #${idx + 1}: ${optionName(o, "en")} (Grade ${o.grade}, Water ${w}, RYI ${ryi})`;
    })
    .join("\n");

  let extra = "";
  if (ctx.fieldCalendar) {
    const bareMonths = ctx.fieldCalendar.bare_observed
      .filter((m) => !m.insufficient && (m.bare_share?.value ?? 0) >= 0.5)
      .map((m) => `${months[m.month - 1]} (${Math.round((m.bare_share?.value ?? 0) * 100)}%)`);
    if (bareMonths.length > 0) {
      extra += `\n• High Observed Bare-Soil Months [O]: ${bareMonths.join(", ")}`;
    }
    const hazards = ctx.fieldCalendar.vulnerability
      .slice(0, 3)
      .map((v) => {
        const ws = Math.max(...(v.shares.water_stress?.values.map((x) => x ?? 0) ?? [0]));
        const hs = Math.max(...(v.shares.heat?.values.map((x) => x ?? 0) ?? [0]));
        return `${cropName(v.crop, "en")} (peak water stress ${Math.round(ws * 100)}%, heat ${Math.round(hs * 100)}%)`;
      });
    if (hazards.length > 0) {
      extra += `\n• Crop Vulnerability Peaks [D]: ${hazards.join("; ")}`;
    }
  }

  if (ctx.fieldScenarios && ctx.fieldScenarios.scenarios.length > 0) {
    const baseTop = Object.entries(
      ctx.fieldScenarios.scenarios.find((s) => s.scenario_id === ctx.fieldScenarios!.baseline_id)?.ranks ?? {},
    ).find(([, r]) => r === 1)?.[0];
    const stress = ctx.fieldScenarios.scenarios.find((s) => s.dt_c >= 2 && s.dp_pct <= -20);
    const stressTop = stress ? Object.entries(stress.ranks).find(([, r]) => r === 1)?.[0] : undefined;
    if (baseTop && stressTop) {
      extra +=
        baseTop === stressTop
          ? `\n• Weather Sensitivity (+2 °C, -20% rain) [D]: Top choice stays stable.`
          : `\n• Weather Sensitivity (+2 °C, -20% rain) [D]: Top choice shifts from ${baseTop} to ${stressTop}.`;
    }
  }

  if (ctx.priorities) {
    const activePrio = Object.entries(ctx.priorities)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
    extra += `\n• Active Priority Weights [A]: ${activePrio}`;
  }

  return (
    `Active Field Context — ${numLabel} (${pack.field.area_ha.toFixed(1)} ha, ${pack.field.interior_pixels} interior 30 m pixels [O], as of ${pack.data_as_of}):\n` +
    `• Recent Crop History: ${pack.story.slice(-5).map((s) => `${s.year}: ${s.crop ? cropName(s.crop, "en") : "Fallow"}`).join(" -> ") || "N/A"}\n` +
    `• ABC Own-Past Credibility: ${cred} [D]\n` +
    (currentOpt ? `• Current Rotation: ${optionName(currentOpt, "en")} (Grade ${currentOpt.grade})\n` : "") +
    `• Top Ranked Alternatives:\n${altLines}\n` +
    `• Sensitivity & Next Step: ${pack.advice.measure_next}` +
    extra
  );
}

function summarizeLiveProfile(prof: LiveClimateProfile, isAr = false): string {
  const top = prof.recommendedRotations[0];
  if (isAr) {
    return (
      `التقييم العالمي النشط (${prof.latitude.toFixed(4)}, ${prof.longitude.toFixed(4)}):\n` +
      `• المنطقة المناخية: ${prof.climateZone} (${prof.source}، ${prof.yearsEvaluated} سنوات)\n` +
      `• المطر السنوي: ${prof.annualPrecipitationMm} ملم | ET0: ${prof.annualEtoMm} ملم | الجفاف: ${prof.aridityIndex}\n` +
      `• سياق التربة: ${prof.soilContext.source} (${prof.soilContext.estimatedAweMm} ملم AWS ${prof.soilContext.tag})\n` +
      (top ? `• أفضل دورة محاكاة (${prof.simulationMode}): ${top.name} — RYI ${top.ryi}، المياه ${top.waterUseMm} ملم، التربة العارية ${top.bareMonths} شهر` : "")
    );
  }
  return (
    `Active Global Evaluation (${prof.latitude.toFixed(4)}, ${prof.longitude.toFixed(4)}):\n` +
    `• Climate Zone: ${prof.climateZone} (${prof.source}, ${prof.yearsEvaluated} yr)\n` +
    `• Annual Rain: ${prof.annualPrecipitationMm} mm | Annual ET0: ${prof.annualEtoMm} mm | Aridity: ${prof.aridityIndex}\n` +
    `• Soil Context: ${prof.soilContext.source} (${prof.soilContext.estimatedAweMm} mm AWS ${prof.soilContext.tag})\n` +
    (top ? `• Top Simulated Rotation (${prof.simulationMode}): ${top.name} — RYI ${top.ryi}, Water ${top.waterUseMm} mm, Bare ${top.bareMonths} mo` : "")
  );
}

function summarizeHindcast(h: RegionHindcast, isAr = false): string {
  const canopy = h.rows.filter((r) => r.mode === "forecast" && r.metric === "canopy_integral");
  const lines = canopy.map((r) => `${r.method}: CRPS=${r.scores.crps?.toFixed(2) ?? "N/A"} (n=${r.n})`);
  return isAr
    ? `لوحة الاختبار التراجعي (${h.region_id}، تاريخ القطع ${h.cutoff}): ${lines.join("؛ ")}`
    : `Active Hindcast Scoreboard (${h.region_id}, cutoff ${h.cutoff}): ${lines.join("; ")}`;
}

export function buildSystemPrompt(ctx: ChatContextSnapshot): string {
  const baseFacts = KNOWLEDGE_BASE.map((k) => `- ${k.title}: ${k.answer}`).join("\n");
  const sections: string[] = [];

  if (ctx.fieldPack) {
    sections.push(`CURRENTLY VIEWED FIELD:\n${summarizeFieldPack(ctx, false)}`);
  } else {
    sections.push(`CURRENT PAGE: ${ctx.page} (Region: ${ctx.regionId}). No pilot field pack open.`);
  }

  if (ctx.liveProfile) {
    sections.push(`GLOBAL ADD-MY-FIELD EVALUATION:\n${summarizeLiveProfile(ctx.liveProfile, false)}`);
  }

  if (ctx.hindcast) {
    sections.push(summarizeHindcast(ctx.hindcast, false));
  }

  const activeLocale = ctx.locale ?? getLocale();
  const langRule =
    activeLocale === "ar"
      ? "4. Respond in clear Modern Standard Arabic matching the user's interface language.\n\n"
      : "4. Respond in the same language as the user's question (English or Arabic).\n\n";

  return (
    "You are the FieldWitness Scientific Assistant for NASA Space Apps Challenge 2026 ('Field Shift: Adapting Farms with NASA Data').\n" +
    "Rules:\n" +
    "1. Answer clearly and honestly using the project facts and active field/page context below.\n" +
    "2. Preserve data provenance tags ([O] observed, [D] derived, [E] external, [A] assumption) when quoting metrics.\n" +
    "3. Never invent harvest mass per hectare, dollar profit, commodity prices, or guaranteed outcomes.\n" +
    langRule +
    "PROJECT KNOWLEDGE:\n" +
    baseFacts +
    "\n\n" +
    sections.join("\n\n")
  );
}

export function resolveFieldLabel(pack: FieldPack | null | undefined, index: RegionIndex | null): string | null {
  if (!pack || !index) return null;
  return String(fieldNumber(pack.field.field_id, index.fields));
}

export function answerQuestion(query: string, ctx: ChatContextSnapshot): ChatAnswer {
  const raw = query.trim();
  const q = raw.toLowerCase();
  const hasArabicScript = /[\u0600-\u06FF]/.test(raw);
  const isAr = ctx.locale === "ar" || hasArabicScript;
  const kb = isAr ? KNOWLEDGE_BASE_AR : KNOWLEDGE_BASE;
  const months = isAr ? MONTHS_SHORT_AR : MONTHS_SHORT_EN;

  if (!q) {
    return isAr
      ? {
          text: "اسألني أي سؤال عن FieldWitness: نظام الشهود الثلاثة، أو درجات الدليل A–D، أو التربة (SSURGO)، أو القمح الشتوي، أو اختبارات الطقس، أو الحقل المعروض حاليًا.",
          sourceLabel: "مساعد FieldWitness",
          followUps: ctx.fieldPack
            ? ["لخّص هذا الحقل", "ما أفضل دورة لهذا الحقل؟", "ما أشهر التربة العارية والمخاطر؟"]
            : ["ما هو FieldWitness؟", "كيف يعمل الشهود الثلاثة؟", "ما هي الحدود الصريحة للمشروع؟"],
        }
      : {
          text: "Ask me anything about FieldWitness—how the Three Witnesses work, evidence grades A–D, soil TAW, winter wheat calibration, climate what-ifs, or the field you are currently viewing.",
          sourceLabel: "FieldWitness Assistant",
          followUps: ctx.fieldPack
            ? ["Summarize this field", "What is the top rotation for this field?", "What are the bare soil months and hazards?"]
            : ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
        };
  }

  // 1. Strict scientific scope guardrail (no dollar profit / yield mass / certainty)
  if (/(profit|dollar|\$|income|price|tonnes|bushel|bu\/ac|guarant|ربح|أرباح|مال|سعر|أسعار|طن|أطنان|ضمان)/.test(q)) {
    const scope = kb.find((e) => e.id === "scope")!;
    return {
      text: scope.answer,
      sourceLabel: scope.sourceLabel,
      followUps: scope.followUps,
    };
  }

  // 2. Live global Add-My-Field query when liveProfile is available
  if (ctx.liveProfile && /(global|my field|coordinate|lat|lon|nasa power|rain|eto|deficit|simulated|location|عالمي|احداثي|إحداثي|مناخ|مطر|حقل)/.test(q)) {
    const p = ctx.liveProfile;
    if (isAr) {
      const rots = p.recommendedRotations
        .slice(0, 3)
        .map((r, i) => `• #${i + 1} **${r.name}**: RYI ${r.ryi} [D]، المياه ${r.waterUseMm} ملم (سنة الجفاف ${r.badYearWaterMm} ملم)، التربة العارية ${r.bareMonths} شهر`)
        .join("\n");
      return {
        text:
          `التقييم المناخي العالمي الحي (${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)}):\n` +
          `• **المنطقة المناخية**: ${p.climateZone} (${p.source}، ${p.yearsEvaluated} سنوات)\n` +
          `• **المطر / ET₀ / العجز**: ${p.annualPrecipitationMm} ملم / ${p.annualEtoMm} ملم / ${p.waterDeficitMm} ملم\n` +
          `• **التربة**: ${p.soilContext.source} (${p.soilContext.estimatedAweMm} ملم AWS ${p.soilContext.tag})\n` +
          `**${p.simulationMode}**:\n${rots}`,
        sourceLabel: "ملف التقييم العالمي FAO-56 [D/E]",
        followUps: ["ما بيانات التربة المستخدمة؟", "كيف يعمل الشهود الثلاثة؟"],
      };
    }
    const rots = p.recommendedRotations
      .slice(0, 3)
      .map((r, i) => `• #${i + 1} **${r.name}**: RYI ${r.ryi} [D], Water ${r.waterUseMm} mm (Worst yr ${r.badYearWaterMm} mm), Bare ${r.bareMonths} mo`)
      .join("\n");
    return {
      text:
        `Live Global Field Assessment (${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)}):\n` +
        `• **Climate Zone**: ${p.climateZone} (${p.source}, ${p.yearsEvaluated} yr)\n` +
        `• **Rain / ET₀ / Deficit**: ${p.annualPrecipitationMm} mm / ${p.annualEtoMm} mm / ${p.waterDeficitMm} mm\n` +
        `• **Soil**: ${p.soilContext.source} (${p.soilContext.estimatedAweMm} mm AWS ${p.soilContext.tag})\n` +
        `**In-Browser ${p.simulationMode}**:\n${rots}`,
      sourceLabel: "Live Global FAO-56 Profile [D/E]",
      followUps: ["What soil data is used?", "How do the three witnesses work?"],
    };
  }

  // 3. Active FieldPack-specific queries
  const pack = ctx.fieldPack;
  const asksAboutThisField =
    pack &&
    /(this field|my field|current field|summarize|summary|top option|best option|top rotation|best rotation|recommend|rank|grade|credibility|history|story|water|bare|flip|measure|sensitive|scenario|climate|hazard|frost|heat|calendar|alternative|الحقل|لخص|لخّص|ملخص|أفضل|توصية|ترتيب|درجة|مصداقية|تاريخ|قصة|مياه|تربة عارية|تقويم|مخاطر|صقيع|حرارة|سيناريو|بديل|قياس)/.test(
      q,
    );

  if (pack && asksAboutThisField) {
    const loc: Locale = isAr ? "ar" : "en";
    const label = ctx.fieldNumberLabel
      ? isAr
        ? `الحقل ${ctx.fieldNumberLabel}`
        : `Field ${ctx.fieldNumberLabel}`
      : isAr
        ? `الحقل ${pack.field.field_id.slice(0, 8)}`
        : `Field ${pack.field.field_id.slice(0, 8)}`;
    const topAlts = pack.options
      .filter((o) => o.option_id !== "current")
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 3);
    const currentOpt = pack.options.find((o) => o.option_id === "current");

    if (/(bare|hazard|frost|heat|calendar|vulnerable|عارية|مخاطر|صقيع|حرارة|تقويم|حساسية)/.test(q) && ctx.fieldCalendar) {
      const bare = ctx.fieldCalendar.bare_observed
        .filter((m) => !m.insufficient && (m.bare_share?.value ?? 0) >= 0.4)
        .map((m) => `${months[m.month - 1]} (${Math.round((m.bare_share?.value ?? 0) * 100)}%)`)
        .join(isAr ? "، " : ", ");
      const vulns = ctx.fieldCalendar.vulnerability
        .slice(0, 3)
        .map((v) => {
          const ws = Math.max(...(v.shares.water_stress?.values.map((x) => x ?? 0) ?? [0]));
          const ht = Math.max(...(v.shares.heat?.values.map((x) => x ?? 0) ?? [0]));
          return isAr
            ? `${cropName(v.crop, "ar")}: إجهاد مائي حتى ${Math.round(ws * 100)}%، حرارة حتى ${Math.round(ht * 100)}%`
            : `${cropName(v.crop, "en")}: water stress up to ${Math.round(ws * 100)}%, heat up to ${Math.round(ht * 100)}%`;
        })
        .join("\n• ");
      return isAr
        ? {
            text:
              `ملخص التقويم والحساسية لـ ${label}:\n` +
              `• **أشهر التربة العارية (≥40% سنوات عارية [O])**: ${bare || "تعرض منخفض طوال السنة"}\n` +
              `• **ذروة إجهاد المحاصيل [D]**:\n• ${vulns || "افتح تبويب التقويم لمراجعة المخططات الشهرية."}`,
            sourceLabel: `تقويم ${label} [O/D]`,
            followUps: ["ما أفضل دورة لهذا الحقل؟", "ما الذي يُنصح بقياسه لاحقًا؟"],
          }
        : {
            text:
              `Calendar & Vulnerability Summary for ${label}:\n` +
              `• **Bare Soil (>=40% years bare [O])**: ${bare || "Low year-round bare exposure"}\n` +
              `• **Crop Stress Peaks [D]**:\n• ${vulns || "Open Calendar tab to inspect monthly charts."}`,
            sourceLabel: `${label} Calendar [O/D]`,
            followUps: ["What is the top rotation for this field?", "What should I measure next?"],
          };
    }

    if (/(measure|flip|sensitive|next|scenario|قياس|تغير|حساسية|تالي|سيناريو)/.test(q)) {
      let scenNote = "";
      if (ctx.fieldScenarios && ctx.fieldScenarios.scenarios.length > 0) {
        const baseTop = Object.entries(
          ctx.fieldScenarios.scenarios.find((s) => s.scenario_id === ctx.fieldScenarios!.baseline_id)?.ranks ?? {},
        ).find(([, r]) => r === 1)?.[0];
        const hotDry = ctx.fieldScenarios.scenarios.find((s) => s.dt_c >= 2 && s.dp_pct <= -20);
        const hdTop = hotDry ? Object.entries(hotDry.ranks).find(([, r]) => r === 1)?.[0] : undefined;
        if (baseTop && hdTop) {
          if (isAr) {
            scenNote =
              baseTop === hdTop
                ? `\n• **اختبار الطقس (+2 °م / −20% مطر) [D]**: يبقى الخيار المتصدر ثابتًا.`
                : `\n• **اختبار الطقس (+2 °م / −20% مطر) [D]**: يتغيّر الخيار #1 إلى ${hdTop}.`;
          } else {
            scenNote =
              baseTop === hdTop
                ? `\n• **+2 °C / −20% rain what-if [D]**: Top-ranked option holds steady.`
                : `\n• **+2 °C / −20% rain what-if [D]**: Rank #1 switches to ${hdTop}.`;
          }
        }
      }
      return isAr
        ? {
            text:
              `بالنسبة إلى **${label}**:\n` +
              `• **القياس التالي الموصى به**: ${pack.advice.measure_next}\n` +
              `• **حساسية تغيّر القرار**: ${pack.advice.counterfactual_flip}\n` +
              `• **احتمال التغيّر**: ${pack.advice.flip_probability.value != null ? `${(pack.advice.flip_probability.value * 100).toFixed(0)}% [D]` : "غير متاح"}` +
              scenNote,
            sourceLabel: `توصيات ${label} [D]`,
            followUps: ["ما أفضل دورة لهذا الحقل؟", "ما تاريخ هذا الحقل؟"],
          }
        : {
            text:
              `For **${label}**:\n` +
              `• **Recommended next measurement**: ${pack.advice.measure_next}\n` +
              `• **Counterfactual flip sensitivity**: ${pack.advice.counterfactual_flip}\n` +
              `• **Flip probability**: ${pack.advice.flip_probability.value != null ? `${(pack.advice.flip_probability.value * 100).toFixed(0)}% [D]` : "N/A"}` +
              scenNote,
            sourceLabel: `${label} Advice [D]`,
            followUps: ["What is the top rotation for this field?", "What is this field's crop history?"],
          };
    }

    if (/(history|story|past|previous|تاريخ|قصة|ماضي|سابق)/.test(q)) {
      const hist = pack.story
        .slice(-8)
        .map((s) =>
          isAr
            ? `${s.year}: ${s.crop ? cropName(s.crop, "ar") : "بور"} (مشاهدات صافية: ${s.clear_obs} [O])`
            : `${s.year}: ${s.crop ? cropName(s.crop, "en") : "Fallow"} (clear obs: ${s.clear_obs} [O])`,
        )
        .join("\n• ");
      return isAr
        ? {
            text: `تاريخ الأقمار الصناعية NASA HLS 30 م لـ **${label}** (${pack.field.interior_pixels} بكسل داخلي [O]):\n• ${hist}`,
            sourceLabel: `قصة ${label} [O/E]`,
            followUps: ["ما أفضل دورة لهذا الحقل؟", "ما الذي يُنصح بقياسه لاحقًا؟"],
          }
        : {
            text: `Observed NASA HLS 30 m history for **${label}** (${pack.field.interior_pixels} interior pixels [O]):\n• ${hist}`,
            sourceLabel: `${label} Satellite Story [O/E]`,
            followUps: ["What is the top rotation for this field?", "What should I measure next?"],
          };
    }

    if (/(top|best|recommend|alternative|option|rank|water|ryi|أفضل|توصية|بديل|خيار|ترتيب|مياه)/.test(q) && topAlts.length > 0) {
      if (isAr) {
        const lines = topAlts
          .map((o, i) => {
            const w = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} ملم` : "غير متاح";
            const by = o.metrics.bad_year_water_mm?.value != null ? `${o.metrics.bad_year_water_mm.value.toFixed(0)} ملم` : "غير متاح";
            const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "غير متاح";
            return `• **#${i + 1} ${optionName(o, "ar")}** — درجة **${o.grade}** | المياه: ${w} (سنة الجفاف: ${by}) [D] | RYI: ${ryi} [D]`;
          })
          .join("\n");
        return {
          text:
            `أعلى الدورات الثلاثية ترتيبًا لـ **${label}** (${pack.field.area_ha.toFixed(1)} هكتار):\n` +
            lines +
            (currentOpt ? `\n• **الدورة الحالية**: ${optionName(currentOpt, "ar")} (درجة ${currentOpt.grade})` : ""),
          sourceLabel: `خيارات ${label} [D/E]`,
          followUps: ["ما الذي يُنصح بقياسه لاحقًا؟", "ما أشهر التربة العارية والمخاطر؟"],
        };
      }
      const lines = topAlts
        .map((o, i) => {
          const w = o.metrics.water_use_mm?.value != null ? `${o.metrics.water_use_mm.value.toFixed(0)} mm` : "N/A";
          const by = o.metrics.bad_year_water_mm?.value != null ? `${o.metrics.bad_year_water_mm.value.toFixed(0)} mm` : "N/A";
          const ryi = o.metrics.ryi?.value != null ? o.metrics.ryi.value.toFixed(2) : "N/A";
          return `• **#${i + 1} ${optionName(o, loc)}** — Grade **${o.grade}** | Water: ${w} (bad yr: ${by}) [D] | RYI: ${ryi} [D]`;
        })
        .join("\n");
      return {
        text:
          `Top ranked 3-season rotations for **${label}** (${pack.field.area_ha.toFixed(1)} ha):\n` +
          lines +
          (currentOpt ? `\n• **Current rotation**: ${optionName(currentOpt, loc)} (Grade ${currentOpt.grade})` : ""),
        sourceLabel: `${label} Options [D/E]`,
        followUps: ["What should I measure next?", "What are the bare soil months and hazards?"],
      };
    }

    return isAr
      ? {
          text: summarizeFieldPack(ctx, true),
          sourceLabel: `سياق ${label} [O/D]`,
          followUps: ["ما أفضل دورة لهذا الحقل؟", "ما أشهر التربة العارية والمخاطر؟", "ما الذي يُنصح بقياسه لاحقًا؟"],
        }
      : {
          text: summarizeFieldPack(ctx, false),
          sourceLabel: `${label} Live Context [O/D]`,
          followUps: ["What is the top rotation for this field?", "What are the bare soil months and hazards?", "What should I measure next?"],
        };
  }

  // 4. Scoreboard / hindcast query
  if (ctx.hindcast && /(scoreboard|hindcast|crps|baseline|b0|b1|b2|metric|لوحة النتائج|اختبار تراجعي|خط الأساس)/.test(q)) {
    const canopy = ctx.hindcast.rows.filter((r) => r.mode === "forecast" && r.metric === "canopy_integral");
    if (canopy.length > 0) {
      const lines = canopy
        .map((r) => `• **${r.method}**: CRPS ${r.scores.crps?.toFixed(2) ?? "N/A"} | ${isAr ? "تغطية 90%" : "90% cov"} ${r.scores.covered90 != null ? `${Math.round(r.scores.covered90 * 100)}%` : "N/A"} (n=${r.n})`)
        .join("\n");
      return isAr
        ? {
            text: `لوحة الاختبار التراجعي للمنطقة **${ctx.hindcast.region_id}** (تاريخ القطع ${ctx.hindcast.cutoff}):\n${lines}`,
            sourceLabel: "لوحة الاختبار التراجعي [D]",
            followUps: ["ما هي الحدود الصريحة للمشروع؟", "كيف يعمل القمح الشتوي؟"],
          }
        : {
            text: `Region **${ctx.hindcast.region_id}** Hindcast Forecast Scoreboard (Canopy Integral, cutoff ${ctx.hindcast.cutoff}):\n${lines}`,
            sourceLabel: "Hindcast Scoreboard [D]",
            followUps: ["What are the project's honest limits?", "How does winter wheat phenology work?"],
          };
    }
  }

  // 5. Scored keyword retrieval over Knowledge Base (supports English + Arabic Unicode tokens)
  const queryTokens = q.split(/[^a-z0-9_\u0600-\u06FF]+/).filter((w) => w.length >= 2);
  let bestEntry: KnowledgeEntry | null = null;
  let bestScore = 0;

  for (const entry of kb) {
    let score = 0;
    for (const kw of entry.keywords) {
      if (q.includes(kw)) {
        score += kw.includes(" ") ? 4 : 2;
      }
    }
    for (const tok of queryTokens) {
      if (entry.title.toLowerCase().includes(tok)) score += 1.5;
      else if (entry.answer.toLowerCase().includes(tok)) score += 0.5;
    }
    if (score > bestScore) {
      bestScore = score;
      bestEntry = entry;
    }
  }

  if (bestEntry && bestScore >= 2) {
    return {
      text: bestEntry.answer,
      sourceLabel: bestEntry.sourceLabel,
      followUps: bestEntry.followUps,
    };
  }

  // 6. Helpful grounded fallback listing active context capabilities
  if (isAr) {
    return {
      text:
        `الوضع الموثق دون اتصال يغطي موضوعات FieldWitness المفهرسة وبيانات الحقل/الصفحة المفتوحة (أضف مفتاح API من زر **API** للإجابة الحرة).\n\n` +
        (pack ? `${summarizeFieldPack(ctx, true)}\n\n` : "") +
        "جرّب السؤال عن **الشهود الثلاثة**، أو **درجات الدليل A–D**، أو **بيانات التربة SSURGO**، أو **القمح الشتوي**، أو **الحدود الصريحة للمشروع**، أو **التقييم المناخي العالمي**.",
      sourceLabel: "الوضع الموثق (دون اتصال)",
      followUps: pack
        ? ["لخّص هذا الحقل", "ما أفضل دورة لهذا الحقل؟", "ما أشهر التربة العارية والمخاطر؟"]
        : ["ما هو FieldWitness؟", "كيف يعمل الشهود الثلاثة؟", "ما هي الحدود الصريحة للمشروع؟"],
    };
  }

  return {
    text:
      `Offline Grounded Mode only covers indexed FieldWitness topics and the active field/page data (connect an API key or proxy in **API** settings for free-form LLM answers).\n\n` +
      (pack ? `${summarizeFieldPack(ctx, false)}\n\n` : "") +
      "Try asking about the **Three Witnesses**, **Evidence Grades A–D**, **USDA SSURGO soil TAW**, **Winter Wheat calibration**, **Honest Hindcast Limits**, or **Global Live Climate Assessment**.",
    sourceLabel: "Grounded Fallback (Offline Mode)",
    followUps: pack
      ? ["Summarize this field", "What is the top rotation for this field?", "What are the bare soil months and hazards?"]
      : ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
  };
}
