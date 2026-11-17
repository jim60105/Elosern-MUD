# Design

## Context

See `proposal.md` for motivation. Facts found while planning:

- `ITEM_REGISTRY` is assembled in `world/lore/items/assembly.py` from `ROWS` tuples in `data_*.py` slices, in a frozen order. A new slice appended after `GUILD_ACCESSORY_ROWS` changes no existing position.
- `ItemDefinition` (`world/lore/items/vocab.py`) validates presentation and mechanism shape at construction. An equipment item needs `equipment_slot` and `modifier_key` together, and the `EquipmentModifierKey` member's value must equal the item key.
- `world/rules/equipment_effects.py` requires exactly one `effects` entry per `EquipmentModifierKey` and checks each value against the budget row of the item's rarity. Budgets today: `uncommon` flat 6, percent 8; `epic` flat 10, percent 12, `weapon_multiplier` 1.30.
- `world/rules/item_effects.py` requires exactly one `items` entry per usable item and none for a non-usable item.
- Food items carry no `use_mechanics` today (`docs/lore/items.md`, 食物 section). The new foods follow that.
- No existing potion restores SP; `stat: sp` is an existing verb.
- World source: `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md`. `tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path.
- `tools/contract_gate.py` runs `tools.map_reference_context --check`, and `content/map-reference-context.json` fingerprints `world/lore/**/*.py` and `world/rules/**/*.yaml`. Editing item data therefore requires regenerating it.
- `world/lore/tests/test_items.py` rejects any ASCII digit in an item's `summary_zh`. 幽月谷村 is the Eolas village (all elements, magic study); 翠綠森林村 is the Fionnen village (light magic, archery). Village life is described in `docs/lore/settlement-locations.md`, 聚落差異深論.

## Goals / Non-Goals

**Goals:**

- Eight items a village host can plausibly make at home, each grounded in a place the village map already has.
- Every item loads through the existing validators with existing vocabulary.

**Non-Goals:**

- No new `ItemKind`, `ItemIconKey`, `ItemRarity`, price band, status key or effect verb.
- No shelf, price, stock or shop row. Prices live in the village changes.
- No test, and no assertion naming any of these items.

## Decisions

### Decision 1: the eight items

All rows set `sellable=True`. `summary_zh` is one line of Traditional Chinese, at most 128 characters, no `<`, URL, emoji, line break or ASCII digit. Write each summary from its "Summary covers" cell; the wording is yours.

| key | `display_name_zh` | kind / icon | rarity | `price_table_key` | mechanism | Summary covers |
| --- | --- | --- | --- | --- | --- | --- |
| `eolas_kiln_flatbread` | 幽月窯烤豆餅 | `FOOD` / `FOOD` | `COMMON` | `specialty_food` | none | bean flatbread baked in 幽月谷村's shared kiln, eaten with herbs |
| `eolas_herb_tonic` | 幽月香草藥露 | `POTION` / `POTION` | `UNCOMMON` | `potion` | `ItemUseMechanics(consumable=True, combat_allowed=True)` | a tonic steeped from the terrace herbs of 幽月谷村 that restores stamina |
| `eolas_glass_pendant` | 幽月琉璃墜 | `ACCESSORY` / `ACCESSORY` | `UNCOMMON` | `jewelry` | `EquipmentSlot.ACCESSORY`, `EquipmentModifierKey.EOLAS_GLASS_PENDANT` | a glass drop fired in the village kiln that steadies the wearer's casting |
| `eolas_proving_wand` | 幽月試法短杖 | `WEAPON` / `WEAPON` | `EPIC` | `masterwork_gear` | `EquipmentSlot.WEAPON_MAIN`, `EquipmentModifierKey.EOLAS_PROVING_WAND` | a short wand the Eolas carve for practice on the proving ground |
| `fionnen_wildflower_honey` | 森林百花蜜 | `FOOD` / `FOOD` | `UNCOMMON` | `specialty_food` | none | honey from the hives of 翠綠森林村's blossom garden |
| `fionnen_beeswax_salve` | 森林蜂蠟膏 | `POTION` / `POTION` | `UNCOMMON` | `potion` | `ItemUseMechanics(consumable=True, combat_allowed=True)` | a wound salve of beeswax and forest herbs |
| `fionnen_archer_bracer` | 森林射手護腕 | `ACCESSORY` / `ACCESSORY` | `UNCOMMON` | `jewelry` | `EquipmentSlot.ACCESSORY`, `EquipmentModifierKey.FIONNEN_ARCHER_BRACER` | a carved wooden bracer forest archers wear on the bow arm |
| `fionnen_leafweave_garb` | 森林葉織獵衣 | `ARMOR` / `ARMOR` | `EPIC` | `masterwork_gear` | `EquipmentSlot.ARMOR`, `EquipmentModifierKey.FIONNEN_LEAFWEAVE_GARB` | light hunting dress woven for moving through the giant trees |

Row order in `ROWS` is the table order. `masterwork_gear` (100..500000) is the band the existing elven craft gear uses; it lets a village price the item at an everyday figure.

Alternative considered: appending to `data_regional_equipment.py`. Rejected: that slice holds equipment only and sits mid-registry; a new last slice keeps every existing position.

### Decision 2: slice and assembly

Create `world/lore/items/data_elven_village_goods.py` with the same imports the neighbouring slices use and one `ROWS: tuple[ItemDefinition, ...]`. In `world/lore/items/assembly.py` add:

```python
from world.lore.items.data_elven_village_goods import ROWS as ELVEN_VILLAGE_GOODS_ROWS
```

and append `*ELVEN_VILLAGE_GOODS_ROWS,` after `*GUILD_ACCESSORY_ROWS,` inside the registry comprehension. Update the module docstring's "last" item note only if it names the last slice.

### Decision 3: enum members

Add to `EquipmentModifierKey` in `world/lore/items/vocab.py`, each in the alphabetical position the existing block uses where one exists, otherwise at the end:

```python
EOLAS_GLASS_PENDANT = "eolas_glass_pendant"
EOLAS_PROVING_WAND = "eolas_proving_wand"
FIONNEN_ARCHER_BRACER = "fionnen_archer_bracer"
FIONNEN_LEAFWEAVE_GARB = "fionnen_leafweave_garb"
```

### Decision 4: equipment effects

Add to `effects:` in `world/rules/rulebook/equipment_effects.yaml`, verbatim:

```yaml
  eolas_glass_pendant:
    adjustments: {mp_cost: "-6%"}
  eolas_proving_wand:
    adjustments: {magic_power: 9, mp_cost: "-10%"}
    # Casting tool: no physical attack bonus, so the neutral declaration stands.
    weapon_damage_multiplier: 1.0
  fionnen_archer_bracer:
    adjustments: {agility: "+5%"}
  fionnen_leafweave_garb:
    adjustments: {defense: 6, agility: 4}
```

Budget check: pendant percent 6 ≤ 8 (uncommon); wand flat 9 ≤ 10 and percent 10 ≤ 12 (epic); bracer percent 5 ≤ 8 (uncommon); garb flat 6 and 4 ≤ 10 (epic). Reference points: `apprentice_focus_staff` (uncommon) is `magic_power: 4, mp_cost: "-5%"`; `beastfolk_gale_earring` (uncommon) is `agility: "+4%"`; `dark_elf_ninja_garb` (epic) is `defense: 5, agility: 5`.

### Decision 5: use effects

Add to `items:` in `world/rules/rulebook/item_effects.yaml`, verbatim:

```yaml
  eolas_herb_tonic:
    effects:
      - stat: sp
        amount: 40
  fionnen_beeswax_salve:
    effects:
      - stat: hp
        amount: 60
```

`mana_potion` restores 40 MP; the tonic restores the same amount of SP. The salve sits between `healing_potion` (40) and `greater_healing_potion` (120).

### Decision 6: lore document

In `docs/lore/items.md`, add one row per item to the table of its category (食物, 藥劑, 武器, 防具, 飾品), after the last existing row of that table, following the columns of that table. 產地／文化 is 幽月谷村（伊歐拉斯族） or 翠綠森林村（斐歐恩族）. The reference price cell is `—` (the item is sold only in its village; the village changes own the figures). Effect cells restate Decisions 4 and 5. Write in Traditional Chinese with the `chinese-content-writing-guideline` and `writing-style-guideline` skills.

### Decision 7: review document

Create `docs/lore/elven-village-goods-review.md` in English: one line per item recording that its name and summary were read against the world source named in Context and the village passages of `docs/lore/settlement-locations.md`, and what the reader checked. This is the human-reviewed record; wording is not test-asserted.

## Risks / Trade-offs

- [An existing test may pin the registry's last key or a per-kind count] → Task 4.3 gives the rule: rewrite such an assertion to the logic it stands for, append no key.
- [`eolas_proving_wand` enters combat calibration suites as a new main-hand weapon] → It declares the neutral multiplier 1.0 like the two existing casting weapons, and is on no starting kit or monster.
