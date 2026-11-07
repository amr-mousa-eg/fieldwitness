// Minimal WKT -> GeoJSON for the geometries our packs carry: POLYGON and MULTIPOLYGON
// (Field.geometry_wkt is written by shapely). Anything else is rejected, not guessed.

type Nested = number[] | Nested[];

function parseNested(src: string): Nested {
  let i = 0;
  const skip = () => {
    while (i < src.length && /\s/.test(src[i])) i++;
  };
  const list = (): Nested => {
    skip();
    if (src[i] !== "(") throw new Error(`WKT: expected "(" at ${i}`);
    i++;
    const items: Nested[] = [];
    for (;;) {
      skip();
      if (src[i] === "(") items.push(list());
      else {
        const m = /^(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)/.exec(src.slice(i));
        if (!m) throw new Error(`WKT: expected a coordinate at ${i}`);
        items.push([Number(m[1]), Number(m[2])]);
        i += m[0].length;
      }
      skip();
      if (src[i] === ",") i++;
      else if (src[i] === ")") {
        i++;
        return items;
      } else throw new Error(`WKT: unexpected "${src[i] ?? "end"}" at ${i}`);
    }
  };
  const out = list();
  skip();
  if (i !== src.length) throw new Error("WKT: trailing characters");
  return out;
}

export function wktToGeometry(wkt: string): GeoJSON.Polygon | GeoJSON.MultiPolygon {
  const m = /^\s*(MULTIPOLYGON|POLYGON)\s*(\(.*\))\s*$/is.exec(wkt);
  if (!m) throw new Error(`WKT: only POLYGON and MULTIPOLYGON are supported: ${wkt.slice(0, 40)}`);
  const coords = parseNested(m[2]);
  return m[1].toUpperCase() === "POLYGON"
    ? { type: "Polygon", coordinates: coords as number[][][] }
    : { type: "MultiPolygon", coordinates: coords as number[][][][] };
}

/** [W, S, E, N] of a set of geometries. */
export function boundsOf(geoms: (GeoJSON.Polygon | GeoJSON.MultiPolygon)[]): [number, number, number, number] {
  const b: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
  const visit = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") {
      const [x, y] = c as number[];
      b[0] = Math.min(b[0], x);
      b[1] = Math.min(b[1], y);
      b[2] = Math.max(b[2], x);
      b[3] = Math.max(b[3], y);
    } else if (Array.isArray(c)) c.forEach(visit);
  };
  geoms.forEach((g) => visit(g.coordinates));
  return b;
}
