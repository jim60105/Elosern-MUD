# Eolas Fare Homes Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `eolas-village-fare-homes` change (`eolas_nirnel`, `eolas_raellin`, `eolas_saelnel`), the three fare homes it adds to 幽月谷村, and the prose that ships with them. The prose under review is the compact cards, the `misunderstood` voice lines, the room descriptions of the three interiors, the greetings and the twelve scenes of the three dialogue tables.

### Profile, Place and Dialogue Bindings

- `eolas_nirnel_home` (place: 妮爾內爾的家, host: 妮爾內爾‧德米多) -> `world/lore/dialogue/content/eolas_nirnel.yaml`
- `eolas_raellin_home` (place: 雷林的家, host: 雷林‧莉特弗特) -> `world/lore/dialogue/content/eolas_raellin.yaml`
- `eolas_saelnel_home` (place: 賽爾內爾的家, host: 賽爾內爾‧妮格汀加勒) -> `world/lore/dialogue/content/eolas_saelnel.yaml`

Each file is named after the host's profile key and declares its topics under the place's `dialogue_key`; the file declares no owner field.

### Canonical Sources

- `tmp/story_settings/world_info.md` (sections: 種族設定 › 精靈族; 生活方式 › 性文化; 社會與文化 › 倫理觀; 特殊設定 › 精靈體質).
- `docs/lore/overview.md` (精靈族, 性別與生殖, 性愛與身體).
- `docs/lore/settlement-locations.md` (幽月谷村 in 聚落差異深論; 公共浴場 聚落差異).
- `world/lore/npc_profiles/eolas_homes_b.py` (the three profiles and their cards).
- `world/lore/settlements/places_eolas.py` (`eolas_nirnel_home`, `eolas_raellin_home`, `eolas_saelnel_home`).
- `world/lore/settlements/assortments.py` (`eolas_remedies`, `eolas_fare`).
- `content/maps/interiors/eolas_nirnel_home.yaml`, `eolas_raellin_home.yaml`, `eolas_saelnel_home.yaml`.
- `skill://npc-dialogue-content` with `references/scene-schema.md`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

The world source states that the Eolas are the 幻童精靈 of 幽月谷村, that all elves are women, that elven society has no fixed trades, no marriage and no formal schooling, and that knowledge comes from a long life. `docs/lore/overview.md` records the Eolas appearance as fixed at twenty years. No player-facing line states an age, an apparent age or a count of years. The hosts' long lives show only in what they remember, how they speak and what their hands know.

---

## 2. Mandatory Lore Checks

### Standing, Rarity and the Absence of Commerce

- Canon: about 300 elves exist across three branches, and the three human and beastfolk nations rank them above royalty. Elves need nothing from outsiders and are neither servants nor curiosities.
- Society: no fixed profession division, no caste, no apprenticeship. The village has no shop as an institution, no posted hours and no proprietor. A villager makes what she loves in her own home and shares it with neighbours or the rare visitor who finds the valley.
- How the change reads it: no card, greeting or scene uses proprietor vocabulary. There is no counter, no sign and no stock count. The door is a door, the shelf holds what she finished this season, and the copper is the village's way of looking after a guest.
- Host handling:
  - `eolas_nirnel`: keeps the herb rows of 石階菜畦, picks by the hour and steeps her remedies. She reads a visitor's tiredness before answering and speaks of what a spent body wants without embarrassment.
  - `eolas_raellin`: bakes bean flatbread in the shared 窯場 and packs food for the trail. She feeds a guest before asking the reason for the visit and is particular about herbs.
  - `eolas_saelnel`: the elder of the village, in the oldest dwelling on 岩屋坡. The village rarely has anything for her to decide, so she reads, remembers and talks with whoever comes. She trades nothing.

### Body and Sex

- Canon: elves have no concept of shame about nudity, the body or sex (`對裸露、性器官、性行為完全沒有羞恥概念`), treat sex as a natural need like breathing (`視性愛為如同呼吸般自然的生理需求`), and give it about 80% of their time. Elven sex between women is ordinary joy, and what they do with their bodies grows more intense over a long life. Other races look away out of awe rather than moral judgment.
- `docs/lore/settlement-locations.md` puts all three villages at open pools with no partitions and no attendant; that contrast is the hook the village's stories use.
- How the change reads it: the ease is stated outright in the hosts' own words, at the frankness of `world/lore/dialogue/content/ciaran_vethiel.yaml` topic_03 and past it where the host's subject invites it. Nirnel speaks of what a spent body wants and keeps her collar open over a warm stove. Raellin feeds a guest first and says plainly what she expects after. Saelnel speaks of how the village spends its nights and turns a stranger's discomfort back to the guest's own freedom. Explicit wording sits in the hosts' speech, in narration and in the cards.
- The one limit is structural, not tonal: an actor line never grants consent, initiates or promises an act. The frankness rides in what a host says and does, never in a scene the player is written into.

### Religion

- Canon: elves never proselytise, and outsiders do not know their faith or the truth of the three goddesses. No non-elf NPC explains 神之秘法.
- Host handling: none of the three hosts teaches theology, names a goddess or explains a divine chain. The library scenes describe written experiment notes, not scripture.

---

## 3. Retained Service Behaviours and Assortment Consistency

All three homes keep their authored place binding without alteration.

- `eolas_nirnel_home` stocks `eolas_remedies` (幽月香草藥露, 魔力藥水, 強效治療藥水). She grows the herbs, steeps the tonic and bottles the remedies; buy-back accepts only her own sealed jars, and she declines herbs picked elsewhere because she cannot trust the hour or the slope they came from.
- `eolas_raellin_home` stocks `eolas_fare` (幽月窯烤豆餅, 普通餐食). She bakes in the shared kiln and packs food for the trail; buy-back accepts only unopened food she packed, and she declines provisions brought from outside because she cannot tell what is in them.
- `eolas_saelnel_home` stocks nothing and buys nothing. Her place row declares only `scripted_dialogue`.

No line of dialogue delivers a free remedy, a custom commission, a discount or a price figure. The scenes name goods by their registry display name and state no quantity.

---

## 4. Per-Host Review

Every scene declares `revision: r1`, opens with a complete actor utterance, holds five to eight lines and carries at least one host line. Every topic is open; the elder's 往事 is a `pure_chain` successor of 山谷 and declares no `requires`. No topic declares a variant, a refusal or an `unavailable` status.

### A. `eolas_nirnel_home` (妮爾內爾‧德米多)

**Card and voice review.** The public leaf reads her as the villager who tends the 石階菜畦 herb rows, picks by the hour and steeps sealed remedies, and it states the elves' ease about the body and about sex in her own words; the appearance leaf carries the brief (moss-green hair under a straw hat, soil under her nails, a row of stoppered jars at her belt) and the speech leaf keeps the even, complete-sentence register that ends advice with 喔. `identity.hidden` is empty as the brief requires, `voice.greeting` stays empty because the table's greeting opens, and `voice.misunderstood` asks whether it is tiredness or a wound, which the greeting's question answers. Canon: 種族設定 › 精靈族 (no fixed trades, a maker's own home); 生活方式 › 性文化. The card and the dialogue agree on the herbs, the steeping and the frank speech.

1. **Opening greeting**: Nirnel sets down a basket of cut herbs, looks the guest over for tiredness and names what is bottled today. Her collar is loose over the warm stove and she does not gather it. Source: 生活方式 › 性文化 (no shame about the body); 種族設定 › 精靈族 (no shop, a maker's own home).
2. `eolas_nirnel_home.topic_01` (`keyword`: 香草, `label`: 香草): the herb rows of 石階菜畦, the hour that decides when a leaf is picked, the stones she carried out of the beds, and the drying bunches above the stove. Source: `docs/lore/settlement-locations.md` 幽月谷村 (族人種塊根、豆子與香草) and the `terrace_gardens` node.
3. `eolas_nirnel_home.topic_02` (`keyword`: 藥露, `label`: 藥露): 幽月香草藥露 is valley herbs and 溪源 water steeped slowly; it restores stamina for the trail, and she warns against treating medicine as water. Source: the `eolas_herb_tonic` registry row (potion band) and the `eolas_remedies` shelf.
4. `eolas_nirnel_home.topic_03` (`keyword`: 魔力, `label`: 魔力): 魔力藥水 restores spent magic and 強效治療藥水 is for deep wounds; elves take no illness, but burns from 試法坪 and broken bones are real, and spent mana is felt in the body. Her last line turns to what a spent body wants in the night, and says the body must hold up first. Source: 種族設定 › 精靈族 (免疫所有疾病); 特殊體質; 生活方式 › 性文化; the two item registry rows.
5. `eolas_nirnel_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back her own sealed jars and empty bottles for copper and declines herbs picked elsewhere. Source: the home's `eolas_remedies` service.

### B. `eolas_raellin_home` (雷林‧莉特弗特)

**Card and voice review.** The public leaf reads her as the villager who loves cooking on 岩屋坡, bakes bean flatbread in the shared 窯場 and packs food for anyone heading up the trail, and it says plainly that she feeds people first and has no shyness about the body or the night; the appearance leaf keeps the brief (honey-brown hair in two short braids, flour to the elbows, a wooden paddle in her belt) and the speech leaf keeps the everyday, lively register with 喔 and 嘛. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` offers bread first and asks for the question again. Canon: 種族設定 › 精靈族; 生活方式 › 性文化. The card and the dialogue agree on the kiln, the bread and the herbs.

1. **Opening greeting**: Raellin comes back from the kiln with warm flatbread, tears the top one in half and offers half before asking where the guest is headed. She says food comes before strength, the night included, and her sleeves are at the shoulder with the kiln's red still on her face. Source: `docs/lore/settlement-locations.md` 幽月谷村 (共用窯燒陶與玻璃); 生活方式 › 性文化.
2. `eolas_raellin_home.topic_01` (`keyword`: 豆餅, `label`: 豆餅): 幽月窯烤豆餅 is terrace beans ground into a paste, kneaded with last season's wheat flour and stuck to the kiln wall while the heat is still in it; she judges the bake by the sound of the crust. Source: the `eolas_kiln_flatbread` registry row and the `eolas_fare` shelf; the `kiln_yard` node.
3. `eolas_raellin_home.topic_02` (`keyword`: 菜畦, `label`: 菜畦): beans, roots and herbs come from 石階菜畦; the terraces are built and watered by the village together, and neighbours trade bread for herbs rather than copper. Source: 幽月谷村 (石階菜畦) and the `terrace_gardens` node; 社會與文化 › 倫理觀.
4. `eolas_raellin_home.topic_03` (`keyword`: 共食, `label`: 共食): the village eats at 共食棚 and nobody pays; a visitor may sit and eat, copper is for what a guest carries away, and she says plainly that a guest who stays on after eating is not sent away and that the night waits until the meal is done. Source: the 共食棚 interior, the village's self-sufficient economy in `docs/lore/settlement-locations.md`, and 生活方式 › 性文化.
5. `eolas_raellin_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back unopened food she packed and declines provisions from outside. Source: the home's `eolas_fare` service.

### C. `eolas_saelnel_home` (賽爾內爾‧妮格汀加勒)

**Card and voice review.** The public leaf reads her as the elder of 幽月谷村 in the oldest dwelling on 岩屋坡, with little to decide, who reads, remembers and talks with whoever comes, and who says without evasion that the village spends most of its days on sex; the appearance leaf keeps the brief (white hair to the waist, calm grey eyes, a worn book within reach) and the speech leaf keeps the slow register with pauses, a remembered detail first and 孩子 for everyone. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` says she did not follow and that there is time to say it again. Canon: 種族設定 › 精靈族 (長老會議, but rarely important business; lifespan-borne knowledge); 生活方式 › 性文化.
1. **Opening greeting**: Saelnel closes a book on her finger to keep the page, pushes it aside and invites the guest to sit and ask about the valley or about old days. Source: 種族設定 › 精靈族 (a long memory, no formal schooling); 社會與文化.
2. `eolas_saelnel_home.topic_01` (`keyword`: 山谷, `label`: 山谷): the valley feeds and clothes itself through 石階菜畦, 蛛絲林, 窯場 and 溪源, and washing, laundry and talk share one edge at 溫泉浴場 with no partitions and no attendant. Source: 幽月谷村; `docs/lore/settlement-locations.md` 公共浴場 聚落差異.
3. `eolas_saelnel_home.topic_02` (`keyword`: 圖書館, `label`: 圖書館): the 圖書館 has no keeper; the shelves hold experiment notes the villagers wrote, and anyone may read or copy them. Source: 幽月谷村 (圖書館) and the `eolas_library` interior.
4. `eolas_saelnel_home.topic_03` (`keyword`: 外人, `label`: 外人): visitors are neither feared nor courted; the village's days continue as they are, the nights included, and a guest who keeps dressed at 溫泉浴場 is not remarked on. Source: 生活方式 › 性文化; 對外態度 (不在意); `docs/lore/settlement-locations.md` 公共浴場 聚落差異.
5. `eolas_saelnel_home.topic_04` (`keyword`: 往事, `label`: 往事, `disclosure`: pure_chain, predecessors: 山谷): a small memory of the kiln's first firing, the planting of 蛛絲林 and the trodden ground of 谷底空地, recalled without a year count. Source: 種族設定 › 精靈族 (千年積累的知識與經驗).

---

## 5. Room Prose Review

- `eolas_nirnel_home` (妮爾內爾的家): a rock-cut room above 石階菜畦, drying herbs overhead, jars sorted by the hour they were picked and a steeping pot kept warm. The prose is a lived-in room: no signboard, no counter, no shopkeeper wording.
- `eolas_raellin_home` (雷林的家): a rock-cut room on 岩屋坡 with a stone hearth, baskets of beans and roots, and flatbread cooling on a board by the window.
- `eolas_saelnel_home` (賽爾內爾的家): the oldest rock-cut room on 岩屋坡, shelves cut into the wall, a low table of open books and a window toward the valley floor.

None of the three names contains 店 or 舖, none of the descriptions contains 櫃檯 or 招牌, and none carries an ASCII word or a change identifier.

---

## 6. Style and Constraint Compliance Verification

- **In character only**: no command, backtick, syntax token, attribute number or interface element appears in the prose.
- **Traditional Chinese**: full-width punctuation throughout, no 您, no sentence-final 的 before a comma or a full stop, no half-width punctuation beside Chinese characters.
- **No wuxia vocabulary**: no 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫 or 掌門.
- **No proprietor vocabulary**: none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門 or 打烊 appears in a village table.
- **Scene shapes**: all twelve scenes open with an actor speech line, hold five to eight lines, carry at least one host line and declare `revision: r1`.
- **No age**: no 歲 figure, no apparent age and no count of years appears in any card, room description, greeting or scene. The ages live only in the profile records the game reads.
- **No mechanics**: no line promises a skill, a stat, a status or a command. The scenes describe the world-side act only.
- **Consent is structural**: no actor line grants consent, initiates an act or promises one; every explicit line belongs to the host.

### Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
|---|---|---|
| 幽月谷村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_eolas`) |
| 石階菜畦 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`terrace_gardens`) |
| 蛛絲林 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`silk_grove`) |
| 窯場 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`kiln_yard`) |
| 溪源 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`brook_head`) |
| 溫泉浴場 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`hot_spring`), `docs/lore/settlement-locations.md` 公共浴場 聚落差異 |
| 谷底空地 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`valley_floor`) |
| 深林獸徑 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`forest_trail`) |
| 共食棚 | Interior | `content/maps/interiors/eolas_shelter.yaml` |
| 圖書館 | Interior | `content/maps/interiors/eolas_library.yaml` |
| 試法坪 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`proving_ground`) |
| 妮爾內爾‧德米多 | NPC host | `world/lore/npc_profiles/eolas_homes_b.py` (`eolas_nirnel`), `places_eolas.py` |
| 雷林‧莉特弗特 | NPC host | `world/lore/npc_profiles/eolas_homes_b.py` (`eolas_raellin`), `places_eolas.py` |
| 賽爾內爾‧妮格汀加勒 | NPC host | `world/lore/npc_profiles/eolas_homes_b.py` (`eolas_saelnel`), `places_eolas.py` |
| 奈拉拉‧弗羅斯特威洛 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_naelara`), `places_eolas.py` |
| 希瑞爾溫‧布瑞特瓦特爾 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_sirelwen`), `places_eolas.py` |
| 泰莉斯‧恩貝爾莉夫 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_taelith`), `places_eolas.py` |
| 幻童精靈 | Race branch (人稱) | `tmp/story_settings/world_info.md` 種族設定 › 精靈族; `docs/lore/overview.md` 精靈族 |
| 幽月香草藥露 | Item (`eolas_herb_tonic`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`eolas_remedies`) |
| 魔力藥水 | Item (`mana_potion`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`eolas_remedies`) |
| 強效治療藥水 | Item (`greater_healing_potion`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`eolas_remedies`) |
| 幽月窯烤豆餅 | Item (`eolas_kiln_flatbread`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`eolas_fare`) |
| 普通餐食 | Item (`meal`) | `world/lore/items/data_core_items.py`, `world/lore/settlements/assortments.py` (`eolas_fare`) |

---

## 7. Offline Verification and Lint Results

- Baseline before the edit: `check_map_sources.py` ended `RESULT: game-ready as far as static checks can tell` with `game-adoption cross-file problems: 0`; the dependency items `eolas_proving_wand` and `fionnen_leafweave_garb` both resolved; the specified free-ID search over `content world docs/development` found no `eolas_nirnel`.
- `world.lore.dialogue.DIALOGUE_SNAPSHOT` loads 31 tables with no `DialogueSourceError`.
- `world.lore.settlements.places.PLACE_REGISTRY` resolves the three homes' `host_profile_key` to `eolas_nirnel`, `eolas_raellin` and `eolas_saelnel`.
- `npc_content_lint.py --places` over the three tables exits 0 with zero errors and one warning, dispositioned in section 8.
- The Traditional Chinese linter reports zero errors over the three dialogue files, the profile module and the three interior documents. Every warning is listed in section 8.
- `check_map_sources.py` reports no structure error, `game-adoption cross-file problems: 0`, and ends `RESULT: game-ready as far as static checks can tell`.
- `tools.map_reference_context --check` reports the reference context up to date.
- `tools.contract_gate` ends `contract gate passed`; `tools.test_data_lint check` and `tools.spec_traceability check` exit 0.
- The six focused Evennia test labels of the change end `OK`. `world.rules.tests.test_guild_config` discovers 119 tests, over the guard's 100, so it runs in two focused commands whose counts add to 119 and both end `OK`. The one module that fails when run entirely alone, `test_item_offer_definitions`, fails identically on `master` because it depends on a neighbouring module having published the map world; the focused command that keeps that order passes.
- Browser playback was not performed in this session; the text emission and the browser player read the same authored scenes. The in-game walkthrough stays open as workflow follow-up.

## 8. Lint Warning Dispositions

- `npc_content_lint.py` `eolas_saelnel.yaml` topic_04 `[reduplication] 「拉拉」` stands. 拉拉 is the authored given name 奈拉拉 inside 奈拉拉‧弗羅斯特威洛, not a reduplicated adverb.
- The Traditional Chinese linter's `[english-term]` warnings over the three dialogue files name YAML keys, scene identifiers and the hosts' romanised slugs. They are structural tokens, not player prose.
- The same `[english-term]` warnings over `eolas_homes_b.py` name Python identifiers, docstring module paths and the romanised slugs.
- The same `[english-term]` warnings over the three interior documents name the header comment, the YAML keys and the doorway aliases.
- No other warning category appears.

## 9. Test Adjustment Notes

No test module, assertion, fixture or data pin was added or edited. The shard modules this change extends were already enumerated by `unpin-village-test-data`, and the focused test runs are recorded in the change's own verification.
