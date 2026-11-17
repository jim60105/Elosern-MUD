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

- 3 homes a player can enter, each with a host who talks and, for 2 of them, trades.
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
| `eolas_nirnel` | 妮爾內爾‧德米多 | Nirnel Dewmeadow (clear spring + brookside; dew meadow) | 調藥者: grows herbs on the terraces and steeps tonics and potions | `eolas_nirnel_home` 妮爾內爾的家 | `terrace_gardens` | 660 / 10 | `eolas_remedies` |
| `eolas_raellin` | 雷林‧莉特弗特 | Raellin Lightfoot (morning dew + song; light foot) | 烤餅好手: bakes bean flatbread and cooks for the road | `eolas_raellin_home` 雷林的家 | `cliff_dwellings` | 380 / 10 | `eolas_fare` |
| `eolas_saelnel` | 賽爾內爾‧妮格汀加勒 | Saelnel Nightingale (spring of wisdom + brookside; nightingale) | 長老: the village elder; remembers and converses, trades nothing | `eolas_saelnel_home` 賽爾內爾的家 | `cliff_dwellings` | 1040 / 10 | none (dialogue only) |

All hosts: `host_race="elf"`, `host_subrace="eolas"`, `host_sex="female"`.

### Decision 2: the home interiors

One file per host, exactly this shape, with no `art_key` line. Write `desc_zh` from the Room brief in the register of `content/maps/interiors/ciaran_*_home.yaml`: a lived-in room, no signboard, no shopkeeper wording. Existing tests read every village room: the room name contains neither 店 nor 舖, the prose contains neither 櫃檯 nor 招牌, and the prose contains no ASCII word.

`content/maps/interiors/eolas_nirnel_home.yaml` — Room brief: a rock-cut room above 石階菜畦; drying herbs overhead, jars sorted by the hour they were picked, a steeping pot kept warm.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_nirnel_home
rooms:
  eolas_nirnel_home:
    name_zh: 妮爾內爾的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: terrace_gardens
  room: eolas_nirnel_home
  doorway_key: 妮爾內爾的家
  doorway_aliases:
  - nirnel
  - nirnel's home
```

`content/maps/interiors/eolas_raellin_home.yaml` — Room brief: a rock-cut room on 岩屋坡; a stone hearth, baskets of beans and roots, flatbread cooling on a board by the window.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_raellin_home
rooms:
  eolas_raellin_home:
    name_zh: 雷林的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: cliff_dwellings
  room: eolas_raellin_home
  doorway_key: 雷林的家
  doorway_aliases:
  - raellin
  - raellin's home
```

`content/maps/interiors/eolas_saelnel_home.yaml` — Room brief: the oldest rock-cut room on 岩屋坡; shelves cut into the wall, a low table of open books, a window toward the valley floor.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: eolas_saelnel_home
rooms:
  eolas_saelnel_home:
    name_zh: 賽爾內爾的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_eolas
  node: cliff_dwellings
  room: eolas_saelnel_home
  doorway_key: 賽爾內爾的家
  doorway_aliases:
  - saelnel
  - saelnel's home
```

### Decision 3: place rows

Insert each of these rows into `ROWS` in `world/lore/settlements/places_eolas.py` at its alphabetical position by `key`, between the existing rows, so the whole tuple stays alphabetical:

```python
    PlaceDefinition(
        key="eolas_nirnel_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_nirnel_home", "eolas_nirnel_home"),
        host_name="妮爾內爾‧德米多",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_nirnel",
        assortment_keys=("eolas_remedies",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_nirnel_home"),
                service_id="eolas_nirnel",
                shop_key="eolas_nirnel_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_nirnel_home"),
                dialogue_key="eolas_nirnel_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_raellin_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_raellin_home", "eolas_raellin_home"),
        host_name="雷林‧莉特弗特",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_raellin",
        assortment_keys=("eolas_fare",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_raellin_home"),
                service_id="eolas_raellin",
                shop_key="eolas_raellin_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_raellin_home"),
                dialogue_key="eolas_raellin_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_saelnel_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_saelnel_home", "eolas_saelnel_home"),
        host_name="賽爾內爾‧妮格汀加勒",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_saelnel",
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_saelnel_home"),
                dialogue_key="eolas_saelnel_home",
            ),
        ),
    ),
```

### Decision 4: shelves

Add to `ASSORTMENT_REGISTRY` in `world/lore/settlements/assortments.py`, after the last existing entry, verbatim:

```python
        AssortmentDefinition(
            key="eolas_remedies",
            display_name_zh="幽月調藥",
            allowed_item_kinds=frozenset({ItemKind.POTION}),
            item_keys=(
                "eolas_herb_tonic", "mana_potion", "greater_healing_potion",
            ),
        ),
        AssortmentDefinition(
            key="eolas_fare",
            display_name_zh="幽月飯食",
            allowed_item_kinds=frozenset({ItemKind.FOOD}),
            item_keys=(
                "eolas_kiln_flatbread", "meal",
            ),
        ),
```

Add one comment above them naming the village and saying each shelf is one villager's home.

### Decision 5: offers, hours and prices

Append to the `assortments:` list of `world/rules/rulebook/commerce/eolas.yaml`:

```yaml
  - key: eolas_remedies
    offers:
      - item_key: eolas_herb_tonic
        buy_copper: 60
        sell_copper: 30
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
      - item_key: mana_potion
        buy_copper: 80
        sell_copper: 40
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
      - item_key: greater_healing_potion
        buy_copper: 150
        sell_copper: 75
        max_stock: 5
        initial_stock: 2
        restock_quantity: 2
  - key: eolas_fare
    offers:
      - item_key: eolas_kiln_flatbread
        buy_copper: 12
        sell_copper: 6
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: meal
        buy_copper: 6
        sell_copper: 3
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
```

and to its `shops:` list:

```yaml
  - shop_key: eolas_nirnel_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: eolas_raellin_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
```

The pricing rule is the one 暗影谷村 uses and the user confirmed: goods are local produce, so the village that makes them sells them at everyday figures, whatever the capital charges. Each figure sits inside the item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and every item the capital also sells is cheaper here.

| Shelf | Item | Buy / sell (copper) | Max / initial / restock | Basis |
| --- | --- | --- | --- | --- |
| `eolas_remedies` | `eolas_herb_tonic` | 60 / 30 | 10 / 5 / 5 | new local item; potion band 50..500 |
| `eolas_remedies` | `mana_potion` | 80 / 40 | 10 / 5 / 5 | capital 120; same figure as 暗影谷村 |
| `eolas_remedies` | `greater_healing_potion` | 150 / 75 | 5 / 2 / 2 | capital 250; same figure as 暗影谷村 |
| `eolas_fare` | `eolas_kiln_flatbread` | 12 / 6 | 20 / 10 / 5 | new local item; specialty_food band 10..100 |
| `eolas_fare` | `meal` | 6 / 3 | 20 / 10 / 5 | capital 10; meal band 5..10 |

Shop hours match 暗影谷村: open 7, close 19, restock 6.

### Decision 6: profiles

Create `world/lore/npc_profiles/eolas_homes_b.py` in the shape of `world/lore/npc_profiles/ciaran_homes_a.py`: a module docstring, the same imports, and `ROWS: tuple[NpcProfile, ...]` with one `NpcProfile` per host in the order of the Decision 1 table. In `world/lore/npc_profiles/__init__.py` add the import `from world.lore.npc_profiles.eolas_homes_b import ROWS as EOLAS_HOMES_B_ROWS  # noqa: E402`, append `("eolas_homes_b", EOLAS_HOMES_B_ROWS),` as the last entry of `PROFILE_SLICES`, add `"EOLAS_HOMES_B_ROWS"` to `__all__`, and add the label to the order named in the module docstring.

World source, mandatory: read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (`tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path), sections 種族設定 › 精靈族, 社會與文化 and 特殊設定, before writing, and write every card from it. All elves are women. About 300 exist and the three nations rank them above royalty. They have no fixed trades, no marriage and no schooling; ability comes from lifespan. A host shares what she loves making and takes coin because the village wants guests looked after, so no card speaks of a shop, stock or business. Eolas look, from the world source: appearance fixed at ten years, 135-145 cm, varied hair and eye colours. Every host is centuries old and speaks with an adult's knowledge and an elder's patience. The village is defined by magic study in all elements, by what its people have read and written, and by a valley that feeds and clothes itself: write each host through her craft, her experiments and her daily work. Dress is the village's own white spider-silk cloth.

Eolas feel no shame about the bare body, about being seen, or about sex (world source 生活方式 › 性文化: 「對裸露、性器官、性行為完全沒有羞恥概念」 and 「視性愛為如同呼吸般自然的生理需求」, with 社會與文化 › 倫理觀; `docs/lore/overview.md` 性愛與身體; `docs/lore/settlement-locations.md` 〈公共浴場〉聚落差異 puts all three villages at open pools with no partitions and no attendant, and keeps that contrast as the hook for stories). The village's days are mostly its own: the world source gives sex about 80% of an elf's time, and the cards and scenes say so outright rather than hinting. Write every host with that ease and that appetite at the frankness of `world/lore/dialogue/content/ciaran_vethiel.yaml` topic_03 (「身軀原本就值得坦然展現，因此織得極薄透光」) and past it wherever her own subject invites it: the herb keeper of what a spent body wants, the baker of feeding a guest before bed and what she expects after, the elder of how the village spends its nights. Explicit wording belongs in the host's own speech, narration and card, in the world's terms, with no OOC vocabulary and no game mechanic. The one hard limit is the scene schema, not the tone: an actor line never grants consent, initiates or agrees to an act, so the frankness rides in what the host says and does, never in a performed scene the player is written into.

Each card fills the seven fields of `NpcCard` from the brief below, in Traditional Chinese, within the card limits (leaf 600, identity section 600, whole card 2000 code points). The brief fixes the facts; the sentences are yours. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and the two writing-guideline skills.

**`eolas_nirnel` 妮爾內爾‧德米多** — `age=660`, `apparent_age=20`

- public: the villager who tends the herb rows of 石階菜畦 and steeps what she grows; keeps tonic, mana potion and strong healing potion for anyone who needs them
- appearance: Eolas look; moss-green hair under a straw hat; soil under her nails; a row of stoppered jars at her belt
- personality: calm, observant, weighs a person's tiredness at a glance; never hurries a steeping
- speech_style: even and gentle, complete sentences, ends advice with 喔; calls the listener 你
- life_story: elves take no illness, so she studied exhaustion instead: of body and of mana; shelves of notes on which herb restores what
- habit: crushes a leaf between her fingers and smells it before she picks the row
- social_connection: 雷林‧莉特弗特 takes her kitchen herbs every morning
- `identity.hidden`: leave empty.
- `voice.misunderstood`: calm; asks whether it is tiredness, mana or a wound. `voice.greeting` stays `None`.

**`eolas_raellin` 雷林‧莉特弗特** — `age=380`, `apparent_age=20`

- public: the villager who loves cooking, living on 岩屋坡; bakes bean flatbread in the shared kiln and packs food for anyone heading up the trail
- appearance: Eolas look; honey-brown hair in two short braids; flour to the elbows; a wooden paddle tucked in her belt
- personality: warm, talkative, feeds people before asking their business; particular about herbs
- speech_style: everyday and lively, uses 喔 and 嘛, short clauses; calls the listener 你
- life_story: learned the bread from whoever baked before her and has changed the herbs again and again since; the shelter eats her bread daily
- habit: breaks the first bread of a batch in half to smell it
- social_connection: picks her herbs from 妮爾內爾‧德米多's terraces
- `identity.hidden`: leave empty.
- `voice.misunderstood`: friendly; offers bread first and asks for the question again. `voice.greeting` stays `None`.

**`eolas_saelnel` 賽爾內爾‧妮格汀加勒** — `age=1040`, `apparent_age=20`

- public: the elder of 幽月谷村, living in the oldest dwelling on 岩屋坡; the village rarely has anything for an elder to decide, so she reads, remembers and talks with whoever comes
- appearance: Eolas look; white hair to her waist, loosely tied; calm grey eyes; a worn book always within reach
- personality: unhurried, dry-humoured, amused by urgency; turns a request for a ruling back into a question
- speech_style: slow, with pauses; begins answers with a small remembered detail; calls everyone 孩子
- life_story: has lived in this valley longer than anyone remembers; has read every shelf of the library and wrote many of them; saw the kiln built and the grove planted
- habit: reads one page aloud to nobody each evening
- social_connection: 希瑞爾溫‧布瑞特瓦特爾 brings her every new note to hear whether it was tried before
- `identity.hidden`: leave empty.
- `voice.misunderstood`: unhurried; says she did not follow, and that there is time to say it again. `voice.greeting` stays `None`.

### Decision 7: dialogue tables

One file per host. The filename stem is the profile key; the file declares no owner field. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and its `references/scene-schema.md` for the schema and the prose standard, and pass its mandatory source gate first.

- `schema_version: 1`, a `greeting`, and exactly the four topics listed for the host.
- Scene ID is the topic ID plus `_scene`; every scene declares `revision: r1`.
- Every formal scene starts with a complete actor utterance, holds 3 to 8 lines and has at least one host line. Actor lines stay true when a possessed companion speaks them.
- A topic marked "pure_chain successor" declares `predecessors` with the named topic's ID and `disclosure: pure_chain`, and no `requires`. Every other topic is open: no `requires`, no `unavailable`.
- A merchant's scenes name only goods on her own shelf, by registry display name, and state no number: no price, no quantity. The 收回 topic matches the service: a merchant buys back only what her shelf offers.
- Name only places that exist: the village's nodes and shared interiors listed in Context, and the hosts of this village named in the Decision 1 table of this change or an earlier applied one.
- Speak as a villager sharing what she makes. Elves need nothing from outsiders and are neither servants nor curiosities.
- The body ease and sexual frankness of Decision 6 ride in the greeting and in the 山谷 and 外人 scenes wherever the host's own subject invites them; explicit speech is allowed. An actor line never initiates, consents to or promises an act.
- No age is stated in player-facing prose: no greeting, scene line, narration or card carries a figure in 歲, an apparent age, or a count of years. The host's long life shows only in what she remembers and how she speaks.
- An existing test reads every village table and rejects proprietor vocabulary. No greeting or line contains any of: 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門, 打烊. Say the world-side thing instead: the door is never shut, the shelf is what she finished this season.

**`world/lore/dialogue/content/eolas_nirnel.yaml`** — topic ID prefix `eolas_nirnel_home`. Greeting: sets down a basket of cut herbs, looks the guest over for tiredness, and names what is bottled today.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_nirnel_home.topic_01` | 香草 | the herb rows of 石階菜畦 and how she picks them |
| `eolas_nirnel_home.topic_02` | 藥露 | 幽月香草藥露: what it restores and when to drink it |
| `eolas_nirnel_home.topic_03` | 魔力 | 魔力藥水 and 強效治療藥水: what each is for; elves take no illness but wounds and spent mana are real |
| `eolas_nirnel_home.topic_04` | 收回 | takes back her own sealed jars; declines herbs picked elsewhere |

**`world/lore/dialogue/content/eolas_raellin.yaml`** — topic ID prefix `eolas_raellin_home`. Greeting: tears a warm flatbread and offers half before asking where the guest is headed.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_raellin_home.topic_01` | 豆餅 | 幽月窯烤豆餅: beans from the terraces, baked in the kiln's cooling heat |
| `eolas_raellin_home.topic_02` | 菜畦 | where the roots, beans and herbs come from: 石階菜畦 |
| `eolas_raellin_home.topic_03` | 共食 | the village eats together at 共食棚 and nobody pays; a guest buys what she carries away |
| `eolas_raellin_home.topic_04` | 收回 | takes back unopened food she packed; declines outside provisions |

**`world/lore/dialogue/content/eolas_saelnel.yaml`** — topic ID prefix `eolas_saelnel_home`. Greeting: closes a book on her finger to keep the page and invites the guest to sit.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `eolas_saelnel_home.topic_01` | 山谷 | how the valley feeds and clothes itself: terraces, grove, kiln, brook, and the open pool at 溫泉浴場 where washing, laundry and talk share one edge |
| `eolas_saelnel_home.topic_02` | 圖書館 | the library nobody runs: shelves of experiment notes anyone may read |
| `eolas_saelnel_home.topic_03` | 外人 | how the village regards visitors: neither wary nor eager; a guest who is here is simply here, and neither a guest who bathes at 溫泉浴場 nor one who keeps dressed is remarked on |
| `eolas_saelnel_home.topic_04` | 往事 | pure_chain successor of 山谷: a small memory of the valley from long ago |

### Decision 8: inventory and ledger

Add to `NPC_SOURCE_INVENTORY` in `world/lore/npc_profiles/inventory.py`, before the `# companions` block, under a comment naming the slice:

```python
    NpcSource("place_host", "eolas_nirnel", "eolas_homes_b"),
    NpcSource("place_host", "eolas_raellin", "eolas_homes_b"),
    NpcSource("place_host", "eolas_saelnel", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_nirnel_home", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_raellin_home", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_saelnel_home", "eolas_homes_b"),
```

In `docs/development/npc-editorial-review.md` add one `place_host` row per host under a new heading `## eolas_homes_b hosts`, and one `dialogue_table` row per table under a new heading `## eolas_homes_b dialogue tables`. Copy the column shape of the 暗影谷村 rows exactly (kind, key, ISO review date, one cell per face, disposition). Write each cell from what you actually read in the finished source; a cell never contains a bare `|`.

### Decision 9: tests

No test edit is planned: the slice modules this change extends are already listed, and `unpin-village-test-data` removed the data pins. If a focused test fails, apply the rule in task 8.5.

### Decision 10: review document and lore document

Create `docs/lore/eolas-fare-homes-review.md` in English, in the shape of `docs/lore/ciaran-crafts-dialogue-review.md`: scope; sources read; per host, the card and voice review, the room prose review, and one line per greeting and scene naming the world-source section it rests on; the list of every proper noun used and the registry row it resolves to; the lint results. This is the human-reviewed record of tone and fidelity.

In `docs/lore/settlement-locations.md`, in Traditional Chinese, using the `chinese-content-writing-guideline` and `writing-style-guideline` skills:

- Find the paragraph that begins `**幽月谷村**位在南北向的小谷裡` in 聚落差異深論. Append sentences that name every host of the village and what she shares, in the register of the surrounding paragraph: 奈拉拉‧弗羅斯特威洛 (織絲者, `silk_grove`); 希瑞爾溫‧布瑞特瓦特爾 (試法者, `proving_ground`); 泰莉斯‧恩貝爾莉夫 (窯匠, `kiln_yard`); 妮爾內爾‧德米多 (調藥者, `terrace_gardens`); 雷林‧莉特弗特 (烤餅好手, `cliff_dwellings`); 賽爾內爾‧妮格汀加勒 (長老, `cliff_dwellings`). Say that each trades from her own home and that it is sharing, not business.
- Find the last item of 未來擴充方向 (it begins `**精靈三村的地點建置**`): edit the item so it lists only 翠綠森林村 as still waiting for personal homes and service hosts.

### Decision 11: regenerated artifact

`content/map-reference-context.json` lists interiors. Regenerate it with `uv run --locked python -m tools.map_reference_context` after the last interior edit.

## Risks / Trade-offs

- [A village price far below the capital's lets a player carry goods out and resell] → This is the accepted 暗影谷村 behaviour: the villages are hidden and the gap is the point of the lore. No new rule is added.
- [One malformed dialogue file or card rejects the whole snapshot and blocks startup] → Tasks load the snapshot and the registries before any prose review.
- [A test elsewhere pins a roster this change grows] → Task 8.5 gives the rule: rewrite the assertion to its logic, append no key.
