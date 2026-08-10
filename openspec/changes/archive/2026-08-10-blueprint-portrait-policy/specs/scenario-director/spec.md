## MODIFIED Requirements

### Requirement: Blueprint validation accepts and bounds the optional npc characterization fields
The scenario director's blueprint validator SHALL accept the four optional per-occupant fields —
`display_name`, paired `age`/`apparent_age`, and `portrait: {stable_key}` — on `npc_req` entries,
in addition to the existing role/tier/disposition checks. Every declared field SHALL be validated
through the shared bound helper under `world/quests/` (the single rule source, imported read-only):
`display_name` bounded non-empty text; `age`/`apparent_age` paired values satisfying
`type(value) is int` with the hard adult floor `18` and an upper bound from
`NPC_TIER_REGISTRY[tier].race_key` → `RACE_REGISTRY[race].lifespan`; `portrait` a mapping with
exactly one `stable_key` field that is subject-key-valid. A payload whose tier is unknown, whose
ages are unpaired, non-integer, underage, or beyond the race lifespan, or whose portrait key is
malformed SHALL be rejected and retried within the budget exactly like today's other semantic
failures. Entries without the optional fields SHALL validate unchanged.

#### Scenario: A valid named occupant with ages passes validation
- **WHEN** a blueprint's `npc_req` entry declares a known tier plus `display_name`, paired ages
  within the race band, and a valid `portrait.stable_key`
- **THEN** the blueprint passes semantic validation and proceeds to compile

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
- **WHEN** a blueprint's optional fields are validated
- **THEN** the checks execute through the shared `world/quests/` helper, and no inline duplicate of
  the age/name/key rules exists in the scenario director

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward` and an issuer branch key. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation. The generated `QuestDefinition.key`
SHALL be a stable content digest over the canonical runtime definition serialization **plus the
canonical serialization of the compiled per-stage spawn requirements**, so two blueprints with
identical runtime stages but different scene requirements (archetype, `anchor_near`,
`scene_sentence`, `npc_reqs`, **or any carried characterization field — `display_name`, paired
`age`/`apparent_age`, or portrait `stable_key`**) always yield different keys and equal content
always yields an equal key. `register_generated_quest(...)` SHALL register the compiled
`QuestDefinition`, its `GuildQuestOffer`, **and its per-stage spawn requirements (readable through
`scene_requirements_for(definition_key)`)** as one all-or-nothing operation: it SHALL preflight all
three registries' equal/conflict states before writing any of them, SHALL roll back every write if
any later write fails, and SHALL leave no spawn-requirement entry behind on a rolled-back
publication, so a generated definition is never left registered without its offer or its
requirements. `scene_requirements_for` SHALL return an empty result for unknown keys.

#### Scenario: Compiled requirements carry the characterization fields
- **WHEN** an accepted blueprint's `npc_req` entry declares `display_name`, paired ages, and a
  portrait `stable_key`
- **THEN** the compiled per-stage spawn requirements expose all three in deterministic order

#### Scenario: Characterization differences change the generated key
- **WHEN** two accepted blueprints differ only in a carried characterization field
- **THEN** their compiled `QuestDefinition.key` digests differ

#### Scenario: A field-less blueprint compiles unchanged
- **WHEN** an accepted blueprint declares no optional characterization fields
- **THEN** the compiled requirements, digest, and registration behave exactly as today
