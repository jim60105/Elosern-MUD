## Purpose

Defines the scenario-director layer that generates validated quest blueprints through the guarded generative pipeline. The layer is deterministic-first: prompt construction is stable and bounded, semantic validators bound every world reference, every failure path degrades to the hand-written template pool, and the canonical payload contract is shared with the deterministic compile boundary so the guardrail and the compiler cannot drift.

## Requirements

### Requirement: Scene-archetype and NPC-tier registries are immutable lore data
`world/lore/scene_archetypes.py` SHALL define a frozen `SceneArchetype` dataclass and a module-level
`SCENE_ARCHETYPE_REGISTRY: dict[str, SceneArchetype]` keyed by scene-kind keys (for example
`forest_path`, `tavern_interior`, `dungeon_interior`, `city_street`, `wilderness_path`,
`mountain_path`, `ruin_interior`, `coastal_path`, `cave_interior`, `shrine_interior`).
`world/lore/npc_tiers.py` SHALL define a frozen `NPCTier` dataclass and a module-level
`NPC_TIER_REGISTRY: dict[str, NPCTier]` keyed by role-tier keys (for example `civilian`, `guard`,
`merchant`, `adventurer`, `mage`, `noble`, `bandit`, `priest`, `knight`). Each `NPCTier` SHALL also
carry `race_key` and `static_tier_key`, naming immutable entries of `RACE_REGISTRY` and
`STATIC_TIER_REGISTRY`, so a role tier's deterministic physical stats resolve from the lore tables and
change 21's SceneBuilder never duplicates balance constants. Both registries SHALL be non-empty,
frozen, and consumable by any package without violating the single-writer or deterministic-path
boundaries; `world/ai/` validators, change 21's SceneBuilder, and the `world/quests` compiler SHALL
read these registry values rather than duplicating constants.

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

### Requirement: QuestBlueprint is the closed, deeply immutable AI proposal type
`world/ai/scenario_director.py` SHALL define frozen `QuestBlueprint` dataclasses whose `quest_type`
SHALL be restricted to exactly the five `QuestType` values (採集, 討伐, 護衛, 探索, 緊急) and whose
stages SHALL carry explicit integer `index` values in a contiguous sequence starting at zero. No
blueprint field SHALL contain a mutable dict or list, and construction SHALL reject any mutable
container so immutability is enforced by the constructor, not only by the dataclass. `QuestBlueprint`
SHALL be a distinct proposal type from the runtime `QuestDefinition`; raw mappings SHALL NOT be
accepted by the runtime quest registry, and the two types SHALL NOT be interchangeable.

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
inspiration only — directly usable, adjustable to the character's declared sex and background, and
`display_name` is recommended but optional. The output-schema optionality of `display_name` and
every semantic validator SHALL be unchanged by the injection.

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
- **THEN** the bank is presented with the library text marking the names as 僅供靈感 (adjustable to
  sex and background) and recommending — not requiring — that `npc_req` entries fill `display_name`

#### Scenario: The output contract stays unchanged by the injection
- **WHEN** a blueprint omits `display_name` on every `npc_req` entry, and another blueprint fills
  it with a name not present in the inspiration bank
- **THEN** both validate exactly as before the injection: `display_name` remains optional, no
  validator rejects a bank-external name, and the registered output schema is byte-identical to
  the pre-change schema

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

### Requirement: generate_quest_blueprint runs the guarded pipeline and enforces the request context
`world/ai/scenario_director.py::generate_quest_blueprint(client, *, context)` SHALL require the
client as an injected argument and SHALL reject an explicit `None` with a named
`ScenarioDirectorClientRequiredError` as its first statement, before any prompt construction or
transport work. It SHALL build a `ChatRequestDescriptor` whose messages come from
`build_scenario_prompt(context)` and whose `schema_id` is `"scenario_director"`, yield the
`scenario_director` layer's `guarded_call`, `json.loads` the accepted text into a frozen
`QuestBlueprint`, and apply a post-guardrail fitness gate that re-checks the parsed blueprint against
the request context (allowed rank, requested quest type, issuer branch, anchor). A blueprint that is
schema- and semantically valid but does not fit the context SHALL be treated as a degrade trigger.
On any degrade trigger (disabled profile, transport failure, exhausted retries, or context misfit)
the call SHALL resolve to a deterministic draw from the hand-written template pool that also fits the
context. When no compatible template exists, the call SHALL errback with a named
`ScenarioDirectorTemplateError`. When the layer is registered, the call SHALL never resolve to an
invalid proposal or to `None`; a call made before registration SHALL errback with a named
`ScenarioDirectorNotRegisteredError`.

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

### Requirement: Semantic validators bound rank, reward, archetype, NPC tier, and every world reference
The `scenario_director` layer SHALL register semantic validators under stable names so the shared
pipeline retries on violations and degrades on exhaustion. Validators SHALL reject: a `rank` outside
`GUILD_RANK_REGISTRY`; reward copper below the rank's `reward_min_copper` or above its
`reward_max_copper` (with S honoring its open upper bound); non-integer or negative merit; reward
item keys outside `ITEM_REGISTRY` with non-positive quantities or duplicate keys; a `location_req`
archetype outside `SCENE_ARCHETYPE_REGISTRY`; an `npc_req` tier outside `NPC_TIER_REGISTRY`; a DEFEAT
stage declaring a `monster_tier` outside `MONSTER_TIER_REGISTRY`; an issuer branch outside
`GUILD_BRANCH_REGISTRY`; non-contiguous stage indices; a `deadline_hours` that is neither `None` nor
a positive integer; empty or non-CJK `name`/`scene_sentence`; fields exceeding length caps; and
leaked template-placeholder syntax. Each rejected attempt SHALL append a concrete validation message
before retrying.

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

### Requirement: The hand-written template pool provides offline quest generation
`world/ai/director_templates.py` SHALL define a non-empty tuple of hand-written, pre-validated
`QuestBlueprint` values that reference only permanent world content (known monster tiers, anchors,
grid coordinates, and known items). Every template SHALL satisfy the output schema and every
semantic validator, SHALL be indexed so a request context can be matched against it (rank, quest
type, issuer branch, anchor), and SHALL compile through the deterministic boundary to a
`QuestDefinition` that registers and can be completed by the deterministic loop without any LLM or
SceneBuilder. The degraded draw SHALL be deterministic: identical request contexts always select the
same template from the pool. The template pool SHALL import the proposal model one-way and SHALL be
read through a lazy accessor so no module-level import cycle forms with the director module.

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

### Requirement: The canonical payload contract is versioned and shared by both boundaries
The `QuestBlueprint.to_payload()` JSON-safe mapping SHALL be the canonical proposal contract. Its
per-stage mapping rules SHALL be pinned: objective `kind` maps to `ObjectiveKind`
(`reach_location`→REACH, `defeat`→DEFEAT, `escort`→ESCORT, `acquire`→ACQUIRE); `location_req.layer`
maps to `DestinationKind` (`anchor`→ANCHOR with a placed anchor key, `grid`→GRID with coordinates,
`instance`→BOUND_INSTANCE, and `wilderness` is not representable); a DEFEAT stage SHALL declare
exactly one of a known `monster_tier` or `npc_reqs` (which becomes `requires_bound_targets=True`); an
ACQUIRE stage SHALL declare a known `item_key`; a `quantity` SHALL be a positive integer; a `deadline`
SHALL map to `QuestDefinition.deadline_hours`; and `failure.conditions` SHALL be accepted only as an
empty list. The `scenario_director` output schema and the compiler SHALL both derive from this one
pinned contract, so the guardrail and the compiler cannot drift.

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

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward` and an issuer branch key. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation. The generated `QuestDefinition.key`
SHALL be a stable content digest over the canonical runtime definition serialization **plus the
canonical serialization of the compiled per-stage spawn requirements**, so two blueprints with
identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`,
or `npc_reqs`, or any carried characterization field — `display_name`, paired `age`/`apparent_age`,
or portrait `stable_key`) always yield different keys and equal content always yields an equal key.
`register_generated_quest(...)` SHALL register the compiled `QuestDefinition`, its `GuildQuestOffer`,
**and its per-stage spawn requirements (readable through `scene_requirements_for(definition_key)`)**
as one all-or-nothing operation: it SHALL preflight all three registries' equal/conflict states
before writing any of them, SHALL roll back every write if any later write fails, and SHALL leave no
spawn-requirement entry behind on a rolled-back publication, so a generated definition is never left
registered without its offer or its requirements. `scene_requirements_for` SHALL return an empty
tuple for any key with no registered requirements (for example a hand-written catalog quest). Raw
AI-shaped dicts SHALL still be rejected by `register_quest_definition` — the compile boundary is the
sole sanctioned translator and AI dicts never enter `QUEST_DEFINITION_REGISTRY` directly.

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
- **WHEN** an accepted blueprint's `npc_req` entry declares `display_name`, paired ages, and a
  portrait `stable_key`
- **THEN** the compiled per-stage spawn requirements expose all three in deterministic order

#### Scenario: Characterization differences change the generated key
- **WHEN** two accepted blueprints differ only in a carried characterization field
- **THEN** their compiled `QuestDefinition.key` digests differ

#### Scenario: A field-less blueprint compiles unchanged
- **WHEN** an accepted blueprint declares no optional characterization fields
- **THEN** the compiled requirements, digest, and registration behave exactly as today

#### Scenario: Spawn requirements are registered with the publication
- **WHEN** a compiled quest is registered and `scene_requirements_for(definition_key)` is read
- **THEN** it returns the compiled stage's spawn requirements, so change 21's SceneBuilder can
  materialize the scene when the player arrives

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
  tiers, branch, indices, deadline, scene-bound rules) is re-checked deterministically, so no proposal
  can reach the registry unchecked

### Requirement: Scene-bound proposal stages are validated before publication
The `scenario_director` guardrail semantic validators and the deterministic compiler SHALL both
enforce the same scene-bound rules, so the two sides cannot drift. A stage SHALL NOT declare any
`npc_req` entry unless its `location_req.layer` is exactly `"instance"` — occupant-bearing scenes
must be reclaimable instances, never permanent rooms, so permanent maps are never polluted by spawned
scene NPCs and scene occupants always have a reclaim lifecycle. An ESCORT stage SHALL use a permanent
(`anchor`/`grid`) destination, never `"instance"` and never `npc_reqs` — the SceneBuilder locates
permanent rooms only, so it never spawns an escort's protected entities into a destination room
(which would auto-complete the escort on entry) and never pollutes a permanent map. A DEFEAT stage
that declares `npc_reqs` SHALL carry an objective `quantity` no greater than the number of `npc_req`
entries, so a bound-target objective is always satisfiable (progress counts distinct bound defeats).
A non-`None` `location_req.anchor_near` SHALL name a key present in `ANCHOR_PLACEMENT_REGISTRY`.
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

### Requirement: Hook registration is atomic, idempotent, and boot-tolerant
`register_scenario_director()` SHALL install the output schema, every semantic validator, and the
sentinel degrade fallback in one operation, and SHALL remove every own hook (by identity) on a
partial failure so the layer is never left half-registered. A second call SHALL be a no-op that keeps
the first registration and swallows only this module's own duplicate-registration errors. Production
SHALL call it from `server/conf/at_server_startstop.py`'s `at_server_start()` hook inside a
boot-tolerant wrapper that logs and skips on a foreign leftover registration without aborting server
startup.

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

### Requirement: The scenario-director layer preserves the single-writer and transport boundaries
`world/ai/scenario_director.py` SHALL import no state writer, no typeclass, and no live transport,
and SHALL consume the client through the injected protocol exactly like `narrator.py` and
`npc_dialogue.py`, so the repository-wide transport-boundary contract stays green with no edits.
`world/quests/compile.py` SHALL contain no `world.ai`/`ollama`/`llm_client` fragment, keeping the
deterministic-path ban green. Every test of this change SHALL use `FakeLLMClient` or an equivalent
recorded fixture and never contact a live endpoint, per design §10.

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
