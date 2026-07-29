# AI-Driven Single-Player MUD Engine — Design

**Date:** 2026-07-29
**Status:** Approved
**Scope:** Deterministic game engine, generative narrative layer, multimodal scene art, containerized delivery.

This document is the single reference for every OpenSpec change in this project. Each change
implements a slice of it. When a change conflicts with this document, this document wins unless
it is explicitly amended.

---

## 1. Product Context

A single-player, adult, AI-driven MUD set in 伊洛瑟恩大陸 (Elosern), a Japanese-style
sword-and-sorcery continent. One shared world foundation; the AI Director generates unlimited
story arcs, main quests, and side quests on top of it.

**Non-negotiable content constraint.** Every character that enters the game — player, NPC, or
imported — is an adult. The import schema enforces `age >= 18` and `apparent_age >= 18` as a hard
rejection, and a regression test asserts that an underage record fails import. This is a code-level
invariant, not a documentation convention. The sample cards currently in `tmp/story_settings/`
(gitignored, never committed) do not satisfy it and cannot be used as seed data.

**Developer background.** Python primary. Existing SillyTavern-style world and character data.
No art capability; Stable Diffusion via external service. Runs on a single machine with a local
GPU serving Ollama and sd-webui.

---

## 2. Architectural Decisions

These were settled during design. Do not relitigate them inside a change.

| # | Decision | Rationale |
|---|---|---|
| D1 | **Combat uses the world's native linear stats plus an overwhelm threshold.** No compression to d20. | The setting spans three orders of magnitude (human HP 100 vs elf HP 10000). Any mapping to a d20 table destroys that semantics. Imported numbers are used verbatim. |
| D2 | **狀態偽裝 is a pure display layer.** `disguised_stats` affects `look`, guild registration, and appraisal items only. Combat, resolution, and damage always read true traits. | Simplest thing that works. Avoids an observer-resolution subsystem nobody asked for. |
| D3 | **Four map layers with selective promotion.** Anchor (permanent) / Grid (xyzgrid) / Virtual (wilderness) / Instance (ephemeral, TTL). Named instance rooms the player interacted with are promoted to permanent. | Keeps the world consistent where it matters and cheap where it doesn't. |
| D4 | **Player-driven clock with explicit time skips.** The world advances only on player action, plus `rest` / `sleep` / `wait` commands. | Single-player. Removes all LLM-latency pressure and makes saves fully reproducible. |
| D5 | **Three-layer Director with separated responsibilities.** ScenarioDirector → SceneBuilder → Narrator, each with its own schema, validation, and retry. | Hallucination is contained to one layer. Narrator physically cannot write state. |
| D6 | **OpenAI-compatible endpoint abstraction with per-layer model selection.** Defaults to local Ollama. | Commercial APIs will refuse this setting's narrative content. Local-first is a functional requirement, not a preference. |
| D7 | **Sexual state is a mechanic, persona is material.** `sexual_baseline` is typed and simulated; `persona` is opaque and only ever injected into prompts. | The engine models what it must compute and stores the rest verbatim. |
| D8 | **Sexual state feeds the combat modifier table.** High arousal degrades agility and accuracy; climax-in-progress zeroes actions. | Explicitly requested. Shares one modifier pipeline with poison and paralysis — no special-case branches. |
| D9 | **`world/lore/` is Python; `world/rules/rulebook/` is YAML.** | Lore is a versioned single source of truth that deserves code review. Balance numbers are data that should be tunable without touching Python. |
| D10 | **Scene art is keyed by archetype, not by room.** A tavern in the capital and a tavern in a border town share one image. | GPU cost scales with scene *kinds*, not room count. Style stays consistent for free. |
| D11 | **The engine never calls Stable Diffusion.** It maintains a queue and shells out to a configurable worker command. | Keeps the engine free of GPU concerns and lets the prompt-writing agent be swapped without touching engine code. |

---

## 3. System Architecture

### 3.1 Layers and the single-writer rule

```
┌─ Presentation ───────────────────────────────┐
│  WebClient / GoldenLayout / OOB push          │  read-only
└───────────────────────────────────────────────┘
┌─ Generative  (world/ai/) ────────────────────┐
│  ScenarioDirector   SceneBuilder              │  reads state
│  Narrator           NPCDialogue               │  emits proposals only
└───────────────────────────────────────────────┘
              ↓ every proposal passes guardrail ↓
┌─ Deterministic Core  (world/rules/) ─────────┐
│  ActionResolver  Combat  Dice  Clock          │  SOLE WRITER
│  Traits  SexualState  Buffs  Quest  Economy   │
└───────────────────────────────────────────────┘
              ↓
        Django ORM / SQLite
```

**Invariant.** No module under `world/ai/` may import a state-mutating API. This is enforced by
module dependency direction and checked in CI with an import-linter contract. The generative layer
changes the world by exactly one route: emit a schema-valid proposal, let `world/rules/` apply it.

### 3.2 Directory layout

```
mygame/
├── typeclasses/
│   ├── entities.py      LivingEntity base (characters and monsters share it)
│   ├── characters.py    PlayerCharacter
│   ├── npcs.py          NPC / LLMNPC
│   ├── rooms.py         AnchorRoom / GridRoom / InstanceRoom
│   └── objects.py       Item / Equipment
├── world/
│   ├── lore/            static world data derived from world_info
│   │                    geography · factions · races · magic · economy · bestiary
│   │                    sexual_vocab   ordered-level vocabularies (owned by change 4,
│   │                                   consumed by change 7 — frozen with the contract)
│   ├── rules/           deterministic engine — SOLE WRITER
│   │                    dice · combat · action · targeting · clock
│   │                    traits · sexual_state · buffs · progression
│   │                    rulebook/   declarative rule tables (YAML)
│   ├── skills/          registry (SkillDef definitions) · handler · equipment
│   │                    Own package rather than under lore/ or rules/, because
│   │                    skills carry both static definitions and resolution
│   │                    behaviour. Path forward-declared by change 4.
│   ├── quests/          blueprint · runtime
│   ├── ai/              client · profiles · schemas/
│   │                    director · scene · narrator · npc_dialogue · guardrail
│   ├── imports/         schema (age gate) · validate CLI · loader · examples/
│   └── art/             archetypes · queue · worker · scheduler · store
├── commands/
└── web/
```

### 3.3 Data flow for one player command

```
command input
  → ActionResolver      parse action + targets
  → targeting           validate presence / alive / range / faction
  → rules               roll, resolve, write state, advance clock
  → EventLog            structured events (rolls, damage, transitions, time cost)
      ├→ Narrator       EventLog → Traditional Chinese prose (pure function)
      └→ art.queue      if the scene archetype has no image, enqueue
  → player sees text; image arrives later via OOB if generated
```

`EventLog` is the load-bearing seam. It decouples narration from state entirely, and it is
replayable, testable, and renderable by a hand-written template when the LLM is unavailable.

---

## 4. Contrib Reuse Matrix

The deterministic core is a thin, setting-specific layer sitting on Evennia contribs — not a
from-scratch engine.

| Our module | Underlying contrib / core module | Strategy |
|---|---|---|
| `rules/traits.py` | `evennia.contrib.rpg.traits` — `TraitHandler`, `Trait`, `StaticTrait`, `CounterTrait`, `GaugeTrait` | **Use directly.** Define the setting's trait set only |
| `rules/sexual_state.py` | `evennia.contrib.rpg.traits` — no ordered/enum trait class ships. Author a new `Trait` subclass (see `CounterTrait`'s `descs` mapping — numeric-bucket-to-label — for the closest built-in precedent) and register its dotted path in `settings.TRAIT_CLASS_PATHS`, the same mechanism the contrib's own example custom trait (`RageTrait`, registered as `world.traits.RageTrait`) uses | **Extend, not subclass-of-existing.** There is nothing named `OrderedLevelTrait` to reuse; the ordered-level trait type must be written from scratch on top of `Trait` |
| `rules/buffs.py` | `evennia.contrib.rpg.buffs` — `BuffHandler`, `BaseBuff` | **Use directly.** Duration/tick/stacking are done |
| `typeclasses/entities.py` | `evennia.contrib.base_systems.components` — `Component`, `ComponentHolderMixin`, `ComponentProperty` | **Use directly.** `QuestGiver` / `Merchant` / `GuildStaff` are project-authored `Component` subclasses; Evennia ships the base class, not these names |
| Map · grid layer | `evennia.contrib.grid.xyzgrid` — `XYZRoom`, `XYZExit` (module `xyzgrid/xyzroom.py`) | **Use directly.** XYZRoom, ASCII maps, shortest path, FOV minimap |
| Map · virtual layer | `evennia.contrib.grid.wilderness` — `WildernessMapProvider` (module `wilderness/wilderness.py`) | **Extend.** Subclass `WildernessMapProvider`; the contrib ships a worked example subclass, `PyramidMapProvider`, to model the override points on |
| Map · instance layer | `evennia.prototypes.spawner` — **this is core Evennia, not a contrib module; do not look for it under `evennia.contrib`** | **Use directly.** `spawn(*prototypes, caller=None, **kwargs)` on SceneBuilder output |
| `ai/client.py` | `evennia.contrib.rpg.llm` — `LLMClient` (module `llm.py` → `llm_client.py`; built on Twisted's `protocol.Protocol` / HTTP11 client factory) | **Subclass.** Keep the Twisted async skeleton; override payload for `/v1/chat/completions` |
| `ai/npc_dialogue.py` | `evennia.contrib.rpg.llm` — `LLMNPC(DefaultCharacter)` (module `llm_npc.py`) | **Subclass.** Chat memory, prompt priority chain, thinking state are done |
| `rules/combat.py` | `evennia.contrib.tutorials.evadventure` — **corrected path; it is not under `contrib.rpg`** (`EvAdventureRollEngine` in `rules.py`, `CombatAction` subclasses and `EvAdventureCombatBaseHandler` in `combat_base.py`) | **Reference only.** It is d20 (confirmed: `EvAdventureRollEngine.roll()` rolls `1d20`/`2d20` against a target of 15); we are linear. Borrow its *structure*, not its *formulas* |
| `rules/dice.py` | `evennia.contrib.rpg.dice` — `roll()` (module `dice.py`) | **Use directly** for the d100 roller — `roll(1, 100, ...)` or the string form `"1d100"` |
| Front-end panel | WebClient GoldenLayout — `evennia/web/static/webclient/js/plugins/goldenlayout_default_config.js` (path confirmed) | **Configure + plugin.** Edit `goldenlayout_default_config.js`, add an OOB receiver |

> **Verified.** Confirmed 2026-07-29 against Evennia **6.1.0** (`pip install evennia`; requires
> Python >=3.12, imports and CLI both verified in an isolated venv) — the version that was actually
> installed, superseding the unverified matrix that previously stood here (sourced from
> `tmp/evennia.md`, a secondary research document). Three corrections were made against that
> document: (1) `evadventure` lives under `contrib.tutorials`, not `contrib.rpg`; (2) no
> `OrderedLevelTrait` class exists anywhere in Evennia — `sexual_state.py` must author its own
> ordered-level `Trait` subclass and register it via `settings.TRAIT_CLASS_PATHS`; (3)
> `prototypes.spawner` is core Evennia, not a contrib module. Also confirmed accurate and unchanged:
> default ports (telnet 4000, webserver 4001, websocket 4002, matching §9), the
> `evennia --init <name>` project skeleton (`commands/`, `server/`, `typeclasses/`, `web/`,
> `world/`), and all other module paths and class names in the table above. One operational nuance
> for §9: `evennia start --log` does not make the server write directly to stdout — `start` still
> daemonizes Portal+Server writing to `server/logs/*.log` as usual, and `--log` separately tails
> those files and streams them to stdout, blocking the foreground process. The `server/logs` volume
> mount in §9 is therefore load-bearing, not optional, even when running with `--log`.

---

## 5. Data Model

### 5.1 Lore (`world/lore/`)

Frozen dataclasses in module-level registries, synced idempotently into the DB at startup, keyed
by `key`.

`RaceProfile` is where the three-orders-of-magnitude gap is encoded, and every consumer
(overwhelm threshold, guild-rank sanity checks, import range validation) reads it rather than
hardcoding magic numbers:

```python
@dataclass(frozen=True)
class RaceProfile:
    key: str                    # human / beastfolk / elf
    lifespan: tuple[int, int]
    magic_cap: int              # human 90 | beastfolk 30 | elf 900
    vital_baseline: Vitals      # human 100 | beastfolk HP/SP 150-200 MP 30-50 | elf 10000
    static_baseline: StaticBand # atk_phys / agility / defense band — see below
    learning_multiplier: float  # elf 10.0
    can_use_divine_arts: bool   # elf only
```

**Vital pools and static stats scale by different factors, and neither may be derived from the
other.** Pools scale ~100× from human to elf (120-150 → 10000); static combat stats scale ~10×
(human elite 8 → elf 88), matching `world_info.md`'s "身體素質為人類精銳戰士的 10 倍". Magic level
likewise scales 10× (cap 90 → 900). Reference points taken from the sample cards:

| | human elite | human non-combatant | elf | ratio |
|---|---|---|---|---|
| `atk_phys` / `agility` / `defense` | 8 / 9 / 7 | 5 / 6 / 6 | 88 / 92 / 90 | ~10× |
| `magic_level` cap | 90 | 90 | 900 | 10× |
| `hp` | 120 | 150 | 10000 | ~100× |

The asymmetry is deliberate: elves are absurdly durable but "only" ten times as damaging, which is
why `hp` is an input to `effective_power()` — a stat-only ratio would not flag an elf-versus-human
fight as overwhelming even though the human cannot win.

**Skill multipliers are a third, independent layer** applied on top of base stats at resolution
time: ×10 (統御術 partial effect), ×100 (身體強化), ×1000 (身體超強化). They are never baked into
stored stats.

Other registries: `Element` (eight elements), `MagicTier` (初級→究極), `RankTitle`
(學徒→術師→大師→賢者→主宰), `Nation` (three states), `GuildRank` (F→S with reward bands),
`MonsterTier` (F-E / D-C / B-A / 災厄級), `Anchor` (capitals, the three elven villages, known
dungeon entrances).

**Currency is stored as an integer count of 銅.** 1 金 = 100 銀 = 10000 銅. Conversion happens only
at display time. No floats anywhere in the money path.

> **Corrected 2026-07-29.** `world_info.md` originally stated `1金=10銀=100銅`, but that rate is
> inconsistent with the same document's own reward and price tables: it collapses the F-rank band
> (`10銅-1銀`) and the C-rank band (`50銀-5金`) to single points, and it puts a commoner's annual
> income (5-10 金) at roughly one tenth of their annual food cost (3 meals/day at 5-10 銅). At
> `1金 = 100銀 = 10000銅` all seven guild bands are non-degenerate and form a clean ten-fold ladder
> (F 10-100 → S 5,000,000+), and the price table becomes internally coherent. The exchange-rate line
> was the outlier and has been corrected in `world_info.md` as well.

### 5.2 Entities

```
LivingEntity                       shared by characters and monsters
├── traits       TraitHandler      deterministic stats
├── sexual       SexualState       sexual state machine
├── buffs        BuffHandler       status effects
├── equipment    EquipmentHandler  equipment slots
├── skills       SkillHandler      active / passive skills
├── relations    RelationHandler   affinity
└── persona      PersonaStore      narrative layer (opaque)

PlayerCharacter(LivingEntity)  + guild rank, quest log, wallet
NPC(LivingEntity)              + dialogue memory, schedule
Monster(LivingEntity)          + threat tier, loot table, behaviour tree
```

Trait types: `hp/mp/sp` are **gauges** (max + regen rate); `atk_phys/agility/defense` are **static**
(base + mod); `magic_level/guild_merit` are **counters**.

Per D2, `disguised_stats` lives in a separate attribute read by exactly three consumers: appearance
rendering, guild registration records, and appraisal items.

```python
@dataclass(frozen=True)
class SkillDef:
    key: str
    kind: SkillKind             # ACTIVE / PASSIVE
    target_spec: TargetSpec     # SELF / SINGLE / AREA / NONE
    cost: dict[str, int]        # {"mp": 20, "sp": 5}
    usable_out_of_combat: bool  # 飛行術, 身體強化, 狀態偽裝 → True
    element: Element | None
    effects: list[str]          # effect IDs resolved against rulebook YAML
```

A skill does not know whether it is in combat. `ActionResolver` is the sole entry point; the combat
turn scheduler and the out-of-combat command both call it.

`PersonaStore` does three things and nothing else: persist imported fields verbatim, retrieve by
key, flatten into prompt blocks. It never interprets content.

### 5.3 Import contract

Frozen at change 4 and handed to the import implementer.

```
world/imports/
├── schema.py       CHARACTER_SCHEMA_V1 / WORLD_SCHEMA_V1
├── validate.py     CLI: python -m world.imports.validate cards/*.json
├── loader.py       instantiate only after validation passes
└── examples/       one valid reference card
```

```jsonc
{
  "schema_version": 1,
  "key": "example_character",
  "display_name": "…",
  "age": 22, "apparent_age": 22,
  "race": "elf", "subrace": "ciaran",

  // Base values only. Skill multipliers (×10 / ×100 / ×1000) are applied at
  // resolution time and must never be baked in here.
  "stats":           { "hp": 10000, "atk_phys": 88, "agility": 92, "magic_level": 250 },
  "disguised_stats": { "atk_phys": 60, "magic_level": 30 },

  "skills":   ["fire_mastery", "flight", "status_disguise"],
  "passives": ["defense_instinct"],
  "equipment": {},
  "inventory": [],

  "sexual_baseline": { "arousal": "微興奮", "sensitivity": {}, "virgin": true },

  "persona": { "identity": {}, "personality": {}, "life_story": {},
               "habit": [], "appearance": {}, "social_connection": {} }
}
```

| Check | On failure |
|---|---|
| `age >= 18` **and** `apparent_age >= 18` | **Reject** |
| `race` / `subrace` exists in the lore registry | **Reject** |
| every `skills` key exists in the skill registry | **Reject** |
| `disguised_stats` keys are a subset of `stats` keys | **Reject** |
| `stats` fall inside the race's plausible band | Warn (prodigies legitimately exceed it) |
| `persona` is a dict | Type only; contents never inspected |

Import is **all-or-nothing**. Failure reports which record, which field, and why. No partial import.

---

## 6. Rules Engine

### 6.1 ActionResolver

```
ActionRequest(actor, skill_key, targets[], context)
  1. skill ownership
  2. resource check           mp / sp
  3. target resolution        → targeting
  4. action capability        buffs forbidding action (paralysis, bind, climax-in-progress)
  5. effect resolution        driven by rulebook
  6. resource deduction
  7. EventLog emission
  8. time cost                → WorldClock
```

Any step may reject with a named reason. Resolution is **atomic** — a mid-pipeline failure rolls
back completely. "Mana spent but the skill did nothing" must be unreachable.

### 6.2 Targeting

```python
class TargetSpec(StrEnum):
    NONE      # no target
    SELF      # self only
    SINGLE    # any present entity, including self
    AREA      # multi-select
```

Four validations: **presence** (same room or battlefield) → **alive** → **range** →
**faction constraint** (`ANY / ALLY / ENEMY / SELF_ONLY`).

In combat, `all-enemies`, `all-allies`, and `all` are shortcuts that expand into an explicit target
list and then pass the same four validations. They bypass nothing.

Out of combat there is no hostility model, so `SINGLE` may target anyone present. This is why
support magic on an ally, self-buffing, and sexual magic on a companion in an inn all work without
special cases.

### 6.3 Combat

```
engage → initiative order (agility-dominant + d100 jitter)
  ↓
turn loop
  ├ each combatant acts (player waits for input / AI runs behaviour tree)
  ├ buff ticks
  └ sexual state decay and transitions
  ↓
end (wipe / flee / special condition)
  ↓
time settlement: rounds × 6s → WorldClock
```

Formulas live in `rulebook/combat.yaml`:

```
effective_power = f(atk_phys, agility, defense, magic_level, hp)

overwhelm check (at engage AND recomputed every round)
  ratio >= 100    → single-shot resolution, ends in one round
  ratio <= 0.01   → reverse overwhelm, player is one-shot
  otherwise       → per-round rolls

to-hit   d100 + attacker agility   vs   60 + defender agility
damage   (atk_phys × roll multiplier) − defender defense, floor 1
```

Overwhelm **compresses** combat, it does not skip it: a full EventLog is still produced so the
Narrator can write the corresponding prose. Recomputing every round handles mid-fight power-tier
shifts, such as dropping a disguise.

### 6.4 Sexual state machine

```python
class SexualState:
    # ordered levels — project-authored Trait subclass, not numeric.
    # Evennia ships no ordered/enum trait type; see §4 for the registration mechanism.
    arousal       平靜 → 微興奮 → 中等 → 高度 → 極限
    wetness       乾燥 → 微濕 → 濕潤 → 大量 → 泛濫
    shame         無 → 輕微 → 中等 → 強烈 → 成癮
    exposure      極低 → 低 → 中等 → 高 → 極高
    climax_phase  未達 → 接近 → 進行中 → 餘韻
    sensitivity   dict[part, 普通 → 高 → 極高 → 敏感異常]

    climax_today      int              reset daily
    virgin            bool             one-way, irreversible
    experience_types  frozenset[str]   append-only
```

Transitions are declarative in `rulebook/sexual.yaml`. Every rule has an ID; every ID has a unit
test:

```yaml
- id: arousal_up_on_stimulus
  when: { event: stimulus_applied }
  then: { field: arousal, delta: "+1..+2" }

- id: wetness_follows_arousal
  when: { field_changed: arousal, direction: up }
  then: { field: wetness, delta: "+1" }

- id: climax_gate
  when: { field: arousal, equals: 極限 }
  then: { field: climax_phase, set: 接近 }

- id: virginity_once
  when: { event: first_vaginal_penetration }
  then: { field: virgin, set: false, irreversible: true }
```

Buffs modify exactly three things: **rate of change**, **clamped bounds**, and **decay rate**.
Sexual magic is a skill that applies such a buff; it travels the identical `ActionResolver` path as
a fireball, differing only in which field the effect targets.

Combat coupling lives in `rulebook/combat_modifiers.yaml`, in the same table as poison and
paralysis:

```yaml
- when: { field: arousal, gte: 高度 }
  then: { agility: "-20%", accuracy: -15 }

- when: { field: climax_phase, equals: 進行中 }
  then: { actions_per_turn: 0 }
```

Monsters are `LivingEntity` and therefore have `SexualState` too; baselines come from the bestiary,
with most monsters at 普通 sensitivity and `shame` clamped to 無.

### 6.5 World clock

```python
class WorldClock:
    tick: int
    calendar: WorldDateTime

    def advance(self, seconds: int) -> list[ScheduledEvent]:
        """Advance and return every event that came due."""
```

Three advance sources: **command defaults** (move 30s, converse 60s, cast 6s), **combat settlement**
(rounds × 6s), and **explicit skips** (`rest 1h`, `sleep`, `wait until dawn`).

Due events settle in a **fixed order**, because order changes outcomes: HP/MP/SP regen → buff
durations → sexual state decay → daily resets (`climax_today`) → caravan arrivals → shop hours →
quest deadlines → NPC schedules.

Explicit skips are gated: reject or shorten if the player is in combat, targeted by a hostile, or
in an unsafe location. Otherwise players will `sleep 8h` in front of a monster.

---

## 7. Generative Layer

### 7.1 ScenarioDirector — emits requirements, not entities

The Director says "I need a forest-path scene and a frightened civilian." It never says "create
room #1234."

```jsonc
{
  "name": "…",
  "type": "探索",              // 採集 / 討伐 / 護衛 / 探索 / 緊急
  "rank": "D",
  "issuer": "guild_branch_…",
  "stages": [{
    "index": 0,
    "objective":    { "kind": "reach_location" },
    "location_req": { "layer": "instance", "archetype": "forest_path",
                      "anchor_near": "…", "scene_sentence": "…" },
    "npc_req":      [{ "role": "victim", "tier": "civilian",
                       "disposition": "frightened" }]
  }],
  "reward":  { "copper": 3000, "items": [], "merit": 50 },
  "failure": { "deadline_hours": 72, "conditions": [] }
}
```

Because the output is requirements, it is **fully validatable before it touches the DB**: rank
legality, reward inside the `GuildRank` band for that rank, archetype known, NPC tier known, stage
indices contiguous. Invalid output is retried or clamped rather than discovered post-corruption.

### 7.2 SceneBuilder — requirements to prototypes

Triggered when the player actually arrives, not when the quest is accepted. Emits a prototype dict
for `spawner.spawn()`.

**The anti-hallucination rule: the LLM never chooses numbers.** It supplies `stats_tier:
"civilian"`; the actual HP/attack/defense come from the lore tier table. `prototype_parent` must
come from a whitelist. There is no path by which an LLM writes "this goblin has 99999 HP."

### 7.3 Narrator — pure function

`EventLog → Traditional Chinese prose`. It has no access to a write API (enforced by dependency
direction), returns plain text, and is never parsed back.

**If the Narrator fails, the game remains fully playable**, with prose degraded to template
rendering. This is an acceptance criterion.

### 7.4 NPC dialogue and intent extraction

```jsonc
{
  "speech": "…",
  "intent": { "kind": "give_item", "item_key": "healing_potion", "qty": 1 }
}
```

Intent whitelist: `give_item` / `take_item` / `offer_quest` / `adjust_relation` / `reveal_lore` /
`none`. The engine verifies the NPC actually holds the item and may issue the quest. **Illegal
intent is discarded while the speech is kept** — the NPC said something it could not do, but the
world was not changed. That is the accepted failure mode.

NPC prompts are injected with `disguised_stats`, so NPCs genuinely underestimate a disguised elf.
The narrative payoff falls out of D2 for free.

### 7.5 Guardrail and degradation

```
1. response_format / json_schema     only when the endpoint supports it
2. local jsonschema validation
3. semantic validation               rank / reward / archetype / whitelists
      ↓ fail
   retry N times with the error message appended
      ↓ still failing
   degrade
```

| Layer | Degradation |
|---|---|
| ScenarioDirector | draw from a hand-written quest template pool |
| SceneBuilder | generic room template for that archetype |
| Narrator | template-render the EventLog |
| NPCDialogue | fall back to greeting or silence |

**The game must remain playable with the LLM entirely offline.** This is an acceptance criterion,
not an aspiration.

---

## 8. Scene Art Pipeline

Keyed by archetype (D10). The engine never calls SD (D11).

```
SceneArchetype registry
  key             "tavern_interior"
  scene_sentence  one-sentence natural-language scene description
  image           path | None

room → references archetype → registry lookup
   ↓ missing
art/queue          engine's only job: track which archetypes lack images
   ↓
external worker    reads queue → writes full prompt → runs SD → stores → writes back
   ↓
any room referencing that archetype hits the cache
```

**Worker contract** — the swap point:

```python
ART_WORKER_CMD = ["python", "-m", "tools.art_worker"]
# stdin  ← [{archetype, scene_sentence, out_path}, …]
# stdout → [{archetype, status, path, error}, …]
```

Replacing the worker with an agent-driven prompt builder, or with a direct sd-webui client, changes
`ART_WORKER_CMD` and nothing else.

| Command | Behaviour |
|---|---|
| `@art status` | queue state: pending / done / failed |
| `@art run [--limit N]` | drain now, asynchronously, never blocking play |
| `@art retry` | retry failed entries |
| `@art requeue <archetype>` | force regeneration |

A scheduler Script drains periodically (settings-configurable, disableable). The worker is
serialized — one job at a time, queue locked — so overlapping schedules cannot saturate the GPU.
Completed entries are idempotent and never regenerate.

OOB push on room entry when an image exists; otherwise the panel keeps the previous image or shows
a placeholder.

---

## 9. Containerization

```
Containerfile     multi-stage, non-root, arbitrary-UID capable
compose.yaml      evennia + volumes; ollama and sd-webui reached over the network
.dockerignore
```

- **Multi-stage.** Builder installs dependencies with BuildKit cache mounts; runtime carries only
  the venv and application code.
- **Non-root with arbitrary UID.** Group 0 writable, OpenShift-compatible, and no root-owned files
  when run locally.
- **Python floor is 3.12**, set by Evennia 6.1.0. Do not target 3.11.
- **Evennia is two processes** (Portal + Server). `evennia start --log` daemonizes both and writes
  to `server/logs/*.log`; the `--log` flag then tails those files to stdout and blocks in the
  foreground. It does **not** redirect logging away from disk, so the `server/logs` volume is
  load-bearing rather than optional.
- **Ports.** 4000 telnet, 4001 webserver, 4002 websocket.
- **Volumes.** SQLite DB, scene art store, `server/logs` (required — see above).
- **GPU services stay outside.** Ollama and sd-webui are reached via environment variables or
  `extra_hosts`; the image needs no GPU runtime and stays small.

Authored to the `containerfile-creator` skill's standards.

---

## 10. Testing Strategy

| Area | Method |
|---|---|
| `rulebook/` rules | **One test per rule ID.** Test names mirror rule IDs one-to-one |
| Dice and combat | Fixed seed, deterministic assertions; golden cases for both overwhelm and normal combat |
| Clock and scheduling | Assert settlement order after a skip (regen → buffs → sexual → resets → world events) |
| Evennia integration | `EvenniaTest` base: rooms, exits, spawn, commands |
| Generative layer | **`FakeLLMClient` replays fixed JSON. Tests never hit a real endpoint** |
| Guardrail | Feed malformed, out-of-range, and adversarial JSON; assert the DB is untouched |
| Import contract | An age-17 record **must** be rejected — a permanent regression test |
| Offline playability | Set every `LLM_PROFILES` entry to fail; a full accept-quest → fight → turn-in loop must complete |

---

## 11. Implementation Roadmap

One change per working day. Dependencies are listed; the rest may run in parallel.

### Phase 0 — Foundation

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `bootstrap-container-evennia` | — | Containerfile, compose, Evennia skeleton, connectable server. **Verify every contrib API signature and correct §4 in place.** |
| 2 | `lore-world-data` | 1 | Races, elements, magic tiers, rank titles, nations, guild ranks, currency, monster tiers, anchors; idempotent startup sync |

### Phase 1 — Entities and stats

| # | Change | Depends on | Content |
|---|---|---|---|
| 3 | `entity-traits` | 1, 2 | `LivingEntity`, TraitHandler mounting, race-driven scales, disguise display layer |
| 4 | `import-contract` | 3 | JSON Schema with the age gate, validate CLI, reference example, loader. **Frozen and handed off after this change.** |
| 5 | `skills-equipment` | 3 | SkillDef registry, SkillHandler, equipment slots, inventory |
| 6 | `buffs-rulebook` | 3 | BuffHandler integration, rulebook rule-engine skeleton, modifier table |

### Phase 2 — Rules core

| # | Change | Depends on | Content |
|---|---|---|---|
| 7 | `sexual-state` | 6 | Ordered-level `Trait` subclass (authored from scratch, registered via `settings.TRAIT_CLASS_PATHS`), the `SexualState` handler, character and monster baselines, the decay callable. Flips change 6's self-arming test. |
| 7b | `sexual-transition-rules` | 7 | `sexual.yaml` — ~25 transition rules transcribed from `variable_rule.md` into change 6's condition grammar, each with a matching per-rule test. Split from change 7 because the rule-plus-test surface alone fills a working day. |
| 8 | `action-resolver` | 5, 6 | ActionResolver, targeting, out-of-combat skill use |
| 9 | `dice-combat` | 8 | d100 resolution, damage, initiative, turn loop |
| 10 | `overwhelm-resolution` | 9 | Overwhelm threshold, single-shot resolution, EventLog compression |
| 10b | `monster-behaviour` | 9, 10 | Monster combat AI. `Monster.behaviour_tree` has been an unbuilt seam since change 3; change 9 supplies only a labelled placeholder that attacks the lowest-hp enemy. The change-16 milestone claims a complete playable game, which needs monsters that fight sensibly. |
| 11 | `world-clock` | 7, 9 | Clock, scheduled events, time-skip commands, safety gate |
| 11b | `character-progression` | 5, 6, 11 | XP, magic-level growth, skill improvement, and the consumer for conferred growth-rate multipliers. §3.2 lists `rules/progression` but no change owned it; surfaced by change 6, which built `growth_rate_multiplier()` with nothing to call it. Guild merit and rank remain change 16's. |

### Phase 3 — World space

| # | Change | Depends on | Content |
|---|---|---|---|
| 12 | `map-anchor-grid` | 2, 3 | Anchor sync, xyzgrid grid layer, one sample city |
| 13 | `map-wilderness` | 12 | `WildernessMapProvider`, terrain description |
| 14 | `map-instance` | 12 | Instance TTL reclamation, promotion of named rooms |

### Phase 4 — Quests and economy

| # | Change | Depends on | Content |
|---|---|---|---|
| 15 | `quest-runtime` | 11, 14 | Quest entity, stage progression, completion and failure |
| 16 | `guild-economy` | 15 | Guild ranks, merit, reward settlement, shops and prices |

### Phase 5 — Generative layer

| # | Change | Depends on | Content |
|---|---|---|---|
| 17 | `llm-client` | 1 | `OpenAICompatClient`, `LLM_PROFILES`, guardrail skeleton, `FakeLLMClient` |
| 18 | `narrator` | 10, 17 | EventLog → prose, template degradation |
| 19 | `npc-dialogue` | 17 | LLMNPC subclass, intent whitelist |
| 20 | `scenario-director` | 15, 17 | QuestBlueprint schema, validation, hand-written template pool |
| 21 | `scene-builder` | 14, 20 | Requirements → prototype → spawn, whitelists |

### Phase 6 — Multimodal and front-end

| # | Change | Depends on | Content |
|---|---|---|---|
| 22 | `art-queue` | 12, 14 | Archetype registry, queue, worker contract, `@art` commands, scheduler |
| 23 | `webclient-panel` | 22 | GoldenLayout config, OOB receiver plugin |

**Critical path:** `1 → 2 → 3 → 6 → 8 → 9 → 10 → 15 → 20 → 21`

**Milestones**

- **After change 4** — the import contract is frozen; the import implementer can start.
- **After change 16** — a complete, playable game with **no LLM at all**: hand-written quests, real
  combat, guild progression, elapsing time. This is the last moment at which combat feel and
  numeric balance can be validated without generative nondeterminism.
- **After change 21** — the AI Director is live; story generation is unbounded.

**Ordering rationale.** The deterministic layer is finished before any LLM work begins, because
every generative schema describes how to manipulate deterministic entities. Designing those schemas
against undefined entities is guesswork.
