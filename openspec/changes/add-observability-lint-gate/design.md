# Design — add-observability-lint-gate

技術決策全量見 `docs/superpowers/specs/2026-09-02-observability-logging-design.md`（已核准）。本檔只記錄本 change 範圍內的決策與邊界。

## Context

repo 無 linter、無向後相容需求、AI 開發者產出多數 code。觀測缺口分兩半：例外被壓成一句話（R2 痛點）與正常路徑零留痕（事件目錄痛點）。本 change 是四個依序 change 的第一個，落地機制＋命令流＋生命週期＋`server/`＋`commands/`。

## Goals / Non-Goals

**Goals**：facade、lint gate、凍結清單 ratchet 機制、`cmd_in`/`cmd_done`、`startup_step`、AGENTS.md、CI。
**Non-Goals**：遷移 `world/`、`typeclasses/`、`web/` 的既有呼叫點（批次 2–4）；JSON line 日誌；分散式 tracing。

## Decisions

1. **命令流 seam 用 repo 自有基類 `commands/command.py::Command`**：覆寫 Evennia `Command.at_pre_cmd`/`at_post_cmd`（實測存在）發 `cmd_in`/`cmd_done`。**現況盤點（實測）：commands/ 下幾乎全部 production 命令直接 `from evennia import Command`**（action、art、background、combat、economy、guild、invite、items、leave、lineage、lore、scene、skip、talk、title、character_creation、localized/general 等）——本 change 將全部站點改挂 repo 基類，以 `from evennia import Command` 於 `commands/` 的搜尋結果為可核對完成清單（Evennia default commands 不在範圍）。替代方案（cmdset 層攔截）被否：Evennia 的呼叫路徑在 `cmdhandler.call_command` 內，基類鉤子是唯一穩定 seam。
2. **凍結清單是檔案粒度、shrink-only**：`tools/observability_freeze.json` 列 repo-relative 路徑；清單內檔案整體豁免 R1–R3；條目指向已無違規的檔案 → lint 報 violation（防止清單膨脹與忘刪）。清單存在 ≠ 永久：批次 4 必須清空。
3. **lint 為單一檔案 `tools/observability_lint.py`**：與 `tools/spec_traceability.py`（單檔、stdlib AST、CLI check/--json）同構，不建 package。
4. **facade 放 `world/observability/`**：game runtime 元件；只依賴 stdlib＋Evennia logger＋settings，不 import game 模組，避免循環依賴。
5. **`exc` 於四個級別皆可用**：任何級別帶 `exc` 都渲染單行 `tb:` 摘要；只有 `log_error` 另把完整 `traceback.format_exception()` 送 Evennia `log_err`（雙寫）。`rollback_restore_failed`／`llm_transport_error` 等 warn 級事件據此攜帶例外鏈。
6. **R3 只驗「有傳 context」不驗內容**：AST 靜態判定值語義不可靠；深度靠 AGENTS.md 與 review。刻意邊界，寫入規範。

## Risks / Trade-offs

- [命令基類事件在長命令（combat round）放大 log 量] → 單人遊戲，info 預設開；高頻細節本該走 `log_debug`。
- [`cmd_done` 的 outcome 判定] → 契約（實測 cmdhandler）：Evennia 只在命令正常完成時呼叫 `at_post_cmd`；func 拋例外時跳過並轉 Evennia error report。故 `cmd_done` 只發 `outcome=ok`，異常結束以「`cmd_in` 未配對 `cmd_done`」重建。不虛構 `error`/`unknown` 判定。
- [凍結清單被瀆職成長] → shrink-only lint：多餘條目即 violation，CI 擋。
- [`log_debug` 的 VERBOSE 不在 settings 定義] → `getattr(settings, "VERBOSE", False)`；測試以 `override_settings` 明測真假兩支。
- [R2 對 `with`／巢狀 `try` 內的 raise 誤判] → R2 遞迴搜尋 handler body 子樹（不含巢狀函式定義內）；豁免註解以 tokenize 定位（except 頭行行尾或 body 首行前）。
- [事件測試 patch 錯對象] → import 慣例：production 用具名匯入；事件測試 patch 呼叫端模組綁定或 capture sink；facade 自測 patch 其內部 evennia logger import＋stderr capture。

## Migration Plan

facade→lint→基類事件→`server/`＋`commands/` 遷移→AGENTS.md→CI 步驟＋contract test 同批改→shards 登記新測試模組。回滾 = revert 單一 change；無持久狀態變更。

## Open Questions

無。事件目錄內容以設計文件 §4 為準。
