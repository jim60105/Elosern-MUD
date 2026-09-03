# extend-concept-proposal-fields — Tasks

實作順序即分組順序：契約層（schema／驗證／正規化）→ 提示詞 → 測試與登記。每組做完先跑該組 focused 測試再勾選；不跑 CI shard 指令。

## 1. 提案契約與正規化（world/ai）

- [x] 1.1 `world/ai/character_creation.py`：`CharacterProposal` 增五個 optional 欄位（`display_name: str | None`、`age: int | None`、`apparent_age: int | None`、`background: str | None`、`affinity_elements: tuple[str, ...] | None`，預設 `None`），docstring 改寫缺席語義（缺席＝消費端維持本地預設）。新增本地界值常數鏡像（`ADULT_AGE_MINIMUM = 18`、`AGE_MAXIMUM_BOUND = 10000`、`MAX_DISPLAY_NAME_CODE_POINTS = 64`、`_AFFINITY_INPUT_BOUNDS = {"human": 2, "beastfolk": 1, "elf": 0}`），模組頂註解註明 transport-boundary 鏡像先例（`ALLOCATABLE_AXES`）。
- [x] 1.2 同檔：`CHARACTER_CREATION_OUTPUT_SCHEMA.properties` 增五鍵（`display_name`／`background` 為 string、`age`／`apparent_age` 為 integer、`affinity_elements` 為 `array<string>`），全部 optional（不入 `required`）——型別錯誤由 jsonschema 走重試路徑。
- [x] 1.3 同檔：`_validate_shape` 的允許鍵集合擴為十字段，錯誤訊息措辭改寫（刪「no age, no other numbers」句，改為僅十字段白名單表述）。
- [x] 1.4 同檔：新增 `_normalize_transient_fields(parsed) -> dict`，實裝設計 D1 表格——年齡 `< 18`→18、`> 10000`→10000；`display_name`／`background` strip＋截斷（64／600）＋空轉缺席；`affinity_elements` 剔除未知元素、保序去重、依 `_AFFINITY_INPUT_BOUNDS[race_key]` 截斷、elf 強制 `()`；在語義驗證全數通過後（`guarded_call` 成功之後）呼叫，再構造 frozen dataclass。元素鍵 membership 以 `world.lore.elements.ELEMENT_REGISTRY` 核對（不得 import `world.rules`）。
- [x] 1.5 同檔：parity 測試常數——正規化界值與 `world/rules/creation_wizard.AGE_MINIMUM`／`AGE_MAXIMUM`、`world/rules/character_creation._AFFINITY_INPUT_BOUNDS` 一致性斷言（測試端 import 規則層，來源端仍零 import）。
- [x] 1.6 同檔：`build_race_catalog()` 每個種族條目追加「（親附上限：N）」（N 讀 `_AFFINITY_INPUT_BOUNDS`），並新增「元素鍵值：…」行（`ELEMENT_REGISTRY` 全鍵，提示詞契約要求）；確認 2000 字上限與截斷標記路徑不變。

## 2. 提示詞（prompts/）

- [x] 2.1 `prompts/character_creation.yaml`：契約 JSON 樣板增 `"display_name": "角色名字", "age": 0, "apparent_age": 0, "background": "精簡背景", "affinity_elements": ["元素鍵值"]`；刪「也不得替玩家決定年齡——年齡一律由玩家自己輸入」與「不得加入年齡欄位」兩句，並移除開頭「成年」措辭與「不得編造…背景」「不得在 persona 之外出現任何自由敘述」等會與新欄位矛盾的全面禁令（改寫為欄位範圍限定：persona 與 background 之外不得自由敘述）；增「affinity_elements 的數量不得超過所選種族標註的親附上限；精靈必須留空」「display_name 使用正體中文」「background 為精簡背景敘事，控制在 600 字以內」指示；「契約中不得出現上述欄位以外的任何鍵」改以十字段集合表述。確認提示詞模板（插值前）不含「18」「成年」字樣（渲染後 system 含玩家 concept，「18」檢查只能對模板做）。
- [x] 2.2 prompt library validate CLI 綠（入口沿用 prompt-library 規格 §validate CLI 條目）。

## 3. 測試與登記

- [x] 3.1 `world/ai/tests/`（概念層既有測試模組）：正規化矩陣案——年齡 17→18、10001→10000、18／10000 原樣；名字 65 cp→截 64、全空白→缺席；背景 601→截 600；affinity 未知鍵剔除、重複去重、beastfolk 給 2 截 1、elf 給非空清空、截後空集為中性 `()`；缺席五鍵 → dataclass 五欄全 `None`；結構性拒絕案（bool 年齡、非 list 親和、第十一個鍵）走重試路徑不進正規化。**既案改寫**：`test_age_field_is_rejected` → age=30 單次通過且 `proposal.age == 30`；`test_retry_exhaustion_degrades_within_the_budget` 的重複回應改用仍屬結構性無效的 payload（bool age 或第十一個鍵）維持三次呼叫降級斷言；`test_race_catalog_never_carries_mechanical_numbers` 改寫為數字只准出現在「（親附上限：N）」後綴且 N 對照映射。掛 `covers_requirement` 於改寫 requirement 的 canonical ID `generative-character-concept::proposals-are-validated-deterministically-against-the-registries`（新增 prompt requirement 的 ID 要到歸檔同步後才可掛，本輪不掛）。
- [x] 3.2 提示詞案：渲染後 system prompt 含五鍵樣板、無年齡禁令句；模板本體（yaml 原文）無「18」「成年」；`build_race_catalog()` 每個種族條目含親附上標註、含元素鍵值行、目錄總長在上限內。
- [x] 3.3 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai`。
- [x] 3.4 `uv run --locked python -m tools.spec_traceability check`；`openspec validate extend-concept-proposal-fields --strict`；`uv run --locked python -m tools.observability_lint check`。
