// @ts-check
import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import AstroPWA from "@vite-pwa/astro";
import { unified } from "@astrojs/markdown-remark";

import rehypeGlossary from "./scripts/rehype-glossary.mjs";

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

/**
 * Serve a SELF-DESTRUCTING /sw.js in dev, and only in dev.
 *
 * `devOptions: { enabled: false }` means the PWA plugin generates no service
 * worker in dev — but a browser that has ever loaded a production build or an
 * `astro preview` on this origin still has the real one REGISTERED, and a
 * registered worker re-fetches its own script forever to check for updates.
 * Against `astro dev` that request 404s, and because `[card].astro` is a
 * single-segment dynamic route the router matches the pattern first and logs a
 * confusing `getStaticPaths()` warning naming the card route, several times a
 * minute, for as long as the server runs.
 *
 * Answering with a worker that unregisters itself and drops its caches fixes it
 * properly rather than silencing it: the stale registration is gone after one
 * reload, and with it the stale PRECACHE, which is the more dangerous half —
 * a service worker left over from a previous build serves that build's assets
 * and hides the change you are looking at.
 *
 * `apply: "serve"` is load-bearing. This must never run during a build, where
 * the real Workbox `sw.js` is the whole PWA update mechanism.
 */
function devServiceWorkerReset() {
  // `event.waitUntil`, not a bare async listener: without it the browser is
  // free to terminate the worker the moment the handler returns its promise,
  // and the cache deletion this exists for is exactly the part that would be
  // cut short — leaving the stale precache that hides the change you are
  // looking at.
  const BODY = [
    "self.addEventListener('install', () => self.skipWaiting());",
    "self.addEventListener('activate', (event) => {",
    "  event.waitUntil((async () => {",
    "    try {",
    "      const keys = await caches.keys();",
    "      await Promise.all(keys.map((k) => caches.delete(k)));",
    "      await self.registration.unregister();",
    "      const clients = await self.clients.matchAll({ type: 'window' });",
    "      for (const c of clients) c.navigate(c.url);",
    "    } catch {}",
    "  })());",
    "});",
  ].join("\n");
  /** @type {import("vite").Plugin} */
  const plugin = {
    name: "dev-service-worker-reset",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? "").split("?")[0];
        if (url !== "/sw.js") return next();
        res.setHeader("Content-Type", "text/javascript");
        res.setHeader("Cache-Control", "no-store");
        res.end(BODY);
      });
    },
  };
  return plugin;
}

// https://astro.build/config
export default defineConfig({
  site: "https://cubepath-six.vercel.app",
  output: "static",
  // Card 1 prints "cubepath-six.vercel.app/learn" on card stock, but the
  // course index lives at "/" — `learn/[...slug]` only emits lesson pages, so
  // the printed URL 404'd. A printed URL cannot be reissued; send it home.
  redirects: { "/learn": "/" },
  // The glossary pass runs over lessons only and rewrites the first mention of
  // each term into a link carrying its definition — see
  // scripts/rehype-glossary.mjs for why this is a plugin and not a component.
  //
  // `markdown.processor`, not `mdx({ rehypePlugins })`: that option is
  // deprecated and, on this version, silently does nothing — the build warns
  // and then produces pages with no glossary links at all. `unified()` from
  // @astrojs/markdown-remark builds Astro's own pipeline with the plugin added,
  // and MDX inherits it.
  markdown: { processor: unified({ rehypePlugins: [rehypeGlossary] }) },
  integrations: [
    mdx(),
    sitemap(),
    AstroPWA({
      registerType: "prompt",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        id: "/",
        name: "Cubepath",
        short_name: "Cubepath",
        description:
          "Learn to solve the cube: zero to full CFOP, plus 4×4 and 5×5. Free, offline, interactive.",
        start_url: "/",
        scope: "/",
        display: "standalone",
        theme_color: "#fcfbf8",
        background_color: "#fcfbf8",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/maskable-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "maskable",
          },
          {
            src: "/icons/maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Precache EVERYTHING — the whole course must work in airplane mode,
        // including cubing.js's lazy worker/wasm/3D chunks.
        globPatterns: ["**/*.{css,js,html,svg,png,ico,txt,json,webmanifest,woff2,wasm,pdf}"],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        navigateFallback: null,
        // `group` is why the offline promise was only three-quarters true.
        // Every lesson's filled primary button is `/practice/?group=<key>` —
        // 16 of them across 12 lessons — and a precache lookup matches on the
        // FULL url, query string included. Workbox strips only `utm_*` and
        // `fbclid` by default, so `?group=` missed `practice/index.html`, and
        // with `navigateFallback: null` there is nothing behind that miss: the
        // button died in airplane mode. Worse quietly — that same element is
        // tagged `data-lesson-advance`, so it is one of the TWO writers of
        // lesson completion, and an offline reader taking the lesson's own
        // call to action earned no credit for the lesson.
        //
        // The option REPLACES the default rather than extending it, so both
        // Workbox defaults are re-listed here on purpose. Deleting either one
        // silently un-fixes a case this does not otherwise mention.
        ignoreURLParametersMatching: [/^utm_/, /^fbclid$/, /^group$/],
      },
      experimental: { directoryAndTrailingSlashHandler: true },
      devOptions: { enabled: false },
    }),
    workerSafePreloadHelper(),
  ],
  vite: {
    plugins: [devServiceWorkerReset()],
    // Known-good cubing.js setup (cubing.js#323/#327)
    optimizeDeps: { exclude: ["cubing"] },
    worker: { format: "es" },
  },
});
