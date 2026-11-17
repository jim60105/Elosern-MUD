# Ciaran Local Goods Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `ciaran-village-local-goods` change. The change adds five goods 暗影谷村 now makes, takes four borrowed goods off its shelves, and rewrites the prose that has to agree with them, namely the cards of `ciaran_lareneth`, `ciaran_valwyn`, `ciaran_vethiel` and `ciaran_nireth`, one room description, four greetings and the scenes the change rewrites.

### Profile, Place and Dialogue Bindings

- `ciaran_lareneth_home` (place: 拉瑞內斯的家, host: 拉瑞內斯‧妮特布倫) -> `world/lore/dialogue/content/ciaran_lareneth.yaml`
- `ciaran_valwyn_home` (place: 瓦爾溫的家, host: 瓦爾溫‧斯蒂爾瓦特爾) -> `world/lore/dialogue/content/ciaran_valwyn.yaml`
- `ciaran_vethiel_home` (place: 維特希爾的家, host: 維特希爾‧威爾德布瑞亞爾) -> `world/lore/dialogue/content/ciaran_vethiel.yaml`
- `ciaran_nireth_home` (place: 妮瑞斯的家, host: 妮瑞斯‧米斯特瓦勒) -> `world/lore/dialogue/content/ciaran_nireth.yaml`

Each file keeps the profile key as its filename, keeps every topic and scene ID, and declares no owner field. The four shelves are `elven_fare`, `elven_sundries`, `elven_remedies` and `elven_attire` in `world/lore/settlements/assortments.py`, priced in `world/rules/rulebook/commerce/ciaran.yaml`.

### Canonical Sources

- `tmp/story_settings/world_info.md` (sections: 地理結構 › 中央山脈; 種族設定 › 精靈族 with 三分支 › 基亞蘭族; 社會結構; 生活方式 › 性文化; 對外態度; 特殊設定 › 精靈與外界互動).
- `docs/lore/overview.md` (精靈族, 性別與生殖, 性愛與身體).
- `docs/lore/settlement-locations.md` (精靈村落 in the location-type table; 防具店與裁縫坊 and 鍊金坊與藥舖 in 聚落差異; 聚落差異深論).
- `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_lareneth`) and `ciaran_homes_b.py` (`ciaran_nireth`, `ciaran_valwyn`, `ciaran_vethiel`).
- `world/lore/settlements/places_ciaran.py` (the four homes and their `dialogue_key` bindings).
- `world/lore/items/data_elven_village_goods.py` (the five new rows) and `world/rules/rulebook/item_effects.yaml` (the tincture's one effect).
- `content/maps/settlements/elven_village_ciaran.yaml` (溪畔小徑, 溪畔下游, 織房坡, 銀葉坡, 藥草園, 村北古樹下, 村中廣場).
- `content/maps/settlements/elven_village_eolas.yaml` (蛛絲林) and `elven_village_fionnen.yaml` (樹冠吊橋).
- `content/maps/interiors/ciaran_valwyn_home.yaml` (the room description).
- `skill://npc-dialogue-content` with `references/scene-schema.md`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

The world source makes 暗影谷村 the Ciaran branch's underground village on the western side of the central range, with brown skin, mostly silver hair and red eyes, fire and dark affinity, a deep blade culture and about a hundred people. It also states that elves have no fixed trades, that each branch develops on its own, and that the three branches visit one another now and then. The change rests every neighbour reference on that last fact.

---

## 2. Mandatory Lore Checks

### Standing, Rarity and the Absence of Commerce

- Canon: about three hundred elves exist across three branches, and the three human and beastfolk nations rank them above royalty. Elves need nothing from outsiders.
- Society: no fixed profession division, no caste, no apprenticeship, no marriage. The village has no shop as an institution, no posted hours and no proprietor; a villager makes what she loves in her own home and shares it with neighbours or the rare visitor.
- How the change reads it: no card, greeting or scene uses proprietor vocabulary. There is no counter, no sign and no stock count. The room is a room, the shelf holds what she finished this season, and copper is the village's way of looking after a guest.

### The Making Villages

- Canon: silk and the white dress belong to 幽月谷村's silk grove and its keeper 奈拉拉‧弗羅斯特威洛 at 蛛絲林; the dew veil belongs to 翠綠森林村's canopy weavers, 伊斯爾林‧斯塔爾威維爾 at 樹冠吊橋; the candied blossom belongs to 翠綠森林村's 花蕊蜜園. The 防具店與裁縫坊 passage already assigns the white silk robe to the Eolas branch and the black kimono to the Ciaran branch.
- How the change reads it: when a Ciaran host is asked about a removed good, she names the making village and its maker as a neighbour's fact, never as a refusal. 瓦爾溫 says spider silk belongs to 幽月谷村 and names 奈拉拉; 維特希爾 places the white silk robe in 幽月谷村 and the dew veil with 伊斯爾林 in 翠綠森林村. Both add that the branches visit one another. No Ciaran host claims to make or keep any of the four goods.

### Body, Dress and Demeanour

- Canon: elves have no concept of shame about nudity, the body or sex; clothing serves movement and beauty; other races look away out of awe rather than moral judgment; elves treat outsiders with calm indifference.
- How the change reads it: 維特希爾's 禮袍 scene keeps the dark elves' own short robe as everyday dress, close at the collar and waist and open at the hem, and she says plainly that a body is worth showing and that outsiders look away at first. No scene stages a sexual act, and no actor line grants consent or initiates one.

### Religion

- Canon: elves never proselytise, and outsiders do not know their faith or the truth of the three goddesses.
- Host handling: none of the four hosts teaches theology, names a goddess or explains a divine chain.

---

## 3. Retained Service Behaviours and Assortment Consistency

All four homes keep their authored place binding without alteration.

- `ciaran_lareneth_home` stocks `elven_fare` (暗影谷夜綻花釀, 暗影谷炭烤蕈串). She brews and roasts both herself; her 收回 answer takes back unopened jars and states that skewers are best eaten warm, so she promises no return of food outside a sound jar.
- `ciaran_valwyn_home` stocks `elven_sundries` (暗影谷藍染, 暗影谷晶砂). She presses the dye from the shoal's plants and pans the sand from the stream; her 以物易物 answer takes back only her own unused dye and crystal sand. The crescent earrings stay a display keepsake and the guest is sent to 格威娜拉 at 銀葉坡.
- `ciaran_vethiel_home` stocks `elven_attire` (精靈短袍傳統服飾, 精靈戰鬥服飾). She weaves both from plant-dyed thread; her 舊衣 answer takes back only those two garments and refuses outside cloth.
- `ciaran_nireth_home` stocks `elven_remedies` (暗影谷解毒草露, 強效治療藥水, 魔力藥水). She brews all three from her own garden; her 藥草 answer takes back sealed, unopened jars and refuses outside herbs.

Every offer in `world/rules/rulebook/commerce/ciaran.yaml` sits inside its item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper`, and each good the capital also sells is cheaper here. The tincture removes only `poisoned`; the holy water keeps its broader `negative` selector. No line of dialogue delivers a free remedy, a custom commission, a discount or a price figure, and the scenes name goods by their registry display name and state no quantity.

---

## 4. Per-Host Review

Every rewritten scene opens with a complete actor utterance, holds six lines and carries at least one host line. Scenes whose lines changed declare `revision: r3`; untouched scenes and the familiar-visitor variant stay at `r2`. No topic gains, loses or renames an ID, and no topic declares a new condition.

### A. `ciaran_lareneth_home` (拉瑞內斯‧妮特布倫)

**Card and voice review.** The public leaf keeps the 花饌好手 of 溪畔小徑 and changes her best work to 暗影谷夜綻花釀; the appearance leaf keeps the dried flower in her hair and changes the honey-stained apron and candied-flower scent to syrup and night-bloom; the personality, speech and social leaves stay. The life story keeps the seasons she has tested and now names the night flower, and the habit gathers the flowers after dark and writes the picking date on every jar. The added sentence that the flower shares the meaning of her surname rests on 種族設定 › 精靈族 (a long memory and a name that carries its own story); it invents no place. `voice.misunderstood` is unchanged.

1. **Opening greeting**: she stirs syrup in the stone home beside 溪畔小徑, offers a taste of 暗影谷夜綻花釀 and asks the guest to sit and talk. Source: 種族設定 › 精靈族 (no fixed trades, a maker's own home); the 溪畔小徑 node.
2. `ciaran_lareneth_home.topic_01` (`keyword`: 花饌, `label`: 花饌): the night flowers open only after dark, she picks them as they open, and the petals steep a full season in syrup. Source: 種族設定 › 精靈族 › 生活方式 (the village lives by the valley's own seasons); the 暗影谷夜綻花釀 row.
3. `ciaran_lareneth_home.topic_02` (`keyword`: 山產, `label`: 山產): the valley's four seasons bring flowers, honey, fruit and rain-season mushrooms; mushrooms go onto skewers over embers as 暗影谷炭烤蕈串, and an unopened jar comes back whole. Source: 地理結構 › 中央山脈 (a hidden valley with its own produce); the 暗影谷炭烤蕈串 row.
4. `ciaran_lareneth_home.topic_03` (`keyword`: 茶點, `label`: 茶點): the low stool and tea are for whoever passes on the path; both local foods are shared, and a guest may ask for jars wrapped in leaves and cord and skewers in a lotus leaf. Source: 種族設定 › 精靈族 (sharing with the rare visitor, not a counter).
5. `ciaran_lareneth_home.topic_04` (`keyword`: 口味, `label`: 口味): Ciaran food stays light and natural, sugar is kept back so the flower's own scent survives, and the scene ends on 暗影谷夜綻花釀. Source: 種族設定 › 基亞蘭族 (a branch's own everyday life); the preserve row.

### B. `ciaran_valwyn_home` (瓦爾溫‧斯蒂爾瓦特爾)

**Card and voice review.** The public leaf keeps the 蒐羅者 of 村北古樹下 and her tagged stories, and replaces braided spider silk with the 暗影谷藍染 she presses and the 暗影谷晶砂 she pans; the appearance, personality and speech leaves stay, and the life story now walks the same streams for dye plants and sand. The social leaf already gives shells and crystal sand to 格威娜拉‧希爾維爾莉夫 and stays. `voice.misunderstood` is unchanged.

1. **Opening greeting**: she sets a stack of pressed blue dye on the shelf, turns in delight and offers the histories of her curios. Source: 種族設定 › 精靈族 (no fixed trades, a collector's own home); the 村北古樹下 node.
2. `ciaran_valwyn_home.topic_01` (`keyword`: 蒐羅, `label`: 蒐羅): the tagged feathers, seeds and shells stay display keepsakes, and a second host line adds the dye and the jar of sand she does share. Source: the host's card; the 溪畔下游 node.
3. `ciaran_valwyn_home.topic_02` (`keyword`: 藍染, `label`: 藍染): 暗影谷藍染 is pressed from the dye plants washed at the shallow shoal downstream, the blue of the cloth hung on 織房坡, and the host says plainly that spider silk is 幽月谷村's and that 奈拉拉‧弗羅斯特威洛 at 蛛絲林 weaves it best. Source: the 溪畔下游 and 織房坡 nodes; 種族設定 › 精靈族 › 社會結構 (the branches visit one another); the 暗影谷藍染 row.
4. `ciaran_valwyn_home.topic_03` (`keyword`: 耳環, `label`: 耳環): unchanged, including the familiar-visitor variant; the earrings stay Gwenaera's work and the guest is sent to 銀葉坡.
5. `ciaran_valwyn_home.topic_04` (`keyword`: 以物易物, `label`: 以物易物): she trades stories before copper and takes back only her own unused dye and crystal sand. Source: the host's card and the `elven_sundries` service.

### C. `ciaran_vethiel_home` (維特希爾‧威爾德布瑞亞爾)

**Card and voice review.** The public leaf keeps the 織衣者 of 織房坡 and now names 精靈短袍傳統服飾 and 精靈戰鬥服飾 as the two things she weaves, plant-dyed; the white silk dress and dew veil leave the card. The appearance, personality and speech leaves stay, the life story names the two garments, and the social leaf turns 瓦爾溫's braided silk into 暗影谷藍染 going into her dye pots. `voice.misunderstood` is unchanged. The greeting names colours only and stays.

1. **Opening greeting**: unchanged; she asks which colour the guest favours and invites a hand on the cloth. Source: 種族設定 › 精靈族 (a maker's own home); the 織房坡 node.
2. `ciaran_vethiel_home.topic_01` (`keyword`: 織衣, `label`: 織衣): the shelf holds the two dark-elf garments, both woven from thread dyed with the valley's plants. Source: 種族設定 › 基亞蘭族 (the branch's own dress); the 織房坡 node; the two item rows.
3. `ciaran_vethiel_home.topic_02` (`keyword`: 戰衣, `label`: 戰衣): unchanged; the ink-black battle dress is cut close for the forest and names no removed good.
4. `ciaran_vethiel_home.topic_03` (`keyword`: 禮袍, `label`: 禮袍): 精靈短袍傳統服飾 is the dark elves' own dress, close at the collar and waist and open at the hem; the host states the elven ease about the body, and one line places the white silk robe in 幽月谷村 and the dew veil with 伊斯爾林‧斯塔爾威維爾 at 樹冠吊橋 in 翠綠森林村. Source: 種族設定 › 精靈族 › 生活方式 › 性文化 and 對外態度; docs/lore/settlement-locations.md 防具店與裁縫坊 聚落差異; the 樹冠吊橋 node.
5. `ciaran_vethiel_home.topic_04` (`keyword`: 舊衣, `label`: 舊衣): she takes back only the two garments from her own loom, unpicks sound thread and refuses cloth woven elsewhere. Source: the `elven_attire` service.

### D. `ciaran_nireth_home` (妮瑞斯‧米斯特瓦勒)

**Card and voice review.** The public leaf keeps the 調藥者 of 藥草園 and adds 暗影谷解毒草露 beside the two potions; the appearance, personality and speech leaves stay, and the life story and social leaf already describe the garden and 海莉爾's burns. `voice.misunderstood` is unchanged.

1. **Opening greeting**: she damps the stove, looks over the guest's gait and shoulders and names the three remedies. Source: 種族設定 › 精靈族 (immune to illness, so her craft serves wounds and guests); the 藥草園 node.
2. `ciaran_nireth_home.topic_01` (`keyword`: 調藥, `label`: 調藥): the garden supplies every plant, the fire is kept low, and the three remedies are named with what each is for, with 暗影谷解毒草露 for poison, 強效治療藥水 for deep wounds and 魔力藥水 for spent mana. Source: the three item rows; 種族設定 › 精靈族 (immunity to disease, not to injury).
3. `ciaran_nireth_home.topic_02` (`keyword`: 重傷, `label`: 重傷): unchanged; the red-corded healing potion and the warning against wasting it stay.
4. `ciaran_nireth_home.topic_03` (`keyword`: 魔力, `label`: 魔力): unchanged; the blue-corded mana potion and the morning cutting of mana grass stay.
5. `ciaran_nireth_home.topic_04` (`keyword`: 藥草, `label`: 藥草): outside herbs are refused, the garden's 解毒草 becomes 暗影谷解毒草露, and unopened sealed jars come back. Source: the host's card; the 藥草園 node; the `elven_remedies` service.

---

## 5. Room Prose Review

`content/maps/interiors/ciaran_valwyn_home.yaml` (瓦爾溫的家) lists her gathered things as feathers, seeds, pressed cakes of blue dye and jars of crystal sand. The sentence's other clauses, the name, the scene archetype, the art key and the entrance are unchanged, so the room's one changed line is the description. The description names no shop, no counter and no signboard.

---

## 6. Documentation Corrections and Working Notes

`docs/lore/items.md` gains the five rows and keeps one row per existing good. The four borrowed goods now name the village that makes them in their 產地／文化 cell, with 精靈蛛絲 and 精靈傳統服飾 pointing to 幽月谷村（伊歐拉斯族） and 精靈森林輕紗 and 精靈蜜漬花蕊 to 翠綠森林村（斐歐恩族）. The two running counts of usable potions and landed potion effects moved from four to five, and the tincture joined the design-reference list, because the registry now has five and the old text would contradict it.

`docs/lore/settlement-locations.md` grep hits, each read and dispositioned:

| Line | Text | Disposition |
| --- | --- | --- |
| 186 | elven village sundries include 蜜漬花蕊 as surplus | Left: the sentence describes elves in general, not 暗影谷村's shelf, and the candied blossom remains a 翠綠森林村 good the other branches may hold. |
| 214 | armour narrative lists 精靈傳統服飾 | Left: a general statement about where the armour category appears in the lore narrative. |
| 226 | 伊歐拉斯族的白色蛛絲服飾 and 基亞蘭族的墨黑短和服 | Left: already assigns the white silk to the Eolas branch and the black robe to the Ciaran branch, which matches the new shelves. |
| 521 | elven villages trade through individual homes | Left: a general statement about all three villages. |
| 523 | 幽月谷村 keeps 蛛絲林 and 奈拉拉 | Left: accurate for the making village. |
| 525 | 翠綠森林村 candies blossom and weaves the veil | Left: accurate for the making village. |

The 鍊金坊與藥舖 聚落差異 paragraph (line 262), which describes 妮瑞斯, now names 暗影谷解毒草露 and says she brews it from the garden's own 解毒草. No sentence in the document presented one of the four removed goods as 暗影谷村's make or stock, and the document does not describe the 暗影谷村 fare host, so no fare correction was available; the change records that rather than inventing one.

`docs/development/npc-editorial-review.md` carries the four refreshed `place_host` rows and the four refreshed `dialogue_table` rows, dated 2026-11-17 and rewritten from the finished sources.

---

## 7. Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
| --- | --- | --- |
| 暗影谷村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_ciaran`) |
| 溪畔小徑 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`stream_path`) |
| 溪畔下游 / 下游淺灘 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`stream_bend`) |
| 織房坡 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`weaving_slope`) |
| 藥草園 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`herb_garden`) |
| 村北古樹下 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`old_tree_north`) |
| 村中廣場 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`village_plaza`) |
| 銀葉坡 | Settlement node | `content/maps/settlements/elven_village_ciaran.yaml` (`silver_leaf_slope`) |
| 幽月谷村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_eolas`) |
| 蛛絲林 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`silk_grove`) |
| 翠綠森林村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_fionnen`) |
| 樹冠吊橋 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`canopy_walk`) |
| 拉瑞內斯‧妮特布倫 | NPC host | `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_lareneth`), `places_ciaran.py` |
| 瓦爾溫‧斯蒂爾瓦特爾 | NPC host | `world/lore/npc_profiles/ciaran_homes_b.py` (`ciaran_valwyn`), `places_ciaran.py` |
| 維特希爾‧威爾德布瑞亞爾 | NPC host | `world/lore/npc_profiles/ciaran_homes_b.py` (`ciaran_vethiel`), `places_ciaran.py` |
| 妮瑞斯‧米斯特瓦勒 | NPC host | `world/lore/npc_profiles/ciaran_homes_b.py` (`ciaran_nireth`), `places_ciaran.py` |
| 格威娜拉‧希爾維爾莉夫 | NPC host | `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_gwenaera`), `places_ciaran.py` |
| 奈拉拉‧弗羅斯特威洛 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_naelara`), `places_eolas.py` |
| 伊斯爾林‧斯塔爾威維爾 | NPC host | `world/lore/npc_profiles/fionnen_homes_a.py` (`fionnen_ithrlin`), `places_fionnen.py` |
| 基亞蘭族 | Race branch (人稱) | `tmp/story_settings/world_info.md` 種族設定 › 精靈族 › 三分支; `docs/lore/overview.md` |
| 王都 | Polity capital | `tmp/story_settings/world_info.md` 國家與政治 |
| 暗影谷夜綻花釀 | Item (`ciaran_nightbloom_preserve`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`elven_fare`) |
| 暗影谷炭烤蕈串 | Item (`ciaran_ember_mushroom_skewer`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`elven_fare`) |
| 暗影谷藍染 | Item (`ciaran_indigo_dye`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`elven_sundries`) |
| 暗影谷晶砂 | Item (`ciaran_crystal_sand`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`elven_sundries`) |
| 暗影谷解毒草露 | Item (`ciaran_antivenom_tincture`) | `world/lore/items/data_elven_village_goods.py`, `world/rules/rulebook/item_effects.yaml` |
| 精靈短袍傳統服飾 | Item (`dark_elf_kimono`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`elven_attire`) |
| 精靈戰鬥服飾 | Item (`dark_elf_ninja_garb`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`elven_attire`) |
| 強效治療藥水 | Item (`greater_healing_potion`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`elven_remedies`) |
| 魔力藥水 | Item (`mana_potion`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`elven_remedies`) |
| 月牙耳環 | Item (`crescent_earring`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`elven_adornments`) |
| 精靈蛛絲 | Item (`elven_spider_silk`) | `world/lore/items/data_armor_accessories_materials.py`, `world/lore/settlements/assortments.py` (`eolas_silkwork`) |
| 精靈傳統服飾 | Item (`elven_traditional_robe`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`eolas_silkwork`) |
| 精靈森林輕紗 | Item (`elven_forest_veil`) | `world/lore/items/data_regional_equipment.py`, `world/lore/settlements/assortments.py` (`fionnen_attire`) |

Short forms in the prose (白的蛛絲袍, 晨霧一樣的輕紗, 花釀, 蕈串, 染塊, 晶砂, 草露, 藥水) resolve to the rows above and name nothing else. The white robe and the dew veil appear only in the sentence that places them in the neighbour villages, and 精靈蛛絲 only in the sentence that gives it to 幽月谷村.

---

## 8. Style and Constraint Compliance Verification

- **In character only**: no command, backtick, syntax token, attribute number or interface element appears in the prose.
- **Traditional Chinese**: full-width punctuation throughout, no 您, no sentence-final 的 before a comma or a full stop, no half-width punctuation beside Chinese characters.
- **No wuxia vocabulary**: no 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫 or 掌門.
- **No proprietor vocabulary**: none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門 or 打烊 appears in a village table.
- **Scene shapes**: every rewritten scene opens with an actor speech line, holds six lines, carries at least one host line and declares `revision: r3`; untouched scenes and the familiar-visitor variant stay at `r2`.
- **Stable IDs**: every topic ID and scene ID is unchanged; only the 蛛絲 keyword and label became 藍染, as the design directs, and the topic ID stayed.
- **No mechanics**: no line promises a skill, a stat, a status or a command. The tincture's effect lives in the rulebook, not in the prose.
- **Consent is structural**: no actor line grants consent, initiates an act or promises one; every request is a question, and no scene stages a sexual act.

---

## 9. Lint and Load Results

- `world.lore.dialogue.DIALOGUE_SNAPSHOT` loads 38 tables with no `DialogueSourceError`; `NPC_PROFILE_REGISTRY` holds 41 profiles; `ITEM_REGISTRY` ends with the five new keys in table order.
- `npc_content_lint.py --places` over the four tables reports 0 errors and 1 warning; `--profiles` over the two profile slices reports 0 errors and 1 warning. Both exit 0.
- The Traditional Chinese linter reports 0 errors over the four dialogue files, the two profile modules and the interior document.
- `check_map_sources.py` ends `RESULT: game-ready as far as static checks can tell`; `tools.map_reference_context --check` reports the reference context up to date after the regeneration.
- `tools.contract_gate` ends `contract gate passed`; `tools.test_data_lint check` and `tools.spec_traceability check` both exit 0; `openspec validate ciaran-village-local-goods --strict` reports the change valid.
- The focused test labels under `world.lore` and `world.rules` end `OK`, run one label set at a time.

### Warning Dispositions

- `npc_content_lint.py` `ciaran_valwyn.yaml` `[reduplication] 拉拉` stands. 拉拉 is part of the authored given name 奈拉拉 inside 奈拉拉‧弗羅斯特威洛, not a reduplicated adverb.
- `npc_content_lint.py --profiles` `ciaran_homes_b.py` `ciaran_teliel/habit` `[reduplication] 天天` stands. 天天 is the ordinary everyday word 每天 in a card this change does not rewrite.
- The Traditional Chinese linter's `[english-term]` warnings name YAML keys, Python identifiers, scene IDs and the hosts' romanised slugs. They are structural tokens, not player prose.
- The Traditional Chinese linter's `[reduplication]` warning over the profile slice again flags 天天 in `ciaran_teliel`, and the one over the interior flags 樣樣, which was already in the room's description; neither is new prose in this change.

---

## 10. Test Adjustment Notes

No test module, assertion, fixture or data pin was added or edited. No test failure occurred in the runs recorded under section 9, so no assertion was rewritten. The prose quality here is carried by this document rather than by an assertion.
