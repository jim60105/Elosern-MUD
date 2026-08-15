## 1. Shared cast-eligibility predicate

- [x] 1.1 Add `can_cast_skill(entity, skill) -> bool` to `world/rules/progression.py`: returns `True` when `spell_tier_for(skill)` is `None`; otherwise returns `can_cast_spell_tier(entity, skill.element.key, tier)`; converts any `ValueError` (malformed MP cost, unknown element, unknown tier) to `False`. Pure and side-effect-free, next to `can_cast_spell_tier`/`spell_tier_for` consumers
- [x] 1.2 Unit tests in `world/rules/tests/test_progression.py` covering: non-elemental skill passes; over-tier spell (`firestorm` at `magic_level=15`, empty affinities) returns `False`; mastery override returns `True`; fire-affinity boundary (`floor(15 * 1.1) == 16`) returns `True`; malformed MP cost and unknown element return `False`, never raise

## 2. ActionResolver adoption

- [x] 2.1 Replace the inline tier-gate block in `world/rules/action.py::_step1_ownership` with a call to `can_cast_skill`, raising `RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)` on `False`; update the module docstring/comment references to the shared predicate
- [x] 2.2 Verify `ElementTierCastGateTests` (`test_action_pipeline_rejections.py`) passes unchanged: under-tier rejection, numeric-level success, mastery success, malformed-cost fail-closed, and resolve-side parity

## 3. Monster policy adoption

- [x] 3.1 Delete `_gate_allows` in `world/rules/monster_behaviour.py` and call `world.rules.progression.can_cast_skill` from `_owned_damage_skills`; drop the now-unused `spell_tier_for`/`can_cast_spell_tier` imports if nothing else uses them
- [x] 3.2 Re-point the malformed-spell test's `patch` target in `test_monster_behaviour_policy.py::test_malformed_element_spell_is_denied_not_raised` to the shared predicate (or its `can_cast_spell_tier` call site in `world.rules.progression`) and confirm the patched-raising case still yields `basic_attack`; keep the tier-above-magic and mastery-override policy tests green unchanged

## 4. Generic NPC policy fix

- [x] 4.1 Add the `can_cast_skill` predicate to the candidate filter in `world/rules/combat.py::default_attack_policy` so a tier-blocked spell is skipped in favor of the next legal damage skill; import the predicate from `world.rules.progression`
- [x] 4.2 Policy-level test in `world/rules/tests/` (e.g. `test_initiative_and_turn_loop.py` or a new file): an NPC owning `skills=["firestorm"]` at `magic_level=15` with `mp>=30` (fixture must set `traits.mp = FakeGauge(30, 30)` so the affordability check passes, mirroring `test_default_policy_does_not_retry_an_unaffordable_skill`), no affinities, and no mastery gets an `ActionRequest` naming `basic_attack`; the same entity with `fire_mastery` gets `firestorm`; `ActionResolver` accepts the returned request
- [x] 4.3 `run_round` integration test using `monster_behaviour_policy` as the provider (the exact delegation path combat sessions use, `combat_session.py:485-491`): a party-style non-Monster companion owning only the blocked spell produces a resolved `EventLog` every round (no silently discarded rejection), and no `action_skipped` entry is emitted for it
- [x] 4.4 Run the affected suites: `world.rules.tests.test_progression`, `test_action_pipeline_rejections`, `test_monster_behaviour_policy`, `test_initiative_and_turn_loop`, `test_combat_party`, `test_combat_session`, and the full `world.rules` package

## 5. Traceability and handoff

- [x] 5.1 Add `covers_requirement` annotations for the two delta requirements (`element-mastery::can-cast-skill-...`, `monster-action-policy::a-delegated-non-monster-entity-...`) after the delta specs are synced into `openspec/specs/` at archive time; run `tools.spec_traceability check` before and after sync
- [x] 5.2 `openspec validate --change fix-npc-policy-cast-gate --strict` passes; `git diff --check` clean
