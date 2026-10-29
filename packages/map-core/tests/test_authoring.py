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
    gate_approach_cell,
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
    data["binding"]["anchor_cell"] = {"cell_x": 15, "cell_y": 21}
    data["wilderness_entry"]["origin"] = {"cell_x": 14, "cell_y": 21}
    data["wilderness_entry"]["shape"] = ["###"]
    data["wilderness_entry"]["gates"] = [{"return_direction": "n", "destination_node": "gate"}]
    world = load_authoring_world(fixtures.custom_sources(settlement=data))
    assert "blocked_approach" in {item.code for item in world.diagnostics}


def test_gate_approach_cell_follows_the_authored_mask_rule():
    from elosern_map_core.documents import WildernessEntryDeclaration

    point = WildernessEntryDeclaration(shape=("#",), origin=(7, 9), gates=())
    assert gate_approach_cell(point, "n") == (7, 9)
    # A 3x1 strip: walking from the midpoint (11, 4) opposite the return
    # direction leaves the mask on the first cell outside it.
    strip = WildernessEntryDeclaration(shape=("###",), origin=(10, 4), gates=())
    assert gate_approach_cell(strip, "w") == (13, 4)
    assert gate_approach_cell(strip, "e") == (9, 4)
    assert gate_approach_cell(WildernessEntryDeclaration(shape=("...",), origin=(0, 0), gates=()), "n") is None


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


def test_d2_matrix_structure_diagnostics():
    # 1. multiple_anchor_rooms
    data_multi = fixtures.settlement_data()
    data_multi["nodes"]["plaza"]["prototype_parent"] = "anchor_room"
    data_multi["nodes"]["plaza"]["anchor_key"] = "demo_location"
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(settlement=data_multi))
    diag = next(d for d in captured.value.diagnostics if d.code == "multiple_anchor_rooms")
    assert diag.category == "structure"
    assert diag.object_id == "demo_map"

    # 2. anchor_location_mismatch
    data_mismatch = fixtures.settlement_data()
    data_mismatch["nodes"]["gate"]["anchor_key"] = "wrong_location"
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(settlement=data_mismatch))
    diag = next(d for d in captured.value.diagnostics if d.code == "anchor_location_mismatch")
    assert diag.category == "structure"
    assert diag.object_id == "demo_map"

    # 3. duplicate_location_binding
    second_settlement = fixtures.settlement_data()
    second_settlement["id"] = "second_map"
    second_settlement["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 6, "cell_y": 6},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    second_src = fixtures.make_source_document(
        "content/maps/settlements/second_map.yaml",
        fixtures.yaml_text(second_settlement),
    )
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world([*fixtures.source_documents(), second_src])
    diag = next(d for d in captured.value.diagnostics if d.code == "duplicate_location_binding")
    assert diag.category == "structure"
    assert "demo_map" in diag.message and "second_map" in diag.message

    # 4. duplicate_interior_room
    int1 = fixtures.interior_data("shop")
    int2 = fixtures.interior_data("inn")
    int2["rooms"] = {"hall": dict(int1["rooms"]["hall"])}
    int2["connections"] = []
    int2["exterior"] = None
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(interiors={"shop": int1, "inn": int2}))
    diag = next(d for d in captured.value.diagnostics if d.code == "duplicate_interior_room")
    assert diag.category == "structure"
    assert "shop" in diag.message and "inn" in diag.message

    # 5. duplicate_doorway
    int_d1 = fixtures.interior_data("shop")
    int_d2 = fixtures.interior_data("inn")
    int_d2["rooms"] = {"inn_room": dict(int_d1["rooms"]["hall"])}
    int_d2["connections"] = []
    int_d2["exterior"] = {
        "settlement": "demo_map",
        "node": int_d1["exterior"]["node"],
        "room": "inn_room",
        "doorway_key": int_d1["exterior"]["doorway_key"],
        "doorway_aliases": [],
    }
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(interiors={"shop": int_d1, "inn": int_d2}))
    diag = next(d for d in captured.value.diagnostics if d.code == "duplicate_doorway")
    assert diag.category == "structure"
    assert "shop" in diag.message and "inn" in diag.message

    # 6. duplicate_gate_destination
    data_dup_gate = fixtures.settlement_data()
    data_dup_gate["wilderness_entry"] = {
        "shape": ["###"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [
            {"return_direction": "n", "destination_node": "gate"},
            {"return_direction": "s", "destination_node": "gate"},
        ],
    }
    with pytest.raises(AuthoringError) as captured:
        load_authoring_world(fixtures.custom_sources(settlement=data_dup_gate))
    diag = next(d for d in captured.value.diagnostics if d.code == "duplicate_gate_destination")
    assert diag.category == "structure"
    assert diag.object_id == "demo_map"


def test_d2_matrix_semantic_diagnostics():
    # Control: valid world has no diagnostics and compiles
    valid_world = fixtures.loaded_world()
    assert not valid_world.diagnostics
    snapshot = compile_runtime(
        valid_world,
        fixtures.valid_external(valid_world),
        fixtures.current_freshness(valid_world),
    )
    assert snapshot is not None

    # 1. missing_anchor_room (saveable WIP, rejected by compile_runtime)
    data_no_anchor = fixtures.settlement_data()
    data_no_anchor["nodes"]["gate"]["prototype_parent"] = "grid_room"
    data_no_anchor["nodes"]["gate"]["anchor_key"] = None
    world = load_authoring_world(fixtures.custom_sources(settlement=data_no_anchor))
    diag = next(d for d in world.diagnostics if d.code == "missing_anchor_room")
    assert diag.category == "semantic"
    assert diag.object_id == "demo_map"
    with pytest.raises(RuntimeRejection) as captured:
        compile_runtime(world, fixtures.valid_external(world), fixtures.current_freshness(world))
    assert "missing_anchor_room" in {d.code for d in captured.value.diagnostics}

    # 2. point_gate_count
    data_point_gates = fixtures.settlement_data()
    data_point_gates["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [
            {"return_direction": "n", "destination_node": "gate"},
            {"return_direction": "s", "destination_node": "plaza"},
        ],
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_point_gates))
    diag = next(d for d in world.diagnostics if d.code == "point_gate_count")
    assert diag.category == "semantic"

    # 3. disconnected_footprint
    data_disc = fixtures.settlement_data()
    data_disc["wilderness_entry"] = {
        "shape": ["#.#"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_disc))
    diag = next(d for d in world.diagnostics if d.code == "disconnected_footprint")
    assert diag.category == "semantic"

    # 4. invalid_footprint_anchor
    data_anchor_dot = fixtures.settlement_data()
    data_anchor_dot["wilderness_entry"] = {
        "shape": ["###", "#.#", "###"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_anchor_dot))
    diag = next(d for d in world.diagnostics if d.code == "invalid_footprint_anchor")
    assert diag.category == "semantic"

    # 5. invalid_footprint_cell (outside frame and impassable terrain)
    data_out_frame = fixtures.settlement_data()
    data_out_frame["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 45, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_out_frame))
    diag = next(d for d in world.diagnostics if d.code == "invalid_footprint_cell")
    assert diag.category == "semantic"

    data_impassable = fixtures.settlement_data()
    data_impassable["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 15, "cell_y": 20},  # summit ridge
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_impassable))
    diag = next(d for d in world.diagnostics if d.code == "invalid_footprint_cell")
    assert diag.category == "semantic"

    # 6. invalid_gate_approach (approach ray leaves frame)
    data_leaves_frame = fixtures.settlement_data()
    data_leaves_frame["wilderness_entry"] = {
        "shape": ["###"],
        "origin": {"cell_x": 37, "cell_y": 5},
        "gates": [{"return_direction": "w", "destination_node": "gate"}],  # exit to east leaves frame (x=40)
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_leaves_frame))
    diag = next(d for d in world.diagnostics if d.code == "invalid_gate_approach")
    assert diag.category == "semantic"

    # 7. overlapping_footprint (footprint overlap and point-anchor containment)
    data1 = fixtures.settlement_data()
    data1["wilderness_entry"] = {
        "shape": ["##", "##"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    data2 = fixtures.settlement_data()
    data2["id"] = "second_map"
    data2["location_ref"] = "second_location"
    data2["nodes"]["gate"]["anchor_key"] = "second_location"
    data2["wilderness_entry"] = {
        "shape": ["##", "##"],
        "origin": {"cell_x": 6, "cell_y": 5},  # overlaps with (6, 5), (6, 6)
        "gates": [{"return_direction": "s", "destination_node": "gate"}],
    }
    locs = fixtures.locations_data()
    locs["locations"]["second_location"] = {
        "kind": "capital",
        "display_name_zh": "第二城",
        "description": "Second town",
        "cell": {"cell_x": 6, "cell_y": 5},
        "geographic_constraint": "synthetic",
        "scene_archetype": None,
    }
    src1 = fixtures.make_source_document("content/maps/settlements/demo_map.yaml", fixtures.yaml_text(data1))
    src2 = fixtures.make_source_document("content/maps/settlements/second_map.yaml", fixtures.yaml_text(data2))
    loc_src = fixtures.make_source_document("content/maps/locations.yaml", fixtures.yaml_text(locs))
    cont_src = fixtures.make_source_document("content/maps/continent.yaml", fixtures.yaml_text(fixtures.continent_data()))
    dist_src = fixtures.make_source_document("content/maps/districts.yaml", fixtures.yaml_text(fixtures.districts_data()))
    world = load_authoring_world([cont_src, loc_src, dist_src, src1, src2])
    diag = next(d for d in world.diagnostics if d.code == "overlapping_footprint")
    assert diag.category == "semantic"
    assert "second_map" in diag.message or "demo_map" in diag.message

    # 8. gate_approach_collision & duplicate_gate_approach
    data_g1 = fixtures.settlement_data()
    data_g1["wilderness_entry"] = {
        "shape": ["###"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],  # approach is (6, 4)
    }
    data_g2 = fixtures.settlement_data()
    data_g2["id"] = "second_map"
    data_g2["location_ref"] = "second_location"
    data_g2["nodes"]["gate"]["anchor_key"] = "second_location"
    data_g2["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 6, "cell_y": 4},
        "gates": [{"return_direction": "w", "destination_node": "gate"}],  # point anchor is (6, 4)
    }
    src_g1 = fixtures.make_source_document("content/maps/settlements/demo_map.yaml", fixtures.yaml_text(data_g1))
    src_g2 = fixtures.make_source_document("content/maps/settlements/second_map.yaml", fixtures.yaml_text(data_g2))
    world = load_authoring_world([cont_src, loc_src, dist_src, src_g1, src_g2])
    diag_coll = next(d for d in world.diagnostics if d.code == "gate_approach_collision")
    assert diag_coll.category == "semantic"

    # duplicate_gate_approach
    data_g2["wilderness_entry"] = {
        "shape": ["###"],
        "origin": {"cell_x": 5, "cell_y": 5},
        "gates": [{"return_direction": "n", "destination_node": "gate"}],
    }
    src_g2_dup = fixtures.make_source_document("content/maps/settlements/second_map.yaml", fixtures.yaml_text(data_g2))
    world_dup = load_authoring_world([cont_src, loc_src, dist_src, src_g1, src_g2_dup])
    diag_dup = next(d for d in world_dup.diagnostics if d.code == "duplicate_gate_approach")
    assert diag_dup.category == "semantic"

    # 9. blocked_point_neighbor
    data_point_blocked = fixtures.settlement_data()
    # origin at (15, 21), return_direction "n" -> neighbor at (15, 20) which is impassable ridge
    data_point_blocked["wilderness_entry"] = {
        "shape": ["#"],
        "origin": {"cell_x": 15, "cell_y": 21},
        "gates": [{"return_direction": "s", "destination_node": "gate"}],  # delta for s is (0, -1) -> neighbor (15, 20)
    }
    world = load_authoring_world(fixtures.custom_sources(settlement=data_point_blocked))
    diag = next(d for d in world.diagnostics if d.code == "blocked_point_neighbor")
    assert diag.category == "semantic"
