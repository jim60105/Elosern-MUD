## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 雷 (fast-attack-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 雷 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `spark_shock` | 電擊術 | 學徒 | 單體 | 13 |
| `static_ward` | 靜電護體 | 學徒 | 單體(自) | 10 |
| `chain_lightning` | 雷鎖術 | 術師 | 範圍 | 27 |
| `paralyzing_bolt` | 麻痺電擊 | 術師 | 單體 | 24 |
| `thunder_combo` | 雷霆連擊 | 大師 | 單體 | 46 |
| `lightning_strike` | 落雷術 | 大師 | 範圍 | 50 |
| `heavens_thunder` | 天雷降臨 | 賢者 | 範圍 | 92 |
| `thunder_gods_haste` | 雷神之速 | 賢者 | 單體(自) | 68 |
| `judgement_thunder` | 審判雷霆 | 主宰 | 單體 | 135 |
| `divine_lightning_slaughter` | 神雷滅殺 | 主宰 | 範圍 | 155 |

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
- Add all ten 雷-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.


**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:lightning:magic` string with no numeric
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

"(自)" annotations become `SELF_ONLY` (cardinality and faction both narrow to the actor); "(友)"
annotations stay `AREA`/`ANY` since the registry has no ally-only enum value that restricts anything —
the narrower intent is presentation-only (label/description text), not a mechanical restriction.

### `effects` per spell

| Key | `effects` | Note |
|---|---|---|
| `spark_shock` | `damage:lightning:magic` |  |
| `static_ward` | `self_buff_apply:lightning_static_ward` |  |
| `chain_lightning` | `damage:lightning:magic` |  |
| `paralyzing_bolt` | `damage:lightning:magic`, `buff_apply:paralysis` |  |
| `thunder_combo` | `damage:lightning:magic` |  |
| `lightning_strike` | `damage:lightning:magic` |  |
| `heavens_thunder` | `damage:lightning:magic` |  |
| `thunder_gods_haste` | `self_buff_apply:lightning_extra_action` |  |
| `judgement_thunder` | `damage:lightning:magic` |  |
| `divine_lightning_slaughter` | `damage:lightning:magic` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `lightning_static_ward`: self counter-attack buff (bounds-shaped defense increase), applied by `static_ward`
- `lightning_extra_action`: self extra-action buff (bounds-shaped `actions_per_turn` increase), applied by `thunder_gods_haste`

The matching `lightning_static_ward`/`lightning_extra_action` rows are also added to
`world/rules/rulebook/status_display.yaml` (Traditional Chinese labels 靜電護體/雷神之速, severities
`beneficial`/`beneficial`): `status_display.py`'s fail-closed coverage requires every buff key to have
exactly one display entry, so a new buff key without one breaks module import at startup.

### Reused existing `buffs.yaml` rows (no new row)

- `paralysis`: 麻痺電擊 (`paralyzing_bolt`) reuses the existing `paralysis` buff row exactly — no new row needed, matching this element's 麻痺 flavor precisely

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's spell rows are grouped
in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 雷 — 學徒` -style comment) around one `*_elemental_spells("lightning", ...)` block, and each pair's
MP cost falls inside §4.3's band for that tier. `static_ward` (學徒 單體(自)) and `thunder_gods_haste`
(賢者 單體(自)) are declared as their own `_skill(...)` calls directly after that block, still under
their tier comments: their `self_buff_apply` effects are inherently self-only, so they declare
`FactionConstraint.SELF_ONLY`, which the builder fixes to `ANY`. This gives
`element-mastery-cast-gate`'s tier lookup an unambiguous signal (position + cost band) without this
change adding a tier field or re-deriving gate logic itself.

### Registry construction: reuse the `_elemental_spells` builder

This change expresses eight of its ten entries through the `_spell`/`_elemental_spells` builders
introduced by `spell-catalog-fire` (see that change's design.md, "Registry construction helper")
instead of writing each `_skill(...)` call by hand: the element is written once per set, and
`SkillKind.ACTIVE` plus `FactionConstraint.ANY` are fixed by the builder. `static_ward` and
`thunder_gods_haste` are the deliberate exceptions (see "Registry ordering" above) and are written as
explicit `_skill(...)` calls with `FactionConstraint.SELF_ONLY`, because the builder's fixed `ANY`
would contradict the `skill-registry` spec's self-only-constraint rule. Field values remain exactly
this change's design-doc table.

## Risks / Trade-offs

- [Risk] This change lands before `element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.


- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `lightning_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).
