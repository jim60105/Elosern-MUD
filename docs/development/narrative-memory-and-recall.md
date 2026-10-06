# 敘事記憶與快速召回開發指南

## 總覽

`world/narrative` 子系統管理持久化的敘事事件、角色的記憶認知，以及經過校準的詞彙召回。

### 核心模組

1. **`world/narrative/events.py`**：
   - 管理持久化的 `NarrativeEvent` 紀錄，來源出處不可變，並以 `ProjectionProgress` 冪等追蹤投射進度。

2. **`world/narrative/memory.py`**：
   - 管理以擁有者為範圍的 `MemoryRecord`，以及只增不改的 `MemoryRevision` 歷史。
   - 強制執行知識範圍（`witnessed`、`told`、`inferred`、`public`）與擁有者的隱私邊界。
   - 紀錄發生有效變更時遞增 `OwnerMemoryGeneration`。

3. **`world/narrative/tokenizer.py`**：
   - 確定性的正體中文與英數分詞器（`tc_v1`）。
   - 擷取正規實體詞（例如 `尤漢娜`、`銀羽驛行`、`保護`、`遭遇`）。
   - 產生 CJK 單字與雙字詞項，並過濾正體中文停用詞。

4. **`world/narrative/ranker.py`**：
   - 純 Python 的 BM25 排序（`bm25_v1`，$k_1=1.5, b=0.75$）。
   - 以精確度為先的詞彙入選閾值（`MIN_LEXICAL_THRESHOLD = 2.0`）。
   - 要求多字詞彙有實質重疊，避免常見單字讓無關的經歷通過入選門檻。

5. **`world/narrative/recall.py`**：
   - `fast_recall(*, owner_id, query, requester_id=None, thread_id=None, limit=5, core_limit=3, working_limit=5, ...)`：
     - 步驟 1：權限過濾與明確範圍檢查（`get_owner_memories`、選配的 `thread_id` 關聯比對）。
     - 步驟 2：有界的固定記憶選取（核心與工作兩個層級），排序確定。
     - 步驟 3：對合格候選執行 BM25 詞彙召回。分數低於閾值者被淘汰；全數不合格時 `recalled` 為空 `[]`。
     - 步驟 4：以元資料加分（顯著性 salience、信心 confidence）重排詞彙候選，永遠不會讓未達詞彙門檻的紀錄重新入選。
     - 步驟 5：以擁有者記憶世代為索引的可替換分詞快取。
     - 透過 `world.observability` 發出 `narrative_fast_recall_executed`。

6. **`world/narrative/calibration_runner.py` 與 `world/narrative/calibration_corpus.py`**：
   - 離線的合成標註固定資料與評估執行器，量測 Recall@1、Recall@2、誤判率與延遲。
   - 已提交的報告位於 `world/narrative/calibration_report.json`。

7. **`world/narrative/context.py`**：
   - 以權限過濾後重現認知脈絡的組裝程序，渲染預算可執行，來源快照不可變。
   - 固定區塊順序：全域規則、世界摘要、能力契約、人物錨點、紀元摘要、輪次框架（召回項目與可執行動作 affordances）。
   - 預算設定檔預留完成輸出額度、未來的 Deep Recall 額度與估算安全邊際；選取與組裝共用同一份渲染表示（含標題），必要區塊超出預算時在生成前直接拒絕。
   - 不可變的 `NarrativeContextSnapshot` 模型（只增不改的管理者加上執行個體防護），追蹤來源 ID、讀取修訂版本、區塊雜湊、預算帳務、截斷決策與可重建的渲染載荷。
   - 輕量的 `NarrativeRequestDescriptor` 把提示詞訊息、驗證器與快照／追蹤識別碼綁在一起，拒絕脈絡與快照出處不相符的配對。
   - 每次新的組裝都重讀擁有者記憶世代，有效記憶的變更因此反映到新一代；重試則重讀權威的持久化快照，不會改寫它。

## 固定時長的書信送達（W2）

`world.narrative.correspondence.send_letter` 接受持久角色主鍵、不為空白且上限 8000 字元的內文，以及選配的穩定來源識別碼與回覆目標來源識別碼。預檢會在持久化之前拒絕未知或非角色的收件人。重複使用來源識別碼只有在寄件人、收件人、內文、回覆連結與來源快照都相同時才具冪等性。已受理的 `LetterSend` 列不可變；帶索引的 `LetterState` 列另行管理狀態轉換。

寄出當下固定住目前的權威 tick，送達期限設在恰好 `CLOCK_YAML["seconds_per_hour"]` 之後的 tick。確定性啟動程序在 `npc_schedules` 之後、`instance_reclamation` 之前登錄 `correspondence_delivery`。命令、戰鬥與跳時間的推進都會結算落在 `(start_tick, end_tick]` 內的確切期限，包含未與整點對齊的寄件。被拒絕的跳時間不會推進；結算從不假設請求的區間一定生效。

NPC 收件人轉為 `delivered`；玩家收件人轉為 `available`，沒有領取與閱讀的 tick。送達過程不查詢收件人、不修改特質、不推進任務、不呼叫模型、不呼叫圖像服務。移動與不在場的即時地點都影響不了已受理的送達。領取與閱讀走下文的玩家介面；選配的回信走各自的遠端通道。書信的記憶投射由 `world.narrative.correspondence_memory` 負責（見下文）。

每次轉換都在同一筆交易原子記錄一個私人 `NarrativeEvent`，帶穩定的 `correspondence:<send-source>:<status>` 識別碼與待處理的 `ProjectionProgress`。`CORRESPONDENCE_PROJECTOR_VERSION = 2` 把這些進度列保留給書信專屬的消費者；通用活記憶投射器的版本 1 啟動佇列永不消費它們。這些列在時鐘推進期間維持待處理；這批待處理的下游工作是已封存送達契約的一部分，由書信消費者排空。這些資料表共用時鐘交易。

宣告的介面契約沒有快取實體，一般 Django 列一律重新查詢、透過 queryset 更新，只以分離的凍結值回傳。沒有任何可變的快取列能存活於回滾之後。邊界日誌在持久提交後執行，內容只有識別碼、tick 與狀態，絕不含信件內文。

## 選配的 NPC 回信（W2）

送達時在同一筆時鐘交易內，為每封送給 NPC 的信建立一筆持久化的 `LetterReplyWork`。送達與啟動程序都不等待生成、不清掃待處理佇列。擁有者主動請求時呼叫一次 `server.correspondence_service.request_letter_reply(source_id)`；呼叫端可以注入記錄好的 `FakeLLMClient`。該服務在正式環境建構專用的 `correspondence` 設定檔客戶端。之後再次明確請求，就是透過既有護欄發起的新一輪嘗試，沒有自動重試政策，也不保證 NPC 會回覆。

`prepare_reply` 把完整的已送達來源與收件人擁有的 W1 召回寫進不可變的脈絡快照。32768 token 的脈絡預算扣除設定檔的完成輸出預算、召回預留額度與安全邊際後，輪次框架的目標與上限為 22000/24000 token，足以容納已受理的 8000 字元輸入。`correspondence` 層配置的模型因此必須支援 32k 脈絡；較小的視窗會讓該次嘗試降級回待處理狀態，絕不帶入截斷的輸入。未擷取或遭截斷的來信輸入不會產生回信。每次嘗試都擷取新的快照；被取代的完成版本、已變更的記憶世代或收件人錨點都會讓工作維持待處理。遠端玩家的私人特質與面對面脈絡不會進入提示詞。

專用的提示詞與 schema 接受不為空白的中文內文，意圖為 `none` 或非負的 `adjust_relation` 增量、上限 10；增量為 0 時等同 `none`，規則寫入器因此絕不被呼叫，也不會產生空的親和紀錄。信件敘述中提到的會面、線索與任務宣稱，在儲存的信件裡維持為陳述。任務、目標、百科、背包、實體動作、組隊邀請與預約的寫入器都不被呼叫。關係提案路由到 `world.rules.correspondence`，沿用既有親和寫入器共用的 `AI_DIALOGUE` 邊界與每日額度，且不要求雙方同處一地。被拒絕的效果會讓工作維持待處理，不會發送暗示效果已生效的台詞。

結算時序列化該筆工作與收件人，重新驗證目前的來源與快照，並原子提交關係變更、不可變的回覆目標／來源快照連結、回寄的信件與工作完成記錄。回寄期限設在本次寄件自身提交 tick 的一小時遊戲時間之後。重播回傳同一封回寄信件，不會再次生成或扣打關係額度。寄件結算失敗時，除了回滾資料庫寫入，也會還原 Evennia 的關係快取。失敗時絕不編造備援信件。

玩家命令語法與瀏覽器動作都沒有變更，命令文件因此維持原樣。邊界事件只帶 ID、計數與 tick，絕不含信件內文、私人召回或提示詞。

## 玩家書信介面（W2）

`world.narrative.player_correspondence` 是玩家生命週期的唯一寫入者。作者設定的 `PlaceDefinition.letter_service` 能力沿用既有帶唯一標籤的永久室內錨點；描述性的 `PlaceKind` 永不授予服務。兩個聚落各有一個無宿主（hostless）的銀羽驛站分部。任何分部都能領取該玩家身分名下全部可領取的信件，並保留未讀狀態。元資料每頁最多二十筆已領取或已讀列，外加一個不透明的數字型 next 游標；清單從不抓取內文、也不建立時鐘。

`read` 在交易內把關擁有者與領取條件，條件式地把 `collected` 改為 `read`，並一併提交首次閱讀的 tick、一筆私人 `correspondence:<source_id>:read` 事件、該事件的版本 2 進度列，以及擁有者的 told 記憶。事件參照不可變的原信，不複製內文。在任何地方重讀都不產生正典寫入，而該完成列代表重播不會新增認知。領取不建立內容知識，也不產生閱讀事件；通用的版本 1 投射器無法消費這個佇列。

文字指令 `信件`（`letters`）與四個白名單內的瀏覽器 `letters.*` 動作都走同一組 API。瀏覽器元資料與明確開啟的內文沿用既有帶相關 ID 的動作結果資料通道，沒有新的面板協定。至多 8000 個 Unicode 碼位以最多四段、每段 2000 碼位的分塊傳送，維持傳輸層既有的 2048 碼位葉節點上限。未知的載荷欄位（含偽造的擁有者欄位）一律 fail closed。草稿未變動時瀏覽器重試保留同一個寄件識別碼；伺服器端寄出維持原子且冪等。工作階段或角色被取代時丟棄本地私人資料，絕不自動重播寄件。工具群的信封開啟共用、焦點鎖定的抽屜；其中的格線信紙使用共用的墨色、紙色與黃銅設計記號，不嵌層疊卡片框。

每次文字指令呼叫都是一次新的寄件，不是帶識別碼的請求重播。內容相同的兩封主動信件必須仍然可行，因為按內文或姓名去重會誤殺正當的書信。文字客戶端在寄出後未收到確認時，不得自動重試結果不明的寄件。兩份玩家文件都寫明了這個區別。帶識別碼的文字重試協定屬於新的命令契約，超出這個邊界現行的文字慣例。

離線冒煙測試：透過受防護的 Evennia 測試入口執行 `world.narrative.tests.test_player_correspondence.PlayerCorrespondenceTests.test_real_text_and_browser_offline_smoke_and_log_privacy`。它以合成資料、不帶任何生成服務，驗收真實的文字寄件、已提交的時鐘送達、另一分部的瀏覽器領取、瀏覽器與文字兩通的閱讀，以及首次閱讀的日誌隱私。僅屬於增量的覆蓋 ID 由後續規格同步擁有者在同步之後取得。

## 書信認知投射（W2）

`world.narrative.correspondence_memory` 是持久信件轉換來源的版本 2 消費者。權威依據是收據，不是內容宣稱：一封信只建立 told 認知，不帶世界真相、任務目標、物品、預約或戰敗事實。NPC 在信件送達的那一刻取得它；玩家只在領取後的首次閱讀取得它。未送達的信與已領取但未讀的信完全沒有記憶，因此檢索、固定選取與提示詞脈絡都不可能取得它們。

每條記憶保留不可變的信件出處（信件來源識別碼、寄件人、寄出與結算 tick、回覆目標連結），加上存放信件內文的 `statement`、範圍 `told`、類別 `correspondence`，其宣稱信心低於親眼目睹的觀察。`summary` 維持為有長度上限的摘錄，因為渲染後的認知列會進入提示詞，而完整陳述留在擁有者的認知裡。層級是 `working`，有上限的固定選取因此能供給面對面對話的脈絡延續，不會把信件檔案庫複製進 `DialogueTurn` 台詞。

結算從四個邊界排空同一個持久佇列。伺服器啟動會復原中斷留下的每一筆待處理版本 2 來源（容忍開機的 `narrative_correspondence_projection_init`；需要重試的待處理來源維持待處理）。`prepare_reply` 在完成工作的提早返回之後、召回擷取之前，排空該封信的送達來源：一筆就緒的回信會看到已結算的送達認知，否則繼續等待；生成從不繞過送達的知識邊界。`build_dialogue_context` 在召回選取前排空，已送達的信因此在面對面輪次裡可用。玩家的首次閱讀在閱讀交易內部完成投射，因為那一刻是擁有者的知識邊界，其他任何事件都不會觸發它。

投射是冪等的：`(source_id, projector_version)` 進度列只結算一次，重播回傳原始紀錄，不複製記憶，兩個版本各自維護獨立的列。邊界事件只帶來源、擁有者、版本與計數的識別碼，即 `correspondence_memory_projected`、`correspondence_memory_projection_skipped`（沒有持久事件的待處理來源維持待處理並回報）與 `correspondence_memory_projection_failed`，絕不含信件文字。投射失敗的來源依設計保留待處理列（持久的工作絕不丟棄），在下一個排空邊界重試，每次嘗試都回報例外鏈，沒有放棄門檻。只有啟動復原入口會宣告已登錄的待處理掃描，熱線上的對話與回信排空因此保持安靜。

這個邊界僅屬於增量的覆蓋 ID，由後續的規格同步擁有者在增量規格進入 `openspec/specs/` 之後取得並標註；本次變更針對既有正典主 ID 標註其實質測試。

## 持久化的六次交流夢境會話（W3）

`world.narrative.dream_session` 負責一場協作夢境對話的持久記帳：六次交流的預算、唯一的待完成輪次，以及確定性的確認、草稿與醒來選項。它只儲存識別碼、計數與參考：一筆 `DreamSession` 列（會話與擁有者識別、`completed_exchanges`、`revision`、`state`、`outcome`、`pending_submission_id`、有上限的 `saved_input`、`draft_id`、`request_key`），加上只增不改的 `DreamExchange` 列（已送達回應的識別、交流編號、提交識別與 `response_ref`）。它絕不儲存生成的散文、絕不開啟傳輸，也不從 `world.ai` 匯入任何東西，因此所有操作在所有生成服務離線時都能運作。開啟夢境、呈現場景、伺服器計算的興奮軌跡與睡眠結算屬於其他能力的範圍；這個邊界只做計算與記錄。

一次交流等於一則玩家訊息加一則成功送達且通過驗證的回應。`begin_turn` 把玩家訊息的識別與其有上限的渲染文字記錄為唯一的待完成輪次，不消耗任何額度；`settle_exchange` 是唯一會遞增持久計數並追加 `DreamExchange` 的操作。計數上限為六，重新連線絕不會重置它（`open_session_for` 回傳同一筆持久列）；剩餘次數來自 `remaining_exchanges` 與 `progress`。第五次交流開始收束（`progress(...).converging`），第六次到達上限（`progress(...).at_cap`），`choices(...)` 回報 `can_input = False` 與確認、草稿、醒來的可用性；會話結束或到達上限後，`begin_turn` 拒絕自由文字。開啟文字、確認動作、傳輸失敗、驗證重試、放棄的輪次與重複提交都不消耗交流。渲染輸入有自己獨立的硬性上限（`MAX_RENDERED_INPUT_CHARS`，由這個邊界擁有的進入口上限）；模型端的渲染回應上限屬於呈現能力。空白或過大的輸入在任何狀態變更之前就被拒絕，一則超大訊息無法繞過會話預算。

記帳持久且冪等。重複的 `delivery_id`（重啟重播）與重複的 `(session, submission_id)`（重複提交，以首次送達的回應為準）都讓 `settle_exchange` 回傳既有列，兩者都不致消耗第二次交流。`delivery_id`、`(session, exchange_number)` 與 `(session, submission_id)` 的唯一性約束是持久防線，`select_for_update` 保留給支援它的後端、SQLite 會忽略它；並發競賽的落敗方解析到獲勝的那一列。交流插入與會話計數更新在同一筆交易提交，持久計數因此絕不會在缺乏持久證據下前進。傳輸失敗、取消或驗證重試時，`abandon_turn` 釋放唯一的待完成槽位，不消耗任何額度，並讓 `saved_input` 可供下次進入時恢復；終端選項與醒來會清除槽位。

兩個呼叫端的契約由此而來。成功送達沿用既有的呈現驗收邊界：通過驗證的回應已提交到可恢復的玩家回應紀錄，並以該識別派送；`settle_exchange` 只在該結果定案之後才被呼叫。在 `abandon_turn` 之後才到來的延遲送達會被拒絕而不會計數，因此預算可能少算一筆真的遺失的結算，絕不會多算。會話的草稿 handle 依會話確定，`preserve_draft` 與 `confirm_session(direction=...)` 因此假設每個擁有者只有一個寫入者，與 `world.narrative.authoring` 文件說明的呼叫端提供 `draft_id` 契約相同。

確認、草稿與醒來都屬確定性操作、無需生成。`preserve_draft` 儲存或更新會話確定的私人 `AuthoringDraft` handle（`dream:<session_id>`），不排定任何工作，不會建立 `CreativeRequest`；`confirm_session` 把驗證與單一提交委派給 `world.narrative.authoring.confirm_draft`，接受一次帶方向的呼叫以一步完成儲存並確認，或確認已儲存的草稿，沒有可確認內容時拋出 `DreamSessionNotDraftedError`，對已確認的會話重複確認會回傳同一筆持久請求。無效的方向會在那裡帶著具體原因拋錯，草稿維持未確認、會話維持開啟，不改變任何持久狀態。`awaken_session` 結束會話，不呼叫模型、不寫入睡眠，且具冪等性（已結束的會話屬純粹的 no-op，沒有事件也沒有修訂變更），重新連線或反覆醒來絕不會重複結算。以擁有者為範圍的讀取（`get_session`、`open_session_for`、`list_open_sessions`、`list_exchanges`）遇到他人或不存在的會話時拋出 `DreamSessionAccessError`。

邊界事件（`dream_session_opened`、`dream_session_submission_accepted`、`dream_session_exchange_completed`、`dream_session_turn_abandoned`、`dream_session_draft_preserved`、`dream_session_confirmed`、`dream_session_awakened`，加上 warn 等級的拒絕事件 `dream_session_input_rejected`、`dream_session_closed`、`dream_session_turn_conflict`、`dream_session_exchange_conflict`、`dream_session_delivery_duplicate`、`dream_session_not_drafted` 與約束競賽事件）只帶識別碼、計數、tick 與穩定的原因程式碼，絕不含玩家訊息或方向摘要。這個邊界僅屬於增量的覆蓋 ID，由後續的規格同步擁有者在增量規格進入 `openspec/specs/` 之後取得並標註；本次變更針對既有正典主 ID 標註其實質測試。

## 明確的夢境呈現與伺服器持有的興奮軌跡（W3）

`world.narrative.dream_track` 負責一場協作夢境對話確定性、僅存在於會話內的愉悅／興奮／高潮軌跡，以及無需生成的結尾（設計文件第 6.4 節）。它是建立在 `world.narrative.dream_session` 所擁有、持久交流計數之上的純唯讀模型，不建立活的 `SexualState` 處理器。它只重用正典的 `AROUSAL_LEVELS`／`CLIMAX_PHASE_LEVELS` 詞彙與唯讀的 `PLEASURE_CONFIG` 區間表，絕不寫入持久特質、愉悅量條、敏感度、貞操／經驗、生涯計數器、`climax_today`、buff、技能、百科或關係狀態，也不實例化任何處理器。已提交的睡眠結算仍是身體恢復的唯一路徑。

`TRACK_VERSION` 1 提交起始愉悅值（`INITIAL_PLEASURE` 0）與每次交流一個設定增量（`EXCHANGE_DELTAS`），校準結果讓六次完成的交流依序走過五個正典區間，並在收束時抵達 `進行中` 高潮階段；`progression_report()` 是已提交的逐交流證據。`track_state(n)` 渲染 `n` 次完成交流後的狀態，`prospective_state(n)` 則給出下一次交流將提交的階段，驗證重試、重複送達、傳輸失敗或放棄輪次因此重用完全相同的階段。生成的回應從不推進軌跡，任何失敗也不會讓它重複遞增。`exchange_mode(n)` 把第五次標為 `convergence`、第六次標為 `summary`。`render_ending(n)` 無需生成，抵達高潮時先渲染正典的高潮後階段（`餘韻`）再淡出，提早離開則直接淡出、不強制高潮；醒來從不依賴模型呼叫。

`world.ai.dream` 負責 `dream` 生成層：一次通過驗證的 JSON 交流（`scene` 露骨場景散文、`dialogue` 對方台詞、`phase`）。`phase_fidelity` 逐呼叫驗證器拒絕伺服器提供階段以外的任何值；該層驗證器接受露骨的性內容，同時攔截系統與元資料洩漏、具名神祇身分、神之秘法揭露與狀態變更宣稱。提示詞渲染帶伺服器階段與交流元資料的 `dream.system`，序列化內容只有玩家訊息、已確認的創作偏好，以及呼叫端提供、已過濾劇透的冒險摘要；StoryDirector 歷史、隱藏答案與其他擁有者的資料都不進入請求。該層登錄自己的 hook、schema 與設定檔槽位（`server/conf/at_server_startstop.py::register_dream_layer`），與 `scenario_director` 之間不共用任何 hook 或設定檔，並在設定檔停用、傳輸失敗或重試預算耗盡時降級為 `None`。`dream_exchange_generated` 邊界事件只帶層名、已完成計數、模式與伺服器階段，絕不含場景散文、對話或玩家訊息。

## 持久化的面對面對話（W1）

`world.narrative.dialogue` 取代會破壞性覆蓋的 NPC Attribute 歷史。`submit_turn` 分配一個進入口識別並保留玩家的原始台詞。`run_npc_exchange` 在結果中帶著該識別與不可變的快照 ID，絕不記錄未送達的 NPC 回應。交談與兩個邀請送達呼叫端都透過 `settle_response` 記錄實際顯示的回應，其 `(submission_id, kind)` 唯一鍵防止重複結算。作者撰寫的離線問候語是已送達的輪次；沉默與過期人設的回應則不是。既有的同處一地／作息延遲拒絕仍會顯示通過驗證的台詞、拒絕其意圖，這段已顯示的台詞因此留在檔案庫中。

`pair_view` 依持久化的 NPC／玩家識別為索引，只讀取設定的尾部（最多 12 輪）。修剪只影響渲染。被略過的輪次計數會伴隨提示詞與快照；原始紀錄在 `DialogueTurn` 中始終可恢復。更改人設會改變之後的渲染，不改寫歷史台詞。沒有相容性的歷史儲存，也不遷移舊的 Attribute 資料。

每次交流先做擁有者權限內的 Fast Recall，再交給既有的脈絡組裝器。核心與工作兩層的選取維持為固定脈絡。保護事件投射到既有的 `archive` 層級：持久的事件式經驗被排除在固定工作選取之外，仍可進入相關的詞彙召回。無關的問題不會把該段經歷逼進認知。W1 系統範本留在提示詞庫；認知內容加在既有使用者 JSON 的位置。快照擷取最終系統與使用者訊息的精確內容，來源只限渲染後仍留在召回區塊的那幾筆。一般日誌只有 ID 與計數，絕不含台詞、私人人設或提示詞文字。

## 作者控制的尤漢娜保護與回頭探訪路線

全新的 NPC 匯入卡是 `world/imports/examples/yohanna_cooper.json`。它撰寫了尤漢娜‧庫珀世襲的桶匠家族與公會工匠人脈，不依賴臨時的交接劇本。精簡卡匯入器是人設、年齡與姓名驗證的邊界；`NPC_SOURCE_INVENTORY` 記錄它既有的 `import_example` 擁有權。

在作者控制的本地世界中，把一位未綁定的玩家放到公會大道上可抵達的房間，且當下不在戰鬥。從既有的管理員 Python 縫隙呼叫 `world.rules.protection_demo.prepare_protection_demo(player)`。例如在 `self` 是玩家的管理員 `@py` 環境中：

```python
from world.rules.protection_demo import prepare_protection_demo
npc, enemy = prepare_protection_demo(self)
```

這會把尤漢娜匯入到玩家身旁，透過真正的隊伍擁有者綁定她，並引出登錄表中最低威脅層級的敵人。它不宣告勝利。使用既有的戰鬥攻擊／動作選單，在尤漢娜存活的前提下擊敗那隻生物。真正的戰鬥結算提交保護事實，一般的投射消費者據此建立她的親眼目睹經歷。用既有的離開隊伍動作遣散她，讓她留在相遇地點。接著用好幾天的一般待機命令，回到同一個可抵達的房間，談起之前的保護事件。無關的主題不會召回那段經歷；兩人的原始對話內容當然仍可能被提及。

沒有引入新的玩家命令、別名、語法或可用性脈絡。永久驗收測試使用合成卡片、固定戰鬥擲骰加上 `FakeLLMClient`；另外登錄的作者資料契約檢查出貨的卡片與設定。受控的記錄／離線冒煙測試可以透過受防護的 Evennia 測試入口點，執行 `DurableDialogueTests.test_real_protection_commit_multi_day_revisit_and_permissioned_recall` 與 `test_offline_delivered_greeting_is_durable_but_silence_is_not` 這兩個焦點標籤。自動化檢查不得啟用線上模型或圖像服務，也不得對線上措詞下斷言。僅屬於增量的新需求標註由後續的規格同步擁有者在取得其正典主 ID 之後補上；本次變更針對既有主 ID 標註實質測試。

## 明確的對話紀元與穩定前綴

DialogueEpoch 是只增不改的配對邊界，與目前目標會話分開。DialogueFrame 保留正典 JSON 位元組、tick 與擷取當下的記憶來源修訂版本。位置、好感度、召回的認知與玩家脈絡屬於目前框架。重播的框架保留原始位元組，目前的權威標記取代它們的狀態，不改寫歷史。全域規則與世界摘要排在提示詞庫的能力／人物錨點之前。`npc_dialogue.system` 的四個預留位置持續支援，`location` 傳入 `""`；NPC 人設維持在 system 側，玩家的公開人設維持在 user 側。渲染錨點、人設或渲染版本的變更會建立新紀元。歷史好感度數值仍受防洩漏驗證器保護。

確定性擁有者暴露 `start_epoch(npc, player)` 處理自然邊界、`compact_epoch(npc, player, client)` 處理壓縮。正式環境注入 `OpenAICompatClient(get_profile("dialogue_summary"))`，測試則注入記錄好的 FakeLLMClient。摘要能力使用自己的 schema 與護欄 hook，摘要對象是有邊界的原始對話，絕不是狀態框架。已受理的生成保留原始輪次的雜湊與修訂版本及其不可變快照。後續摘要可以引用前一次摘要的生成版本。原始輪次絕不移除。無效、離線與過期的完成不會觸發後繼者。啟動中的紀元透過有邊界的尾部視圖維持可用。NPC 列鎖定與配對／序列唯一性讓邊界序列化。

`dialogue_summary` 設定檔沿用既有的端點與設定檔控制（包含自動產生的 `LLM_DIALOGUE_SUMMARY_*` 環境變數名稱）。業者的快取控制屬選配，經過驗證的快取 token 數量僅供元資料參考。[渲染校準報告](dialogue-epoch-calibration.md)記錄各設定檔的預留額度、來源與輸出量測，以及摘要的硬性上限。玩家命令介面沒有變更，兩份命令參考因此維持原樣。新的 dialogue-epochs 主需求 ID 由後續的同步／封存擁有者取得並標註，進行中的增量需求不屬於正典 ID。

## 故事線：生命週期與真實連結（W3）

`world.narrative.threads` 負責確定性的 `StoryThread` 列：不可變的 `origin`、`participants`、`visible_to`（擁有者的 ACL）、事實性的 `factual_summary`、`unresolved_questions`、`proposed_plans`、由玩法建立的 `commitments`、`memory_references`、`development_ticks`、生命週期 `state`，以及單調遞增的 `revision`。`thread_id` 與 `origin` 不可變，每次有效變更都追加一筆只增不改的 `StoryThreadRevision`，持久列則拒絕 queryset 層級的修改、批次更新與刪除。

事實與計畫分開存放。`establish_commitment` 是唯一會追加 `commitments` 的路徑，且要求一筆已存在、非陳述管道的持久 `NarrativeEvent`：宣稱（`claim_receipt`）、書信（`correspondence_delivery`／`correspondence_read`）與私人創作都會被拒絕，信件中表達的意願因此以 `relation="statement"` 連結，絕不會變成承諾。對尚不存在的玩法承諾事件型別設定白名單會淪為只有一項的佔空檢查，所以把關條件改為開發文件記錄的負向陳述管道集合，未來帶有陳述性質的事件型別必須加入該集合。

承諾的重播不算有效變更：對已連結的事件重複提交相同的承諾文字會直接返回、不推進修訂版本，後續快照因此不會被無謂地作廢。

生命週期有明確的狀態規則。`transition_thread` 只接受四個狀態，並拒絕從 `resolved`／`abandoned` 移出的轉換；`mark_thread_dormant` 與 `apply_inactivity` 只能把進行中的故事線轉入休眠，判斷依據是建立時刻、`development_ticks` 與連結 tick 之中最新的一個，單靠不活躍永遠不會造成放棄。放棄與結案都是要陳述原因的明確操作。`note_thread_quest_completion` 要求已存在的任務連結，記錄 `relation="quest_completion"`，維持故事線狀態不動：完成的任務絕不結算其所屬故事線。任務只以持久識別連結（`link_quest_to_thread`），任務生命週期仍由 `world/quests` 負責，敘事端既不複製它也不讀取任務登錄表，任務參考依原樣儲存（不檢查存在性），其連結出處記錄 `identity_only`。

每次有效變更都在與實體更新相同的交易內，追加一筆只增不改的 `StoryThreadRevision` 列。`(thread, revision)` 唯一列是並發防線：不支援列鎖定的後端會讓落敗的寫入者以型別化的 `NarrativeThreadError` 明確失敗，不會無聲遺失更新，外層交易同時回滾。

連結都指向真實存在的列。`StoryThreadLink` 列以 `(thread, source_kind, source_ref, relation)` 為鍵，並在儲存連結前驗證被引用的 `NarrativeEvent`、`LetterSend`、`DialogueTurn`（`submission_id:kind`）或 `MemoryRecord`（`mem:<pk>`）列確實存在；關係依來源型別設有白名單。來源參考依原樣儲存、區分大小寫比對，連結屬持久資料：活得比記憶的取代更久，召回則照樣排除已被取代的認知，除非明確要求包含。`link_memory_to_thread` 也會把故事線識別寫進該記憶最新修訂版本的 relations，既有 `fast_recall` 的故事線範圍正是以此過濾。以這種方式標記記憶會追加一筆記憶修訂、進而推進擁有者記憶世代：這是刻意保守地作廢該擁有者之後的每一筆快照，而正式環境沒有任何路徑會每輪都連結。

故事線修訂版本是脈絡讀取的識別。`assemble_narrative_context` 接受明確的 `thread_id`，讀取該範圍以及每筆經驗證記憶的 `relations['thread_id']` 的目前修訂版本，把結果記錄在每個 `SourceReference` 與 `AssembledContext.thread_revisions`，`persist_context_snapshot` 再把這張對照表存進不可變快照；`build_request_descriptor` 以它做出處比對。新的世代看到新的修訂版本，歷史擷取與重試則保留各自擷取到的版本。分詞快取刻意*不*以故事線修訂版本為索引：分詞只取決於不可變的紀錄內容，而任何連結變更都已推進快取索引所依據的擁有者記憶世代。

明確的故事線召回在排序前把關。`fast_recall(..., thread_id=...)` 解析故事線並要求擁有者在 `visible_to` 名單內；未知或無權存取的故事線不會產生任何合格視圖，並發出 warn 事件 `narrative_thread_recall_denied`，私人的故事線與來源內容因此進不了召回。邊界事件（`narrative_thread_created`、`narrative_thread_linked`、`narrative_thread_revised`、`narrative_thread_recall_denied`）只帶識別碼、計數、tick 與修訂版本，絕不含摘要、承諾或信件文字。這個邊界僅屬於增量的覆蓋 ID，由後續的規格同步擁有者在增量規格進入 `openspec/specs/` 之後取得並標註；本次變更針對既有正典主 ID 標註其實質測試。

## 私人的夢境創作紀錄（W3）

`world.narrative.authoring` 負責創作邊界。`AuthoringDraft` 是一場協商方向的私人紀錄：不可變的 `draft_id`、`owner_id` 與 `created_tick`，想要的 `direction`、持久的 `sources`、單調遞增的 `revision`，以及 `confirmed_revision`。`CreativeRequest` 是不可變、帶版本的請求，只由確認動作建立。兩者都是創作資料，從來不是世界內知識：不給線索、物品、任務進度、持續的數值變更、技能精進、buff 或百科解鎖；模組不建立 `NarrativeEvent`、`ProjectionProgress` 或 `MemoryRecord`，私人討論依設計不存在於認知與召回之中。模組不從 `world.ai` 匯入任何東西、不開啟傳輸；確認具確定性，在所有生成服務離線時都能運作。

確認機制明確且帶版本。`save_draft` 建立草稿，或更新其內容並推進 `revision`，內容絕不會被無聲丟棄（內容相同的儲存是 no-op）。`draft.confirmed_revision == draft.revision` 代表目前版本已確認，編輯已確認的草稿會讓新版本重新變成未確認，一律需要新的確認。`confirm_draft` 驗證目前版本，然後建立一筆 `submission_key` 為 `"{draft_id}:v{version}"` 的 `CreativeRequest`。對同一版本重複確認（包含重新連線之後）回傳同一筆列、不產生第二次提交；`submission_key` 與 `(draft, version)` 的唯一性約束才是持久的提交一次保證，列鎖不是（`select_for_update` 保留給支援它的後端，SQLite 忽略它）。先前確認的版本維持權威且不可變，直到更新版本被確認為止；未確認的編輯不會撤回它。草稿本身不排定任何工作。

驗證具備確定性、原因具體。`validate_direction` 只讀取持久列，回傳正規化的方向，或帶有面對玩家訊息的具名原因程式碼：被引用的 `thread_id` 必須存在、為請求的擁有者所有（`thread_accessible`），且不處於終止狀態；已提交歷史的目標必須存在，存在則以 `committed_history_rewrite` 拒絕（個性與結果的改寫各有自己的程式碼）；任何請求的 `effects` 都是 `unauthorized_effects`；形狀、邊界與未知鍵則是 `malformed_direction`／`malformed_participants`。拒絕不改變任何持久狀態，`DirectionValidationError` 帶著原因，草稿保留已儲存的方向，重跑驗證會重現同一個原因，不必讀取可能過期的儲存狀態。核准的是方向，不是結果：與過往經驗無關的 `new_story` 方向屬有效，只須在明確確認後才取得資格。

存取以擁有者為範圍。`get_draft`／`get_request` 遇到他人的或遺失的紀錄時拋出 `AuthoringAccessError`，`list_drafts`／`list_requests` 只回傳擁有者自己的列。`collaborator_creative_brief` 是提供給協作者的、已過濾劇透的唯讀模型：只有最新確認版本的摘要與偏好欄位，沒有來源參考、驗證內部、其他擁有者的資料，或 StoryDirector 的隱藏答案（這個紀錄模型本來就沒有）。確定的新近鍵（先 `submitted_tick`，再持久的單調列 id）讓 `latest_confirmed_request` 把同 tick 的提交解析到較後的那一筆，呼叫端提供的 `draft_id` 無法左右結果。

邊界事件（`narrative_authoring_draft_saved`、`narrative_authoring_draft_edited`、`narrative_authoring_validation_rejected`、`narrative_authoring_request_submitted`）只帶識別碼、計數、tick 與原因程式碼，絕不含方向摘要、主題或原因訊息。這個邊界僅屬於增量的覆蓋 ID，由後續的規格同步擁有者在增量規格進入 `openspec/specs/` 之後取得並標註；本次變更針對既有正典主 ID 標註其實質測試。

## 確定性的敘事注意力（W3）

`world.narrative.attention` 負責確定性的過濾與排序邊界，縮窄後續 StoryDirector 可能追尋的方向。它不產生文字、不呼叫模型、不持久化任何橋段：`rank_attention` 是在純不可變的 `AttentionCandidate`／`AttentionContext` 值之上執行的純函式，模組唯讀，一次執行絕不修改、刪除或隱藏未被選中的故事狀態。輸出是有上限的 `AttentionDecision`：受焦點數量限制的 `selected` 集合、完整的 `ranked` 順序、附原因的 `excluded` 候選、不可變的識別加修訂版本 `sources`、輸入與設定的指紋 `snapshot_hash`（與順序無關），以及 `reason_counts` 計數。

`build_attention_candidates(owner=...)` 是唯讀的持久擷取層。每個進行中的 `StoryThread` 都成為一個候選，標上 `knowledge`（擁有者在 `visible_to` 中、是參與者，或擁有已連結的記憶／事件／對話／書信經歷）與 `invested`（擁有者是參與者，或擁有這類已連結經歷）；只有 ACL 權限的故事線屬已知但尚未投入。每個有效的 `CreativeRequest` 版本都成為 `confirmed` 請求候選，只有權威的 `latest_confirmed_request` 標上 `authoritative`；較早的版本以 `superseded_request` 排除項留在結果中，決策因此可被觀察。故事線的 `unresolved_stakes` 計算未解問題加上玩法承諾的數量，`repetition` 計算超出建立時刻的發展次數，`last_activity_tick` 是最新的發展、連結或建立時刻（請求候選使用 `submitted_tick`）。

資格檢查在任何計分之前執行。知識（`unknown_to_owner`）、投入來源或已確認請求（`not_invested`）、能力可行性（`not_executable`，只有 `dialogue`、`letter` 與 `quest` 有確定性擁有者）、地點可達性（`location_unreachable`，`required_location` 是最新連結事件的地點）、參與 NPC 的 `schedule_state` 以 `interaction_reason` 阻擋互動（`schedule_blocked`），以及已被取代的請求版本，全部先被淘汰，高顯著性但不合格的候選永遠壓不過合格候選。因此無關的新故事只有作為明確確認的請求才合格，絕不會作為自動歷史入選。

計分把具名成分正規化：未解決的賭注、投入度、關係（`relations.affinity_for`）、期限、地點相關性、重複度與冷卻，各自夾在 `0..1`，再以校準過的 `AttentionWeights` 組合；重複度與冷卻走減分。投入度只由可觀察的擁有者行為構成：主動發起的對話、持續的書信往來、明確的線索提問，與投入的玩法參與。被動接收（領取與閱讀信件，以及其寫入的私人 `correspondence_read` 事件）計入 `passive_receipts`，貢獻為零。投入度以對象為範圍：查詢範圍由候選的其他參與者圈定，沒有其他對象的候選直接歸零，不沿用擁有者的全域活動。並列時以 `candidate_id` 決勝，相同的輸入與設定在離線環境永遠產生相同的順序與原因資料。權重、飽和值、冷卻與焦點上限都是校準決定，記錄在 `world/narrative/attention_calibration.py` 與已提交的 `world/narrative/attention_calibration_report.json`（以 `python -m world.narrative.attention_calibration` 重新產生）。報告固定了一個刻意的行為：對剛發展過的故事線，冷卻加重複度可以壓過較高的賭注，注意力因此不會重複它。

邊界事件（`narrative_attention_ranked`，以及讀取上限被觸及時 warn 等級的 `narrative_attention_candidates_truncated`／`narrative_attention_engagement_truncated`）只帶擁有者 id、設定版本、計數、tick 與快照雜湊，絕不含玩家散文、故事線摘要或方向文字。這個邊界僅屬於增量的覆蓋 ID，由後續的規格同步擁有者在增量規格進入 `openspec/specs/` 之後取得並標註；本次變更針對既有正典主 ID 標註其實質測試。

## 確定性的故事主導節拍結算（W3）

`world.narrative.director` 是故事主導邊界的確定性那一半；`world/ai/story_director/` 供給生成的那一半，僅供提案。一個決策恰好從一個有邊界的來源出發，來源是既有投入故事線上合格的注意力選取，或明確確認的 `CreativeRequest` 版本（`new_story` 或 `thread_direction`）。自動候選永遠無法發起無關的新故事，那需要明確確認。擁有者、故事線可見性與非終結狀態在解析時與套用前都會各重新驗證一次。

`prepare_decision` 透過 `assemble_narrative_context` 擷取權限內脈絡（能力 `story_director`、自有的提示詞版本與輸出 schema），並持久化不可變的快照；生成針對擷取到的訊息執行，之後的讀取改變不了已提案的內容。有邊界的框架只帶擁有者許可的故事線事實、來源識別與修訂版本，以及允許的種類。

`settle_decision` 每個決策**最多排定一個**節拍，也可以完全不排。路由確定且集中，一種種類對應一種效果（`follow_up`／`clue`／`invitation` → `narrative_statement`、`letter` → `letter_send`、`quest_seed` → `quest_seed`），只有已登錄的效果會被具體化。`quest_seed` 使用節拍範圍的 ScenarioDirector 生成與既有的任務編譯／登錄擁有者；不可用或不合身的提案產生 `no_content`，絕不產生模板填充物。連結的藍圖、定義與快照識別持久保存在只增不改的節拍載荷裡。敘事端只寫入自己的資料（一筆敘事事件加一筆故事線發展連結，或一次 `send_letter`）；`relation_delta` 提案路由給規則擁有者（`apply_letter_relationship`），敘事端絕不代寫。

決策識別就是擷取到的來源*修訂版本*（`decision_id_for`），重啟重播同一個識別會回傳持久的決策與其單一節拍，不產生第二次模型呼叫；之後對同一條故事線再跑一次注意力會擷取到更高的修訂版本，屬於真正的新決策。每個決策恰好記錄一個結果，`scheduled`、`no_content`、`unsupported_effect`、`unauthorized_write`、`unsupported_target`、`invalid_proposal`、`stale`、`thread_unavailable` 或 `conflict`；`(owner, source kind, source ref, source revision)` 與 `(thread, arrangement_revision)` 兩個唯一性約束是抵禦重複來源與同一故事線修訂版本上衝突安排的持久防線。拒絕不會動到故事線，也不會動到任何無權的擁有者。

邊界事件（`story_director_decision_prepared`、`story_director_beat_scheduled`、`story_director_decision_reused`，以及 warn 等級的 `story_director_decision_rejected`／`story_director_decision_stale`／`story_director_decision_conflict`）只帶識別碼、修訂版本、計數與原因程式碼，絕不含提案摘要或任何故事散文。

## 與睡眠連動的夢境呈現介面（W3）

`commands.skip.CmdSleep` 接受 `sleep [dream]`；瀏覽器的 `explore.wait` 在一般睡眠之外，也接受精確的選擇加入載荷 `{"sleep": true, "dream": true}`。兩個介面卡都保留既有的安全性、時長、恢復與提名路徑，捕捉各自單次成功結算前後實際的時鐘 tick，接著呼叫 `server.dream_service.enter_after_sleep`。被受理的零秒睡眠有效，拒絕絕不會關聯會話。目前的時鐘是全有或全無，中斷結果的測試注入一筆較短的已提交時鐘結果，不另發明中斷引擎。

`world.narrative.dream_surface` 擁有持久化的角色 Attribute `dream_surface`，內容包含已關聯的會話 id、實際睡眠 tick、請求時長、事件種類、最新通過驗證的場景與對話，以及玩家的方向。已關聯的開放會話優先於最新開放會話查詢；之後明確的睡眠會在延續該場討論的同時記錄一筆新結果。重新連線只讀取這份紀錄與以擁有者為範圍的持久生命週期。讀取模型與任何離開操作都不推進時間或身體特質。`resume_saved_session` 重新開啟明確再次進入、尚未確認的討論，不重置其交流計數；已確認的會話維持定案。醒來會在結束前把未完成的方向保存為草稿。

`server.dream_service.act` 是組合根。`say` 只帶著已確認的創作偏好呼叫既有的受防護 `dream` 協作者，不帶隱藏的主導脈絡。回應送達時仍必須與會話、擁有者、目前控制權、開放狀態與待處理提交相符。修訂版本相等只對玩家請求設閘門，不約束非同步回應，生成期間儲存草稿可能合法地改變修訂版本。已放棄或已結束會話的延遲回應會被丟棄，不計入交流。只有已送達、通過驗證的場景加對話才會結算一次交流。呈現內容包含伺服器持有的夢境軌跡，不寫入活的 `SexualState`。確認、草稿與醒來沿用既有的創作與生命週期 API；確認狀態由 `draft_is_confirmed` 推得。方向支援既有的 `new_story` 與 `thread_direction` 紀錄，外加主題、氣氛、參與者、著重與排除欄位。擁有者可見、非終結狀態的故事線選項由伺服器撰寫（最多 32 個），確認時會重新驗證已變更的故事線狀態。無效的方向維持未確認的草稿，並回傳確定性的具體原因訊息。文字端接受方向的 JSON；瀏覽器傳送同一個物件，介面層有 8192 位元組的上限。後續聊天會保留明確儲存過的結構化草稿；單純確認絕不會無聲地把故事線方向變成新故事的聊天摘要。瀏覽器在同一場會話內回填已變更的草稿欄位，不清除未傳送的聊天，已結束的面板則完全跳過故事線選項查詢。結尾使用 `dream_track.render_ending`，絕不進行第二次模型呼叫。

`dream` 的 OOB 面板有嚴格鏡像的瀏覽器 schema（v2 起狀態多一個由伺服器解析的 `scene_art`）。`dream.say` 以兩個有邊界的 `message_parts` 傳送最多 4000 個 Unicode 碼位，維持全域每字串 2048 碼位的信封上限。生成會立即歸還瀏覽器的動作鎖；獨立的完成事件另行重新整理面板，呼叫待處理期間仍能離線派送草稿、確認與醒來。夢境舞台中的 Escape 走同樣帶修訂版本閘門的動作喚醒。文字端的 `dream` 指令暴露同樣的生命週期選項，但只呈現開場、場景、對話與剩餘次數，沒有舞台美術，也不顯示興奮階段。

焦點合成證據位於 `world.narrative.tests.test_dream_surface`，包含真實受理的零秒睡眠 → 記錄好的 FakeLLMClient 交流 → 草稿 → 確認 → 離線醒來的冒煙測試。僅屬於增量的新追溯 ID 仍由封存同步擁有者取得；既有主 ID 標註對應的睡眠、生命週期與呈現測試。

前端互動故事板是 `World / DreamPanel / Storyboard`。在倉庫根目錄執行 `pnpm run serve-storybook`，或以 `pnpm run build-storybook` 建置離線展示，再透過 HTTP 提供 `.storybook-out`。它掛載真實的獨立 `DreamPanel` 舞台。其上標示清楚的僅故事發布控制，能驅動已受理回應、拒絕／模型失敗、第六次交流上限、重新連線與離開等框架；不需要 Evennia 或模型服務就能檢視已送出的動作與確切載荷。固定資料控制與正式環境動作都使用共用的核心 `ui-btn` 樣式，只有方向確認帶有主要強調。依照使用者提供的核心面板備註，美術填滿整個舞台，不框在視窗裡。左下角的對話器具沒有完整邊框、圓角面板或陰影，羽化的共用墨色、一枚黃銅菱形、冠飾與脊線都讓成年女神透過開放的邊緣可見。表格化的計數、伺服器撰寫的場景與對話排在唯一的對話輸入之前。共用的焦點鎖包含原生揭開控制項、排除其收合內容；Escape 喚醒，卸載時還原焦點。預設視圖呈現一個對話輸入，接著明確預覽確認將儲存的方向。方向編輯與淺白語言、一行一項的偏好欄位採逐步揭開；瀏覽器絕不要求 JSON，也不把故事線 ID 顯示成選項標籤。擁有者可見的故事線選項帶有邊界的 `{id, label}` 紀錄，標籤只取自有權存取的故事線事實摘要。吸附式的動作頁尾寫明確認的離開後果，並讓醒來保持可見。方向為空時按下確認，會開啟並聚焦方向編輯器，不請求模型。僅故事的發布工具預設收合。舞台美術來自外部官方美術目錄：`<ART_OFFICIAL_ROOT>/npc/dream_goddess/dream-throne.webp` 於啟動時被索引，由伺服器以同源 URL 隨面板狀態下發；目錄缺失、身分未通過索引或載入失敗時，面板退回平鋪的墨色舞台，不顯示破圖。它是靜態的呈現美術，不是角色肖像，也不是權威的世界狀態，且絕不進版控、絕不打包進前端；正式環境與永久測試都不提交它。`Pending`、`Failed` 與 `AtCap` 提供隔離的邊界框架。故事板全程把已提交的睡眠固定資料保持在 tick 100，絕不模擬權威的身體恢復或線上伺服器。
