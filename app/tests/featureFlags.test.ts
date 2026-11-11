// Rotation Builder and Farm view are on for everybody; ?builder=0 / ?farm=0 are kill switches.
import { afterEach, describe, expect, it } from "vitest";
import { builderEnabled, builderOpenAtStart, farmEnabled } from "../src/featureFlags";

const g = globalThis as Record<string, unknown>;
const at = (search: string) => {
  g.window = { location: { search } };
};

describe("feature flags", () => {
  afterEach(() => {
    delete g.window;
  });

  it("on by default with no query string", () => {
    at("");
    expect(builderEnabled()).toBe(true);
    expect(farmEnabled()).toBe(true);
    expect(builderOpenAtStart()).toBe(false);
  });

  it("?builder=0 turns both off; ?farm=0 turns only the farm off", () => {
    at("?builder=0");
    expect(builderEnabled()).toBe(false);
    expect(farmEnabled()).toBe(false);
    at("?farm=0");
    expect(builderEnabled()).toBe(true);
    expect(farmEnabled()).toBe(false);
    at("?builder=0&farm=1");
    expect(farmEnabled()).toBe(true);
  });

  it("old ?builder=1 links open the builder panel", () => {
    at("?builder=1");
    expect(builderEnabled()).toBe(true);
    expect(builderOpenAtStart()).toBe(true);
  });
});
