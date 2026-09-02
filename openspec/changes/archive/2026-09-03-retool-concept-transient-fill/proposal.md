# retool-concept-transient-fill

## Why

概念（concept）功能目前把 LLM 生成的 persona 藏進一個伺服器獨有的概念草稿，呈現契約（archive `creation-persona-persistence` D4）又規定 persona 內容從不下線，於是玩家在套用概念後只看到預填的數值，背景輸入框一片空白——LLM 確實寫了生平，但整個 WebClient 沒有任何地方顯示它。archive 自己的 Open Questions 也承認「瀏覽器是否該讓玩家檢視／編輯生成 persona」是被延後的懸案。設計源頭：`docs/superpowers/specs/2026-09-02-concept-transient-fill-persona-design.md` §1–§4、§10。

## What Changes

- 概念降為暫態填入器：`creation.concept` 一次呼叫、零持久寫入，驗證過的提案（含暫態 `revision` 序號）經 session 瞬態槽（`session.ndb.concept_proposal` → `build_presentation_context` 快照 → panel `proposal` 槽，仿 `options_state` 既有模式）送達客戶端填入表單。**BREAKING**（draft 與 panel schema 變更，無相容層）。
- 退役伺服器端概念草稿：`concept_filled` 草稿階段、`apply_concept_proposal`、指紋 CAS 的 concept 用途、custom save 的 persona 承接與 race 比對分支、wire 欄位 `background_generated` 與「背景已生成」指示文字，全數刪除。
- `custom_filled` 草稿新增必現、值可 null 的 `persona` 鍵（恰 `{personality, life_story, habit}`、各自 1..600 字非空）；`creation.custom` payload 增必填 `persona` 鍵（null 或恰三鍵物件），伺服端只驗格式與數值規則、不驗語意。
- `creation` panel schema v1 → v2：增 optional 頂層 `proposal` 槽與 draft 的 `persona` 鍵；啟動的 persona 來源從概念草稿改讀 custom draft。
- Vue 表單：收到 proposal 即填入本地未送出的表單（種族、血統、配點、三個 persona textarea），三 textarea 恆渲染、採「要填就填滿」本地驗證；換種族帶生成文字時顯示純 UI 審視提示。
- Telnet `character concept` 流同步降為暫態：顯示提案摘要 → 收名字與年齡 → 直接啟動，不再經概念草稿。

## Capabilities

### New Capabilities
- `concept-transient-fill`: 概念的暫態填入語意——一次呼叫零持久寫入、session 瞬態提案槽及其生命週期、panel `proposal` 渲染、persona 作為 custom draft／payload／啟動來源。

### Modified Capabilities
- `creation-persona-persistence`: 概念草稿階段、指紋 CAS 的 concept 用途、custom save 承接規則退役（REMOVED）；啟動 persona 寫入來源由概念 draft 改為 custom draft（MODIFIED）；「後台可自由更新 background」與「background 貫穿旅程」兩條要求以 MODIFIED 清除概念相關條目。
- `webclient-character-creation-ui`: panel v2（optional `proposal`、draft `persona`）、draft 只餘兩模式、custom payload 增 `persona` 鍵、「面板不暴露 persona」斷言反轉為「persona 僅以 proposal 與 draft 兩種身份上線」。
- `player-character-creation`: custom 模式收集可編輯 persona 塊；custom draft 承載 persona 鍵。
- `character-creation-ux`: 建立 surface 的 concept 條目改寫為暫態填入器語意。

## Impact

- `world/rules/creation_wizard.py`（退役概念草稿與承接、draft persona 鍵）、`world/rules/character_creation.py`（啟動 persona 來源）、`web/webclient/actions/creation_actions.py`（concept 零寫入＋session 槽、custom validator 9 鍵）、`web/webclient/presentation/creation.py`（v2）、`web/webclient/presentation/context.py` 與 `web/webclient/presentation/ingress.py` 的 `build_presentation_context`（提案快照欄與 revision，仿 `options_state`）、`web/webclient-app/components/CreationOverlay.vue`、`web/static/webclient/js/elosern/protocol.js`、`commands/character_creation.py`（Telnet 暫態流）。
- 測試：`world/rules/tests/test_creation_wizard.py`、`test_character_creation.py`、`web/webclient/presentation/tests/test_creation_panel.py`、`web/webclient/actions/tests/test_creation_actions.py`、JS Node 鏡像驗證器案、Vitest `creation_overlay`、一個 Playwright class；`.github/evennia-shards.json` 同步。
- 無後端相容層（未發布、零使用者）。與 `add-persona-edit-surface` 無檔案重疊，可完全平行。
