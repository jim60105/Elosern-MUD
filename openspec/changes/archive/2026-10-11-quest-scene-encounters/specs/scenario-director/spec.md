# Spec Delta

## MODIFIED Requirements

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type

The deterministic compile boundary SHALL revalidate proposals against shared schema and immutable lore constraints before mutation and produce immutable runtime definitions, rewards, issuance declarations, and scene requirements. Contiguous stage indices, supported objective/destination kinds, quantity/deadline rules, item/tier/archetype references, bounded complete characterization, rank reward bands, zero private merit, empty unsupported failure conditions, and satisfiable bound-target DEFEAT quantities SHALL remain enforced. ESCORT publication SHALL remain refused until its production protected-role flow lands. Package planning MAY declare a validated symbolic issuer role without an existing actor; such a declaration SHALL remain unresolved and unregistered until activation provisions and authorizes the exact bound issuer. Explicit runtime issuer keys SHALL still require an authorized carrier. Permanent occupants SHALL require validated package ownership and retention contracts. Publication SHALL validate the entire package, including unambiguous locators, role/scene references, reciprocal relationships, provenance-bearing initial knowledge, reachable dialogue coverage, issuer scope, and registered effects. Invalid proposals SHALL raise named errors before writes. Registration SHALL remain strict, atomic, conflict-rejecting, and idempotent; stable digests SHALL include runtime and scene characterization content, equal content SHALL yield equal keys, distinct issuer identities SHALL coexist, and raw proposal mappings SHALL remain invalid runtime registry inputs.

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
- **THEN** it is a stable content digest over the canonical runtime definition serialization plus the canonical serialization of the compiled per-stage spawn requirements, so two blueprints with identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`, or `npc_reqs`, or any carried characterization field; the required `display_name` and `title`, the optional paired `age`/`apparent_age`, or portrait `stable_key`) always yield different keys and equal content always yields an equal key

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

## ADDED Requirements

### Requirement: Scene package proposals share the canonical bounded contract

Generated package schemas and deterministic compilation SHALL derive from the same canonical bounded payload contract for reusable roles, encounters, phase dialogue, quest requirements, and symbolic issuer declarations. Proposal generation SHALL remain data-only and SHALL NOT mutate persistent state, lore registries, or supply executable conditions, typeclass paths, or mechanical magnitudes. Immutable published payloads SHALL round-trip through durable storage without persona or reference drift.

#### Scenario: Canonical package round-trip preserves references
- **WHEN** a schema-valid synthetic package is compiled, published, and reloaded
- **THEN** its normalized role references, dialogue definitions, quest requirements and source identity remain unchanged and independently revalidate
