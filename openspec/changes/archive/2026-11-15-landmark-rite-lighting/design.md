# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §8. Existing code, read on 2026-11-14:

- `world/rules/map_district_lighting.py`: `lit_district_keys_from_visits(visits, registry=None)` and `lit_district_keys(character, registry=None)` (reads `map_knowledge`, raises `KnowledgeError` on a corrupt record).
- `world/rules/map_knowledge.py`: `KnowledgeSnapshot.lit_district_keys()`, `KnowledgeSnapshot.revealed_in_bounds(bounds, *, obj="")` (calls `self.lit_district_keys()`), `_lit_district_keys_for_record(visited, chunks)`, and the module function `revealed_in_bounds(character, bounds)`.
- Callers of the lit set: `world/rules/sight.py` (`visible_distant_markers`), `world/rules/travel_events.py` (`_capture`), `world/rules/travel_interrupts.py` (`read_movement_facts`), `web/webclient/presentation/area_map.py` (`_lit_landmarks(visited)` and `snapshot.revealed_in_bounds(bounds, obj=...)` in the wilderness layer), `web/webclient/presentation/world_map.py` (`assemble_world_map(*, visit_ids, current, markers)` and `world_map_presenter` both derive `lit` from visited node ids), `web/webclient/presentation/rite.py` (`district.lit`).
- Other callers of `assemble_world_map`: `tools/world_map_payload.py` (builds a payload by visiting every landmark), `web/webclient/presentation/tests/test_world_map.py`, `web/webclient/presentation/tests/test_world_map_measurement.py`.
- Callers of the module-level `revealed_in_bounds(character, bounds)`: `world/rules/travel_plan.py`, `world/rules/wilderness_disclosure.py` (signature unchanged, callers unchanged).
- `world/rules/map_discovery.py` `publish_traversal_narrative(actor, before)`: appends `\n已探明：<district>` to the movement message and logs `map_district_discovered` when the reached node is a landmark first visited by this traversal.
- `world/rules/landmark_rite_record.py`: `completed_district_keys(owner)` (raises `LandmarkRiteRecordError`), `read_record`, `with_completion`, `write_record`.
- Test fixtures that light a district by visiting its landmark include `web/webclient/presentation/tests/test_area_map/_wilderness_fixture.py` and `web/webclient/presentation/tests/test_area_map/test_wilderness_content.py`; they do not name any lighting function.

## Goals / Non-Goals

**Goals**

- One source of the lit set, one function every consumer calls.
- Map knowledge stops deriving lighting.

**Non-Goals**

- No migration of `map_knowledge` or of existing characters.
- No change to what a visit reveals: sight discs, visited places and the trail are unchanged.
- No announcement of a newly lit district on a rite, in text or in the browser (`landmark-rite-discovery-notice`). Between the two changes a first rite lights the district silently; the world map still animates it.
- No removal of the `district_lit` interrupt flag, the `lit_district` notice field or the landmark card's lit row (`landmark-rite-arrival-signal-removal`). After this change they are always false or null; do not touch them here.

## Decisions

### D1. Lighting module (`world/rules/map_district_lighting.py`)

Replace the module's functions with:

```python
def lit_district_keys(character, registry=None) -> frozenset[str]:
    """The districts whose rite this character has completed at least once."""

def readable_lit_district_keys(character, registry=None) -> frozenset[str]:
    """As lit_district_keys, degrading to an empty set when the record is unreadable."""
```

`lit_district_keys`: `completed_district_keys(character)` intersected with the keys of `registry` (default `world.lore.map_districts.current().districts`). It reads no `map_knowledge`, writes nothing and creates no attribute. A corrupt record raises `LandmarkRiteRecordError`.

`readable_lit_district_keys`: calls `lit_district_keys`; on `LandmarkRiteRecordError` it logs `log_warn("landmark_rite_record_corrupt", exc=error, context={"char": getattr(character, "pk", None), "district": ""})` and returns `frozenset()`.

Delete `lit_district_keys_from_visits`. Update the module docstring.

`character` is the record owner. Every caller below already passes the knowledge owner (the player character or the commander behind a possessed body).

### D2. Map knowledge (`world/rules/map_knowledge.py`)

- `KnowledgeSnapshot.revealed_in_bounds(self, bounds, *, lit: frozenset[str] = frozenset(), obj: str = "")`: use the `lit` argument where it called `self.lit_district_keys()`.
- Delete `KnowledgeSnapshot.lit_district_keys` and `_lit_district_keys_for_record`.
- Module function `revealed_in_bounds(character, bounds)`: after the snapshot is read, `from world.rules.map_district_lighting import readable_lit_district_keys` (inside the function) and call `snapshot.revealed_in_bounds(bounds, lit=readable_lit_district_keys(character), obj=str(character))`. The early returns for a missing or unreadable knowledge record stay as they are: a character who completed a rite stood on the landmark, so a knowledge record exists. Update the docstrings: lit ownership now means a completed rite.

### D3. Consumers

- `world/rules/sight.py`, `world/rules/travel_events.py`, `world/rules/travel_interrupts.py`: import and call `readable_lit_district_keys` in place of `lit_district_keys`. In `travel_interrupts.py` update the docstring sentence about a corrupt knowledge record raising.
- `web/webclient/presentation/area_map.py`: replace `_lit_landmarks(visited)` with `_lit_landmarks(lit: frozenset[str])` returning `{key: node_id for key, node_id in landmark_node_ids(registry).items() if key in lit}`; in the wilderness layer compute `lit = readable_lit_district_keys(actor)` once, pass it to `snapshot.revealed_in_bounds(bounds, lit=lit, obj=str(actor))` and to `_lit_landmarks`. Keep the surrounding `try`/`PanelUnavailableError` structure. `gate_visited` stays for the gateway disclosure it also serves.
- `web/webclient/presentation/world_map.py`: `assemble_world_map(*, visit_ids, current, markers, lit)` takes the lit set as a required keyword argument and no longer derives it; `world_map_presenter` computes `lit = readable_lit_district_keys(actor)` and passes it to both `quest_markers` and `assemble_world_map`.
- `tools/world_map_payload.py`: pass an explicit `lit` (the full set of district keys, since the tool builds the fully explored payload) instead of relying on visited landmarks.
- `web/webclient/presentation/rite.py`: `district.lit` uses `readable_lit_district_keys(owner)`; drop the `KnowledgeError` handling there.

### D4. Movement narrative

`world/rules/map_discovery.py` `publish_traversal_narrative`: remove the discovery computation, the `已探明` suffix and the `map_district_discovered` log. The function still sends `你移動到了<room>。` on commit and keeps its signature. `visited_before_traversal` and `persisted_visits` stay (the world map uses `persisted_visits`).

### D5. Documentation

- `docs/development/map-panel-protocol.md` and `docs/development/continental-geography.md`: where they say a district is lit by visiting its landmark, or that `已探明：<district>` follows a first arrival, state that the lit set comes from the completed-rite record and that a movement announces nothing.

### D6. Tests

Rewrite the lighting fixtures; do not delete coverage. Add the test helper `complete_rite_record(owner, district_key)` in `world/rules/tests/rite_fixtures.py` (or the shared fixture module `landmark-rite-action` created there), which calls `write_record(owner, with_completion(read_record(owner), district_key, "t", 0))`.

- `world/rules/tests/test_map_district_lighting.py`: the lit set equals the completed keys the registry declares; a completed key the registry does not declare is not lit; a visited landmark with no completed rite lights nothing; reading writes nothing and creates no attribute; a corrupt record raises from `lit_district_keys` and yields an empty set and one warning from `readable_lit_district_keys`.
- `world/rules/tests/test_ground_reveal.py`: `KnowledgeSnapshot.revealed_in_bounds` with an injected lit set equals the independently computed union of discs and the lit district's cells; with an empty lit set a visited landmark reveals only its disc; the character-level function passes the record-derived set (one completed rite reveals that district's cells beyond the disc).
- `typeclasses/tests/test_map_discovery.py`: a first landmark traversal emits one movement line and no second line, logs no `map_district_discovered` event, and leaves the district unlit; the failed-movement cases keep asserting no announcement.
- `world/rules/tests/test_landmark_rites.py`: after a first committed rite `lit_district_keys(owner)` contains the district; a refused or rolled-back rite lights nothing.
- `web/webclient/presentation/tests/test_world_map.py` and `test_world_map_measurement.py`: pass `lit` explicitly to `assemble_world_map`; a visited landmark with an empty `lit` yields an unlit district row; update the custom checker object in `test_world_map.py` that calls it.
- `web/webclient/presentation/tests/test_area_map/_wilderness_fixture.py` and `test_wilderness_content.py`: light the fixture district with `complete_rite_record` instead of a landmark visit.
- `web/webclient/presentation/tests/test_rite_panel.py`: the lit flag follows a completed rite, not a patched visit read.
- Inventory of the rest: `grep -rln "landmark_node_ids\|record_arrival\|record_visit\|assemble_world_map\|lit_district" --include=*.py world web typeclasses tests commands tools`. For each listed test module, run it; convert every fixture that expected a visit to light a district. Expected modules include `world.rules.tests.test_travel_plan`, `world.rules.tests.test_travel_events`, `world.rules.tests.test_travel_interrupts`, `web.webclient.actions.tests.test_travel_actions`, `world.maps.tests.test_static_map_references`, `world.lore.tests.test_map_district_content`, `tests.test_map_client_contracts`.

## Risks / Trade-offs

- Map progress becomes slower by design: a district needs a deliberate act at its landmark.
- A corrupt rite record leaves that character with no lit district until the GM repairs it; visits and discs still reveal.
- Many tests light districts by visits today, some without naming any lighting symbol. The inventory grep is deliberately broad; a missed fixture fails loudly because the visit no longer lights.
