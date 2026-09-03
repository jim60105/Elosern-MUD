# prefill-telnet-concept-from-proposal — Design

## Context

現狀（`commands/character_creation.py` 實讀）：`CmdCharacterConcept` 走 guarded pipeline 取得提案後，`_complete_interactively` generator 顯示 `_proposal_summary`，然後三道提示——「角色姓名（輸入 cancel 取消）」「實際年齡（至少 18…）」「外表年齡（至少 18…）」，`_integer` 解析年齡。查證：姓名提示**沒有**重問迴圈——空字串原樣接受、一路送到 `_activate_creation` 才由 preflight 以「輸入無效…請重新執行 character concept」整段中止（全部輸入作廢）；年齡解析失敗同樣整段中止。啟動時組的 `CharacterCreationRequest(mode="custom", …)` 不帶 `background`／`affinity_elements`（dataclass 兩欄存在且 custom 路徑已支援），提案的 persona 塊則如實傳入 `_activate_creation`。

上游 `extend-concept-proposal-fields` 讓提案物件帶五個正規化欄位（`None`＝缺席）。本變更把 Telnet 流對齊 webclient 的「提案＝暫態填入器」語意：提案值為預設、玩家把關。

約束：prompt 機架（sync generator 路徑＋async `_ConceptPromptCmdSet` feeder）不動；`cancel` 語意與「至少 18」提示訊息的成年表述不動（那是玩家覆寫時的把關說明，非 LLM 約束）；`preflight_character_creation` 仍是最終權威；命令鍵／別名／語法不動。

## Goals / Non-Goals

**Goals:**

- 三道提示變成「預填可覆寫」：提示文案顯示提案預設值（如「角色姓名（預設：雪貓，Enter 採納，cancel 取消）」），空輸入（Enter）→ 採納預設；非空 → 覆寫；提案缺席該欄 → 維持現行強制輸入文案。
- 請求攜帶 `background`／`affinity_elements`。
- 摘要顯示五欄，讓玩家在補欄前讀到將採納的值。

**Non-Goals:**

- 新增任何交互步驟（不問背景／親和——提案給就採納，沒給就留空，與 webclient 表單缺席語意一致；玩家啟動後可用 persona 命令族改背景）。
- prompt cmdset 機架重寫；webclient 面（owned by `retool-concept-fill-navigation`）。

## Decisions

### D1: 預設採納以「空輸入」表達，不問 yes/no

三道提示在提案有值時改文案為「預設：X，按 Enter 採納」；`_feed_input`／generator 收到空字串即取預設值。

- 替代方案（「採納預設？(Y/n)」第四道提示）：被否——多一次往返與一個失敗模式，且與既有「cancel 取消」慣例堆疊；空輸入＝採納是預填流程的通用語意。
- 缺席姓名的空回覆改為**就地重問**（strip 後為空 → 重示同一提示，直到非空或 `cancel`）。這是**新增**行為而非現行語意（現行：空字串直送 preflight、整段中止）：預填流程裡讓一個空 Enter 作廢全部進度是不可接受的失敗模式。年齡提示維持現行 `_integer` 錯誤→整段中止路徑（格式錯誤非空回覆類別，改它超出本變更範圍）。

### D2: 年齡覆寫仍走 `_integer` + 成年閘；預設值天然過閘

提案年齡經生成層夾取必 ≥ 18，Enter 採納必過 `preflight`；玩家覆寫打 17 → 既有 `CharacterCreationError` 路徑（「輸入無效…請重新執行」）不變——成年閘不可繞過契約原樣保留。缺席年齡（`None`）→ 提示無預設、強制輸入，同現行。

### D3: 摘要擴充與請求組裝

`_proposal_summary` 在 persona 段落前插「姓名／實際年齡／外表年齡／背景／元素親和」行（缺席顯示「（未提案，將由你輸入／留空）」）。`_activate_creation` 呼叫點增 `background=proposal.background`、`affinity_elements=proposal.affinity_elements`（缺席 `None` 直傳——custom 驗證器把 `None` 標準化為中性 `()`）。
