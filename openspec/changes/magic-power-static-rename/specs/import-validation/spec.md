## MODIFIED Requirements

### Requirement: disguised_stats keys must be a subset of stats keys
`validate.py` SHALL reject a character record where any key present in `disguised_stats` is not
also present in `stats`, naming the offending key(s).

#### Scenario: A disguised_stats key absent from stats is rejected
- **WHEN** a character record's `stats` has no `magic_power` key but `disguised_stats` sets
  `"magic_power": 30`
- **THEN** the record is rejected, naming `magic_power` as the offending disguised_stats key

#### Scenario: A disguised_stats that is a proper subset of stats keys passes this check
- **WHEN** a character record's `disguised_stats` keys are all also present in `stats`
- **THEN** this check produces no rejection

### Requirement: physical and vital stats outside plausible bands warn; magic above its cap rejects
`validate.py` SHALL compare each present `stats` value against the corresponding band from
`world.lore.races.RACE_REGISTRY[race].vital_baseline`/`static_baseline` (adjusted for
`Subrace.vital_overrides` when a subrace with an override is present), and SHALL emit a warning —
never a rejection — for any value outside that plausible band. The race's
`static_baseline.magic_power` upper bound is the hard mechanical maximum instead: `magic_power`
above it SHALL be rejected (deterministic `Issue("stats.magic_power", ...)`) before Evennia can
clamp it, and a value below the lower bound warns like the other static axes.

#### Scenario: A stat value outside the race's band produces a warning, not a rejection
- **WHEN** a human character record has `"stats": {"atk_phys": 50, ...}` (above the human
  `static_baseline` ceiling of 22)
- **THEN** the record produces a warning naming `stats.atk_phys`, and this warning alone does not
  cause the record to be rejected

#### Scenario: A stat value inside the race's band produces no warning
- **WHEN** an elf character record has `"stats": {"atk_phys": 88, ...}` (inside the elf
  `static_baseline` band of 70-95)
- **THEN** no warning is produced for `stats.atk_phys`

#### Scenario: A subrace vital_override shifts the checked band
- **WHEN** a beastfolk character record has `"subrace": "foxkin"` and `"stats": {"mp": 60, ...}`
  (outside the species `vital_baseline.mp` band of 30-50, but inside foxkin's overridden band of
  50-70)
- **THEN** no warning is produced for `stats.mp`, since the override band is what is checked

#### Scenario: Magic above the race cap is rejected
- **WHEN** an elf record has `stats.magic_power` greater than its race band's upper bound
  (`RACE_REGISTRY["elf"].static_baseline.magic_power[1]`)
- **THEN** the record is rejected on `stats.magic_power`
