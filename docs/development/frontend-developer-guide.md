# Frontend Developer Guide (Vue WebClient)

**Owner change:** A2 (`webclient-vue-01-foundation`) authored this document.
**Precedence:** shared how-to only — the change-specific OpenSpec artifacts
and the architecture reference
([`frontend-vue-architecture.md`](frontend-vue-architecture.md)) outrank it.
**Linked from:** `docs/_sidebar.md` at D1.

## Prerequisites

- **Node 24 + npm** (the CI quality gate pins Node 24; the repo's Python side
  is uv-managed and independent of Node).
- **uv 0.12.0+** for the Python/Evennia side (browser tests boot a real
  server).
- No other setup: the frontend is a dev/CI-time toolchain only — the browser
  runtime never fetches an npm package or any remote asset.

## Commands (repo root)

| Command | What it does | CI owner |
| --- | --- | --- |
| `npm ci` | Install the locked toolchain (dev-only deps) | `frontend` job, browser workspaces |
| `npm run build` | Vite production build → `web/static/webclient/app/dist/` (stable `index.js` + `index.css`, hashed `assets/`; **not committed**) | `frontend` job, browser workspaces |
| `npm test` | Vitest component gate (`web/webclient-app/**/*.test.js`, jsdom, offline) | `frontend` job + top-level contract tests |
| `npm run build-storybook` | Storybook static build → `.storybook-out/` (gitignored) | `frontend` job |
| `npm run showcase-coverage` | Component-coverage check against `web/webclient-app/component-manifest.json` | `frontend` job + top-level contract tests |
| `npm run dev` | Vite dev server (HMR) for local work | — (local only) |
| `node --test web/static/webclient/js/tests/*.test.js` | Dependency-free Node gate over the preserved DOM-independent logic (~1 s) | preflight + top-level contract tests |

**Python-vs-npm split:** everything under `web/static/webclient/js/`
(elosern logic, plugins, the text console) is dependency-free and Node-24
`node --test` gateable — no `require` of an npm package, no `document`/
`window` at load time, `module.exports` UMD. Everything under
`web/webclient-app/` is the Vue app (Vite/Vitest/Storybook). `package.json`
stays at the repo root with **no runtime `dependencies`** (contract-tested).

## Layout

```
package.json / package-lock.json / vite.config.js / vitest.config.js   (root)
.storybook/                                     vue3-vite config (root)
scripts/component-coverage.mjs                  Storybook coverage gate
web/webclient-app/
  package.json                                  ("type": "module" for the app tree)
  main.js                                       SPA entry (mounts #main-sub)
  App.vue                                       root (A2 build stub; B1 AppShell)
  lib/*.js                                      ESM wrappers over js/elosern/* (CJS interop)
  styles/tokens.css                             design-system tokens (D6)
  styles/fonts.css                              self-hosted @font-face (D6)
  styles/app-shell.css                          stub page chrome
  fonts/{iansui,notosans,notoserif}/*.woff2     subsetted faces from the 設計稿
  component-manifest.json                       required-story manifest (B1 seeds, B5 freezes)
  tests/*.test.js                               Vitest component gate
  stories/**                                    Storybook stories (B wave onward)
web/static/webclient/
  js/elosern/*                                  preserved DOM-independent logic (re-exposed via lib/*)
  js/text_console.js                            D10 vanilla console (both branches)
  js/jquery_ready_shim.js                       the evennia.js ready bootstrap shim
  css/webclient.css  css/ansi_palette.css       shared page + ANSI theme
  app/dist/                                     Vite output (gitignored, built everywhere it's served)
  (the retired `js/plugins/*` view plugins, `vendor/*` runtimes, and dead CSS
   goldenlayout.css / elosern.css were deleted at D1)
web/templates/webclient/base.html               XOR-flag script loading (A2)
web/webclient/context_processors.py             webclient_vue_enabled context value
```

## Hard rules

1. **Never edit `web/static/webclient/js/elosern/*`** (or its Node tests) to
   serve the Vue app. Import them through `web/webclient-app/lib/*`; if a
   wrapper needs a tweak, the wrapper changes, not the UMD source.
2. **No remote runtime request.** The built page loads only from the project
   origin; do not add any CDN, registry fetch at runtime, or absolute
   third-party URL. `base.html` stays pinned-local.
3. **No runtime npm dependency.** `package.json` must keep a `devDependencies`
   only layout; the Node gate stays dependency-free.
4. **Build the dist before browser tests.** The managed browser suite serves
   static files from the checkout; without `npm run build` the Vue-branch
   checks fail. (CI builds it in both workspaces automatically.)
5. **The XOR flag is mutually exclusive.** One view stack per page:
   `webclient_vue_enabled` (context) picks the Vue bundle **or** the legacy
   rollback branch (the D10 vanilla text console, no view code). Production
   default is the **Vue bundle** (flipped at C4); the legacy branch is only
   reachable by rollback. `?__vue=1` forces the Vue branch for review /
   offline-load checks; `ELOSERN_BROWSER_VUE_CLIENT=1` (browser test settings)
   is the test-config switch C3 uses.

## Browser (managed-runtime) tests

- Run one focused file/class rather than the whole suite:
  `uv run --locked python -m unittest web.tests.browser.test_vue_foundation`
  (boots a real loopback Evennia server; ~1–2 min for the A2 class).
- New browser test methods must be added to **exactly one** process list in
  `.github/browser-shards.json` (enforced by
  `tests/test_evennia_test_optimization_contract.py`).
- Every non-local request is aborted by `guard_local_only`; deterministic
  fixtures only (`web/tests/browser/seed.py`) — no LLM, no image service.

## Container

The `Containerfile` `vue-dist` stage (Node 24) runs `npm ci && npm run build`
and the app-layout stage copies the produced `dist` into
`/app/web/static/webclient/app/dist/`; the entrypoint runs
`evennia collectstatic --noinput` after `evennia migrate --noinput` to
refresh the persistent `server/.static` volume. Local workflow:
`podman compose build && podman compose up` (do not add Ollama/sd-webui to
the image).

## Traceability for frontend-adjacent requirements

Browser tests and top-level contract tests carry
`@covers_requirement(...)` annotations (import from
`tools.spec_traceability`); see
[`spec-test-traceability.md`](spec-test-traceability.md). The A2 gates are
covered by `tests/test_frontend_toolchain_contract.py` (npm execution),
`tests/test_browser_verification_contract.py` (workflow/static), and
`web/tests/browser/test_vue_foundation.py` (browser behavior).
