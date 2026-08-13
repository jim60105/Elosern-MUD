## 1. Correct the label texts

- [x] 1.1 In `world/skills/registry.py`, change the labels of `reincarnation_boon_elosia`,
      `reincarnation_boon_yuka`, and `reincarnation_boon_yuna` to 轉生祝福·伊洛希雅,
      轉生祝福·悠花, and 轉生祝福·悠奈 respectively, leaving keys/effects/costs/kinds unchanged.
- [x] 1.2 In `world/rules/rulebook/status_display.yaml`, change the
      `reincarnation_boon_yuka_agility_bonus` row label to 轉生祝福·悠花敏捷提升.
- [x] 1.3 In `world/rules/rulebook/combat_modifiers.yaml`, update the comment mentioning the old
      transliteration to 轉生祝福·悠花.

## 2. Parity test and traceability

- [x] 2.1 Add a data-driven registry test with an explicit `(preset_key, boon_key, expected
      label)` table asserting each boon's label equals exactly `轉生祝福·<preset.display_name>`
      (轉生祝福·悠花 / 轉生祝福·悠奈 / 轉生祝福·伊洛希雅) AND that each boon's `kind`
      (`SkillKind.PASSIVE`), `target_spec` (`TargetSpec.NONE`), `cost` (empty), and `effects`
      are byte-identical to the shipped values (`growth_rate:magic:100` /
      `combat_prediction:武感` / `sexual_magic_mastery`), so the label fix cannot silently drift
      from the spec's exact wording or alter mechanics; assert the `status_display.yaml` row
      `reincarnation_boon_yuka_agility_bonus` label reads 轉生祝福·悠花敏捷提升; annotate with
      `covers_requirement("skill-registry::reincarnation-boon-labels-match-the-preset-character-names")`
      once `tools.spec_traceability list` confirms the ID.

## 3. Verification

- [x] 3.1 Run the full touched domains:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput
      --parallel 16 world.lore world.skills world.rules` plus
      `uv run --locked -m unittest discover -s tests -t .`.
- [x] 3.2 Sync the delta into `openspec/specs/skill-registry/spec.md`, then run
      `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked openspec validate reincarnation-boon-label-fix --strict`.
- [x] 3.3 (evidence gate: 750/760 covered; the 10 uncovered are browser-suite-only webclient requirements unaffected by this label-only change; full browser evidence belongs to the final handoff run) Produce shared evidence per AGENTS.md: run the Evennia test entry point and
      `uv run --locked -m unittest discover -s tests -t .` with the same
      `OPENSPEC_TEST_EVIDENCE` path, then run
      `uv run --locked python -m tools.spec_traceability verify --evidence <path>`.
