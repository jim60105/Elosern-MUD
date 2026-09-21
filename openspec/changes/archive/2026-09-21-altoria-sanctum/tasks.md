## 1. The bundle

- [x] 1.1 Add `sanctum_wares` (聖所用品) holding the twelve `intimacy_tool` keys plus
  `baptismal_holy_water`.
- [x] 1.2 Remove `baptismal_holy_water` from `general_sundries`, leaving seventeen keys there.
- [x] 1.3 Move its offer row verbatim into the new section — same buy, sell, stock and restock.
- [x] 1.4 Price the twelve new rows **against each item's `PRICE_TABLE` band**, reading the
  band first. Resolved buy prices outside the band fail at load, so deriving the price from
  the band is faster than guessing and fixing.

## 2. The two places

- [x] 2.1 Add 聖潔王都光明神殿 off 大神殿前 `(4,4)`: host 艾莉安娜·寒水, title
  聖潔王都光明神殿主祭, human, female, profession `attendant`, its own `dialogue_key`, no
  assortments.
- [x] 2.2 Add 聖潔王都聖所 off the same exterior: host 羅海西亞·芬威克, title
  聖潔王都聖所執事, human, female, profession `merchant`, referencing `sanctum_wares`.
  Its doorway name must differ from the sanctuary's.
- [x] 2.2a Author the sanctuary as `PlaceKind.TEMPLE` and its shop as `PlaceKind.SANCTUM_SHOP`.
- [x] 2.3 Add the `shops:` row for the sanctum shop.
- [x] 2.4 Author a `dialogue_key` and a dialogue table for the deacon too — the `merchant`
  blueprint carries a dialogue component, so her place fails load without one. Her register
  is the same matter-of-fact one the sanctuary's requires.

## 3. The dialogue

- [x] 3.1 Author the sanctuary's dialogue table in `world/lore/dialogue/altoria.py`: a greeting
  and keywords covering worship, blessing, the ministry and the shop.
- [x] 3.2 Write it in the register the source document requires. Re-read line 326 before
  drafting — 「聖所以性愛為修道之途、公開經營妓院事業，在這個世界是**社會常識**」 and a
  framing of 「只有信眾知曉的隱密核心」 is named there as a wrong reading. The priest should
  answer a question about the sanctum the way an innkeeper answers a question about rooms.
- [x] 3.3 Land the dialogue row and the place row together. An authored `dialogue_key` with no
  table fails catalog load.

## 4. Coverage

- [x] 4.1 Both interiors exist off the one exterior with distinct doorways, and each leads
  back out.
- [x] 4.2 The two hosts' trade offices are disjoint — the sanctuary's host carries a
  scripted-dialogue component and no merchant component; the shop's host carries the
  merchant component (and, per the merchant blueprint, her own dialogue table), and the
  priest's table ships no trade guidance she could not execute.
- [x] 4.3 A player who has never visited can enter both and list the shop's stock with no
  lock, reveal or knowledge step consulted, and buying resolves through the ordinary merchant
  path. Search the trade path for a branch naming this shop, its settlement or its goods'
  kind and assert none exists.
- [x] 4.4 The capital's offered union is unchanged: 受洗聖水 is still purchasable in the
  capital, from a different counter.

## 5. The lore document

- [x] 5.1 Line 335: 「賽萊絲汀·晨曦」 → 艾莉安娜·寒水, 「維薇安·蜜語」 → 羅海西亞·芬威克.
- [x] 5.2 Line 146: 受洗聖水 no longer sits with the sundries.
- [x] 5.3 Run the lore, rules-commerce, guild-economy-sync and scripted-dialogue suites, the
  test-data lint, and `uv run --locked python -m tools.spec_traceability check`.
