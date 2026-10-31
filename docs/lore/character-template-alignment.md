# 角色模板對齊審查紀錄

## 1. 審查結論與範疇

本文件是八張玩家角色模板（`world/lore/player_presets/data_pack_cards.py` 與
`data_story_cards.py` 的 `PLAYER_PRESET_REGISTRY`）在
`align-character-template-development` 這次對齊後的審查權威：開局技能組、宣告式練習
XP、精通選擇、天生數值與角色描述的最終內容，以本文件為準。

審查範圍：

- 四張精靈卡（希爾溫、悠花、悠奈、伊洛希雅）的一般學習廣度。
- 莉茲婭與薇歐蕾特的武器與術法訓練。
- 艾莉莎、娜茲卡、希爾溫、薇歐蕾特的角色描述用語修正。
- 四張故事卡的來源註解與天生數值敘述。

不在本次範圍：規則程式、效果定義、種族／亞種數值帶與配點預算、裝備與偽裝數值、
同行夥伴關係、既有專門技能與被動、任何血脈閉包或 seed 機制。

## 2. 兩條核心不變式

1. **配點是增量，不是最終值。** `allocations` 每一軸都是對該種族／亞種下限的
   增量；啟動時最終值 = 該軸下界 + 配點，物理三軸（`atk_phys`／`agility`／
   `defense`）再乘上亞種的靜態修正，`magic_power` 可配但無修正。
2. **天生數值固定，熟練度靠後天。** 卡上的天生數值不得因為「學習」或「鍛鍊」的敘述
   而改變；學習寫進技能與練習 XP，不寫進天生數值。

## 3. 核准的一般根基線矩陣

「一般根」＝技能登錄表中同時符合下列條件的節點：`ACTIVE`、沒有前置、類別屬於
`elemental_magic`／`martial_arts`／`divine_mystery`、對該卡種族與亞種身分資格相符，
且不是 `basic_attack` 這類人人天生持有的通用動作。六個僅限魔物物種的根
（例如 `grain_shaking_peck`）依身分資格排除。

| 學習領域 | 目前實作且資格相符的根 |
| --- | --- |
| 火 | `fire_arrow` |
| 水 | `tide_pull`、`water_bolt` |
| 風 | `gale_step`、`wind_blade` |
| 土 | `stone_shard`、`hardened_skin` |
| 雷 | `static_ward`、`spark_shock` |
| 冰 | `frost_breath`、`ice_shard` |
| 光 | `heal`、`light_arrow` |
| 暗 | `weaken`、`shadow_bolt` |
| 共通劍術 | `basic_swordplay` |
| 共通影武藝 | `shadow_slash` |
| 共通神之秘法 | `dominion_art`、`mentors_covenant`、`status_disguise` |

入門等級一律 Lv.1（50.0 XP），只有下列具名例外更高。四張精靈卡都持有這整份根基線；
人類卡不套用（其內容各依所屬卡的既定設計）。

## 4. 精通與宣告式 XP 的優先序

精通（`fire_mastery`／`dark_mastery`／`wind_mastery`／`light_mastery`）的前置宣告
閉合了整個元素的樹，啟動時由共用閉包補齊所有祖先、由共用 seed 把每個未滿足的前置邊
播到剛好達標。**宣告式 XP 永遠壓過 seed**，所以失敗條件是：在精通閉包裡的尋常魔法
成員寫下**低於該條需求邊**的字面值（哪怕只是 Lv.1），該坐標就會反過來壓低精通所需的
終端等級，使精通失效。落在精通閉包之外、屬於其他血脈的鍵不受此限——例如帶闇屬性傷害
的武藝根 `shadow_slash` 仍在武藝樹裡照常宣告自己的字面值。因此：

- 悠花、悠奈（火＋闇精通）不在火／闇的尋常魔法成員上寫任何字面 XP。
- 伊洛希雅（風＋光精通）不寫任何風／光字面 XP。
- 希爾溫與薇歐蕾特沒有精通，全部字面宣告。

## 5. 各卡核准內容

| 卡 | 保留的既有深度 | 本次新增 | 精通 | 高於 Lv.1 的顯式值 |
| --- | --- | --- | --- | --- |
| 希爾溫 `sylwen_stillwater` | `defense_instinct`、`elf_longevity`、盾與重甲裝載 | 完整一般根基線 + `flowing_strikes`、`body_enhancement`（×100） | 無 | `hardened_skin`、`heal`、`basic_swordplay` 各 Lv.3 |
| 悠花 `yuka_darknight` | `dual_blade_waltz`、`shadow_slash`、`status_disguise`、雙刀架式、移動、轉生特典、×1000 身體超強化 | 非精通元素的一般根 + `elf_longevity` | 火、闇 | `dual_blade_waltz` Lv.8、`shadow_slash` Lv.3 |
| 悠奈 `yuna_darknight` | `divine_sexual_arts`、`status_disguise`、性魔法專門、移動、×100 身體強化 | 非精通元素的一般根 + `elf_longevity` | 火、闇 | — |
| 伊洛希雅 `elosia_shadowmoon` | `dominion_art`、`status_disguise`、移動、×100 身體強化 | 非風／光元素的一般根 + `elf_longevity` | 風、光 | — |
| 薇歐蕾特 `violet_altoria` | `fire_ball`、`wind_blade`、`magic_circle_comprehension`、`precise_mana_control`、`flight` | `fire_arrow` | 無 | `fire_arrow`、`fire_ball`、`wind_blade` 各 Lv.3（皆在扣除前置後的樹冠上限內） |
| 莉茲婭 `lidzia_rosenthal` | `basic_swordplay`、`body_enhancement_basic`、隨從武藝訓練、護主本能 | `flowing_strikes` | 無 | `basic_swordplay` Lv.3（`flowing_strikes` 的前置邊） |
| 艾莉莎 `elysa_snow` | 技能組不動（`basic_swordplay`、`body_enhancement_basic`） | — | 無 | — |
| 娜茲卡 `nazka_bloodfang` | 技能組不動（`gale_step`、`flash_step`、風親和） | — | 無 | — |

悠花、悠奈、伊洛希雅三人另補上純敘事的 `elf_longevity`（希爾溫原本就有）。
悠花維持只有 ×1000 身體超強化，不疊加 ×100 或 ×1.2。悠奈與伊洛希雅維持 ×100。

## 6. 原始最終天生數值（未變更）

以下數值由 `resolve_preset_values()` 以現行種族帶與配點算出，本次對齊沒有改動任何
配點 tuple 或天生數值；HP／MP／SP 皆為 10000（精靈）。

| 卡 | 配點（增量） | `atk_phys`／`agility`／`defense` | `magic_power` |
| --- | --- | --- | --- |
| 希爾溫 | 12／12／13，魔力 400 | 82／82／83 | 500 |
| 悠花 | 18／22／20，魔力 377 | 88／92／90 | 477 |
| 悠奈 | 0／0／22，魔力 415 | 70／70／92 | 515 |
| 伊洛希雅 | 0／0／25，魔力 412 | 70／70／95 | 512 |
| 薇歐蕾特 | 4／5／4，魔力 51 | 5／6／6 | 56 |
| 莉茲婭 | 6／8／7，魔力 23 | 8／9／7 | 28 |
| 艾莉莎 | 10／10／11，魔力 43 | 11／11／12 | 48 |
| 娜茲卡 | 15／15／15，魔力 14 | 18／22／17 | 15 |

精靈的全能天生強度與「魔力極高」的高魔敘事都維持不變；專精描述的是後天深度。

## 7. 角色描述與註解修正

- **艾莉莎**：`emphasis` 與背景末句改寫成「十年抄寫之餘練出來的劍術與基礎強化」，
  不再用配點／最佳化的說法描述角色定位。
- **娜茲卡**：`emphasis` 由「近身作戰優先」改為「遠程斥候優先」。她是狐人族信使，
  以風系移動與長弓、飛斧作戰，沒有任何天生 ×1.2 的宣告。
- **希爾溫**：`emphasis` 與背景改為「劍盾守護是本分，元素防護與光系療癒是後天練成」，
  並保留她原有的防禦定位、裝備與數值。
- **薇歐蕾特**：`emphasis` 改為「天生高魔力、風系操控後天練成」，不給精通、也不弱化
  高魔敘事；天生魔力 56 與 5／6／6 的物理值不變。
- **悠花**：移除「剩餘預算把魔力推高到故事值 250 以上」這類錯誤註解，改為正確陳述：
  配點是對基亞蘭下限的增量，最終天生魔力 477，×1000 身體超強化是技能不是配點。
- **悠奈**：同上，最終天生 70／70／92、魔力 515。
- **伊洛希雅**：移除 873 級、「超過創造上限」與「魔力是精靈平均百倍」這些過期且與
  數值不符的數字（她的轉生特典是風屬性練習 ×5，不是天生魔力倍率），改為「天生就
  超越同齡精靈的魔力（最終 512）＋後天練出的各系術法熟練度」；背景敘述同步改成天生
  魔力與學習熟練度。
- **莉茲婭**：配點與天生 8／9／7、魔力 28 維持不變；文書與行政能力維持敘事不增機制。

## 8. 來源決策與已退役的鍵

- 已核准的非性事實一律以**追蹤檔案**（`world/lore/` 登錄表與本文件）重新撰寫後才成為
  種子權威；忽略的個人參考 `tmp/story_settings/` 不具權威、永不進入執行期、也不進入
  提交，僅作為來源出處。
- `light_sword_style`（光劍架式）已於 commit `40c254d233f85b8d880e0a5dc90ca2866a0d7e72`
  退役；追蹤檔案中已無殘留引用，唯一現存出處是忽略檔
  `tmp/story_settings/character/LidziaRosenthal.md:40`。莉茲婭對應的訓練改以共通的
  劍術訓練 `basic_swordplay` 加上第二式 `flowing_strikes` 表達；不恢復舊鍵、不加別名、
  不改寫歷史紀錄或封存變更。
- 影武藝的一般根 `shadow_slash` 是公開技藝，不需要雙持架式；只學根基線的角色不會因此
  獲得架式或更深層的影技。

## 9. 自動化證據與呈現層上限

- `world/lore/tests/test_player_presets.py`：由登錄表自身推導一般根集合與身分資格，
  斷言每張精靈卡都持有並正向發展每個根、且沒有任何已擁有技能留下未滿足的前置邊。
- `world/rules/tests/test_character_creation/test_preset_activation_kit.py`：以合成卡
  走真實啟動、精通閉包、seed、可用性與提交後重讀，並保留一個未啟動的對照角色。
- 角色面板的 actives 列上限 `MAX_ACTIVE_ROWS` 由 96 提高到 128：完整根基線讓悠奈的
  合法 active 列達到 102 列（含 58 個解鎖的性愛技藝列），舊上限會讓面板失敗關閉。
  上限仍是失敗關閉的 wire guard，不是截斷機制；主規格
  `webclient-exploration-menu` 以本變更的 delta 同步該數值。
