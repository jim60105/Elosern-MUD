# Tasks: align-gallery-art-consumption-specs

## 1. Contract verification (behavior already shipped)

- [ ] 1.1 Confirm `web/webclient-app/components/face-rect.js` still implements
  exactly the delta's mapping: center-to-percentage pair, the
  epsilon-tolerant clamp, and the centered `50% 50%` fallback set. If the
  helper moved or gained fields, update the delta, not the helper.
- [ ] 1.2 Confirm the consumer list in the requirement matches the actual
  importers (`ParticipantFrame.vue`, `PartyStrip.vue`, `PartyDrawer.vue`,
  `NarrativeFeed.vue`, `AppClient.vue` interact avatars, `DockMenu.vue` target
  rows, `CharacterSwitcher.vue`, `ReferenceArtwork.vue`) — re-grep
  `faceObjectPosition` before syncing.

## 2. Traceability obligations at archive time

- [ ] 2.1 After syncing the two ADDED requirements, annotate the executed
  evidence: `covers_requirement` on the mapping suite
  (`web/webclient-app/tests/data/face_rect.test.js`) and the frame suite
  (`web/webclient-app/tests/core/reference_artwork.test.js`), following the
  node-suite evidence-harness pattern in
  `web/webclient/tests/test_node_suite_evidence.py` if a Vitest file needs a
  registered harness row.
- [ ] 2.2 Confirm `pnpm run showcase-coverage` still passes against the frozen
  51-entry manifest including `World/ReferenceArtwork`.

## 3. Verification

- [ ] 3.1 `openspec validate align-gallery-art-consumption-specs --strict`.
- [ ] 3.2 Vitest evidence files: `npx --no-install vitest run
  web/webclient-app/tests/data/face_rect.test.js
  web/webclient-app/tests/core/reference_artwork.test.js
  web/webclient-app/tests/combat/participant_frame.test.js`.
- [ ] 3.3 `uv run --locked python -m tools.spec_traceability check` after the
  archive-time annotations.
- [ ] 3.4 At archive time: `openspec validate --all --strict`.
