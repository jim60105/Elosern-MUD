# 稱號系統 — 設計文件

**日期：** 2026-08-30
**狀態：** Approved
**範圍：** 以兩個稱號家族取代除役的魔法位階稱號帶：由規則謂詞授予的決定論固定稱
號，以及經玩家同意投票採納的 LLM 提案綽號；新增稱號冊 UI、複合綽號、以及 `title`
命令家族。本設計不依賴成長重設計的任何部分，只依賴 change
`magic-power-trait-demotion` 已先行移除 `magic_rank_title()` 與
`RANK_TITLE_REGISTRY`。

## 1. 背景與問題

目前唯一的稱號是顯示用的魔法位階帶（學徒→賢者），由 `magic_level` 計算。那個數
字在成長重設計後不再是成長計數器，稱號帶隨之除役。另一方面，遊戲裡有大量未被表
達的身份訊號：技能系譜鏈頂、怪物階層首殺、任務弧、公會位階、性里程碑。加上 LLM
層能為 EventLog 目睹之事命名。

設計目標是有安全性的風味文字。稱號是純顯示／lore 消耗品；決定論家族在全部 AI 服
務離線時照常運作；生成式家族在任何情況下都不能未經玩家明確同意寫入狀態。這正是
本專案對 `world/ai/` 的「僅提案」邊界，玩家是最後一道驗證閘。

## 2. 目標

- 兩個稱號家族共用同一條收藏 invariant：**只增不減、永不剝奪**。
- 固定稱號：registry 宣告、謂詞授予、寫入觸發事件的同一筆原子交易；AI 服務全離線
  時功能完整。
- AI 綽號：一次提案五個、驗證後取三個的同意投票；程式面過濾；永不與固定稱號或玩
  家已採納綽號相同。
- 複合綽號：固定部分與綽號部分同時被消費（「B級冒險者 風趣的旅人」），供顯示、
  appraisal 周邊散文與 LLM prompt 脈絡使用。
- 稱號冊是收集慾介面：每個固定稱號都可被發現，未解鎖者附作者撰寫的提示。

## 3. 非目標與前瞻縫隙

- **稱號不帶機械能力值效果。** 稱號只餵敘事與社交消費。（任務／NPC 條件日後可
  以*讀取*收藏；該前瞻縫隙屬資料讀取，不在本 change。）
- **不做稱號剝奪、到期，兩個槽位之外不做堆疊上限。**
- **不做 AI 內容審查管線。** 同意就是安全閥；程式只擋硬性碰撞與畸形格式。拒絕事件
  寫入 EventLog 讓 Director 軟學習，不做持久黑名單。
- **公會位階保持自己的軸。** 不併入稱號 registry 語意；每次位階升級只是同時多授予
  一個固定稱號（D3），固定槽可以展示它。

## 4. 決策總覽

| # | 決策 | 章節 |
|---|---|---|
| D1 | 只增收藏 + 兩個裝備槽 + 純函數合成 | §5 |
| D2 | 固定稱號：lore registry + EventLog planner 授予 | §6 |
| D3 | 公會位階升級授予該位階稱號 | §6.4 |
| D4 | 綽號投票：觸發、5 驗 3、同意、冷卻 | §7 |
| D5 | 複合綽號的消費分層（敘事對機械） | §8 |
| D6 | 稱號冊 + Telnet 等價 + 命令家族 | §9 |

## 5. D1 — 資料模型

持久狀態（玩家 typeclass 屬性；使用前全部先向 snapshot/restore 面處理器登記）：

```python
# db.title_collection — list[dict]，只增，順序 = 取得順序
{"kind": "fixed",    "key": "zombie_hunter_of_the_gutters",
 "granted_tick": 1234}
{"kind": "nickname", "display": "風趣的旅人",
 "origin_quote": "你在月舞酒館連贏三場嘴仗…",   # 投票時的「事蹟引用」
 "granted_tick": 2010}

# db.title_equipped — dict，複合綽號的兩個槽
{"fixed": "E級冒險者" or None, "nickname": <collection index or None>}
```

- 收藏條目以 `(kind, key|display)` 識別；固定 key 至多出現一次（重複授予靜默 no-op），
  綽號 display 在收藏內唯一，因為 D4 的驗證在採納當下就擋掉碰撞。
- `db.title_equipped["fixed"]` 存固定 key；`["nickname"]` 存收藏索引，所以重新裝備
  舊綽號是寫指標，不是複製。
- 兩個屬性在角色啟動時預設為空（`[]` 與 `{"fixed": None, "nickname": None}`）；屬
  性缺失的讀取與預設值等價。

`compose_epithet`（純函數，`world/rules/titles.py`）：

```python
def compose_epithet(fixed: str | None, nickname: str | None) -> str:
    parts = [p for p in (fixed, nickname) if p]
    return "　".join(parts)          # full-width space
```

固定在前、綽號在後，以全形空格連接，空槽部分省略，兩槽皆空回傳空字串。所有消費者
在空字串時退回角色本名。永不存合成後的副本；每次讀取即時合成。

## 6. D2 — 固定稱號：registry 與 EventLog 謂詞

### 6.1 Registry（`world/lore/titles.py`，frozen，冪等同步進 Scripts）

```python
@dataclass(frozen=True)
class FixedTitleDef:
    key: str                    # canonical id，covers_requirement 風格
    display_name_zh: str        # "屠龍者"
    category: TitleCategory     # COMBAT|SPELL|EXPLORE|GUILD|ROMANCE
    flavor_zh: str              # 解鎖後顯示的敘事散文
    hint_zh: str                # 未解鎖列的提示（作者決定含蓄度）
    predicate: TitlePredicate   # 宣告式家族 + 參數，見 6.2
```

Registry 載入驗證：key 唯一；`hint_zh` 非空（未解鎖列必須永遠可呈現）；謂詞只引用
存在的 registry 面（元素、怪物階層、任務 key、位階 key、性經驗類型）。

### 6.2 謂詞家族（逐筆內容列屬後續內容工作）

| 家族 | 謂詞參數 | 範例 |
|---|---|---|
| `lineage_complete` | 元素／武藝系譜的根 key | 火系鏈磨練至不滅鳳凰焰（`phoenix_eternal_flame`）見頂 |
| `mastery_owned` | 元素 key | 持有火焰精通（`fire_mastery`） |
| `first_kill_tier` | 怪物 threat tier | 首次擊殺 calamity 階 |
| `quest_completed` | 任務定義 key | 具名任務弧完成 |
| `guild_rank_reached` | 位階 key | 升級至 E 級（D3） |
| `sexual_experience` | `experience_types` 成員 | 記錄異種性愛 |
| `counter_threshold` | 性 lifetime 計數器 + n | 自慰次數 ≥ 30 |

### 6.3 授予路徑

一個 `title` EventLog planner（與任務 planner 並列登記）在行動的效果解析完成後掃
描 EventLog，評審待判謂詞（非 EventLog 的資料讀取沿用 `status_query` 的同一組讀取
輔助），暫存候選授予。規則層把 `title_collection` 寫入**觸發行動的同一筆原子交
易**；snapshot 面未登記就會在登記時拋例外（既有 invariant）。成功的授予推 OOB 通
知（「獲得稱號：屠龍者」），稱號冊的鎖定列隨之翻面。

謂詞重評審具冪性（收藏已含該 key 即跳過），因此暫存後被 rollback 的行動，在其事件
下次再現時自然重授予；沒有任何東西能被寫兩次。

### 6.4 D3 — 公會位階稱號

每個 `GUILD_RANK_REGISTRY` 列配對一個稱號（各階 display 由作者撰寫；F 級註冊本身
授予「F級冒險者」）。E→S 的授予搭 `settle_exam_outcome` 的升級交易（planner 看見升
級事件）；F 級搭 `register_guild_member` 的交易。重新註冊、分會移動、merit 變動都
不碰收藏。位階對 offers／考試的權威軸不變，稱號只是裝飾性同步。萬一未來出現降階
情境（目前不存在），也永不剝奪已入庫稱號（只增 invariant）。

## 7. D4 — AI 綽號投票

### 7.1 觸發與節流

- 觸發點只限敘事休息點，戰鬥結算中途絕不觸發：登出；世界時鐘日界且角色處於休息；
  公會考試通過；任務弧完成。每個觸發呼叫 `maybe_nominate(entity)`。
- 每個 entity 同時至多一個待決投票；已有待決時 `maybe_nominate` 靜默返回。
- 冷卻：投票被拒絕或逾期後，`NOMINATION_COOLDOWN_DAYS` 個日界（registry 常數，初
  值 2）抑制再提名。被採納的投票不觸發冷卻（下次提名反正要等下個觸發點）。
- 每個觸發點以既有 options service 的「結算內同步、有逾時上界」模式呼叫 LLM；任何
  失敗即作廢。

### 7.2 提案與驗證管線

1. **Prompt**（Director）：近期場次的 EventLog 摘要，要求恰好 5 個候選，每個附
   `{display, basis}`，basis 是一段短句「事蹟引用」（≤ 80 字）。Prompt 只要求形
  式：正體中文、2–8 字、名詞片語、不得含玩家名字。**碰撞規則刻意不寫進 prompt**，
   由程式面執行，維持 prompt 文字平直、token 成本固定。
2. **Schema 驗證**（`world/ai/schemas`）：封閉形狀
   `{candidates: [{display: str, basis: str}] × 5}`；JSON 畸形、數量錯誤、欄位過長
   時整輪作廢。
3. **決定論碰撞過濾**，逐候選、按下列順序、首個存活者勝：
   - 形式：2–8 字、不含玩家名子串、無空白字元；
   - 與 registry 中任何 `FixedTitleDef.display_name_zh` 相同，拒絕；
   - 與該 entity 收藏中任何綽號相同，拒絕；
   - 批內重複，保留第一個、丟棄其餘。
4. **投票組成**：取前 3 個存活者。1–3 個存活者就照人數成票（無最低門檻）。0 個存活
   者，該輪靜默作廢。LLM 離線、逾時、或 degraded 模式，該環節不觸發；固定稱號不受
   影響（決定論可玩 invariant）。
5. **呈現與同意**：持久化為 `db.pending_title_ballot`
   （`[{display, basis}]`）。投票永不到期：跨登出與重線存活，且有待決投票時所有提
   名觸發點都被抑制（§12），不存在替換路徑。WebClient 呈 OOB 選單（稱號卡＋事蹟引
   用，按鈕「接受 1／2／3」＋「放棄」）。Telnet 同一份清單配 `title accept
   <1|2|3>`／`title decline`。自由文字輸入永不用於選投票項。
6. **採納**→ rules 層 `accept_title(entity, index)`：附加綽號記錄
   （`display, origin_quote=basis, granted_tick`）並設定綽號槽，單筆原子交易、snapshot
   面已登記。**拒絕／忽略**→ 該批丟棄；EventLog 記錄被拒的 display 集合，讓
   Director 後續摘要看見玩家拒絕了什麼（軟學習，無程式黑名單）。

`world/ai/` 的第 1–4 步驟除了待決投票以外不寫任何東西；狀態變更只存在於
`world/rules/` 的 `accept_title` 之後。單寫者邊界毫髮無損。

## 8. D5 — 複合綽號的消費分層

- **敘事／社交消費者**呼叫
  `compose_epithet(read_fixed_slot(), read_nickname_slot())`：角色面板標頭、
  appraisal 散文、狀態介面、Director／NPC 對話的 prompt 脈絡（具名區段 `epithet`；
  當 Director 要求身份脈絡時，另附收藏中最多的 5 筆條目及其 basis 引用）。有複合綽
  號時 NPC 以它稱呼玩家，這個迴路才是稱號有意義的來源。
- **機械謂詞**（§6.2、未來的任務條件）讀完整的 `title_collection`，永不讀裝備槽。
  裝備與否純屬呈現；未裝備的稱號照常滿足謂詞。
- 合成為空時，消費者退回本名；LLM prompt 的該區段整個省略（不是填「無」）。

## 9. D6 — 稱號冊與命令介面

### 9.1 Read model（`world/rules/title_view.py`）

`TitleCodexView` 欄位：`fixed_rows: tuple[FixedTitleRow, ...]`（registry 全數列：
是否解鎖、display、flavor 或 hint、category、取得 tick）、
`nickname_rows: tuple[NicknameRow, ...]`（display、basis、取得日期 tick、是否裝
備）、`equipped: {fixed: ..., nickname: ...}`、`composite: str`、計數器
`unlocked_fixed / total_fixed`。純導出 view。新 OOB 契約常數（`TITLE_MAX_ROWS`、
`TITLE_MAX_DISPLAY_CHARS`、`TITLE_MAX_BASIS_CHARS`、category 列舉）依
frozen-contract 四鏡像流程（server view → wire validator → JS validator → 邊界測
試）。

### 9.2 WebClient 稱號冊視窗

- 角色 dock 的 icon 開啟大視窗（與搭檔 change 的技能系譜面板同一視窗級別）。
- 標頭：複合綽號預覽；`已收集 X / Y` 全 registry 完成度計數器（收集慾引擎）。
- **事蹟**區塊（固定稱號）：分類頁籤列（戰鬥／法術／探索／公會／風流韻事）；已解鎖
  卡顯示名稱＋風味文＋取得 tick；未解鎖卡顯示 🔒 加 `hint_zh`。點已解鎖卡＝裝備固定
  槽。
- **綽號**區塊（AI 歷史）：已採納綽號按時間倒序，各附事蹟引用；點擊＝裝備綽號槽；
  已裝備列帶 ★ 標記。永不可刪除。
- 兩個槽皆可清空、皆可留空；有待決投票時以第三個頁籤（「提名中」）呈現，重現待決選
  單，讓錯過的投票仍可回答。

### 9.3 Telnet 命令（命令文件 invariant 於同一 change 適用）

```
title list                       # 兩個區塊，含未解鎖列與提示
title equip fixed <display|key>  # 固定槽
title equip nickname <display>   # 綽號槽
title clear fixed|nickname
title accept <1|2|3>             # 待決投票
title decline                    # 待決投票
```

未知 display 回決定論拒絕且不列任何候選（不給亂猜的 oracle）；無待決投票時的
`title accept` 回穩定原因碼。

## 10. Change 切分

單一 change `title-system`，排在 `magic-power-trait-demotion`（刪除舊稱號帶）之後。
內部提交順序：lore registry 加規則層寫入者（`world/rules/titles.py`：收藏、裝備、
合成、採納）→ planner／授予路徑與公會位階配對 → read model、OOB 契約、webclient、
browser class → 命令與文件 → 測試模組同 change 登記分片清單。

## 11. 測試

- **純 `unittest`**：`compose_epithet` 矩陣（兩槽／只有固定／只有綽號／全空、全形空
  格、玩家名子串守衛）；碰撞過濾（固定 registry 命中、自身收藏命中、批內重複、順序
  保持、5→3 截斷、剩 1 個與剩 0 個路徑、畸形 schema 作廢）；冷卻算術（採納對拒絕）；
  待決投票單例；謂詞 registry 載入驗證（缺 hint、懸空引用）。
- **Evennia 整合**：固定授予與觸發行動原子提交、強制交易中失敗時完整還原；公會考試
  通過在升級交易內授予位階稱號、rollback 即移除；F 級註冊授予「F級冒險者」；
  `accept_title` 附加與裝備原子完成；重複授予 no-op；收藏跨登出／重載存活；LLM 路
  徑全程 mock（絕不真實連線）。
- **Browser**：稱號冊渲染鎖定／解鎖列、兩條裝備路徑、複合預覽更新、待決投票頁籤
  （本地一個 class，完整清單歸 CI）。
- **Traceability**：新 `title-system` capability spec；每條需求配一個
  `covers_requirement` 標註的行為測試；新模組同 change 登記
  `.github/evennia-shards.json`。

## 12. 錯誤處理

| 情境 | 行為 |
|---|---|
| 投票持久化失敗 | 該輪作廢，不留半筆提案（單屬性寫入、all-or-nothing） |
| `title equip` 帶未知稱號 | 穩定拒絕，無狀態變更 |
| Registry 謂詞引用不存在的資料面 | registry 載入即拋例外（匯入期） |
| 有待決投票時觸發新提名 | 提名被抑制（一次一個），不存在替換競爭 |
| LLM 回傳 4 個、6 個候選或壞 JSON | 整輪作廢（schema 是封閉的） |
| 玩家重線後才回答投票 | 投票屬性持久，選單重渲染，採納行為完全相同 |

## 13. 對權威來源文件的修訂

- 除役的 `RANK_TITLE_REGISTRY`／學徒→賢者帶（由 `magic-power-trait-demotion` 移
  除）由本系統取代；數值稱號帶不再回歸。
- 重申 `2026-07-29-ai-mud-engine-design.md` 的 D14：投票與稱號冊都是 server-authored
  OOB 選單；自由格式維持文字輸入。
- `world/ai/` 維持僅提案邊界：唯一的寫入路徑是在玩家明確同意之後、規則層的
  `accept_title`。
