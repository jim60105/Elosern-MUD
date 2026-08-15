## 1. Shared cost-adjustment helper

- [x] 1.1 Add `apply_cost_modifier(amount: int, percentage: str | None) -> int` to
      `world/rules/combat_modifiers.py`: `None` returns `amount` unchanged; otherwise parse the
      signed, possibly fractional percentage with the module's existing `_PERCENT_RE` and return
      `max(0, math.floor(amount * (1 + pct / 100)))`
- [x] 1.2 Add focused unit tests for the helper (in `world/rules/tests/test_combat_modifiers.py` or
      a sibling module): no modifier, zero/positive/negative percentages, fractional percentage
      (e.g. `"-5%"` on cost 10 → 9), zero clamp (`"-100%"` and beyond → 0), and malformed
      percentage strings raising

## 2. Resolver and preview cost sinks

- [x] 2.1 Add a private `_adjusted_costs(actor, skill) -> dict[str, int]` in
      `world/rules/action.py` that computes one `evaluate_combat_modifiers(actor)` bundle and maps
      each `skill.cost` resource key through `apply_cost_modifier` with the
      `f"{resource_key}_cost"` bundle key
- [x] 2.2 Rewire `_step2_resource_check` (`action.py:245-251`) to compare stored trait values
      against `_adjusted_costs` instead of `skill.cost` verbatim
- [x] 2.3 Rewire `_step6_resource_deduction` (`action.py:579-599`) to use `_adjusted_costs` for
      both the recheck and the staged amount, so the `resource_spend|...|{amount}` description and
      the event-log `amount`/`trait_delta` report the real deduction
- [x] 2.4 Rewire the resource loop in `_skill_wide_failure` (`action_preview.py:96-98`) to apply
      `apply_cost_modifier` with `evaluate_combat_modifiers_no_create(actor)`, reusing the single
      bundle evaluation also used for the `actions_per_turn` check
- [x] 2.5 Tests (each with `covers_requirement` where a main-spec requirement applies): a
      `precise_mana_control` owner with MP exactly at `floor(cost * 0.9)` casts where the declared
      cost would reject; the deduction and event log carry the adjusted amount; the adjusted cost
      clamps at zero without staging a negative amount; a fractional conferred-grant percentage
      floors identically in check, deduction, and preview; zero-cost skills (`flee`) and resource
      keys with no `X_cost` bundle entry are unchanged

## 3. Damage sinks

- [x] 3.1 Add pure helpers in `world/rules/combat.py`: an adjusted-attack helper that adds the
      flat `atk_phys` bundle value only when `attack_key == "atk_phys"`, and an adjusted-defense
      helper that adds the flat `defense` bundle value, both reading `evaluate_combat_modifiers()`
- [x] 3.2 Use both helpers in `_handle_damage` (`combat.py:274-275`) so the magnitude becomes
      `max(round(adjusted_attack * multiplier) - adjusted_defense, floor)`
- [x] 3.3 Tests: physical damage with and without `atk_phys` rules (exact staged amount
      `round((eff + 5) * multiplier) - defense`); magic-school damage is unaffected by the
      `atk_phys` bonus; physical and magic damage both mitigated by the `defense` bonus; the
      damage floor still clamps
- [x] 3.4 Confirm `test_to_hit_calibration.py` and `test_golden_combat.py` still pass unchanged
      (to-hit math is untouched)

## 4. Damage-estimation surfaces

- [x] 4.1 Switch `_expected_damage_per_attack` (`overwhelm.py:159-175`) to the shared
      adjusted-attack/defense helpers
- [x] 4.2 Switch `_choose_skill.expected_damage` (`monster_behaviour.py:275-285`) to the shared
      helpers so physical candidates include the `atk_phys` bonus, computing the defender's
      adjusted defense once per `_choose_skill` call rather than per candidate
- [x] 4.3 Tests: the overwhelm estimator includes both flat bonuses in its terms; a monster
      choosing between physical and magic candidates ranks the physical candidate with its
      `atk_phys` bonus

## 5. Data and presentation

- [x] 5.1 Update inline comments in `world/rules/rulebook/combat_modifiers.yaml` for the four now-
      live fields (`defense`, `atk_phys`, `mp_cost`, `sp_cost` rows) to state the field is consumed
      by deterministic damage/resource math; make NO numeric changes
- [x] 5.2 Make no changes to `status_query.py` or `status_display.yaml`, and verify the status
      panel is unchanged by running `test_status_query.py`, `test_status_display.py`, and
      `test_combat_view.py`; add one regression test asserting the read-model conditions for an
      entity owning all four sink skills carry the exact same codes, labels, and modifiers as the
      bundle

## 6. Traceability and regression sweep

- [x] 6.1 Read `docs/development/spec-test-traceability.md`; obtain canonical requirement IDs with
      `uv run --locked python -m tools.spec_traceability list` and annotate the new tests with
      `covers_requirement` (never construct IDs manually)
- [x] 6.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the existing
      annotations on the amended "eight previously-dead" requirement still resolve
- [x] 6.3 Run the affected suites (`world.rules` package tests, `world.skills` tests if touched),
      then `uv run --locked python -m compileall -q world typeclasses commands server` and
      `git diff --check`; run the full Evennia suite (`--parallel 16 --noinput`) once
- [x] 6.4 Run `openspec validate --change fix-combat-rule-sinks --strict` and confirm all
      apply-required artifacts are done before handoff
