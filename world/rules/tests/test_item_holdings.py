"""Tests for the read-only item holdings query (item-holdings-panel).

For one selected item, the query reports every party member's canonical held
count and, for equipment, each member's server-computed stat delta against
that member's current slot occupant. The delta is the character panel's own
breakdown arithmetic run twice (canonical and hypothetical after mapping), so
nothing is written and the client computes neither counts nor deltas.

The canonical requirement IDs this module carries (they join the traceability
index when the change's delta specs sync into ``openspec/specs/``):

- ``webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel``
- ``webclient-item-holdings-panel::holdings-rows-report-counts-and-transfer-availability``
- ``webclient-item-holdings-panel::equipment-deltas-are-server-computed-against-each-member-s-slot-occupant``
- ``webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection``

Data-independent: every item is a synthetic kit row and every magnitude is a
test-authored equipment rule.
"""

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey, EquipmentSlot
from world.rules.combat_session import engage
from world.rules.equipment import (
    EquipmentToggleReason,
    normalize_equipment_mapping,
    normalized_equipment,
    toggle_equipment,
)
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.party import join_party
from world.rules.party_inventory import (
    MAX_EQUIPMENT_DELTA_CHANGES,
    MAX_ITEM_HOLDINGS_ROWS,
    TRANSFER_MESSAGES,
    PartyInventoryViewError,
    equipment_delta,
    item_holdings,
)
from world.rules.party_scope import PARTY_SCOPE_MESSAGES
from world.rules.status_query import StatusQueryError, build_stat_breakdown
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
)
from .combat_fixtures import BattlefieldIsolation

_SWORD = make_item(
    "t_hold_sword",
    display_name_zh="測試鋼劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_STAFF = make_item(
    "t_hold_staff",
    display_name_zh="測試法杖",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.APPRENTICE_FOCUS_STAFF,
)
_WARHAMMER = make_item(
    "t_hold_warhammer",
    display_name_zh="測試戰鎚",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.BEASTFOLK_WARHAMMER,
)
_CHARMS = tuple(
    make_item(
        f"t_hold_charm_{index}",
        display_name_zh=f"測試飾品{index}",
        sellable=False,
        equipment_slot=EquipmentSlot.ACCESSORY,
        modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
    )
    for index in range(6)
)
_CAP_ARMOR = make_item(
    "t_hold_cap_armor",
    display_name_zh="測試生命鎧",
    sellable=False,
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=EquipmentModifierKey.APOTHECARY_BEADS,
)
_ROBE = make_item(
    "t_hold_robe",
    display_name_zh="測試長袍",
    sellable=False,
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=EquipmentModifierKey.LEATHER_ARMOR,
)
_SEAL = make_item(
    "t_hold_seal",
    display_name_zh="測試封印環",
    sellable=False,
    guild_property=True,
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
)
_TONIC_KEY = "t_hold_tonic"
_TONIC = make_item(_TONIC_KEY, display_name_zh="測試藥水", sellable=False)

_ITEMS = {
    row.key: row
    for row in (
        _SWORD,
        _STAFF,
        _WARHAMMER,
        *_CHARMS,
        _CAP_ARMOR,
        _ROBE,
        _SEAL,
        _TONIC,
    )
}

# Test-authored magnitudes: the sword's +6, the staff's neutral +0 and the
# warhammer's +10 are the design's independent arithmetic cases.
_EFFECT_RULES = {
    EquipmentModifierKey.PLAIN_SWORD: EquipmentEffectRule(
        adjustments={"atk_phys": 6},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.APPRENTICE_FOCUS_STAFF: EquipmentEffectRule(
        adjustments={},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.BEASTFOLK_WARHAMMER: EquipmentEffectRule(
        adjustments={"atk_phys": 10},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.SILVER_HAIRPIN: EquipmentEffectRule(
        adjustments={"defense": 2},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.APOTHECARY_BEADS: EquipmentEffectRule(
        adjustments={},
        gauge_caps={"hp": 20},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.LEATHER_ARMOR: EquipmentEffectRule(
        adjustments={"defense": 4},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
}

_EMPTY = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


class ItemHoldingsTests(BattlefieldIsolation, EvenniaTestCase):
    """A co-located commander, two companions, and a present monster."""

    def setUp(self):
        open_synthetic_scope(self, "items", extra={"items": dict(_ITEMS)})
        effects = patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", _EFFECT_RULES
        )
        effects.start()
        self.addCleanup(effects.stop)
        super().setUp()
        self.room = create_object(Room, key="item holdings room")
        self.other_room = create_object(Room, key="item holdings far room")
        self.commander = _player("item holdings commander")
        self.commander.location = self.room
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.commander)
        return npc

    def _hold(self, entity, *keys):
        entity.db.inventory = list(keys)

    def _wear(self, entity, **slots):
        entity.db.equipment = {**_EMPTY, **slots}

    def _row(self, view, member):
        return next(row for row in view.rows if row.member_id == int(member.pk))

    def _changes(self, delta):
        return [(change.key, change.label, change.amount) for change in delta.changes]

    def _spawn_monster(self):
        monster = _monster("item holdings goblin", hp=500)
        monster.location = self.room
        return monster

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_sword_upgrade_and_downgrade_are_independent_arithmetic(self):
        self._hold(self.aila, _STAFF.key)
        self._wear(self.aila, weapon_main=_STAFF.key)
        self._hold(self.kahn, _WARHAMMER.key)
        self._wear(self.kahn, weapon_main=_WARHAMMER.key)

        aila = equipment_delta(self.aila, _SWORD.key)
        kahn = equipment_delta(self.kahn, _SWORD.key)

        # Staff +0 -> sword +6, warhammer +10 -> sword +6.
        self.assertTrue(aila.equippable)
        self.assertEqual(self._changes(aila), [("atk_phys", "攻擊", 6)])
        self.assertTrue(kahn.equippable)
        self.assertEqual(self._changes(kahn), [("atk_phys", "攻擊", -4)])
        # Ownership is not required for the preview: neither member holds it.
        self.assertNotIn(_SWORD.key, self.aila.db.inventory)
        self.assertNotIn(_SWORD.key, self.kahn.db.inventory)

    def test_a_member_who_does_not_hold_the_item_still_gets_a_delta(self):
        self._hold(self.aila, _STAFF.key)
        self._wear(self.aila, weapon_main=_STAFF.key)

        view = item_holdings(
            self.commander, self.commander, _SWORD.key, in_combat=False
        )

        aila = self._row(view, self.aila)
        self.assertEqual(aila.held, 0)
        self.assertEqual(self._changes(aila.delta), [("atk_phys", "攻擊", 6)])
        # Settlement still enforces ownership.
        result = toggle_equipment(self.aila, _SWORD.key)
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, EquipmentToggleReason.ITEM_NOT_HELD)

    def test_accessory_append_reports_the_added_slot_contribution(self):
        self._wear(self.aila)
        self._hold(self.aila, _CHARMS[0].key)

        delta = equipment_delta(self.aila, _CHARMS[0].key)

        self.assertTrue(delta.equippable)
        self.assertEqual(self._changes(delta), [("defense", "防禦", 2)])

    def test_full_accessory_slots_refuse_with_the_toggle_reason(self):
        self._hold(self.aila, *[charm.key for charm in _CHARMS])
        self._wear(self.aila, accessories=[charm.key for charm in _CHARMS[:5]])

        delta = equipment_delta(self.aila, _CHARMS[5].key)

        self.assertFalse(delta.equippable)
        self.assertEqual(delta.reason, "accessory_slots_full")
        self.assertEqual(delta.changes, ())

    def test_already_equipped_item_reports_no_change(self):
        self._hold(self.aila, _SWORD.key, _SEAL.key)
        self._wear(self.aila, weapon_main=_SWORD.key, accessories=[_SEAL.key])

        sword = equipment_delta(self.aila, _SWORD.key)
        seal = equipment_delta(self.aila, _SEAL.key)

        # A real toggle would unequip; the holdings comparison is a no-op.
        self.assertTrue(sword.equippable)
        self.assertEqual(sword.changes, ())
        # The already-worn shortcut precedes the guild-property refusal.
        self.assertTrue(seal.equippable)
        self.assertEqual(seal.changes, ())

        view = item_holdings(
            self.commander, self.commander, _SWORD.key, in_combat=False
        )
        row = self._row(view, self.aila)
        self.assertTrue(row.equipped)
        self.assertEqual(row.delta.changes, ())

    def test_non_equipment_delta_is_null(self):
        self._hold(self.aila, _TONIC_KEY)

        view = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=False
        )

        aila = self._row(view, self.aila)
        self.assertEqual(aila.held, 1)
        self.assertFalse(aila.equipped)
        self.assertIsNone(aila.delta)

    def test_refusals_publish_the_toggle_reason(self):
        self._hold(self.aila, _SEAL.key, _TONIC_KEY)

        non_equipment = equipment_delta(self.aila, _TONIC_KEY)
        locked = equipment_delta(self.aila, _SEAL.key)

        self.assertFalse(non_equipment.equippable)
        self.assertEqual(non_equipment.reason, "not_equipment")
        self.assertFalse(locked.equippable)
        self.assertEqual(locked.reason, "guild_property")

    def test_exam_restriction_refuses_the_preview(self):
        self._hold(self.aila, _SWORD.key)
        self.aila.db.guild_exam_restriction = {
            "host_id": self.aila.pk,
            "exam_id": "t_hold_exam",
            "allowed_skills": [],
            "ceilings": {},
            "neutral_ceilings": {},
        }
        try:
            delta = equipment_delta(self.aila, _SWORD.key)
        finally:
            self.aila.db.guild_exam_restriction = None

        self.assertFalse(delta.equippable)
        self.assertEqual(delta.reason, "exam_kit_locked")

    def test_gauge_cap_increase_and_removal_are_projected(self):
        self.aila.traits.hp.base = 100
        self.aila.traits.hp.mod = 0
        self.aila.traits.hp.current = 100
        self._hold(self.aila, _CAP_ARMOR.key, _ROBE.key)

        upgrade = equipment_delta(self.aila, _CAP_ARMOR.key)
        self.assertEqual(
            self._changes(upgrade), [("hp", "生命", 20)]
        )

        # Wear the cap armor canonically, then preview the robe that removes it.
        self.aila.traits.hp.mod = 20
        self.aila.traits.hp.current = 120
        self._wear(self.aila, armor=_CAP_ARMOR.key)
        downgrade = equipment_delta(self.aila, _ROBE.key)
        self.assertEqual(
            self._changes(downgrade),
            [("hp", "生命", -20), ("defense", "防禦", 4)],
        )
        # The hypothetical current clamps to the lowered ceiling.
        rows = {
            row.key: row
            for row in build_stat_breakdown(
                self.aila,
                equipment=normalize_equipment_mapping(
                    {**_EMPTY, "armor": _ROBE.key}
                ),
            )
        }
        self.assertEqual(rows["hp"].effective, 100)
        self.assertEqual(rows["hp"].current, 100)

    def test_injected_breakdown_decomposes_under_an_exam_ceiling(self):
        self.aila.traits.hp.base = 100
        self.aila.traits.hp.mod = 10
        self.aila.traits.hp.current = 110
        self._wear(self.aila, armor=_CAP_ARMOR.key)
        self.aila.db.guild_exam_restriction = {
            "host_id": self.aila.pk,
            "exam_id": "t_hold_exam",
            "allowed_skills": [],
            "ceilings": {"hp": 110},
            "neutral_ceilings": {},
        }
        try:
            rows = {
                row.key: row
                for row in build_stat_breakdown(
                    self.aila,
                    equipment=normalize_equipment_mapping(
                        {**_EMPTY, "armor": _CAP_ARMOR.key}
                    ),
                )
            }
        finally:
            self.aila.db.guild_exam_restriction = None

        self.assertEqual(rows["hp"].effective, 110)
        self.assertEqual(rows["hp"].current, 110)

    def test_injected_read_rejects_unexplained_canonical_modifiers(self):
        self.aila.traits.hp.base = 100
        self.aila.traits.hp.mod = 7
        self.aila.traits.hp.current = 50

        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(
                self.aila, equipment=normalize_equipment_mapping(_EMPTY)
            )

    def test_projected_gauge_defaults_an_unset_current_to_the_new_maximum(self):
        traits = dict(self.aila.attributes.get("traits", category="traits"))
        traits["hp"] = {"base": 100, "mod": 0, "mult": 1}
        self.aila.attributes.add("traits", traits, category="traits")

        rows = {
            row.key: row
            for row in build_stat_breakdown(
                self.aila,
                equipment=normalize_equipment_mapping(
                    {**_EMPTY, "armor": _CAP_ARMOR.key}
                ),
            )
        }

        self.assertEqual(rows["hp"].effective, 120)
        self.assertEqual(rows["hp"].current, 120)

    def test_non_unit_gauge_multiplier_is_rejected_by_the_injected_read(self):
        self.aila.traits.hp.mult = 2
        self.aila.traits.hp.current = 0
        try:
            with self.assertRaises(StatusQueryError):
                build_stat_breakdown(
                    self.aila, equipment=normalized_equipment(self.aila)
                )
        finally:
            self.aila.traits.hp.mult = 1

    def test_default_read_model_path_is_byte_identical(self):
        self._hold(self.aila, _SWORD.key, _TONIC_KEY)
        self._wear(self.aila, weapon_main=_SWORD.key)

        canonical = build_stat_breakdown(self.aila)
        injected = build_stat_breakdown(
            self.aila, equipment=normalized_equipment(self.aila)
        )

        self.assertEqual(canonical, injected)

    def test_no_selection_yields_no_rows(self):
        for item_key in (None, "t_hold_unregistered"):
            with self.subTest(item_key=item_key):
                view = item_holdings(
                    self.commander, self.commander, item_key, in_combat=False
                )
                self.assertIsNone(view.item_key)
                self.assertEqual(view.rows, ())

    def test_rows_follow_party_order_commander_first(self):
        self._hold(self.commander, _TONIC_KEY)
        self._hold(self.kahn, _TONIC_KEY, _TONIC_KEY)

        view = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=False
        )

        self.assertEqual(
            [row.member_id for row in view.rows],
            [int(self.commander.pk), int(self.aila.pk), int(self.kahn.pk)],
        )
        self.assertEqual([row.held for row in view.rows], [1, 0, 2])

    def test_own_row_is_disabled_without_a_reason(self):
        self._hold(self.commander, _TONIC_KEY)

        view = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=False
        )

        own = self._row(view, self.commander)
        self.assertFalse(own.receive.enabled)
        self.assertIsNone(own.receive.reason)
        other = self._row(view, self.aila)
        self.assertTrue(other.receive.enabled)
        self.assertIsNone(other.receive.reason)

    def test_absent_receiver_reports_the_presence_message(self):
        self._hold(self.commander, _TONIC_KEY)
        self.kahn.location = self.other_room

        view = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=False
        )

        kahn = self._row(view, self.kahn)
        self.assertEqual(kahn.held, 0)
        self.assertFalse(kahn.receive.enabled)
        self.assertEqual(
            kahn.receive.reason, PARTY_SCOPE_MESSAGES["member_not_present"]
        )

    def test_locked_or_unheld_items_refuse_every_receiver(self):
        self._hold(self.commander, _SEAL.key)
        locked = item_holdings(
            self.commander, self.commander, _SEAL.key, in_combat=False
        )
        self.assertEqual(
            self._row(locked, self.aila).receive.reason,
            TRANSFER_MESSAGES["item_locked"],
        )

        self._hold(self.commander)
        unheld = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=False
        )
        self.assertEqual(
            self._row(unheld, self.aila).receive.reason,
            TRANSFER_MESSAGES["item_not_held"],
        )

    def test_combat_reports_counts_and_the_fixed_transfer_bar(self):
        self._hold(self.commander, _TONIC_KEY)
        engage(self.commander, self._spawn_monster())

        view = item_holdings(
            self.commander, self.commander, _TONIC_KEY, in_combat=True
        )

        self.assertEqual([row.held for row in view.rows], [1, 0, 0])
        for row in view.rows:
            with self.subTest(member=row.member_id):
                self.assertFalse(row.receive.enabled)
                self.assertEqual(
                    row.receive.reason,
                    TRANSFER_MESSAGES["transfer_in_combat"],
                )

    def test_malformed_storage_fails_closed(self):
        self._hold(self.commander, _TONIC_KEY)
        self.aila.db.equipment = {"weapon_main": _SWORD.key}

        with self.assertRaises(PartyInventoryViewError) as caught:
            item_holdings(
                self.commander, self.commander, _TONIC_KEY, in_combat=False
            )

        self.assertEqual(caught.exception.args[0], "malformed_equipment")

    def test_malformed_inventory_fails_closed(self):
        self.commander.db.inventory = "not a list"

        with self.assertRaises(PartyInventoryViewError) as caught:
            item_holdings(
                self.commander, self.commander, _TONIC_KEY, in_combat=False
            )

        self.assertEqual(caught.exception.args[0], "malformed_inventory")

    def test_over_bound_party_fails_closed_instead_of_dropping_members(self):
        extra = []
        for index in range(MAX_ITEM_HOLDINGS_ROWS):
            npc = create_object(
                NPC, key=f"額外成員{index}", location=self.room, home=self.room
            )
            npc.race = _race_key()
            npc.apply_race_baseline()
            npc.db.party_member = int(self.commander.pk)
            extra.append(npc)
        roster = list(self.commander.db.party or []) + [int(npc.pk) for npc in extra]
        self.commander.db.party = roster
        self.commander.db.party_meta = {
            str(dbid): {"general": True, "reasons": []} for dbid in roster
        }

        with self.assertRaises(PartyInventoryViewError) as caught:
            item_holdings(
                self.commander, self.commander, _TONIC_KEY, in_combat=False
            )

        self.assertEqual(caught.exception.args[0], "party_too_large")

    def test_the_query_writes_nothing(self):
        self._hold(self.commander, _TONIC_KEY)
        self._hold(self.aila, _SWORD.key, _STAFF.key)
        self._hold(self.kahn)
        self._wear(self.aila, weapon_main=_STAFF.key)
        members = (self.commander, self.aila, self.kahn)
        before = {
            "inventories": [list(member.db.inventory) for member in members],
            "equipment": [deepcopy(member.db.equipment) for member in members],
            "traits": [
                deepcopy(member.attributes.get("traits", category="traits"))
                for member in members
            ],
            "buffs": [deepcopy(member.db.buffs) for member in members],
            "party": deepcopy(self.commander.db.party),
        }

        first = item_holdings(
            self.commander, self.commander, _SWORD.key, in_combat=False
        )
        second = item_holdings(
            self.commander, self.commander, _SWORD.key, in_combat=False
        )

        self.assertEqual(first, second)
        self.assertEqual(
            [list(member.db.inventory) for member in members],
            before["inventories"],
        )
        self.assertEqual(
            [member.db.equipment for member in members], before["equipment"]
        )
        self.assertEqual(
            [
                member.attributes.get("traits", category="traits")
                for member in members
            ],
            before["traits"],
        )
        self.assertEqual([member.db.buffs for member in members], before["buffs"])
        self.assertEqual(self.commander.db.party, before["party"])

    def test_the_bounds_match_the_design_ceilings(self):
        self.assertEqual(MAX_ITEM_HOLDINGS_ROWS, 17)
        self.assertEqual(MAX_EQUIPMENT_DELTA_CHANGES, 16)
