# Proposal

## Why

A district is lit the moment the character's landmark node enters map knowledge, so walking onto a landmark reveals a whole district with nothing for the player to do. Rites are now performable from the text client and the browser, recorded on the player character, and available at every district landmark. This change is the behavioural flip of the design (`docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §8): a district is lit if and only if the player character has completed at least one rite there.

Everything a player needs to light a district already exists when this change lands, so no district is ever unlit by construction.

## What Changes

- **BREAKING** District lighting is derived from the rite completion record. A visited landmark node no longer lights anything. Existing characters keep their visit history but their districts are unlit until they complete a rite; development databases are reset, there is no migration.
- The reveal projection takes the lit set from its caller. Map knowledge remains a view of visits only.
- The area map, the world map, distant markers, travel planning and wilderness disclosure all read the one record-derived lit set. An unreadable rite record degrades to an empty lit set with a warning.
- A movement no longer announces `已探明：<district>`. The announcement returns on the first completed rite in `landmark-rite-discovery-notice`; until then the world map's own newly-lit animation is the only notice.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-districts`: lighting derives from completed rites.
- `map-district-discovery`: a movement announces no discovery.
- `wilderness-ground-reveal`: the reveal projection's lit ownership comes from completed rites.

## Impact

- Edits: `world/rules/map_district_lighting.py`, `world/rules/map_knowledge.py`, `world/rules/map_discovery.py`, `world/rules/sight.py`, `world/rules/travel_events.py`, `world/rules/travel_interrupts.py`, `web/webclient/presentation/area_map.py`, `web/webclient/presentation/world_map.py`, `web/webclient/presentation/rite.py`, `tools/world_map_payload.py`, and the tests that light a district by a visit.
- Documentation: `docs/development/map-panel-protocol.md`, `docs/development/continental-geography.md`.
- The movement-time `district_lit` flag and the `lit_district` notice field become dead and are removed by `landmark-rite-arrival-signal-removal`.

## Batch:

- depends-on: landmark-rite-stage
- conflicts: `landmark-rite-arrival-signal-removal` (`travel_events.py`, `travel_interrupts.py`), `landmark-rite-discovery-notice` (`world/rules/landmark_rites.py` tests) and `landmark-rite-art` (`web/webclient/presentation/rite.py`); run serially with them.
- parallel with: `landmark-rite-journeys`, `landmark-rite-performer-picking`, `landmark-rite-watch-perspectives` (no shared file).
