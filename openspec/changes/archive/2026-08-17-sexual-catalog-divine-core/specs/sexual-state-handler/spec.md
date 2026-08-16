## MODIFIED Requirements

### Requirement: SexualState.unlocked_act_keys() gates the sexual act catalogue by counter thresholds, or unlocks it entirely for a mastery holder
`SexualState` SHALL expose `unlocked_act_keys() -> frozenset[str]`, returning every key in
`SEXUAL_ACT_REGISTRY` whose `unlock` mapping's thresholds are all met by the entity's own lifetime
counters, **or** the entire `SEXUAL_ACT_REGISTRY` keyset **minus every act whose paired `SkillDef`
declares `requires_divine_arts=True`** when the entity directly owns any skill whose parsed effects
include a `SexualMasteryEffect`. The mastery check SHALL consult `entity.skills.base_owned_keys()`,
never `entity.skills.owned_keys()` and never `entity.skills.conferred_grants()`.

#### Scenario: Direct ownership of a SexualMasteryEffect-bearing skill unlocks the entire catalogue except divine acts
- **WHEN** `unlocked_act_keys()` is read on an entity whose `entity.skills.base_owned_keys()` includes
  a skill carrying `SexualMasteryEffect`, regardless of that entity's counter values
- **THEN** the returned set equals the full `SEXUAL_ACT_REGISTRY` keyset minus every act whose paired
  `SkillDef` declares `requires_divine_arts=True`
