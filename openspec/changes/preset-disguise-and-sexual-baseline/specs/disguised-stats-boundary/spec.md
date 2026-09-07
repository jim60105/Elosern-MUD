# disguised-stats-boundary delta

## MODIFIED Requirements

### Requirement: disguised_stats keys are readable by exactly three consumers, including implemented guild registration
The docstring of `get_display_value` and this specification SHALL name exactly three permitted call
sites: appearance rendering (`look`), guild registration records, and appraisal items. Appearance
rendering SHALL be implemented through the `look <target>` displayed-stats block, which SHALL call
the accessor for the displayed combat five (`atk_phys`, `agility`, `defense`, `magic_power`, `hp`).
Guild registration SHALL call the accessor once per documented trait key to persist a historical
displayed-stat snapshot. Appraisal items MAY remain deferred. No other guild operation, including
board eligibility, reward settlement, merit checks, examiner profile selection, combat, or
promotion, SHALL call the accessor or read `disguised_stats`.

This requirement bounds READERS. Seeding the layer is a separate, bounded set of WRITERS:
`world/imports/loader.py` (import records) and `world/rules/character_creation.py` (preset
activation) SHALL be the only production modules that assign `entity.db.disguised_stats`, each
writing an authored declaration once at entity construction and never reading the mapping back to
make a decision. A writer SHALL NOT be counted as a consumer, and the forbidden-module list
(`world/rules/combat.py`, `world/rules/dice.py`, `world/rules/targeting.py`) SHALL remain closed to
both reads and writes.

#### Scenario: Accessor documentation still names exactly three consumers
- **WHEN** `get_display_value`'s docstring is inspected
- **THEN** it names appearance rendering (`look`), guild registration records, and appraisal items
  as the only permitted callers and states that combat, resolution, and damage must not call it

#### Scenario: Appearance rendering and registration are the only implemented consumers
- **WHEN** production (non-test) source modules are scanned for `get_display_value` or
  `disguised_stats`
- **THEN** the sanctioned readers are exactly the `look <target>` displayed-stats block and the
  guild-registration snapshot path, the sanctioned writers are exactly the import loader and preset
  activation, and no other module reads the raw disguise mapping directly

#### Scenario: Promotion uses canonical state
- **WHEN** a registered actor changes or clears disguise before a guild examination
- **THEN** merit eligibility, examiner stats, combat, and promotion outcomes are unchanged

#### Scenario: The forbidden modules stay closed to the seeding path
- **WHEN** `world/rules/combat.py`, `world/rules/dice.py`, and `world/rules/targeting.py` are scanned
- **THEN** none of them contains `disguised_stats` or `get_display_value`, unchanged by the creation-side writer
