## Context

See proposal.md for motivation and scope. Current sources independently inspected for this proposal:

- `web/webclient-app/composables/use-letters.js:14-24,41-73`: the mount attempts `letters.list`; the boundary watch returns a fresh array and clears pending/page/opened/drafts whenever dependencies are invalidated by replacement of `store.view`. Results already carry request-ID/epoch/generation correlation.
- `stores/elosern/view.js:348-374` publishes a new `ctx.view.value` after lifecycle/result/lock handling. `stores/elosern/transport.js:344-429` dispatches under connected/active/mutation/in-flight/beat gates and publishes in `finally`. A mount-only attempt can silently miss its initial load when an earlier opening's request still owns the global lock.
- `components/LettersPanel.vue:6-40` exposes reload, branch-only collection/composer, explicit reads, and cursor pagination. `AppClient.vue:525-544` uses `v-if` for drawer and letter-panel mounting, so close really unmounts local state.
- `stores/elosern/creation.js:273-313` closes non-NPC-persona drawers on transport loss, epoch change, and detach. `web/static/webclient/js/elosern/protocol/store.js:119-141` resets the active epoch to null and publishes on generation change. Thus a normally mounted letters panel with an active epoch is torn down by the existing epoch-change path on `beginTransport`, without a parallel letters lifecycle watcher. Implementation must establish this through real-store tests, not assume generation safety from a mock.
- `world/narrative/player_correspondence.py:33-49,74-155` authorizes authored unique branch anchors before send/collect; metadata includes only owned collected/read states, and explicit reading enforces owner/collection before first-read writes. `web/webclient/actions/correspondence_actions.py:60-85` already includes authoritative pages in collect/send responses.
- `web/webclient-app/tests/letters.test.js:10-19,52-62` mutates a stable reactive view; dispatch is mocked without publications. It does not reproduce production replacement semantics and its identity test bypasses actual drawer teardown.

The supplied prior browser observation recorded an unchanged epoch, generation 1, connected state true, and a successful `letters.list` result (`letters.ok`, empty collected page, revision 4 to 5), yet the UI displayed its session-change warning. Supplied module-smoke evidence also reproduced this. Those are existing incident evidence, not checks rerun in this proposal. The approved engine design §2 D13/D14 and §3.1 keeps presentation separate from deterministic narrative ownership; the narrative-memory design §3.4 and §5.3 keeps collection separate from player knowledge at first explicit reading. No amendment is necessary.

## Goals / Non-Goals

**Goals:** A component-lifetime initial load with deterministic lock waiting; ordinary publications must preserve local state. Private state ends at existing drawer teardown, and response correlation must reject prior-opening/session results. Keep the authoritative correspondence domain unchanged except for a demonstrated acceptance defect.

**Non-Goals:** No persistent drafts, caching across openings, polling, backend list-on-open collection, retry scheduler, protocol changes, new lifecycle framework, migrations, compatibility aliases, delivery/clock changes, or replacement of the global dispatch lock. No application edits occur during proposal creation.

## Decisions

### 1. Make one component lifetime one opening

Remove the Reload/Refresh button and rename the composable's `refresh` API to a list/page operation at its sole component caller, with no obsolete alias. Use that operation for explicit pagination and the one initial load. Do not recreate the panel on ordinary revisions or add a revision key to `AppClient`; its current conditional mount is the lifecycle boundary. All recipient/body/opened/page/send identity state remains component-local and disappears on unmount as today.

Removing just the button leaves the confirmed successful-result discard intact. Deep equality around the existing boundary watch is also inferior to removing its redundant ownership: drawer teardown already owns private-session lifetime.

### 2. Represent an unsent initial load, not an automatic retry

Maintain a small component-scoped initial-load intent, eligible only while mounted in the opening's captured epoch/generation. Watch dispatch readiness using primitive or computed sources, never a newly allocated array as the watch getter. Readiness must match the existing `dispatchAction` gates: connected, active phase, no mutation lock, no in-flight request/local pending action, and no beat lock. This is frontend scheduling, not server authorization and not permission to bypass transport gates.

Before invoking dispatch, consume the initial intent so synchronous `publishView` re-entry cannot schedule a second initial request. Capture correlation at submission. A readiness refusal returning no request ID has not submitted a request: retain the unsent intent only while the same opening remains live, and reevaluate on readiness transitions without timers or a tight loop. Once a request ID exists, that initial attempt is consumed permanently for this opening, even on rejection/error or synchronous transport failure. Do not re-arm on result/lock release. Closing disposes the intent and readiness observation before the lock can cause a later submission.

Handle server failures on the existing result channel and known synchronous send failures through the store's existing correlated local dispatch state. `dispatchAction` catches a thrown sender, sets uncertainty, clears its in-flight record, publishes, and still returns the request ID without emitting a result. Inspect the post-dispatch state immediately after that ID returns, since the synchronous publication precedes assignment of the composable's pending record: a matching `dispatch.submittedRequestId`, cleared in-flight state, and `dispatch.uncertain` can identify this local failure when no matching completed result is present. Do not treat an unrelated or pre-existing uncertainty flag alone as this request's failure; retain request/opening/epoch/generation correlation and prefer a matching completed result if one arrived synchronously. Clear only this opening's local pending state, retain the consumed initial intent, and show failure plus Traditional Chinese close-and-reopen guidance. Do not clear global uncertainty, synthesize a server response, or change the transport contract.

Pagination failures likewise do not auto-retry. Do not add timeout/recovery infrastructure in this change. Waiting UI is distinct from an actual request failure. Explicit collect/read/send remain user actions, not queued automatic mutations. A focused sender-throws regression must observe no action result, terminal local failure guidance, and no retry or guidance overwrite on later publications.

### 3. Use the existing teardown owner and retain correlation

Delete the array-returning boundary-clearing watch. Exercise `syncHudDrawer` plus `AppClient`'s real conditional mounting for disconnect, `no_puppet` detach, epoch replacement, and `beginTransport` generation reset. If an actual supported generation transition can preserve the epoch and leave letters mounted, add only the necessary letters generation-close condition to the same `syncHudDrawer` owner; do not restore a composable boundary clearer or change NPC-persona draft behavior. Document the verified lifecycle path or the reason for that narrow guard in the implementation evidence.

Keep request-ID/epoch/generation checks and verify current opening identity before applying responses or submitting delayed initial loads. The retired component's watchers stop on unmount; the new component tracks only its own request. Same-session request IDs remain monotonically generated, while generation protects reset counters. Vue batching must not allow a pending old result or unsent intent to populate a new identity before teardown takes effect.

### 4. Reuse authoritative pages without changing acquisition or reading

Keep collect/send success applying `result.data` directly (their adapters already call the domain list internally). No extra browser `letters.list` follows either action. Their response replaces the displayed page with its authoritative first page, preserving its next cursor; pagination remains explicit. A collection response must not call `letters.read`, mutate read ticks, or establish knowledge. A send success clears the sent body as today. Ordinary view publications do not clear opened prose or a different unsent draft.

Branch controls use the server's `page.branch` for presentation only. The server rechecks current authored/uniquely anchored location on every collect/send, including after moving away from a previously loaded branch page. Metadata/body authorization remains owner plus collected/read state. Retain Unicode/body bounds and same-draft explicit-send identity semantics; no remote acquisition path is introduced.

### 5. Require production-shaped regression evidence

Extend the existing letters component tests with view replacement on dispatch and result publications, and use the real Pinia/store reducer plus a mounted conditional letters host for teardown and request-lock cases. Do not let a stable-object-only mock serve as evidence for the false-invalidation fix. Reuse existing real-store fixture patterns after inspecting their setup.

Focused acceptance must cover one initial load per opening, waiting/canceling under previous in-flight and mutation/presentation locks, pagination, success/failure/non-retry, current-opening correlation, preserved list/body/draft on ordinary publications, true boundary unmount and draft loss, and collect/send response reuse. Extend existing synthetic domain/adapter tests for forged remote send/collect, duplicate/unauthored anchors, portable unread read, and foreign/uncollected refusals without read/knowledge writes. Use existing modules to avoid introducing new shard ownership.

Implementation gates: focused Vitest letters/store lifecycle tests; the focused `world.narrative.tests.test_player_correspondence` Evennia module using the repository-required temporary env-file guard; player command documentation contracts; strict OpenSpec validation; and `uv run --locked python -m tools.contract_gate`. Resolve future main-spec traceability IDs through the project tool when syncing rather than inventing IDs. One real logged-in browser smoke must exercise the production Pinia replacement path, opening/reopening request counts, preserved draft/body, explicit collection without an extra list or read, and an outside-branch portable-read/denied-acquisition case. Inspect action envelopes/results and actual rendered UI; a composable-only smoke cannot substitute. Keep it to one focused scenario/file, not the full CI-managed browser/evidence suite, and never create synthetic player-visible letters in a real player's retained world merely to obtain a fixture.

## Risks / Trade-offs

- Readiness scheduling can duplicate dispatch through synchronous publication. Consume the initial intent before dispatch and test request counts across lock release and ordinary replacement publications.
- Closing does not cancel an already submitted server action or release its global lock. A new opening waits for the existing lock and then loads once; closing only cancels its own unsent intent. Existing transport recovery owns a lock that never releases.
- A loaded `branch` flag can outlive movement during the same opening. Server authorization remains authoritative; no location-triggered list request, auto-collection, or duplicate capability cache is added. Explicit rejected operations must not reveal prose or mutate correspondence.
- Removing the redundant watcher is safe only with proven teardown. Tests must cover the actual reducer generation transition and Vue unmount timing, including waiting/in-flight openings, before claiming privacy isolation.
- Close/reopen intentionally loses drafts, and failed loads intentionally require explicit recovery. Document that behavior in `docs/game/commands.md` and `docs/game/command-reference.md`; text syntax and commands remain unchanged.

## Dependencies and Conflict Surface

No active-change dependency. Existing correspondence-player-surface implementation and its delivery/memory owners are landed prerequisites, not new batch work. Coordinate any concurrent edits to `use-letters.js`, `LettersPanel.vue`, `letters.test.js`, drawer teardown/store lifecycle tests, the player correspondence test module, and either player command reference. `creation.js` is a conditional conflict only if a demonstrated generation teardown gap needs the narrow guard; domain/action production files are otherwise intentionally unchanged. Keep this proposal and all commits confined to its CLI-resolved change directory on the primary branch.
