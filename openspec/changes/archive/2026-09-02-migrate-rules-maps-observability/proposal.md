## Why

`world/rules/` 與 `world/maps/` 是全 repo 最大的 log 熱區（實測 rules 17 檔＋maps 1 檔 import Evennia logger，含 clock、combat_session、action、cast_settlement 等回滾敏感路徑）。現有 `except Exception` 之後的 restore 失敗多半被裸 `pass` 吞掉，回滾故障無法從 log 重建；且所有狀態提交點（action commit、combat round、clock advance）正常路徑零留痕。設計源頭：`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2、§5 批次 2。依賴 `add-observability-lint-gate`（facade 與 lint gate 已存在）。

## What Changes

- 將 `world/rules/` 全部既有 log 呼叫遷移至 `world.observability` facade：snake_case event 碼、補 context（char／room／tick／key）、吞掉的 restore 失敗改 `rollback_restore_failed` warn 事件或豁免註解；同步收縮 `tools/observability_freeze.json`。
- 將 `world/maps/`（bootstrap、wilderness_population）呼叫點遷移至 facade。
- rules 提交點依事件目錄發 info 事件：`action_commit`、`combat_round_settled`、`clock_advance`、`settlement_done`（`quest_transition` 由批次 4 的 world/quests 落地）。
- 新增事件斷言測試並登記 `.github/evennia-shards.json`。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `world-clock`: advance 成功與 rollback-restore 失敗的邊界事件。
- `player-combat-session`: 每回合與終局結算的邊界事件。
- `action-resolution-pipeline`: 成功 commit 的邊界事件。

## Impact

- 修改：`world/rules/` 約 17 檔、`world/maps/` 約 2 檔；`tools/observability_freeze.json` 收縮；新測試模組 → `.github/evennia-shards.json`。
- 與 `migrate-ai-art-server-observability` 目錄不相交，可並行。
- 無向後相容需求；無 player-facing 命令變更。
