"""Repository-wide parity contract for the services panel (webclient-service-menus).

The D4 ``services`` bounds are shared between the Python validator in
``web/webclient/presentation/services.py`` and the JavaScript validator in
``web/static/webclient/js/elosern/protocol.js``. This contract enforces
numerically identical values so a browser never disables a panel the server
considers valid (or vice versa), mirroring the local_map D10a parity contract.
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_SERVICES = REPO_ROOT / "web/webclient/presentation/services.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

_SERVICES_CONSTANTS = (
    ("MAX_BOARD_ROWS", "SERVICES_MAX_BOARD_ROWS"),
    ("MAX_QUEST_ROWS", "SERVICES_MAX_QUEST_ROWS"),
    ("MAX_STOCK_ROWS", "SERVICES_MAX_STOCK_ROWS"),
    ("MAX_SELLABLE_ROWS", "SERVICES_MAX_SELLABLE_ROWS"),
    ("MAX_INVENTORY_ROWS", "SERVICES_MAX_INVENTORY_ROWS"),
    ("MAX_KEY_CODE_POINTS", "SERVICES_MAX_KEY"),
    ("MAX_DISPLAY_NAME_CODE_POINTS", "SERVICES_MAX_DISPLAY_NAME"),
    ("MAX_SUMMARY_CODE_POINTS", "SERVICES_MAX_SUMMARY"),
    ("MAX_DETAIL_CODE_POINTS", "SERVICES_MAX_DETAIL"),
    ("MAX_DEADLINE_LINE_CODE_POINTS", "SERVICES_MAX_DEADLINE_LINE"),
    ("MAX_RANK_KEY_CODE_POINTS", "SERVICES_MAX_RANK_KEY"),
    ("MAX_HOST_DISPLAY_NAME_CODE_POINTS", "SERVICES_MAX_HOST_DISPLAY_NAME"),
    ("MAX_LABEL_CODE_POINTS", "SERVICES_MAX_LABEL"),
    ("MAX_REASON_MESSAGE_CODE_POINTS", "SERVICES_MAX_REASON_MESSAGE"),
    ("MAX_QUANTITY", "SERVICES_MAX_QUANTITY"),
    ("MIN_QUANTITY", "SERVICES_MIN_QUANTITY"),
)


class ServicesValidatorParityContract(unittest.TestCase):
    def test_python_and_js_validators_share_identical_d4_bounds(self):
        py_source = _PY_SERVICES.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _SERVICES_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS services bounds diverged")

    def test_python_and_js_share_quest_states_and_action_ids(self):
        py_source = _PY_SERVICES.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        for fragment in (
            '"in_progress", "completed", "failed"',
            '"guild.register"',
            '"guild.quest_accept"',
            '"guild.quest_abandon"',
            '"guild.quest_turnin"',
            '"guild.exam_start"',
            '"shop.buy"',
            '"shop.sell"',
        ):
            self.assertIn(fragment, py_source, f"Python services missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")


if __name__ == "__main__":
    unittest.main()
