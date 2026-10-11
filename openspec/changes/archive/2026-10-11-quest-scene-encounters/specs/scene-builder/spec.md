# Spec Delta

## MODIFIED Requirements

### Requirement: SceneBuilder is the deterministic requirements-to-spawn materialization layer

The scene materializer SHALL consume validated stage and published package requirements as plain data without importing generative modules or live transport. It SHALL share existing whitelisted prototype, characterization, trait, portrait, and binding construction. Room lifecycle SHALL remain maps-owned, quest role and stage bindings quest-owned, component initialization rules-owned, and knowledge/events narrative-owned. Conversable generated roles SHALL use the whitelisted generative-NPC path with scripted dialogue capability; unrelated monsters and non-conversable prototypes SHALL remain unchanged.

#### Scenario: Generated conversational role uses shared construction
- **WHEN** an encounter materializes a validated named conversable role
- **THEN** its registry-derived traits, validated persona and ages, portrait identity, scripted topics, and free-form seam are initialized through the shared deterministic path without a model call

#### Scenario: Construction rejects mechanical injection
- **WHEN** a role supplies a numeric trait/reward magnitude, an arbitrary typeclass path, or an age outside 0..10000 or applicable race bounds
- **THEN** validation rejects it before spawning and leaves lore registries unchanged

#### Scenario: The module stays inside the deterministic-path ban
- **WHEN** the repository-wide deterministic-path contract scans `world/quests/`
- **THEN** `scene_builder.py` carries no `world.ai`, `ollama`, or `llm_client` fragment, and no
  contract test requires an edit

#### Scenario: Every state change flows through the deterministic core
- **WHEN** `scene_builder.py` is inspected against the state-writer surface
- **THEN** it spawns and binds only through the named deterministic APIs and never calls a
  generative-layer module to write state

#### Scenario: Each lifecycle API serves its named role
- **WHEN** the materializer's state writes are inspected
- **THEN** instance rooms are created through `world.maps.instance.spawn_instance_room`, occupants through Evennia prototype spawning, occupant ownership through `world.maps.instance.register_owned_entity`, and stage binding through `world.quests.binding.bind_stage_runtime`

#### Scenario: Commands can drive the builder without the generative package
- **WHEN** a module under `commands/` imports and calls the SceneBuilder
- **THEN** the call succeeds without referencing the generative package

### Requirement: Materializing a stage spawns the destination, sets scene metadata, and binds one stage atomically and idempotently

Accepted-stage materialization SHALL resolve the actor's current in-progress stage and reject unknown, inactive, terminal, requirement-less, or wrong-origin requests with named side-effect-free errors. Instance destinations SHALL create one whitelisted room and plain exit pair with scene metadata, materialize occupants, register disposable ownership, and bind objective targets atomically. Permanent anchor/grid destinations SHALL reuse their validated existing room and permit only validated package-owned occupants and exact role bindings without rewriting shared descriptions or creating rooms/exits. Stages without such occupants SHALL remain locate-only. Repeated bindings SHALL be validated and reused without resetting actor location or state. Failures SHALL roll back objects, ownership and binding writes and restore affected caches; player movement and portrait/presentation callbacks SHALL follow commit. Bound-target DEFEAT SHALL bind only its objective targets and quantities SHALL remain satisfiable. ESCORT publication and protected-entity binding SHALL stay guarded until the owning protected-role flow exists and SHALL never auto-complete on entry.

#### Scenario: Validated permanent occupants replace the blanket restriction
- **WHEN** a validated package stage requiring a named role materializes at a permanent destination
- **THEN** the existing room is reused, its description is unchanged, and exactly one package-owned role binding exists

#### Scenario: Instance stage preserves ordinary construction
- **WHEN** a valid accepted instance stage with disposable occupants is materialized
- **THEN** one room and bidirectional exit pair with scene metadata and owned occupants are committed with the objective binding, and repeat materialization creates nothing

#### Scenario: Stage and encounter eligibility remain separate
- **WHEN** accepted-stage materialization is attempted without an in-progress quest
- **THEN** it rejects without writes, while independently eligible pre-acceptance encounters use their separate lifecycle boundary

#### Scenario: Escort remains guarded
- **WHEN** an ESCORT definition is proposed before a protected-role production binding path exists
- **THEN** publication rejects it and entering a destination grants no escort progress

#### Scenario: Binding failure rolls back the scene
- **WHEN** failure occurs after instance creation, occupant writes, or binding
- **THEN** no partial objects or stale binding remain after reload and no move or presentation occurs

#### Scenario: An instance scene is spawned, described, and bound
- **WHEN** a current `BOUND_INSTANCE` stage with `npc_reqs` is materialized from a caller's room
- **THEN** one `InstanceRoom` and a bidirectional plain exit pair exist, the room carries the
  requirement's `scene_archetype` and description, one NPC per `npc_req` is present and owned, and
  the stage is bound to the room and objective targets in one atomic operation

#### Scenario: A permanent-layer scene is located without spawning or binding
- **WHEN** a current permanent anchor/grid stage without validated package-owned occupants is materialized, including any legacy ESCORT stage still guarded from publication
- **THEN** it locates the existing room without spawning or binding and never grants escort progress

#### Scenario: DEFEAT occupants map to the objective-target binding set
- **WHEN** a DEFEAT stage materializes its occupants
- **THEN** the DEFEAT stage's occupants are recorded as objective targets, no entity appears in any
  other binding set, and an ESCORT stage is never bound through the SceneBuilder

#### Scenario: A mid-spawn failure rolls everything back
- **WHEN** an occupant spawn fails after the room and its first exit were created
- **THEN** the call raises, and neither the room, the exit pair, nor any created occupant remains in
  the database

#### Scenario: A failure after binding rolls back and leaves no stale binding
- **WHEN** a failure occurs after the room and occupants were bound
- **THEN** the call raises, no room, exit, or occupant remains, and a fresh quest-log read shows the
  stage unbound (no stale in-process binding is observable)

#### Scenario: Re-entry is idempotent
- **WHEN** `materialize_stage` is called again for a stage that is already bound
- **THEN** it returns the existing binding and creates no new room, exit, or occupant

#### Scenario: Invalid materialization requests are named and side-effect-free
- **WHEN** `materialize_stage` targets an unknown quest, an inactive or terminal stage, a stage
  without spawn requirements, or an origin room that does not match the stage's declared `anchor_near`
- **THEN** it raises a named `SceneBuilderError` variant and no state changes

#### Scenario: The call resolves the actor's current active stage
- **WHEN** `materialize_stage` is invoked
- **THEN** it resolves the actor's current active stage and that stage's registered spawn requirements

#### Scenario: Instance materialization uses the whitelisted prototype and plain exit pair
- **WHEN** an `instance`-layer destination materializes
- **THEN** the `InstanceRoom` spawns through `world.maps.instance.spawn_instance_room` using the whitelisted `instance_room` prototype with a plain exit pair

#### Scenario: The room carries the scene metadata
- **WHEN** an instance room is spawned
- **THEN** the room's `scene_archetype`, `named`, and scene description (the requirement's `scene_sentence` or the archetype registry's) are set

#### Scenario: Occupants are spawned per requirement and owned
- **WHEN** an instance stage carrying `npc_req` entries; or a monster-tier DEFEAT stage; is materialized
- **THEN** one NPC is spawned per `npc_req` entry and `objective.quantity` monsters are spawned for a monster-tier DEFEAT stage, and every occupant is registered as an owned entity

#### Scenario: An ESCORT stage never spawns or binds its protected entities
- **WHEN** an ESCORT stage is materialized
- **THEN** it is treated as a permanent destination located only, the SceneBuilder never spawns or binds the escort's protected entities, and an ESCORT can never auto-complete on entry

#### Scenario: Occupant-bearing scenes are instance-layer by publication rule
- **WHEN** an occupant-bearing definition is published
- **THEN** disposable ordinary scenes remain instance-owned, while permanent occupants require the replacement validated package ownership, exact binding and retention contracts; unsupported ESCORT publication stays rejected

#### Scenario: The atomic scope covers every instance write
- **WHEN** an instance materialization runs
- **THEN** the room spawn, the exit pair, the occupants, their ownership, and the binding all run inside the one outer `transaction.atomic()`, so a failure at any point rolls back every created object and restores the actor's quest-log state leaving no stale binding observable

#### Scenario: The move into the scene follows the commit
- **WHEN** a caller materializes a scene it is entering
- **THEN** the player's move into the scene happens only after the materialization commits

#### Scenario: The idempotent return is validated
- **WHEN** repeated current-stage materialization returns an existing binding
- **THEN** its room and exact actor availability are revalidated against the declared instance or permanent destination without actor recreation

