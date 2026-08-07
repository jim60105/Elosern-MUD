# 遊戲指令總覽

本文以分類方式總覽所有玩家可在遊戲中輸入的指令，並連結到[指令參考](/game/command-reference)中的詳細條目。每條指令的別名、語法與可用情境以指令參考為準，且由 `tests/test_command_docs.py` 契約測試保護。

情境標示「管理員」的指令需要 `Developer` 權限。登入前的指令（`connect`、`create`、`login`）不屬於遊戲內輸入，完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

## 探索與移動

| 指令 | 說明 |
| --- | --- |
| [`進入`](/game/command-reference?id=進入) | 進入任務場景。 |
| [`goto`](/game/command-reference?id=goto) | 沿最短路徑自動移動。 |
| [`map`](/game/command-reference?id=map) | 檢視地圖。 |

## 對話

| 指令 | 說明 |
| --- | --- |
| [`talk`](/game/command-reference?id=talk) | 與 NPC 交談。 |

## 時間跳躍

| 指令 | 說明 |
| --- | --- |
| [`rest`](/game/command-reference?id=rest) | 休息並推進時間。 |
| [`sleep`](/game/command-reference?id=sleep) | 睡到完全恢復。 |
| [`wait`](/game/command-reference?id=wait) | 等待直到指定時段。 |

## 戰鬥

| 指令 | 說明 |
| --- | --- |
| [`engage`](/game/command-reference?id=engage) | 與敵對魔物開戰。 |
| [`combat forfeit`](/game/command-reference?id=combat-forfeit) | 投降結束戰鬥。 |
| [`combat actions`](/game/command-reference?id=combat-actions) | 列出戰鬥動作與目標。 |

## 技能施放

| 指令 | 說明 |
| --- | --- |
| [`cast`](/game/command-reference?id=cast) | 施放技能。 |

## 公會

| 指令 | 說明 |
| --- | --- |
| [`guild register`](/game/command-reference?id=guild-register) | 註冊為冒險者。 |
| [`guild list`](/game/command-reference?id=guild-list) | 查看任務板。 |
| [`guild accept`](/game/command-reference?id=guild-accept) | 接取委託。 |
| [`guild log`](/game/command-reference?id=guild-log) | 查看任務記錄。 |
| [`guild show`](/game/command-reference?id=guild-show) | 查看任務詳情。 |
| [`guild abandon`](/game/command-reference?id=guild-abandon) | 放棄任務。 |
| [`guild turnin`](/game/command-reference?id=guild-turnin) | 回報任務並領取報酬。 |
| [`guild merit`](/game/command-reference?id=guild-merit) | 查看階級與功績。 |
| [`guild request`](/game/command-reference?id=guild-request) | 委託公會規劃任務。 |
| [`guild exam`](/game/command-reference?id=guild-exam) | 申請公會考核。 |

## 經濟

| 指令 | 說明 |
| --- | --- |
| [`shop stock`](/game/command-reference?id=shop-stock) | 查看商店庫存。 |
| [`buy`](/game/command-reference?id=buy) | 購買物品。 |
| [`sell`](/game/command-reference?id=sell) | 販賣物品。 |
| [`inventory`](/game/command-reference?id=inventory) | 查看錢包與背包。 |

## 角色建立

| 指令 | 說明 |
| --- | --- |
| [`character`](/game/command-reference?id=character) | 建立角色或使用預設角色。 |

## 管理員

| 指令 | 說明 |
| --- | --- |
| [`art status`](/game/command-reference?id=art-status) | 列出美術資產記錄。 |
| [`art run`](/game/command-reference?id=art-run) | 立即排空美術佇列。 |
| [`art retry`](/game/command-reference?id=art-retry) | 重新排入失敗記錄。 |
| [`art requeue`](/game/command-reference?id=art-requeue) | 強制重新生成主體。 |

## 系統與建造

| 指令 | 說明 |
| --- | --- |
| [`@teleport`](/game/command-reference?id=teleport) | 傳送至其他位置。 |
| [`@open`](/game/command-reference?id=open) | 建立出口。 |
