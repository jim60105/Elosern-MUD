# oob-result-data-slot — Proposal

## Why

現有 version-1 `ui_action_result` envelope 是 exact 七鍵（僅 `outcome == "error"` 時多一個 `correlation_id` 條件槽），任何額外鍵即被雙端驗證器拒絕——伺服器端 action 成功時沒有任何通用管道可把一個即時結果值（如擲名建議）直接回給發起畫面。`namegen-creation-ui` 的 `creation.roll_name` 需要回 `{display_name}`，但 envelope 擴充本身是與任何特定消費端無關的通用 OOB 協議能力：把它從消費端 change 拆出成獨立前置 change，協議層契約可先行定案、雙端鏡像驗證先行落地，同時讓 `namegen-creation-ui` 的工作包縮回單一工程師 8 小時內。設計源頭：`docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5.2（「回 `ui_action_result` 帶 `{"display_name": ...}`」）。

## What Changes

- `ui_action_result` 加**條件性選填 `data` 槽**：僅當 `outcome == "success"` 且被准入的 adapter 明確回帶時存在；值為 JSON object（至多 8 鍵、鍵名 1..64 小寫識別字、值為 JSON-safe 標量/object/list 且沿用全域 envelope 界），且不得攜帶 actor、session、epoch、revision、exception、本地路徑或 live object 引用。非 `success` 結果出現 `data`、`data` 非 object、或超界 → exact envelope 驗證拒絕。
- 伺服器端：`web/webclient/actions/dispatcher.py` 的 `_normalize_result` 接受並透傳 `data`（僅 success 可帶、驗證失敗走既有內部錯誤路徑）、`_send_action_result` 僅在實際存在時掛鍵；`web/webclient/presentation/protocol.py::validate_ui_action_result` 同步鏡像驗證。
- 瀏覽器鏡像：`web/static/webclient/js/elosern/protocol.js::validateActionResult` 加同樣的 success 條件 `data` 驗證；`web/webclient-app/stores/elosern.js` 的 result 視圖透傳 `data`（鏡像驗證後的合法鍵不被白名單 strip），讓發起畫面拿得到結果值。
- 向後不變：所有既有 adapter 都不回 `data` → 其結果 envelope 逐鍵不變；本 change 不新增 action、不改 panel、不動玩家命令面。無相容層（未發布、零使用者）。

## Capabilities

### New Capabilities

（無。）

### Modified Capabilities

- `webclient-oob-protocol`：「Result and protocol-error envelopes are exact and non-overlapping」一条——`ui_action_result` 的 exact 鍵集合加 success 條件性 `data` 槽，鏡像驗證器（伺服器端與瀏覽器）雙邊接受合法 `data`、拒絕非 success／非 object／超界 `data`；新增兩個 scenario（success 可帶 adapter data 槽、非 success 不可帶）。

## Impact

- `web/webclient/actions/dispatcher.py`（`_normalize_result`、`_send_action_result`）、`web/webclient/presentation/protocol.py`（`validate_ui_action_result`）。
- `web/static/webclient/js/elosern/protocol.js`（`validateActionResult`）、`web/webclient-app/stores/elosern.js`（result 視圖 `data` 透傳）。
- 測試全部擴充既有已註冊模組：`web.webclient.actions.tests.test_dispatcher`（success 掛鍵送達／非 success 出現即拒／`data` 非 object／9 鍵／超界走驗證失敗路徑／既有無 `data` 結果逐鍵不變）、`web.webclient.presentation.tests.test_protocol`（`validate_ui_action_result` 接受/拒絕矩陣）、JS `node --test` `protocol.test.js`（雙向 parity）、Vitest store 結果路徑（透傳不吞 `data`）。`.github/evennia-shards.json` 無需變動（無新 test module）。
- **依賴順序**：本 change 無上游代碼依賴（純協議層擴充），但必須排在 `namegen-creation-ui` 之前动工——四級前置鏈為 `npc-namegen-lore-registry` → `npc-namegen-rules-roller` → `oob-result-data-slot` → `namegen-creation-ui`。第一個（也是本 change 唯一動機性）消費端 `creation.roll_name` 的註冊、adapter 與前端回填屬 `namegen-creation-ui`；本 change 只交付 envelope 能力與鏡像驗證，registry 裡不出現任何具體 consumer action。
