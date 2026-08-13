## 1. Typed effects

- [x] 1.1 Add `SexualMasteryEffect` and `DivineMysteryEffect(name, mechanized)` to
      `world/skills/effects.py`'s dispatch table (depends on `skill-effects-typed-model`)

## 2. Add registry entries

- [x] 2.1 Confirm `reincarnation_boon_yuna`'s `effects` is already `["sexual_magic_mastery"]` (fixed
      by the `skill-effects-typed-model` prerequisite — this change does not re-do that edit)
- [x] 2.2 Add `divine_sexual_mastery` (PASSIVE, flavor/title, `sexual_magic_mastery`)
- [x] 2.3 Read existing `world/rules/rulebook/`'s sexual-transition rule data to find a reusable event
      name before authoring `divine_sexual_arts`'s `sexual_event:<name>`; add new rule rows only if
      nothing existing fits
- [x] 2.4 Add `divine_sexual_arts` (ACTIVE, `usable_out_of_combat=True`, empty cost,
      `sexual_event:<name>`)
- [x] 2.5 Re-tag `status_disguise` into the 神之秘法 family (label/description update only — no
      behavior change to `set_disguise`)
- [x] 2.6 Add the four unmechanized mystery skills (時間加速/減速, 空間扭曲, 物質轉換, 生命延續) as
      `DivineMysteryEffect(mechanized=False)`, `usable_out_of_combat=True`

## 3. Race gate

- [x] 3.1 Add the `can_use_divine_arts` gate check to wherever skill-cast eligibility is validated for
      these six skills (reuse the existing field; add no new `RaceProfile` field)

## 4. Tests

- [x] 4.1 Non-elf cannot cast any of the six Divine Mystery skills
- [x] 4.2 Elf can cast `divine_sexual_arts` at zero MP/SP cost
- [x] 4.3 `divine_sexual_mastery` does not gate `divine_sexual_arts`
- [x] 4.4 The four unmechanized mysteries are castable (accepted) but produce no state change
- [x] 4.5 `reincarnation_boon_yuna` parses as `SexualMasteryEffect`, not `ElementMasteryEffect`
