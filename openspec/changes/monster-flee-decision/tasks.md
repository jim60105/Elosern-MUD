## 1. Rulebook profile extension and validation

- [ ] 1.1 Add `flee_hp_fraction` to every archetype in
      `world/rules/rulebook/monster_behaviour.yaml`, using YAML `null` for archetypes that never
      voluntarily flee and keeping all concrete threshold values out of Python.
- [ ] 1.2 Add `flee_hp_fraction: float | None` to the frozen `BehaviourProfile`.
- [ ] 1.3 Define `MonsterBehaviourConfigError(ValueError)` with stable prefix
      `invalid monster behaviour rulebook:` and add focused profile-table validation before
      `BEHAVIOUR_PROFILES` construction for mapping shape, exact required fields, tier-default
      references, strategy enums, boolean area preference, and nullable real-number flee fractions
      in inclusive range `[0.0, 1.0]`.
- [ ] 1.4 Test every shipped archetype and tier default, including that null disables flight and
      booleans, strings, out-of-range values, missing fields, and unknown references fail loudly.
- [ ] 1.5 Test that an instance `behaviour_tree` override changes the flee threshold without changing
      the monster's tier or any persistent state.

## 2. Deterministic flee decision branch

- [ ] 2.1 Add a focused predicate that reads `combat._stored_hp()` and `combat._max_hp()`, guards a
      non-positive maximum, and uses the inclusive current/max comparison from design D-2.
- [ ] 2.2 Insert the flee predicate after non-monster delegation and living-enemy discovery but before
      damage-skill enumeration, area/target/skill selection, or seeded tie-breaking.
- [ ] 2.3 Import 10c's `FLEE_SKILL_KEY` from `world.rules.disengage` and return a self-targeted
      `ActionRequest` using that constant with
      `BattlefieldActionContext(battlefield, event_context={"battlefield": battlefield})`.
- [ ] 2.4 Test exact-boundary selection, above-threshold attack preservation, below-threshold
      selection, null disabling, and the non-positive-maximum guard.
- [ ] 2.5 Test that a threshold-triggered monster can flee with no affordable damage skill, calls no
      policy `roll_d100()`, and returns `None` rather than flee when no living enemy remains.
- [ ] 2.6 Test the existing non-monster delegation path and every above-threshold 10b target,
      skill-choice, area-choice, and fixed-seed golden test unchanged.
- [ ] 2.7 Test that evaluating the branch leaves HP gauge backing data, `Battlefield.fled`, traits,
      sexual state, buffs, skill grants, inventory, and currency unchanged.

## 3. Resolver and combat integration

- [ ] 3.1 Add a focused request-shape test for actor, self target, `"flee"` skill key, targeting
      battlefield, and `event_context["battlefield"]` identity.
- [ ] 3.2 Add a fresh-interpreter import test proving importing `world.rules.monster_behaviour`
      alone loads 10c's `FLEE_SKILL_KEY`, skill definition, and effect handler, and that the generated
      request does not reject as `UNKNOWN_SKILL`.
- [ ] 3.3 Test a successful fixed-roll flee through `run_round()` and `ActionResolver`: the monster
      attacks no target, enters `Battlefield.fled`, emits 10c's EventLog, and is excluded from later
      turns, targeting, and team-power aggregation.
- [ ] 3.4 Test a failed fixed-roll flee through `run_round()`: the monster remains in the battlefield,
      attacks no target that turn, and emits 10c's failed-attempt EventLog.
- [ ] 3.5 Test `resolve_overwhelm()` with the same policy: no special branch is added to
      `overwhelm.py`, and a successful flee affects the next existing reclassification.
- [ ] 3.6 Add fixed-state/fixed-dice golden cases for each tier-default archetype and at least one
      per-instance override, proving reproducible flee-versus-attack decisions and outcomes.

## 4. Architectural regression and validation

- [ ] 4.1 Add source-scan assertions that monster behaviour imports no `world.ai`, performs no
      network or direct Python-random call, contains no shipped flee threshold literal, and never
      mutates `Battlefield.fled` or calls `ActionResolver.resolve()`.
- [ ] 4.2 Run all 10b monster-behaviour and 10c combat-disengage focused tests together and resolve
      regressions without changing their ownership boundaries.
- [ ] 4.3 Run `uv run --locked evennia test --settings settings.py .`.
- [ ] 4.4 Run `uv run --locked -m unittest discover tests` and
      `uv run --locked python -m compileall -q world typeclasses commands server`.
- [ ] 4.5 Run `openspec validate monster-flee-decision --strict` and `git diff --check`.
