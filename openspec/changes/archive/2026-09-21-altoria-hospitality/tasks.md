## 1. The three places

- [x] 1.1 Add 聖潔王都醉月酒館 off 客棧巷 `(4,1)`: host 蘿溫·古橡, title 聖潔王都酒館老闆,
  human, female, `attendant`, no assortments.
- [x] 1.2 Add 聖潔王都爐火旅店 off the same exterior: host 溫弗蕾德·古林, title
  聖潔王都旅店老闆娘, human, female, `attendant`. Give it a doorway name distinct from the
  tavern's — they share the lane.
- [x] 1.3 Add 聖潔王都公共浴場 off 浴場前 `(5,1)`: host 伊莎貝爾·葦沼, title
  聖潔王都公共浴場管理員, human, female, `attendant`.
- [x] 1.3a Author the three as `PlaceKind.TAVERN`, `PlaceKind.LODGING` and `PlaceKind.BATHHOUSE`.
- [x] 1.4 Author the three room descriptions. The bathhouse's should carry the nudity-ethics
  contrast the document calls a narrative hook, visibly enough that a later scene can use it.

## 2. The three dialogue tables

- [x] 2.1 Author each in `world/lore/dialogue/altoria.py`, landed in the same commit as its place
  row — an authored `dialogue_key` with no table fails catalog load.
- [x] 2.2 The innkeeper's lines name `rest`, `sleep` and `practice`; the tavern keeper's name
  `talk` and `invite`; the bathhouse keeper's explain the separated sides. Follow the guild
  staff table's shape: a greeting that orients, then keyword responses.
- [x] 2.3 Do not promise anything unimplemented. The innkeeper must not quote a nightly rate,
  the tavern keeper must not offer a drink that does something.

## 3. Coverage

- [x] 3.1 All three interiors exist once, are reachable both ways, and each holds one
  dialogue-carrying host.
- [x] 3.2 The two lane places produce two distinct doorways on the shared exterior.
- [x] 3.3 Resting and practising inside the inn and outside it give identical outcomes and
  identical clock cost, and no charge is taken.
- [x] 3.4 Compare the command set and the persisted attribute set before and after this change
  and assert both are unchanged. This is the anti-scope-creep gate.
- [x] 3.5 Talking to the innkeeper and the tavern keeper surfaces their commands.

## 4. The lore document

- [x] 4.1 Line 287: 「布蘭卡·醉月」 → 蘿溫·古橡. Line 310: 「蘿莎琳·爐火」 → 溫弗蕾德·古林.
  Line 354: 「彭妮·皂花」 → 伊莎貝爾·葦沼.
- [x] 4.2 Run the lore, guild-economy-sync and scripted-dialogue suites plus
  `uv run --locked python -m tools.spec_traceability check`.
