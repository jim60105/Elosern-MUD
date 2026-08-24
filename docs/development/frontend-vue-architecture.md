# Frontend Vue SPA Architecture (shared cross-change context)

**Owner change:** A2 (`webclient-vue-01-foundation`) authored this document.
**Precedence:** this document is shared context only — the change-specific
`openspec/changes/webclient-vue-NN-*/design.md` files, the
[roadmap](../superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md),
`2026-08-02-webclient-ui-design.md`, and the
engine design doc (`2026-07-29-ai-mud-engine-design.md`) all outrank it.
**Linked from:** `docs/_sidebar.md` at D1.

This is the single shared context for the twelve Vue-migration changes, so a
change's focused design never duplicates it.

## Context: the current-state constraints the migration must preserve

The Elosern web client is served from the Django/Evennia template pair
`web/templates/webclient/{base.html, webclient.html}`. After the Vue
migration (C4 flip, finalized by D1), `base.html` loads the Evennia-provided
`evennia.js` WebSocket transport and the Vite-built Vue 3 SPA bundle
(`web/static/webclient/app/dist/index.js`), the dependency-free vanilla text
console (`js/text_console.js`, the D10 offline fallback), and the `$(document).ready`
shim (`js/jquery_ready_shim.js`, supplying the single jQuery surface evennia.js
needs at bootstrap). The retired legacy jQuery/GoldenLayout view files and their
dead CSS were deleted at D1. The preserved DOM-independent logic lives in
`web/static/webclient/js/elosern/*` (protocol reducer, keyboard router,
narrative markup pipeline, command echo, local-map model, choice-point/option-card
logic, art focus); the Vue app re-exposes it through `webclient-app/lib/*` ESM
wrappers via Vite's CommonJS interop. The Vue `AppShell` mounts into `#main-sub`;
`#messagewindow` remains the degraded text fallback.

- **Offline invariant:** the page makes no remote request for a runtime UI
  dependency. Every runtime asset is served from the project origin.
- **DOM-independent logic is the source of truth.** The `js/elosern/*` UMD
  modules enforce the exact OOB contract (mirroring
  `web/webclient/presentation/protocol.py`) and are covered by a
  dependency-free `node --test web/static/webclient/js/tests/*.test.js` gate.
- **Transport is Evennia's** (`evennia.js`): authenticated WebSocket puppet,
  OOB snapshots/updates, allowlisted action dispatch, one-mutation-in-flight,
  version/epoch/revision ordering, reconnect and lock-on-disconnect
  semantics.
- **Browser harness:** Playwright tests boot an isolated managed Evennia
  runtime (temp SQLite, dynamic loopback ports, deterministic fixtures,
  localhost-only requests).
- **Quality gate:** `quality-gate.yml` runs the Node gate, strict OpenSpec
  validation, the frontend gates (A2+), and sharded Evennia + managed browser
  + top-level suites under coverage. The aggregate 80% branch gate is
  **Python-scoped** (`commands|server|typeclasses|web|world`); JS is not
  measured by it.
- **Telnet parity** and **0 released users** (no back-compat, no migrations).

The validated single-screen design draft (the 設計稿) lands in `docs/design/`
at A1 and defines the target IA, the contextual mode visibility matrix, the
ink-night/seal-red design system, the component surfaces, and the self-hosted
fonts.

## Decisions (D1–D10, lifted from the original proposal; A2 outcomes noted)

### D1 — Framework: Vue 3 (SFC) + Vite
Vue 3 single-file components, built by Vite 6.x, ES modules. Dev via
`npm run dev`; production via `npm run build`. Chosen over React (second
ecosystem, weaker Storybook fit for this design-first flow), over a no-build
global Vue (no SFC/HMR), and over staying on jQuery (cannot deliver
component-first, previewable UI). GoldenLayout's tab/panel model is replaced
by the component tree.

### D2 — Reuse the logic via CJS interop; never edit it
The `js/elosern` UMD modules are imported by the Vite bundle through the
`web/webclient-app/lib/*` ES wrappers (Vite/esbuild CommonJS interop); the
sources and the dependency-free Node gate are untouched. Caveat: CJS interop
does **not** set the `window.Elosern.*` browser globals — that is C2's
browser-bridge job (D9). **A2 outcome:** the interop is proven by the Vite
production build (the `dist/index.js` check in
`tests/test_frontend_toolchain_contract.py` asserts the bundle carries the
preserved reducer) and by the Vitest wrapper tests.

### D3 — Pinia store as the single writer of view state
A Pinia 3 store is the sole writer of client view state; it wires the
preserved protocol reducer in as its core, receives transport events
(OOB snapshot/update, result, protocol-error), and dispatches actions through
the transport. Components are passive consumers that emit user-intent events
only.

### D4 — Offline self-contained bundle, stable output names
Vite emits **stable, non-hashed entry names** (`webclient/app/dist/index.js`
+ `index.css`, plus a hashed `assets/` dir) into the existing static tree;
`base.html` references them via `{% static %}`. `dist/` is **not committed**
and is built in **every environment that serves the client**: the CI
`frontend` job, the CI browser workspaces (both two-process checkouts), and
the Containerfile `vue-dist` Node build stage (entrypoint runs
`evennia collectstatic --noinput` after, refreshing the persistent static
volume). The built base is `/static/webclient/app/dist/` so in-bundle font
URLs resolve from the origin. **A2 outcome:** the mutually-exclusive
XOR load flag (`webclient_vue_enabled` context value; production default
legacy, `?__vue=1` review fixture) loads exactly one view stack per page; the
production flip is C4 (C3 uses the flag in a test config only). The
`?__vue=1` opt-in is deliberately unauthenticated: this is a private,
single-player, unreleased deployment and the fixture exists only for the
offline-load browser check and manual review (review-accepted); it is removed
together with the flag at the C4 flip.

### D5 — Preserve the DOM contract hooks; `data-testid` elsewhere
The Vue app keeps the identifiers the OOB and browser contracts already
depend on (the focusable `#action-dock`, the `action-`/`target-` item keys,
the combat-row id pattern, the required panel surface ids); every other
surface exposes a stable `data-testid`. This keeps the existing Playwright
slices and their traceability tests working until C4 re-maps the rest.

### D6 — Design system extracted from the 設計稿
The tokens live in `web/webclient-app/styles/tokens.css` (ink-night palette,
single seal-red accent, gold focus, typography ramps, spacing, motion) and
the subsetted self-hosted `.woff2` faces (Iansui / Noto Serif TC /
Noto Sans TC unicode-range slices) in `web/webclient-app/fonts/`.
`prefers-reduced-motion` and not-color-only status markers are enforced at
the token/utility level (`.status-marker--*`) so they stay testable.

### D7 — Testing strategy: four gates
- **Node gate (unchanged, logic):** `node --test
  web/static/webclient/js/tests/*.test.js`, dependency-free.
- **Vitest (components):** `npm test` — mounted SFC component tests under
  `web/webclient-app/` (jsdom, offline).
- **Storybook gate:** `npm run build-storybook` + the component-coverage
  check (`npm run showcase-coverage`) against
  `web/webclient-app/component-manifest.json` (seeded B1, frozen B5).
- **Playwright (integration):** the managed-runtime browser suite.
The Python 80% coverage gate is unaffected (JS is not in the Python source
roots).

### D8 — Repository layout
Vue sources live in `web/webclient-app/` (SFCs, future `stores/`, `lib/`
wrappers, `styles/`, `fonts/`, Vitest tests, `stories/`, the component
manifest), with Vite output to `web/static/webclient/app/dist/` (gitignored).
`package.json`/`vite.config.js`/`vitest.config.js`/`.storybook/` live at the
repo root; the root package stays CommonJS so the Node gate keeps running
under Node's `.js = CJS` semantics — the app directory is ESM through
`web/webclient-app/package.json`. The 設計稿 is committed under `docs/design/`
(A1).

### D9 — Preserve the public contract via a browser-bridge
The Vue app keeps the same stable public contract surface:
`window.Elosern.Protocol` / `.KeyboardRouter` are the imported UMD modules;
`window.Elosern.narrativeInput` is the narrative/choice-point append path;
`window.Elosern.actions.submit` is the single action-dispatch entry. The
Phase-0 contract audit (A1) freezes the exact façade surface and the
`MODIFIED`/`RENAMED` delta set that C2 applies.

### D10 — Dependency-free vanilla text fallback
A small vanilla-JS text console
(`web/static/webclient/js/text_console.js`, UMD, Node-gated) is bound
directly to the `evennia.js` transport, independent of Vue and jQuery: the
authoritative text path, hidden once the app mounts, active again on bundle
failure / incompatible OOB. **A2 spike outcome:** `evennia.js` is
jQuery-free on every transport path **except its final load-time bootstrap
call `$(document).ready(...)`** — the Vue branch therefore loads the 30-line
`web/static/webclient/js/jquery_ready_shim.js` (scoped to that single
surface, never alongside full jQuery) instead of keeping jQuery. The console
also **renders transport `text` lines as plain text**
(`textContent`, never `innerHTML`) so game payload is treated as data, not
markup; rich ANSI/Evennia-markup rendering lands with the shell wave through
the allowlisted `NarrativeMarkup` pipeline (review remediation: no
server-originated content may be injected as HTML before that pipeline is
in the Vue path). The Vue branch opens the socket itself — the stock
bootstrap only calls `Evennia.init()` (deferred 500 ms) and the legacy GUI
shell is the component that normally calls `Evennia.connect()`, so
`base.html` runs the idempotent `init()` synchronously, binds the console
listeners, then `connect()`.

## Risks / trade-offs

- **npm toolchain in a Python-first repo** → dev/CI-time only; root package
  keeps zero runtime npm dependencies (contract-tested); the Node gate stays
  dependency-free; every npm step is an explicit, non-suppressed CI step.
- **Browser-test churn on the shell swap** → D5 hooks + D9 bridge + the A1
  audit freeze the delta set; behavioral slices are re-mapped at C4.
- **Transport wiring bugs (epoch/revision/reconnect/lock)** → C1 reuses the
  Node-tested reducer as the store core; C3/C4 re-run the existing
  Playwright acceptance.
- **`dist/` 404 in a serving environment** → built in the CI front job, both
  browser workspaces, and the container `vue-dist` stage; a managed-browser
  check (A2) proves the bundle + styles + fonts load from the origin with all
  non-local requests blocked.
- **Two DOM managers during the switch** → the XOR flag (never both), single
  legacy default, deleted at D1.
- **Stable non-hashed entry names** → Evennia's own `/static` serving needs
  nothing special; if the deployment is later put behind a reverse proxy that
  long-caches `/static`, set `no-cache` (or a short TTL) for
  `app/dist/index.js` / `index.css`, or add a build-version query string —
  revisit at C4 (production flip).
- **Stale hashed assets in the persistent `.static` volume** → the entrypoint
  `collectstatic` (without `--clear`) leaves superseded `assets/*` behind;
  harmless (entries reference the current hashes). Do not add `--clear`
  without confirming multi-replica behavior first.

## Store-slice contract (pinned for C1 ∥ Wave B)

Wave B builds offline components against this shape; C1 implements it, so
both must target the same surface:

- **One Pinia store owns the view state** (`web/webclient-app/stores/`). Its
  core is the imported protocol reducer (`lib/protocol.js` — never a second,
  hand-rolled reducer) and the imported keyboard router for focus state.
- **Atomic publish, committed-only reads:** the store publishes a new
  immutable state snapshot only after a full reducer transaction; components
  never read in-flight state. Every OOB message (snapshot/update/result/
  protocol-error) is applied by the reducer first; the publish is the only
  moment observers may see it.
- **View slices:** components read narrow derived slices (e.g. the
  `context_actions` panel, the narrative log, the transport lock state) from
  the store's public getters; they emit user-intent events (action
  submissions, text input) and the store routes them through the single
  dispatch entry — dispatch-only, one mutation in flight.
- **Events in, intents out:** the store subscribes to the transport event
  channel (C3 binds it); components never subscribe to the transport.
- Storybook stories for B-wave components receive the slice as a plain
  fixture object (the same shape the store's getters will return) so the
  offline stories and the live views cannot drift.

## Cross-change mechanics (roadmap summary)

- ~1-workday changes, each independently green, landed in topological order;
  **merge + archive are strictly topological** (never two writers on a hot
  file, never two archives of one capability at once).
- `webclient-vue-application` and `webclient-component-showcase` are ADDED
  (as brand-new capabilities) in B1 and MODIFIED by later changes.
- The component-coverage manifest grows: B1 seeds, B2–B4 extend, B5 freezes.
- Truthful data scope: no component may present data with no backing OOB
  read model (allowlist) or text stream; the deferred surfaces (party panel,
  intimate status, full inventory, event-log toasts) are asserted **absent**
  at B5.
