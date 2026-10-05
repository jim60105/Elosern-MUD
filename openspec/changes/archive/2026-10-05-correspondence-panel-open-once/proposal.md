## Why

The personal correspondence folio discards successful responses and private local state when an ordinary Pinia publication replaces `store.view`, despite an unchanged session identity. Removing the redundant reload control must fix that confirmed lifecycle defect and make closing/reopening the explicit refresh boundary without weakening branch authorization or first-read semantics.

## What Changes

- Remove the personal letters Reload/Refresh button; load the first collected-letter page once per genuine opening and load it again after closing/reopening. Retain explicit cursor pagination.
- Wait for existing dispatch readiness when a newly opened panel encounters a preceding request or mutation lock; cancel this unsent initial load on close. Never automatically retry a request that was submitted and failed.
- Remove `useLetters`' redundant array-returning boundary-clearing watcher. Use existing drawer teardown/unmount for disconnect, detach, and identity/epoch replacement; verify generation reset through the actual reducer and add only a narrow guard in that existing teardown owner if needed.
- Preserve request-ID/epoch/generation correlation and reject results belonging to a prior opening. Ordinary view publications preserve the current list, opened prose, and unsent draft; closing still discards the draft.
- Apply successful collect/send response pages directly without an extra browser list request. Listing/opening the panel never collects letters or marks them read.
- Preserve authoritative, uniquely anchored authored Silver Feather branch checks for sending/collection, portable reading of owned collected letters (including unread letters), and server-side denial of foreign/uncollected bodies.
- Add focused real-store/component and permission regressions plus one real-browser implementation smoke gate; document opening/reopening and failure recovery in both player command references without changing text syntax.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `correspondence-player-surface`: Specify open-once loading, lock-aware deferred dispatch, lifecycle isolation, result-page reuse, and explicit refresh recovery; clarify the existing authoritative acquisition/read boundary.

## Impact

One engineer-day change, concentrated in `web/webclient-app/composables/use-letters.js`, `components/LettersPanel.vue`, existing drawer lifecycle tests, `tests/letters.test.js`, `world/narrative/tests/test_player_correspondence.py`, and the two player command references. `AppClient.vue`, Pinia view/transport publication, the protocol reducer, and correspondence adapters/domain APIs are integration surfaces to exercise, not new protocol or backend designs.

Architecture remains aligned with the approved engine design §2 D13/D14 and §3.1, and the narrative-memory design §3.4/§5.3. No architectural amendment, database migration, compatibility layer, polling, automatic acquisition, automatic retry, draft persistence, delivery change, or full CI browser suite is included. There are no active-change prerequisites; correspondence-player-surface and its domain/adapters already exist on the primary branch.
