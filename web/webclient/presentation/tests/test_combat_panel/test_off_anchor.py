import unittest
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

from ._support import _player


class OffAnchorContextActionsTests(BattlefieldIsolation, EvenniaTestCase):
    """The exploration context form carries no coarse service navigation.

    Schema 5 of the exploration panel owns the target-bound services field; the
    shared action vocabulary therefore emits no guild/shop navigation row, and
    the context_actions exploration form (which reads that vocabulary) carries
    none either. The off-anchor host is represented honestly by its own
    services projection in the exploration panel.
    """

    def setUp(self):
        super().setUp()
        from typeclasses.components import Merchant
        from typeclasses.npcs import NPC

        self.anchor = create_object(Room, key="店面")
        self.square = create_object(Room, key="廣場")
        self.player = _player(key="表單測試")
        self.player.location = self.square
        self.merchant = create_object(NPC, key="行腳商人", location=self.square)
        component = Merchant.create(
            self.merchant, service_id="silence_shop", branch_key="plaza_stall"
        )
        self.merchant.components.add(component)
        component.service_binding = "place"
        component.anchor_room_id = self.anchor.pk
        self.registry = build_production_registry()

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_exploration_form_carries_no_guild_or_shop_navigation(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertEqual(payload["kind"], "exploration")
        surfaces = {
            affordance.get("surface")
            for affordance in payload["affordances"]
            if affordance.get("navigation")
        }
        self.assertEqual(surfaces, set())
        # The off-anchor provider is still named honestly, through the
        # exploration panel's own target-bound services field.
        panel = self.registry.render(
            "exploration",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        target = next(
            item
            for item in panel["interact"]
            if item["identity"] == int(self.merchant.pk)
        )
        service = next(
            entry for entry in target["services"]["entries"] if entry["key"] == "shop"
        )
        self.assertFalse(service["enabled"])
        self.assertEqual(
            service["disabled_reason"],
            {"code": "off_anchor", "message": "他的服務不在這裡營業。"},
        )


if __name__ == "__main__":
    unittest.main()
