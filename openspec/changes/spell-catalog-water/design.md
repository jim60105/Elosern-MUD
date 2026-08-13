## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 水 (heal/defense-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 水 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `water_bolt` | 水箭術 | 學徒 | 單體 | 12 |
| `minor_heal` | 治癒滴露 | 學徒 | 單體 | 11 |
| `healing_spring` | 治癒之泉 | 術師 | 範圍 | 28 |
| `water_shield` | 水盾術 | 術師 | 單體 | 22 |
| `abyssal_whirlpool` | 深海漩渦 | 大師 | 範圍 | 50 |
| `wellspring_of_life` | 生命湧泉 | 大師 | 單體 | 40 |
| `tsunami` | 海嘯術 | 賢者 | 範圍 | 95 |
| `tidal_revival` | 復生之潮 | 賢者 | 單體 | 78 |
| `sea_of_life` | 生命之海 | 主宰 | 範圍 | 160 |
| `abyssal_tide` | 深淵巨潮 | 主宰 | 範圍 | 145 |

**§4.3 MP cost-tier table** (for reference — the MP column above is already the correct
tier-consistent value, this table is the source it was drawn from):

| Tier | Level band | Single/direct-effect MP | Area/strong-effect MP |
|---|---|---|---|
| 學徒 | 0-15 | 10-16 | 14-20 |
| 術師 | 16-30 | 20-28 | 26-34 |
| 大師 | 31-70 | 35-48 | 45-60 |
| 賢者 | 71-90 | 65-85 | 80-110 |
| 主宰 | 90+ | 120-150 | 140-180 |


### The `heal:` effect prefix does not exist yet — this is a real gap, not an oversight

No heal mechanism exists anywhere in the current codebase. `world/rules/combat.py` implements
`damage:<element>:<school>` (parsed by `_parse_damage_effect`) with a cast-time handler wired into
`world/rules/action.py`'s `_EFFECT_HANDLERS`; there is no equivalent for restoring HP. The design doc's
§4.4 table lists 水-element healing spells (minor_heal, healing_spring, wellspring_of_life, tidal_revival, sea_of_life)
as if the mechanism already existed, but it doesn't — `heal-effect-handler` is the change that adds it,
and this change is a downstream consumer of its contract, not the owner of it.

**Grammar is not yet fixed.** This proposal writes each healing spell's `effects` entry using
`heal:<single|area>`
as the best-guess shape (mirroring `damage:<element>:<school>`'s own `<prefix>:<shape>` pattern), but
the exact grammar `heal-effect-handler` settles on is that change's contract to define, not this one's.
`tasks.md` includes a task to confirm/align the grammar once `heal-effect-handler` lands, so this change
does not guess a contract it does not own.

## Goals / Non-Goals

**Goals:**
- Add all ten 水-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.


**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:water:magic` string with no numeric
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
- **`tidal_revival`'s "瀕死急救型大量治療" and `sea_of_life`'s "瀕死急救" flavor do not revive a
  knocked-out ally.** Found during rubber-duck review: `world/rules/targeting.py` structurally rejects
  selecting an `hp <= 0` (knocked-out) entity as a skill target at all (`_validate_alive`'s
  `target_dead` rejection, and AREA shorthand's exclusion of `knocked_out` entities), and
  `heal-effect-handler`'s own Non-Goals explicitly exclude reviving one. Both spells resolve as ordinary
  `heal:single`/`heal:area` against an already-alive target — the "emergency rescue" framing is flavor
  text describing a large heal, not a distinct revival mechanic. A future battlefield-state change could
  add real revival; this change does not.
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
| `water_bolt` | `damage:water:magic` |  |
| `minor_heal` | `heal:single` |  |
| `healing_spring` | `heal:area` |  |
| `water_shield` | `buff_apply:water_shield` | pure shield, no damage component |
| `abyssal_whirlpool` | `damage:water:magic`, `buff_apply:water_bind` |  |
| `wellspring_of_life` | `heal:single` |  |
| `tsunami` | `damage:water:magic` |  |
| `tidal_revival` | `heal:single` |  |
| `sea_of_life` | `heal:area` |  |
| `abyssal_tide` | `damage:water:magic` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `water_shield`: bounds-shaped defense buff (temporarily raises the `defense` bounds ceiling), applied by `water_shield`
- `water_bind`: marker control buff (empty `modifiers`, same shape as the existing `paralysis`/`fear` rows) representing 束縛, applied by `abyssal_whirlpool`

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's ten spell rows are grouped
in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 水 — 學徒` -style comment) inside one `*_elemental_spells("water", ...)` block, and each pair's MP
cost falls inside §4.3's band for that tier. This gives `element-mastery-cast-gate`'s tier lookup an
unambiguous signal (position + cost band) without this change adding a tier field or re-deriving gate
logic itself.

### Registry construction: reuse the `_elemental_spells` builder

This change expresses its entries through the `_spell`/`_elemental_spells` builders introduced by
`spell-catalog-fire` (see that change's design.md, "Registry construction helper") instead of writing
each `_skill(...)` call by hand: the element is written once per set, and `SkillKind.ACTIVE` plus
`FactionConstraint.ANY` are fixed by the builder. Field values remain exactly this change's
design-doc table.

## Risks / Trade-offs

- [Risk] This change lands before `heal-effect-handler`/`element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.
- [Risk] The provisional `heal:` grammar guessed here does not match what `heal-effect-handler` ships. -> Mitigation: tasks.md includes an explicit confirm/align task; the mismatch is caught at that change's own registry-load-time validation (an unrecognized prefix raises).

- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `water_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).

## Open Questions

- Exact `heal:<...>` effect-ID grammar — owned by `heal-effect-handler`, not this change; tracked as a
  task here.
