## MODIFIED Requirements

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than the single, explicitly marked `usable_out_of_combat` gate and
the deferred tiered-monster kill-XP staging check. That check MAY inspect whether the caller supplied a
battlefield-backed context solely to stage `grant_combat_kill_xp()` for each unique, resolved `Monster`
target that was initially alive and is reduced to zero HP during the action's atomic commit. All other
combat-vs-non-combat behavior SHALL be expressed entirely through which concrete `ActionContext`
implementation the caller supplies.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

#### Scenario: A battlefield action stages tiered Monster kill XP only
- **WHEN** a battlefield-backed action reduces a resolved `Monster` with a known `threat_tier` from
  positive HP to zero
- **THEN** the action stages exactly one deferred combat-kill XP effect for that target, while a
  non-Monster target with the same `threat_tier` receives no kill-XP effect

#### Scenario: No public callable takes a combat-shaped parameter
- **WHEN** every public callable in `action.py`, `targeting.py`, and `event_log.py` has its signature
  inspected
- **THEN** no parameter is named `in_combat`, `combat_state`, `turn`, or `is_combat`

#### Scenario: Identical code, different ActionContext, different faction outcome
- **WHEN** `ActionResolver.resolve()` is called twice with byte-identical `ActionRequest`s (same actor,
  same `skill_key` whose `SkillDef.faction_constraint` is `FactionConstraint.ENEMY`) differing only in
  which `ActionContext` is supplied — once with `RoomActionContext`, once with a test double whose
  `relation_to()` reports `Relation.ENEMY` for the same target
- **THEN** the `RoomActionContext` call rejects with `RejectReason.TARGET_FACTION_FORBIDDEN` and the
  test-double call succeeds, with no difference in `action.py`'s or `targeting.py`'s executed source
  between the two calls
