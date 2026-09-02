# Tasks — migrate-world-client-observability

前置：批次 1–3 已合併，凍結清單僅剩 `world/quests/`、`typeclasses/`、`web/` 條目。契約見 `local://observability-contract.md`。

## 1. Quests

- [ ] 1.1 遷移 `world/quests/transitions.py`、`scene_builder.py`、`deadlines.py`、`runtime.py` log 呼叫與 restore 吞點（`rollback_restore_failed` warn 或豁免註解附理由）
- [ ] 1.2 `transitions.py` 成功收尾發 `quest_transition`（char、quest、stage_from、stage_to）；回滾不發
- [ ] 1.3 事件断言測試（含回滾不發事件）＋shards 登記；凍結清單移除四檔

## 2. Typeclasses／web

- [ ] 2.1 遷移 `typeclasses/characters.py`、`typeclasses/exits.py` log 站點（按語義選級別、補 context）
- [ ] 2.2 遷移 `web/webclient/actions/dispatcher.py`、`presentation/art_push.py`、`coordinator.py`、`registry.py`：降級路徑 event 碼帶 surface 標識＋context（char pk、surface 名）
- [ ] 2.3 `typeclasses/tests/test_npc_dialogue.py`、`web/webclient/actions/tests/test_dialogue_composition.py`、`web/webclient/presentation/tests/test_art_push.py` 改 patch facade
- [ ] 2.4 凍結清單移除上述六檔

## 3. 清空凍結清單（硬收尾）

- [ ] 3.1 `tools/observability_freeze.json` 清空為空清單；本地 `tools.observability_lint check` exit 0
- [ ] 3.2 新增 contract test：斷言凍結清單無條目（防回歸），登記於 top-level `tests/`

## 4. 驗證

- [ ] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.quests typeclasses web.webclient`
- [ ] 4.2 Traceability：`quest-lifecycle` 新需求 id 以 `covers_requirement` 標註於 1.3 測試；`check` 綠
- [ ] 4.3 人工時間線驗收（設計文件 §9.4）：開 server 走數個命令＋一次戰鬥或 quest transition，`server/logs/` 可重建時間線；结果記錄於 change 備註
- [ ] 4.4 `openspec validate migrate-world-client-observability --strict`
