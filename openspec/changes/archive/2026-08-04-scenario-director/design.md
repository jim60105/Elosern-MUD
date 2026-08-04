## Context

Change 15 shipped the deterministic quest runtime with an explicit handoff: its design.md D-1 and
Open Questions reserve the AI `QuestBlueprint` proposal and the "narrow conversion boundary" for
change 20, and the `quest-blueprint` main spec records that raw AI-shaped dicts are rejected by the
runtime registry. Change 17 shipped the generative foundation — `OpenAICompatClient`, per-layer
`LLM_PROFILES` (the `scenario_director` layer already exists in `world/ai/profiles.py`), the
validation–retry–degrade guardrail with per-layer semantic-validator and degrade-fallback registries,
`FakeLLMClient`, and the schema registry seam. Change 18 (narrator) and change 19 (NPC dialogue)
established the two reference patterns this change follows: a `world/ai/` module that consumes the
client only through an injected protocol, registers its own output schema/validators/fallback
atomically and idempotently, and degrades without ever mutating state; plus a deterministic
counterpart in `world/rules/` (npc_intents) that verifies and applies.

Design §7.1 fixes the director's contract: it "emits requirements, not entities" — a `QuestBlueprint`
JSON object with `name`, `type` (採集/討伐/護衛/探索/緊急), `rank`, `issuer`, `stages` (each with
`index`, `objective`, `location_req`, `npc_req`), `reward`, and `failure`. Because the output is
requirements, it is "fully validatable before it touches the DB: rank legality, reward inside the
`GuildRank` band for that rank, archetype known, NPC tier known, stage indices contiguous." Design
§7.5 fixes the degradation: the ScenarioDirector layer draws from a hand-written quest template pool.
Design §10 fixes the test rule: generative tests use `FakeLLMClient` and never contact a real
endpoint. Design §8 introduces the `SceneArchetype` registry (key + `scene_sentence` + image) as the
archetype source of truth.

Two architectural constraints shape every decision:

1. **The single-writer / transport boundary.** No module under `world/ai/` may import a state writer
   (`world.rules`, `world.maps`, `world.quests`, `typeclasses`, spawner, create) or a live transport
   (`evennia.contrib.rpg.llm`, `twisted.web`, `twisted.internet.reactor`). The repository-wide
   contract test (`tests/test_ai_transport_contract.py`) enforces this by AST scan with no edits.
   Consequences: the director cannot construct `QuestDefinition`, cannot read `world.quests`
   registries, and cannot call the runtime registry. `world.lore` is read-only registry data and is
   NOT a banned import, so the director's semantic validators read lore registries directly (matching
   the `guardrail` spec: "Semantic validation never mutates game state — they read registry data and
   the proposed output only"). The inverse matters just as much: **change 21's SceneBuilder and the
   `world/quests` compiler are deterministic consumers that must not import `world.ai`**, so any
   vocabulary the director's output references must live in a package both sides may import —
   `world/lore`.
2. **The deterministic-path ban.** `world/quests/`, `world/rules/`, `world/maps/`, and `commands/`
   must not reference the fragments `world.ai`, `ollama`, or `llm_client` anywhere in source. The
   compile boundary therefore lives in `world/quests/compile.py` and accepts a plain, validated
   JSON-safe payload — never a `QuestBlueprint` object from `world/ai` — so the two packages stay
   import-disjoint, and it reads the same `world.lore` registries the guardrail validators read.

The deterministic surfaces already exist and are consumed, never rewritten: change-15
`QuestDefinition`/`validate_definition`/`register_quest_definition` in `world/quests/definitions.py`,
change-16 `QuestReward`/`GuildQuestOffer`/`register_guild_offer` in `world/rules/guild_offers.py`, and
the read-only lore registries (`GUILD_RANK_REGISTRY`, `GUILD_BRANCH_REGISTRY`, `ITEM_REGISTRY`,
`MONSTER_TIER_REGISTRY`, `ANCHOR_PLACEMENT_REGISTRY`).

## Goals / Non-Goals

**Goals:**

- Provide `world/ai/scenario_director.py` with `generate_quest_blueprint(client, *, context) ->
  Deferred[QuestBlueprint]`, a guarded mapping that always resolves to a **valid** `QuestBlueprint`
  that also **fits the request context**: LLM-generated-and-validated on success, or a deterministic
  context-fitting draw from the hand-written template pool on any degrade trigger. The client is a
  **required** injected argument; an explicit `None` errbacks with a named
  `ScenarioDirectorClientRequiredError` as the first statement.
- Provide `build_scenario_prompt(context)` — deterministic, bounded, faithful prompt construction
  whose system message fixes the director role, 正體中文, the no-invention fidelity rule, and the
  `QuestBlueprint` JSON output contract, and whose user message serializes the request context with
  stable JSON.
- Define the closed proposal type `QuestBlueprint` with frozen nested values, a `quest_type`
  restricted to the five `QuestType` values, explicit contiguous stage indices, and constructor-level
  rejection of mutable containers; register `SCENARIO_DIRECTOR_OUTPUT_SCHEMA` under the
  `scenario_director` schema id.
- Establish the archetype and NPC-tier vocabularies as **immutable lore registries**
  (`world/lore/scene_archetypes.py`, `world/lore/npc_tiers.py`) so the `world/ai` validators, change
  21's SceneBuilder, and the `world/quests` compiler all read one shared source of truth without
  crossing the single-writer boundary.
- Register the `scenario_director` layer's semantic validators: rank legality, reward inside the
  rank's copper band (S open upper bound), non-negative integer merit, known reward item keys with
  positive quantities and no duplicates, known scene archetype (`SCENE_ARCHETYPE_REGISTRY`), known
  NPC tier (`NPC_TIER_REGISTRY`), known monster tier when a DEFEAT stage declares one, known issuer
  branch, contiguous stage indices, `deadline_hours` `None`-or-positive, bounded non-empty CJK
  `name`/`scene_sentence`, and no leaked template-placeholder syntax. Register the sentinel degrade
  fallback. `register_scenario_director()` installs all hooks atomically with rollback, idempotently,
  and boot-tolerantly, exactly like `register_narrator`/`register_npc_dialogue`.
- Provide `world/ai/director_templates.py`, a non-empty hand-written template pool whose entries are
  pre-validated `QuestBlueprint` values referencing only permanent world content, every entry locked
  by tests to pass the schema and semantic validators and to compile into a registerable, completable
  `QuestDefinition`, and the pool indexable by rank/type/branch so the degraded draw honors the
  request context.
- Provide `world/quests/compile.py`: `compile_quest_blueprint(validated_payload) -> CompiledQuest`
  that re-validates deterministically against the lore registries and maps the proposal onto the
  closed runtime type using a **pinned per-stage mapping contract**, and
  `register_generated_quest(...)` that registers the `QuestDefinition` and `GuildQuestOffer`
  **all-or-nothing** through existing APIs. Raw AI dicts never enter `QUEST_DEFINITION_REGISTRY`.
- Provide a deterministic degraded-draw and compile path proven by an offline end-to-end `EvenniaTest`
  (disabled profile → template blueprint → compile → atomic register → accept → fight → turn in) with
  no LLM and no generative state mutation.
- Preserve the single-writer and transport boundaries exactly as the existing contract tests enforce
  them, and keep every generative test offline via `FakeLLMClient`.

**Non-Goals:**

- Wiring the director to any player-facing command, the guild board, or the quest board's
  accept/turn-in flow. `commands/` is deterministic and may not import `world.ai`; the roadmap assigns
  the composition root (ask the director for a quest, compile it, post the offer) to change 21 and
  future guild-board wiring. This change ships the consumable seams: the guarded proposal layer, the
  template pool, and the deterministic compile boundary.
- Spawning instances, NPCs, or prototypes; interpreting `location_req`/`npc_req` into objects. Change
  21 owns SceneBuilder and binds its created objects via `bind_stage_runtime()`. `CompiledQuest`
  carries the per-stage spawn requirements as plain validated data so change 21 can consume them
  without importing `world/ai`. The offline end-to-end test proves the director+compile+existing
  runtime loop with a directly created permanent-content target, exactly as change 15's own offline
  integration tests do; it does **not** pretend SceneBuilder spawn exists in this change.
- Implementing deterministic failure conditions beyond `deadline_hours`. The `failure.conditions`
  field is accepted only as an empty list (a forward-declared seam); a non-empty value is rejected by
  the compiler with a named error rather than silently ignored.
- Structured tool calls, streaming, or re-parsing a blueprint back into the LLM. The `QuestBlueprint`
  is the typed contract; only the deterministic compiler may interpret it.
- Any change to `world/ai/guardrail.py`, `world/ai/client.py`, `world/ai/profiles.py`,
  `world/quests/definitions.py`, `world/rules/guild_offers.py`, or the deterministic game loop.
- New settings keys, dependencies, container changes, or persisted-data migrations. The
  `scenario_director` profile already exists with the local-first default.
- Backward-compatibility adapters; the project is unreleased.

## Decisions

### D1. `QuestBlueprint` is a closed, deeply immutable proposal type, distinct from `QuestDefinition`

`world/ai/scenario_director.py` defines frozen dataclasses mirroring design §7.1:

```python
@dataclass(frozen=True)
class BlueprintLocation:
    layer: str                       # "anchor" | "grid" | "instance" (wilderness not representable)
    archetype: str | None = None     # SCENE_ARCHETYPE_REGISTRY key
    anchor_key: str | None = None    # destination anchor for layer="anchor"
    anchor_near: str | None = None   # placement hint for instance scenes (change 21)
    xyz: tuple[int, int, str] | None = None
    scene_sentence: str | None = None

@dataclass(frozen=True)
class BlueprintNpcReq:
    role: str
    tier: str                        # NPC_TIER_REGISTRY key
    disposition: str | None = None

@dataclass(frozen=True)
class BlueprintObjective:
    kind: str                        # "defeat" | "reach_location" | "escort" | "acquire"
    quantity: int = 1
    monster_tier: str | None = None  # defeat-by-known-tier variant
    item_key: str | None = None      # acquire variant

@dataclass(frozen=True)
class BlueprintStage:
    index: int
    objective: BlueprintObjective
    location: BlueprintLocation | None = None
    npc_reqs: tuple[BlueprintNpcReq, ...] = ()

@dataclass(frozen=True)
class BlueprintReward:
    copper: int
    items: tuple[ItemQuantity, ...]  # reuse world.rules.guild_offers.ItemQuantity as plain data
    merit: int

@dataclass(frozen=True)
class BlueprintFailure:
    deadline_hours: int | None
    conditions: tuple[()] = ()       # forward-declared; must stay empty in this change

@dataclass(frozen=True)
class QuestBlueprint:
    name: str
    quest_type: str                  # exactly one of QuestType's five values
    rank: str
    issuer: str                      # GUILD_BRANCH_REGISTRY key
    stages: tuple[BlueprintStage, ...]
    reward: BlueprintReward
    failure: BlueprintFailure
```

`QuestBlueprint` is a **proposal value**, never runtime input: `register_quest_definition` continues
to accept only `QuestDefinition`, and the `quest-blueprint` spec's raw-mapping rejection is untouched.
Deep immutability is enforced by construction: `__post_init__` walks the nested values and rejects any
`dict`/`list` container, so the `frozen=True` guarantee cannot be undermined by a field holding a
mutable collection. The `quest_type` vocabulary and the objective `kind` vocabulary are closed
StrEnum-backed sets, stage `index` values are validated contiguous from zero, and `to_payload()`
returns a JSON-safe mapping for the compile boundary.

Alternative considered: having the director emit `QuestDefinition` directly. Rejected — that couples
the generative layer to the runtime type and state registry, violating the single-writer boundary.

### D2. `build_scenario_prompt` is deterministic, bounded, and faithful

`build_scenario_prompt(context)` returns a `(system, user)` message pair. The system message fixes
the director role (伊洛瑟恩大陸 的任務企劃), the language (正體中文), the fidelity rule ("只能引用世界
上真實存在的內容；不得編造任何公會階級、場景類型、NPC 階級、物品或獎勵"), and the output contract
(the `QuestBlueprint` JSON shape, with stage indices required contiguous from zero). The user message
serializes the request context — requested quest type, allowed rank, issuer branch, anchor, and an
optional bounded request note — with stable sorted JSON serialization (`sort_keys=True`,
`ensure_ascii=False`).

Hard bounds mirror the narrator: per-field string-length caps and a bounded total size, so a
pathological request cannot produce an unbounded prompt. The prompt contains only plain
JSON-compatible data — no live entity references — consistent with the entity-key-only rule.
Identical context always produces byte-identical prompts.

The context is the caller's request, resolved by the future composition root, not by this module: it
is plain data (allowed rank, branch, anchor, type hint). The module never reads player state, so it
cannot accidentally leak true or disguised stats into the proposal.

### D3. The request context is a hard constraint enforced at the entry point, not in the guardrail

The guardrail's semantic validators are **context-free by contract** (design §7.5: the pipeline
passes only the parsed output to validators; the registered fallback is a zero-arg callable). They
verify a blueprint is *known and well-formed*, never that it *answers the request*. A caller who asks
for an F-rank Altoria hunt must not receive a well-formed C-rank foreign quest. So the request fit is
checked by `generate_quest_blueprint` **after** the guarded pipeline returns, in a deterministic
fitness gate:

```python
def _fits_context(blueprint: QuestBlueprint, context: Mapping[str, Any]) -> bool:
    # rank <= allowed_rank (by GUILD_RANK_REGISTRY order) when allowed_rank is given
    # quest_type == requested type when requested_type is given
    # issuer == requested branch when issuer_branch is given
    # location.anchor_key/anchor_near == requested anchor when anchor is given
```

A blueprint that passes schema + semantic validation but fails the fitness gate is treated as a
degrade trigger: the call discards it and resolves to a context-fitting template draw instead (D6).
This keeps the guardrail pipeline untouched (context-free, per §7.5) while guaranteeing the caller
receives a proposal that is both valid *and applicable*.

Alternative considered: passing context into the guardrail semantic validators. Rejected — the
`guardrail` spec fixes the validator signature as `(parsed) -> errors`, the pipeline is layer-neutral,
and reworking it for one layer would modify a frozen shared surface. The entry-point gate is the
smallest change that honors the contract.

### D4. Semantic validators enforce the closed proposal contract the guardrail spec anticipates

The `scenario_director` layer registers semantic validators under stable names, each reading only
lore registry data and the parsed output (per the `guardrail` spec's "Semantic validation never
mutates game state" requirement):

- `rank_known` — `rank` is a key in `GUILD_RANK_REGISTRY`.
- `reward_in_band` — reward copper is an integer within `[reward_min_copper, reward_max_copper]` of
  the blueprint's rank (S honors `None` upper bound, mirroring `validate_offer`'s band rule);
  `merit` is a non-negative integer.
- `reward_items_known` — every reward item key is in `ITEM_REGISTRY` with a positive integer quantity
  and no duplicate keys.
- `archetype_known` — every `location_req.archetype` is in `SCENE_ARCHETYPE_REGISTRY`.
- `npc_tier_known` — every `npc_req.tier` is in `NPC_TIER_REGISTRY`.
- `monster_tier_known` — a DEFEAT stage's optional `monster_tier` is in `MONSTER_TIER_REGISTRY`.
- `issuer_known` — `issuer` is a key in `GUILD_BRANCH_REGISTRY`.
- `stage_indices_contiguous` — stage indices are `0..n-1` in order.
- `deadline_valid` — `deadline_hours` is `None` or a positive integer.
- `strings_bounded_cjk` — `name` and each `scene_sentence` are non-empty, within the length cap, and
  contain at least one CJK Unified Ideograph.
- `no_template_placeholder` — no `{actor}`/`{target}`/`{data[...]}`-style leaked template syntax.

The output jsonschema constrains structure (closed `quest_type` enum, objective `kind` enum, integer
bounds, array shapes); the semantic validators carry the registry-backed checks jsonschema cannot
express without a `oneOf` matrix. Each failure appends a concrete message and retries within
`1 + max_retries`; the final fallback is the template-pool draw (D6). These are conservative shape
and reference checks, not quality scoring.

Alternative considered: enforcing registry-backed bounds only in the deterministic compiler and
keeping `world/ai` validators purely structural. Rejected — design §7.1 explicitly requires the
proposal to be "fully validatable before it touches the DB", and the guardrail spec names
rank/reward/archetype validators as exactly the per-layer hooks later changes add.

### D5. `register_scenario_director()` wires hooks atomically and idempotently from the registration site

`register_scenario_director()` installs `SCENARIO_DIRECTOR_OUTPUT_SCHEMA` (via
`schemas.registry.register_output_schema("scenario_director", ...)`), every semantic validator, and
the sentinel degrade fallback in one operation, and marks the layer registered only after every hook
is installed. It is atomic with rollback (a mid-way failure removes every own hook by identity), and
idempotent: a second call is a no-op that keeps the first registration and swallows only this
module's own duplicate-registration errors (`GuardrailRegistrationError`,
`DuplicateSchemaError`). The D3 gate reads the guardrail's actual registries, so a test that resets
them automatically forces the next call through the not-registered path.

Production calls it from `server/conf/at_server_startstop.py`'s `at_server_start()` hook (after
`evennia._init()` has populated `evennia.logger`) via `_register_scenario_director_layer()`, a
boot-tolerant wrapper identical in shape to `_register_npc_dialogue_layer` that catches
`GuardrailRegistrationError` and `DuplicateSchemaError`, logs, and continues startup. One startup
integration test locks the seam.

### D6. The hand-written template pool is the sole degradation source, is pre-validated, and honors the request context

`world/ai/director_templates.py` defines `QUEST_TEMPLATE_POOL: tuple[QuestBlueprint, ...]`, a
non-empty set of hand-written proposals referencing only **permanent world content**: known monster
tiers (`MONSTER_TIER_REGISTRY` keys), placed anchors (`ANCHOR_PLACEMENT_REGISTRY` keys), grid
coordinates, and known item keys. Instance-layer stages are deliberately absent from templates: an
instance scene cannot be completed until change 21's SceneBuilder binds a room, so a template with an
instance stage would not be offline-completable. Templates are written as `QuestBlueprint` values
(not `QuestDefinition`) so they flow through the exact same compile boundary as LLM output.

The pool is **indexed for context matching**: each template carries its rank, type, issuer, and
anchor, and `_draw_template(context)` deterministically selects the first entry whose `_fits_context`
predicate (D3) passes — first pool entry in stable order that fits, else a named
`ScenarioDirectorTemplateError`. No randomness, so identical contexts degrade identically (locked by
a test), and a caller never receives a well-formed-but-inapplicable offline quest.

**Import direction is pinned to avoid a startup cycle.** `director_templates.py` imports the proposal
model from `scenario_director.py` (one direction: templates → model). The director module reads the
pool through a lazy accessor — a module-level `get_template_pool()` function that imports
`world.ai.director_templates` inside the call, or an injected pool — so registering the layer at
startup never forces both modules to import each other's partially-initialized state. A cold-start
import test locks this.

Tests lock the pool's contract: non-empty; every entry passes the output schema and every semantic
validator; every entry compiles via `compile_quest_blueprint` into a definition that passes
`validate_definition`, registers, and has stages resolvable through permanent content; and the
degraded draw is deterministic and context-fitting. Because templates live in `world/ai`, they may
not import `world.quests`; they reference permanent content by the same registry keys the semantic
validators check.

### D7. The canonical payload contract is versioned and shared by both boundaries

Both sides of the boundary must interpret one proposal shape, or the guardrail and the compiler will
drift. `QuestBlueprint.to_payload()` produces the canonical JSON-safe mapping, and the pinned mapping
rules live in the delta spec so they are reviewable and testable:

| Blueprint field | Runtime mapping |
|---|---|
| `quest_type` 採集/討伐/護衛/探索/緊急 | `QuestType.GATHER/DEFEAT/ESCORT/EXPLORE/EMERGENCY` |
| objective `kind` `reach_location` | `ObjectiveKind.REACH` |
| objective `kind` `defeat` | `ObjectiveKind.DEFEAT` — exactly one of a known `monster_tier` or non-empty `npc_reqs` (which becomes `requires_bound_targets=True`) |
| objective `kind` `escort` | `ObjectiveKind.ESCORT` with a destination and protected-entity requirement |
| objective `kind` `acquire` | `ObjectiveKind.ACQUIRE` with a known `item_key` and positive `quantity` |
| `location_req.layer` `anchor` | `RoomLocator(ANCHOR, anchor_key=...)` — must be present in `ANCHOR_PLACEMENT_REGISTRY` |
| `location_req.layer` `grid` | `RoomLocator(GRID, xyz=...)` — map key known to the xyzgrid |
| `location_req.layer` `instance` | `RoomLocator(BOUND_INSTANCE)` plus a preserved spawn requirement for change 21 |
| `location_req.layer` `wilderness` | rejected (not representable per the `quest-blueprint` spec) |
| `deadline_hours` | `QuestDefinition.deadline_hours` |
| `failure.conditions` | must be `[]`; non-empty rejected with a named error (forward-declared seam) |
| `reward` / `issuer` | `QuestReward` and the offer's `issuer_branch_key` |

The guardrail's output schema and the compiler's re-validation both derive from this one contract, so
a payload that passes the guardrail always compiles structurally (a test asserts the shared-contract
scenario).

### D8. The deterministic compile boundary lives in `world/quests/` and re-validates everything

`world/quests/compile.py` owns `compile_quest_blueprint(validated_payload: Mapping) -> CompiledQuest`
and `register_generated_quest(compiled)`. This is change 15's reserved "narrow conversion boundary":
it is the only sanctioned translator from the validated proposal to the closed runtime type.

`compile_quest_blueprint` accepts the **JSON-safe validated payload** (the `QuestBlueprint.to_payload()`
mapping), never a `world/ai` object — `world/quests` must not import `world.ai` (deterministic-path
ban), and `world/ai` must not import `world.quests` (state-writer ban), so plain data is the only
disjoint contract. It re-validates every constraint the guardrail validators checked — rank, reward
band, item keys, archetype, NPC tiers, monster tier, branch, contiguous indices, deadline — reading
the **same `world.lore` registries** the guardrail read, plus the runtime's own definition rules, and
raises a named `QuestCompileError` naming the failing field on any violation, before any mutation.
Because both sides read `world.lore` (the compiler may import it; `world/quests` already imports
`world.rules.guild_offers`), the vocabularies cannot drift between the guardrail and the compiler.

The generated `QuestDefinition.key` is a **stable content digest**: `sha256` over the canonical
runtime definition serialization (the compiled `QuestDefinition`'s own fields), hex-prefixed (e.g.
`ai_<first-16-hex>`). Equal content therefore always yields an equal key — `register_quest_definition`
treats equal content as an idempotent no-op — and different content never collides. Reward and issuer
are offer-level, not definition identity: two blueprints with identical stages but different rewards
share a definition key and produce conflicting offers (which `register_generated_quest` surfaces
all-or-nothing, D9).

`CompiledQuest` is a frozen dataclass carrying `definition: QuestDefinition`, `reward: QuestReward`,
`issuer_branch_key: str`, and `stage_requirements: tuple[StageSpawnRequirement, ...]` — the per-stage
`location_req`/`npc_req` plain data preserved for change 21's SceneBuilder, so the blueprint's
spawn requirements survive the boundary without `world/quests` importing `world/ai`.

Alternative considered: compiling in `world/ai/`. Rejected — the compile mutates the runtime registry
and reads `world.quests` types; `world/ai` is banned from both. Alternative considered: having the
director call a `world/rules` applier like change 19's `apply_npc_intent`. Rejected — the
deterministic-path ban forbids `world/rules` from importing `world.ai`, and the compile needs the
`QuestDefinition`/`GuildQuestOffer` types owned by `world/quests`.

### D9. `register_generated_quest` is one all-or-nothing board registration

`register_generated_quest(compiled)` registers the `QuestDefinition` and the `GuildQuestOffer`
together. A generated definition must never be left on the board without its offer, or an offline
retry or repeated sync would observe a half-published quest. Because both registries are
process-local module dicts (not a database), the operation is made atomic by construction:

1. **Preflight** both sides with no writes: compute the definition-registry decision (new / equal /
   conflicting) and the offer-registry decision (new / equal / conflicting) against the existing
   registries, using the existing `register_quest_definition`/`register_guild_offer` validation
   semantics.
2. If either side is a **conflict** (same identity, different content), raise the named
   `QuestCompileError` before writing anything.
3. Otherwise write the definition first, then the offer; if the offer write raises despite preflight
   (defensive), remove the just-added definition entry (rollback) before re-raising, so neither
   registry retains a partial publication.

An `EvenniaTest`-level test asserts the "definition new + offer conflicting" path leaves both
registries unchanged.

Alternative considered: two independent `register_*` calls. Rejected — a mid-sequence failure would
leave an orphan definition and a confusing conflict on retry, exactly the failure the reviewer
surfaced.

### D10. The proposal vocabularies are immutable lore registries, consumable on both sides of the boundary

Design §7.1's validation list requires "archetype known" and "NPC tier known", and change 21
(SceneBuilder) and change 22 (scene art) need the same vocabulary, but no registry exists: rooms carry
an intentionally unvalidated `scene_archetype` seam (`scene-archetype-mixin` spec), and NPC tiers
exist only as race-specific `STATIC_TIER_REGISTRY` entries. The vocabularies therefore become
immutable lore registries:

- `world/lore/scene_archetypes.py` — frozen `SceneArchetype` + keyed `SCENE_ARCHETYPE_REGISTRY`
  (keys such as `forest_path`, `tavern_interior`, `dungeon_interior`, `city_street`,
  `wilderness_path`, `mountain_path`, `ruin_interior`, `coastal_path`, `cave_interior`,
  `shrine_interior`), matching the design §8 `SceneArchetype` registry concept (this change supplies
  the key vocabulary and a `scene_sentence`-ready shape; change 22 adds the image field surface it
  owns).
- `world/lore/npc_tiers.py` — frozen `NPCTier` + keyed `NPC_TIER_REGISTRY` (keys such as `civilian`,
  `guard`, `merchant`, `adventurer`, `mage`, `noble`, `bandit`, `priest`, `knight`).

This is required because the vocabulary must be consumable by three parties that cannot import each
other: the `world/ai` validators (may import `world.lore`), change 21's SceneBuilder (a deterministic
consumer that may not import `world.ai`), and the `world/quests` compiler (also may not import
`world.ai`). `world.lore` is the one package all three may import. It also honors the project
invariant ("Treat module-level lore registries as the source of truth. Use frozen dataclasses and
keyed registries") and the design's own §5.1 lore-as-source-of-truth model. `world/lore/sync.py` is
not modified: these registries are consumed as process-local immutable data, not synced as Scripts,
so no startup-sync delta is needed.

Alternative considered: frozen tuples in `world/ai/scenario_director.py`. Rejected — change 21 and
the compiler cannot legally import `world.ai`, forcing either a boundary violation or constant
duplication; the lore registry is the only shared, boundary-safe home.

## Risks / Trade-offs

- [The guardrail's zero-arg registered fallback cannot know the request context] → D3/D6: the
  registered fallback returns the internal sentinel; `generate_quest_blueprint` maps it to
  `_draw_template(context)` with the actual request, and the template draw is deterministic and
  context-fitting.
- [A well-formed but inapplicable LLM quest could be accepted] → D3's post-guardrail fitness gate
  re-checks rank/type/branch/anchor against the request and treats a misfit as a degrade trigger, so
  the caller never receives a valid-but-inapplicable proposal.
- [`world/ai` cannot import `world.quests`, so the director cannot compile] → D7/D8's disjoint
  contract: the compile boundary lives in `world/quests/compile.py` and accepts the JSON-safe
  validated payload via `QuestBlueprint.to_payload()`; the director never sees a runtime type, and
  the compiler never sees a `world/ai` object.
- [The guardrail schema and the compiler could drift apart] → D7 pins the per-stage mapping in the
  delta spec, both sides derive from `QuestBlueprint.to_payload()`, and a shared-contract test asserts
  a guardrail-valid payload compiles structurally.
- [A proposal that passed the guardrail could still be corrupted in transit to the compiler] → D8's
  compiler re-validates every constraint deterministically against the same `world.lore` registries
  and raises `QuestCompileError` before any mutation; raw dicts remain rejected by
  `register_quest_definition` (locked by a test).
- [An offline director could stop producing quests, or produce inapplicable ones] → D6: degradation
  is a positive draw from a non-empty, pre-validated, context-indexed template pool, and
  `generate_quest_blueprint` never resolves to `None` or an invalid blueprint; the offline end-to-end
  test proves the whole accept→fight→turn-in loop.
- [Template-pool entries could drift from the validators] → D6: every entry is locked by tests to
  pass schema + semantic validation and to compile + register, so pool content can never regress
  silently.
- [Reward-band and registry checks duplicated across the guardrail and the compiler] → deliberate
  defense in depth: the guardrail retries cheaply on the LLM path; the compiler is the deterministic
  gate that no invalid dict can pass. Both read the same `world.lore` registries, so they cannot
  disagree on the authority.
- [A generated definition could be registered without its offer] → D9's all-or-nothing preflight +
  rollback: the conflicting-offer path leaves both registries unchanged, locked by a test.
- [Deterministic content-digest keys could collide] → D8: the digest covers the compiled runtime
  definition's own canonical fields (not reward/issuer), is long enough to make collision
  negligible, and equal content always yields an equal key; reward/issuer differences surface as
  offer conflicts through D9 rather than silent overwrites.
- [Instance-layer stages in LLM output are not completable until change 21] → accepted: the compiler
  accepts them as `BOUND_INSTANCE` and preserves the spawn requirements; templates avoid instance
  layers so offline play remains complete without SceneBuilder. Change 21 binds spawned rooms via
  `bind_stage_runtime`.
- [`failure.conditions` in the §7.1 example has no deterministic surface] → rejected as a
  forward-declared seam when non-empty (named `QuestCompileError`), so the gap is visible rather than
  silently dropped; the schema still accepts the empty-list shape the design example uses.
- [Deterministic-path ban could be tripped by a stray comment] → the compile module's docstrings and
  comments must avoid the fragments `world.ai`, `ollama`, and `llm_client`; the repository-wide ban
  test scans source text and will catch a violation.
- [Module-level import cycle between the pool and the director] → D6 pins one-way imports
  (templates → model) and a lazy pool accessor; a cold-start import test locks the ordering.
- [Duplicate registration could silently override hooks] → D5 defines idempotence narrowly (own
  re-registration is a no-op; incompatible registrations surface the guardrail error), and the
  startup wrapper's skip is boot tolerance, not silent correctness loss — the registration gate fails
  loudly on use.
- [Registration order at server startup] → `_register_scenario_director_layer()` runs from
  `at_server_start` after `evennia._init()`, is idempotent, and is boot-tolerant to foreign leftover
  registrations; one startup integration test locks the seam.

## Migration Plan

1. Add `world/lore/scene_archetypes.py` and `world/lore/npc_tiers.py` with frozen dataclasses and
   keyed registries, plus registry tests.
2. Add `world/ai/scenario_director.py` (proposal dataclasses with constructor-level immutability,
   prompt builder, output schema, semantic validators, sentinel fallback, context-fit gate,
   `generate_quest_blueprint`, `register_scenario_director`) with package-local tests under
   `world/ai/tests/test_scenario_director.py`.
3. Add `world/ai/director_templates.py` (the hand-written, context-indexed template pool, one-way
   model import, lazy accessor) with pool validation tests.
4. Add `world/quests/compile.py` (`compile_quest_blueprint`, `register_generated_quest`,
   `CompiledQuest`, `StageSpawnRequirement`, `QuestCompileError`, content-digest keys,
   all-or-nothing registration) with package-local tests under `world/quests/tests/test_compile.py`,
   including an `EvenniaTest` offline end-to-end loop.
5. Add `_register_scenario_director_layer()` to `server/conf/at_server_startstop.py`'s
   `at_server_start()` hook plus one startup integration test.
6. Run the focused `world.ai`, `world.quests`, and `world.lore` tests, the repository-wide contract
   test, the full Evennia suite, the spec-traceability check, and strict OpenSpec validation.

No persisted-game-data migration applies: this change stores no new state and changes no
deterministic behavior, so rollback is a clean removal of the new modules, the registries, the
template pool, and the startup registration line. No production layer consumes the proposal seam until
change 21 lands.

## Open Questions

None. The proposal contract (§7.1), the degradation (template-pool draw, §7.5), the boundary
constraints (required injected client, plain-data compile contract, no state writers, no transport),
the request-context fitness gate, and the test rule (FakeLLMClient only) are all fixed by the approved
engine design and the change-15/change-16/change-17 contracts. The forward-declared seams —
`failure.conditions` and instance-layer spawn requirements — are deliberately rejected/preserved
rather than faked, and change 21 (SceneBuilder) consumes `CompiledQuest.stage_requirements` and binds
through `bind_stage_runtime` when it lands.
