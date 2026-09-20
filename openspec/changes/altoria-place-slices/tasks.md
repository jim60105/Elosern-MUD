## 1. The guard first

- [ ] 1.1 Capture the assembled `PLACE_REGISTRY` — keys and every field of every row — before
  the split, and write the test comparing it after. Moving rows between files by hand is
  where one disappears.

## 2. The split

- [ ] 2.1 Create `places_altoria_lower.py`, `places_altoria_middle.py` and
  `places_altoria_upper.py`, and delete `places_altoria.py`.
- [ ] 2.2 Distribute the five landed rows by terrace: 餐館 to lower; 公會, 雜貨店, 鍛造鋪 and
  裁縫坊 to middle.
- [ ] 2.3 Assemble all three in `places.py` alongside the village slice, following the
  existing assembly's shape and extending its slice-order comment to say why the order is
  what it is.
- [ ] 2.4 Change no row's content. If the diff shows a description, a coordinate or a host
  field, revert it.
- [ ] 2.5 The split reorders rows relative to each other, so the derived roster order
  changes. Search for a test asserting roster or place order and fix it deliberately rather
  than meeting it as a failure.

## 3. The doorway-collision rule

- [ ] 3.1 In `validate_place_registry`, reject two places that share an exterior and a
  doorway key, naming both places and the shared name.
- [ ] 3.2 Cover both sides over synthetic rows: two places on one exterior with different
  doorway names load and yield two doorways; the same name fails.
- [ ] 3.3 Confirm the shipped craft alley passes — the replan hand-checked it, and this is
  the check that makes that permanent.

## 4. Handoff

- [ ] 4.1 The assembled registry is identical to task 1.1's capture.
- [ ] 4.2 Run the lore settlements, guild-config and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
