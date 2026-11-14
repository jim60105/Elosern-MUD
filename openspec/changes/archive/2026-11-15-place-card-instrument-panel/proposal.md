# Proposal

## Why

The place card is the first of the three `map`-column surfaces the approved prototype (`docs/design/map-column-instrument-panels/PlaceCardInstrument.vue`) restates as a borderless instrument panel, after the style guide `docs/development/hud-instrument-panels.md`. Today it is a bordered, rounded, shadowed card with outlined pill buttons, and its location heading slides in from the left, away from the column's anchored right edge.

## What Changes

- A shared stylesheet `web/webclient-app/components/instrument-panel.css` (class `instrument-panel`) carries the column's per-panel chrome: a feathered ink ground (`var(--panel)` with a 9px × S backdrop blur, masked to feather to the left and over the last 12px × S at the bottom) and one brass fitting (the `--band-ornament` lozenge at the top-right corner, a 1px crown running left along the top, a 1px spine 14px × S in from the right edge). It has no border, radius, shadow or opaque fill, and pads its content 12px top, 6px bottom, 10px left and, by default, 26px right to clear the spine. The minimap and objective line reuse it in the next two changes.
- `PlaceCard.vue` wears that chrome instead of the island box. Place and time are right-aligned against the spine: the heading in `--paper-50`, a 56px gold rule fading toward the left, the time in tabular `--f-num` figures in `--paper-500`, all with a dark text shadow.
- The two room actions (查看房間, 休息) lose their outlined pill: no border, no fill, the same 30px × S hit box, the glyph at opacity .86 rising to 1 on hover or keyboard focus, and a 10×1px `--gold-500` brass tick under the active one. 休息 keeps its visible word.
- A new location slides in from the right (the anchored edge) instead of the left; `reduced` keeps the fade and drops the travel, `off` has no CSS phase.
- The short-viewport `.place-card` duplicate in `styles/app-shell.css` is removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: a new requirement defines the instrument-panel chrome; the place-card requirement replaces its island-chrome scenario with the instrument panel, right-aligns its two lines and makes its room actions chromeless; the transition requirement's location slide enters from the right.

## Impact

- Code: new `web/webclient-app/components/instrument-panel.css`; `web/webclient-app/components/PlaceCard.vue` (template classes and the whole `<style>` block; props, events, `data-testid`s and the `inertWhileLeaving` transition binding unchanged); `web/webclient-app/styles/app-shell.css` (the `.place-card` lines under `@media (max-height: 820px)`).
- Tests: `web/webclient-app/tests/place_card.test.js`; `web/tests/browser/test_browser_scene_transitions.py` (slide direction); a new method in `web/tests/browser/test_browser_map_column_instruments.py`, registered in `.github/browser-shards.json`.
- Stories: `web/webclient-app/stories/Core/PlaceCard.stories.js` frame width and header comment; the component manifest is unchanged.
- Human-reviewed: the place panel's visual fidelity against `PlaceCardInstrument.vue`, recorded in the review document named in `design.md` (§ Visual review). No automated test judges the look.

## Batch:

- depends-on: map-column-instrument-geometry
- conflicts: shares the `@media (max-height: 820px)` block of `styles/app-shell.css` with `map-column-instrument-geometry`; `local-map-instrument-panel` and `objective-tracker-instrument-panel` import the stylesheet this change creates, add methods to `web/tests/browser/test_browser_map_column_instruments.py` and append to `.github/browser-shards.json`. Land it second.
