import { describe, expect, it } from "vitest";
import { fieldNumber, getFieldNumberMap, gradeRank } from "../src/fields";
import type { FieldSummary } from "../src/types";

const makeField = (id: string, grade: "A" | "B" | "C" | "D" = "B"): FieldSummary => ({
  field_id: id,
  geometry_wkt: "POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))",
  area_ha: 50.0,
  current_sequence: ["maize", "wheat"],
  top_option_id: "opt1",
  top_grade: grade,
});

describe("fields numbering and sorting", () => {
  it("assigns stable 1-based numbering sorted lexicographically by field_id", () => {
    const fields = [
      makeField("ccc"),
      makeField("aaa"),
      makeField("bbb"),
    ];
    const map = getFieldNumberMap(fields);
    expect(map.get("aaa")).toBe(1);
    expect(map.get("bbb")).toBe(2);
    expect(map.get("ccc")).toBe(3);
    expect(fieldNumber("aaa", fields)).toBe(1);
    expect(fieldNumber("bbb", fields)).toBe(2);
    expect(fieldNumber("ccc", fields)).toBe(3);
  });

  it("returns 1 if field not found", () => {
    const fields = [makeField("aaa")];
    expect(fieldNumber("zzz", fields)).toBe(1);
  });

  it("ranks grades correctly for sorting", () => {
    expect(gradeRank("A")).toBe(4);
    expect(gradeRank("B")).toBe(3);
    expect(gradeRank("C")).toBe(2);
    expect(gradeRank("D")).toBe(1);
  });
});
