"""Test that the served WebClient page title derives from the game name.

The webclient page `<title>` comes from Evennia's ``game_name`` context
variable, which is ``settings.SERVERNAME`` (``evennia/web/utils/general_context.py``).
This test renders the real webclient URL through Django's test client and
asserts the title carries the game name, never the skeleton placeholder.
"""

from django.test import Client

from evennia.utils.test_resources import EvenniaTest

from django.conf import settings

from tools.spec_traceability import covers_requirement


class WebClientPageTitleTest(EvenniaTest):
    """The webclient page title uses the configured game name."""

    @covers_requirement("webclient-login-gate::the-webclient-uses-the-real-game-name-in-its-brand-surfaces")
    def test_webclient_page_title_uses_game_name(self):
        self.assertNotEqual(settings.SERVERNAME, "evennia-skeleton")
        response = Client().get("/webclient/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"<title> {settings.SERVERNAME} </title>")
        self.assertNotContains(response, "evennia-skeleton")
