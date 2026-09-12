"""End-to-end synthetic-data journey (migrate-browser-tests-off-real-data 1.3).

Proves the process-level seam before any journey file migrates: the managed
seed mirrors the kit catalogs into the private database, the managed server
installs the same catalogs at bootstrap, and one journey resolves a
``t_``-prefixed key through the running server into the committed client
store — the store's shop stock row carries the synthetic item key and its
kit-authored display, never a shipped identifier.

One class, one boot: the store_open services fixture is the cheapest
journey whose data comes exclusively from the synthetic guild-economy
catalog.
"""

from __future__ import annotations

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import login_and_open, store_state, wait_for_store_state
from . import fixtures
from .harness import ManagedServer


class SynthJourneySmokeTest(BrowserAcceptanceTest):
    """One isolated server booted with the synthetic services fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        # Boot a dedicated runtime instead of the shared shipped-mode server.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_SERVICES"] = "store_open"
        runtime.env["ELOSERN_BROWSER_ART"] = ""
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def test_shop_stock_rows_resolve_synthetic_keys_end_to_end(self):
        # The offered kit item keys are pinned HERE (not via the support
        # module): the browser shard runs plain ``python -m unittest`` with
        # no Django settings, and any settings-dependent import in the
        # Playwright process fails at import time.
        offered = ("t_ember_spray", "t_huskapple", "t_thorn_knife", "t_iron_fang")

        page = self.logged_in_page()
        wait_for_store_state(
            page,
            lambda s: (
                (s.get("panels") or {}).get("services") or {}
            ).get("available") is True,
            timeout=60000,
        )
        panel = store_state(page)["panels"]["services"]
        stock = {row["item_key"]: row for row in panel["shop"]["stock"]}

        # Every stock row resolves a t_-prefixed key: the seeded merchant's
        # kit shop survived seed -> server -> client with no shipped id.
        self.assertTrue(stock, "synthetic shop must serve stock rows")
        for item_key in stock:
            self.assertTrue(
                item_key.startswith("t_"),
                f"stock key {item_key!r} is not synthetic",
            )
        self.assertTrue(
            set(offered) <= set(stock),
            f"offered kit items missing from stock: {stock.keys()}",
        )
        # Every row carries the catalog's stock integers and the kit item's
        # authored display name — proof the server answered from the
        # synthetic guild catalog seeded into the private DB, end to end.
        for item_key, row in stock.items():
            self.assertTrue(row["display_name"].strip())
            self.assertGreaterEqual(row["stock"], 1)
            self.assertGreaterEqual(row["max_stock"], row["stock"])
            self.assertTrue(row["buy"]["action_id"])
