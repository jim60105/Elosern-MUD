# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Party v3 presenter and validator (2.5h)

- [ ] 1.1 Bump `party.py` to v3 with the commander row, MP/SP, `role`, `knocked_out`, `unread` (from the copied unlock snapshot) and `viewed_member_id`; verify presenter tests for ordering, null bond/membership on the commander row, true traits under disguise, possession-identical payloads, fallback after leave/delete, and a maximal 17-row payload within the byte bound.

## 2. Selection and action (2h)

- [ ] 2.1 Add `party_view_selection.py`, the copied context field and `party.view_member` (`{member_id, tab}`); verify action tests for exact schema, forged member rejection without substitution, absent-but-effective member accepted, selection surviving a possession transition, skills-tab clearing only that member's unread mark, and the registry composition test.

## 3. JS mirror and consumers (1.5h)

- [ ] 3.1 Update the JS protocol mirror, parity contract and fixtures to v3; make `PartyDrawer.vue`, `CompanionLineup`, `party-helpers.js` and the combat HUD join skip the commander row; verify the Node gate mirror tests and the touched Vitest files.

## 4. Integration (1h)

- [ ] 4.1 Annotate canonical IDs for the renamed/modified and added `webclient-party-panel` requirements and the modified `webclient-action-dispatch` requirement, register any new test module in one shard, run `uv run --locked python -m tools.contract_gate` and `openspec validate party-panel-v3-view-member --strict`.
