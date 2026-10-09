"""Tests for status panel presentation (webclient-status-presentation)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.status import STATUS_SCHEMA_VERSION, status_presenter


class StatusPanelPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.player = create_object(
            PlayerCharacter,
            key="StatusActor",
            location=self.room1,
        )
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.save()
        self.registry = build_production_registry()

    def _context(self, actor=None):
        return PresentationContext(actor or self.player, 1)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_status_panel_renders_zero_maximum_gauge_verbatim(self):
        traits = dict(self.player.attributes.get("traits", category="traits"))
        traits["mp"] = {"base": 0, "mod": 0, "mult": 1, "current": 0}
        self.player.attributes.add("traits", traits, category="traits")

        context = self._context()
        payload = status_presenter(context)
        self.assertEqual(payload["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["resources"]["mp"], {"current": 0, "maximum": 0})

        # Also confirm rendering through registry produces an available payload
        rendered = self.registry.render("status", context)
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertTrue(rendered["available"])
        self.assertEqual(rendered["resources"]["mp"], {"current": 0, "maximum": 0})

    def test_status_panel_negative_and_nonzero_on_zero_maximum_fail_closed(self):
        traits = dict(self.player.attributes.get("traits", category="traits"))
        # (b1) negative computed maximum
        traits["mp"] = {"base": -5, "mod": 0, "mult": 1, "current": 0}
        self.player.attributes.add("traits", traits, category="traits")
        rendered = self.registry.render("status", self._context())
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertFalse(rendered["available"])
        self.assertEqual(rendered["reason"]["code"], "presentation_unavailable")

        # (b2) nonzero current on zero maximum
        traits["mp"] = {"base": 0, "mod": 0, "mult": 1, "current": 10}
        self.player.attributes.add("traits", traits, category="traits")
        rendered = self.registry.render("status", self._context())
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertFalse(rendered["available"])
        self.assertEqual(rendered["reason"]["code"], "presentation_unavailable")
