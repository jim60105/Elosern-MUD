## 0. Phase 0 — Contract audit, transport spike, build pipeline (before app code)

- [ ] 0.1 Contract audit: enumerate every implementation-bound contract across `openspec/specs/webclient-*` and the Playwright suite — public façades (`window.Elosern.*`), the WebClient-plugin `onKeydown` path, DOM ids, layout-persistence keys, and the input path — and classify each as preserve-via-bridge vs delta; commit the frozen façade-bridge surface + the complete `MODIFIED`/`RENAMED` delta list, and apply those deltas to the affected capability specs
- [ ] 0.2 Transport-bootstrap spike: confirm Evennia 6.1's `evennia.js` connects and round-trips text without jQuery (else add a minimal local jQuery scoped to that path only)
- [ ] 0.3 Stand up the frontend build pipeline in CI: preflight `npm ci`/`npm run build`/Vitest/Storybook+component-coverage, the `dist` build in the browser test workspaces, and a Containerfile Node build stage; add a browser check that the Vite bundle loads from the project origin with all non-local requests blocked

## 1. Phase 1 — Commit the design 設計稿 to docs

- [ ] 1.1 Copy the validated showcase (the 設計稿 `index.html` + its self-hosted `fonts.css`/assets) into `docs/design/`, keep it self-contained/offline (no CDN), and make the fonts local
- [ ] 1.2 Add a `docs/_sidebar.md` entry for the 設計稿 under a design section so the design draft is linked and reachable from the docs home
- [ ] 1.3 Add a frontend developer-guide page under `docs/development/` (install, `npm ci`/`npm run build`/`npm test`/`npm run dev`/`npm run build-storybook`, the Python-vs-npm split) plus a sidebar entry
- [ ] 1.4 Add a small check (top-level or browser) that the 設計稿 file exists, is linked from `docs/_sidebar.md`, and renders with remote requests blocked; apply `covers_requirement` per the traceability doc

## 2. Phase 2 — Frontend toolchain (offline, no server)

- [ ] 2.1 Add `package.json` + lockfile at the repo root with dev-only deps (Vue 3, Vite, `@vitejs/plugin-vue`, Pinia, `@storybook/vue3` + vite framework, Vitest, `@vue/test-utils`, `@storybook/test`); confirm Node 24 in CI is used
- [ ] 2.2 Add `vite.config.*` emitting stable, non-hashed entry names into `web/static/webclient/app/dist/`, with esbuild CJS interop for importing `web/static/webclient/js/elosern/*` (protocol, keyboard_router, narrative_markup, local_map, choicepoint, option_cards)
- [ ] 2.3 Add `.storybook/` (vue3 + vite framework) and a deterministic component-coverage script that reads the required-component list (design D7) and fails when a component is unregistered/undocumented
- [ ] 2.4 Extract the 設計稿 design system: CSS custom-property tokens (ink-night palette, single seal-red accent, type ramps, spacing, motion), subsetted self-hosted `.woff2` fonts, `prefers-reduced-motion`, and colorblind-safe (not-color-only) status utilities
- [ ] 2.5 Add the frontend gate steps to `quality-gate.yml` (non-suppressed): `npm ci`, Vite production build, Vitest component tests, and Storybook build + component-coverage; the `dist` artifact is consumed by the browser workspaces and built in the container image — alongside the unchanged Node gate and every existing gate
- [ ] 2.6 In `base.html`, add a build/test-only flag with a mutually-exclusive script load (Vue bundle XOR legacy plugins, single default = Vue) kept only for one PR-review window, and add the dependency-free vanilla text console (D10) that talks to `evennia.js` independently of Vue and jQuery

## 3. Phase 2 — Build the component showcase (Storybook-first, offline, no live server)

- [ ] 3.1 Root/layout: `AppShell`, `TopBar`/`Header`, `ConnectOverlay` — SFCs + Storybook stories (props/events/states) + Vitest tests, matching the 設計稿
- [ ] 3.2 Narrative: `NarrativeFeed` (renders through the existing `narrative_markup` pipeline), `UnreadIndicator`, `CommandDrawer` — stories + tests (allowlist render vs literal-text degradation, unread count + jump, send/cancel focus)
- [ ] 3.3 Action dock: `ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`, `ChoicePointBlock` — stories + tests (focused cell + disabled, submenu detail pane, exact card shape, ready/generating states, move)
- [ ] 3.4 Status/character: `StatusPanel` (gauges hp/mp/sp, counters, static, wallet, conditions + derived modifiers), `CharacterPanel` (incl. equipped items, disguise, guild rank/merit, persona) — stories + tests (status never color-only, disguise display-only vs true traits). `IntimateStatus` is deferred (no field in the current status/character OOB payload).
- [ ] 3.5 Skill/book/map/art: `SkillBook` (active/passive tabs, categories, search, category>group>skill, cost/target/cast detail), `LocalMap` (states, actionable adjacent, legend + detail, colorblind-safe), `ArtPanel` (16:9 + portrait overlay, truthful placeholder, degraded) — stories + tests
- [ ] 3.6 Service panels (from the `services` OOB panel — no invented data): `ShopPanel` (stock/buy/sell), `QuestBoard` (+ detail), `LoreDrawer`, and `InventoryPanel` (equipped items only; full bag deferred) — stories + tests. A dedicated `PartyPanel` is deferred (no `party` OOB panel; the companion is only visible via `exploration` affordances).
- [ ] 3.7 Full overlays: `MapOverlay`, `SettingsOverlay` (fonts, type scale, reduced-motion, text-to-html toggle, colorblind + `options.*`), `HelpOverlay`, `CreationOverlay` (presets/custom/concept wizard, adult gate on both age fields, activate) — stories + tests
- [ ] 3.8 Confirm the deferred scopes (PartyPanel, IntimateStatus, full inventory bag, event-log Toasts) are NOT built here and are documented as separate OOB changes; assert no component mocks data it has no backing read model for
- [ ] 3.9 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green; `node --test web/static/webclient/js/tests/*.test.js` still green; no remote request in any story/build (verify offline)

## 4. Phase 3 — Wire to the live transport and replace the shell

- [ ] 4.1 Implement the public-contract bridge (D9 façades: `window.Elosern.{Protocol,KeyboardRouter,narrativeInput,actions}`) over the imported logic + store, and apply the Phase-0 audited `MODIFIED`/`RENAMED` deltas to the affected `webclient-*` specs; re-point their traceability tests
- [ ] 4.2 Build the Pinia store using the preserved protocol reducer (CJS-interop import) as its core; expose view slices; enforce atomic publish + subscribers-see-committed; add a store integration test for snapshot adoption and old-epoch/revision rejection
- [ ] 4.3 Bind the store to the `evennia.js` transport OOB events (snapshot/update/result/protocol-error) and dispatch actions through the unchanged allowlisted path (dispatch-only, one-mutation-in-flight, no local mutation); add reconnect/epoch/lock integration tests
- [ ] 4.4 Mount the app into `web/templates/webclient/webclient.html` (`#app`); retire the GoldenLayout `#main-sub` mount in favor of the Vue mount; keep the dependency-free vanilla text console (D10) as the always-playable text path
- [ ] 4.5 Migrate the legacy view behavior (`js/plugins/*_dock.js`, `elosern_ui.js`) into store-bound components; preserve the DOM contract hooks (`#action-dock`, `action-`/`target-` keys, `#combat-row-0`, panel ids) and add stable `data-testid` to every other interactive surface
- [ ] 4.6 Update `base.html` (remove the jQuery/GoldenLayout/plugin `<script>` loads; keep `evennia.js` + the vanilla text console + the Vite bundle + design-system CSS) so the page makes no remote runtime request
- [ ] 4.7 Re-map Playwright selectors to `data-testid` where preserved ids do not apply and make the per-surface browser slices green (layout/shell, local map, exploration, combat, combat-rejection, creation, services, input/narrative, options, art, choicepoints, pointer, session lifecycle, reconnect)
- [ ] 4.8 Offline/behavior regression: bundle blocked → text playable via the vanilla console; incompatible OOB → graphical locked with text round-tripping; reduced-motion honored; not-color-only status holds; 1440×900 and 1280×720 usable

## 5. Phase 4 — Remove legacy, finalize docs, amend design

- [ ] 5.1 Delete the retired legacy view files (jQuery dock plugins, goldenlayout plugin, `elosern_ui.js`) and dead CSS (`goldenlayout.css`, legacy `elosern.css` sections); confirm nothing imports them; keep `js/elosern/*` logic and `evennia.js`
- [ ] 5.2 Update `AGENTS.md` with the frontend commands, the Python-vs-npm split, and which JS gates (Node/Vitest/Storybook) apply
- [ ] 5.3 Amend the engine design doc (`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`) D13/webclient row from "GoldenLayout shell" to "Vue SPA on the same Evennia extension points"
- [ ] 5.4 Finalize `docs/`: 設計稿 entry, component-showcase link, and the frontend developer guide + sidebar

## 6. Traceability + final gates

- [ ] 6.1 Read `docs/development/spec-test-traceability.md`; obtain canonical IDs with `python -m tools.spec_traceability list`; apply `covers_requirement` to the Python-annotatable tests that establish each `webclient-vue-application` and `webclient-component-showcase` requirement (Playwright browser tests + a top-level/CI contract test for the offline build, no-remote-request, self-hosted fonts, and the Storybook/component-coverage gate + its before-wiring ordering)
- [ ] 6.2 Run `tools.spec_traceability check` (and `verify --evidence` with the combined evidence at handoff) to confirm no uncovered main requirement
- [ ] 6.3 Final: `openspec validate webclient-vue-migration --strict` then `openspec validate --all --strict`; full Evennia + managed browser + Node + Vitest + Storybook + top-level suites; aggregate Python branch coverage ≥ 80% and exact-root check; Codecov
