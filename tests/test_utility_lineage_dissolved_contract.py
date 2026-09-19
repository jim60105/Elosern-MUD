"""Repository regression pinning the dissolved 雜學秘術 lineage page.

``docs/lore/skill-trees/utility.md`` was deleted (dissolve-utility-lineage):
its six nodes had no engine verb to implement them against. This is a plain
repository check (no new main-capability requirement, so no
``covers_requirement`` annotation), scoped to this one deletion rather than a
general link checker, matching ``tests/test_design_draft_contract.py``'s
precedent.
"""

from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
DELETED_PAGE = REPO_ROOT / "docs" / "lore" / "skill-trees" / "utility.md"
DOCS_ROOT = REPO_ROOT / "docs"
LINK_TARGET = "skill-trees/utility"


class UtilityLineageDissolvedContract(unittest.TestCase):
    def test_the_deleted_page_does_not_exist(self):
        self.assertFalse(DELETED_PAGE.exists())

    def test_no_docs_file_links_to_the_deleted_page(self):
        offenders = []
        for path in sorted(DOCS_ROOT.rglob("*.md")):
            source = path.read_text(encoding="utf-8")
            if LINK_TARGET in source:
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
