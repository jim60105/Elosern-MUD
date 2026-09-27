## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C12, C13a, and C13b are archived.

- **The queue (C13b).**
  - `lib/beat_queue.js` `planRound` builds steps `{seq, action, kind, actor, target, amount, hpAfter, text, firstOfAction, actorKnown, targetKnown}`, `hpStart`, `coveredLines`, `auto`, and `terminal`. It takes the pre-round roster from `prev.combatParticipants`.
  - The reducer's phases are `text` → `pause` → `done`. The store slice `stores/elosern/beats.js` schedules `paused` after `readMotionMs("--motion-beat")`.
  - `view.beatPlayback` and `view.displayHp` are published. `displayHp` is `null` at `done`.
  - The round binds even when the committed mode is already `exploration` (a terminal round).
- **The line-up (C13a).**
  - `FoeLineup.vue` renders up to three `StageActor`s from committed active foes in a `TransitionGroup name="foe"` (leave: fade over `--motion-actor`, inert).
  - Each slot carries `data-portrait-ref` and a decorative HP gauge (`.foe-lineup__gauge`, `data-testid="foe-gauge"`, fill and trailing bar on `--motion-slow`, `--motion-trail`, `--motion-trail-delay`) from the committed `hp_current / hp_maximum` (`foeHpPercent` in `components/foe-lineup.js`).
  - The row is depth-staged (front foe largest, each foe behind smaller and higher), and its geometry lives in `components/foe-lineup.js`. `AppClient` keeps the caption clear through `--foe-lineup-span` / `--foe-front-scale`, released in the `foes-enter` `after-leave`.
  - `AppClient` mounts it in `#actor-right` inside `<Transition name="foes-enter">` while `mode === 'combat'`.
- **`StageActor.vue`** (C10b, C11b): the root `[data-testid="stage-actor"][data-side][data-speaking]` holds the `actor-xfade` transition around `ReferenceArtwork`, and the dim filter eases over `--motion-fast`.
- **`HudFrame.vue`** (C11c):
  - `.stage-combat-veil` is always rendered and `aria-hidden`. It is `opacity: 0`, and `opacity: 1` in combat mode, with the pulse on a `::before` layer active only in combat. Under `[data-mode-change]` it transitions its opacity over `--motion-actor`.
  - `data-mode-change` drives the flash and the flip once per live change.
- **`VitalsTrack.vue`** (C11a, C13b): the fill runs `width var(--motion-slow)`, and the ghost runs `width var(--motion-trail) ease var(--motion-trail-delay)` (600ms after 250ms). `displayHp` drives the hp row during playback.
- **Motion levels** (C11a): `reduced` allows no translation, no shake, no flash, and only fades of at most 150ms. At `off` everything is 0.
- **Committed state at a terminal round:**
  - The snapshot commits mode `exploration`.
  - `data-elosern-mode` flips, and so do the minimap, the objective line, the participant frame (gone), and the dock's content (flip-out plays at commit).
  - The foe line-up and the veil would leave at commit.

## Goals / Non-Goals

**Goals:**
- Design §10.2's gestures, per beat and per level, from tokens only. The queue waits for each gesture through the script-side reader.
- A foe stays on stage until its own defeat beat is shown.
- A terminal round's beats play in front of the combat stage. That stage leaves when the round ends or is skipped, and committed state is never held back.

**Non-Goals:**
- Allies on stage. A beat that names an ally who is not on stage changes only that ally's frame numerals (C13b).
- Any change to the queue's order, lock, pages, skip, or flush (C13b).
- Deferring the flash, the flip, or any mode-gated surface. Only decorative layers are held.

## Decisions

### D1. Tokens and keyframes
| Token | `full` | `reduced` | `off` | Consumer |
|---|---|---|---|---|
| `--motion-beat-step` | 240ms | 0ms | 0ms | actor lunge (there and back) |
| `--motion-beat-hit` | 180ms | 0ms | 0ms | target shake and flash |
| `--motion-beat-float` | 600ms | 0ms | 0ms | floating damage number |
| `--motion-beat-defeat` | 350ms | 150ms | 0ms | defeat fade (and drop at `full`) |
| `--motion-trail-delay` | 300ms (was 250ms) | 0ms | 0ms | trailing bar |
| `--motion-beat-lunge` / `--motion-beat-shake` / `--motion-beat-rise` | 24px / 6px / 48px | (multiplied by `--motion-travel` = 0) | same |

Keyframes, in `tokens.css` next to C11c's:
- `elosern-beat-lunge-right` / `-left`: `50% { transform: translateX(calc(±1 * var(--motion-beat-lunge) * var(--motion-travel))) }`.
- `elosern-beat-hit`: horizontal ±`--motion-beat-shake` at 20/40/60/80%, plus `filter: brightness(calc(1 + 0.8 * var(--motion-flash-peak)))` at 20%. C11a's `--motion-flash-peak` is 0 under `reduced`, so no flash survives there, even though the duration is also 0.
- `elosern-beat-float`: from `opacity: 1; transform: translateY(0)` to `opacity: 0; transform: translateY(calc(-1 * var(--motion-beat-rise) * var(--motion-travel)))`.
- `elosern-beat-defeat`: to `opacity: 0; transform: translateY(calc(var(--motion-shift-lg) * var(--motion-travel)))`, with `fill-mode: forwards`.

The retune of the trailing delay changes the existing vitals too. That is design §10.2's number, and it is imperceptibly different outside combat.

### D2. The `act` phase
The reducer's step becomes `text` → `act` → `pause`:
- `shown(i)` enters `act`. The step's HP applies now, so the fill and the gauge move with the shake.
- `acted` enters `pause`.

The store waits `actMs(state)` between `act` and `acted`: the maximum of the gestures the step plays (D3's `gestures`), read through `readMotionMs`. When it is 0 (a step with no gesture, or the `reduced` level's 0ms step and hit), `acted` applies in the same pass, so the pause starts at once as it did before this change.
- `--motion-beat-step` when `firstOfAction && actorKnown`
- `--motion-beat-hit` for a known `damage` target
- `--motion-beat-defeat` for a known `target_defeated` foe

The float and the trailing bar run on into the pause. They are decorative and nothing waits for them. At `reduced`, `actMs` is 0 or 150ms and the pause stays 400ms. At `off` there is no auto playback (C13b).

`skip` and `flush` from `act` go to `done` as from any phase. The queue's contract is unchanged, and C13b's Vitest keeps passing with an extra phase row.

### D3. The stage slice
`stageFor(state)` returns `null` unless `state.phase ∈ {text, act, pause}` and `plan.auto`. Otherwise it returns:
- `step`: the current index
- `key`: `"<round>:<step>"`, which each stage actor uses as its `gestureKey`
- `gestures`: a map from key to `{ gesture, amount }`, filled during the step's `act` and `pause` and empty during `text`. The rising number (600ms) runs on into the pause, and clearing the map at `pause` would re-key the wrapper and remove the number mid-rise. Only keys that stand on the stage get one (the player, and the first three foes of `foes`):
  - the actor gets `lunge` when `firstOfAction`
  - a damage target gets `hit` with `amount`
  - a defeat target that is a foe gets `defeat`
  - the player never gets `defeat`
- `foes`: the plan's pre-round active foe rows, `roster.filter(team === "foes" && state === "active")`, minus the keys in `defeated`
- `defeated`: every pre-round foe key whose `target_defeated` step index is < the current step, in every phase. The defeated foe therefore still stands during its own defeat step's `act` and `pause`, where it plays `defeat`, and leaves the list at the next step (or at `done`). A child that leaves a `TransitionGroup` is unmounted and never patched again, so if the foe left in the same patch that assigned its gesture, `data-beat="defeat"` would never render. Leaving afterwards, the slot keeps its unpatched faded DOM (the keyframe ends at `opacity: 0` with `forwards`), so C13a's leave fade is invisible.

The view publishes it as `view.beatStage`, next to C13b's `beatPlayback`. A key the plan does not know gets no gesture (design §12). A step that names a foe not on stage (the fourth or later) animates nothing on stage, and only its frame numerals change (C13b).

`view.beatHold` is `plan.terminal && plan.auto && phase !== "done"`.

### D4. Gestures on `StageActor`
- New props:
  - `gesture` (String or null)
  - `gestureKey` (String, `"<round>:<step>"`)
  - `floatAmount` (Number or null)
- The template wraps the existing `actor-xfade` transition in `<div class="stage-actor__beat" :key="beatKey" :data-beat="gesture || null">`. `beatKey` is the step's `gestureKey` while a gesture plays. At rest it keeps the last gesture's key (`rest` before the first one), so the wrapper is re-keyed once per gesture and never just for a rest phase. Re-keying restarts a CSS animation cleanly for a new step, and dropping `data-beat` renders the idle state.
- CSS, written against `[data-testid="stage-actor"]` as C11b D5 does:
  - `[data-beat="lunge"][data-side="left"]`: `animation: elosern-beat-lunge-right var(--motion-beat-step) var(--ease-standard) 1`. The right side uses `-left`, so both step toward the centre.
  - `[data-beat="hit"]`: `elosern-beat-hit var(--motion-beat-hit) linear 1`.
  - `[data-beat="defeat"]`: `elosern-beat-defeat var(--motion-beat-defeat) var(--ease-exit) 1 forwards`.
- The float is `<span v-if="gesture === 'hit' && floatAmount !== null" class="stage-actor__float" aria-hidden="true" :key="`float:${gestureKey}`">−{{ floatAmount }}</span>`:
  - absolutely positioned at 30% from the top, in the seal colour, bold, at 1.5 times the message text size, with an ink outline painted under the fill, so it reads over pale and dark art
  - anchored at the figure's face and leaning toward the stage centre by side (`--float-x`), so it stays clear of the vitals column on the left and the participant frame on the right
  - `animation: elosern-beat-float var(--motion-beat-float) var(--ease-exit) 1 forwards`
  - At `off` and `reduced` the duration is 0, so it ends invisible at once. The amount is in the beat's text and the HP numerals, so nothing is lost.
- Nothing becomes focusable, and every layer stays in the anchor's `pointer-events: none`.

*Why a keyed wrapper and not a class toggle:* two consecutive `hit`s on the same foe (a multi-hit skill) need the animation to restart. Re-keying one wrapper per step is the only pure-CSS restart, with no forced reflow in script. The re-key remounts the portrait inside it, too. A remounted `<img>` whose URL is already loaded is `complete` when it is inserted (checked in Chromium with the looping `BeatHit` story), so it paints in its first frame and nothing pops.

### D5. The line-up during a round
`FoeLineup` gains `stage` (the `view.beatStage` slice or null) and `displayHp`.
- `shown = (stage ? stage.foes : foes).slice(0, 3)`. So during a round the row stands the pre-round foes. A foe whose defeat beat has played leaves the `TransitionGroup`: its own `defeat` animation runs first, then C13a's leave fade. That is design §10.2's "fades and drops out".
- At `done`, `stage` is `null` and the committed foes take over. On a skip, every foe defeated in the round leaves at once through the ordinary leave.
- Each slot's gauge (shipped by C13a) reads the displayed value:
  - width = `(displayHp?.[ref] ?? row.hp_current) / row.hp_maximum`; the fill and the trailing bar keep C13a's look and transitions
  - The numerals remain the participant frame's only. The gauge is the stage's reading of "that target's HP bar animates to `hp_after`" (design §10.2), and it is visible during the terminal hold, when the frame is gone.
- Each slot's actor receives `gesture`, `gestureKey`, and `floatAmount` from `stage.gestures[portrait_ref]`. The slot also carries the gesture as `data-beat`, so a defeated foe's gauge fades out with its figure over `--motion-beat-defeat` instead of floating on alone until the slot leaves. `AppClient` passes the player's from `stage.gestures[status.actor.identity]`.

### D6. The terminal-round hold
- `HudFrame` gains the `beatHold` prop and renders `:data-beat-hold="beatHold ? 'combat' : null"` on `.elosern-stage`.
- CSS: `.elosern-stage[data-beat-hold="combat"] .stage-combat-veil { opacity: 1 }`, and the `::before` pulse runs during the hold too. It is the same animation, so the running pulse continues unbroken across the mode flip instead of jumping to full opacity. When the attribute goes away, the veil fades out on the combat exit's own transition (`[data-mode-change] .stage-combat-veil`, `--motion-actor`), because `data-mode-change` is still `combat-exploration`.
- `AppClient` renders the line-up while `store.view.mode === 'combat' || store.view.beatHold`, from `beatStage.foes`, and binds `:inert="store.view.beatHold"` on it. The foes are art whose committed state no longer exists, so they must be out of reach even though they are on screen.
- When the hold ends, the `foes-enter` leave (C13a) fades the line-up out beside the veil. That is §9.3's "foes fade out, veil fades out".

What the hold does not do:
- `data-elosern-mode`, `data-mode-change`, the flip, the minimap, the objective line, the dock's content, focus, and the accessibility tree all change at commit, as C11a and C11c require.
- The dock stays locked by C13b's playback lock, so the committed exploration overview it shows cannot act before the beats end.

*Alternative:* delay `data-mode-change` or the mode attribute until the round ends. Rejected. It gates committed state, which C11a's contract forbids and its scenario "A mode change commits before its transition ends" tests.

*Alternative:* keep the whole combat HUD, including the participant frame, visible. Rejected for the same reason. The frame is a committed surface, and the gauges (D5) carry the foes' HP on stage.

### D7. Tests
- **Vitest** `tests/beat_choreography.test.js`:
  - `stageFor`: the lunge on the first beat of each action only, hit with amount, defeat only for foes (never the player), `foes` minus defeated per phase, and `null` at `done` and at `off`
  - the `act` phase duration picks the maximum of the stubbed gesture tokens
  - `beatHold` only for a terminal auto round
- `tests/core/stage_actor.test.js`: the `data-beat` wrapper re-keys per `gestureKey`, the float renders `−12` `aria-hidden`, and `null` gestures render the rest state.
- `tests/core/foe_lineup.test.js`: a stage slice keeps a committed-defeated foe until its step, the gauge width follows `displayHp`, and there are no numerals.
- `tests/hud_frame.test.js`: `data-beat-hold` renders only with the prop.
- `tests/beat_queue.test.js` and `tests/store/beat_playback.test.js` gain the `act` row, with the act timer stubbed. `tests/motion_tokens.test.js` requires the four new tokens.
- **Browser** `web/tests/browser/test_browser_combat_choreography.py`, on the shared server. The synthetic kit's monsters have 200 HP and no browser journey reaches a one-attack defeat on a real server, so every journey plays a synthetic round through the live client's own store:
  - it commits a combat snapshot with its own participants and art catalog
  - it dispatches `combat.cast` with the outbound `ui_action` swallowed, so the server never sees it
  - it appends the round's lines, then commits the completing publication (a `ui_update` in combat, or a full `ui_snapshot` in `exploration` for a terminal round) with the `combat_beats` panel, and then the action's result

  The store binds and plays that round exactly as it does a live one, and C13b's real-server journeys keep the end-to-end binding covered. Gestures are read from the computed `animation-name` and `animation-duration` on the gesture wrapper, polled per animation frame. `getAnimations()` is not used, because a finished animation without a fill drops out of it while `data-beat` stays through the pause.
  - `test_beat_gestures_full_motion` (`motion_level=None`). It plays a roll and a damage beat. On the matching actor it reads:
    - `data-beat="lunge"` with `elosern-beat-lunge-right` at 240ms on the player
    - `data-beat="hit"` with `elosern-beat-hit` at 180ms on the foe, and a `.stage-actor__float` with `elosern-beat-float` at 600ms
    - the vitals ghost's computed `transition-delay` `0.3s`

    It never asserts elapsed time.
  - `test_beat_gestures_reduced` (`motion_level="reduced"`): the lunge and hit durations are 0s, the float is not visible, and the defeat animation is ≤ 0.15s with an identity transform.
  - `test_terminal_round_holds_the_stage` (`motion_level="reduced"`): the synthetic round defeats the last foe and commits `exploration`. Right after the snapshot:
    - `data-elosern-mode` is `exploration`, the minimap island is visible, and `data-beat-hold` is `combat`
    - the veil's computed opacity is 1, and the line-up is present and `inert`
    - a click on the message window then removes `data-beat-hold`, and the line-up is eventually gone
  - `test_terminal_round_at_off_holds_nothing` (default `off`): after the defeating snapshot, `data-beat-hold` is absent and there is no line-up.
  - Annotations:
    - all journeys: `webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level`
    - the terminal journeys also: `webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode` and `webclient-combat-menu::a-combat-round-plays-beat-by-beat`
- **Evidence:** `test_node_suite_evidence.py` gains `test_beat_choreography_vitest_evidence_passes`, annotated with the new ID.

### D8. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" | C13a `webclient-combat-foes-on-stage` |
| contextual-hud "Surface visibility is gated by the committed game mode" | C13a |
| contextual-hud "Foes stand opposite the player during combat" | C13a (ADDED there) |
| contextual-hud "Vitals pair an icon, a label, and numerals with a trailing damage bar" | C13b `webclient-combat-beat-queue` |
| combat-menu "A combat round plays beat by beat" | C13b (ADDED there) |

- Every scenario title is kept. Each block adds at most one scenario, so no annotation moves.
- The new ID is covered as D7 lists.
- `openspec validate` may report that blocks based on unarchived series changes cannot apply yet. That is expected.

**Archive order: C12 (`combat-beats-panel`) → C13a (`webclient-combat-foes-on-stage`) → C13b (`webclient-combat-beat-queue`) → C13c (this change).** This is the last change of the series. If a base block changes before archive, re-sync this change's blocks and keep only its own edits: the gestures, the pre-round line-up and gauges, the terminal hold, and the 300ms trail.

## Risks / Trade-offs

- [The held line-up and veil show combat over a committed exploration HUD for a few seconds] → They are decorative, inert, and `aria-hidden`, the round's text explains them, and one click ends the hold. This is the price of C11a's "committed state is never gated", which is worth more than a perfect tableau.
- [A foe's `defeat` animation and C13a's leave fade stack] → The defeat keyframe ends at `opacity: 0` with `forwards`, so the later leave fade is invisible. It only delays the slot's removal by `--motion-actor`.
- [Many actions per round make the lunge repeat] → The lunge plays only on the first beat of each `action` group and lasts 240ms, which is less than the 400ms pause.
- [Two hits on one foe in consecutive steps] → The per-step `gestureKey` restarts the animation (D4).
- [Budget] → tokens and keyframes (1h), act phase and stage slice (1.5h), StageActor gestures and float (1.5h), line-up snapshot and gauges (1.25h), hold (0.75h), Vitest (1h), browser (1h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
