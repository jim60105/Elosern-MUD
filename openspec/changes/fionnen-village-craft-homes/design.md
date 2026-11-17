# Design

## Context

See `proposal.md` for motivation. Facts found while planning:

- The village map `content/maps/settlements/elven_village_fionnen.yaml` exists with these nodes: `leaf_veiled_path` 葉隱小徑, `light_court` 林間光庭, `archery_lane` 靶道, `blossom_garden` 花蕊蜜園, `forest_brook` 林溪, `bathing_pool` 林泉浴場, `forest_plots` 林間菜圃, `craft_glade` 木作空地, `root_dwellings` 樹根屋, `canopy_walk` 樹冠吊橋, `lookout_bough` 瞭望枝. Shared interiors exist: 共食棚, 銀羽驛站・翠綠森林分站, 蜜漬房, 弓棚. No home or host exists.
- `SETTLEMENT_REGISTRY` already carries `elven_village_fionnen`; subrace `fionnen` belongs to race `elf`, whose `allowed_sexes` is `female` only.
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
| `fionnen_corith` | 科瑞斯‧蒙希斯佩爾 | Corith Moonwhisper (woodland + faint light; moon whisper) | 巧作者: carves bracers, tunes pleasure crystals and raises vines | `fionnen_corith_home` 科瑞斯的家 | `root_dwellings` | 430 / 24 | `fionnen_trinkets` |
| `fionnen_gwynnel` | 格威內爾‧斯威夫塔羅 | Gwynnel Swiftarrow (pure white + brookside; swift arrow) | 弓匠: makes the village's longbows on the shared woodworking ground | `fionnen_gwynnel_home` 格威內爾的家 | `craft_glade` | 560 / 27 | `fionnen_bowcraft` |
| `fionnen_ithrlin` | 伊斯爾林‧斯塔爾威維爾 | Ithrlin Starweaver (moonlight + song; star weaver) | 織衣者: weaves hunting dress, dew veils and the white traditional dress | `fionnen_ithrlin_home` 伊斯爾林的家 | `canopy_walk` | 470 / 31 | `fionnen_attire` |

All hosts: `host_race="elf"`, `host_subrace="fionnen"`, `host_sex="female"`.

### Decision 2: the home interiors

One file per host, exactly this shape, with no `art_key` line. Write `desc_zh` from the Room brief in the register of `content/maps/interiors/ciaran_*_home.yaml`: a lived-in room, no signboard, no shopkeeper wording. Existing tests read every village room: the room name contains neither 店 nor 舖, the prose contains neither 櫃檯 nor 招牌, and the prose contains no ASCII word.

`content/maps/interiors/fionnen_corith_home.yaml` — Room brief: a room between buttress roots in 樹根屋; a carving bench, crystals on a cloth, potted vines stirring along the wall.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_corith_home
rooms:
  fionnen_corith_home:
    name_zh: 科瑞斯的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: root_dwellings
  room: fionnen_corith_home
  doorway_key: 科瑞斯的家
  doorway_aliases:
  - corith
  - corith's home
```

`content/maps/interiors/fionnen_gwynnel_home.yaml` — Room brief: a room between buttress roots beside 木作空地; staves seasoning in the rafters, a shaving horse, unstrung bows on pegs.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_gwynnel_home
rooms:
  fionnen_gwynnel_home:
    name_zh: 格威內爾的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: craft_glade
  room: fionnen_gwynnel_home
  doorway_key: 格威內爾的家
  doorway_aliases:
  - gwynnel
  - gwynnel's home
```

`content/maps/interiors/fionnen_ithrlin_home.yaml` — Room brief: a canopy platform room on 樹冠吊橋; a loom in the light, veils hung to catch the wind, hunting dress folded on a chest.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_ithrlin_home
rooms:
  fionnen_ithrlin_home:
    name_zh: 伊斯爾林的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: canopy_walk
  room: fionnen_ithrlin_home
  doorway_key: 伊斯爾林的家
  doorway_aliases:
  - ithrlin
  - ithrlin's home
```

### Decision 3: place rows

Create `world/lore/settlements/places_fionnen.py` with a short module docstring (the village's homes are private dwellings whose hosts share what they make; rows stay alphabetical by key), the same four imports `world/lore/settlements/places_ciaran.py` uses, and:

```python
ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="fionnen_corith_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_corith_home", "fionnen_corith_home"),
        host_name="科瑞斯‧蒙希斯佩爾",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_corith",
        assortment_keys=("fionnen_trinkets",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_corith_home"),
                service_id="fionnen_corith",
                shop_key="fionnen_corith_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_corith_home"),
                dialogue_key="fionnen_corith_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_gwynnel_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_gwynnel_home", "fionnen_gwynnel_home"),
        host_name="格威內爾‧斯威夫塔羅",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_gwynnel",
        assortment_keys=("fionnen_bowcraft",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_gwynnel_home"),
                service_id="fionnen_gwynnel",
                shop_key="fionnen_gwynnel_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_gwynnel_home"),
                dialogue_key="fionnen_gwynnel_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_ithrlin_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_ithrlin_home", "fionnen_ithrlin_home"),
        host_name="伊斯爾林‧斯塔爾威維爾",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_ithrlin",
        assortment_keys=("fionnen_attire",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_ithrlin_home"),
                service_id="fionnen_ithrlin",
                shop_key="fionnen_ithrlin_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_ithrlin_home"),
                dialogue_key="fionnen_ithrlin_home",
            ),
        ),
    ),
)
```

In `world/lore/settlements/places.py` add, beside the other slice imports:

```python
from world.lore.settlements.places_fionnen import ROWS as FIONNEN_ROWS  # noqa: E402
```

and insert `*FIONNEN_ROWS,` directly after `*EOLAS_ROWS,` in the `PLACE_REGISTRY` comprehension, before the four courier-station rows. Update the comment above the imports to name the new slice.

### Decision 4: shelves

Add to `ASSORTMENT_REGISTRY` in `world/lore/settlements/assortments.py`, after the last existing entry, verbatim:

```python
        AssortmentDefinition(
            key="fionnen_trinkets",
            display_name_zh="森林巧作",
            allowed_item_kinds=frozenset({ItemKind.ACCESSORY, ItemKind.TOY}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ACCESSORY}),
            item_keys=(
                "fionnen_archer_bracer", "tremor_crystal", "embracing_vine",
            ),
        ),
        AssortmentDefinition(
            key="fionnen_bowcraft",
            display_name_zh="森林弓藝",
            allowed_item_kinds=frozenset({ItemKind.WEAPON}),
            allowed_equipment_slots=frozenset({EquipmentSlot.WEAPON_MAIN}),
            item_keys=(
                "elven_longbow",
            ),
        ),
        AssortmentDefinition(
            key="fionnen_attire",
            display_name_zh="森林衣飾",
            allowed_item_kinds=frozenset({ItemKind.ARMOR}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ARMOR}),
            item_keys=(
                "fionnen_leafweave_garb", "elven_forest_veil", "elven_traditional_robe",
            ),
        ),
```

Add one comment above them naming the village and saying each shelf is one villager's home.

### Decision 5: offers, hours and prices

Create `world/rules/rulebook/commerce/fionnen.yaml` with a header comment in the style of `world/rules/rulebook/commerce/ciaran.yaml` and exactly:

```yaml
assortments:
  - key: fionnen_trinkets
    offers:
      - item_key: fionnen_archer_bracer
        buy_copper: 110
        sell_copper: 55
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: tremor_crystal
        buy_copper: 150
        sell_copper: 75
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: embracing_vine
        buy_copper: 60
        sell_copper: 30
        max_stock: 5
        initial_stock: 2
        restock_quantity: 1
  - key: fionnen_bowcraft
    offers:
      - item_key: elven_longbow
        buy_copper: 100
        sell_copper: 50
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
  - key: fionnen_attire
    offers:
      - item_key: fionnen_leafweave_garb
        buy_copper: 100
        sell_copper: 50
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: elven_forest_veil
        buy_copper: 150
        sell_copper: 75
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
      - item_key: elven_traditional_robe
        buy_copper: 120
        sell_copper: 60
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1

shops:
  - shop_key: fionnen_corith_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: fionnen_gwynnel_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: fionnen_ithrlin_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
```

Add one line to `price_scales:` in `world/rules/rulebook/commerce/scales.yaml`:

```yaml
  elven_village_fionnen: 100
```

The pricing rule is the one 暗影谷村 uses and the user confirmed: goods are local produce, so the village that makes them sells them at everyday figures, whatever the capital charges. Each figure sits inside the item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and every item the capital also sells is cheaper here.

| Shelf | Item | Buy / sell (copper) | Max / initial / restock | Basis |
| --- | --- | --- | --- | --- |
| `fionnen_trinkets` | `fionnen_archer_bracer` | 110 / 55 | 3 / 1 / 1 | new local item; jewelry band floor is 100 |
| `fionnen_trinkets` | `tremor_crystal` | 150 / 75 | 3 / 1 / 1 | capital 15000; elven work, made here |
| `fionnen_trinkets` | `embracing_vine` | 60 / 30 | 5 / 2 / 1 | capital 600; raised here |
| `fionnen_bowcraft` | `elven_longbow` | 100 / 50 | 3 / 1 / 1 | sold nowhere else; mundane_weapon band floor is 100 |
| `fionnen_attire` | `fionnen_leafweave_garb` | 100 / 50 | 3 / 1 / 1 | new local item; same figure as the battle dress in 暗影谷村 |
| `fionnen_attire` | `elven_forest_veil` | 150 / 75 | 3 / 1 / 1 | same figure as 暗影谷村 |
| `fionnen_attire` | `elven_traditional_robe` | 120 / 60 | 3 / 1 / 1 | same figure as 暗影谷村 |

Shop hours match 暗影谷村: open 7, close 19, restock 6.

### Decision 6: profiles

Create `world/lore/npc_profiles/fionnen_homes_a.py` in the shape of `world/lore/npc_profiles/ciaran_homes_a.py`: a module docstring, the same imports, and `ROWS: tuple[NpcProfile, ...]` with one `NpcProfile` per host in the order of the Decision 1 table. In `world/lore/npc_profiles/__init__.py` add the import `from world.lore.npc_profiles.fionnen_homes_a import ROWS as FIONNEN_HOMES_A_ROWS  # noqa: E402`, append `("fionnen_homes_a", FIONNEN_HOMES_A_ROWS),` as the last entry of `PROFILE_SLICES`, add `"FIONNEN_HOMES_A_ROWS"` to `__all__`, and add the label to the order named in the module docstring.

World source, mandatory: read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (`tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path), sections 種族設定 › 精靈族, 社會與文化 and 特殊設定, before writing, and write every card from it. All elves are women. About 300 exist and the three nations rank them above royalty. They have no fixed trades, no marriage and no schooling; ability comes from lifespan. A host shares what she loves making and takes coin because the village wants guests looked after, so no card speaks of a shop, stock or business. Fionnen look, from the world source: fair skin, mostly blonde hair and blue or green eyes, 160-180 cm. The village is defined by archery, light magic, bees and woodwork. Elves treat sex and the bare body as naturally as breathing and feel no shame about either (world source, 性文化 and 倫理觀); write every host with that ease. It shows in how she dresses, sits and speaks of her own goods, at the frankness of the accepted reference `world/lore/dialogue/content/ciaran_vethiel.yaml`.

Each card fills the seven fields of `NpcCard` from the brief below, in Traditional Chinese, within the card limits (leaf 600, identity section 600, whole card 2000 code points). The brief fixes the facts; the sentences are yours. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and the two writing-guideline skills.

**`fionnen_corith` 科瑞斯‧蒙希斯佩爾** — `age=430`, `apparent_age=24`

- public: a villager who loves small clever things, living in 樹根屋; carves archer's bracers, tunes 恆振晶 and raises 纏枝魔藤 in pots; makes them for her own pleasure and the village's, and lets a visitor take one for coin
- appearance: Fionnen look; short tousled blonde hair; a loose wrap worn open; a tuned crystal on a cord between her breasts; green stains on her fingers from the vines
- personality: playful, frank, endlessly inventive about pleasure; tries every piece on herself first and says how it went
- speech_style: lively and direct, laughs easily, uses 嘛 and 啦; describes what a piece does to the body in plain words; calls the listener 你
- life_story: a long life of making things that feel good; her crystals are the ones human scholars cannot read; half the village keeps one of her vines
- habit: wears whatever she finished last for a full day before she lets it go
- social_connection: trades shuttles for veils with 伊斯爾林‧斯塔爾威維爾, and tests new pieces with her
- `identity.hidden`: leave empty.
- `voice.misunderstood`: amused; asks whether it is about the bracers, the crystals or the vines. `voice.greeting` stays `None`.

**`fionnen_gwynnel` 格威內爾‧斯威夫塔羅** — `age=560`, `apparent_age=27`

- public: the village's bow maker, living beside 木作空地; shapes longbows for anyone in the village who wants one, and a visitor may take one for coin
- appearance: Fionnen look; tall, blonde hair in one long braid; wood shavings on her bare shoulders; a draw-hand calloused at two fingers
- personality: steady, exacting, measures a person's arm with her eyes; little patience for a bow left strung
- speech_style: plain and brief, craft words, few particles; calls the listener 你
- life_story: has made bows since before the canopy walk went up; each stave seasons until it is ready; most bows in 弓棚 are hers
- habit: sights down every stave against the light before the first cut
- social_connection: 科瑞斯‧蒙希斯佩爾 carves the grips and nocks of her bows
- `identity.hidden`: leave empty.
- `voice.misunderstood`: brief; asks whether it is about a bow. `voice.greeting` stays `None`.

**`fionnen_ithrlin` 伊斯爾林‧斯塔爾威維爾** — `age=470`, `apparent_age=31`

- public: the village's weaver, living on a platform of 樹冠吊橋; weaves hunting dress, the dew veil and the white dress, for villagers freely and for visitors for coin
- appearance: Fionnen look; pale gold hair loose to the hips; wears her own sheer veil and nothing under it; thread wound round two fingers
- personality: gentle, sensual, unembarrassed; chooses cloth by how it feels on skin; teases a guest who looks away
- speech_style: soft, unhurried, uses 呢 and 喔; invites the listener to touch the cloth; calls the listener 你
- life_story: has woven in the canopy since the first platform went up; gathers dew thread at dawn; dressed most of the village and undressed a good part of it
- habit: holds new cloth against her own body before she lets anyone wear it
- social_connection: 科瑞斯‧蒙希斯佩爾 carves her loom shuttles and is paid in veils
- `identity.hidden`: leave empty.
- `voice.misunderstood`: soft; asks whether it is about clothes or about weaving. `voice.greeting` stays `None`.

### Decision 7: dialogue tables

One file per host. The filename stem is the profile key; the file declares no owner field. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and its `references/scene-schema.md` for the schema and the prose standard, and pass its mandatory source gate first.

- `schema_version: 1`, a `greeting`, and exactly the four topics listed for the host.
- Scene ID is the topic ID plus `_scene`; every scene declares `revision: r1`.
- Every formal scene starts with a complete actor utterance, holds 3 to 8 lines and has at least one host line. Actor lines stay true when a possessed companion speaks them.
- A topic marked "pure_chain successor" declares `predecessors` with the named topic's ID and `disclosure: pure_chain`, and no `requires`. Every other topic is open: no `requires`, no `unavailable`.
- A merchant's scenes name only goods on her own shelf, by registry display name, and state no number: no price, no quantity. The 收回 topic matches the service: a merchant buys back only what her shelf offers.
- Name only places that exist: the village's nodes and shared interiors listed in Context, and the hosts of this village named in the Decision 1 table of this change or an earlier applied one.
- Speak as a villager sharing what she makes. Elves need nothing from outsiders and are neither servants nor curiosities.
- No age is stated in player-facing prose: no greeting, scene line, narration or card carries a figure in 歲, an apparent age, or a count of years. The host's long life shows only in what she remembers and how she speaks.
- An existing test reads every village table and rejects proprietor vocabulary. No greeting or line contains any of: 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門, 打烊. Say the world-side thing instead: the door is never shut, the shelf is what she finished this season.

**`world/lore/dialogue/content/fionnen_corith.yaml`** — topic ID prefix `fionnen_corith_home`. Greeting: looks up from a crystal she is tuning against her own skin and asks which kind of toy the guest came for.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_corith_home.topic_01` | 護腕 | 森林射手護腕: carved for the bow arm |
| `fionnen_corith_home.topic_02` | 恆振晶 | 恆振晶: how she tunes it and what it does to the wearer, from her own use; follow its row in `docs/lore/items.md` 性玩具 |
| `fionnen_corith_home.topic_03` | 魔藤 | 纏枝魔藤: how it is raised, watered and woken, and what it does; follow its row in `docs/lore/items.md` 性玩具 |
| `fionnen_corith_home.topic_04` | 收回 | takes back her own pieces; declines things made elsewhere |

**`world/lore/dialogue/content/fionnen_gwynnel.yaml`** — topic ID prefix `fionnen_gwynnel_home`. Greeting: sets down the drawknife, looks at the guest's arms, and takes an unstrung bow from its peg.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_gwynnel_home.topic_01` | 製弓 | how a stave is chosen, seasoned and shaped |
| `fionnen_gwynnel_home.topic_02` | 長弓 | 精靈長弓: what it asks of the archer and what it gives |
| `fionnen_gwynnel_home.topic_03` | 弓棚 | the shared 弓棚 by 靶道: villagers take what they need; a guest exchanges coin here |
| `fionnen_gwynnel_home.topic_04` | 收回 | takes back her own undamaged bows; declines bows made elsewhere |

**`world/lore/dialogue/content/fionnen_ithrlin.yaml`** — topic ID prefix `fionnen_ithrlin_home`. Greeting: lets the shuttle rest, turns in her sheer veil without a thought, and asks what the guest likes against the skin.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_ithrlin_home.topic_01` | 獵衣 | 森林葉織獵衣: woven for moving through the giant trees |
| `fionnen_ithrlin_home.topic_02` | 輕紗 | 精靈森林輕紗: dew thread gathered at dawn, in season |
| `fionnen_ithrlin_home.topic_03` | 白衣 | 精靈傳統服飾 and the elven ease with the bare body, told as her own everyday fact |
| `fionnen_ithrlin_home.topic_04` | 收回 | takes back her own garments to unpick the thread; declines outside clothing |

### Decision 8: inventory and ledger

Add to `NPC_SOURCE_INVENTORY` in `world/lore/npc_profiles/inventory.py`, before the `# companions` block, under a comment naming the slice:

```python
    NpcSource("place_host", "fionnen_corith", "fionnen_homes_a"),
    NpcSource("place_host", "fionnen_gwynnel", "fionnen_homes_a"),
    NpcSource("place_host", "fionnen_ithrlin", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_corith_home", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_gwynnel_home", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_ithrlin_home", "fionnen_homes_a"),
```

In `docs/development/npc-editorial-review.md` add one `place_host` row per host under a new heading `## fionnen_homes_a hosts`, and one `dialogue_table` row per table under a new heading `## fionnen_homes_a dialogue tables`. Copy the column shape of the 暗影谷村 rows exactly (kind, key, ISO review date, one cell per face, disposition). Write each cell from what you actually read in the finished source; a cell never contains a bare `|`.

### Decision 9: tests

Two tests list the place slice modules. Add the new module to each; add no assertion that names a place, host or item of this change. The data pins these suites used to carry were removed by `unpin-village-test-data`.

- `world/lore/tests/test_settlements.py`, the slice-order case (it imports `ROWS` from each `places_*` module and compares the concatenation with the head of `PLACE_REGISTRY`): add `from world.lore.settlements.places_fionnen import ROWS as fionnen_rows` and append `*fionnen_rows` to the concatenation, after the existing slices. Change nothing else.
- `tests/test_map_runtime_contract.py`, the `_modules(...)` call that lists the place slice files: add `"world/lore/settlements/places_fionnen.py",` to the list.

One tool lists them too. In `tools/map_reference_context.py::_find_place_source_file`, add `places_fionnen` to the import tuple and `(places_fionnen, "world/lore/settlements/places_fionnen.py"),` to `module_map`, after the last existing entry, so regenerated references cite the right file.

### Decision 10: review document

Create `docs/lore/fionnen-craft-homes-review.md` in English, in the shape of `docs/lore/ciaran-crafts-dialogue-review.md`: scope; sources read; per host, the card and voice review, the room prose review, and one line per greeting and scene naming the world-source section it rests on; the list of every proper noun used and the registry row it resolves to; the lint results. This is the human-reviewed record of tone and fidelity.

No lore document edit in this change. The village's case description is revised by the village's second change, once all its hosts exist.

### Decision 11: regenerated artifact

`content/map-reference-context.json` lists interiors. Regenerate it with `uv run --locked python -m tools.map_reference_context` after the last interior edit.

## Risks / Trade-offs

- [A village price far below the capital's lets a player carry goods out and resell] → This is the accepted 暗影谷村 behaviour: the villages are hidden and the gap is the point of the lore. No new rule is added.
- [One malformed dialogue file or card rejects the whole snapshot and blocks startup] → Tasks load the snapshot and the registries before any prose review.
- [A test elsewhere pins a roster this change grows] → Task 8.5 gives the rule: rewrite the assertion to its logic, append no key.
