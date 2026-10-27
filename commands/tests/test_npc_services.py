"""Text/web service parity and explicit provider targeting (npc-service-text-parity).

The text surfaces read the same derived descriptors the browser receives:
``services <npc>`` and the appended block of ``看 <NPC>`` print the selected
provider's stable key, canonical label, exact availability reason and the
existing text route, and every provider command accepts one terminal
``@#<dbid>`` that resolves through ``require_service_target`` with no
substitution. Discovery and every rejection are read-only.
"""

from tools.spec_traceability import covers_requirement

# Preimport the import-time-validated equipment rulebook BEFORE the synthetic
# catalogs below can be scoped (same reason as the sibling command suites).
import world.rules.equipment_effects  # noqa: F401

from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.combat import CmdGuildExam
from commands.economy import CmdBuy, CmdSell, CmdShopStock
from commands.guild import (
    CmdGuildAbandon,
    CmdGuildAccept,
    CmdGuildList,
    CmdGuildLog,
    CmdGuildRegister,
    CmdGuildTurnIn,
)
from commands.localized.general import CmdLook
from commands.npc_services import CmdServices
from typeclasses.components import (
    ChurchHost,
    GuildExamReception,
    GuildStaff,
    Merchant,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic, DialogueService
from world.lore.scenes import Scene, Speech
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import QuestState, fulfill_record, read_records
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.quests.transitions import apply_quest_log_replacement
from world.rules.dialogue import live_dialogue_session
from world.rules.dialogue_availability import TOPIC_OPEN, TopicProjection
from world.rules.guild import register_adventurer
from world.rules.guild_exams import ExamReason
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    register_guild_offer,
)
from world.rules.npc_services import (
    STATE_READY,
    UNREADABLE_MESSAGE,
    project_npc_services,
    service_report_lines,
)
from world.rules.npc_schedules import SCHEDULE_BLOCKED_REASON
from world.rules.service_gate import MESSAGE_OFF_ANCHOR
from world.rules.service_messages import rejection_message
from world.rules.service_targets import (
    ServiceTargetReason,
    split_terminal_target,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    price_band,
    rank_reward_band,
    synth_catalog,
    synth_shop_config,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY

BRANCH = SYNTH_GUILD_BRANCH_KEY
_NOT_FOUND = rejection_message(ServiceTargetReason.UNKNOWN_TARGET)
_WRONG_CAPABILITY = rejection_message(ServiceTargetReason.WRONG_CAPABILITY)

# Two locally authored storefronts over the kit goods; the display names are
# this file's own fixtures, never shipped identities.
SHOP_A = "t_parity_stall_a"
SHOP_B = "t_parity_stall_b"
SHOP_A_NAME = "合成甲店"
SHOP_B_NAME = "合成乙店"
_MEAL = "t_huskapple"
_GOODS = ("t_ember_spray", "t_iron_fang", _MEAL)


def _person_bound(component):
    """Declare the authored person binding the shared gate requires."""
    component.service_binding = "person"
    return component


def _place_bound(component, room):
    """Declare the authored place binding of a venue-bound host."""
    component.service_binding = "place"
    component.anchor_room_id = room.pk
    return component


def _snapshot(player, *hosts):
    """Every canonical surface these commands could touch."""
    return {
        "wallet": player.db.wallet,
        "inventory": tuple(player.db.inventory or ()),
        "registration": dict(player.db.guild_registration or {}),
        "rank": player.db.guild_rank,
        "quest_log": player.db.quest_log,
        "hosts": tuple(
            (
                int(host.pk),
                None if host.location is None else int(host.location.pk),
                host.db.schedule_state,
            )
            for host in hosts
        ),
    }


def _scene(scene_id):
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="打擾了。"),
            Speech(speaker="host", text="請說。"),
        ),
    )


def _writes(callable_):
    """Run ``callable_`` and return the SQL write statements it issued."""
    with CaptureQueriesContext(connection) as queries:
        result = callable_()
    writes = [
        query["sql"]
        for query in queries
        if query["sql"].lstrip().split(" ", 1)[0].upper()
        in {"INSERT", "UPDATE", "DELETE", "REPLACE"}
    ]
    return result, writes


class TerminalTargetParserTests(EvenniaTest):
    """The terminal suffix is stripped before every existing parse."""

    def test_suffix_forms(self):
        self.assertEqual(split_terminal_target(""), ("", None, False))
        self.assertEqual(split_terminal_target("12"), ("12", None, False))
        self.assertEqual(split_terminal_target("@#12"), ("", 12, True))
        self.assertEqual(
            split_terminal_target("sword 2 = Bob @#12"), ("sword 2 = Bob", 12, True)
        )
        # Malformed payloads are still explicit attempts, never implicit input.
        for payload in ("@#", "@#abc", "@#-3", "@#1.5"):
            with self.subTest(payload=payload):
                self.assertEqual(split_terminal_target(payload), ("", None, True))
        # An identity token that is not terminal is ordinary input.
        self.assertEqual(
            split_terminal_target("@#12 sword"), ("@#12 sword", None, False)
        )


class _ServiceTextBase(BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="t_parity_hall")
        self.char1.location = self.room

    def _npcs(self, key):
        host = create_object(NPC, key=key, location=self.room)
        return host

    def _merchant(self, host, shop_key="t_parity_shop", *, binding="person"):
        component = Merchant.create(host, service_id=host.key, shop_key=shop_key)
        host.components.add(
            _person_bound(component)
            if binding == "person"
            else _place_bound(component, self.room)
        )
        return component

    def _staff(self, host, branch_key=BRANCH):
        component = GuildStaff.create(
            host, service_id=host.key, branch_key=branch_key
        )
        host.components.add(_person_bound(component))
        return component

    def _reception(self, host, branch_key=BRANCH):
        component = GuildExamReception.create(
            host, service_id=host.key, branch_key=branch_key
        )
        host.components.add(_person_bound(component))
        return component

    def _church(self, host):
        component = ChurchHost.create(
            host,
            service_id=host.key,
            church="t_parity_church",
            initial_arousal="none",
        )
        host.components.add(_person_bound(component))
        return component


class ServiceDiscoveryCommandTests(_ServiceTextBase):
    def setUp(self):
        super().setUp()
        self.host = self._npcs("t_service_host")
        self._merchant(self.host)
        self._staff(self.host)
        self._reception(self.host)
        self._church(self.host)
        self.bystander = self._npcs("t_service_bystander")
        self._merchant(self.bystander, shop_key="t_parity_other_shop")

    def test_services_reports_the_selected_provider_projection(self):
        services = project_npc_services(self.char1, self.char1, self.host)
        self.assertEqual(services.state, STATE_READY)
        output = self.call(CmdServices(), self.host.key)
        self.assertTrue(output.startswith(self.host.key))
        for entry in services.entries:
            self.assertIn(entry.key, output)
            self.assertIn(entry.label, output)
        # Only the selected provider's rows exist: the bystander merchant in
        # the same room contributes nothing.
        self.assertEqual(output.count("  shop　"), 1)
        self.assertNotIn(self.bystander.key, output)
        self.assertEqual(
            output.splitlines(), service_report_lines(self.host, services)
        )
        # Route guidance names the existing text flow with the exact provider.
        for expected in (
            f"shop stock @#{self.host.pk}",
            f"guild register @#{self.host.pk}",
            f"guild list @#{self.host.pk}",
            f"guild turnin <quest_id> @#{self.host.pk}",
            f"guild exam @#{self.host.pk}",
            f"church join #{self.host.pk}",
        ):
            self.assertIn(expected, output)

    def test_alias_none_state_usage_and_read_only_discovery(self):
        plain = self._npcs("t_plain_host")
        before = _snapshot(self.char1, plain)
        output, writes = _writes(lambda: self.call(CmdServices(), plain.key, cmdstring="服務"))
        self.assertEqual(output.strip(), "t_plain_host 目前沒有提供服務。")
        self.assertEqual(writes, [])
        self.assertEqual(before, _snapshot(self.char1, plain))
        self.call(CmdServices(), "", "用法：services <npc>")

    def test_unreadable_is_distinct_from_none(self):
        plain = self._npcs("t_plain_host")
        with patch(
            "world.rules.npc_services.service_available",
            side_effect=RuntimeError("boom"),
        ):
            broken = self.call(CmdServices(), self.host.key)
        self.assertIn(UNREADABLE_MESSAGE, broken)
        self.assertNotIn("的服務：", broken)
        self.assertNotIn("shop", broken)
        self.assertIn("目前沒有提供服務", self.call(CmdServices(), plain.key))

    def test_paused_entries_keep_their_reason_and_no_guidance(self):
        self.host.db.schedule_state = "busy"
        output = self.call(CmdServices(), self.host.key)
        self.assertIn(SCHEDULE_BLOCKED_REASON, output)
        for key in ("shop", "guild.register", "guild.board", "guild.report", "guild.exam", "church.enroll"):
            self.assertIn(key, output)
        self.assertNotIn("shop stock @#", output)
        self.assertNotIn("church join #", output)

    def test_services_look_and_web_payload_share_one_projection(self):
        from web.webclient.presentation.exploration import _services_payload

        # The church entry is inline-disabled (already enrolled) while the
        # merchant entry stays enabled: a mixed ready projection.
        with patch(
            "world.rules.church.read_ledger",
            return_value={"merit": 0, "enrolled_tick": 5},
        ):
            services = project_npc_services(self.char1, self.char1, self.host)
            payload = _services_payload(self.char1, self.host)
            service_output = self.call(CmdServices(), self.host.key)
            look_output = self.call(CmdLook(), self.host.key)
        self.assertEqual(payload, services.as_dict())
        for entry in services.entries:
            for output in (service_output, look_output):
                self.assertIn(entry.key, output)
                self.assertIn(entry.label, output)
                if entry.disabled_reason is not None:
                    self.assertIn(entry.disabled_reason.message, output)
        enrolled = next(entry for entry in services.entries if entry.key == "church.enroll")
        self.assertFalse(enrolled.enabled)
        self.assertIn(enrolled.disabled_reason.message, look_output)
        self.assertNotIn("church join #", look_output)

    def test_hidden_and_departed_objects_never_report_services(self):
        hidden = self._npcs("t_hidden_host")
        hidden.locks.add("view:false()")
        self._merchant(hidden)
        self.call(CmdServices(), hidden.key, _NOT_FOUND)
        self.call(CmdServices(), f"#{hidden.pk}", _NOT_FOUND)
        self.assertNotIn("的服務", self.call(CmdLook(), hidden.key))

        departed = self._npcs("t_departed_host")
        self._merchant(departed)
        departed_pk = departed.pk
        departed.location = create_object(Room, key="t_elsewhere")
        self.call(CmdServices(), f"#{departed_pk}", _NOT_FOUND)
        self.assertNotIn("的服務", self.call(CmdLook(), f"#{departed_pk}"))

    def test_a_hidden_same_name_bystander_never_causes_ambiguity(self):
        hidden_twin = self._npcs(self.host.key)
        hidden_twin.locks.add("view:false()")
        self._merchant(hidden_twin, shop_key="t_parity_twin_shop")
        output = self.call(CmdServices(), self.host.key)
        self.assertIn(f"{self.host.key} 的服務：", output)
        self.assertIn("shop", output)

    def test_dialogue_guidance_starts_nothing(self):
        source = type(
            "Source",
            (),
            {
                "dialogue": AuthoredDialogue(
                    greeting=None,
                    topics=(
                        AuthoredTopic(
                            topic_id="t_synth.offer",
                            keyword="委託",
                            label="洽談委託",
                            fallback=_scene("t_parity_offer_scene"),
                        ),
                    ),
                    services=(
                        DialogueService(
                            key="t_parity_association",
                            topic_id="t_synth.offer",
                            label="洽談委託",
                        ),
                    ),
                )
            },
        )()
        dialogue_host = self._npcs("t_dialogue_host")
        dialogue_host.components.add(
            _person_bound(
                ScriptedDialogue.create(dialogue_host, dialogue_key="t_parity_key")
            )
        )
        row = TopicProjection(
            topic_id="t_synth.offer",
            keyword="委託",
            label="洽談委託",
            availability=TOPIC_OPEN,
            requirement_hint=None,
            descriptor={
                "npc_id": int(dialogue_host.pk),
                "topic_id": "t_synth.offer",
                "context_id": None,
            },
            unread=False,
            predecessors=(),
        )
        with patch(
            "world.rules.dialogue_sources.dialogue_source_for_host",
            return_value=source,
        ), patch(
            "world.rules.dialogue_availability.project_topics",
            return_value=(row,),
        ), patch(
            "world.rules.dialogue.authorized_dialogue_open", return_value=True
        ):
            output = self.call(CmdServices(), dialogue_host.key)
            self.assertIsNone(live_dialogue_session(self.char1))
        self.assertIn(f"talk {dialogue_host.key}（話題 t_synth.offer）", output)
        self.assertIn("dialogue.t_parity_association", output)


class TargetedShopCommandTests(_ServiceTextBase):
    def setUp(self):
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "items",
            "prices",
            "elements",
            "shops",
        )
        super().setUp()
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    SHOP_A: synth_shop_config(
                        SHOP_A, _GOODS, display_name_zh=SHOP_A_NAME
                    ),
                    SHOP_B: synth_shop_config(
                        SHOP_B, _GOODS, display_name_zh=SHOP_B_NAME
                    ),
                }
            ),
        )
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.db.wallet = 500
        self.keeper_a = create_object(NPC, key="t_keeper_a", location=self.room)
        self.merchant_a = self._merchant(self.keeper_a, SHOP_A)
        self.merchant_a.merchant_stock = {key: 20 for key in _GOODS}
        self.keeper_b = create_object(NPC, key="t_keeper_b", location=self.room)
        self.merchant_b = self._merchant(self.keeper_b, SHOP_B)
        # Below the shared stock cap so the sell side can still accept goods.
        self.merchant_b.merchant_stock = {key: 10 for key in _GOODS}

    def _stock(self, merchant, key):
        return merchant.merchant_stock[key]

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_stock_listing_uses_exactly_the_selected_shop(self):
        self.assertIn(
            SHOP_A_NAME, self.call(CmdShopStock(), f"@#{self.keeper_a.pk}")
        )
        self.assertNotIn(
            SHOP_B_NAME, self.call(CmdShopStock(), f"@#{self.keeper_a.pk}")
        )
        self.assertIn(
            SHOP_B_NAME, self.call(CmdShopStock(), f"@#{self.keeper_b.pk}")
        )
        self.assertNotIn(
            SHOP_A_NAME, self.call(CmdShopStock(), f"@#{self.keeper_b.pk}")
        )

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_trade_settles_only_against_the_selected_merchant(self):
        floor, _ceiling = price_band(_MEAL)
        with patch("world.rules.economy.get_world_clock") as clock:
            clock.return_value.tick = 12 * 3600
            self.call(CmdBuy(), f"{_MEAL} 2 @#{self.keeper_a.pk}", "你買了 2 個")
        self.assertEqual(self._stock(self.merchant_a, _MEAL), 18)
        self.assertEqual(self._stock(self.merchant_b, _MEAL), 10)
        self.assertEqual(self.char1.db.wallet, 500 - 2 * (floor + 2))
        self.char1.db.inventory = [_MEAL]
        with patch("world.rules.economy.get_world_clock") as clock:
            clock.return_value.tick = 12 * 3600
            self.call(CmdSell(), f"{_MEAL} 1 @#{self.keeper_b.pk}", "你賣了 1 個")
        self.assertEqual(self._stock(self.merchant_a, _MEAL), 18)
        self.assertEqual(self._stock(self.merchant_b, _MEAL), 11)
        self.assertEqual(self.char1.db.wallet, 500 - 2 * (floor + 2) + floor)

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_a_departed_target_is_never_replaced_by_the_bystander(self):
        departed_pk = self.keeper_a.pk
        self.keeper_a.location = create_object(Room, key="t_shop_elsewhere")
        before = _snapshot(self.char1, self.keeper_a, self.keeper_b)
        stock_before = dict(self.merchant_b.merchant_stock)
        for command, args in (
            (CmdShopStock(), f"@#{departed_pk}"),
            (CmdBuy(), f"{_MEAL} 1 @#{departed_pk}"),
            (CmdSell(), f"{_MEAL} 1 @#{departed_pk}"),
        ):
            output = self.call(command, args)
            self.assertIn(_NOT_FOUND, output)
            self.assertNotIn(SHOP_B_NAME, output)
        self.assertEqual(before, _snapshot(self.char1, self.keeper_a, self.keeper_b))
        self.assertEqual(self.merchant_b.merchant_stock, stock_before)

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_off_anchor_and_wrong_capability_refusals_change_nothing(self):
        component = self.keeper_a.components.get(Merchant.get_component_slot())
        component.service_binding = "place"
        component.anchor_room_id = create_object(Room, key="t_real_anchor").pk
        before = _snapshot(self.char1, self.keeper_a)
        self.assertIn(
            MESSAGE_OFF_ANCHOR, self.call(CmdShopStock(), f"@#{self.keeper_a.pk}")
        )
        clerk = self._npcs("t_shop_clerk")
        self._staff(clerk)
        self.assertIn(
            _WRONG_CAPABILITY, self.call(CmdShopStock(), f"@#{clerk.pk}")
        )
        self.assertEqual(before, _snapshot(self.char1, self.keeper_a))

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_a_paused_merchant_refuses_with_its_reason_and_no_transaction(self):
        self.keeper_a.db.schedule_state = "busy"
        before = _snapshot(self.char1, self.keeper_a)
        stock_before = dict(self.merchant_a.merchant_stock)
        self.assertIn(
            SCHEDULE_BLOCKED_REASON, self.call(CmdShopStock(), f"@#{self.keeper_a.pk}")
        )
        self.assertIn(
            SCHEDULE_BLOCKED_REASON,
            self.call(CmdBuy(), f"{_MEAL} 1 @#{self.keeper_a.pk}"),
        )
        self.assertEqual(before, _snapshot(self.char1, self.keeper_a))
        self.assertEqual(self.merchant_a.merchant_stock, stock_before)

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_malformed_suffix_and_omitted_target_never_fall_back(self):
        self.assertIn(_NOT_FOUND, self.call(CmdShopStock(), "@#abc"))
        self.assertNotIn(SHOP_A_NAME, self.call(CmdShopStock(), "@#abc"))
        # Omission keeps today's ambiguity refusal with two merchants present.
        self.call(CmdShopStock(), "", "這裡沒有商人。")
        self.call(CmdBuy(), f"{_MEAL} 1", "這裡沒有商人。")


class _GuildTargetBase(_ServiceTextBase, QuestRegistryIsolation):
    def setUp(self):
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "items",
            "prices",
            "elements",
            "guild_branches",
        )
        super().setUp()
        register_catalog()
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())
        self.addCleanup(self._restore_offers)
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.hall = self.room
        self.staff_a = self._npcs("t_guild_staff_a")
        self._staff(self.staff_a)
        self.staff_b = self._npcs("t_guild_staff_b")
        self._staff(self.staff_b)

    def _restore_offers(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)

    def _offer(self, definition_key="introductory_hunt"):
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition_key,
                issuer_branch_key=BRANCH,
                reward=QuestReward(copper=rank_reward_band("F")[0], items=(), merit=25),
            )
        )


class TargetedGuildCommandTests(_GuildTargetBase):
    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_explicit_staff_survives_a_same_class_bystander(self):
        self.staff_a.db.schedule_state = "busy"
        before = _snapshot(self.char1, self.staff_a, self.staff_b)
        self.assertIn(
            SCHEDULE_BLOCKED_REASON,
            self.call(CmdGuildRegister(), f"@#{self.staff_a.pk}"),
        )
        self.assertEqual(before, _snapshot(self.char1, self.staff_a, self.staff_b))
        self.call(
            CmdGuildRegister(), f"@#{self.staff_b.pk}", "你已註冊為冒險者"
        )
        self.assertEqual(self.char1.db.guild_registration["branch_key"], BRANCH)

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_omitted_target_keeps_the_ambiguous_host_refusal(self):
        self.call(CmdGuildRegister(), "", "這裡沒有公會服務人員")
        self.assertIsNone(self.char1.db.guild_registration)

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_a_departed_target_never_substitutes_the_remaining_staff(self):
        self.staff_a.location = create_object(Room, key="t_guild_elsewhere")
        self.call(CmdGuildRegister(), f"@#{self.staff_a.pk}", _NOT_FOUND)
        self.assertIsNone(self.char1.db.guild_registration)

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_list_accept_turnin_and_abandon_use_the_selected_staff(self):
        self._offer()
        register_adventurer(self.char1, self.staff_b)
        self.assertIn(
            "introductory_hunt",
            self.call(CmdGuildList(), f"@#{self.staff_b.pk}"),
        )
        self.call(
            CmdGuildAccept(),
            f"introductory_hunt @#{self.staff_b.pk}",
            "你接取了任務",
        )
        record = next(
            item
            for item in read_records(self.char1)
            if item.definition_key == "introductory_hunt"
        )
        completed = fulfill_record(
            record, QUEST_DEFINITION_REGISTRY["introductory_hunt"]
        )
        apply_quest_log_replacement(
            self.char1,
            [
                completed if item.quest_id == record.quest_id else item
                for item in read_records(self.char1)
            ],
        )
        self.staff_a.db.schedule_state = "busy"
        before = _snapshot(self.char1, self.staff_a, self.staff_b)
        self.assertIn(
            SCHEDULE_BLOCKED_REASON,
            self.call(CmdGuildTurnIn(), f"{record.quest_id} @#{self.staff_a.pk}"),
        )
        self.assertEqual(before, _snapshot(self.char1, self.staff_a, self.staff_b))
        self.call(
            CmdGuildTurnIn(),
            f"{record.quest_id} @#{self.staff_b.pk}",
            "你回報了任務",
        )

        from world.quests.tests._fixtures import accept

        second = accept(self.char1, "introductory_hunt")
        self.assertEqual(second.state, QuestState.IN_PROGRESS)
        self.assertIn(
            SCHEDULE_BLOCKED_REASON,
            self.call(CmdGuildAbandon(), f"{second.quest_id} @#{self.staff_a.pk}"),
        )
        self.assertEqual(
            next(
                item
                for item in read_records(self.char1)
                if item.quest_id == second.quest_id
            ).state,
            QuestState.IN_PROGRESS,
        )
        self.call(
            CmdGuildAbandon(), f"{second.quest_id} @#{self.staff_b.pk}", "你放棄了任務"
        )

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_personal_commands_stay_host_free(self):
        self.char1.location = create_object(Room, key="t_guild_empty")
        self.assertIn("任務記錄", self.call(CmdGuildLog(), ""))


class TargetedExamCommandTests(_GuildTargetBase):
    def setUp(self):
        super().setUp()
        self.reception_a = self._npcs("t_reception_a")
        self._reception(self.reception_a)
        self.reception_b = self._npcs("t_reception_b")
        self._reception(self.reception_b, branch_key="t_other_branch")

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_explicit_reception_is_the_only_counter_considered(self):
        self.reception_a.db.schedule_state = "busy"
        self.assertIn(
            SCHEDULE_BLOCKED_REASON,
            self.call(CmdGuildExam(), f"E @#{self.reception_a.pk}"),
        )
        # The free counter is selected by identity; its own branch and the
        # actor's (absent) registration decide the answer.
        self.assertIn(
            rejection_message(ExamReason.UNREGISTERED),
            self.call(CmdGuildExam(), f"E @#{self.reception_b.pk}"),
        )
        self.assertIsNone(self.char1.db.active_combat)

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_selected_reception_supplies_the_branch(self):
        register_adventurer(self.char1, self.staff_a)
        self.assertIn(
            rejection_message(ExamReason.WRONG_BRANCH),
            self.call(CmdGuildExam(), f"E @#{self.reception_b.pk}"),
        )
        own_branch = self.call(CmdGuildExam(), f"E @#{self.reception_a.pk}")
        self.assertNotIn(rejection_message(ExamReason.WRONG_BRANCH), own_branch)
        self.assertIsNone(self.char1.db.active_combat)

    @covers_requirement(
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host"
    )
    def test_a_departed_reception_never_substitutes(self):
        self.reception_a.location = create_object(Room, key="t_counter_elsewhere")
        self.call(CmdGuildExam(), f"E @#{self.reception_a.pk}", _NOT_FOUND)
        self.assertIsNone(self.char1.db.active_combat)
