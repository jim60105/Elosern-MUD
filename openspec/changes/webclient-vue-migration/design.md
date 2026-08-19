## Context

The Elosern web client is served from the Django/Evennia template pair `web/templates/webclient/{base.html, webclient.html}`. `base.html` loads a pinned local jQuery 3.2.1, the Evennia-provided `evennia.js` WebSocket transport, the goldenlayout 1.x runtime, and about 30 project `<script>` files: DOM-independent logic in `web/static/webclient/js/elosern/*` (protocol reducer, keyboard router, narrative markup pipeline, command echo, local-map model, choice-point/option-card logic, art focus) and imperative view plugins in `web/static/webclient/js/plugins/*` (`elosern_ui.js`, the per-mode dock plugins, `goldenlayout.js`, `elosern_state.js`, `elosern_actions.js`). GoldenLayout mounts the version-1 shell into `#main-sub`; `#messagewindow` is the degraded text fallback.

Key current-state constraints that the migration must preserve:
- **Offline invariant:** "The page must make no remote request for a runtime UI dependency" (base.html). Every runtime asset is served from the project origin.
- **DOM-independent logic is the source of truth.** The `js/elosern/*` modules enforce the exact OOB contract (mirroring `web/webclient/presentation/protocol.py`) and are covered by a dependency-free `node --test` gate (`web/static/webclient/js/tests/*.test.js`). These are mature and heavily tested.
- **Transport is Evennia's** (`evennia.js`): authenticated WebSocket puppet, OOB snapshots/updates, action dispatch through an allowlisted registry, one-mutation-in-flight, version/epoch/revision ordering, reconnection and lock-on-disconnect semantics.
- **Browser harness:** Playwright tests boot an isolated managed Evennia runtime (temp SQLite, dynamic ports, deterministic fixtures, localhost-only) and assert on real DOM ids/selectors (`#action-dock`, `#combat-row-0`, `action-`/`target-` keys, panel ids).
- **Quality gate:** a single `quality-gate.yml` runs the Node gate, strict OpenSpec validate, static traceability check, then sharded Evennia + managed browser + top-level suites under coverage (aggregate 80% branch gate is **Python-scoped** to `commands|server|typeclasses|web|world`; JS is not measured by it).
- **Telnet parity** and **0 released users** (no back-compat, no data migration needed, per proposal).

A complete, validated single-screen design — the Elosern 設計稿 (`/tmp/opencode/elosern-redesign/index.html`) — already exists and defines the target IA, the contextual mode visibility matrix, the ink-night/seal-red design system, the component surfaces, and self-hosted fonts.

Stakeholders: single-player players (browser), GMs (docs), and the CI quality gate.

## Goals / Non-Goals

**Goals:**
- Migrate the **view layer** to a maintained, previewable, component-testable Vue 3 SPA while keeping the deterministic game, Telnet parity, offline behavior, and every OOB/transport/dispatch contract identical.
- Reuse, not rewrite, the DOM-independent logic (`js/elosern/*` + its Node gate).
- Build and review the **entire component set in a Storybook before wiring** (the design-first phase the change is organized around).
- Land the 設計稿 as the committed design reference in `docs/`.
- Add the frontend build/test/Storybook gates to CI without weakening any existing gate.

**Non-Goals:**
- No change to the server, the OOB protocol shape, the action dispatch/allowlist, or the presentation read models (status/character/context/art/local_map/combat/creation/services). The Vue app consumes them as-is.
- No mobile/tablet or responsive-mobile support (desktop-only, 1440×900 and 1280×720).
- No runtime CDN dependency and no runtime npm dependency.
- No data migration or back-compat (0 users).
- Do not add a competing second client; Telnet stays fully playable and the browser remains the first-class graphical client (design D13, amended implementation).

## Decisions

### D1 — Framework: Vue 3 (SFC) + Vite, not React / not no-build / not more jQuery
**Decision:** Vue 3 single-file components, built by Vite (6.x), with ES modules. Dev via `npm run dev` (Vite HMR); production via `npm run build`.
**Why:** The change is organized around a *component showcase first* (Storybook) and SFCs are the natural unit Vue + Storybook operate on. Vue is chosen over React for SFC ergonomics and the Storybook-Vue-first workflow; over a no-build "global Vue" for real SFCs, HMR, and a self-contained prod bundle; over keeping jQuery for maintainability, preview, and per-component testability. GoldenLayout's tab/panel model is replaced by the component tree (self-identifying surfaces, no tab strip — matching the existing `webclient-desktop-shell` requirement).
**Alternatives considered:** (a) Stay on jQuery + GoldenLayout — rejected: cannot deliver the component-first, previewable target. (b) React — viable but adds a second ecosystem the repo doesn't use and a weaker storybook fit for this design-first flow. (c) Vanilla no-build Vue global build — rejected: no SFC, no HMR, cannot cleanly host a Storybook.

### D2 — Keep Evennia's transport and the DOM-independent logic; add a Pinia store as the single writer
**Decision:** The app keeps `evennia.js` as the socket/transport. The existing `js/elosern/*` UMD modules are imported by the Vite bundle via esbuild CommonJS interop (they set `module.exports = factory()` under `module`, so Vite consumes them and the Node gate is untouched). A **Pinia** store is the sole writer of client view state; it wires the preserved protocol reducer in as its core and receives transport events (OOB snapshot/update, result, protocol-error) then dispatches actions through the transport. Components are passive consumers that emit user-intent events only. **Bridge caveat:** esbuild's CJS interop does *not* set the `window.Elosern.*` browser globals the current `<script>`-load path exposes, so a browser-bridge (D9) re-exposes the stable public façades (`window.Elosern.Protocol`, `.KeyboardRouter`, `.narrativeInput`, `.actions`) backed by the imported modules — the contractual API is unchanged while the DOM becomes Vue.
**Why:** The reducer/keyboard/markup/map logic is battle-tested and Node-tested; reusing it keeps the Node gate and behavioral contracts green and avoids rewrite risk. A single reactive store preserves the "strict and atomic, subscribers see only committed state" invariant now described in `webclient-desktop-shell`.
**Alternatives considered:** (a) Rewrite logic in Vue composition API — rejected: discards mature tested code. (b) Vuex — rejected: Pinia is the Vue 3 standard, ESM-first, and has a simpler store-per-domain shape. (c) Keep jQuery as the DOM layer and layer Vue on top — rejected: two DOM managers.

### D3 — Offline self-contained bundle, stable output names, served from project static
**Decision:** Vite is configured to **emit stable, non-hashed entry names** (e.g. `webclient/app/dist/index.js` and `index.css`, plus a stable hashed assets dir) into the existing static tree, and `base.html` loads them via `{% static "webclient/app/dist/index.js" %}`. The bundle is produced by `npm ci && npm run build` in CI and during the container image build; the `dist/` is **not committed**. No `<script type=module crossorigin>` is required because there is no runtime fetch — everything (JS, CSS, and the self-hosted `.woff2` font files) is bundled or copied locally by the build, so nothing is fetched at runtime.
**Why:** Evennia serves static from the project origin and the Django template cannot reference a per-commit hashed filename without a manifest plugin. Stable names plus a locally-served `dist` keep the template trivial and preserve the no-remote-request invariant. `dist/` stays out of git (a build artifact) and is built in **every environment that serves the client**: the CI preflight step (`npm ci && npm run build`) produces it and a Storybook build, the managed browser workspaces consume that artifact, and the container image builds it in a dedicated Node build stage (with the container entrypoint ordering `collectstatic` after the build and the persistent static volume refreshed). Because the static tree is a persistent volume, the `dist` is published **atomically** — a release-versioned assets directory, or keep-old-assets until a safe window, with the HTML entry served no-cache — so a stale `index.js` never points at a removed chunk (this also covers rollback).
**Alternatives considered:** (a) Commit `dist/` — rejected: build artifacts in git. (b) Vite manifest + a Django template filter to inject hashed names — viable and more "standard", but adds a serve-time dependency for a single-client, version-by-commit codebase; stable names are simpler and equally offline. Chosen: stable names (note manifest option as the upgrade path).

### D4 — Preserve the DOM contract hooks; add `data-testid` everywhere else
**Decision:** The Vue app keeps the identifiers the OOB and browser contract already depend on — the focusable `#action-dock` target the keyboard router dispatches into, the `action-`/`target-` item keys on dock/submenu/choice rows, the combat-row id pattern the art-panel keyboard journey awaits, and the required panel surface ids. Every other interactive surface exposes a stable, unique `data-testid`.
**Why:** This dramatically reduces browser-test churn — the ~28 managed Playwright tests and the specs that assert on these hooks (e.g. `webclient-browser-verification`'s `document.getElementById('action-dock').focus()` and `#combat-row-0`) keep working, and the rest are re-mapped to `data-testid` in lockstep with the component work.

### D5 — Design system extracted from the 設計稿
**Decision:** Extract the 設計稿's CSS into a small design-system layer (CSS custom properties for the ink-night palette + single seal-red accent, typography ramps, spacing, and motion tokens) plus self-hosted font files (display / serif / sans). The Vue app consumes the tokens; `prefers-reduced-motion` and colorblind-safe status encodings are enforced at the token/utility level.
**Why:** The 設計稿 already validates the look; a token layer keeps the Vue app consistent and offline (self-hosted fonts, no remote font fetch), and makes the reduced-motion and not-color-only rules testable rather than ad-hoc.
**Note:** the mockup's `fonts.css` is large (base64-inlined faces); production uses subsetted local `.woff2` files to keep the `dist` lean.

### D6 — Testing strategy: Node gate (unchanged, logic) + Vitest (components) + Storybook gate + Playwright (integration)
**Decision:** Keep `node --test web/static/webclient/js/tests/*.test.js` dependency-free for the DOM-independent logic. Add **Vitest + `@vue/test-utils`** component unit tests (mounted with mock store slices/asserting emitted intents) under `web/webclient-app/`. Add a **Storybook** static build plus a deterministic **component-coverage** check (a required-component list; fails when a required component is unregistered/undocumented). Keep the Playwright managed-runtime browser suite for integration/behavior. All four are mandatory CI steps.
**Why:** Each layer is tested where it belongs; the dependency-free Node gate keeps the "no npm for the logic" rule alive; the Storybook gate enforces the "design every component" mandate; Playwright keeps end-to-end behavior + the offline/localhost rules. The Python 80% coverage gate is unaffected (JS isn't in the Python source roots).

### D7 — Component decomposition (the "divide all the components" plan)
**Decision:** The application surface is divided into the components below. "Data" names the OOB panel / read model the component reads; "Emits" names the action id / inputfunc it produces. Every surface is backed **only** by the current OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration, character) or the transport text stream; the set is completed and documented in Storybook **before** wiring (D6). Surfaces the 設計稿 shows but that have **no backing read model today** are marked *(deferred)* and are separate OOB changes, not built here — the app never invents data.

| Component | Surfaces | Data (OOB panel / read model) | Emits |
| --- | --- | --- | --- |
| `AppShell` | root layout, mode, live regions, reduced-motion | active mode + full store | — |
| `TopBar` `Header` | title, location, world date/time, connection dot | `status` header fields | — |
| `NarrativeFeed` | scrolling narrative, authoritative text surface | narrative log (markup pipeline) | text input → `default` input |
| `UnreadIndicator` | badge + jump button + polite region | unread count | scroll-to-bottom |
| `CommandDrawer` | input line, history, `/` open, send, Escape | (client) | plain text command |
| `ActionDock` + `DockMenu`/`DockMenuItem` | seal-red framed grid, guidance line, focused/disabled cells | `context_actions` v5 + mode menus | `action-` keys → dispatch |
| `OptionCard` / `ChoiceCardRow` | suggestion / choice cards | `context_actions`.suggestions | exact OOB envelopes |
| `ChoicePointBlock` | stream-end block, ready/generating, movable | narrative choicepoint | choice selection |
| `StatusPanel` | gauges (hp/mp/sp), counters (magic_level, guild_merit), static traits, wallet, conditions + derived modifiers | `status` v3 | (read-only) / condition focus |
| *(deferred)* `IntimateStatus` | **adult block** (arousal/wetness/shame/exposure, climax, sensitivity, virgin) — **not in the current status/character OOB payload** | separate OOB change (add fields + adult gate) | — |
| `CharacterPanel` | details, equipment, disguise, guild rank/merit, persona | `character` v3 | (read-only) |
| `SkillBook` | active/passive tabs, categories, search, category>group>skill, detail (cost/target/cast) | `character` v3 actives/passives | `combat.cast`, target/shorthand |
| `LocalMap` | lattice, states, actionable adjacent nodes, legend, detail line, colorblind-safe | `local_map` v1 | `explore.move` |
| `ArtPanel` | 16:9 scene + contextual portrait overlay; truthful placeholder; degraded | `art` panel | (read-only) |
| *(deferred)* `PartyPanel` | dedicated companion data (bond/affinity/follow/跟丟了) — **no `party` panel in the OOB allowlist**; the companion is only visible via `exploration` affordances today | separate OOB change | — |
| `InventoryPanel` | equipped items (full bag *(deferred)* — no OOB inventory today) | `character` `.equipment` (equipped only) | equip/use envelopes |
| `ShopPanel` | stock / buy / sell | `services` (shop host) | `shop.stock/buy/sell` |
| `QuestBoard` | quest list + detail | `services` (guild/quest host) | `guild.*` envelopes |
| `LoreDrawer` | lore entries | `services` (lore host) | (read-only) |
| `MapOverlay` (full) | expanded map, legend/legend-layers | map-knowledge / local_map | `explore.move` |
| `SettingsOverlay` (full) | fonts, type scale, reduced-motion, text-to-html toggle, colorblind | options surface | `options.*` |
| `HelpOverlay` (full) | in-game help / onboarding | onboarding-guide | (read-only) |
| `CreationOverlay` (full) | creation wizard (presets/custom/concept, adult gate, activate) | creation read model | `creation.*` envelopes |
| *(deferred)* `Toasts` | **event-log notices** — **no `event-log` panel in the OOB allowlist today** | separate OOB change | — |
| `ConnectOverlay` | connecting / disconnected / control-lock | transport state | (lock graphical on loss) |

### D8 — Repository layout
**Decision:** New frontend source lives in `web/webclient-app/` (Vue SFCs, `stores/`, `lib/` ESM re-exports of the pure logic, design-system CSS, Vitest tests, Storybook config) with Vite output to `web/static/webclient/app/dist/`. `package.json`/`vite.config.*`/`.storybook/` live at the repo root (Node is already provisioned in CI). The 設計稿 is copied to `docs/design/` (assets included) and linked from `docs/_sidebar.md`.
**Why:** Keeps the Vue app cleanly separated from the legacy static tree during migration (easy to remove legacy once wired), keeps the Node gate on the existing `web/static/webclient/js/elosern/*` path, and colocates the build in the standard npm location.

### D9 — Preserve the public contract via a browser-bridge; settle all implementation-bound contracts in a Phase-0 audit
**Decision:** The Vue app keeps the *same* stable public contract surface the current client exposes, implemented as browser-bridge shims over the imported logic and the store: `window.Elosern.Protocol` and `window.Elosern.KeyboardRouter` are the imported UMD modules; `window.Elosern.narrativeInput` is the Vue narrative/choice-point append path (owned by the store, no second append path); `window.Elosern.actions.submit` is the single action-dispatch entry. Document key events route through the KeyboardRouter and are **claimed exactly when the router consumes them** (unconsumed keys fall through to the text path). A **Phase-0 contract audit** enumerates every implementation-bound contract across `openspec/specs/webclient-*` and the Playwright suite — public façades, the WebClient-plugin `onKeydown` path, DOM ids, layout-persistence keys, and the input path — and labels each *preserve-via-bridge* or *delta*. Its output freezes the façade-bridge surface and the complete set of `MODIFIED`/`RENAMED` deltas (updating the affected `webclient-*` capabilities and their traceability tests) before implementation.
**Why:** several existing contracts are implementation-bound (they name the `window.Elosern.*` façades, the Evennia plugin `onKeydown` path, and specific DOM ids); the DOM can become Vue only if that public surface is preserved and each implementation-bound requirement is bridged or re-expressed. The audit makes it explicit and governed, and it is what *settles* the change's delta set rather than assuming it.
**Alternatives considered:** (a) assume the behavioral requirements are unchanged and only re-map selectors — rejected: it ignores façade/plugin-bound requirements (action-choicepoints, options-surface, pointer-activation, desktop-shell keyboard routing, narrative-markup, character-creation-ui) and would silently break them; (b) keep the Evennia jQuery plugin system as the DOM — rejected: defeats the migration.

### D10 — A dependency-free vanilla text fallback, independent of Vue and jQuery
**Decision:** a small vanilla-JS text console (input + output) bound directly to the retained `evennia.js` transport is loaded in `base.html` independent of Vue and jQuery. It is the authoritative text path: active until the Vue app mounts successfully (then hidden) and active again if the Vue bundle fails to load or the OOB channel is incompatible, when graphical controls lock and text still round-trips. It does **not** depend on the removed jQuery `default_out`/`history`/`webclient_gui` plugins. A **Phase-0 transport-bootstrap spike** confirms Evennia 6.1's `evennia.js` connects and round-trips text without jQuery; if a thin jQuery dependency turns out load-bearing, keep a minimal local jQuery scoped to that path only and document it.
**Why:** the specs require "text always playable" and "bundle blocked keeps text playable"; the current fallback happens to ride on jQuery plugins this change removes, so the fallback must be re-founded on the transport alone and verified rather than assumed.
**Alternatives considered:** (a) keep the Evennia stock `default_out`/`history` plugins for the fallback — rejected: they are jQuery/GoldenLayout-era and the point is to drop that stack; (b) leave the fallback undefined — rejected: it is a correctness blocker for the offline/playable guarantee.

## Risks / Trade-offs

- **[npm toolchain in a Python-first repo] →** divergence and CI surface: lockfile (`package-lock.json`), dev-time-only npm, Node gate kept dependency-free, frontend build/test/Storybook as explicit CI steps, and an `AGENTS.md` section documenting the Python-vs-npm split and the exact frontend commands.
- **[Browser-test churn on the shell swap] →** ~28 Playwright tests assert current DOM *and* the `window.Elosern.*` façades/keyboard contract: preserve the façades via the bridge (D9) + the DOM contract hooks (D4), re-map the rest to `data-testid` in the same commit that lands each component, and let the Phase-0 audit freeze the exact delta set; run per-surface browser slices incrementally, full suite at the end.
- **[Transport wiring bugs (epoch/revision/reconnect/lock)] →** reuse the existing protocol reducer and its Node tests as the store core; rely on the existing Playwright reconnect/lock acceptance to catch regressions; add store integration tests for snapshot adoption and dispatch-only.
- **[Two DOM managers during transition] →** the legacy load is a *build/test-only* flag with a **mutually-exclusive** script load (never both), single default = Vue, used only for one PR-review window and deleted in the same change once the suite is green — a transient switch, not a compatibility layer (0 users).
- **[Bundle/font weight] →** Vite code-splitting + lazy full overlays + subsetted self-hosted fonts + 16:9 art; keep `dist` out of git.
- **[Coverage-root / gate confusion] →** the aggregate 80% branch gate is Python-scoped; add an explicit note + the JS gates are separate so `tools.verify_coverage_roots` and the aggregate check are unaffected by JS.
- **[Design drift between 設計稿 and Vue] →** the tokens + Storybook are the shared source; each Storybook story links back to its 設計稿 region; a component is "done" only when its story matches the draft and its gate passes.
- **[dist/ 404 — bundle not built in a serving environment] →** the CI browser workspaces and the container image MUST produce the `dist` (preflight artifact + a Containerfile Node build stage); gate CI on the dist build and add a browser check that the Vite bundle loads from the origin with remote requests blocked.
- **[Invented / speculative data] →** the app renders only OOB-allowlist data or the text stream; the design and specs mark every surface by its backing read model, and PartyPanel/IntimateStatus/full-inventory/event-log-toasts are explicitly deferred — a component with no backing data is out of scope, never mocked to look real.

## Migration Plan (0 users, no back-compat)

**Phase 0 — Contract audit + transport spike + build pipeline (before any app code).** (a) Freeze the public-contract bridge (D9 façades) and the full set of `MODIFIED`/`RENAMED` deltas by auditing `openspec/specs/webclient-*` and the Playwright suite; commit the façade surface + delta list. (b) Confirm Evennia 6.1's `evennia.js` connects and round-trips text without jQuery (D10 spike). (c) Stand up the npm gates in CI (preflight `npm ci`/build/vitest/storybook+coverage) and the `dist` build for the browser workspaces + a Containerfile Node build stage (D3). Gate: audit deliverable committed, spike green, build pipeline green.

1. **Phase 1 — Design 設計稿 into docs (no app change).** Copy the validated showcase (HTML + assets, self-hosted fonts) into `docs/design/`, add a `docs/_sidebar.md` entry and a short frontend developer-guide page. Gate: file present, linked, renders (a browser/docs check).
2. **Phase 2 — Toolchain + component showcase (offline, no server).** Add `package.json`/Vite/Pinia/Storybook/Vitest; extract the 設計稿 design tokens + fonts; implement **every** D7 component as an SFC with Storybook stories (props/events/states) + Vitest tests; add the Storybook + component-coverage gate to CI. No WebSocket wiring yet. Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green; Node gate still green.
3. **Phase 3 — Wire to the live transport and replace the shell.** Mount the app into `webclient.html` (`#app`), wire the Pinia store to the `evennia.js` transport + preserved reducer (snapshot adoption, dispatch-only, reconnect/lock), convert legacy `js/plugins/*_dock.js`/`elosern_ui.js` behavior into store-bound components, update `base.html` (remove jQuery/GoldenLayout/plugin `<script>` load; keep `evennia.js`; load the Vite bundle). Preserve D4 DOM hooks; re-map Playwright selectors to `data-testid`. Gate: full Evennia + managed browser + Node + Vitest + Storybook + traceability green; offline/localhost checks hold.
4. **Phase 4 — Remove legacy, finalize docs + amend design doc.** Delete the retired GoldenLayout/jQuery plugin view files and their dead CSS; update `AGENTS.md` (frontend commands), `docs/` (frontend guide, sidebar), and amend the engine design doc D13/webclient row (GoldenLayout shell → Vue SPA on the same extension points). Gate: `openspec validate --all --strict`, static traceability, aggregate coverage ≥ 80% (Python), Codecov.

**Rollback:** because the client is served from `base.html` script wiring, rollback is reverting the template's script load + removing the app `dist`; the server, protocol, and Telnet are never touched, so the game is unaffected at any point.

## Open Questions

- **Container build details (confirm at Phase 0/2):** the exact Containerfile Node build stage + entrypoint ordering so `collectstatic` serves `web/static/webclient/app/dist/`, and that Evennia's static finder discovers that path. (Decided: build in the image; do **not** commit `dist/`.)
- **Exact version pins:** Vue 3.5.x, Vite 6.x, Pinia 3.x, Storybook (vue3 + vite framework) major, Vitest 2/3, `@vue/test-utils` 2.x — to be locked in `package-lock.json` at Phase 2.
- **Vitest vs reusing `node --test` for component tests:** chosen Vitest + `@vue/test-utils`; confirm the CI job shape and how component-test evidence feeds (it is a gate, not part of the Python traceability evidence).
- **Storybook gate weight:** static `build-storybook` in CI (heavier) vs a lightweight component-coverage script only (lighter) — default to the static build for a true "showcase is built" guarantee, downgradable if CI time grows.
- **`web/webclient-app/` vs colocating under `web/static/webclient/`:** chose `web/webclient-app/`; confirm it does not need to be under `web/` for the Python coverage `source` roots (it is JS, not Python, so it is outside the Python coverage source either way).
