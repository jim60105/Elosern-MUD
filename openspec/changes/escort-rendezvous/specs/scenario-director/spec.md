# Spec Delta

## MODIFIED Requirements

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
The deterministic compiler SHALL revalidate shared schema and immutable lore constraints before mutation, producing immutable runtime definitions, rewards, issuance declarations and scene requirements. Existing contiguous indices, supported kinds, quantity/deadline, item/tier/archetype, characterization, age, rank reward band, zero private merit, empty unsupported failure clause and bound-target quantity rules SHALL remain. Escort publication SHALL admit the complete proved protected-role/destination-or-rendezvous flow and refuse incomplete contracts. Symbolic issuer roles SHALL remain unresolved/unregistered until activation authorizes the exact bound issuer; explicit runtime issuer keys SHALL require an authorized carrier. Permanent occupants SHALL retain validated package ownership/retention. Whole-package validation SHALL retain unambiguous locators, exact role/scene references, reciprocal relations, provenance-bearing knowledge, reachable dialogue, scoped authority and registered effects. Registration SHALL remain atomic, conflict-rejecting and idempotent, using stable runtime/scene characterization digests extended with the new completion/group fields. Separate issuer identities SHALL coexist and raw proposal mappings SHALL never enter runtime registries.

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

### Requirement: Scene-bound proposal stages are validated before publication
Semantic validators and deterministic compilation SHALL enforce the same validated package ownership/retention, bound-target quantity, registry locator/anchor and escort-binding rules. ESCORT SHALL permit exactly the implemented destination or rendezvous contract with complete protected roles and validated meeting/relation references. Ordinary stage occupants SHALL retain instance ownership unless explicitly package-owned under the upstream permanent-role contract. Escort participants SHALL resolve existing published roles without destination auto-spawn or invented nearby actors. Invalid declarations SHALL return generative validation errors and deterministic `QuestCompileError` before publication. Unsupported templates and arbitrary failure-condition expressions SHALL remain rejected.

#### Scenario: Closed escort validation agrees across boundaries
- **WHEN** complete destination and rendezvous packages and malformed mixed/role-less alternatives are submitted to semantic validation and compilation
- **THEN** complete supported packages agree on acceptance and malformed alternatives agree on side-effect-free rejection

#### Scenario: Unsupported templates never invent a protected actor
- **WHEN** an ordinary offline escort template lacks published protected-role and completion declarations
- **THEN** it stays unavailable and no nearby NPC is chosen or spawned to make it pass

#### Scenario: Existing scene-bound constraints remain enforced
- **WHEN** ordinary occupants lack instance/package ownership, a bound DEFEAT exceeds its target count, or `anchor_near` is unknown
- **THEN** both validators reject before writes

#### Scenario: An occupant-bearing stage must be an instance scene
- **WHEN** ordinary occupant-bearing stage data lacks instance ownership or a validated upstream permanent package ownership/retention contract
- **THEN** semantic validation and compilation refuse before any state change

#### Scenario: An ESCORT stage must be a permanent destination
- **WHEN** an escort declares any locator or roles without the complete protected-role and closed completion contract
- **THEN** both validation paths reject; complete destination supports existing anchor/XYZ/bound-instance locators and complete rendezvous needs no fixed destination

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
- **WHEN** ordinary disposable stage occupants are declared outside an instance without validated package ownership and retention
- **THEN** publication refuses; upstream validated permanent-role ownership remains supported

#### Scenario: Escorts require permanent destinations and no occupants
- **WHEN** a proposal tries to satisfy escort by inventing destination occupants instead of binding published protected roles
- **THEN** both validators reject; supported exact protected bindings and destination/rendezvous fields are required

#### Scenario: Bound-target quantities stay satisfiable
- **WHEN** a DEFEAT stage declares `npc_reqs`
- **THEN** it carries an objective `quantity` no greater than the number of `npc_req` entries, so a bound-target objective is always satisfiable (progress counts distinct bound defeats)

#### Scenario: A declared anchor_near must be a placed anchor
- **WHEN** a stage declares a non-`None` `location_req.anchor_near`
- **THEN** it must name a key present in `ANCHOR_PLACEMENT_REGISTRY`

## ADDED Requirements

### Requirement: Canonical generated escort payloads preserve all executable references
The shared schema/proposal/payload/compiler/restore contract SHALL preserve exact package, commission, protected/meeting roles, typed relations, closed completion and explicit final-result groups. Distinct alternatives SHALL retain separate definition/issuance/reward references. New fields SHALL enter content identity and independently revalidate at compilation and registration.

#### Scenario: Complete escort references round-trip
- **WHEN** a synthetic related-role package with distinct commissions is compiled, published and restored
- **THEN** every completion/relation/group reference and reward survives unchanged, different predicate content has different identity, and no accepted record is fabricated

#### Scenario: Direct compiler or registration bypass refuses
- **WHEN** schema validation is skipped or a compiled escort is manually constructed without complete binding metadata
- **THEN** deterministic compilation or generated registration raises `QuestCompileError` before registry/durable publication

#### Scenario: Existing unsafe mechanical fields stay rejected
- **WHEN** a proposal injects typeclass paths, out-of-range ages, unknown registry keys, nonempty unsupported failure clauses, unauthorized runtime issuers or private merit
- **THEN** existing semantic/compiler rejection remains with no state mutation

#### Scenario: Complete canonical generated escort payloads preserve all executable references contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** The shared versioned blueprint schema, immutable proposal type, canonical payload, compiler and durable restore SHALL carry exact package/commission/protected/meeting role references, closed completion fields, typed relations and explicit exclusive final-result group membership. Quantity one, contiguous stages, registry-derived mechanics/rewards, age bounds, namespaced issuer authority, zero private merit and empty unsupported failure conditions SHALL remain enforced. Symbolic issuer roles SHALL remain planning declarations until authorized actor activation. Distinct alternatives SHALL retain separate definition/issuance/reward references. The content digest SHALL include all new runtime-critical fields; equal content SHALL remain idempotent and conflicting registration SHALL remain atomic. `compile_quest_blueprint` and generated registration SHALL independently reject incomplete or forged executable escort contracts before writes.
