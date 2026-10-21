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
| 聚落道路的物理公尺座標與路段長度 | `world/maps/altoria_capital.py::PHYSICAL_POSITIONS`、`world/maps/village_ciaran.py::PHYSICAL_POSITIONS`、`world/maps/sparse_graph.py` |
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
- 聚落節點同時有「目前 xyzgrid 座標」與「作者宣告的絕對公尺位置」。路段長度一律
  取物理位置（含彎道折線全長）；羅盤方向仍由邏輯座標決定，所以座標搬遷不會悄悄
  改寫出口方位。`PHYSICAL_POSITIONS` 以座標為鍵，必須與 `NODE_IDS` 的格位完全
  一致，否則 `build_sparse_graph()` 在寫入前拒絕。
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
- 每位成員的速度 = 地形速度 × 該成員出發展疲勞階段的精確 `foot_speed_scale`；
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
- **恰好在抵達時歸零**是允許的：整趟照常提交，並由外部疲勞契約在目的地轉為強制
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
與 `test_altoria_capital.py` 釘值。
