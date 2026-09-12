## MODIFIED Requirements

### Requirement: divine_sexual_mastery and divine_sexual_arts exist as distinct skills
`SKILL_REGISTRY` SHALL contain `divine_sexual_mastery` (性魔法主宰, `PASSIVE`,
`effects=["sexual_magic_mastery"]`, flavor/title content not gating any other skill's castability in
this change) and `divine_sexual_arts` (神之秘法：性愛系統, `ACTIVE`, `usable_out_of_combat=True`, empty
`cost`, `effects=["sexual_event_target:stimulus_applied"]`), both gated by `can_use_divine_arts` per
the `divine-mystery` capability's requirement. `divine_sexual_arts` SHALL be registered through
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` catalogue row rather than an inline
`SKILL_REGISTRY` entry in `world/skills/registry.py`, so its `SKILL_REGISTRY` entry and its
`SEXUAL_ACT_REGISTRY` row are the same paired objects the catalogue import installs.

#### Scenario: divine_sexual_mastery does not gate divine_sexual_arts
- **WHEN** an elf entity owns `divine_sexual_arts` but not `divine_sexual_mastery`
- **THEN** casting `divine_sexual_arts` is not rejected for lacking `divine_sexual_mastery`

#### Scenario: divine_sexual_arts is registered through the catalogue
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` and `SEXUAL_ACT_REGISTRY["divine_sexual_arts"]` are
  inspected
- **THEN** both exist, share the key, and the `SkillDef` is one the sexual-acts catalogue package
  registered — `world/skills/registry.py` defines no inline entry for the key

#### Scenario: divine_sexual_arts carries the target-scoped stimulus effect
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"].effects` is inspected
- **THEN** it equals `["sexual_event_target:stimulus_applied"]` and its parsed effects resolve to a
  single `TargetSexualEventEffect`

#### Scenario: every world.skills import installs the catalogue rows
- **WHEN** a fresh process imports `world.skills.registry` (or any module under `world.skills`)
  before any other game module
- **THEN** `SKILL_REGISTRY` already contains every `SEXUAL_ACT_REGISTRY` key, including
  `divine_sexual_arts`, because `world/skills/__init__.py` installs the sexual-act catalogue as its
  final bootstrap edge — registry assembly never depends on which module the host imports first
