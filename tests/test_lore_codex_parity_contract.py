"""Repository-wide parity contract for the lore_codex panel.

The ``lore_codex`` bounds and category vocabulary are shared between the
Python presenter/validator in ``web/webclient/presentation/lore_codex.py`` and
the JavaScript validator in ``web/static/webclient/js/elosern/protocol.js``.
This contract enforces numerically identical values and exact category mapping
order so the client and server validators can never diverge.
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_LORE_CODEX = REPO_ROOT / "web/webclient/presentation/lore_codex.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

_LORE_CODEX_CONSTANTS = (
    ("LORE_CODEX_SCHEMA_VERSION", "LORE_CODEX_SCHEMA_VERSION"),
    ("LORE_CODEX_MAX_ENTRIES_PER_CATEGORY", "LORE_CODEX_MAX_ENTRIES_PER_CATEGORY"),
    ("LORE_CODEX_MAX_TOTAL_ENTRIES", "LORE_CODEX_MAX_TOTAL_ENTRIES"),
    ("LORE_CODEX_MAX_CARD_FIELDS", "LORE_CODEX_MAX_CARD_FIELDS"),
    ("LORE_CODEX_MAX_KEY_CODE_POINTS", "LORE_CODEX_MAX_KEY_CODE_POINTS"),
    ("LORE_CODEX_MAX_TITLE_CODE_POINTS", "LORE_CODEX_MAX_TITLE_CODE_POINTS"),
    ("LORE_CODEX_MAX_LABEL_CODE_POINTS", "LORE_CODEX_MAX_LABEL_CODE_POINTS"),
    ("LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS", "LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS"),
    ("LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS", "LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS"),
)

_EXPECTED_CATEGORIES = (
    "race",
    "nation",
    "region",
    "monster",
    "element",
    "magic",
    "anchor",
    "guild",
)


class LoreCodexValidatorParityContract(unittest.TestCase):
    def test_python_and_js_lore_codex_bounds_are_identical(self):
        py_source = _PY_LORE_CODEX.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _LORE_CODEX_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS lore_codex bounds diverged")

    def test_python_and_js_share_exact_categories_in_mapping_order(self):
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        match = re.search(
            r"var LORE_CODEX_CATEGORIES\s*=\s*\[([\s\S]*?)\];", js_source
        )
        self.assertIsNotNone(match, "LORE_CODEX_CATEGORIES not found in JS protocol")
        raw_items = match.group(1)
        js_categories = tuple(re.findall(r'"([a-z_]+)"', raw_items))
        self.assertEqual(
            js_categories,
            _EXPECTED_CATEGORIES,
            "JS LORE_CODEX_CATEGORIES does not match canonical mapping order",
        )


if __name__ == "__main__":
    unittest.main()
