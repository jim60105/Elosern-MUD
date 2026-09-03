## Why

目前全 repo 約 160 處 log 呼叫混用 `evennia.logger`、`evennia.utils.logger` 與 stdlib `logging`，大量 `except Exception` 把例外壓成一句自由句子或直接 `pass` 吞掉；正確執行路徑幾乎不留痕跡，異常與正常運行都無法從 log 診斷，只能進 container 寫 code 復現。本 change 落地可觀測性規範的執行機制（facade＋lint gate），讓未來的所有實作（尤其 AI 產出的 code）被工具鏈強制可觀測。設計源頭：`docs/superpowers/specs/2026-09-02-observability-logging-design.md`。

## What Changes

- 新增 `world/observability/` log facade：`log_info`／`log_warn`／`log_error`／`log_debug`，統一單行結構化輸出（`event | mod.func:line | k=v | tb:` ），自動附 caller 資訊，永不拋例外。
- 新增 `tools/observability_lint.py`（與 `tools/spec_traceability.py` 同構）：AST 規則 R1（唯一寫入點）、R2（except 不得無痕吞例外；作用域＝已匯入 facade 的檔案，legacy error-hygiene 債務顯式延後）、R3（log 必帶 context），豁免註解與只許縮小的過渡凍結清單 `tools/observability_freeze.json`（由掃描生成＝R1 import 債務檔集合，條目只壓 R1）。
- 命令基底類別統一發出 `cmd_in`／`cmd_done` 事件；`at_server_startstop.py` 生命週期步驟發 `startup_step`——正常路徑開始留痕。
- 遷移 `server/`＋`commands/` 的既有 log 呼叫與吞例外點到 facade（其餘目錄由後續三個遷移 change 接手，暫列凍結清單）。
- `AGENTS.md` 新增 Observability 規範條目；`quality-gate.yml` preflight 接入 lint 步驟（同批改 `tests/test_quality_gate_contract.py` contract）。

## Capabilities

### New Capabilities
- `observability-logging`: game-code 唯一的 log facade——API、單行結構化渲染、例外鏈摘要、永不拋例外、命令流與生命週期正常路徑事件。
- `observability-lint-gate`: AST 靜態 gate——R1/R2/R3 規則、豁免註解、shrink-only 凍結清單、CLI 與 CI 強制。

### Modified Capabilities
- `spec-test-traceability`: CI 品質閘門清單納入 observability lint（「Continuous integration enforces both quality dimensions」）。

## Impact

- 新增 code：`world/observability/`、`tools/observability_lint.py`、`tools/observability_freeze.json`、命令基底類別事件層。
- 修改：`server/conf/at_server_startstop.py`、`server/scene_flavor_service.py`、`server/option_proposal_service.py`、`server/title_nomination_service.py`、`commands/` 基底類別、`.github/workflows/quality-gate.yml`、`tests/test_quality_gate_contract.py`、`AGENTS.md`、`.github/evennia-shards.json`（新測試模組登記）。
- 無 player-facing 命令增刪改（key/alias/syntax 不動），`docs/game/commands.md` 不受影響。
- 無向後相容需求（專案未發布、零使用者）；凍結清單為過渡機制，批次 4 清空。
