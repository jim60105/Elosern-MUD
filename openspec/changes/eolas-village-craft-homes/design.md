# Design

## Context

See `proposal.md` for motivation. Facts found while planning:

- The village map `content/maps/settlements/elven_village_eolas.yaml` exists with these nodes: `forest_trail` 深林獸徑, `brook_head` 溪源, `proving_ground` 試法坪, `hot_spring` 溫泉浴場, `valley_floor` 谷底空地, `silk_grove` 蛛絲林, `cliff_dwellings` 岩屋坡, `terrace_gardens` 石階菜畦, `kiln_yard` 窯場. Shared interiors exist: 共食棚, 銀羽驛站・幽月谷分站, 圖書館, 儲糧窖. No home or host exists.
- `SETTLEMENT_REGISTRY` already carries `elven_village_eolas`; subrace `eolas` belongs to race `elf`, whose `allowed_sexes` is `female` only.
- A hosted place needs, all at once or startup fails: the interior document whose room ID equals the place key; the `PlaceDefinition` row; an `NpcProfile` whose key is the row's `host_profile_key`; a dialogue file `world/lore/dialogue/content/<profile key>.yaml` for the row's `dialogue_key`; one `place_host` and one `dialogue_table` row in `NPC_SOURCE_INVENTORY`; one entry per source in `docs/development/npc-editorial-review.md`. For a merchant also: an assortment, its offers and a shop-hours row. `docs/development/adding-npcs.md` describes each gate.
- A settlement with shops needs an explicit entry in `price_scales` (`world/rules/guild_config/_commerce.py::validate_price_scales`).
- The eight local items come from `elven-village-local-goods`, which is applied first. `unpin-village-test-data` is applied first too: it removed the test assertions that assumed 暗影谷村 was the only village with hosts.
- An existing test (`test_ciaran_village_commerce.py::test_rarity_is_read_nowhere_in_resolving_village_prices`) requires every good sold both in a village and in the capital to be strictly cheaper in the village. Every figure in Decision 5 satisfies it.
- Reference implementation: 暗影谷村 — `world/lore/settlements/places_ciaran.py`, `world/lore/npc_profiles/ciaran_homes_a.py`, `world/lore/dialogue/content/ciaran_*.yaml`, `content/maps/interiors/ciaran_*_home.yaml`, `world/rules/rulebook/commerce/ciaran.yaml`.

## Goals / Non-Goals

**Goals:**

- 3 homes a player can enter, each with a host who talks and, for 3 of them, trades.
- Content that reads as this world, written from the world source named in Decision 6.

**Non-Goals:**

- No change to the settlement map document, to any existing place, profile, dialogue table or item.
- No schedule, quest, artwork or new capability type.
- No test, and no assertion naming a place, host, item, price or line of this change.

## Decisions

### Decision 1: the hosts

Names were rolled with `.agents/skills/fantasy-name-generator` (elf pack, female pool) and chosen for meaning. Use them exactly.

| Profile key | Name | Original spelling (meaning) | Role | Place key and room name | Opens from node | `age` / `apparent_age` | Shelf |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `eolas_naelara` | 奈拉拉‧弗羅斯特威洛 | Naelara Frostwillow (night mist + grace; frost willow) | 織絲者: keeps the village spiders, reels their silk and weaves the white dress | `eolas_naelara_home` 奈拉拉的家 | `silk_grove` | 610 / 20 | `eolas_silkwork` |
| `eolas_sirelwen` | 希瑞爾溫‧布瑞特瓦特爾 | Sirelwen Brightwater (silver radiance + pure white; bright water) | 試法者: spends her days on the proving ground and carves practice wands | `eolas_sirelwen_home` 希瑞爾溫的家 | `proving_ground` | 720 / 20 | `eolas_wandcraft` |
| `eolas_taelith` | 泰莉斯‧恩貝爾莉夫 | Taelith Emberleaf (sky + faint light; ember leaf) | 窯匠: fires pottery and glass in the shared kiln | `eolas_taelith_home` 泰莉斯的家 | `kiln_yard` | 540 / 20 | `eolas_kilnware` |

All hosts: `host_race="elf"`, `host_subrace="eolas"`, `host_sex="female"`.

### Decision 2: the home interiors

One file per host, exactly this shape, with no `art_key` line. Write `desc_zh` from the Room brief in the register of `content/maps/interiors/ciaran_*_home.yaml`: a lived-in room, no signboard, no shopkeeper wording. Existing tests read every village room: the room name contains neither 店 nor 舖, the prose contains neither 櫃檯 nor 招牌, and the prose contains no ASCII word.

`content/maps/interiors/eolas_naelara_home.yaml` — Room brief: a rock-cut room beside 蛛絲林; reels of silk on pegs, a loom by the door, white cloth folded on a stone shelf.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_naelara_home
rooms:
  eolas_naelara_home:
    name_zh: 奈拉拉的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: silk_grove
  room: eolas_naelara_home
  doorway_key: 奈拉拉的家
  doorway_aliases:
  - naelara
  - naelara's home
```

`content/maps/interiors/eolas_sirelwen_home.yaml` — Room brief: a rock-cut room at the edge of 試法坪; slates of notes on the wall, wand blanks drying on a rack, a scorch mark by the door.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_sirelwen_home
rooms:
  eolas_sirelwen_home:
    name_zh: 希瑞爾溫的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: proving_ground
  room: eolas_sirelwen_home
  doorway_key: 希瑞爾溫的家
  doorway_aliases:
  - sirelwen
  - sirelwen's home
```

`content/maps/interiors/eolas_taelith_home.yaml` — Room brief: a rock-cut room facing 窯場; shelves of bowls and glass, a rack of pendants catching the light, the kiln's warmth through the doorway.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_taelith_home
rooms:
  eolas_taelith_home:
    name_zh: 泰莉斯的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: kiln_yard
  room: eolas_taelith_home
  doorway_key: 泰莉斯的家
  doorway_aliases:
  - taelith
  - taelith's home
```

### Decision 3: place rows

Create `world/lore/settlements/places_eolas.py` with a short module docstring (the village's homes are private dwellings whose hosts share what they make; rows stay alphabetical by key), the same four imports `world/lore/settlements/places_ciaran.py` uses, and:

```python
ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="eolas_naelara_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_naelara_home", "eolas_naelara_home"),
        host_name="奈拉拉‧弗羅斯特威洛",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_naelara",
        assortment_keys=("eolas_silkwork",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_naelara_home"),
                service_id="eolas_naelara",
                shop_key="eolas_naelara_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_naelara_home"),
                dialogue_key="eolas_naelara_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_sirelwen_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_sirelwen_home", "eolas_sirelwen_home"),
        host_name="希瑞爾溫‧布瑞特瓦特爾",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_sirelwen",
        assortment_keys=("eolas_wandcraft",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_sirelwen_home"),
                service_id="eolas_sirelwen",
                shop_key="eolas_sirelwen_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_sirelwen_home"),
                dialogue_key="eolas_sirelwen_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_taelith_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_taelith_home", "eolas_taelith_home"),
        host_name="泰莉斯‧恩貝爾莉夫",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_taelith",
        assortment_keys=("eolas_kilnware",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_taelith_home"),
                service_id="eolas_taelith",
                shop_key="eolas_taelith_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_taelith_home"),
                dialogue_key="eolas_taelith_home",
            ),
        ),
    ),
)
```

In `world/lore/settlements/places.py` add, beside the other slice imports:

```python
from world.lore.settlements.places_eolas import ROWS as EOLAS_ROWS  # noqa: E402
```

and insert `*EOLAS_ROWS,` directly after `*CIARAN_ROWS,` in the `PLACE_REGISTRY` comprehension, before the four courier-station rows. Update the comment above the imports to name the new slice.

### Decision 4: shelves

Add to `ASSORTMENT_REGISTRY` in `world/lore/settlements/assortments.py`, after the last existing entry, verbatim:

```python
        AssortmentDefinition(
            key="eolas_silkwork",
            display_name_zh="幽月絲織",
            allowed_item_kinds=frozenset({ItemKind.MATERIAL, ItemKind.ARMOR}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ARMOR}),
            item_keys=(
                "elven_spider_silk", "elven_traditional_robe",
            ),
        ),
        AssortmentDefinition(
            key="eolas_wandcraft",
            display_name_zh="幽月杖作",
            allowed_item_kinds=frozenset({ItemKind.WEAPON}),
            allowed_equipment_slots=frozenset({EquipmentSlot.WEAPON_MAIN}),
            item_keys=(
                "eolas_proving_wand",
            ),
        ),
        AssortmentDefinition(
            key="eolas_kilnware",
            display_name_zh="幽月窯作",
            allowed_item_kinds=frozenset({ItemKind.ACCESSORY, ItemKind.TOOL}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ACCESSORY}),
            item_keys=(
                "eolas_glass_pendant", "magic_lamp",
            ),
        ),
```

Add one comment above them naming the village and saying each shelf is one villager's home.

### Decision 5: offers, hours and prices

Create `world/rules/rulebook/commerce/eolas.yaml` with a header comment in the style of `world/rules/rulebook/commerce/ciaran.yaml` and exactly:

```yaml
assortments:
  - key: eolas_silkwork
    offers:
      - item_key: elven_spider_silk
        buy_copper: 60
        sell_copper: 30
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: elven_traditional_robe
        buy_copper: 120
        sell_copper: 60
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
  - key: eolas_wandcraft
    offers:
      - item_key: eolas_proving_wand
        buy_copper: 100
        sell_copper: 50
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
  - key: eolas_kilnware
    offers:
      - item_key: eolas_glass_pendant
        buy_copper: 110
        sell_copper: 55
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: magic_lamp
        buy_copper: 40
        sell_copper: 20
        max_stock: 10
        initial_stock: 5
        restock_quantity: 2

shops:
  - shop_key: eolas_naelara_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: eolas_sirelwen_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: eolas_taelith_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
```

Add one line to `price_scales:` in `world/rules/rulebook/commerce/scales.yaml`:

```yaml
  elven_village_eolas: 100
```

The pricing rule is the one 暗影谷村 uses and the user confirmed: goods are local produce, so the village that makes them sells them at everyday figures, whatever the capital charges. Each figure sits inside the item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and every item the capital also sells is cheaper here.

| Shelf | Item | Buy / sell (copper) | Max / initial / restock | Basis |
| --- | --- | --- | --- | --- |
| `eolas_silkwork` | `elven_spider_silk` | 60 / 30 | 20 / 10 / 5 | capital 60000; same figure as 暗影谷村 |
| `eolas_silkwork` | `elven_traditional_robe` | 120 / 60 | 3 / 1 / 1 | same figure as 暗影谷村 |
| `eolas_wandcraft` | `eolas_proving_wand` | 100 / 50 | 3 / 1 / 1 | new local item; same figure as 暗影鋼刀 in 暗影谷村 |
| `eolas_kilnware` | `eolas_glass_pendant` | 110 / 55 | 3 / 1 / 1 | new local item; jewelry band floor is 100 |
| `eolas_kilnware` | `magic_lamp` | 40 / 20 | 10 / 5 / 2 | capital 60; the glass is blown here |

Shop hours match 暗影谷村: open 7, close 19, restock 6.

### Decision 6: profiles

Create `world/lore/npc_profiles/eolas_homes_a.py` in the shape of `world/lore/npc_profiles/ciaran_homes_a.py`: a module docstring, the same imports, and `ROWS: tuple[NpcProfile, ...]` with one `NpcProfile` per host in the order of the Decision 1 table. In `world/lore/npc_profiles/__init__.py` add the import `from world.lore.npc_profiles.eolas_homes_a import ROWS as EOLAS_HOMES_A_ROWS  # noqa: E402`, append `("eolas_homes_a", EOLAS_HOMES_A_ROWS),` as the last entry of `PROFILE_SLICES`, add `"EOLAS_HOMES_A_ROWS"` to `__all__`, and add the label to the order named in the module docstring.

World source, mandatory: read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (`tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path), sections 種族設定 › 精靈族, 社會與文化 and 特殊設定, before writing, and write every card from it. All elves are women. About 300 exist and the three nations rank them above royalty. They have no fixed trades, no marriage and no schooling; ability comes from lifespan. A host shares what she loves making and takes coin because the village wants guests looked after, so no card speaks of a shop, stock or business. Eolas look, from the world source: appearance fixed at twenty years, 135-145 cm, varied hair and eye colours. Every host is centuries old and speaks with an adult's knowledge and an elder's patience. The village is defined by magic study in all elements, by what its people have read and written, and by a valley that feeds and clothes itself: write each host through her craft, her experiments and her daily work. Dress is the village's own white spider-silk cloth.

Eolas feel no shame about the bare body or about being seen (world source 生活方式 › 性文化 and 社會與文化 › 倫理觀; `docs/lore/overview.md` 性愛與身體; `docs/lore/settlement-locations.md` 〈公共浴場〉聚落差異 puts all three villages at open pools with no partitions and no attendant, and keeps that contrast as the hook for stories). Write every host with that ease: it sits in how she dresses, how she sits and how she speaks of what she makes, at the frankness of `world/lore/dialogue/content/ciaran_vethiel.yaml` topic_03 (「身軀原本就值得坦然展現，因此織得極薄透光」). The ease stays in bearing, dress and everyday talk: no scene stages a sexual act, and no line remarks on the guest's body. The Eolas look twenty and are centuries old; the prose never uses that gap for sexual content.

Each card fills the seven fields of `NpcCard` from the brief below, in Traditional Chinese, within the card limits (leaf 600, identity section 600, whole card 2000 code points). The brief fixes the facts; the sentences are yours. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and the two writing-guideline skills.

**`eolas_naelara` 奈拉拉‧弗羅斯特威洛** — `age=610`, `apparent_age=10`

- public: the village's silk keeper, living at the edge of 蛛絲林; reels silk and weaves the white cloth everyone wears; a visitor may take a bundle or a dress for coin
- appearance: Eolas look; pale silver hair tied back so it never touches a web; fine silk threads caught on her sleeves; walks without a sound
- personality: patient, exact, quietly proud of unbroken thread; dislikes sudden noise because the spiders do
- speech_style: soft and slow, short sentences, lowers her voice near the grove; calls the listener 你
- life_story: has kept the grove for centuries, since the keeper before her turned to other studies; knows each web by its tree
- habit: counts the webs at dawn and hums one low note so the spiders know her
- social_connection: 泰莉斯‧恩貝爾莉夫 fires the glass weights that hang from her loom
- `identity.hidden`: leave empty.
- `voice.misunderstood`: quiet; asks whether the visitor came for silk or the white dress. `voice.greeting` stays `None`.

**`eolas_sirelwen` 希瑞爾溫‧布瑞特瓦特爾** — `age=720`, `apparent_age=10`

- public: the villager most often found on 試法坪; tries spells of every element and writes down what happened; carves short wands and lets a visitor take one for coin
- appearance: Eolas look; dark hair cut short after one fire too many; ink on her fingers; a scorched hem she has not noticed
- personality: curious, blunt, delighted by a failed spell because it teaches more; forgets meals
- speech_style: fast, precise, corrects herself mid-sentence; answers a question with a better question; calls the listener 你
- life_story: has filled shelves of the village library with her notes over seven centuries; carves a wand for each element she is studying
- habit: writes the result on a slate before the smoke clears
- social_connection: borrows the heat of 泰莉斯‧恩貝爾莉夫's kiln to test her fire spells
- `identity.hidden`: leave empty.
- `voice.misunderstood`: brisk; asks whether the visitor wants a wand or wants to watch. `voice.greeting` stays `None`.

**`eolas_taelith` 泰莉斯‧恩貝爾莉夫** — `age=540`, `apparent_age=10`

- public: the one who tends the shared kiln at 窯場; fires bowls, glass and lamp globes; visitors may take a glass pendant or a lamp for coin
- appearance: Eolas look; copper-red hair under a soot-marked cloth; forearms dusted with ash; a glass drop of her own making at her throat
- personality: cheerful, restless, judges everything by how it took the fire; breaks a flawed piece without regret
- speech_style: quick and bright, talks with her hands, uses 喔 and 啦; calls the listener 你
- life_story: spent decades testing which fire spell holds an even heat before she trusted the kiln to it; the village's bowls are hers
- habit: taps each cooled piece with a fingernail and listens to the ring
- social_connection: trades glass loom weights to 奈拉拉‧弗羅斯特威洛 for silk to wrap her finished pieces
- `identity.hidden`: leave empty.
- `voice.misunderstood`: bright; asks whether it is about the glass or the lamps. `voice.greeting` stays `None`.

### Decision 7: dialogue tables

One file per host. The filename stem is the profile key; the file declares no owner field. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and its `references/scene-schema.md` for the schema and the prose standard, and pass its mandatory source gate first.

- `schema_version: 1`, a `greeting`, and exactly the four topics listed for the host.
- Scene ID is the topic ID plus `_scene`; every scene declares `revision: r1`.
- Every formal scene starts with a complete actor utterance, holds 3 to 8 lines and has at least one host line. Actor lines stay true when a possessed companion speaks them.
- A topic marked "pure_chain successor" declares `predecessors` with the named topic's ID and `disclosure: pure_chain`, and no `requires`. Every other topic is open: no `requires`, no `unavailable`.
- A merchant's scenes name only goods on her own shelf, by registry display name, and state no number: no price, no quantity. The 收回 topic matches the service: a merchant buys back only what her shelf offers.
- Name only places that exist: the village's nodes and shared interiors listed in Context, and the hosts of this village named in the Decision 1 table of this change or an earlier applied one.
- Speak as a villager sharing what she makes. Elves need nothing from outsiders and are neither servants nor curiosities.
- The body ease of Decision 6 rides in the greeting and in the 白衣 scene; it never becomes a sexual scene.
- An existing test reads every village table and rejects proprietor vocabulary. No greeting or line contains any of: 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門, 打烊. Say the world-side thing instead: the door is never shut, the shelf is what she finished this season.

**`world/lore/dialogue/content/eolas_naelara.yaml`** — topic ID prefix `eolas_naelara_home`. Greeting: pauses the reel, asks the guest to step softly, offers to show the silk and the white dress.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_naelara_home.topic_01` | 養蛛 | how the spiders are kept: quiet steps, a season lost when a web tears |
| `eolas_naelara_home.topic_02` | 蛛絲 | what a bundle of 精靈蛛絲 is for and why it is plentiful here |
| `eolas_naelara_home.topic_03` | 白衣 | 精靈傳統服飾 as the village's everyday white cloth, woven from this grove and worn thin on purpose: a body is worth showing plainly, and a guest who finds it too sheer is the one out of place |
| `eolas_naelara_home.topic_04` | 收回 | takes back her own unused silk and dresses; declines cloth from outside |

**`world/lore/dialogue/content/eolas_sirelwen.yaml`** — topic ID prefix `eolas_sirelwen_home`. Greeting: looks up from a slate, asks which element the guest favours, and points to the wands on the rack.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_sirelwen_home.topic_01` | 試法 | what happens on 試法坪 and why it sits far from the dwellings |
| `eolas_sirelwen_home.topic_02` | 短杖 | 幽月試法短杖: what it is carved from and what it does for a caster |
| `eolas_sirelwen_home.topic_03` | 元素 | the Eolas affinity for every element, told through her own experiments |
| `eolas_sirelwen_home.topic_04` | 收回 | takes back her own undamaged wands; declines staves from outside |

**`world/lore/dialogue/content/eolas_taelith.yaml`** — topic ID prefix `eolas_taelith_home`. Greeting: wipes ash from her hands and holds a fresh glass drop to the light for the guest to see.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_taelith_home.topic_01` | 窯火 | how the shared kiln is fired and what the village makes in it |
| `eolas_taelith_home.topic_02` | 琉璃墜 | 幽月琉璃墜: a glass drop that steadies casting; why she wears one |
| `eolas_taelith_home.topic_03` | 魔法燈 | 魔法燈: the globes are blown here, useful in the deep forest beyond the trail |
| `eolas_taelith_home.topic_04` | 收回 | takes back her own unbroken glass and lamps; declines outside wares |

### Decision 8: inventory and ledger

Add to `NPC_SOURCE_INVENTORY` in `world/lore/npc_profiles/inventory.py`, before the `# companions` block, under a comment naming the slice:

```python
    NpcSource("place_host", "eolas_naelara", "eolas_homes_a"),
    NpcSource("place_host", "eolas_sirelwen", "eolas_homes_a"),
    NpcSource("place_host", "eolas_taelith", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_naelara_home", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_sirelwen_home", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_taelith_home", "eolas_homes_a"),
```

In `docs/development/npc-editorial-review.md` add one `place_host` row per host under a new heading `## eolas_homes_a hosts`, and one `dialogue_table` row per table under a new heading `## eolas_homes_a dialogue tables`. Copy the column shape of the 暗影谷村 rows exactly (kind, key, ISO review date, one cell per face, disposition). Write each cell from what you actually read in the finished source; a cell never contains a bare `|`.

### Decision 9: tests

Two tests list the place slice modules. Add the new module to each; add no assertion that names a place, host or item of this change. The data pins these suites used to carry were removed by `unpin-village-test-data`.

- `world/lore/tests/test_settlements.py`, the slice-order case (it imports `ROWS` from each `places_*` module and compares the concatenation with the head of `PLACE_REGISTRY`): add `from world.lore.settlements.places_eolas import ROWS as eolas_rows` and append `*eolas_rows` to the concatenation, after the existing slices. Change nothing else.
- `tests/test_map_runtime_contract.py`, the `_modules(...)` call that lists the place slice files: add `"world/lore/settlements/places_eolas.py",` to the list.

One tool lists them too. In `tools/map_reference_context.py::_find_place_source_file`, add `places_eolas` to the import tuple and `(places_eolas, "world/lore/settlements/places_eolas.py"),` to `module_map`, after the last existing entry, so regenerated references cite the right file.

### Decision 10: review document

Create `docs/lore/eolas-craft-homes-review.md` in English, in the shape of `docs/lore/ciaran-crafts-dialogue-review.md`: scope; sources read; per host, the card and voice review, the room prose review, and one line per greeting and scene naming the world-source section it rests on; the list of every proper noun used and the registry row it resolves to; the lint results. This is the human-reviewed record of tone and fidelity.

No lore document edit in this change. The village's case description is revised by the village's second change, once all its hosts exist.

### Decision 11: regenerated artifact

`content/map-reference-context.json` lists interiors. Regenerate it with `uv run --locked python -m tools.map_reference_context` after the last interior edit.

## Risks / Trade-offs

- [A village price far below the capital's lets a player carry goods out and resell] → This is the accepted 暗影谷村 behaviour: the villages are hidden and the gap is the point of the lore. No new rule is added.
- [One malformed dialogue file or card rejects the whole snapshot and blocks startup] → Tasks load the snapshot and the registries before any prose review.
- [A test elsewhere pins a roster this change grows] → Task 8.5 gives the rule: rewrite the assertion to its logic, append no key.
