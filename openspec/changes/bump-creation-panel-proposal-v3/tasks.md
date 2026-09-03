# bump-creation-panel-proposal-v3 — Tasks

實作順序即分組順序：slot（actions）→ snapshot/context → presenter v3 → JS 鏡像 → 測試與登記。每組做完先跑該組 focused 測試再勾選；不跑 CI shard 指令。

## 1. Session 槽與快照（web/webclient）

- [x] 1.1 `web/webclient/actions/creation_actions.py` 的 `_store_proposal`：槽 dict 增五個 optional 鍵——從提案讀 `display_name`／`age`／`apparent_age`／`background`／`affinity_elements`，值為 `None` 時不寫鍵（缺席＝鍵不存在），`affinity_elements` 寫成 plain list。
- [x] 1.2 `web/webclient/presentation/context.py`：`ProposalSnapshot` 增五個 optional 欄位（`None` 缺席）與 `as_dict` 條件序列化（缺席鍵不入 dict）；建構／owner 驗證路徑沿用既有模式。
- [x] 1.3 `web/webclient/presentation/ingress.py` 的 `build_presentation_context`：提案快照深拷貝帶五鍵（缺席合法、缺槽／損毀／owner 不符降級 None 的既有路徑不動）。

## 2. Presenter v3（web/webclient/presentation/creation.py）

- [x] 2.1 `CREATION_SCHEMA_VERSION = 3`；`_validate_proposal` 增五個 optional 鍵的精確校驗——`display_name` 1..64 code points、`age`／`apparent_age` 整數 18..10000（bool 拒絕）、`background` 1..600、`affinity_elements` ≤8 個已註冊元素鍵無重複清單；缺席鍵合法、null 值拒絕；未知鍵拒絕。
- [x] 2.2 更新 `web/webclient/presentation/tests/test_creation_panel.py`：v3 通過／v2 拒絕；proposal 帶五鍵渲染；缺席五鍵省略（非 null）；五鍵的界外值（17 歲、65 字名、601 字背景、9 元素、null 值）逐一結構拒絕；worst-case（3×600 persona + 600 background + 64 名 + 兩 int + 8 元素）envelope 上限斷言。掛 `covers_requirement` 於 `concept-transient-fill::creation-panel-renders-the-transient-proposal` 與 `webclient-character-creation-ui::creation-panel-is-exact-read-only`（先跑 `uv run --locked python -m tools.spec_traceability list` 取 canonical ID）。
- [x] 2.3 更新 `web/webclient/actions/tests/test_creation_actions.py`：concept 套用後槽含五鍵（提案帶值時）／省略（提案缺席時）；save／reset 清槽路徑不受影響。
- [x] 2.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation web.webclient.actions`。

## 3. JS 鏡像（protocol.js / creation_menu.js）

- [x] 3.1 `web/static/webclient/js/elosern/protocol.js`：`CREATION_SCHEMA_VERSION = 3`；creation panel `proposal` 槽鏡像驗證器增五個 optional 鍵（同界值、缺席合法、null 拒絕）。
- [x] 3.2 （查證取消）`creation_menu.js` 經查證無 panel 驗證器（只還原已驗證面板）——零改動；僅其 Node 測試 fixture 的 schema 字面隨 3.3 遷 v3。
- [x] 3.3 更新 `web/static/webclient/js/tests/` 鏡像案：v3+五鍵通過、v2 payload 拒絕、缺席省略、null 值拒絕。跑 `node --test web/static/webclient/js/tests/*.test.js`。

## 4. 收尾與登記

- [x] 4.1 既有瀏覽器 creation 測試（`web/tests/browser/test_browser_creation.py`）與 Vitest 中任何 panel 形狀／schema_version 斷言遷到 v3（僅形狀遷移，不加新行為斷言——新行為屬 `retool-concept-fill-navigation`）。
- [x] 4.2 `uv run --locked python -m tools.spec_traceability check`；`openspec validate bump-creation-panel-proposal-v3 --strict`；`uv run --locked python -m tools.observability_lint check`；確認 `.github/evennia-shards.json` 無需變動（無新測試模組）。
- [x] 4.3 `tests/test_creation_parity_contract.py`：allowlist 錨改 `creation: 3`、版本常量一致斷言、新增 proposal display-name 界平行錨；focused 跑 `tests.test_creation_parity_contract`。
