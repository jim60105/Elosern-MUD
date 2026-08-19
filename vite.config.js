import { defineConfig } from "vite";
import { transformSync } from "esbuild";
import vue from "@vitejs/plugin-vue";

// A2 (webclient-vue-01-foundation): the Vue view layer builds into the
// existing static tree so the page stays fully served from the project origin
// (offline invariant). Entry names are stable (non-hashed) because the Django
// template references them directly; only the assets/ dir is hashed. The
// preserved DOM-independent logic is imported through web/webclient-app/lib/*
// ES wrappers — the UMD sources and the dependency-free Node gate are never
// edited.
const DIST_BASE = "/static/webclient/app/dist/";

// The preserved UMD logic is CommonJS (`module.exports = factory()`). Rollup
// does not auto-convert source-tree CJS, so the interop is explicit esbuild
// (design D1): anything the app imports from web/static/webclient/js is
// transformed to ESM with CJS default-export semantics. The files keep
// working under Node's node --test (untransformed CJS) and under the browser
// script-load path (the UMD root-global branch).
function elosernCjsInterop() {
  return {
    name: "elosern-cjs-interop",
    enforce: "pre",
    transform(code, id) {
      const cleanId = id.split("?")[0];
      if (!/web[\\/]static[\\/]webclient[\\/]js[\\/]/.test(cleanId)) return null;
      if (!/\bmodule\.exports\b/.test(code)) return null;
      const result = transformSync(code, {
        loader: "js",
        format: "esm",
        sourcemap: "external",
      });
      return { code: result.code, map: result.map };
    },
  };
}

// Vite emits the single merged entry stylesheet (cssCodeSplit: false) as a
// hashed "style-*.css" asset inside assets/. The template must reference a
// stable name (design D2/D3), so move it to the stable, dist-root index.css.
// Asset URLs inside the stylesheet are absolute (base), so no rewriting is
// needed.
function stableEntryCss() {
  return {
    name: "elosern-stable-entry-css",
    enforce: "post",
    generateBundle(_options, bundle) {
      const cssAssets = Object.values(bundle).filter(
        (item) => item.type === "asset" && item.fileName.endsWith(".css"),
      );
      if (cssAssets.length !== 1) {
        throw new Error(
          `expected exactly one entry CSS asset, found ${cssAssets.length}: ` +
            cssAssets.map((item) => item.fileName).join(", "),
        );
      }
      const css = cssAssets[0];
      if (!css.fileName.startsWith("assets/")) {
        throw new Error(`unexpected entry CSS location: ${css.fileName}`);
      }
      if (bundle["index.css"]) {
        throw new Error("stable entry CSS already present in bundle");
      }
      css.fileName = "index.css";
    },
  };
}

export default defineConfig({
  base: DIST_BASE,
  plugins: [vue(), elosernCjsInterop(), stableEntryCss()],
  build: {
    outDir: "web/static/webclient/app/dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: {
        index: "web/webclient-app/main.js",
      },
      output: {
        entryFileNames: "index.js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
