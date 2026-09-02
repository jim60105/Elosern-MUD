# retool-concept-transient-fill — Design

## Context

現行概念流（archive `creation-persona-persistence`）：`creation.concept` adapter 跑 guarded pipeline 後呼叫 `apply_concept_proposal`，把提案值＋persona 塊存進 `concept_filled` 草稿階段，並以 draft 指紋 compare-and-swap 防晚到回應；呈現層依 D4 把 persona 塊完全隔離於 wire 之外，只發 `background_generated` 布林指示。custom save 只在 submitted race 等於概念 draft race 時承接 persona，否則清空。啟動時 persona 由概念 draft 讀入。

查證（設計文件 §1）確立：persona 只在建立時被 LLM 寫一次、之後無生成覆寫路徑；background 是 persona record 內的一個鍵，與三欄敘事文字同類；客戶端上傳玩家選擇值並經伺服端重驗是既有成熟模式（allocations 與 background textarea 皆然）。本變更把概念降為無狀態填入器，把 persona 交還玩家。

約束：單一寫入者邊界（`world/ai/` 永不寫入）；`ui_action_result` envelope exact 無 data 欄位（`webclient-oob-protocol`），提案不能經 result 送達；panel payload 走 exact-field 驗證與 65536 bytes envelope 上限；無相容層義務（未發布）。

## Goals / Non-Goals

**Goals:**

- 概念一次呼叫零持久寫入；提案以倉庫現成的 session 瞬態模式送達（仿 `session.ndb.options_state` → `PresentationContext.options_state` → presenter 渲染）。
- 退役 `concept_filled` 階段、`apply_concept_proposal`、CAS 的 concept 用途、承接與 race 比對、`background_generated` 指示。
- persona 三欄成為 custom draft／`creation.custom` payload／啟動寫入的一等欄位，驗證重用 `_validate_persona_block`。
- 建立表單渲染三個可編輯 persona textarea；換種族時僅 UI 警示，伺服端不覆蓋、不拒絕。
- Telnet 概念流與 WebClient 共用同一暫態語意（提案摘要 → 補欄 → 啟動）。

**Non-Goals:**

- 啟用後的 persona 編輯面與角色面板四欄（owned by `add-persona-edit-surface`）。
- `identity / appearance / social_connection` 的渲染與注入（owned by `add-persona-depth-dialogue-injection`）。
- 玩家編輯 persona 的上傳防偽裝／清洗策略（上傳即意圖，見 D5）。
- 指紋函式本體退役（啟動確認綁定 `fix-creation-finalization-safety` 仍需要它）。

## Decisions

### D1: 提案送達走 session 瞬態槽，仿 options_state 先例

adapter 依既有三參 ABI 取得 session，把驗證過的提案連同 session 內單調遞增的暫態序號 `revision` 寫入 `session.ndb.concept_proposal`；`web/webclient/presentation/ingress.py` 的 `build_presentation_context`（全倉庫所有發布路徑唯一的 context 工廠，現行即在此深拷貝 `options_state`）依同款先例深拷貝為提案快照欄；creation presenter 渲染 optional 頂層 `proposal` 鍵。回傳 confirmed success（code `concept_applied`）並宣告 affected `creation`，走既有 panel-update 發布路徑。

- 替代方案 A（result envelope 加 data 欄）：被否，直接抵觸 `webclient-oob-protocol` 的 exact-envelope 契約，為一個功能重開協定欄位得不償失。
- 以內容相等去重取代 `revision`：被否，兩次合法套用的內容可能完全相同，內容去重無法區分「面板重建」與「相同內容的新套用」，必棄其一契約。
- 替代方案 B（persist 於 character.db）：被否，就是現行被退役的草稿機。
- ndb 的斷線即滅語意正是「暫態填入」；重新連線後提案槽消失等同「進行中的填入遺失」，與已接受代價一致。

生命週期：寫入於套用成功（覆蓋舊提案並递增 `revision`）；清除於 custom save 成功、`creation.reset`、session 結束。自訂儲存前每次面板重建照常渲染 proposal，讓中斷前已套用未送出的表單可在同 session 內重建。`revision` 是傳輸層識別元：客戶端只在 `revision` 大於已套用值時填入，內容完全相同的連續套用也能觸發覆蓋，同時面板重建不覆寫玩家編輯。

### D2: persona 鍵在 custom draft 為「必現、可 null」

`custom_filled` 草稿增 `persona: dict | null`。必現鍵＋缺鍵降級的組合讓 `_normalize_draft` 維持「缺鍵＝舊形狀損壞」的單一判準，null 則明確表達「玩家沒有 persona」。`save_custom_draft` 只寫送進來的值，不做任何承接或 race 比對。

- 替代方案（optional 鍵、缺鍵合法）：被否，無法區分「尚未寫入」與「舊形狀草稿」，且違反 repo 的 exact-fields 慣例。

### D3: `creation.custom` payload 增必填 `persona` 鍵（null 或恰三鍵）

九鍵 exact-set 驗證；非 null 值經 `_validate_persona_block`（恰三鍵、各自 1..600 非空）。前端慣例照舊：wire 恆帶齊全鍵，三欄全空送 null。

- 替代方案（欄位扁平為 `persona_personality` 等頂級鍵）：被否，與 DB import-card 形狀分叉、驗證器要另建鍵名映射；repo 慣例是 exact-fields 巢狀區塊（`allocations` 同款）。

### D4: 啟動 persona 來源改為 custom draft

`_request_from_draft` 時代終結後，`activate_player_character` 呼叫端把 `draft["persona"]` 傳入既有 `persona` 參數；無 persona 時維持僅寫 background 的 `elif` 分支。啟動交易、成年閘、全部-or-無語意不動。

### D5: 伺服端放棄 persona 語意防堵

換種族不覆蓋、不拒絕、不清空——玩家看得見自己送出的內容，上传即意圖；UI 在概念提案的種族／血統與目前選擇不同時顯示審視提示（純文案）。現行「race 不同即清空 persona」規則整體消失。

- 替代方案（保留換種族清空，即使 persona 可見）：被否，等於伺服端覆蓋玩家剛打的字，抵觸上傳即意圖模型。

### D6: Telnet 概念流同步降為暫態

`character concept` 改為：跑 guarded pipeline → 顯示提案摘要（含 persona 三欄文字）→ 以互動提示收名字與兩個年齡（過成年閘）→ 以提案值加親打欄位直接啟動。概念摘要就是終端版的「填入表單」，玩家的確認回應即将提案視為自己的輸入。命令語法與別名不變，命令文件不動。

## Risks / Trade-offs

- [概念進行中斷線或關頁，填入遺失] → 已接受代價；同 session 內重按套用即可，面板重建不丟已存 draft。
- [玩家把矛盾的生成生平（錯種族）存進檔] → 伺服端不攔；UI 審視提示＋「重新套用概念一律替換」把修正成本壓在建立期。
- [draft 形狀變更波及 reconnect/activate 既有測試] → 無相容層原則下全數更新既有測試；`--keepdb` 保留庫無舊 draft（pending 角色不跨變更存續）。
- [session.ndb 提案被多餘路徑渲染成幽靈] → 生命週期以測試鎖死：custom save 後、reset 後、新套用覆蓋後三個清除點各一 scenario。
- [worst-case persona 撐破 envelope] → 3×600 CJK ≈ 6 KB，對 65536 上限以 worst-case 測試鎖定。
