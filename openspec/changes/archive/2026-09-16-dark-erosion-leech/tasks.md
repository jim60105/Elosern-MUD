## Batch order (dark wave — integration contract in ../dark-spell-catalog/design.md)

0. Predecessors (ALL archived and merged; this change is wave change 1 and needs no live sibling):
   - water wave (`water-mp-depletion-reaction`, `water-mana-transfer`, `water-damage-redirect-shield`, `water-spell-catalog`) — ships the attributed hp-loss tick path, grant-time source attribution, and the `gauge_transfer` caster-share leg this change mirrors
   - `dark-self-recovery-missing-fraction` — INDEPENDENT (no shared files); batch order does not constrain this change
   - `dark-spell-catalog` lands AFTER this change (it authors the erosion rows' `caster_share` data)

## 1. Rate-grammar extension (definition load)

- [x] 1.1 Inspect current `world/rules/buffs.py::load_buff_definitions` rate validation and the shipped `_handle_buff_apply` attribution fields before editing; confirm `caster_share` is absent from the grammar (no partial prior work).
- [x] 1.2 Validate one optional `caster_share` clause on the fixed-delta hp-target negative-delta rate shape: finite number in (0, 1]; fail closed at load (offending key named) on non-hp target, non-negative delta, boolean/non-finite/out-of-range value, and co-declaration with `recovery` or `scale_from_source`. Rows without the clause keep loading bit-identically.

## 2. Tick-site credit leg

- [x] 2.1 In `_apply_rate_modifier`'s hp branch, after the existing `actual_loss` computation and the existing single `hp_loss` dispatch: when the rate carries `caster_share`, resolve the origin caster from the buff cache's persisted grant-time `source_pk` (roster-then-dbref posture, matching the upkeep credit resolver's semantics), and credit `floor(actual_loss × caster_share)` through the same clamped living-only HP-increase leg the shipped `gauge_transfer` caster-share hp leg uses — never above maximum, never reviving, dispatching no outcome event. A dead/unresolvable origin or absent share changes nothing.
- [x] 2.2 Confirm non-goals in code: no `state_reactions.yaml` vocabulary change, no registry rows, no buffs.yaml row ships `caster_share` in this change (the catalog change authors the erosion data), no new upkeep stage, no element/skill-key branch anywhere in the leg.

## 3. Behavioral evidence and integration

- [x] 3.1 Synthetic behavior suite (new module `world/rules/tests/test_erosion_leech.py`): full-share transfer; floor-bound partial credit; dead-origin skip; max clamp; one-dispatch-per-tick (victim reaction fires once, credit dispatches nothing); refresh redirect (newest applier) and refresh-without-source retention; expiry/dispel extinguishment; unresolvable origin; spoofed caller `source_pk` ignored; non-share rows (poison/fire_scorch shape) bit-identical. Tests must fail on credit-on-requested, double credit, resurrection credit, and post-expiry credit. Real settlement through `tick_buffs` (and one combat-round upkeep pass proving no double death settlement), not source-text or row assertions.
- [x] 3.2 Register the new module in exactly one shard in `.github/evennia-shards.json`; verify the ownership-contract test.
- [x] 3.3 Run the focused labels below; `tools.observability_lint check`; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate dark-erosion-leech --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing the new `erosion-leech` IDs and the supersets of the modified `buff-handler-integration` ID.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_erosion_leech world.rules.tests.test_buffs world.rules.tests.test_upkeep_settlement
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate dark-erosion-leech --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. `world.rules.tests.test_erosion_leech` is the intended synthetic module owned by this change, not an existing-test claim. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
