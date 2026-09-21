## 1. The two staffed places

- [x] 1.1 Add 聖潔王都王立魔法學院 off 學院前 `(5,5)`: host 奧德溫·薩契, title
  聖潔王都魔法學院院長, human, male, `attendant`.
- [x] 1.2 Add 聖潔王都商會公所 off 東市 `(5,3)`: host 尤斯汀·柯德溫, title
  聖潔王都商會會長, human, male, `attendant`. Its doorway name must differ from the
  alchemist's on that exterior.

## 2. The host-less stalls

- [x] 2.1 Add 聖潔王都市集棚 off 市場街 `(2,3)` with no host fields. Its doorway name must
  differ from both the general store's and the jeweller's — that exterior now carries three.
- [x] 2.1a Author the three as `PlaceKind.ACADEMY`, `PlaceKind.MERCHANT_HALL` and `PlaceKind.MARKET`.
- [x] 2.2 Author its description as covered ground between other people's counters, the kind
  of place a transient stallholder would later be spawned into.

## 3. The dialogue

- [x] 3.1 Author the academy table with real subject matter: read the magic-rank and element
  vocabularies from lore first and answer from them, rather than inventing parallel prose.
  Keywords at minimum for ranks and for elements.
- [x] 3.2 Author the merchant hall table. The guild master may speak about caravans and trade
  routes as world-building; he must not offer work, quote a commission, or imply escort
  contracts can be taken.
- [x] 3.3 Land each table with its place row.

## 4. The two refusals

- [x] 4.1 Add no skill-granting or teaching path at the academy. Cover it: no new command
  grants a skill and the host exposes no such capability.
- [x] 4.2 Add no commission or caravan-board surface at the merchant hall. Cover it: the host
  carries no quest-issuer component and no new work-listing command exists.

## 5. Coverage and the lore document

- [x] 5.1 All three interiors exist once and are reachable both ways; two hold a
  dialogue-carrying host, the stalls hold none.
- [x] 5.2 The academy host answers on both ranks and elements.
- [x] 5.3 市場街 resolves three distinct doorways and 東市 two.
- [x] 5.4 Lines 245 and 456: 「達里歐·秤金」 → 尤斯汀·柯德溫, 「艾德蒙·星辰」 → 奧德溫·薩契.
- [x] 5.5 Run the lore, guild-economy-sync and scripted-dialogue suites plus
  `uv run --locked python -m tools.spec_traceability check`.
