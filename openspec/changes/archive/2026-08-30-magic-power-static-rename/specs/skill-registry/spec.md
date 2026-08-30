## MODIFIED Requirements

### Requirement: Reincarnation boon labels match the preset character names
The three per-character 轉生特典 passives SHALL declare labels that read 轉生祝福·悠花
(`reincarnation_boon_yuka`), 轉生祝福·悠奈 (`reincarnation_boon_yuna`), and 轉生祝福·伊洛希雅
(`reincarnation_boon_elosia`) — each matching the `display_name` of the preset character whose kit
declares that boon in `PLAYER_PRESET_REGISTRY`. Their keys, costs, kinds, and target
specs SHALL NOT change, and each `effects` list keeps its shape with exactly one re-keying: the
伊洛希雅 boon's effect string is `growth_rate:practice:100` (D-A4 re-key of the retired
`growth_rate:magic:100` prefix; the old prefix fails registry load). The derived `status_display.yaml` row `reincarnation_boon_yuka_agility_bonus`
SHALL label itself 轉生祝福·悠花敏捷提升.

#### Scenario: Every preset-carried boon label equals its owner's display name exactly
- **WHEN** the label of each `reincarnation_boon_*` skill declared by a preset's skill kit is
  compared against that preset's `display_name`
- **THEN** the label equals exactly `轉生祝福·<display_name>` (轉生祝福·悠花, 轉生祝福·悠奈,
  轉生祝福·伊洛希雅), and the skill's `kind`, `target_spec`, `cost`, and `effects` are
  byte-identical to the shipped registry values (all PASSIVE, `TargetSpec.NONE`, empty cost,
  `growth_rate:practice:100` / `combat_prediction:武感` / `sexual_magic_mastery` respectively)

#### Scenario: The status display row follows the corrected name
- **WHEN** the `status_display.yaml` row keyed `reincarnation_boon_yuka_agility_bonus` is inspected
- **THEN** its label is 轉生祝福·悠花敏捷提升
