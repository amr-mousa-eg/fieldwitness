# FieldWitness — migration and continuation plan

Prepared 8 Nov 2026 for moving `D:\NASA Project` to a second Windows laptop and continuing with a different AI coding environment.

**Status of this document:** plan only. Nothing here has been executed. Every command is read-only until §3 Phase A, and Phase A only starts after you approve it.

**Evidence levels used throughout**

| Label | Meaning |
|---|---|
| **REPORTED** | Stated by a Claude Code session or the autopilot during this project (commit hashes, test counts, file paths). Not re-inspected for this plan. |
| **TO VERIFY** | Must be confirmed by the inspection in §0 before migration. |
| **UNKNOWN** | No evidence either way. |

---

## 0. Inspection first (read-only, old laptop)

Run in **PowerShell**, from **`D:\NASA Project`**. Nothing here changes any file. Save the whole output (it contains no secrets) and keep it with this plan; it becomes the factual basis for §1–§2.

**Before you start:** stop the autopilot cleanly so the state doesn't move while you inspect.

```powershell
# Directory: D:\NASA Project
New-Item AUTOPILOT_STOP -ItemType File
# Wait until the loop window prints: AUTOPILOT_STOP found - stopping.
```

**Inspection block** (copy all of it; output goes to the console and to a file in your Documents folder, outside the repo):

```powershell
# Directory: D:\NASA Project
$out = "$HOME\Documents\fieldwitness_inspection_$(Get-Date -Format yyyyMMdd-HHmm).txt"
& {
  "=== TOOLS ==="
  git --version; uv --version; node --version; npm --version
  try { gitleaks version } catch { "gitleaks: not on PATH" }
  try { claude --version } catch { "claude: not on PATH" }
  uv python list --only-installed

  "=== GIT: branch, remote, sync ==="
  git status --short --branch
  git remote -v
  git branch -a -vv
  git fetch origin --prune --dry-run 2>&1
  "ahead/behind (left=origin/main, right=main):"; git rev-list --left-right --count origin/main...main
  "last commit:"; git log -1 --format="%H %ci %s"
  "stash:"; git stash list
  "worktrees:"; git worktree list
  "local config (no credentials expected):"; git config --local --list

  "=== GIT: nested repositories (expect only .\.git) ==="
  Get-ChildItem -Force -Recurse -Directory -Filter .git -ErrorAction SilentlyContinue |
    Where-Object FullName -notmatch 'node_modules' | Select-Object -ExpandProperty FullName

  "=== WORKING TREE ==="
  "modified/staged:"; git status --porcelain
  "untracked, not ignored:"; git ls-files --others --exclude-standard
  "ignored top-level items:"; git status --ignored --porcelain | Select-String '^!!' | ForEach-Object { $_.Line } | Select-Object -First 60

  "=== SIZES OF IGNORED FOLDERS (MB) ==="
  foreach ($p in 'data','packs','docs\refs','logs','results','app\node_modules','app\public\packs','app\dist','.venv') {
    if (Test-Path $p) {
      $s = (Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum)
      "{0,-20} {1,10:N1} MB {2,8} files" -f $p, ($s.Sum/1MB), $s.Count
    } else { "{0,-20} (absent)" -f $p }
  }

  "=== AUTOPILOT STATE ==="
  "BLOCKED.md: $(Test-Path BLOCKED.md)"; if (Test-Path BLOCKED.md) { Get-Content BLOCKED.md }
  "AUTOPILOT_STOP: $(Test-Path AUTOPILOT_STOP)"; "AUTOPILOT_WAIT: $(Test-Path AUTOPILOT_WAIT)"
  "last runs:"; Get-Content logs\autopilot\runs.csv -Tail 5
  "review queue present: $(Test-Path docs\review_queue.md)"

  "=== PLAN PROGRESS ==="
  "ticked: " + (Select-String -Path PLAN.md -Pattern '^\s*- \[x\]').Count
  "open:   " + (Select-String -Path PLAN.md -Pattern '^\s*- \[ \]').Count
  "open tasks:"; Select-String -Path PLAN.md -Pattern '^\s*- \[ \]' | ForEach-Object { $_.Line.Trim().Substring(0, [Math]::Min(110, $_.Line.Trim().Length)) }
  "gate reviews:"; Get-ChildItem docs\gates -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name

  "=== DOCUMENTATION FILES ==="
  Get-ChildItem -File *.md | Select-Object -ExpandProperty Name
  Get-ChildItem docs -Recurse -File -Include *.md -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName

  "=== HANDOFF (first 40 lines) ==="
  $t = Get-Content DECISIONS.md; $i = ($t | Select-String '^## Autopilot handoff').LineNumber | Select-Object -First 1
  if ($i) { $t[($i-1)..([Math]::Min($t.Count-1, $i+40))] } else { "no handoff section found" }

  "=== ANTI-GRAVITY MENTIONS (tracked files) ==="
  git grep -n -i -E "anti.?gravity" ; if ($LASTEXITCODE -eq 1) { "none found" }

  "=== CI ==="
  Get-ChildItem .github\workflows | Select-Object -ExpandProperty Name
} *>&1 | Tee-Object -FilePath $out
"Saved to $out"
```

**What a healthy result looks like**

- `git status --short --branch` → `## main...origin/main` with **no** `[ahead N]` and no file lines.
- ahead/behind → `0	0`.
- Nested repositories → only `D:\NASA Project\.git`. Any `app\.git` would mean the app is a separate repository (not expected: it was merged with `git merge` in `cd3a25a`).
- Worktrees → only `D:/NASA Project`. If `D:/NASA Project-app` still appears, run `git worktree prune` before migrating.
- Untracked, not ignored → empty. Anything listed here is **not** in git and **not** covered by `.gitignore`; decide about each file before migration (see §6).

---

## 1. Current project state report

### 1.1 The project

**FieldWitness** — NASA Space Apps 2026 entry for "Field Shift: Adapting Farms with NASA Data". A crop-rotation decision-support web app: for a field, it reconstructs the field's history from NASA HLS satellite data, simulates rotation options with a FAO-56 water-balance model calibrated to that history, compares them with natural experiments in neighbouring fields, grades the evidence A–D, explains every option (why, evidence, benefits, gaps, risks), and scores its own predictions against later seasons (hindcast). Hackathon: 14–15 Nov 2026; official rules and submission guide released 13 Nov.

### 1.2 Repository structure (REPORTED; confirm with §0)

One Git repository, `D:\NASA Project`, remote `origin = https://github.com/amr-mousa-eg/fieldwitness.git` (private).

```
CLAUDE.md            standing rules for any AI coding session (hard rules, workflow, environment)
PLAN.md              roadmap: phases 0–10, task IDs with acceptance tests, gates, schedule, schemas (§3, §3b)
DECISIONS.md         decision log (dated entries) + "## Autopilot handoff" (current state, next tasks)
AUTOPILOT_PROMPT.md  per-run instructions of the unattended Claude Code loop (rules apply to any agent)
DATA.md              every dataset, URL, licence, attribution
README.md, AI_USE.md moved from docs/drafts at the Gate 6 merge, still marked DRAFT
config/              regions.yaml, crops.yaml (FAO-56 values with refs), grading.yaml, ranking config
src/fieldwitness/    Python pipeline: data/, resolve/, story/, physics/, infer/, neighbours/, rotate/, ledger/, packs/, schemas.py, cli
app/                 React + Vite + TypeScript + MapLibre + Recharts web app (merged from branch app)
scripts/             autopilot.ps1, check_*.py, t6x/t7x analysis scripts, fixtures, sync scripts
tests/               pytest suite (241 tests at last report) + app tests in app/tests (45 at last report)
docs/                api_notes.md, census/, gates/, official_challenge.md, fao56_equations.md, hcat_annual_arable.md,
                     schema_ext_proposal.md, drafts/submission.md, (review_queue.md when first used)
results/             validation outputs (classifier, story, inference, neighbours, rotate, hindcast)
.claude/settings.json  Claude Code permission allow/deny lists (Claude-specific)
.github/workflows/   CI: lint + tests, gitleaks secret scan
```

Gitignored (therefore **not** on GitHub): `data/`, `packs/` (generated packs), `docs/refs/` (FAO-56 equation images), `logs/`, `app/node_modules/`, `app/public/packs/`, `app/dist/`, `.venv/`, `BLOCKED.md`, `AUTOPILOT_STOP`, `AUTOPILOT_WAIT`.

### 1.3 What is done (REPORTED)

| Area | Status |
|---|---|
| Phase 0 setup, data access, census, configs | Done. Regions: Kansas T14SLH (Tier 1), Toulouse T31TCJ (Tier 2), central Ukraine T36UVU (Tier 3); Nile Delta T36RTV for the confidence map only |
| Phase 1 data (Kansas) | Done: as_of leakage guard, POWER, SoilGrids (WCS fallback), 200 pilot fields, HLS-VI series (1.3 GB via AppEEARS), CSB labels, SMAP/GRACE/slope context |
| Phase 2 field story | T2.1, T2.2 done; **T2.2 is a recorded negative result** (78.3 % on the fresh test vs a 90 % target); T2.3 classifier **deferred** to the Tier 2/3 day |
| Phase 3 physics | Done: FAO-56 ETo verified against Example 18 (3.88 mm/day), Kc curve, water balance, batched multi-year rotation engine, vulnerability calendar |
| Phase 4 calibration | Done except **T4.6 (WIMAS irrigation check): waiting for a manual download by the user** (docs/wimas_request.md when written) |
| Phase 6 rotation engine | Done: Current option, candidates with constraints, ranking (RYI per rotation year), what-to-measure-next, grades, five-part explanations, priority metrics, what-if scenarios, farmer corrections (T6.9) |
| Phase 7 hindcast | Done: forecast + forced modes, baselines B0–B3, winter wheat included, skill-vs-field-size, degraded observations, ablation. **Skill is weak and reported as is** |
| Phase 8 packs | Done: 200 Kansas packs in `packs/ks_t14slh/`, validator 0 problems; rank bug fixed (ce69ebf); app types generated (T8.2) |
| Phase 9 app | All views built and running on real Kansas packs; offline cache; explainers; map layers; methods page |
| Phase 5 neighbours | T5.4 literature check done (descriptive only); **T5.x matching-history design blocked** by tool-output compression (see §1.5) |

### 1.4 What remains (REPORTED; confirm open boxes in §0)

1. Phase 5 neighbour evidence (T5.x design, T5.2 double ML, T5.3 diagnostics).
2. Deployment (T9.8): Netlify account exists; plan is a ~40-field demo set, dragged as a built folder. Repo stays private until the user decides.
3. Tier 2/3 regions (Toulouse, Ukraine), T2.3 classifier, Nile confidence map — extras.
4. WIMAS manual download (T4.6), OpenET (stretch, terms unread).
5. Phase 10: LICENSE (missing), README/AI_USE final, red-team review, official rules check (13 Nov), demo video or 7 slides, submission page, References field.
6. Optional polish: app bundle 1.77 MB (lazy-load the map), POWER and GBIF/USDA licence confirmation in DATA.md.

### 1.5 Known issues that matter for the move

| Issue | Effect on the new laptop |
|---|---|
| **caveman plugin** compresses tool output in Claude Code sessions (it blocked T5.x reads) | Disappears if the new environment doesn't install it. Do not install it on the new laptop. |
| `uv` was on PATH only via `%APPDATA%\Python\Python315\Scripts` | Install uv with its standalone installer on the new laptop instead (§4). |
| Earthdata credentials live in `%USERPROFILE%\_netrc` | Must be recreated by hand (§5, §6). Never copied. |
| Folder trust for Claude Code is in `~/.claude.json` | Machine-specific; only relevant if Claude Code is used on the new laptop. |
| Absolute paths in docs and handoff (`D:/NASA Project`, `C:\Users\Amr 13_03`) | Use the same project path `D:\NASA Project` on the new laptop if it has a D: drive; otherwise update the handoff note (§7). |
| CI tests that read `data/` use the `needs_data` marker | CI stays green without data; locally they run only when `data/` is restored. |
| Slow, unstable connection | Copy `data/` (1.3 GB+) by drive, don't re-download. `git config http.lowSpeedLimit/lowSpeedTime` is repo-local and must be set again. |

### 1.6 Autopilot: is it finished?

**No (REPORTED).** The loop is a Claude Code workflow (`scripts/autopilot.ps1` → `claude -p`). Its last known state: Phase 5 subtask T5.xa blocked; the remaining work is listed in §1.4. A stop file existing does **not** mean the work is complete — §0 shows the real state (open boxes in PLAN.md, `BLOCKED.md`, the handoff).

---

## 2. Repository and Git status report

| Item | Value | Evidence |
|---|---|---|
| Repositories | 1 (`D:\NASA Project`) | REPORTED; nested `.git` check in §0 |
| Remote | `origin https://github.com/amr-mousa-eg/fieldwitness.git` | REPORTED |
| Visibility | Private | REPORTED (GitHub page) |
| Branches | `main` (active); `app` (pushed to origin, merged into main at `cd3a25a`) | REPORTED; `git branch -a -vv` in §0 |
| Last known commit | `d54f122` (T7.4c) or later | REPORTED; TO VERIFY |
| Commit identity | repo-local `user.name amr-mousa-eg`, `user.email 352196580+amr-mousa-eg@users.noreply.github.com` | REPORTED |
| Repo-local tuning | `http.lowSpeedLimit 1000`, `http.lowSpeedTime 20` | REPORTED |
| Worktree `D:\NASA Project-app` | Removed; prune state | TO VERIFY |
| Unpushed commits, stash, uncommitted or untracked files | — | TO VERIFY (§0) |
| CI | Green since `34ac382` (needs_data fix) | REPORTED |
| Branch protection | None (GitHub banner dismissed) | REPORTED |

**Rule for migration:** the GitHub remote must hold everything that is tracked. Only gitignored data moves by drive.

---

## 3. Exact migration checklist

Replace `E:` with the letter of your external drive. All paths are quoted because they contain spaces.

### Phase A — old laptop (after you approve this plan)

| # | Directory | Command | Success looks like |
|---|---|---|---|
| A1 | `D:\NASA Project` | Autopilot stopped (§0) | Loop window shows `AUTOPILOT_STOP found - stopping.` |
| A2 | `D:\NASA Project` | Resolve every item from §0 "modified/staged" and "untracked": commit through a normal session, or list it for manual copy | `git status --porcelain` prints nothing |
| A3 | `D:\NASA Project` | `git push origin main` | `Everything up-to-date` or `main -> main` |
| A4 | `D:\NASA Project` | `git rev-list --left-right --count origin/main...main` | `0	0` |
| A5 | `D:\NASA Project` | `git ls-remote --heads origin` | lines for `refs/heads/main` and `refs/heads/app` |
| A6 | `D:\NASA Project` | `git bundle create "E:\fieldwitness\fieldwitness-all.bundle" --all` (offline backup of every branch and commit) | file created; `git bundle verify "E:\fieldwitness\fieldwitness-all.bundle"` ends with `is okay` |
| A7 | `D:\NASA Project` | Copy the ignored folders (below) | robocopy summary: `Failed 0` |
| A8 | `D:\NASA Project` | Write a size/count manifest (below) | `E:\fieldwitness\manifest_old.csv` exists |

**A7 — copy the ignored folders** (robocopy copies only; it never deletes from the source):

```powershell
# Directory: D:\NASA Project
$dst = "E:\fieldwitness\ignored"
foreach ($p in 'data','packs','docs\refs','logs') {
  if (Test-Path $p) { robocopy $p "$dst\$p" /E /COPY:DAT /DCOPY:T /R:2 /W:2 /NP /LOG+:"E:\fieldwitness\robocopy.log" }
}
```

Folders deliberately **not** copied (regenerated on the new laptop): `app\node_modules`, `app\dist`, `app\public\packs` (rebuilt by `node scripts/sync-packs.mjs ../packs`), `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`.
`logs\` is optional (autopilot history and run logs; useful for audit, not needed to work).

**A8 — manifest:**

```powershell
# Directory: D:\NASA Project
foreach ($p in 'data','packs','docs\refs','logs') { if (Test-Path $p) {
  $s = Get-ChildItem $p -Recurse -File -Force | Measure-Object Length -Sum
  "$p,$($s.Count),$($s.Sum)" } } | Set-Content "E:\fieldwitness\manifest_old.csv"
```

**Leave the old laptop untouched** after Phase A: no deletions, no cleanup, no uninstalls, until §10 passes on the new laptop and ideally until after submission (16 Nov).

### Phase B — new laptop

| # | Directory | Command | Success looks like |
|---|---|---|---|
| B1 | any | Install software (§4) | each `--version` prints a version |
| B2 | any | GitHub sign-in (§5) | `gh auth status` → `Logged in to github.com account amr-mousa-eg` |
| B3 | `D:\` | `gh repo clone amr-mousa-eg/fieldwitness "D:\NASA Project"` | `Cloning into 'D:\NASA Project'...` then done |
| B4 | `D:\NASA Project` | `git log -1 --format="%H"` | identical hash to A4's `git log -1` on the old laptop |
| B5 | `D:\NASA Project` | `git branch -a` | `* main`, `remotes/origin/main`, `remotes/origin/app` |
| B6 | `D:\NASA Project` | repo-local settings (below) | `git config --local --list` shows them |
| B7 | `D:\NASA Project` | restore ignored folders (below) | robocopy `Failed 0`; manifest identical |
| B8 | `D:\NASA Project` | `uv sync --frozen` | ends without error; `.venv` created |
| B9 | `D:\NASA Project` | `uv run pre-commit install` | `pre-commit installed at .git\hooks\pre-commit` |
| B10 | `D:\NASA Project\app` | `npm ci` | `added N packages`, no `ERR!` |
| B11 | `D:\NASA Project\app` | `node scripts/sync-packs.mjs ../packs` | reports 803 files copied (200 fields) |
| B12 | any | Earthdata `_netrc` (§5) | `Test-Path "$HOME\_netrc"` → `True` |
| B13 | `D:\NASA Project` | Full verification (§10) | all checks pass |

**B6 — repo-local settings** (same values as the old laptop):

```powershell
# Directory: D:\NASA Project
git config --local user.name "amr-mousa-eg"
git config --local user.email "352196580+amr-mousa-eg@users.noreply.github.com"
git config --local http.lowSpeedLimit 1000
git config --local http.lowSpeedTime 20
```

**B7 — restore and compare:**

```powershell
# Directory: D:\NASA Project
$src = "E:\fieldwitness\ignored"
foreach ($p in 'data','packs','docs\refs','logs') {
  if (Test-Path "$src\$p") { robocopy "$src\$p" $p /E /COPY:DAT /DCOPY:T /R:2 /W:2 /NP }
}
foreach ($p in 'data','packs','docs\refs','logs') { if (Test-Path $p) {
  $s = Get-ChildItem $p -Recurse -File -Force | Measure-Object Length -Sum
  "$p,$($s.Count),$($s.Sum)" } } | Set-Content "E:\fieldwitness\manifest_new.csv"
Compare-Object (Get-Content "E:\fieldwitness\manifest_old.csv") (Get-Content "E:\fieldwitness\manifest_new.csv")
```

Success: `Compare-Object` prints **nothing**.

**Why clone instead of copying the whole folder:** a clone proves that GitHub holds the complete history (B4–B5), gives a clean `.git` without machine-specific state (old worktree entries, hooks pointing at old paths), and avoids copying `node_modules`/`.venv`, which are not portable. The bundle from A6 is the offline fallback if GitHub is unreachable: `git clone "E:\fieldwitness\fieldwitness-all.bundle" "D:\NASA Project"`, then `git remote set-url origin https://github.com/amr-mousa-eg/fieldwitness.git`.

If the new laptop has no D: drive, use another path (e.g. `C:\Projects\NASA Project`) and record it in the handoff (§7).

---

## 4. New laptop software and dependencies

| Tool | Version target | How | Check (any directory) |
|---|---|---|---|
| Git for Windows | current | git-scm.com installer (includes Git Credential Manager) | `git --version` |
| GitHub CLI | current | cli.github.com installer | `gh --version` |
| uv | 0.13.x or newer | standalone installer from docs.astral.sh/uv (PowerShell one-liner on that page); **not** via pip | `uv --version` |
| Python | 3.12 (pinned in `.python-version`) | installed automatically by `uv sync`, or `uv python install 3.12` | `uv run python --version` → `Python 3.12.x` |
| Node.js | same major version as the old laptop (from §0) | nodejs.org LTS installer | `node --version`, `npm --version` |
| gitleaks | 8.30.1 (same as the pre-commit hook and CI) | release binary from github.com/gitleaks/gitleaks, verify the published checksum, put on PATH | `gitleaks version` |
| Google Antigravity | current | official site; sign in with your Google account (§8.1) | opens `D:\NASA Project` as workspace |
| Claude Code | optional | only if you want the autopilot loop on this laptop | `claude --version` |

Do **not** install the caveman plugin on the new laptop.

Python packages are pinned by `uv.lock` (`uv sync --frozen` installs exactly those versions, including scikit-learn 1.9.1 and doubleml 0.11.4). Node packages are pinned by `app/package-lock.json` (`npm ci`).

Environment variables to set again: **none required**. Optional: `UV_HTTP_TIMEOUT=300` (user variable) because of the slow connection. Earthdata uses `_netrc`, not variables.

---

## 5. GitHub account and authentication

Recommended approach: **HTTPS with the GitHub CLI** (no SSH keys to create, copy or protect; same as the old laptop's HTTPS remote).

```powershell
# Directory: any
gh auth login
#   choose: GitHub.com → HTTPS → Yes (authenticate Git with your GitHub credentials) → Login with a web browser
#   enter the one-time code in the browser, approve as amr-mousa-eg
gh auth status
#   success: "Logged in to github.com account amr-mousa-eg"
gh auth setup-git
#   makes git use gh for HTTPS credentials
```

Then clone (§3 B3) and set the repo-local identity (§3 B6). Commits keep the GitHub no-reply email, so your personal email stays out of the history.

**Earthdata `_netrc` (recreate, never copy).** Type the values yourself; nothing is echoed or saved in history:

```powershell
# Directory: any
$u = Read-Host "Earthdata USERNAME"
$p = Read-Host "Earthdata password" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))
Set-Content -Path "$HOME\_netrc" -Value "machine urs.earthdata.nasa.gov login $u password `"$plain`"" -Encoding ascii -NoNewline
Remove-Variable plain, p
```

Check its structure without showing it:

```powershell
(Get-Content "$HOME\_netrc" -Raw) -split '\s+(?=(?:[^"]*"[^"]*")*[^"]*$)' | ForEach-Object { if ($_ -in 'machine','urs.earthdata.nasa.gov','login','password') { $_ } else { '<value>' } }
```

Success: six lines — `machine`, `urs.earthdata.nasa.gov`, `login`, `<value>`, `password`, `<value>`.

**Netlify:** sign in through the browser when deploying; nothing to configure in the repo.

**Safety rules for this phase:** no force push, no branch deletion, no merges, no visibility change, no secrets in files or logs.

---

## 6. Secure file transfer checklist

**Never copy** (recreate on the new laptop instead):

- `%USERPROFILE%\_netrc` or `.netrc` (Earthdata password)
- Git Credential Manager / Windows Credential Manager entries, `gh` tokens
- `%USERPROFILE%\.claude.json`, `%USERPROFILE%\.claude\` (Claude Code login, settings, plugins, memory)
- Browser profiles, cookies, password stores
- Any file with `token`, `secret`, `.env` in its name — none are expected in the repo; §0 "untracked" would show them

**Copy only** the folders in §3 A7. Before copying, scan the ignored folders that could contain text logs:

```powershell
# Directory: D:\NASA Project
gitleaks dir logs --no-banner
gitleaks dir docs\refs --no-banner
```

Success: `no leaks found`. (If your gitleaks version uses a different subcommand for directory scans, use the one the pre-commit hook in `.pre-commit-config.yaml` uses.)

**Untracked files from §0:** each one is either committed (if it is project work), copied with the ignored folders (if it is data), or left on the old laptop (if it is a leftover such as a scratch script). Decide per file; nothing is deleted on the old laptop.

**External drive:** keep it until §10 passes; afterwards it can stay as an offline backup until after submission.

---

## 7. Documentation updates required (proposed; apply on the new laptop after §10 passes, as one commit)

No new documentation system is created. Changes go into the existing files:

1. **DECISIONS.md — new dated entry "Migration to second laptop (date)":** what moved (repo by clone, ignored folders by drive, manifest identical), new environment (tool versions from §10), project path, that the Claude Code autopilot is paused, which AI environment continues, and that `_netrc` and GitHub auth were recreated.
2. **DECISIONS.md — handoff:** replace with one entry: state after migration, next task (from PLAN.md open boxes), open blockers (T4.6 WIMAS manual, T5.x design), and a note that the caveman compression issue no longer applies.
3. **CLAUDE.md — Environment section:** make it machine-neutral: Python 3.12 via uv, Node LTS, Windows, project path; remove hardware specifics or list both laptops; keep every hard rule unchanged. Add one line: "These rules apply to every AI coding environment used on this project."
4. **AGENTS.md (new, short pointer, not a second rule set):** "Read CLAUDE.md, then PLAN.md (open tasks, acceptance tests), then the Autopilot handoff at the end of DECISIONS.md. Those files are the source of truth. Follow AUTOPILOT_PROMPT.md §4–§7 for how to work, commit and hand off." Antigravity, Cursor, Codex and Claude Code all read `AGENTS.md` at the project root, so every environment gets the same rules from the same files. Keep it well under 12,000 characters (Antigravity's per-file rule limit).
5. **AUTOPILOT_PROMPT.md — header note:** the loop (`scripts/autopilot.ps1`) is Claude-Code-specific and paused; its working rules (one task at a time, handoff, commit after each task, decision policy and review queue, BLOCKED.md for hard stops) apply to any environment.
6. **PLAN.md — new milestone "M1 Migration":** the §10 checks as acceptance tests, ticked when they pass. No feature entry for Antigravity (it is the coding environment, §8).

---

## 8. Continuing in Google Antigravity

**Decision (user, 8 Nov):** "Anti-Gravity" means **Google Antigravity**, the AI coding IDE used on the new laptop. It is **not** a FieldWitness feature, so no feature task is added to PLAN.md. Development continues with the existing open tasks.

### 8.1 Setup on the new laptop

1. Install Google Antigravity from its official site and sign in with your Google account.
2. Open the folder `D:\NASA Project` as the workspace.
3. Make sure `AGENTS.md` exists at the project root (§7 item 4). Antigravity loads it automatically as a workspace rule, so every agent task starts from the project's real rules. Do not create a `GEMINI.md`; it would take precedence over `AGENTS.md` and become a second rule set.
4. Agent permissions: allow it to edit files and run the project's commands (`uv run ...`, `npm test`, `npm run build`, `git status/add/commit`). Keep **review required** for `git push`, package installs (`uv add`, `npm install`), file deletion, and any browser or deploy action. This mirrors the deny rules of `.claude/settings.json`, which Antigravity does not read.
5. Use **planning mode** for each task, so you approve its plan before it changes code.
6. Send the master prompt from §9 as the first message.

### 8.2 How work continues

- Same loop as before, now with you approving each plan: next task from the handoff → plan (≤10 lines) → implement → acceptance test + full test suite → tick PLAN.md → one line in DECISIONS.md → commit → push when green.
- The Claude Code autopilot (`scripts/autopilot.ps1`) is paused. Keep the script in the repo; it still works if Claude Code is ever used again.
- Priority order up to the 13 Nov freeze: Phase 5 (T5.x design, T5.2 double ML, T5.3 diagnostics) → deployment of the ~40-field demo (you approve each step) → Phase 10 (LICENSE, README/AI_USE final, red team, rules check on 13 Nov) → extras (Toulouse, Ukraine, Nile confidence map) only if time remains.
- The demo video or 7 slides and the submission page are yours; the agent can draft texts in `docs/drafts/`.

### 8.3 Risks specific to the switch

| Risk | Mitigation |
|---|---|
| A new agent "improves" working code or re-decides settled questions | The master prompt forbids it; DECISIONS.md is binding; review each plan |
| Rules drift between environments | One rule source (CLAUDE.md), one pointer (AGENTS.md); no GEMINI.md |
| Agent claims results without running them | Require the test output in every task report |
| Usage or quota limits in the new tool | Tasks stay small; handoff is updated after every task, so work resumes cleanly |

---

## 9. Master handoff prompt for the new AI coding assistant

Paste this as the first message in the new environment, opened at the project root.

```
You are continuing an existing engineering project, not starting a new one. Inspect files before assuming anything.

PROJECT
FieldWitness — NASA Space Apps 2026 entry for the challenge "Field Shift: Adapting Farms with NASA Data" (full text: docs/official_challenge.md). A crop-rotation decision-support web app. For a field it reconstructs the field's history from NASA HLS 30 m satellite data, simulates rotation options with a FAO-56 water-balance model calibrated to that history, compares them with natural experiments in neighbouring fields, grades the evidence A–D, explains each option (why, evidence, benefits, gaps, risks), and scores its own predictions against later seasons (hindcast vs baselines). Hackathon 14–15 Nov 2026; official rules released 13 Nov (feature freeze that day).

SOURCE OF TRUTH (read in this order before doing anything)
1. CLAUDE.md — hard rules and working agreement. They apply to you, whatever your environment.
2. PLAN.md — phases, task IDs, acceptance tests, gates, schemas (§3, §3b), schedule.
3. DECISIONS.md — decision log, and the "## Autopilot handoff" section at the end: current state and next task.
4. AUTOPILOT_PROMPT.md §4–§7 — how to work, commit and hand off (the Claude Code loop itself is paused).
5. DATA.md, docs/api_notes.md, docs/gates/, docs/review_queue.md (if present), results/.
Do not create new planning or decision files; update these.

REPOSITORY
One Git repository at the project root, remote origin = github.com/amr-mousa-eg/fieldwitness (private). Branch main is active; branch app is merged and kept for history. Python pipeline in src/fieldwitness (uv, Python 3.12, uv.lock); web app in app/ (React + Vite + TypeScript + MapLibre + Recharts, package-lock.json). Gitignored local data: data/, packs/ (generated field packs), docs/refs/ (FAO-56 equation images), logs/.

STATE (verify against PLAN.md ticks and the handoff)
Done: Phases 0–4 (T2.2 negative result recorded; T2.3 deferred; T4.6 waits for a manual WIMAS download), Phase 6, Phase 7 (hindcast skill weak, reported as is), Phase 8 (200 Kansas packs, validator clean), Phase 9 views on real data.
Open: Phase 5 neighbour evidence (T5.x design, double ML with doubleml 0.11.4, diagnostics), deployment (Netlify, ~40-field demo set; ask the user before any deploy or account action), Tier 2/3 regions (extras), Phase 10 (LICENSE, README/AI_USE final, red team, rules check on 13 Nov, demo, submission).

RULES THAT MATTER MOST (full list in CLAUDE.md)
- Never fabricate data, endpoints, parameters, coefficients, results or citations. Verify every external API from its official docs first.
- Every user-facing number carries a source tag O/D/E/A. No yield in tonnes, no soil fertility from space, no price forecasts, no LLM making decisions.
- No leakage: data access goes through the as_of guard; validation splits are spatially blocked.
- Negative results are recorded, never hidden; never weaken a test to make it pass.
- Tests that read data/ use the needs_data marker so CI stays green.
- Ask before: schema changes, new dependencies not named in PLAN.md, downloads over 1 GB, accepting any terms, anything with credentials, making the repo public, deploying, merging branches, force-pushing.
- Never read or print credentials (%USERPROFILE%\_netrc is used programmatically for NASA Earthdata only, in memory).

HOW TO WORK
One task at a time from PLAN.md, in the handoff's order. For each task: plan in ≤10 lines → implement → run its acceptance test and the full test suite (uv run pytest -q; uv run ruff check .; in app/: npm test, npm run build) → tick the box in PLAN.md with a one-line note → one line in DECISIONS.md → commit with a clear message → push only when tests pass and gitleaks is clean. Split any task too big for one session into subtasks listed in the handoff. Reversible decisions within scope: take the recommended option, log it in DECISIONS.md and docs/review_queue.md, continue. Update the handoff (one entry, replacing the previous one) at the end of every session.

DO NOT
Rewrite working code without a task that requires it. Silently change approved decisions (see DECISIONS.md). Claim anything works without running it (show the test output in every report). Create a GEMINI.md or any other rule file: AGENTS.md points to CLAUDE.md, which is the single rule source. Push, install packages, delete files, or deploy without my approval.

FIRST STEPS
1. Read the five sources above and summarise the current state in ≤15 lines, including the next task and any open blocker.
2. Run the verification commands (uv run pytest -q, uv run ruff check ., and in app/: npm test, npm run build) and report the results.
3. Wait for my OK before starting the next task.
```

---

## 10. Post-migration verification checklist (new laptop)

| # | Directory | Command | Success looks like |
|---|---|---|---|
| V1 | `D:\NASA Project` | `git status --short --branch` | `## main...origin/main`, no other lines |
| V2 | `D:\NASA Project` | `git log -1 --format="%H"` | same hash as the old laptop at A4 |
| V3 | `D:\NASA Project` | `git rev-list --count HEAD` | same number as on the old laptop |
| V4 | `D:\NASA Project` | `git branch -a` | `main`, `origin/main`, `origin/app` |
| V5 | `D:\NASA Project` | `git push --dry-run` | `Everything up-to-date` (auth works, nothing pushed) |
| V6 | `D:\NASA Project` | `Compare-Object` of the manifests (§3 B7) | no output |
| V7 | `D:\NASA Project` | `uv run python --version` | `Python 3.12.x` |
| V8 | `D:\NASA Project` | `uv run pytest -q` | same passed/skipped counts as the old laptop with data present (last report: 241 passed); no failures |
| V9 | `D:\NASA Project` | `uv run ruff check . ; uv run ruff format --check .` | `All checks passed!`, no files to reformat |
| V10 | `D:\NASA Project` | `uv run pre-commit run --all-files` | every hook `Passed` (ruff, gitleaks) |
| V11 | `D:\NASA Project\app` | `npm test` | all app tests pass (last report: 45) |
| V12 | `D:\NASA Project\app` | `npm run build` | build succeeds (size warning about the 1.77 MB bundle is known) |
| V13 | `D:\NASA Project` | pack validator, as documented in README or the handoff (`cli validate-packs`) | 0 problems |
| V14 | `D:\NASA Project\app` | `npm run dev`, open the printed localhost URL | map shows 200 Kansas fields, no "DEMO DATA" banner, Field Card, Calendar, Advisor Console and Scoreboard load, browser console has no errors |
| V15 | `D:\NASA Project` | `uv run python scripts/check_earthdata.py` | `authenticated: True` and a granule list |
| V16 | GitHub | Actions tab | latest run green (no new run is triggered by verification alone) |
| V17 | `D:\NASA Project` | apply §7 documentation updates as one commit, then push | CI green on that commit |

When V1–V16 pass, migration is complete. Record the results in the DECISIONS.md migration entry (§7 item 1) and tick milestone M1 in PLAN.md.

---

## Minimum information to collect from the old Claude Code sessions

None is strictly required: the repository documents are the source of truth, and §0 captures the rest. Do **not** reopen the old sessions just for this (each would reload ~370k tokens). If the §0 inspection shows uncommitted work, the loop window and `logs/autopilot/` explain which run produced it.
