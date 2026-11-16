# Design

## Context

Facts below were checked on master at e076e764, before `subrace-start-settlements`
was applied.

- `sync_grid()` (`world/maps/bootstrap.py`) creates one forward exit from 虛境 for each
  `CITY_GATE_REGISTRY` row, using `_ensure_exit`, and then deletes every exit whose
  destination is 虛境 (`_prune_exits_into`). The registry is
  `PublishedView("city_gates")` (`world/maps/city_gates.py`). The view is composed in
  `world/maps/map_data.py::_compose_document` / `compose_settlements` from the document's
  `city_gate` block. Four documents fill it in today (`capital_altoria`,
  `elven_village_ciaran`, `elven_village_eolas`, `elven_village_fionnen`); the other
  334 have an empty key.
- `world/rules/city_gates.py::reanchor_home_on_gate_arrival` is called from
  `typeclasses/exits.py::after_successful_movement` and from
  `world/rules/movement_settlement.py::settle_relocation`. `_compensate_home` (in
  `movement_settlement.py`, called from `_compensate`) exists only because that
  re-anchor could write `home` during a settlement.
- `world/maps/static_references.py` validates `city_gates` as a family, and includes it
  in `StaticWorld.fingerprint` and `binding_signature()`.
- Many test fixtures find "a materialized city room at a gateway face" by taking
  `CITY_GATE_REGISTRY[sorted(registry)[0]].gate`. That is the capital's `south_gate`.
  The sorted-first `WILDERNESS_ENTRY_REGISTRY` entry is also the capital, and its first
  authored gate (`return_direction: n`) also targets `south_gate`. The synthetic kit
  already relies on that entry for its second borrowed ref
  (`world/tests/synthetic_data/vocab.py::_shipped_second_wilderness_gate_ref`).
- `subrace-start-settlements` (a dependency) sets `home` at activation, so the
  re-anchor guard `home == 虛境` is never true for a player character.

## Goals / Non-Goals

Goals: 虛境 owns no exits. No game code reads the `city_gate` block. The re-anchor and
its rollback step are gone. Every fixture that used the gate registry as a node probe
uses one shared probe that resolves to the same node today.

Non-goals:
- No change to the map-core schema, the map editor, the settlement synthesis tools or
  the settlement YAML. Those belong to `drop-settlement-city-gate-field`. The
  `city_gate` key still parses and is still checked by the authoring validator
  (`packages/map-core/elosern_map_core/authoring.py`) until then.
- No change to `LimboRoom`, `LIMBO_KEY`, `LIMBO_DESC` or `sync_limbo`'s identity
  convergence. The room still holds creation-pending shells.
- No change to `DEFAULT_HOME`. Instance reclamation still sends unowned non-character
  occupants there. `LimboRoom` refuses only characters.

## Decisions

### D1. 虛境 owns no exits; `sync_limbo` converges that

Remove the whole Limbo block from `sync_grid()`: the `find_starting_rooms(LIMBO_KEY)`
lookup, the `bootstrap_grid_limbo_room_missing` warning, the registry loop and the
`_prune_exits_into` call. Delete `_ensure_exit` (its only caller is that loop; check
with `rg "_ensure_exit\(" world`) and `_prune_exits_into`. Update the `sync_grid`
docstring. Remove the `CITY_GATE_REGISTRY` and `settlement_node_xyz` imports if nothing
else uses them.

Add to the end of `sync_limbo()`, after the typeclass convergence:

```python
    _prune_limbo_exits(room)
```

```python
def _prune_limbo_exits(limbo) -> None:
    """Delete every persisted exit located in or leading into ``limbo``.

    虛境 is a backstage holding room for creation-pending shells
    (retire-limbo-city-gates D1): it owns no exits, and no exit leads into it.
    The query runs at the unscoped ``ObjectDB`` level so every Exit subclass is
    caught; the ``isinstance`` gate leaves non-exit objects untouched. On a
    converged database this deletes and logs nothing.
    """

    for side, rows in (
        ("location", ObjectDB.objects.filter(db_location=limbo.id)),
        ("destination", ObjectDB.objects.filter(db_destination=limbo.id)),
    ):
        for exit_obj in rows:
            if not isinstance(exit_obj, Exit):
                continue
            log_info(
                "bootstrap_limbo_exit_pruned",
                context={
                    "exit_key": exit_obj.key,
                    "exit_dbref": exit_obj.dbref,
                    "side": side,
                    "action": "limbo_owns_no_exits",
                },
            )
            exit_obj.delete()
```

An exit that is both in 虛境 and leads into it is deleted on the first pass. The second
query runs after that delete, so it cannot return the exit again. The `sync_limbo`
docstring gets one sentence about this.

Why `sync_limbo` and not `sync_grid`? This is a property of the room, it holds even
when no settlement is selected, and `sync_limbo` already runs on every start before
`sync_grid`.

### D2. Delete the gate view and its composition

- Delete `world/maps/city_gates.py`.
- `world/maps/map_data.py`: remove the `CityGateDef` import, the
  `SettlementSnapshot.city_gates` field and its docstring mention, the `city_gate` part
  of `_compose_document` (lines that build `CityGateDef`; the function then returns five
  values), the `city_gates` dict in `compose_settlements`, and the keyword in the
  `SettlementSnapshot(...)` call. Do not add any check of `document.city_gate`. The
  map-core authoring validator still covers it.
- `world/maps/static_references.py`: remove the `city_gates` field from `StaticWorld`,
  its fingerprint part, its problems loop, its two constructor keywords, its
  `binding_signature()` part and import, and the "city gates" words in the docstrings.
- Run `rg -n "city_gates|CITY_GATE|CityGateDef" world web server typeclasses commands`.
  After this change the only hits may be in `world/maps/tests/test_village_ciaran.py`
  document assertions (see D5).

### D3. Delete the re-anchor and its rollback step

- Delete `world/rules/city_gates.py`.
- `typeclasses/exits.py::after_successful_movement`: remove the import and call, and the
  docstring paragraph that starts "The tail additionally runs the one-way-gate home re-anchor".
- `world/rules/movement_settlement.py`: in `settle_relocation`, remove the import and
  the `reanchor_home_on_gate_arrival(entity, destination)` call, and "re-homes a gate
  arrival" from the docstring. Delete `_compensate_home` and its call in `_compensate`.
  Nothing else in the codebase writes `home` inside a movement settlement; confirm with
  `rg -n "\.home\s*=" world/rules typeclasses`.

### D4. One shared node probe for fixtures

Add to `world/tests/geography_fixture.py`:

```python
def entrance_refs(count: int) -> tuple:
    """First gate destinations of the ``count`` sorted-first wilderness entries.

    The node probe for fixtures that need materialized settlement rooms at a
    wilderness gateway face. It names no shipped key: the registry is looked up
    by attribute string, the same idiom ``synthetic_data.vocab`` uses. Every
    wilderness entry comes from a settlement document, so each ref lies on a
    distinct settlement map.
    """

    import importlib

    module = importlib.import_module(".".join(("world", "lore", "wilderness_entry")))
    registry = getattr(module, "WILDERNESS" + "_ENTRY_REGISTRY")
    return tuple(registry[key].gates[0].destination for key in sorted(registry)[:count])


def first_entrance_ref():
    """The first gate destination of the sorted-first wilderness entry."""

    return entrance_refs(1)[0]
```

Call sites:
- An expression `registry[sorted(registry)[0]].gate`, where `registry` is the gate
  registry, becomes `first_entrance_ref()`.
- `web/webclient/presentation/tests/test_local_map/_support.py::_city_gate_row_for(gate)`
  is deleted. Its users take `gate.destination` directly. For `_NORTH_FACE` that is the
  same node, because the helper asserted that the row stood at `_NORTH_FACE`'s room.
  Users in `test_gateway_resolution.py` that read `.gate` from the row now use
  `_NORTH_FACE.destination`.
- `world/rules/tests/test_map_knowledge_integration/_support.py`: replace
  `self.gate_row = live_city_gate_registry()[self.map]` and its use with the map's own
  entry gate whose `return_direction == "n"`. Find the entry with
  `_entry_with_west_gate_on(self.map)` (already in that file) and take
  `entry.gate_for("n").destination`. Delete `live_city_gate_registry` from
  `world/rules/tests/_knowledge_probes.py` and from its `__all__`.
- `world/tests/synthetic_data/vocab.py::_shipped_first_gate_ref` reads the wilderness
  registry in the same way (same body as `first_entrance_ref`, kept local, because the
  kit must not import test fixtures). Its docstring says it borrows the first entry
  gate.
- `world/tests/synthetic_data`: delete `SYNTH_CITY_GATES`, `make_city_gate`, the
  `city_gates` content row in `targets.py`, the `SETTLEMENT_TARGETS["city_gates"]` row
  and the `CityGateDef` imports and exports in `data_world.py`, `factories.py`,
  `__init__.py` and `targets.py`.
- `world/maps/tests/_bootstrap_fixtures.py`: rename `CITY_GATE_MAP_IDS` to `PROBE_MAP_IDS`
  and set it to `(first_entrance_ref().map_id,)`. Update the other gate helpers there,
  and every importer in `world/maps/tests/test_bootstrap/*`, to the new name.
- `web/tests/browser/fixtures.py::journey_settlement_scope`: the base set becomes
  `{ref.map_id for ref in entrance_refs(2)}`. Today that is the capital and the
  second-sorted settlement, which replaces the gate maps. `second_map_xyz()` below needs
  a second materialized map. Keep the creation-only union that
  `subrace-start-settlements` added, and rewrite the docstring to match.
- `web/tests/browser/incremental_sync_fixture.py`: `_gate_registry` and
  `gate_positions` become `entrance_positions()`. It returns
  `(f"entrance{index}", x, y, map_id)` for each ref of `entrance_refs(2)`, with the
  coordinate from `settlement_node_xyz(ref)`. `first_gate_xyz` and `second_map_xyz`
  read it, and their names stay the same.
- `web/tests/browser/seed/minimap_fixture.py`, `seed/exploration_fixture.py` and
  `web/tests/browser/browser_helpers.py`: replace the sorted-first gate-row expression
  with `first_entrance_ref()`. Fix the comments that call it "the city-gate row".

### D5. Tests that asserted gate behavior

- Delete these outright: tests of forward exits, gate-row convergence, missing-gate
  warnings, registry growth, the re-anchor and `city_gate_home_reanchored` (in
  `world/maps/tests/test_bootstrap_sync.py`, `test_bootstrap/test_bootstrap_grid.py`,
  `test_bootstrap/test_bootstrap_selection.py`, `test_limbo_room.py`, `test_gm.py`'s two
  re-anchor fault-injection tests, and `test_settlement_sources.py:146`). Remove the
  `city_gate:` keys from the inline synthetic YAML only if the parser would reject them.
  It will not until `drop-settlement-city-gate-field`, so leave inline YAML alone.
- `test_gm.py`: the two tests inject a failure through the re-anchor patch target.
  Retarget the patch to `world.rules.dialogue.clear_dialogue_session`. `settle_relocation`
  imports it function-locally and calls it right after the old re-anchor point, after
  companions arrive. Make sure the test moves between two different rooms, so that the
  call actually happens. Keep the
  assertions.
- `world/maps/tests/test_village_ciaran.py::test_the_declared_entrance_is_the_city_gate_registry_slot`:
  delete it. Assertions on `self.document.city_gate` stay until the next change.
- `world/rules/tests/test_met_people.py:115`: drop the `city_gates=` keyword.
- `world/maps/tests/_editor_adoption_fixtures.py`: drop the `static.city_gates` loop.
- New tests in `world/maps/tests/test_limbo_room.py`, one per scenario of "sync_limbo
  removes every exit that touches 虛境": a forward exit and a reverse exit are pruned
  (assert the `bootstrap_limbo_exit_pruned` event by patching
  `world.maps.bootstrap.log_info`), a second run is idempotent, and a non-exit object with
  `destination` set to 虛境 survives. In `test_bootstrap_sync.py`, one test runs
  `sync_grid(settlement_ids=(first_entrance_ref().map_id,))` with a 虛境 room present and
  asserts that no exit is located in or leads into it. In
  `world/maps/tests/test_sample_city*.py`, or whichever module covers
  `sample-city-altoria` (find it with
  `rg -l "sample-city-altoria::" world`), annotate the existing wilderness-gate-exits
  test with the new requirement ID and add the "no city room is joined to 虛境" assertion.

### D6. Specs and docs

- Main spec Purpose lines mention the bridge. Edit them directly during apply, because
  a delta cannot carry a Purpose for an existing capability:
  `openspec/specs/limbo-one-way-gates/spec.md` ("Define 虛境 as a backstage holding room
  that admits no character and owns no exit."), `limbo-room` (drop "and the zh-tw bridge
  exit surface to the capital"), `grid-room-sync` (drop "plus the Limbo-bridging exit
  pair"), `sample-city-altoria` (replace "and one forward bridge from Limbo per
  city-gate registry row" with "and its wilderness gates as the only way out").
- Docs: in `docs/development/evennia-testing-guide.md`, `docs/development/metric-settlements.md`
  and `docs/lore/settlement-locations.md`, remove sentences saying that 虛境 bridges to
  gates or that a gate re-homes a character. Prepend a one-line note to
  `docs/superpowers/specs/2026-09-04-onboarding-removal-one-way-limbo-design.md`:
  "Superseded in part by subrace-start-settlements and retire-limbo-city-gates: 虛境 has
  no gates; characters start in their subrace's settlement."
- `world/maps/AGENTS.md`: the row "City gates, Limbo, room art | city_gates.py, limbo.py,
  room_art.py" becomes "Limbo, room art | limbo.py, room_art.py". `world/rules/AGENTS.md`:
  remove `city_gates.py` from the movement row.
- `content/map-reference-context.json`: regenerate with
  `uv run --locked python -m tools.map_reference_context` if the generator reads the game
  gate view. If the file does not change, commit nothing.

## Risks / Trade-offs

- [A fixture probe changes node and shifts browser expectations.] The probe resolves to
  the same node today (see Context). Task 5.3 runs the affected browser classes.
- [A developer database keeps characters whose `home` is 虛境.] Accepted. There are no
  released users, and AGENTS.md forbids migrations. Such characters would be refused by
  `LimboRoom` on `home`. Recreate the database.
- [`city_gate` stays in the schema with no consumer between this change and the next.]
  Accepted for one batch step. It is dead data, not a compatibility path.
