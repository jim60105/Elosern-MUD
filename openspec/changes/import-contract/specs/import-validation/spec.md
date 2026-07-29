## ADDED Requirements

### Requirement: validate.py provides a CLI that validates one or more record files
`world/imports/validate.py` SHALL be runnable as `python -m world.imports.validate <files...>`,
accepting one or more JSON file paths (including shell-expanded globs such as `cards/*.json`),
classifying each by its required `record_type` field as a character record or a world-info record,
validating each against the corresponding schema and semantic rules, and printing a report naming,
for every issue, which record, which field, and why.

#### Scenario: A clean batch of files exits successfully
- **WHEN** `python -m world.imports.validate` is run against a set of files that all pass every
  reject-level check
- **THEN** the process exits with status 0 and the report shows no rejections for any file

#### Scenario: Any single rejection in the batch causes a non-zero exit
- **WHEN** `python -m world.imports.validate` is run against a set of files where exactly one file
  fails a reject-level check
- **THEN** the process exits with a non-zero status, and the report identifies that specific file,
  the specific field that failed, and the reason

#### Scenario: A record with a missing or unrecognized record_type is reported as a rejection, not routed to either schema
- **WHEN** a file contains a JSON object whose `record_type` is absent, `null`, or a value other
  than `"character"`/`"world_entry"`
- **THEN** the report flags that file as rejected for its `record_type`, naming both valid values,
  and this counts as a rejection for exit-code purposes — the file is never validated against
  either `CHARACTER_SCHEMA_V1` or `WORLD_SCHEMA_V1` on a guess

### Requirement: The CLI prints a prominent banner whenever any check is running in degraded mode
Whenever `validate_batch()`'s result reports one or more degraded checks (currently: the pluggable
skill-registry check, when `world.skills.registry.SKILL_REGISTRY` is not importable), `validate.py`
SHALL print a banner naming every degraded check and the reason it is degraded, before any
per-record report output, on every run for which the condition holds — never only in a verbose
mode, and never suppressed by an otherwise-clean result.

#### Scenario: The banner appears before the per-record report when a check is degraded
- **WHEN** the skill registry is unavailable and `validate.py` is run against any batch of files
- **THEN** the printed output's degraded-mode banner appears before any per-record validation
  output, naming `skill-registry` and the reason it is not being enforced

#### Scenario: The banner appears even when every record in the batch is otherwise valid
- **WHEN** the skill registry is unavailable but every file in the batch passes every other
  reject-level check
- **THEN** the CLI still prints the degraded-mode banner, and the process still exits 0 — a clean
  exit code does not suppress the banner

#### Scenario: No banner is printed once the degraded check is no longer degraded
- **WHEN** the skill registry is available (a resolvable `SKILL_REGISTRY`)
- **THEN** the CLI prints no degraded-mode banner, since `validate_batch()` reports zero degraded
  checks

### Requirement: race and subrace must resolve in the lore registries, with subrace cross-checked against race
`validate.py` SHALL reject a character record whose `race` does not exist as a key in
`world.lore.races.RACE_REGISTRY`, and SHALL reject a record whose `subrace` (when present) either
does not exist in `world.lore.races.SUBRACE_REGISTRY` or whose `race_key` does not equal the
record's own `race`.

#### Scenario: An unknown race is rejected
- **WHEN** a character record has `"race": "dragonkin"` (not a `RACE_REGISTRY` key)
- **THEN** the record is rejected, naming the `race` field

#### Scenario: An unknown subrace is rejected
- **WHEN** a character record has `"race": "elf"` and `"subrace": "sunkin"` (not a
  `SUBRACE_REGISTRY` key)
- **THEN** the record is rejected, naming the `subrace` field

#### Scenario: A subrace belonging to a different race than declared is rejected
- **WHEN** a character record has `"race": "human"` and `"subrace": "ciaran"` (an elf subrace)
- **THEN** the record is rejected, naming the mismatch between `subrace` and `race`

#### Scenario: A record with no subrace is not rejected for that reason
- **WHEN** a character record omits `subrace` entirely
- **THEN** no rejection is produced for the subrace check, since `subrace` is optional

### Requirement: disguised_stats keys must be a subset of stats keys
`validate.py` SHALL reject a character record where any key present in `disguised_stats` is not
also present in `stats`, naming the offending key(s).

#### Scenario: A disguised_stats key absent from stats is rejected
- **WHEN** a character record's `stats` has no `magic_level` key but `disguised_stats` sets
  `"magic_level": 30`
- **THEN** the record is rejected, naming `magic_level` as the offending disguised_stats key

#### Scenario: A disguised_stats that is a proper subset of stats keys passes this check
- **WHEN** a character record's `disguised_stats` keys are all also present in `stats`
- **THEN** this check produces no rejection

### Requirement: stats outside the race's plausible band produce a warning, never a rejection
`validate.py` SHALL compare each present `stats` value against the corresponding band from
`world.lore.races.RACE_REGISTRY[race].vital_baseline`/`static_baseline`/`magic_cap` (adjusted for
`Subrace.vital_overrides` when a subrace with an override is present), and SHALL emit a warning —
never a rejection — for any value outside that band.

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

### Requirement: sexual_baseline shape violations are rejections
`validate.py` SHALL treat any `sexual_baseline` that fails `CHARACTER_SCHEMA_V1`'s structural
constraints (missing required fields, or any level value outside its vocabulary) as a rejection,
distinct from the warning-only stats-band check.

#### Scenario: An out-of-vocabulary sexual_baseline value is a rejection, not a warning
- **WHEN** a character record's `sexual_baseline.shame` is a value not in `SHAME_LEVELS`
- **THEN** the record is rejected, naming the `sexual_baseline.shame` field — this does not appear
  in the report as a warning

### Requirement: skills and passives are checked against a pluggable skill registry that degrades to a warning when the registry is unavailable
`validate.py` SHALL attempt to resolve a skill registry from `world.skills.registry.SKILL_REGISTRY`.
When that module is not importable, every key in `skills` and `passives` SHALL produce a warning
stating the registry is unavailable, never a rejection. When the module is importable, every key in
`skills` or `passives` not found in the resolved registry SHALL produce a rejection.

#### Scenario: Skill keys are warnings when the registry module does not exist
- **WHEN** `world.skills.registry` is not importable (as is the case for this change, since change
  5 has not been implemented) and a character record's `skills` includes `"fire_mastery"`
- **THEN** a warning is produced naming `fire_mastery` and stating the registry is unavailable, and
  this does not cause rejection

#### Scenario: An unknown skill key is a rejection once the registry is available
- **WHEN** `world.skills.registry.SKILL_REGISTRY` is importable and does not contain the key
  `"nonexistent_skill"`, and a character record's `skills` includes `"nonexistent_skill"`
- **THEN** the record is rejected, naming `nonexistent_skill`

#### Scenario: A known skill key produces neither a warning nor a rejection once the registry is available
- **WHEN** `world.skills.registry.SKILL_REGISTRY` is importable and contains the key
  `"fire_mastery"`, and a character record's `skills` includes `"fire_mastery"`
- **THEN** no warning or rejection is produced for that key

### Requirement: The skill-registry promotion is verified against the real module, not only a mock
Alongside the mocked-import test of the degrade/promote logic, the test suite SHALL include a test
that checks whether `world.skills.registry.SKILL_REGISTRY` is genuinely importable in the current
environment — skipping itself while it is not — and, once it genuinely is, asserts that an unknown
skill key is rejected. This test SHALL NOT be satisfiable by a mock; it exists so that change 5
cannot be considered complete while its registry leaves skill-key validation permanently lenient.

#### Scenario: The self-arming test skips while the registry does not genuinely exist
- **WHEN** the test suite runs in an environment where `world.skills.registry` does not exist
- **THEN** the self-arming skill-registry test reports as skipped, not passed and not failed

#### Scenario: The self-arming test actively asserts rejection once the registry genuinely exists
- **WHEN** the test suite runs in an environment where `world.skills.registry.SKILL_REGISTRY`
  genuinely exists and is importable (not mocked)
- **THEN** the self-arming skill-registry test executes and fails if an unknown skill key is not
  rejected by `_check_skills()`

### Requirement: Import validation is all-or-nothing across a batch of files
`validate.py` SHALL treat a set of files passed to one invocation as one batch: if any file in the
batch produces a rejection, the batch as a whole is reported as failed (non-zero exit), even though
individual files within the batch may have produced zero rejections of their own.

#### Scenario: One rejecting file in a batch of otherwise-valid files fails the whole batch
- **WHEN** three files are validated together, two of which pass every check cleanly and one of
  which has an age-17 record
- **THEN** the batch-level result is failure, and the report still lists all three files' individual
  results (the two clean ones marked valid, the age-17 one marked rejected)

### Requirement: Every reported issue names the record, the field, and the reason
Every rejection or warning `validate.py` reports SHALL include the record's `key` (or file path if
`key` cannot be determined), the specific field path within the record, and a human-readable reason.

#### Scenario: A rejection report includes all three pieces of information
- **WHEN** a character record with `"key": "example_npc"` fails the age gate
- **THEN** the reported issue names `example_npc` (or its file path), the field `age`, and states
  the value found and the required minimum
