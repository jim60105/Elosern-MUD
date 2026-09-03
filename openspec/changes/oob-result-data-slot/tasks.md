# oob-result-data-slot — Tasks

前置條件：無上游代碼依賴（純 OOB 協議層擴充）。實作順序：伺服器端 → 前端鏡像 → 測試 → 收尾。每組做完先跑該組 focused 驗證再勾選；全程不跑 CI shard 指令。工作量預估：後端 + 前端鏡像 + 測試約 5–6 小時，單一工程師一個工作日內。

## 1. 伺服器端：正規化、emitter、validator

- [ ] 1.1 `web/webclient/presentation/protocol.py`：新增私有 `_validate_result_data(value)`——`data` 須為 dict、≤8 鍵、鍵名 1..64 小寫識別字（沿用 `_validate_identifier` 形）、值為 JSON-safe 標量/object/list 且遞迴沿用全域界（nesting、字串 cp、safe-integer）；違規拋 `ProtocolValidationError`。`validate_ui_action_result` 的 `_require_exact_fields` 條件表加 `"data": "conditional"`：`outcome == "success"` 且鍵存在 → 驗證並把正規化 `data` 放進返回 dict；鍵缺席 → 返回 dict 不帶 `data`；非 `success` 且鍵存在 → 拋錯（對稱於 `correlation_id` 的既有拒法）。
- [ ] 1.2 `web/webclient/actions/dispatcher.py::_normalize_result`：success 結果讀選填 `data`，以 1.1 驗證器驗證；缺席 → 結果 dict 不帶鍵；違規（非 object、超界）或非 success 誤帶 `data` → 走既有 `_internal_result(None)` 路徑（out-of-schema adapter result 的既有處置，不吞、不部分接受）。
- [ ] 1.3 `web/webclient/actions/dispatcher.py::_send_action_result`：僅當正規化結果含 `data` 時在 envelope 掛鍵；無鍵時输出一份與現行完全相同的 envelope（回歸基線）。

## 2. 前端鏡像：protocol.js + store 透传

- [ ] 2.1 `web/static/webclient/js/elosern/protocol.js::validateActionResult`：實作與 1.1 逐規則相同的驗證——success+合法 object `data` 接受並保留；非 success 出現 `data` 拒；非 object／>8 鍵／鍵形不符／值超全域界拒。返回物件只在存在時帶 `data`。
- [ ] 2.2 `web/webclient-app/stores/elosern.js`：result 鏡像驗證後的視圖透傳 `data`——若既有 normalize 逐白名單撿鍵，白名單加 `data`；鏡像驗證拒絕的 result 走既有 out-of-schema 處置，髒 `data` 絕不發佈。

## 3. 測試（全部擴充既有已註冊模組；`@covers_requirement` 掛 `webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping`，先跑 `uv run --locked python -m tools.spec_traceability list` 確認 canonical ID）

- [ ] 3.1 `web/webclient/presentation/tests/test_protocol.py`：`validate_ui_action_result` 矩陣——success+合法 `data` 接受且返回帶鍵；success 無 `data` 返回無鍵；`rejected`／`stale`／`error`+`data` 拒；`data` 非 object／9 鍵／鍵名違規／值超全域界（超長字串、深 nesting）各別拒。
- [ ] 3.2 `web/webclient/actions/tests/test_dispatcher.py`：stub adapter 回 `{"outcome": "success", ..., "data": {...}}` → 發送的 envelope 帶 `data` 且過 `validate_ui_action_result`；adapter 非 success 帶 `data`／`data` 超界 → 內部錯誤 envelope 路徑；**回歸**：既有無 `data` adapter 的結果 envelope 與擴充前逐鍵相同（斷言鍵集合恰為既有集合）。
- [ ] 3.3 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_protocol web.webclient.actions.tests.test_dispatcher`。
- [ ] 3.4 `web/static/webclient/js/tests/protocol.test.js`：雙向 parity——同組 fixtures（合法 success+`data`、三類非 success+`data`、非 object、9 鍵、超界值）餵 `validateActionResult`，接受/拒絕判定與 3.1 的 Python 矩陣一一相同。驗證：`node --test web/static/webclient/js/tests/protocol.test.js`。
- [ ] 3.5 Vitest store 透傳測（落既有 store 結果路徑測所在檔，如 `web/webclient-app/tests/store/` 下既有 result/protocol 測試檔）：鏡像驗證通過的 `data` 出現在 result 視圖供發起面讀取；驗證失敗的 result 不發佈任何 `data` 鍵。驗證：`npm test`（篩該檔）。

## 4. 登記與收尾

- [ ] 4.1 確認 `.github/evennia-shards.json` 無需變動：3.1／3.2 落點已在 shard 5（`web.webclient` package label 遞迴涵蓋），無新 test module。
- [ ] 4.2 `uv run --locked python -m tools.spec_traceability check`（本 change 無新 main-spec requirement；確認掛標測試零錯誤）。
- [ ] 4.3 `openspec validate oob-result-data-slot --strict`。
- [ ] 4.4 確認零消費端殘留：`web/webclient/actions/registry.py`、`creation_actions.py`、Vue 組件、`world/` 全部不動（design D5）；`docs/game/commands.md` 不動（無命令面變動）。
