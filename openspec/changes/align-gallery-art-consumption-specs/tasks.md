# Tasks: align-gallery-art-consumption-specs

## 1. Contract verification (behavior already shipped)

- [x] 1.1 Confirm `web/webclient-app/components/face-rect.js` still implements
  exactly the delta's mapping: center-to-percentage pair, the
  normalized-bound validation with two-decimal rounding, and the centered
  `50% 50%` fallback set. If the
  helper moved or gained fields, update the delta, not the helper.
  Verified 2026-09-10 (L14-27): non-numeric/non-finite fields, negative x/y,
  non-positive w/h, and x+w>1 / y+h>1 all return "50% 50%"; otherwise the
  rounded center pair. face_rect.test.js pins "50% 31%" and the boundary
  "0% 100%". Delta wording tightened in the same audit: the helper validates
  exactly (no epsilon clamp), and the universal claim excludes ArtPanel's own
  grid tiles/full view (centered default crop) and scene backdrops (scene
  media, not portrait entries).
- [x] 1.2 Confirm the consumer list in the requirement matches the actual
  importers (`ParticipantFrame.vue`, `PartyStrip.vue`, `PartyDrawer.vue`,
  `NarrativeFeed.vue`, `AppClient.vue` interact avatars, `DockMenu.vue` target
  rows, `CharacterSwitcher.vue`, `ReferenceArtwork.vue`) — re-grep
  `faceObjectPosition` before syncing.
  Verified 2026-09-10 by re-grep — exactly these eight files import the
  helper (ParticipantFrame L94/128, PartyStrip L83, PartyDrawer L256,
  NarrativeFeed L352, AppClient L1062, DockMenu L323, CharacterSwitcher
  L152/217, ReferenceArtwork L30). ArtPanel does not import it; the delta now
  names that exclusion instead of claiming every cover-cropped image.

## 2. Traceability obligations at archive time

- [ ] 2.1 After syncing the two ADDED requirements, annotate the executed
  evidence, following the node-suite evidence-harness pattern in
  `web/webclient/tests/test_node_suite_evidence.py`: add harness rows that
  execute the mapping suite (`web/webclient-app/tests/data/face_rect.test.js`)
  and the frame suite (`web/webclient-app/tests/core/reference_artwork.test.js`)
  and carry `covers_requirement` for the two canonical post-sync IDs. This is
  MANDATORY, not conditional — `tools/spec_traceability.py` discovers
  associations only from Python `test_*.py` files, so the Vitest suites cannot
  cover the synced main requirements on their own and `check` would fail them.
  Register the harness rows in the existing module (no new test module, so no
  `.github/evennia-shards.json` change).
- [ ] 2.2 Confirm `pnpm run showcase-coverage` still passes against the frozen
  51-entry manifest including `World/ReferenceArtwork`.

## 3. Verification

- [x] 3.1 `openspec validate align-gallery-art-consumption-specs --strict`.
  Passes (exit 0) after the contract audit's delta corrections, 2026-09-10.
- [x] 3.2 Vitest evidence files: `npx --no-install vitest run
  web/webclient-app/tests/data/face_rect.test.js
  web/webclient-app/tests/core/reference_artwork.test.js
  web/webclient-app/tests/combat/participant_frame.test.js
  web/webclient-app/tests/data/party_strip.test.js
  web/webclient-app/tests/data/party_drawer.test.js
  web/webclient-app/tests/dialogue_feed.test.js
  web/webclient-app/tests/action/dock_menu.test.js
  web/webclient-app/tests/core/character_switcher.test.js`.
  All pass (exit 0): the three named suites plus the five suites asserting the
  framed-portrait `object-position` values for six of the seven enumerated
  surfaces — combat participant frame (ally and foe), party strip, party
  drawer, dialogue host avatar, dock target rows, and character switcher.
  The seventh named surface, the AppClient interact-target avatar, carries the
  mapping binding (AppClient.vue L1061-1063) but has no executed crop
  assertion: the current wire schema forces `interact` targets' `portrait_ref`
  to null (protocol.js L3407-3409), so no committed snapshot can give that
  avatar a URL-bearing portrait and an AppClient-level crop test is
  unreachable through the validator. Recorded as the scenario's per-surface
  evidence gap, to close when the schema starts carrying interact refs;
  DockMenu's nav-row suite exercises the identical portraitFor → mapping
  path for the same data shape. The ArtPanel grid tiles/full view are
  excluded by the requirement.
- [ ] 3.3 `uv run --locked python -m tools.spec_traceability check` after the
  archive-time annotations.
- [ ] 3.4 At archive time: `openspec validate --all --strict`.
