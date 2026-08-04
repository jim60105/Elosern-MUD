## 1. NPC tier stat mapping in lore

- [x] 1.1 Extend `world/lore/npc_tiers.py` `NPCTier` with frozen `race_key: str` and
  `static_tier_key: str` fields and populate every registry entry so each role tier maps to a
  `STATIC_TIER_REGISTRY` entry belonging to its `RACE_REGISTRY` race (e.g. `civilian` →
  `human_commoner`, `guard`/`adventurer`/`bandit` → `human_adventurer`, `knight` → `human_elite`,
  `merchant`/`mage`/`noble`/`priest` → `human_commoner`)
- [x] 1.2 Add registry tests under `world/lore/tests/test_npc_tiers.py`: every tier's keys resolve in
  `RACE_REGISTRY`/`STATIC_TIER_REGISTRY` with the static tier belonging to the named race; the
  registry stays frozen and non-empty

## 2. Scene occupant prototypes and whitelist

- [x] 2.1 Add `SCENE_NPC` (`typeclass: "typeclasses.npcs.NPC"`, `prototype_key: "scene_npc"`) and
  `SCENE_MONSTER` (`typeclass: "typeclasses.monsters.Monster"`, `prototype_key: "scene_monster"`)
  module prototypes to `world/prototypes.py`
- [x] 2.2 Add `SCENE_OCCUPANT_PROTOTYPE_WHITELIST: tuple[str, ...] = ("scene_npc", "scene_monster")`
  in `world/quests/scene_builder.py` plus a validation helper mirroring
  `world.maps.instance._validate_prototype_parent` (parent in whitelist and no explicit `typeclass`
  override), and test that both prototype keys resolve and the whitelist rejects anything else

## 3. Scene-bound validation and requirement registration at the compile boundary

- [x] 3.1 Add the scene-bound semantic validators to `world/ai/scenario_director.py`: a stage with any
  `npc_req` must use `location_req.layer == "instance"`; an ESCORT stage must use a permanent
  (`anchor`/`grid`) destination — never `instance`, never `npc_reqs`; a DEFEAT stage with `npc_reqs`
  must have `quantity <= len(npc_reqs)`; a non-`None` `anchor_near` must be in
  `ANCHOR_PLACEMENT_REGISTRY` — and enforce the identical rules in `world/quests/compile.py`
  (`QuestCompileError`), with a shared-contract test that a guardrail-valid payload compiles and an
  un-guardrail-validated scene-bound violation is rejected deterministically
- [x] 3.2 Extend `world/quests/compile.py` with `SCENE_REQUIREMENT_REGISTRY: dict[str,
  tuple[StageSpawnRequirement, ...]]` and `scene_requirements_for(definition_key) -> tuple[
  StageSpawnRequirement, ...]` returning the entry or an empty tuple for keys never compiled
- [x] 3.3 Fold the canonical serialization of the compiled stage requirements into the definition
  content digest (`_definition_key`), so equal scenes yield equal keys and different scenes never
  collide
- [x] 3.4 Make `register_generated_quest` register the compiled `stage_requirements` in the same
  all-or-nothing publication: preflight the definition, offer, and requirement registries'
  equal/conflict states before writing any, and roll all writes (including the requirement entry) back
  together on any failure
- [x] 3.5 Add tests under `world/quests/tests/test_compile.py` and
  `world/ai/tests/test_scenario_director.py`: occupant stages at anchor/grid are rejected by both
  sides; an ESCORT stage at `instance` is rejected by both sides while an ESCORT at a permanent
  destination compiles; bound DEFEAT quantity exceeding `npc_reqs` count is rejected; unknown
  `anchor_near` is rejected; after registration `scene_requirements_for` returns the stage
  requirements; two blueprints differing only in scenes compile to different keys; the
  conflicting-offer rollback path leaves no requirement entry; a hand-written catalog definition
  reads back an empty tuple; double registration remains idempotent with one requirement entry

## 4. SceneBuilder materialization layer

- [x] 4.1 Add `world/quests/scene_builder.py` with the `SceneBuilderError` hierarchy
  (`SceneBuilderNotActive`, `SceneBuilderNoRequirements`, `SceneBuilderLocationError`,
  `SceneBuilderSpawnError`), the occupant whitelist, and `materialize_stage(actor, quest_id, *,
  origin_room=None)`
- [x] 4.2 Implement stage resolution: `read_records` → `find_record`, require `IN_PROGRESS` with the
  current stage still matching, read the persisted `scene_requirements_for(definition_key)` entry for
  the current stage, and raise `SceneBuilderNoRequirements` for a hand-written stage with no entry
- [x] 4.3 Implement destination resolution: for `BOUND_INSTANCE` spawn one `InstanceRoom` via
  `spawn_instance_room` (prototype `{"prototype_parent": "instance_room"}`, plain exit pair,
  `named=True`), validating `origin_room` (not an `InstanceRoom`; an `anchor_near` must match the
  origin's `anchor_key`); for `ANCHOR`/`GRID` locate the existing room, spawn nothing, and bind
  nothing
- [x] 4.4 Implement scene metadata: set `scene_archetype` from the requirement, `db.desc` from the
  requirement's `scene_sentence` or the archetype registry's sentence
- [x] 4.5 Implement occupant spawning (instance scenes only): one `scene_npc` per `npc_req`
  (deterministic key, stats from `build_initial_traits(tier.race_key, tier=tier.static_tier_key)` with
  `magic_level` = `starting_magic_level`, disposition stored), `objective.quantity` `scene_monster`
  for a monster-tier DEFEAT (stats from `build_initial_traits_for_monster_tier(tier, "floor")`,
  `threat_tier` set); register every occupant via `register_owned_entity`
- [x] 4.6 Implement binding: DEFEAT occupants → `objective_targets` (bound and monster-tier alike);
  REACH/ACQUIRE occupants unbound (flavor only); ESCORT stages are permanent destinations located
  only and are never bound through the SceneBuilder; call `bind_stage_runtime` with the resolved room
  and identity set
- [x] 4.7 Implement atomicity and idempotency: the room, exit pair, occupants, ownership, and binding
  compose ONE outer `transaction.atomic()` (inner blocks nest as savepoints) with no compensation
  deletes and with the actor's quest log restored to its pre-operation value on any failure (so no
  stale binding is observable); an already-bound current stage returns the existing binding (re-
  validated to still be an `InstanceRoom`) and spawns nothing
- [x] 4.8 Add `EvenniaTest` tests under `world/quests/tests/test_scene_builder.py`: an instance scene
  is spawned, described, owned, and bound in one operation; a permanent-layer scene is located without
  spawning or binding (including a permanent ESCORT stage); DEFEAT maps occupants to the correct
  binding sets; a mid-spawn failure rolls everything back; a post-bind failure rolls back and leaves
  no stale quest-log binding; re-entry is idempotent; unknown/inactive/no-requirement/mismatched-
  origin requests raise named errors with no state change; spawned occupant stats equal the
  lore-derived values

## 5. Composition root service

- [x] 5.1 Add `server/ai_director_service.py::request_generated_quest(client=None, *, context)` that
  defers every `world.ai` import into the call path, builds a client from the enabled
  `scenario_director` profile (or passes a stub when disabled), yields `generate_quest_blueprint`,
  compiles via `compile_quest_blueprint(blueprint.to_payload())`, registers via
  `register_generated_quest`, and resolves to the registered `CompiledQuest`
- [x] 5.2 Add tests under `server/conf/tests/test_ai_director_service.py` using `FakeLLMClient`: a
  valid fixture resolves to a registered definition + offer + requirements with no state mutation by
  generative code; a disabled profile resolves to a context-fitting template quest with zero client
  calls; a cold import of the module before `evennia._init()` succeeds without binding a `None`
  logger; no test constructs `OpenAICompatClient` or opens a socket

## 6. Instance-layer template, trigger commands, and the offline loop

- [x] 6.1 Add one instance-layer bound-target template to `world/ai/director_templates.py` (e.g. an
  F-rank DEFEAT with `npc_reqs` at `forest_path`, `anchor_near` `capital_altoria`) and test that it
  passes the output schema, every semantic validator (including the scene-bound rules), compiles, and
  registers with a bound instance stage
- [x] 6.2 Add `commands/scene.py::CmdEnterScene` (`進入`/`enter`): select the caller's first
  enterable active instance stage (anchor-matched unless already inside the bound room), call
  `materialize_stage` for it, then after commit move the caller into the spawned room through the
  created plain exit (ordinary traversal, charging the standard move cost and recording map
  knowledge) — verifying the exit's traverse access first and reporting success only after the caller
  actually reaches the room; report permanent/no-requirement/wrong-anchor stages side-effect-free;
  every rejection is a named, side-effect-free message
- [x] 6.3 Add `commands/guild.py::CmdGuildRequest` (`guild request`/`guild 委託`): require a valid
  guild registration, resolve the branch via `_GuildCommandBase.resolve_staff()`, build the director
  request context (requested type defaulting to 討伐, `allowed_rank` from the player's rank,
  `issuer_branch`, `anchor` from the caller's room), call `request_generated_quest`, and report the
  posted offer's definition key (surfacing `ScenarioDirectorTemplateError` when no template fits
  offline); reject a duplicate submission while a live request is in flight
- [x] 6.4 Register both commands in `commands/default_cmdsets.py`
- [x] 6.5 Add an `EvenniaTest` offline end-to-end loop test: disable every `LLM_PROFILES` entry →
  `guild request` posts the instance-layer template quest → `guild accept` takes it → `進入`
  materializes the scene → the bound occupants are defeated → `guild turnin` claims the reward, with
  zero LLM calls and no generative state mutation
- [x] 6.6 Add command tests: the two command sources contain no `world.ai`/`ollama`/`llm_client`
  fragment; `進入` with no active instance stage, from inside the already-bound room, from a
  mismatched origin, or when the only instance quest anchors elsewhere is a named side-effect-free
  rejection; `進入` selects the first enterable instance stage among several; a vetoed traversal is
  not reported as success

## 7. Boundary and contract verification

- [x] 7.1 Verify `world/quests/scene_builder.py` imports no `world.ai` module, no live transport, and
  no `world/ai` state writer, and that the repository-wide AI transport-boundary and
  deterministic-path contract tests pass with no edits
- [x] 7.2 Verify no `world/ai/` production module imports `world.quests.scene_builder` or any other
  state writer
- [x] 7.3 Add a regression test that every scene-builder and service test uses `EvenniaTest` /
  `FakeLLMClient` and never constructs `OpenAICompatClient` or opens a network connection
- [x] 7.4 Add a test asserting the process-local lifetime contract: generated requirements are
  registered only through `register_generated_quest`, and the documentation/risk note that generated
  content does not survive a server restart is accurate (no startup re-sync exists for it)

## 8. Verification

- [x] 8.1 Map every delta-spec scenario to at least one deterministic test and apply
  `covers_requirement` annotations using literal IDs from
  `uv run --locked python -m tools.spec_traceability list` (both the new `scene-builder` requirement
  IDs and the modified/added `scenario-director` IDs)
- [x] 8.2 Run focused tests: `uv run --locked evennia test --settings settings.py
  world.quests.tests.test_scene_builder world.quests.tests.test_compile world.ai.tests.test_scenario_director
  world.lore.tests server.conf.tests commands`, plus the repository-wide contract test
- [x] 8.3 Run `uv run --locked evennia test --settings settings.py .` (or the affected domain suites)
- [x] 8.4 Run `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] 8.5 Run `uv run --locked python -m tools.spec_traceability check`
- [x] 8.6 Run `openspec validate scene-builder --strict` and `openspec validate --all --strict`
- [x] 8.7 Run `git diff --check` and confirm only planning artifacts are changed by this proposal
