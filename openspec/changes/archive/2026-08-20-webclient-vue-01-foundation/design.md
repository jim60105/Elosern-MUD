## Context

Part **A2** (foundation; parallel to A1, no shared file). This is the substrate for the whole migration.
Shared architectural context (Vue/Vite/Pinia choice, reuse-not-rewrite, offline bundle, design system)
lives in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, the roadmap, and (authored here,
linked in D1) `docs/development/frontend-vue-architecture.md`.

## Goals / Non-Goals

**Goals**
- A green, offline, gated npm toolchain that builds a self-contained bundle from the project origin and
  reuses the preserved logic unchanged.
- The design-system tokens/fonts, the dependency-free vanilla text console + `base.html` XOR flag.
- The `dist` produced in every serving environment (CI browser workspaces + container) and the CI gates.
- A transport spike proving `evennia.js` round-trips text without jQuery.

**Non-Goals**
- No real components (B wave), no store (C1), no transport/OOB binding or mount (C3), no façade bridge
  (C2), no shell swap. The Vue load into the live page is infrastructure only (XOR flag), default legacy.

## Decisions

- **D1 — Reuse the logic via CJS interop, never edit it.** The `js/elosern` UMD modules are imported by
  the Vite bundle through `lib/*` ES wrappers (esbuild CommonJS interop); the source and its
  dependency-free Node gate are untouched. Caveat: esbuild CJS interop does **not** set the
  `window.Elosern.*` browser globals — that is C2's browser-bridge job; A2 only proves the import builds.

- **D2 — Stable, non-hashed `dist` from the origin; not committed; built everywhere it's served.**
  `vite.config` emits `webclient/app/dist/index.js` + `index.css` + a hashed assets dir; `dist/` stays out
  of git; it is `npm run build` output produced in the CI preflight/browser workspaces and in the
  Containerfile Node build stage, published atomically so a stale entry never points at a removed chunk.
  The offline-load bundle check loads the Vue app via the XOR flag on a **test-routed page / `?__vue=1`
  fixture**, so the bundle, its styles, and its self-hosted fonts are proven to load from the origin offline
  while the production default remains legacy (the Vue production flip is C4).

- **D3 — Design system as tokens + self-hosted fonts.** Extract the 設計稿 into CSS custom properties
  (palette, single accent, ramps, spacing, motion) + subsetted local `.woff2`; reduced-motion and
  not-color-only enforced at the token/utility level so they are testable.

- **D4 — Dependency-free vanilla text console (D10).** A small vanilla-JS input/output bound directly to
  `evennia.js`, loaded independent of Vue and jQuery; the authoritative text path (hidden once the app
  mounts, active again on bundle failure / incompatible OOB). `base.html` gets a mutually-exclusive
  script-load flag (Vue bundle XOR legacy plugins, single default, review-window only) — a transient
  switch, not a compatibility layer (0 users). The transport spike confirms `evennia.js` round-trips
  text without jQuery before relying on it.

## Risks / Trade-offs

- **Two DOM managers during the switch** → the mutually-exclusive flag (never both), single default,
  deleted in D1. **`dist/` 404 in a serving env** → built in workspace + container, CI-gated, browser
  check blocks non-local requests. **npm in a Python-first repo** → dev/CI-only, Node gate stays
  dependency-free, AGENTS split documented in D1. **jQuery turns out load-bearing for transport** →
  spike result: keep a minimal scoped local jQuery for that path only, documented; otherwise drop it.

## Migration Plan

XOR flag off by default (legacy) until C4 flips the production default to Vue (C3 uses the flag in a
test config only, per the roadmap §5/§6.1); rollback is reverting the `base.html` script wiring.
No server/protocol/Telnet impact.

## Resolved During Implementation

- **Containerfile stage + collectstatic ordering:** a `vue-dist` Node 24 stage (uv/npm-cache mounted)
  runs `npm ci && npm run build` and the `app-layout` stage copies the produced
  `web/static/webclient/app/dist/` into the served image tree; the entrypoint runs
  `evennia migrate --noinput`, then `evennia collectstatic --noinput` (refreshing the persistent
  `server/.static` volume), then `evennia start --log`. The portal also serves static through the
  filesystem finder, so the baked `dist` is served either way.
- **Version pins:** locked in the A2 `package-lock.json` — Vue 3.5.x, Vite 6.x, Pinia 3.x,
  Storybook 8.6.x, Vitest 3.2.x, `@vitejs/plugin-vue` 6.x, `@vue/test-utils` 2.4.x, `esbuild` 0.25.x
  (the explicit CJS-interop transform), Node 24 in every CI job.
- **CJS interop mechanism:** Rollup does not auto-convert source-tree CJS, so the Vite build applies an
  explicit esbuild `CJS -> ESM` transform (the `elosern-cjs-interop` plugin, `vite.config.js`) to
  `web/static/webclient/js/**` imports; the bundle is asserted to carry the preserved reducer by
  `tests/test_frontend_toolchain_contract.py`.
