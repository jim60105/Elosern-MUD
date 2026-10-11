# Tasks

## 1. Deterministic visual provenance

- [ ] 1.1 Add the frozen visual declarations in `world/lore/monster_visuals.py` as specified in design D1: public-appearance projection of complete combat species plus the twelve authored baseline visual rows; reject duplicate/tier/reserved keys and compose at consumer seams so registry replacement in tests remains visible.
- [ ] 1.2 Extend `MonsterPopulation` with `art_species_key`; preserve current hash, tier selection, label ordering, traits and balance. Persist the selected authored visual key in `_spawn` under population ownership; include it in owned-population reconciliation without display-name inference, foreign-object mutation or a migration.
- [ ] 1.3 Extend official provenance's pure attribute reader for absent complete-species provenance only; invalid present `species_key` must not borrow baseline identity. Unknown/missing visual provenance remains a monster silhouette and never creates combat profiles, variants or skills.

## 2. Species subject, generation and serving cutover

- [ ] 2.1 Replace tier art membership/description in subjects, presenter, art-view classification and gallery fallback with registered visual species and explicit Monster typeclass classification. Remove obsolete tier art fallback metadata/validation from MonsterTier while preserving all balance fields and consumers.
- [ ] 2.2 Replace startup and automatic/manual generation's monster tier loops with visual membership; retain card caps, capabilities, classic species recovery, official-image suppression and the single serialized worker. Render only selected public physical species appearance in `prompts/art.yaml`, with no mixed tier examples or private lore.
- [ ] 2.3 Enforce current visual membership at service/gallery, seed, staff retry/requeue, queue/claim/settle, presenter and classic/gallery media admission seams. Refuse parsed/forged/queued retired tiers including calamity without copying, converting, applying or serving old output; preserve current secure path confinement.

## 3. Selection, gallery and shared consumers

- [ ] 3.1 Keep species-shared runtime cards/defaults, but store monster personal official selection/geometry on the live entity under the gallery writer and lock. Preserve character mutual-clearing semantics; species shared defaults must not clear another individual's preferences. Resolve the documented precedence with entity context.
- [ ] 3.2 Publish the bounded stable-key species rail with the design's capacity rule and official previews. Add `supports_personal_official_preferences` to schema version 2 and mirror it in frontend validation/fixtures; hide personal controls for bare species subjects and reject their direct writes with `entity_required`, while retaining species generate/select/delete/default actions.
- [ ] 3.3 Update all semantic subject consumers, CLI help, seed examples and gallery UI controls/stories to registered species keys; remove old aliases, tier examples and obsolete art-only imports. Preserve official mounted images and generated cutouts, not just silhouette-only rendering.

## 4. Contracts, assertion ownership and verification

- [ ] 4.1 Amend engine D15, §8 and Phase 6 roadmap, the focused portrait UI §§2/3/5 and monster-data-model §7 as specified in design D4. Update relevant deployment/seed guides and changelog, with no historical archive rewriting.
- [ ] 4.2 Replace conflicting assertions in existing subject/species-identity, official refs, presenter, service startup, gallery prompt/action/panel, queue/media/staff/seed and wilderness population suites. Use the cutover matrix to assign each mechanism once; registry closure uses production membership without a duplicate roster, while expected behavior uses fixed independent examples. Exercise actual goblin producer provenance and same-tier cross-species leakage.
- [ ] 4.3 Generate merged-main requirement IDs with `tools.spec_traceability list` for the renamed/new requirements, update actual per-assertion mappings and required test registration using the existing traceability guide. Register any genuinely new Python test module in `.github/evennia-shards.json`; do not add allowlists, aliases or redundant regressions.
- [ ] 4.4 After implementation is integrated, run the repository-prescribed affected Python suites, root-config gallery/art Vitest tests and traceability validation, plus `openspec validate fix-monster-species-portraits --strict`. Record exercised outcomes and leave first-combat browser acceptance to the dependent publication change rather than claiming this slice completes it.
