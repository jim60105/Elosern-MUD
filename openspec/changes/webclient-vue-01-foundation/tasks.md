## 1. Toolchain and offline bundle

- [ ] 1.1 Add `package.json` + lock at the repo root with dev-only deps (Vue 3, Vite, `@vitejs/plugin-vue`, Pinia, `@storybook/vue3` + vite framework, Vitest, `@vue/test-utils`, `@storybook/test`); confirm CI Node 24 is used
- [ ] 1.2 Add `vite.config.*` emitting stable, non-hashed entry names into `web/static/webclient/app/dist/` with esbuild CJS interop for importing `web/static/webclient/js/elosern/*`; add `web/webclient-app/lib/*` ES re-exports (protocol, keyboard_router, narrative_markup, local_map, choicepoint, option_cards)
- [ ] 1.3 Extract the design system: CSS custom-property tokens (ink-night palette, single seal-red accent, type ramps, spacing, motion), subsetted self-hosted `.woff2` fonts, `prefers-reduced-motion`, not-color-only status utilities
- [ ] 1.4 Add a minimal offline Vue root (build stub) so the bundle, its styles, and its fonts load from the origin offline
- [ ] 1.5 Write the shared `frontend-vue-architecture.md` (Context, D1–D10, risks) and `frontend-developer-guide.md` reference docs under `docs/development/` (leave linking to D1)

## 2. Text fallback and shell load flag

- [ ] 2.1 Implement the dependency-free vanilla text console bound directly to `evennia.js`, independent of Vue and jQuery
- [ ] 2.2 Add the `base.html` mutually-exclusive script-load flag (Vue bundle XOR legacy plugins, single default legacy); do not flip to Vue and do not mount the app here
- [ ] 2.3 Transport-bootstrap spike: confirm Evennia 6.1's `evennia.js` connects and round-trips text without jQuery (else add a minimal scoped local jQuery to that path only and document it)

## 3. Build pipeline and CI gates

- [ ] 3.1 Add the frontend gate steps to `quality-gate.yml` (non-suppressed): `npm ci`, Vite production build, Vitest component tests, Storybook build + component-coverage; the `dist` consumed by the browser workspaces
- [ ] 3.2 Add the `dist` build to the browser test workspaces and a Containerfile Node build stage (entrypoint `collectstatic` after build, persistent static volume refreshed)
- [ ] 3.3 Add a managed browser check that the Vite bundle loads from the project origin with all non-local requests blocked, using the XOR flag on a test-routed page (or a dedicated `?__vue=1` fixture) so the production `base.html` default stays legacy
- [ ] 3.4 Gate: `npm ci && npm run build && npm test && npm run build-storybook` green, the dependency-free Node gate still green, and the offline-load browser check passes

## 4. Traceability (archive gate)

- [ ] 4.1 Add `@covers_requirement`-annotated Python tests (wrapping the Node/Vitest/browser execution) for each `webclient-browser-verification` requirement this change modifies, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
