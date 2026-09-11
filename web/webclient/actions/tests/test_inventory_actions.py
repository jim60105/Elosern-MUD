"""Inventory action adapters and dispatcher integration (add-inventory-item-actions).

Exercises the ``inventory.use`` and ``inventory.toggle_equip`` validators,
adapters (out-of-combat settlement, combat round routing, free-action toggle),
and dispatcher-level stale/duplicate handling with canonical surfaces only.

Runs on the synthetic kit (test-data-independence): the scoped item registry
carries a usable self-heal potion, a slotted blade, an inert pass, and six
accessory rings — every expectation derives from those rows, never from a
shipped catalog key or display name.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.service_actions import (
    ServiceActionError,
    _inventory_toggle_equip_adapter,
    _inventory_use_adapter,
    validate_inventory_toggle_equip_payload,
    validate_inventory_use_payload,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.items import ItemDefinition
from world.rules.clock import get_world_clock
from world.rules.combat_session import engage, read_session
from world.skills.equipment import EquipmentSlot, list_items
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_ITEMS

# Kit identities (items+prices scope; the price rows ride along so the kit
# rows' price-table keys resolve):
#   _T_POTION  usable consumable self-heal (the healing-potion role)
#   _T_BLADE   slotted weapon (the equip-toggle role)
#   _T_UNUSABLE inert item: neither usable nor equipment (the meal role)
_T_POTION = SYNTH_ITEMS["t_ember_spray"]
_T_BLADE = SYNTH_ITEMS["t_thorn_knife"]
_T_UNUSABLE = SYNTH_ITEMS["t_wayfarer_pass"]


def _ring_rows() -> dict[str, ItemDefinition]:
    """Six accessory rows to probe the production accessory-slot cap."""
    rows = {}
    for index in range(6):
        rows[f"t_ring_{index}"] = replace(
            _T_BLADE,
            key=f"t_ring_{index}",
            display_name_zh=f"測試戒指{index}",
            equipment_slot=EquipmentSlot.ACCESSORY,
        )
    return rows


_SCOPE_EXTRA = {"items": {**SYNTH_ITEMS, **_ring_rows()}}


class InventoryActionBase(EvenniaTestCase):
    def setUp(self):
        # Every adapter path resolves item keys through the scoped registry,
        # so the kit rows replace the shipped catalog for the whole lifecycle.
        open_synthetic_scope(self, "items", "prices", extra=_SCOPE_EXTRA)
        get_world_clock()
        self.room = create_object(Room, key="item field")
        self.player = create_object(PlayerCharacter, key="inventory actor")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.player.db.wallet = 100
        self.player.db.inventory = []
        self.player.db.equipment = None

    def _monster(self, key="goblin"):
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.location = self.room
        return monster

    def _hurt(self, missing: int) -> int:
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum - missing
        return maximum


class InventoryPayloadValidatorTests(InventoryActionBase):
    def test_validators_accept_one_item_key(self):
        for validator in (
            validate_inventory_use_payload,
            validate_inventory_toggle_equip_payload,
        ):
            self.assertEqual(
                validator({"item_key": _T_POTION.key}),
                {"item_key": _T_POTION.key},
            )

    @covers_requirement(
        "inventory-item-actions::inventory-mutations-use-exact-allowlisted-ui-actions"
    )
    def test_whitespace_item_keys_are_rejected(self):
        # The typed `use`/`equip` commands parse the first whitespace token
        # and the input echo prints the key verbatim: a whitespace-bearing
        # key would echo a line whose keyboard replay targets a different
        # item, so the action boundary rejects it (complete-ui-command-echo D1).
        for validator in (
            validate_inventory_use_payload,
            validate_inventory_toggle_equip_payload,
        ):
            for key in ("t_ember spray", "t_ember\tspray", " t_ember_spray", "t_ember_spray "):
                with self.subTest(validator=validator.__name__, key=key):
                    with self.assertRaises(ServiceActionError):
                        validator({"item_key": key})

    @covers_requirement(
        "inventory-item-actions::inventory-mutations-use-exact-allowlisted-ui-actions"
    )
    def test_authority_like_fields_are_rejected(self):
        cases = (
            {},
            {"item_key": ""},
            {"item_key": "x" * 65},
            {"item_key": _T_UNUSABLE.key, "quantity": 1},
            {"item_key": _T_UNUSABLE.key, "slot": "weapon_main"},
            {"item_key": _T_UNUSABLE.key, "effect_key": "self_heal"},
            {"item_key": _T_UNUSABLE.key, "actor": 7},
            {"item_key": _T_UNUSABLE.key, "consumable": True},
            _T_POTION.key,
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ServiceActionError):
                    validate_inventory_use_payload(payload)
                with self.assertRaises(ServiceActionError):
                    validate_inventory_toggle_equip_payload(payload)


class InventoryUseAdapterTests(InventoryActionBase):
    @covers_requirement(
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative"
    )
    def test_out_of_combat_success_consumes_heals_and_publishes_full_snapshot(self):
        maximum = self._hurt(20)
        self.player.db.inventory = [_T_POTION.key, _T_POTION.key]
        clock = get_world_clock()
        tick_before = clock.tick
        result = _inventory_use_adapter(self.player, {"item_key": _T_POTION.key})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "item_used")
        self.assertEqual(result["affected_panels"], ())
        self.assertIn(_T_POTION.display_name_zh, result["message"])
        self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(list_items(self.player), [_T_POTION.key])
        self.assertEqual(get_world_clock().tick - tick_before, 6)

    @covers_requirement(
        "webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation"
    )
    def test_domain_rejections_are_stable_and_unmutating(self):
        self.player.db.inventory = [_T_POTION.key, _T_UNUSABLE.key]
        cases = (
            ({"item_key": _T_POTION.key}, "hp_full"),
            ({"item_key": "mystery_key"}, "unknown_item"),
            ({"item_key": _T_BLADE.key}, "not_usable"),
            ({"item_key": _T_UNUSABLE.key}, "not_usable"),
            ({"item_key": _T_POTION.key}, "hp_full"),
        )
        before = {
            "inventory": list(self.player.db.inventory),
            "hp": int(self.player.traits.hp.current),
            "wallet": self.player.db.wallet,
        }
        for payload, code in cases:
            with self.subTest(item_key=payload["item_key"]):
                result = _inventory_use_adapter(self.player, payload)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], code)
        self.assertEqual(list(self.player.db.inventory), before["inventory"])
        self.assertEqual(int(self.player.traits.hp.current), before["hp"])
        self.assertEqual(self.player.db.wallet, before["wallet"])

    @covers_requirement(
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative",
        "inventory-item-actions::inventory-actions-publish-all-affected-canonical-panels",
    )
    def test_in_combat_use_occupies_the_round_and_publishes_full_snapshot(self):
        self._hurt(20)
        self.player.db.inventory = [_T_POTION.key]
        engage(self.player, self._monster())
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
        ):
            result = _inventory_use_adapter(
                self.player, {"item_key": _T_POTION.key}
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "round")
        self.assertEqual(result["affected_panels"], ())
        self.assertEqual(list_items(self.player), [])
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(record.rounds_elapsed, 1)

    def test_in_combat_full_hp_rejection_carries_stable_code(self):
        self.player.db.inventory = [_T_POTION.key]
        engage(self.player, self._monster())
        result = _inventory_use_adapter(
            self.player, {"item_key": _T_POTION.key}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "hp_full")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)


class InventoryToggleAdapterTests(InventoryActionBase):
    @covers_requirement(
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative"
    )
    def test_toggle_equips_and_unequips_with_chinese_messages(self):
        self.player.db.inventory = [_T_BLADE.key]
        equipped = _inventory_toggle_equip_adapter(
            self.player, {"item_key": _T_BLADE.key}
        )
        self.assertEqual(equipped["outcome"], "success")
        self.assertEqual(equipped["code"], "equipment_toggled")
        self.assertEqual(equipped["affected_panels"], ())
        self.assertIn("你裝備了", equipped["message"])
        self.assertIn(_T_BLADE.key, list_items(self.player))
        self.assertEqual(self.player.db.equipment["weapon_main"], _T_BLADE.key)
        unequipped = _inventory_toggle_equip_adapter(
            self.player, {"item_key": _T_BLADE.key}
        )
        self.assertIn("你卸下了", unequipped["message"])
        self.assertIsNone(self.player.db.equipment["weapon_main"])

    def test_toggle_rejections_are_stable_and_unmutating(self):
        self.player.db.inventory = [_T_UNUSABLE.key]
        cases = (
            ("mystery_key", "unknown_item"),
            (_T_UNUSABLE.key, "not_equipment"),
            (_T_POTION.key, "not_equipment"),
            (_T_BLADE.key, "item_not_held"),
        )
        for item_key, code in cases:
            with self.subTest(item_key=item_key):
                result = _inventory_toggle_equip_adapter(
                    self.player, {"item_key": item_key}
                )
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], code)
        self.assertIsNone(self.player.db.equipment)

    def test_sixth_accessory_refuses_with_cap_reason(self):
        # The six ring rows ride inside the base class's scoped registry, so
        # no manual registry mutation (and no shipped modifier enum member)
        # is needed to reach the production accessory-slot cap.
        self.player.db.inventory = [f"t_ring_{index}" for index in range(6)]
        for index in range(5):
            result = _inventory_toggle_equip_adapter(
                self.player, {"item_key": f"t_ring_{index}"}
            )
            self.assertEqual(result["outcome"], "success")
        overflow = _inventory_toggle_equip_adapter(
            self.player, {"item_key": "t_ring_5"}
        )
        self.assertEqual(overflow["outcome"], "rejected")
        self.assertEqual(overflow["code"], "accessory_slots_full")
        self.assertEqual(
            self.player.db.equipment["accessories"],
            [f"t_ring_{index}" for index in range(5)],
        )
        removal = _inventory_toggle_equip_adapter(
            self.player, {"item_key": "t_ring_2"}
        )
        self.assertEqual(removal["outcome"], "success")
        self.assertEqual(
            self.player.db.equipment["accessories"],
            ["t_ring_0", "t_ring_1", "t_ring_3", "t_ring_4"],
        )


class InventoryDispatchTests(InventoryActionBase):
    def setUp(self):
        super().setUp()
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()
        self.session = SimpleNamespace(
            puppet=self.player,
            sent=[],
            ndb=SimpleNamespace(),
            sessid=1,
        )
        self.session.msg = lambda **kwargs: self.session.sent.append(kwargs)

    def _coordinator(self):
        coordinator = attach_coordinator(self.session, self.registry)
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        return coordinator

    def _envelope(self, coordinator, action_id, payload, request_id="r1", base_revision=None):
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": (
                coordinator.revision if base_revision is None else base_revision
            ),
            "action_id": action_id,
            "payload": payload,
        }

    def _last_result(self):
        results = [call for call in self.session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    @covers_requirement(
        "webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation"
    )
    def test_duplicate_item_request_settles_once(self):
        self._hurt(20)
        self.player.db.inventory = [_T_POTION.key]
        coordinator = self._coordinator()
        envelope = self._envelope(
            coordinator, "inventory.use", {"item_key": _T_POTION.key},
            request_id="dup-item",
        )
        for _ in range(2):
            handle_ui_action(
                self.session,
                self.player,
                envelope,
                self.action_registry,
                self.registry,
            )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "item_used")
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(int(self.player.traits.hp.current), int(self.player.traits.hp.max))

    @covers_requirement(
        "webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation"
    )
    def test_stale_revision_consumes_nothing(self):
        self._hurt(20)
        self.player.db.inventory = [_T_POTION.key]
        coordinator = self._coordinator()
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator, "inventory.use", {"item_key": _T_POTION.key},
                request_id="fresh",
            ),
            self.action_registry,
            self.registry,
        )
        hp_after_first = int(self.player.traits.hp.current)
        self.player.db.inventory = [_T_POTION.key, _T_POTION.key]
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator, "inventory.use", {"item_key": _T_POTION.key},
                request_id="stale",
                base_revision=coordinator.revision - 1,
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(self.player.db.inventory.count(_T_POTION.key), 2)
        self.assertEqual(int(self.player.traits.hp.current), hp_after_first)

    @covers_requirement(
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative"
    )
    def test_tampered_payload_never_reaches_the_adapter(self):
        self.player.db.inventory = [_T_POTION.key]
        coordinator = self._coordinator()
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "inventory.use",
                {"item_key": _T_POTION.key, "quantity": 5},
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(self.player.db.inventory.count(_T_POTION.key), 1)
