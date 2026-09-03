# 稱號系統 — 設計文件

**日期：** 2026-08-30
**狀態：** Approved
**範圍：** 以兩個稱號家族取代除役的魔法位階稱號帶：由規則謂詞授予的決定論「固定
稱號」，以及經玩家同意投票採納、取自市井傳頌的「異名」；新增稱號冊 UI、複合全
銜、槽位非空不變與啟始授予（教學環節即取得首枚稱號與異名）、異名刪除（含覆核流
程，永不刪到空）、以及 `title` 命令家族。本設計不依賴成長重設計的任何部分，只依
賴 change `magic-power-trait-demotion` 已先行移除 `magic_rank_title()` 與
`RANK_TITLE_REGISTRY`。

搭檔文件為 `2026-08-30-use-driven-progression-design.md`。

## 1. 背景與問題

目前唯一的稱號是顯示用的魔法位階帶（學徒→賢者），由 `magic_level` 計算。那個數
字在成長重設計後不再是成長計數器，稱號帶隨之除役。另一方面，遊戲裡有大量未被表
達的身份訊號：技能系譜樹頂、怪物階層首殺、任務弧、公會位階、性里程碑。加上 LLM
層能為 EventLog 目睹之事命名。

設計目標是有安全性的風味文字。稱號是純顯示／lore 消耗品；決定論家族在全部 AI 服
務離線時照常運作；生成式家族在任何情況下都不能未經玩家明確同意寫入狀態。這正是
本專案對 `world/ai/` 的「僅提案」邊界，玩家是最後一道驗證閘。

生成式家族定名為「異名」。在這個世界觀裡，冒險者的異名從酒館閒談、吟遊詩人之歌
與公會流言裡長出來；Director 承擔「替市井取一個會流傳的名字」的職能，採納與否完
全由玩家決定。介面與文件措辭統一使用「稱號」與「異名」兩個詞，不使用「AI 稱
號」或「綽號」這類系統腔；程式內部對應 `fixed` 與 `epithet` 兩個 kind。

## 2. 目標

- 固定稱號只增不減、永不剝奪。異名僅能由玩家本人經覆核流程刪除，且永不刪到收藏
  為空（D5）。
- 槽位不變：某家族只要有藏品，對應裝備槽就不得為空；新藏品在槽位空時自動裝備
  （決定論取新獲得的那枚；「隨機一個」被決定論可玩 invariant 否決）。教學環節保
  證每位角色從啟始就有一個稱號與一個異名（D8、§6.5）。
- 固定稱號：registry 宣告、謂詞授予、寫入觸發事件的同一筆原子交易；AI 服務全離線
  時功能完整。
- 異名：一次提案五個、驗證後取三個的同意投票；程式面過濾；永不與固定稱號或玩家
  現有異名相同。
- 全銜：固定稱號與異名同時被消費（「B級冒險者 風趣的旅人」），供顯示、appraisal
  周邊散文與 LLM prompt 脈絡使用。
- 稱號冊是收集慾介面：每個固定稱號都可被發現，未解鎖者附作者撰寫的提示。
- 刪除異名不可逆，任何入口都強制二步覆核。

## 3. 非目標與前瞻縫隙

- **稱號不帶機械能力值效果。** 稱號只餵敘事與社交消費。（任務／NPC 條件日後可以
  *讀取*收藏；該前瞻縫隙屬資料讀取，不在本 change。）
- **固定稱號不存在刪除途徑。** 不做剝奪、到期，也不做批量操作；可刪除的只有異名，
  且僅限玩家主動。
- **不存在清空槽位或留空槽位的機制。** 裝備槽一旦有藏品就被永久佔用，玩家只能換
  裝，不能卸裝；`title clear` 命令與等價 OOB 動作都不存在（D8）。
- **不做 AI 內容審查管線。** 同意就是安全閥；程式只擋硬性碰撞與畸形格式。拒絕與
  刪除事件都寫入 EventLog 讓 Director 軟學習，不做持久黑名單。
- **公會位階保持自己的軸。** 不併入稱號 registry 語意；每次位階升級只是同時多授予
  一個固定稱號（D3），固定槽可以展示它。

## 4. 決策總覽

| # | 決策 | 章節 |
|---|---|---|
| D1 | 資料模型：收藏、兩槽、全銜合成 | §5 |
| D2 | 固定稱號：lore registry + EventLog planner 授予 | §6 |
| D3 | 公會位階升級授予該位階稱號 | §6.4 |
| D4 | 異名投票：觸發、5 驗 3、同意、冷卻 | §7 |
| D5 | 異名刪除：守門＋覆核，永不刪到空或刪到裝備中 | §8 |
| D6 | 全銜的消費分層（敘事對機械） | §9 |
| D7 | 稱號冊與命令介面 | §10 |
| D8 | 槽位非空不變與啟始授予（教學環節） | §5, §6.5 |

## 5. D1 — 資料模型

持久狀態（玩家 typeclass 屬性；使用前全部先向 snapshot/restore 面處理器登記）：

```python
# db.title_collection — list[dict]，固定稱號只增；異名僅經 D5 刪除且永不歸零
{"kind": "fixed",    "key": "zombie_hunter_of_the_gutters",
 "granted_tick": 1234}
{"kind": "epithet",  "display": "風趣的旅人",
 "origin_quote": "你在月舞酒館連贏三場嘴仗…",   # 投票時的「事蹟引用」
 "granted_tick": 2010}

# db.title_equipped — dict，全銜的兩個槽
{"fixed": <fixed key or None>, "epithet": <display or None>}
```

- 收藏條目以 `(kind, key|display)` 識別；固定 key 至多出現一次（重複授予靜默
  no-op）。異名 display 在收藏內唯一，因為 D4 的驗證在採納當下就擋掉碰撞；刪除後
  該名字回到可提案狀態（見 §8）。
- `db.title_equipped` 的兩個槽都存識別符而非複製：固定槽存 fixed key，異名槽存
  display（display 在收藏內唯一，且刪除其他條目會使列表索引位移，索引作為指標不安
  全）。重新裝備舊異名是寫識別符，不是複製。
- 兩個屬性在角色啟動時預設為空（`[]` 與 `{"fixed": None, "epithet": None}`）；屬
  性缺失的讀取與預設值等價。
- **槽位非空不變（D8）**：對每個 kind，「收藏非空 ⇒ 對應裝備槽非空」。由全部
  mutator 共同維持：固定授予與異名採納在對應槽為空時，於同一筆交易自動裝備新條
  目；異名刪除只准觸及未裝備條目（§8）；系統不存在清空槽位的路徑，`title clear`
  命令因此不存在。收藏為空的窗口只剩「角色已建立、尚未完成公會註冊」的啟始段，
  而 §6.5 的啟始授予正是在該窗口收尾。

`compose_title`（純函式，`world/rules/titles.py`）：

```python
def compose_title(fixed: str | None, epithet: str | None) -> str:
    parts = [p for p in (fixed, epithet) if p]
    return "　".join(parts)          # full-width space
```

固定在前、異名在後，以全形空格連接，空槽部分省略，兩槽皆空回傳空字串。所有消費者
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
存在的 registry 面（元素、怪物階層、任務 key、位階 key、性經驗型別）。

### 6.2 謂詞家族（逐筆內容列屬後續內容工作）

| 家族 | 謂詞參數 | 範例 |
|---|---|---|
| `lineage_complete` | 元素／武藝系譜的根 key | 火系樹磨練至不滅鳳凰焰（`phoenix_eternal_flame`）見頂 |
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

授予寫入固定槽的語意服從 D8：固定槽為空時，授予在同一筆交易內自動裝備新稱號；
槽已佔用時新稱號只入庫，由稱號冊決定是否換裝。

### 6.4 D3 — 公會位階稱號

每個 `GUILD_RANK_REGISTRY` 列配對一個稱號（各階 display 由作者撰寫；F 級註冊本身
授予「F級冒險者」）。E→S 的授予搭 `settle_exam_outcome` 的升級交易（planner 看見
升級事件）；F 級搭 `register_guild_member` 的交易。重新註冊、分會移動、merit 變動
都不碰收藏。位階對 offers／考試的權威軸不變，稱號只是裝飾性同步。萬一未來出現降
階情境（目前不存在），也永不剝奪已入庫稱號（固定稱號只增 invariant）。

### 6.5 D8 — 啟始授予（教學環節）

啟始身份必須決定論可玩，因此不押注 LLM 投票：教學環節的公會註冊交易
（`register_guild_member`）一次授予兩個條目——

- 固定稱號「F級冒險者」（既有的位階配對，D3）；
- **啟始異名**：`world/lore/titles.py` 的 registry 常數 `STARTER_EPITHET`（display
  「南門新客」，basis 由作者撰寫，範例：「你在南門守衛的目送下踏入阿爾托利亞，成
  為公會的新面孔。」）。它以普通 epithet 條目入庫，之後的採納碰撞過濾、裝備與刪除
  規則對它的適用方式與其他異名完全相同。

兩個條目在空槽上自動裝備（D8），全銜自教學完成起即為「F級冒險者　南門新客」；授
予各自推 OOB 通知，稱號冊解鎖列同步翻面。重複註冊對啟始授予是冪等 no-op（固定
key 去重、display 收藏去重，兩條既有規則天然覆蓋）。此後玩家要淘汰啟始異名，走正
規流程：先採納新異名並在稱號冊換裝，再刪除已成未裝備條目的舊名。

兩個條目都是決定論授予，直接搭 `register_guild_member` 的既有原子交易（與 D3 的
F 級配對同一個掛點、同一筆提交），不需要 LLM、也不需要 EventLog planner 參與；
`world/rules/onboarding` 本身不需要知道稱號系統的存在，掛點在公會註冊的 rules 路
徑內。

## 7. D4 — 異名投票

### 7.1 觸發與節流

- 觸發點只限敘事休息點，戰鬥結算中途絕不觸發：登出；世界時鐘日界且角色處於休
  息；公會考試通過；任務弧完成。每個觸發呼叫 `maybe_nominate(entity)`。
- 每個 entity 同時至多一個待決投票；已有待決時 `maybe_nominate` 靜默返回。
- 冷卻：投票被拒絕或逾期後，`NOMINATION_COOLDOWN_DAYS` 個日界（registry 常數，初
  值 2）抑制再提名。被採納的投票不觸發冷卻（下次提名反正要等下個觸發點）。
- 每個觸發點以既有 options service 的「結算內同步、有逾時上界」模式呼叫 LLM；任何
  失敗即作廢。

### 7.2 提案與驗證管線

1. **Prompt**（Director）：近期場次的 EventLog 摘要，要求恰好 5 個候選，每個附
   `{display, basis}`，basis 是一段短句「事蹟引用」（≤ 80 字）。Prompt 只要求形
   式：正體中文、2–8 字、名詞片語、不得含玩家名字。**碰撞規則刻意不寫進
   prompt**，由程式面執行，維持 prompt 文字平直、token 成本固定。
2. **Schema 驗證**（`world/ai/schemas`）：封閉形狀
   `{candidates: [{display: str, basis: str}] × 5}`。JSON 畸形、數量錯誤、欄位過長
   時整輪作廢。
3. **決定論碰撞過濾**，逐候選、按下列順序、首個存活者勝：
   - 形式：2–8 字、不含玩家名子串、無空白字元；
   - 與 registry 中任何 `FixedTitleDef.display_name_zh` 相同，拒絕；
   - 與該 entity 收藏中任何異名相同，拒絕（被刪除過的名字因收藏已無此列而可再次
     入票，見 §8）；
   - 批內重複，保留第一個、丟棄其餘。
4. **投票組成**：取前 3 個存活者。1–3 個存活者就照人數成票（無最低門檻）；0 個存
   活者該輪靜默作廢。LLM 離線、逾時、或 degraded 模式時該環節不觸發；固定稱號
   不受影響（決定論可玩 invariant）。
5. **呈現與同意**：持久化為 `db.pending_title_ballot`
   （`[{display, basis}]`）。投票永不到期：跨登出與重線存活，且有待決投票時所有提
   名觸發點都被抑制（§7.1），不存在替換路徑。WebClient 呈 OOB 選單（稱號卡＋事蹟
   引用，按鈕「接受 1／2／3」＋「放棄」）。Telnet 同一份清單配 `title accept
   <1|2|3>`／`title decline`。自由文字輸入永不用於選投票項。
6. **採納**→ rules 層 `accept_epithet(entity, index)`。附加異名記錄
   （display, origin_quote=basis, granted_tick）於單筆原子交易、snapshot 面已登
   記；異名槽為空時同一筆交易自動裝備該新異名（D8），槽已佔用則只入庫、由稱號冊
   決定換裝。**拒絕／忽略**→ 該批丟棄，EventLog 記錄被拒的 display 集合，讓
   Director 後續摘要看見玩家拒絕了什麼（軟學習，無程式黑名單）。

`world/ai/` 的第 1–4 步驟除了待決投票以外不寫任何東西；狀態變更只存在於
`world/rules/` 的 `accept_epithet` 與 `remove_epithet` 之後。單寫者邊界毫髮無損。

## 8. D5 — 異名刪除與覆核流程

玩家事後覺得某個異名不合適，可以自行移除。此操作不可逆，因此所有入口都強制覆核。

- **唯一 mutator**：rules 層 `remove_epithet(entity, display)`，只接受 `kind ==
  "epithet"` 且**同時通過兩道守門**的條目：(a) 該條目未裝備於異名槽——要刪先換
  裝，收藏至少兩枚時玩家總能先把要刪的換下來；(b) 刪除後收藏不得為空——收藏只剩
  一枚異名時一律拒絕。兩道守門都在第一步就回絕並回穩定原因碼，不進入覆核流程。
  固定稱號沒有刪除 API、沒有刪除命令、沒有任何程式路徑（invariant 由「不存在」保
  證，測試斷言介面不存在）。
- **不可逆**：條目從收藏移除，不落地任何回收站、無還原 API。
- **覆核流程（二步）**：
  - WebClient：異名卡上的「移除」開啟確認單，逐字顯示該異名的 display 與事蹟引
    用，附「此操作不可恢復」警示，按鈕為「確認移除／取消」。一律單筆操作，無批次
    刪除。正裝備的卡與只剩一枚異名時，「移除」按鈕不出現（守門在 UI 層就顯現，
    不留給玩家撞牆的機會）。
  - Telnet：`title remove epithet <display>` 第一步回顯覆核資訊與所需確認指令，不執
    行；同一指令附字面 `confirm` 才真正執行。任何其它輸入視同取消。
  - **刪除的連動效果**：守門保證被刪條目必為未裝備，槽位不動、全銜不變短；
    EventLog 記錄 `title_epithet_removed`（含 display），Director 後續摘要讀得到。
- **刪除不等於封鎖**：碰撞過濾讀即時收藏，被刪過的名字未來可再次入票。玩家的意圖
  是「這個名字現在不適合我」；要再次拒絕，再刪一次的成本極低。持久黑名單屬於非目
  標（§3）。
- snapshot 面沿用 `title_collection` 既有登記，不新增面。

## 9. D6 — 全銜的消費分層

- **敘事／社交消費者**呼叫 `compose_title(read_fixed_slot(),
  read_epithet_slot())`：角色面板標頭、appraisal 散文、狀態介面、Director／NPC 對
  話的 prompt 脈絡（具名區段 `epithet`；當 Director 要求身份脈絡時，另附收藏中最
  多的 5 筆條目及其 basis 引用）。有全銜時 NPC 以它稱呼玩家，這個迴路才是稱號有意
  義的來源。
- **機械謂詞**（§6.2、未來的任務條件）讀完整的 `title_collection`，永不讀裝備槽。
  裝備與否純屬呈現；未裝備的稱號照常滿足謂詞。
- 全銜為空的窗口只剩公會註冊完成前的啟始段（D8）；該窗口內消費者退回本名，LLM
  prompt 的該區段整個省略（不是填「無」）。

## 10. D7 — 稱號冊與命令介面

### 10.1 Read model（`world/rules/title_view.py`）

`TitleCodexView` 欄位：`fixed_rows: tuple[FixedTitleRow, ...]`（registry 全數列：
是否解鎖、display、flavor 或 hint、category、取得 tick）、`epithet_rows:
tuple[EpithetRow, ...]`（display、basis、取得日期 tick、是否裝備）、`equipped:
{fixed: ..., epithet: ...}`、`full_style: str`、計數器 `unlocked_fixed /
total_fixed`。每筆 epithet 列附決定論旗標 `can_remove`（守門 a、b 的 server 端結
論），客戶端照旗標渲染、零規則。純導出 view。新 OOB 契約常數（`TITLE_MAX_ROWS`、
`TITLE_MAX_DISPLAY_CHARS`、`TITLE_MAX_BASIS_CHARS`、category 列舉）依
frozen-contract 四鏡像流程（server view → wire validator → JS validator → 邊界測
試）。

### 10.2 WebClient 稱號冊視窗

- 角色 dock 的 icon 開啟大視窗（與搭檔 change 的技能系譜面板同一視窗級別）。
- 標頭：全銜預覽；`已收集 X / Y` 全 registry 完成度計數器（收集慾引擎）。
- **事蹟**區塊（固定稱號）：分類頁籤列（戰鬥／法術／探索／公會／風流韻事）；已解鎖
  卡顯示名稱＋風味文＋取得 tick；未解鎖卡顯示 🔒 加 `hint_zh`。點已解鎖卡＝裝備固
  定槽。
- **異名**區塊：已採納異名按時間倒序，各附事蹟引用；點擊＝裝備異名槽（換裝）；已
  裝備列帶 ★ 標記；`can_remove` 為真的卡附「移除」按鈕，觸發 §8 的確認單，其餘卡
  不出現按鈕。
- 兩個槽永遠有裝備（啟始授予完成後；D8），UI 只有換裝、沒有卸裝；有待決投票時以
  第三個頁籤（「提名中」）呈現，重現待決選單，讓錯過的投票仍可回答。

### 10.3 Telnet 命令（命令文件 invariant 於同一 change 適用）

```
title list                            # 兩個區塊，含未解鎖列與提示
title equip fixed <display|key>       # 固定槽（換裝，永無卸裝）
title equip epithet <display>         # 異名槽（換裝，永無卸裝）
title remove epithet <display>        # 第一步：回顯覆核資訊
title remove epithet <display> confirm  # 第二步：執行刪除
title accept <1|2|3>                  # 待決投票
title decline                         # 待決投票
```

未知 display 回決定論拒絕且不列任何候選（不給亂猜的 oracle）；無待決投票時的
`title accept` 回穩定原因碼；`title remove fixed ...` 與 `title clear ...` 都不存
在於命令表；刪除守門的穩定原因碼為 `TITLE_EQUIPPED_UNREMOVABLE` 與
`TITLE_LAST_EPITHET`。

## 11. Change 切分

原單一 change 依「單一工程師一個工作日」粒度拆為三個序列 change，全部排在
`magic-power-static-rename`（刪除舊稱號帶）與 `magic-xp-engine-retirement` 之後：

- **F `title-fixed-core`**（依賴 A、B；§5／§6／§6.5）：兩類稱號儲存與 lore
  registry、`world/rules/titles.py` 規則層寫入者（收藏、裝備、合成、採納）、
  `STARTER_EPITHET`「南門新客」與「F級冒險者」同一交易授予、D8 槽非空
  ＋自動裝備、EventLog planner 授予、`title list`／`title equip`、read model 與
  webclient、命令文件；新capability `title-system` 於此 change ADDED。
- **G `title-epithet-nomination`**（依賴 F；§7）：投票流程（5→schema→撞名→top-3）、
  單一 pending 投票、跨兩日邊界冷卻、`title accept`／`title decline`。
- **H `title-codex-removal`**（依賴 F、G；§8＋§10）：codex read model＋視窗＋
  `can_remove`、兩關兩步綽號刪除（`TITLE_EQUIPPED_UNREMOVABLE`／
  `TITLE_LAST_EPITHET`）。

嚴格序列 F → G → H（共享 `world/rules/titles.py` 與 lore registry；不平行）。
每個 change 的新測試模組同 change 登記 `.github/evennia-shards.json`；玩家命令
變更同 change 更新兩份命令文件與 `tests/test_command_docs.py`。

## 12. 測試

- **純 `unittest`**：`compose_title` 矩陣（兩槽／只有固定／只有異名／全空、全形空
  格、玩家名子串守衛）；碰撞過濾（固定 registry 命中、自身收藏命中、批內重複、順序
  保持、5→3 截斷、剩 1 個與剩 0 個路徑、畸形 schema 作廢）；冷卻算術（採納對拒
  絕）；待決投票單例；謂詞 registry 載入驗證（缺 hint、懸空引用）。
- **刪除矩陣**：二步強制（缺 `confirm` 一律不執行）；守門拒絕正裝備的異名與唯一
  一枚異名（穩定原因碼，且不進入覆核）；換裝後刪除舊名成功且槽位不動；刪除後同名
  字可再次入票；固定稱號無刪除介面（結構斷言）；刪除不存在的異名回穩定拒絕；
  `title_epithet_removed` 寫入 EventLog。
- **槽位不變與啟始授予**：固定授予／異名採納在空槽自動裝備、非空槽只入庫；公會
  註冊交易一次入庫「F級冒險者」＋「南門新客」且全銜即刻為二者合成；重複註冊冪等
  no-op；任何 mutator 序列之後都不存在「收藏非空且槽為空」的狀態（invariant 測
  試）。
- **Evennia 整合**：固定授予與觸發行動原子提交、強制交易中失敗時完整還原；公會考試
  通過在升級交易內授予位階稱號、rollback 即移除；F 級註冊授予「F級冒險者」；
  `accept_epithet` 附加與裝備原子完成；重複授予 no-op；收藏與刪除跨登出／重載存活；
  LLM 路徑全程 mock（絕不真實連線）。
- **Browser**：稱號冊渲染鎖定／解鎖列、兩條換裝路徑、全銜預覽更新、待決投票頁籤、
  `can_remove` 控制「移除」按鈕顯隱、移除確認單的顯示與取消路徑（本地一個 class，
  完整清單歸 CI）。
- **Traceability**：新 `title-system` capability spec；每條需求配一個
  `covers_requirement` 標註的行為測試；新模組同 change 登記
  `.github/evennia-shards.json`。

## 13. 錯誤處理

| 情境 | 行為 |
|---|---|
| 投票持久化失敗 | 該輪作廢，不留半筆提案（單屬性寫入、all-or-nothing） |
| `title equip` 帶未知稱號 | 穩定拒絕，無狀態變更 |
| Registry 謂詞引用不存在的資料面 | registry 載入即拋例外（匯入期） |
| 有待決投票時觸發新提名 | 提名被抑制（一次一個），不存在替換競爭 |
| LLM 回傳 4 個、6 個候選或壞 JSON | 整輪作廢（schema 是封閉的） |
| 玩家重線後才回答投票 | 投票屬性持久，選單重渲染，採納行為完全相同 |
| `title remove` 指向未知或非 epithet 條目 | 穩定拒絕，無狀態變更 |
| 移除正裝備的異名 | 第一步回絕 `TITLE_EQUIPPED_UNREMOVABLE`，不進入覆核 |
| 只剩一枚異名時移除 | 第一步回絕 `TITLE_LAST_EPITHET`，不進入覆核 |
| 移除第一步後未輸入 `confirm` | 視同取消，無狀態變更 |
| 移除未裝備且非唯一的異名 | 收藏移除，槽位不動，EventLog 記錄 |

## 14. 對權威來源文件的修訂

- 除役的 `RANK_TITLE_REGISTRY`／學徒→賢者帶（由 `magic-power-trait-demotion` 移
  除）由本系統取代；數值稱號帶不再回歸。
- 重申 `2026-07-29-ai-mud-engine-design.md` 的 D14：投票與稱號冊都是 server-authored
  OOB 選單；自由格式維持文字輸入。
- `world/ai/` 維持僅提案邊界：唯一的寫入路徑是玩家明確同意後的 `accept_epithet`
  與玩家主動覆核後的 `remove_epithet`，兩者都在 rules 層。
- 用語定案：玩家介面與文件的兩個家族名稱是「稱號」（固定稱號）與「異名」；程式
  key 是 `fixed` 與 `epithet`；複合顯示字串稱「全銜」（`compose_title`）。
