## Context

`world/skills/registry.py` ships three per-character passives keyed `reincarnation_boon_elosia`
(轉生祝福·艾露西亞), `reincarnation_boon_yuka` (轉生祝福·由花), `reincarnation_boon_yuna`
(轉生祝福·由奈). The preset catalog (`world/lore/player_presets.py`, landed in
`preset-skill-kits`) binds these skills to template characters named 伊洛希雅、悠花、悠奈, whose
display names use different transliterations. Player-facing skill labels are rendered from
`SkillDef.label`; `world/rules/rulebook/status_display.yaml` additionally carries a derived status
label for `reincarnation_boon_yuka_agility_bonus`, and `combat_modifiers.yaml` has a code comment
referencing the old name. No test or main-spec requirement pins the old label texts, so the
correction is a pure presentation-content change.

## Goals / Non-Goals

**Goals:**
- Correct the three boon labels (and the derived status label/comment) to match the preset
  display names.
- Add a parity test so boon labels and preset display names cannot drift apart again.

**Non-Goals:**
- No change to keys, effects, costs, kinds, target specs, or any mechanical behavior.
- No change to the story-character files under `tmp/`.
- No migration or backward-compatibility layer (project unreleased, zero users).

## Decisions

**D1. Label text.** 轉生祝福·艾露西亞 → 轉生祝福·伊洛希雅; 轉生祝福·由花 → 轉生祝福·悠花;
轉生祝福·由奈 → 轉生祝福·悠奈. The label prefix 轉生祝福· is retained; only the character-name
transliteration segment changes, keeping the visual rhythm of the existing skill family.

**D2. Status display and comments.** `status_display.yaml` row `reincarnation_boon_yuka_agility_bonus`
label becomes 轉生祝福·悠花敏捷提升 (the `*_agility_bonus` suffix and code stay byte-identical), and
the `combat_modifiers.yaml` comment is updated to 悠花. These are player-visible/developer-visible
text derived from the same name and must move with the registry labels.

**D3. Parity test.** A data-driven registry test with an explicit `(preset_key, boon_key,
expected label)` table asserts each boon's label equals exactly `轉生祝福·<preset.display_name>`
(exact equality, not `contains`, so a format drift like 轉生祝福·悠花（武感） fails), AND pins each
boon's `kind` (`PASSIVE`), `target_spec` (`TargetSpec.NONE`), `cost` (empty), and `effects`
byte-identical to the shipped values, so the "mechanics SHALL NOT change" clause of the requirement
is actually tested. Renaming a preset or relabeling a boon fails the test until the other side is
updated deliberately.

**D4. Spec delta.** Add one requirement to the `skill-registry` main spec stating the three boon
labels SHALL read 轉生祝福·悠花/悠奈/伊洛希雅 and SHALL match the preset display names, with the
parity test annotated via `covers_requirement` for traceability.

## Risks / Trade-offs

- **Label text in tests is content, not behavior**: the parity test couples skill labels to preset
  display names, which is exactly the drift we want to prevent; the coupling is intentional and
  scoped to the three boons.
- **None mechanical**: labels are presentation-only in every consumer (skill menu, event log,
  status display), so no downstream computation changes.
