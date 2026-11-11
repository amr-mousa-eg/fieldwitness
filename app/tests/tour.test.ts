import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { PRESET_LOCATIONS, isInsideKansasTile } from "../src/customField";
import { parseHash } from "../src/route";
import en from "../src/strings/en.json";
import {
  DEMO_FIELD_ID,
  DEMO_REGION_ID,
  TOUR_STEPS,
  TOUR_STORAGE_KEY,
  emptyProgress,
  findTargets,
  goToStep,
  isStepDone,
  loadProgress,
  recordAction,
  restoreHash,
  saveProgress,
  stepEntryHash,
  type TourProgress,
} from "../src/tour";
import { TOUR_EVENT, type TourAction, onTourAction } from "../src/tourEvents";

const str = (k: string) => (en as Record<string, string>)[k];
const step = (key: string) => TOUR_STEPS.find((s) => s.key === key)!;

/** Wire a tour state to an event target the way TourGuide.tsx does, and dispatch real CustomEvents. */
function harness(start: TourProgress = emptyProgress()) {
  const target = new EventTarget();
  let progress = start;
  const off = onTourAction(target, (a) => (progress = recordAction(progress, a)));
  const emit = (action: string) => target.dispatchEvent(new CustomEvent(TOUR_EVENT, { detail: { action } }));
  return { target, emit, off, get: () => progress };
}

function memoryStorage(): Storage & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    key: (i) => [...data.keys()][i] ?? null,
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => void data.set(k, String(v)),
    removeItem: (k) => void data.delete(k),
  };
}

describe("try-it tour: steps", () => {
  it("has the 7 steps in the agreed order", () => {
    expect(TOUR_STEPS.map((s) => s.key)).toEqual(["field", "season", "priority", "why", "sim3d", "limits", "addfield"]);
    expect(TOUR_STEPS.map((s) => s.requires)).toEqual([
      ["field"],
      ["season"],
      ["priority"],
      ["why-ranking"],
      ["sim-play", "sim-drought"],
      ["limits"],
      ["preset:cairo-demo", "preset:garden-city"],
    ]);
  });

  it("uses the verified Kansas pilot demo field", () => {
    expect(DEMO_REGION_ID).toBe("ks_t14slh");
    expect(DEMO_FIELD_ID).toBe("0d5615b52572c5c2eeac7fdfef8cdda167050a22");
  });

  it("every step has a title, a body and a label for each action", () => {
    for (const s of TOUR_STEPS) {
      expect(str(`tour.${s.key}.title`), s.key).toBeTruthy();
      expect(str(`tour.${s.key}.body`)?.length, s.key).toBeGreaterThan(40);
      for (const a of s.requires) expect(str(`tour.check.${a}`), a).toBeTruthy();
    }
  });

  it("every action is emitted by a real component", () => {
    const src = (f: string) => readFileSync(join(import.meta.dirname, "..", "src", f), "utf8");
    const emitters: Record<string, string[]> = {
      field: ["MapPage.tsx", "FieldList.tsx"],
      season: ["FieldStory.tsx"],
      priority: ["FieldCard.tsx"],
      "why-ranking": ["RankingExplainerSection.tsx"],
      "sim-play": ["Field3DView.tsx"],
      "sim-drought": ["Field3DView.tsx"],
      limits: ["Scoreboard.tsx"],
    };
    for (const [action, files] of Object.entries(emitters)) {
      for (const f of files) expect(src(f), `${action} in ${f}`).toMatch(new RegExp(`(emitTour|useTourSeen)\\("${action}"\\)`));
    }
    expect(src("AddFieldPage.tsx")).toContain("emitTour(`preset:${preset.id}`)");
  });
});

describe("try-it tour: each action ticks its step", () => {
  const cases: [string, string[]][] = [
    ["field", ["field"]],
    ["season", ["season"]],
    ["priority", ["priority"]],
    ["why", ["why-ranking"]],
    ["sim3d", ["sim-play", "sim-drought"]],
    ["limits", ["limits"]],
    ["addfield", ["preset:cairo-demo", "preset:garden-city"]],
  ];
  for (const [key, actions] of cases) {
    it(`${key}: ticks after ${actions.join(" + ")}`, () => {
      const h = harness();
      expect(isStepDone(step(key), h.get().done)).toBe(false);
      actions.forEach((a, i) => {
        h.emit(a);
        expect(isStepDone(step(key), h.get().done)).toBe(i === actions.length - 1);
      });
      h.off();
    });
  }

  it("3D needs both Play and the drought scenario", () => {
    const h = harness();
    h.emit("sim-drought");
    expect(isStepDone(step("sim3d"), h.get().done)).toBe(false);
    h.emit("sim-play");
    expect(isStepDone(step("sim3d"), h.get().done)).toBe(true);
  });

  it("Add my field: Garden City before Cairo does not count", () => {
    const h = harness();
    h.emit("preset:garden-city");
    h.emit("preset:cairo-demo");
    expect(isStepDone(step("addfield"), h.get().done)).toBe(false);
    h.emit("preset:garden-city");
    expect(isStepDone(step("addfield"), h.get().done)).toBe(true);
  });

  it("ignores unrelated or malformed events and stops listening when closed", () => {
    const h = harness();
    h.emit("preset:scott-city");
    h.target.dispatchEvent(new Event(TOUR_EVENT)); // no detail
    expect(TOUR_STEPS.some((s) => isStepDone(s, h.get().done))).toBe(false);
    h.off();
    h.emit("field");
    expect(h.get().done).not.toContain("field");
  });

  it("an action does not move the step: Next does", () => {
    const h = harness();
    h.emit("field");
    expect(h.get().step).toBe(0);
  });
});

describe("try-it tour: navigation", () => {
  it("Next works without doing the action, through to the last step", () => {
    let p = emptyProgress();
    for (let i = 1; i < TOUR_STEPS.length; i++) {
      p = goToStep(p, p.step + 1);
      expect(p.step).toBe(i);
      expect(isStepDone(TOUR_STEPS[i - 1], p.done)).toBe(false);
    }
    expect(goToStep(p, p.step + 1).step).toBe(TOUR_STEPS.length - 1);
    expect(goToStep(emptyProgress(), -1).step).toBe(0);
  });

  it("field steps open the demo field only when no field is open", () => {
    const s = step("season");
    const to = stepEntryHash(s, "#/ks_t14slh/scoreboard");
    expect(to).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/story`);
    expect(parseHash(to!).fieldId).toBe(DEMO_FIELD_ID);
    expect(stepEntryHash(s, "#/ks_t14slh/02cced77704c6b4a72bfdb5e0462c450800b7ae3/options")).toBeNull();
    expect(stepEntryHash(step("field"), "#/ks_t14slh/scoreboard")).toBeNull();
    expect(stepEntryHash(step("limits"), "#/ks_t14slh/methods")).toBeNull();
  });

  it("Skip returns to the page the tour started on", () => {
    const start = "#/ks_t14slh/scoreboard";
    const loc = { hash: start };
    const to = stepEntryHash(step("priority"), loc.hash);
    if (to) loc.hash = to; // the tour moved the page
    expect(loc.hash).not.toBe(start);
    restoreHash(loc, start);
    expect(loc.hash).toBe(start);
    restoreHash(loc, start); // idempotent
    expect(loc.hash).toBe(start);
  });
});

describe("try-it tour: missing targets", () => {
  it("returns no element, never throws, when the control is not on the page", () => {
    const empty = { querySelectorAll: () => [] as Element[] };
    const broken = {
      querySelectorAll: () => {
        throw new Error("bad selector");
      },
    };
    for (const s of TOUR_STEPS) {
      expect(findTargets(empty, s)).toEqual({ els: [], primary: false });
      expect(findTargets(broken, s)).toEqual({ els: [], primary: false });
      expect(findTargets(null, s)).toEqual({ els: [], primary: false });
    }
  });

  it("prefers the real control, then falls back to the link that leads to it", () => {
    const visible = { getClientRects: () => [{}] } as unknown as Element;
    const hidden = { getClientRects: () => [] } as unknown as Element;
    const s = step("priority");
    const only = (sel: string, el: Element) => ({ querySelectorAll: (q: string) => (q === sel ? [el] : []) });
    expect(findTargets(only(s.targets[0], visible), s)).toEqual({ els: [visible], primary: true });
    expect(findTargets(only(s.targets[1], visible), s)).toEqual({ els: [visible], primary: false });
    expect(findTargets(only(s.targets[0], hidden), s).els).toEqual([]);
  });
});

describe("try-it tour: progress is remembered", () => {
  it("saves and restores step and ticks", () => {
    const store = memoryStorage();
    let p = recordAction(emptyProgress(), "field");
    p = goToStep(p, 3);
    saveProgress(store, p);
    expect(store.data.has(TOUR_STORAGE_KEY)).toBe(true);
    expect(loadProgress(store)).toEqual({ step: 3, done: ["field"] });
  });

  it("falls back to a fresh start on blocked, empty or bad storage", () => {
    const throwing = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
    };
    expect(() => saveProgress(throwing, emptyProgress())).not.toThrow();
    expect(loadProgress(throwing)).toEqual(emptyProgress());
    expect(loadProgress(null)).toEqual(emptyProgress());
    const store = memoryStorage();
    expect(loadProgress(store)).toEqual(emptyProgress());
    store.setItem(TOUR_STORAGE_KEY, "{not json");
    expect(loadProgress(store)).toEqual(emptyProgress());
    store.setItem(TOUR_STORAGE_KEY, JSON.stringify({ step: 99, done: ["field", 3] }));
    expect(loadProgress(store)).toEqual({ step: TOUR_STEPS.length - 1, done: ["field"] });
  });
});

describe("try-it tour: honest copy", () => {
  const all = TOUR_STEPS.map((s) => `${str(`tour.${s.key}.title`)} ${str(`tour.${s.key}.body`)}`).join(" ");

  it("uses no forbidden claims", () => {
    for (const re of [/guarantee/i, /optimal/i, /best yield/i, /profit/i, /tonnes?/i, /foolproof/i, /\bgrade a\b/i]) {
      expect(all).not.toMatch(re);
    }
  });

  it("only repeats claims the app already makes", () => {
    expect(str("tour.field.body")).toContain("B at best");
    expect(str("methods.limits.4")).toContain("top out at B");
    expect(str("tour.season.body")).toContain("78.3 %");
    expect(str("methods.limits.3")).toContain("78.3 %");
    expect(str("tour.priority.body")).toContain("saved in this browser only");
    expect(str("card.store")).toContain("saved in this browser only");
    expect(str("tour.sim3d.body")).toContain("not a photo");
    expect(str("sim3d.honesty")).toContain("not a photo");
    expect(str("sim3d.disclaimer")).toContain("not a forecast");
    const verdict = "could not show that evidence grades predict accuracy (n = 463 field-seasons)";
    expect(str("tour.limits.body")).toContain(verdict);
    expect(str("score.gradeValidity.verdict")).toContain(verdict);
  });

  it("Cairo is a real out-of-footprint preset and Garden City is inside the pilot tile", () => {
    const cairo = PRESET_LOCATIONS.find((p) => p.id === "cairo-demo")!;
    const garden = PRESET_LOCATIONS.find((p) => p.id === "garden-city")!;
    // Tahrir Square, central Cairo: 30.0444 N, 31.2357 E
    expect([cairo.latitude, cairo.longitude]).toEqual([30.0444, 31.2357]);
    expect(cairo.is_supported).toBe(false);
    expect(isInsideKansasTile(cairo.longitude, cairo.latitude)).toBe(false);
    expect(garden.is_supported).toBe(true);
    expect(isInsideKansasTile(garden.longitude, garden.latitude)).toBe(true);
    const actions = step("addfield").requires as TourAction[];
    expect(actions).toEqual([`preset:${cairo.id}`, `preset:${garden.id}`]);
  });
});
