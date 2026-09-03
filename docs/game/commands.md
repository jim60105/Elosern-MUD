# 遊戲指令總覽

本文以分類方式總覽所有玩家可在遊戲中輸入的指令，並連結到[指令參考](/game/command-reference)中的詳細條目。每條指令的別名、語法與可用情境以指令參考為準，且由 `tests/test_command_docs.py` 契約測試保護。

情境標示「管理員」的指令需要 `Developer` 權限。登入前的指令（`connect`、`create`、`login`）不屬於遊戲內輸入，完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

## 探索與移動

| 指令 | 說明 |
| --- | --- |
| [`進入`](/game/command-reference?id=進入) | 進入任務場景。 |
| [`前往`](/game/command-reference?id=前往) | 沿最短路徑自動移動。 |
| [`地圖`](/game/command-reference?id=地圖) | 檢視地圖。 |
| [`看`](/game/command-reference?id=看) | 觀察所在位置或對象；查看對象時顯示對方當前所見的戰鬥數值，查看自己時顯示含來源明細的完整數值構成。 |
| [`回家`](/game/command-reference?id=回家) | 返回重生點。 |

## 說明與幫助

| 指令 | 說明 |
| --- | --- |
| [`說明`](/game/command-reference?id=說明) | 開啟說明系統。 |

## 對話

| 指令 | 說明 |
| --- | --- |
| [`talk`](/game/command-reference?id=talk) | 與 NPC 交談；對公會職員說「回報」可交回完成任務。 |
| [`invite`](/game/command-reference?id=invite) | 邀請眼前的 NPC 加入你的隊伍。 |
| [`leave`](/game/command-reference?id=leave) | 解散一名同伴。 |
| [`說`](/game/command-reference?id=說) | 在房間內說話。 |
| [`動作`](/game/command-reference?id=動作) | 以第三人稱演出動作。 |
| [`耳語`](/game/command-reference?id=耳語) | 私下對特定對象說話。 |

## 時間跳躍

| 指令 | 說明 |
| --- | --- |
| [`rest`](/game/command-reference?id=rest) | 休息並推進時間；可用 `practice <技能>` 宣告每整小時熟練度修煉。 |
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
| [`cast`](/game/command-reference?id=cast) | 施放技能；持有屬性主宰者可搭配 `@<scale>` 比例調整威力與 MP 消耗。性愛技能亦屬可施放之列，隨遊玩解鎖後可經 `combat actions` 的分類檢視。 |
| [`lineage`](/game/command-reference?id=lineage) | 檢視技能系譜：各系的熟練度、見頂節點與解鎖門檻。 |

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
| [`guild request`](/game/command-reference?id=guild-request) | 委託公會規劃任務（護衛尚未開放）。 |
| [`guild exam`](/game/command-reference?id=guild-exam) | 申請公會考核。 |

## 知識圖鑑

| 指令 | 說明 |
| --- | --- |
| [`lore`](/game/command-reference?id=lore) | 檢視已發現的知識圖鑑。 |

## 經濟

| 指令 | 說明 |
| --- | --- |
| [`shop stock`](/game/command-reference?id=shop-stock) | 查看商店庫存。 |
| [`buy`](/game/command-reference?id=buy) | 購買物品。 |
| [`sell`](/game/command-reference?id=sell) | 販賣物品。 |
| [`inventory`](/game/command-reference?id=inventory) | 查看錢包、背包與角色數值構成（與角色面板同源）。 |
| [`使用`](/game/command-reference?id=使用) | 使用一件持有物品；戰鬥中佔用一個回合。 |
| [`裝備`](/game/command-reference?id=裝備) | 裝備或卸下裝備；免費動作，飾品上限 5 件。 |
| [`拿`](/game/command-reference?id=拿) | 撿起地上的物品，登錄物品會同步計入背包清單。 |
| [`丟`](/game/command-reference?id=丟) | 丟棄背包中的物品，登錄物品的背包清單記錄會同步移除。 |
| [`給`](/game/command-reference?id=給) | 將物品交給他人，登錄物品的背包清單記錄會同步移除。 |

## 角色建立與個人化

| 指令 | 說明 |
| --- | --- |
| [`character`](/game/command-reference?id=character) | 建立角色或使用預設角色。 |
| [`character concept`](/game/command-reference?id=character-concept) | 依角色構想生成提案，提案值預填姓名與年齡，Enter 採納或輸入覆寫，再完成建立。 |
| [`設定描述`](/game/command-reference?id=設定描述) | 設定你的個人描述。 |
| [`設定背景`](/game/command-reference?id=設定背景) | 設定或檢視你的背景（風味文字）。 |
| [`設定個性`](/game/command-reference?id=設定個性) | 設定或檢視你的個性（風味文字）。 |
| [`設定生平`](/game/command-reference?id=設定生平) | 設定或檢視你的生平（背景故事，風味文字）。 |
| [`設定習慣`](/game/command-reference?id=設定習慣) | 設定或檢視你的習慣（風味文字）。 |
| [`title`](/game/command-reference?id=title) | 檢視稱號冊（list/codex）、更換掛上的稱號或異名、回覆異名提名投票，並以兩步確認移除異名。 |
| [`暱稱`](/game/command-reference?id=暱稱) | 建立或檢視個人暱稱。 |

## 帳號與連線

| 指令 | 說明 |
| --- | --- |
| [`登出`](/game/command-reference?id=登出) | 登出遊戲。 |
| [`在線`](/game/command-reference?id=在線) | 檢視線上玩家列表。 |
| [`離開角色`](/game/command-reference?id=離開角色) | 離開角色身分（OOC）。 |
| [`進入世界`](/game/command-reference?id=進入世界) | 附身角色進入遊戲。 |
| [`傳訊`](/game/command-reference?id=傳訊) | 傳送私人訊息。 |
| [`密碼`](/game/command-reference?id=密碼) | 變更你的密碼。 |
| [`選項`](/game/command-reference?id=選項) | 檢視與設定帳號選項。 |
| [`連線`](/game/command-reference?id=連線) | 檢視目前的連線。 |
| [`色彩`](/game/command-reference?id=色彩) | 測試與調整色彩。 |
| [`樣式`](/game/command-reference?id=樣式) | 調整文字樣式。 |
| [`降權`](/game/command-reference?id=降權) | 暫時以較低權限行動。 |

## 管理員

| 指令 | 說明 |
| --- | --- |
| [`art status`](/game/command-reference?id=art-status) | 列出美術資產記錄。 |
| [`art run`](/game/command-reference?id=art-run) | 立即排空美術佇列。 |
| [`art retry`](/game/command-reference?id=art-retry) | 重新排入失敗記錄。 |
| [`art requeue`](/game/command-reference?id=art-requeue) | 強制重新生成主體。 |
| [`art options`](/game/command-reference?id=art-options) | 查詢 sd-webui 可選名稱。 |
| [`art health`](/game/command-reference?id=art-health) | 檢視 sd-webui 連線與管線狀態。 |

## 系統與建造

| 指令 | 說明 |
| --- | --- |
| [`@teleport`](/game/command-reference?id=teleport) | 傳送至其他位置。 |
| [`@open`](/game/command-reference?id=open) | 建立出口。 |
