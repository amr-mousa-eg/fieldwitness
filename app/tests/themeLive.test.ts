// Theme-update path: a Light / Dark / Auto choice reaches every subscriber at once (no reload),
// and a 3D scene re-colours its registered materials and lights in place (no rebuild).
import * as THREE from "three";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeBinder } from "../src/field3d/themed";
import { getEffectiveTheme, getStoredTheme, setStoredTheme, subscribeTheme } from "../src/theme";

describe("shared theme store", () => {
  const g = globalThis as Record<string, unknown>;
  let attr: string | null = null;
  beforeEach(() => {
    const store = new Map<string, string>();
    g.window = Object.assign(new EventTarget(), { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) });
    g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k) };
    g.document = { documentElement: { setAttribute: (_: string, v: string) => (attr = v), removeAttribute: () => (attr = null) } };
  });
  afterEach(() => {
    delete g.window;
    delete g.localStorage;
    delete g.document;
  });

  it("notifies every subscriber and updates the effective theme and data-theme", () => {
    const seen: string[][] = [[], []];
    const offs = [0, 1].map((i) => subscribeTheme(() => seen[i].push(getEffectiveTheme())));
    setStoredTheme("dark");
    setStoredTheme("light");
    setStoredTheme("system");
    expect(seen[0]).toEqual(["dark", "light", "light"]);
    expect(seen[1]).toEqual(seen[0]);
    expect(attr).toBeNull();
    setStoredTheme("dark");
    expect(attr).toBe("dark");
    expect(getStoredTheme()).toBe("dark");
    offs.forEach((off) => off());
    setStoredTheme("light");
    expect(seen[0]).toHaveLength(4); // unsubscribed
  });

  it("keeps the choice in this tab when localStorage is blocked", () => {
    g.localStorage = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    };
    setStoredTheme("dark");
    expect(getStoredTheme()).toBe("dark");
    expect(getEffectiveTheme()).toBe("dark");
  });
});

describe("ThemeBinder: scene colours change in place", () => {
  it("re-applies colours, opacities and custom setters to the same objects", () => {
    const T = new ThemeBinder(false);
    const mat = T.color(new THREE.MeshBasicMaterial(), 0x112233, 0xaabbcc);
    T.opacity(mat, 0.4, 0.6);
    const light = new THREE.HemisphereLight();
    T.on((d) => (light.intensity = d ? 0.75 : 0.95));
    expect(mat.color.getHex()).toBe(0x112233);
    expect(mat.opacity).toBeCloseTo(0.4);
    expect(light.intensity).toBeCloseTo(0.95);
    const sameMat = mat;
    T.apply(true);
    expect(mat).toBe(sameMat);
    expect(mat.color.getHex()).toBe(0xaabbcc);
    expect(mat.opacity).toBeCloseTo(0.6);
    expect(light.intensity).toBeCloseTo(0.75);
    T.apply(false);
    expect(mat.color.getHex()).toBe(0x112233);
    expect(T.size).toBe(3);
  });
});
