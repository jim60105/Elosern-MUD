# 任務產生的三種模式

遊戲裡有三條路徑會生出任務，它們共用同一套導演能力，服務的需求卻不同。公會櫃檯的委託回應玩家當下的要求，故事橋段的任務種子回應敘事節奏，夢境確認後的場景套件回應玩家親手寫下的念頭。差異集中在四個面向，觸發者、輸出契約、離線降級，以及是否在世界留下痕跡。

> [!TIP]
> **快速導航指引**
> * 十個生成層的完整清單與其餘情境，請參閱 [LLM 10 大業務情境與調度流程](/development/llm-scenarios)。
> * 輸出如何被驗證與降級，請參閱 [護欄天梯與語意驗證機制](/development/llm-guardrails)。
> * 單一寫入者邊界與非同步架構，請參閱 [核心架構與邊界契約](/development/llm-architecture)。

---

## 三條路徑對照

| 面向 | 公會櫃檯委託 | 故事橋段的任務種子 | 夢境確認後的場景套件 |
| :--- | :--- | :--- | :--- |
| 觸發者 | 玩家在公會櫃檯輸入指令 | 決定性敘事核心（目前無生產觸發者） | 玩家確認夢境方向 |
| 進入點函式 | `generate_quest_blueprint` | `generate_beat_quest_blueprint` | `generate_beat_scene_blueprint` |
| 輸出契約 | `QuestBlueprint` | `QuestBlueprint` | 擴充藍圖，任務本體加套件區段 |
| 結構定義（schema）宣告 | 能力層已註冊的輸出結構定義 | 同左 | 同層，就地覆寫為擴充結構定義 |
| 離線降級 | 抽手寫範本池 | 回傳 `None` | 回傳 `None`，能力未開時工作停在等待 |
| 世界殘留 | 任務板一筆委託，場景與佔用者隨回收消失 | 排定的橋段與其註冊任務 | 具名持久角色、對話階段、參與者記憶 |
| 公會身分 | 必須具備 | 依情境要求 | 不需要 |

三條路徑都由 `world/ai/scenario_director/` 承接，共用同一組護欄、重試預算與語意驗證器。差別落在輸出契約的形狀與降級語意。

---

## 一、公會櫃檯委託（通用任務）

### 業務觸發

玩家走到公會櫃檯，以已註冊冒險者的身分輸入 `guild request [討伐|採集|護衛|探索|緊急]`，未指定類型時預設為討伐。指令實作在 `commands/guild.py::CmdGuildRequest`，別名為 `guild 委託` 與 `委託任務`。

情境限制由 `resolve_staff()` 判斷，必須在公會且能找到帶 `GuildStaff` 元件的櫃檯人員。指令進行期間 `caller.ndb.guild_request_pending` 會阻擋重複送出，玩家看到「委託正在規劃中，請稍後再試。」。這是因為生成過程會跨多次非同步呼叫，不能讓玩家連點。

### 呼叫鏈路

```text
玩家輸入 guild request [類型]              # commands/guild.py::CmdGuildRequest
  └── resolve_staff()                      # 需在公會、已註冊冒險者
        └── request_generated_quest()      # server/ai_director_service.py
              ├── build_scenario_director_client()   # 依 scenario_director 設定檔
              ├── generate_quest_blueprint()         # world/ai/scenario_director/generation.py
              │     ├── 成功 ──> QuestBlueprint
              │     └── 降級 ──> 自手寫範本池抽取符合條件者
              │     └── 無合適範本 ──> NoSuitableTemplateError
              └── compile_quest_blueprint()          # world/quests/compile/
                    └── register_generated_quest()   # 註冊並張貼至公會任務板
```

`server/ai_director_service.py` 是 `generate_quest_blueprint` 唯一的生產呼叫者，它的位置在 `server/` 是因為只有該目錄允許同時匯入規則層與生成層。

### 輸出與權威

輸出為一份任務藍圖，包含階級、發行者、階段、獎勵與失敗條件。發行者由情境注入的公會分部決定，階級帶受限於玩家階級，功績不得為私人來源。這些檢查發生在編譯期，未通過就不會註冊，玩家也不會在任務板上看到任何痕跡。

### 離線降級

模型未啟用或輸出不合規時，改從手寫範本池抽取條件相符的任務，玩家仍能取得一份可玩的委託。連範本都沒有才具名失敗，訊息為「公會目前沒有適合你的委託。」。

### 世界殘留與雙方視角

任務板多出一筆委託，玩家以 `guild accept` 承接。場景屬臨時副本，佔用者在回收時消失，因此公會路線不會在世界留下持久的角色。玩家感受是可預期、可重複，當場拿到結果。對 GM 而言，來源是一份以定義鍵索引的註冊任務，壞了可以重新產生，處置手段集中在既有的任務 GM 動詞。

---

## 二、故事橋段的任務種子

### 業務觸發

決定性敘事核心挑出一個注意力候選，或收到一筆已確認的創作請求，之後呼叫 `world/narrative/director.py::attempt_decision()` 決定是否安排橋段。橋段家族包含後續、線索、邀請、信件與任務種子，其中任務種子會生出真正的任務。

**目前沒有生產觸發者。** 在 `commands`、`server`、`web`、`typeclasses` 與 `world` 全範圍搜尋 `attempt_decision`，非測試檔案只有它的定義本身，其餘呼叫者都在測試裡。夢境路線也不經過這個入口，`world/narrative/dispatch_runner.py` 自行組裝呼叫後直接進入 `settle_decision()`。因此「自動續篇、主動來信、線索浮現」目前不會自行發生，需要一個尚未實作的生產排程器。

### 呼叫鏈路

```text
決定性敘事核心
  └── attempt_decision(candidate=… 或 request=…)
        ├── 準備不可變脈絡框架
        │     └── 超過 MAX_TOTAL_SIZE ──> 放棄本次決策
        ├── generate_beat_quest_blueprint()     # world/ai/scenario_director/generation.py
        │     ├── 成功 ──> QuestBlueprint
        │     └── 降級 ──> None（不抽範本）
        └── settle_decision()                   # 交易式寫入
              └── 導演決策、故事線、排定橋段、任務註冊一併提交
```

### 輸出與權威

輸出為 `PreparedQuestBeat`，再由 `world/narrative/quest_beats.py` 轉成任務註冊所需的資料。發行者取自既有參與者或公會發行情境，因為此時的任務通常接續既有故事線，而非憑空創造新的權威來源。

### 離線降級

模型不可用時回傳 `None`，不安排任何橋段。設計明文要求不以替代內容填充失敗的敘事橋段，所以這條路徑沒有範本池。

### 世界殘留與雙方視角

只有被排定並註冊的橋段才會留下痕跡，包含導演決策紀錄、故事線關聯與任務本身。玩家看到的內容與一般公會委託相同，差別在來源。對 GM 而言，這條路徑的價值在於「為什麼會出現這份任務」有完整紀錄，代價是它需要一個生產排程器才會運作。

---

## 三、夢境確認後的場景套件

### 業務觸發

玩家在睡夢中與夢境協作者推敲一個念頭，確認前會看到系統理解的具體要求，例如指定地點、需要的新角色與私人委託。確認之後玩家立刻醒來繼續遊玩，生成在背景進行，不佔用當下的操作，也不推進遊戲時間。

### 呼叫鏈路

```text
玩家確認夢境方向                            # server/dream_service.py
  └── 同一筆交易建立或取回工作記錄            # world/narrative/（夢境派送紀錄）
        └── 提交後喚醒背景泵                  # server/dream_dispatch_service.py
              ├── 單一進行中生成，能力檢查先於階段領取
              ├── 故事階段 ──> story_director 能力
              ├── 場景階段 ──> generate_beat_scene_blueprint()
              │                  └── world/narrative/quest_beats.py::to_scene_package()
              └── 發布階段 ──> publish_scene_package()      # world/quests/encounters.py
                                    └── 在 settle_decision() 的交易內提交
```

發布完成後，遭遇啟用由 `world/quests/encounter_activation.py::activate_scene_encounter()` 在真實探索邊界判定，涵蓋移動、重連、啟動，以及發布當下玩家已經符合條件的情形。啟用會建立或取回具名角色、綁定套件身分並配置對話階段，再進行該次位置變化的結果判定。

### 輸出與權威

輸出為一份場景套件，內含角色定義、獨立觸發的相遇、各階段開場白與話題、私人委託，以及互斥結果群組。委託由套件宣告的角色發行，不需要公會身分。嚴格檢查落在啟用期的實際實體註冊，因此授權鏈比公會路線長。

### 離線降級

模型不可用時回傳 `None`，工作停在 `waiting_service` 並保留原因，不以範本或替代內容補位。玩家會看到等待或失敗訊息，不會看到以生成文字冒充的完成狀態。

### 世界殘留與雙方視角

這條路徑留下的痕跡最多，包含持久具名角色、保留的目的地、對話階段、參與者記憶與互斥結果群組。同一版本只會產生一份工作，重複確認與過期回覆都不會生成第二套角色，玩家可以離線等待並在重連後取得最新狀態。

對 GM 而言，可追蹤的鏈路涵蓋確認的念頭版本、工作記錄、導演決策、排定的橋段、已發布套件與啟用綁定，事件帶著請求、工作、階段、權杖、決策、故事線、套件與場景等識別碼。內容無法從範本重製，處置需跨敘事、任務與地圖三個領域的 GM 動詞。

---

## 分工與已知限制

選擇哪條路徑取決於需求。玩家要一份工作就用公會櫃檯，敘事需要下一拍就用橋段種子，玩家親手寫下的念頭才走夢境。三者的共同前提是確定性核心負責套用所有狀態變更，生成層只提交提案。

目前有三項限制值得記住。公會與夢境兩條路線共用 `scenario_director` 這個能力層與其設定檔，因此無法單獨調參或單獨停用場景路線，設計上的終態是讓場景路線擁有自己的層與設定檔。橋段種子那條路徑缺生產排程器，功能完整但不會自行啟動。護衛委託能在公會櫃檯提出，但護衛階段要求完整契約（數量為一、單一完成判準，且受保護與會合角色必須來自已發布的場景套件），櫃檯的一般提案沒有套件角色，所以這條路線拿不到護衛委託，私人護衛委託只從夢境路線產生。

---

## 程式碼對照

| 位置 | 職責 |
| :--- | :--- |
| `commands/guild.py` | `guild request` 指令、公會情境檢查與重複送出防護 |
| `server/ai_director_service.py` | 通用任務生成的唯一生產呼叫者與客戶端建構 |
| `server/dream_dispatch_service.py` | 夢境派送的背景泵，單一進行中生成與生命週期 |
| `world/ai/scenario_director/generation.py` | 三個進入點與各自的降級語意 |
| `world/narrative/director.py` | 橋段決策入口與交易式結算 |
| `world/narrative/dispatch_runner.py` | 夢境派送的檢查點階段執行器 |
| `world/narrative/quest_beats.py` | 橋段資料與場景套件重排 |
| `world/quests/encounters.py` | 套件發布、角色查詢與保留 |
| `world/quests/encounter_activation.py` | 真實探索邊界的遭遇啟用 |
| `world/quests/compile/` | 任務藍圖的編譯與註冊 |
