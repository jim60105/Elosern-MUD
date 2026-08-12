## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 冰 (control/attack-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 冰 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `ice_shard` | 冰錐術 | 學徒 | 單體 | 13 |
| `frost_breath` | 凍結之息 | 學徒 | 單體 | 11 |
| `ice_wall` | 冰牆術 | 術師 | 單體(自/友) | 25 |
| `frost_arrow_rain` | 冷凍箭雨 | 術師 | 範圍 | 28 |
| `permafrost_domain` | 永凍領域 | 大師 | 範圍 | 48 |
| `ice_prison` | 冰封監牢 | 大師 | 單體 | 44 |
| `blizzard` | 暴風雪 | 賢者 | 範圍 | 88 |
| `absolute_tundra` | 絕對凍土 | 賢者 | 範圍 | 82 |
| `absolute_zero` | 絕對零度 | 主宰 | 單體 | 140 |
| `eternal_ice_field` | 永夜冰原 | 主宰 | 範圍 | 158 |

**§4.3 MP cost-tier table** (for reference — the MP column above is already the correct
tier-consistent value, this table is the source it was drawn from):

| Tier | Level band | Single/direct-effect MP | Area/strong-effect MP |
|---|---|---|---|
| 學徒 | 0-15 | 10-16 | 14-20 |
| 術師 | 16-30 | 20-28 | 26-34 |
| 大師 | 31-70 | 35-48 | 45-60 |
| 賢者 | 71-90 | 65-85 | 80-110 |
| 主宰 | 90+ | 120-150 | 140-180 |


## Goals / Non-Goals

**Goals:**
- Add all ten 冰-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.


**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:ice:magic` string with no numeric
  magnitude encoded in the string. Magnitude is derived elsewhere in the existing combat formula from
  caster stats, unchanged by this proposal.
- Flavor descriptions in §4.4's table such as "多段傷害" (multi-hit), "無視防禦" (ignores defense), "DoT"
  (damage over time, where not explicitly modeled as a rate-buff below), and "控制" variants outside the
  named set (root, stun, freeze, slow, fear, paralyze, defense-down, accuracy-down, atk-down) are
  **narrative flavor for this pass**. This change does not invent new combat-formula variants: no
  multi-hit resolution, no defense-piercing flag, no new status-effect mechanics beyond the existing
  `buff_apply`/`self_buff_apply` + `buffs.yaml` mechanism.
- Where a spell's flavor genuinely names one of the listed status effects, it is modeled via the
  existing `buff_apply`/`self_buff_apply` prefixes plus a new (or reused) `buffs.yaml` row — never a
  new prefix or a new cast-time handler.
- Shield/ward spells likewise use `buff_apply`/`self_buff_apply` + a `buffs.yaml` row (a defense-bounds-
  shaped buff), not a new prefix.
- Element-mastery cast-gating (`can_cast_spell_tier`) is consumed, not reimplemented, here. This change
  only makes each spell's tier obvious from registry position/cost; the gate logic itself belongs to
  `element-mastery-cast-gate`.
- No new `RejectReason`, no new resource type, no new targeting cardinality beyond the existing
  `TargetSpec`/`FactionConstraint` enums.

## Decisions

### Target-column mapping

§4.4's target column uses shorthand not identical to the registry's `TargetSpec`/`FactionConstraint`
enums. The `skill-registry` spec is explicit that only `ANY` and `SELF_ONLY` are legal
`FactionConstraint` values for shipped content ("No skill SHALL be restricted to enemies or allies
only"), so a "friendly-only" table annotation cannot become an `ALLY`-restricted constraint. This
change maps consistently:

| §4.4 target column | `TargetSpec` | `FactionConstraint` |
|---|---|---|
| 單體 | `TargetSpec.SINGLE` | `FactionConstraint.ANY` |
| 範圍 | `TargetSpec.AREA` | `FactionConstraint.ANY` |
| 單體(自/友) | `TargetSpec.SINGLE` | `FactionConstraint.ANY` |

"(自)" annotations become `SELF_ONLY` (cardinality and faction both narrow to the actor); "(友)"
annotations stay `AREA`/`ANY` since the registry has no ally-only enum value that restricts anything —
the narrower intent is presentation-only (label/description text), not a mechanical restriction.

### `effects` per spell

| Key | `effects` | Note |
|---|---|---|
| `ice_shard` | `damage:ice:magic` |  |
| `frost_breath` | `buff_apply:ice_slow` | pure debuff, no damage component |
| `ice_wall` | `buff_apply:ice_wall` | pure shield, no damage component |
| `frost_arrow_rain` | `damage:ice:magic` |  |
| `permafrost_domain` | `buff_apply:ice_freeze` | pure control, no damage component |
| `ice_prison` | `buff_apply:ice_prison` | pure control, no damage component |
| `blizzard` | `damage:ice:magic` |  |
| `absolute_tundra` | `damage:ice:magic`, `buff_apply:ice_freeze` |  |
| `absolute_zero` | `damage:ice:magic`, `buff_apply:ice_freeze` |  |
| `eternal_ice_field` | `damage:ice:magic`, `buff_apply:ice_freeze` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `ice_slow`: slow debuff (rate-shaped agility/speed reduction), applied by `frost_breath`
- `ice_wall`: shield buff (defense bounds ceiling, self-or-ally target), applied by `ice_wall`
- `ice_freeze`: marker control buff (empty `modifiers`, same shape as `paralysis`/`fear`) representing 凍結, applied by `permafrost_domain`, `absolute_tundra`, `absolute_zero`, and `eternal_ice_field`
- `ice_prison`: marker control buff (empty `modifiers`) representing 定身, applied by `ice_prison`

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's ten `_skill(...)` calls are
grouped in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 冰 — 學徒` -style comment), and each pair's MP cost falls inside §4.3's band for that tier. This
gives `element-mastery-cast-gate`'s tier lookup an unambiguous signal (position + cost band) without
this change adding a tier field or re-deriving gate logic itself.

## Risks / Trade-offs

- [Risk] This change lands before `heal-effect-handler`/`element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.


- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `ice_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).

## Open Questions

- Exact `heal:<...>` effect-ID grammar — owned by `heal-effect-handler`, not this change; tracked as a
  task here.
