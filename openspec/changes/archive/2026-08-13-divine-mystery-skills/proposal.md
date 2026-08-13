## Why

World lore defines 神之秘法 (Divine Mystery) as a second, non-elemental magic system usable only by
entities with 神性 (currently: the three elf subraces), costing no mana. Per the approved design doc
(D7, §6), this round mechanizes only what already has a working substrate: 狀態偽裝 (already
`set_disguise`) and a new 性愛系統 skill routed through the already-rulebook-driven `sexual_event`
effect. `reincarnation_boon_yuna`'s effect string was also malformed (`element_mastery_rank:性魔法:主宰`,
a three-segment string inconsistent with every other mastery skill's two-segment form) — **that string
fix now lands in `skill-effects-typed-model` instead of here** (moved during rubber-duck review: the
malformed string would otherwise have broken `skill-effects-typed-model`'s own registry-load
validation the moment it landed, since no other change in the batch was a declared prerequisite of it).
This change only adds the `sexual_magic_mastery` domain's new castable-skill *behavior*.

## What Changes

- Race-gating reuses the **already-existing** `RaceProfile.can_use_divine_arts` field
  (`world/lore/races.py`, already `True` for `"elf"` and `False` for `"human"`/`"beastfolk"` per the
  landed `lore-registries` spec) — no new `RaceProfile` field is needed; the design doc's assumption
  that this field didn't exist yet was wrong, caught while writing this proposal.
- Add `SexualMasteryEffect` handling: `sexual_magic_mastery` becomes its own effect prefix (not a
  malformed variant of `element_mastery_rank`), consumed the same way `ElementMasteryEffect` is
  (ownership unlocks casting), but scoped to the non-elemental 性魔法 domain rather than one of the
  eight elements.
- Add `divine_sexual_mastery` (性魔法主宰, the skill body itself — distinct from
  `reincarnation_boon_yuna`, which grants one specific character's *innate* version) with
  `effects=["sexual_magic_mastery"]`.
- Add `divine_sexual_arts` (神之秘法：性愛系統), `usable_out_of_combat=True`, no MP/SP cost, gated on
  `can_use_divine_arts`, `effects=["sexual_event:<name>"]` targeting other entities, reusing the
  existing rule-driven `world/rules/sexual_transitions.py` engine.
- Re-tag `status_disguise` into the same 神之秘法 family (no mechanical change — still `set_disguise`).
- Add four flavor-only entries for the remaining known mysteries (時間加速/減速, 空間扭曲, 物質轉換,
  生命延續) using `DivineMysteryEffect(mechanized=False)` — ownable, race-gated, explicitly inert.

## Capabilities

### New Capabilities
- `divine-mystery`: the 神之秘法 skill family, its race-gating rule, and the mechanized/unmechanized
  split (D7).

### Modified Capabilities
- `skill-registry`: two new castable skills; four new flavor-only skills; `status_disguise` re-tagged
  (no behavior change). (`reincarnation_boon_yuna`'s effect-string fix now belongs to
  `skill-effects-typed-model`, not this change.)

## Impact

- `world/skills/registry.py` (2 new mechanized skills + 4 new flavor-only skills + 1 re-tagged skill,
  7 entries touched total), `world/skills/effects.py` (`SexualMasteryEffect`, `DivineMysteryEffect` —
  `SexualMasteryEffect`'s
  *type* is already defined by `skill-effects-typed-model`; this change only adds its two new
  consumers). No change to `world/lore/races.py` — `can_use_divine_arts` already exists and is reused
  as-is.
- Depends on `skill-effects-typed-model` (now also for the already-fixed `reincarnation_boon_yuna`
  string, which this change's own `divine_sexual_mastery`/`divine_sexual_arts` additions sit alongside).
  Does not depend on `element-mastery-cast-gate` (性魔法 is a separate, non-elemental domain —
  `SexualMasteryEffect` is its own gate concept, not routed through `can_cast_spell_tier`).
