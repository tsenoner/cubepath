// @ts-check
import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

/**
 * Vite's preload helper touches `document` unguarded, which crashes when it
 * gets bundled into cubing.js's search worker chunk (vitejs/vite#14499,
 * cubing/cubing.js#309). Guard the DOM branch so the helper degrades to a
 * plain dynamic import inside workers.
 */
function workerSafePreloadHelper() {
  /** @type {import("astro").AstroIntegration} */
  const integration = {
    name: "worker-safe-preload-helper",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        const astroDir = join(fileURLToPath(dir), "_astro");
        for (const name of await readdir(astroDir)) {
          if (!name.startsWith("preload-helper") || !name.endsWith(".js")) continue;
          const path = join(astroDir, name);
          const src = await readFile(path, "utf8");
          const patched = src.replace(
            /if\((\w+)&&\1\.length>0\)\{/,
            'if($1&&$1.length>0&&typeof document<"u"){',
          );
          if (patched === src) {
            throw new Error(
              "worker-safe-preload-helper: pattern not found — Vite's helper changed; re-verify worker safety",
            );
          }
          await writeFile(path, patched);
        }
      },
    },
  };
  return integration;
}

// https://astro.build/config
export default defineConfig({
  site: "https://cubepath.vercel.app",
  output: "static",
  integrations: [mdx(), workerSafePreloadHelper()],
  vite: {
    // Known-good cubing.js setup (cubing.js#323/#327)
    optimizeDeps: { exclude: ["cubing"] },
    worker: { format: "es" },
  },
});
