// The production build must refuse to ship SYNTHETIC fixtures (user requirement, Phase 9).
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { build } from "vite";

const APP = resolve(import.meta.dirname, "..");
const FIXTURE = join(APP, "fixtures", "ks_demo_synthetic", "index.SYNTHETIC.json");
const temps: string[] = [];
const savedEnv = process.env.VITE_DATA;

function temp(): string {
  const d = mkdtempSync(join(tmpdir(), "fw-guard-"));
  temps.push(d);
  return d;
}

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

async function prodBuild(publicDir: string | false): Promise<string> {
  const outDir = temp();
  await build({
    root: APP,
    configFile: join(APP, "vite.config.ts"),
    logLevel: "silent",
    publicDir,
    build: { outDir, emptyOutDir: true },
  });
  return outDir;
}

afterEach(() => {
  if (savedEnv === undefined) delete process.env.VITE_DATA;
  else process.env.VITE_DATA = savedEnv;
  for (const d of temps.splice(0)) rmSync(d, { recursive: true, force: true });
});

describe("production build vs synthetic fixtures", () => {
  it("builds without fixtures, and the output holds no fixture file or marker", async () => {
    delete process.env.VITE_DATA;
    const all = files(await prodBuild(false));
    expect(all.length).toBeGreaterThan(0);
    for (const f of all) {
      expect(f).not.toMatch(/SYNTHETIC/);
      expect(readFileSync(f, "latin1")).not.toContain("SYNTHETIC:fixture");
    }
  });

  it("refuses VITE_DATA=fixtures", async () => {
    process.env.VITE_DATA = "fixtures";
    await expect(prodBuild(false)).rejects.toThrow(/Refusing to build with VITE_DATA=fixtures/);
  });

  it("refuses a fixture file copied into public/", async () => {
    delete process.env.VITE_DATA;
    const pub = temp();
    mkdirSync(join(pub, "packs"), { recursive: true });
    copyFileSync(FIXTURE, join(pub, "packs", "index.SYNTHETIC.json"));
    await expect(prodBuild(pub)).rejects.toThrow(/Refusing to ship synthetic fixtures/);
  });

  it("refuses fixture content even under a real-looking name", async () => {
    delete process.env.VITE_DATA;
    const pub = temp();
    mkdirSync(join(pub, "packs", "ks_t14slh"), { recursive: true });
    copyFileSync(
      join(APP, "fixtures", "ks_demo_synthetic", "layers.SYNTHETIC.json"),
      join(pub, "packs", "ks_t14slh", "layers.json"),
    );
    await expect(prodBuild(pub)).rejects.toThrow(/Refusing to ship synthetic fixtures/);
  });
});
