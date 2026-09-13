## ADDED Requirements

### Requirement: Status removal is expressed as one selector-driven operation returning a count
`world/rules/buffs.py` SHALL expose a public removal function taking an entity and one selector, and
returning the number of buff instances actually removed. The selector vocabulary SHALL be exactly: a
concrete `buffs.yaml` definition key, `negative` (every active debuff-polarity instance), `positive`
(every active buff-polarity instance), and `all` (both). Selection SHALL resolve against **live buff
instances**, not definition keys, so a definition with several live instances loses all of them; every
removal SHALL route through the same `dispel=True` external-removal path the cleanse handler already
uses. A selector matching nothing SHALL write nothing and return `0`.

#### Scenario: The negative selector removes every debuff and nothing else
- **WHEN** the removal function is called with `negative` against a target carrying two active
  debuff-polarity buffs and one buff-polarity buff
- **THEN** both debuffs are gone, the beneficial buff remains active, and the call returns `2`

#### Scenario: The positive selector removes beneficial buffs only
- **WHEN** the removal function is called with `positive` against a target carrying one
  buff-polarity and one debuff-polarity buff
- **THEN** only the buff-polarity instance is removed and the call returns `1`

#### Scenario: The all selector removes both polarities
- **WHEN** the removal function is called with `all` against a target carrying one of each polarity
- **THEN** the target has no active buffs afterward and the call returns `2`

#### Scenario: A concrete key removes every live instance of that definition
- **WHEN** the removal function is called with a concrete definition key against a target carrying two
  live instances of that definition under different instance keys
- **THEN** both instances are removed and the call returns `2`

#### Scenario: A selector matching nothing is a no-op
- **WHEN** the removal function is called with `negative` against a target carrying no debuffs
- **THEN** nothing is written and it returns `0`

## MODIFIED Requirements

### Requirement: cleanse:status removes every active debuff-polarity buff from the target
`world/rules/buffs.py` SHALL define a `cleanse` effect handler, registered via
`register_effect_handler` in `world/rules/action.py`, resolving `cleanse:status` by removing every
currently-active buff on the target whose `buffs.yaml` definition has `polarity == "debuff"`. It
SHALL obtain that set through the same shared selector-driven removal every other debuff-clearing
caller uses, so the cleanse effect and any other clearing path can never diverge. Buffs with
`polarity == "buff"` SHALL NOT be removed. Removal SHALL route through
`entity.buffs.remove(..., dispel=True)`, whose dispel flag runs Evennia's external-removal hooks
(`at_dispel` then `at_remove`), recording cleanse as a forced external removal rather than a natural
expiry.

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
