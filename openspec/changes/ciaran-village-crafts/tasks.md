## 1. The map

- [ ] 1.1 Add the four prototypes and extend `MAPSTR` to the ten-node layout in `design.md`.
  Confirm with `XYMap.parse()` that it is ten nodes, nine links, connected and acyclic, and
  that the six original coordinates are unchanged before anything else is written.
- [ ] 1.2 Author the four descriptions. They are Traditional Chinese, which is what
  `village-ciaran-map` requires. **The six existing descriptions are English and in violation
  of that requirement** — convert them in this change so the file is consistent and the spec
  is true of it.
- [ ] 1.3 The wilderness footprint and the entrance node are unchanged, so
  `WILDERNESS_ENTRY_REGISTRY` and `CITY_GATE_REGISTRY` need no edit. Confirm
  `validate_wilderness_entries()` still passes rather than assuming it.

## 2. The two bundles

- [ ] 2.1 Add `elven_adornments` (精靈綴飾) holding `prism_charm` and `crescent_earring`, and
  `elven_remedies` (精靈調藥) holding the restorative potions.
- [ ] 2.2 Remove `crescent_earring` from `elven_sundries` and move its offer row verbatim.
  After the move exactly one village shop offers the key — the per-shop overlap rule depends
  on it.
- [ ] 2.3 Price the remedies at the village's everyday scale, inside each item's band. These
  are what a villager keeps on a shelf, not what an outsider would pay.

## 3. The two homes

- [ ] 3.1 Add 格威娜拉的家 off 銀葉坡 `(2,3)`: host 格威娜拉·希爾維爾莉夫, title
  暗影谷村綴飾者, elf, `ciaran`, female, `merchant`, referencing `elven_adornments`.
- [ ] 3.2 Add 妮瑞斯的家 off 藥草園 `(3,1)`: host 妮瑞斯·米斯特瓦勒, title 暗影谷村調藥者,
  elf, `ciaran`, female, `merchant`, referencing `elven_remedies`.
- [ ] 3.2a Author both as `PlaceKind.HOME`. They are dwellings whose occupants trade, which is what the kind rule is for.
- [ ] 3.3 Room names follow the village convention 「⟨given name⟩的家」, and neither title
  says shopkeeper.
- [ ] 3.4 Add both `shops:` rows with the village's hours.
- [ ] 3.5 Author a `dialogue_key` and a dialogue table for each host in
  `world/lore/dialogue/ciaran.py`. They speak as villagers sharing what they make, not as
  proprietors — the register rule the merchant-dialogue change establishes.

## 4. Coverage

- [ ] 4.1 The map is a ten-node tree and the original six coordinates are unmoved.
- [ ] 4.2 Both homes trade through the ordinary path; search the trade path for a branch on
  settlement or archetype and assert none exists.
- [ ] 4.3 The two-price rule over a key offered in both settlements: the resolved prices
  differ and the two acquired items are the same definition. Use the shipped shared key —
  this is one of the existing tagged data-contract tests' territory, so extend that rather
  than adding an untagged test naming shipped content.
- [ ] 4.4 `crescent_earring` is offered by exactly one village shop after the move, at the
  price it had before.

## 5. The lore document

- [ ] 5.1 Lines 214 and 232 gain the authored host names for the two villagers they describe.
- [ ] 5.2 Record in the 旅店 section, or in this change's design, that the elven village
  deliberately has no lodging place despite the matrix's 「變」, and why.
- [ ] 5.3 Run the maps, lore, rules-commerce and guild-economy-sync suites, the test-data
  lint, and `uv run --locked python -m tools.spec_traceability check`.
