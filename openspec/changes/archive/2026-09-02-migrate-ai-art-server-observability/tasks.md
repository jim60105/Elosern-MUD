# Tasks — migrate-ai-art-server-observability

前置：`add-observability-lint-gate` 已合併。契約見 `local://observability-contract.md`。與 `migrate-rules-maps-observability` 不相交，可並行。

## 1. AI 邊界

- [x] 1.1 `world/ai/client.py`：遷移 log 呼叫；transport 失敗點發 `llm_transport_error`（endpoint、exc）
- [x] 1.2 `world/ai/guardrail.py`：guarded 呼叫收尾發恰好一條 `llm_call`（layer、profile、ms、result、reason）；重試細節走 `log_debug`
- [x] 1.3 `world/ai/action_options.py` 降級診斷改 facade event＋context
- [x] 1.4 `world/ai/tests/test_guardrail.py` 改 patch facade；新增事件斷言測試（成功恰好一條、degraded 雙事件鏈）＋shards 登記
- [x] 1.5 凍結清單移除 `world/ai/` 三檔

## 2. Art 邊界

- [x] 2.1 `world/art/service.py`、`sd_worker.py`：遷移 log 呼叫；claim/settle 事件按 design D5 於 worker 編排層發出（job、subject、status、reason）
- [x] 2.2 `world/art/worker.py`：`sd_internal_error`／`sd_client_config_error` 吞點補 `exc` 鏈＋endpoint context（對外包裝碼零變更）；claim 失敗路徑發事件後 re-raise
- [x] 2.3 `world/art/presenter.py` 遷移（佔位降級發 warn＋context）
- [x] 2.4 `world/art/tests/test_sd_worker.py`、`test_worker.py` 改 patch 呼叫端模組綁定；新增事件基數測試：多 record client-config 失敗批次逐 record 恰一條帶 reason 的 settled、stale claim 不發假 settle、正常成功 claim/settle 各恰一條＋shards 登記
- [x] 2.5 凍結清單移除 `world/art/` 四檔

## 3. Prompt library

- [x] 3.1 `world/prompts/loader.py`：移除 stdlib logger，改 facade（load 結果 event、degrade 清單進 context、失敗 `log_error(exc=…)`）

## 4. 驗證

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai world.art world.prompts`
- [x] 4.0 基準盤點：`tools.observability_lint check --json` 列 `world/ai|art|prompts` 違規檔為本批完成清單；共享檔紀律同契約（freeze/shards 僅自有 commit 內改，與批次 2 並行合併序 2→3）
- [x] 4.2 Traceability：三個 MODIFIED 能力的新需求 id 以 `covers_requirement` 標註於 1.4/2.4 測試；`check` 綠
- [x] 4.3 `openspec validate migrate-ai-art-server-observability --strict`
