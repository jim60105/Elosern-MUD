# Design

## Context

Approved interface: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2. Existing code, read on 2026-11-14:

- `web/webclient-app/stores/elosern/camp.js` is the model of a store group that owns a centred card, dispatches one action and adopts its result:
  - it wraps `ctx.centredCardOpen` (`const centred = ctx.centredCardOpen; ctx.centredCardOpen = () => centred() || <own open state>`); `stores/elosern/travel.js` stops a walk and `stores/elosern/presence.js` stops the rail while it is true;
  - it sends only when `rs.connected && rs.phase === "active" && !ctx.inFlight && !rs.mutationsLocked`;
  - `ctx.dispatchAction(actionId, payload, null)` returns a request id or a falsy value;
  - it matches the committed result `rs.lastActionResult` to its pending `{requestId, epoch, generation}` by `requestId` and `epoch`, and reads the result's `data` unnormalised;
  - `ctx.publishView()` publishes the group's part of `view`.
- `web/webclient-app/stores/elosern.js` composes the groups in order (`applyTravelLog(ctx)` and its neighbours).
- The `rite` panel shape (`landmark-rite-panel` design D1) and `ritePerformers` of `components/rite/rite-model.js`.
- The action result data is `{delivery, first_completion}` (`landmark-rite-action` design D2).
- Store tests use the harness of `web/webclient-app/tests/travel/support.js`, as `tests/travel/camp.test.js` does.

## Goals / Non-Goals

**Goals**

- One source of truth for the rite presentation state, fully tested as a state machine.

**Non-Goals**

- No component, composable or `AppClient.vue` edit (`landmark-rite-stage`).
- No performer state: the dispatched `member_id` is the argument given, `null` by default (`landmark-rite-performer-picking`).
- No newly-lit flag (`landmark-rite-discovery-notice`).
- No auto-play of a delivery found in the panel on a reconnect.

## Decisions

### D1. Store group (`web/webclient-app/stores/elosern/rite.js`)

`applyRite(ctx)`, composed in `stores/elosern.js` after `applyTravelLog(ctx)`. It publishes `view.rite`:

```js
{
  panel,        // the committed, available `rite` panel, or null
  phase,        // "closed" | "card" | "stage"
  revisit,      // the card was opened from the return entry
  pending,      // a rite request is in flight (boolean in the view)
  delivery,     // the delivery being played, or null
  playing,      // delivery !== null and its scene has not finished
}
```

Internal state also holds `seenKey` (the district key the group last saw available in this `generation|epoch` session), `hydrated` (false until the first committed snapshot of the session was processed) and the pending record `{requestId, epoch, generation}`.

Wrap `ctx.centredCardOpen` as `camp.js` does, adding `phase !== "closed"`.

`ctx.settleRite(rs)` runs in `stores/elosern/view.js` `publishView` directly after `ctx.settleCamp(rs)`, and `buildView` publishes `rite: ctx.riteView(rs)` beside `camp`, as the camp group is wired. A state with a null `activeEpoch` (before the first snapshot of a transport) has no session.

On every committed state (the hook `camp.js` uses for adoption):

1. `panel` = the committed `rite` panel when it is available, else `null`.
2. `panel === null`, or the committed mode is not `exploration`: reset to `{phase: "closed", revisit: false, pending: null, delivery: null, playing: false}`; when `panel === null` also clear `seenKey`. When the panel is available but the mode is not `exploration` and the session is not yet `hydrated`, set `seenKey` to its district key: a session that begins in dialogue or combat on a landmark is a reconnect too, and its return to exploration opens nothing. Steps 3 and 5 do not run.
3. Otherwise, when `panel.district.key !== seenKey`: set `seenKey`; if `hydrated` and `phase === "closed"`, set `phase = "card"`, `revisit = false`. The first snapshot of a session never opens the card: a reconnect on a landmark shows the return entry.
4. Set `hydrated = true`.
5. Adopt a pending result exactly as `camp.js` matches one: a success outcome whose `data.delivery` is an object -> `delivery = data.delivery`, `playing = true`, `pending = null`; any other outcome -> `pending = null` (the recognized-result handler already writes the server's message to the log).

Methods (each returns a boolean and calls `ctx.publishView()` when it changed state):

- `openRiteCard()`: `panel` and `phase === "closed"` -> `phase = "card"`, `revisit = true`.
- `approachRite()`: `phase === "card"` -> `phase = "stage"`.
- `leaveRite()`: `phase !== "closed"`, not `playing`, not `pending` -> `phase = "closed"`, `revisit = false`, `delivery = null`.
- `performRite(optionKey, memberId)`: requires `phase === "stage"`, not `pending`, not `playing`, `optionKey` one of `panel.options[].key`, and the send guards of `camp.js` (`rs.connected`, `rs.phase === "active"`, `!ctx.inFlight`, `!rs.mutationsLocked`). Then `ctx.dispatchAction("explore.landmark_rite", {option: optionKey, member_id: memberId ?? null}, null)`; a falsy request id returns false; else store the pending record.
- `finishRiteScene()`: `playing` -> `playing = false`, `delivery = null`.

A session change (`generation|epoch`) resets everything including `hydrated` and `seenKey`.

### D2. Tests (`tests/rite/store.test.js`)

With synthetic panels (the `ritePanel` fixture of `stories/fixtures/rite.js`):

- the first snapshot on a landmark leaves the phase closed; a later snapshot whose panel becomes available opens the card; a second snapshot for the same district does not reopen a dismissed card; another district opens it again; a new session starts closed again;
- `approachRite`, `leaveRite` and `openRiteCard` transitions, and each one's refusal in the wrong phase;
- `performRite` sends exactly one `explore.landmark_rite` with `{option, member_id: null}`; a second call while pending sends none; an unknown option key, a disconnected state and a locked state each send none;
- a success result adopts the delivery and sets `playing`; `leaveRite` is refused while playing; `finishRiteScene` clears it;
- a rejected result clears `pending` and plays nothing;
- a result for another request id is ignored;
- the panel becoming unavailable, and the mode leaving exploration, each reset to closed;
- `ctx.centredCardOpen()` is true while the phase is card or stage and false when closed (assert through the travel store's walk refusal the way `tests/travel/camp.test.js` asserts it for the camp card, if that test does; otherwise through the predicate).

## Risks / Trade-offs

- A card that opens only on a change of district key will not reopen when the player steps off and back onto the same landmark within one session unless the panel was unavailable in between; step 2 clears `seenKey` on unavailability, so it does reopen. The test "another district opens it again" covers both paths.
