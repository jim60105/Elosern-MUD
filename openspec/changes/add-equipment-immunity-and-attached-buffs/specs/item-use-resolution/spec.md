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
