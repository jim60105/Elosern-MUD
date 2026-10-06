import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { GM_ALIASES } from "./web/admin-app/gm-aliases.mjs";

// GM portal build (gm-portal-s1-foundation, design D4): an independent entry,
// base, and output so the operator SPA never shares a runtime with the game
// bundle. The game's vite.config.js keeps its single-stylesheet invariant
// untouched. Entry names are stable (non-hashed) because the Django shell
// template (web/templates/gm/index.html) references them directly; only the
// assets/ dir is hashed. The cleaning boundary is web/static/gm/dist alone.
const ROOT = fileURLToPath(new URL(".", import.meta.url));
const DIST_BASE = "/static/gm/dist/";
const OUT_DIR = resolve(ROOT, "web/static/gm/dist");

// Move the single merged entry stylesheet (cssCodeSplit: false) to the
// stable dist-root index.css.
function stableGmEntryCss() {
  return {
    name: "elosern-gm-stable-entry-css",
    enforce: "post",
    generateBundle(_options, bundle) {
      if (!bundle["index.js"]) return;
      const cssAssets = Object.values(bundle).filter(
        (item) => item.type === "asset" && item.fileName.endsWith(".css"),
      );
      if (cssAssets.length !== 1) {
        throw new Error(
          `GM build: expected exactly one entry CSS asset, found ${cssAssets.length}`,
        );
      }
      cssAssets[0].fileName = "index.css";
    },
  };
}

export default defineConfig({
  base: DIST_BASE,
  publicDir: false,
  plugins: [vue(), stableGmEntryCss()],
  resolve: {
    alias: Object.fromEntries(
      Object.entries(GM_ALIASES).map(([key, target]) => [key, resolve(ROOT, target)]),
    ),
  },
  build: {
    outDir: OUT_DIR,
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: { index: resolve(ROOT, "web/admin-app/main.js") },
      output: {
        entryFileNames: "index.js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
