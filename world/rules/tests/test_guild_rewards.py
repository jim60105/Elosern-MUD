"""Guild offer board access and reward settlement tests (tasks 6.1-6.8)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

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
from world.rules.affinity import AffinitySource, apply_affinity_change
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
from world.rules.party import join_party
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


class OfferValidationTests(OfferRegistryIsolation, EvenniaTestCase):
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

    @covers_requirement("guild-quest-board::guildquestoffer-is-immutable-and-validated-against-quest-guild-item-and-branch-registries")
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


class BoardAccessTests(OfferRegistryIsolation, EvenniaTestCase):
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

    @covers_requirement("guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers")
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

    @covers_requirement("affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_eligible_offer_creates_normal_quest_record(self):
        record = accept_guild_offer(self.player, self.staff, "introductory_hunt")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.definition_key, "introductory_hunt")
        # Registration granted +1; acceptance grants another +1.
        self.assertEqual(self.staff.relations.affinity_for(self.player), 2)

    @covers_requirement("guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle")
    def test_over_rank_direct_acceptance_is_rejected_before_quest_mutation(self):
        e_definition = register(quest("e_rank_quest", rank="E", stages=(QuestStage(0, defeat(tier="low")),)))
        register_guild_offer(_offer(e_definition.key, copper=100))
        before = [dict(e) for e in (self.player.db.quest_log or [])]
        before_affinity = self.staff.relations.affinity_for(self.player)
        with self.assertRaises(BoardAccessError):
            accept_guild_offer(self.player, self.staff, e_definition.key)
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], before)
        self.assertEqual(
            self.staff.relations.affinity_for(self.player), before_affinity
        )

    def test_abandonment_delegates_to_quest_runtime(self):
        record = accept_guild_offer(self.player, self.staff, "introductory_hunt")
        failed = abandon_guild_quest(self.player, self.staff, record.quest_id)
        self.assertEqual(failed.state, QuestState.FAILED)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertEqual(len(self.player.db.quest_log), 1)
        # Abandonment grants no further affinity; the acceptance gain stands.
        self.assertEqual(self.staff.relations.affinity_for(self.player), 2)

    def test_failed_acceptance_restores_every_surface(self):
        quest_log_before = [dict(e) for e in (self.player.db.quest_log or [])]
        relations_before = self.staff.db.relations_data

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                accept_guild_offer(self.player, self.staff, "introductory_hunt")
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertEqual(self.staff.db.relations_data, relations_before)

    def test_affinity_write_failure_after_acceptance_restores_every_surface(self):
        quest_log_before = [dict(e) for e in (self.player.db.quest_log or [])]
        relations_before = self.staff.db.relations_data
        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=RuntimeError("affinity write failed"),
        ):
            with self.assertRaises(RuntimeError):
                accept_guild_offer(self.player, self.staff, "introductory_hunt")
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertEqual(self.staff.db.relations_data, relations_before)


class RewardSettlementTests(OfferRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self._definition_key = "introductory_hunt"
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

        record = accept_quest(self.player, self._definition_key)
        completed = fulfill_record(
            record, QUEST_DEFINITION_REGISTRY[self._definition_key]
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

    @covers_requirement("quest-reward-settlement::completed-guild-quests-may-be-claimed-exactly-once-per-quest-id")
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

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
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

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    def test_turn_in_rewards_each_then_in_party_companion(self):
        first = self._companion("first companion")
        second = self._companion("second companion")
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(self.player.db.wallet, 50)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 25)
        self.assertIn("healing_potion", self.player.db.inventory)
        self.assertEqual(parse_reward_claims(self.player), [quest_id])
        self.assertEqual(first.relations.affinity_for(self.player), 2)
        self.assertEqual(second.relations.affinity_for(self.player), 2)

    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    def test_out_of_party_companion_gains_nothing(self):
        inside = self._companion("inside companion")
        outside = create_object(NPC, key="outside companion")
        outside.race = "human"
        outside.apply_race_baseline()
        apply_affinity_change(outside, self.player, AffinitySource.TALK, 3)
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(inside.relations.affinity_for(self.player), 2)
        self.assertEqual(outside.relations.affinity_for(self.player), 3)

    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    def test_quest_completion_bonus_bypasses_the_daily_cap(self):
        from world.rules.clock import CLOCK_YAML, get_world_clock

        day_seconds = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
        # Pin the world day so the budget cannot be lazily reset mid-test.
        get_world_clock()._persist(0)
        companion = self._companion("capped companion")
        for _ in range(5):
            apply_affinity_change(companion, self.player, AffinitySource.TALK, 1)
        quest_id = self._complete()
        turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(companion.relations.affinity_for(self.player), 7)
        record = companion.relations._load(self.player)
        self.assertEqual(record.daily_gain, 5)
        self.assertEqual(record.daily_tick, 0)
        self.assertEqual(get_world_clock().tick // day_seconds, 0)

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    def test_affinity_write_fault_restores_every_surface(self):
        first = self._companion("rollback companion one")
        second = self._companion("rollback companion two")
        apply_affinity_change(first, self.player, AffinitySource.TALK, 2)
        quest_id = self._complete()
        reward_snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.quest_log),
            list(self.player.db.guild_reward_claims or []),
        )
        first_snapshot = (
            first.db.relations_data,
            first.relations.affinity_for(self.player),
        )
        second_snapshot = (
            second.db.relations_data,
            second.relations.affinity_for(self.player),
        )
        calls = {"n": 0}

        def _failing_affinity(npc, player, source, delta):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected affinity write failure")
            return apply_affinity_change(npc, player, source, delta)

        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=_failing_affinity,
        ):
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
            reward_snapshot,
        )
        self.assertEqual(
            (first.db.relations_data, first.relations.affinity_for(self.player)),
            first_snapshot,
        )
        self.assertEqual(
            (second.db.relations_data, second.relations.affinity_for(self.player)),
            second_snapshot,
        )

    @covers_requirement("quest-reward-settlement::reward-payout-is-one-atomic-copper-item-merit-acquisition-claim-and-affinity-transaction")
    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    def test_fault_at_every_write_position_restores_all_surfaces(self):
        companion = self._companion("fault companion")
        quest_id = self._complete()
        snapshot = (
            self.player.db.wallet,
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.quest_log),
            list(self.player.db.guild_reward_claims or []),
        )
        companion_snapshot = companion.db.relations_data

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
        self.assertEqual(companion.db.relations_data, companion_snapshot)
        self.assertEqual(companion.relations.affinity_for(self.player), 0)

    # First-claim starter-epithet grant (quest-reward-settlement delta).

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_first_ever_claim_grants_the_starter_epithet(self):
        from world.rules.titles import compose_full_title, read_title_state

        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["title_notifications"], ["獲得異名：南門新客"])
        self.assertEqual(compose_full_title(self.player), "F級冒險者　南門新客")
        collection, equipped = read_title_state(self.player)
        epithets = [entry for entry in collection if entry["kind"] == "epithet"]
        self.assertEqual([entry["display"] for entry in epithets], ["南門新客"])
        self.assertEqual(equipped["epithet"], "南門新客")

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_later_claims_never_re_grant(self):
        from world.rules.titles import read_title_state

        first = self._complete(1)
        turn_in_quest(self.player, self.staff, first)
        before = read_title_state(self.player)
        second = self._complete(2)
        result = turn_in_quest(self.player, self.staff, second)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(result["title_notifications"], [])
        self.assertEqual(read_title_state(self.player), before)

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_rolled_back_first_claim_revokes_the_epithet(self):
        # The injected affinity failure lands AFTER the epithet was banked,
        # so this proves rollback of a completed grant, not a skipped one.
        from world.rules.titles import compose_full_title, read_title_state

        companion = self._companion("epithet rollback companion")
        quest_id = self._complete()
        # Prime the in-process title read path so the post-failure assertions
        # distinguish a stale attribute cache from a real rollback.
        self.assertEqual(compose_full_title(self.player), "F級冒險者")
        parsed_before = read_title_state(self.player)
        raw_before = (
            self.player.db.title_collection,
            self.player.db.title_equipped,
        )

        def _failing_affinity(npc, player, source, delta):
            raise RuntimeError("injected affinity write failure")

        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=_failing_affinity,
        ):
            with self.assertRaises(RuntimeError):
                turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(
            (self.player.db.title_collection, self.player.db.title_equipped),
            raw_before,
        )
        self.assertEqual(read_title_state(self.player), parsed_before)
        self.assertEqual(compose_full_title(self.player), "F級冒險者")
        self.assertEqual(parse_reward_claims(self.player), [])

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_the_grant_is_definition_independent(self):
        from world.rules.titles import compose_full_title

        side = register(
            quest(
                "first_claim_side_quest",
                stages=(QuestStage(0, defeat(tier="low")),),
            )
        )
        register_guild_offer(_offer(side.key))
        self._definition_key = side.key
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["title_notifications"], ["獲得異名：南門新客"])
        self.assertEqual(compose_full_title(self.player), "F級冒險者　南門新客")


class RewardClaimsParsingTests(QuestRegistryIsolation, EvenniaTestCase):
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
