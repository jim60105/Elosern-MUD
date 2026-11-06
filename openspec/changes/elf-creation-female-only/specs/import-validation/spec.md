## ADDED Requirements

### Requirement: A character record's sex must be permitted by its race
Character import validation SHALL reject a record whose `sex` is not a member of the sex set its `race` declares in `RACE_REGISTRY`, naming the record, the `sex` field and the reason. A record whose race permits the declared sex SHALL produce no issue for this check, and an unresolvable race SHALL leave the judgement to the race check.

#### Scenario: An elf record with a non-female sex is rejected
- **WHEN** a character record declares `"race": "elf"` and `"sex": "male"` or `"sex": "other"`
- **THEN** the record is rejected with one issue whose field is `sex` naming the declared value and
  the race that forbids it, that issue is reported under the record's own key, and the record is
  excluded from the batch's instantiable characters

#### Scenario: An elf record with a female sex passes
- **WHEN** a character record declares `"race": "elf"` and `"sex": "female"`
- **THEN** the sex check produces no issue and the record continues to its other checks

#### Scenario: Races that permit the value are untouched
- **WHEN** a character record declares `"race": "human"` or `"race": "beastfolk"` with any `SEX_VALUES` member
- **THEN** the sex check produces no issue for any of the three members

#### Scenario: An unresolvable race is not reported twice
- **WHEN** a character record names a race absent from `RACE_REGISTRY`
- **THEN** the race check owns that rejection and the sex check adds no issue of its own

#### Scenario: The check applies to every character record, not only player targets
- **WHEN** the same elf-and-non-female record is validated for an NPC target
- **THEN** it is rejected by this same check, because the loader's character contract is shared and the world's canon admits no male elf at all

#### Scenario: A rejected batch persists nothing
- **WHEN** a batch containing an elf record with a non-female sex is loaded together with an otherwise valid sibling record
- **THEN** the load raises the import rejection and no entity from that batch exists afterwards, because validation precedes the all-or-nothing transaction
