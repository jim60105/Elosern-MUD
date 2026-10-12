# Spec Delta

## MODIFIED Requirements

### Requirement: Materializing a stage spawns the destination, sets scene metadata, and binds one stage atomically and idempotently
Stage materialization SHALL retain accepted-current-stage eligibility, shared whitelisted construction, exact bindings, disposable instance ownership, permanent package-role ownership/retention, validated idempotent reuse, and all-or-nothing cache restoration from the upstream encounter change. Escort acceptance SHALL bind the upstream's already materialized exact protected actors through the quest/party owners. Escort destination materialization SHALL resolve its validated anchor/XYZ or actual bound instance separately from protected-role creation; it SHALL not spawn replacement participants into the destination or grant progress from description/room creation. Rendezvous SHALL require no fabricated destination. Missing/dead/departed bound actors SHALL return named unavailable results without repair.

#### Scenario: Existing stage construction remains atomic
- **WHEN** an ordinary accepted instance stage materializes or a validated package stage uses a permanent room
- **THEN** existing room/exit/metadata/occupant ownership and exact-binding behavior remains and an injected later failure restores objects and caches

#### Scenario: Escort uses the retained actor
- **WHEN** a protected role has moved away from its original encounter and its destination is materialized
- **THEN** the role's exact identity/location/history remain unchanged, no second NPC appears, and progress requires actual settled movement

#### Scenario: Wrong eligibility refuses without scene edits
- **WHEN** stage materialization targets an unknown, inactive, terminal, requirement-less or wrong-origin record
- **THEN** the existing named side-effect-free error returns and independent encounter activation remains a separate operation

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
- **WHEN** an escort proposal lacks the complete implemented protected-role and completion contract
- **THEN** publication rejects and entering a destination cannot grant false escort progress

#### Scenario: Binding failure rolls back the scene
- **WHEN** failure occurs after instance creation, occupant writes, or binding
- **THEN** no partial objects or stale binding remain after reload and no move or presentation occurs

#### Scenario: An instance scene is spawned, described, and bound
- **WHEN** a current `BOUND_INSTANCE` stage with `npc_reqs` is materialized from a caller's room
- **THEN** one `InstanceRoom` and a bidirectional plain exit pair exist, the room carries the
  requirement's `scene_archetype` and description, one NPC per `npc_req` is present and owned, and
  the stage is bound to the room and objective targets in one atomic operation

#### Scenario: A permanent-layer scene is located without spawning or binding
- **WHEN** a permanent destination without validated package-owned occupants is materialized
- **THEN** the existing room is located without room/exit/participant creation; protected escort actors remain independently bound through acceptance

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
- **WHEN** an escort destination materializes or a rendezvous objective is evaluated
- **THEN** the builder creates no protected replacement actor; acceptance owns exact protected binding, and actual settled position determines completion

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

### Requirement: The composition root posts one generated quest to the guild board and degrades offline
The existing composition root SHALL retain injected-client/disabled-profile degradation and deterministic compile/registration ownership. Supported generated escorts SHALL proceed only when the complete new published-role/completion contract is available and the owning flow is implemented and proved. An unsupported escort request SHALL retain the shared pre-transport unsupported-template refusal (`NoSuitableTemplateError`); no template SHALL fabricate actors or relabel an objective. Complete private scene packages SHALL publish scoped commissions through upstream publication/activation without autoacceptance or forcing a guild offer. Existing guild requests SHALL keep their registered-offer result and `NoSuitableTemplateError` behavior.

#### Scenario: Supported and unsupported escort requests are distinct
- **WHEN** synthetic requests exercise a complete supported escort package and an unsupported ordinary escort template through the composition service
- **THEN** the supported path reaches deterministic publication and later real acceptance/completion; the unsupported path refuses before client work and registers nothing

#### Scenario: Existing disabled-profile guild flow still works
- **WHEN** an ordinary guild request uses a disabled director profile
- **THEN** the context-fitting template posts the same registered offer without calling live transport

#### Scenario: A generated quest reaches the guild board
- **WHEN** a client returns a valid context-fitting blueprint and `request_generated_quest` runs
- **THEN** the Deferred resolves to a `CompiledQuest` whose definition, offer, and spawn requirements
  are all registered, and no `world.ai` module mutated state

#### Scenario: The offline path posts a template quest
- **WHEN** the `scenario_director` profile is disabled and `request_generated_quest` is called
- **THEN** it resolves to a context-fitting template quest compiled and registered with zero client
  calls

#### Scenario: The module imports before server initialization without binding a logger
- **WHEN** `server.ai_director_service` is cold-imported before `evennia._init()`
- **THEN** the import succeeds and no generative module-level logger is bound at import time

#### Scenario: The client falls back to the enabled profile
- **WHEN** no client is injected and the `scenario_director` profile is enabled
- **THEN** `request_generated_quest` calls `generate_quest_blueprint` with an `OpenAICompatClient` built from the `scenario_director` profile

#### Scenario: Generative imports defer to the call path
- **WHEN** the module's source is inspected
- **THEN** every `world.ai` import is deferred to the call path, so importing the module at server startup cannot bind a `None` logger

#### Scenario: The call never resolves empty or unregistered
- **WHEN** `request_generated_quest` resolves
- **THEN** it resolves to the registered `CompiledQuest` — never to `None` and never to an unregistered definition

#### Scenario: Degradation matches the blueprint generator
- **WHEN** the profile is disabled or every attempt degrades
- **THEN** the call resolves to a context-fitting hand-written template quest, exactly as `generate_quest_blueprint` degrades

## ADDED Requirements

### Requirement: Generated escort registration guards durable publication and restore
Generated registration SHALL revalidate the complete protected-role/completion/group contract independently of the generative path, before durable or registry writes. Successful publication/restoration SHALL preserve every exact reference and separate issuance. Conflicting registration or durable write failure SHALL restore all registry/cache/durable surfaces. Publication SHALL create no accepted quest or temporary party source; those belong to explicit acceptance.

#### Scenario: Forged compiled escort cannot reach persistence
- **WHEN** direct generated registration receives an escort missing its executable protected-role contract
- **THEN** it returns a named compile/publication refusal without durable payload, definition, issuance or requirements entry

#### Scenario: Registration and reload preserve the real path
- **WHEN** a supported package is registered twice and restored after restart
- **THEN** its exact definitions, references and issuances resolve once, no accepted quest is added, and later acceptance uses the same actual role bindings
