"""Repository-wide schema-version parity contract for all registered OOB panels.

Each panel's wire schema version is defined in four places that must never
diverge: the presenter module's ``<PANEL>_SCHEMA_VERSION`` constant, the
production registry's ``schema_version=<CONST>`` registration reference, the
client ``PANEL_ALLOWLIST`` mirror in ``protocol.js``, and the client's
per-panel available-form re-check value (a literal or a reference to the
mirrored top-level constant). This contract extracts all four
from source text (top-level discovery runs without Evennia settings, so game
modules cannot be imported here) and asserts they are numerically equal,
mirroring the existing bounds parity contracts.

A companion coverage test makes the enumeration itself registry-driven: every
``name="…"`` registration in ``registry.py`` must appear in the checked table,
the UMD ``PANEL_ALLOWLIST``, and the Vue store ``PANEL_ALLOWLIST`` — the
three-list agreement gate (webclient-align-04) that turns any future panel
registered without its client mirrors into a loud contract failure instead of
a silently frozen table.
"""

from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_REGISTRY = REPO_ROOT / "web/webclient/presentation/registry.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"
_VUE_STORE = REPO_ROOT / "web/webclient-app/stores/elosern.js"

# Stable production panel names, each with its presenter module (context_actions
# lives in combat_panel.py; the rest are name-matched). Kept in registration
# order; the coverage test below fails if the registry ever grows a panel that
# is absent from this table.
_PANEL_MODULES = (
    ("art", "art.py"),
    ("status", "status.py"),
    ("context_actions", "combat_panel.py"),
    ("local_map", "local_map.py"),
    ("party", "party.py"),
    ("services", "services.py"),
    ("creation", "creation.py"),
    ("exploration", "exploration.py"),
    ("character", "character.py"),
    ("lineage", "lineage.py"),
    ("title_ballot", "title_ballot.py"),
    ("title_codex", "title_codex.py"),
)


class PanelSchemaVersionParityContract(unittest.TestCase):
    @covers_requirement(
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only",
        "webclient-oob-protocol::every-panel-payload-has-an-exact-availability-discriminator",
    )
    def test_panel_schema_versions_are_equal_everywhere(self):
        registry_source = _PY_REGISTRY.read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        mismatches = []
        for panel_name, module_name in _PANEL_MODULES:
            constant = self._registry_reference(registry_source, panel_name)
            if constant is None:
                mismatches.append(f"{panel_name}: registry schema_version is a literal, not a constant")
                continue
            module_version = self._module_value(module_name, constant)
            allowlist_version = self._js_allowlist_value(js_source, panel_name)
            recheck_version = self._js_recheck_value(js_source, panel_name)
            values = {
                "module": module_version,
                "allowlist": allowlist_version,
                "recheck": recheck_version,
            }
            for location, version in values.items():
                if version is None:
                    mismatches.append(
                        f"{panel_name}: missing {constant} / {location} version"
                    )
                elif version != module_version:
                    mismatches.append(
                        f"{panel_name}: module {constant}={module_version} vs {location}={version}"
                    )
        self.assertEqual(
            mismatches,
            [],
            "panel schema versions diverged across module, registry, and client",
        )

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes",
    )
    def test_panel_registration_is_mirrored_in_all_three_lists(self):
        # Three-list agreement (webclient-align-04): every name the production
        # registry registers must exist in the checked table, the UMD
        # allowlist, and the Vue store allowlist, and no list may carry a
        # name the registry does not register.
        registry_source = _PY_REGISTRY.read_text(encoding="utf-8")
        registered = set(
            re.findall(
                r'name="([a-z0-9_]+)"\s*,\s*schema_version=',
                registry_source,
            )
        )
        self.assertTrue(registered, "registry.py registration pattern matched nothing")
        table = {name for name, _module in _PANEL_MODULES}
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        block_match = re.search(r"var PANEL_ALLOWLIST\s*=\s*\{(.*?)\};", js_source, re.DOTALL)
        self.assertIsNotNone(block_match, "UMD PANEL_ALLOWLIST block vanished")
        umd = set(re.findall(r"(\w+):\s*\d+", block_match.group(1)))
        vue_source = _VUE_STORE.read_text(encoding="utf-8")
        vue_match = re.search(r"const PANEL_ALLOWLIST\s*=\s*\[(.*?)\];", vue_source, re.DOTALL)
        self.assertIsNotNone(vue_match, "Vue PANEL_ALLOWLIST list vanished")
        vue = set(re.findall(r'"([a-z0-9_]+)"', vue_match.group(1)))
        self.assertEqual(registered, table, "checked table diverged from registry registrations")
        self.assertEqual(registered, umd, "UMD allowlist diverged from registry registrations")
        self.assertEqual(registered, vue, "Vue store allowlist diverged from registry registrations")

    def test_party_row_and_display_bounds_are_pinned(self):
        # The party row cap mirrors the rules companion bound and the shared
        # display-name ceiling, in Python AND the UMD mirror (review round:
        # the presenter's "fails loudly" claim needs an executed guard).
        party_source = (
            REPO_ROOT / "web/webclient/presentation/party.py"
        ).read_text(encoding="utf-8")
        rules_source = (REPO_ROOT / "world/rules/party.py").read_text(
            encoding="utf-8"
        )
        affordances_source = (
            REPO_ROOT / "web/webclient/presentation/affordances.py"
        ).read_text(encoding="utf-8")
        js_source = _JS_PROTOCOL.read_text(encoding="utf-8")
        values = {
            "party.PARTY_MAX_ROWS": re.search(
                r"^PARTY_MAX_ROWS\s*=\s*(\d+)", party_source, re.MULTILINE
            ),
            "rules PARTY_MAX_COMPANIONS": re.search(
                r"^PARTY_MAX_COMPANIONS\s*=\s*(\d+)", rules_source, re.MULTILINE
            ),
            "js PARTY_MAX_ROWS": re.search(
                r"^  var PARTY_MAX_ROWS\s*=\s*(\d+);", js_source, re.MULTILINE
            ),
            "affordances MAX_DISPLAY_NAME_CODE_POINTS": re.search(
                r"^MAX_DISPLAY_NAME_CODE_POINTS\s*=\s*(\d+)",
                affordances_source,
                re.MULTILINE,
            ),
            "js PARTY_MAX_DISPLAY_NAME": re.search(
                r"^  var PARTY_MAX_DISPLAY_NAME\s*=\s*(\d+);",
                js_source,
                re.MULTILINE,
            ),
        }
        extracted = {key: match.group(1) for key, match in values.items()}
        self.assertNotIn(None, [match for match in values.values()], extracted)
        rows = {extracted[key] for key in (
            "party.PARTY_MAX_ROWS",
            "rules PARTY_MAX_COMPANIONS",
            "js PARTY_MAX_ROWS",
        )}
        self.assertEqual(len(rows), 1, f"party row cap drifted: {extracted}")
        names = {extracted[key] for key in (
            "affordances MAX_DISPLAY_NAME_CODE_POINTS",
            "js PARTY_MAX_DISPLAY_NAME",
        )}
        self.assertEqual(len(names), 1, f"display-name bound drifted: {extracted}")

    @staticmethod
    def _registry_reference(source, panel_name):
        # Identifier-only reference: a numeric literal fails to match.
        match = re.search(
            rf'name="{panel_name}"\s*,\s*schema_version=([A-Z][A-Z0-9_]+)',
            source,
            re.DOTALL,
        )
        if match is None:
            return None
        return match.group(1)

    @staticmethod
    def _module_value(module_name, constant):
        module_source = (REPO_ROOT / "web/webclient/presentation" / module_name).read_text(
            encoding="utf-8"
        )
        match = re.search(rf"^{constant}\s*=\s*([0-9]+)", module_source, re.MULTILINE)
        if match is None:
            return None
        return int(match.group(1))

    @staticmethod
    def _js_allowlist_value(js_source, panel_name):
        block_match = re.search(r"var PANEL_ALLOWLIST\s*=\s*\{(.*?)\};", js_source, re.DOTALL)
        if block_match is None:
            return None
        for name, version in re.findall(r"(\w+): (\d+)", block_match.group(1)):
            if name == panel_name:
                return int(version)
        return None

    @staticmethod
    def _js_recheck_value(js_source, panel_name):
        function_name = "validate" + "".join(
            part.capitalize() for part in panel_name.split("_")
        ) + "Panel"
        start = js_source.find(f"function {function_name}(payload)")
        if start == -1:
            return None
        # Bound the scan to the validator body so a deleted re-check cannot
        # silently pick up the next validator's same-version literal.
        remainder = js_source[start:]
        boundary = re.search(r"\n  function [a-zA-Z_]+\(payload\)", remainder)
        if boundary is not None:
            remainder = remainder[: boundary.start()]
        # The re-check is a numeric literal or an identifier reference to the
        # mirrored top-level constant (e.g. ``!== CREATION_SCHEMA_VERSION``);
        # both spellings are intended forms of the same mirror.
        match = re.search(r"payload\.schema_version !== ([0-9]+|[A-Z][A-Z0-9_]*)", remainder)
        if match is None:
            return None
        token = match.group(1)
        if token.isdigit():
            return int(token)
        # Resolve the identifier against its module-scope var declaration (the
        # protocol module body is IIFE-indented by two spaces) so a function
        # -local shadow at deeper indentation can never satisfy it.
        var_match = re.search(
            rf"^ {{0,2}}var {token}\s*=\s*([0-9]+)\s*;", js_source, re.MULTILINE
        )
        return int(var_match.group(1)) if var_match is not None else None


if __name__ == "__main__":
    unittest.main()
