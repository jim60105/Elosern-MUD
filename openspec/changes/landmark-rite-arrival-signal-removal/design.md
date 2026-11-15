# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §10. Sites found on 2026-11-14 with `rg "district_lit|lit_district\b|litDistrict"`:

- `world/rules/travel_interrupts.py`: `FLAG_ORDER` contains `"district_lit"`; `MovementFacts.lit_districts`; `read_movement_facts` fills it from the lighting module; `movement_flags` raises `"district_lit": bool(after.lit_districts - before.lit_districts)`; the module docstring lists the flag.
- `world/rules/travel_events.py`: `TravelCapture.lit_districts`; `_capture` fills it; the `landmark_reached` text renderer appends `<lit_district>已探明。`; the draft builder computes `newly_lit` and sets the `lit_district` param.
- `web/webclient/presentation/travel_log.py`: `PARAM_FIELDS["landmark_reached"]` includes `lit_district`; `_optional_str(params, "lit_district")`.
- Browser protocol: `protocol/panels/travel_log.js` (`PARAM_FIELDS.landmark_reached`, `optionalName(params.lit_district, ...)`).
- Browser app: `stores/elosern/travel.js` (`litDistrict: p.lit_district ?? null` in the arrival record), `components/travel/leg-model.js` (`district_lit: "探明新的地區"` in the interrupt text table), `components/travel/LandmarkCard.vue` (the `landmark-card__lit` paragraph, its style, and the header comment naming `litDistrict`).
- Fixtures, stories, tests and documents listed in the proposal's Impact.

## Goals / Non-Goals

**Goals**

- No remaining reference to the two dead signals in code, fixtures, tests or documents outside `openspec/changes/archive/` and `docs/superpowers/`.

**Non-Goals**

- No replacement movement flag or notice field. The world map already announces a newly lit district from the committed map panel, and the rite stage names it.
- No change to any other flag, notice kind, bound or to the landmark card's art, prose, focus or dismissal.
- No removal of `LandmarkCard.vue`: it remains the arrival card when the `rite` panel is unavailable.
- No schema version change and no compatibility shim.
- `docs/design/wilderness-travel/` (an approved prototype, reference only) is not edited.

## Decisions

### D1. Server

- `travel_interrupts.py`: remove `"district_lit"` from `FLAG_ORDER` and from `movement_flags`; remove `MovementFacts.lit_districts` and the lighting import and read in `read_movement_facts`; update the docstrings (including the paragraph about a corrupt knowledge record). With the lighting read gone, `read_movement_facts`'s `knowledge_owner` keyword has no use: remove it, and stop forwarding it from `movement_settlement.MovementObservation`'s private interrupt captures. The public `capture_before` / `capture_after` keep it for the travel log capture.
- `travel_events.py`: remove `TravelCapture.lit_districts` and its fill in `_capture`; the lit set stays a local read in `_capture` because `_distant_in_sight` still names a visible distant source only for a lit district (the `landmark_sighted` naming rule, unchanged); the `landmark_reached` renderer returns `f"抵達{p['name']}。"`; remove `newly_lit` and the `lit_district` key from the draft params.
- `travel_log.py`: `PARAM_FIELDS["landmark_reached"] = frozenset({"arrival_node", "name", "prose", "artwork"})`; remove the `lit_district` validation line. The schema version stays 1: the exact-field validators already reject a stale record, and a version bump is a compatibility device this pre-release project does not need.

### D2. Browser

- `protocol/panels/travel_log.js`: the same field list and no `lit_district` validation.
- `stores/elosern/travel.js`: the arrival record is `{id, name, prose, artwork}` (plus whatever other keys it has today besides `litDistrict`).
- `leg-model.js`: remove the `district_lit` entry.
- `LandmarkCard.vue`: remove the lit paragraph, the `.landmark-card__lit` style rules and the mention in the header comment.
- Fixtures and stories: remove `lit_district` from every `landmark_reached` params object and any story arg that only fed it (the `lit` arg of the landmark story in `WildernessTravel.stories.js`, with its argType).

### D3. Tests

Update, do not delete, the tests that named the signals:

- `test_travel_interrupts.py`: the transition table no longer has a lit-district row; add one assertion that the flag set of a step onto a landmark is exactly `("landmark_reached",)` and that `FLAG_ORDER` does not contain `district_lit`.
- `test_travel_events.py`: a landmark arrival draft has exactly the four params, and its text names the synthetic landmark once and is the same whether or not the owner holds a completed rite for that district.
- `test_travel_log.py` and `travel_log.test.js`: the four-field record is accepted; a record that still carries `lit_district` is rejected as an extra key, on both sides.
- `landmark.test.js`: the arrival record has no `litDistrict`; the card renders no lit row.
- `route-walking.test.js`, `test_wilderness_travel.py`, `travel_log_fixture.py`, `test_world_map.py`, `protocol_immutable.test.js`: remove the flag and the field from their fixtures and flag lists.
- Also carrying the dead signals (found while applying): `world/maps/tests/test_wilderness_population.py` (a `MovementFacts` constructor), `web/webclient-app/tests/app_client_rite.test.js` and `web/tests/browser/test_landmark_rite.py` (a `lit_district: null` arrival fixture), and the `landmark-card-lit` hook row in `docs/development/webclient-vue-frozen-contract-audit.md`. `travel_log_fixture.py` and `test_world_map.py` hold no reference and stay unchanged.

### D4. Documentation

- `docs/development/map-panel-protocol.md`: the interrupt list example and its bullet list lose `district_lit`.
- `docs/development/webclient-synchronization.md`: the `landmark_reached` row of the source table, its params row and the nullable-fields sentence lose `lit_district`.
- `web/webclient-app/AGENTS.md`: the landmark card paragraph loses the `◆ <district>已探明` clause.

## Risks / Trade-offs

- Deploy skew: both validators match fields exactly, so a browser still running a bundle from before this change rejects a four-field `landmark_reached` record (and the reverse) until the page reloads. Travel notices are never persisted, so only that short window is affected; it is accepted rather than covered by a version bump or shim.

- A wire change without a version change: a stale local `dist` hides a mistake in the browser mirror. Run `pnpm run build` before any browser test.
