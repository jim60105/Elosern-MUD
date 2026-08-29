"""Inertness guards for the equipment-effect rulebook (tasks 4.1).

(a) A structural scan proves no production module imports
    ``world.rules.equipment_effects`` outside the loader itself and the
    one sanctioned startup validation hook in
    ``server/conf/at_server_startstop.py`` (fail-loud boot validation,
    allowlisted below). The scan covers absolute AND package-relative
    import forms (resolved against each scanned file's package) plus
    literal ``import_module``/``__import__`` calls; deliberately obfuscated
    dynamic imports are out of its (and the requirement's) scope.

(b) Deviant-copy behavior tests prove dormant fields cannot leak: every
    probe entity WEARS the items whose rulebook entries are swapped for
    copies whose dormant-only fields differ — the pleasure probe wears the
    mutated ``black_maid_dress``, the heal probe wears the mutated
    ``sister_vestments``, and the immune/attachment probe wears the mutated
    accessories — and the regen buff is added under the mutated item's
    source key. Combat modifier evaluation, item-use preflight, and buff
    application results must stay identical between the two copies, and
    each test first proves the two copies genuinely load differently.
"""

import ast
import tempfile
import unittest
from pathlib import Path

import yaml

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import EquipmentModifierKey
from world.rules import equipment_effects
from world.rules.buffs import _add_buff, _remove_buff_keys, tick_buffs
from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create
from world.rules.items import ItemUseRequest, preflight_item_use
from world.rules.equipment_effects import reload_equipment_effect_rules

_ROOT = Path(__file__).resolve().parents[3]
_PRODUCTION_ROOTS = ("commands", "server", "typeclasses", "web", "world")
# The loader module may reference itself; the server-start hook is the one
# bootstrap consumer whose import performs startup validation (design D4).
# The inertness requirement bars GAMEPLAY consumers, not this validation
# hook, and the allowlist records exactly that distinction.
_ALLOWLIST = frozenset(
    {
        Path("world/rules/equipment_effects.py"),
        Path("server/conf/at_server_startstop.py"),
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


class EquipmentRulebookDormancyTests(EvenniaTestCase):
    """Deviant copies differing only in dormant fields cannot move gameplay."""

    def setUp(self):
        super().setUp()
        self.entity = self._entity()

    def _entity(self):
        entity = create_object(PlayerCharacter, key="inertness probe")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.traits.hp.rate = 0
        return entity

    def _rulebook_copy(self, mutate) -> Path:
        source = Path(__file__).parents[1] / "rulebook" / "equipment_effects.yaml"
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
        mutate(document)
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.safe_dump(document, handle, allow_unicode=True)
        handle.close()
        return Path(handle.name)

    def _gameplay_observations(self, armor: str = "black_maid_dress"):
        """Probe every deterministic surface the dormant fields claim to feed.

        The probe wears exactly the rulebook items a test mutates (the
        ``armor`` slot is chosen per test), so a hypothetical consumer that
        reads the entries of WORN equipment has no unexercised path to hide
        behind. Entity state is normalized to a
        fixed shape before each probe and every observation is a
        state-DELTA view, so the same entity can be re-probed after a
        rulebook swap without inheriting the previous capture's absolutes.
        """
        self.entity.db.inventory = [
            "healing_potion",
            armor,
            "fearless_brooch",
            "apothecary_beads",
        ]
        self.entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": armor,
            "accessories": ["fearless_brooch", "apothecary_beads"],
        }
        self.entity.traits.hp.current = self.entity.traits.hp.max - 20
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.entity, item_key="healing_potion"),
            in_combat=False,
        )
        stable_preflight = (
            preflight.allowed,
            preflight.reason,
            None
            if preflight.plan is None
            else (
                preflight.plan.item_key,
                preflight.plan.effect_key,
                preflight.plan.gauge,
                preflight.plan.consumable,
                preflight.plan.amount,
                preflight.plan.gauge_restored,
            ),
        )
        bundle = evaluate_combat_modifiers_no_create(self.entity)
        _add_buff(
            self.entity,
            "item_regen_light",
            instance_key="item_regen_light:apothecary_beads",
            source_key="apothecary_beads",
        )
        self.entity.traits.hp.current = self.entity.traits.hp.max - 10
        before = self.entity.traits.hp.value
        records = tick_buffs(self.entity)
        healed = self.entity.traits.hp.value - before
        # Leave no buff instance behind so capture B's healed delta is
        # produced by exactly one fresh grant.
        _remove_buff_keys(self.entity, ("item_regen_light:apothecary_beads",))
        return {
            "preflight": repr(stable_preflight),
            "bundle": repr(sorted(bundle.items())),
            "tick_records": repr(records),
            "healed": healed,
        }

    def _observations_under(self, mutate, armor: str = "black_maid_dress"):
        reload_equipment_effect_rules(self._rulebook_copy(mutate))
        self.addCleanup(reload_equipment_effect_rules)
        return self._gameplay_observations(armor)

    def test_dormant_pleasure_value_never_leaks_from_worn_armor(self):
        def deviate_a(document):
            document["effects"]["black_maid_dress"]["adjustments"][
                "pleasure_gain"
            ] = "+7%"

        def deviate_b(document):
            document["effects"]["black_maid_dress"]["adjustments"][
                "pleasure_gain"
            ] = "+14%"

        first = self._observations_under(deviate_a)
        second = self._observations_under(deviate_b)
        # The loaded dormant value really does differ between the captures.
        self.assertEqual(
            equipment_effects.EQUIPMENT_EFFECT_RULES[
                EquipmentModifierKey.BLACK_MAID_DRESS
            ].adjustments["pleasure_gain"],
            "+14%",
        )
        self.assertEqual(first, second)

    def test_dormant_heal_value_never_leaks_from_worn_vestments(self):
        def deviate_a(document):
            document["effects"]["sister_vestments"]["adjustments"][
                "heal_gain"
            ] = "+3%"

        def deviate_b(document):
            document["effects"]["sister_vestments"]["adjustments"][
                "heal_gain"
            ] = "+15%"

        first = self._observations_under(deviate_a, armor="sister_vestments")
        second = self._observations_under(deviate_b, armor="sister_vestments")
        # The loaded dormant value really does differ between the captures.
        self.assertEqual(
            equipment_effects.EQUIPMENT_EFFECT_RULES[
                EquipmentModifierKey.SISTER_VESTMENTS
            ].adjustments["heal_gain"],
            "+15%",
        )
        self.assertEqual(first, second)

    def test_dormant_immune_and_attached_values_never_leak(self):
        def deviate_a(document):
            document["effects"]["fearless_brooch"] = {}
            document["effects"]["apothecary_beads"] = {}

        def deviate_b(document):
            document["effects"]["fearless_brooch"] = {"immune": ["poisoned"]}
            document["effects"]["apothecary_beads"] = {
                "attached_buffs": ["item_regen_light"]
            }

        first = self._observations_under(deviate_a)
        second = self._observations_under(deviate_b)
        # Capture B genuinely loaded the immune/attachment deviants.
        self.assertEqual(
            equipment_effects.EQUIPMENT_EFFECT_RULES[
                EquipmentModifierKey.FEARLESS_BROOCH
            ].immune,
            ("poisoned",),
        )
        self.assertEqual(
            equipment_effects.EQUIPMENT_EFFECT_RULES[
                EquipmentModifierKey.APOTHECARY_BEADS
            ].attached_buffs,
            ("item_regen_light",),
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
