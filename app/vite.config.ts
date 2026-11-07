/// <reference types="vitest/config" />
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Data modes.
 *  - "fixtures": SYNTHETIC demo data from app/fixtures, served by the dev server only.
 *  - "packs":    real field packs under public/packs (after Gate 6 and the merge).
 * Default: fixtures in dev, packs in a build. A build with fixtures is refused.
 */
const FIXTURES_DIR = resolve(import.meta.dirname, "fixtures");
const FIXTURE_FILE = /\.SYNTHETIC\.json$/;
const FIXTURE_MARKER = "SYNTHETIC:fixture"; // every Tagged.source in the fixtures

function dataMode(command: "serve" | "build"): "fixtures" | "packs" {
  const m = process.env.VITE_DATA ?? (command === "serve" ? "fixtures" : "packs");
  if (m !== "fixtures" && m !== "packs") throw new Error(`VITE_DATA must be fixtures|packs, got ${m}`);
  return m;
}

/** Dev only: /packs/<path>.json -> fixtures/<path>.SYNTHETIC.json */
function serveFixtures(): Plugin {
  return {
    name: "fieldwitness-serve-fixtures",
    apply: (_, env) => env.command === "serve" && dataMode("serve") === "fixtures",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = decodeURIComponent((req.url ?? "").split("?")[0]);
        if (!url.startsWith("/packs/")) return next();
        const m = /^\/packs\/([\w./-]+)\.json$/.exec(url);
        const file = m && !m[1].includes("..") && join(FIXTURES_DIR, `${m[1]}.SYNTHETIC.json`);
        if (!file || !existsSync(file)) {
          res.statusCode = 404; // never fall back to index.html for data
          return res.end();
        }
        res.setHeader("Content-Type", "application/json");
        res.end(readFileSync(file));
      });
    },
  };
}

function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

/** Build only: refuse fixture mode, and fail if any fixture file or marker reaches the output. */
export function refuseFixtures(): Plugin {
  let outDir = "";
  return {
    name: "fieldwitness-refuse-fixtures",
    apply: "build",
    configResolved(config) {
      if (dataMode("build") === "fixtures") {
        throw new Error("Refusing to build with VITE_DATA=fixtures: synthetic data must not ship.");
      }
      outDir = resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      const bad = walk(outDir).filter(
        (p) => FIXTURE_FILE.test(p) || readFileSync(p, "latin1").includes(FIXTURE_MARKER),
      );
      if (bad.length > 0) {
        throw new Error(`Refusing to ship synthetic fixtures in the build:\n  ${bad.join("\n  ")}`);
      }
    },
  };
}

/**
 * Public path the app is served from: "/" (Netlify, local) or "/<repo>/" (a GitHub Pages project
 * site). Data, the service worker and its scope all follow it (import.meta.env.BASE_URL).
 */
function basePath(): string {
  const b = process.env.VITE_BASE ?? "/";
  if (!b.startsWith("/") || !b.endsWith("/")) throw new Error(`VITE_BASE must start and end with "/", got ${b}`);
  return b;
}

export default defineConfig(({ command }) => ({
  base: basePath(),
  plugins: [react(), serveFixtures(), refuseFixtures()],
  // The app reads this to show the DEMO DATA banner; a build can only be "packs".
  define: { __FW_DATA_MODE__: JSON.stringify(dataMode(command)) },
  test: { environment: "node", testTimeout: 120_000 },
}));
