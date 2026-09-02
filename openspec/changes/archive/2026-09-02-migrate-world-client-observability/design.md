# Design — migrate-world-client-observability

機制契約全部沿用 `add-observability-lint-gate`；批次 2、3 已分別清空 rules/maps 與 ai/art/prompts 條目。本 change 收尾清空凍結清單。

## Context

facade 與 lint gate 已上線，rules/maps 與 ai/art 邊界事件已點亮。剩餘：`world/quests/`（含 quest transition 的 restore 吞點）、`typeclasses/` 2 檔、`web/` 4 檔。`quest_transition` 事件因跨 quests 目錄而排在本批次。

## Decisions

1. **`quest_transition` 發點選 `world/quests/transitions.py` 的成功收尾**：transition 的 apply 與 cache 復原都在此完成；bind/abandon 等 lifecycle 操作各自發對應 event（同一 event 名、stage context 表達差異），不在每個 caller 重複發。
2. **凍結清單清空是硬收尾**：本 change 合併後清單必須為空；加一條 contract test 斷言 `tools/observability_freeze.json` 無條目，防止回歸。
3. **`web/` 站點多為 presentation 降級路徑**：遷移時 event 碼帶 surface 標識（如 `art_push_unavailable`），context 帶 char pk＋surface 名。
4. **typeclasses 站點屬生命週期雜項**：按实际語義選 info/warn，不新增事件族。

## Risks / Trade-offs

- [最後一批若凍結清單殘留殭屍條目，shrink-only lint 會在 CI 報錯] → 這是機制設計預期；tasks 內先本地跑 `check` 再 commit。
- [`web/` 改動牽動 frozen webclient contract tests] → 純 Python 側 log 遷移，不動 wire 格式；跑 `web.webclient` focused suite 確認。

## Migration Plan

逐檔：換 import→補 context→restore 吞點改事件→quest_transition 落地→凍結清單清空→contract test→人工時間線驗收（設計文件 §9.4）。回滾 = revert。

## Open Questions

無。
