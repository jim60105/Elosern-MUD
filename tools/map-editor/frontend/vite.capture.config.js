import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { EDITOR_ALIASES } from "./editor-aliases.mjs";

// Offline capture build: the editor's aliases and import boundary, but a
// map-only document opened straight from disk.
//
// A file:// page cannot load ES modules (an opaque origin blocks them), so the
// entry is one classic IIFE script: no code splitting, no module preload, no
// dynamic chunk fetch. Assets stay separate files addressed relatively, so the
// local font faces and the stylesheet resolve next to index.html without a
// server. The normal `build`/`dist/` output and entry are untouched.
const FRONTEND = fileURLToPath(new URL(".", import.meta.url));
const REPO_ROOT = resolve(FRONTEND, "../../..");

// Vite writes every page entry as `<script type="module">` and marks the
// assets `crossorigin`; on file:// a module script is refused (the origin is
// opaque) and a CORS-marked stylesheet cannot be fetched either. The bundle is
// already a classic IIFE, so the emitted page only has to say so: drop the
// module type, the preload hints that assume a module graph, and the CORS
// marker that no file:// response can satisfy.
function classicPage() {
  return {
    name: "capture-classic-page",
    enforce: "post",
    generateBundle(_options, bundle) {
      for (const output of Object.values(bundle)) {
        if (output.type === "asset" && output.fileName.endsWith(".html")) {
          output.source = String(output.source)
            .replace(/<script type="module" crossorigin /g, "<script defer ")
            .replace(/<link rel="modulepreload"[^>]*>/g, "")
            .replace(/ crossorigin/g, "");
        }
      }
    },
  };
}

export default defineConfig({
  root: resolve(FRONTEND, "capture"),
  base: "./",
  publicDir: false,
  plugins: [vue(), classicPage()],
  resolve: {
    alias: Object.fromEntries(
      Object.entries(EDITOR_ALIASES).map(([key, target]) => [key, resolve(REPO_ROOT, target)]),
    ),
  },
  build: {
    outDir: resolve(FRONTEND, "capture-dist"),
    emptyOutDir: true,
    assetsDir: "assets",
    assetsInlineLimit: 0,
    // One stylesheet file, linked relatively from the page: the theme tokens,
    // the editor rule set and the capture page's own rules stay inspectable
    // files next to the bundle instead of a <style> injected by the script.
    cssCodeSplit: false,
    modulePreload: false,
    rollupOptions: {
      output: {
        format: "iife",
        inlineDynamicImports: true,
        entryFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
