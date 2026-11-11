// "Try it" tour: step definitions and pure state logic (no React, no DOM globals), so the tour
// can be unit-tested in node. The card itself is TourGuide.tsx; events come from tourEvents.ts.
import { parseHash, routeHref } from "./route";
import type { TourAction } from "./tourEvents";

/** Representative pilot field used when a step needs a field and none is open. */
export const DEMO_FIELD_ID = "0d5615b52572c5c2eeac7fdfef8cdda167050a22";
export const DEMO_REGION_ID = "ks_t14slh";

export interface TourStep {
  key: string;
  /** Actions that tick the step; all are needed. */
  requires: TourAction[];
  /** The actions only count in this order (a later one is ignored until the earlier ones happened). */
  ordered?: boolean;
  /** The step happens on a field page: open the demo field if no field is open. */
  needsField?: boolean;
  /**
   * Selector groups, tried in order. The first group with a visible match is highlighted:
   * the real control first, then the link that leads to it.
   */
  targets: string[];
  /** Scroll the real control into view once (off for steps whose action is finding it). */
  scroll?: boolean;
}

export const TOUR_STEPS: TourStep[] = [
  {
    key: "field",
    requires: ["field"],
    targets: [".field-items-list, .map-container", ".app-nav a:first-child"],
  },
  {
    key: "season",
    requires: ["season"],
    needsField: true,
    targets: [".chart-season-select", '.tabs a[href$="/story"]'],
    scroll: true,
  },
  {
    key: "priority",
    requires: ["priority"],
    needsField: true,
    targets: [".priority-panel", '.tabs a[href$="/options"]'],
    scroll: true,
  },
  {
    key: "why",
    requires: ["why-ranking"],
    needsField: true,
    targets: [".ranking-explainer-card", '.tabs a[href$="/options"]'],
  },
  {
    key: "sim3d",
    requires: ["sim-play", "sim-drought"],
    needsField: true,
    targets: [".sim3d-play-btn, #sim3d-scenario-select", '.tabs a[href$="/sim3d"]'],
    scroll: true,
  },
  {
    key: "limits",
    requires: ["limits"],
    targets: [".grade-validity-verdict", '.app-nav a[href$="/scoreboard"]'],
  },
  {
    key: "addfield",
    requires: ["preset:cairo-demo", "preset:garden-city"],
    ordered: true,
    targets: [".presets-bar", '.app-nav a[href="#/add-field"]'],
    scroll: true,
  },
];

export interface TourProgress {
  step: number;
  done: TourAction[];
}

export const TOUR_STORAGE_KEY = "fw:tour:progress";

export function emptyProgress(): TourProgress {
  return { step: 0, done: [] };
}

/** Add an action to the progress. Ordered steps ignore an action until its predecessors happened. */
export function recordAction(p: TourProgress, action: TourAction): TourProgress {
  if (p.done.includes(action)) return p;
  const blocked = TOUR_STEPS.some((s) => {
    const i = s.requires.indexOf(action);
    return s.ordered && i > 0 && !s.requires.slice(0, i).every((a) => p.done.includes(a));
  });
  return blocked ? p : { ...p, done: [...p.done, action] };
}

export function isStepDone(step: TourStep, done: readonly TourAction[]): boolean {
  return step.requires.every((a) => done.includes(a));
}

export function clampStep(n: number): number {
  return Math.min(Math.max(0, Math.trunc(n) || 0), TOUR_STEPS.length - 1);
}

export function goToStep(p: TourProgress, step: number): TourProgress {
  return { ...p, step: clampStep(step) };
}

/** window.localStorage, or null when the browser blocks it (the getter itself can throw). */
export function browserStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

/** Saved progress, or a fresh start when nothing valid is stored or storage is blocked. */
export function loadProgress(storage: Pick<Storage, "getItem"> | null): TourProgress {
  try {
    const raw = storage?.getItem(TOUR_STORAGE_KEY);
    if (!raw) return emptyProgress();
    const v = JSON.parse(raw) as Partial<TourProgress>;
    const done = Array.isArray(v.done) ? v.done.filter((a): a is TourAction => typeof a === "string") : [];
    return { step: clampStep(Number(v.step)), done };
  } catch {
    return emptyProgress();
  }
}

export function saveProgress(storage: Pick<Storage, "setItem"> | null, p: TourProgress): void {
  try {
    storage?.setItem(TOUR_STORAGE_KEY, JSON.stringify(p));
  } catch {
    // storage full or blocked: the tour still works, it just will not resume
  }
}

export function clearProgress(storage: Pick<Storage, "removeItem"> | null): void {
  try {
    storage?.removeItem(TOUR_STORAGE_KEY);
  } catch {
    // ignore
  }
}

/** Where to go when entering a step, or null to stay (the user drives navigation). */
export function stepEntryHash(step: TourStep, hash: string): string | null {
  if (!step.needsField) return null;
  return parseHash(hash).fieldId ? null : routeHref(DEMO_REGION_ID, DEMO_FIELD_ID, "story");
}

interface QueryRoot {
  querySelectorAll(selector: string): ArrayLike<Element>;
}

function visible(el: Element): boolean {
  return typeof el.getClientRects !== "function" || el.getClientRects().length > 0;
}

/**
 * Elements to highlight for a step: all visible matches of the first selector group that has
 * one. A missing target (or a bad selector) gives an empty list, never an error.
 */
export function findTargets(root: QueryRoot | null | undefined, step: TourStep): { els: Element[]; primary: boolean } {
  if (!root) return { els: [], primary: false };
  for (let i = 0; i < step.targets.length; i++) {
    try {
      const els = Array.from(root.querySelectorAll(step.targets[i])).filter(visible);
      if (els.length > 0) return { els, primary: i === 0 };
    } catch {
      // invalid selector or detached document: try the next group
    }
  }
  return { els: [], primary: false };
}

/** Skip/Escape: put the page back where the tour started (only the hash; nothing else is changed). */
export function restoreHash(loc: { hash: string }, startHash: string): void {
  if (loc.hash !== startHash) loc.hash = startHash;
}
