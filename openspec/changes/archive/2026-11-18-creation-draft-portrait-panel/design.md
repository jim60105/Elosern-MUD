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

Add `read_draft_portrait(character)` to the rules-owned `creation_portrait.py` as a pure immutable read. It never creates policy, receipt, cache or job state. Read request slice's `read_portrait_service_availability()` snapshot; neither reader nor presenter performs a probe. State precedence is: malformed/unauthorized receipt safely unavailable; an already admitted live latest job pending; a current failed service snapshot unavailable with its safe reason; otherwise a successful latest card ready, recorded unsuccessful latest request failed, and no receipt or no remaining current work/card/error empty. Unknown/expired availability does not manufacture a refusal. This is the server-provided signal consumed by slot/drawer; no new availability wire field is needed.

Service unavailability is transient projection, not persisted portrait state: it neither cancels an admitted job nor deletes/hides storage ownership of an existing card. The unavailable view uses the silhouette; after a refreshed healthy/unknown snapshot, the same stored successful card can render ready again. Pending/failed also show silhouette while a retained older card remains stored, per approved §7.1. Explicit `ui_sync` re-renders availability using the existing cache's validity rules; it does not call a probe, refresh cache age or replay generation. The request owner independently refuses known unavailability even if a stale/malicious client ignores disabled controls.

Add a read-only exact-card draft descriptor builder beside the change-1 builders in `world/art/presenter.py`. Resolve only the receipt’s card id on the character’s own `portrait:character:<pk>` subject. Use runtime card identity/version/geometry, ordinary generation truth and the receipt’s validated `fallback_key` for the alpha terminal. No live-character canonical-age eligibility call is appropriate for this already validated pending receipt; no official or unrelated card is substituted. This is a narrow authorized draft-art read, not a global eligibility bypass. Return empty retention sources; the UI deliberately shows a silhouette during pending/failure. Extend the immutable `CreationView`/serialization boundary or pass a separate immutable portrait view into `_serialize`; do not let `world/rules` import web presentation code.

The `official-art-resolution` eligibility delta makes this pending-receipt exception explicit. Its existing ordinary-character rejection scenarios stay unchanged; draft request validation supplies the eligibility proof only for its exact output. This resolves a current-spec conflict inherent in the approved early-generation design.

### Publication and client state

Own the full completion plumbing in `world/art/worker.py`, `world/art/signals.py` and `web/webclient/presentation/art_push.py`. Replace subject-only batch results with immutable completion values containing exactly `subject_key` and canonical UUID `image_id`, captured before settlement deletes the job. `_run_and_settle_batch` returns every applied success/failure; `_fail_batch` returns its actually applied failures instead of discarding them, including client-resolution/constructor failure. Stale-token or deleted-record no-ops return no completion. `_notify_completed_batch` emits both fields on the reactor/calling-test thread, never the generation thread; deduplicate only exact `(subject_key, image_id)` pairs, not different requests sharing a subject. Migrate every signal producer, receiver, fixture and signal-shape assertion in one cutover, with no subject-only compatibility path. Ordinary art/gallery/roster consumers continue matching fresh subject references; image identity only narrows creation qualification.

Extend `_push_for_subject` to render candidate `creation` only for a pending actor whose named subject matches the completed subject and whose current receipt owns the completed image id. Do not rely solely on `portrait.artwork.generation_subject`, which is absent during pending/failed states. Recheck receipt/image qualification in the coordinator's current-context factory, not only at signal receipt: an older queued completion must not qualify after a newer admission/reset. Hand the candidate to the existing `PresentationCoordinator`; preserve its epoch checks, bounded queue, single publication and failure logging. Success and all applied failure paths share this watcher fan-out. A canceled or foreign image does not produce a matching creation candidate.

Request success already declares `creation` affected; its pending panel precedes its result. Settlement is an independent publication group. No timer, browser resubmit or second coordinator is added. Keep the creation store's navigation signature as preset keys/race keys/draft only, but this is not sufficient to preserve fields: fresh decoded panels create a new equal `draft` object and `composables/use-creation-form.js` currently resynchronizes on its identity.

The request slice's offline rejection also declares only `creation` affected. Its publication projects the freshly cached failed verdict without an actor-state write; preserve the same result/revision ordering and input-preserving content guard. Normal explicit synchronization/reconnect recomputes transient availability, so no durable unavailable state needs clearing.

Include `use-creation-form.js`, `CreationOverlay.vue` and `AppClient.vue` explicitly. Compare incoming draft contents using the existing `lib/stable_stringify.js` helper before calling `syncFromDraft`; record the applied signature, not the panel/portrait object identity. An equal draft in the same presentation context is a no-op for every local field, touched flag, concept pin, mode and step. Real draft-content changes, confirmed reset and correlated successful creation save still use the existing guarded synchronization; portrait success/failure never forces it. Pass a presentation-context prop `{generation: store.view.generation, epoch: store.view.epoch}` from `AppClient` to the overlay so a new actor/epoch does not inherit an old actor's equal-draft signature; preserve the existing no-draft/touched-field guards when initializing a lifecycle. This prop is client wiring, not a new wire field or reset on each portrait revision. The final drawer integration consumes the same context prop.

## Risks / Trade-offs

State can be reconstructed after reconnect/restart without a second persisted state machine. Strict state-dependent omission is less permissive than optional-null bags and exposes serializer mistakes early. The authorized draft descriptor deliberately avoids the activated-entity eligibility path; tests must prove it cannot read another subject/id or disclose prompt material.

## Acceptance and documentation

Add `web/webclient/presentation/tests/test_creation_panel/test_portrait.py`; extend `test_validation_core.py`, `test_art_push.py`, `world/art/tests/test_worker/test_gallery_worker.py` and Node `protocol_creation.test.js`, plus a focused store regression in `web/webclient-app/tests/store/creation_portrait.test.js`. Use request-owned synthetic ids, malformed payload matrices and an unrelated-actor control. Exercise real worker → signal → coordinator success, generation failure and client-constructor failure; deliver an older completion after a newer receipt admission. Assert no stale creation candidate, no pending spinner stranded by failure, no presenter writes and one qualifying publication per notification.

Cover cached unavailable → explicit refreshed unknown/healthy → explicit admission without receipt writes or presenter probes, including ready-card preservation and already-admitted pending work. For client-construction failure tests, admit against a successful verdict before injecting worker resolution failure; the new admission gate must not be bypassed by the fixture. Use patched cache clock/configuration or explicit test cache reset, never wall-clock assertions.

Add a mounted-real-overlay regression in existing `web/webclient-app/tests/overlays/creation_overlay.test.js`: begin with a saved custom draft, edit several identity/story/allocation fields, then supply freshly decoded pending/ready/failed creation panels whose draft contents are equal but object identities differ. Preserve every edit, current step and concept revision. Separate controls must prove changed draft contents, confirmed reset, correlated save and new presentation context still synchronize correctly; a store-only test cannot establish field preservation.

Update synthetic creation fixtures to schema 8 and synchronization documentation with the exact union and push scope.

```text
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel.test_portrait web.webclient.presentation.tests.test_creation_panel.test_validation_core
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_art_push
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_worker.test_gallery_worker
node --test web/static/webclient/js/tests/protocol_creation.test.js
pnpm exec vitest run web/webclient-app/tests/store/creation_portrait.test.js web/webclient-app/tests/overlays/creation_overlay.test.js
openspec validate creation-draft-portrait-panel --strict
```
