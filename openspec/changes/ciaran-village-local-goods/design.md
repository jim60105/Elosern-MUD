# Design

## Context

See `proposal.md` for motivation. Facts found while planning:

- 暗影谷村's six shelves are `elven_crafted_arms`, `elven_attire`, `elven_fare`, `elven_sundries`, `elven_adornments` and `elven_remedies` in `world/lore/settlements/assortments.py`, priced in `world/rules/rulebook/commerce/ciaran.yaml`. Assortment keys are permanent IDs and are not renamed.
- After the village home changes, 幽月谷村 sells `elven_spider_silk` and `elven_traditional_robe` (shelf `eolas_silkwork`, host 奈拉拉‧弗羅斯特威洛 at 蛛絲林), and 翠綠森林村 sells `elven_forest_veil` and `elven_traditional_robe` (shelf `fionnen_attire`, host 伊斯爾林‧斯塔爾威維爾 at 樹冠吊橋) and `elven_candied_blossom` (shelf `fionnen_fare`, host 盧梅斯‧布瑞特莉夫 at 花蕊蜜園).
- `world/lore/items/data_elven_village_goods.py` exists (from `elven-village-local-goods`) and is the last slice of `ITEM_REGISTRY`; rows appended to its `ROWS` keep every existing position.
- `world/rules/item_effects.py` accepts `remove_status` with a concrete status key from `world/rules/rulebook/buffs.yaml`; `poisoned` is a key there. No existing item removes it alone (`baptismal_holy_water` removes every negative status).
- Food and material items carry no mechanism.
- Existing tests that read this content derive it from the registries: a merchant's table must contain the last two characters of at least one display name on her own shelf; no two merchants share a greeting; every dialogue table has exactly four topics; every good sold both in a village and in the capital is strictly cheaper in the village; village tables contain none of 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門, 打烊; village room names contain neither 店 nor 舖 and room prose neither 櫃檯 nor 招牌.
- `content/map-reference-context.json` fingerprints `world/lore/**/*.py` and `world/rules/**/*.yaml`, and the contract gate checks it.
- World source: `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md`. `tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path. 暗影谷村 is the Ciaran village: dark elves (brown skin, mostly silver hair and red eyes, 160-180 cm), fire and dark magic, a deep blade culture, on the western, underground side of the central range. The village map (`content/maps/settlements/elven_village_ciaran.yaml`) has a herb garden, a stream with a dyeing shoal downstream, a weaving slope hung with plant-dyed cloth, and a silver-leaf slope where shells and rounded crystal sand are worked into ornaments.

## Goals / Non-Goals

**Goals:**

- Every good on a 暗影谷村 shelf is either made in this valley or a general potion; none is another village's produce.
- The village gains a food and a remedy of its own.
- Cards, rooms and dialogue agree with the shelves.

**Non-Goals:**

- No change to place rows, hosts' names, ages, capabilities or shop hours.
- No rename of any assortment key, topic ID or item key. No change to the capital's shelves or prices.
- No new vocabulary: no new kind, icon, rarity, price band, status key or effect verb.
- No test, and no assertion naming an item, price or line of this change.

## Decisions

### Decision 1: five new items

Append to `ROWS` in `world/lore/items/data_elven_village_goods.py`, after the existing rows, in this order. All rows set `sellable=True`. `summary_zh` is one line of Traditional Chinese, at most 128 characters, with no `<`, URL, emoji, line break or ASCII digit; write it from the "Summary covers" cell.

| key | `display_name_zh` | kind / icon | rarity | `price_table_key` | mechanism | Summary covers |
| --- | --- | --- | --- | --- | --- | --- |
| `ciaran_nightbloom_preserve` | 暗影谷夜綻花釀 | `FOOD` / `FOOD` | `UNCOMMON` | `specialty_food` | none | night-blooming valley flowers steeped in syrup, the fare host's best work |
| `ciaran_ember_mushroom_skewer` | 暗影谷炭烤蕈串 | `FOOD` / `FOOD` | `COMMON` | `specialty_food` | none | valley mushrooms roasted over embers on a skewer |
| `ciaran_indigo_dye` | 暗影谷藍染 | `MATERIAL` / `MATERIAL` | `COMMON` | `material` | none | a cake of plant dye from the shoal downstream, the blue of the village's cloth |
| `ciaran_crystal_sand` | 暗影谷晶砂 | `MATERIAL` / `MATERIAL` | `UNCOMMON` | `material` | none | rounded crystal sand panned from the valley stream, worked into ornaments |
| `ciaran_antivenom_tincture` | 暗影谷解毒草露 | `POTION` / `POTION` | `UNCOMMON` | `potion` | `ItemUseMechanics(consumable=True, combat_allowed=True)` | a tincture of herb-garden plants that clears poison |

The fare host's surname 妮特布倫 is Nightbloom (夜綻); the preserve is named for the same flower. No equipment item is added, so `EquipmentModifierKey` and `equipment_effects.yaml` are untouched.

### Decision 2: the tincture's effect

Add to `items:` in `world/rules/rulebook/item_effects.yaml`, verbatim:

```yaml
  ciaran_antivenom_tincture:
    effects:
      - remove_status: poisoned
```

Alternative considered: `remove_status: negative`. Rejected: that is the holy water's effect; a village herb tincture clears one thing.

### Decision 3: the shelves

In `ASSORTMENT_REGISTRY` (`world/lore/settlements/assortments.py`), change only the `item_keys` of four entries. Keys, display names and shelf policies stay.

| Assortment | `item_keys` today | `item_keys` after |
| --- | --- | --- |
| `elven_attire` | `"dark_elf_kimono", "dark_elf_ninja_garb", "elven_traditional_robe", "elven_forest_veil"` | `"dark_elf_kimono", "dark_elf_ninja_garb"` |
| `elven_fare` | `"elven_candied_blossom"` | `"ciaran_nightbloom_preserve", "ciaran_ember_mushroom_skewer"` |
| `elven_sundries` | `"elven_spider_silk"` | `"ciaran_indigo_dye", "ciaran_crystal_sand"` |
| `elven_remedies` | `"greater_healing_potion", "mana_potion"` | `"ciaran_antivenom_tincture", "greater_healing_potion", "mana_potion"` |

Each new item's kind is already allowed by its shelf (`FOOD`, `MATERIAL`, `POTION`). Rewrite the comment block above the elven assortments: it currently says the village shares `elven_spider_silk` and `elven_candied_blossom` with the capital; say instead that each of the three villages sells what it makes, and that the goods a village shares with the capital are priced at everyday figures at home.

### Decision 4: offers and prices

In `world/rules/rulebook/commerce/ciaran.yaml`, replace the `offers` of the four assortments so they read exactly as below. Leave `elven_crafted_arms`, `elven_adornments` and the whole `shops:` section unchanged. Update the comments so none mentions a removed good.

```yaml
  - key: elven_attire
    offers:
      - item_key: dark_elf_kimono
        buy_copper: 100
        sell_copper: 50
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: dark_elf_ninja_garb
        buy_copper: 100
        sell_copper: 50
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
  - key: elven_fare
    offers:
      - item_key: ciaran_nightbloom_preserve
        buy_copper: 20
        sell_copper: 10
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: ciaran_ember_mushroom_skewer
        buy_copper: 12
        sell_copper: 6
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
  - key: elven_sundries
    offers:
      - item_key: ciaran_indigo_dye
        buy_copper: 30
        sell_copper: 15
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: ciaran_crystal_sand
        buy_copper: 40
        sell_copper: 20
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
  - key: elven_remedies
    offers:
      - item_key: ciaran_antivenom_tincture
        buy_copper: 60
        sell_copper: 30
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
      - item_key: greater_healing_potion
        buy_copper: 150
        sell_copper: 75
        max_stock: 5
        initial_stock: 2
        restock_quantity: 2
      - item_key: mana_potion
        buy_copper: 80
        sell_copper: 40
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
```

Price basis, the 暗影谷村 pattern the user confirmed (local produce at everyday figures in the village that makes it): the preserve takes the figure the candied blossom had (20); the skewer matches the other villages' plain local food (12); the two materials sit just above the `material` band floor of 20; the tincture matches the other villages' local potions (60, `potion` band 50..500). The kept rows are unchanged.

### Decision 5: cards

Edit only the sentences that name a removed good or must name a new one. Keep every other sentence, the ages and the `misunderstood` lines. Stay inside the card limits (leaf 600, identity section 600, whole card 2000 code points). Write from the world source in Context; no card speaks of a shop, stock or business.

| Profile (file) | What changes |
| --- | --- |
| `ciaran_lareneth` (`ciaran_homes_a.py`) | Her best work becomes 暗影谷夜綻花釀, made from night-blooming valley flowers; she also roasts mushrooms over embers. Every mention of 精靈蜜漬花蕊, 花蕊 picking and honey-candying becomes the night flowers and their syrup: she gathers them after dusk, when they open. Her surname means the same flower; a line may say the flower was named in her dwelling's name. |
| `ciaran_valwyn` (`ciaran_homes_b.py`) | She no longer braids 精靈蛛絲. What she gathers most and lets guests take is 暗影谷藍染, pressed from the plants of the dyeing shoal downstream, and 暗影谷晶砂, panned from the stream. Keep her as the 蒐羅者 whose every curio has a story, and keep that she gives shells and crystal sand to 格威娜拉‧希爾維爾莉夫. |
| `ciaran_vethiel` (`ciaran_homes_b.py`) | She weaves the dark-elf garments: 精靈短袍傳統服飾 and 精靈戰鬥服飾, dyed with the valley's plant dyes. Remove the white spider-silk dress and the dew veil from what she makes. Her `social_connection` currently says 瓦爾溫's braided silk goes into her loom: change it to 瓦爾溫's 暗影谷藍染 going into her dye pots. |
| `ciaran_nireth` (`ciaran_homes_b.py`) | Add 暗影谷解毒草露 to what she brews from her own garden, beside the two potions. |

### Decision 6: room prose

`content/maps/interiors/ciaran_valwyn_home.yaml`: the description lists 一綑綑紮起的絲 among her gathered things. Replace that item with cakes of blue dye and jars of crystal sand; change nothing else in the sentence or the file. The other homes' descriptions name no removed good and stay.

### Decision 7: dialogue

Follow `.agents/skills/npc-dialogue-content/SKILL.md` and its `references/scene-schema.md`, and pass its mandatory source gate first. Keep every `topic_id` and `scene_id`. Every scene whose lines change declares `revision: r3`; an untouched scene keeps `r2`. Scenes keep the shape rule: a complete actor utterance first, 3 to 8 lines, at least one host line, possession-safe actor lines, no number for a price or quantity. A merchant names only goods on her own shelf by registry display name, and her 收回-style topic matches the service: she takes back only what her shelf offers. Greetings stay distinct from every other merchant's greeting.

Where a scene tells a guest where a removed good can be found, it names the making village and its maker as a neighbour's fact, never as a refusal: the three branches visit one another now and then (world source, 社會結構).

| File | Topic (keyword today) | Change |
| --- | --- | --- |
| `ciaran_lareneth.yaml` | greeting | Rewrite: she offers a taste of 暗影谷夜綻花釀 instead of candied blossom. |
| | `topic_01` 花饌 | Rewrite: how the night-blooming flowers are gathered after dusk and steeped; names 暗影谷夜綻花釀. |
| | `topic_02` 山產 | Rewrite: the valley's mushrooms and 暗影谷炭烤蕈串; taking back unopened jars. |
| | `topic_03` 茶點 | Rewrite: hospitality by the stream and packing food for the road, with the two local foods. |
| | `topic_04` 口味 | Rewrite only if it names candied blossom or 花蕊; otherwise leave at `r2`. |
| `ciaran_valwyn.yaml` | greeting, `topic_01` 蒐羅 | Rewrite any line that names silk; her gathered things now include dye cakes and crystal sand. |
| | `topic_02` 蛛絲 | Rewrite wholesale. `keyword` and `label` become 藍染. The scene covers 暗影谷藍染: pressed from the plants of the shoal downstream, the blue of the village's cloth. One line says spider silk is 幽月谷村's, kept by 奈拉拉‧弗羅斯特威洛 at 蛛絲林. |
| | `topic_03` 耳環 (and its `familiar_visitor` variant) | Leave unchanged unless a line names silk. |
| | `topic_04` 以物易物 | Rewrite: she trades stories and takes back her own unused dye and crystal sand; names 暗影谷晶砂. |
| `ciaran_vethiel.yaml` | greeting, `topic_01` 織衣 | Rewrite any line that names the white dress or the veil. |
| | `topic_02` 戰衣 | Leave unchanged unless a line names a removed good. |
| | `topic_03` 禮袍 | Rewrite wholesale; keep `keyword` and `label`. The scene covers 精靈短袍傳統服飾 as the dark elves' own dress, worn with the ease about the body the world source describes. One line says the white spider-silk dress is woven in 幽月谷村 and the dew veil in 翠綠森林村 by 伊斯爾林‧斯塔爾威維爾. |
| | `topic_04` 舊衣 | Rewrite any line that names a removed good; she takes back only her own two garments. |
| `ciaran_nireth.yaml` | greeting, `topic_01` 調藥 | Rewrite to name three remedies: 暗影谷解毒草露, 強效治療藥水 and 魔力藥水. |
| | `topic_02` 重傷, `topic_03` 魔力 | Leave unchanged. |
| | `topic_04` 藥草 | Rewrite: the antidote herb grows in her own garden and becomes 暗影谷解毒草露; keep that she uses only her own plants and takes back sealed jars. |

One line outside these four tables also follows the change: `ciaran_gwenaera.yaml` `topic_03` called 瓦爾溫 the silk gatherer. It now calls her the dye-presser and the scene moves to `r3`.

Each of the four files keeps exactly four topics.

### Decision 8: documents

- `docs/lore/items.md`: add one row per new item to the table of its category (食物, 藥劑, 素材), after the last existing row, following that table's columns; 產地／文化 is 暗影谷村（基亞蘭族）; the reference price cell is `—`. In the existing rows, set 產地／文化 to name the making village: `elven_spider_silk` and `elven_traditional_robe` → 幽月谷村（伊歐拉斯族）; `elven_forest_veil` and `elven_candied_blossom` → 翠綠森林村（斐歐恩族）. Change no other cell of those rows.
- `docs/lore/settlement-locations.md`: run `grep -n "蛛絲\|蜜漬\|輕紗\|傳統服飾" docs/lore/settlement-locations.md` and read each hit. Where a sentence presents one of the four goods as something 暗影谷村 makes or sells, correct it to the making village, and where the 暗影谷村 fare or herb host is described, name her local good. Leave sentences about the other villages and about elves in general.
- `docs/development/npc-editorial-review.md`: refresh the `place_host` rows of the four hosts and the `dialogue_table` rows of the four tables: new ISO review date, cells rewritten from what the finished source says. A cell never contains a bare `|`.
- `docs/lore/ciaran-local-goods-review.md` (new, English, in the shape of `docs/lore/ciaran-crafts-dialogue-review.md`): scope; sources read; per host, the card edit and one line per rewritten greeting and scene naming the world-source section it rests on; the room prose edit; every proper noun used and the registry row it resolves to; the lint results. This is the human-reviewed record of tone and fidelity.

Write Traditional Chinese with the `chinese-content-writing-guideline` and `writing-style-guideline` skills.

### Decision 9: regenerated artifact

Run `uv run --locked python -m tools.map_reference_context` after the last edit under `world/lore/`, `world/rules/` or `content/maps/`.

## Risks / Trade-offs

- [A development world keeps stock rows and runtime personas for the removed goods] → Pre-release: reset the database per the reset runbook. No migration is written.
- [A player who bought the four goods in 暗影谷村 can no longer sell them back there] → Intended: a merchant buys back only what her shelf offers, and the making villages buy them.
- [One malformed dialogue file or card rejects the whole snapshot and blocks startup] → Tasks load the registries and the snapshot before any prose review.
- [A test elsewhere pins one of the four goods to a 暗影谷村 shelf] → Planning found none (no spec or test names these item keys). Task 7.4 gives the rule if one appears: rewrite the assertion to its logic, append no key.
