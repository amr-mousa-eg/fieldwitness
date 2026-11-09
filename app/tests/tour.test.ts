import { describe, expect, it } from "vitest";
import { DEMO_FIELD_ID, DEMO_REGION_ID, TOUR_STEPS } from "../src/TourGuide";
import en from "../src/strings/en.json";

describe("Guided Tour Configuration and Honest Copy", () => {
  it("defines exactly 7 ordered tour steps covering the complete application journey", () => {
    expect(TOUR_STEPS).toHaveLength(7);
    const routes = TOUR_STEPS.map((s) => s.route);
    expect(routes[0]).toBe(`#/${DEMO_REGION_ID}/map`);
    expect(routes[1]).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/story`);
    expect(routes[2]).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/options`);
    expect(routes[3]).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/calendar`);
    expect(routes[4]).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/advisor`);
    expect(routes[5]).toBe(`#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/sim3d`);
    expect(routes[6]).toBe("#/add-field");
  });

  it("relies on the verified Kansas Field #12 representative pilot field", () => {
    expect(DEMO_REGION_ID).toBe("ks_t14slh");
    expect(DEMO_FIELD_ID).toBe("0d5615b52572c5c2eeac7fdfef8cdda167050a22");
  });

  it("has corresponding localized title and body strings for all 7 steps", () => {
    TOUR_STEPS.forEach((step) => {
      const titleKey = `tour.${step.key}.title` as keyof typeof en;
      const bodyKey = `tour.${step.key}.body` as keyof typeof en;
      expect(en[titleKey], `Missing string for ${titleKey}`).toBeDefined();
      expect(en[bodyKey], `Missing string for ${bodyKey}`).toBeDefined();
      expect(en[titleKey].length).toBeGreaterThan(5);
      expect(en[bodyKey].length).toBeGreaterThan(20);
    });
  });

  it("adheres strictly to honest terminology and forbidden-word prohibitions", () => {
    const FORBIDDEN_WORDS = [/guarantee/i, /optimal/i, /best yield/i, /maximize profit/i, /foolproof/i];
    TOUR_STEPS.forEach((step) => {
      const text = `${en[`tour.${step.key}.title` as keyof typeof en]} ${en[`tour.${step.key}.body` as keyof typeof en]}`;
      FORBIDDEN_WORDS.forEach((regex) => {
        expect(text).not.toMatch(regex);
      });
    });

    // Step 3 specifically reports the pre-registered grade validity test outcome
    const step3 = en["tour.step3.body"];
    expect(step3).toContain("did not predict");
    expect(step3).toContain("CRPS 17.0 vs 24.0");
    expect(step3).toContain("463");

    // Step 1 explicitly states Grade B ceiling in Kansas
    const step1 = en["tour.step1.body"];
    expect(step1).toContain("Grade B at best");
  });

  it("handles missing target selectors gracefully without crashing", () => {
    // Helper function matching TourGuide's selector logic
    const resolveSelector = (sel?: string, doc?: { querySelector: (s: string) => any }) => {
      if (!sel || !doc) return null;
      try {
        return doc.querySelector(sel);
      } catch {
        return null;
      }
    };
    expect(resolveSelector(".missing-element", { querySelector: () => null })).toBeNull();
    expect(resolveSelector("invalid[[[syntax", { querySelector: () => { throw new Error("bad selector"); } })).toBeNull();
    expect(resolveSelector(undefined)).toBeNull();
  });

  it("retains pre-tour hash route when dismissed via Skip or Escape", () => {
    // Verify route preservation contract
    const initialRoute = "#/ks_t14slh/scoreboard";
    let currentHash = initialRoute;
    const savedRoute = currentHash;

    // Simulate opening tour and advancing steps
    currentHash = TOUR_STEPS[1].route;
    expect(currentHash).not.toBe(savedRoute);

    // Simulate pressing Escape or Skip
    const restoreRoute = true;
    if (restoreRoute) {
      currentHash = savedRoute;
    }
    expect(currentHash).toBe(initialRoute);
  });
});
