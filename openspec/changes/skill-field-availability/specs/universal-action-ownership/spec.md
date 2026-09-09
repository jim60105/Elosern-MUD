## MODIFIED Requirements

### Requirement: INNATE_SKILL_KEYS makes flee and basic_attack ownable by every LivingEntity regardless of import or spawn data
`world/skills/handler.py` SHALL declare `INNATE_SKILL_KEYS: frozenset[str]`, seeded with exactly
`{"flee", "basic_attack"}`, and `SkillHandler.owned_keys()` SHALL include every key in `INNATE_SKILL_KEYS` in its
returned list, in addition to the entity's own imported `active`/`passive` keys.
`basic_attack` SHALL be a zero-cost active SINGLE/ENEMY physical-damage skill that SHALL resolve
through the ordinary ActionResolver path. It SHALL declare `usable_out_of_combat=True`, meaning it is
*selectable* from exploration solely as a field-combat initiation; it SHALL remain unable to resolve
without a battlefield, because `action-resolution-pipeline`'s damaging-action gate rejects a
`DamageEffect`-carrying skill whose context has no battlefield. `flee` SHALL declare
`usable_out_of_combat=False`.

#### Scenario: An entity with no imported skill data still owns both innate actions
- **WHEN** `SkillHandler.owned_keys()` is called for an entity whose `entity.db.skills` is unset
  (`None`) or empty
- **THEN** the returned list contains `"flee"` and `"basic_attack"`

#### Scenario: An entity with a full imported skill list also owns both innate actions
- **WHEN** `SkillHandler.owned_keys()` is called for an entity whose `entity.db.skills` contains several
  active and passive keys imported from a character card
- **THEN** the returned list contains every imported key plus `"flee"` and `"basic_attack"`

#### Scenario: A Monster instance can fight without spawned skill data
- **WHEN** `SkillHandler.owned_keys()` is called for a `Monster` instance constructed with no
  `entity.db.skills` data at all (no bestiary/spawn system exists in this project's dependency chain)
- **THEN** it owns both innate actions and its behavior policy can select `basic_attack` against an enemy

#### Scenario: Basic attack does not bypass ActionResolver
- **WHEN** an entity invokes `basic_attack` in combat
- **THEN** ownership, target, capability, damage, EventLog, planner, and commit behavior use the same
  ActionResolver pipeline as a registered imported damage skill

#### Scenario: Basic attack is selectable from exploration but cannot resolve without a battlefield
- **WHEN** `basic_attack` is resolved with a `RoomActionContext`
- **THEN** the `usable_out_of_combat` gate does not reject it, and it rejects with
  `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` instead — no damage is dealt and no resource is spent
