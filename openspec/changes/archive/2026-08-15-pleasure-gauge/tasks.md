## 1. Data: sexual_pleasure.yaml and its loader

- [x] 1.1 Create `world/rules/rulebook/sexual_pleasure.yaml` with `pleasure_bands` (five entries,
      `{level, floor, ceiling}`, per design.md D-1's exact table) and `sensitivity_multipliers`
      (four `SENSITIVITY_LEVELS` keys) and `shame_multipliers` (five `SHAME_LEVELS` keys), using the
      exact values in design.md D-1. Do **not** add a `participant_count_multiplier` section — that
      is `B5`'s addition, not this proposal's (design.md D-1).
- [x] 1.2 Add a `PleasureConfig` frozen dataclass and loader function in
      `world/rules/sexual_state.py`, following the `AffinityConfig`/`world/rules/affinity_config.py`
      precedent: validate the five bands are contiguous, ascending, cover `0..100` exactly, one per
      `AROUSAL_LEVELS` entry in order; validate `sensitivity_multipliers`'/`shame_multipliers`' key
      sets match `SENSITIVITY_LEVELS`/`SHAME_LEVELS` exactly, each a positive float. Fail closed
      (raise, naming the problem) on any deviation. Load it once at module import time into a
      **module-level singleton, `PLEASURE_CONFIG`** (matching `_RULES = _load_rules()`'s existing
      eager-load pattern in `sexual_transitions.py`) — every consumer in sections 2, 3, and 6 below
      imports this same object; there is exactly one loaded instance, never a per-caller reload.
- [x] 1.3 Add `ordinal_for(pleasure_value: int) -> int` and `floor_for_level(level: str) -> int` (and
      `floor_for(pleasure_value: int) -> int`, returning the *current* band's floor, used by decay)
      methods on `PleasureConfig`.

## 2. SexualState: pleasure field and derived arousal

- [x] 2.1 Drop `"arousal"` from `_ORDERED_FIELDS`; add `pleasure` construction in
      `_build_from_baseline()` per design.md D-2 (band-floor of the baseline's `arousal` string,
      defaulting to `AROUSAL_LEVELS[0]`'s floor).
- [x] 2.2 Add `SexualState.pleasure` property returning `self._traits.pleasure`.
- [x] 2.3 Replace the `arousal` property with the derived, read-only version (design.md D-3): add a
      small `_DerivedArousal` class (module-level in `sexual_state.py`) exposing `.value`, `.levels`,
      `.level`, and the five comparison dunders, with no value setter.
- [x] 2.4 Update `__all__` to export `PLEASURE_CONFIG` (needed by `sexual_transitions.py`,
      `combat_modifiers.py`, and `status_query.py` — sections 3 and 6 below) and `_DerivedArousal`
      only if a type reference to it is needed outside this module (confirm during implementation;
      likely not required).

## 3. sexual_transitions.py: the bounded_counter kind

- [x] 3.1 Import `PLEASURE_CONFIG` (the module-level singleton, not a per-call reload) from
      `sexual_state.py`.
- [x] 3.2 `FIELD_KINDS`: remove `"arousal"`, add `"pleasure": "bounded_counter"`.
- [x] 3.3 `_validate_rule_effect()`: add the `bounded_counter` branch — same allowed-keys shape as
      `ordered_level` (`{"field","delta"}` or `{"field","set"}`); `set` must be an `int` in
      `[0, 100]`, raising otherwise (name the invalid value in the error).
- [x] 3.4 `_apply_then()`: add the `bounded_counter` branch exactly as design.md D-4 specifies (read
      `PLEASURE_CONFIG.ordinal_for(trait.value)` **live, immediately before and immediately after**
      the mutation — do not read the before-value from `context["arousal"]`) — **critically, it must
      return `field="arousal"`, not `field="pleasure"`**, with `direction` computed by comparing the
      two live ordinals read in 3.4's parenthetical above — not by comparing raw pleasure numbers, and
      not by reading `context["arousal"]`.

## 4. sexual.yaml: rewrite the four arousal-writing rules

- [x] 4.1 `arousal_up_on_stimulus`: `then: {field: pleasure, delta: "+8..+14"}` (id unchanged).
- [x] 4.2 `arousal_up_on_sustained_stimulus`: `then: {field: pleasure, delta: "+6"}` (id unchanged).
- [x] 4.3 `arousal_extreme_stimulus_to_max`: `then: {field: pleasure, set: 100}` (id unchanged).
- [x] 4.4 `arousal_reset_after_climax`: `then: {field: pleasure, set: 15}` (id unchanged).
- [x] 4.5 Leave `wetness_follows_arousal`, `climax_gate`, and every other rule's `when` clause
      referencing `field: arousal` completely unchanged — they continue to read the derived view.

## 5. decay_tick: the pleasure branch

- [x] 5.1 Rename `DECAY_CONFIG`'s `"arousal"` key to `"pleasure"`; keep `floor: 0` for documentation
      symmetry (unused by the new branch — see design.md D-5).
- [x] 5.2 Add the `field == "pleasure"` branch in `decay_tick()`'s dispatch, before the generic
      `else` branch: `current_band_floor = PLEASURE_CONFIG.floor_for(trait.value); trait.base =
      max(0, current_band_floor - 1)`. `decay_tick()` lives in the same module as `PLEASURE_CONFIG`
      (`sexual_state.py`), so no new import is needed for this call site.
- [x] 5.3 **Collateral fix found by the full-suite run:** `world/rules/clock.py::_has_settlement_work()`
      iterates `DECAY_CONFIG` reading `getattr(sexual, field).level`, which `CounterTrait` does not
      expose — the rename alone crashes clock settlement on any materialized entity. Teach it a
      counter-aware branch: when the trait has no `.level`, compare `trait.value` against
      `PLEASURE_CONFIG.floor_for_level(config["floor"])` (the `平靜` floor, `0`) instead. Import
      `PLEASURE_CONFIG` in `clock.py` (no circular import — `sexual_state.py` imports nothing from
      `clock.py`).

## 6. combat_modifiers.py and status_query.py: teach the no-create readers about pleasure

**Found during review — required scope, not optional cleanup. Without this section, skill-cast
preview and the player status panel silently freeze at each character's import-time arousal baseline
the moment their `SexualState` is materialized, and never again reflect a runtime `pleasure` change.
See design.md D-7 for the full analysis.**

- [x] 6.1 In `world/rules/combat_modifiers.py::_stored_sexual_level()`, add a `field == "arousal"`
      branch **before** the existing generic `elif isinstance(traits, Mapping) and field in
      traits:` branch: look up `"pleasure"` (not `"arousal"`) in the raw `traits` mapping; if present
      and its `raw.get("base")` is an `int` **and not a `bool`** (Python treats `True` as int 1),
      **clamp it into `[0, 100]`** (`min(100, max(0, base))`) as defensive corruption-guard —
      `CounterTrait.base`'s own setter already clamps every write into `[0, 100]` in this Evennia
      version, so an out-of-range stored value can only mean corrupted storage — then return
      `_StoredLevel(PLEASURE_CONFIG.ordinal_for(base), AROUSAL_LEVELS)`; otherwise fall through to
      the existing baseline-fallback branch at the bottom of the function, unchanged. Do not alter
      the `climax_phase` path (the unmodified generic branch continues to serve it).
- [x] 6.2 Import `PLEASURE_CONFIG` from `world.rules.sexual_state` in `combat_modifiers.py` (no
      circular import — `sexual_state.py` imports nothing from `combat_modifiers.py`).
- [x] 6.3 Apply the identical `field == "arousal"` branch (including the defensive `[0, 100]` clamp
      and the `bool` rejection — see 6.1's note) to `world/rules/status_query.py::_sexual_level()`,
      using that file's own `_LevelRef` wrapper type (not `_StoredLevel` — the two files use
      different but structurally identical wrapper classes; do not import one file's wrapper into
      the other). Import `PLEASURE_CONFIG` from `world.rules.sexual_state` in `status_query.py` as
      well.
- [x] 6.4 Confirm neither edit changes `build_no_create_condition_context()`'s or
      `_sexual_condition_context()`'s own signatures, the `"arousal"` outer context key name, or any
      `climax_phase`-handling code path — the fix is scoped to the raw-storage lookup for `arousal`
      only, inside each file's private helper function.

## 7. Migrate existing direct arousal-value test call sites

Every site sets `entity.sexual.arousal.value = "<level>"` to arm a threshold; replace with
`entity.sexual.pleasure.base = <floor>` using this table: `平靜→0, 微興奮→15, 中等→35, 高度→60,
極限→85`.

- [x] 7.1 `world/rules/tests/test_combat_modifiers.py` — lines ~61 (`"高度"`→`60`), ~66 (`"中等"`
      →`35`), ~68 (`"極限"`→`85`), ~275 (`"高度"`→`60`). Verify against current line numbers before
      editing; `exposure-combat-modifier` (already proposed, separate change) only *adds* new test
      methods to this file and does not touch these lines, so no merge conflict is expected when
      both land.
- [x] 7.2 `world/rules/tests/test_combat_modifiers_self_arming.py` — line ~31 (`"高度"`→`60`).
- [x] 7.3 `world/rules/tests/test_combat_modifiers_matched.py` — lines ~42, ~53 (`"高度"`→`60` each).
- [x] 7.4 `world/rules/tests/test_sexual_transitions.py` — lines ~65 (`"微興奮"`→`15`), ~71
      (`"高度"`→`60`), ~123 (`"高度"`→`60`), ~324 (`"高度"`→`60`), ~332 (`"高度"`→`60`), ~336
      (`"高度"`→`60`), ~351 (`"極限"`→`85`). **Line ~284 is a different case**: it primes a
      *synthetic* monkeypatched `Rule` set (not production `sexual.yaml`) whose `then.field` is
      literally `"arousal"`, used to test `RuleConvergenceError` detection. Every rule in that set
      must retarget to `{"field": "pleasure", "delta": "+6"}` / `"-6"` (any `then.field` left as
      `"arousal"` KeyErrors `FIELD_KINDS` before the convergence loop is ever exercised), and the
      priming line must become `entity.sexual.pleasure.base = 10` (keeping `exposure.value = 1`):
      the oscillation only cycles while the ±6 deltas cross the `平靜`/`微興奮` boundary (10↔16) —
      band-staying deltas (e.g. `+1` from `15`) would make the set converge and the test never
      raise.
- [x] 7.5 `world/rules/tests/test_sexual_state.py` — line ~86 (`"高度"`→`60`).
- [x] 7.6 `world/rules/tests/test_sexual_decay_and_reset.py` — lines ~18 (`"極限"`→`85`), ~55
      (`"中等"`→`35`). **These two tests exercise decay directly** — after migration, also update
      their assertions to match design.md D-5's new decay behaviour (one band down, not one ordinal
      down) if the existing assertions checked the old ordinal-decrement mechanism.
- [x] 7.7 `world/rules/tests/test_monster_sexual_baseline.py` — line ~30 (`"高度"`→`60`; note this
      site uses a bare `state.arousal.value =`, not `entity.sexual.arousal.value =` — confirm
      whether `state` there is a `SexualState` instance and adjust to `state.pleasure.base =`
      accordingly).
- [x] 7.8 `world/rules/tests/test_status_query.py` — line ~99 (`"極限"`→`85`).
- [x] 7.9 `world/rules/tests/test_status_boundary.py` — line ~68 (`"高度"`→`60`).
- [x] 7.10 `world/rules/tests/test_action_pipeline_atomicity.py` — line ~63: `setattr(entity.sexual.
      arousal, "value", 2)` primes the injected-failure effect; retarget to `setattr(entity.sexual.
      pleasure, "base", 2)`. Line ~72's read assertion (`entity.sexual.arousal.value == 0`) keeps
      working against the derived view and needs no edit.
- [x] 7.11 `world/rules/tests/test_sexual_event_self_arming.py` — lines ~32/47 read
      `actor.sexual.arousal.value` before/after a `sexual_event:stimulus_applied` resolution and
      assert it rose. The `+8..+14` delta from `0` stays inside the `平靜` band, so the derived
      ordinal does not move; retarget both reads to `actor.sexual.pleasure.value` (before/after),
      which rises.
- [x] 7.12 `world/rules/tests/test_divine_mystery_gate.py` —
      `test_elf_casts_divine_sexual_arts_at_no_resource_cost` lines ~101/109 do the same
      before/after ordinal reads on `target.sexual`; retarget to `target.sexual.pleasure.value`.
      `test_unmechanized_mysteries_cast_without_state_change` (lines ~137/140) only asserts an
      *unchanged* ordinal and keeps working against the derived view — no edit.
- [x] 7.10 `world/rules/tests/test_sexual_event_self_arming.py` — lines ~32 and ~47: **found during apply
      review, missed by this task list's original grep pass** (D-6's "twenty sites" count also missed it).
      This file asserts the *ordinal* rose after `sexual_event:stimulus_applied` (`before =
      .arousal.value; assertGreater(.arousal.value, before)`); with pleasure `+8..+14` resolved from 0
      (FixedRng lower → +8), the ordinal stays `0` (`平靜`), so the old assertion would silently stop
      failing correctly. Rewrite both lines to read `actor.sexual.pleasure.value` instead — the test's
      intent is "the resolver applied a sexual mutation", which the gauge value proves directly.
- [x] 7.11 `world/rules/tests/test_action_pipeline_atomicity.py` — line ~63: **found during apply review,
      missed by the original grep pass.** D-6's "(or, once, an integer ordinal)" site: `setattr(
      entity.sexual.arousal, "value", 2)` is itself a direct write and must become
      `setattr(entity.sexual.pleasure, "base", 2)` before it runs. Line ~72's `assertEqual(.arousal.
      value, 0)` is a read-only check against the derived view and passes unchanged (rollback restored
      the original state, pleasure 0 → ordinal 0).
- [x] 7.12 `world/rules/tests/test_divine_mystery_gate.py` — lines ~101 and ~109: **found during apply
      review, missed by the original grep pass.** Same pattern as 7.10 — `before = target.sexual.
      arousal.value; assertGreater(...)` after a `divine_sexual_arts` cast whose `sexual_event:
      stimulus_applied` resolves to pleasure +8 from 0, ordinal stuck at 0. Rewrite both lines to
      `target.sexual.pleasure.value`. Lines ~137–140 (unmechanized mysteries, `assertEqual` of two
      derived reads) pass unchanged and must stay untouched.

## 8. New tests

- [x] 8.1 Band table: parametrised test asserting every `pleasure` value `0..100` maps to the
      documented `arousal` level, including boundary values `14/15`, `34/35`, `59/60`, `84/85`.
- [x] 8.2 `PleasureConfig` load-time validation: a malformed band table (gap, overlap, wrong count,
      not covering `0..100`) raises at load; a malformed multiplier table (missing/extra key,
      non-positive value) raises at load.
- [x] 8.3 Construction: the three `sexual-state-handler` ADDED-requirement scenarios (imported level
      → band floor; omitted arousal → floor 0; Monster with no baseline → floor 0).
- [x] 8.4 Bounds: the two `sexual-state-handler` ADDED-requirement clamp scenarios (delta exceeding
      100 clamps at 100; delta below 0 clamps at 0).
- [x] 8.5 Derived arousal: mid-band read, comparison operators, and that direct assignment
      (`entity.sexual.arousal.value = 3`) raises `AttributeError`.
- [x] 8.6 Decay: the three `sexual-state-handler` ADDED-requirement decay scenarios (mid-band decays
      to one-band-down; floor-band clamps at 0; a single interval never crosses more than one band
      even from the top of a band).
- [x] 8.7 **The D-4 regression, highest priority in this task list**: a test proving
      `wetness_follows_arousal` still fires when a `pleasure`-targeting rule's resolved delta crosses
      an arousal band boundary, and does **not** fire when the resolved delta stays within one band
      — the two `sexual-transition-rulebook` ADDED-requirement scenarios for `bounded_counter`.
- [x] 8.8 `climax_gate` regression: an `extreme_stimulus_applied` event still drives `climax_phase`
      from `未達` to `接近` within one `apply_event()` call, proving `when: {field: arousal, equals:
      極限}` conditions evaluate correctly against the derived view.
- [x] 8.9 Rewritten-rule tests: update the four existing `test_rule_arousal_up_on_stimulus` /
      `test_rule_arousal_up_on_sustained_stimulus` / `test_rule_arousal_extreme_stimulus_to_max` /
      `test_rule_arousal_reset_after_climax` functions in
      `world/rules/tests/test_sexual_transitions.py` to assert against `entity.sexual.pleasure.value`
      (exact deltas: `+8..+14`, `+6`, `set: 100`, `set: 15`) instead of `entity.sexual.arousal`'s
      ordinal. Function names stay unchanged — `test_every_rule_id_has_a_test()` matches by rule id,
      not by assertion content.
- [x] 8.10 **The D-7 regression, second-highest priority** — in
      `world/rules/tests/test_action_preview.py` (or `test_combat_modifiers.py`, wherever the
      existing no-create tests live): a test asserting `evaluate_combat_modifiers_no_create(entity)`
      reports `high_arousal_agility_accuracy_penalty`'s adjustment for a **materialized** entity whose
      `pleasure` has been raised at runtime past the `高度` floor — proving the preview path tracks
      live state, not the frozen import baseline — plus a companion test for an entity with no
      materialized handler at all, confirming the baseline-string fallback still works and that no
      `sexual_traits` Attribute is created by the call (pin both `combat-modifier-table` ADDED-
      requirement scenarios).
- [x] 8.11 **The D-7 regression, status side** — in `world/rules/tests/test_status_query.py`: a test
      asserting `build_status_read_model()`'s `conditions` include the sexual-threshold entry for a
      materialized, runtime-raised entity, and a second test asserting the entry **disappears** again
      once `pleasure` is reduced below the threshold on the same entity across two builds — pinning
      both `webclient-status-presentation` ADDED-requirement scenarios ("reflects live pleasure" and
      "disappears again"), plus a companion unmaterialized-baseline test mirroring 8.10's.
- [x] 8.12 Loader: `.nan` and `.inf` multiplier values raise at load (`math.isfinite` gate).
- [x] 8.13 **The `current`-channel invariant (rubber-duck finding):** `CounterTrait.value` is
      `(current + mod) * mult` and falls back to `base` only while no `"current"` key is stored — a
      single stray `.current` write would freeze the gauge and hide every later `.base` write.
      Pin it with (a) a behavior test: after a rule mutation and a `decay_tick`, raw `pleasure`
      storage contains no `"current"` key and `raw["base"] == entity.sexual.pleasure.value`, and
      (b) a source-inspection test: `sexual_transitions.py` contains no `.pleasure.current` and
      `decay_tick` contains no `.current` write.
- [x] 8.14 No-create readers reject a `bool` stored `base` (fail closed, no crash): preview returns
      no arousal-driven bundle, status shows no sexual-threshold entry.

## 9. Verification

- [x] 9.1 Run `uv run --locked python -m tools.spec_traceability list` and confirm the new
      requirement ids for `sexual-state-handler`'s four `ADDED Requirements`,
      `sexual-transition-rulebook`'s one `ADDED Requirement`, `combat-modifier-table`'s one `ADDED
      Requirement`, and `webclient-status-presentation`'s one `ADDED Requirement`; annotate every new
      test from sections 8 with `@covers_requirement(...)` using the literal ids.
- [x] 9.2 Confirm `test_field_kinds_covers_every_targetable_field()` and
      `test_every_rule_id_has_a_test()` (both pre-existing, generic, no hardcoded field/rule names)
      pass unmodified.
- [x] 9.3 Run the focused test modules:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.rules.tests.test_sexual_state world.rules.tests.test_sexual_transitions
      world.rules.tests.test_sexual_decay_and_reset world.rules.tests.test_monster_sexual_baseline
      world.rules.tests.test_combat_modifiers world.rules.tests.test_combat_modifiers_self_arming
      world.rules.tests.test_combat_modifiers_matched world.rules.tests.test_status_query
      world.rules.tests.test_status_boundary world.rules.tests.test_action_preview`.
- [x] 9.4 Run `uv run --locked python -m tools.spec_traceability check`.
- [x] 9.5 Run `openspec validate pleasure-gauge --strict`.
- [x] 9.6 Run the full non-browser suite once
      (`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput
      --parallel 16 commands server typeclasses world web.webclient`) to catch any further
      `entity.sexual.arousal.value =` call site this task list's grep pass missed, and any other
      raw-storage `"arousal"` key lookup section 6's grep pass may have missed.
