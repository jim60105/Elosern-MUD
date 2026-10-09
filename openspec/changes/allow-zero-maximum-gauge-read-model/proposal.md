# Proposal

## Why

A zero MP/SP maximum is a sanctioned part of the monster data model — tier bands carry zero MP/SP and balance-approved variant profiles (e.g. `ridge_burrow_hare` 掘巢型, live individual #236) author `mp: 0, sp: 0` verbatim (`world/rules/traits.py` documents this). But the shared status/character read model rejects any gauge whose computed maximum is not strictly positive (`world/rules/status_query/readers.py:_require_gauge`), so the GM portal monster detail page degrades its 資源, 狀態與增益 and 屬性 sections to `source_unavailable` for every such monster, even though the stored state is valid, displayable data.

## What Changes

- Relax the status read model's gauge validation (`_require_gauge`, shared with the breakdown via `_require_gauge_record`): a gauge whose computed maximum is exactly `0` with stored `current` `0` becomes valid canonical state; a negative computed maximum (and every existing per-field type/bounds violation, including `current > maximum` and a nonzero `current` on a zero-maximum gauge) stays a `StatusQueryError` fail-closed.
- GM monster detail: the 資源 / 狀態與增益 / 屬性 sections render for zero-MP/SP monsters (`0 / 0` rows) instead of degrading to `source_unavailable`.
- Webclient character-panel wire validator: the trait-row `max` bound accepts `0` (was minimum 1), so the wire boundary does not reject what the read model now accepts; gauge ratios stay defined client-side as 0 for a zero maximum (already implemented and test-pinned in `webclient-app`'s `gaugeRatio` and in `GmMeter`).
- Add behavior tests across `world/rules/tests/test_status_query`, the webclient status/character presenters, and the GM monster reader (no existing test pins a zero-maximum rejection — verified — so existing fail-closed tests stay unchanged): a zero-maximum mp gauge with `current 0` renders resources/conditions/traits fully; a negative maximum and a nonzero current on a zero maximum still fail closed.
- No backward-compat layers and no data migration: nothing was ever stored that this change newly rejects, and nothing needs rewriting.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-status-presentation`: the compact status resources contract changes the `maximum` bound from "positive safe integer" to "non-negative safe integer" — a zero-maximum gauge is reported verbatim (`0 / 0`) instead of making the panel unavailable; missing, malformed, or negative-maximum gauges still fail closed.
- `gm-runtime-state`: a monster whose sanctioned numeric source zeroes a gauge renders its resource, condition and trait sections instead of `source_unavailable`; corrupt-section isolation and the other entity kinds are unchanged.

## Impact

`world/rules/status_query/readers.py` (`_require_gauge`); downstream verified-tolerant consumers `world/rules/status_query/status.py` (resources), `character.py` (traits rows render `0 / 0`), `breakdown.py` (`_gauge_breakdown` decomposes a zero maximum with no layers, no division); `web/webclient/presentation/character.py` (trait-row `max` bound); `web/gm/readers/` (no code change — sections recover once the read model accepts the state); Vue clients verified non-dividing (`webclient-app/components/vitals.js`, `admin-app/components/GmMeter.vue`, `admin-app/lib/format.js` denominator-zero guard). Combat and resolution use the `DeterministicGaugeTrait` handlers directly — `GaugeTrait` permits `max == 0` (`_enforce_boundaries` clamps to 0) and the flee/feedback paths already pin zero-maximum non-division — so only the read model is out of step; the deterministic core is re-verified by test during implementation.

## Non-goals

No change to monster authoring data, gauge construction, regen, equipment ceiling sync, combat costs/clamps, or possession routing; no webclient payload schema-version bumps; no compatibility layer or migration; no change to how malformed (negative-maximum or type-violating) gauges fail closed.

## Batch:

```text
depends-on: (none)
code-conflicts: (none known; touches world/rules/status_query/, web/webclient/presentation/character.py, world/rules/tests/test_status_query/, web/gm/tests/)
```

Standalone; no dependency on or conflict with the in-flight quest-drawer / guild-board changes.

## Size and standalone delivery

One engineer-day (~7h): reader relaxation plus negative-case pins (1h), webclient wire-bound relaxation (1h), GM monster zero-gauge fixture and reader test plus `covers_requirement` annotations (2.5h), regression run of status-query/breakdown/GM/webclient suites (1.5h), spec-traceability check and docs touch (1h).
