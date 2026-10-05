# LLM 10 大業務情境與調度流程

《伊洛瑟恩》的生成體系共涵蓋 10 個落地的業務情境層（Generative Layers）。每個情境層均擁有專屬的業務觸發點、脈絡組裝管線、Prompt 契約以及確定性離線降級機制。

> [!TIP]
> **快速導航指引**
> * 欲了解頂層單一寫入者邊界與非同步架構，請參閱 [核心架構與邊界契約](/development/llm-architecture)。
> * 欲了解各情境背後的驗證管線與 12 階天梯，請參閱 [護欄天梯與語意驗證機制](/development/llm-guardrails)。
> * 欲配置個別情境層所使用的模型與溫度參數，請參閱 [端點配置與模型調優指南](/development/llm-configuration)。
> * 欲調整各情境的提示詞字句，請參閱 [提示詞資料庫](/gm/prompts)。

---

## 10 大生成層快速對照表

| 層級名稱 (`LAYER_NAMES`) | 核心模組 | 業務觸發點 | 輸出類型 | 離線降級結果 (Fallback) |
| :--- | :--- | :--- | :--- | :--- |
| **`narrator`** | `world/ai/narrator.py` | 戰鬥/行動事件日誌結算 | 正體中文散文 | 呼叫本地範本渲染器輸出標準文字 |
| **`npc_dialogue`** | `world/ai/npc_dialogue.py` | 玩家發起對話（`talk`） | JSON（台詞 + 8 種意圖） | 回退為作者手寫問候語或保持沉默 |
| **`dialogue_summary`** | `world/narrative/epochs.py` | 決定性擁有者要求紀元壓縮 | JSON（衍生摘要） | 保留原始對話與目前紀元，使用有界的近期脈絡 |
| **`correspondence`** | `world/ai/correspondence.py` | 決定性擁有者明確要求回信 | JSON（信文與受限關係提案） | 來信照常送達，回信工作保留待處理 |
| **`dream`** | `world/ai/dream.py` | 夢境協商會話的一次已完成交換 | JSON（露骨場景散文 + 對談者台詞 + 伺服器興奮階段） | 回傳 `None`（無生成散文；`world.narrative.dream_track.render_ending` 仍可無模型收尾與喚醒） |
| **`scenario_director`** | `world/ai/scenario_director.py` | 公會委託櫃檯任務查詢 | JSON（任務藍圖） | 自手寫任務範本池抽取符合條件之任務 |
| **`scene_builder`** | `world/ai/scene_flavor.py` | 玩家進入動態副本房間 | 正體中文氛圍散文 (50-200 字) | 回傳 `None`（房間不附加額外氛圍） |
| **`character_creation`** | `world/ai/character_creation.py` | 玩家輸入自然語言創角構想 | JSON（配點/人設/技能） | 回傳 `None`（引導切換至手動點選精靈） |
| **`action_options`** | `world/ai/action_options.py` | 移動進房、行動結算、登入 | JSON（3～5 張行動卡片） | 回傳 `None`（前端僅呈現原生按鈕） |
| **`title_nomination`** | `world/ai/title_nomination.py` | 登出、休息結算、公會升階、任務通關 | JSON（候選異名與事蹟引用） | 回傳空選票（不生成新稱號） |
| **`story_director`** | `world/ai/story_director/` | 決定性敘事核心排定故事橋段（`world/narrative/director.py`） | JSON（單一橋段提案：後續／線索／邀請／信件／任務種子） | 回傳 `None`（不排定任何橋段，不生成替代內容） |

---

## 1. 旁白敘事層 (`narrator`)

### 業務定位
將遊戲底層發生的客觀事件日誌（`EventLog`，例如戰鬥傷害、格擋、狀態賦予、道具消耗）轉換為連貫、具備文學質感且嚴格忠於事實的正體中文敘事散文。

### 呼叫鏈路
```text
遊戲事件結算 (EventLog)
  └── narrate_event_logs(event_logs, client)          # world/ai/narrator.py
        └── guarded_call("narrator", client, descriptor)
              ├── 成功 ──> 返回散文文字
              └── 降級 ──> 呼叫注入的 _template_renderer(event_logs)
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/narrator.yaml` $\rightarrow$ `narrator.system`（無動態預留位置）。
* **使用者輸入**：將結構化的 `EventLog` 清單序列化為嚴格受限的文字字串，包含發動者、目標、行為與數值。
* **邊界限制**：輸入記錄數最多 20 筆、每筆最多 60 個條目、總序列化上限 12,000 字元。

### 語意防護與降級
* **語意檢查器**：檢查輸出非空、長度不超過 2,000 字、必須含有 CJK 統一漢字、不得殘留如 `{actor}` 或 `{target}` 等未置換的範本標籤。
* **確定性降級**：若連線失敗或輸入超出限制，直接呼叫啟動時注入的 `world.rules.event_log.render_plain_text`，渲染出完全確定性的標準日誌文本。

---

## 2. NPC 對話與意圖層 (`npc_dialogue`)

### 業務定位
讓 NPC 在面對玩家時，能根據自身完整人設、所處環境、當前記憶、好感度狀態以及玩家的外在偽裝，產出符合語境的對話內容，並能主動提出具備遊戲規則效力的行為意圖。

### 呼叫鏈路
```text
玩家發起指令 (commands/talk.py 或 Webclient 對話面板)
  └── typeclasses/npcs.py: NPC.at_talked_to()
        ├── 檢查排程與作息 (npc_schedules.interaction_reason)
        ├── 啟動思考提示計時器 (_echo_thinking)
        ├── generate_npc_reply(...)                   # world/ai/npc_dialogue.py
        │     └── guarded_call("npc_dialogue", ...)
        └── 收到結果
              ├── 成功 ──> 顯示台詞，呼叫 world/rules/npc_intents.py 套用意圖
              └── 降級 (None) ──> 顯示手寫預設問候語 (default_greeting) 或沉默
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/npc_dialogue.yaml` $\rightarrow$ `npc_dialogue.system`。
* **白名單預留位置**：`{name}`（NPC 名字）、`{desc}`（外觀特徵）、`{location}`（API 保留，穩定定錨傳入空字串）、`{persona}`（人設區塊）。當前位置放在新回合框架；歷史框架保留原始時間與資料。
* **動態記憶與脈絡**：
  * 最近 12 輪交談記憶（Memory Window）。
  * 玩家對象資訊：公開形象、表觀特徵與社交連結（玩家的真實隱藏身分與隱藏背景絕不進入 Prompt）。
  * 秘密清單（`no_leak_secrets`）：包含 NPC 內部數值好感度、玩家被偽裝的真實屬性數值。

### 輸出契約與意圖白名單
LLM 必須輸出 JSON 格式：
```json
{
  "speech": "正體中文對話台詞",
  "intent": {
    "kind": "adjust_relation",
    "delta": 3
  }
}
```
* **8 種合法意圖白名單**：
  1. `give_item`：贈予物品
  2. `take_item`：索取物品
  3. `offer_quest`：主動提供任務
  4. `request_guild_exam`：引導/要求公會升階測驗
  5. `adjust_relation`：好感度微調（`delta` 限制在 0～10）
  6. `reveal_lore`：揭露特定世界觀情報
  7. `party_invite`：邀請組隊
  8. `none`：純交談無額外行為

### 語意防護與降級
* **數值洩漏防護（No-leak Validation）**：若 `speech` 台詞中出現任何屬於 `no_leak_secrets` 的具體數值，一律判定驗證失敗並發起重試。
* **降級機制**：模型異常或重試耗盡時回傳 `None`，呼叫端自動顯示手寫的作者問候語。

---

## 3. 任務企劃導演層 (`scenario_director`)

### 業務定位
由「任務導演（ScenarioDirector）」扮演公會委託企劃，依據公會分部、玩家階級與當前環境，動態生成一份結構完整、符合世界觀規章的任務藍圖（`QuestBlueprint`）。

### 呼叫鏈路
```text
公會櫃檯查詢任務 (commands/guild.py)
  └── server/ai_director_service.py: request_generated_quest()
        └── world/ai/scenario_director.py: generate_quest_blueprint()
              └── guarded_call("scenario_director", ...)
                    ├── 成功 ──> compile_quest_blueprint() 編譯並登錄任務
                    └── 降級 ──> 從 director_templates.py 挑選合適手寫範本
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/scenario_director.yaml` $\rightarrow$ `scenario_director.system`。
* **預留位置**：`{name_inspiration}`（種族命名風格參考）。
* **任務類型（5 大類別）**：採集（`GATHER`）、討伐（`DEFEAT`）、護衛（`ESCORT`）、探索（`EXPLORE`）、緊急（`EMERGENCY`）。

### 輸出規格與藍圖結構
輸出必須為吻合 `QuestBlueprint` 的 JSON 物件：
* `stages`：階段目標（擊敗怪物、到達地點、護送 NPC、取得道具）。
* `location_req`：場景階層與原型需求（Anchor、Grid 或動態 Instance）。
* `npc_req`：目標 NPC 之角色階層、署名身分（`display_name`、`title`），以及必填的精簡人物卡 `persona`（`identity` 含 `public`／`hidden`、`appearance`、`personality`、`speech_style`、`life_story`、`habit`、`social_connection` 七欄）；整份藍圖所有階段的 `npc_req` 合計最多 3 個。
* `reward`：銅幣（整數）、物品清單與公會功績點（Merit）。
* `failure`：期限時數與失敗代價。

### 語意防護與降級
* **登錄表存在性校驗**：藍圖中引用的怪物階級、物品程式碼、錨點與公會分部，必須 100% 存在於 `world.lore` 靜態登錄表，杜絕幻覺產生不存在的獎勵或目標。
* **獎勵邊界保護**：報酬銅幣不得超過該公會階級的上限。
* **人物卡契約**：每個 `npc_req` 的人物卡都透過共用的 `world/quests/characterization.py` 依精簡人物卡契約（`world/lore/npc_card.py`）驗證必填欄位與字數上限；編譯、持久化還原與場景具現化時都會再驗證一次，具現化時經 `initialize_npc_persona` 以 `generated_quest` 來源寫入 NPC。
* **降級機制**：若失敗，立即由 `world/ai/director_templates.py` 根據請求的階級與地點，隨機抽出一張預先編寫的手寫任務範本編譯交付。

---

## 4. 場景氛圍散文層 (`scene_builder`)

### 業務定位
為動態生成的任務副本房間提供一段 50 到 200 字的正體中文感官氛圍散文（描繪光影、空氣、濕度、聲音與氣味）。

### 呼叫鏈路
```text
玩家移動進入副本房間 (commands/scene.py)
  └── transaction.on_commit(schedule_scene_flavor)
        └── server/scene_flavor_service.py: schedule_scene_flavor()
              └── world/ai/scene_flavor.py: generate_scene_flavor()
                    ├── 成功 ──> 寫入 room.db.scene_flavor 並推送至客戶端
                    └── 降級 (None) ──> 不設置氛圍，無副作用
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/scene_builder.yaml` $\rightarrow$ `scene_builder.system`。
* **預留位置**：`{scene_sentence}`（核心場景句）、`{quest_context}`（任務背景）、`{room_name}`（房間名稱）、`{region}`（所在區域）。

### 語意防護與降級
* **無數字鐵律（No Fabricated Numbers）**：**文本中嚴禁出現任何半形或全形阿拉伯數字**。若出現數字（例如「3 隻哥布林」、「長度 10 公尺」），驗證器立即判定失敗並要求重試，防止 LLM 越權虛構實體數量或規格。
* **長度硬性邊界**：字數嚴格限制在 50～200 字之間。
* **降級機制**：回傳 `None`，房間維持原生基礎描述，不影響玩家探索。

---

## 5. 創角概念轉換層 (`character_creation`)

### 業務定位
將玩家以自然語言輸入的模糊角色構想（例如「隱居雪山的獸人狂戰士，外表冷酷但性格敦厚」），精確轉換為符合遊戲規則與配點預算的合法角色提案（`CharacterProposal`）。

### 呼叫鏈路
```text
玩家在創角介面輸入構想 (CLI 或 Webclient 創角面板)
  └── server/ai_director_service.py: request_character_proposal()
        └── world/ai/character_creation.py: generate_character_proposal()
              ├── 成功 ──> 回傳 CharacterProposal 供介面預覽確認
              └── 降級 (None) ──> 回傳 None，介面提示手動配點
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/character_creation.yaml` $\rightarrow$ `character_creation.system`。
* **預留位置**：`{concept}`（玩家原始輸入）、`{race_catalog}`（動態種族/子種族屬性上下限與親和預算清單）。

### 輸出規格與核心校驗
輸出為結構化 JSON 提案：
* `race_key` / `subrace_key`：必須存在於登錄表。
* `allocations`：7 大屬性配點（`hp`、`mp`、`sp`、`atk_phys`、`agility`、`defense`、`magic_power`），總和必須精確等於該種族預算。
* `suggested_skills`：推薦初始技能（最多 8 個）。
* `persona`：三人設草稿（`personality` 性格、`life_story` 生平、`habit` 習慣）。
* **年齡合理值（Age Range Bound）**：`age` 與 `apparent_age` 為 $0$ 至 $10000$ 的整數，越界的提案由底層驗證器直接修正到範圍內。

---

## 6. 行動建議卡片層 (`action_options`)

### 業務定位
在 Webclient HUD 介面的情境操作區，為處於探索模式（Exploration Mode）的玩家即時運算出 3～5 張符合當前環境、具備高度可行性的行動建議卡片（`SuggestionCard`）。

### 呼叫鏈路
```text
玩家移動、行動結算或登入 (at_post_move / dispatcher.py / ingress.py)
  └── server/option_proposal_service.py: schedule_action_options()
        └── world/ai/action_options.py: generate_action_options()
              └── 12 階驗證天梯 (Ladder 0～11)
                    ├── 成功 ──> 快取並推送 OOB 訊息至 Webclient
                    └── 降級 (None) ──> 記錄短期負向快取，前端顯示預設按鈕
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/action_options.yaml` $\rightarrow$ `action_options.system` 與 `action_options.user`。
* **使用者輸入預留位置**：`{room_name}`、`{room_summary}`、`{npc_entries}`、`{monster_entries}`、`{objective}`、`{narrative_tail}`、`{affordances}`（現場確實可執行的動作清單）。
* **結構化需求**：此層級要求 Profile 必須支援 `supports_response_format: True`。

### 12 階驗證天梯（Ladder）
所有建議卡片必須在本地連續通過 12 道嚴格關卡，詳見 [護欄天梯與語意驗證機制](/development/llm-guardrails)。其中最核心者為：**卡片內之 `action_code` 必須與當前環境實際提供的可執行動作（Affordances）完全一致**，杜絕無效動作卡。

---

## 7. 異名稱號提名層 (`title_nomination`)

### 業務定位
在冒險的重要休息節點，根據玩家近期的真實冒險歷程（`EventLog`），提煉出 5 個具備事蹟佐證的候選異名（Epithet），並過濾出前 3 名合格者組成投票選票。

### 呼叫鏈路
```text
觸發休息或里程碑 (登出 / 旅店休息 / 公會晉階 / 任務完成)
  └── server/title_nomination_service.py: schedule_epithet_nomination()
        └── world/ai/title_nomination.py: generate_epithet_candidates()
              └── 執行碰撞過濾器 (長度、本名排斥、去重)
                    ├── 成功 ──> 規則層 persist_nomination_ballot 寫入待選清單
                    └── 降級 (None 或空) ──> 不產生選票，流程靜默結束
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/title_nomination.yaml` $\rightarrow$ `title_nomination.system` 與 `title_nomination.user`。
* **預留位置**：`{player_name}`、`{full_title}`、`{recent_events}`（近期事件紀錄）、`{declined}`（歷史拒絕清單）、`{removed}`（主動卸除清單）。

### 輸出與碰撞過濾
* **輸出格式**：5 筆 `{"display": "2~8字異名", "basis": "80字以內事蹟引用"}`。
* **碰撞過濾器**：
  1. 字符必須為 2 到 8 個 CJK 漢字。
  2. 絕對不得包含玩家角色姓名。
  3. 排除登錄表既有固定稱號、已獲得稱號或歷史名單。
  4. 批次去重後挑選前 3 名建立候選選票，推送至前端供玩家點選。

---

## 8. 故事導演層 (`story_director`)

### 業務定位
由確定性敘事核心（`world/narrative/director.py`）驅動的故事橋段排定：每次決策最多排定一個橋段，也可以選擇不排定。生成層只提出值（value-only）提案，路由、驗證與寫入一律由確定性擁有者執行。

### 呼叫鏈路
```text
決定性注意力候選 或 已確認創作請求 (CreativeRequest)
  └── world/narrative/director.py: attempt_decision()
        └── 擷取不可變脈絡快照 (capability=story_director)
              └── world/ai/story_director/: generate_beat_proposal()
                    └── guarded_call("story_director", ...)
                          ├── 成功 ──> settle_decision() 依 kind 決定效果
                          └── 降級 ──> 回傳 None：不排定任何內容，不留替代填充
```

### 輸入與提示詞
* **提示詞鍵值**：`prompts/story_director.yaml` $\rightarrow$ `story_director.system`。
* **預留位置**：無（有界的候選／請求脈絡以使用者訊息中的確定性 JSON 影格傳入）。
* **輸出欄位**：`kind`（`follow_up`／`clue`／`invitation`／`letter`／`quest_seed`）、`summary`（1–600 字正體中文），可選 `recipient`、`relation_delta`（0–10）、`writes`（必須為空陣列）。

### 效果路由（確定性核心決定）
* `follow_up`／`clue`／`invitation` $\rightarrow$ `narrative_statement`：敘事擁有者寫入敘事事件並登錄故事線發展。
* `letter` $\rightarrow$ `letter_send`：敘事擁有者以 `send_letter` 送出並登錄為故事線陳述。
* `quest_seed` → `generate_beat_quest_blueprint()` → 確定性的任務編譯與連結發布。缺少或降級的節拍藍圖產生 `no_content`，絕不會改用作者範本取代。
* `relation_delta`：關係屬於規則擁有者的資料，敘事僅把提案值路由給規則套用器；失敗則整筆拒絕且不留部分狀態。

---

### 任務節拍編譯邊界（2026-10-04）

`attempt_decision()` 先擷取允許的不可變導演框架，再於結算交易之外請求任務藍圖。節拍專用的客戶端透過 `quest_client` 傳入，或由伺服器組合根以 ScenarioDirector 設定檔建構，絕不使用故事導演的傳輸通道。節拍專用的 ScenarioDirector 入口沿用既有的設定檔、護欄、schema 與語意驗證器。與一般的 `generate_quest_blueprint()` 不同，它在傳輸停用、驗證耗盡、脈絡不合或框架過大時回傳空內容。一般入口保留其作者離線範本。

發行人是擁有者已登錄的公會分支，或由節拍明確指名的授權 NPC 參與者。發布時重檢來源／請求版本、故事線修訂與存取權、當前階級、發行人身分與地點錨點。任務編譯器對獎勵、典據參考、場景需求與發行人授權仍具權威。任何散文都不能承接委託、推進目標、宣稱已完成的行動，或建立房間。

`ScheduledBeat.payload.quest` 保留正規化的藍圖、定義鍵、發行人鍵與脈絡快照 ID。節拍與持久的產生任務鏡像一起提交；任務擁有者的發布範圍在 savepoint 失敗後還原行程註冊表與 Evennia 屬性快取。重播已擷取的來源身分會回傳既有的決策，不再呼叫模型。SceneBuilder、執行個體回收、接觸式承接與任務執行期都不變。

變更紀錄：啟用真實的任務種子發布，加入無填充產生與來源重驗證，並保留一般的離線行為。玩家指令與瀏覽器動作都沒有變更。

## 相關延伸閱讀

* 深入探索各情境的語意驗證器與天梯實作：[護欄天梯與語意驗證機制](/development/llm-guardrails)
* 了解如何為不同層級配置不同的模型與 API 端點：[端點配置與模型調優指南](/development/llm-configuration)
* 查閱各情境對應的 YAML 提示詞範本：[提示詞資料庫](/gm/prompts)
