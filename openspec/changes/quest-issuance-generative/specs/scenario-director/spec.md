# Delta spec: scenario-director (quest-issuance-generative)

## MODIFIED Requirements

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward`, an issuer key, and a settlement mode. The issuer key SHALL be
either guild-namespaced or character-namespaced; a character-namespaced issuance SHALL carry zero
merit and SHALL name a carrier authorized to issue, and a violation of either SHALL raise before any
mutation. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation. The generated `QuestDefinition.key`
SHALL be a stable content digest over the canonical runtime definition serialization **plus the
canonical serialization of the compiled per-stage spawn requirements**, so two blueprints with
identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`,
or `npc_reqs`, or any carried characterization field — the required `display_name` and `title`, the
optional paired `age`/`apparent_age`, or portrait `stable_key`) always yield different keys and equal
content always yields an equal key. `register_generated_quest(...)` SHALL register the compiled
`QuestDefinition`, its issuance, **and its per-stage spawn requirements (readable through
`scene_requirements_for(definition_key)`)** as one all-or-nothing operation. The issuance SHALL be
written through the sole writer of its own namespace — a guild issuance as a `GuildQuestOffer` in the
guild offer registry, a character issuance as a `QuestIssuance` in the quest issuance registry — so
neither store gains a second writer. The operation SHALL: it SHALL preflight all
three registries' equal/conflict states before writing any of them, SHALL roll back every write if
any later write fails, and SHALL leave no spawn-requirement entry behind on a rolled-back
publication, so a generated definition is never left registered without its issuance or its
requirements. `scene_requirements_for` SHALL return an empty tuple for any key with no registered
requirements (for example a hand-written catalog quest). Raw AI-shaped dicts SHALL still be rejected
by `register_quest_definition` — the compile boundary is the sole sanctioned translator and AI dicts
never enter `QUEST_DEFINITION_REGISTRY` directly.

#### Scenario: A valid blueprint compiles to a registrable definition
- **WHEN** a validated blueprint passes through `compile_quest_blueprint`
- **THEN** the compiled `QuestDefinition` passes `validate_definition` and its reward, issuer key,
  and settlement mode are the blueprint's declared values

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
  is unchanged, and the settlement mode is the blueprint's declared value

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
