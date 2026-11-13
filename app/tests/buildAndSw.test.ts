import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "vite";
import { afterEach, describe, expect, it } from "vitest";

const APP = resolve(import.meta.dirname, "..");
const temps: string[] = [];

afterEach(() => {
  for (const d of temps.splice(0)) rmSync(d, { recursive: true, force: true });
});

describe("Phase 5 bundle splitting and service worker versioning", () => {
  it("isolates heavy vendor chunks and stamps dist/sw.js cache version identically to main bundle", async () => {
    const outDir = mkdtempSync(join(tmpdir(), "fw-sw-"));
    temps.push(outDir);
    const prevData = process.env.VITE_DATA;
    const prevNodeEnv = process.env.NODE_ENV;
    delete process.env.VITE_DATA;
    process.env.NODE_ENV = "production";

    try {
      await build({
        root: APP,
        mode: "production",
        configFile: join(APP, "vite.config.ts"),
        logLevel: "silent",
        build: { outDir, emptyOutDir: true },
      });
    } finally {
      if (prevData === undefined) delete process.env.VITE_DATA;
      else process.env.VITE_DATA = prevData;
      if (prevNodeEnv === undefined) delete process.env.NODE_ENV;
      else process.env.NODE_ENV = prevNodeEnv;
    }

    const assetsDir = join(outDir, "assets");
    const assetFiles = readdirSync(assetsDir);

    expect(assetFiles.some((f) => f.startsWith("vendor-maplibre-") && f.endsWith(".js"))).toBe(true);
    expect(assetFiles.some((f) => f.startsWith("vendor-three-") && f.endsWith(".js"))).toBe(true);
    expect(assetFiles.some((f) => f.startsWith("vendor-charts-") && f.endsWith(".js"))).toBe(true);
    expect(assetFiles.some((f) => f.startsWith("vendor-react-") && f.endsWith(".js"))).toBe(true);

    const swPath = join(outDir, "sw.js");
    expect(existsSync(swPath)).toBe(true);
    const swText = readFileSync(swPath, "utf-8");
    expect(swText).not.toContain('"v2-dev"');
    const match = /const CACHE_VERSION = "([^"]+)"/.exec(swText);
    expect(match?.[1]).toMatch(/^v2-[a-z0-9]+$/i);

    const indexBundle = assetFiles.find((f) => f.startsWith("index-") && f.endsWith(".js"));
    expect(indexBundle).toBeDefined();
    const indexText = readFileSync(join(assetsDir, indexBundle!), "utf-8");
    expect(indexText).toContain(`fw-app-${match![1]}`);
  });
});
