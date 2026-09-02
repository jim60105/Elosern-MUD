# retool-concept-transient-fill — Tasks

實作順序即分組順序：contract（draft/規則）→ actions/presenter → wire（JS 鏡像）→ Vue → Telnet → 文件與登记。每組做完先跑該組 focused 測試再勾選；全程不跑 CI shard 指令。

## 1. Draft 與規則層（world/rules）

- [x] 1.1 `world/rules/creation_wizard.py`：`DRAFT_VERSION` 升 2；`CUSTOM_STAGE` 形狀增必現 `persona` 鍵（null 或恰 `{personality, life_story, habit}`，經 `_validate_persona_block`）；`_normalize_draft` 對缺 `persona` 鍵的 custom 形狀走既有降級路徑；刪除 `CONCEPT_STAGE`、`_normalize_background` 的 concept 分支、`apply_concept_proposal`、以及 save 時的 persona 承接／race 比對（`save_custom_draft` 直存送來的 persona）。指紋 helper 保留（啟動確認用）。
- [x] 1.2 `world/rules/character_creation.py`：`activate_player_character` 的 persona 來源改接 custom draft 的 `persona` 鍵（null → 走既有 background-only 分支）；concept 相關註解清除。
- [x] 1.3 更新 `world/rules/tests/test_creation_wizard.py`：persona 鍵的往返／malformed 拒絕／缺鍵降級；退役概念階段與承接的消極斷言（模組表面無 `apply_concept_proposal`、存舊形狀 draft 降級為無 draft）。`world/rules/tests/test_character_creation.py`：啟動 persona 來自 custom draft、null persona 僅 background、寫入失敗回滾。掛 `covers_requirement` 於 `concept-transient-fill::persona-rides-the-custom-draft-payload-and-activation` 與 `creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape` 等 ID（先跑 `uv run --locked python -m tools.spec_traceability list` 取 canonical ID）。
- [x] 1.4 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_wizard world.rules.tests.test_character_creation`。

## 2. Actions 與呈現層（web/webclient）

- [x] 2.1 `web/webclient/actions/creation_actions.py`：`_validate_custom_payload` 改九鍵 exact-set（增必填 `persona`：null 或恰三鍵、各自 1..600 非空）。`_creation_concept_adapter` 改零持久寫入：跑 guarded pipeline → 驗證提案 → （完成時 `session.puppet` 仍是准入 actor 才）寫 `session.ndb.concept_proposal`（覆蓋式，含 `owner_actor_id` 綁定）→ `_success("concept_applied", AFFECTED_CREATION)`——概念路徑完全不讀寫 `FINGERPRINT_NDB_KEY`；降級走既有穩定碼；删 fingerprint／stale 分支。`_creation_custom_adapter` 與 `_creation_reset_adapter` 成功後清 `session.ndb.concept_proposal`。
- [x] 2.2 `web/webclient/presentation/context.py`：新增 frozen `ProposalSnapshot`（仿 `OptionsSnapshot`：`revision` ＋四內容鍵＋owner 驗證、deep-copy）與 `PresentationContext.proposal` 欄位；`web/webclient/presentation/ingress.py` 的 `build_presentation_context`（所有發布路徑唯一的 context 工廠）加提案快照深拷貝（缺槽／損毀／owner 不符降級為 None，仿 `options_snapshot`），並在換偶／sequence 重置路徑清 `concept_proposal`。
- [x] 2.3 `web/webclient/presentation/creation.py`：`CREATION_SCHEMA_VERSION` 升 2；draft custom 形狀增 `persona`（null 或三鍵物件）；增 optional 頂層 `proposal` 鍵（僅 slot 有值時）；驗證器同步；worst-case 600×3 persona 的 envelope 上限測試。刪 `background_generated`。
- [x] 2.4 更新 `web/webclient/actions/tests/test_creation_actions.py` 與 `web/webclient/presentation/tests/test_creation_panel.py`：九鍵 validator、concept 零寫入＋slot 生命週期（套用／save 清除／reset 清除／再套用覆蓋且 revision 遞增）、完成序 ui_update 先於 result 且含 proposal、panel v2 proposal 槽渲染與省略、reconnect 無 proposal。掛 traceability ID（`concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes`、`::creation-panel-renders-the-transient-proposal`）。
- [x] 2.5 Focused：`... evennia test --settings test_settings.py --keepdb web.webclient.actions web.webclient.presentation`。

## 3. Wire 鏡像（protocol.js）

- [x] 3.1 `web/static/webclient/js/elosern/protocol.js`：creation panel v2 鏡像驗證（optional `proposal` 四鍵、draft `persona`）；`creation.custom` payload 九鍵鏡像（含 persona null/三鍵）。同步 JS 端 schema 常量註解（O2 對應處）。legacy `creation_menu.js` 完整切 v2：`stateFromDraft`／`defaultCustomState`／`validateCustom`／`customPayload` 移除 concept draft 分支與 `background_generated` 假設、persona 入 form state 與 payload。
- [x] 3.2 更新 `web/static/webclient/js/tests/` 鏡像測試：v2 通過／v1 payload 拒絕／proposal 鍵精確性。跑 `node --test web/static/webclient/js/tests/*.test.js`。

## 4. Vue 表單（CreationOverlay.vue）

- [x] 4.1 persona 三 textarea 恆渲染（刪 `background_generated` 指示與 `#creation-result-message` 相關殘留）；form state 增 persona 欄位；`syncFromDraft` 帶 persona；送出組裝九鍵（全空→null，部分填→本地擋）。
- [x] 4.2 proposal 填入：watch panel `proposal`，僅當 `revision` > 本地已套用序號時填入並記入該序號（重建不覆寫編輯、相同內容新套用仍覆蓋）；填入 race/subrace/allocations/persona；切 custom 模式採「確認後切換」；race 不符且本地有 persona 文字 → 非阻擋審視提示（純文案）。
- [x] 4.3 Vitest：`web/webclient-app/tests/` 增 proposal 填入、同 revision 重建不覆寫編輯、遞增 revision 覆蓋（含內容相同者）、部分填擋送出、審視提示案例。`npm test`。
- [x] 4.4 `npm run build`、`npm run build-storybook`、`npm run showcase-coverage`（新 surface 若影響 showcase 清冊則同步）。

## 5. Telnet 概念流（commands）

- [x] 5.1 `commands/character_creation.py`：`CmdCharacterConcept` 改暫態流——guarded pipeline 成功後顯示提案摘要（含三欄 persona 文字）、以互動提示收名字＋兩年齡、過成年閘後直接以提案值＋persona 啟動；刪 `apply_concept_proposal` 呼叫與 concept 提示狀態。語法／別名不變。
- [x] 5.2 更新 `commands/tests/test_command_branch_behaviour.py` 的 concept 分支案：摘要→補欄→啟動、離線降級、成年閘不可繞過。

## 6. 文件、登记與收尾

- [x] 6.1 `docs/game/commands.md` 與 `docs/game/command-reference.md`：概念流描述更新（無「存草稿」措辭；命令鍵／別名不動）、確認 `設定背景` 條目不受影響；`tests.test_command_docs` 綠。
- [x] 6.2 若 1/2/5 組新增測試模組：同變更更新 `.github/evennia-shards.json`，跑 `tests.test_evennia_test_optimization_contract`。
- [x] 6.3 刪 `tmp/deltas/`、`tmp/story_settings/` 之外本變更暫存；確認無 `background_generated`／`apply_concept_proposal`／`concept_filled` 殘留（`rg` 消極檢查，openspec archive 除外）。瀏覽器測試（`web/tests/browser/test_browser_creation.py` 的 raw custom envelope 與 persona-absent 斷言）、`stories/fixtures.js`、Vue/Node 測試全部遷到 v2 形狀。
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check`；`openspec validate retool-concept-transient-fill --strict`。
- [x] 6.5 終局驗證：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world web.webclient` 一次；瀏覽器手動 smoke（建立 → concept 套用 → 表單填入含三 textarea → 存 → 啟動）若環境可用。
