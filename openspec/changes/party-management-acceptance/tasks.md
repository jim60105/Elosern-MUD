# Tasks

Total estimate: **7.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Help content (1.5h)

- [ ] 1.1 Add the 隊伍 help section (follow rules, transfer rules, combat restrictions, 系譜 legend with shape and text, one-price shop convention, P B C K L J M hotkeys) and its story; verify a Vitest content test and that no party or shop window renders rule prose.

## 2. Residue sweep (1h)

- [ ] 2.1 Search for any remaining reference to the seven deleted components (code, stories, CSS, `.elosern-root` duplicates, tests, specs, manifest) and remove it in its owning change if found; verify `pnpm run build-storybook`, `pnpm run showcase-coverage` and `tests.test_webclient_frozen_contract`.

## 3. Assembled acceptance (4h)

- [ ] 3.1 Run the agent-browser journey: buy potions for 艾拉, transfer some to 卡恩, re-equip 艾拉, cast a field heal as 艾拉, have 艾拉 open combat on a monster through the 開戰並施放 confirmation (cancel once, then confirm) and finish the encounter, possess 艾拉 and walk her through an exit confirming the player's body and 卡恩 follow, and confirm the party window, shop and navigation are unchanged, then in combat re-equip a companion and observe transfer disabled with 戰鬥中無法交換物品; record each step's committed state.
- [ ] 3.2 Exercise each text command once in a live session (`給`, `取回`, `裝備 = 成員`, `買`/`賣 = 成員`, `使用 = 成員`, `cast 由 成員`, `修煉 = 成員`, `狀態`, `技能`, `系譜`) and record the transcript lines.

## 4. Integration (1h)

- [ ] 4.1 Register the help browser method in `.github/browser-shards.json`, annotate canonical IDs for the added requirement, run `tests.test_evennia_test_optimization_contract`, `tests/test_command_docs.py`, `uv run --locked python -m tools.contract_gate` and `openspec validate party-management-acceptance --strict`.
