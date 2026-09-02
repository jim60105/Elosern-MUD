## Why

When a dispatched `ui_action` ends non-success, the server-authored Traditional Chinese message travels inside the `ui_action_result` envelope, but the only client surface that renders `view.lastActionResult` is the creation overlay (`AppClient.vue:961` → `CreationOverlay`). In exploration and combat the failure is invisible: the player sees a command echo and nothing else, which reads as a frozen UI (design doc §1). Non-success outcomes are `rejected`, `stale`, and `error` (OOB protocol outcome vocabulary; `base_revision` admission returns `stale`, domain rejection returns `rejected`), and all three remain reachable after declarative frames land — multi-session races, recovery snapshots, and transport-edge paths — so the player must be able to see why an action did not apply.

## What Changes

- A recognized non-success `ui_action_result` (outcome `rejected` | `stale` | `error`, same request id and epoch — the identity `handleActionResult` already validates) appends the envelope's server-authored `message` to the narrative feed as one `err`-kind line, exactly once per recognized result, through the existing bounded `appendText` path so the full log and markup rules apply unchanged. A message-less non-success falls back to one stable local line.
- Success results surface nothing; the in-flight/uncertain machinery (revision-gated release — including the `stale` rule holding the lock until the recovery snapshot commits — and the uncertain-result notice) is untouched.
- Single-surface rule for creation mode: while the creation overlay presents the result, the same result appends no narrative line, keeping one visible statement per failure.
- No protocol, dispatcher, server, or player-command changes; `docs/game/commands.md` untouched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-action-dispatch`: adds the client-side surfacing requirement for non-success results (message visible once, `stale` path proven, creation-overlay exclusion, no automatic resubmit unchanged).

## Impact

- Code: `web/webclient-app/stores/elosern.js` (`handleActionResult` hook + one append rule); no component change expected (the narrative feed already renders `err` lines).
- Tests: Vitest store test for append/dedup/creation-exclusion/fallback; one browser method driving a real `stale` admission (tampered `base_revision` over the test transport) and one driving a real domain `rejected` result, asserting the visible line; `covers_requirement` on the browser methods.
- Dependencies: none. All three frame-refresh changes start after this one (shared `stores/elosern.js`); see design doc §9 for the serialized order.
