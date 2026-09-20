## 1. Ordering

- [ ] 1.1 This change lands after `altoria-capital-replan` and `ciaran-village-crafts`. Both
  rewrite their map module's descriptions in Traditional Chinese; the guard in task 3 fails
  if either has not landed. Confirm both are in before starting.

## 2. The nine descriptions

- [ ] 2.1 Convert the five `room_desc_zh` values in `places_altoria.py` to Traditional
  Chinese. Say what the English said — this is a conversion, not a rewrite, and a reviewer
  should be able to check it line for line.
- [ ] 2.2 Convert the four in `places_ciaran.py`. These are elven homes; the register should
  match the village's map prose rather than the capital's.
- [ ] 2.3 Drop the parenthetical spec references some descriptions carry (「(guild-economy
  D-9)」 and similar). They are authoring notes that leaked into player-facing text.

## 3. The rule and the guard

- [ ] 3.1 Add the requirement to `grid-room-sync` that authored room prose is Traditional
  Chinese and that a room's name and description are in the same language.
- [ ] 3.2 Write the guard over every authored room description — the grid prototypes in both
  map modules and every place's interior description. Predominantly Han, with no
  sentence-length run of English words.
- [ ] 3.3 Tune the run-length threshold against the converted corpus, not before it. Record
  the chosen threshold and why in a comment.

## 4. Coverage

- [ ] 4.1 The guard fails on a synthetic English description and passes on the shipped corpus.
- [ ] 4.2 Run the lore, maps and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
