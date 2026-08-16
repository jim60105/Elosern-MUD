"""Repository-wide schema-version parity contract for all eight OOB panels.

Each panel's wire schema version is defined in four places that must never
diverge: the presenter module's ``<PANEL>_SCHEMA_VERSION`` constant, the
production registry's ``schema_version=<CONST>`` registration reference, the
client ``PANEL_ALLOWLIST`` mirror in ``protocol.js``, and the client's
per-panel available-form re-check literal. This contract extracts all four
from source text (top-level discovery runs without Evennia settings, so game
modules cannot be imported here) and asserts they are numerically equal,
mirroring the existing bounds parity contracts.
"""

from pathlib import Path
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

_PY_REGISTRY = REPO_ROOT / "web/webclient/presentation/registry.py"
_JS_PROTOCOL = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

# Stable production panel names, each with its presenter module (context_actions
# lives in combat_panel.py; the rest are name-matched).
_PANEL_MODULES = (
    ("art", "art.py"),
    ("status", "status.py"),
    ("context_actions", "combat_panel.py"),
    ("local_map", "local_map.py"),
    ("services", "services.py"),
    ("creation", "creation.py"),
    ("exploration", "exploration.py"),
    ("character", "character.py"),
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
        match = re.search(r"payload\.schema_version !== (\d+)", remainder)
        if match is None:
            return None
        return int(match.group(1))


if __name__ == "__main__":
    unittest.main()
