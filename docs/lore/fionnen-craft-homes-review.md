# Fionnen Craft Homes Editorial Review

## 1. Scope and Canonical Ownership

This document records the editorial and lore verification for the `fionnen-village-craft-homes` change (`fionnen_corith`, `fionnen_gwynnel`, `fionnen_ithrlin`), the three craft homes it adds to 翠綠森林村, and the prose that ships with them: the compact cards, the `misunderstood` voice lines, the room descriptions of the three interiors, the greetings and the twelve scenes of the three dialogue tables.

### Profile, Place and Dialogue Bindings

- `fionnen_corith_home` (place: 科瑞斯的家, host: 科瑞斯‧蒙希斯佩爾) -> `world/lore/dialogue/content/fionnen_corith.yaml`
- `fionnen_gwynnel_home` (place: 格威內爾的家, host: 格威內爾‧斯威夫塔羅) -> `world/lore/dialogue/content/fionnen_gwynnel.yaml`
- `fionnen_ithrlin_home` (place: 伊斯爾林的家, host: 伊斯爾林‧斯塔爾威維爾) -> `world/lore/dialogue/content/fionnen_ithrlin.yaml`

Each file is named after the host's profile key and declares its topics under the place's `dialogue_key`; the file declares no owner field.

### Canonical Sources

- `tmp/story_settings/world_info.md` (sections: 種族設定 › 精靈族; 生活方式 › 性文化; 社會與文化 › 教育、婚姻、倫理觀; 特殊設定 › 精靈與外界互動).
- `docs/lore/overview.md` (精靈族, 性別與生殖, 性愛與身體).
- `docs/lore/settlement-locations.md` (翠綠森林村 in 聚落差異深論; 精靈村落 in the location-type table).
- `docs/lore/items.md` (性玩具: 恆振晶 and 纏枝魔藤 rows).
- `world/lore/npc_profiles/fionnen_homes_a.py` (the three profiles and their cards).
- `world/lore/settlements/places_fionnen.py` (`fionnen_corith_home`, `fionnen_gwynnel_home`, `fionnen_ithrlin_home`).
- `world/lore/settlements/assortments.py` (`fionnen_trinkets`, `fionnen_bowcraft`, `fionnen_attire`).
- `world/rules/rulebook/commerce/fionnen.yaml` (offers and shop hours).
- `content/maps/interiors/fionnen_corith_home.yaml`, `fionnen_gwynnel_home.yaml`, `fionnen_ithrlin_home.yaml`.
- `skill://npc-dialogue-content` with `references/scene-schema.md`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

The world source states that the Fionnen are the 森林精靈 of 翠綠森林村, that all elves are women, that elven society has no fixed trades, no marriage and no formal schooling, and that knowledge comes from a long life. No player-facing line states an age, an apparent age or a count of years: the hosts' long lives show only in what they remember, how they speak and what their hands know.

---

## 2. Mandatory Lore Checks

### Standing, Rarity and the Absence of Commerce

- Canon: about 300 elves exist across three branches, and the three human and beastfolk nations rank them above royalty. Elves need nothing from outsiders and are neither servants nor curiosities.
- Society: no fixed profession division, no caste, no apprenticeship. The village has no shop as an institution, no posted hours and no proprietor. A villager makes what she loves in her own home and shares it with neighbours or the rare visitor who finds the valley.
- How the change reads it: no card, greeting or scene uses shopkeeper vocabulary. There is no counter, no sign and no stock count. The door is a door, the shelf holds what she finished this season, and the copper is the village's way of looking after a guest.
- Host handling:
  - `fionnen_corith`: carves, tunes and raises what she likes to use herself, between the buttress roots of 樹根屋. She talks about each piece from her own wearing of it and lets a visitor take one for coin.
  - `fionnen_gwynnel`: shapes the village's longbows beside 木作空地, judges a visitor by the arm rather than by rank, and treats a bow left strung as a small neglect.
  - `fionnen_ithrlin`: weaves on a platform of 樹冠吊橋, chooses cloth by how it meets skin, and receives a guest the way she receives a neighbour.

### Body and Sex

- Canon: elves have no concept of shame about nudity, the body or sex (`對裸露、性器官、性行為完全沒有羞恥概念`), treat sex as a natural need like breathing (`視性愛為如同呼吸般自然的生理需求`), and give it the greater part of their time. Elven sex between women is ordinary joy, and what they do with their bodies grows more intense over a long life. Other races look away out of awe rather than moral judgment.
- How the change reads it: the ease sits in dress, bearing and how each host speaks of her own goods, at the frankness of `world/lore/dialogue/content/ciaran_vethiel.yaml` topic_03 and past it where the subject invites it. Corith states what her crystal does to the body from a full day and night of wearing it, and what the vine does when it wakes. Ithrlin's veil sits open without a second thought, and her white-dress topic states the village's ordinary nakedness and ordinary nights as her own fact.
- The one limit is structural, not tonal: an actor line never grants consent, initiates or promises an act. The frankness rides in what a host says and does, never in a scene the player is written into.

### Religion

- Canon: elves never proselytise, and outsiders do not know their faith or the truth of the three goddesses. No non-elf NPC explains 神之秘法.
- Host handling: none of the three hosts teaches theology, names a goddess or explains a divine chain. The white dress is described as the village's everyday garment, not as a rite.

---

## 3. Retained Service Behaviours and Assortment Consistency

All three homes keep their authored place binding without alteration.

- `fionnen_corith_home` stocks `fionnen_trinkets` (森林射手護腕, 恆振晶, 纏枝魔藤). She carves the bracer, tunes the crystal and raises the vine herself; buy-back accepts only her own pieces and she declines work made elsewhere.
- `fionnen_gwynnel_home` stocks `fionnen_bowcraft` (精靈長弓). She shapes each bow from a stave seasoned in her rafters; buy-back accepts only her own undamaged bows and she declines bows made elsewhere.
- `fionnen_ithrlin_home` stocks `fionnen_attire` (森林葉織獵衣, 精靈森林輕紗, 精靈傳統服飾). She weaves every piece on her own loom; buy-back accepts only her own cloth, which she unpicks for the thread, and she declines clothing from outside.

Every offer in `world/rules/rulebook/commerce/fionnen.yaml` sits inside its item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and each good the capital also sells is cheaper here. Shop hours match 暗影谷村: open 7, close 19, restock 6. No line of dialogue delivers a free repair, a custom commission, a discount or a price figure. The scenes name goods by their registry display name and state no quantity.

---

## 4. Per-Topic Intent and Scene Structure Review

Every scene declares `revision: r1`, opens with a complete actor utterance, holds six to eight lines and carries at least one host line. No topic declares `requires`, `unavailable`, a variant, a predecessor or a disclosure; every topic is open.

### A. `fionnen_corith_home` (科瑞斯‧蒙希斯佩爾)

**Card and voice review.** The public leaf reads her as the village's 巧作者 in 樹根屋 who carves 森林射手護腕, tunes 恆振晶 and raises 纏枝魔藤, and it lets her say that she makes them for her own pleasure and the village's and that a visitor may take one for coin; the appearance leaf keeps the brief (short tousled blonde hair, the loose wrap worn open, the crystal on a cord between her breasts, green stains from the vines), the personality and speech leaves keep the playful, frank register with 嘛 and 啦, and the life story keeps the human scholars who cannot read her crystals and the half of the village that keeps her vines. `identity.hidden` is empty as the brief requires, `voice.greeting` stays empty because the table's greeting opens, and `voice.misunderstood` is amused and asks whether it is about the bracers, the crystals or the vines. Canon: 種族設定 › 精靈族 (no fixed trades, a maker's own home); 生活方式 › 性文化.

1. **Opening greeting**: Corith sits at the window bench tuning a milky crystal against her forearm, looks up laughing and asks which kind of toy the guest came for. Source: 生活方式 › 性文化 (pleasure spoken of without evasion); 種族設定 › 精靈族 (no shop, a maker's own home).
2. `fionnen_corith_home.topic_01` (`keyword`: 護腕, `label`: 護腕): 森林射手護腕 is cut to the shape of the arm, the notch sits on the wrist bone so the wrist does not strain at full draw, a worn pair comes back for a new one, and the inner face is sanded and waxed so it does not bite. Source: the item registry row (`fionnen_archer_bracer`, 斐歐恩族弓手綁在持弓手臂上的木雕護腕); 種族設定 › 精靈族 特色 (擅長弓術).
3. `fionnen_corith_home.topic_02` (`keyword`: 恆振晶, `label`: 恆振晶): the 恆振晶's tiny vibration spell is tuned by rhythm, too fast stings and too slow scatters; worn against the skin it trembles all day at the most sensitive place; she wore it a full day and night herself and says how that night went; human scholars see only grooves. Source: `docs/lore/items.md` 性玩具 配戴型 恆振晶 row; 生活方式 › 性文化.
4. `fionnen_corith_home.topic_03` (`keyword`: 魔藤, `label`: 魔藤): 纏枝魔藤 is kept in the window light and watered when the soil dries; soaked through it wakes, climbs the body, works every sensitive place at a force that stops short of bruising, then withdraws to the pot and sleeps until the next watering; half the village's windowsills hold cuttings from her pots. Source: `docs/lore/items.md` 性玩具 可用型 纏枝魔藤 row; 生活方式 › 性文化.
5. `fionnen_corith_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back only the pieces she carved and tuned, judges their condition for copper, keeps the wood and crystal to reuse, and declines work from outside because another hand's craft would scatter under hers. Source: the home's `fionnen_trinkets` service; 種族設定 › 精靈族 (she works for love of the making).

### B. `fionnen_gwynnel_home` (格威內爾‧斯威夫塔羅)

**Card and voice review.** The public leaf reads her as the village's bow maker beside 木作空地 who shapes 精靈長弓 for whoever in the village wants one and lets a visitor take one for coin; the appearance leaf keeps the brief (tall, one long blonde braid, wood shavings on her bare shoulders, the draw hand calloused at two fingers), the personality and speech leaves keep the steady, sparing register and her impatience with a bow left strung, and the life story keeps the bows made before the canopy walk went up and the staves seasoned until they bend. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` is brief and asks whether it is about a bow. Canon: 種族設定 › 精靈族 (no fixed trades, 擅長弓術); 生活方式 › 性文化.

1. **Opening greeting**: Gwynnel sets down the drawknife, looks at the guest's arms, measures one and takes an unstrung bow from its peg. Source: 種族設定 › 精靈族 特色 (擅長弓術); the 弓棚 interior and 木作空地 node.
2. `fionnen_gwynnel_home.topic_01` (`keyword`: 製弓, `label`: 製弓): staves come from 木作空地 cuttings and are chosen by a straight grain, few knots and a deep note; they season in the rafters, turned so the wind dries them evenly, and are cut to the person's arm. Source: the 木作空地 node description (弓、箭在這裡做); 種族設定 › 精靈族 (ability from long practice).
3. `fionnen_gwynnel_home.topic_02` (`keyword`: 長弓, `label`: 長弓): the 精靈長弓 carries an arrow farther and holds steadier at full draw, costs strength, carries the archer's tremor instead of aiming for her, and rewards practice before accuracy. Source: the item registry row (`elven_longbow`, 精靈以自產弓術淬鍊而成的長弓); 種族設定 › 精靈族 特色.
4. `fionnen_gwynnel_home.topic_03` (`keyword`: 弓棚, `label`: 弓棚): the 弓棚 by 靶道 never shuts, strings hang on its wall, villagers take what they need without asking her, and a visitor takes a bow from her hand with copper in hers. Source: `content/maps/interiors/fionnen_bow_shed.yaml`; the 靶道 node; 聚落差異深論 精靈村落 (無掛牌商店，機能由個別精靈在家中承擔).
5. `fionnen_gwynnel_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back only her own undamaged bows, weighs the nock and limbs for copper, keeps broken wood to split for other work, and declines outside bows because the wood and the stringing differ. Source: the home's `fionnen_bowcraft` service.

### C. `fionnen_ithrlin_home` (伊斯爾林‧斯塔爾威維爾)

**Card and voice review.** The public leaf reads her as the village's 織衣者 on a platform of 樹冠吊橋 who weaves 森林葉織獵衣, 精靈森林輕紗 and the white 精靈傳統服飾, freely for the village and for coin for a visitor; the appearance leaf keeps the brief (pale gold hair loose to the hips, her own sheer veil with nothing under it, thread round two fingers), the personality and speech leaves keep the gentle, sensual, unembarrassed register with 呢 and 喔, and the life story keeps the weaving since the first platform, the dew thread gathered at dawn, and the village she has both dressed and undressed. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` is soft and asks whether it is about clothes or about weaving. Canon: 種族設定 › 精靈族 (no fixed trades); 生活方式 › 性文化; 社會與文化 › 倫理觀.

1. **Opening greeting**: Ithrlin lets the shuttle rest, turns in her sheer veil without gathering it, and asks what the guest likes against the skin. Source: 生活方式 › 性文化 (no shame about the body); 社會與文化 › 倫理觀 (精靈對性與裸露完全無羞恥概念).
2. `fionnen_ithrlin_home.topic_01` (`keyword`: 獵衣, `label`: 獵衣): 森林葉織獵衣 twists the forest's tough grass into its thread and is woven loose so it does not bind; the giant trees' low branches would snag thick cloth; running warms it; a hand's room is left under the arm for drawing and climbing. Source: the item registry row (`fionnen_leafweave_garb`, 為在巨木之間穿行而織的輕獵衣); the 翠綠森林村 paragraph of `docs/lore/settlement-locations.md`.
3. `fionnen_ithrlin_home.topic_02` (`keyword`: 輕紗, `label`: 輕紗): 精靈森林輕紗 is dew thread gathered before dawn while the dew still holds, only in season, fine and slow to spin, barely any weight, and follows the skin in the wind; she weaves only a few bolts a season. Source: the item registry row (`elven_forest_veil`) and the 森林輕紗 description in `ciaran_vethiel.yaml` topic_03; 生活方式 › 性文化.
4. `fionnen_ithrlin_home.topic_03` (`keyword`: 白衣, `label`: 白衣): the white 精靈傳統服飾 is the village's everyday garment, woven thin so skin feels the wind and people can be seen; no one thinks a body needs hiding, indoors and out, clothes open when it is hot, and bodies come together when they want like eating or sleeping; a guest looks away at first and stops when nobody laughs at him. Source: 生活方式 › 性文化; 社會與文化 › 倫理觀; `ciaran_vethiel.yaml` topic_03.
5. `fionnen_ithrlin_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back her own garments, unpicks and washes the thread and spins it again, pays copper for good cloth, keeps the worn for warp, and declines outside cloth because the twist and dye differ. Source: the home's `fionnen_attire` service.

---

## 5. Room Prose Review

- `fionnen_corith_home` (科瑞斯的家): a low room between buttress roots under the sloping trunk, a bench of carving tools and half-finished rings, milky crystals on a cloth, and potted vines climbing the bark. The prose is a lived-in room: no signboard, no counter, no shopkeeper wording.
- `fionnen_gwynnel_home` (格威內爾的家): a room between buttress roots beside 木作空地, staves seasoning in the rafters, a shaving horse in the corner, unstrung bows on pegs and a layer of shavings on the floor.
- `fionnen_ithrlin_home` (伊斯爾林的家): a canopy platform a few steps below the leaves, the floor moving with the wind through the boards, a loom where the light falls, veils hung under the beams and a folded hunting dress on a chest.

None of the three names contains 店 or 舖, none of the descriptions contains 櫃檯 or 招牌, and none carries an ASCII word or a change identifier.

---

## 6. Style and Constraint Compliance Verification

- **In character only**: no command, backtick, syntax token, attribute number or interface element appears in the prose.
- **Traditional Chinese**: full-width punctuation throughout, no 您, no sentence-final 的 before a comma or a full stop, no half-width punctuation beside Chinese characters.
- **No wuxia vocabulary**: no 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫 or 掌門.
- **No proprietor vocabulary**: none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門 or 打烊 appears in a village table.
- **Scene shapes**: all twelve scenes open with an actor speech line, hold six to eight lines, carry at least one host line and declare `revision: r1`.
- **No age**: no 歲 figure, no apparent age and no count of years appears in any card, room description, greeting or scene.
- **No mechanics**: no line promises a skill, a stat, a status or a command. The scenes describe the world-side act only.

### Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
|---|---|---|
| 翠綠森林村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_fionnen`) |
| 樹根屋 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`root_dwellings`), `places_fionnen.py` (`fionnen_corith_home`) |
| 木作空地 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`craft_glade`), `places_fionnen.py` (`fionnen_gwynnel_home`) |
| 樹冠吊橋 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`canopy_walk`), `places_fionnen.py` (`fionnen_ithrlin_home`) |
| 靶道 | Settlement node | `content/maps/settlements/elven_village_fionnen.yaml` (`archery_lane`) |
| 弓棚 | Interior | `content/maps/interiors/fionnen_bow_shed.yaml` |
| 科瑞斯‧蒙希斯佩爾 | NPC host | `world/lore/npc_profiles/fionnen_homes_a.py` (`fionnen_corith`), `places_fionnen.py` |
| 格威內爾‧斯威夫塔羅 | NPC host | `world/lore/npc_profiles/fionnen_homes_a.py` (`fionnen_gwynnel`), `places_fionnen.py` |
| 伊斯爾林‧斯塔爾威維爾 | NPC host | `world/lore/npc_profiles/fionnen_homes_a.py` (`fionnen_ithrlin`), `places_fionnen.py` |
| 斐歐恩族 | Race branch (人稱) | `tmp/story_settings/world_info.md` 種族設定 › 精靈族; `docs/lore/overview.md` 精靈族 |
| 森林射手護腕 | Item (`fionnen_archer_bracer`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`fionnen_trinkets`) |
| 恆振晶 | Item (`tremor_crystal`) | `world/lore/items/data_intimacy_items.py`, `docs/lore/items.md` 性玩具, `world/lore/settlements/assortments.py` (`fionnen_trinkets`) |
| 纏枝魔藤 | Item (`embracing_vine`) | `world/lore/items/data_intimacy_items.py`, `docs/lore/items.md` 性玩具, `world/lore/settlements/assortments.py` (`fionnen_trinkets`) |
| 精靈長弓 | Item (`elven_longbow`) | `world/lore/items/data_regional_equipment.py`, `world/lore/settlements/assortments.py` (`fionnen_bowcraft`) |
| 森林葉織獵衣 | Item (`fionnen_leafweave_garb`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`fionnen_attire`) |
| 精靈森林輕紗 | Item (`elven_forest_veil`) | `world/lore/items/data_regional_equipment.py`, `world/lore/settlements/assortments.py` (`fionnen_attire`) |
| 精靈傳統服飾 | Item (`elven_traditional_robe`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`fionnen_attire`) |

---

## 7. Offline Verification and Lint Results

- `world.lore.dialogue.DIALOGUE_SNAPSHOT` loads 34 tables with no `DialogueSourceError`.
- `world.lore.settlements.places.PLACE_REGISTRY` resolves the three homes' `host_profile_key` to `fionnen_corith`, `fionnen_gwynnel` and `fionnen_ithrlin`.
- `npc_content_lint.py --places` over the three tables exits 0 with zero errors and zero warnings.
- The Traditional Chinese linter reports zero errors over the three dialogue files, the profile module and the three interior documents. Its remaining warnings are the English-term prompts for YAML keys, the profile module's Python identifiers and the hosts' romanised slugs.
- `check_map_sources.py` reports no structure error, `game-adoption cross-file problems: 0`, and ends `RESULT: game-ready as far as static checks can tell`.
- `tools.map_reference_context --check` reports the reference context up to date.
- `tools.contract_gate` ends `contract gate passed` over reference-context, traceability, observability, test-data, manifests and contracts.
- `tools.test_data_lint check` and `tools.spec_traceability check` both exit 0.
- `openspec validate fionnen-village-craft-homes --strict` reports the change valid.
- Browser playback was not performed in this session; the text emission and the browser player read the same authored scenes.
- The in-game walkthrough recorded under the change's Workflow follow-up is a human step and is not claimed here.

The non-player-facing review of the rules is recorded in `docs/development/npc-editorial-review.md` under `fionnen_homes_a hosts` and `fionnen_homes_a dialogue tables`.

---

## 8. Test Adjustment Notes

- `world/lore/tests/test_settlements.py::PlaceRegistryTests::test_place_iteration_order_is_the_load_bearing_slice_order` now imports the new place slice and appends its rows to the concatenation it compares with the head of `PLACE_REGISTRY`. No assertion was weakened and no shipped key was appended.
- `tests/test_map_runtime_contract.py` lists the new place slice file beside the existing ones, so its import-time contract check covers it.
- `tools/map_reference_context.py::_find_place_source_file` maps the new slice, so regenerated references cite `world/lore/settlements/places_fionnen.py`.
- Running the `world.rules.tests.test_guild_config` package alone is refused by the 100-test guard (119 tests), so its modules were run as separate labels. `world.rules.tests.test_guild_config.test_item_offer_definitions` then fails at module level with `world.maps.map_data.SettlementNotLoaded: settlement maps are not loaded; adopt the map world with world.maps.runtime before using map consumers`. The failure is a pre-existing ordering dependency: the module uses the published map world but does not publish one, and a neighbouring module in a larger run does it. The same module passes when run beside `test_assortment_shop_rules` (40 tests, `OK`). No test file was edited beyond the two the design names, and no assertion or key was added.
