# 使用驅動成長與 magic_power 降格 — 設計文件

**日期：** 2026-08-30
**狀態：** Approved
**範圍：** 將 `magic_level` 降格並更名為 `magic_power`，改為固定戰鬥屬性；除役魔
法 XP 引擎；讓「各技能的使用熟練度」成為唯一的成長貨幣；以前置技能系譜鏈作為技
能階層的使用門檻；新增宣告式修煉跳時與技能系譜面板 UI。本文件修訂
`2026-07-29-ai-mud-engine-design.md`（見 §17）。

搭檔文件為 `2026-08-30-title-system-design.md`，其中的 `title-system` change 取
代本次除役的魔法位階稱號帶。

## 1. 背景與問題

目前的角色成長跑在四條軸線上：魔法等級 XP 計數器（`magic_level`，受種族上限約
束，來源為 SKIP 來源的讀書 XP 與階層怪物擊殺 XP）、每技能練習熟練度、公會位階
（merit 加非致命考試）、以及性狀態里程碑計數器。設計評審確認了三項缺陷。

1. **魔法軸存在領域偏見。** 本專案的物理戰鬥如今與魔法同等重要，但唯一具備等級
   性質的計數器，無論命名或機械行為都綁在魔法上。物理取向角色完全沒有一條看得見
   的成長軸。
2. **SKIP 來源的讀書 XP 屬於無意圖的成長。** 玩家什麼都沒宣告、只跳過八小時就會
   獲得魔法 XP。主流 RPG 直覺與使用者的明確方向都否定「時間流逝本身產生成長」。
3. **熟練度沒有機械消費者。** `skill_proficiency_level()` 會導出並持久化，但除了
   測試之外沒有任何東西讀用它，使用制軸線形同虛設。

另一項發現重塑了修法。`magic_level` 不只是等級計數器。`combat.py` 把它當成魔法
系的攻擊屬性讀取（與 `atk_phys` 對稱的位置），治療量、appraisal 戰力評分、裝備
bundle、`disguised_stats`、webclient 的「魔力」欄也都讀它，全倉庫約 95 個引用
點。因此殺掉這個名字是錯誤的手術，只移除它的成長職責才對。

## 2. 目標

- 只有一種成長貨幣：**技能使用 → 熟練度 → 系譜解鎖**。沒有全域等級，擊殺不給
  XP，時間流逝也不給。
- `magic_power` 成為第四個固定（static）戰鬥屬性，與 `atk_phys`、`agility`、
  `defense` 完全對稱。傷害公式、appraisal、裝備、偽裝資料與「魔力」顯示全部照常
  運作，行為零變更。
- 成長不再偏魔法：種族 `learning_multiplier` 縮放的是學習（練習 XP），適用於所有
  技能。精靈學得快，但不會自動魔法升等比較快。
- 熟練度取得真正的消費者：技能系譜鏈上的前置門檻，以及 freeform 規模階梯。
- 反刷規則讓「刷最便宜的技能」在機械上沒有意義。
- 玩家能看見每條鏈距離下一個節點的進度（技能系譜面板）。

## 3. 非目標與前瞻縫隙

刻意記錄於此，讓後續 change 不需重新設計即可落地；本文件不偽造任何實作
（AGENTS.md 前瞻縫隙規則）。

- **不做能力值訓練。** 儲存的固定屬性維持匯入或擲骰的 literal 值（AGENTS.md
  invariant：永不把倍率 bake 進 traits）。數值成長仍是裝備與 `stat_multiply` 被動
  經 `SkillHandler.effective_value` 的專屬權利。
- **不做熟練度戰鬥加成。** 評審明確否決：熟練度不減消耗、不加傷害。熟練度只買准
  入。
- **本系統不給任何形式的擊殺獎勵。** 擊殺照舊由現有 owner 給戰利品、任務 DEFEAT
  進度與公會 merit。`COMBAT_KILL_XP_TABLE` 是刪除，不重新指派。
- **不新增物理專屬等級。** 物理成長由同樣的系譜鏈加上裝備與被動承擔，構造上自然
  對稱。
- **武器與物理親和**屬前瞻縫隙：親和乘數讀 `affinity_elements`，對物理技能天然不
  匹配（乘數 1.0）。未來 change 要加武器親和時零重構。
- **公會位階與性狀態軸完全不動**，唯一例外是公會位階升級現在也會同時授予一個固
  定稱號（由搭檔文件擁有）。

## 4. 決策總覽

| # | 決策 | 章節 |
|---|---|---|
| D1 | `magic_level` → `magic_power`，counter 改 static | §5 |
| D2 | 種族與權力帶資料改為四維 | §6 |
| D3 | XP 引擎直接除役（不做 shim） | §7 |
| D4 | 使用是唯一成長（原子練習結算） | §8 |
| D5 | 技能系譜鏈是使用門檻；registry 載入驗證圖形 | §9 |
| D6 | 鏈頂上限與同 tick 去重反刷 | §10 |
| D7 | 宣告式修煉取代環境讀書 | §11 |
| D8 | 技能系譜 read model 與 WebClient 面板、Telnet 命令 | §12 |
| D9 | 兩個有順序的 change 加一個獨立 change | §13 |

## 5. D1 — `magic_level` 更名為 `magic_power`，counter 改 static

`world/rules/traits.py` before/after：

```python
# before
STATIC_KEYS = ("atk_phys", "agility", "defense")
COUNTER_KEYS = ("magic_level", "guild_merit")

# after
STATIC_KEYS = ("atk_phys", "agility", "defense", "magic_power")
COUNTER_KEYS = ("guild_merit",)
```

- `trait_config_for_values` 將 `magic_power` 與其他三者一樣建成
  `{"trait_type": "static", "base": value, "mod": 0}`；帶 `min/max` 的 counter 分支
  隨著魔法上限一起消失。
- 顯示名維持「魔力」。`equipment_effects.py` 的中文對應變成
  `("magic_power", "魔力")`，`displayed_stats.DISPLAYED_KEYS` 換 key。玩家看到的字
  從來沒變過，有誤導性的只有程式 key（`level` 描述的是已死的系統）。
- 變更後的 invariant：沒有任何 rules 路徑會寫 `magic_power` 的儲存 base。唯一的變
  更來源是既有的 trait-modifier 管線（裝備與技能 `effective_value`），永不觸碰
  `base`。一支迴歸測試斷言沒有 production caller 把 `magic_power` 傳給任何 counter
  寫入介面。
- `combat.py` 在傷害路徑改名（`attack_key = "atk_phys" if school == "physical"
  else "magic_power"`）、治療量、appraisal 屬性和。其餘公式逐位元組不變。

## 6. D2 — 種族與權力帶資料改為四維

`StaticBand` 增加第四維；種族欄位 `magic_cap` 與 `starting_magic_level` 刪除：

```python
@dataclass(frozen=True)
class StaticBand:
    atk_phys: tuple[int, int]
    agility: tuple[int, int]
    defense: tuple[int, int]
    magic_power: tuple[int, int]
```

種族基準帶為暫定值，把舊的 starting/cap lore 換算成帶尺度（人類平凡、獸人體魄強
健、精靈魔力深厚）：

| 種族 | atk_phys / agility / defense | magic_power 帶 | learning_multiplier |
|---|---|---|---|
| human | (1, 22) | (5, 90) | 1.0 |
| beastfolk | (4, 34) | (1, 30) | 1.0 |
| elf | (70, 95) | (100, 900) | 10.0 |

`STATIC_TIER_REGISTRY` 各列照現有三維的做法為每維補上更窄的 tier 帶，tier 帶必須
是種族帶的子集合，載入時檢查。舊的數值 lore 錨點以 tier 提示形式存活，例如
`human_adventurer` 落在帶中段。

消費者：

- `imports/schema.py`：`stats` 與 `disguised_stats` 以 `magic_power` 取代
  `magic_level`；`imports/validate.py` 把魔法上限檢查換成對種族基準帶的區間成員檢
  查（決定論的 `Issue("stats.magic_power", ...)`）。
- `character_creation.py`：專屬的 magic sampler（`starting_magic_interval` 及其助手）
  刪除；`magic_power` 加入其他三個固定屬性的現行路徑。preset 照舊固定全部四個值。
- `scene_builder.py` NPC 建構讀 tier 的四條帶；`example_character.json` 的
  `magic_level: 60` 移入語意合法的 `magic_power` 帶位。
- WebClient 角色面板：「魔力」格在結構上與攻擊、敏捷、防禦完全相同（base/mod 分
  解，無進度語意）。

## 7. D3 — XP 引擎除役（刪除對照表）

| 符號或介面 | 模組 | 後續動作 |
|---|---|---|
| `magic_xp` 屬性與 `_stored_magic_xp` | progression | 移除 snapshot 面登記 |
| `magic_xp_per_level`、`MAGIC_XP_PER_LEVEL` | progression.yaml/py | 常數刪除 |
| `accrue_magic_study`、`_apply_level_ups` | progression | 時鐘 `magic_study` stage 改指（D7） |
| `grant_combat_kill_xp`、`COMBAT_KILL_XP_TABLE` | progression | EventLog planner 掛載鉤刪除 |
| `magic_rank_title`、`MAGIC_RANK_BANDS`、`RANK_TITLE_REGISTRY`、`MAGIC_TIER_THRESHOLDS` 比較邏輯 | progression、lore/magic | 稱號系統取代；tier 降為資料標籤 |
| `can_cast_spell_tier`、元素主宰門檻覆寫、`_element_effective_magic_level` | progression | 由 `can_use_skill` 取代（D5）；過渡期僅檢查 ownership（見 §13） |
| `element_mastery_rank` effect 前綴（元素域） | skills/effects 與內容列 | typed effect 類別連同元素覆寫一併刪除；mastery 被動保留身份、以 key-presence 把關 freeform；effect 列由本次內容工作重寫為風味。`sexual_magic_mastery` 分支不除役：該域的解鎖階梯由 counter 把關（SEXUAL_ACT_REGISTRY），`can_use_skill` 原樣保留該分支 |
| `element_affinity_multiplier` 的有效等級導出 | progression | 乘數保留、改錨到練習 XP（D4）；「有效等級」概念刪除 |
| `conferred_growth_rate` 的目標 `magic_level_growth` | buffs | 目標改為 `skill_practice`；pull-read 路徑保留 |
| 被動 effect 前綴 `growth_rate:magic:<N>` | skills/registry | 改 key 為 `growth_rate:practice:<N>`；舊前綴令 registry 載入失敗 |
| freeform scale 階梯的等級門檻 | progression | 改錨到熟練度（D5） |
| 測試 fixture 中為讓施法過門而設 `traits.magic_level.base = 30` 的寫法 | quests/rules tests | 刪除；由 change 2 的 `grant_proficiency()` 輔助取代 |

沒有正式使用者，一次性 cutover、零相容 shim（AGENTS.md）。

## 8. D4 — 使用是唯一成長

每次 `ActionResolver.resolve()` 原子提交時，actor 就其所使用的技能累計：

```
practice_xp += SKILL_PRACTICE_XP_PER_USE
             × RACE_REGISTRY[race].learning_multiplier          (elf ×10)
             × ELEMENT_AFFINITY_MULT if skill.element in entity.affinity_elements
               (affinity 1.1 / non-affinity 0.9; physical or non-elemental
                skills: 1.0)
             × growth_rate_multiplier(entity)                   (conferred buff, pull-read)
```

- 儲存結構維持現形：`db.skill_proficiency[skill_key]` 存 float XP；
  `skill_proficiency_level() = floor(xp / 50)` 不變；等級在未觸及 D6 上限前一樣無上
  限。
- 魔法施放路上既有的練習 seam 泛化給所有 ACTIVE 技能，語意完全相同：同一個
  snapshot/restore 面、同樣的 rollback 保證、與技能自身效果及資源扣款同一筆交易提
  交。PASSIVE 技能不累計，因為沒有東西會使用它們。
- 物理與魔法的對稱是徹底的：`basic_attack` 給自己累計、劍技用一下就累計，累計公
  式中沒有任何一處讀取 school。
- 明確的反向測試。一場完整戰鬥（含擊殺）除了實際使用之外不改變任何熟練度；公會考
  試不累計（考試上下文已有 nonlethal 標記，`nonlethal` 時跳過累計，與舊擊殺 XP 檢
  查相同的隔離，如今覆蓋所有成長介面）。

## 9. D5 — 技能系譜鏈是使用門檻

### 9.1 資料

```python
@dataclass(frozen=True, slots=True)
class SkillPrerequisite:
    skill_key: str
    min_proficiency: int          # >= 1

# on SkillDef (frozen, like everything else)
prerequisites: tuple[SkillPrerequisite, ...] = ()
```

示範火系鏈如下。每個 key 與顯示名都是 `world/skills/registry.py` 的真實條目；邊
本身是本次 change 要撰寫的新 registry 內容（示意調值）。`cap` 欄為 D6 導出的累計
上限，即消耗該節點的所有邊中最大的要求值，鏈頂預設 10：

| 節點 | prerequisites | cap（導出） |
|---|---|---|
| 火焰箭（`fire_arrow`） | 無（root） | 3 |
| 火球術（`fire_ball`） | (`fire_arrow`, 3) | 3 |
| 灼熱波動（`scorching_wave`） | (`fire_ball`, 3) | 3 |
| 火焰風暴（`firestorm`） | (`scorching_wave`, 3) | 5 |
| 熔岩術（`lava_burst`） | (`firestorm`, 5) | 8 |
| 龍炎術（`dragon_flame`） | (`lava_burst`, 8) | 8 |
| 不滅鳳凰焰（`phoenix_eternal_flame`） | (`dragon_flame`, 8) | 10（tip） |

其餘火系姊妹法術（業火纏繞 `infernal_wrap`、煉獄業火 `hellfire`、焚世終焰
`world_ending_blaze`）由同一輪內容工作補上各自的邊。五個元素精通被動（火焰精通
`fire_mastery` 等）是 PASSIVE，因此不是鏈節點。沒有東西會使用它們，它們由匯入或
授予取得，剩下的唯一機械角色是下方 freeform 資格的 key-presence 檢查。

### 9.2 門檻

```python
def can_use_skill(entity, skill) -> bool:
    if skill.key not in entity.skills.owned_keys():
        return False
    for pre in skill.prerequisites:
        if pre.skill_key not in entity.skills.owned_keys():
            return False
        if skill_proficiency_level(entity, pre.skill_key) < pre.min_proficiency:
            return False
    return True
```

- 這個單一門檻取代 `can_cast_spell_tier`，套用於所有 ACTIVE 技能，法術與武技一視
  同仁。`ActionResolver._step1_ownership`、preview 與兩套選單都改呼叫它。主宰階的
  特殊覆寫路徑整個刪除：主宰階准入如今就是鏈頂條件成立。
- ownership 不受門檻限制（匯入、preset、NPC 場景建構、conferred grant 照舊直接給
  ownership）；受門檻限制的是使用。匯入的宗師級角色擁有深層技能，如何取得可施用
  的熟練度見下方 auto-seed。
- 五個 `cost_tiers` 階層保留為選單與稱號 registry 階層謂詞用的資料標籤，不再承載門
  槛值。
- **Freeform 規模階梯改錨**（progression.yaml 常數）：資格仍需該元素精通（對已持有
  的 `<element>_mastery` 做 key 檢查，例如火焰精通 `fire_mastery`）；之後允許的
  scale 讀該技能自身熟練度：0.25 無條件、0.5 ≥1、1.0 ≥3、2.0 ≥6、4.0 ≥10。與 D6
  上限的交互是刻意的：衍生 cap 小於 10 的中段技能會停在 cap 允許的最高規模（例如
  cap 5 對應最大 scale 2.0）；scale 4.0 只有鏈頂技能（衍生 cap 為 tip 預設 10）能
  觸及。行為決定論、由系譜面板渲染、對玩家完全不隱藏。

### 9.3 Registry 載入驗證（fail closed，匯入期）

1. 每個 `prerequisites.skill_key` 存在於 `SKILL_REGISTRY`。
2. 圖形無環（拓撲排序；有環即拋例外，訊息點名該環）。
3. `min_proficiency` 為大於等於 1 的整數。
4. 沒有前置即視為鏈根宣告，不需要額外 flag。
5. 反向邊映射於載入時算出並快取，供 D6 上限使用。

### 9.4 匯入 auto-seed

匯入角色預設會擁有前置熟練度不滿足的技能。Loader 規則於既有 all-or-nothing 交易
內執行：對每個已擁有技能，若其某條前置邊的等級要求不滿足，就把該前置的熟練度
seed 到恰好等於要求值（絕不高於）。auto-seed 於 schema 區間驗證之前執行，因此畸形
匯入仍然全部拒絕；匯入檔中明確寫的 `skill_proficiency` 永遠勝過 auto-seed。NPC 場
景建構共用同一支輔助。

## 10. D6 — 鏈頂上限與反刷

兩條硬規則，全部由 registry 資料導出，不做逐技能的手工調值。

1. **按消費者設上限。** 對技能 S，`cap(S)` 取遍所有消耗 S 的邊、取其
   `min_proficiency` 最大值；若 S 不消耗任何人（鏈頂），cap 設為
   `PROFICIENCY_TIP_CAP`（yaml 常數，初值 10）。累計飽和：一旦
   `level(S) >= cap(S)`，XP 停止進帳，系譜面板顯示「見頂」。把已被完全消耗的底層技
   能刷到永遠為零，RuneScape 的「對空氣放火球」病理在機械上失去意義。
2. **同 tick 去重。** 一組 `(actor, skill_key, target)` 每個世界時鐘 tick 最多計一
   次。狀態是暫時的 per-tick dict（模組層級，tick 改變即清空），永不持久化、不進
   snapshot 面。AOE 技能對每個不同目標各計一次。戰鬥外每次施放結算都會推進時鐘，
   連續施放自然落在不同 tick 上。

## 11. D7 — 宣告式修煉取代環境讀書

命令語法，於既有 `skip` 命令加一個可選子句：

```
skip <hours> [practice <skill>]
skip <hours> [rest]          # explicit rest; also the no-clause default
```

- `practice <skill>`：只對該技能累計
  `hours × PRACTICE_XP_PER_STUDY_HOUR × learning × affinity × growth buff`。
  PRACTICE_XP_PER_STUDY_HOUR 初值 10.0 每小時。舊的 1.0 每小時讀書率是對 600 XP
  每級的池子校準的；在 50 XP 每級下，10 每小時讓人類無親和時約 5 小時升一級熟練
  度。全部暫定；`progression.yaml` 保留「playtest 後重校」的檔頭註解。
- 任何時鐘推進前先 preflight：技能必須已擁有、合法（技能本身 owned）、未見頂。拒
  絕回穩定原因碼（`PRACTICE_SKILL_UNKNOWN`、`PRACTICE_SKILL_CAPPED`），且時鐘零推
  進。skip 絕不半套生效。
- `rest` 與未標註的 skip 推進時鐘、不給任何成長。世界時鐘 stage 保留契約外形（僅
  SKIP 來源、每 entity 每次呼叫一次閉式計算，與秒數大小無關），只有內容從環境讀書
  改為宣告技能。結算順序位置（`magic_study` 位於性狀態衰減與每日重置之間）不變；
  stage 改名 `practice_settlement`，設計文件的時鐘章節修訂記錄於此。
- 批次備註：結算讀的是行動玩家自己的宣告；其他隊員的 skip 由各自的命令獨立結算。

## 12. D8 — 技能系譜面板（lineage ledger）

純 read model，新模組 `world/rules/lineage_query.py`，全部由
`db.skill_proficiency` 與 registry 前置資料導出。無新持久狀態、無新寫入者。

```python
@dataclass(frozen=True)
class LineageNodeView:
    skill_key: str
    display_name_zh: str
    owned: bool
    usable: bool                    # can_use_skill right now
    level: int
    xp_into_level: float
    xp_to_next_level: float         # 50 - xp_into_level, 0 when capped
    capped: bool
    prereq_text_zh: str             # "需「火球術 Lv.3」" / "" when root/unlocked
@dataclass(frozen=True)
class LineageChainView:
    root_skill_key: str
    element_or_style_zh: str
    nodes: tuple[LineageNodeView, ...]   # topological order
    consumed: bool                        # every node capped
    meter: float                          # 0..1 shallowest-uncapped progress
@dataclass(frozen=True)
class LineageView:
    chains: tuple[LineageChainView, ...]
    completed_count: int
    total_count: int
```

- **WebClient**：新 icon 開啟大視窗。展開的鏈逐節點渲染等級與 XP 量表
  （`xp_into_level / 50`，例如「23/50 → 下一階」），未解鎖節點附具體前置文字；收合
  的鏈渲染一條鏈級量表；標頭顯示 `已完成 3 / 11 鏈`。一切由 view 渲染，客戶端零規
  則。新 OOB 契約常數依 frozen-contract 流程走四鏡像（protocol validator、panel
  view、JS validator、邊界測試），使用慣例的 `LINEAGE_MAX_*` 上限。
- **Telnet**：`lineage` 命令印出同一棵樹，見頂節點標記「見頂」，未解鎖節點附
  `prereq_text_zh`。命令文件 invariant 照走（`docs/game/commands.md`、
  `docs/game/command-reference.md`、`tests/test_command_docs.py`）。
- 解鎖瞬間沿用既有 toast/menu 通道推 OOB 通知（「新法術可用：火焰風暴」）。

## 13. D9 — Change 切分與 cutover 清單

**Change 1 `magic-power-trait-demotion`**（對戰鬥行為零變更；刪掉舊成長寫入者）：

- `traits.py` keys；`lore/races.py` 與 tier 帶（四維）；`lore/magic.py` 稱號
  registry 刪除。
- 執行 §7 刪除對照表；過渡期使用門檻僅 ownership（系譜在 change 2 落地；兩個
  change 都在任何 release 之前完成，無門檻的過渡態不會出貨）。
- `combat.py`、`displayed_stats.py`、`equipment_effects.py`、
  `character_creation.py`、`imports/`（schema、validate、example）、
  `quests/scene_builder.py`、`buffs.py` 目標改名、skills registry 前綴改 key。
- Webclient 鏡像與 vitest fixtures；文件部分僅當玩家可見措辭變更時動命令文件。
- 聚焦測試：`world.rules`、`world.imports`、`world.skills`、`typeclasses`；除非測試
  模組搬移，分片清單不動。

**Change 2 `use-driven-progression`**（依賴 change 1）：

- `SkillDef.prerequisites`、載入驗證、反向邊上限；`can_use_skill` 接入
  resolver/preview/選單；freeform 改錨。
- 練習累計泛化（含物理技能）、考試隔離檢查、去重暫存器、上限飽和。
- `skip ... practice <skill>` 命令與 `practice_settlement` stage 改名；匯入
  auto-seed。
- `lineage_query.py`、OOB 契約、webclient 面板、`lineage` 命令與兩份命令文件；新測
  試模組於同一 change 登記進 `.github/evennia-shards.json`。

**Change 3 `title-system`**：見搭檔文件，獨立推進。

## 14. 測試

- **純 `unittest`**（`world/rules/tests/`）：前置圖形驗證（環、懸空 key、root、`min
  >= 1`）；`can_use_skill` 矩陣（owned、缺前置、等級不足、恰好達標）；按消費者導出
  上限（鏈頂預設 10、中段取 max）；去重 key 語意（同目標同 tick 只計一次、不同目
  標、AOE）；練習結算閉式（僅 SKIP、倍率合成、上限飽和、rest 與未標註零成長）；
  freeform 階梯帶；物理技能的 `can_use_skill` 路徑與法術完全一致。
- **Evennia 整合**：使用在同一筆提交內累計、於強制提交失敗時完整還原（沿用既有原
  子施放故障注入模式）；考試零累計；完整戰鬥序列證明擊殺零成長；loader auto-seed
  滿足系譜、明確熟練度優先、畸形匯入仍然 all-or-nothing 拒絕；`magic_power` 為
  static（已無任何寫入路徑殘留）；`lineage` 命令輸出；webclient 面板渲染 view（本
  地跑一個 browser class，完整 browser suite 歸 CI）。
- **Traceability**：`magic-level-progression` 除役；`element-affinity-progression`
  改錨到練習乘數；`skill-proficiency-tracking` 折進新的
  `use-driven-progression` capability spec。ID 一律經 `tools.spec_traceability
  list` 取得；`covers_requirement` 標在建立斷言的測試上。

## 15. 錯誤處理（穩定原因碼）

| 情境 | 行為 |
|---|---|
| 前置 key 未知、有環、或 `min < 1` | registry 載入即拋例外（匯入期，點名違規者） |
| `skip practice` 指向未擁有技能 | `PRACTICE_SKILL_UNKNOWN`，時鐘零推進 |
| `skip practice` 指向見頂技能 | `PRACTICE_SKILL_CAPPED`，時鐘零推進 |
| 使用門檻失敗 | 沿用既有拒絕介面，原樣呈現缺哪個前置與需求等級（資料來自 registry） |
| 非有限數倍率輸入 | 既有 fail-closed 驗證器在任何寫入前拋例外 |
| 成長寫入在交易中失敗 | 既有 snapshot/restore 把熟練度還原到行動前值；新面必須向 snapshot handler 登記，否則登記時即拋例外 |

## 16. 世界觀語意

成長敘事維持 registries 已經使用的西方奇幻語域：成長是冒險者以實務鍛練技能，更深
的技巧隨著基本功純熟而解鎖。術師與戰士 build 共用完全相同的機器；種族差異只剩學
習速度加上種族天賦基值。除役的「學徒→賢者」稱號帶不以數值形式殘留；這些詞（學
徒、術師、大師、賢者、主宰）僅作為 cost-tier 資料標籤保留，與法術 registry 註解現
行的用法一致。敘事性頭銜由稱號系統（搭檔文件）與公會位階承擔。

## 17. 對權威來源文件的修訂

本文件對 `2026-07-29-ai-mud-engine-design.md` 修訂如下：

- §3.2 路線圖 row 11b（`character-progression`）被取代：XP 與魔法等級成長刪除；該
  row 剩下的目的（成長倍率的練習結算消費者）改指向 change 2 後存活。
- §6 trait 模型：`COUNTER_KEYS` 失去 `magic_level`；固定屬性為 D1/D2 所述的四個。
- 時鐘結算章節：`magic_study` stage 變成 `practice_settlement`（位置相同、僅
  SKIP、內容改為宣告技能）。
- 公會位階考試的 XP 隔離（D12）保留並強化：考試不給任何種類的成長。
