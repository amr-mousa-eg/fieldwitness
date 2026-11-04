import { useEffect, useState } from "react";

/** App location in the URL hash: #/<region_id> or #/<region_id>/<field_id>. */
export interface Route {
  regionId: string | null;
  fieldId: string | null;
}

export function parseHash(hash: string): Route {
  const [regionId = null, fieldId = null] = hash
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map(decodeURIComponent);
  return { regionId, fieldId };
}

export function routeHref(regionId: string, fieldId?: string | null): string {
  const parts = [regionId, fieldId].filter((p): p is string => !!p).map(encodeURIComponent);
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
