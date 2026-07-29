## Context

This is roadmap item #2 (design doc §11), depending on change 1 (`bootstrap-container-evennia`),
which provides the Evennia project skeleton, the pinned Evennia 6.1.0 dependency, and the
`world/lore/` empty-stub package. No code exists yet for this change's scope — `world/lore/` is
currently an empty package per change 1's task 2.2.

The source data is `tmp/story_settings/world_info.md`: free-form Traditional Chinese, YAML-shaped
but not schema-validated, gitignored, and never committed. This change's job is narrow — convert
that prose into frozen dataclasses per design doc §5.1 and D9 ("`world/lore/` is Python, not
YAML"), and sync them idempotently into the DB, keyed by `key`. It does not implement any consumer
of this data (combat overwhelm thresholds, import validation, quest reward checks) — those are
changes 3, 4, 9, 10, and 16's jobs, each reading these registries rather than hardcoding numbers.

## Goals / Non-Goals

**Goals:**
- Typed, frozen-dataclass registries for every category design doc §5.1 names:
  `RaceProfile`, `Element`, `MagicTier`, `RankTitle`, `Nation`, `GuildRank`, `MonsterTier`,
  `Anchor`, plus a currency/price-table module — all derived faithfully from `world_info.md`.
- A `Subrace` registry (not named in §5.1, but required by the import contract's own reference
  example, which already assumes `subrace: "ciaran"` resolves against something) covering the
  three elf branches and the seven named beastfolk subspecies.
- An idempotent startup sync that mirrors every registry entry into the DB, keyed by `key`, safe
  to run on every server start with no duplication.
- A self-consistency test suite over the registries themselves (band contiguity, race power-gap
  assertion, currency arithmetic, sync idempotency).

**Non-Goals:**
- No consumer logic. The overwhelm threshold (change 10), guild-rank reward *validation*
  (change 16 / change 20's ScenarioDirector), and import range checks (change 4) are not
  implemented here — only the data they will read.
- No `LivingEntity`, `TraitHandler`, or any runtime entity state (change 3).
- No Rooms, no `XYZRoom` grid entries for the anchors listed here — `Anchor` is pure lore data;
  turning an anchor into a walkable room is change 12 (`map-anchor-grid`)'s job.
- No YAML lore format. D9 is explicit that `world/lore/` is Python; this change does not introduce
  a parallel YAML representation of any registry defined here.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users, and `world/lore/` currently doesn't exist beyond an empty stub.
- No sexual-state or character-level data of any kind (`sexual_baseline`, `persona`) — that is
  change 7's scope per the task framing; this change models geography, races, nations, magic, the
  economy, and monsters only.

## Decisions

### D-1. `RaceProfile` uses exactly the six fields design doc §5.1 gives, no more.

```python
@dataclass(frozen=True)
class RaceProfile:
    key: str                    # "human" | "beastfolk" | "elf"
    lifespan: tuple[int, int]
    magic_cap: int
    vital_baseline: Vitals
    learning_multiplier: float
    can_use_divine_arts: bool
```

Three entries only, matching §5.1 verbatim. Display names, population figures, and social-structure
notes from `world_info.md` are deliberately **not** added as extra fields here — the task calls
this "the load-bearing one" that every consumer reads magic numbers from, and the design doc gives
an exact field list. Adding descriptive fields nobody reads risks the dataclass drifting from the
contract other changes design against. Values:

| key | lifespan | magic_cap | learning_multiplier | can_use_divine_arts |
|---|---|---|---|---|
| human | (60, 80) | 90 | 1.0 | False |
| beastfolk | (50, 70) | 30 | 1.0 | False |
| elf | (800, 1200) | 900 | 10.0 | True |

`magic_cap` and `learning_multiplier` for elf are given directly in §5.1's own comment (90 / 30 /
900 and 10.0). `learning_multiplier` for human and beastfolk has no number in either source
document — **judgment call**: default both to `1.0` (the implicit baseline elf's 10x is measured
against), documented here rather than silently invented.

### D-2. `Vitals` stores a `(baseline, gifted_ceiling)` band per stat, not a single number.

```python
@dataclass(frozen=True)
class Vitals:
    hp: tuple[int, int]
    mp: tuple[int, int]
    sp: tuple[int, int]
```

§5.1's inline comment shorthands this as single numbers ("human 100 | elf 10000"), but
`world_info.md` gives human and beastfolk each a baseline **and** a gifted ceiling ("100為基準，
天賦者可達150-200"; beastfolk "150-200" HP/SP vs "30-50" MP). A `(min, max)` tuple per stat is the
natural encoding both races share, and it is exactly the shape import range validation (design doc
§5.3, "stats fall inside the race's plausible band → Warn") will want to read against.

| race | hp | mp | sp |
|---|---|---|---|
| human | (100, 200) | (100, 200) | (100, 200) |
| beastfolk | (150, 200) | (30, 50) | (150, 200) |
| elf | (10000, 10000) | (10000, 10000) | (10000, 10000) |

**Judgment call on elf**: `world_info.md` states elves don't perceive precise values below their
own order of magnitude ("在這個位數之下他們感受不到零頭數值，故無準確數字意義"), so there is no
documented gifted range to encode — a fixed `(10000, 10000)` is used as a canonical reference
point, not a hard ceiling. This is intentionally consistent with the import contract's own
reference example, which imports an elf with `hp: 10000` but `atk_phys: 88000` — i.e., individual
elf stats are expected to exceed this baseline by orders of magnitude for prodigies, and the import
check for out-of-band stats is a **warning**, not a rejection (§5.3), precisely because elf values
are not meant to be tightly bounded.

### D-3. `Subrace` is a new, generic registry — not folded into `RaceProfile`.

The task calls out that elves have three sub-branches and asks how subrace should be modelled.
`RaceProfile` stays at exactly three entries (D-1), so subrace needs its own registry:

```python
@dataclass(frozen=True)
class Subrace:
    key: str                       # e.g. "ciaran", "wolfkin"
    race_key: str                  # references RaceProfile.key
    display_name_zh: str           # e.g. "基亞蘭族"
    common_name_zh: str            # e.g. "黑暗精靈"
    population: int | None         # None where world_info gives no figure
    home_anchor_key: str | None    # references Anchor.key; elf branches only
    affinity_elements: tuple[str, ...]  # references Element.key; empty if none documented
    specialty: str                 # short English note, e.g. "excels at blade arts"
```

`SUBRACE_REGISTRY: dict[str, Subrace]` holds ten entries:

- Elf branches (all three have a home village and documented elemental affinity):
  `fionnen` (斐歐恩族/森林精靈, population 120, home `village_fionnen`, affinity `("light",)`),
  `ciaran` (基亞蘭族/黑暗精靈, population 100, home `village_ciaran`, affinity `("fire", "dark")`),
  `eolas` (伊歐拉斯族/幻童精靈, population 80, home `village_eolas`, affinity all eight elements
  plus divine-arts access — encoded as the full `ELEMENT_REGISTRY` key tuple).
- Beastfolk subspecies (`race_key="beastfolk"`, `home_anchor_key=None` — `world_info.md` does not
  tie any beastfolk subspecies to a specific settlement, only to Valhalla's territory generally,
  and `population=None` for all seven since the source gives no per-subspecies count, only
  qualitative rank like "最多"): `wolfkin` (狼人, most numerous, team combat), `catkin` (貓人,
  agile, assassination/scouting), `bearkin` (熊人, strongest, heavy weapons), `rabbitkin` (兔人,
  fastest, archery), `bovinekin` (牛人), `tigerkin` (虎人), `foxkin` (狐人) — the last three are
  `world_info.md`'s "其他" catch-all, listed individually rather than as one combined "other" entry
  so import validation (`subrace exists in the lore registry`, §5.3) can resolve any of them without
  a special-cased fallback key.

**Judgment call on required-ness**: the import contract's reference example only sets `subrace` for
the elf record; human records presumably omit it. `subrace` is modelled as optional at the import
layer (change 4's concern, not this change's), but *when present* it SHALL resolve in
`SUBRACE_REGISTRY` and its `race_key` SHALL match the character's `race` — this cross-check is
listed as a task for whichever change consumes it (change 4), not implemented here.

### D-4. Registries are one module per lore category, mirroring §3.2's tree.

```
world/lore/
├── __init__.py    re-exports every public registry and dataclass
├── races.py        Vitals, RaceProfile, RACE_REGISTRY, Subrace, SUBRACE_REGISTRY
├── elements.py      Element, ELEMENT_REGISTRY
├── magic.py         MagicTier, MAGIC_TIER_REGISTRY, RankTitle, RANK_TITLE_REGISTRY
├── nations.py        Nation, NATION_REGISTRY
├── guild.py          GuildRank, GUILD_RANK_REGISTRY
├── monsters.py       MonsterTier, MONSTER_TIER_REGISTRY
├── anchors.py         AnchorKind, Anchor, ANCHOR_REGISTRY
├── economy.py         COPPER_PER_SILVER, COPPER_PER_GOLD, to_copper(), PriceEntry, PRICE_TABLE
├── sync.py            sync_all() — see D-8
└── tests/             self-consistency tests, one module per lore module above
```

`races.py` and `magic.py` each hold two related dataclasses (`Vitals`+`RaceProfile`/`Subrace`, and
`MagicTier`+`RankTitle`) rather than one file per dataclass, because they are read together by the
same future consumers (entity trait scaling; magic-rank gating) and splitting them buys nothing.
`anchors.py` depends on `nations.py` (a `Nation.capital_anchor_key` and an `Anchor.nation_key` are
each other's forward/back reference) — resolved by keeping both as plain string keys with no
circular import, validated by a test rather than by type-level referential integrity.

### D-5. `MagicTier` bands are non-overlapping; the 90/91 seam is a resolved ambiguity.

`world_info.md` writes 超級(71-90) directly followed by 究極(90級以上) — the boundary literally
overlaps at 90. Two non-overlapping level bands can't both include 90.

**Resolution**: 超級 keeps `level_max=90` (as literally stated), 究極 starts at `level_min=91`. This
is a judgment call, not a literal transcription — documented here so a future reader of
`world_info.md` doesn't "fix" the code to reintroduce the overlap. `MagicTier.level_max` is
`int | None` (`None` for 究極, which is open-ended).

```python
@dataclass(frozen=True)
class MagicTier:
    key: str
    display_name_zh: str
    level_min: int
    level_max: int | None
    example_spells_zh: tuple[str, ...]
    description: str   # English
```

| key | zh | band | example spells |
|---|---|---|---|
| apprentice | 初級 | 0–15 | 火球, 水箭, 風刃, 治癒術, 身體強化 |
| intermediate | 中級 | 16–30 | 火焰風暴, 冰牆, 飛行術 |
| advanced | 高級 | 31–70 | 熔岩術, 暴風雪, 高級治癒, 統御術 |
| superior | 超級 | 71–90 | 龍炎術, 地震術, 神聖光輝 |
| ultimate | 究極 | 91–None | (none documented — "人類幾乎不可能掌握") |

`RankTitle` (學徒/術師/大師/賢者/主宰) is a separate, ordered registry with an `order: int` field
(1–5) and an optional `unlocks_tier: str | None` referencing `MagicTier.key`, capturing
`world_info.md`'s explicit tier-to-title mapping (術師→中級, 大師→高級; 賢者 and 主宰 map loosely
to 超級/究極 since the source describes them by capability — "develops new magic" / "transcends
formula" — rather than a level band).

### D-6. `GuildRank` reward bands are converted at the corrected 1:100:10000 rate; every band is a
strictly increasing, non-degenerate ten-fold ladder.

`COPPER_PER_SILVER = 100`, `COPPER_PER_GOLD = 10000` (per design doc §5.1: "1 金 = 100 銀 =
10000 銅"). **Note on the exchange rate itself**: an earlier draft of this design used the rate
`1金=10銀=100銅`, which `world_info.md` stated at the time; that rate collapsed two of the seven
reward bands (F, C) to single-point ranges and produced an internally inconsistent economy (a
commoner's annual income undercutting their own annual food cost). The design doc has since been
corrected upstream to `1金=100銀=10000銅`, with the full reasoning recorded there (§5.1) — this
document does not restate it, only carries the corrected constants forward.

Converting `world_info.md`'s reward table at the corrected rate:

```python
@dataclass(frozen=True)
class GuildRank:
    key: str              # "F".."S"
    order: int            # 1..7
    reward_min_copper: int
    reward_max_copper: int | None   # None only for S (open-ended)
    description: str      # English, task scope per world_info.md
```

| key | order | band (copper) | task scope |
|---|---|---|---|
| F | 1 | 10–100 | simple collection/escort tasks |
| E | 2 | 100–500 | low-tier monster hunts |
| D | 3 | 500–5,000 | dungeon party runs |
| C | 4 | 5,000–50,000 | solo-capable adventurer |
| B | 5 | 50,000–500,000 | high-difficulty commissions |
| A | 6 | 500,000–5,000,000 | top-tier human combat strength |
| S | 7 | 5,000,000–None | legendary; fewer than 10 across the continent |

Every band is now strictly non-degenerate and each rank's ceiling equals the next rank's floor,
forming a clean ten-fold ladder — this property is asserted directly by a test (tasks.md §9.5) so a
future edit that reintroduces a wrong exchange rate is caught immediately rather than rediscovered
by hand.

The purchasing-power price table (`economy.py`'s `PRICE_TABLE`) is converted at the same corrected
rate (e.g. 魔法藥劑 "50銅-5銀" → `(50, 500)`; 普通劍 "1-5銀" → `(100, 500)`), and is likewise
non-degenerate throughout.

### D-7. `Anchor` and `Nation` cross-reference by string key, `AnchorKind` distinguishes the three
anchor shapes.

```python
class AnchorKind(StrEnum):
    CAPITAL = "capital"
    ELVEN_VILLAGE = "elven_village"
    DUNGEON = "dungeon"

@dataclass(frozen=True)
class Anchor:
    key: str
    kind: AnchorKind
    display_name_zh: str
    nation_key: str | None   # None for elven villages (neutral) and dungeons with no clear owner
    population: int | None
    floors: int | None       # dungeons only
    description: str         # English
```

Nine anchors: three capitals (輝煌帝都/聖潔王都/咆哮王城, tied to their nation), three elven
villages (翠綠森林村/暗影谷村/幽月谷村, `nation_key=None` — `world_info.md` explicitly states the
central mountains housing them are "各國無法深入的中立地帶"), and three dungeons (永夜迷宮 80F,
龍之巢穴 50F, 魔導遺跡 60F). **Judgment call on dungeon `nation_key`**: 龍之巢穴 is in "帝國東部"
(Grandia) and 魔導遺跡 in "王國西部" (Altoria) — both get a `nation_key`. 永夜迷宮 sits in "北方大
森林", which `world_info.md` describes as under Valhalla's *nominal* jurisdiction only ("獸王國擁
有邊境名義管轄權，但實際難以掌控") — it is still given `nation_key="valhalla"` with that caveat in
its `description`, rather than `None`, since a nominal claim is still a claim and `None` would erase
that distinction from the data entirely.

`StrEnum` matches the pattern design doc §6.2 already uses for `TargetSpec`, kept consistent rather
than introducing a plain `str` or a different enum base.

### D-8. Startup sync uses one Evennia `Script` row per lore entry, wired into the existing
`at_server_start()` hook — no new Django model, no migration.

```python
# world/lore/sync.py
def sync_all() -> None:
    for category, registry in _ALL_REGISTRIES.items():   # dict[str, Mapping[str, Any]]
        for key, entry in registry.items():
            sync_one(category, key, entry)

def sync_one(category: str, key: str, entry: Any) -> None:
    script_key = f"lore:{category}:{key}"
    script = search_script(script_key) or create_script(
        "world.lore.sync.LoreRecord", key=script_key, persistent=True,
    )
    script.db.category = category
    script.db.fields = dataclasses.asdict(entry)
```

`LoreRecord` is a minimal `DefaultScript` subclass with no ticking/interval behavior — it exists
purely as a persistent, queryable DB row. This reuses Evennia's own `ScriptDB` (core, already part
of the change-1 skeleton) instead of adding a new Django app and migration, keeping this change's
scope to a single working day. **Idempotency** comes from two properties working together:
`search_script(script_key)` finds an existing row before creating one (no duplicates across
restarts), and `sync_one` unconditionally overwrites `.db.fields` from the current Python registry
(so the DB always mirrors code — consistent with D9's rationale that lore-as-Python is the single
source of truth, and the DB copy is a queryable mirror of it, not a second authority).

`sync_all()` is called from `at_server_start()` in `server/conf/at_server_startstop.py` — the hook
file `evennia --init` scaffolds empty in change 1. This is the standard Evennia extension point for
"run this once every time the server comes up," and requires no new settings or global-script
registration. **Flagged for implementer verification** (same caution as change 1's contrib-matrix
work): confirm the hook file path and function signature against the installed Evennia 6.1.0 before
wiring the call in; this design assumes the conventional `evennia --init` scaffold, which change 1
already produced.

**Alternative considered**: Evennia's `settings.GLOBAL_SCRIPTS` mechanism (auto-creates persistent
scripts at server start if missing). Rejected for this change because it is designed around a
*small, fixed* number of named singleton scripts (e.g., one weather script), not a bulk
get-or-create loop over ~60+ dynamically-keyed lore entries — bending it to that shape would need
more scaffolding than the direct `at_server_start()` call for no behavioral benefit.

## Risks / Trade-offs

- **[Risk] The 90/91 magic-tier seam is a judgment call that could be read differently by a future
  contributor skimming `world_info.md` fresh.** → Mitigation: recorded explicitly in this document
  (D-5) with the reasoning, and the test suite (tasks.md §9.3) asserts the exact bands so any
  accidental "correction" back toward the source's literal overlapping text fails a test
  immediately.
- **[Risk] The guild-rank reward ladder silently regresses to a degenerate or non-monotonic shape
  if the exchange-rate constants (`COPPER_PER_SILVER`, `COPPER_PER_GOLD`) are ever edited without
  re-deriving every band.** → Mitigation: tasks.md §9.5 asserts the ladder is strictly increasing
  and non-degenerate across all seven ranks — this is exactly the property whose violation caught
  the earlier wrong exchange rate, so the test is written to keep catching it.
- **[Risk] `Subrace` is new — not named in design doc §5.1 — so a future change could assume it
  doesn't exist and re-derive subrace data ad hoc.** → Mitigation: the import contract's own
  reference example already depends on a `subrace` registry existing (`"subrace": "ciaran"`), so
  this is a completion of §5.1's implied contract, not a scope addition; call this out explicitly
  when change 4 (`import-contract`) is proposed.
- **[Risk] The `at_server_start()` hook assumption in D-8 could be wrong if change 1's actual
  skeleton generation didn't scaffold that file as expected.** → Mitigation: task list includes an
  explicit verification step before wiring in the call, mirroring change 1's own "verify before
  trusting" discipline for Evennia APIs.
- **[Risk] Beastfolk subspecies population figures don't exist in `world_info.md`.** → Accepted:
  `population=None` for all seven; no invented numbers. Any later change needing beastfolk
  population breakdowns must get that data from a different source or an explicit design decision,
  not from this change's registries.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/lore/` currently contains no code beyond change 1's empty stub. The only sequencing concern
is operational: the very first server start after this change lands performs the initial sync
(creating ~60+ `LoreRecord` rows); every subsequent start is a no-op overwrite of the same rows.

## Open Questions

- Should `Subrace` eventually move into design doc §5.1 itself, given the import contract already
  assumes it exists? Left as an open question for whoever proposes change 4 — this design treats it
  as a necessary completion of §5.1's implied contract, not a redesign of the approved document.
- Exact `LoreRecord` script typeclass placement (`world/lore/sync.py` vs. a shared
  `world/lore/scripts.py`) is left to the implementer; either satisfies this design.
