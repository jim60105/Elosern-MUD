# Skill System Redesign — Design

**Date:** 2026-08-12
**Status:** Approved (pending final user review of this document)
**Scope:** `world/skills/`, `world/rules/action.py` effect handlers, `world/rules/rulebook/combat_modifiers.yaml`,
`world/rules/progression.py` (element rank), skill content additions driven by `tmp/story_settings/`.

This document is the reference for the OpenSpec change(s) that implement it. It supersedes the
opaque-effect-ID convention documented in `world/skills/registry.py`'s module docstring and in the
`skill-registry` / `skill-handler` specs where they conflict with the decisions below.

---

## 1. Problem Statement

A second-run game-logic audit (`~/security-audit-skill/MUD/run-2/`) found that `SKILL_REGISTRY`
declares seven distinct effect-ID prefixes, but only `stat_multiply` (read-time, in
`SkillHandler.effective_value`) and six cast-time prefixes registered in `action.py`'s
`_EFFECT_HANDLERS` are actually consumed anywhere. Six prefixes — `movement`, `weapon_style`,
`element_mastery_rank`, `passive_buff`, `passive_trait`, `combat_prediction` — cover 18 of the ~28
non-innate skills in the registry and have **zero consumers** in the non-test codebase. Owning them
does nothing. Casting the ACTIVE ones among them always rejects `UNKNOWN_EFFECT_ID`.

Separately, `tmp/story_settings/` (five detailed character sheets plus world/rule lore, gitignored,
never committed — see `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`'s non-negotiable
adult-content-only constraint for why these never become seed data directly) describes a much richer
skill and magic system than the registry currently implements: named element-mastery ranks tied to
numeric magic level, a second non-elemental magic system (神之秘法, Divine Mystery), and several
per-character unique passives/actives that have no registry entry at all.

This change fixes both problems together: it makes every effect prefix the registry can declare
actually do something, and it substantially grows the content (skills and elemental magic) the
registry declares, using the character sheets as inspiration rather than a literal transcription
target (per this document's own D-instruction: no real-world individual is modeled, and the sheets
themselves are illustrative, not exhaustive — the design explicitly extrapolates beyond them).

---

## 2. Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Every `SkillDef.effects` string is parsed into a typed dataclass at registry-load time**, not lazily re-parsed by each consumer. An unrecognized prefix raises at import time, not silently at use time. | The root cause of the 18 dead skills was "opaque by convention, no owner." Making the registry itself refuse to load an effect it cannot classify makes a new opaque prefix impossible to land by accident. |
| D2 | **Two consumption paths, chosen by effect shape, not by historical accident.** Cast-triggered effects (movement commands, attack skills, disguise, conferral, sexual events) stay in `action.py`'s per-prefix handler registry. Ownership-triggered effects that are *not* combat-stat multipliers — accuracy/initiative/flat-stat adjustments (`passive_buff`, `combat_prediction`, the `dual_wield_style` stance) — move into the existing `combat_modifiers.yaml` rule-table engine via one new `skill_owned` condition primitive. `stat_multiply` is explicitly excluded from this move and stays in `SkillHandler.effective_value` (see D3, §3.1) — `buff-handler-integration`'s own spec already reserves combat-stat multiplier scaling as `effective_value`'s exclusive territory and forbids the rule table from configuring one. | `combat_modifiers.yaml` already proved this pattern for buff-origin and sexual-origin rows under one evaluator with no source-branching (see `buff-handler-integration` spec). Ownership-triggered skill effects of the *adjustment-bundle* shape are the same class of problem — extending the existing table is cheaper and more consistent than a third bespoke mechanism, and it was cheap now precisely because change 6 (`buffs-rulebook`) built the evaluator this landing already reuses. Multiplier effects are a different shape (multiplicative, not an adjustment bundle) and already have a working, spec-mandated home. |
| D3 | **`stat_multiply`-bearing skills (身體強化 family) are reclassified `PASSIVE`.** Ownership alone applies the multiplier; there is no cast action and never was one that worked. | Matches every observed narrative use (these read as a permanent condition, not a per-turn action) and removes the permanently-broken cast path instead of building one nobody asked for. |
| D4 | **Element mastery is a binary cast-gate override, not a rule-table adjustment.** Owning `<element>_mastery` unlocks casting every spell of that element regardless of numeric magic level; without it, casting is gated purely by the numeric magic-level tier thresholds already defined in world lore. | Matches the character data exactly: 薇歐蕾特 (level 30, no mastery skill) can only cast the two lowest-tier spells she knows; 伊洛希雅 (level 873, holds explicit `風之主宰`/`光之主宰` skills) can cast every spell of those two elements. Mastery is a narratively-granted key, not a side effect of a level number. |
| D5 | **A separate, purely cosmetic rank title function derives 學徒/術師/大師/賢者/主宰 from numeric magic level**, independent of D4's per-element gate. | World lore ties the five title names to numeric level bands for *display* ("階級稱號"); D4 is the *mechanical* gate. Conflating them would make every level-90+ caster automatically "主宰" of elements they hold no mastery skill for, contradicting D4. |
| D6 | **`ConferredSkillGrant` generalizes to any continuous-valued effect** (`stat_multiply`, `growth_rate`, the new rule-table passive adjustments), scaled by the grant's `scale`. It explicitly **excludes** binary/gate effects (`element_mastery_rank`, `set_disguise`) — "partial disguise" or "partial spell unlock" has no defined meaning, and 統御術's own description ("授予目標一部分自身技能的效果") only ever promises a fractional share of a quantity. | Keeps the generalization honest to what the skill claims to do, rather than forcing every effect type through one mechanism for uniformity's sake. |
| D7 | **神之秘法 (Divine Mystery) ships this round as free-cost, race-gated ACTIVE skills with no new numeric resource.** Only 狀態偽裝 (already mechanized as `set_disguise`) and a new 性愛系統 skill (routes to the already-rulebook-driven `sexual_event` effect) are mechanized. The remaining four known mysteries (time dilation, short-range teleport, matter transmutation, life extension) ship as registry entries with flavor-only descriptions and no mechanical effect. | Each of the four deferred mysteries implies its own subsystem (tick-rate manipulation, a teleport/permission system, item generation, an aging/death model) that does not exist today. Bundling any of them into this change would make it a skill-system change in name only. A real `精神力` resource is deferred for the same reason — nothing consumes it yet. |
| D8 | **Movement skills (`flight`, `flash_step`) grant a cost/restriction waiver on existing movement commands** (skip `wilderness_move` clock cost; pass movement-gated exits that require flight) rather than a new fast-travel/zone system. | The lore's "can reach far/near locations" reads as flavor for existing traversal, and the engine has no distance-tiered destination system to hook a real one into. Building one is a separate, larger proposal. |
| D9 | **All new/rebalanced MP costs follow one tier table** (§5) keyed to the five magic-level bands already defined in world lore, so relative costs are predictable across all eight elements instead of ad hoc per skill. | Existing costs (`fire_ball` 20, `wind_blade` 24, `flight` 10) predate any tier concept and get rebalanced under this table for consistency — acceptable because this project has zero users and no backward-compatibility obligation (per `tmp/propose.md`). |

---

## 3. Core Architecture (Typed Effects)

### 3.1 `world/skills/effects.py` (new module)

Replaces ad hoc `effect_id.split(":")` parsing scattered across `handler.py`, `action.py`, and
(under this change) `combat_modifiers.py`. Each effect prefix maps to exactly one frozen dataclass:

| Prefix | Effect class | Consumption path |
|---|---|---|
| `stat_multiply` | `StatMultiplyEffect(trait, multiplier)` | Ownership → `SkillHandler.effective_value` (unchanged mechanism, now typed) |
| `element_mastery_rank` | `ElementMasteryEffect(element)` | Ownership → cast-gate override (D4), new `world/rules/progression.py` query |
| `sexual_magic_mastery` (renamed from the malformed 3-segment `element_mastery_rank:性魔法:主宰`) | `SexualMasteryEffect()` | Ownership → cast-gate override for the sex-magic skill family, same mechanism as D4 but keyed off a non-elemental domain |
| `passive_buff`, `combat_prediction` | `RuleTableEffect(rule_key)` | Ownership → `skill_owned` row in `combat_modifiers.yaml` |
| `passive_trait` | `FlavorEffect(name)` | No mechanical consumer — explicitly inert by design (e.g. `elf_longevity`); registry load does not reject it, since "flavor with no mechanical effect" is a legitimate, declared category, unlike today's *undeclared* opacity |
| `movement` | `MovementEffect(mode)` | Cast → `action.py` handler granting the waiver described in D8 |
| `weapon_style` | `WeaponStyleEffect(style)` | Cast (attack skills) or ownership via `skill_owned` rule row (stance skills), split per skill — see §3.3 |
| `confer_skill_partial` | `ConferralEffect()` | Cast → generalized `ConferredSkillGrant` (D6) |
| `set_disguise`, `buff_apply`, `self_buff_apply`, `confer_growth_rate`, `sexual_event` | unchanged existing classes | unchanged existing cast handlers, now sourced from typed objects instead of re-splitting the string |
| `divine_mystery` | `DivineMysteryEffect(name, mechanized: bool)` | Cast when `mechanized=True` (currently only `sexual_event`-backed 性愛系統); registry-declared no-op otherwise (D7) |

`SkillDef.__post_init__` parses every string in `effects` through a single dispatch table keyed by
prefix; an unrecognized prefix raises `ValueError` at import time. The module docstring in
`registry.py` claiming `stat_multiply` is "the only effect-ID convention interpreted by this
package" is removed and replaced with a pointer to this module.

### 3.2 New rule-table condition: `skill_owned`

`world/rules/rulebook/schema.py`'s condition vocabulary gains one primitive:
`{"skill_owned": "<skill_key>"}`, evaluated against `entity.skills.owned_keys()` (already exists).
`combat_modifiers.yaml` gains one row per `passive_buff`/`combat_prediction` skill translating its
flavor name into a concrete adjustment (e.g. `defense_instinct` → `passive_buff:defense_small` becomes
a `skill_owned: defense_instinct` rule granting a small flat `defense` adjustment). `scale` from a
`ConferredSkillGrant` (D6) is folded into the adjustment the same way `combat_modifiers.py` already
merges multiple matching rules — no new merge mechanism, reusing `evaluate_combat_modifiers()`'s
existing bundle-merge behavior.

### 3.3 Weapon styles split by shape

- `light_sword_style` (an attack: `SINGLE` target, deals damage) stays a cast-time skill in
  `action.py`, unchanged in kind.
- `dual_wield_style` (a stance: `SELF` target, no direct effect except enabling a different combat
  posture) reclassifies to the `skill_owned` rule-table path — owning it while equipped with two
  weapons grants a to-hit/damage rule-table adjustment, matching how `dual_wield_style` actually reads
  narratively (a standing posture, not a repeatable cast).

---

## 4. Element Mastery & Magic Tier System

### 4.1 Rank titles (display only, D5)

`world/rules/progression.py` gains `magic_rank_title(entity) -> str`, a pure function of
`entity.traits.magic_level.value` against the exact bands from world lore:

| Title | Level band |
|---|---|
| 學徒 | 0–15 |
| 術師 | 16–30 |
| 大師 | 31–70 |
| 賢者 | 71–90 |
| 主宰 | 90+ |

### 4.2 Cast-gate (mechanical, D4)

`world/rules/progression.py` gains `can_cast_spell_tier(entity, element, tier) -> bool`:
`True` if `entity`'s numeric magic level meets the tier's band threshold, **or** `True`
unconditionally if `entity.skills.owned_keys()` contains that element's `<element>_mastery` skill.
A `ConferredSkillGrant` referencing a mastery skill does **not** satisfy this check — per D6, mastery
is explicitly excluded from conferral, so only direct ownership counts here.
This function is called by the same action-resolution step that already validates skill ownership
before allowing a cast, so an ungated spell attempt fails the same way an unowned-skill cast fails
today (`RejectedAction`), not a new reject reason.

### 4.3 MP cost tiers (D9)

| Tier | Level band | Single/direct-effect MP | Area/strong-effect MP |
|---|---|---|---|
| 學徒 | 0–15 | 10–16 | 14–20 |
| 術師 | 16–30 | 20–28 | 26–34 |
| 大師 | 31–70 | 35–48 | 45–60 |
| 賢者 | 71–90 | 65–85 | 80–110 |
| 主宰 | 90+ | 120–150 | 140–180 |

Human talented characters cap around 150–200 MP; elves around 10000. This makes "究極魔法人類幾乎不可
能掌握" (world lore) a mechanical fact (a human can rarely afford even one 主宰-tier cast) rather than
only a narrative claim.

### 4.4 Full spell catalog — 8 elements × 5 tiers × 2 spells (80 entries)

Three keys already exist in `SKILL_REGISTRY` and are rebalanced to this table rather than duplicated:
`fire_ball` (火/學徒), `wind_blade` (風/學徒), `flight` (風/術師). Every other row is new.

**火 Fire** (offense-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `fire_ball` *(existing, recost)* | 火球術 | 學徒 | 單體 | 傷害 | 14 |
| `fire_arrow` | 火焰箭 | 學徒 | 單體 | 傷害(低耗能) | 10 |
| `firestorm` | 火焰風暴 | 術師 | 範圍 | 傷害 | 30 |
| `scorching_wave` | 灼熱波動 | 術師 | 單體 | 傷害+灼燒(DoT) | 24 |
| `lava_burst` | 熔岩術 | 大師 | 範圍 | 傷害+地形控制 | 52 |
| `infernal_wrap` | 業火纏繞 | 大師 | 單體 | 高傷害 | 42 |
| `dragon_flame` | 龍炎術 | 賢者 | 範圍 | 高傷害 | 95 |
| `hellfire` | 煉獄業火 | 賢者 | 單體 | 極高傷害 | 78 |
| `phoenix_eternal_flame` | 不滅鳳凰焰 | 主宰 | 範圍 | 極高傷害+自我治療 | 150 |
| `world_ending_blaze` | 焚世終焰 | 主宰 | 單體 | 毀滅級傷害 | 130 |

**水 Water** (heal/defense-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `water_bolt` | 水箭術 | 學徒 | 單體 | 傷害 | 12 |
| `minor_heal` | 治癒滴露 | 學徒 | 單體 | 治療 | 11 |
| `healing_spring` | 治癒之泉 | 術師 | 範圍 | 治療 | 28 |
| `water_shield` | 水盾術 | 術師 | 單體 | 護盾 | 22 |
| `abyssal_whirlpool` | 深海漩渦 | 大師 | 範圍 | 傷害+控制(束縛) | 50 |
| `wellspring_of_life` | 生命湧泉 | 大師 | 單體 | 大量治療 | 40 |
| `tsunami` | 海嘯術 | 賢者 | 範圍 | 極高傷害 | 95 |
| `tidal_revival` | 復生之潮 | 賢者 | 單體 | 瀕死急救型大量治療 | 78 |
| `sea_of_life` | 生命之海 | 主宰 | 範圍 | 全體大量治療+瀕死急救 | 160 |
| `abyssal_tide` | 深淵巨潮 | 主宰 | 範圍 | 毀滅級傷害 | 145 |

**風 Wind** (speed/range-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `wind_blade` *(existing, recost)* | 風刃術 | 學徒 | 範圍 | 傷害 | 14 |
| `gale_step` | 疾風術 | 學徒 | 單體(自) | 增益(速度) | 10 |
| `flight` *(existing, recost)* | 飛行術 | 術師 | 單體(自) | 移動(見 D8) | 22 |
| `tornado_blade` | 龍捲風刃 | 術師 | 單體 | 高傷害 | 26 |
| `storm_domain` | 暴風領域 | 大師 | 範圍 | 傷害+控制(擊退) | 50 |
| `gale_dance_strike` | 疾風刃舞 | 大師 | 單體 | 多段傷害 | 40 |
| `heavens_wrath_storm` | 天譴風暴 | 賢者 | 範圍 | 極高傷害 | 90 |
| `haste_domain` | 神速領域 | 賢者 | 範圍(友) | 增益(速度+迴避) | 70 |
| `vacuum_severance` | 真空斬滅 | 主宰 | 單體 | 處決級傷害 | 130 |
| `sky_tempest` | 蒼穹暴風 | 主宰 | 範圍 | 毀滅級傷害+控制 | 150 |

**土 Earth** (defense/control-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `stone_shard` | 石礫術 | 學徒 | 單體 | 傷害 | 12 |
| `hardened_skin` | 硬化肌膚 | 學徒 | 單體(自) | 增益(防禦) | 10 |
| `stone_armor` | 岩甲術 | 術師 | 單體 | 護盾 | 24 |
| `dust_veil` | 沙塵術 | 術師 | 範圍 | 減益(命中) | 22 |
| `earth_bind` | 地縛術 | 大師 | 範圍 | 控制(束縛) | 42 |
| `rockslide` | 岩壁崩落 | 大師 | 範圍 | 傷害 | 48 |
| `earthquake` | 地震術 | 賢者 | 範圍 | 極高傷害+控制 | 90 |
| `earthen_ward` | 大地庇護 | 賢者 | 範圍(友) | 護盾 | 75 |
| `mountain_collapse` | 山嶽崩落 | 主宰 | 範圍 | 毀滅級傷害 | 150 |
| `earths_judgment` | 大地審判 | 主宰 | 單體 | 處決級傷害 | 130 |

**雷 Lightning** (fast-attack-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `spark_shock` | 電擊術 | 學徒 | 單體 | 傷害 | 13 |
| `static_ward` | 靜電護體 | 學徒 | 單體(自) | 增益(反擊) | 10 |
| `chain_lightning` | 雷鎖術 | 術師 | 範圍 | 傷害 | 27 |
| `paralyzing_bolt` | 麻痺電擊 | 術師 | 單體 | 傷害+減益(麻痺) | 24 |
| `thunder_combo` | 雷霆連擊 | 大師 | 單體 | 多段高傷害 | 46 |
| `lightning_strike` | 落雷術 | 大師 | 範圍 | 傷害 | 50 |
| `heavens_thunder` | 天雷降臨 | 賢者 | 範圍 | 極高傷害 | 92 |
| `thunder_gods_haste` | 雷神之速 | 賢者 | 單體(自) | 增益(追加行動) | 68 |
| `judgement_thunder` | 審判雷霆 | 主宰 | 單體 | 處決級傷害 | 135 |
| `divine_lightning_slaughter` | 神雷滅殺 | 主宰 | 範圍 | 毀滅級傷害 | 155 |

**冰 Ice** (control/attack-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `ice_shard` | 冰錐術 | 學徒 | 單體 | 傷害 | 13 |
| `frost_breath` | 凍結之息 | 學徒 | 單體 | 減益(遲緩) | 11 |
| `ice_wall` | 冰牆術 | 術師 | 單體(自/友) | 護盾 | 25 |
| `frost_arrow_rain` | 冷凍箭雨 | 術師 | 範圍 | 傷害 | 28 |
| `permafrost_domain` | 永凍領域 | 大師 | 範圍 | 控制(凍結) | 48 |
| `ice_prison` | 冰封監牢 | 大師 | 單體 | 控制(定身) | 44 |
| `blizzard` | 暴風雪 | 賢者 | 範圍 | 極高傷害 | 88 |
| `absolute_tundra` | 絕對凍土 | 賢者 | 範圍 | 傷害+控制 | 82 |
| `absolute_zero` | 絕對零度 | 主宰 | 單體 | 處決級傷害+凍結 | 140 |
| `eternal_ice_field` | 永夜冰原 | 主宰 | 範圍 | 毀滅級傷害+控制 | 158 |

**光 Light** (heal/purify-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `heal` | 治癒術 | 學徒 | 單體 | 治療 | 12 |
| `light_arrow` | 光箭術 | 學徒 | 單體 | 傷害(對暗/不死加成) | 14 |
| `purify` | 淨化術 | 術師 | 單體 | 解除異常狀態 | 22 |
| `mass_heal` | 群體治癒 | 術師 | 範圍(友) | 治療 | 30 |
| `advanced_heal` | 高級治癒 | 大師 | 單體 | 大量治療 | 46 |
| `holy_shield` | 聖盾術 | 大師 | 單體 | 護盾 | 40 |
| `holy_radiance` | 神聖光輝 | 賢者 | 範圍 | 傷害(對暗/不死加成)+淨化 | 90 |
| `revival_light` | 復甦之光 | 賢者 | 單體 | 大量治療+解除瀕死 | 82 |
| `goddess_blessing` | 女神降福 | 主宰 | 範圍(友) | 全體大量治療+增益 | 145 |
| `heavens_judgment_light` | 天啟聖裁 | 主宰 | 單體 | 毀滅級傷害(對暗/不死) | 135 |

**暗 Dark** (curse/debuff-focused)

| Key | 名稱 | 位階 | 目標 | 效果 | MP |
|---|---|---|---|---|---|
| `shadow_bolt` | 暗影箭 | 學徒 | 單體 | 傷害 | 14 |
| `weaken` | 衰弱術 | 學徒 | 單體 | 減益(攻擊力) | 11 |
| `curse` | 詛咒術 | 術師 | 單體 | 減益(多項) | 26 |
| `dark_burst` | 闇裂術 | 術師 | 範圍 | 傷害 | 29 |
| `dark_corrosion_domain` | 闇蝕領域 | 大師 | 範圍 | 傷害+DoT | 47 |
| `shadow_torment` | 暗影凌遲 | 大師 | 單體 | 高傷害+DoT | 41 |
| `abyss_devour` | 深淵吞噬 | 賢者 | 單體 | 處決級傷害(無視防禦) | 85 |
| `dark_dominion` | 黑暗支配 | 賢者 | 範圍 | 減益(恐懼/控制) | 72 |
| `void_annihilation` | 終焉黑洞 | 主宰 | 範圍 | 毀滅級傷害+吸取 | 155 |
| `netherworld_judgment` | 冥府審判 | 主宰 | 單體 | 處決級傷害 | 135 |

`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery` (existing) remain the four shipped
element-mastery skills; `water_mastery`, `earth_mastery`, `lightning_mastery`, `ice_mastery` are added
as the same pattern to cover the remaining four elements, so every element has a mastery skill
available to grant.

---

## 5. Conferral (統御術) Generalization

See D6. `ConferredSkillGrant` becomes `{source_key: str, skill_key: str, scale: float}`. Consumers
that resolve a continuous-valued typed effect (§3.1's `StatMultiplyEffect`, `growth_rate`'s existing
class, and the new `skill_owned` rule-table adjustments) each independently check
`entity.skills.conferred_grants()` for a grant referencing a skill whose parsed effect they know how
to scale, and fold in `resolved_value * grant.scale`. No change to the existing
`confer_skill_key`/`confer_scale`/`confer_trait_keys` event-context contract is required beyond
dropping the now-redundant explicit `trait_keys` (derivable from the referenced skill's own typed
effect).

---

## 6. 神之秘法 (Divine Mystery)

Per D7, this round: `status_disguise` is retagged into this family (no mechanical change — still
`set_disguise`); a new `divine_sexual_mastery` skill (性魔法主宰 — the skill body itself, distinct from
`reincarnation_boon_yuna` which grants a specific character's *innate* version of it) carries
`effects=["sexual_magic_mastery"]` unlocking casting of `divine_sexual_arts` (神之秘法：性愛系統),
which uses `effects=["sexual_event:<name>"]` against the existing rule-driven
`world/rules/sexual_transitions.py` engine, targetable at other entities. Both require the caster's
race to carry `has_divine_affinity` (new `RaceProfile` field, `True` only for the three elf subraces).
The four unmechanized mysteries (時間加速/減速, 空間扭曲, 物質轉換, 生命延續) ship as registry entries
using `DivineMysteryEffect(mechanized=False)` — ownable, flavor-text only, explicitly not a
placeholder for "someone forgot to wire this up" (D1's registry-load validation accepts
`mechanized=False` as a deliberately declared category, not an unrecognized prefix).

---

## 7. Content Additions (character-sheet-driven, §G)

| 角色卡技能 | 處理方式 |
|---|---|
| 護主本能（莉茲婭） | 沿用既有 `guardian_instinct`，更新中文標籤與描述 |
| 侍從武術訓練 | 既有 `retainer_martial_training`，不變 |
| 刀術強化（悠花） | 既有 `blade_art_mastery`，更新描述涵蓋刀術 |
| 極限耐久（悠花） | 既有 `extreme_endurance`，不變 |
| 魔法陣理解(天賦)（薇歐蕾特） | 既有 `magic_circle_comprehension`，不變 |
| 統御術（伊洛希雅） | 既有 `dominion_art`，行為依 §5 泛化 |
| 性魔法主宰（技能本體） | 新增 `divine_sexual_mastery`（見 §6），修正 `reincarnation_boon_yuna` 的格式錯誤三段式效果 ID |
| 雙刀流（悠花，"宗師級"） | `dual_wield_style` 保留為初階架式（見 §3.3，改走 `skill_owned` 規則表）；新增 `dual_blade_mastery`（宗師級雙刀連擊，`SINGLE`，SP 30）作為 Cast 型攻擊技 |
| 水/土/雷/冰屬性精通 | 新增 `water_mastery`／`earth_mastery`／`lightning_mastery`／`ice_mastery`，補齊八屬性（見 §4.4） |

**SP cost tiers for non-magic weapon/stance skills** (calibrated against existing `light_sword_style`
6 / `dual_wield_style` 8 / `flash_step` 12 / `shadow_slash` 18): 基礎架式/移動 6–12 SP，中階連段技
15–25 SP，宗師級奧義 25–40 SP.

---

## 8. Error Handling & Validation

- **Registry load**: an unrecognized effect prefix raises `ValueError` immediately on import (module
  load time, i.e. server startup), not on first use — extending the existing duplicate-multiplier
  check in `skill-handler`'s spec (`effective_value` already raises on a `SkillDef` declaring two
  multipliers for the same trait) to the full typed-effect dispatch table.
- **Cast-gate rejection**: an unmet `can_cast_spell_tier` check reuses the existing `RejectedAction`
  path with the existing unowned-skill reject reason — no new `RejectReason` enum member, since from
  the resolver's point of view "you may not cast this" is the same class of rejection whether the
  cause is "you don't own the skill" or "you don't meet its element-tier gate."
- **Conferral of a non-continuous effect**: attempting `confer_skill_partial` targeting a skill whose
  parsed effect is not one of the continuous-valued classes raises at cast-resolution time with the
  existing `EFFECT_RESOLUTION_FAILED` reason — this is a content-authoring bug (a skill wrongly
  granted the conferral effect), not a player-reachable state, since `dominion_art`'s own effect list
  is fixed content.

## 9. Testing Strategy

- **Registry-level**: parametrized test asserting every effect prefix currently defined across all 80
  new spells + existing skills round-trips through the typed dispatch table without raising, plus a
  negative test asserting a fabricated unknown prefix raises at construction.
- **Cast-gate**: table-driven tests over the tier boundaries (14/15/16, 30/31, 70/71, 90/91) for an
  entity with no mastery skill, and a separate test proving an entity with the mastery skill can cast
  the 主宰-tier spell at magic level 1.
- **Rule-table**: extend the existing `combat_modifiers.yaml` test fixtures with `skill_owned` rows,
  reusing the existing "multiple matching rules merge" scenario style already proven for buff/sexual
  origins.
- **Conferral**: a scale=0.5 grant test mirroring the existing `magic-level-progression` spec's
  `conferred_growth_rate` scenario, applied to a `stat_multiply` skill instead.
- **Content smoke test**: importing `example_character.json` and each of the five illustrative
  character-sheet skill loadouts (as ad hoc test fixtures, not committed narrative content) resolves
  every skill key against `SKILL_REGISTRY` with no `KeyError`.

## 10. Explicitly Out of Scope (deferred)

- A real `精神力` numeric resource (D7).
- Mechanizing 時間加速/減速, 空間扭曲, 物質轉換, 生命延續 (D7).
- A distance-tiered fast-travel/zone-permission system for `movement` skills beyond the existing
  command cost/restriction waiver (D8).
- Per-element proficiency tracking distinct from the single global `magic_level` number (ranks are
  derived from one shared level, per D5; nothing in the current character data requires per-element
  levels).
