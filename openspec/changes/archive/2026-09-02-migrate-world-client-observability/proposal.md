## Why

可觀測遷移的最後一哩：`world/quests/`（scene_builder、transitions、deadlines、runtime 的 restore 吞點）、`typeclasses/`（characters、exits）與 `web/`（dispatcher、presentation 三檔）仍在凍結清單內；`quest_transition` 事件因 `world/quests/` 屬本批次而尚未落地。本 change 清空 `tools/observability_freeze.json`，observability lint 轉為全 repo 永久強制。設計源頭：`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §5 批次 4。依賴批次 1–3（凍結清單需已收斂至剩餘條目）。

## What Changes

- 遷移 `world/quests/`、`typeclasses/`、`web/` 全部剩餘 log 呼叫與吞例外點至 facade；凍結清單逐檔收縮至清空。
- quest 生命週期邊界事件：transition／bind 成功收尾發 `quest_transition`（char、quest、stage_from、stage_to）。
- 凍結清單清空後：lint 對全 repo 無例外強制；新增 contract test 斷言清單為空（防止有人再塞條目）。
- 最終人工驗收：開 server 走一段遊戲，從 `server/logs/` 重建行動時間線。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `quest-lifecycle`: quest transition 邊界事件。

## Impact

- 修改：`world/quests/` 4 檔、`typeclasses/characters.py`、`typeclasses/exits.py`、`web/webclient/` 4 檔、`tools/observability_freeze.json`（清空）。
- 測試改 patch facade：`typeclasses/tests/test_npc_dialogue.py`、`web/webclient/actions/tests/test_dialogue_composition.py`、`web/webclient/presentation/tests/test_art_push.py`。
- 新測試模組 → `.github/evennia-shards.json`；`tests/test_quality_gate_contract.py` 加凍結清單為空的 contract。
  該 contract test 是 `observability-lint-gate`「凍結清單為收斂式 ratchet」需求的回歸斷言，
  以該需求的正式 id 標註 traceability，不新增主 spec 需求。
- 無向後相容需求；無 player-facing 命令變更。
