# 前端 Vue SPA 架構（跨變更共用脈絡）

**所屬變更：** A2（`webclient-vue-01-foundation`）撰寫本文件。
**優先順序：** 本文件僅為共用脈絡，變更專屬的 `openspec/changes/webclient-vue-NN-*/design.md` 檔案、[路線圖](../superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md)、`2026-08-02-webclient-ui-design.md` 以及引擎設計文件（`2026-07-29-ai-mud-engine-design.md`）皆具有更高優先順序。
**連結來源：** 於 D1 連結自 `docs/_sidebar.md`。

這是十二個 Vue 遷移變更的單一共用脈絡，讓各變更的焦點設計無需重複說明。

## 背景脈絡：遷移過程必須保留的現狀限制

Elosern 網頁客戶端由 Django 與 Evennia 範本組合 `web/templates/webclient/{base.html, webclient.html}` 提供服務。在 Vue 遷移完成後（C4 切換，並於 D1 定案），`base.html` 會載入 Evennia 提供的 `evennia.js` WebSocket 傳輸層、Vite 建置的 Vue 3 SPA 組合包（`web/static/webclient/app/dist/index.js`）、無相依套件的原生文字主控台（`js/text_console.js`，D10 離線備用機制），以及 `$(document).ready` 的 shim（`js/jquery_ready_shim.js`，提供 evennia.js 在啟動時所需的單一 jQuery 介面）。已停用的舊版 jQuery 與 GoldenLayout 檢視檔案及其無效 CSS 已在 D1 刪除。保留的獨立於 DOM 邏輯位於 `web/static/webclient/js/elosern/*`（協定 reducer、鍵盤路由器、敘事標記管線、指令回顯、局部地圖模型、抉擇點與分頁標籤邏輯、美術焦點）；Vue 應用程式透過 Vite 的 CommonJS 互通機制，經由 `webclient-app/lib/*` ESM 包裝器重新匯出這些邏輯。Vue 的 `AppShell` 掛載至 `#main-sub`；`#messagewindow` 則維持作為降級的文字備用方案。

- **離線不變量：** 頁面絕不為執行期 UI 相依套件發出遠端請求。每個執行期資產均由專案來源端提供服務。
- **獨立於 DOM 的邏輯為單一事實來源。** `js/elosern/*` UMD 模組強制執行精確的 OOB 契約（鏡像對應 `web/webclient/presentation/protocol.py`），並由無相依套件的 `node --test web/static/webclient/js/tests/*.test.js` 閘門涵蓋。
- **傳輸層使用 Evennia 內建機制**（`evennia.js`）：具備身分驗證的 WebSocket puppet、OOB 快照與更新、允許清單動作分派、單一進行中狀態異動（one-mutation-in-flight）、版本／epoch／修訂版本排序，以及重新連線與斷線鎖定語意。
- **瀏覽器測試控管架構：** Playwright 測試會啟動隔離的受管 Evennia 執行期（暫存 SQLite、動態 loopback 連接埠、確定性 fixtures、僅限本機請求）。
- **品質閘門：** `quality-gate.yml` 執行 Node 閘門、嚴格 OpenSpec 驗證、前端閘門（A2+），以及在覆蓋率測量下的分片 Evennia、受管瀏覽器與最上層測試套件。匯總 80% 分支覆蓋率閘門**僅限定於 Python 範圍**（`commands|server|typeclasses|web|world`），不測量 JavaScript。
- **Telnet 等價性**與 **0 釋出使用者**（無需向後相容層或資料遷移）。

經過驗證的單畫面設計稿位於 `docs/design/`（A1），定義了目標資訊架構、情境化模式可見性矩陣、墨夜／印紅設計系統、元件外觀與自我代管字型。

## 決策（D1–D10，摘自原始提案；附註 A2 成果）

### D1 — 框架：Vue 3（SFC）+ Vite
採用 Vue 3 單一檔案元件（SFC），由 Vite 6.x 建置為 ES 模組。開發使用 `pnpm run dev`；正式建置使用 `pnpm run build`。捨棄 React（第二生態系，在此設計導向流程中與 Storybook 契合度較弱）、免建置的全域 Vue（無 SFC 與 HMR），以及繼續停留在 jQuery（無法提供元件優先且可預覽的 UI）。GoldenLayout 的分頁／面板模型由元件樹取代。

### D2 — 透過 CJS 互通重用邏輯，切勿修改原始碼
`js/elosern` 的 UMD 模組由 Vite 組合包透過 `web/webclient-app/lib/*` ES 包裝器匯入（Vite 與 esbuild 的 CommonJS 互通）；原始碼與無相依套件的 Node 閘門完全維持不變，注意 CJS 互通**不會**設定 `window.Elosern.*` 瀏覽器全域變數，那是 C2 瀏覽器橋接器的工作（D9）。**A2 成果：** 互通性已由 Vite 正式建置（`tests/test_frontend_toolchain_contract.py` 中的 `dist/index.js` 檢查會驗證組合包包含保留的 reducer）與 Vitest 包裝器測試所證實。

### D3 — Pinia store 作為檢視狀態的唯一寫入者
Pinia 3 store 是客戶端檢視狀態的唯一寫入者；它將保留的協定 reducer 接入作為核心，接收傳輸事件（OOB 快照／更新、結果、協定錯誤），並透過傳輸層分派動作。元件是只發出使用者意圖事件的被動消費者。

### D4 — 離線自包含組合包與穩定輸出檔名
Vite 會輸出**穩定、非雜湊的進入點名稱**（`webclient/app/dist/index.js` + `index.css`，加上雜湊化的 `assets/` 目錄）至現有的靜態檔案樹中；`base.html` 透過 `{% static %}` 引用。`dist/` **不納入版本控制**，且在**每個提供服務的環境中建置**：CI 的 `frontend` 工作、CI 瀏覽器工作區（兩個雙行程工作目錄），以及 Containerfile 的 `vue-dist` Node 建置階段（進入點隨後執行 `evennia collectstatic --noinput`，重新整理持久化靜態磁碟卷）。建置基礎路徑為 `/static/webclient/app/dist/`，使組合包內的字型 URL 能從來源端正確解析。**A2 成果：** 互斥的 XOR 載入旗標（`webclient_vue_enabled` 脈絡變數；正式環境預設為舊版，`?__vue=1` 供審查使用）每頁僅載入一種檢視堆疊；正式切換於 C4 進行（C3 僅在測試設定中使用該旗標）。`?__vue=1` 刻意不設身分驗證，因為這是私有、單人且未公開釋出的部署，此測試端點僅供離線載入瀏覽器檢查與手動審查，並將在 C4 切換時與旗標一同移除。

### D5 — 保留 DOM 契約掛鉤，其餘使用 data-testid
Vue 應用程式保留 OOB 與瀏覽器契約已相依的識別碼（可聚焦的 `#action-dock`、`action-` 與 `target-` 項目鍵、戰鬥列 id 模式、必要的面板外觀 id）；其他所有外觀均提供穩定的 `data-testid`。這可維持現有的 Playwright 切片及其可追溯性測試正常運作，直到 C4 重新對應其餘部分。

### D6 — 設計稿為具約束力的視覺與 IA 參考
經過驗證的單畫面設計稿（`docs/design/elosern-redesign/`，`index.html` + `REDESIGN.md`）是客戶端視覺語言與資訊架構的**具約束力**參考，其角色超出設計系統來源。其 tokens 位於 `web/webclient-app/styles/tokens.css`（墨夜色盤、單一印紅強調色、金色焦點、排版級距、間距、動態效果），自我代管的子集化 `.woff2` 字型（Iansui、Noto Serif TC、Noto Sans TC unicode 範圍切片，以及作為等寬字體的 Jim Mono TC 切片）位於 `web/webclient-app/fonts/`。`prefers-reduced-motion` 與非純顏色的狀態標記在 token 與工具類別層級強制執行（`.status-marker--*`），維持其可測試性。

### D7 — 測試策略：四道閘門
- **Node 閘門（維持不變，邏輯）：** `node --test web/static/webclient/js/tests/*.test.js`，無相依套件。
- **Vitest（元件）：** `pnpm test`，位於 `web/webclient-app/` 底下的 SFC 掛載元件測試（jsdom、離線）。
- **Storybook 閘門：** `pnpm run build-storybook` + 對照 `web/webclient-app/component-manifest.json` 執行的元件覆蓋率檢查（`pnpm run showcase-coverage`）（B1 植入初始值，B5 凍結）。
- **Playwright（整合）：** 受管執行期瀏覽器套件。
Python 80% 覆蓋率閘門不受影響（JavaScript 不在 Python 原始碼根目錄內）。

### D8 — 儲存庫目錄結構
Vue 原始碼位於 `web/webclient-app/`（SFC、未來的 `stores/`、`lib/` 包裝器、`styles/`、`fonts/`、Vitest 測試、`stories/`、元件清單），Vite 輸出至 `web/static/webclient/app/dist/`（已被 git 忽略）。`package.json`、`vite.config.js`、`vitest.config.js`、`.storybook/` 位於儲存庫根目錄；根目錄套件維持 CommonJS，使 Node 閘門能在 Node 的 `.js = CJS` 語意下繼續執行；應用程式目錄則透過 `web/webclient-app/package.json` 宣告為 ESM。設計稿於 A1 提交至 `docs/design/` 底下。

### D9 — 透過瀏覽器橋接保留公開契約
Vue 應用程式保持相同的穩定公開契約介面：`window.Elosern.Protocol` 與 `.KeyboardRouter` 為匯入的 UMD 模組；`window.Elosern.narrativeInput` 為敘事與抉擇點的附加路徑；`window.Elosern.actions.submit` 為單一動作分派進入點。Phase-0 契約審查（A1）凍結了精確的 façade 介面與 C2 所套用的 `MODIFIED`/`RENAMED` 增量集合。

### D10 — 無外部相依的原生文字備用機制
一個小型的原生 JavaScript 文字主控台（`web/static/webclient/js/text_console.js`，UMD，受 Node 閘門保護）直接綁定至 `evennia.js` 傳輸層，獨立於 Vue 與 jQuery，作為權威文字路徑；在應用程式掛載後隱藏，並在組合包失敗或 OOB 不相容時重新啟動。**A2 探針成果：** `evennia.js` 在所有傳輸路徑上均無 jQuery 相依，**唯獨在其最後載入時的啟動呼叫 `$(document).ready(...)` 例外**；因此 Vue 分支載入了 30 行的 `web/static/webclient/js/jquery_ready_shim.js`（僅限於該單一介面，絕不與完整 jQuery 並存）以取代保留 jQuery。主控台也**將傳輸層的 `text` 行算繪為純文字**（使用 `textContent`，絕不使用 `innerHTML`），使遊戲資料被視為純資料而非標記語言；豐富的 ANSI 與 Evennia 標記算繪將隨主架構波次透過允許清單的 `NarrativeMarkup` 管線提供（審查修正：在該管線進入 Vue 路徑前，不得將伺服器來源內容作為 HTML 注入）。Vue 分支自行開啟通訊端，原廠啟動流程僅呼叫延遲 500 毫秒的 `Evennia.init()`，而舊版 GUI 主架構通常是負責呼叫 `Evennia.connect()` 的元件，因此 `base.html` 會同步執行等冪的 `init()`，綁定主控台接聽器，然後執行 `connect()`。

## 風險與權衡

- **在 Python 優先儲存庫中引入 pnpm 工具鏈** → 僅限開發與 CI 期間使用；根目錄套件保持零執行期 npm 或 pnpm 相依（受契約測試驗證）；Node 閘門保持無外部相依；每個 pnpm 步驟均為明確且不壓制錯誤的 CI 步驟。
- **替換主架構時的瀏覽器測試變動** → D5 掛鉤 + D9 橋接器 + A1 審查凍結了增量集合；行為切片於 C4 重新對應。
- **傳輸層接線錯誤（epoch／修訂版本／重新連線／鎖定）** → C1 重用經過 Node 測試的 reducer 作為 store 核心；C3 與 C4 重新執行現有的 Playwright 驗收測試。
- **提供服務的環境出現 `dist/` 404** → 在 CI 前端工作、兩個瀏覽器工作區以及容器 `vue-dist` 階段中建置；受管瀏覽器檢查（A2）驗證組合包、樣式與字型能從來源端載入，並封鎖所有非本機請求。
- **切換期間存在兩個 DOM 管理器** → 使用 XOR 旗標（絕不同時載入兩者），單一舊版預設值，於 D1 刪除。
- **穩定非雜湊的進入點名稱** → Evennia 自身的 `/static` 服務無需特殊處理；若部署環境後續置於長期快取 `/static` 的反向代理之後，請為 `app/dist/index.js` 與 `index.css` 設定 `no-cache`（或較短的 TTL），或加入建置版本查詢字串，於 C4（正式切換）時再次檢視。
- **持久化 `.static` 磁碟卷殘留過期雜湊資產** → 進入點的 `collectstatic`（未帶 `--clear`）會留下被取代的 `assets/*`；此為無害現象（進入點會引用目前的雜湊）。在確認多副本行為之前，切勿加入 `--clear`。

## 同伴頭像列（Companion portrait lineup）

`CompanionLineup` 取代先前的隊伍快捷列（party quickbar）。隊伍抽屜仍可經角色狀態抽屜開啟。隊伍 schema v2 保留六個列索引鍵；`portrait_ref` 為 null 或 1–32 位 ASCII 十進位數字，僅透過已提交的圖資目錄解析。缺少圖資、沒有預設圖資或被容量上限擠退的圖資，一律改用共用的首字母佔位顯示。呈現端從不建立圖庫紀錄，也從不要求生成圖資。

受控角色立於最右側，隊伍順序向左延伸，所有立繪等比例、全尺寸，站在同一條地面線上。只有水平重疊會被壓縮，包含為清空對話選項所做的壓縮。附身（possession）會交換受控同伴與名冊角色的精確位置。`status.actor.identity` 是受控工作階段角色的有界**字串**識別碼（附身期間也相同）；隊伍識別碼仍是安全整數，在此處 join 時正規化為十進位字串。其他狀態欄位維持以擁有者為索引鍵的混合契約。

附身期間，名冊仍以已驗證 puppet 所屬帳號為根。即時綁定的擁有者必須屬於該帳號；A 維持名冊現行狀態並保留既有頭像與待處理標記，B 絕不會變成帳號角色。名冊切換鎖定與原因仍依 B 的戰鬥述詞判定，而非 A 的；附身本身不會新增切換鎖定或承載欄位。

同伴沿用 StageActor 的傾聽變暗機制。身分符合已提交對話主持者、且既有說話者訊號為 `host` 的同伴，會暫時取得最高的繪製 z 層級與完整亮度。說話者變更、離開對話、附身與數量變更都會讓 z 層級回到基準，且不會移動立繪。只有受控立繪會收到戰鬥節拍。關閉動態與 `prefers-reduced-motion` 下，這些狀態變更仍會生效，只是沒有動畫。已存在於已提交隊伍／受控陣容中的對話主持者不會在 actor-right 重複出現；非隊伍主持者保留既有頭像與動態，名牌、分頁與焦點不變。敵人陣容、生命狀態 dock 與地點卡片欄維持不變。

探索模式的動詞卡沿用同一個以立繪為準的身分 join。成員判定只讀 `CompanionLineup` 實際描繪的那份有界清單（`displayedLineup`，上限為 `COMPANION_LINEUP_MAX`），並以 `lineupSlotByIdentity` 依 `String(identity)` 比對，比對前先擋掉 null。數字隊伍 identity 與有界字串狀態 identity 因此在同一次比對中相等；頭像為 null 或名稱相同都不影響判定，而被上限擠退的原始隊伍列、名稱、圖資鍵與圖資可用性都不得作為成員依據。比對到 slot 時只把該 slot 原生的數字 identity 傳入既有的同伴說話訊號，字串正規化僅用於比對本身。

被選取的同伴沿用同一組傾聽變暗機制：該立繪取得高於所有基準的繪製 z 層級並失去聽眾變暗，其餘非受控立繪維持基準 z 與聽眾變暗，受控立繪則永遠不會被當成聽眾，自身的變暗與節拍語意不變。同一身分不會在 actor-right 重複出現；卡片開啟期間該身分進入或離開排隊時，代表權在同一筆提交內轉移，右側不播放離場動畫，因此不會留下同一人的第二個立繪。焦點狀態全由已提交狀態推導，返回、Escape、查看、離開房間、移動、面板不可用、模式切換、epoch 重置與隊伍或附身變更都會回到當前基準，沒有任何依賴轉場結束的延後清除。這份推導歸 `AppClient.vue` 所有，卡片的生命週期仍由 store 既有的提交時結算負責。

探索面板 schema v4 為每個在場實體與互動目標附上一個 nullable `portrait_ref`，形狀與隊伍的圖資目錄鍵完全相同（null 或 1–32 位 ASCII 十進位數字，驗證器絕不塑形或跨面板 join）。呈現端只對同時滿足兩個條件的身分發出參考：屬於目前 `art` 面板圖資目錄的成員，且其自身 canonical 解析帶有 `runtime`／`official` 來源的真實媒體 URL；被容量上限擠退、目錄缺席或只有佔位／剪影者一律為真實的 null。`art` 面板本身的成員資格、上限與臉部裁切不變。此契約為一次性切換：伺服器與前端組合包必須一同部署，正常重連即取得新快照，沒有相容適配層或資料遷移。

因為前一段的 nullable 是刻意的真實值，待生成中的肖像完成時，探索描述子不會自己變新。圖像完成推播因此多帶一個有界的同伴面板：當剛重繪的**目前肖像目錄**引用該完成主體、且工作階段處於探索模式時，同一個 affected-panel `ui_update`（同一個 revision，不額外推播、不廣播全量快照）內一併附上新鮮重繪且可用的 `exploration` 面板，讓原本為 null 的描述子直接取得真實目錄鍵，玩家不需要再做任何遊戲動作或焦點動作。只有場景引用該主體、工作階段不在探索模式、或探索面板不可用時，都不附加探索面板（場景完成不得擴大推播範圍）；離開房間或已離開的主體仍由重新推導擋下。前端只讀已提交的目錄鍵，絕不自行合成主體鍵或媒體 URL。

## Store 切片契約（固定供 C1 與 Wave B 使用）

Wave B 依此結構建置離線元件；C1 進行實作，雙方必須鎖定相同的介面：

- **單一 Pinia store 擁有檢視狀態**（`web/webclient-app/stores/`）。其核心為匯入的協定 reducer（`lib/protocol.js`，絕不另外手寫第二個 reducer）以及用於焦點狀態的匯入鍵盤路由器。
- **不可部分發布，僅讀取已認可狀態：** store 僅在完成完整的 reducer 交易後才發布新的不可變狀態快照；元件絕不讀取處理中的暫存狀態。每個 OOB 訊息（快照／更新／結果／協定錯誤）均先由 reducer 套用；發布是觀察者能看見該狀態的唯一時刻。
- **檢視切片：** 元件從 store 的公開 getters 讀取狹窄的衍生切片（例如 `context_actions` 面板、敘事日誌、傳輸鎖定狀態）；元件發出使用者意圖事件（動作提交、文字輸入），store 透過單一分派進入點路由它們，僅限分派，且維持單一進行中狀態異動。
- **事件進入，意圖輸出：** store 訂閱傳輸事件頻道（由 C3 綁定）；元件絕不直接訂閱傳輸層。
- Wave B 元件的 Storybook stories 會接收作為純 fixture 物件的切片（與 store 的 getters 回傳形狀相同），讓離線 stories 與線上檢視不會脫鉤。

## 跨變更執行機制（路線圖摘要）

- 每個變更約需 1 個工作天，各自能獨立通過測試，並依拓撲順序落地；**合併與封存嚴格遵循拓撲順序**（絕不在同一作用中檔案上有兩個寫入者，絕不同時封存相同能力的兩個變更）。
- `webclient-vue-application` 與 `webclient-component-showcase` 於 B1 作為全新能力新增（ADDED），並由後續變更修改（MODIFIED）。
- 元件覆蓋率清單持續擴充：B1 植入初始值，B2 至 B4 擴充，B5 凍結。
- 真實資料範圍：任何元件不得呈現缺乏後端 OOB 讀取模型（允許清單）或文字串流支援的資料；延後實作的外觀（隊伍面板、親密狀態、完整背包、事件日誌 toast）在 B5 被明確斷言為不存在。

## 圖片載入與資源結果的單一擁有者（unified-image-loading-core）

所有需要多來源排序的圖片介面（圖庫編輯器、立繪、頭像、場景、夢境）共用同一條載入生命週期。這是**唯一**的載入／資源／結果擁有者；後續的圖庫、立繪、場景整合只擴充它，不另寫第二個載入器。

- **`lib/image-attempts.js`（純 reducer）** 擁有一次解析中的嘗試順序、僅已到達的失敗、資源身分／版本的與安全耗盡。輸入是**正規化的內部載入請求**，不是任何面板線路形狀：
  `{ subjectId, epoch, attempts, terminal }`，其中每個 image 嘗試攜帶
  `{ source_id, rank, resource }`，而 `resource` 為
  `{ resource_id, version, url, origin, geometry }`；fault 嘗試攜帶 `{ source_id, rank, reason }`。
  優先序是穩定的 `rank`，**絕不是**陣列索引：reducer 先排序再依資源身分／版本去重（保留最高優先者），因此重複的資源或終端不可能改變優先序或遮蔽較高優先的候選。耗盡一定終止並保留已到達的失敗，沒有遞迴或無限回退。
- **`composables/useImageAttempts.js`（本地驅動）** 綁定作用中的主體／epoch／嘗試權杖，以實際 DOM 載入／解碼（真實 `naturalWidth`/`naturalHeight`）觀測成敗，拒絕過期回呼，並在替換或卸載時清除。它把已解碼的位元組重用在**僅幾何變更**的修訂上：重啟身分是有序的解析事實加上主體／epoch 與可用性，幾何不在其中，因此幾何修訂不發出新請求、不改變來源鍵、也不交叉淡入。相同修訂重繪不重試，已到達的失敗維持不變；新的資源版本／鍵才會重新解析。
- **可用性輸入** `{ state: ready|expected_absent|failed, view_subject_id }` 與描述子分離：`failed` 讓本地 `panel_unavailable` 持續，並使過期回呼與原始儲存資格失效；`expected_absent` 與載入中不得使用錯誤樣式，也不得聲稱生成正在進行。
- **公開結果** 為 `{ selected, reachedFaults, phase, dimensions }`；`selected` 攜帶實際成功的資源、穩定的 source_id/rank 與觀測到的自然尺寸。消費者可以另外持有顯示內容，但不能自行設定載入成功或重設 reachedFaults。
- **`ArtworkFailure.vue`／`ArtworkAlpha.vue`** 是共用的呈現原語：失敗標記持續、非模態且具鍵盤／輔助技術說明；alpha 填色只在同一 URL 已被觀測成功後才上色，因此缺席的資源不可能被畫成不透明矩形。
- **內部請求與標準線路的區別：** 本變更讓既有 gallery v2 編輯器**只**以它已提交的單一原始身分／URL／幾何建構一個 rank-10 原始請求（`terminal: null`）——不製造主體解析、不接受多種線路形狀、也不新增面板欄位。gallery v3 切換（`unified-gallery-image-contract`）已把該呼叫端輸入換成後端描述子（見下一節）；同一個資源驅動不變。

## 作品描述子與圖庫 v3 的單一來源（unified-gallery-image-contract）

圖庫（以及其後的立繪／場景／頭像）不再各自解讀線路形狀：**一個**標準描述子攜帶全部圖像事實，**一個**共用綁定把它餵進上面的載入生命週期。v2 的扁平列欄位（`url`／`face_rect`／`stage`）已移除，兩個驗證器都會拒絕它們，沒有新舊雙形狀或轉接器。

- **描述子** `{subject_id, revision, generation_subject, generation_state, attempts, terminal, retention_sources}`：
  `subject_id` 為穩定的主體身分（雜湊前綴加精確圖像鍵，128 字元上限）；
  `revision` 為有序來源／失敗事實、來源版本、幾何、綁定／存取適用性與生成事實的 64 字元摘要；
  `generation_state` 為 `missing|pending|done|failed`（既有 `in_progress` 正規化為 `pending`），描述已記錄的生成狀態而**與可見來源無關**——官方候選可在生成為 pending／failed 時呈現，且不得抹除已記錄的失敗。
  `attempts` 最多 16 筆：image 為 `{type, source_id, rank, resource}`，fault 為 `{type, source_id, rank, reason}` 且**永不**帶 URL。`resource` 為 `{resource_id, version, url, origin, geometry}`，`origin ∈ runtime|official|bundled_official|silhouette`，URL 限同源且各 origin 有各自上限（runtime／silhouette 129；official／bundled_official 256），並只接受單一封閉的 `?v=<sha256>` 快取版本查詢。`geometry` 固定為 `{image_size, face_rect, stage, aspect_ratio}`，不適用者為 `null`。
  `terminal` 為 `null` 或 `{kind: alpha_mask|scene_image, source_id, rank, resource}`：圖庫列一律附帶主體已提交的剪影 alpha 遮罩（rank 100），其資源與嘗試中的候選去重。
  `retention_sources` 為最多 16 筆 `{source_id, token}`：token 涵蓋主體／生成主體與當前授權的綁定／存取適用性，**不含**幾何與 pending／failed 重新生成狀態，因此重新生成不會撤銷仍有效的既有輸出；輸出已知遺失或來源被拒時不授權保留。
- **來源順序**由穩定 `rank` 決定，與陣列索引無關（圖庫：精確原始 10、alpha 終端 100；立繪：綁定卡 10、個人官方選取 20、紀錄預設 30、經典資產 40、官方預設 50、alpha 終端 100）；fault 與其候選共用同一 `source_id`/`rank`，新增 fault 永不改變來源優先序。
- **立繪來源的單一擁有者（unified-portrait-source-resolution，僅後端準備）：** `world/art/presenter.py` 的 `describe_portrait`／`describe_entity` 是立繪來源順序的唯一決定者，其來源身分為 `portrait.bound:<image-id>`、`portrait.personal:<official-identity>`、`portrait.default:<image-id>`、`portrait.classic:<generation-subject>`、`portrait.official:<kind>/<key>` 與 `portrait.alpha:<key>`；實體的官方參照是**一個**來源位置，因此已提交的預設圖與該來源的所有 fault 共用同一 `source_id`／`rank`。明確的個人選取或紀錄預設若無法解析，其有界 fault 留在原位置、先於其替代者，且已存偏好永不被刪除；立繪描述子不帶 `retention_sources`（保留授權屬後續線路擁有者）。`describe_portrait`／`describe_entity` 與（僅供場景的）扁平投影**同一次**列舉結果，因此不存在第二個選擇器；立繪線路已在 `unified-portrait-image-contract` 完成描述子切換：art 面板 v3 的 `portrait_catalog` 值恰為 `{artwork, context}`（完整描述子加有界的顯示 context），roster v3 的每列 `portrait` **就是**描述子本身，party／exploration 的 `portrait_ref` 則改由**成員資格**（`world.rules.art_view` 的當前有界視圖）決定而不再看真實影像是否解析——已收錄的主體即使只有輪廓也保有參照，`null` 只保留給未被收錄者，因此沒有第二種形狀、沒有欄位複製、也沒有相容層。
- **`composables/useArtwork.js`** 是唯一的面板描述子綁定：它把描述子轉成正規化載入請求（epoch 為穩定主體身分，因此**僅幾何變更**的修訂仍重用已解碼位元組），並轉發驅動的 `{subjectId, revision, phase, selected, reachedFaults, exhausted}` 與元素處理器。消費者可以保留自己的顯示內容，但不能設定載入成功或清除已到達的失敗。
- **`lib/artwork.js`** 提供唯一的可用性翻譯 `artworkAvailability({panel, required, hasReference, artwork, viewSubjectId})`：非必要介面或刻意無參照的可用面板為 `expected_absent`；必要面板缺席／`available:false`／懸空參照為 `failed`；`ready` 需要真正的描述子。不可用面板**永不**被讀成生成進度。同一模組亦提供描述子選擇器（最高優先 image 候選、其幾何、終端 URL）。
- **`components/ReferenceArtwork.vue`** 是共用的**立繪**框：同一份描述子載入狀態餵養兩種位置——舞台（`stage`：contain、貼地、描述子自帶的擺放三元組）與框景（cover：共用 face-rect 裁切）。**兩種圖像版面都允許**描述子自帶的 alpha 終端：沒有真實立繪成功時由共用的 `ArtworkAlpha` 上色，且只在同一資源本身載入成功後才填色，版面模式永不關閉輪廓政策。已到達的失敗維持持續、可存取的本地標記，並以辨識文字加說明取代實心矩形；真實幾何與輪廓幾何各自獨立，僅幾何變更的修訂就地套用而不重掛。
- **`components/AvatarArtwork.vue`（unified-avatar-rendering）** 是唯一的**微型頭像**渲染器：頂欄角色切換器的收合縮圖與每一列、presence medallion、隊伍抽屜的同行列，以及戰鬥參與者列全部使用它。它消費同一份描述子，但套用頭像自己的政策——載入請求**不含**終端圖像（剪影不是頭像，絕不請求 `/art/defaults/*`）、裁切跟隨**實際成功**候選自己的 `face_rect`（不是最高優先候選的，也不受描述子 `stage` 三元組影響）、沒有真實影像時由 `components/character-identity.js` 的 `portraitGlyph` 畫出**修剪後名稱的第一個字素叢集**（空名稱則為中性的文字符號，絕不露出孤立代理項、也不切開組合序列）。已到達的失敗維持持續的緊湊標記：獨立表面（隊伍列、戰鬥列）的標記本身是**可聚焦的按鈕**，其無障礙名稱即整句有界說明；被別人的可聚焦控制或 roving-tabindex 複合元件包住的表面（切換器按鈕、presence rail 的 listbox）則讓宿主控制以 `aria-describedby` 指向同一句說明，頭像本身不再嵌套第二個可聚焦控制。期待中的缺席與載入中不帶錯誤樣式。
- **`components/ArtworkPreview.vue`** 是唯一的預覽位置：它渲染精確原始；原始失敗時由描述子的終端 alpha 遮罩接手，且**只在同一遮罩資源本身載入成功後**才由 `ArtworkAlpha` 上色（失敗不會留下實心矩形）。已到達的失敗維持持續、可鍵盤存取的標記，且永不改變卡片狀態、永不切換原圖、永不啟用替代編輯。預覽**不**顯示載入中文字。
- **編輯器**（`GalleryFaceRectModal`／`GalleryStageTransformModal`）消費同一描述子，但其載入請求**不含**終端圖像（`useArtwork(..., {terminal: false})`）：剪影不是可量測的幾何參照，因此原始載入失敗時編輯器保持不可儲存。
- **圖庫線路 v3：** 卡片列為 `{image_id, status, label, artwork, is_default, chips, requested_fields, binding_present, created_at}`，官方列為 `{identity, artwork, is_current, is_catalog_default}`。可讀卡片若輸出遺失或被拒，仍以**該精確卡片**的身分保留為 rank-10 具名 fault 且無 URL（不再略過、也不以其他卡片替代）；pending／failed 列則完全不含圖像（無候選、無幾何、無終端），只帶真實的生成狀態。

## 兩個原始編輯器的儲存資格（unified-gallery-original-editors）

臉部框選與比例調整共用同一條資格規則，實作於
`composables/useOriginalEligibility.js`；兩個編輯器各自把自己的驅動結果餵進去，
並把答案交給自己的儲存處理器與停用狀態。

- **證明對象是驅動「實際觀測到」的那個原始。** 資格證明取自驅動自己成功解析出的觀測
  （`lib/artwork.js` 的 `artworkSelectedIdentity`：驅動 `selected` 的來源層、資源身分與
  版本），**不是**編輯器當下的描述子；同一模組的 `artworkOriginalIdentity` 以同一組事實
  描述描述子所稱的精確原始，兩者必須相等。因此即使描述子已被替換、而某個仍在飛行的元素
  才剛解碼成功，記下的仍是「真的解碼了哪一個」，不可能借用當前描述子的身分。
  描述子端則要求**當前**描述子仍攜帶同一個原始，這補上**同一個 tick** 就失效的那一半
  （不必等驅動的前置 flush 重啟完成）；相對地，**僅幾何變更**的修訂、以及相同事實的
  無害重繪，都保留已解碼的憑證與玩家草稿。身分刻意不含描述子修訂（它涵蓋幾何，
  loading-core 會刻意重用已解碼位元組）也不含主體（列的身分已內含在來源層與資源路徑中，
  而派送的主體另由已提交面板提供）。剪影、其他卡片、場景底圖與成人比例尺永不進入這個證明。
- **只有在解碼成功且有可用尺寸時才可儲存。** `decoded` 需要驅動回報 `success`
  且觀測到的自然尺寸為正的整數；載入中或失敗時仍可用數值編輯草稿，但**不**會派送。
  派送內容永遠只有被編輯的那個元件（`{face_rect}` 或 `{stage}`），主體／卡本身分由
  `GalleryPanel` 以已提交身分補上。
- **載入中與失敗是不同的可見狀態。** 兩者各有自己的 zh-TW 說明；原始失敗時破損的
  原始與方形裁切預覽 `<img>` 一併移除，並保留持續、非模態、具 `role="status"`
  的在地失敗標記（`ArtworkFailure`）。已到達的失敗不會被較低來源的成功抹除。
- **成人比例尺是獨立的被觀測資源。** 比例調整為固定的 `/art/defaults/man.webp`
  另開一條生命週期（`components/adult-reference.js`）：其主體與資源都不在卡片
  的 `attempts`／`terminal` 內，其尺寸**永不**成為原始尺寸、也永不授權儲存。
  它維持既有的靜態 CSS 遮罩外觀，並以一個永不繪製的探針 `<img>`
  （與 `ArtworkPreview` 的剪影探針同一手法）承載自身的載入／錯誤訊號；比例尺失敗時
  遮罩移除，顯示自己的在地失敗指示，而健康的原始仍是唯一可儲存的目標
  （原始失敗＋比例尺健康時，仍**不**可儲存）。

## 場景表面：描述子、保留與臨時背景（unified-scene-rendering）

場景背景不再由元件自行解析線路，也不再自帶解碼器或失敗網址快取：`art`
面板 v4 的 `scene` 恰好是 `{archetype, label, alt, artwork}`，其中
`artwork` 是場景解析出的標準描述子（邏輯地點身分、來源鏈的排序候選與已觸
及故障、獨立的生成事實、允許的終端與保留授權）。`SceneBackdrop` 只透過
`composables/useArtwork.js` 消費它，並且只決定「畫面上是什麼」：

- **保留內容**由 `lib/scene-artwork.js` 的純規則決定：只有當新描述子的
  `subject_id` 與 `generation_subject` 與保留項目相同、且
  `retention_sources` 仍帶著同一組 `{source_id, token}` 時才保留；較低優先
  序的成功替補（例如 bundled 圖）永遠不會取代已保留的良好生成圖，較高或同
  優先序的替換才會接手。每一次提交都會在讀取時重新驗證保留項目，因此搬家、
  綁定移除、授權撤銷或來源失效都在同一次提交內丟棄像素。
- **臨時背景**（provisional）是該場景自己的 bundled／terminal 資源，由同一
  個載入核心的 `options.provisionalSource` 在較高優先序來源仍在載入時於排
  序之外抓取：它的成功只是暫時顯示，失敗維持潛伏直到游標走到該位置才成為已
  觸及故障，並且在該位置直接重用、不重複請求（核心在元素出現前就登記
  `loading` 的所有權）。排序解析一旦結算，臨時元素即退休。
- **同場景替換**才會有淡入淡出，且由 `SceneBackdrop` 以單一動作權杖的時長驅
  動（`:css="false"` 加上明確的進入／離開鉤子）；搬家、授權失效與 `off` 動態
  層級都在提交的同一影格完成切換，舊地點的畫面絕不會跨場景殘留。
- 載入核心的解析事實（`factsKey`）改為**同步**重啟，因此任何同一次提交的消費
  者讀到的是已清空的選擇，不會把本次提交的事實與上一次的結果配對。

相關閘門：`pnpm test`（含 `tests/scene_retention.test.js`）、Node 閘門的
`protocol_art.test.js`，以及受管理的 `UnifiedScenesBrowserTest` 兩個旅程。

## 受指揮成員與草稿進度（webclient-party-command-selection）

戰鬥指令卡現在以「受指揮成員」為單位，而不是以登入角色為單位。`combat_menu.js`
的 `actorItems`／`progressLine`／`commandEnvelope` 把 v7 面板的
`actors`／`choices`／`draft` 轉成三個事實：

- **成員框架**（`combat.actor`，`menus.actor`）：依伺服器盟軍順序一列一名成員，
  標籤取該成員的顯示名稱（同名者附帶 session token），說明文字依權威草稿顯示
  「已確認」／「待選擇」，或伺服器撰寫的重選原因（`draft.reselection_reasons`）；
  不可指揮的成員保留自身原因並停用。
- **進度列**：卡片外框內的單行 `combat-actor-line`（`store.view.combatProgress`），
  顯示受指揮成員與已確認／需求數量；其 `變更成員` 按鈕是卡片層級的控制項，
  **不是**新的根清單列（根清單恰為 attack／skills／items／bag／defend／dodge／taunt／
  retreat／surrender；兩列出場操作見「整隊撤退與投降」一節）。
  開啟成員框架時會把 DOM 焦點交還 dock，按鈕本身於框架掛載後消失。
- **守門信封**：`combat.command` 的 `session_id`／`round_revision`／`draft_version`／
  `actor_id` 在送出當下由已提交面板讀取（絕不沿用舊版本），技能本體維持原本
  的內部酬載形狀（`{kind: "skill", payload: {...}}`）。

流程規則：

- 選擇成員只發一次唯讀 `combat.actor_choices {session_id, round_revision, actor_id}`，
  待該成員的 `choices` 提交後才回到根目錄重新開始技能／分類／威力／目標流程；
  不會樂觀顯示上一位成員的目錄。
- 受指揮成員變更（切換、重連、伺服器改派預設成員）會丟棄未確認的技能／威力／
  目標選擇並取消待答警告，但**不碰**伺服器已確認的草稿條目。
- 非最終的接受結果（`draft_saved`）會觸發一次唯讀查詢，指向
  `required_actor_ids ∩ needs_selection_ids ∩ commandable` 中第一個仍待指令的成員；
  此查詢在視圖發布之後發出（信封帶到最新 epoch／revision），且是一次性關聯
  （generation／session／requestId），重連或重複觀察結果都不會重播意圖。無論由成員框架
  或自動前進所發起，成員切換都收斂為恰好一層根目錄。
- SELF 的舞台位置綁定受指揮成員的人物（同伴亦然），跨陣營確認的目標集合與措辭
  也以受指揮成員為準；玩家彼端的身分仍只用於生命值 dock 與控制員判斷。

相關閘門：`pnpm test`（`tests/store/party_command_selection.test.js` 等）、Node 閘門的
`combat_menu.test.js`，以及受管理的 `test_actor_selector_chrome_returns_to_root_without_a_command`。

## 同伴道具與基本戰術（webclient-party-items-tactics）

道具與 Defend／Dodge／Taunt 都只讀受指揮成員自己已提交的 `choices`；全域背包、
共享隊伍背包與玩家彼端身上的物品都不參與選單內容。

- **`combat.items`（`menus.items`）**：一列一件該成員的可使用庫存，標籤為
  `<名稱> ×<數量>`，說明欄是伺服器撰寫的效果摘要，不可用的一列帶著自己已提交的
  `reason`（焦點可及、說明可讀、絕不送出）。根目錄的 `道具` 列僅在該成員確實持有
  庫存時啟用，否則停用並附本機能力原因（`no_usable_item`）。
- **`combat.item`（`openItem`）**：單件道具的檢視／目標框架。`target_spec` 為
  `none`／`self` 時是一列確認（`none-confirm`／`self-confirm`，不帶目標欄位，伺服器
  綁定受指揮成員）；`single` 時沿用舞台單體目標步驟（`combat.item` 屬
  `STAGE_TARGET_SOURCES`），每列酬載為 `{item_key, target_id}`。玩家端送出的命令是
  封閉 v7 線路聯集 `{kind: "item", payload: {...}}`；面板回顯的草稿條目另有自己的
  `tactical`／`tactical_key` 拼法，兩者不可互換。
- **`combat.tactic`（`tacticMenu`）**：Defend／Dodge 是一列 `確認<名稱>`，送出
  `{kind: "tactic", payload: {key}}`（零資源、送出當下不施加任何效果）；Taunt 是
  伺服器列出的存活敵軍單體目標步驟，酬載 `{key: "taunt", target_id}`。線路種類字面
  是 `tactic`（`web/webclient/actions/combat_actions.py` 的 `COMMAND_KINDS`）。
- **跨陣營警告**：`askCrossSide(kind, form, focusKey, command, display)` 依命令種類
  取用技能或道具已提交的 `hostile`／`beneficial` 與目標集合；蓄意傷害友方或增益敵方
  的道具與技能一樣先問一次。持有中的問題綁定成員、session／round／draft 版本與框架
  主體，任何一項變動（含道具消失或停用、裝備變更導致重新提交）都直接取消且不送出。
  基本戰術無極性事實，永不觸發此問題。
- **戰鬥中的背包**：`InventoryPanel` 的 `combat` 屬性為真時，啟用中的 `inventory.use`
  立刻發出意圖、不開本機確認視窗；`composables/intents.js` 把它轉成
  `store.useCombatItem(item_key)`，也就是與 `道具` 列相同的檢視／目標／送出流程，
  因此戰鬥中永不送出無成員的 `inventory.use`。該成員沒有這件物品時只留一則可見提示。
  檢視與本人裝備切換維持免費、原樣。
- **重新驗證**：框架內容在每次讀取時由已提交面板重解；道具消失或停用時解析為
  `unresolvable` 標記並彈回上一層，裝備變更後不需要任何客戶端補救。

相關閘門：`tests/store/party_items_tactics.test.js`、`tests/world/inventory_panel.test.js`、
Node 閘門的 `combat_menu.test.js`，以及受管理的
`test_item_and_tactic_choices_send_the_actor_command`。

## 整隊撤退與投降（webclient-party-exit-confirmation）

撤退與投降是**隊伍範圍**的操作，不是受指揮成員的個人動作：任何成員的根目錄（含
recovery 根目錄）都能開啟，且不要求該成員可被指揮。兩者共用同一個伺服器綁定的確認
契約，沒有相容傳輸。

- **根目錄兩列**：`撤退`／`投降`（`combat_menu.js` 的 `partyExitRow`）恆為啟用，本身
  不帶 action id；啟動只發出一次唯讀的 `combat.exit_prompt`
  `{session_id, round_revision, operation}`（送出當下由已提交面板讀取）。退役的
  `combat.flee`／`combat.forfeit` 生產者與其本機二次確認框架（`menus.forfeit`、
  `combat.forfeit` descriptor、DockMenu 的 `confirm` 警告文案）一併移除。
- **共用確認契約**：`CombatMenu.partyExitPrompt(operation, data)` 驗證伺服器
  `party_exit_prompt` 結果的四個欄位（`operation`／`confirmation_token`／`scope=party`
  ／`consequence`），產生唯一的問句（`確定要全隊撤退？`／`確定要全隊投降？`）、
  伺服器撰寫的後果全文與 token；任一不符即 `null`（不開卡、無可確認項）。
- **安全預設的視窗**：`AppClient` 在 `choices` 錨點以既有的 `QuestionCard`（caution、
  初始焦點 `否`、`no-while-locked`）呈現；`view.partyExitConfirm` 只帶
  `{operation, label, question, consequence}`。卡片開啟時 dock 為 `inert`、舞台命中區
  與 dock 按鍵全部失效（`#action-dock` 變暗、`data-party-exit-open`），且
  `onRouterEvent`、`stageTargetPointer` 都不動作。
- **取消**：`否`／✕／Escape 走 `cancelPartyExit()`，只丟棄本機提示——不推任何框架、
  不送出任何 `ui_action`、不推進時間，焦點回到開啟它們的那一列；伺服器草稿與既有
  草稿條目完全不動。
- **確認**：`confirmPartyExit()` 只在持有提示且無進行中 mutation 時，送出恰好一次
  `combat.exit_confirm`（`session_id`／`round_revision`／`operation`／
  `confirmation_token`）；卡片立即關閉，重連或重播結果都不會重送同一個 Yes，
  也不保留可重試的副本。成功的撤退失敗／成功／投降狀態由後續已提交面板（含
  canonical 回合與 terminal 快照）取代視圖，客戶端不自行推算搬遷或治療。
- **失效**：提示綁定 `session_id`／`round_revision`／transport generation／epoch。
  任一替換、斷線、模式變更或回合播放中的提示一律取消且不重試；同回合的無關
  resync（token 仍有效）保留提示。
- **舊路由**：`combat.flee`／`combat.forfeit` 僅剩伺服器端既有的拒絕與淘汰紀錄；
  客戶端不再有任何生產者，`Elosern.actions` 之外的程式路徑也無法確認沒有 token 的
  操作。

相關閘門：`tests/store/party_exit_confirmation.test.js`、Node 閘門的
`combat_menu.test.js`（含 `partyExitPrompt` 契約）、以及受管理的
`test_party_exit_prompt_confirm_sends_one_exit_confirm` 與
`test_party_exit_cancel_keeps_the_draft_and_the_clock`。
