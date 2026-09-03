# Tasks — add-observability-lint-gate

## 1. Facade

- [x] 1.1 建立 `world/observability/`：`render.py`（context 渲染、例外鏈摘要、單行組裝）＋`api.py`（四函式共用單一 `_emit(event, level, exc, context, caller_skip)`，caller 以 `sys._getframe(caller_skip)` 於 `_emit` 內取得；`__init__.py` 再匯出）；雙層防呆：①`log_debug` 的 VERBOSE 以窄域 guard 讀取（settings 未配置→False、不寫入、不觸發退路）②渲染/logger 取得/每次寫入/stderr 退路各自 nested try/except，外層公開 API 對 `Exception` 必正常返回（`BaseException` 不吞）；Evennia logger 以單一 lazy `_get_evennia_logger()` seam 取得（成功後快取）
- [x] 1.2 `world/observability/tests/test_render.py`（`unittest.TestCase`）：鍵排序、200 字元截斷、None 跳過、空白引號、例外鏈外到內 ` <- ` 串接
- [x] 1.3 `world/observability/tests/test_api.py`：patch `_get_evennia_logger` seam 驗證四級別映射、任意級別 `exc=` 渲染 `tb:`、`log_error` 雙寫（單行摘要＋完整 traceback）；故障注入五路：logger 拋錯→stderr、renderer（repr 拋錯）→降級行、`log_error` 全文二寫失敗→不波及、stderr 本身失敗→呼叫端仍正常返回、settings 未配置→debug 靜默不升 stderr；VERBOSE 真假兩支以 monkeypatch settings 物件明測；經 `world.observability` 公開再匯出測 caller module.func:line 正確（非 facade 自身）；caller frame 深度以固定簽名契約測試
- [x] 1.3b 確立 import 慣例並寫入 AGENTS.md（5.1 引用）：production 用具名匯入（`from world.observability import log_warn`）；事件斷言測試 patch 呼叫端模組綁定或 capture sink，不得 patch `world.observability.*`
- [x] 1.4 `.github/evennia-shards.json`：`world.observability` 測試模組登記於恰好一個 shard（依 manifest 現有 world 條目慣例）

## 2. Lint gate

- [x] 2.1 `tools/observability_lint.py`（單檔、stdlib AST、CLI `check [--json]`、exit 0/1）：R1 唯一寫入點、R2 except 不得無痕、R3 log 必帶 context；豁免註解 `# observability: ignore <rule>: <reason>`；shrink-only 凍結清單 `tools/observability_freeze.json`；parse error = violation；豁免計數進 JSON
- [x] 2.2 `tests/test_observability_lint.py`（放 top-level `tests/`，走 `unittest discover`，不進 evennia shards）：每規則正/反/豁免、R2 adopter 範圍（non-adopter 沉默 handler 合規、frozen adopter 仍被 R2/R3 打）、凍結清單命中與殭屍（無 R1 債務即殭屍）、空 reason 報錯、parse error、範圍排除 `tests/`；規則引擎以 source-string 純函式直測＋一個 repo 整合斷言
- [x] 2.3 生成初始 `tools/observability_freeze.json`：**恰好等於 lint 掃描產出的 R1 import 債務檔集合（實測 34 檔）**，由工具生成、提交前與掃描結果逐一核對（無重複、無不存在路徑）；不含本 change 已遷移的 server/commands 檔則在遷移後自然不入列

## 3. 正常路徑事件（本 change 範圍）

- [x] 3.1 `commands/command.py::Command` 基底類別 `at_pre_cmd`/`at_post_cmd` 發 `cmd_in`/`cmd_done`（args 截斷 200、ms、outcome 不可判定時不謊報 ok）
- [x] 3.2 以 `rg "from evennia import Command" commands/` 產出完整盤點清單（實測含 action、art、background、combat、economy、guild、invite、items、leave、lineage、lore、scene、skip、talk、title、character_creation、localized/general 等檔），**全部**改掛 `commands.command.Command`；完成標準＝該搜尋於 `commands/` production 檔回空
- [x] 3.3 `commands/tests/test_command_observability.py`（`EvenniaCommandTest`）：經命令處理器（非直接 `.func()`）執行兩個來自不同模組的命令，各恰一對 `cmd_in`/`cmd_done`、含 actor pk、命令 key、ms；`cmd_done` 僅 `outcome=ok`
- [x] 3.4 `server/conf/at_server_startstop.py`：以 design D7 的有序步驟目錄逐一包 `_startup_step(name, fn)`（保留原始呼叫語義、嚴禁改序）：成功發 `startup_step`（step、ms）；fail-loud 步驟失敗發 facade `log_error(exc=…)` 後 **re-raise**；boot-tolerant 步驟保留容忍但發結構化 degrade（step context）；prompt library 失敗發 `log_error(exc=…)`＋degrade context
- [x] 3.4b 同批改寫既有 source-order guard 測試（`world/rules/tests/test_guild_economy_guards.py`、`world/maps/tests/test_bootstrap.py`、`test_limbo_room.py`、`world/quests/tests/test_deadlines.py` 的 `inspect.getsource` 字串斷言）為對 `_startup_step` 記錄器的行為式順序斷言；`test_instance_stage_wiring.py`、`test_degrade.py` 全程跑 `at_server_start` 者驗證不破
- [x] 3.4c `server/conf/tests/test_startup_observability.py`：patch 全部 startup 操作＋固定時鐘，斷言目錄內每步恰一條 `startup_step`、序完全一致；一個 fail-loud 失敗案例顯示事件＋例外仍傳播

## 4. server/ 與 commands/ 遷移

- [x] 4.1 遷移 4 檔 server service 模組＋`at_server_startstop.py` 全部 log 呼叫：event 改 snake_case、補 context、吞例外改 `log_error(exc=…)` 或豁免註解
- [x] 4.2 遷移 `commands/` 內唯一 log 站點（`character_creation.py`）；基底類別改掛（3.2）不屬 log 遷移、不受凍結清單影響
- [x] 4.3 `server/conf/tests/test_scene_flavor_service.py` 改 patch facade

## 5. 規範與 CI

- [x] 5.1 `AGENTS.md` 新增 Observability 條目（六規則＋慣例 context 鍵＋事件目錄指向設計文件）
- [x] 5.2 `.github/workflows/quality-gate.yml` preflight 加 "Run observability lint" 步驟（command 固定為 `uv run --locked python -m tools.observability_lint check`）；同批改 `tests/test_quality_gate_contract.py`：步驟名稱與該精確 command 字串都進 contract 斷言

## 6. 驗證

- [x] 6.1 `uv run --locked python -m tools.observability_lint check` exit 0（凍結清單內）
- [x] 6.2 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.observability commands server.conf`（554 tests OK）
- [x] 6.3 Traceability（刻意時序）：本 change 期間**不標註**兩個新能力的 id——`tools.spec_traceability` 只索引 `openspec/specs/` 主規格，active delta 的 id 會令 `check` 報 `unknown-requirement-id` 而紅。既有主規格 id（`spec-test-traceability::continuous-integration-enforces-both-quality-dimensions`）照常標註於 5.2 的 contract test。兩個新能力的 `covers_requirement` 標註在 archive 同步主規格時同批加入（列入批次 4 收尾/archive 工作），並以 `check` 綠為驗收
- [x] 6.4 `openspec validate add-observability-lint-gate --strict`
