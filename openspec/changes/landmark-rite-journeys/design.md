# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §15 (Browser row). Existing code, read on 2026-11-14:

- `web/tests/browser/test_wilderness_travel.py`: the `_TravelStage` base class and `TravelRouteTests` drive the travel stage with synthetic committed panels and synthetic action results, and assert on `data-testid`s; `TravelRouteTests` covers the generic landmark card's focus. `web/tests/browser/travel_log_fixture.py` builds travel log panels.
- Every browser test class and method must be listed in `.github/browser-shards.json`; `tests.test_evennia_test_optimization_contract` enforces exact ownership.
- Local browser runs use the prebuilt bundle: run `pnpm run build` first.
- Test ids of the rite surfaces: `rite-arrival-card`, `rite-arrival-approach`, `rite-arrival-leave`, `rite-arrival-seen`, `rite-panel`, `rite-backdrop`, `rite-entry` (`landmark-rite-surfaces`, `landmark-rite-stage`).
- The viewports and the 16px text floor are the project's standing browser checks.

## Goals / Non-Goals

**Goals**

- The two journeys of the design, each under the five-minute CI budget.

**Non-Goals**

- No new behaviour. A journey that fails because the flow is wrong is fixed by correcting the component or binding to match `landmark-rite-surfaces` and `landmark-rite-stage`; a requirement is never changed here.
- No performer picking, no newly-lit line, no art assertion (the synthetic panel carries no artwork in one journey and a bundled scene descriptor in the other, only to exercise both layouts).
- No real server-side rite: the committed panels and the action result are synthetic, as in the travel stage tests.

## Decisions

### D1. Test module (`web/tests/browser/test_landmark_rite.py`)

Class `LandmarkRiteTests`, built on the stage harness of `test_wilderness_travel.py` (import its base class and helpers; move a helper into a shared module only if it cannot be imported). A module-level helper builds a synthetic available `rite` panel (two options, one performer, synthetic names) and a synthetic success result for `explore.landmark_rite` whose data carries a three-line delivery (narration, actor speech, host speech).

`test_wilderness_rite_journey`:

1. At 1451x790, start on the travel stage with no `rite` panel; commit a snapshot that makes the panel available together with a `landmark_reached` notice.
2. The rite arrival card is visible, the generic landmark card is not, focus is on the approach button, the card lies inside the choices anchor's box, and no text node in the card computes below 16px.
3. Press Enter: the rite backdrop and the rite panel are visible, the party figures are visible, the travel map is not, and the page has no horizontal or vertical scrollbar.
4. Press `1`: exactly one `explore.landmark_rite` action was sent with the first option's key and a null member; the panel is gone.
5. Commit the synthetic success result: the first scene line is visible; advance with Space until the scene finishes; each line's text appears in order.
6. The panel is back and holds focus. Press Escape: the travel map is back and the return entry is visible.
7. Resize to 2560x1440, press R, press Enter: the stage shows with no scrollbar, the panel inside the choices anchor, and no text below 16px.

`test_city_rite_journey` at 1451x790: the same steps 1 to 6 from a settlement room (the non-travel layout): the card over the room, the stage, the option, the scene, and the return entry under the place card.

Register `LandmarkRiteTests.test_wilderness_rite_journey` and `LandmarkRiteTests.test_city_rite_journey` in `.github/browser-shards.json`, in the shard that holds `test_wilderness_travel.TravelRouteTests`.

### D2. Defect fixes

When a journey exposes a layout, focus or overflow defect, fix the smallest thing in `components/rite/*.vue`, `composables/use-rite-stage.js` or the rite bindings of `AppClient.vue`, and add or extend the matching Vitest assertion in `tests/rite/surfaces.test.js` or `tests/app_client_rite.test.js` when the defect is observable there. Name every such fix in the hand-off.

## Risks / Trade-offs

- A journey that grows past five minutes in CI must be split by method; the two methods are already independent.
