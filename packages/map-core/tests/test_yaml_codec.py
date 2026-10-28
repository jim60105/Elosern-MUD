"""Mechanism tests for the restricted YAML codec and its round trips."""

from __future__ import annotations

import copy
import dataclasses

import pytest

import authoring_fixtures as fixtures
from elosern_map_core.codec import (
    document_from_data,
    parse_document,
    serialize_document,
)
from elosern_map_core.diagnostics import AuthoringError
from elosern_map_core.schema import MAX_DOCUMENT_BYTES, schema

SETTLEMENT_PATH = fixtures.SETTLEMENT_PATH


def _codes(text: str) -> set[str]:
    with pytest.raises(AuthoringError) as captured:
        parse_document(SETTLEMENT_PATH, text)
    return {item.code for item in captured.value.diagnostics}


@pytest.mark.parametrize(
    "text, code",
    [
        ("version: 1\nversion: 2\n", "duplicate_key"),
        ("a: !dangerous 1\n", "unsupported_tag"),
        ("a: &shared 1\nb: *shared\n", "anchor_or_alias"),
        ("child:\n  <<: {x: 1}\n", "merge_key"),
        ("a: 2024-01-01\n", "timestamp_value"),
        ("a: !!timestamp 2024-01-01\n", "unsupported_tag"),
        ("a: 2024-01-01\n", "timestamp_value"),
        ("a: .inf\n", "non_finite_number"),
        ("a: .nan\n", "non_finite_number"),
        ("a: 0o17\n", "invalid_number_literal"),
        ("a: 1_000\n", "invalid_number_literal"),
        ("a: !!set {x: null}\n", "unsupported_tag"),
        ("a: !!binary aGk=\n", "unsupported_tag"),
        ("a: 1\n---\nb: 2\n", "multiple_documents"),
        ("", "empty_document"),
    ],
)
def test_unsafe_yaml_constructs_are_rejected(text, code):
    assert code in _codes(text)


def test_quoted_timestamp_looking_text_stays_a_string():
    data = fixtures.settlement_data()
    data["nodes"]["plaza"]["desc"] = "2024-01-01"
    document = document_from_data(SETTLEMENT_PATH, data)
    assert document.data["nodes"]["plaza"]["desc"] == "2024-01-01"


def test_duplicate_keys_are_detected_in_nested_mappings_before_construction():
    text = """
version: 1
kind: settlement
id: demo_map
nodes:
  plaza:
    x_m: 0
    x_m: 1
"""
    assert "duplicate_key" in _codes(text)


def test_quoted_and_unquoted_duplicate_keys_are_the_same_key():
    assert "duplicate_key" in _codes('a: 1\n"a": 2\n')


def test_identical_keys_in_sibling_mappings_are_allowed():
    data = fixtures.settlement_data()
    data["nodes"]["gate"]["scene_archetype"] = None
    data["nodes"]["plaza"]["scene_archetype"] = None
    text = fixtures.yaml_text(data)
    document = parse_document(SETTLEMENT_PATH, text)
    assert set(document.document.nodes) == {"gate", "plaza"}


def test_document_size_is_bounded_before_parsing():
    text = "a: " + "x" * MAX_DOCUMENT_BYTES
    assert "invalid_document_size" in _codes(text)


def test_document_depth_is_bounded():
    text = "a: " + "[" * 40 + "]" * 40
    assert "invalid_document_depth" in _codes(text)


def test_malformed_yaml_is_a_structured_rejection_with_location():
    with pytest.raises(AuthoringError) as captured:
        parse_document(SETTLEMENT_PATH, "nodes: [\n")
    diagnostic = captured.value.diagnostics[0]
    assert diagnostic.code == "invalid_yaml"
    assert diagnostic.relative_path == SETTLEMENT_PATH
    assert diagnostic.line is not None
    assert diagnostic.column is not None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data["nodes"]["plaza"].__setitem__("x_m", []),
        lambda data: data["roads"][0].__setitem__("source", []),
        lambda data: data["roads"][0].__setitem__("direction", []),
    ],
)
def test_malformed_uniqueness_operands_are_rejected_not_crashes(mutator):
    data = _bad_data(mutator)
    with pytest.raises(AuthoringError):
        document_from_data(SETTLEMENT_PATH, data)
    with pytest.raises(AuthoringError):
        parse_document(SETTLEMENT_PATH, fixtures.yaml_text(data))


def _bad_data(mutator):
    data = copy.deepcopy(fixtures.settlement_data())
    mutator(data)
    return data


@pytest.mark.parametrize("value", [True, 1.5, "1"])
def test_integer_fields_reject_booleans_fractions_and_numeric_strings(value):
    data = _bad_data(lambda candidate: candidate["nodes"]["plaza"].__setitem__("y_m", value))
    with pytest.raises(AuthoringError) as captured:
        document_from_data(SETTLEMENT_PATH, data)
    assert "invalid_field_value" in {item.code for item in captured.value.diagnostics}


def test_unknown_root_nested_and_prototype_fields_are_rejected():
    for mutator in (
        lambda data: data.__setitem__("mystery", 1),
        lambda data: data["binding"].__setitem__("mystery", 1),
        lambda data: data["nodes"]["plaza"].__setitem__("mystery", 1),
    ):
        with pytest.raises(AuthoringError) as captured:
            document_from_data(SETTLEMENT_PATH, _bad_data(mutator))
        assert "unknown_field" in {item.code for item in captured.value.diagnostics}


def test_unknown_version_and_identity_mismatch_are_rejected():
    with pytest.raises(AuthoringError) as captured:
        document_from_data(
            SETTLEMENT_PATH,
            _bad_data(lambda data: data.__setitem__("version", 2)),
        )
    assert "unsupported_version" in {item.code for item in captured.value.diagnostics}

    with pytest.raises(AuthoringError) as captured:
        document_from_data(
            "content/maps/settlements/other_map.yaml",
            fixtures.settlement_data(),
        )
    assert "identity_mismatch" in {item.code for item in captured.value.diagnostics}


def test_unknown_document_kind_is_rejected():
    with pytest.raises(AuthoringError) as captured:
        document_from_data(
            "content/maps/settlements/demo_map.yaml",
            {"version": 1, "kind": "castle", "id": "demo_map"},
        )
    assert "identity_mismatch" in {item.code for item in captured.value.diagnostics}


ROUND_TRIP_TEXT = """# document comment
version: 1
kind: settlement
id: demo_map
location_ref: demo_location  # location comment
binding:
  anchor_cell: {cell_x: 5, cell_y: 5}
  local_anchor_m: {east_m: 0, north_m: 0}
options: {map_visual_range: 2, map_mode: nodes}
exit_prototype: {prototype_parent: xyz_exit, typeclass: tests.Exit}
nodes:
  gate:  # retained node comment
    x_m: 0
    y_m: 0
    prototype_parent: anchor_room
    key: Gate
    desc: |-
      The way in.
    anchor_key: demo_location
    typeclass: null
    scene_archetype: city_street
  plaza:
    x_m: 100
    y_m: 0
    prototype_parent: grid_room
    key: Plaza
    desc: |-
      The middle of town.
      A second line of prose.
    anchor_key: null
    typeclass: null
    scene_archetype: null
roads:
  - source: gate  # retained road comment
    destination: plaza
    direction: e
    bends:
      - {x_m: 50, y_m: 10}
  - source: plaza
    destination: gate
    direction: w
    bends: []
wilderness_entry:
  shape:
    - "#.."
    - "###"
  origin: {cell_x: 5, cell_y: 5}
  gates:
    - {return_direction: n, destination_node: gate}
city_gate: {node: gate, exit_key: Gate, exit_aliases: [gate]}
"""


def test_round_trip_retains_prose_masks_bends_and_comments():
    parsed = parse_document(SETTLEMENT_PATH, ROUND_TRIP_TEXT)
    data = fixtures.plain_data(parsed.document.data)
    data["nodes"]["plaza"]["desc"] = "Edited prose.\nStill two lines."
    candidate = document_from_data(SETTLEMENT_PATH, data)
    emitted = serialize_document(candidate, parsed.round_trip)

    assert "# document comment" in emitted
    assert "# retained node comment" in emitted
    assert "# retained road comment" in emitted
    assert "Edited prose." in emitted
    assert "Still two lines." in emitted
    assert "###" in emitted

    reparsed = parse_document(SETTLEMENT_PATH, emitted)
    assert reparsed.document.data == candidate.data
    assert reparsed.document.data["wilderness_entry"]["shape"] == ("#..", "###")
    assert reparsed.document.data["roads"][0]["bends"] == (
        {"x_m": 50, "y_m": 10},
    )


def test_unchanged_nested_sequence_keeps_its_comments():
    text = ROUND_TRIP_TEXT.replace(
        "      - {x_m: 50, y_m: 10}",
        "      - {x_m: 50, y_m: 10}  # retained bend comment",
    )
    parsed = parse_document(SETTLEMENT_PATH, text)
    data = fixtures.plain_data(parsed.document.data)
    data["nodes"]["plaza"]["desc"] = "Only the prose changed."
    candidate = document_from_data(SETTLEMENT_PATH, data)
    emitted = serialize_document(candidate, parsed.round_trip)
    assert "# retained bend comment" in emitted


def test_reordering_identified_road_objects_keeps_their_comment():
    parsed = parse_document(SETTLEMENT_PATH, ROUND_TRIP_TEXT)
    data = fixtures.plain_data(parsed.document.data)
    data["roads"] = [data["roads"][1], data["roads"][0]]
    candidate = document_from_data(SETTLEMENT_PATH, data)
    emitted = serialize_document(candidate, parsed.round_trip)

    assert "# retained road comment" in emitted
    reparsed = parse_document(SETTLEMENT_PATH, emitted)
    assert [road["source"] for road in reparsed.document.data["roads"]] == [
        "plaza",
        "gate",
    ]


def test_a_failed_candidate_does_not_mutate_the_retained_tree():
    parsed = parse_document(SETTLEMENT_PATH, ROUND_TRIP_TEXT)
    def emit_tree():
        from io import StringIO

        from ruamel.yaml import YAML

        output = StringIO()
        YAML(typ="rt", pure=True).dump(parsed.round_trip, output)
        return output.getvalue()

    before = emit_tree()
    bad_data = dict(parsed.document.data)
    bad_data["mystery"] = 1
    bad = dataclasses.replace(parsed.document, data=bad_data)
    with pytest.raises(AuthoringError):
        serialize_document(bad, parsed.round_trip)
    assert emit_tree() == before


def test_serializer_reparses_its_own_output():
    document = document_from_data(SETTLEMENT_PATH, fixtures.settlement_data())
    emitted = serialize_document(document)
    reparsed = parse_document(SETTLEMENT_PATH, emitted)
    assert reparsed.document.data == document.data


def test_an_interior_room_carries_an_optional_artwork_key():
    """A room's artwork key is authored, optional, and never inferred.

    The declaration is the only source of a room's registered artwork lineage:
    an absent or explicit ``null`` key means the room declares no artwork of
    its own, so a reader can distinguish "not authored" from a key that merely
    happens to match the room id.
    """

    data = fixtures.interior_data()
    data["rooms"]["hall"]["art_key"] = "hall_art"
    data["rooms"]["inner"]["art_key"] = None
    path = fixtures.INTERIOR_PATH.format("demo_interior")

    document = parse_document(path, fixtures.yaml_text(data)).document
    assert document.rooms["hall"].art_key == "hall_art"
    assert document.rooms["inner"].art_key is None

    omitted = fixtures.interior_data()
    reparsed = parse_document(
        path, fixtures.yaml_text(omitted)
    ).document
    assert reparsed.rooms["hall"].art_key is None


def test_an_interior_artwork_key_must_be_an_identifier():
    data = fixtures.interior_data()
    data["rooms"]["hall"]["art_key"] = "Sanctum Art"
    with pytest.raises(AuthoringError) as captured:
        parse_document(
            fixtures.INTERIOR_PATH.format("demo_interior"), fixtures.yaml_text(data)
        )
    assert "invalid_field_value" in {item.code for item in captured.value.diagnostics}


def test_schema_is_machine_readable_and_mutation_isolated():
    first = schema()
    assert first["version"] == 1
    assert set(first["document_kinds"]) == {
        "continent",
        "locations",
        "districts",
        "settlement",
        "interior",
        "layout",
    }
    node_fields = first["document_kinds"]["settlement"]["fields"]["nodes"]["items"][
        "fields"
    ]
    assert {
        "prototype_parent",
        "anchor_key",
        "key",
        "desc",
        "typeclass",
        "scene_archetype",
        "x_m",
        "y_m",
    } <= set(node_fields)
    first["document_kinds"]["settlement"]["fields"]["nodes"]["items"]["fields"][
        "mystery"
    ] = {"type": "str"}
    assert "mystery" not in schema()["document_kinds"]["settlement"]["fields"][
        "nodes"
    ]["items"]["fields"]
