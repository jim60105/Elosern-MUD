# npc-namegen-lore-registry — Tasks

實作順序即分組順序：registry 模組 → 鏡接管線 → 測試 → 登記與收尾。每組做完先跑該組 focused 驗證再勾選；全程不跑 CI shard 指令。

## 1. 語料層模組 `world/lore/names.py`

- [ ] 1.1 定義 frozen `NamePart`（`text`／`zh`／`meaning_zh`）與 frozen `NamePack`（`key`、`race_key: str | None`、`surnames: tuple[NamePart, ...]`、`given`（宣告 `Mapping[str, tuple[NamePart, ...]]`，執行期 plain dict，鍵恰 `m`／`f`／`u`）、`naming_note_zh`），與設計 D2／spec 欄位一一對應；`meaning` 缺失的零件 `meaning_zh` 為空字串。
- [ ] 1.2 以純函式解析 `third_party/fantasy-namegen/data/packs/` 五檔與 `data/translit/fantasy.json`：`surnames[].s`／`given[m|f|u][].g` 為零件原文，`meaning` 為註解，`zh` 查 translit；`naming_note_zh` 取 `rules.naming.note`。
- [ ] 1.3 import 尾部三不變量驗證（違反丟具名例外、不留半成品綁定）：(1) translit 全覆蓋，例外訊息列缺詞清單；(2) 每包 `surnames` 非空且 m／f／u 池非空＋`NAME_PACK_BY_RACE` 值皆為已註冊包；(3) 全包最長 `given.zh + "・" + surname.zh` 字串逐一過 `_validate_name`，驗證器以驗證 helper 內函數級 `from world.rules.character_creation import _validate_name` 延遲 import（先例 `world/lore/titles.py`）。
- [ ] 1.4 暴露頂層凍結常量：`NAME_PACK_REGISTRY = MappingProxyType(...)`（五包）、`NAME_PACK_BY_RACE = MappingProxyType({"human": "fantasy-human", "elf": "fantasy-elf", "beastfolk": "fantasy-orc"})`；`fantasy-dwarf`／`fantasy-halfling` 的 `race_key=None` 且不進映射。
- [ ] 1.5 合成常量與 helper：`NAME_SEPARATOR = "・"`（U+30FB）、`compose_display_name(given, surname) -> f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`；輸出只含 `zh` 欄與分隔符。

## 2. 啟動鏡接管線

- [ ] 2.1 `world/lore/sync.py`：`_ALL_REGISTRIES` 增 `"name_packs": NAME_PACK_REGISTRY` 一列（import 自 `.names`）。確認 `NamePack.given` 為 plain dict 使 `asdict` deepcopy 可過（mappingproxy 不可 deepcopy，設計 D2）；不動 `_db_safe`／`sync_one`／`sync_all` 其餘邏輯，`lore-startup-sync` main spec 原文不動。

## 3. 測試 `world/lore/tests/test_names.py`

- [ ] 3.1 `unittest.TestCase` pure-logic 案：五鍵恰清單＋`MappingProxyType` 型別＋每包 `given` 恰 m/f/u；覆蓋斷言採精確語意——逐 pack、逐 `surnames`／`given[m|f|u]` 來源陣列，registry 內容與 vendored pack JSON 對應陣列逐項等長度、等順序，registry occurrence 總數＝1,274；明示不要求 `NamePart.text` 全域唯一（translit 1,261 distinct＜1,274 即因合法重複拼寫，各 occurrence 各自成一個 `NamePart`）；`zh` 非空且等於 translit 對照、且不含 ASCII 字母；三族綁定恰三條且值皆已註冊、dwarf／halfling `race_key is None` 且不在映射值中；每包 `surnames` 與三池皆非空。掛 `@covers_requirement("namegen-corpus-registry::name-pack-registry-freezes-the-vendored-corpus-at-import-time", "namegen-corpus-registry::race-binding-maps-the-three-playable-races-and-leaves-the-spare-packs-unbound", "namegen-corpus-registry::registry-load-enforces-the-corpus-invariants-at-import-time")`（先跑 `uv run --locked python -m tools.spec_traceability list` 確認 canonical ID）。
- [ ] 3.2 不變量 fail-fast 案：呼叫暴露的載入／驗證 helper（純函式、吃路徑或 dict 注入）以缺 translit 詞的語料斷言具名例外且訊息含缺詞；空池語料 likewise。最長合成名案：對全部 pack 取 `max(len(given.zh) + 1 + len(surname.zh))` 的實際字串送 `_validate_name` 斷言不擲。掛不變量 requirement ID。
- [ ] 3.3 合成格式案：`NAME_SEPARATOR == "・"`（U+30FB）；`compose_display_name` 對已知對（「加斯帕」+「斯諾」→「加斯帕・斯諾」）與全包配對抽樣斷言格式＝`given.zh＋・＋surname.zh`、結果不含任何零件 `text`。掛 `@covers_requirement("namegen-corpus-registry::display-names-compose-from-chinese-renderings-with-the-middle-dot-separator")`。
- [ ] 3.4 鏡射案（同模組 `EvenniaTestCase`，仿 `test_sync.py::test_anchor_placements_record_is_mirrored_and_idempotent`）：`sync_all()` 後五筆 `lore:name_packs:<key>` Script 各恰一筆、`db.category == "name_packs"`、`db.fields == _db_safe(asdict(entry))`（含巢狀 given）；二次 `sync_all()` 無重複、內容不變。掛 `@covers_requirement("namegen-corpus-registry::name-pack-registry-is-mirrored-into-lorerecord-scripts-idempotently")`。
- [ ] 3.5 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_names`。

## 4. 登記與收尾

- [ ] 4.1 Shard 歸屬：新模組經 shard 4（`quests-skills-art-ai-onboarding-lore`）的 `world.lore` package label 遞迴涵蓋；跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` 驗證恰好一主——僅當 contract 要求顯式 label 時才改 `.github/evennia-shards.json`，否則不動 manifest。
- [ ] 4.2 `uv run --locked python -m tools.spec_traceability check`（五條 requirement 全覆蓋、零錯誤）。
- [ ] 4.3 `openspec validate npc-namegen-lore-registry --strict`；確認 `docs/game/commands.md` 與前端／wire 零變動（本 change 無命令面）。
