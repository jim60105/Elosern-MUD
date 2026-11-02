"""Synthetic reference-preserving replacement, brief and prose application.

Every fixture is the editor's synthetic workspace: ``synthetic_town`` bound to
``synthetic_place``, with its anchor ``gate``, its node ``yard`` and an interior
doorway and district landmark that name ``yard``. No shipped location, map or
node identifier appears here.

Refused runs compare full tree digests, and accepted runs compare the emitted
node order, the retained identities and every road and gate endpoint. The
nearest-binding distances are recomputed from the printed coordinates rather
than from the resolver's own arithmetic.
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from elosern_map_core import discover_source_documents, load_authoring_world
from elosern_map_core.codec import (
    document_from_data,
    parse_document,
    serialize_document,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"

SETTLEMENT = "synthetic_town"
LOCATION = "synthetic_place"


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name} from {EDITOR_TESTS}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


synthetic = _load("synthetic_workspace")


def _masked(data, node_ids: tuple[str, ...]):
    """One document's data with the listed nodes' key and desc left out."""

    nodes = {
        node_id: {
            field: value
            for field, value in node.items()
            if not (node_id in node_ids and field in ("key", "desc"))
        }
        for node_id, node in data["nodes"].items()
    }
    masked = dict(data)
    masked["nodes"] = nodes
    return masked


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self._root_dir = tempfile.TemporaryDirectory()
        self._aux_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._root_dir.cleanup)
        self.addCleanup(self._aux_dir.cleanup)
        self.root = Path(self._root_dir.name)
        self.aux = Path(self._aux_dir.name)
        synthetic.write_workspace(self.root)
        synthetic.write_reference_context(self.root)
        self.lore = self.aux / "lore.json"
        self.lore.write_text(
            json.dumps({LOCATION: {"nation": None, "population": 200_000}}),
            encoding="utf-8",
        )
        self._bind_count = 0

    def _digest(self) -> dict[str, str]:
        return synthetic.tree_digest(self.root)

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.settlement_synthesis",
                *arguments,
                "--root",
                str(self.root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def _bind(self, rows: dict[str, str]) -> Path:
        self._bind_count += 1
        path = self.aux / f"bind-{self._bind_count}.json"
        path.write_text(json.dumps({"bindings": rows}), encoding="utf-8")
        return path

    def _replace(
        self, rows: dict[str, str], *, plan_only: bool = False
    ) -> subprocess.CompletedProcess[str]:
        arguments = [
            "generate",
            LOCATION,
            "--replace",
            "--bind",
            str(self._bind(rows)),
            "--lore",
            str(self.lore),
        ]
        if plan_only:
            arguments.append("--plan-only")
        return self._run(*arguments)

    def _settlement_path(self) -> Path:
        return self.root / "content" / "maps" / "settlements" / f"{SETTLEMENT}.yaml"

    def _document(self):
        return parse_document(
            f"content/maps/settlements/{SETTLEMENT}.yaml",
            self._settlement_path().read_text(encoding="utf-8"),
        ).document

    def _add_node(self, node_id: str) -> None:
        relative_path = f"content/maps/settlements/{SETTLEMENT}.yaml"
        parsed = parse_document(
            relative_path, self._settlement_path().read_text(encoding="utf-8")
        )
        data = dict(parsed.document.data)
        data["nodes"] = {
            key: dict(value) for key, value in data["nodes"].items()
        }
        data["nodes"][node_id] = {
            "x_m": 100,
            "y_m": 100,
            "prototype_parent": "grid_room",
            "key": "Stray",
            "desc": "",
            "anchor_key": None,
            "typeclass": None,
            "scene_archetype": None,
        }
        self._settlement_path().write_text(
            serialize_document(
                document_from_data(relative_path, data), parsed.round_trip
            ),
            encoding="utf-8",
        )

    def _remove_field(self, field: str) -> None:
        relative_path = f"content/maps/settlements/{SETTLEMENT}.yaml"
        parsed = parse_document(
            relative_path, self._settlement_path().read_text(encoding="utf-8")
        )
        data = dict(parsed.document.data)
        data.pop(field, None)
        self._settlement_path().write_text(
            serialize_document(
                document_from_data(relative_path, data), parsed.round_trip
            ),
            encoding="utf-8",
        )

    def _add_location(
        self,
        location_id: str,
        *,
        display_name_zh: str,
        geographic_constraint: str,
        cell: tuple[int, int],
    ) -> None:
        relative_path = "content/maps/locations.yaml"
        path = self.root / relative_path
        parsed = parse_document(relative_path, path.read_text(encoding="utf-8"))
        data = dict(parsed.document.data)
        data["locations"] = {
            key: dict(value) for key, value in data["locations"].items()
        }
        data["locations"][location_id] = {
            "kind": "town",
            "display_name_zh": display_name_zh,
            "description": "A synthetic neighbour.",
            "cell": {"cell_x": cell[0], "cell_y": cell[1]},
            "geographic_constraint": geographic_constraint,
            "scene_archetype": None,
        }
        path.write_text(
            serialize_document(
                document_from_data(relative_path, data), parsed.round_trip
            ),
            encoding="utf-8",
        )
        lore = json.loads(self.lore.read_text(encoding="utf-8"))
        lore[location_id] = {"nation": None, "population": 5_000}
        self.lore.write_text(json.dumps(lore), encoding="utf-8")


class ReplaceTests(_Workspace):
    def test_missing_protected_binding_is_refused(self) -> None:
        before = self._digest()

        result = self._replace({"gate": "central_plaza"})

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("unbound_protected:yard", result.stderr)
        self.assertEqual(self._digest(), before)

    def test_bound_identities_survive(self) -> None:
        result = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        document = self._document()
        nodes = document.data["nodes"]
        self.assertEqual(nodes["gate"]["key"], "Gate")
        self.assertEqual(nodes["gate"]["desc"], "The way in.")
        self.assertEqual(nodes["gate"]["prototype_parent"], "anchor_room")
        self.assertEqual(nodes["gate"]["anchor_key"], LOCATION)
        self.assertEqual(nodes["yard"]["key"], "Yard")
        self.assertEqual(nodes["yard"]["desc"], synthetic.HOSTILE_DESC)

        anchor = document.anchor_node
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor.node_id, "gate")
        self.assertEqual(report["bound"]["gate"], "central_plaza")
        yard_row = next(row for row in report["slots"] if row["id"] == "yard")
        self.assertIn(yard_row["role"], ("approach", "filler"))
        self.assertIsNotNone(document.city_gate)
        self.assertIn(document.city_gate.node, nodes)

        # The emitted node order is the plan order, not the old authored order.
        self.assertEqual(
            [row["id"] for row in report["slots"]], list(nodes)
        )
        self.assertTrue(report["index_present"])
        self.assertEqual(report["dropped"], [])

        world = load_authoring_world(discover_source_documents(self.root))
        interior = world.interiors[synthetic.INTERIOR_ID]
        self.assertEqual(interior.exterior.settlement, SETTLEMENT)
        self.assertEqual(interior.exterior.node, "yard")
        landmark = world.districts.districts["synthetic_district"].landmark
        self.assertEqual(landmark.domain, "settlement_node")
        self.assertEqual(landmark.map_id, SETTLEMENT)
        self.assertEqual(landmark.object_id, "yard")

        lint = self._run("lint", SETTLEMENT)
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)

    def test_refused_bindings(self) -> None:
        plan = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"},
            plan_only=True,
        )
        self.assertEqual(plan.returncode, 0, plan.stderr)
        filler = next(
            (
                row["id"]
                for row in json.loads(plan.stdout)["slots"]
                if row["role"] == "filler"
            ),
            None,
        )
        self.assertIsNotNone(filler, "the synthetic capital plan has no filler slot")

        cases = {
            "anchor to a filler slot": (
                {"gate": filler, "yard": "nearest:central_plaza"},
                f"anchor_mismatch:{filler}",
            ),
            "two ids on one slot": (
                {"gate": "central_plaza", "yard": "central_plaza"},
                "duplicate_slot:central_plaza",
            ),
            "unknown existing node": (
                {
                    "gate": "central_plaza",
                    "yard": "nearest:central_plaza",
                    "absent": "nearest:central_plaza",
                },
                "unknown_node:absent",
            ),
            "unknown slot": (
                {"gate": "central_plaza", "yard": "no_such_slot"},
                "unknown_slot:yard->no_such_slot",
            ),
        }
        for label, (rows, problem) in cases.items():
            with self.subTest(label):
                before = self._digest()
                result = self._replace(rows)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(problem, result.stderr)
                self.assertEqual(self._digest(), before)

    def test_unreferenced_node_is_dropped_with_an_index(self) -> None:
        self._add_node("stray")
        before = self._digest()

        result = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["dropped"], ["stray"])
        nodes = self._document().data["nodes"]
        self.assertNotIn("stray", nodes)
        self.assertIn("yard", nodes)
        self.assertNotEqual(self._digest(), before)

    def test_missing_index_protects_every_existing_node(self) -> None:
        self._add_node("stray")
        (self.root / "content" / "map-reference-context.json").unlink()
        before = self._digest()

        result = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("unbound_protected:stray", result.stderr)
        self.assertEqual(self._digest(), before)

    def test_stale_index_protects_every_existing_node(self) -> None:
        self._add_node("stray")
        (self.root / "external" / "declarations.txt").write_text(
            "changed after the index was exported\n", encoding="utf-8"
        )
        before = self._digest()

        result = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("unbound_protected:stray", result.stderr)
        self.assertEqual(self._digest(), before)

    def test_optional_fields_follow_the_existing_document(self) -> None:
        self._remove_field("exit_prototype")
        first = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        data = self._document().data
        self.assertNotIn("exit_prototype", data)
        self.assertIn("options", data)

        self._remove_field("options")
        second = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        data = self._document().data
        self.assertNotIn("options", data)
        self.assertNotIn("exit_prototype", data)


class NearestBindingTests(_Workspace):
    def _nearest_rows(self) -> dict[str, str]:
        return {
            "gate": "central_plaza",
            "yard": "nearest:central_plaza",
            "stray_a": "nearest:central_plaza",
        }

    def test_nearest_resolution_and_repeat(self) -> None:
        self._add_node("stray_a")
        original = self._settlement_path().read_bytes()
        rows = self._nearest_rows()

        plan = self._replace(rows, plan_only=True)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        report = json.loads(plan.stdout)
        slots = {row["id"]: row for row in report["slots"]}
        anchor = slots["gate"]

        def distance(row) -> float:
            return math.hypot(
                row["x_m"] - anchor["x_m"], row["y_m"] - anchor["y_m"]
            )

        candidates = sorted(
            distance(row) for row in report["slots"] if row["role"] in ("approach", "filler")
        )
        chosen = sorted((distance(slots["yard"]), distance(slots["stray_a"])))
        self.assertAlmostEqual(chosen[0], candidates[0], places=6)
        self.assertAlmostEqual(chosen[1], candidates[1], places=6)
        self.assertNotEqual(report["bound"]["yard"], report["bound"]["stray_a"])

        first = self._replace(rows)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_bytes = self._settlement_path().read_bytes()

        self._settlement_path().write_bytes(original)
        second = self._replace(rows)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first_bytes, self._settlement_path().read_bytes())

    def test_identifier_collision_takes_the_first_free_suffix(self) -> None:
        self._add_node("market_street")

        result = self._replace(
            {
                "gate": "central_plaza",
                "yard": "nearest:central_plaza",
                "market_street": "nearest:central_plaza",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["renamed_slots"].get("market_street"), "market_street_2")
        identifiers = [row["id"] for row in report["slots"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))

        data = self._document().data
        nodes = data["nodes"]
        self.assertIn("market_street", nodes)
        self.assertIn("market_street_2", nodes)
        for road in data["roads"]:
            self.assertIn(road["source"], nodes)
            self.assertIn(road["destination"], nodes)
        for gate in data["wilderness_entry"]["gates"]:
            self.assertIn(gate["destination_node"], nodes)
        self.assertIn(data["city_gate"]["node"], nodes)


class ProseTests(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        result = self._replace(
            {"gate": "central_plaza", "yard": "nearest:central_plaza"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_brief_is_read_only(self) -> None:
        self._add_location(
            "synthetic_neighbour",
            display_name_zh="鄰鎮",
            geographic_constraint="neighbour-constraint",
            cell=(6, 5),
        )
        before = self._digest()

        result = self._run("brief", SETTLEMENT, "--lore", str(self.lore))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        document = self._document()
        self.assertEqual([row["id"] for row in payload["nodes"]], list(document.nodes))
        fields = {
            "id",
            "key",
            "role",
            "bearing",
            "distance_m",
            "desc_empty",
            "gate_return_direction",
        }
        for row in payload["nodes"]:
            self.assertEqual(set(row), fields)
        anchor = next(row for row in payload["nodes"] if row["id"] == "gate")
        self.assertEqual(anchor["role"], "anchor")
        self.assertIsNone(anchor["bearing"])
        self.assertEqual(anchor["distance_m"], 0.0)
        self.assertIn("settlement_class", payload)
        self.assertIn("morphology", payload)
        self.assertEqual(payload["map_id"], SETTLEMENT)
        self.assertEqual(payload["location_id"], LOCATION)
        self.assertEqual(payload["display_name_zh"], "合成城")
        self.assertEqual(payload["geographic_constraint"], "synthetic")
        neighbour = next(
            row for row in payload["neighbours"] if row["id"] == "synthetic_neighbour"
        )
        self.assertEqual(neighbour["display_name_zh"], "鄰鎮")
        self.assertEqual(self._digest(), before)

    def test_prose_changes_only_the_listed_names_and_descriptions(self) -> None:
        before = self._document().data
        entries = {
            "gate": {"key": "北門", "desc": "城牆下的石門，門洞裡還留著昨夜的火把氣味。"},
            "yard": {"key": "庭園", "desc": "院子裡有一棵老樹，樹蔭下擺著幾張石凳。"},
        }
        prose = self.aux / "prose.json"
        prose.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

        result = self._run("prose", SETTLEMENT, str(prose))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prose: 2 nodes updated", result.stdout)
        after = self._document().data
        for node_id, fields in entries.items():
            self.assertEqual(after["nodes"][node_id]["key"], fields["key"])
            self.assertEqual(after["nodes"][node_id]["desc"], fields["desc"])
        self.assertEqual(_masked(before, ("gate", "yard")), _masked(after, ("gate", "yard")))

    def test_invalid_entries_are_rejected_atomically(self) -> None:
        before = self._settlement_path().read_bytes()
        prose = self.aux / "invalid.json"
        prose.write_text(
            json.dumps(
                {
                    "gate": {"key": "北門", "desc": "城牆下的石門。", "extra": "x"},
                    "absent": {"key": "不存在的節點", "desc": "不存在的描述。"},
                    "yard": {"key": "庭園", "desc": "   "},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = self._run("prose", SETTLEMENT, str(prose))

        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown_node:absent", result.stderr)
        self.assertIn("unexpected_field:gate:extra", result.stderr)
        self.assertIn("empty_desc:yard", result.stderr)
        self.assertEqual(self._settlement_path().read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
