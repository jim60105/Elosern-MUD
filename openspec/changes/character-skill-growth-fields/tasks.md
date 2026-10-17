# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Rules reads (2h)

- [ ] 1.1 Add `freeform_ladder_for` and a lineage-position read; verify unit tests for a mastery owner with locked rungs (unlock levels from a synthetic anchored ladder), a non-master (no ladder), a zero adjusted cost, and prerequisite/next lists for a two-parent merge node.

## 2. character v9 rows and selected skill (3.5h)

- [ ] 2.1 Add the compact row facts and bump to v9; verify presenter tests (fresh true then false in a new session, booked flag, capped row) and a maximal fixture (96 rows, all sections at cap, full `selected_skill`) within 65,536 bytes.
- [ ] 2.2 Extend `party.view_member` to `{member_id, tab, skill_key}` with the stored selection and add `selected_skill` (lineage, ladder) to the panel; verify action schema tests, null for unowned/unknown keys, the validator exactly-one-of rung rule and the JS mirror parity.

## 3. Transitional client and integration (1.5h)

- [ ] 3.1 Make `SkillBook.vue`/`SkillDetailPane.vue` read unlocked rungs from `freeform_ladder`; verify Vitest scale rendering; annotate canonical IDs for the renamed/modified and added `webclient-exploration-menu` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate character-skill-growth-fields --strict`.
