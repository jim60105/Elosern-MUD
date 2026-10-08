## Purpose

Defines the scenario-director layer that generates validated quest blueprints through the guarded generative pipeline. The layer is deterministic-first: prompt construction is stable and bounded, semantic validators bound every world reference, every failure path degrades to the hand-written template pool, and the canonical payload contract is shared with the deterministic compile boundary so the guardrail and the compiler cannot drift.

## Requirements

### Requirement: Scene-archetype and NPC-tier registries are immutable lore data
`world/lore/scene_archetypes.py` SHALL define a frozen `SceneArchetype` dataclass and a module-level
`SCENE_ARCHETYPE_REGISTRY: dict[str, SceneArchetype]` keyed by scene-kind keys, and
`world/lore/npc_tiers.py` SHALL define a frozen `NPCTier` dataclass and a module-level
`NPC_TIER_REGISTRY: dict[str, NPCTier]` keyed by role-tier keys. Both registries SHALL be non-empty,
frozen, and consumable by any package without violating the single-writer or deterministic-path
boundaries.

#### Scenario: Both registries are non-empty and closed
- **WHEN** `SCENE_ARCHETYPE_REGISTRY` and `NPC_TIER_REGISTRY` are inspected
- **THEN** each maps its documented keys to frozen values, and no consumer-defined extension can
  mutate either mapping

#### Scenario: The design-document example vocabulary resolves
- **WHEN** a blueprint references archetype `forest_path` and NPC tier `civilian`
- **THEN** both keys resolve to registry entries, so the design §7.1 example vocabulary is valid

#### Scenario: Every NPC tier resolves a deterministic stat mapping
- **WHEN** each `NPC_TIER_REGISTRY` entry's `race_key` and `static_tier_key` are looked up in
  `RACE_REGISTRY` and `STATIC_TIER_REGISTRY`
- **THEN** every lookup resolves, and the referenced static tier belongs to the referenced race, so
  the SceneBuilder's tier-to-stats derivation is fully lore-backed

#### Scenario: Registry consumers stay inside their boundaries
- **WHEN** the repository-wide transport-boundary contract scans `world/ai/` and the
  deterministic-path ban scans `world/quests/`
- **THEN** both consumers reference the lore registry values without importing a state writer or
  duplicating the constants

#### Scenario: The registry key vocabularies are the documented examples
- **WHEN** the registries are keyed
- **THEN** scene-kind keys include (for example) `forest_path`, `tavern_interior`, `dungeon_interior`, `city_street`, `wilderness_path`, `mountain_path`, `ruin_interior`, `coastal_path`, `cave_interior`, `shrine_interior`, and role-tier keys include (for example) `civilian`, `guard`, `merchant`, `adventurer`, `mage`, `noble`, `bandit`, `priest`, `knight`

#### Scenario: Each NPC tier resolves its physical stats from lore
- **WHEN** an `NPCTier` is declared
- **THEN** it carries `race_key` and `static_tier_key`, naming immutable entries of `RACE_REGISTRY` and `STATIC_TIER_REGISTRY`, so a role tier's deterministic physical stats resolve from the lore tables and change 21's SceneBuilder never duplicates balance constants

#### Scenario: Consumers read the registries instead of duplicating
- **WHEN** `world/ai/` validators, change 21's SceneBuilder, and the `world/quests` compiler consume tier data
- **THEN** they read these registry values rather than duplicating constants

### Requirement: QuestBlueprint is the closed, deeply immutable AI proposal type
`world/ai/scenario_director.py` SHALL define frozen `QuestBlueprint` dataclasses whose `quest_type`
SHALL be restricted to exactly the five `QuestType` values (採集, 討伐, 護衛, 探索, 緊急) and whose
stages SHALL carry explicit integer `index` values in a contiguous sequence starting at zero. No
blueprint field SHALL contain a mutable dict or list, and construction SHALL reject any mutable
container so immutability is enforced by the constructor, not only by the dataclass.

#### Scenario: A valid blueprint preserves explicit stage indices
- **WHEN** a blueprint is constructed with stages carrying indices 0 and 1
- **THEN** both explicit indices remain inspectable on the frozen value

#### Scenario: Blueprint content cannot be mutated after construction
- **WHEN** a constructed blueprint's stages, reward, or failure is accessed
- **THEN** no nested mutable collection is available through which validated content can be changed

#### Scenario: Quest type is a closed vocabulary
- **WHEN** content attempts to construct a blueprint whose type is outside the five `QuestType`
  values
- **THEN** construction fails and no `QuestBlueprint` value is produced

#### Scenario: The proposal type stays distinct from the runtime type
- **WHEN** proposals face the runtime quest registry
- **THEN** `QuestBlueprint` is a distinct proposal type from the runtime `QuestDefinition`, raw mappings are NOT accepted by the runtime quest registry, and the two types are not interchangeable

### Requirement: ScenarioDirector prompt construction is deterministic, bounded, and faithful
`world/ai/scenario_director.py::build_scenario_prompt(context)` SHALL return a (system, user) message
pair. The system message SHALL be the prompt library's `scenario_director.system` key rendered via
`render_prompt("scenario_director.system", name_inspiration=<inspiration bank>)` — the library is the
sole source of its text — and SHALL carry a deterministic name-inspiration bank. Identical input
SHALL always produce byte-identical prompts.

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

#### Scenario: The rendered system message fixes role, language, fidelity, and contract
- **WHEN** the rendered system message is inspected
- **THEN** it fixes the director role in 伊洛瑟恩大陸, the 正體中文 language, the fidelity rule (reference only known world content, never invent ranks, archetypes, NPC tiers, item keys, or rewards), and the JSON output contract that is the `QuestBlueprint` shape

#### Scenario: The user message serializes the request context stably
- **WHEN** the user message is built
- **THEN** it serializes the request context (requested quest type, allowed rank, issuer branch, anchor) with stable sorted JSON serialization

#### Scenario: The bank rolls a fixed count through the read-only rule layer
- **WHEN** the module builds the inspiration bank
- **THEN** it computes `zlib.crc32` over the serialized bounded request context and rolls a fixed number of names through the read-only `world.rules.namegen.roll_name_for_race(None, "", Random(seed))`, injecting them as the `name_inspiration` values

#### Scenario: The prompt is size-bounded plain data
- **WHEN** a prompt is constructed
- **THEN** it is bounded by fixed per-field length caps and a bounded total size and contains only plain JSON-compatible data with no live entity references

#### Scenario: The bank is inspiration only, never a system-written fallback
- **WHEN** the bank is injected with the library text's guidance that the names are inspiration only — directly usable, or adjustable to the character's declared sex and background — countering same-name bias when the author runs out of inspiration
- **THEN** the rolled names are never a fallback final name written by the system

#### Scenario: Identity requiredness is the validator's job, not the prompt's
- **WHEN** the prompt states that every `npc_req` entry MUST carry the required identity fields `display_name` and `title`
- **THEN** the injection itself adds no output-schema field, and the requiredness of `display_name` and `title` is enforced by the shared characterization validator, not by the prompt

### Requirement: generate_quest_blueprint runs the guarded pipeline and enforces the request context
`world/ai/scenario_director.py::generate_quest_blueprint(client, *, context)` SHALL require the
client as an injected argument and SHALL reject an explicit `None` with a named
`ScenarioDirectorClientRequiredError` as its first statement, before any prompt construction or
transport work. It SHALL apply a post-guardrail fitness gate that re-checks the parsed blueprint
against the request context (allowed rank, requested quest type, issuer branch, anchor).

#### Scenario: A valid context-fitting blueprint resolves to a frozen QuestBlueprint
- **WHEN** `generate_quest_blueprint()` is called with a client that returns accepted blueprint JSON
  that fits the request context
- **THEN** the Deferred resolves to a frozen `QuestBlueprint` equal to the fixture and no game state
  changes

#### Scenario: An explicit None client is rejected before any prompt or transport work
- **WHEN** `generate_quest_blueprint()` is called with `client=None`
- **THEN** it errbacks with `ScenarioDirectorClientRequiredError` without building a prompt or
  contacting a transport

#### Scenario: A valid but context-misfitting blueprint is replaced by a template
- **WHEN** a client returns a schema-valid blueprint whose rank or branch does not fit the request
  context
- **THEN** the call treats it as a degrade trigger and resolves to a context-fitting template
  blueprint instead of returning the inapplicable proposal

#### Scenario: A disabled profile draws a template-pool blueprint
- **WHEN** the `scenario_director` profile is disabled and `generate_quest_blueprint()` is called
- **THEN** the Deferred resolves to a valid, context-fitting `QuestBlueprint` drawn deterministically
  from the template pool, with zero client calls

#### Scenario: Transport failure and exhausted retries draw a template-pool blueprint
- **WHEN** the client errbacks with a transport failure, or every retry returns output that fails
  schema or semantic validation
- **THEN** the Deferred resolves to a valid `QuestBlueprint` drawn from the template pool, never to
  the invalid output and never to `None`

#### Scenario: No compatible template errbacks with a named error
- **WHEN** the request context has no compatible template in the pool
- **THEN** the call errbacks with `ScenarioDirectorTemplateError` and no blueprint is fabricated

#### Scenario: Missing registration fails loudly with a named error
- **WHEN** `generate_quest_blueprint()` is called before the `scenario_director` hooks are installed,
  including after a test has reset the shared guardrail registries
- **THEN** the call errbacks with a named `ScenarioDirectorNotRegisteredError` rather than silently
  fabricating a blueprint

#### Scenario: The pipeline runs through the descriptor and the guarded call
- **WHEN** the call proceeds with a client
- **THEN** it builds a `ChatRequestDescriptor` whose messages come from `build_scenario_prompt(context)` and whose `schema_id` is `"scenario_director"`, yields the `scenario_director` layer's `guarded_call`, and `json.loads` the accepted text into a frozen `QuestBlueprint`

#### Scenario: A context-misfitting valid blueprint is a degrade trigger
- **WHEN** a blueprint is schema- and semantically valid but does not fit the request context
- **THEN** it is treated as a degrade trigger

#### Scenario: Any degrade trigger draws a context-fitting template
- **WHEN** any degrade trigger occurs (disabled profile, transport failure, exhausted retries, or context misfit)
- **THEN** the call resolves to a deterministic draw from the hand-written template pool that also fits the context

#### Scenario: No compatible template is a named errback
- **WHEN** no compatible template exists for the context
- **THEN** the call errbacks with a named `ScenarioDirectorTemplateError`

#### Scenario: A registered layer never resolves invalid or None
- **WHEN** the layer is registered, or a call is made before registration
- **THEN** the call never resolves to an invalid proposal or to `None`, and a pre-registration call errbacks with a named `ScenarioDirectorNotRegisteredError`

### Requirement: Semantic validators bound rank, reward, archetype, NPC tier, and every world reference
The `scenario_director` layer SHALL register semantic validators under stable names so the shared
pipeline retries on violations and degrades on exhaustion, covering the rank, reward, archetype, tier,
branch, index, deadline, string, and placeholder rejections pinned by the scenarios below. Each
rejected attempt SHALL append a concrete validation message before retrying.

#### Scenario: An unknown rank is rejected and retried
- **WHEN** a client returns a blueprint whose `rank` is not in `GUILD_RANK_REGISTRY`
- **THEN** the pipeline rejects it, appends the error, and retries rather than returning the
  invalid blueprint

#### Scenario: Out-of-band reward copper is rejected
- **WHEN** a client returns a blueprint whose reward copper exceeds that rank's band ceiling
- **THEN** the pipeline rejects it and does not return the blueprint

#### Scenario: Unknown archetype and NPC tier are rejected
- **WHEN** a client returns a blueprint whose `location_req.archetype` or `npc_req` tier is not in
  the lore registries
- **THEN** the pipeline rejects it and does not return the blueprint

#### Scenario: Non-contiguous stage indices are rejected
- **WHEN** a client returns a blueprint with stage indices 0 and 2
- **THEN** the pipeline rejects it and does not return the blueprint

#### Scenario: A valid bounded blueprint passes on the first attempt
- **WHEN** a client returns a blueprint whose rank, reward, archetype, tiers, branch, indices,
  deadline, and strings are all valid and within bounds
- **THEN** the pipeline returns it as a frozen `QuestBlueprint` with no retry

#### Scenario: Out-of-band or malformed rewards are rejected
- **WHEN** a blueprint declares reward copper below the rank's `reward_min_copper` or above its `reward_max_copper` (with S honoring its open upper bound), non-integer or negative merit, or reward item keys outside `ITEM_REGISTRY` with non-positive quantities or duplicate keys
- **THEN** the validators reject it

#### Scenario: A rank outside the registry is rejected
- **WHEN** a blueprint declares a `rank` outside `GUILD_RANK_REGISTRY`
- **THEN** the validators reject it

#### Scenario: A monster tier or issuer branch outside the registries is rejected
- **WHEN** a DEFEAT stage declares a `monster_tier` outside `MONSTER_TIER_REGISTRY` or the issuer branch is outside `GUILD_BRANCH_REGISTRY`
- **THEN** the validators reject it

#### Scenario: A bad deadline is rejected
- **WHEN** a blueprint declares a `deadline_hours` that is neither `None` nor a positive integer
- **THEN** the validators reject it

#### Scenario: Bad strings, oversize fields, and placeholder leaks are rejected
- **WHEN** a blueprint carries empty or non-CJK `name`/`scene_sentence`, fields exceeding length caps, or leaked template-placeholder syntax
- **THEN** the validators reject it

### Requirement: Blueprint validation accepts and bounds the optional npc characterization fields
The scenario director's blueprint validator SHALL require three per-occupant characterization
fields — `display_name`, `title`, and `persona` — on every `npc_req` entry, in addition to the
existing role/tier/disposition checks, and SHALL accept the two optional fields `age`/`apparent_age`
(paired) and `portrait: {stable_key}`, with every field validated through the shared bound helper
under `world/quests/` — the single rule source.

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

#### Scenario: Too many card-bearing occupants are rejected
- **WHEN** a blueprint declares four `npc_req` entries across its stages
- **THEN** the output is treated as a validation failure naming the occupant total and retried within the budget

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

#### Scenario: The required fields carry their shared shapes
- **WHEN** the required characterization fields are validated
- **THEN** `display_name` is authored name as bounded non-empty text through the shared bound helper and `title` is authored NPC title as single-line plain text through the shared bound helper, each required with its shared character-set rules

#### Scenario: The persona card obeys the compact card contract
- **WHEN** `persona` is validated
- **THEN** it is required and must satisfy the compact card contract (exactly seven fields, required leaves non-empty, per-leaf, identity-section, and total rendered bounds)

#### Scenario: The ages obey int-ness, floor, and race lifespan
- **WHEN** `age`/`apparent_age` are validated
- **THEN** they must be paired values satisfying `type(value) is int` with the hard age floor `0` and an upper bound from `NPC_TIER_REGISTRY[tier].race_key` → `RACE_REGISTRY[race].lifespan`

#### Scenario: The portrait key must be subject-key-valid
- **WHEN** `portrait` is validated
- **THEN** it must be a mapping with exactly one `stable_key` field that is subject-key-valid

#### Scenario: The proposal shape excludes background and partial cards
- **WHEN** a proposal declares the `background` field or any partial persona block
- **THEN** neither is part of the proposal shape

#### Scenario: Every characterization violation retries then degrades
- **WHEN** a payload's tier is unknown, its occupant is missing `display_name`, `title`, or `persona`, its card violates the contract, its ages are unpaired, non-integer, negative, or beyond the race lifespan, or its portrait key is malformed
- **THEN** it is rejected and retried within the budget exactly like today's other semantic failures, and on budget exhaustion the call degrades to the offline template pool

#### Scenario: The occupant total is capped at three
- **WHEN** a blueprint declares `npc_req` occupants across its stages
- **THEN** it declares at most three in total across all of its stages, so its occupant cards fit one bounded model response, and a blueprint exceeding that total is rejected and retried like any other semantic failure

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

#### Scenario: The prompt sizes the cards and caps the occupants
- **WHEN** the prompt-library text is inspected
- **THEN** it asks for compact cards of roughly 800 code points each and at most three occupants per blueprint

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

### Requirement: The hand-written template pool provides offline quest generation
`world/ai/director_templates.py` SHALL define a non-empty tuple of hand-written, pre-validated
`QuestBlueprint` values that reference only permanent world content (known monster tiers, anchors,
grid coordinates, and known items). Every template SHALL satisfy the output schema and every
semantic validator and SHALL be indexed so a request context can be matched against it (rank, quest
type, issuer branch, anchor).

#### Scenario: The pool is non-empty and every template validates
- **WHEN** the template pool is inspected and each template is run through the schema and semantic
  validators
- **THEN** the pool is non-empty and every template passes with no errors

#### Scenario: Every template compiles to a registerable completable definition
- **WHEN** each template is passed to the deterministic compile boundary
- **THEN** the resulting `QuestDefinition` passes `validate_definition`, registers, and its stages
  are resolvable through permanent world content

#### Scenario: The degraded draw is deterministic and context-fitting
- **WHEN** two calls with identical contexts both degrade to the template pool
- **THEN** both resolve to the same template blueprint and that template fits the request context

#### Scenario: Offline end-to-end playability through the template pool
- **WHEN** every `LLM_PROFILES` entry is disabled and the full loop runs — `generate_quest_blueprint`
  degrades to a template, the deterministic boundary compiles it, the definition and offer register
  as one operation, the player accepts the quest, fights the declared permanent-content target, and
  turns it in
- **THEN** the loop completes with no LLM call and no generative module ever mutating state

#### Scenario: Templates compile through the deterministic boundary
- **WHEN** a template is compiled for play
- **THEN** it compiles through the deterministic boundary to a `QuestDefinition` that registers and can be completed by the deterministic loop without any LLM or SceneBuilder

#### Scenario: The degraded draw is deterministic
- **WHEN** the template pool is consulted on a degrade
- **THEN** the draw is deterministic: identical request contexts always select the same template from the pool

#### Scenario: The pool is read lazily to avoid import cycles
- **WHEN** the director module needs the pool
- **THEN** the template pool imports the proposal model one-way and is read through a lazy accessor, so no module-level import cycle forms with the director module

### Requirement: The canonical payload contract is versioned and shared by both boundaries
The `QuestBlueprint.to_payload()` JSON-safe mapping SHALL be the canonical proposal contract. Its
per-stage mapping rules SHALL be pinned — the objective-kind, layer, DEFEAT/ACQUIRE, quantity,
deadline, and failure-clause rules below — and the `scenario_director` output schema and the
compiler SHALL both derive from this one pinned contract, so the guardrail and the compiler cannot
drift.

#### Scenario: The guardrail schema and the compiler accept the same payload
- **WHEN** a payload passes the `scenario_director` output schema and semantic validators
- **THEN** the same payload compiles through `compile_quest_blueprint` without a contract-shaped
  rejection

#### Scenario: Every stage kind has one deterministic mapping
- **WHEN** each objective kind, layer, and DEFEAT/ACQUIRE variant in the contract is compiled
- **THEN** the resulting `QuestDefinition` carries exactly the corresponding `ObjectiveKind`,
  `DestinationKind`, `requires_bound_targets`, `item_key`, and quantity

#### Scenario: Wilderness destinations cannot be declared
- **WHEN** a payload declares `location_req.layer: "wilderness"`
- **THEN** both the semantic validator and the compiler reject it, and no destination can represent
  it

#### Scenario: Non-empty failure conditions are rejected, not ignored
- **WHEN** a payload declares a non-empty `failure.conditions` list
- **THEN** the compiler rejects it with a named error rather than silently dropping the conditions

#### Scenario: Objective kinds map onto the runtime enum
- **WHEN** an objective `kind` is mapped
- **THEN** `reach_location`→REACH, `defeat`→DEFEAT, `escort`→ESCORT, `acquire`→ACQUIRE

#### Scenario: Layers map onto destination kinds
- **WHEN** `location_req.layer` is mapped
- **THEN** `anchor`→ANCHOR with a placed anchor key, `grid`→GRID with coordinates, `instance`→BOUND_INSTANCE, and `wilderness` is not representable

#### Scenario: DEFEAT declares exactly one target source
- **WHEN** a DEFEAT stage is contracted
- **THEN** it declares exactly one of a known `monster_tier` or `npc_reqs` (which becomes `requires_bound_targets=True`)

#### Scenario: ACQUIRE, quantity, and deadline obey their shapes
- **WHEN** a stage declares an ACQUIRE objective, a quantity, or a deadline
- **THEN** an ACQUIRE stage declares a known `item_key`, a `quantity` is a positive integer, and a `deadline` maps to `QuestDefinition.deadline_hours`

#### Scenario: Failure conditions accept only the empty list
- **WHEN** `failure.conditions` is contracted
- **THEN** it is accepted only as an empty list

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward`, an issuer key, and a settlement mode. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation.

#### Scenario: A valid blueprint compiles to a registrable definition
- **WHEN** a validated blueprint passes through `compile_quest_blueprint`
- **THEN** the compiled `QuestDefinition` passes `validate_definition`, its reward is the
  blueprint's declared reward, and its issuer key and settlement mode are deterministically derived
  from the blueprint's declared issuer (a namespaced key; counter settlement for a guild branch,
  automatic settlement for a character carrier)

#### Scenario: An invalid proposal fails compile before any change
- **WHEN** a payload declares reward copper outside its rank's band or an unknown item key
- **THEN** `compile_quest_blueprint` raises `QuestCompileError` and neither the definition registry,
  the offer registry, nor the issuance registry changes

#### Scenario: Generated quest registration is idempotent
- **WHEN** the same compiled quest (definition, issuance, and requirements all equal) is registered twice
- **THEN** one `QuestDefinition` entry, one issuance entry, and one spawn-requirement entry
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
- **WHEN** a compiled definition is new but a conflicting issuance already exists for its
  `(definition_key, issuer_key)` identity, or a conflicting spawn-requirement entry already
  exists for its definition key
- **THEN** neither the definition registry, the offer registry, the issuance registry, nor the
  spawn-requirement registry changes, and a named error is raised

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
  tiers, issuer, indices, deadline, scene-bound rules) is re-checked deterministically, so no
  proposal can reach the registry unchecked

#### Scenario: A private commission compiles and registers into the issuance registry
- **WHEN** a validated blueprint declaring a character-namespaced issuer with zero merit is compiled
  and registered
- **THEN** one `QuestDefinition` entry and one `QuestIssuance` entry exist, the guild offer registry
  is unchanged, and the registered issuance settles automatically under that issuer key

#### Scenario: A private commission carrying merit fails compile
- **WHEN** a blueprint declares a character-namespaced issuer with non-zero reward merit
- **THEN** `compile_quest_blueprint` raises `QuestCompileError` and no registry changes

#### Scenario: A private commission naming an unauthorized carrier fails compile
- **WHEN** a blueprint declares a character-namespaced issuer key naming no carrier authorized to
  issue
- **THEN** `compile_quest_blueprint` raises `QuestCompileError` and no registry changes

#### Scenario: Two commissioners of identical stages do not collide
- **WHEN** two blueprints declare identical runtime stages and scene requirements but different
  character-namespaced issuers
- **THEN** both compile to the same definition key and register as two distinct issuances under that
  one definition, neither overwriting the other

#### Scenario: Issuer keys follow the namespacing rules
- **WHEN** a compiled issuance key is derived
- **THEN** it is either guild-namespaced or character-namespaced; a character-namespaced issuance carries zero merit and names a carrier authorized to issue, and a violation of either raises before any mutation

#### Scenario: The boundary accepts both branch spellings
- **WHEN** a blueprint declares a registered branch as its bare branch key (the form the request context and guardrail declare today) or as the full `guild:<branch key>` form
- **THEN** the boundary accepts either, and the compiled issuance key is always namespaced

#### Scenario: The definition key digests runtime content plus scene requirements
- **WHEN** a `QuestDefinition.key` is generated
- **THEN** it is a stable content digest over the canonical runtime definition serialization plus the canonical serialization of the compiled per-stage spawn requirements, so two blueprints with identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`, or `npc_reqs`, or any carried characterization field — the required `display_name` and `title`, the optional paired `age`/`apparent_age`, or portrait `stable_key`) always yield different keys and equal content always yields an equal key

#### Scenario: Registration publishes definition, issuance, and requirements atomically
- **WHEN** `register_generated_quest(...)` runs
- **THEN** it registers the compiled `QuestDefinition`, its issuance, and its per-stage spawn requirements (readable through `scene_requirements_for(definition_key)`) as one all-or-nothing operation

#### Scenario: Issuance rides the sole writer of its namespace
- **WHEN** a generated issuance is written
- **THEN** a guild issuance is written as a `GuildQuestOffer` in the guild offer registry and a character issuance as a `QuestIssuance` in the quest issuance registry, so neither store gains a second writer

#### Scenario: The publication preflights and rolls back completely
- **WHEN** the all-or-nothing registration writes its three registries
- **THEN** it preflights all three registries' equal/conflict states before writing any of them, rolls back every write if any later write fails, and leaves no spawn-requirement entry behind on a rolled-back publication, so a generated definition is never left registered without its issuance or its requirements

#### Scenario: Keys without requirements read back empty
- **WHEN** `scene_requirements_for` is called for a key with no registered requirements (for example a hand-written catalog quest)
- **THEN** it returns an empty tuple

#### Scenario: AI dicts never enter the registry directly
- **WHEN** a raw AI-shaped dict is offered for registration
- **THEN** `register_quest_definition` still rejects it — the compile boundary is the sole sanctioned translator and AI dicts never enter `QUEST_DEFINITION_REGISTRY` directly

### Requirement: Scene-bound proposal stages are validated before publication
The `scenario_director` guardrail semantic validators and the deterministic compiler SHALL both
enforce the same scene-bound rules, so the two sides cannot drift, covering the occupant-layer,
escort-destination, bound-target-quantity, and `anchor_near` rules pinned by the scenarios below.
Every violation SHALL be reported as a validation error that triggers a retry on the generative path
and a named `QuestCompileError` on the deterministic path, before any publication.

#### Scenario: An occupant-bearing stage must be an instance scene
- **WHEN** a payload declares `npc_reqs` with `location_req.layer` set to `"anchor"` or `"grid"`
- **THEN** both the semantic validator and the compiler reject it, so no scene occupant is ever
  spawned into a permanent room

#### Scenario: An ESCORT stage must be a permanent destination
- **WHEN** a payload declares an ESCORT objective at `location_req.layer: "instance"` (or an ESCORT
  objective together with `npc_reqs`)
- **THEN** both the semantic validator and the compiler reject it, so the SceneBuilder never spawns
  an escort's protected entities into the destination room and never auto-completes the escort on
  entry

#### Scenario: A bound-target DEFEAT quantity is bounded by its targets
- **WHEN** a DEFEAT stage declares `npc_reqs` and an objective `quantity` greater than the number of
  `npc_req` entries
- **THEN** both the semantic validator and the compiler reject it, so the objective can always be
  completed by defeating the bound targets

#### Scenario: anchor_near must be a placed anchor
- **WHEN** a stage declares a non-`None` `anchor_near` that is absent from
  `ANCHOR_PLACEMENT_REGISTRY`
- **THEN** both the semantic validator and the compiler reject it before publication

#### Scenario: The guardrail and the compiler share the same rule set
- **WHEN** a payload passes the `scenario_director` output schema and semantic validators
- **THEN** the same payload compiles through `compile_quest_blueprint` without a scene-bound-shaped
  rejection, and an un-guardrail-validated payload with a scene-bound violation is rejected by the
  compiler deterministically

#### Scenario: Occupants require an instance layer
- **WHEN** a stage declares any `npc_req` entry
- **THEN** its `location_req.layer` must be exactly `"instance"` — occupant-bearing scenes must be reclaimable instances, never permanent rooms, so permanent maps are never polluted by spawned scene NPCs and scene occupants always have a reclaim lifecycle

#### Scenario: Escorts require permanent destinations and no occupants
- **WHEN** an ESCORT stage is validated
- **THEN** it must use a permanent (`anchor`/`grid`) destination, never `"instance"` and never `npc_reqs` — the SceneBuilder locates permanent rooms only, so it never spawns an escort's protected entities into a destination room (which would auto-complete the escort on entry) and never pollutes a permanent map

#### Scenario: Bound-target quantities stay satisfiable
- **WHEN** a DEFEAT stage declares `npc_reqs`
- **THEN** it carries an objective `quantity` no greater than the number of `npc_req` entries, so a bound-target objective is always satisfiable (progress counts distinct bound defeats)

#### Scenario: A declared anchor_near must be a placed anchor
- **WHEN** a stage declares a non-`None` `location_req.anchor_near`
- **THEN** it must name a key present in `ANCHOR_PLACEMENT_REGISTRY`

### Requirement: Hook registration is atomic, idempotent, and boot-tolerant
`register_scenario_director()` SHALL install the output schema, every semantic validator, and the
sentinel degrade fallback in one operation, and SHALL remove every own hook (by identity) on a
partial failure so the layer is never left half-registered. A second call SHALL be a no-op that keeps
the first registration and swallows only this module's own duplicate-registration errors.

#### Scenario: Duplicate registration keeps the first registration
- **WHEN** `register_scenario_director()` is called twice
- **THEN** the second call is a no-op and the layer remains registered with the first schema,
  validators, and fallback

#### Scenario: Partial hook failure leaves no hooks installed
- **WHEN** a validator registration is fault-injected to raise after an earlier hook succeeded
- **THEN** every scenario_director hook belonging to this module is removed and the error propagates

#### Scenario: A foreign leftover registration does not abort server startup
- **WHEN** `at_server_start()` runs while an incompatible `scenario_director` registration already
  exists
- **THEN** the wrapper logs a warning, server startup continues, and the reply gate still fails
  loudly on use

#### Scenario: Production wires the registration into server startup
- **WHEN** the server boots in production
- **THEN** it calls `register_scenario_director()` from `server/conf/at_server_startstop.py`'s `at_server_start()` hook inside a boot-tolerant wrapper that logs and skips on a foreign leftover registration without aborting server startup

### Requirement: The scenario-director layer preserves the single-writer and transport boundaries
`world/ai/scenario_director.py` SHALL import no state writer, no typeclass, and no live transport,
and SHALL consume the client through the injected protocol exactly like `narrator.py` and
`npc_dialogue.py`, so the repository-wide transport-boundary contract stays green with no edits.
`world/quests/compile.py` SHALL contain no `world.ai`/`ollama`/`llm_client` fragment, keeping the
deterministic-path ban green.

#### Scenario: The scenario-director module stays inside the transport boundary
- **WHEN** the repository-wide transport-boundary contract scans `world/ai/scenario_director.py`
- **THEN** it finds no import of a state writer, no live transport symbol, and no socket import, and
  the module is not `client.py`

#### Scenario: The compile module stays inside the deterministic-path ban
- **WHEN** the deterministic-path ban scan checks `world/quests/compile.py`
- **THEN** the source contains no `world.ai`, `ollama`, or `llm_client` fragment

#### Scenario: All scenario-director tests run offline
- **WHEN** the scenario-director test suite runs with no LLM service available
- **THEN** every test passes using recorded fixtures and none opens a network connection

#### Scenario: Tests use fakes or fixtures per design §10
- **WHEN** any test of this change exercises the layer
- **THEN** it uses `FakeLLMClient` or an equivalent recorded fixture and never contacts a live endpoint, per design §10

### Requirement: The scenario-director name inspiration reads the namegen rule layer without crossing the single-writer boundary
`world/ai/scenario_director.py` SHALL consume `world.rules.namegen` strictly as a pure read: no
`world/ai/` module SHALL write state through it, and the repository-wide state-writer ban SHALL
carry `world.rules.namegen` on its documented read-only-rule allowlist alongside
`world.quests.characterization`, so the transport-boundary contract test keeps failing any other
`world.rules` import from `world/ai/`.

#### Scenario: The read-only rule allowlist names exactly the pure rule modules
- **WHEN** the AI transport-boundary contract test resolves its read-only allowlist
- **THEN** `world.rules.namegen` and `world.quests.characterization` are the only exemptions under
  the state-writer prefixes, each documented as side-effect-free, and an `world/ai/` module that
  imports any other `world.rules` module still fails the scan

#### Scenario: Prompt construction leaves no generative state behind
- **WHEN** `build_scenario_prompt()` runs to completion with the inspiration bank
- **THEN** no database write, attribute write, or registry mutation occurred, and the rolled names
  exist only inside the returned message strings

### Requirement: Beat-scoped blueprint generation does not substitute template filler

A beat-scoped ScenarioDirector entry point SHALL accept a validated quest beat and permitted immutable narrative context, use the existing client/profile/guardrail/schema and semantic validators, and return a context-fitting QuestBlueprint proposal or a no-content outcome. Disabled transport, exhausted validation and context misfit SHALL NOT substitute a generic template. The existing generate_quest_blueprint entry point SHALL retain its generic authored-template degradation contract.

#### Scenario: Beat misfit does not draw template
- **WHEN** a schema-valid beat blueprint fails its narrative/rank/issuer/anchor fitness gate
- **THEN** the beat entry point yields no content and no template draw

#### Scenario: Generic degradation still works
- **WHEN** the generic non-beat entry point runs with disabled generation
- **THEN** it draws a compatible authored template as before
