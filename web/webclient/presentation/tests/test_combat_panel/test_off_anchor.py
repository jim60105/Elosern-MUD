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
    """The context_actions exploration form renders the disabled entry.

    One emitter change must surface in BOTH presenters: the v5
    context_actions form passes the off-anchor shop entry through its
    validator as a disabled navigation affordance.
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
    def test_exploration_form_carries_the_disabled_navigation_entry(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertEqual(payload["kind"], "exploration")
        entry = next(
            a for a in payload["affordances"] if a.get("navigation") and a.get("surface")
        )
        self.assertEqual(entry["surface"], "shop")
        self.assertFalse(entry["enabled"])
        self.assertEqual(
            entry["disabled_reason"],
            {
                "code": "service_unavailable",
                "message": "他的服務不在這裡營業。",
            },
        )


if __name__ == "__main__":
    unittest.main()
