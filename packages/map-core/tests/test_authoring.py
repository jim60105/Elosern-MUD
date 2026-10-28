"""Mechanism tests for authoring load, diagnostics and runtime acceptance."""

from __future__ import annotations

import copy
import dataclasses

import pytest

import authoring_fixtures as fixtures
from elosern_map_core.authoring import (
    PARTITION_ALGORITHM_VERSION,
    AuthoritativeExternalResult,
    PartitionFreshness,
    compile_runtime,
    diagnose_world,
    load_authoring_world,
)
from elosern_map_core.codec import document_from_data, serialize_document
from elosern_map_core.diagnostics import (
    AuthoringError,
    RuntimeRejection,
    diagnostic_sort_key,
)
from elosern_map_core.schema import validate_document
from elosern_map_core.sources import (
    discover_source_documents,
    discover_source_paths,
    fingerprint_text,
    make_source_document,
)

SETTLEMENT_PATH = fixtures.SETTLEMENT_PATH


def _codes(error: AuthoringError) -> set[str]:
    return {item.code for item in error.diagnostics}


def _write(root, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_discovery_is_sorted_and_excludes_layouts_and_artifacts(tmp_path):
    _write(tmp_path, "content/maps/continent.yaml", "a: 1\n")
    _write(tmp_path, "content/maps/locations.yaml", "a: 1\n")
    _write(tmp_path, "content/maps/districts.yaml", "a: 1\n")
    _write(tmp_path, "content/maps/settlements/b_map.yaml", "a: 1\n")
    _write(tmp_path, "content/maps/settlements/a_map.yaml", "a: 1\n")
    _write(tmp_path, "content/maps/interiors/z_interior.yaml", "a: 1\n")
    _write(tmp_path, "content/map-editor-layouts/z_interior.yaml", "a: 1\n")
    _write(tmp_path, "world/maps/data/district_partition.json", "{}")

    assert discover_source_paths(tmp_path) == (
        "content/maps/continent.yaml",
        "content/maps/districts.yaml",
        "content/maps/interiors/z_interior.yaml",
        "content/maps/locations.yaml",
        "content/maps/settlements/a_map.yaml",
        "content/maps/settlements/b_map.yaml",
    )
    documents = discover_source_documents(tmp_path)
    assert [document.relative_path for document in documents] == list(
        discover_source_paths(tmp_path)
    )
    for document in documents:
        assert document.fingerprint == fingerprint_text(document.text)


def test_provenance_records_one_based_source_locations():
    text = fixtures.yaml_text(fixtures.settlement_data())
    parsed = fixtures.parsed_settlement_text(text)
    expected_line = next(
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip() == "x_m: 100"
    )
    location = parsed.provenance["nodes.plaza.x_m"]
    assert location.line == expected_line
    assert location.column >= 1


def test_synthetic_world_loads_without_diagnostics_and_compiles():
    world = fixtures.loaded_world()
    assert world.diagnostics == ()
    assert diagnose_world(world) == ()
    snapshot = compile_runtime(
        world,
        fixtures.valid_external(world),
        fixtures.current_freshness(world),
    )
    assert set(snapshot.settlements) == {"demo_map"}
    graph = snapshot.settlements["demo_map"]
    assert graph.route("gate", "plaza") is not None


def test_empty_world_is_saveable_but_runtime_rejected():
    districts = fixtures.districts_data()
    districts["districts"]["demo_district"]["landmark"] = {
        "domain": "wilderness_cell",
        "map_id": None,
        "object_id": None,
        "cell": {"cell_x": 5, "cell_y": 5},
    }
    settlement = fixtures.settlement_data(nodes={}, roads=[], entry=False)
    settlement["city_gate"] = None
    world = load_authoring_world(
        fixtures.custom_sources(settlement=settlement, districts=districts)
    )
    assert "empty_graph" in {item.code for item in world.diagnostics}
    assert diagnose_world(world) == world.diagnostics

    # Saveability: every document still serializes through the same codec.
    emitted = serialize_document(world.settlements["demo_map"])
    assert "nodes" in emitted

    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(
            world,
            fixtures.valid_external(world),
            fixtures.current_freshness(world),
        )
    assert "empty_graph" in {item.code for item in captured.value.diagnostics}


def test_unreachable_landmark_is_saveable_work_in_progress():
    world = fixtures.loaded_world(roads=[])
    assert "unreachable_landmark" in {item.code for item in world.diagnostics}
    emitted = serialize_document(world.settlements["demo_map"])
    assert "plaza" in emitted
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(
            world,
            fixtures.valid_external(world),
            fixtures.current_freshness(world),
        )
    assert "unreachable_landmark" in {
        item.code for item in captured.value.diagnostics
    }


def test_blocked_approach_is_a_semantic_diagnostic():
    data = fixtures.settlement_data()
    data["binding"]["anchor_cell"] = {"cell_x": 15, "cell_y": 20}
    data["wilderness_entry"]["origin"] = {"cell_x": 15, "cell_y": 20}
    world = load_authoring_world(fixtures.custom_sources(settlement=data))
    assert "blocked_approach" in {item.code for item in world.diagnostics}


def test_interiors_load_and_resolve_their_references():
    world = load_authoring_world(
        fixtures.custom_sources(
            settlement=fixtures.settlement_data(),
            interiors={"demo_interior": fixtures.interior_data()},
        )
    )
    assert world.diagnostics == ()
    interior = world.interiors["demo_interior"]
    assert interior.exterior is not None
    assert interior.exterior.settlement == "demo_map"


def _interior_landmark_districts() -> dict:
    districts = fixtures.districts_data()
    districts["districts"]["demo_district"]["landmark"] = {
        "domain": "interior_room",
        "map_id": "demo_interior",
        "object_id": "inner",
        "cell": None,
    }
    return districts


def test_reachable_interior_room_landmark_compiles():
    world = load_authoring_world(
        fixtures.custom_sources(
            settlement=fixtures.settlement_data(),
            districts=_interior_landmark_districts(),
            interiors={"demo_interior": fixtures.interior_data()},
        )
    )
    assert world.diagnostics == ()
    compile_runtime(
        world,
        fixtures.valid_external(world),
        fixtures.current_freshness(world),
    )


def test_disconnected_interior_room_landmark_is_saveable_but_rejected():
    interior = fixtures.interior_data()
    interior["connections"] = []
    world = load_authoring_world(
        fixtures.custom_sources(
            settlement=fixtures.settlement_data(),
            districts=_interior_landmark_districts(),
            interiors={"demo_interior": interior},
        )
    )
    assert "unreachable_landmark" in {item.code for item in world.diagnostics}
    serialize_document(world.interiors["demo_interior"])
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(
            world,
            fixtures.valid_external(world),
            fixtures.current_freshness(world),
        )
    assert "unreachable_landmark" in {
        item.code for item in captured.value.diagnostics
    }


def test_entrance_less_interior_room_landmark_is_rejected():
    interior = fixtures.interior_data()
    interior["exterior"] = None
    world = load_authoring_world(
        fixtures.custom_sources(
            settlement=fixtures.settlement_data(),
            districts=_interior_landmark_districts(),
            interiors={"demo_interior": interior},
        )
    )
    assert "unreachable_landmark" in {item.code for item in world.diagnostics}


def test_exterior_room_must_belong_to_the_interior():
    interior = fixtures.interior_data()
    interior["exterior"]["room"] = "nowhere"
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(
            fixtures.custom_sources(
                settlement=fixtures.settlement_data(),
                interiors={"demo_interior": interior},
            )
        )
    assert "unknown_reference" in _codes(captured.value)


def _bad_settlement(mutator) -> dict:
    data = fixtures.settlement_data()
    mutator(data)
    return data


@pytest.mark.parametrize(
    "mutator, code",
    [
        (
            lambda data: data["nodes"]["plaza"].__setitem__("x_m", 0),
            "duplicate_coordinate",
        ),
        (
            lambda data: data["roads"].append(copy.deepcopy(data["roads"][0])),
            "duplicate_identity",
        ),
        (
            lambda data: data["roads"].append(
                {
                    "source": "gate",
                    "destination": "gate",
                    "direction": "w",
                    "bends": [],
                }
            ),
            "self_loop",
        ),
        (
            lambda data: data["roads"][0].__setitem__("destination", "nowhere"),
            "unknown_node",
        ),
        (
            lambda data: data["city_gate"].__setitem__("node", "nowhere"),
            "unknown_node",
        ),
        (
            lambda data: data["wilderness_entry"]["gates"][0].__setitem__(
                "destination_node", "nowhere"
            ),
            "unknown_node",
        ),
        (
            lambda data: data.__setitem__("location_ref", "nowhere"),
            "unknown_reference",
        ),
    ],
)
def test_structural_defects_are_load_rejections(mutator, code):
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(
            fixtures.custom_sources(settlement=_bad_settlement(mutator))
        )
    assert code in _codes(captured.value)


@pytest.mark.parametrize(
    "mutator, code",
    [
        (
            lambda continent: continent["regions"]["eastern_plains"].__setitem__(
                "terrain_flavor_zh", ["only one variant"]
            ),
            "invalid_collection_size",
        ),
        (
            lambda continent: continent["regions"]["eastern_plains"].__setitem__(
                "terrain_flavor_zh", ["a real variant", "   "]
            ),
            "invalid_field_value",
        ),
        (
            lambda continent: continent["regions"]["eastern_plains"].__setitem__(
                "display_name_zh",
                continent["regions"]["southeast_coast"]["display_name_zh"],
            ),
            "duplicate_value",
        ),
    ],
)
def test_region_declarations_reject_incomplete_or_duplicate_authoring(mutator, code):
    continent = fixtures.continent_data()
    mutator(continent)
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(continent=continent))
    assert code in _codes(captured.value)


def test_duplicate_outgoing_direction_is_structural():
    data = fixtures.settlement_data()
    data["nodes"]["market"] = {
        "x_m": 200,
        "y_m": 0,
        "prototype_parent": "grid_room",
        "key": "Market",
        "desc": "A market.",
        "anchor_key": None,
        "typeclass": None,
        "scene_archetype": None,
    }
    data["roads"].append(
        {
            "source": "gate",
            "destination": "market",
            "direction": "e",
            "bends": [],
        }
    )
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(settlement=data))
    assert "duplicate_outgoing_direction" in _codes(captured.value)


def test_unknown_interior_references_are_structurally_rejected():
    interior = fixtures.interior_data()
    interior["exterior"]["node"] = "nowhere"
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(
            fixtures.custom_sources(
                settlement=fixtures.settlement_data(),
                interiors={"demo_interior": interior},
            )
        )
    assert "unknown_reference" in _codes(captured.value)

    interior = fixtures.interior_data()
    interior["interior_links"] = [
        {
            "source_room": "hall",
            "target_interior": "missing_interior",
            "target_room": "inner",
            "label": "through",
            "return_label": None,
        }
    ]
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(
            fixtures.custom_sources(
                settlement=fixtures.settlement_data(),
                interiors={"demo_interior": interior},
            )
        )
    assert "unknown_reference" in _codes(captured.value)


def test_required_documents_missing_and_unsupported_paths_are_rejected():
    settlement = make_source_document(
        SETTLEMENT_PATH, fixtures.yaml_text(fixtures.settlement_data())
    )
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world((settlement,))
    assert "missing_document" in _codes(captured.value)

    sources = list(fixtures.custom_sources(settlement=fixtures.settlement_data()))
    sources.append(
        make_source_document(
            "content/map-editor-layouts/demo_interior.yaml",
            "version: 1\nkind: layout\nid: demo_interior\npositions: {}\n",
        )
    )
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(sources)
    assert "unsupported_source_path" in _codes(captured.value)


def test_duplicate_source_paths_and_fingerprint_mismatch_are_rejected():
    sources = list(fixtures.custom_sources(settlement=fixtures.settlement_data()))
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(sources + [sources[0]])
    assert "duplicate_source_path" in _codes(captured.value)

    tampered = make_source_document(
        SETTLEMENT_PATH,
        fixtures.yaml_text(fixtures.settlement_data()),
        fingerprint="not-the-content",
    )
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(
            tuple(
                source
                for source in sources
                if source.relative_path != SETTLEMENT_PATH
            )
            + (tampered,)
        )
    assert "fingerprint_mismatch" in _codes(captured.value)


def test_unknown_kind_is_rejected_by_the_schema():
    diagnostics = validate_document("castle", {"version": 1, "kind": "castle"})
    assert "unsupported_kind" in {item.code for item in diagnostics}


def test_diagnostics_are_deterministically_ordered():
    data = fixtures.settlement_data()
    data["location_ref"] = "nowhere"
    data["city_gate"]["node"] = "nowhere"
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(settlement=data))
    diagnostics = captured.value.diagnostics
    assert diagnostics == tuple(sorted(diagnostics, key=diagnostic_sort_key))
    lines = [item.line for item in diagnostics if item.line is not None]
    assert lines == sorted(lines)


def test_runtime_accepts_only_a_complete_world():
    world = fixtures.loaded_world()
    snapshot = compile_runtime(
        world,
        fixtures.valid_external(world),
        fixtures.current_freshness(world),
    )
    assert snapshot.partition_algorithm_version == PARTITION_ALGORITHM_VERSION
    assert snapshot.external_fingerprint == "external-evidence"


@pytest.mark.parametrize(
    "external_overrides, code",
    [
        ({"valid": False}, "external_reference_invalid"),
        ({"version": 2}, "external_version_unsupported"),
        ({"fingerprint": ""}, "external_reference_unavailable"),
        ({"world_fingerprint": "other"}, "external_result_stale"),
    ],
)
def test_runtime_rejects_failed_external_results(external_overrides, code):
    world = fixtures.loaded_world()
    external = dataclasses.replace(
        fixtures.valid_external(world), **external_overrides
    )
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(
            world, external, fixtures.current_freshness(world)
        )
    assert code in {item.code for item in captured.value.diagnostics}


@pytest.mark.parametrize(
    "freshness_overrides, code",
    [
        ({"current": False}, "stale_partition"),
        ({"input_signature": "other"}, "stale_partition"),
        ({"algorithm_version": 2}, "partition_algorithm_unsupported"),
        ({"input_signature": ""}, "partition_signature_missing"),
    ],
)
def test_runtime_rejects_stale_or_missing_freshness(freshness_overrides, code):
    world = fixtures.loaded_world()
    freshness = dataclasses.replace(
        fixtures.current_freshness(world), **freshness_overrides
    )
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(world, fixtures.valid_external(world), freshness)
    assert code in {item.code for item in captured.value.diagnostics}


def test_runtime_rejects_a_missing_external_result_or_freshness():
    world = fixtures.loaded_world()
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(world, None, fixtures.current_freshness(world))
    assert "external_reference_unavailable" in {
        item.code for item in captured.value.diagnostics
    }
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(world, fixtures.valid_external(world), None)
    assert "partition_missing" in {
        item.code for item in captured.value.diagnostics
    }


def test_an_external_result_from_another_world_cannot_authorize_this_one():
    first = fixtures.loaded_world()
    second = fixtures.loaded_world(roads=fixtures.settlement_data()["roads"][:1])
    assert first.fingerprint != second.fingerprint
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(
            second,
            fixtures.valid_external(first),
            fixtures.current_freshness(second),
        )
    assert "external_result_stale" in {
        item.code for item in captured.value.diagnostics
    }


def test_diagnose_world_reports_a_stale_partition_as_saveable():
    world = fixtures.loaded_world()
    stale = PartitionFreshness(
        algorithm_version=PARTITION_ALGORITHM_VERSION,
        input_signature="different-inputs",
        current=True,
    )
    assert "stale_partition" in {
        item.code for item in diagnose_world(world, partition_freshness=stale)
    }
    assert diagnose_world(
        world, partition_freshness=fixtures.current_freshness(world)
    ) == ()


def test_snapshot_and_documents_are_immutable():
    world = fixtures.loaded_world()
    snapshot = compile_runtime(
        world,
        fixtures.valid_external(world),
        fixtures.current_freshness(world),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.fingerprint = "changed"
    with pytest.raises(TypeError):
        snapshot.settlements["other"] = None
    with pytest.raises(TypeError):
        world.settlements["demo_map"].data["nodes"]["plaza"]["x_m"] = 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        world.settlements["demo_map"].nodes["plaza"].x_m = 1


def test_mask_cells_list_every_hash_cell_even_for_a_point_shape():
    from elosern_map_core.documents import WildernessEntryDeclaration

    point = WildernessEntryDeclaration(shape=(".#",), origin=(5, 7), gates=())
    assert point.footprint_cells == frozenset()
    assert point.mask_cells == frozenset({(6, 7)})
    block = WildernessEntryDeclaration(shape=("#.", "##"), origin=(1, 2), gates=())
    assert block.mask_cells == block.footprint_cells == frozenset({(1, 2), (1, 3), (2, 3)})
