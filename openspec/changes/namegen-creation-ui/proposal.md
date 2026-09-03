# namegen-creation-ui — Proposal

## Why

前置三個 change 已鋪完路:`npc-namegen-lore-registry`／`npc-namegen-rules-roller` 交付名字規則層(`world/rules/namegen.py` 的 `roll_name_for_race(race_key, sex, rng)`,race/sex 對照、race 為 `None` 時走規則層 sorted 已綁定包兜底、永不拋錯)與 `NAME_PACK_REGISTRY` 語料;`oob-result-data-slot` 交付 `ui_action_result` 的 success 條件性 `data` 槽(emitter 透傳、雙端鏡像驗證、store 透傳)。設計文件 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5 要求把這套語料接進角色創建 UI:自訂表單目前沒有性別欄位(`world/lore/sex.py` 的 `SEX_VALUES` 在創建側完全未被收集,`world/imports/loader.py` 已寫 `entity.sex` 而創建流沒有對應缺口補齊),也沒有擲名入口,玩家無法用世界語料取名。本 change 是最後的接線片:panel 送 sex 選項、`creation.custom`/草稿帶 sex、新 UI action `creation.roll_name` 經既有 `ui_action` 通道回擲名、前端加性別下拉與 🎲 按鈕回填姓名欄。

## What Changes

- **Panel v4**:`world/rules/creation_wizard.py` 的 `CustomFormView` 與 `web/webclient/presentation/creation.py` 的 `custom` 描述元新增 `sex` 欄——至多 8 個 `{key, label}` 選項,由 `world/lore/sex.py` 的 `SEX_VALUES` 加後端中文標籤(女性/男性/其他)派生,前端不寫死;`CREATION_SCHEMA_VERSION` 3→4(雙向鏡像同 bump)。
- **sex 收斂進資料流**:`creation.custom` payload 加選填 `sex`(缺或 null → `DEFAULT_SEX`);自訂草稿帶 nullable `sex` 持久化/還原(同 `display_name`);`CharacterCreationRequest` 加 `sex` 欄,preflight 驗證為 `SEX_VALUES` 成員或 None(None→`DEFAULT_SEX`),`activate_player_character` 寫 `entity.sex`(補齊 loader 已有而創建側沒有的缺口),rollback 快照鍵集合跟隨。
- **新 UI action `creation.roll_name`**:payload 恰好 `race`/`subrace`/`sex`(均可 null);adapter 做**語意驗證**——`race` 為 null 或 `RACE_REGISTRY` 成員、`subrace` 為 null 或屬該 race 的 `SUBRACE_REGISTRY` 成員(race 為 null 時 subrace 必為 null)、`sex` 為 null 或 `SEX_VALUES` 成員,表外值走既有 validation error(`rejected`,經既有結果通道回 `ui_protocol_error` 級錯誤語意),**不得兜底成功**;通過驗證後經 `roll_name_for_race` 以 adapter module 層級唯一私有未種子化 `random.Random()`(只在 roll_name 路徑使用)擲名,**零持久寫、不刷 panel**,結果經 `ui_action_result` 的條件性 `data` 槽帶 `{display_name}`(envelope 契約由前置 `oob-result-data-slot` 交付,本 change 只消費)。
- **前端**:`CreationOverlay.vue` 姓名欄下方加性別 `<select>`(選項讀自 panel `custom.sex`)、姓名輸入框右側加 🎲 按鈕(`data-testid="creation-roll-name"`),點擊 dispatch `creation.roll_name`,收到結果即回填姓名欄(玩家仍可手動改寫,最終以 `creation.custom` 經 `_validate_name` 為準);`creation_menu.js` 純邏輯帶 sex 進 draft/payload 與擲名 payload;`protocol.js` 同步 panel v4 與 `creation.roll_name` payload 驗證表(result `data` envelope 鏡像屬前置 `oob-result-data-slot`,不動)。
- **無相容層**:系統未發布、零使用者,舊 panel v3 payload 直接由版本閘門拒絕,不保留雙棧。

## Capabilities

### Modified Capabilities

- `webclient-character-creation-ui`:panel schema 升 v4 且 `custom` 描述元加 `sex` 選項欄;自訂草稿帶 nullable `sex`;action 註冊表加 `creation.roll_name` 且 `creation.custom` 收選填 `sex`;dock 鍵盤優先契約涵蓋性別下拉與擲名按鈕。
- `player-character-creation`:custom 模式收集選填 sex;規則層驗證 sex 並 persisted 到角色 entity(`entity.sex`),preset 與缺 sex 的 custom 走 `DEFAULT_SEX`。

### New Capabilities

(無。)

## Impact

- **依賴順序(四級前置鏈)**:`npc-namegen-lore-registry` → `npc-namegen-rules-roller` → `oob-result-data-slot` → 本 change。本 change 直接 import 前兩者的 `roll_name_for_race`／`NAME_PACK_REGISTRY`,並**只消費** `oob-result-data-slot` 已定的 result `data` envelope——emitter／雙端驗證器／store 透傳皆不動,故本 change 無協議層工作包(原 `test_dispatcher`／`test_protocol` 的 `data` 槽測試與 JS result `data` 鏡像、store 透傳已整體搬至該 change)。
- `world/rules/creation_wizard.py`(`CustomFormView.sex`、`build_custom_form`、draft 正規化/序列化、preflight 接 sex)
- `world/rules/character_creation.py`(`CharacterCreationRequest.sex`、`_validate_sex`、`_ValidatedCreation.sex`、activation 寫 `entity.sex`、`_CREATION_ATTRIBUTE_KEYS` 加 `sex`)
- `world/lore/sex.py`(僅消費 `SEX_VALUES`/`DEFAULT_SEX`,不動)
- `web/webclient/presentation/creation.py`(panel v4、`custom.sex`、wire 驗證)、`web/webclient/actions/creation_actions.py`(`roll_name` adapter 含語意驗證與模組級私有 rng、custom sex 欄)、`web/webclient/actions/registry.py`(註冊 `creation.roll_name`)
- `web/static/webclient/js/elosern/protocol.js`(`CREATION_SCHEMA_VERSION` 4、`custom.sex`、`creation.roll_name` payload 驗證表;result `data` 鏡像屬前置 change,不動)、`creation_menu.js`(draft/payload/擲名 payload)、`web/webclient-app/components/CreationOverlay.vue`(性別 select、🎲 按鈕、回填)、`web/webclient-app/tests/overlays/creation_overlay.test.js`、`web/webclient-app/stories/Overlays/CreationOverlay.stories.js`(stores/elosern.js 的 `data` 透傳屬前置 change,不動)
- 測試:`world/rules/tests/test_character_creation.py`、`world/rules/tests/test_creation_wizard.py`、`web/webclient/presentation/tests/test_creation_panel.py`、`web/webclient/actions/tests/test_creation_actions.py`、JS `node --test`(`protocol.test.js`、`creation_menu.test.js`、`ui_contract.test.js`)
- 不動:`docs/game/commands.md`(`creation.roll_name` 是 UI action 不是玩家命令,判斷記錄於 design.md)、`character-creation-ux`(Telnet 精靈不收集 sex,預設走 `DEFAULT_SEX`,語意不變)、`.github/evennia-shards.json`(全部測試落點皆已登記)
