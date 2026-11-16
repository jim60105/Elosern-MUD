# Design

## Context

- Fixtures probe `CITY_GATE_REGISTRY[sorted(registry)[0]].gate`. That is the capital's
  `south_gate` node.
- The sorted-first `WILDERNESS_ENTRY_REGISTRY` key is the same settlement. Its first
  authored gate (`return_direction: n`) targets `south_gate`. Checked on e076e764 in
  `content/maps/settlements/capital_altoria.yaml`. The kit's second borrowed ref
  (`world/tests/synthetic_data/vocab.py::_shipped_second_wilderness_gate_ref`) already
  reads that entry.
- `web/webclient/presentation/tests/test_local_map/_support.py::_city_gate_row_for(gate)`
  returns the unique gate row standing at `gate.destination`'s room, and raises
  otherwise. Its users only read `.gate` (and `.gate.map_id`), which is that same node.

## Goals / Non-Goals

Goal: every single-node probe of the gate registry resolves through the wilderness entry
instead, with no assertion change.

Non-goals:
- Fixtures that read `exit_key` or `exit_aliases` (`world/rules/tests/test_map_knowledge_integration/test_recording.py`).
- Fixtures that use the set of gate maps (`world/maps/tests/_bootstrap_fixtures.py`,
  `web/tests/browser/fixtures.py::journey_settlement_scope`,
  `web/tests/browser/incremental_sync_fixture.py`).
- The synthetic `SYNTH_CITY_GATES` row.
- `world/maps/tests/test_limbo_room.py`.

All of these belong to `retire-limbo-city-gates`.

## Decisions

### D1. Helpers

Add to `world/tests/geography_fixture.py`:

```python
def entrance_refs(count: int) -> tuple:
    """First gate destinations of the ``count`` sorted-first wilderness entries.

    The node probe for fixtures that need materialized settlement rooms at a
    wilderness gateway face. It names no shipped key: the registry is looked up
    by attribute string, the same idiom ``synthetic_data.vocab`` uses. Every
    wilderness entry comes from a settlement document, so each ref lies on a
    distinct settlement map. Like every helper here, it publishes the shipped
    map world first when nothing is published yet.
    """

    import importlib

    publish_shipped_map_world()
    module = importlib.import_module(".".join(("world", "lore", "wilderness_entry")))
    registry = getattr(module, "WILDERNESS" + "_ENTRY_REGISTRY")
    return tuple(registry[key].gates[0].destination for key in sorted(registry)[:count])


def first_entrance_ref():
    """The first gate destination of the sorted-first wilderness entry."""

    return entrance_refs(1)[0]
```

The publish call is needed because the old probe failed in modules that read it
before anything published the map world (`test_node_ids` raised
`SettlementNotLoaded` when run alone on 5db8d4d4). It is idempotent, so callers that
already publish are unaffected.

### D2. Call sites

- `commands/tests/test_localized/test_xyz_grid_and_help.py`: delete `_gate_row()`.
  Replace `_gate_row().gate` with `first_entrance_ref()` (two uses).
- `web/webclient/actions/tests/test_node_ids.py::_south_gate_xyz`: its body becomes
  `return settlement_node_xyz(first_entrance_ref())`, and the docstring says it is the
  first wilderness entrance.
- `web/webclient/actions/tests/test_exploration_actions/test_move_and_look.py` (near
  line 327) and `web/webclient/presentation/tests/test_affordances/test_vocabulary.py`
  (near line 110): replace the inline registry lookup with `first_entrance_ref()`.
- `web/webclient/presentation/tests/test_local_map/_support.py`: delete
  `_city_gate_row_for`. `SOUTH_GATE_XYZ` uses `_NORTH_FACE.destination`, and
  `_T_PLAZA_XYZ` keys the placement by `_NORTH_FACE.destination.map_id`. In
  `test_gateway_resolution.py`, drop the `_city_gate_row_for` import. `gate_row.gate`
  (line 43) and `_city_gate_row_for(_NORTH_FACE).gate` (line 115) become
  `_NORTH_FACE.destination`. Line 43 may read `gate_row` only for its node; if it reads
  anything else, stop and leave that test to `retire-limbo-city-gates`.
- `world/rules/tests/test_map_knowledge_integration/_support.py`: compute
  `self.south_gate_xyz = settlement_node_xyz(entry.gate_for("n").destination)`, using
  the `entry` already returned by `_entry_with_west_gate_on(self.map)` (move that call
  above this line). Keep `self.gate_row`, because `test_recording.py` still reads its
  labels.
- `world/tests/synthetic_data/vocab.py::_shipped_first_gate_ref`: the body reads
  `WILDERNESS_ENTRY_REGISTRY` by attribute string and returns
  `registry[sorted(registry)[0]].gates[0].destination`. Update the docstring.
- `web/tests/browser/browser_helpers.py` (near line 40),
  `web/tests/browser/seed/minimap_fixture.py` (near line 44) and
  `web/tests/browser/seed/exploration_fixture.py` (near line 159): replace the
  sorted-first gate-row expression with `first_entrance_ref()`, imported inside the
  function from `world.tests.geography_fixture`. Fix the comments.

## Risks / Trade-offs

- [The two probes diverge if the capital's gate order or the sorted key set changes.]
  The equality holds on e076e764. Task 1.1 checks it right before the edit and stops if
  it fails.
