import { describe, expect, it } from "vitest";
import { emptyCorrections } from "../src/corrections";
import { clearCorrections, loadCorrections, saveCorrections, type StorageLike } from "../src/correctionStore";

const mem = (): StorageLike & { m: Map<string, string> } => {
  const m = new Map<string, string>();
  return {
    m,
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
    removeItem: (k) => void m.delete(k),
  };
};
const throwing: StorageLike = {
  getItem: () => {
    throw new Error("denied");
  },
  setItem: () => {
    throw new Error("quota");
  },
  removeItem: () => {
    throw new Error("denied");
  },
};

describe("correctionStore", () => {
  it("round-trips with numeric keys restored", () => {
    const s = mem();
    const c = { cropByYear: { 2022: "maize" }, sowingDay: { 2022: 120 }, irrigated: true };
    expect(saveCorrections("f1", c, s)).toBe(true);
    expect(loadCorrections("f1", s)).toEqual(c);
  });
  it("is per field", () => {
    const s = mem();
    saveCorrections("f1", { ...emptyCorrections(), irrigated: false }, s);
    expect(loadCorrections("f2", s)).toEqual(emptyCorrections());
  });
  it("empty set removes the entry; clear works", () => {
    const s = mem();
    saveCorrections("f1", { ...emptyCorrections(), irrigated: false }, s);
    saveCorrections("f1", emptyCorrections(), s);
    expect(s.m.size).toBe(0);
    saveCorrections("f1", { ...emptyCorrections(), irrigated: true }, s);
    expect(clearCorrections("f1", s)).toBe(true);
    expect(s.m.size).toBe(0);
  });
  it("bad JSON or wrong shape gives empty", () => {
    const s = mem();
    s.setItem("fw.corrections.v1.f1", "{not json");
    expect(loadCorrections("f1", s)).toEqual(emptyCorrections());
    s.setItem("fw.corrections.v1.f1", JSON.stringify({ cropByYear: { a: 1 }, sowingDay: {}, irrigated: null }));
    expect(loadCorrections("f1", s)).toEqual(emptyCorrections());
  });
  it("works when storage is unavailable or throws", () => {
    expect(loadCorrections("f1", null)).toEqual(emptyCorrections());
    expect(saveCorrections("f1", { ...emptyCorrections(), irrigated: true }, null)).toBe(false);
    expect(loadCorrections("f1", throwing)).toEqual(emptyCorrections());
    expect(saveCorrections("f1", { ...emptyCorrections(), irrigated: true }, throwing)).toBe(false);
    expect(clearCorrections("f1", throwing)).toBe(false);
  });
});
