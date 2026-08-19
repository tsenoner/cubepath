// @ts-check
import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import AstroPWA from "@vite-pwa/astro";

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
  site: "https://cubepath-six.vercel.app",
  output: "static",
  integrations: [
    mdx(),
    AstroPWA({
      registerType: "prompt",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        id: "/",
        name: "Cubepath",
        short_name: "Cubepath",
        description: "Learn to solve the cube: zero to full CFOP, plus 4×4 and 5×5. Free, offline, interactive.",
        start_url: "/",
        scope: "/",
        display: "standalone",
        theme_color: "#fcfbf8",
        background_color: "#fcfbf8",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icons/maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
          { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Precache EVERYTHING — the whole course must work in airplane mode,
        // including cubing.js's lazy worker/wasm/3D chunks.
        globPatterns: ["**/*.{css,js,html,svg,png,ico,txt,json,webmanifest,woff2,wasm,pdf}"],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        navigateFallback: null,
      },
      experimental: { directoryAndTrailingSlashHandler: true },
      devOptions: { enabled: false },
    }),
    workerSafePreloadHelper(),
  ],
  vite: {
    // Known-good cubing.js setup (cubing.js#323/#327)
    optimizeDeps: { exclude: ["cubing"] },
    worker: { format: "es" },
  },
});
