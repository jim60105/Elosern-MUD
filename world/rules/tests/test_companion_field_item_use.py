"""Explicit-user field item use for a present party member.

Covers ``world/rules/party_inventory.py::use_member_item``: the acting-purpose
member boundary, the unchanged entity-scoped item settlement with the member
as its actor (her own bag, SELF binding, the commander's six-second present-
party advance), the stable refusals with nothing consumed, and the party-wide
combat refusal that keeps the field path off a session persisted under the
commander.

The ``companion-field-actions`` requirements this change adds are annotated at
the archive step, where the delta lands in the main spec; the existing
``party-member-authority`` and ``party-time-settlement`` requirements this
module establishes are annotated with their canonical IDs below.

Data-independent: the potion is a synthetic kit row with its own profile, and
every expected number derives from that row (MP 40 of 120, +30 restores 70).
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import ItemUseMechanics
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat_session import engage, is_in_active_session
from world.rules.item_effects import (
    ITEM_USE_SECONDS,
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
)
from world.rules.items import ItemUseReason
from world.rules.party import join_party
from world.rules.party_inventory import use_member_item
from world.rules.party_scope import (
    REASON_MEMBER_CANNOT_ACT,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
    present_party_scope,
)
from world.skills.equipment import list_items
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
)
from .combat_fixtures import BattlefieldIsolation

_KEY = "t_companion_mana"
_AMOUNT = 30
_ITEM = make_item(
    _KEY,
    display_name_zh="同伴魔力藥水",
    price_table_key="t_mossmeals",
    sellable=True,
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)
# One self-scoped mana adjustment: the default scope binds the effect to the
# user, so the member's own gauge is the only one the use can reach.
_PROFILE = ItemEffectProfile(
    effects=(GaugeAdjustEffect(stat=ItemStat.MP, amount=_AMOUNT),)
)
_SCOPE_EXTRA = {
    "items": {_KEY: _ITEM},
    "item_effect_profiles": {_KEY: _PROFILE},
}


class _CompanionItemUseCase(BattlefieldIsolation, EvenniaTestCase):
    """A co-located commander, two companions, an outsider and a clock."""

    def setUp(self):
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        super().setUp()
        self.room = create_object(Room, key="companion item meadow")
        self.elsewhere = create_object(Room, key="companion item elsewhere")
        self.commander = _player("companion item commander")
        self.commander.location = self.room
        self.commander.db.inventory = []
        self.commander.db.equipment = None
        self.commander.traits.mp.current = self.commander.traits.mp.max
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        for entity in (self.commander, self.aila, self.kahn):
            self._freeze_regen(entity)
        self.clock = WorldClock()

    def _freeze_regen(self, entity):
        """Keep the fixture arithmetic independent of the clock's regen stage.

        The advance still settles the party (asserted through the clock spy);
        disabling the per-second rates only keeps the potion's exact
        restoration independent of the six seconds it takes.
        """
        for gauge_key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, gauge_key, None)
            if gauge is not None:
                gauge.rate = 0

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = 100
        npc.traits.hp.current = 100
        npc.traits.mp.base = 120
        npc.traits.mp.current = 40
        npc.db.inventory = []
        npc.db.equipment = None
        join_party(npc, self.commander)
        return npc

    def _outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.db.inventory = []
        return npc

    def _use(self, member, target=None):
        """Run one member use against this test's own world clock."""
        with patch(
            "world.rules.items.settlement.get_world_clock",
            return_value=self.clock,
        ):
            return use_member_item(
                self.commander, int(member.pk), _KEY, target=target
            )


class CompanionItemUseRuleTests(_CompanionItemUseCase):
    """The wrapper uses the member's bag and settles the party exactly once."""

    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-present-party"
    )
    @covers_requirement(
        "companion-field-actions::a-field-item-use-names-its-user-explicitly"
    )
    def test_a_companion_drinks_her_own_potion(self):
        self.aila.db.inventory = [_KEY]
        commander_mp = int(self.commander.traits.mp.current)
        with patch.object(
            self.clock, "advance", wraps=self.clock.advance
        ) as advance:
            outcome = self._use(self.aila)
        self.assertIs(outcome.member, self.aila)
        self.assertEqual(outcome.settlement.result.outcome, "success")
        # Independent arithmetic: MP 40 of 120 plus the potion's own +30.
        self.assertEqual(int(self.aila.traits.mp.current), 40 + _AMOUNT)
        self.assertEqual(list_items(self.aila), [])
        # The commander's bag and gauge are untouched: the member paid.
        self.assertEqual(list_items(self.commander), [])
        self.assertEqual(int(self.commander.traits.mp.current), commander_mp)
        # Exactly one six-second command advance, settled over the present
        # party resolved through the member's commander.
        advance.assert_called_once()
        seconds, source, scope = advance.call_args.args
        self.assertEqual(seconds, ITEM_USE_SECONDS)
        self.assertEqual(seconds, 6)
        self.assertEqual(source, AdvanceSource.COMMAND)
        self.assertEqual(scope, (self.commander, self.aila, self.kahn))
        self.assertEqual(scope, present_party_scope(self.aila))
        self.assertEqual(self.clock.tick, ITEM_USE_SECONDS)

    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-present-party"
    )
    @covers_requirement(
        "companion-field-actions::a-field-item-use-names-its-user-explicitly"
    )
    def test_self_effects_bind_to_the_user_only(self):
        self.aila.db.inventory = [_KEY]
        self.kahn.db.inventory = [_KEY]
        self.kahn.traits.mp.current = 100
        self._use(self.aila)
        self.assertEqual(int(self.aila.traits.mp.current), 40 + _AMOUNT)
        self.assertEqual(int(self.kahn.traits.mp.current), 100)
        self.assertEqual(list_items(self.kahn), [_KEY])

    @covers_requirement(
        "party-member-authority::acting-purposes-exclude-knocked-out-members"
    )
    @covers_requirement(
        "companion-field-actions::a-field-item-use-names-its-user-explicitly"
    )
    def test_a_knocked_out_member_is_refused_without_consuming(self):
        self.kahn.db.inventory = [_KEY]
        self.kahn.traits.hp.current = 1
        with self.assertRaises(PartyScopeError) as caught:
            self._use(self.kahn)
        self.assertEqual(caught.exception.reason, REASON_MEMBER_CANNOT_ACT)
        self.assertEqual(list_items(self.kahn), [_KEY])
        self.assertEqual(int(self.kahn.traits.mp.current), 40)
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "party-member-authority::member-presence-is-checked-against-the-commander-s-room"
    )
    def test_an_absent_member_is_refused_without_consuming(self):
        self.aila.db.inventory = [_KEY]
        self.aila.location = self.elsewhere
        with self.assertRaises(PartyScopeError) as caught:
            self._use(self.aila)
        self.assertEqual(caught.exception.reason, REASON_MEMBER_NOT_PRESENT)
        self.assertEqual(list_items(self.aila), [_KEY])
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "party-member-authority::a-named-member-is-re-derived-and-never-substituted"
    )
    def test_a_forged_member_is_refused_and_never_replaced_by_the_commander(self):
        outsider = self._outsider()
        self.commander.db.inventory = [_KEY]
        with self.assertRaises(PartyScopeError) as caught:
            self._use(outsider)
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
        # The commander is never substituted for the refused identity.
        self.assertEqual(list_items(self.commander), [_KEY])
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "companion-field-actions::combat-item-use-stays-on-the-actor-command-flow"
    )
    def test_a_party_session_refuses_the_field_path(self):
        # The member carries no session of her own: only the party-wide check
        # keeps the field path off the commander's encounter.
        self.aila.db.inventory = [_KEY]
        monster = _monster("companion item wolf", hp=100, atk=0)
        monster.location = self.room
        engage(self.commander, monster)
        self.assertFalse(is_in_active_session(self.aila))
        outcome = self._use(self.aila)
        self.assertEqual(outcome.settlement.result.outcome, "rejected")
        self.assertEqual(
            outcome.settlement.result.reason, ItemUseReason.ACTIVE_SESSION
        )
        self.assertEqual(list_items(self.aila), [_KEY])
        self.assertEqual(int(self.aila.traits.mp.current), 40)
        self.assertEqual(self.clock.tick, 0)
