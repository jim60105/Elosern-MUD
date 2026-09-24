## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C12 and C13a are archived.

- **The panel (C12).**
  - `combat_beats` v1 carries `round` (`"<session_id>/<rounds_elapsed>"`) and at most 64 beats `{seq, action, kind, actor, target, amount, hp_after, text}`.
  - `kind` is one of `roll`, `damage`, `target_defeated`, or `other`. `actor` and `target` are catalog keys or null.
  - It is available only in the publication that completes `combat.cast`, `combat.flee`, or an in-session `inventory.use`. That includes a terminal round's full snapshot, whose mode is already `exploration`.
  - Every other publication carries the unavailable form, reconnect included. A round with heals, drains, or diverts, or one over a bound, is unavailable.
  - A non-terminal round rides a `ui_update` (it is in `AFFECTED_PANELS`), so the stored panel keeps its last available value until the next snapshot. Only a new `round` id means a new round.
- **Narrative (`world/rules/combat_result.py`).** `emit_settlement` sends one `actor.msg(render_plain_text(log))` per EventLog, then the terminal line (`行動完成，繼續戰鬥。` or the outcome). A terminal result's logs also include the defeat aftermath.
  - So a round's beats cover the response's first `max(action) + 1` `out` lines, and every later line is the round's tail.
  - Beat `text` is plain: `_ENTRY_TEMPLATES` carry no colour codes.
- **Order on the wire.** The text lines arrive, then the `ui_update` or snapshot, then `ui_action_result`. `ctx.inFlight` (`stores/elosern/transport.js`) lives from dispatch until `releaseIfReady` sees the declared revision.
- **Response segmentation (C6a).**
  - `dispatchAction` pushes a response mark, `ctx.narrativeSeq + 1`, right after `sendAction`. The response that starts at that mark has `startSeq` equal to it.
  - `MessageWindow` (C6b, C7, C10c, C11b) keeps `responseKey`, `pageIndex`, typing through `use-typewriter`, the flush on a pending mark or new response, and the `reading-change` signal. It receives `lines`, `marks`, `mode`, `dialogue`, `fontScale`, `textSpeed`, `autoAdvance`, `motionLevel`, and `held`.
  - Pages come from `lib/message_pages.js` `paginate(blocks, fits)`.
- **Lock.**
  - `dispatchAction` refuses while `ctx.inFlight` is set.
  - `syncRouterGates` (`stores/elosern/creation.js`) calls `router.setMutationInFlight(!!ctx.inFlight)`, and the keyboard router refuses activation while that flag is set.
  - The command line accepts a send only while connected, unlocked, and not in flight (C10c `accepting`).
- **Identities.**
  - `status.actor.identity` is `str(entity.pk)`, which is the same string as `portrait_catalog_key` and as a beat's `actor` / `target` for the player.
  - Combat participants carry `portrait_ref` with the same keys (C12 D6).
  - `view.combatParticipants` is empty once `context_actions` is the exploration kind.
- **Motion (C11a).** `<html data-motion>` carries the effective level, and `store.view.motionLevel` publishes it. Typing is instant whenever the level is not `full`. The contract "Presentation timing never gates committed state or input" names C13 as the owner of the script-side token reader and of combat's unlock rule.

## Goals / Non-Goals

**Goals:**
- One round plays as ordered text steps with truthful intermediate HP, built only from the committed panel.
- The command panel unlocks only when playback has ended and the revision is accepted.
- Skip, flush, reconnect, and fallback all end in exactly the committed state.
- Every wait comes from a token, and `off` never waits.

**Non-Goals:**
- Gestures, HP bars on stage, and the terminal-round stage hold (C13c).
- Replaying anything after a reconnect.
- Parsing narrative prose. The tail rule counts lines and never reads their text.

## Decisions

### D1. The script-side token reader
```
export function readMotionMs(name, root = globalThis.document?.documentElement) {
  if (!root || typeof getComputedStyle !== "function") return 0;
  const raw = getComputedStyle(root).getPropertyValue(name).trim();
  const m = /^(\d*\.?\d+)(ms|s)$/.exec(raw);
  return m ? Number(m[1]) * (m[2] === "s" ? 1000 : 1) : 0;
}
```
- Every read happens when the wait starts, so a level change applies from the next wait.
- Unparsable values give 0, because a missing token must never hold the lock (C11a contract, rule 1).

### D2. `--motion-beat` and the three levels
| Token | `full` | `reduced` | `off` |
|---|---|---|---|
| `--motion-beat` | 400ms | 400ms | 0ms |

Design §9.1 says `reduced` keeps "combat beats … their order and pauses but skip[s] the motion". The pause is not a movement, so it stays 400ms. C11a's `reduced` rule constrains transitions and animations only, and this token drives neither: only the script reads it. The `off` block's `0s !important` rule does not reach script waits, so the token itself is 0 at `off`. C11a's guard test learns the token so that each level block must define it.

### D3. The plan: pure, from committed data only
`planRound` takes:
- `panel`: the available `combat_beats`
- `roster`: `prev.combatParticipants`
- `statusHp`: `prev` status `resources.hp.current`
- `playerKey`: the committed `status.actor.identity`
- `level`, `startSeq`, and `terminal` (the committed mode is not `combat`)

It returns:
- `steps[i] = { seq, action, kind, actor, target, amount, hpAfter, text, firstOfAction, actorKnown, targetKnown }`, where "known" means the key is the player or a roster `portrait_ref`
- `coveredLines = max(action) + 1`, or 0 with no beats
- `hpStart[key]` for every known target of a `damage` step: the roster row's `hp_current`, or `statusHp` for the player
- `auto = level !== "off"`

Beats are used in `seq` order. The panel validator already guarantees contiguous `seq` and non-decreasing `action`, so "out of order" (design §12) cannot reach the client. A damage beat whose target is unknown, or whose target has no pre-round value, stays a text step and changes no HP (design §12: "plays the beats it can map").

`displayHpFor(state)`:
- While the round plays, each key in `hpStart` shows the `hpAfter` of the last applied damage step for it, or its `hpStart` before the first one.
- Every other key, including heals on undamaged participants, shows its committed value.
- Once `phase === "done"`, the result is `null`, so every surface snaps to committed `status` and participant values.

Only HP is displayed this way. MP and SP, the low-HP marker, the vignette, and the vitals visibility rule follow committed values, because a beat carries no other resource.

### D4. The state machine
The state is `{ plan, index, phase }` with `phase ∈ {"text", "pause", "done"}`. Events:

| Event | From | To |
|---|---|---|
| start (auto) | — | `index 0, text`; with 0 steps, `done` |
| start (`off`) | — | `done` (the pages remain for reading, D6) |
| `shown(i)` with `i === index` | `text` | `pause` (the step's HP applies) |
| `paused` | `pause` | `index + 1, text`, or `done` after the last step |
| `skip` / `flush` | any | `done` |
| `reset` | any | no round |

A stale `shown(i)` whose `i !== index` is ignored. The reducer never throws on out-of-sequence events, so a double click or a late timer cannot corrupt it.

### D5. The store slice and the lock
`applyBeats(ctx)` holds `ctx.beatState = null`, `ctx.lastBeatRound = { epoch, round }`, and one pending `setTimeout` handle.
- **Starting.** `ctx.syncBeatRound(prev, rs)` runs in `publishView` right after `ctx.releaseIfReady(rs)`. It starts a round when all of these hold:
  - `rs.panels.combat_beats?.available === true`
  - `(rs.activeEpoch, round)` differs from `lastBeatRound`
  - `ctx.inFlight` exists, with `actionId` in `BEAT_ACTIONS = {"combat.cast", "combat.flee", "inventory.use"}` and a non-null `responseMark`

  It records `lastBeatRound` either way, so a round seen outside those conditions never plays later.
  - `releaseIfReady` may already have cleared `inFlight` in this same pass, because the result can land in the same tick. So the slice reads the in-flight record captured at the top of `publishView` (`const flight = ctx.inFlight`, passed in).
- **Stepping.**
  - `ctx.beatShown(i)` applies `shown`. If the phase became `pause`, it schedules `paused` after `readMotionMs("--motion-beat")` and calls `publishView`.
  - `ctx.skipBeats()` and `ctx.flushBeats()` clear the timer, apply `skip` / `flush`, and publish.
  - `handleTransportLifecycle` calls `resetBeats()` on a generation change and on detach.
- **Locking.**
  - `ctx.beatLocked()` is `!!ctx.beatState && ctx.beatState.phase !== "done"`.
  - `dispatchAction` adds `|| ctx.beatLocked()` to its refusal guard.
  - `syncRouterGates` passes `!!ctx.inFlight || ctx.beatLocked()`.
  - The in-flight lock releases on the declared revision exactly as before, so the dock is usable only when both are clear. This is the existing rule of `webclient-combat-menu` plus playback.
- **Typed commands.** The command line is not the command panel. Its `accepting` rule is unchanged. `sendText` calls `ctx.flushBeats()` before it appends the `in` line, so a typed command ends the round, as C11a's flush rule requires, and never waits on it.
- **The response mark.** `dispatchAction` stores the mark it pushes in `ctx.inFlight.responseMark`. The exposed `view.dispatch.inFlight` keeps its two-field shape.

*Why the store and not a composable:* the lock must gate `dispatchAction` and the router, which live in the store, and three components read the playback (MessageWindow, VitalsTrack, ParticipantFrame). The window reports only "this beat is fully shown", because typing speed and the fit test are its own.

*Why not bind by timing* (the next response after the panel commits): the text arrives before the panel. The in-flight record is the one thing that links the request, its mark, and its panel.

### D6. Beat pages in the message window
`MessageWindow` gains the prop `beatPlayback` (the published slice or null). When `beatPlayback.startSeq === responseKey`:
- **Pages.**
  - `pages = [...beatPages, ...tailPages]`
  - `beatPages` = for each step, `paginate([beatBlocks(plan)[i]], fits)`, each page tagged `beat: i`
  - `tailPages = paginate(tailBlocks(response.blocks, coveredLines), fits)`
  - A beat is almost always one page (at most 256 code points against about 250 per page at 1080). A longer one splits under the normal rules.
- **Auto** (`auto && phase !== "done"`):
  - `pageIndex` is the first page of beat `index`, and the page types at the reader's speed. Instant below `full`, as C11a states.
  - When a beat page is fully shown, a further page of the same beat is shown after `readMotionMs("--motion-beat")`. The last page's completion emits `beat-shown(index)` once per beat.
  - A pointer activation, or Enter / Space on the page surface, emits `beat-skip` and does nothing else.
  - The `▼` / `■` marker is hidden and auto-advance is disarmed, because the queue paces the pages.
- **After playback** (`phase === "done"` with `auto`): `pageIndex` becomes the first tail page, which starts typing. With no tail, the window stays on the last beat page, fully shown with `■`. Normal reading resumes.
- **`off`** (`auto: false`): the pages are ordinary reader pages from page 1, with the ordinary controls, marker, and flush. This gives "sequential text pages only", and it never gates input (D4: the state is `done` at start).
- **Binding late.** If the response is on screen when the round binds, typically page 1 typing the first log's lines, the window restarts that response at beat 0. This happens within the same delivery batch, so at most a few characters are re-typed.
- **Flush.** When a new response starts, the window's own flush rules (C7 D8) apply to the beat pages like any pages. The store has already applied `flush`.
- **Reading signal.** `readingComplete` (C10c) stays false while auto playback runs.
- **Announcements.** The live region announces each beat page once when it starts (C6b D5), which gives screen-reader users the round in order.

*Why the tail count and not text matching:* matching beat text against narrative lines would compare prose. Counting delivered lines uses only the settlement's one-message-per-log shape (Context). An unrelated line arriving between the dispatch and the round's first log would shift the count by one. Nothing is lost then: the line stays in the log (Risks).

### D7. HP display wiring
- `VitalsTrack` gains `displayHp` (Number or null, default null). `gauge("hp")` uses it for `current` when it is non-null.
  - The numerals and the fill therefore follow the beat.
  - The ghost's width is bound to the same ratio with its delayed transition, so it trails every displayed drop and every snap. No new trailing logic is needed.
  - `StatusPanel` forwards it, and `AppClient` binds `store.view.displayHp?.[status.actor.identity] ?? null`.
- `ParticipantFrame` gains `displayHp` (Object or null). A row whose `portrait_ref` is a key shows that value in place of `hp_current`, and `AppClient` binds `store.view.displayHp`.
- The trailing-bar requirement now names "a previously displayed ratio" whose source is committed data: `status`, or a committed beat's `hp_after`.

### D8. Terminal rounds, fallback, reconnect
- **Terminal.** The completing snapshot's mode is `exploration`, but the round binds all the same: the in-flight action is combat's. It plays as text under the lock while the exploration surfaces are already committed and visible. The combat stage hold is C13c's.
- **Fallback.** When the completing publication carries the unavailable form, nothing binds. The response pages as before, `VitalsTrack` animates once to the committed values through its existing transitions, and the lock is the revision rule alone.
- **Reconnect.** A new epoch resets the slice. The reconnect snapshot carries the unavailable form (C12 D4), and the window's mount rule shows the last page, fully shown. So no round replays.

### D9. Tests
- **Vitest:**
  - `tests/motion_tokens_reader.test.js`: `ms`, `s`, fractional, empty, garbage, and no-document values.
  - `tests/beat_queue.test.js`:
    - a planned round with roll → damage → defeated beats, `firstOfAction` per group, and `coveredLines`
    - `hpStart` from the roster and status
    - `displayHpFor` stepping 30 → 18 → 0 and `null` at `done`
    - an unknown target is a text-only step
    - `off` starts `done`
    - skip and flush from every phase
    - stale `shown` is ignored
    - `tailBlocks` drops exactly N `out` blocks and keeps later `sys` / `err` blocks
    - `beatBlocks` never tokenizes markup (a beat text holding `<b>` renders literally)
  - `tests/store/beat_playback.test.js`, with fake timers and a stubbed `readMotionMs`:
    - a `combat.cast` dispatch, its text, its update with `combat_beats`, and its result bind one round
    - `dispatchAction` returns null and the router reports in-flight until the round is done and the revision accepted
    - the pause is 400ms from the stubbed token
    - `skipBeats` releases at once
    - `sendText` flushes before appending
    - a repeated `round` never replays
    - a panel arriving with no combat action in flight does not play
    - a terminal snapshot binds with `prev` roster values
    - a generation change resets
    - the unavailable form binds nothing
  - `tests/message_window_beats.test.js` (code-point `pageFit`, fake rAF):
    - beat pages and then tail pages
    - `beat-shown` once per beat after typing
    - a click emits `beat-skip` and does not advance
    - `done` moves to the first tail page
    - `off` pages are reader-driven
    - a late bind restarts at beat 0
    - one announcement per beat page
  - `tests/data/vitals_track.test.js`: `displayHp` drives the numerals and fill, and `null` restores the committed value.
  - `tests/combat/participant_frame.test.js`: a `displayHp` key replaces one row's numerals.
  - `tests/motion_tokens.test.js`: the three blocks define `--motion-beat`.
- **Browser** `web/tests/browser/test_browser_combat_beats.py`. It uses an isolated managed server like `test_browser_combat_panels.py`, reusing its `_engage`, `_press`, `_walk_to`, and `_basic_attack_target_identity`. One basic attack per journey.
  - `test_round_pages_beats_at_off` (default `off`):
    - after the attack, `view.beatPlayback.auto` is false and `phase` is `done`
    - the dock accepts the next action once the revision is accepted
    - pressing Enter on the page surface walks one page per beat, whose text equals each beat's `text` in order, and then the tail page holds `行動完成，繼續戰鬥。`
  - `test_round_plays_and_skips_reduced` (`motion_level="reduced"`):
    - while `phase` is not `done`, `view.dispatch.beatLocked` is true and a dock Enter sends no second `ui_action`
    - the store's `index` advances
    - a click on the message window makes `phase` `done` and the lock clear at once
    - `displayHp` is null afterwards, and the vitals numerals equal the committed `status`
  - `test_reconnect_replays_no_round`: after a round, a reload shows `beatPlayback` null and the last page fully shown.
  - Annotations: all of them `webclient-combat-menu::a-combat-round-plays-beat-by-beat`. The reduced journey also `webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs` and `webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input`.
- **Existing combat journeys.** They run at `off` (C11a's seed), so the dock unlocks on the revision as before. Any that read `message-page` text after a round now see beat pages: page through with Enter, or read `narrative_log_text` (C6a helper) instead. Find them with `grep -n "message-page" web/tests/browser/test_browser_combat_*.py`.
- **Evidence:** `test_node_suite_evidence.py` gains `test_beat_queue_vitest_evidence_passes`, which runs the four new Vitest files and is annotated with the new ID and the modified contextual-hud and input-narrative IDs.

### D10. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| combat-menu "Combat results update canonical panels and preserve narrative logs" | C12 `combat-beats-panel` |
| contextual-hud "Presentation timing never gates committed state or input" | C11a `webclient-motion-level` (ADDED there) |
| contextual-hud "The message window presents the current response one page at a time in the band's message region" | C11b `webclient-scene-transitions` |
| contextual-hud "Vitals pair an icon, a label, and numerals with a trailing damage bar" | main spec |
| contextual-hud "The combat participant frame presents the session's participants and their portraits" | C13a `webclient-combat-foes-on-stage` |
| input-narrative "The message window's reading controls advance pages and a new action flushes unread pages" | C7 `webclient-typewriter-reading-prefs` |

- Every scenario title is kept. Each MODIFIED block adds at most one scenario, so no annotation moves.
- The new ID is covered as D9 lists.
- `openspec validate` may report that blocks based on unarchived series changes cannot apply yet. That is expected.

**Archive order: C12 (`combat-beats-panel`) → C13a (`webclient-combat-foes-on-stage`) → C13b (this change) → C13c (`webclient-combat-beat-choreography`).** C13c modifies "A combat round plays beat by beat" and "Vitals pair an icon…" again, on this change's text. If a base block changes before archive, re-sync this change's blocks and keep only its own edits: beat pages, the playback lock, the displayed HP, and the click that ends a round.

## Risks / Trade-offs

- [An unrelated line (another player's shout) lands between the dispatch and the round's first log] → The tail count is off by one. One round line shows again as a tail page, or one tail line is left out of the window. Both remain in the full log, and nothing is presented as state.
- [A slow reader at `slow` text speed holds the dock for the round's length] → A click or Enter on the window ends the round at once. The unlock never waits on anything but the round and the revision.
- [A keyboard player with focus on the dock cannot skip without moving focus] → The round ends on its own within its typed length plus 400ms per beat, and C13c keeps each gesture under the pause. Tab reaches the page surface in one step (C6b).
- [The first beat page restarts a page that had begun typing] → Bounded by one delivery batch (D6).
- [Budget] → reader, token, and guard (0.5h), `beat_queue.js` and Vitest (2h), store slice, lock, and Vitest (2h), MessageWindow beat pages and Vitest (1.5h), HP props (0.5h), browser (1h), specs and gates (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
