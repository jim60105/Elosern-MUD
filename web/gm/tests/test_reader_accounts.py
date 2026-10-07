"""Fixed-fixture reader tests: accounts (task 2.1 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
account kind: name, permissions, created/last-login dates, live sessions and
the owned character list, read without creating or repairing anything. The
``gm-runtime-state::*`` requirement IDs this module covers enter the
traceability index when the change's delta spec is synced at archive (the
documented ``web/gm/tests/test_spa_evidence.py`` precedent).
"""

from __future__ import annotations

from evennia.utils.test_resources import EvenniaTest

from web.gm.readers import accounts
from web.gm.readers._entities import stored_attribute_keys
from web.gm.tests._state_support import (
    failed_sections,
    link_kinds,
    row_value,
    section_keys,
    section_of,
)

EXPECTED_SECTIONS = ["identity", "access", "lifecycle", "sessions", "characters"]


class AccountReaderTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account.permissions.add("t_reader_perm")
        # EvenniaTest links char1's account reference; the reverse ownership
        # list is what an account page shows, so register it like any login.
        self.account.characters.add(self.char1)

    def test_detail_exposes_every_named_account_field(self):
        detail = accounts.detail(self.account)
        self.assertEqual(detail["kind"], "accounts")
        self.assertEqual(detail["dbref"], self.account.pk)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "名稱"), self.account.key)
        self.assertEqual(row_value(identity, "識別碼"), f"#{self.account.pk}")
        access = section_of(detail, "access")
        self.assertIn("t_reader_perm", [chip["label"] for chip in access["chips"]])
        lifecycle = section_of(detail, "lifecycle")
        self.assertTrue(row_value(lifecycle, "建立時間"))
        self.assertTrue(row_value(lifecycle, "最後登入"))

    def test_owned_characters_cross_link_to_their_entity_pages(self):
        detail = accounts.detail(self.account)
        characters = section_of(detail, "characters")
        self.assertEqual(failed_sections(detail), {})
        self.assertIn("characters", link_kinds(characters))
        self.assertEqual(len(characters["rows"]), 1)
        # Every row is an identifier that resolves to the character's page.
        for row in characters["rows"]:
            cell = row["cells"]["name"]
            self.assertEqual(cell["link"]["kind"], "characters")
            self.assertTrue(str(cell["link"]["id"]).isdigit())

    def test_reading_an_account_creates_no_attributes(self):
        before = stored_attribute_keys(self.account)
        accounts.detail(self.account)
        accounts.item_of(self.account)
        self.assertEqual(stored_attribute_keys(self.account), before)

    def test_item_row_carries_summary_fields_only(self):
        item = accounts.item_of(self.account)
        self.assertEqual(item["id"], str(self.account.pk))
        self.assertEqual(item["kind"], "accounts")
        labels = [field["label"] for field in item["fields"]]
        self.assertEqual(labels, ["權限", "角色數", "最後登入"])
        self.assertNotIn("attributes", item)
