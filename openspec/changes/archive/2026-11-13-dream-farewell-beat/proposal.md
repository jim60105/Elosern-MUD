# Proposal: a deterministic farewell beat when the dream ends

## Batch: dream proposal co-editing

Stage 10 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Farewell").

- depends-on: dream-wish-change-report
- conflict: `web/webclient-app/components/DreamPanel.vue`,
  `tests/dream.test.js`, `stories/World/DreamPanel.stories.js`,
  `test_vue_dream_stage_evidence.py` (shared with the two panel stages);
  `world/narrative/dream_surface.py` and
  `world/narrative/tests/test_dream_surface.py` (shared with the server
  stages); `web/webclient-app/AppClient.vue` and
  `composables/use-sleep-handoff.js` are touched only by this change in the
  batch but are busy files for other work. Apply last.

## Why

Confirming or awakening closes the dream at once: the panel disappears on
the same publication that commits the departure, and the only closing words
are one generic sentence. The design ends the dream with a short closing line
from the goddess that depends on how the player leaves, and it must work with
every model service offline.

## What Changes

- The server authors the closing line as fixed text chosen by the departure
  outcome (confirmed, wish kept as a draft, left with nothing) and by whether
  the dream track reached climax. It replaces the current ending sentence in
  the panel state's `ending` field, in the ordinary output (so it reaches the
  message log) and in the text client. The canonical post-climax phase stays
  reported through `ending_phase`; the `dream-explicit-presentation`
  requirement that the ending also narrates it is amended, as the source
  design's "in place of the current ending sentence" already intends. No
  model call, no new wire field.
- The browser keeps the dream stage mounted for a farewell state after a live
  departure: the closing line types into the message band, waits for Enter or
  a click, then the stage fades and releases to the existing waking flow. All
  dream controls are inert meanwhile. Reduced or disabled motion shows the
  line in full and omits the fade. A reconnect or a fresh page shows the
  waking surface without replaying the farewell. Every surface that yields to
  an open dream stays yielded while the farewell is held, including the
  travel layout, which previously read only the committed `open` flag.
- The departure still commits on the server first; the farewell gates no
  committed state and sleep continuation proceeds regardless.
- **Human-reviewed:** the six closing lines and the farewell's visual
  transition are reviewed by a person against the source design's "Farewell"
  section and Storybook `Design/DreamWish` (stories `FarewellGranted`,
  `FarewellKept`). Tests establish selection, state and gating only and pin
  no wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dream-sleep-surface`: adds the server-authored farewell requirement.
- `webclient-dream-stage`: adds the browser farewell state.
- `dream-explicit-presentation`: the deterministic ending reports the
  post-climax phase and presents the farewell line.

## Impact

- Code: `world/narrative/dream_surface.py`,
  `world/narrative/tests/test_dream_surface.py`,
  `web/webclient-app/components/DreamPanel.vue`,
  `web/webclient-app/composables/use-dream-farewell.js` (new),
  `web/webclient-app/composables/use-app-client.js`,
  `web/webclient-app/composables/use-sleep-handoff.js`,
  `web/webclient-app/AppClient.vue`,
  `web/webclient-app/components/travel/travel-model.js`,
  `web/webclient-app/stores/elosern.js`,
  `web/webclient-app/stores/elosern/travel.js`,
  `web/webclient-app/stores/elosern/travel_log.js`,
  `web/webclient-app/tests/dream.test.js`,
  `web/webclient-app/tests/dream_farewell.test.js` (new),
  `web/webclient-app/tests/travel/layout.test.js`,
  `stories/World/DreamPanel.stories.js`,
  `web/webclient/tests/test_vue_dream_stage_evidence.py`, rebuilt `dist`.
- No wire shape change, no action change, no migration.
- Estimate: 8 hours (server line and tests 1.5 h, composable and mount 1.5 h,
  panel farewell state 1.5 h, travel layout 0.5 h, Vitest 2 h, stories and
  gates 1 h).
