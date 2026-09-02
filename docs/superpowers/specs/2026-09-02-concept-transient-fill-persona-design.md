# 概念暫態填入與 persona 玩家擁有化 — 設計文件

**日期：** 2026-09-02
**狀態：** Approved（待讀者對本文件做最終審閱）
**範圍：** `world/rules/creation_wizard.py`、`world/rules/character_creation.py`、`world/rules/persona_edit.py`、`world/rules/persona.py`、`web/webclient/actions/creation_actions.py`、`web/webclient/presentation/creation.py`、`web/webclient/presentation/character.py`、`web/webclient-app/components/CreationOverlay.vue`、`web/webclient-app/components/CharacterStatusDrawer.vue`、`web/static/webclient/js/elosern/protocol.js`、`typeclasses/npcs.py`、`world/ai/npc_dialogue.py`、`commands/`、`commands/background.py` 命令家族。

本文件是後續 OpenSpec change 實作的依據，並在其與 `creation-persona-persistence`（archive）之 D4 決策衝突時取其優先地位。

---

## 1. 問題陳述

玩家在建立角色時使用概念（concept）功能請 LLM 產生背景豐富的角色，套用後自訂表單只預填數值，「背景（可選）」輸入框為空白。根因查證如下。

LLM 輸出結構（`world/ai/character_creation.py` 的 `PERSONA_FIELDS`）產生 `personality / life_story / habit` 三欄，沒有 `background` 鍵。套用服務 `apply_concept_proposal`（`world/rules/creation_wizard.py`）把三欄寫進伺服器獨有的 persona 草稿區塊，而呈現層契約（archive `creation-persona-persistence` D4）規定 persona 內容從不下線，客戶端只收到一個布林值 `background_generated`。前端 `CreationOverlay.vue` 據此把背景 textarea 填成空字串。

後續查證確立了三項事實，構成本設計的基礎。

其一，`background` 並非 persona 之外的東西，它就是 persona record（import-card 形狀）裡的一個鍵，與三欄敘事文字同類、共用同一個 600 字上限常數 `MAX_PERSONA_FIELD_LENGTH`。

其二，客戶端上傳玩家選擇值已有成熟管道。allocations、年齡、種族等數值一律經伺服端以不可變 registry 重驗（`preflight_character_creation`），authority-like 拒絕清單針對的是身份綁定與伺服器推導值（actor、account、session、host、skill、equipment、magic level、calculated stats）。背景 textarea 本身就是「有界自由文字上傳、伺服端重驗」的現成先例，persona 三欄走同一管道在工程上完全成立。

其三，玩家角色的 persona 只在建立啟動時被 LLM 寫入一次。全部寫入者為：匯入載入器（`world/imports/loader.py`）、建立啟動（`activate_player_character`）、玩家編輯（`world/rules/persona_edit.py`，僅 `background` 鍵）、任務場景建立器（僅 NPC，資料來自作者撰寫的任務 JSON）。`world/ai/` 依架構不變詞永不寫入，因此交還玩家編輯不會與生成系統發生寫入競爭。

archive 文件本身也承認了這個洞：`creation-persona-persistence` design.md 的 Open Questions 把「瀏覽器是否應讓玩家在啟動前檢視並編輯生成的 persona 區塊」列為延後事項。本設計就是對該問題的回答。

## 2. 設計原則

### 2.1 persona 的定位：玩家擁有、可重生的敘事素材

LLM 生成的 persona 三欄與玩家親寫的 background 屬於同類資料。生成發生於建立當下，交還玩家檢視、編輯、儲存之後，擁有權即歸玩家。生成素材可以被後續的生成替換（見 2.3），但經玩家儲存進入 draft 的內容只依玩家的意圖變化。

### 2.2 概念功能：暫態填入器

概念只做一件事：呼叫 LLM 產生一份提案，把提案值填入客戶端尚未送出的表單。填入完成，概念的職責即結束。提案不落地為伺服器草稿，送出後的驗證由表單驗證器承接，與概念無關。

這個切分廢除了「概念草稿機」的全部狀態：`concept_filled` 草稿階段、指紋比對（compare-and-swap）、種族比對承接規則、late-response 防護。概念在伺服器端變得無狀態。

### 2.3 驗證邊界：規則由伺服端把關，語意由玩家把關

伺服端只驗證格式與數值規則（鍵集合、長度、上下限、預算總和、registry 成員資格）。人與角色設定在語意上是否自洽（例如把精靈的生平套到人類身上），由看得見內容的玩家負責，伺服端不做語意檢查，也不覆蓋玩家送出的內容。

### 2.4 已定案的三項定位決策

1. 生成 persona 在建立期間與啟動後兩個階段都交給玩家（建立表單可編輯，啟動後角色面板可見可編輯）。
2. WebClient 與 Telnet 對稱，兩條 surface 共用同一確定性寫入服務。
3. 重新套用概念一律替換表單上的生成欄位。persona 定位為可重生素材，玩家最終定稿靠儲存動作。

## 3. 退役清單

下列既有機制全數刪除，無相容層（本專案尚無正式發布使用者）。

| 退役項目 | 位置 |
|---|---|
| `concept_filled` 草稿階段與 `CONCEPT_STAGE` | `world/rules/creation_wizard.py` |
| `apply_concept_proposal` 服務與 `ConceptDraftStaleError` | `world/rules/creation_wizard.py` |
| 草稿指紋 `draft_fingerprint` 的概念 CAS 用途（指紋本身保留，仍供啟動確認綁定 `fix-creation-finalization-safety` 使用） | `world/rules/creation_wizard.py` |
| custom save 的 persona 承接與 race 比對分支 | `save_custom_draft` |
| wire 欄位 `background_generated` 與「已套用構想草稿，背景已生成」指示文字 | `web/webclient/presentation/creation.py`、`CreationOverlay.vue` |
| concept 路徑的確認失效（invalidate-on-reject）用法 | `web/webclient/actions/creation_actions.py` |
| 主規格 `creation-persona-persistence` 的概念草稿、CAS、承接、指示文字諸要求 | `openspec/specs/creation-persona-persistence/`（由本 change 的 delta 改寫） |

## 4. 建立期設計

### 4.1 草稿存儲

draft 只剩 `preset_selected` 與 `custom_filled` 兩種模式。`custom_filled` 增一個必現、值可為 null 的 `persona` 鍵。值為物件時必恰 `{personality, life_story, habit}` 三鍵，各自為 1 至 600 字非空文字，驗證直接重用既有 `_validate_persona_block`。缺鍵的舊形狀 draft 視為損壞，降級單一草稿槽位（沿用 `_normalize_draft` 的降級慣例）。

### 4.2 `creation.concept`（一次呼叫，零持久寫入）

payload 維持恰 `{concept}`。adapter 跑既有 guarded pipeline（注入 client、預算驗證、降級標記），成功後不寫任何持久狀態，降級與驗證失敗走既有 `concept_unavailable` 穩定拒絕。

提案的送達走倉庫現成的 session 瞬態模式（options suggestions 的 `session.ndb.options_state` → `PresentationContext.options_state` → presenter 渲染，本設計與 `FrozenCard`/`OptionsSnapshot` 同構）：adapter 以它依 ABI 收到的 session，把驗證過的提案寫入 `session.ndb.concept_proposal`（不持久化、斷線即滅，正是暫態填入的語意），回傳 confirmed success（code `concept_applied`）並宣告 affected `creation` panel；presenter 從 context 的提案快照渲染出 panel 的 `proposal` 槽，客戶端據此填入表單。`PresentationContext` 依 `options_state` 的既有先例新增提案快照欄位，由 coordinator 在建立 context 時從 session 複製。

提案的生命週期：寫入於套用成功；清除於 `creation.custom` 儲存成功、`creation.reset`、概念再次套用、或 session 結束。自訂儲存前的每次面板重建照樣渲染提案，讓重新連線能重建暫態填入；儲存成功後提案即不再出現。

信封上限方面，最差情況三欄各 600 個中日韓文字約 6 KB，對 `MAX_CANONICAL_JSON_BYTES = 65536` 餘裕充足，並以 worst-case 測試鎖定。

### 4.3 `creation.custom`

payload 從 8 鍵增為 9 鍵，新增必填 `persona` 鍵，值為 null 或恰三鍵物件。沿用「wire payload 恆帶齊全鍵、空白欄位送出其 JSON 安全預設」的既有慣例。伺服端以 `_validate_persona_block` 與既有 preflight 重驗，不驗語意、不驗數值來源。

承接規則：payload `persona: null` 時寫 null。玩家換種族或血統不觸發任何伺服端覆蓋或拒絕。

### 4.4 啟動

`activate_player_character` 的 persona 參數改從 custom draft 的 `persona` 鍵取得。有 persona 塊時沿用既有 import-card 形狀寫入；無 persona 塊時維持現有 `elif` 分支，僅在玩家有 background 時寫入。`background` 的值照樣經 `CharacterCreationRequest` 進入 record 的 `background` 鍵。

### 4.5 creation panel（schema v1 → v2）

available payload 增一個 optional 頂層鍵 `proposal`（僅存在且有未消费的暫態提案時；恰 `{race_key, subrace_key, allocations, persona{personality, life_story, habit}}`，沿用 optional 鍵的既有先例），`schema_version` 升為 2。draft 的 custom 形狀增 `persona`（物件或 null）；concept 形狀不復存在。presenter、`presentation/creation.py` 驗證器、`protocol.js` 鏡像驗證器同步為 v2。custom 模式不再有任何「非內容指示」，persona 內容僅以 proposal（暫態填入來源）與 draft（已儲存值）兩種身份上線，「面板不暴露 persona」的舊斷言據此改寫為「不渲染伺服端草稿 persona 之外的 persona 資料」。

### 4.6 Vue 表單（`CreationOverlay.vue`）

- 收到 `concept_filled` 結果時，把提案值寫入尚未送出的本地表單：race、subrace、allocations、三個 persona textarea。`syncFromDraft` 只認伺服端已接收的值，不看未送出的提案。
- 三個 textarea 於 custom 模式恆渲染，無值時空白供親手填寫。
- 本地驗證：persona 三欄探「要填就填滿」規則，部分填寫以本地訊息阻擋（與 subrace 錯誤同一機制），不發出 action。
- 概念套用成功後 dock 由 concept 翻到 custom 的導覽保留，這是 store 本地狀態。
- 玩家換掉種族或血統而表單仍帶生成文字時，persona 區塊旁顯示審視提示（純 UI 文案，無伺服端邏輯）。

### 4.7 Telnet `character concept` 流

流程改為：跑 guarded pipeline → 於終端顯示提案摘要（含 persona 三欄文字）→ 收集名字與兩個年齡並過成年閘 → 以提案值加親打欄位直接啟動。語意上正式承認提案為暫態填入物，啟動前玩家的回應即是把關。命令語法與命令文件不變。

## 5. 啟動後設計

### 5.1 寫入服務（`world/rules/persona_edit.py`）

`update_background` 泛化為 `update_persona_field(character, field, text)`。欄位白名單為模組常數 `PERSONA_EDITABLE_FIELDS`，恰 `background / personality / life_story / habit` 四鍵。文字經 trim 與 600 字上限驗證；None 或空白表示移除該鍵；無 persona record 時先建 import-card 形狀 record；其餘鍵（含未知鍵）一律原樣保留。`update_background` 保留為 `update_persona_field(character, "background", text)` 的薄包裝，既有呼叫者零改動。模組 docstring 的單寫者宣言改述為四鍵白名單。

### 5.2 character panel（schema v6 → v7）

`persona` 區塊從恰 `{background}` 擴為恰 `{background, personality, life_story, habit}`，各自可為 null 且上限 600 字。`character_presenter` 從 `actor.persona` 逐鍵取值，沿用既有「非字串轉 None、純空白轉 None」清洗。`protocol.js` 鏡像驗證器同步。`CharacterStatusDrawer.vue` 的背景區塊升級為四段顯示（個性、生平、習慣、背景），空值走既有「未設定」佔位樣式。

### 5.3 新 action `character.persona.update`

payload 恰 `{field, text}`。`field` 必屬四鍵白名單，`text` 為 null 或 trim 後 1 至 600 字的字串（空白等同清除）。adapter 走標準所有權解析（本人 puppet、探索模式），直呼 `update_persona_field`，回傳 confirmed success 與繁體中文訊息，並刷新 character panel。驗證失敗回穩定拒絕碼。對不存在欄位執行清除為 no-op success。registry 恰鍵清單同步增一條。

### 5.4 Telnet 命令家族

`設定背景` 不動。新增三個命令，行為逐字複製 `CmdBackground` 的三段式（無參數顯示現值與用法；有參數設定；空白參數清除），並全部經 `update_persona_field`。

| 命令鍵 | 別名 | 欄位 |
|---|---|---|
| 設定個性 | 個性 | `personality` |
| 設定生平 | 生平、背景故事 | `life_story` |
| 設定習慣 | 習慣 | `habit` |

命令文件契約同步：`docs/game/commands.md` 與 `docs/game/command-reference.md` 增三筆條目，`tests/test_command_docs.py` 保持綠。

## 6. 錯誤處理矩陣

| 失敗點 | 行為 | 狀態 |
|---|---|---|
| 概念：LLM 離線、提案驗證失敗、重試耗盡 | `concept_unavailable` 穩定拒絕與中文訊息；表單原樣可手動填寫 | 零寫入 |
| 概念進行中斷線或關閉瀏覽器 | 進行中的填入遺失，重連後回到表單，玩家重按套用 | 零寫入（已接受的代價） |
| `creation.custom` persona 鍵集合錯誤、空字串、超 600 字 | `CreationActionError` 映射穩定拒絕碼與中文訊息 | 草稿不動，本地表單保留輸入 |
| 本地驗證：persona 部分填寫 | Vue 本地訊息阻擋 | 無 action 送出 |
| `character.persona.update` 欄位非白名單或文字超界 | 穩定拒絕碼 | record 不動 |
| 建立面板最差情況超過信封上限 | 雙端驗證器以 65536 位元組 fail-closed | 以測試鎖最差情況通過 |

## 7. 測試與驗證

純邏輯層（`unittest`）：`_normalize_draft` 對 custom persona 鍵的四類情形（缺鍵損壞降級、null 合法、非恰三鍵拒絕、超界降級）；`validate_creation_custom_payload` 的 9 鍵；`update_persona_field` 四鍵乘以（設定、清除、保留未知鍵、600 界線）；`activate_player_character` 自 custom draft 寫入 persona 與無 persona 僅寫 background 兩路徑。

Evennia 整合層：三個新命令各四路徑（顯示、設定、清除、超界）的 `EvenniaCommandTest`；`creation.concept` adapter 回傳 `concept_filled` data 形狀且零狀態變更的斷言；`creation` v2 與 `character` v7 兩個 presenter 驗證。

JS 層：`protocol.js` Node 鏡像驗證器新案（draft persona、custom 9 鍵、character v7、`ui_action_result` 的 affected data）；Vitest 覆蓋 `CreationOverlay` 的概念填入、textarea 預填、編輯後 9 鍵 payload、部分填寫本地阻擋，以及 `CharacterStatusDrawer` 四段渲染。

瀏覽器層：單一 Playwright class 走完整旅程（概念 → 表單編輯 → 啟動 → drawer 顯示），全量瀏覽器套件歸 CI。

契約層：新與改的主規格每條 requirement 掛 `covers_requirement`，`tools.spec_traceability check` 綠；新測試模組註冊 `.github/evennia-shards.json`；命令文件兩式同步。

驗收腳本（smoke）：啟動伺服器，網頁端以概念句「背景豐富的角色」走完整流程，確認三 textarea 預填生成文字，編輯其中一欄後儲存啟動，drawer 顯示四欄且含編輯痕跡；Telnet 以 `設定生平` 改一欄，重新整理確認；最後於 LLM 關閉狀態重驗純手動建立全程。

## 8. OpenSpec 衝擊

| 既有 capability | 動作 |
|---|---|
| `creation-persona-persistence` | 改寫（概念降為暫態填入器；草稿階段、CAS、承接、指示文字諸要求退役） |
| `webclient-character-creation-ui` | modified（draft 兩模式、custom payload 9 鍵、creation panel v2） |
| `player-character-creation` | modified（啟動 persona 來源改自 custom draft；概念流語意改寫） |
| `webclient-action-dispatch` | modified（registry 增 `character.persona.update`） |
| `webclient-oob-protocol` | modified（`ui_action_result` affected data 增 `concept_filled` 形狀） |
| `persona-store` | modified（`flatten` 取得 `identity / appearance / social_connection` 的寬容渲染，見 §11） |
| `persona-dialogue-injection` | modified（注入欄位選取政策，見 §11.4） |
| `import-schema` | 不變（persona 驗證維持 verbatim opaque） |

## 9. 取捨與已接受代價

1. 概念進行中斷線會遺失進行中的填入，玩家需要重按套用。換得的是概念在伺服器端完全無狀態，刪除了 CAS、承接比對、確認失效三組機制。
2. 伺服端放棄對 persona 語意的最後防堵（種族與生平矛盾的自動清理）。換得的是「上傳即意圖」模型的一致性，玩家看得見自己送出的內容，矛盾的把關交還給看得見內容的玩家，UI 提供審視提示。
3. 兩個 panel schema 版本、九鍵 custom payload、四鍵白名單命令家族同時變動，變更面大，但每處都是既有精確模式（exact-fields、穩定拒絕碼、三段式命令）的機械性擴充。

## 10. 範圍外

- NPC persona 的任何變動（任務場景建立器路徑不動）。
- 遊戲中由生成系統更新 persona（未來若需要，須另行領取確定性寫入 seam 並另行定義衝突規則）。
- persona 的 `identity / appearance / social_connection` 鍵的編輯，以及它們在角色面板的呈現。本變更為它們提供存儲、讀取與 LLM 注入（見 §11），編輯 UI 留待有實際需求後另行變更。

## 11. 三鍵 persona 整合（identity / appearance / social_connection）

### 11.1 由來與查證

這三個鍵源自 `tmp/story_settings/character/` 角色表的既有欄位，五張角色表的結構完全一致（匯入範例把它們壓成字串只是範例精簡，並非原始意圖）。各鍵的真實意義如下。

- `identity`：雙層結構。`public` 是外在公開的身分、職責與頭銜；`hidden` 是不為人所知的真實身分或秘密。分層的用途在於讓不同消費者看到不同深度。
- `appearance`：可供描述與生成參照的外觀檔。固定子鍵為 `height / weight / measurement / style / overview`，另有 `attire`（場景到服裝的映射）與 `feature`（標誌性配件清單）。角色表的 DNA 與成人欄位屬於狀態系統領域名稱，不進 persona。
- `social_connection`：以對象名為鍵的字典，每筆含 `relationship` 文字（與本人的關係、情感定位、互動記憶），是對話時「知道誰、怎麼稱呼、什麼態度」的依據。

現行倉庫對這三鍵零消費者（`PersonaStore.flatten` 的預設欄位集不含它們）。本節為它們建立第一個消費者，也就是對話 prompt 注入。

### 11.2 形狀定義（文件層契約）

上述結構以文件層契約定義，不進驗證器，persona 的匯入驗證維持 verbatim opaque。`PersonaStore` 的渲染採寬容策略：字面值照渲染、Mapping 渲染為「子鍵：值」行、清單渲染為列點、未知形狀跳過不抛錯。匯入範例的字串寫法與角色表的巢狀寫法於焉皆可渲染。

### 11.3 flatten 擴充

為 `identity / appearance / social_connection` 新增渲染組與正體中文標籤（公開身分、隱秘身分、外觀、人脈）。每一項受 600 字上限、整塊受 block limit 約束，沿用既有 `_cap` 截斷機制。欄位集參數維持呼叫端可覆寫的現行設計。

### 11.4 注入欄位選取政策（已核准）

- NPC 自己的 persona：全欄提供，含 `identity.hidden`。角色自己的秘密交給角色自己的 LLM 是角色扮演的本意，數值洩漏由既有 no-leak validator 把關。
- 玩家的 persona 送入 NPC prompt：提供 `identity.public`、`appearance`、`social_connection`。NPC 眼中的玩家僅止於外觀、公開身分、與 NPC 自己的人脈記錄。`identity.hidden` 排除，那層留給未來的敘事者層材料。

### 11.5 編輯界線

三鍵維持排除於建立表單與四鍵編輯白名單之外，結構化欄位不適用單文字欄編輯模型。本變更只開放「存得進、讀得出、進了 LLM prompt」。

### 11.6 測試

純邏輯層：角色表巢狀形狀的渲染、匯入範例字串形狀的相容渲染、單項截斷、整塊截斷、未知形狀跳過。整合層：NPC system message 含隱秘身分的斷言、玩家 persona 塊不含 `identity.hidden` 的斷言、無 persona 玩家的 payload 位元等值（沿用既有場景）。

### 11.7 代價

玩家 persona 塊變大後，NPC 對話 prompt 的 token 成本上升，2000 字的 block limit 可能觸發截斷。緩解方式是呼叫端按 surface 覆寫上下限（`PersonaStore` 建構子已參數化）。
