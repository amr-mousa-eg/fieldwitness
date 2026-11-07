# Deployment (prepared, not deployed)

Nothing here creates an account or publishes anything. The owner decides the host and runs the
first deploy.

## Facts checked (2026-11-07)

| | GitHub Pages | Netlify (Free) |
|---|---|---|
| Private repo | **No** on GitHub Free: the Free plan lists "GitHub Pages in public repositories"; private repositories need Pro / Team ([GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)) | **Yes** for a personal account: "Private projects ✓ Owner only"; organization-owned private repos need Pro ([credit-based plans](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/)) |
| Our repo today | `amr-mousa-eg/fieldwitness` is **PRIVATE** (`gh repo view`), so Pages needs it made public first (the challenge wants a public repo anyway) | works as it is |
| Size | site ≤ 1 GB; repo recommended ≤ 1 GB ([Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)) | no size line found on the plan page |
| Traffic | soft limit 100 GB / month (same page) | 300 credits / month, **hard limit**. 1 GB = 20 credits, 10 000 requests = 2 credits, 1 production deploy = 15 credits (same page). What a site shows after the limit is not stated there; forum posts report paused deploys |
| Deploy | Actions workflow (`deploy/github-pages.yml`), manual trigger | drag-and-drop of `app/dist`, or Git-linked build (`app/netlify.toml`) |
| URL path | `https://<owner>.github.io/<repo>/`, so the build needs `VITE_BASE=/<repo>/` | `/` (default) |

## Our load (measured)

- Kansas region: 803 files, 85.7 MB raw, **7.7 MB gzip** (Python `gzip` level 6).
- A first visit in a production build downloads the whole region for offline use
  (`cacheRegionForOffline`, T9.1). That is about 803 requests and about 7.7 MB per first visit,
  **assuming the host serves JSON gzip-compressed** (not verified for either host).
- Estimate, same assumption. Netlify Free: 4 deploys = 60 credits, which leaves 240 credits, or
  about 12 GB. That is about 1 500 first visits per month, plus about 0.16 credits of requests per
  visit. GitHub Pages: 100 GB soft limit, about 13 000 first visits per month.
- Three regions would roughly triple the load per visitor only if all regions were prefetched; today
  only the open region is.

## Packs are not in git

`packs/*` is gitignored except `packs/demo/`. A CI build (GitHub Actions or a Git-linked Netlify
site) only sees packs that are committed. There are two options:

1. **Build locally, upload `app/dist`.** No packs in git. Netlify: drag-and-drop in the UI. Pages:
   it would need a workflow that downloads the packs from a release asset (not prepared).
2. **Commit the demo packs** under `packs/demo/` (the `regions.json` and region folders, about
   86 MB; no file over 1 MB). Both prepared configs then build in CI from `packs/demo`.

## Run it (after the owner says yes)

Local production build on real packs:

```
cd app
node scripts/sync-packs.mjs "D:/NASA Project/packs"
npm run build                                   # Netlify / root path
MSYS_NO_PATHCONV=1 VITE_BASE=/fieldwitness/ npm run build   # Pages path (Git Bash)
```

In Git Bash, `MSYS_NO_PATHCONV=1` is needed. Without it, `/fieldwitness/` is rewritten to
`C:/Program Files/Git/fieldwitness/`, and the build refuses that value.

Checked locally on 2026-11-07 with the `/fieldwitness/` build in `vite preview`:
- `scripts/offline-check.mjs` passes;
- the service worker controls the page;
- the app shell and 200 fields render after an offline reload.

- **GitHub Pages:**
  1. Make the repo public.
  2. Copy `app/deploy/github-pages.yml` to `.github/workflows/pages.yml` on `main`.
  3. Set Settings > Pages > Source to "GitHub Actions".
  4. Run the workflow from the Actions tab.
  - The workflow uses `actions/configure-pages@v5`, `upload-pages-artifact@v4` and
    `deploy-pages@v4`, the versions in GitHub's docs.
  - `checkout@v4` and `setup-node@v4` are not checked against their latest releases (UNVERIFIED).
- **Netlify:**
  - Route A: drop `app/dist` into a manual (drag-and-drop) deploy in the Netlify UI. The exact menu names are not checked.
  - Route B: link the repo with Base directory `app`.
  - `npm i -g netlify-cli` would allow command-line deploys. It is a new package: ask first.
