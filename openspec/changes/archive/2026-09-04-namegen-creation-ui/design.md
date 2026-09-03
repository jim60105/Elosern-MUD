# namegen-creation-ui — Design

## Context

上游三個 change 已定型:`npc-namegen-lore-registry`(`NAME_PACK_REGISTRY`、`NamePack.race_key`)、`npc-namegen-rules-roller`(`world/rules/namegen.py` 的 `roll_name_for_race(race_key, sex, rng) -> str`:race_key 有綁定 → 經 `NAME_PACK_BY_RACE` 取包;race_key 為 `None` 或未對照 → 從規則層 `sorted(NAME_PACK_BY_RACE.values())` 的已綁定包清單(human／elf／orc 三包;dwarf／halfling 不在映射值、永不參與)隨機挑一;sex `female`→f 池、`male`→m 池、`other`→u 池、表外值 → 隨機池;永不拋錯;回傳名恆 ≤64 code points 且過 `_validate_name`)、以及 `oob-result-data-slot`(`ui_action_result` 的 success 條件性 `data` 槽:emitter 透傳、伺服器／JS 雙端鏡像驗證、store 透傳)。本 change 實作設計文件 §5「角色創建 UI 接線」:panel 送 sex 選項、`creation.custom`/草稿/request/activation 帶 sex、`creation.roll_name` UI action、前端性別下拉與 🎲 回填;對 envelope 層**只消費不擴充**。系統未發布、零使用者 → 全套無相容層(cutover 一次到位,舊 v3 payload/舊 v2 草稿由版本閘門直接拒絕)。

現狀關鍵事實(已驗證):

- `world/lore/sex.py`:`SEX_VALUES = ("female", "male", "other")`、`DEFAULT_SEX = "other"`;`LivingEntity.sex` 是 AttributeProperty(預設 other);`world/imports/loader.py` 匯入時已寫 `entity.sex`,創建側沒有對應寫入。
- `CREATION_SCHEMA_VERSION = 3`(panel),JS 鏡像 `protocol.js` 同值;draft `DRAFT_VERSION = 2`;`creation.custom` wire payload 恰 9 鍵(`_validate_custom_payload`),`_normalize_draft` 逐鍵驗證。
- `ui_action_result` envelope 的原始形態是 exact 七鍵(+ error 時的 `correlation_id`):`_send_action_result` 構造、`presentation/protocol.py::validate_ui_action_result` 伺服器端驗證、`protocol.js::validateActionResult` 鏡像,三處同步。success 條件性 `data` 槽由前置 change `oob-result-data-slot` 在這三處落地——本 change 動工時該槽已存在且其 focused 測試(「A success result may carry an adapter data slot」等 scenario)已綠,本 change 只做消費端斷言。
- roll_name 語意驗證需要的兩個 registry:`world/lore/races.py` 的 `RACE_REGISTRY`(dict,key 為種族鍵)與 `SUBRACE_REGISTRY`(dict,`Subrace.race_key` 標明歸屬);`creation.custom` 的既有 preflight 已用同一對 registry 做 race/subrace 相容檢查,roll_name adapter 的語意驗證沿用同源常量。
- `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5 是契約來源:§5.1 性別下拉(選項讀自 panel `custom.sex`、後端送中文標籤、前端不寫死;規則層驗證 sex 為 `SEX_VALUES` 成員或 None,None→`DEFAULT_SEX`,寫入 entity,補齊 loader/創建缺口);§5.2 骰子按鈕(🎲 在姓名 input 右側、`data-testid="creation-roll-name"`、payload `{race, subrace, sex}`、經既有 `ui_action` 通道、結果帶 `{display_name}` 回填、語料零進前端、玩家可手動改寫);§8 錯誤表:無效 race/sex → 走既有驗證錯誤通道。

## Goals / Non-Goals

**Goals**

1. `custom` panel 描述元有 `sex` 選項欄(`SEX_VALUES` 派生 + 後端中文標籤),schema v4。
2. sex 全鏈路:`creation.custom` payload(選填)→ preflight 驗證/歸一 → 草稿持久化/還原 → activation 寫 `entity.sex`。
3. `creation.roll_name` UI action:exact payload + 語意驗證(null 或 registry 成員,表外值拒絕不兜底)、零持久寫、經 `ui_action_result` 回 `display_name`,前端回填姓名欄。
4. 作為 `oob-result-data-slot` 已交付 `data` 槽的第一個消費者,以端到端測證明 success 結果攜槽往返不破壞既有結果流(槽的雙端鏡像驗證本身屬前置 change,不在本 change 工作包)。
5. 後端 Evennia 測試、JS node --test、Vitest/Storybook/showcase 覆蓋全部新契約。

**Non-Goals**

- NPC 生成流接線(設計 §6,屬後續 change)。
- result envelope `data` 槽的擴充本身(`_normalize_result` 的欄位集、`_send_action_result` 的 envelope 構造、`validate_ui_action_result`、JS `validateActionResult`、store 透傳)——屬前置 change `oob-result-data-slot`,本 change 不動。唯一例外是 D10 的 dispatcher 完成通道分支:它只讀取 adapter 傳回的內部旗標,不改變任何上線訊息形狀。
- Telnet 創建精靈加 sex 提示(`character-creation-ux` 不動;Telnet 流不收集 sex,activation 走 `DEFAULT_SEX`)。
- 擲名歷史、重擲冷卻、語料前端可見性(語料零進前端)。
- preset 模式的 sex 自訂(preset 目錄無 sex 欄,preset 激活恆 `DEFAULT_SEX`)。

## Decisions

### D1 — 只消費 `oob-result-data-slot` 交付的條件性 `data` 槽

設計文件 §5.2 明文「回 `ui_action_result` 帶 `{"display_name": ...}`」。envelope 擴充(success 條件性 `data` 槽,≤8 鍵、鍵 1..64 識別字、值 JSON-safe 沿全域界;emitter 透傳 + 雙端鏡像驗證 + store 透傳)已由前置 change `oob-result-data-slot` 定案並落地。原「在本 change 內直接改 `webclient-oob-protocol`」的方案因工作包超額(協議層 + 消費端疊加超過單一工程師 8 小時)且把通用協議能力鎖死在單一消費端而拆出;原拒絕方案(session ndb slot + panel 快照、借 `message` 塞 JSON、`ui_update` panel-only 刷)的評理記錄見該 change 的 design D1。本 change 的邊界:roll_name adapter 回 `{"outcome": "success", "data": {"display_name": name}}` 走既有 `_normalize_result` 路徑;前端 watch store 已透傳的 result `data`;端到端測斷言攜槽結果線上往返(消費端證據),槽的 accept/reject 矩陣測留在前置 change。

### D2 — sex 形態:wire 選填可 null,入站即歸一,draft/activation 恆為具體成員

`creation.custom` payload 的 `sex` 為選填鍵:`sex ∈ SEX_VALUES` 或缺鍵/null → 歸一為 `DEFAULT_SEX`(同 `background` 缺鍵→空的既有慣例)。邊界(2026-09-03 修訂,依 delta spec「A custom submission with an unknown sex is rejected」scenario 與 `age` 既有慣例):結構層只收缺鍵 / null / 1..64 字串,不做成員資格檢查;非成員字串放行到規則層,由 `_validate_sex` 以穩定代碼 `unknown_sex` 在 preflight 拒絕(零寫入)。`_normalize_draft` 的 custom 形狀存**歸一後的具體成員值**(required key、值必為 `SEX_VALUES` 成員)——「draft 存伺服器接受的原值」,還原路徑不需再歸一。`CharacterCreationRequest` 加尾位 `sex: str | None = None`(Telnet 精靈構造不帶 sex → 預設 None → 同樣歸一);`_ValidatedCreation` 帶具體 `sex`;activation 寫 `attribute_values["sex"] = validated.sex`,`_CREATION_ATTRIBUTE_KEYS` 加 `"sex"` 進 rollback 快照。preset 模式不收集 sex,激活恆寫 `DEFAULT_SEX`。
(Telnet 語意不變:設計 §5.1 只要求規則層接受 None→DEFAULT_SEX;entity 預設本就是 other,寫入具體值使創建與 loader 行為對稱。)

### D3 — `DRAFT_VERSION` 2→3,cutover 不遷移

sex 進 draft 形狀後,舊 v2 draft 缺 `sex` 鍵會被 `_normalize_draft` 拒。系統未發布零使用者 → `DRAFT_VERSION` 直接 2→3,加載端既有「版本不符 → 視為無草稿」路徑自然處置殘留 v2,不寫遷移器。`CREATION_SCHEMA_VERSION` 3→4 同步(雙端鏡像、unavailable 表單自動跟隨註冊常量)。

### D4 — `custom.sex` 描述元形狀:≤8 個 `{key,label}`,派生自 `SEX_VALUES`

`build_custom_form()` 加 `sex: tuple[{key,label}, ...]`,由 `SEX_VALUES` 序 + 伺服器標籤表(`female→女性`、`male→男性`、`other→其他`)派生;標籤住在 `world/rules/creation_wizard.py`(設計:「由 panel view 送出,前端不寫死」)。綁定:每 key/label 1..64 code points,列表 ≤8、非空。前端 `<select>` 選項順序即此列表順序,預設選中 `DEFAULT_SEX` 對應項(比較 key,不比標籤)。

### D5 — `creation.roll_name` adapter 契約

- payload 恰 `{race, subrace, sex}` 三鍵,每鍵 null 或有值;通過結構界(1..64 識別字等)後再做**語意驗證**,任何一項不合格 → 穩定 `rejected` code 走既有 validation error 通道(`ui_action_result` 的 rejected 結果),**絕不兜底成功**:
  - `race`:null 或 `RACE_REGISTRY` 成員。表外種族鍵(如 `"dragonborn"`)是髒輸入,直接拒絕——roll_name 是 UI 入口,輸入源是 panel 的有限 `races` 列表,不該出現 registry 外的值;規則層「未對照走隨機包」的兜底只服務**真實未選種族**(`race: null` → `roll_name_for_race(None, …)`)與 NPC 側原型缺族情境,不是 UI 髒值的免死金牌。
  - `subrace`:null,或**屬該 race** 的 `SUBRACE_REGISTRY` 成員(`SUBRACE_REGISTRY[subrace].race_key == race`);`race` 為 null 時 `subrace` 必須 null(髒組合)。跨族 subrace、表外 subrace → 同級拒絕。
  - `sex`:null 或 `SEX_VALUES` 成員;表外字串 → 同級拒絕(規則層 roll 對表外 sex 隨機兜底,但 UI 入口收緊,避免下拉以外的髒值)。
- 擲名用**未種子化 `random.Random()`**,依設計 §4 原文「模組級無種子 `random.Random()`」定案為:`creation_actions.py` module 層級唯一的私有執行個體 `_ROLL_NAME_RNG = random.Random()`,**只在 `creation.roll_name` 的 roll 路徑讀取**(其他 action 零觸及)。設計 §4 的「模組級」是與 NPC 側「呼叫端自建種子執行個體」相對的語意(UI 骰不需要重放,故無種子;每次呼叫新建執行個體屬實作自由、非契約要求,且高頻 `time` 種子下相鄰呼叫間隔可能小於時鐘解析度)。單一私有執行個體把無種子 randomness 的 blast radius 鎖在一條 action 路徑,同時避免每次呼叫構造執行個體。
- 零持久寫、不刷 panel、不動草稿:result-only。`success` + `data: {display_name}`;名稱恆過 `_validate_name`(roller 保證 ≤64 + 界內字元)。
- 經既有 dispatcher 全部閘門(epoch/base_revision/in-flight/request-id/puppet 所有權 + `creation_pending`),註冊進 `build_production_registry`。

### D6 — 前端:性別下拉、🎲 按鈕、request-id 配對回填

`CreationOverlay.vue` 姓名 `<input>` 右側 🎲 按鈕(`data-testid="creation-roll-name"`,同層 aria-label 中文「擲名」),姓名欄**下方**性別 `<select>`(`data-testid="creation-sex"`):
- 按鈕點按 → `creation_menu.js` 純邏輯 `rollNamePayload(state)` 造 `{race, subrace, sex}`(未選 Race → 該鍵 null)→ dispatch `creation.roll_name`;沿用既有單在飛閘門(在飛期間按鈕與提交閘門同形禁用)。
- 結果收斂同概念流模式:watch store 最新 `ui_action_result`,僅 `requestId === submittedRequestId` 且 `outcome === "success"` 且帶 `data.display_name` 時回填 `name` 輸入框;非 success/錯 id 只結算在飛態不改欄。回填後玩家可手動改寫;最終仍由 `creation.custom` 經 `_validate_name` 為準。
- `creation_menu.js`:`customPayload()` 加 `sex`(sexKey 為鏡像預設或 null → 不帶鍵,靠伺服器歸一;選了非預設就帶);`defaultCustomState()` 的 `sexKey` 初始化為鏡像常數 `DEFAULT_SEX_KEY`(D11);draft→state 還原讀 `draft.sex`;`rollNamePayload(state)` 純函數進 UMD(可 node --test),恆送目前顯示選中的 key(新表單即預設 key,與可見選中項一致)。
- `protocol.js`:`CREATION_SCHEMA_VERSION = 4`;`PANEL_ALLOWLIST.creation = 4`;`custom` 驗證加 `sex` 欄(≤8 項 `{key,label}`);`validateCreationDraft` custom 分支加必填 `sex ∈ SEX_VALUES`;匯出 `CREATION_SEX_VALUES`/`CREATION_SEX_DEFAULT` 鏡像常數(僅 key、不含標籤,由 `tests/test_creation_parity_contract.py` 雙端釘選)。出站 `ui_action` payload 無客戶端驗證表(研究發現:原稿引用的 `validateUiMessage` action 表不存在,JS 只驗證入站訊息;roll_name payload 與既有 `creation.custom` 同樣由伺服端 registry 驗證)。`validateActionResult` 的 success 條件 `data` 驗證已由前置 change 落地,本 change 不動。

### D7 — 測試落點與 shard(不新增模組)

sex/roll 契約全部補進既有模組:`world.rules.tests.test_character_creation`(request 歸一、activation 寫 `entity.sex`、rollback 快照含 sex、preset 寫 DEFAULT_SEX)、`world.rules.tests.test_creation_wizard`(draft 帶 sex、v2 拒絕、form 描述元 sex 欄)、`web.webclient.presentation.tests.test_creation_panel`(v4 payload、`custom.sex` 標籤/界、鏡像拒 v3)、`web.webclient.actions.tests.test_creation_actions`(custom sex 變體、roll_name roundtrip、payload exact、語意驗證矩陣——表外 race／跨族 subrace／髒 sex 全 rejected 且 roller 零觸及、null race 走 `roll_name_for_race(None)`、兜底名恆落 human／elf／orc 三包零件、零寫入斷言)。result `data` 槽的 emitter/validator 矩陣測(`test_dispatcher.py`、`test_protocol.py`、JS `validateActionResult` parity、store 透傳)屬前置 change `oob-result-data-slot`,不在本 change。前端:node --test `protocol.test.js`/`creation_menu.test.js`/`ui_contract.test.js`;Vitest `tests/overlays/creation_overlay.test.js`(下拉渲染讀 panel 選項、🎲 dispatch payload、success 回填、非 success 不回填);Storybook `CreationOverlay.stories.js` 加 sex 變體 story。全部 shard 標籤(`web.webclient` 遞歸、`world.rules.tests.test_character_creation`、`test_creation_wizard`)已登記於 `.github/evennia-shards.json`,無需動 manifest。

### D8 — 文件判斷:`docs/game/commands.md` 不動

`creation.roll_name` 是 allowlisted UI action(經 `ui_action` 通道、不過文字命令解析器),不是玩家命令;設計 §5.2 明文「經既有 `ui_action` 通道」。`docs/game/commands.md` 只記文字命令,故不改。Telnet 無新命令/無語意變化 → `character-creation-ux` 無 delta。

### D9 — 追溯

新 requirement 文字內以代號引用既有符號(`SEX_VALUES`、`DEFAULT_SEX`、`roll_name_for_race`、`creation.roll_name`、`data` 槽、`creation-roll-name` testid),與 D7 測試一一對映;`tools.spec_traceability list`/`check` 沿用上游 change 的驗證流程。
### D10 — dispatcher result-only 完成通道(研究發現的必要修正)

現況 `_complete_action` 對每個完成的 action 必定出版:`affected_panels` 缺失/空 → 全量快照,
非空 → 該面板更新;`panel_update` 無內容去重。因此「`creation.roll_name` 不刷 panel」的契約
(spec scenario「no panel refresh is emitted」)在不改 dispatcher 的前提下不可實作。修正:完成
通道讀取 adapter 結果的內部布林旗標 `no_presentation`(僅 success/rejected 可帶),為真時跳過
出版、直接以當前 revision 送結果;`_normalize_result` 維持既有欄位白名單,旗標永不上線。重複
請求的 busy-result 已是「送結果不出版」的現成先例,客戶端 `releaseIfReady` 對「結果
presentation_revision == 已提交 revision」立即放行,reducer 收到結果即 notify,不需要新出版。
既有動作全部不帶旗標,出版路徑零行為變動。

### D11 — sex 的客戶端形態:鏡像常數、真實選中值、無 null-model select

研究發現:原生 `<select v-model>` 配 null 模型無法可靠表示「預選 DEFAULT_SEX」(瀏覽器首項
fallback 與 Vue 模型會分岔),且 prop 面板不帶 default 欄。定案(比照 `CREATION_AXES`/八元素詞
彙既有鏡像慣例):
- 鏡像常數住在 `protocol.js`(`CREATION_SEX_VALUES`、`CREATION_SEX_DEFAULT`,僅 key)與
  `creation_menu.js`(`DEFAULT_SEX_KEY`)、`CreationOverlay.vue`(`SEX_DEFAULT_KEY`,比照
  `ACTION_RESULT_FALLBACK_MESSAGE` 的 byte-identical 註解釘選先例);三個鏡像一律由
  `tests/test_creation_parity_contract.py` 的正則釘選對照 `world/lore/sex.py`(該檔才是既有
  雙端釘選場所;`test_webclient_contract.py` 與 `ui_contract.test.js` 無此職責)。
- 模型恒為具體 key:`defaultCustomState().sexKey = DEFAULT_SEX_KEY`;overlay `sex = ref` 初始
  `SEX_DEFAULT_KEY`,`syncFromDraft` 讀 `d.sex ?? 預設`;下拉的可見選中項、`rollNamePayload`
  送出的 sex、`customPayload` 的省略判斷三者永遠同源。
- `customPayload()`:sexKey 等於預設 → 不帶鍵(伺服器歸一,語意與顯式預設等價);非預設 → 帶鍵。

## Risks / Trade-offs

- **[結果 envelope 擴充觸及全部結果流]** → 該風險由前置 change 承擔(`data` 僅 success 可存在且預設缺席、其鏡像驗證場景與回歸測在該 change 落地);本 change 只新增第一個回 `data` 的 adapter,端到端測斷言其餘結果流不變。
- **[panel/draft 雙版本 bump 造成鏡像漂移]** → 既有雙向 parity 測試(`test_registry`/`ui_contract`)天然鎖定;版本常量各一處(服務端 `creation.py`、JS `protocol.js`)。
- **[回填競態(擲名返回前玩家已打字)]** → 契約上回填是覆寫(同概念 fill),玩家隨后可再改;Vitest 斷言只在 request-id 配對 success 時回填。
- **[髒 race 企圖借隨機包兜底成功]** → UI 入口以語意驗證封死:表外 race/跨族 subrace/髒 sex 一律 rejected 且 roller 零觸及(monkeypatch 計數斷言);規則層兜底僅剩 `race: null`(真實未選)與 NPC 側入口,spec 場景明文兩者的邊界。
- **[null race 兜底名來自哪個包]** → 規則層契約:候選是 `sorted(NAME_PACK_BY_RACE.values())`(human／elf／orc;dwarf／halfling 不參與);adapter 測以「結果名零件恆落三包零件集」斷言,防止未來綁族悄悄擴大 UI 兜底面。
- **[`entity.sex` 寫入與 loader 雙路徑]** → 兩者都寫 `SEX_VALUES` 成員,語意同源常量,無分叉。

## Migration Plan

單次部署:後端(schema v4 + DRAFT_VERSION 3)+ 前端同版發布;殘留 v2 草稿被載入端視為不存在(玩家從頭填,未發布可接受);舊 v3 客戶端由 `CREATION_SCHEMA_VERSION` 鏡像閘門拒絕並要求重新載入。回滾 = 回退兩端版本;無資料遷移需反做(v3 閘門同樣拒新版草稿,行為一致)。

## Open Questions

(無 — sex 形態、data 槽、版本 bump 策略均已定案如上。)
