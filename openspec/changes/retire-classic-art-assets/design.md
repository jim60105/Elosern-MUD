# Design

## Context

See proposal.md for motivation. This is a single-repository pre-release deletion/refactoring change, bounded to one engineer-day (about eight hours including focused regression gates). It follows `unify-artwork-selection`, whose priority, suppression and preference behavior must survive unchanged.

| Evidence | Removal boundary |
| --- | --- |
| `world/art/store.py:42-80` | `ArtAssetRecord` combines fixed-output state with gallery job fields. Deleting the class without replacing its job carrier would break the live worker. |
| `world/art/queue.py:80-117,143-278,336-478,518-688` | Subject ensure/requeue/settle are classic-only; gallery enqueue/claim/token settle are live. |
| `world/art/worker.py:93-116,310-375,489-502` | Expected fixed identity and classic publish branch are obsolete; claim-time token snapshot is required for stale-settle safety. |
| `world/art/presenter.py:130,337-414,498-503,879-891` | Classic lookup, attempts, version helper and generation truth still read fixed-output state. Scene generated art already reads gallery cards. |
| `world/art/service.py:707-861` | Classic scene conversion, file cleanup and startup migration are isolated deletion targets. |
| `server/conf/at_server_startstop.py:653` | `art_scene_migration` invokes that conversion before prune. |
| `web/art_media.py:64,128`; `web/gm/readers/art.py:57-59` | Media and GM inspection still query classic record class. |
| `web/gm/dashboard.py:270-297` | Dashboard directly imports the classic carrier and builds failure rows from terminal records, so both its count and error sources must change. |
| `commands/art.py:27-28,174,192,332` | Staff commands retain unreachable classic requeue/retry and terminal record reporting. |
| `server/saves/tests/test_lease_reclaim.py:9-22` | Save/lease regression fixtures depend on classic enqueue even though the lease mechanism remains live. |

The supplied runtime observation of no classic records/outputs is accepted. No live database inspection or destructive reset is part of planning.

## Goals / Non-Goals

Remove the entire fixed-output lifecycle, including unreachable writers/readers, model fields, media admission, startup conversion, fixtures and current contracts. Preserve real gallery, seed, queue, prompt, cutout, encoding, offline and publication barriers.

Non-goals are gameplay changes, new settings, artwork changes, changing the sibling's source policy, migrations, compatibility aliases, a legacy cleanup command, retained job history, browser architecture changes and unrelated refactoring. No branch, worktree, archive or implementation is authorized by this proposal.

## Decisions

### D1. Replace the physical carrier cleanly

In `world/art/store.py`, replace `ArtAssetRecord` with `GalleryJobRecord(DefaultScript)`. No alias, old class registration, legacy manager or typeclass migration remains. Keep `ArtAssetStatus` and the fields actually read during gallery job lifetime:

```text
kind, subject_key, source_description, source_hash, prompt_digest,
generation_token, status, attempt_count, last_error_code,
enqueued_at, claimed_at, completed_at, aspect_ratio,
gallery_image_id, gallery_binding, gallery_face_rect, gallery_requested_fields
```

Remove `output_identity`, `prior_output_identity`, `published_generation_token`, `hash_changed` and record-level `seed`. Seed, actual prompt pair, checkpoint and decoded image size remain on committed gallery cards; job prompt digests remain request metadata, never a completed-subject review workflow. Remove status-rank/consolidation helpers once their subject-record consumers are deleted.

Do not migrate existing records. Development/test state is recreated by its owner when needed, outside application startup. New jobs use the new typeclass immediately; no old-class import path may be retained for old databases.

### D2. Keep useful gallery queue contracts

Retain these names and real behavior:

| Seam | Contract after cutover |
| --- | --- |
| `record_key(subject)` | Return `art:<full-subject-key>` as the job-key prefix only; never read/create a record at that prefix. |
| `gallery_record_key(subject, image_id)` | Return the per-image job key with `:gen:<image-id>`. |
| `is_gallery_job(record)` | Validate gallery job type and nonempty image id/key shape; malformed synthetic or foreign records return false. It must not become an unconditional compatibility stub. |
| `gallery_job_in_flight`, `pending_gallery_jobs` | Direct gallery job lookup scoped to subject; retain lease state reporting. |
| `enqueue_gallery_job` | One new job per accepted request under the queue lock, retaining capability and membership validation. |
| `claim`, `reclaim_expired_leases` | Claim gallery jobs only, with current membership and existing deterministic ordering/lease bounds. |
| `settle_gallery_generated`, `settle_gallery_failed` | Validate claim-time token under lock; publish card or recorded error, then delete the terminal job. Stale token changes nothing. |
| `failed_keys()` | Return unique sorted canonical subject keys from the gallery error accessor; deleted terminal jobs are never a retry database. |

Delete `ensure`, `requeue`, `settle`, `settle_generated`, their `_settle_by_key`/`_settle_generated_by_key` paths, `_records_for`/find-or-create/consolidation helpers and classic prior-output cleanup. Keep shared token/temp-file/confinement helpers only where gallery paths use them. Keep lock order `queue_lock -> gallery_lock`, one worker slot and publication pause semantics used by saves.

### D3. Publish only per-image gallery output

`worker.output_identity_for` accepts a gallery job and constructs `gallery/<declared-directory>/<subject-key>/<image-id><extension>`. Invalid metadata rejects; it never falls back to a fixed path. Delete `expected_output_identity`, `_prior_output`, classic `_publish`/failure branches and fixed-output deletion logic.

Keep claim-time snapshots across every asynchronous boundary, translation before request construction, cutout before encoding, atomic temporary-file publication and actual request provenance. On failure existing cards/files remain; on a capped successful replacement the gallery writer commits the new card/default before deleting its displaced unreferenced file. A cleanup failure leaves an orphan with a bounded diagnostic and never reverses publication. Startup gallery orphan prune remains the recovery owner.

### D4. Remove all classic presentation and media access

Remove `_record_for`, `_classic_attempts`, `_published_output_version` and classic resource/version fields from presenter enumeration; after the predecessor, remove the temporary classic slot and `supports_classic_source` declaration field from their shared owners too. `_generation_facts` reads live jobs, gallery error and cards in that order. Official sources cannot change it to done.

Remove `portrait_classic_source_id`, its source prefix/rank and dead fixed-path version helper from `descriptors.py` only if no retained gallery consumer uses it. Preserve other source ids/ranks; there is no need to renumber existing layers or accept two descriptor shapes.

In `web/art_media.py`, remove fixed scene/portrait `_ALLOWED_IDENTITY` admission and its scan of `ArtAssetRecord`. Keep exact card-referenced gallery admission and official/bundled/default roots, symlink refusal and closed extensions. `web/urls.py` may retain the shared `/art/<identity>` dispatcher, but former fixed identities must return 404. No file existence fallback or conversion is allowed. Retain immutable gallery media serving through configured-format changes.

GM art inspection changes its job list query to `GalleryJobRecord`. Preserve the existing GM transport shape unless a field describes classic committed output, in which case remove that field and migrate its concrete consumer together. Gallery holdings remain read through gallery accessors.

`web/gm/dashboard.py::_art` also changes in this cutover. Preserve `{counts, drain, failures}` and the existing status-key vocabulary: counts measure current `GalleryJobRecord` rows, so missing/done/failed counts are zero after ordinary terminal deletion, without claiming historical totals. Build newest bounded failure rows from `gallery.erroring_subjects()` using its subject key/kind, bounded error and recorded error timestamp. A later successful publication clears the error and its dashboard row. Preserve the existing row keys and limit/order, so `web/admin-app/views/overview/ArtPanel.vue` and `lib/dashboard.js::ART_SEGMENTS` need no alternate shape or compatibility path. Update the old typeclass fixture in `web/admin-app/tests/json-tree.test.js` without copy/markup assertions. Dashboard failures remain section-local and all reads remain non-creating.

### D5. Delete conversion, retain startup and staff behavior

Delete service helpers `_classic_scene_output_identities`, `_delete_classic_scene_files`, `_scene_created_at`, `_scene_image_size`, `_convert_classic_scene_output`, `_migrate_classic_scene_record` and `migrate_classic_scene_records`, plus the `art_scene_migration` startup step and its catalog/test patch target. Prune scans `GalleryJobRecord` and gallery records only. `gallery_seed.py` remains active and unchanged except an import/docstring made obsolete by the carrier rename.

`CmdArtStatus` reports gallery holdings/default/error through accessors, with jobs still hidden. Delete the empty classic-record section and completed seed rows. `CmdArtRetry` uses `failed_keys` and `retry_gallery_subject`, reporting one gallery request count; official-satisfied/in-flight/ineligible declines retain errors, card-satisfied declines clear moot errors. `CmdArtRequeue` always uses the validated gallery force path or rejects gallery-less declarations. `CmdArtHealth` keeps five sections but replaces terminal record counts with live pending/in_progress gallery-job counts. No new command or old-output compatibility wording remains.

### D6. Retire obsolete contracts explicitly

All twelve `art-asset-lifecycle` requirements are REMOVED. Eleven active lifecycle guarantees are re-owned under `art-gallery-autogen`; conversion is removed outright. The sole-writer and named-spawn titles are revised for gallery terminology. Lifecycle scheduling, canonical ages, post-commit transaction ownership, explicit skip, official satisfaction, transport parity, failure isolation, startup ordering and deletion suppression remain required. No tests of these real guarantees are deleted merely because the old capability is retired.

OpenSpec strict validation refuses omitted scenarios in a MODIFIED block. Requirements containing deleted classic scenarios therefore use explicit REMOVED plus ADDED gallery replacement contracts, with reasons and no-migration instructions. This is a behavior retirement, not a scenario-loss workaround or validation waiver. The rewrite ledger below records each replacement. Other blocks remain MODIFIED with their full retained scenarios.

The delta also revises `art-prompt-translation`, `portrait-source-attempts`, `species-portrait-identity`, `webclient-art-panel`, `webclient-gallery-management-actions` and `webclient-party-panel`, because current contracts there still name classic sources. Preserve their unrelated scenarios and current wire shapes.

### D7. Observability survives terminal job deletion

Keep `sd_job_claim`, `sd_job_settled`, `gallery_generate`, `gallery_settle`, `art_cutout_done`, `art_cutout_failed` and the predecessor's suppression event. Snapshot job/subject/image ids before deleting the job so terminal boundary events remain attributable. Remove `art_scene_migration` and `art_scene_migration_failed` emitters, startup registrations and obsolete assertions. Production exceptions re-raise or carry named `world.observability` events with `exc=` and identifier context. No freeze additions or log suppression.

## Requirement rewrite ledger

The explicit gallery replacements are listed in tasks.md's traceability handoff table. Retired subject-record hashing and scene conversion have no replacement. The eleven active lifecycle requirements move from `art-asset-lifecycle` to `art-gallery-autogen`; the sole-writer title becomes “Gallery lifecycle writes stay inside the deterministic art owner”. Their mechanism assertions survive and must be re-annotated only after synchronization supplies real canonical IDs.

## Sequencing and conflict matrix

| Predecessor | Required state | Shared requirement areas | Code conflict | Archive order |
| --- | --- | --- | --- | --- |
| unify-artwork-selection | Implemented and main specs synchronized before retirement integration | Shared chain, default generation, fallback terminal, generation seam, model, typed subject, fault attribution and official selection | presenter/gallery_match, service, gallery actions/read models and overlapping tests | unify first, retire second |

Retirement's shared blocks already include predecessor scenarios. Before apply, resolve CLI artifacts against the then-current main specs and preserve all non-classic additions. No parallel cutover of shared files and no reverse archive order. No child repository participates.

The exact shared requirement blocks are listed here without a dependency on a sibling artifact path. Relocation preserves the predecessor's recovery, creation-skip and transport-parity qualifications.

| Capability | Shared requirement |
| --- | --- |
| art-gallery-autogen | Automatic character portraits produce exactly one unbound default card |
| art-gallery-resolution | Display resolution is one deterministic chain from equipment to fallback |
| art-gallery-resolution | Monster subjects resolve through the chain without the binding steps |
| art-gallery-kind-capabilities | One closed declaration states what every subject kind's gallery may do |
| official-art-resolution | The extended chain stays deterministic, offline, and side-effect-free |
| art-gallery-model | One gallery record per art subject carries an ordered card list and a default |
| art-gallery-fallback | The fallback seam supplies a URL and a face rectangle and reports its use |
| art-gallery-generation | One validated service seam requests every gallery image |
| art-source-fault-facts | Faults are attributed to requested sources |
| art-asset-lifecycle | Startup recovery rescans explicit unique portrait policies |
| art-asset-lifecycle | Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit |
| art-asset-lifecycle | Every player-activation path finalizes the portrait lifecycle |

## Risks / Trade-offs

Carrier rename invalidates old development databases intentionally. A model-only deletion without fixture migration would break commands, media, scheduler and save lease tests; these are one cutover. Deleting terminal jobs must not erase failure visibility, so gallery errors and boundary events remain durable. Removing terminal records also removes their staff seed rows; seeds remain inspectable on gallery cards and generation metadata, not reconstructed history.

Keeping the old typeclass as a gallery alias, leaving unreachable fallback branches, migrating old images, creating a cleanup command or weakening strict validation are rejected alternatives. The bounded approach changes existing modules and tests, adding no new package or architecture.

## Test strategy and acceptance

Use existing synthetic art subjects/registries and temp roots, injectable image/translation/cutout clients and fixed clocks. Rebuild classic fixture helpers around `enqueue_gallery_job` and real gallery card append. Preserve stale success/failure, atomic write rollback, capped replacement cleanup, format/metadata/alpha, portrait/scene eligibility, startup ordering, save lease and publication-pause coverage.

Delete only classic-fixed-output, classic hash-review and conversion-only tests. Replace mixed tests with gallery publication assertions; never remove a meaningful concurrency/failure assertion without its gallery equivalent. Browser seed fixtures must use gallery APIs, but this refactor requires no full browser run or browser-only behavior gate.

Expected state is no `ArtAssetRecord`, fixed-output APIs, classic source slots or startup migration in production/current contracts/active test fixtures; gallery jobs still generate, settle, retry, reclaim and serve exact cards. Historical OpenSpec archives and historical approved design chronology are not rewritten. Current policy sections and deployment/command guides are updated. Focused commands and traceability handoff are in tasks.md. Open questions: none.
