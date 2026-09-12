## MODIFIED Requirements

### Requirement: SexualState.unlocked_act_keys() gates the sexual act catalogue by counter thresholds, or unlocks it entirely for a mastery holder
`SexualState` SHALL expose `unlocked_act_keys() -> frozenset[str]`, returning every key in
`SEXUAL_ACT_REGISTRY` whose `unlock` mapping's thresholds are all met by the entity's own lifetime
counters **and which does not declare `SexualActDef.ownership_gated=True`**, **or** the entire
`SEXUAL_ACT_REGISTRY` keyset **minus every act whose paired `SkillDef` declares
`requires_divine_arts=True` and minus every `ownership_gated=True` row** when the entity directly
owns any skill whose parsed effects include a `SexualMasteryEffect`. The mastery check SHALL consult
`entity.skills.base_owned_keys()`, never `entity.skills.owned_keys()` and never
`entity.skills.conferred_grants()`. Ownership-gated rows are reachable only through actual skill
ownership — directly or via conferred grants — which the derivation path never supplies; the shipped
`divine_sexual_arts` row is the only ownership-gated act, and it is excluded from both branches by
both of its markers simultaneously, so no shipped entity's derived set changes beyond gaining that
one key's exclusion.

#### Scenario: An act unlocks when every one of its thresholds is met
- **WHEN** `unlocked_act_keys()` is read on an entity whose counters meet every threshold in one
  act's `unlock` mapping
- **THEN** that act's key is present in the returned set

#### Scenario: An act stays locked when any one threshold is unmet
- **WHEN** `unlocked_act_keys()` is read on an entity whose counters meet every threshold in one
  act's `unlock` mapping except one
- **THEN** that act's key is absent from the returned set

#### Scenario: A seed act with an empty unlock mapping is always present
- **WHEN** `unlocked_act_keys()` is read on an entity with every counter at zero
- **THEN** every non-ownership-gated act whose `unlock` mapping is empty is present in the returned
  set

#### Scenario: An ownership-gated row with an empty unlock mapping is never derived
- **WHEN** `unlocked_act_keys()` is read on any entity — fresh or counter-saturated, mastery holder
  or not — that does not own the key
- **THEN** `divine_sexual_arts` is absent from the returned set even though its `unlock` mapping is
  empty

#### Scenario: Direct ownership of a SexualMasteryEffect-bearing skill unlocks the entire catalogue except divine acts
- **WHEN** `unlocked_act_keys()` is read on an entity whose `entity.skills.base_owned_keys()` includes
  a skill carrying `SexualMasteryEffect`, regardless of that entity's counter values
- **THEN** the returned set equals the full `SEXUAL_ACT_REGISTRY` keyset minus every act whose paired
  `SkillDef` declares `requires_divine_arts=True` and minus every `ownership_gated=True` row

#### Scenario: A conferred, not directly owned, mastery grant does not unlock the catalogue
- **WHEN** an entity's `entity.skills.conferred_grants()` includes a fractional grant of a
  `SexualMasteryEffect`-bearing skill, but that skill's key is absent from
  `entity.skills.base_owned_keys()`
- **THEN** `unlocked_act_keys()` does not apply the blanket unlock, and returns only the acts whose
  counter thresholds are independently met

#### Scenario: The mastery check does not read owned_keys()
- **WHEN** `unlocked_act_keys()`'s implementation is inspected
- **THEN** its mastery-ownership check calls `entity.skills.base_owned_keys()`, and no line in that
  check calls `entity.skills.owned_keys()`
