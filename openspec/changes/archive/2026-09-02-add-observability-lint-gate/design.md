# Design — add-observability-lint-gate

技術決策全量見 `docs/superpowers/specs/2026-09-02-observability-logging-design.md`（已核准）。本檔只記錄本 change 範圍內的決策與邊界。

## Context

repo 無 linter、無向後相容需求、AI 開發者產出多數 code。觀測缺口分兩半：例外被壓成一句話（R2 痛點）與正常路徑零留痕（事件目錄痛點）。本 change 是四個依序 change 的第一個，落地機制＋命令流＋生命週期＋`server/`＋`commands/`。

## Goals / Non-Goals

**Goals**：facade、lint gate、凍結清單 ratchet 機制、`cmd_in`/`cmd_done`、`startup_step`、AGENTS.md、CI。
**Non-Goals**：遷移 `world/`、`typeclasses/`、`web/` 的既有呼叫點（批次 2–4）；JSON line 日誌；分散式 tracing。

## Decisions

1. **命令流 seam 用 repo 自有基底類別 `commands/command.py::Command`**：覆寫 Evennia `Command.at_pre_cmd`/`at_post_cmd`（實測存在）發 `cmd_in`/`cmd_done`。**現況盤點（實測）：commands/ 下幾乎全部 production 命令直接 `from evennia import Command`**（action、art、background、combat、economy、guild、invite、items、leave、lineage、lore、scene、skip、talk、title、character_creation、localized/general 等）——本 change 將全部站點改掛 repo 基底類別，以 `from evennia import Command` 於 `commands/` 的搜尋結果為可核對完成清單（Evennia default commands 不在範圍）。替代方案（cmdset 層攔截）被否：Evennia 的呼叫路徑在 `cmdhandler.call_command` 內，基底類別鉤子是唯一穩定 seam。
2. **凍結清單＝R1 債務清單、只壓 R1、shrink-only**：`tools/observability_freeze.json`（唯一正典路徑）在 gate 落地時由掃描**生成**，恰好等於全 repo R1 import 債務檔集合（實測 34 檔）。凍結條目只豁免該檔的 R1；**R2/R3 對「已匯入 facade 的檔案」永遠生效（含凍結檔）**——凍結中偷偷採用的檔不會繞過品質線。殭屍判定＝「該檔已無 R1 債務卻仍在清單」。這同時鎖死終點：批次 1–4 遷移的正是這 34 檔，批次 4 清空的條件可機械驗證。既有 323 處 legacy 吞例外點中 67 檔不屬任何批次的 R1 債務——R2 以 adopter 為範圍，使 legacy error-hygiene 債務顯式延後（各自被後續真實觸及該檔的遷移自然收編），換得 ratchet 可完結；此取捨寫入規格 scenario。
3. **lint 為單一檔案 `tools/observability_lint.py`**：與 `tools/spec_traceability.py`（單檔、stdlib AST、CLI check/--json）同構，不建 package。
4. **facade 放 `world/observability/`**：game runtime 元件；只依賴 stdlib＋Evennia logger＋settings，不 import game 模組，避免循環依賴。
5. **`exc` 於四個級別皆可用**：任何級別帶 `exc` 都渲染單行 `tb:` 摘要；只有 `log_error` 另把完整 `traceback.format_exception()` 送 Evennia `log_err`（雙寫）。`rollback_restore_failed`／`llm_transport_error` 等 warn 級事件據此攜帶例外鏈。
6. **R3 只驗「有傳 context」不驗內容**：AST 靜態判定值語義不可靠；深度靠 AGENTS.md 與 review。刻意邊界，寫入規範。
7. **`_startup_step` 有序步驟目錄（正典列舉，順序即契約）**：`world_clock_init`、`equipment_rulebook_validation`、`sync_all`、`sync_limbo`、`sync_grid`、`sync_service_interiors`、`sync_quest_runtime`、`sync_guild_economy`、`sync_guard_npc`、`sync_npc_schedules`、`register_title_planner`、`restore_persisted_sessions`、`sync_wilderness`＝fail-loud（記錄後 re-raise）；`load_prompt_library`、`register_narrator_layer`、`register_npc_dialogue_layer`、`register_scenario_director_layer`、`register_character_creation_layer`、`register_scene_flavor_layer`、`register_action_options_layer`、`register_title_nomination_layer`、`register_nomination_triggers`＝boot-tolerant（結構化 degrade、不 raise）；`art_sync_all`、`connect_art_push`＝外層容忍（內部已 bounded）。包裝只計時＋發事件＋改 log 出口，**不改呼叫序、不改容錯語義**；既有 `inspect.getsource` 字串式 order-guard 測試同批改為行為式斷言（task 3.4b）。
8. **Traceability 標註延到 archive**：`tools.spec_traceability` 只索引 `openspec/specs/`；active delta 的 id 于實作期間必紅（`unknown-requirement-id`）。新能力 id 的 `covers_requirement` 標註與主規格同步同批（archive 時），P1 只標既有主規格 id。

## Risks / Trade-offs

- [命令基底類別事件在長命令（combat round）放大 log 量] → 單人遊戲，info 預設開；高頻細節本該走 `log_debug`。
- [`cmd_done` 的 outcome 判定] → 契約（實測 cmdhandler）：Evennia 只在命令正常完成時呼叫 `at_post_cmd`；func 拋例外時跳過並轉 Evennia error report。故 `cmd_done` 只發 `outcome=ok`，異常結束以「`cmd_in` 未配對 `cmd_done`」重建。不虛構 `error`/`unknown` 判定。
- [凍結清單被瀆職成長] → shrink-only lint：多餘條目即 violation，CI 擋。
- [`log_debug` 的 VERBOSE 不在 settings 定義] → `getattr(settings, "VERBOSE", False)`；測試以 `override_settings` 明測真假兩支。
- [R2 對 `with`／巢狀 `try` 內的 raise 誤判] → R2 遞迴搜尋 handler body 子樹（不含巢狀函式定義內）；豁免註解以 tokenize 定位（except 頭行行尾或 body 首行前）。
- [事件測試 patch 錯對象] → import 慣例：production 用具名匯入；事件測試 patch 呼叫端模組綁定或 capture sink；facade 自測 patch 其內部 evennia logger import＋stderr capture。

## Migration Plan

facade→lint→基底類別事件→`server/`＋`commands/` 遷移→AGENTS.md→CI 步驟＋contract test 同批改→shards 登記新測試模組。回滾 = revert 單一 change；無持久狀態變更。

## Open Questions

無。事件目錄內容以設計文件 §4 為準。
