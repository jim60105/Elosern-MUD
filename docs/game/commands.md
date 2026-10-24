# 遊戲指令總覽

本文以分類方式總覽所有玩家可在遊戲中輸入的指令，並連結到[指令參考](/game/command-reference)中的詳細條目。每條指令的別名、語法與可用情境以指令參考為準，且由 `tests/test_command_docs.py` 契約測試保護。

情境標示「管理員」的指令需要 `Developer` 權限。登入前的指令（`connect`、`create`、`login`）不屬於遊戲內輸入，完整說明請見 [Evennia 官方文件](https://evennia.com/docs/latest/Components/Commands.html)。

## 探索與移動

| 指令 | 說明 |
| --- | --- |
| [`進入`](/game/command-reference?id=進入) | 進入任務場景。 |
| [`前往`](/game/command-reference?id=前往) | 沿最短路徑自動移動。 |
| [`地圖`](/game/command-reference?id=地圖) | 檢視地圖。 |
| [`看`](/game/command-reference?id=看) | 觀察所在位置或對象；房間外觀只顯示名稱、描述、內容物與出口，不再自動附上文字小地圖（網頁客戶端另以地圖面板呈現）。查看對象時顯示對方當前所見的戰鬥數值，查看自己時顯示含來源明細的完整數值構成。 |
| [`回家`](/game/command-reference?id=回家) | 返回重生點。 |

## 說明與幫助

| 指令 | 說明 |
| --- | --- |
| [`說明`](/game/command-reference?id=說明) | 開啟說明系統。 |

網頁客戶端的頂端列依序是 **隊伍**、**任務**、**地圖** 三個入口，接著是工具圖示 **信件**、**圖鑑**、**稱號冊**、**角色肖像圖庫**（可用時才出現）與 **說明**，最後是 **設定**。**隊伍** 會開啟隊伍視窗，停在上次離開的分頁；戰鬥中沒有 **任務** 與 **地圖**。焦點不在文字輸入欄時，也可以用快捷鍵開啟：P 隊伍、B 背包、C 狀態、K 技能、L 系譜、J 任務、M 地圖。按住 Ctrl、Alt、Shift 等修飾鍵、輸入法組字中、或有確認問題開著時，快捷鍵不會作用；該介面目前不可用時（例如戰鬥中按 M），按鍵也不會有反應。

**地圖** 有 **區域** 與 **世界** 兩個分頁：在城鎮、地城與室內預設開啟區域地圖，在荒野預設開啟世界地圖，兩個分頁各自記得上次的平移與縮放。地圖開著時，方向鍵平移，＋／－ 在預設比例間縮放，C 回到目前位置，0 顯示全圖，1／2 切換分頁；拖曳可平移，滾輪可連續縮放，點選地點、分區或委託會在右側顯示詳情，相鄰的出口可按 **前往** 移動。左上的 **委託** 清單列出所有已接下的委託，畫面外的委託會在邊緣以指標提示。Esc 依序關閉圖例或清單、選取的詳情，最後關閉地圖。

隊伍視窗集中呈現成員的背包、狀態、技能與系譜；商店也沿用同一個成員選擇。同行與附身、交換物品、戰鬥限制、系譜菱形圖例及商店單一價格的規則，請開啟工具列的 **說明 → 隊伍**。隊伍與商店視窗只顯示目前狀態、數值與無法操作的原因。

## 對話

| 指令 | 說明 |
| --- | --- |
| [`talk`](/game/command-reference?id=talk) | 與 NPC 交談；對公會職員說「回報」可交回完成任務。 |
| [`invite`](/game/command-reference?id=invite) | 邀請眼前的 NPC 成為一般同伴；護送同行者仍可接受邀請。 |
| [`leave`](/game/command-reference?id=leave) | 移除一般同伴身分；有效護送委託仍保留同行關係。 |
| [`possess`](/game/command-reference?id=possess) | 附身至同伴身上行動。 |
| [`unpossess`](/game/command-reference?id=unpossess) | 結束附身並歸位。 |
| [`說`](/game/command-reference?id=說) | 在房間內說話。 |
| [`動作`](/game/command-reference?id=動作) | 以第三人稱演出動作。 |
| [`耳語`](/game/command-reference?id=耳語) | 私下對特定對象說話。 |

## 時間跳躍

| 指令 | 說明 |
| --- | --- |
| [`rest`](/game/command-reference?id=rest) | 等待並推進時間；可用 `practice <技能>` 宣告每整小時熟練度修煉，只有實際清醒的整小時才會結算。 |
| [`修煉`](/game/command-reference?id=修煉) | `修煉 <技能> [= <成員>]` 為成員排入修煉；只記錄排入，下一次休息、睡眠或等待才依完整小時結算。 |
| [`sleep`](/game/command-reference?id=sleep) | 自願入睡：預設或 `until-recovered` 恢復至生命、法力、體力與精神儲備全滿，也可用 `sleep <時長>` 指定時長；`sleep all` 讓在場全員一起入睡，`sleep continue` 續睡目前的睡眠。只有確實流逝的自願睡眠才會開啟 `sleep dream` 的夢境協作。 |
| [`handoff`](/game/command-reference?id=handoff) | 檢視或確認沉睡身體的控制權交接：列出回到自己身體或接手清醒同伴的選項與精神儲備；取消不推進時間。 |
| [`dream`](/game/command-reference?id=dream) | 查看夢境剩餘交流次數，商談故事方向、儲存草稿、確認或醒來。 |
| [`wait`](/game/command-reference?id=wait) | 等待直到指定時段。 |

網頁客戶端的 **等待** 提供黎明、完全恢復的睡眠與自訂時數的等待，自訂等待上限為 12 小時。修煉是持續有效的排入：文字客戶端用 `修煉 <技能> [= <成員>]`，網頁客戶端在 **隊伍 → 技能** 選定成員與主動技能後按 **排入修煉**（送出該成員的識別碼）。排入本身不推進時間，下一次休息、睡眠或等待才會依完整小時給付熟練度；只有該成員在該段時間內保持清醒才會結算並消耗排入，沉睡成員的排入會保留到下一次清醒的等待。一般休息與睡眠不會自行宣告修煉，但會結算在場成員既有的排入。

隊伍同行時，任何在場成員處於強制沉睡都會使旅行保持原地：一般出口、聚落出口、荒野步伐與跨層關卡都會在移動前拒絕，附身清醒成員也不能搬運或傳送沉睡者。安全的室內仍可查看狀態、與當地對象互動或戰鬥；沒有清醒成員時，可直接等待到第一位成員自然甦醒，等待會在該邊界停止，不會在背景推進時間。

移動的耗時依距離、地形與隊伍最慢成員的疲勞階段分段計算；路段中途越過疲勞門檻時，只有剩下的路程改用較慢的速度，整趟仍只取整一次。出發前若預估任何在場成員會在抵達前耗盡精神儲備，該次移動會被拒絕，時間、位置、精神儲備與地圖知識都不變；恰好在抵達時耗盡則照常完成，並在目的地轉為強制沉睡，下一次出發會因沉睡而被拒絕。

夢境協作需明確選擇。文字客戶端使用 `sleep dream`，網頁客戶端在等待畫面選擇「睡眠並進入夢境協作」。一般睡眠、休息與等待不會開啟對話。安全檢查拒絕睡眠時也不會開啟夢境；只有確實有正向流逝時間的自願睡眠才會開啟夢境，零秒或強制睡眠不會。

當目前控制的身體自願入睡時，控制權不會自動轉移。`handoff` 會列出當下合法的選項：回到自己的身體，或接手同一房間內清醒、活著且能行動的同伴，並標明雙方的精神儲備百分比。`handoff <編號>` 確認該次交接；`handoff cancel`（或 `取消`）只關閉交接，不推進時間、不宣稱完成任何睡眠。選項在確認時會重新驗證帳號、連線、成員身分、同房與清醒狀態，已移動、入睡、離隊或死亡的候選人會被拒絕並重新列出，不會被替換成別人。沉睡的身體不能施法、移動或使用物品，只能查看狀態、交接，或以 `sleep continue` 續睡同一段已接受的睡眠；重新連線會保留同一份睡眠紀錄，不會重播時間。網頁客戶端在隊伍視窗中對候選同伴按 **附身**、對沉睡同伴按 **解除附身** 即送出同一個確認；戰鬥中合法的睡眠交接仍可使用，戰鬥草稿與時間都不會改變。

睡眠分為恢復與明確時長兩種：恢復模式以最慢的生命、法力、體力或精神儲備恢復時間為預定甦醒時間，滿儲備不會把明確時長縮短；兩者都受既有睡眠上限約束，達到上限仍未全滿時會如實回報尚未完全恢復。接受睡眠只先寫入姿勢與持久睡眠紀錄，不推進時間；玩家可以交接控制權、以 `sleep continue` 續睡，或在其他成員的等待、行動與戰鬥結算中由世界時鐘被動甦醒，控制權不會因此被搶走。`sleep all` 只選取目前房間內有效的在世成員，已在睡眠中的成員保留原本目標，遠端成員不變；任何一位在場成員無法入睡時整次入睡都不會寫入。

夢境顯示場景與對方的話語，每次成功送達的回應才消耗交流額度，上限為六次。`dream say <文字>` 提出方向，`dream draft [故事方向]` 儲存私人草稿，`dream confirm [故事方向]` 明確確認並提交方向，`dream awaken` 醒來。六次用完後仍可儲存、確認與醒來。生成失敗或回應尚未送達時，醒來也不需模型服務。夢境交流與離開不會再推進時間或重複恢復身體。
方向若帶著可執行的需求（指定的地點、需要的新角色或私人委託），`dream` 會以可讀文字列出；確認時必須回報你實際看過的版本與同一份摘要，尚未看過、已過期或已被改寫的需求不會被默默寫入（改寫摘要後網頁客戶端會先提示你「記下念頭」，`dream draft` 會把改寫後的方向與原本的需求存成新版本），方向仍保留為未確認草稿。確認成功後只會收到「正在準備中」的收據，這不是成局；是否真的遇上遭遇，仍要由你在世界中探索。

## 戰鬥

| 指令 | 說明 |
| --- | --- |
| [`engage`](/game/command-reference?id=engage) | 與敵對魔物開戰。 |
| [`combat forfeit`](/game/command-reference?id=combat-forfeit) | `combat forfeit` 取得整隊投降的確認提示，`combat forfeit confirm <token>` 才是確認；未確認前不改變戰況、不丟棄已選指令，也不推進時間。 |
| [`combat retreat`](/game/command-reference?id=combat-retreat) | `combat retreat` 取得整隊撤退的確認提示，`combat retreat confirm <token>` 才嘗試脫離戰鬥；戰鬥中施放 `flee` 取得的是同一份提示。這兩個指令的 `confirm` 是同一個確認入口，token 綁定哪一種整隊操作就執行哪一種。 |
| [`combat command`](/game/command-reference?id=combat-command) | `combat command <actor-token> skill <skill_key>[@<scale>][=<targets>]`、`combat command <actor-token> item <item_key>[=<target-token>]`、`combat command <actor-token> defend/dodge/taunt[=<enemy-token>]`：以同伴代號（`a2` 等）確認該成員的指令，不需要附身該成員；再次輸入同一成員即改選並取代前一筆，最後一位成員確認後自動結算本回合。 |
| [`combat actions`](/game/command-reference?id=combat-actions) | `combat actions [<actor-token>]` 列出指定成員（省略代號時是你）的技能、道具與戰術，以及本回合的指令進度；列出同伴的指令同樣不需要附身。 |

戰鬥中的生理疲勞只在終局結算時一次計入（完成回合數 × 6 秒），不會每回合消耗精神儲備、推進世界時間或自然醒來；沉睡會持續到終局結算，除非日後有明確的狀態效果改變它。沉睡的成員仍在場上、仍可被選為目標，但不會被要求下達指令，也不會自動出手，畫面以「沉睡中，無法行動」標示，與倒地或擊破不同；沉睡時仍可指揮清醒的同伴。

終局結算會依每位成員在戰鬥中的實際姿態計入：整場清醒者以每秒 12 單位消耗精神儲備，整場沉睡者以每秒 12 單位恢復；若成員在回合邊界被明確喚醒或轉為沉睡，只按各自的清醒與沉睡秒數分別計算，不會把整場都算成睡眠。清醒者在戰鬥中即使降到 0.1% 也不提前倒下，只有在終局一次扣至零並轉為強制沉睡；沉睡者在終局結算恢復到 20% 才會自然甦醒，未達門檻者保持沉睡、隊伍仍無法旅行，但清醒成員的本地行動不受影響。已倒地或已判定戰敗的成員不會因精神恢復而甦醒或復活。終局結算只發生一次：重新連線、重新載入或重試終局操作都不會再次扣除或恢復同一段戰鬥時間。

若開戰當下所有在場隊友都處於強制沉睡，戰鬥不會等待指令、不會讓敵方行動，也不會模擬旁觀回合；系統直接以零個完成回合進入原本的終局判定（一般戰鬥為戰敗，公會考核為不合格），既有戰敗後續與考核復原照常執行，世界時間也不會因此多出虛構的戰鬥秒數。其餘沒有可下令成員的情況仍維持原本的暫停與隊伍退出選項。

## 技能施放

| 指令 | 說明 |
| --- | --- |
| [`cast`](/game/command-reference?id=cast) | 施放技能；持有屬性主宰者可搭配 `@<scale>` 比例調整威力與 MP 消耗。`cast ... 由 <成員>` 改以同隊且同房的成員身分施法：探索中由該成員支付 MP、自身效果與熟練度都記在該成員，時間消耗與你相同；戰鬥中則替該成員存下與 `combat command` 相同的技能指令，不立即施法。探索中瞄準同場怪物會直接開戰並以該技能為開場指令（同伴指令到齊後才結算回合）；以 `由 <成員>` 施放時，開戰的也是該成員的這次施放，該技能成為該成員的開場指令、由該成員先出手，戰鬥仍記在你名下，你與其他同伴的指令到齊後才結算。傷害技能只能瞄準怪物。具狀態或接觸條件的法術需滿足條件方可施展；性愛技能亦屬可施放之列，隨遊玩解鎖後可經 `combat actions` 的分類檢視。 |
| [`lineage`](/game/command-reference?id=lineage) | 檢視指定成員（省略時為指揮者）的技能系譜圖：各圖的根、已持有／總節點數、前置關係與解鎖門檻、見頂與可解鎖節點。 |

網頁客戶端不需輸入指令也能施放：開啟 **隊伍 → 技能**，在左側成員列選擇施放者（自己或同伴），再選擇主動技能；右側詳情卡會列出目標、消耗、熟練度、系譜位置，以及「可於戰鬥外使用」或「僅能在戰鬥中使用」，擁有該元素精通時另列 **威力與消耗**。按 **施放** 後，隊伍視窗會關閉，由右下的行動面板替該成員接手選擇目標（範圍技能以 Space 勾選）、調整威力與最後確認；對同場魔物施放會另行確認 **開戰並施放**。按 Esc 可逐層返回，回到技能分頁時焦點停在原本的技能。戰鬥中 **施放** 與 **排入修煉** 皆停用，請改用指令卡的「技能」。文字 `cast` 的語法與判定完全不變。

## 成員資訊

| 指令 | 說明 |
| --- | --- |
| [`狀態`](/game/command-reference?id=狀態) | 檢視指定成員（省略時為指揮者）的真實數值構成、公會階級與功績、作用中的狀態，以及另列標明的偽裝顯示數值；成員不需在場。 |
| [`技能`](/game/command-reference?id=技能) | 檢視指定成員的主動與被動技能，含熟練度、見頂、修煉中、本次連線解鎖標記、前置與下一個解鎖，以及威力階梯；成員不需在場。 |

## 公會

| 指令 | 說明 |
| --- | --- |
| [`guild register`](/game/command-reference?id=guild-register) | 註冊為冒險者。 |
| [`guild list`](/game/command-reference?id=guild-list) | 查看任務板與每個委託的第一目標說明；任務板只列出目前能完成的委託。 |
| [`guild accept`](/game/command-reference?id=guild-accept) | 接取委託。 |
| [`guild log`](/game/command-reference?id=guild-log) | 查看任務記錄。 |
| [`guild show`](/game/command-reference?id=guild-show) | 查看任務詳情（含階級、評價理由與背景）。 |
| [`guild abandon`](/game/command-reference?id=guild-abandon) | 放棄任務。 |
| [`guild turnin`](/game/command-reference?id=guild-turnin) | 回報任務並領取報酬。 |
| [`guild merit`](/game/command-reference?id=guild-merit) | 查看階級與功績。 |
| [`guild request`](/game/command-reference?id=guild-request) | 委託公會規劃任務（護衛委託需完整契約，角色須來自已發布套件）。 |
| [`guild exam`](/game/command-reference?id=guild-exam) | 預約升等考核：考官在場時開始考核，不在時告知預定到場時間。 |

## 教會

| 指令 | 說明 |
| --- | --- |
| [`church join`](/game/command-reference?id=church-join) | 在主祭面前入教（入教／洗禮）。 |
| [`church pray`](/game/command-reference?id=church-pray) | 在教會聖所祈禱，花費時間累積恩寵（祈禱）。 |
| [`church offer`](/game/command-reference?id=church-offer) | 向 NPC 獻上性愛服務，依對方意願獲得恩寵與銅錢。 |
| [`church redeem`](/game/command-reference?id=church-redeem) | 以恩寵兌換教會敘階（敘階）。 |
| [`church merit`](/game/command-reference?id=church-merit) | 查閱自己的教會恩寵記錄（唯讀）。 |

## 知識圖鑑

| 指令 | 說明 |
| --- | --- |
| [`lore`](/game/command-reference?id=lore) | 檢視已發現的知識圖鑑。 |

## 信件

| 指令 | 說明 |
| --- | --- |
| [`信件`](/game/command-reference?id=信件) | 在銀羽驛站寄信與領信；已領取信件可隨身閱讀。別名 `letters`。 |

文字寄信每次輸入都會建立新信件；寄出後未收到回覆時，請勿自動重送。

瀏覽器的「信件」面板每次開啟只載入第一頁一次，沒有重新載入按鈕；需要重新整理，或清單載入失敗時，請關閉面板後重新開啟。關閉面板會一併捨棄尚未寄出的草稿。寄信與領信僅限銀羽驛站分站，已領取信件可在任何地方閱讀。

NPC 可選擇回信，送達不代表必定收到回覆。回信寄出後另需一個遊戲小時送達；信中邀請與任務宣稱只保留為陳述，不會接受任務、完成目標、轉移物品或建立正式約定。

## 經濟

| 指令 | 說明 |
| --- | --- |
| [`shop stock`](/game/command-reference?id=shop-stock) | 查看商店庫存（標題冠以商店名稱）。 |
| [`buy`](/game/command-reference?id=buy) | 購買物品（別名 `買`），可用 `= <成員>` 指定同行的隊伍成員收下物品；未指定成員時由目前操作的隊伍成員收下；費用由隊伍錢袋（指揮者的錢包）支付；附身中仍可購買。 |
| [`sell`](/game/command-reference?id=sell) | 販賣物品（別名 `賣`），可用 `= <成員>` 指定同行的隊伍成員出賣其未裝備的物品；未指定成員時賣出目前操作成員的物品；所得進入隊伍錢袋；附身中仍可販賣。 |
| [`inventory`](/game/command-reference?id=inventory) | 查看錢包、背包與角色數值構成（與角色面板同源）；附身時顯示隊伍錢袋，背包仍屬於目前操作的角色。 |
| [`使用`](/game/command-reference?id=使用) | 使用一件持有物品，可帶一個目標名稱，並可用 `= <成員>` 指定同行的隊伍成員（物品從該成員自己的背包消耗、自身效果綁定該成員，倒地的同伴會被拒絕）；戰鬥中只存入該成員的那筆指令（未指定時是你自己的），完整回合確認後才在結算時消耗道具與一個回合。 |
| [`裝備`](/game/command-reference?id=裝備) | 裝備或卸下裝備，物品可用登錄鍵或顯示名稱指定，並可用 `= <成員>` 指定同行的隊伍成員（倒地的同伴也可以）；免費動作，飾品上限 5 件。 |
| [`拿`](/game/command-reference?id=拿) | 撿起地上的物品，登錄物品會同步計入背包清單。 |
| [`丟`](/game/command-reference?id=丟) | 丟棄背包中的物品，登錄物品的背包清單記錄會同步移除。 |
| [`給`](/game/command-reference?id=給) | 將物品交給他人，登錄物品的背包清單記錄會同步移除；對象是隊伍成員時改由隊伍轉移規則處理（免費、不推進時間、不改變好感度，戰鬥中拒絕），其他對象維持原樣，把任務物品交給任務綁定的對象時交付目標會隨之推進。任務專屬的交付請用 [`交付`](/game/command-reference?id=交付)。 |
| [`交付`](/game/command-reference?id=交付) | 把任務物品交給任務指定的對象；對象不符或未持有足夠物品時，不會改變任何東西。 |
| [`取回`](/game/command-reference?id=取回) | 從同行的隊伍成員身上取回物品，放進指揮者的背包；免費、不推進時間、不改變好感度，戰鬥中拒絕。 |

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
