import { useEffect, useState } from "react";

export type FieldTab = "story" | "options";
const TABS: FieldTab[] = ["story", "options"];

/** App location in the URL hash: #/<region_id>[/<field_id>[/<tab>]]. */
export interface Route {
  regionId: string | null;
  fieldId: string | null;
  tab: FieldTab;
}

export function parseHash(hash: string): Route {
  const [regionId = null, fieldId = null, tab = "story"] = hash
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map(decodeURIComponent);
  return { regionId, fieldId, tab: TABS.includes(tab as FieldTab) ? (tab as FieldTab) : "story" };
}

export function routeHref(regionId: string, fieldId?: string | null, tab?: FieldTab): string {
  const parts = [regionId, fieldId, fieldId ? tab : null]
    .filter((p): p is string => !!p)
    .map(encodeURIComponent);
  return `#/${parts.join("/")}`;
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
