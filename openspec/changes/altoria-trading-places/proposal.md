## Why

聖潔王都 has one shop, and it sells everything.

`docs/lore/settlement-locations.md:146` says so outright and calls it a
development shortcut: 「目前落地的『阿爾托利亞雜貨商店』事實上身兼雜貨、武器、防具、
飾品、藥劑等所有品項。這是開發初期把所有商店機制塞進一間店的暫定作法，本文建議未來把它拆成
雜貨店與下方各專門店，各自對應更貼近世界觀的產地敘事。」

A capital where the blacksmith's forge is a locked exterior and the armour
comes off a general-store shelf has no production narrative. The lore
document gives each specialist location its own trade, its own craftsman and
its own place in the city, and none of that exists.

The infrastructure now does. Assortments already group the general store's
goods along the axis the specialists need, and a place is one authored row.
What remains is content.

The map needs no work: every exterior this change attaches to already exists
in the thirteen-node grid — 鐵匠鋪外 at (0,2), 南大道 at (2,1) and 北大道 at
(2,3). A full capital redesign (王宮, 魔法學院, 貴族區 interiors) is a
separate future change and is deliberately not attempted here.

## What Changes

- Add three trading places to 聖潔王都, each an authored place row with its
  own interior, host and goods:
  - **聖潔王都鍛造鋪** off 鐵匠鋪外 (0,2), host 維爾登·黑潭
    (`聖潔王都鍛造鋪鐵匠`), selling the weapons assortment.
  - **聖潔王都餐館** off 南大道 (2,1), host 西格瑪·庫柏
    (`聖潔王都餐館老闆`), selling the food assortment.
  - **聖潔王都裁縫坊** off 北大道 (2,3), host 妮絲塔·狐溪
    (`聖潔王都裁縫坊坊主`), selling the armour assortment.
- Narrow 阿爾托利亞雜貨商店 to the remaining sundries assortment. The
  capital's total item coverage is unchanged — every key one of the three
  specialists takes on, the general store gives up — so no equipment becomes
  unobtainable while 首飾店 and 鍊金坊 are still unbuilt.
- Names are rolled from the project's fantasy name corpus and chosen so the
  etymology fits the trade: Blackmere reads as a quenching pool, Cooper is a
  barrel-maker whose family trade became an eatery, Foxbourne carries both
  the fur and the streamside fulling. Registry names use U+00B7 `·`, the
  authored convention, not the generator's U+30FB.
- **BREAKING** (authored lore text): `docs/lore/settlement-locations.md`
  names 霍布·熔爐 (line 170) and 柯爾特·暖爐 (line 265) as the capital's
  smith and eatery owner. Those examples are replaced by the rolled names so
  the document and the registry agree.

## Capabilities

### Modified Capabilities

- `sample-city-altoria`: the "xyzgrid remains thirteen exterior nodes while
  permanent service interiors are attached" requirement changes its count
  and its enumeration — five permanent interiors rather than two, each named
  by a place record rather than by the requirement text. The thirteen
  coordinates, twelve links, tree topology and sole AnchorRoom are
  unchanged, which is the part of the requirement that matters.

## Impact

- `world/lore/settlements/places_altoria.py` — three new place rows; the
  general store's assortment reference narrows to sundries.
- `world/rules/rulebook/commerce.yaml` — three new shop rows carrying hours.
  No new assortment: `commerce-assortment-registry` already split the goods
  along this axis.
- `docs/lore/settlement-locations.md` — two host names corrected.
- `world/maps/altoria_capital.py` — unchanged. No new exterior is needed.
- `world/lore/wilderness_entry.py`, `world/maps/city_gates.py`,
  `world/lore/anchor_placement.py` — unchanged.
- **Depends on `settlement-place-registry`** for the place row, and on
  `commerce-assortment-registry` for the assortments it references.
- **Conflicts with `ciaran-village-commerce`** on
  `world/rules/rulebook/commerce.yaml` only, as disjoint appended rows;
  places live in separate per-settlement modules and do not collide.
