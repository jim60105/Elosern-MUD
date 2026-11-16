# Tasks

## 1. Replace the job carrier and remove subject-record queue operations

- [ ] 1.1 Start only after `unify-artwork-selection` is implemented and synchronized into main specs. Resolve the retirement deltas against those full requirement blocks, retaining every non-classic predecessor scenario and source policy. Do not reverse apply/archive order or implement concurrently in shared files.
- [ ] 1.2 Replace `store.ArtAssetRecord` with `GalleryJobRecord` and exactly the field boundary in design D1; retain `ArtAssetStatus`. Remove fixed-output, prior-output, publication-token, record seed, hash-review and dead status-rank state. Add no old class alias, migration, dual read or legacy cleanup.
- [ ] 1.3 Migrate `queue.py` to the new carrier. Retain the concrete seams and behavior in design D2; delete `ensure`, `requeue`, `settle`, `settle_generated` and their classic-only helper paths. Implement `failed_keys` from gallery error accessors, and useful `is_gallery_job` validation. Preserve direct per-subject pending lookups, one queue lock, lease reclaim, fresh claim tokens, membership validation and publication pause.
- [ ] 1.4 Rewrite `test_queue.py`, `test_scheduler.py` and `server/saves/tests/test_lease_reclaim.py` around real gallery enqueue/claim. Preserve deterministic ordering, lease expiry, stale claim and save publication-barrier assertions. Update the shared worker/service fixture helpers before migrating their consumers.

## 2. Remove fixed-output publication, presentation, migration and serving

- [ ] 2.1 Make `worker.output_identity_for` gallery-only; delete `expected_output_identity`, `_prior_output`, classic publish/failure/cleanup branches and unused imports. Preserve translation/cutout/encode ordering, atomic temp-file publication, claim-time success/failure token guards, exact request provenance and capped cleanup-after-commit.
- [ ] 2.2 Remove the temporary classic slot and `supports_classic_source` field from the predecessor's shared enumerator/declaration, and remove `presenter._record_for`, `_classic_attempts`, `_published_output_version` and unused record fields. Derive generation state only from live jobs, gallery errors and cards. Delete classic source id/rank/prefix helpers from `descriptors.py`, preserving all live ranks and canonical wire shapes.
- [ ] 2.3 Delete the seven named conversion/file helpers and `migrate_classic_scene_records` in design D5. Remove `art_scene_migration` from `server/conf/at_server_startstop.py` and its startup observability test catalog. Restrict prune job scans to `GalleryJobRecord`; keep gallery orphan cleanup, current species checks and `gallery_seed.py` active.
- [ ] 2.4 Remove fixed scene/portrait admission and done-record scans from `web/art_media.py`; keep exact gallery-card, official, bundled and alpha serving with confinement/404 behavior. Remove obsolete identity URL declarations only if their route is separate; keep the shared dispatcher. Convert `web/gm/readers/art.py` to live gallery-job inspection and migrate any actual committed-output field consumer in the same change.
- [ ] 2.5 Migrate remaining concrete fixture consumers in `commands/tests/test_character_creation/_support.py`, `web/webclient/presentation/tests/test_party_panel.py`, `web/tests/browser/seed/exploration_fixture.py` and `web/browser_support/unified_image_transitions.py` to real gallery enqueue/card state. Migrate direct old-carrier references in official catalog/provenance, species identity, gallery match, scene/presenter/source-fault tests. Remove import-only obsolete record assertions rather than introducing a fake model.
- [ ] 2.6 Migrate `web/gm/dashboard.py::_art` to live `GalleryJobRecord` counts and `gallery.erroring_subjects()` failure rows per design D4, preserving transport/status keys and section isolation. Replace old-carrier sources/fixtures in `web/gm/tests/test_dashboard.py`, `test_runtime_immutability.py`, `test_state_api.py` and the opaque typeclass fixture in `web/admin-app/tests/json-tree.test.js`. Assert recorded failures survive terminal deletion, clear after success, and dashboard/state reads perform no writes.

## 3. Complete staff cutover and regression replacement

- [ ] 3.1 In `commands/art.py`, remove classic status/retry/requeue branches, use gallery accessors and the retained `failed_keys` seam, and change health's record section to live pending/in_progress job counts. Preserve permission, filters, sensitive-data exclusions, one forced probe and failure-isolated gallery retry. Update `commands/tests/test_art.py` for gallery-only outcomes.
- [ ] 3.2 Delete conversion-only tests in `test_service/test_gallery_prune.py` and fixed-output/hash-review tests in queue/worker suites. Rewrite mixed tests in `test_worker/test_gallery_worker.py`, `test_cutout_failure.py`, `test_cutout_stage.py`, `test_output_format_pipeline.py`, `test_store_isolation.py`, `test_translate_stage.py` and `test_subjects.py` around gallery jobs and card identities. Preserve metadata/alpha, path confinement, UTF-8 bounds, lease, stale success/failure and no-network mechanisms.
- [ ] 3.3 Add `world/art/tests/test_gallery_only_cutover.py` with at most ten deterministic integration methods covering gallery-only enqueue/settle deletion, capped failed/successful replacement, stale success/failure, generation state, 404 for former fixed routes and surviving gallery/official/bundled/default serving. Use synthetic registries, temp roots and injected image client, never shipped artwork or copy.
- [ ] 3.4 Update `test_art_observability.py`, cutout and startup event assertions so job/subject/image context is captured before deletion. Keep exactly one claim/settle and generate/settle pair per current job; remove only migration events. Keep `world.observability` named imports and exceptions with `exc=`; do not expand the freeze.

## 4. Current documentation and traceability cutover

- [ ] 4.1 Update `docs/development/official-artwork-deployment.md`, `docs/game/commands.md` and `docs/game/command-reference.md` for removed fixed-output behavior, gallery-only status/retry/requeue/health, immutable media and no migration. Update current engine artwork sections and unified-image policy sections, plus current GM operations descriptions that name subject records. Preserve historical archives as history.
- [ ] 4.2 Preserve mechanism tests for all eleven relocated lifecycle guarantees in `test_service/test_art_service.py`, `test_autogen_retrofit.py`, `test_gallery_request_seam.py`, creation/import/spawn tests and startup tests. Remove retired annotation IDs from each actual affected test individually; record “test method -> delta requirement/scenario” in the implementation handoff before changing decorators. Do not automatically replace IDs across files or annotate unrelated tests.
- [ ] 4.3 Use `uv run --locked python -m tools.spec_traceability list` and literal IDs from the canonical table below for retained MODIFIED contracts. Newly ADDED replacement and relocated requirements have no current canonical IDs: implement behavior tests without guessed/borrowed decorators and hand off the exact scenario mapping for the authorized archive worker to retrieve and annotate after synchronization. The `--change` gate tolerates only explicitly REMOVED current requirements, never missing tests for retained requirements.
- [ ] 4.4 Run `uv run --locked python -m tools.shard_register fix` whenever a test module is added/deleted/renamed; commit generated manifest changes. Do not hand-edit manifests. There are no compatibility tests to retain for deleted classic APIs.

## 5. Focused acceptance after all changes land

Run commands individually, never inside wrappers or chained to other shell commands. Use module labels rather than package discovery; every new regression module is bounded below 100 tests. No full browser suite, CI shard command or aggregate evidence verification.

- [ ] 5.1 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_gallery_only_cutover`
- [ ] 5.2 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_queue`
- [ ] 5.3 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_worker.test_gallery_worker`
- [ ] 5.4 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_worker.test_cutout_failure`
- [ ] 5.5 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_worker.test_output_format_pipeline`
- [ ] 5.6 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb server.saves.tests.test_lease_reclaim`
- [ ] 5.7 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb commands.tests.test_art`
- [ ] 5.8 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb server.conf.tests.test_startup_observability`
- [ ] 5.9 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_art_observability`
- [ ] 5.10 `uv run --locked python -m unittest tests.test_command_docs`
- [ ] 5.11 `uv run --locked python -m tools.observability_lint check`
- [ ] 5.12 `uv run --locked python -m tools.contract_gate --change retire-classic-art-assets`
- [ ] 5.13 `openspec validate retire-classic-art-assets --strict`
- [ ] 5.14 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.gm.tests.test_dashboard`
- [ ] 5.15 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.gm.tests.test_runtime_immutability`
- [ ] 5.16 `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.gm.tests.test_state_api`
- [ ] 5.17 `pnpm exec vitest run web/admin-app/tests/json-tree.test.js`

Expected state is successful focused tests, no active import/caller of removed classic APIs, no fixed output media serving, no migration startup step, preserved gallery/seed generation, and strict validation without warnings. Development databases are not reset by these tasks.

## Canonical IDs for retained mechanism tests

IDs below were obtained from the canonical list command. Apply `covers_requirement` only to discoverable assertions that substantively establish that specific requirement.

| Assertion owner | Literal canonical ID |
| --- | --- |
| Gallery record serialization/read-only tests | `art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default` |
| Card rectangle/unknown-size fallback tests | `art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant` |
| Validated manual request tests | `art-gallery-generation::one-validated-service-seam-requests-every-gallery-image` |
| Unregistered species gallery prune tests | `art-gallery-generation::the-startup-prune-reclaims-stored-art-of-unregistered-monster-keys` |
| Encoding/format replacement tests | `art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality` |
| Typed subject parsing tests | `art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access` |
| UTF-8 key-bound tests using per-image paths | `art-stable-key-contract::stable-keys-share-one-producer-contract` |
| Source-attribution regression | `art-source-fault-facts::faults-are-attributed-to-requested-sources` |
| Gallery-only generation truth regression | `artwork-descriptor::descriptors-preserve-independent-artwork-facts` |
| Official priority regression | `official-art-resolution::the-extended-chain-stays-deterministic-offline-and-side-effect-free` |
| Retained stale-selection preference tests | `official-art-personalization::stale-official-selections-are-retained-but-ignored-for-resolution` |
| Portrait source ordering tests | `portrait-source-attempts::portrait-source-order-retains-current-policy` |
| Cross-species isolation tests | `species-portrait-identity::monster-portraits-never-borrow-runtime-state-across-visual-species` |
| Source-specific stage tests | `webclient-art-panel::resolved-artwork-carries-stage-without-changing-asset-or-placeholder-truth` |
| Default deletion tests | `webclient-gallery-management-actions::default-set-and-card-delete-follow-the-shipped-delete-never-dangles-contract` |
| Party canonical portrait reference tests | `webclient-party-panel::the-party-panel-is-an-exact-read-only-version-3-presentation-panel` |
| Queue boundary event tests | `art-queue-worker::worker-claim-and-settle-emit-boundary-events` |
| In-flight wire-state tests | `art-queue-worker::in-flight-generation-exposes-a-wire-stable-status` |
| Gallery-only declaration contract tests | `art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do` |
| GM live-count, durable-error and read-only tests | `gm-operations-dashboard::independent-read-only-dashboard-sections` |

## Replacement requirement traceability handoff

The following table records deliberate mechanism rewrites. Existing old IDs retire; new IDs must come from the canonical list after spec synchronization. None is a compatibility alias.

| Capability / old requirement | New requirement | Assertion owner |
| --- | --- | --- |
| art-gallery-autogen / Automatic character portraits produce exactly one unbound default card | Automatic generation publishes gallery defaults only | service autogen tests |
| art-gallery-fallback / The fallback seam supplies a URL and a face rectangle and reports its use | Declared terminal resources retain geometry and observability | shared terminal regression |
| art-gallery-resolution / Display resolution is one deterministic chain from equipment to fallback | All artwork subjects use the gallery-only deterministic chain | shared-chain regression |
| art-gallery-resolution / Monster subjects resolve through the chain without the binding steps | Declared binding support gates shared resolution | declaration mutation tests |
| art-gallery-resolution / Every resolution payload carries a face rectangle or null | Gallery and official resources carry their own geometry | presenter geometry tests |
| art-portrait-cutout / Character and monster portraits are stored with their background removed | Gallery portraits publish background-removed artifacts | cutout-stage tests |
| art-portrait-cutout / A background-removal failure is a bounded, terminal, non-degrading job failure | Gallery cutout failure preserves existing cards | cutout-failure tests |
| art-prompt-translation / The translation stage sits between the claimed description and the generation call | Gallery descriptions pass through configured prompt translation | translation-stage tests |
| art-queue-worker / Asset records carry the full contract and never a live object reference | Gallery jobs carry transient request state only | queue serialization and settle tests |
| art-queue-worker / The queue is keyed by subject identity and enqueue is idempotent | Gallery image requests own independent queue jobs | independent enqueue tests |
| art-queue-worker / Scenes and portraits share one serialization lock and one worker concurrency slot | Gallery jobs share one lock and worker slot | concurrent drain tests |
| art-queue-worker / The internal worker contract generates every output through the sd-webui client and confines paths to the store root | Gallery workers publish confined immutable image outputs | gallery worker and fault injection tests |
| art-queue-worker / Media serving maps validated stored identities to same-origin URLs without exposing the store root | Runtime media serves gallery card identities only | gallery-only media regression |
| art-staff-commands / @art status lists and filters records without leaking sensitive data | Staff status reports gallery holdings without sensitive data | command status tests |
| art-staff-commands / @art retry re-enqueues failed records | Staff retry re-drives recorded gallery failures | command retry tests |
| art-staff-commands / @art requeue accepts one validated full subject key and forces regeneration under the lock | Staff requeue forces one validated gallery request | command requeue tests |
| art-staff-commands / @art health reports server reachability, scheduler state, queue counts, and output policy | Staff health separates live jobs from gallery outcome state | command health tests |
| internal-art-worker / Art generation prompts are stored in the prompt library | Prompt library edits affect subsequent gallery requests only | prompt/worker provenance tests |

Eleven active lifecycle requirements move to `art-gallery-autogen` with their full non-classic guarantees. The conversion requirement and completed-record hash-review requirement are removed with no successor. The authorized archive handoff must annotate the new canonical IDs without a waiver after synchronization.
