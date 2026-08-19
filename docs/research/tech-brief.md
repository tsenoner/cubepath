# Cubepath PWA — Integration Brief

Synthesis of 7 research tracks (cubing.js, Astro+PWA, storage/FSRS, Vercel, competitors, install UX, curriculum sources). All claims carry inline sources; disagreements and unverified claims are flagged **UNVERIFIED**.

---

## 1) Pinned versions

| Package | Version | Pin style | Why |
|---|---|---|---|
| `astro` | `7.2.3` | `^7.2.3` | Latest; Node >=22.12.0; ships Vite ^8.0.13 (Rolldown) ([npm](https://www.npmjs.com/package/astro), [astro.build/blog/astro-7](https://astro.build/blog/astro-7/)) |
| `@astrojs/mdx` | `7.0.6` | `^7.0.6` | Peer `astro ^7.0.0` ([npm](https://www.npmjs.com/package/@astrojs/mdx)) |
| `@astrojs/check` | `0.9.10` | `^0.9.10` | `astro check` in CI ([docs](https://docs.astro.build/en/reference/cli-reference/)) |
| `typescript` | `^5.9.0` | caret | Peer of @astrojs/check |
| `cubing` | `0.63.3` | **exact** | Pre-1.0; all key attrs are `experimental-*` and may change in 0.x minors ([npm](https://www.npmjs.com/package/cubing), [js.cubing.net](https://js.cubing.net/cubing/)) |
| `@vite-pwa/astro` | `1.2.0` | **exact** | Requires npm `overrides` workaround for Astro 7 (see §3) ([issue #72](https://github.com/vite-pwa/astro/issues/72)) |
| `vite-plugin-pwa` | `1.3.0` | `^1.3.0` | Peer `vite ^3–^8` — Vite 8/Rolldown ready ([npm](https://www.npmjs.com/package/vite-plugin-pwa)) |
| `ts-fsrs` | `5.4.1` | `^5.4.1` | v6 beta exists (`6.0.0-beta.7`) — do **not** take v6 yet ([npm](https://www.npmjs.com/package/ts-fsrs), [repo](https://github.com/open-spaced-repetition/ts-fsrs)) |
| `idb` | `8.0.3` | `^8.0.3` | Stable/mature ([npm](https://www.npmjs.com/package/idb)) |
| `@playwright/test` | `1.62.1` | `^1.62.1` | E2E offline tests |
| `vitest` | `4.1.11` | `^4.1.11` | cubing.js kpuzzle suite verified green on this version (local execution) |

**No `@astrojs/vercel` adapter** — pure static output deploys with zero config ([Astro deploy guide](https://docs.astro.build/en/guides/deploy/vercel/)).

**Node: use 22.12+ everywhere** (Astro requires >=22.12.0, cubing requires >=22.3.0). Set `"engines": { "node": ">=22.12.0" }` and pin Node 22 in Vercel project settings/CI.

---

## 2) cubing.js integration guide

### Imports (ESM-only, subpath-only)
No root `"cubing"` import, no CJS. Valid entries: `cubing/alg`, `cubing/twisty`, `cubing/kpuzzle`, `cubing/puzzles`, `cubing/scramble`, `cubing/search`, `cubing/notation` (package.json exports of `cubing@0.63.3`; [js.cubing.net](https://js.cubing.net/cubing/)). License: `MPL-2.0 OR GPL-3.0-or-later` — choose MPL-2.0; keep notices, no app-code obligations ([npm](https://www.npmjs.com/package/cubing)).

### Case display pattern (the core Cubepath pattern)
Set `experimental-setup-anchor="end"` + put the **solving** alg in `alg`: the player starts at the scrambled case (start state = setup ∘ inverse(alg)) and plays forward to solved (verified from shipped `AnchorTransformationProp` code; [twisty docs](https://js.cubing.net/cubing/twisty/)):

```html
<script>import "cubing/twisty"; // registers <twisty-player>; Node-import-safe (verified)</script>

<twisty-player
  puzzle="3x3x3"
  alg="R U R' U' R' F R2 U' R' U' R U R' F'"
  experimental-setup-anchor="end"
  experimental-stickering="PLL"
  hint-facelets="none" background="none"
  control-panel="bottom-row" tempo-scale="2"
></twisty-player>
```

- **Stickering masks** (all verified from [puzzle-stickerings.ts](https://github.com/cubing/cubing.js/blob/main/src/cubing/puzzles/stickerings/puzzle-stickerings.ts)): `OLL`, `PLL`, `LL`, `F2L`, `Cross`, `Daisy`, `EPLL`, `ELL`, `COLL`, `OCLL`, `ZBLL`, `2x2x2`, `2x2x3`, big-cube `L2C` (4x4/5x5/6x6) and `opposite-centers` (4x4). 4x4/5x5 also accept all 3x3 masks (executed: `puzzles["4x4x4"].stickerings()`).
- **Big cubes**: `puzzle="4x4x4"`/`"5x5x5"` fully supported incl. SiGN wide moves (`Rw`, `Uw2`, `3Rw`). They render via the heavier PG3D path — mitigate with `hint-facelets="none"`, `background="none"`, one visible player at a time (player lazy-inits via IntersectionObserver). Perf implication is **UNVERIFIED** (inferred, not benchmarked).
- **In Astro/MDX**: `client:*` directives are framework-components-only ([directives ref](https://docs.astro.build/en/reference/directives-reference/)). Wrap in a `TwistyPlayer.astro` component with a processed `<script>import "cubing/twisty"</script>` (bundled, deduped) and import that into MDX — do not put `<script>` tags directly in `.mdx` (undocumented; historical bugs withastro/astro#5991/#6035/#8034 — **UNVERIFIED** whether still broken).
- Useful methods: `play()`, `pause()`, `jumpToStart({flash})`, `jumpToEnd({flash})`, `experimentalScreenshot({width,height})` → PNG data URL.

### Scramble worker
```ts
import { randomScrambleForEvent } from "cubing/scramble";
import { setSearchDebug } from "cubing/search";
setSearchDebug({ showWorkerInstantiationWarnings: false });

const s = await randomScrambleForEvent("333"); // random-state, ~80ms (measured)
// "444": random-state, ~1s first call; "555": random-MOVES via wasm, ~30ms
```
- 333/222/444 = random-state; **555/666/777 = random-moves** (shipped `wcaEvents` data) — don't advertise WCA-regulation 5x5 scrambles.
- **Fully offline once bundled**: zero CDN requests; twsearch WASM is base64-inlined in a JS chunk (`twips_wasm_bg-*.js`, 215 KB gz), all lazily loaded same-origin. The precache manifest **must glob all `dist/**/*.js`** (worker entry, wasm chunk, per-event solver chunks, `twisty-dynamic-3d-*.js`) or offline breaks on first use (verified from Vite 8 build output inspection).
- Bundle budget (measured, esbuild --minify): player first 3D render ≈ **190 KB gz** (28 entry + 136 lazy three.js + shared); scramble adds 23 KB gz (333) + lazy 215 KB gz wasm chunk (444/555).

### Known-good Vite config (belt-and-suspenders; default config also built clean on Vite 8.2.1 — verified)
```js
vite: {
  optimizeDeps: { exclude: ["cubing"] }, // kills dev-mode search-worker-entry errors (cubing.js #327)
  worker: { format: "es" },              // module workers (compat issue #323 recommendation)
}
```
Canonical compat doc: [cubing.js#323](https://github.com/cubing/cubing.js/issues/323) (Vite ≥5.1.6 OK); background: [#309](https://github.com/cubing/cubing.js/issues/309), [#327](https://github.com/cubing/cubing.js/issues/327), [vite#14499](https://github.com/vitejs/vite/issues/14499).
**UNVERIFIED**: in-browser scramble generation after an Astro **production** build was not exercised in a real browser (build output + dev server verified only) — smoke-test on the first deployed preview (M0 gate).

### Vitest kpuzzle verification pattern (this exact suite ran green — Vitest 4.1.11/Node 26)
```ts
import { expect, test } from "vitest";
import { Alg } from "cubing/alg";
import { cube3x3x3, puzzles } from "cubing/puzzles";

const kpuzzlePromise = cube3x3x3.kpuzzle();

async function solves(setup: string, solution: string) {
  const kpuzzle = await kpuzzlePromise;
  return kpuzzle.defaultPattern().applyAlg(setup).applyAlg(solution)
    .experimentalIsSolved({ ignorePuzzleOrientation: true, ignoreCenterOrientation: true }); // BOTH required
}

test("T-perm solves its case", async () => {
  const t = "R U R' U' R' F R2 U' R' U' R U R' F'";
  expect(await solves(new Alg(t).invert().toString(), t)).toBe(true);
});
// Alternative: kpuzzle.algToTransformation(setup).applyAlg(solution).isIdentityTransformation()
// 4x4: (await puzzles["4x4x4"].kpuzzle()).defaultPattern()... — verified with Rw U Rw'.
```
Gotcha (verified): `new Alg("R Q")` **parses fine** (SiGN parsing is puzzle-agnostic); unknown moves throw only at `algToTransformation` ("Invalid move for KPuzzle"); true syntax errors (`"R ++"`) throw at parse. Write validation tests at the kpuzzle level.

---

## 3) Astro + PWA config

### The blocker and its fix
`@vite-pwa/astro@1.2.0` peer-depends on `astro ^1.6–^5` — install fails under Astro 7 ([#72](https://github.com/vite-pwa/astro/issues/72), [#74](https://github.com/vite-pwa/astro/issues/74) open; PR #73 closed unmerged). **UNVERIFIED (community-tested with Astro 7.0.4, not first-party)** — npm `overrides` workaround:

```json
{
  "overrides": {
    "@vite-pwa/astro": {
      "astro": "^1.6.0 || ^2.0.0 || ^3.0.0 || ^4.0.0 || ^5.0.0 || ^6.0.0 || ^7.0.0"
    }
  }
}
```

### astro.config.mjs (complete)
Note: researchers split on `registerType` (`'prompt'` vs `'autoUpdate'`) and on `maximumFileSizeToCacheInBytes` (6 vs 8 MiB). Decision: **`'prompt'`** (matches the official [pwa-prompt example](https://github.com/vite-pwa/astro/tree/main/examples/pwa-prompt) and gives user-controlled updates) and **8 MiB** (safely covers the 704 KB raw wasm-in-JS chunk; workbox default 2 MiB silently drops big files, and vite-plugin-pwa ≥0.20.2 fails the build — [vite-pwa docs](https://vite-pwa-org.netlify.app/guide/service-worker-precache)).

```js
// app/astro.config.mjs
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import AstroPWA from '@vite-pwa/astro';

export default defineConfig({
  site: 'https://cubepath.example.com',
  output: 'static', // no Vercel adapter needed
  integrations: [
    mdx(),
    AstroPWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg'],
      manifest: {
        id: '/',                          // explicit id decouples it from start_url (https://developer.chrome.com/docs/capabilities/pwa-manifest-id)
        name: 'Cubepath', short_name: 'Cubepath',
        description: "Learn to solve the Rubik's Cube: zero to CFOP, plus 4x4 and 5x5.",
        start_url: '/', scope: '/', display: 'standalone',
        theme_color: '#111114', background_color: '#111114',
        icons: [ // SEPARATE any/maskable entries — no "any maskable" combos (https://web.dev/articles/maskable-icon)
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // precache EVERYTHING (lazy cubing.js worker/wasm chunks are hashed .js under dist/_astro/)
        globPatterns: ['**/*.{css,js,html,svg,png,ico,txt,json,webmanifest,woff2,wasm}'],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
      },
      experimental: { directoryAndTrailingSlashHandler: true }, // /page/ -> page/index.html offline (https://vite-pwa-org.netlify.app/frameworks/astro)
      devOptions: { enabled: true, suppressWarnings: true },
    }),
  ],
  vite: {
    optimizeDeps: { exclude: ['cubing'] },
    worker: { format: 'es' },
  },
});
```

### Service-worker strategy
- **Precache-everything** (generateSW). Vercel deploys are atomic — old hashed `/_astro/*` URLs 404 after a deploy, so lazy runtime-caching alone would strand offline users mid-upgrade. Full precache at install time is mandatory.
- Update flow: `virtual:pwa-register` → `registerSW({ immediate: true, onNeedRefresh, onOfflineReady })`; call the returned `refreshSW(true)` from the update toast's Reload button ([pwa-prompt example](https://github.com/vite-pwa/astro/tree/main/examples/pwa-prompt)).
- Types in `src/env.d.ts`: `/// <reference types="vite-plugin-pwa/info" />` + `/// <reference types="vite-plugin-pwa/vanillajs" />` (`vite-plugin-pwa` as devDependency).
- SW scripts can't use dynamic `import()` (spec-disallowed — [ServiceWorker spec](https://w3c.github.io/ServiceWorker/), **UNVERIFIED** citation depth); generateSW handles this for you.

### Toasts
Two states, one component rendered in the base layout: **offline-ready** ("App ready to work offline", dismiss-only) and **update available** ("New content available — reload", Reload + Close buttons wired to `refreshSW(true)`). Pattern verbatim from the official example above.

### Astro 7 gotchas
- Content Layer API mandatory: `src/content.config.ts`, `glob()` loader from `astro/loaders`, Zod 4 via `astro/zod`, `render(entry)` from `astro:content` ([upgrade-to/v6](https://docs.astro.build/en/guides/upgrade-to/v6/)).
- Rust compiler: unclosed HTML tags = build errors; Sätteri replaces remark/rehype by default (opt back via `markdown: { processor: unified() }` from `@astrojs/markdown-remark` if the guide needs remark plugins) ([upgrade-to/v7](https://docs.astro.build/en/guides/upgrade-to/v7/)).
- `src/fetch.ts` is reserved — don't use that path.
- tsconfig: `{ "extends": "astro/tsconfigs/strict", "include": [".astro/types.d.ts", "**/*"], "exclude": ["dist"] }`; CI: `astro check && astro build` ([TS guide](https://docs.astro.build/en/guides/typescript/)).
- Playwright offline E2E: test against `astro build && astro preview` (port 4321), wait for `navigator.serviceWorker.controller`, then `context.setOffline(true)` + reload + assert content + zero `requestfailed`. **Caveat**: `setOffline` doesn't block SW-originated fetches ([playwright#2311](https://github.com/microsoft/playwright/issues/2311) closed unfixed) — for a strict test use `PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS=1` + `context.route` aborting `route.request().serviceWorker()` requests. Never set `serviceWorkers: 'block'`.

---

## 4) Vercel deploy config

- **No adapter.** Framework preset auto-detects `astro build` → `dist` ([Astro deploy guide](https://docs.astro.build/en/guides/deploy/vercel/)). Bonus: the preset's `defaultRoutes` already long-cache `/_astro/(.*)` as immutable ([frameworks.ts](https://raw.githubusercontent.com/vercel/vercel/main/packages/frameworks/src/frameworks.ts)).
- **Root Directory = `app` is dashboard-only** (Settings → Build and Deployment → Root Directory) — there is **no** `rootDirectory` key in vercel.json, and **vercel.json must live at `app/vercel.json`** ([configure-a-build](https://vercel.com/docs/builds/configure-a-build#root-directory), [monorepo FAQ](https://vercel.com/docs/monorepos/monorepo-faq)).
- **Production branch**: default order main → **master** → repo default, so this repo's `master` is picked automatically; pin under Settings → Environments → Production ([git docs](https://vercel.com/docs/git#production-branch)).
- **Deployment Protection is ON by default** for new projects ([changelog](https://vercel.com/changelog/deployment-protection-is-now-enabled-by-default-for-new-projects)). Production is never blocked on Hobby, but preview URLs redirect to SSO — which breaks SW registration and mobile install testing on previews (**UNVERIFIED** direct consequence, mechanism documented at [Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication)). **Disable it** (Settings → Deployment Protection, or API `PATCH { "ssoProtection": null }`); verify with `curl -sI <preview>/sw.js` → expect 200, not 30x.
- Hobby limits fit (100 GB transfer, 1M edge requests, 100 deploys/day, 45-min builds; non-commercial only; overage pauses, no billing) ([hobby](https://vercel.com/docs/plans/hobby), [limits](https://vercel.com/docs/limits)). Repo must stay on the personal GitHub account (org repos need Pro).

### app/vercel.json
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "astro",
  "buildCommand": "astro build",
  "outputDirectory": "dist",
  "headers": [
    { "source": "/sw.js",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=0, must-revalidate" }] },
    { "source": "/manifest.webmanifest",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=0, must-revalidate" },
                  { "key": "Content-Type", "value": "application/manifest+json" }] },
    { "source": "/_astro/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] },
    { "source": "/icons/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=86400, stale-while-revalidate=604800" }] }
  ]
}
```
The `/sw.js` never-cache rule is Vercel's own documented pattern ([vercel.json ref](https://vercel.com/docs/project-configuration/vercel-json), [cache headers](https://vercel.com/docs/caching/cache-control-headers)). `headers.source` is case-sensitive and must match the **actual emitted SW filename** (vite-plugin-pwa default: `sw.js`).

Post-deploy checks: `curl -sI .../sw.js` (200 + revalidate), `curl -sI .../_astro/<hash>.js` (immutable), preview URL not SSO-redirected.

---

## 5) Storage + FSRS module design

### ts-fsrs 5.4.1 (API verified by execution + published .d.ts)
- `Rating {Manual=0, Again=1, Hard=2, Good=3, Easy=4}`; `Grade = Exclude<Rating, Manual>`; `State {New, Learning, Review, Relearning}`.
- `createEmptyCard()` → new card; `f.repeat(card, now)` → all-4-grades preview (for interval labels on answer buttons); `f.next(card, now, grade)` → `{ card, log }`.
- `next()/repeat()` accept `CardInput` with ISO-string dates — JSON-imported backups feed straight back in without revival.
- Gotchas: `Card.elapsed_days` is deprecated (removed in v6) — never build on it; `f.get_retrievability(card, now)` returns a **string** ("100.00%") unless you pass `false` as 3rd arg.

### idb 8.0.3 schema (Cubepath)
```ts
interface CubepathDB extends DBSchema {
  progress: { key: string; value: { caseId: string; status: 'unseen'|'learning'|'learned'; updatedAt: number } };
  cards:    { key: string; value: Card & { caseId: string }; indexes: { 'by-due': Date } };
  reviews:  { key: number; value: { caseId: string; rating: number; review: Date } };
  settings: { key: string; value: unknown }; // out-of-line keys
}
```
- `openDB('cubepath', v, { upgrade(db, oldVersion, _, tx) { if (oldVersion < N) ... } })` — migration ladders; data transforms **must** use the provided versionchange `tx` (can't open your own); handle `blocking()` (reload) for multi-tab upgrades ([idb README](https://github.com/jakearchibald/idb)).
- Write card + review log + progress in **one** readwrite transaction (atomicity). `Date` objects store natively via structured clone. Due queue: `getAllFromIndex('cards', 'by-due', IDBKeyRange.upperBound(now))`.
- Persist **raw FSRS Card objects**, not derived fields — makes the v6 migration a data no-op.

### Persistence + backup
- `navigator.storage.persist()`: call at the **first meaningful save inside a user gesture** (first graded review), after checking `persisted()`; retry on `appinstalled`. Chrome grants silently by heuristics (PWA install helps); Firefox prompts; Safari grants silently by heuristics incl. Home-Screen install ([web.dev](https://web.dev/articles/persistent-storage), [WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/)).
- JSON export/import (no server): per-store `getAll()` → versioned envelope (`{ app, schemaVersion, exportedAt, data }`) → Blob → `<a download>`; import via `<input type=file>` → validate envelope → clear+write in one transaction ([reference impl](https://github.com/Polarisation/indexeddb-export-import), [dexie pattern](https://dexie.org/docs/ExportImport/dexie-export-import)). Two traps: the `settings` store's out-of-line keys need `getAllKeys()+getAll()` pairing, and the `cards` import must **revive `due`/`last_review` to real Dates** for the `by-due` index (ts-fsrs itself tolerates strings, which masks the bug).

---

## 6) Install UX per platform

| Platform | Mechanism | UX |
|---|---|---|
| **iOS 26 / Safari 26** | Zero installability requirements; every Add-to-Home-Screen opens as a web app by default ("Open as Web App" toggle, on) ([WebKit Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)) | No `beforeinstallprompt` ever ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event)). Detect `matchMedia('(display-mode: standalone)')` + iOS UA; show one-time dismissible hint: "Tap Share → Add to Home Screen." Ship a 180×180 `<link rel="apple-touch-icon">` identical to the manifest icon art — **UNVERIFIED for iOS 26**: apple-touch-icon overriding manifest icons was last verified iOS 15.4–17 ([firt.dev](https://firt.dev/notes/pwa-ios/)) |
| **Android/desktop Chromium** | `beforeinstallprompt` when: HTTPS, not installed, engagement (1 click + 30s ever), manifest with name, 192+512 icons, start_url, standalone-class display. **SW no longer required** (removed Chrome 108/112) ([web.dev criteria](https://web.dev/articles/install-criteria), [Chrome blog](https://developer.chrome.com/blog/update-install-criteria)) | `preventDefault()`, stash event, show Install button *whenever the deferred event exists* (heuristic fires late), `prompt()` → `userChoice`; hide on `appinstalled`. Desktop Chrome ~124+ also has menu "Install page as app" fallback (**UNVERIFIED**) |
| **Firefox** | No `beforeinstallprompt` | No install UI; app still works as a site |

**Storage stakes**: non-installed Safari-tab users are subject to ITP's 7-day script-writable-storage eviction; **Home-Screen web apps have their own days-of-use counter and are effectively exempt** ([WebKit ITP](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/)). Installed iOS apps get browser-level quota (~60% of disk) ([WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/)). So the install nudge doubles as the data-safety nudge; JSON export is the belt-and-braces.

---

## 7) Competitor-informed product decisions

Competitors: CuberPal (iOS, $4.99/wk–$39.99/yr, 25 subs / $112 MRR — [trustmrr](https://trustmrr.com/startup/cuberpal), [cuberpal.com](https://www.cuberpal.com/)), JPerm trainer ([jperm.net/algs/pll](https://www.jperm.net/algs/pll)), SpeedCubeDB ([speedcubedb.com/a/3x3/PLL](https://speedcubedb.com/a/3x3/PLL)).

| Decision | What | Source |
|---|---|---|
| **Emulate** | JPerm's 3-state case lifecycle (Unlearned → Learning → Finished) + Trash, cycled by tapping the case tile; auto-sort Learning up | [jperm.net/algs/pll](https://www.jperm.net/algs/pll) |
| **Emulate** | JPerm selection modes: All / Group / Status / **Slowest**; probability **Balanced vs Realistic** (real case frequencies) | same |
| **Emulate** | JPerm hint flow: timer front-and-center, alg hidden, one tap/keystroke reveal, triggers chunked in brackets; keyboard-first (Space, ←/→) | same |
| **Emulate** | SpeedCubeDB alg-row anatomy: primary alg + ETM/STM badges + generator tag, alternates collapsed behind "More"; **setup-moves line** per case (doubles as physical-cube scramble); "n/total" subset chips as filter+progress | [speedcubedb.com/a/3x3/PLL](https://speedcubedb.com/a/3x3/PLL) |
| **Improve** | Persistence: IndexedDB + JSON export/import beats JPerm's cookies (wiped on clear) and SpeedCubeDB's Google-login gate — no accounts | [jperm.net/algs/oll](https://www.jperm.net/algs/oll) help text |
| **Improve** | **Free transparent FSRS** over case statuses with due-today queue — CuberPal paywalls SRS; JPerm has none. Biggest available differentiator | [cuberpal.com](https://www.cuberpal.com/) |
| **Improve** | Interactive 3D (twisty-player scrub/step) on every alg — CuberPal paywalls 3D; JPerm/SCDB use static images + YouTube | — |
| **Improve** | Recognition quizzes (show case → pick name/alg before timing), free — only CuberPal has this, paywalled | [cuberpal.com](https://www.cuberpal.com/) |
| **Improve** | Lesson → pre-filtered trainer deep links — none of the three connect curriculum to trainer sets | — |
| **Improve** | 4x4/5x5 curriculum — CuberPal teaches only 3x3 (**UNVERIFIED**: inferred from changelog/roadmap); uncontested space | [cuberpal.com/roadmap](https://www.cuberpal.com/roadmap) |
| **Skip** | AI video analysis / coach chat (server-bound, expensive, reportedly fragile per App Store reviews); camera solver; accounts/leaderboards/XP/daily challenges; community alg voting (needs backend+mass — ship curated primary + 2–3 vetted alternates statically); any paywall | [App Store](https://apps.apple.com/us/app/cuberpal-cube-timer-coach/id6758110729) |

Positioning: everything CuberPal charges for, minus the AI, free, offline, on every platform. Caution: borrow JPerm's interaction model, not its skin/labels. **UNVERIFIED**: CuberPal launch date (2025 vs 2026 source conflict); JPerm scramble = inverse-alg + random AUF (inference); SpeedCubeDB's trainer UX (its /practice 404s to direct fetch — unevaluated).

---

## 8) Curriculum data extraction plan

**Pipeline**: one-time `scripts/extract-algs.ts` — fetch JPerm `/lib/*.js` files, parse `algsetAlgs` arrays (`{name, alg[], group, prob}`; **`alg[0]` = recommended**), expand the 4x4 `[*]` parity placeholder, validate every string through `new Alg(s).toString()` (verified: all 213 JPerm 3x3 algs parse in cubing@0.63.3 incl. `2R2`, `3Rw`, `Uw2`, M/S/E, rotations, parens; only `[*]` fails), verify each alg solves its case via the kpuzzle pattern (§2), emit typed JSON into `src/data/`. **Commit the JSON — never fetch at build/runtime** (offline-first; undocumented format).

| Field | Primary source | Method | Cross-check |
|---|---|---|---|
| OLL 57 (alg, alternates, 15 shape groups, prob) | [jperm.net/lib/oll.js](https://jperm.net/lib/oll.js) | automated parse | [CubeSkills OLL PDF](https://www.cubeskills.com/uploads/pdf/tutorials/oll-algorithms.pdf), [SCDB](https://speedcubedb.com/a/3x3/OLL) |
| PLL 21 | [jperm.net/lib/pll.js](https://jperm.net/lib/pll.js) | automated parse | [CubeSkills PLL PDF](https://www.cubeskills.com/uploads/pdf/tutorials/pll-algorithms.pdf), [SCDB](https://speedcubedb.com/a/3x3/PLL) |
| 2-look OLL/PLL | jperm.net/lib 2look files | automated parse | — |
| F2L 41 | JPerm Best F2L PDF (Drive id `1nzAXYUWZJ6H2wIOXaHdWXep3W57tArbR` via bit.ly/bestf2l; jperm.net/algs/f2l is a **404**) | **semi-manual**: pdftotext clean but needs human mapping to [SCDB F2L 1–41 numbering](https://speedcubedb.com/a/3x3/F2L) | [CubeSkills F2L PDF](https://www.cubeskills.com/uploads/pdf/tutorials/f2l.pdf) |
| PLL 2-sided recognition | [Sarah Strong's guide](https://sarah.cubing.net/3x3x3/pll-recognition-guide) | encode the **system** as data (headlights → swap type, blocks/checkers); original prose | speedsolving wiki (names only) |
| Probabilities | JPerm `prob` (OLL /216: 51×1/54, 5×1/108, OLL 20 = 1/216; PLL /72: most 1/18, Z/E 1/36, H/Na/Nb 1/72) | computed in parse | CubeSkills PDFs agree exactly (grep-verified) |
| 4x4 parity | jperm.net/4x4 verbatim: OLL parity `Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'`; PLL parity `2R2 U2 2R2 Uw2 2R2 Uw2` | hardcode | [SCDB OLLParity](https://speedcubedb.com/a/4x4/OLLParity) |
| 4x4 OLL/PLL-with-parity sets (27 + 22) | [jperm.net/lib/4x4oll.js](https://jperm.net/lib/4x4oll.js), [4x4pll.js](https://jperm.net/lib/4x4pll.js) | parse + expand `[*]` | — |
| Yau structure | [jperm.net/4x4](https://jperm.net/4x4) + [wiki Yau_method](https://www.speedsolving.com/wiki/index.php/Yau_method) | original prose | — |
| 5x5 L2E — **13 cases, not 12** | [speedcubedb.com/a/5x5/L2E](https://speedcubedb.com/a/5x5/L2E) | manual transcription (no API) | jperm.net/5x5 |
| 5x5 edge parity | jperm.net/5x5 verbatim: `Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'` — **`3Rw'` differs from the 4x4 form**; keep as separate entries | hardcode | — |

**Copyright hygiene** (verified against [copyright.gov FAQ](https://www.copyright.gov/help/faq/faq-protect.html)): alg strings, names, groups, probabilities = unprotectable facts — extract freely. All prose and diagrams = original (self-generate via twisty-player/the repo's Python SVG pipeline; never copy VisualCube renders). Re-group into Cubepath's own order (avoids thin compilation copyright). Speedsolving wiki declares **no license** — terminology checks only. Credit JPerm/CubeSkills/SpeedCubeDB as good citizenship.

---

## 9) Risk register

| # | Risk | Likelihood/Impact | Mitigation |
|---|---|---|---|
| 1 | **@vite-pwa/astro has no Astro 7 peer support** — overrides workaround is community-tested only (**UNVERIFIED** first-party) and could break on any release ([#72](https://github.com/vite-pwa/astro/issues/72)) | Med / High | Pin exact versions; verify `npm ci` + build in M0; tracked TODO to drop the override; fallback = raw `vite-plugin-pwa` in `vite.plugins` |
| 2 | **Offline scramble/3D breaks if lazy cubing.js chunks miss the precache** (worker entry, wasm-in-JS 215 KB gz, solver + 3D chunks all load at runtime) | Med / High | `globPatterns` covers all `dist` JS; `maximumFileSizeToCacheInBytes: 8 MiB`; Playwright offline E2E that actually generates a scramble and renders a player |
| 3 | **In-browser scramble after production Astro build UNVERIFIED** in a real browser (only build output + [#323](https://github.com/cubing/cubing.js/issues/323) attest) | Low / High | M0 gate: deploy preview, run `randomScrambleForEvent("333"/"444"/"555")` in-browser before building features on it |
| 4 | **cubing.js pre-1.0 `experimental-*` API churn** | Med / Med | Exact pin `0.63.3`; upgrades are deliberate tasks with visual regression + kpuzzle test suite |
| 5 | **Playwright `setOffline` doesn't block SW-originated fetches** ([#2311](https://github.com/microsoft/playwright/issues/2311) closed unfixed) → false-passing offline tests | Med / Med | `PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS=1` + route-abort of `route.request().serviceWorker()`; or server-kill variant |
| 6 | **Vercel Deployment Protection breaks preview SW/mobile testing** (on by default) | High / Low | Disable Vercel Authentication at project creation; `curl -sI <preview>/sw.js` in the deploy checklist |
| 7 | **Atomic deploys 404 old hashed assets** for offline users mid-upgrade | Med / Med | Full precache-at-install; `registerType: 'prompt'` toast so users pull complete new versions |
| 8 | **ts-fsrs v6 imminent** (removes `elapsed_days`, monorepo reshape) | Med / Low | `^5.4.1`; persist raw Cards only; never touch `elapsed_days`; remember `get_retrievability` string gotcha |
| 9 | **Safari 7-day eviction wipes non-installed users' progress** ([WebKit ITP](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/)) | Med / High | `persist()` on first save (user gesture) + install nudge (installed apps exempt) + prominent JSON export |
| 10 | **JSON import must revive Date fields** for the `by-due` index — ts-fsrs tolerating strings masks the bug | Med / Med | Import path revives dates (§5); roundtrip unit test export→import→`getDueCards()` |
| 11 | **F2L PDF → 41-case mapping is manual and error-prone** (no case numbers in extracted text) | High / Med | Budget human verification; verify every alg solves its case via kpuzzle in CI; map to SCDB numbering |
| 12 | **4x4 vs 5x5 parity algs differ by one move** (`Rw'` vs `3Rw'`) — copy-paste hazard | Low / High | Two distinct data entries; kpuzzle verification on the correct puzzle each |
| 13 | **JPerm `/lib/*.js` format is undocumented/internal** | Low / Low | One-time extraction, commit JSON; script fails loudly if format shifts |
| 14 | **Astro 7 Sätteri/Rust compiler differences** (no recma, unclosed-tag errors, `compressHTML: 'jsx'`) | Low / Med | Write MDX fresh (no legacy markup); opt into `unified()` only if a needed remark plugin surfaces |
| 15 | **Hobby plan hard-pauses on overage; non-commercial only; org repos unsupported** ([limits](https://vercel.com/docs/limits)) | Low / Med | Static-only keeps costs near zero; keep repo on personal account; app stays free |
| 16 | **CuberPal competitive gap may narrow** (Android in dev; fast iteration) — web still unannounced | Low / Low | Ship the free web/PWA wedge fast; 4x4/5x5 curriculum is uncontested |
| 17 | **iOS icon precedence UNVERIFIED on iOS 26** (apple-touch-icon vs manifest icons, last verified iOS 15.4–17) | Low / Low | Ship apple-touch-icon identical to manifest icon art so precedence is moot |
| 18 | **Node floor**: Astro needs >=22.12, cubing >=22.3 | Low / Med | `engines.node: ">=22.12.0"`, pin Node 22 in Vercel + CI |