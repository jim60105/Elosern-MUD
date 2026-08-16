## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `world/skills/sexual_acts/interspecies.py` still ships `INTERSPECIES_ACTS = ()`,
  pre-declared and empty, from `sexual-act-seeds`.
- [x] 1.2 Confirm `world/rules/sexual_state.py`'s `hostile_act_count`/`climax_count`/
  `interspecies_act_count` and their sole mutators (`record_hostile_act`, `record_climax_count`,
  `record_interspecies_act`) are unchanged, and that `climax_count` is credited only by the
  climax-settlement clock, never by an act's own `actor_counters`.
- [x] 1.3 Confirm `_act_family()`'s `_PARLESS_LINES = ("異種", "神之秘法")` check and its rejection of
  any 異種-line row declaring a non-`None` `target_part` are unchanged — every row in this change
  depends on `target_part=None` being the only accepted value.
- [x] 1.4 Confirm `resolve_part`'s `Monster` collapse to `GENERIC_BODY_PART` (`world/rules/
  sexual_act_effects.py`) is unchanged.
- [x] 1.5 Confirm `world/rules/rulebook/sexual.yaml`'s `experience_interspecies_added` row
  (`when: {event: sexual_activity_with_nonhuman}` → `then: {field: experience_types, add: 異種性愛}`)
  is unchanged. If its event name differs at implementation time, update `interspecies_mating`'s
  `sexual_events` tuple accordingly before writing any row.
- [x] 1.6 Confirm `_handle_sexual_event`'s target-only application (`world/rules/action.py`) is still
  the case, and confirm whether `sexual-catalog-partner` (C4)'s disclosed D-3 gap has been fixed by
  any intervening proposal. If fixed, update design.md D-4 and this change's tests to assert the
  corrected (actor-inclusive) behavior instead of the currently-shipped one.

## 2. `world/skills/sexual_acts/interspecies.py`: Tier 1 (two acts)

- [x] 2.1 Replace the empty `INTERSPECIES_ACTS = ()` with a `_act_family("異種", ...)` call
  containing the two Tier 1 rows from design.md D-1 (`interspecies_touch`, `interspecies_caress`),
  each `unlock={"hostile_act_count": 10}`, `target_spec=TargetSpec.SINGLE`, `target_part=None`,
  `actor_counters=("interspecies_act_count",)`, `participant_counters=()`, `sexual_events=()`,
  `resistible=True`.

## 3. `world/skills/sexual_acts/interspecies.py`: Tier 2 (two acts)

- [x] 3.1 Add `interspecies_entangle` (`unlock={"hostile_act_count": 30}`, `actor_part="腰腹"`,
  `base_pleasure=18`, `actor_pleasure_ratio=0.7`, otherwise matching Tier 1's shape).
- [x] 3.2 Add `interspecies_receive` (same unlock, `actor_part="私處"`, `base_pleasure=18`,
  `actor_pleasure_ratio=0.9`).

## 4. `world/skills/sexual_acts/interspecies.py`: Tier 3 (one act)

- [x] 4.1 Add `interspecies_mating` (`unlock={"hostile_act_count": 30, "climax_count": 20}`,
  `actor_part="私處"`, `base_pleasure=26`, `actor_pleasure_ratio=0.7`,
  `sexual_events=("sexual_activity_with_nonhuman",)`, otherwise matching Tier 1's shape).

## 5. `world/skills/sexual_acts/interspecies.py`: Tier 4 (two acts)

- [x] 5.1 Add `interspecies_domination` (`unlock={"interspecies_act_count": 20}`, `actor_part="大腿"`,
  `base_pleasure=22`, `actor_pleasure_ratio=0.6`, otherwise matching Tier 1's shape).
- [x] 5.2 Add `interspecies_resonance` (same unlock, `actor_part="乳房"`, `base_pleasure=22`,
  `actor_pleasure_ratio=0.6`).

## 6. Behaviour tests for the delta spec

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-interspecies::*` from this change's delta spec.
- [x] 6.2 Add `world/skills/sexual_acts/tests/test_interspecies_catalog.py` (new `EvenniaTest`-based
  module, using a `Monster` fixture as the target) covering each delta-spec scenario: a Tier 1 act
  absent below threshold and present at it; `interspecies_mating`'s compound gate; a Tier 4 act gated
  by `interspecies_act_count` alone; every act crediting `interspecies_act_count` on the actor only,
  never on the `Monster` target; every act's `target_part` reading `None` and its cast against a
  `Monster` resolving to `GENERIC_BODY_PART`; `interspecies_mating` emitting
  `sexual_activity_with_nonhuman` and no other new act naming that event; `interspecies_receive`'s
  `actor_pleasure_ratio` (`0.9`) exceeding all six sibling acts'; `compute_pleasure_gain`'s
  worst-case (`普通` sensitivity, `強烈` shame, `participant_count == 2`) comparison between
  `interspecies_mating` and `interspecies_receive`, confirming the same-body-part (私處) actor-value
  ordering across Tiers 2→3 holds even in the worst case (design.md D-1's corrected margin).
- [x] 6.3 Add one test (not in the delta spec, a design.md D-4 regression) proving
  `interspecies_mating`'s cast currently credits `異種性愛` to the `Monster` target's
  `experience_types`, not the actor's — pinning the presently-shipped, disclosed gap so a future
  `_handle_sexual_event` fix is a deliberate, visible behavior change rather than a silent one.
- [x] 6.4 Apply `covers_requirement("sexual-catalog-interspecies::<id>")` (using the IDs from 6.1) to
  each test function whose assertions establish that requirement.
- [x] 6.5 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-interspecies` requirement is covered.

## 7. Full verification

- [x] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-seven-row `INTERSPECIES_ACTS`
  tuple.
- [x] 7.2 Run `uv run --locked python -m compileall -q world`.
- [x] 7.3 Run `openspec validate sexual-catalog-interspecies --strict` and resolve any reported
  issue.
- [x] 7.4 Confirm no file outside `world/skills/sexual_acts/interspecies.py` and the new
  `world/skills/sexual_acts/tests/test_interspecies_catalog.py` was touched, matching the proposal's
  Impact list exactly — in particular, confirm `world/rules/action.py` and `world/rules/rulebook/
  sexual.yaml` both have zero diff from this change.
