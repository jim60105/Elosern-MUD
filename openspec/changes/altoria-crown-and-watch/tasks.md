## 1. The palace

- [ ] 1.1 Add 聖潔王都王宮 off 王宮前庭 `(4,6)` as a host-less place: no host fields, no
  profession, no service id, no assortments.
- [ ] 1.2 Author its description as a throne approach that is plainly the edge of what is
  built — grand, and waiting. Do not write a scene into it.
- [ ] 1.3 Assert it exists once after one sync and still once after two, with no host either
  time. Those are two different failures.

## 2. The three staffed places

- [ ] 2.1 Add 聖潔王都貴族區衛所 off 貴族區前 `(3,5)`: host 古利安·鷹守, title
  聖潔王都貴族區衛隊長, human, male, `attendant`.
- [ ] 2.2 Add 聖潔王都衛兵駐所 off 南門 `(3,0)`: host 托瓦德·鄧堡, title
  聖潔王都衛兵隊隊長, human, male, `attendant`.
- [ ] 2.3 Add 聖潔王都校場 off 校場外 `(2,4)`: host 伊沃·高丘, title 聖潔王都訓練場教頭,
  human, male, `attendant`.
- [ ] 2.3a Author the four as `PlaceKind.PALACE`, `PlaceKind.WATCH_POST` (both watch posts) and `PlaceKind.TRAINING_GROUND`.
- [ ] 2.4 Author the three dialogue tables, each landed with its place row. The instructor's
  lines name `rest` plus `practice` and `guild exam`; the gate captain's orient a player
  arriving through the south gate; the noble-quarter captain's make clear the quarter is open
  and that there is simply nothing to petition for yet.

## 3. The two refusals

- [ ] 3.1 Add no lock, rank check or quest prerequisite to the palace or the noble quarter.
  Cover it: a player with no rank, no quest and no prior visit enters both.
- [ ] 3.2 Add no bounty board and no work-listing surface. Cover it: the guardhouse host
  carries no quest-issuer component and no new command exists.

## 4. Coverage and the lore document

- [ ] 4.1 All four interiors exist once and are reachable both ways; three hold a
  dialogue-carrying host and the palace holds none.
- [ ] 4.2 Lines 395, 412, 433: 「戴斯蒙·磐石」 → 古利安·鷹守, 「凱爾文·堅盾」 → 托瓦德·鄧堡,
  「羅蘭·練兵」 → 伊沃·高丘.
- [ ] 4.3 Run the lore, guild-economy-sync and scripted-dialogue suites plus
  `uv run --locked python -m tools.spec_traceability check`.
