## 1. `flee` SkillDef and universal ownership

- [ ] 1.1 Add `INNATE_SKILL_KEYS = frozenset({"flee"})` to `world/skills/handler.py`, with a module
      comment attributing it to change 10c (`combat-disengage`) and its rationale.
- [ ] 1.2 Add `INNATE_SKILL_KEYS`'s members to `SkillHandler.owned_keys()`'s returned list (one
      additive line; existing `active`/`passive` reads untouched).
- [ ] 1.3 Test: `owned_keys()` includes `"flee"` for an entity with `entity.db.skills` unset, for an
      entity with a populated skill list, and for a bare `Monster` instance with no bestiary data.
- [ ] 1.4 Test: `owned_keys()` includes `"flee"` identically whether or not the entity is currently a
      `Battlefield` roster member (no combat-state dependency).
- [ ] 1.5 Test: `world/skills/handler.py` has no import from `world.rules.*`; `world/rules/
      disengage.py` imports `INNATE_SKILL_KEYS` from `world.skills.handler`.
- [ ] 1.6 Create `world/rules/disengage.py`; declare `FLEE_SKILL_KEY = "flee"` and register its `SkillDef`
      (`target_spec=SELF`, `faction_constraint=SELF_ONLY`, `cost={}`, `usable_out_of_combat=False`,
      `effects=["disengage:self"]`) into `world.skills.registry.SKILL_REGISTRY`.
- [ ] 1.7 Test: casting `flee` outside combat (`ActionContext.battlefield is None`) rejects with
      `SKILL_NOT_USABLE_OUT_OF_COMBAT` via the existing, unmodified step-1 gate.
- [ ] 1.8 Test: casting `flee` for a dead actor rejects with `TARGET_DEAD`; for an already-fled actor
      rejects with `TARGET_NOT_PRESENT` — both via the unmodified four-validation targeting path.
- [ ] 1.9 Test: `flee`'s resource check always passes regardless of the actor's current mp/sp (cost is
      `{}`).
- [ ] 1.10 Test: a successful `flee` resolution reports `time_cost_seconds == DEFAULT_CAST_SECONDS`
      (6), confirming no `SKILL_TIME_OVERRIDES` entry was added.

## 2. The disengage effect handler and the flee-success formula

- [ ] 2.1 Implement `_adjusted_agility(entity)`: `effective_value("agility")` adjusted by
      `evaluate_combat_modifiers(entity)`'s `agility` percentage only (never `accuracy`).
- [ ] 2.2 Implement `_fastest_pursuer_agility(battlefield, actor)`: greatest `_adjusted_agility()`
      among every living, non-fled member of the opposing team; returns `None` if none remain.
- [ ] 2.3 Implement `_attempt_flee(actor, battlefield)`: `roll_d100() + actor_agility >=
      combat.COMBAT_YAML["to_hit"]["defender_constant"] + pursuer_agility`; automatic success (no
      roll) when `_fastest_pursuer_agility()` returns `None`.
- [ ] 2.4 Implement `_handle_disengage(actor, targets, effect_id, event_context)`: reads
      `event_context["battlefield"]` (raising `EFFECT_RESOLUTION_FAILED` naming the missing key if
      absent); stages one `PendingEffect` whose `entity` field is the `Battlefield`, `apply` adding
      the actor's key to `battlefield.fled` on success or a no-op on failure.
- [ ] 2.5 Register the handler: `register_effect_handler("disengage", _handle_disengage,
      surfaces=frozenset({"battlefield"}))`.
- [ ] 2.6 Test (statistical): 10,000 fixed-seed trials at exact agility parity land within tolerance
      of a 50% success rate.
- [ ] 2.7 Test (saturation): an agility gap of 50 or more in either direction produces an exact 0% or
      100% success rate across every seed tried.
- [ ] 2.8 Test (the hard-requirement proof): a human-elite-tier fleeing entity (agility ~9) against an
      elf-tier pursuer (agility ~92) has exactly 0% escape rate; the reverse pairing has exactly 100%.
      Assert no branch in `disengage.py` reads `effective_power()`, `classify_overwhelm()`, or any
      overwhelm-ratio concept.
- [ ] 2.9 Test: the comparison uses the single fastest living, non-fled opposing member, not an
      average, across a fixture with mixed-agility opponents.
- [ ] 2.10 Test: `_adjusted_agility()` never reads the `accuracy` key of `evaluate_combat_modifiers()`'s
      bundle (source inspection + behavioral test with an accuracy-only modifier fixture).
- [ ] 2.11 Test: with every opposing team member dead or fled, the attempt succeeds without calling
      `roll_d100()`.
- [ ] 2.12 Test: a missing `"battlefield"` key in `event_context` rejects with
      `EFFECT_RESOLUTION_FAILED`, no exception escaping, no state mutated.
- [ ] 2.13 Test: a successful flee adds the actor's key to `battlefield.fled`; a failed attempt leaves
      it absent and leaves every entity's `traits`/`sexual`/`buffs`/`skill_grants` untouched.
- [ ] 2.14 Test: both outcomes produce a real `EventLog` with a `"disengage_attempt"`-kind entry
      recording `success`, `roll`, `actor_agility`, and `pursuer_agility`.

## 3. Extending ActionResolver's atomicity mechanism

- [ ] 3.1 Add `"battlefield"` to `world/rules/action.py`'s `SNAPSHOTTED_SURFACES`.
- [ ] 3.2 Implement `_is_battlefield_like(obj)` (duck-typed: `hasattr(obj, "fled") and hasattr(obj,
      "roster")`) — no import of `world.rules.combat.Battlefield`.
- [ ] 3.3 Implement `_snapshot_touched(obj)`/`_restore_touched(obj, snapshot)`, dispatching to a new
      battlefield-shaped branch (snapshotting/restoring exactly `.fled`) or the existing, unmodified
      per-entity `_snapshot_entity_state()`/`_restore_entity_state()` path.
- [ ] 3.4 Redirect `_commit()`'s existing snapshot/restore call sites through the two new dispatch
      functions; confirm `_commit()`'s own control flow is otherwise unchanged.
- [ ] 3.5 Test: `register_effect_handler("disengage", ..., surfaces=frozenset({"battlefield"}))`
      succeeds without raising `UnsnapshottedSurfaceError`.
- [ ] 3.6 Test: `register_effect_handler()` still raises `UnsnapshottedSurfaceError` for a surface
      outside `{"traits", "sexual", "buffs", "skill_grants", "battlefield"}` (e.g. `"inventory"`).
- [ ] 3.7 Test: a commit involving one `Battlefield`-shaped `PendingEffect` and one ordinary-entity
      `PendingEffect` in the same call snapshots each correctly via its own dispatch branch.
- [ ] 3.8 Test: `world/rules/action.py` contains no `isinstance(..., Battlefield)` check and no import
      of `world.rules.combat.Battlefield`.
- [ ] 3.9 Test (rollback proof): a commit staging a successful disengage effect followed by a second,
      synthetic effect whose `apply()` raises results in `COMMIT_FAILED` and an unchanged
      `battlefield.fled` (the disengage mutation is reversed).
- [ ] 3.10 Re-run action-resolver's own pre-existing atomicity test suite (all eight fault-injection
      scenarios, the three-effects-second-raises test) unmodified; confirm all still pass.
- [ ] 3.11 Re-run action-resolver's own no-combat-branching tripwire tests (forbidden-token scan,
      signature scan, the positive polymorphism proof) unmodified against the edited `action.py`;
      confirm all still pass and no new forbidden token was introduced.

## 4. Integration with the already-built combat engine

- [ ] 4.1 Test: `combat.run_round(battlefield, action_provider)` skips a fled roster member's turn,
      with zero modification to `world/rules/combat.py`.
- [ ] 4.2 Test: `overwhelm.team_effective_power()`/`hit_rate_verdict()` exclude a fled member from
      their team's aggregate, with zero modification to `world/rules/overwhelm.py`.
- [ ] 4.3 Test: any `TargetSpec.SINGLE` skill resolved against a fled target rejects with
      `TARGET_OUT_OF_RANGE`, via `BattlefieldActionContext.is_in_range()`'s existing behavior.
- [ ] 4.4 Test: a full `resolve_overwhelm()` call, with an `action_provider` that issues a `flee`
      request for one combatant partway through, completes correctly — the fled combatant is excluded
      from the very next `classify_overwhelm()` recomputation, with zero modification to
      `world/rules/overwhelm.py`.
- [ ] 4.5 Test: `monster_behaviour_policy()` (change 10b, unmodified) continues to produce correct,
      unaffected decisions on a battlefield containing a fled entity — it already filters fled
      members via its own `_living_enemies()` helper.

## 5. Golden fixed-seed scenarios

- [ ] 5.1 Golden case: a same-tier flee attempt (comparable agility) — assert the exact success/
      failure outcome a fixed seed produces, and the resulting `Battlefield.fled`/`EventLog` state.
- [ ] 5.2 Golden case: the human-elite-vs-elf saturated-impossible-escape fixture, run across several
      distinct seeds, asserting failure in every one.
- [ ] 5.3 Golden case: the elf-vs-human-elite saturated-guaranteed-escape fixture, run across several
      distinct seeds, asserting success in every one.
- [ ] 5.4 Golden case: a failed flee attempt's full round — assert the fleeing entity's turn produced
      no damage/benefit while a surviving opponent's own turn that round still executed normally,
      demonstrating the opportunity-cost analysis in design.md D-1/D-4's Risks concretely.

## 6. Validation

- [ ] 6.1 Run `openspec validate combat-disengage --strict` and resolve any reported issues.
