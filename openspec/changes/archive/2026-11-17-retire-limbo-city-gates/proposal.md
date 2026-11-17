# Proposal

## Why

After `subrace-start-settlements`, activation puts every character in its own start
settlement and sets its `home` there. Nobody walks out of 虛境 any more. The owner has
decided that 虛境 becomes a backstage holding room for creation-pending shells only. The
forward gate exits, the gate registry view and the first-gate `home` re-anchor have no
purpose left. The bridges also leak a known defect: every race can see the hidden elven
village paths from 虛境.

## What Changes

- **BREAKING**: `sync_grid()` no longer builds 虛境-to-settlement exits.
  `CITY_GATE_REGISTRY`, `CityGateDef` (`world/maps/city_gates.py`) and the composed
  `SettlementSnapshot.city_gates` view are deleted. The map composer stops reading a
  document's `city_gate` block. The schema still parses it until
  `drop-settlement-city-gate-field` removes it.
- **BREAKING**: the first-gate `home` re-anchor is deleted: `world/rules/city_gates.py`,
  its calls in `typeclasses/exits.py::after_successful_movement` and in
  `world/rules/movement_settlement.py::settle_relocation`, and the movement settlement's
  `_compensate_home` step, whose only writer was the re-anchor.
- The city-gate family is removed from the static-reference closure, its fingerprint
  and `binding_signature()`.
- `sync_limbo()` now removes every exit located in 虛境 or leading into it, and logs
  each removal. This replaces the forward pass and the separate prune pass in
  `sync_grid()`. It is the room's own declarative convergence, not a migration: 虛境
  owns no exits.
- `LimboRoom`'s hard gate (no non-superuser character may enter) is unchanged.
- The remaining gate-registry fixtures (gate labels, gate-map sets, the kit's gate row,
  the closure tests) are removed or retargeted onto the `entrance_refs` probe that
  `entrance-probe-fixtures` adds.

## Batch:

- depends-on: subrace-start-settlements (homes are set at activation; this change's
  `map-knowledge` delta copies the text that change archives)
- depends-on: entrance-probe-fixtures (the shared probe)
- Batch order: `subrace-start-locations`, `subrace-start-settlements`,
  `entrance-probe-fixtures`, `retire-limbo-city-gates` (this change),
  `drop-settlement-city-gate-field`.
- Conflict notes: this change and `subrace-start-settlements` both edit
  `world/maps/static_references.py`, `world/tests/synthetic_data/{__init__,targets}.py`
  and `web/tests/browser/fixtures.py`. Apply after it.
  `world/maps/tests/test_bootstrap/test_bootstrap_selection.py`,
  `world/maps/tests/test_settlement_sources.py` and `web/tests/browser/fixtures.py`
  were last touched by the merged `elven-villages-eolas-fionnen`. Rebase on current
  master.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `limbo-one-way-gates`: the gate registry, forward-exit, missing-gate, growth and
  re-anchor requirements are removed. The reverse-exit prune requirement is replaced by
  the rule that `sync_limbo` removes every exit touching 虛境. The hard entry gate stays.
- `limbo-room`: the zh-tw bridge-exit requirement is removed, and the `sync_limbo`
  scenarios no longer mention a bridge.
- `grid-room-sync`: the Limbo-bridging exit requirement is removed.
- `sample-city-altoria`: the "exactly one bridging exit from Limbo" requirement is
  replaced by a wilderness-gate-only connectivity requirement.
- `map-knowledge`: the grid-traversal scenario no longer names the Limbo bridge.
- `village-ciaran-map`: the entrance requirement, which describes the arrival from 虛境
  and the registry slot, is replaced by one where the wilderness entrance is the only
  outside connection.
- `test-data-independence`: the synthetic kit no longer has a city-gates catalog.

## Impact

- Code: `world/maps/{city_gates.py (deleted),map_data.py,static_references.py,bootstrap.py,AGENTS.md}`,
  `world/rules/{city_gates.py (deleted),movement_settlement.py,AGENTS.md}`,
  `typeclasses/exits.py`.
- Tests and fixtures: about 40 modules that import the gate registry (full list in
  tasks.md), the synthetic kit's `SYNTH_CITY_GATES` and `make_city_gate`, and the
  browser seed and fixture probes.
- Docs: `docs/development/evennia-testing-guide.md`, `docs/lore/settlement-locations.md`
  and `docs/development/metric-settlements.md` stop describing 虛境 gates.
  `docs/superpowers/specs/2026-09-04-onboarding-removal-one-way-limbo-design.md` gets a
  "superseded" note.
- No human-reviewed document.
