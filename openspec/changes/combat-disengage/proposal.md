## Why

Design doc §6.3 lists "flee" as one of three ways a combat encounter ends (wipe / flee / special
condition), and `Battlefield.fled` has existed as a declared field since change 9 (`dice-combat`) —
read by `is_present()`/`is_in_range()` (both treat a fled key as "no longer a valid target") and by
change 10's team-power aggregation (a fled member contributes nothing) and change 11's skip-safety
gate (`IN_COMBAT` excludes fled members by definition). **No change writes to it.** Change 10b
(`monster-behaviour`) explicitly declined to build it, naming fleeing "an execution mechanism, not a
decision," and named this change as the mechanism's owner. Without a writer, the only exits from a
fight are victory and death — harsh in a world where an elf can one-shot a human (dice-combat's own
D-2/D-4 worked tables), and the one place this project would otherwise have no answer to "I know I'm
going to lose, can I leave."

## What Changes

- Add exactly one new `SkillDef` (`flee`) to change 5's `SKILL_REGISTRY`, `target_spec=SELF`,
  `faction_constraint=SELF_ONLY`, `usable_out_of_combat=False`, `cost={}` — castable through the
  unmodified `ActionResolver.resolve()` pipeline, the unmodified out-of-combat/in-combat gate (D-3 of
  `action-resolver`), and the unmodified four-validation targeting path (`TargetSpec.SELF` still runs
  presence/alive/range/faction against the actor).
- Add a small `INNATE_SKILL_KEYS` set consumed by `SkillHandler.owned_keys()` (change 5), so every
  `LivingEntity` — player or monster, regardless of import/spawn data — can always attempt `flee`
  without needing it explicitly granted. One additive line in an already-landed function.
- Register a `disengage` effect handler into change 8's open effect registry
  (`register_effect_handler("disengage", ...)`), computing flee success from the **same** agility
  comparison and **same** recalibrated constant (`51`) dice-combat's own to-hit formula already uses —
  no new formula, no new number, no `if overwhelmed: return False`.
- On success: adds the fleeing entity's key to `Battlefield.fled` (the field's first-ever writer). On
  failure: no state changes beyond the entity having spent its turn — the existing turn-loop mechanics
  (everyone else still acts that round) supply the cost.
- Extend `ActionResolver`'s atomicity mechanism (`SNAPSHOTTED_SURFACES`, `_commit()`'s snapshot/
  restore) with one new mutation surface, `"battlefield"`, since `Battlefield.fled` is the first
  effect-handler mutation target in the whole project that is not an entity substate. This answers
  action-resolver's own Open Question ("Left to whichever change first needs one").
- No new player-facing command: `flee` is cast exactly like any other skill (`cast flee`), through the
  identical `CmdCast`/`ActionResolver.resolve()` path already built. No new command file.
- No change to `run_round()`, `resolve_overwhelm()`, `classify_overwhelm()`, or any monster-behaviour
  file. Fleeing is only ever expressed as an `ActionRequest` an `action_provider` chooses to return —
  the same seam `monster_behaviour_policy()` already fills for attacks. A concrete extension point
  (and exactly what `monster_behaviour.yaml` would need) is specified for change 10b as a **named
  follow-up**, not built here.

## Capabilities

### New Capabilities
- `disengage-action`: the `flee` `SkillDef`, the `disengage` effect handler, the agility-based flee
  success formula and its saturation behavior, the failure cost, and the resulting `EventLog` shape.
- `battlefield-commit-surface`: the new `"battlefield"` mutation surface in `ActionResolver`'s
  atomicity mechanism, letting a registered effect handler safely mutate `Battlefield.fled` with the
  same all-or-nothing commit/rollback guarantee every entity-state mutation already has.
- `universal-action-ownership`: `INNATE_SKILL_KEYS`, making `flee` (and any future universally-owned
  action) castable by every `LivingEntity` without requiring it in imported/spawned skill data.

### Modified Capabilities
- None. No existing `openspec/specs/` capability exists yet for any of changes 1-10b (nothing has been
  archived), so there is nothing to modify at the spec level — only new capabilities are added.

## Impact

- **New file**: `world/rules/disengage.py` — the `flee` `SkillDef` registration, the `disengage`
  effect handler, the flee-success formula, and the `INNATE_SKILL_KEYS` constant.
- **Additive edit to `world/rules/action.py`** (change 8's implementation, not its OpenSpec artifacts):
  `SNAPSHOTTED_SURFACES` gains `"battlefield"`; the commit-time snapshot/restore dispatch gains a
  duck-typed branch for a Battlefield-shaped object alongside the existing per-entity path. No change
  to `resolve()`'s eight steps, `RejectReason`, or the no-combat-branching tripwire's scanned tokens.
- **Additive edit to `world/skills/handler.py`** (change 5's implementation): `SkillHandler.owned_keys()`
  gains `INNATE_SKILL_KEYS` in its return value — one line.
- **Read-only reuse, zero edits**: `world/rules/combat.py` (`COMBAT_YAML["to_hit"]["defender_constant"]`,
  `dice.roll_d100()`, `Battlefield`), `world/rules/overwhelm.py`, `world/rules/monster_behaviour.py`,
  `world/rules/rulebook/combat.yaml`, `world/rules/rulebook/overwhelm.yaml`,
  `world/rules/rulebook/monster_behaviour.yaml`.
- **Named follow-up for change 10b** (not built here, not an edit to its artifacts): a
  `flee_hp_threshold`-shaped tunable per archetype in `monster_behaviour.yaml`, and one new branch in
  `monster_behaviour_policy()` evaluated before its existing attack-selection logic. Reported to the
  coordinator, not authored.
- **Seam for changes 12-14**: fleeing removes a combatant from the `Battlefield`'s active contest only
  — it does not relocate the entity's Evennia room location, since no room/exit topology exists yet to
  relocate it to. A real "flee to an adjacent room" mechanic is named as future scope once map layers
  land.
