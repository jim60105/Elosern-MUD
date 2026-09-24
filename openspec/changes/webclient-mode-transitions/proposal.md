## Why

After `webclient-scene-transitions` (C11b), location, appearance, and vitals changes move, but mode changes still cut:
- Entering dialogue hides the command region with `display:none` (C10b). The host portrait, the name plate, and the choice list pop in.
- Entering combat swaps the dock's content, and the combat veil appears with `display` alone.

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §9.3) asks for these rows:
- **Exploration ↔ dialogue:** the command panel slides out to the right over 250ms, the message window widens, the NPC portrait slides in from the right with a 350ms fade, the name plate appears, and exiting reverses all of it.
- **Exploration ↔ combat:** a 120ms white flash, the veil fading in, and the command panel flipping to the combat root, with the reverse on the way out.
- **Dialogue choices:** rows appear with a 40ms stagger.
- **Drawers:** they keep their transitions under the motion level.

This change (C11c, the last C11 slice) delivers those rows. The foes' entrance in combat belongs to C13.

**Implementation profile:** visual. The band's slide-out over the widened window, the flash strength, the panel flip, and the stagger rhythm need motion and look-and-feel judgement at the reference viewport.

## What Changes

- `web/webclient-app/components/HudFrame.vue`:
  - **Collapse by slide, not `display:none`.** In dialogue mode `.stage-band` still switches to one column at commit, so the message window widens in one step (coordinator-approved, design D1).
    - `[data-anchor="band-command"]` becomes an absolutely positioned layer over the band's right third. It carries `inert` from the commit's frame, slides right (`translateX(calc(100% * var(--motion-travel)))`), and fades out over `--motion-panel`, then becomes `visibility: hidden`.
    - Leaving dialogue reverses the slide from the commit's frame, and `inert` clears at commit.
  - **Mode-change hook.** A new `data-mode-change` attribute on the stage root names the last live transition (`exploration-combat`, `combat-exploration`, `exploration-dialogue`, `dialogue-exploration`, …). It is set by a non-immediate watcher, so mount and reconnect never set it.
  - **Combat flash.** A new decorative `.stage-flash` layer (`aria-hidden`, `pointer-events: none`) plays `elosern-stage-flash` once when entering combat: white, peak opacity `--motion-flash-peak`, over `--motion-flash`.
  - **Veil fade.** The combat veil is always rendered. Its opacity fades in and out over `--motion-reveal`, and it pulses only in combat.
  - **Panel flip.** The command region's content plays `elosern-panel-flip-in` when entering combat and `elosern-panel-flip-out` when leaving it: a `rotateY` scaled by `--motion-travel`, with a fade over `--motion-panel`.
- `web/webclient-app/AppClient.vue`: the host's `StageActor` in `#actor-right` is wrapped in `<Transition name="actor-enter" v-bind="inertWhileLeaving">`. It slides in from the right (`--motion-shift-lg × --motion-travel`) and fades over `--motion-actor`, and it leaves the same way.
- `web/webclient-app/components/MessageWindow.vue`: the name plate is wrapped in `<Transition name="plate" v-bind="inertWhileLeaving">`, fading over `--motion-reveal`.
- `web/webclient-app/components/DialogueChoices.vue` (C10c):
  - The rows render inside a `<TransitionGroup tag="div" name="choice-row" appear>` that is the `role="menu"` element itself. Each row carries `--row-index`.
  - A row enters with a fade and a `--motion-shift-sm` rise, delayed by `calc(var(--motion-stagger) * var(--row-index))` over `--motion-reveal`.
  - The card fades in over `--motion-reveal`.
  - Leaving rows are removed at once.
  - Keys and pointer work from the first frame.
- `web/webclient-app/components/AppShell.vue`: the entering-dialogue focus rescue is unchanged (C10b D5). The post-flush rescue on leaving dialogue may now focus the dock while its panel slides back in, because an entering element is in reach.
- `web/webclient-app/styles/tokens.css`: new keyframes `elosern-stage-flash`, `elosern-panel-flip-in`, and `elosern-panel-flip-out`, next to the shared keyframes, all driven by C11a's tokens.
- Drawers and overlays: no change. `HudDrawer`'s slide and the stage recession already use `--motion-base`, which C11a resolves per level. `OverlayHost` has no transition.
- Stories:
  - `stories/Core/HudFrame.stories.js` gains `DialogueEnter` and `CombatEnter` stories.
  - `stories/Core/DialogueChoices.stories.js` gains `Stagger`.
- Browser: a new `web/tests/browser/test_browser_mode_transitions.py` runs at `full`, `reduced`, and `off`.
- No OOB schema, presenter, server, persistence, or component-manifest change. No component is added or deleted.

Out of scope:
- Foes sliding in and out in combat, and every beat animation: `webclient-combat-beat-playback` (C13).
- Location, portrait, vitals, and message-clear transitions, and the inert rule: `webclient-scene-transitions` (C11b).
- The motion level and the tokens: `webclient-motion-level` (C11a).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The command region collapses in dialogue mode and the message window spans the band" (C10c text): the region is inert at commit and slides out, instead of `display:none`.
  - MODIFIED "Surface visibility is gated by the committed game mode" (C10c text): the collapsed command region is the one mode-hidden surface that animates out. It is inert at commit and `visibility: hidden` once its slide ends.
  - ADDED "Mode changes transition at the motion level"

## Impact

- New: `web/tests/browser/test_browser_mode_transitions.py`, Vitest `web/webclient-app/tests/mode_transitions.test.js`.
- Edited source:
  - `web/webclient-app/components/{HudFrame,MessageWindow,DialogueChoices,AppShell}.vue`, `web/webclient-app/AppClient.vue`
  - `web/webclient-app/styles/tokens.css`, `web/webclient-app/styles/app-shell.css` (if the band's dialogue rules live there, per C10b)
- Stories: `stories/Core/HudFrame.stories.js`, `stories/Core/DialogueChoices.stories.js`.
- Tests edited:
  - Vitest: `tests/hud_frame.test.js` (the dialogue band is no longer `display:none`), `tests/app.test.js`, `tests/dialogue_choices.test.js`
  - Python: `web/webclient/tests/test_node_suite_evidence.py`, and `web/webclient/tests/test_vue_showcase_evidence.py` only if it pins the story ids
  - Browser: `test_browser_exploration_dialogue.py` and `test_browser_layout.py`, where they assert the command region's `display:none` in dialogue
  - `.github/browser-shards.json`
- Spec traceability: one new ID. The two modified titles keep their IDs.
- Dependencies:
  - Archive order: C10c → C11a → C11b (`webclient-scene-transitions`) → C11c (this change). C13 (`webclient-combat-beat-playback`) archives after this change and reuses `data-mode-change` and `inertWhileLeaving` for the foes.
  - Hot-spot files shared with C10b, C10c, and C11b: `HudFrame.vue`, `AppClient.vue`, `AppShell.vue`, `MessageWindow.vue`.
