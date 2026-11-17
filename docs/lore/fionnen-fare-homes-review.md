# Fionnen Fare Homes Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `fionnen-village-fare-homes` change (`fionnen_elunwen`, `fionnen_firwen`, `fionnen_lumeth`, `fionnen_sylara`), the four fare homes it adds to 翠綠森林村, and the prose that ships with them: the compact cards, the `misunderstood` voice lines, the room descriptions of the four interiors, the greetings and the sixteen scenes of the four dialogue tables.

### Profile, Place and Dialogue Bindings

- `fionnen_elunwen_home` (place: 埃倫溫的家, host: 埃倫溫‧斯威夫塔羅) -> `world/lore/dialogue/content/fionnen_elunwen.yaml`
- `fionnen_firwen_home` (place: 菲爾溫的家, host: 菲爾溫‧埃文斯塔爾) -> `world/lore/dialogue/content/fionnen_firwen.yaml`
- `fionnen_lumeth_home` (place: 盧梅斯的家, host: 盧梅斯‧布瑞特莉夫) -> `world/lore/dialogue/content/fionnen_lumeth.yaml`
- `fionnen_sylara_home` (place: 希拉拉的家, host: 希拉拉‧希倫特布魯克) -> `world/lore/dialogue/content/fionnen_sylara.yaml`

Each file is named after the host's profile key and declares its topics under the place's `dialogue_key`; the file declares no owner field.

### Canonical Sources

- `tmp/story_settings/world_info.md` (sections: 種族設定 › 精靈族 and 斐歐恩族; 生活方式 › 性文化; 社會與文化 › 教育、婚姻、倫理觀; 特殊設定 › 精靈與外界互動).
- `docs/lore/overview.md` (精靈族, 性別與生殖, 性愛與身體).
- `docs/lore/settlement-locations.md` (翠綠森林村 in 聚落差異深論; 精靈村落 in the location-type table; 公共浴場 in 聚落差異).
- `world/lore/npc_profiles/fionnen_homes_b.py` (the four profiles and their cards).
- `world/lore/settlements/places_fionnen.py` (`fionnen_elunwen_home`, `fionnen_firwen_home`, `fionnen_lumeth_home`, `fionnen_sylara_home`).
- `world/lore/settlements/assortments.py` (`fionnen_fare`, `fionnen_remedies`).
- `world/rules/rulebook/commerce/fionnen.yaml` (offers and shop hours).
- `content/maps/settlements/elven_village_fionnen.yaml` (the nodes the host prose names).
- `content/maps/interiors/fionnen_elunwen_home.yaml`, `fionnen_firwen_home.yaml`, `fionnen_lumeth_home.yaml`, `fionnen_sylara_home.yaml`, `fionnen_honey_house.yaml`.
- `skill://npc-dialogue-content` with `references/scene-schema.md`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

The world source states that the Fionnen are the 森林精靈 of 翠綠森林村, that all elves are women, that elven society has no fixed trades, no marriage and no formal schooling, and that knowledge comes from a long life. No player-facing line states an age, an apparent age or a count of years: the hosts' long lives show only in what they remember, how they speak and what their hands know.

---

## 2. Mandatory Lore Checks

### Standing, Rarity and the Absence of Commerce

- Canon: about 300 elves exist across three branches, and the three human and beastfolk nations rank them above royalty. Elves need nothing from outsiders and are neither servants nor curiosities.
- Society: no fixed profession division, no caste, no apprenticeship. The village has no shop as an institution, no posted hours and no proprietor. A villager makes what she loves in her own home and shares it with neighbours or the rare visitor who finds the village.
- How the change reads it: no card, greeting or scene uses proprietor vocabulary. There is no counter, no sign and no stock count. The door is a door, the shelf holds what she finished this season, and the copper is the village's way of looking after a guest.
- Host handling:
  - `fionnen_elunwen`: keeps the targets and the swinging tags of 靶道 and shoots beside whoever comes, teaching nobody by hand. She converses and trades nothing.
  - `fionnen_firwen`: the elder, on the highest platform of 樹冠吊橋. The village rarely needs an elder's word, so she watches the forest and talks with whoever climbs up. She converses and trades nothing.
  - `fionnen_lumeth`: keeps the hives of 花蕊蜜園, candies blossom in honey and feeds the village from 蜜漬房. A visitor takes a jar away for coin.
  - `fionnen_sylara`: tends the herb beds of 林間菜圃, cuts 止血藥草, cooks 森林蜂蠟膏 and keeps 治療藥水 for hunters and for guests.

### Body and Sex

- Canon: elves have no concept of shame about nudity, the body or sex (`對裸露、性器官、性行為完全沒有羞恥概念`), treat sex as a natural need like breathing (`視性愛為如同呼吸般自然的生理需求`), and give it the greater part of their time. Elven sex between women is ordinary joy, and what they do with their bodies grows more intense over a long life. Other races look away out of awe rather than moral judgment.
- How the change reads it: the ease sits in dress, bearing and how each host speaks of her own goods. 菲爾溫 wears one open mantle over nothing and says the village has nothing to hide, that washing, laundry and talk share the 林泉浴場, and that who lies with whom at night is no more hidden than who eats at whose house. 盧梅斯 feeds a guest honey from her own finger before saying anything else, 希拉拉 reads a body for blood before she asks a question, and 埃倫溫's card keeps the bracer-and-quiver dress of a woman who works in the open.
- The scenes stay in the hosts' homes: the body ease is talked about, never staged. No fare home becomes a sexual scene, and the 蜜漬房 scene explains that nobody pays there, which is what the lore says about the shared room.
- The one limit is structural, not tonal: an actor line never grants consent, initiates or promises an act. The frankness rides in what a host says and does, never in a scene the player is written into.

### Religion

- Canon: elves never proselytise, and outsiders do not know their faith or the truth of the three goddesses. No non-elf NPC explains 神之秘法.
- Host handling: none of the four hosts teaches theology, names a goddess or explains a divine chain. 希拉拉's 光魔法 scene treats light magic as a villager's everyday craft and heals nobody in the scene.

---

## 3. Retained Service Behaviours and Assortment Consistency

All four homes keep their authored place binding without alteration.

- `fionnen_elunwen_home` declares only `scripted_dialogue`: no assortment, no shop row, nothing sold or bought.
- `fionnen_firwen_home` declares only `scripted_dialogue`: no assortment, no shop row, nothing sold or bought.
- `fionnen_lumeth_home` stocks `fionnen_fare` (森林百花蜜, 精靈蜜漬花蕊, 普通餐食). She keeps the hives, candies the blossom and packs the fare herself; buy-back names those three goods and declines goods outside her assortment.
- `fionnen_sylara_home` stocks `fionnen_remedies` (森林蜂蠟膏, 止血藥草, 治療藥水). She grows and cuts the herb, cooks the salve and bottles the potion; buy-back names those three goods and declines other herbs.

Every offer in `world/rules/rulebook/commerce/fionnen.yaml` sits inside its item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and each good the capital also sells is cheaper here (`elven_candied_blossom` 20 against 60, `meal` 6 against 10, `healing_herb` 20 against 40, `healing_potion` 60 against 100). Shop hours match 暗影谷村: open 7, close 19, restock 6. No line of dialogue delivers a free remedy, a custom commission, a discount or a price figure. The scenes name goods by their registry display name and state no quantity.

---

## 4. Per-Host Review

Every scene opens with a complete actor utterance, holds six lines and carries at least one host line. Three scenes were revised after the first delivery and declare `revision: r2`, namely `fionnen_lumeth_home.topic_01`, `fionnen_sylara_home.topic_01` and `fionnen_sylara_home.topic_03`; the other thirteen stay at `r1`. Every topic is open except 菲爾溫's 往事, which is a `pure_chain` successor of 森林 and declares no `requires`. No topic declares a variant, a refusal or an unavailable status.

### A. `fionnen_elunwen_home` (埃倫溫‧斯威夫塔羅)

**Card and voice review.** The public leaf reads her as the village's 箭術導師 whose home stands at the head of 靶道, who checks the target skins, ties the swinging tags back up and shoots beside whoever comes without teaching by hand; the appearance leaf keeps the brief (lean, blonde hair cut at the jaw, one old bracer on the left arm, a quiver worn low and little else), and the personality and speech leaves keep the quiet, sparing register that speaks between shots. The life story keeps the lane, the deep-forest hunt and the village's children who learn by standing beside her, and the social connection keeps the bows of 格威內爾‧斯威夫塔羅 and the shared dwelling name. `identity.hidden` is empty as the brief requires, `voice.greeting` stays empty because the table's greeting opens, and `voice.misunderstood` asks whether the visitor came to shoot. Canon: 種族設定 › 精靈族 (no fixed trades, 擅長弓術); 生活方式 › 性文化.

1. **Opening greeting**: Elunwen lowers her bow after the shot lands, looks over the guest's stance and nods at the spare bows by the door. Source: 種族設定 › 斐歐恩族 特色 (擅長弓術); the 靶道 node.
2. `fionnen_elunwen_home.topic_01` (`keyword`: 箭術, `label`: 箭術): stance comes before breath and breath before the hand, the full draw is released on a half-exhale, and the practice ends when the hand stops needing the thought. Source: 種族設定 › 精靈族 (ability comes from long practice); the 靶道 node.
3. `fionnen_elunwen_home.topic_02` (`keyword`: 靶道, `label`: 靶道): targets are nailed to trunks for beginners, the far tags swing on ropes and must be timed, the lane never shuts, and she resets the tags every morning. Source: `content/maps/settlements/elven_village_fionnen.yaml` (`archery_lane`).
4. `fionnen_elunwen_home.topic_03` (`keyword`: 光魔法, `label`: 光魔法): archery and light magic share one lane, accuracy is the same discipline in both, and the village's children first learn to hold light in the palm there. Source: 種族設定 › 斐歐恩族 特色 (親和光屬性魔法); the 靶道 node.
5. `fionnen_elunwen_home.topic_04` (`keyword`: 比試, `label`: 比試): she declines a contest, measures the day against the last practice instead, and points at the target that neither yields nor loses and at the spare bows by the door. Source: the host's dialogue-only declaration; 種族設定 › 精靈族 (no fixed trades, nothing to sell).

### B. `fionnen_firwen_home` (菲爾溫‧埃文斯塔爾)

**Card and voice review.** The public leaf reads her as the village's 長老 on the highest platform of 樹冠吊橋, with little to decide, who watches the forest and talks with whoever climbs up; the appearance leaf keeps the brief (silver-gold hair to the knees pinned with a wooden pin, a single open mantle over nothing, the longbow on the wall behind her), the personality and speech leaves keep the unhurried, warm register that begins with what she can see and calls everyone 孩子, and the life story keeps the trees she has lived in longer than anyone remembers and the village she has loved in her time. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` says she did not hear and that the day is long. Canon: 種族設定 › 精靈族 (長老會議 but rarely important business; lifespan-borne memory); 生活方式 › 性文化; 社會與文化 › 倫理觀.

1. **Opening greeting**: Firwen turns from the view without rising and offers the guest the board where the light will fall. Source: 社會與文化 › 倫理觀 (no shame about the body); 種族設定 › 精靈族 (a long memory).
2. `fionnen_firwen_home.topic_01` (`keyword`: 森林, `label`: 森林): the village has a ground level and a canopy level joined by bridges and rope ladders; the brook feeds the plots, the hives stand at the garden, and the open 林泉浴場 is where washing, laundry and talk share one edge with nobody hiding. Source: `docs/lore/settlement-locations.md` 翠綠森林村 and 公共浴場 聚落差異; the `bathing_pool` node; 生活方式 › 性文化.
3. `fionnen_firwen_home.topic_02` (`keyword`: 光庭, `label`: 光庭): 林間光庭 is the gap in the canopy where work is handed out and news is traded, the children chase the light, and few things there are important enough to be decided. Source: the `light_court` node; 種族設定 › 精靈族 (rarely important business).
4. `fionnen_firwen_home.topic_03` (`keyword`: 外人, `label`: 外人): visitors are neither watched nor courted; 葉隱小徑 stays hidden because nobody thinks to point it out, not because anyone hides it. Source: 特殊設定 › 精靈與外界互動 (精靈極少離開村落); 種族設定 › 對外態度 (不在意); the `leaf_veiled_path` node.
5. `fionnen_firwen_home.topic_04` (`keyword`: 往事, `label`: 往事, `disclosure`: pure_chain, predecessors: 森林): a small memory of the canopy before it opened, when the oldest tree lost a limb and the light came through the gap. Source: 種族設定 › 精靈族 (千年積累的知識與經驗).

### C. `fionnen_lumeth_home` (盧梅斯‧布瑞特莉夫)

**Card and voice review.** The public leaf reads her as the villager who keeps the hives at 花蕊蜜園, candies blossom in honey and packs a jar for a visitor for coin; the appearance leaf keeps the brief (sun-gold curls pinned back, honey to the wrist, a bee or two riding her shoulder), the personality and speech leaves keep the cheerful, everyday register with 喔 and 呀 that puts a taste on a guest's lips before a word, and the life story keeps the hives taken from an elder who went back to her bow and the fact that she started later than the village's other makers. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` offers a taste and asks again. Canon: 種族設定 › 精靈族 (no fixed trades); 生活方式 › 性文化.

1. **Opening greeting**: Lumeth lifts the pot off the fire, dips a finger in the honey and holds it out before asking whether the guest came for honey or for something else. Source: 生活方式 › 性文化 (the body and its senses spoken of without evasion); 種族設定 › 精靈族 (a maker's own home).
2. `fionnen_lumeth_home.topic_01` (`keyword`: 養蜂, `label`: 養蜂): the hives stand at the edge of the flower beds and follow the bloom; 森林百花蜜 is gathered by the season and tastes of the flowers that opened. Source: the `blossom_garden` node; the item registry row (`fionnen_wildflower_honey`); the `fionnen_fare` shelf.
3. `fionnen_lumeth_home.topic_02` (`keyword`: 蜜漬, `label`: 蜜漬): 精靈蜜漬花蕊 is petals washed, dried, cooked once with honey and taken off the fire before they soften, then sealed and cooled. Source: the `blossom_garden` node description (蜜與花瓣一起熬煮); the item registry row (`elven_candied_blossom`).
4. `fionnen_lumeth_home.topic_03` (`keyword`: 蜜漬房, `label`: 蜜漬房): the shared 蜜漬房 holds the pots and the shelves of sweet food, nobody pays copper there, and a guest who wants a jar comes to her home. Source: `content/maps/interiors/fionnen_honey_house.yaml`; `docs/lore/settlement-locations.md` 精靈村落 (無掛牌商店，機能由個別精靈在家中承擔).
5. `fionnen_lumeth_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back the three goods on her own shelf, pays copper for what is sound, and declines food outside her assortment because she cannot judge it. Source: the home's `fionnen_fare` service.

### D. `fionnen_sylara_home` (希拉拉‧希倫特布魯克)

**Card and voice review.** The public leaf reads her as the village's 藥草者 who keeps the herb beds of 林間菜圃, cuts 止血藥草, cooks 森林蜂蠟膏 and keeps 治療藥水 for hunters and guests; the appearance leaf keeps the brief (ash-blonde hair pinned with a twig, green eyes, a salve tin on a cord), the personality and speech leaves keep the composed, practical register that treats a wound before asking about it, and the life story keeps the long work of patching hunters, the fact that elves mend by themselves, and the guests and animals she learned on. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` asks whether it is a wound or the herbs. Canon: 種族設定 › 精靈族 (immune to illness); 生活方式 › 性文化.

1. **Opening greeting**: Sylara comes in from the herb beds, looks the guest over for blood, wipes her hands and names what is ready. Source: 種族設定 › 精靈族 (免疫所有疾病, so her craft is for wounds and for guests); the `forest_plots` node.
2. `fionnen_sylara_home.topic_01` (`keyword`: 藥草, `label`: 藥草): 止血藥草 grows in the shaded inner beds, is hung to dry out of the sun, and is rubbed onto a cut to close it. Source: the `forest_plots` node; the item registry row (`healing_herb`); the `fionnen_remedies` shelf.
3. `fionnen_sylara_home.topic_02` (`keyword`: 蜂蠟膏, `label`: 蜂蠟膏): 森林蜂蠟膏 is hive wax from 盧梅斯 cooked slowly with herbs until it darkens, and it seals a cut against water and soil. Source: the item registry row (`fionnen_beeswax_salve`); the hives at 花蕊蜜園.
4. `fionnen_sylara_home.topic_03` (`keyword`: 光魔法, `label`: 光魔法): the Fionnen affinity for light is an everyday fact, light closes a wound and takes down swelling, and bone and dirt still need hands. Source: 種族設定 › 斐歐恩族 特色 (親和光屬性魔法); 生活方式 › 性文化 (the body spoken of plainly).
5. `fionnen_sylara_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back the three goods on her own shelf and declines herbs she does not keep. Source: the home's `fionnen_remedies` service.

---

## 5. Room Prose Review

- `fionnen_elunwen_home` (埃倫溫的家): a room built into the trunks at the head of 靶道, open on the lane side, arrows sorted by fletching, strung bows on wall pegs, a moss bed, a water jar and a whetstone.
- `fionnen_firwen_home` (菲爾溫的家): the highest platform room on 樹冠吊橋, open to the leaves on three sides, a faded mantle on a peg, an old longbow on the wall and little else.
- `fionnen_lumeth_home` (盧梅斯的家): a room among the flower beds of 花蕊蜜園, sealed honey jars on the shelves, petals drying on cloth, the pot still warm on the stove.
- `fionnen_sylara_home` (希拉拉的家): a room beside the beds of 林間菜圃, 止血藥草 drying under the beams, a pot of beeswax on a low fire, salve tins and bottles in a row.

None of the four names contains 店 or 舖, none of the descriptions contains 櫃檯 or 招牌, and none carries an ASCII word or a change identifier. Each reads as a lived-in room: no signboard, no counter, no shopkeeper wording.

---

## 6. Style and Constraint Compliance Verification

- **In character only**: no command, backtick, syntax token, attribute number or interface element appears in the prose.
- **Traditional Chinese**: full-width punctuation throughout, no 您, no sentence-final 的 before a comma or a full stop, no half-width punctuation beside Chinese characters.
- **No wuxia vocabulary**: no 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫 or 掌門.
- **No proprietor vocabulary**: none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門 or 打烊 appears in a village table.
- **Scene shapes**: all sixteen scenes open with an actor speech line, hold six lines and carry at least one host line; the three revised scenes declare `revision: r2` and the other thirteen `r1`.
- **No age**: no 歲 figure, no apparent age and no count of years appears in any card, room description, greeting or scene. The longbow's age is written as older than the kingdom, and the elder's memory as what she recalls.
- **No mechanics**: no line promises a skill, a stat, a status or a command. The scenes describe the world-side act only.
- **Consent is structural**: no actor line grants consent, initiates an act or promises one; every frank line belongs to the host, and no fare home stages a sexual scene.

### Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
|---|---|---|
| 翠綠森林村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_fionnen`) |
| 靶道 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`archery_lane`), `places_fionnen.py` (`fionnen_elunwen_home`) |
| 樹冠吊橋 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`canopy_walk`), `places_fionnen.py` (`fionnen_firwen_home`) |
| 花蕊蜜園 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`blossom_garden`), `places_fionnen.py` (`fionnen_lumeth_home`) |
| 林間菜圃 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`forest_plots`), `places_fionnen.py` (`fionnen_sylara_home`) |
| 林泉浴場 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`bathing_pool`), `docs/lore/settlement-locations.md` 公共浴場 聚落差異 |
| 林間光庭 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`light_court`) |
| 葉隱小徑 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`leaf_veiled_path`) |
| 林溪 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`forest_brook`) |
| 蜜漬房 | Interior | `content/maps/interiors/fionnen_honey_house.yaml` |
| 埃倫溫‧斯威夫塔羅 | NPC host | `world/lore/npc_profiles/fionnen_homes_b.py` (`fionnen_elunwen`), `places_fionnen.py` |
| 菲爾溫‧埃文斯塔爾 | NPC host | `world/lore/npc_profiles/fionnen_homes_b.py` (`fionnen_firwen`), `places_fionnen.py` |
| 盧梅斯‧布瑞特莉夫 | NPC host | `world/lore/npc_profiles/fionnen_homes_b.py` (`fionnen_lumeth`), `places_fionnen.py` |
| 希拉拉‧希倫特布魯克 | NPC host | `world/lore/npc_profiles/fionnen_homes_b.py` (`fionnen_sylara`), `places_fionnen.py` |
| 格威內爾‧斯威夫塔羅 | NPC host | `world/lore/npc_profiles/fionnen_homes_a.py` (`fionnen_gwynnel`), `places_fionnen.py` |
| 斐歐恩族 | Race branch (人稱) | `tmp/story_settings/world_info.md` 種族設定 › 精靈族; `docs/lore/overview.md` 精靈族 |
| 王國 | Polity | `tmp/story_settings/world_info.md` 國家與政治 (人類王國‧阿爾托利亞) |
| 森林百花蜜 | Item (`fionnen_wildflower_honey`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`fionnen_fare`) |
| 精靈蜜漬花蕊 | Item (`elven_candied_blossom`) | `world/lore/items/data_inspect_only_codex.py`, `world/lore/settlements/assortments.py` (`fionnen_fare`) |
| 普通餐食 | Item (`meal`) | `world/lore/items/data_core_items.py`, `world/lore/settlements/assortments.py` (`fionnen_fare`) |
| 森林蜂蠟膏 | Item (`fionnen_beeswax_salve`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`fionnen_remedies`) |
| 止血藥草 | Item (`healing_herb`) | `world/lore/items/data_armor_accessories_materials.py`, `world/lore/settlements/assortments.py` (`fionnen_remedies`) |
| 治療藥水 | Item (`healing_potion`) | `world/lore/items/data_core_items.py`, `world/lore/settlements/assortments.py` (`fionnen_remedies`) |

Short forms in the prose (蜂蠟膏, 藥膏, 蜜) resolve to the rows above and name nothing else.

---

## 7. Offline Verification and Lint Results

- Baseline before the edit: `check_map_sources.py` ended `RESULT: game-ready as far as static checks can tell`; the dependency items `eolas_proving_wand` and `fionnen_leafweave_garb` both resolved; the free-ID search over `content world docs/development` found no `fionnen_elunwen`.
- `world.lore.dialogue.DIALOGUE_SNAPSHOT` loads 38 tables with no `DialogueSourceError`.
- `world.lore.settlements.places.PLACE_REGISTRY` resolves the four homes' `host_profile_key` to `fionnen_elunwen`, `fionnen_firwen`, `fionnen_lumeth` and `fionnen_sylara`.
- `npc_content_lint.py --places` over the four tables exits 0 with zero errors and one warning, dispositioned in section 8. `--profiles` over the profile slice exits 0 with zero errors and one warning, of the same kind.
- The Traditional Chinese linter reports zero errors over the four dialogue files, the profile module and the four interior documents. Its warnings are the English-term prompts for YAML keys, Python identifiers and the hosts' romanised slugs, plus the name 希拉拉.
- `check_map_sources.py` reports no structure error, `game-adoption cross-file problems: 0`, and ends `RESULT: game-ready as far as static checks can tell`.
- `tools.map_reference_context --check` reports the reference context up to date after the regeneration that followed the last interior edit.
- `tools.contract_gate` ends `contract gate passed`; `tools.test_data_lint check` and `tools.spec_traceability check` both exit 0.
- The focused test labels end `OK`. `world.rules.tests.test_guild_config` discovers 119 tests over the guard's 100, so its modules run as separate labels; `test_item_offer_definitions` keeps the ordering dependency recorded in `docs/lore/fionnen-craft-homes-review.md` and passes beside `test_assortment_shop_rules`.
- Browser playback was not performed for this change; the text emission and the browser player read the same authored scenes. The in-game walkthrough recorded under the change's Workflow follow-up is a human step.

---

## 8. Lint Warning Dispositions

- `npc_content_lint.py` `fionnen_sylara.yaml` greeting `[reduplication] 「拉拉」` stands. 拉拉 is the authored given name 希拉拉 inside 希拉拉‧希倫特布魯克, not a reduplicated adverb. The same warning over the profile slice's 盧梅斯 social connection names the same host.
- The Traditional Chinese linter's `[english-term]` warnings over the four dialogue files name YAML keys, scene identifiers and the hosts' romanised slugs. They are structural tokens, not player prose.
- The same warnings over `fionnen_homes_b.py` name Python identifiers, docstring module paths and the romanised slugs.
- The same warnings over the four interior documents name the header comment, the YAML keys and the doorway aliases.
- The Traditional Chinese linter's `[reduplication]` warning over the sylara dialogue file and the sylara interior document flags 希拉拉, as above.
- No other warning category appears.

---

## 9. Test Adjustment Notes

No test module, assertion, fixture or data pin was added or edited. The shard modules this change extends were already enumerated by `unpin-village-test-data`, and the focused test runs are recorded in the change's own verification.
