## Batch order (water wave)

1. `water-mp-depletion-reaction` — predecessor (canonical MP writer + attribution fields). MUST land first.
2. `water-mana-transfer` — parallel sibling; this change is independent of it (shared files serialize per the catalog design's schedule).
3. `water-damage-redirect-shield` (this change).
4. `water-spell-catalog` — rebinds the registry node to `buff_apply:water_film`.

## 1. Divert profile and loader

- [ ] 1.1 Inspect current source and exported references (codegraph/LSP) for the buff loader, `_handle_damage`'s staging path and `buffs.yaml` consumers before editing; confirm the predecessor's writer API matches ../water-spell-catalog/design.md.
- [ ] 1.2 Extend `load_buff_definitions` with the validated `divert` profile per design D1 (gauge target, finite fraction (0,1], positive-int cap, finite duration required) and a consumed-budget cache helper reading/updating `divert_consumed` on the instance cache.

## 2. Damage-stage divert

- [ ] 2.1 Implement the divert consumption in `_handle_damage` after the full amount pipeline per design D2/D3: key-ascending profile order against the residual, three-bound clamp (fraction, cap − consumed, current gauge), staged HP write of the residual only, gauge payment through the canonical writer attributed to the profile's persisted grant-time source/tier, commit-time cache-budget update derived from the writer's actual delta.
- [ ] 2.2 Verify step-7 projected-HP/defeat and loss-driven feedback consume only the reduced staged amount; a fully diverted hit stages no defeat crossing.

## 3. Row replacement

- [ ] 3.1 Delete the dev-era inert `water_shield` bounds row from `buffs.yaml` and its `status_display.yaml` entry; add the `water_film` divert row (mp, 0.3, cap 30, duration 60) plus a display entry (水膜, beneficial). No alias, no migration.
- [ ] 3.2 Update the dev-era `test_buffs.py` water-shape correspondence test to the synthetic-shape posture for the removed row (delete or re-home to a synthetic divert-shape test; do not re-pin the retired bounds row).

## 4. Behavioral evidence and integration

- [ ] 4.1 Implement synthetic behavior tests for every delta scenario: post-defense placement (identical rolls, nonzero defense, profile on/off), three-bound minimums, cap exhaustion vs expiry, deterministic stacked order summing to the incoming amount, miss/zero-damage no-consume, rollback restoring gauge + budget + HP, grant-replaces vs data-refresh-retains budget posture, divert-to-zero dispatching one attributed depletion fact, malformed divert authoring failing at load. Each test must fail on a plausible behavioral error. No water data-contract tests (ratified NON-GOAL).
- [ ] 4.2 Register new non-browser test modules in exactly one `.github/evennia-shards.json` shard and verify the ownership optimization contract test.
- [ ] 4.3 Disposable offline scenario: apply the divert row to a synthetic defender, land scripted hits exhausting the cap, observe HP/gauge/budget; delete only after proof.
- [ ] 4.4 Run the focused labels below after editing stops; `tools.observability_lint check` same batch (damage/state path changes); `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate water-damage-redirect-shield --strict`. Canonical IDs via `tools.spec_traceability list` at the separately authorized main-sync.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_damage_divert world.rules.tests.test_buffs world.rules.tests.test_combat_resolution
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate water-damage-redirect-shield --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
