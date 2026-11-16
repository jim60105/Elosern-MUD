# Proposal

## Why

Every shipped art kind generates gallery cards, yet the unused classic fixed-output model still owns queue branches, presentation fallback, media serving and startup conversion. Remove that dormant system completely while retaining gallery generation.

## What Changes

- **BREAKING**: delete `ArtAssetRecord`, classic fixed identities, classic enqueue/requeue/settle APIs, portrait classic source positions and classic scene startup migration.
- Replace the shared physical record carrier with a gallery-only `GalleryJobRecord`, retaining gallery request metadata, leases, claim tokens and shared status vocabulary.
- Keep `GalleryRecord`, immutable per-image gallery outputs, seed synchronization, job serialization and failure isolation.
- Retain public gallery queue seams, including `record_key`, `is_gallery_job` and `failed_keys`, with useful gallery-only contracts and no compatibility aliases.
- **BREAKING**: staff status/retry/health report gallery holdings, errors and live jobs rather than classic terminal records; requeue remains an explicit gallery generation request.
- Delete or rewrite classic-only tests and fixtures, update traceability, shard ownership, current documentation and architecture descriptions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-asset-lifecycle`: remove classic lifecycle requirements; preserve active lifecycle guarantees in gallery autogeneration.
- `art-queue-worker`: gallery-only jobs, worker and media.
- `art-gallery-resolution`: remove classic position and geometry.
- `art-staff-commands`: gallery-only status, retry, requeue and health.
- `art-gallery-autogen`: retain active startup/creation/import/spawn/entry lifecycle.
- `art-gallery-model`: remove classic storage/geometry references.
- `art-gallery-generation`: gallery-only prune and request guarantees.
- `art-portrait-cutout`: gallery publication/failure semantics.
- `art-output-format-pipeline`: per-image outputs and replacement safety.
- `art-subject-model`: gallery-only typed accesses.
- `internal-art-worker`: remove completed-subject digest review.
- `art-stable-key-contract`: retain key limits without classic identity rationale.
- `art-source-fault-facts`: no classic fault sources.
- `artwork-descriptor`: gallery-only generation truth.
- `official-art-resolution`: remove classic priority references.
- `official-art-personalization`: remove classic stale-selection fallback.
- `art-gallery-fallback`: remove classic worker terminology.
- `art-gallery-kind-capabilities`: remove the predecessor's temporary classic-read declaration.
- `art-prompt-translation`: translate gallery jobs without a classic publication branch.
- `portrait-source-attempts`: remove classic attempt order.
- `species-portrait-identity`: keep species isolation with gallery runtime state only.
- `webclient-art-panel`: remove classic stage/default examples.
- `webclient-gallery-management-actions`: deletion falls to official/terminal sources.
- `webclient-party-panel`: remove classic portrait precedence.

## Impact

Targets `world/art/`, `commands/art.py`, startup, media routes, GM readers, save/lease consumers and deterministic test/browser-seed fixtures. Update deployment and both command guides. Pre-release cutover has no data conversion, dual reads, aliases or startup cleanup of retired records. Existing development databases must be recreated outside application code. No child repositories are needed. Human review concerns policy/document consistency in `design.md`; there is no new visual fidelity requirement.

## Batch:

depends-on: unify-artwork-selection

Apply and archive after `unify-artwork-selection`. Shared capabilities include resolution, autogen, model, generation, subject-model, source-fault-facts and official/fallback policy. Shared code includes presenter/service and their tests. Replay the predecessor's full modified blocks and added scenarios before applying this change; delete only classic contracts. No concurrent edits or reversed archive order.
