## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` (§4.4) defines the full eight-
element, five-tier, 80-entry spell catalog. This change implements only the 光 (heal/purify-focused) slice: ten
`SKILL_REGISTRY` entries at the keys, labels, tiers, targets, and MP costs below, unchanged from that
table.

**§4.4 excerpt — 光 spells:**

| Key | 名稱 | 位階 | 目標 | MP |
|---|---|---|---|---|
| `heal` | 治癒術 | 學徒 | 單體 | 12 |
| `light_arrow` | 光箭術 | 學徒 | 單體 | 14 |
| `purify` | 淨化術 | 術師 | 單體 | 22 |
| `mass_heal` | 群體治癒 | 術師 | 範圍(友) | 30 |
| `advanced_heal` | 高級治癒 | 大師 | 單體 | 46 |
| `holy_shield` | 聖盾術 | 大師 | 單體 | 40 |
| `holy_radiance` | 神聖光輝 | 賢者 | 範圍 | 90 |
| `revival_light` | 復甦之光 | 賢者 | 單體 | 82 |
| `goddess_blessing` | 女神降福 | 主宰 | 範圍(友) | 145 |
| `heavens_judgment_light` | 天啟聖裁 | 主宰 | 單體 | 135 |

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
§4.4 table lists 光-element healing spells (heal, mass_heal, advanced_heal, revival_light, goddess_blessing)
as if the mechanism already existed, but it doesn't — `heal-effect-handler` is the change that adds it,
and this change is a downstream consumer of its contract, not the owner of it.

**Grammar is not yet fixed.** This proposal writes each healing spell's `effects` entry using
`heal:<single|area>`
as the best-guess shape (mirroring `damage:<element>:<school>`'s own `<prefix>:<shape>` pattern), but
the exact grammar `heal-effect-handler` settles on is that change's contract to define, not this one's.
`tasks.md` includes a task to confirm/align the grammar once `heal-effect-handler` lands, so this change
does not guess a contract it does not own.

### A second, newly discovered gap: `purify`'s cleanse/dispel mechanism

`purify`'s 解除異常狀態 (cleanse/dispel active debuffs) flavor has **no existing handler** in the codebase — grep across `world/rules/action.py`, `world/rules/buffs.py`, and `world/rules/combat.py` finds no `dispel`/`cleanse`/`purify` effect prefix or any `.remove()` call site for `BuffHandler`, even though `BuffHandler.remove()` itself exists per the `buff-handler-integration` spec. This is the same category of gap as the `heal:` prefix (a real mechanism the design doc's spell catalog implies but does not spell out), except it is not covered by any of this batch's declared dependencies. This proposal does not invent a new handler for it (that would exceed a content-change's scope per this change's Non-Goals) — it declares `purify`'s `effects` as `["cleanse:status"]` as a **provisional, unconfirmed** typed-effect grammar, and `tasks.md` includes a task to raise a `cleanse-effect-handler` prerequisite change (mirroring `heal-effect-handler`'s shape) and align `purify`'s effect string to whatever grammar that change settles on before this spell is cast-functional. Declaring `purify` with an empty `effects` list instead was rejected: that would ship a tenth dead spell, which is exactly the problem class this whole redesign exists to eliminate.

## Goals / Non-Goals

**Goals:**
- Add all ten 光-element spells to `SKILL_REGISTRY` with the exact keys/labels/tiers/targets/costs
  from §4.4, each with a typed-effect-compatible `effects` list.
- Organize the registry entries so each spell's tier is unambiguous from its position and MP cost band
  alone, for `can_cast_spell_tier` (from `element-mastery-cast-gate`) to consume without this change
  re-deriving any gate logic.
- Add the necessary `buffs.yaml` rows backing this element's status-effect and shield spells.


**Non-Goals:**
- Damage spells use the existing `damage:<element>:<school>` effect convention exactly as `fire_ball`/
  `wind_blade`/`shadow_slash` already use it today — a bare `damage:light:magic` string with no numeric
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
- **`revival_light`'s "解除瀕死" flavor does not revive a knocked-out ally.** Found during rubber-duck
  review: `world/rules/targeting.py` structurally rejects selecting an `hp <= 0` (knocked-out) entity as
  a skill target at all, and `heal-effect-handler`'s own Non-Goals explicitly exclude reviving one.
  `revival_light` resolves as an ordinary `heal:single` against an already-alive target — "解除瀕死" is
  flavor text for a large heal, not a distinct revival mechanic (same resolution as `spell-catalog-
  water`'s `tidal_revival`/`sea_of_life`).
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
| 範圍(友) | `TargetSpec.AREA` | `FactionConstraint.ANY` |

"(自)" annotations become `SELF_ONLY` (cardinality and faction both narrow to the actor); "(友)"
annotations stay `AREA`/`ANY` since the registry has no ally-only enum value that restricts anything —
the narrower intent is presentation-only (label/description text), not a mechanical restriction.

### `effects` per spell

| Key | `effects` | Note |
|---|---|---|
| `heal` | `heal:single` |  |
| `light_arrow` | `damage:light:magic` |  |
| `purify` | `cleanse:status` | pure cleanse, no damage component |
| `mass_heal` | `heal:area` |  |
| `advanced_heal` | `heal:single` |  |
| `holy_shield` | `buff_apply:light_holy_shield` | pure shield, no damage component |
| `holy_radiance` | `damage:light:magic` |  |
| `revival_light` | `heal:single` |  |
| `goddess_blessing` | `heal:area`, `buff_apply:light_blessing` |  |
| `heavens_judgment_light` | `damage:light:magic` |  |

### New `buffs.yaml` rows

Per the shared scope boundary, every status-effect or shield spell in this set is modeled via the
**existing, already-working** `buff_apply`/`self_buff_apply` effect prefixes plus a **new row** in
`world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per `buff-handler-integration`'s
existing constraints — no combat-stat multiplier configured in the buff definition itself). This change
adds:

- `light_holy_shield`: shield buff (defense bounds ceiling), applied by `holy_shield`
- `light_blessing`: party buff (rate/bounds-shaped multi-stat boost), applied by `goddess_blessing`

### Registry ordering makes tier obvious without a new field

`SkillDef` has no `tier` field — tier is derived from context. This change's ten `_skill(...)` calls are
grouped in registry order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰, each pair preceded by a
`# 光 — 學徒` -style comment), and each pair's MP cost falls inside §4.3's band for that tier. This
gives `element-mastery-cast-gate`'s tier lookup an unambiguous signal (position + cost band) without
this change adding a tier field or re-deriving gate logic itself.

## Risks / Trade-offs

- [Risk] This change lands before `heal-effect-handler`/`element-mastery-cast-gate` merge, leaving new
  keys in the registry that either fail to parse (once `skill-effects-typed-model` lands) or cast
  ungated. -> Mitigation: `tasks.md`'s first task group is a hard prerequisite gate; do not merge this
  change's registry edits until its prerequisites are confirmed landed.
- [Risk] The provisional `heal:` grammar guessed here does not match what `heal-effect-handler` ships. -> Mitigation: tasks.md includes an explicit confirm/align task; the mismatch is caught at that change's own registry-load-time validation (an unrecognized prefix raises).
- [Risk] `purify`'s provisional `cleanse:status` grammar has no owning change in this batch at all. -> Mitigation: tasks.md raises the follow-up `cleanse-effect-handler` prerequisite explicitly rather than silently shipping a dead or guessed-correct spell.
- [Risk] A future `spell-catalog-<other-element>` change picks the same `buffs.yaml` key by coincidence,
  causing a merge conflict. -> Mitigation: every new buff key in this change is prefixed with `light_`
  (or reuses an existing generic key verbatim, never inventing a second definition for it).

## Open Questions

- Exact `heal:<...>` effect-ID grammar — owned by `heal-effect-handler`, not this change; tracked as a
  task here. Exact `cleanse:<...>` effect-ID grammar and its owning change — not yet raised as a formal OpenSpec change; tracked as a task here.
