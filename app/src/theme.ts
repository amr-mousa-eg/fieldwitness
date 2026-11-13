export type ThemeChoice = "system" | "light" | "dark";

/** Event fired on `window` whenever the Light / Dark / Auto choice changes (shared by all views). */
export const THEME_EVENT = "fw:theme";

// The choice made in this tab, also when localStorage is blocked (then it lasts until reload).
let memoryChoice: ThemeChoice | null = null;

export function getStoredTheme(): ThemeChoice {
  if (memoryChoice) return memoryChoice;
  try {
    const val = localStorage.getItem("fw-theme");
    if (val === "light" || val === "dark") return val;
  } catch {
    // blocked or unavailable
  }
  return "system";
}

export function setStoredTheme(choice: ThemeChoice): void {
  memoryChoice = choice;
  try {
    if (choice === "system") localStorage.removeItem("fw-theme");
    else localStorage.setItem("fw-theme", choice);
  } catch {
    // blocked or unavailable: the in-memory choice still applies
  }
  try {
    if (choice === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", choice);
  } catch {
    // no document (tests)
  }
  if (typeof window !== "undefined") window.dispatchEvent(new Event(THEME_EVENT));
}

/**
 * Call `cb` when the effective theme may have changed: a choice in any component, a choice in
 * another tab (storage event) or the system light/dark setting. Returns the unsubscribe function.
 */
export function subscribeTheme(cb: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const media = window.matchMedia?.("(prefers-color-scheme: dark)");
  const onStorage = (e: StorageEvent) => {
    if (e.key === "fw-theme") {
      memoryChoice = null;
      cb();
    }
  };
  window.addEventListener(THEME_EVENT, cb);
  window.addEventListener("storage", onStorage);
  media?.addEventListener?.("change", cb);
  return () => {
    window.removeEventListener(THEME_EVENT, cb);
    window.removeEventListener("storage", onStorage);
    media?.removeEventListener?.("change", cb);
  };
}

export function getEffectiveTheme(choice: ThemeChoice = getStoredTheme()): "light" | "dark" {
  if (choice === "light" || choice === "dark") return choice;
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

export const CHART_COLOURS = {
  light: {
    smooth: "#0f2936",
    grid: "#cbd5d1",
    axis: "#4b5b63",
    muted: "#4b5b63",
    pred: "#0b6ea8",
    obs: "#c26a19",
    ndvi: "#1b7a3d",
    evi: "#7c3aed",
    marks: "#b45309",
    line: "#475569",
    refAlt: "#64748b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#94a3b8",
    tooltipText: "#0f172a",
  },
  dark: {
    smooth: "#e2f1ec",
    grid: "#334155",
    axis: "#cbd5e1",
    muted: "#94a3b8",
    pred: "#38bdf8",
    obs: "#fbbf24",
    ndvi: "#4ade80",
    evi: "#c084fc",
    marks: "#fbbf24",
    line: "#94a3b8",
    refAlt: "#94a3b8",
    tooltipBg: "#1e293b",
    tooltipBorder: "#475569",
    tooltipText: "#f1f5f9",
  },
} as const;

export function getMapColours(dark: boolean) {
  return {
    background: dark ? "#3b3d36" : "#d8d6cc",
    regionLine: dark ? "#8f8c7c" : "#7d7a6c",
    fieldFill: "#c9a43a",
    fieldLine: dark ? "#f0cf65" : "#5b4813",
    // Dark ring around the amber point keeps it readable on satellite imagery in both themes.
    markerLine: "#14181a",
    selected: dark ? "#ffffff" : "#22313a",
  };
}
