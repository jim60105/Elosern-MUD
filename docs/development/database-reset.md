# 開發資料庫重置與全新初始化操作手冊 (Developer Database Reset Runbook)

本手冊說明在專案架構、資料庫結構或內容基線（如 NPC 人物設定卡規範、生成任務酬載格式）發生不相容更新時，如何銷毀舊版開發資料庫並完成全新初始化。

---

## 1. 適用背景與架構原則

依據設計文件 `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §13b 條款，本專案在發布前之開發階段遵循**全新初始化原則**，不提供執行期向上相容解碼器（no legacy compatibility decoders）或資料庫線上遷移腳本（no database migration scripts）：

1. **全新初始化保證完整性**：所有生產環境 NPC 生成機制（服務公會主持人、考核官、開局夥伴、劇本生成任務佔位者等）在實例建立時，便直接寫入完整的七欄位緊湊人物設定卡（Compact NpcCard）與內容世代標記（`generation = NPC_PERSONA_CONTENT_GENERATION`）。
2. **開機校驗阻擋不完整世界**：伺服器開機時由 `npc_persona_roster_validation` 嚴格把關，若有名冊未完整初始化則立即中止開機（fail-loud）。
3. **舊版酬載嚴格阻擋（Fail-Closed）**：任務儲存庫採用嚴格解碼器，任何未升級的舊格式酬載（如帶有已淘汰的 `background` 欄位或舊三欄位設定者）在還原時均會拋出明確例外並拒絕載入。
4. **開發者唯一支援復原途徑**：當本機資料庫持有舊版資料時，支援的操作程序為**銷毀現有資料庫並重新初始化**。

---

## 2. ⚠️ 重要警示：進度與資料銷毀

> **警告**：執行資料庫重置將**永久刪除**該資料庫中的所有既有資料，包含：
> - 所有帳號與帳號關聯（Accounts）
> - 所有玩家角色、等級、能力值與背包物品（Player Characters & Inventory）
> - 所有 NPC 互動歷史、好感度記錄（Affinity & Relations）
> - 進行中的任務實例與世界動態狀態（Active Quests & Runtime State）
>
> 本程序**僅限於開發環境、測試環境與內部預發布驗證**使用。

---

## 3. 資料庫檔案位置確認

在執行刪除前，請確認目標資料庫檔案路徑：

- **開發環境預設資料庫**：
  依據 `server/conf/settings.py`：
  ```python
  DATABASES["default"]["NAME"] = os.path.join(GAME_DIR, "server", "db", "evennia.db3")
  ```
  專案預設開發資料庫檔案為：
  ```
  server/db/evennia.db3
  ```
  *(註：若使用客製設定，檔名可能為 `evennia.db`，請以本機有效 settings 的 `DATABASES["default"]["NAME"]` 為準。)*

- **測試環境保留資料庫**：
  依據 `server/conf/test_settings.py` 及 `AGENTS.md`：
  ```
  server/db/evennia-test.sqlite3
  ```

- **容器化部署環境**：
  依據 `compose.yaml`，容器內的 SQLite 資料庫目錄掛載於 `/app/server/db`，對應具名磁碟區（Volume）為 `evennia-db`。

---

## 4. 標準重置與全新初始化流程

請在專案根目錄下依序執行以下 5 個步驟：

### 步驟 1：停止 Evennia 伺服器
確保沒有正在運行的 Evennia 處理程序持有資料庫檔案鎖定：
```bash
uv run evennia stop
```

### 步驟 2：刪除現有資料庫檔案
刪除主資料庫檔案以及 SQLite 的預寫日誌（WAL）與共享記憶體（SHM）暫存檔：
```bash
rm -f server/db/evennia.db3 server/db/evennia.db3-shm server/db/evennia.db3-wal
```

### 步驟 3：執行資料庫結構全新遷移（Migrate）
執行 Django / Evennia 結構遷移，建立所有最新的資料庫資料表結構：
```bash
uv run --locked evennia migrate
```
此步驟會初始化全新資料表結構，包含 ObjectDB、ScriptDB、Attribute 表與所有相依模組。

### 步驟 4：啟動伺服器並建立全新世界資料
啟動 Evennia 伺服器：
```bash
uv run evennia start
```
Evennia 開機程序會自動呼叫 `server/conf/at_server_startstop.py` 中的 `at_server_start()`，按 `STARTUP_STEP_ORDER` 執行世界與 NPC 全新同步：
1. `npc_persona_roster_validation`：在世界同步前執行，嚴格檢驗所有靜態名冊設定、人物卡規範與對話表引用。
2. `sync_grid` 與 `sync_service_interiors`：同步王都、城鎮網格與服務室內空間地圖。
3. `sync_quest_runtime`：初始化任務系統執行期環境。
4. `sync_guild_economy`：透過 `sync_service_content` 自動生成所有公會服務主持人（Host）與考核官，並直接賦予標準人物設定卡與內容標記。
5. `sync_npc_schedules`：為全體 NPC 綁定生活日程標記。

### 步驟 5：驗證初始化成果
檢查伺服器日誌以確認所有開機步驟成功完成：
```bash
tail -n 100 server/logs/server.log
```
驗證重點：
- 搜尋 `startup_step` 事件，確認各步驟均正常耗時紀錄並回傳成功。
- 確認 `npc_persona_roster_validation` 步驟成功執行，證明靜態名冊定義完整無誤。
- 透過檢視腳本或登入確認經由 `sync_guild_economy` 生成的實例全體皆帶有最新版本標記（`generation == 1`，`persona_version >= 1`）與合規的緊湊人物設定卡。

---

## 5. 測試資料庫重置（Test Database）

本專案本機測試常使用 `--keepdb` 旗標以加速測試執行。若在結構變更後遭遇保留資料庫狀態殘留或無法載入的錯誤：

1. **直接刪除保留測試庫**：
   請先確保無正在運行的測試行程，然後刪除保留資料庫檔案：
   ```bash
   rm -f server/db/evennia-test.sqlite3
   ```
2. **或在執行測試時省略 `--keepdb` 並加上 `--noinput` 透過測試設定重建**：
   測試環境專用設定檔為 `server/conf/test_settings.py`，需搭配 `MUD_TEST_SETTINGS=1`：
   ```bash
   MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput tests.test_evennia_test_optimization_contract
   ```

---

## 6. 容器持久化磁碟區重置（Container Volume）

若在容器化開發環境中運行：

1. **僅重置資料庫磁碟區（建議）**：
   為了保留美術圖片快取（`evennia-art`）、去背模型（`evennia-rembg`）、日誌（`evennia-logs`）等無關資料，僅移除 `evennia-db` 磁碟區：
   ```bash
   docker compose stop evennia
   docker compose rm -f evennia
   docker volume rm mud_evennia-db  # 預設專案前綴，或使用 docker volume ls 查詢確認名稱
   ```
   隨後透過 bootstrap 服務重建結構並啟動：
   ```bash
   docker compose --profile bootstrap run --rm bootstrap
   docker compose up -d evennia
   ```

2. **全堆疊完整重置（選用）**：
   > **警告**：使用 `docker compose down -v` 會一併刪除所有具名磁碟區（包含生成的美術圖片、去背快取、翻譯模型與歷史日誌）。
   ```bash
   docker compose down -v
   ```
