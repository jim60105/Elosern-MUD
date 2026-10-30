# 距離制旅行與地形耗時

本頁記錄 `charge-distance-based-travel` 引進的「單位與所有權契約」（world-map-scale
design §10）。它說明移動耗時如何由作者宣告的物理幾何與地形速度算出，以及在什麼
情況下一次移動會退回明確的「非距離連接器」固定耗時。改動移動、地圖幾何或疲勞速度
縮放前請先讀本頁。

`integrate-fatigue-aware-traversal` 在同一契約上加上分段積分：耗時不再只取出發
當下的最慢速度，而是在每個成員疲勞門檻與地形邊界重算，並在出發前拒絕「到不了」
的行程。

## 所有權

| Concern | Owner |
| --- | --- |
| 地形速度表、區域→地形對照、單次向上取整的耗時計算 | `world/rules/travel_cost.py`、`world/rules/rulebook/movement.yaml` |
| 聚落道路的公尺座標、作者宣告的羅盤方位與路段長度 | `content/maps/settlements/<map_id>.yaml`、`packages/map-core/elosern_map_core/sparse.py` |
| 荒野格距、區域判定 | `world/maps/wilderness_provider.py`（`WILDERNESS_KM_PER_CELL`、`region_for_coordinates`） |
| 城門絕對公尺幾何與聚落錨點轉換 | `world/maps/wilderness_destination.py::settlement_world_position_m`、`gate_approach_distance_m` |
| 移動前預檢與單一充能入口 | `world/rules/travel_cost.py::preflight_movement_cost`、`world/rules/movement.py::charge_movement` |
| 移動結算邊界（交易、補償） | `world/rules/movement_settlement.py::settle_movement` |
| 出口種類與成功後流程 | `typeclasses/exits.py::{MovementCostMixin, WildernessGateExit, WildernessReturnExit}` |

`world/rules` 只計算時間；`world/maps` 只宣告幾何與房間生命週期；出口只負責
預檢、移動與呼叫共用完成函式。沒有任何出口內嵌 `get_world_clock().advance()`。

## 單位契約

- 速度以「整數公尺／小時」宣告，因此單一路段的秒數在取整前是精確分數：
  settlement／road 4500、open ground 3000、woodland 2000、mountain trail 1500。
  1.25 m/s = 4500 m/h；3 km/h = 3000 m/h。
- 聚落節點座標本身就是聚落區域座標系中的整數公尺位置（`x` 向東、`y` 向北）；
  `z` 仍是邏輯地圖／圖層鍵，不是海拔。路段長度取兩端公尺座標的歐氏距離（含作者
  宣告的彎道折線全長）。羅盤方位由每條有向道路作者宣告，因為不規則的公尺佈局幾
  乎不會與軸對齊；由原始座標差推導會把所有主要街道誤判為斜向。聚落文件中的
  `nodes` 與 `roads` 必須描述同一組節點，否則圖形建構在寫入前拒絕。
  節點鍵使用 `south_gate`、`quay` 等穩定英文識別字；節點的 `key` 則是
  南門、碼頭埠等中文顯示名稱。節點與道路數量以
  `content/maps/settlements/<map_id>.yaml` 的宣告為準。
- 荒野距離 = 歐氏格距 × 宣告格距（`WILDERNESS_KM_PER_CELL × 1000` 公尺；自
  `rescale-wilderness-geography` 起為每格 1 公里）。斜向不是一格：`(1,1)` 格的
  斜向距離是 `√2 × 格距`。地形取兩端較慢者，因此同一條邊雙向同價。荒野格是否
  可通行由 `world.maps.wilderness_provider.is_valid_wilderness_cell` 單一判定
  （外框、大陸多邊形、封閉山脊、內陸水道與錨點足跡）。
- 城門跨越只算一段：由聚落錨點轉換
  `world_anchor_center + local_position - local_anchor_position` 得到城門的絕對
  公尺位置，再量到外部 approach cell 的中心。進城與出城共用同一段，不另外加整格
  荒野步或第二次市街步。
- 取整只發生一次：`plan_traversal()` 把整條折線的所有「等速段」以精確 `Fraction`
  相加後向上取整。兩段各 0.4 秒的物理腿合計 1 秒，不會變成 2 秒；次秒級的疲勞
  門檻也不會被逐段取整掉。提交的整數秒與 `WorldClock` 的疲勞結算完全相同。
- 耗時是積分而非單點取樣：每一段的速度 = 地形速度 × 該成員在該段開始時的外出
  疲勞縮放（`outgoing_foot_speed_scale`）。段與段之間只以「某位成員跨過疲勞門檻」
  或「地形改變」切分，不是逐公尺或逐秒模擬；換速度只影響剩下的距離。
- 多段地形以 `plan_traversal(((distance_m, terrain), ...), members)` 表示；目前
  作者資料的單一路段仍只傳入一段，未來彎道／混合地形宣告不需要改計算核心。

## 隊伍速度

- 出發時在來源房間以 `follow_scope` 取得「旅遊者 + 跟隨者」一次，該名單同時用於
  速度、充能實體與補償；遠端隊員不計入。
- `follow_scope` 仍是唯一的來源在場判定；`party.travel_scope()` 是「旅遊者 +
  跟隨者」的正式組合入口，`travel_cost.source_present_members()` 只是它的轉接。
  移動結算的快照也重用預檢記錄裡的同一組成員。
- 每位成員的速度 = 地形速度 × 該成員出發時疲勞階段的精確 `foot_speed_scale`；
  隊伍速度取最慢者。沒有隊伍人數懲罰，也不平均成員速度。被附身時，指揮者本體
  也在名單內。
- 完全沒有精神儲備狀態的實體（尚未初始化）以基礎速度旅行；狀態損毀或禁止旅行
  （自願／強制睡眠）在預檢即拒絕，不會被當成健康速度計價。

## 出發前拒絕（預先耗盡）

`world/rules/travel_cost.py::refuse_pre_destination_depletion` 與
`plan_traversal()` 共用同一條規則：

- 若任一位在場成員會在**抵達前**耗盡精神儲備，預檢就以
  `pre_destination_depletion` 拒絕；時鐘、位置、精神儲備、地圖知識、任務狀態與
  荒野房間都不會被寫入，也不會建立未命名的中途房間或自動休息。
- **恰好在抵達時歸零**仍可提交：整趟照常結算，並由外部疲勞契約在目的地轉為強制
  沉睡；下一次出發會因沉睡被拒絕。
- 不是只有距離邊：明確的非距離連接器（一般房門、副本門、虛境橋）用作者宣告的
  `command_defaults` 秒數做同一項判定。強制沉睡的拒絕更早，且在飛行豁免之前，
  所以飛行擁有者也不能帶走沉睡成員。
- 預檢只讀狀態、不寫入；`MovementPreflightRefused.reason` 是穩定的拒絕碼。

## 預檢與充能

每個出口在 `at_traverse` 內、任何寫入之前呼叫 `preflight_movement_cost(...)`：

1. 解析 `TraversalCost`（距離、地形、秒數、出發時隊伍名單）並放入同步的
   context 堆疊；`charge_movement` 只消費這筆不可變記錄，事後房間被荒野池回收也
   不會改變價格。
2. 具距離的戶外血緣（聚落道路、荒野步、城門跨越）若解析不到幾何，預檢回報
   `UNRESOLVED`，出口乾淨拒絕：不移動、不推進時鐘、不記錄地圖知識。
3. 明確的非距離連接器（虛境橋、副本門、兩個無道路的一般房間）分類為
   `NON_DISTANCE`，使用 `rulebook/clock.yaml` 的 `command_defaults` 作者耗時。
   `wilderness_move` 只保留為飛行豁免的荒野情境鍵與此類連接器的作者耗時，不再是
   荒野步的秒數權威：真正的荒野步若解析不到物理邊會拋出而非猜測。
4. 實際充能走 `WorldClock.advance_bounded(...)`：一趟超過時鐘單次上限
   （`MAX_ADVANCE_SECONDS`＝86,400 秒）的已提交行程，會在**同一個移動交易**內
   切成數個有界內部推進，並以「整趟視窗」建立一次前推進快照；整趟只取整一次，
   不會被截成單日上限。任一段失敗都會還原整個視窗，而不是只還原最後一段。
5. 移動結算的 `MovementSnapshot` 以預檢記錄的成員與 `window_seconds`（已提交秒數）
   建立快照視窗；晚到的失敗會還原全部旅客的地點、精神儲備、睡眠姿態、地圖知識、
   任務介面與時鐘。

荒野斜向步另有轉角規則：任一正交鄰格不可通行（越界或錨點足跡格）時拒絕斜向，
`wilderness_neighbor`、canonical resolver 與小地圖三者共用同一條規則，因此在任何
消費者眼中都不會出現「看得到卻走不過去」的邊。

## 驗證

```sh
uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  world.rules.tests.test_movement world.rules.tests.test_movement_settlement \
  world.rules.tests.test_clock world.rules.tests.test_party_follow_possession \
  world.rules.tests.test_party_time_settlement
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate integrate-fatigue-aware-traversal --strict
```

`<file>` 只需包含 `MUD_TEST_SETTINGS=1`。取整、地形速度與格距的純計算測試位於
`world/rules/tests/test_movement.py`（含分段積分、次秒門檻與預先耗盡拒絕）；
疲勞感知的長途視窗與回滾在 `test_movement_settlement.py` 與 `test_clock.py`；
隊伍耗時與實際城門／荒野路段秒數由 `test_party_time_settlement.py`、
`test_party_follow_possession.py`、`world/maps/tests/test_city_movement_cost.py`
與 `test_altoria_capital.py`／`test_settlement_reload.py` 的機制斷言（路段長度即端點距離、耗時與距離成正比）。

## 視野（ground sight 與遠方目擊）

荒野視野與移動耗時共用同一組區域判定，但**不是**同一張地形表：移動分類看步速，
視野分類看遮蔽與展望。這個子系統只計算是什麼、看得到什麼，不儲存任何狀態，
也不點亮任何分區。

| Concern | Owner |
| --- | --- |
| 光相（時段）、視野半徑列、突出度加成、展望加成、暮光與聚落足跡係數、聚落匿名側影 | `world/rules/rulebook/sight.yaml` |
| 純計算：`light_phase`、`ground_radius`、`in_ground_disc`、`distant_markers` | `world/rules/sight.py` |
| 區域→視野地形列的委派、格距 | `world/maps/wilderness_provider.py::sight_terrain_class`、`WILDERNESS_KM_PER_CELL` |
| 每格突出度階級 | `world/maps/elevation.py::prominence_tier` |
| 分區地標、聚落錨點與荒野入口足跡 | `world/lore/map_districts.py`、`world/lore/anchors.py`、`WILDERNESS_ENTRY_REGISTRY` |

- **光相**：`day`、`dusk`、`night`、`dawn`；邊界小時屬於「由它開始」的相位，
  暮光與黎明讀 `twilight` 列。這些相位與 `clock.yaml` 的 daypart 錨點無關。
- **地面半徑** `r = max(terrain + prominence_bonus[tier], vantage 或 0)`。林地與
  深林的樹冠把突出度階級壓成 0（展望地標仍然有效），半徑上限為 8 格。
- **視野圓盤**：`dx² + dy² ≤ (r + 0.5)²`；半徑 0 只涵蓋自己所在的格。沒有遮蔽線
  計算，也不做山口判定。
- **遠方目擊**：分區地標可宣告 `sight_km`／`light_km`／`silhouette_zh`；非隱藏的
  聚落由足跡面積（佔用格數的平方根）乘上作者係數自動成為來源，夜間是光源。
  隱藏地點（精靈村落、副本）永遠不是來源；來源必須在當前可見距離內、且在即時
  視野外；站在樹冠地形上完全看不到側影。同一地點的來源合併成一個標記，白天與
  夜間的可見距離取各自最大值，所以「只有白天範圍的地標」不會蓋掉聚落的夜間燈火。
- **標記內容**固定為 `{bearing, distance_km, silhouette_zh, name}`：16 方位
  （zh-TW，北起順時針，半區間平手取順時針側）、距離四捨五入到 5 公里（平手向上）、
  當前相位的側影，以及**只有在該分區已為角色點亮時**才出現的地標名稱。來源格、
  目標 ID 與分區鍵都不會序列化。
- **只讀**：每次讀取都重算、不推進時鐘。即時視野與遠方目擊本身仍不寫入任何狀態；
  只有下述「地面揭露」會把已經站過的格子的最大視野半徑持久化。

驗證：`uv run --locked python -m unittest world.rules.tests.test_sight`。這些測試
一律注入合成政策、合成來源與固定時數，斷言機制（相位邊界、半徑組合與上限、
圓盤邊緣、相位可見度、方位／距離平手、來源隱私與合併、政策拒絕），不綁定出貨
數值或文案；側影與地標文案由人工依設計文件審閱。

## 地圖知識與地面揭露

`world/rules/map_knowledge.py` 仍是角色 `map_knowledge` 的唯一寫入者；地面揭露只
新增一個窄入口，不新增第二份真相，也不儲存逐格的「已看見」點陣或燈光紀錄。

| Concern | Owner |
| --- | --- |
| 荒野單格觀測寫入（首次／最後 tick、最大 `sight`） | `world/rules/map_knowledge.py::record_ground_observation`、`record_arrival` |
| 抵達 seam | `typeclasses/exits.py::after_successful_movement`、`world/rules/party.py::_move_commander_body` |
| 明確跳過的單次終點觀測 | `world/rules/clock.py::WorldClock.advance` 的 `ground_observer` 輸入 |
| 跳過外層交易的觀測回滾面 | `continue_sleep` 的 `build_advance_snapshot_registry` 外層註冊 |
| 純揭露投影 | `world/rules/map_knowledge.py::revealed_in_bounds`、`is_revealed` |
| 分區歸屬與點亮判定 | `world/maps/district_partition.py::district_at`、`world/lore/map_districts.py::landmark_node_ids` |

### 何時寫入

- **抵達**：`record_arrival` 仍只在既有的成功移動 seam 呼叫。荒野抵達時，以實際
  抵達後的時鐘 tick 與 `world/rules/sight.py::ground_radius_at` 算出的當格半徑寫入
  該格；`first_seen_tick` 保留第一次、`last_seen_tick` 前進、`sight` 取
  `max(舊值, 新半徑)`，永不下降。非荒野的 `grid:`／`room:` 仍只記 `{first,last}`。
- **附身**：知識永遠屬於授權的 `PlayerCharacter`（指揮者）。附身時移動與跳過都只
  寫指揮者的紀錄；被附身的同伴不會產生自己的歷史。觀測格是指揮者實際所在的荒野
  格，不會借用遠端本體的另一格。
- **明確跳過**：`WorldClock.advance` 的 `ground_observer=(角色, 格)` 是關鍵字專用
  輸入，只允許 `AdvanceSource.SKIP`；其他來源帶此參數會在寫入前拒絕。真正的觀測
  發生在階段結算與 tick 持久化之後、同一交易結束之前，只對正數區間執行一次。
  `advance_wait`（等待／休息）與 `continue_sleep`（自願睡眠、全隊睡眠、強制睡眠
  續行）只在實際結算秒數大於零時傳入觀察者；零秒、重播、拒絕、讀取、重連與傳送
  都不會觀測。強制睡眠的每個已提交邊界區間由 `continue_sleep` 各自觀測一次，沒有
  額外的上層或階段脈衝觀測。
- **半徑取樣**：終點觀測以結算後的 tick 對應的光相重新計算半徑；抵達與跳過共用
  `record_ground_observation`，因此同一格在同一天稍晚的較大視野會單調提升
  `sight`。讀取失敗只留下診斷，不會因為觀測失敗而取消已完成的移動。
- **回滾**：觀測寫入在時鐘交易內。`advance` 自己的快照註冊與 `continue_sleep` 的
  外層快照註冊都包含該角色的 `map_knowledge`，所以階段、tick、收據或外層提交之後
  的失敗會同時還原資料庫列與 Attribute 快取；沒有通用的回滾日誌或第二套機制。

### 揭露投影（純讀）

- `revealed_in_bounds(character, bounds)` 回傳查詢矩形內的已揭露格集合；
  `is_revealed(character, cell)` 是同一投影的單格查詢。兩者都只讀，不寫紀錄、
  不推進時鐘、不建立燈光或點陣狀態，結果會裁剪到查詢與荒野外框。
- 先以**精確**的分區地標節點判定分區是否已點亮：只逐一檢查有限的地標 ID（`grid:`／
  `room:` 查 `visited`；`wild:` 只解碼該地標所在 chunk），不整個
  `parse_knowledge`。點亮的分區整區揭露。
- 其餘格由已儲存的觀測圓盤聯集揭露：只解碼與「查詢矩形外擴 8 格」相交的 chunk，
  對每個觀測以 `sight` 為半徑取 `in_ground_disc`，再裁剪回查詢。8 是
  `MAX_GROUND_SIGHT_RADIUS`，因此不存在能影響查詢的遠方觀測。
- 揭露只決定地形可見性：水域、阻擋與錨點足跡格可以是「已揭露但不可走」；隱藏
  地點／精靈村落的地點身分仍需精確 `has_visited`，即時實體另由族群視圖處理。
- **損壞處理**：信封／schema 無效時沒有可信的點亮集合，揭露為空且位元組保留；
  查詢選中的觀測 chunk 損壞時保留原紀錄、記錄診斷，丟棄圓盤聯集，只讓獨立可讀的
  精確地標歸屬揭露。

驗證：

```sh
uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  world.rules.tests.test_ground_reveal world.rules.tests.test_map_knowledge \
  world.rules.tests.test_map_knowledge_integration world.rules.tests.test_sight \
  world.rules.tests.test_clock world.rules.tests.test_sleep_receipt \
  world.rules.tests.test_party_follow_possession
```

測試以合成 schema-2 紀錄、合成分區歸屬與注入的半徑斷言機制（單調最大半徑、首次
保留、正數區間只觀測一次、排除路徑、兩層回滾、chunk 邊界聯集、點亮捷徑、損壞
回退），不釘住出貨資料或文案。
