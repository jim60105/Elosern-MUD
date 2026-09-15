## Batch order (water wave)

1. `water-mp-depletion-reaction` (this change) — MUST land before any 潮退 buffs.yaml row goes live.
2. `water-mana-transfer` — depends on this change's canonical writer.
3. `water-damage-redirect-shield` — depends on this change's writer; independent of 2.
4. `water-reflux-team-marker` — depends on 2.
5. `water-spell-catalog` — depends on all; data-only final integration.

## 1. Canonical writer and routing

- [ ] 1.1 Inspect current source and exported references (codegraph/LSP) for every `traits.mp` write site; enumerate them in the PR notes. Confirm the shared interfaces in ../water-spell-catalog/design.md and that no predecessor contract is unimplemented.
- [ ] 1.2 Implement `world/rules/mp_flow.py` per design D1: one clamped writer returning the actual signed change, `remove_mp` drain-all entry, exactly-once `mp_zero` dispatch on positive→zero crossings via a decrease, source-skill + source-tier attribution with first-tier fallback; extend `dispatch_outcome_reaction` with the optional event-source parameter without changing existing callers.
- [ ] 1.3 Route the buff engine's `rate {target: mp}` tick through the writer (both signs), persisting grant-time source/tier attribution into the event; keep the hp branch's `hp_loss` dispatch, the pull no-op and recovery profiles unchanged.
- [ ] 1.4 Route the step-6 cast-cost `mp` deduction through the writer inside the existing staged pending effect with the cast skill as source; hp/sp deduction and preflight/recheck agreement untouched.
- [ ] 1.5 Add the closed `event_source_skill` when key to `state_reactions.py` validation and the shared condition evaluator (fail closed on missing/unknown/non-string; load-time rejection when paired with no `event`); verify an alternate synthetic rule reuses the key with no water-key branch in generic code.

## 2. Rulebook rows (no-silent-window given: DoT rows ship here)

- [ ] 2.1 Add `ebbing` / `ebbing_deep` / `ebbing_maelstrom` rows to `buffs.yaml` (`rate {target: mp, delta: -5|-12|-18}`, tick_interval 10, duration 60, polarity debuff, refresh stacking) and `suffocated` (duration 40, debuff, empty modifiers).
- [ ] 2.2 Add `suffocation_locks_actions` and the bind-marker lock row to `combat_modifiers.yaml` (`actions_per_turn: 0`); keep the per-rule-ID test correspondence requirement satisfied by adding exactly one test per new rule ID.
- [ ] 2.3 Add the `drowning_suffocation` rule to `state_reactions.yaml` (`event: mp_zero` + `event_source_skill` qualification per design D5, `then: apply_buff: suffocated`); confirm load-time validation passes with the row present while the qualified registry node arrives only with the catalog change.
- [ ] 2.4 Add fail-closed `status_display.yaml` rows (潮退／潮退退潮 wording per the wave naming decision recorded in the catalog design, 窒息) for every new buff key

## 3. Behavioral evidence and integration

- [ ] 3.1 Implement synthetic behavior tests for every delta scenario: writer clamping/actual-delta, exactly-once crossing, no-dispatch on already-zero/increase/zero-actual, hp-branch regression, cast-cost routed payment to zero (commit + event; rejected cast = no event), DoT tick attribution across partitions, immunity blocking of new mp-DoT grants, rule-layer source filtering (qualified vs unqualified vs missing source), transactional rollback of a reaction-applied marker inside a failing cast and clock advance. Every test must fail on a plausible behavioral error; no source-string or data-echo assertions.
- [ ] 3.2 Register new non-browser test modules in exactly one `.github/evennia-shards.json` shard and verify the ownership optimization contract test.
- [ ] 3.3 Exercise the changed engine path with a disposable offline scenario (apply an mp DoT to a synthetic entity, advance the clock to the crossing, observe suffocation lock via the cast gate); delete it only after proof.
- [ ] 3.4 Run the focused labels below after editing stops; `tools.observability_lint check` in the same batch (state/event paths change); `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate water-mp-depletion-reaction --strict`. Obtain canonical IDs via `tools.spec_traceability list` during the separately authorized main-sync and annotate exactly the tests establishing them.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_mp_flow world.rules.tests.test_mp_state_feedback world.rules.tests.test_buffs world.rules.tests.test_state_reactions world.rules.tests.test_combat_modifiers
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate water-mp-depletion-reaction --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. New test labels are intended behavior modules owned by this change. No full local suite, browser, or aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
