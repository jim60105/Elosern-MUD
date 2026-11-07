# Design

## Context

See `proposal.md` for motivation. `docs/superpowers/specs/2026-11-07-official-roads-design.md` is the approved design. Its Units table places parameters in `content/maps/road_network.yaml` and encoding, decoding and freshness in `roads_codec.py`. This change is the shared base of `road-network-generation` and `road-network-runtime`.

## Goals / Non-Goals

**Goals:** the parameter document, the stdlib codec, the region speed reader.

**Non-Goals:** do not create `roads.py`, `tools/road_network.py`, `world/maps/road_network.py` or `world/maps/data/road_network.json`. Do not edit any file under `tools/map-editor/`.

## Decisions

### D1. New optional singleton document kind

`road_network` is a real source kind, so it joins the world fingerprint and editor file following by the existing rules.

- `sources.py`: add `"content/maps/road_network.yaml": ("road_network", "road_network")` to `FIXED_SOURCES`; update the module docstring.
- `authoring.py`: add `"road_network"` to `WORLD_SOURCE_KINDS`. Do **not** add it to the required loop `for kind in ("continent", "locations", "districts")`. Add `road_network: RoadNetworkDocument | None` to `AuthoringWorld` after `interiors`, and pass the parsed entry's `.document`, or `None` when no entry exists, into both constructors in `load_authoring_world`.
- Add `_road_network_diagnostics(road_network, continent)` returning one diagnostic per `forbidden_regions` entry missing from `continent.regions`: code `unknown_road_region`, category `STRUCTURE`, field path `forbidden_regions`. Extend `diagnostics` with it in the same statement group as `_structural_diagnostics(...)`, **before** the `if diagnostics: raise AuthoringError(...)` that follows.

Alternative rejected: a required document. It would edit every synthetic world in `authoring_fixtures.py`, `synthetic_workspace.py` and the top-level contract tests for a document those worlds never read. `docs/development/map-authoring-documents.md` says missing singletons fail the load, so that sentence is amended to name this exception.

Schema entry in `_DOCUMENT_KINDS`, `kind: road_network`, fixed id `road_network`:

| Field | Spec |
| --- | --- |
| `version` | `_int(constant=SCHEMA_VERSION)` |
| `kind` | `_enum(("road_network",))` |
| `id` | `_str(pattern=IDENTIFIER_PATTERN, constant="road_network")` |
| `node_kinds` | `_list(_enum(LOCATION_KINDS), min_items=1)` |
| `forbidden_regions` | `_list(_str(pattern=IDENTIFIER_PATTERN))` |
| `slope_factor_per_band` | `_number(min_value=0)` |
| `noise_amplitude` | `_number(min_value=0, max_value=0.9)` |
| `noise_wavelength_cells` | `_number(min_value=2)` |
| `noise_seed` | `_int(min_value=0)` |
| `detour_limit` | `_number(min_value=1)` |
| `reuse_factor` | `_number(min_value=0.01, max_value=1)` |

`documents.py`: `RoadNetworkDocument(AuthoringDocument)` follows `LocationsDocument`, exposing each field by the same name with lists as tuples and numbers as `float`. Register it in `DOCUMENT_CLASSES`.

Shipped `content/maps/road_network.yaml` initial values are unvalidated starting points, tuned later from the preview. No test pins them.

```yaml
version: 1
kind: road_network
id: road_network
node_kinds: [capital, city, port, town]
forbidden_regions: [north_deep_forest]
slope_factor_per_band: 0.15
noise_amplitude: 0.15
noise_wavelength_cells: 48
noise_seed: 20261107
detour_limit: 1.8
reuse_factor: 0.4
```

### D2. Codec contract

`packages/map-core/elosern_map_core/roads_codec.py` imports the standard library and `.sources` only.

```python
FORMAT_VERSION = 1
ROAD_ALGORITHM_VERSION = 1
ROAD_SOURCE_KINDS = frozenset({"continent", "locations", "settlement", "road_network"})

class RoadDocumentError(ValueError): ...

@dataclass(frozen=True, slots=True)
class RoadFreshness:
    algorithm_version: int
    input_signature: str
    current: bool

@dataclass(frozen=True, slots=True)
class RoadMetadata:
    format_version: int
    algorithm_version: int
    source_signature: str
    fingerprint: str

@dataclass(frozen=True, eq=False)
class RoadNetwork:
    fingerprint: str
    nodes: tuple[str, ...]
    roads: tuple[tuple[str, str, tuple[tuple[int, int], ...]], ...]  # sorted by (first, second)
    cells: frozenset[tuple[int, int]]

def road_source_signature(fingerprints: Mapping[str, str], *,
                          elevation_fingerprint: str,
                          region_speeds: Mapping[str, int]) -> str: ...
def road_freshness(metadata: RoadMetadata, source_signature: str | None,
                   algorithm_version: int = ROAD_ALGORITHM_VERSION) -> RoadFreshness: ...
def road_fingerprint(nodes: Sequence[str],
                     roads: Sequence[tuple[str, str, Sequence[tuple[int, int]]]]) -> str: ...
def encode_road_document(*, frame_cells: int, source_signature: str, nodes: Sequence[str],
                         roads: Sequence[tuple[str, str, Sequence[tuple[int, int]]]]) -> str: ...
def read_road_metadata(source: Mapping | str) -> RoadMetadata: ...
def decode_road_network(source: Mapping | str) -> RoadNetwork: ...
```

`road_source_signature` follows `partition_source_signature_from_fingerprints`: it hashes the sorted `(path, fingerprint)` rows of `ROAD_SOURCE_KINDS`, then the elevation fingerprint, then sorted `(region, speed)` rows. A falsy signature is never current, matching `partition_freshness`.

The approved design's input list names terrain time but not where it comes from. Speeds stay in `world/rules/rulebook/movement.yaml`, the single authority, and they join the signature, so a speed change reads as stale. Elevation joins for the same reason.

`road_fingerprint` is SHA-256 over canonical `json.dumps({"nodes": nodes, "roads": rows}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, where each row is `[first, second, flat_cells]`. Encoding and decoding both call it, so the two cannot drift.

Artifact layout, with one road per line:

```json
{
  "algorithm_version": 1,
  "fingerprint": "<road_fingerprint>",
  "frame_cells": 2700,
  "nodes": ["<key>"],
  "roads": [
    {"cells": [0, 0, 1, 1], "first": "<key>", "second": "<key>"}
  ],
  "source_signature": "<sha256>",
  "version": 1
}
```

`cells` is flat `[x0, y0, x1, y1, ...]`. Each road object is `json.dumps(road, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`. The text ends with one line feed. `encode_road_document` sorts roads by `(first, second)` and nodes by key. `decode_road_network` rejects a wrong `version`, a non-string `first` or `second`, `first >= second`, an empty or odd `cells`, a non-integer or boolean coordinate, a coordinate outside `0..frame_cells - 1`, and a fingerprint that disagrees with the recomputed value.

### D3. Region speed reader

`world/rules/travel_cost.py` gains, with an `__all__` entry:

```python
def region_speeds_m_per_hour() -> dict[str, int]:
    """Each wilderness region's authored speed, the road generator's terrain price."""
    return {region: terrain_speed_m_per_hour(terrain) for region, terrain in WILDERNESS_TERRAIN.items()}
```

### D4. Test placement and traceability

Tests live in top-level `tests/test_road_network_format.py`, in the root environment. Worlds come from `packages/map-core/tests/authoring_fixtures.py`, imported through the `sys.path` pattern in `tests/test_elevation_contract.py::_synthetic_workspace`; do not copy that file. No test names shipped regions, locations or values.

Do **not** add `covers_requirement` in this change. `tools/spec_traceability.py` knows only IDs in `openspec/specs/`, so an annotation on an active-change requirement fails the gate. As in archived changes, the hand-off lists the test-to-requirement mapping and archive adds the annotations after sync. Top-level placement is what allows that later, since map-core's environment cannot import `tools.spec_traceability`.

## Risks / Trade-offs

- [`content/map-reference-context.json` hashes `packages/map-core/elosern_map_core/**/*.py` and `world/rules/**/*.py`, so it goes stale here] → Task 4.1 regenerates it after the last source edit.
- [Optional at load could hide a deleted file] → `road-network-generation` and `road-network-runtime` both refuse to proceed without it.

## Migration Plan

None.
