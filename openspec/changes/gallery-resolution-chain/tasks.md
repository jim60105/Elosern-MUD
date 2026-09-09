## 1. Resolution chain

- [x] 1.1 Create `world/art/gallery_match.py` with `resolve_card(subject, entity)` implementing steps 1-4: stored snapshot, full-mask equality filter, most-slots-wins, newest-`created_at` tie-break, then `default_image_id`
- [x] 1.2 Skip steps 1-3 for monster subjects and compute no equipment snapshot for them
- [x] 1.3 Treat an unbound card as eligible only as the explicit default
- [x] 1.4 Add `validated_card_identity(subject, card)`: subject-prefix, closed store-extension, and `world/art/paths.py::resolved_under_store_root` checks; a card failing any check is skipped and the chain continues
- [x] 1.5 Add the terminal seam `fallback_for(subject)` returning `None` in this change, consulted after the classic asset record and before the placeholder
- [x] 1.6 Keep the module free of `world.ai`, `ollama`, `llm_client`, and `world.art.connectivity` imports and free of every write

## 2. Presenter integration

- [x] 2.1 Insert the chain into `resolve_subject` / `resolve_character` / `resolve_entity` ahead of the existing classic asset resolution, keeping every current placeholder kind and label
- [x] 2.2 Build gallery URLs through the existing `media_url_for` from validated card identities only; never expose `out_path` or the store root
- [x] 2.3 Add `face_rect` to every payload: the card's rectangle, the shared default for a classic asset or a fallback image, `null` for every placeholder
- [x] 2.4 Degrade a malformed stored rectangle to the shared default with one bounded diagnostic
- [x] 2.5 Adopt `world/art/paths.py::resolved_under_store_root` in `presenter.py` in place of its private confinement probe

## 3. Media route

- [x] 3.1 Extend `web/art_media.py` with the gallery identity pattern `gallery/(character|monster)/<subject-key>/<image-id>.(png|webp|jpg|avif)`
- [x] 3.2 Admit a gallery identity only when the `GalleryRecord` addressed by the identity's own kind and subject-key segments holds a card whose stored identity equals the request exactly — a direct record lookup, never a full scan
- [x] 3.3 Keep every existing rejection rule and the closed extension-to-media-type map; return 404 for a mis-addressed, unreferenced, symlinked, or out-of-root gallery identity
- [x] 3.4 Add the `defaults/<fallback-key>.<ext>` branch serving from one fixed in-repo defaults directory with the same extension map and confinement discipline; 404 on a missing file, sub-path, symlink, or escaping path
- [x] 3.5 Leave the classic `done`-record path untouched

## 4. Wire payloads

- [x] 4.1 Add `face_rect` to the art panel catalog entry serialization in `web/webclient/presentation/art.py` and to its exact-field validator, enforcing exactly `x`, `y`, `w`, `h` in `[0, 1]` when a URL is present and `null` for placeholders
- [x] 4.2 Add the same field and validation to the roster row portrait in `web/webclient/presentation/roster.py`
- [x] 4.3 Bump BOTH `ART_SCHEMA_VERSION` and `ROSTER_SCHEMA_VERSION` — one convention, applied to any nested field-set change — and update every payload fixture and assertion that pins the exact field set
- [x] 4.4 Verify the live Vue client under `web/webclient-app/` reads catalog and roster entries by key and performs no `schema_version` check, so the added field and the version bump are additive for it
- [x] 4.5 Update `web/webclient-app/stories/fixtures.js` and the `portrait_catalog` fixtures in `tests/data/party_strip.test.js` and `tests/combat/participant_frame.test.js` to carry `face_rect`, changing no component
- [x] 4.6 Record that consuming the rectangle in the avatar surfaces (`ParticipantFrame`, `CharacterSwitcher`, `PartyStrip`, `PartyDrawer`, `NarrativeFeed`) stays a TODO for the Vue rewrite (design D12)

## 5. Tests

- [x] 5.1 `world/art/tests/test_gallery_match.py`: specificity wins, newest-`created_at` tie-break, empty-slot binding matches, equipment change swaps the card, no-match falls to default
- [x] 5.2 `world/art/tests/test_gallery_match.py`: unbound cards with no default are never shown; an unbound default is shown
- [x] 5.3 `world/art/tests/test_gallery_match.py`: the monster variant computes no snapshot and falls through to the classic asset
- [x] 5.4 `world/art/tests/test_gallery_match.py`: a card whose file vanished, addresses another subject, resolves out of root, or is a symlink is skipped and the chain continues
- [x] 5.5 `world/art/tests/test_presenter.py`: `face_rect` present with a URL, `null` for every placeholder, malformed rect degrades to the default with one diagnostic
- [x] 5.6 `web/tests/` or the existing media-route suite: a card-referenced gallery identity is served with its media type; unreferenced, mis-addressed, traversal, symlink, and out-of-root identities return 404
- [x] 5.7 `web/webclient/presentation/tests/`: art panel and roster payloads carry `face_rect` and fail validation when it is malformed
- [x] 5.8 Register every new test module in `.github/evennia-shards.json` in this change (`world.art` is already covered by its package label; new presentation modules are not)
- [x] 5.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art web.webclient.presentation web.webclient.tests`
- [x] 6.2 `uv run --locked python -m tools.observability_lint check`
- [x] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.4 `uv run --locked python -m tools.verify_coverage_roots` (shard manifest completeness)
- [x] 6.5 Re-run the JS gates after the fixture update: the dependency-free legacy gate (`node --test web/static/webclient/js/tests/`), Vitest, and the Storybook build
- [x] 6.6 `openspec validate gallery-resolution-chain --strict`
