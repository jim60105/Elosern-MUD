# Tasks — migrate-rules-maps-observability

前置：`add-observability-lint-gate` 已合併（facade、lint、凍結清單就緒）。契約見 `local://observability-contract.md`。

## 0. 基準盤點

- [ ] 0.1 跑 `tools.observability_lint check --json`，把 `world/rules/`＋`world/maps/` 的違規檔案清單（lint 實測 18 檔：rules 17＋maps 1）列為本 change 的可核對完成清單；此清單＝凍結清單中本批將移除的條目集合，並寫入本 change 備註作為 pre-freeze inventory
- [ ] 0.2 宣告共享檔紀律：`tools/observability_freeze.json` 與 `.github/evennia-shards.json` 僅在自有 commit 內改；與批次 3 並行時合併順序 2→3，批次 3 rebase 後 freeze 條目取兩批移除集合聯集

## 1. Clock

- [ ] 1.1 遷移 `world/rules/clock.py` 全部 log 呼叫至 facade（snake_case、context 補 tick／obj／key）；restore helper 吞點改 `rollback_restore_failed` warn（exc 入 context）
- [ ] 1.2 `advance()` 成功收尾發 `clock_advance`（tick_from、tick_to、scope）
- [ ] 1.3 事件断言測試（patch facade 或 capture）＋shards 登記；凍結清單移除 clock.py

## 2. Combat／settlement

- [ ] 2.1 遷移 `combat_session.py`、`cast_settlement.py`、`movement_settlement.py` log 呼叫與 restore 吞點
- [ ] 2.2 回合提交後發 `combat_round_settled`；終局結算後發 `settlement_done`
- [ ] 2.3 事件断言測試（含回滾路徑不發事件）＋shards 登記；凍結清單移除三檔

## 3. Action pipeline

- [ ] 3.1 遷移 `action.py`、`surfaces.py` log 呼叫與 restore 吞點
- [ ] 3.2 commit 收尾發 `action_commit`；回滾不發
- [ ] 3.3 事件断言測試＋shards 登記；凍結清單移除兩檔

## 4. rules 其餘（以 0.1 盤點清單為準，逐檔核對，不用 glob）

- [ ] 4.1 遷移盤點清單中 §1–§3 未列的全部 `world/rules/` 檔案（實測：affinity、caravan_arrivals、guild、guild_economy、guild_exams、guild_offers、items、equipment、economy、map_knowledge、npc_schedules、onboarding、party、shop_hours、displayed_stats、movement_settlement 等，以 0.1 為準）呼叫點與吞點：自由句子→event 碼、補 context、豁免註解附理由
- [ ] 4.2 凍結清單移除 0.1 清單內全部檔案（逐檔核對，非 glob）；`tools.observability_lint check` exit 0

## 5. maps

- [ ] 5.1 遷移 `world/maps/bootstrap.py`、`wilderness_population.py`（含 `except: continue` 吞點：改 warn＋context 或豁免）
- [ ] 5.2 focused：`world.maps` 測試綠；凍結清單移除

## 6. 驗證

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules world.maps`
- [ ] 6.2 Traceability：三個 MODIFIED 能力的新需求 id 以 `covers_requirement` 標註於 1.3/2.3/3.3 測試；`check` 綠
- [ ] 6.3 `openspec validate migrate-rules-maps-observability --strict`
