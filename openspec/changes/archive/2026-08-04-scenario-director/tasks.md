## 1. Immutable lore registries for proposal vocabularies

- [x] 1.1 Add `world/lore/scene_archetypes.py` with a frozen `SceneArchetype` dataclass and a
  non-empty, keyed `SCENE_ARCHETYPE_REGISTRY` covering the design §8 scene-kind vocabulary (e.g.
  `forest_path`, `tavern_interior`, `dungeon_interior`, `city_street`, `wilderness_path`,
  `mountain_path`, `ruin_interior`, `coastal_path`, `cave_interior`, `shrine_interior`)
- [x] 1.2 Add `world/lore/npc_tiers.py` with a frozen `NPCTier` dataclass and a non-empty, keyed
  `NPC_TIER_REGISTRY` covering role tiers (e.g. `civilian`, `guard`, `merchant`, `adventurer`,
  `mage`, `noble`, `bandit`, `priest`, `knight`)
- [x] 1.3 Add registry tests: both registries are non-empty and frozen with no consumer-visible
  mutation; the design §7.1 example keys `forest_path` and `civilian` resolve; `world/ai/` validators,
  change-21-style consumers, and the `world/quests` compiler all reference the registry values
  without a state-writer import or duplicated constants

## 2. Proposal type and closed vocabularies

- [x] 2.1 Add `world/ai/scenario_director.py` with the frozen proposal dataclasses `BlueprintLocation`,
  `BlueprintNpcReq`, `BlueprintObjective`, `BlueprintStage`, `BlueprintReward`, `BlueprintFailure`,
  and `QuestBlueprint`, plus `QuestBlueprint.to_payload()` returning a JSON-safe mapping
- [x] 2.2 Enforce constructor-level immutability: `__post_init__` walks nested values and rejects any
  `dict`/`list` container; validate `quest_type` against the five `QuestType` values and stage
  `index` contiguity in the constructor
- [x] 2.3 Add tests under `world/ai/tests/test_scenario_director.py`: a valid blueprint preserves
  explicit stage indices; content cannot be mutated after construction (including nested fields
  holding a mutable container being rejected); an unknown `quest_type` and non-contiguous indices
  fail construction; `to_payload()` round-trips through JSON with no mutable values and no live
  references

## 3. Prompt construction

- [x] 3.1 Add `build_scenario_prompt(context) -> tuple[dict, dict]` returning a deterministic
  system/user pair: system fixes the director role in 伊洛瑟恩大陸, 正體中文, the no-invention
  fidelity rule, and the `QuestBlueprint` JSON output contract; user serializes the request context
  (requested type, allowed rank, issuer branch, anchor, optional note) with stable sorted JSON and
  `ensure_ascii=False`
- [x] 3.2 Enforce hard bounds: per-field string-length caps and a bounded total size; identical input
  SHALL produce byte-identical prompts with no live entity references
- [x] 3.3 Add tests: identical contexts yield byte-identical prompts; oversized context is bounded and
  valid; the system message names the blueprint contract and forbids inventing world references; the
  serialization contains branch/anchor keys and no live entity objects

## 4. Schema, semantic validators, and registration

- [x] 4.1 Define `SCENARIO_DIRECTOR_OUTPUT_SCHEMA` (closed `quest_type` enum, objective `kind` enum
  `defeat`/`reach_location`/`escort`/`acquire`, integer bounds, contiguous `index` array shape,
  reward/failure shapes) and register it under the `scenario_director` schema id
- [x] 4.2 Add the internal `_SCENARIO_DIRECTOR_DEGRADED` sentinel, the
  `ScenarioDirectorClientRequiredError`/`ScenarioDirectorNotRegisteredError`/
  `ScenarioDirectorTemplateError` exceptions, and the `scenario_director`-layer semantic validators:
  `rank_known`, `reward_in_band` (S open upper bound), `reward_items_known` (positive quantities, no
  duplicates), `archetype_known`, `npc_tier_known`, `monster_tier_known`, `issuer_known`,
  `stage_indices_contiguous`, `deadline_valid`, `strings_bounded_cjk`, `no_template_placeholder`
- [x] 4.3 Add `register_scenario_director()` that atomically installs the output schema, every
  semantic validator, and the sentinel degrade fallback with rollback on partial failure, and is
  idempotent: a second call is a no-op swallowing only this module's own duplicate-registration
  errors, never an incompatible one
- [x] 4.4 Add tests: an unknown rank is rejected and retried with the error appended; out-of-band
  reward copper is rejected; unknown archetype/NPC tier/monster tier/issuer are rejected;
  non-contiguous indices are rejected; a valid bounded blueprint passes on the first attempt; partial
  hook-registration failure leaves no `scenario_director` hooks installed; duplicate registration is
  a no-op

## 5. Guarded generation with request-context enforcement

- [x] 5.1 Add `generate_quest_blueprint(client, *, context) -> Deferred[QuestBlueprint]` that rejects
  an explicit `None` client with `ScenarioDirectorClientRequiredError` as the first statement, gates
  on the guardrail's actual registries (`ScenarioDirectorNotRegisteredError` when absent), builds a
  `ChatRequestDescriptor(messages, schema_id="scenario_director")`, yields
  `guarded_call("scenario_director", client, descriptor)`, `json.loads` the accepted text into a
  frozen `QuestBlueprint`, and maps the internal sentinel to `_draw_template(context)` on any degrade
  trigger
- [x] 5.2 Add the `_fits_context(blueprint, context)` predicate (rank at or below allowed rank by
  `GUILD_RANK_REGISTRY` order, quest type/issuer/anchor match when requested) and apply it as a
  post-guardrail gate: a schema-valid blueprint that fails the gate is treated as a degrade trigger
  and replaced by a context-fitting template
- [x] 5.3 Add `_draw_template(context)` with deterministic selection (first pool entry fitting the
  context in stable order) and raise `ScenarioDirectorTemplateError` when no compatible template
  exists
- [x] 5.4 Add tests: a valid context-fitting fixture resolves to a frozen `QuestBlueprint` with no
  state change; an explicit `None` client errbacks before any prompt/transport work; a
  schema-valid-but-context-misfitting blueprint is replaced by a fitting template; a disabled profile
  resolves to a valid context-fitting template with zero client calls; transport failure and
  exhausted retries resolve to a template, never invalid output or `None`; identical degraded
  contexts draw identical templates; an unsatisfiable context errbacks with
  `ScenarioDirectorTemplateError`; calling before registration errbacks with
  `ScenarioDirectorNotRegisteredError`

## 6. Hand-written template pool

- [x] 6.1 Add `world/ai/director_templates.py` defining `QUEST_TEMPLATE_POOL: tuple[QuestBlueprint, ...]`
  with at least two hand-written entries using only permanent world content (known monster tier,
  placed anchor or grid coordinate, known item) and no instance-layer stages; import the proposal
  model one-way from `scenario_director` and expose the pool through a lazy accessor used by the
  director module
- [x] 6.2 Add pool tests: the pool is non-empty; every entry passes the output schema and every
  semantic validator; every entry compiles via `compile_quest_blueprint` into a definition that
  passes `validate_definition` and registers; the degraded draw is deterministic and context-fitting
  for identical contexts; a cold-start import order test proves the pool and the director module do
  not form a module-level import cycle

## 7. Canonical payload contract

- [x] 7.1 Pin the per-stage mapping contract in `QuestBlueprint.to_payload()` and its docstring:
  objective `kind` → `ObjectiveKind`; `location_req.layer` → `DestinationKind` (anchor/grid/instance,
  wilderness rejected); DEFEAT declares exactly one of a known `monster_tier` or `npc_reqs`
  (`requires_bound_targets=True`); ACQUIRE declares a known `item_key`; `quantity` positive;
  `deadline` → `deadline_hours`; `failure.conditions` accepted only as `[]`
- [x] 7.2 Add a shared-contract test: a payload that passes the `scenario_director` output schema and
  semantic validators compiles through `compile_quest_blueprint` without a contract-shaped
  rejection, and each stage kind maps to exactly the corresponding runtime fields

## 8. Deterministic compile boundary

- [x] 8.1 Add `world/quests/compile.py` with `QuestCompileError`, frozen `StageSpawnRequirement`,
  frozen `CompiledQuest(definition, reward, issuer_branch_key, stage_requirements)`, and
  `compile_quest_blueprint(validated_payload) -> CompiledQuest` that re-validates every constraint
  (rank, reward band, item keys, archetype, tiers, branch, contiguous indices, deadline, empty
  `conditions`) against the same `world.lore` registries the guardrail reads and maps the payload
  onto `QuestDefinition` + `QuestReward` + issuer; `wilderness` layers and non-empty
  `failure.conditions` are rejected with named errors; the definition `key` is a stable content
  digest over the canonical compiled definition serialization
- [x] 8.2 Add `register_generated_quest(compiled)` that preflights both registries' equal/conflict
  states, writes the definition and then the offer, and rolls the definition write back if the offer
  write fails, so a generated definition is never registered without its offer
- [x] 8.3 Add tests under `world/quests/tests/test_compile.py`: a valid payload compiles to a
  definition passing `validate_definition` with the declared reward/issuer; out-of-band reward and
  unknown item keys raise `QuestCompileError` with no registry change; `wilderness` layer and
  non-empty `conditions` raise named errors; equal content yields equal keys and double registration
  is idempotent with one definition and one offer; a "definition new + offer conflicting" path leaves
  both registries unchanged; a raw AI-shaped dict is still rejected by `register_quest_definition`;
  every guardrail-checked constraint is re-checked on an un-guardrail-validated payload
- [x] 8.4 Add an `EvenniaTest` offline end-to-end test: disable every `LLM_PROFILES` entry, run
  `generate_quest_blueprint` to a context-fitting template, compile, atomically register definition
  and offer, accept the quest, resolve a lethal action against a directly created permanent-content
  target (exactly as change 15's offline integration tests create one), reach `COMPLETED`, and turn
  in the reward — with no LLM call and no generative state mutation

## 9. Boundary and startup wiring

- [x] 9.1 Verify `world/ai/scenario_director.py` imports no state writer, no typeclass, no live
  transport symbol, and no socket, and consumes the client only through the injected protocol
  (repository contract test stays green with no edits)
- [x] 9.2 Verify `world/quests/compile.py` contains no `world.ai`, `ollama`, or `llm_client` fragment
  in source (deterministic-path ban test stays green with no edits)
- [x] 9.3 Add `_register_scenario_director_layer()` to `server/conf/at_server_startstop.py`'s
  `at_server_start()` hook (post-`evennia._init()`), calling `register_scenario_director()` inside a
  boot-tolerant try/except that logs and skips on a foreign leftover registration; add one startup
  integration test that invokes the seam and asserts the layer is registered with the sentinel
  fallback
- [x] 9.4 Add a regression test that every scenario-director test uses `FakeLLMClient` or recorded
  fixtures and never constructs `OpenAICompatClient` or opens a network connection

## 10. Verification

- [x] 10.1 Map every delta-spec scenario to at least one deterministic test and apply
  `covers_requirement` annotations to the discoverable `test_*` functions using literal IDs from
  `uv run --locked python -m tools.spec_traceability list`
- [x] 10.2 Run focused tests: `uv run --locked evennia test --settings settings.py world.ai.tests.test_scenario_director world.quests.tests.test_compile world.lore.tests`, the server-start test, and the
  repository-wide contract test
- [x] 10.3 Run `uv run --locked evennia test --settings settings.py .` (or the affected domain suites)
- [x] 10.4 Run `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] 10.5 Run `uv run --locked python -m tools.spec_traceability check`
- [x] 10.6 Run `openspec validate scenario-director --strict` and `openspec validate --all --strict`
- [x] 10.7 Run `git diff --check` and confirm only planning artifacts are changed by this proposal
