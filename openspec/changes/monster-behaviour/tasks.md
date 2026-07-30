## 1. Package layout and confirmations

- [ ] 1.1 Confirm `world/rules/` holds change 8's `action.py` (`ActionRequest`, `ActionResolver`),
      change 9's `combat.py` (`Battlefield`, `BattlefieldActionContext`, `effective_power`,
      `default_attack_policy`) and `dice.py` (`roll_d100`), and change 10's `overwhelm.py`
      (`resolve_overwhelm`); create `world/rules/monster_behaviour.py` and
      `world/rules/rulebook/monster_behaviour.yaml` as new files.
- [ ] 1.2 Confirm the exact import paths for `world.rules.combat.{Battlefield,
      BattlefieldActionContext, effective_power, default_attack_policy}`, `world.rules.dice.roll_d100`,
      `world.rules.action.{ActionRequest, ActionResolver}`, `world.rules.overwhelm.resolve_overwhelm`,
      `world.skills.registry.{SkillDef, SkillKind, TargetSpec, SKILL_REGISTRY}`, and
      `world.lore.monsters.MONSTER_TIER_REGISTRY` against how changes 2/5/8/9/10 actually landed — no
      code in this change should assume an unconfirmed symbol name before this step.
- [ ] 1.3 Confirm `typeclasses/monsters.py`'s actual `Monster.threat_tier`/`Monster.behaviour_tree`
      attribute shapes and placeholder default values against how change 3 actually landed, so
      `resolve_behaviour_profile()`'s "unset" check (task 3.2) tests the real placeholder value, not an
      assumed one.

## 2. Rulebook data (`world/rules/rulebook/monster_behaviour.yaml`)

- [ ] 2.1 Author `tier_default_archetype` per design.md D-2: one entry per `MONSTER_TIER_REGISTRY` key
      (`low`, `mid`, `high`, `calamity`), each mapped to an archetype key defined in task 2.2, with an
      inline comment naming the `world_info.md` examples that justify each mapping (point to design.md
      D-1/D-2/D-3, do not restate the full derivation).
- [ ] 2.2 Author the `archetypes` table per design.md D-2: `instinctive`, `pack_hunter`, `brute`,
      `tactical_caster`, `apex_predator`, each declaring `target_strategy`, `skill_choice`, and
      `prefer_area_when_multiple_enemies`.
- [ ] 2.3 Implement a small loader in `world/rules/monster_behaviour.py`
      (`MONSTER_BEHAVIOUR_YAML = yaml.safe_load(...)`), mirroring change 9's `COMBAT_YAML` and change
      10's `OVERWHELM_YAML` loader pattern exactly.
- [ ] 2.4 Test: every `tier_default_archetype` value exists as a key in `archetypes`; every
      `MONSTER_TIER_REGISTRY` key has exactly one `tier_default_archetype` entry; no two tiers share the
      same default archetype; at least one `archetypes` entry is not any tier's default (the named-example
      override slot, `tactical_caster`).

## 3. Behaviour profile resolution (`world/rules/monster_behaviour.py`)

- [ ] 3.1 Implement `BehaviourProfile` (frozen dataclass: `target_strategy: str`, `skill_choice: str`,
      `prefer_area_when_multiple_enemies: bool`) per design.md D-2.
- [ ] 3.2 Implement `resolve_behaviour_profile(monster) -> BehaviourProfile` per design.md D-1: reads
      `monster.behaviour_tree`, treating its change-3 placeholder ("unset") value as falsy; when set,
      looks it up directly in `MONSTER_BEHAVIOUR_YAML["archetypes"]`; when unset, looks up
      `MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][monster.threat_tier]` first.
- [ ] 3.3 Test: an unset `behaviour_tree` resolves to the correct tier default for each of the four
      tiers; a set `behaviour_tree` overrides the tier default; confirm no edit to
      `typeclasses/monsters.py` was made (`git diff` check against the pre-change tree).

## 4. Owned-skill discovery (`world/rules/monster_behaviour.py`)

- [ ] 4.1 Implement `_owned_damage_skills(entity) -> list[SkillDef]`: resolves
      `entity.skills.owned_keys()` through `SKILL_REGISTRY`, keeping `SkillKind.ACTIVE` entries whose
      `effects` contain at least one `damage:`-prefixed ID, preserving the entity's own owned-key order.
- [ ] 4.2 Implement `_damage_school(skill: SkillDef) -> str`: parses the skill's `damage:<school>
      [:<element>]`-shaped effect ID exactly as change 9's `_handle_damage` does, returning `"physical"`
      or `"magic"`.
- [ ] 4.3 Test: an entity owning a mix of `PASSIVE` and `ACTIVE` skills, and skills with and without a
      `damage:`-prefixed effect, yields exactly the `ACTIVE`+`damage:`-effect subset, in owned order; an
      entity owning zero such skills yields an empty list.

## 5. Living-enemy discovery (`world/rules/monster_behaviour.py`)

- [ ] 5.1 Implement `_living_enemies(battlefield, actor) -> list[LivingEntity]`: finds `actor`'s own
      team via `battlefield.team_of(actor.key)`, the other team's roster keys, filtered to
      `hp.value > 0` and not in `battlefield.fled` — mirroring change 10's own `_living_members()`
      pattern.
- [ ] 5.2 Test: a battlefield with one dead and one fled enemy on the opposing team yields only the
      remaining living, non-fled member(s); an actor whose own team has no opposing team members
      remaining yields an empty list.

## 6. Target and skill selection (`world/rules/monster_behaviour.py`)

- [ ] 6.1 Implement `_choose_target(entity, enemies, strategy) -> LivingEntity` per design.md D-3:
      `"lowest_hp"` sorts by current `hp.value`; `"highest_effective_power"` sorts by
      `combat.effective_power()` descending; an exact tie among the top-ranked candidates is broken via
      `tied[dice.roll_d100() % len(tied)]`, never `random`.
- [ ] 6.2 Implement `_choose_skill(entity, candidates, strategy, target) -> SkillDef` per design.md D-3:
      `"first_owned"` returns `candidates[0]`; `"highest_expected_damage"` compares
      `entity.skills.effective_value(attacking_stat)` (via task 4.2's school lookup), minus
      `target.skills.effective_value("defense")` when `target` is not `None`, breaking an exact tie the
      identical seeded way as task 6.1.
- [ ] 6.3 Test: `_choose_target()`'s two strategies each select the documented candidate on a roster with
      distinct values; an exact tie is broken reproducibly under a fixed seed via a `dice.roll_d100()`
      call (assert the call, not just the outcome); `_choose_skill()`'s two strategies each select the
      documented candidate; `highest_expected_damage` factors in the target's defense when a target is
      supplied and omits that term when `target is None` (the `AREA` case); no call to `random` or
      `random.choice` anywhere in either function (source-inspection or call-count assertion).

## 7. The decision tree and action_provider entry point (`world/rules/monster_behaviour.py`)

- [ ] 7.1 Implement `monster_behaviour_policy(entity, battlefield) -> ActionRequest | None` per
      design.md D-2/D-5: delegates to `combat.default_attack_policy(entity, battlefield)` when `entity`
      has no `threat_tier` attribute; otherwise finds living enemies (task 5.1, returning `None` if
      empty), resolves the behaviour profile (task 3.2), splits owned damage skills (task 4.1) into
      `SINGLE`/`AREA` groups, decides the area-vs-single shape per design.md D-2's exact rule (prefer
      area when configured AND >1 living enemy AND an area skill is owned; OR fall back to area when no
      single-target skill is owned at all), and builds the `ActionRequest` — `targets="all-enemies"` for
      the area branch, `targets=[chosen_target]` for the single branch — with
      `context=BattlefieldActionContext(battlefield)`. Returns `None` when no eligible damage skill
      exists in either group.
- [ ] 7.2 Confirm (grep-based check, mirroring changes 9/10's own discipline) that
      `world/rules/monster_behaviour.py` contains no reference to `combat_modifiers`,
      `evaluate_combat_modifiers`, `actions_per_turn`, `entity.buffs`, or `entity.sexual` — the
      zeroed-actions gate is entirely change 9's `run_round()`'s job, never duplicated here.
- [ ] 7.3 Confirm (grep-based check) that `world/rules/monster_behaviour.py` imports nothing from
      `world/ai/` and contains no reference to an LLM-client module or network call.

## 8. Tests

- [ ] 8.1 `world/rules/tests/test_monster_behaviour_profile.py` — per the `monster-behaviour-profile`
      capability: task 2.4's and task 3.3's assertions.
- [ ] 8.2 `world/rules/tests/test_monster_behaviour_selection.py` — per the `monster-action-policy`
      capability's target/skill-selection requirements: task 4.3's, 5.2's, and 6.3's assertions.
- [ ] 8.3 `world/rules/tests/test_monster_behaviour_policy.py` — per the `monster-action-policy`
      capability's decision-tree requirements: the area-vs-single decision's four named scenarios (area
      preferred and multiple enemies present; single enemy suppresses the area branch even when
      preferred; no single-target skill owned falls back to area even when not preferred; no eligible
      skill at all returns `None`); a non-`Monster` entity (no `threat_tier`) produces the exact value
      `combat.default_attack_policy()` would for identical arguments, and `default_attack_policy` is
      confirmed not called at all when `entity` does have `threat_tier` (mock or call-count assertion).
- [ ] 8.4 `world/rules/tests/test_monster_behaviour_determinism.py` — per hard requirement 2 and the
      `monster-action-policy` capability: repeated calls with no intervening `roll_d100()` call and no
      entity/battlefield state change produce identical `ActionRequest`s; the source-scan assertions from
      tasks 7.2/7.3.
- [ ] 8.5 `world/rules/tests/test_monster_behaviour_golden.py` — per the golden fixed-seed requirement:
      construct one battlefield with a distinct low-hp/low-power enemy and a distinct high-hp/high-power
      enemy; run a `low`-tier-default and a `calamity`-tier-default `Monster` against that identical
      roster under the same fixed seed; assert the `low`-tier monster targets the low-hp enemy and the
      `calamity`-tier monster targets the high-power enemy; assert the full decision sequence is
      byte-identical across two runs under the same seed.
- [ ] 8.6 `world/rules/tests/test_monster_behaviour_integration.py` — per the drop-in `action_provider`
      requirement: `combat.run_round(battlefield, monster_behaviour_policy)` completes and produces the
      expected `EventLog` for a `Monster`'s turn; `overwhelm.resolve_overwhelm(battlefield,
      monster_behaviour_policy, max_rounds)` completes and returns a valid `OverwhelmResult`; a
      zeroed-`actions_per_turn` fixture (reusing change 9's own `combat_modifiers`-driven test pattern)
      confirms `monster_behaviour_policy` is never invoked for that combatant's turn and an
      `"action_skipped"` entry appears instead.

## 9. Verification

- [ ] 9.1 Run the full `world/rules/tests/` suite added by this change and confirm every test passes.
- [ ] 9.2 Confirm this change modifies no file authored by any earlier change — `git diff --stat` against
      the pre-change tree shows only new files under `world/rules/monster_behaviour.py`,
      `world/rules/rulebook/monster_behaviour.yaml`, and `world/rules/tests/`.
- [ ] 9.3 Confirm change 9's own test suites (`test_golden_combat.py`, `test_initiative_and_turn_loop.py`)
      and change 10's own test suites still pass unmodified — this change never edits `combat.py`,
      `dice.py`, `overwhelm.py`, or either's `rulebook/*.yaml`.
- [ ] 9.4 Confirm change 8's own no-combat-branching tripwire suite (`test_no_combat_branching.py`) still
      passes unmodified — this change never touches `action.py`, `targeting.py`, or `event_log.py`.
- [ ] 9.5 Run `openspec validate monster-behaviour --strict` and confirm it passes.
