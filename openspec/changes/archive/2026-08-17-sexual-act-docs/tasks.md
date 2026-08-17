## 1. Confirm the documented surface this change extends

- [x] 1.1 Re-read the `### cast` and `### combat actions` canonical entries in
  `docs/game/command-reference.md` in full and confirm their current 語法/情境/說明 rows still match
  `EXPECTED_COMMANDS["cast"]` / `["combat actions"]` in `tests/test_command_docs.py`. This change edits
  only the 說明 field of each and adds prose below `cast`'s table — it must not touch 語法 or 情境.
- [x] 1.2 Re-read the 技能施放 section of `docs/game/commands.md` and confirm the `cast` row's link
  fragment still resolves to `command-reference?id=cast` per `docsify_slug("cast")`.
- [x] 1.3 Confirm `world/rules/combat_view.py::group_skill_views` still groups owned skills by
  `SkillCategory`, with `sexual_act` sub-grouped by line (`group`) — the fact the `combat actions`
  extension describes.
- [x] 1.4 Confirm `world/rules/sexual_resist.py`'s contest is still wired into every cast (in and out of
  combat) via `sexual-resist-cast-wiring` (`action.py::_step4b_sexual_resist_gate`), and that
  `AffinitySource.SEXUAL_FORCED`'s affinity penalty is applied by **both**
  `world/rules/combat_session.py::_scan_sexual_coercion` (in-combat) and the archived
  `sexual-resist-out-of-combat`'s `world/rules/cast_settlement.py::_scan_out_of_combat_sexual_coercion`
  (out of combat, wired into `settle_out_of_combat_cast`). Verified: both scans exist and run inside
  transactions covering the resulting auto-leave; task 2.3's affinity bullet therefore states the
  consequence **without** "in combat only" scoping.
- [x] 1.5 Confirm `world/rules/rulebook/status_display.yaml` still carries the three condition labels
  quoted in the proposal (`high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`,
  `high_exposure_defense_penalty`) with their current Traditional Chinese labels.
- [x] 1.6 Confirm `RaceProfile.can_use_divine_arts` and `action.py::_step1_divine_arts_gate` still gate
  神之秘法 acts by race via the pre-existing `divine_sexual_arts` skill, and that
  `requires_divine_arts` is still the field name used to identify that line.
  `sexual-catalog-divine-core`/`-mutators` have since archived and `world/skills/sexual_acts/divine.py`
  ships the seven acts; this task list's Non-Goal about not describing individual divine acts still
  holds (this proposal never enumerates acts), so the prose documents only the race gate.
- [x] 1.7 Confirm how a character obtains the baseline `divine_sexual_arts` gate skill. Verified:
  `world/lore/player_presets.py` grants it as an active skill only on presets whose race declares
  `can_use_divine_arts=True` (the 悠奈 darknight preset; elf is the only race with the flag), so the
  baseline gate skill is available from character creation only to divine-affinity races.

## 2. `docs/game/command-reference.md`: extend `cast` and `combat actions`

- [x] 2.1 Append one clause to the `cast` entry's 說明 field stating that a character's unlocked 性愛
  skills are cast through the same `cast <skill_key>[@<scale>][=<target_key>]` syntax, with basic seed
  acts available at creation and the rest unlocking through play. The field must contain the
  substrings `性愛` and `解鎖`.
- [x] 2.2 Append one clause to the `combat actions` entry's 說明 field stating that owned skills are
  grouped by category, and that unlocked 性愛 acts form their own category (sub-grouped by line) once a
  character meets that act's unlock requirement. The field must contain the substring `性愛`.
- [x] 2.3 Add a Markdown prose block directly below the `cast` field table, still under the `### cast`
  heading (before the next `## 公會` heading), covering — corrected per the implementation rubber-duck
  review, which verified `unlocked_act_keys_for()` semantics and the resist wiring in `action.py`:
  - Unlock is per-act: seed acts with an empty unlock table (solo 3, shame 1, partner 2, combat 1) are
    owned from character creation; every other act gates on play-earned counters. (Must contain the
    substring `解鎖`.)
  - A resistible act's target gets one resist roll, in or out of combat: a successful resist leaves
    that target unaffected by the cast's target effects, while the cast still consumes time and the
    skill's resource cost (if any) and the caster's own effects still apply; failure executes the act
    against the target. Do NOT claim "the cast does not execute" — actor-side effects and practice XP
    still run (verified `_step5_effect_resolution`/`_step6_skill_practice` are unconditional), and
    divine acts declare `cost={}`. (Must contain the substrings `抵抗` and `戰鬥`.)
  - Forcing a companion NPC (a failed resist) costs relationship affinity and can trigger the companion
    auto-leaving the party; the caster is notified when that happens. State the consequence as applying
    to forced acts generally — `sexual-resist-out-of-combat` has archived and an out-of-combat cast
    incurs the same penalty (re-check task 1.4 before writing this sentence). (Must contain the
    substring `好感度`.)
  - Sustained arousal, an in-progress climax, and high exposure show up as ordinary combat condition
    labels while active — name the three labels from task 1.5. (Must contain the substrings `興奮`,
    `高潮`, and `露出`.)
  - 神之秘法 (divine arts) acts require a race-eligible caster and have no counter unlock threshold
    (their containment is the cast-time race gate). Do not enumerate or describe individual divine-arts
    acts — none of the seven labels may appear in the section. (Must contain the substring `神之秘法`.)
- [x] 2.4 Re-read the edited `### cast` section top to bottom and confirm no line accidentally matches
  the `| field | value |` table-row pattern for a `CANONICAL_FIELDS` name outside the original table —
  such a line would silently overwrite that field when `parse_canonical_entries` re-parses the section.

## 3. `docs/game/commands.md`: extend the `cast` row

- [x] 3.1 Extend the `cast` row's description in the 技能施放 table: mention that sexual-act skills are
  included among castable skills, unlocked through play, and discoverable through `combat actions`'s
  category grouping. The row's description must contain the substring `性愛`.

## 4. Protect the new content with a contract test

- [x] 4.1 In `tests/test_command_docs.py`, add `test_cast_and_combat_actions_document_sexual_acts`
  asserting: `entries["cast"]["說明"]` contains `性愛` and `解鎖`; `entries["combat actions"]["說明"]`
  contains `性愛`; the full `### cast` section text (table plus trailing prose — read the raw reference
  file between the `### cast` and next `## ` heading) contains `抵抗`, `好感度`, `解鎖`, `興奮`, `高潮`,
  `露出`, `戰鬥`, and `神之秘法`, and contains none of the seven divine-arts act labels
  (絕頂律令, 時姦, 神域搾取, 感度創世, 恥辱剝奪, 絕對從屬, 無垢回歸). Decorate it with
  `@covers_requirement("game-command-docs::the-command-reference-documents-the-sexual-act-system", "game-command-docs::the-command-reference-documents-the-resist-affinity-and-status-consequences")`
  — verify both slugs against `tools.spec_traceability list` in task 5.1 after the delta sync.
- [x] 4.2 Add a second assertion (or extend `test_overview_groups_commands_by_category` /
  `test_overview_links_only_documented_keys_and_all_keys`'s test class) verifying the `cast` row text in
  `docs/game/commands.md` contains `性愛` (and, per the spec scenario, mentions that such skills are
  unlocked through play — assert `解鎖` as well), decorated with
  `@covers_requirement("game-command-docs::the-overview-page-describes-the-sexual-act-system-s-discoverability")`.
- [x] 4.3 Run `uv run --locked python -m unittest discover -s tests -t . -p test_command_docs.py -v`
  (the repository has no pytest; this is the documented unittest entry point for top-level regression
  tests) and confirm every existing test still passes alongside the new ones (in particular
  `test_no_orphan_canonical_entries`, `test_cast_entry_documents_the_freeform_scale_token`, and
  `test_overview_links_only_documented_keys_and_all_keys`).

## 5. Validate and sync

- [x] 5.1 Run `uv run --locked python -m tools.spec_traceability list` after the delta sync (task 5.3)
  and confirm the three new `game-command-docs` requirement IDs match the `covers_requirement` slugs
  used in tasks 4.1/4.2; fix any mismatch.
- [x] 5.2 Run `openspec validate --change sexual-act-docs --strict` and fix any reported issues.
- [x] 5.3 Sync the delta spec into `openspec/specs/game-command-docs/spec.md` and archive this change.
- [x] 5.4 Run `openspec validate --all --strict` to confirm the full spec tree still passes.
