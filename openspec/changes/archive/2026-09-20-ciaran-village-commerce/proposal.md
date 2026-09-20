## Why

暗影谷村 is walkable and empty. A player can reach it, walk its six rooms,
and do nothing there.

`docs/lore/settlement-locations.md:490` sets an explicit floor for this
settlement: 「玩家必須能像在人類的城鎮一樣在精靈村落裡買賣、補給、休息，而不是走進一座
只能觀賞的空景。」 An elven village has no guild, no temple, no bathhouse, no
walls and — crucially — no shops. And it must still be fully playable. The
document resolves the tension the same way each time: 「地點機能由擅長該事項的
個別精靈在家中承擔」. Someone who likes forging handles the village's blades;
someone who likes cooking handles its food. Their premises are their homes.
It is sharing an interest, not running a business.

That is a narrative claim with a mechanical consequence worth proving: it
must cost **nothing**. If de-commercialising a settlement requires a code
branch, a second trade path, or a special-case host type, the place
abstraction is wrong. Four elven homes running the identical `merchant`
component through the identical `buy`/`sell` transaction as a capital shop —
differing only in authored data — is the demonstration this whole design
rests on.

## What Changes

- Register 暗影谷村 as a settlement of the elven-village archetype.
- Add four places, each a villager's home rather than a premises. Room names
  are 「⟨given name⟩的家」, because the full 名·姓 form is unwieldy and is not
  how a village refers to a neighbour's house:
  - **海莉爾的家** off 練刀場 — 海莉爾·斯塔爾法爾, `暗影谷村鑄刃者`, blades.
  - **拉瑞內斯的家** off 溪畔小徑 — 拉瑞內斯·妮特布倫, `暗影谷村花饌好手`, food.
  - **瓦爾溫的家** off 村北古樹下 — 瓦爾溫·斯蒂爾瓦特爾, `暗影谷村蒐羅者`,
    sundries and materials.
  - **維特希爾的家** off 織房坡 — 維特希爾·威爾德布瑞亞爾, `暗影谷村織衣者`,
    garments.
- All four hosts are elves of the `ciaran` subrace and female. Their titles
  deliberately avoid 老闆 and 店主: those words denote commercial
  establishments, which this settlement does not have.
- Add four assortments of elven craft. They are the first consumers of the
  `masterwork_gear` band, which is what makes elven blades, garments and
  jewellery purchasable at an everyday village price at all.
- Demonstrate location-dependent pricing on one shared good.
  `elven_spider_silk` is **already** offered by the capital's general store,
  at 60,000 copper (`guild_economy.yaml:261` today, carried into the sundries
  assortment by `commerce-assortment-registry`). This change adds it to the
  village collector's assortment at an everyday village price. One item key
  and one item definition; two assortments; two prices three orders of
  magnitude apart.
  No override, no stocked addition and no exclusion are involved: two shops
  referencing two different assortments that each contain the key is the
  mechanism working as designed. The duplicate rejection this design
  introduces is scoped to one shop referencing two assortments that overlap,
  which this is not.

## Capabilities

### New Capabilities

- `ciaran-village-commerce`: the village's trading places as private homes,
  its elven-craft goods, and the guarantee that trading in a settlement with
  no commerce traverses exactly the same path as trading in one with shops.

### Modified Capabilities

None. Every mechanism this change uses — places, assortments, scaling and
overrides, authored host race and sex, the masterwork band — is delivered by
its dependencies. This change is content that exercises them.

## Impact

- `world/lore/settlements/places_ciaran.py` — new module with four place
  rows.
- `world/lore/settlements/settlements.py` — the `village_ciaran` settlement
  row.
- `world/rules/rulebook/commerce.yaml` — four elven assortments and four
  shop rows. The capital's existing `elven_spider_silk` offer is left exactly
  as it is.
- `world/lore/settlements/places_altoria.py` — **untouched.** An earlier
  draft of this change added the silk to the capital as a stocked addition;
  that was wrong, because the capital has always offered it.
- No map change. `ciaran-village-map` built every exterior this attaches to.
- No change to `world/rules/economy.py`, `commands/economy.py` or
  `typeclasses/components.py` — which is the point.
- **Depends on** `masterwork-gear-price-band` (the craft goods must be
  sellable), `settlement-place-registry` (the place row and its authored
  host race/subrace/sex fields), `place-driven-service-sync` (which is what
  applies those fields and builds the interiors),
  `commerce-assortment-registry` (assortments) and `ciaran-village-map`
  (the exteriors). It does **not** depend on
  `place-price-scaling`: with the two-assortment approach this change needs
  no scale and no override.
- **Conflicts with `altoria-trading-places`** on
  `world/rules/rulebook/commerce.yaml` only, as disjoint appended rows.
  Places live in separate per-settlement modules and do not collide at all.
