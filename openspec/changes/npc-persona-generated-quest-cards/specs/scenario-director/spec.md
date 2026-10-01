## MODIFIED Requirements

### Requirement: Blueprint validation accepts and bounds the optional npc characterization fields
The scenario director's blueprint validator SHALL require three per-occupant characterization
fields — `display_name` (authored name, bounded non-empty text through the shared bound helper),
`title` (authored NPC title, single-line plain text through the shared bound helper), and
`persona` (a complete compact NPC card) — on every `npc_req` entry, in addition to the existing
role/tier/disposition checks, and SHALL accept the two optional fields `age`/`apparent_age`
(paired) and `portrait: {stable_key}`. The `background` field and any partial persona block SHALL
NOT be part of the proposal shape. Every field SHALL be validated through the shared bound helper
under `world/quests/` (the single rule source, imported read-only): `display_name` and `title`
required with their shared character-set rules; `persona` required and satisfying the compact card
contract (exactly seven fields, required leaves non-empty, per-leaf, identity-section, and total
rendered bounds); `age`/`apparent_age` paired values satisfying `type(value) is int` with the hard
age floor `0` and an upper bound from `NPC_TIER_REGISTRY[tier].race_key` →
`RACE_REGISTRY[race].lifespan`; `portrait` a mapping with exactly one `stable_key` field that is
subject-key-valid. A payload whose tier is unknown, whose occupant is missing `display_name`,
`title`, or `persona`, whose card violates the contract, whose ages are unpaired, non-integer,
negative, or beyond the race lifespan, or whose portrait key is malformed SHALL be rejected and
retried within the budget exactly like today's other semantic failures, and on budget exhaustion
SHALL degrade to the offline template pool.

#### Scenario: A valid named occupant with a title and ages passes validation
- **WHEN** a blueprint's `npc_req` entry declares a known tier plus `display_name`, `title`, a
  valid compact card, paired ages within the race band, and a valid `portrait.stable_key`
- **THEN** the blueprint passes semantic validation and proceeds to compile

#### Scenario: A missing identity field is rejected and retried
- **WHEN** an `npc_req` entry omits `display_name` or `title`
- **THEN** the output is treated as a validation failure, the named error is appended, and the
  pipeline retries within the budget

#### Scenario: A missing or invalid card is rejected and retried
- **WHEN** an `npc_req` entry omits `persona`, carries a card without `speech_style`, carries a
  `background` key, or carries a card whose rendered block exceeds the total bound
- **THEN** the output is treated as a validation failure naming the persona leaf or budget, and the
  pipeline retries within the budget and then degrades to the template pool

#### Scenario: An unpaired, negative, or non-integer declaration is rejected and retried
- **WHEN** an `npc_req` entry declares `age` without `apparent_age`, either age negative, or any
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
- **THEN** the checks execute through the shared `world/quests/` helper, which applies the compact
  card contract, and no inline duplicate of the age/name/title/key/card rules exists in the
  scenario director

## ADDED Requirements

### Requirement: The director prompt asks for a complete card per occupant
The `scenario_director.system` prompt-library text SHALL instruct the model to give every
`npc_req` a `persona` object with the seven compact-card fields, SHALL state which leaves may be
empty (`identity.hidden`, `social_connection`), that `speech_style` describes how the character
talks, and the per-leaf and total bounds, and SHALL contain no shipped NPC's card prose. The
`scenario_director` output schema SHALL require that object with exactly those keys at both levels
and no `background` key.

#### Scenario: The prompt names the card fields and bounds
- **WHEN** the rendered system message is inspected
- **THEN** it names all seven card fields, marks the two optional leaves, and states the bounds

#### Scenario: The schema rejects a background key
- **WHEN** an `npc_req` persona object carries a `background` key or omits `speech_style`
- **THEN** output-schema validation fails

### Requirement: Offline template occupants carry fully authored cards
Every NPC-bearing template in the hand-written template pool SHALL declare, for each occupant, a
fully authored compact card that passes the shared characterization helper, so a degraded,
LLM-free quest generation still materializes occupants with complete characterization.

#### Scenario: Every template occupant carries a valid card
- **WHEN** every `npc_req` of every template in the pool is validated
- **THEN** each carries a compact card that passes the card contract

#### Scenario: An offline-generated occupant spawns with its card
- **WHEN** every `LLM_PROFILES` entry is disabled, a template with an occupant is compiled, registered, and its scene materialized
- **THEN** the spawned occupant's persona equals the template card and carries persona metadata at version 1
