## Why

This is change **A2**, the foundation, of the Vue SPA WebClient migration (see
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`; depends on nothing,
runs **parallel** to A1 with no shared file). Every later change is built on the offline, buildable,
gated frontend foundation this change stands up: the npm/Vue/Vite/Pinia/Storybook/Vitest toolchain, the
ESM `lib` wrappers over the preserved logic, the offline design system, the dependency-free vanilla text
console (D10) with its `base.html` mutually-exclusive load flag, and the `dist`-in-every-serving-environment
build pipeline. It also proves Evennia 6.1's `evennia.js` round-trips text without jQuery (the transport
spike) so the text fallback is re-founded on the transport alone.

## What Changes

- **npm/Node toolchain (dev-only):** `package.json` + lock, `vite.config` (stable, non-hashed entry names
  into `web/static/webclient/app/dist`, CJS interop for `web/static/webclient/js/elosern/*`), `.storybook/`
  (vue3 + vite) with a component-coverage script skeleton, and Vitest.
- **`web/webclient-app/lib/*`:** ES-module wrappers re-exporting the preserved pure logic (protocol,
  keyboard_router, narrative_markup, local_map, choicepoint, option_cards) so the bundle imports them
  without editing the source or its Node gate.
- **Offline design system:** the 設計稿 tokens (ink-night palette, single seal-red accent, type ramps,
  spacing, motion), subsetted self-hosted `.woff2` fonts, `prefers-reduced-motion`, and not-color-only
  status utilities.
- **Dependency-free vanilla text console (D10)** + the `base.html` mutually-exclusive script-load flag
  (Vue bundle XOR legacy plugins, single default legacy, review-window only); the production flip-to-Vue
  is C4 (C3 uses the flag in a test config only, per the roadmap §5/§6.1).
- **Build pipeline + CI gates:** `npm ci` / Vite build / Vitest / Storybook build + component-coverage as
  non-suppressed quality-gate steps; the `dist` built in the browser test workspaces and in the container
  image; a browser check that the bundle loads from the origin with all non-local requests blocked.
- **A transport-bootstrap spike:** confirm `evennia.js` connects and round-trips text without jQuery.
- **A minimal offline Vue root (build stub)** so `build` / Storybook / the offline-load check are green;
  the real `AppShell` lands in B1.

## Capabilities

### New Capabilities
(none — `webclient-vue-application` and `webclient-component-showcase` are introduced in B1.)

### Modified Capabilities
- `webclient-browser-verification`: the Node gate wording now states the pure logic is dependency-free
  UMD/CommonJS imported by the Node gate *and* reused by the Vue app via Vite CJS interop, with the Vue
  view layer in a separate Vitest gate; the mandatory quality-gate steps gain the `npm ci` / Vite build /
  Vitest / Storybook + component-coverage / `dist` pipeline.

## Impact

- **New:** `package.json`/lock, `vite.config`, `.storybook/`, `vitest` config, `web/webclient-app/lib/*`
  + design tokens/fonts + a minimal root, the CI gate steps, a Containerfile Node build stage, and the
  shared `frontend-vue-architecture.md` + `frontend-developer-guide.md` reference docs (linked in D1).
- **Modified:** `web/templates/webclient/base.html` (XOR flag + vanilla console + bundle-load
  infrastructure; the test-harness mount is C3 and the production flip-to-Vue is C4),
  `.github/workflows/quality-gate.yml`, `Containerfile` /
  `docker-entrypoint.sh`, `docs/development/` (the two reference docs).
- **Preserved:** the preserved `js/elosern/*` logic (wrapped, never edited), the dependency-free Node gate,
  `evennia.js` transport, and all server/OOB behavior.
