"""Mechanism tests for qualified static-reference resolution."""

from __future__ import annotations

import pytest

import authoring_fixtures as fixtures
from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import (
    DUPLICATE_REFERENCE,
    INVALID_REFERENCE,
    UNKNOWN_DOMAIN,
    UNKNOWN_REFERENCE,
    WRONG_DOMAIN,
    ReferenceError,
    ReferenceIndex,
    interior_room_ref,
    location_ref,
    resolve_reference,
    settlement_node_ref,
    settlement_position,
    wilderness_cell_ref,
)


def _index() -> ReferenceIndex:
    return ReferenceIndex.build(
        settlement_nodes=[
            ("demo_map", "gate", (0, 0)),
            ("demo_map", "plaza", (4, 4)),
        ],
        interior_rooms=[("demo_interior", "inner"), ("demo_interior", "door")],
        locations=[("demo_location", (5, 5))],
        frame_cells=40,
    )


def _rejected(code: str, reference: QualifiedRef, *, source: str = "") -> ReferenceError:
    with pytest.raises(ReferenceError) as captured:
        resolve_reference(_index(), reference, source=source)
    assert captured.value.code == code
    return captured.value


def test_each_domain_resolves_against_its_current_binding():
    index = _index()

    node = resolve_reference(index, settlement_node_ref("demo_map", "plaza"))
    assert node.domain == "settlement_node"
    assert node.map_id == "demo_map"
    assert node.object_id == "plaza"
    assert node.position_m == (4, 4)
    assert node.cell is None

    room = resolve_reference(index, interior_room_ref("demo_interior", "inner"))
    assert room.object_id == "inner"
    assert room.position_m is None and room.cell is None

    location = resolve_reference(index, location_ref("demo_location"))
    assert location.cell == (5, 5)
    assert location.position_m is None

    cell = resolve_reference(index, wilderness_cell_ref((39, 0)))
    assert cell.cell == (39, 0)
    assert cell.map_id is None and cell.object_id is None


def test_absent_target_names_the_reference_and_its_source():
    error = _rejected(
        UNKNOWN_REFERENCE,
        settlement_node_ref("demo_map", "nowhere"),
        source="district demo_district",
    )
    assert str(error).startswith("district demo_district: ")
    assert "settlement_node:demo_map:nowhere" in str(error)
    assert "no authored node" in str(error)


def test_absent_map_is_distinguished_from_an_absent_node():
    error = _rejected(UNKNOWN_REFERENCE, settlement_node_ref("missing_map", "plaza"))
    assert "no authored settlement 'missing_map'" in str(error)


def test_wrong_domain_names_the_domain_the_identity_is_authored_under():
    error = _rejected(WRONG_DOMAIN, settlement_node_ref("demo_map", "inner"))
    assert "is not an authored settlement_node" in str(error)
    assert "authored interior_room" in str(error)

    error = _rejected(WRONG_DOMAIN, location_ref("plaza"))
    assert "authored settlement_node" in str(error)


def test_unknown_domain_is_rejected_before_lookup():
    error = _rejected(UNKNOWN_DOMAIN, QualifiedRef(domain="city_gate", object_id="x"))
    assert "domain 'city_gate'" in str(error)
    assert UNKNOWN_DOMAIN in str(error.code)


@pytest.mark.parametrize(
    "reference",
    [
        QualifiedRef(domain="settlement_node", object_id="plaza"),
        QualifiedRef(domain="settlement_node", map_id="demo_map", object_id="plaza", cell=(1, 1)),
        QualifiedRef(domain="location", map_id="demo_map", object_id="demo_location"),
        QualifiedRef(domain="wilderness_cell", object_id="demo_location", cell=(1, 1)),
        QualifiedRef(domain="wilderness_cell"),
    ],
)
def test_domain_shape_violations_are_invalid_references(reference):
    error = _rejected(INVALID_REFERENCE, reference)
    assert error.code == INVALID_REFERENCE


def test_cell_outside_the_frame_is_rejected():
    error = _rejected(INVALID_REFERENCE, wilderness_cell_ref((40, 0)))
    assert "outside the 40-cell frame" in str(error)


def test_duplicate_bindings_are_rejected_while_building_the_index():
    with pytest.raises(ReferenceError) as captured:
        ReferenceIndex.build(
            settlement_nodes=[
                ("demo_map", "plaza", (4, 4)),
                ("demo_map", "plaza", (5, 5)),
            ]
        )
    assert captured.value.code == DUPLICATE_REFERENCE
    assert "demo_map:plaza" in str(captured.value)

    with pytest.raises(ReferenceError) as captured:
        ReferenceIndex.build(locations=[("demo_location", (5, 5)), ("demo_location", (6, 6))])
    assert captured.value.code == DUPLICATE_REFERENCE


def test_a_consumer_requiring_a_settlement_node_rejects_other_domains():
    index = _index()
    with pytest.raises(ReferenceError) as captured:
        settlement_position(index, location_ref("demo_location"))
    assert captured.value.code == WRONG_DOMAIN
    assert settlement_position(index, settlement_node_ref("demo_map", "gate")) == (0, 0)


def test_authoring_world_exposes_its_current_reference_index():
    world = fixtures.loaded_world()

    node = resolve_reference(
        world, settlement_node_ref("demo_map", "plaza"), source="synthetic"
    )
    assert node.position_m == world.settlements["demo_map"].nodes["plaza"].coordinate
    assert resolve_reference(world, location_ref("demo_location")).cell == (5, 5)
