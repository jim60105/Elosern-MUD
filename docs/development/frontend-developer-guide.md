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
| `pnpm test` | Vitest 元件閘門（`web/webclient-app/**/*.test.js`、jsdom、離線） | `frontend` 工作 + 最上層契約測試 |
| `pnpm run build-storybook` | Storybook 靜態建置 → `.storybook-out/`（已被 git 忽略） | `frontend` 工作 |
| `pnpm run showcase-coverage` | 對照 `web/webclient-app/component-manifest.json` 檢查元件覆蓋率 | `frontend` 工作 + 最上層契約測試 |
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

`Containerfile` 的 `vue-dist` 階段（Node 24）會啟用 Corepack 並執行 `pnpm install --frozen-lockfile && pnpm run build`，應用程式佈局階段會將產生的 `dist` 複製至 `/app/web/static/webclient/app/dist/`；進入點在執行 `evennia migrate --noinput` 之後會執行 `evennia collectstatic --noinput` 以更新持久化的 `server/.static` 磁碟卷。本機工作流程為 `podman compose build && podman compose up`（請勿將 Ollama 或 sd-webui 加入此映像檔中）。

## 前端相關需求的可追溯性

瀏覽器測試與最上層契約測試皆帶有 `@covers_requirement(...)` 標註（從 `tools.spec_traceability` 匯入）；請參閱 [`spec-test-traceability.md`](spec-test-traceability.md)。A2 閘門由 `tests/test_frontend_toolchain_contract.py`（pnpm 執行）、`tests/test_browser_verification_contract.py`（工作流程與靜態檢查）以及 `web/tests/browser/test_vue_foundation.py`（瀏覽器行為）所涵蓋。

## Desktop visual-reading repair (2026-10-05)

The acceptance viewport is exactly **1451 × 790 CSS px**, not an outer browser
window size. Desktop chrome uses
`clamp(1, min(innerHeight / 790, innerWidth / 1451), 1.4)`; 1741 × 948 is an
uncapped spot check and 2560 × 1440 exercises the cap. Message and full-log
prose use the bundled Jim Mono TC face at **16 / 18 / 20 CSS px** for A− / A /
A+ at reference. Measure actual drawn glyphs after `document.fonts.ready`;
the computed family token alone does not prove which face drew a character.

The 240px minimap clips oversized lattice and radial drawings through a
current-centered, scale-1 window rather than shrinking 16-unit SVG labels.
Its lattice pitch reserves horizontal label clearance and vertical clearance
between an upper label and the lower marker, including lower wilderness nodes
whose shared name is suppressed. The full map also has a scale-1 zoom-out
floor: oversized drawings open around the current location and remain
reachable with pan, zoom, focus reveal and remembered-location controls.
Do not restore historical whole-map fits or a 0.75 island floor: those produce
effective text smaller than 16 CSS px.

Opening the full log and appending to the response being read must retain the
message page when its box and prose setting are unchanged. Actual layout
reflow still follows the response-space reveal anchor. Mount-time
`document.fonts.ready` does not load Jim Mono TC slices for characters that
have not appeared yet: prepare the actual rendered response/beat glyph stream
in both weights before performing synchronous page-fit probes. Superseded and
unmounted preparations cannot commit; an uncommitted response/binding cannot
pace combat beats or advance the previous response. Reader tests must keep
their baseline from before opening the log, not reset it after an append.

Inventory headings allow their informational tag to wrap onto a new row
without splitting the two-character heading vertically. Informational tags,
counts, money units and empty-equipment text use the readable muted-paper
step, not the low-contrast disabled-ink step.

After rebuilding a running managed fixture's SPA, refresh **that fixture's**
isolated static root with `uv run --locked evennia collectstatic --noinput
--settings browser_settings` using its existing `runtime.env`. A reload alone
can keep serving the static copy collected at fixture startup. Never collect
against the live user settings/database for a visual review.

See [the final visual-review evidence](2026-10-05-final-visual-review.md) and
the OpenSpec amendment `repair-retarget-visual-reading`. The two archived
retarget changes remain historical records.

## Narrative palette showcase

`Core/MessageWindow/NarrativeTones` renders the generated ANSI palette on the
message-band gradient and opens the same markup in the real full-log overlay.
Storybook imports `web/static/webclient/css/ansi_palette.css`; do not add a
story-local palette. Regenerate that stylesheet with
`uv run --locked python tools/gen_ansi_palette.py`.

Foreground mapping uses twelve authored ANSI tones and an inward-rounded
0.62 cube saturation cap before the existing paper contrast floor against
`#141019`. Backgrounds remain raw. Hue/lightness preservation is a pre-floor
invariant; the paper blend can shift both. The 3:1 floor does not establish
WCAG AA for normal-sized grayscale/cube prose or arbitrary artwork behind
the translucent band. Inspect both surfaces at their actual font sizes.
The change's [verification record](../../openspec/changes/webclient-ansi-narrative-tones/design.md)
includes measured contrast and the tested viewport/motion matrix.
