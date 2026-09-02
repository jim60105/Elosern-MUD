## Context

The keyboard router's frames freeze menu copies at open time and the store's rebuild gate only signatures the root items, so open submenus never refresh (full root-cause analysis in `docs/superpowers/specs/2026-09-02-declarative-frame-refresh-design.md` §2). The approved fix (design doc D1) is declarative frames: a frame stores only `{descriptor, focusKey}` and content is derived from committed panels at access time. This change lands only the derivation side — the store's resolver registry — while the router and push sites keep working on copies until the dependent change flips them.

Existing assets reused verbatim as resolver backends: `exploration_menu.js` (`rootItems`, exit/look/interact/wait/target/keyword builders). The committed-state single source is the protocol reducer's state as surfaced through `publishView()`/`buildView()`. The services, combat, and creation families join the table in the later cutover changes that migrate their push sites, keeping each wave one engineer-day.

## Goals / Non-Goals

**Goals:**

- One registry, keyed by descriptor source, returning menus derived from committed state at call time.
- Pure functional contract: no resolver mutates store or model state except the deliberate `CombatMenu.rebuildForPanel` selection-preservation path, which owns its state in the combat model.
- Shared unresolvable marker so degradation rules live in one place (the dependent change decides pop-versus-disabled rendering).
- Testable without a browser: resolvers are plain functions over a committed-state object.

- Any change to `keyboard_router.js`, the push sites, the copy-based frame lifecycle, or component bindings (dependent changes).
- The services/combat/creation resolver families beyond reserving their table rows in the spec text (the cutover slices add them with their own waves).
- Surfacing action-result messages (`webclient-action-result-feedback`).
- Protocol/server changes.

## Decisions

**D-A: Registry lives behind a store-injected deps object, not a standalone UMD.** Resolvers need committed panels and (in later waves) the combat model and service quantity-form context — all store-owned. A `createFrameResolver(deps)` factory exported from a sibling module `stores/frame-resolvers.js` keeps the store file growth bounded and lets Vitest mount resolvers against synthetic committed state. Alternative (registry inside `keyboard_router.js`) rejected: the router must stay DOM-independent and copy-free of panel knowledge; injection direction is store → router.

**D-B: Descriptor vocabulary is the spec's finite table.** `resolve(descriptor)` on a source absent from the implemented table is reported as unresolvable rather than crashing consumers. This change implements the exploration family only (8 sources, identity params for target/keyword); the spec names the reserved services/combat/creation rows and their params (`questIndex`, `categoryIndex`/`groupIndex`/`skillKey`, `{view}`, `{kind, presetKey?}`) so the later waves are spec-visible additions, not silent expansion. Alternative (all families now) rejected against the one-day budget: each family's builder seam and fixtures differ enough that bundling them reproduces the cutover-size risk this split exists to avoid.

**D-C: The unresolvable marker is data, not an exception.** `{unresolvable: true, reason: string | null}` with `reason` preferring the server-authored panel `reason.message`; the registry catches resolver throws and converts them to the same marker (design doc §5.3 exception protection). Consumers (change 2) pop or render disabled. Alternative (throwing) rejected: every render/navigation call site would need try/catch, re-creating scattered special-casing.

**D-D: This change ships the registry unused by the shipped dock path, with direct Vitest coverage of every implemented source.** Landing the derivation seam first keeps the cutover a pure replacement (copies → resolve calls, delete refresh machinery) instead of one giant mixed commit. No backward-compat layering is needed: the project is unreleased, and the registry's consumers arrive in the next changes.

## Risks / Trade-offs

- [Registry and copy path coexist briefly and can drift] → Coexistence window spans the cutover slices that delete the copy path surface by surface. Vitest pins resolver output against real panel fixtures (reuse `stories/fixtures.js` shapes) so drift surfaces as a red test.
- [Suggestions `unavailable` semantics split between registry (marker) and surface (no root entry)] → Intentional: the registry reports "nothing to render"; the stack rule owns leaving the frame, and the options-surface no-pane contract stays untouched. A Vitest pins `unavailable` → marker and `generating` → muted row.
- [Descriptor params drift from panel payloads (identity encoding)] → Params carry the same server-authored identifiers the rows already carry (`identity`); a resolver receiving a well-formed but unknown identity returns the unresolvable marker, which is exactly the degradation path.

## Migration Plan

Additive module plus store wiring; rollback is reverting the commit — nothing consumes it yet beyond the new tests. No data, no protocol, no server surface.

## Open Questions

None blocking. (`exploration.suggestions` resolves through the same suggestions builder the current in-place replacement uses; when change 2 deletes `replaceSuggestionsFrameInPlace`, the suggestions frame keeps its four-status rendering contract from `webclient-options-surface` unchanged.)
