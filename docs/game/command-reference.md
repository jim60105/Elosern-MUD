# 遊戲指令參考

本文是玩家在遊戲中可直接輸入的指令參考，涵蓋三層輸入介面：本專案自行撰寫的玩家指令（含角色建立指令 `character`）、XYZGrid 貢獻指令（`goto`、`map`、`@teleport`、`@open`），以及保留的 Evennia 預設角色與帳號指令。每條指令的別名、語法與情境都受 `tests/test_command_docs.py` 的契約測試保護，任何指令的增刪或行為異動都必須在同一個變更中更新本文。

- 情境標示「管理員」的指令需要 `Developer` 權限（目前為 `art` 指令家族）。
- 登入前的指令（`connect`、`create`、`login`）不屬於遊戲內輸入，完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。
- Evennia 預設指令的完整細節請見頁尾索引表的 Evennia 官方文件連結。

## 探索與移動

### 進入

| 項目 | 內容 |
| --- | --- |
| 指令 | `進入` |
| 別名 | `enter` |
| 語法 | `進入` |
| 情境 | 一般（需有任務場景入口） |
| 說明 | 進入當前任務階段生成的任務場景。 |

### goto

| 項目 | 內容 |
| --- | --- |
| 指令 | `goto` |
| 別名 | `path` |
| 語法 | `goto <location>`、`path <location>`、`path clear` |
| 情境 | 一般（探索與移動） |
| 說明 | 沿最短路徑自動移動到同一區域內的指定地點；`path` 只顯示路線而不移動，`path clear` 清除目前路線。不帶參數時顯示目前路線；自動移動中再次輸入 `goto` 可中止。 |

### map

| 項目 | 內容 |
| --- | --- |
| 指令 | `map` |
| 別名 | （無） |
| 語法 | `map [<Zcoord>]`、`map list` |
| 情境 | 一般（探索，需建造者權限） |
| 說明 | 檢視目前區域的地圖，或指定座標層的地圖；`map list` 列出所有地圖。此為建造者導向的指令。 |

## 對話

### talk

| 項目 | 內容 |
| --- | --- |
| 指令 | `talk` |
| 別名 | `交談`、`對話` |
| 語法 | `talk <npc>`、`talk <npc> <keyword>` |
| 情境 | 一般（需有交談對象） |
| 說明 | 與眼前的 NPC 交談；對具備對話能力的對象可加上關鍵字（例如：公會、冒險、危險、再見）進行詢問。 |

## 時間跳躍

### rest

| 項目 | 內容 |
| --- | --- |
| 指令 | `rest` |
| 別名 | `休息` |
| 語法 | `rest <數字><s|m|h|d>` |
| 情境 | 一般 |
| 說明 | 休息指定的時間（例如 `rest 2h`），推進世界時間並回復生命與體力。 |

### sleep

| 項目 | 內容 |
| --- | --- |
| 指令 | `sleep` |
| 別名 | `睡眠` |
| 語法 | `sleep` |
| 情境 | 一般 |
| 說明 | 睡到生命與體力完全恢復，並推進世界時間。 |

### wait

| 項目 | 內容 |
| --- | --- |
| 指令 | `wait` |
| 別名 | `等待` |
| 語法 | `wait until <midnight|dawn|noon|dusk>` |
| 情境 | 一般 |
| 說明 | 等待直到指定的時段（`midnight`、`dawn`、`noon`、`dusk`），並推進世界時間。 |

## 戰鬥

### engage

| 項目 | 內容 |
| --- | --- |
| 指令 | `engage` |
| 別名 | `攻擊`、`戰鬥` |
| 語法 | `engage <target>` |
| 情境 | 戰鬥（需有敵對魔物） |
| 說明 | 與眼前的敵對魔物開始戰鬥。 |

### combat forfeit

| 項目 | 內容 |
| --- | --- |
| 指令 | `combat forfeit` |
| 別名 | `combat 投降`、`投降` |
| 語法 | `combat forfeit` |
| 情境 | 戰鬥（需在進行中的戰鬥） |
| 說明 | 在進行中的戰鬥或公會考核中投降認輸。 |

### combat actions

| 項目 | 內容 |
| --- | --- |
| 指令 | `combat actions` |
| 別名 | `combat 動作`、`戰鬥動作` |
| 語法 | `combat actions` |
| 情境 | 戰鬥（需在進行中的戰鬥） |
| 說明 | 列出戰鬥中可用的技能、目標代號與使用狀態。 |

## 技能施放

### cast

| 項目 | 內容 |
| --- | --- |
| 指令 | `cast` |
| 別名 | `施法` |
| 語法 | `cast <skill_key>[=<target_key>]` |
| 情境 | 一般（戰鬥內外皆可施放技能） |
| 說明 | 施放指定的技能；在戰鬥中可指定目標代號（`cast <技能>=<代號>` 或 `cast <技能>=<代號1,代號2>`）。 |

## 公會

### guild register

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild register` |
| 別名 | `guild 註冊`、`註冊公會`、`guild join` |
| 語法 | `guild register` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 向公會註冊成為冒險者，起始階級為 F。 |

### guild list

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild list` |
| 別名 | `guild 任務`、`任務列表` |
| 語法 | `guild list` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 查看任務板上目前開放、且符合你階級的任務。 |

### guild accept

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild accept` |
| 別名 | `guild 接取`、`接取任務` |
| 語法 | `guild accept <definition_key>` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 接取任務板上指定的委託。 |

### guild log

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild log` |
| 別名 | `guild 記錄`、`任務記錄` |
| 語法 | `guild log` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 查看自己的任務記錄與目前階段。 |

### guild show

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild show` |
| 別名 | `guild 詳情`、`guild detail`、`任務詳情` |
| 語法 | `guild show <quest_id>` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 查看單一任務的詳情、目標與報酬。 |

### guild abandon

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild abandon` |
| 別名 | `guild 放棄`、`放棄任務` |
| 語法 | `guild abandon <quest_id>` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 放棄指定的進行中任務。 |

### guild turnin

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild turnin` |
| 別名 | `guild 回報`、`回報任務`、`guild turn-in` |
| 語法 | `guild turnin <quest_id>` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 回報已完成任務並領取一次性的報酬。 |

### guild merit

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild merit` |
| 別名 | `guild 功績`、`公會階級` |
| 語法 | `guild merit` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 查看你的公會階級與累計功績，以及升階所需門檻。 |

### guild request

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild request` |
| 別名 | `guild 委託`、`委託任務` |
| 語法 | `guild request [討伐|採集|護衛|探索|緊急]` |
| 情境 | 公會（需已註冊冒險者） |
| 說明 | 委託公會規劃一份新的任務並張貼到任務板；未指定類型時預設為討伐。 |

### guild exam

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild exam` |
| 別名 | `guild 考核`、`公會考核` |
| 語法 | `guild exam [<rank>]` |
| 情境 | 公會（需當地考核官） |
| 說明 | 向考核官申請下一階級的公會考核；未指定階級時預設為 E。 |

## 經濟

### shop stock

| 項目 | 內容 |
| --- | --- |
| 指令 | `shop stock` |
| 別名 | `shop 庫存`、`商店庫存` |
| 語法 | `shop stock` |
| 情境 | 經濟（需當地商人） |
| 說明 | 查看當地商人的庫存、買賣價格與營業狀態。 |

### buy

| 項目 | 內容 |
| --- | --- |
| 指令 | `buy` |
| 別名 | `購買`、`shop buy` |
| 語法 | `buy <item_key> [數量]` |
| 情境 | 經濟（需當地商人） |
| 說明 | 向當地商人購買指定物品，未指定數量時購買 1 個。 |

### sell

| 項目 | 內容 |
| --- | --- |
| 指令 | `sell` |
| 別名 | `販賣`、`shop sell` |
| 語法 | `sell <item_key> [數量]` |
| 情境 | 經濟（需當地商人） |
| 說明 | 向當地商人販賣背包中的物品，未指定數量時販賣 1 個。 |

### inventory

| 項目 | 內容 |
| --- | --- |
| 指令 | `inventory` |
| 別名 | `背包`、`inv` |
| 語法 | `inventory` |
| 情境 | 一般（隨時可用） |
| 說明 | 查看你的錢包與背包內容。 |

## 角色建立

### character

| 項目 | 內容 |
| --- | --- |
| 指令 | `character` |
| 別名 | `角色` |
| 語法 | `character`、`character preset <key>`、`character create` |
| 情境 | 角色建立（建立模式取代一般指令，仍可用 help 與 quit） |
| 說明 | 進入角色建立流程：不帶參數時顯示可用的預設角色；`character preset <key>` 直接採用指定預設角色；`character create` 啟動互動式自訂精靈（姓名、年齡、種族、配點）。精靈中隨時可輸入 `cancel` 取消建立。尚未建立角色時，一般遊戲指令會被此模式取代，`help` 與 `quit` 仍然可用。 |

## 管理員

### art status

| 項目 | 內容 |
| --- | --- |
| 指令 | `art status` |
| 別名 | （無） |
| 語法 | `art status [scene|portrait|monster]` |
| 情境 | 管理員（需 Developer 權限） |
| 說明 | 列出美術資產記錄與其狀態；可依類型（場景、肖像、魔物）過濾。 |

### art run

| 項目 | 內容 |
| --- | --- |
| 指令 | `art run` |
| 別名 | （無） |
| 語法 | `art run [--limit N]` |
| 情境 | 管理員（需 Developer 權限） |
| 說明 | 立即排空美術佇列，工作會在背景執行；可指定單次處理上限。 |

### art retry

| 項目 | 內容 |
| --- | --- |
| 指令 | `art retry` |
| 別名 | （無） |
| 語法 | `art retry` |
| 情境 | 管理員（需 Developer 權限） |
| 說明 | 將所有失敗的美術記錄重新排入佇列。 |

### art requeue

| 項目 | 內容 |
| --- | --- |
| 指令 | `art requeue` |
| 別名 | （無） |
| 語法 | `art requeue <full-subject-key>` |
| 情境 | 管理員（需 Developer 權限） |
| 說明 | 強制重新生成指定的美術主體，即使原本沒有失敗記錄。 |

## 系統與建造

### @teleport

| 項目 | 內容 |
| --- | --- |
| 指令 | `@teleport` |
| 別名 | `@tel` |
| 語法 | `@teleport <目標位置>`、`@teleport (X,Y[,Z])`、`@teleport <物件> = <目標位置>` |
| 情境 | 一般（探索與建造，需建造者權限） |
| 說明 | 將自己（或指定物件）傳送至其他位置；目標可以是名稱或 (X,Y)、 (X,Y,Z) 座標。支援 `/quiet`、`/tonone`、`/loc` 等切換；完整用法請見 Evennia 官方文件。 |

### @open

| 項目 | 內容 |
| --- | --- |
| 指令 | `@open` |
| 別名 | （無） |
| 語法 | `@open <新出口>[;別名;..] = <目的地>`、`@open <新出口>[;別名;..],<回程出口>[;別名;..] = <目的地>`、`@open <新出口> = (X,Y,Z)` |
| 情境 | 一般（建造，需建造者權限） |
| 說明 | 從目前房間建立通往指定目的地或座標的出口；可選擇一併建立回程出口。 |

## Evennia 預設角色指令（CharacterCmdSet）

以下為保留的 Evennia 預設角色指令。完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

| 指令 | 描述 |
| --- | --- |
| `@about` | 檢視 Evennia 版本與平台資訊 |
| `@accounts` | 列出所有帳號（管理員） |
| `@alias` | 建立或檢視指令的個人別名 |
| `@cmdsets` | 檢視物件掛載的指令集 |
| `@copy` | 複製指令至另一物件 |
| `@cpattr` | 複製物件屬性 |
| `@create` | 建立新物件 |
| `@desc` | 設定物件的描述 |
| `@destroy` | 永久摧毀物件 |
| `@dig` | 開挖新房間並建立出口 |
| `@examine` | 檢視物件的完整詳細資料 |
| `@find` | 依名稱搜尋物件 |
| `@link` | 連結或重設出口的目標 |
| `@lock` | 設定或檢視物件的鎖定規則 |
| `@mvattr` | 移動或重新命名屬性 |
| `@name` | 重新命名物件 |
| `@objects` | 列出世界上所有物件（管理員） |
| `@open` | 從目前房間建立出口 |
| `@py` | 直接執行 Python 程式碼（管理員） |
| `@scripts` | 檢視與管理指令碼 |
| `@server` | 檢視伺服器資訊與設定 |
| `@service` | 檢視或重啟 Evennia 服務 |
| `@set` | 設定物件屬性 |
| `@sethome` | 設定你的重生點 |
| `@spawn` | 依照原型建立物件 |
| `@tag` | 檢視或管理標籤 |
| `@tasks` | 檢視背景工作佇列 |
| `@teleport` | 傳送至其他位置 |
| `@tickers` | 檢視與管理週期計時器 |
| `@time` | 檢視伺服器與世界時間 |
| `@tunnel` | 建立通往指定位置的隧道 |
| `@typeclass` | 變更物件的型別類別 |
| `@wipe` | 清除物件上的所有屬性 |
| `access` | 檢視或修改物件上的權限設定 |
| `ban` | 管理封鎖名單（管理員） |
| `batchcode` | 執行批次 Python 腳本（管理員） |
| `batchcommands` | 執行批次指令檔（管理員） |
| `boot` | 強制中斷使用者的連線（管理員） |
| `drop` | 丟棄背包中的物品 |
| `emit` | 對房間廣播一段訊息 |
| `force` | 強制他人執行指令（管理員） |
| `get` | 撿起地上的物品 |
| `give` | 將物品交給他人 |
| `help` | 開啟說明系統 |
| `home` | 立即返回重生點 |
| `inventory` | 檢視你的背包 |
| `look` | 檢視目前位置與物品 |
| `nick` | 建立或檢視個人暱稱 |
| `perm` | 檢視或設定權限 |
| `pose` | 以第三人稱演出動作 |
| `say` | 在房間內說話 |
| `setdesc` | 設定你的個人描述 |
| `sethelp` | 編輯文件的說明文字 |
| `unban` | 移除封鎖名單（管理員） |
| `unlink` | 移除出口的連結目標 |
| `wall` | 向所有連線廣播訊息（管理員） |
| `whisper` | 對房間內的特定對象說悄悄話 |

## Evennia 預設帳號指令（AccountCmdSet）

以下為保留的 Evennia 預設帳號指令；帳號指令與角色指令會在附身角色時合併。完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

| 指令 | 描述 |
| --- | --- |
| `@channel` | 管理聊天頻道 |
| `@examine` | 檢視帳號詳細資料 |
| `@py` | 執行 Python 程式碼（管理員） |
| `@reload` | 重新載入伺服器程式碼 |
| `@reset` | 重置伺服器狀態 |
| `@shutdown` | 關閉伺服器 |
| `charcreate` | 為帳號建立新角色（管理員） |
| `chardelete` | 刪除帳號的角色（管理員） |
| `color` | 調整色彩與樣式設定 |
| `discord2chan` | 將 Discord 頻道連結到遊戲頻道 |
| `grapevine2chan` | 將 Grapevine 頻道連結到遊戲頻道 |
| `help` | 開啟說明系統 |
| `ic` | 登入遊戲世界（附身角色） |
| `irc2chan` | 將 IRC 頻道連結到遊戲頻道 |
| `ircstatus` | 檢視 IRC 連結狀態 |
| `look` | 檢視目前位置與物品 |
| `nick` | 建立或檢視個人暱稱 |
| `ooc` | 離開遊戲世界（回到帳號層級） |
| `option` | 檢視與設定帳號選項 |
| `page` | 傳送私人訊息給其他帳號 |
| `password` | 變更你的密碼 |
| `quell` | 暫時以較低權限行動 |
| `quit` | 登出遊戲 |
| `rss2chan` | 將 RSS 摘要連結到遊戲頻道 |
| `style` | 調整文字樣式 |
| `userpassword` | 變更其他帳號的密碼（管理員） |
| `who` | 檢視線上玩家列表 |
