# Design — migrate-ai-art-server-observability

機制契約全部沿用 `add-observability-lint-gate`。本 change 只做遷移與 AI／SD 邊界事件落地。

## Context

facade 與 lint gate 已上線；`world/ai/`、`world/art/`、`world/prompts/` 在凍結清單內。這些模組的既有錯誤簽名（`LLMTransportError`、命名錯誤碼、guardrail degrade 回傳值）都是已規格化的契約，觀測只能加不能改。

## Decisions

1. **`llm_call` 事件發在 guardrail 包裝層的呼叫收尾**，不是 transport 底層：只有 guardrail 層同時看得到 layer、profile、最終 result（ok/degraded/rejected）與 ms。一次 guarded 呼叫恰好一條 `llm_call`；重試不各發一條（重試細節屬 `log_debug`），避免規格「每一次呼叫」與 guardrail 重試語義打架。
2. **`llm_transport_error` 發在 `world/ai/client.py` transport 失敗點**，帶 endpoint＋exc——這是唯一看得到原始 http 細節的位置；與 `llm_call result=degraded` 各自獨立，兩者相加即完整診斷鏈。
3. **prompts loader 收斂進 facade**：它目前用 stdlib `logging`，遷移後刪除該 logger（facade 為唯一出口）。
4. **art worker 對外的命名錯誤碼（`sd_internal_error` 等）零變更**：facade 事件只補 `exc` 鏈與 endpoint context。
5. **art 事件的 emission ownership 在 worker 編排層**（`worker.drain`／settle 迴圈），不包住 queue API：`sd_job_claim` 僅在 claim 實際回傳 record 後發、每 record 一條；`sd_job_settled` 僅對「實際走到 terminal settle 的 record」發。client-config 批次失敗（`_fail_batch` 路徑）與 stale/reclaimed claim 各自不發假 settle；`_fail_batch` 需保留 `(record, subject)` 對應以便失敗批次逐 record 帶 reason 記 settled 事件。job identity 以 record 的稳定欄位（subject identity）為準。

## Risks / Trade-offs

- [測試改 patch 對象後，事件断言變多導致既有測試脆弱] → 事件断言放新測試檔；既有測試只改 patch 目標不改斷言邏輯。
- [`llm_call` 在離線 fake client 測試環境仍發事件] → 這是期望行為；fake client 測試斷言事件存在即證明離線可觀測。

## Migration Plan

逐檔：換 import→event 碼→補 context→guardrail 層與 client 層發事件→worker claim/settle 事件→凍結清單移除→focused tests。回滾 = revert。

## Open Questions

無。
