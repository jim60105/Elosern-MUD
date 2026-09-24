## Why

After C12 (`combat-beats-panel`), the completing publication of a settled combat round carries a `combat_beats` panel: the round's server-authored beats with `hp_after`. The store commits the panel, but nothing reads it. So the round still pages as one block of prose, and every HP value jumps to the end state at once. C13a (`webclient-combat-foes-on-stage`) stands the foes on the stage. The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §10.2, §9.2, §12) asks the client to play each new round one beat at a time:
- Show one beat's text per page.
- Display HP from `hp_after` while the round plays, and snap to the committed values at the end.
- Keep the command panel locked until playback ends and the declared revision is accepted.
- Skip to the round's end on a click, and flush it on a new action.
- At `off`, show text pages only.
- Fall back to plain paging when no beats are available.

This change (C13b) delivers that queue, its lock, the HP display values, and the script-side motion-token reader that C11a (`webclient-motion-level`) promised. C13c (`webclient-combat-beat-choreography`) adds the gestures and the terminal-round stage hold on top.

**Implementation profile:** logic. The work is a pure state machine, a store slice, reader-state wiring, and prop plumbing. Every outcome is asserted by Vitest and by browser runs at `off` and `reduced`, so no visual judgement is needed.

## What Changes

- New pure module `web/webclient-app/lib/motion_tokens.js` (no Vue):
  - `readMotionMs(name, root = document.documentElement)` reads the computed value of a `--motion-*` custom property and parses `<n>ms` / `<n>s` into milliseconds.
  - An empty or unparsable value, or no `document`, gives `0`, so a missing token never holds anything.
  - This is the script-side reader C11a D6 promised.
- `web/webclient-app/styles/tokens.css`: new `--motion-beat` token, 400ms at `full`, 400ms at `reduced`, and 0ms at `off` (design D2). `tests/motion_tokens.test.js` (C11a's guard) adds `--motion-beat` to the tokens every level block must define.
- New pure module `web/webclient-app/lib/beat_queue.js` (no Vue, no DOM):
  - `planRound({ panel, roster, statusHp, playerKey, level, startSeq, terminal })`. It maps the beats to steps and flags the first beat of each `action` group. It records `coveredLines = max(action) + 1`. It builds each damaged participant's pre-round HP and keeps unknown participants as text-only steps.
  - A reducer, `beatReducer(state, event)`, handles `shown`, `paused`, `skip`, `flush`, and `reset`.
  - `displayHpFor(state)` returns the HP each damaged participant shows.
  - `beatBlocks(plan)` returns one plain-text `out` block per beat, never parsed as markup.
  - `tailBlocks(blocks, coveredLines)` returns a response's blocks after its first `coveredLines` `out` blocks.
- New store slice `web/webclient-app/stores/elosern/beats.js` (`applyBeats(ctx)`), composed in `stores/elosern.js`:
  - `ctx.syncBeatRound(prev, rs)` runs in `publishView` after `releaseIfReady`. It starts a round only when all of these hold:
    - `combat_beats` is available
    - its `round` is new for the epoch
    - `combat.cast`, `combat.flee`, or `inventory.use` is in flight
  - The round binds to the in-flight dispatch's response mark. `dispatchAction` now records that mark as `ctx.inFlight.responseMark`.
  - The pre-round roster comes from `prev.combatParticipants` and the pre-round HP from `prev.panels.status`, because a terminal snapshot's `context_actions` is already the exploration kind. The player's key is `status.actor.identity`.
  - `beatShown(index)` applies the beat and waits `readMotionMs("--motion-beat")` before the next step. `skipBeats()` and `flushBeats()` end the round at once.
  - A generation change or detach resets without playing.
- **The lock.**
  - `stores/elosern/transport.js` `dispatchAction` refuses while a round plays (`ctx.beatLocked()`).
  - `stores/elosern/creation.js` `syncRouterGates` passes `!!ctx.inFlight || ctx.beatLocked()` to `router.setMutationInFlight`.
  - `sendText` (a typed command) calls `flushBeats()` first.
- `stores/elosern/view.js` publishes:
  - `beatPlayback`: `null`, or `{ round, startSeq, auto, index, count, phase, texts, coveredLines, terminal }`
  - `displayHp`: `null`, or a map from catalog key to HP
  - `dispatch.beatLocked`
- `web/webclient-app/components/MessageWindow.vue`:
  - A new prop `beatPlayback`. While its `startSeq` is the current response's key, the response's pages are the beat pages (each beat paginated alone), then the tail's pages.
  - While `auto` is true, the store's `index` picks the beat page. A beat is typed at the reader's speed, and the window emits `beat-shown(index)` once the beat's last page is fully shown. A click, or Enter / Space on the page surface, emits `beat-skip` instead of completing or advancing.
  - When playback ends, the window shows the tail's first page. With no tail, it stays on the last beat page, fully shown.
  - At `off` (`auto: false`), the beat pages and the tail are ordinary reader pages.
  - `AppShell.vue` and `AppClient.vue` forward the prop and the two emits to `store.beatShown` / `store.skipBeats`.
- **HP display.**
  - `StatusPanel.vue` → `VitalsTrack.vue` gain a `displayHp` prop (Number or null). When set, it replaces `resources.hp.current` for the hp numerals and fill, so the trailing bar follows the displayed value.
  - `ParticipantFrame.vue` gains `displayHp` (map or null), which replaces `hp_current` for rows whose `portrait_ref` it names.
  - `AppClient.vue` binds both from `store.view.displayHp`.
  - The low-HP marker and vignette stay on committed values.
- Browser: new `web/tests/browser/test_browser_combat_beats.py` (real rounds on an isolated server, at `off` and `reduced`).
- No OOB schema, presenter, server, persistence, or component-manifest change. No component is added or deleted.

Out of scope:
- The actor step, shake, flash, floating number, defeat drop, foe HP bars, the 300ms trailing-bar retune, and holding the veil and foes on stage during a terminal round: `webclient-combat-beat-choreography` (C13c).
- The foe line-up: `webclient-combat-foes-on-stage` (C13a).
- The panel itself: `combat-beats-panel` (C12).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-combat-menu`:
  - MODIFIED "Combat results update canonical panels and preserve narrative logs" (C12 text). Unlock waits for the round's playback as well.
  - ADDED "A combat round plays beat by beat".
- `webclient-contextual-hud`:
  - MODIFIED "Presentation timing never gates committed state or input" (C11a text). Combat beats are stepped presentation, a new action flushes them, and they hold the command panel's lock.
  - MODIFIED "The message window presents the current response one page at a time in the band's message region" (C11b text). A round's beat pages.
  - MODIFIED "Vitals pair an icon, a label, and numerals with a trailing damage bar" (main spec). A displayed value from a beat.
  - MODIFIED "The combat participant frame presents the session's participants and their portraits" (C13a text). The frame's numerals show the displayed value during playback.
- `webclient-input-narrative`: MODIFIED "The message window's reading controls advance pages and a new action flushes unread pages" (C7 text). A click ends a playing round.

## Impact

- New:
  - `web/webclient-app/lib/motion_tokens.js`, `web/webclient-app/lib/beat_queue.js`, `web/webclient-app/stores/elosern/beats.js`
  - Vitest `web/webclient-app/tests/motion_tokens_reader.test.js`, `web/webclient-app/tests/beat_queue.test.js`, `web/webclient-app/tests/store/beat_playback.test.js`, `web/webclient-app/tests/message_window_beats.test.js`
  - `web/tests/browser/test_browser_combat_beats.py`
- Edited source:
  - `web/webclient-app/stores/elosern.js`, `stores/elosern/{transport,creation,view}.js`
  - `web/webclient-app/components/{MessageWindow,AppShell,StatusPanel,VitalsTrack,ParticipantFrame}.vue`, `web/webclient-app/AppClient.vue`
  - `web/webclient-app/styles/tokens.css`
- Stories: `stories/Core/MessageWindow.stories.js` (`CombatRound`), `stories/Data/VitalsTrack.stories.js` (`DisplayedHp`), `stories/Data/ParticipantFrame.stories.js` (`DisplayedHp`).
- Tests edited:
  - Vitest: `tests/motion_tokens.test.js`, `tests/data/vitals_track.test.js`, `tests/combat/participant_frame.test.js`, `tests/store/store_dispatch_focus.test.js` (the lock)
  - Python: `web/webclient/tests/test_node_suite_evidence.py`
  - Browser: combat journeys that read `message-page` text after a round (`test_browser_combat_panels.py`, `test_browser_combat_menu.py`, `test_browser_combat_skills.py`), and `.github/browser-shards.json`
- Spec traceability: one new ID (`webclient-combat-menu::a-combat-round-plays-beat-by-beat`). Every modified title is unchanged, so no annotation moves.
- Dependencies:
  - Archive order: C12 (`combat-beats-panel`) → C13a (`webclient-combat-foes-on-stage`) → C13b (this change) → C13c (`webclient-combat-beat-choreography`).
  - Hot-spot files shared with C6–C11 and C13a: `MessageWindow.vue`, `AppShell.vue`, `AppClient.vue`, `tokens.css`, `stores/elosern/view.js`.
