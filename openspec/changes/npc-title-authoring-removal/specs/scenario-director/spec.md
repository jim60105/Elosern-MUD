# Spec Delta

## MODIFIED Requirements

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
  `display_name`

#### Scenario: The injection changes no output-schema field
- **WHEN** a blueprint uses a bank name verbatim as `display_name`, adapts a bank name, or declares
  a name absent from the bank
- **THEN** the validator's decision depends only on the shared identity rules — a bank-external name
  is accepted, an omitted display_name is rejected and a supplied title field is rejected — and the injection adds no schema
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
- **WHEN** the prompt states that every `npc_req` entry MUST carry the required identity fields `display_name`
- **THEN** the injection itself adds no output-schema field, and the requiredness of `display_name` is enforced by the shared characterization validator, not by the prompt

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written

### Requirement: Blueprint validation accepts and bounds the optional npc characterization fields
The scenario director's blueprint validator SHALL require two per-occupant characterization
fields (`display_name` and `persona`) on every `npc_req` entry, in addition to the
existing role/tier/disposition checks, and SHALL accept the two optional fields `age`/`apparent_age`
(paired) and `portrait: {stable_key}`, with every field validated through the shared bound helper
under `world/quests/` — the single rule source.

#### Scenario: A valid named occupant with a title and ages passes validation
- **WHEN** a current characterization input carries the removed title field
- **THEN** it is rejected by the closed schema before compile or template registration, while the title-free form retains all name/age/portrait/persona checks

#### Scenario: A missing identity field is rejected and retried
- **WHEN** an `npc_req` entry omits display_name
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
  card contract, and no inline duplicate of the age/name/key/card rules exists in the
  scenario director

#### Scenario: The required fields carry their shared shapes
- **WHEN** the required characterization fields are validated
- **THEN** `display_name` is authored name as bounded non-empty text through the shared bound helper with its shared character-set rules; the removed title field is rejected

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
- **WHEN** a payload's tier is unknown, its occupant is missing display_name or persona, its card violates the contract, its ages are unpaired, non-integer, negative, or beyond the race lifespan, or its portrait key is malformed
- **THEN** it is rejected and retried within the budget exactly like today's other semantic failures, and on budget exhaustion the call degrades to the offline template pool

#### Scenario: The occupant total is capped at three
- **WHEN** a blueprint declares `npc_req` occupants across its stages
- **THEN** it declares at most three in total across all of its stages, so its occupant cards fit one bounded model response, and a blueprint exceeding that total is rejected and retried like any other semantic failure

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
The compiler SHALL revalidate shared schema and immutable lore constraints before mutation, producing immutable runtime definitions, rewards, issuance declarations and scene requirements. Escort publication SHALL admit the complete proved protected-role/destination-or-rendezvous flow and refuse incomplete contracts. Symbolic issuer roles SHALL remain unresolved/unregistered until activation authorizes the exact bound issuer; explicit runtime issuer keys SHALL require an authorized carrier.

#### Scenario: Existing compiler and issuer behavior remains strict
- **WHEN** equal ordinary content, distinct authorized issuers, unauthorized runtime keys and conflicting registrations are exercised
- **THEN** equal content is idempotent, authorized issuances coexist, unauthorized keys refuse, and conflict leaves no partial durable or registry state

#### Scenario: Symbolic planning still grants no runtime authority
- **WHEN** a complete escort package names an unmaterialized symbolic issuer role
- **THEN** publication creates no actor, accepted quest or runtime commission until authorized encounter activation

#### Scenario: Escort predicate differences affect content identity
- **WHEN** payloads differ only in protected/meeting roles, completion mode, relation or group final-result references
- **THEN** their runtime-critical content is included in stable identity and cannot overwrite another definition silently

#### Scenario: Symbolic issuer planning creates no commission
- **WHEN** a package declares a validated role-issued commission whose actor is unmaterialized
- **THEN** the package can be published without accepting or registering a quest, creating an actor, or treating the role ID as an authorized issuer key

#### Scenario: Existing unauthorized issuer is still rejected
- **WHEN** a proposal explicitly names an ordinary NPC as runtime issuer without issuing authority
- **THEN** compilation rejects it without package or registry changes

#### Scenario: Whole package validation rejects invalid references
- **WHEN** a package names an ambiguous or unknown place, inconsistent relationship, absent role, missing phase, unsupported effect, or injected mechanical data
- **THEN** publication fails with the named offending reference and no nearest-place substitution or partial writes

#### Scenario: Existing compiler behavior remains deterministic
- **WHEN** equal ordinary blueprints are compiled and registered twice, or equal stages are issued by two authorized carriers
- **THEN** equal content has equal keys and one requirements entry, repeat registration is a no-op, and each carrier retains its separate issuance

#### Scenario: Conflict rolls back registration
- **WHEN** publication encounters conflicting definition, requirements, or issuance content
- **THEN** no partial registry or durable payload change remains

#### Scenario: Unsupported mechanics remain rejected
- **WHEN** a proposal declares an unsupported destination, invalid quantity/reward/tier, nonempty unsupported failure conditions, or an ESCORT stage without its protected-role production flow
- **THEN** it fails before writes despite having valid scene dialogue

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
- **WHEN** an accepted blueprint's `npc_req` entry declares the required `display_name`
  plus paired ages and a portrait `stable_key`
- **THEN** the compiled per-stage spawn requirements expose all four in deterministic order

#### Scenario: Characterization differences change the generated key
- **WHEN** two accepted blueprints differ only in a carried characterization field
- **THEN** their compiled `QuestDefinition.key` digests differ

#### Scenario: An option-field-less blueprint compiles with the identity-bearing digest
- **WHEN** an accepted blueprint declares no optional characterization fields (no ages, no portrait)
- **THEN** it compiles with the same deterministic registration behavior, and its digest includes
  the required `display_name` of every occupant

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
- **THEN** it is a stable content digest over the canonical runtime definition serialization plus the canonical serialization of the compiled per-stage spawn requirements, so two blueprints with identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`, or `npc_reqs`, or any carried characterization field; the required `display_name`, the optional paired `age`/`apparent_age`, or portrait `stable_key`) always yield different keys and equal content always yields an equal key

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
- **THEN** `register_quest_definition` still rejects it; the compile boundary is the sole sanctioned translator and AI dicts never enter `QUEST_DEFINITION_REGISTRY` directly

#### Scenario: The retained rule set and registration behavior
- **WHEN** an ordinary proposal, a whole package or a conflicting registration is compiled
- **THEN** The existing rule set SHALL remain: contiguous indices, supported kinds, quantity/deadline, item/tier/archetype, characterization, age, rank reward band, zero private merit, empty unsupported failure clause and bound-target quantity rules.
- **THEN** Permanent occupants SHALL retain validated package ownership/retention. Whole-package validation SHALL retain unambiguous locators, exact role/scene references, reciprocal relations, provenance-bearing knowledge, reachable dialogue, scoped authority and registered effects.
- **THEN** Registration SHALL remain atomic, conflict-rejecting and idempotent, using stable runtime/scene characterization digests extended with the new completion/group fields. Separate issuer identities SHALL coexist and raw proposal mappings SHALL never enter runtime registries.

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written
