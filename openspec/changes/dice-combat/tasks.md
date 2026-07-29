## 1. Package layout and confirmations

- [ ] 1.1 Confirm `world/rules/` holds change 8's `action.py`/`targeting.py`/`event_log.py`, change 6's
      `rulebook/schema.py`/`combat_modifiers.py`/`buffs.py`, and change 5's `world/skills/handler.py`;
      create `world/rules/dice.py`, `world/rules/combat.py`, and `world/rules/rulebook/combat.yaml` as
      new files.
- [ ] 1.2 Confirm the exact import paths for `world.rules.action.{ActionResolver, ActionRequest,
      ActionResult, RejectReason, PendingEffect, register_effect_handler, SNAPSHOTTED_SURFACES}`,
      `world.rules.targeting.{ActionContext, Relation}`, `world.rules.buffs.{tick_buffs,
      blocks_action}`, `world.rules.combat_modifiers.evaluate_combat_modifiers`, and
      `world.skills.handler.SkillHandler.effective_value` against how changes 5/6/8 actually landed —
      no code in this change should assume an unconfirmed symbol name before this step.
- [ ] 1.3 Confirm `evennia.contrib.rpg.dice.roll()`'s exact call signature and whether it exposes a
      seed/RNG-injection parameter, per design.md D-1.

## 2. Dice roller (`world/rules/dice.py`)

- [ ] 2.1 Implement `roll_d100() -> int` wrapping `evennia.contrib.rpg.dice.roll()`, per design.md D-1.
- [ ] 2.2 Confirm reproducibility under a fixed seed (Python's `random.seed()` if the contrib exposes no
      first-class seed parameter) — this is the mechanism the golden tests (task 8) depend on.

## 3. Rulebook data (`world/rules/rulebook/combat.yaml`)

- [ ] 3.1 Author `to_hit.defender_constant: 51` with the design.md D-2 derivation referenced in an
      inline YAML comment (not restated in full — point to design.md).
- [ ] 3.2 Author `damage.{crit_multiplier, solid_hit_margin, solid_hit_multiplier, base_multiplier,
      floor}` per design.md D-3, flagged inline as invented placeholder values.
- [ ] 3.3 Author `initiative.agility_weight: 10` per design.md D-8.
- [ ] 3.4 Author `round.seconds: 6` per design doc §6.3.
- [ ] 3.5 Implement a small loader in `world/rules/combat.py` (`COMBAT_YAML = yaml.safe_load(...)`) —
      this file is flat tunable data, not a `when`/`then` rule table, so it does NOT go through change
      6's `rulebook/schema.py` loader.

## 4. To-hit and damage (`world/rules/combat.py`)

- [ ] 4.1 Implement `_apply_percent_mod(base: float, pct: str | None) -> float` parsing
      `combat_modifiers.yaml`-style percentage strings (e.g. `"-20%"`) against a base value, returning
      `base` unchanged when `pct` is `None`.
- [ ] 4.2 Implement the to-hit calculation exactly as design.md D-2/D-5 specify: `roll_d100() +
      attacker_effective_agility (adjusted) + accuracy_modifier >= COMBAT_YAML["to_hit"]
      ["defender_constant"] + defender_effective_agility (adjusted)`. No natural-roll override on the
      hit/miss determination (design.md D-2's explicit rejection of that alternative).
- [ ] 4.3 Implement `_roll_multiplier(raw_roll: int, margin: int) -> float` per design.md D-3: returns
      `crit_multiplier` if `raw_roll == 100`, else `solid_hit_multiplier` if `margin >=
      solid_hit_margin`, else `base_multiplier`.
- [ ] 4.4 Implement the damage number: `max(round(effective_attack_stat * roll_multiplier) -
      effective_defense, COMBAT_YAML["damage"]["floor"])`, computed only when the to-hit check passed.

## 5. effective_power (`world/rules/combat.py`)

- [ ] 5.1 Implement `effective_power(entity) -> float` per design.md D-4: sum of
      `entity.skills.effective_value()` for `atk_phys`/`agility`/`defense`/`magic_level`, multiplied by
      `max(entity.traits.hp.value, 0)`. Confirm it assigns to no entity attribute (pure query, mirroring
      change 5's `effective_value()` and change 6's `evaluate_combat_modifiers()` discipline).
- [ ] 5.2 Construct the four worked reference cases from design.md D-4 (human elite, elf, mid-tier
      monster, high-tier monster vs. sword-master) as fixtures reusable by both this task group's tests
      and the golden tests (task 8).

## 6. BattlefieldActionContext (`world/rules/combat.py`)

- [ ] 6.1 Implement `Battlefield` (frozen or plain dataclass): `teams: dict[str, frozenset[str]]`
      (exactly two team keys), `roster: dict[str, LivingEntity]`, `fled: set[str]`, and
      `team_of(key) -> str | None`, per design.md D-6.
- [ ] 6.2 Implement `BattlefieldActionContext` conforming to `world.rules.targeting.ActionContext`:
      `battlefield` (always the real `Battlefield`, never `None`), `is_present()`, `relation_to()`
      (`SELF`/`ALLY`/`ENEMY` from team membership), `is_in_range()` per design.md D-7 (returns `False`
      for any target in `battlefield.fled`, `True` otherwise — melee-vs-ranged explicitly not built,
      documented inline with a docstring pointing to design.md D-7's reasoning).
- [ ] 6.3 Confirm `expand_target_shorthand()` (change 8, unmodified) resolves `"all-enemies"`/
      `"all-allies"`/`"all"` correctly against `Battlefield.teams` with zero edit to `targeting.py`.

## 7. damage:* effect handler (`world/rules/combat.py`)

- [ ] 7.1 Implement `_handle_damage(actor, targets, effect_id, event_context) -> list[PendingEffect]`
      per design.md D-5: parses `effect_id` as `damage:<school>[:<element>]`; for each target, computes
      the raw roll, the to-hit determination (task 4.2), and — only if hit — the damage number (task
      4.4) entirely within this function (staging), never inside the `PendingEffect.apply` closure.
- [ ] 7.2 Implement `_apply_hp_delta(entity, delta) -> None`: the only mutator any `PendingEffect.apply`
      from this handler calls, writing through `entity.traits.hp.value`.
- [ ] 7.3 Call `register_effect_handler("damage", _handle_damage, surfaces=frozenset({"traits"}))` at
      module import time — confirm it raises no `UnsnapshottedSurfaceError` (traits is already in
      change 8's `SNAPSHOTTED_SURFACES`).
- [ ] 7.4 Confirm every stat `_handle_damage` reads (`atk_phys`/`magic_level`, `agility`, `defense`)
      goes through `entity.skills.effective_value()`, never `entity.traits.<key>.value` directly (hard
      requirement 3) — a grep-based check mirroring change 5's own D-5 tripwire discipline.
- [ ] 7.5 Confirm `evaluate_combat_modifiers()` is read for both the acting entity and each target, and
      that no conditional in `_handle_damage` branches on which rule (poison vs. arousal vs. fear)
      produced an `agility`/`accuracy` adjustment — only the bundle's output keys are consulted.

## 8. Initiative and the turn loop (`world/rules/combat.py`)

- [ ] 8.1 Implement `roll_initiative(battlefield) -> list[str]` per design.md D-8.
- [ ] 8.2 Implement `default_attack_policy(entity, battlefield) -> ActionRequest | None` per design.md
      D-9: the explicitly-labeled placeholder action provider (selects the lowest-hp living, non-fled
      enemy; returns `None` if the entity owns no `damage:*`-effect skill). Docstring names this as a
      placeholder for `Monster.behaviour_tree` (change 3's unbuilt seam), not production AI.
- [ ] 8.3 Implement `run_round(battlefield, action_provider) -> list[EventLog]` per design.md D-9: for
      each roster key in initiative order, skip dead/fled entities; read
      `evaluate_combat_modifiers(entity)`, skip the turn (emitting an `"action_skipped"` `EventLog`,
      never calling `ActionResolver.resolve()`) if `actions_per_turn == 0`; otherwise call
      `action_provider(entity, battlefield)` and, if it returns a request, call
      `ActionResolver.resolve()` and collect the resulting `EventLog` on success.
- [ ] 8.4 Implement `_end_of_round_upkeep(battlefield) -> None`: calls `tick_buffs(entity)`
      unconditionally (hard dependency, no self-arming) and `_try_sexual_decay(entity)` (self-arming,
      lazy `world.rules.sexual_transitions.decay_tick` import, degrading to a no-op on `ImportError`)
      for every living roster member.
- [ ] 8.5 Implement `is_battle_over(battlefield) -> bool` (or equivalent): a side with zero living,
      non-fled members ends the battle.
- [ ] 8.6 Implement `run_battle(battlefield, action_provider, max_rounds) -> BattleResult` per design.md
      D-9: loops `run_round()` until `is_battle_over()` or `max_rounds`, accumulates every round's
      `EventLog`s, and returns `total_seconds = rounds_elapsed * COMBAT_YAML["round"]["seconds"]`.
      Confirm no call anywhere in this function resembles `WorldClock.advance()`.

## 9. Tests

- [ ] 9.1 `world/rules/tests/test_dice.py` — `roll_d100()` stays in `[1, 100]`; reproducibility under a
      fixed seed; per the `dice-roller` capability.
- [ ] 9.2 `world/rules/tests/test_to_hit_calibration.py` — per the `combat-resolution` capability's
      to-hit requirement: exact-parity hit rate is 50% (statistical, large-N); the seven matchups from
      the task brief (human elite vs. human elite, human novice vs. low monster, human elite vs. mid
      monster, sword-master vs. high monster, elf vs. human elite both directions, elf vs. elf) produce
      the exact ranges design.md D-2's final table states; a 48+ point agility gap saturates fully in
      both directions; a natural 100 does not override a saturated miss.
- [ ] 9.3 `world/rules/tests/test_damage_bands.py` — per the damage-multiplier requirement: bare hit,
      solid hit, and natural-100 critical bands each produce the documented multiplier; the floor
      applies when the raw subtraction is non-positive; a miss applies no damage and no floor.
- [ ] 9.4 `world/rules/tests/test_effective_power.py` — per the `effective_power` requirement: reads
      through `effective_value()` (a multiplier-active fixture proves this); the elf/human-elite ratio
      is at least 100; the mid-tier-monster/human-elite ratio is greater than 1 but well below 100;
      `effective_power()` strictly decreases as current hp drops (not at zero); a dead entity (`hp ==
      0`) returns exactly `0`.
- [ ] 9.5 `world/rules/tests/test_battlefield_action_context.py` — per the `battlefield-action-context`
      capability: full protocol conformance; `relation_to()`'s three-way truth table over team
      membership; `is_present()`/`is_in_range()` both keyed on `battlefield.fled`; the out-of-range
      rejection reaches `ActionResolver.resolve()` and produces `RejectReason.TARGET_OUT_OF_RANGE`
      end-to-end; `expand_target_shorthand()`'s `all-enemies`/`all-allies` resolve correctly against
      `Battlefield.teams` with no edit to `targeting.py`.
- [ ] 9.6 `world/rules/tests/test_damage_effect_handler.py` — per the `damage-effect-handlers`
      capability: a `damage:*`-effect skill no longer rejects `UNKNOWN_EFFECT_ID` once
      `world/rules/combat.py` is imported; the registration declares exactly `{"traits"}`; a request
      staged successfully but rejected at a later step leaves every target's `hp` unchanged even though
      a roll was already consumed; `apply()` performs no randomness call; combat-modifier adjustments
      apply with no branch on rule origin.
- [ ] 9.7 `world/rules/tests/test_initiative_and_turn_loop.py` — per the initiative and turn-loop
      requirements: a 10+ point agility gap guarantees order across every roll pair; a smaller gap can
      be reordered by at least one roll pair; `actions_per_turn: 0` skips a turn without calling
      `ActionResolver.resolve()` and emits an `"action_skipped"` entry; `tick_buffs()` runs
      unconditionally every round; sexual decay is a no-op while `sexual_transitions` doesn't exist and
      a guarded, `pytest.importorskip`-style companion test proves it fires once that module exists
      (expected to report **skipped** at this point in the roadmap).
- [ ] 9.8 `world/rules/tests/test_golden_combat.py` — per design.md D-10: the normal-exchange golden
      case (fixed seed, exact hit/miss/damage sequence assertion) and the lopsided-exchange golden case
      (fixed seed, full saturation across every round of the fixture); both assert `total_seconds ==
      rounds_elapsed * 6`.

## 10. Verification

- [ ] 10.1 Run the full `world/rules/tests/` suite added by this change and confirm every test passes,
      except `test_initiative_and_turn_loop.py`'s guarded sexual-decay integration test, which is
      expected to report **skipped** (before changes 7/7b land).
- [ ] 10.2 Confirm `world/rules/combat.py` never calls `WorldClock.advance()` or anything resembling it
      (grep-based check).
- [ ] 10.3 Confirm `register_effect_handler` is the only way `world/rules/combat.py` registers into
      change 8's effect-handler registry — no direct write to `_EFFECT_HANDLERS`/
      `_EFFECT_HANDLER_SURFACES` (grep-based check, mirroring change 8's own task 8.5 discipline).
- [ ] 10.4 Confirm this change modifies no file authored by any earlier change — `git diff --stat`
      against the pre-change tree shows only new files under `world/rules/dice.py`,
      `world/rules/combat.py`, `world/rules/rulebook/combat.yaml`, and `world/rules/tests/`.
- [ ] 10.5 Confirm change 8's own no-combat-branching tripwire test suite
      (`test_no_combat_branching.py`) still passes unmodified — this change never edits
      `action.py`/`targeting.py`/`event_log.py`, so no new branch can have been introduced there.
- [ ] 10.6 Run `openspec validate dice-combat --strict` and confirm it passes.
