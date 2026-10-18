"""Tests for the read-only member inventory view (party-inventory-panel).

The view groups one party member's canonical bag into rows, normalizes the
member's worn slots, and derives the three server-authored descriptors from
the rules' own side-effect-free preflights: field use or the combat draft, the
free equipment toggle, and the transfer preflight. The purse is the
commander's wallet. Nothing is written.

Data-independent: every item is a synthetic kit row.
"""

from copy import deepcopy

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey, EquipmentSlot, ItemUseMechanics
from world.rules.combat_session import engage, read_session
from world.rules.equipment import materialize_registry_object
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)
from world.rules.party import join_party
from world.rules.party_inventory import (
    MAX_MEMBER_INVENTORY_ROWS,
    ROUTE_COMBAT_DRAFT,
    ROUTE_FIELD_USE,
    ROUTE_TOGGLE,
    TRANSFER_MESSAGES,
    PartyInventoryViewError,
    inventory_view,
)
from world.rules.party_scope import PARTY_SCOPE_MESSAGES
from world.rules.service_messages import SERVICE_REASON_MESSAGES
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
)
from .combat_fixtures import BattlefieldIsolation

_BLADE = make_item(
    "t_view_blade",
    display_name_zh="測試長劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_ROBE = make_item(
    "t_view_robe",
    display_name_zh="測試長袍",
    sellable=False,
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=EquipmentModifierKey.LEATHER_ARMOR,
)
_CHARMS = tuple(
    make_item(
        f"t_view_charm_{index}",
        display_name_zh=f"測試飾品{index}",
        sellable=False,
        equipment_slot=EquipmentSlot.ACCESSORY,
        modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
    )
    for index in range(6)
)
_TONIC_KEY = "t_view_tonic"
_TONIC = make_item(
    _TONIC_KEY,
    display_name_zh="測試藥水",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)
_FIELD_ONLY_KEY = "t_view_salve"
_FIELD_ONLY = make_item(
    _FIELD_ONLY_KEY,
    display_name_zh="測試藥膏",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=False),
)
_SEAL = make_item(
    "t_view_seal",
    display_name_zh="測試封印環",
    sellable=False,
    guild_property=True,
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
)
_MATERIALS = tuple(
    make_item(f"t_view_material_{index}", display_name_zh=f"測試素材{index}")
    for index in range(40)
)

_HEAL_PROFILE = ItemEffectProfile(
    effects=(
        GaugeAdjustEffect(stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SELF),
    )
)

_SCOPE_EXTRA = {
    "items": {
        row.key: row
        for row in (
            _BLADE,
            _ROBE,
            *_CHARMS,
            _TONIC,
            _FIELD_ONLY,
            _SEAL,
            *_MATERIALS,
        )
    },
    "item_effect_profiles": {
        _TONIC_KEY: _HEAL_PROFILE,
        _FIELD_ONLY_KEY: _HEAL_PROFILE,
    },
}


class PartyInventoryViewTests(BattlefieldIsolation, EvenniaTestCase):
    """Builds a co-located commander, two companions and a present monster."""

    def setUp(self):
        # Entered before super().setUp() so entity construction also resolves
        # the scoped item rows.
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        super().setUp()
        self.room = create_object(Room, key="party inventory room")
        self.commander = _player("party inventory commander")
        self.commander.location = self.room
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        join_party(npc, self.commander)
        return npc

    def _hold(self, entity, *keys):
        entity.db.inventory = list(keys)
        for key in dict.fromkeys(keys):
            materialize_registry_object(entity, key)

    def _row(self, view, item_key):
        return next(row for row in view.rows if row.item_key == item_key)

    def _spawn_monster(self):
        monster = _monster("party inventory goblin", hp=500)
        monster.location = self.room
        return monster

    @covers_requirement(
        "webclient-party-inventory-panel::equipment-reflects-the-viewed-member-s-worn-slots"
    )
    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_rows_group_held_equipped_and_slot_with_presentation(self):
        self._hold(self.aila, _BLADE.key, _BLADE.key, _TONIC_KEY)
        self.aila.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }

        view = inventory_view(self.aila, in_combat=False)

        blade = self._row(view, _BLADE.key)
        self.assertEqual(blade.held, 2)
        self.assertEqual(blade.equipped_count, 1)
        self.assertEqual(blade.slot, EquipmentSlot.WEAPON_MAIN.value)
        self.assertIsNotNone(blade.presentation)
        self.assertEqual(blade.presentation.kind.value, "weapon")
        self.assertEqual(blade.give.max_quantity, 1)
        self.assertEqual(blade.toggle.route, ROUTE_TOGGLE)
        self.assertTrue(blade.toggle.enabled)
        self.assertIsNone(blade.use)

        tonic = self._row(view, _TONIC_KEY)
        self.assertEqual(tonic.held, 1)
        self.assertEqual(tonic.equipped_count, 0)
        self.assertIsNone(tonic.slot)
        self.assertIsNone(tonic.toggle)
        self.assertEqual(tonic.use.route, ROUTE_FIELD_USE)
        self.assertEqual(tonic.give.max_quantity, 1)

        # Rows are the sorted canonical keys, never a bag-order echo.
        self.assertEqual(
            [row.item_key for row in view.rows], sorted([_BLADE.key, _TONIC_KEY])
        )
        self.assertEqual(view.equipment.weapon_main, _BLADE.key)
        self.assertIsNone(view.equipment.weapon_off)
        self.assertIsNone(view.equipment.armor)
        self.assertEqual(view.equipment.accessories, ())
        self.assertEqual(view.equipment.accessory_limit, 5)

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_purse_is_the_commanders_wallet_and_a_companion_wallet_is_ignored(self):
        self.commander.db.wallet = 1240
        self.aila.db.wallet = 999
        self._hold(self.aila, _TONIC_KEY)

        self.assertEqual(inventory_view(self.aila, in_combat=False).purse, 1240)
        self.assertEqual(
            inventory_view(self.commander, in_combat=False).purse, 1240
        )

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_equipped_copies_cannot_be_given(self):
        self._hold(self.kahn, _BLADE.key)
        self.kahn.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }

        give = self._row(inventory_view(self.kahn, in_combat=False), _BLADE.key).give

        self.assertFalse(give.enabled)
        self.assertEqual(give.reason, TRANSFER_MESSAGES["item_equipped"])
        self.assertEqual(give.max_quantity, 0)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_locked_items_report_the_item_locked_refusal_with_unequipped_copies(self):
        self._hold(self.aila, *([_SEAL.key] * 4))

        give = self._row(inventory_view(self.aila, in_combat=False), _SEAL.key).give

        self.assertFalse(give.enabled)
        self.assertEqual(give.reason, TRANSFER_MESSAGES["item_locked"])
        self.assertEqual(give.max_quantity, 4)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_exam_restriction_locks_giving(self):
        self._hold(self.aila, _TONIC_KEY, _TONIC_KEY)
        self.aila.db.guild_exam_restriction = {
            "host_id": self.aila.pk,
            "exam_id": "t_view_exam",
            "allowed_skills": [],
        }
        try:
            give = self._row(
                inventory_view(self.aila, in_combat=False), _TONIC_KEY
            ).give
        finally:
            self.aila.db.guild_exam_restriction = None

        self.assertFalse(give.enabled)
        self.assertEqual(give.reason, TRANSFER_MESSAGES["item_locked"])
        self.assertEqual(give.max_quantity, 2)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_more_than_the_transfer_cap_reports_every_unequipped_copy(self):
        self._hold(self.aila, *([_TONIC_KEY] * 120))

        give = self._row(inventory_view(self.aila, in_combat=False), _TONIC_KEY).give

        self.assertTrue(give.enabled)
        self.assertIsNone(give.reason)
        self.assertEqual(give.max_quantity, 120)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_combat_disables_giving_with_the_fixed_reason_on_every_row(self):
        self.aila.traits.hp.current = 50
        self._hold(self.aila, _BLADE.key, _BLADE.key, _TONIC_KEY)
        self.aila.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        engage(self.commander, self._spawn_monster())

        view = inventory_view(self.aila, in_combat=True)

        for row in view.rows:
            with self.subTest(item=row.item_key):
                self.assertFalse(row.give.enabled)
                self.assertEqual(
                    row.give.reason, TRANSFER_MESSAGES["transfer_in_combat"]
                )
        blade = self._row(view, _BLADE.key)
        self.assertEqual(blade.give.max_quantity, 1)
        # Toggles stay available for every member while a session runs.
        self.assertTrue(blade.toggle.enabled)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_combat_draft_use_is_enabled_for_a_commandable_companion(self):
        self.aila.traits.hp.current = 50
        self._hold(self.aila, _TONIC_KEY, _FIELD_ONLY_KEY)
        engage(self.commander, self._spawn_monster())

        view = inventory_view(self.aila, in_combat=True)

        tonic = self._row(view, _TONIC_KEY)
        self.assertEqual(tonic.use.route, ROUTE_COMBAT_DRAFT)
        self.assertTrue(tonic.use.enabled)
        self.assertIsNone(tonic.use.reason)
        # A combat-disallowed item has no draft action at all.
        self.assertIsNone(self._row(view, _FIELD_ONLY_KEY).use)

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_combat_draft_use_is_disabled_for_a_knocked_out_companion(self):
        from world.rules.player_messages import session_reason_message

        self.kahn.traits.hp.current = 1
        self._hold(self.kahn, _TONIC_KEY)
        engage(self.commander, self._spawn_monster())
        # A knocked-out companion is not collected into the session's allied
        # roster, so the combat authorization rejects it before any item read.
        self.assertNotIn(self.kahn.pk, read_session(self.commander).player_ids)

        use = self._row(inventory_view(self.kahn, in_combat=True), _TONIC_KEY).use

        self.assertEqual(use.route, ROUTE_COMBAT_DRAFT)
        self.assertFalse(use.enabled)
        self.assertEqual(use.reason, session_reason_message("forbidden_actor"))

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_combat_without_a_readable_session_disables_the_draft(self):
        from world.rules.player_messages import session_reason_message

        self._hold(self.aila, _TONIC_KEY)

        use = self._row(
            inventory_view(self.aila, in_combat=True), _TONIC_KEY
        ).use

        self.assertEqual(use.route, ROUTE_COMBAT_DRAFT)
        self.assertFalse(use.enabled)
        self.assertEqual(use.reason, session_reason_message("no_active_session"))

        self.commander.db.active_combat = {"not": "a session"}
        malformed = self._row(
            inventory_view(self.aila, in_combat=True), _TONIC_KEY
        ).use
        self.assertFalse(malformed.enabled)
        self.assertEqual(malformed.reason, session_reason_message("malformed_session"))

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_exploration_use_descriptor_reports_the_item_preflight_reason(self):
        self._hold(self.aila, _TONIC_KEY)
        self.aila.traits.hp.current = 50

        enabled = self._row(
            inventory_view(self.aila, in_combat=False), _TONIC_KEY
        ).use
        self.assertEqual(enabled.route, ROUTE_FIELD_USE)
        self.assertTrue(enabled.enabled)
        self.assertIsNone(enabled.reason)

        self.aila.traits.hp.current = self.aila.traits.hp.max
        disabled = self._row(
            inventory_view(self.aila, in_combat=False), _TONIC_KEY
        ).use
        self.assertFalse(disabled.enabled)
        self.assertEqual(disabled.reason, SERVICE_REASON_MESSAGES["hp_full"])

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_toggle_reports_the_accessory_cap_reason(self):
        equipped = [charm.key for charm in _CHARMS[:5]]
        self._hold(self.aila, *[charm.key for charm in _CHARMS])
        self.aila.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": equipped,
        }

        view = inventory_view(self.aila, in_combat=False)

        full = self._row(view, _CHARMS[5].key).toggle
        self.assertEqual(full.route, ROUTE_TOGGLE)
        self.assertFalse(full.enabled)
        self.assertEqual(
            full.reason, SERVICE_REASON_MESSAGES["accessory_slots_full"]
        )
        worn = self._row(view, _CHARMS[0].key).toggle
        self.assertTrue(worn.enabled)
        self.assertEqual(view.equipment.accessories, tuple(equipped))

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_toggle_reports_the_exam_kit_reason(self):
        self._hold(self.aila, _BLADE.key)
        self.aila.db.guild_exam_restriction = {
            "host_id": self.aila.pk,
            "exam_id": "t_view_exam",
            "allowed_skills": [],
        }
        try:
            toggle = self._row(
                inventory_view(self.aila, in_combat=False), _BLADE.key
            ).toggle
        finally:
            self.aila.db.guild_exam_restriction = None

        self.assertFalse(toggle.enabled)
        self.assertEqual(toggle.reason, SERVICE_REASON_MESSAGES["exam_kit_locked"])

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_absent_companion_rows_stay_readable_but_every_action_is_refused(self):
        self._hold(self.aila, _BLADE.key, _TONIC_KEY)
        self.aila.location = create_object(Room, key="party inventory far room")
        presence = PARTY_SCOPE_MESSAGES["member_not_present"]

        view = inventory_view(self.aila, in_combat=False)

        self.assertEqual(len(view.rows), 2)
        blade = self._row(view, _BLADE.key)
        self.assertFalse(blade.toggle.enabled)
        self.assertEqual(blade.toggle.reason, presence)
        self.assertFalse(blade.give.enabled)
        self.assertEqual(blade.give.reason, presence)
        tonic = self._row(view, _TONIC_KEY)
        self.assertFalse(tonic.use.enabled)
        self.assertEqual(tonic.use.reason, presence)

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_knocked_out_companion_cannot_use_but_can_organize(self):
        self.kahn.traits.hp.current = 1
        self._hold(self.kahn, _BLADE.key, _TONIC_KEY)

        view = inventory_view(self.kahn, in_combat=False)

        tonic = self._row(view, _TONIC_KEY)
        self.assertFalse(tonic.use.enabled)
        self.assertEqual(
            tonic.use.reason, PARTY_SCOPE_MESSAGES["member_cannot_act"]
        )
        blade = self._row(view, _BLADE.key)
        self.assertTrue(blade.toggle.enabled)
        self.assertTrue(blade.give.enabled)
        self.assertEqual(blade.give.max_quantity, 1)

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_malformed_inventory_fails_closed(self):
        for malformed in ("not a list", [1, 2], {"weapon_main": _BLADE.key}):
            with self.subTest(malformed=malformed):
                self.aila.db.inventory = malformed
                with self.assertRaises(PartyInventoryViewError) as caught:
                    inventory_view(self.aila, in_combat=False)
                self.assertEqual(caught.exception.args[0], "malformed_inventory")

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_malformed_equipment_fails_closed(self):
        self._hold(self.aila, _BLADE.key)
        self.aila.db.equipment = {"weapon_main": _BLADE.key}

        with self.assertRaises(PartyInventoryViewError) as caught:
            inventory_view(self.aila, in_combat=False)

        self.assertEqual(caught.exception.args[0], "malformed_equipment")

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_malformed_wallet_uses_the_stable_unreadable_code(self):
        self.commander.db.wallet = -1

        with self.assertRaises(PartyInventoryViewError) as caught:
            inventory_view(self.aila, in_combat=False)

        self.assertEqual(caught.exception.args[0], "wallet_unreadable")

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_rows_are_capped_at_the_inventory_ceiling(self):
        keys = [row.key for row in _MATERIALS]
        self._hold(self.aila, *keys)

        view = inventory_view(self.aila, in_combat=False)

        self.assertEqual(len(view.rows), MAX_MEMBER_INVENTORY_ROWS)
        self.assertEqual(
            [row.item_key for row in view.rows],
            sorted(keys)[:MAX_MEMBER_INVENTORY_ROWS],
        )

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_unknown_registry_key_is_presented_without_invention(self):
        self._hold(self.aila, "t_view_unregistered")

        row = self._row(
            inventory_view(self.aila, in_combat=False), "t_view_unregistered"
        )

        self.assertEqual(row.display_name, "t_view_unregistered")
        self.assertIsNone(row.presentation)
        self.assertIsNone(row.slot)
        self.assertIsNone(row.use)
        self.assertIsNone(row.toggle)
        self.assertFalse(row.give.enabled)
        self.assertEqual(row.give.reason, TRANSFER_MESSAGES["item_not_held"])
        self.assertEqual(row.give.max_quantity, 1)

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_the_view_writes_nothing(self):
        from world.rules.clock import get_world_clock

        self.commander.db.wallet = 321
        self._hold(self.aila, _BLADE.key, _TONIC_KEY)
        self.aila.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        before = {
            "inventory": list(self.aila.db.inventory),
            "equipment": deepcopy(self.aila.db.equipment),
            "wallet": self.commander.db.wallet,
            "party": deepcopy(self.commander.db.party),
            "tick": get_world_clock().tick,
        }

        first = inventory_view(self.aila, in_combat=False)
        second = inventory_view(self.aila, in_combat=False)

        self.assertEqual(first, second)
        self.assertEqual(list(self.aila.db.inventory), before["inventory"])
        self.assertEqual(self.aila.db.equipment, before["equipment"])
        self.assertEqual(self.commander.db.wallet, before["wallet"])
        self.assertEqual(self.commander.db.party, before["party"])
        self.assertEqual(get_world_clock().tick, before["tick"])
