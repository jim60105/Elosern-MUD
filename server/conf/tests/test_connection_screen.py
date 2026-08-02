"""Tests for the project connection screen and its server configuration."""

from tools.spec_traceability import covers_requirement

import importlib
import unittest

from django.conf import settings


class ConnectionScreenTests(unittest.TestCase):
    @covers_requirement(
        "evennia-project-skeleton::runnable-evennia-project-skeleton",
        "connection-screen::the-connection-screen-presents-the-project-s-custom-login-presentation",
    )
    def test_configured_connection_screen_serves_the_custom_screen(self):
        module = importlib.import_module(settings.CONNECTION_SCREEN_MODULE)
        screen = module.CONNECTION_SCREEN
        self.assertIn("伊洛瑟恩大陸", screen)
        self.assertIn("等待英雄", screen)
        self.assertIn("connect", screen)
        self.assertIn("create", screen)

    def test_module_static_content_is_self_consistent(self):
        from server.conf.connection_screens import CONNECTION_SCREEN

        self.assertEqual(settings.CONNECTION_SCREEN_MODULE, "server.conf.connection_screens")
        self.assertIn("伊洛瑟恩大陸", CONNECTION_SCREEN)
        self.assertIn("新帳號必須建立一個成年角色", CONNECTION_SCREEN)
        self.assertIn("connect", CONNECTION_SCREEN)
        self.assertIn("create", CONNECTION_SCREEN)


if __name__ == "__main__":
    unittest.main()
