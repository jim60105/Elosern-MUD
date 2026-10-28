import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { EDITOR_ALIASES } from "./editor-aliases.mjs";

// Standalone map editor build: an independent root, entry and output served
// by the editor service from dist/. No game bundle, CDN or runtime network
// asset: fonts referenced by the allowlisted font CSS are emitted locally.
const FRONTEND = fileURLToPath(new URL(".", import.meta.url));
const REPO_ROOT = resolve(FRONTEND, "../../..");

export default defineConfig({
  root: FRONTEND,
  base: "/",
  publicDir: false,
  plugins: [vue()],
  resolve: {
    alias: Object.fromEntries(
      Object.entries(EDITOR_ALIASES).map(([key, target]) => [key, resolve(REPO_ROOT, target)]),
    ),
  },
  server: {
    fs: { allow: [FRONTEND, resolve(REPO_ROOT, "packages/map-view"), resolve(REPO_ROOT, "web/webclient-app")] },
  },
  build: {
    outDir: resolve(FRONTEND, "dist"),
    emptyOutDir: true,
    assetsDir: "assets",
    // Never inline: every font stays a same-origin file (CSP font-src 'self').
    assetsInlineLimit: 0,
    modulePreload: { polyfill: false },
  },
});
