# extend-concept-proposal-fields — Design

## Context

現行生成層（`world/ai/character_creation.py`）以 guardrail 的 validation-retry-degrade 管線把概念映成凍結 `CharacterProposal{race_key, subrace_key, allocations, suggested_skills, persona}`；`_validate_shape` 拒絕一切契約外鍵（錯誤訊息明文「no age, no other numbers」），提示詞（`prompts/character_creation.yaml`）同步禁止年齡。主規格 `generative-character-concept` 的「Proposals are validated deterministically」一條把「提案含年齡」列為整體失敗條件。

查證（設計文件 §1）：玩家六問題中的四個空欄位（名字、背景、親和、年齡）全部源自這份契約不產生這些欄位。本變更把提案擴為「暫態填入器」的完整載荷：五個 optional 新鍵 + 「正規化不棄回覆」的失敗分界。

約束：`world/ai/` 永不寫入狀態（架構不變量）；transport-boundary 契約禁止 import `world.rules`（年齡/親和界值必須以 registry 派生值或本地常數鏡像重複，沿用 `ALLOCATABLE_AXES` 先例並以 parity test 鎖住）；`web/` 消費端此刻尚未讀新鍵，擴形狀零破壞；無相容層義務。

## Goals / Non-Goals

**Goals:**

- `CharacterProposal` 增五個 optional 鍵（缺席＝消費端維持本地預設）：`display_name: str | None`、`age: int | None`、`apparent_age: int | None`、`background: str | None`、`affinity_elements: tuple[str, ...] | None`。
- 失敗分界重劃：結構性錯誤（非物件、契約外鍵、persona 缺鍵、配點超預算、假鍵）維持整體失敗→重試→降級；五欄界外值是單欄缺陷，在驗證通過的規範化階段就地修正。
- 提示詞五鍵模板、種族目錄帶親和上限、刪年齡禁令；不向 LLM 敘述成年約束。

**Non-Goals:**

- session 槽 `concept_proposal` 的鍵集擴展與 panel `proposal` 槽 v3（owned by `bump-creation-panel-proposal-v3`）。
- Vue/Telnet 消費（owned by `retool-concept-fill-navigation` / `prefill-telnet-concept-from-proposal`）。
- 客戶端 toast（owned by `add-action-feedback-toasts`）。
- custom save / 激活路徑的任何驗證改變——成年閘（`_validate_adult`）與 custom payload 九鍵驗證器原樣不動；正規化後提案值天然過閘。
- 界值差異的調和——`_validate_adult` 只設下限（≥18、無上限），本層 10000 上限是提案槽/提示詞的生成策略界（鏡像 `creation_wizard.AGE_MAXIMUM` 與 web 驗證器 `AGE_MAXIMUM`），兩者本就不等構；本變更只鎖 parity 一致性，不改任何入口界值。

## Decisions

### D1: 正規化是 validator 的修正返回，不是 guardrail 的重試語義

`world/ai/guardrail.py` 的語義驗證器契約是「回傳錯誤列表」。正規化不改該契約：新增一個驗證器之後的規範化步驟（`_normalize_proposal(parsed) -> dict`），語義驗證全數通過後把界外值就地夾取/截斷/剔除，再構造凍結 dataclass。guardrail 的重試/降級路徑逐字不動。

夾取規則（單一把關點，webclient 與 Telnet 共享）：

| 鍵 | 規則 |
|---|---|
| `age`/`apparent_age` | 缺鍵 → `None`；`< 18` → `18`；`> 10000` → `10000` |
| `display_name` | strip；超 64 code points 截斷；trim 後空 → `None`（缺席） |
| `background` | strip；超 600 截斷；trim 後空 → `None`（缺席） |
| `affinity_elements` | 缺鍵 → `None`；剔除未知元素、去重（保序）、依 `max_affinity_elements(race_key)` 截斷；`race_key == "elf"` → `()`；LLM 給了清單而截後為空 → `()`（中性空集，交付），不是缺席 |

型別錯誤（bool 年齡、null 年齡、非 list 親和、非 str 文本）由輸出 jsonschema 層擋下（`integer`/`string`/`array<string>` 嚴格型別、五鍵 optional），走既有「錯誤附加 → 重試 → 降級」結構路徑；規範化只處理型別正確但界外的值。這讓「不棄回覆」承諾精確落在「數值界外」而非「LLM 給錯型別」上——後者本來就值得一次重試。

- 替代方案（界外值走重試）：被否——重試語義是「LLM 給錯了，再問一次」；年齡 < 18 是設計文件明令「覆寫即可、不告知 LLM」的類別，重試既慢又可能耗盡降級，違反「不棄回覆」要求。
- 替代方案（消費端各自夾取）：被否——兩條 surface 重複規則，違背單一把關點原則。
- 18/10000/2-1-0 界值鏡像在本模組以本地常數 + parity 測試鎖與 `world/rules`（`AGE_MINIMUM`、`_AFFINITY_INPUT_BOUNDS`）一致——transport-boundary 契約禁止 import，先例是 `ALLOCATABLE_AXES` 的鏡像與 parity test。

### D2: 五鍵在輸出 schema 與 shape 白名單為 optional，缺席即 None

`CHARACTER_CREATION_OUTPUT_SCHEMA.properties` 增五鍵（`age`/`apparent_age` 為 `{"type": "integer"}`；LLM 若給非整數，jsonschema 層會拒絕並走重試——這是型別錯誤，屬結構性；界外數值如 15 是合法整數，由 D1 夾取）。`_validate_shape` 的允許鍵集合擴為十字段；「no age」錯誤訊息措辭同步改寫。

缺席語義寫進 dataclass docstring：缺席＝消費端維持本地預設（名字空、年齡 18），不是空字串/0。

### D3: 提示詞改動最小化

`character_creation.system`：契約 JSON 樣板加 `"display_name": "角色名字", "age": 0, "apparent_age": 0, "background": "精簡背景", "affinity_elements": ["元素鍵值"]`；刪除「也不得替玩家決定年齡——年齡一律由玩家自己輸入」與「不得加入年齡欄位」兩句；新增指示：「affinity_elements 的數量不得超過所選種族的親附上限；精靈必須留空」「background 控制在 600 字以內」。`build_race_catalog()` 每個種族條目追加「（親附上限：N）」，N 由本地親和界值映射派生；目錄截斷路徑與長度上限（2000）不變，worst-case 測試重鎖。

替代方案（在提示詞寫明「年齡必須 ≥ 18」）：被否——用戶明令降低 LLM 工作複雜度；成年把關是伺服器夾取職責，提示詞重複約束徒增 token 與漂移面。
