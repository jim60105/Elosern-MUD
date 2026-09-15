# 身心強化：取得條件一覽

身心強化（`ENHANCEMENT`）是整個遊戲的「取得型被動家族」（Acquired passives），底下的技能絕大多數為 PASSIVE，持有即生效，不走 `SkillPrerequisite` 練習系譜。本分支除了通用被動與倍率鏈外，亦整合了移動增益（「身法」顯示標籤）與先天特質（「天賦」顯示標籤），這裡改用**取得條件**交代每個技能落到角色身上的途徑。

## 身體強化倍率鏈

三個倍率技能彼此不互斥，但敘事上通常代表同一個角色一生中最多只會落在其中一個區間：

| Key | 名稱 | 倍率 | 取得條件 |
| --- | --- | --- | --- |
| `body_enhancement_basic` | 基礎身體強化 | ×1.2 | 完成所屬機構（人類騎士學院、獸人部族成年禮、冒險者公會晉升考核）認可的基礎戰鬥訓練，人類與獸人皆可透過長年苦練達成，是唯一「後天努力就能取得」的一階 |
| `body_enhancement` | 身體強化 | ×100 | 精靈血統出生即帶有；非精靈唯一已知的取得方式是劇情授予的「轉生特典」一類天賦異能，無法透過訓練跨過這道門檻 |
| `body_enhancement_extreme` | 身體超強化 | ×1000 | 僅頂尖精靈或握有特殊天賦異能者，劇情授予，全大陸屈指可數 |

## 其他被動精煉技能

以下技能不改變施法者能學會什麼，只讓既有能力發揮得更好，取得條件分成三類：**種族天生**、**劇情授予／匯入**、以及本設計新增的**跨系譜門檻自動授予**。後者指角色在其他系譜樹達到特定深度時，敘事上自然而然「悟出」對應的被動精煉，不需要另外練習這個被動本身：

| Key | 名稱 | 取得條件 |
| --- | --- | --- |
| `defense_instinct` | 防禦直覺 | 劇情授予／匯入，常見於長年擔任護衛或前線戰鬥角色 |
| `blade_art_mastery` | 劍術精通 | 跨系譜自動授予：武藝系譜「劍術路線」任一節點達到熟練（Lv.3）以上時視為已悟出 |
| `extreme_endurance` | 極限耐力 | 劇情授予，常見於長期高強度體能訓練者（如刀術狂熱者、獸人戰士） |
| `magic_circle_comprehension` | 魔法陣理解 | 跨系譜自動授予：任一元素系譜樹的任一節點達到大師（Lv.5）以上時視為已悟出陣文結構 |
| `precise_mana_control` | 精準魔力控制 | 跨系譜自動授予：任兩條不同元素系譜樹的節點皆達到大師（Lv.5）以上時觸發，代表對魔力運用的通用理解已經超越單一屬性 |
| `retainer_martial_training` | 隨從武藝訓練 | 劇情授予，僅授予擔任他人隨從／侍從職務的角色 |
| `guardian_instinct` | 護主本能 | 劇情授予，僅授予以守護特定對象為職責的角色 |
| `concentration` | 集中 | 例外：這是本分支唯一的 ACTIVE 技能（自我增益，效果：專注 +5、命中 +5，持續 60 秒），任何角色取得即可直接使用，不需要額外門檻 |

## 為什麼這樣設計

「跨系譜自動授予」把身心強化從一組孤立的旗標，變成元素魔法與武藝系譜深度的**副產物**。一個把兩條元素系譜都點到大師位階的施法者，理應對魔力運用有更全面的直覺，`precise_mana_control` 就是這份直覺的機制化身。這個機制刻意獨立於 `SkillPrerequisite`（檢查的是其他系譜樹節點的熟練度是否達標，不消耗某個技能的使用次數），下一階段實作時建議另開一張「跨系譜自動授予規則表」獨立維護，不必併入系譜前置圖。

## 身法標籤被動技能（移動豁免）

以下技能機制分類屬於身心強化分支（`category=SkillCategory.ENHANCEMENT`），並以 `group="身法"` 標籤呈現於介面，免除特定移動消耗或限制。詳細力量來源與敘事見 [身法：取得條件一覽](/lore/skill-trees/movement)：

| Key | 名稱 | 效果 | 取得條件權威 |
| --- | --- | --- | --- |
| `flight` | 飛行術 | `movement:flight`，免除荒野移動費用 | [身法頁面](/lore/skill-trees/movement) |
| `flash_step` | 瞬步 | `movement:flash_step`，近距位移 | [身法頁面](/lore/skill-trees/movement) |

## 天賦標籤特質技能（與生俱來／機緣賦予）

以下技能機制分類屬於身心強化分支（`category=SkillCategory.ENHANCEMENT`），並以 `group="天賦"` 標籤呈現於介面，無法透過常規訓練習得。詳細效果與敘事見 [天賦異能：取得條件一覽](/lore/skill-trees/innate-gift)：

| Key | 名稱 | 效果 | 取得條件權威 |
| --- | --- | --- | --- |
| `elf_longevity` | 精靈長壽 | `passive_trait:elf_longevity` | [天賦異能頁面](/lore/skill-trees/innate-gift) |
| `reincarnation_boon_elosia` | 轉生祝福·伊洛希雅 | `growth_rate:practice:100` | [天賦異能頁面](/lore/skill-trees/innate-gift) |
| `reincarnation_boon_yuka` | 轉生祝福·悠花 | `combat_prediction:武感` | [天賦異能頁面](/lore/skill-trees/innate-gift) |
