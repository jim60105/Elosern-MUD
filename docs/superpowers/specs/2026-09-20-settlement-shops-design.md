# Settlement Places and Assortment-Driven Shops — Design

**Date:** 2026-09-20
**Status:** Draft
**Scope:** Introduce a three-layer commerce data model (assortments, places,
settlements) so a shop is one authored row instead of four hand-synced
sources; add per-shop and per-item price variation; land four trading places
in 聖潔王都 and a complete new settlement (暗影谷村) on the elven-village
archetype.

---

## 1. Context and Problem

`docs/lore/settlement-locations.md` defines eighteen place types across six
settlement archetypes. The runtime can express exactly one shop.

Creating one shop today requires four hand-synchronized edits:

| Source | Content |
| --- | --- |
| `world/lore/shops.py:24` | `ShopDefinition`: key, host name/title, every offered item key |
| `world/rules/rulebook/guild_economy.yaml:98` | `shops:` — per item buy/sell/max/initial/restock |
| `world/rules/rulebook/guild_economy.yaml:460` | `service_hosts:` — one roster row |
| `world/maps/bootstrap.py:44` | Hard-coded interior room constants and calls |

`world/rules/guild_config.py:322` additionally enforces exact alignment
between `offered_item_keys` and `offers`: a missing or surplus entry fails
catalog load. That fail-closed contract is correct and is kept, but today it
is paid **per shop**. The single shipped shop carries 58 items, so its YAML
block is 58 × 6 lines. Six settlements × eight shops under this model is
unmaintainable.

Three further gaps block the lore document:

- **No shop kind and no shop display name.** `commands/economy.py:127`
  prints a hard-coded `商店（營業中）：`, so a player cannot tell a forge
  from a bakery.
- **No settlement archetype.** `AnchorKind` has only `capital`,
  `elven_village`, `dungeon`. The applicability matrix at
  `docs/lore/settlement-locations.md:44` has no machine-readable form.
- **Interiors are code.** `sync_service_interiors()` hard-codes two rooms.

### 1.1 Defect found during design

`world/rules/guild_config.py:227`:

```python
known_parents = {definition.merchant_component_key: definition.key
                 for definition in SHOP_REGISTRY.values()}
```

`merchant_component_key` is `"merchant"` for every shop, so this dict always
holds exactly one entry — later shops overwrite earlier ones. The loop's
`known_parents.pop(shop.merchant_component_key, None)` then clears it on the
first shop, and the closing "shops is missing rules for …" completeness check
becomes a no-op. With one shop the bug is invisible; with two it silently
accepts a shop whose entire YAML rule block is absent.

`merchant_component_key` carries no information (its value is constant). This
design removes the field and re-keys the completeness check on `shop_key`.

---

## 2. Goals and Non-Goals

**Goals**

- One authored row per place; no cross-file synchronization.
- Named assortments reusable across settlements, validated once per
  assortment rather than once per shop.
- Same `item_key` priced differently per location, with the item identity
  unchanged.
- Land four trading places in 聖潔王都 and four in a new 暗影谷村.
- Machine-readable settlement archetype vocabulary.

**Non-Goals**

- Rebuilding the 聖潔王都 map. The lore document calls for a full redesign
  (王宮, 魔法學院, 貴族區 interiors); that is a separate future change. The
  `PlaceDefinition` shape is additive so it will not block that work.
- The remaining fourteen place types (旅店, 公共浴場, 訓練場, 魔法學院,
  商會, 貴族區, 市場街, …). No mechanism changes are needed to add them
  later — only rows.
- Durability/repair, lodging fees, escort commissions. All are marked
  〔提案〕 in the lore document and stay out.
- New professions. `merchant` covers every trading place; the lore document
  (line 77) already states that 鐵匠/裁縫師/鍊金師 are titles, not
  professions.

---

## 3. Architecture

Three new layers, following the established split: immutable identity in
`world/lore/*` as frozen dataclasses, tunable numbers in
`world/rules/rulebook/*.yaml`, joined and fully validated at load time by
`world/rules/guild_config.py`.

```
world/lore/settlements/            (new package)
  settlements.py   SettlementArchetype, SettlementDefinition, SETTLEMENT_REGISTRY
  places.py        PlaceKind, PlaceDefinition, PLACE_REGISTRY
  assortments.py   AssortmentDefinition, ASSORTMENT_REGISTRY
  shops.py         SHOP_REGISTRY derived from PLACE_REGISTRY + the two validators

world/rules/rulebook/commerce.yaml (new)
  price_scales, assortments[].offers[], shops[] (hours + overrides)
```

`world/lore/shops.py` is deleted. Its only non-test consumer is
`world/rules/guild_config.py`; everything else is tests and synthetic
fixtures, so no compatibility shim is warranted.

### 3.1 Assortment layer

```python
@dataclass(frozen=True)
class AssortmentDefinition:
    key: str                      # "common_arms"
    display_name_zh: str
    item_keys: tuple[str, ...]
```

Numbers live in `commerce.yaml`:

```yaml
assortments:
  - key: common_arms
    offers:
      - item_key: plain_sword
        buy_copper: 250
        sell_copper: 100
        max_stock: 3
        initial_stock: 1
        restock_quantity: 1
```

The existing alignment contract is preserved verbatim, but now binds
`AssortmentDefinition.item_keys` to that assortment's `offers`. Ten shops
referencing one assortment pay the alignment cost once.

### 3.2 Place layer

```python
class PlaceKind(StrEnum):
    GUILD_HALL = "guild_hall"
    GENERAL_STORE = "general_store"
    WEAPONSMITH = "weaponsmith"
    OUTFITTER = "outfitter"
    EATERY = "eatery"

@dataclass(frozen=True)
class PlaceDefinition:
    key: str                              # also the interior room tag
    settlement_key: str
    kind: PlaceKind
    room_name_zh: str
    room_desc_zh: str
    exterior_xy: tuple[int, int]          # z derived from the settlement
    doorway_key_zh: str
    doorway_aliases: tuple[str, ...]
    host_name: str
    host_title: str
    profession: str
    service_id: str
    assortment_keys: tuple[str, ...]
    extra_item_keys: tuple[str, ...]      # per-place additions
    excluded_item_keys: tuple[str, ...]   # per-place removals
    authored_kwargs: tuple[tuple[str, str], ...]   # frozen mapping
```

`authored_kwargs` carries the per-component identity fields the profession
blueprint needs — `shop_key` for `merchant`, `branch_key` + `dialogue_key`
for `guild_staff` — and is projected onto the blueprint exactly as
`validate_service_hosts` projects roster kwargs today. A flat `shop_key`
field would not cover the guild hall, whose host is `guild_staff`.

Validation rules on a place row:

- Blueprint coverage and dead-kwarg rejection are inherited unchanged from
  `validate_service_hosts` (every component's identity fields except the
  row-level `service_id` must be authored; surplus kwargs are an error).
- `assortment_keys` is non-empty **iff** `authored_kwargs` contains
  `shop_key`. A trading place without an assortment, or an assortment on a
  non-trading place, fails load.

`SHOP_REGISTRY` and the `service_hosts:` roster are both **derived** from
`PLACE_REGISTRY`. A place contributes a `ShopDefinition` iff its
`authored_kwargs` carry a `shop_key`. `offered_item_keys` is the union of
the referenced assortments' `item_keys`, plus `extra_item_keys`, minus
`excluded_item_keys`. The cross-registry authored-name uniqueness check
(shops × guild branches × guild ranks) runs unchanged over the derived rows.

### 3.3 Settlement layer

```python
class SettlementArchetype(StrEnum):
    CAPITAL = "capital"
    TOWN = "town"
    PORT = "port"
    BEAST_CITY = "beast_city"
    ELVEN_VILLAGE = "elven_village"
    FRONTIER = "frontier"

@dataclass(frozen=True)
class SettlementDefinition:
    key: str                  # equals the ANCHOR_REGISTRY key
    archetype: SettlementArchetype
    zcoord: str
```

`AnchorKind` is left alone: it includes `dungeon` and classifies geography,
whereas the archetype classifies construction. They are different axes.

---

## 4. Price Model

Two layers, one multiplication, one rounding.

```
final_buy  = override.buy_copper            if the place overrides this item
           = round(base_buy  * scale / 100) otherwise
final_sell = override.sell_copper           if the place overrides this item
           = round(base_sell * scale / 100) otherwise
```

- `base_*` — the assortment offer's copper values.
- `scale` — integer percent. Defaults to the settlement's `price_scales`
  entry; a place may declare its own. `100` is par.
- **Overrides replace absolutely and are not scaled.** This keeps the
  arithmetic to a single multiplication so there is no rounding-order
  ambiguity.

An override row is always **complete** — all five fields (`buy_copper`,
`sell_copper`, `max_stock`, `initial_stock`, `restock_quantity`) — and
wholly replaces the assortment's row for that item. Partial overrides are
rejected: a half-specified row is exactly the kind of implicit merge this
codebase's fail-closed loader exists to prevent.

This makes overrides also the supply route for `extra_item_keys`, which by
definition belong to no referenced assortment and therefore have no base
row. Each `extra_item_keys` entry **must** carry a complete override, and
each override must name an item the place actually offers (an assortment
item or an extra). Both directions fail load.

```yaml
shops:
  - shop_key: altoria_general_store
    open_hour: 8
    close_hour: 20
    restock_hour: 6
    price_scale: 100          # optional; defaults to the settlement's
    overrides:
      - item_key: elven_spider_silk    # an extra_item_keys entry
        buy_copper: 8000
        sell_copper: 4000
        max_stock: 1
        initial_stock: 0
        restock_quantity: 1
```

Rounding is integer-only, half-up: `(base * scale + 50) // 100`. No float
ever enters the path, matching the existing integer-copper contract.

Validation runs **after** scaling: the scaled `buy_copper` must lie inside
the item's `PRICE_TABLE` band, `scaled_sell <= scaled_buy` must hold, and
`scale` must be an integer in `1..1000`. A violation fails catalog load at
startup, never at trade time.

### 4.1 Worked example

`elven_spider_silk` (band `material`, floor 20, **no ceiling**). Both
settlements take `scale = 100`, so the village price is the unscaled
assortment base and the capital price comes from an override:

| Place | Source | Final buy |
| --- | --- | --- |
| 塞雷的家 (暗影谷村) | `elven_sundries` base, scale 100 | 60 copper |
| 阿爾托利亞雜貨商店 (聖潔王都) | per-item override on the place row | 8,000 copper |

One `item_key`, one `ItemDefinition`. What the player carries away is
identical in both places. The capital reaches the item through
`extra_item_keys`, not by referencing the elven assortment — it stocks the
silk, not the elves' whole shelf.

### 4.2 Known limitation

`PRICE_TABLE` bands are **global per item**. A band whose ceiling is lower
than the intended outside-world price cannot express that price at all. This
change widens the affected items' band (§5) rather than working around the
check. Should a future change need an outside price above the widened
ceiling, it must either widen the band again or introduce location-scoped
bands — not bypass the validator.

---

## 5. Item Registry Changes

### 5.1 New price band

```python
"masterwork_gear": PriceEntry(
    "masterwork_gear", "名匠裝備", 100, 500_000,
    "Master-crafted gear priced by scarcity, not materials: ordinary "
    "inside the maker's community, extraordinary outside it.",
),
```

The floor of 100 admits the in-village ordinary price; the 500,000 ceiling
(50 gold) supports the outside-world price while staying below `relic`'s
999,999 floor so the keepsake band is not eroded. The key is deliberately
race-neutral: human master smiths and beastfolk tribal artisans fit the same
band later.

Rationale: a high price outside an elven village is a *market* fact, not a
property of the object. The band must describe what the object is — a very
good steel blade — and be wide enough for both markets.

### 5.2 Band migration

Seven items move, and `sellable` opens on the six `relic` rows:

| item_key | 顯示名 | From | To | sellable |
| --- | --- | --- | --- | --- |
| `shadow_blade` | 暗影鋼刀 | relic | masterwork_gear | False → True |
| `shadow_blade_echo` | 暗影鋼刀·影 | relic | masterwork_gear | False → True |
| `dark_elf_kimono` | 精靈短袍傳統服飾 | relic | masterwork_gear | False → True |
| `dark_elf_ninja_garb` | 精靈戰鬥服飾 | relic | masterwork_gear | False → True |
| `elven_traditional_robe` | 精靈傳統服飾 | relic | masterwork_gear | False → True |
| `crescent_earring` | 月牙耳環 | relic | masterwork_gear | False → True |
| `elven_forest_veil` | 精靈森林輕紗 | armor | masterwork_gear | already True |

`dark_elf_kimono`'s own summary already reads 「精靈村商店的現成品」 while
sitting in a band that forbids trade — the data contradicted itself.

Nine `relic` rows stay: `family_crest_token`, `ancient_mystery_key`,
`royal_signet_ring`, `royal_heirloom_pendant`, `rose_crest_rapier`,
`silver_feather_earring`, `black_maid_dress`, `elven_child_toy`,
`guild_recruit_badge`. These are genuinely one-of-a-kind.

### 5.3 Rarity

Rarity is presentation-only and never enters price validation (the existing
`item-presentation-metadata` contract). Elven goods are raised to reflect
that elves produce epic and legendary work as daily output:

| item_key | From | To |
| --- | --- | --- |
| `elven_candied_blossom` | UNCOMMON | RARE |
| `prism_charm` | UNCOMMON | RARE |
| `elven_longbow` | RARE | EPIC |

All migrated items keep their existing EPIC / LEGENDARY rarity.
`elven_forest_veil` is the precedent that LEGENDARY rarity and a tradeable
band already coexist.

---

## 6. Landed Content

### 6.1 聖潔王都 (`capital_altoria`, CAPITAL)

The existing 5×5 grid already has an exterior node for every place in this
change, so `world/maps/altoria_capital.py`, `WILDERNESS_ENTRY_REGISTRY`,
`CITY_GATE_REGISTRY` and `ANCHOR_PLACEMENT_REGISTRY` are **untouched**.

| Interior | Exterior node | Host | Assortment |
| --- | --- | --- | --- |
| 阿爾托利亞冒險者公會大廳 | (3,1) 冒險者公會外 | 葛里安·衛登 (unchanged) | — |
| 阿爾托利亞雜貨商店 | (1,2) 市場街 | 瑪爾特·金秤 (unchanged) | `general_sundries` |
| 聖潔王都鍛造鋪 | (0,2) 鐵匠鋪外 | 維爾登·黑潭 | `common_arms` |
| 聖潔王都餐館 | (2,1) 南大道 | 西格瑪·庫柏 | `staple_meals` |
| 聖潔王都裁縫坊 | (2,3) 北大道 | 妮絲塔·狐溪 | `common_outfits` |

The existing 58-item monolith is redistributed into four non-overlapping
assortments — weapons to `common_arms`, armor to `common_outfits`, food to
`staple_meals`, the remainder (potions, accessories, materials, tools, toys)
staying in `general_sundries`. Total capital item coverage is unchanged, so
no equipment becomes unobtainable while 首飾店 and 鍊金坊 are still pending.

### 6.2 暗影谷村 (`village_ciaran`, ELVEN_VILLAGE)

New `world/maps/village_ciaran.py`. Six nodes: 村中廣場 (the `anchor_room`
for `village_ciaran`), 隱密小徑 (the gate node), plus four exterior nodes —
練刀場, 溪畔小徑, 村北古樹下, 織房坡.

Every trading place is a private home, not a storefront. Room names use the
given name only; the full 名·姓 form would be unwieldy and is not how a
village refers to a neighbour's house.

| Interior | Exterior node | Host | Assortment |
| --- | --- | --- | --- |
| 倫溫的家 | 練刀場 | 倫溫·斯塔爾法爾 | `elven_crafted_arms` |
| 拉瑞內斯的家 | 溪畔小徑 | 拉瑞內斯·妮特布倫 | `elven_fare` |
| 塞雷的家 | 村北古樹下 | 塞雷·拉文伍德 | `elven_sundries` |
| 凱拉斯的家 | 織房坡 | 凱拉斯·菲溫德 | `elven_attire` |

村中廣場 and 練刀場 are public space and carry no components this change;
`practice` is already room-independent.

New registry rows: `ANCHOR_PLACEMENT_REGISTRY["village_ciaran"]`,
`WILDERNESS_ENTRY_REGISTRY["village_ciaran"]` (footprint must avoid the
capital's (58,98)–(62,102)), and `CITY_GATE_REGISTRY["village_ciaran"]` with
`exit_key="隱密小徑"`.

The Limbo gate is required because the game ships an elf player preset.
`world/maps/city_gates.py:10` states that race-based gate selection is out of
scope, so **every race will see both gates from 虛境**. This is accepted:
restricting non-elf access to the hidden village is deferred.

### 6.3 NPC identities

Names were rolled with the `fantasy-name-generator` skill and chosen so the
etymology matches the character. Registry names use U+00B7 `·` (the authored
convention), not the generator's U+30FB. Titles carry no internal whitespace,
per `validate_npc_title`.

| Name | Original | Title | Why |
| --- | --- | --- | --- |
| 維爾登·黑潭 | Verdon Blackmere | `聖潔王都鍛造鋪鐵匠` | "Blackmere" reads as the quenching pool |
| 西格瑪·庫柏 | Sigmar Cooper | `聖潔王都餐館老闆` | Cooper = barrel-maker; the family trade became an eatery |
| 妮絲塔·狐溪 | Nesta Foxbourne | `聖潔王都裁縫坊坊主` | Fox fur and streamside fulling — material and process both in the surname |
| 倫溫·斯塔爾法爾 | Lumwyn Starfall | `暗影谷村鑄刃者` | "Starfall" = meteoric iron, tying to the 暗影鋼 blades |
| 拉瑞內斯·妮特布倫 | Lareneth Nightbloom | `暗影谷村花饌好手` | Night-blooming flowers: the valley's darkness and the 蜜漬花蕊 |
| 塞雷·拉文伍德 | Serai Ravenwood | `暗影谷村蒐羅者` | Ravens hoard; that *is* the collector trait |
| 凱拉斯·菲溫德 | Caellas Faewind | `暗影谷村織衣者` | "Leaf-light one" + "Faewind" for the gossamer elven weaves |

The three elven titles deliberately avoid 老闆 / 店主 — those words denote
commercial establishments, which elven villages do not have.

`docs/lore/settlement-locations.md` names 霍布·熔爐 (line 170) and 柯爾特·暖爐
(line 265) as the capital's smith and eatery owner. Those examples must be
updated to the names above as part of this change.

---

## 7. Component and Runtime Changes

- **`world/maps/bootstrap.py`** — delete the two hard-coded interior constant
  sets and the bespoke calls. `sync_service_interiors()` iterates
  `PLACE_REGISTRY`, groups by `settlement_key`, resolves each settlement's
  `zcoord`, and creates the tagged interior plus its two doorway exits. The
  existing "exterior missing → warn and skip" behaviour is kept.
  `XYMAP_DATA_LIST` grows to two maps.
- **`world/rules/guild_config.py`** — `validate_shop_configs` splits into
  assortment validation and per-place resolution; the completeness check is
  re-keyed on `shop_key` (§1.1); `validate_service_hosts` reads the derived
  roster instead of raw YAML.
- **`commands/economy.py:127`** — print the place's `room_name_zh`:
  `聖潔王都鍛造鋪（營業中）：`.
- **`world/rules/rulebook/guild_economy.yaml`** — the `shops:` block and the
  `service_hosts:` roster are removed; commerce moves to `commerce.yaml` and
  the roster becomes derived.

No changes to `world/rules/economy.py`, `typeclasses/components.py`, the
trade transaction, the affinity grant, the clock event sources, or
`service_gate.py`. The elven homes run the *identical* code path as the
capital's shops — the de-commercialized narrative requires no mechanical
branch, which is the central claim this change validates.

---

## 8. Testing

- **Assortment alignment** — a missing offer, a surplus offer, and an unknown
  `item_key` each fail catalog load.
- **Price scaling** — half-up rounding boundaries; a scaled price outside the
  `PRICE_TABLE` band fails; `scaled_sell > scaled_buy` fails; `scale` bounds
  (0, 1, 1000, 1001).
- **Override semantics** — an override is used verbatim and is *not* scaled;
  a partial override fails; an override naming an item the place does not
  offer fails; an `extra_item_keys` entry without an override fails.
- **Place row shape** — a `shop_key` with no assortments fails, and
  assortments on a place with no `shop_key` fails; a place whose
  `authored_kwargs` miss a blueprint component's identity field fails, and a
  surplus kwarg fails.
- **Completeness regression** — two shops where the second has no rules must
  fail, locking the `guild_config.py:227` defect.
- **Derivation** — `PLACE_REGISTRY` → `SHOP_REGISTRY` and → roster produce
  the expected rows; cross-registry authored-name uniqueness still fires on a
  planted collision.
- **Band migration** — every migrated item is purchasable; every retained
  `relic` item is still rejected by `buy`.
- **Same item, two prices** — buying `elven_spider_silk` in both settlements
  yields the same `item_key` at the two configured prices.
- **Bootstrap** — repeated sync is idempotent; both settlements' interiors
  and doorways appear; a missing exterior warns without raising.
- **Elven parity** — `buy`/`sell` against an elven home traverses the same
  API as a capital shop.

---

## 9. Future Hooks

- Remaining place types are additive `PlaceDefinition` rows.
- Remaining settlement archetypes (TOWN, PORT, BEAST_CITY, FRONTIER) need
  only a map module plus rows.
- A full 聖潔王都 redesign (王宮, 魔法學院, 貴族區 interiors) can replace
  the map module without touching the commerce layers.
- Outside-world prices above 500,000 copper require a band widening or
  location-scoped bands (§4.2).
- Restricting hidden-village access by race remains open (§6.2).
