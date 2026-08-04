## Why

The change-16 milestone left the deterministic game fully playable offline, change 15 shipped the
quest runtime with an explicit conversion boundary for the AI proposal type, and change 17 delivered
the generative foundation — `OpenAICompatClient`, per-layer `LLM_PROFILES` (the `scenario_director`
layer already exists), the validation-retry-degrade guardrail, `FakeLLMClient`, and the schema
registry seam. Change 20 ships the ScenarioDirector, the first generative consumer that *proposes*
quests instead of narrating or replying. It turns the design §7.1 contract into a validated,
degradable proposal seam so change 21 (SceneBuilder) and the "AI Director is live" milestone (post-21)
have one guarded path to a deterministic `QuestDefinition`.

## What Changes

- Add `world/ai/scenario_director.py`, the `scenario_director` generative layer: a frozen
  `QuestBlueprint` proposal dataclass (name, type, rank, issuer, stages with `location_req`/`npc_req`,
  reward, failure), the `SCENARIO_DIRECTOR_OUTPUT_SCHEMA` registered under the `scenario_director`
  schema id, `build_scenario_prompt(context)` for deterministic bounded prompt construction, and
  `generate_quest_blueprint(client, *, context) -> Deferred[QuestBlueprint]` that runs the layer's
  guarded pipeline. The client is a required injected argument (an explicit `None` errbacks with a
  named `ScenarioDirectorClientRequiredError` before any prompt or transport work); on degrade the
  call resolves to a deterministic draw from the hand-written template pool, never to a raw invalid
  proposal — the game keeps generating quests with the LLM fully offline.
- **Enforce the request context as a hard constraint at the entry point, not in the guardrail.**
  Guardrail semantic validators are context-free by design (they receive only the parsed output), so
  `generate_quest_blueprint` applies a post-guardrail fitness gate: after the guarded pipeline returns
  a valid blueprint, the entry point checks it against the request context (allowed rank, requested
  quest type, issuer branch, anchor). A blueprint that is valid but does not fit the request (e.g.
  the caller asked for an F-rank Altoria quest and got a C-rank foreign quest) is treated as a degrade
  trigger and replaced by a context-fit template draw, so a caller never receives a well-formed but
  inapplicable quest.
- Register the layer's guardrail hooks with `register_scenario_director()`: the output jsonschema,
  semantic validators (rank in `GUILD_RANK_REGISTRY`, reward copper inside that rank's copper band
  with S honoring its open upper bound, non-negative integer merit, known reward item keys with
  positive quantities and no duplicates, known scene archetype, known NPC tier, known monster tier
  when a DEFEAT stage declares one, known issuer branch, contiguous stage indices, `deadline_hours`
  being `None` or a positive integer, CJK/bounded `name` and `scene_sentence`, and no leaked
  template-placeholder syntax), and a sentinel degrade fallback. Registration is atomic with rollback,
  idempotent, and boot-tolerant exactly like `register_narrator`/`register_npc_dialogue`.
- **Establish the two proposal vocabularies as immutable lore registries**, not `world/ai`
  constants: `world/lore/scene_archetypes.py` defines a frozen `SceneArchetype` dataclass and a
  keyed `SCENE_ARCHETYPE_REGISTRY`, and `world/lore/npc_tiers.py` defines a frozen `NPCTier`
  dataclass and a keyed `NPC_TIER_REGISTRY`. This is required so the vocabularies are legally
  consumable by every consumer on both sides of the single-writer boundary: the `world/ai` semantic
  validators (which may import `world.lore`), change 21's SceneBuilder (a deterministic consumer that
  may not import `world.ai`), and the `world/quests` compiler — all read the same immutable registry
  values instead of duplicating constants. This matches the design §5.1/§8 source-of-truth model (the
  §8 `SceneArchetype` registry) and the project invariant that lore registries are the shared
  immutable world data.
- Add `world/ai/director_templates.py`, the hand-written quest template pool (design §7.5's
  ScenarioDirector degradation): a non-empty tuple of pre-validated `QuestBlueprint` values that use
  only permanent world content (known monster tiers, anchors, grid coordinates, known items) so every
  template compiles to a `QuestDefinition` registrable and completable through the deterministic loop
  with no LLM and no SceneBuilder. Every template must pass the same schema and semantic validators,
  locked by a test. The pool is indexed so the degraded draw can honor the request context (rank,
  type, branch); a context with no compatible template raises a named `ScenarioDirectorTemplateError`
  rather than silently returning an inapplicable quest.
- Add `world/quests/compile.py`, the deterministic translation boundary quest-runtime D-1 reserved
  for change 20: `compile_quest_blueprint(validated_payload) -> CompiledQuest` re-validates the
  validated proposal payload against the lore registries and maps it onto the closed immutable
  runtime type (`QuestDefinition` plus a `QuestReward` and issuer branch), raising a named
  `QuestCompileError` on anything invalid, and `register_generated_quest(...)` registers the compiled
  definition and its `GuildQuestOffer` **as one all-or-nothing operation**: both registries'
  equal/conflict states are preflighted before either dict is written, and a failure on the offer
  write rolls the definition write back, so a generated definition is never left on the board without
  its offer. The compiler re-checks every constraint the guardrail checked, reading the same
  `world.lore` registries, so the AI validators and the compiler cannot drift.
- Define the **canonical payload contract** as the shared neutral contract both sides read: the
  JSON-safe `QuestBlueprint.to_payload()` mapping whose per-stage mapping rules (objective kind →
  `ObjectiveKind`, `location_req.layer` → `DestinationKind`, `npc_req` presence →
  `requires_bound_targets`, `item_key` → ACQUIRE, quantity, deadline) are pinned in the delta spec so
  the guardrail schema and the compiler agree on one versioned shape. The compiler's `QuestDefinition`
  `key` is a stable content digest over the canonical runtime definition serialization, so equal
  content always yields an equal key (idempotent re-registration) and different content never
  collides.
- Keep the single-writer and transport boundaries intact: `world/ai/scenario_director.py` imports no
  state writer, no typeclass, and no live transport (the repository-wide contract test stays green
  with no edits); the compile step lives in `world/quests/` (deterministic) and its source contains
  no `world.ai`/`ollama`/`llm_client` fragment, keeping the deterministic-path ban test green; the
  template pool imports the proposal model one-way from `scenario_director` and is read through a
  lazy accessor, so no module-level import cycle can form at startup.
- Wire `_register_scenario_director_layer()` into `server/conf/at_server_startstop.py`'s
  `at_server_start()` hook (the post-`evennia._init()` seam), boot-tolerant like the narrator and
  npc_dialogue registrations.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased. The
  layer produces validated proposals and a deterministic compile boundary as a consumable seam; the
  composition root that asks the director for a quest and posts the compiled offer to the guild board
  belongs to change 21 / future wiring, not this change.

## Capabilities

### New Capabilities

- `scenario-director`: The generative quest-proposal layer — closed `QuestBlueprint` schema, bounded
  deterministic prompt construction, a guarded Deferred-returning entry point that always resolves to
  a valid blueprint that also fits the request context, semantic validators bounding
  rank/reward/archetype/NPC tier/references against immutable lore registries, a hand-written
  template pool as the offline degradation draw, and the deterministic compile boundary that
  translates validated proposals into the immutable `QuestDefinition` + `QuestReward` runtime type
  (with an all-or-nothing board registration) without ever feeding raw AI dicts to the registry.

### Modified Capabilities

- None. The `llm-profiles` spec already names `scenario_director` as one of the four layer keys, the
  `guardrail` spec already supports per-layer semantic-validator and degrade-fallback registration,
  the `quest-blueprint` spec already reserves the AI `QuestBlueprint` proposal as change 20's
  distinct type and forbids raw mappings in the runtime registry (unchanged), and the repository-wide
  transport-boundary contract already scans every production module under `world/ai/`.

## Impact

- Adds `world/ai/scenario_director.py` (proposal model, prompt builder, output schema, semantic
  validators, sentinel fallback, request-context fitness gate, `generate_quest_blueprint`,
  `register_scenario_director`) and package-local tests under `world/ai/tests/test_scenario_director.py`.
- Adds `world/lore/scene_archetypes.py` (`SceneArchetype` + `SCENE_ARCHETYPE_REGISTRY`) and
  `world/lore/npc_tiers.py` (`NPCTier` + `NPC_TIER_REGISTRY`) with registry tests, consumed by the
  validators, change 21's SceneBuilder, and the compiler.
- Adds `world/ai/director_templates.py` (the hand-written template pool) with pool validation tests
  that every template validates, compiles, and is context-indexable.
- Adds `world/quests/compile.py` (`compile_quest_blueprint`, `register_generated_quest`,
  `CompiledQuest`, `QuestCompileError`) and package-local tests under
  `world/quests/tests/test_compile.py`, including an `EvenniaTest` offline end-to-end loop.
- Adds `_register_scenario_director_layer()` to `server/conf/at_server_startstop.py`'s
  `at_server_start()` hook plus one startup integration test.
- Consumes the change-17 `guardrail`, `profiles` (`scenario_director` layer already present),
  `schemas.descriptor`, and `schemas.registry` seams; change-15 `QuestDefinition` /
  `register_quest_definition`; change-16 `QuestReward` / `GuildQuestOffer` / `register_guild_offer`;
  and read-only lore registries (`GUILD_RANK_REGISTRY`, `GUILD_BRANCH_REGISTRY`, `ITEM_REGISTRY`,
  `MONSTER_TIER_REGISTRY`, `ANCHOR_PLACEMENT_REGISTRY`, plus the new scene-archetype and NPC-tier
  registries).
- No container, dependency, settings-schema, or persisted-data change; no `LLM_PROFILES` edit.
- Establishes the validated proposal seam consumed by change 21 (SceneBuilder spawns from
  `location_req`/`npc_req` and binds through `bind_stage_runtime`) and by future guild-board wiring;
  those consumers remain outside this change.
