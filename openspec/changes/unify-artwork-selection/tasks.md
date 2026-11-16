# Tasks

## 1. Declare reference, preference and terminal policies

- [ ] 1.1 Extend `world/art/gallery_kinds.py::GalleryKindCapabilities`, `with_values`, representation and declaration validator with the policy fields and temporary classic-support flag in design D1. Keep scene classic support false, the module import-free and exhaustive, and current cap/geometry/age flags.
- [ ] 1.2 Add `official_refs.official_content_reference_for_subject(subject, entity=None)` and scene membership in `_registry_for`; align both `OFFICIAL_CONTENT_KINDS` tuples and avoid duplicating scene in `OFFICIAL_LAYOUT_KINDS`. Use typed registry producers for scene/species, existing provenance resolver for characters and existing authored room-art membership for room overrides.
- [ ] 1.3 Extend `world/art/tests/test_gallery_kinds.py`, `test_official_refs_provenance.py` and `test_official_catalog.py` with synthetic policy redeclaration, bare scene/species references, unknown-key rejection and character provenance controls. Never assert a shipped key roster or artwork count.

## 2. Unify selection and preference ownership

- [ ] 2.1 Make `gallery_match.resolve_display_chain` the single ordered subject-slot enumerator in design D3, including the temporarily retained classic reader. Migrate `resolve_display`, portrait enumeration and scene generated/default selection to projections; remove duplicate `_scene_gallery_card` selection. Preserve binding specificity/newest tie-break, unbound default rules, immutable card validation and reached-fault ordering.
- [ ] 2.2 Update `presenter.describe_scene` to wrap the common archetype chain with existing authored room override and declared bundled/terminal resources. Keep source ids/ranks, terminal deduplication, logical scene identity and retention authorization truthful. Use capability policies for terminal/geometry decisions, never inline kind comparisons.
- [ ] 2.3 Route official preference reads/writes in `gallery.py`, `web/webclient/actions/gallery_actions.py` and `web/webclient/presentation/gallery.py` through the declared scope. Replace the scene-official refusal with subject-scoped select/clear while keeping existing admission checks and refusing scene geometry. Generation never clears explicit official selection; only an explicit runtime-default action clears the relevant owner.
- [ ] 2.4 Extend `test_gallery_match.py`, `test_scene_resolution.py`, gallery preference tests and `web/webclient/actions/tests/test_gallery_actions.py`. Assert equivalent generated-versus-official priority, explicit selection surviving first append/replacement, entity-local monster controls, shared-archetype scene selection and room override independence. Check no read path mutates or enqueues.

## 3. Fix automatic satisfaction without disabling explicit generation

- [ ] 3.1 Use the shared subject reference in `service._official_default_satisfies` and `_guarded_gallery_request` for startup/room-entry/entity paths. Preserve declared age checks, card/job idempotency, intentionally emptied scene suppression, on-commit ordering and per-subject failure isolation.
- [ ] 3.2 Add the bounded `art_auto_generation_suppressed` facade info event from design D6 for registry-subject official suppression. Reuse catalog and generation events; patch caller-module bindings in tests. Never log prompt text, credentials or roots.
- [ ] 3.3 Add `world/art/tests/test_unified_selection.py` with at most 12 deterministic regression methods covering bare startup subjects, valid/refused/substituted official defaults, no state/prompt/id on suppression, manual bypass, capped replacement success/failure, explicit selection retention and a redeclared synthetic kind. Reuse synthetic fixtures and fake image client. Extend `test_service/test_autogen_retrofit.py`, `test_gallery_request_seam.py` and `test_art_observability.py` where the owning mechanism already lives.

## 4. Documentation and traceability

- [ ] 4.1 Update `docs/development/official-artwork-deployment.md` with the common chain, operator-only suppression, manual generation and shared scene preference ownership. Amend the current source-policy sections of `docs/superpowers/specs/2026-10-14-unified-image-resolution-design.md` and engine D10 amendment reference as recorded in design “Policy review”. Keep room override, bundled terminals and dream exception explicit. No command syntax/availability changes, so no command-guide rewrite is required here.
- [ ] 4.2 Import `covers_requirement` from `tools.spec_traceability` on discoverable tests whose assertions establish the contracts in the table below. Use the literal canonical IDs obtained by `uv run --locked python -m tools.spec_traceability list`, not inferred slugs. Record each regression test method's matching delta scenario in the implementation handoff. No skipped or assertion-free coverage claims.
- [ ] 4.3 Run `uv run --locked python -m tools.shard_register fix` after adding the new regression module or moving/removing any tests; commit its generated manifests with the tests. Do not hand-edit shard manifests.

## 5. Focused acceptance after all edits

Run each command separately, with no wrappers or command chaining. These are implementation gates, not instructions to execute during proposal writing. Expected state is all focused tests passing, no observability/traceability exceptions, and strict OpenSpec validation without warnings.

- [ ] 5.1 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_unified_selection`
- [ ] 5.2 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_gallery_kinds`
- [ ] 5.3 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_official_refs_provenance`
- [ ] 5.4 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_scene_resolution`
- [ ] 5.5 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_gallery_actions`
- [ ] 5.6 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_art_observability`
- [ ] 5.7 `uv run --locked python -m tools.observability_lint check`
- [ ] 5.8 `uv run --locked python -m tools.contract_gate --change unify-artwork-selection`
- [ ] 5.9 `openspec validate unify-artwork-selection --strict`

No full browser suite, aggregate evidence verification or CI shard command belongs in this local plan.

## Canonical traceability assignment

Each row names the assertion owner, not permission to annotate every test in that module. Existing requirement IDs remain stable for MODIFIED deltas.

| Assertion owner | Literal canonical requirement ID |
| --- | --- |
| `test_unified_selection`: suppression/no writes | `art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery` |
| Service autogen tests: standard request/settle | `art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card` |
| Shared-chain regression: source order/purity | `art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback` |
| Redeclared-kind regression: no equipment | `art-gallery-resolution::monster-subjects-resolve-through-the-chain-without-the-binding-steps` |
| Terminal adapter regression | `art-gallery-resolution::the-chain-ends-at-one-fallback-seam` |
| `test_gallery_kinds`: immutable closed policies | `art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do` |
| Official reference/priority regression | `official-art-resolution::the-extended-chain-stays-deterministic-offline-and-side-effect-free` |
| Preference actions: ownership and preserved choice | `official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference` |
| `test_official_catalog`: synthetic scene membership | `official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot` |
| Manual request regression | `art-gallery-generation::one-validated-service-seam-requests-every-gallery-image` |
| Replacement success/failure regression | `art-gallery-model::monster-subjects-hold-at-most-one-card` |
| Terminal geometry/fallback regression | `art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use` |
| Typed registry reference tests | `art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries` |
| Missing selection/substitute regression | `art-source-fault-facts::faults-are-attributed-to-requested-sources` |
| Creation skip/official suppression controls | `art-gallery-autogen::player-creation-may-skip-the-automatic-portrait` |
| Scene explicit-choice/room-override regression | `scene-artwork-presentation::normal-scenes-use-the-complete-authored-source-chain` |
| Scene selection admission/action regression | `webclient-gallery-management-actions::gallery-mutations-resolve-scene-subjects-through-the-scene-producer` |
| Scene cardless preference/uncapped controls | `art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default` |
| Recovery official-satisfaction controls | `art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies` |
| Creation/import transaction and skip controls | `art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit` |
| Transport parity with suppression/skip | `art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle` |
