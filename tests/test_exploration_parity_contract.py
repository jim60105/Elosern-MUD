"""Repository-wide parity contract for the exploration/character panels.

The D10 ``exploration`` and ``character`` bounds are shared between the Python
validators in ``web/webclient/presentation/exploration.py`` and
``web/webclient/presentation/character.py`` and the JavaScript validators in
``web/static/webclient/js/elosern/protocol.js``. The canonical affordance
vocabulary bounds live in ``web/webclient/presentation/affordances.py`` (the
version-1 panel delegates to it); this contract enforces numerically identical
values so a browser never disables a panel the server considers valid (or
vice versa), mirroring the local_map D10a and services D4 parity contracts.
"""

from pathlib import Path
import re

from tools.protocol_client_source import protocol_client_source
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_EXPLORATION = REPO_ROOT / "web/webclient/presentation/exploration.py"
_PY_AFFORDANCES = REPO_ROOT / "web/webclient/presentation/affordances.py"
_PY_CHARACTER = REPO_ROOT / "web/webclient/presentation/character.py"
_PY_NPC_SERVICES = REPO_ROOT / "world/rules/npc_services.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

# Bounds the exploration panel still owns (look entities are panel-only; the
# disabled-reason message bound is shared by the panel validator).
_EXPLORATION_ONLY_CONSTANTS = (
    ("MAX_LOOK_ENTITIES", "EXPLORATION_MAX_LOOK_ENTITIES"),
    ("MAX_REASON_MESSAGE_CODE_POINTS", "EXPLORATION_MAX_REASON_MESSAGE"),
)

# Bounds owned by the canonical affordance vocabulary, imported by the panel.
_AFFORDANCE_CONSTANTS = (
    ("MAX_MOVE_EXITS", "EXPLORATION_MAX_MOVE_EXITS"),
    ("MAX_LOOK_OBJECTS", "EXPLORATION_MAX_LOOK_OBJECTS"),
    ("MAX_INTERACT_TARGETS", "EXPLORATION_MAX_INTERACT_TARGETS"),
    ("MAX_AFFORDANCES", "EXPLORATION_MAX_AFFORDANCES"),
    ("MAX_EXIT_REF_CHARS", "EXPLORATION_MAX_EXIT_REF"),
    ("MAX_NODE_ID_CHARS", "EXPLORATION_MAX_NODE_ID"),
    ("MAX_DISPLAY_NAME_CODE_POINTS", "EXPLORATION_MAX_DISPLAY_NAME"),
    ("MAX_LABEL_CODE_POINTS", "EXPLORATION_MAX_LABEL"),
)

_CHARACTER_CONSTANTS = (
    ("MAX_TRAIT_ROWS", "CHARACTER_MAX_TRAIT_ROWS"),
    ("MAX_ACTIVE_ROWS", "CHARACTER_MAX_ACTIVE_ROWS"),
    ("MAX_PASSIVE_ROWS", "CHARACTER_MAX_PASSIVE_ROWS"),
    ("MAX_EQUIPMENT_ROWS", "CHARACTER_MAX_EQUIPMENT_ROWS"),
    ("MAX_DISPLAYED_ROWS", "CHARACTER_MAX_DISPLAYED_ROWS"),
    ("MAX_KEY_CODE_POINTS", "CHARACTER_MAX_KEY"),
    ("MAX_LABEL_CODE_POINTS", "CHARACTER_MAX_LABEL"),
    ("MAX_DESCRIPTION_CODE_POINTS", "CHARACTER_MAX_DESCRIPTION"),
    ("MAX_SLOT_CODE_POINTS", "CHARACTER_MAX_SLOT"),
    ("MAX_CONDITION_ROWS", "CHARACTER_MAX_CONDITIONS"),
    ("MAX_CONDITION_LABEL_CODE_POINTS", "CHARACTER_MAX_CONDITION_LABEL"),
    ("MAX_MODIFIER_KEYS", "CHARACTER_MAX_MODIFIER_KEYS"),
    ("MAX_CONDITION_SOURCE_CODE_POINTS", "CHARACTER_MAX_CONDITION_SOURCE"),
    ("MAX_MODIFIER_TEXT_CODE_POINTS", "CHARACTER_MAX_MODIFIER_TEXT"),
    ("MAX_SELECTED_LINEAGE_ROWS", "CHARACTER_MAX_SELECTED_LINEAGE_ROWS"),
    ("MAX_FREEFORM_LADDER_RUNGS", "CHARACTER_MAX_FREEFORM_LADDER_RUNGS"),
)


_EXPLORATION_FRAGMENTS = (
    '"explore.talk_scripted"',
    '"explore.talk_freeform"',
    '"explore.party_invite"',
    '"explore.party_leave"',
    '"explore.engage"',
    '"action"',
    '"navigate"',
    '"npc_persona"',
    '"services"',
    '"entries"',
    '"route"',
)

# The version-5 contextual service vocabulary lives in the projection owner
# (``world/rules/npc_services.py``) since the P cutover removed the coarse
# guild/shop navigation rows from the exploration panel; the client mirror's
# exploration validator repeats the same states, route kinds, sections and the
# one text command a route may pre-fill.
_SERVICE_FRAGMENTS = (
    '"none"',
    '"ready"',
    '"unreadable"',
    '"services"',
    '"dialogue"',
    '"command"',
    '"shop"',
    '"registration"',
    '"board"',
    '"report"',
    '"rank"',
    '"church join"',
)


class ExplorationValidatorParityContract(unittest.TestCase):
    def test_python_and_js_exploration_bounds_are_identical(self):
        py_source = _PY_EXPLORATION.read_text(encoding="utf-8")
        js_source = protocol_client_source()
        mismatches = []
        for py_name, js_name in _EXPLORATION_ONLY_CONSTANTS:
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

    def test_python_and_js_affordance_bounds_are_identical(self):
        py_source = _PY_AFFORDANCES.read_text(encoding="utf-8")
        js_source = protocol_client_source()
        mismatches = []
        for py_name, js_name in _AFFORDANCE_CONSTANTS:
            py_match = re.search(rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE)
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_match is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_match.group(1) != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_match.group(1)} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS affordance bounds diverged")

    def test_python_and_js_character_bounds_are_identical(self):
        py_source = _PY_CHARACTER.read_text(encoding="utf-8")
        js_source = protocol_client_source()
        mismatches = []
        for py_name, js_name in _CHARACTER_CONSTANTS:
            py_match = re.search(
                rf"^{py_name}\s*=\s*([0-9]+)", py_source, re.MULTILINE
            )
            py_value = py_match.group(1) if py_match is not None else None
            js_match = re.search(rf"var {js_name}\s*=\s*([0-9]+)", js_source)
            if py_value is None or js_match is None:
                mismatches.append(f"{py_name}/{js_name}: missing constant")
                continue
            if py_value != js_match.group(1):
                mismatches.append(
                    f"{py_name}={py_value} vs {js_name}={js_match.group(1)}"
                )
        self.assertEqual(mismatches, [], "Python/JS character bounds diverged")

    def test_python_and_js_share_affordance_fragments(self):
        py_source = _PY_EXPLORATION.read_text(encoding="utf-8")
        js_source = protocol_client_source()
        for fragment in _EXPLORATION_FRAGMENTS:
            self.assertIn(fragment, py_source, f"Python exploration missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")

    def test_python_and_js_share_the_contextual_service_vocabulary(self):
        py_source = _PY_NPC_SERVICES.read_text(encoding="utf-8")
        js_source = protocol_client_source()
        for fragment in _SERVICE_FRAGMENTS:
            self.assertIn(fragment, py_source, f"Python services missing {fragment!r}")
            self.assertIn(fragment, js_source, f"JS protocol missing {fragment!r}")

    def test_character_category_group_bound_matches_the_skillcategory_enum(self):
        from world.skills.registry import SkillCategory

        js_source = protocol_client_source()
        js_match = re.search(
            r"var CHARACTER_MAX_CATEGORY_GROUPS\s*=\s*([0-9]+)", js_source
        )
        self.assertIsNotNone(
            js_match, "JS protocol missing CHARACTER_MAX_CATEGORY_GROUPS"
        )
        # One extra slot beyond the member count carries the presentation-only
        # synthetic fallback group for keys absent from SKILL_REGISTRY.
        self.assertEqual(
            int(js_match.group(1)),
            len(SkillCategory) + 1,
            "CHARACTER_MAX_CATEGORY_GROUPS must equal len(SkillCategory) + 1",
        )


if __name__ == "__main__":
    unittest.main()
