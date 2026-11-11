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
    smooth: "#22313a",
    grid: "#c9d1cd",
    muted: "#56646b",
    pred: "#1f5f7e",
    obs: "#8a6a1f",
    ndvi: "#2f6b3a",
    evi: "#6b5ea8",
    marks: "#8a6a1f",
    line: "#56646b",
  },
  dark: {
    smooth: "#e4ebe8",
    grid: "#34424a",
    muted: "#a2b0b6",
    pred: "#64b5f6",
    obs: "#ffd54f",
    ndvi: "#68bb76",
    evi: "#b39ddb",
    marks: "#ffd54f",
    line: "#a2b0b6",
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
