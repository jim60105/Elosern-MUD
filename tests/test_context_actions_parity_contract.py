"""Repository-wide parity contract for the context_actions suggestions section.

The v5 ``context_actions`` panel's ``suggestions`` bounds and enums are shared
between the Python validator in ``web/webclient/presentation/options.py`` and
the JavaScript validator in ``web/static/webclient/js/elosern/protocol.js``.
This contract enforces numerically identical values and identical shared
fragments so a browser never rejects a payload the server considers valid (or
vice versa), mirroring the exploration/services/local_map parity contracts.
"""

from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_OPTIONS = REPO_ROOT / "web/webclient/presentation/options.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

# Numerically identical Python/JS bound pairs for the suggestions section.
_OPTIONS_CONSTANTS = (
    ("MAX_OPTION_CARDS", "MAX_OPTION_CARDS"),
    ("MAX_OPTION_LABEL", "MAX_OPTION_LABEL"),
    ("MAX_OPTION_HINT", "MAX_OPTION_HINT"),
    ("MAX_OPTION_PARAMS", "MAX_OPTION_PARAMS"),
)

# Shared enum/value fragments that must co-exist identically on both sides.
_OPTIONS_FRAGMENTS = (
    '"generating"',
    '"ready"',
    '"degraded"',
    '"unavailable"',
    '"known_action"',
    '"freeform"',
    '"explore.talk_freeform"',
)


class ContextActionsOptionsParityContract(unittest.TestCase):
    @covers_requirement("webclient-context-actions-suggestions::the-v5-client-mirror-and-parity-contract-enforce-the-suggestions-shape")
    def test_python_and_js_option_bounds_are_identical(self):
        py_source = _PY_OPTIONS.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _OPTIONS_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS option bounds diverged")

    def test_python_and_js_share_option_fragments(self):
        py_source = _PY_OPTIONS.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        for fragment in _OPTIONS_FRAGMENTS:
            self.assertIn(fragment, py_source, f"Python options missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")

    def test_python_option_statuses_and_kinds_are_exact(self):
        import ast

        py_source = _PY_OPTIONS.read_text(encoding="utf-8")
        tree = ast.parse(py_source)
        values: dict[str, tuple[str, ...]] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in {"OPTIONS_STATUSES", "OPTIONS_CARD_KINDS"}
                and isinstance(node.value, ast.Tuple)
            ):
                values[node.targets[0].id] = tuple(
                    element.value for element in node.value.elts
                )
        self.assertEqual(
            values["OPTIONS_STATUSES"],
            ("generating", "ready", "degraded", "unavailable"),
        )
        self.assertEqual(
            values["OPTIONS_CARD_KINDS"],
            ("known_action", "freeform"),
        )


if __name__ == "__main__":
    unittest.main()
