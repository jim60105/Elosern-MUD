"""Shared fixtures for the GM backend tests (not a test module).

The four account classes of the S1 acceptance matrix: anonymous, an ordinary
player account, a Developer account (``EvenniaTest``'s ``self.account``), and
a superuser. Clients are logged in with ``force_login`` so every request goes
through the real middleware stack and URL map.
"""

from __future__ import annotations

import json

from django.test import Client
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class GmTestCase(EvenniaTest):
    """``EvenniaTest`` plus logged-in clients for each account class."""

    def setUp(self):
        super().setUp()
        self.superuser = create.create_account(
            "GmSuperuser",
            email="gm-super@example.com",
            password="testpassword",
            is_superuser=True,
        )

    def tearDown(self):
        self.superuser.delete()
        super().tearDown()

    def client_for(self, kind: str, **client_kwargs) -> Client:
        client = Client(**client_kwargs)
        account = {
            "anonymous": None,
            "player": self.account2,
            "developer": self.account,
            "superuser": self.superuser,
        }[kind]
        if account is not None:
            client.force_login(account)
        return client

    def assert_error_envelope(self, response, status: int, code: str) -> dict:
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response["Content-Type"], "application/json")
        body = json.loads(response.content)
        self.assertEqual(set(body), {"ok", "error"})
        self.assertIs(body["ok"], False)
        self.assertEqual(set(body["error"]), {"code", "message"})
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        self.assertTrue(body["error"]["message"])
        # Operator copy is Traditional Chinese, not an English fallback.
        self.assertRegex(body["error"]["message"], r"[一-鿿]")
        return body

    def assert_ok_envelope(self, response) -> dict:
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response["Content-Type"], "application/json")
        body = json.loads(response.content)
        self.assertEqual(set(body), {"ok", "data"})
        self.assertIs(body["ok"], True)
        return body["data"]
