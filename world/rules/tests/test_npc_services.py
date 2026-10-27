"""Derived contextual service projection (npc-contextual-service-projection).

One read-only owner turns the selected NPC's capabilities and its explicit
dialogue associations into bounded service entries. These tests pin the fixed
mapping order, the difference between entry availability and operation
eligibility, the exact target-bound routes, the distinct unreadable state, and
that a projection writes nothing.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
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
from world.rules.dialogue_availability import (
    TOPIC_LOCKED,
    TOPIC_OPEN,
    TopicProjection,
)
from world.rules.npc_services import (
    STATE_NONE,
    STATE_READY,
    STATE_UNREADABLE,
    ServiceRoute,
    native_entry_count,
    project_npc_services,
    validate_service_capacity,
)


def _scene(scene_id):
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="打擾了。"),
            Speech(speaker="host", text="請說。"),
        ),
    )


def _dialogue_source(services=()):
    """A resolved-source stand-in carrying explicit service associations."""

    class _Source:
        def __init__(self):
            self.dialogue = AuthoredDialogue(
                greeting=None,
                topics=(
                    AuthoredTopic(
                        topic_id="t_synth.offer",
                        keyword="委託",
                        label="詢問委託",
                        fallback=_scene("t_synth.offer_scene"),
                    ),
                ),
                services=tuple(services),
            )

    return _Source()


def _row(topic_id, *, availability=TOPIC_OPEN, hint=None):
    return TopicProjection(
        topic_id=topic_id,
        keyword="委託",
        label="詢問委託",
        availability=availability,
        requirement_hint=hint,
        descriptor={"npc_id": 1, "topic_id": topic_id, "context_id": None},
        unread=False,
        predecessors=(),
    )


class _ProjectionBase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="t_projection_hall")
        self.player = create_object(PlayerCharacter, key="t_projection_player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room

    def _host(self, name):
        return create_object(NPC, key=name, location=self.room)

    def _add(self, host, component):
        host.components.add(component)
        return component

    def _merchant(self, host, *, binding="person", anchor=None):
        component = self._add(
            host, Merchant.create(host, service_id=host.key, shop_key="t_shop")
        )
        component.service_binding = binding
        component.anchor_room_id = anchor
        return component

    def _staff(self, host, *, binding="person", anchor=None):
        component = self._add(
            host,
            GuildStaff.create(host, service_id=host.key, branch_key="t_branch"),
        )
        component.service_binding = binding
        component.anchor_room_id = anchor
        return component

    def _reception(self, host, *, binding="person", anchor=None):
        component = self._add(
            host,
            GuildExamReception.create(
                host, service_id=host.key, branch_key="t_branch"
            ),
        )
        component.service_binding = binding
        component.anchor_room_id = anchor
        return component

    def _church(self, host, *, binding="person", anchor=None):
        component = self._add(
            host,
            ChurchHost.create(
                host,
                service_id=host.key,
                church="t_church",
                initial_arousal="none",
            ),
        )
        component.service_binding = binding
        component.anchor_room_id = anchor
        return component

    def _project(self, host, actor=None):
        actor = actor or self.player
        return project_npc_services(actor, actor, host)


class NativeProjectionTests(_ProjectionBase):
    def test_mapping_order_and_exact_routes(self):
        host = self._host("t_全服務")
        self._merchant(host)
        self._staff(host)
        self._reception(host)
        self._church(host)
        services = self._project(host)
        self.assertEqual(services.state, STATE_READY)
        self.assertEqual(
            [entry.key for entry in services.entries],
            [
                "shop",
                "guild.register",
                "guild.board",
                "guild.report",
                "guild.exam",
                "church.enroll",
            ],
        )
        self.assertEqual(
            [entry.route.as_dict() for entry in services.entries],
            [
                {"kind": "services", "npc_id": int(host.pk), "section": "shop"},
                {
                    "kind": "services",
                    "npc_id": int(host.pk),
                    "section": "registration",
                },
                {"kind": "services", "npc_id": int(host.pk), "section": "board"},
                {"kind": "services", "npc_id": int(host.pk), "section": "report"},
                {"kind": "services", "npc_id": int(host.pk), "section": "rank"},
                {"kind": "command", "npc_id": int(host.pk), "command": "church join"},
            ],
        )
        self.assertTrue(all(entry.enabled for entry in services.entries))

    def test_a_bystander_never_contributes_entries(self):
        host = self._host("t_櫃檯")
        self._staff(host)
        bystander = self._host("t_旁觀商人")
        self._merchant(bystander)
        services = self._project(bystander)
        self.assertEqual([entry.key for entry in services.entries], ["shop"])
        self.assertEqual(
            [entry.key for entry in self._project(host).entries],
            ["guild.register", "guild.board", "guild.report"],
        )

    def test_a_plain_host_reports_no_services(self):
        host = self._host("t_路人")
        services = self._project(host)
        self.assertEqual(services.state, STATE_NONE)
        self.assertEqual(services.entries, ())

    def test_off_anchor_place_binding_keeps_its_entry_with_a_reason(self):
        anchor = create_object(Room, key="t_anchor")
        host = self._host("t_行商")
        self._merchant(host, binding="place", anchor=anchor.pk)
        (entry,) = self._project(host).entries
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "off_anchor")
        self.assertEqual(entry.disabled_reason.message, "他的服務不在這裡營業。")

    def test_a_schedule_block_disables_the_entry_with_its_reason(self):
        host = self._host("t_忙碌商")
        self._merchant(host)
        host.db.schedule_state = "busy"
        (entry,) = self._project(host).entries
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "schedule_blocked")

    def test_a_possessed_actor_keeps_only_the_merchant_counters(self):
        host = self._host("t_全服務")
        self._merchant(host)
        self._staff(host)
        self._reception(host)
        self._church(host)
        owner = create_object(PlayerCharacter, key="t_owner")
        owner.location = self.room
        self.player.db.possessed_by = owner.pk
        services = self._project(host)
        enabled = [entry.key for entry in services.entries if entry.enabled]
        self.assertEqual(enabled, ["shop"])
        for entry in services.entries:
            if entry.key != "shop":
                self.assertEqual(entry.disabled_reason.code, "possessed_service")


class EntryVersusOperationTests(_ProjectionBase):
    def test_an_unaffordable_shopper_still_gets_the_shop_entry(self):
        host = self._host("t_商")
        self._merchant(host)
        self.player.db.wallet = 0
        (entry,) = self._project(host).entries
        self.assertTrue(entry.enabled)

    def test_the_exam_entry_never_depends_on_registration_merit_or_host(self):
        host = self._host("t_考官")
        self._reception(host)
        (entry,) = self._project(host).entries
        self.assertEqual(entry.key, "guild.exam")
        self.assertTrue(entry.enabled)

    def test_registration_and_board_stay_open_before_registration(self):
        host = self._host("t_職員")
        self._staff(host)
        services = self._project(host)
        self.assertTrue(all(entry.enabled for entry in services.entries))

    def test_church_enrollment_is_inline_disabled_once_enrolled(self):
        host = self._host("t_主祭")
        self._church(host)
        (entry,) = self._project(host).entries
        self.assertTrue(entry.enabled)
        with patch(
            "world.rules.church.read_ledger",
            return_value={"merit": 0, "enrolled_tick": 5},
        ):
            (enrolled,) = self._project(host).entries
        self.assertFalse(enrolled.enabled)
        self.assertEqual(enrolled.disabled_reason.code, "already_enrolled")

    def test_church_enrollment_needs_a_player_acting_body(self):
        host = self._host("t_主祭")
        self._church(host)
        companion = create_object(NPC, key="t_同伴")
        companion.location = self.room
        (entry,) = self._project(host, actor=companion).entries
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "not_a_player")


class DialogueAssociationProjectionTests(_ProjectionBase):
    def setUp(self):
        super().setUp()
        self.host = self._host("t_對話主人")
        self._add(self.host, ScriptedDialogue.create(self.host, dialogue_key="t_key"))
        component = self.host.components.get(ScriptedDialogue.get_component_slot())
        component.service_binding = "person"
        self.service = DialogueService(
            key="guild_report_dialogue",
            topic_id="t_synth.offer",
            label="交談回報委託",
        )

    def _project_with(self, *, source, rows, actor=None):
        actor = actor or self.player
        with patch(
            "world.rules.dialogue_sources.dialogue_source_for_host",
            return_value=source,
        ), patch(
            "world.rules.dialogue_availability.project_topics",
            return_value=tuple(rows),
        ), patch(
            "world.rules.dialogue.authorized_dialogue_open", return_value=True
        ):
            return project_npc_services(actor, actor, self.host)

    def test_an_open_association_is_a_dialogue_route_entry(self):
        services = self._project_with(
            source=_dialogue_source([self.service]), rows=[_row("t_synth.offer")]
        )
        (entry,) = services.entries
        self.assertEqual(entry.key, "dialogue.guild_report_dialogue")
        self.assertEqual(entry.label, "交談回報委託")
        self.assertTrue(entry.enabled)
        self.assertEqual(
            entry.route.as_dict(),
            {
                "kind": "dialogue",
                "npc_id": int(self.host.pk),
                "topic_id": "t_synth.offer",
            },
        )

    def test_a_hidden_association_is_omitted_entirely(self):
        services = self._project_with(
            source=_dialogue_source([self.service]), rows=[]
        )
        self.assertEqual(services.state, STATE_NONE)

    def test_schedule_refusal_never_discloses_a_hidden_association(self):
        self.host.db.schedule_state = "busy"
        services = self._project_with(source=_dialogue_source([self.service]), rows=[])
        self.assertEqual(services.state, STATE_NONE)

    def test_a_locked_association_stays_focusable_but_disabled(self):
        services = self._project_with(
            source=_dialogue_source([self.service]),
            rows=[_row("t_synth.offer", availability=TOPIC_LOCKED, hint="需要聲望")],
        )
        (entry,) = services.entries
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "topic_locked")
        self.assertEqual(entry.disabled_reason.message, "需要聲望")


class ProjectionFailureTests(_ProjectionBase):
    def test_a_projection_failure_is_the_distinct_unreadable_state(self):
        host = self._host("t_壞掉")
        self._merchant(host)
        with patch(
            "world.rules.npc_services.service_available",
            side_effect=RuntimeError("boom"),
        ), patch("world.rules.npc_services.log_warn") as warned:
            services = self._project(host)
        self.assertEqual(services.state, STATE_UNREADABLE)
        self.assertEqual(services.entries, ())
        self.assertTrue(warned.called)

    def test_a_read_projection_writes_nothing(self):
        host = self._host("t_全服務")
        self._merchant(host)
        self._staff(host)
        self._church(host)
        classes = (
            Merchant,
            GuildStaff,
            GuildExamReception,
            ChurchHost,
            ScriptedDialogue,
        )

        def snapshot():
            return (
                host.location,
                host.key,
                host.db.schedule_state,
                self.player.location,
                self.player.db.wallet,
                tuple(self.player.db.inventory or ()),
                tuple(
                    (
                        component_class.name,
                        host.components.get(component_class.get_component_slot()).service_binding,
                        host.components.get(component_class.get_component_slot()).anchor_room_id,
                    )
                    for component_class in classes
                    if host.components.has(component_class.name)
                ),
            )

        before = snapshot()
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            self._project(host)
        writes = [
            query["sql"] for query in queries
            if query["sql"].lstrip().split(" ", 1)[0].upper()
            in {"INSERT", "UPDATE", "DELETE", "REPLACE"}
        ]
        self.assertEqual(writes, [])
        after = snapshot()
        self.assertEqual(before, after)


class ServiceCapacityTests(EvenniaTest):
    def test_native_entry_count_matches_the_mapping(self):
        self.assertEqual(native_entry_count(()), 0)
        self.assertEqual(native_entry_count({Merchant.name}), 1)
        self.assertEqual(native_entry_count({GuildStaff.name}), 3)
        self.assertEqual(
            native_entry_count({Merchant.name, GuildStaff.name, ChurchHost.name}), 5
        )

    def test_capacity_rejects_overflow_instead_of_truncating(self):
        validate_service_capacity({GuildStaff.name}, 13)  # 3 + 13 == 16
        with self.assertRaises(ValueError):
            validate_service_capacity({GuildStaff.name}, 14)
        with self.assertRaises(TypeError):
            validate_service_capacity({GuildStaff.name}, True)
        with self.assertRaises(ValueError):
            validate_service_capacity({GuildStaff.name}, -1)

    def test_route_shape_rejects_a_foreign_or_malformed_value(self):
        with self.assertRaises(ValueError):
            ServiceRoute("services", 1, section="counter")
        with self.assertRaises(ValueError):
            ServiceRoute("dialogue", 1)
        with self.assertRaises(ValueError):
            ServiceRoute("command", 1, command="church pray")
        with self.assertRaises(ValueError):
            ServiceRoute("drawer", 1)
