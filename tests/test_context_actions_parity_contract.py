"""Repository-wide parity contract for the context_actions combat panel bounds.

The ``context_actions`` combat payload's shared bounds must be numerically
identical between the Python view in ``world/rules/combat_view.py`` and the
JavaScript validator in ``web/static/webclient/js/elosern/protocol.js``, so a
browser never rejects a payload the server considers valid (or vice versa),
mirroring the exploration/services/local_map parity contracts.
"""

from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement
from tools.protocol_client_source import protocol_client_source

REPO_ROOT = Path(__file__).resolve().parents[1]


class ContextActionsParityContract(unittest.TestCase):
    @covers_requirement("webclient-combat-menu::combat-context-actions-are-an-exact-read-only-panel")
    def test_participant_condition_bound_is_identical(self):
        py_source = (REPO_ROOT / "world/rules/combat_view.py").read_text(encoding="utf-8")
        py_match = re.search(r"^MAX_PARTICIPANT_CONDITIONS\s*=\s*([0-9]+)", py_source, re.MULTILINE)
        js_match = re.search(r"var MAX_PARTICIPANT_CONDITIONS\s*=\s*([0-9]+)", protocol_client_source())
        self.assertIsNotNone(py_match)
        self.assertIsNotNone(js_match)
        self.assertEqual(py_match.group(1), js_match.group(1))
        self.assertEqual(py_match.group(1), "8")


if __name__ == "__main__":
    unittest.main()
