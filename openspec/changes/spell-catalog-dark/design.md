## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 暗 (curse/debuff-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 暗 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `shadow_bolt` | 暗影箭 | 學徒 | 單體 | 14 |
| `weaken` | 衰弱術 | 學徒 | 單體 | 11 |
| `curse` | 詛咒術 | 術師 | 單體 | 26 |
| `dark_burst` | 闇裂術 | 術師 | 範圍 | 29 |
| `dark_corrosion_domain` | 闇蝕領域 | 大師 | 範圍 | 47 |
| `shadow_torment` | 暗影凌遲 | 大師 | 單體 | 41 |
| `abyss_devour` | 深淵吞噬 | 賢者 | 單體 | 85 |
| `dark_dominion` | 黑暗支配 | 賢者 | 範圍 | 72 |
| `void_annihilation` | 終焉黑洞 | 主宰 | 範圍 | 155 |
| `netherworld_judgment` | 冥府審判 | 主宰 | 單體 | 135 |

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
- Add all ten 暗-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.


**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:dark:magic` string with no numeric
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

"(自)" annotations become `SELF_ONLY` (cardinality and faction both narrow to the actor); "(友)"
annotations stay `AREA`/`ANY` since the registry has no ally-only enum value that restricts anything —
the narrower intent is presentation-only (label/description text), not a mechanical restriction.

### `effects` per spell

| Key | `effects` | Note |
|---|---|---|
| `shadow_bolt` | `damage:dark:magic` |  |
| `weaken` | `buff_apply:dark_atk_down` | pure debuff, no damage component |
| `curse` | `buff_apply:dark_curse` | pure debuff, no damage component |
| `dark_burst` | `damage:dark:magic` |  |
| `dark_corrosion_domain` | `damage:dark:magic`, `buff_apply:dark_corrosion` |  |
| `shadow_torment` | `damage:dark:magic`, `buff_apply:dark_corrosion` |  |
| `abyss_devour` | `damage:dark:magic` |  |
| `dark_dominion` | `buff_apply:fear` | pure debuff, no damage component |
| `void_annihilation` | `damage:dark:magic` |  |
| `netherworld_judgment` | `damage:dark:magic` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `dark_atk_down`: atk-down debuff (bounds-shaped `atk_phys`/`magic_level` reduction), applied by `weaken`
- `dark_curse`: multi-stat debuff (bounds-shaped reduction across several stats, per 減益(多項)), applied by `curse`
- `dark_corrosion`: DoT (rate: hp delta negative, same shape as `poisoned`/`fire_scorch`), applied by `dark_corrosion_domain` and `shadow_torment`

### Reused existing `buffs.yaml` rows (no new row)

- `fear`: 黑暗支配 (`dark_dominion`) reuses the existing `fear` buff row exactly — no new row needed, matching this element's 恐懼 flavor precisely

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's ten `_skill(...)` calls are
grouped in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 暗 — 學徒` -style comment), and each pair's MP cost falls inside §4.3's band for that tier. This
gives `element-mastery-cast-gate`'s tier lookup an unambiguous signal (position + cost band) without
this change adding a tier field or re-deriving gate logic itself.

## Risks / Trade-offs

- [Risk] This change lands before `heal-effect-handler`/`element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.


- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `dark_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).

## Open Questions

- Exact `heal:<...>` effect-ID grammar — owned by `heal-effect-handler`, not this change; tracked as a
  task here.
