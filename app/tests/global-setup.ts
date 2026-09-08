import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

import type { sync } from "astro";

/**
 * Give vitest a content collection to read.
 *
 * Vitest runs Vite in serve mode, and in serve mode Astro's content plugin
 * reads the DEV data store, `.astro/data-store.json` — a file only `astro dev`
 * writes. `astro sync`, `astro check` and `astro build` all write
 * `node_modules/.astro/data-store.json` instead, so on a fresh checkout every
 * `getCollection()` inside a test returned `[]`, and the first spec to iterate
 * the lessons passed in CI with nothing to check (run 33872766897 is the one
 * that caught it, because it also pinned a count). Pointing Astro's own
 * programmatic `sync` at the dev location is the one public knob that makes the
 * two agree; `tests/teaches.spec.ts` asserts the collection is the whole lesson
 * directory, so this cannot silently stop working.
 *
 * The import goes through the resolved file rather than the bare `astro`
 * specifier because inside Astro's Vite config that specifier resolves to an
 * empty module (it is the name `.astro` components import the runtime under).
 */
export async function setup(): Promise<void> {
  const astroEntry = pathToFileURL(createRequire(import.meta.url).resolve("astro")).href;
  const astro = (await import(astroEntry)) as { sync: typeof sync };
  await astro.sync({
    root: fileURLToPath(new URL("../", import.meta.url)),
    cacheDir: ".astro",
    logLevel: "silent",
  });
}
