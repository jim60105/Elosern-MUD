"""Repository-wide contracts for map knowledge (map-knowledge-minimap).

Two structural invariants are enforced mechanically so they cannot silently
drift:

- ``world/rules/map_knowledge.py`` is the SOLE writer of the player's
  ``map_knowledge`` attribute. No other first-party module may assign or
  mutate that attribute key, matching the single-writer boundary.
- The D10a ``local_map`` bounds shared by the Python and JavaScript validators
  stay numerically identical, so a browser never disables a panel the server
  considers valid (or vice versa).
"""

import ast
from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
FIRST_PARTY_ROOTS = ("commands", "server", "typeclasses", "web", "world")
KNOWLEDGE_ATTR = "map_knowledge"
SOLE_WRITER = "world/rules/map_knowledge.py"

_PY_LOCAL_MAP = REPO_ROOT / "web/webclient/presentation/local_map.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"


def _iter_py_files() -> list[Path]:
    paths = []
    for root in FIRST_PARTY_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            parts = path.relative_to(REPO_ROOT).parts
            if "__pycache__" in parts:
                continue
            if "/tests/" in "/" + str(path.relative_to(REPO_ROOT)):
                continue
            paths.append(path)
    return paths


class MapKnowledgeSingleWriterContract(unittest.TestCase):
    @covers_requirement("map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record")
    def test_only_map_knowledge_module_writes_the_knowledge_attribute(self):
        offenders = []
        for path in _iter_py_files():
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative == SOLE_WRITER:
                continue
            source = path.read_text(encoding="utf-8")
            for match in re.finditer(
                r"\.attributes\.(add|set|update)\(\s*[\"']map_knowledge[\"']",
                source,
            ):
                offenders.append(f"{relative}:{source.count(chr(10), 0, match.start()) + 1}")
            if re.search(r"\bdb\.map_knowledge\s*=", source) or re.search(
                r"\bmap_knowledge\s*=\s*[^=]", source
            ):
                offenders.append(f"{relative}: direct assignment")
        self.assertEqual(
            offenders, [], "modules other than world/rules/map_knowledge.py write map_knowledge"
        )

    def test_no_presenter_or_adapter_imports_the_write_seam(self):
        # Presenters and adapters may import only the read parser and node-ID
        # helpers, never the write helpers.
        for path in _iter_py_files():
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative.startswith("web/webclient/presentation") or relative.startswith(
                "world/maps"
            ):
                source = path.read_text(encoding="utf-8")
                if re.search(
                    r"from world\.rules\.map_knowledge import .*?(record_arrival|prune_reclaimed_room)",
                    source,
                ):
                    self.fail(f"{relative} imports a map-knowledge write helper")


_LOCAL_MAP_CONSTANTS = (
    ("MAX_NODES", "LOCAL_MAP_MAX_NODES"),
    ("MAX_EDGES", "LOCAL_MAP_MAX_EDGES"),
    ("MAX_LEGEND", "LOCAL_MAP_MAX_LEGEND"),
    ("MAX_STRING_CODE_POINTS", "LOCAL_MAP_MAX_STRING"),
    ("MAX_TITLE_CODE_POINTS", "LOCAL_MAP_MAX_TITLE"),
    ("MAX_NODE_ID_CHARS", "LOCAL_MAP_MAX_NODE_ID"),
    ("MAX_EXIT_REF_CHARS", "LOCAL_MAP_MAX_EXIT_REF"),
    ("COORD_MIN", "LOCAL_MAP_COORD_MIN"),
    ("COORD_MAX", "LOCAL_MAP_COORD_MAX"),
)


class LocalMapValidatorParityContract(unittest.TestCase):
    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_python_and_js_validators_share_identical_d10a_bounds(self):
        py_source = _PY_LOCAL_MAP.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _LOCAL_MAP_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9-]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9-]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS local_map bounds diverged")

    def test_python_and_js_share_visibility_layer_and_action_kind_sets(self):
        py_source = _PY_LOCAL_MAP.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        for py_fragment, js_fragment in (
            ("\"current\", \"visible_unvisited\", \"visible_visited\", \"remembered\"", "LOCAL_MAP_VISIBILITIES"),
            ("\"grid\", \"wilderness\", \"instance\", \"interior\"", "LOCAL_MAP_LAYERS"),
            ("(\"move\",)", "LOCAL_MAP_ACTION_KINDS"),
        ):
            self.assertIn(py_fragment, py_source, f"Python missing {py_fragment!r}")
            self.assertIn(js_fragment, js_source, f"JS missing {js_fragment!r}")


if __name__ == "__main__":
    unittest.main()
