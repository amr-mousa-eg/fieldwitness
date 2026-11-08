import { useEffect, useState } from "react";

export type FieldTab = "story" | "options" | "calendar" | "advisor";
export const TABS: FieldTab[] = ["story", "options", "calendar", "advisor"];

/** Region-level pages. Field ids are 40-hex hashes, so these names never collide with one. */
export type RegionPage = "map" | "scoreboard" | "methods" | "add-field";
export const PAGES: RegionPage[] = ["map", "scoreboard", "methods", "add-field"];

/** App location in the URL hash: #/<region_id>[/<page> | /<field_id>[/<tab>]] or #/add-field. */
export interface Route {
  regionId: string | null;
  page: RegionPage;
  fieldId: string | null;
  tab: FieldTab;
}

export function parseHash(hash: string): Route {
  const parts = hash
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map(decodeURIComponent);
  if (parts[0] === "add-field") {
    return { regionId: null, page: "add-field", fieldId: null, tab: "story" };
  }
  const [regionId = null, second = null, tab = "story"] = parts;
  const page = PAGES.includes(second as RegionPage) ? (second as RegionPage) : "map";
  const fieldId = second !== null && !PAGES.includes(second as RegionPage) ? second : null;
  return { regionId, page, fieldId, tab: TABS.includes(tab as FieldTab) ? (tab as FieldTab) : "story" };
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

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
