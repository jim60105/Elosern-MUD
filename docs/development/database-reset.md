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
  在 Docker / Podman 容器中，SQLite 資料庫檔案掛載於 `/var/evennia/server/db` 或具名磁碟區（Volume）。

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
1. `sync_grid` 與 `sync_service_interiors`：同步王都與城鎮室內空間地圖。
2. `sync_service_content`：自動生成所有公會服務主持人（Host）與考核官，並直接賦予標準人物設定卡與內容標記。
3. `npc_persona_roster_validation`：自動全面校驗伺服器名冊的完整性。
4. `sync_quest_runtime`：初始化任務系統執行期環境。

### 步驟 5：驗證初始化成果
檢查伺服器日誌以確認所有開機步驟成功完成：
```bash
tail -n 100 server/logs/server.log
```
驗證重點：
- 搜尋 `startup_step` 事件，確認各步驟均正常耗時紀錄並回傳成功。
- 確認 `npc_persona_roster_validation` 步驟成功執行，無任何缺少人物設定卡的異常回報。
- 登入遊戲或透過檢視腳本確認全體 NPC 皆帶有最新版本標記（`generation == 1`，`persona_version >= 1`）。

---

## 5. 測試資料庫重置（Test Database）

本專案本機測試常使用 `--keepdb` 旗標以加速測試執行。若在結構變更後遭遇保留資料庫狀態殘留或無法載入的錯誤：

1. **直接刪除保留測試庫**：
   ```bash
   rm -f server/db/evennia-test.sqlite3
   ```
2. **或在下次執行測試時省略 `--keepdb` 並加上 `--noinput`**：
   ```bash
   uv run evennia test --settings settings.py --noinput tests.test_evennia_test_optimization_contract
   ```

---

## 6. 容器持久化磁碟區重置（Container Volume）

若在容器化開發環境中運行：

1. 停止並移除容器與磁碟區：
   ```bash
   docker compose down -v
   ```
   或手動移除對應的資料庫 volume：
   ```bash
   docker volume rm mud_evennia_db
   ```
2. 重新啟動容器，容器啟動指令會自動執行 `evennia migrate` 與 `at_server_start()` 完成全新初始化。
