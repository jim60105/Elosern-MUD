## 1. The communal shelter

- [ ] 1.1 Add 共食棚 off 村中廣場 `(1,1)` with no host fields, no profession, no assortments.
- [ ] 1.1a Author the shelter as `PlaceKind.COMMONS`, and the instructor's and elder's dwellings as `PlaceKind.HOME`.
- [ ] 1.2 Author its description as a shared roof over shared food — no counter, no server,
  no prices anywhere in the text.
- [ ] 1.3 Assert it exists once after one sync and still once after two, with no host either
  time.

## 2. The instructor

- [ ] 2.1 Add 泰莉爾的家 off 練刀場 `(2,1)`: host 泰莉爾·菲溫德, title 暗影谷村刀術導師,
  elf, `ciaran`, female, `attendant`. Give it a doorway name distinct from 海莉爾的家's —
  they share the clearing.
- [ ] 2.2 Author her dialogue: the branch's sword culture, and `rest` plus `practice` as how
  a player actually trains. She teaches nothing directly and must not imply she can.

## 3. The elder

- [ ] 3.1 Add 艾莉妮斯的家 off 長老古樹下 `(1,3)`: host 艾莉妮斯·達恩斯特瑞德爾, title
  暗影谷村長老, elf, `ciaran`, female, `attendant`.
- [ ] 3.2 Author her dialogue as memory rather than office: the branch, the forest, the
  village's past. No petition, no permission, no council business, no commission.
- [ ] 3.3 Do not invent elven religious content. The document states elven faith is not shown
  to outsiders and warns against designing a temple for them; her lines must respect that
  silence rather than fill it.

## 4. Coverage

- [ ] 4.1 All three interiors exist once and are reachable both ways; two hold a
  dialogue-carrying host and the shelter holds none.
- [ ] 4.2 練刀場 resolves two distinct doorways.
- [ ] 4.3 No merchant capability exists at any of the three.
- [ ] 4.4 The elder's host carries no quest-issuer capability and entering her dwelling
  consults no lock or prerequisite.
- [ ] 4.5 The command set and persisted attribute set are unchanged before and after.

## 5. The lore document

- [ ] 5.1 Add the authored names to the elven-village notes in the 訓練場 section (line 441)
  and the 貴族區／統治機構 section (line 402).
- [ ] 5.2 Run the lore, guild-economy-sync and scripted-dialogue suites plus
  `uv run --locked python -m tools.spec_traceability check`.
