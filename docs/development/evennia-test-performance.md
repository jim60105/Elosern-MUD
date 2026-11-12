# Evennia 測試效能報告

本報告記錄了 `optimize-evennia-testing` 變更的測量基準。各項時間皆為參考機器的觀測值，僅在相同環境條件下成立。一般性的優化指導原則請參見「[Evennia 測試效能優化指南](evennia-testing-guide)」。

## 環境

- Baseline commit: `d258ed7b65fb0e2e2d461c16b2ca806f76fe3fa8`
- Optimized revision identity: dirty worktree branch `feat/optimize-evennia-testing`，基於 `d258ed7b65fb0e2e2d461c16b2ca806f76fe3fa8`；待審查變更提交後，請以最終 commit SHA 取代此暫定識別。
- Python：3.13.14
- Evennia：6.1.0
- Django：6.0.7
- uv：0.12.0
- 邏輯處理器：24
- `uv.lock` SHA-256：`bd909fdaa68a4aa76ba72897f0e568b1a58f579e425be58c1f2e25fa8defec1b`
- 覆蓋率測量工具：效能測試期間停用
- 目標擁有權：`commands server typeclasses world web.webclient`
- 資料庫狀態：序列執行的 `--keepdb`，採用相同的資料庫遷移、fixtures、目標集合與暖機協定。基準版本預設使用記憶體資料庫，因此儘管加上 `--keepdb`，仍會在每個行程重新建置 schema；優化後的儲存設定檔則使用由 `DATABASES["default"]["TEST"]["NAME"]` 指定的專用檔案並重用其暖機 schema。這項記錄的儲存差異屬於刻意的優化變數（storage difference is an intentional optimization variable）。

## 測試執行器驗證

鎖定版本的 Evennia 啟動器會將確切的 `test` 操作與未知選項轉發給 Django 執行器。直接探測已驗證了以點分隔的模組／類別／方法標籤、`--keepdb`、`--noinput`、`--timing` 與 `--durations`。Django 6.0 可接受 `--parallel 4` 與單獨的 `--parallel`；其適用性評估如下。測試設定防護要求 `sys.argv[1]` 的操作參數必須恰好為 `test` 且帶有 `MUD_TEST_SETTINGS=1`；後續包含該 token 的參數無法授權伺服器或遷移命令。

原始備註中結合 `:memory:` 與 `--keepdb` 的建議已被拒絕，原因是記憶體資料庫無法在行程結束後繼續留存。原始備註中無條件啟用平行 worker 的建議同樣被拒絕，除非證據、覆蓋率、資源隔離與重複計時皆證明具備同等效果。

## 基準版本

命令：

```sh
uv run --locked evennia test --settings settings.py --keepdb --timing \
  --durations 20 commands server typeclasses world web.webclient
```

一次暖機與三次測量的序列執行皆通過全部 1,146 項測試。

| Run | Test time | Database setup | Total time | Result |
|---|---:|---:|---:|---|
| Warm-up | 515.414 s | 2.551 s | 519.151 s | Pass |
| Measured 1 | 514.764 s | 2.339 s | 518.046 s | Pass |
| Measured 2 | 519.437 s | 2.515 s | 522.980 s | Pass |
| Measured 3 | 516.756 s | 2.510 s | 520.285 s | Pass |

測得的中位數為 **520.285 seconds**。

最慢的測試始終是 `test_onboarding_journey.py` 與 `test_phase4_integration.py` 中的整合旅程，每次約需 1.47 至 1.92 秒。這些測試實際執行了真實 Typeclass、指令、交易以及公會與戰鬥狀態，因此移除 fixture 會改變被測邊界。

## Fixture 清點

在轉換前，有 84 個測試檔案匯入了 `EvenniaTest`，66 個檔案直接宣告了 `EvenniaTest` 類別，9 個檔案使用了 `EvenniaCommandTestMixin`，53 個檔案宣告了 `setUp()`，且沒有任何檔案使用 `EvenniaTestCase` 或 `setUpTestData()`。WebClient 擁有權掃描在基準 SHA 發現 `web/webclient/**/test*.py` 底下有六個非瀏覽器檔案，以及 `web/tests/browser/test*.py` 底下的五個受管瀏覽器檔案。這兩個集合互斥，聯集即為 `web` 底下的所有 Python 測試。

第一批安全的優化作業將七個純剖析器、AST 與 YAML 測試移出全域世界 fixtures：

- `RegistrationBoundaryScanTests`
- `InstanceYamlTests`
- `CombatSessionRecordTests` 中的兩項儲存測試
- `ExamRecordTests`

由資料庫支援的確定性工作階段 ID 方法仍保留在獨立的 `EvenniaTest` 類別中。未引入類別層級的可變 fixtures 或外部 I/O 模擬，因為測量的候選項並不具備足夠依據。

## 優化後成果

優化後的修訂版本是在套用僅限測試設定、fixture 批次修改與互斥擁有權變更後，從此工作樹進行測量。一次暖機與三次測量的序列執行皆通過相同的 1,146 項測試。

| Run | Test time | Database setup | Total time | Result |
|---|---:|---:|---:|---|
| Warm-up | 353.774 s | 0.549 s | 355.384 s | Pass |
| Measured 1 | 353.021 s | 0.418 s | 354.432 s | Pass |
| Measured 2 | 352.608 s | 0.591 s | 354.189 s | Pass |
| Measured 3 | 355.937 s | 0.480 s | 357.400 s | Pass |

優化後的中位數為 **354.432 seconds**，相較於 520.285 秒的基準中位數減少了 31.9%（31.9% reduction），通過了 416.228 秒的驗收門檻。針對乾淨資料庫的聚焦執行順利通過，且連續兩次保留資料庫的聚焦執行將資料庫設定時間從初次建立的 3.086 秒減少為重用時的 0.463 秒，同時未改動開發者資料庫。

## 平行執行評估

初次保留資料庫的 `--parallel 4` 執行在 60.395 秒內通過了全部 1,146 項測試。但隨即重複的執行並不穩定：共享的魔物技能註冊表狀態導致 `test_depleted_resource_falls_back_to_basic_attack` 收到 `shadow_slash` 而非 `basic_attack`，隨後 Django 無法對來自 worker 的失敗追蹤進行 pickle 序列化。這是正確性、隔離性與診斷機制的缺陷，因此在未花費更多時間於單純 `--parallel`、乾淨複製、證據收集或子行程覆蓋率執行前，先駁回平行執行方案。

### 2026-08-11：品質閘門穩定化與 CI 導入平行處理

品質閘門先前以單一工作序列執行整個帶有覆蓋率的非瀏覽器 Evennia 套件：在 3,004 項測試時，CI 耗時 **2,385 秒（約 40 分鐘）**，且因順序相關的註冊表洩漏連續兩次在合併時失敗。本次變更修復了隔離缺陷、證明了平行等價性、在 CI 中採用了平行設定檔，並將匯總覆蓋率提升至閘門之上。

**已修復的隔離缺陷（CI 失敗的根本原因）：**

- `OnboardingHuntIntegrationTests` 執行了 `sync_guild_economy()` 卻僅還原 `QUEST_DEFINITION_REGISTRY`，將標準的 `introductory_hunt` 委託洩漏至行程全域的 `GUILD_OFFER_REGISTRY` 中；後續測試衝突的 `×1` 註冊因此引發 `GuildOfferError`。目前這三個註冊表（`QUEST_DEFINITION_REGISTRY`、`GUILD_OFFER_REGISTRY`、`SCENE_REQUIREMENT_REGISTRY`）皆透過單一可重用的 `RegistryIsolationMixin`（`world/quests/tests/_fixtures.py`）進行快照與還原，且在任何異動前透過 `addCleanup` 註冊還原，因此失敗的 `setUp` 也不會洩漏狀態。
- `test_scenario_director` 破壞性地清空了三個註冊表而未還原先前內容；這些位置現已改用 mixin。冷啟動模組重新匯入測試還原了 `sys.modules` 但未還原 `world.ai` 套件屬性，導致後續測試的模組身分失效；兩者現皆已還原。
- `test_clock` 就地重新載入 `world.rules.clock`，使其他模組在匯入時綁定的類別身分失效；模組層級的間隔驗證已被提煉至 `_validate_settlement_intervals()`，測試直接呼叫它而非重新載入模組。
- 戰鬥測試在行程全域的略過安全註冊表 `_BATTLEFIELDS` 中留下了陳舊項目（以 Evennia fixtures 重用的實體鍵為鍵，例如每個 `char1` 皆為 `"Char"`），且呼叫 `at_server_start()` 或 `sync_guild_economy()` 的測試會重新註冊被拋棄的戰鬥階段。`BattlefieldIsolation` mixin 現於所有接觸戰鬥的類別以及同步與啟動呼叫端中對 `_BATTLEFIELDS` 進行快照與還原。
- 數個類別在自身 setup 未註冊任務目錄的情況下載入親和性規則書（其會解析 `introductory_hunt`），導致在最先執行它們的 worker 上失敗；各類別現於自身的 `setUp` 中呼叫 `register_catalog()`。

**等價性證據（當時為 3,007 項測試，加入覆蓋率測試後為 3,104 項）：** 連續兩次單純的 `--parallel 4`、`--shuffle 42`、`-r`（反向），以及額外的 `--parallel 16` 執行皆全數綠燈通過。在平行 worker 下收集的需求證據能組合成可剖析且無交錯行的 JSONL。子行程覆蓋率（`coverage run --concurrency=multiprocessing --parallel-mode`）為每個 worker 產生一個 sidecar 檔案；`coverage combine` 會合併它們，且合併後的報告維持精確的 `commands server typeclasses web world` 根目錄。

**執行時間（CI 相關設定檔）：** 整個非瀏覽器 Evennia 套件在 `--parallel 4` 且包含覆蓋率檢測下約需 152 秒，相較於序列 CI 步驟的 2,385 秒加速了約 15 倍。在 24 核心開發機上，`--parallel 16` 約於 45 秒內完成執行。受管瀏覽器套件（148 項測試，每個分片行程啟動一個真實 Evennia 伺服器，戰鬥測試每項皆啟動專用伺服器）本機測量約為 3,465 秒（約 58 分鐘），並依提交的清單（`.github/browser-shards.json`）分片於六個 CI 工作中；每個分片仍為其檔案的唯一序列擁有者，且最上層回歸測試斷言所有探索到的瀏覽器測試檔案恰好屬於單一分片。

**覆蓋率：** 全部三個進入點的匯總覆蓋率（包含子行程覆蓋率的完整非瀏覽器 Evennia 套件、完整受管瀏覽器套件，以及最上層回歸套件）在本次變更開始時測得 88%，在為 `commands/localized/`（帳號、通用、說明、xyzgrid 指令）、scenario-director 資料類別與驗證器形狀、任務編譯邊界、公會設定與考核驗證、buff 定義驗證以及創角面板中最大的未涵蓋分支加入聚焦測試後達到 **91.06%**。瀏覽器套件的父行程對這五個根目錄無可測量的覆蓋率貢獻（遊戲程式碼在受管伺服器子行程中執行），因此匯總覆蓋率由非瀏覽器 Evennia 套件主導，與閘門先前的計算方式完全一致。

**CI 採用：** 單一品質閘門工作拆分為五個：快速的 `preflight` 工作（OpenSpec 驗證、靜態可追溯性檢查、Node 套件、分片矩陣計算）、`evennia` 工作（帶有子行程覆蓋率的平行設定檔）、六個 `browser` 矩陣分片、`top-level` 工作，以及 `gate` 工作。gate 工作會下載所有工件，驗證每個預期的覆蓋率與證據工件皆存在且非空，依進入點順序串接證據檔案，執行 `spec_traceability verify`，以 `coverage combine` 合併所有上傳的 sidecar，驗證覆蓋率根目錄，執行 80% 匯總分支閘門，並僅從合併後的資料發布 Codecov XML。序列執行仍保留為最終交接證據的標準設定檔。

### 2026-08：修復隔離性後採用平行處理

在 2,525 項測試時，序列套件執行時間增長至約 1,033 秒。重新評估平行執行並修復了所觀察到的各項失敗根本原因：

- **非確定性的擲骰平手判定：** 中階 `pack_hunter` 魔物設定檔依最高預期傷害挑選技能，而兩個可負擔的單體物理技能平手時，`_choose_skill` 會以 `dice.roll_d100()` 判定。未設定種子的全域 PRNG 狀態在各 worker 間不同，導致 `test_depleted_resource_falls_back_and_resolves` 與 `test_unaffordable_preference_falls_back_to_affordable_skill` 斷言 `shadow_slash` 卻偶爾收到 `basic_attack`。這兩項測試現已使用 `patch("world.rules.monster_behaviour.dice.roll_d100", return_value=0)` 固定平手擲骰結果。
- **無法 pickle 序列化的失敗追蹤：** 加入 `tblib`（3.2.2）作為開發相依套件，使 Django 能序列化 worker 的追蹤訊息；平行模式下的失敗現已可診斷。
- **共享規則書檔案競爭：** `AffinityConfigValidationTests` 就地重寫 `world/rules/rulebook/affinity.yaml` 並在 `tearDown` 中還原；平行 worker 在該檔案上發生競爭並讀取到異常數值。`load_config(path=...)` 現接受明確的規則書路徑，且測試從 `TemporaryDirectory` 複本中測試異常規則書，共享的來源檔案絕不再被重寫。
- **行程全域任務與目錄註冊表洩漏：** 數個測試類別註冊了 `QUEST_DEFINITION_REGISTRY`、`GUILD_OFFER_REGISTRY` 或 `CATALOG` 而未進行快照還原（或在註冊後才快照），將 `introductory_hunt` 洩漏至執行它們的 worker。已在 `test_onboarding_journey`、`test_guild_config`、`test_dialogue`、`test_service_view`、`test_service_view_side_effects`、`test_guild_economy_sync`、`test_party_offline_loop`、`test_guild_registration` 以及轉換後的 `web.webclient` 展示器與動作類別中完成修復。編譯邊界測試現斷言註冊表相對於自身的 setUp 快照維持不變，而非斷言字面上的空註冊表，這才是語意上正確的契約。
- **讀取路徑的資料庫寫入：** `map_knowledge._registered_grid_bounds` 呼叫了 xyzgrid contrib 的 `get_xyzgrid()`，該函式在純讀取時會建立全域 `XYZGrid` script。純 `unittest.TestCase` 在 autocommit 下執行，導致語法測試永久認可了該 script 並污染後續所有 `--keepdb` 的啟動執行。查詢現於未佈建網格時返回 `None`，因此驗證路徑絕不寫入資料庫。
- **依賴大量 fixture 的展示器測試：** `web.webclient` 展示與動作轉接器類別（213 個方法，每項因負擔 `sync_grid()` 與 `sync_wilderness()` 耗時約 1.8 秒）從 `EvenniaTest` 移至 `EvenniaTestCase`，昂貴的網格、Wilderness 與目錄同步提升至類別層級，並於每個測試中建立實體。它們現在序列執行約需 13 秒且具備平行安全性。

證據執行（完整 2,525 項測試套件，`--parallel 4 --noinput`，連續執行兩次）：

| Run | Test time | Total time | Result |
|---|---:|---:|---|
| Parallel 1 | 125.423 s | 129.525 s | Pass |
| Parallel 2 | 125.149 s | 129.153 s | Pass |

相較於 1,033 秒的序列基準加速了約 8.2 倍。序列執行仍為最終交接證據的標準；轉換與新隔離的測試類別亦能通過完整的序列套件（跨次執行測得 1,006 至 1,054 秒，與先前第一階段報告中 1,146 項測試集合在 354 秒的表現相符）。保留的 `--keepdb` 資料庫在完整執行後維持乾淨：`world.maps.tests.test_bootstrap` 的全新網格前提條件在重複連續執行下順利通過。

序列執行仍為交接標準，但 `--parallel 16 --noinput` 是開發期間記載的預設全套件命令（CI 維持 `--parallel 4` 作為其 worker 設定檔）。移除重複的受管瀏覽器探索僅在最終序列證據與匯總覆蓋率執行通過後另行接受。

最終乾淨覆蓋率探測亦確認既有保留的 SQLite 檔案會導致 Django 要求刪除確認。標準的非互動式乾淨命令因此傳入 `--noinput`；這允許僅替換專用的測試資料庫，並避免在 CI 中發生 `EOFError`。

### 2026-08-16：Evennia 套件在六個 CI 工作間進行機器級分片

單一 CI evennia 工作（一台 `ubuntu-latest` 執行器執行整個非瀏覽器套件，在 run 31939321935 中耗時 **14 分 02 秒**）已被由 `.github/evennia-shards.json` 驅動的六工作矩陣取代。每個分片在其專屬執行器上以相同的 worker 設定檔（`--parallel 4`，子行程覆蓋率）執行其清單標籤，寫入 `coverage-evennia-shard-<n>*` 與 `evidence.evennia-shard-<n>.jsonl`，並將它們作為各分片工件上傳。閘門循環檢查清單索引以維持完整性，將 `evidence.evennia-shard-*.jsonl` 與瀏覽器及最上層證據串接，並將 `coverage-evennia*` sidecar 與其餘部分合併，聚合語意維持不變。此舉旨在將 evennia 工作從約 14 分鐘縮短至約 2 至 4 分鐘，移出 CI 關鍵路徑，且在公開 Free 方案下零額外成本（6 個額外 `ubuntu-latest` 工作；evennia 與 browser 總工作數維持 ≤ 20）。

**套件規模（2026-08-16）：** 非瀏覽器 Evennia 套件現探索到 **4,263 項測試**（在後續功能與目錄變更後，由 2026-08-11 CI 採用的 3,104 項增長而來），涵蓋 `commands`、`server`、`typeclasses`、`world` 與 `web.webclient` 共 267 個測試模組。

**清單分割與本機序列計時**（24 核心參考機器，`--keepdb`，無覆蓋率；CI 以 `--parallel 4` 執行相同標籤）：

| Shard | Labels | Tests | Serial test time | Serial wall time |
|---|---|---:|---:|---:|
| 1 rules-a | 38 `world.rules.tests` modules | 650 | 137.6 s | ~2:40 |
| 2 rules-b | 37 `world.rules.tests` modules | 596 | 163.0 s | 2:47 |
| 3 rules-c | 37 `world.rules.tests` modules | 574 | 96.2 s | 1:39 |
| 4 | `world.quests world.skills world.art world.ai world.onboarding world.lore` | 1,154 | 171.7 s | 2:55 |
| 5 | `world.maps web.webclient world.imports world.prompts world.tests` | 817 | 153.3 s | 2:36 |
| 6 | `commands server typeclasses` | 472 | 118.0 s | 2:01 |

在初次測量後進行了一次重新平衡：初始的套件分組產生了一個 19 秒的分片與一個約 226 秒的分片（max/mean ≈ 1.6）；將 `web.webclient` 移離 `commands` 與 `typeclasses`（兩者合併執行時間約為各部分總和的兩倍），並將 `world.quests` 與輕量套件配對，使 max/mean 降至 **1.23**（172 秒 / 140 秒平均），低於 1.35 的重新平衡門檻。

**初次 CI 觀測（run 31945742664，分支 `feat/split-evennia-ci-shards`，首次即全綠通過）：**

| Job | Duration |
|---|---:|
| preflight | 24 s |
| evennia shard 1 (rules-a) | 2 m 10 s |
| evennia shard 2 (rules-b) | 2 m 46 s |
| evennia shard 3 (rules-c) | 1 m 39 s |
| evennia shard 4 (quests-skills-art-ai-onboarding-lore) | 2 m 23 s |
| evennia shard 5 (maps-webclient-imports-prompts-tests) | 2 m 8 s |
| evennia shard 6 (commands-server-typeclasses) | 1 m 40 s |
| top-level | 23 s |
| browser shard 1 (combat) | 19 m 10 s |
| browser shard 2 (creation-layout) | 16 m 31 s |
| browser shard 3 (exploration-reconnect) | 13 m 4 s |
| browser shard 4 (shell-actions-local-map-input-narrative) | 5 m 23 s |
| browser shard 5 (services-pointer) | 16 m 26 s |
| browser shard 6 (art-harness) | 11 m 36 s |
| gate | 23 s |

Evennia 套件現已移出 CI 關鍵路徑：其最慢分片（2 分 46 秒）取代了先前單一工作的 14 分 02 秒，六個分片在 1.29 的 max/median 內完成（166 秒 / 129 秒），低於 ≥ 2× 的重新平衡門檻，因此無需進一步平衡。整體工作流程耗時仍約 20 分鐘僅因受管瀏覽器套件主導（combat 19 分 10 秒）；該部分由同級的 `pack-browser-ci-shards` 變更處理。

### 2026-08-16：瀏覽器套件打包為 11 個雙行程分片

六個瀏覽器工作（各為單一 `unittest` 行程，檔案層級清單標籤）被替換為 **11 個工作 × 2 個隔離行程**。每個瀏覽器分片檢出儲存庫兩次（`w-a` 與 `w-b`），因為 Evennia 啟動器寫入 GAMEDIR 相對的 pid 檔案（`server/server.pid`、`server/portal.pid`）；在單一工作樹中的兩個測試架構會在此檔案上競爭並互相終止對方的行程。第二次檢出成本極低（儲存庫打包約 5 MB）。

- `.github/browser-shards.json` 現包含 11 個分片，每個分片包含兩個以點分隔模組／類別／方法標籤的行程清單 `files_a` 與 `files_b`。戰鬥測試（每項測試啟動伺服器，每項約 50 秒）在方法層級拆分至五個包含 4 至 5 項測試的清單；創角與服務類別在類別層級拆分；探索與美術在方法層級拆分；輕量的 shell 系列檔案則完整打包進一或兩個清單。每個行程清單依測得的每項測試權重以 ≤ 240 秒為預估目標（combat 約 50 秒、creation/layout 約 38 秒、services/pointer 約 47 秒、exploration/reconnect 約 40 秒、art/harness 約 36 秒、shell 系列約 6.4 秒）。
- `browser` 工作以內嵌的每行程 `COVERAGE_FILE`（`coverage-browser-shard-<n>-p1`/`-p2`）與 `OPENSPEC_TEST_EVIDENCE`（`evidence.browser-shard-<n>-p1.jsonl`/`-p2.jsonl`）將其兩個 `unittest` 呼叫作為平行背景行程執行，使用防護的 `wait "$pid" || status=$?` 等待兩者（GitHub 的 `set -e` 會在失敗的單純 `wait` 上中止），將兩個證據檔案依 A 後 B 的順序串接至 `evidence.browser-shard-<n>.jsonl`，將兩個覆蓋率檔案複製到工作根目錄，並在兩者狀態不皆為零時判定步驟失敗。無 `|| true`，無 `continue-on-error`。
- 閘門的聚合契約維持不變：各分片工件保持 `coverage-browser-shard-<n>*` 與 `evidence.browser-shard-<n>.jsonl` 名稱，完整性迴圈、證據串接與 `coverage combine coverage-browser-shard-*` 皆以索引為基準運作。20 個並行工作上限計算的是工作數量而非行程：1 preflight + 6 evennia + 11 browser + 1 top-level + 1 gate = 20。
- 瀏覽器擁有權契約測試由檔案層級移至**方法層級分割**（基於 AST，無匯入）：每個 `web/tests/browser/test_*.py` 檔案的每個 `test_*` 方法皆由 22 個行程清單中的恰好一個所擁有。後續 CI 觀察後的重新平衡僅為清單編輯加上契約測試，非工作流程編輯。

預期效果：戰鬥分片的 19 分 09 秒拆分至約 5 個平行行程清單（各約 4 至 5 分鐘），使瀏覽器關鍵路徑降至約 5 至 6 分鐘，並與 Evennia 機器分片一同使整體品質閘門總耗時不超過 10 分鐘。

**初次 CI 觀測（分支 `feat/pack-browser-ci-shards`）：**

- Run 31951553328：每個瀏覽器分片在步驟開始時皆以 `syntax error near unexpected token '&&'` 失敗，原因是 run-step 的常面文字區塊在每個背景子 shell 內的 `&&` 前放置了換行。透過將每個 `(cd w-a && ...)` / `(cd w-b && ...)` 子 shell 摺疊至單一行完成修復（防護等待、覆蓋率複製、證據串接與雙狀態檢查皆維持不變）。
- Run 31951788668：11 個瀏覽器分片中有 10 個通過；分片 4（創角，每個旅程皆啟動專用伺服器）有一項測試失敗，錯誤為 `twisted.internet.error.CannotListenError: Couldn't listen on 127.0.0.1:44951: [Errno 98] Address already in use`。這是測試架構記載的短期連接埠釋放後綁定競爭（`allocate_ports` 在 portal 綁定該連接埠前先行關閉其 socket）：在單一執行器上同時配置與啟動兩個測試架構行程時，競爭成為真實問題。此修復**修正了該變更「不改動 harness」的非目標**：當診斷顯示連接埠衝突標記（`CannotListenError` / `Address already in use`）時，`ManagedServer.start()` 現會以全新的執行期重試最多兩次，因此同級行程搶佔釋放的連接埠不再導致整個分片失敗。兩項快速單元測試鎖定了重試機制（衝突時使用新執行期，預算耗盡時拋出例外）。
- Run 31952671241：11 個瀏覽器分片中有 10 個通過；分片 11（art-harness-shell）的 `test_image_load_failure_shows_fallback_without_refetch` 失敗，出現 `AssertionError: 2 != 1`，場景圖像 URL 被請求了兩次。這暴露了潛在的客戶端競爭條件：在 `img.src = url` 與圖像的 `error` 事件之間重新算繪的快照更新為相同 URL 建立了第二個 `<img>`，違反了「不得重複擷取」的需求。雙行程的 CPU 競爭擴大了該時間窗口。美術面板現依 URL 將進行中的圖像元素暫存（`pendingImages`），並在重新算繪時重用它們而非發出重複請求；該元素僅在 `load` 或 `error` 時移出快取。一項 Node 契約測試鎖定了此重用行為。
- Run 31953234137：分片 10（art）的兩項全螢幕檢視測試失敗。上述重用引入了陳舊閉包回歸：附加至重用元素的接聽器閉包捕獲了 `renderScene` 的 `model` *參數*（首次算繪的快照），因此 `model.sceneFullView = true` 修改了失效的物件。該參數更名為 `panelModel`，使接聽器讀取外掛層級的 `model`，而 `render()` 始終保持其為最新狀態；完整的 `test_browser_art` 模組（14 項測試）再次全數通過。進一步 CI 觀察後的重新平衡仍維持為清單編輯加上契約測試。

### 2026-09-06：依 CI 實測重新平衡為 10 個 Evennia 分片與 18 個瀏覽器分片

CI run 33979656279 的分級實測（job 總時數）顯示僅兩個家族超出 5 分鐘預算：Evennia 分片 5（maps-webclient-imports-prompts-tests）為 5 分 06 秒（run-step 4.8 分鐘、1,568 項測試 268.6 秒），以及多個瀏覽器分片（5.2 至 9.1 分鐘）。瀏覽器 runner 的固定開銷（雙 checkout、雙 uv sync、pnpm install+build、Chromium 安裝）約為 54 秒，Evennia runner 約 15–55 秒，因此重打包直接以 run-step 預算為目標。

- `.github/evennia-shards.json` 由 6 個分片重切為 **10 個**：rules-a/b/c 與 quests-skills-art-ai-lore 原封不動（實測 1.8–2.8 分鐘）；原分片 5 依成本拆為四個專責分片：`webclient-actions`（含 `world.tests`）、`webclient-evidence`（`web.webclient.tests`，節點/vitest 轉接子行程最昂貴）、`maps-imports-prompts-observability`，以及按測試數對半切分的 `webclient-presentation-a`/`-b`（684 項測試，341/343）；`commands-server-typeclasses` 移至索引 5。預計每個 Evennia run-step ≤ 約 2 分鐘。
- `.github/browser-shards.json` 由 16 個分片重打包為 **18 個**（36 個行程清單）：以每個類別/method 的 CI 實測每測試權重（重型專用伺服器類別 40–55 秒、共享伺服器類別約 6–12 秒加一次開機）做 LPT 打包，單一走清單上限約 235 秒，預計最壞瀏覽器 job 總時數約 4.8 分鐘。重型類別維持方法層級分割（每清單最多 3–4 個 method），共享伺服器類別以類別層級標籤打包，使每個類別只在單一行程執行一次開機。
- 擁有權契約（`tests/test_evennia_test_optimization_contract.py`）在離線以相同 AST 解析演算法驗證：378 個非瀏覽器模組各由恰好一個分片擁有；269 個瀏覽器 method 各由 36 個行程清單中的恰好一個擁有。索引皆唯一且排序；本次未改動 workflow 與測試檔。
- 並行工作數為 1 preflight + 10 evennia + 18 browser + 1 frontend + 1 top-level + 1 gate = 32；超出 20 並行上限的工作排隊執行，因每個 job 本身 ≤ 5 分鐘，僅影響總牆鐘時間而非單一 job 預算。

### 2026-11-01：分片預算改以 CI 的每測試實測為依據

CI run 41290568911（33 個工作全綠）以 run-step 實測（`Run evennia shard N` 與
`Run browser shard N` 步驟本身）顯示 28 個分片工作中有 **19 個超過 6 分鐘**：
evennia shard 2（rules-b）與 shard 7（webclient-evidence）各 841 秒、shard 8
751 秒、shard 1（rules-a）595 秒、shard 4 425 秒；browser shard 9 788 秒、
shard 16 751 秒、shard 5 568 秒、shard 3 554 秒，另有 shard 7、10、11、2、14、
12、17、19 落在 6 至 9 分鐘之間。這一輪的 run-step 時間是重新打包唯一採用的
時間依據（每個瀏覽器分片的兩個行程另外各有一行 `Ran N tests in Xs`）。

分片層級的總和不足以重新打包：同一個清單裡最貴的測試可能佔掉大部分時間，而
log 只給出行程總和。兩個進入點因此都改為輸出**每測試**時間：

- evennia 分片的指令加上 `--durations 0`。Django 把 `--durations` 轉交
  `unittest.TextTestRunner`；`--parallel 4` 下送回的仍是各 worker 實測的每測試
  時間（以拋棄式 Django 專案在本專案環境驗證：`--parallel 2 --durations 0`
  印出實際的 0.300s/0.200s/0.050s）。
- `web/tests/browser/unittest_driver.py` 除了 `durations=0`，另裝一個 result
  class，在跑完後逐列印出每個測試的 **method 時間**與它前面的 **boundary
  時間**（前一個 `stopTest` 到本測試 `startTest`，其中包含前一類別的
  `tearDownClass` 與本類別的 `setUpClass`，也就是瀏覽器類別啟動共享 runtime
  的位置），最後再印 run 與 process 總時間。單一行程的這些數字直接落在該 job
  的 log 中。

`unittest` 的 `durations` 只涵蓋 method 區間（`setUp` 到 `doCleanups`），類別層級
fixture 跑在 suite 中而不在其中（`unittest/case.py` 的 `run()` 在
`_handleClassSetUp` 之後才計時）；瀏覽器的共享 runtime 開機因此必須由 boundary
欄位補上。打包時也一併對帳 CI 的行程總和（`Ran N tests in Xs`）與 run 總時間，
兩者的差即為首個類別的 fixture 與 suite 起始成本。

兩項都只增加診斷輸出：不改變標籤、worker 設定、斷言、超時或任何預算，也不
需要在本機重跑任何分片；重新打包以 CI log 的實測值為準。

同一日隨後的 CI run 41294398351（`5da11906`，34 個工作全綠）即以此輸出重新
打包，該輪本身的 run-step 也顯示原清單已普遍超出上限：瀏覽器 20 個分片有 19
個超過 5 分鐘（最差的 shard 9 為 1,045 秒），evennia 10 個分片有 5 個超過
（最差的 shard 2 為 831 秒）。

**打包模型（輸入全部來自該輪 CI 實測）：**

成本被拆成三塊，各自的量都直接來自該輪的每測試輸出：

- **每測試 method 時間**：`durations`／driver 表的 method 欄位。
- **類別層級 fixture**：driver 表的 boundary 欄位。boundary 是「前一個
  `stopTest` 到本測試 `startTest`」，因此它同時包含前一類別的 `tearDownClass`
  與本類別的 `setUpClass`；同一個類別因此有兩種觀測：進入「已在同一個清單裡
  用過共享伺服器」的類別（暖、實測中位數 0 秒），與該清單第一次用到共享伺服器
  的那一次（冷）。冷啟動的實測中位數為 **51.8 秒**（22 次觀測，範圍 33–67 秒），
  暖轉換為 0 秒。
- **行程層級開銷**：共享伺服器啟動（每個用到共享伺服器的清單一次，不隨類別數
  增加）、suite 常數約 5 秒，以及瀏覽器 job 的前置（兩次 checkout、兩次
  `uv sync`、Node/pnpm 與三份前端 bundle 建置、Playwright 安裝）約 80 秒。

| 進入點 | 每個清單／分片的成本模型 | 上限 |
|---|---|---|
| browser | Σ method ＋ 清單內每個出現類別的暖 boundary ＋（清單用到共享伺服器時）冷啟動一次 ＋ 5 秒 | 行程清單 ≤ 150 秒（預測 job ≤ 230 秒；乘上實測最差的 1.67 倍清單變異為 330 秒） |
| evennia | 依 Django 真實派工順序模擬 makespan：標籤順序即 discovery 順序，Django 接著依 `reorder_by = (TestCase, SimpleTestCase)` 重新分桶並逐 class 分派，模型中套用同樣的分桶與「逐 class 交給最空閒 worker」 | makespan ≤ 200 秒（預測 job ≤ 258 秒；乘上實測 1.55 倍變異為 359 秒） |

兩者都在**原始清單**上重算過：browser 的逐清單殘差為 max +23.9 秒、min
−10.5 秒、rms 9.0 秒（40 個清單，3 個低估且都 ≤ 10.5 秒）；evennia 的
分桶後 makespan 對 10 個分片預測 `Ran N tests in Xs` 的落差為 −8.3 至 +28.3 秒
（中位數 +4.9 秒）。相較之下，先前用「Σ ÷ 4」或 LPT 的近似會低估 3.5–88 秒，
因此模型改為模擬 Django 的真實派工順序與分桶。

**打包規則：只切不混。** 第一批重平衡把不同舊分片的模組依主題家族重新混合，
並把標籤按模組成本降序排列；該輪 CI（run 41297991078）有 7 個 evennia 分片與
3 個瀏覽器分片失敗，暴露出這套 suite 潛在的跨模組狀態依賴：

- `server/conf/tests/**` 的兩個守門測試要求該套件由套件層級 `server` 標籤擁有，
  不得逐模組列出（`test_new_module_path_is_not_listed_in_the_shard_manifest`）。
- `world/rules/tests/test_guild_economy_sync` 整包在沒有同分片夥伴先發布地圖世界
  時全數失敗（`SettlementNotLoaded`：`register_catalog()` 會走
  `ANCHOR_PLACEMENT_REGISTRY`）。已在 `_support.ServiceContentIsolation.setUp`
  自行呼叫 `map_runtime.ensure_published()`（這是既有測試 fixture 慣例），
  該模組單獨執行 28 項測試由此轉綠。
- 其餘分片出現 `IntegrityError: objects_objectdb … db_home_id` 的連鎖，受害者
  模組（`test_stat_breakdown`、`test_subject_ages` 等）單獨執行皆綠，只在重新
  混合的分片裡才失敗，且無法在本機以子集重現。

因此最終採用的規則是「只切不混」：每個舊分片（或舊行程清單）依原本的標籤順序
切成連續片段，片段之間不交換模組，每個新分片都是某個舊分片的連續子序列，
`server` 保持套件標籤完整。這保留了原本已綠的相鄰關係與 import 順序，並直接
對應「不要把會互相衝突的測試混在一起」的要求。

**成本模型改用「跨兩輪的最差實測」**：run 41303367823 的 runner 對 CPU 密集的
遊戲模擬測試比前一輪慢約 2 倍（同一組 `EncounterCalibrationTests` 的兩個測試
在快池是 132.9 秒 + 64.0 秒，在慢池是 235.4 秒 + 139.4 秒），因此每個測試的權重
取兩輪的較大值，分片上限也以該慢池的單位表示：瀏覽器清單 160 秒、evennia
makespan 200 秒、top-level 分片 170 秒。這讓兩種池都能落在 6 分鐘內（快池約
一半時間，慢池約 230-280 秒的 job）。

**結果（本日最終版）：**

- 瀏覽器：20 → **78 個分片**（156 個行程清單），最重清單 192 秒（上限 160 秒
  加上合併相鄰片段所致）、預測最重 job 272 秒（4.5 分鐘）；標籤維持方法層級
  （590 個方法各屬恰好一個清單），每個清單都是目前清單的連續子序列。含
  `test_repaint_budget` 這類效能預算測試的清單優先配到最輕的夥伴，其餘清單
  才依負載「最重配最輕」；配對只決定哪兩個清單共用 runner，不影響內容。
- **每個行程清單都必須含有至少一個 `covers_requirement` 標註的測試**：沒有標註
  的清單不會產生 evidence 檔，而 workflow 會在該分片「成功卻沒有 evidence」時
  直接讓步驟失敗——這正是 run 41300923484 裡 10 個瀏覽器分片紅燈的原因。切點
  因此只落在標註測試之後；若某片段仍無標註，就從鄰近片段移入一個最輕的標註
  測試（僅搬一個測試，其餘順序不動）。
- Evennia：10 → **37 個分片**，其中前端 evidence 套件（`web.webclient.tests`）
  為 `workers: 1` 的分片，其餘為 `workers: 4`；標籤維持**逐模組**
  （900 個已探索模組各屬恰好一個分片），每個分片都是舊分片標籤順序的連續子序列。
- **單一 class 是排程下限，過重就拆**：`--parallel 4` 不能把一個 class 拆給兩個
  worker，慢池下 `test_human_combat_calibration.EncounterCalibrationTests` 的兩個
  測試合計 375 秒（一個 worker 序列執行），整批分片無法壓到 6 分鐘內。該 class
  因此在同一個模組內拆成「共用的 fixture mixin ＋ 兩個測試類別」，讓兩個 pass
  落到不同 worker；測試、斷言與標註完全未變，模組的所有權也沒有變動。
- **Top-level 也分片**：原本單一 `top-level` 工作近兩輪為 1,371 秒與 820 秒
  （使用者另觀察到一輪超過 20 分鐘仍在跑）。新增 `.github/top-level-shards.json`
  （**11 個分片**，80 個 `tests/` 模組各屬恰好一個），workflow 以 matrix 執行
  `coverage run -m unittest --durations 0 <labels>`，每個分片有自己的
  `coverage-top-level-shard-N*` 與 `evidence.top-level-shard-N.jsonl`；gate 的
  完整性迴圈、證據串接與 coverage combine 同步改為逐分片。初步切法把會自己啟動
  子行程或 Chromium 的重模組（`test_map_image_capture`、`test_evennia_test_guard`、
  前端工具鏈與地圖作者模組）各自隔離，其餘 80 個模組依測試數平分成三份；每個
  分片同樣保證至少一個標註測試，`--durations 0` 讓下一輪能用實測值再平衡。
- **分片把隱藏的啟動依賴翻出來**：`tests/test_creation_parity_contract.py` 與
  `tests/test_map_runtime_contract.py` 在單一 job 裡是靠較早被 discover 的模組
  （`tests/test_command_docs.py`、`tests/test_contrib_matrix.py`）先把 Django
  settings 設定好才能 import 遊戲模組；拆成獨立分片後它們的 import 鏈
  （`evennia.contrib.grid.wilderness`）直接失敗。兩者已改用文件化的
  top-level bootstrap（`os.environ.setdefault("DJANGO_SETTINGS_MODULE",
  "server.conf.settings")` + `django.setup()` + `evennia._init()`），單獨執行
  16 項測試已綠。其餘 9 個頂層模組同樣在 import 遊戲碼但沒有 bootstrap；它們在
  目前這個切法下綠燈，後續若再重切應優先補上同樣的 bootstrap。
- manifest 新增 `workers` 欄位，workflow 以 `matrix.workers` 決定 `--parallel`
  （原本以分片名稱字串 `webclient-evidence` 判斷，拆出多個 evidence 分片後
  會回到 4 個 worker 並重新造成 Vitest/build 的 oversubscription）。
- 取捨：每個行程清單都要付一次共享伺服器冷啟動（實測中位數 51.8 秒）、約
  80 秒的瀏覽器 job 前置，以及 top-level 每個分片約 40 秒的工具鏈前置，因此
  切得越細，runner 總分鐘數越高（144 個瀏覽器清單的冷啟動約 7,500 秒，舊版
  40 個清單約 2,500 秒）。換得的是每個分片負載低、對 1.67 倍慢 runner 仍有
  餘裕，且在慢 runner 上不易觸發超時類的 flake。
- **editor service suite 移出 preflight**：原先 `preflight` 內嵌的
  `tools/map-editor` pytest 步驟，其成敗與 Evennia／browser／top-level 分片
  毫無關係，卻因為位於共同前置而讓 editor 套件的失敗短路掉後面 128 個工作
  （其中 126 個是分片工作）；這個耦合本身就是缺陷，把它獨立成 `map-editor`
  工作（`needs: preflight`，`gate` 的 `needs` 一併加上它）後，無關的套件不再
  決定分片能不能跑，editor suite 仍是 `gate` 的前置（它失敗就是整個 run 紅），
  附帶效果是關鍵路徑上的 `preflight` 縮短（所有分片都在等它）。新工作只需
  checkout、uv 與釘住的 Python：editor 自己的 project/lock 會把
  `packages/map-core` 當路徑相依解掉，而 suite 刻意用 scrubbed `PATH` 啟動服務
  並斷言「前端未建置」的 503 路徑，因此不裝 Node/pnpm、也不建置前端。
  `preflight` 仍保有 map-core 套件測試與 `tools.contract_gate manifests
  contracts` 等真正的共用契約。
- 工作數：1 preflight + 1 map-editor + 37 evennia + 78 browser + 11 top-level +
  1 frontend + 1 gate = 130。若後續要把工作數壓回來，可考慮先在 job 前置階段
  預先啟動共享執行環境（harness 的 `_boot_until_ready` 會沿用既有 runtime）或
  只建置該分片需要的前端 bundle，兩者都能讓清單上限放寬而不犧牲 6 分鐘預算。

本次重平衡只改 manifest 標籤分配、`workers` 欄位與本文件，未改動任何測試、
斷言、worker 數以外的設定、超時或預算。推送後的 CI 執行是唯一驗收：每個分片
的**完整 job 時長**（含前置與上傳，即 GitHub 顯示的 job 時間）必須 ≤ 6 分鐘。

實測結果（以 GitHub job 時間為準，非本地推測）：

| 執行 | 提交 | 分片工作 | 超過 360 秒 | 最慢分片工作 | 其他工作 |
|---|---|---:|---:|---|---|
| `41305471250` | `3c7f00eb` | 126 | 0 | 311 秒 | 兩個頂層分片缺 Django bootstrap 而紅 |
| `41307019044` | `edfff8ca` | 126 | 0 | 317 秒（`evennia` `webclient-26`，`workers: 1`） | preflight 122 秒、frontend 217 秒、gate 57 秒，全綠 |
| `41308349284` | `9407416d` | 126 | 0 | 328 秒（`evennia` `webclient-24`，`workers: 1`） | preflight 58 秒、map-editor 105 秒、frontend 255 秒、gate 59 秒，全綠 |

`41305471250` 的兩個失敗分片由 `edfff8ca` 修掉（top-level 的 settings bootstrap），
下一輪 `41307019044` 全綠且仍在預算內。`41308349284` 是 editor suite 移出
preflight 後的驗收：`map-editor` 自成一個工作（105 秒，遠低於 6 分鐘預算），
而所有分片都在等的 `preflight` 由 122 秒縮到 58 秒。

### 2026-11-03：逐格幾何成本與每測試世界收斂，37 → 46 個 Evennia 分片

CI run 41605121589 的 37 個 evennia 分片工作有 8 個超過 6 分鐘（其餘皆在
360 秒內，最接近者為 shard 9 的 357 秒）：

| 分片 | job 時長 | 測試執行時間 | 主因 |
|---|---:|---:|---|
| `maps-32` | 5,975 s | 5,887 s | `test_wilderness_population_species` 兩個 method 各 2,805/2,789 秒 |
| `maps-30` | 2,683 s | 2,601 s | `test_monster_provisioning`／`test_runtime_adoption` 共 15 個 method 超過 150 秒 |
| `webclient-35` | 1,427 s | 1,355 s | `test_area_map` 每個 method 約 95 秒 |
| `webclient-34` | 1,320 s | 1,239 s | `test_local_map.test_wilderness` 每個 method 約 135 秒 |
| `quests-16` | 1,188 s | 1,108 s | `test_species_hunt_acceptance` 六個 method 143–385 秒 |
| `maps-28` | 1,175 s | 1,090 s | `test_editor_final_yaml_adoption` 四個 method 164–402 秒 |
| `commands-19` | 669 s | 585 s | `test_scene_flavor_service` 三個 method 135–174 秒 |
| `maps-31` | 536 s | 469 s | `test_wilderness_geography_contract` 四個 method 82–246 秒 |

`--durations 0` 的每測試輸出指向三個成本來源，全部與斷言無關：

1. **逐格多邊形判定**：`is_land_cell` 每個 cell 都重跑 750 頂點的多邊形
   even-odd 掃描（本機實測約 189 µs/cell）；provider 的
   `is_valid_wilderness_cell` 另外每次重建並雜湊 60 筆 registry 內容
   （約 31 µs/call）。任何列舉 region window 的程式因此是 10⁶ 級成本。
2. **每個 method 重付整個世界**：`sync_test_settlements(全部 gate 目的地)`
   會在 setUp 物化 60 張地圖（本機冷啟動 40 秒、暖機 10.6 秒）；只站在
   一兩個 gate 的 local_map／area_map／scene_flavor 測試也付整張世界。
3. **單一 class 是排程下限**：`test_bootstrap` 的兩個 17/24-method class
   各 535／532 秒；`test_editor_final_yaml_adoption` 與
   `test_runtime_adoption` 各只有一個 class，4 個 worker 幫不上忙。

修正（標籤擁有權、斷言與 worker 數以外的設定均未改動）：

- `elosern_map_core.terrain`：`is_land_cell` 改讀每列的 land X 區間；區間由
  同一多邊形規則建一次並快取，`mainland_row_intervals` 成為該表的裁切視圖。
  全 frame 7.29M 格的 `is_land_cell` 由約 23 分鐘降到 2.2 秒；
  `is_valid_wilderness_cell` 由 31 µs 降到 1.25 µs。
- `world/maps/wilderness_provider._footprint_union`：published registry 的
  快取鍵改為 (registry, entries) 的 identity（快取值保留兩者，id 不會被回收
  後誤命中），由 28.9 µs 降到 0.24 µs；純 mapping 的測試 patch 仍以內容為鍵。
- `ServiceContentIsolation` 的世界與內部空間收斂升為 `setUpTestData`；會拆掉
  並重建 authored interiors 的三個 class（learning exchange、crown watch、
  hospitality）以 `converge_world_per_test = True` 保留逐 method 收斂。
- 只宣告測試真正讀到的地圖：local_map gateway／disclosure 與 area_map 用
  capital + 被隱藏點入口所在的地圖（皆由 registry 推導），scene_flavor 用
  它選中的 anchor 那一張。
- `test_editor_final_yaml_adoption` 的 moved-node 契約仍要求完整世界基準
  （「收斂後不新增也不刪除任何 room／exit」），因此這兩個 method 的 class
  fixture 仍物化全部 60 張地圖，只把兩個 method 拆成獨立 class 讓它們落在
  不同 worker 並行；拒絕案例不寫入任何資料，只有它把 fixture 收斂到
  interiors 所在與點入口的 settlement（scope 由 bundle 的 map id 推導）。
- `test_runtime_adoption` 拆成「bundle 發布／拒絕」與「同步失敗回滾」兩個
  class，`test_bootstrap` 拆成 Grid／Anchor／Bridging／Startup 與 Wilderness
  的 GateProvisioning／Resync／其餘，讓 4 個 worker 有足夠的排程單位。

**分片結果：37 → 40**。維持「只切不混」：每個新分片都是舊清單的連續子序列，
`server` 套件標籤完整，每個模組仍只有一個擁有者。

| 舊分片 | 新分片 | 內容（連續切片） |
|---|---|---|
| `maps-28` | `maps-28` / `maps-29` / `maps-30` | `altoria_capital`+輕量 bootstrap ／ 新增 `test_bootstrap_sync`（四個整世界 class）／ `city_*`+`editor_final_yaml_adoption`；`geography_source`…`interior_sources` 移到 `maps-31` |
| `maps-30` | `maps-33` / `maps-34` | `monster_provisioning`…`room_art_metadata` ／ `runtime_adoption` |
| `webclient-38`（舊 `webclient-35`） | `webclient-39` / `webclient-40` / `webclient-41` / `webclient-42` | `test_area_map` ／ `test_world_map_measurement` ／ `test_world_map_transport`+`test_world_map` ／ 其餘 12 個 presentation 模組 |
| `maps-30`（editor） | `maps-30` / `maps-31` | moved-node ／ moved-location + 拒絕案例 |
| 其餘 | 內容不變 | 僅重新編號 |

本機驗收（24 核心參考機，`--parallel 4`，`--keepdb`）：

| 模組 | 本輪 CI（合計／最慢 method） | 修正後本機 |
|---|---:|---:|
| `test_wilderness_population_species` | 5,887 s／2,805 s | 最慢 method 4.1 s |
| `test_monster_provisioning` + `test_species_hunt_acceptance` | 4,640 s／385 s | 24 tests 8.0 s／最慢 3.6 s |
| `test_wilderness_geography_contract` | 732 s／246 s | 最慢 method 2.0 s |
| `test_area_map` | 1,401 s／118 s | 46 tests 45.1 s／最慢 4.0 s |
| `test_local_map.test_wilderness` | 1,567 s／171 s | 最慢 method 3.8 s |
| `test_scene_flavor_service` | 449 s／174 s | 14 tests 13.6 s／最慢 9.0 s |
| `test_service_host_identity` | 726 s／99 s | 28 tests 25.2 s／最慢 2.2 s |
| `test_bootstrap` + `test_bootstrap_sync` | 1,235 s／207 s | 61 tests 80.8 s；同步模組單獨 20 tests 46.3 s／最慢 44.2 s |
| `test_editor_final_yaml_adoption` | 972 s／402 s | 4 tests 78.6 s／最慢 30.7 s |
| `test_runtime_adoption` | 1,513 s／319 s | 7 tests（兩個 class）85.7 s／最慢 18.9 s |

唯一驗收仍是下一次 CI：每個分片的**完整 job 時長**必須 ≤ 6 分鐘。本輪的
最慢分片工作（`webclient-24`／`-26` 這類 `workers: 1` 的 evidence 分片）
未被本次改動影響。

**第一次推送（run 41669564625，40 個分片）的 CI 觀測**：所有分片皆綠，8 個原本
超時的分片全部落到 360 秒內，只剩兩個仍超標：

| 分片 | job 時長 | run-step | 原因 |
|---|---:|---:|---|
| `maps-28` | 435 s | 405 s | `test_bootstrap` 內四個「整世界」class 因 discovery 順序被排在同一批 worker，出現序列化 |
| `webclient-38`（舊 `webclient-35`） | 385 s | 355 s | `test_area_map` 與 15 個 presentation 模組共用一個 job |

因此再切：把 `test_bootstrap` 的整世界 class 抽成獨立模組
`world/maps/tests/test_bootstrap_sync.py`（共用的推導常數與 cooperative base
放進不參與 discovery 的 `_bootstrap_fixtures` 模組），讓四個 45 秒級 class 在
同一個 job 的四個 worker 上並行；再把 `webclient-38` 切成 `test_area_map`
單獨一個分片與其餘 15 個模組一個分片。`test_bootstrap_sync` 的本機 wall 為
20 tests 46.3 秒（最慢 44.2 秒）。

第二次推送（run 41673963246，42 個分片）全綠，只剩 `webclient-40`（15 個
presentation 模組）449 秒；同一輪的 `maps-35` 352 秒、`webclient-38` 340 秒
都在預算內。該 15 個模組的本機 wall 只有約 90 秒，其中三個 `test_world_map*`
模組單獨執行就要 58.7 秒（22 tests）：`test_world_map_measurement` 的
`setUpClass` 會用真實大陸幾何組出 representative／worst／1 km 三份 payload
（worst 有 145,800 條 trail run），這是量測契約本身的成本，不是重複的 fixture。
因此三個模組再拆：`test_world_map_measurement` 單獨一個分片，
`test_world_map_transport`+`test_world_map` 一個分片，其餘 12 個面板模組一個
分片。

第三次推送（run 41677298637，43 個分片）全綠，仍有兩個分片超過 360 秒：
`maps-30`（城市模組 + editor）443 秒、`webclient-40`（三個 world-map 模組）
389 秒。這一輪也顯示同一份內容在不同 runner 上的變異可達 30%：`maps-35`
在三次執行分別是 295／352／215 秒。最終調整把兩個「單一 class 就是排程下限」
的案例各自隔離：

- `maps-30` 只留 editor 的 moved-node 案例，`maps-31` 放 moved-location 與
  拒絕案例；三個城市模組移回 `maps-28`。editor 的 fixture 只先播種
  interiors 所在與點入口的 settlement（lookup 用），每個 moved 契約 method
  自己在讀取 baseline **之前**以未裁切的 `runtime.synchronize()` 收斂完整
  世界，因此「收斂後不新增／不刪除」仍是 whole-candidate 斷言，被測的
  synchronize 也沒有被裁切。兩個 moved 案例因此不再在同一台 runner 上同時
  跑兩次冷啟動的整世界收斂；本機三個模組合跑 4 tests 78.9 秒（moved-location
  單獨 71.5 秒）。
- `webclient-40` 只留 `test_world_map_measurement`；它單一 class 的
  `setUpClass` 就是 58.7 秒本機成本，拆無可拆。

第四次推送（run 41682627873，45 個分片）全綠，`maps-31`（editor moved
cases）降到 356 秒，但仍有 `maps-35`（runtime adoption）與 `webclient-41`
（world-map measurement）388 秒。前者是兩個 class 各自付一次完整世界 fixture
（同一台 runner 上兩次冷啟動互相拖慢），因此把 `MapWorldAdoptionTests` 與
`MapWorldSynchronizationRollbackTests` 拆成兩個模組、各自一個分片；後者是
單一 class 的 `setUpClass` 成本，`workers` 降為 1，避免 4 份 DB clone 與
Evennia import 與該 class 競爭 CPU。

第五次推送（run 41685640231，46 個分片）全綠，只剩下兩個單一 class 的分片
超過 360 秒：`webclient-42`（world-map measurement）387 秒與 `maps-36`
（runtime adoption rollback）366 秒。兩者的 `workers` 都降為 1（單一 class
不需要平行 worker，少掉 DB clone 與重複 import 對完整世界收斂的競爭）。

第六次推送（run 41687556193）是驗收：46 個 evennia 分片全部成功，最慢的
`commands-19` 為 351 秒、其次 `webclient-40` 347 秒，**0 個分片超過 360 秒**。

最終 46 個分片，仍是「只切不混」。editor 的 moved 案例、runtime 的 rollback
案例與 world-map measurement 是已知的不可再分割下限：若後續 CI 的慢 runner
仍讓它們逼近上限，只能從 `sync_grid` 的 ORM 成本或 world-map payload 的
組裝成本下手，而不是再切分片。`test_world_map_measurement` 的 57 秒本機成本來自
`representative_payload()` 第一次組裝真實大陸／district 世界（`one_km` 與
`worst` 各不到 1 秒）。

editor 的完整世界契約維持不變：兩個 moved-node method 仍各自在完整世界上
做一次真實收斂（本機 4 tests 78.6 秒），不靠縮小 fixture 換時間。

### 2026-11-05：以 run 42025038878 的每測試實測重新打包，46 → 60 個 Evennia 分片、78 → 84 個瀏覽器分片

CI run 42025038878（`bc43efa6`，138 個工作）的實測顯示 5 個 evennia 分片與 4 個
瀏覽器分片超過 360 秒，其中最嚴重的是 `maps-34` 的 **2,506 秒**。該輪 log 的
`--durations 0` 與瀏覽器 driver 逐 method 輸出即為本次重新打包的唯一輸入。

**evennia 的實際成本結構**：`maps-34` 的 2,506 秒並非分片分配問題，而是三個
「跨 reload/re-entry 的 cleared one-shot site」測試本身：

| 測試 | CI 時間 |
|---|---:|
| `test_monster_sites.MonsterSiteLifecycleTests.test_a_one_shot_site_stays_cleared_across_advances_and_re_entry` | 2,117.8 s |
| `test_content_expansion_sites.TransferStationEncounterTests.test_a_cleared_one_shot_site_stays_cleared_across_reload_settlement_read_and_acceptance` | 1,065.0 s |
| `test_content_expansion_sites.HighTierBossEncounterTests.test_defeating_the_crocodile_boss_leaves_the_site_cleared_across_reload_revisit_read_and_acceptance` | 903.0 s |

三者都以「清空一次性 site 後整天 skip」為主體。本機量測（把 86,400 秒的 advance
暫改成 600 秒）顯示 `population_lifecycle._settle_population_at` 在 600 秒內被
呼叫 15 次（邊界序列 60, 90, 120, 180, 240, 270, 300, …，即 30 至 60 秒一次），
一個 method 約 7 秒；換算整天 skip 為 2,880 次邊界結算，CI 上每次約 0.7 秒，
正好對上 2,000 秒級的實測。這是**每次邊界結算的成本**與**30 秒一次的 blocked
recovery 重試節奏**相乘的結果，不是分片能解決的問題。

因此本次**只切不混**地重新分配，並保留這個已知下限：

- evennia：46 → **60 個分片**。每個超過 700 秒序列成本的分片切成連續片段
  （`maps-34` 切成 4 個，`webclient-21`、`rules-6`、`rules-13`、`maps-28`、
  `webclient-40`、`rules-12`、`rules-2`、`rules-4`、`quests-15`、`rules-11`、
  `quests-16`、`commands-19`、`rules-1`、`maps-37` 各切成 2 至 3 個），標籤順序
  不交換，`server` 套件標籤維持完整。
- browser：78 → **84 個分片**。逐 method 實測換算後，把 `packed-13`（501 秒）、
  `packed-56`（388 秒）、`packed-61`（1,174 秒）、`packed-51`（722 秒）的
  `files_a`／`files_b` 各自切成等量連續片段並重新配對，讓每個清單的 method
  總和降到 90 秒附近；`test_browser_dream_artwork`（單一 method 286.6 秒）與
  `test_browser_exploration_actions…test_safe_wait_until_dawn`（209.0 秒）是單一
  method 的下限，只能各自獨佔一個清單。

兩個 manifest 通過 `tests.test_evennia_test_optimization_contract` 與
`tests.test_quality_gate_contract`（索引唯一且排序、每個標籤恰好一個擁有者、
每個清單非空）。

**尚未解決的下限**：`maps-34` 的兩個新分片仍會各花約 2,000 秒，因為它們各自帶著
一個上述的整天-skip 測試；`packed-56` 的分片仍約 290 + 固定開銷秒。要讓它們進入
6 分鐘預算，下一步必須降低 `_settle_population_at` 的每次成本或讓 blocked
recovery 不要在每 30 秒重試，再把 `day`-skip 的邊界數從 2,880 降下來；繼續切
分片不會有幫助。

### 2026-11-05：run 42037867084 的實測——長尾是每 job 的瀏覽器安裝，不是測試

run 42037867084（`0311a245`）的 84 個瀏覽器 job 中，測試步驟本身的中位數是 205 秒、
最大值 295 秒；但**整個 job 的中位數是 295 秒、最大值 1,548 秒**，差額全部落在
`Install Chromium and Firefox for browser acceptance`：

| 步驟 | 一般 job | 被節流的 job |
|---|---:|---:|
| Check out repository workspace A/B | 6–15 s | 6–15 s |
| Sync locked environment（兩個 workspace） | 3–5 s | 3–5 s |
| Build Vue dist in browser workspaces | 21–31 s | 21–31 s |
| **Install Chromium and Firefox** | **29 s** | **1,253–1,320 s** |
| Run browser shard | 132–295 s | 130–223 s |

84 個 job 同時向 apt 與 Playwright CDN 各拉一份 Chromium、Firefox、
chrome-headless-shell 與約 30 個系統套件；被節流的 job 就把 30 秒變成 20 分鐘。
同一段時間內 `top-level-5` 連 `Check out repository` 都花了 30 分鐘，是同一波
網路壅塞。這才是「一次 run 跑一小時」的原因；在這個前提下切更多分片只會更嚴重。

**修正**：`browser` job 改在 `mcr.microsoft.com/playwright/python:v1.62.0-noble`
容器內執行——瀏覽器與系統相依套件都已在映像內，job 只跑一次
`Verify the container's browser bundle`（真啟動 chromium 與 firefox，約 1 秒）。
並為 `evennia`、`browser`、`top-level` 三個 matrix job 加上 `timeout-minutes: 20`：
病態 runner 會明確失敗，不會再把整條 run 拖過一小時。

**整天 skip 的成本**：`world/maps/population_lifecycle.settle_population_lifecycle`
在一次 86,400 秒的 skip 裡走過 **1,921 個邊界**（本機 385 秒、CI 約 1,362 秒），
平均每次邊界 0.17 秒；節奏由 `monster_activity` 的 30 秒移動刻決定，換算一天
2,880 次。三個驗收測試原本都以「整天」為跨度，但 `monster-site-placement` 的需求
只要求「in-game clock advances」，因此改為 **4 小時**（可恢復 camp 的 1 小時視窗
的 4 倍：同一次 advance 會讓可恢復的站恢復、一次性站仍清空）。斷言一條未減，
單一測試從 1,362 秒降到約 250 秒。

**重新打包**：evennia 60 → **72** 個分片、browser 84 → **89** 個分片，兩者都以
本次 run 的實測 `Run … shard` 步驟時間為依據（evennia 只切 > 240 秒、browser 只切
> 250 秒的分片），且保證兩個行程清單都非空、沒有任何標籤遺失。

**單一模組無法再切分時的處理**：`tests.test_evennia_test_optimization_contract` 只
接受模組或套件目錄作為標籤，因此一個 600 秒以上的單一模組不能靠調整清單拆開。這兩個
模組改為套件：

| 原模組 | 套件 | 拆出的模組 |
|---|---|---|
| `world.maps.tests.test_monster_sites`（615 秒） | `test_monster_sites/` | `test_site_population`、`test_site_clearing`、`test_site_without_world`、`test_site_row_vocabulary` |
| `web.webclient.presentation.tests.test_area_map`（641 秒） | `test_area_map/` | `test_wilderness_window`、`test_wilderness_content`、`test_grid_area`、`test_room_graph_area`、`test_area_map_dispatch`、`test_fog_and_bounds` |
| `world.rules.tests.test_map_knowledge_integration`（733 秒） | `test_map_knowledge_integration/` | `test_recording`、`test_non_recording`、`test_pruning` |

三者共用一個 `_support` 模組（非 `test*.py`，因此不被探索）：`test_monster_sites`
把原本 1,677 行的單一測試類別拆成 `_MonsterSiteFixture` 基底加上兩個測試子類別，
`test_area_map` 的荒野類別同樣拆成 `_WildernessFixture` 與兩個子類別；其餘類別原本
就各自獨立，依類別搬移即可。`test_map_knowledge_integration` 的 16 個 seam 旅程
同樣拆成 `_MapKnowledgeFixture` 加兩個子類別。evennia 分片因此由 72 增至 **81**，
新增的九個分片各自只承載一個模組。本機整包量測：`test_monster_sites` 43 個測試
126 秒、`test_area_map` 58 個測試 131 秒、`test_map_knowledge_integration` 22 個
測試 77 秒（原本分別是單一 job 615／641／733 秒）。

第一版的荒野對半分（14／12）在 CI 上仍留下 376 秒的分片：每個荒野旅程的固定成本
約 27 秒（fixture 主導），所以 14 個測試就是 376 秒。實際切法是依「每個分片 ≤ 9
個旅程」重新平衡成 9／9／8。

### 2026-11-06：每個分片都必須執行到至少一個帶需求聲明的測試

`gate` job 的完整性檢查要求每個分片都有非空的
`evidence.<owner>-shard-<index>.jsonl`，而該檔案只由 `covers_requirement` 裝飾器
在測試成功時寫入。因此一個只裝有「不宣稱任何需求」的冒煙模組的分片永遠產不出
證據：`test_content_expansion_sites` 與 `test_movement_roundtrip` 各自獨占的分片
（原本的 53 與 57）在 42179475404 首次讓整個矩陣全綠時才被檢查到。兩者分別併入
`maps-28`（44）與 `rules-3`（4），分片數由 81 減為 **79**，索引重新編號為 0–78；
兩個合併後的分片在本機分別通過並各自產出 2.7 KB／2.9 KB 的證據檔。

### 2026-11-12：怪物棲地資料成長下的啟動、物化與世界建構成本

怪物內容（species／placement／activity）把
`ECOLOGY_ZONE_REGISTRY` 從 9 帶到 155 個 zone（合計 74,500 個 zone 矩形格）、
`WeightedComposition` 從 19 帶到 617。run 43140279866（commit `2756bfee`）對照
最後一次全綠的 42935733556（`1c5b4791`），CI 實測顯示三個成本來源同時放大：

| 觀測（全部取自 CI log） | 綠（`1c5b4791`） | 紅（`2756bfee`） |
|---|---:|---:|
| 瀏覽器 `harness timing … ready=` | 20–50 s | 170–200 s |
| `LocalMapPerGateFootprintTests` 每個 method | ~9 s | ~195 s |
| `RoadNetworkAdoptionTests`（只做 adoption） | 56 s | 233 s |
| evennia 各分片 `Ran` 總和 | 7,068 s | 11,505 s |
| browser 各分片 `Ran` 總和 | 15,195 s | 28,614 s |

**三個來源與修法（皆不改斷言、不改旗標擁有權）：**

1. **主大陸 ring 每次重驗**：`is_on_mainland` 每次都重新驗證 750 個頂點
   （單次 adoption 內 12,932 次呼叫）。改以身分（不是值）快取驗證後的 ring：
   `(False, 0)` 與 `(0, 0)` 相等，值快取會讓畸形邊界得到別人的驗證結果。附上
   「暖快取後仍拒絕 bool／float 頂點」的回歸測試。
2. **逐格的聚落排除**：`eligible_birth_cells` 對每個候選格掃過所有聚落 footprint
   （74,500 格 × 聚落 × footprint）。改為一次建出排除集合，逐格只做一次成員查詢。
3. **每個 zone 各付一次世界掃描**：`_provision_wilderness_script` 逐 zone 呼叫
   `initialize_zone`，每個 zone 各付一次 surface snapshot 與（每個 wave）兩次全體
   presence 掃描。新增 `initialize_zones`：整批共用一次 rollback surface、一次
   tick 投影的 presence 讀取、一次 protected cell 讀取，每 wave 只寫一次座標註冊，
   並把本批新建立的個體加進共用 presence。`initialize_zone` 保留為單 zone 入口並
   委派；`commit_population_wave` 仍讀即時狀態與即時計數。

**測試的物化宣告延伸到初始族群**：initial population 由 authored zone 決定，
一個只宣告兩張地圖的測試或瀏覽器 journey 仍會初始化全部 155 個 zone 的 1,065 隻
個體。現在 `sync_test_wilderness(settlement_ids)` 與瀏覽器啟動 hook 都以
`world.tests.geography_fixture.zones_for_settlements(...)` 把宣告換算成「這些聚落
所在區域的 zone」，並且世界把實際初始化的 zone 集合記錄在
`population_zone_scope`；後續啟動驗證的就是那份記錄（production 記錄完整 roster，
行為不變；記錄缺失時視為完整 roster）。`require_initialized_population` 因此對
bounded 世界仍然嚴格：缺一個記錄的 zone 或多一個不在記錄內的 zone 都是同一個
named refusal。

**驗收方式**：`--durations 0`（evennia）與 driver 的 method／boundary 欄位
（browser）本來就會把每測試實測寫進 job log；重新打包仍以那一輪 CI 的 job 時長為
唯一依據，預算維持每分片 ≤ 6 分鐘（硬限 20 分鐘的 job timeout）。

**第二批：把「不是受測物」的初始族群移出固定成本。** 同一輪 CI 的
`--durations 0` 顯示剩下來的長尾幾乎都是「單一個測試跑一次全量 provisioning」：

| 分片 | 單一測試（run 43164896133 實測） |
|---|---|
| 51 `test_limbo_room` | `test_at_server_start_renames_legacy_room_and_bridges_it` 354 s |
| 47 `test_bootstrap_sync` | `test_sync_wilderness_is_idempotent` 368 s、`test_sync_wilderness_provisions_one_gate_exit_per_authored_gate` 359 s |
| 45 `test_bootstrap_grid`（分片 821 s） | 四個 `at_server_start` 測試 199–258 s |
| 32 `test_exits`（分片 391 s） | `WildernessGatewayExitTests` 單一類別 335 s |

四個修法都只改變「測試宣告了多大的世界」，沒有放寬任何斷言：

1. **空 scope 是合法的已初始化世界**：`sync_test_wilderness` 與
   `selected_startup_settlements` 接受顯式 `zone_keys`，`()` 表示「這份合約
   不主張任何環境族群」。seed、時間線、activity 記錄與 `population_zone_scope`
   仍會寫入，`require_initialized_population` 仍以記錄為準，因此「多一個 zone」
   與「少一個 zone」仍是同一個 named refusal。
2. **守門、啟動與 lore mirror 合約宣告空 scope**：這些合約的受測物是 gate
   exit、房間數與 mirror，不是族群。本機實測 `test_limbo_room` 的啟動測試
   354 → 53 秒、`test_bootstrap_sync` 的兩個全量 pass 368／359 → 44／44 秒、
   `test_bootstrap_grid` 的兩個啟動測試 258／246 → 11／11 秒（整模組 26 個測試
   175 秒，原本單一分片 821 秒）。
3. **`test_exits` 拆成共用 fixture 加兩個類別**：同一類別的測試只能序列執行，
   335 秒的類別是多核心也吃不到的牆。
4. **`test_map_knowledge_integration` 的 fixture 只宣告自己那張地圖**：原本同步
   所有帶城門的聚落（162 個 zone），但每個 seam 旅程只走其中一張地圖的兩個
   gate；改成先解析 `live_map_key()` 再宣告它。

`test_bootstrap_grid` 仍刻意保留一個真正的主張：
`test_fresh_wilderness_provisioning_initializes_population_once` 走 production
全量 roster 路徑（本機 46 秒、CI 199 秒），因為「一次寫入全量族群」正是它的
受測物。
