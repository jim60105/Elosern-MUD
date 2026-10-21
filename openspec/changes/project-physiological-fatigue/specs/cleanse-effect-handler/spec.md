# Spec Delta

## MODIFIED Requirements

### Requirement: cleanse:status removes every active debuff-polarity buff from the target
`world/rules/buffs.py` SHALL define a `cleanse` effect handler, registered via
`register_effect_handler` in `world/rules/action.py`, resolving `cleanse:status` by removing every
currently-active buff on the target whose `buffs.yaml` definition has `polarity == "debuff"` and is eligible for external removal. Buffs
with `polarity == "buff"` and protected physiological projections SHALL NOT be removed. Reserve and posture SHALL remain unchanged.

#### Scenario: Cleansing removes an active debuff
- **WHEN** a `cleanse:status` effect resolves against a target with an active `poisoned` buff
- **THEN** the target no longer has `poisoned` active afterward

#### Scenario: Cleansing does not remove a beneficial buff
- **WHEN** a `cleanse:status` effect resolves against a target with an active `focus` buff and no
  active debuffs
- **THEN** `focus` remains active afterward

#### Scenario: The cleanse effect and the shared removal cannot diverge
- **WHEN** `cleanse:status` resolution is traced against a target carrying a mix of polarities
- **THEN** it reaches the same shared selector-driven removal, with the debuff selector, that every
  other debuff-clearing caller reaches

#### Scenario: Removal runs the external-removal hooks
- **WHEN** a `cleanse:status` removal executes
- **THEN** it routes through `entity.buffs.remove(..., dispel=True)`, whose dispel flag runs
  Evennia's external-removal hooks (`at_dispel` then `at_remove`), recording cleanse as a forced
  external removal rather than a natural expiry

### Requirement: Status removal is expressed as one selector-driven operation returning a count
`world/rules/buffs.py` SHALL expose a public removal function taking an entity and one selector, and
returning the number of eligible buff instances actually removed. Protected physiological projections SHALL be excluded for every selector. The selector vocabulary SHALL be exactly: a
concrete `buffs.yaml` definition key, `negative` (every active debuff-polarity instance), `positive`
(every active buff-polarity instance), and `all` (both). A selector matching nothing SHALL write
nothing and return `0`.

#### Scenario: The negative selector removes every debuff and nothing else
- **WHEN** the removal function is called with `negative` against a target carrying two active
  externally removable debuff-polarity buffs and one buff-polarity buff
- **THEN** both debuffs are gone, the beneficial buff remains active, and the call returns `2`

#### Scenario: The positive selector removes beneficial buffs only
- **WHEN** the removal function is called with `positive` against a target carrying one
  externally removable buff-polarity and one externally removable debuff-polarity buff
- **THEN** only the buff-polarity instance is removed and the call returns `1`

#### Scenario: The all selector removes both polarities
- **WHEN** the removal function is called with `all` against a target carrying one externally removable instance of each polarity
- **THEN** the target has no active buffs afterward and the call returns `2`

#### Scenario: A concrete key removes every live instance of that definition
- **WHEN** the removal function is called with a concrete definition key against a target carrying two
  externally removable live instances of that definition under different instance keys
- **THEN** both instances are removed and the call returns `2`

#### Scenario: A selector matching nothing is a no-op
- **WHEN** the removal function is called with `negative` against a target carrying no debuffs
- **THEN** nothing is written and it returns `0`

#### Scenario: Selection resolves against live buff instances
- **WHEN** a selector is applied
- **THEN** it resolves against **live buff instances**, not definition keys, so a definition with
  several live instances loses all of them

#### Scenario: Every removal routes through the dispel path
- **WHEN** the removal function removes any instance
- **THEN** it routes through the same `dispel=True` external-removal path the cleanse handler
  already uses

## ADDED Requirements

### Requirement: Physiological protection applies to every external selector
All general status-removal selectors SHALL exclude protected physiological fatigue and sleep instances, including concrete keys, negative and all. Removal counts SHALL include only actually removed eligible instances. Future explicit reserve/posture effects SHALL use the authoritative state writer.

#### Scenario: Mixed cleanse
- **WHEN** a target has poison, an ordinary beneficial buff and physiological fatigue and receives negative then all then a concrete fatigue selector
- **THEN** negative removes only poison, all removes only the remaining ordinary buff, the fatigue selector removes zero; reserve/posture/projection are unchanged

