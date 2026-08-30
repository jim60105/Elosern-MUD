# Design: magic-power-static-rename

## Context

Authoritative source: `docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`
§5 (D1) and §6 (D2), plus the rename rows of the §7 deletion table. `magic_level`
is read as the magic-school attack stat by `combat.py`, healing, appraisal,
equipment bundles, the disguise accessor, and the WebClient 魔力 column (~95
call sites), while being typed as a `CounterTrait` clamped by `magic_cap` and fed
by an XP engine. This change performs only the mechanical half of the demotion:
rename → retype → re-band → delete the display rank title. The growth writers
(`accrue_magic_study`, `grant_combat_kill_xp`, `magic_xp`) keep running against
the renamed static value until `magic-xp-engine-retirement` deletes them; the XP
engine's `traits.magic_level.base`-style writes become `magic_power` writes with
identical arithmetic (a static trait's `base` is writable by that code path just
as the counter's was, so nothing breaks mid-cutover).

Current facts verified in-tree:

- `world/rules/traits.py:17-20` — `STATIC_KEYS = ("atk_phys","agility","defense")`,
  `COUNTER_KEYS = ("magic_level","guild_merit")`; `trait_config_for_values(values,
  magic_cap)` has a counter branch with `max=magic_cap`.
- `world/lore/races.py` — `StaticBand` is 3-D; `RaceProfile` carries `magic_cap`
  and `starting_magic_level`; `_static_band()` replicates one band to three axes.
- `world/rules/status_query.py:55-62` — label map (`魔法階級`) plus `_STATIC_KEYS`/
  `_COUNTER_KEYS` mirrors, pinned by a mirror test against the Vue
  `CharacterStatusDrawer.vue` allowlist.
- `web/webclient-app/components/character-identity.js` — duplicated client-side
  `magicRankTitle` band table; `CharacterHead.vue` reads the `magic_level` trait
  row for a badge and a 魔階·<rank> rank line.
- `world/rules/progression.py:157-185` — `MAGIC_RANK_BANDS` + `magic_rank_title()`
  (display-only); `MAGIC_TIER_THRESHOLDS` (cast gate) is separate and stays.
- `world/lore/magic.py` `RANK_TITLE_REGISTRY` mirrored by `world/lore/sync.py`
  under category key `"rank_titles"`.
- Growth-rate vocabulary: passive effect prefix `growth_rate:magic:<N>`
  (`GrowthRateEffect(stat="magic")`), buff target string `magic_level_growth`
  (`_NO_OP_RATE_TARGETS` in `world/rules/buffs.py`), pull query
  `effective_magic_growth_multiplier()`.
- `world/ai/character_creation.py` duplicates `ALLOCATABLE_AXES` (six axes)
  because `world/ai` must not import `world/rules`.

## Goals / Non-Goals

**Goals**

- One mechanical cutover: every `magic_level` occurrence becomes `magic_power`;
  every `magic_cap`/`starting_magic_level` consumer reads the fourth `StaticBand`
  axis; behavior (damage numbers, display rows, schema acceptance) is
  byte-identical apart from the explicitly listed wording deltas.
- Rank-title deletion confined to the display path; the numeric cast gate keeps
  working unchanged against the renamed static.
- All four mirrors (Python trait keys, status_query mirror, Vue allowlists,
  vitest fixtures) move in lockstep in this one change.

**Non-Goals**

- No deletion of growth writers, clock stage, kill-XP planner, or cast gate —
  `magic-xp-engine-retirement` owns those.
- No new capability specs; no new commands; no shard-manifest change.
- No rename of the tier-name vocabulary (學徒/術師/大師/賢者/主宰 stay as
  `MAGIC_TIER_THRESHOLDS` keys and cost-tier data labels).

## Decisions

### D-A1: `magic_power` joins `STATIC_KEYS`; counter list shrinks to `guild_merit`

`traits.py` becomes `STATIC_KEYS = ("atk_phys","agility","defense","magic_power")`,
`COUNTER_KEYS = ("guild_merit",)`. `trait_config_for_values(values, magic_cap)`
loses the `magic_cap` parameter entirely (it existed only for the magic counter
branch): signature becomes `trait_config_for_values(values)`; the
`_trait_config` internal alias follows. `race_floor()` returns
`"magic_power": race.static_baseline.magic_power[0]` instead of
`"magic_level": 0` — race baseline construction now lands magic power at the
race band floor like the other three statics. The invariant "a race-baseline
entity's magic starts at 0" dies with the counter; nothing reads it any more
(verified consumers all display or compute from the trait value).

### D-A2: `StaticBand` is four-dimensional; race fields deleted

`StaticBand` gains `magic_power: tuple[int, int]`. `_static_band()` (uniform
three-axis helper) is replaced by explicit per-axis bands. Race baselines are the
design doc §6 interim table:

| race | atk_phys/agility/defense | magic_power |
|---|---|---|
| human | (1, 22) | (5, 90) |
| beastfolk | (4, 34) | (1, 30) |
| elf | (70, 95) | (100, 900) |

`RaceProfile.magic_cap` and `.starting_magic_level` are deleted fields. The
human band upper bound 90 and elf 900 keep the old caps as band ceilings, which
keeps `import-validation`'s hard-reject semantics expressible (above the band
upper bound = reject, exactly mirroring the old above-cap reject).

`STATIC_TIER_REGISTRY`'s `band: tuple[int, int | None]` stays the shared
physical-power band for the three combat axes (tiers today use one band for all
of atk/agility/defense; the design doc keeps that shape) and gains
`magic_band: tuple[int, int]` — a race-magic-band sub-band authored per tier,
each a subset of the owning race's `magic_power` band, validated at registry
module import (an existing load-time validation function in `races.py` gains the
check). This is the mechanism by which scene-builder NPCs and tier-built player
profiles get a deterministic magic power instead of the deleted
`starting_magic_level`. Tier magic bands are interim authored values anchored to
old lore: human tiers span their race band (平民 floor 5 … 大劍豪 ceiling 90,
`human_adventurer` mid-band ≈ 30, honoring the old human average 30 as the old
spec required "old numeric lore anchors survive as tier hints"); beastfolk tiers
sit low in (1,30); elf tiers at/above (100,900) floor, `elf_prodigy` open-ended
`magic_power` band is a two-tuple (no open-ended magic dimension).
`MonsterTier.static_band` becomes four-dimensional too: Monster magic power is
documented nowhere in lore, so every monster tier authors `magic_power` as
`(0, 0)`-equivalent `("0,0")` — concretely `magic_power=(0, 0)`, preserving the
existing "Monster magic defaults to zero, nobody invented a band" requirement.
`build_initial_traits(tier=...)` sets the fourth static from `static_tier.magic_band[0]`.

### D-A3: rank titles deleted; tiers stay as labels

Delete `RANK_TITLE_REGISTRY`, `RankTitle` (`world/lore/magic.py`), the
`"rank_titles"` sync category, `MAGIC_RANK_BANDS`, and `magic_rank_title()`
(`world/rules/progression.py`). `MAGIC_TIER_REGISTRY`/`MagicTier` (the 初級…究極
cost-tier bands) and `MAGIC_TIER_THRESHOLDS` stay untouched — they are cost-tier
data, not display titles. Callers of `magic_rank_title()` are the head-card
display path and its tests only (verified: `world/rules/progression.py` +
`test_progression.py`); no rules consumer exists. The `element_mastery_rank`
typed effect keeps parsing and keeps being owned-registry content in this change
(its deletion is `magic-xp-engine-retirement`, which deletes the elemental
override branch with the gate it feeds); keeping it here would force rewriting
24 registry effect strings inside a supposedly behavior-preserving rename.

### D-A4: growth-rate vocabulary re-keyed, semantics untouched

`GrowthRateEffect` stat key: `growth_rate:magic:<N>` → `growth_rate:practice:<N>`
(one registry entry: `reincarnation_boon_elosia`). The buff target string
`magic_level_growth` → `skill_practice` everywhere: `buffs.yaml` conferred
growth-rate rows, `_NO_OP_RATE_TARGETS`, `effective_magic_growth_multiplier()`
(decision: rename the query to `effective_growth_multiplier()`, since after
this change it scales practice, not magic, and its callers —
`progression.accrue_magic_study` and `progression.grant_combat_kill_xp`'s
multiplier folds — feed the surviving growth writes; the rename is in-scope
because leaving `magic` in the name of the surviving multiplier contradicts the
change's whole point). Registry-load and buff-table load MUST reject the old
prefixes/target (fail closed on the old key, per design doc §7 "old prefix
fails registry load").
`element_mastery_rank` is NOT touched here (see D-A3).

### D-A5: creation loses its sampler; `magic_power` rides the static path

`world/rules/character_creation.py`: delete `starting_magic_interval()` and the
sampler validation block; `magic_power` is added to the allocable static set, so
custom creation allocates it like `atk_phys` (bounds from the race's fourth band
plus subrace handling — subrace `static_modifiers` gains `magic_power: float =
0.0`? No: `StatModifiers` stays three-field and subrace magic is untouched,
because lore documents no subrace magic skew; the axis is allocable but
modifier-free). Budget becomes `floor(sum(axis_max - axis_min) / 2)` across
seven axes (formula shape unchanged, axis count changes — budget numbers shift;
all creation tests re-pinned). `ALLOCATABLE_AXES` in `world/ai/character_creation.py`
gains `magic_power` (the duplication is the transport-boundary contract; the
mirror test in `world/ai/tests/test_character_creation.py` pins it). Presets fix
all four static values as before. The completion echo rewords
`初始魔法等級為 X` → `初始魔力為 X` (`commands/character_creation.py`,
`web/webclient/actions/creation_actions.py`, `web/webclient/presentation`
creation payload field `magic_level` → `magic_power` and its allowlisted client
mirror).

### D-A6: display stays player-identical

`displayed_stats.DISPLAYED_KEYS` order keeps slot four renamed → label
`魔法階級`? Decision: the look-row label follows the trait rename to
`魔力`-labeled rows would break byte-identical look output; design doc §5 says
顯示名維持「魔力」 for the panel, and §13 says command docs change only when
player-visible wording changes. The look row and the server `TRAIT_LABELS` keep
`魔法階級` → decision: RENAME the label value to `魔力` and update
`docs/game/command-reference.md`'s look row wording (攻擊、敏捷、防禦、魔法階級、
生命 → …魔力…) in this change. Rationale: 「階級」 literally means rank-class,
advertising the deleted rank system to players every `look`; the drawer's
client-side abbreviation override becomes `magic_power: 魔力` and the drawer's
server-shared label 魔法階級 → 魔力 removes the need for a 魔階 abbreviation —
the drawer override is deleted, both surfaces render 魔力. `TRAIT_LABELS` map key
renames in all four mirror sites (`displayed_stats.py`, `status_text.py`,
`status_query.py`, `web/webclient/presentation/character.py` share the map —
single source where already shared, renamed per-site where duplicated).

### D-A7: WebClient head card becomes guild-rank-only

`character-identity.js`: delete `magicRankTitle()` and its band table.
`CharacterHead.vue`: badge reads `magic_power` trait row; the rank line renders
`公會 <rank> · 功績 <merit>` only (no 魔階· prefix; guild-less shows 未加入公會).
`character_head.test.js`, `character_identity.test.js` (band-table tests deleted),
`status_panel.test.js` rank assertions, `fixtures.js` trait rows (`key:
"magic_power", label: "魔力"`), `CharacterHead.stories.js`, and
`CharacterStatusDrawer.vue`'s `ATTRIBUTE_KEYS`/`TRAIT_LABEL_OVERRIDES` move in the
same commit. The `status_query` mirror-pin test updates its expected allowlist to
`["atk_phys","agility","defense","magic_power"]`. No OOB contract changes (trait
rows are data-driven key/label rows; payload shape unchanged), so the
frozen-contract four-mirror ritual is not triggered — only the vitest fixtures
and the Python panel-presentation fixtures move.

### D-A8: imports

`schema.py`: `stats` key list and the `disguised_stats` example rename; the
eight-key count is unchanged. `validate.py`: the magic-cap hard reject becomes
"above the race band upper bound rejects" (same severity, same
`Issue(field, reason)` determinism, field name `stats.magic_power`); below the
lower bound warns exactly like the other static axes (new behavior, replacing the
old silent floor tolerance: old code only rejected above cap; a value below the
floor previously didn't warn — the band check unifies it and is the design doc's
「區間成員檢查」). Example card: `"magic_level": 60` → `"magic_power": 60`
(inside human 5–90). `disguised_stats` boundary-capacity tests re-key.

## Risks / Trade-offs

- The interim state between this change and `magic-xp-engine-retirement` has the
  XP engine writing a StaticTrait base. Accepted: both changes ship before any
  release; the writer's arithmetic is identical; D-A1 documents why.
- Seven-axis creation budget changes every existing creation test number; pinning
  them mechanically is the cost of one clean cutover versus a shim (forbidden).
- Deleting the client rank table loses the only client-side duplication of the
  rank bands; acceptable because the band system itself is being retired and the
  title-system line replaces the display.

## Migration Plan

Single-commit cutover on an unreleased project (zero users, no data migration).
Order inside the commit: lore → traits → rules consumers → skills/buffs →
imports → creation → webclient mirrors → fixtures/docs. `--keepdb` test DB reuse
works because trait configs are rebuilt per entity in tests.

## Open Questions

(None — the design doc settles every value table; interim balance numbers are
explicitly flagged for post-playtest rebalance in `progression.yaml` header style.)
