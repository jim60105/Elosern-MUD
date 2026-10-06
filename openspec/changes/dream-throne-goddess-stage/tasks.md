## 1. Scene prose and prompt

- [x] 1.1 Rewrite `OPENING` in `world/narrative/dream_surface.py` as the cloud-throne staging (white throne on a sea of clouds, obscured goddess pleasuring herself, exaggerated well-used genitals spurting into the ankle-deep flood the player recognizes as her fluids) and verify the opening prose is what `dream_state()` serves
- [x] 1.2 Retheme the two ending strings in `dream_state()` to the goddess's climax and the fading cloud dream, and verify the reached-climax ending names the post-climax phase before awakening
- [x] 1.3 Rewrite the `dream.system` prompt in `prompts/dream.yaml` for the cloud-throne goddess scene (throne on a sea of clouds, self-pleasuring obscured counterpart, exaggerated spurting genitals, the ankle-deep flood recognized as her fluids, server-supplied arousal phase authoritative) while keeping `schema_version: 1`, the exact `scene`/`dialogue`/`phase` output contract, and the approved-explicit-vocabulary mandate, and verify the prompt still parses and validates

## 2. Goddess-owned arousal track wording

- [x] 2.1 Re-own the `world/narrative/dream_track.py` docstrings to the dream's goddess counterpart (her deterministic session-only pleasure/arousal/climax track, her climax at six-exchange convergence ends the dream, the player's live sexual state never involved) with deltas, canonical five bands, and `TRACK_VERSION` unchanged, and verify `world.narrative.tests.test_dream_track` passes with no counter behavior change

## 3. Server-resolved scene_art and official identity constants

- [x] 3.1 Add `DREAM_GODDESS_NPC_KEY = "dream_goddess"` and `DREAM_GODDESS_SCENE_IDENTITY = "npc/dream_goddess/dream-throne.webp"` to `world/narrative/dream_surface.py` and a `scene_art_url()` helper returning `official.current_catalog().url_for(...) or ""`, and verify an absent official catalog yields the empty URL
- [x] 3.2 Emit `scene_art: scene_art_url()` from `dream_state()` and verify the panel state carries it for both the empty and the admitted-catalog cases
- [x] 3.3 Add the `dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame` catalog-resolution test to `world/narrative/tests/test_dream_surface.py` proving `scene_art` is `""` with an empty snapshot and `/art/official/<fingerprint>/npc/dream_goddess/dream-throne.webp` when the snapshot admits the identity, and verify the URL stays within 256 characters

## 4. Dream panel wire schema v2 across Python/JS mirrors

- [x] 4.1 Bump `DREAM_SCHEMA_VERSION` from 1 to 2 in `web/webclient/presentation/dream.py` (the registry registration references the constant by identifier and follows automatically), and verify the presenter emits `schema_version: 2`
- [x] 4.2 Set `PANEL_ALLOWLIST.dream` to `2` in `web/static/webclient/js/elosern/protocol/constants.js`, and verify the UMD export mirrors the new version
- [x] 4.3 Update the client validator `web/static/webclient/js/elosern/protocol/panels/dream.js` to require schema 2, add `scene_art` to the exact state field set, and bound it as a string of at most `MAX_SCENE_ART_URL = 256` characters mirroring `world.art.presenter.MAX_PORTRAIT_MEDIA_URL`, and verify a non-string `scene_art` rejects (the vitest negative case; the 256-character bound itself is the shipped mirror and is not separately exercised)
- [x] 4.4 Verify the four mirrored version sites agree (`DREAM_SCHEMA_VERSION`, the registry reference, `PANEL_ALLOWLIST.dream`, and the validator re-check) by running `tests/test_panel_schema_version_parity_contract.py` and the Node protocol gate

## 5. Panel art, labels, and removal of the bundled asset

- [x] 5.1 Render `state.scene_art` in `web/webclient-app/components/DreamPanel.vue` only when non-empty and drop the bundled `dream-white-bed.avif` import, and verify the panel shows no `<img>` when `scene_art` is empty
- [x] 5.2 Relabel the panel to the cloud-throne staging (`雲上王座之夢`, `王座上的女神`, `女神的興奮`) and reword the counterpart-facing copy, and verify the shipped UI, prompt, and synthetic fixtures carry no white-bed/夢中的身影 wording (historical change records and archives are out of scope)
- [x] 5.3 Delete `web/webclient-app/assets/redesign/dream-white-bed.avif` and remove its path from `APPROVED_NON_RUNTIME_IMAGES` in `world/art/tests/test_gallery_fallback.py`, and verify the non-runtime-image contract passes against the tracked tree
- [x] 5.4 Update `web/webclient-app/tests/dream.test.js` and `web/webclient-app/stories/World/DreamPanel.stories.js` to schema 2 with a `scene_art` fixture, and verify the new vitest case asserts the art renders only when the panel carries one

## 6. Verification

- [x] 6.1 Run the focused Evennia suites `world.narrative.tests.test_dream_surface tests.test_panel_schema_version_parity_contract world.art.tests.test_gallery_fallback` (47 tests OK) and `world.ai.tests.test_dream_presentation world.narrative.tests.test_dream_track world.narrative.tests.test_dream_session` (76 tests OK)
- [x] 6.2 Run the Node protocol gate (exit 0) and `pnpm test` (137 files / 1578 tests pass)
- [x] 6.3 Run `uv run --locked python -m tools.contract_gate` (green: traceability 1897/1897 covered, observability 0 violations, manifests, contracts 18 OK), `pnpm run build`, `pnpm run build-storybook`, and `pnpm run showcase-coverage` (all OK)

## 7. Review round (independent post-implementation critique)

- [x] 7.1 Degrade the stage to the flat background when the artwork URL fails to load — `@error` on `DreamPanel.vue`'s `<img>` drops it, and a changed published URL is a fresh attempt — and verify the vitest case proves both the drop and the retry
- [x] 7.2 Add the catalog-admissibility tripwire test in `world/narrative/tests/test_dream_surface.py` pinning the artwork identity to `OFFICIAL_CONTENT_KINDS`, `is_valid_subject_key`, and `STORE_EXTENSIONS`, and verify it passes
- [x] 7.3 Reword the first requirement body in both `openspec/specs/dream-explicit-presentation/spec.md` and this change's delta to name the shipped staging (the counterpart seated on the throne, the player standing in her flood), and verify the two requirement blocks remain byte-identical
- [x] 7.4 Correct the documentation: `docs/development/narrative-memory-and-recall.md` describes the externally served stage artwork and the text client's prose-only view, `docs/development/official-artwork-deployment.md` names the dream identity and its verification step, and `world/ai/tests/test_dream_presentation.py`'s synthetic fixture is re-themed — and verify no shipped document still describes the deleted bundled AVIF
- [x] 7.5 Record the review dispositions in `design.md` (adopted fallback, tripwire, prose accuracy, documentation fixes; the server-side URL guard rejected and the stale-tab ops note deferred) and verify `openspec validate dream-throne-goddess-stage --type change --strict` passes
