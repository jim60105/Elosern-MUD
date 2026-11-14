# Proposal

## Why

After `landmark-rite-lighting`, a district lights only when a rite completes, never on a movement step. Two movement-time signals therefore can never fire: the `district_lit` travel interrupt flag and the `lit_district` field of the `landmark_reached` travel notice, together with the generic landmark card's `◆ <district>已探明` row that renders it. Dead wire fields and dead flags mislead later work. This change removes them (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §10).

## What Changes

- **BREAKING** The wilderness step interrupt flags no longer include `district_lit`. The remaining flags keep their order.
- **BREAKING** The `landmark_reached` travel notice carries exactly `arrival_node`, `name`, `prose` and `artwork`.
- The travel log line for a landmark arrival is `抵達<name>。` with no lighting suffix.
- The travel captures no longer read or carry the lit-district set.
- The generic landmark card loses its lit row; the browser's arrival record loses `litDistrict`; the walking interrupt text table loses `district_lit`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `wilderness-travel-interrupts`: `district_lit` removed from the flag set.
- `webclient-travel-log`: `landmark_reached` carries no lighting field.
- `webclient-travel-route-walking`: the landmark arrival card shows no lighting row.

## Impact

- Server: `world/rules/travel_interrupts.py`, `world/rules/travel_events.py`, `web/webclient/presentation/travel_log.py`.
- Browser: `web/static/webclient/js/elosern/protocol/panels/travel_log.js`, `web/webclient-app/stores/elosern/travel.js`, `web/webclient-app/components/travel/leg-model.js`, `web/webclient-app/components/travel/LandmarkCard.vue`, `web/webclient-app/stories/fixtures/travel_log.js`, `web/webclient-app/stories/World/WildernessTravel.stories.js`.
- Tests: `world/rules/tests/test_travel_interrupts.py`, `world/rules/tests/test_travel_events.py`, `web/webclient/presentation/tests/test_travel_log.py`, `web/webclient/presentation/tests/test_world_map.py`, `web/static/webclient/js/tests/travel_log.test.js`, `web/static/webclient/js/tests/protocol_immutable.test.js`, `web/webclient-app/tests/travel/landmark.test.js`, `web/webclient-app/tests/travel/route-walking.test.js`, `web/tests/browser/test_wilderness_travel.py`, `web/tests/browser/travel_log_fixture.py`.
- Documentation: `docs/development/map-panel-protocol.md`, `docs/development/webclient-synchronization.md`, `web/webclient-app/AGENTS.md`.

## Batch:

- depends-on: landmark-rite-lighting
- conflicts: none after `landmark-rite-lighting`; `landmark-rite-performer-picking` touches different files.
