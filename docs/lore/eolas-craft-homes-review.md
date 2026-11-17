# Eolas Craft Homes Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `eolas-village-craft-homes` change (`eolas_naelara`, `eolas_sirelwen`, `eolas_taelith`), the three homes it adds to 幽月谷村, and the prose that ships with them: the compact cards, the `misunderstood` voice lines, the room descriptions of the three interiors, the greetings and the twelve scenes of the three dialogue tables.

### Profile, Place and Dialogue Bindings

- `eolas_naelara_home` (place: 奈拉拉的家, host: 奈拉拉‧弗羅斯特威洛) -> `world/lore/dialogue/content/eolas_naelara.yaml`
- `eolas_sirelwen_home` (place: 希瑞爾溫的家, host: 希瑞爾溫‧布瑞特瓦特爾) -> `world/lore/dialogue/content/eolas_sirelwen.yaml`
- `eolas_taelith_home` (place: 泰莉斯的家, host: 泰莉斯‧恩貝爾莉夫) -> `world/lore/dialogue/content/eolas_taelith.yaml`

Each file is named after the host's profile key and declares its topics under the place's `dialogue_key`; the file declares no owner field.

### Canonical Sources

- `tmp/story_settings/world_info.md` (sections: 種族設定 › 精靈族; 生活方式 › 性文化; 社會與文化 › 教育、婚姻、倫理觀; 特殊設定 › 精靈與外界互動).
- `docs/lore/overview.md` (精靈族, 性別與生殖, 性愛與身體).
- `docs/lore/settlement-locations.md` (幽月谷村 in 聚落差異深論; 公共浴場 聚落差異).
- `world/lore/npc_profiles/eolas_homes_a.py` (the three profiles and their cards).
- `world/lore/settlements/places_eolas.py` (`eolas_naelara_home`, `eolas_sirelwen_home`, `eolas_taelith_home`).
- `world/lore/settlements/assortments.py` (`eolas_silkwork`, `eolas_wandcraft`, `eolas_kilnware`).
- `content/maps/interiors/eolas_naelara_home.yaml`, `eolas_sirelwen_home.yaml`, `eolas_taelith_home.yaml`.
- `skill://npc-dialogue-content` with `references/scene-schema.md`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

The world source states that the Eolas are the 幻童精靈 of 幽月谷村, that all elves are women, that elven society has no fixed trades, no marriage and no formal schooling, and that knowledge comes from a long life. `docs/lore/overview.md` and `docs/lore/magic-system.md` record the Eolas appearance as fixed at twenty years. No player-facing line states an age, an apparent age or a count of years: the hosts' long lives show only in what they remember, how they speak and what their hands know.

---

## 2. Mandatory Lore Checks

### Standing, Rarity and the Absence of Commerce

- Canon: about 300 elves exist across three branches, and the three human and beastfolk nations rank them above royalty. Elves need nothing from outsiders and are neither servants nor curiosities.
- Society: no fixed profession division, no caste, no apprenticeship. The village has no shop as an institution, no posted hours and no proprietor. A villager makes what she loves in her own home and shares it with neighbours or the rare visitor who finds the valley.
- How the change reads it: no card, greeting or scene uses shopkeeper vocabulary. There is no counter, no sign, no stock count. The door is a door, the shelf holds what she finished this season, and the copper is the village's way of looking after a guest.
- Host handling:
  - `eolas_naelara`: keeps the 蛛絲林, reels the silk and weaves the white cloth the village wears. She receives a guest the way she receives a neighbour and lets the loom speak for her work.
  - `eolas_sirelwen`: works the 試煉場, writes down every result and carves short wands for her own experiments. She judges a visitor by what that visitor wants to try, never by rank.
  - `eolas_taelith`: tends the shared 窯場 and fires the village's bowls, glass and lamp globes. The kiln's heat is the room's own warmth, and she talks about it the way she talks about her work.

### Body and Sex

- Canon: elves have no concept of shame about nudity, the body or sex (`對裸露、性器官、性行為完全沒有羞恥概念`), treat sex as a natural need like breathing (`視性愛為如同呼吸般自然的生理需求`), and give it about 80% of their time. Elven sex between women is ordinary joy, and what they do with their bodies grows more intense over a long life. Other races look away out of awe rather than moral judgment.
- `docs/lore/settlement-locations.md` puts all three villages at open pools with no partitions and no attendant; that contrast is the hook the village's stories use.
- How the change reads it: the ease is stated outright in the hosts' own words, at the frankness of `world/lore/dialogue/content/ciaran_vethiel.yaml` topic_03 and past it where the host's subject invites it. Naelara speaks of what the white cloth is worn for and left off, and of the body as nothing to hide. Sirelwen speaks of what a body is asked to bear in spellwork and of the night after. Taelith speaks of the heat the kiln puts in a room and what it does to a body. Explicit wording sits in the hosts' speech, in narration and in the cards.
- The one limit is structural, not tonal: an actor line never grants consent, initiates or promises an act. The frankness rides in what a host says and does, never in a scene the player is written into.

### Religion

- Canon: elves never proselytise, and outsiders do not know their faith or the truth of the three goddesses. No non-elf NPC explains 神之秘法.
- Host handling: none of the three hosts teaches theology, names a goddess or explains a divine chain. The white cloth is described as the village's everyday garment, not as a rite.

---

## 3. Retained Service Behaviours and Assortment Consistency

All three homes keep their authored place binding without alteration.

- `eolas_naelara_home` stocks `eolas_silkwork` (精靈蛛絲, 精靈傳統服飾). She reels the silk herself and weaves the cloth on her own loom; buy-back accepts only her own unused silk and dresses, and she declines cloth from outside because she cannot read its thread or dye.
- `eolas_sirelwen_home` stocks `eolas_wandcraft` (幽月練習短杖). She cuts each wand from valley wood and carves it for the element she is studying; buy-back accepts only her own unbroken wands, and she declines staves from outside.
- `eolas_taelith_home` stocks `eolas_kilnware` (幽月琉璃墜, 魔法燈). She blows the glass and fires the globes in the shared kiln; buy-back accepts only her own unbroken glass and lamps, and she declines wares fired elsewhere.

No line of dialogue delivers a free repair, a custom commission, a discount or a price figure. The scenes name goods by their registry display name and state no quantity.

---

## 4. Per-Topic Intent and Scene Structure Review

Every scene declares `revision: r1`, opens with a complete actor utterance, holds five to seven lines and carries at least one host line. No topic declares `requires`, `unavailable`, a variant, a predecessor or a disclosure; every topic is open.

### A. `eolas_naelara_home` (奈拉拉‧弗羅斯特威洛)

**Card and voice review.** The public leaf reads her as the village's silk keeper beside the 蛛絲林, reeling the silk and weaving the white cloth, and it states the elves' ease about the body and about sex in her own words; the appearance, personality, life story and habit leaves carry the brief (pale silver hair tied back from the webs, threads caught on her sleeves, the webs counted at dawn) and the speech leaf keeps the slow, low register every scene uses. `identity.hidden` is empty as the brief requires, `voice.greeting` stays empty because the table's greeting opens, and `voice.misunderstood` asks whether the visitor came for the silk or the white dress, which the greeting's offer answers. Canon: 種族設定 › 精靈族 (no shop, a maker's own home); 生活方式 › 性文化. The card agrees with the dialogue: the same grove, the same thin cloth, the same quiet.

1. **Opening greeting**: Naelara stops the loom, asks the guest to step softly because the spiders have just finished a new web, and offers the silk and the white dress. The cloth sits loose on one shoulder and she does not gather it. Source: 生活方式 › 性文化 (no shame about the body); 種族設定 › 精靈族 (no shop, a maker's own home).
2. `eolas_naelara_home.topic_01` (`keyword`: 養蛛, `label`: 養蛛): the spiders feed themselves; quiet steps are the keeper's whole craft, and a season of silk was lost to a passer-by. Source: `docs/lore/settlement-locations.md` 幽月谷村 (養蛛取絲) and the 蛛絲林 node.
3. `eolas_naelara_home.topic_02` (`keyword`: 蛛絲, `label`: 蛛絲): 精靈蛛絲 is tough, fine and useful for cloth, cord and bowstring; the sheltered valley is why the webs are dense. She refuses to discuss a price outside the valley. Source: 精靈蛛絲 registry row; 幽月谷村 養蛛取絲.
4. `eolas_naelara_home.topic_03` (`keyword`: 白衣, `label`: 白衣): the 精靈傳統服飾 is the village's everyday white cloth, woven thin so the body can breathe and be seen; the elves walk bare without a second glance, and sex is as ordinary as breathing. A guest who finds it too sheer brought his own rules into the valley. Source: 生活方式 › 性文化; 社會與文化 › 倫理觀; `ciaran_vethiel.yaml` topic_03.
5. `eolas_naelara_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back her own unused silk and dresses for copper and declines outside cloth. Source: the home's `eolas_silkwork` service.

### B. `eolas_sirelwen_home` (希瑞爾溫‧布瑞特瓦特爾)

**Card and voice review.** The public leaf reads her as the villager most often on the 試煉場, testing all eight elements, writing down what happened and leaving carved wands on the rack; the appearance leaf keeps the brief (hair cut short after one fire too many, ink on the fingers, the scorched hem she has not noticed) and the speech leaf keeps the fast, self-correcting register that answers a question with a better one. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` asks whether the visitor wants a wand or wants to watch, which matches the greeting's invitation to try one. Canon: 種族設定 › 精靈族 (親和所有屬性魔法); 生活方式 › 性文化. The card agrees with the dialogue: the experiments, the burns and the body's limits are the same story.

1. **Opening greeting**: Sirelwen looks up from a slate, asks which element the guest favours, points at the wand rack and offers to let the visitor try one at her risk. She opens her scorched hem to the air, the burn across her chest uncovered. Source: 生活方式 › 性文化; 幽月谷村 試煉場.
2. `eolas_sirelwen_home.topic_01` (`keyword`: 法術, `label`: 法術): the 試煉場 takes fire, ice and lightning because it sits far from the dwellings; she writes the intent before and the result after, and a spell that works once does not count. Source: the 試煉場 node description (離住屋最遠); 種族設定 › 精靈族 (learning by long practice).
3. `eolas_sirelwen_home.topic_02` (`keyword`: 短杖, `label`: 短杖): 幽月練習短杖 is cut from old valley wood, dried and shaped per element; the wand casts nothing on its own, but magic runs straighter through it, so the same spell leaves the hand with more force and takes less out of the caster, and a burnt wand is cheaper to replace than a burnt hand. Source: the item registry row, the `world/rules/rulebook/equipment_effects.yaml` row and the 幽月杖作 shelf.
4. `eolas_sirelwen_home.topic_03` (`keyword`: 元素, `label`: 元素): the Eolas touch all eight elements and none of them comes free; her own experiment burnt the room down, and what a body can bear is part of what she learns. The night after is spoken of plainly. Source: 種族設定 › 精靈族 (親和所有屬性魔法); 生活方式 › 性文化.
5. `eolas_sirelwen_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back her own unbroken wands and declines staves from outside. Source: the home's `eolas_wandcraft` service.

### C. `eolas_taelith_home` (泰莉斯‧恩貝爾莉夫)

**Card and voice review.** The public leaf reads her as the keeper of the shared 窯場 who fires bowls, glass and lamp globes, and it lets her speak of the kiln's heat on a body without embarrassment; the appearance leaf keeps the brief (copper-red hair under a soot-marked cloth, ash on the forearms, her own glass drop at the throat) and the speech leaf keeps the quick, hand-talking register with 喔 and 啦. `identity.hidden` is empty, `voice.greeting` stays empty, and `voice.misunderstood` asks whether it is about the glass or the lamps, which the greeting asks first. Canon: 幽月谷村 (共用窯燒陶與玻璃); 生活方式 › 性文化. The card agrees with the dialogue: the same kiln, the same glass, the same warmth.

1. **Opening greeting**: Taelith wipes kiln ash from her hands, lifts a fresh glass drop into the doorway light and asks whether the guest came for the glass or the lamps. Source: 幽月谷村 (共用窯燒陶與玻璃); 生活方式 › 性文化 (the body spoken of without embarrassment).
2. `eolas_taelith_home.topic_01` (`keyword`: 窯火, `label`: 窯火): the 窯場 is shared, whoever has blanks queues for it, and the village's bowls, plates, glass drops and lamp globes come out of it; firing depends on the thickness of the piece. Source: the 窯場 node description.
3. `eolas_taelith_home.topic_02` (`keyword`: 琉璃墜, `label`: 琉璃墜): 幽月琉璃墜 is glass shaped in fire; worn on the skin it steadies the casting and the flow of magic, and she likes how it feels more than what it does. Source: the item registry row and the 幽月窯作 shelf.
4. `eolas_taelith_home.topic_03` (`keyword`: 魔法燈, `label`: 魔法燈): the globes are blown here and the thin glass throws light far; beyond 深林獸徑 the trees close in and a lamp is what keeps a walker on the path. Source: the item registry row; the 深林獸徑 node.
5. `eolas_taelith_home.topic_04` (`keyword`: 收回, `label`: 收回): she takes back her own unbroken glass and lamps and declines wares fired elsewhere. Source: the home's `eolas_kilnware` service.

---

## 5. Room Prose Review

- `eolas_naelara_home` (奈拉拉的家): a rock-cut room beside the 蛛絲林, reels of silk on pegs, a loom by the door and white cloth folded on a stone shelf. The prose is a lived-in room: no signboard, no counter, no shopkeeper wording.
- `eolas_sirelwen_home` (希瑞爾溫的家): a rock-cut room at the edge of the 試煉場, slates of notes on the wall, wand blanks drying on a rack and a scorch mark by the door.
- `eolas_taelith_home` (泰莉斯的家): a rock-cut room facing the 窯場, shelves of bowls and glass, a rack of pendants catching the light and the kiln's warmth through the doorway.

None of the three names contains 店 or 舖, none of the descriptions contains 櫃檯 or 招牌, and none carries an ASCII word or a change identifier.

---

## 6. Style and Constraint Compliance Verification

- **In character only**: no command, backtick, syntax token, attribute number or interface element appears in the prose.
- **Traditional Chinese**: full-width punctuation throughout, no 您, no sentence-final 的 before a comma or a full stop, no half-width punctuation beside Chinese characters.
- **No wuxia vocabulary**: no 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫 or 掌門.
- **No proprietor vocabulary**: none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門 or 打烊 appears in a village table.
- **Scene shapes**: all twelve scenes open with an actor speech line, hold five to seven lines, carry at least one host line and declare `revision: r1`.
- **No age**: no 歲 figure, no apparent age and no count of years appears in any card, room description, greeting or scene.
- **No mechanics**: no line promises a skill, a stat, a status or a command. The scenes describe the world-side act only.

### Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
|---|---|---|
| 幽月谷村 | Settlement | `world/lore/settlements/settlements.py` (`elven_village_eolas`) |
| 蛛絲林 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`silk_grove`), `places_eolas.py` (`eolas_naelara_home`) |
| 試煉場 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`proving_ground`), `places_eolas.py` (`eolas_sirelwen_home`) |
| 窯場 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`kiln_yard`), `places_eolas.py` (`eolas_taelith_home`) |
| 深林獸徑 | Settlement node | `content/maps/settlements/elven_village_eolas.yaml` (`forest_trail`) |
| 圖書館 | Interior | `content/maps/interiors/eolas_library.yaml` |
| 奈拉拉‧弗羅斯特威洛 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_naelara`), `places_eolas.py` |
| 希瑞爾溫‧布瑞特瓦特爾 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_sirelwen`), `places_eolas.py` |
| 泰莉斯‧恩貝爾莉夫 | NPC host | `world/lore/npc_profiles/eolas_homes_a.py` (`eolas_taelith`), `places_eolas.py` |
| 幻童精靈 | Race branch (人稱) | `tmp/story_settings/world_info.md` 種族設定 › 精靈族; `docs/lore/overview.md` 精靈族 |
| 精靈蛛絲 | Item (`elven_spider_silk`) | `world/lore/items/data_armor_accessories_materials.py`, `world/lore/settlements/assortments.py` (`eolas_silkwork`) |
| 精靈傳統服飾 | Item (`elven_traditional_robe`) | `world/lore/items/data_named_equipment.py`, `world/lore/settlements/assortments.py` (`eolas_silkwork`) |
| 幽月練習短杖 | Item (`eolas_proving_wand`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`eolas_wandcraft`) |
| 幽月琉璃墜 | Item (`eolas_glass_pendant`) | `world/lore/items/data_elven_village_goods.py`, `world/lore/settlements/assortments.py` (`eolas_kilnware`) |
| 魔法燈 | Item (`magic_lamp`) | `world/lore/items/data_armor_accessories_materials.py`, `world/lore/settlements/assortments.py` (`eolas_kilnware`) |

---

## 7. Offline Verification and Lint Results

- `world.lore.dialogue.DIALOGUE_SNAPSHOT` loads 28 tables with no `DialogueSourceError`.
- `world.lore.settlements.places.PLACE_REGISTRY` resolves the three homes' `host_profile_key` to `eolas_naelara`, `eolas_sirelwen` and `eolas_taelith`.
- `npc_content_lint.py --places` over the three tables exits 0 with zero errors and three warnings. All three warnings are the same `reduplication` prompt on 「拉拉」: it is the host's authored given name 奈拉拉, not a reduplicated adverb, so the line stands.
- The Traditional Chinese linter reports zero errors over the three dialogue files, the profile module and the three interior documents. Its remaining warnings are the English-term prompts for YAML keys, the profile module's Python identifiers and the hosts' romanised slugs.
- `check_map_sources.py` reports no structure error, `game-adoption cross-file problems: 0`, and ends `RESULT: game-ready as far as static checks can tell`.
- `tools.map_reference_context --check` reports the reference context up to date.
- Browser playback was not performed in this session; the text emission and the browser player read the same authored scenes.

The non-player-facing review of the rules is recorded in `docs/development/npc-editorial-review.md` under `eolas_homes_a hosts` and `eolas_homes_a dialogue tables`.

## 8. Test Adjustment Notes

- `world/lore/tests/test_settlements.py::DerivedShopRegistryTests::test_shops_are_derived_from_the_places_that_author_a_shop_identity` compared `SHOP_REGISTRY` against a literal roster of shop keys. The assertion now compares it with the shop identities the place registry authors, which is the rule the test states; no key was appended and no other assertion changed.
- The split test runs that the 100-test guard requires exposed a pre-existing ordering dependency in five rules test modules: they use a published map world but did not publish one, and only a neighbouring module in a bigger run did. Each of `world/rules/tests/test_npc_roster_validation.py`, `world/rules/tests/test_authored_dialogue_runtime.py`, `world/rules/tests/test_guild_config/test_assortment_shop_rules.py`, `world/rules/tests/test_guild_config/test_catalog_loading.py` and `world/rules/tests/test_guild_config/test_commerce_rulebook_slices.py` now calls `publish_shipped_map_world()` at import, the convention `test_service_host_roster.py` already follows. No assertion, key or shipped-data pin was added.
