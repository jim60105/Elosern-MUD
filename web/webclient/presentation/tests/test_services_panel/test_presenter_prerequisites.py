"""Services presenter prerequisite-gating regression for the 2026-06-08 hotfix."""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import PanelUnavailableError, build_production_registry
from world.rules.service_view import ServicesViewError
import unittest


class ServicesPresenterPrerequisiteTests(EvenniaTestCase):
    """Global-prerequisite failures render the common unavailable form."""


    def setUp(self):
        self.room1 = create_object(Room, key="room")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()


    def test_services_view_error_renders_unavailable(self):
        from unittest.mock import patch

        actor = self.char1
        actor.location = self.room1
        context = PresentationContext(actor=actor, protocol_version=1)
        with patch(
            "web.webclient.presentation.services.build_services_view",
            side_effect=ServicesViewError("world clock is absent"),
        ):
            from web.webclient.presentation.registry import PanelUnavailableError

            with self.assertRaises(PanelUnavailableError):
                from web.webclient.presentation.services import services_presenter

                services_presenter(context)
        # A panel render converts it to the registry unavailable form.
        payload = build_production_registry().render("services", context)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "services_unavailable")


    def test_creation_pending_renders_unavailable(self):
        actor = self.char1
        actor.db.creation_pending = True
        context = PresentationContext(actor=actor, protocol_version=1)
        payload = build_production_registry().render("services", context)
        self.assertFalse(payload["available"])
        self.assertNotIn("player", payload)


if __name__ == "__main__":
    unittest.main()
