# extend-concept-proposal-fields

## Why

概念功能的 LLM 藍圖契約只產生 `{race_key, subrace_key, allocations, suggested_skills, persona}`，明確禁止名字、背景、元素親和與年齡，導致玩家輸入「一個貓人少女，有豐富的背景設定，性格極端」之後，自訂表單的名字、背景、元素親和一片空白、年齡停在 18——概念功能名不副實。設計源頭：`docs/superpowers/specs/2026-09-03-concept-proposal-expansion-toast-feedback-design.md` §5（本文件同時修訂 2026-09-02 設計「年齡一律玩家輸入」條款）。

## What Changes

- `world/ai/character_creation.py` 的 `CharacterProposal` 與輸出 schema 新增五個 optional 欄位：`display_name`、`age`、`apparent_age`、`background`、`affinity_elements`。**BREAKING**（提案契約形狀變更，無相容層）。
- 新增「正規化、不棄回覆」語意：通過結構驗證的提案，五欄界外值一律就地夾取／截斷／剔除——`age`/`apparent_age` < 18 → 覆寫 18、> 10000 → 覆寫 10000（不重試、不告知 LLM）；`display_name` 截斷至 64、`background` 截斷至 600；`affinity_elements` 剔除未知鍵、去重、依種族上限（human 2／beastfolk 1／elf 0）截斷，精靈強制清空。結構性錯誤（型別錯誤、persona 缺鍵、配點超預算）維持既有「整體失敗 → 重試 → 降級」。
- `prompts/character_creation.yaml`：藍圖契約 JSON 樣板增五鍵；移除「不得替玩家決定年齡」兩句禁令（提示詞不敘述成年約束，降低 LLM 複雜度）；`race_catalog` 每個種族附帶親附上限，並指示精靈留空。
- 本變更止於生成層契約：提案物件、提示詞、驗證器、正規化矩陣與其純邏輯測試。session 槽、panel、前端Consumption 由後續變更承接。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `generative-character-concept`: 「Proposals are validated deterministically against the registries」一條改寫——提案形狀增五個 optional 欄位；「no age」禁令反轉為「age 可出現、由驗證器夾至成年區間」；新增「界外值正規化而非棄提案」的失敗分界（結構性失敗 vs 單欄界外）。

## Impact

- `world/ai/character_creation.py`（dataclass、輸出 schema、語義驗證器、正規化輔助）、`prompts/character_creation.yaml`、`world/ai/tests/`（正規化矩陣、worst-case 文本）。
- 消費端（`web/webclient/actions/creation_actions.py` 的槽儲存、panel presenter、前端）在本變更中不受影響：尚未讀取新欄位。
- 無後端相容層（未發布、零使用者）。與 `add-action-feedback-toasts` 完全不相交，可平行。
