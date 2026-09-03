# namegen-creation-ui — Tasks

前提:上游 `npc-namegen-lore-registry`、`npc-namegen-rules-roller`(`world/rules/namegen.py` 可 import)與 `oob-result-data-slot`(`ui_action_result` 的 success 條件性 `data` 槽:emitter、雙端驗證、store 透傳已落地且其 focused 測試已綠)已實作。本 change 無協議層工作包——`dispatcher.py`、`presentation/protocol.py`、JS `validateActionResult`、`stores/elosern.js` 一行不動,只消費既定 envelope。全程無相容層:panel v3 payload 與 draft v2 由版本閘門直接拒絕,不寫遷移。每項測試只跑列出的模組,不跑全場。

## D1 — 規則層:sex 進 request / preflight / activation

- [ ] `world/rules/character_creation.py`:`CharacterCreationRequest` 尾位加 `sex: str | None = None`;新增 `_validate_sex(value)`(None/缺 → `DEFAULT_SEX`;`SEX_VALUES` 成員 → 原值;其他 → 穩定 `CreationError`);`_preflight` 呼叫並把歸一值放進 `_ValidatedCreation.sex`;`activate_player_character` 寫 `attribute_values["sex"] = validated.sex`;`_CREATION_ATTRIBUTE_KEYS` 加 `"sex"`(rollback 快照覆蓋)。
- [ ] 測 `world/rules/tests/test_character_creation.py`:custom 帶 `sex="female"` 激活後 `entity.sex == "female"`;缺 sex / null sex → `entity.sex == DEFAULT_SEX`;`sex="x"` → preflight 穩定拒絕且 entity 無寫入;preset 激活 → `entity.sex == DEFAULT_SEX`;注入激活交易失敗 → `sex` 一併回滾。
- [ ] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation`

## D2 — 規則層:creation_wizard 表單 view + 草稿帶 sex(DRAFT_VERSION 3)

- [ ] `world/rules/creation_wizard.py`:`CustomFormView` 加 `sex: tuple[SexOption, ...]`(`{key,label}` dataclass 或既有同形);模組級 `_SEX_LABELS = {"female": "女性", "male": "男性", "other": "其他"}` 由 `SEX_VALUES` 序派生進 `build_custom_form()`;`DRAFT_VERSION` 2→3;custom 草稿形狀加必填 `sex`(存歸一後的具體成員),`_normalize_draft` 驗證 `sex ∈ SEX_VALUES`,缺鍵(舊 v2 形)因版本閘門自然出局;`_request_from_draft` 帶 `sex`;draft 序列化/還原鏡像。
- [ ] 測 `world/rules/tests/test_creation_wizard.py`:form 描述元含 `custom.sex` 三項(key/label/序);保存缺 sex 的 payload → 草稿存 `DEFAULT_SEX`;`sex="male"` 往返(reload 後仍在);`sex="nope"` → 穩定拒絕且舊草稿不變;存 v2 草稿/version 欄為 2 → 載入視為無草稿。
- [ ] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_wizard`

## D3 — presentation:panel v4 + wire 驗證

- [ ] `web/webclient/presentation/creation.py`:`CREATION_SCHEMA_VERSION` 3→4;available payload 構造把 `CustomFormView.sex` 送進 `custom.sex`;wire/panel 驗證器(`_validate_draft` custom 分支、panel 深驗)加 `sex` 鍵(草稿必填成員;缺/超界拒)。
- [ ] 測 `web/webclient/presentation/tests/test_creation_panel.py`:panel `schema_version == 4`;`custom.sex` 恰三項、標籤為女性/男性/其他、每項恰 `{key,label}`、≤8 界;含 sex 草稿往返;缺 sex 的 draft payload 被鏡像驗證拒;舊 v3 payload 被版本閘門拒。
- [ ] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel`

## D4 — actions:custom sex + `creation.roll_name` adapter + registry

- [ ] `web/webclient/actions/creation_actions.py`:`_validate_custom_payload` 鍵集合加選填 `sex`(null 或 `SEX_VALUES` 成員;其他拒),custom adapter 透傳 `sex=payload.get("sex")`;新增 roll_name adapter:payload 恰 `{race, subrace, sex}` 過結構界(1..64 識別字)後做**語意驗證**——`race` null 或 `RACE_REGISTRY` 成員、`subrace` null 或 `SUBRACE_REGISTRY[subrace].race_key == race`(race null 時 subrace 必 null)、`sex` null 或 `SEX_VALUES` 成員;任何表外值 → 穩定 `rejected` code 走既有 validation error 通道、roller 零觸及、**不兜底成功**;通過驗證 → 呼叫 `roll_name_for_race(race, sex, _ROLL_NAME_RNG)`(module 層級唯一私有 `_ROLL_NAME_RNG = random.Random()`,只在 roll 路徑讀取)回 `{"outcome": "success", "data": {"display_name": name}}`(零持久寫、不刷 panel)。
- [ ] `web/webclient/actions/registry.py`:`build_production_registry` 註冊 `creation.roll_name`(與既有 creation 五項同組)。
- [ ] 測 `web/webclient/actions/tests/test_creation_actions.py`:`creation.custom` 帶 `sex="female"` roundtrip(草稿含歸一 sex)、缺 sex → 草稿 `DEFAULT_SEX`、`sex` 為鍵集合內但髒值 → 結構拒且無寫入;`creation.roll_name` 有效 payload(race+subrace 同族、sex 成員)→ success 且 result `data.display_name` 非空、前後 `db` 快照 byte 相同、無 panel 刷;**語意驗證矩陣(全部 rejected 且 roller 零觸及,monkeypatch 計數)**:表外 race(`"dragonborn"`)、跨族 subrace、表外 subrace、null race+非 null subrace、髒 sex;結構面:額外鍵 / 超界 → 穩定 code;`race: null`+`subrace: null` → success,且斷言結果名的 given／surname 零件恆落 `fantasy-human`／`fantasy-elf`／`fantasy-orc` 三包零件集(`fantasy-dwarf`／`fantasy-halfling` 獨有零件從不出現);斷言 roll 路徑讀 `_ROLL_NAME_RNG` 且模組無其他 `random.Random()` 實例化點。
- [ ] 驗證:`uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_creation_actions`

## D5 — JS 純邏輯 + 協議鏡像(protocol.js / creation_menu.js)

- [ ] `web/static/webclient/js/elosern/protocol.js`:`CREATION_SCHEMA_VERSION` 3→4;`custom` 驗證加 `sex`(1..8 項、恰 `{key,label}`、1..64 cp);`creation.custom` payload 驗證加選填 `sex`(null 或成員);`validateUiMessage` action 表加 `creation.roll_name` = 恰 `{race, subrace, sex}`(null 或 1..64 識別字;sex null 或成員)。result `data` 鏡像(`validateActionResult`)已由前置 change 落地,不動。
- [ ] `web/static/webclient/js/elosern/creation_menu.js`:`customPayload()` 加 `sex`(狀態有選 → 帶鍵;未選/預設 → 不帶,由伺服器歸一);`stateFromDraft` 讀 `draft.sex`;新增 `rollNamePayload(state)` 純函數造 `{race, subrace, sex}`(未選 Race → null)。
- [ ] 測 `web/static/webclient/js/tests/protocol.test.js`、`creation_menu.test.js`、`ui_contract.test.js`:v4 面板驗證通過/v3 拒;`custom.sex` 界;`creation.roll_name` payload 驗證表(恰三鍵、null/識別字形、髒 sex 拒);`customPayload` sex 變體;`rollNamePayload` 缺 race → null。
- [ ] 驗證:`node --test web/static/webclient/js/tests/*.test.js`

## D6 — Vue:性別下拉、🎲 按鈕、回填

- [ ] `web/webclient-app/components/CreationOverlay.vue`:姓名 input 右側 🎲 按鈕 `data-testid="creation-roll-name"`(aria-label「擲名」);姓名欄下方 `<select data-testid="creation-sex">` 選項逐字讀 `custom.sex`(無前端標籤字面量;fresh 表單預選比對 `DEFAULT_SEX` key — 由後端草稿歸一保證);點擊 🎲 → `rollNamePayload` → dispatch `creation.roll_name`,記 `submittedRequestId`;watch store 最新 result(store 的 `data` 透傳已由前置 change 落地),`requestId` 配對 + `outcome==="success"` + `data.display_name` → 回填 `name`;在飛期間按鈕 disabled(沿既有單在飛閘門)。
- [ ] `web/webclient-app/lib/protocol.js` re-export 不需動(純再匯出)。
- [ ] 測 `web/webclient-app/tests/overlays/creation_overlay.test.js`(Vitest):下拉選項等於 panel `custom.sex`;選 sex 後 `creation.custom` payload 帶鍵;未選不帶;點 🎲 → dispatch `creation.roll_name` 恰 payload;success(result 帶配對 requestId+`data.display_name`)→ name 欄回填、按鈕恢復;非 success / 錯 requestId → 不回填只結算;在飛時第二次點擊不重複 dispatch。
- [ ] `web/webclient-app/stories/Overlays/CreationOverlay.stories.js`:加「自訂表單(含性別與擲名)」story(現有 mock panel 升 v4 帶 `custom.sex`,result 回填態可講)。
- [ ] 驗證:`npm test`(webclient-app Vitest 篩 `creation_overlay`)、`npm run showcase-coverage`

## D7 — 端到端與收尾

- [ ] 後端全鏈 roundtrip 測(落 `test_creation_actions.py` 或既有 dispatcher 集成測):`creation.roll_name` 經真實 dispatcher → `ui_action_result` 線上傳輸含 `data` 且過 `validate_ui_action_result`(消費前置 change 已交付的槽,斷言往返即證接線正確);`creation.custom`(sex)→ 草稿 → `creation.activate` → `entity.sex` 落地 → 草稿清除。
- [ ] `tools.spec_traceability list` / `check`(沿用上游 change 流程)確認新 requirement 符號(`SEX_VALUES`、`DEFAULT_SEX`、`roll_name_for_race`、`creation.roll_name`、`creation-roll-name`、result `data` 槽消費)可追溯;確認 `.github/evennia-shards.json` 無需變動(D1–D4 測試全落已登記模組)。
- [ ] 確認 `docs/game/commands.md` 與 `character-creation-ux` 未動(design D8 判斷);Playwright 創建journey 測若既有斷言 panel 欄位集合,同步 sex select/🎲 按鈕的鍵盤可達性(Tab 序:姓名 → 🎲 → 性別)。
- [ ] 驗證(一次性):`uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation world.rules.tests.test_creation_wizard web.webclient.actions.tests.test_creation_actions web.webclient.presentation.tests.test_creation_panel`;`node --test web/static/webclient/js/tests/*.test.js`;`npm test`;`npm run showcase-coverage`。
