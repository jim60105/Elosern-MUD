## MODIFIED Requirements

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

### Requirement: The deterministic compile boundary translates validated proposals into the runtime type
`world/quests/compile.py` SHALL provide `compile_quest_blueprint(validated_payload) -> CompiledQuest`
that re-validates the proposal against the lore registries and maps it onto the closed immutable
runtime type: a `QuestDefinition` (with `QuestType`, contiguous stages, objective kinds, destinations,
and deadline) plus a `QuestReward` and an issuer branch key. It SHALL raise a named
`QuestCompileError` on any invalid payload before any mutation. The generated `QuestDefinition.key`
SHALL be a stable content digest over the canonical runtime definition serialization **plus the
canonical serialization of the compiled per-stage spawn requirements**, so two blueprints with
identical runtime stages but different scene requirements (archetype, `anchor_near`, `scene_sentence`,
or `npc_reqs`) always yield different keys and equal content always yields an equal key.
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

## ADDED Requirements

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
