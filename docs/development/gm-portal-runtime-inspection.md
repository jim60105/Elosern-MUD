# GM 執行期狀態檢視

這個頁面說明 GM 控制台「執行期狀態」區塊的介面契約與唯讀限制。這是 `gm-portal-s3-runtime-state` 交付的範圍，位於 `/gm/runtime`，提供帳號、玩家角色、NPC、魔物、房間、任務、敘事紀錄與美術資產的策展摘要，任何 Evennia 物件的原始資料，以及 NPC 記憶與對話的檢查介面。

所有檢視都是唯讀。讀取層不會建立 Attribute、不會修補資料、不會呼叫敘事寫入函式，也不會自行重算規則。若要修改世界狀態，請走既有的確定性核心與來源檔，不要透過這個介面。

## 路由

伺服器端在 `web/gm/urls.py` 註冊五個路由家族，全部經由 `gm_path` 套用 Developer 權限檢查，回應沿用既有的 JSON 信封。

| 路由 | 用途 |
| --- | --- |
| `GET /gm/api/state/<kind>?cursor=&limit=&<filters>` | 某種類的摘要清單，預設 50 筆，上限 200 筆 |
| `GET /gm/api/state/<kind>/<id>` | 單一實體的策展摘要 |
| `GET /gm/api/state/object/<dbref>/raw` | 任意 Evennia 物件的原始資料 |
| `GET /gm/api/state/search?q=` | 全域搜尋 |
| `POST /gm/api/state/npc/<dbref>/recall` | NPC 召回預覽，需要 CSRF 權杖 |

`search`、`object/<dbref>/raw` 與 `npc/<dbref>/recall` 這三個保留路徑必須先註冊，否則會被 `state/<kind>` 吞掉。前端路由 `web/admin-app/router.js` 維持相同的順序。

清單游標是不透明的 base64url 文件，內容包含下一頁位移與當時的篩選指紋。把游標套用到不同的篩選條件會得到 400 `invalid_cursor`，不會靜默跳過資料列。記錄型別的識別碼由擁有者界定範圍，因此任務、記憶、快照與對話的請求都要帶 `owner`，前端連結也會一併帶上。

## 手動重新整理

執行期頁面不做自動輪詢。實體頁的「重新載入」按鈕重新讀取目前選取的分頁，概要與原始資料會更新「最後載入」時間。記憶與對話分頁各自帶有「重新載入」，因為它們讀取的是另一組集合路由（記憶、情境快照、對話），按鈕會重新讀取該分頁的集合。只有總覽頁的營運儀表板沿用「可視性感知輪詢」的既有生命週期（每 5 秒、分頁隱藏時暫停），執行期頁面不會繼承它，也不會建立任何計時器。

## 診斷錯誤

傳輸層與策展區塊各自有明確的失敗代碼，用戶端只依代碼分支，訊息是給營運者看的正體中文。

| 代碼 | HTTP | 意義 |
| --- | --- | --- |
| `object_not_found` | 404 | 找不到指定的物件或紀錄 |
| `kind_mismatch` | 404 | 物件存在，但不是路由指名的種類 |
| `unsupported_kind` | 404 | 不支援的狀態種類 |
| `invalid_filter` | 400 | 篩選條件不正確（例如任務缺少 `owner`） |
| `invalid_limit` | 400 | 每頁筆數不在 1 到 200 之間 |
| `invalid_cursor` | 400 | 游標格式錯誤，或與目前的篩選條件不符 |
| `invalid_query` | 400 | 搜尋或召回請求的文字不正確 |
| `query_too_long` | 400 | 召回文字超過 2000 字元，請求不會執行 |

策展摘要由多個獨立區塊組成。單一區塊的來源失敗時，只有那個插槽帶著 `{"error": {"code": ..., "message": ...}}`，整頁仍以成功信封回應，其餘區塊照常顯示。因此 `wallet`、`persona`、`schedule` 之類的區塊各自失敗時，營運者看得到缺口在哪裡，而不是整頁變成 404。

搜尋的比對順序固定為精確 `#dbref`、物件鍵、任務編號、來源識別。同一筆查詢不會把不同層級的結果混成單一分數排序。

## 召回的唯讀限制

召回預覽以 NPC 自身作為擁有者與請求者，呼叫既有的 `fast_recall`，轉送 `thread_id`、`include_superseded` 與 `include_inactive`，並原樣輸出核心、工作與召回的入選項目、BM25 分數與記憶世代。它不重新排序，也不放寬敘事權限，未知或不可存取的故事線不會貢獻任何內容。

工具不會呼叫 `build_dialogue_context`。那個函式會結清通信、建立紀元、寫入情境快照並附加對話框，屬於寫入路徑。要查看過去的提示與對話內容，請使用既有的 S2 transcript 與已保存的快照。

`web/gm/tests/test_npc_narrative.py` 以相同輸入直接比對 `fast_recall` 的結果，並在讀取前後比對 Attribute 與敘事資料表的資料列數量。`web/gm/tests/test_read_only_contract.py` 以 AST 檢查 `web/gm/readers` 不得出現寫入呼叫、儲存欄位賦值或已知寫入函式的匯入，`web/gm/tests/test_runtime_immutability.py` 則比對整個檢視介面（清單、明細、原始資料、敘事分頁、召回）執行前後，每個敘事資料表的實際儲存內容。

## 測試與閘門

讀取層每個種類各有一個固定 fixture 的 `EvenniaTest` 模組，另有傳輸層的存取矩陣與錯誤矩陣測試。前端由 Vitest 覆蓋連結、JSON 標記、篩選分頁、手動更新與區塊錯誤，Storybook 覆蓋每個新元件。

交接前請執行 `uv run --locked python -m tools.contract_gate`、`uv run --locked python -m tools.spec_traceability check`、`openspec validate gm-portal-s3-runtime-state --strict`，以及 `pnpm test`、`pnpm run test:gm-boundary`、`pnpm run build:gm`、`pnpm run showcase-coverage`。

新加入的 Python 測試模組都位於 `web/gm/tests/`，該套件由 `.github/evennia-shards.json` 既有的 `web.gm.tests` 標籤遞迴涵蓋，因此不需要新增分片標籤。前端新增的瀏覽器測試類別若超出目前範圍，才需要登記到 `.github/browser-shards.json`。

## 尚未交付的部分

世界資料瀏覽、存檔、開發者寫入主控台（S4、S5、S6）仍未交付，導覽列上維持「尚未開放」且沒有路由。伺服器只開放 `web/gm/urls.py` 列出的路徑，未知的 `api` 路徑回傳 404 信封，不會落到前端外殼。
