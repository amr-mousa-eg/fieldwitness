import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

/** Must match APP_CACHE in public/sw.js. */
const APP_CACHE = `fw-app-${__FW_CACHE_VERSION__}`;

// Offline after the first visit (T9.1). Production only: a dev service worker would cache
// stale modules and fight the dev server.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  const base = import.meta.env.BASE_URL;
  void navigator.serviceWorker.register(`${base}sw.js`, { scope: base });
  // The first visit loads the app files before the service worker exists, so it never sees
  // them. Once it is ready, store what this page already loaded (packs/ go to the data cache).
  void navigator.serviceWorker.ready.then(async () => {
    const root = new URL(base, location.href);
    const packs = new URL("packs/", root).href;
    const loaded = performance
      .getEntriesByType("resource")
      .map((e) => e.name)
      .filter((u) => u.startsWith(root.href) && !u.startsWith(packs));
    const urls = [...new Set([root.href, new URL(workerUrl, location.href).href, ...loaded])];
    const cache = await caches.open(APP_CACHE);
    await Promise.allSettled(urls.map((u) => cache.add(u)));
  });
}
