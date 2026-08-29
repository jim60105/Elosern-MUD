# Design: render-equipment-breakdown-webclient

## Context

Parent design §11 (Vue paragraph). P6 ships the v5 character payload:
trait rows `{key, label, base, current, max, effective, layers}` plus
equipment `adjustment` strings, with P6's transitional tolerance making
both clients accept 4|5. Vue surfaces: `CharacterStatusDrawer.vue` (stat
rows + intimate section), `EquipmentDoll.vue`, `InventoryPanel.vue`;
fixtures live in `stories/fixtures.js` (character fixture currently
schema_version 4); the frozen required-set manifest
(`component-manifest.json`) drives `npm run showcase-coverage`; Vitest
suite under `tests/`. The legacy client (`protocol.js` + its gate) still
renders totals.

## Goals / Non-Goals

**Goals:**

- Players see WHY each number is what it is, formatted entirely from
  payload data.
- v5 becomes the only accepted character payload version; the transitional
  v4 branch dies.
- All JS gates green: `npm test`, `build-storybook`, `showcase-coverage`.

**Non-Goals:**

- Any Python/payload change (P6 owns them), new components/manifest
  entries, recomputation or re-sorting in JS, command-surface changes.

## Decisions

### D1 — Chips are a pure projection of the payload

`CharacterStatusDrawer` renders, per stat row: the existing value line
(gauge rows keep their `current / max` text exactly as today; layer chips
attach to the maximum, whose decomposed value IS the payload `max`) and
one chip per layer IN PAYLOAD ORDER — ALL layers rendered, wrapping freely
(≤ 16 by payload bound; NO truncation or `+n` collapse concept exists),
source-tinted (skill／狀況／裝備 palette from existing design tokens),
label = layer `name` verbatim, formatted amount by `kind` (`mult` → `×1.2`
with trailing zeros stripped, `flat` → `+4`/`−2`, `pct` → `−10%`/`+15%`,
server amounts re-signed only for display, never recomputed). No sorting,
no grouping arithmetic, no client-side totals. Rows without layers keep
the existing value text and render NO breakdown elements (no chip
containers, no wrappers). Unknown `source`/`kind` values are a
DEFENSE-IN-DEPTH for direct component rendering only: the wire contract
(Python + legacy JS exact validators) still REJECTS unknown enums, and a
component-level Vitest renders an unknown-enum props object directly to
prove the neutral 其他 chip never corrupts the value line — no wire
relaxation anywhere. Accessibility: chips are text-bearing (never
color-alone) per the existing WCAG baseline.

### D2 — Adjustment text renders where equipment is listed

`EquipmentDoll` slot tooltips/rows print the character payload's
`adjustment` string verbatim. `InventoryPanel` equipment rows source the
SAME server-generated string by joining on `item_key` against the
character payload's equipment rows already held in the app store — a
presentation-layer join of two server-formatted sources (registry item ⇒
identical string), never client-side synthesis; an item whose character
row is absent (bag-only item) renders no adjustment. Empty renders nothing.
The v5 Storybook fixture MUST carry a worn bias-bearing item so the
exposure row's stored-base value differs from its effective value; the
component test asserts the effective ordinal AND asserts the base ordinal
is NOT rendered (non-vacuous).

### D3 — v5-only acceptance closes the tolerance window

Vue app validation, legacy `protocol.js` gate, and fixtures accept ONLY
schema version 5; the P6 v4 branches and v4 fixture are deleted (unreleased
project — no compat per AGENTS.md). The legacy client keeps its totals-only
rendering at v5 (long-lived fallback for non-Vue contexts).

### D4 — Showcase coverage stays frozen-manifest-clean

Breakdown states ship as new STORIES on the three existing manifest
components (drawer with full-breadth layers, doll with adjustment-bearing
slots, inventory mixed rows) driven by an updated v5 `characterFixture`
mirroring the Python contract test's fixture values; no new components, so
`showcase-coverage` required-set is untouched.

### D5 — Traceability lands in the shipped evidence-test pattern

Both new main-spec requirements get substantively matching Python
evidence tests in the shipped pattern of
`web/webclient/tests/test_vue_showcase_data_evidence.py` (`run_npm`
subprocess + `covers_requirement` with canonical IDs obtained after spec
sync via `tools.spec_traceability list`): one evidence test runs the new
Vitest data-family suites for the rendering requirement, one runs the
Storybook build + `showcase-coverage` for the showcase requirement — the
substantive assertions live in Vitest; the Python test is the CI execution
evidence, exactly like the precedent. The legacy JS changes are covered by
the dependency-free Node gate (`node --test
web/static/webclient/js/tests/*.test.js`), whose v4/5-tolerance tests from
P6 are rewritten here to v5-only (accept 5, reject 4) and stay wired
through their existing Python evidence runner.

### D6 — No new components, manifest frozen

All rendering extends the three existing manifest components (drawer,
doll, inventory panel); `component-manifest.json` and the frozen
required-set are byte-unchanged, so `showcase-coverage` passes without
manifest edits.

## Risks / Trade-offs

- [Fixture drifts from the Python payload contract] → the v5 fixture is
  copied from the Python panel contract test's serialized sample;
  reviewers diff both when either changes.
- [Many-chip rows get tall] → all layers render (≤ 16 by payload contract)
  with wrapping; no data-hiding truncation is allowed by the wire contract,
  so presentation must absorb the height (tested at the 16-chip bound).
- [Deleting v4 support while any stale bundle cached] → dev-only tree, hard
  refresh; no users.

## Open Questions

None.
