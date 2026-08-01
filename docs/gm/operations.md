# 維運與驗證

世界資料、任務目錄與公會經濟會在伺服器啟動時以可重複執行的方式同步。內容異動後，先在本機驗證資料與測試，再重新啟動服務套用登錄資料。既有持久狀態由其對應模組管理，啟動同步不應被當成手動覆寫玩家進度的工具。

## 啟動順序

`server/conf/at_server_startstop.py` 的 `at_server_start()` 會依序同步世界資料、網格地圖、荒野、服務室內空間、任務執行期與公會經濟。任務目錄先註冊，公會經濟才會讀取其中的任務鍵與報酬設定。

在容器環境中，使用 Podman Compose。第一次使用新的資料庫卷時，先執行一次性 bootstrap，再啟動服務。

```sh
podman compose --profile bootstrap run --rm bootstrap
podman compose up
```

本機 Python 指令一律經由鎖定的 `uv` 環境執行。不要直接以系統 Python、`pip` 或手動編輯 `uv.lock` 執行專案作業。

## 內容變更檢查清單

- 角色卡先通過匯入驗證，並檢查拒絕與警告。
- 任務定義中的物品、魔物、錨點、地圖與公會階級鍵都存在於登錄表。
- 公會報酬使用整數銅幣，且符合該階級的報酬範圍。
- 新任務的事件推進與失敗情境已有確定性測試。
- 異動不直接修改玩家任務紀錄、金錢、背包或戰鬥狀態。

## 驗證命令

先驗證角色資料，再執行與變更範圍相符的測試。任務、角色載入或伺服器整合有變動時，交付前執行完整 Evennia 測試套件。

```sh
uv run --locked -m world.imports.validate world/imports/examples/example_character.json
uv run --locked evennia test --settings settings.py world.imports world.quests world.rules commands
uv run --locked evennia test --settings settings.py .
uv run --locked -m unittest discover tests
uv run --locked python -m compileall -q world typeclasses commands server
git diff --check
```

OpenSpec 變更中的內容工作還需遵循該變更的 `tasks.md`。在交付前，執行 `openspec validate <change> --strict`，並確認勾選的工作項目都有對應的已驗證實作。

## 常見失敗訊息的處理方向

`record_type` 或 `schema_version` 錯誤表示角色 JSON 不符合目前格式。`race`、`subrace`、技能、物品或魔物階級未知，表示資料引用了尚未登錄的鍵。`disguised_stats` 鍵不在 `stats` 中，表示展示層引用了不存在的真實數值。這些情況應修正來源資料或先新增登錄值，不要降低驗證條件。

任務目錄註冊衝突表示同一任務鍵已帶有不同內容。請為新任務使用新鍵；若修改既有任務，先評估是否已有持久任務紀錄引用該定義。公會報酬驗證失敗時，核對 `definition_key`、物品鍵、階級報酬區間與整數數值。

服務人員不存在或任務板沒有項目時，先確認啟動同步已完成，角色位於正確分會的服務 NPC 所在房間，並已完成公會註冊。任務板只提供符合玩家目前階級的本地分會任務。
