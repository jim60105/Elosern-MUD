## ADDED Requirements

### Requirement: Every skill declares usable_out_of_combat deliberately, under one written policy
`usable_out_of_combat` SHALL mean exactly "this skill may be *selected* while no combat session is
in progress"; it SHALL NOT mean the skill's effects may resolve without a battlefield, which
`action-resolution-pipeline`'s damaging-action gate governs independently.

Every entry of `SKILL_REGISTRY` SHALL declare a deliberate value at its own construction site — or,
for a generated family, at the builder that produces that family — judged by one policy: an `ACTIVE`
skill SHALL declare `True` unless casting it with no fight in progress is meaningless, because the
effect has nothing to act on, or would bypass a subsystem that owns the outcome. `PASSIVE` skills
SHALL also carry a deliberate value even though the capability step rejects them with
`RejectReason.SKILL_NOT_ACTIVE` before either out-of-combat gate is reached.

Skills carrying a `world.skills.effects.DamageEffect` SHALL declare `True`: their only use outside a
fight is opening one, and the damaging-action gate confines that use to a battlefield.

#### Scenario: Damage-carrying skills are selectable outside combat
- **WHEN** every `SKILL_REGISTRY` entry whose parsed `effects` include a `DamageEffect` is inspected
- **THEN** each declares `usable_out_of_combat=True`

#### Scenario: A damage skill selected outside combat still cannot resolve without a battlefield
- **WHEN** one of those skills is resolved with a `RoomActionContext`
- **THEN** it rejects with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, demonstrating that the flag
  governs selection and the gate governs resolution

#### Scenario: flee remains unselectable outside combat
- **WHEN** `SKILL_REGISTRY["flee"]` is inspected after `world.rules.disengage` has been imported
- **THEN** its `usable_out_of_combat` is `False`, declared at its own construction site in
  `world/rules/disengage.py`, because there is nothing to disengage from outside combat

#### Scenario: The value is declared at the construction site, never patched afterwards
- **WHEN** `world/skills/registry.py`, `world/skills/sexual_acts/_builder.py`, and
  `world/rules/disengage.py` are inspected
- **THEN** each skill's `usable_out_of_combat` is supplied as an argument at construction, and no
  module mutates the field on an already-built `SkillDef`

### Requirement: The set of skills declaring usable_out_of_combat False is a frozen inventory
`world/skills/tests/` SHALL assert that the set of `SKILL_REGISTRY` keys declaring
`usable_out_of_combat=False` equals an explicit literal set enumerated in the test. Because
`SkillDef`'s construction helpers default the field to `False`, a newly authored skill that omits a
deliberate value SHALL fall outside the pinned set and SHALL fail this assertion, naming the
undecided key. The assertion SHALL cover the hand-written definitions, every generated family, the
sexual-act catalog, and `flee` in one inventory.

#### Scenario: The inventory matches the registry exactly
- **WHEN** the frozen-inventory test runs against the current registry
- **THEN** the computed `False` set equals the enumerated set, with no extra and no missing key

#### Scenario: A new skill that omits a decision fails and is named
- **WHEN** a skill is added to `SKILL_REGISTRY` without supplying `usable_out_of_combat`
- **THEN** the frozen-inventory assertion fails and its failure message names that skill's key as
  undecided

#### Scenario: Flipping a pinned skill to True fails until the inventory is updated
- **WHEN** a skill currently enumerated in the `False` set is changed to declare `True` without
  editing the test
- **THEN** the frozen-inventory assertion fails, so every change of judgement is recorded in one
  place
