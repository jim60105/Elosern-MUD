"""Synthetic definitions exercise actual escort acceptance and source owners."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.quests import scene_store
from world.quests.definitions import EscortCompletion, QuestStage, QuestType
from world.quests.escort_lifecycle import EscortOperationError, accept_escort_commission
from world.quests.planner import quest_event_effect_planner
from world.quests.runtime import accept_quest, abandon_quest, read_records
from world.rules.party import is_companion, join_party, party_size, reasons_for
from world.rules.quest_issuance import (
    QuestIssuance, Settlement, provision_scoped_issuer, register_quest_issuance,
)
from world.rules.guild_offers import QuestReward
from world.rules.action import _EVENT_EFFECT_PLANNERS, register_event_effect_planner
from world.rules.buffs import tick_buffs
from world.rules.combat import Battlefield
from world.rules.upkeep import settle_upkeep
from world.quests.compile import compile_quest_blueprint
from world.quests.tests._compile_helpers import _defeat_payload
from world.tests.synthetic_data import (
    SYNTH_SKILLS,
    make_skill,
    synthetic_registries,
)

from ._fixtures import (
    QuestRegistryIsolation, bound_instance_locator, escort, quest, register,
    register_catalog_once,
)

# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process
# (the guild/service suites do the same at import, before any synthetic scope).
register_catalog_once()


class EscortFixtureMixin:
    """The shared synthetic escort package, issuer, roles and stores."""

    def setUp(self):
        super().setUp()
        self.owner = self.char1
        self.protected = create_object(NPC, key="protected participant", location=self.room1)
        self.issuer = create_object(NPC, key="commission issuer", location=self.room1)
        self.meeting = create_object(NPC, key="meeting participant", location=self.room2)
        for actor in (self.protected, self.issuer, self.meeting):
            actor.race = "human"
            actor.apply_race_baseline()
        self.definition = register(quest(
            "synthetic_bound_escort", quest_type=QuestType.ESCORT,
            stages=(QuestStage(0, escort(
                completion=EscortCompletion.RENDEZVOUS,
                protected_role_refs=("protected",), meeting_role_refs=("meeting",),
            )),),
        ))
        self.issuer_key = provision_scoped_issuer(self.issuer, content_key="synthetic_bound_issuer")
        register_quest_issuance(QuestIssuance(
            definition_key=self.definition.key, issuer_key=self.issuer_key,
            reward=QuestReward(copper=1, items=(), merit=0), settlement=Settlement.AUTO,
        ))
        # Store construction is the upstream supported synthetic setup, not a
        # successful generated validation mock. All publication guards stay shut.
        self.package, _ = scene_store.publish_package(
            package_id="synthetic_bound_package", source_id=None, owner_id="fixture",
            payload={
                "roles": [{"role_id": role} for role in ("issuer", "protected", "meeting")],
                "commissions": [{"role_id": "issuer", "issuer_content_key": "synthetic_bound_issuer"}],
                "dialogue": [{"role_id": "issuer", "phases": [{
                    "phase_id": "offer", "topics": self.offer_topics(),
                }]}], "outcome_groups": self.outcome_groups(),
            },
        )
        for role, actor in (("issuer", self.issuer), ("protected", self.protected), ("meeting", self.meeting)):
            scene_store.bind_role(self.package, role, actor.pk)
        scene_store.ensure_commission_grant(
            self.package, "issuer", self.definition.key, issuer_key=self.issuer_key,
        )
        scene_store.assign_grant_actor(self.package, "issuer", self.definition.key, self.issuer.pk)
        scene_store.set_grant_registered(self.package, "issuer", self.definition.key, True)
        scene_store.set_dialogue_phase(self.package, "issuer", "offer")

    def offer_topics(self):
        return [{"keyword": "escort", "effect_verb": "offer_commission",
                 "effect_reference": self.definition.key}]

    def outcome_groups(self):
        return []


class EscortTestBase(EscortFixtureMixin, QuestRegistryIsolation, EvenniaTest):
    """The shared synthetic escort fixture for the escort behaviour suites."""


class EscortLifecycleTests(EscortTestBase):
    """Acceptance, release and settled evaluation through the real owners."""

    def test_acceptance_returns_exact_persisted_binding_beyond_general_quota(self):
        for _ in range(4):
            join_party(create_object(NPC, key="general member", location=self.room1), self.owner)
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        self.assertEqual(record.protected_roles, (("protected", self.protected.pk),))
        self.assertEqual(record.protected_entity_ids, (self.protected.pk,))
        self.assertTrue(is_companion(self.protected, self.owner))
        self.assertEqual(party_size(self.owner), 4)
        self.owner.attributes.reset_cache()
        self.protected.attributes.reset_cache()
        self.assertEqual(read_records(self.owner)[0], record)
        self.assertEqual(reasons_for(self.protected, self.owner), ((record.quest_id, "protected"),))

    def test_current_offer_revision_presence_and_foreign_ownership_refuse(self):
        for setup, reason in (
            (lambda: None, "offer_stale"),
            (lambda: setattr(self.protected, "location", self.room2), "role_not_co_located"),
            (lambda: setattr(self.protected.db, "party_member", self.char2.pk), "membership_owned_elsewhere"),
        ):
            with self.subTest(reason=reason):
                self.protected.location = self.room1
                self.protected.db.party_member = None
                setup()
                with self.assertRaises(EscortOperationError) as failure:
                    accept_escort_commission(
                        self.owner, self.definition.key, self.issuer_key,
                        expected_revision=1 if reason == "offer_stale" else 0,
                    )
                self.assertEqual(failure.exception.reason, reason)
                self.assertEqual(read_records(self.owner), [])

    def test_source_write_fault_restores_acceptance_and_paired_cache(self):
        with patch("world.quests.escort_lifecycle.add_temporary_source", side_effect=RuntimeError("source fault")):
            with self.assertRaises(EscortOperationError) as failure:
                accept_quest(self.owner, self.definition.key, self.issuer_key)
        self.assertEqual(failure.exception.reason, "acceptance_write_failed")
        for reload in (False, True):
            if reload:
                self.owner.attributes.reset_cache()
                self.protected.attributes.reset_cache()
            self.assertEqual(read_records(self.owner), [])
            self.assertFalse(is_companion(self.protected, self.owner))
            self.assertIsNone(self.protected.db.party_member)

    def test_abandonment_releases_only_record_source_and_keeps_general_member(self):
        join_party(self.protected, self.owner)
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        failed = abandon_quest(self.owner, record.quest_id)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertEqual(reasons_for(self.protected, self.owner), ())
        self.assertTrue(is_companion(self.protected, self.owner))

    def test_real_direct_protected_move_completes_pays_and_reloads(self):
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        wallet_before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        completed = read_records(self.owner)[0]
        self.assertEqual(completed.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.assertEqual(list(self.owner.db.guild_reward_claims), [record.quest_id])
        self.assertFalse(is_companion(self.protected, self.owner))
        self.owner.attributes.reset_cache()
        self.protected.attributes.reset_cache()
        self.assertEqual(read_records(self.owner)[0], completed)
        self.assertTrue(self.protected.move_to(self.room1, quiet=True))
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)

    def test_forged_source_is_rejected_without_writes(self):
        from world.quests.escort_events import EscortSource, evaluate_escort_event

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        with self.assertRaises(EscortOperationError) as failure:
            evaluate_escort_event(self.owner, self.package.package_id, source=EscortSource())
        self.assertEqual(failure.exception.reason, "invalid_source")
        self.assertEqual(read_records(self.owner)[0], record)

    def test_acceptance_settles_an_already_satisfied_rendezvous(self):
        # The meeting role already stands beside the exact protected actor, so
        # the acceptance's own settled pass completes and pays the commission.
        self.meeting.location = self.room1
        wallet_before = self.owner.db.wallet or 0
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.assertEqual(list(self.owner.db.guild_reward_claims), [record.quest_id])


class EscortExclusiveOutcomeTests(EscortTestBase):
    def outcome_groups(self):
        return [{
            "group_id": "reunion", "alternatives": [self.definition.key],
            "result": {"completion": "rendezvous", "protected_role_refs": ["protected"],
                       "meeting_role_refs": ["meeting"]},
        }]

    def test_real_meeting_move_selects_winner_before_payment(self):
        from world.quests.escort_events import exclusive_outcome_status

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        before = self.owner.db.wallet or 0
        self.assertTrue(self.meeting.move_to(self.room1, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, record.quest_id)
        self.assertFalse(group.no_commission)
        self.assertEqual(read_records(self.owner)[0].state.value, "completed")
        self.assertEqual(self.owner.db.wallet, before + 1)
        self.owner.attributes.reset_cache()
        self.assertEqual(list(self.owner.db.guild_reward_claims), [record.quest_id])


class EscortAlternativeMixin(EscortFixtureMixin):
    """Two distinct commissions share one exclusive result; one winner pays."""

    ALTERNATIVE = "synthetic_bound_escort_alternative"
    SINGLETON = "synthetic_bound_escort_singleton"

    def offer_topics(self):
        return [
            *super().offer_topics(),
            {"keyword": "escort", "effect_verb": "offer_commission",
             "effect_reference": self.ALTERNATIVE},
            {"keyword": "escort", "effect_verb": "offer_commission",
             "effect_reference": self.SINGLETON},
        ]

    def outcome_groups(self):
        return [{
            "group_id": "reunion",
            "alternatives": [self.definition.key, self.ALTERNATIVE],
            "result": {"completion": "rendezvous", "protected_role_refs": ["protected"],
                       "meeting_role_refs": ["meeting"]},
        }]

    def setUp(self):
        super().setUp()
        register(quest(
            self.ALTERNATIVE, quest_type=QuestType.ESCORT,
            stages=self.alternative_stages(),
        ))
        register_quest_issuance(QuestIssuance(
            definition_key=self.ALTERNATIVE, issuer_key=self.issuer_key,
            reward=QuestReward(copper=1, items=(), merit=0), settlement=Settlement.AUTO,
        ))
        scene_store.ensure_commission_grant(
            self.package, "issuer", self.ALTERNATIVE, issuer_key=self.issuer_key,
        )
        scene_store.assign_grant_actor(self.package, "issuer", self.ALTERNATIVE, self.issuer.pk)
        scene_store.set_grant_registered(self.package, "issuer", self.ALTERNATIVE, True)
        # An unrelated escort commission on the same package that belongs to no
        # exclusive group; resolving the group must leave it untouched.
        register(quest(
            self.SINGLETON, quest_type=QuestType.ESCORT,
            stages=(QuestStage(0, escort(
                bound_instance_locator(), protected_role_refs=("protected",),
            )),),
        ))
        register_quest_issuance(QuestIssuance(
            definition_key=self.SINGLETON, issuer_key=self.issuer_key,
            reward=QuestReward(copper=1, items=(), merit=0), settlement=Settlement.AUTO,
        ))
        scene_store.ensure_commission_grant(
            self.package, "issuer", self.SINGLETON, issuer_key=self.issuer_key,
        )
        scene_store.assign_grant_actor(self.package, "issuer", self.SINGLETON, self.issuer.pk)
        scene_store.set_grant_registered(self.package, "issuer", self.SINGLETON, True)

    def alternative_stages(self):
        return (QuestStage(0, escort(
            completion=EscortCompletion.RENDEZVOUS,
            protected_role_refs=("protected",), meeting_role_refs=("meeting",),
        )),)


class EscortAlternativeTestBase(EscortAlternativeMixin, QuestRegistryIsolation, EvenniaTest):
    """The two-commission exclusive-result fixture."""


class EscortExclusiveAlternativeTests(EscortAlternativeTestBase):
    """Exclusive alternative-resolution behaviour."""

    def test_first_accepted_alternative_wins_and_the_other_is_invalidated(self):
        from world.quests.escort_events import exclusive_outcome_status

        winner = accept_quest(self.owner, self.definition.key, self.issuer_key)
        other = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, winner.quest_id)
        records = {record.quest_id: record for record in read_records(self.owner)}
        self.assertEqual(records[winner.quest_id].state.value, "completed")
        self.assertEqual(records[other.quest_id].state.value, "invalidated")
        self.assertEqual(
            records[other.quest_id].invalidated_reason["code"], "obsolete_outcome",
        )
        self.assertEqual(self.owner.db.wallet, before + 1)
        self.owner.attributes.reset_cache()
        self.protected.attributes.reset_cache()
        self.assertEqual(list(self.owner.db.guild_reward_claims), [winner.quest_id])
        # A restarted identical source cannot advance or repay.
        self.assertTrue(self.protected.move_to(self.room1, quiet=True))
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        self.assertEqual(self.owner.db.wallet, before + 1)
        reloaded = {record.quest_id: record for record in read_records(self.owner)}
        self.assertEqual(reloaded[winner.quest_id].state.value, "completed")
        self.assertEqual(reloaded[other.quest_id].state.value, "invalidated")

    def test_distinct_acceptances_get_monotonic_sequences(self):
        first = accept_quest(self.owner, self.definition.key, self.issuer_key)
        second = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        self.assertIsNotNone(first.acceptance_sequence)
        self.assertIsNotNone(second.acceptance_sequence)
        self.assertLess(first.acceptance_sequence, second.acceptance_sequence)

    def test_meeting_first_order_selects_the_earlier_sequence(self):
        from world.quests.escort_events import exclusive_outcome_status

        winner = accept_quest(self.owner, self.definition.key, self.issuer_key)
        other = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        # The exact meeting role walks to the stationary protected actor.
        self.assertTrue(self.meeting.move_to(self.room1, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, winner.quest_id)
        records = {record.quest_id: record for record in read_records(self.owner)}
        self.assertEqual(records[winner.quest_id].state.value, "completed")
        self.assertEqual(records[other.quest_id].state.value, "invalidated")

    def test_simultaneous_satisfaction_picks_the_earlier_sequence(self):
        from world.quests.escort_events import exclusive_outcome_status

        winner = accept_quest(self.owner, self.definition.key, self.issuer_key)
        other = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        before = self.owner.db.wallet or 0
        # Moving the protected actor beside the meeting role satisfies both
        # alternatives at once; the earlier acceptance sequence wins.
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, winner.quest_id)
        records = {record.quest_id: record for record in read_records(self.owner)}
        self.assertEqual(records[winner.quest_id].state.value, "completed")
        self.assertEqual(records[other.quest_id].state.value, "invalidated")
        self.assertEqual(self.owner.db.wallet, before + 1)

    def test_active_alternatives_without_an_attributable_candidate_stay_unresolved(self):
        from world.quests.escort_events import exclusive_outcome_status

        accept_quest(self.owner, self.definition.key, self.issuer_key)
        accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        # An unrelated companion moves; no protected or meeting binding moves,
        # so nothing is attributable and the group must stay unresolved.
        unrelated = create_object(NPC, key="bystander", location=self.room1)
        join_party(unrelated, self.owner)
        self.assertTrue(unrelated.move_to(self.room2, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertFalse(group.resolved)
        records = read_records(self.owner)
        self.assertEqual({record.state.value for record in records}, {"in_progress"})

    def test_unrelated_commission_is_not_invalidated_by_group_resolution(self):
        from world.quests.escort_events import exclusive_outcome_status

        winner = accept_quest(self.owner, self.definition.key, self.issuer_key)
        accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        singleton = accept_quest(self.owner, self.SINGLETON, self.issuer_key)
        self.assertIsNone(singleton.group_id)
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, winner.quest_id)
        records = {record.quest_id: record for record in read_records(self.owner)}
        # The group-less commission is untouched: neither completed nor
        # invalidated by a resolution that never named it.
        self.assertEqual(records[singleton.quest_id].state.value, "in_progress")

    def test_a_closed_unaccepted_offer_cannot_be_accepted(self):
        from world.quests.escort_lifecycle import EscortOperationError

        accept_quest(self.owner, self.definition.key, self.issuer_key)
        # The meeting role comes to the still-co-located protected actor, so the
        # group resolves while the issuer offer preflight still passes.
        self.assertTrue(self.meeting.move_to(self.room1, quiet=True))
        with self.assertRaises(EscortOperationError) as failure:
            accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        self.assertEqual(failure.exception.reason, "outcome_resolved")
        records = {record.quest_id: record for record in read_records(self.owner)}
        self.assertEqual(list(records), ["synthetic_bound_escort:1"])


class EscortEntitlementTests(EscortTestBase):
    """Only the group winner, or a group-less record, is ever entitled."""

    def outcome_groups(self):
        return [{
            "group_id": "reunion", "alternatives": [self.definition.key],
            "result": {"completion": "rendezvous", "protected_role_refs": ["protected"],
                       "meeting_role_refs": ["meeting"]},
        }]

    def test_entitlement_follows_the_group_result(self):
        from types import SimpleNamespace

        from world.quests import outcome_store
        from world.quests.escort_events import reward_entitled

        outcome_store.mark_group_resolved(
            owner_id=self.owner.pk, package_id="pkg", group_id="g",
            resolution_source="s", winner_quest_id="winner:1",
        )
        self.assertTrue(reward_entitled(
            self.owner, SimpleNamespace(group_id="g", package_id="pkg", quest_id="winner:1")
        ))
        self.assertFalse(reward_entitled(
            self.owner, SimpleNamespace(group_id="g", package_id="pkg", quest_id="loser:1")
        ))
        outcome_store.mark_group_resolved(
            owner_id=self.owner.pk, package_id="pkg2", group_id="g2",
            resolution_source="s2", no_commission=True,
        )
        self.assertFalse(reward_entitled(
            self.owner, SimpleNamespace(group_id="g2", package_id="pkg2", quest_id="any:1")
        ))
        # A record with no exclusive group is unconditionally entitled.
        self.assertTrue(reward_entitled(
            self.owner, SimpleNamespace(group_id=None, package_id=None, quest_id="free:1")
        ))

    def test_automatic_planning_skips_a_completed_non_winner(self):
        from world.quests import outcome_store
        from world.quests.escort_events import reward_entitled
        from world.quests.runtime import apply_quest_log_replacement, fulfill_record_for
        from world.quests.settlement import plan_auto_settlement

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        outcome_store.mark_group_resolved(
            owner_id=self.owner.pk, package_id=self.package.package_id,
            group_id="reunion", resolution_source="s", winner_quest_id="other:9",
        )
        completed = fulfill_record_for(self.owner, record, self.definition)
        apply_quest_log_replacement(self.owner, [completed])
        self.assertFalse(reward_entitled(self.owner, completed))
        self.assertEqual(plan_auto_settlement(self.owner, [completed]).entries, ())


class EscortCounterClaimTests(EscortTestBase):
    """The counter-claim path turns in exactly the entitled record."""

    def outcome_groups(self):
        return [{
            "group_id": "reunion", "alternatives": [self.definition.key],
            "result": {"completion": "rendezvous", "protected_role_refs": ["protected"],
                       "meeting_role_refs": ["meeting"]},
        }]

    def setUp(self):
        from world.rules.tests._combat_session_helpers import open_synthetic_scope

        open_synthetic_scope(self, "guild_branches", "items", "monster_tiers")
        super().setUp()
        from typeclasses.components import GuildStaff
        from world.rules.guild import register_adventurer
        from world.rules.guild_offers import (
            GuildQuestOffer, QuestReward, register_guild_offer,
        )
        from world.rules.tests._guild_service_probes import (
            rank_reward_band, synthetic_branch_key,
        )

        self.branch = synthetic_branch_key()
        self.staff = create_object(NPC, key="公會職員", location=self.room1)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=self.branch)
        )
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        register_adventurer(self.owner, self.staff)
        low, _high = rank_reward_band(self.definition.rank)
        register_guild_offer(GuildQuestOffer(
            self.definition.key, self.branch, QuestReward(low, (), 0),
        ))

    def test_a_completed_non_winner_is_refused_by_the_counter_claim(self):
        from world.quests import outcome_store
        from world.quests.runtime import apply_quest_log_replacement, fulfill_record_for
        from world.rules.guild import RewardClaimError, turn_in_quest

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        outcome_store.mark_group_resolved(
            owner_id=self.owner.pk, package_id=self.package.package_id,
            group_id="reunion", resolution_source="s", winner_quest_id="other:9",
        )
        completed = fulfill_record_for(self.owner, record, self.definition)
        apply_quest_log_replacement(self.owner, [completed])
        self.assertEqual(read_records(self.owner)[0].state.value, "completed")
        with self.assertRaises(RewardClaimError):
            turn_in_quest(self.owner, self.staff, completed.quest_id)


class EscortResultFaultTests(EscortAlternativeTestBase):
    """A fault after any result write rolls the whole result back."""

    def _begin(self):
        winner = accept_quest(self.owner, self.definition.key, self.issuer_key)
        other = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        return winner, other, (self.owner.db.wallet or 0)

    def _assert_unresolved_baseline(self, winner, other, wallet_before):
        from world.quests.escort_events import exclusive_outcome_status

        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertFalse(group.resolved)
        self.owner.attributes.reset_cache()
        records = {record.quest_id: record.state.value for record in read_records(self.owner)}
        self.assertEqual(records[winner.quest_id], "in_progress")
        self.assertEqual(records[other.quest_id], "in_progress")
        self.assertEqual(self.owner.db.wallet, wallet_before)
        self.assertEqual(list(self.owner.db.guild_reward_claims or []), [])

    def test_a_group_write_fault_rolls_the_whole_result_back(self):
        from unittest.mock import patch

        from world.quests import outcome_store

        winner, other, wallet_before = self._begin()
        with patch.object(
            outcome_store, "mark_group_resolved", side_effect=RuntimeError("group fault")
        ):
            with self.assertRaises(RuntimeError):
                self.protected.move_to(self.room2, quiet=True)
        self._assert_unresolved_baseline(winner, other, wallet_before)

    def test_a_narrative_fault_rolls_the_whole_result_back(self):
        from unittest.mock import patch

        winner, other, wallet_before = self._begin()
        with patch(
            "world.narrative.memory.record_memory",
            side_effect=RuntimeError("narrative fault"),
        ):
            with self.assertRaises(RuntimeError):
                self.protected.move_to(self.room2, quiet=True)
        self._assert_unresolved_baseline(winner, other, wallet_before)

    def test_a_record_write_fault_rolls_the_whole_result_back(self):
        from unittest.mock import patch

        winner, other, wallet_before = self._begin()
        with patch(
            "world.quests.escort_events.apply_quest_log_replacement",
            side_effect=RuntimeError("record fault"),
        ):
            with self.assertRaises(RuntimeError):
                self.protected.move_to(self.room2, quiet=True)
        self._assert_unresolved_baseline(winner, other, wallet_before)

    def test_a_reward_write_fault_rolls_the_whole_result_back(self):
        from unittest.mock import patch

        winner, other, wallet_before = self._begin()
        with patch(
            "world.quests.settlement.commit_auto_settlement",
            side_effect=RuntimeError("reward fault"),
        ):
            with self.assertRaises(RuntimeError):
                self.protected.move_to(self.room2, quiet=True)
        self._assert_unresolved_baseline(winner, other, wallet_before)

    def test_a_handback_fault_rolls_the_whole_result_back(self):
        from unittest.mock import patch

        winner, other, wallet_before = self._begin()
        with patch(
            "world.rules.possession.release_for_party_change",
            side_effect=RuntimeError("handback fault"),
        ):
            with self.assertRaises(RuntimeError):
                self.protected.move_to(self.room2, quiet=True)
        self._assert_unresolved_baseline(winner, other, wallet_before)


class EscortIntermediateStageTests(EscortAlternativeTestBase):
    """A multi-stage alternative advances without settling its final group."""

    def alternative_stages(self):
        stage = escort(
            completion=EscortCompletion.RENDEZVOUS,
            protected_role_refs=("protected",), meeting_role_refs=("meeting",),
        )
        return (QuestStage(0, stage), QuestStage(1, stage))

    def test_intermediate_stage_advances_without_resolving_the_group(self):
        from world.quests.escort_events import exclusive_outcome_status

        record = accept_quest(self.owner, self.ALTERNATIVE, self.issuer_key)
        before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        advanced = read_records(self.owner)[0]
        self.assertEqual(advanced.quest_id, record.quest_id)
        self.assertEqual(advanced.state.value, "in_progress")
        self.assertEqual(advanced.stage_index, 1)
        group = exclusive_outcome_status(self.owner, self.package.package_id, "reunion")
        self.assertFalse(group.resolved)
        self.assertEqual(self.owner.db.wallet, before)


class EscortCasualtyTests(EscortTestBase):
    """Lawful committed death fails an escort without kill-credit attribution."""

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        super().tearDown()

    def _field(self, *entities):
        teams, roster = {}, {}
        for index, entity in enumerate(entities):
            team = "party" if index == 0 else "foes"
            teams.setdefault(team, set()).add(entity.key)
            roster[entity.key] = entity
        return Battlefield(
            {team: frozenset(members) for team, members in teams.items()}, roster,
        )

    def test_environmental_lethal_tick_fails_the_escort(self):
        from world.rules.buffs import apply_buff

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        monster = create_object(Monster, key="environmental source", location=self.room1)
        field = self._field(self.owner, monster, self.protected)
        self.protected.traits.hp.base = 3
        self.protected.traits.hp.current = 3
        apply_buff(self.protected, "poisoned")
        records = {self.protected.key: tick_buffs(self.protected, 10)}
        self.assertEqual(self.protected.traits.hp.current, 0)
        settle_upkeep(field, records)
        failed = read_records(self.owner)[0]
        self.assertEqual(failed.quest_id, record.quest_id)
        self.assertEqual(failed.state.value, "failed")
        self.assertEqual(failed.failure_reason, "protected_actor_dead")
        self.assertEqual(reasons_for(self.protected, self.owner), ())

    def test_deleted_source_lethal_tick_still_fails_the_escort(self):
        from world.rules.buffs import apply_buff

        accept_quest(self.owner, self.definition.key, self.issuer_key)
        source = create_object(Monster, key="doomed source", location=self.room1)
        self.protected.traits.hp.base = 3
        self.protected.traits.hp.current = 3
        apply_buff(self.protected, "poisoned", source_pk=int(source.pk))
        source.delete()
        field = self._field(self.owner, self.protected)
        records = {self.protected.key: tick_buffs(self.protected, 10)}
        settle_upkeep(field, records)
        failed = read_records(self.owner)[0]
        self.assertEqual(failed.state.value, "failed")
        self.assertEqual(failed.failure_reason, "protected_actor_dead")

    def test_attributed_hostile_tick_fails_the_protected_escort(self):
        from world.rules.buffs import apply_buff

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        monster = create_object(Monster, key="hostile caster", location=self.room1)
        self.protected.traits.hp.base = 3
        self.protected.traits.hp.current = 3
        apply_buff(self.protected, "poisoned", source_pk=int(monster.pk))
        field = self._field(self.owner, monster, self.protected)
        records = {self.protected.key: tick_buffs(self.protected, 10)}
        settle_upkeep(field, records)
        failed = read_records(self.owner)[0]
        self.assertEqual(failed.quest_id, record.quest_id)
        self.assertEqual(failed.state.value, "failed")
        self.assertEqual(failed.failure_reason, "protected_actor_dead")
        self.assertEqual(reasons_for(self.protected, self.owner), ())

    def test_source_less_monster_kill_still_grants_no_quest_progress(self):
        from world.rules.buffs import apply_buff

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        monster = create_object(Monster, key="unattributed target", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 3
        monster.traits.hp.current = 3
        apply_buff(monster, "poisoned")
        field = self._field(self.owner, monster)
        records = {monster.key: tick_buffs(monster, 10)}
        settle_upkeep(field, records)
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "in_progress")

    def test_surviving_unattributed_tick_does_not_fail_the_escort(self):
        from world.rules.buffs import apply_buff

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        monster = create_object(Monster, key="mild source", location=self.room1)
        self.protected.traits.hp.base = 100
        self.protected.traits.hp.current = 100
        apply_buff(self.protected, "poisoned")
        field = self._field(self.owner, monster)
        records = {self.protected.key: tick_buffs(self.protected, 10)}
        self.assertGreater(self.protected.traits.hp.current, 0)
        settle_upkeep(field, records)
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "in_progress")

    def test_simulated_unattributed_lethal_tick_does_not_fail_the_escort(self):
        from world.rules.buffs import apply_buff

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        monster = create_object(Monster, key="exam source", location=self.room1)
        self.protected.traits.hp.base = 3
        self.protected.traits.hp.current = 3
        apply_buff(self.protected, "poisoned")
        field = self._field(self.owner, monster)
        records = {self.protected.key: tick_buffs(self.protected, 10)}
        settle_upkeep(field, records, simulated=True)
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "in_progress")


class EscortEventBoundaryTests(EscortTestBase):
    """Movement boundaries settle exactly once and attribute real actors."""

    def test_unrelated_general_companion_move_cannot_advance_a_rendezvous(self):
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        unrelated = create_object(NPC, key="unrelated companion", location=self.room1)
        join_party(unrelated, self.owner)
        self.assertTrue(unrelated.move_to(self.room2, quiet=True))
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "in_progress")

    def test_restart_replay_does_not_advance_again(self):
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        wallet_before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        completed = read_records(self.owner)[0]
        self.assertEqual(completed.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.assertTrue(self.protected.move_to(self.room1, quiet=True))
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        self.assertEqual(read_records(self.owner)[0], completed)
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)

    def test_protected_actor_under_possession_completes_for_the_owner(self):
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        self.protected.location = self.room1
        self.owner.db.possession = {"npc_dbid": int(self.protected.pk), "since_tick": 0}
        self.protected.db.possessed_by = int(self.owner.pk)
        wallet_before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        completed = read_records(self.owner)[0]
        self.assertEqual(completed.quest_id, record.quest_id)
        self.assertEqual(completed.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.assertEqual(self.owner.location, self.room1)

    def test_follower_settlement_completes_the_rendezvous_once(self):
        from world.rules.movement_settlement import settle_movement
        from world.rules.party import follow_companions

        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        wallet_before = self.owner.db.wallet or 0
        source = self.owner.location

        def traverse():
            self.owner.move_to(self.room2, quiet=True)
            follow_companions(self.owner, source, destination=self.room2)

        settle_movement(
            self.owner, source, traverse=traverse, destination=self.room2,
        )
        completed = read_records(self.owner)[0]
        self.assertEqual(completed.quest_id, record.quest_id)
        self.assertEqual(completed.state.value, "completed")
        self.assertEqual(self.protected.location, self.room2)
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        # A replayed identical settled movement neither advances nor repays.
        self.assertTrue(self.protected.move_to(self.room1, quiet=True))
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)


#: Kit-shaped rows for the 6.1 smoke: every cast runs on synthetic skills
#: installed through the scope, so no shipped registry row is named or mutated.
_SMOKE_PHYS = f"damage:{SYNTH_SKILLS['t_ember_burst'].element.key}:physical"
_SMOKE_CLAW = make_skill("t_smoke_claw", cost={}, effects=[_SMOKE_PHYS])
_SMOKE_SCOPE = synthetic_registries(
    "skills", extra={"skills": {_SMOKE_CLAW.key: _SMOKE_CLAW}}
)


def _smoke_gate():
    """The live gateway face and its landing cell (never a literal key)."""
    import importlib

    registry = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )
    entry = next(item for item in registry.values() if item.gate_for("w") is not None)
    gate = entry.gate_for("w")
    return (*gate.grid_xy, gate.z_map_key), entry.approach_cell(gate)


@_SMOKE_SCOPE
class EscortRealOwnerSmokeTests(EscortTestBase):
    """Task 6.1: the change's own real-owner smoke, construction to reload.

    One flow: authorized acceptance, a literal ``Exit`` traversal, a literal
    wilderness gateway traversal, received combat damage through the real
    action pipeline, then rendezvous completion, exclusive resolution, payment
    and a committed reload. Nothing is mocked to succeed and no objective is
    relabelled.
    """

    def setUp(self):
        super().setUp()
        from world.quests.planner import quest_event_effect_planner
        from world.rules.action import (
            _EVENT_EFFECT_PLANNERS,
            register_event_effect_planner,
        )

        register_event_effect_planner("quest", quest_event_effect_planner)
        self.addCleanup(_EVENT_EFFECT_PLANNERS.pop, "quest", None)

    def outcome_groups(self):
        return [{
            "group_id": "reunion", "alternatives": [self.definition.key],
            "result": {"completion": "rendezvous", "protected_role_refs": ["protected"],
                       "meeting_role_refs": ["meeting"]},
        }]

    def _field(self, actor, targets):
        from world.rules.combat import Battlefield

        return Battlefield(
            {
                "party": frozenset({actor.key}),
                "foes": frozenset(target.key for target in targets),
            },
            {actor.key: actor, **{target.key: target for target in targets}},
        )

    def test_task_6_1_real_owner_smoke(self):
        from unittest.mock import patch

        from evennia.utils.create import create_object
        from typeclasses.exits import Exit, WildernessGateExit
        from typeclasses.rooms import GridRoom, Room, TerrainRoom
        from world.maps.bootstrap import sync_grid, sync_wilderness
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.combat import BattlefieldActionContext
        from world.rules.tests.combat_fixtures import grant_lineage

        # 1) Construction: a real published package with exact role bindings.
        self.assertEqual(
            scene_store.get_role_binding(
                self.package.package_id, "protected"
            ).npc_id,
            int(self.protected.pk),
        )

        # 2) Authorized acceptance through the real commission owner.
        record = accept_quest(self.owner, self.definition.key, self.issuer_key)
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "in_progress")
        self.assertTrue(is_companion(self.protected, self.owner))

        # 3) A literal wilderness gateway traversal from the grid, with the
        #    protected companion following into the wilderness.
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        xyz, approach = _smoke_gate()
        grid_room = GridRoom.objects.filter_xyz(xyz=xyz).first()
        gate = [
            exit_obj
            for exit_obj in grid_room.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]
        gate.at_traverse(self.owner, grid_room)
        self.assertIsInstance(self.owner.location, TerrainRoom)
        self.assertEqual(self.owner.location.coordinates, approach)
        self.assertEqual(self.protected.location, self.owner.location)

        # 4) Received combat damage through the real action pipeline.
        hostile = create_object(NPC, key="伏兵", location=self.owner.location)
        hostile.race = "human"
        hostile.apply_race_baseline()
        grant_lineage(hostile, [_SMOKE_CLAW.key])
        hp_before = self.protected.traits.hp.current
        field = self._field(hostile, [self.protected])
        request = ActionRequest(
            hostile,
            _SMOKE_CLAW.key,
            [self.protected],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(self.protected.traits.hp.current, hp_before)
        self.assertGreater(self.protected.traits.hp.current, 0)
        self.assertEqual(read_records(self.owner)[0].state.value, "in_progress")

        # 5) Back to the grid, then possession movement: the owner possesses
        #    the protected actor and walks it through a literal Exit to the
        #    meeting role, so one traversal carries possession, movement and
        #    the settled rendezvous evaluation.
        self.owner.move_to(self.room1, quiet=True)
        self.protected.move_to(self.room1, quiet=True)
        wallet_before = self.owner.db.wallet or 0
        self.protected.db.possessed_by = int(self.owner.pk)
        self.owner.db.possession = {
            "npc_dbid": int(self.protected.pk),
            "since_tick": 0,
        }
        doorway = create_object(
            Exit, key="穿堂", location=self.room1, destination=self.room2
        )
        doorway.at_traverse(self.protected, self.room2)
        self.assertEqual(self.protected.location, self.room2)

        # 6) Rendezvous completion, exclusive resolution and payment.
        from world.quests.escort_events import exclusive_outcome_status

        completed = read_records(self.owner)[0]
        self.assertEqual(completed.quest_id, record.quest_id)
        self.assertEqual(completed.state.value, "completed")
        group = exclusive_outcome_status(
            self.owner, self.package.package_id, "reunion"
        )
        self.assertTrue(group.resolved)
        self.assertEqual(group.winner_quest_id, record.quest_id)
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)

        # 7) Committed reload: caches reset, durable state unchanged.
        self.owner.attributes.reset_cache()
        self.protected.attributes.reset_cache()
        reloaded = read_records(self.owner)[0]
        self.assertEqual(reloaded.quest_id, record.quest_id)
        self.assertEqual(reloaded.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.assertEqual(list(self.owner.db.guild_reward_claims), [record.quest_id])
        self.assertEqual(reasons_for(self.protected, self.owner), ())


def _generated_escort_payload():
    """A compilable complete rendezvous-escort proposal for the real chain."""
    payload = _defeat_payload()
    payload["name"] = "護衛重逢"
    payload["quest_type"] = "護衛"
    payload["stages"][0]["objective"] = {
        "kind": "escort",
        "quantity": 1,
        "completion": "rendezvous",
        "protected_role_refs": ["protected"],
        "meeting_role_refs": ["meeting"],
    }
    # A rendezvous declares no destination locator.
    payload["stages"][0]["location_req"] = None
    return payload


#: The compiled definition key is deterministic, so the package fixture can
#: publish a commission that offers it before the generated registration runs.
_GENERATED_ESCORT_KEY = compile_quest_blueprint(
    _generated_escort_payload()
).definition.key


class EscortGeneratedPublicationTests(
    EscortFixtureMixin, QuestRegistryIsolation, EvenniaTest
):
    """Task 6.2: a generated escort publishes, is accepted, completes and pays.

    The flow starts from a scripted proposal and runs the real chain - the
    guardrail semantic validators, the deterministic compile boundary and the
    generated registration - then accepts the published definition through the
    real acceptance owner with its package bindings and party sources, and
    resolves it in each encounter order through to payment and a committed
    reload. Nothing is mocked to succeed and no objective is relabelled.
    """

    def offer_topics(self):
        return [
            *super().offer_topics(),
            {
                "keyword": "escort",
                "effect_verb": "offer_commission",
                "effect_reference": _GENERATED_ESCORT_KEY,
            },
        ]

    def outcome_groups(self):
        # The published package indexes the owner for the definition, so a
        # meeting-role move is attributable exactly as a protected-role move is
        # (escort-rendezvous §5).
        return [{
            "group_id": "reunion",
            "alternatives": [_GENERATED_ESCORT_KEY],
            "result": {
                "completion": "rendezvous",
                "protected_role_refs": ["protected"],
                "meeting_role_refs": ["meeting"],
            },
        }]

    def _publish_generated(self):
        """Run the real generative chain and return the registered definition."""
        import json

        from server.ai_director_service import request_generated_quest
        from world.ai.fake_client import FakeLLMClient
        from world.ai import guardrail, scenario_director
        from world.ai.schemas.registry import _OUTPUT_SCHEMAS

        # Install the director layer idempotently, and remove it again so this
        # suite never leaks the registration into another module's process.
        guardrail._semantic_validators.pop("scenario_director", None)
        guardrail._degrade_fallbacks.pop("scenario_director", None)
        _OUTPUT_SCHEMAS.pop("scenario_director", None)
        scenario_director.register_scenario_director()
        self.addCleanup(guardrail._semantic_validators.pop, "scenario_director", None)
        self.addCleanup(guardrail._degrade_fallbacks.pop, "scenario_director", None)
        self.addCleanup(_OUTPUT_SCHEMAS.pop, "scenario_director", None)

        payload = _generated_escort_payload()
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: True, json.dumps(payload, ensure_ascii=False)
        )
        from django.test import override_settings
        from world.ai.profiles import default_profiles

        # The director layer must be enabled for the injected client to be used
        # (an environment-resolved profile may disable it), so this call pins
        # the local-first defaults the scripts expect.
        with override_settings(LLM_PROFILES=default_profiles()):
            deferred = request_generated_quest(
                client,
                context={
                    "requested_type": payload["quest_type"],
                    "allowed_rank": payload["rank"],
                    "issuer_branch": payload["issuer"],
                    "anchor": None,
                },
            )
            result = deferred.result
            deferred.addErrback(lambda failure: None)
        if hasattr(result, "raiseException"):
            result.raiseException()
        return result

    def setUp(self):
        super().setUp()
        compiled = self._publish_generated()
        self.assertEqual(compiled.definition.key, _GENERATED_ESCORT_KEY)
        # The published package's own commission issues the definition: the
        # scoped issuer's issuance plus its registered grant.
        register_quest_issuance(QuestIssuance(
            definition_key=_GENERATED_ESCORT_KEY, issuer_key=self.issuer_key,
            reward=QuestReward(copper=1, items=(), merit=0),
            settlement=Settlement.AUTO,
        ))
        scene_store.ensure_commission_grant(
            self.package, "issuer", _GENERATED_ESCORT_KEY, issuer_key=self.issuer_key,
        )
        scene_store.assign_grant_actor(
            self.package, "issuer", _GENERATED_ESCORT_KEY, self.issuer.pk,
        )
        scene_store.set_grant_registered(
            self.package, "issuer", _GENERATED_ESCORT_KEY, True,
        )

    def _assert_paid_and_reloaded(self, record, wallet_before):
        stored = read_records(self.owner)[0]
        self.assertEqual(stored.quest_id, record.quest_id)
        self.assertEqual(stored.state.value, "completed")
        self.assertEqual(self.owner.db.wallet, wallet_before + 1)
        self.owner.attributes.reset_cache()
        self.protected.attributes.reset_cache()
        self.assertEqual(read_records(self.owner)[0].state.value, "completed")
        self.assertEqual(
            list(self.owner.db.guild_reward_claims), [record.quest_id]
        )
        self.assertEqual(reasons_for(self.protected, self.owner), ())

    def test_protected_first_order(self):
        record = accept_quest(self.owner, _GENERATED_ESCORT_KEY, self.issuer_key)
        self.assertEqual(read_records(self.owner)[0].state.value, "in_progress")
        wallet_before = self.owner.db.wallet or 0
        self.assertTrue(self.protected.move_to(self.room2, quiet=True))
        self._assert_paid_and_reloaded(record, wallet_before)

    def test_meeting_first_order(self):
        record = accept_quest(self.owner, _GENERATED_ESCORT_KEY, self.issuer_key)
        wallet_before = self.owner.db.wallet or 0
        self.assertTrue(self.meeting.move_to(self.room1, quiet=True))
        self._assert_paid_and_reloaded(record, wallet_before)
