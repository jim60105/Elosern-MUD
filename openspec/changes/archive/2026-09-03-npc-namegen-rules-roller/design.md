# npc-namegen-rules-roller — Design

## Context

`npc-namegen-lore-registry`（前置 change，必須先落地）已在 `world/lore/names.py` import 時凍結 `NAME_PACK_REGISTRY`（五包：`fantasy-human`／`fantasy-elf`／`fantasy-dwarf`／`fantasy-orc`／`fantasy-halfling`，每包 `given` 恰 `m`／`f`／`u` 三池、池非空由 import 不變量 2 保證）與 `NAME_PACK_BY_RACE`（human／elf／beastfolk → 三包；dwarf／halfling `race_key=None` 不綁族），並提供 `NAME_SEPARATOR = "・"` 與 `compose_display_name(given, surname)`。本 change 實作其唯一的下游消費者——規則層擲名 `world/rules/namegen.py`，即設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §4。

分層契約：`rules/namegen` 只讀 `lore`，純函式、無 DB、無 Evennia import、不寫狀態。兩個接線消費端（`namegen-creation-ui` 的骰子、`namegen-npc-flow` 的靈感名＋兜底補名）屬後續 change；本 change 只交付函式本體與可直接單測的純介面。sex 詞彙為 `world/lore/sex.py::SEX_VALUES = ("female", "male", "other")`（`entity-sex-vocabulary` capability），本層以字串值消費、不改寫該模組。

## Goals / Non-Goals

**Goals:**
- `roll_name(pack_key, sex, rng)`：female→f、male→m、other→u 池優先、空字串／`None`→以 `rng` 隨機挑一池；輸出為 `compose_display_name` 合成的「名・姓」譯名。
- `roll_name_for_race(race_key, sex, rng)`：經 `NAME_PACK_BY_RACE` 解析；`None`／無映射→隨機挑一個有 `race_key` 綁定的包（dwarf／halfling 不參與兜底）。
- 錯誤語意：未知 `pack_key`→`KeyError` 不吞；過濾後池為空→退回該包全池，產生器絕不死掉。
- 可重放契約：同注入 `rng` 之狀態必得同名；測試以固定種子驗證全語意。

**Non-Goals:**
- RNG 策略的落地（UI 無種子 vs NPC crc32）——兩個消費端 change 各自持有；本層只吃注入的 `Random`。
- NPC 補名處的 `action_commit` 觀察性事件、`creation.roll_name` ui_action、性別下拉、前端回填。
- dwarf／halfling 綁族、多候選名 prompt、`meaning_zh` 展示。

## Decisions

### D1：RNG 一律由呼叫端注入；雙策略只寫進文件、不寫進本層
設計 §4 明文 RNG 來源分兩條、不共用：UI 骰用模組級無種子 `random.Random()`（擲出的名字進入 payload 後與手打名字同等待遇，無需重放）；NPC 側呼叫端自建 `Random(zlib.crc32(f"{definition.key}:{stage_index}:{role}".encode()))`（同藍圖重建必得同名 NPC）。兩條都住在消費端。`namegen.py` 內部永不構造 `Random`、不讀全域 RNG（不用 `random.choice` 模組函式），只用傳入 `rng` 的 `choice`——這是「可重放性由呼叫端種子保證」的機制面保證，也是函式可固定種子直測的前提。拒絕替代方案：模組級共享 `Random()` 讓 NPC 側自行 reseed（隱式全域狀態使 NPC/UI 兩條策略互相汙染種子序列）。

### D2：sex→池映射為常數表；無法辨識的值一視同仁走隨機池
`{"female": "f", "male": "m", "other": "u"}` 常數對映；空字串與 `None` 明文走「隨機挑一池」。設計 §4 未列「值不在 `SEX_VALUES` 內」的情境；本層選擇與未指定同處理（隨機池）而非拋錯，理由：(a) 設計 §8 的錯誤面只有 `KeyError`（包不存在）與空池退回兩條，擲名器自身「絕不死掉」；(b) sex 的合法性把關在各自入口（`creation.custom` validator、`read_sex` 型別正規化），規則層重複驗證只會創造第二個失敗模式。u 池「優先」在語料上由 lore 不變量 2（u 池恆非空）平凡滿足，但實作仍走 D3 的退回路徑，對手改語料的未來防呆。

### D3：空池退回＝該包全部 given 池（m、f、u 串接）；核心拆成吃 `NamePack` 的純 helper
「過濾後池為空→退回該包全池」的「全池」定義為 `given["m"] + given["f"] + given["u"]` 串接（姓氏池不受 sex 過濾、且由不變量 2 保證非空，無需退回路徑）。實作拆私有核心 `_roll_from_pack(pack: NamePack, sex: str, rng: Random) -> str`（選池→抽 given／surname→`compose_display_name`），公開 `roll_name` 只做 registry 查表後委派。理由：registry 是凍結常量，測試要觸及「空池退回」就得 patch `MappingProxyType` 裡的 entry；核心直接吃合成 `NamePack` 即可用「u 池為空的假包」直測，不需要任何 patch。同理 `_pick_pack_for_race(race_key, rng)` 回傳 `NamePack`。

### D4：隨機兜底的候選包＝`NAME_PACK_BY_RACE.values()` 排序後清單
候選取自映射值（種族綁定的唯一真相，與 registry 掃描等價——lore spec 已綁定「每個綁定包 `race_key` 等於其種族鍵」）再 `sorted()`，使 `rng.choice` 的索引基準與 mapping 的字面插入順序解耦：重放契約不因上游改寫 `NAME_PACK_BY_RACE` 的字面順序而漂移。dwarf／halfling 因不在映射值中而天然被排除，符合設計 §4「不參予隨機兜底」。

### D5：registry 於呼叫時查表；`KeyError` 原樣傳播
`roll_name` 以 `NAME_PACK_REGISTRY[pack_key]` 取包，不捕獲——`KeyError` 是程式內常量錯誤，吞掉會把錯包名字靜態送進玩家視野；讓呼叫端 traceback 直指來源。本模組以頂層 `from world.lore.names import ...` 綁定符號（與 repo 慣例一致）；由於 registry 是不可變凍結常量，測試的可測性不依賴 patch 模組屬性——空池退回以合成 `NamePack` 直呼 `_roll_from_pack`（D3），兜底候選集以記錄 `choice` 入參的注入式 RNG 直測 `_pick_pack_for_race`。

### D6：合成只經 lore 的 `compose_display_name`；本層零合成常量
分隔符 `・`（U+30FB）是 lore change D7 裁定的「registry 內唯一合成常量」；`namegen.py` 自帶分隔符或字串串接會分裂該契約。given 與 surname 皆為 `NamePart`，輸出天然不含 `text`。

### D7：測試為純 `unittest.TestCase`；新 test module 需顯式 shard label
驗證過 `.github/evennia-shards.json` 現況：`world.rules` 側三個 shard（rules-a／b／c）的 labels 全部是顯式模組名，**無** `world.rules` 或 `world.rules.tests` package label——不同於 lore change 的 `world.lore`（shard 4，package label 遞迴涵蓋）。故 `world.rules.tests.test_namegen` 必須顯式加入 manifest，否則 `tests.test_evennia_test_optimization_contract::test_evennia_shard_manifest_owns_every_non_browser_test_module_exactly_once` 的「每個 test module 恰一主」斷言必紅。依字母序落 shard 2（rules-b：介於 `test_movement_settlement` 與 `test_no_combat_branching` 之間）。

## Risks / Trade-offs

- [前置 change 未落地時 import 即 `AttributeError`] → 依賴順序寫進 proposal；本 change 的 CI 紅燈會直接指向缺失的 registry，屬正確的 fail-fast，不預先寫防呆。
- [無法辨識的 sex 值走隨機池，掩護了上游漏驗證] → 入口驗證（creation validator、`read_sex` 正規化）才是把關點；本契約由 spec scenario 明文，測試釘死死語意，不會無聲漂移。
- [`sorted()` 候選清單讓 NPC 兜底名與 mapping 字面順序無關，但與字母序綁死] → 上游若調整包名（未發布、零使用者下不太可能）會改寫所有兜底種子結果；重放契約只承諾「同程式版本＋同種子→同名」，跨版本不承諾。
- [`_roll_from_pack` 為私有、被測試直接呼叫，形同半公開面] → 接受：它是 spec 空池退回語意的最小可測單位；公開 API 仍是 `roll_name`／`roll_name_for_race` 兩條。

## Open Questions

（無。sex 映射、退回池定義、兜底候選集、shard 落點均已核定。）
