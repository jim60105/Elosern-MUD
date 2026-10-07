# GM 世界資料瀏覽

這個頁面說明 GM 控制台「世界資料」區塊的介面契約、登錄表索引與引用宣告。這是 `gm-portal-s4-world-data` 交付的範圍，位於 `/gm/world`，用來瀏覽伺服器目前載入的手寫世界資料、雙向追蹤條目之間的引用，並以唯讀方式檢視規則書與提示詞的 YAML 原始檔。

手寫資料仍然是 git 中的原始碼。這個介面不會寫入任何原始檔，也不會變更世界狀態。唯一的動作是把 `prompts/` 重新載入記憶體中的提示詞庫。

## 登錄表索引

`world/lore/registry_index.py` 的 `REGISTRY_INDEX` 是手動維護的清單，每個項目是一個 `RegistrySpec`：

| 欄位 | 說明 |
| --- | --- |
| `name` | 唯一的 snake_case 名稱，也是 URL 片段；不得命名為 `sources` |
| `label` | 正體中文顯示名稱 |
| `group` | 八個分組之一：世界、生物、物品與經濟、聚落、人物、技能、任務、規則書 |
| `loader` | 延遲載入函式，回傳 `key → frozen dataclass` 的唯讀對應 |
| `source_path` | 相對於儲存庫根目錄的原始檔或資料夾 |
| `summary_fields` | 清單頁顯示的欄位，可用點號表示巢狀欄位；未宣告時改用第一個非 `key` 的字串欄位 |

載入函式在呼叫時才匯入擁有該資料的模組，所以匯入索引不會連帶載入 `world/rules`、`world/skills` 或 `world/quests`。載入函式讀取的是伺服器程序已載入的值，而不是重新讀取原始檔：

- lore 登錄表、技能與魔物行為設定直接讀取模組層級的對應。
- 任務定義讀取手寫的 `QUEST_CATALOG`。程序內的 `QUEST_DEFINITION_REGISTRY` 也包含執行期生成的任務，那屬於執行期狀態，由「執行期狀態」區塊檢視。
- 職業讀取 `profession_config` 的載入快取。
- 公會考試對手、商店營業設定與服務主持人在伺服器啟動後讀取 `guild_config.CATALOG`。目錄尚未載入時（離線工具、測試），改用目錄載入器本身的驗證函式組出同一份資料，只略過需要啟動時任務登錄表的任務獎勵段落。

新增登錄表時，把它加進 `REGISTRY_INDEX` 即可瀏覽。啟動同步（`world/lore/sync.py` 的 `_ALL_REGISTRIES`）的每個登錄表都必須出現在索引中，合約測試會檢查這一點。

## 引用宣告

`world/lore/registry_refs.py` 是不匯入任何遊戲模組的葉模組，提供兩個產生 `dataclasses.field` 中繼資料的函式：

```python
from dataclasses import dataclass, field
from world.lore.registry_refs import ref, ref_many


@dataclass(frozen=True)
class MonsterSite:
    region_key: str = field(metadata=ref("wilderness_regions", inverse="monster_sites"))
    variant_keys: tuple[str, ...] = field(
        metadata=ref_many("monster_variants", inverse="monster_sites")
    )
```

- `ref(registry, *, inverse, nullable=False)`：欄位存放一個 key；宣告 `nullable` 時允許 `None`，`None` 不會產生引用。
- `ref_many(registry, *, inverse)`：欄位存放 tuple、list 或 frozenset 形式的多個 key。frozenset 依排序後的順序走訪。
- `inverse`：目標條目列出引用者時使用的名稱。同一個目標登錄表的不同宣告（宣告類別加欄位）不得共用 inverse 名稱。同一個宣告的多個實例不算衝突。

宣告只加中繼資料，不改變欄位型別、預設值或值。沒有預設值的欄位寫成 `field(metadata=...)` 仍然是必填欄位；有預設值的欄位寫成 `field(default=..., metadata=...)`。巢狀 dataclass 內的欄位也可以宣告，走訪會遞迴進入 dataclass、tuple、list、frozenset 與 mapping。

只宣告直接存放 key 的欄位。複合引用（key 還必須與另一個欄位一致）以及帶前綴或需要解析的 key 仍由各登錄表既有的驗證函式負責，不要宣告成引用。

第一批宣告涵蓋魔物物種、變體、據點與環境配置，任務定義（含目標與目的地），物品，場所、商店與商品組合，以及作為目標的 NPC 人物設定。

### 索引與完整性檢查

- `build_reference_index()` 回傳 `ReferenceIndex`：`forward[(registry, key)]` 依欄位順序列出引用；`inverse[(target_registry, target_key)][inverse_name]` 依 inverse 名稱分組列出引用者。登錄表在執行期不會改變，所以結果依索引 tuple 快取整個程序的生命週期。
- `check_references()` 回傳每個目標 key 不存在的 `DanglingReference(registry, key, field_path, target_registry, missing_key)`。
- `declaration_errors()` 回報指向未登錄名稱的宣告與 inverse 名稱衝突。除了走訪實例，它也會依型別註記遞迴收集宣告，所以沒有任何出貨資料填入的巢狀宣告（例如任務目的地的 `anchor_key`）同樣會被檢查。

這些檢查是 CI 合約（`world/lore/tests/test_registry_index_contract.py`），不在伺服器啟動時執行。出貨資料必須沒有懸空引用；如果新的宣告暴露出懸空 key，請在同一個變更中修正資料。

欄位路徑的格式在後端走訪與前端 JSON 樹之間共用：屬性以點號連接，序列位置以 `[n]` 表示，例如 `stages[0].objective.species_key`。

## 路由

伺服器端在 `web/gm/urls.py` 註冊下列路由，全部經由 `gm_path` 套用 Developer 權限檢查，回應沿用既有的 JSON 信封。讀取函式位於 `web/gm/readers/world.py` 與 `web/gm/readers/sources.py`，受讀取層 AST 唯讀合約約束。

| 路由 | 用途 |
| --- | --- |
| `GET /gm/api/registry/` | 登錄表索引（名稱、標籤、分組、條目數、原始檔路徑、摘要欄位） |
| `GET /gm/api/registry/?q=` | 跨登錄表搜尋：回傳所有符合的 `{registry, key}`，依登錄表名稱再依 key 排序，不分頁 |
| `GET /gm/api/registry/<registry>?cursor=&limit=&q=` | 條目清單：依 key 排序，預設 50 筆，上限 200 筆，游標綁定查詢文字 |
| `GET /gm/api/registry/<registry>/<key>` | 條目明細：轉換後的欄位、依欄位路徑列出的引用、依 inverse 名稱分組的引用者 |
| `GET /gm/api/sources/` | 原始檔允許清單 |
| `GET /gm/api/sources/<name>` | 單一原始檔的磁碟內容 |
| `POST /gm/api/sources/prompts/reload` | 重新載入提示詞庫，需要 CSRF 權杖 |

`/gm/api/registry` 有沒有結尾斜線都可以。保留的 `sources/prompts/reload` 路由必須在 `sources/<name>` 之前註冊。前端路由同樣先註冊 `/gm/world/sources/...`，再註冊 `/gm/world/<registry>` 與 `/gm/world/<registry>/<key>`。

搜尋比對 key 以及條目中每個字串值（含巢狀 dataclass），不分大小寫，查詢文字上限 200 字元。欄位值的轉換沿用 `world/lore/sync.py` `_db_safe` 的語意：列舉轉為值、tuple 轉為 list，並遞迴進入巢狀 dataclass。JSON 無法表示的值會成為 `$unserializable` 標記。

錯誤碼：未知的登錄表為 404 `registry_not_found`，未知的 key 為 404 `entry_not_found`，不在允許清單中的原始檔為 404 `source_not_found`。存取、CSRF、方法與分頁錯誤沿用既有的錯誤碼。

## 原始檔檢視

允許清單在每次請求時從三個目錄重新建立：`world/rules/rulebook/*.yaml`、`world/rules/rulebook/commerce/*.yaml`，以及提示詞庫目錄（`settings.PROMPT_ROOT`，預設為 `prompts/`）中的 `*.yaml`。檔名以帶根目錄前綴的名稱識別，例如 `rulebook/combat.yaml`、`rulebook/commerce/altoria.yaml`、`prompts/art.yaml`，所以不同目錄下的同名檔案不會衝突。

請求的名稱只會在允許清單中查詢，不會與檔案系統路徑串接。解析後跳出核准目錄的符號連結會被排除，讀取時也會再檢查一次。無法以 UTF-8 解碼或超過 1 MB 的檔案視為 `source_not_found`。

原始檔頁面顯示的是磁碟上的內容，不一定是伺服器目前載入的版本。規則書與登錄表的修改都需要重新啟動伺服器才會生效。

## 提示詞重新載入

提示詞原始檔頁面提供「重新載入提示詞庫」。處理函式位於 `web/gm/world_api.py`，不在唯讀讀取層內。它依序呼叫 `reset_prompt_library()` 與 `load_prompt_library()`，並回傳載入診斷：

```json
{"outcome": "ok", "available": 22, "total": 22, "root": "prompts", "unavailable": []}
```

`outcome` 在有任何提示詞 key 無法使用時為 `degraded`，`unavailable` 列出每個 key 的檔案與問題。載入失敗的語意與伺服器啟動時完全相同：載入器把失敗的 key 標記為無法使用，使用它的層級改走確定性降級路徑。這裡沒有額外的回復或備援。

缺少或無效的 CSRF 權杖會得到 403 `csrf_failed`，GET 會得到 405，兩者都不會呼叫載入器。每次重新載入都會發出 `gm_prompts_reloaded` 與 `gm_action` 兩個 facade 事件，context 包含操作帳號、結果與無法使用的 key，不包含提示詞內文。

## 執行期連結

「執行期狀態」區塊中存放登錄表 key 的欄位會連到對應的手寫條目，包括角色的種族與亞種、魔物的物種與變體、任務紀錄的定義鍵，以及任務目標的物種、據點與區域。連結描述為 `{"kind": "registry", "registry": "<name>", "id": "<key>"}`，由 `web/gm/readers/world.py` 的 `authored_link()` 產生。key 不在已載入的索引中時（例如執行期生成的任務定義）不產生連結，只顯示原值。

前端以 `GmEntityLink` 渲染這類連結，並加上 ◇ 符號，與執行期物件（▸）區分。宣告了引用但目標不存在時，顯示為帶刪除線的文字與「目標不存在」標記，不會成為連結。

## 測試

- `world/lore/tests/test_registry_refs.py`：以合成登錄表測試 `ref`、`ref_many`、`nullable`、巢狀走訪、frozenset 順序、懸空引用、宣告驗證與快取。
- `world/lore/tests/test_registry_index_contract.py`：出貨資料的索引涵蓋範圍、引用完整性與延遲匯入合約，並登記在 test-data 合約清單中。
- `web/gm/tests/test_world_api.py`：以替換過的合成索引與暫存遊戲目錄測試存取矩陣、信封、分頁、搜尋、明細、原始檔允許清單、提示詞重新載入、事件，以及讀取與重新載入後資料列、Attribute 與原始檔位元組都不變（含網路停用的情況）。
- `web/admin-app/tests/world.test.js`：連結路由、JSON 樹的欄位路徑連結、引用與引用者清單、四個頁面與重新載入流程。
