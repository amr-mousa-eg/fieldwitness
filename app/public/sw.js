// FieldWitness service worker (production only; registered in src/main.tsx).
// - App files under assets/ have hashed names: cache first.
// - Pages and packs/: network first, so data stays fresh online; the cached copy is used offline.
const APP_CACHE = "fw-app-v1";
const DATA_CACHE = "fw-data-v1"; // must match src/data.ts
const KEEP = [APP_CACHE, DATA_CACHE];

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !KEEP.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function cacheFirst(request) {
  const hit = await caches.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (res.ok) (await caches.open(APP_CACHE)).put(request, res.clone());
  return res;
}

// A static host may answer a missing pack with index.html and status 200: never store that as data.
const storable = (res, cacheName) =>
  res.ok && (cacheName !== DATA_CACHE || (res.headers.get("content-type") || "").includes("json"));

async function networkFirst(request, cacheName) {
  try {
    const res = await fetch(request);
    if (storable(res, cacheName)) (await caches.open(cacheName)).put(request, res.clone());
    return res;
  } catch (err) {
    const hit = await caches.match(request, { ignoreSearch: request.mode === "navigate" });
    if (hit) return hit;
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  const scope = new URL(self.registration.scope).pathname;
  const path = url.pathname.slice(scope.length);
  if (path.startsWith("assets/")) event.respondWith(cacheFirst(request));
  else if (path.startsWith("packs/")) event.respondWith(networkFirst(request, DATA_CACHE));
  else event.respondWith(networkFirst(request, APP_CACHE));
});
