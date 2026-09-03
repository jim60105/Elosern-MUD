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
採用 Vue 3 單一檔案元件（SFC），由 Vite 6.x 建置為 ES 模組。開發使用 `npm run dev`；正式建置使用 `npm run build`。捨棄 React（第二生態系，在此設計導向流程中與 Storybook 契合度較弱）、免建置的全域 Vue（無 SFC 與 HMR），以及繼續停留在 jQuery（無法提供元件優先且可預覽的 UI）。GoldenLayout 的分頁／面板模型由元件樹取代。

### D2 — 透過 CJS 互通重用邏輯，切勿修改原始碼
`js/elosern` 的 UMD 模組由 Vite 組合包透過 `web/webclient-app/lib/*` ES 包裝器匯入（Vite 與 esbuild 的 CommonJS 互通）；原始碼與無相依套件的 Node 閘門完全維持不變。注意事項：CJS 互通**不會**設定 `window.Elosern.*` 瀏覽器全域變數，那是 C2 瀏覽器橋接器的工作（D9）。**A2 成果：** 互通性已由 Vite 正式建置（`tests/test_frontend_toolchain_contract.py` 中的 `dist/index.js` 檢查會驗證組合包包含保留的 reducer）與 Vitest 包裝器測試所證實。

### D3 — Pinia store 作為檢視狀態的唯一寫入者
Pinia 3 store 是客戶端檢視狀態的唯一寫入者；它將保留的協定 reducer 接入作為核心，接收傳輸事件（OOB 快照／更新、結果、協定錯誤），並透過傳輸層分派動作。元件是只發出使用者意圖事件的被動消費者。

### D4 — 離線自包含組合包與穩定輸出檔名
Vite 會輸出**穩定、非雜湊的進入點名稱**（`webclient/app/dist/index.js` + `index.css`，加上雜湊化的 `assets/` 目錄）至現有的靜態檔案樹中；`base.html` 透過 `{% static %}` 引用。`dist/` **不納入版本控制**，且在**每個提供服務的環境中建置**：CI 的 `frontend` 工作、CI 瀏覽器工作區（兩個雙行程工作目錄），以及 Containerfile 的 `vue-dist` Node 建置階段（進入點隨後執行 `evennia collectstatic --noinput`，重新整理持久化靜態磁碟卷）。建置基礎路徑為 `/static/webclient/app/dist/`，使組合包內的字型 URL 能從來源端正確解析。**A2 成果：** 互斥的 XOR 載入旗標（`webclient_vue_enabled` 脈絡變數；正式環境預設為舊版，`?__vue=1` 供審查使用）每頁僅載入一種檢視堆疊；正式切換於 C4 進行（C3 僅在測試設定中使用該旗標）。`?__vue=1` 刻意不設身分驗證，因為這是私有、單人且未公開釋出的部署，此測試端點僅供離線載入瀏覽器檢查與手動審查，並將在 C4 切換時與旗標一同移除。

### D5 — 保留 DOM 契約掛鉤，其餘使用 data-testid
Vue 應用程式保留 OOB 與瀏覽器契約已相依的識別碼（可聚焦的 `#action-dock`、`action-` 與 `target-` 項目鍵、戰鬥列 id 模式、必要的面板外觀 id）；其他所有外觀均提供穩定的 `data-testid`。這可維持現有的 Playwright 切片及其可追溯性測試正常運作，直到 C4 重新對應其餘部分。

### D6 — 設計稿為具約束力的視覺與 IA 參考
經過驗證的單畫面設計稿（`docs/design/elosern-redesign/`，`index.html` + `REDESIGN.md`）是客戶端視覺語言與資訊架構的**具約束力**參考，不只是設計系統的來源。其 tokens 位於 `web/webclient-app/styles/tokens.css`（墨夜色盤、單一印紅強調色、金色焦點、排版級距、間距、動態效果），自我代管的子集化 `.woff2` 字型（Iansui、Noto Serif TC、Noto Sans TC unicode 範圍切片）位於 `web/webclient-app/fonts/`。`prefers-reduced-motion` 與非純顏色的狀態標記在 token 與工具類別層級強制執行（`.status-marker--*`），維持其可測試性。

### D7 — 測試策略：四道閘門
- **Node 閘門（維持不變，邏輯）：** `node --test web/static/webclient/js/tests/*.test.js`，無相依套件。
- **Vitest（元件）：** `npm test`，位於 `web/webclient-app/` 底下的 SFC 掛載元件測試（jsdom、離線）。
- **Storybook 閘門：** `npm run build-storybook` + 對照 `web/webclient-app/component-manifest.json` 執行的元件覆蓋率檢查（`npm run showcase-coverage`）（B1 植入初始值，B5 凍結）。
- **Playwright（整合）：** 受管執行期瀏覽器套件。
Python 80% 覆蓋率閘門不受影響（JavaScript 不在 Python 原始碼根目錄內）。

### D8 — 儲存庫目錄結構
Vue 原始碼位於 `web/webclient-app/`（SFC、未來的 `stores/`、`lib/` 包裝器、`styles/`、`fonts/`、Vitest 測試、`stories/`、元件清單），Vite 輸出至 `web/static/webclient/app/dist/`（已被 git 忽略）。`package.json`、`vite.config.js`、`vitest.config.js`、`.storybook/` 位於儲存庫根目錄；根目錄套件維持 CommonJS，使 Node 閘門能在 Node 的 `.js = CJS` 語意下繼續執行；應用程式目錄則透過 `web/webclient-app/package.json` 宣告為 ESM。設計稿於 A1 提交至 `docs/design/` 底下。

### D9 — 透過瀏覽器橋接保留公開契約
Vue 應用程式保持相同的穩定公開契約介面：`window.Elosern.Protocol` 與 `.KeyboardRouter` 為匯入的 UMD 模組；`window.Elosern.narrativeInput` 為敘事與抉擇點的附加路徑；`window.Elosern.actions.submit` 為單一動作分派進入點。Phase-0 契約審查（A1）凍結了精確的 façade 介面與 C2 所套用的 `MODIFIED`/`RENAMED` 增量集合。

### D10 — 無外部相依的原生文字備用機制
一個小型的原生 JavaScript 文字主控台（`web/static/webclient/js/text_console.js`，UMD，受 Node 閘門保護）直接綁定至 `evennia.js` 傳輸層，獨立於 Vue 與 jQuery，作為權威文字路徑；在應用程式掛載後隱藏，並在組合包失敗或 OOB 不相容時重新啟動。**A2 探針成果：** `evennia.js` 在所有傳輸路徑上均無 jQuery 相依，**唯獨在其最後載入時的啟動呼叫 `$(document).ready(...)` 例外**；因此 Vue 分支載入了 30 行的 `web/static/webclient/js/jquery_ready_shim.js`（僅限於該單一介面，絕不與完整 jQuery 並存）以取代保留 jQuery。主控台也**將傳輸層的 `text` 行算繪為純文字**（使用 `textContent`，絕不使用 `innerHTML`），使遊戲資料被視為純資料而非標記語言；豐富的 ANSI 與 Evennia 標記算繪將隨主架構波次透過允許清單的 `NarrativeMarkup` 管線提供（審查修正：在該管線進入 Vue 路徑前，不得將伺服器來源內容作為 HTML 注入）。Vue 分支自行開啟通訊端，原廠啟動流程僅呼叫延遲 500 毫秒的 `Evennia.init()`，而舊版 GUI 主架構通常是負責呼叫 `Evennia.connect()` 的元件，因此 `base.html` 會同步執行等冪的 `init()`，綁定主控台接聽器，然後執行 `connect()`。

## 風險與權衡

- **在 Python 優先儲存庫中引入 npm 工具鏈** → 僅限開發與 CI 期間使用；根目錄套件保持零執行期 npm 相依（受契約測試驗證）；Node 閘門保持無外部相依；每個 npm 步驟均為明確且不壓制錯誤的 CI 步驟。
- **替換主架構時的瀏覽器測試變動** → D5 掛鉤 + D9 橋接器 + A1 審查凍結了增量集合；行為切片於 C4 重新對應。
- **傳輸層接線錯誤（epoch／修訂版本／重新連線／鎖定）** → C1 重用經過 Node 測試的 reducer 作為 store 核心；C3 與 C4 重新執行現有的 Playwright 驗收測試。
- **提供服務的環境出現 `dist/` 404** → 在 CI 前端工作、兩個瀏覽器工作區以及容器 `vue-dist` 階段中建置；受管瀏覽器檢查（A2）驗證組合包、樣式與字型能從來源端載入，並封鎖所有非本機請求。
- **切換期間存在兩個 DOM 管理器** → 使用 XOR 旗標（絕不同時載入兩者），單一舊版預設值，於 D1 刪除。
- **穩定非雜湊的進入點名稱** → Evennia 自身的 `/static` 服務無需特殊處理；若部署環境後續置於長期快取 `/static` 的反向代理之後，請為 `app/dist/index.js` 與 `index.css` 設定 `no-cache`（或較短的 TTL），或加入建置版本查詢字串，於 C4（正式切換）時再次檢視。
- **持久化 `.static` 磁碟卷殘留過期雜湊資產** → 進入點的 `collectstatic`（未帶 `--clear`）會留下被取代的 `assets/*`；此為無害現象（進入點會引用目前的雜湊）。在確認多副本行為之前，切勿加入 `--clear`。

## Store 切片契約（固定供 C1 與 Wave B 使用）

Wave B 依此結構建置離線元件；C1 進行實作，雙方必須鎖定相同的介面：

- **單一 Pinia store 擁有檢視狀態**（`web/webclient-app/stores/`）。其核心為匯入的協定 reducer（`lib/protocol.js`，絕不另外手寫第二個 reducer）以及用於焦點狀態的匯入鍵盤路由器。
- **不可部分發布，僅讀取已認可狀態：** store 僅在完成完整的 reducer 交易後才發布新的不可變狀態快照；元件絕不讀取處理中的暫存狀態。每個 OOB 訊息（快照／更新／結果／協定錯誤）均先由 reducer 套用；發布是觀察者能看見該狀態的唯一時刻。
- **檢視切片：** 元件從 store 的公開 getters 讀取狹窄的衍生切片（例如 `context_actions` 面板、敘事日誌、傳輸鎖定狀態）；元件發出使用者意圖事件（動作提交、文字輸入），store 透過單一分派進入點路由它們，僅限分派，且維持單一進行中狀態異動。
- **事件進入，意圖輸出：** store 訂閱傳輸事件頻道（由 C3 綁定）；元件絕不直接訂閱傳輸層。
- Wave B 元件的 Storybook stories 會接收作為純 fixture 物件的切片（與 store 的 getters 回傳形狀相同），確保離線 stories 與線上檢視不會脫鉤。

## 跨變更執行機制（路線圖摘要）

- 每個變更約需 1 個工作天，各自能獨立通過測試，並依拓撲順序落地；**合併與封存嚴格遵循拓撲順序**（絕不在同一作用中檔案上有兩個寫入者，絕不同時封存相同能力的兩個變更）。
- `webclient-vue-application` 與 `webclient-component-showcase` 於 B1 作為全新能力新增（ADDED），並由後續變更修改（MODIFIED）。
- 元件覆蓋率清單持續擴充：B1 植入初始值，B2 至 B4 擴充，B5 凍結。
- 真實資料範圍：任何元件不得呈現缺乏後端 OOB 讀取模型（允許清單）或文字串流支援的資料；延後實作的外觀（隊伍面板、親密狀態、完整背包、事件日誌 toast）在 B5 被明確斷言為不存在。
