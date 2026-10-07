# GM 世界存檔

這個頁面說明 GM 控制台「存檔」區塊的操作流程與介面契約。這是 `gm-portal-s5-saves` 交付的範圍，位於 `/gm/saves`。Elosern 是單人遊戲，玩家與營運者是同一個人，所以一份世界存檔就是遊戲的存檔欄位：實驗或修復之前先存檔，出問題時回到那個狀態。

存檔在遊戲規則之下運作：它複製整個資料庫與美術庫，從不寫入任何遊戲欄位。讀檔不在執行中的伺服器裡進行，伺服器只記下請求並關機，下次啟動前由預啟動工具套用。

## 存檔內容與位置

一份存檔包含 SQLite 世界資料庫與生成的美術庫。資料庫只記錄檔案識別，重新生成會原地取代檔案、改副檔名時會刪除舊檔、刪除圖庫卡片也會刪檔，所以只還原資料庫會看到較新的圖或退回剪影。

不在存檔裡的東西：`prompts/`、規則書與 lore（git 中的原始碼）、模型檔（`.translate`、`.rembg`）、日誌與 LLM transcript。

資料庫與美術庫是兩個不同的容器 volume（`evennia-db`、`evennia-art`），hardlink 不能跨 volume，所以每份存檔分成兩半，各自放在自己的 volume 裡，不需要修改 compose：

```text
server/db/saves/<id>/evennia.db3
server/db/saves/<id>/manifest.json
server/db/saves/RESTORE_PENDING          # 等待套用的存檔 id
server/db/saves/RESTORE_RESULT.json      # 最近一次套用的結果
server/.art/.saves/<id>/...              # 美術庫樹狀結構的鏡像
```

`<id>` 的格式是 `YYYYMMDDTHHMMSS-<6 位十六進位>`（UTC）。每個路由與函式在碰觸檔案系統之前都會先驗證格式。只有兩半與 manifest 都完整的存檔才會列出；資料庫那一半（含 manifest）最後發布、最先刪除。

`GM_SAVES_ROOT` 固定為 `server/db/saves`，與 `ART_STORE_ROOT` 一樣不能用環境變數覆寫，因為預啟動工具不經過 Django，自行推導同一個預設配置。

## 建立存檔

`server/saves/snapshot.py` 的 `create_snapshot(kind, label)` 負責建立。同一時間只會有一份存檔在進行，重疊的請求回 `save_in_progress`。

1. 進入 `world.art.publication.paused()`：設定暫停旗標，讓 `ArtDrainScript` 的每次觸發與手動 drain 都直接返回，並取得美術發布閘門。任何正在發布的生成結果（記錄轉換、原子取代、刪除被取代的舊檔）會先完成；之後到來的發布會等待。生成本身（等待 sd-webui）不在閘門內，只有很短的發布步驟會等待。玩家刪除圖庫卡片時最多等 2 秒，等不到就略過刪檔，留下的未引用檔案由啟動時的孤兒清理回收。閘門一律在 `queue_lock`、`gallery_lock` 之前取得，從不在持有它們時等待：卡片的刪檔在釋放 `gallery_lock` 之後才進行。
2. 以 SQLite online backup API 複製資料庫（一次完成，期間其他寫入者的 commit 會短暫延後），絕不直接複製執行中的檔案位元組。
3. 走訪美術庫（略過 `.saves/`、`.restore-*` 工作目錄、符號連結與寫入者的暫存檔 `.<name>.<random>.tmp`），把每個檔案 hardlink 進存檔，連結失敗時改為複製。走訪途中消失的檔案會略過。
4. 離開閘門後寫入 manifest，再把兩個 `.partial` 目錄改名為正式名稱。任何失敗都會移除 `.partial` 與已發布的一半，並送出 `save_failed`；閘門與暫停旗標一定會解除。

hardlink 之所以安全，是因為每個美術寫入者都先寫暫存檔再原子取代，從不原地寫入：worker 的輸出一向如此；圖庫種子同步（`gallery_seed.py`）在這個變更中改為暫存檔加 `os.replace`，並且不再拒絕多重連結的目的檔，因為取代只換掉名稱，存檔裡的另一個連結保留原本的位元組。刪除只移除名稱，同樣不影響存檔。

### manifest

```json
{
  "version": 1,
  "id": "20261007T061530-3fa9c2",
  "label": "決戰之前",
  "kind": "manual",
  "created_at": "2026-10-07T06:15:30.123456+00:00",
  "clock": {"tick": 86400, "year": 1, "season": "春", "day": 2, "hour": 0, "minute": 0},
  "players": [{"name": "艾琳", "location": "harbor_square"}],
  "migrations": {"narrative": "0011_...", "objects": "0013_..."},
  "file_count": 128,
  "size_bytes": 73400320,
  "files": {"db": {"path": "evennia.db3", "size": 52428800}, "art": [{"path": "scene/forest.webp", "size": 81234}]}
}
```

- `kind`：`manual`、`auto_restore`（讀檔前自動）、`auto_intervention`（S6 介入前自動）。
- `created_at` 精確到微秒，用來排序同一秒內建立的存檔；id 只有到秒。
- `migrations` 是存檔資料庫每個 app 最近套用的 migration（從存檔的 `django_migrations` 讀取）。
- `files` 是驗證清單：每個檔案的相對路徑與大小。讀檔前逐一核對存在與大小，這是實作選擇，不是上游設計要求的格式；沒有 checksum。
- `label` 會去頭尾空白、把換行與控制字元換成空白，最長 80 字；可以是空字串。

## 保留與刪除

- 每種自動存檔在建立成功後最多保留 `GM_AUTOSAVE_KEEP` 份（預設 10，可用環境變數覆寫），刪除該種類最舊的幾份。手動存檔永不自動刪除。
- 操作者只能刪除手動存檔，刪除前需要確認；刪除自動存檔回 `save_delete_forbidden`。
- 讀檔請求選定的存檔在套用完成前受到保護：請求期間（記憶體中的 pin）與 `RESTORE_PENDING` 存在期間，該存檔所屬種類的清理會延後，下次啟動時由 `saves_restore_report` 步驟補做。所以選定「最舊的讀檔前自動存檔」時，讀檔前存檔不會把它刪掉，該種類會暫時超過上限一份。

## 讀檔

1. 操作者在頁面確認。對話框說明三件事：目前的世界會先存成讀檔前自動存檔、伺服器隨即關機並中斷所有連線、需要由操作者重新啟動。
2. 伺服器依序：
   1. 檢查 migration 相容性：存檔資料庫裡有目前程式碼不認得的 migration 時回 `save_incompatible`，不做任何事。
   2. 建立 `auto_restore` 存檔；失敗就不寫標記、不關機。
   3. 寫入 `RESTORE_PENDING`。
   4. 回應頁面（202），兩秒後走 Evennia 的關機路徑（`SESSION_HANDLER.portal_shutdown()`，等同 `@shutdown`）。排程關機失敗時會移除標記，避免下次無關的重啟默默套用讀檔。
   標記存在期間，新的存檔與第二個讀檔請求都回 `save_in_progress`。
3. 操作者重新啟動伺服器：本機執行 `scripts/serve.sh`，容器執行 `podman compose up`。兩個啟動器都在 `evennia migrate` 之前執行：

   ```sh
   uv run --locked python -m server.saves.restore --apply-pending   # scripts/serve.sh
   python -m server.saves.restore --apply-pending                   # docker-entrypoint.sh
   ```

   容器的最終映像沒有 uv，`/venv` 的 python 就是 uv 同步的專案直譯器。
4. 預啟動工具只用標準函式庫，不匯入 Django、Evennia 或 observability facade：
   1. 沒有標記就什麼都不做。
   2. 驗證 id、manifest、清單中的每個檔案（存在、一般檔案、大小相符）、存檔資料庫的 `PRAGMA quick_check`，以及 migration 相容性。已知的 migration 由標準函式庫掃描專案套件與已安裝的 `evennia`、`django` 的 `migrations` 套件取得，伺服器端的檢查使用同一個函式；合約測試確認 Django 自己載入的每個 migration 都在這份清單裡。驗證失敗時移除標記、寫入失敗結果，照常啟動目前的世界。
   3. 在兩個 volume 內各自準備可寫入的獨立副本（`.restore-staging`）。
   4. 把目前的資料庫（連同 `-journal`／`-wal`／`-shm`）與美術庫的每個頂層項目移到 `.restore-aside`。美術庫根目錄是 volume 掛載點，所以移動的是項目而不是根目錄；`.saves/` 不動。
   5. 安裝副本（美術只安裝 manifest 清單內、已驗證的一般檔案）。成功就刪除移開的原檔與標記；任何失敗都把原檔移回、移除標記，照常啟動。存檔本身從不被消耗。
   6. 兩種結果都寫入 `RESTORE_RESULT.json` 並印在 stdout。
5. `evennia migrate` 照常執行，較舊的存檔會被往前遷移。被捕捉為 `in_progress` 的美術工作由既有的 lease 回收重新排入佇列。
6. 伺服器啟動時 `saves_restore_report` 步驟讀取結果檔，送出 `save_restored` 或 `save_restore_failed` 一次（之後在檔案中標記 `reported`），然後補做延後的保留清理。頁面頂端顯示最近一次結果。

### 無法自動復原的情況

預啟動工具在可以照常啟動時結束碼為 0。以下情況結束碼為 2，啟動器（`set -e`）會停下，避免在不一致的世界上啟動：

- 回滾本身失敗（例如 volume 變成唯讀）。原檔留在 `server/db/.restore-aside/` 與 `server/.art/.restore-aside/`，結果檔標記 `"rollback": "failed"`。
- 上一次讀檔中途中斷，留下 `.restore-aside`。

`.restore-aside` 的檢查在每次啟動都會執行，不論有沒有讀檔標記，所以回滾失敗之後的重試也會一直停下，不會在空的資料庫上遷移出一個新世界。讀檔成功後若無法刪除移開的原檔（例如檔案被占用），工具只在 stdout 回報，並把它改名為 `.restore-done-<時間>` 後照常啟動；確認不需要後可以手動刪除。

這時需要手動處理：確認 `.restore-aside` 內是原本的資料庫與美術檔，把它們移回原位，刪除 `.restore-aside` 與 `.restore-staging`，再重新啟動。這是明確的操作限制，不是崩潰復原協定。

## 下載

`GET /gm/api/saves/<id>/download` 串流一個未壓縮的 tar，內容為 `<id>/manifest.json`、`<id>/evennia.db3` 與 `<id>/art/...`。標頭以 PAX 格式產生，事先算好 `Content-Length`，檔案以 64 KiB 分段讀出，不會把整份封存緩衝在記憶體。串流途中檔案變短或消失會中斷連線，不會送出損壞的 tar。開始串流前的錯誤仍是 JSON 錯誤信封。沒有上傳或匯入功能。

頁面透過 `web/admin-app/lib/api.js` 的 `download()` 下載：成功時取得檔案內容，失敗時與其他 API 走同一套登入、權限與錯誤碼處理。

## API

| 路由 | 用途 | 成功 |
| --- | --- | --- |
| `GET /gm/api/saves/` | 存檔清單、最近一次讀檔結果、待套用的存檔、`autosave_keep` | 200 |
| `POST /gm/api/saves/` | 建立手動存檔，請求主體 `{"label": "..."}`（格式錯誤視為空白標籤） | 201，回傳存檔 |
| `POST /gm/api/saves/<id>/restore` | 請求讀檔 | 202，`{"save", "pre_restore_save", "shutdown": true}` |
| `POST /gm/api/saves/<id>/delete` | 刪除手動存檔 | 200，`{"deleted": id}` |
| `GET /gm/api/saves/<id>/download` | 下載 | 200，`application/x-tar` |

清單中的每份存檔：`id`、`label`、`kind`、`created_at`、`clock`、`players`、`migrations`、`file_count`、`size_bytes`、`deletable`（只有手動存檔為 true）、`pending`。讀檔結果：`save`、`kind`、`label`、`outcome`（`restored`／`failed`）、`reason`、`finished_at`。

錯誤碼與狀態：

| 代碼 | 狀態 | 說明 |
| --- | --- | --- |
| `invalid_save_id` | 400 | id 格式不正確 |
| `save_not_found` | 404 | 找不到或不完整 |
| `save_incompatible` | 409 | 含有目前程式碼不認得的 migration |
| `save_in_progress` | 409 | 另一份存檔進行中，或有待套用的讀檔 |
| `save_delete_forbidden` | 409 | 自動存檔不能手動刪除 |
| `save_failed` | 500 | 建立存檔時發生非預期錯誤；部分檔案已清除，世界沒有變動 |

領域拒絕一律用 409，不用 403，前端也只在代碼為 `forbidden` 時才導向權限不足頁面，所以 `save_delete_forbidden` 不會被誤認為帳號權限問題。`save_failed` 是這個變更新增的實作錯誤碼，上游設計沒有列出，用來回報非預期的存檔失敗。

所有寫入都走 POST 並需要 CSRF token，也會額外送出 `gm_action`（`account`、`action`、`target`、`outcome`）。下載雖然不是寫入，但封存包含整個資料庫（含帳號密碼雜湊），所以每次下載也會送出 `gm_action`（`action` 為 `save_download`）。

## 事件

| 事件 | 等級 | context |
| --- | --- | --- |
| `save_created` | info | `save`、`kind`、`file_count`、`size_bytes` |
| `save_failed` | error | `save`、`kind`（排程關機失敗時另有 `stage`），附例外 |
| `save_deleted` | info | `save`、`kind`、`reason`（`manual`／`retention`） |
| `save_restore_requested` | info | `save`、`kind`、`pre_save` |
| `save_restored` | info | `save`、`kind` |
| `save_restore_failed` | warn | `save`、`kind`、`reason`（伺服器已在原本的世界上啟動） |
| `gallery_card_file_delete_deferred` | warn | `subject`、`identity`（存檔進行中，刪檔延後給啟動清理） |

預啟動工具不能使用 facade，只透過結果檔與 stdout 回報。
