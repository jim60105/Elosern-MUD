"""Repository-wide parity contract for the creation panel (webclient-character-creation-ui).

The D2 ``creation`` bounds are shared between the Python validator in
``web/webclient/presentation/creation.py`` and the JavaScript validator in
``web/static/webclient/js/elosern/protocol.js``. This contract enforces
numerically identical values so a browser never disables a panel the server
considers valid (or vice versa), mirroring the services/local_map parity
contracts.
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_CREATION = REPO_ROOT / "web/webclient/presentation/creation.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

_CREATION_CONSTANTS = (
    ("MAX_PRESETS", "CREATION_MAX_PRESETS"),
    ("MAX_RACES", "CREATION_MAX_RACES"),
    ("MAX_SUBRACES", "CREATION_MAX_SUBRACES"),
    ("MAX_PROFILES", "CREATION_MAX_PROFILES"),
    ("MIN_NAME_LENGTH", "CREATION_MIN_NAME_LENGTH"),
    ("MAX_NAME_LENGTH", "CREATION_MAX_NAME_LENGTH"),
    ("AGE_MINIMUM", "CREATION_AGE_MINIMUM"),
    ("AGE_MAXIMUM", "CREATION_AGE_MAXIMUM"),
    ("APPARENT_AGE_MINIMUM", "CREATION_APPARENT_AGE_MINIMUM"),
    ("APPARENT_AGE_MAXIMUM", "CREATION_APPARENT_AGE_MAXIMUM"),
    ("MAX_PRESET_KEY_CODE_POINTS", "CREATION_MAX_PRESET_KEY"),
    ("MAX_DISPLAY_NAME_CODE_POINTS", "CREATION_MAX_DISPLAY_NAME"),
    ("MAX_RACE_KEY_CODE_POINTS", "CREATION_MAX_RACE_KEY"),
    ("MAX_DESCRIPTION_CODE_POINTS", "CREATION_MAX_DESCRIPTION"),
    ("MAX_EMPHASIS_CODE_POINTS", "CREATION_MAX_EMPHASIS"),
    ("MAX_BACKGROUND_CODE_POINTS", "CREATION_MAX_BACKGROUND"),
    ("MAX_SUBRACE_KEY_CODE_POINTS", "CREATION_MAX_SUBRACE_KEY"),
    ("MAX_SPECIALTY_CODE_POINTS", "CREATION_MAX_SPECIALTY"),
    ("MAX_LABEL_CODE_POINTS", "CREATION_MAX_LABEL"),
    ("MAX_EXPLANATION_CODE_POINTS", "CREATION_MAX_EXPLANATION"),
    ("MAX_AFFINITY_CHOICES", "CREATION_MAX_AFFINITY_ELEMENTS"),
)


class CreationValidatorParityContract(unittest.TestCase):
    def test_python_and_js_validators_share_identical_d2_bounds(self):
        py_source = _PY_CREATION.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for py_name, js_name in _CREATION_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS creation bounds diverged")

    def test_python_and_js_share_axes_and_stages(self):
        py_source = _PY_CREATION.read_text(encoding="utf-8")
        py_wizard = (REPO_ROOT / "world/rules/creation_wizard.py").read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        for fragment in ('"hp", "mp", "sp", "atk_phys", "agility", "defense"',):
            self.assertIn(fragment, py_source, f"Python creation missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")
        for fragment in ('"preset_selected"', '"custom_filled"', '"concept_filled"'):
            self.assertIn(fragment, py_wizard, f"Python wizard missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")

    def test_concept_and_persona_bounds_are_shared_across_the_boundaries(self):
        # The concept input bound and the persona field cap are duplicated at
        # every boundary they cross: the wire adapter, the Telnet command, the
        # generative layer, the deterministic wizard, and the JS validator.
        # This contract keeps them numerically identical so an over-bound
        # concept can never be accepted by one surface and rejected by another.
        sources = {
            "adapter": (REPO_ROOT / "web/webclient/actions/creation_actions.py",
                        r"^MAX_CONCEPT_CODE_POINTS\s*=\s*([0-9]+)"),
            "command": (REPO_ROOT / "commands/character_creation.py",
                        r"^MAX_CONCEPT_LENGTH\s*=\s*([0-9]+)"),
            "layer": (REPO_ROOT / "world/ai/character_creation.py",
                      r"^MAX_CONCEPT_LENGTH\s*=\s*([0-9]+)"),
            "wizard": (REPO_ROOT / "world/rules/character_creation.py",
                       r"^MAX_PERSONA_FIELD_LENGTH\s*=\s*([0-9]+)"),
            "layer persona": (REPO_ROOT / "world/ai/character_creation.py",
                              r"^MAX_PERSONA_FIELD_LENGTH\s*=\s*([0-9]+)"),
            "js": (_JS_PROTOCOL, r"var CREATION_MAX_CONCEPT\s*=\s*([0-9]+)"),
        }
        values = {}
        for label, (path, pattern) in sources.items():
            match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
            self.assertIsNotNone(match, f"{label}: missing constant {pattern!r}")
            values[label] = match.group(1)
        self.assertEqual(values["adapter"], values["command"])
        self.assertEqual(values["adapter"], values["layer"])
        self.assertEqual(values["adapter"], values["js"])
        self.assertEqual(values["adapter"], "500")
        self.assertEqual(values["wizard"], values["layer persona"])
        self.assertEqual(values["wizard"], "600")

    def test_custom_draft_background_bound_matches_the_persona_field_cap(self):
        # The custom/concept draft background travels in the wire draft and is
        # validated by the Python presenter against the persona field cap; the
        # JS validator must use the same numeric bound (not the preset-card
        # prose bound, which is smaller).
        py_source = (REPO_ROOT / "world/rules/character_creation.py").read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        py_match = re.search(r"^MAX_PERSONA_FIELD_LENGTH\s*=\s*([0-9]+)", py_source, re.MULTILINE)
        js_match = re.search(r"var CREATION_MAX_PERSONA_BACKGROUND\s*=\s*([0-9]+)", js_source)
        self.assertIsNotNone(py_match, "Python MAX_PERSONA_FIELD_LENGTH missing")
        self.assertIsNotNone(js_match, "JS CREATION_MAX_PERSONA_BACKGROUND missing")
        self.assertEqual(py_match.group(1), js_match.group(1))
        self.assertEqual(js_match.group(1), "600")

    def test_panel_allowlist_contains_creation_v1(self):
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        self.assertIn("creation: 1", js_source)

    def test_affinity_race_maxima_match_the_deterministic_bound_mapping(self):
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        match = re.search(
            r"var CREATION_AFFINITY_MAXIMUMS\s*=\s*\{([^}]*)\}", js_source
        )
        self.assertIsNotNone(match, "JS affinity maxima mapping missing")
        pairs = re.findall(r"(\w+)\s*:\s*(\d+)", match.group(1))
        py_source = (
            REPO_ROOT / "world/rules/character_creation.py"
        ).read_text(encoding="utf-8")
        py_match = re.search(
            r"_AFFINITY_INPUT_BOUNDS:\s*dict\[str, int\]\s*=\s*\{(.*?)\}",
            py_source,
            re.DOTALL,
        )
        self.assertIsNotNone(py_match, "Python affinity bound mapping missing")
        py_pairs = re.findall(r"\"(\w+)\":\s*(\d+)", py_match.group(1))
        self.assertEqual(
            {race: int(value) for race, value in pairs},
            {race: int(value) for race, value in py_pairs},
        )
        self.assertEqual(
            {race: int(value) for race, value in py_pairs},
            {"human": 2, "beastfolk": 1, "elf": 0},
        )
        py_creation = (REPO_ROOT / "web/webclient/presentation/creation.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("max_affinity_elements", py_creation)
        # The JS validator derives its descriptor bound from the same mapping.
        self.assertIn("CREATION_AFFINITY_MAXIMUMS", js_source)


if __name__ == "__main__":
    unittest.main()
