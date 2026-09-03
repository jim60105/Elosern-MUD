# npc-namegen-lore-registry — Tasks

實作順序即分組順序：registry 模組 → 鏡接管線／映像烘焙 → 測試 → 登記與收尾。每組做完先跑該組 focused 驗證再勾選；全程不跑 CI shard 指令。

## 1. 語料層模組 `world/lore/names.py`

- [x] 1.1 定義 frozen `NamePart`（`text`／`zh`／`meaning_zh`）與 frozen `NamePack`（`key`、`race_key: str | None`、`surnames: tuple[NamePart, ...]`、`given`（宣告 `Mapping[str, tuple[NamePart, ...]]`，執行期 `FrozenDict`（拒 mutate 的 concrete dict subclass），鍵恰 `m`／`f`／`u`）、`naming_note_zh`），與設計 D2／spec 欄位一一對應；`meaning` 缺失的零件 `meaning_zh` 為空字串。
- [x] 1.2 以純函式解析 `third_party/fantasy-namegen/data/packs/` 五檔與 `data/translit/fantasy.json`：`surnames[].s`／`given[m|f|u][].g` 為零件原文，`meaning` 為註解，`zh` 查 translit；`naming_note_zh` 取 `rules.naming.note`。
- [x] 1.3 import 尾部三不變量驗證（違反丟具名例外、不留半成品綁定）：載入／驗證收在純函式 `_build_registry(pack_payloads, translit, race_bindings)`（設計 D9，binding 顯式傳參以便注入壞語料測試）。(1) 包集合恰五鍵＋translit 全覆蓋，例外訊息列缺詞清單；(2) 每包 `surnames` 非空、m／f／u 池恰存在且非空、binding 鍵屬 `RACE_REGISTRY` 且值為已註冊包；(3) 每包代表最長組合（池內最長 `given.zh` ＋ `NAME_SEPARATOR` ＋ 最長 `surname.zh`）過 `_validate_name`，驗證器以驗證 helper 內函數級 `from world.rules.character_creation import _validate_name` 延遲 import（先例 `world/lore/titles.py`；本模組 settings-required，見設計 D5 實測修正）。`NAME_SEPARATOR` 定義在任何組合驗證之前、registry 建構在模組尾。
- [x] 1.4 暴露頂層凍結常量：`NAME_PACK_REGISTRY = MappingProxyType(...)`（五包）、`NAME_PACK_BY_RACE = MappingProxyType({"human": "fantasy-human", "elf": "fantasy-elf", "beastfolk": "fantasy-orc"})`；`fantasy-dwarf`／`fantasy-halfling` 的 `race_key=None` 且不進映射。
- [x] 1.5 合成常量與 helper：`NAME_SEPARATOR = "・"`（U+30FB）、`compose_display_name(given, surname) -> f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`；輸出只含 `zh` 欄與分隔符。

## 2. 啟動鏡接管線與映像烘焙

- [x] 2.1 `world/lore/sync.py`：`_ALL_REGISTRIES` 增 `"name_packs": NAME_PACK_REGISTRY` 一列（import 自 `.names`）。確認 `NamePack.given` 為 `FrozenDict`（concrete dict 使 `asdict` deepcopy 可過、`__reduce__` 保型別，設計 D2）；不動 `_db_safe`／`sync_one`／`sync_all` 其餘邏輯，`lore-startup-sync` main spec 原文不動。
- [x] 2.2 `Containerfile` app-layout stage 增 `COPY --chown=root:0 third_party/ /app/third_party/`（設計 D8：`names.py` import 讀語料，映像必須烘焙）；`.containerignore` 維持不排除 `third_party/`。

## 3. 測試 `world/lore/tests/test_names.py`

- [x] 3.1 `unittest.TestCase` pure-logic 案：五鍵恰清單＋`MappingProxyType` 型別＋每包 `given` 恰 m/f/u 且執行期為 `FrozenDict`；另加凍結案：`given` 的 setitem/clear/pop/setdefault 全丟 `TypeError`、`_db_safe(asdict(...))` 鏡射值為相等 plain dict、deepcopy 經 `__reduce__` 重建型別；覆蓋斷言採精確語意——逐 pack、逐 `surnames`／`given[m|f|u]` 來源陣列，registry 內容與 vendored pack JSON 對應陣列逐項等長度、等順序（`NamePart` 全欄位相等），registry occurrence 總數＝1,274；明示不要求 `NamePart.text` 全域唯一（translit 1,261 distinct＜1,274 即因合法重複拼寫，各 occurrence 各自成一個 `NamePart`）；`zh` 非空且等於 translit 對照、且不含 ASCII 字母；三族綁定恰三條且值皆已註冊、dwarf／halfling `race_key is None` 且不在映射值中；每包 `surnames` 與三池皆非空；`_ALL_REGISTRIES["name_packs"] is NAME_PACK_REGISTRY`。
- [x] 3.2 不變量 fail-fast 案：呼叫 `_build_registry`（純函式、三樣輸入全 dict 注入）斷言各 reject 路徑皆具名例外——缺 translit 詞（訊息含全部缺詞）、包集合缺／多、空 `surnames`／空池、表外 race 鍵、未註冊包目標、過長 `zh` 合成（經 builder 而非直調驗證器，證明 import 尾真的呼叫每條不變量）。正向案：真實語料每包代表最長組合送 `_validate_name` 斷言不擲。
- [x] 3.3 合成格式案：`NAME_SEPARATOR == "・"`（U+30FB）；`compose_display_name` 對「加斯帕」+「斯諾」斷言「加斯帕・斯諾」（該對是設計文件的示意名、非真實語料零件，以合成 `NamePart` 輸入）；fantasy-human 全包配對抽樣斷言格式＝`given.zh＋・＋surname.zh`、結果不含任何 ASCII 零件 `text`。
- [x] 3.4 鏡射案（同模組 `EvenniaTestCase`，仿 `test_sync.py::test_anchor_placements_record_is_mirrored_and_idempotent`）：`sync_all()` 後五筆 `lore:name_packs:<key>` Script 各恰一筆、`db.category == "name_packs"`、`db.fields == _db_safe(asdict(entry))`（含巢狀 given）；二次 `sync_all()` 無重複、同 id、內容不變。
- [x] 3.5 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_names`。
- [x] 3.6 容器烘焙契約：`tests/test_container_contract.py` 加靜態斷言（app-layout 含 corpus COPY、`.containerignore` 無 `third_party` 樣式）；focused `tests.test_container_contract`。

## 4. 登記與收尾

- [x] 4.1 Shard 歸屬：新模組經 shard 4（`quests-skills-art-ai-onboarding-lore`）的 `world.lore` package label 遞迴涵蓋；跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` 驗證恰好一主——僅當 contract 要求顯式 label 時才改 `.github/evennia-shards.json`，否則不動 manifest。
- [x] 4.2 `uv run --locked python -m tools.spec_traceability check` 維持綠燈且不變（1195 covered／0 uncovered／0 errors）——本 change 刻意不掛 `@covers_requirement`：delta ID 未進 main index，提前標註是 unknown-requirement-id 錯誤（先例 movement-settlement-atomicity 4.1）。
- [x] 4.3 `openspec validate npc-namegen-lore-registry --strict`；確認 `docs/game/commands.md` 與前端／wire 零變動（本 change 無命令面）。

## Post-sync traceability（archive sync 時執行，不在本 change 實作期）

- [ ] P1 delta sync 進 `openspec/specs/namegen-corpus-registry/spec.md` 後，以 `uv run --locked python -m tools.spec_traceability list` 取六條 canonical ID，依對應關係標註既有測試：registry 凍結＋覆蓋＋zh 渲染 → `test_names.py` 對應 pure 案；種族綁定 → binding 案；三不變量 → fail-fast 案（含 injected-invalid 案）；`・` 合成 → 合成格式案；鏡射 → `NamePackMirrorTests`；映像烘焙 → `test_container_contract.py::test_vendored_name_corpus_is_baked_into_the_runtime_image`。
- [ ] P2 `tools.spec_traceability check` 六條全覆蓋、零錯誤。
