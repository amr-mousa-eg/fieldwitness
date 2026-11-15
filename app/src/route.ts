import { useEffect, useState } from "react";
import {
  type Constraints,
  DEFAULT_PRIORITIES,
  NO_CONSTRAINTS,
  PRIORITY_KEYS,
  type Priorities,
  isDefault,
} from "./rank";

export type FieldTab = "story" | "options" | "calendar" | "advisor" | "sim3d";
export const TABS: FieldTab[] = ["story", "options", "calendar", "advisor", "sim3d"];

/** Region-level pages. Field ids are 40-hex hashes, so these names never collide with one. */
export type RegionPage = "map" | "scoreboard" | "compare" | "methods" | "add-field";
export const PAGES: RegionPage[] = ["map", "scoreboard", "compare", "methods", "add-field"];

/** App location in the URL hash: #/<region_id>[/<page> | /<field_id>[/<tab>]] or #/add-field. */
export interface Route {
  regionId: string | null;
  page: RegionPage;
  fieldId: string | null;
  tab: FieldTab;
}

export function parseHash(hash: string): Route {
  const clean = hash.split("?")[0];
  const parts = clean
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map(decodeURIComponent);
  if (parts[0] === "add-field") {
    return { regionId: null, page: "add-field", fieldId: null, tab: "story" };
  }
  const [regionId = null, second = null, tab = "story"] = parts;
  const rawSecond = second !== null ? second.split(/[?#]/)[0] : null;
  const normSecond = rawSecond === "glossary" ? "methods" : rawSecond;
  const page = PAGES.includes(normSecond as RegionPage) ? (normSecond as RegionPage) : "map";
  const fieldId = normSecond !== null && !PAGES.includes(normSecond as RegionPage) ? normSecond : null;
  return { regionId, page, fieldId, tab: TABS.includes(tab as FieldTab) ? (tab as FieldTab) : "story" };
}

export function parseCompareQuery(hash: string): { a: string | null; b: string | null } {
  const qIdx = hash.indexOf("?");
  if (qIdx < 0) return { a: null, b: null };
  const params = new URLSearchParams(hash.slice(qIdx + 1));
  return {
    a: params.get("a") || null,
    b: params.get("b") || null,
  };
}

export function compareHref(regionId: string, a?: string | null, b?: string | null): string {
  const params = new URLSearchParams();
  if (a) params.set("a", a);
  if (b) params.set("b", b);
  const qs = params.toString();
  return `#/${encodeURIComponent(regionId)}/compare${qs ? `?${qs}` : ""}`;
}

export function routeHref(regionId: string, fieldId?: string | null, tab?: FieldTab): string {
  const parts = [regionId, fieldId, fieldId ? tab : null]
    .filter((p): p is string => !!p)
    .map(encodeURIComponent);
  return `#/${parts.join("/")}`;
}

export function pageHref(regionId: string, page: RegionPage): string {
  if (page === "add-field") return "#/add-field";
  return page === "map" ? routeHref(regionId) : `#/${encodeURIComponent(regionId)}/${page}`;
}

export interface SharedFieldState {
  hasState: boolean;
  priorities?: Priorities;
  constraints?: Constraints;
  dt?: number;
  dp?: number;
}

const VALID_TEMPS = new Set([0, 1, 2]);
const VALID_RAINS = new Set([-20, -10, 0, 10]);

export function encodeFieldStateQuery(
  p: Priorities,
  c: Constraints,
  dt: number,
  dp: number,
): string {
  const params = new URLSearchParams();
  if (!isDefault(p)) {
    params.set("pw", PRIORITY_KEYS.map((k) => p[k]).join(","));
  }
  if (c.dontWant.length > 0) params.set("no", c.dontWant.join(","));
  if (c.cantGrow.length > 0) params.set("cg", c.cantGrow.join(","));
  if (c.canSell !== null) params.set("cs", c.canSell.join(","));
  if (c.irrigation !== "unset") params.set("irr", c.irrigation);
  if (c.waterCapMm !== null && Number.isFinite(c.waterCapMm)) {
    params.set("cap", String(c.waterCapMm));
  }
  if (dt !== 0 && VALID_TEMPS.has(dt)) params.set("dt", String(dt));
  if (dp !== 0 && VALID_RAINS.has(dp)) params.set("dp", String(dp));
  return params.toString();
}

export function parseFieldStateQuery(hash: string): SharedFieldState {
  const qIdx = hash.indexOf("?");
  if (qIdx < 0) return { hasState: false };
  const params = new URLSearchParams(hash.slice(qIdx + 1));
  const out: SharedFieldState = { hasState: false };

  const pw = params.get("pw");
  if (pw) {
    const nums = pw.split(",").map((x) => Number(x));
    if (nums.length === PRIORITY_KEYS.length && nums.every((n) => Number.isInteger(n) && n >= 0 && n <= 3)) {
      const next = { ...DEFAULT_PRIORITIES };
      PRIORITY_KEYS.forEach((k, i) => {
        next[k] = nums[i];
      });
      out.priorities = next;
      out.hasState = true;
    }
  }

  const noRaw = params.get("no");
  const cgRaw = params.get("cg");
  const csRaw = params.get("cs");
  const irrRaw = params.get("irr");
  const capRaw = params.get("cap");
  if (noRaw !== null || cgRaw !== null || csRaw !== null || irrRaw !== null || capRaw !== null) {
    const c: Constraints = {
      dontWant: noRaw ? noRaw.split(",").filter(Boolean) : [...NO_CONSTRAINTS.dontWant],
      cantGrow: cgRaw ? cgRaw.split(",").filter(Boolean) : [...NO_CONSTRAINTS.cantGrow],
      canSell: csRaw !== null ? csRaw.split(",").filter(Boolean) : null,
      irrigation: irrRaw === "yes" || irrRaw === "no" ? irrRaw : "unset",
      waterCapMm: capRaw !== null && capRaw !== "" && Number.isFinite(Number(capRaw)) ? Number(capRaw) : null,
    };
    out.constraints = c;
    out.hasState = true;
  }

  const dtRaw = params.get("dt");
  const dpRaw = params.get("dp");
  if (dtRaw !== null && VALID_TEMPS.has(Number(dtRaw))) {
    out.dt = Number(dtRaw);
    out.hasState = true;
  }
  if (dpRaw !== null && VALID_RAINS.has(Number(dpRaw))) {
    out.dp = Number(dpRaw);
    out.hasState = true;
  }

  return out;
}

export function fieldStateHref(
  regionId: string,
  fieldId: string,
  tab: FieldTab,
  p: Priorities,
  c: Constraints,
  dt: number,
  dp: number,
): string {
  const base = routeHref(regionId, fieldId, tab);
  const qs = encodeFieldStateQuery(p, c, dt, dp);
  return qs ? `${base}?${qs}` : base;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
