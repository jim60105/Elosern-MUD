# 可觀測性日誌規範設計（Observability Logging Design）

日期：2026-09-02
狀態：已核准（待實作）

## 1. 問題陳述

目前全 repo 約 160 處 log 呼叫混用 `evennia.logger`、`evennia.utils.logger`
與 stdlib `logging`，且大量 `except Exception` 把例外壓成一句自由句子、或
直接 `pass` 吞掉。後果：

1. 異常發生時，log 裡看不到是哪個 entity、哪個 tick、哪個 prompt layer、
   交易到哪一步斷掉——只能進 container 寫 code 復現，這不可接受。
2. 正確執行路徑幾乎不留痕跡：無法從 log 重建「這一局遊戲系統到底做了什麼」
   的時間線。正常執行狀態同樣不可觀測。

目標不是定點修補，而是建立開發規範＋工具鏈，使未來的所有實作（尤其是
AI 開發者產出的 code）都強制可觀測。

## 2. 決策摘要

| 決策 | 選擇 | 理由 |
|---|---|---|
| 痛點範圍 | 全 codebase 通例規範 | 各類異常（AI 降級、rules 回滾、art worker）都被壓成一句話 |
| 輸出形態 | 結構化 context 尾綴、維持 Evennia logger 純文字檔 | 人類可讀、grep 友好、改動最小；不引入 JSON line 雙軌 |
| 遷移範圍 | 全部既有呼叫點遷移，分 1＋3 個 change 執行（見 §5） | 全量遷移超出單一 change 單一工程師單日容量；凍結清單僅為遷移期臨時機制，最終必須為空 |
| R2 作用域 | 例外不得無痕規則以「已匯入 facade 的檔案」為作用域（含凍結檔） | 實測 legacy 吞例外散佈 89 檔／323 處，其中 67 檔不屬任何遷移批次——全 repo R2 使凍結清單永遠清不空；adopter 範圍讓檔案一採用 facade 立即受管，全部 log 站點於批次 4 後 100% 受 R2/R3 涵蓋；一般性 error-hygiene 債務顯式延後給後續觸及該檔的變更 |
| 實作路線 | 方案 A：自建 log facade ＋ AST 掃描 gate 工具 | repo 刻意無 linter；自寫工具可表達「except 必須含 log 或 re-raise」等 ruff 表達不了的規則；零新增依賴 |

拒絕的替代方案：

- **方案 B（引入 ruff custom rule）**：把整個 lint 工具鏈引進刻意零 linter
  的 repo，且相關規則在 ruff plugin API 尚不穩定，成本高於收益。
- **方案 C（import hook／monkey-patch 自動注入）**：隱式 magic、AI 產出
  code 行為不可控、難測試；且只能補機械資訊，補不出業務 context。
  facade 本來就能自動取 caller 資訊，無此必要。

## 3. 架構

三個元件，各自單一職責：

### 3.1 `world/observability/` — 執行期 log facade

唯一的 game-code log 寫入點。位置選 `world/` 下而非頂級目錄：facade 是
game runtime 元件，與 `world/rules/` 等同層級被 import。

公開 API（由 `world/observability/__init__.py` 再匯出）：

```python
def log_info(event: str, *, exc: BaseException | None = None,
             context: Mapping[str, object] | None = None) -> None: ...
def log_warn(event: str, *, exc: BaseException | None = None,
             context: Mapping[str, object] | None = None) -> None: ...
def log_error(event: str, *, exc: BaseException | None = None,
              context: Mapping[str, object] | None = None) -> None: ...
def log_debug(event: str, *, exc: BaseException | None = None,
              context: Mapping[str, object] | None = None) -> None: ...
```

`exc` 於四個級別皆可用：任何級別帶 `exc` 都渲染 `tb:` 單行摘要；只有
`log_error` 另把完整 traceback 全文送 Evennia error log。

輸出單行格式：

```
[warn] scene_flavor_apply_skipped | world.quests.scene_builder:_apply:506 | room=1234 quest=main_arc tb: ValueError: bad token @ world/quests/compile.py:88 <- TimeoutError: connect
```

渲染規則：

- `event`：穩定 snake_case 事件識別碼，非自由句子；英文。玩家-facing 的
  正體中文文案不進 log。
- caller 段 `mod.func:line` 由 facade 從 `sys._getframe` 取得，呼叫端不傳。
- context 渲染為 `k=v`：str 原樣（含空白加引號）、int/float/bool 直譯、
  Mapping／序列 `repr` 後截斷至 200 字元、值為 None 時整個鍵跳過；
  鍵排序輸出，保證可 diff、單行、grep 友好。
- `exc` 渲染為 `tb:` 段：例外鏈由外到內每一環 `Type: msg @ file:line`，
  以 ` <- ` 串接。單行摘要供 grep；同時 `log_error` 將
  `traceback.format_exception()` 全文送 Evennia `log_err` 進 error log，
  完整棧供深挖，兩者不缺。
- 級別映射：`log_info`→Evennia `log_info`、`log_warn`→`log_warn`、
  `log_error`→`log_err`。`log_debug` 由 facade 以
  `getattr(settings, "VERBOSE", False)` 閘門（repo settings 未定義
  VERBOSE，直接屬性存取會 AttributeError；Evennia logger 本身不過濾），
  未開啟時直接回傳不寫入。
- 冪等防呆：facade 內部任何失敗（import 失敗、logger 拋錯）退回 stdlib
  `print` 至 stderr。觀測工具自身不能成為故障源；facade 永不向上拋例外。
- 依賴方向：facade 只依賴 stdlib ＋ Evennia logger，不 import 任何 game
  模組，避免循環依賴。

慣例 context 鍵（推薦非強制，lint 只驗非空）：`room`、`char`／`npc`（pk）、
`tick`、`layer`（AI）、`quest`（quest key）、`job`（art worker）、
`endpoint`（HTTP）。能取得的業務標識一律放 context，不塞進 event 字串。

### 3.2 `tools/observability_lint/` — CI／本地 gate 工具

與 `tools.spec_traceability` 完全同構：stdlib AST 掃描、JSON 報告、
`uv run --locked python -m tools.observability_lint check [--json]`，
exit 0/1。無 `list` 子命令（無 registry 可列）。

掃描範圍：`world/`、`typeclasses/`、`commands/`、`server/`、`web/`，
不含各 `tests/` 目錄（測試允許 patch logger）。

規則（AST，非字串匹配）：

- **R1 — 唯一寫入點**（列舉全部規避形態）：範圍內
  `import evennia.utils.logger`、
  `from evennia.utils.logger import <任何名字>`（含 `log_warn` 等直接函式
  import）、`from evennia import logger`、`from evennia.utils import
  logger`（含 alias）與 `import evennia` 後的 `evennia.logger.*` 呼叫一律
  違規；`world/observability/` 自身是唯一白名單。violation 訊息含檔案:行。
- **R2 — 例外不得無痕吞掉**（作用域＝匯入 facade 的檔案，含凍結檔；未
  採用 facade 的 legacy 檔不受 R2 約束，見 §2 決策表）：
  每個 `except`／`except*` 區塊的 body 必須
  滿足其一：① body 的 AST 子樹（遞迴尋找、不含巢狀函式定義內部）出現
  `raise` ② 出現 facade log 呼叫 ③ 或豁免註解（見下）。豁免註解定位以
  tokenize 判定：R2 在 `except` 頭行行尾或 body 首行之前；R3 在呼叫行
  行尾或其前一行；R1 在 import 行行尾或其前一行。
- **R3 — log 必帶 context**：facade 四個函式的呼叫必須帶 `context` kwarg
  且非常數 `None`；`log_error` 另需 `exc=` 或同一 `except` 區塊內有
  `raise`。靜態只驗「有傳」，值內容的深度靠 AGENTS.md 慣例與 review。

豁免註解語法（R1/R2/R3 通用）：

```python
# observability: ignore <rule-id>: <reason>
```

lint 驗證 reason 非空，並把豁免計數輸出到 JSON 報告，使豁免膨脹可見。

無法 parse 的檔案視為 violation——parse error 不能成為旁路。

### 3.3 `AGENTS.md` Observability 規範條目

新增「Observability」一節，要點：

1. 所有 game-code log 一律經 `world.observability` facade；禁止直接
   import Evennia logger（由 lint 執行）。
2. event 碼為 snake_case 穩定識別碼、英文；玩家文案不進 log。
3. `context` 必帶；能取得的業務標識（room／tick／layer／quest／job）
   一律放 context 鍵。
4. `except` 區塊三選一：re-raise／facade log／豁免註解（附理由）。
5. **正常路徑留痕**：新增或修改任何持久狀態變更、外部 I/O 或跨系統
   workflow 時，必須在其邊界依事件目錄（§4）留 info 事件。
6. 修改任何會 log 的 code path 時，`tools.observability_lint check` 與
   focused tests 同批驗證。

## 4. 事件目錄（正常路徑強制留痕）

錯誤可見只是半邊；從 log 重建執行時間線是另一半。以下事件為必留痕基線
（單人遊戲，log 量不是問題，info 級預設開）。目錄收錄於本檔，作為
OpenSpec `verify` 階段的對照清單。

### 4.1 命令流

將全部 `commands/` 下直接繼承 Evennia `Command` 的 production 命令掛到
repo 基類 `commands/command.py::Command`（Evennia default commands 不在
範圍），於其 `at_pre_cmd`／`at_post_cmd` 統一實作：

| event | 級別 | context |
|---|---|---|
| `cmd_in` | info | `char`（pk）、`cmd`（命令 key）、`args`（截斷） |
| `cmd_done` | info | `char`、`cmd`、`ms`（耗時）、`outcome=ok` |

Evennia 的 cmdhandler 只在命令正常完成時呼叫 `at_post_cmd`（func 拋例外
時直接跳過並轉為 Evennia error report），因此 `cmd_done` 只代表成功；
異常結束由「`cmd_in` 未配對 `cmd_done`」重建，不虛構 `error` 判定。

### 4.2 rules 提交點（狀態邊界）

每個「狀態真的變了」的邊界寫一條 info——這是回滾失敗時重建時間線的關鍵：

| event | context |
|---|---|
| `action_commit` | `char`、`action`、`ms` |
| `combat_round_settled` | `char`、`opponent`、`tick`、`hp_before`、`hp_after` |
| `clock_advance` | `tick_from`、`tick_to`、`scope` |
| `quest_transition` | `char`、`quest`、`stage_from`、`stage_to` |
| `settlement_done` | `char`、`ms`、`notifications`（數量） |
| `rollback_restore_failed` | `key`、`obj`＋`exc`（warn 級，取代現有裸 `pass`） |

### 4.3 AI／外部服務邊界

| event | context |
|---|---|
| `llm_call` | `layer`、`profile`、`ms`、`result`（`ok`／`degraded`／`rejected`）、`reason`（降級時的原因碼） |
| `llm_transport_error` | `layer`、`endpoint`、`exc` |
| `sd_job_claim` | `job`、`subject` |
| `sd_job_settled` | `job`、`subject`、`status`、`reason` |

### 4.4 伺服器生命週期

startup 各 registration 步驟、prompt library load、degrade 清單——
現在只有失敗才 log；成功路徑補 info（`startup_step`，context 含
`step`、`ms`），使「開機時哪些子系統正常、哪些降級」一 log 可讀。

### 4.5 高頻細節

combat 每回合中間值等高頻資料走 `log_debug`，受 Evennia `VERBOSE` 控制，
預設不污染 server.log。

## 5. 遷移策略

遷移量（約 160 處 log 呼叫＋大量吞例外點）超出單一 change 的容量，分四個
依序實作的 change，每個皆可由單一工程師在一個工作日內完成：

1. **`add-observability-lint-gate`**：facade ＋ lint 工具＋兩者自身測試、
   命令流事件（`cmd_in`／`cmd_done`）、生命週期事件、事件目錄落地、
   AGENTS.md 條目、CI 接入，並遷移 `server/`＋`commands/`。掃到既有
   code 時以**過渡期凍結清單**（`tools/observability_freeze.json`）
   豁免尚未遷移的檔案。清單由掃描生成、恰好等於全 repo Evennia-logger
   import 債務檔集合（R1 inventory）；條目只壓 R1，R2/R3 對已採用 facade
   的檔案即時生效（含凍結檔）。凍結清單只許縮小——lint 對清單中已無 R1
   債務卻未移除的殭屍條目報錯。
2. **`migrate-rules-maps-observability`**：`world/rules/`＋
   `world/maps/` 呼叫點與提交點事件（§4.2）。
3. **`migrate-ai-art-server-observability`**：`world/ai/`＋
   `world/art/`＋`world/prompts/`；AI／SD 邊界事件（§4.3）。
4. **`migrate-world-client-observability`**：`world/quests/`＋
   `typeclasses/`＋`web/` 收尾，清空凍結清單，轉為全 repo 永久強制。

批次 2 與 3 目錄不相交，可並行；批次 4 必須最後（依賴 freeze list
收斂為空）。每個遷移批次的 commit 內 `tools.observability_lint check`
必須 exit 0。

每處遷移不只是換 import：

- 補有意義的 context（該處可取得的 room／tick／layer／pk）；
- 吞掉的例外改 `log_error(..., exc=error)` 或補豁免註解；
- 自由句子改 snake_case event 碼；
- 依 §4 事件目錄點亮該子系統的正常路徑；
- 現有 patch `evennia.logger.log_warn` 的測試改成 patch facade 函式。

`web/webclient` 下的 JS／Python 介面若無 log 呼叫則不受影響；有則同規則
遷移。

## 6. 錯誤處理

- facade 永不拋例外（§3.1 stderr 退路）。
- lint 對無法 parse 的檔案報 violation。
- traceability 標註時序：`tools.spec_traceability` 只索引
  `openspec/specs/` 主規格；active change delta 的 id 在實作期間標註必報
  `unknown-requirement-id`。新能力測試的 `covers_requirement` 標註與
  archive 同步主規格同批加入。
- 事件目錄由 AGENTS.md 規則 ＋ OpenSpec verify 清單雙重把關；lint 不
  靜態驗證正常路徑 coverage（AST 無法可靠判定），這是刻意的邊界。

## 7. 測試

- `tests/test_observability_lint.py`（top-level，stdlib `unittest`，走
  `unittest discover`，不佔 evennia shard）：以
  `textwrap.dedent` 小段原始碼字串跑規則，每規則正例／反例／豁免三案；
  另測 parse error 報 violation、豁免 reason 為空報錯。
- facade 純邏輯測試（stdlib `unittest`）：context 渲染（排序、截斷、
  None 跳過、空白引號）、例外鏈摘要格式、logger 拋錯時退回 stderr。
- Evennia 整合面：命令基類 `cmd_in`/`cmd_done` 以
  `EvenniaCommandTest` 驗證實際執行會產生兩條 log。
- 遷移不新增行為測試；既有測試改 patch 對象後必須保持綠。

## 8. CI 接入

`quality-gate.yml` preflight 區加一步，與 spec_traceability gate 同位置
同模式：

```yaml
- name: Observability lint
  run: uv run --locked python -m tools.observability_lint check
```

## 9. 驗收標準

1. `uv run --locked python -m tools.observability_lint check` 全 repo
   exit 0。
2. 非瀏覽器 Evennia suite 綠（`--parallel 16 --noinput`）。
3. Node／JS gates 不受影響（純 Python 改動）。
4. 人工檢查：以真實配置開 server、走一小段遊戲（數個命令、一次戰鬥或
   quest transition），`server/logs/` 能不靠任何額外工具重建完整行動
   時間線，且任一人為製造的失敗（如擋掉 SD endpoint）在 log 單行內即
   可辨識 event、context、例外鏈。
