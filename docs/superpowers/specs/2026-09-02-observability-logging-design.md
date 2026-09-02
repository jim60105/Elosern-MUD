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
   的時間線。正常運行狀態同樣不可觀測。

目標不是定點修補，而是建立開發規範＋工具鏈，使未來的所有實作（尤其是
AI 開發者產出的 code）都強制可觀測。

## 2. 決策摘要

| 決策 | 選擇 | 理由 |
|---|---|---|
| 痛點範圍 | 全 codebase 通例規範 | 各類異常（AI 降級、rules 回滾、art worker）都被壓成一句話 |
| 輸出形態 | 結構化 context 尾綴、維持 Evennia logger 純文字檔 | 人類可讀、grep 友好、改動最小；不引入 JSON line 雙軌 |
| 遷移範圍 | 既有呼叫點一次全部遷移，無凍結期 | 符合 repo「無向後相容層」慣例；避免長期兩種寫法 |
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
def log_info(event: str, *, context: Mapping[str, object] | None = None) -> None: ...
def log_warn(event: str, *, context: Mapping[str, object] | None = None) -> None: ...
def log_error(event: str, *, exc: BaseException | None = None,
              context: Mapping[str, object] | None = None) -> None: ...
def log_debug(event: str, *, context: Mapping[str, object] | None = None) -> None: ...
```

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
  `log_error`→`log_err`。`log_debug` 由 facade 自行檢查
  `django.conf.settings.VERBOSE`（facade 內部門檻，Evennia logger 本身
  不會過濾），未開啟時直接回傳不寫入。
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

- **R1 — 唯一寫入點**：範圍內
  `import evennia.utils.logger`、`from evennia import logger`、
  `from evennia.utils import logger` 一律違規；`world/observability/`
  自身是唯一白名單。violation 訊息含檔案:行。
- **R2 — 例外不得無痕吞掉**：每個 `except`／`except*` 區塊的 body 必須
  滿足其一：① 含 `raise`（裸 re-raise 或 raise 新例外）② 含 facade log
  呼叫 ③ 區塊首行是豁免註解（見下）。
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

錯誤可見只是半邊；從 log 重建運行時間線是另一半。以下事件為必留痕基線
（單人遊戲，log 量不是問題，info 級預設開）。目錄收錄於本檔，作為
OpenSpec `verify` 階段的對照清單。

### 4.1 命令流

於 `commands/` 基類層統一實作，一處覆蓋全 repo：

| event | 級別 | context |
|---|---|---|
| `cmd_in` | info | `char`（pk）、`cmd`（命令 key）、`args`（截斷） |
| `cmd_done` | info | `char`、`cmd`、`ms`（耗時）、`outcome`（`ok`／`error`） |

### 4.2 rules 提交點（狀態邊界）

每個「狀態真的變了」的邊界寫一條 info——這是回滾失敗時重建時間線的關鍵：

| event | context |
|---|---|
| `action_commit` | `char`、`action`、`ms` |
| `combat_round_settled` | `char`、`opponent`、`tick`、`hp_before`、`hp_after` |
| `clock_advance` | `tick_from`、`tick_to`、`scope` |
| `quest_transition` | `char`、`quest`、`stage_from`、`stage_to` |
| `settlement_done` | `char`、`ms`、`notifications`（數量） |
| `rollback_restore_failed` | `key`、`obj`（warn 級，取代現有裸 `pass`） |

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

無凍結期，一次遷移；lint 落地即全 repo 強制。

1. facade ＋ lint 工具 ＋ 兩者自身測試先落地；同批完成全量遷移，
   lint 落地的 commit 即全綠。
2. 按目錄分批 commit：`world/rules/`（最大，約半數呼叫點）→
   `world/ai/` ＋ `world/art/` → `world/quests/` ＋ `world/maps/` →
   `typeclasses/` ＋ `commands/` ＋ `server/` ＋ 其餘。每批跑該目錄
   focused tests。
3. 每處遷移不只是換 import：
   - 補有意義的 context（該處可取得的 room／tick／layer／pk）；
   - 吞掉的例外改 `log_error(..., exc=error)` 或補豁免註解；
   - 自由句子改 snake_case event 碼；
   - 依 §4 事件目錄點亮該子系統的正常路徑。
4. 現有 patch `evennia.logger.log_warn` 的測試改成 patch facade 函式。
5. `web/webclient` 下的非瀏覽器 JS／Python 介面若無 log 呼叫則不受影響；
   有則同規則遷移。

## 6. 錯誤處理

- facade 永不拋例外（§3.1 stderr 退路）。
- lint 對無法 parse 的檔案報 violation。
- 事件目錄由 AGENTS.md 規則 ＋ OpenSpec verify 清單雙重把關；lint 不
  靜態驗證正常路徑 coverage（AST 無法可靠判定），這是刻意的邊界。

## 7. 測試

- `tools/tests/test_observability_lint.py`（stdlib `unittest`）：以
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
   時間線，且任一人为制造的失敗（如擋掉 SD endpoint）在 log 單行內即
   可辨識 event、context、例外鏈。
