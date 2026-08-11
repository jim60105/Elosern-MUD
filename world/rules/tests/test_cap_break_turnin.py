"""Guild turn-in cap-break integration tests (affinity-cap-break 4.2).

Covers the deterministic milestone contract: turning in a quest whose
``cap_breaks`` entry matches a then-in-party companion raises that companion's
affinity cap inside the same atomic transaction as the reward and the
``quest_completion`` gains, before those gains so a record at the old cap
cannot clamp the +2. Also covers no-op entries, idempotent re-completion,
recordless companions, overlapping entries resolving to the highest ``new_cap``,
role-selector matching, and fault-injection restore of caps and values.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.runtime import QuestState, accept_quest, fulfill_record, read_records
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.affinity import (
    AffinitySource,
    apply_affinity_change,
    raise_affinity_cap,
)
from world.rules.affinity_config import load_config
from world.rules.guild import register_adventurer, turn_in_quest
from world.rules.guild_config import load_catalog_into_cache, register_catalog_offers
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.party import join_party
from world.rules.npc_schedules import set_npc_schedule

ALTORIA_BRANCH = "guild_branch_altoria"
MATCHED_NPC_KEY = "altoria_guild_master"


def _attach_staff(npc) -> None:
    npc.components.add(
        GuildStaff.create(npc, service_id="staff", branch_key=ALTORIA_BRANCH)
    )


class CapBreakTurnInBase(EvenniaTest):
    """Shared turn-in scaffold: staff, registered intro hunt offer, party."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.hall = create_object(Room, key="cap hall")
        self.staff = create_object(NPC, key="cap staff", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="cap player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        self.offer = GuildQuestOffer(
            definition_key="introductory_hunt",
            issuer_branch_key=ALTORIA_BRANCH,
            reward=QuestReward(
                copper=50, items=(ItemQuantity("healing_potion", 1),), merit=25
            ),
        )
        register_guild_offer(self.offer)

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

    def _complete(self, acceptance: int = 1) -> str:
        from world.quests.transitions import apply_quest_log_replacement

        record = accept_quest(self.player, "introductory_hunt")
        completed = fulfill_record(
            record, QUEST_DEFINITION_REGISTRY["introductory_hunt"]
        )
        records = read_records(self.player)
        new_records = [
            completed if r.quest_id == record.quest_id else r for r in records
        ]
        apply_quest_log_replacement(self.player, new_records)
        return completed.quest_id

    def _companion(self, key: str) -> NPC:
        npc = create_object(NPC, key=key, location=self.hall)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        return npc

    def _with_rulebook(self, config):
        """Return a context manager substituting ``get_config`` for one test.

        The affinity config singleton is read through ``get_config`` at the
        turn-in call path; patching the accessor (never the frozen module
        singleton) keeps the override scoped to the test.
        """
        return patch("world.rules.affinity_config.get_config", return_value=config)


class CapBreakTurnInTests(CapBreakTurnInBase):
    """Matching companion caps rise in the same transaction as the reward."""

    @covers_requirement("affinity-cap-break::the-cap-breaks-rulebook-table-drives-milestone-cap-raises-at-quest-turn-in")
    def test_matching_companion_cap_rises_with_the_reward(self):
        matching = self._companion(MATCHED_NPC_KEY)
        self._companion("non-matching companion")
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(self.player.db.wallet, 50)
        self.assertEqual(matching.relations._load(self.player).cap, 150)
        self.assertEqual(matching.relations.affinity_for(self.player), 2)

    def test_non_matching_entry_is_a_no_op(self):
        companion = self._companion("some other npc")
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(companion.relations._load(self.player).cap, 99)
        self.assertEqual(companion.relations.affinity_for(self.player), 2)

    def test_cap_break_does_not_lose_the_turn_in_gain(self):
        companion = self._companion(MATCHED_NPC_KEY)
        apply_affinity_change(
            companion, self.player, AffinitySource.QUEST_COMPLETION, 99
        )
        record = companion.relations._load(self.player)
        self.assertEqual(record.value, 99)
        self.assertEqual(record.cap, 99)
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        record = companion.relations._load(self.player)
        self.assertEqual(record.cap, 150)
        self.assertEqual(record.value, 101)

    def test_recordless_matching_companion_still_gets_its_cap_break(self):
        companion = self._companion(MATCHED_NPC_KEY)
        self.assertFalse(companion.relations.has_record(self.player))
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        record = companion.relations._load(self.player)
        self.assertEqual(record.cap, 150)
        self.assertEqual(record.value, 2)

    def test_re_completing_a_milestone_is_idempotent(self):
        matching = self._companion(MATCHED_NPC_KEY)
        first = self._complete(1)
        turn_in_quest(self.player, self.staff, first)
        self.assertEqual(matching.relations._load(self.player).cap, 150)
        second = self._complete(2)
        turn_in_quest(self.player, self.staff, second)
        self.assertEqual(matching.relations._load(self.player).cap, 150)
        self.assertEqual(matching.relations.affinity_for(self.player), 4)

    def test_multiple_matching_entries_resolve_to_the_highest_new_cap(self):
        base = load_config()
        entry = base.cap_breaks[0]
        extra = replace(
            entry,
            new_cap=200,
        )
        with self._with_rulebook(replace(base, cap_breaks=(*base.cap_breaks, extra))):
            matching = self._companion(MATCHED_NPC_KEY)
            quest_id = self._complete()
            turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(matching.relations._load(self.player).cap, 200)

    def test_role_selector_matches_the_schedule_role_template_key(self):
        base = load_config()
        guard = replace(
            base.cap_breaks[0],
            selector_kind="role",
            selector="guard",
        )
        with self._with_rulebook(replace(base, cap_breaks=(guard,))):
            companion = self._companion("值班衛兵")
            set_npc_schedule(companion, {"schema_version": 1, "template": "guard"})
            self._companion("無排班路人")
            quest_id = self._complete()
            turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(companion.relations._load(self.player).cap, 150)

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
    @covers_requirement("affinity-cap-break::the-cap-breaks-rulebook-table-drives-milestone-cap-raises-at-quest-turn-in")
    def test_fault_injection_restores_caps_and_values(self):
        matching = self._companion(MATCHED_NPC_KEY)
        apply_affinity_change(
            matching, self.player, AffinitySource.QUEST_COMPLETION, 30
        )
        record_before = matching.relations._load(self.player)
        cap_snapshot = record_before.cap
        quest_id = self._complete()

        def _failing_raise(npc, player, new_cap):
            raise RuntimeError("injected cap raise failure")

        with patch(
            "world.rules.affinity.raise_affinity_cap", side_effect=_failing_raise
        ):
            with self.assertRaises(RuntimeError):
                turn_in_quest(self.player, self.staff, quest_id)
        record = matching.relations._load(self.player)
        self.assertEqual(record.cap, cap_snapshot)
        self.assertEqual(record.value, 30)
        self.assertEqual(self.player.db.wallet, 0)


class OfferSyncIsolationRegressionTests(RegistryIsolationMixin, unittest.TestCase):
    """Regression: catalog-offer registration must not leak from a failing setup.

    The pre-fix CI failure: ``OnboardingHuntIntegrationTests`` registered the
    canonical ×2 healing-potion offer and left it behind, so the conflicting
    ×1 registration in ``CapBreakTurnInTests.setUp`` raised
    ``GuildOfferError``. The single test below proves the restoration contract
    directly, so it holds under any test ordering (serial, parallel, shuffled,
    reversed). The class itself mutates the offer registry (the successful
    conflicting registration at the end), so it restores the three registries
    around every test.
    """

    @covers_requirement("evennia-test-optimization::tests-restore-process-global-registry-state")
    def test_failing_setup_does_not_leak_the_canonical_offer(self):
        from world.quests.compile import SCENE_REQUIREMENT_REGISTRY

        class _FailingSetupProbe(RegistryIsolationMixin, unittest.TestCase):
            """A case whose setUp registers the catalog offers and then fails."""

            def setUp(self):
                super().setUp()
                register_catalog()
                register_catalog_offers(load_catalog_into_cache())
                raise RuntimeError("injected failure after offer registration")

            def runTest(self):
                pass

        quests_before = dict(QUEST_DEFINITION_REGISTRY)
        offers_before = dict(GUILD_OFFER_REGISTRY)
        requirements_before = dict(SCENE_REQUIREMENT_REGISTRY)

        probe = _FailingSetupProbe("runTest")
        result = unittest.TestResult()
        probe.run(result)
        self.assertEqual(len(result.errors), 1)

        self.assertEqual(dict(QUEST_DEFINITION_REGISTRY), quests_before)
        self.assertEqual(dict(GUILD_OFFER_REGISTRY), offers_before)
        self.assertEqual(dict(SCENE_REQUIREMENT_REGISTRY), requirements_before)

        # With the canonical offer gone, the conflicting ×1 registration that
        # broke CI succeeds (the catalog definitions are re-registered exactly
        # as ``CapBreakTurnInBase.setUp`` does).
        register_catalog()
        offer = GuildQuestOffer(
            definition_key="introductory_hunt",
            issuer_branch_key=ALTORIA_BRANCH,
            reward=QuestReward(
                copper=50, items=(ItemQuantity("healing_potion", 1),), merit=25
            ),
        )
        register_guild_offer(offer)


if __name__ == "__main__":
    import unittest

    unittest.main()
