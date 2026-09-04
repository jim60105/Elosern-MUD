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

### Requirement: ScenarioDirector prompt construction is deterministic, bounded, and faithful
`world/ai/scenario_director.py::build_scenario_prompt(context)` SHALL return a (system, user) message
pair. The system message SHALL be the prompt library's `scenario_director.system` key rendered via
`render_prompt("scenario_director.system", name_inspiration=<inspiration bank>)` — the library is the
sole source of the system prompt text, and the module SHALL NOT embed it as a Python constant. The
rendered system message SHALL fix the director role in 伊洛瑟恩大陸, the 正體中文 language, the
fidelity rule (reference only known world content, never invent ranks, archetypes, NPC tiers, item
keys, or rewards), and the JSON output contract that is the `QuestBlueprint` shape. The user message
SHALL serialize the request context (requested quest type, allowed rank, issuer branch, anchor)
with stable sorted JSON serialization. The prompt SHALL be bounded by fixed per-field length caps and
a bounded total size, and SHALL contain only plain JSON-compatible data with no live entity
references, so identical input always produces byte-identical prompts.

The system message SHALL additionally carry a deterministic name-inspiration bank: the module SHALL
compute `zlib.crc32` over the serialized bounded request context, roll a fixed number of names
through the read-only `world.rules.namegen.roll_name_for_race(None, "", Random(seed))`, and inject
them as the `name_inspiration` values together with the library text's guidance that the names are
inspiration only — directly usable, or adjustable to the character's declared sex and background —
countering same-name bias when the author runs out of inspiration, and that every `npc_req` entry
MUST carry the required identity fields `display_name` and `title`. The bank remains an
inspiration-only surface: the rolled names are never a fallback final name written by the system,
and the injection itself SHALL add no output-schema field; the requiredness of `display_name` and
`title` is enforced by the shared characterization validator, not by the prompt.

#### Scenario: Identical contexts produce identical prompts
- **WHEN** `build_scenario_prompt()` is called twice with the same context
- **THEN** both calls return byte-identical system and user messages, including an identical
  name-inspiration bank

#### Scenario: The name-inspiration bank is context-seeded and rolled through the rule layer
- **WHEN** `build_scenario_prompt()` renders the system message
- **THEN** every injected name comes from `world.rules.namegen.roll_name_for_race` with a
  `Random` seeded from `zlib.crc32` of the serialized bounded context, and the same context always
  yields the same names while a different context may yield a different bank

#### Scenario: The injected names are framed as inspiration only
- **WHEN** the system message is inspected
- **THEN** the bank is presented with the library text marking the names as 僅供靈感 (directly
  usable or adjustable to sex and background) and stating that `npc_req` entries carry the required
  `display_name` and `title`

#### Scenario: The injection changes no output-schema field
- **WHEN** a blueprint uses a bank name verbatim as `display_name`, adapts a bank name, or declares
  a name absent from the bank
- **THEN** the validator's decision depends only on the shared identity rules — a bank-external name
  is accepted, an omitted `display_name` or `title` is rejected — and the injection adds no schema
  field of its own

#### Scenario: An oversized context produces a bounded prompt
- **WHEN** `build_scenario_prompt()` is called with fields exceeding the caps
- **THEN** the returned messages stay within the fixed bounds and remain valid prompt text

#### Scenario: The prompt instructs the blueprint output contract
- **WHEN** the system message is inspected
- **THEN** it directs output as a `QuestBlueprint` JSON object in Traditional Chinese and forbids
  inventing world references beyond the known registries

#### Scenario: The prompt carries plain data, never live references
- **WHEN** the serialized user message is inspected for a request naming branch
  `guild_branch_altoria` and anchor `capital_altoria`
- **THEN** it contains those keys and contains no live entity object anywhere in the serialization

#### Scenario: The system message is sourced from the prompt library
- **WHEN** the ScenarioDirector system message is inspected
- **THEN** its template text equals the library's `scenario_director.system` key — the prompt-library
  file is the only place its text (including the naming-guidance sentence) is defined — and the
  module renders it rather than embedding any of the text as a Python constant

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward` and an issuer branch key. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation. The generated `QuestDefinition.key`
SHALL be a stable content digest over the canonical runtime definition serialization **plus the
canonical serialization of the compiled per-stage spawn requirements**, so two blueprints with
identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`,
or `npc_reqs`, or any carried characterization field — the required `display_name` and `title`, the
optional paired `age`/`apparent_age`, or portrait `stable_key`) always yield different keys and equal
content always yields an equal key. `register_generated_quest(...)` SHALL register the compiled
`QuestDefinition`, its `GuildQuestOffer`, **and its per-stage spawn requirements (readable through
`scene_requirements_for(definition_key)`)** as one all-or-nothing operation: it SHALL preflight all
three registries' equal/conflict states before writing any of them, SHALL roll back every write if
any later write fails, and SHALL leave no spawn-requirement entry behind on a rolled-back
publication, so a generated definition is never left registered without its offer or its
requirements. `scene_requirements_for` SHALL return an empty tuple for any key with no registered
requirements (for example a hand-written catalog quest). Raw AI-shaped dicts SHALL still be rejected
by `register_quest_definition` — the compile boundary is the sole sanctioned translator and AI dicts
never enter `QUEST_DEFINITION_REGISTRY` directly.

#### Scenario: A valid blueprint compiles to a registrable definition
- **WHEN** a validated blueprint passes through `compile_quest_blueprint`
- **THEN** the compiled `QuestDefinition` passes `validate_definition` and its reward and issuer are
  the blueprint's declared values

#### Scenario: An invalid proposal fails compile before any change
- **WHEN** a payload declares reward copper outside its rank's band or an unknown item key
- **THEN** `compile_quest_blueprint` raises `QuestCompileError` and neither the definition registry
  nor the offer registry changes

#### Scenario: Generated quest registration is idempotent
- **WHEN** the same compiled quest (definition, offer, and requirements all equal) is registered twice
- **THEN** one `QuestDefinition` entry, one `GuildQuestOffer` entry, and one spawn-requirement entry
  exist, and the second call is a no-op

#### Scenario: Equal content yields equal keys
- **WHEN** the same blueprint content is compiled twice
- **THEN** both compilations produce the same deterministic definition key

#### Scenario: Different scenes under equal runtime stages yield different keys
- **WHEN** two blueprints have identical runtime stages but differ only in scene requirements (for
  example a different `npc_req` tier or `scene_sentence`)
- **THEN** they compile to different definition keys, so neither can silently overwrite the other's
  spawn requirements

#### Scenario: Compiled requirements carry the characterization fields
- **WHEN** an accepted blueprint's `npc_req` entry declares the required `display_name` and `title`
  plus paired ages and a portrait `stable_key`
- **THEN** the compiled per-stage spawn requirements expose all four in deterministic order

#### Scenario: Characterization differences change the generated key
- **WHEN** two accepted blueprints differ only in a carried characterization field
- **THEN** their compiled `QuestDefinition.key` digests differ

#### Scenario: An option-field-less blueprint compiles with the identity-bearing digest
- **WHEN** an accepted blueprint declares no optional characterization fields (no ages, no portrait)
- **THEN** it compiles with the same deterministic registration behavior, and its digest includes
  the required `display_name` and `title` of every occupant

#### Scenario: Spawn requirements are registered with the publication
- **WHEN** a compiled quest is registered and `scene_requirements_for(definition_key)` is read
- **THEN** it returns the compiled stage's spawn requirements, so the SceneBuilder can materialize
  the scene when the player arrives

#### Scenario: A conflicting offer rolls back the definition, its requirements, and the offer
- **WHEN** a compiled definition is new but a conflicting `GuildQuestOffer` already exists for its
  `(definition_key, issuer_branch_key)` identity, or a conflicting spawn-requirement entry already
  exists for its definition key
- **THEN** neither the definition registry, the offer registry, nor the spawn-requirement registry
  changes, and a named error is raised

#### Scenario: Hand-written definitions read back empty requirements
- **WHEN** `scene_requirements_for` is called for a catalog (hand-written) definition key that was
  never compiled through the boundary
- **THEN** it returns an empty tuple and no requirement entry is fabricated

#### Scenario: Raw AI-shaped dicts are still rejected by the runtime registry
- **WHEN** a plain dict shaped like a blueprint is passed to `register_quest_definition`
- **THEN** registration rejects it without modifying `QUEST_DEFINITION_REGISTRY`

#### Scenario: The compiler re-validates every guardrail-checked constraint
- **WHEN** a payload that was never guardrail-validated is passed to `compile_quest_blueprint`
- **THEN** every constraint the semantic validators check (rank, reward band, item keys, archetype,
  tiers, branch, indices, deadline, scene-bound rules) is re-checked deterministically, so no
  proposal can reach the registry unchecked
