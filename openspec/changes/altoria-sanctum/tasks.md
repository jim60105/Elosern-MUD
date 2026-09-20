## 1. The bundle

- [ ] 1.1 Add `sanctum_wares` (聖所用品) holding the twelve `intimacy_tool` keys plus
  `baptismal_holy_water`.
- [ ] 1.2 Remove `baptismal_holy_water` from `general_sundries`, leaving seventeen keys there.
- [ ] 1.3 Move its offer row verbatim into the new section — same buy, sell, stock and restock.
- [ ] 1.4 Price the twelve new rows **against each item's `PRICE_TABLE` band**, reading the
  band first. Resolved buy prices outside the band fail at load, so deriving the price from
  the band is faster than guessing and fixing.

## 2. The two places

- [ ] 2.1 Add 聖潔王都光明神殿 off 大神殿前 `(4,4)`: host 艾莉安娜·寒水, title
  聖潔王都光明神殿主祭, human, female, profession `attendant`, its own `dialogue_key`, no
  assortments.
- [ ] 2.2 Add 聖潔王都聖所 off the same exterior: host 羅海西亞·芬威克, title
  聖潔王都聖所執事, human, female, profession `merchant`, referencing `sanctum_wares`.
  Its doorway name must differ from the sanctuary's.
- [ ] 2.2a Author the sanctuary as `PlaceKind.TEMPLE` and its shop as `PlaceKind.SANCTUM_SHOP`.
- [ ] 2.3 Add the `shops:` row for the sanctum shop.
- [ ] 2.4 Author a `dialogue_key` and a dialogue table for the deacon too — the `merchant`
  blueprint carries a dialogue component, so her place fails load without one. Her register
  is the same matter-of-fact one the sanctuary's requires.

## 3. The dialogue

- [ ] 3.1 Author the sanctuary's dialogue table in `world/lore/dialogue/altoria.py`: a greeting
  and keywords covering worship, blessing, the ministry and the shop.
- [ ] 3.2 Write it in the register the source document requires. Re-read line 326 before
  drafting — 「聖所以性愛為修道之途、公開經營妓院事業，在這個世界是**社會常識**」 and a
  framing of 「只有信眾知曉的隱密核心」 is named there as a wrong reading. The priest should
  answer a question about the sanctum the way an innkeeper answers a question about rooms.
- [ ] 3.3 Land the dialogue row and the place row together. An authored `dialogue_key` with no
  table fails catalog load.

## 4. Coverage

- [ ] 4.1 Both interiors exist off the one exterior with distinct doorways, and each leads
  back out.
- [ ] 4.2 The two hosts carry disjoint capabilities — dialogue and no merchant, merchant and
  no dialogue.
- [ ] 4.3 A player who has never visited can enter both and list the shop's stock with no
  lock, reveal or knowledge step consulted, and buying resolves through the ordinary merchant
  path. Search the trade path for a branch naming this shop, its settlement or its goods'
  kind and assert none exists.
- [ ] 4.4 The capital's offered union is unchanged: 受洗聖水 is still purchasable in the
  capital, from a different counter.

## 5. The lore document

- [ ] 5.1 Line 335: 「賽萊絲汀·晨曦」 → 艾莉安娜·寒水, 「維薇安·蜜語」 → 羅海西亞·芬威克.
- [ ] 5.2 Line 146: 受洗聖水 no longer sits with the sundries.
- [ ] 5.3 Run the lore, rules-commerce, guild-economy-sync and scripted-dialogue suites, the
  test-data lint, and `uv run --locked python -m tools.spec_traceability check`.
