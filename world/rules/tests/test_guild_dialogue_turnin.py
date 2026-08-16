"""Dialogue-driven guild turn-in service tests (guild-dialogue-turnin D2/D4).

These EvenniaTest cases exercise ``reportable_quest_summary`` (read-only
listing over parsed records, branch offers, and reward claims) and
``dialogue_turn_in`` (sole-local-staff enforcement before the atomic
``turn_in_quest`` settlement).
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestStage
from world.quests.runtime import (
    QuestState,
    abandon_quest,
    accept_quest,
    read_records,
)
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    acquire,
    defeat,
    quest,
    register,
)
from world.rules.guild import (
    GuildServiceError,
    RewardClaim,
    RewardClaimError,
    dialogue_turn_in,
    parse_reward_claims,
    register_adventurer,
    reportable_quest_summary,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.surfaces import read_counter_trait

ALTORIA_BRANCH = "guild_branch_altoria"
_NO_STAFF_LINE = "這裡沒有公會服務人員。"
_NOTHING_LINE = "「目前沒有可以交回的任務。」"


def _attach_staff(npc, service_id: str = "staff") -> None:
    npc.components.add(
        GuildStaff.create(npc, service_id=service_id, branch_key=ALTORIA_BRANCH)
    )


def _offer(
    definition_key: str, copper: int = 50, merit: int = 25, items=("healing_potion",)
) -> GuildQuestOffer:
    return GuildQuestOffer(
        definition_key=definition_key,
        issuer_branch_key=ALTORIA_BRANCH,
        reward=QuestReward(
            copper=copper,
            items=tuple(ItemQuantity(key, 1) for key in items),
            merit=merit,
        ),
    )


class DialogueTurnInRegistryIsolation(QuestRegistryIsolation):
    """Snapshot the offer registry too, mirroring the guild-rewards pattern."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()


class ReportableQuestSummaryTests(DialogueTurnInRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="hall")
        self.staff = create_object(NPC, key="公會職員", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="dialogue player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        from world.rules.guild_config import load_guild_catalog

        catalog_offer = load_guild_catalog(
            QUEST_DEFINITION_REGISTRY
        ).offer_by_definition["introductory_hunt"]
        register_guild_offer(catalog_offer)

    def _complete(self, definition_key: str) -> str:
        from world.quests.runtime import fulfill_record
        from world.quests.transitions import apply_quest_log_replacement

        record = accept_quest(self.player, definition_key)
        completed = fulfill_record(
            record, QUEST_DEFINITION_REGISTRY[definition_key]
        )
        records = read_records(self.player)
        new_records = [
            completed if r.quest_id == record.quest_id else r for r in records
        ]
        apply_quest_log_replacement(self.player, new_records)
        return completed.quest_id

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_listing_orders_reportable_quests_by_accepted_tick_then_quest_id(self):
        alpha = register(quest("alpha_quest", stages=(QuestStage(0, defeat()),)))
        beta = register(quest("beta_quest", stages=(QuestStage(0, defeat()),)))
        register_guild_offer(_offer(alpha.key))
        register_guild_offer(_offer(beta.key))
        alpha_id = self._complete(alpha.key)
        beta_id = self._complete(beta.key)
        summary = reportable_quest_summary(self.player, self.staff)
        self.assertIn(f"任務編號 {alpha_id}", summary)
        self.assertIn(f"任務編號 {beta_id}", summary)
        # Same accepted tick (world clock does not advance between accepts),
        # so the deterministic tiebreak is the quest id.
        self.assertLess(summary.index(alpha_id), summary.index(beta_id))
        self.assertIn("2 個任務可以交回", summary)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_listing_excludes_in_progress_failed_claimed_and_offer_less(self):
        alpha = register(quest("alpha_quest", stages=(QuestStage(0, defeat()),)))
        beta = register(quest("beta_quest", stages=(QuestStage(0, defeat()),)))
        gamma = register(quest("gamma_quest", stages=(QuestStage(0, defeat()),)))
        delta = register(quest("delta_quest", stages=(QuestStage(0, defeat()),)))
        register_guild_offer(_offer(alpha.key))
        register_guild_offer(_offer(beta.key))
        register_guild_offer(_offer(gamma.key))
        alpha_id = self._complete(alpha.key)
        dialogue_turn_in(self.player, self.staff, alpha_id)  # claimed
        beta_id = accept_quest(self.player, beta.key).quest_id  # in-progress
        gamma_id = accept_quest(self.player, gamma.key).quest_id
        abandon_quest(self.player, gamma_id)  # failed
        delta_id = self._complete(delta.key)  # completed but offer-less
        summary = reportable_quest_summary(self.player, self.staff)
        self.assertEqual(summary, _NOTHING_LINE)
        for quest_id in (alpha_id, beta_id, gamma_id, delta_id):
            self.assertNotIn(f"任務編號 {quest_id}", summary)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_listing_only_offers_quests_the_settlement_accepts(self):
        alpha = register(quest("alpha_quest", stages=(QuestStage(0, defeat()),)))
        beta = register(quest("beta_quest", stages=(QuestStage(0, defeat()),)))
        register_guild_offer(_offer(alpha.key))
        register_guild_offer(_offer(beta.key))
        alpha_id = self._complete(alpha.key)
        beta_id = self._complete(beta.key)
        summary = reportable_quest_summary(self.player, self.staff)
        for quest_id in (alpha_id, beta_id):
            self.assertIn(quest_id, summary)
            dialogue_turn_in(self.player, self.staff, quest_id)  # never rejects
        self.assertEqual(parse_reward_claims(self.player), [alpha_id, beta_id])

    def test_unregistered_player_gets_none_and_non_player_gets_none(self):
        other = create_object(PlayerCharacter, key="unregistered")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.hall
        self.assertIsNone(reportable_quest_summary(other, self.staff))
        talker = create_object(NPC, key="talker", location=self.hall)
        self.assertIsNone(reportable_quest_summary(talker, self.staff))

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_ambiguous_staff_yields_the_rejection_line(self):
        second = create_object(NPC, key="second clerk", location=self.hall)
        _attach_staff(second, service_id="second")
        self.assertEqual(
            reportable_quest_summary(self.player, self.staff), _NO_STAFF_LINE
        )

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_talked_to_npc_must_be_the_resolved_host(self):
        plain = create_object(NPC, key="plain", location=self.hall)
        self.assertEqual(
            reportable_quest_summary(self.player, plain), _NO_STAFF_LINE
        )

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_unregistered_player_still_hits_the_ambiguous_host_rule(self):
        second = create_object(NPC, key="second clerk", location=self.hall)
        _attach_staff(second, service_id="second")
        other = create_object(PlayerCharacter, key="unregistered")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.hall
        self.assertEqual(
            reportable_quest_summary(other, self.staff), _NO_STAFF_LINE
        )


class DialogueTurnInTests(DialogueTurnInRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="hall")
        self.staff = create_object(NPC, key="公會職員", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="dialogue player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        from world.rules.guild_config import load_guild_catalog

        catalog_offer = load_guild_catalog(
            QUEST_DEFINITION_REGISTRY
        ).offer_by_definition["introductory_hunt"]
        register_guild_offer(catalog_offer)

    def _complete(self) -> str:
        from world.quests.runtime import fulfill_record
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

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_turn_in_pays_exactly_once_and_completes_onboarding(self):
        quest_id = self._complete()
        result = dialogue_turn_in(self.player, self.staff, quest_id)
        self.assertEqual(result["quest_id"], quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(result["merit"], 25)
        self.assertIn("healing_potion", result["items"])
        self.assertTrue(result["onboarding_completed"])
        self.assertTrue(self.player.onboarded)
        self.assertEqual(self.player.db.wallet, 50)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 25)
        self.assertEqual(parse_reward_claims(self.player), [quest_id])

    def test_turn_in_rejects_unknown_and_already_claimed_ids(self):
        quest_id = self._complete()
        dialogue_turn_in(self.player, self.staff, quest_id)
        with self.assertRaises(RewardClaimError) as ctx:
            dialogue_turn_in(self.player, self.staff, quest_id)
        self.assertEqual(ctx.exception.args[0], RewardClaim.ALREADY_CLAIMED)
        with self.assertRaises(RewardClaimError) as ctx:
            dialogue_turn_in(self.player, self.staff, "introductory_hunt:99")
        self.assertEqual(ctx.exception.args[0], RewardClaim.NO_COMPLETED_RECORD)

    def test_turn_in_rejects_unregistered_ambiguous_and_foreign_npc(self):
        quest_id = self._complete()
        other = create_object(PlayerCharacter, key="unregistered")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.hall
        with self.assertRaises(RewardClaimError) as ctx:
            dialogue_turn_in(other, self.staff, quest_id)
        self.assertEqual(ctx.exception.args[0], RewardClaim.UNREGISTERED)

        second = create_object(NPC, key="second clerk", location=self.hall)
        _attach_staff(second, service_id="second")
        with self.assertRaises(GuildServiceError):
            dialogue_turn_in(self.player, self.staff, quest_id)

        self.staff.location = None
        plain = create_object(NPC, key="plain", location=self.hall)
        with self.assertRaises(GuildServiceError):
            dialogue_turn_in(self.player, plain, quest_id)

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
    def test_reward_item_advances_another_acquire_quest_atomically(self):
        acquire_def = register(
            quest(
                "potions_please",
                stages=(QuestStage(0, acquire("healing_potion", quantity=2)),),
            )
        )
        accept_quest(self.player, acquire_def.key)
        quest_id = self._complete()
        dialogue_turn_in(self.player, self.staff, quest_id)
        acquire_records = [
            r
            for r in read_records(self.player)
            if r.definition_key == "potions_please"
        ]
        self.assertEqual(acquire_records[0].state, QuestState.COMPLETED)
        self.assertEqual(acquire_records[0].stage_progress, 2)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_fault_injection_restores_all_surfaces(self):
        quest_id = self._complete()
        snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.quest_log),
            list(self.player.db.guild_reward_claims or []),
            self.player.onboarded,
        )

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                dialogue_turn_in(self.player, self.staff, quest_id)
        self.assertEqual(
            (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                read_counter_trait(self.player, "guild_merit"),
                list(self.player.db.quest_log),
                list(self.player.db.guild_reward_claims or []),
                self.player.onboarded,
            ),
            snapshot,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
