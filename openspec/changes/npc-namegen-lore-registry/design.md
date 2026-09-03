# npc-namegen-lore-registry — Design

## Context

`third_party/fantasy-namegen/` 已 vendor 完毕：`data/packs/` 五個 pack JSON（fantasy-human／elf／dwarf／orc／halfling，共 1,274 個零件，每包 `surnames: [{s, meaning}]`、`given: {m|f|u: [{g, meaning, note?}]}`、`rules.naming.note`）、`data/translit/fantasy.json`（原文→正體中文對照，對現況全部零件零缺漏）、`data/regions/fantasy.json`。上游為 CC BY 4.0，僅手動重抓。

本 change 只落地語料層：把上述 JSON 在 `world/lore/names.py` import 時解析、驗證、凍結成 registry 常量，並接上既有 lore 啟動鏡接管線。唯一真相為 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §3；規則層（`world/rules/namegen.py`）、創建骰子、NPC 補名屬後續 change。

分層現況：`world/lore/` 純資料模組、頂層不依賴 rules（`titles.py` 對 rules 的引用採驗證函式內延遲 import）；`world/rules/character_creation.py` 頂層 import lore。鏡射側 `world/lore/sync.py::sync_all()` 以 `dataclasses.asdict` ＋ `_db_safe` 把 `_ALL_REGISTRIES` 每個 entry 寫進 `LoreRecord` Script。

## Goals / Non-Goals

**Goals:**
- `NAME_PACK_REGISTRY`（五包）與 `NAME_PACK_BY_RACE`（三族綁定）在 module import 時完成解析與凍結，import 即完成、來源即真相。
- 三條 import 時不變量 fail-fast：translit 全覆蓋、池非空＋映射合法、最長合成名過 `_validate_name`。
- `・`（U+30FB）合成常量與「名・姓」helper 收在此層，玩家可見輸出只含譯名。
- 經 `sync_all()` 冪等鏡射，啟動鏡接管線不斷鏈。

**Non-Goals:**
- 擲名規則（sex→池映射、RNG 策略、`roll_name*`）——後續 rules 層 change。
- dwarf／halfling 兩包的消費端、`meaning_zh` 進 lore codex、上游自動同步、前端／命令面任何變動。

## Decisions

### D1：import 時解析＋凍結，而非執行期載入或 DB-first
與 `RACE_REGISTRY` 同契約：module import 以純函式讀七檔 JSON，建構 frozen dataclass 後以 `MappingProxyType` 包住兩個頂層常量（`NAME_PACK_REGISTRY`、`NAME_PACK_BY_RACE`）。204 KB 七檔的 import 成本可忽略；執行期載入會把缺詞／錯映射推成第一次擲名才炸的執行期故障，違反 fail-fast 意圖。

### D2：dataclass 形狀照設計 §3；巢狀 `given` 的執行期值為 plain dict
`NamePart(text, zh, meaning_zh)`、`NamePack(key, race_key, surnames: tuple[NamePart, ...], given: Mapping[str, tuple[NamePart, ...]], naming_note_zh)` 皆 `@dataclass(frozen=True)`；`given` 的鍵恆為 `m`／`f`／`u`。巢狀 `given` 的宣告型別為 `Mapping`，但執行期值必須是 plain `dict` 而非 `MappingProxyType`：鏡射路徑 `sync.py::sync_one` 走 `dataclasses.asdict()`，`asdict` 對非 dataclass／list／tuple 欄位做 `copy.deepcopy`，而 mappingproxy 無法被 pickle／deepcopy（實測 `TypeError: cannot pickle 'mappingproxy' object`）。先例同形：`Subrace.vital_overrides` 宣告 `dict | None`、registry 凍結在頂層 `MappingProxyType`（`npc_tiers.py`、`scene_archetypes.py`、`titles.py` 亦只凍頂層）。凍結契約由頂層 constant 與 frozen dataclass 承擔。
`naming_note_zh` 取 pack JSON 的 `rules.naming.note`；`meaning_zh` 取零件的 `meaning`（缺失時空字串，MVP 不顯示）。

### D3：種族綁定 human→fantasy-human、elf→fantasy-elf、beastfolk→fantasy-orc
對上 `RACE_REGISTRY` 現有三族；粗嚳音韻以 orc 包最接近獸人系。`fantasy-dwarf`／`fantasy-halfling` 入 registry 但 `race_key=None`，不出現在 `NAME_PACK_BY_RACE`——留給未來新族，且不參與隨機兜底（該篩選屬 rules 層 change 的責任，本層只如實承載 `race_key`）。

### D4：不變量在 module import 尾部驗證，違反丟具名例外
驗證函式於 import 時執行（同 `wilderness_entry.validate_wilderness_entries` 的 all-or-nothing 精神，但提前到 import：不合法語料連 registry 都不該被拿到）。缺詞例外訊息帶缺詞清單；池為空／映射指向未註冊包／最長合成名過不了驗證器 likewise fail-fast。拒絕替代方案：只在 `sync_all()` 驗證——rules 層 import 讀 registry 會繞過 DB 鏡射，缺口必須在 import 面攔截。

### D5：不變量 3 延遲 import 真驗證器，不改寫、不複製規則
`world/rules/character_creation.py::_validate_name`（1..`MAX_ENTITY_KEY_LENGTH`=64 字元、無控制字元、無 `|{} /:`）是本 change 的接受閘門；名字「最長組合」取全包 `max(len(given.zh) + 1 + len(surname.zh))` 的實際字串逐一送验。驗證器住在 rules 且 rules 頂層 import lore，故 `names.py` 在驗證 helper 內函數級 `from world.rules.character_creation import _validate_name`——先例：`world/lore/titles.py` 驗證函式內延遲 import `world.rules.*`。複製驗證邏輯进 lore 會被 `_validate_name` 單方演進甩開（drift），被拒。延遲 import 觸發點仍在 module import（驗證於 import 尾部執行），Evennia 載入順序下 Django 設定已就緒，`from django.db import transaction` 於 import 期不連線、不查庫。

### D6：進啟動鏡接管線，category `"name_packs"`
判讀：`lore-startup-sync` 首條 requirement 明文框定「該 change 定義的十個 registry」，並非「所有 lore registry 一律鏡射」的通用條款；repo 的慣例是每个新 registry 由自己的 capability spec 以 ADDED requirement 宣告鏡射並加入 `_ALL_REGISTRIES`（`anchor-placement`、`wilderness-terrain`、`wilderness-gateway`、`title-system` 皆如此），且各自以 scenario 斷言 lore-startup-sync 原文不動。源設計 §3 亦明載「啟動同步沿用既有 lore 鏡接管線，保持冪等」。故 `sync.py::_ALL_REGISTRIES` 增 `"name_packs": NAME_PACK_REGISTRY` 一列，產生 `lore:name_packs:fantasy-human` 等五筆 `LoreRecord`；`lore-startup-sync` 與 `lore-registries` 兩個 main spec 均不需 MODIFIED delta（前者列舉綁定原十registry，後者各 requirement 綁定具體模組，新 registry 不觸犯任何既有條款）。

### D7：合成常量與 helper 放 lore 層
`NAME_SEPARATOR = "・"`（U+30FB）為 registry 內唯一合成常量；`compose_display_name(given: NamePart, surname: NamePart) -> str` 回傳 `f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`。合成屬資料形態（顯示名的定義）而非規則（選誰），放 rules 層會迫使 rules 自帶分隔符常量、與「registry 內唯一合成常量」的契約分裂。`NamePart.text` 永不進入 helper 輸出。

## Risks / Trade-offs

- [上游手動重抓引入 translit 缺詞] → 不變量 1 於 import 即炸並列缺詞清單；執行期永不发生（測試以 patch 缺詞語料重跑驗證器路徑斷言）。
- [上游新成長詞使最長「名・姓」逼近 64 字元上限] → 不變量 3 同樣 import 即炸；現況最長組合遠低於上限。
- [mappingproxy deepcopy 陷阱讓鏡射在 CI 才炸] → D2 明文 `given` 用 plain dict，鏡射斷言（`db.fields` 比對）收進 Evennia 級測試。
- [延遲 import `_validate_name` 讓 lore/names 間接拖入 rules→django 依賴鏈] → 僅驗證路徑一次、於 import 尾部；若未來 rules 層出現循環，退路是把 `_validate_name` 降為 rules→lore 單向注入（呼叫端注入），本 change 不做。
- [`world.lore` shard label 以目錄遞迴涵蓋新 test module，若 manifest 誤加顯式 label 會造成雙主] → 以 `tests.test_evennia_test_optimization_contract` 的 ownership contract 為準，任務只驗證不重複註冊。

## Open Questions

（無。種族映射、分隔符、鏡射 category 均已由源設計核定。）
