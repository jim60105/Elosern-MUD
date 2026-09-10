"""Tests for the durable generated-quest store and startup restore.

Covers the store Script CRUD (get/list/append/clear, idempotent by issuance
identity), the payload serialization round-trip, durable-first registration
with fault injection, startup restore healing the crash window between append
and registration, the restart-then-read quest lifecycle for both issuer
kinds, the guild-board surface after restore, and the ``sync_quest_runtime``
wiring. DB-backed behavior uses ``EvenniaTest``; the pure fault-injection
unit stays DB-free by patching the store boundary.
"""

from dataclasses import replace
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from evennia.utils.create import create_object, create_script
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, QuestIssuer
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, Room
from world.quests.bootstrap import restore_generated_quests, sync_quest_runtime
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    QuestCompileError,
    StageSpawnRequirement,
    _compiled_to_payload,
    compile_quest_blueprint,
    payload_to_registrations,
    register_generated_quest,
    register_restored_quest,
    scene_requirements_for,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
)
from world.quests.generated_quest_store import (
    GeneratedQuestStore,
    StorePayloadConflictError,
    append_payload,
    clear,
    get_store,
    list_payloads,
)
from world.quests.runtime import (
    QuestState,
    abandon_quest,
    accept_quest,
    definition_for,
    read_records,
)
from world.quests.tests._fixtures import RegistryIsolationMixin, accept
from world.rules.action import ActionRequest, ActionResolver
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.guild import register_adventurer
from world.rules.guild_config import load_catalog_into_cache, register_catalog_offers
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    accept_guild_offer,
    list_guild_offers,
)
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    Settlement,
    resolve_issuance,
)
from world.rules.service_view import build_services_view
from world.rules.tests.combat_fixtures import grant_lineage
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

from ._compile_helpers import _anchor_key, _archetype_key, _issuer_key

from tools.spec_traceability import covers_requirement

#: The restart-cast class fights on the kit's spell row.
_T_SKILL = SYNTH_SKILLS["t_ember_burst"].key
_SCOPE = synthetic_registries("skills")


def _defeat_payload(**overrides):
    payload = {
        "name": "討伐低階魔物",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": _issuer_key(),
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": {
                    "layer": "anchor",
                    "archetype": _archetype_key(),
                    "anchor_key": _anchor_key(),
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _characterized_payload(**overrides):
    payload = _defeat_payload()
    payload["stages"][0]["objective"] = {
        "kind": "defeat",
        "quantity": 1,
        "monster_tier": None,
    }
    payload["stages"][0]["location_req"] = {
        "layer": "instance",
        "archetype": _archetype_key(),
        "anchor_key": None,
        "anchor_near": _anchor_key(),
        "xyz": None,
        "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
    }
    payload["stages"][0]["npc_req"] = [
        {
            "role": "bandit",
            "tier": "bandit",
            "disposition": None,
            "display_name": "黑鬍",
            "title": "林間盜匪首領",
            "age": 35,
            "apparent_age": 35,
            "portrait": {"stable_key": "forest_bandit_chief"},
        }
    ]
    payload.update(overrides)
    return payload


def _npc_payload(**overrides):
    payload = _defeat_payload()
    payload["issuer"] = "npc:grey_granny"
    payload["reward"] = {"copper": 50, "items": [], "merit": 0}
    payload.update(overrides)
    return payload


def _clear_process_registries():
    """Empty the four process-global quest registries (restart simulation)."""
    from world.rules.guild_offers import GUILD_OFFER_REGISTRY as _offers

    QUEST_DEFINITION_REGISTRY.clear()
    _offers.clear()
    QUEST_ISSUANCE_REGISTRY.clear()
    SCENE_REQUIREMENT_REGISTRY.clear()


class GeneratedQuestStoreTests(EvenniaTestCase):
    """Task 1.1/4.1: the store Script CRUD contract."""

    def test_get_store_creates_one_persistent_script(self):
        store = get_store()
        self.assertIsInstance(store, GeneratedQuestStore)
        self.assertEqual(len(search_script("generated_quest_store")), 1)
        self.assertEqual(get_store(), store)
        self.assertEqual(list_payloads(), [])

    def test_append_is_idempotent_by_issuance_identity(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        payload = _compiled_to_payload(compiled)
        self.assertTrue(append_payload(payload))
        self.assertFalse(append_payload(payload))
        self.assertEqual(len(list_payloads()), 1)
        other = compile_quest_blueprint(_characterized_payload())
        self.assertTrue(append_payload(_compiled_to_payload(other)))
        self.assertEqual(len(list_payloads()), 2)

    def test_two_commissioners_of_one_definition_coexist_in_the_store(self):
        with patch(
            "world.quests.compile.issuer_is_authorized", return_value=True
        ):
            first = compile_quest_blueprint(_npc_payload(issuer="npc:grey_granny"))
            second = compile_quest_blueprint(_npc_payload(issuer="npc:old_martha"))
        self.assertEqual(first.definition.key, second.definition.key)
        self.assertTrue(append_payload(_compiled_to_payload(first)))
        self.assertTrue(append_payload(_compiled_to_payload(second)))
        self.assertEqual(len(list_payloads()), 2)
        from world.quests.generated_quest_store import remove_payload

        remove_payload(first.definition.key, "npc:grey_granny")
        remaining = list_payloads()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["issuance"]["issuer_key"], "npc:old_martha")

    def test_clear_empties_the_store(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        append_payload(_compiled_to_payload(compiled))
        clear()
        self.assertEqual(list_payloads(), [])
        self.assertEqual(get_store().db.payloads, [])

    def test_duplicate_store_scripts_fail_loudly(self):
        create_script(GeneratedQuestStore, key="generated_quest_store", persistent=True)
        create_script(GeneratedQuestStore, key="generated_quest_store", persistent=True)
        with self.assertRaises(RuntimeError):
            get_store()


class StoreConflictTests(RegistryIsolationMixin, EvenniaTestCase):
    """Durable-first registration rejects store content divergence."""

    def test_append_conflicting_payload_raises_and_keeps_the_store(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        self.assertTrue(
            append_payload(_compiled_to_payload(compiled))
        )
        conflicting = _compiled_to_payload(compiled)
        conflicting["issuance"]["reward"]["copper"] = 999
        with self.assertRaises(StorePayloadConflictError):
            append_payload(conflicting)
        self.assertEqual(len(list_payloads()), 1)

    def test_mid_crash_divergence_aborts_registration_with_no_in_memory_entries(self):
        # Simulate the crash window: the store already holds payload A, the
        # registries are empty, and a same-key quest with a different reward is
        # registered. Preflight passes (empty registries); the store conflict
        # must abort before any in-memory write so the restart cannot regress
        # the stored offer/reward silently.
        compiled = compile_quest_blueprint(_defeat_payload())
        self.assertTrue(
            append_payload(_compiled_to_payload(compiled))
        )
        _clear_process_registries()
        variant = compile_quest_blueprint(
            {**_defeat_payload(), "reward": {"copper": 60, "items": [], "merit": 25}}
        )
        with self.assertRaises(StorePayloadConflictError):
            register_generated_quest(variant)
        self.assertNotIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertNotIn(
            (compiled.definition.key, _issuer_key()),
            GUILD_OFFER_REGISTRY,
        )
        self.assertNotIn(compiled.definition.key, SCENE_REQUIREMENT_REGISTRY)
        self.assertEqual(len(list_payloads()), 1)


class PayloadRoundTripTests(RegistryIsolationMixin, EvenniaTestCase):
    """Task 1.2/4.1: serialization round-trip and registration idempotency."""

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    @covers_requirement("npc-identity-titles::the-existing-scene-builder-and-generated-quest-contracts-are-unchanged-where-not-amended")
    def test_register_persists_a_payload_that_reconstructs_equal_values(self):
        compiled = compile_quest_blueprint(_characterized_payload())
        register_generated_quest(compiled)
        payloads = list_payloads()
        self.assertEqual(len(payloads), 1)
        restored = payload_to_registrations(payloads[0])
        self.assertEqual(restored, compiled)
        requirements = restored.stage_requirements
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].characterizations[0].display_name, "黑鬍")
        self.assertEqual(requirements[0].characterizations[0].title, "林間盜匪首領")
        self.assertEqual(requirements[0].characterizations[0].portrait_stable_key, "forest_bandit_chief")

    @covers_requirement("scene-builder::generated-quest-content-is-durably-stored-at-registration-time")
    def test_registering_the_same_quest_twice_keeps_one_store_payload(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        register_generated_quest(compiled)
        self.assertEqual(len(list_payloads()), 1)


class StoreFailureInjectionTests(RegistryIsolationMixin, unittest.TestCase):
    """Task 2.3: a store write failure leaves every registry unchanged."""

    def test_store_failure_aborts_registration_with_no_in_memory_entries(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        quests_before = dict(QUEST_DEFINITION_REGISTRY)
        offers_before = dict(GUILD_OFFER_REGISTRY)
        requirements_before = dict(SCENE_REQUIREMENT_REGISTRY)
        with patch(
            "world.quests.compile.append_generated_quest_payload",
            side_effect=RuntimeError("store unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                register_generated_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, quests_before)
        self.assertEqual(GUILD_OFFER_REGISTRY, offers_before)
        self.assertEqual(SCENE_REQUIREMENT_REGISTRY, requirements_before)
        self.assertNotIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)


class CorruptStorePayloadTests(RegistryIsolationMixin, EvenniaTestCase):
    """Design D3: malformed store payloads fail loudly at restore time."""

    def _payload(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        return _compiled_to_payload(compiled)

    def _restore_raises(self, payload):
        with self.assertRaises(QuestCompileError):
            restore_generated_quests()

    def test_issuance_naming_an_unknown_guild_branch_is_rejected(self):
        payload = self._payload()
        payload["issuance"]["issuer_key"] = "guild:not_a_branch"
        append_payload(payload)
        self._restore_raises(payload)

    def test_private_commission_issuance_carrying_merit_is_rejected(self):
        payload = self._payload()
        payload["issuance"]["issuer_key"] = "npc:grey_granny"
        payload["issuance"]["settlement"] = "auto"
        append_payload(payload)
        self._restore_raises(payload)

    def test_guild_issuance_with_auto_settlement_is_rejected(self):
        payload = self._payload()
        payload["issuance"]["settlement"] = "auto"
        append_payload(payload)
        self._restore_raises(payload)

    def test_private_commission_with_counter_settlement_is_rejected(self):
        payload = self._payload()
        payload["issuance"]["issuer_key"] = "npc:grey_granny"
        payload["issuance"]["settlement"] = "counter"
        append_payload(payload)
        self._restore_raises(payload)

    def test_unknown_enum_value_is_rejected(self):
        payload = self._payload()
        payload["definition"]["quest_type"] = "bogus"
        append_payload(payload)
        with self.assertRaises(ValueError):
            restore_generated_quests()

    def test_requirement_index_out_of_range_is_rejected(self):
        payload = self._payload()
        payload["requirements"][0]["index"] = 7
        append_payload(payload)
        self._restore_raises(payload)

    def test_requirement_objective_kind_mismatch_is_rejected(self):
        payload = self._payload()
        payload["requirements"][0]["objective_kind"] = "acquire"
        append_payload(payload)
        self._restore_raises(payload)

    def test_conflicting_existing_requirements_are_rejected(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        conflicting = StageSpawnRequirement(
            index=0,
            objective_kind=ObjectiveKind.ACQUIRE,
            location=None,
            archetype=None,
            anchor_near=None,
            scene_sentence=None,
            npc_reqs=(),
        )
        with self.assertRaises(QuestCompileError):
            register_restored_quest(replace(compiled, stage_requirements=(conflicting,)))
        self.assertEqual(
            scene_requirements_for(compiled.definition.key),
            compiled.stage_requirements,
        )


class CrashWindowHealingTests(RegistryIsolationMixin, EvenniaTestCase):
    """Task 2.3: startup restore heals the append-then-crash window."""

    def test_restore_repopulates_all_three_registries_from_the_store(self):
        compiled = compile_quest_blueprint(_characterized_payload())
        self.assertTrue(
            append_payload(_compiled_to_payload(compiled))
        )
        _clear_process_registries()
        restore_generated_quests()
        self.assertEqual(
            QUEST_DEFINITION_REGISTRY.get(compiled.definition.key),
            compiled.definition,
        )
        self.assertEqual(
            GUILD_OFFER_REGISTRY.get((compiled.definition.key, _issuer_key())),
            GuildQuestOffer(
                definition_key=compiled.definition.key,
                issuer_branch_key=_issuer_key(),
                reward=compiled.reward,
            ),
        )
        self.assertEqual(
            scene_requirements_for(compiled.definition.key),
            compiled.stage_requirements,
        )


@_SCOPE
class RestartRestoreIntegrationTests(RegistryIsolationMixin, EvenniaTestCase):
    """Task 4.2: an accepted generated quest survives a simulated restart."""

    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the skill scope is
        # entered here too before the casting entity is built.
        stack = ExitStack()
        stack.enter_context(_SCOPE)
        self.addCleanup(stack.close)
        sync_quest_runtime()
        self.player = create_object(PlayerCharacter, key="restore-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human static magic_power at 術師 tier so the synthetic spell casts pass.
        self.player.traits.magic_power.base = 30
        grant_lineage(self.player, [_T_SKILL])

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve_lethal(self, monster: Monster):
        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({monster.key})},
            {self.player.key: self.player, monster.key: monster},
        )
        request = ActionRequest(
            self.player,
            _T_SKILL,
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    @covers_requirement("quest-lifecycle::generated-quest-definitions-resolve-after-a-server-restart")
    def test_accepted_generated_quest_reads_resolves_and_abandons_after_restore(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        record = accept(self.player, compiled.definition.key)
        _clear_process_registries()
        restore_generated_quests()
        restore_generated_quests()
        records = read_records(self.player)
        self.assertEqual([r.quest_id for r in records], [record.quest_id])
        self.assertEqual(definition_for(records[0]), compiled.definition)
        abandoned = abandon_quest(self.player, record.quest_id)
        self.assertIs(abandoned.state, QuestState.FAILED)
        self.assertEqual(len(list_payloads()), 1)

    @covers_requirement("quest-lifecycle::generated-quest-definitions-resolve-after-a-server-restart")
    def test_accept_bind_progress_complete_path_works_after_restore(self):
        from world.quests.binding import bind_stage_runtime

        compiled = compile_quest_blueprint(_characterized_payload())
        register_generated_quest(compiled)
        record = accept(self.player, compiled.definition.key)
        _clear_process_registries()
        restore_generated_quests()

        room = create_object(InstanceRoom, key="restore-instance")
        monster = self._monster("restore-goblin")
        bound = bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(monster,),
        )
        self.assertEqual(bound.objective_target_ids, (monster.pk,))
        result = self._resolve_lethal(monster)
        self.assertEqual(result.outcome, "success")
        completed = [
            r
            for r in read_records(self.player)
            if r.definition_key == compiled.definition.key
            and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "quest did not auto-complete after restore")


    @covers_requirement("quest-lifecycle::generated-quest-definitions-resolve-after-a-server-restart")
    def test_a_restored_private_commission_resolves_its_reward_and_settlement(self):
        # The genuine carrier scan runs here: a real NPC carries QuestIssuer
        # with an authored key, so compile authorization needs no patch.
        carrier = create_object(NPC, key="grey granny")
        carrier.components.add(QuestIssuer.create(carrier, issuer_key="grey_granny"))
        compiled = compile_quest_blueprint(_npc_payload())
        register_generated_quest(compiled)
        record = accept_quest(self.player, compiled.definition.key, "npc:grey_granny")
        _clear_process_registries()
        restore_generated_quests()
        restore_generated_quests()

        issuance = resolve_issuance(compiled.definition.key, "npc:grey_granny")
        self.assertIsNotNone(issuance)
        self.assertEqual(issuance.reward, compiled.reward)
        self.assertIs(issuance.settlement, Settlement.AUTO)
        records = read_records(self.player)
        self.assertEqual([r.quest_id for r in records], [record.quest_id])
        self.assertEqual([r.issuer_key for r in records], ["npc:grey_granny"])

    @covers_requirement("quest-lifecycle::generated-quest-definitions-resolve-after-a-server-restart")
    def test_restored_issuances_of_both_kinds_register_exactly_once(self):
        carrier = create_object(NPC, key="old martha")
        carrier.components.add(QuestIssuer.create(carrier, issuer_key="old_martha"))
        private = compile_quest_blueprint(_npc_payload(issuer="npc:old_martha"))
        register_generated_quest(private)
        guild = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(guild)
        _clear_process_registries()
        restore_generated_quests()
        restore_generated_quests()

        self.assertEqual(len(list_payloads()), 2)
        self.assertEqual(
            len(
                [
                    key
                    for key in QUEST_ISSUANCE_REGISTRY
                    if key[0] == private.definition.key
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    key
                    for key in GUILD_OFFER_REGISTRY
                    if key[0] == guild.definition.key
                ]
            ),
            1,
        )


class GuildBoardRestoreTests(RegistryIsolationMixin, EvenniaTestCase):
    """Delta guild-quest-board: offers resolve, board stays single, accept works."""

    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        register_catalog_offers(load_catalog_into_cache())
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.hall = create_object(Room, key="restore-guild-hall")
        self.staff = create_object(NPC, key="restore staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key=_issuer_key()
            )
        )
        self.player = create_object(PlayerCharacter, key="restore-board-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    @covers_requirement("guild-quest-board::generated-guild-offers-survive-a-server-restart")
    def test_generated_offer_resolves_after_restore_and_accepted_offer_stays_single(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        accept_guild_offer(self.player, self.staff, compiled.definition.key)
        _clear_process_registries()
        restore_generated_quests()
        restore_generated_quests()

        offers = list_guild_offers(self.player, self.staff)
        self.assertIn(compiled.definition.key, [o.definition_key for o in offers])
        board = build_services_view(self.player).guild.board
        rows = [row for row in board if row.definition_key == compiled.definition.key]
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].accept.enabled)
        self.assertEqual(rows[0].accept.reason_code, "quest_already_active")
        self.assertEqual(
            len(
                [
                    key
                    for key in GUILD_OFFER_REGISTRY
                    if key[0] == compiled.definition.key
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    payload
                    for payload in list_payloads()
                    if payload["definition"]["key"] == compiled.definition.key
                ]
            ),
            1,
        )

    def test_accept_guild_offer_works_after_restore(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        _clear_process_registries()
        restore_generated_quests()
        record = accept_guild_offer(self.player, self.staff, compiled.definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        self.assertIn(compiled.definition.key, [r.definition_key for r in read_records(self.player)])


class SyncQuestRuntimeRestoreTests(RegistryIsolationMixin, EvenniaTestCase):
    """Task 3.2: sync restores generated content ahead of catalog registration."""

    def test_sync_restores_generated_content_and_catalog_together(self):
        from world.quests.catalog import INTRODUCTORY_HUNT

        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        _clear_process_registries()
        sync_quest_runtime()
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            QUEST_DEFINITION_REGISTRY.get(compiled.definition.key),
            compiled.definition,
        )
        self.assertIn(INTRODUCTORY_HUNT.key, QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            scene_requirements_for(compiled.definition.key),
            compiled.stage_requirements,
        )

    @covers_requirement("quest-lifecycle::generated-quest-definitions-resolve-after-a-server-restart")
    def test_sync_is_idempotent_across_repeated_starts(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        register_generated_quest(compiled)
        sync_quest_runtime()
        sync_quest_runtime()
        self.assertEqual(
            sum(
                1
                for definition in QUEST_DEFINITION_REGISTRY.values()
                if definition == compiled.definition
            ),
            1,
        )
        self.assertEqual(len(list_payloads()), 1)


if __name__ == "__main__":
    unittest.main()
