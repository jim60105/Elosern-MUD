"""Member-scoped equipment toggle tests (party-member-equipment).

Covers the rule entry that authorizes one present party member for the
organizing purpose and then applies the unchanged entity-scoped toggle, in
exploration and during an active session: the member's own bag and equipment
change, a knocked-out companion is admitted, an absent or non-member identity
is refused without toggling the commander, the tick and round never advance,
and a saved combat draft entry is invalidated by the toggle and re-preflighted
against the member's new equipment when the full draft submits.

Data-independent (test-data-independence): every item is a synthetic kit row;
the immunity accessory binds the rulebook's own immunity row through a runtime
content probe, never a shipped item key or display name.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey, EquipmentSlot, ItemUseMechanics
from world.rules.buffs import entity_active_buffs
from world.rules.clock import get_world_clock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    read_session,
    submit_player_action,
    submit_player_item_use,
)
from world.rules.item_effects import ItemEffectProfile, StatusApplyEffect
from world.rules.party import join_party
from world.rules.party_inventory import toggle_member_equipment
from world.rules.party_scope import (
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
)
from world.skills.equipment import list_items
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import _monster, _player, _race_key, open_synthetic_scope
from ._equipment_rulebook_probes import immune_to_key
from .combat_fixtures import BattlefieldIsolation

_BLADE = make_item(
    "t_member_equipment_blade",
    display_name_zh="測試長劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_AXE = make_item(
    "t_member_equipment_axe",
    display_name_zh="測試戰斧",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_DRAUGHT_KEY = "t_member_equipment_draught"
_DRAUGHT = make_item(
    _DRAUGHT_KEY,
    display_name_zh="測試毒劑",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)
_WARD = make_item(
    "t_member_equipment_ward",
    display_name_zh="測試守護吊飾",
    sellable=False,
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=immune_to_key("poisoned"),
)

#: The debuff the synthetic draught applies; the probed immunity row blocks it.
_DRAUGHT_DEBUFF = "poisoned"

_SCOPE_EXTRA = {
    "items": {row.key: row for row in (_BLADE, _AXE, _DRAUGHT, _WARD)},
    "item_effect_profiles": {
        _DRAUGHT_KEY: ItemEffectProfile(
            effects=(StatusApplyEffect(status=_DRAUGHT_DEBUFF),)
        )
    },
}


class PartyMemberEquipmentTests(BattlefieldIsolation, EvenniaTestCase):
    """Builds a co-located commander, two companions and a present monster."""

    def setUp(self):
        # Entered before super().setUp() so entity construction also resolves
        # the scoped item rows.
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        super().setUp()
        self.room = create_object(Room, key="member equipment room")
        self.commander = _player("member equipment commander")
        self.commander.location = self.room
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        self.clock = get_world_clock()

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        join_party(npc, self.commander)
        return npc

    def _outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def _spawn_monster(self):
        monster = _monster("member equipment goblin", hp=500)
        monster.location = self.room
        return monster

    def _assert_refused(self, member_id, item_key, reason):
        with self.assertRaises(PartyScopeError) as caught:
            toggle_member_equipment(self.commander, member_id, item_key)
        self.assertEqual(caught.exception.reason, reason)
        return caught.exception

    @covers_requirement(
        "equipment-inventory::equipment-toggle-revalidates-ownership-and-registry-slot"
    )
    def test_companion_equips_replaces_and_unequips_in_its_own_bag(self):
        self.aila.db.inventory = [_BLADE.key, _AXE.key]
        self.commander.db.inventory = [_BLADE.key]
        tick_before = self.clock.tick

        equipped = toggle_member_equipment(self.commander, self.aila.pk, _BLADE.key)
        self.assertIs(equipped.member, self.aila)
        self.assertEqual(equipped.result.outcome, "success")
        self.assertEqual(equipped.result.action, "equip-singleton")
        self.assertEqual(self.aila.db.equipment["weapon_main"], _BLADE.key)
        # The commander's own equipment is never touched by a member toggle.
        self.assertIsNone(self.commander.db.equipment)

        replaced = toggle_member_equipment(self.commander, self.aila.pk, _AXE.key)
        self.assertEqual(replaced.result.action, "equip-singleton")
        self.assertEqual(replaced.result.replaced_key, _BLADE.key)
        self.assertEqual(self.aila.db.equipment["weapon_main"], _AXE.key)
        # The replaced weapon stays held, unequipped.
        self.assertEqual(list_items(self.aila), [_BLADE.key, _AXE.key])

        unequipped = toggle_member_equipment(self.commander, self.aila.pk, _AXE.key)
        self.assertEqual(unequipped.result.action, "unequip-singleton")
        self.assertIsNone(self.aila.db.equipment["weapon_main"])
        self.assertEqual(list_items(self.aila), [_BLADE.key, _AXE.key])
        self.assertEqual(self.clock.tick, tick_before)

    @covers_requirement(
        "party-member-authority::acting-purposes-exclude-knocked-out-members"
    )
    def test_knocked_out_companion_is_re_equipped_and_nothing_else_changes(self):
        self.kahn.traits.hp.current = 1
        self.kahn.db.inventory = [_BLADE.key, _AXE.key]
        tick_before = self.clock.tick

        equipped = toggle_member_equipment(self.commander, self.kahn.pk, _BLADE.key)
        self.assertEqual(equipped.result.outcome, "success")
        self.assertEqual(self.kahn.db.equipment["weapon_main"], _BLADE.key)

        replaced = toggle_member_equipment(self.commander, self.kahn.pk, _AXE.key)
        self.assertEqual(replaced.result.replaced_key, _BLADE.key)
        self.assertEqual(self.kahn.db.equipment["weapon_main"], _AXE.key)
        self.assertEqual(list_items(self.kahn), [_BLADE.key, _AXE.key])
        # Reorganizing gear is not acting: the stored HP is untouched.
        self.assertEqual(int(self.kahn.traits.hp.current), 1)
        self.assertEqual(self.clock.tick, tick_before)

    @covers_requirement(
        "party-member-authority::member-presence-is-checked-against-the-commander-s-room"
    )
    def test_absent_member_is_rejected_and_changes_nothing(self):
        self.aila.db.inventory = [_BLADE.key]
        self.aila.location = create_object(Room, key="member equipment far room")

        self._assert_refused(self.aila.pk, _BLADE.key, REASON_MEMBER_NOT_PRESENT)
        self.assertIsNone(self.aila.db.equipment)
        self.assertEqual(list_items(self.aila), [_BLADE.key])

    @covers_requirement(
        "party-member-authority::a-named-member-is-re-derived-and-never-substituted"
    )
    def test_forged_member_is_rejected_without_toggling_the_commander(self):
        outsider = self._outsider()
        self.commander.db.inventory = [_BLADE.key]
        self.aila.db.inventory = [_BLADE.key]

        for member_id in (outsider.pk, 10**9):
            with self.subTest(member_id=member_id):
                self._assert_refused(member_id, _BLADE.key, REASON_NOT_PARTY_MEMBER)
        self.assertIsNone(self.commander.db.equipment)
        self.assertIsNone(self.aila.db.equipment)
        self.assertEqual(list_items(self.commander), [_BLADE.key])

    @covers_requirement(
        "equipment-inventory::equipment-toggling-consumes-neither-a-combat-turn-nor-world-time"
    )
    def test_active_session_toggle_is_free_and_invalidates_the_member_draft(self):
        self.aila.db.inventory = [_DRAUGHT_KEY, _WARD.key]
        monster = self._spawn_monster()
        engage(self.commander, monster)

        # The companion's saved selection is valid against the current state.
        saved = submit_player_item_use(
            self.commander, _DRAUGHT_KEY, commanded_actor=self.aila
        )
        self.assertEqual(saved["outcome"], "draft")
        self.assertTrue(saved["ok"])
        # Every other required actor is already selected, so the commander's
        # later submission is the draft's own final confirmation and nothing
        # else can explain an incomplete result.
        ally_saved = submit_player_action(
            self.commander, BASIC_ATTACK_KEY, [monster], commanded_actor=self.kahn
        )
        self.assertEqual(ally_saved["outcome"], "draft")
        self.assertTrue(ally_saved["ok"])
        record = read_session(self.commander)
        self.assertIn(self.aila.pk, record.draft_entries)
        self.assertIn(self.kahn.pk, record.draft_entries)
        tick_before = self.clock.tick

        # Equipping the probed immunity accessory invalidates the saved entry's
        # preview for the re-equipped member, and stays a free action.
        toggled = toggle_member_equipment(self.commander, self.aila.pk, _WARD.key)
        self.assertEqual(toggled.result.outcome, "success")
        self.assertEqual(self.aila.db.equipment["accessories"], [_WARD.key])
        after_toggle = read_session(self.commander)
        self.assertEqual(after_toggle.draft_version, record.draft_version + 1)
        self.assertIn(self.aila.pk, after_toggle.draft_entries)
        self.assertEqual(after_toggle.round_revision, record.round_revision)
        self.assertEqual(after_toggle.rounds_elapsed, record.rounds_elapsed)
        self.assertEqual(self.clock.tick, tick_before)

        # The full draft submission re-preflights every saved entry against the
        # member's new equipment instead of settling the round.
        submitted = submit_player_action(self.commander, BASIC_ATTACK_KEY, [monster])
        self.assertTrue(submitted["ok"], submitted)
        self.assertEqual(submitted["outcome"], "draft")
        self.assertNotEqual(submitted.get("reason"), "stale_draft_version")
        self.assertFalse(submitted["is_complete"])
        # The re-equipped member is the ONLY missing actor: the invalidation,
        # not an unfilled draft, is what stops the round.
        self.assertEqual(submitted["missing_actors"], (self.aila.pk,))
        self.assertEqual(set(submitted["reselection_reasons"]), {self.aila.pk})
        self.assertEqual(
            submitted["reselection_reasons"][self.aila.pk]["reason"],
            "status_blocked",
        )

        settled = read_session(self.commander)
        self.assertNotIn(self.aila.pk, settled.draft_entries)
        self.assertEqual(settled.round_revision, record.round_revision)
        self.assertEqual(settled.rounds_elapsed, record.rounds_elapsed)
        self.assertEqual(self.clock.tick, tick_before)
        # Nothing settled: the draught is still held and the debuff never
        # applied to the companion.
        self.assertIn(_DRAUGHT_KEY, list_items(self.aila))
        self.assertNotIn(_DRAUGHT_DEBUFF, entity_active_buffs(self.aila))
