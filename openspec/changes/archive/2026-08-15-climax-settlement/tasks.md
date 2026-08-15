## 1. Confirm the dependency surface this change binds to

- [x] 1.1 Confirm `world/rules/sexual_state.py` already has `pleasure`-based fields from the
  `pleasure-gauge` change landed (arousal derived/comparable, `FIELD_KINDS` in
  `sexual_transitions.py` targets `pleasure` not `arousal`). If not yet landed, stop and coordinate —
  this change is not implementable ahead of it.
- [x] 1.2 Open the landed `sexual-counters` change's diff or the current
  `world/rules/sexual_state.py` and identify the exact public mutator method names for the `高潮次數`
  and `連續高潮次數` counters. Also confirm where those two counters are persisted: if they live
  inside the `sexual_traits` `TraitHandler` (like `climax_today`), rollback coverage is inherited via
  both snapshot enumerations; if they are `sexual_state`-category attributes, they must be added to
  the enumerations in task 5b. Write the findings down for use in tasks 2.4 and 5b.3 — do not guess
  or invent names.

## 2. `world/rules/sexual_state.py`: extension bookkeeping and the settlement decision

- [x] 2.1 Add `SexualState.climax_turns` (read-only `int` property) and
  `SexualState.pending_climax_extension` (read-only `int` property), both backed by
  `entity.attributes.add(key, value, category=_STATE_CATEGORY)`, matching the existing
  `virgin`/`experience_types` storage pattern (not a `TraitHandler` counter — see design.md D2).
- [x] 2.2 Add `SexualState.stage_climax_extension(count: int = 1) -> None` as the sole additive write
  path for `pending_climax_extension`, raising `ValueError` unless `count` is a positive `int`
  (`>= 1`) and leaving the counter unchanged otherwise (design.md D2).
- [x] 2.3 Add module-level `climax_settlement_action(entity) -> str | None`:
  - If `getattr(entity, "sexual", None) is None`: return `None` with no writes — the defensively
    guarded test-seam/robustness path (design.md D6).
  - If `entity.sexual.climax_phase.level != "進行中"`: reset `climax_turns` and
    `pending_climax_extension` to `0` if either is nonzero, return `None`.
  - Else: increment `climax_turns` by `1`. If `pending_climax_extension > 0`, decrement it by `1` and
    return `"extend"`. Otherwise return `"end"`.
- [x] 2.4 Inside `climax_settlement_action()`, immediately before returning `"end"` or `"extend"`, call
  the counter mutators identified in task 1.2 — the `高潮次數` mutator on `"end"`, the `連續高潮次數`
  mutator on `"extend"` — exactly once each.
- [x] 2.5 Add `climax_settlement_action` to this module's `__all__`.
- [x] 2.6 Confirm no import from `world.rules.sexual_transitions` is added to this file —
  `climax_settlement_action()` must not call `apply_event()` itself (design.md D1; avoids the circular
  import `sexual_transitions.py` → `sexual_state.py` already establishes).

## 3. `world/rules/rulebook/sexual.yaml`: the two new rows

- [x] 3.1 Add `sp_cost_on_climax_extension` (`when: {event: climax_extended}`,
  `then: {field: sp, delta: "-15..-10"}`), mirroring `sp_cost_on_climax`'s shape.
- [x] 3.2 Add `experience_gay_added` (`when: {event: penetrative_sex_with_male}`,
  `then: {field: experience_types, add: 男男性愛}`), mirroring `experience_lesbian_added`.
- [x] 3.3 Add `test_rule_sp_cost_on_climax_extension` and `test_rule_experience_gay_added` to
  `world/rules/tests/test_sexual_transitions.py` — required by the existing structural check
  `test_every_rule_id_has_a_test`, which fails otherwise.
- [x] 3.4 Run `test_field_kinds_covers_every_targetable_field` and confirm it still passes unmodified —
  both new rows target fields (`sp`, `experience_types`) already present in `FIELD_KINDS`.

## 4. `world/rules/combat.py`: per-round upkeep wiring

- [x] 4.1 Import `apply_event` from `world.rules.sexual_transitions` and `climax_settlement_action`
  from `world.rules.sexual_state` in `combat.py`.
- [x] 4.2 In `_end_of_round_upkeep`, immediately after the existing `decay_tick(entity, seconds)` call,
  add:
  ```python
  action = climax_settlement_action(entity)
  if action == "extend":
      apply_event(entity, "climax_extended")
  elif action == "end":
      apply_event(entity, "climax_ends")
  ```

## 5. `world/rules/clock.py`: out-of-combat settlement wiring and the early-exit fix

- [x] 5.1 Import `apply_event` from `world.rules.sexual_transitions` and `climax_settlement_action`
  from `world.rules.sexual_state` in `clock.py`.
- [x] 5.2 In `_settle_buffs_and_decay`, add the same three-line block from task 4.2 immediately after
  **both** existing `decay_tick(...)` calls — the one inside the quanta loop and the one in the
  remainder branch.
- [x] 5.3 In `_has_settlement_work`, add the `climax_phase == "進行中"` disjunct before the existing
  `DECAY_CONFIG` loop, per design.md D4:
  ```python
  sexual = getattr(entity, "sexual", None)
  if sexual is None:
      return False
  if sexual.climax_phase.level == "進行中":
      return True
  return any(...)  # existing loop, unchanged
  ```

## 5b. Rollback surfaces and existing settlement-test audit

- [x] 5b.1 Add `("climax_turns", "sexual_state")` and `("pending_climax_extension", "sexual_state")`
  to `world/rules/clock.py::_ADVANCE_ENTITY_SURFACES`.
- [x] 5b.2 Add both attributes to `world/rules/action.py::_snapshot_entity_state()` and
  `_restore_entity_state()` (design.md D6 — rollback coverage is by explicit enumeration, not by
  attribute category). Also add them to the third explicit `sexual_state`-category enumeration,
  `world/rules/cast_settlement.py::_ENTITY_SURFACES` (the out-of-combat cast boundary's
  actor/target surface list), so a rolled-back cast restores a target's climax bookkeeping too.
- [x] 5b.3 If task 1.2 found either lifetime counter persisted as a `sexual_state`-category
  attribute rather than inside `sexual_traits`, add it to the same two enumerations.
- [x] 5b.4 Audit every existing test that drives `run_round`/`_end_of_round_upkeep` or
  `advance`/`_settle_buffs_and_decay` while patching `tick_buffs`/`decay_tick` (e.g.
  `tests/test_initiative_and_turn_loop.py`'s `FakeEntity`, `tests/test_clock.py`'s `sexual = None`
  entities and its defensive-cap/remainder tests, `tests/test_golden_combat.py`,
  `tests/test_monster_behaviour_integration.py`): confirm the design.md D6 guard or an explicit
  `climax_settlement_action` patch keeps them green, and add the explicit mock wherever a fixture
  carries real sexual state at `進行中` and would otherwise emit a real `climax_ends`/`climax_extended`
  event.

## 6. Tests

- [x] 6.1 Unit tests for `climax_settlement_action()` in isolation (no combat/clock involvement):
  returns `None` and resets both counters when not in `進行中`; returns `None` with no writes for an
  entity without a sexual handler (design.md D6 guard); returns `"end"` with no staged
  extension; returns `"extend"` and decrements by exactly `1` per call across a multi-stage scenario
  (`stage_climax_extension(count=3)` consumed over three calls, fourth call returns `"end"`); a stage
  made outside `進行中` does not carry forward.
- [x] 6.2 Unit tests for `climax_turns`: increments once per call while in `進行中`; resets to `0` on
  leaving.
- [x] 6.3 Unit tests (via direct `apply_event(entity, "climax_extended", rng=<stub>)` calls) asserting
  the exact SP delta under an injected RNG, and that the gauge floor is respected at `sp` near `0`.
- [x] 6.4 Unit tests for `experience_gay_added`: adds `男男性愛`; does not touch `virgin`.
- [x] 6.5 Counter-increment tests: `climax_settlement_action()` returning `"end"` increments only the
  `高潮次數` counter; returning `"extend"` increments only `連續高潮次數`.
- [x] 6.6 Integration test on `combat.py::_end_of_round_upkeep` (or `run_round`): a roster member
  entering `進行中` with no staged extension climaxes by the end of that same round; SP decrease is
  asserted qualitatively (within the documented `-30..-20` range), not to an exact value (design.md
  D5). A roster member with a staged extension remains in `進行中` after upkeep and its SP decrease
  falls within `-15..-10`.
- [x] 6.7 Integration test on `clock.py::_settle_buffs_and_decay` (or `WorldClock.advance`): an entity
  in `進行中` with every other `DECAY_CONFIG` field pre-set at floor still resolves to `餘韻` within one
  `advance()` call spanning multiple quanta — the regression test for the early-exit bug described in
  design.md D4 and the corresponding `settlement-stage-order` delta scenario.
- [x] 6.8 Regression test for the original dead-end bug: an entity whose `climax_phase` is driven to
  `進行中` (via the existing `climax_gate` /
  `climax_phase_critical_point_to_in_progress` rules, using the landed `pleasure-gauge` mechanics from
  task 1.1) and then settled through either call site returns to `未達` without any external
  `climax_ends` call — i.e. the `sexual-state-handler` capability's climax cycle is no longer
  reachable-but-unresolvable in practice.
- [x] 6.9 Confirm `world/rules/tests/test_sexual_transitions.py`'s existing
  `test_every_rule_id_has_a_test` and `test_field_kinds_covers_every_targetable_field` still pass with
  the two new rows present.
- [x] 6.10 Unit tests for `stage_climax_extension` validation: `count` of `0`, a negative value, and
  a non-integer each raise `ValueError` and leave `pending_climax_extension` unchanged.
- [x] 6.11 Rollback regression tests (design.md D6): a failed-and-rolled-back `advance()`, a failed
  action commit, and a failed combat-session round each restore `climax_turns`,
  `pending_climax_extension`, and — per task 1.2/5b.3 — the two lifetime counters to their
  pre-transaction persisted values (assert the persisted attribute values, not only the public
  read-only properties).

## 7. Traceability and validation

- [x] 7.1 Run `uv run --locked python -m tools.spec_traceability list` after the delta specs are
  written to obtain the canonical requirement IDs for the new `climax-settlement` capability and the
  modified requirements in `combat-resolution`/`settlement-stage-order`.
- [x] 7.2 Apply `covers_requirement` (imported from `tools.spec_traceability`) to the test functions
  from section 6, using the literal IDs from 7.1 — one test per requirement at minimum; the
  multi-scenario requirements (extension staging, the two counters) may need more than one covering
  test to substantively match every scenario.
- [x] 7.3 Run `uv run --locked python -m tools.spec_traceability check` and resolve any reported gap.
- [x] 7.4 Run the focused package tests this change touches:
  `uv run --locked evennia test --settings test_settings.py world.rules.tests.test_sexual_state
  world.rules.tests.test_sexual_transitions world.rules.tests.test_combat world.rules.tests.test_clock`
  (adjust dotted paths to match wherever the new tests from section 6 actually land).
- [x] 7.5 Confirm no player-facing command changed key, alias, syntax, or availability — this change
  touches no `commands/` file, so `docs/game/commands.md` and `docs/game/command-reference.md` need no
  update (AGENTS.md's command-docs requirement does not apply here).
- [x] 7.6 Run `openspec validate climax-settlement --strict` and resolve any reported issue.
- [x] 7.7 Run the full non-browser Evennia suite once
  (`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands
  server typeclasses world web.webclient`) before handoff, per AGENTS.md's test-runtime guidance —
  this change touches settlement code paths (`combat.py`, `clock.py`) with existing broad test
  coverage that a narrow diff could regress.
