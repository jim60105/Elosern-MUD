# Design

## Context

See proposal.md (Why). This change builds on `settlement-terrain-fit` and `settlement-graph-generator`, both landed. They provide `generate_settlement`, `GenerationInput`, `GenerationResult.slots` (whose `role` values are `anchor`, `crossing`, `gate`, `approach`, `filler` or a catalogue slot id), `WorkspaceView`, `blocked_cells`, `write_atomic`, `settlement_path`, `lint_settlement` and the CLI.

Where references live:

- `InteriorDocument.exterior` has `.settlement` and `.node`, read from `world.interiors[*]`.
- A district landmark is `world.districts.districts[*].landmark`, a `QualifiedRef` with `.domain`, `.map_id` and `.object_id`. The settlement-node domain is the literal `"settlement_node"`.
- `content/map-reference-context.json` has an `incoming_references` object keyed by qualified id strings. A settlement node key has the form `settlement_node:<map_id>:<node_id>`. The file may be absent. Today it has no settlement-node keys, but the rule must still apply.
- The settlement's own `city_gate.node`, and its anchor node (`document.anchor_node.node_id`).

## Goals / Non-Goals

**Goals:**
- a deterministic replace that never loses a referenced id;
- a brief and prose apply that touch only `key` and `desc`.

**Non-Goals:**
- writing the prose itself. That is an agent task inside the batch changes.
- changing interiors, districts or Python lore;
- bends.

## Decisions

### D1. Bind file and resolution (`rework.py`)

```python
@dataclass(frozen=True)
class ReworkPlan:
    data: Mapping[str, Any]          # final settlement document data
    bound: Mapping[str, str]         # existing_id -> slot_id (resolved)
    dropped: tuple[str, ...]         # sorted existing ids removed
    renamed_slots: Mapping[str, str] # generated slot id -> suffixed id
    warnings: tuple[str, ...]

class ReworkError(ValueError):
    def __init__(self, problems: Sequence[str]): ...   # message lists every problem, one per line

def protected_nodes(view: WorkspaceView, map_id: str) -> tuple[frozenset[str], bool]:
    """(protected ids, index_present). Missing index -> every existing node id, False."""

def apply_bindings(existing: SettlementDocument, result: GenerationResult,
                   bindings: Sequence[tuple[str, str]], protected: frozenset[str]) -> ReworkPlan
```

The bind file is JSON of the form `{"bindings": {"<existing_id>": "<slot_id>" | "nearest:<slot_id>", ...}}`. Read it with `json.load`, which keeps the file order, and pass `list(obj["bindings"].items())`.

`apply_bindings` collects every problem first and then raises one `ReworkError`. The checks run in this order:

1. **Unknown existing id.** Problem `unknown_node:<id>`.
2. **Direct binding.** The slot id must exist in `result.slots`, otherwise `unknown_slot:<id>->...`, and it must not already be bound, otherwise `duplicate_slot:<slot>`.
3. **Nearest binding** `nearest:<ref>`. The reference slot must exist. The candidates are slots with `role in {"approach", "filler"}` that are not yet bound. Pick the one with the smallest Euclidean `rel_m` distance to the reference slot, breaking ties by plan order. With no candidate, report `no_nearest:<id>`.
4. **Anchor.** If the existing anchor id is bound to a slot other than `central_plaza`, report `anchor_mismatch:<slot>`.
5. **Unbound protected ids.** For each protected id without a binding, report `unbound_protected:<id>`, sorted.

After all checks pass, the final ids are built:

- Each bound slot takes its existing id.
- Each unbound slot keeps its generated id. If that id collides with any final id, it becomes `<id>_<n>` for the first `n = 2, 3, …` that is free, recorded in `renamed_slots`.
- Rename consistently in the node keys, every road's `source` and `destination`, and every gate's `destination_node`.
- Bound nodes copy the existing node's `key`, `desc`, `typeclass` and `scene_archetype`. Position and `prototype_parent` come from the plan.
- `dropped` is the set of existing ids left unbound. With a current index these ids are unprotected.
- `options`, `exit_prototype` and `city_gate` come from the existing document. `city_gate.node` is an existing id and is necessarily bound, because the city gate is protected.
- The node and road order is the plan order.

### D2. CLI additions (`__main__.py`)

```
generate LOCATION_ID --replace --bind FILE [--gates OCTANT[,OCTANT...]] [--root DIR] [--lore FILE] [--plan-only]
brief MAP_ID [--root DIR] [--lore FILE]
prose MAP_ID FILE [--root DIR]
```

- **`--replace`.**
  - It requires `--bind` and an existing `settlement_path`.
  - `blocked_cells(map_id)` already excludes the map's own document.
  - Generate as usual, call `protected_nodes`, then `apply_bindings`.
  - Validate the result with `document_from_data` and `lint_settlement`, which must report no error.
  - Print a report: the generator report plus `bound`, `dropped`, `renamed_slots` and `index_present`.
  - `--plan-only` prints and writes nothing. Without it, write with `write_atomic(path, serialize_document(document, parsed.round_trip))`, where `parsed = parse_document(rel_path, old_text)`. That keeps the file's header comments.
  - `ReworkError` exits 1. `--replace` without an existing file exits 1 with `missing: <path>`.
- **`brief`.** The output is JSON:

  ```json
  {"map_id", "location_id", "display_name_zh", "kind", "nation", "population", "geographic_constraint",
   "settlement_class", "morphology",
   "water": [{"kind", "name", "bearing", "distance_cells"}],
   "uphill",
   "neighbours": [{"id", "display_name_zh", "bearing", "distance_cells"}],
   "nodes": [{"id", "key", "role", "bearing", "distance_m", "desc_empty", "gate_return_direction"}]}
  ```

  - `role` comes from `role_of(node_id, document)`:
    - `"anchor"` for the anchor node;
    - `"gate"` for a wilderness gate destination node;
    - a catalogue `slot_id` when the id equals one, or when it starts with that slot id followed by `_<digits>`;
    - `"approach"` for ids matching `^[a-z]+_gate_road_\d+$`;
    - `"crossing"` for `ford_crossing`;
    - `"filler"` for ids matching `^lane_\d+$`;
    - `"authored"` otherwise.
  - `bearing` and `distance_m` are measured from the anchor in local metres. The anchor itself has bearing `null` and distance `0`.
  - `settlement_class` and `morphology` are recomputed with the generator's D3 functions. `water` lists the site rivers and the sea within reach.
  - Nothing is written. Exit 2 on `WorkspaceError` or an unknown map.
- **`prose`.** The file holds JSON `{"<node_id>": {"key": str, "desc": str}}`.
  - Collect every problem: `unknown_node:<id>`, `empty_key:<id>` and `empty_desc:<id>` (after `.strip()`), plus `unexpected_field:<id>:<field>` for any field other than `key` and `desc`.
  - When any problem exists, exit 1 and write nothing.
  - Otherwise, set only `data["nodes"][id]["key"]` and `["desc"]` on a thawed copy of `parsed.document.data`. Then call `document_from_data` and `write_atomic(path, serialize_document(document, parsed.round_trip))`.
  - Exit 0 and print `prose: <n> nodes updated`.

### D3. Prose standard (`docs/development/settlement-synthesis.md` § Prose pass)

Agent writers follow these rules. They are human-reviewed, never tested.

- Write in Traditional Chinese for Taiwan readers, with full-width punctuation. Follow `.agents/skills/chinese-content-writing-guideline`. The setting is JRPG sword and magic. Never use 武俠 vocabulary.
- `key` is 2–8 characters and unique within the map. It names the place a traveller stands in, such as 南門, 河港碼頭 or 鐵砧巷. It does not repeat the settlement's name.
- `desc` is 1–3 sentences and 40–140 characters. It must include one concrete site cue taken from the brief, for example the river side, the uphill direction, the gate's road toward a named neighbour, or the market where approach roads meet. The settlement's `display_name_zh` may appear at most once.
- Write in-world only. Never mention a command, a game mechanic, a UI element, coordinates or an id.
- Follow the archetype's place matrix in `docs/lore/settlement-locations.md`:
  - a beast settlement has no academy, alchemist or church temple; it has a tribal hall and an ancestral altar;
  - only a port has a sea quay;
  - shops stay narrative mentions, because interiors are out of scope.
- For a bound node that already has prose, leave it untouched unless the brief shows that its site cue is now false. An example is a riverbank description on a node that moved away from the river. In that case rewrite only the false clause.

### D4. Tests (`tests/test_settlement_map_rework.py`)

- The tests use `unittest` and `synthetic_workspace.write_workspace(tmp)`. In that workspace:
  - `synthetic_town` (location `synthetic_place`, kind `capital`) has the anchor `gate`, the node `yard` and a city gate on `gate`;
  - the interior `synthetic_hall` names `yard` as its doorway;
  - the district landmark is also `yard`.
- Lore file: `{"synthetic_place": {"nation": null, "population": 200000}}`.
- The bindings are `{"gate": "central_plaza", "yard": "nearest:central_plaza"}`, with variants per scenario.
- The reference index is written with `synthetic_workspace.write_reference_context(tmp)`; one scenario uses no index at all.
- Each scenario compares `tree_digest` values.
- `prose` and `brief` run on the replaced map.

Requirement → test class mapping, decorated at archive:

| Requirement ID | Test class |
| --- | --- |
| `settlement-map-rework::replacing-a-settlement-preserves-every-referenced-node-identity` | `ReplaceTests` |
| `settlement-map-rework::nearest-bindings-resolve-deterministically` | `NearestBindingTests` |
| `settlement-map-rework::prose-briefs-and-prose-application-touch-only-names-and-descriptions` | `ProseTests` |

## Risks / Trade-offs

- [A worker binds a protected node to a slot with an unsuitable role, for example a shop street to a gate] → `altoria-capital-river-rework` gives the full binding table. The brief exposes roles for review.
- [`round_trip` merge keeps stale comments for dropped nodes] → `serialize_document`'s merge deletes keys that are absent from the new data. Header comments survive, which is the intent.
- [Prose drifts from reality after later hand edits] → `brief` reports `desc_empty`, and the human review checklist includes rereading every description whose site cue changed.

## Migration Plan

None. This change adds tooling only.
