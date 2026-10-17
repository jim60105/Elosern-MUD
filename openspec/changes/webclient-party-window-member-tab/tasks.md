# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Window shell (2.5h)

- [ ] 1.1 Implement `PartyWindow.vue` on `WindowFrame`/`MemberRail` with tab memory and server-truth selection; mount it under the `party` drawer key; verify Vitest dispatch payloads, pending state, adoption of `viewed_member_id`, fallback reset of local item/quantity, and identical rendering with and without possession.

## 2. 成員 tab (2.5h)

- [ ] 2.1 Implement `PartyMemberTab.vue` (companion, commander, 空位) from `party_member` descriptors, move persona editing into it, and route stage-lineup activation to 成員 with that companion; verify Vitest two-step leave with Escape cancel, 人物卡 opening `NpcPersonaEditor`, 附身/解除附身 dispatch, persona edit submit and refresh, empty-slot descriptor, and the no-rule-prose text check.

## 3. Deletion and stories (1h)

- [ ] 3.1 Delete `PartyDrawer.vue`, its story, `Overlays/PartyDrawer` manifest title, its tests and duplicate `.elosern-root` rules; add stories for the four member states at both viewport sizes; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 4. Integration (1h)

- [ ] 4.1 Add one browser method opening the window and switching members, registered in `.github/browser-shards.json`; update `web/webclient-app/AGENTS.md`; annotate canonical IDs for the renamed/modified and added requirements; run the touched Vitest files, `tests.test_evennia_test_optimization_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-window-member-tab --strict`.

## Workflow follow-up

- After archive, edit `openspec/specs/webclient-party-panel/spec.md` `## Purpose` by hand (delta specs cannot change an existing Purpose): replace "the version-1 `party` presentation panel … that the companion quickbar and party drawer consume" with the version-3 panel consumed by the companion quickbar and the party window, then rerun `openspec validate --all --strict`.
