## 1. The two bundles

- [x] 1.1 Add `capital_adornments` (王都飾品) to the assortment registry holding exactly the
  eleven accessory-slot keys the capital sells, and `capital_remedies` (王都藥劑) holding the
  six remedies. Derive the eleven from `equipment_slot`, do not transcribe them from this
  document — the rule is the source, the list is its output.
- [x] 1.2 Remove those seventeen keys from `general_sundries`, leaving eighteen: the tools, the
  raw materials, and 受洗聖水, which stays until the sanctuary change moves it.

## 2. The offers

- [x] 2.1 Move the seventeen offer rows in `rulebook/commerce/altoria.yaml` (the capital slice;
  the monolith was split by `commerce-rulebook-slices`) into the two new assortment sections.
  Copy every field unchanged — buy, sell, max stock, initial stock, restock.
- [x] 2.2 Before anything else in this section, write the test that compares each moved item's
  resolved offer before and after. Seventeen hand-moved rows is where a digit goes missing.

## 3. The two places

- [x] 3.1 Add 聖潔王都首飾坊 off 市場街 `(2,3)`, host 艾蓮娜·鴉丘, title 聖潔王都首飾坊主,
  human, female, `merchant`, referencing `capital_adornments`. Its doorway name must not
  collide with the general store's or the stalls' on that same exterior.
- [x] 3.2 Add 聖潔王都鍊金坊 off 東市 `(5,3)`, host 希碧拉·灰沼, title 聖潔王都鍊金坊主,
  human, female, `merchant`, referencing `capital_remedies`.
- [x] 3.2a Author the two places as `PlaceKind.JEWELLER` and `PlaceKind.ALCHEMIST`.
- [x] 3.3 Add both `shops:` rows to the commerce rulebook with opening hours matching the
  other capital shops.
- [x] 3.4 Author a `dialogue_key` and a dialogue table for each of the two hosts. The
  `merchant` blueprint carries a dialogue component, so a merchant place without one fails
  load. The jeweller answers about gemwork and settings, the alchemist about what each
  remedy does.

## 4. Coverage

- [x] 4.1 Pin the partition rule: the capital's accessory-slot keys equal the adornments
  bundle's keys exactly, computed from both sides rather than asserted against a literal list.
- [x] 4.2 Pin that the union of every capital place's goods is unchanged by this change — the
  capital sells neither more nor less, only from different counters.
- [x] 4.3 Both new shops are reachable, open and tradeable through the ordinary command path,
  with the stock listing naming each shop's own room.

## 5. The lore document

- [x] 5.1 Line 206: 「奧莉薇亞·晶琢」 → 艾蓮娜·鴉丘. Line 224: 「賽菲拉·藥缽」 → 希碧拉·灰沼.
- [x] 5.2 Line 146 promises this split is still pending. Rewrite it to record that it landed,
  and that 受洗聖水 now sits with the sundries only until the sanctuary opens.
- [x] 5.3 Run the lore, rules-commerce and guild-economy-sync suites, plus the test-data lint
  and `uv run --locked python -m tools.spec_traceability check`.
