# extend-concept-proposal-fields — Tasks

實作順序即分組順序：契約層（schema／驗證／正規化）→ 提示詞 → 測試與登記。每組做完先跑該組 focused 測試再勾選；不跑 CI shard 指令。

## 1. 提案契約與正規化（world/ai）

- [ ] 1.1 `world/ai/character_creation.py`：`CharacterProposal` 增五個 optional 欄位（`display_name: str | None`、`age: int | None`、`apparent_age: int | None`、`background: str | None`、`affinity_elements: tuple[str, ...] | None`，預設 `None`），docstring 改寫缺席語義（缺席＝消費端維持本地預設）。新增本地界值常數鏡像（`ADULT_AGE_MINIMUM = 18`、`AGE_MAXIMUM_BOUND = 10000`、`MAX_DISPLAY_NAME_CODE_POINTS = 64`、`_AFFINITY_INPUT_BOUNDS = {"human": 2, "beastfolk": 1, "elf": 0}`），模組頂註解註明 transport-boundary 鏡像先例（`ALLOCATABLE_AXES`）。
- [ ] 1.2 同檔：`CHARACTER_CREATION_OUTPUT_SCHEMA.properties` 增五鍵（`display_name`／`background` 為 string、`age`／`apparent_age` 為 integer、`affinity_elements` 為 `array<string>`），全部 optional（不入 `required`）——型別錯誤由 jsonschema 走重試路徑。
- [ ] 1.3 同檔：`_validate_shape` 的允許鍵集合擴為十字段，錯誤訊息措辭改寫（刪「no age, no other numbers」句，改為僅十字段白名單表述）。
- [ ] 1.4 同檔：新增 `_normalize_transient_fields(parsed, race_key) -> dict`，實裝設計 D1 表格——年齡 `< 18`→18、`> 10000`→10000；`display_name`／`background` strip＋截斷（64／600）＋空轉缺席；`affinity_elements` 剔除未知元素、保序去重、依 `_AFFINITY_INPUT_BOUNDS[race_key]` 截斷、elf 強制 `()`；在語義驗證全數通過後呼叫，再構造 frozen dataclass。元素鍵 membership 以 `world.lore` 既有元素 registry 來源核對（不得 import `world.rules`）。
- [ ] 1.5 同檔：parity 測試常數——正規化界值與 `world/rules/creation_wizard.AGE_MINIMUM`／`AGE_MAXIMUM`、`world/rules/character_creation._AFFINITY_INPUT_BOUNDS` 一致性斷言（測試端 import 規則層，來源端仍零 import）。
- [ ] 1.6 同檔：`build_race_catalog()` 每個種族條目追加「（親附上限：N）」（N 讀 `_AFFINITY_INPUT_BOUNDS`）；確認 2000 字上限與截斷標記路徑不變。

## 2. 提示詞（prompts/）

- [ ] 2.1 `prompts/character_creation.yaml`：契約 JSON 樣板增 `"display_name": "角色名字", "age": 0, "apparent_age": 0, "background": "精簡背景", "affinity_elements": ["元素鍵值"]`；刪「也不得替玩家決定年齡——年齡一律由玩家自己輸入」與「不得加入年齡欄位」兩句；增「affinity_elements 的數量不得超過所選種族標註的親附上限；精靈必須留空」「display_name 使用正體中文」「background 為精簡背景敘事，控制在 600 字以內」指示；「契約中不得出現上述欄位以外的任何鍵」改以十字段集合表述。確認渲染後 prompt 不含「18」「成年」字樣。
- [ ] 2.2 prompt library validate CLI 綠（入口沿用 prompt-library 規格 §validate CLI 條目）。

## 3. 測試與登記

- [ ] 3.1 `world/ai/tests/`（概念層既有測試模組）：正規化矩陣案——年齡 17→18、10001→10000、18／10000 原樣；名字 65 cp→截 64、全空白→缺席；背景 601→截 600；affinity 未知鍵剔除、重複去重、beastfolk 給 2 截 1、elf 給非空清空、截後空集為中性 `()`；缺席五鍵 → dataclass 五欄全 `None`；結構性拒絕案（bool 年齡、非 list 親和、第十一個鍵）走重試路徑不進正規化。掛 `covers_requirement` 於 `generative-character-concept` 兩條改寫 requirement 的 canonical ID（先跑 `uv run --locked python -m tools.spec_traceability list` 取 ID）。
- [ ] 3.2 提示詞案：渲染後 system prompt 含五鍵樣板、無年齡禁令句、無成年字樣；`build_race_catalog()` 每個種族條目含親附上標註、目錄總長在上限內。
- [ ] 3.3 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai`。
- [ ] 3.4 `uv run --locked python -m tools.spec_traceability check`；`openspec validate extend-concept-proposal-fields --strict`；`uv run --locked python -m tools.observability_lint check`。
