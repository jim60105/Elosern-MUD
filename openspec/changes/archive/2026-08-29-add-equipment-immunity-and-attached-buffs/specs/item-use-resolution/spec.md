## MODIFIED Requirements

### Requirement: Successful item use emits a stable EventLog entry
Every successful item use SHALL emit one `item_used` EventLog entry for the actor and self target. Its data SHALL carry `item_key`, `effect_key`, and `consumable`, plus the per-family payload: gauge-restoring effects SHALL additionally carry `amount`, the actual bounded effect applied; the `blessed_cleansing` effect SHALL additionally carry `count`, the number of debuff-polarity buffs actually removed. Rejected preflight SHALL emit no item-use EventLog. A compressed commanded-action marker SHALL identify the selected item separately and SHALL NOT replace the item-use entry.

#### Scenario: Healing log records actual restoration
- **WHEN** a potion configured for more healing than the actor's missing HP succeeds
- **THEN** one `item_used` entry reports the potion and effect keys, consumable true, and amount equal only to the HP actually restored

#### Scenario: Cleanse log records the removed count
- **WHEN** 受洗聖水 removes three active debuffs
- **THEN** the `item_used` entry carries the potion and `blessed_cleansing` effect keys, consumable true, and a `count` of exactly three with no `amount` field

## ADDED Requirements

### Requirement: Blessed cleansing consumes holy water to purge debuffs

`blessed_cleansing` SHALL be a registered deterministic item-effect key
whose rulebook entry carries no amount. Using a held 受洗聖水 SHALL remove
every active debuff-polarity buff from the actor through the shipped
cleanse removal path, consume exactly one item key (with its contained
mirror when present), emit its stable EventLog entry, and commit atomically
with the existing item-use settlement. The item-use touched-journal SHALL
snapshot and restore the buff storage surface so a post-cleanse failure
rolls back persistence and live buff reads together.

#### Scenario: Holy water cleanses the actor

- **WHEN** an actor afflicted with `poisoned` and `fear` uses 受洗聖水
- **THEN** both debuffs are gone, exactly one potion key was consumed, and
  a stable event entry was logged

#### Scenario: Nothing to cleanse rejects without consuming

- **WHEN** an unafflicted actor uses 受洗聖水
- **THEN** preflight rejects with the registered `no_debuffs` reason
  (mirroring the `hp_full` heal discipline) rendered in Traditional Chinese
  through the shipped reason surfaces, the potion is not consumed, and no
  world clock advances

#### Scenario: Post-cleanse failure restores buffs

- **WHEN** settlement fails after the cleanse removal (injected fault)
- **THEN** the potion key, the debuffs, and live buff reads are all
  restored to their pre-use state

#### Scenario: Cleanse entry shape is validated

- **WHEN** the item-effects rulebook gives a `blessed_cleansing` entry an
  `amount` field
- **THEN** the validated loader rejects it
