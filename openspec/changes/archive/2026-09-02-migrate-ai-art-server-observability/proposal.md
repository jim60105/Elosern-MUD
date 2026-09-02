## Why

AI／SD 是全 repo 最依賴「事後看 log 診斷」的邊界：LLM transport 錯誤、guardrail 拒絕、schema 降級目前只留一句自由句子，看不到 layer、profile、延遲、降級原因；art worker 把 http 失敗吞成 `sd_internal_error` 字串代碼碼後不回任何棧。設計源頭：`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.3、§5 批次 3。依賴 `add-observability-lint-gate`。與 `migrate-rules-maps-observability` 目錄不相交，可並行。

## What Changes

- 遷移 `world/ai/`（client、guardrail、action_options）、`world/art/`（service、sd_worker、worker、presenter）、`world/prompts/loader.py`（含其 stdlib `logging` 站點）全部 log 呼叫至 `world.observability` facade；吞例外點改 `log_error(exc=…)` 或豁免註解；凍結清單同步收縮。
- AI／SD 邊界事件落地：每次 LLM 呼叫一條 `llm_call`（layer、profile、ms、result=ok|degraded|rejected、reason）；transport 失敗 `llm_transport_error`（endpoint、exc）；SD job `sd_job_claim`／`sd_job_settled`（job、subject、status、reason）。
- `world/art/worker.py` 的 `except Exception: return FAILED, "sd_internal_error"` 型吞點：保留對外的命名錯誤碼契約，但事件帶 `exc` 鏈與 endpoint。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `llm-client`: 每次呼叫與 transport 失敗發邊界事件（安全降級語義不變）。
- `art-queue-worker`: claim／settle 邊界事件。
- `internal-art-worker`: 降級錯誤碼事件帶 exception chain 與 endpoint。

## Impact

- 修改：`world/ai/` 3 檔、`world/art/` 4 檔、`world/prompts/loader.py`；測試 `world/ai/tests/test_guardrail.py`、`world/art/tests/test_sd_worker.py`、`world/art/tests/test_worker.py` 改 patch facade；`tools/observability_freeze.json` 收縮；新測試模組 → `.github/evennia-shards.json`。
- 事件僅觀測：guardrail 重試／降級、worker 錯誤碼契約零語義變更。
- 無向後相容需求；無 player-facing 命令變更。
