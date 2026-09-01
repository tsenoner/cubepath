import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Every route the site publishes, read from the built sitemap.
 *
 * A MODULE, not a spec — Playwright's default `testMatch` only collects
 * `*.spec.ts`, so nothing here runs as a suite. It lives on its own because
 * three specs wanted it and each grew its own copy: `regressions.spec.ts` read
 * every shard off disk, while `nav.spec.ts` and `stickering.spec.ts` fetched
 * `sitemap-0.xml` by name over HTTP. The shard detail is the whole point of
 * the careful one — @astrojs/sitemap shards at 45,000 URLs and a hardcoded
 * shard would quietly stop covering the overflow — so the copies that skipped
 * it were sweeps that silently stop being exhaustive.
 *
 * `npx playwright test` serves `dist/` via `astro preview`, so a build is
 * already a precondition of any suite that imports this.
 */
const DIST = fileURLToPath(new URL("../dist/", import.meta.url));

/**
 * Every route the site publishes, as a path, in sitemap order. Read from every
 * `sitemap-N.xml` rather than just `sitemap-0.xml`, because @astrojs/sitemap
 * shards at 45 000 URLs and a hardcoded shard would quietly stop covering the
 * overflow.
 */
export function publishedRoutes(): string[] {
  const shards = readdirSync(DIST).filter((f) => /^sitemap-\d+\.xml$/.test(f));
  if (shards.length === 0) {
    throw new Error(
      `no sitemap-N.xml in ${DIST} — the E2E suite needs a build first ` +
        "(`npx astro build`, or `make ci`).",
    );
  }
  const routes = shards
    .sort()
    .flatMap((shard) => [
      ...readFileSync(join(DIST, shard), "utf8").matchAll(/<loc>([^<]+)<\/loc>/g),
    ])
    .map((m) => m[1])
    .filter((loc): loc is string => typeof loc === "string")
    .map((loc) => new URL(loc).pathname);
  if (routes.length === 0) throw new Error(`${DIST} sitemaps contained no <loc> entries`);
  return routes;
}
