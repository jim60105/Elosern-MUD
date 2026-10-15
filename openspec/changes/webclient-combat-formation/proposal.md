# Proposal: Stand both sides in a shared-scale combat formation with glance plates

## Why

The user ruled the following:

- The combat command card stands at the stage's true dead centre with a clear gap.
- Both sides are always drawn at one shared scale.
- In combat only, the party may leave its single row.
- Every foe up to the maximum stands on the stage.
- The redundant participant roster (參戰名單, `ParticipantFrame.vue`) is removed in favour of a compact plate on
  each figure.

`webclient-combat-formation-engine` computes that geometry. This change puts it on the stage.

## What Changes

- **Formation on stage.** In combat, the controlled figure, every drawn companion and every active foe (now up to 15,
  previously 3) stand at the engine's boxes, recomputed from the live stage, the band, the top band and the vitals
  dock box on every resize. Exploration and dialogue keep today's single-row layout exactly.
- **Shared scale at every moment.** Entering or leaving combat, and every roster change, glides all figures with the
  same duration, easing and start frame, so heights stay equal throughout. `reduced` and `off` place the figures in
  the commit's frame. Foes still enter as the flash releases.
- **The `map` anchor is not rendered in combat.** The participant frame is deleted. The place card is hidden while in
  combat, because the formation needs the right column: with the place card kept, the planning prototype could not
  fit 11 or more foes at any scale and pushed even single foes down to 0.72–0.78. The place card returns in
  exploration.
- **Glance plates.** A new `plates` stage layer holds one `FigurePlate` per non-controlled figure in its engine slot:
  - `full` form: the name, a 4px tapered hit-point stroke with the trailing damage segment, and a tabular readout
    (current bright, `/ max` receding);
  - `compact` form: no visible name (it stays the accessible name), the stroke and the current value.
  - Plates read `displayHp` during playback.
  - The chrome follows `tmp/core-panel-design-notes.md`: no box, a feathered ground fading upward, one brass hairline
    crown and no lozenge, token colours only.
  - The controlled figure's values stay in the vitals dock (decision-first: one place for the player's own vitals).
- The foe line-up's floor name plate and gauge are removed (the plate replaces them), and so are the depth table and
  the three-foe cap.
- Conditions, tooltips, the keyboard plate group and the low-HP alarm come in `webclient-combat-figure-plates`.
  The defeated/down states come in `webclient-combat-defeated-foes`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`:
  - adds "Combat figures stand in a shared-scale formation" and "Combat figures carry glance plates";
  - removes "Foes stand opposite the player during combat" and "The combat participant frame presents the session's
    participants and their portraits";
  - amends the full-bleed stage (the `plates` layer, the combat positions), the visibility matrix (the place card is
    hidden in combat, plus a plates row), the companion line-up (combat uses the formation), the HUD island stack,
    "Combat identity and status remain legible…" and the beat-choreography damage wording.
- `webclient-combat-menu`: amends the keyboard-hierarchy scenarios and the beat-playback scenarios that named the
  participant frame.
- `webclient-art-panel`: drops the participant frame from the framed-portrait surface lists.

## Impact

- Code (`web/webclient-app/`):
  - `AppClient.vue`: the formation state, a ResizeObserver, plates layer content, the map anchor in combat, and the
    ParticipantFrame mount removed.
  - `components/HudFrame.vue`: the `plates` slot/layer, portrait anchors spanning the stage in combat, the map anchor
    hidden in combat.
  - `components/CompanionLineup.vue` and `components/FoeLineup.vue`: a `formation` prop with stage-coordinate slots
    and shared transitions; floor plate and gauge removed; `foe-lineup.js` cap raised to 15 and depth table retired.
  - New `components/FigurePlate.vue`.
  - `components/ParticipantFrame.vue` deleted.
  - `styles/app-shell.css`: `.elosern-root` duplicates for these classes checked per the Styling pitfall.
- Storybook: `Data/ParticipantFrame` removed and `Core/FigurePlate` added in `component-manifest.json`; formation
  stories on `Core/AppShell`.
- Tests: the formation/plates Vitest files, deletion of the two ParticipantFrame tests, a live-client browser
  geometry method registered in `.github/browser-shards.json`, and migration of browser tests that read
  `participant-frame` or `foe-gauge`.
- `web/webclient-app/AGENTS.md` layout lines.

## Batch: webclient combat stage

- depends-on: webclient-combat-formation-engine
- Code conflicts:
  - With `webclient-combat-figure-plates` (`FigurePlate.vue`, `AppClient.vue`, stories), `webclient-combat-defeated-foes`
    (`FoeLineup.vue`, `CompanionLineup.vue`, `StageActor.vue` usage), `webclient-combat-command-card-centred`
    (`HudFrame.vue`, `AppClient.vue`, `AppShell` stories) and `webclient-combat-stage-target-picking` (both line-ups).
  - Its MODIFIED blocks for the full-bleed stage, the visibility matrix, the companion line-up and the keyboard
    hierarchy are the base the later changes build on.
- Apply in order; archive `webclient-combat-figure-plates` right after this change. Between the two, conditions are
  visible only for the player.
