"""Tests for the party member authority boundary (party-member-authority).

Intended requirement IDs, recorded here until the capability is synced into
``openspec/specs/`` and ``tools.spec_traceability list`` can hand out the
canonical ones (``covers_requirement`` decorators are added then):

- ``party-member-authority::the-commander-is-resolved-from-the-authenticated-acting-character``
- ``party-member-authority::a-named-member-is-re-derived-and-never-substituted``
- ``party-member-authority::member-presence-is-checked-against-the-commander-s-room``
- ``party-member-authority::acting-purposes-exclude-knocked-out-members``
- ``party-member-authority::the-present-party-scope-is-ordered-and-room-bound``
- ``party-member-authority::text-member-tokens-resolve-only-within-the-party``
- ``party-member-authority::combat-activity-is-judged-across-the-involved-members``
- ``party-member-authority::a-stale-possession-flag-grants-no-authority``
- ``party-member-authority::membership-rejections-are-stable-and-write-nothing``
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.party import join_party
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    PURPOSE_ACT,
    PURPOSE_ORGANIZE,
    REASON_MEMBER_CANNOT_ACT,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    present_party_scope,
    resolve_commander,
    resolve_member_token,
)
from world.rules.player_control import is_player_driven
from world.rules.possession import enter_possession

from ._combat_session_helpers import _race_key


def _attribute_rows(entity):
    """The stored Attribute rows of an entity as detached, sortable tuples."""
    return sorted(
        (str(attribute.key), str(attribute.category or ""), repr(attribute.value))
        for attribute in entity.attributes.all()
    )


def _rejected(case, call, reason):
    """Run ``call``, assert the stable rejection and return the error."""
    with case.assertRaises(PartyScopeError) as context:
        call()
    error = context.exception
    case.assertEqual(error.reason, reason)
    case.assertEqual(error.message, PARTY_SCOPE_MESSAGES[reason])
    case.assertEqual(str(error), reason)
    return error


class PartyScopeInputTests(unittest.TestCase):
    """Identity input is validated before any object is read."""

    def test_non_dbid_member_identities_are_rejected(self):
        # A boolean is an int subclass, a string is an id in text form, and a
        # float is not an identity: none may authorize anything.
        for member_id in (True, False, "12", 1.5, None, 0, -3):
            with self.subTest(member_id=member_id):
                _rejected(
                    self,
                    lambda: authorize_member(object(), member_id, PURPOSE_ACT),
                    REASON_NOT_PARTY_MEMBER,
                )

    def test_unknown_purpose_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            authorize_member(object(), 1, "trade")

    def test_rejection_messages_are_fixed_and_complete(self):
        self.assertEqual(
            PARTY_SCOPE_MESSAGES,
            {
                REASON_NOT_PARTY_MEMBER: "對方不是你的隊伍成員。",
                REASON_MEMBER_NOT_PRESENT: "對方不在這裡。",
                REASON_MEMBER_CANNOT_ACT: "對方目前無法行動。",
            },
        )
        for reason, message in PARTY_SCOPE_MESSAGES.items():
            self.assertEqual(PartyScopeError(reason).message, message)


class PartyScopeTestCase(EvenniaTest):
    """Builds co-located companions through the real join writer."""

    def _companion(self, key, *, hp=100, player=None):
        player = self.char1 if player is None else player
        npc = create_object(
            NPC, key=key, location=player.location, home=player.location
        )
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        join_party(npc, player)
        return npc


class CommanderResolutionTests(PartyScopeTestCase):
    """The commander comes from the acting character, never from a caller."""

    def test_player_character_is_its_own_commander(self):
        self.assertIs(resolve_commander(self.char1), self.char1)

    def test_possession_keeps_the_commander(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)

        self.assertTrue(is_player_driven(companion))
        self.assertIs(resolve_commander(companion), self.char1)

    def test_non_player_non_possessed_objects_are_rejected(self):
        for acting in (
            create_object(NPC, key="路人", location=self.room1),
            self.room2,
            self.obj1,
            None,
        ):
            with self.subTest(acting=acting):
                _rejected(
                    self,
                    lambda: resolve_commander(acting),
                    REASON_NOT_PARTY_MEMBER,
                )

    def test_flagged_but_unpuppeted_npc_is_refused(self):
        npc = create_object(NPC, key="殘旗", location=self.room1)
        npc.db.possessed_by = self.char1.pk
        self.assertEqual(npc.sessions.count(), 0)

        _rejected(
            self, lambda: resolve_commander(npc), REASON_NOT_PARTY_MEMBER
        )

    def test_malformed_or_unresolvable_owner_is_rejected(self):
        npc = create_object(NPC, key="殘旗二", location=self.room1)
        outsider = create_object(NPC, key="旁人", location=self.room1)
        for owner_id in ("not-a-dbid", True, 10**9, outsider.pk, self.room2.pk):
            with self.subTest(owner_id=owner_id):
                npc.db.possessed_by = owner_id
                with patch(
                    "world.rules.party_scope.is_player_driven", return_value=True
                ):
                    _rejected(
                        self,
                        lambda: resolve_commander(npc),
                        REASON_NOT_PARTY_MEMBER,
                    )

    def test_missing_owner_mirror_grants_no_authority(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)
        # A stale flag with a live session but no owner-side mirror is a
        # half-written possession: it authenticates nobody.
        self.char1.db.possession = None

        _rejected(
            self,
            lambda: resolve_commander(companion),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_mirror_naming_another_companion_grants_no_authority(self):
        companion = self._companion("艾拉")
        other = self._companion("卡恩")
        enter_possession(self.char1, companion)
        self.char1.db.possession = {
            "npc_dbid": other.pk,
            "since_tick": 0,
            "account_id": self.account.pk,
        }

        _rejected(
            self,
            lambda: resolve_commander(companion),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_foreign_account_session_grants_no_authority(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)

        with patch.object(self.session, "account", self.account2):
            _rejected(
                self,
                lambda: resolve_commander(companion),
                REASON_NOT_PARTY_MEMBER,
            )

    def test_stale_flag_rejection_writes_nothing(self):
        npc = create_object(NPC, key="殘旗三", location=self.room1)
        npc.db.possessed_by = self.char1.pk
        entities = (self.char1, npc)
        before = [_attribute_rows(entity) for entity in entities]

        _rejected(
            self, lambda: resolve_commander(npc), REASON_NOT_PARTY_MEMBER
        )

        self.assertEqual(
            [_attribute_rows(entity) for entity in entities], before
        )

    def test_foreign_session_rejection_writes_nothing(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)
        entities = (self.char1, companion)
        before = [_attribute_rows(entity) for entity in entities]

        with patch.object(self.session, "account", self.account2):
            _rejected(
                self,
                lambda: resolve_commander(companion),
                REASON_NOT_PARTY_MEMBER,
            )

        self.assertEqual(
            [_attribute_rows(entity) for entity in entities], before
        )


class MemberAuthorizationTests(PartyScopeTestCase):
    """A named member is re-derived from the roster, never substituted."""

    def test_commander_is_always_an_authorized_member(self):
        self.assertIs(
            authorize_member(self.char1, self.char1.pk, PURPOSE_ORGANIZE),
            self.char1,
        )
        self.assertIs(
            authorize_member(self.char1, self.char1.pk, PURPOSE_ACT),
            self.char1,
        )

    def test_effective_companion_is_admitted_for_both_purposes(self):
        companion = self._companion("艾拉")
        for purpose in (PURPOSE_ORGANIZE, PURPOSE_ACT):
            with self.subTest(purpose=purpose):
                self.assertIs(
                    authorize_member(self.char1, companion.pk, purpose),
                    companion,
                )

    def test_non_member_npc_in_the_room_is_rejected(self):
        outsider = create_object(NPC, key="路人", location=self.room1)
        _rejected(
            self,
            lambda: authorize_member(self.char1, outsider.pk, PURPOSE_ORGANIZE),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_deleted_member_identity_is_rejected(self):
        companion = self._companion("艾拉")
        stale_id = companion.pk
        companion.delete()

        _rejected(
            self,
            lambda: authorize_member(self.char1, stale_id, PURPOSE_ORGANIZE),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_forged_roster_entry_is_rejected(self):
        # A non-NPC object with a matching back-reference is not a companion:
        # the membership read owns the filter, not the stored roster list.
        self.obj1.db.party_member = self.char1.pk
        self.char1.db.party = [self.obj1.pk]

        _rejected(
            self,
            lambda: authorize_member(self.char1, self.obj1.pk, PURPOSE_ORGANIZE),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_absent_member_is_rejected(self):
        companion = self._companion("卡恩")
        self.assertTrue(companion.move_to(self.room2, quiet=True))

        _rejected(
            self,
            lambda: authorize_member(self.char1, companion.pk, PURPOSE_ORGANIZE),
            REASON_MEMBER_NOT_PRESENT,
        )

    def test_an_anchor_cannot_widen_the_presence_check(self):
        nearby = self._companion("艾拉")
        remote = self._companion("卡恩")
        self.assertTrue(remote.move_to(self.room2, quiet=True))

        # The remote member's own room is not the commander's room, so it
        # neither authorizes the member nor moves the effective room.
        _rejected(
            self,
            lambda: authorize_member(
                self.char1, remote.pk, PURPOSE_ORGANIZE, anchor=remote
            ),
            REASON_MEMBER_NOT_PRESENT,
        )
        _rejected(
            self,
            lambda: authorize_member(
                self.char1, nearby.pk, PURPOSE_ORGANIZE, anchor=remote
            ),
            REASON_MEMBER_NOT_PRESENT,
        )

    def test_knocked_out_companion_cannot_act_but_can_be_organized(self):
        companion = self._companion("卡恩", hp=1)

        _rejected(
            self,
            lambda: authorize_member(self.char1, companion.pk, PURPOSE_ACT),
            REASON_MEMBER_CANNOT_ACT,
        )
        self.assertIs(
            authorize_member(self.char1, companion.pk, PURPOSE_ORGANIZE),
            companion,
        )

    def test_hp_above_the_floor_is_admitted_for_acting(self):
        # The floor compares the unrounded stored value: 1.5 HP is above the
        # nonlethal floor even though the integer presentation pair reads 1.
        companion = self._companion("邊緣者", hp=1.5)

        self.assertIs(
            authorize_member(self.char1, companion.pk, PURPOSE_ACT),
            companion,
        )

    def test_rejections_write_nothing(self):
        companion = self._companion("艾拉")
        outsider = create_object(NPC, key="路人", location=self.room1)
        knocked_out = self._companion("卡恩", hp=1)
        absent = self._companion("遠方者")
        self.assertTrue(absent.move_to(self.room2, quiet=True))
        entities = (self.char1, companion, outsider, knocked_out, absent)

        cases = (
            (
                lambda: authorize_member(
                    self.char1, outsider.pk, PURPOSE_ORGANIZE
                ),
                REASON_NOT_PARTY_MEMBER,
            ),
            (
                lambda: authorize_member(self.char1, 10**9, PURPOSE_ACT),
                REASON_NOT_PARTY_MEMBER,
            ),
            (
                lambda: authorize_member(self.char1, absent.pk, PURPOSE_ORGANIZE),
                REASON_MEMBER_NOT_PRESENT,
            ),
            (
                lambda: authorize_member(self.char1, knocked_out.pk, PURPOSE_ACT),
                REASON_MEMBER_CANNOT_ACT,
            ),
        )
        for call, reason in cases:
            before = [_attribute_rows(entity) for entity in entities]
            _rejected(self, call, reason)
            self.assertEqual(
                [_attribute_rows(entity) for entity in entities],
                before,
                "a membership rejection must leave every persistent attribute unchanged",
            )


class PresentPartyScopeTests(PartyScopeTestCase):
    """The present scope is ordered, room-bound, and always includes the actor."""

    def test_scope_lists_the_commander_then_roster_order(self):
        first = self._companion("艾拉")
        second = self._companion("卡恩")

        self.assertEqual(
            present_party_scope(self.char1), (self.char1, first, second)
        )

    def test_companion_elsewhere_is_outside_the_scope(self):
        first = self._companion("艾拉")
        second = self._companion("卡恩")
        self.assertTrue(second.move_to(self.room2, quiet=True))

        self.assertEqual(present_party_scope(self.char1), (self.char1, first))

    def test_possession_does_not_change_the_scope(self):
        first = self._companion("艾拉")
        second = self._companion("卡恩")
        before = present_party_scope(self.char1)

        enter_possession(self.char1, first)

        self.assertEqual(before, (self.char1, first, second))
        self.assertEqual(present_party_scope(first), before)

    def test_duplicate_roster_entries_appear_once(self):
        first = self._companion("艾拉")
        second = self._companion("卡恩")
        self.char1.db.party = [first.pk, first.pk, second.pk, second.pk]

        self.assertEqual(
            present_party_scope(self.char1), (self.char1, first, second)
        )

    def test_empty_party_is_the_commander(self):
        self.assertEqual(present_party_scope(self.char2), (self.char2,))

    def test_rootless_commander_is_the_whole_scope(self):
        rootless = create_object(PlayerCharacter, key="無根者")

        self.assertEqual(present_party_scope(rootless), (rootless,))

    def test_acting_figure_left_behind_is_still_in_scope(self):
        first = self._companion("艾拉")
        second = self._companion("卡恩")
        enter_possession(self.char1, first)
        # A non-exit relocation after possession: the figure that acted is out
        # of the commander's room but must never be omitted from the scope.
        first.location = self.room2

        self.assertEqual(
            present_party_scope(first), (self.char1, second, first)
        )


class MemberTokenTests(PartyScopeTestCase):
    """Text tokens resolve by exact name inside the party only."""

    def test_plain_key_resolves(self):
        companion = self._companion("艾拉")

        self.assertIs(resolve_member_token(self.char1, "艾拉"), companion)

    def test_surrounding_whitespace_is_ignored(self):
        companion = self._companion("艾拉")

        self.assertIs(resolve_member_token(self.char1, "  艾拉 "), companion)

    def test_titled_companion_resolves_by_composed_name_and_bare_key(self):
        companion = self._companion("艾拉")
        companion.npc_title = "見習劍士"

        self.assertIs(
            resolve_member_token(self.char1, "艾拉　見習劍士"), companion
        )
        self.assertIs(resolve_member_token(self.char1, "艾拉"), companion)

    def test_unknown_and_blank_tokens_are_rejected(self):
        self._companion("艾拉")
        create_object(NPC, key="路人", location=self.room1)
        for token in ("路人", "不存在", "", "   ", None, 5):
            with self.subTest(token=token):
                _rejected(
                    self,
                    lambda: resolve_member_token(self.char1, token),
                    REASON_NOT_PARTY_MEMBER,
                )

    def test_ambiguous_token_is_rejected(self):
        self._companion("雙胞胎")
        self._companion("雙胞胎")

        _rejected(
            self,
            lambda: resolve_member_token(self.char1, "雙胞胎"),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_composed_name_collision_is_rejected(self):
        titled = self._companion("甲")
        titled.npc_title = "乙"
        self._companion("甲　乙")

        _rejected(
            self,
            lambda: resolve_member_token(self.char1, "甲　乙"),
            REASON_NOT_PARTY_MEMBER,
        )

    def test_commander_is_a_legitimate_match(self):
        self._companion("艾拉")

        self.assertIs(resolve_member_token(self.char1, self.char1.key), self.char1)

    def test_remote_companion_resolves_but_is_not_present(self):
        # Token resolution is identity-only; presence is authorized separately.
        companion = self._companion("卡恩")
        self.assertTrue(companion.move_to(self.room2, quiet=True))

        self.assertIs(resolve_member_token(self.char1, "卡恩"), companion)
        _rejected(
            self,
            lambda: authorize_member(self.char1, companion.pk, PURPOSE_ORGANIZE),
            REASON_MEMBER_NOT_PRESENT,
        )

    def test_token_rejections_write_nothing(self):
        first = self._companion("艾拉")
        create_object(NPC, key="路人", location=self.room1)
        entities = (self.char1, first)

        for token in ("路人", "不存在"):
            before = [_attribute_rows(entity) for entity in entities]
            _rejected(
                self,
                lambda token=token: resolve_member_token(self.char1, token),
                REASON_NOT_PARTY_MEMBER,
            )
            self.assertEqual(
                [_attribute_rows(entity) for entity in entities], before
            )

        self._companion("雙胞胎")
        self._companion("雙胞胎")
        before = [_attribute_rows(entity) for entity in entities]
        _rejected(
            self,
            lambda: resolve_member_token(self.char1, "雙胞胎"),
            REASON_NOT_PARTY_MEMBER,
        )
        self.assertEqual(
            [_attribute_rows(entity) for entity in entities], before
        )


class PartyInCombatTests(PartyScopeTestCase):
    """Combat activity is judged across every involved member."""

    def _in_combat(self, *in_combat):
        def predicate(actor):
            return any(actor is member for member in in_combat)

        return patch(
            "world.rules.combat_session.is_in_active_session",
            side_effect=predicate,
        )

    def test_possessed_figure_in_combat_bars_the_request(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)

        with self._in_combat(companion):
            self.assertTrue(party_in_combat(companion))
            self.assertTrue(party_in_combat(self.char1, companion))

    def test_commander_in_combat_bars_a_request_made_through_the_figure(self):
        companion = self._companion("艾拉")
        enter_possession(self.char1, companion)

        with self._in_combat(self.char1):
            self.assertTrue(party_in_combat(companion))

    def test_named_member_in_combat_bars_the_request(self):
        companion = self._companion("艾拉")

        with self._in_combat(companion):
            self.assertTrue(party_in_combat(self.char1, companion))
            self.assertFalse(party_in_combat(self.char1))

    def test_no_active_session_is_not_in_combat(self):
        companion = self._companion("艾拉")

        with self._in_combat():
            self.assertFalse(party_in_combat(self.char1, companion))

    def test_every_involved_identity_is_consulted(self):
        companion = self._companion("艾拉")
        consulted = []

        def predicate(actor):
            consulted.append(actor)
            return False

        with patch(
            "world.rules.combat_session.is_in_active_session",
            side_effect=predicate,
        ):
            self.assertFalse(party_in_combat(self.char1, companion))

        self.assertEqual(consulted, [self.char1, companion])

    def test_non_party_actor_returns_false_instead_of_raising(self):
        with self._in_combat():
            self.assertFalse(party_in_combat(self.obj1))
