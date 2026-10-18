"""Tests for the version-1 ``party_member`` presentation panel.

Presenter shape (viewed-member facts, bond pips from the stage table, escort
and possession verdicts, commander persona while possessing, fallback to the
commander, maximal bounds, no raw affinity, read-only rendering), the pure
validator's drift rejections, the unavailable forms, and the registry/action
wiring.

The canonical requirement IDs this module carries (attached at the change's
archive/sync commit, once traceability could index ``openspec/specs`` — the
party-panel-v3-view-member precedent):

- ``webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel``
- ``webclient-party-member-panel::companion-facts-are-truthful-and-bounded``
- ``webclient-party-member-panel::companion-actions-are-server-authored-descriptors``
- ``webclient-party-member-panel::the-commander-persona-edit-descriptor-is-server-authored``
- ``webclient-party-member-panel::commander-facts-carry-persona-prose``
- ``webclient-party-member-panel::the-panel-follows-the-viewed-member``
"""

from copy import deepcopy
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from tools.spec_traceability import covers_requirement
from web.webclient.actions.exploration_actions import _party_leave_adapter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party import PARTY_MAX_SLOTS
from web.webclient.presentation.party_member import (
    ACTION_COMMANDER_PERSONA,
    ACTION_NPC_PERSONA,
    ACTION_PARTY_LEAVE,
    ACTION_POSSESS,
    ACTION_POSSESS_RELEASE,
    MAX_BOND_STAGE_CODE_POINTS,
    MAX_REASON_CODE_POINTS,
    PARTY_MEMBER_SCHEMA_VERSION,
    PartyMemberPanelError,
    party_member_presenter,
    validate_party_member,
)
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.quests.catalog import register_catalog
from world.quests.definitions import EscortCompletion, QuestStage, QuestType
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.quests.tests._fixtures import QuestRegistryIsolation, escort, quest, register
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import get_config
from world.rules.party import (
    ESCORT_BOUND_MESSAGE,
    HANDBACK_FIRST_MESSAGE,
    add_temporary_source,
    has_general_membership,
    is_companion,
    join_party,
    leave_party,
    reasons_for,
)
from world.rules.npc_persona import initialize_npc_persona
from world.rules.possession import (
    POSSESSED_REFUSAL_MESSAGES,
    REASON_POSSESSED_TALK,
    enter_possession,
)

NOT_EXPLORING_MESSAGE = "你目前無法編輯角色資料。"


def _player(key="成員測試者"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _companion(key, room):
    npc = create_object(NPC, key=key, location=room)
    npc.race = "human"
    npc.apply_race_baseline()
    return npc


def _descriptor(action_id, params, enabled, reason=None):
    return {
        "action_id": action_id,
        "params": params,
        "enabled": enabled,
        "reason": reason,
    }


def _companion_actions(member_id=41, *, leave_reason=None, persona_reason=None):
    return [
        _descriptor(ACTION_POSSESS, {"npc_id": member_id}, True),
        _descriptor(ACTION_PARTY_LEAVE, {"npc_id": member_id}, leave_reason is None, leave_reason),
        _descriptor(ACTION_NPC_PERSONA, {"npc_id": member_id}, persona_reason is None, persona_reason),
    ]


def _commander_actions(reason=None):
    return [
        _descriptor(ACTION_COMMANDER_PERSONA, {}, reason is None, reason),
    ]


def _intimate():
    return {
        "arousal": "中等",
        "wetness": "微濕",
        "shame": "輕微",
        "exposure": "低",
        "climax_phase": "未達",
        "climax_today": 2,
    }


def _companion_section(member_id=41, **overrides):
    section = {
        "bond": {"stage": "親睦", "step": 3, "steps": 7},
        "membership": {"general": True, "temporary_commissions": []},
        "intimate": None,
        "actions": _companion_actions(member_id),
    }
    section.update(overrides)
    return section


def _commander_section(**overrides):
    section = {
        "persona": {
            "background": None,
            "personality": "沉穩",
            "life_story": None,
            "habit": None,
        },
        "intimate": None,
        "actions": _commander_actions(),
    }
    section.update(overrides)
    return section


def _panel(role="companion", member_id=41, section=None):
    if section is None:
        section = (
            _companion_section(member_id)
            if role == "companion"
            else _commander_section()
        )
    return {
        "schema_version": PARTY_MEMBER_SCHEMA_VERSION,
        "available": True,
        "kind": "party_member",
        "member_id": member_id,
        "role": role,
        "companion": section if role == "companion" else None,
        "commander": section if role == "commander" else None,
    }


def _numbers(value):
    """Every integer anywhere in a JSON-shaped payload."""
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, dict):
        return [number for child in value.values() for number in _numbers(child)]
    if isinstance(value, list):
        return [number for child in value for number in _numbers(child)]
    return []


class PartyMemberValidatorTests(unittest.TestCase):
    """The exact version-1 schema rejects every shape drift."""

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_valid_companion_and_commander_forms_normalize_identically(self):
        companion = _panel()
        self.assertEqual(validate_party_member(companion), companion)
        commander = _panel("commander", member_id=7, section=_commander_section())
        self.assertEqual(validate_party_member(commander), commander)

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_shape_drift_is_rejected(self):
        base_companion = _panel()
        base_commander = _panel("commander", member_id=7, section=_commander_section())
        drift = {
            "unknown top-level field": {**base_companion, "extra": 1},
            "both sections non-null": {
                **base_companion,
                "commander": _commander_section(),
            },
            "companion without its section": {**base_companion, "companion": None},
            "commander with a companion section": {
                **base_commander,
                "companion": _companion_section(),
            },
            "unknown role": {**base_companion, "role": "ally"},
            "unsupported schema version": {
                **base_companion,
                "schema_version": PARTY_MEMBER_SCHEMA_VERSION + 1,
            },
            "unavailable form": {**base_companion, "available": False},
            "wrong kind": {**base_companion, "kind": "party"},
            "boolean member id": {**base_companion, "member_id": True},
            "zero member id": {**base_companion, "member_id": 0},
            "bond unknown field": _panel(
                section=_companion_section(
                    bond={"stage": "親睦", "step": 3, "steps": 7, "affinity": 30}
                )
            ),
            "bond blank stage": _panel(
                section=_companion_section(
                    bond={"stage": "  ", "step": 3, "steps": 7}
                )
            ),
            "bond step zero": _panel(
                section=_companion_section(
                    bond={"stage": "親睦", "step": 0, "steps": 7}
                )
            ),
            "bond step beyond steps": _panel(
                section=_companion_section(
                    bond={"stage": "親睦", "step": 8, "steps": 7}
                )
            ),
            "bond over-bound stage": _panel(
                section=_companion_section(
                    bond={
                        "stage": "長" * (MAX_BOND_STAGE_CODE_POINTS + 1),
                        "step": 1,
                        "steps": 7,
                    }
                )
            ),
            "membership unknown field": _panel(
                section=_companion_section(
                    membership={
                        "general": True,
                        "temporary_commissions": [],
                        "extra": 1,
                    }
                )
            ),
            "membership numeric general": _panel(
                section=_companion_section(
                    membership={"general": 1, "temporary_commissions": []}
                )
            ),
            "duplicate commissions": _panel(
                section=_companion_section(
                    membership={
                        "general": False,
                        "temporary_commissions": [
                            {"quest_id": "q", "role_id": "r", "label": "l"},
                            {"quest_id": "q", "role_id": "r", "label": "l"},
                        ],
                    }
                )
            ),
            "unknown intimate field": _panel(
                section=_companion_section(intimate={**_intimate(), "extra": 1})
            ),
            "unknown intimate level": _panel(
                section=_companion_section(
                    intimate={**_intimate(), "arousal": "很高"}
                )
            ),
            "actions arity": _panel(
                section=_companion_section(
                    actions=_companion_actions()[:2]
                )
            ),
            "actions order": _panel(
                section=_companion_section(
                    actions=list(reversed(_companion_actions()))
                )
            ),
            "wrong action id": _panel(
                section=_companion_section(
                    actions=[
                        _descriptor("explore.possess_other", {"npc_id": 41}, True),
                        *_companion_actions()[1:],
                    ]
                )
            ),
            "wrong action params": _panel(
                section=_companion_section(
                    actions=[
                        _descriptor(ACTION_POSSESS, {"npc_id": 42}, True),
                        *_companion_actions()[1:],
                    ]
                )
            ),
            "enabled with a reason": _panel(
                section=_companion_section(
                    actions=[
                        _descriptor(ACTION_POSSESS, {"npc_id": 41}, True, "不行"),
                        *_companion_actions()[1:],
                    ]
                )
            ),
            "disabled without a reason": _panel(
                section=_companion_section(
                    actions=[
                        _descriptor(ACTION_POSSESS, {"npc_id": 41}, False),
                        *_companion_actions()[1:],
                    ]
                )
            ),
            "blank reason": _panel(
                section=_companion_section(
                    actions=_companion_actions(leave_reason="   ")
                )
            ),
            "over-bound reason": _panel(
                section=_companion_section(
                    actions=_companion_actions(
                        leave_reason="長" * (MAX_REASON_CODE_POINTS + 1)
                    )
                )
            ),
            "commander persona unknown key": _panel(
                "commander",
                member_id=7,
                section=_commander_section(
                    persona={
                        "background": None,
                        "personality": None,
                        "life_story": None,
                        "habit": None,
                        "identity": {},
                    }
                ),
            ),
            "commander persona over bound": _panel(
                "commander",
                member_id=7,
                section=_commander_section(
                    persona={
                        "background": "長" * 601,
                        "personality": None,
                        "life_story": None,
                        "habit": None,
                    }
                ),
            ),
            "commander action arity": _panel(
                "commander",
                member_id=7,
                section=_commander_section(actions=[]),
            ),
            "commander wrong action": _panel(
                "commander",
                member_id=7,
                section=_commander_section(
                    actions=[
                        _descriptor(ACTION_NPC_PERSONA, {"npc_id": 7}, True)
                    ]
                ),
            ),
        }
        for name, payload in drift.items():
            with self.subTest(name=name):
                with self.assertRaises(ProtocolValidationError):
                    validate_party_member(payload)

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_maximal_payload_stays_within_the_canonical_byte_bound(self):
        member_id = MAX_SAFE_INTEGER
        stage = "長" * MAX_BOND_STAGE_CODE_POINTS
        label = "長" * 128
        reason = "長" * MAX_REASON_CODE_POINTS
        commissions = [
            {"quest_id": f"{index:02d}" + "q" * 126, "role_id": label, "label": label}
            for index in range(PARTY_MAX_SLOTS)
        ]
        companion = _panel(
            member_id=member_id,
            section=_companion_section(
                member_id,
                bond={"stage": stage, "step": 7, "steps": 7},
                membership={"general": False, "temporary_commissions": commissions},
                intimate=_intimate(),
                actions=_companion_actions(
                    member_id, leave_reason=reason, persona_reason=reason
                ),
            ),
        )
        normalized = validate_party_member(companion)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)

        commander = _panel(
            "commander",
            member_id=member_id,
            section=_commander_section(
                persona={
                    "background": "長" * 600,
                    "personality": "長" * 600,
                    "life_story": "長" * 600,
                    "habit": "長" * 600,
                },
                intimate=_intimate(),
                actions=_commander_actions(reason=reason),
            ),
        )
        normalized = validate_party_member(commander)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    @covers_requirement(
        "webclient-party-member-panel::companion-facts-are-truthful-and-bounded"
    )
    def test_a_raw_affinity_number_is_never_part_of_the_shape(self):
        payload = _panel()
        self.assertNotIn(30, _numbers(payload))
        with self.assertRaises(ProtocolValidationError):
            validate_party_member(_panel(section=_companion_section(affinity=30)))


class PartyMemberPresenterTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.room = create_object(Room, key="成員大廳")
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()

    def _init_card(self, npc):
        initialize_npc_persona(
            npc,
            {
                "identity": {"public": "隊友", "hidden": ""},
                "appearance": "俐落。",
                "personality": "沉穩。",
                "speech_style": "簡短。",
                "life_story": "同行已久。",
                "habit": "擦拭武器。",
                "social_connection": "",
            },
            {"kind": "profile", "profile": "member_test"},
        )

    def _render(self, *, actor=None, member=None):
        selection = (
            None
            if member is None
            else PartyViewSelection(int(self.player.pk), int(member.pk), "member")
        )
        context = PresentationContext(
            actor=actor or self.player,
            protocol_version=1,
            party_view=selection,
        )
        return party_member_presenter(context)

    def _escort_member(self, key="護衛測試者", owner=None):
        """A real temporary-only escort binding for ``self.player``."""
        owner = self.player if owner is None else owner
        register(
            quest(
                "member_escort",
                quest_type=QuestType.ESCORT,
                stages=(
                    QuestStage(
                        0,
                        escort(
                            completion=EscortCompletion.RENDEZVOUS,
                            meeting_role_refs=("meeting",),
                        ),
                    ),
                ),
            )
        )
        npc = _companion(key, owner.location)
        record = QuestRecord(
            quest_id="member_escort:1",
            definition_key="member_escort",
            issuer_key=f"npc:#{npc.pk}",
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(npc.pk,),
            failure_reason=None,
            protected_roles=(("escortee", npc.pk),),
        )
        owner.db.quest_log = [
            *list(owner.db.quest_log or []),
            to_storage(record),
        ]
        add_temporary_source(npc, owner, record.quest_id, "escortee")
        return npc, record

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    @covers_requirement(
        "webclient-party-member-panel::companion-facts-are-truthful-and-bounded"
    )
    def test_companion_payload_is_exact_and_reports_bond_pips(self):
        companion = _companion("薇拉", self.room)
        self._init_card(companion)
        join_party(companion, self.player)
        outcome = apply_affinity_change(
            companion, self.player, AffinitySource.QUEST_COMPLETION, 30
        )
        self.assertTrue(outcome.applied)
        affinity_value = companion.relations.affinity_for(self.player)
        config = get_config()
        stage = config.stage_for_value(affinity_value)
        step = next(
            index
            for index, entry in enumerate(config.stages, 1)
            if entry.id == stage.id
        )

        payload = self._render(member=companion)

        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "available",
                "kind",
                "member_id",
                "role",
                "companion",
                "commander",
            },
        )
        self.assertEqual(payload["schema_version"], PARTY_MEMBER_SCHEMA_VERSION)
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["kind"], "party_member")
        self.assertEqual(payload["member_id"], int(companion.pk))
        self.assertEqual(payload["role"], "companion")
        self.assertIsNone(payload["commander"])
        self.assertEqual(
            set(payload["companion"]),
            {"bond", "membership", "intimate", "actions"},
        )
        self.assertEqual(
            payload["companion"]["bond"],
            {"stage": stage.name, "step": step, "steps": len(config.stages)},
        )
        self.assertEqual(
            payload["companion"]["membership"],
            {"general": True, "temporary_commissions": []},
        )
        self.assertIsNone(payload["companion"]["intimate"])
        self.assertEqual(
            [action["action_id"] for action in payload["companion"]["actions"]],
            [ACTION_POSSESS, ACTION_PARTY_LEAVE, ACTION_NPC_PERSONA],
        )
        for action in payload["companion"]["actions"]:
            self.assertEqual(action["params"], {"npc_id": int(companion.pk)})
            self.assertIs(action["enabled"], True)
            self.assertIsNone(action["reason"])
        # The raw affinity value never ships anywhere in the payload.
        self.assertNotIn(affinity_value, _numbers(payload))

    @covers_requirement(
        "webclient-party-member-panel::companion-actions-are-server-authored-descriptors"
    )
    def test_escort_bound_leave_descriptor_uses_the_existing_reason(self):
        companion, record = self._escort_member()
        payload = self._render(member=companion)
        leave = payload["companion"]["actions"][1]
        self.assertEqual(leave["action_id"], ACTION_PARTY_LEAVE)
        self.assertIs(leave["enabled"], False)
        self.assertEqual(
            leave["reason"],
            ESCORT_BOUND_MESSAGE.format(quests=record.quest_id),
        )

    @covers_requirement(
        "webclient-party-member-panel::companion-actions-are-server-authored-descriptors"
    )
    def test_general_plus_temporary_member_may_relinquish_general_membership(self):
        # ``leave_party`` removes only the general identity of a dual member;
        # handback-first applies only when the removal would detach entirely.
        companion, _record = self._escort_member()
        join_party(companion, self.player)
        self.player.db.possession = {
            "npc_dbid": int(companion.pk),
            "since_tick": 0,
        }
        companion.db.possessed_by = int(self.player.pk)
        payload = self._render(actor=companion, member=companion)
        leave = payload["companion"]["actions"][1]
        self.assertIs(leave["enabled"], True)
        self.assertIsNone(leave["reason"])

    @covers_requirement(
        "webclient-party-member-panel::companion-actions-are-server-authored-descriptors"
    )
    def test_advertised_leave_succeeds_for_the_possessed_general_temporary_member(self):
        # ``self.char1`` carries the live account session the party authority
        # boundary requires; the custom test player does not.
        commander = self.char1
        companion, record = self._escort_member(owner=commander)
        join_party(companion, commander)
        enter_possession(commander, companion)
        result = _party_leave_adapter(companion, {"npc_id": int(companion.pk)})
        self.assertEqual(result["outcome"], "success", result)
        self.assertFalse(has_general_membership(companion, commander))
        self.assertTrue(is_companion(companion, commander))
        self.assertEqual(
            reasons_for(companion, commander),
            ((record.quest_id, "escortee"),),
        )
        self.assertEqual(commander.db.possession["npc_dbid"], int(companion.pk))
        self.assertEqual(companion.db.possessed_by, int(commander.pk))

    @covers_requirement(
        "webclient-party-member-panel::companion-actions-are-server-authored-descriptors"
    )
    @covers_requirement(
        "webclient-party-member-panel::companion-facts-are-truthful-and-bounded"
    )
    def test_possessed_companion_offers_release_and_keeps_companion_facts(self):
        companion = _companion("艾拉", self.room)
        join_party(companion, self.player)
        companion.db.sexual = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
        }
        self.player.db.persona = {
            "personality": "指揮官個性",
            "life_story": "",
            "habit": "",
            "background": "",
        }
        companion.db.persona = {
            "personality": "同伴個性",
            "life_story": "",
            "habit": "",
            "background": "",
        }

        before = self._render(member=companion)
        self.player.db.possession = {
            "npc_dbid": int(companion.pk),
            "since_tick": 0,
        }
        companion.db.possessed_by = int(self.player.pk)
        after = self._render(actor=companion, member=companion)

        possession = after["companion"]["actions"][0]
        self.assertEqual(possession["action_id"], ACTION_POSSESS_RELEASE)
        self.assertIs(possession["enabled"], True)
        self.assertIsNone(possession["reason"])
        # The companion facts are identical; the remaining descriptors carry
        # their possession verdicts.
        for field in ("bond", "membership", "intimate"):
            self.assertEqual(after["companion"][field], before["companion"][field])
        leave = after["companion"]["actions"][1]
        self.assertEqual(leave["action_id"], ACTION_PARTY_LEAVE)
        self.assertIs(leave["enabled"], False)
        self.assertEqual(leave["reason"], HANDBACK_FIRST_MESSAGE)
        persona = after["companion"]["actions"][2]
        self.assertEqual(persona["action_id"], ACTION_NPC_PERSONA)
        self.assertIs(persona["enabled"], False)
        self.assertEqual(
            persona["reason"], POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
        )

    @covers_requirement(
        "webclient-party-member-panel::commander-facts-carry-persona-prose"
    )
    @covers_requirement(
        "webclient-party-member-panel::the-commander-persona-edit-descriptor-is-server-authored"
    )
    def test_commander_section_carries_persona_intimate_and_edit_descriptor(self):
        self.player.db.persona = {
            "personality": "沉穩",
            "life_story": "來自邊境",
            "habit": "  ",
            "background": "",
        }
        self.player.db.sexual = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
            "climax_today": 2,
        }
        payload = self._render()
        self.assertEqual(payload["role"], "commander")
        self.assertEqual(payload["member_id"], int(self.player.pk))
        self.assertIsNone(payload["companion"])
        self.assertEqual(
            payload["commander"]["persona"],
            {
                "background": None,
                "personality": "沉穩",
                "life_story": "來自邊境",
                "habit": None,
            },
        )
        self.assertEqual(payload["commander"]["intimate"], _intimate())
        self.assertEqual(len(payload["commander"]["actions"]), 1)
        action = payload["commander"]["actions"][0]
        self.assertEqual(action["action_id"], ACTION_COMMANDER_PERSONA)
        self.assertEqual(action["params"], {})
        self.assertIs(action["enabled"], True)
        self.assertIsNone(action["reason"])

    @covers_requirement(
        "webclient-party-member-panel::commander-facts-carry-persona-prose"
    )
    @covers_requirement(
        "webclient-party-member-panel::the-commander-persona-edit-descriptor-is-server-authored"
    )
    def test_possession_shows_the_commanders_own_persona_and_disables_its_editor(self):
        companion = _companion("艾拉", self.room)
        join_party(companion, self.player)
        self.player.db.persona = {
            "personality": "指揮官個性",
            "life_story": "",
            "habit": "",
            "background": "",
        }
        companion.db.persona = {
            "personality": "同伴個性",
            "life_story": "",
            "habit": "",
            "background": "",
        }
        self.player.db.possession = {
            "npc_dbid": int(companion.pk),
            "since_tick": 0,
        }
        companion.db.possessed_by = int(self.player.pk)

        payload = self._render(actor=companion)
        self.assertEqual(payload["role"], "commander")
        self.assertEqual(
            payload["commander"]["persona"]["personality"], "指揮官個性"
        )
        action = payload["commander"]["actions"][0]
        self.assertIs(action["enabled"], False)
        self.assertEqual(action["reason"], NOT_EXPLORING_MESSAGE)

    @covers_requirement(
        "webclient-party-member-panel::the-panel-follows-the-viewed-member"
    )
    def test_the_panel_falls_back_to_the_commander_after_leave(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        selection = PartyViewSelection(
            int(self.player.pk), int(companion.pk), "member"
        )
        context = PresentationContext(
            actor=self.player, protocol_version=1, party_view=selection
        )
        self.assertEqual(
            party_member_presenter(context)["member_id"],
            int(companion.pk),
        )
        leave_party(companion, self.player, "dismissed")
        payload = party_member_presenter(context)
        self.assertEqual(payload["member_id"], int(self.player.pk))
        self.assertEqual(payload["role"], "commander")

    @covers_requirement(
        "webclient-party-member-panel::the-party-member-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_rendering_leaves_an_unchanged_attribute_snapshot(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        companion.db.sexual = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
        }
        self.player.db.persona = {
            "personality": "沉穩",
            "life_story": "",
            "habit": "",
            "background": "",
        }
        before = {
            "party": deepcopy(self.player.db.party),
            "meta": deepcopy(self.player.db.party_meta),
            "player_persona": deepcopy(self.player.db.persona),
            "player_sexual": deepcopy(self.player.db.sexual),
            "player_traits": deepcopy(dict(self.player.traits.trait_data)),
            "relations": deepcopy(companion.db.relations_data),
            "sexual": deepcopy(companion.db.sexual),
            "persona": deepcopy(companion.db.persona),
            "traits": deepcopy(dict(companion.traits.trait_data)),
            "possession": deepcopy(self.player.db.possession),
            "possessed_by": companion.db.possessed_by,
        }
        first = self._render(member=companion)
        second = self._render(member=companion)
        self.assertEqual(first, second)
        self.assertEqual(self.player.db.party, before["party"])
        self.assertEqual(self.player.db.party_meta, before["meta"])
        self.assertEqual(self.player.db.persona, before["player_persona"])
        self.assertEqual(self.player.db.sexual, before["player_sexual"])
        self.assertEqual(
            dict(self.player.traits.trait_data), before["player_traits"]
        )
        self.assertEqual(companion.db.relations_data, before["relations"])
        self.assertEqual(companion.db.sexual, before["sexual"])
        self.assertEqual(companion.db.persona, before["persona"])
        self.assertEqual(dict(companion.traits.trait_data), before["traits"])
        self.assertEqual(self.player.db.possession, before["possession"])
        self.assertEqual(companion.db.possessed_by, before["possessed_by"])

    def test_unavailable_forms_use_the_registry_reason(self):
        cases = {}
        creation_pending = _player("待建立者")
        creation_pending.location = self.room
        creation_pending.creation_pending = True
        cases["creation pending"] = creation_pending
        no_location = _player("無處者")
        cases["no location"] = no_location
        cases["dangling possession"] = _companion("陌生附身者", self.room)
        for name, actor in cases.items():
            with self.subTest(name=name):
                payload = self.registry.render(
                    "party_member",
                    PresentationContext(actor=actor, protocol_version=1),
                )
                self.assertEqual(
                    payload,
                    {
                        "schema_version": PARTY_MEMBER_SCHEMA_VERSION,
                        "available": False,
                        "reason": {
                            "code": "party_member_unavailable",
                            "message": "隊伍成員資訊目前無法顯示",
                        },
                    },
                )


class PartyMemberWiringTests(EvenniaTest):
    @covers_requirement(
        "webclient-party-member-panel::the-panel-follows-the-viewed-member"
    )
    def test_registry_registers_the_panel_and_the_selection_republishes_it(self):
        from web.webclient.actions.registry import build_production_action_registry

        registry = build_production_registry()
        spec = registry.spec("party_member")
        self.assertEqual(spec.schema_version, PARTY_MEMBER_SCHEMA_VERSION)
        action = build_production_action_registry().spec("party.view_member")
        self.assertEqual(
            action.affected_panels,
            ("party", "party_member", "character", "party_inventory"),
        )
