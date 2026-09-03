# scenario-director delta

## MODIFIED Requirements

### Requirement: Blueprint validation accepts and bounds the optional npc characterization fields
The scenario director's blueprint validator SHALL require two per-occupant identity fields —
`display_name` (authored name, bounded non-empty text through the shared bound helper) and `title`
(authored NPC title, single-line plain text through the shared bound helper) — on every `npc_req`
entry, in addition to the existing role/tier/disposition checks, and SHALL accept the three
optional fields `age`/`apparent_age` (paired) and `portrait: {stable_key}`. Every field SHALL be
validated through the shared bound helper under `world/quests/` (the single rule source, imported
read-only): `display_name` and `title` required with their shared character-set rules;
`age`/`apparent_age` paired values satisfying `type(value) is int` with the hard adult floor `18`
and an upper bound from `NPC_TIER_REGISTRY[tier].race_key` → `RACE_REGISTRY[race].lifespan`;
`portrait` a mapping with exactly one `stable_key` field that is subject-key-valid. A payload whose
tier is unknown, whose occupant is missing `display_name` or `title`, whose ages are unpaired,
non-integer, underage, or beyond the race lifespan, or whose portrait key is malformed SHALL be
rejected and retried within the budget exactly like today's other semantic failures.

#### Scenario: A valid named occupant with a title and ages passes validation
- **WHEN** a blueprint's `npc_req` entry declares a known tier plus `display_name`, `title`,
  paired ages within the race band, and a valid `portrait.stable_key`
- **THEN** the blueprint passes semantic validation and proceeds to compile

#### Scenario: A missing identity field is rejected and retried
- **WHEN** an `npc_req` entry omits `display_name` or `title`
- **THEN** the output is treated as a validation failure, the named error is appended, and the
  pipeline retries within the budget

#### Scenario: An unpaired, underage, or non-integer declaration is rejected and retried
- **WHEN** an `npc_req` entry declares `age` without `apparent_age`, either age below 18, or any
  age whose `type` is not exactly `int` (including booleans and `None`)
- **THEN** the output is treated as a validation failure, the error is appended, and the pipeline
  retries within the budget

#### Scenario: An out-of-race-band age is rejected
- **WHEN** an `npc_req` entry declares an age above its tier race's lifespan upper bound
- **THEN** the blueprint is rejected and retried; no compiled requirement is produced

#### Scenario: A malformed portrait object is rejected
- **WHEN** `portrait` is not a mapping, carries keys other than exactly one `stable_key`, or its
  `stable_key` is empty, colon-containing, or overlong
- **THEN** the blueprint is rejected and retried

#### Scenario: The shared helper is the sole rule implementation
- **WHEN** a blueprint's per-occupant fields are validated
- **THEN** the checks execute through the shared `world/quests/` helper, and no inline duplicate of
  the age/name/title/key rules exists in the scenario director
