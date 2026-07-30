## Why

Design doc §11 roadmap item #10b, depending on changes 9 (`dice-combat`) and 10 (`overwhelm-resolution`).
Change 9 built the turn loop but explicitly refused to build real monster AI, naming its own
`default_attack_policy` a "labelled placeholder, not a real AI" that always targets the lowest-hp living
enemy with whichever `damage:*`-effect skill the entity happens to own first — identical behaviour for
a 史萊姆 and a 古龍. Change 3 declared `Monster.behaviour_tree` as an unbuilt seam back in Phase 1 and
left it `None` ever since. Without this change, the change-16 milestone's claim of "a complete, playable
game" is not true: every monster in the game, regardless of `MonsterTier`, fights identically and
predictably, which is the exact gap change 9's own Risks section named this change to close.

This change is scoped narrowly: it is monster **combat decision-making** only — which target to engage,
which owned skill to cast, and (per an amendment folded in after change 10c, `combat-disengage`, landed)
when to attempt to flee instead — each round, expressed as an `ActionRequest` for change 8's
`ActionResolver` to resolve exactly as it would any other actor's action. It does not invent loot,
dialogue, scheduling, or any generative behaviour, and it does not build the flee *mechanism* itself —
change 10c owns the `flee` skill, its success formula, and `Battlefield.fled`'s writer; this change owns
only the decision of when an archetype attempts it, the extension point change 10c's own design named
this change to fill.

## What Changes

- Add `world/rules/monster_behaviour.py`: `monster_behaviour_policy(entity, battlefield) -> ActionRequest
  | None`, a drop-in replacement for change 9's `default_attack_policy` as an `action_provider` callable.
  For a `Monster` entity, decision quality is driven by a resolved `BehaviourProfile` (target-selection
  strategy, skill-choice strategy, area-skill preference) looked up from `Monster.threat_tier` (change 2's
  `MonsterTier` key, defaulted) with an optional per-instance override read from `Monster.behaviour_tree`
  (change 3's declared, previously-unbuilt seam — this change is what finally gives that attribute
  consumed meaning). For any non-`Monster` entity encountered in the same turn loop (an NPC ally with no
  input source wired up yet, for instance), the function delegates to change 9's own
  `default_attack_policy` unmodified — this change only changes monster decision quality, nothing else's.
- Add `world/rules/rulebook/monster_behaviour.yaml`: the tier→archetype default mapping and every
  archetype's tunable parameters (target strategy, skill-choice strategy, area-skill preference, and —
  per the amendment below — a per-archetype `flee_hp_fraction`), as data, per design doc D9 — no
  balance-relevant number is a Python literal.
- A small, fully deterministic decision tree (Python structure, YAML-tuned leaves): decide whether to
  flee this round (per the amendment below), else decide single-target vs. area-target, pick a target
  (or rely on `"all-enemies"` shorthand for area), pick which owned `damage:*`-effect skill to cast. Any
  tie-break this tree needs (e.g. two enemies at exactly equal hp) draws from change 9's seeded
  `dice.roll_d100()` wrapper, never Python's `random` module directly, so golden fixed-seed tests can
  assert exact, reproducible decisions.
- **Amendment (post-acceptance, following change 10c's landing)**: a per-archetype `flee_hp_fraction:
  float | None` tunable and one new decision-tree branch, evaluated before the single-vs-area decision,
  that returns an `ActionRequest` invoking change 10c's innately-owned `flee` skill (with
  `event_context={"battlefield": battlefield}` populated, per that change's own required convention) once
  the acting monster's current-hp fraction falls at or below its archetype's threshold. The check is
  stateless — re-evaluated fresh every turn from current hp, with no "already attempted" memory — and the
  four thresholds are calibrated per tier (史萊姆-tier `instinctive` flees earliest; 古龍-tier
  `apex_predator` never flees), not a single shared number. See design.md D-6 for the full grounding and
  for why re-evaluation (not persistence) is the resolution to change 10c's own deferred question.
- Every decision is expressed as a single `ActionRequest` handed to `ActionResolver.resolve()` — this
  change adds no new effect handler, no new `RejectReason`, and no edit to
  `action.py`/`targeting.py`/`event_log.py`. It relies entirely on change 8's existing pipeline and
  change 9's existing `BattlefieldActionContext` for targeting, faction validation, and range.
- No new handling for `actions_per_turn: 0`, arousal thresholds, or any `combat_modifiers.yaml` rule.
  Change 9's `run_round()` already reads `evaluate_combat_modifiers(entity)` and skips a zeroed-actions
  combatant's turn **before** calling `action_provider` at all — a monster whose actions are zeroed
  simply never reaches this change's code. This change adds no monster-specific bypass of that gate,
  because there is no gate left for it to bypass by the time `action_provider` is invoked.
- No LLM call, no import from `world/ai/`, anywhere in this change's code — a source-scan test proves it,
  mirroring the discipline changes 3/5/8/9 already established for their own tripwires.
- Golden, fixed-seed tests proving each of the four `MonsterTier` archetypes makes a different,
  reproducible decision on an identical battlefield, that the seeded tie-break is reproducible, that a
  non-`Monster` entity still gets change 9's original placeholder behaviour unchanged, and that this
  change's `action_provider` works correctly as the callable passed into both change 9's `run_round()`
  and change 10's `resolve_overwhelm()` with no special-casing in either caller.

## Capabilities

### New Capabilities
- `monster-behaviour-profile`: the tier→archetype default mapping, the archetype parameter table
  (`monster_behaviour.yaml`), and the resolution function that reads `Monster.threat_tier` and the
  now-consumed `Monster.behaviour_tree` override to produce one `BehaviourProfile` per monster.
- `monster-action-policy`: `monster_behaviour_policy()`'s decision tree (target selection, skill
  selection, single-vs-area choice, the seeded tie-break), its conformance as an `action_provider` for
  both change 9's `run_round()` and change 10's `resolve_overwhelm()`, its delegation to
  `default_attack_policy` for non-`Monster` entities, and the structural guarantees (no LLM, no new
  `ActionResolver` extension point, no `actions_per_turn` special-casing).

### Modified Capabilities
- None. `openspec/specs/` is empty (no earlier change has been archived yet), and this change edits no
  file authored by any earlier change — it only reads change 2's `MONSTER_TIER_REGISTRY`, change 3's
  `Monster.threat_tier`/`behaviour_tree` attributes, change 5's `SkillDef`/`SKILL_REGISTRY`, change 8's
  `ActionRequest`/`ActionResolver`, change 9's `Battlefield`/`BattlefieldActionContext`/
  `effective_power()`/`dice.roll_d100()`/`default_attack_policy`, and change 10c's
  `disengage.FLEE_SKILL_KEY`, all as their already-public surfaces.

## Impact

- **New files**: `world/rules/monster_behaviour.py`, `world/rules/rulebook/monster_behaviour.yaml`,
  `world/rules/tests/test_monster_behaviour_*.py` (new test modules for this change's scope).
- **Modified files**: none. `Monster.behaviour_tree` already exists as a placeholder attribute (change 3)
  defaulting to a value this change treats as "no override, use the tier default" — no edit to
  `typeclasses/monsters.py` is required to give that field consumed meaning.
- **Depends on**: change 9 (`dice-combat`) for `Battlefield`, `BattlefieldActionContext`,
  `effective_power()`, `dice.roll_d100()`, and `default_attack_policy` (the function this change
  supersedes for `Monster` entities specifically); change 10 (`overwhelm-resolution`) for
  `resolve_overwhelm()`'s `action_provider` contract, which this change's policy must satisfy without
  modification; **change 10c (`combat-disengage`)** for `FLEE_SKILL_KEY` and the `disengage`/
  `INNATE_SKILL_KEYS` mechanism the flee branch invokes — read-only reuse, no edit to `disengage.py`;
  transitively, change 8 (`action-resolver`) for `ActionRequest`/`ActionResolver.resolve()`, change 5
  (`skills-equipment`) for `SkillDef`/`SkillHandler.effective_value()`, and change 2 (`lore-world-data`)
  for `MONSTER_TIER_REGISTRY`.
- **Consumers deferred to later changes**: none named by this change — `monster_behaviour_policy()` is
  itself a leaf consumer of changes 2/3/5/8/9/10's existing surfaces, not a new seam for anything else to
  build against. Whoever eventually wires up a live, player-input-driven combat command (not on the
  roadmap under any number yet) is expected to dispatch to this change's function for `Monster` turns and
  to a real input source for player turns — a composition point named explicitly in design.md, not built
  here.
