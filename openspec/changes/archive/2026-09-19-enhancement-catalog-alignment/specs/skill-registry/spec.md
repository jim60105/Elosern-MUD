## MODIFIED Requirements

### Requirement: flight and flash_step are PASSIVE
`flight` and `flash_step` SHALL declare `kind=SkillKind.PASSIVE` (reclassified from the previous
`SkillKind.ACTIVE`, which had no working cast path — `movement` was never registered in `action.py`'s
`_EFFECT_HANDLERS`). Ownership alone triggers the waiver behavior defined by the
`movement-cost-charging` capability; no cast action exists for either skill. Both SHALL declare an
empty `cost`: a PASSIVE skill has no cast action from which any resource could be deducted, so a
non-empty cost on either is inert data that can only mislead.

#### Scenario: flight is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player attempts to cast `flight`
- **THEN** the attempt is rejected the same way casting any other `PASSIVE` skill is rejected

#### Scenario: Neither movement waiver declares a spendable cost
- **WHEN** the `cost` of `flight` and of `flash_step` is inspected
- **THEN** both are empty

### Requirement: Reincarnation boon labels match the preset character names
The three per-character 轉生特典 passives SHALL declare labels that read 轉生祝福·悠花
(`reincarnation_boon_yuka`), 轉生祝福·悠奈 (`reincarnation_boon_yuna`), and 轉生祝福·伊洛希雅
(`reincarnation_boon_elosia`) — each matching the `display_name` of the preset character whose kit
declares that boon in `PLAYER_PRESET_REGISTRY`. Their keys, costs, kinds, and target
specs SHALL NOT change, and each `effects` list keeps its shape with exactly one re-keying: the
伊洛希雅 boon's effect string is `growth_rate:practice:5:wind` — a scoped growth rate naming the wind
tree, replacing the unscoped `growth_rate:practice:100`, whose three-segment form no longer parses. The derived `status_display.yaml` row `reincarnation_boon_yuka_agility_bonus`
SHALL label itself 轉生祝福·悠花敏捷提升.

#### Scenario: Every preset-carried boon label equals its owner's display name exactly
- **WHEN** the label of each `reincarnation_boon_*` skill declared by a preset's skill kit is
  compared against that preset's `display_name`
- **THEN** the label equals exactly `轉生祝福·<display_name>` (轉生祝福·悠花, 轉生祝福·悠奈,
  轉生祝福·伊洛希雅), and the skill's `kind`, `target_spec`, `cost`, and `effects` are
  byte-identical to the shipped registry values (all PASSIVE, `TargetSpec.NONE`, empty cost,
  `growth_rate:practice:5:wind` / `combat_prediction:武感` / `sexual_magic_mastery` respectively)

#### Scenario: The status display row follows the corrected name
- **WHEN** the `status_display.yaml` row keyed `reincarnation_boon_yuka_agility_bonus` is inspected
- **THEN** its label is 轉生祝福·悠花敏捷提升
