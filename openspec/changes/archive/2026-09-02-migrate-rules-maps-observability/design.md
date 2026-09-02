# Design — migrate-rules-maps-observability

機制與格式契約全部沿用 `add-observability-lint-gate`（facade API、事件目錄 §4.2、凍結清單 ratchet）。本 change 無新機制，只有遷移與事件落地，故本檔極短。

## Context

facade 與 lint gate 已上線；`world/rules/` 與 `world/maps/` 在凍結清單內。rules 是回滾語義最重的目錄：restore helper（`_restore_attribute` 等）在 clock、action、cast_settlement、combat_session、equipment、guild 各檔重複出現，內層 `except: pass` 是本次最大盲區。

## Decisions

1. **每個子目錄一個 commit**：rules-clock、rules-combat、rules-action/settlement、rules-guild/economy/items 其餘、maps——凍結清單同步逐檔移除，任一 commit 內 `check` 綠。
2. **還原失敗的語義不動**：restore helper 保持 best-effort（吞掉以不掩蓋原始例外），只把吞掉改為 `log_warn("rollback_restore_failed", context={...}, exc=error)`。事件級別為 warn，不是 error：回滾已發生，這是補盲不是改語義。
3. **提交點事件放在各檔案既有的成功收尾處**，不重構控制流：單行 info，context 只放該處現成可得的標識（設計 §4.2 表）。實作落地（rubber-duck 計畫審查 BLOCKER 採納）：邊界事件一律經 `transaction.on_commit` 註冊在成功路徑內——rules 的 atomic 常是外層交易（item／combat）的 savepoint，只有 on_commit 保證「最外層持久提交才發、回滾即丟棄」；`combat_round_settled` 限普通 `run_round` 分支（overwhelm 壓縮不是「一普通回合」）、tick 走非建立式的 `read_world_clock()`、`settlement_done` 的 notifications 為顯式傳入的提交後通知行數而非 `len(logs)`。
4. **ms 用 `time.monotonic` 差值**於 commit／settlement 邊界成對計時，不放高頻迴圈內。

## Risks / Trade-offs

- [提交點事件在 combat 長戰鬥增加 log 行] → 每回合 1 行 info，單人規模可接受；更細細節屬 `log_debug`。
- [遷移時誤動回滾控制流引入 regression] → 每 commit 必跑該檔既有 focused tests；語義改動零容忍，事件只加不改。

## Migration Plan

按目錄逐檔：換 import→補 event/context→restore 吞點改 warn 事件→提交點發 info→凍結清單移除該檔→focused tests。回滾 = revert。

## Open Questions

無。
