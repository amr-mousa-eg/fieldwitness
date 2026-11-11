import type * as THREE from "three";

/**
 * Live theme for a three.js scene: colours, opacities and lights are registered once with their
 * light and dark values and re-applied on a theme change, so the scene, its WebGL context,
 * geometries and materials are kept (no rebuild on Light / Dark / Auto).
 */
export class ThemeBinder {
  private readonly setters: ((dark: boolean) => void)[] = [];

  constructor(public dark: boolean) {}

  /** Run `fn` now and on every theme change. */
  on(fn: (dark: boolean) => void): void {
    this.setters.push(fn);
    fn(this.dark);
  }

  /** Material (or anything with a colour) whose colour depends on the theme; returned for chaining. */
  color<T extends { color: THREE.Color }>(obj: T, light: number, dark: number): T {
    this.on((d) => obj.color.setHex(d ? dark : light));
    return obj;
  }

  /** Material opacity that depends on the theme. */
  opacity<T extends { opacity: number }>(obj: T, light: number, dark: number): T {
    this.on((d) => {
      obj.opacity = d ? dark : light;
    });
    return obj;
  }

  apply(dark: boolean): void {
    this.dark = dark;
    for (const s of this.setters) s(dark);
  }

  get size(): number {
    return this.setters.length;
  }
}
