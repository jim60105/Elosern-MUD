## 1. Payload semantics

- [ ] 1.1 Rework the `world/art/presenter.py` fallback branch so the resolved fallback key/media identity/rectangle are carried as a decorative `fallback` field beside the subject's true asset/gallery status — established here as the vocabulary owner (`runtime | silhouette | placeholder` origin, retained beside real images for load-failure re-render; no `done`/generated label) — and verify payload tests for missing/pending/failed underlying states each proving status passthrough, unchanged persisted records, silhouette origin, and fallback retention beside a resolved real image
- [ ] 1.2 Mirror the new origin vocabulary and decorative `fallback` field through the art-panel wire vocabulary on both validator sides (self-contained: nothing from `official-art-resolution-contracts` is required — that change later extends the vocabulary with `official`), and verify parity tests reject a one-sided payload

## 2. Stage silhouette rendering

- [ ] 2.1 Replace the inline stage SVG in `ReferenceArtwork.vue` with the CSS alpha-mask rendering of the carried fallback identity (explicit mask-alpha semantics, dark fill styling, aspect preserved, floor-aligned via the existing stage box) and verify component tests that each fallback key renders its own identity and the SVG path is gone
- [ ] 2.2 Keep labels/name/targeting outside the mask, retain pending shimmer + reduced-motion behavior, and verify motion-level and accessibility tests (labels readable at every level; mask decorative/aria-hidden)
- [ ] 2.3 Implement the load-failure paths — real-image failure reuses the carried silhouette reference plus load-failure label with no state mutation or refetch, and bundled-mask failure retains name + truthful text placeholder with a usable interaction surface — and verify failure-injection tests for both

## 3. Selection-rule regression

- [ ] 3.1 Verify no selection logic moved to JavaScript and no selection rule changed: contract tests pin band boundaries (≤12 child / ≥60 elder / adult fail-closed), stable-hash-for-other-sex determinism, `monster_anon` for monsters, registry-declaration overrides, and entity-identity-only hashing for entities without a named subject (reusing existing `fallback_key_for` tests plus new stage-level assertions)

## 4. Verification

- [ ] 4.1 One focused local browser file/class exercising the actual stage: adult male/female, boy/girl, elder, and monster actors show their corresponding silhouettes (acceptance criterion 7), the stage transitions to a real image when one resolves, and image-load failure returns to the correct silhouette without claiming generation success (acceptance criterion 8)
- [ ] 4.2 Run the package-adjacent Python/Node tests and the contract gate once for the changed vocabularies and confirm the compact/cover surfaces are unchanged by the stage edit
