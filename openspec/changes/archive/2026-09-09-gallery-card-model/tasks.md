## 1. Store-root confinement helper

- [x] 1.1 Create `world/art/paths.py` exposing `resolved_under_store_root(identity) -> Path | None`: rejects `..`, absolute paths, symlinked components, and any path resolving to or outside `ART_STORE_ROOT`
- [x] 1.2 Keep the module free of `world.ai`, `ollama`, `llm_client`, and `world.art.connectivity` imports so the deterministic-path and connectivity import-boundary contract tests pass unedited

## 2. Gallery record and card contract

- [x] 2.1 Create `world/art/gallery.py` with a `GalleryRecord(DefaultScript)` carrying `kind`, `subject_key`, `cards`, `default_image_id`, `last_error_code`, `last_error_at` as `AttributeProperty` fields
- [x] 2.2 Add `record_key(subject) -> "gallery:<full-subject-key>"` and a lazy `record_for(subject, *, create=False)` that never scans and never creates on read
- [x] 2.3 Add `DEFAULT_FACE_RECT = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}` and `validate_face_rect(...)` enforcing exact keys, `[0, 1]` range, `x+w <= 1`, `y+h <= 1`, `w > 0`, `h > 0`
- [x] 2.4 Add `SLOT_ORDER = ("weapon_main", "weapon_off", "armor", "accessories")` and `validate_binding(...)` enforcing the non-empty declared-order mask, the exact snapshot key set, string-or-`None` single slots, and the sorted accessory list
- [x] 2.5 Add `snapshot_for(entity)` reading `entity.db.equipment` directly (no `EquipmentHandler`, no write), failing closed to the empty snapshot on missing or malformed storage
- [x] 2.6 Add `validate_card(...)` enforcing the exact key set, types, uuid `image_id` uniqueness, the `gallery/<kind-dir>/<subject-key>/<image-id><ext>` identity shape with the closed kind-directory set `character` / `monster`, and the closed `source` vocabulary

## 3. Write API

- [x] 3.1 `append_card(subject, **card_fields)`: validate, default the face rect, set `created_at`, make the first card the default, raise a typed error on any violation
- [x] 3.2 Enforce the monster one-card cap inside `append_card`: replace the existing card, delete its file through `resolved_under_store_root`, and reject a non-`None` binding on a monster card
- [x] 3.3 `remove_card(subject, image_id)`: remove the entry, unlink exactly the confined file (missing or unresolvable file is a bounded log, not a raise), and reset `default_image_id` to `None` when the removed card was the default
- [x] 3.4 `set_default(subject, image_id)`: reject an `image_id` no card of the record carries
- [x] 3.5 `cards_for(subject)`: tolerant read that skips malformed entries and logs `gallery_card_invalid` once per skipped entry through the `world.observability` facade
- [x] 3.6 Add `record_error(subject, code)` / `clear_error(subject)` writing `last_error_code` and `last_error_at` (consumed by the generation change)

## 4. Tests

- [x] 4.1 `world/art/tests/test_gallery.py`: lazy creation, empty read for an unwritten subject, first-card-becomes-default, later append leaves the default, unknown-id default set rejected
- [x] 4.2 Card contract: exact key set, extra/missing/wrong-typed key rejected, duplicate `image_id` rejected, seed-provenance card with `prompt`/`seed` `None` accepted, no environment-driven parameter stored
- [x] 4.3 Face rect: default applied when absent, each out-of-bounds form rejected, valid rect stored verbatim
- [x] 4.4 Binding: declared-order mask, exact snapshot key set, sorted accessories, all-empty snapshot legal, `None` legal, each malformed form rejected
- [x] 4.5 Snapshot: no-create on an entity with no equipment attribute, fail-closed on every malformed storage shape
- [x] 4.6 Monster cap: second append replaces and deletes the prior file; bound monster card rejected
- [x] 4.7 Deletion: confined unlink, out-of-root identity never unlinked, default cleared when the default card is removed
- [x] 4.8 Tolerant reads: one malformed entry skipped with one `gallery_card_invalid` event; an all-malformed record reads empty
- [x] 4.9 Annotate every test with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`
- [x] 4.10 Confirm `world/art/tests/test_gallery.py` is covered by the existing `world.art` label in `.github/evennia-shards.json` (no manifest edit expected; add one if the label set changed)

## 5. Verification

- [x] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art`
- [x] 5.2 `uv run --locked python -m tools.observability_lint check`
- [x] 5.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 5.4 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_art_offline_contract` (deterministic-path ban still clean)
- [x] 5.5 `openspec validate gallery-card-model --strict`
