# bump-creation-panel-proposal-v3

## Why

`extend-concept-proposal-fields` 讓生成層提案帶上五個暫態填入欄位後，這些值目前停在 `CharacterProposal` 物件裡：session 瞬態槽只存 `{revision, race, subrace, allocations, persona}`，`creation` panel 的 `proposal` 槽 likewise 只有五鍵，前端拿不到名字、背景、年齡、親和。本變更把這條伺服器線路打通到 wire，為前端消費（owned by `retool-concept-fill-navigation`）提供承載。設計源頭：`docs/superpowers/specs/2026-09-03-concept-proposal-expansion-toast-feedback-design.md` §5.3。

## What Changes

- `_store_proposal`（`web/webclient/actions/creation_actions.py`）寫入 session 槽時帶上提案的五個正規化欄位（缺席欄位不寫鍵）。
- `ProposalSnapshot`（`web/webclient/presentation/context.py`）增五個 optional 欄位與序列化；`build_presentation_context` 深拷貝路徑同步。
- `creation` panel schema **v2 → v3**（**BREAKING**，無相容層）：`proposal` 槽物件增五個 optional 鍵，驗證器精確校驗（年齡 18..10000、名字 ≤64、背景 ≤600、親和為已註冊元素鍵清單且 ≤8、缺席鍵合法）；worst-case envelope 測試重鎖（persona 1.8 KB + 背景 600 + 名字 64 + 兩 int + 八元素鍵 < 65536 bytes）。
- `web/static/webclient/js/elosern/protocol.js` 鏡像驗證器同步 v3；legacy `creation_menu.js` 的 panel 驗證鏡像同步（其 form state 不讀新鍵——消費屬下一變更）。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `concept-transient-fill`: 「The creation panel renders the transient proposal」一條改寫——`proposal` 槽精確鍵集合增五個 optional 暫態填入鍵，缺席鍵合法。
- `webclient-character-creation-ui`: 「The creation panel is an exact read-only creation-mode panel」一條改寫——`schema_version` 為 3，`proposal` 鍵依暫態填入契約 v3 形狀渲染。

## Impact

- `web/webclient/actions/creation_actions.py`（`_store_proposal`）、`web/webclient/presentation/context.py`（`ProposalSnapshot`）、`web/webclient/presentation/ingress.py`（深拷貝欄位）、`web/webclient/presentation/creation.py`（v3 + 驗證器）、`web/static/webclient/js/elosern/protocol.js`、`web/static/webclient/js/creation_menu.js`。
- 測試：`web/webclient/actions/tests/test_creation_actions.py`、`web/webclient/presentation/tests/test_creation_panel.py`、Node 鏡像案、既有瀏覽器 creation 測試的 panel 形狀斷言。
- 前置：`extend-concept-proposal-fields`（提案物件先有新欄位可讀）。與 `add-action-feedback-toasts` 不相交。Vue 表單在本變更中不讀新鍵，panel v3 對現行 Vue 為向後相容的鍵增加（鏡像驗證器放行缺席）。
