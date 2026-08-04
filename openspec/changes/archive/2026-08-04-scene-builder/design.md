## Context

Change 20 shipped the last generative seam: `generate_quest_blueprint` returns a frozen
`QuestBlueprint` (always valid and context-fitting, degrading to the hand-written template pool when
offline), and the deterministic compile boundary maps it onto `QuestDefinition` + `QuestReward` +
issuer, publishing definition and offer all-or-nothing through `register_generated_quest`. The
compiled `CompiledQuest` carries `stage_requirements: tuple[StageSpawnRequirement, ...]` — per-stage
plain data (objective kind, destination locator, archetype, anchor hint, scene sentence, NPC role
requirements) explicitly preserved so change 21 can consume it "without importing the generative
package". Design §7.2 fixes what change 21 must do: turn those requirements into a prototype dict and
spawn, **triggered when the player actually arrives**, with the anti-hallucination rule that the LLM
never chooses numbers and `prototype_parent` comes from a whitelist. The roadmap labels the change
`Requirements → prototype → spawn, whitelists` and puts it on the critical path; after it, "the AI
Director is live".

The deterministic surfaces change 21 consumes already exist:

- `world/maps/instance.py::spawn_instance_room(origin_room, prototype, *, exit_key, return_key,
  ttl_seconds=None, named=False, caller=None)` spawns an `InstanceRoom` through
  `evennia.prototypes.spawner.spawn()`, validates `prototype_parent` against
  `INSTANCE_PROTOTYPE_WHITELIST` (= `("instance_room",)`, explicitly reserved for change 21),
  sets `expire_tick`/`named`/`origin_room`, and atomically attaches a plain `Exit` pair.
  `register_owned_entity(room, entity)` marks occupants so reclamation despawns them.
- `world/quests/binding.py::bind_stage_runtime(actor, quest_id, *, room, objective_targets,
  protected_entities)` pins the room (`quest:<cid>:<qid>:stage:<index>`) and entity dbrefs atomically
  and idempotently. `world/quests/runtime.py` gives `read_records`/`find_record`/`definition_for` and
  the `QuestRecord` fields (`stage_room_id`, `objective_target_ids`, `protected_entity_ids`).
- Lore registries: `SCENE_ARCHETYPE_REGISTRY`, `NPC_TIER_REGISTRY`, `MONSTER_TIER_REGISTRY`,
  `ANCHOR_PLACEMENT_REGISTRY`, `RACE_REGISTRY`, `STATIC_TIER_REGISTRY`; `world/rules/traits.py`
  derives stat configs (`build_initial_traits`, `build_initial_traits_for_monster_tier`).
- `world/prototypes.py` already defines `GRID_ROOM`, `ANCHOR_ROOM`, `INSTANCE_ROOM` module
  prototypes.

Two architectural constraints shape every decision:

1. **The single-writer / deterministic-path boundary.** No module under `world/ai/` may import a
   state writer (world.rules, world.maps, world.quests, typeclasses, spawner, create) or a live
   transport. Inversely, `world/rules`, `world/maps`, `world/quests`, and `commands` must not
   reference the fragments `world.ai`, `ollama`, or `llm_client` anywhere in source (enforced by an
   AST scan). Change 20 resolved that SceneBuilder is **deterministic** — it spawns, so it cannot
   live in `world/ai/` — and must consume requirements as plain data, not proposal objects.
2. **Lazy materialization.** §7.2: the scene is created when the player arrives, not when the quest
   is accepted. That means the spawn requirements must be reachable at arrival (they are transient in
   `CompiledQuest` today), and the trigger is a deterministic player action.

One additional observation drives placement: **`world/ai/scenario_director` may not be imported by
any deterministic package, and no deterministic package may drive the director.** The composition
root that asks the director for a quest and posts the compiled offer therefore cannot live in
`world/quests/`, `world/rules/`, `world/maps/`, `commands/`, or `world/ai/` — it must live where both
import directions are legal. `server/` is that seam: `server/conf/at_server_startstop.py` already
imports `world.ai` modules after `evennia._init()`, and `server/` is not scanned by either contract
test.

> **Design-document amendment (this change).** The approved design §3.1 lists `SceneBuilder` in the
> generative `world/ai/` layer and §7.5 gives it a generic-room degradation row. §7.2's own
> anti-hallucination rule — the LLM never chooses numbers, `prototype_parent` comes from a whitelist —
> plus the single-writer invariant and change 20's explicit resolution make the materializer a
> deterministic requirements→prototype→spawn compiler, not a generative LLM layer. This change
> amends §3.1 and §7.5: the generative "SceneBuilder" role is carried by the ScenarioDirector's
> `QuestBlueprint` (which already emits the scene requirements); the deterministic `world/quests`
> SceneBuilder is the sole §7.2 implementation; and §7.5's "SceneBuilder → generic room template"
> degradation row is replaced by "a named, side-effect-free rejection when a scene cannot
> materialize" (a deterministic layer needs no LLM degradation). The forward-declared `scene_builder`
> LLM profile remains registered but unused, available to a future generative scene-flavor layer.

## Goals / Non-Goals

**Goals:**

- Provide `world/quests/scene_builder.py::materialize_stage(actor, quest_id, *, origin_room=None)`
  as the deterministic, atomic, idempotent materialization of one active stage's spawn requirements:
  instance destination room, lore-statted occupants, scene metadata, owned-entity registration, and
  `bind_stage_runtime` binding — all inside one outer transaction, with the player's move deferred
  until commit.
- Keep permanent rooms clean: occupant-bearing scenes are instance-layer by construction (enforced at
  publication by both guardrail and compiler), so permanent `anchor`/`grid` scenes are located only
  and never accumulate spawned entities.
- Enforce §7.2's anti-hallucination rule by construction: requirements carry only registry keys;
  every numeric stat comes from the lore tables; occupant class lineage is selected only from
  `SCENE_OCCUPANT_PROTOTYPE_WHITELIST`; anything else is rejected before a spawn.
- Register the spawn requirements at the compile boundary (`register_generated_quest` →
  `scene_requirements_for`) inside the same all-or-nothing publication, folding them into the
  definition content digest and the equal/conflict preflight so equal scenes dedupe and different
  scenes can never overwrite each other.
- Extend `NPCTier` with `race_key`/`static_tier_key` so NPC stats resolve deterministically from
  lore (no duplicated balance constants in the deterministic core).
- Provide the composition root `server/ai_director_service.py::request_generated_quest(client=None,
  *, context)` so a generated quest's offer reaches the guild board, degrading to a context-fitting
  template quest offline and never resolving to an unregistered definition or `None`.
- Add one instance-layer bound-target template so the offline path produces a SceneBuilder-
  materializable quest and the offline loop exercises the instance scene path end to end.
- Provide minimal deterministic triggers — `進入`/`enter` (materialize and enter the current stage's
  instance scene) and `guild request`/`guild 委託` (request a generated quest) — and prove the full
  offline loop (request → accept → materialize → fight → turn in) with no LLM and no generative state
  mutation.
- Keep both repository contract tests (AI transport boundary + deterministic-path ban) green with no
  edits, and keep every new test offline (`EvenniaTest` + `FakeLLMClient`).

**Non-Goals:**

- Adding any LLM call to SceneBuilder. The `scene_builder` profile layer already exists in
  `world/ai/profiles.py` as a forward-declared seam; this change leaves `profiles.py` and the
  `scene_builder` profile untouched.
- Cross-restart persistence of generated content. Like change 20's `QUEST_DEFINITION_REGISTRY` and
  `GUILD_OFFER_REGISTRY`, generated quests and their scene requirements are process-local: a server
  restart loses generated offers and surfaces accepted generated-quest records as a loud
  `QuestDataError`. A durable generated-quest store re-synced at startup is future work, tracked as an
  Open Question; the hand-written catalog keeps the game playable offline across restarts.
- Modifying the `QuestDefinition` runtime type. Spawn requirements stay out of
  `world/quests/definitions.py` (whose contract `quest-blueprint` pins); they are registered in a
  compile-owned side registry instead.
- Spawning scene occupants into permanent rooms or into the wilderness layer; the former is rejected
  at publication and the compiler already rejects `layer: "wilderness"`.
- Rebuilding the guild board, quest list, or exploration menus; change 16 already provides
  `guild list/accept/log/show/abandon/turnin`, and change 23 owns the WebClient exploration menus.
- Changing `world/maps/instance.py`'s whitelist; instance scenes keep using the reserved
  `instance_room` entry, so the `instance-spawn` spec's "a future change (change 21) may extend it"
  reservation is honored by *not* extending it.
- Backward-compatibility adapters or persisted-data migrations; the project is unreleased.
- Per-room scene art or portraits; change 22 owns the art queue, and SceneBuilder only sets the
  `scene_archetype` attribute change 22 reads.

## Decisions

### D1. SceneBuilder lives in `world/quests/`, not `world/ai/` and not `world/maps/`

`world/quests/scene_builder.py` is a deterministic module in the quest-lifecycle package. It consumes
`StageSpawnRequirement` and `scene_requirements_for` (world.quests), spawns rooms through
`world.maps.instance.spawn_instance_room` (world.maps), and binds through `world.quests.binding`
(world.quests). `world/maps` does not import `world.quests` in production and `world/quests` does not
import `world.maps`, so there is no cycle.

Rationale against the alternatives:

- *world/ai/* — banned: it spawns and binds, i.e. it applies state, which `world/ai/` never does.
  This is also why the design document is amended (see Context): the §3.1 generative listing described
  a layer that cannot legally exist under the single-writer invariant.
- *world/maps/* — the room lifecycle primitive (`spawn_instance_room`) already lives there, but the
  materializer is driven by quest stage requirements and ends in a quest binding; co-locating it with
  quest lifecycle keeps "which quest stage materializes which scene" with the quests it serves. The
  room primitive stays the world/maps-owned API.
- *A new top-level package* — the design §3.2 directory layout reserves no such package, and
  `world/quests/` is the explicit deterministic home for quest-stage behavior.

### D2. Anti-hallucination by construction: keys in, lore numbers out, class lineage from a whitelist

The registered `StageSpawnRequirement` carries only registry keys (archetype, tier, anchor, layer)
and free-text scene sentences — no stats, no typeclass, no `prototype_parent`. SceneBuilder:

1. Re-validates every key against the immutable registries and rejects an unknown key with a named
   `SceneBuilderError` before any spawn (defense in depth; the guardrail and compiler already checked
   the same keys once).
2. Derives every stored stat from `world.rules.traits.build_initial_traits(race_key,
   tier=static_tier_key)` for NPC role tiers (D3) and `build_initial_traits_for_monster_tier(tier,
   "floor")` for monster tiers. There is no path by which a proposal number reaches a stored trait.
3. Builds each occupant prototype as `{"prototype_parent": <whitelisted key>, "key": <deterministic
   name>}` and validates it against `SCENE_OCCUPANT_PROTOTYPE_WHITELIST` before `spawner.spawn()`,
   mirroring `world/maps/instance.py::_validate_prototype_parent` (which also rejects an explicit
   `typeclass` override so the whitelist gates the actually-spawned type).

`world/prototypes.py` gains two module prototypes so the whitelist contains real prototype keys, not
bare typeclass paths:

```python
SCENE_NPC = {"typeclass": "typeclasses.npcs.NPC", "prototype_key": "scene_npc",
             "desc": "A scene occupant (scene-builder)."}
SCENE_MONSTER = {"typeclass": "typeclasses.monsters.Monster", "prototype_key": "scene_monster",
                 "desc": "A scene monster (scene-builder)."}
```

`SCENE_OCCUPANT_PROTOTYPE_WHITELIST: tuple[str, ...] = ("scene_npc", "scene_monster")` lives beside
the builder in `world/quests/scene_builder.py` (the instance-room whitelist stays in world/maps, which
owns rooms; the occupant whitelist is scene content owned by the materializer).

Alternative considered: letting the proposal carry an optional `typeclass`/`stats` block for
flexibility. Rejected — it would reopen the exact "LLM writes 99999 HP" hole §7.2 closes.

### D3. NPC role tiers resolve deterministic physical stats through the lore registries

`NPCTier` gains two frozen fields, `race_key: str` and `static_tier_key: str`, naming entries of
`RACE_REGISTRY` and `STATIC_TIER_REGISTRY` (the static tier must belong to the named race, locked by
a registry test). SceneBuilder derives an NPC's trait config from
`build_initial_traits(race_key, tier=static_tier_key)` and sets `magic_level` to the race's
`starting_magic_level`. Representative content (tunable in lore, locked by tests): `civilian` →
`human_commoner`, `guard`/`adventurer`/`bandit` → `human_adventurer`, `knight` → `human_elite`,
`merchant`/`mage`/`noble`/`priest` → `human_commoner` (mage/priest derive their magic level from the
race starting value). Numbers stay in lore; the builder reads registry values and never duplicates
constants.

Alternative considered: a private mapping dict inside `world/quests/scene_builder.py`. Rejected —
that would duplicate balance constants and violate the "consumers read registry values" invariant;
the mapping is game content and belongs in the immutable lore registry.

### D4. Spawn requirements register at the compile boundary, not on `QuestDefinition`

`CompiledQuest.stage_requirements` is transient. Because materialization is lazy (§7.2), the
requirements must be reachable at arrival time from the accepted record's `definition_key`.
`world/quests/compile.py` gains a process-local `SCENE_REQUIREMENT_REGISTRY: dict[str,
tuple[StageSpawnRequirement, ...]]`:

- `register_generated_quest(compiled)` writes `SCENE_REQUIREMENT_REGISTRY[definition.key] =
  compiled.stage_requirements` as part of the existing all-or-nothing publication, rolled back with
  the definition and offer on any failure.
- `scene_requirements_for(definition_key) -> tuple[StageSpawnRequirement, ...]` returns the entry or
  an empty tuple for keys that were never compiled (hand-written catalog quests).

**The requirement entry is part of the definition's identity.** The `QuestDefinition.key` content
digest (`_definition_key`) now hashes the canonical runtime definition serialization **plus** the
canonical serialization of the compiled stage requirements. Two blueprints with identical runtime
stages but different scenes (archetype, `anchor_near`, `scene_sentence`, `npc_reqs`) therefore get
different keys and can never overwrite each other's requirements; identical content (including scenes)
stays idempotent. `register_generated_quest`'s preflight checks all three registries — definition,
offer, requirements — for equal/conflict before writing any of them, and rolls all three back
together on any failure, so a generated definition is never left registered without its offer or its
requirements.

**Lifetime is explicit.** These are process-local registries, exactly like change 20's own. A server
restart drops generated definitions, offers, and requirements; accepted generated-quest records then
fail loudly (`QuestDataError`, missing definition) rather than corrupting silently. Cross-restart
durability of generated content is deliberately out of scope (Open Question / Non-Goal).

The `QuestDefinition` runtime type is untouched, so the `quest-blueprint` contract is unchanged and
hand-written offline quests (which use permanent content and need no scene) are naturally
distinguished from generated ones by having no requirement entry.

Alternative considered: adding a `scene_requirements` field to `QuestDefinition`. Rejected — it
modifies the pinned runtime type and forces every hand-written definition to carry an empty tuple,
mixing scene-spawn data into the immutable definition contract.

### D5. Occupant-bearing scenes are instance-layer; permanent scenes are located only

The rubber-duck review surfaced two lifecycle holes. First: occupants spawned into permanent rooms
(`register_owned_entity` only despawns on `InstanceRoom` reclaim) would accumulate across generated
quests with no cleanup. Rather than inventing a per-permanent-room despawn lifecycle, this design
**closes the hole at publication**: a stage that declares any `npc_req` MUST use
`location_req.layer: "instance"`. The rule lives in **both** the `scenario_director` guardrail
semantic validators and the deterministic compiler (one shared rule set, locked by the
shared-contract test), so an anchor/grid occupant-bearing quest can never be published. Second:
binding an ESCORT's protected entities into the destination instance room would auto-complete the
escort on entry (`observe_room_entry` requires every protected entity to be present in the bound
room). ESCORT stages are therefore restricted to permanent (`anchor`/`grid`) destinations — never
`instance`, never `npc_reqs` — so the materializer only locates the escort's destination room and
never spawns or binds protected entities.

Consequences:

- Every spawned scene occupant lives in a reclaimable `InstanceRoom`; the quest pin holds the room
  while the stage is active, and TTL reclamation despawns owned occupants after the stage is done.
  No permanent-room cleanup is needed because none is possible.
- `materialize_stage` for a permanent `anchor`/`grid` destination only locates the existing room —
  it never spawns and never binds. A permanent monster-tier hunt remains completable through the
  natural wilderness population (the change-20 template's own flow), and a permanent REACH stage is
  advanced by the room observer. An ESCORT stage is located only, so its protected entities are never
  auto-spawned into the destination and an escort can never complete merely by entering.
- `bind_stage_runtime`'s `InstanceRoom`-only `room` requirement is always satisfiable, because the
  only scenes SceneBuilder binds are instance scenes.

Related rules (same shared validation): a DEFEAT stage with `npc_reqs` must have `quantity <=
len(npc_reqs)`, because bound-target progress counts distinct bound defeats and a larger quantity
would be uncompletable. And `anchor_near`, when present, must name a placed anchor in
`ANCHOR_PLACEMENT_REGISTRY` (it selects the origin room SceneBuilder attaches to).

### D6. `materialize_stage` semantics: destination, occupants, binding, atomicity, idempotency

`materialize_stage(actor, quest_id, *, origin_room=None)`:

1. **Resolve.** `read_records(actor)` → `find_record`; require `IN_PROGRESS` with the current stage
   still matching its definition; read the persisted `scene_requirements_for(definition_key)` entry
   for the current stage. A stage with no registered requirement (hand-written quest) raises
   `SceneBuilderNoRequirements`.
2. **Destination.** For `BOUND_INSTANCE`: call `spawn_instance_room(origin_room, {"prototype_parent":
   "instance_room"}, exit_key=..., return_key=..., named=True)`. `origin_room` must be a real,
   non-`InstanceRoom` room (reusing the nested-instance rejection); when the stage declares an
   `anchor_near`, the origin room must be that anchor's `AnchorRoom` (a `SceneBuilderLocationError`
   otherwise). For `ANCHOR`/`GRID`: resolve the existing room and return it without spawning or
   binding (D5).
3. **Scene metadata.** Set `room.scene_archetype = requirement.archetype` (change 22's art seam),
   `room.db.desc` from `requirement.scene_sentence` or the archetype registry's `scene_sentence`.
   Instance scenes spawn with `named=True` so a scene the player actually enters can promote to
   permanent (D3's promotion rule) after its TTL.
4. **Occupants.** One `scene_npc` per `npc_req` entry (key derived deterministically from role/tier,
   stats from D3, `disposition` copied to `db.disposition` for dialogue flavor); for a monster-tier
   DEFEAT stage, `objective.quantity` `scene_monster` occupants (stats from the tier floor,
   `threat_tier` set). Every occupant is registered through
   `world.maps.instance.register_owned_entity(room, occupant)` so reclamation despawns them. (For a
   monster-tier DEFEAT, the planner counts defeated targets by tier, so the spawned monsters are bound
   as objective targets for bookkeeping but any same-tier natural monster would also satisfy the
   objective — harmless, and documented in the tests.)
5. **Bind.** Map occupants to `objective_targets` for DEFEAT stages (a monster-tier DEFEAT binds its
   spawned monsters for bookkeeping; a bound-target DEFEAT binds its NPCs). REACH/ACQUIRE occupants
   are flavor only (owned, not bound). ESCORT stages are permanent destinations located only (D5), so
   `_bind_stage` never receives an ESCORT stage and never binds protected entities. Call
   `bind_stage_runtime(actor, quest_id, room=room, objective_targets=...)`.
6. **Atomicity.** The room spawn, exit pair, occupants, ownership, and the quest binding compose ONE
   outer `transaction.atomic()`. `spawn_instance_room` and `bind_stage_runtime` each use their own
   inner atomic blocks, which nest as savepoints; no compensation-delete step is needed because the
   whole materialization commits or rolls back together. On any failure the actor's quest log is
   restored to its pre-operation value (the same snapshot/restore the transitions layer uses), so the
   in-process Evennia attribute cache can never observe a stale binding after the database rolled
   back. The player's move into the scene happens only after the call returns (post-commit), in the
   command layer.
7. **Idempotency.** If the record is already bound (`stage_room_id` set or targets set), re-validate
   that the bound room still exists as an `InstanceRoom`, return the existing binding, and spawn
   nothing — the reconnect/re-entry path, and `bind_stage_runtime` already treats identical rebinding
   as a no-op.

Named errors: `SceneBuilderError` base with `SceneBuilderNotActive`, `SceneBuilderNoRequirements`,
`SceneBuilderLocationError`, `SceneBuilderSpawnError`.

### D7. The composition root lives in `server/ai_director_service.py`

`request_generated_quest(client=None, *, context)` is the only production caller of
`generate_quest_blueprint`. It bridges generative to deterministic:

```python
@defer.inlineCallbacks
def request_generated_quest(client=None, *, context):
    if client is None:
        # deferred imports: never bind world.ai at module import time
        from world.ai.client import OpenAICompatClient
        from world.ai.profiles import get_profile
        profile = get_profile("scenario_director")
        if profile.enabled:
            client = OpenAICompatClient(profile)
    blueprint = yield generate_quest_blueprint(client, context=context)
    compiled = compile_quest_blueprint(blueprint.to_payload())
    register_generated_quest(compiled)
    return compiled
```

`server/` is outside both contract-scan roots: the deterministic-path ban covers
`world/rules|maps|quests|commands` and the transport boundary covers `world/ai/`, so this one module
may legally import both `world.ai.scenario_director` and `world.quests.compile`. The `world.ai`
imports are deferred into the call path for the same reason the narrator/dialogue registration seams
defer them: `world.ai.guardrail` captures the logger at import time, and importing it at module scope
would bind a `None` logger during settings/cmdset load. A cold-import test locks this.

The client defaults to an `OpenAICompatClient` built from the `scenario_director` profile **only when
that profile is enabled**; when the profile is disabled the service passes a stub so
`generate_quest_blueprint`'s required-client gate is satisfied while the degrade path (which never
touches the client) produces the template draw. Tests always inject `FakeLLMClient`. On any degrade
trigger the call resolves to a context-fitting template quest through the director, which then
compiles and registers like any other proposal — so the offline loop is the same code path as the LLM
path.

### D8. The triggers are two minimal deterministic commands

- `commands/scene.py::CmdEnterScene` (`進入`/`enter`): selects the caller's **first enterable**
  active instance stage (the first active quest, in log order, whose current stage carries a
  registered `BOUND_INSTANCE` spawn requirement whose declared `anchor_near`, if any, matches the
  caller's current location — unless the caller is already inside the bound room), calls
  `materialize_stage(self.caller, quest_id, origin_room=self.caller.location)`, and then, after the
  materialization commits, moves the caller into the spawned instance room through the plain exit the
  builder created — ordinary traversal, which charges the standard `move` clock cost and records map
  knowledge through the shared `typeclasses.exits.Exit` machinery. The command verifies the exit's
  `traverse` access before traversing (calling `at_traverse` directly bypasses the exit command's
  lock check) and reports success only after confirming `caller.location` is the spawned room, so a
  vetoed or failed move is never reported as success. For a permanent destination, a stage with no
  requirements, or a wrong-anchor stage, the command reports that nothing needs entering
  (side-effect-free). Every rejection path is a named, side-effect-free message.
- `commands/guild.py::CmdGuildRequest` (`guild request`/`guild 委託`): requires a valid guild
  registration (reuses `_GuildCommandBase.resolve_staff()` for the branch, reads `actor.guild_rank`),
  builds the director request context (`requested_type` from an optional argument, defaulting to
  討伐; `allowed_rank` = the player's rank, which the fitness gate treats as the maximum allowed;
  `issuer_branch` = the local branch; `anchor` = the caller's room's anchor key), calls
  `request_generated_quest`, and reports the posted offer's definition key (the existing
  `guild list`/`guild accept` flow then takes it). On the live path the request may not resolve
  synchronously: the command tracks one pending request per caller (a retry while pending is
  rejected instead of double-submitting) and reports the posted offer or the named rejection when the
  Deferred fires. The command constrains the context to the branch and anchor the template pool
  actually covers; if no template fits (offline, exotic context) the named
  `ScenarioDirectorTemplateError` is surfaced to the player rather than fabricating a quest.

Neither command imports a `world.ai` module, so the deterministic-path ban stays green; the
composition service is reached through `server.ai_director_service` (a module name with no banned
fragment).

### D9. The template pool gains one instance-layer scene

Change 20 deliberately omitted instance-layer templates because an instance scene could not be
completed before SceneBuilder existed. Change 21 supplies the materializer, so `director_templates.py`
gains one instance-layer template (e.g. an F-rank bound-target DEFEAT at `forest_path`, anchored near
`capital_altoria`). This does two things:

- A disabled-profile `guild request` can resolve to a quest whose scene SceneBuilder actually builds,
  so the offline loop exercises `spawn_instance_room`, the exit pair, the room pin, and re-entry — not
  just permanent-room static content.
- The milestone "AI Director is live" is verifiable without any LLM: request → accept → materialize →
  fight → turn in completes deterministically.

The new template must satisfy the output schema, every semantic validator (including the D5
scene-bound rules), and compile/register with a bound instance stage.

### D10. The `scene_builder` LLM profile stays a forward-declared seam

`world/ai/profiles.py` already names `scene_builder` in `LAYER_NAMES`, but no `scene_builder` layer
hooks are registered in the guardrail and nothing calls it. This change adds no LLM call and does not
edit `profiles.py`: the deterministic SceneBuilder is the whole §7.2 implementation. Keeping the
profile registered preserves the setting surface for a future generative scene-flavor or prompt-agent
layer (change 22's art worker contract is the natural consumer) without shipping dead code. The
guardrail has no `scene_builder` registration, so there is no half-registered seam to maintain.

## Risks / Trade-offs

- [Generated content is process-local and lost on server restart] → D4/Non-Goals: this is change 20's
  own property, not new; accepted records fail loudly (`QuestDataError`) rather than corrupting; the
  hand-written catalog keeps the game playable offline across restarts; a durable generated-quest
  store is an explicit Open Question.
- [Instance scenes promote to permanent, growing the database with generated content] → D6: scenes
  spawn `named=True` and promote only after a `PlayerCharacter` actually enters (`interacted`), so
  only visited scenes persist; unvisited ones reclaim after the TTL, and the quest pin holds the room
  only while the stage is active. Bounding this further is content policy, tracked for change 22/art.
- [NPC stat derivation is content that could feel off (e.g. a `mage` with mostly physical stats)] →
  D3: all numbers live in the lore registries and are locked by derivation tests; tuning a tier edits
  lore, not code. `magic_level` uses the race starting value so mage/priest tiers are non-zero.
- [Bound DEFEAT quantity could exceed the number of targets] → D5: both the guardrail and the compiler
  reject `quantity > len(npc_reqs)` before publication, so a bound-target objective is always
  satisfiable.
- [Occupant-bearing scenes at permanent rooms would pollute the shared map] → D5: publication rejects
  `npc_reqs`/ESCORT/bound stages outside `instance`, and `materialize_stage` never spawns for
  permanent destinations, so permanent rooms can never accumulate scene entities; scene occupants are
  always reclaimed with their instance.
- [`request_generated_quest` with a disabled profile still needs a non-None client] → D7: the service
  constructs the real client only when the profile is enabled and otherwise passes a stub; the
  director hits the degrade path before any transport work. The offline end-to-end test locks zero
  client calls.
- [Importing `server.ai_director_service` at cmdset load could bind a `None` logger] → D7: every
  `world.ai` import is deferred into the call path; a cold-import test locks the ordering, matching
  the narrator/dialogue registration seams.
- [Occupant spawning through `spawner.spawn()` could be bypassed by a forged prototype] → D2: the
  whitelist check runs before `spawn()`, rejects an explicit `typeclass` override, and the builder
  constructs the prototype itself from whitelisted parents; a spawned non-NPC/non-Monster object is a
  named `SceneBuilderSpawnError`, mirroring `spawn_instance_room`'s defense-in-depth branch.
- [Two triggers touch the deterministic-path ban] → D8: both commands import only deterministic
  modules plus the `server.ai_director_service` name (no banned fragment); the repository contract
  test scans `commands/` and stays green, locked by a test.
- [The composition root in `server/` is an unusual home for game logic] → D7: `server/` is the Evennia
  application seam that already imports `world.ai` at startup; the module is a thin bridge with no
  rules of its own, and it is the only legal place under both contract constraints for a module that
  both asks the director and posts to the board.
- [A monster-tier DEFEAT in an instance scene is bound but the planner counts by tier] → D6: the bound
  set is bookkeeping; any same-tier kill advances the objective, which in an instance is only the
  scene's own monsters. Documented in tests; not a progression bug.
- [`guild request` offline needs a matching template or it errbacks] → D8/D9: the context is
  constrained to the branch/anchor/ranks the pool covers, an instance-layer template is added, and an
  unmatched context surfaces the named template error to the player instead of fabricating a quest.
- [Rolling the requirement entry into the digest changes existing generated keys] → D4: keys are
  content digests with no persisted meaning (generated content is process-local), and tests assert
  determinism, not specific values.

## Migration Plan

1. Extend `world/lore/npc_tiers.py` `NPCTier` with `race_key`/`static_tier_key` and lock the mapping
   with a registry test (`world/lore/tests/test_npc_tiers.py`).
2. Add `SCENE_NPC` / `SCENE_MONSTER` module prototypes to `world/prototypes.py`.
3. Extend the scenario-director layer: two new semantic validators (occupant stages are instance-only;
   bound DEFEAT quantity ≤ `npc_reqs` count; `anchor_near` is a placed anchor) in
   `world/ai/scenario_director.py`, and the same checks in `world/quests/compile.py`; fold the
   compiled stage requirements into `_definition_key` and the `register_generated_quest` preflight/
   rollback; add `SCENE_REQUIREMENT_REGISTRY` + `scene_requirements_for`. Add tests under
   `world/quests/tests/test_compile.py` and `world/ai/tests/test_scenario_director.py`.
4. Add one instance-layer bound-target template to `world/ai/director_templates.py` with validation,
   compile, and offline-draw tests.
5. Add `world/quests/scene_builder.py` (whitelist, requirement resolution, destination resolution,
   occupant spawning with lore-derived stats, scene metadata, one outer atomic binding block, named
   errors) with `EvenniaTest` tests under `world/quests/tests/test_scene_builder.py`, including
   rollback and re-entry cases.
6. Add `server/ai_director_service.py` (composition root with deferred `world.ai` imports) with
   `FakeLLMClient` tests under `server/conf/tests/test_ai_director_service.py`.
7. Add `commands/scene.py::CmdEnterScene` and `commands/guild.py::CmdGuildRequest`, register both in
   `commands/default_cmdsets.py`, and add an `EvenniaTest` offline end-to-end loop test covering
   request → accept → materialize → fight → turn in with zero LLM calls.
8. Verify: the focused `world.quests`, `world.ai`, `world.lore`, and `server.conf` suites; the
   repository-wide contract tests; the full Evennia suite; `compileall`; `tools.spec_traceability
   check`; `openspec validate scene-builder --strict` and `openspec validate --all --strict`;
   `git diff --check`.

No persisted-game-data migration applies: the change stores no new player-facing state (spawn
requirements are process-local registry data; scenes are ordinary Evennia objects with existing
lifetimes). Rollback is a clean removal of the new modules, the prototype entries, the registry
extension, the new validators, the instance-layer template, and the two commands; the compile-boundary
registration is additive and harmless to existing hand-written quests (they read back empty
requirements).

## Open Questions

- Whether generated quests should survive server restarts (a durable, startup-re-synced generated-quest
  store covering definition + offer + requirements together). This change explicitly scopes it out and
  documents the process-local lifetime; the design doc milestone does not require it.
- The exact deterministic exit keys for spawned instance scenes (e.g. derived from the archetype's
  display name) are left to the implementation tasks; they must be stable so re-entry and the `進入`
  command agree.
