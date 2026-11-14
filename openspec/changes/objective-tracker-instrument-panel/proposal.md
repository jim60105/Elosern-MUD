# Proposal

## Why

The objective line is the last of the three `map`-column surfaces the approved prototype (`docs/design/map-column-instrument-panels/ObjectiveLineInstrument.vue`) restates as a borderless instrument panel. Today it is a 32px boxed pill whose visible `目標` label truncates the objective itself in the column, whose completion box and `n/m` tag state progress only as text, and whose further-rows count reads as a second `+N` beside a `+reward`.

## What Changes

- `ObjectiveTracker.vue` wears the shared `instrument-panel` chrome (from `place-card-instrument-panel`) and spans the column; no fixed 32px box, border, radius, shadow or fill.
- The visible `目標` label is removed; `目標` stays the region's accessible name.
- The completion box becomes a 12px lozenge: an open gold outline while in progress, filled `--buff` with a dark check once `stage_progress >= objective_quantity`, with the accessible name 進行中 / 已達成 (shape and text, never colour alone).
- A counted objective (`objective_quantity > 1`) adds quantity strokes under the line: one 13×3px slanted tick per unit up to 12 units (reached ticks `--gold-400`, or `--buff` once done; empty ticks a faint paper wash), and above 12 units one continuous 3px stroke tapering to a point at its left end, filled to `stage_progress / objective_quantity`. Its readout becomes tabular `n` (`--paper-50`, weight 600) `/ m` (`--paper-500`).
- The `+reward_copper` tag stays in gold mono.
- The further-rows count becomes a stacked-lines glyph plus the number, with the accessible name `另有 N 項追蹤目標`, so it never reads as a second `+N`.
- Every existing `data-testid` is kept; the HudFrame rule that hides `.obj` outside exploration keeps working because the root keeps the `obj` class.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the objective tracker requirement drops the visible label and the fixed row height, states the completion marker by shape plus accessible name, adds the tick and stroke quantity marks and the tabular readout, and turns the further-rows count into a glyph-and-number with an accessible name.

## Impact

- Code: `web/webclient-app/components/ObjectiveTracker.vue` (script computeds, template, scoped styles).
- Tests: `web/webclient-app/tests/overlays/objective_tracker.test.js`, `tests/overlays/objective_tracker_integration.test.js`; browser `web/tests/browser/test_browser_contextual_hud_stage.py` (`test_objective_line_shows_only_in_exploration`) and a new method in `web/tests/browser/test_browser_map_column_instruments.py`, registered in `.github/browser-shards.json`.
- Stories: `web/webclient-app/stories/Overlays/ObjectiveTracker.stories.js` (frame, header comment, two new stories for a reached count and a count above 12); the component manifest is unchanged.
- Human-reviewed: the objective panel's visual fidelity against `ObjectiveLineInstrument.vue`, recorded in the review document named in `design.md` (§ Visual review). No automated test judges the look.

## Batch:

- depends-on: local-map-instrument-panel
- conflicts: imports `components/instrument-panel.css` from `place-card-instrument-panel`; edits `tests/overlays/objective_tracker_integration.test.js` after `local-map-instrument-panel` changed its expected child order; adds a method to `web/tests/browser/test_browser_map_column_instruments.py` and appends to `.github/browser-shards.json`. Land it last.
