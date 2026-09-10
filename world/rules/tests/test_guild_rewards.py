"""Guild offer board access and reward settlement tests (tasks 6.1-6.8)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestStage,
)
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    defeat,
    quest,
    register,
)
from world.rules.quest_issuance import guild_issuer_key, resolve_issuance
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
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    a_live_monster_tier_key,
    live_guild_branch_registry,
    rank_reward_band,
    synthetic_branch_key,
)
from world.tests.synthetic_data import SYNTH_ITEMS
from world.quests.tests._fixtures import register_catalog_once

# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process.
# Registered at import (no synthetic scope is open yet), exactly as the other
# catalog-riding suites do.
register_catalog_once()

# Board identity is the kit synthetic guild branch, and reward items are the
# kit potion row -- no shipped content key is named anywhere below.
ALTORIA_BRANCH = synthetic_branch_key()
T_ITEM = SYNTH_ITEMS["t_ember_spray"].key


def _attach_staff(npc) -> None:
    npc.components.add(
        GuildStaff.create(npc, service_id="staff", branch_key=ALTORIA_BRANCH)
    )


def _offer(definition_key: str, copper: int = 50, merit: int = 25, items=(T_ITEM,)) -> GuildQuestOffer:
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
        # Branch, item, and tier identities validate against the kit rows.
        open_synthetic_scope(self, "guild_branches", "items", "monster_tiers")
        super().setUp()
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
                stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),),
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
                    QuestReward(50, (ItemQuantity(T_ITEM, 0),), 0),
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
                        (ItemQuantity(T_ITEM, 1), ItemQuantity(T_ITEM, 1)),
                        0,
                    ),
                )
            )

    def test_out_of_band_copper_is_rejected(self):
        floor, ceiling = rank_reward_band("F")
        for out in (floor - 1, ceiling + 1):
            with self.subTest(copper=out):
                with self.assertRaises(GuildOfferError):
                    register_guild_offer(_offer(self.test_definition.key, copper=out, items=()))

    @covers_requirement("guild-quest-board::guildquestoffer-is-immutable-and-validated-against-quest-guild-item-and-branch-registries")
    def test_s_rank_open_upper_bound_is_honored(self):
        s_floor, _ = rank_reward_band("S")
        s_definition = register(
            quest(
                "s_rank_quest",
                rank="S",
                stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),),
            )
        )
        large = _offer(s_definition.key, copper=s_floor + 1, items=())
        register_guild_offer(large)  # No upper cap invented for S.
        self.assertIn((s_definition.key, ALTORIA_BRANCH), GUILD_OFFER_REGISTRY)


class BoardAccessTests(OfferRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="hall")
        self.staff = create_object(NPC, key="staff", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="board player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        # A locally-issued F-rank offer stands in for any catalog row.
        self.board_quest = register(
            quest(
                "board_f_quest",
                stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),),
            )
        )
        register_guild_offer(_offer(self.board_quest.key, copper=50, items=()))

    def test_f_member_sees_only_local_f_offers(self):
        # Only the branch-local F-rank offer is listed for a fresh F member.
        self.assertEqual(
            [o.definition_key for o in list_guild_offers(self.player, self.staff)],
            [self.board_quest.key],
        )

    @covers_requirement("guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers")
    def test_true_exceptional_power_does_not_bypass_rank(self):
        e_definition = register(quest("e_rank_quest", rank="E", stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),)))
        register_guild_offer(_offer(e_definition.key, copper=100))
        self.player.traits.atk_phys.base = 88
        self.assertEqual(
            [o.definition_key for o in list_guild_offers(self.player, self.staff)],
            [self.board_quest.key],
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
        record = accept_guild_offer(self.player, self.staff, self.board_quest.key)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.definition_key, self.board_quest.key)
        # Registration granted +1; acceptance grants another +1.
        self.assertEqual(self.staff.relations.affinity_for(self.player), 2)

    @covers_requirement("guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle")
    def test_over_rank_direct_acceptance_is_rejected_before_quest_mutation(self):
        e_definition = register(quest("e_rank_quest", rank="E", stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),)))
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
        record = accept_guild_offer(self.player, self.staff, self.board_quest.key)
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
                accept_guild_offer(self.player, self.staff, self.board_quest.key)
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
                accept_guild_offer(self.player, self.staff, self.board_quest.key)
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertEqual(self.staff.db.relations_data, relations_before)


class BoardAcceptanceIssuerKeyTests(OfferRegistryIsolation, EvenniaTestCase):
    """Board acceptance names the issuing branch as the record's issuer key."""

    SECOND_BRANCH = "t_second_branch"

    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="issuer hall")
        self.staff_a = create_object(NPC, key="staff a", location=self.hall)
        _attach_staff(self.staff_a)
        self.player = create_object(PlayerCharacter, key="issuer player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff_a)
        self.definition = register(
            quest("branch_issuer_quest", stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),))
        )

    def _inject_second_branch(self) -> None:
        """A second invented branch, host, and offer for the same definition."""
        from world.lore.guild import GuildBranch

        registry = live_guild_branch_registry()
        branch_items = list(registry.items())
        self.addCleanup(
            lambda: (
                registry.clear(),
                registry.update(branch_items),
            )
        )
        registry[self.SECOND_BRANCH] = GuildBranch(
            self.SECOND_BRANCH,
            "埃洛西恩冒險者公會 第二分會",
            "測試會長",
            "測試分會會長",
            # Branch anchors are free-form identities on this invented row.
            "t_hollow_tarn",
        )
        self.staff_b = create_object(NPC, key="staff b", location=self.hall)
        self.staff_b.components.add(
            GuildStaff.create(
                self.staff_b, service_id="staff-b", branch_key=self.SECOND_BRANCH
            )
        )

    @covers_requirement("guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle")
    def test_board_acceptance_names_the_issuing_branch(self):
        offer = _offer(self.definition.key, copper=50, items=())
        register_guild_offer(offer)
        record = accept_guild_offer(self.player, self.staff_a, self.definition.key)
        self.assertEqual(record.issuer_key, f"guild:{ALTORIA_BRANCH}")
        self.assertEqual(
            resolve_issuance(record.definition_key, record.issuer_key).reward,
            offer.reward,
        )

    @covers_requirement("guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle")
    def test_two_branches_offering_one_definition_produce_distinguishable_records(self):
        self._inject_second_branch()
        offer_a = _offer(self.definition.key, copper=50, items=())
        offer_b = GuildQuestOffer(
            definition_key=self.definition.key,
            issuer_branch_key=self.SECOND_BRANCH,
            reward=QuestReward(copper=60, items=(), merit=0),
        )
        register_guild_offer(offer_a)
        register_guild_offer(offer_b)
        first = accept_guild_offer(self.player, self.staff_a, self.definition.key)
        abandon_guild_quest(self.player, self.staff_a, first.quest_id)
        second = accept_guild_offer(self.player, self.staff_b, self.definition.key)
        records = {r.quest_id: r for r in read_records(self.player)}
        self.assertEqual(records[first.quest_id].issuer_key, f"guild:{ALTORIA_BRANCH}")
        self.assertEqual(
            records[second.quest_id].issuer_key, f"guild:{self.SECOND_BRANCH}"
        )
        self.assertEqual(
            resolve_issuance(self.definition.key, f"guild:{ALTORIA_BRANCH}").reward,
            offer_a.reward,
        )
        self.assertEqual(
            resolve_issuance(self.definition.key, f"guild:{self.SECOND_BRANCH}").reward,
            offer_b.reward,
        )


class RewardSettlementTests(OfferRegistryIsolation, EvenniaTestCase):
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
        # An invented settlement quest with an invented reward: 50 copper,
        # 25 merit, and two of the kit potion (the atomic-acquire test relies
        # on the quantity; every number here is the fixture's own).
        self._definition = register(
            quest(
                "settlement_quest",
                stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),),
            )
        )
        self._definition_key = self._definition.key
        register_guild_offer(
            GuildQuestOffer(
                definition_key=self._definition.key,
                issuer_branch_key=ALTORIA_BRANCH,
                reward=QuestReward(
                    copper=50, items=(ItemQuantity(T_ITEM, 2),), merit=25
                ),
            )
        )

    def _complete(self, acceptance: int = 1) -> str:
        from world.quests.runtime import fulfill_record
        from world.quests.transitions import apply_quest_log_replacement

        record = accept_quest(
            self.player, self._definition_key, guild_issuer_key(ALTORIA_BRANCH)
        )
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
        self.assertIn(T_ITEM, self.player.db.inventory)
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
            turn_in_quest(self.player, self.staff, self._definition_key + ":99")
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
                stages=(QuestStage(0, _acquire(T_ITEM, quantity=2)),),
            )
        )
        accept(self.player, acquire_def.key)
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
        self.assertIn(T_ITEM, self.player.db.inventory)
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
        from world.rules.titles import (
            compose_full_title,
            compose_title,
            read_title_state,
        )

        registered_title = compose_full_title(self.player)
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["title_notifications"], ["獲得異名：南門新客"])
        self.assertEqual(
            compose_full_title(self.player),
            compose_title(registered_title, "南門新客"),
        )
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
        registered_title = compose_full_title(self.player)
        self.assertTrue(registered_title)
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
        self.assertEqual(compose_full_title(self.player), registered_title)
        self.assertEqual(parse_reward_claims(self.player), [])

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_the_grant_is_definition_independent(self):
        from world.rules.titles import compose_full_title, compose_title

        side = register(
            quest(
                "first_claim_side_quest",
                stages=(QuestStage(0, defeat(tier=a_live_monster_tier_key())),),
            )
        )
        register_guild_offer(_offer(side.key))
        self._definition_key = side.key
        registered_title = compose_full_title(self.player)
        quest_id = self._complete()
        result = turn_in_quest(self.player, self.staff, quest_id)
        self.assertEqual(result["title_notifications"], ["獲得異名：南門新客"])
        self.assertEqual(
            compose_full_title(self.player),
            compose_title(registered_title, "南門新客"),
        )


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
