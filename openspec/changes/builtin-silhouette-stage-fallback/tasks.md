## 1. Payload semantics

- [x] 1.1 Rework the `world/art/presenter.py` fallback branch so the resolved fallback key/media identity/rectangle are carried as a decorative `fallback` field beside the subject's true asset/gallery status — established here as the vocabulary owner (`runtime | silhouette | placeholder` origin, retained beside real images for load-failure re-render; no `done`/generated label) — and verify payload tests for missing/pending/failed underlying states each proving status passthrough, unchanged persisted records, silhouette origin, and fallback retention beside a resolved real image
  Verified: `world.art.tests.test_presenter` (38 tests, incl. `SilhouettePayloadTests`), `world.art.tests.test_gallery_fallback` (30), `world.rules.tests.test_character_creation.test_portrait_finalization` — all green.
- [x] 1.2 Mirror the new origin vocabulary and decorative `fallback` field through the art-panel wire vocabulary on both validator sides (self-contained: nothing from `official-art-resolution-contracts` is required — that change later extends the vocabulary with `official`), and verify parity tests reject a one-sided payload
  Verified: `web.webclient.presentation.tests.test_art_panel` + `test_roster` + `test_art_push` (73 tests) and the dependency-free Node suite (`protocol_art.test.js`, `art_panel.test.js`; 480 tests) reject missing/unknown origins and every incoherent one-sided fallback shape on both sides.

## 2. Stage silhouette rendering

- [x] 2.1 Replace the inline stage SVG in `ReferenceArtwork.vue` with the CSS alpha-mask rendering of the carried fallback identity (explicit mask-alpha semantics, dark fill styling, aspect preserved, floor-aligned via the existing stage box) and verify component tests that each fallback key renders its own identity and the SVG path is gone
  Verified: `tests/core/reference_artwork.test.js` (14 tests; all six keys, `mask-mode: alpha`, contain/bottom-center, no SVG when an identity is carried, the grounded SVG retained when none is).
- [x] 2.2 Keep labels/name/targeting outside the mask, retain pending shimmer + reduced-motion behavior, and verify motion-level and accessibility tests (labels readable at every level; mask decorative/aria-hidden)
  Verified: same Vitest file — chest/figcaption labels outside the mask, `aria-hidden` mask, the pending figure's data-status/data-motion contract with the label readable at every level, the shimmer selector extended to the mask inside the existing reduced-motion block.
- [x] 2.3 Implement the load-failure paths — real-image failure reuses the carried silhouette reference plus load-failure label with no state mutation or refetch, and bundled-mask failure retains name + truthful text placeholder with a usable interaction surface — and verify failure-injection tests for both
  Verified: same Vitest file (real-image `error` returns to the carried identity's mask with the load-failure label and no 已生成 claim; probe `error` drops the figure and keeps name + label) plus the browser failure injection in `web/tests/browser/test_browser_stage_silhouette.py`.

## 3. Selection-rule regression

- [x] 3.1 Verify no selection logic moved to JavaScript and no selection rule changed: contract tests pin band boundaries (≤12 child / ≥60 elder / adult fail-closed), stable-hash-for-other-sex determinism, `monster_anon` for monsters, registry-declaration overrides, and entity-identity-only hashing for entities without a named subject (reusing existing `fallback_key_for` tests plus new stage-level assertions)
  Verified: the existing band/declaration tests plus the new `EntityDecorationRuleTests`/`EntityMonsterConstantTests` (entity path shares `_band_or_hash`/`_declared_key_for_entity` and matches the subject path per band, declaration, and monster constant; the entity identity is the sole hash input); no selection moved to JavaScript (the client validates vocabulary only).

## 4. Verification

- [ ] 4.1 One focused local browser file/class exercising the actual stage: adult male/female, boy/girl, elder, and monster actors show their corresponding silhouettes (acceptance criterion 7), the stage transitions to a real image when one resolves, and image-load failure returns to the correct silhouette without claiming generation success (acceptance criterion 8)
- [x] 4.2 Run the package-adjacent Python/Node tests and the contract gate once for the changed vocabularies and confirm the compact/cover surfaces are unchanged by the stage edit
  Verified: the Python art/presentation modules above, the full dependency-free Node suite (480), the full Vitest suite (1565; the cover-mode/compact surfaces' own assertions unchanged and green), and `uv run --locked python -m tools.contract_gate` (traceability, observability, test-data, manifests, contracts) — green.
