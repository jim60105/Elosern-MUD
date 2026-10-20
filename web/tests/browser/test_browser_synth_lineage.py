"""Managed synthetic member lineage parity (seeded-lineage-readability).

One dedicated isolated runtime boots the existing synthetic store-companion
fixture. 艾拉's lineage is read through the authenticated text command and the
party window's 系譜 tab: both consumers derive the same bounded view, so their
roots, node identities/order and prerequisite edges must agree while the
committed party and viewed-member panels stay unchanged across repeated reads.

The kit's installed skill catalog is the fixture: the companion owns no skill,
so its graph is the catalog's two-node burst/comet edge. Before the catalog
boundary rebuilt the lineage reverse-edge index, the valid installed graph
looked cyclic to the read model and both surfaces reported unavailable.
"""

from __future__ import annotations

import re
from copy import deepcopy

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    narrative_log_length,
    narrative_log_text,
    store_state,
    wait_for_narrative_settled,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin

COMPANION_NAME = "艾拉"

#: Both text and panel read this one installed catalog edge.
ROOT_KEY = "t_ember_burst"
CHILD_KEY = "t_ember_comet"
EDGE_LEVEL = 3


class SynthLineageBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """The synthetic member journey on its own runtime (the shop companion)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Boot a dedicated runtime instead of the shared shipped-mode server.
        pass

    def setUp(self) -> None:
        self.server = ManagedServer()
        self.server.runtime.env["ELOSERN_BROWSER_SERVICES"] = "store_open_companion"
        self.server.runtime.env["ELOSERN_BROWSER_ART"] = ""
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # -- journey plumbing ---------------------------------------------------

    def _companion_id(self, state: dict) -> int:
        party = state["panels"]["party"]
        companion = next(
            row["identity"]
            for row in party["slots"]
            if row["display_name"] == COMPANION_NAME
        )
        return int(companion)

    def _commander_id(self, state: dict) -> int:
        party = state["panels"]["party"]
        return int(
            next(
                row["identity"]
                for row in party["slots"]
                if row["role"] == "commander"
            )
        )

    def _stored_snapshot(self, *identities: int) -> tuple:
        """The committed object rows and attributes of these database objects.

        The managed panel comparison only observes the client transport; this
        reads the private runtime database so a write that emits no updated
        panel is still caught. ``skill_proficiency`` and ``skills`` are member
        attributes, so they ride the attribute rows.
        """
        import sqlite3

        placeholders = ",".join("?" for _ in identities)
        connection = sqlite3.connect(
            str(self.server.runtime.database_path), timeout=10
        )
        try:
            objects = connection.execute(
                "SELECT id, db_key, db_typeclass_path, db_date_created, "
                "db_lock_storage, db_sessid, db_cmdset_storage, db_account_id, "
                "db_destination_id, db_home_id, db_location_id "
                f"FROM objects_objectdb WHERE id IN ({placeholders}) ORDER BY id",
                identities,
            ).fetchall()
            attributes = connection.execute(
                "SELECT a.id, a.db_key, COALESCE(a.db_category, ''), "
                "a.db_value, a.db_strvalue, a.db_lock_storage, a.db_model, "
                "a.db_attrtype FROM typeclasses_attribute a "
                "JOIN objects_objectdb_db_attributes m "
                "ON m.attribute_id = a.id "
                f"WHERE m.objectdb_id IN ({placeholders}) "
                "ORDER BY m.objectdb_id, a.db_key, a.db_category",
                identities,
            ).fetchall()
        finally:
            connection.close()
        return (objects, attributes)

    def _read_lineage_text(self, page) -> str:
        """Send the authenticated text command and return the settled log."""
        before = narrative_log_length(page)
        page.evaluate(
            "([name]) => Evennia.msg('text', [`系譜 ${name}`], {})",
            [COMPANION_NAME],
        )
        wait_for_narrative_settled(page, before)
        return narrative_log_text(page)

    def _view_companion_lineage(self, page, companion: int) -> dict:
        """Select the companion in the party window and open its 系譜 tab."""
        page.locator('[data-nav-slot="party"]').focus()
        page.keyboard.press("l")
        page.wait_for_selector('[data-testid="party-window"]', timeout=15000)
        page.locator(f'[data-testid="member-rail__entry--{companion}"]').click()
        wait_for_store_state(
            page,
            lambda state: (
                ((state.get("panels") or {}).get("party") or {}).get(
                    "viewed_member_id"
                )
                == companion
            ),
            timeout=30000,
        )
        page.locator('[data-testid="icon-tabs__tab--lineage"]').click()
        wait_for_store_state(
            page,
            lambda state: (
                ((state.get("panels") or {}).get("lineage") or {}).get("available")
                is True
            ),
            timeout=30000,
        )
        return store_state(page)["panels"]["lineage"]

    def _assert_text_matches_panel(self, text: str, panel: dict) -> None:
        # The narrative store keeps the rendered line markup; its line breaks
        # are `<br>` elements rather than newlines.
        text = re.sub(r"<br\s*/?>", "\n", text)
        self.assertNotIn("無法閱讀", text, text)
        marker = (
            f"技能系譜：已完成 {panel['completed_count']} / {panel['total_count']} 樹"
        )
        self.assertIn(marker, text)
        # Repeated reads append another report; assert against the latest one.
        text = marker + text.rpartition(marker)[2]
        headers = [line for line in text.splitlines() if line.startswith("── ")]
        self.assertEqual(len(headers), len(panel["graphs"]), text)
        expected_nodes = []
        for header, graph in zip(headers, panel["graphs"]):
            names = {
                node["skill_key"]: node["display_name_zh"]
                for node in graph["nodes"]
            }
            self.assertEqual(
                len(names), len(graph["nodes"]), "node identities must be distinct"
            )
            self.assertIn(
                "根：" + "‧".join(names[key] for key in graph["root_keys"]), header
            )
            self.assertIn(
                f"（{graph['owned_count']}/{graph['total_count']}）", header
            )
            expected_nodes.extend(graph["nodes"])

        node_lines = [
            line.strip()
            for line in text.splitlines()
            if line.startswith("  ") and " Lv." in line
        ]
        self.assertEqual(len(node_lines), len(expected_nodes), text)
        positions = {
            node["skill_key"]: index for index, node in enumerate(expected_nodes)
        }
        for index, node in enumerate(expected_nodes):
            self.assertTrue(
                node_lines[index].startswith(node["display_name_zh"] + " Lv."),
                f"{node['skill_key']} is not at topological position {index}: "
                f"{node_lines[index]!r}",
            )
        for graph in panel["graphs"]:
            names = {
                node["skill_key"]: node["display_name_zh"]
                for node in graph["nodes"]
            }
            for edge in graph["edges"]:
                child = node_lines[positions[edge["to_key"]]]
                self.assertIn(
                    f"← {names[edge['from_key']]} Lv.{edge['min_level']}", child
                )

    # -- the journey --------------------------------------------------------

    @covers_requirement(
        "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-"
        "side-effect-free"
    )
    def test_synthetic_member_lineage_matches_text_and_panel(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        wait_for_store_state(
            page,
            lambda state: (
                ((state.get("panels") or {}).get("party") or {}).get("available")
                is True
            ),
            timeout=60000,
        )
        state = store_state(page)
        companion = self._companion_id(state)
        commander = self._commander_id(state)
        stored_before = self._stored_snapshot(companion, commander)

        panel = self._view_companion_lineage(page, companion)
        self.assertEqual(panel["kind"], "lineage")
        self.assertEqual(panel["schema_version"], 2)
        graph = next(
            item for item in panel["graphs"] if item["graph_id"] == ROOT_KEY
        )
        self.assertEqual(graph["root_keys"], [ROOT_KEY])
        self.assertEqual(
            [node["skill_key"] for node in graph["nodes"]],
            [ROOT_KEY, CHILD_KEY],
        )
        self.assertEqual(
            [
                (edge["from_key"], edge["to_key"], edge["min_level"])
                for edge in graph["edges"]
            ],
            [(ROOT_KEY, CHILD_KEY, EDGE_LEVEL)],
        )
        state = store_state(page)
        lineage_first = deepcopy(panel)
        party_before = deepcopy(state["panels"]["party"])
        character_before = deepcopy(state["panels"].get("character"))

        text = self._read_lineage_text(page)
        self._assert_text_matches_panel(text, panel)

        # The same read again: text still names the graph and the committed
        # panels are unchanged (no write, no repair).
        again = self._read_lineage_text(page)
        self._assert_text_matches_panel(again, panel)

        # Re-request the viewed-member panel from the server by selecting
        # another rail row and coming back.
        for member in (commander, companion):
            page.locator(
                f'[data-testid="member-rail__entry--{member}"]'
            ).click()
            wait_for_store_state(
                page,
                lambda state: (
                    ((state.get("panels") or {}).get("party") or {}).get(
                        "viewed_member_id"
                    )
                    == member
                    and ((state.get("panels") or {}).get("lineage") or {}).get(
                        "available"
                    )
                    is True
                ),
                timeout=30000,
            )
        state = store_state(page)
        self.assertEqual(state["panels"]["lineage"], lineage_first)
        self.assertEqual(state["panels"]["party"], party_before)
        self.assertEqual(state["panels"].get("character"), character_before)
        self.assertEqual(
            self._stored_snapshot(companion, commander), stored_before
        )
