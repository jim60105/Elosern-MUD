## ADDED Requirements

### Requirement: Divine Mystery skills are gated by RaceProfile.can_use_divine_arts
The six 神之秘法 family skills (`divine_sexual_mastery`, `divine_sexual_arts`, and the four
unmechanized mysteries) SHALL declare `SkillDef.requires_divine_arts=True` and be ownable/castable
only by an entity whose race's `RaceProfile.can_use_divine_arts` is `True`. Skills without the marker
(including the generic `sexual_event` mechanism) SHALL NOT be race-gated by this change. This
change SHALL NOT modify `can_use_divine_arts` itself or its existing per-race values — it only adds
consumers gated by the already-landed field.

#### Scenario: A non-elf cannot cast a Divine Mystery skill even if granted ownership
- **WHEN** a `human` or `beastfolk` entity somehow owns `divine_sexual_arts`
- **THEN** casting it is rejected, since `RACE_REGISTRY["human"].can_use_divine_arts` and
  `RACE_REGISTRY["beastfolk"].can_use_divine_arts` are both `False`

#### Scenario: An elf can cast divine_sexual_arts at no MP/SP cost
- **WHEN** an elf entity owning `divine_sexual_arts` casts it at a valid target
- **THEN** the cast is not rejected for insufficient MP or SP (the skill's `cost` is empty), and it
  resolves via the existing `sexual_event` effect handler

### Requirement: Unmechanized Divine Mysteries are explicitly declared, not silently missing
`SKILL_REGISTRY` SHALL contain four entries for 時間加速/減速, 空間扭曲, 物質轉換, and 生命延續, each
using `effects=["divine_mystery:<name>"]` where `parse_effect` resolves to
`DivineMysteryEffect(name=<name>, mechanized=False)`. No consumer in `world/rules/` SHALL treat a
`mechanized=False` `DivineMysteryEffect` as anything other than flavor text.

#### Scenario: The four unmechanized mysteries exist and are race-gated like their mechanized siblings
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains four entries whose parsed effect is `DivineMysteryEffect(mechanized=False)`,
  each `usable_out_of_combat=True` and gated by `can_use_divine_arts` the same way
  `divine_sexual_arts` is

#### Scenario: Casting an unmechanized mystery has no mechanical effect
- **WHEN** an eligible entity casts one of the four unmechanized mystery skills
- **THEN** the cast is accepted (not rejected as unknown) but produces no state change beyond whatever
  narrative/log presentation the resolver already gives any successfully-cast skill
