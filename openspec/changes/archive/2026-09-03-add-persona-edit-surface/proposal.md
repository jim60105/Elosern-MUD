# add-persona-edit-surface

## Why

設計文件 `docs/superpowers/specs/2026-09-02-concept-transient-fill-persona-design.md` §5 把生成 persona 的第二個階段——啟動後檢視與編輯——交給玩家。角色面板目前只顯示 `persona` 區塊的 `background` 單鍵（archive `creation-persona-persistence` 的產物），玩家在建立期存進去的人格、生平、習慣三欄，啟動後無處可見、無處可改，等建立表單把 persona 交給玩家之後，啟動卻又把其中三欄鎖回黑箱。本變更把四鍵敘事文字統一為一套可編輯面。設計源頭 §5.1–§5.4、§6、§7、§10。

## What Changes

- 寫入服務 `world/rules/persona_edit.py`：`update_background` 泛化為 `update_persona_field(character, field, text)`，欄位白名單為模組常數 `PERSONA_EDITABLE_FIELDS`（恰 `background / personality / life_story / habit`）；trim＋600 字上限驗證、None/空白移除該鍵、無 record 時建 import-card 形狀、其餘鍵（含未知鍵）原樣保留。`update_background` 保留為薄包裝，既有呼叫者零改動。
- 新 action `character.persona.update`（恰 `{field, text}`）：四鍵白名單、所有權解析、直呼 `update_persona_field`、重新整理 character panel、穩定拒絕碼。registry 恰鍵清單同步＋1。
- `character` panel schema v6 → v7：`persona` 區塊從恰 `{background}` 擴為恰 `{background, personality, life_story, habit}`，各自可 null、上限 600 字；presenter 逐鍵清洗；`protocol.js` 鏡像同步。
- `CharacterStatusDrawer.vue`：背景區塊升級為四段顯示（個性、生平、習慣、背景），空值走「未設定」佔位。
- Telnet 命令家族：`設定背景` 不動；新增 `設定個性`（個性）、`設定生平`（生平、背景故事）、`設定習慣`（習慣），行為逐字複製 `CmdBackground` 三段式，全經 `update_persona_field`。命令文件兩式同步。

## Capabilities

### New Capabilities
- `persona-editing`: 啟動後的四鍵 persona 編輯契約——伺服端單一寫入服務、`character.persona.update` action、四鍵命令家族、四段角色面板顯示。

### Modified Capabilities
- `creation-persona-persistence`: 「後台可自由更新 background」要求以 MODIFIED 升級為四鍵編輯白名單。
- `webclient-action-dispatch`: registry 恰鍵清單增 `character.persona.update`。
- `webclient-exploration-menu`: `character` panel schema version-5 要求由 version-7 要求取代（live code `CHARACTER_SCHEMA_VERSION` 現為 6 → 7）、`persona` 區塊四鍵；伺服器常數、registry 導出版本、unavailable form、JS allowlist 與逐面板版本複核全部同步落 v7。
- `game-command-docs`: persona 命令家族條目。

## Impact

- `world/rules/persona_edit.py`、`web/webclient/actions/character_actions.py`、`web/webclient/presentation/character.py`、`web/static/webclient/js/elosern/protocol.js`、`web/webclient-app/components/CharacterStatusDrawer.vue`、`commands/background.py`（抽出共用基底類別並保留 `CmdBackground`）、`commands/persona.py`（三個新命令子類別別）、`commands/default_cmdsets.py`（掛載）、`docs/game/commands.md`、`docs/game/command-reference.md`、`tests/test_command_docs.py`。
- 測試：persona_edit 純邏輯四鍵×四路徑；action 與 panel presenter 整合案；三命令 `EvenniaCommandTest`；JS 鏡像與 Vitest 四段渲染；`.github/evennia-shards.json` 註冊新測試模組。
- 邊界：`identity / appearance / social_connection` 三鍵維持排除（§10），本變更只開放四鍵敘事文字。
- 檔案重疊僅 `protocol.js`／registry 與 change A 的建立面（不同函式），可與 A 錯峰；與 C 無重疊。
