# Elosern 霧落 — 現代化遊戲 UI 重設計（v2）

設計角色：Game UI Designer。目標：從「文字 MUD」轉向「現代單機 RPG 網頁駕駛艙」，
保留全部既有可操作功能與 deterministic 契約，用「情境化 HUD + 多個頁面/抽屜」取代單一畫面。

本檔是功能清單與資訊架構（IA）的權威盤點；實作見 `index.html`。

---

## 0. 設計原則（依 Game-UI 教義）

1. **情境化 HUD（contextual show/hide）**：每個遊戲狀態只顯示「此刻需要」的表面，
   0.3–0.5s 淡入淡出；不顯示的絕對隱藏（不是灰掉）。→ 回應用戶「戰鬥時不需要地圖」。
2. **單一事實來源**：所有清單（技能、狀態、任務、同伴、圖鑑）消費既有 payload schema，
   不新造資料；未解鎖技能「藏而不禁用」（hide, do not disable）。
3. **敘事仍是主角**：中樞為量寬限制的 serif 敘流；HUD 錨在四角/邊緣，中央留給情境回饋。
4. **指令列是 MUD 的心跳，永遠可見**：底部長駐 + 快捷詞 + 歷史；圖形選單是「加速」，不是「取代」。
5. **多層選單明確、可決定性回退**：每個選單都有父層；Escape 回父層；子選單開啟不重建。
6. **可達性**：狀態絕不只靠顏色（圖示＋符號＋數值）；focus 環、reduced-motion、
   色盲模式、字級縮放、音量分層；敘述/狀態區 live region。
7. **成人向、誠實**：親密狀態區塊可折疊、用語節制；圖版缺失用真誠占位，離線仍可玩。

---

## 1. 完整功能盤點（依「是否可操作」與「屬於哪個表面」分組）

### 1.1 長駐 HUD（世界模式，情境化顯示）
| 元素 | 資料 | 可操作 | 說明 |
|---|---|---|---|
| 角色卡 | 名稱/種族(亞種)/職業/階級(魔法 rank F..主宰)、肖像 | 點開「狀態」全表 | 左上錨點 |
| 生命/魔力/耐力 | hp/mp/sp（current/max）| 點開狀態 | 組合條＋數字＋受傷拖尾bar；低血暈影 |
| 計數器 | guild_merit | — | 顯示功績 |
| 靜態屬性 | atk_phys/agility/defense/magic_power（真值＋技能乘數有效值）| 狀態 | hover 顯示乘數來源 |
| 錢包 | 銅（整數）| — | 分群格式 3,240 銅 |
| 公會階級 | rank F–S | 點開任務 | 徽記 |
| 偽裝旗標 | disguise_active | — | 「目前有偽裝」 |
| 條件行 | 26 buff/debuff + 16 派生修正（severity 五級）| 點開狀態 | icon+持續秒；溢出顯示 6–8 + 「…」 |
| 局部地圖/小地圖 | 節點網格（current/已訪/未訪/記憶）；fog-of-war | 點開全地圖 | **戰鬥時隱藏** |
| 目標追蹤 | 1–3 追蹤任務目標＋路徑 | 點開任務 | 右下角；戰鬥收縮為純目標 |
| 同伴快帶 | ≤4 同伴（肖像/HP/狀態/羈絆 stage）| 點開同伴面板 | **無專面板＝目前缺口，補上** |
| 通知 toast | 事件（升級/任務完成/解鎖/金錢）| 點掉 | 優先級隊列，max 4 |
| 美術背景/頭像 | 場景背景 + 3:4 頭像 | 點開全圖 | 離線＝真誠占位 |
| 指令列 | 文字解析器（全部 58 指令 + 動態出口）| 永遠 | 長駐底部；快捷詞；歷史；`/` 不再需要 |

### 1.2 行動甲板（action dock）— 情境互斥，**多層選單**
五個互斥 surface。核心是多層導航模型：`根 → 子選單 → (再)子選單 → 提交 payload`。

**A. 探索 dock**（世界、非戰鬥）
- 根：`移動 / 查看 / 互動 / 任務 / 物品`
  - **移動**：出口清單（含命名門、動態 `南門/wilderness/…`），帶 current-node 舊位置守衛 → `explore.move`
  - **查看**：看房間 / 看活物（顯示其攻/敏/防/魔/命）/ 看物件 → `explore.look`
  - **互動**：目標清單 → 每目標「伺服器授權」行為：腳本關鍵字鈕、自由對話（借用指令列）、`engage` 開戰、`party_invite/leave`（同伴）、跳轉服務（公會/商店，只開子選單不提交）
  - **任務/物品**：進入服務 surface
- **AI 建議卡**：`known_action` 一鍵卡（move/cast/talk，參數伺服器預填）＋ 可清除

**B. 戰鬥 dock**（戰鬥中）— `root = 攻擊 / 技能 / 道具(暫灰) / 防禦(暫灰) / 逃跑 / 投降(二次確認)`
- **技能**＝關鍵多層選單：`分類 → 群組(元素/性愛線) → 技能 → (威力 1/4..4) → 目標(代號/範圍)`
  - 每個技能 descriptor：cost、target_spec、enabled/reason_code/reason_message、valid_target_ids、shorthands、freeform_scales
  - 目標：party(aN) vs foes(eN)；SINGLE 單選 / AREA 空格多選 / `all-enemies/all-allies/all`
  - 投降→`services-confirm` 二次確認 → `combat.forfeit`
- **參戰框架**：party＋foes，每人 token/姓名/HP條/state(active|fled|knocked_out|defeated)/threat

**C. 角色 dock**（唯讀全表）：traits、主動/被動（分類分群）、裝備、偽裝「真值 vs 顯示」、公會、錢包、背景
**D. 服務 surface**（由探索 進入）：
- **公會**：註冊 / 任務板(接取) / 任務紀錄(回報·放棄[確認]·詳情) / 功·階(考核)
- **商店**：庫存(買/賣+數量表單、時段門) / 餘額
- **背包**：錢包 + 物品清單（web 只讀；拿/丟走指令）
**E. 建角 dock/畫面**：預設卡 / 自訂(名稱+雙成年年齡+種族/亞種+六條有界軸) / AI 構想提案；草稿還原；欄位驗證 live region

### 1.3 抽屜 / 覆蓋層（不常用→隱藏，打開才占版面）
| 抽屜 | 內容 | 多層? |
|---|---|---|
| **技能書** | 主動/被動分頁；分類→群組；搜尋；位階/成本；`可用於戰鬥外` 徽記；鍛鍊級數 | 2 層 |
| **同伴/隊伍** | 4 格：肖像/名/HP/狀態/羈絆 stage(7 階,數值隱藏)/關係 flavor；邀請/解散；「跟丟」提示 | — |
| **背包/裝備** | 紙娃娃(武器主/副·甲·飾) + 物品格；稀有度邊框；比較 tooltip；排序/篩選/搜尋 | — |
| **商店** | 買/賣分頁；分類；買賣價；數量；餘額；貴物確認 | 分頁 |
| **任務** | 追蹤/進行中/完成/失敗；目標 checklist(計數 3/10)；報酬(銅/物品/經驗)；追蹤/放棄[確認] | 分類 |
| **圖鑑** | 8 大分類；**僅已發現**；分類→卡（未知不洩露存在性） | 2 層 |
| **狀態** | 全 8 trait 行、全條件(持續)、偽裝對照、裝備、錢包 | — |
| **親密狀態**（狀態內可折疊）| arousal(5)/wetness(5)/shame(5)/exposure(5)/climax_phase(4)/climax_today/10部位敏感/處女旗 | — |
| **全地圖** | 分層(地形/路口/地點/標記/任務/霧)、縮放/平移、圖例 | — |
| **設定** | 音訊(分層音量) / 顯示(字級) / 可達(色盲模式、motion 減量、文字背景) / 輸入(重映射) | 分類 |
| **說明** | 分類索引→條目→子條目（深度不定） | 多層 |
| **全圖** | 場景/頭像全螢幕（art_focus 跟焦） | — |

### 1.4 可操作功能 → 表面 對應（速查）
- 移動/尋路(前往) → 探索·移動 + 小地圖
- 看/說/動作/耳語/拿/丟/給 → 探索·查看/互動 + 快捷詞 + 指令列
- 交談(talk 關鍵詞/自由)、邀請/解散同伴 → 探索·互動 + 同伴面板
- 休息/睡眠/等待 → 探索（安全門：戰鬥中禁）
- 開戰/投降/戰鬥動作/cast → 戰鬥 dock + 快捷 + 指令列
- 公會 9 項+考核 → 服務·公會
- 商店 3 項 + 背包 → 服務·商店/背包
- 圖鑑(lore) → 圖鑑抽屜（web 面板，非動詞提交）
- 建角(預設/自訂/構想) → 建角畫面
- 帳戶/連線(OOC/登出/傳訊/密碼/選項/樣式/暱稱/色彩…) → 設定/說明 + 指令列（少用，藏於設定）
- 管理(art 家族) / 建造(@tel/@open/地圖) → **不進玩家主 UI**，保留 telnet（Developer/Builder 權限）
- 24 個 Web WS 具名 action（combat./guild./shop./creation./explore./options.）→ 對應上列 surface 提交

### 1.5 不進主 UI（保留文字面）
Developer `art status/run/retry/requeue`；Builder `@teleport/@open/地圖`；Evennia 預設管理動詞。
理由：罕用、權限隔離、避免污染玩家 HUD。

---

## 2. 資訊架構（IA）：模式 × 表面 可見性矩陣

| 表面 | 探索 | 戰鬥 | 對話 | 選單開啟 | 建角 |
|---|---|---|---|---|---|
| 敘事(中樞) | ● 故事 | ● 戰鬥日誌 | ● 對話聚焦 | 變暗 | 隱藏 |
| 生命條(左上) | ● | ● 醒目 | ● | 變暗 | 隱藏 |
| 條件行 | ● | ● | ● | 變暗 | 隱藏 |
| **小地圖** | ● | **隱藏** | ● | 隱藏 | 隱藏 |
| **同伴快帶** | ● | ●(參戰隊列) | ● | 隱藏 | 隱藏 |
| **目標追蹤** | ● | 收縮目標 | ● | 隱藏 | 隱藏 |
| 行動甲板 | 探索 | 戰鬥 | 探索（同探索）※ | — | 建角 |
| 快捷詞+指令列 | ● | ●(cast) | ● | 變暗 | 隱藏 |
| 美術背景 | ● 氛圍 | ● 變暗 | 頭像聚焦 | — | — |

**戰鬥差異（關鍵 UX）**：小地圖消失；同伴快帶變成「參戰 party/foes 框架」；
行動甲板變戰鬥選單；敘流變戰鬥日誌；生命條醒目＋低血暈影；目標追蹤收縮為純目標。

> ※ 2026-09-06 修訂（webclient-align-11-dialogue-ux）：對話模式的「對話選項」
> 行動甲板鏡像已移除——對話選項只在敘事對話框呈現（含 `結束對話` 出口列），
> 行動甲板在對話期間維持普通探索形式。

---

## 3. 多層選單狀態機（keyboard + pointer 雙路徑）

```
探索dock:
  根[移動|查看|互動|任務|物品]
    └ 移動 → 出口清單 → (選) 提交 explore.move
    └ 互動 → 目標清單 → 目標行為[腳本|自由|engage|邀請|解散|跳服務]
                └ 自由對話 → 借用指令列(輸入→提交, 被鎖則留欄)
戰鬥dock:
  根[攻擊|技能|道具|防禦|逃跑|投降]
    └ 技能 → 分類 → 群組 → 技能 → [威力(僅master)] → 目標[token/範圍] → 提交 cast
    └ 投降 → 二次確認 → combat.forfeit
Escape 一律回父層；子選單開啟不重建父選單；改動進行中抑制提交。
```

---

## 4. 技能書 payload 契約（直接複用，不新增資料）
- 非戰鬥：`character` 面板 `actives`/`passives`，結構 `[{category,label,groups:[{group,label,skills:[{key,label}]}]}]`
- 戰鬥：`context_actions.skills`（category→groups→skill descriptor，v5 欄位）
- 8 分類（固定順序）：元素魔法(8元素) / 武技 / 強化 / 天賦 / 移動 / 神之秘法 / 特殊 / 性愛行為(7線)
- `usable_out_of_combat` → 顯示 `戰鬥外可施放` 徽記；`cost.mp/sp`；位階由 MP 帶派生（學徒..主宰）
- 未解鎖 sex act **完全不出現**（hide not disable）

---

## 5. 可達性清單（實作必達）
- [x] 狀態/資源：圖示＋符號＋數值（不只顏色）
- [x] focus 環（非純色）、disabled 行仍可 focus 讀 reason_message
- [x] `prefers-reduced-motion` 全停用動畫
- [x] 字級 scale（A-/A/A+）可於任何選單改
- [x] 色盲模式（色＋形狀雙編碼：buff▲/debuff▽/team 形狀）
- [x] live region（敘流、通知、驗證）
- [x] 音量分層 + 重要音效有視覺替代

## 6. 開放問題
1. 親密狀態預設展開或收折？（建議：收折，且僅「狀態」內可展開）
2. 小地圖戰鬥時是完全隱藏，還是縮為「敵我方位」簡版？（建議：完全隱藏，參戰框架已含方位）
3. 快捷詞要固定一組，還是隨 context 換（探索=看/走/拿/說，戰鬥=cast/flee/defend）？（建議：隨 context 換）

---

## 7. Map layouts — 局部地圖的兩種版面（design note, English）

*Pre-wave design for `openspec/changes/webclient-map-02-layout-variants`. The visual draft (`index.html`) implements both layouts; this section records why the split looks the way it does.*

### 7.1 Two data formats, two layouts — never player-selected

The world ships **two fundamentally different map formats**, and the layout is a pure function of the payload, mirroring the Evennia source model:

| payload layer | Evennia source | coordinates | layout |
|---|---|---|---|
| `grid` | xyzgrid contrib (`XYZNode.X/Y`, 8-way links) | validated world coordinates | 網格圖 (coordinate lattice) |
| `wilderness` | wilderness contrib (8 direction exits over provider coords) | validated world coordinates | 網格圖 |
| `interior` / `instance` | plain Evennia room/exit graph | none (node `x` is a layout index, not a place) | 連線圖 (radial graph) |

`isCoordinateLayer(layer) = layer ∈ {grid, wilderness}` is the one resolver; island and overlay read the same resolved value, so divergence is impossible. The layout's formal names follow Evennia — `grid` for the xyzgrid coordinate space, `wilderness` for the Wilderness contrib's — and the Chinese word 荒野 is a usage example of the coordinate space only, never a code or spec name. There is **no player-facing layout control, preference, or storage of any kind** — a player who stands in a coordinate space sees the lattice, and one who stands in a room cluster sees the graph. (An earlier revision of this note specified a three-segment manual switch; the owner ruled it out: the format follows the world, not taste.) The closed se...

Both layouts share one renderer contract: identical marker states (current seal-red r8/r9 + pin > visited filled > unvisited hollow > gold landmark; seen-not-visited = gold at 0.5 opacity), identical edge colours/widths (solid = traversable, dashed = blocked exit), identical labels and palette. What differs is **what the geometry is allowed to claim**:

| | 連線圖 (graph) | 網格圖 (lattice) |
|---|---|---|
| Claims | **connectivity only** — which nodes are reachable from where | **relative position** — nodes sit at committed coordinates, current node is the origin, `+y = 北` |
| Position meaning | decorative; pixel angles mean nothing | meaningful; lattice pitch = 1 coordinate cell |
| Header mark | none — a graph asserts no axis | `北↑ 東→` (valid only where axes are drawn) |
| Readout line | `連線圖` (names the drawing) | `坐標空間` (names the drawing) |
| Fog vignette | knowledge edge (not terrain) | knowledge edge (not terrain) |

Neither readout ever shows a bearing, compass angle, distance, or coordinate figure. Lattice node placement is driven by committed coordinates/exit directions, never by graph-layer pixel angles.

### 7.2 Remote-known places: edge direction markers (lattice only)

A coordinate payload can remember places **outside the drawn visual range** (the presenter puts them in `remembered` with their real coordinates — e.g. a trade city on the eastern plains or an underground cavern seen before). The lattice SHALL plot every node whose coordinates fall inside the drawn extent at its true cell, and SHALL render each remembered node outside the extent as an **edge direction marker**: a memory diamond (gold ring if landmark) sitting on the canvas's marker-safe border, positioned where the **ray from the current node through the raw coordinate delta** (`dx = remote.x − current.x`, `dy = remote.y − current.y`) crosses that border.

The direction contract is testable and strict:

- The ray is computed from **raw, pre-compression coordinates** — never from `col`/`row` ranks (rank compression preserves order, not ratios; `(100,1)` must not render as 45°). A pure helper (`remoteDirection(current, remote) → { dx, dy, octant }`) owns this; `+y = 北`, eight octants with explicit half-open sector bounds.
- The marker conveys **direction only**: no distance figure, no angle, no coordinate readout. A faint ray segment from the current node to the marker is allowed as a pure visual (it encodes direction, which the data backs).
- Markers are a bounded decoration layer (payload caps at 64 nodes): deterministic ordering, per-edge slotting so markers never overlap each other, the current node, or the axes. They carry no travel action.
- **Accessibility floor:** on the lattice variant, the island's remembered list is replaced by the named edge direction markers on the canvas border, with an untruncated visually-hidden text alternative mirror (`已知的地圖出入口`) providing the complete reading path for assistive technology; on the graph variant (`interior`/`instance`), the island keeps the bounded, non-focusable remembered list. On the full-map overlay, each marker carries its place name as visible text and as its accessible name.
- Coordinate-free payloads never get markers — their `x` is a layout index, and an interior remembered node stays list-only.

### 7.3 Coordinate semantics: two meanings, one field

The payload's node `x`/`y` carries two distinct semantics, and the spec must say so: under `grid`/`wilderness` they are **validated world coordinates** (from `XYMap` / the wilderness provider) and may drive relative-direction geometry; under `interior`/`instance` they are **renderer-local layout values** and MUST NEVER be read as direction, distance, or place. The old blanket ban on bearing figures stands — it now reads: no numeric angle/distance/coordinate readout anywhere, and direction geometry only from validated coordinates.

### 7.4 Draft demo device and accessibility

The static draft shows both layouts through a **demo fixture selector** (`.demofx`, bottom-left, dashed border, legend `展示資料（非遊戲控制）`): it swaps which committed fixture payload the mock renders (`無座標房間 payload` = interior graph; `wilderness 座標 payload` = wilderness lattice) and stores nothing. It is review chrome, visually distinct from game HUD, and never ships; the layout still comes from the payload's `layer` through the same resolver the product uses. The variant SVGs carry `role="img"` + per-variant `aria-label` (`局部地圖（連線圖）` / `局部地圖（網格圖）`). Lattice dot-field and axis cross are tuned to be plainly visible (`#3a3344` at 0.85 dot fill-opacity, 1.5px axis at 0.65) — the lattice's geometry is its claim, so it must not be invisible; implementation waves pin their presence and contrast.

```mermaid
flowchart LR
  P["local_map payload<br/>layer 欄位"] --> R{"isCoordinateLayer?<br/>grid / wilderness"}
  R -->|yes| G["網格圖 lattice<br/>真實座標落點＋邊緣方位標記"]
  R -->|no (interior/instance)| F["連線圖 graph<br/>BFS 環狀拓撲"]
  G --> S["單一解析值同步島嶼＋全地圖"]
  F --> S
```
