# Bounded complete recovery

## Context

D rejects incompatible bases; A rejects incomplete or corrupt multipart publications. Current app `stores/elosern/transport.js` watches invalid/missing_envelope presentation results, while `use-resync.js` and bridge.js share a one-request presentation guard. `releaseIfReady` waits for a revision but a newer claimed action result currently does not actively initiate recovery. Preserve request deduplication, disconnect uncertainty and the no-automatic-mutation-resubmit policy.

## Goals / Non-Goals

One automatic complete repair per failure episode, coalesced across every failure source. No normal-path ACK, retry loop, historical replay, manual state patch or action re-execution.

## Decisions

Reducer owns recovery state `{status:"idle"|"needed"|"requested"|"failed", cause, generation}` in addition to committed presentation. Failures are base_mismatch, invalid/missing_envelope, A assembly failure/expiry, recoverable server presentation error and matching action result claiming `presentation_revision > committed revision`. Lock mutations immediately, preserve committed data and its revision, and mark presentation unavailable through the existing view failure surface. Do not erase last complete panels to simulate a commit. Stale generations/epochs/targets and ordinary duplicate results do not trigger recovery.

Expose reducer `markRecoveryRequested()` and `failRecovery(cause)` for the app's sender/timeout owner, plus committed read-only recovery state. requestResync("presentation") in bridge.js becomes the single coalescing request gate, driven from use-resync.js and reducer changes. Remove the parallel generation-only guard as an independent authority; bridge delegates to reducer state. If disconnected, record needed without sending and reconnect uses the existing initial-sync lifecycle. Once a sendSync is issued set requested. No new ui_sync fields or acknowledgement are added. Every ui_sync still asks ingress for a freshly rendered complete eager snapshot.

The automatic repair response uses the same general assembly limits. Start one 30000ms recovery response deadline at sendSync; C/A's independent assembly deadline starts at its first part. Expiry of either while requested marks failed and cancels outstanding recovery timers/buffers. If a repair snapshot or its parts fail validation/assembly, status becomes failed immediately and no second automatic sync is sent. Unrelated traffic, partial parts, deltas and action results cannot clear/rearm a failed episode. A valid newer complete snapshot for the live sequence clears recovery/error state and unlocks only when existing protocol and action-result gates also allow it. A new transport generation resets recovery; an explicit player-requested sync may make one further attempt while failed, but never retries the mutation. Distinguish explicit bridge client.sync from automatic requestResync so manual intent can attempt once without an automated retry chain.

A matching result claiming a newer uncommitted revision is recorded once for message/data deduplication but cannot release in-flight mutation state. Ordered publication means it implies a missed/unadopted publication and starts recovery immediately, rather than waiting indefinitely. A result at or below committed revision can satisfy the matched action after existing request/epoch checks, but never changes committed metadata or panels. Busy/foreign results do not unlock another request. Multipart pending outcomes never call releaseIfReady as an accepted presentation. If presentation publication succeeded and result was lost, preserve existing uncertain semantics after disconnect; do not fabricate completion.

### Server failure integration

B's preflight failures emit a safe presentation_unavailable/internal_error protocol envelope through ingress/dispatcher without claiming a new revision. Partial sends invalidate the baseline and may send a bounded error only if transport remains usable. A claimed future result is never emitted as successful synchronized completion after a failed presentation. Next explicit/automatic sync freshly snapshots every eager panel. If that snapshot cannot fit the logical policy, return presentation_unavailable and stop; no truncation/fake fallback data or auto-loop. Safe text play remains usable.

### Exact targets and acceptance

Own protocol/store.js recovery state and result checks; app stores/elosern/transport.js receive/result/release handling; stores/elosern/view.js failure projection; bridge.js shared gate; composables/use-resync.js request transition; app transport.js timer/lifecycle integration. Change ingress.py/dispatcher.py only safe failure/result paths, without reimplementing B publication. Tests are new Node protocol_recovery.test.js, existing app_client_completion.test.js, transport.test.js and app_client_resync.test.js. Timers are injected or fake-timed.

Test base mismatch preserving all old references/data, one sync across simultaneous failures, failed repair staying locked with no further sync after 60s and repeated traffic, valid full repair replacing all eager panels, newer result initiating repair, old results not rolling back, manual attempt, disconnect/epoch retirement canceling timers and request-cache unchanged. Update main protocol degradation requirement through delta and failure behavior documentation. No browser timing benchmark.

## Risks / Trade-offs

A one-attempt episode may require manual reload after repeated server faults; text fallback stays usable. Fixed finite response timers bound waiting rather than proving delivery latency. Recovery markers are transport-local and never persisted.
