## Why

`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` lands trading
places in 暗影谷村, whose four hosts sell 基亞蘭族 craft. Every one of those
goods is unsellable today.

`shadow_blade`, `shadow_blade_echo`, `dark_elf_kimono`, `dark_elf_ninja_garb`,
`elven_traditional_robe` and `crescent_earring` all declare
`price_table_key="relic"` — a band whose floor is 999,999 copper and whose
note reads "One-of-a-kind keepsake, never traded" — together with
`sellable=False`. An elven weaponsmith's assortment would contain zero legal
items.

The data already contradicts itself: `dark_elf_kimono`'s own
`summary_zh` reads 「精靈的墨黑短袍傳統服飾⋯⋯精靈村商店的**現成品**」 while
sitting in the band that forbids trade.

The band was wrong because it encoded a market fact as a property of the
object. A 暗影鋼刀 is an excellent steel blade; it is expensive *outside* an
elven village because elves do not trade outward, not because the blade is a
unique keepsake. Price bands describe what a thing is. Scarcity is priced by
the shop.

No band can currently express this. `mundane_weapon` caps at 2,000 copper and
`armor` at 5,000 — neither reaches an outside-world price — while the next
weapon band, `magic_weapon`, does not start until 100,000. The 2,000–100,000
range is empty.

## What Changes

- Add a `masterwork_gear` price band spanning 100 to 500,000 copper for
  master-crafted goods whose price is set by scarcity rather than materials:
  ordinary inside the maker's own community, extraordinary outside it. The
  floor admits an in-village everyday price; the ceiling stays below
  `relic`'s 999,999 floor so the keepsake band is not eroded. The key is
  deliberately race-neutral so human master smiths and beastfolk tribal
  artisans fit it later.
- **BREAKING** (authored item identity): seven items change band, and the six
  leaving `relic` also flip `sellable` to `True` — `shadow_blade`,
  `shadow_blade_echo`, `dark_elf_kimono`, `dark_elf_ninja_garb`,
  `elven_traditional_robe`, `crescent_earring` (from `relic`) and
  `elven_forest_veil` (from `armor`, already sellable).
- State that a keepsake-band item is never shelvable. The **enforcement** of
  that rule lives in `commerce-assortment-registry`, which owns the validator
  that would carry it — see Impact.
- Raise the rarity of three elven goods so the registry reflects that elves
  produce epic work as daily output: `elven_candied_blossom` and
  `prism_charm` UNCOMMON → RARE, `elven_longbow` RARE → EPIC. Rarity is
  presentation-only and never enters price validation.
- Nine genuinely one-of-a-kind items stay in `relic`:
  `family_crest_token`, `ancient_mystery_key`, `royal_signet_ring`,
  `royal_heirloom_pendant`, `rose_crest_rapier`, `silver_feather_earring`,
  `black_maid_dress`, `elven_child_toy`, `guild_recruit_badge`.

## Capabilities

### New Capabilities

- `masterwork-price-band`: what the `masterwork_gear` band means, what may
  sit in it, and the complementary rule that a `relic`-band item can never be
  offered for sale.

### Modified Capabilities

None. `lore-item-catalog`'s existing rules are unchanged: a non-sellable item
still cannot be traded, and a registered item still does not become
purchasable merely by existing. This change edits which band and flag seven
authored rows carry, not the rules that read them.

## Impact

- `world/lore/economy.py` — one new `PRICE_TABLE` entry.
- `world/lore/items/data_named_equipment.py` — six rows change band and
  `sellable` (`dark_elf_kimono`, `shadow_blade`, `shadow_blade_echo`,
  `dark_elf_ninja_garb`, `crescent_earring`, `elven_traditional_robe`).
- `world/lore/items/data_armor_accessories_materials.py` — `prism_charm`
  rarity.
- `world/lore/items/data_regional_equipment.py` — `elven_longbow` rarity and
  `elven_forest_veil` band. (`elven_traditional_robe` is defined in
  `data_named_equipment.py:71`, not here.)
- `world/lore/items/data_inspect_only_codex.py` — `elven_candied_blossom`
  rarity.
- `world/rules/guild_config.py` — **not touched.** The keepsake-offer
  rejection belongs in the goods-list validator that
  `commerce-assortment-registry` rewrites wholesale. Enforcing it here would
  put two changes inside `validate_shop_configs`, and whichever landed second
  would have to re-apply its edit over the other's restructuring — exactly how
  a fail-closed check silently becomes a no-op, which is the defect this
  design set already found once. The rule is stated here and enforced there,
  so this change and `commerce-assortment-registry` share no file.
- `world/lore/tests/` — band coverage.
- No shipped shop offers a `relic`-band item, so the rule starts satisfied.
