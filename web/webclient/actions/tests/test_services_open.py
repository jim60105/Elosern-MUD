"""The private, correlated ``services.open`` read (npc-targeted-service-flows).

One selected provider per read. The result's own data slot is exactly
``{npc_id, services}`` where ``services`` is the complete schema-8 snapshot of
that NPC; every outcome is presentation-free and writes nothing, and a refused
selection never substitutes another provider.
"""

from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExamReception, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.service_actions import (
    REASON_SERVICES_TOO_LARGE,
    _services_open_adapter,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.services import SERVICES_SCHEMA_VERSION
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import register_catalog_once
from world.rules.clock import get_world_clock, read_world_clock
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_shop_config,
    synthetic_branch_key,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

BRANCH = synthetic_branch_key()
_T_SHOP = "t_mossgate_stall"
_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_TICK = 12 * 3600

register_catalog_once()
assert _T_SHOP in SYNTH_SHOPS


class ServicesOpenTests(EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "guild_branches", "items", "prices", "shops")
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    _T_SHOP: synth_shop_config(_T_SHOP, (_ITEM,)),
                }
            ),
        )
        get_world_clock()._persist(_TICK)
        self.hall = create_object(Room, key="guild hall")
        self.staff = create_object(NPC, key="guild master", location=self.hall)
        staff_component = GuildStaff.create(
            self.staff, service_id="staff", branch_key=BRANCH
        )
        staff_component.service_binding = "place"
        staff_component.anchor_room_id = self.hall.pk
        self.staff.components.add(staff_component)
        self.counter = create_object(NPC, key="guild counter", location=self.hall)
        counter_component = GuildExamReception.create(
            self.counter, service_id="counter", branch_key=BRANCH
        )
        counter_component.service_binding = "place"
        counter_component.anchor_room_id = self.hall.pk
        self.counter.components.add(counter_component)
        self.keeper = create_object(NPC, key="store keeper", location=self.hall)
        merchant_component = Merchant.create(
            self.keeper, service_id="store", shop_key=_T_SHOP
        )
        merchant_component.service_binding = "place"
        merchant_component.anchor_room_id = self.hall.pk
        self.keeper.components.add(merchant_component)
        merchant_component.merchant_stock = {_ITEM: 5}
        self.player = create_object(PlayerCharacter, key="targeted reader")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.player.db.wallet = 1000

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        super().tearDown()

    def _state(self):
        return (
            list(self.player.db.quest_log or []),
            self.player.db.wallet,
            dict(self.player.db.guild_registration or {}),
            getattr(self.player, "guild_rank", None),
            list(self.keeper.components.get(Merchant.get_component_slot()).merchant_stock),
            read_world_clock().tick if read_world_clock() else None,
        )

    @covers_requirement(
        "webclient-service-menus::opening-selected-provider-services-is-read-only-and-correlated"
    )
    def test_a_successful_read_returns_the_exact_private_wrapper(self):
        before = self._state()
        result = _services_open_adapter(self.player, {"npc_id": int(self.staff.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertTrue(result["no_presentation"])
        self.assertEqual(result["affected_panels"], ())
        self.assertEqual(set(result["data"]), {"npc_id", "services"})
        self.assertEqual(result["data"]["npc_id"], int(self.staff.pk))
        services = result["data"]["services"]
        self.assertEqual(services["schema_version"], SERVICES_SCHEMA_VERSION)
        self.assertEqual(services["guild"]["provider_id"], int(self.staff.pk))
        self.assertIsNone(services["shop"])
        self.assertEqual(self._state(), before)

    def test_each_selected_surface_names_its_own_provider(self):
        counter = _services_open_adapter(self.player, {"npc_id": int(self.counter.pk)})
        self.assertIsNone(counter["data"]["services"]["guild"])
        self.assertEqual(
            counter["data"]["services"]["rank"]["provider_id"], int(self.counter.pk)
        )
        keeper = _services_open_adapter(self.player, {"npc_id": int(self.keeper.pk)})
        self.assertEqual(
            keeper["data"]["services"]["shop"]["provider_id"], int(self.keeper.pk)
        )
        self.assertIsNone(keeper["data"]["services"]["guild"])
        self.assertIsNone(keeper["data"]["services"]["rank"])

    @covers_requirement(
        "webclient-service-menus::opening-selected-provider-services-is-read-only-and-correlated"
    )
    def test_two_merchants_read_one_exact_shop_each(self):
        twin = create_object(NPC, key="second keeper", location=self.hall)
        twin_component = Merchant.create(
            twin, service_id="store_two", shop_key=_T_SHOP
        )
        twin_component.service_binding = "place"
        twin_component.anchor_room_id = self.hall.pk
        twin.components.add(twin_component)
        twin_component.merchant_stock = {_ITEM: 2}
        before = self._state()
        for keeper, expected_stock in ((self.keeper, 5), (twin, 2)):
            result = _services_open_adapter(self.player, {"npc_id": int(keeper.pk)})
            self.assertEqual(result["outcome"], "success")
            shop = result["data"]["services"]["shop"]
            self.assertEqual(shop["provider_id"], int(keeper.pk))
            self.assertEqual(shop["stock"][0]["item_key"], _ITEM)
            self.assertEqual(shop["stock"][0]["stock"], expected_stock)
        self.assertEqual(self._state(), before)

    @covers_requirement(
        "webclient-service-menus::opening-selected-provider-services-is-read-only-and-correlated"
    )
    def test_two_counters_read_one_exact_reception_each(self):
        twin = create_object(NPC, key="second counter", location=self.hall)
        twin_component = GuildExamReception.create(
            twin, service_id="counter_two", branch_key=BRANCH
        )
        twin_component.service_binding = "place"
        twin_component.anchor_room_id = self.hall.pk
        twin.components.add(twin_component)
        for counter in (self.counter, twin):
            result = _services_open_adapter(self.player, {"npc_id": int(counter.pk)})
            self.assertEqual(result["outcome"], "success")
            services = result["data"]["services"]
            self.assertEqual(services["rank"]["provider_id"], int(counter.pk))
            self.assertIsNone(services["guild"])
            self.assertIsNone(services["shop"])

    @covers_requirement(
        "webclient-service-menus::opening-selected-provider-services-is-read-only-and-correlated"
    )
    def test_an_unusable_selection_is_refused_without_data_or_writes(self):
        hidden = create_object(NPC, key="hidden clerk", location=self.hall)
        hidden_component = GuildStaff.create(
            hidden, service_id="hidden", branch_key=BRANCH
        )
        hidden_component.service_binding = "place"
        hidden_component.anchor_room_id = self.hall.pk
        hidden.components.add(hidden_component)
        hidden.locks.add("view:false()")
        before = self._state()
        for npc_id, code in (
            (999_999, "no_such_target"),
            (int(hidden.pk), "no_such_target"),
            (int(self.keeper.pk) + 1000, "no_such_target"),
        ):
            with self.subTest(npc_id=npc_id):
                result = _services_open_adapter(self.player, {"npc_id": npc_id})
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], code)
                self.assertNotIn("data", result)
                self.assertTrue(result["no_presentation"])
        # A plain object carries no supported capability.
        plain = create_object(NPC, key="bystander", location=self.hall)
        result = _services_open_adapter(self.player, {"npc_id": int(plain.pk)})
        self.assertEqual(result["code"], "wrong_capability")
        self.assertNotIn("data", result)
        self.assertEqual(self._state(), before)

    def test_an_invisible_provider_is_refused(self):
        self.staff.locks.add("view:false()")
        result = _services_open_adapter(self.player, {"npc_id": int(self.staff.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_such_target")

    def test_an_oversized_read_is_refused_without_truncating(self):
        with patch(
            "web.webclient.actions.service_actions.MAX_RESULT_DATA_BYTES", 16
        ):
            result = _services_open_adapter(self.player, {"npc_id": int(self.staff.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_SERVICES_TOO_LARGE)
        self.assertNotIn("data", result)
        self.assertTrue(result["no_presentation"])

    def test_the_dispatcher_delivers_the_read_without_publishing_a_panel(self):
        session = SimpleNamespace(
            puppet=self.player, sent=[], ndb=SimpleNamespace(), sessid=1
        )
        session.msg = lambda **kwargs: session.sent.append(kwargs)
        registry = build_production_registry()
        coordinator = attach_coordinator(session, registry)
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "read1",
            "base_revision": coordinator.revision,
            "action_id": "services.open",
            "payload": {"npc_id": int(self.staff.pk)},
        }
        before_frames = len(session.sent)
        handle_ui_action(
            session, self.player, envelope,
            build_production_action_registry(), registry,
        )
        frames = session.sent[before_frames:]
        self.assertTrue(any("ui_action_result" in frame for frame in frames))
        self.assertFalse(any("ui_snapshot" in frame for frame in frames))
        self.assertFalse(any("ui_update" in frame for frame in frames))
