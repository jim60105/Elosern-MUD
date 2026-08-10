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
`world/quests/scene_builder.py` SHALL be a deterministic module that imports no `world.ai` module and
no live transport, SHALL consume a stage's spawn requirements only as plain validated data
(`StageSpawnRequirement` read through `scene_requirements_for(definition_key)`), and SHALL change game
state only through the deterministic lifecycle APIs: `world.maps.instance.spawn_instance_room` for
instance rooms, Evennia prototype spawning for occupants, `world.maps.instance.register_owned_entity`
for occupant ownership, and `world.quests.binding.bind_stage_runtime` for stage binding. The module
SHALL be importable and callable from `commands/` without referencing the generative package.

#### Scenario: The module stays inside the deterministic-path ban
- **WHEN** the repository-wide deterministic-path contract scans `world/quests/`
- **THEN** `scene_builder.py` carries no `world.ai`, `ollama`, or `llm_client` fragment, and no
  contract test requires an edit

#### Scenario: Every state change flows through the deterministic core
- **WHEN** `scene_builder.py` is inspected against the state-writer surface
- **THEN** it spawns and binds only through the named deterministic APIs and never calls a
  generative-layer module to write state

### Requirement: Anti-hallucination: the proposal never chooses numbers, stats, or class lineage
SceneBuilder SHALL accept from a stage's registered requirements only registry keys — archetype in
`SCENE_ARCHETYPE_REGISTRY`, NPC tier in `NPC_TIER_REGISTRY`, monster tier in `MONSTER_TIER_REGISTRY`,
anchor in `ANCHOR_PLACEMENT_REGISTRY`, and a layer — and SHALL derive every stored numeric stat
deterministically from the immutable lore tables (`world.rules.traits.build_initial_traits` for NPC
role tiers and `build_initial_traits_for_monster_tier` for monster tiers). Every occupant SHALL be
spawned through a prototype whose parent is selected only from the module's
`SCENE_OCCUPANT_PROTOTYPE_WHITELIST`. A requirement that fails to resolve, or any payload that
attempts to supply a numeric stat, a typeclass path, or a prototype parent outside the whitelist,
SHALL be rejected with a named `SceneBuilderError` before any room or entity is created. The
number ban SHALL cover mechanical and balance values — numeric stats, rewards, and bands. The
validated characterization fields (`display_name`, paired `age`/`apparent_age` bounded by the
adult floor and the race lifespan, and the portrait `stable_key`) are authored content like
speech and SHALL NOT be treated as mechanical numbers; they never feed stored stats, which remain
derived deterministically from the lore tables.

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

### Requirement: NPC role tiers resolve deterministic physical stats through the lore registries
SceneBuilder SHALL derive an NPC occupant's stored traits from its `NPCTier` entry's `race_key` and
`static_tier_key` via `world.rules.traits.build_initial_traits(race_key, tier=static_tier_key)`,
setting `magic_level` to the race's `starting_magic_level`; it SHALL read these values from the
immutable registries and SHALL NOT duplicate balance constants anywhere in `world/quests/`.

#### Scenario: Two NPCs of one tier store identical lore-derived stats
- **WHEN** two occupants are spawned from the same `npc_req` tier
- **THEN** both store identical stats equal to the race/static-tier-derived values

#### Scenario: The derivation is fully registry-backed
- **WHEN** the scene-builder tests inspect the derivation inputs
- **THEN** every race key and static tier key resolves in `RACE_REGISTRY` and
  `STATIC_TIER_REGISTRY`, with the static tier belonging to the declared race

### Requirement: Materializing a stage spawns the destination, sets scene metadata, and binds one stage atomically and idempotently
`world/quests/scene_builder.py::materialize_stage(actor, quest_id, *, origin_room=None)` SHALL resolve
the actor's current active stage and its registered spawn requirements. For an `instance`-layer
destination it SHALL spawn one `InstanceRoom` through `world.maps.instance.spawn_instance_room` using
the whitelisted `instance_room` prototype with a plain exit pair, set `scene_archetype`, `named`, and
the scene description (the requirement's `scene_sentence` or the archetype registry's), spawn one NPC
per `npc_req` entry and `objective.quantity` monsters for a monster-tier DEFEAT stage, register every
occupant as an owned entity, map occupants to objective targets for DEFEAT stages, and bind room and
entity identities through `bind_stage_runtime`. (ESCORT stages are permanent destinations located
only; the SceneBuilder never spawns or binds an escort's protected entities, so an ESCORT can never
auto-complete on entry.) For a permanent `anchor`/`grid` destination it SHALL only locate the existing
room and SHALL NOT spawn occupants or bind — occupant-bearing scenes are always instance-layer
(enforced at publication), so a permanent layer never accumulates spawned scene entities and needs no
scene cleanup. The whole instance materialization SHALL run inside one outer `transaction.atomic()`
(the room spawn, the exit pair, the occupants, their ownership, and the binding), so a failure at any
point rolls back every created object and restores the actor's quest-log state so no stale binding is
observable; the player's move into the scene SHALL happen only after the materialization commits.
Repeating the call for an already-bound current stage SHALL be idempotent — it returns the existing
binding (validated to still be an `InstanceRoom`) and spawns nothing. An unknown quest, an inactive or
terminal stage, a stage with no spawn requirements, or a caller not at a valid origin SHALL raise a
named `SceneBuilderError` variant with no state change.

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

### Requirement: The composition root posts one generated quest to the guild board and degrades offline
`server/ai_director_service.py::request_generated_quest(client=None, *, context)` SHALL bridge the
director's guarded proposal to the deterministic compile boundary: it SHALL call
`generate_quest_blueprint` with the injected client (or an `OpenAICompatClient` built from the
`scenario_director` profile when no client is injected and that profile is enabled), compile the
accepted blueprint through `compile_quest_blueprint`, and publish it through `register_generated_quest`
so the offer appears on the guild board. It SHALL defer every `world.ai` import to the call path so
importing the module at server startup cannot bind a `None` logger. The call SHALL resolve to the
registered `CompiledQuest` — never to `None` and never to an unregistered definition — and SHALL
resolve to a context-fitting hand-written template quest when the profile is disabled or every attempt
degrades, exactly as `generate_quest_blueprint` degrades.

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

### Requirement: The hand-written template pool gains an instance-layer scene so offline play exercises the materializer
`world/ai/director_templates.py` SHALL add at least one instance-layer template whose stage carries
`location_req.layer: "instance"` and a non-empty `npc_req`, so a disabled-profile `guild request` can
resolve to a quest whose scene change 21's SceneBuilder materializes. The added template SHALL satisfy
the output schema, every semantic validator (including the scene-bound rules), and compile to a
definition whose instance stage binds through `bind_stage_runtime`, keeping the offline loop fully
playable without an LLM.

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

### Requirement: Scene entry and generated-quest triggers are deterministic commands that keep the offline loop playable
`commands/scene.py::CmdEnterScene` (`進入`/`enter`) SHALL materialize the caller's first enterable
active instance stage (the first active quest, in log order, whose current stage carries a
registered instance-layer spawn requirement whose declared `anchor_near`, if any, matches the
caller's current location — unless the caller is already inside the bound room) through
`materialize_stage` and, after the scene commits, move the caller into the spawned room through the
plain exit the builder created (ordinary traversal, which charges the standard `move` clock cost and
records map knowledge); the command SHALL verify the exit's traverse access before traversing and
SHALL report success only after the caller actually reaches the room. When the caller has no
enterable instance scene (permanent destination, no requirements, or a wrong anchor) it SHALL report
that side-effect-free. `commands/guild.py::CmdGuildRequest` (`guild request`/`guild 委託`) SHALL build
the director request context from the caller's guild registration and call `request_generated_quest`,
reporting the posted offer's definition key (or the named error when no compatible template exists
offline); while a request is in flight it SHALL reject a duplicate submission. Neither command SHALL
import a `world.ai` module. The combined offline flow — every `LLM_PROFILES` entry disabled → `guild
request` posts the instance-layer template quest → `guild accept` accepts it → `進入` materializes the
scene → the bound occupants are defeated → `guild turnin` claims the reward — SHALL complete with no
LLM call and no generative state mutation.

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
`world/quests/scene_builder.py` SHALL, after spawning and registering occupants inside the same outer
atomic materialization, schedule a portrait ensure through `transaction.on_commit` for any occupant
that carries an explicit `{"mode": "named", "stable_key": ...}` portrait policy, so the schedule fires
only after the materialization commits and an art failure can never roll back a materialized scene. An
occupant with no policy (every role-based scene NPC and monster spawned today) SHALL schedule nothing.
The existing atomicity, idempotency, and lore-derived-stat behavior of `materialize_stage` SHALL be
unchanged.

#### Scenario: A generic role-based occupant schedules no portrait
- **WHEN** a scene with role-based NPCs and monsters is materialized
- **THEN** none of the occupants carries a portrait policy and no post-commit portrait job is scheduled

#### Scenario: A named-policy occupant schedules after commit only
- **WHEN** an occupant carrying an explicit named portrait policy is materialized and the transaction
  commits
- **THEN** exactly one post-commit portrait ensure is scheduled for that occupant's subject, and no
  artwork failure can roll back the materialization

#### Scenario: A rolled-back materialization emits no portrait job
- **WHEN** an occupant spawn fails after an earlier occupant was spawned and the outer transaction
  rolls back
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is unchanged

