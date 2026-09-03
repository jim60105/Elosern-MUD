# namegen-creation-ui — Proposal

## Why

前置三個 change 已鋪完路:`npc-namegen-lore-registry`／`npc-namegen-rules-roller` 交付名字規則層(`world/rules/namegen.py` 的 `roll_name_for_race(race_key, sex, rng)`,race/sex 對照、race 為 `None` 時走規則層 sorted 已綁定包兜底、永不拋錯)與 `NAME_PACK_REGISTRY` 語料;`oob-result-data-slot` 交付 `ui_action_result` 的 success 條件性 `data` 槽(emitter 透傳、雙端鏡像驗證、store 透傳)。設計文件 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5 要求把這套語料接進角色創建 UI:自訂表單目前沒有性別欄位(`world/lore/sex.py` 的 `SEX_VALUES` 在創建側完全未被收集,`world/imports/loader.py` 已寫 `entity.sex` 而創建流沒有對應缺口補齊),也沒有擲名入口,玩家無法用世界語料取名。本 change 是最後的接線片:panel 送 sex 選項、`creation.custom`/草稿帶 sex、新 UI action `creation.roll_name` 經既有 `ui_action` 通道回擲名、前端加性別下拉與 🎲 按鈕回填姓名欄。

## What Changes

- **Panel v4**:`world/rules/creation_wizard.py` 的 `CustomFormView` 與 `web/webclient/presentation/creation.py` 的 `custom` 描述元新增 `sex` 欄——至多 8 個 `{key, label}` 選項,由 `world/lore/sex.py` 的 `SEX_VALUES` 加後端中文標籤(女性/男性/其他)派生,前端不寫死標籤;`CREATION_SCHEMA_VERSION` 3→4(雙向鏡像同 bump)。
- **sex 收斂進資料流**:`creation.custom` payload 加選填 `sex`(缺或 null → `DEFAULT_SEX`;結構層只收 1..64 字串或 null,成員資格由規則層 `_validate_sex` 以穩定代碼 `unknown_sex` 拒絕);自訂草稿帶必填 `sex`(存歸一後的具體成員)持久化/還原(同 `display_name`);`CharacterCreationRequest` 加 `sex` 欄,`activate_player_character` 寫 `entity.sex`(補齊 loader 已有而創建側沒有的缺口),rollback 快照鍵集合跟隨。
- **新 UI action `creation.roll_name`**:payload 恰好 `race`/`subrace`/`sex`(均可 null);adapter 做**語意驗證**——`race` 為 null 或 `RACE_REGISTRY` 成員、`subrace` 為 null 或屬該 race 的 `SUBRACE_REGISTRY` 成員(race 為 null 時 subrace 必為 null)、`sex` 為 null 或 `SEX_VALUES` 成員,表外值走既有 validation error(`rejected`,經既有結果通道回 `ui_protocol_error` 級錯誤語意),**不得兜底成功**;通過驗證後經 `roll_name_for_race` 以 adapter module 層級唯一私有未種子化 `random.Random()`(只在 roll_name 路徑使用)擲名,**零持久寫、不刷 panel**,結果經 `ui_action_result` 的條件性 `data` 槽帶 `{display_name}`(envelope 契約由前置 `oob-result-data-slot` 交付,本 change 只消費)。
- **前端**:`CreationOverlay.vue` 姓名欄下方加性別 `<select>`(選項讀自 panel `custom.sex`、新表單以鏡像的 `DEFAULT_SEX` key 預選)、姓名輸入框右側加 🎲 按鈕(`data-testid="creation-roll-name"`),點擊 dispatch `creation.roll_name`,收到結果即回填姓名欄(玩家仍可手動改寫,最終以 `creation.custom` 經 `_validate_name` 為準);`creation_menu.js` 純邏輯帶 sex 進 draft/payload 與擲名 payload(未選/預設 → custom payload 不帶鍵,由伺服器歸一);`protocol.js` 同步 panel v4(版本常數、`PANEL_ALLOWLIST`、`custom.sex`、draft `sex` 鏡像驗證)並匯出 sex 詞彙鏡像常數;`creation.roll_name` 的 payload 驗證僅在伺服端 registry——客戶端 `protocol.js` 只驗證入站訊息,與既有 `creation.custom` 同形,不設出站驗證表。
- **dispatcher 完成通道(唯一的協議層變動)**:`_complete_action` 新增內部 `no_presentation` 結果旗標分支(僅 success/rejected 可帶,`_normalize_result` 永不複製到 envelope),讓 result-only 適配器如約「不刷 panel」;envelope 形狀、雙端驗證器、store 透傳零變動(見 design D10)。
- **echo 目錄登記**:`creation.roll_name` 無文字命令等價物 → 登記為 silent presentation control(`command_echo.js`、覆蓋 manifests、Node/Vitest/Python 三處消費端同步)。
- **無相容層**:系統未發布、零使用者,舊 panel v3 payload 直接由版本閘門拒絕,不保留雙棧(既有 JS/Vitest 樣板與釘選測試同批升 v4)。

## Capabilities

### Modified Capabilities

- `webclient-character-creation-ui`:panel schema 升 v4 且 `custom` 描述元加 `sex` 選項欄;自訂草稿帶必填 `sex`;action 註冊表加 `creation.roll_name` 且 `creation.custom` 收選填 `sex`;dock 鍵盤優先契約涵蓋性別下拉與擲名按鈕。
- `player-character-creation`:custom 模式收集選填 sex;規則層驗證 sex 並 persisted 到角色 entity(`entity.sex`),preset 與缺 sex 的 custom 走 `DEFAULT_SEX`。

### New Capabilities

(無。)

## Impact

- **依賴順序(四級前置鏈)**:`npc-namegen-lore-registry` → `npc-namegen-rules-roller` → `oob-result-data-slot` → 本 change。本 change 直接 import 前兩者的 `roll_name_for_race`／`NAME_PACK_REGISTRY`,並**只消費** `oob-result-data-slot` 已定的 result `data` envelope——wire envelope／雙端驗證器／store 透傳皆不動;唯一的 dispatcher 變動是 D10 的內部 `no_presentation` 完成分支(不變動任何上線訊息形狀,既有動作的出版行為零改變)。
- `world/rules/creation_wizard.py`(`CustomFormView.sex`、`build_custom_form`、draft 正規化/序列化、preflight 接 sex)
- `world/rules/character_creation.py`(`CharacterCreationRequest.sex`、`_validate_sex`、`_ValidatedCreation.sex`、activation 寫 `entity.sex`、`_CREATION_ATTRIBUTE_KEYS` 加 `sex`)
- `world/rules/creation_messages.py`(穩定代碼 `unknown_sex` + zh 訊息 + 片段映射)
- `world/lore/sex.py`(僅消費 `SEX_VALUES`/`DEFAULT_SEX`,不動)
- `web/webclient/presentation/creation.py`(panel v4、`custom.sex`、wire 驗證)、`web/webclient/actions/creation_actions.py`(`roll_name` adapter 含語意驗證與模組級私有 rng、custom sex 欄)、`web/webclient/actions/registry.py`(註冊 `creation.roll_name`)、`web/webclient/actions/dispatcher.py`(僅 D10 完成分支)
- `web/static/webclient/js/elosern/protocol.js`(v4 鏡像、sex 詞彙常數;result `data` 鏡像屬前置 change,不動)、`creation_menu.js`(draft/payload/擲名 payload)、`web/webclient-app/components/CreationOverlay.vue`(性別 select、🎲 按鈕、回填)、`web/webclient-app/tests/overlays/creation_overlay.test.js`、`web/webclient-app/stories/Overlays/CreationOverlay.stories.js`(stores/elosern.js 的 `data` 透傳屬前置 change,不動)
- 契約面遷移(硬 cutover 的既有代價):`web/webclient-app/stories/fixtures.js` 與 `web/webclient-app/tests/preserved_contract.test.js` 的 creation panel 樣板升 v4 帶 `custom.sex`;`tests/test_creation_parity_contract.py` 版本釘選 3→4 並新增 sex 詞彙雙端對照;`web/webclient/tests/test_vue_showcase_overlays_evidence.py` frozen story id 集合加入新 story;`command_echo.js`/`command_echo_coverage_manifest.json`/`command_echo.test.js`/`command_echo_surfaces.test.js` 登記 silent 擲名控制
- 測試:`world/rules/tests/test_character_creation.py`、`world/rules/tests/test_creation_wizard.py`、`web/webclient/presentation/tests/test_creation_panel.py`、`web/webclient/actions/tests/test_creation_actions.py`、JS `node --test`(`protocol.test.js`、`creation_menu.test.js`、`command_echo.test.js`)
- 不動:`docs/game/commands.md`(`creation.roll_name` 是 UI action 不是玩家命令,判斷記錄於 design.md)、`character-creation-ux`(Telnet 精靈不收集 sex,預設走 `DEFAULT_SEX`,語意不變)、`.github/evennia-shards.json`(全部測試落點皆已登記)
