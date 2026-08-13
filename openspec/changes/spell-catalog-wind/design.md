## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 風 (speed/range-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 風 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `wind_blade` *(existing, recost)* | 風刃術 | 學徒 | 範圍 | 14 |
| `gale_step` | 疾風術 | 學徒 | 單體(自) | 10 |
| `flight` *(existing, recost)* | 飛行術 | 術師 | 單體(自) | 22 |
| `tornado_blade` | 龍捲風刃 | 術師 | 單體 | 26 |
| `storm_domain` | 暴風領域 | 大師 | 範圍 | 50 |
| `gale_dance_strike` | 疾風刃舞 | 大師 | 單體 | 40 |
| `heavens_wrath_storm` | 天譴風暴 | 賢者 | 範圍 | 90 |
| `haste_domain` | 神速領域 | 賢者 | 範圍(友) | 70 |
| `vacuum_severance` | 真空斬滅 | 主宰 | 單體 | 130 |
| `sky_tempest` | 蒼穹暴風 | 主宰 | 範圍 | 150 |

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
- Add all ten 風-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.
- Recost the pre-existing 風 anchor skill(s) per §4.3, without duplicating them.

**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:wind:magic` string with no numeric
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
| 單體(自) | `TargetSpec.SELF` | `FactionConstraint.SELF_ONLY` |
| 範圍(友) | `TargetSpec.AREA` | `FactionConstraint.ANY` |

"(自)" annotations become `SELF_ONLY` (cardinality and faction both narrow to the actor); "(友)"
annotations stay `AREA`/`ANY` since the registry has no ally-only enum value that restricts anything —
the narrower intent is presentation-only (label/description text), not a mechanical restriction.

### `effects` per spell

| Key | `effects` | Note |
|---|---|---|
| `wind_blade` | `damage:wind:magic` |  |
| `gale_step` | `self_buff_apply:wind_haste` |  |
| `flight` | `movement:flight` |  |
| `tornado_blade` | `damage:wind:magic` |  |
| `storm_domain` | `damage:wind:magic` |  |
| `gale_dance_strike` | `damage:wind:magic` |  |
| `heavens_wrath_storm` | `damage:wind:magic` |  |
| `haste_domain` | `buff_apply:wind_haste_domain` | pure party buff, no damage component |
| `vacuum_severance` | `damage:wind:magic` |  |
| `sky_tempest` | `damage:wind:magic` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `wind_haste`: self speed buff (rate/bounds-shaped agility increase), applied by `gale_step`
- `wind_haste_domain`: party speed+evasion buff (broader bounds than `wind_haste`), applied by `haste_domain`

### Pre-existing anchor skill(s) are recosted in place, not duplicated

- `wind_blade`: `mp=24` -> `mp=14` (its `effects`, `target_spec`, `label`, and every other field are unchanged — only the `cost` dict's `mp` value is edited)
- `flight`: `mp=10` -> `mp=22` (its `effects`, `target_spec`, `label`, and every other field are unchanged — only the `cost` dict's `mp` value is edited)

Per design doc §4.4: "Three keys already exist in `SKILL_REGISTRY` and are rebalanced to this table
rather than duplicated." `fire_ball`/`wind_blade`/`flight` predate the §4.3 MP tier concept; this change
brings them into that tier system for consistency with every other spell added across all eight
`spell-catalog-<element>` changes.

**`flight`'s recosted `mp=22` is display-only.** Found during rubber-duck review: this change now
depends on `movement-skill-waiver` landing first (see `proposal.md`'s Impact section), which
reclassifies `flight` from `ACTIVE` to `PASSIVE` — a `PASSIVE` skill never reaches
`ActionResolver.resolve()`'s resource-check step, so `flight`'s `cost` field, while kept
tier-consistent for presentational/UI purposes, is never actually spent. This is unlike every other
spell in this table, all of which remain `ACTIVE` and genuinely spend their listed MP.

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's spell rows are grouped
in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 風 — 學徒` -style comment) inside one `*_elemental_spells("wind", ...)` block, and each pair's MP
cost falls inside §4.3's band for that tier. This gives `element-mastery-cast-gate`'s tier lookup an
unambiguous signal (position + cost band) without this change adding a tier field or re-deriving gate
logic itself.

### Registry construction: reuse the `_elemental_spells` builder

This change expresses its entries through the `_spell`/`_elemental_spells` builders introduced by
`spell-catalog-fire` (see that change's design.md, "Registry construction helper") instead of writing
each `_skill(...)` call by hand: the element is written once per set, and `SkillKind.ACTIVE` plus
`FactionConstraint.ANY` are fixed by the builder. Field values remain exactly this change's
design-doc table. `flight` is a PASSIVE movement skill, so it is NOT part of the `_elemental_spells`
block; it keeps its existing `_skill(...)` entry and is recosted in place (task 5.2).

## Risks / Trade-offs

- [Risk] This change lands before `heal-effect-handler`/`element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.


- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `wind_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).

## Open Questions

- Exact `heal:<...>` effect-ID grammar — owned by `heal-effect-handler`, not this change; tracked as a
  task here.
