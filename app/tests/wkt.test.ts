import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { boundsOf, wktToGeometry } from "../src/wkt";
import { pageHref, parseHash, routeHref } from "../src/route";

describe("wktToGeometry", () => {
  it("parses a polygon with a hole", () => {
    const g = wktToGeometry("POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0), (1 1, 2 1, 2 2, 1 1))");
    expect(g.type).toBe("Polygon");
    expect(g.coordinates).toHaveLength(2);
    expect(g.coordinates[0][1]).toEqual([4, 0]);
  });

  it("parses a multipolygon with negative and exponent coordinates", () => {
    const g = wktToGeometry("MULTIPOLYGON (((-100.9 38, -100.8 38, -100.8 38.1, -100.9 38)), ((1e-3 2, 3 4, 5 6, 1e-3 2)))");
    expect(g.type).toBe("MultiPolygon");
    expect(g.coordinates).toHaveLength(2);
    expect(g.coordinates[1][0][0]).toEqual([0.001, 2]);
  });

  it("rejects other geometry types and broken input", () => {
    expect(() => wktToGeometry("POINT (1 2)")).toThrow(/only POLYGON/);
    expect(() => wktToGeometry("POLYGON ((0 0, 1 1)")).toThrow();
    expect(() => wktToGeometry("POLYGON ((0 0, 1 x))")).toThrow();
  });

  it("parses every fixture field and finds them inside the region bbox", () => {
    const idx = JSON.parse(
      readFileSync(join(import.meta.dirname, "../fixtures/ks_demo_synthetic/index.SYNTHETIC.json"), "utf8"),
    );
    const [w, s, e, n] = boundsOf(idx.fields.map((f: { geometry_wkt: string }) => wktToGeometry(f.geometry_wkt)));
    const [W, S, E, N] = idx.bbox_lonlat;
    expect(w).toBeGreaterThanOrEqual(W);
    expect(s).toBeGreaterThanOrEqual(S);
    expect(e).toBeLessThanOrEqual(E);
    expect(n).toBeLessThanOrEqual(N);
  });
});

describe("hash routes", () => {
  it("round-trips region and field", () => {
    const map = { page: "map", tab: "story" };
    expect(parseHash(routeHref("ks_t14slh", "abc123"))).toEqual({ ...map, regionId: "ks_t14slh", fieldId: "abc123" });
    expect(parseHash(routeHref("ks_t14slh"))).toEqual({ ...map, regionId: "ks_t14slh", fieldId: null });
    expect(parseHash(routeHref("r", "f", "options")).tab).toBe("options");
    expect(parseHash(routeHref("r", "f", "advisor")).tab).toBe("advisor");
    expect(parseHash("#/r/f/bogus").tab).toBe("story");
    expect(parseHash("")).toEqual({ ...map, regionId: null, fieldId: null });
  });

  it("round-trips region pages, which are never field ids", () => {
    expect(parseHash(pageHref("ks", "scoreboard"))).toMatchObject({ regionId: "ks", page: "scoreboard", fieldId: null });
    expect(pageHref("ks", "map")).toBe("#/ks");
  });
});
