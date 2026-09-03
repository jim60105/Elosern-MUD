# namegen-creation-ui — Tasks

前提:上游 `npc-namegen-lore-registry`、`npc-namegen-rules-roller`(`world/rules/namegen.py` 可 import)與 `oob-result-data-slot`(`ui_action_result` 的 success 條件性 `data` 槽:emitter、雙端驗證、store 透傳已落地且其 focused 測試已綠)已實作。本 change 無協議層工作包——`presentation/protocol.py`、JS `validateActionResult`、`stores/elosern.js` 一行不動,只消費既定 envelope;`dispatcher.py` 僅新增 D10 的內部 `no_presentation` 完成分支(不變任何上線訊息形狀)。另:新註冊 action 必須同步 command-echo 覆蓋 manifest 三處消費端(D7)。全程無相容層:panel v3 payload 與 draft v2 由版本閘門直接拒絕,不寫遷移。每項測試只跑列出的模組,不跑全場。

## D1 — 規則層:sex 進 request / preflight / activation

- [x] `world/rules/character_creation.py`:`CharacterCreationRequest` 尾位加 `sex: str | None = None`;新增 `_validate_sex(value)`(None/缺 → `DEFAULT_SEX`;`SEX_VALUES` 成員 → 原值;其他 → 穩定 `CreationError`);`_preflight` 呼叫並把歸一值放進 `_ValidatedCreation.sex`;`activate_player_character` 寫 `attribute_values["sex"] = validated.sex`;`_CREATION_ATTRIBUTE_KEYS` 加 `"sex"`(rollback 快照覆蓋)。
- [x] 測 `world/rules/tests/test_character_creation.py`:custom 帶 `sex="female"` 激活後 `entity.sex == "female"`;缺 sex / null sex → `entity.sex == DEFAULT_SEX`;`sex="x"` → preflight 穩定拒絕且 entity 無寫入;preset 激活 → `entity.sex == DEFAULT_SEX`;注入激活交易失敗 → `sex` 一併回滾。
- [x] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation`

## D2 — 規則層:creation_wizard 表單 view + 草稿帶 sex(DRAFT_VERSION 3)

- [x] `world/rules/creation_wizard.py`:`CustomFormView` 加 `sex: tuple[SexOption, ...]`(`{key,label}` dataclass 或既有同形);模組級 `_SEX_LABELS = {"female": "女性", "male": "男性", "other": "其他"}` 由 `SEX_VALUES` 序派生進 `build_custom_form()`;`DRAFT_VERSION` 2→3;custom 草稿形狀加必填 `sex`(存歸一後的具體成員),`_normalize_draft` 驗證 `sex ∈ SEX_VALUES`,缺鍵(舊 v2 形)因版本閘門自然出局;`_request_from_draft` 帶 `sex`;draft 序列化/還原鏡像。
- [x] 測 `world/rules/tests/test_creation_wizard.py`:form 描述元含 `custom.sex` 三項(key/label/序);保存缺 sex 的 payload → 草稿存 `DEFAULT_SEX`;`sex="male"` 往返(reload 後仍在);`sex="nope"` → 穩定拒絕且舊草稿不變;存 v2 草稿/version 欄為 2 → 載入視為無草稿。
- [x] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_wizard`

## D3 — presentation:panel v4 + wire 驗證

- [x] `web/webclient/presentation/creation.py`:`CREATION_SCHEMA_VERSION` 3→4;available payload 構造把 `CustomFormView.sex` 送進 `custom.sex`;wire/panel 驗證器(`_validate_draft` custom 分支、panel 深驗)加 `sex` 鍵(草稿必填成員;缺/超界拒)。
- [x] 測 `web/webclient/presentation/tests/test_creation_panel.py`:panel `schema_version == 4`;`custom.sex` 恰三項、標籤為女性/男性/其他、每項恰 `{key,label}`、≤8 界;含 sex 草稿往返;缺 sex 的 draft payload 被鏡像驗證拒;舊 v3 payload 被版本閘門拒。
- [x] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel`

## D4 — actions:custom sex + `creation.roll_name` adapter + registry

- [x] `web/webclient/actions/creation_actions.py`:`validate_creation_custom_payload` 鍵集合加選填 `sex`(結構層:缺鍵 / null / 1..64 字串;成員資格不查——非成員字串由規則層 `_validate_sex` 以 `unknown_sex` 在 preflight 拒絕、零寫入,比照 `age` 慣例,design D2/R2 修訂),custom adapter 透傳 `sex=payload.get("sex")`(缺鍵 → None);新增 roll_name adapter:payload 恰 `{race, subrace, sex}` 過結構界(1..64 識別字)後做**語意驗證**——`race` null 或 `RACE_REGISTRY` 成員、`subrace` null 或 `SUBRACE_REGISTRY[subrace].race_key == race`(race null 時 subrace 必 null)、`sex` null 或 `SEX_VALUES` 成員;任何表外值 → 穩定 `rejected` code 走既有 validation error 通道、roller 零觸及、**不兜底成功**;通過驗證 → 呼叫 `roll_name_for_race(race, sex, _ROLL_NAME_RNG)`(module 層級唯一私有 `_ROLL_NAME_RNG = random.Random()`,只在 roll 路徑讀取)回 `{"outcome": "success", "code": "name_rolled", "message": <zh>, "data": {"display_name": name}, "no_presentation": True}`(零持久寫、不刷 panel;語意拒絕與 ownership 拒絕同樣帶 `no_presentation`)。
- [x] `web/webclient/actions/registry.py`:`build_production_registry` 註冊 `creation.roll_name`(與既有 creation 五項同組)。
- [x] 測 `web/webclient/actions/tests/test_creation_actions.py`:`creation.custom` 帶 `sex="female"` roundtrip(草稿含歸一 sex)、缺 sex → 草稿 `DEFAULT_SEX`、`sex` 為鍵集合內但非成員值 → 規則層 `unknown_sex` 穩定拒且無寫入(design D2 修訂);`creation.roll_name` 有效 payload(race+subrace 同族、sex 成員)→ success 且 result `data.display_name` 非空、前後 `db` 快照 byte 相同、無 panel 刷;**語意驗證矩陣(全部 rejected 且 roller 零觸及,monkeypatch 計數)**:表外 race(`"dragonborn"`)、跨族 subrace、表外 subrace、null race+非 null subrace、髒 sex;結構面:額外鍵 / 超界 → 穩定 code;`race: null`+`subrace: null` → success,且斷言結果名的 given／surname 零件恆落 `fantasy-human`／`fantasy-elf`／`fantasy-orc` 三包零件集(`fantasy-dwarf`／`fantasy-halfling` 獨有零件從不出現);以 monkeypatch `roll_name_for_race` seam 記錄 rng 識體,連續兩次 roll 斷言恆為同一 `_ROLL_NAME_RNG` 物件(行為證明,不做來源文字掃描)。
- [x] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_creation_actions`

## D5 — JS 純邏輯 + 協議鏡像(protocol.js / creation_menu.js)

- [x] `web/static/webclient/js/elosern/protocol.js`:`CREATION_SCHEMA_VERSION` 3→4;`PANEL_ALLOWLIST.creation` 3→4;`custom` 驗證加 `sex`(1..8 項、恰 `{key,label}`、1..64 cp、keys 恰 `SEX_VALUES` 序);`validateCreationDraft` custom 分支加必填 `sex ∈ SEX_VALUES`;匯出 `CREATION_SEX_VALUES`/`CREATION_SEX_DEFAULT` 鏡像常數。出站 action payload 無客戶端驗證表——原稿的 `validateUiMessage` 表經研究確認不存在(JS 只驗證入站訊息;roll_name payload 由伺服端 registry 驗證),該項作廢(design R1/D6)。result `data` 鏡像(`validateActionResult`)已由前置 change 落地,不動。
- [x] `web/static/webclient/js/elosern/creation_menu.js`:`DEFAULT_SEX_KEY` 鏡像常數;`defaultCustomState().sexKey = DEFAULT_SEX_KEY`(D11);`customPayload()` 加 `sex`(sexKey 為預設 → 不帶鍵,由伺服器歸一;非預設 → 帶鍵);`stateFromDraft` 讀 `draft.sex || DEFAULT_SEX_KEY`;新增 `rollNamePayload(state)` 純函數造 `{race, subrace, sex}`(未選 Race → null;sex 恆為顯示選中 key)。
- [x] 測 `web/static/webclient/js/tests/protocol.test.js`、`creation_menu.test.js`:v4 面板驗證通過/v3 拒(既有 creation 樣板升 v4 帶 `custom.sex`);`custom.sex` 界;draft `sex` 必填/髒值拒;`customPayload` sex 變體(預設不帶鍵、非預設帶);`rollNamePayload` 缺 race → null、新表單 sex → 預設 key。
- [x] 契約樣板遷移:`web/webclient-app/stories/fixtures.js` 的 creation panel 樣板(含 custom draft 樣板)升 v4 帶 `custom.sex` 三選項;`web/webclient-app/tests/preserved_contract.test.js` 的 `creationPanel()` 同步升 v4(其消费測試如 app_client_toast/action_result_feedback/declarative_surfaces 依賴此樣板)。
- [x] 驗證:`node --test web/static/webclient/js/tests/*.test.js`

## D6 — Vue:性別下拉、🎲 按鈕、回填

- [x] `web/webclient-app/components/CreationOverlay.vue`:姓名 input 右側 🎲 按鈕 `data-testid="creation-roll-name"`(aria-label「擲名」);姓名欄下方 `<select data-testid="creation-sex">` 選項逐字讀 `custom.sex`(無前端標籤字面量);模型 `sex = ref(SEX_DEFAULT_KEY)`(鏡像常數,比照 `ACTION_RESULT_FALLBACK_MESSAGE` byte-identical 釘選先例;`syncFromDraft` 讀 `d.sex ?? SEX_DEFAULT_KEY`——可見選中項、roll payload、custom 省略判斷三者同源,D11);點擊 🎲 → 造 `{race, subrace, sex}` → 以 concept 同款 admitted-dispatch 模式 dispatch `creation.roll_name`,記 `submittedRequestId`;watch store 最新 result(store 的 `data` 透傳已由前置 change 落地),`requestId` 配對 + `outcome==="success"` + `data.display_name` → 回填 `name`;非 success/錯 id 只結算在飛態;在飛期間按鈕 disabled(沿既有單在飛閘門)。
- [x] `web/webclient-app/lib/protocol.js` re-export 不需動(純再匯出)。
- [x] 測 `web/webclient-app/tests/overlays/creation_overlay.test.js`(Vitest):下拉選項等於 panel `custom.sex`;選 sex 後 `creation.custom` payload 帶鍵;未選不帶;點 🎲 → dispatch `creation.roll_name` 恰 payload;success(result 帶配對 requestId+`data.display_name`)→ name 欄回填、按鈕恢復;非 success / 錯 requestId → 不回填只結算;在飛時第二次點擊不重複 dispatch。
- [x] `web/webclient-app/stories/Overlays/CreationOverlay.stories.js`:加「自訂表單(含性別與擲名)」story(現有 mock panel 升 v4 帶 `custom.sex`,result 回填態可講)。
- [x] 驗證:`npm test`(webclient-app Vitest 篩 `creation_overlay`)、`npm run showcase-coverage`

## D7 — 端到端與收尾

- [x] echo 目錄登記:`creation.roll_name` 加入 `web/static/webclient/js/elosern/command_echo.js` 的 `SILENT_PRESENTATION_CONTROLS`、`web/static/webclient/js/tests/command_echo_coverage_manifest.json` 的 `registeredMutationActionIds` + `silentPresentationControlIds`、`command_echo.test.js` 的 `REGISTERED_MUTATION_ACTIONS`(null 表 silent + 顯式 silent 斷言)、`web/webclient-app/tests/store/command_echo_surfaces.test.js` 依 options.dismiss 先例加 expected-silence 表面列(以真實 payload dispatch)。`web/webclient/actions/tests/test_action_catalog_coverage.py` 的 registry==manifest 釘選自然通過。
- [x] 雙端釘選:`tests/test_creation_parity_contract.py` 的 `creation: 3`/版本相等釘選升 4;新增 sex 詞彙對照測試(正則讀 `protocol.js` 的 `CREATION_SEX_VALUES`/`CREATION_SEX_DEFAULT` 與 `creation_menu.js` 的 `DEFAULT_SEX_KEY`,逐字對照 `world/lore/sex.py`)。
- [x] showcase 釘選:`web/webclient/tests/test_vue_showcase_overlays_evidence.py` 的 `OVERLAYS_STORY_IDS` 加入新 story id(與 D6 匯出名一致)。
- [x] 後端全鏈 roundtrip 測(落 `test_creation_actions.py` 或既有 dispatcher 集成測):`creation.roll_name` 經真實 dispatcher → `ui_action_result` 線上傳輸含 `data` 且過 `validate_ui_action_result`(消費前置 change 已交付的槽,斷言往返即證接線正確),並斷言該請求從 admitted 到結果之間傳輸捕捉幀中無任何 `ui_snapshot`/`ui_update`(D10 通道生效的線上證據);`creation.custom`(sex)→ 草稿 → `creation.activate` → `entity.sex` 落地 → 草稿清除。
- [x] `tools.spec_traceability list` / `check`(沿用上游 change 流程)確認新 requirement 符號(`SEX_VALUES`、`DEFAULT_SEX`、`roll_name_for_race`、`creation.roll_name`、`creation-roll-name`、result `data` 槽消費)可追溯;確認 `.github/evennia-shards.json` 無需變動(D1–D4 測試全落已登記模組)。
- [x] 確認 `docs/game/commands.md` 與 `character-creation-ux` 未動(design D8 判斷);Playwright 創建journey 測若既有斷言 panel 欄位集合,同步 sex select/🎲 按鈕的鍵盤可達性(Tab 序:姓名 → 🎲 → 性別)。
- [x] 驗證(一次性):`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation world.rules.tests.test_creation_wizard web.webclient.actions.tests.test_creation_actions web.webclient.actions.tests.test_action_catalog_coverage web.webclient.presentation.tests.test_creation_panel tests.test_creation_parity_contract`;`node --test web/static/webclient/js/tests/*.test.js`;`npm test`;`npm run showcase-coverage`。
