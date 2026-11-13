# Design

## Context

Three classes derive the same property from the mask alone:

| Class | File |
| --- | --- |
| `WildernessEntryDeclaration` | `packages/map-core/elosern_map_core/documents.py` |
| `WildernessEntryGeometry` | `packages/map-core/elosern_map_core/documents.py` |
| `WildernessEntryPoint` | `world/lore/wilderness_entry.py` |

Each has `is_point_shape`, defined as `hash_cell_count == 1`, and `footprint_cells`, which is empty for a point shape. Every consumer branches on those two properties:

- map-core diagnostics (`authoring.py`): a point shape allows exactly one gate (`point_gate_count`) and uses the anchor cell as its approach;
- `gate_approach_cell` and `WildernessEntryPoint.approach_cell`: a point shape returns the anchor, a footprint walks out of the mask opposite the gate's return direction;
- the runtime gateway match (`world/maps/wilderness_destination.py`, `world/maps/wilderness_provider.py`);
- the partition and the road generator, which treat `footprint_cells` as obstacles;
- `world/maps/population_geometry.py`, `world/rules/sight.py` and `tools/settlement_synthesis/fit_lint.py`.

So the only thing missing is a way to say that a one-`#` mask is a footprint.

## Goals / Non-Goals

**Goals:**

- A one-cell settlement with several gates, each entered from the neighbouring cell.
- Existing documents behave exactly as before.

**Non-Goals:**

- No shipped document gains the field.
- No change to the settlement generator, the size budget or the road generator. `single-cell-settlement-layout` and `road-spur-stage` own those.
- No map editor control for the field. The editor edits a parsed document in place, so the field survives its commands; setting it is a hand edit.
- No change to any consumer listed in Context beyond the three classes.

## Decisions

### D1. An explicit optional field, default false

Schema, in `_WILDERNESS_ENTRY` of `schema.py`:

```python
        "single_cell_footprint": _bool(required=False),
```

YAML:

```yaml
wilderness_entry:
  shape:
    - '#'
  offset: {dx: 0, dy: 0}
  single_cell_footprint: true
  gates:
    - return_direction: e
      destination_node: west_end
    - return_direction: w
      destination_node: east_end
```

Alternatives considered:

- Derive the meaning from the location kind. Rejected: the entry classes do not know the kind, and the partition and the road generator read footprints with no location join.
- Derive it from the gate count. Rejected: a one-gate hamlet at the end of a lane would silently become a concealed entry.
- Allow several gates on a point shape. Rejected: a point gate is taken by standing on the cell and stepping in the gate direction, so a road passing through the cell would be captured by the gate and could never be followed.

### D2. One property changes in three classes

Each class gains a field `single_cell_footprint: bool = False`, placed last so positional construction keeps working, and:

```python
    @property
    def is_point_shape(self) -> bool:
        return self.hash_cell_count == 1 and not self.single_cell_footprint
```

`footprint_cells` and `mask_cells` are unchanged in code: for a flagged one-`#` mask `is_point_shape` is false, so `footprint_cells` returns the one cell.

Plumbing:

- `SettlementDocument.__post_init__` passes `single_cell_footprint=bool(entry_data.get("single_cell_footprint", False))`.
- `WildernessEntryDeclaration.geometry` passes the field to `WildernessEntryGeometry`.
- `world/maps/map_data.py` passes `single_cell_footprint=entry.single_cell_footprint` when it builds `WildernessEntryPoint`.

### D3. The field on any other mask is a semantic diagnostic

In `diagnose_settlement_semantics`, a settlement whose entry has `single_cell_footprint` true and `hash_cell_count != 1` gets one diagnostic: code `single_cell_footprint_mask`, category semantic, field path `wilderness_entry.single_cell_footprint`, message naming the settlement and the `#` count. The field has no effect on such a mask, because `is_point_shape` is already false.

It is semantic, not structural, so growing a flagged mask in the map editor stays saveable work in progress instead of an unloadable world.

### D4. Tests

All inputs are synthetic.

| Test | File | Scenario established |
| --- | --- | --- |
| A flagged one-`#` entry with two gates loads with no `point_gate_count`; its `footprint_cells` is the one cell; `gate_approach_cell` for return direction `e` is the west neighbour and for `ne` is the south-west neighbour | `packages/map-core/tests/test_authoring.py` | map-settlement-sources "Flagged one-cell mask" |
| The same mask without the field keeps `point_gate_count` for two gates and an empty `footprint_cells` | same | "Unflagged mask is unchanged" |
| A flagged two-`#` mask yields `single_cell_footprint_mask` and its geometry equals the unflagged one | same | "Field on another mask" |
| A document with `single_cell_footprint: "yes"` is rejected by schema validation | same | "Field type" |
| `WildernessEntryPoint` built with the flag: `approach_cell` of each gate is the neighbour cell, and `footprint_cells` holds the anchor | `world/lore/tests/test_wilderness_entry.py` | wilderness-gateway "Approach cells" |
| `find_gateway` matches at an approach cell with the gate's return direction, and matches nothing at the footprint cell itself or at the approach cell in another direction | `world/maps/tests/test_wilderness_destination.py` | wilderness-gateway "Gateway match" |
| The lint reports a node outside a flagged one-cell footprint and an unwalkable approach, and still skips both for an unflagged one-`#` entry | `tests/test_settlement_terrain_fit.py` | settlement-terrain-fit "One-cell physical footprint" |

`fit_lint.py` needs no code change: it sets `multi_cell = bool(footprint)`, which becomes true for a flagged cell.

Do not add `covers_requirement` to tests of ADDED requirements; list them in the hand-off (`docs/development/spec-test-traceability.md`). The lint requirement is MODIFIED and keeps its identifier.

### D5. Documentation

- `.agents/skills/map-data-authoring/references/settlements.md`, section "Wilderness entry (footprint and gates)": add a bullet "One-cell footprint" after "Point shape", with the YAML of D1 and the sentence that the cell is an obstacle and each gate is taken from the neighbouring approach cell.
- `docs/development/map-authoring-documents.md`: add `single_cell_footprint` to the settlement entry fields.

## Risks / Trade-offs

- [A consumer recomputes the point shape from the mask instead of the property] → `grep -rnE "hash_cell_count|count\(\"#\"\)" --include='*.py' world web typeclasses tools packages` at design time shows `hash_cell_count` used for the point decision only inside the three classes; `world/rules/sight.py` reads it as an occupied-cell count, where 1 is correct for a flagged cell.
- [A flagged cell on a trunk road makes the road generator route around it] → Intended until `road-spur-stage` lands; that change makes village and hamlet cells open to roads. No shipped document is flagged before then.
