# 情慾秘術：分類定位與目錄結構

情慾秘術是獨立於元素魔法與神之秘法之外的技能分類（`SkillCategory.SEXUAL_ACT`），與光明教會信仰體系、精靈族生理特質緊密相關。它不走「使用次數換算等級」的熟練度系譜樹（見 [總覽與機械規則](/lore/skill-trees/index) §2），而是以**行為目錄＋終身計數器解鎖**的骨架運作：招式本身就是技能，能不能使出取決於這具身體做過什麼。本頁描述現行實作（`world/skills/sexual_acts/`）的完整分類結構。

## 分類位置

| 項目 | 說明 |
| --- | --- |
| 對應分類 | `SkillCategory.SEXUAL_ACT` |
| 技能形態 | 絕大多數招式為 ACTIVE、零消耗（`cost={}`）、可戰外施展、無屬性歸屬；每招同時登記進 `SKILL_REGISTRY`（技能面）與 `SEXUAL_ACT_REGISTRY`（行為面 sidecar） |
| 資源與判定 | 不耗 MP、不進熟練度曲線；門檻是存在於 `SexualState`（`world/rules/sexual_state.py`）的**終身行為計數器**與施法時的**抗性判定** |
| 解鎖階梯 | 由每招自帶的 `unlock` 計數器門檻表把關（全部條件為 AND，空表＝人人可使）；統一入口 `unlocked_act_keys_for()` |
| 神性門檻 | 神之秘法線與頂點被動「性魔法主宰」（`divine_sexual_mastery`）、悠奈簽名技「神之秘法：性愛系統」（`divine_sexual_arts`）共用 `requires_divine_arts` 閘門，規則上唯精靈可及 |

## 六條路線（`group` 欄）

目錄由六個路線模組構成，共 66 個行為（`divine_sexual_mastery` 另有登記於主冊）：

| 路線 | 模組 | 行為數 | 定位 | 主計數器軸 |
| --- | --- | --- | --- | --- |
| 獨處 | `solo.py` | 14 | 自我探索：手、玩具、拘束 | `masturbation_count`、`toy_use_count` |
| 關係 | `partner.py` | 18 | 伴侶互動：愛撫、口舌、交合、多人 | `duo_act_count`、`group_act_count`、`climax_count` |
| 羞恥 | `shame.py` | 10 | 露出與觀看：衣襬到無恥宣言 | `exposure_act_count`、`watched_count` |
| 戰鬥 | `combat.py` | 9 | 對敵施為：挑逗到絕頂支配 | `hostile_act_count`、`climax_count`、`climax_extension_count` |
| 異種 | `interspecies.py` | 7 | 對魔獸施為／承受 | `hostile_act_count`、`interspecies_act_count`、`climax_count` |
| 神之秘法 | `divine.py` | 8 | 刻意打破前五條線平衡的神之律令 | 無（計數器門檻不適用；簽名技走持有門檻） |

### 解鎖階梯一覽（實作門檻）

| 路線 | 階梯（AND 語意） |
| --- | --- |
| 獨處 | 種子 3 招無門檻 → 中階 5 招 `自慰≥10` → 玩具 3 招 `自慰≥25` → 高階玩具／拘束 3 招 `自慰≥25 且 玩具≥15`（玩具招同時計兩軸） |
| 關係 | 種子 2 招（愛撫、牽手）→ 4 招 `雙人≥5` → 5 招 `雙人≥15` → 交合群 4 招 `雙人≥30 且 高潮≥10`；多人線：多人愛撫 `雙人≥30`、多人交歡 `多人≥15`、群體服務 `多人≥30` |
| 羞恥 | 撩起衣襬無門檻 → 半露群 `露出≥5` → 全露出 `露出≥20` → 公開自慰 `露出≥20 且 自慰≥25`；觀看軸：挑釁凝視 `被看≥10`、公開表演 `被看≥10 且 露出≥20`、獻身姿態 `露出≥50`、無恥宣言 `露出≥50 且 被看≥30` |
| 戰鬥 | 挑逗無門檻 → 耳語／觸碰 `敵對≥5` → 魅惑／束縛愛撫／強制快感 `敵對≥20` → 強制絕頂／連續責め `敵對≥40 且 高潮≥30` → 絕頂支配（範圍）`敵對≥80 且 延長≥30` |
| 異種 | 觸碰／愛撫 `敵對≥10` → 纏繞／承受 `敵對≥30` → 異種交合 `敵對≥30 且 高潮≥20` → 支配／共鳴 `異種≥20` |
| 神之秘法 | 全線 `unlock={}`——計數器永不把關，守門的是施法當下的血統閘門（見下）；唯悠奈簽名技 `divine_sexual_arts` 為 `ownership_gated`，只認實際持有，計數器與主宰全解都繞過它 |

階梯的敘事邏輯：每條線都是一部**身體史**。解鎖不是研讀，是經歷——目錄本身就是「性經歷即修行」這條世界觀機制的直接體現，也是 [光屬性系譜樹](/lore/skill-trees/light) 聖禮路線刻意與之分離（走熟練度）、只在狀態層共享興奮／高潮系統的原因。

## 終身計數器（11 軸）

`SexualState` 暴露 11 個單調遞增的終身計數器，每個只有一個正名 mutator：

`masturbation_count`、`toy_use_count`、`exposure_act_count`、`watched_count`、`duo_act_count`、`group_act_count`、`hostile_act_count`、`restraint_count`、`interspecies_act_count`、`climax_count`、`climax_extension_count`。

計數語意的目錄慣例：**無方向計數器**（`hostile_act_count`、`interspecies_act_count`）記錄「兩個身體之間發生了事」，經 `participant_counters` 同步記給所有其他參與者；**有方向計數器**（`exposure_act_count`、`watched_count`、`masturbation_count`）記錄單一身體獨自做過／承受過什麼，只記施為者（`actor_counters`）。`climax_count` 與 `climax_extension_count` 由高潮結算機制（`climax_settlement_action`：結束計前者、延長計後者）在每週期結算時遞增，與每日計數 `climax_today` 互不干涉。`restraint_count` 目前不由任何招式門檻消費，留給拘束系後續內容。

## 招式資料結構（`SexualActDef` sidecar）

每個行為的技能面之外，凍結資料類 `SexualActDef` 攜帶：

| 欄位 | 語意 |
| --- | --- |
| `unlock` | 計數器→門檻映射（AND；構造時鎖為唯讀） |
| `base_pleasure` | 正整數基準快感值（現行目錄實帶 3–34），乘上目標側加算後經 `_apply_pleasure_gain` 唯一入口注入 pleasure 計 |
| `actor_pleasure_ratio` | 施為者自身獲得的快感比例（獨處 1.0；伴侶線 0.5–1.0；戰鬥線壓到 0.4–0.6——對人施為時自己爽得少）；一般線必須為正，僅神之秘法線可為 0 |
| `actor_part`／`target_part` | 觸碰部位，取 `BODY_PARTS` 十部位（口唇、頸項、耳朵、乳房、腰腹、臀部、大腿、足部、私處、後庭）；部位敏感帶隨使用個別強化。異種與神之秘法為**無部位線**（target 一律為魔獸／神性抽象，不得宣告部位；魔獸端折疊進通用部位「軀體」） |
| `actor_counters`／`participant_counters` | 見上節方向語意 |
| `sexual_events` | 該招發射的狀態事件名（見事件詞彙） |
| `resistible` | 對他人的招式為 True、對自己的招式為 False——目錄層直接寫死「不會有人對自己反抗」 |
| `pair_events` | （選填）依雙方 `sex` 在施放當下選擇發射的事件：交合／深度交合以此實裝異性分支（初次的陰道插入對雙方打破 `virgin`；否則發射 `penetrative_sex_with_female`／`penetrative_sex_with_male`），僅限單體招 |

`_act_family()` 在 import 期做結構驗證（門檻型別、部位合法性、禁用事件、pair_events 契約），目錄作者的錯誤在載入時炸掉而不是在遊玩時炸掉。

## 效果字串與事件詞彙

技能面 effects 清單由 builder 自動生成：`pleasure:<key>`、`sexual_counter:<key>`、每個事件一條 `sexual_event:<name>`（參與者範圍）或 `sexual_event_actor:<name>`（施為者範圍），宣告 `pair_events` 時附一條 `act_pair_event:<key>`。

- **施為者範圍事件**（狀態屬於做這件事的人）：`self_exposure`、`public_exposure`、`public_sexual_activity`、`watched_during_activity`（後者僅在同在場觀察者存在時發射）。builder 強制走 actor 字首，目錄作者無法誤掛。
- **參與者範圍事件**（現行目錄）：`masturbation_climax`、`breast_sex_performed`、`sexual_activity_with_nonhuman`，以及 pair_events 的三個性狀條件事件。
- **招式永不得宣告**：`stimulus_applied`／`sustained_stimulus_applied`／`extreme_stimulus_applied`（直接推 pleasure 計，會與招式自身加算重複計數）與 `climax_ends`／`climax_extended`（高潮結算機制專有）。高潮的觸發與結束屬於**狀態機與世界時鐘**，不屬於任何一招——這是 [光屬性系譜樹](/lore/skill-trees/light) 的天賜高潮能安全借用同一套邊緣推進而不與招式打架的原因。

## 抗性判定與服從短路

`resistible=True` 的招式在生效前經 `resist_verdict()`（`world/rules/sexual_resist.py`）二元競賽：雙方分數混合有效敏捷與物理攻擊，抵抗方再取親和階級修正。擲骰之前有三條**自動服從短路**：

1. NPC 抵抗者對玩家親和達 `至愛`／`絕對羈絆`（超過自然上限的信任，擲骰無法保證服從，規則直接判定）；
2. 抵抗者身上有該施法者的 `submission_marks`（絕對從屬印記，見神之秘法線）；
3. 抵抗者正處於高潮進行中的**前 5 個結算點**（`climax_turn_auto_comply_limit: 5`）——高潮中的身體無法反抗，之後恢復正常擲骰。

被**強迫**（既非自願服從也非抵抗成功）的結算會扣減 NPC 對施法者的親和（戰鬥內外各有一條掃描管線），自願與抵抗成功不扣。抵抗判定會消耗一個戰鬥行動。

## 頂點：神性門檻與主宰解鎖

- **性魔法主宰**（`divine_sexual_mastery`，PASSIVE）：效果 `sexual_magic_mastery` 是一條**全面解鎖**——持有者無需計數器即可使出前五條線的全部行為；但它明確**不涵蓋神之秘法線**（主宰與神性兩條取得途徑互不相干），且只認持有者本身的直接擁有，轉授不生效。
- **神之秘法：性愛系統**（`divine_sexual_arts`，ACTIVE）：悠奈簽名技，目錄第八對 hand-built 行。效果僅一條 `sexual_event_target:stimulus_applied`——「僅目標受效」的接收範圍由 `sexual_event_target:` 前綴 statically（施法當下之前、按字面前綴）決定，施法者永不吃到自己的刺激事件；它是光屬性 [`holy_kiss_heal`](/lore/skill-trees/light) 借用刺激幅度時的詞彙源頭。它也是全目錄唯一 `ownership_gated=True` 的行：血統閘門只擋血統，這招 additionally（除血統之外）只認實際持有——authored 資料面唯 `yuna_darknight` 一張卡宣稱它，計數器派生與主宰全解都繞過它，轉授更不是取得途徑。
- **神之秘法線 7 招**（皆 `requires_divine_arts=True`、無計數器門檻、無部位、可抵抗）：每招一條專屬效果字首——`divine_pleasure_max`（絕頂律令：無視加乘直接把 pleasure 推至封頂，雙邊前進）、`divine_climax_extension_stage:3`（時姦：一次施放堆 3 段延長）、`divine_drain`（神域搾取：目標快感轉為施法者 MP/SP/HP）、`divine_saturate_sensitivity`（感度創世：全部位敏感異常）、`divine_clamp_shame`（恥辱剝奪：羞恥永久釘在成癮；魔獸目標直接拒絕）、`divine_mark_submission`（絕對從屬：以施法者資料庫 id 植入永久自動順從印記）、`divine_restore_purity`（無垢回歸：逆轉 `virgin` 旗標）。封鎖由施法當下的 `_step1_divine_arts_gate` ＋ `RaceProfile.can_use_divine_arts` 承擔——血統就是守門員，目錄本身對所有人開放。

這七招是目錄中唯一**刻意打破平衡**的群：比例、門檻、可逆性全被神性豁免，呼應世界觀裡「神之秘法直接干涉世界之理」的定位，也解釋為何精靈把這批技法藏得比任何禁咒都深。

## 與相鄰系統的接縫

- **光屬性系譜樹**：兩軸完全獨立（計數器 vs 熟練度），共享同一套興奮等級、高潮期相循環與濕潤／敏感帶狀態；[`blessed_climax`](/lore/skill-trees/light) 借用 `divine_pleasure_max` 已驗證的雙邊推進路徑即屬此接縫。
- **戰敗後果**：戰敗侵犯結算（`world/rules/defeat_aftermath.py`）自行記入 `hostile_act_count`／`interspecies_act_count` 與勝利快感增量——目錄因此也會被**被動經歷**推進：被魔獸擊敗的冒險者會不自覺解鎖異種線。這是「性經歷即修行」最殘酷的一面，設計上刻意保留。
- **親和系統**：強迫結算扣親和、至愛／絕對羈絆短路抵抗——情慾秘術與親和系統互為因果。
- **羞恥與露出**：羞恥線事件推進 `shame` 狀態軸（無→輕微→中等→強烈→成癮，五級；`shame_multipliers` 讓它直接放快或扣減快感增益——成癮 1.6 倍是唯一超過 1 的異數），露出則走 `exposure` 軸（極低→低→中等→高→極高）疊加裝備 `exposure_bias` 形成有效露出，見 [光屬性系譜樹](/lore/skill-trees/light) 的露出計價。
