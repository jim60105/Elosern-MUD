# Design

## Context

See `proposal.md`. This change consumes the request slice’s persistent `creation_portrait` receipt and existing gallery job/card/error reads. `art_push.py::_push_for_subject` currently considers only art/gallery/roster. The creation store signature already compares preset keys, race keys and draft, excluding art and proposal; preserve that separation.

## Goals / Non-Goals

**Goals:** exact schema 8 and reconstructible read-only portrait state with completion pushes.

**Non-Goals:** new requests, alternate transport/result envelopes, drawer code, polling, new persistent state, draft version changes or reset cleanup.

## Decisions

### Exact wire union

Move `CREATION_SCHEMA_VERSION` from 7 to 8 in presenter/mirror/fixtures. This is the second and final panel-shape increment for the approved feature; UI/action/lifecycle changes do not increment it. Available keys are exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`, `portrait`, plus optional `proposal`. Unavailable uses the registered common shape, with no portrait. Keep the single version authority requirement established by change 1.

The exact union is:

| status | required keys | forbidden keys |
| --- | --- | --- |
| empty | status | artwork, reason |
| pending | status | artwork, reason |
| ready | status, artwork | reason |
| failed | status, reason | artwork |
| unavailable | status, reason | artwork |

`reason` is nonblank safe server-owned zh-TW text, at most 512 code points; never raw exceptions, URLs, prompts or credential-bearing endpoint details. `artwork` validates through the existing canonical validator. A reason or artwork cannot be null. Both validators reject extra keys, missing fields and invalid status/type combinations, retaining the existing canonical-byte limit.

### State reader and descriptor

Add `read_draft_portrait(character)` to the rules-owned `creation_portrait.py` as a pure immutable read. It never creates a missing policy/record/receipt. No receipt means empty; a malformed receipt is safely unavailable with a bounded diagnostic/reason, never silently repaired. For a valid receipt, the latest id’s live job yields pending; its successful card yields ready; an unsuccessful latest request with the gallery's recorded error yields failed. A retained previous card is preserved in storage but pending/failed still show the silhouette, per approved §7.1. A valid receipt with neither live job, current card nor recorded error is empty, permitting explicit retry rather than fabricating progress. `unavailable` is a structural authorization/receipt failure, not an offline connectivity verdict. Neither this reader nor presenter calls/imports a probe; offline attempts follow the request design's ordinary pending-to-failed path.

Add a read-only exact-card draft descriptor builder beside the change-1 builders in `world/art/presenter.py`. Resolve only the receipt’s card id on the character’s own `portrait:character:<pk>` subject. Use runtime card identity/version/geometry, ordinary generation truth and the receipt’s validated `fallback_key` for the alpha terminal. No live-character canonical-age eligibility call is appropriate for this already validated pending receipt; no official or unrelated card is substituted. This is a narrow authorized draft-art read, not a global eligibility bypass. Return empty retention sources; the UI deliberately shows a silhouette during pending/failure. Extend the immutable `CreationView`/serialization boundary or pass a separate immutable portrait view into `_serialize`; do not let `world/rules` import web presentation code.

The `official-art-resolution` eligibility delta makes this pending-receipt exception explicit. Its existing ordinary-character rejection scenarios stay unchanged; draft request validation supplies the eligibility proof only for its exact output. This resolves a current-spec conflict inherent in the approved early-generation design.

### Publication and client state

Extend `_push_for_subject` to render candidate `creation` only for a pending actor whose named subject matches the settled job and whose receipt owns that image. Do not rely solely on `portrait.artwork.generation_subject`, which is absent during pending/failed states. Hand the candidate to the existing `PresentationCoordinator`; preserve its current-context rebuilding, epoch checks, bounded queue, single publication and failure logging. Success and failure settlements both trigger the existing asset-completion signal; reuse its watcher fan-out. A canceled or foreign image does not produce a matching candidate.

Request success already declares `creation` affected; its pending panel precedes its result. Settlement is an independent publication group. No timer, browser resubmit or second coordinator is added. The creation store signature remains preset keys/race keys/draft only; portrait updates must not navigate the dock, reapply concepts, remount the form or reset local steps.

## Risks / Trade-offs

State can be reconstructed after reconnect/restart without a second persisted state machine. Strict state-dependent omission is less permissive than optional-null bags and exposes serializer mistakes early. The authorized draft descriptor deliberately avoids the activated-entity eligibility path; tests must prove it cannot read another subject/id or disclose prompt material.

## Acceptance and documentation

Add `web/webclient/presentation/tests/test_creation_panel/test_portrait.py`; extend `test_validation_core.py`, `test_art_push.py` and Node `protocol_creation.test.js`, plus a focused store regression in `web/webclient-app/tests/store/creation_portrait.test.js`. Use request-owned synthetic ids, malformed payload matrices and an unrelated-actor control. Assert pending and both settlement outcomes, reconnect reconstruction, no presenter writes, one matching publication and unchanged step/field state.

Update synthetic creation fixtures to schema 8 and synchronization documentation with the exact union and push scope.

```text
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel.test_portrait web.webclient.presentation.tests.test_creation_panel.test_validation_core
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_art_push
node --test web/static/webclient/js/tests/protocol_creation.test.js
pnpm exec vitest run web/webclient-app/tests/store/creation_portrait.test.js
openspec validate creation-draft-portrait-panel --strict
```
