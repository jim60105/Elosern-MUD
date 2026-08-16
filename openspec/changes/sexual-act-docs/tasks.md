## 1. Confirm the documented surface this change extends

- [ ] 1.1 Re-read the `### cast` and `### combat actions` canonical entries in
  `docs/game/command-reference.md` in full and confirm their current 語法/情境/說明 rows still match
  `EXPECTED_COMMANDS["cast"]` / `["combat actions"]` in `tests/test_command_docs.py`. This change edits
  only the 說明 field of each and adds prose below `cast`'s table — it must not touch 語法 or 情境.
- [ ] 1.2 Re-read the 技能施放 section of `docs/game/commands.md` and confirm the `cast` row's link
  fragment still resolves to `command-reference?id=cast` per `docsify_slug("cast")`.
- [ ] 1.3 Confirm `world/rules/combat_view.py::group_skill_views` still groups owned skills by
  `SkillCategory`, with `sexual_act` sub-grouped by line (`group`) — the fact the `combat actions`
  extension describes.
- [ ] 1.4 Confirm `world/rules/sexual_resist.py`'s contest is still wired into every cast (in and out of
  combat) via `sexual-resist-cast-wiring`, and that `AffinitySource.SEXUAL_FORCED`'s affinity penalty is
  still applied **only** by `world/rules/combat_session.py::_scan_sexual_coercion` (in-combat). Confirm
  `world/rules/cast_settlement.py` still has **no** matching out-of-combat coercion scan — if
  `sexual-resist-out-of-combat` has since archived and added one, task 2.3's affinity bullet must drop
  its "in combat only" scoping and this task list must be revised before writing the prose.
- [ ] 1.5 Confirm `world/rules/rulebook/status_display.yaml` still carries the three condition labels
  quoted in the proposal (`high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`,
  `high_exposure_defense_penalty`) with their current Traditional Chinese labels.
- [ ] 1.6 Confirm `RaceProfile.can_use_divine_arts` and `_step1_divine_arts_gate` still gate 神之秘法
  acts by race via the pre-existing `divine_sexual_arts` skill, and that `requires_divine_arts` is still
  the field name used to identify that line. Confirm `world/skills/sexual_acts/divine.py` still ships
  either an empty `DIVINE_ACTS` tuple or real content — if `sexual-catalog-divine-core`/`-mutators` have
  since archived, this task list's Non-Goal about not describing individual divine acts still holds (this
  proposal never enumerates acts), so no task changes are needed either way.
- [ ] 1.7 Confirm how a character obtains the baseline `divine_sexual_arts` gate skill (character
  creation grant, race default, or otherwise) against `world/lore/player_presets.py` or the actual
  creation-time skill grant, so task 2.3's divine-arts bullet states the gate accurately.

## 2. `docs/game/command-reference.md`: extend `cast` and `combat actions`

- [ ] 2.1 Append one clause to the `cast` entry's 說明 field stating that a character's unlocked 性愛
  skills are cast through the same `cast <skill_key>[@<scale>][=<target_key>]` syntax once unlocked by
  play. The field must contain the substrings `性愛` and `解鎖`.
- [ ] 2.2 Append one clause to the `combat actions` entry's 說明 field stating that owned skills are
  grouped by category, and that unlocked 性愛 acts form their own category (sub-grouped by line) once a
  character meets that act's unlock requirement. The field must contain the substring `性愛`.
- [ ] 2.3 Add a Markdown prose block directly below the `cast` field table, still under the `### cast`
  heading (before the next `## 公會` heading), covering:
  - Unlock is play-driven; nothing beyond the baseline `divine_sexual_arts` cast-gate skill is available
    at character creation (per task 1.7's finding on how that baseline skill is granted).
  - A resistible act's target gets one resist roll, in or out of combat: success wastes the caster's
    turn and the act does not execute; failure executes it. (Must contain the substring `抵抗`.)
  - Forcing a companion NPC **in combat** (a failed resist during a fight) costs relationship affinity
    and can trigger the companion auto-leaving the party; the caster is notified when that happens.
    State this explicitly as a combat-scoped consequence (e.g. "戰鬥中強迫...") — do NOT imply it also
    applies to an out-of-combat cast; that mechanism (`sexual-resist-out-of-combat`) is not shipped as of
    this writing (re-check task 1.4 before writing this sentence). (Must contain the substring `好感度`
    and a combat-scoping word such as `戰鬥`.)
  - Sustained arousal, an in-progress climax, and high exposure show up as ordinary combat condition
    labels while active — name the three labels from task 1.5. (Must contain the substring `興奮`.)
  - 神之秘法 (divine arts) acts require a race-eligible caster. Do not enumerate or describe individual
    divine-arts acts — re-check task 1.6 first; if the catalog proposals are still open, only the
    pre-existing race gate is a documentable fact. (Must contain the substring `神之秘法`.)
- [ ] 2.4 Re-read the edited `### cast` section top to bottom and confirm no line accidentally matches
  the `| field | value |` table-row pattern for a `CANONICAL_FIELDS` name outside the original table —
  such a line would silently overwrite that field when `parse_canonical_entries` re-parses the section.

## 3. `docs/game/commands.md`: extend the `cast` row

- [ ] 3.1 Extend the `cast` row's description in the 技能施放 table: mention that sexual-act skills are
  included among castable skills, unlocked through play, and discoverable through `combat actions`'s
  category grouping. The row's description must contain the substring `性愛`.

## 4. Protect the new content with a contract test

- [ ] 4.1 In `tests/test_command_docs.py`, add `test_cast_and_combat_actions_document_sexual_acts`
  (or extend the existing cast-scale test class) asserting: `entries["cast"]["說明"]` contains `性愛`
  and `解鎖`; `entries["combat actions"]["說明"]` contains `性愛`; the full `### cast` section text
  (table plus trailing prose — read the raw reference file between the `### cast` and next `## `
  heading) contains `抵抗`, `好感度`, `興奮`, and `神之秘法`. Decorate it with
  `@covers_requirement("game-command-docs::the-command-reference-documents-the-resist,-in-combat-affinity,-and-status-consequences")`
  or the equivalent ID from `tools.spec_traceability list` for the two new requirements this change adds
  — use `tools.spec_traceability list` to get the real slug rather than trusting this placeholder.
- [ ] 4.2 Add a second assertion (or extend `test_overview_groups_commands_by_category` /
  `test_overview_links_only_documented_keys_and_all_keys`'s test class) verifying the `cast` row text in
  `docs/game/commands.md` contains `性愛`, decorated with the matching `covers_requirement` ID for "The
  overview page describes the sexual act system's discoverability".
- [ ] 4.3 Run `uv run --locked python -m pytest tests/test_command_docs.py -q` and confirm every
  existing test still passes alongside the new ones (in particular
  `test_no_orphan_canonical_entries`, `test_cast_entry_documents_the_freeform_scale_token`, and
  `test_overview_links_only_documented_keys_and_all_keys`).

## 5. Validate and sync

- [ ] 5.1 Run `tools.spec_traceability list` (or the project's equivalent invocation) to obtain the
  exact requirement IDs for the two new `game-command-docs` requirements and fix the `covers_requirement`
  decorators from tasks 4.1/4.2 if the derived IDs differ from the placeholder above.
- [ ] 5.2 Run `openspec validate --change sexual-act-docs --strict` and fix any reported issues.
- [ ] 5.3 Sync the delta spec into `openspec/specs/game-command-docs/spec.md` and archive this change.
- [ ] 5.4 Run `openspec validate --all --strict` to confirm the full spec tree still passes.
