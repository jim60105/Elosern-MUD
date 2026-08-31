# Evennia 測試效能報告

本報告記錄了 `optimize-evennia-testing` 變更的測量基準。各項時間皆為參考機器的觀測值，並非跨平台的絕對限制。一般性的優化指導原則請參見「[Evennia 測試效能優化指南](evennia-testing-guide)」。

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

原始備註中結合 `:memory:` 與 `--keepdb` 的建議已被拒絕：記憶體資料庫無法在行程結束後繼續留存。原始備註中無條件啟用平行 worker 的建議同樣被拒絕，除非證據、覆蓋率、資源隔離與重複計時皆證明具備同等效果。

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

預期效果：戰鬥分片的 19 分 09 秒拆分至約 5 個平行行程清單（各約 4 至 5 分鐘），使瀏覽器關鍵路徑降至約 5 至 6 分鐘，並與 Evennia 機器分片一同將整體品質閘門總耗時壓在 10 分鐘以內。

**初次 CI 觀測（分支 `feat/pack-browser-ci-shards`）：**

- Run 31951553328：每個瀏覽器分片在步驟開始時皆以 `syntax error near unexpected token '&&'` 失敗，原因是 run-step 的常面文字區塊在每個背景子 shell 內的 `&&` 前放置了換行。透過將每個 `(cd w-a && ...)` / `(cd w-b && ...)` 子 shell 摺疊至單一行完成修復（防護等待、覆蓋率複製、證據串接與雙狀態檢查皆維持不變）。
- Run 31951788668：11 個瀏覽器分片中有 10 個通過；分片 4（創角，每個旅程皆啟動專用伺服器）有一項測試失敗，錯誤為 `twisted.internet.error.CannotListenError: Couldn't listen on 127.0.0.1:44951: [Errno 98] Address already in use`。這是測試架構記載的短期連接埠釋放後綁定競爭（`allocate_ports` 在 portal 綁定該連接埠前先行關閉其 socket）：在單一執行器上同時配置與啟動兩個測試架構行程時，競爭成為真實問題。此修復**修正了該變更「不改動 harness」的非目標**：當診斷顯示連接埠衝突標記（`CannotListenError` / `Address already in use`）時，`ManagedServer.start()` 現會以全新的執行期重試最多兩次，因此同級行程搶佔釋放的連接埠不再導致整個分片失敗。兩項快速單元測試鎖定了重試機制（衝突時使用新執行期，預算耗盡時拋出例外）。
- Run 31952671241：11 個瀏覽器分片中有 10 個通過；分片 11（art-harness-shell）的 `test_image_load_failure_shows_fallback_without_refetch` 失敗，出現 `AssertionError: 2 != 1`，場景圖像 URL 被請求了兩次。這暴露了潛在的客戶端競爭條件：在 `img.src = url` 與圖像的 `error` 事件之間重新算繪的快照更新為相同 URL 建立了第二個 `<img>`，違反了「不得重複擷取」的需求。雙行程的 CPU 競爭擴大了該時間窗口。美術面板現依 URL 將進行中的圖像元素暫存（`pendingImages`），並在重新算繪時重用它們而非發出重複請求；該元素僅在 `load` 或 `error` 時移出快取。一項 Node 契約測試鎖定了此重用行為。
- Run 31953234137：分片 10（art）的兩項全螢幕檢視測試失敗。上述重用引入了陳舊閉包回歸：附加至重用元素的接聽器閉包捕獲了 `renderScene` 的 `model` *參數*（首次算繪的快照），因此 `model.sceneFullView = true` 修改了失效的物件。該參數更名為 `panelModel`，使接聽器讀取外掛層級的 `model`，而 `render()` 始終保持其為最新狀態；完整的 `test_browser_art` 模組（14 項測試）再次全數通過。進一步 CI 觀察後的重新平衡仍維持為清單編輯加上契約測試。
