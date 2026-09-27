## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §4, §9.3, §10.2) puts the foes on the stage opposite the player during combat. Today only the player stands in `actor-left`. The foes exist only as 38px thumbnails in `ParticipantFrame.vue` in the `map` anchor, and `actor-right` stays empty in combat, as C10b and C10c require ("`actor-right` … SHALL carry no content in every other state"). C11c (`webclient-mode-transitions`) left the foes' entrance to C13. This change (C13a, the first of three C13 slices) stands the foes in `actor-right` as a composed group in depth, gives each a decorative HP gauge with a trailing bar (design §10.2, C13a paragraph), and keeps `ParticipantFrame` as the numbers panel. C13b (`webclient-combat-beat-queue`) and C13c (`webclient-combat-beat-choreography`) then play the rounds on this line-up.

**Implementation profile:** visual. The depth staging, the scale steps per foe count, the gauges, the slide-in beside the flash, and the look beside the player and the islands at the supported viewports need layout and motion judgement.

## What Changes

- **New governed component `web/webclient-app/components/FoeLineup.vue`**, with its pure geometry and selection in `components/foe-lineup.js`, story `stories/Core/FoeLineup.stories.js`, and manifest title `Core/FoeLineup`.
  - Props: `foes` (the committed combat participants whose `team` is `foes` and whose `state` is `active`, in presenter order), `artPanel`, and `motionLevel`.
  - It renders at most three `StageActor`s (`side="right"`, never dimmed) inside a `<TransitionGroup name="foe">`, keyed by `identity`. Each slot carries `data-portrait-ref` and `--foe-index`.
  - The portrait entry is `artPanel.portrait_catalog[portrait_ref]`. A `null` ref or a missing entry passes `null`, so `StageActor` shows the truthful name placeholder. The component builds no key and no URL.
  - Each slot carries a decorative HP gauge (`aria-hidden`, no numerals) from the committed `hp_current / hp_maximum`, with a trailing bar on the vitals' trail tokens. C13c later feeds it the displayed value during playback.
  - Foes beyond the third are not on stage. `ParticipantFrame` lists every participant.
  - The root is `div.foe-lineup[data-testid="foe-lineup"][data-count][aria-hidden="true"]`. It is decorative art: no focusable element and no pointer events.
- **Layout (design D2).**
  - A depth-staged row that grows leftward: the first foe stands in front, each later foe behind the one before it, further left, smaller (1 | 0.9, 0.78 | 0.8, 0.7, 0.61 of the player's height), and a little higher up-stage. Each later foe shows 46% of its width past the one in front.
  - The row steps in from `actor-right`'s inset until the front foe's face clears the participant frame, which fills the `map` anchor in combat (new token `--foe-face-clear`, larger at short viewports so the front gauge clears a full frame too).
  - At 1920x1080, 1440x900, and 1280x720 the row stays right of the stage's centre, clear of the player, the scene caption, and the expanded command line.
- `web/webclient-app/components/HudFrame.vue`: `[data-anchor="actor-right"]` keeps its box and gains an explicit `overflow: visible` in combat; the header comment names the line-up.
- `web/webclient-app/AppClient.vue`:
  - `#actor-right` renders `<Transition name="foes-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving" @after-leave><FoeLineup v-if="mode === 'combat' && combatFoes.length" …/></Transition>` beside the dialogue host.
  - Entering combat, the row fades in over `--motion-actor` after half the flash while each foe slides in from the right, the front foe furthest. Leaving combat, it fades while the foes drift right, and the leaving copy is inert. Mounting in combat (a reload or reconnect) plays nothing.
  - Inside combat, a foe that leaves the active set (defeated, fled) fades where it stands, a foe that joins slides in, and the rest glide to their new places and sizes.
  - It exposes the row's reach (`--foe-lineup-span`, `--foe-front-scale`) on the client root until a leaving row has faded.
- **The scene caption** (`styles/app-shell.css`, `SceneBackdrop.vue`): in combat the caption plate stays centred between the player and the row's leftmost foe and glides with the row; in a narrow caption the alt text now truncates before the label.
- **Visual refinements of earlier work:**
  - `StageActor.vue` (C10b): the figure mask reaches zero at the box's edges and top, so no rectangular seam shows on a dark scene or where foes overlap. Foes use a tighter mask so overlapping portraits read as bodies, not pale cards.
  - The participant frame's product styling (`styles/app-shell.css`, H3/C4c): denser rows (32px token, 36px thumbnail, 6px row padding), a long name ends in an ellipsis, and a compact variant at short viewports, so a six-participant frame ends above the stage floor at 1920x1080 and 1440x900.
- Stories: `stories/Core/FoeLineup.stories.js` with `OneFoe`, `TwoFoes`, `ThreeFoes`, `FiveFoesCapped`, `PendingPlaceholder`, and `MissingEntry` on a stage-geometry frame; shared fixtures `stories/fixtures/combat_stage.js`. `Core/HudFrame` combat stories show a line-up; `Core/AppShell` `CombatHud` stands three foes with portraits, `CombatOneFoe` and `CombatFiveFoes` are added, and `ModeJourney` fights three foes and gains a `defeat` step.
- Browser: new `web/tests/browser/test_browser_combat_stage.py`.
- No OOB schema, presenter, server, store, or persistence change.

Out of scope:
- Beat playback, the submission lock during playback, and displayed HP values: `webclient-combat-beat-queue` (C13b).
- Every beat gesture, feeding the gauges the displayed value, and holding the combat stage during a terminal round: `webclient-combat-beat-choreography` (C13c).
- The combat flash, veil, and panel flip: `webclient-mode-transitions` (C11c).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces". `actor-right` carries the foe line-up in combat.
  - MODIFIED "Surface visibility is gated by the committed game mode". A foe line-up row joins the matrix.
  - MODIFIED "Stage actors present the player and the dialogue host with a speaking state". Foe stage actors, never dimmed.
  - MODIFIED "The combat participant frame presents the session's participants and their portraits". The frame stays the numbers panel, compact and ellipsised, and `actor-right` holds only the line-up's art and gauges.
  - MODIFIED "The scene backdrop renders the art payload truthfully behind the stage". The caption clears the line-up.
  - ADDED "Foes stand opposite the player during combat".
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story". Adds the foe line-up.
- `webclient-art-panel`: MODIFIED "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded". Stage actors join the list of portrait-consuming surfaces (C10b removed the "dialogue host avatar" it named).

## Impact

- New:
  - `web/webclient-app/components/FoeLineup.vue`, `web/webclient-app/components/foe-lineup.js`
  - `web/webclient-app/stories/Core/FoeLineup.stories.js`, `web/webclient-app/stories/fixtures/combat_stage.js`
  - `web/webclient-app/tests/core/foe_lineup.test.js`
  - `web/tests/browser/test_browser_combat_stage.py`
- Edited source:
  - `web/webclient-app/AppClient.vue`
  - `web/webclient-app/components/{HudFrame,StageActor,SceneBackdrop}.vue`
  - `web/webclient-app/styles/{tokens,app-shell}.css`
  - `web/webclient-app/component-manifest.json`
- Stories: `stories/Core/{HudFrame,AppShell}.stories.js`, `stories/fixtures.js`.
- Tests edited:
  - Vitest: `tests/app_client_stage_actor.test.js`, `tests/mode_transitions.test.js`, `tests/hud_frame.test.js`, `tests/overlays/objective_tracker_integration.test.js`
  - Python: `web/webclient/tests/test_node_suite_evidence.py`, and the four showcase evidence lists that name `Core/StageActor`
  - Browser: `test_browser_contextual_hud_combat.py` (the participant-frame test's `actor-right` assertion), `.github/browser-shards.json`
- Spec traceability: one new ID (`webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`). Every modified title is unchanged, so no annotation moves.
- Dependencies:
  - Archive order: C11c (`webclient-mode-transitions`) → C12 (`combat-beats-panel`) → C13a (this change) → C13b (`webclient-combat-beat-queue`) → C13c (`webclient-combat-beat-choreography`).
  - Hot-spot files shared with C10b, C10c, C11b, and C11c: `AppClient.vue`, `HudFrame.vue`, `StageActor.vue`.
  - C13c's artifacts are adjusted: the gauge now ships here, and C13c feeds it the displayed value.
