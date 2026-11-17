# Proposal

## Why

The existing gallery request requires canonical ages and identity already written on an activated entity. Creation needs a validated draft-value path without writing that identity.

## What Changes

- Register exact `creation.portrait.generate` and route it through a rules-owned request service.
- Share named-policy establishment with activation, compose from validated draft values and enqueue on the same character subject.
- Serialize per-subject admission, track draft-owned image ids and replace only the previous draft image on success.
- Keep receipt discovery through commit under queue-before-database serialization and defer lock-taking commit callbacks until release.
- Extend registry/catalog coverage without inventing a typed command or echoing prompt text.
- Preserve the handoff's diagnostic-only connectivity decision: offline generation fails through the existing worker, not a new preflight probe. This documented deviation from approved §7.3 avoids changing the existing non-gating contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the creation contract owned by this slice.
- `webclient-action-dispatch`: the exact creation action allowlist.
- `webclient-input-narrative`: one bounded portrait-request echo without prompt content.
- `art-gallery-generation`: the validated draft-value request path.
- `art-gallery-autogen`: draft-age exception and activation/rollback ownership.
- `art-subject-model`: draft-value physical description.

## Impact

Pending-character portrait requests. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. One action plus its request/description seam, isolated queue provenance and minimal shared commit-callback deferral. No panel rendering, completion-signal cutover, reset or drawer work; existing validators/worker are reused. This bounded admission unit is one engineer-day; the shared deferral is required by its atomicity, not a separate transaction framework.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

## Batch:

- depends-on: creation-panel-artwork
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. Detailed matrix is in `creation-draft-portrait/design.md`.
- No code/spec conflict with `ciaran-village-local-goods`, `fionnen-village-craft-homes` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
