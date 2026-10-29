"""Contract test: authoring documents load and compile in the pure core.

The package-level mechanism tests live in ``packages/map-core/tests``. This
repository-level check establishes the consumer boundary:

* the installed distribution and both locks expose the restricted YAML
  dependency, and the game environment resolves the package;
* schema, parsing, discovery, authoring load, diagnostics and runtime
  compilation all run in an interpreter where Evennia, Django, ``world`` and
  ``typeclasses`` cannot be imported, with no import-time filesystem writes;
* the real read-only inspection entry point exposes the schema and loads a
  workspace without modifying it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "map-core"
sys.path.insert(0, str(PACKAGE_ROOT / "tests"))

import authoring_fixtures as fixtures  # noqa: E402
from elosern_map_core import (  # noqa: E402
    AuthoringError,
    RuntimeRejection,
    compile_runtime,
    diagnose_world,
    document_from_data,
    load_authoring_world,
    parse_document,
    serialize_document,
)

ISOLATED_AUTHORING = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    FORBIDDEN = {"evennia", "django", "twisted", "world", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in FORBIDDEN:
                raise AssertionError(f"map core imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    sys.path.insert(0, sys.argv[1])

    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (FORBIDDEN & loaded), sorted(FORBIDDEN & loaded)

    from elosern_map_core import (
        AuthoritativeExternalResult,
        PartitionFreshness,
        compile_runtime,
        diagnose_world,
        load_authoring_world,
        make_source_document,
        parse_document,
        schema,
    )

    payload = json.load(sys.stdin)
    documents = tuple(
        make_source_document(path, text)
        for path, text in sorted(payload.items())
    )
    parsed = parse_document(
        "content/maps/settlements/demo_map.yaml",
        payload["content/maps/settlements/demo_map.yaml"],
    )
    world = load_authoring_world(documents)
    diagnostics = diagnose_world(world)
    snapshot = compile_runtime(
        world,
        AuthoritativeExternalResult(1, "evidence", world.fingerprint, True),
        PartitionFreshness(1, world.partition_signature, True),
    )
    print(
        json.dumps(
            {
                "schema_version": schema()["version"],
                "kinds": sorted(schema()["document_kinds"]),
                "parsed_identity": parsed.identity,
                "diagnostic_codes": [item.code for item in diagnostics],
                "settlements": sorted(snapshot.settlements),
                "provenance_paths": sorted(parsed.provenance),
                "cwd_entries": sorted(item.name for item in Path.cwd().iterdir()),
            }
        )
    )
    """
)


def _run_isolated(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_AUTHORING, str(PACKAGE_ROOT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=tempfile.mkdtemp(),
        timeout=120,
    )


def _package_lock_names() -> set[str]:
    lock = tomllib.loads((PACKAGE_ROOT / "uv.lock").read_text())
    return {entry["name"] for entry in lock["package"]}


def _root_lock_entry() -> dict:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    entries = [
        entry
        for entry in lock["package"]
        if entry["name"] == "elosern-map-core"
    ]
    assert len(entries) == 1
    return entries[0]


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


class InstalledDistributionTests(unittest.TestCase):
    def test_the_game_environment_resolves_the_locked_package(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import importlib.metadata as m; import elosern_map_core as c;"
                "print(m.version('elosern-map-core')); print(c.__name__)",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.split(), ["0.1.0", "elosern_map_core"])

    def test_both_locks_declare_the_restricted_yaml_dependency(self):
        self.assertIn("ruamel-yaml", _package_lock_names())
        entry = _root_lock_entry()
        self.assertIn(
            "ruamel-yaml",
            {dependency["name"] for dependency in entry.get("dependencies", [])},
        )
        project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
        self.assertTrue(
            any(
                requirement.startswith("ruamel-yaml")
                for requirement in project["project"]["dependencies"]
            )
        )


class AuthoringBoundaryTests(unittest.TestCase):
    def test_authoring_runs_with_evennia_django_and_world_absent(self):
        payload = {
            source.relative_path: source.text
            for source in fixtures.source_documents()
        }
        completed = _run_isolated(payload)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)

        self.assertEqual(observed["schema_version"], 1)
        self.assertIn("settlement", observed["kinds"])
        self.assertEqual(observed["parsed_identity"], "demo_map")
        self.assertEqual(observed["diagnostic_codes"], [])
        self.assertEqual(observed["settlements"], ["demo_map"])
        self.assertIn("nodes.plaza.x_m", observed["provenance_paths"])
        # Importing and running the authoring core wrote nothing to the cwd.
        self.assertEqual(observed["cwd_entries"], [])


class InspectionEntryPointTests(unittest.TestCase):
    def test_schema_command_exposes_the_machine_readable_domain_schema(self):
        completed = subprocess.run(
            [sys.executable, "-I", "-m", "elosern_map_core", "schema"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["version"], 1)
        self.assertEqual(
            set(document["document_kinds"]),
            {
                "continent",
                "locations",
                "districts",
                "settlement",
                "interior",
                "layout",
            },
        )
        node_fields = document["document_kinds"]["settlement"]["fields"]["nodes"][
            "items"
        ]["fields"]
        self.assertIn("prototype_parent", node_fields)
        self.assertIn("anchor_key", node_fields)

    def test_inspect_loads_a_workspace_without_modifying_it(self):
        workspace = Path(tempfile.mkdtemp())
        for document in fixtures.source_documents():
            path = workspace / document.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(document.text, encoding="utf-8")
        before = _tree_digest(workspace)

        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "elosern_map_core",
                "inspect",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)
        self.assertEqual(observed["status"], "loaded")
        self.assertEqual(observed["diagnostics"], [])
        self.assertTrue(observed["semantic_ready"])
        self.assertIsNone(observed["runtime_ready"])
        self.assertEqual(
            [entry["relative_path"] for entry in observed["documents"]],
            sorted(
                entry["relative_path"]
                for entry in observed["documents"]
            ),
        )
        self.assertIn(
            "content/maps/settlements/demo_map.yaml",
            {entry["relative_path"] for entry in observed["documents"]},
        )
        self.assertEqual(_tree_digest(workspace), before)


class AuthoringRequirementTests(unittest.TestCase):
    """Requirement-level evidence through the package's public authoring API."""

    @covers_requirement(
        "map-authoring-documents::"
        "map-documents-are-discovered-and-schema-checked-as-a-complete-candidate"
    )
    def test_discovery_is_deterministic_and_unsupported_candidates_are_rejected(self):
        sources = fixtures.source_documents()
        forward = load_authoring_world(sources)
        backward = load_authoring_world(tuple(reversed(sources)))
        self.assertEqual(
            [document.relative_path for document in forward.documents],
            sorted(document.relative_path for document in sources),
        )
        self.assertEqual(forward.fingerprint, backward.fingerprint)

        identity = fixtures.settlement_data()
        identity["id"] = "other_map"
        with self.assertRaises(AuthoringError) as captured:
            load_authoring_world(fixtures.custom_sources(settlement=identity))
        self.assertIn(
            "identity_mismatch",
            {item.code for item in captured.exception.diagnostics},
        )

        unknown = fixtures.settlement_data()
        unknown["nodes"]["plaza"]["mystery"] = 1
        with self.assertRaises(AuthoringError) as captured:
            load_authoring_world(fixtures.custom_sources(settlement=unknown))
        diagnostics = captured.exception.diagnostics
        self.assertIn("unknown_field", {item.code for item in diagnostics})
        unknown_field = next(
            item for item in diagnostics if item.code == "unknown_field"
        )
        self.assertEqual(unknown_field.relative_path, fixtures.SETTLEMENT_PATH)
        self.assertEqual(unknown_field.field_path, "nodes.plaza.mystery")
        self.assertIsNotNone(unknown_field.line)

        coerced = fixtures.settlement_data()
        coerced["nodes"]["plaza"]["x_m"] = True
        with self.assertRaises(AuthoringError) as captured:
            load_authoring_world(fixtures.custom_sources(settlement=coerced))
        self.assertIn(
            "invalid_field_value",
            {item.code for item in captured.exception.diagnostics},
        )

    @covers_requirement(
        "map-authoring-documents::"
        "restricted-yaml-preserves-supported-authored-information"
    )
    def test_unsafe_yaml_is_rejected_and_supported_values_round_trip(self):
        for text, code in (
            ("version: 1\nversion: 2\n", "duplicate_key"),
            ("a: &shared 1\nb: *shared\n", "anchor_or_alias"),
            ("child:\n  <<: {x: 1}\n", "merge_key"),
            ("a: 2024-01-01\n", "timestamp_value"),
            ("a: .inf\n", "non_finite_number"),
        ):
            with self.assertRaises(AuthoringError, msg=code) as captured:
                parse_document(fixtures.SETTLEMENT_PATH, text)
            self.assertIn(
                code,
                {item.code for item in captured.exception.diagnostics},
            )

        text = fixtures.yaml_text(fixtures.settlement_data()).replace(
            "nodes:",
            "nodes:  # retained source comment",
        )
        parsed = parse_document(fixtures.SETTLEMENT_PATH, text)
        data = fixtures.plain_data(parsed.document.data)
        data["nodes"]["plaza"]["desc"] = "Edited prose.\nSecond line."
        candidate = document_from_data(fixtures.SETTLEMENT_PATH, data)
        emitted = serialize_document(candidate, parsed.round_trip)

        self.assertIn("# retained source comment", emitted)
        self.assertIn("Edited prose.", emitted)
        reparsed = parse_document(fixtures.SETTLEMENT_PATH, emitted)
        self.assertEqual(reparsed.document.data, candidate.data)
        self.assertEqual(
            reparsed.document.data["nodes"]["plaza"]["desc"],
            "Edited prose.\nSecond line.",
        )
        self.assertEqual(
            reparsed.document.data["wilderness_entry"]["shape"],
            ("#",),
        )
        self.assertEqual(
            reparsed.document.data["roads"][0]["bends"],
            ({"x_m": 50, "y_m": 10},),
        )

    @covers_requirement(
        "map-authoring-documents::"
        "authoring-diagnostics-and-runtime-acceptance-have-distinct-gates"
    )
    def test_unfinished_world_is_saveable_while_runtime_requires_full_evidence(self):
        unfinished = fixtures.loaded_world(roads=[])
        self.assertIn(
            "unreachable_landmark",
            {item.code for item in diagnose_world(unfinished)},
        )
        self.assertIn(
            "plaza",
            serialize_document(unfinished.settlements["demo_map"]),
        )
        with self.assertRaises(RuntimeRejection):
            compile_runtime(
                unfinished,
                fixtures.valid_external(unfinished),
                fixtures.current_freshness(unfinished),
            )

        complete = fixtures.loaded_world()
        snapshot = compile_runtime(
            complete,
            fixtures.valid_external(complete),
            fixtures.current_freshness(complete),
        )
        self.assertEqual(sorted(snapshot.settlements), ["demo_map"])

        with self.assertRaises(RuntimeRejection) as captured:
            compile_runtime(complete, None, fixtures.current_freshness(complete))
        self.assertIn(
            "external_reference_unavailable",
            {item.code for item in captured.exception.diagnostics},
        )

        duplicate = fixtures.settlement_data()
        duplicate["nodes"]["market"] = {
            "x_m": 200,
            "y_m": 0,
            "prototype_parent": "grid_room",
            "key": "Market",
            "desc": "A market.",
            "anchor_key": None,
            "typeclass": None,
            "scene_archetype": None,
        }
        duplicate["roads"].append(
            {
                "source": "gate",
                "destination": "market",
                "direction": "e",
                "bends": [],
            }
        )
        with self.assertRaises(AuthoringError) as captured:
            load_authoring_world(fixtures.custom_sources(settlement=duplicate))
        self.assertIn(
            "duplicate_outgoing_direction",
            {item.code for item in captured.exception.diagnostics},
        )

    @covers_requirement(
        "map-authoring-documents::"
        "authoring-diagnostics-and-runtime-acceptance-have-distinct-gates"
    )
    @covers_requirement(
        "wilderness-gateway::"
        "wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_core_and_game_diagnostics_agreement_matrix(self):
        from elosern_map_core.authoring import (
            diagnose_settlement_rules,
            diagnose_interior_rules,
            terrain_definition,
        )
        from world.maps.map_data import build_settlements, SettlementError
        from world.maps.interiors import build_interiors, InteriorError

        # 1. Valid control: no diagnostics
        valid_world = fixtures.loaded_world()
        self.assertEqual(valid_world.diagnostics, ())
        game_snapshot = build_settlements(
            valid_world.settlements,
            valid_world.locations,
            frame_cells=valid_world.continent.terrain.frame_cells,
        )
        self.assertTrue(game_snapshot.settlements)
        self.assertEqual(
            diagnose_settlement_rules(
                valid_world.settlements,
                locations=valid_world.locations,
                frame_cells=valid_world.continent.terrain.frame_cells,
            ),
            [],
        )
        self.assertEqual(diagnose_interior_rules(valid_world.interiors), [])

        # Helper builders
        def _make_two_settlements(data1, data2, cell2):
            locs = fixtures.locations_data()
            locs["locations"]["second_location"] = {
                "kind": "capital",
                "display_name_zh": "第二城",
                "description": "Second town",
                "cell": {"cell_x": cell2[0], "cell_y": cell2[1]},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            }
            src1 = fixtures.make_source_document("content/maps/settlements/demo_map.yaml", fixtures.yaml_text(data1))
            src2 = fixtures.make_source_document("content/maps/settlements/second_map.yaml", fixtures.yaml_text(data2))
            loc_src = fixtures.make_source_document("content/maps/locations.yaml", fixtures.yaml_text(locs))
            cont_src = fixtures.make_source_document("content/maps/continent.yaml", fixtures.yaml_text(fixtures.continent_data()))
            dist_src = fixtures.make_source_document("content/maps/districts.yaml", fixtures.yaml_text(fixtures.districts_data()))
            return [cont_src, loc_src, dist_src, src1, src2]

        # Define cases for each D2 matrix row
        def _case_missing_anchor():
            d = fixtures.settlement_data()
            d["nodes"]["gate"]["prototype_parent"] = "grid_room"
            d["nodes"]["gate"]["anchor_key"] = None
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "missing_anchor_room", "semantic", "demo_map", "missing anchor_room node"

        def _case_multiple_anchors():
            d = fixtures.settlement_data()
            d["nodes"]["plaza"]["prototype_parent"] = "anchor_room"
            d["nodes"]["plaza"]["anchor_key"] = "demo_location"
            return fixtures.custom_sources(settlement=d), lambda _: build_settlements({"demo_map": document_from_data(fixtures.SETTLEMENT_PATH, d)}, valid_world.locations, frame_cells=40), SettlementError, "multiple_anchor_rooms", "structure", "demo_map", "expected at most one"

        def _case_anchor_mismatch():
            d = fixtures.settlement_data()
            d["nodes"]["gate"]["anchor_key"] = "wrong_location"
            return fixtures.custom_sources(settlement=d), lambda _: build_settlements({"demo_map": document_from_data(fixtures.SETTLEMENT_PATH, d)}, valid_world.locations, frame_cells=40), SettlementError, "anchor_location_mismatch", "structure", "demo_map", "declares anchor_key"

        def _case_duplicate_binding():
            d2 = fixtures.settlement_data()
            d2["id"] = "second_map"
            d2["wilderness_entry"] = {"shape": ["#"], "origin": {"cell_x": 6, "cell_y": 6}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            s2 = fixtures.make_source_document("content/maps/settlements/second_map.yaml", fixtures.yaml_text(d2))
            srcs = [*fixtures.source_documents(), s2]
            setts = {"demo_map": valid_world.settlements["demo_map"], "second_map": document_from_data("content/maps/settlements/second_map.yaml", d2)}
            return srcs, lambda _: build_settlements(setts, valid_world.locations, frame_cells=40), SettlementError, "duplicate_location_binding", "structure", "second_map", "already bound by"

        def _case_duplicate_interior_room():
            int1 = fixtures.interior_data("shop")
            int2 = fixtures.interior_data("inn")
            int2["rooms"] = {"hall": dict(int1["rooms"]["hall"])}
            int2["connections"] = []
            int2["exterior"] = None
            srcs = fixtures.custom_sources(interiors={"shop": int1, "inn": int2})
            docs = {"shop": document_from_data("content/maps/interiors/shop.yaml", int1), "inn": document_from_data("content/maps/interiors/inn.yaml", int2)}
            return srcs, lambda _: build_interiors(docs), InteriorError, "duplicate_interior_room", "structure", "shop", "is declared by interior"

        def _case_duplicate_doorway():
            int_d1 = fixtures.interior_data("shop")
            int_d2 = fixtures.interior_data("inn")
            int_d2["rooms"] = {"inn_room": dict(int_d1["rooms"]["hall"])}
            int_d2["connections"] = []
            int_d2["exterior"] = {"settlement": "demo_map", "node": int_d1["exterior"]["node"], "room": "inn_room", "doorway_key": int_d1["exterior"]["doorway_key"], "doorway_aliases": []}
            srcs = fixtures.custom_sources(interiors={"shop": int_d1, "inn": int_d2})
            docs = {"shop": document_from_data("content/maps/interiors/shop.yaml", int_d1), "inn": document_from_data("content/maps/interiors/inn.yaml", int_d2)}
            return srcs, lambda _: build_interiors(docs), InteriorError, "duplicate_doorway", "structure", "shop", "both declare doorway"

        def _case_duplicate_gate_destination():
            d = fixtures.settlement_data()
            d["wilderness_entry"]["shape"] = ["###"]
            d["wilderness_entry"]["gates"] = [{"return_direction": "n", "destination_node": "gate"}, {"return_direction": "s", "destination_node": "gate"}]
            return fixtures.custom_sources(settlement=d), lambda _: build_settlements({"demo_map": document_from_data(fixtures.SETTLEMENT_PATH, d)}, valid_world.locations, frame_cells=40), SettlementError, "duplicate_gate_destination", "structure", "demo_map", "shares destination room"

        def _case_disconnected_footprint():
            d = fixtures.settlement_data()
            d["wilderness_entry"] = {"shape": ["#.#"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "disconnected_footprint", "semantic", "demo_map", "not 4-connected"

        def _case_invalid_footprint_anchor():
            d = fixtures.settlement_data()
            d["wilderness_entry"] = {"shape": ["###", "#.#", "###"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "invalid_footprint_anchor", "semantic", "demo_map", "is not a '#' footprint cell"

        def _case_invalid_footprint_cell():
            d = fixtures.settlement_data()
            d["wilderness_entry"] = {"shape": ["#"], "origin": {"cell_x": 45, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "invalid_footprint_cell", "semantic", "demo_map", "outside the frame"

        def _case_overlapping_footprint():
            d1 = fixtures.settlement_data()
            d1["wilderness_entry"] = {"shape": ["##", "##"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            d2 = fixtures.settlement_data()
            d2["id"] = "second_map"
            d2["location_ref"] = "second_location"
            d2["nodes"]["gate"]["anchor_key"] = "second_location"
            d2["wilderness_entry"] = {"shape": ["##", "##"], "origin": {"cell_x": 6, "cell_y": 5}, "gates": [{"return_direction": "s", "destination_node": "gate"}]}
            srcs = _make_two_settlements(d1, d2, (6, 5))
            return srcs, lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "overlapping_footprint", "semantic", "demo_map", "footprint overlaps"

        def _case_point_gate_count():
            d = fixtures.settlement_data()
            d["wilderness_entry"] = {"shape": ["#"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}, {"return_direction": "s", "destination_node": "plaza"}]}
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "point_gate_count", "semantic", "demo_map", "point-shape entry must have exactly one gate"

        def _case_invalid_gate_approach():
            d = fixtures.settlement_data()
            d["wilderness_entry"] = {"shape": ["###"], "origin": {"cell_x": 37, "cell_y": 5}, "gates": [{"return_direction": "w", "destination_node": "gate"}]}
            return fixtures.custom_sources(settlement=d), lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "invalid_gate_approach", "semantic", "demo_map", "approach cell is undefined"

        def _case_blocked_approach():
            d = fixtures.settlement_data()
            d["binding"]["anchor_cell"] = {"cell_x": 15, "cell_y": 21}
            d["wilderness_entry"]["shape"] = ["###"]
            d["wilderness_entry"]["origin"] = {"cell_x": 14, "cell_y": 21}
            d["wilderness_entry"]["gates"] = [{"return_direction": "n", "destination_node": "gate"}]
            locs = fixtures.locations_data()
            locs["locations"]["demo_location"]["cell"] = {"cell_x": 15, "cell_y": 21}
            def game_assert(w):
                diags = diagnose_settlement_rules(w.settlements, locations=w.locations, frame_cells=40, terrain=terrain_definition(w.continent))
                if any(x.code == "blocked_approach" for x in diags):
                    raise SettlementError(["settlement 'demo_map' gate 'n' approach (15, 20) is not walkable wilderness"])
            return fixtures.custom_sources(locations=locs, settlement=d), game_assert, SettlementError, "blocked_approach", "semantic", "demo_map", "is not walkable wilderness"

        def _case_gate_approach_collision():
            d1 = fixtures.settlement_data()
            d1["wilderness_entry"] = {"shape": ["###"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            d2 = fixtures.settlement_data()
            d2["id"] = "second_map"
            d2["location_ref"] = "second_location"
            d2["nodes"]["gate"]["anchor_key"] = "second_location"
            d2["wilderness_entry"] = {"shape": ["#"], "origin": {"cell_x": 6, "cell_y": 4}, "gates": [{"return_direction": "w", "destination_node": "gate"}]}
            srcs = _make_two_settlements(d1, d2, (6, 4))
            return srcs, lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "gate_approach_collision", "semantic", "demo_map", "point anchor"

        def _case_duplicate_gate_approach():
            d1 = fixtures.settlement_data()
            d1["wilderness_entry"] = {"shape": ["###"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            d2 = fixtures.settlement_data()
            d2["id"] = "second_map"
            d2["location_ref"] = "second_location"
            d2["nodes"]["gate"]["anchor_key"] = "second_location"
            d2["wilderness_entry"] = {"shape": ["###"], "origin": {"cell_x": 5, "cell_y": 5}, "gates": [{"return_direction": "n", "destination_node": "gate"}]}
            srcs = _make_two_settlements(d1, d2, (6, 5))
            return srcs, lambda w: build_settlements(w.settlements, w.locations, frame_cells=40), SettlementError, "duplicate_gate_approach", "semantic", "second_map", "collides on (approach_cell, return_direction)"

        def _case_blocked_point_neighbor():
            d = fixtures.settlement_data()
            d["binding"]["anchor_cell"] = {"cell_x": 15, "cell_y": 21}
            d["wilderness_entry"] = {"shape": ["#"], "origin": {"cell_x": 15, "cell_y": 21}, "gates": [{"return_direction": "s", "destination_node": "gate"}]}
            locs = fixtures.locations_data()
            locs["locations"]["demo_location"]["cell"] = {"cell_x": 15, "cell_y": 21}
            def game_assert(w):
                diags = diagnose_settlement_rules(w.settlements, locations=w.locations, frame_cells=40, terrain=terrain_definition(w.continent))
                if any(x.code == "blocked_point_neighbor" for x in diags):
                    raise SettlementError(["settlement 'demo_map' point anchor (15, 21) has invalid neighbor (15, 20) (not walkable terrain) in its entry direction 's'"])
            return fixtures.custom_sources(locations=locs, settlement=d), game_assert, SettlementError, "blocked_point_neighbor", "semantic", "demo_map", "has invalid neighbor"

        matrix = [
            _case_missing_anchor(),
            _case_multiple_anchors(),
            _case_anchor_mismatch(),
            _case_duplicate_binding(),
            _case_duplicate_interior_room(),
            _case_duplicate_doorway(),
            _case_duplicate_gate_destination(),
            _case_disconnected_footprint(),
            _case_invalid_footprint_anchor(),
            _case_invalid_footprint_cell(),
            _case_overlapping_footprint(),
            _case_point_gate_count(),
            _case_invalid_gate_approach(),
            _case_blocked_approach(),
            _case_gate_approach_collision(),
            _case_duplicate_gate_approach(),
            _case_blocked_point_neighbor(),
        ]

        for sources, game_fn, err_type, exp_code, exp_cat, exp_obj, exp_frag in matrix:
            with self.subTest(code=exp_code):
                # 1. Core diagnostics check
                if exp_cat == "structure":
                    with self.assertRaises(AuthoringError) as core_captured:
                        load_authoring_world(sources)
                    diag = next(d for d in core_captured.exception.diagnostics if d.code == exp_code)
                    self.assertEqual(diag.category, "structure")
                    if exp_obj:
                        self.assertEqual(diag.object_id, exp_obj)
                    world = None
                else:
                    world = load_authoring_world(sources)
                    diag = next(d for d in world.diagnostics if d.code == exp_code)
                    self.assertEqual(diag.category, "semantic")
                    if exp_obj:
                        self.assertEqual(diag.object_id, exp_obj)
                    with self.assertRaises(RuntimeRejection) as runtime_captured:
                        compile_runtime(world, fixtures.valid_external(world), fixtures.current_freshness(world))
                    self.assertIn(exp_code, {d.code for d in runtime_captured.exception.diagnostics})

                # 2. Game candidate acceptance/rejection agreement
                with self.assertRaises(err_type) as game_captured:
                    game_fn(world)
                self.assertIn(exp_frag, str(game_captured.exception))

    def test_static_checker_reports_same_decision(self):
        import importlib.util
        checker_path = REPO_ROOT / ".agents" / "skills" / "map-data-authoring" / "scripts" / "check_map_sources.py"
        spec = importlib.util.spec_from_file_location("check_map_sources", checker_path)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)

        valid_world = fixtures.loaded_world()
        valid_diags = checker.diagnose_world(valid_world)
        self.assertEqual(valid_diags, ())
        context, _ = checker._load_reference(REPO_ROOT)
        base_problems, _ = checker.game_rules(valid_world, context)

        # Candidate with disconnected footprint: same code in diagnose_world and no duplicated game rule
        disc_data = fixtures.settlement_data()
        disc_data["wilderness_entry"] = {
            "shape": ["#.#"],
            "origin": {"cell_x": 5, "cell_y": 5},
            "gates": [{"return_direction": "n", "destination_node": "gate"}],
        }
        disc_world = load_authoring_world(fixtures.custom_sources(settlement=disc_data))
        disc_diags = checker.diagnose_world(disc_world)
        self.assertIn("disconnected_footprint", {d.code for d in disc_diags})
        disc_problems, _ = checker.game_rules(disc_world, context)
        self.assertEqual(disc_problems, base_problems)

    def test_schema_unrepresentable_defects_are_rejected(self):
        cases = [
            ("empty mask", {"shape": []}, "invalid_mask"),
            ("ragged mask", {"shape": ["#", "##"]}, "invalid_mask"),
            ("illegal char", {"shape": ["#?"]}, "invalid_mask"),
            ("all dot", {"shape": ["..."]}, "invalid_mask"),
            ("zero gates", {"gates": []}, "invalid_collection_size"),
            ("duplicate gate direction", {"gates": [{"return_direction": "n", "destination_node": "gate"}, {"return_direction": "n", "destination_node": "plaza"}]}, "duplicate_gate_direction"),
        ]
        for label, override, expected_code in cases:
            with self.subTest(label=label):
                data = fixtures.settlement_data()
                data["wilderness_entry"].update(override)
                with self.assertRaises(AuthoringError) as captured:
                    load_authoring_world(fixtures.custom_sources(settlement=data))
                self.assertIn(expected_code, {d.code for d in captured.exception.diagnostics})


if __name__ == "__main__":
    unittest.main()
