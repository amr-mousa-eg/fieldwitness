// Copy real field packs into app/public/packs, where the dev server (VITE_DATA=packs) and the
// build read them. No merge needed: the source is any folder laid out as PLAN.md §3
// (regions.json + one folder per region with index.json, <field_id>*.json, hindcast.json,
// layers.json). app/public/packs is gitignored (app/.gitignore) and is replaced on every run.
//
// Usage (from app/):  node scripts/sync-packs.mjs "<packs folder>" [region_id ...]
//   e.g.              node scripts/sync-packs.mjs "D:/NASA Project/packs"
// With no region ids, every region listed in <packs folder>/regions.json is copied.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const [src, ...only] = process.argv.slice(2);
if (!src) {
  console.error('usage: node scripts/sync-packs.mjs "<packs folder>" [region_id ...]');
  process.exit(2);
}
const SRC = resolve(src);
const DEST = resolve(import.meta.dirname, "..", "public", "packs");
const MARKER = "SYNTHETIC:fixture"; // fixtures must never be copied as packs (see vite.config.ts)

const fail = (msg) => {
  console.error(`sync-packs: ${msg}`);
  process.exit(1);
};

const regionsFile = join(SRC, "regions.json");
if (!existsSync(regionsFile)) fail(`no regions.json in ${SRC}`);
const list = JSON.parse(readFileSync(regionsFile, "utf8"));
const known = list.regions.map((r) => r.region_id);
const unknown = only.filter((r) => !known.includes(r));
if (unknown.length > 0) fail(`not in regions.json: ${unknown.join(", ")} (known: ${known.join(", ")})`);
const regions = only.length > 0 ? list.regions.filter((r) => only.includes(r.region_id)) : list.regions;

for (const r of regions) {
  const dir = join(SRC, r.region_id);
  if (!existsSync(join(dir, "index.json"))) fail(`${r.region_id}/index.json is missing`);
}

rmSync(DEST, { recursive: true, force: true });
mkdirSync(DEST, { recursive: true });
writeFileSync(join(DEST, "regions.json"), JSON.stringify({ ...list, regions }));

let files = 0;
let bytes = 0;
for (const r of regions) {
  const from = join(SRC, r.region_id);
  const to = join(DEST, r.region_id);
  mkdirSync(to);
  for (const name of readdirSync(from).filter((n) => n.endsWith(".json"))) {
    const text = readFileSync(join(from, name), "latin1");
    if (text.includes(MARKER)) fail(`${r.region_id}/${name} contains ${MARKER}: that is a fixture, not a pack`);
    cpSync(join(from, name), join(to, name));
    files += 1;
    bytes += statSync(join(from, name)).size;
  }
  const idx = JSON.parse(readFileSync(join(to, "index.json"), "utf8"));
  console.log(`${r.region_id}: ${idx.fields.length} fields in index.json`);
}
console.log(`copied ${files} files, ${(bytes / 1e6).toFixed(1)} MB, into ${DEST}`);
