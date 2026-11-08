export type ThemeChoice = "system" | "light" | "dark";

export function getStoredTheme(): ThemeChoice {
  try {
    const val = localStorage.getItem("fw-theme");
    if (val === "light" || val === "dark") return val;
  } catch {
    // blocked or unavailable
  }
  return "system";
}

export function setStoredTheme(choice: ThemeChoice): void {
  try {
    if (choice === "system") {
      localStorage.removeItem("fw-theme");
      document.documentElement.removeAttribute("data-theme");
    } else {
      localStorage.setItem("fw-theme", choice);
      document.documentElement.setAttribute("data-theme", choice);
    }
  } catch {
    // blocked or unavailable
  }
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
    selected: dark ? "#ffffff" : "#22313a",
  };
}
