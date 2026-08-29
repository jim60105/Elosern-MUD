"""Inertness guards for the equipment-effect rulebook (tasks 4.1).

(a) A structural scan proves no production module imports
    ``world.rules.equipment_effects`` outside the loader itself and the
    one sanctioned startup validation hook in
    ``server/conf/at_server_startstop.py`` (fail-loud boot validation,
    allowlisted below). The scan covers absolute AND package-relative
    import forms (resolved against each scanned file's package) plus
    literal ``import_module``/``__import__`` calls; deliberately obfuscated
    dynamic imports are out of its (and the requirement's) scope.

(b) The deviant-copy behavior probes are all retired: the heal probe when
    wire-equipment-combat-modifiers (P2) made ``heal_gain`` live, the
    immune/attachment probes when add-equipment-immunity-and-attached-buffs
    (P3) landed those fields, and the pleasure probe when
    add-equipment-sexual-effects (P4) made ``pleasure_gain`` live. Their
    liveness is asserted by the P2/P3/P4 suites instead; this file keeps
    the import scan as the standing guard for any future dead field.
"""

from tools.spec_traceability import covers_requirement

import ast
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_PRODUCTION_ROOTS = ("commands", "server", "typeclasses", "web", "world")
# The loader module may reference itself; the server-start hook is the one
# bootstrap consumer whose import performs startup validation (design D4);
# the two combat-modifier consumers are the authorized P2 gameplay readers
# (the merged-bundle accessor lives in the loader module itself, and the
# gauge-ceiling sync consumes the cap accessor); P3 lands the
# immunity/attached/prose consumers — the action staging gate, the buff
# handler backstop, the equipment toggle lifecycle, the item-use cleanse
# path, the object look card, and the command/web prose surfaces — each is
# a gameplay consumer, but only of fields its own change owns. P4 lands the
# sexual overlay consumers — the pleasure call site (already listed via the
# action workflow) and the status read model's effective-exposure reads. The
# inertness requirement bars ADDITIONAL resolution paths, and the allowlist
# records exactly the sanctioned surface.
_ALLOWLIST = frozenset(
    {
        Path("world/rules/equipment_effects.py"),
        Path("world/rules/combat_modifiers.py"),
        Path("world/rules/equipment.py"),
        Path("server/conf/at_server_startstop.py"),
        Path("world/rules/status_query.py"),
        Path("world/rules/action.py"),
        Path("world/rules/buffs.py"),
        Path("world/rules/equipment.py"),
        Path("world/rules/items.py"),
        Path("commands/economy.py"),
        Path("commands/items.py"),
        Path("typeclasses/objects.py"),
        Path("web/webclient/actions/service_actions.py"),
    }
)
_MODULE = "world.rules.equipment_effects"


def _resolve_from(node: ast.ImportFrom, package: tuple[str, ...]) -> str | None:
    """Resolve an ImportFrom node to an absolute dotted module name."""
    if not node.level:
        return node.module
    trim = node.level - 1
    if trim > len(package):
        return None
    base = ".".join(package[: len(package) - trim])
    return f"{base}.{node.module}" if node.module else base


_PARENT_PACKAGE = _MODULE.rpartition(".")[0]


def _imports_rulebook(tree: ast.AST, package: tuple[str, ...] = ()) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _MODULE or alias.name.startswith(_MODULE + "."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_from(node, package)
            if target == _MODULE:
                return True
            if target == _PARENT_PACKAGE and any(
                alias.name == "equipment_effects" for alias in node.names
            ):
                return True
        elif isinstance(node, ast.Call):
            # Literal dynamic-import forms would smuggle a consumer past the
            # static import scan; none are permitted in the scanned roots.
            function = node.func
            name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else getattr(function, "id", None)
            )
            if name in {"import_module", "__import__"} and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and first.value == _MODULE:
                    return True
    return False


class EquipmentRulebookImportInertnessTests(unittest.TestCase):
    @covers_requirement(
        "equipment-effects::rulebook-fields-stay-inert-until-their-owning-change-lands"
    )
    def test_no_production_module_imports_the_rulebook(self):
        offenders: list[str] = []
        for root in _PRODUCTION_ROOTS:
            for path in (_ROOT / root).rglob("*.py"):
                relative = path.relative_to(_ROOT)
                if "tests" in relative.parts:
                    continue
                if relative in _ALLOWLIST:
                    continue
                if _imports_rulebook(
                    ast.parse(path.read_text(encoding="utf-8")),
                    relative.parts[:-1],
                ):
                    offenders.append(str(relative))
        self.assertEqual(offenders, [])

if __name__ == "__main__":
    unittest.main()
