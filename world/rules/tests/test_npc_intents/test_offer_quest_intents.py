"""Slice of ``test_npc_intents``: OfferQuestIntentTests.
"""
import inspect
from unittest.mock import patch
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, QuestIssuer
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire as _acquire,
    quest as _quest,
    register as _register_quest,
)
from world.rules.combat_session import read_session
from world.rules.guild import GuildDataError, register_adventurer
from world.rules.guild_config import CATALOG
from world.rules.guild_exams import ExamState, _read_exams
from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.npc_intents import (
    STALE_CONTEXT_REASON,
    IntentOutcome,
    _apply_plan,
    apply_npc_intent,
    intent_context_ok,
    is_stale_context,
)
from world.rules.quest_issuance import (
    QuestIssuance,
    Settlement,
    guild_issuer_key,
    npc_issuer_key,
    register_quest_issuance,
    resolve_issuance,
)
from world.rules.surfaces import write_counter_trait
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
)
from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS
from tools.spec_traceability import covers_requirement


from ._support import (
    BRANCH,
    ExamRegistryIsolation,
)


class OfferQuestIntentTests(ExamRegistryIsolation, EvenniaTestCase):
    """The offer_quest intent routes through the issuer-aware offer surface."""

    ALTORIA_BRANCH = BRANCH

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="offer quest room")
        self.player = create_object(PlayerCharacter, key="offer quest player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.staff = create_object(NPC, key="offer staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        register_adventurer(self.player, self.staff)
        definition = _register_quest(_quest("forest_clearing", rank="F"))
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=self.ALTORIA_BRANCH,
                reward=QuestReward(copper=50, items=(), merit=25),
            )
        )
        self.quest_key = definition.key

    def _offer_intent(self, quest_key="forest_clearing"):
        return {"kind": "offer_quest", "quest_key": quest_key}

    def _affinity(self, player=None):
        return self.staff.relations._load(player or self.player)

    def _records(self):
        return read_records(self.player)

    def _commissioner(self, issuer_key=None):
        name = f"commissioner {issuer_key or 'pk'}"
        commissioner = create_object(NPC, key=name, location=self.room)
        commissioner.components.add(
            QuestIssuer.create(
                commissioner,
                service_id=f"commission-{issuer_key or 'pk'}",
                issuer_key=issuer_key,
            )
        )
        return commissioner

    def _register_commission(self, definition_key, issuer_key):
        issuance = QuestIssuance(
            definition_key=definition_key,
            issuer_key=issuer_key,
            reward=QuestReward(copper=30, items=(), merit=0),
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance)
        return issuance

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_verified_offer_assigns_the_quest_and_applies_guild_affinity(self):
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.reason, "quest assigned")
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(records[0].issuer_key, guild_issuer_key(self.ALTORIA_BRANCH))
        self.assertEqual(records[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(self._affinity().value, 2)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_capped_affinity_write_commits_the_quest_without_rollback(self):
        from world.rules.affinity import AffinityRecord

        self.staff.db.relations_data = {
            str(self.player.pk): AffinityRecord(
                value=99, cap=99, daily_gain=0, daily_tick=0
            ).to_storage()
        }
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(outcome.applied)
        self.assertIn("capped", outcome.reason)
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(self._affinity().value, 99)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_non_npc_speaker_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(self.player, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "offer_quest requires an NPC speaker")
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_speaker_without_guild_staff_is_rejected_without_state_change(self):
        plain = create_object(NPC, key="plain npc", location=self.room)
        outcome = apply_npc_intent(plain, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff or QuestIssuer speaker"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_speaker_without_branch_key_is_rejected_without_state_change(self):
        branchless = create_object(NPC, key="branchless staff", location=self.room)
        branchless.components.add(
            GuildStaff.create(branchless, service_id="branchless")
        )
        outcome = apply_npc_intent(branchless, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unregistered_offer_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(
            self.staff, self.player, self._offer_intent("unregistered_quest")
        )
        self.assertFalse(outcome.applied)
        self.assertIn("no guild offer", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unregistered_player_is_rejected_without_state_change(self):
        other = create_object(PlayerCharacter, key="unregistered player")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.room
        outcome = apply_npc_intent(self.staff, other, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "actor is not registered")
        self.assertEqual(read_records(other), [])
        self.assertIsNone(self._affinity(other))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_rankless_player_is_rejected_without_state_change(self):
        self.player.guild_rank = None
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "actor has no guild rank")
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unknown_player_rank_is_rejected_without_state_change(self):
        self.player.guild_rank = "Z"
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("unknown guild rank", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_registration_discards_only_the_intent(self):
        self.player.db.guild_registration = {"branch_key": 123}
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("guild_registration", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_rank_below_the_quest_band_is_rejected_without_state_change(self):
        definition = _register_quest(_quest("ranked_quest", rank="E"))
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=self.ALTORIA_BRANCH,
                reward=QuestReward(copper=200, items=(), merit=25),
            )
        )
        outcome = apply_npc_intent(
            self.staff, self.player, self._offer_intent(definition.key)
        )
        self.assertFalse(outcome.applied)
        self.assertIn("not rank-eligible", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_duplicate_quest_rejection_is_delegated_to_the_quest_runtime(self):
        first = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(first.applied)
        second = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(second.applied)
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(self._affinity().value, 2)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_injected_commit_failure_restores_quest_log_and_affinity_record(self):
        with patch(
            "world.rules.npc_intents.apply_affinity_change",
            side_effect=RuntimeError("affinity write failure"),
        ):
            outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("rolled back", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)
        self.staff.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(list(self.player.db.quest_log or []), [])

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-carries-exactly-one-quest-key-field")
    def test_malformed_offer_payloads_are_rejected_without_state_change(self):
        for intent in (
            {"kind": "offer_quest"},
            {"kind": "offer_quest", "quest_key": ""},
            {"kind": "offer_quest", "quest_key": 3},
            {"kind": "offer_quest", "quest_key": "x", "extra": 1},
            {"kind": "offer_quest", "quest_key": "q" * 65},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.staff, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertIsNotNone(outcome.reason)
                self.assertEqual(self._records(), [])
                self.assertEqual(self._affinity().value, 1)

    # -- private commission path (quest-issuance-dialogue-gate) --

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_authorized_commissioner_assigns_its_private_commission(self):
        issuer_key = npc_issuer_key(content_key="grey_granny")
        issuance = self._register_commission(self.quest_key, issuer_key)
        commissioner = self._commissioner("grey_granny")
        unregistered = create_object(PlayerCharacter, key="unregistered seeker")
        unregistered.race = "human"
        unregistered.apply_race_baseline()
        unregistered.location = self.room
        outcome = apply_npc_intent(
            commissioner, unregistered, self._offer_intent(self.quest_key)
        )
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.reason, "quest assigned")
        records = read_records(unregistered)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(records[0].issuer_key, issuer_key)
        resolved = resolve_issuance(records[0].definition_key, records[0].issuer_key)
        self.assertEqual(resolved, issuance)
        self.assertEqual(resolved.settlement, Settlement.AUTO)
        self.assertEqual(commissioner.relations._load(unregistered).value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_identity_form_commissioner_assigns_under_its_primary_key(self):
        commissioner = self._commissioner()
        issuer_key = npc_issuer_key(pk=commissioner.pk)
        issuance = self._register_commission(self.quest_key, issuer_key)
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(records[0].issuer_key, issuer_key)
        self.assertEqual(resolve_issuance(self.quest_key, issuer_key), issuance)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_commissioner_without_issuance_for_the_key_is_rejected(self):
        commissioner = self._commissioner("grey_granny")
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="other_commission")
        )
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, f"no commission {self.quest_key!r} at this issuer"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(commissioner.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unauthorized_npc_cannot_issue_even_when_a_commission_exists(self):
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        plain = create_object(NPC, key="plain bystander", location=self.room)
        outcome = apply_npc_intent(plain, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff or QuestIssuer speaker"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(plain.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_payload_cannot_reach_another_issuers_commission(self):
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        other = self._commissioner()
        outcome = apply_npc_intent(other, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, f"no commission {self.quest_key!r} at this issuer"
        )
        self.assertEqual(self._records(), [])

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_dual_authority_with_both_issuances_fails_verification(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason,
            f"quest {self.quest_key!r} is issued under both this branch and this issuer",
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_dual_authority_resolves_by_the_guild_namespace(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(records[0].issuer_key, guild_issuer_key(self.ALTORIA_BRANCH))
        self.assertEqual(dual.relations._load(self.player).value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_dual_authority_resolves_by_the_private_namespace(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key="guild_branch_other"
            )
        )
        issuance = self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(
            records[0].issuer_key, npc_issuer_key(content_key="grey_granny")
        )
        self.assertEqual(resolve_issuance(self.quest_key, records[0].issuer_key), issuance)
        self.assertEqual(dual.relations._load(self.player).value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_authored_issuer_key_is_rejected(self):
        commissioner = self._commissioner("bad:key")
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest QuestIssuer carries a malformed issuer_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(commissioner.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_branch_key_is_rejected_without_state_change(self):
        malformed = create_object(NPC, key="malformed staff", location=self.room)
        malformed.components.add(
            GuildStaff.create(
                malformed, service_id="malformed-staff", branch_key="bad:branch"
            )
        )
        outcome = apply_npc_intent(malformed, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest GuildStaff carries a malformed branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_issuer_key_fails_closed_over_a_valid_guild_offer(self):
        dual = self._commissioner("bad:key")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest QuestIssuer carries a malformed issuer_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(dual.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_branch_key_fails_closed_over_a_valid_commission(self):
        dual = self._commissioner("grey_granny")
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key="bad:branch"
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest GuildStaff carries a malformed branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(dual.relations._load(self.player))
