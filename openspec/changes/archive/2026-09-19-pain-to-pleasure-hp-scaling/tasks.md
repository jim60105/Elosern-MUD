## 1. Thread the loss amount to the dispatcher

- [x] 1.1 Add an optional `hp_loss_amount` parameter to `dispatch_outcome_reaction` in `world/rules/state_reactions.py`, defaulting to `None` and carried into the action-execution context. Verify existing callers still dispatch unchanged with the default.
- [x] 1.2 Pass the already-computed `actual_loss` from all five `hp_loss` dispatch sites: `world/rules/combat.py:486`, `world/rules/buffs.py:469` (the rate-tick loss — this file's other dispatch is `negative_buff_added`, leave it alone), `world/rules/items.py:972`, `world/rules/action/effects/gauge_transfer.py:100`, and `world/rules/state_reactions.py:560` — the `counter_damage` branch's recursive self-call, which must forward its own `source_actual_loss`. Verify each site passes the value its own `if actual_loss > 0` guard tested, and specifically that a counter-damage strike still triggers the passive on the counter-struck source.

## 2. Loss-proportional gain

- [x] 2.1 Rewrite the `pleasure_gain` execution branch to compute `floor(coefficient × actual_loss ÷ max_hp)` from the rule's authored `max_hp_coefficient`, reading maximum HP through the damage pipeline's existing trait accessor. Verify with synthetic entities that equal losses from spell, item and periodic sources yield equal gains, and that a half-max-HP loss yields five times a tenth-max-HP loss.
- [x] 2.2 Route the `negative_buff_added` shape through the same derivation using the rule's authored `flat_max_hp_fraction` (design D3). Verify a no-loss negative instance yields the flat-fraction gain.
- [x] 2.3 Make every indeterminate case apply nothing rather than guess: absent `hp_loss_amount` on a loss-fraction rule, and unreadable, zero or negative maximum HP. Verify no state write occurs and no exception escapes into the damage settlement.

## 3. Rulebook data and load validation

- [x] 3.1 Re-author the two `pain_to_pleasure` rules in `world/rules/rulebook/state_reactions.yaml` to the new shapes, replacing both six-tier mappings. Verify the rulebook loads and both rules are present.
- [x] 3.2 Extend the loader's `then`-shape validation to accept the two new `pleasure_gain` shapes, to keep accepting a plain integer gain, and to reject a source-tier-keyed mapping fail-closed naming the rule id. Verify with synthetic rule tables, one per accepted and rejected shape.
- [x] 3.3 Confirm `source_tier` retains its other roles: verify a periodic effect still captures its tier at application and `apply_buff_to_source` still attributes by it.

## 4. Traceability and gates

- [x] 4.1 Update the `@covers_requirement` annotations on the tests covering the modified requirement, taking ids from `uv run --locked python -m tools.spec_traceability list`.
- [x] 4.2 Verify `uv run --locked python -m tools.test_data_lint check` passes with `tools/test_data_freeze.json` unchanged — the new assertions use synthetic entities and synthetic rule tables only.
- [x] 4.3 Run `openspec validate pain-to-pleasure-hp-scaling --strict` and the focused labels `world.rules.tests.test_state_reactions`, `world.rules.tests.test_combat_modifiers` and the damage-feedback test module, and confirm all are green.
