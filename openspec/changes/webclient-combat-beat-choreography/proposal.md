## Why

After C13b (`webclient-combat-beat-queue`), a round plays one beat per page with truthful intermediate HP, but nothing moves on the stage. The foes C13a (`webclient-combat-foes-on-stage`) stood in `actor-right` also leave the line-up at the round's commit, before their defeat beat is read. A round that ends the fight commits mode `exploration`, so the foes and the combat veil vanish while its beats are still playing. The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §10.2) asks for these gestures:
- on the first beat of each action, the actor steps 24px toward the centre and back
- on `damage`, the target shakes (6px, 180ms) and flashes, a floating number rises, and the HP display animates with the trailing bar 300ms behind
- on `target_defeated`, the target fades and drops out

C12 (`combat-beats-panel` D3) requires a terminal round's beats to play before C11c's (`webclient-mode-transitions`) combat → exploration transition. This change (C13c, the last of the series) adds those gestures and holds the combat stage for the terminal round, without holding back any committed state.

**Implementation profile:** visual. The step, shake, flash, float, and drop, the foes' gauges, and how the held veil and foes feel against the already-committed exploration HUD need motion and look-and-feel judgement at the reference viewport.

## What Changes

- `web/webclient-app/styles/tokens.css`:
  - New duration tokens with the three-level pattern:
    - `--motion-beat-step` (240ms / 0 / 0)
    - `--motion-beat-hit` (180ms / 0 / 0)
    - `--motion-beat-float` (600ms / 0 / 0)
    - `--motion-beat-defeat` (350ms / 150ms / 0)
  - New distance tokens: `--motion-beat-lunge` (24px), `--motion-beat-shake` (6px), and `--motion-beat-rise` (48px), each multiplied by `--motion-travel`.
  - New keyframes: `elosern-beat-lunge-right`, `elosern-beat-lunge-left`, `elosern-beat-hit` (shake plus a brightness flash), `elosern-beat-float`, and `elosern-beat-defeat`.
  - `--motion-trail-delay` becomes 300ms at `full` (design §10.2; C11a set 250ms).
  - `tests/motion_tokens.test.js` learns the four duration tokens.
- `web/webclient-app/lib/beat_queue.js` (C13b):
  - A new `act` phase between `text` and `pause`, lasting the longest gesture the step plays, read through `readMotionMs`.
  - HP now applies when the act starts.
  - `stageFor(state)` returns:
    - the current step's `gesture` per catalog key (`lunge`, `hit`, `defeat`) and its `amount`
    - a `foes` roster, taken from the plan's pre-round active foes
    - the keys whose defeat beat has played
- `web/webclient-app/stores/elosern/beats.js` and `view.js`:
  - The act timer.
  - `view.beatStage`, which is `null` outside a playing round. At the round's end (by itself, or by a skip or flush) it is `null`.
  - `view.beatHold`, which is true while a round whose committed mode is no longer `combat` plays by itself.
- `web/webclient-app/components/StageActor.vue` (C10b, C11b):
  - New props `gesture` (`null` | `lunge` | `hit` | `defeat`), `gestureKey` (restarts the animation per step), and `floatAmount`.
  - An inner keyed wrapper carries `data-beat` and the gesture animation. A `lunge` moves toward the stage's centre, by side.
  - A decorative floating `−N` (`aria-hidden`) rises and fades above the portrait.
  - `defeat` fades and drops the portrait.
  - The player's actor never plays `defeat`: the player stands on stage at all times (design §2).
- `web/webclient-app/components/FoeLineup.vue` (C13a):
  - New props `displayHp` and `stage`.
  - While a round plays, the row stands the round's pre-round active foes, minus those whose defeat beat has played (that foe drops out through the `foe` leave). Otherwise it stands the committed active foes.
  - Each slot gains a slim decorative HP gauge (`aria-hidden`, no numerals) with a fill and a trailing bar, driven by the displayed HP.
- `web/webclient-app/components/HudFrame.vue` (C11c):
  - A new prop `beatHold` renders `data-beat-hold="combat"` on the stage root.
  - While it is set, the combat veil keeps its combat opacity, without the pulse. It fades out over `--motion-reveal` when the hold ends.
  - The flash, the flip, and every mode-gated surface still follow the committed mode at commit.
- `web/webclient-app/AppClient.vue`:
  - It passes each stage actor its gesture from `view.beatStage`: the player by `status.actor.identity`, and each foe by `portrait_ref` inside `FoeLineup`.
  - The line-up renders while `mode === 'combat' || view.beatHold`, and is `inert` during the hold.
  - `HudFrame` receives `beatHold`.
- Stories:
  - `stories/Core/StageActor.stories.js` gains `BeatLunge`, `BeatHit`, and `BeatDefeat`.
  - `stories/Core/FoeLineup.stories.js` gains `RoundInProgress`.
  - `stories/Core/HudFrame.stories.js` gains `TerminalRoundHold`.
- Browser: new `web/tests/browser/test_browser_combat_choreography.py`. It covers a full-motion computed-style check, a reduced run, and the terminal hold at `off` and `reduced`.
- No OOB schema, presenter, server, persistence, or component-manifest change. No component is added or deleted.

Out of scope:
- The queue, the lock, the beat pages, and displayed HP numerals: `webclient-combat-beat-queue` (C13b).
- The foe line-up's layout: `webclient-combat-foes-on-stage` (C13a).
- The flash, veil fade, and panel flip on live mode changes: `webclient-mode-transitions` (C11c).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" (C13a text). `actor-right` keeps the line-up during a held terminal round.
  - MODIFIED "Surface visibility is gated by the committed game mode" (C13a text). The terminal-round hold is the exception for the decorative veil and line-up.
  - MODIFIED "Foes stand opposite the player during combat" (C13a ADDED). The pre-round roster during playback, and a decorative gauge per foe.
  - MODIFIED "Vitals pair an icon, a label, and numerals with a trailing damage bar" (C13b text). The trailing bar follows 300ms behind the fill.
  - ADDED "Combat beats are choreographed on the stage at the motion level".
- `webclient-combat-menu`: MODIFIED "A combat round plays beat by beat" (C13b ADDED). Each beat plays its stage gesture before the pause.

## Impact

- New: `web/tests/browser/test_browser_combat_choreography.py`, Vitest `web/webclient-app/tests/beat_choreography.test.js`.
- Edited source:
  - `web/webclient-app/lib/beat_queue.js`, `web/webclient-app/stores/elosern/{beats,view}.js`
  - `web/webclient-app/components/{StageActor,FoeLineup,HudFrame}.vue`, `web/webclient-app/AppClient.vue`
  - `web/webclient-app/styles/tokens.css`
- Stories: `stories/Core/StageActor.stories.js`, `stories/Core/FoeLineup.stories.js`, `stories/Core/HudFrame.stories.js`.
- Tests edited:
  - Vitest: `tests/beat_queue.test.js`, `tests/store/beat_playback.test.js`, `tests/core/foe_lineup.test.js`, `tests/core/stage_actor.test.js`, `tests/hud_frame.test.js`, `tests/motion_tokens.test.js`
  - Python: `web/webclient/tests/test_node_suite_evidence.py`, and `web/webclient/tests/test_vue_showcase_evidence.py` if it pins the story ids
  - Browser: `.github/browser-shards.json`
- Spec traceability: one new ID (`webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level`). Every modified title is unchanged, so no annotation moves.
- Dependencies:
  - Archive order: C12 (`combat-beats-panel`) → C13a (`webclient-combat-foes-on-stage`) → C13b (`webclient-combat-beat-queue`) → C13c (this change).
  - Hot-spot files shared with C10b, C11b, C11c, C13a, and C13b: `StageActor.vue`, `FoeLineup.vue`, `HudFrame.vue`, `AppClient.vue`, `tokens.css`.
