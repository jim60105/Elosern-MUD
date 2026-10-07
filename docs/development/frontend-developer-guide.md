# 前端開發指南（Vue WebClient）

**所屬變更：** A2（`webclient-vue-01-foundation`）撰寫本文件。
**優先順序：** 僅為共用操作指南，變更專屬的 OpenSpec 工件與架構參考（[`frontend-vue-architecture.md`](frontend-vue-architecture.md)）具有更高優先順序。
**連結來源：** 於 D1 連結自 `docs/_sidebar.md`。

## 先決條件

- **Node 24 + pnpm**（CI 品質閘門固定使用 Node 24 搭配 Corepack 啟用的 pnpm；儲存庫的 Python 端由 uv 管理，與 Node 相互獨立）。
- **uv 0.12.0+** 供 Python 與 Evennia 端使用（瀏覽器測試會啟動真實伺服器）。
- 無其他安裝設定，前端僅為開發與 CI 期間的工具鏈，瀏覽器執行期絕不向遠端抓取 npm 或 pnpm 套件或任何遠端資產。

## 命令（儲存庫根目錄）

| 命令 | 說明 | CI 擁有者 |
| --- | --- | --- |
| `pnpm install --frozen-lockfile` | 安裝鎖定版本的工具鏈（僅開發用相依套件） | `frontend` 工作、瀏覽器工作區 |
| `pnpm run build` | Vite 生產建置 → `web/static/webclient/app/dist/`（穩定的 `index.js` + `index.css`，加上雜湊化 `assets/`；**不納入版本控制**） | `frontend` 工作、瀏覽器工作區 |
| `pnpm test` | Vitest 元件閘門（`web/webclient-app/**/*.test.js` 與 `web/admin-app/**/*.test.js`、jsdom、離線） | `frontend` 工作 + 最上層契約測試 |
| `pnpm run build-storybook` | Storybook 靜態建置 → `.storybook-out/`（已被 git 忽略） | `frontend` 工作 |
| `pnpm run showcase-coverage` | 對照 `web/webclient-app/component-manifest.json` 與 GM 的 `web/admin-app/component-manifest.json` 檢查元件覆蓋率 | `frontend` 工作 + 最上層契約測試 |
| `pnpm run build:gm` | GM 控制台的獨立 Vite 建置（`vite.gm.config.js`）→ `web/static/gm/dist/`（穩定的 `index.js` + `index.css`；**不納入版本控制**，只清除 GM 自己的輸出目錄） | `frontend` 工作、瀏覽器工作區、容器 |
| `pnpm run test:gm-boundary` | GM 相依邊界的無相依套件 Node 測試（`scripts/tests/gm-import-boundary.test.mjs`） | `frontend` 工作 + `web.gm.tests` 證據橋接 |
| `pnpm run dev` | 本機工作用的 Vite 開發伺服器（HMR） | —（僅供本機） |
| `node --test web/static/webclient/js/tests/*.test.js` | 針對保留的獨立於 DOM 邏輯執行無相依套件的 Node 閘門（約 1 秒） | preflight + 最上層契約測試 |

**Python 與 pnpm 的分工：** `web/static/webclient/js/` 底下的所有程式碼（elosern 邏輯、外掛程式、文字主控台）皆無相依套件，且受 Node 24 `node --test` 閘門保護，不 `require` 任何外部套件，載入時無 `document` 或 `window`，並採用 `module.exports` UMD 模組格式。`web/webclient-app/` 底下的所有內容均為 Vue 應用程式（Vite、Vitest、Storybook）。`package.json` 保持在儲存庫根目錄，且**沒有執行期 `dependencies`**（受契約測試驗證）。

## 目錄結構

```
package.json / pnpm-lock.yaml / vite.config.js / vitest.config.js   (根目錄)
.storybook/                                     vue3-vite 設定 (根目錄)
scripts/component-coverage.mjs                  Storybook 覆蓋率閘門
web/webclient-app/
  package.json                                  (應用程式樹的 "type": "module")
  main.js                                       SPA 入口點 (掛載至 #main-sub)
  App.vue                                       根元件 (A2 建置存根；B1 AppShell)
  lib/*.js                                      封裝 js/elosern/* 的 ESM 包裝器 (CJS 互通)
  styles/tokens.css                             設計系統 tokens (D6)
  styles/fonts.css                              自我代管的 @font-face (D6)
  styles/fonts-mono.css                         Jim Mono TC 等寬字體的 @font-face（由匯入工具輸出，勿手動編輯）
  styles/app-shell.css                          存根頁面外觀樣式
  fonts/{iansui,notosans,notoserif}/*.woff2     擷取自設計稿的子集化字型
  fonts/jimmonotc/*.woff2 + licenses/           Jim Mono TC 等寬字體的 unicode-range 切片、碼位清單與授權
  component-manifest.json                       必要 Story 清單 (B1 植入初始值，B5 凍結)
  tests/*.test.js                               Vitest 元件閘門
  stories/**                                    Storybook stories (自 B 波次起)
web/static/webclient/
  js/elosern/*                                  保留的獨立於 DOM 邏輯 (透過 lib/* 重新匯出)
  js/text_console.js                            D10 原生文字主控台 (兩分支皆有)
  js/jquery_ready_shim.js                       evennia.js ready 啟動 shim
  css/webclient.css  css/ansi_palette.css       共用頁面 + ANSI 主題
  app/dist/                                     Vite 輸出目錄 (已被 git 忽略，在所有提供服務的環境建置)
  (已停用的 `js/plugins/*` 檢視外掛、`vendor/*` 執行期與無效 CSS
   goldenlayout.css / elosern.css 已在 D1 刪除)
web/templates/webclient/base.html               XOR 旗標腳本載入 (A2)
web/webclient/context_processors.py             webclient_vue_enabled 脈絡變數
```

## 強制規則

1. **切勿直接編輯 `web/static/webclient/js/elosern/*`**（或其 Node 測試）來配合 Vue 應用程式。請透過 `web/webclient-app/lib/*` 匯入；若包裝層需要微調，應修改包裝器，而非修改 UMD 原始碼。
2. **禁止發出遠端執行期請求。** 建置後的頁面僅從專案來源端載入；不得加入任何 CDN、執行期的 registry 擷取，或絕對的第三方 URL。`base.html` 保持固定於本機來源。
3. **不得引入執行期 npm 或 pnpm 相依套件。** `package.json` 必須維持僅有 `devDependencies` 的結構；Node 閘門保持無外部相依。
4. **執行瀏覽器測試前必須先建置 dist。** 受管瀏覽器套件會直接從工作樹提供靜態檔案；未執行 `pnpm run build` 會導致 Vue 分支檢查失敗（CI 會在兩個工作區中自動建置）。
5. **XOR 旗標採互斥載入。** 每個頁面只啟用一種檢視堆疊，`webclient_vue_enabled`（脈絡變數）會挑選 Vue 組合包**或**舊版復原分支（D10 原生文字主控台，無檢視程式碼）。正式環境預設為 **Vue 組合包**（於 C4 切換）；舊版分支僅能透過復原機制進入。`?__vue=1` 可強制切換至 Vue 分支以供審查或離線載入檢查；`ELOSERN_BROWSER_VUE_CLIENT=1`（瀏覽器測試設定）為 C3 使用的測試設定開關。

## 等寬字體（Jim Mono TC）

`--f-mono` 為 `"Jim Mono TC", "Noto Sans TC", monospace`。拉丁字母、數字、箭頭、框線字元與 CJK 都由自我代管的 [Jim Mono TC](https://github.com/jim60105/JimMonoTC)（SIL OFL 1.1）繪製，不依賴玩家電腦安裝的字型。Jim Mono TC 合併了拉丁基底字形與 Noto Sans CJK TC 的 CJK 字形，每個 CJK 字元的寬度剛好是兩個拉丁字元，因此含中文的框線地圖能逐欄對齊。地圖幾何使用的一格寬度（`CELL_EM`，拉丁字元的 advance 除以 upem）唯一來源是匯入清單 `codepoints.json` 的 `cell_advance`，由 `lib/mono_cells.js` 的產生區塊匯出；上游換版改變格寬時，所有地圖標簽預算自動隨產生值重算，不需要改寫任何常數。Noto Sans TC 只負責 Jim Mono TC 未收錄的罕用 CJK（寬 1em）。

字型保留程式設計連字（例如 `->`、`==`），連字的寬度與原本的字元數相同，不會改變欄位。

切片來自上游 release 的 `-web.zip`，本專案只匯入、不自行切字型。常規（400）與粗體（700）各保留：

- 單格群組 `latin`、`latin-ext`、`greek-cyrillic`、`box`、`symbols`；
- 依 Noto Sans TC 使用頻率分段的 `cjk-<N>` 群組。

Nerd Fonts 圖示（`icons-<N>`）、罕用 CJK（`cjk-x<N>`）與斜體不匯入。每個切片不超過 64 KB，頁面只下載實際繪製到的切片。

切片、`licenses/`、`codepoints.json` 與 `styles/fonts-mono.css` 皆由匯入工具輸出並提交至版本庫，請勿手動編輯。升級字型時，先更新 `tools/import_mono_font.py` 中釘選的 release、資產檔名、SHA-256 與拉丁 `CELL_ADVANCE`（新版的 hmtx 實測值），再執行：

```sh
uv run --locked python -m tools.import_mono_font
uv run --locked python tools/gen_mono_cells.py
```

匯入工具會下載 release 並驗證 SHA-256（也可以把已下載的 zip 路徑當作唯一參數），輸出的位元組可重現（重新執行後 `git status` 應保持乾淨）。第二個指令依新的碼位清單重新產生地圖使用的單格表 `lib/mono_cells.js`。`tests/test_mono_font_contract.py` 檢查切片大小、範圍互不重疊、兩種字重的 CJK 相同，以及授權檔案。

## 瀏覽器（受管執行期）測試

- 請執行單一特定檔案或類別，而非整個套件：
  `uv run --locked python -m unittest web.tests.browser.test_vue_foundation`
  （啟動真實的 loopback Evennia 伺服器；A2 類別約需 1 至 2 分鐘）。
- 新增的瀏覽器測試方法必須恰好加入 `.github/browser-shards.json` 中的**單一**行程清單（由 `tests/test_evennia_test_optimization_contract.py` 強制驗證）。
- 每個非本機請求都會被 `guard_local_only` 中止；僅使用確定性 fixtures（`web/tests/browser/seed.py`），不使用 LLM 與圖像生成服務。

## 容器

`Containerfile` 的 `vue-dist` 階段（Node 24）會啟用 Corepack 並執行 `pnpm install --frozen-lockfile && pnpm run build && pnpm run build:gm`，應用程式佈局階段會將兩份產生的 `dist` 分別複製至 `/app/web/static/webclient/app/dist/` 與 `/app/web/static/gm/dist/`，並複製 `pyproject.toml`（GM session API 從中讀取遊戲版本）；進入點在執行 `evennia migrate --noinput` 之後會執行 `evennia collectstatic --noinput` 以更新持久化的 `server/.static` 磁碟卷。本機工作流程為 `podman compose build && podman compose up`（請勿將 Ollama 或 sd-webui 加入此映像檔中）。

## GM 控制台（`web/admin-app/`，S1 基礎＋S2 營運總覽）

GM 控制台是僅限 Developer 帳號使用的營運者介面，掛載於 `/gm/`，與遊戲 WebClient 分開建置、分開提供（設計：`docs/superpowers/specs/2026-10-06-gm-portal-design.md` §§3–5）。S1 交付基礎骨架，S2 把首頁「總覽」換成營運儀表板（設計：`docs/superpowers/specs/2026-10-06-gm-portal-s2-dashboard-design.md`）：

- **存取：** `/gm/` 底下所有頁面與 API 都要求 `check_permstring("Developer")`（superuser 亦可）；staff 身分不能替代。未登入的頁面請求導向 `LOGIN_URL?next=…`，API 回傳 401 `unauthenticated`；權限不足時頁面回 403、API 回 403 `forbidden`。所有路由只能透過 `web/gm/urls.py` 的 `gm_path()` 註冊；`web/gm/tests/test_access.py` 會走訪 URL 解析器，未包裝的路由會讓測試失敗。
- **API：** `GET /gm/api/session`、`GET /gm/api/dashboard` 與 `GET /gm/api/llm/calls/<call_id>`。S1 的 `/gm/api/health` 已移除且沒有別名，Django／資料庫健康檢查併入 dashboard 的 `process` 區塊。dashboard 的每個區塊各自計算，失敗的區塊只在自己的位置放 `{"error": {"code", "message"}}`；它只讀取既有資料（不建立世界時鐘或任何紀錄），也不探測 LLM 端點（LLM 健康由近期 `llm_call` 事件被動推算，SD 使用既有的 TTL 快取探測）。LLM 統計只涵蓋行程內有界緩衝區（`GM_RECENT_LLM_CAPACITY`／`GM_RECENT_ISSUE_CAPACITY`）保留的事件，不是啟動以來的總數，reload 後清空。呼叫明細讀取 S2a transcript：格式錯誤回 400 `invalid_call_id`、查無紀錄回 404 `transcript_not_found`、transcript 停用回 409 `transcript_disabled`。回應格式為 `{"ok": true, "data": …}` 或 `{"ok": false, "error": {"code", "message"}}`，用戶端只依 `code` 分支。寫入一律走 POST 並附上 `X-CSRFToken`；S1 沒有正式的寫入端點。
- **觀測性：** 每個 GM API 請求都會發出一次 `gm_request`（帶最終狀態碼），每次拒絕存取都會發出 `gm_denied`，皆透過 `world.observability` 門面。
- **相依邊界：** `web/admin-app/` 只能從遊戲樹匯入 `styles/tokens.css` 與 `styles/fonts*.css`；`scripts/gm-import-boundary.mjs` 會先解析相對路徑、別名（`web/admin-app/gm-aliases.mjs`）與符號連結再套用允許清單。
- **總覽儀表板：** `views/OverviewView.vue` 透過 `lib/poller.js` 每 5 秒輪詢一次（以 setTimeout 串接、不重疊請求、分頁隱藏時暫停、回到前景立即更新一次），輪詢失敗時保留上一份資料並標示「資料過期」；401／403 會停止輪詢交給路由守衛。各區塊位於 `views/overview/`，選取最近呼叫會開啟 `GmCallDrawer`（原生 `<dialog>` 模態側欄），只在選取時才查詢 transcript。
- **元件：** `GmShell`、`GmNav`、`GmPageHeader`、`GmPanel`、`GmTable`、`GmEmpty`、`GmError`、`GmStatusBadge`，以及 S2 新增的 `GmMeter`、`GmServiceCard`、`GmRefreshBar`、`GmCodeBlock`、`GmCallDrawer`，都只以設計代符構成，Storybook 標題為 `GM/<元件>`，並列於 GM 的元件清單中。seal 紅與 `.ui-btn--danger` 只保留給破壞性操作。
- **導覽：** 側欄的 維運、執行期狀態、世界資料、操作、GM 介入 皆顯示為「尚未開放」，沒有路由也沒有佔位頁面，要等各自的後續變更（S2–S6）落地。
- **後端測試：** `web/gm/tests/`（`EvenniaTest`）已登錄於 `.github/evennia-shards.json`；新增的 GM 測試模組必須同時登錄。

## 前端相關需求的可追溯性

瀏覽器測試與最上層契約測試皆帶有 `@covers_requirement(...)` 標註（從 `tools.spec_traceability` 匯入）；請參閱 [`spec-test-traceability.md`](spec-test-traceability.md)。A2 閘門由 `tests/test_frontend_toolchain_contract.py`（pnpm 執行）、`tests/test_browser_verification_contract.py`（工作流程與靜態檢查）以及 `web/tests/browser/test_vue_foundation.py`（瀏覽器行為）所涵蓋。

## 桌面視覺可讀性修復（2026-10-05）

驗收視埠恰為 **1451 × 790 CSS px**，指的是視埠尺寸，非瀏覽器外框視窗尺寸。桌面框架層使用 `clamp(1, min(innerHeight / 790, innerWidth / 1451), 1.4)`；1741 × 948 是不設上限的抽樣檢查，2560 × 1440 則驗證上限是否生效。訊息與完整日誌的散文在基準縮放下，以隨附的 Jim Mono TC 字型呈現，A− / A / A+ 對應 **16 / 18 / 20 CSS px**。量測要在 `document.fonts.ready` 之後對實際繪出的字形進行；光看計算後的 family token，無法證明某個字由哪個字型繪出。

240px 小地圖對過大的格線與放射狀圖形，改用以現位置為中心、scale-1 的視窗裁切，不縮小 16 單位的 SVG 標籤。格線間距同時保留標籤的水平淨空，以及上方標籤與下方標記之間的垂直淨空，包含共用名稱被隱藏的下方荒野節點。全圖也有 scale-1 的最小縮出下限，過大的圖形圍繞現位置展開，平移、縮放、焦點揭示與記憶地點控制仍可達。切勿恢復過往的整圖 fit 行為或 0.75 島嶼下限，那會讓文字的有效尺寸小於 16 CSS px。

開啟完整日誌並追加正在閱讀的回應時，只要訊息框與散文設定未變，訊息頁必須保留。實際版面 reflow 仍跟隨回應空間的 reveal anchor。掛載期的 `document.fonts.ready` 不會為尚未出現的字元載入 Jim Mono TC 切片，因此進行同步的頁面貼合探測前，要先以兩種字重準備好實際渲染的回應／節拍字形串流。已被取代或未掛載的準備不可提交；未提交的回應／綁定不可驅動戰鬥節拍，也不可推進前一則回應。閱讀器測試的基準要取在開啟日誌之前，不可在追加後重設。

背包標題讓資訊標籤換行到新列即可，不得把兩個字的標題垂直切開。資訊標籤、計數、貨幣單位與空裝備文字使用可讀的 muted-paper 色階，不用低對比的 disabled-ink 色階。

重建執行中受管 fixture 的 SPA 後，要用該 fixture 現有的 `runtime.env`，透過 `uv run --locked evennia collectstatic --noinput --settings browser_settings` 重新整理**該 fixture** 的隔離靜態根目錄。只重新整理頁面仍可能持續提供 fixture 啟動時收集的靜態複本。視覺檢視時絕不可針對正式使用者設定／資料庫執行 collectstatic。

最終視覺檢視證據見 `openspec/changes/archive/2026-10-05-repair-retarget-visual-reading/review.md`，OpenSpec 修正案為 `repair-retarget-visual-reading`。兩個已封存的 retarget 變更維持為歷史記錄。

## 敘事色調展示（Narrative palette showcase）

`Core/MessageWindow/NarrativeTones` 在訊息帶漸層背景上算繪產生的 ANSI 色板，並在真正的完整日誌 overlay 中開啟同一段標記。Storybook 匯入 `web/static/webclient/css/ansi_palette.css`；切勿再加 story 本地色板。該樣式表以 `uv run --locked python tools/gen_ansi_palette.py` 重新產生。

前景對映使用十二個作者製 ANSI 色調，並在套用到 `#141019` 的既有紙面對比下限之前，先把 cube 飽和度封頂在內收的 0.62。背景維持原始值。色相／明度保持是下限之前的不變量；紙面混色可能讓兩者都偏移。3:1 下限不足以讓一般尺寸的灰階／cube 散文或半透明帶後方的任意圖資達成 WCAG AA。兩個表面都要在實際字寸下檢視。該變更的[驗證記錄](../../openspec/changes/webclient-ansi-narrative-tones/design.md)內含實測對比與受測的視埠／動態矩陣。
