# NPC 姓名產生器設計（NPC Name Generation Design）

日期：2026-09-03
狀態：已核准（待實作）

## 1. 問題陳述

遊戲目前沒有系統化的姓名來源。角色創建的自訂表单要求玩家自己想名字；
NPC 側只有 `BlueprintNpcReq.display_name` 這個選填欄位，LLM 沒填時名字就缺失，
離線模板路徑僅有一個硬編碼的「黑鬍」。後果是 LLM 離線時 NPC 無名可用，
在線時名字風格又完全依賴模型自由發揮。

本設計以已 vendor 化的 CC BY 4.0 語料（`third_party/fantasy-namegen/`，
上游 <https://inknomu.com/namegen/fantasy>，174 個姓氏、1,100 個名字、
1,261 筆中文譯名對照）為基礎，建立確定性的姓名產生器，供兩個消費端使用：

1. 角色創建 UI 自訂表单姓名欄旁的骰子按鈕。
2. NPC 生成流程（LLM 靈感來源＋離線兜底補名）。

## 2. 決策摘要

| 決策 | 選擇 | 理由 |
|---|---|---|
| 語料承載 | `world/lore/names.py` module-level 凍結 registry，import 時解析 vendored JSON | 與 `RACE_REGISTRY` 同契約（來源即真相、import 即完成）；204 KB 七檔，import 成本可忽略 |
| 種族映射 | human→human 包、elf→elf 包、beastfolk→orc 包；dwarf／halfling 入 registry 但不綁族 | 三包對上現有 `RACE_REGISTRY` 三族；粗嚳音韻以 orc 包最接近兽人系；兩包留給未來新族 |
| 顯示名形式 | 純正體中文譯名（「加斯帕・斯諾」），經 translit 表組成 | 已驗證 translit 表對全部 1,274 個零件零缺漏、全部單詞無需拆詞；中文世界觀一致 |
| 骰子語料位置 | 伺服器端，走 OOB `ui_action` 往返 | SPA 維持 view-layer only；語料只在伺服器一份，不進前端 bundle |
| 骰子上下文 | 讀表單的種族與性別欄 | 行為直覺，且與 NPC 側共用同一規則函式 |
| 性別欄位 | 自訂表单新增「性別」下拉（女性／男性／其他），隨 payload 持久化到 `entity.sex` | `SEX_VALUES` registry 已存在、import 載入側已寫 `entity.sex`，創建側是缺口，一併補齊 |
| NPC 整合 | 方案 A＋靈感化 B：prompt 階段注入「僅供靈感」建議名，spawn 階段對缺失名確定性補名；validator 與 schema 必填性不動 | 只用 A 時名字風格可能與 LLM 敘事脫節；只用 B 時 LLM 仍可能自創名。灵感定位讓 LLM 可依性別／背景調整（用戶核定），離線時兜底補名仍保證可玩 |
| RNG 策略 | UI 骰用模組級無種子 `Random()`；NPC 側用 `Random(crc32("definition.key:stage:role"))` | 玩家擲名本質是輸入的另一種形式，無需重放；NPC 名要與藍圖同種子可重放 |

拒絕的替代方案：把語料 bundle 進前端（SPA 契約禁止語料層、且 204 KB 進
bundle）；validator 白名單強制 LLM 只能回傳語料內名字（駁回率會咬 LLM
供貨率，且「黑鬍」等既有模板名要開例外）；每次擲骰隨機性別或固定男性池
（與表單狀態脫節、觀感差）。

## 3. 語料層：`world/lore/names.py`

凍結 dataclass 加 `MappingProxyType`，與 `RACE_REGISTRY` 同規格。module import
時以純函式解析 `third_party/fantasy-namegen/data/` 的五個 pack 檔與 translit
表；啟動同步沿用既有 lore 鏡接管線（`world/lore/sync.py`），保持冪等。

```python
@dataclass(frozen=True)
class NamePart:
    text: str          # "Edvard"（原文，永不顯示於遊戲）
    zh: str            # "愛德華"（translit 查得）
    meaning_zh: str    # 詞源或意象註解；MVP 不顯示，留給未來 lore codex

@dataclass(frozen=True)
class NamePack:
    key: str                                    # "fantasy-human"
    race_key: str | None                        # "human"；dwarf／halfling 為 None
    surnames: tuple[NamePart, ...]
    given: Mapping[str, tuple[NamePart, ...]]   # m／f／u 三池
    naming_note_zh: str

NAME_PACK_REGISTRY: Mapping[str, NamePack]      # 五包
NAME_PACK_BY_RACE: Mapping[str, str]            # human／elf／beastfolk → 三包
```

import 時不變量（違反即 import 失敗，fail-fast）：

1. translit 表覆蓋全部零件（現況 1,274 筆零缺漏；上游手動同步若引入新詞，
   這條第一時間抓到缺口，而不是執行期掉字）。
2. 每包 m／f／u 池非空；`NAME_PACK_BY_RACE` 只指向已註冊包。
3. 最長「名・姓」組合通過 `world/rules/character_creation.py`
   `_validate_name` 的字數與字元限制（上限 64；現況最長組合遠低於此）。

姓名合成格式為 `f"{given.zh}・{surname.zh}"`，分隔符 `・`（U+30FB）是
registry 內唯一合成常量。名字原文（`text`）永不出現在玩家可見輸出。

## 4. 規則層：`world/rules/namegen.py`

純函式模組，無 DB、無 Evennia import，是擲名的唯一實作點。

```python
def roll_name(pack_key: str, sex: str, rng: Random) -> str: ...
def roll_name_for_race(race_key: str | None, sex: str, rng: Random) -> str: ...
```

`roll_name` 依 `pack_key` 取包，依 `sex` 選池（`female`→f、`male`→m、
`other`→u 池優先、空字串或 None→隨機挑一池），回傳合成譯名。
`roll_name_for_race` 先經 `NAME_PACK_BY_RACE` 解析包，`race_key` 為 None 或
無映射時隨機挑一個有 `race_key` 綁定的包（dwarf／halfling 不參予隨機兜底）。

錯誤處理：包不存在→ `KeyError`（呼叫端是程式內常量，不吞）；過濾後池為空→
退回該包全池，產生器絕不死掉。觀察性：依 facade 規範，NPC 補名處發
`action_commit` 級 info 事件，context 帶 `quest`／`stage`／`role`。

RNG 來源分兩條、不共用：

- 角色創建骰子：模組級無種子 `random.Random()`。擲出的名字進入 payload 後
  與手打名字同等待遇，經 `_validate_name` 持久化。
- NPC 生成：呼叫端自建 `Random(seed)`，`seed =
  zlib.crc32(f"{definition.key}:{stage_index}:{role}".encode())`（`QuestDefinition.key`
  即藍圖身份）。同藍圖重建必得同名 NPC。

## 5. 角色創建 UI 接線

### 5.1 性別下拉

`CreationOverlay.vue` 自訂表單在「名稱」欄位**下方**新增「性別」`<select>`。
選項讀自 panel 新增的 `custom.sex`（值為 `SEX_VALUES` 加中文標籤「女性／
男性／其他」，由 `world/rules/creation_wizard.py` 的 panel view 送出，前端
不寫死）。`customPayload`（`creation_menu.js`）加 `sex` 欄；草稿持久化與
還原同 `display_name`。規則層驗證 `sex` 為 `SEX_VALUES` 成員或 None
（None→`DEFAULT_SEX`），並寫入角色 entity，補齊 `world/imports/loader.py`
已有而創建側沒有的 `entity.sex` 缺口。

### 5.2 骰子按鈕

姓名 `<input>` 右側加 🎲 按鈕（`data-testid="creation-roll-name"`）。點擊經
既有 `ui_action` 通道發 `creation.roll_name`，payload 為
`{"race": ..., "subrace": ..., "sex": ...}`；`creation_wizard` 認得此 action，
以 `roll_name_for_race` 擲名並回 `ui_action_result` 帶 `{"display_name": ...}`；
前端收到即回填姓名欄。語料零進前端。擲名結果可被玩家手動改寫，最終仍以
`creation.custom` payload 經 `_validate_name` 為準。

## 6. NPC 生成流接線

### 6.1 Prompt 階段：靈感名

`world/prompts/registry.py` 組 scenario-director prompt 時，對每個 stage NPC
需求槽位先以 `roll_name_for_race(None, "", Random(crc32(f"{definition_key}:{stage}:{role}")))`
擲一個靈感名，註明「僅供靈感」：

> suggested_name（僅供靈感）：加斯帕・斯諾 － 可直接採用，或依角色性別、
> 背景、語氣調整；建議填寫 display_name

schema 指示同步加一句：`display_name` 建議填寫，風格可參考建議名，依敘事
需要調整。JSON schema 本身不動（`display_name` 維持選填），validator 不動。
定位為靈感，讓語料風格錨定與 LLM 敘事自由共存；擲名不綁性別或需求時，
模型有權改寫。

### 6.2 Spawn 階段：兜底補名

`world/quests/scene_builder.py` 的 `_apply_characterization()` 在
`display_name is None` 分支呼叫 `roll_name_for_race(race_key, sex,
Random(crc32(f"{definition.key}:{stage_index}:{role}")))` 並寫
`npc.db.display_name`。
`race_key` 從 NPC 原型取，取不到時傳 None 走隨機包；`sex` 同取原型預設。
LLM 已填名字的佔用者完全不動（「黑鬍」等模板名路徑不受影響）。種子座標與
prompt 階段一致，離線模板重跑必得同名。

## 7. 資料流總覽

```
third_party/fantasy-namegen/*.json
        │ import 時解析＋凍結
        ▼
world/lore/names.py（NAME_PACK_REGISTRY）
        │ 只讀
        ▼
world/rules/namegen.py（roll_name／roll_name_for_race）
   │                │
   │ UI 骰（無種子） │ NPC（crc32 種子）
   ▼                ▼
creation_wizard    prompts/registry.py（靈感名）
  creation.roll_name      │
   │ ui_action_result     ▼
   ▼                LLM 填 display_name（可改寫靈感名）
CreationOverlay 回填        │
  → creation.custom        ▼
  → _validate_name    scene_builder._apply_characterization
  → entity.sex             │ None 時兜底補名
                           ▼
                      npc.db.display_name
```

單向依賴：`lore` 不依賴任何人；`rules/namegen` 只讀 lore；兩個消費端只呼叫
rules。`world/ai/` 全程不落地任何狀態，靈感名由 prompt 組合器讀 rules 產生。

## 8. 錯誤處理

| 情境 | 行為 |
|---|---|
| translit 缺詞（上游同步後） | import 時不變量 1 直接炸出，附缺詞清單；執行期永不发生 |
| 池過濾為空 | 退回該包全池（不死） |
| 不存在的 pack_key | `KeyError`，不吞 |
| `creation.roll_name` 帶無效 race／sex | 規則層以既有 validation 錯誤回 `ui_protocol_error`，前端顯示既有錯誤通道訊息 |
| LLM 回傳超長或含非法字元的名字 | 走既有 `MAX_NAME_LENGTH` 與 validator 路徑，本設計不新增規則 |
| `display_name` 缺失（LLM 未填或離線） | spawn 兜底補名，必然有名 |

## 9. 測試與契約同步

- `world/lore/tests/test_names.py`（`unittest.TestCase`）：registry 載入不變量
  三條、最長名過 `_validate_name`、合成格式常量。
- `world/rules/tests/test_namegen.py`：固定種子可重放、sex→池映射、`other`→u
  池優先、空池退回、非法包 `KeyError`、`roll_name_for_race` 映射與隨機兜底。
- `creation_wizard` 面板測試（Evennia 級）：`custom.sex` 欄存在；
  `creation.roll_name` 行動往返；`creation.custom` 帶／不帶 `sex` 的驗證與
  `entity.sex` 落地。
- `scene_builder` 測試：`display_name=None` 補名且同種子重放同名；有名字時
  不覆寫；靈感名出現在 prompt 組裝輸出且不影響 schema 必填性。
- 前端：`creation_menu.js` 純邏輯測試（roll payload 形狀、result 回填、sex
  欄進出 draft）；Vitest 元件測（🎲 按鈕、性別下拉渲染與選擇）；新元件抽檔時
  補 Storybook story 與 showcase coverage。
- `.github/evennia-shards.json` 註冊兩個新 test module（同一 change 內）。
- `tools.spec_traceability`：新 capability spec 每條 requirement 配
  `covers_requirement` 標註。
- 玩家命令面無變動，`docs/game/commands.md` 不動。
- 授權面：玩家可見處（若有 namegen 相關關於頁）依
  `third_party/fantasy-namegen/THIRD_PARTY_NOTICES.md` 署名；程式內不改寫上游
  語料文字，僅組合成顯示名。

## 10. 範圍外

- dwarf／halfling 兩包的遊戲內消費端（留給未來新族或 subrace 分包）。
- `meaning_zh` 進 lore codex 知識卡。
- 玩家替 NPC 提名、staff 端 namegen 收藏匣命令。
- prompt 注入多候選名或依 archetype 綁包（留作後續 tweak，與本設計不互斥）。
- 上游語料自動同步（明確禁止：僅手動重抓並更新 THIRD_PARTY_NOTICES 日期）。
