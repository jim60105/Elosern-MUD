## ADDED Requirements

### Requirement: Startup converts classic scene outputs into scene gallery cards
Before the gallery orphan prune, startup SHALL convert every settled classic scene record: a `done` record whose output is presentable becomes the archetype's scene gallery card when the gallery holds none; then the record and its classic output files SHALL be deleted. Unsettled records SHALL be left for a later startup. The step SHALL be idempotent, bounded per record, and leave no orphan file or record.

#### Scenario: A done classic scene becomes one card
- **WHEN** synthetic archetype `t_arch` has a `done` classic record with a presentable output and an empty scene gallery
- **THEN** after startup its gallery holds exactly one default card whose file holds the same bytes, and neither the classic record nor the classic output file remains

#### Scenario: An existing card wins
- **WHEN** `t_arch` already holds a scene gallery card and also a `done` classic record
- **THEN** the card is unchanged, and the classic record and its output files are deleted

#### Scenario: Failed and missing records are dropped
- **WHEN** a classic scene record is `failed`, `missing`, or `done` without a presentable output
- **THEN** it and any of its output files are deleted and no card is created

#### Scenario: An unsettled record waits
- **WHEN** a classic scene record is `pending` or `in_progress`
- **THEN** it is left unchanged

#### Scenario: Running twice changes nothing more
- **WHEN** the conversion runs a second time
- **THEN** it creates, deletes and moves nothing

#### Scenario: One bad record never aborts startup
- **WHEN** converting one record raises
- **THEN** a bounded diagnostic is logged, the other records are converted, and startup continues
