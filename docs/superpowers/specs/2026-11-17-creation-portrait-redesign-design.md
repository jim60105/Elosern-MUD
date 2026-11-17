# 角色創建介面重設計與建角肖像設計（Creation Portrait Redesign Design）

日期：2026-11-17
狀態：已核准（提案完成；七個 OpenSpec change 與平行實作批次見 §9）

版面參考：`docs/design/creation-portraits/`（Storybook `Design/CreationPortraits`，合成資料，立繪為內建預設圖）。

## 1. 問題陳述

webclient 的設計方向是 AVG＋RPG，圖是畫面的主體。角色創建卻是整個 client 裡唯一沒有圖的畫面：

- 預設角色卡只有編號菱形與文字。八位預設角色都有官方立繪（`art-official/preset/<key>/`），玩家在選角時卻看不到。
- 自由創建看不到角色的樣子。肖像要等角色啟用後才自動生成，玩家無法在確認前看到或重生。
- 自由創建把身分、故事、能力三區塞在同一頁，1451x790 下三區各自捲動，故事區第三個欄位以下與能力區第五軸以下都在摺線之下。
- 概念模式左側只有一段說明，沒有告訴玩家該寫什麼、寫了會得到什麼。

本設計重做三個模式的版面，並加入兩項功能：預設角色顯示官方圖，自由創建以剪影起始、可在建角過程中生成肖像。

## 2. 範圍

範圍內：

- `CreationOverlay` 的外框與三個模式的版面。
- `creation` 面板 schema 升版，承載預設角色圖、剪影對照與建角肖像狀態。
- 新的建角肖像生成動作，以及它與啟用、重設的互動。
- 既有 `GalleryGenerateDrawer` 的重用。

範圍外：

- Telnet 建角精靈。
- 配點規則、預算、年齡界線、名稱驗證等任何建角規則。
- 概念生成的提示詞與提案內容。
- 預設角色資料與官方圖本身。
- 啟用後的圖庫行為。

## 3. 遊玩情境與決策對應

平台為桌面 16:9，滑鼠與鍵盤並用，參考視窗 1451x790 與 2560x1440。建角沒有時間壓力，是一次性的、不可逆的選擇。

| 模式 | 玩家的決策 | 需要的資訊 | 呈現 |
| --- | --- | --- | --- |
| 預設角色 | 選哪一位 | 長相、種族與血統、專長、來歷 | 八張圖卡同時可見；展開的一張給完整資訊 |
| 自由創建 | 每個欄位填什麼；要不要現在生成肖像 | 該步驟的欄位、剩餘點數、肖像目前的狀態 | 一次一步；肖像欄與剩餘點數常駐 |
| 概念生成 | 寫什麼 | 可以寫的方向、會被填好的項目、不會被填的項目 | 左側引導，右側輸入 |

啟用角色是唯一不可逆的動作，沿用現有的確認畫面，不新增第二條確認路徑。

## 4. 外框

- 頁首三欄：左為標題，中為模式分頁，右為副標。分頁沿用共用的 `.ui-tabs`，標籤為「預設角色／自由創建／概念生成」。分頁移進頁首後，內容區多出一整列高度。
- 頁尾固定：左為「重設」（`.ui-btn--danger`），右為該模式唯一的主要動作（`.ui-btn--primary`）。預設角色模式的主要動作在展開的卡片內，頁尾右側改放鍵盤提示。
- 確認畫面、結果訊息、表單訊息、不可用原因的行為與 `data-testid` 不變，只調整樣式以配合新外框。
- 所有尺寸乘上 `--ui-scale`，顏色、字體、間距、動態只用 `styles/tokens.css` 的既有 token，不新增 token。

## 5. 預設角色：卡牌牆

### 5.1 版面

八張直幅卡排成一列，高度填滿內容區。

- 收合的卡：立繪以卡片高度為準置頂裁切，壓暗並降低飽和；底部漸層上放編號與直排名字。滑鼠移入時恢復亮度與飽和，邊框轉金。
- 展開的卡：寬度約為收合卡的七倍。左側是完整立繪（9:16，不裁切，帶金色光暈），右側是卷宗：「預設角色 NN / 08」、名字、種族與血統、分隔紋飾、專長（`emphasis`）、來歷（`background`），底部是主要動作「以〈名字〉啟程」。
- 立繪在兩種狀態下用同一套尺寸定義：高度永遠等於卡片高度，寬度為高度的 9/16（以卡片為 size container 的 `cqh` 單位）。展開與收合只改變它的水平位置與 `transform: scale`。兩種狀態若各用一套 `background-size` 或盒模型，切換的瞬間無法補間，圖片會跳動。
- 展開與收合以 `flex-grow` 過渡，時間與曲線取 `--motion-*`／`--ease-*`，動態等級為 `reduced` 或 `off` 時直接切換。

### 5.2 互動

- 點收合的卡、按 ← →、按數字鍵 1–8，都只改變「展開哪一張」。這是瀏覽器本地狀態，不送出任何動作。
- 只有「以〈名字〉啟程」與 Enter 會呼叫現有的 `selectPreset`，之後走現有的草稿與確認流程。
- 進入模式時展開草稿中的 `preset_key`；沒有草稿時展開第一張。
- 收合的卡是原生 `button`，名稱為角色名；展開狀態以 `aria-current` 與金色邊框雙重表示，不只靠顏色。焦點框沿用現有的金色 outline。

現況是點卡片就直接選定。改成兩段的理由：卡片現在同時是「看圖」的入口，瀏覽不應該推進流程。

### 5.3 圖片來源

- 每張預設卡多一個 `artwork` 欄位，是伺服器組好的 canonical artwork descriptor，以 `ArtworkPreview` 顯示。
- 伺服器以 `world/art/official_refs.py::official_content_reference_for_preset` 解析官方圖。這個入口本來就是為建角預覽保留的。
- 沒有官方圖時，descriptor 的終端回退是內建預設圖，鍵由卡片宣告的 `fallback_key` 或性別／年齡帶規則決定（`world/art/gallery_fallback.py`）。瀏覽器永遠不拼接圖片網址。
- 圖片載入失敗時沿用 `ArtworkPreview` 的既有降級行為。

## 6. 自由創建：分步表單

### 6.1 版面

左側是固定寬度的肖像欄（§7），右側是三個步驟：

| 步驟 | 欄位 |
| --- | --- |
| 01 身分 | 名稱與擲名、性別、種族、年齡、外觀年齡、血統、種族說明 |
| 02 角色故事 | 元素親和、背景、個性、生平、習慣 |
| 03 能力配置 | 已配置點數、七軸步進器與長條 |

- 步驟列在表單上方，三格等寬，每格是一個按鈕：編號加標題。目前步驟以金色上緣線與金色文字雙重表示，已完成的步驟上緣線為暗金。
- 03 的格子右側常駐顯示剩餘點數，玩家在 01、02 也看得到。
- 每一步的內容在 1451x790 下不需要捲動。能力配置排成兩欄。
- 步驟下方有「上一步」與「下一步：〈標題〉」。

### 6.2 互動

- 步驟不鎖順序，可直接點步驟列跳轉。
- 「確認角色」常駐頁尾，任何步驟都能按。
- 驗證與送出沿用 `use-creation-form.js`／`use-creation-custom.js` 的現有管線，不新增瀏覽器端規則。驗證失敗時，表單訊息照舊顯示，並自動切到第一個有問題欄位所在的步驟；該步驟在步驟列上加朱紅標記與「需修正」文字。
- 欄位與步驟的對應是一張靜態表，放在新的 `use-creation-steps.js`。目前步驟是瀏覽器本地狀態，不進草稿。
- 概念提案填入表單後停在 01，審閱提示照舊顯示在表單上方。
- 所有欄位的 `data-testid` 不變。原生 `select`、`input`、`textarea` 與步進器的直接輸入行為不變。

三區同頁改成分步的代價是故事與點數不能同時看，由常駐的剩餘點數補償。

## 7. 肖像欄與建角肖像生成

### 7.1 肖像欄

肖像欄出現在自由創建，由新元件 `CreationPortraitSlot.vue` 負責。它只讀 props，不直接送動作。

| 狀態 | 畫面 | 說明文字 | 按鈕 |
| --- | --- | --- | --- |
| 空白 | 剪影 | 填好身分後，為角色繪製肖像。 | 生成肖像 |
| 繪製中 | 呼吸的剪影加轉圈 | 可以繼續填寫，完成後會自動出現。 | 停用 |
| 完成 | 生成的肖像 | 不滿意可以重新繪製。 | 重新生成肖像 |
| 失敗 | 剪影 | 伺服器給的失敗原因 | 生成肖像 |
| 服務離線 | 剪影 | 伺服器給的離線原因 | 停用 |

- 剪影是內建預設圖套上 CSS 遮罩後的純色人形，不是另一批素材。
- 用哪一張預設圖由性別與外觀年齡決定。對照表由伺服器放在面板的 `custom.silhouettes`，瀏覽器只查表，不複製年齡帶規則。
- 肖像欄下方顯示目前的名稱；未命名時顯示「尚未命名」。
- 繪製中的轉圈與呼吸動畫遵守動態等級。狀態同時以文字表示。

### 7.2 生成流程

1. 玩家按「生成肖像」，開啟既有的 `GalleryGenerateDrawer`。
2. drawer 收到的 capabilities 為 `supports_field_selection: false`、`supports_free_text: true`、`max_cards: 1`。建角時沒有裝備，自訂表單也沒有外貌欄位，所以只開放補充提示詞。
3. 玩家送出後，`CreationOverlay` 發出新動作 `creation.portrait.generate`，payload 為 `race`、`subrace`、`sex`、`apparent_age`、`custom_prompt`，前四項取自表單目前的值。
4. 伺服器驗證通過後排入既有的生成佇列，面板的 `portrait.status` 轉為 `pending`。
5. 生成完成後，面板的 `portrait` 帶上 `artwork`，肖像欄原地換成成品。

drawer 的文案有兩處依賴「已存在的角色」（「透過目前的角色資料」與「送出後會在圖庫中顯示」）。`GalleryGenerateDrawer` 新增一個選用的 `context` prop，值為 `creation` 時換成建角文案；預設值維持圖庫的現有行為，圖庫端不需要改動。

### 7.3 伺服器端

- `creation.portrait.generate` 加入 `web/webclient/actions/creation_actions.py` 並登記在 `registry.py` 的 allowlist。它只在角色為 `creation_pending` 時接受。
- 驗證重用建角既有的驗證器：種族與血統的註冊與從屬、性別對種族的限制、外觀年齡 `0..10000`、補充提示詞走 `world/art/gallery_prompt.py::validate_custom_prompt`。任何一項失敗都整筆拒絕，不排入佇列。
- 生成的對象是待啟用角色自己的肖像 subject。啟用後它就是同一個角色，圖不需要搬移。這個動作在排入佇列前先為待啟用角色建立具名的 `portrait_policy`，建立方式與 `finalize_player_portrait` 相同，並抽成兩者共用的函式。
- 描述文字由 payload 的值組成，不讀角色身上尚未寫入的身分屬性。`world/art/subjects.py` 新增一個以種族鍵、血統鍵、外觀年齡為輸入的描述函式，與 `character_description` 共用同一個提示詞模板，不帶外貌與裝備區塊。
- 狀態變更由 `world/rules/` 套用。`world/art/` 仍只負責佇列與產圖，維持單一寫入者邊界。
- 同一個 subject 已有進行中的工作時拒絕新的請求，沿用現有的 in-flight 判斷。
- 生圖服務不可用時動作被拒絕，原因來自既有的 art connectivity surface；面板同時把這個原因放進 `portrait`，讓按鈕在送出前就停用。

### 7.4 與啟用、重設的互動

- 啟用：`finalize_player_portrait` 排程的自動生成有既有的冪等防護（`_gallery_auto_generation_pending`），圖庫已有卡片或有進行中的工作時不再生成。建角時生成過的角色因此不會重複生成；沒生成過的角色照舊在啟用後自動生成。
- 啟用失敗而回滾時，建角期間生成的圖保留。它屬於待啟用角色，不屬於那次啟用交易。
- 重設：清除草稿的同一個操作刪除該 subject 在建角期間產生的卡片，並取消進行中的工作，肖像欄回到剪影。
- 改了性別、種族或外觀年齡之後，已生成的肖像保留，不自動作廢，也不提示。玩家想換就按「重新生成肖像」。
- 以預設角色啟用時，建角期間為自訂草稿生成的卡片先刪除，再走預設角色原本的肖像流程，避免預設角色帶著不相干的圖。

## 8. 概念生成

- 左側是引導欄，分三塊：
  - 「可以寫些什麼」：四個問題（出身與成長環境、維生方式與專長、性格與習慣、踏上旅途的理由）。
  - 「會幫你填好」：名稱、年齡與外觀年齡、種族與血統、能力配點、元素親和、背景、個性、生平、習慣。清單對應提案契約的欄位。提案抵達後，有值的項目打勾。
  - 底部一行：性別與肖像不會自動產生，套用後請在自由創建中補上。
- 右側是標題、一行流程說明與填滿高度的輸入框，範例句放在 placeholder。
- 生成中的讀取狀態、`applyFrozen`、成功 toast、失敗訊息的行為不變。
- 概念文字不會帶進肖像的補充提示詞。

## 9. 面板契約與 OpenSpec 拆分

`creation` 面板的可用 payload 變更如下，伺服器 presenter 與瀏覽器端鏡像驗證器同步修改：

| 欄位 | 內容 | 所屬 change |
| --- | --- | --- |
| `presets[].artwork` | canonical artwork descriptor | `creation-panel-artwork` |
| `custom.silhouettes` | 性別與外觀年齡區間對應的 artwork descriptor 清單 | `creation-panel-artwork` |
| `portrait` | `status`（`empty`／`pending`／`ready`／`failed`／`unavailable`）、選用的 `artwork`、選用的 `reason` | `creation-draft-portrait-panel` |

每個 change 各升一次 schema 版本，舊版本一律拒絕。專案沒有已發布的使用者，不做相容層。

### 9.1 提案清單

本設計原先規劃兩個交付（`creation-portrait-layout` 與 `creation-draft-portrait`）；實際提案依「一個工作天可完成」切成七個 change。協議變更、兩個 UI 介面，以及請求／狀態／生命週期的整合各自有獨立的測試擁有者，因此分開交付；肖像欄的空白狀態留在 UI 切片，其餘狀態與生成流程一起交付。

| 序 | change | 範圍 | schema | 前端視覺 | commit |
| --- | --- | --- | --- | --- | --- |
| 1 | `creation-panel-artwork` | `presets[].artwork` 與 `custom.silhouettes` 的 canonical descriptor、presenter 與瀏覽器鏡像驗證器 | 7 | 間接：只提供資料與 fixtures，無版面 | `b10d6d91`、`9083d9d8` |
| 2 | `creation-preset-card-wall` | 卡牌牆的本地展開與明確選取 | 7 | **是**：卡牌牆版面、`creation-overlay.css`、stories、`visual-review.md` | `f49cd972` |
| 3 | `creation-stepped-form` | 三步表單、概念引導、空白肖像欄 | 7 | **是**：分步表單與引導欄版面、元件 CSS 拆分、stories、`visual-review.md` | `21682318` |
| 4 | `creation-draft-portrait-request` | `creation.portrait.generate` 的准入與序列化、connectivity 的唯一例外 | 7 | 否：後端 action 與驗證 | `a483442a`、`5b7c45d7`、`12f61043` |
| 5 | `creation-draft-portrait-panel` | 面板 `portrait` 區塊、schema 8、完成發佈 | 8 | 間接：提供狀態與表格同步，無版面 | `3126d1e9`、`f3b02b74`、`4d506462` |
| 6 | `creation-draft-portrait-cleanup` | 重設與啟用的所有權、rollback 保證 | 8 | 否：只有生命週期與行為回歸 | `ef4f72d8`、`7ebd5d07` |
| 7 | `creation-draft-portrait` | 真實 `GalleryGenerateDrawer` 整合與顯式狀態刷新 | 8 | **是**：肖像欄五態、drawer 文案與版面、stories、`visual-review.md` | `c17480e7`、`3edcd79d`、`b3aebb81` |

兩個 schema 切換點：change 1 升到 7（descriptor 與 silhouettes），change 5 升到 8（`portrait` 區塊）。其餘 change 沿用當前版本。

前端視覺的實作者是 change 2、3、7；三者各自產出 `visual-review.md`，並在 1451x790 與 2560x1440 驗證。change 1 與 5 只讓畫面有東西可畫（descriptor 與 portrait 狀態），change 4 與 6 不動任何版面。

### 9.2 依賴、衝突與平行實作批次

縮寫：A artwork、W wall、S steps、R request、P panel、C cleanup、I integration。

依賴 DAG：A → W → S；A → R；R 與 S → P → C；S 與 C → I。P 依賴 S，因為它的 mounted-form 保留回歸必須跑真實步驟。單一工程師的安全順序是 A、W、S、R、P、C、I。不需要子 Git repo。

| 批次 | 可同時進行的 change | 前置 |
| --- | --- | --- |
| 1 | A `creation-panel-artwork` | 無 |
| 2 | W `creation-preset-card-wall`、R `creation-draft-portrait-request` | A |
| 3 | S `creation-stepped-form` | A、W |
| 4 | P `creation-draft-portrait-panel` | S、R |
| 5 | C `creation-draft-portrait-cleanup` | R、P |
| 6 | I `creation-draft-portrait` | S、C |

衝突判定：`共享` 表示必須序列化共用檔案或同一條 spec requirement；`平行` 表示實質程式碼互斥，只需一般文件與 manifest 整合。

| 組合 | 衝突與必要順序 |
| --- | --- |
| A/W | artwork props 與 fixtures 由卡牌牆消費；A 先於 W |
| A/S | silhouette 表與 fixtures 由肖像欄消費；A 先於 S |
| A/R | presenter／fallback API 與 art 測試；A 先於 R |
| A/P | 同一面板／鏡像／fixtures 與版本 requirement；A 先於 P |
| A/C | 在 R 之後可平行；沒有共同 requirement 替換 |
| A/I | descriptor 與 fixture 消費；A 先於 I |
| W/S | 同一 overlay／CSS／stories 與 workspace requirement；W 先於 S |
| W/R | A 之後程式碼可平行；registry 對 UI，只共用文件與 manifest |
| W/P | A、R 之後程式碼可平行；共用 fixtures 與文件需整合 |
| W/C | R 之後程式碼可平行；共用 overlay 測試 |
| W/I | 同一 overlay／stories／focus；W 先於 I |
| S/R | 前置完成後實質程式碼可平行 |
| S/P | 同一 overlay／form／stories 與 mounted-step 回歸；S 先於 P |
| S/C | 程式碼可平行；共用 overlay 測試 |
| S/I | 同一 slot／overlay／composable／stories；S 先於 I |
| R/P | receipt／read model 與 publication 結果；R 先於 P |
| R/C | 同一 rules／service／queue／測試，autogen spec 檔但不同 requirement 區塊；R 先於 C |
| R/I | request 與 echo 由 drawer host 消費；R 先於 I |
| P/C | receipt／錯誤／重設的 publication 語意；P 先於 C |
| P/I | union／result／state 由 slot 消費；P 先於 I |
| C/I | 生命週期瀏覽器旅程；C 先於 I |

| 目前開啟中的其他 change | 對 A/W/S/R/P/C/I 的衝突 |
| --- | --- |
| `ciaran-village-local-goods` | 無；產品檔案與 spec 無交集，不觸發 creation／art／資料重生 |
| `fionnen-village-fare-homes` | 無；僅在新測試登記時共用 CI manifest |

`fionnen-village-craft-homes` 已封存，不計入開啟中的衝突。connectivity capability 的 delta 只由 R 擁有；P 與 I 消費 R 的 API 與狀態，不另寫 connectivity delta。目前沒有其他開啟中的 change 觸及 `art-service-connectivity-surface` 或 `world/art/connectivity.py`，因此這個修訂沒有外部衝突；日後開啟的 change 若觸及這兩者，必須與 R 序列化。

### 9.3 既有 requirement 的改寫

`openspec/specs/webclient-character-creation-ui/spec.md` 需要改寫的既有要求：

- 「三個桌面區域」改為 §4–§6 的外框、卡牌牆與分步表單。
- 「預設卡不得宣稱未提供的肖像」改為：預設卡顯示伺服器提供的 artwork descriptor，瀏覽器不得自行組出圖片位置。
- 面板的欄位清單與 schema 版本。

`art-gallery-generation`、`art-gallery-autogen`、`art-subject-model`、`webclient-action-dispatch` 與 `webclient-input-narrative` 由 `creation-draft-portrait-request` 增補建角期間生成的要求；`player-character-creation` 由 `creation-draft-portrait-cleanup` 增補重設與 rollback 的要求。

## 10. 元件與檔案

| 單元 | 責任 | 依賴 |
| --- | --- | --- |
| `CreationOverlay.vue` | 外框、模式切換、確認畫面、訊息、頁尾；把動作往外發 | `use-creation-overlay.js`、下列三個子元件 |
| `CreationPresetWall.vue` | 卡牌牆與展開狀態；發出 `choose` | `ArtworkPreview` |
| `CreationCustomSteps.vue` | 步驟列、三步內容、上一步與下一步 | `use-creation-steps.js`、既有表單狀態 |
| `CreationPortraitSlot.vue` | 肖像欄五種狀態；發出 `generate` | `ArtworkPreview` |
| `CreationConceptGuide.vue` | 引導欄 | 無 |
| `use-creation-steps.js` | 目前步驟、欄位對步驟的對應、錯誤落點 | 無 |
| `GalleryGenerateDrawer.vue` | 新增選用的 `context` prop | 不變 |

`CreationOverlay.vue` 目前 449 行、樣式 284 行，拆開後每個檔案只負責一個模式。樣式跟著元件拆分。既有 composable 的狀態與處理函式名稱不變，由 `CreationOverlay` 以 props 與事件傳給子元件。

## 11. 無障礙

- 所有文字不小於 `--text-xs`（16px 乘上 `--ui-scale`）。
- 選取、展開、目前步驟、錯誤步驟、肖像狀態都以顏色之外的形狀或文字再表示一次。
- 卡牌牆、步驟列、肖像欄的每個可操作元素都是原生 `button`，有可見的焦點框。
- 肖像狀態變更以 `role="status"` 宣告；表單錯誤維持 `role="alert"`。
- 剪影是裝飾，`aria-hidden`；生成的肖像與預設立繪帶替代文字。
- 動畫全部遵守動態等級設定。

## 12. 錯誤處理

| 情況 | 行為 |
| --- | --- |
| 預設角色沒有官方圖 | 顯示內建預設圖 |
| 圖片載入失敗 | `ArtworkPreview` 的既有降級 |
| 生成請求被拒（驗證失敗、已有進行中的工作） | drawer 保留輸入並顯示既有的「操作未完成」訊息 |
| 生圖服務離線 | 生成按鈕停用，肖像欄顯示原因；建角其餘功能不受影響 |
| 生成失敗 | 肖像欄回到剪影並顯示原因，可再按一次 |
| 繪製中重新連線 | 面板的 `portrait.status` 是伺服器狀態，重新連線後照實顯示 |
| LLM 與生圖服務全部離線 | 預設角色與自由創建完整可用，概念生成照現況顯示不可用 |

## 13. 測試

測試只定義邏輯，使用合成資料，不指名任何出貨的預設角色。

- Vitest：卡牌牆的展開與選擇分離、鍵盤操作、草稿還原；步驟切換、錯誤落點、剩餘點數常駐；肖像欄五種狀態；概念引導的打勾；`GalleryGenerateDrawer` 的 `context`。既有 `creation_overlay.test.js` 與 `concept_fill_navigation.test.js` 依新結構改寫，原有的行為斷言保留。
- Storybook：`Overlays/CreationOverlay` 的 story 依新版面重寫，涵蓋三個模式、三個步驟、肖像欄每種狀態、drawer 開啟、確認畫面、拒絕結果與不可用；fixtures 升到新 schema。
- 伺服器：面板 presenter 與驗證器的新欄位與舊版本拒絕；`creation.portrait.generate` 的驗證、僅限 `creation_pending`、進行中拒絕、服務離線拒絕；啟用不重複生成；重設清除卡片與工作；以預設角色啟用時清除草稿卡片。
- 瀏覽器驗收：1451x790 與 2560x1440 下三個模式都沒有頁面層級的水平捲動；鍵盤完成自由創建；預設角色的展開與選擇；生成肖像從送出到成品出現（使用假的生圖 client）。

## 14. 風險

- **待啟用角色提前取得 `portrait_policy`。** 現況是啟用時才建立。提前建立後，「回滾的建角不留下肖像狀態」這條既有保證的適用範圍要在 `creation-draft-portrait-cleanup` 的規格中重新界定為「回滾的啟用不新增肖像狀態」。
- **八張卡的寬度。** 預設角色上限是 8。卡牌牆在 1451 寬、七倍展開比例下，收合卡約 96px 寬。上限若提高，卡牌牆要改成可橫向捲動的一列，屆時另行設計。
- **立繪構圖差異。** 收合卡以置頂裁切取臉，構圖偏離中央的立繪會切到。官方圖的臉部框選資料已存在於 descriptor，實作時以它定位裁切，沒有框選資料時才用置頂。
