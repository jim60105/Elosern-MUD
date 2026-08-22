# Vue SPA WebClient Migration — Roadmap

**Date:** 2026-08-19
**Status:** Approved
**Scope:** View-layer migration of the Elosern browser WebClient from a jQuery + GoldenLayout 1.x
shell to a Vue 3 SPA (Vite + Pinia) on top of the existing Evennia transport.

This is a **roadmap / intent document**, not an implementation spec. It is the authoritative record
of the *why*, the *delivery order*, and the *cross-change mechanics* that keep the twelve sub-changes
coherent. The fine-grained requirements for each slice live in that slice's OpenSpec change.

This document supersedes the single `webclient-vue-migration` OpenSpec change, which no longer fits
one reviewable unit and is split into the delivery-waved sequence below.

---

## 1. Intent

The browser WebClient is today a hand-rolled jQuery + GoldenLayout 1.x shell: about 30 imperative
`<script>` plugin files that build the entire UI over the Evennia WebSocket transport, plus a bespoke
state reducer and keyboard router. It works, but the UI is hard to evolve, preview, or review, and it
cannot be designed component-by-component. A complete, validated single-screen design (the 設計稿,
the Elosern design draft) now exists, and building to it as yet another pile of jQuery DOM code would
not scale.

The intent is to migrate the **view layer** to a Vue 3 SPA — a Vite bundle and a reactive Pinia store —
on top of the *existing* Evennia transport and the *existing* DOM-independent logic modules, so the
deterministic game, Telnet parity, offline behavior, and every protocol contract stay intact while the
UI becomes a maintained, previewable, component-testable codebase.

Because one large change cannot be reviewed or rolled back safely, the migration is broken into a
dependency-waved sequence of ~1-workday changes, each independently green. This document owns the order
and the rules that make twelve independent changes behave like one migration.

---

## 2. Goals and Non-Goals

**Goals**
- Migrate the view layer to Vue 3 (SFC) + Vite + Pinia while keeping the deterministic game, Telnet
  parity, offline behavior, and every OOB/transport/dispatch contract identical.
- Reuse, not rewrite, the DOM-independent logic (`js/elosern/*`) and its dependency-free Node gate;
  the app imports them through Vite's CommonJS interop.
- Design and build the **entire** component set in a Storybook before any live wiring.
- Land the 設計稿 as a committed, linked design reference in `docs/`.
- Add the frontend build / test / Storybook gates to CI without weakening any existing gate; the
  aggregate branch-coverage gate stays Python-scoped.
- Keep the whole delivery reviewable: each change ≈ 1 workday, independently green, landed in topological
  order.

**Non-Goals**
- No change to the server, the OOB protocol shape, the action dispatch / allowlist, or the presentation
  read models. The Vue app consumes them as-is.
- No mobile or tablet support. Desktop only: 1440×900 and a 1280×720 minimum.
- No runtime CDN dependency and no runtime npm dependency; the built page is served entirely from the
  project origin.
- No data migration or back-compat (0 released users).
- No competing second client; Telnet stays fully playable and the browser remains the first-class
  graphical client.
- No inventing data for UI-only surfaces that have no backing OOB read model today (see §7).

---

## 3. Source of Truth and Precedence

The source-of-truth chain, highest precedence first:

1. `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` — the architectural source of truth
   (per AGENTS.md).
2. `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` — the WebClient suite's source of truth,
   including its §13 Delivery Roadmap convention and §7 player-facing surfaces.
3. **This roadmap** — authoritative for the Vue-migration intent, delivery order, and cross-change
   mechanics; supersedes the single `webclient-vue-migration` change.
4. Each `webclient-vue-NN-*` change — the implementation contract for its own slice.

On conflict, the higher document wins. This roadmap may amend the two source docs **only** for the single
documented implementation change below; it may not weaken any invariant of the engine design doc. A
sub-change that conflicts with this roadmap is amended to conform (see §9).

**Implementation-intent amendment (applied formally by `webclient-vue-11-finalize`):** engine design
**D13** keeps "the browser is the first-class graphical client and Telnet remains fully playable as
text," but its *implementation* moves from the GoldenLayout shell to a Vue 3 SPA on the same Evennia
extension points. This roadmap states the intent now; `webclient-vue-11-finalize` writes it back into the
engine design doc's webclient row and into `webclient-ui-design.md`.

---

## 4. Cross-Cutting Mechanics of the Split

These rules bind every sub-change; they are what make twelve independent changes coherent.

- **~1-workday sizing.** Each change is one reviewable unit that lands with its own CI green (its gates
  plus a focused test slice). A change that cannot be verified in ~1 workday is split, not stretched.
- **Sequential archive, ADDED-once.** The two new capabilities `webclient-vue-application` and
  `webclient-component-showcase` are `ADDED` (as brand-new capabilities) in the first change that
  establishes each requirement, and `MODIFIED` by later changes. Because archive is topological (§6.4),
  each archive is *true-at-archive*: a capability's main spec under `openspec/specs/` reflects exactly
  the requirements established by every archived change so far, so `openspec validate --strict` and
  traceability stay green after every archive.
- **Component-coverage manifest grows.** The "required component set" is enforced by a code manifest,
  not hardcoded in a single spec. B1 seeds it with the core families; B2–B4 extend it; B5 freezes it to
  the complete set. The `webclient-component-showcase` spec's explicit list is `MODIFIED` in lockstep at
  each archive. The "showcase is complete before wiring" gate is satisfied at B5, before any C-change.
- **Truthful data scope.** No component may present data with no backing OOB read model (allowlist) or
  text stream. UI-only surfaces in the 設計稿 that lack a backing model are deferred (§7); a component
  is never mocked to look real.
- **Reuse, don't rewrite.** The preserved `js/elosern/*` logic and its dependency-free `node --test`
  gate are untouched; the app re-exposes the stable public façades and preserves the DOM contract hooks
  (or re-maps the rest to `data-testid`).

---

## 5. Delivery Roadmap

| Order | OpenSpec change | Depends on | Delivers | Status |
|---|---|---|---|---|
| A1 | `webclient-vue-00-audit-and-design-docs` | — | Phase-0 contract audit: the frozen public-façade surface + the complete `MODIFIED`/`RENAMED` delta list, committed as a deliverable (applied later by C2, not here); the 設計稿 copied into `docs/design/` + a `docs/_sidebar.md` entry + a render/offline check | Done |
| A2 | `webclient-vue-01-foundation` | — (∥ A1) | transport-bootstrap spike (text round-trips without jQuery); `package.json` + lock / `vite.config` / `vitest` / `.storybook`; `lib/*` ESM wrappers over the preserved pure logic; the dependency-free vanilla text console (D10) + the `base.html` XOR-flag infrastructure; the npm / build / Vitest / Storybook component-coverage / `dist` CI gates; the `dist` build in the browser test workspaces + a Containerfile Node build stage; a minimal Vue root component (build stub; the real `AppShell` lands in B1); the shared `frontend-vue-architecture.md` and `frontend-developer-guide.md` reference docs (linked in D1) | Done |
| B1 | `webclient-vue-02-showcase-core` | A2 | the `webclient-component-showcase` capability (required-set via a code manifest + the before-wiring CI gate + offline deterministic stories); the component-coverage manifest, seeded with the core families; root/layout + narrative components: `AppShell`, `TopBar`/`Header`, `ConnectOverlay`, `NarrativeFeed`, `UnreadIndicator`, `CommandDrawer` | Done |
| B2 | `webclient-vue-03-showcase-action` | B1 | the action-dock family: `ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`, `ChoicePointBlock`; extend the manifest | Done |
| B3 | `webclient-vue-04-showcase-data` | B2 | `StatusPanel`, `CharacterPanel`, `SkillBook` (disguise display-only vs true traits); extend the manifest | Done |
| B4 | `webclient-vue-05-showcase-world` | B3 | `LocalMap`, `ArtPanel` (truthful placeholder), and the `services`-backed `ShopPanel`/`QuestBoard`/`LoreDrawer`/`InventoryPanel` (equipped only); extend the manifest | Planned |
| B5 | `webclient-vue-06-showcase-overlays` | B2, B3, B4 | the full overlays `MapOverlay`/`SettingsOverlay`/`HelpOverlay`/`CreationOverlay` (adult gate on both age fields); assert the deferred surfaces are **not** built; **freeze the manifest** to the complete required set | Done |
| C1 | `webclient-vue-07-wire-store` | A2 (∥ Wave B) | the Pinia store using the preserved protocol reducer (CJS-interop import) as its core; view slices; atomic publish / committed-only reads; store integration tests (snapshot adoption, old-epoch/revision rejection) | In-progress |
| C2 | `webclient-vue-08-wire-bridge-contracts` | A1, C1 (∥ B5) | the public-contract bridge (`window.Elosern.{Protocol,KeyboardRouter,narrativeInput,actions}`) over the store + imported logic; apply A1's frozen `MODIFIED`/`RENAMED` deltas to the façade-referencing `webclient-*` capabilities and re-point their traceability tests | Planned |
| C3 | `webclient-vue-09-wire-transport-mount` | C2, B5 | bind the store to the `evennia.js` OOB events (snapshot/update/result/protocol-error: reconnect/epoch/lock re-asserted) and the unchanged allowlisted dispatch (dispatch-only, one-mutation-in-flight); bind the B-wave components to the store as the live renderers; prove it in a managed-browser harness (the A2 XOR flag, **test config only** — the production `base.html` default stays legacy); `webclient-vue-application` gains the "degraded text stays playable" requirement | Planned |
| C4 | `webclient-vue-10-wire-views-browser` | C3 | the single atomic production flip: `base.html` default → the Vite bundle + remove the jQuery/GoldenLayout/plugin loads; mount the app as the live client; `webclient-desktop-shell` RENAMED from the GoldenLayout shell to the Vue SPA **desktop** shell; re-map the **production** Playwright behavioral slices to the preserved hooks + `data-testid`; offline/behavior regression (bundle blocked → text playable; incompatible OOB → graphical locked with text round-tripping) | Planned |
| D1 | `webclient-vue-11-finalize` | C4 | delete retired legacy view files + dead CSS; `AGENTS.md` frontend commands + the Python-vs-npm split; apply the D13/webclient amendment to the engine design doc + `webclient-ui-design.md`; finalize `docs/` links; traceability + all gates (Python branch ≥ 80%) | Planned |

Within Wave B the **Depends on** column encodes the mandatory *landing* order, not a data dependency
between the independent component families: the shared component-coverage `manifest` and the
`webclient-component-showcase` spec are a single coordination point, so B2→B3→B4→B5 must land in order
(§6.3) even though, e.g., `StatusPanel` has no data dependency on the action-dock family.

**Waves**
- **Wave A** — up-front, no frontend build. A1 (contract audit + design draft in `docs/`) and A2
  (toolchain + build pipeline) establish the frozen contract list, the 設計稿, and the npm/Storybook/`dist`
  machinery. A1 ∥ A2 (§6).
- **Wave B** — offline component showcase, before wiring. B1→B2→B3→B4→B5 build the whole component set
  in Storybook with deterministic offline data and no live transport. **Wave B is a serial chain**, not
  parallel (§6.3).
- **Wave C** — wire. C1 (store; parallel-safe with Wave B) → C2 (bridge + contracts) → C3 (transport +
  mount) → C4 (views + Playwright).
- **Wave D** — finalize. D1 removes legacy, amends the source docs, and runs the final gates.

**Critical path:** `A1/A2 → B1 → B2 → B3 → B4 → B5 → C2 → C3 → C4 → D1`. C1 runs under Wave B and does
not extend the critical path unless the store work itself slips; C2 may overlap B5 (§6.2) for the same
reason.

---

## 6. Parallelism and File Ownership

Logical independence is not the same as file-level independence. A "parallel" change must not double-write
a shared file; the map below assigns each hot file to exactly one author per phase, and the global rule
in §6.4 is what keeps the archive from corrupting the shared specs.

### 6.1 Shared-file ownership

A non-owner that needs to edit a row's file is a **forced serialize**, not a merge.

| Hot file | Author (writes it) | Rule for all others |
|---|---|---|
| `package.json` / lock, `vite.config`, `vitest.config`, `.storybook/` | **A2** | B*/C* add source and test files only; a needed config edit serializes behind A2 |
| `web/webclient-app/lib/*` (ESM wrappers over the preserved pure logic) | **A2** | B*/C* are consumers; a wrapper tweak serializes |
| `web/webclient-app/components/**` + `stories/**` | the B-change that owns that family | distinct per family (core / action / data / world / overlays) |
| component-coverage `manifest` | B1 seeds → B2→B3→B4 extend → B5 freezes | this is the Wave B serial bottleneck |
| `openspec` main spec for `webclient-component-showcase` | B1 ADDED → B2–B5 MODIFIED (at archive) | serial |
| `web/templates/webclient/base.html` | **A2** (XOR-flag infra + vanilla console) → **C4** (flip-to-Vue + remove legacy loads) | B* / C1 / C2 do not touch it; C3 only uses the flag in a test config |
| `web/templates/webclient/webclient.html` | **C4** (single live mount) | A2's build stub renders in Storybook only; C3 mounts in the test harness |
| `.github/workflows/quality-gate.yml` | **A2** (npm/build/Vitest/Storybook/`dist` gates) | B1 only completes the manifest; no workflow edit |
| `Containerfile` / `docker-entrypoint.sh` | **A2** | — |
| `docs/design/` (the 設計稿) + `docs/_sidebar.md` (its entry) | **A1** → **D1** (finalize links) | A2 writes `docs/development/` files but **not** the sidebar |
| `docs/development/frontend-vue-architecture.md`, `frontend-developer-guide.md` | **A2** (standalone, unlinked) → **D1** (link + finalize) | — |
| engine design doc webclient row, `webclient-ui-design.md`, `AGENTS.md` | **D1** | — |
| `openspec/specs/<capability>/spec.md` (main specs) | applied only at a change's archive, in topological order | never two archives of the same capability at once |

### 6.2 Safe parallel lanes

- **A1 ∥ A2** — safe because A1 owns `docs/design/` + its one sidebar entry and A2 owns toolchain / code
  plus standalone `docs/development/` files (no sidebar). No shared file; A2 documents the toolchain it
  itself creates, so the frontend guide is knowledge-correct.
- **C1 ∥ Wave B** — the one real overlap. C1 writes `stores/` + its own store tests; B writes
  `components/` / `stories/` + its own tests. Safe *iff* A2 already froze `vite`/`vitest`/`package.json`
  and the `lib/*` wrappers, so B and C1 are consumers only. The store-slice contract is pinned in A2's
  `frontend-vue-architecture.md` so both sides target the same shape.
- **C2 ∥ B5 (optional)** — C2's bridge is over the store + pure logic, not the components, so it is
  file-independent of the B tail and may overlap B5 to shorten the path. It still lands before C3.

### 6.3 Serial bottlenecks

- **Wave B is a chain**, not parallel: the component-coverage `manifest` (one growing code file) and the
  `webclient-component-showcase` spec list (one `MODIFIED` chain), plus the shared Storybook registry and
  shared story-util helpers, are a single coordination point. B1→B2→B3→B4→B5 land in order. Within a
  single change, the components are distinct files, so contributors can parallelize *inside* a change —
  but the changes land in order.
- `base.html` (A2 → C4) and `package.json`/`vite`/`vitest` (A2 only) are single-owner.

### 6.4 Global rule

Coding may overlap as in §6.2, but **merge + archive are strictly topological**: never two writers on a
hot file, and never two archives of the same `openspec/specs/<capability>/spec.md`, at once. Every
"parallel" in this document overlaps *coding*, never *landing*.

---

## 7. Surfaces: OOB-Backed vs Deferred

The app surfaces exactly what the current OOB panel allowlist (art, status, context_actions, local_map,
services, creation, exploration, character) and the text stream deliver. The per-surface mapping is
`webclient-ui-design.md` §7 plus the "Delivers" column in §5.

**Deferred** — separate OOB changes, not built in this migration because they have no backing read model
in the current allowlist:
- a dedicated Party / companion data panel (bond, affinity, follow);
- the intimate / adult status collapsible (the current status/character OOB payload has no such fields);
- a full inventory bag (only equipped items are modeled today);
- the event-log Toasts surface (no `event-log` panel in the allowlist today).

B5 asserts these surfaces are **absent** rather than mocked. Each deferred surface gets its own OpenSpec
change when its OOB read model lands; that change will `MODIFIED` the component-showcase manifest to add
it.

---

## 8. Risks and Trade-offs

- **npm toolchain in a Python-first repo** → dev/CI-time npm only; the Node gate stays dependency-free;
  explicit CI steps; `AGENTS.md` documents the Python-vs-npm split.
- **Browser-test churn on the shell swap** → roughly 28 Playwright tests assert the current DOM *and* the
  `window.Elosern.*` façades / keyboard contract; preserved via the bridge (C2) + the DOM contract hooks,
  the rest re-mapped to `data-testid` (C4); the Phase-0 audit (A1) freezes the exact delta set.
- **Two-writer / merge conflict** → the §6.1 ownership map + topological landing (§6.4). This is exactly
  why Wave B is a chain, why A2 does not touch the docs sidebar, and why a non-owner edit forces a
  serialize rather than a merge.
- **`dist/` 404 in a serving environment** → the `dist` is built in the browser test workspaces and the
  container image (A2); CI gates on it; a browser check blocks non-local requests and asserts the bundle
  loads from the origin.
- **Transport wiring bugs (epoch / revision / reconnect / lock)** → the store reuses the tested reducer;
  covered by store integration tests (C1) and the existing Playwright acceptance (C3 / C4).
- **Invented / speculative data** → truthful-data scope (§7); B5 asserts the deferred surfaces are absent.
- **Roadmap ↔ twelve-changes drift** → the roadmap owns order + mechanics only; each change owns its
  fine-grained spec, so a task resize does not edit this doc. The one drift that matters — reordering —
  is gated by §9.

---

## 9. Governance

- **The Status column is the tracker.** Flip each row `Planned → In-progress → Done` as it lands. `Done`
  only after `openspec validate <change> --strict` passes and the change's own CI gates + focused test
  slice are green. This column is the single dependency-order view.
- **Every sub-change must cite this roadmap** in its `proposal.md` and adopt the "Depends on" column as
  its binding prerequisite. A sub-change may not start before its dependencies are `Done`.
- **Original change:** `webclient-vue-migration` is **superseded**. It is **deleted** (not archived) when
  A1 lands, so no second owner exists for these specs during the migration. Its content is redistributed
  into A1–D1 or the shared architecture reference.
- **Amending this roadmap.** A delivery-order or mechanic change is made by editing this document (a
  visible, reviewed change) and is the only way to re-order sub-changes. A sub-change that resizes its
  own tasks does not edit this document.
- **Precedence.** If a sub-change finds this roadmap wrong, it amends this roadmap (or escalates to a
  source-doc amendment) rather than silently diverging.

---

## 10. Focused Design Documents

Each sub-change's `openspec/changes/webclient-vue-NN-*/design.md` is its focused design and **must be
based on this roadmap** and the two source docs above — mirroring the `webclient-ui-design.md` §14 rule
that a unit's proposal is based on both the suite document and its focused design. There is no separate
per-change document; the OpenSpec change's own proposal / design / tasks / specs are the focused
artifacts.

The shared, cross-change context (the current-state context, the D1–D10 decisions, and the risks) that
lived in the original `webclient-vue-migration/design.md` is lifted into
`docs/development/frontend-vue-architecture.md` (authored in A2, linked in D1) so the twelve focused
designs share one context instead of duplicating it. C1 references that reference doc by path for the
store-slice contract.
