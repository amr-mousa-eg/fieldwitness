// Tour buttons must stay readable in both themes. The test reads the theme tokens from
// src/styles.css and the tokens the buttons use from src/TourGuide.css, then computes
// WCAG 2.x contrast ratios (relative luminance, WCAG 2.2 §1.4.3 text >= 4.5:1,
// §1.4.11 non-text / borders >= 3:1).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(import.meta.dirname, "..", "src");
const styles = readFileSync(join(SRC, "styles.css"), "utf8");
const tourCss = readFileSync(join(SRC, "TourGuide.css"), "utf8");

/** Token map of the first `{ ... }` block whose selector text matches `selector`. */
function tokens(css: string, selector: string): Record<string, string> {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`selector not found: ${selector}`);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  const out: Record<string, string> = {};
  for (const m of css.slice(open + 1, close).matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

/** Declarations of a plain CSS rule (exact selector) in TourGuide.css. */
function rule(css: string, selector: string): Record<string, string> {
  const m = css.match(new RegExp(`(^|\\n)${selector.replace(/[.:]/g, "\\$&")}\\s*\\{([^}]*)\\}`));
  if (!m) throw new Error(`rule not found: ${selector}`);
  const out: Record<string, string> = {};
  for (const d of m[2].matchAll(/([\w-]+)\s*:\s*([^;]+);/g)) out[d[1]] = d[2].trim();
  return out;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? [...h].map((c) => c + c).join("") : h;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as [number, number, number];
}

/** WCAG 2.x relative luminance. */
function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const THEMES = {
  light: tokens(styles, ":root {"),
  "light (explicit)": tokens(styles, ':root[data-theme="light"] {'),
  "dark (explicit)": tokens(styles, ':root[data-theme="dark"] {'),
  "dark (system)": tokens(styles, ':root:not([data-theme="light"]) {'),
};

/** Resolve `var(--x)` (or a literal hex) against a theme. */
function resolveColour(value: string, theme: Record<string, string>): string {
  const v = value.match(/^var\((--[\w-]+)\)$/);
  const hex = v ? theme[v[1]] : value;
  if (!hex || !/^#[0-9a-f]{3,6}$/i.test(hex)) throw new Error(`cannot resolve colour "${value}"`);
  return hex;
}

const next = rule(tourCss, ".tour-next-btn");
const prev = rule(tourCss, ".tour-prev-btn");

describe("tour buttons contrast (computed from theme tokens)", () => {
  it("contrast() matches known WCAG reference values", () => {
    expect(contrast("#ffffff", "#000000")).toBeCloseTo(21, 5);
    expect(contrast("#777777", "#ffffff")).toBeCloseTo(4.48, 2);
  });

  for (const [name, theme] of Object.entries(THEMES)) {
    describe(name, () => {
      const panel = theme["--panel"];

      it("Next is a filled button: text >= 4.5:1 on its fill, fill/border >= 3:1 on the dialog", () => {
        const bg = resolveColour(next.background, theme);
        const fg = resolveColour(next.color, theme);
        const border = resolveColour(next["border-color"], theme);
        expect(bg).not.toBe(panel); // filled, not transparent-looking
        expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
        expect(contrast(bg, panel)).toBeGreaterThanOrEqual(3);
        expect(contrast(border, panel)).toBeGreaterThanOrEqual(3);
      });

      it("Back is an outlined button: text >= 4.5:1, border >= 3:1 on the dialog", () => {
        const bg = resolveColour(prev.background, theme);
        const fg = resolveColour(prev.color, theme);
        const border = resolveColour(prev["border-color"], theme);
        expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
        expect(contrast(border, bg)).toBeGreaterThanOrEqual(3);
        expect(contrast(border, panel)).toBeGreaterThanOrEqual(3);
      });
    });
  }

  it("both dark blocks define the same button tokens", () => {
    for (const k of ["--accent", "--on-accent", "--panel", "--ink", "--muted"]) {
      expect(THEMES["dark (system)"][k], k).toBe(THEMES["dark (explicit)"][k]);
    }
  });

  it("disabled Back on step 1 is hidden, not a faint ghost", () => {
    expect(rule(tourCss, ".tour-prev-btn:disabled").visibility).toBe("hidden");
  });
});
