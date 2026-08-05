"""Repository-wide parity contract for the exploration/character panels.

The D10 ``exploration`` and ``character`` bounds are shared between the Python
validators in ``web/webclient/presentation/exploration.py`` and
``web/webclient/presentation/character.py`` and the JavaScript validators in
``web/static/webclient/js/elosern/protocol.js``. This contract enforces
numerically identical values so a browser never disables a panel the server
considers valid (or vice versa), mirroring the local_map D10a and services D4
parity contracts.
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_EXPLORATION = REPO_ROOT / "web/webclient/presentation/exploration.py"
_PY_CHARACTER = REPO_ROOT / "web/webclient/presentation/character.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

_EXPLORATION_CONSTANTS = (
    ("MAX_MOVE_EXITS", "EXPLORATION_MAX_MOVE_EXITS"),
    ("MAX_LOOK_ENTITIES", "EXPLORATION_MAX_LOOK_ENTITIES"),
    ("MAX_LOOK_OBJECTS", "EXPLORATION_MAX_LOOK_OBJECTS"),
    ("MAX_INTERACT_TARGETS", "EXPLORATION_MAX_INTERACT_TARGETS"),
    ("MAX_AFFORDANCES", "EXPLORATION_MAX_AFFORDANCES"),
    ("MAX_SCRIPTED_KEYWORDS", "EXPLORATION_MAX_SCRIPTED_KEYWORDS"),
    ("MAX_EXIT_REF_CHARS", "EXPLORATION_MAX_EXIT_REF"),
    ("MAX_NODE_ID_CHARS", "EXPLORATION_MAX_NODE_ID"),
    ("MAX_DISPLAY_NAME_CODE_POINTS", "EXPLORATION_MAX_DISPLAY_NAME"),
    ("MAX_LABEL_CODE_POINTS", "EXPLORATION_MAX_LABEL"),
    ("MAX_KEYWORD_ID_CHARS", "EXPLORATION_MAX_KEYWORD_ID"),
    ("MAX_KEYWORD_LABEL_CODE_POINTS", "EXPLORATION_MAX_KEYWORD_LABEL"),
    ("MAX_REASON_MESSAGE_CODE_POINTS", "EXPLORATION_MAX_REASON_MESSAGE"),
)

_CHARACTER_CONSTANTS = (
    ("MAX_TRAIT_ROWS", "CHARACTER_MAX_TRAIT_ROWS"),
    ("MAX_PASSIVE_ROWS", "CHARACTER_MAX_PASSIVE_ROWS"),
    ("MAX_EQUIPMENT_ROWS", "CHARACTER_MAX_EQUIPMENT_ROWS"),
    ("MAX_DISPLAYED_ROWS", "CHARACTER_MAX_DISPLAYED_ROWS"),
    ("MAX_KEY_CODE_POINTS", "CHARACTER_MAX_KEY"),
    ("MAX_LABEL_CODE_POINTS", "CHARACTER_MAX_LABEL"),
    ("MAX_DESCRIPTION_CODE_POINTS", "CHARACTER_MAX_DESCRIPTION"),
    ("MAX_SLOT_CODE_POINTS", "CHARACTER_MAX_SLOT"),
)

_EXPLORATION_FRAGMENTS = (
    '"explore.talk_scripted"',
    '"explore.talk_freeform"',
    '"explore.engage"',
    '"guild"',
    '"shop"',
    '"action"',
    '"navigate"',
)


class ExplorationValidatorParityContract(unittest.TestCase):
    def test_python_and_js_exploration_bounds_are_identical(self):
        py_source = _PY_EXPLORATION.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _EXPLORATION_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS exploration bounds diverged")

    def test_python_and_js_character_bounds_are_identical(self):
        py_source = _PY_CHARACTER.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _CHARACTER_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS character bounds diverged")

    def test_python_and_js_share_affordance_fragments(self):
        py_source = _PY_EXPLORATION.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        for fragment in _EXPLORATION_FRAGMENTS:
            self.assertIn(fragment, py_source, f"Python exploration missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")


if __name__ == "__main__":
    unittest.main()
