## Purpose

Defines the deterministic SceneBuilder materialization layer (design §7.2): turning one stage's
registered spawn requirements into a real scene — instance room, lore-statted occupants, scene
metadata, and an atomic `bind_stage_runtime` binding — under the anti-hallucination rule that
requirements carry only registry keys and the LLM never chooses numbers. It also owns the
composition root that posts generated quests to the guild board, the instance-layer offline template,
and the minimal commands that trigger generation and scene entry. The materializer is deterministic
(it spawns and binds, so it lives in `world/quests/`), atomic, and idempotent; permanent layers are
located only and never accumulate spawned entities.
## Requirements

### Requirement: SceneBuilder is the deterministic requirements-to-spawn materialization layer
`world/quests/scene_builder.py` SHALL be a deterministic module that imports no `world.ai` module and no live transport, consumes a stage's spawn requirements only as plain validated data (`StageSpawnRequirement` via `scene_requirements_for(definition_key)`), and changes game state only through the deterministic lifecycle APIs: `world.maps.instance.spawn_instance_room`, Evennia prototype spawning, `world.maps.instance.register_owned_entity`, and `world.quests.binding.bind_stage_runtime`.

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

### Requirement: Anti-hallucination: the proposal never chooses numbers, stats, or class lineage
SceneBuilder SHALL accept from a stage's registered requirements only registry keys — archetype in `SCENE_ARCHETYPE_REGISTRY`, NPC tier in `NPC_TIER_REGISTRY`, monster tier in `MONSTER_TIER_REGISTRY`, anchor in `ANCHOR_PLACEMENT_REGISTRY`, and a layer — and SHALL derive every stored numeric stat deterministically from the immutable lore tables (`world.rules.traits.build_initial_traits` for NPC role tiers and `build_initial_traits_for_monster_tier` for monster tiers).

#### Scenario: An unknown key is rejected before any spawn
- **WHEN** a stage's requirement names an archetype or tier absent from the lore registries
- **THEN** `materialize_stage` raises a named `SceneBuilderError` and no room, exit, or occupant is
  created

#### Scenario: A numeric stat in a payload is rejected
- **WHEN** a stage's requirement payload attempts to supply a numeric stat (for example an HP or
  attack value)
- **THEN** it is rejected with a named `SceneBuilderError` before any entity is created

#### Scenario: A validated characterization age is not a mechanical number
- **WHEN** a stage's requirement carries the validated `age`/`apparent_age` fields
- **THEN** the requirement resolves normally, the ages never enter any stored trait, and all stored
  stats still come from the lore tables

#### Scenario: Stored stats equal the lore-table values
- **WHEN** occupants are spawned from a tier
- **THEN** each occupant's stored `hp`, `atk_phys`, `agility`, and `defense` equal the values the
  lore registries produce, and no number from any proposal influenced them

#### Scenario: Occupants spawn only from whitelisted prototypes
- **WHEN** the materializer spawns an occupant
- **THEN** the prototype's parent is selected only from the module's `SCENE_OCCUPANT_PROTOTYPE_WHITELIST`

#### Scenario: An unresolvable requirement or forged payload identity is rejected
- **WHEN** a requirement fails to resolve, or a payload attempts to supply a numeric stat, a typeclass path, or a prototype parent outside the whitelist
- **THEN** it is rejected with a named `SceneBuilderError` before any room or entity is created

#### Scenario: The number ban spans mechanical and balance values
- **WHEN** a proposal attempts to supply mechanical or balance values
- **THEN** numeric stats, rewards, and bands are all banned and none is accepted

#### Scenario: Characterization fields are authored content, not numbers
- **WHEN** a requirement carries the validated `display_name`, paired `age`/`apparent_age` bounded by the age floor and the race lifespan, and the portrait `stable_key`
- **THEN** they are treated as authored content like speech and SHALL NOT be treated as mechanical numbers, and they never feed stored stats, which remain derived deterministically from the lore tables

### Requirement: NPC role tiers resolve deterministic physical stats through the lore registries
SceneBuilder SHALL derive an NPC occupant's stored traits from its `NPCTier` entry's `race_key` and `static_tier_key` via `world.rules.traits.build_initial_traits(race_key, tier=static_tier_key)`, reading the values from the immutable registries; it SHALL NOT duplicate balance constants anywhere in `world/quests/`.

#### Scenario: Two NPCs of one tier store identical lore-derived stats
- **WHEN** two occupants are spawned from the same `npc_req` tier
- **THEN** both store identical stats equal to the race/static-tier-derived values

#### Scenario: Spawned deep-skill NPCs can use their skills
- **WHEN** an NPC tier owns a skill carrying prerequisite edges and is materialized
- **THEN** the spawned entity's `can_use_skill` passes for that skill via exactly-seeded prerequisites

#### Scenario: The derivation is fully registry-backed
- **WHEN** the scene-builder tests inspect the derivation inputs
- **THEN** every race key and static tier key resolves in `RACE_REGISTRY` and
  `STATIC_TIER_REGISTRY`, with the static tier belonging to the declared race

#### Scenario: Magic power comes from the tier's magic_band floor
- **WHEN** an NPC occupant's traits are derived
- **THEN** the derivation reads the tier's `magic_band` floor into `magic_power`, and the deleted race-level `starting_magic_level` has no successor constant

#### Scenario: The spawn path shares the lineage auto-seed helper
- **WHEN** the spawn path materializes an occupant with deep skills
- **THEN** it shares the lineage auto-seed helper — prerequisite proficiency seeded to exactly the edge values for owned deep skills, with explicit assignments winning

### Requirement: Materializing a stage spawns the destination, sets scene metadata, and binds one stage atomically and idempotently
`world/quests/scene_builder.py::materialize_stage(actor, quest_id, *, origin_room=None)` SHALL, for an `instance`-layer destination, spawn one `InstanceRoom`, set scene metadata, spawn occupants, and bind room and entity identities through `bind_stage_runtime` inside one outer `transaction.atomic()`; for a permanent `anchor`/`grid` destination it SHALL only locate the existing room, never spawning occupants or binding.

#### Scenario: An instance scene is spawned, described, and bound
- **WHEN** a current `BOUND_INSTANCE` stage with `npc_reqs` is materialized from a caller's room
- **THEN** one `InstanceRoom` and a bidirectional plain exit pair exist, the room carries the
  requirement's `scene_archetype` and description, one NPC per `npc_req` is present and owned, and
  the stage is bound to the room and objective targets in one atomic operation

#### Scenario: A permanent-layer scene is located without spawning or binding
- **WHEN** a current stage with a permanent `anchor`/`grid` destination (including an ESCORT stage)
  is materialized
- **THEN** the existing room is located, and no room, exit, occupant, or quest binding is created, so
  permanent rooms are never polluted by scene entities and an ESCORT never auto-completes on entry

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
- **WHEN** an instance stage carrying `npc_req` entries — or a monster-tier DEFEAT stage — is materialized
- **THEN** one NPC is spawned per `npc_req` entry and `objective.quantity` monsters are spawned for a monster-tier DEFEAT stage, and every occupant is registered as an owned entity

#### Scenario: An ESCORT stage never spawns or binds its protected entities
- **WHEN** an ESCORT stage is materialized
- **THEN** it is treated as a permanent destination located only, the SceneBuilder never spawns or binds the escort's protected entities, and an ESCORT can never auto-complete on entry

#### Scenario: Occupant-bearing scenes are instance-layer by publication rule
- **WHEN** a quest definition is published
- **THEN** occupant-bearing scenes are enforced to be instance-layer, so a permanent layer never accumulates spawned scene entities and needs no scene cleanup

#### Scenario: The atomic scope covers every instance write
- **WHEN** an instance materialization runs
- **THEN** the room spawn, the exit pair, the occupants, their ownership, and the binding all run inside the one outer `transaction.atomic()`, so a failure at any point rolls back every created object and restores the actor's quest-log state leaving no stale binding observable

#### Scenario: The move into the scene follows the commit
- **WHEN** a caller materializes a scene it is entering
- **THEN** the player's move into the scene happens only after the materialization commits

#### Scenario: The idempotent return is validated
- **WHEN** a repeated `materialize_stage` call for an already-bound current stage returns the existing binding
- **THEN** the returned binding is validated to still be an `InstanceRoom`

### Requirement: The composition root posts one generated quest to the guild board and degrades offline
`server/ai_director_service.py::request_generated_quest(client=None, *, context)` SHALL bridge the director's guarded proposal to the deterministic compile boundary: it SHALL call `generate_quest_blueprint` with the injected client, compile the accepted blueprint through `compile_quest_blueprint`, and publish it through `register_generated_quest` so the offer appears on the guild board.

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

### Requirement: The hand-written template pool gains an instance-layer scene so offline play exercises the materializer
`world/ai/director_templates.py` SHALL add at least one instance-layer template whose stage carries `location_req.layer: "instance"` and a non-empty `npc_req`, so a disabled-profile `guild request` can resolve to a quest whose scene change 21's SceneBuilder materializes. The added template SHALL satisfy the output schema, every semantic validator (including the scene-bound rules), and compile to a definition whose instance stage binds through `bind_stage_runtime`.

#### Scenario: The new instance template validates and compiles
- **WHEN** the instance-layer template is run through the output schema, the semantic validators, and
  `compile_quest_blueprint`
- **THEN** it passes all three and registers with a definition whose instance stage carries the
  preserved spawn requirements

#### Scenario: An offline request can produce a materializable instance quest
- **WHEN** the `scenario_director` profile is disabled and the request context matches the new
  instance template
- **THEN** the degraded draw is the instance-layer template, which SceneBuilder can materialize into a
  real room and occupants

#### Scenario: The offline loop stays fully playable without an LLM
- **WHEN** the new instance template serves disabled-profile requests end to end
- **THEN** the offline loop remains fully playable without an LLM

### Requirement: Scene entry and generated-quest triggers are deterministic commands that keep the offline loop playable
`commands/scene.py::CmdEnterScene` (`進入`/`enter`) SHALL materialize the caller's first enterable active instance stage through `materialize_stage` and, only after the scene commits, move the caller into the spawned room through the plain exit the builder created. `commands/guild.py::CmdGuildRequest` SHALL call `request_generated_quest` with a context built from the caller's guild registration. Neither command SHALL import a `world.ai` module.

#### Scenario: The offline end-to-end loop materializes an instance scene without an LLM
- **WHEN** every `LLM_PROFILES` entry is disabled and the full request → accept → materialize → fight
  → turn-in loop runs
- **THEN** the loop completes, SceneBuilder spawns the instance room and its bound occupants, every
  state change flows through the deterministic core, and no generative module wrote state

#### Scenario: The command sources stay inside the deterministic-path ban
- **WHEN** the repository-wide deterministic-path contract scans `commands/`
- **THEN** the two command modules carry no `world.ai`, `ollama`, or `llm_client` fragment

#### Scenario: Entering without a valid instance scene is a named, side-effect-free rejection
- **WHEN** `進入` is used with no active instance stage, from inside the already-bound room, or from an
  origin that does not match the stage's declared location
- **THEN** it reports a named error and no room, exit, or occupant is created

#### Scenario: Entering selects the first enterable instance stage
- **WHEN** the caller holds several active instance-stage quests but only a later one is enterable
  from the current anchor
- **THEN** `進入` selects and enters the enterable stage rather than failing on an earlier one

#### Scenario: A failed traversal is not reported as success
- **WHEN** the created plain exit denies traverse access or the caller's move is vetoed
- **THEN** `進入` does not report that the caller entered the scene

#### Scenario: Entry stage selection is anchored and log-ordered
- **WHEN** `CmdEnterScene` picks the stage to materialize
- **THEN** it selects the first active quest, in log order, whose current stage carries a registered instance-layer spawn requirement whose declared `anchor_near`, if any, matches the caller's current location — unless the caller is already inside the bound room

#### Scenario: The move into the spawned room is ordinary traversal
- **WHEN** the caller moves through the builder-created plain exit
- **THEN** the traversal is ordinary: it charges the standard `move` clock cost and records map knowledge

#### Scenario: Traverse access is verified before the command reports
- **WHEN** `CmdEnterScene` traverses the created exit
- **THEN** it verifies the exit's traverse access before traversing and reports success only after the caller actually reaches the room

#### Scenario: No enterable scene is reported side-effect-free
- **WHEN** the caller has no enterable instance scene (permanent destination, no requirements, or a wrong anchor)
- **THEN** `進入` reports that side-effect-free

#### Scenario: The guild request reports the posted offer or the named error
- **WHEN** `CmdGuildRequest` (`guild request`/`guild 委託`) runs
- **THEN** it reports the posted offer's definition key, or the named error when no compatible template exists offline

#### Scenario: A duplicate request is rejected while one is in flight
- **WHEN** `guild request` is submitted while a previous request is still in flight
- **THEN** the duplicate submission is rejected

#### Scenario: The named offline flow completes without an LLM
- **WHEN** every `LLM_PROFILES` entry is disabled and the combined flow runs: `guild request` posts the instance-layer template quest → `guild accept` accepts it → `進入` materializes the scene → the bound occupants are defeated → `guild turnin` claims the reward
- **THEN** the flow completes with no LLM call and no generative state mutation

### Requirement: Every scene-builder test runs offline and the boundary invariants stay green
Scene-builder tests SHALL use `evennia.utils.test_resources.EvenniaTest` for database, typeclass,
room, and command integration and `FakeLLMClient` for the composition service; they SHALL never
construct `OpenAICompatClient` and never open a network connection. The repository-wide AI
transport-boundary and deterministic-path contract tests SHALL pass with no edits, and no module
under `world/ai/` SHALL import the SceneBuilder.

#### Scenario: All scene-builder tests run without a live endpoint
- **WHEN** the scene-builder test suites run with no LLM service available
- **THEN** every test passes using `EvenniaTest` fixtures and `FakeLLMClient`, and none constructs
  `OpenAICompatClient` or a socket

#### Scenario: The repository-wide contracts stay green with no edits
- **WHEN** the AI transport-boundary and deterministic-path contract tests run after this change
- **THEN** they pass unchanged, and no `world/ai/` production module imports `world.quests.scene_builder`
  or any other state writer

### Requirement: The occupant spawn path exposes a post-commit portrait-eligibility seam with unchanged atomicity
`world/quests/scene_builder.py`'s occupant spawn path SHALL apply the characterization carried by `StageSpawnRequirement` (display name, paired canonical ages, and the named portrait `stable_key` from `blueprint-portrait-policy`) when present: `db.display_name`, `db.age` / `db.apparent_age` (declared values, or the deterministic age baseline 25 when a portrait policy is declared and the ages are absent), and `db.portrait_policy = {"mode": "named", "stable_key": ...}`.

#### Scenario: A generic role-based occupant schedules no portrait
- **WHEN** an occupant carries no portrait policy
- **THEN** no post-commit portrait job is scheduled, matching the pre-change behavior

#### Scenario: A characterized named occupant schedules exactly one portrait
- **WHEN** an occupant carrying an applied named portrait policy is materialized and the transaction
  commits
- **THEN** exactly one post-commit portrait ensure is scheduled for that occupant's subject, and
  no other scheduling path exists

#### Scenario: A rolled-back materialization emits no portrait job
- **WHEN** the materialization transaction rolls back after occupants were created
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is
  unchanged

#### Scenario: The portrait apply writes the full policy dict
- **WHEN** a characterized occupant is spawned
- **THEN** `db.portrait_policy` is exactly `{"mode": "named", "stable_key": ...}` and canonical
  ages are present before the policy is set

#### Scenario: The portrait schedule fires only after the commit
- **WHEN** an occupant carrying an explicit named portrait policy is materialized inside the atomic materialization
- **THEN** the spawn path schedules a portrait ensure through `transaction.on_commit`, inside the same atomic materialization, so the schedule fires only after the materialization transaction commits and an art failure can never roll back a materialized scene

#### Scenario: A rollback keeps its existing full behavior
- **WHEN** the materialization transaction rolls back
- **THEN** it emits no post-commit portrait job and the existing full rollback behavior is unchanged

#### Scenario: A generic occupant without characterization schedules nothing
- **WHEN** a generic role-based occupant without characterization is spawned
- **THEN** it carries no portrait policy and schedules nothing

### Requirement: NPC characterization carries a complete compact card through compile, restore, and materialization
Every occupant characterization on a `StageSpawnRequirement` SHALL carry a complete compact NPC card. The compiled requirement, the canonical payload, and the durable generated-quest payload SHALL store the normalized card, and decoding a durable payload SHALL reproduce it unchanged. Materialization SHALL revalidate the card through the shared characterization helper before any spawn and SHALL write it through the deterministic NPC persona initializer inside the same atomic materialization.

#### Scenario: A card survives compile and restore unchanged
- **WHEN** a blueprint occupant card is compiled, encoded into the durable store, decoded at restore, and materialized
- **THEN** the spawned NPC's persona equals the normalized proposal card leaf for leaf and its metadata is at version 1 with `generated_quest` provenance

#### Scenario: A forged requirement cannot bypass validation
- **WHEN** a `StageSpawnRequirement` is constructed directly with an occupant card that violates the contract and materialization runs
- **THEN** materialization raises before any spawn and no room, NPC, or binding persists

#### Scenario: A pre-change payload fails restore by name
- **WHEN** the durable store holds a payload whose occupant carries the old optional prose block or no card
- **THEN** restore raises naming the quest, stage, and occupant, and no partial registration remains

#### Scenario: Re-materialization keeps an edited occupant card
- **WHEN** an occupant's card was edited to version 2 and the same stage is materialized again idempotently
- **THEN** the occupant's card and version 2 are unchanged

#### Scenario: A payload with a missing or nonconforming card fails decoding by name
- **WHEN** a durable payload's occupant card is missing or does not satisfy the card contract
- **THEN** decoding fails with an error naming the quest, stage, and occupant, with no fallback decoder

#### Scenario: The persona write carries generated_quest provenance
- **WHEN** materialization writes an occupant's card through the deterministic NPC persona initializer
- **THEN** the provenance is `generated_quest` naming the quest, stage, and occupant position

#### Scenario: Re-materialization never overwrites an occupant card
- **WHEN** a stage is re-materialized over existing occupants
- **THEN** no existing occupant's card is overwritten

#### Scenario: The card never influences stored stats
- **WHEN** a characterized occupant is materialized
- **THEN** the card is characterization only and never influences stored stats

### Requirement: Scene materialization exposes deterministic flavor context for fresh instance scenes
For a freshly spawned `instance`-layer scene (not an already-bound stage, not a permanent destination), `materialize_stage` SHALL include in its `SceneMaterialization` result an optional flavor context: a plain bounded dict with exactly the four keys `scene_sentence`, `quest_context`, `room_name`, and `region`.

#### Scenario: A fresh instance scene carries the four-key flavor context
- **WHEN** a fresh instance scene materializes with a scene-sentence context and an `anchor_near`
  requirement
- **THEN** the result's flavor context is a bounded dict with exactly `scene_sentence`,
  `quest_context`, `room_name`, and `region` populated from deterministic sources

#### Scenario: An already-bound stage carries no flavor context
- **WHEN** `materialize_stage` returns an already-bound stage (idempotent re-entry)
- **THEN** the result's flavor context is `None` and nothing is scheduled

#### Scenario: A scene without a sentence carries no flavor context
- **WHEN** a stage's requirement has neither a scene sentence nor a resolvable archetype sentence
- **THEN** the result's flavor context is `None`

#### Scenario: Each flavor key has its deterministic source
- **WHEN** the flavor context is assembled
- **THEN** `scene_sentence` is the requirement's sentence or the archetype registry's, `quest_context` is the definition's `display_name` plus its `quest_type`, `room_name` is the scene room's name, and `region` is the anchor placement display name when the requirement declares `anchor_near`, else empty

#### Scenario: The context assembly stays off the generative path
- **WHEN** the flavor-context assembly is inspected
- **THEN** it references no generative module and no LLM profile, keeping the deterministic-path ban green

### Requirement: The scene flavor write is deterministic and never affects materialization
`world/quests/scene_builder.py` SHALL provide an `apply_scene_flavor(room, text)` helper as the sole writer of `room.db.scene_flavor`: it SHALL verify the room's database row authoritatively (`ObjectDB.objects.filter(pk=room.pk).exists()`) before any read-modify-write, SHALL otherwise write the flavor and return `True`, SHALL never touch `room.db.desc`, and SHALL never raise from a flavor context (a failure SHALL be a logged diagnostic with no state change).

#### Scenario: The sole writer applies once and only once
- **WHEN** `apply_scene_flavor` runs for an existing flavor-less room
- **THEN** it writes the flavor, returns `True`, and `room.db.desc` is unchanged

#### Scenario: Re-application is a no-op
- **WHEN** `apply_scene_flavor` runs again for a room that already carries the flavor
- **THEN** it returns `False` and keeps the existing value

#### Scenario: A vanished room is skipped without raising
- **WHEN** `apply_scene_flavor` runs with only a stale cached room reference after the instance
  room was reclaimed
- **THEN** the authoritative existence check fails (or the lookup raises and is caught), the helper
  returns `False`, and no state change occurs

#### Scenario: The deterministic path stays free of generative references
- **WHEN** the flavor-related source in `world/quests` is inspected
- **THEN** it contains no `world.ai`, `ollama`, or `llm_client` fragment, and the existing
  deterministic-path contract test passes without modification

#### Scenario: The database row, not the cache, proves existence
- **WHEN** the helper decides whether the room still exists
- **THEN** it trusts the authoritative database check because a cached typeclass is not proof of existence after reclamation

#### Scenario: Gone or already-flavored rooms are a no-op
- **WHEN** the room is gone or already carries a flavor
- **THEN** the helper no-ops and returns `False`

#### Scenario: Database and deletion exceptions return False
- **WHEN** a database or object-deletion exception is raised during the flavor write
- **THEN** the helper catches it and returns `False`

#### Scenario: Scheduling callers stay generative-free
- **WHEN** the helper's scheduling callers are inspected
- **THEN** they contain no reference to `world.ai` or any LLM profile, keeping `world/quests` inside the deterministic-path ban

### Requirement: Generated quest content is durably stored at registration time
The system SHALL persist the compiled definition, guild offer, and stage spawn requirements of every generated quest to durable storage as part of `register_generated_quest`.

#### Scenario: Generated quest registration persists content
- **WHEN** `register_generated_quest` publishes a compiled generated quest
- **THEN** the compiled definition, offer, and spawn requirements are appended to the durable generated-quest store

#### Scenario: Registration is idempotent
- **WHEN** the same generated quest key is registered twice
- **THEN** the durable store contains exactly one payload for that key
