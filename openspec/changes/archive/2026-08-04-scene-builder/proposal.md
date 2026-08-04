## Why

Change 20 shipped the ScenarioDirector's validated proposal seam — `QuestBlueprint` →
`compile_quest_blueprint` → a frozen `CompiledQuest` carrying per-stage `StageSpawnRequirement` plain
data — but a generated quest is still not playable: nothing materializes those spawn requirements into
a real room and occupants, and nothing posts a generated quest onto the guild board. Change 21 is the
last critical-path change (`15 → 20 → 21`); after it the "AI Director is live" milestone holds. Design
§7.2 fixes the one rule that makes this safe: **the LLM never chooses numbers** — SceneBuilder maps
tier keys to lore-table stats and only whitelisted prototype parents reach the spawner.

> **Design-document amendment (this change).** The approved design §3.1 lists `SceneBuilder` in the
> generative `world/ai/` layer and §7.5 gives it a generic-room degradation row, but §7.2's
> anti-hallucination rule and change 20's resolution both require the materializer to be deterministic
> — it spawns, so it cannot live under `world/ai/` (which never applies a state change). This change
> explicitly amends §3.1 and §7.5: **SceneBuilder is the deterministic requirements→prototype→spawn
> compiler in `world/quests/`**; the generative role is carried by the ScenarioDirector's `QuestBlueprint`,
> which already contains the scene requirements; and §7.5's "SceneBuilder → generic room template"
> degradation row becomes "a named, side-effect-free rejection when a scene cannot materialize" (a
> deterministic layer needs no LLM degradation). The forward-declared `scene_builder` LLM profile stays
> registered and unused as a seam for a future generative scene-flavor layer.

## What Changes

- Add `world/quests/scene_builder.py`, the deterministic requirements→prototype→spawn layer.
  `materialize_stage(actor, quest_id, *, origin_room=None)` resolves the player's current active
  stage's registered spawn requirements. For an `instance`-layer destination it spawns one
  `InstanceRoom` through `world.maps.instance.spawn_instance_room` (whitelisted `instance_room`
  prototype) with a plain exit pair, sets `scene_archetype`, `named`, and the scene description,
  spawns occupants (NPCs per `npc_reqs`, monsters per a monster-tier DEFEAT), registers them as owned
  entities, and binds the room plus objective targets through `bind_stage_runtime` (ESCORT stages are
  permanent destinations located only — the materializer never spawns or binds an escort's protected
  entities, so an ESCORT can never auto-complete on entry). For a permanent `anchor`/`grid`
  destination it only locates the existing room — permanent layers are never given spawned occupants
  (they stay clean, and natural wilderness population covers monster-tier hunts), so no cleanup
  lifecycle is needed there. **Atomicity:** destination, metadata, occupants, ownership, and binding
  compose ONE outer `transaction.atomic()` (inner blocks nest as savepoints); a failure rolls
  everything back and restores the actor's quest-log state so no stale binding is observable, and the
  player's move into the scene happens only after commit. Re-materialization of an already-bound
  stage is idempotent (validated to still be an `InstanceRoom`) and spawns nothing. Named
  `SceneBuilderError` variants replace half-written scenes.
- **Enforce §7.2's anti-hallucination rule by construction.** SceneBuilder accepts only registry keys
  (archetype, NPC tier, monster tier, anchor, layer) from the registered requirements: no numeric
  stat, no typeclass path, and no `prototype_parent` ever travels in the proposal. Every stored stat
  comes from the immutable lore tables (`build_initial_traits` for NPC tiers,
  `build_initial_traits_for_monster_tier` for monster tiers), and occupant class lineage is selected
  only from a new `SCENE_OCCUPANT_PROTOTYPE_WHITELIST`. A requirement whose key fails to resolve is
  rejected with a named error before any spawn.
- Extend `world/lore/npc_tiers.py`'s `NPCTier` with `race_key` and `static_tier_key` so a role tier's
  physical stats resolve deterministically from the race/static-tier registries. Numbers stay in
  lore; SceneBuilder reads registry values and never duplicates balance constants. The `scene_builder`
  LLM profile stays a forward-declared seam — this change adds no LLM call.
- **Validate scene-bound stages before publication.** The scenario-director guardrail and the
  deterministic compiler both enforce: a stage with any `npc_reqs` MUST use
  `location_req.layer: "instance"` (occupant-bearing scenes are always reclaimable instances, never
  permanent rooms); an ESCORT stage MUST use a permanent (`anchor`/`grid`) destination — never
  `instance` and never `npc_reqs` — so the materializer never spawns an escort's protected entities
  into the destination room (which would auto-complete the escort on entry) and never pollutes a
  permanent map; a DEFEAT stage with `npc_reqs` MUST have `quantity <= len(npc_reqs)` so the
  bound-target objective is always satisfiable; and a non-`None` `anchor_near` MUST name a placed
  anchor in `ANCHOR_PLACEMENT_REGISTRY`. The guardrail and the compiler share one rule set, so the two
  sides cannot drift.
- **Register spawn requirements at the compile boundary** so a scene can be built on arrival, not
  when the quest was accepted: `register_generated_quest()` additionally stores the compiled
  `stage_requirements` under the definition key (read via a new `scene_requirements_for(definition_key)`),
  inside the same all-or-nothing operation that registers definition and offer. The definition
  content digest now covers the canonical spawn requirements too, so two blueprints with identical
  runtime stages but different scenes get different keys and can never silently overwrite each other;
  the publication preflight treats a requirements mismatch as a conflict and rolls the whole write
  back. Hand-written catalog quests (never compiled) read back an empty tuple.
  > **Note on lifetime.** Like `QUEST_DEFINITION_REGISTRY` and `GUILD_OFFER_REGISTRY` (change 20),
  > these are process-local registries: generated quests and their scene requirements do not survive a
  > server restart. A restart loses generated offers and surfaces accepted generated-quest records as
  > a loud `QuestDataError` (missing definition), never a silent corruption. Cross-restart persistence
  > of generated content is explicitly out of scope and tracked as an open question; the hand-written
  > catalog keeps the game playable offline across restarts.
- Add the composition root `server/ai_director_service.py::request_generated_quest(client=None, *,
  context)` that bridges the director's guarded proposal to the deterministic compile boundary
  (`generate_quest_blueprint` → `compile_quest_blueprint` → `register_generated_quest`) so a generated
  quest's offer reaches the guild board. It accepts an injected client, defaults to an
  `OpenAICompatClient` built from the `scenario_director` profile only when that profile is enabled,
  defers every `world.ai` import to the call path (so importing the module at startup cannot bind a
  `None` logger, the same rule the narrator/dialogue registration seams follow), resolves to a
  context-fitting template quest when offline, and never resolves to an unregistered definition or
  `None`.
- Add one **instance-layer bound-target template** to `world/ai/director_templates.py` so the offline
  `guild request` path can produce a SceneBuilder-materializable quest and the offline loop exercises
  the instance scene path end to end. (Change 20 deliberately omitted instance templates because
  SceneBuilder did not exist; this change supplies the missing materializer.)
- Add minimal deterministic player-facing triggers: a `guild request`/`guild 委託` command that asks
  the composition root for a generated quest and reports the posted offer (rejecting a duplicate
  submission while a request is in flight), and an `進入`/`enter` command that materializes and enters
  the caller's first enterable instance scene — matching the current anchor — after verifying the
  created plain exit's traverse access and confirming the caller actually reaches the room. Both live
  in `commands/` and import only deterministic modules or the composition service — never `world.ai` —
  so the deterministic-path ban stays green.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased. Full
  guild-board menu polish and the WebClient exploration menus remain change 23's.

## Capabilities

### New Capabilities

- `scene-builder`: The deterministic materialization layer that turns one stage's registered spawn
  requirements into a real scene — instance room, lore-statted occupants, scene metadata, and atomic
  `bind_stage_runtime` binding — under §7.2's anti-hallucination rule (keys in, numbers/class-lineage
  never), plus the composition root that posts generated quests to the guild board, the instance-layer
  offline template, and the minimal commands that trigger generation and scene entry.

### Modified Capabilities

- `scenario-director`: The registries requirement gains `NPCTier.race_key`/`static_tier_key`; the
  deterministic compile boundary's `register_generated_quest()` also registers the compiled per-stage
  spawn requirements (via `scene_requirements_for`) in the same all-or-nothing publication, folds them
  into the definition content digest and preflight; and new scene-bound validation rules (occupant
  stages are instance-only, bound DEFEAT quantity is bounded, `anchor_near` is a placed anchor) are
  enforced by both the guardrail semantic validators and the compiler.

## Impact

- Adds `world/quests/scene_builder.py` (whitelist, requirement resolution, room/occupant spawning,
  atomic binding, `SceneBuilderError` variants) and package-local tests under
  `world/quests/tests/test_scene_builder.py`.
- Adds `server/ai_director_service.py` (the composition root bridging `world.ai.scenario_director`
  and `world.quests.compile`; `world.ai` imports deferred to the call path) with tests under
  `server/conf/tests/test_ai_director_service.py`.
- Adds `commands/scene.py` (`進入`/`enter`) and a `CmdGuildRequest` in `commands/guild.py`
  (`guild request`/`guild 委託`), both registered in `commands/default_cmdsets.py`.
- Modifies `world/quests/compile.py` (requirement registration + `scene_requirements_for`; digest and
  preflight over requirements; anchor_near validation; instance-only + quantity constraints),
  `world/ai/scenario_director.py` (two new semantic validators), `world/ai/director_templates.py` (one
  instance-layer template), `world/lore/npc_tiers.py` (two new `NPCTier` fields), and
  `world/prototypes.py` (new `SCENE_NPC` / `SCENE_MONSTER` module prototypes).
- Consumes change-20 seams unchanged: `CompiledQuest.stage_requirements`, `StageSpawnRequirement`,
  `compile_quest_blueprint`, `register_generated_quest`; change-14 `spawn_instance_room` /
  `INSTANCE_PROTOTYPE_WHITELIST` / `register_owned_entity`; change-15 `bind_stage_runtime`; change-17
  `get_profile` / `OpenAICompatClient` / `FakeLLMClient`; and the immutable lore registries.
- Preserves both repository contract tests unchanged: the SceneBuilder lives under `world/quests/`
  (deterministic-path ban green, no `world.ai` fragment), `server/ai_director_service.py` is outside
  both scanned roots, and no `world/ai` module imports a state writer.
- No settings-schema, container, or dependency change; `world/ai/profiles.py` is untouched (the
  `scene_builder` layer remains a forward-declared profile).
