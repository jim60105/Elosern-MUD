# npc-namegen-rules-roller — Tasks

前置條件：`npc-namegen-lore-registry` 已實作落地（`world/lore/names.py` 的 `NAME_PACK_REGISTRY`／`NAME_PACK_BY_RACE`／`NAME_SEPARATOR`／`compose_display_name`／`NamePart`／`NamePack` 皆可 import）。實作順序即分組順序：模組 → 測試 → 登記與收尾。每組做完先跑該組 focused 驗證再勾選；全程不跑 CI shard 指令。

## 1. 規則層模組 `world/rules/namegen.py`

- [ ] 1.1 建立純函式模組：只用標準函式庫（`random.Random` 型別引用、必要時 `collections.abc`），無 DB、無 Evennia import、無 module-level `Random()` 執行個體、不用 `random` 模組級函式； randomness 唯一來源是傳入的 `rng` 參數（設計 D1）。頂層 import 只取 `world.lore.names` 的 `NAME_PACK_REGISTRY`、`NAME_PACK_BY_RACE`、`compose_display_name`、`NamePack`（不 import `NAME_SEPARATOR`、不自帶分隔符常量，設計 D6）。
- [ ] 1.2 定義 sex→池常數表 `{"female": "f", "male": "m", "other": "u"}`，並定義「空字串／`None`／表外值 → 以 `rng.choice(["m","f","u"])` 隨機挑池」的正規化 helper（設計 D2：表外值與未指定同處理，本層不拋錯、不驗證 `SEX_VALUES`）。
- [ ] 1.3 實作私有核心 `_roll_from_pack(pack: NamePack, sex: str | None, rng: Random) -> str`：選池→若該池為空則退回 `given["m"] + given["f"] + given["u"]` 串接（設計 D3）→ `rng.choice` 抽 given 與 surname → 回傳 `compose_display_name(given, surname)`。核心吃 `NamePack` 值而非 pack_key，讓空池退回可用合成包直測、免 patch 凍結 registry。
- [ ] 1.4 實作 `roll_name(pack_key: str, sex: str | None, rng: Random) -> str`：呼叫時以 `NAME_PACK_REGISTRY[pack_key]` 查表（模組屬性延遲解析，設計 D5），不捕獲例外——未知 `pack_key` 原樣拋 `KeyError`——再委派 `_roll_from_pack`。
- [ ] 1.5 實作 `_pick_pack_for_race(race_key: str | None, rng: Random) -> NamePack`：`race_key` 有映射→`NAME_PACK_REGISTRY[NAME_PACK_BY_RACE[race_key]]`；`None`／無映射→`rng.choice(sorted(NAME_PACK_BY_RACE.values()))` 對應的包（排序使索引基準與 mapping 字面順序解耦，dwarf／halfling 天然被排除，設計 D4）。
- [ ] 1.6 實作 `roll_name_for_race(race_key: str | None, sex: str | None, rng: Random) -> str` = `_roll_from_pack(_pick_pack_for_race(race_key, rng), sex, rng)`。
- [ ] 1.7 導出 `__all__ = ["roll_name", "roll_name_for_race"]`；私有 helper 不導出但可被同包測試直接 import。

## 2. 測試 `world/rules/tests/test_namegen.py`（`unittest.TestCase`，pure logic，不用 EvenniaTest）

- [ ] 2.1 固定種子重放案：對 `Random(42)` 各建兩份，`roll_name`（五包 × sex `female`／`male`／`other`／`""`／`None` 抽樣）與 `roll_name_for_race`（三族＋`None`＋未知族）逐一雙呼，斷言每對結果字串相同。掛 `@covers_requirement("npc-name-generation::rolling-is-a-pure-function-of-the-injected-rng-for-replayability")`（先跑 `uv run --locked python -m tools.spec_traceability list` 確認四條 canonical ID，以下各案同）。
- [ ] 2.2 sex→池映射案：對 `fantasy-human` 以固定種子多次擲，斷言 `female`→given 的 `zh` 恆落 `given["f"]`、`male`→`"m"`、`other`→`"u"`（u 池優先）；`""`／`None` 的 given 落三池并集且同種子可重放；輸出形如 `X・Y`（U+30FB）且兩段皆可在該包池的 `zh` 中找到、不含任何零件 `text`。掛 `@covers_requirement("npc-name-generation::roll-name-maps-sex-to-the-given-pool-of-a-pack-and-composes-the-chinese-display-name")`。
- [ ] 2.3 種族解析＋隨機兜底案：三族各擲 → given／surname 只落其綁包池；`None`／`"dragonborn"` 遍歷足量種子 → 結果包恆屬 `{fantasy-human, fantasy-elf, fantasy-orc}`，斷言 `fantasy-dwarf`／`fantasy-halfling` 的獨有零件 `zh` 從不出現。掛 `@covers_requirement("npc-name-generation::roll-name-for-race-resolves-via-name-pack-by-race-with-a-bound-packs-only-random-fallback")`。
- [ ] 2.4 KeyError 案：`roll_name("fantasy-dragonkin", "female", Random(1))` 以 `assertRaises(KeyError)` 斷言且 `str(exc)` 含該 key，無名字回傳。掛 `@covers_requirement("npc-name-generation::unknown-pack-keys-raise-keyerror-and-empty-filtered-pools-fall-back-to-the-full-given-pool")`。
- [ ] 2.5 空池退回案：以 `NamePack` 直建合成包（`u` 池為 `()`、`m`／`f` 非空），直呼 `_roll_from_pack(synthetic, "other", rng)` → 斷言 given 落 `m ∪ f`、回傳合法合成名不擲；同包 sex `"female"` 正常路徑不受影響。掛同 2.4 requirement ID。
- [ ] 2.6 無全域 RNG 案：靜態斷言 `world.rules.namegen` 模組內無 `Random()` 實例化、無對 `random` 模組級 `choice`／`randint` 的呼叫（可 `inspect.getsource` 掃描或 patch `random.Random` 構造器斷言零呼叫）；兩次同種子呼叫間不互相消耗狀態。掛 2.1 requirement ID。
- [ ] 2.7 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_namegen`。

## 3. 登記與收尾

- [ ] 3.1 Shard 歸屬：已查 `.github/evennia-shards.json`——`world.rules` 側三個 shard（rules-a／b／c）全用顯式模組 label，無 package label 可遞迴涵蓋（與 lore change 的 `world.lore` 情境相反），故須顯式註冊。在 shard 2（`rules-b`）labels 依字母序插入 `"world.rules.tests.test_namegen"`（`test_movement_settlement` 與 `test_no_combat_branching` 之間）。跑 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` 驗證「恰一主」。
- [ ] 3.2 `uv run --locked python -m tools.spec_traceability check`（四條 requirement 全覆蓋、零錯誤）。
- [ ] 3.3 `openspec validate npc-namegen-rules-roller --strict`；確認 `docs/game/commands.md`、前端／wire、`world/lore/`、`world/ai/` 零變動（本 change 無命令面、無狀態寫入）。
- [ ] 3.4 終局驗證：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 1 world.rules.tests.test_namegen world.rules.tests.test_character_creation`（新擲名＋被 lore 不變量 3 綁定的名字驗證器回歸）。
