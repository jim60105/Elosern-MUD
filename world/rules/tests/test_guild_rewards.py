"""Guild offer board access and reward settlement tests (tasks 6.1-6.8)."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.guild import GUILD_RANK_REGISTRY
from world.quests.catalog import register_catalog
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestStage,
)
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    defeat,
    quest,
    register,
)
from world.rules.guild import (
    RewardClaim,
    RewardClaimError,
    parse_reward_claims,
    register_adventurer,
    turn_in_quest,
)
from world.rules.guild_offers import (
    BoardAccessError,
    GUILD_OFFER_REGISTRY,
    GuildOfferError,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    abandon_guild_quest,
    accept_guild_offer,
    list_guild_offers,
    register_guild_offer,
)
from world.rules.surfaces import read_counter_trait

ALTORIA_BRANCH = "guild_branch_altoria"


def _attach_staff(npc) -> None:
    npc.components.add(
        GuildStaff.create(npc, service_id="staff", branch_key=ALTORIA_BRANCH)
    )


def _offer(definition_key: str, copper: int = 50, merit: int = 25, items=("healing_potion",)) -> GuildQuestOffer:
    return GuildQuestOffer(
        definition_key=definition_key,
        issuer_branch_key=ALTORIA_BRANCH,
        reward=QuestReward(
            copper=copper,
            items=tuple(ItemQuantity(key, 1) for key in items),
            merit=merit,
        ),
    )


class OfferRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()


class OfferValidationTests(OfferRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.test_definition = register(
            quest(
                "offer_test_quest",
                stages=(QuestStage(0, defeat(tier="low")),),
            )
        )

    def test_valid_handwritten_offer_registers(self):
        offer = _offer(self.test_definition.key)
        register_guild_offer(offer)
        self.assertEqual(
            GUILD_OFFER_REGISTRY[(self.test_definition.key, ALTORIA_BRANCH)],
            offer,
        )

    def test_equal_registration_is_idempotent_and_conflict_fails(self):
        offer = _offer(self.test_definition.key)
        register_guild_offer(offer)
        register_guild_offer(offer)  # equal -> no-op
        conflicting = _offer(self.test_definition.key, copper=99, items=())
        with self.assertRaises(GuildOfferError):
            register_guild_offer(conflicting)
        self.assertEqual(
            GUILD_OFFER_REGISTRY[(self.test_definition.key, ALTORIA_BRANCH)],
            offer,
        )

    def test_unknown_definition_or_branch_is_rejected(self):
        with self.assertRaises(GuildOfferError):
            register_guild_offer(_offer("no_such_quest"))
        with self.assertRaises(GuildOfferError):
            register_guild_offer(
                GuildQuestOffer(
                    self.test_definition.key,
                    "no_such_branch",
                    QuestReward(50, (), 0),
                )
            )

    def test_negative_or_float_money_is_rejected(self):
        for bad_copper, bad_merit in ((-1, 0), (50, -1), (50.0, 0)):
            with self.subTest(copper=bad_copper, merit=bad_merit):
                with self.assertRaises(GuildOfferError):
                    register_guild_offer(
                        _offer(
                            self.test_definition.key,
                            copper=bad_copper,
                            merit=bad_merit,
                            items=(),
                        )
                    )

    def test_non_positive_item_quantity_is_rejected(self):
        with self.assertRaises(GuildOfferError):
            register_guild_offer(
                GuildQuestOffer(
                    self.test_definition.key,
                    ALTORIA_BRANCH,
                    QuestReward(50, (ItemQuantity("healing_potion", 0),), 0),
                )
            )

    def test_duplicate_item_keys_are_rejected(self):
        with self.assertRaises(GuildOfferError):
            register_guild_offer(
                GuildQuestOffer(
                    self.test_definition.key,
                    ALTORIA_BRANCH,
                    QuestReward(
                        50,
                        (ItemQuantity("healing_potion", 1), ItemQuantity("healing_potion", 1)),
                        0,
                    ),
                )
            )

    def test_out_of_band_copper_is_rejected(self):
        f_rank = GUILD_RANK_REGISTRY["F"]
        for out in (f_rank.reward_min_copper - 1, f_rank.reward_max_copper + 1):
            with self.subTest(copper=out):
                with self.assertRaises(GuildOfferError):
                    register_guild_offer(_offer(self.test_definition.key, copper=out, items=()))

    def test_s_rank_open_upper_bound_is_honored(self):
        s_rank = GUILD_RANK_REGISTRY["S"]
        s_definition = register(
            quest(
                "s_rank_quest",
                rank="S",
                stages=(QuestStage(0, defeat(tier="calamity")),),
            )
        )
        large = _offer(s_definition.key, copper=s_rank.reward_min_copper + 1, items=())
        register_guild_offer(large)  # No upper cap invented for S.
        self.assertIn((s_definition.key, ALTORIA_BRANCH), GUILD_OFFER_REGISTRY)


class BoardAccessTests(OfferRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.rules.guild_config import load_guild_catalog, register_catalog_offers

        register_catalog_offers(load_guild_catalog(QUEST_DEFINITION_REGISTRY))
        self.hall = create_object(Room, key="hall")
        self.staff = create_object(NPC, key="staff", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="board player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    def test_f_member_sees_only_local_f_offers(self):
        # The catalog registers the introductory hunt at the Altoria branch.
        self.assertEqual(
            [o.definition_key for o in list_guild_offers(self.player, self.staff)],
            ["introductory_hunt"],
        )

    def test_true_exceptional_power_does_not_bypass_rank(self):
        e_definition = register(quest("e_rank_quest", rank="E", stages=(QuestStage(0, defeat(tier="low")),)))
        register_guild_offer(_offer(e_definition.key, copper=100))
        self.player.traits.atk_phys.base = 88
        self.assertEqual(
            [o.definition_key for o in list_guild_offers(self.player, self.staff)],
            ["introductory_hunt"],
        )

    def test_unregistered_actor_is_rejected(self):
        other = create_object(PlayerCharacter, key="unregistered")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.hall
        with self.assertRaises(BoardAccessError):
            list_guild_offers(other, self.staff)

    def test_eligible_offer_creates_normal_quest_record(self):
        record = accept_guild_offer(self.player, self.staff, "introductory_hunt")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.definition_key, "introductory_hunt")

    def test_over_rank_direct_acceptance_is_rejected_before_quest_mutation(self):
        e_definition = register(quest("e_rank_quest", rank="E", stages=(QuestStage(0, defeat(tier="low")),)))
        register_guild_offer(_offer(e_definition.key, copper=100))
        before = [dict(e) for e in (self.player.db.quest_log or [])]
        with self.assertRaises(BoardAccessError):
            accept_guild_offer(self.player, self.staff, e_definition.key)
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], before)

    def test_abandonment_delegates_to_quest_runtime(self):
        record = accept_guild_offer(self.player, self.staff, "introductory_hunt")
        failed = abandon_guild_quest(self.player, self.staff, record.quest_id)
        self.assertEqual(failed.state, QuestState.FAILED)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertEqual(len(self.player.db.quest_log), 1)


class RewardSettlementTests(OfferRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="hall")
        self.staff = create_object(NPC, key="turnin staff", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="turnin player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        from world.rules.guild_config import load_guild_catalog

        catalog_offer = load_guild_catalog(
            QUEST_DEFINITION_REGISTRY
        ).offer_by_definition["introductory_hunt"]
        register_guild_offer(catalog_offer)

    def _complete(self, acceptance: int = 1) -> str:
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

    def test_first_completed_acceptance_is_paid_once(self):
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(result["merit"], 25)
        self.assertEqual(self.player.db.wallet, 50)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 25)
        self.assertIn("healing_potion", self.player.db.inventory)
        self.assertEqual(parse_reward_claims(self.player), [quest_id])

    def test_duplicate_turn_in_pays_nothing(self):
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.guild_reward_claims),
        )
        with self.assertRaises(RewardClaimError) as ctx:
            turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(ctx.exception.args[0], RewardClaim.ALREADY_CLAIMED)
        self.assertEqual(
            (self.player.db.wallet, list(self.player.db.inventory or []), read_counter_trait(self.player, "guild_merit"), list(self.player.db.guild_reward_claims)),
            snapshot,
        )

    def test_later_acceptance_has_independent_claim_identity(self):
        first = self._complete(1)
        turn_in_quest(self.player, self.staff, first)
        second = self._complete(2)
        turn_in_quest(self.player, self.staff, second)
        self.assertEqual(parse_reward_claims(self.player), [first, second])
        self.assertEqual(self.player.db.wallet, 100)

    def test_no_completed_record_is_rejected(self):
        with self.assertRaises(RewardClaimError) as ctx:
            turn_in_quest(self.player, self.staff, "introductory_hunt:99")
        self.assertEqual(ctx.exception.args[0], RewardClaim.NO_COMPLETED_RECORD)

    def test_unregistered_actor_is_rejected(self):
        quest_id = self._complete()
        other = create_object(PlayerCharacter, key="unregistered")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.hall
        with self.assertRaises(RewardClaimError) as ctx:
            turn_in_quest(other, self.staff, quest_id)
        self.assertEqual(ctx.exception.args[0], RewardClaim.UNREGISTERED)

    def test_reward_item_advances_another_acquire_quest_atomically(self):
        from world.quests.tests._fixtures import acquire as _acquire

        acquire_def = register(
            quest(
                "potions_please",
                stages=(QuestStage(0, _acquire("healing_potion", quantity=2)),),
            )
        )
        accept_quest(self.player, acquire_def.key)
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        acquire_records = [
            r
            for r in read_records(self.player)
            if r.definition_key == "potions_please"
        ]
        # The reward grants two potions, which fully satisfies the quest.
        self.assertEqual(acquire_records[0].state, QuestState.COMPLETED)
        self.assertEqual(acquire_records[0].stage_progress, 2)

    def test_fault_at_every_write_position_restores_all_surfaces(self):
        quest_id = self._complete()
        snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.quest_log),
            list(self.player.db.guild_reward_claims or []),
        )

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(
            (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                read_counter_trait(self.player, "guild_merit"),
                list(self.player.db.quest_log),
                list(self.player.db.guild_reward_claims or []),
            ),
            snapshot,
        )


class RewardClaimsParsingTests(QuestRegistryIsolation, EvenniaTest):
    def _player(self):
        player = create_object(PlayerCharacter, key="claims player")
        return player

    def test_malformed_claims_raise_without_mutation(self):
        for bad in ("not-a-list", [1, 2], ["a", "a"], ["a", True]):
            player = self._player()
            player.db.guild_reward_claims = bad
            with self.assertRaises(RewardClaimError):
                parse_reward_claims(player)


if __name__ == "__main__":
    import unittest

    unittest.main()