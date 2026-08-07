# 遊戲指令總覽

本文以分類方式總覽所有玩家可在遊戲中輸入的指令，並連結到[指令參考](command-reference)中的詳細條目。每條指令的別名、語法與可用情境以指令參考為準，且由 `tests/test_command_docs.py` 契約測試保護。

情境標示「管理員」的指令需要 `Developer` 權限。登入前的指令（`connect`、`create`、`login`）不屬於遊戲內輸入，完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

## 探索與移動

| 指令 | 說明 |
| --- | --- |
| [`進入`](command-reference#進入) | 進入任務場景。 |
| [`goto`](command-reference#goto) | 沿最短路徑自動移動。 |
| [`map`](command-reference#map) | 檢視地圖。 |

## 對話

| 指令 | 說明 |
| --- | --- |
| [`talk`](command-reference#talk) | 與 NPC 交談。 |

## 時間跳躍

| 指令 | 說明 |
| --- | --- |
| [`rest`](command-reference#rest) | 休息並推進時間。 |
| [`sleep`](command-reference#sleep) | 睡到完全恢復。 |
| [`wait`](command-reference#wait) | 等待直到指定時段。 |

## 戰鬥

| 指令 | 說明 |
| --- | --- |
| [`engage`](command-reference#engage) | 與敵對魔物開戰。 |
| [`combat forfeit`](command-reference#combat-forfeit) | 投降結束戰鬥。 |
| [`combat actions`](command-reference#combat-actions) | 列出戰鬥動作與目標。 |

## 技能施放

| 指令 | 說明 |
| --- | --- |
| [`cast`](command-reference#cast) | 施放技能。 |

## 公會

| 指令 | 說明 |
| --- | --- |
| [`guild register`](command-reference#guild-register) | 註冊為冒險者。 |
| [`guild list`](command-reference#guild-list) | 查看任務板。 |
| [`guild accept`](command-reference#guild-accept) | 接取委託。 |
| [`guild log`](command-reference#guild-log) | 查看任務記錄。 |
| [`guild show`](command-reference#guild-show) | 查看任務詳情。 |
| [`guild abandon`](command-reference#guild-abandon) | 放棄任務。 |
| [`guild turnin`](command-reference#guild-turnin) | 回報任務並領取報酬。 |
| [`guild merit`](command-reference#guild-merit) | 查看階級與功績。 |
| [`guild request`](command-reference#guild-request) | 委託公會規劃任務。 |
| [`guild exam`](command-reference#guild-exam) | 申請公會考核。 |

## 經濟

| 指令 | 說明 |
| --- | --- |
| [`shop stock`](command-reference#shop-stock) | 查看商店庫存。 |
| [`buy`](command-reference#buy) | 購買物品。 |
| [`sell`](command-reference#sell) | 販賣物品。 |
| [`inventory`](command-reference#inventory) | 查看錢包與背包。 |

## 角色建立

| 指令 | 說明 |
| --- | --- |
| [`character`](command-reference#character) | 建立角色或使用預設角色。 |

## 管理員

| 指令 | 說明 |
| --- | --- |
| [`art status`](command-reference#art-status) | 列出美術資產記錄。 |
| [`art run`](command-reference#art-run) | 立即排空美術佇列。 |
| [`art retry`](command-reference#art-retry) | 重新排入失敗記錄。 |
| [`art requeue`](command-reference#art-requeue) | 強制重新生成主體。 |

## 系統與建造

| 指令 | 說明 |
| --- | --- |
| [`@teleport`](command-reference#teleport) | 傳送至其他位置。 |
| [`@open`](command-reference#open) | 建立出口。 |
