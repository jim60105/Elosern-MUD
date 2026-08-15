## 1. Data: sexual_pleasure.yaml and its loader

- [ ] 1.1 Create `world/rules/rulebook/sexual_pleasure.yaml` with `pleasure_bands` (five entries,
      `{level, floor, ceiling}`, per design.md D-1's exact table) and `sensitivity_multipliers`
      (four `SENSITIVITY_LEVELS` keys) and `shame_multipliers` (five `SHAME_LEVELS` keys), using the
      exact values in design.md D-1. Do **not** add a `participant_count_multiplier` section — that
      is `B5`'s addition, not this proposal's (design.md D-1).
- [ ] 1.2 Add a `PleasureConfig` frozen dataclass and loader function in
      `world/rules/sexual_state.py`, following the `AffinityConfig`/`world/rules/affinity_config.py`
      precedent: validate the five bands are contiguous, ascending, cover `0..100` exactly, one per
      `AROUSAL_LEVELS` entry in order; validate `sensitivity_multipliers`'/`shame_multipliers`' key
      sets match `SENSITIVITY_LEVELS`/`SHAME_LEVELS` exactly, each a positive float. Fail closed
      (raise, naming the problem) on any deviation. Load it once at module import time into a
      **module-level singleton, `PLEASURE_CONFIG`** (matching `_RULES = _load_rules()`'s existing
      eager-load pattern in `sexual_transitions.py`) — every consumer in sections 2, 3, and 6 below
      imports this same object; there is exactly one loaded instance, never a per-caller reload.
- [ ] 1.3 Add `ordinal_for(pleasure_value: int) -> int` and `floor_for_level(level: str) -> int` (and
      `floor_for(pleasure_value: int) -> int`, returning the *current* band's floor, used by decay)
      methods on `PleasureConfig`.

## 2. SexualState: pleasure field and derived arousal

- [ ] 2.1 Drop `"arousal"` from `_ORDERED_FIELDS`; add `pleasure` construction in
      `_build_from_baseline()` per design.md D-2 (band-floor of the baseline's `arousal` string,
      defaulting to `AROUSAL_LEVELS[0]`'s floor).
- [ ] 2.2 Add `SexualState.pleasure` property returning `self._traits.pleasure`.
- [ ] 2.3 Replace the `arousal` property with the derived, read-only version (design.md D-3): add a
      small `_DerivedArousal` class (module-level in `sexual_state.py`) exposing `.value`, `.levels`,
      `.level`, and the five comparison dunders, with no value setter.
- [ ] 2.4 Update `__all__` to export `PLEASURE_CONFIG` (needed by `sexual_transitions.py`,
      `combat_modifiers.py`, and `status_query.py` — sections 3 and 6 below) and `_DerivedArousal`
      only if a type reference to it is needed outside this module (confirm during implementation;
      likely not required).

## 3. sexual_transitions.py: the bounded_counter kind

- [ ] 3.1 Import `PLEASURE_CONFIG` (the module-level singleton, not a per-call reload) from
      `sexual_state.py`.
- [ ] 3.2 `FIELD_KINDS`: remove `"arousal"`, add `"pleasure": "bounded_counter"`.
- [ ] 3.3 `_validate_rule_effect()`: add the `bounded_counter` branch — same allowed-keys shape as
      `ordered_level` (`{"field","delta"}` or `{"field","set"}`); `set` must be an `int` in
      `[0, 100]`, raising otherwise (name the invalid value in the error).
- [ ] 3.4 `_apply_then()`: add the `bounded_counter` branch exactly as design.md D-4 specifies (read
      `PLEASURE_CONFIG.ordinal_for(trait.value)` **live, immediately before and immediately after**
      the mutation — do not read the before-value from `context["arousal"]`) — **critically, it must
      return `field="arousal"`, not `field="pleasure"`**, with `direction` computed by comparing the
      two live ordinals read in 3.4's parenthetical above — not by comparing raw pleasure numbers, and
      not by reading `context["arousal"]`.

## 4. sexual.yaml: rewrite the four arousal-writing rules

- [ ] 4.1 `arousal_up_on_stimulus`: `then: {field: pleasure, delta: "+8..+14"}` (id unchanged).
- [ ] 4.2 `arousal_up_on_sustained_stimulus`: `then: {field: pleasure, delta: "+6"}` (id unchanged).
- [ ] 4.3 `arousal_extreme_stimulus_to_max`: `then: {field: pleasure, set: 100}` (id unchanged).
- [ ] 4.4 `arousal_reset_after_climax`: `then: {field: pleasure, set: 15}` (id unchanged).
- [ ] 4.5 Leave `wetness_follows_arousal`, `climax_gate`, and every other rule's `when` clause
      referencing `field: arousal` completely unchanged — they continue to read the derived view.

## 5. decay_tick: the pleasure branch

- [ ] 5.1 Rename `DECAY_CONFIG`'s `"arousal"` key to `"pleasure"`; keep `floor: 0` for documentation
      symmetry (unused by the new branch — see design.md D-5).
- [ ] 5.2 Add the `field == "pleasure"` branch in `decay_tick()`'s dispatch, before the generic
      `else` branch: `current_band_floor = PLEASURE_CONFIG.floor_for(trait.value); trait.base =
      max(0, current_band_floor - 1)`. `decay_tick()` lives in the same module as `PLEASURE_CONFIG`
      (`sexual_state.py`), so no new import is needed for this call site.

## 6. combat_modifiers.py and status_query.py: teach the no-create readers about pleasure

**Found during review — required scope, not optional cleanup. Without this section, skill-cast
preview and the player status panel silently freeze at each character's import-time arousal baseline
the moment their `SexualState` is materialized, and never again reflect a runtime `pleasure` change.
See design.md D-7 for the full analysis.**

- [ ] 6.1 In `world/rules/combat_modifiers.py::_stored_sexual_level()`, add a `field == "arousal"`
      branch **before** the existing generic `elif isinstance(traits, Mapping) and field in
      traits:` branch: look up `"pleasure"` (not `"arousal"`) in the raw `traits` mapping; if present
      and its `raw.get("base")` is an `int`, return `_StoredLevel(PLEASURE_CONFIG.ordinal_for(raw
      ["base"]), AROUSAL_LEVELS)`; otherwise fall through to the existing baseline-fallback branch at
      the bottom of the function, unchanged. Do not alter the `climax_phase` path (the unmodified
      generic branch continues to serve it).
- [ ] 6.2 Import `PLEASURE_CONFIG` from `world.rules.sexual_state` in `combat_modifiers.py` (no
      circular import — `sexual_state.py` imports nothing from `combat_modifiers.py`).
- [ ] 6.3 Apply the identical `field == "arousal"` branch to
      `world/rules/status_query.py::_sexual_level()`, using that file's own `_LevelRef` wrapper type
      (not `_StoredLevel` — the two files use different but structurally identical wrapper classes;
      do not import one file's wrapper into the other). Import `PLEASURE_CONFIG` from
      `world.rules.sexual_state` in `status_query.py` as well.
- [ ] 6.4 Confirm neither edit changes `build_no_create_condition_context()`'s or
      `_sexual_condition_context()`'s own signatures, the `"arousal"` outer context key name, or any
      `climax_phase`-handling code path — the fix is scoped to the raw-storage lookup for `arousal`
      only, inside each file's private helper function.

## 7. Migrate existing direct arousal-value test call sites

Every site sets `entity.sexual.arousal.value = "<level>"` to arm a threshold; replace with
`entity.sexual.pleasure.base = <floor>` using this table: `平靜→0, 微興奮→15, 中等→35, 高度→60,
極限→85`.

- [ ] 7.1 `world/rules/tests/test_combat_modifiers.py` — lines ~61 (`"高度"`→`60`), ~66 (`"中等"`
      →`35`), ~68 (`"極限"`→`85`), ~275 (`"高度"`→`60`). Verify against current line numbers before
      editing; `exposure-combat-modifier` (already proposed, separate change) only *adds* new test
      methods to this file and does not touch these lines, so no merge conflict is expected when
      both land.
- [ ] 7.2 `world/rules/tests/test_combat_modifiers_self_arming.py` — line ~31 (`"高度"`→`60`).
- [ ] 7.3 `world/rules/tests/test_combat_modifiers_matched.py` — lines ~42, ~53 (`"高度"`→`60` each).
- [ ] 7.4 `world/rules/tests/test_sexual_transitions.py` — lines ~65 (`"微興奮"`→`15`), ~71
      (`"高度"`→`60`), ~123 (`"高度"`→`60`), ~324 (`"高度"`→`60`), ~332 (`"高度"`→`60`), ~336
      (`"高度"`→`60`), ~351 (`"極限"`→`85`). **Line ~284 is a different case**: it primes a
      *synthetic* monkeypatched `Rule` set (not production `sexual.yaml`) whose `then.field` is
      literally `"arousal"`, used to test `RuleConvergenceError` detection. Update that synthetic
      rule's `then` to `{"field": "pleasure", "delta": "+1"}` as well (not just the priming line, or
      `FIELD_KINDS["arousal"]` will KeyError before the convergence loop is ever exercised), then
      change the priming line to `entity.sexual.pleasure.base = 15` (ordinal 1 = `微興奮`).
- [ ] 7.5 `world/rules/tests/test_sexual_state.py` — line ~86 (`"高度"`→`60`).
- [ ] 7.6 `world/rules/tests/test_sexual_decay_and_reset.py` — lines ~18 (`"極限"`→`85`), ~55
      (`"中等"`→`35`). **These two tests exercise decay directly** — after migration, also update
      their assertions to match design.md D-5's new decay behaviour (one band down, not one ordinal
      down) if the existing assertions checked the old ordinal-decrement mechanism.
- [ ] 7.7 `world/rules/tests/test_monster_sexual_baseline.py` — line ~30 (`"高度"`→`60`; note this
      site uses a bare `state.arousal.value =`, not `entity.sexual.arousal.value =` — confirm
      whether `state` there is a `SexualState` instance and adjust to `state.pleasure.base =`
      accordingly).
- [ ] 7.8 `world/rules/tests/test_status_query.py` — line ~99 (`"極限"`→`85`).
- [ ] 7.9 `world/rules/tests/test_status_boundary.py` — line ~68 (`"高度"`→`60`).

## 8. New tests

- [ ] 8.1 Band table: parametrised test asserting every `pleasure` value `0..100` maps to the
      documented `arousal` level, including boundary values `14/15`, `34/35`, `59/60`, `84/85`.
- [ ] 8.2 `PleasureConfig` load-time validation: a malformed band table (gap, overlap, wrong count,
      not covering `0..100`) raises at load; a malformed multiplier table (missing/extra key,
      non-positive value) raises at load.
- [ ] 8.3 Construction: the three `sexual-state-handler` ADDED-requirement scenarios (imported level
      → band floor; omitted arousal → floor 0; Monster with no baseline → floor 0).
- [ ] 8.4 Bounds: the two `sexual-state-handler` ADDED-requirement clamp scenarios (delta exceeding
      100 clamps at 100; delta below 0 clamps at 0).
- [ ] 8.5 Derived arousal: mid-band read, comparison operators, and that direct assignment
      (`entity.sexual.arousal.value = 3`) raises `AttributeError`.
- [ ] 8.6 Decay: the three `sexual-state-handler` ADDED-requirement decay scenarios (mid-band decays
      to one-band-down; floor-band clamps at 0; a single interval never crosses more than one band
      even from the top of a band).
- [ ] 8.7 **The D-4 regression, highest priority in this task list**: a test proving
      `wetness_follows_arousal` still fires when a `pleasure`-targeting rule's resolved delta crosses
      an arousal band boundary, and does **not** fire when the resolved delta stays within one band
      — the two `sexual-transition-rulebook` ADDED-requirement scenarios for `bounded_counter`.
- [ ] 8.8 `climax_gate` regression: an `extreme_stimulus_applied` event still drives `climax_phase`
      from `未達` to `接近` within one `apply_event()` call, proving `when: {field: arousal, equals:
      極限}` conditions evaluate correctly against the derived view.
- [ ] 8.9 Rewritten-rule tests: update the four existing `test_rule_arousal_up_on_stimulus` /
      `test_rule_arousal_up_on_sustained_stimulus` / `test_rule_arousal_extreme_stimulus_to_max` /
      `test_rule_arousal_reset_after_climax` functions in
      `world/rules/tests/test_sexual_transitions.py` to assert against `entity.sexual.pleasure.value`
      (exact deltas: `+8..+14`, `+6`, `set: 100`, `set: 15`) instead of `entity.sexual.arousal`'s
      ordinal. Function names stay unchanged — `test_every_rule_id_has_a_test()` matches by rule id,
      not by assertion content.
- [ ] 8.10 **The D-7 regression, second-highest priority** — in
      `world/rules/tests/test_action_preview.py` (or `test_combat_modifiers.py`, wherever the
      existing no-create tests live): a test asserting `evaluate_combat_modifiers_no_create(entity)`
      reports `high_arousal_agility_accuracy_penalty`'s adjustment for a **materialized** entity whose
      `pleasure` has been raised at runtime past the `高度` floor — proving the preview path tracks
      live state, not the frozen import baseline — plus a companion test for an entity with no
      materialized handler at all, confirming the baseline-string fallback still works and that no
      `sexual_traits` Attribute is created by the call (pin both `combat-modifier-table` ADDED-
      requirement scenarios).
- [ ] 8.11 **The D-7 regression, status side** — in `world/rules/tests/test_status_query.py`: a test
      asserting `build_status_read_model()`'s `conditions` include the sexual-threshold entry for a
      materialized, runtime-raised entity, and a second test asserting the entry **disappears** again
      once `pleasure` is reduced below the threshold on the same entity across two builds — pinning
      both `webclient-status-presentation` ADDED-requirement scenarios ("reflects live pleasure" and
      "disappears again"), plus a companion unmaterialized-baseline test mirroring 8.10's.

## 9. Verification

- [ ] 9.1 Run `uv run --locked python -m tools.spec_traceability list` and confirm the new
      requirement ids for `sexual-state-handler`'s four `ADDED Requirements`,
      `sexual-transition-rulebook`'s one `ADDED Requirement`, `combat-modifier-table`'s one `ADDED
      Requirement`, and `webclient-status-presentation`'s one `ADDED Requirement`; annotate every new
      test from sections 8 with `@covers_requirement(...)` using the literal ids.
- [ ] 9.2 Confirm `test_field_kinds_covers_every_targetable_field()` and
      `test_every_rule_id_has_a_test()` (both pre-existing, generic, no hardcoded field/rule names)
      pass unmodified.
- [ ] 9.3 Run the focused test modules:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.rules.tests.test_sexual_state world.rules.tests.test_sexual_transitions
      world.rules.tests.test_sexual_decay_and_reset world.rules.tests.test_monster_sexual_baseline
      world.rules.tests.test_combat_modifiers world.rules.tests.test_combat_modifiers_self_arming
      world.rules.tests.test_combat_modifiers_matched world.rules.tests.test_status_query
      world.rules.tests.test_status_boundary world.rules.tests.test_action_preview`.
- [ ] 9.4 Run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 9.5 Run `openspec validate pleasure-gauge --strict`.
- [ ] 9.6 Run the full non-browser suite once
      (`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput
      --parallel 16 commands server typeclasses world web.webclient`) to catch any further
      `entity.sexual.arousal.value =` call site this task list's grep pass missed, and any other
      raw-storage `"arousal"` key lookup section 6's grep pass may have missed.
