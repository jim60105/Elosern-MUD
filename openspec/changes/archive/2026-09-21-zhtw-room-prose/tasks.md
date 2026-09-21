## 1. Ordering

- [x] 1.1 This change lands after `altoria-capital-replan` and `ciaran-village-crafts`. Both
  rewrite their map module's descriptions in Traditional Chinese; the guard in task 3 fails
  if either has not landed. Confirm both are in before starting.

## 2. The authored descriptions

Scope note: the proposal was written before the places slice split and the capital replan.
The English-authored descriptions actually shipped are twenty-eight interior
`room_desc_zh` values across `places_altoria_lower.py` / `places_altoria_middle.py` /
`places_altoria_upper.py` / `places_ciaran.py`, plus twenty-one grid `desc` values in
`altoria_capital.py` (the replan authored those in English too). `village_ciaran.py` is
untouched: its rooms were authored in Chinese by the replan/crafts changes.

- [x] 2.1 Convert the interior `room_desc_zh` values in the three Altoria place slices to
  Traditional Chinese. Say what the English said — this is a conversion, not a rewrite, and
  a reviewer should be able to check it line for line.
- [x] 2.2 Convert the elven-village interiors in `places_ciaran.py`. These are elven homes;
  the register should match the village's map prose rather than the capital's.
- [x] 2.3 Convert the capital grid `desc` values in `altoria_capital.py` (drift approved by
  Main; the delta requirement covers every shipped authored description, grid included).
- [x] 2.4 Drop the parenthetical spec references some descriptions carried (「(guild-economy
  D-9)」 and similar). They are authoring notes that leaked into player-facing text.

## 3. The rule and the guard

- [x] 3.1 Add the requirement to `grid-room-sync` that authored room prose is Traditional
  Chinese and that a room's name and description are in the same language.
- [x] 3.2 Write the guard over every authored room description — the grid prototypes in both
  map modules and every place's interior description. Predominantly Han, with no
  sentence-length run of English words.
- [x] 3.3 Tune the run-length threshold against the converted corpus, not before it. Record
  the chosen threshold and why in a comment.

## 4. Coverage

- [x] 4.1 The guard fails on a synthetic English description and passes on the shipped corpus.
- [x] 4.2 Run the lore, maps and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
