## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §4, §9.3, §10.2) puts the foes on the stage opposite the player during combat. Today only the player stands in `actor-left`. The foes exist only as 38px thumbnails in `ParticipantFrame.vue` in the `map` anchor, and `actor-right` stays empty in combat, as C10b and C10c require ("`actor-right` … SHALL carry no content in every other state"). C11c (`webclient-mode-transitions`) left the foes' entrance to C13. This change (C13a, the first of three C13 slices) stands the foes in `actor-right`, lays out several of them, and keeps `ParticipantFrame` as the numbers panel. C13b (`webclient-combat-beat-queue`) and C13c (`webclient-combat-beat-choreography`) then play the rounds on this line-up.

**Implementation profile:** visual. The overlapping row, the scale steps per foe count, the slide-in, and the look beside the player at the reference viewport need layout and motion judgement.

## What Changes

- **New governed component `web/webclient-app/components/FoeLineup.vue`**, with story `stories/Core/FoeLineup.stories.js` and manifest title `Core/FoeLineup`.
  - Props: `foes` (the committed combat participants whose `team` is `foes` and whose `state` is `active`, in presenter order) and `artPanel`.
  - It renders at most three `StageActor`s (`side="right"`, never dimmed) inside a `<TransitionGroup name="foe">`, keyed by `identity`. Each actor carries `data-portrait-ref` and `--foe-index`.
  - The portrait entry is `artPanel.portrait_catalog[portrait_ref]`. A `null` ref or a missing entry passes `null`, so `StageActor` shows the truthful name placeholder. The component builds no key and no URL.
  - Foes beyond the third are not on stage. `ParticipantFrame` lists every participant.
  - The root is `div.foe-lineup[data-testid="foe-lineup"][data-count]`. It is decorative art: no focusable element and no pointer events.
- **Layout (design D2).**
  - The line-up grows leftward from `actor-right`'s right edge and is bottom-aligned on the band.
  - The height scale is 1, 0.9, or 0.8 of the portrait anchor's height for one, two, or three foes. Each later foe is offset left by 65% of a slot width and sits behind the one before it.
  - At every supported viewport the row stays right of the stage's centre and clear of the player's actor.
- `web/webclient-app/components/HudFrame.vue`:
  - `[data-anchor="actor-right"]` keeps its box but gains `overflow: visible` in combat, so the row can extend left.
  - The header comment names the line-up.
- `web/webclient-app/AppClient.vue`:
  - `#actor-right` renders `<Transition name="foes-enter" v-bind="inertWhileLeaving"><FoeLineup v-if="mode === 'combat' && combatFoes.length" …/></Transition>` beside the existing dialogue host branch.
  - `combatFoes` is computed from `contextActionsPanel.participants`.
  - Entering combat slides the row in from the right (`--motion-shift-lg × --motion-travel`) with a fade over `--motion-actor`. Leaving combat fades it out, and the leaving copy is inert.
  - Mounting in combat (a reload or reconnect) plays nothing.
  - Inside combat, a foe that leaves the active set (defeated, fled) fades out over `--motion-actor`. A foe that joins slides in, and the rest move to their new slots.
- `ParticipantFrame.vue` is unchanged. It stays the complete numbers panel in `map`, with both sides, tokens, HP numerals, state markers, and thumbnails.
- Stories: `stories/Core/FoeLineup.stories.js` with `OneFoe`, `ThreeFoes`, `FiveFoesCapped`, `PendingPlaceholder`, and `MissingEntry`. `stories/Core/HudFrame.stories.js` `CombatEnter` (C11c) gains a line-up in `actor-right`.
- Browser: new `web/tests/browser/test_browser_combat_stage.py`.
- No OOB schema, presenter, server, store, or persistence change. `ParticipantFrame`, `StageActor`, and `ReferenceArtwork` are unchanged.

Out of scope:
- Beat playback, the submission lock during playback, and HP display values: `webclient-combat-beat-queue` (C13b).
- Every beat gesture, the foes' HP bars, and holding the combat stage during a terminal round: `webclient-combat-beat-choreography` (C13c).
- The combat flash, veil, and panel flip: `webclient-mode-transitions` (C11c).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" (C10c text). `actor-right` carries the foe line-up in combat.
  - MODIFIED "Surface visibility is gated by the committed game mode" (C11c text). A foe line-up row joins the matrix.
  - MODIFIED "Stage actors present the player and the dialogue host with a speaking state" (C10b text). Foe stage actors, never dimmed.
  - MODIFIED "The combat participant frame presents the session's participants and their portraits" (main spec). The frame stays the numbers panel, and `actor-right` holds only the line-up's art.
  - ADDED "Foes stand opposite the player during combat".
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story" (C10c text). Adds the foe line-up.
- `webclient-art-panel`: MODIFIED "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded" (main spec). Stage actors join the list of portrait-consuming surfaces. C10b added the stage actor but did not restate this list; this change fixes that.

## Impact

- New:
  - `web/webclient-app/components/FoeLineup.vue`
  - `web/webclient-app/stories/Core/FoeLineup.stories.js`
  - `web/webclient-app/tests/core/foe_lineup.test.js`
  - `web/tests/browser/test_browser_combat_stage.py`
- Edited source:
  - `web/webclient-app/AppClient.vue`
  - `web/webclient-app/components/HudFrame.vue`
  - `web/webclient-app/styles/app-shell.css`, for the combat `actor-right` overflow if the portrait rules live there
  - `web/webclient-app/component-manifest.json`
- Stories: `stories/Core/HudFrame.stories.js`.
- Tests edited:
  - Vitest: `tests/app_client_stage_actor.test.js`, `tests/hud_frame.test.js`
  - Python: `web/webclient/tests/test_node_suite_evidence.py`, and the showcase snapshot tests that list `Core/StageActor` (`test_vue_showcase_{action,data,world,overlays}_evidence.py`)
  - Browser: `test_browser_contextual_hud_combat.py` (the participant-frame scenario's `actor-right` assertion), `test_browser_contextual_hud_stage.py` (combat now has content in `actor-right`), `.github/browser-shards.json`
- Spec traceability: one new ID (`webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`). Every modified title is unchanged, so no annotation moves.
- Dependencies:
  - Archive order: C11c (`webclient-mode-transitions`) → C12 (`combat-beats-panel`) → C13a (this change) → C13b (`webclient-combat-beat-queue`) → C13c (`webclient-combat-beat-choreography`).
  - Hot-spot files shared with C10b, C10c, C11b, and C11c: `AppClient.vue`, `HudFrame.vue`.
