# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Navigation bar (2.5h)

- [ ] 1.1 Rework `DesktopNavigation.vue` and `nav-tools.js` to 隊伍/任務/地圖, the five-tool group and 設定 last, with 隊伍 opening the party window on its last tab; verify Vitest order per mode, absent entries without placeholders, tool order, last-tab opening and possession-identical rendering, plus the Node geometry test for 1px stability at 1451x790, 1741x948 and 2560x1440.

## 2. Hotkeys (2h)

- [ ] 2.1 Add `composables/use-window-hotkeys.js` (P B C K L J M) with input, contenteditable, IME, modifier and modal guards, wired through the same openers; verify Vitest for each key, the guards, and M inert in combat.

## 3. Integration (1.5h)

- [ ] 3.1 Update `Core/DesktopNavigation` stories (with and without possession), add one browser method pressing P and B registered in `.github/browser-shards.json`, update the web-client paragraphs in `docs/game/commands.md` (and the drift test if needed) and `web/webclient-app/AGENTS.md`; annotate canonical IDs; run the touched Vitest/Node files, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-main-navigation-hotkeys --strict`.
