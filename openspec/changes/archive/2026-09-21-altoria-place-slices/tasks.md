## 1. The guard first

- [x] 1.1 Capture the assembled `PLACE_REGISTRY` — keys and every field of every row — before
  the split, and write the test comparing it after. Moving rows between files by hand is
  where one disappears.
  Landed as `PRE_SPLIT_CONTENT_CAPTURE` + `test_the_assembled_registry_equals_the_pre_split_capture`
  in `world/lore/tests/test_settlements.py`, keyed by place key (a live-field dump transcribed
  verbatim) so the deliberate reorder cannot weaken it. Committed before the split.

## 2. The split

- [x] 2.1 Create `places_altoria_lower.py`, `places_altoria_middle.py` and
  `places_altoria_upper.py`, and delete `places_altoria.py`.
- [x] 2.2 Distribute the five landed rows by terrace: 餐館 to lower; 公會, 雜貨店, 鍛造鋪 and
  裁縫坊 to middle. (Upper ships empty — its rows arrive with the sanctum change.)
- [x] 2.3 Assemble all three in `places.py` alongside the village slice, following the
  existing assembly's shape and extending its slice-order comment to say why the order is
  what it is.
- [x] 2.4 Change no row's content. If the diff shows a description, a coordinate or a host
  field, revert it. — The pre-split capture (1.1) passed unchanged through the split commit.
- [x] 2.5 The split reorders rows relative to each other, so the derived roster order
  changes. Search for a test asserting roster or place order and fix it deliberately rather
  than meeting it as a failure.
  Four order contracts found and fixed deliberately: the place-iteration pin and the
  shop-order pin (`test_settlements.py`, `test_shops.py`) re-pinned to terrace order; the
  derived-roster order pins in `test_guild_config/test_service_host_roster.py` re-pinned,
  with the field-neutrality comparisons switched to locating rows by `service_id` so they
  keep guarding identities not sequences; `test_guild_economy_sync/test_service_host_identity.py`
  locates the guild host's creation event by service id instead of index.

## 3. The doorway-collision rule

- [x] 3.1 In `validate_place_registry`, reject two places that share an exterior and a
  doorway key, naming both places and the shared name. — Cross-record pass keyed by
  (settlement_key, exterior_xy, doorway_key_zh); the z derives from the settlement, so the
  same coordinate in two settlements stays two streets.
- [x] 3.2 Cover both sides over synthetic rows: two places on one exterior with different
  doorway names load and yield two doorways; the same name fails. — Validator pair in
  `test_settlements.py`; the "yields two doorways" half runs over the live sync seams in
  `world/maps/tests/test_service_interiors.py` with a synthetic patched-registry pair.
- [x] 3.3 Confirm the shipped craft alley passes — the replan hand-checked it, and this is
  the check that makes that permanent. — `validate_place_registry(PLACE_REGISTRY)` passes
  with the new rule, and the existing dynamic two-doorways test still observes 工匠巷's pair.

## 4. Handoff

- [x] 4.1 The assembled registry is identical to task 1.1's capture. — Proven by
  `test_the_assembled_registry_equals_the_pre_split_capture` on the final tree.
- [x] 4.2 Run the lore settlements, guild-config and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`. — All green:
  `world.lore.tests.test_settlements`/`test_shops`, every `test_guild_config` module, every
  `test_guild_economy_sync` module, plus `world.maps.tests.test_service_interiors`;
  spec_traceability check reports 1639/1639 covered, 0 errors. test_data_lint introduces no
  new violation over master's one pre-existing finding.
