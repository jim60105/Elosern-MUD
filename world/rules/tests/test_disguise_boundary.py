"""Regression tests for the display-only disguise boundary."""

from tools.spec_traceability import covers_requirement

import inspect
import re
from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.traits import get_display_value

FORBIDDEN_MODULES = (
    "world/rules/combat.py",
    "world/rules/dice.py",
    "world/rules/targeting.py",
)

# Every production module that assigns entity.db.disguised_stats, classified
# (preset-disguise-and-sexual-baseline writer clause). The three SEEDERS
# author a declaration at entity construction — the import loader, player
# preset activation, and the companion builder binding each partner preset's
# own authored card during activation; the typeclass shell init is the
# storage convention entity-traits declared, and the status_disguise runtime
# write is bound by the skill-handler capability's own requirement — neither
# authors a preset/import declaration. Snapshot/restore machinery re-assigns
# previously recorded values through its own helpers and so never appears as
# a raw assignment below. Anything outside this ledger fails the scan.
ASSIGNED_BY = {
    "world/imports/loader.py": "import-record seeder",
    "world/rules/character_creation.py": "preset-activation seeder",
    "world/rules/starting_companions.py": "companion-activation seeder (partner-preset declaration)",
    "typeclasses/entities.py": "storage-convention shell init to None",
    "world/rules/skill_effects.py": "skill-handler runtime write",
}

# Production source trees the writer scan covers.
PRODUCTION_ROOTS = ("world", "typeclasses", "commands")

_ASSIGNMENT = re.compile(
    r"db\.disguised_stats\s*=|attributes\.add\(\s*[\"']disguised_stats[\"']"
    r"|\[[\"']disguised_stats[\"']\]\s*="
)


class DisguiseBoundaryTests(EvenniaTest):
    @covers_requirement("disguised-stats-boundary::combat-resolution-and-damage-modules-never-call-the-disguise-accessor")
    def test_forbidden_rules_modules_do_not_read_disguise_layer(self):
        root = Path(__file__).resolve().parents[3]
        for relative_path in FORBIDDEN_MODULES:
            path = root / relative_path
            if path.exists():
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("disguised_stats", source, relative_path)
                self.assertNotIn("get_display_value", source, relative_path)

    @covers_requirement("disguised-stats-boundary::disguised-stats-is-stored-separately-from-traithandler", "disguised-stats-boundary::get-display-value-is-the-single-sanctioned-accessor-for-a-possibly-disguised-stat")
    def test_accessor_changes_display_without_changing_true_values(self):
        entity = create_object(PlayerCharacter, key="disguised")
        entity.race = "elf"
        entity.apply_race_baseline()
        true_attack = entity.traits.atk_phys.value
        true_defense = entity.traits.defense.value
        entity.db.disguised_stats = {"atk_phys": 60, "magic_power": 30}
        self.assertEqual(get_display_value(entity, "atk_phys"), 60)
        self.assertEqual(get_display_value(entity, "defense"), true_defense)
        self.assertEqual(entity.traits.atk_phys.value, true_attack)
        # magic_power is static; the elf floor is its true value, while the
        # disguise layer renders 30 through the sanctioned accessor.
        self.assertEqual(entity.traits.magic_power.value, 100)
        self.assertEqual(get_display_value(entity, "magic_power"), 30)

    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_production_writers_of_the_layer_are_the_documented_ledger(self):
        # The writer half of the reader/writer split: every production
        # assignment of the attribute is accounted in ASSIGNED_BY, so the
        # only modules seeding an AUTHORED declaration at construction remain
        # the import loader, player preset activation, and the companion
        # builder seeding each declared partner's own preset card. A new
        # write site has to be classified here deliberately rather than
        # silently widening the set.
        root = Path(__file__).resolve().parents[3]
        assigned = set()
        for tree in PRODUCTION_ROOTS:
            for path in sorted((root / tree).rglob("*.py")):
                relative = path.relative_to(root).as_posix()
                if "/tests/" in f"/{relative}":
                    continue
                if _ASSIGNMENT.search(path.read_text(encoding="utf-8")):
                    assigned.add(relative)
        self.assertEqual(
            assigned,
            set(ASSIGNED_BY),
            f"unclassified production writer of disguised_stats: "
            f"{sorted(assigned ^ set(ASSIGNED_BY))}",
        )

    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_accessor_docstring_names_the_reader_and_writer_split(self):
        # The docstring is the normative record of the split: it keeps naming
        # the three readers and names both construction-time seeding writers.
        doc = inspect.getdoc(get_display_value).lower()
        self.assertIn("readers", doc)
        self.assertIn("writers", doc)
        self.assertIn("world/imports/loader.py", doc)
        self.assertIn("world/rules/character_creation.py", doc)
        self.assertIn("world/rules/starting_companions.py", doc)
        self.assertIn("skill_effects.py", doc)
