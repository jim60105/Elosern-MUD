# Tasks — add-observability-lint-gate

## 1. Facade

- [ ] 1.1 建立 `world/observability/`：`render.py`（context 渲染、例外鏈摘要、單行組裝）＋`api.py`（四函式、caller frame、級別映射、VERBOSE 閘門、stderr 退路），`__init__.py` 再匯出
- [ ] 1.2 `world/observability/tests/test_render.py`（`unittest.TestCase`）：鍵排序、200 字元截斷、None 跳過、空白引號、例外鏈外到內 ` <- ` 串接
- [ ] 1.3 `world/observability/tests/test_api.py`：patch facade 內部的 evennia logger import，驗證四級別映射、任意級別 `exc=` 渲染 `tb:`、`log_error` 雙寫（單行摘要＋完整 traceback）、logger 拋錯退 stderr（stderr capture）、`override_settings(VERBOSE=True/False)` 明測 `log_debug` 兩支、永不拋例外；四个級別簽名皆含 keyword-only `exc`
- [ ] 1.3b 確立 import 慣例並寫入 AGENTS.md（5.1 引用）：production 用具名匯入（`from world.observability import log_warn`）；事件斷言測試 patch 呼叫端模組綁定或 capture sink，不得 patch `world.observability.*`
- [ ] 1.4 `.github/evennia-shards.json` 登記新測試模組

## 2. Lint gate

- [ ] 2.1 `tools/observability_lint.py`（單檔、stdlib AST、CLI `check [--json]`、exit 0/1）：R1 唯一寫入點、R2 except 不得無痕、R3 log 必帶 context；豁免註解 `# observability: ignore <rule>: <reason>`；shrink-only 凍結清單 `tools/observability_freeze.json`；parse error = violation；豁免計數進 JSON
- [ ] 2.2 `tests/test_observability_lint.py`：每規則正/反/豁免、凍結清單命中與殭屍條目報錯、空 reason 報錯、parse error、範圍排除 `tests/`；以 `covers_requirement` 標註 observability-lint-gate 需求
- [ ] 2.3 生成初始 `tools/observability_freeze.json`：批次 2–4 目錄的全部違規檔（world 29＋typeclasses 2＋web 4 等），不含本 change 遷移的 server/commands

## 3. 正常路徑事件（本 change 範圍）

- [ ] 3.1 `commands/command.py::Command` 基類 `at_pre_cmd`/`at_post_cmd` 發 `cmd_in`/`cmd_done`（args 截斷 200、ms、outcome 不可判定時不謊報 ok）
- [ ] 3.2 以 `rg "from evennia import Command" commands/` 產出完整盤點清單（實測含 action、art、background、combat、economy、guild、invite、items、leave、lineage、lore、scene、skip、talk、title、character_creation、localized/general 等檔），**全部**改挂 `commands.command.Command`；完成標準＝該搜尋於 `commands/` production 檔回空
- [ ] 3.3 `commands/tests/test_command_observability.py`（`EvenniaCommandTest`）：經命令處理器（非直接 `.func()`）執行兩個來自不同模組的命令，各恰一對 `cmd_in`/`cmd_done`、含 actor pk、命令 key、ms；`cmd_done` 僅 `outcome=ok`
- [ ] 3.4 `server/conf/at_server_startstop.py`：各步驟成功發 `startup_step`（step、ms）；失敗改 facade `log_error(exc=…)`；prompt library load 結果含 degrade context

## 4. server/ 與 commands/ 遷移

- [ ] 4.1 遷移 4 檔 server service 模組＋`at_server_startstop.py` 全部 log 呼叫：event 改 snake_case、補 context、吞例外改 `log_error(exc=…)` 或豁免註解
- [ ] 4.2 遷移 `commands/` 內唯一 log 站點（`character_creation.py`）；基類改挂（3.2）不屬 log 遷移、不受凍結清單影響
- [ ] 4.3 `server/conf/tests/test_scene_flavor_service.py` 改 patch facade

## 5. 規範與 CI

- [ ] 5.1 `AGENTS.md` 新增 Observability 條目（六規則＋慣例 context 鍵＋事件目錄指向設計文件）
- [ ] 5.2 `.github/workflows/quality-gate.yml` preflight 加 "Run observability lint" 步驟（command 固定為 `uv run --locked python -m tools.observability_lint check`）；同批改 `tests/test_quality_gate_contract.py`：步驟名稱與該精確 command 字串都進 contract 斷言

## 6. 驗證

- [ ] 6.1 `uv run --locked python -m tools.observability_lint check` exit 0（凍結清單內）
- [ ] 6.2 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.observability commands server.conf`
- [ ] 6.3 Traceability：以 `uv run --locked python -m tools.spec_traceability list` 取得本 change 兩能力的正式 requirement id；在 2.x/3.x/1.x 建立的每個行為測試方法上以 `covers_requirement` 標註字面 id，`check` 綠且每個需求至少一個標註
- [ ] 6.4 `openspec validate add-observability-lint-gate --strict`
