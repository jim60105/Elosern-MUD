# oob-result-data-slot — Design

## Context

`webclient-oob-protocol` main spec 的「Result and protocol-error envelopes are exact and non-overlapping」規定 `ui_action_result` 恰七鍵，僅 `outcome == "error"` 時可多 `correlation_id`；三處實作同步——`web/webclient/actions/dispatcher.py` 的 `_normalize_result`（adapter 回值正規化）與 `_send_action_result`（envelope 構造）、`web/webclient/presentation/protocol.py::validate_ui_action_result`（伺服器端精確驗證，`_require_exact_fields` 以 `{"correlation_id": "conditional"}` 表達條件槽）、`web/static/webclient/js/elosern/protocol.js::validateActionResult`（瀏覽器鏡像）。下游 `namegen-creation-ui` 的 `creation.roll_name` 要在成功結果裡回 `{display_name}` 給發起畫面即時回填；設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5.2 明文「回 `ui_action_result` 帶 `{"display_name": ...}`」。本 change 把這個 envelope 擴充獨立成通用協議能力：不帶任何特定消費端（registry 不出現 `creation.roll_name`、前端不出現回填 UI），只交付槽契約、雙端鏡像驗證、store 透傳。系統未發布、零使用者 → 無相容層。

既有結果流的消費者（Vue store `web/webclient-app/stores/elosern.js`）對 result 做鏡像驗證後以白名單鍵視圖呈現；擴充必須讓合法 `data` 不被 strip，否則槽在瀏覽器端形同不存在。

## Goals / Non-Goals

**Goals**

1. `ui_action_result` 的 success 條件性選填 `data` 槽：語意、界、缺席預設值全部進 main-spec delta 並由雙端驗證器執行。
2. 伺服器 emitter（`_normalize_result` → `_send_action_result`）與伺服器 validator（`validate_ui_action_result`）與 JS 鏡像（`validateActionResult`）三處同步，雙向 parity。
3. JS store 的 result 視圖透傳驗證過的 `data`，發起畫面可讀。
4. 既有結果流逐鍵不變：所有不回 `data` 的 adapter 其 envelope 位元組級同形。

**Non-Goals**

- 任何具體消費 action（`creation.roll_name` 的 adapter、registry 註冊、前端回填按鈕）——全部屬 `namegen-creation-ui`。
- `ui_protocol_error` 加 `data`（錯誤結果帶 payload 違反「非 success 不可帶」契約本身）。
- panel/snapshot/update envelope 的任何變動；`ui_update` 路徑不動。
- 結果快取（in-flight/request cache）語意變動——快取的仍是正規化後的 dict，`data` 只是多一個合法鍵。

## Decisions

### D1 — 槽形態：`correlation_id` 式條件鍵，僅 success 可存在

仿 `correlation_id` 的條件槽模式，`ui_action_result` 加選填 `data`：僅當 `outcome == "success"` 且被准入 adapter 明確回帶時存在；缺席是預設（所有既有 adapter 不回）。值為 JSON object，至多 8 鍵、鍵名 1..64 小寫識別字、值為 JSON-safe 標量/object/list 且沿用全域 envelope 界（ nesting ≤8、字串 ≤2048 cp、safe-integer 界等）；內容不得攜帶 actor、session、epoch、revision、exception、本地路徑或 live object 引用（由「值必須 JSON-safe、emitter 只序列化純資料」結構性保證，驗證器再擋非 JSON-safe 型別）。拒絕的替代方案：
- (拒) 借用 `message` 欄塞 JSON——違反「message 是 1..512 code points 安全顯示文字」契約，前端要解析顯示欄，屬編碼 hack。
- (拒) 走 `ui_update` panel 快照——即時建議值無 canonical 狀態可刷 panel，硬造 session slot 重量與需求不成比例，且值會隨快照重複送達。
- (拒) 無限界 `Any` payload——exact-envelope 契約是本 capability 的存在理由，無界槽把 65 KB/nesting 防護讓渡給 adapter 誠實。
界額（8 鍵）取自「一個結果值不是面板」原則：超過即該走 panel，不該塞結果槽。

### D2 — 伺服器端：正規化層驗證、emitter 條件掛鍵、validator 鏡像

- `_normalize_result`：`outcome == "success"` 時接受選填 `data`，逐界驗證（object、≤8 鍵、鍵 1..64 小寫識別字、值 JSON-safe 且沿全域界）；**驗證失敗不吞成內部錯誤**——非 success 帶 `data`、或 `data` 超界，屬於 adapter 契約違反，走既有「out-of-schema adapter result → `_internal_result`」路徑（瀏覽器永遠不會看到 out-of-schema 結果）。非 success 結果一律丟棄 adapter 誤帶的 `data` 前先判形：其存在本身就是 schema 違反 → 同樣走內部錯誤路徑，與 `correlation_id` 的既有處理對稱。
- `_send_action_result`：僅當正規化結果實際含 `data` 時掛鍵——既有 adapter 的結果 dict 無此鍵，envelope 逐鍵不變（回歸測釘死）。
- `validate_ui_action_result`：`_require_exact_fields` 的條件表加 `"data": "conditional"`；`outcome == "success"` 時逐界驗證，非 success 出現即 `ProtocolValidationError`；返回 dict 只在存在時帶正規化 `data`。
請求端（`ui_action`）與 error envelope 完全不動。

### D3 — 瀏覽器鏡像：`validateActionResult` 同規則、store 白名單放行

JS `protocol.js::validateActionResult` 實作與 D2 validator 逐規則相同的驗證（接受 success+合法 `data`、拒非 success+`data`、拒非 object/超界），返回物件保留 `data`；雙向 parity 測試（同一組 fixtures 餵雙端）沿用 `protocol.test.js` 既有 pattern。`stores/elosern.js` 的 result 處理以鏡像驗證結果為準：驗證過的 `data` 鍵進 result 視圖、發起畫面（watch 最新 result 的 surface）可讀——若既有 normalize 逐白名單撿鍵，白名單加 `data`。非法 `data` 在鏡像驗證層就被拒，與既有 out-of-schema result 處置相同（不發佈髒鍵）。

### D4 — 測試全部擴充既有模組，shards 零變動

後端：`web.webclient.actions.tests.test_dispatcher`（adapter 回 `data` → envelope 帶鍵送達；非 success 帶 `data`／`data` 非 object／9 鍵／超界 → 內部錯誤路徑；既有無 `data` 結果 envelope 逐鍵不變）、`web.webclient.presentation.tests.test_protocol`（`validate_ui_action_result` accept/reject 矩陣）。新測試案掛 `@covers_requirement("webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping")`（先跑 `tools.spec_traceability list` 確認 canonical ID）。前端：node --test `web/static/webclient/js/tests/protocol.test.js`（鏡像雙向 parity）、Vitest store 結果路徑測（透傳不吞合法 `data`、髒 `data` 不發佈）。全部落點皆為已登記模組（shard 5 `web.webclient` package label 遞迴涵蓋）→ `.github/evennia-shards.json` 不動。無新 test module → 無 shard 任務。

### D5 — 消費端邊界：本 change 零 consumer 程式碼

registry、`creation_actions.py`、Vue 組件一行不動。消費端（`creation.roll_name`）只依賴本 change 交付的三件事：emitter 透傳、雙端驗證接受、store 透傳。這使兩 change 可嚴格串接驗證：本 change 的 focused 測試全綠即等於消費端的 envelope 前提成立，消費端只需測自己的 adapter/UI 契約。

## Risks / Trade-offs

- **[結果 envelope 擴充觸及全部結果流]** → `data` 預設缺席：既有 adapter 全部不回；回歸測斷言既有結果 envelope 逐鍵不變，鏡像驗證器以「非 success 帶 data 即拒」「超界即拒」場景釘死邊界。
- **[雙端鏡像漂移]** → 雙向 parity 測試用同組 fixtures 餵 Python validator 與 JS validator，任何一側獨放行即紅。
- **[store 白名單遺漏致槽失效]** → Vitest 透傳測直接斷言發起面可讀 `data`；消費端 change 的端到端測再兜一層。
- **[8 鍵界將來不夠用]** → 未發布階段界額是刻意的保守值；放寬是 spec 層 decision（MODIFIED delta），不是實作偷跑。

## Migration Plan

單次部署：後端（dispatcher + validator）與前端（protocol.js + store）同版發布；無資料遷移、無相容窗口（未發布零使用者）。回滾 = 回退兩端版本，條件槽自然消失，所有不回 `data` 的既有結果流行為不變。

## Open Questions

（無 — 槽形態、界額、失敗路徑、shard 判斷均已核定。）
