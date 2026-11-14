"""Data-contract test: the shipped rite document validates against the shipped districts

The authored rite document assigns every district of the authored district
document to one archetype, and the loader rejects any unassigned, unknown or
unused key. This module proves the two shipped documents agree; it asserts
nothing about the prose, the archetype count or any authored value.
"""

from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement
from world.lore.map_districts import DISTRICTS_PATH, REPOSITORY_ROOT, parse_districts_document
from world.lore.rites import CONTENT_PATH
from world.lore.rites.loader import load_rites


def _district_keys() -> frozenset[str]:
    text = (REPOSITORY_ROOT / Path(DISTRICTS_PATH)).read_text(encoding="utf-8")
    return frozenset(parse_districts_document(text).districts)


class ShippedRiteDocumentContractTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_the_shipped_document_assigns_every_shipped_district(self):
        district_keys = _district_keys()
        snapshot = load_rites(CONTENT_PATH, district_keys=district_keys)

        self.assertEqual(set(snapshot.districts), set(district_keys))


if __name__ == "__main__":
    unittest.main()