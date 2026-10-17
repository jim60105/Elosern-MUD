# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Tab browsing (2.5h)

- [ ] 1.1 Port segment, search and category tree into `PartySkillTab.vue` with meters, levels, 新 tags, detail card, lineage-position links and the 威力與消耗 ladder; verify re-pointed Vitest ordering/search tests, ladder rendering for master and non-master, and the `tab: skills` selection dispatch.

## 2. Actions (1.5h)

- [ ] 2.1 Wire 施放 to the caster-explicit skill-use flow and 排入修煉 to `explore.practice {actor_id, skill}`, both disabled with committed reasons in combat; verify Vitest payloads, dock handoff closing the window, and combat-disabled reasons.

## 3. Deletion, stories and docs (2h)

- [ ] 3.1 Delete `SkillBook.vue`, its story, manifest title, tests and duplicate `.elosern-root` rules; add skill stories (book, freeform scales, in combat) at both sizes; update the graphical-use paragraph in `docs/game/commands.md` (and `tests/test_command_docs.py` if affected) and `web/webclient-app/AGENTS.md`; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 4. Integration (1h)

- [ ] 4.1 Add one browser method casting a companion field heal from the tab, registered in `.github/browser-shards.json`; annotate canonical IDs for the renamed/modified/added requirements; run the touched Vitest files, `tests.test_evennia_test_optimization_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-skill-tab --strict`.
