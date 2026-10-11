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

from ._fixtures import (
    QuestRegistryIsolation, bound_instance_locator, escort, quest, register,
)


class EscortLifecycleTests(QuestRegistryIsolation, EvenniaTest):
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


class EscortExclusiveOutcomeTests(EscortLifecycleTests):
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


class EscortExclusiveAlternativeTests(EscortLifecycleTests):
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


class EscortIntermediateStageTests(EscortExclusiveAlternativeTests):
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


class EscortCasualtyTests(EscortLifecycleTests):
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


class EscortEventBoundaryTests(EscortLifecycleTests):
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
