## 1. Balance data

- [x] 1.1 Create `world/rules/rulebook/sexual_act_effects.yaml` with `participant_multipliers`
      (`"1": 1.0`, `"2": 1.1`, `"3+": 1.2`) and `climax_extension_threshold: 20`.
- [x] 1.2 Implement `load_effects_config()` in `world/rules/sexual_act_effects.py`, validating exactly
      the keys/shape in design.md D-3, failing closed on any deviation.

## 2. Core functions

- [x] 2.1 Implement `resolve_part(entity, declared_part)` per design.md D-4, with the `Monster` import
      deferred inside the function body.
- [x] 2.2 Implement `participants(actor, targets)` per design.md D-2.
- [x] 2.3 Implement `compute_pleasure_gain(participant, part, base_pleasure, ratio,
      participant_count)` per design.md D-3, reading `PLEASURE_CONFIG` read-only.
- [x] 2.4 Implement the explicit `_COUNTER_MUTATORS` table per design.md D-6 (all eleven entries).

## 3. Effect dataclasses and dispatch

- [x] 3.1 Add `PleasureEffect(act_key: str)` and `SexualCounterEffect(act_key: str)` to
      `world/skills/effects.py`.
- [x] 3.2 Add the two `parse_effect` dispatch branches using `_parse_single_arg`.

## 4. Effect handlers

- [x] 4.1 Implement `_handle_pleasure_effect` in `world/rules/action.py` per design.md D-5: resolve
      `part`/`ratio` per role (actor uses `actor_part`/`actor_pleasure_ratio`; every other participant
      uses `target_part`/`1.0`), compute `participant_count` once, stage one `PendingEffect` per
      participant.
- [x] 4.2 Implement `_apply_pleasure_gain(entity, gain)` per design.md D-5's full sequence: capture
      pre-mutation arousal ordinal and `climax_phase.level == "接近"`; mutate
      `entity.sexual.pleasure.base`; bump `entity.sexual.wetness.value` by one if arousal's ordinal
      rose; attempt `_apply_climax_phase_set(entity, "接近")` if arousal is now `極限`; attempt
      `_apply_climax_phase_set(entity, "進行中")` if the pre-mutation capture found `"接近"`; stage
      `stage_climax_extension()` if now `進行中` and the pre-clamp gain meets threshold. Import
      `_apply_climax_phase_set` and `PLEASURE_CONFIG` from `world.rules.sexual_state` at ordinary top
      level (no cycle to guard against — `sexual_state.py` does not import this module).
- [x] 4.3 Implement `_handle_sexual_counter_effect` per design.md D-7: `actor_counters` on the actor,
      `participant_counters` on every other participant, via `_COUNTER_MUTATORS`.
- [x] 4.4 Register both via `register_effect_handler`, surfaces `frozenset({"sexual"})`, no required
      event context.
- [x] 4.5 Both handlers raise `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)` if
      `act_key` is absent from `SEXUAL_ACT_REGISTRY` (defensive; unreachable while `_act_family()` is
      the only producer of these strings).

## 5. Wire into the registry builder

- [x] 5.1 Update `_act_family()` (`world/skills/sexual_acts/_builder.py`) to set
      `effects=[f"pleasure:{key}", f"sexual_counter:{key}", *(f"sexual_event:{name}" for name in
      row.sexual_events)]` for every row.
- [x] 5.2 Add the `_FORBIDDEN_SEXUAL_EVENTS` frozenset per design.md D-8
      (`stimulus_applied`, `sustained_stimulus_applied`, `extreme_stimulus_applied`, `climax_ends`,
      `climax_extended`) and validate every row's `sexual_events` against it inside `_act_family()`
      itself (per-row, at import time — consistent with `sexual-act-registry`'s existing per-row
      checks, not deferred to the whole-registry test module).
- [x] 5.3 Add the two new structural checks to `sexual-act-registry`'s existing test module (solo
      acts declare no `participant_counters`; non-異種/神之秘法 acts targeting others declare a
      non-`None` `target_part`) per this change's own delta spec.

## 6. Tests

- [x] 6.1 `world/rules/tests/test_sexual_act_effects.py`: unit tests for `resolve_part`,
      `participants`, `compute_pleasure_gain` (including the sensitivity/shame multiplier cases and
      the ratio=0 case).
- [x] 6.2 End-to-end test casting a test-local act (built the same way `sexual-act-registry`'s own
      acceptance test does — `unittest.mock.patch.dict` installing one row for the test's duration,
      never committed to a line module) through `ActionResolver`, asserting: pleasure applied to
      actor and target with the correct part/ratio split; both counter ledgers incremented correctly
      for a symmetric counter; the extension staged when computed gain crosses threshold on a `進行中`
      participant, including the pre-clamp-vs-post-clamp case.
- [x] 6.3 Climax-phase progression tests per design.md D-5's scenarios: 未達→接近 only on a first
      crossing into `極限`; 接近→進行中 on a second, separate gain application while already at 接近;
      never both transitions from one gain application.
- [x] 6.4 Wetness tests: an arousal-band-crossing gain raises `wetness.value` by exactly one; a gain
      that stays within the same band leaves it unchanged.
- [x] 6.5 `sexual_event:` reuse test: an act declaring `sexual_events=("frequent_stimulation",)`
      resolves `apply_event(target, "frequent_stimulation", part=...)` and
      `sensitivity_up_on_frequent_stimulation` applies, with no new handler registered for it.
- [x] 6.6 Forbidden-events structural test: a hypothetical act declaring
      `sexual_events=("stimulus_applied",)` fails at `_act_family()` construction time; one declaring
      `("direct_stimulus_applied",)` succeeds.
- [x] 6.7 Structural test for `_COUNTER_MUTATORS` per design.md D-6.

## 7. Traceability and verification

- [x] 7.1 Run `uv run --locked python -m tools.spec_traceability list` and annotate every new test
      with `covers_requirement` for the three capabilities this change touches.
- [x] 7.2 Run `uv run --locked python -m tools.spec_traceability check`.
- [x] 7.3 Run `uv run --locked evennia test --settings test_settings.py world.rules world.skills`.
- [x] 7.4 Run `uv run --locked python -m compileall -q world`.
- [x] 7.5 Run `openspec validate sexual-act-effects --strict`.
