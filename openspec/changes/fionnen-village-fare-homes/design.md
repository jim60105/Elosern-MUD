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

- 4 homes a player can enter, each with a host who talks and, for 2 of them, trades.
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
| `fionnen_elunwen` | 埃倫溫‧斯威夫塔羅 | Elunwen Swiftarrow (starry vault + pure white; swift arrow) | 箭術導師: keeps the archery lane; converses, trades nothing | `fionnen_elunwen_home` 埃倫溫的家 | `archery_lane` | 590 / 29 | none (dialogue only) |
| `fionnen_firwen` | 菲爾溫‧埃文斯塔爾 | Firwen Evenstar (starlight + pure white; evening star) | 長老: the village elder; remembers and converses, trades nothing | `fionnen_firwen_home` 菲爾溫的家 | `canopy_walk` | 1010 / 40 | none (dialogue only) |
| `fionnen_lumeth` | 盧梅斯‧布瑞特莉夫 | Lumeth Brightleaf (radiance + oath; bright leaf) | 蜜漬好手: keeps the hives and candies blossom | `fionnen_lumeth_home` 盧梅斯的家 | `blossom_garden` | 350 / 22 | `fionnen_fare` |
| `fionnen_sylara` | 希拉拉‧希倫特布魯克 | Sylara Silentbrook (wood spirit + grace; silent brook) | 藥草者: grows herbs between the giant trees and makes salve | `fionnen_sylara_home` 希拉拉的家 | `forest_plots` | 620 / 34 | `fionnen_remedies` |

All hosts: `host_race="elf"`, `host_subrace="fionnen"`, `host_sex="female"`.

### Decision 2: the home interiors

One file per host, exactly this shape, with no `art_key` line. Write `desc_zh` from the Room brief in the register of `content/maps/interiors/ciaran_*_home.yaml`: a lived-in room, no signboard, no shopkeeper wording. Existing tests read every village room: the room name contains neither 店 nor 舖, the prose contains neither 櫃檯 nor 招牌, and the prose contains no ASCII word.

`content/maps/interiors/fionnen_elunwen_home.yaml` — Room brief: a room at the head of 靶道; arrows sorted by fletching, a rack for strung bows, the lane visible through the open side.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_elunwen_home
rooms:
  fionnen_elunwen_home:
    name_zh: 埃倫溫的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: archery_lane
  room: fionnen_elunwen_home
  doorway_key: 埃倫溫的家
  doorway_aliases:
  - elunwen
  - elunwen's home
```

`content/maps/interiors/fionnen_firwen_home.yaml` — Room brief: the highest platform room on 樹冠吊橋; open to the leaves on three sides, a mantle on a peg, an old longbow on the wall.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_firwen_home
rooms:
  fionnen_firwen_home:
    name_zh: 菲爾溫的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: canopy_walk
  room: fionnen_firwen_home
  doorway_key: 菲爾溫的家
  doorway_aliases:
  - firwen
  - firwen's home
```

`content/maps/interiors/fionnen_lumeth_home.yaml` — Room brief: a room among the flower beds of 花蕊蜜園; honey jars on every shelf, petals drying on cloth, hives humming outside the window.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_lumeth_home
rooms:
  fionnen_lumeth_home:
    name_zh: 盧梅斯的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: blossom_garden
  room: fionnen_lumeth_home
  doorway_key: 盧梅斯的家
  doorway_aliases:
  - lumeth
  - lumeth's home
```

`content/maps/interiors/fionnen_sylara_home.yaml` — Room brief: a room beside the beds of 林間菜圃; bundles of 止血藥草 drying, a wax pot on a low fire, tins and bottles in rows.

```yaml
# Permanent interior authored source (schema version 1).
# The sole authority for the room's identity, name, prose, scene metadata and
# its one exterior entrance relationship. The room id is the stable place key
# a service record joins to, so a service record declares no geometry.
version: 1
kind: interior
id: fionnen_sylara_home
rooms:
  fionnen_sylara_home:
    name_zh: 希拉拉的家
    desc_zh: <one to three sentences, written from the "Room" brief>
    scene_archetype: tavern_interior
connections: []
exterior:
  settlement: elven_village_fionnen
  node: forest_plots
  room: fionnen_sylara_home
  doorway_key: 希拉拉的家
  doorway_aliases:
  - sylara
  - sylara's home
```

### Decision 3: place rows

Insert each of these rows into `ROWS` in `world/lore/settlements/places_fionnen.py` at its alphabetical position by `key`, between the existing rows, so the whole tuple stays alphabetical:

```python
    PlaceDefinition(
        key="fionnen_elunwen_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_elunwen_home", "fionnen_elunwen_home"),
        host_name="埃倫溫‧斯威夫塔羅",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_elunwen",
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_elunwen_home"),
                dialogue_key="fionnen_elunwen_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_firwen_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_firwen_home", "fionnen_firwen_home"),
        host_name="菲爾溫‧埃文斯塔爾",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_firwen",
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_firwen_home"),
                dialogue_key="fionnen_firwen_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_lumeth_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_lumeth_home", "fionnen_lumeth_home"),
        host_name="盧梅斯‧布瑞特莉夫",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_lumeth",
        assortment_keys=("fionnen_fare",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_lumeth_home"),
                service_id="fionnen_lumeth",
                shop_key="fionnen_lumeth_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_lumeth_home"),
                dialogue_key="fionnen_lumeth_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_sylara_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_sylara_home", "fionnen_sylara_home"),
        host_name="希拉拉‧希倫特布魯克",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_sylara",
        assortment_keys=("fionnen_remedies",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_sylara_home"),
                service_id="fionnen_sylara",
                shop_key="fionnen_sylara_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_sylara_home"),
                dialogue_key="fionnen_sylara_home",
            ),
        ),
    ),
```

### Decision 4: shelves

Add to `ASSORTMENT_REGISTRY` in `world/lore/settlements/assortments.py`, after the last existing entry, verbatim:

```python
        AssortmentDefinition(
            key="fionnen_fare",
            display_name_zh="森林飯食",
            allowed_item_kinds=frozenset({ItemKind.FOOD}),
            item_keys=(
                "fionnen_wildflower_honey", "elven_candied_blossom", "meal",
            ),
        ),
        AssortmentDefinition(
            key="fionnen_remedies",
            display_name_zh="森林藥草",
            allowed_item_kinds=frozenset({ItemKind.POTION, ItemKind.MATERIAL}),
            item_keys=(
                "fionnen_beeswax_salve", "healing_herb", "healing_potion",
            ),
        ),
```

Add one comment above them naming the village and saying each shelf is one villager's home.

### Decision 5: offers, hours and prices

Append to the `assortments:` list of `world/rules/rulebook/commerce/fionnen.yaml`:

```yaml
  - key: fionnen_fare
    offers:
      - item_key: fionnen_wildflower_honey
        buy_copper: 15
        sell_copper: 8
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: elven_candied_blossom
        buy_copper: 20
        sell_copper: 10
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: meal
        buy_copper: 6
        sell_copper: 3
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
  - key: fionnen_remedies
    offers:
      - item_key: fionnen_beeswax_salve
        buy_copper: 70
        sell_copper: 35
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
      - item_key: healing_herb
        buy_copper: 20
        sell_copper: 10
        max_stock: 20
        initial_stock: 10
        restock_quantity: 5
      - item_key: healing_potion
        buy_copper: 60
        sell_copper: 30
        max_stock: 10
        initial_stock: 5
        restock_quantity: 5
```

and to its `shops:` list:

```yaml
  - shop_key: fionnen_lumeth_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
  - shop_key: fionnen_sylara_home
    open_hour: 7
    close_hour: 19
    restock_hour: 6
```

The pricing rule is the one 暗影谷村 uses and the user confirmed: goods are local produce, so the village that makes them sells them at everyday figures, whatever the capital charges. Each figure sits inside the item's `PRICE_TABLE` band, `sell_copper` is half of `buy_copper` rounded up, and every item the capital also sells is cheaper here.

| Shelf | Item | Buy / sell (copper) | Max / initial / restock | Basis |
| --- | --- | --- | --- | --- |
| `fionnen_fare` | `fionnen_wildflower_honey` | 15 / 8 | 20 / 10 / 5 | new local item; specialty_food band 10..100 |
| `fionnen_fare` | `elven_candied_blossom` | 20 / 10 | 20 / 10 / 5 | capital 60; same figure as 暗影谷村 |
| `fionnen_fare` | `meal` | 6 / 3 | 20 / 10 / 5 | capital 10; meal band 5..10 |
| `fionnen_remedies` | `fionnen_beeswax_salve` | 70 / 35 | 10 / 5 / 5 | new local item; potion band 50..500 |
| `fionnen_remedies` | `healing_herb` | 20 / 10 | 20 / 10 / 5 | capital 40; material band floor is 20 |
| `fionnen_remedies` | `healing_potion` | 60 / 30 | 10 / 5 / 5 | capital 100; potion band 50..500 |

Shop hours match 暗影谷村: open 7, close 19, restock 6.

### Decision 6: profiles

Create `world/lore/npc_profiles/fionnen_homes_b.py` in the shape of `world/lore/npc_profiles/ciaran_homes_a.py`: a module docstring, the same imports, and `ROWS: tuple[NpcProfile, ...]` with one `NpcProfile` per host in the order of the Decision 1 table. In `world/lore/npc_profiles/__init__.py` add the import `from world.lore.npc_profiles.fionnen_homes_b import ROWS as FIONNEN_HOMES_B_ROWS  # noqa: E402`, append `("fionnen_homes_b", FIONNEN_HOMES_B_ROWS),` as the last entry of `PROFILE_SLICES`, add `"FIONNEN_HOMES_B_ROWS"` to `__all__`, and add the label to the order named in the module docstring.

World source, mandatory: read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (`tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path), sections 種族設定 › 精靈族, 社會與文化 and 特殊設定, before writing, and write every card from it. All elves are women. About 300 exist and the three nations rank them above royalty. They have no fixed trades, no marriage and no schooling; ability comes from lifespan. A host shares what she loves making and takes coin because the village wants guests looked after, so no card speaks of a shop, stock or business. Fionnen look, from the world source: fair skin, mostly blonde hair and blue or green eyes, 160-180 cm. The village is defined by archery, light magic, bees and woodwork. Elves treat sex and the bare body as naturally as breathing and feel no shame about either (world source, 性文化 and 倫理觀); write every host with that ease. It shows in how she dresses, sits and speaks of her own goods, at the frankness of the accepted reference `world/lore/dialogue/content/ciaran_vethiel.yaml`.

Each card fills the seven fields of `NpcCard` from the brief below, in Traditional Chinese, within the card limits (leaf 600, identity section 600, whole card 2000 code points). The brief fixes the facts; the sentences are yours. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and the two writing-guideline skills.

**`fionnen_elunwen` 埃倫溫‧斯威夫塔羅** — `age=590`, `apparent_age=29`

- public: the archer most often found on 靶道, living beside it; keeps the targets and the swinging tags in order and shoots beside anyone who comes, teaching nobody by the hand
- appearance: Fionnen look; lean, blonde hair cropped at the jaw; a bracer on the left arm and little else; a quiver worn low
- personality: quiet, focused, generous with silence; praises nothing but notices everything
- speech_style: sparse, exact, speaks between shots; calls the listener 你
- life_story: six centuries at the lane; hunts the deep forest when she wants a living target; the village's young learn by standing next to her
- habit: walks the lane at dawn and resets every tag by hand
- social_connection: tests every bow 格威內爾‧斯威夫塔羅 finishes; they share a dwelling name
- `identity.hidden`: leave empty.
- `voice.misunderstood`: quiet; asks whether the visitor came to shoot. `voice.greeting` stays `None`.

**`fionnen_firwen` 菲爾溫‧埃文斯塔爾** — `age=1010`, `apparent_age=40`

- public: the elder of 翠綠森林村, living on the highest platform of 樹冠吊橋; the village rarely needs an elder's word, so she watches the forest and talks with whoever climbs up
- appearance: Fionnen look; silver-blonde hair to the knees; bare under a single open mantle; a longbow older than the kingdom on the wall behind her
- personality: serene, warm, impossible to hurry; finds mortal urgency endearing
- speech_style: slow and melodic; begins with what she can see from her platform; calls everyone 孩子
- life_story: a thousand years in these trees; remembers the clearing before the canopy opened; has loved most of the village at one time or another
- habit: names the first bird she hears each morning
- social_connection: taught 埃倫溫‧斯威夫塔羅 to draw a bow five centuries ago
- `identity.hidden`: leave empty.
- `voice.misunderstood`: serene; says she did not follow, and that the day is long. `voice.greeting` stays `None`.

**`fionnen_lumeth` 盧梅斯‧布瑞特莉夫** — `age=350`, `apparent_age=22`

- public: the villager who keeps the hives of 花蕊蜜園 and candies blossom in honey; feeds the village from 蜜漬房 and packs jars for a visitor for coin
- appearance: Fionnen look; sun-gold curls; bare arms sticky to the wrist; a bee or two riding her shoulder unbothered
- personality: sweet-natured, generous, a little vain about her honey; puts a taste on a guest's lips before a word is said
- speech_style: cheerful, everyday, uses 喔 and 呀; calls the listener 你
- life_story: the youngest of the village's makers at three and a half centuries; took the hives from an elder who went back to her bow
- habit: licks the spoon and names the flower before she seals a jar
- social_connection: 希拉拉‧希倫特布魯克 takes her beeswax for salve
- `identity.hidden`: leave empty.
- `voice.misunderstood`: cheerful; offers a taste and asks again. `voice.greeting` stays `None`.

**`fionnen_sylara` 希拉拉‧希倫特布魯克** — `age=620`, `apparent_age=34`

- public: the villager who tends the herb beds of 林間菜圃; cuts 止血藥草, cooks beeswax salve and keeps healing potion for hunters and for guests
- appearance: Fionnen look; ash-blonde hair pinned up with a twig; green-eyed, level gaze; a salve tin on a cord at her hip
- personality: composed, practical, kind without softness; treats a wound before she asks how it happened
- speech_style: measured, complete sentences, gives instructions clearly; calls the listener 你
- life_story: six centuries patching hunters who came back from the deep forest; elves mend by themselves, so she learned her craft on the village's guests and animals
- habit: washes her hands in the brook before and after every bed
- social_connection: 盧梅斯‧布瑞特莉夫 brings her wax after every harvest
- `identity.hidden`: leave empty.
- `voice.misunderstood`: level; asks whether there is a wound or whether it is about herbs. `voice.greeting` stays `None`.

### Decision 7: dialogue tables

One file per host. The filename stem is the profile key; the file declares no owner field. Follow `.agents/skills/npc-dialogue-content/SKILL.md` and its `references/scene-schema.md` for the schema and the prose standard, and pass its mandatory source gate first.

- `schema_version: 1`, a `greeting`, and exactly the four topics listed for the host.
- Scene ID is the topic ID plus `_scene`; every scene declares `revision: r1`.
- Every formal scene starts with a complete actor utterance, holds 3 to 8 lines and has at least one host line. Actor lines stay true when a possessed companion speaks them.
- A topic marked "pure_chain successor" declares `predecessors` with the named topic's ID and `disclosure: pure_chain`, and no `requires`. Every other topic is open: no `requires`, no `unavailable`.
- A merchant's scenes name only goods on her own shelf, by registry display name, and state no number: no price, no quantity. The 收回 topic matches the service: a merchant buys back only what her shelf offers.
- Name only places that exist: the village's nodes and shared interiors listed in Context, and the hosts of this village named in the Decision 1 table of this change or an earlier applied one.
- Speak as a villager sharing what she makes. Elves need nothing from outsiders and are neither servants nor curiosities.
- That body ease rides in the greeting and in 菲爾溫's 森林 scene; it never becomes a sexual scene in a fare host's home.
- An existing test reads every village table and rejects proprietor vocabulary. No greeting or line contains any of: 老闆, 店主, 本店, 營業時間, 營業, 庫存, 存貨, 存量, 售價, 光臨, 開店, 開門, 打烊. Say the world-side thing instead: the door is never shut, the shelf is what she finished this season.

**`world/lore/dialogue/content/fionnen_elunwen.yaml`** — topic ID prefix `fionnen_elunwen_home`. Greeting: lowers her bow after the shot lands, glances at the guest's stance, and nods toward the spare bows.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_elunwen_home.topic_01` | 箭術 | what the bow asks of an archer: breath, stance and patience |
| `fionnen_elunwen_home.topic_02` | 靶道 | 靶道: targets nailed to trunks, wooden tags swinging further off, open to all |
| `fionnen_elunwen_home.topic_03` | 光法 | light magic is practised on the same lane as archery |
| `fionnen_elunwen_home.topic_04` | 比試 | declines a contest; points to the targets and the spare bows instead |

**`world/lore/dialogue/content/fionnen_firwen.yaml`** — topic ID prefix `fionnen_firwen_home`. Greeting: turns from the view without rising and invites the guest to sit where the light falls.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_firwen_home.topic_01` | 森林 | the village in the giant trees: two levels, brook, plots, hives, and the open 林泉浴場 where washing, laundry and talk happen among neighbours |
| `fionnen_firwen_home.topic_02` | 光庭 | 林間光庭: the gap in the canopy where the village gathers |
| `fionnen_firwen_home.topic_03` | 外人 | how the village regards visitors: unconcerned; the path stays hidden because nobody thinks to show it |
| `fionnen_firwen_home.topic_04` | 往事 | pure_chain successor of 森林: a small memory from before the canopy opened |

**`world/lore/dialogue/content/fionnen_lumeth.yaml`** — topic ID prefix `fionnen_lumeth_home`. Greeting: dips a finger in fresh honey, holds it out for the guest to taste, then asks what they came for.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_lumeth_home.topic_01` | 養蜂 | the hives of 花蕊蜜園 and 森林百花蜜 |
| `fionnen_lumeth_home.topic_02` | 蜜漬 | 精靈蜜漬花蕊: petals and honey cooked together |
| `fionnen_lumeth_home.topic_03` | 蜜漬房 | the shared 蜜漬房: the village's candying room and food store; nobody pays there |
| `fionnen_lumeth_home.topic_04` | 收回 | takes back unopened jars; declines outside food |

**`world/lore/dialogue/content/fionnen_sylara.yaml`** — topic ID prefix `fionnen_sylara_home`. Greeting: looks the guest over for blood first, then wipes her hands and names what is ready.

| `topic_id` | `keyword` and `label` | The scene covers |
| --- | --- | --- |
| `fionnen_sylara_home.topic_01` | 藥草 | 止血藥草 from the beds of 林間菜圃 |
| `fionnen_sylara_home.topic_02` | 蜂蠟膏 | 森林蜂蠟膏: wax from the hives, cooked with herbs; what it closes |
| `fionnen_sylara_home.topic_03` | 光法 | the Fionnen affinity for light magic and healing, as a villager's everyday fact; she heals no one in the scene |
| `fionnen_sylara_home.topic_04` | 收回 | takes back her own sealed tins and bottles; declines outside herbs |

### Decision 8: inventory and ledger

Add to `NPC_SOURCE_INVENTORY` in `world/lore/npc_profiles/inventory.py`, before the `# companions` block, under a comment naming the slice:

```python
    NpcSource("place_host", "fionnen_elunwen", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_firwen", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_lumeth", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_sylara", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_elunwen_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_firwen_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_lumeth_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_sylara_home", "fionnen_homes_b"),
```

In `docs/development/npc-editorial-review.md` add one `place_host` row per host under a new heading `## fionnen_homes_b hosts`, and one `dialogue_table` row per table under a new heading `## fionnen_homes_b dialogue tables`. Copy the column shape of the 暗影谷村 rows exactly (kind, key, ISO review date, one cell per face, disposition). Write each cell from what you actually read in the finished source; a cell never contains a bare `|`.

### Decision 9: tests

No test edit is planned: the slice modules this change extends are already listed, and `unpin-village-test-data` removed the data pins. If a focused test fails, apply the rule in task 8.5.

### Decision 10: review document and lore document

Create `docs/lore/fionnen-fare-homes-review.md` in English, in the shape of `docs/lore/ciaran-crafts-dialogue-review.md`: scope; sources read; per host, the card and voice review, the room prose review, and one line per greeting and scene naming the world-source section it rests on; the list of every proper noun used and the registry row it resolves to; the lint results. This is the human-reviewed record of tone and fidelity.

In `docs/lore/settlement-locations.md`, in Traditional Chinese, using the `chinese-content-writing-guideline` and `writing-style-guideline` skills:

- Find the paragraph that begins `**翠綠森林村**建在巨木之間` in 聚落差異深論. Append sentences that name every host of the village and what she shares, in the register of the surrounding paragraph: 科瑞斯‧蒙希斯佩爾 (巧作者, `root_dwellings`); 格威內爾‧斯威夫塔羅 (弓匠, `craft_glade`); 伊斯爾林‧斯塔爾威維爾 (織衣者, `canopy_walk`); 埃倫溫‧斯威夫塔羅 (箭術導師, `archery_lane`); 菲爾溫‧埃文斯塔爾 (長老, `canopy_walk`); 盧梅斯‧布瑞特莉夫 (蜜漬好手, `blossom_garden`); 希拉拉‧希倫特布魯克 (藥草者, `forest_plots`). Say that each trades from her own home and that it is sharing, not business.
- Find the last item of 未來擴充方向 (it begins `**精靈三村的地點建置**`): replace the item's text so it no longer says the homes and hosts of the two villages are missing: all three villages now have homes and service hosts.

### Decision 11: regenerated artifact

`content/map-reference-context.json` lists interiors. Regenerate it with `uv run --locked python -m tools.map_reference_context` after the last interior edit.

## Risks / Trade-offs

- [A village price far below the capital's lets a player carry goods out and resell] → This is the accepted 暗影谷村 behaviour: the villages are hidden and the gap is the point of the lore. No new rule is added.
- [One malformed dialogue file or card rejects the whole snapshot and blocks startup] → Tasks load the snapshot and the registries before any prose review.
- [A test elsewhere pins a roster this change grows] → Task 8.5 gives the rule: rewrite the assertion to its logic, append no key.
