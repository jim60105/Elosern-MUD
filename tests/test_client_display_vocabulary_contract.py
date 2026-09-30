"""Repository contract: the client's closed display vocabularies cover the server's.

The Vue client names a few finite server identifiers itself instead of
printing them (webclient-zh-tw-copy-and-labels): the combat-modifier
adjustment keys (``lib/condition_label.js``), the skill target types and
elements (``lib/skill_labels.js``), and the lore codex card fields
(``lib/codex_field_label.js``). Each dictionary falls back to a neutral name
for an unknown identifier, so a server-side addition would silently read as
其他修正 / 未知屬性 / 資料. This contract fails first instead: every identifier
the server can ship has an entry, and element names equal the registry's own.
"""

from pathlib import Path
import re
import unittest

import yaml

from tools.spec_traceability import covers_requirement

from web.webclient.presentation.combat_panel import TARGET_SPECS
from world.lore.elements import ELEMENT_REGISTRY
from world.rules.lore_knowledge import CODE_CATEGORIES

REPO_ROOT = Path(__file__).resolve().parents[1]
_LIB = REPO_ROOT / "web/webclient-app/lib"


def _frozen_map(path: Path, name: str) -> dict[str, str]:
    """Read one ``export const NAME = Object.freeze({ key: "value", ... })``."""
    source = path.read_text(encoding="utf-8")
    match = re.search(
        rf"export const {name} = Object\.freeze\(\{{(.*?)\}}\);", source, re.S
    )
    if match is None:
        raise AssertionError(f"{name} not found in {path}")
    return dict(re.findall(r'^\s*(\w+): "([^"]*)",', match.group(1), re.M))


class ClientDisplayVocabularyContractTests(unittest.TestCase):
    def test_every_combat_modifier_key_has_a_readable_name(self):
        rules = yaml.safe_load(
            (REPO_ROOT / "world/rules/rulebook/combat_modifiers.yaml").read_text(
                encoding="utf-8"
            )
        )
        keys = {key for rule in rules for key in (rule.get("then") or {})}
        labels = _frozen_map(_LIB / "condition_label.js", "MODIFIER_LABELS")
        self.assertEqual(sorted(keys - labels.keys()), [])

    @covers_requirement(
        "webclient-contextual-hud::client-help-and-finite-display-vocabularies-are-localized"
    )
    def test_every_target_spec_and_element_has_a_readable_name(self):
        targets = _frozen_map(_LIB / "skill_labels.js", "TARGET_SPEC_LABELS")
        self.assertEqual(set(targets), set(TARGET_SPECS))
        elements = _frozen_map(_LIB / "skill_labels.js", "ELEMENT_LABELS")
        self.assertEqual(
            elements,
            {key: row.display_name_zh for key, row in ELEMENT_REGISTRY.items()},
        )

    def test_every_codex_card_field_has_a_readable_name(self):
        fields = {
            field
            for category in CODE_CATEGORIES.values()
            for field in category.card_fields
        }
        labels = _frozen_map(_LIB / "codex_field_label.js", "CODEX_FIELD_LABELS")
        self.assertEqual(sorted(fields - labels.keys()), [])


if __name__ == "__main__":
    unittest.main()
