## 1. Preference storage

- [ ] 1.1 Extend `GalleryRecord` with the selected-official-identity field and the bounded per-identity geometry-override map in `world/art/gallery.py` (new public writers under `gallery_lock`, tolerant reads with bounded diagnostics), and verify sole-writer scan tests, card-contract-unchanged tests (empty `cards` with preferences set), and malformed-preference-reads-as-absent tests

## 2. Selection-aware resolution

- [ ] 2.1 Make chain step 1 selection-aware in `world/art/gallery_match.py`: a selected-and-resolving official identity presents at the gallery-default slot while equipment-bound cards keep precedence, and verify chain tests for the outranking order, fall-through on unresolvable selection (preference retained), and mutual clearing between runtime-default and official-selection writers
- [ ] 2.2 Implement update tolerance — retained identity resolving new bytes after restart, fall-through without deletion when the identity disappears — and verify restart-simulation tests for both paths
- [ ] 2.3 Apply personal geometry overrides in `world/art/presenter.py` official payloads (validate against current decoded dimensions; invalid override → metadata/fitted geometry with retained preference and one bounded diagnostic) and verify two-characters-same-image tests (independent overrides, unchanged source, unaffected other characters)

## 3. Read models and actions

- [ ] 3.1 Project `official_entries` for the selected subject in the gallery panel presenter and mirror the exact row shape through the Python and JavaScript validators, and verify dual-direction parity tests (official rows never in `cards`, empty list for no-reference subjects, malformed rows rejected both sides)
- [ ] 3.2 Add the four preference adapters (select, clear selection, set geometry, clear geometry) with exact payload validators, reference-scope identity re-resolution, and stable codes, and verify adapter tests including replay-idempotence and no-partial-write on rejection
- [ ] 3.3 Make the existing mutation adapters reject official identities with `official_read_only` and verify direct-dispatch refusal tests prove byte-for-byte unchanged official files, cards, and preferences (acceptance criterion 6)

## 4. Frontend affordances

- [ ] 4.1 Render official rows in `GalleryPanel.vue`/`GalleryDetailRail.vue` (select/preview/geometry affordances; delete/replace/regenerate hidden), and verify showcase/browser-local coverage for the new states per the frozen component manifest

## 5. Verification

- [ ] 5.1 Run package-adjacent tests (gallery model, chain, presenter, adapters), wire-parity tests, and the contract gate once, confirming acceptance criterion 4 end-to-end: two preset-born characters sharing official bytes choose different images and geometry with zero cross-effects
