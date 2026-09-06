"""Repository-wide parity contract for the quest_log panel.

The ``quest_log`` bounds are shared between the Python presenter/validator in
``web/webclient/presentation/quest_log.py`` and the JavaScript validator in
``web/static/webclient/js/elosern/protocol.js``. The Python side imports every
bound from its owning module (the services row cap and wire ceilings, the
affordances display-name bound, and the issuer-key grammar length), so this
contract pins the import chain — quest_log.py must reference the canonical
names, never a second literal — and enforces numerically identical JS values
so the client and server validators can never diverge.
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_QUEST_LOG = REPO_ROOT / "web/webclient/presentation/quest_log.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

# (Python owning module, Python constant, JS constant).
_OWNED_BOUNDS = (
    ("web/webclient/presentation/services.py", "MAX_QUEST_ROWS", "QUEST_LOG_MAX_ROWS"),
    ("web/webclient/presentation/objectives.py", "MAX_QUEST_ID_CODE_POINTS", "QUEST_LOG_MAX_QUEST_ID"),
    ("web/webclient/presentation/objectives.py", "MAX_OBJECTIVE_LINE_CODE_POINTS", "QUEST_LOG_MAX_OBJECTIVE_LINE"),
    ("web/webclient/presentation/objectives.py", "MAX_DEADLINE_LINE_CODE_POINTS", "QUEST_LOG_MAX_DEADLINE_LINE"),
    ("web/webclient/presentation/affordances.py", "MAX_DISPLAY_NAME_CODE_POINTS", "QUEST_LOG_MAX_DISPLAY_NAME"),
    ("web/webclient/presentation/services.py", "MAX_KEY_CODE_POINTS", "QUEST_LOG_MAX_KEY"),
    ("web/webclient/presentation/services.py", "MAX_DETAIL_CODE_POINTS", "QUEST_LOG_MAX_DETAIL"),
    ("web/webclient/presentation/services.py", "MAX_LABEL_CODE_POINTS", "QUEST_LOG_MAX_TRACK_LABEL"),
    ("web/webclient/presentation/services.py", "MAX_SUMMARY_CODE_POINTS", "QUEST_LOG_MAX_REWARD_LINE"),
    ("world/rules/quest_issuance.py", "MAX_ISSUER_KEY_LENGTH", "QUEST_LOG_MAX_ISSUER_KEY"),
)

_IMPORT_ANCHORS = (
    r"from web\.webclient\.presentation\.affordances import MAX_DISPLAY_NAME_CODE_POINTS",
    r"from web\.webclient\.presentation\.objectives import \([^)]*MAX_QUEST_ID_CODE_POINTS",
    r"from web\.webclient\.presentation\.objectives import \([^)]*MAX_OBJECTIVE_LINE_CODE_POINTS",
    r"from web\.webclient\.presentation\.objectives import \([^)]*MAX_DEADLINE_LINE_CODE_POINTS",
    r"from web\.webclient\.presentation\.services import \([^)]*MAX_QUEST_ROWS",
    r"from web\.webclient\.presentation\.services import \([^)]*MAX_KEY_CODE_POINTS",
    r"from web\.webclient\.presentation\.services import \([^)]*MAX_DETAIL_CODE_POINTS",
    r"from web\.webclient\.presentation\.services import \([^)]*MAX_LABEL_CODE_POINTS",
    r"from web\.webclient\.presentation\.services import \([^)]*MAX_SUMMARY_CODE_POINTS",
    r"from world\.rules\.quest_issuance import \([^)]*MAX_ISSUER_KEY_LENGTH",
)


class QuestLogValidatorParityContract(unittest.TestCase):
    def _py_source(self, relative: str) -> str:
        return (REPO_ROOT / relative).read_text(encoding="utf-8")

    def test_quest_log_imports_the_canonical_bounds_without_second_literals(self):
        quest_log_source = _QUEST_LOG.read_text(encoding="utf-8")
        missing = [
            anchor
            for anchor in _IMPORT_ANCHORS
            if re.search(anchor, quest_log_source, re.DOTALL) is None
        ]
        self.assertEqual(
            missing,
            [],
            "quest_log.py must import the canonical bounds from their owning modules",
        )

    def test_python_and_js_quest_log_bounds_are_identical(self):
        quest_log_source = _QUEST_LOG.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for module, constant, js_name in _OWNED_BOUNDS:
            py_match = re.search(
                rf"^{constant}\s*=\s*([0-9]+)",
                self._py_source(module),
                re.MULTILINE,
            )
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{module}:{constant}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{constant}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS quest_log bounds diverged")

    def test_alias_values_reach_the_js_constants(self):
        # The alias assignments must exist so a renamed import cannot silently
        # decouple the panel from its owning module while JS keeps the number.
        quest_log_source = _QUEST_LOG.read_text(encoding="utf-8")
        self.assertIsNotNone(
            re.search(
                r"^QUEST_LOG_MAX_ROWS\s*=\s*MAX_QUEST_ROWS",
                quest_log_source,
                re.MULTILINE,
            )
        )

    def test_python_and_js_share_schema_version_one(self):
        quest_log_source = _QUEST_LOG.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        py_match = re.search(
            r"^QUEST_LOG_SCHEMA_VERSION\s*=\s*([0-9]+)", quest_log_source, re.MULTILINE
        )
        js_match = re.search(r"var QUEST_LOG_SCHEMA_VERSION\s*=\s*([0-9]+)", js_source)
        self.assertIsNotNone(py_match)
        self.assertIsNotNone(js_match)
        self.assertEqual(py_match.group(1), js_match.group(1))


if __name__ == "__main__":
    unittest.main()
