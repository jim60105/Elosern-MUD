"""Tests for the party membership module (party-core).

Covers the sole-writer contract for ``player.db.party`` and
``npc.db.party_member`` (``join_party`` / ``leave_party`` /
``purge_npc_memberships``), the deterministic join gates (target, co-location,
duplicate, 4-companion bound), atomicity with in-process restore under fault
injection, reload persistence, the deletion-purge path, stale-dbid reads, and
the wired auto-leave rule run from the affinity writer's negative-delta path.
"""

from tools.spec_traceability import covers_requirement

import ast
import re
from pathlib import Path
from unittest.mock import patch
import unittest

from django.db import transaction

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage, QuestType
from world.quests.runtime import QuestState, read_records, to_storage
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import get_config
from world.rules.character_creation import (
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.party import combat_companions, follow_companions
from world.rules.party import (
    ALREADY_COMPANION_MESSAGE,
    AUTO_LEAVE_MESSAGE,
    PARTY_MAX_COMPANIONS,
    REASON_ALREADY_COMPANION,
    REASON_NOT_CO_LOCATED,
    REASON_NOT_NPC,
    REASON_PARTY_FULL,
    PartyJoinError,
    PartyWriteError,
    is_companion,
    join_party,
    leave_party,
    live_companion_ids,
    live_companions,
    party_ids,
    party_size,
    purge_npc_memberships,
)
from typeclasses.rooms import AnchorRoom
from evennia.utils.create import create_account
from evennia.utils.test_resources import EvenniaTest
from typeclasses.accounts import Account

from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    anchor_locator,
    quest,
    reach,
    register,
)
from world.rules.tests._combat_session_helpers import _race_key, open_synthetic_scope
from world.tests.synthetic_data import SYNTH_PRESETS

# Activation parity rides the kit card: the synthetic preset (with its
# declared companion chain) and the kit race/subrace/kit registries replace
# the shipped activation data, and the quest's anchor destination resolves
# through the patched placement registry to a locally built AnchorRoom.
_T_PRESET = next(iter(SYNTH_PRESETS))  # t_pale_wren: declares a twin
_SCOPE_LOGICALS = (
    "presets",
    "races",
    "subraces",
    "static_tiers",
    "starting_kits",
    "items",
    "prices",
    "skills",
    "elements",
    "anchors",
    "anchor_placements",
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_OWNERSHIP_EXCLUSIONS = ("world/rules/party.py",)


def _production_sources(root: Path, package: str):
    """Yield (package-relative_path, text) for non-test Python files."""
    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts
        if "tests" in parts or "__pycache__" in parts:
            continue
        yield f"{package}/{path.relative_to(root).as_posix()}", path.read_text(encoding="utf-8")


class MembershipOwnershipContractTests(unittest.TestCase):
    """No module outside ``world/rules/party.py`` assigns party attributes."""

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_only_party_module_assigns_the_membership_attributes(self):
        offenders = []
        for package in ("world", "typeclasses", "commands", "web", "server"):
            for relative, source in _production_sources(REPO_ROOT / package, package):
                if relative in _OWNERSHIP_EXCLUSIONS:
                    continue
                for attribute in ("db.party", "db.party_member"):
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if not isinstance(node, ast.Assign):
                            continue
                        for target in node.targets:
                            if ast.unparse(target).startswith(attribute):
                                offenders.append(f"{relative}: assigns {attribute}")
                    if re.search(rf"\b{attribute}\s*=\s*", source) is not None:
                        offenders.append(f"{relative}: assigns {attribute}")
        self.assertEqual(offenders, [])


class PartyMembershipTests(EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "races", "subraces", "static_tiers")
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="party room")
        self.player = create_object(PlayerCharacter, key="party player")
        self.player.race = _race_key()
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="party npc", location=self.room)

    def _other_room(self):
        return create_object(Room, key="elsewhere")

    def _join(self, count):
        """Bind ``count`` distinct NPCs to the player and return them."""
        npcs = []
        for index in range(count):
            npc = create_object(NPC, key=f"companion {index}", location=self.room)
            join_party(npc, self.player)
            npcs.append(npc)
        return npcs

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_valid_join_binds_both_sides(self):
        existing = self._join(2)
        join_party(self.npc, self.player)
        self.assertEqual(party_ids(self.player), [npc.pk for npc in (*existing, self.npc)])
        self.assertEqual(len(party_ids(self.player)), 3)
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))
        self.assertTrue(is_companion(self.npc, self.player))
        self.assertEqual(party_size(self.player), 3)

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_party_bound_rejects_a_fifth_join(self):
        companions = self._join(PARTY_MAX_COMPANIONS)
        with self.assertRaises(PartyJoinError) as context:
            join_party(self.npc, self.player)
        self.assertEqual(context.exception.reason, REASON_PARTY_FULL)
        self.assertEqual(party_ids(self.player), [npc.pk for npc in companions])
        self.assertFalse(is_companion(self.npc, self.player))

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_remote_npc_cannot_join(self):
        other = self._other_room()
        far = create_object(NPC, key="far npc", location=other)
        with self.assertRaises(PartyJoinError) as context:
            join_party(far, self.player)
        self.assertEqual(context.exception.reason, REASON_NOT_CO_LOCATED)
        self.assertEqual(party_ids(self.player), [])
        self.assertIsNone(far.db.party_member)

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_duplicate_join_is_rejected_without_change(self):
        join_party(self.npc, self.player)
        before = party_ids(self.player)
        with self.assertRaises(PartyJoinError) as context:
            join_party(self.npc, self.player)
        self.assertEqual(context.exception.reason, REASON_ALREADY_COMPANION)
        self.assertEqual(party_ids(self.player), before)
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_non_npc_target_is_rejected(self):
        other = create_object(Room, key="target room", location=self.room)
        with self.assertRaises(PartyJoinError) as context:
            join_party(other, self.player)
        self.assertEqual(context.exception.reason, REASON_NOT_NPC)

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_join_write_failure_restores_both_entities(self):
        before_player = list(self.player.db.party or [])
        original_add = self.npc.attributes.add
        armed = {"active": True}

        def _failing_add(key, *args, **kwargs):
            if armed["active"] and key == "party_member":
                armed["active"] = False
                raise RuntimeError("injected party_member write failure")
            return original_add(key, *args, **kwargs)

        with patch.object(self.npc.attributes, "add", side_effect=_failing_add):
            with self.assertRaises(PartyWriteError):
                join_party(self.npc, self.player)
        self.assertEqual(party_ids(self.player), before_player)
        self.assertIsNone(self.npc.db.party_member)
        self.npc.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(party_ids(self.player), before_player)
        self.assertIsNone(self.npc.db.party_member)

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_membership_survives_a_simulated_reload(self):
        join_party(self.npc, self.player)
        self.player.attributes.reset_cache()
        self.npc.attributes.reset_cache()
        self.assertEqual(party_ids(self.player), [self.npc.pk])
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))
        self.assertTrue(is_companion(self.npc, self.player))

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_leave_is_idempotent_and_removes_both_sides(self):
        join_party(self.npc, self.player)
        leave_party(self.npc, self.player, reason="dismissed")
        self.assertEqual(party_ids(self.player), [])
        self.assertIsNone(self.npc.db.party_member)
        self.assertFalse(is_companion(self.npc, self.player))
        leave_party(self.npc, self.player, reason="dismissed")

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_leave_of_a_non_bound_npc_is_a_no_op(self):
        leave_party(self.npc, self.player, reason="dismissed")
        self.assertEqual(party_ids(self.player), [])

    @covers_requirement("party-system::deleting-an-npc-purges-its-party-bindings")
    def test_deleting_a_bound_npc_frees_the_slot(self):
        self._join(PARTY_MAX_COMPANIONS - 1)
        join_party(self.npc, self.player)
        self.npc.delete()
        self.assertNotIn(self.npc.pk, party_ids(self.player))
        self.assertEqual(party_size(self.player), PARTY_MAX_COMPANIONS - 1)
        newcomer = create_object(NPC, key="newcomer", location=self.room)
        join_party(newcomer, self.player)
        self.assertEqual(party_size(self.player), PARTY_MAX_COMPANIONS)

    @covers_requirement("party-system::deleting-an-npc-purges-its-party-bindings")
    def test_purge_is_idempotent(self):
        join_party(self.npc, self.player)
        purge_npc_memberships(self.npc)
        purge_npc_memberships(self.npc)
        self.assertEqual(party_ids(self.player), [])
        self.assertIsNone(self.npc.db.party_member)

    @covers_requirement("party-system::deleting-an-npc-purges-its-party-bindings")
    def test_stale_dbid_reads_as_absent(self):
        join_party(self.npc, self.player)
        stale = self.npc.pk
        self.npc.delete()
        # Simulate a corrupt binding whose NPC no longer exists (purge
        # bypassed): reads must treat the stale dbid as absent, never crash.
        self.player.db.party = [stale]
        self.assertEqual(party_ids(self.player), [stale])
        self.assertEqual(live_companion_ids(self.player), [])
        self.assertEqual(party_size(self.player), 0)
        other = create_object(NPC, key="other", location=self.room)
        self.assertFalse(is_companion(other, self.player))
        join_party(other, self.player)
        # The join writes the cleaned list: the stale dbid is dropped.
        self.assertEqual(party_ids(self.player), [other.pk])
        self.assertEqual(party_size(self.player), 1)

    @covers_requirement("party-system::deleting-an-npc-purges-its-party-bindings")
    def test_stale_dbid_never_permanently_consumes_capacity(self):
        stale = []
        for index in range(PARTY_MAX_COMPANIONS):
            npc = create_object(NPC, key=f"gone {index}", location=self.room)
            join_party(npc, self.player)
            stale.append(npc.pk)
            npc.delete()
        self.assertEqual(party_ids(self.player), [])
        self.assertEqual(party_size(self.player), 0)
        # A join must succeed despite the four stale entries.
        join_party(self.npc, self.player)
        self.assertEqual(party_size(self.player), 1)
        self.assertEqual(party_ids(self.player), [self.npc.pk])

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_leave_never_clears_a_backref_owned_by_another_player(self):
        other_player = create_object(PlayerCharacter, key="other player")
        other_player.race = _race_key()
        other_player.apply_race_baseline()
        other_player.location = self.room
        join_party(self.npc, self.player)
        # A corrupt backref held by another player must survive this leave.
        self.npc.db.party_member = other_player.pk
        leave_party(self.npc, self.player, reason="dismissed")
        self.assertNotIn(self.npc.pk, party_ids(self.player))
        self.assertEqual(int(self.npc.db.party_member), int(other_player.pk))


class AutoLeaveIntegrationTests(EvenniaTestCase):
    """The wired auto-leave rule run from the affinity writer (party-core D-5)."""

    def setUp(self):
        open_synthetic_scope(self, "races", "subraces", "static_tiers")
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="auto room")
        self.player = create_object(PlayerCharacter, key="auto player")
        self.player.race = _race_key()
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="auto npc", location=self.room)
        self.threshold = get_config().invite_threshold

    def _bind_at(self, value):
        apply_affinity_change(self.npc, self.player, AffinitySource.QUEST_COMPLETION, value)
        join_party(self.npc, self.player)

    @covers_requirement("party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold")
    def test_below_threshold_drop_ends_the_party_and_returns_the_notification(self):
        self._bind_at(self.threshold)
        with patch.object(self.player, "msg") as msg:
            outcome = apply_affinity_change(
                self.npc, self.player, AffinitySource.TALK, -1
            )
        self.assertEqual(outcome.delta_used, -1)
        self.assertEqual(self.npc.relations.affinity_for(self.player), self.threshold - 1)
        self.assertFalse(is_companion(self.npc, self.player))
        self.assertIsNone(self.npc.db.party_member)
        # The writer never notifies; the caller sends the returned line only
        # after its own transaction commits (party-core D-5).
        self.assertEqual(outcome.auto_leave_notification, AUTO_LEAVE_MESSAGE)
        self.assertEqual(msg.call_count, 0)

    @covers_requirement("party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold")
    def test_caller_sends_the_auto_leave_notification_after_its_commit(self):
        self._bind_at(self.threshold)
        with patch.object(self.player, "msg") as msg:
            with transaction.atomic():
                outcome = apply_affinity_change(
                    self.npc, self.player, AffinitySource.TALK, -1
                )
                self.assertEqual(outcome.auto_leave_notification, AUTO_LEAVE_MESSAGE)
                # The writer never sends inside the transaction; the caller
                # owns the notification (party-core D-5).
                self.assertEqual(msg.call_count, 0)
            # The caller's transaction committed; it now notifies the player.
            self.assertEqual(msg.call_count, 0)
            self.assertEqual(self.npc.relations.affinity_for(self.player), self.threshold - 1)
            self.assertFalse(is_companion(self.npc, self.player))
            msg(outcome.auto_leave_notification)
        self.assertEqual([str(call.args[0]) for call in msg.call_args_list], [AUTO_LEAVE_MESSAGE])

    @covers_requirement("party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold")
    def test_at_threshold_drop_keeps_the_party(self):
        self._bind_at(self.threshold)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 2
        )
        self.assertEqual(outcome.delta_used, 2)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.TALK, -2
        )
        self.assertEqual(outcome.delta_used, -2)
        self.assertEqual(self.npc.relations.affinity_for(self.player), self.threshold)
        self.assertTrue(is_companion(self.npc, self.player))
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))
        self.assertIsNone(outcome.auto_leave_notification)

    @covers_requirement("party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold")
    def test_non_companion_negative_delta_runs_the_hook_without_effects(self):
        apply_affinity_change(self.npc, self.player, AffinitySource.QUEST_COMPLETION, 90)
        with patch.object(self.player, "msg") as msg:
            outcome = apply_affinity_change(
                self.npc, self.player, AffinitySource.TALK, -5
            )
        self.assertEqual(outcome.delta_used, -5)
        self.assertIsNone(outcome.auto_leave_notification)
        self.assertEqual(msg.call_count, 0)
        self.assertIsNone(self.npc.db.party_member)

    @covers_requirement("party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold")
    def test_failed_auto_leave_rolls_back_the_affinity_write(self):
        self._bind_at(self.threshold)
        original_add = self.npc.attributes.add
        armed = {"active": True}

        def _failing_add(key, *args, **kwargs):
            if armed["active"] and key == "party_member":
                armed["active"] = False
                raise RuntimeError("injected party_member write failure")
            return original_add(key, *args, **kwargs)

        with patch.object(self.player, "msg") as msg:
            with patch.object(self.npc.attributes, "add", side_effect=_failing_add):
                with self.assertRaises(PartyWriteError):
                    apply_affinity_change(
                        self.npc, self.player, AffinitySource.TALK, -1
                    )
        self.assertEqual(self.npc.relations.affinity_for(self.player), self.threshold)
        self.assertTrue(is_companion(self.npc, self.player))
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))
        self.npc.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(self.npc.relations.affinity_for(self.player), self.threshold)
        self.assertTrue(is_companion(self.npc, self.player))
        self.assertEqual(msg.call_count, 0)


class ActivationBoundParityTests(QuestRegistryIsolation, EvenniaTest):
    """Activation-bound companions behave exactly like invited ones.

    Party membership is origin-agnostic: the sole-writer surfaces are the
    same, so every consumer (follow, combat, quest-assist arrival
    observation, dismissal) must treat an activation-bound companion and an
    invited NPC identically (party-system delta).
    """

    def setUp(self):
        # Scope before construction: entity races, the activation card, and
        # the quest anchor all resolve through the patched registries, so no
        # shipped grid content is consulted (the anchor room is built locally
        # under the kit placement key).
        open_synthetic_scope(self, *_SCOPE_LOGICALS)
        super().setUp()
        register_catalog()
        self.anchor = create_object(AnchorRoom, key="parity anchor room")
        self.anchor.anchor_key = anchor_locator().anchor_key
        self.assertIsInstance(self.anchor, AnchorRoom)
        self.account = create_account(
            "parity-maker", "parity@example.test", "testpassword", typeclass=Account
        )
        self.invited = create_object(NPC, key="受邀夥伴", location=self.room1)
        self.invited.race = _race_key()
        self.invited.apply_race_baseline()
        self.player = None

    def _activate_parity_player(self, key: str) -> PlayerCharacter:
        """A freshly activated kit-card holder with her bound twin in ``room1``."""
        shell = create_object(PlayerCharacter, key=key)
        self.account.at_post_create_character(shell)
        shell.location = self.room1
        activate_player_character(
            self.account, shell,
            CharacterCreationRequest(mode="preset", preset_key=_T_PRESET),
        )
        return shell

    def _records(self, player):
        return [to_storage(record) for record in read_records(player)]

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_activation_binding_writes_the_same_membership_surfaces(self):
        # The activation writes exactly what a join_party() writes: the same
        # party/party_member surfaces, so consumers never branch on origin.
        player = self._activate_parity_player("parity-shell")
        bound = player.db.party
        self.assertEqual(len(bound), 1)
        companion = self.invited
        join_party(companion, player)
        self.assertEqual(party_size(player), 2)
        for npc in (
            live_companions(player)[0],
            companion,
        ):
            self.assertEqual(int(npc.db.party_member), int(player.pk))
        self.assertTrue(is_companion(companion, player))

    @covers_requirement("party-system::party-membership-is-bounded-persistent-and-single-writer")
    def test_follow_combat_and_dismissal_treat_both_origins_identically(self):
        player = self._activate_parity_player("parity-shell-2")
        bound = live_companions(player)[0]
        join_party(self.invited, player)
        # Follow: both origins move together with the player.
        player.move_to(self.room2, quiet=True)
        follow_companions(player, self.room1, destination=self.room2)
        self.assertIs(player.location, self.room2)
        self.assertIs(bound.location, self.room2)
        self.assertIs(self.invited.location, self.room2)
        # Combat: both are collected at the destination.
        engaged = {int(npc.pk) for npc in combat_companions(player)}
        self.assertEqual(engaged, {int(bound.pk), int(self.invited.pk)})
        # Quest assist: the followed companion's presence drives the arrival
        # observation at the anchor stage (party-follow D-2 re-observation).
        definition = register(
            quest(
                "reach_activation_bound",
                quest_type=QuestType.EXPLORE,
                stages=(QuestStage(0, reach(anchor_locator())),),
            )
        )
        record = accept(player, definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        player.move_to(self.anchor, quiet=True)
        follow_companions(player, self.room2, destination=self.anchor)
        stored = self._records(player)[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)
        # Dismissal: leave unwrites both identically.
        leave_party(bound, player, reason="dismissed")
        leave_party(self.invited, player, reason="dismissed")
        self.assertFalse(is_companion(bound, player))
        self.assertFalse(is_companion(self.invited, player))
        self.assertEqual(party_ids(player), [])
        self.assertEqual(party_size(player), 0)
        self.assertIsNone(bound.db.party_member)
        self.assertIsNone(self.invited.db.party_member)


if __name__ == "__main__":
    unittest.main()
