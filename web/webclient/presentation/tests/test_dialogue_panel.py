"""Tests for the version-2 ``dialogue`` presentation panel (webclient-align-10).

Presenter shape (party-row host vocabulary, canonical bond-stage NAME or null,
table-order keyword choices, the recorded line), registered unavailable forms
(no session, corrupt-at-parse stored line, stale host dbid), read-only
rendering, the pure validator's drift rejections, the coordinator mode matrix
(creation > combat > dialogue-live > exploration), the live->clear committed
transitions through the wire, and the NPC-departure panel push seam.
The two new ``webclient-dialogue-session`` IDs are annotated on their
establishing tests (landed with the change's spec-sync commit).
"""

from copy import deepcopy
from types import SimpleNamespace
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tools.spec_traceability import covers_requirement

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.exploration_actions import _engage_adapter
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import dialogue as dialogue_module
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import _scripted_keyword_descriptors
from web.webclient.presentation.combat_panel import MAX_PARTICIPANT_REF
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.dialogue import (
    DIALOGUE_MAX_CHOICES,
    DIALOGUE_SCHEMA_VERSION,
    MAX_DIALOGUE_PORTRAIT_REF,
    DialoguePanelError,
    dialogue_presenter,
    validate_dialogue,
)
from web.webclient.presentation.protocol import (
    DIALOGUE_BUNDLE_MAX_BYTES,
    DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES,
    DIALOGUE_ENVELOPE_MAX_BYTES,
    DIALOGUE_PANEL_MAX_BYTES,
    DIALOGUE_SCENE_MAX_BYTES,
    JSONSafetyError,
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
    validate_ui_snapshot,
    validate_ui_update,
)
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.tests._support import (
    committed_view,
    last_frame,
    recorded_frames,
)
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.art_view import (
    MAX_PORTRAIT_CATALOG,
    ArtViewError,
    portrait_catalog_key,
)
from world.rules.combat_session import engage, is_in_active_session
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    MAX_DIALOGUE_SESSION_LINE_CODE_POINTS,
    DialogueDefinition,
    KeywordResponse,
    clear_dialogue_session,
    live_dialogue_session,
    open_or_refresh_dialogue,
)
from world.rules.movement_settlement import settle_movement
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.quests.catalog import register_catalog
from world.lore.dialogue.conditions import Carries, RaceIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_RACES,
    synthetic_registries,
)

UNAVAILABLE_PAYLOAD = {
    "schema_version": DIALOGUE_SCHEMA_VERSION,
    "available": False,
    "reason": {"code": "dialogue_unavailable", "message": "對話目前無法顯示"},
}

CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


def _player(key="對話面板測試者"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _host(room, key="公會職員"):
    return _host_with_key(room, GUILD_STAFF_DIALOGUE_KEY, key=key)


def _host_with_key(room, dialogue_key, key="公會職員"):
    npc = create_object(NPC, key=key, location=room)
    npc.components.add(
        ScriptedDialogue.create(npc, dialogue_key=dialogue_key)
    )
    return npc


# A synthetic availability table: one openly qualified topic, one visibly
# locked topic with an authored refusal, and one race-hidden topic. Every
# scene carries a unique sentinel so "no protected body before selection" is
# a recursive string search, not a field-shape guess.
_PANEL_AVAILABILITY_KEY = "t_panel_availability"
_PANEL_OPEN = f"{_PANEL_AVAILABILITY_KEY}.open"
_PANEL_LOCKED = f"{_PANEL_AVAILABILITY_KEY}.locked"
_PANEL_HIDDEN = f"{_PANEL_AVAILABILITY_KEY}.hidden"
_PANEL_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_PANEL_RACE = next(iter(SYNTH_RACES))
_PANEL_OTHER_RACE = next(key for key in SYNTH_RACES if key != _PANEL_RACE)

_PANEL_SENTINEL_OPEN = "PANEL-OPEN-BODY"
_PANEL_SENTINEL_LOCKED = "PANEL-LOCKED-FORMAL"
_PANEL_SENTINEL_REFUSAL = "PANEL-LOCKED-REFUSAL"
_PANEL_SENTINEL_HIDDEN = "PANEL-HIDDEN-BODY"
_PANEL_SENTINELS = (
    _PANEL_SENTINEL_OPEN,
    _PANEL_SENTINEL_LOCKED,
    _PANEL_SENTINEL_REFUSAL,
    _PANEL_SENTINEL_HIDDEN,
)


def _panel_scene(scene_id: str, host_text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _panel_availability_dialogue() -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成職員抬眼：「有事就問。」",
        topics=(
            AuthoredTopic(
                topic_id=_PANEL_OPEN,
                keyword="合成公開",
                label="合成公開",
                fallback=_panel_scene("t_panel_availability_open", _PANEL_SENTINEL_OPEN),
            ),
            AuthoredTopic(
                topic_id=_PANEL_LOCKED,
                keyword="合成鎖定",
                label="合成鎖定",
                fallback=_panel_scene(
                    "t_panel_availability_locked_formal", _PANEL_SENTINEL_LOCKED
                ),
                requires=Carries(item_key=_PANEL_ITEM),
                unavailable="locked",
                refusal=_panel_scene(
                    "t_panel_availability_locked_refusal", _PANEL_SENTINEL_REFUSAL
                ),
            ),
            AuthoredTopic(
                topic_id=_PANEL_HIDDEN,
                keyword="合成隱藏",
                label="合成隱藏",
                fallback=_panel_scene("t_panel_availability_hidden", _PANEL_SENTINEL_HIDDEN),
                requires=RaceIs(race_key=_PANEL_OTHER_RACE),
                unavailable="hidden",
            ),
        ),
    )


def _panel_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _panel_strings(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _panel_strings(item)


def _panel_body_sentinels(payload) -> list[str]:
    return [
        text
        for text in _panel_strings(payload)
        if any(sentinel in text for sentinel in _PANEL_SENTINELS)
    ]


# File-local six-keyword dialogue row: the panel-cap decoupling below is a
# panel-vs-affordance mechanic, so it proves itself against a locally authored
# over-cap table rather than an incidental shipped row's keyword count.
_T_OVER_CAP_KEY = "t_panel_over_cap_host"

_T_OVER_CAP_ROW = DialogueDefinition(
    greeting="櫃檯後的人抬起眼：「有事說一聲就好。」",
    responses=tuple(
        KeywordResponse(f"合成關鍵詞{index}", f"「合成回應{index}。」")
        for index in range(18)
    ),
)


class _RecordingSession:
    """Minimal session stand-in that records every transport send."""

    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 931

    def msg(self, **kwargs):
        self.sent.append(kwargs)


def _choice(keyword):
    return {
        "topic_id": f"guild_staff.{keyword}",
        "keyword_id": keyword,
        "label": keyword,
        "availability": "open",
        "requirement_hint": None,
        "unread": False,
        "predecessors": [],
        "action_payload": {"npc_id": 41, "topic_id": f"guild_staff.{keyword}", "context_id": "ctx-1"},
    }


def _available(**overrides):
    payload = {
        "schema_version": DIALOGUE_SCHEMA_VERSION,
        "available": True,
        "kind": "dialogue",
        "host": {
            "identity": 41,
            "display_name": "公會職員",
            "portrait_ref": None,
        },
        "actor": {
            "identity": 1,
            "display_name": "測試者",
            "portrait_ref": None,
        },
        "bond_stage": "熟人",
        "context_id": "ctx-1",
        "delivery": None,
        "choices": [_choice("公會"), _choice("任務")],
        "pure_chain": [],
        "reading_revision": 0,
        "completed_topic_ids": [],
        "unlock_batch": None,
    }
    payload.update(overrides)
    return payload


class DialoguePresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        # The bond-stage reader resolves affinity cap-break quests.
        register_catalog()
        self.room = create_object(Room, key="公會大廳")
        self.away = create_object(Room, key="別處", location=None)
        self.player = _player()
        self.player.location = self.room
        self.host = _host(self.room)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("dialogue", self.context)

    @covers_requirement('npc-identity-titles::every-npc-identity-surface-uses-the-plain-authored-name')
    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_available_form_is_exact_vocabulary_for_a_bonded_host(self):
        apply_affinity_change(
            self.host, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        affinity_value = self.host.relations.affinity_for(self.player)
        self.host.attributes.add("npc_title", "合成稱號")
        open_or_refresh_dialogue(self.player, self.host, "任務板在右側。")

        payload = self._render()
        self.assertNotIn("合成稱號", str(payload["host"]))
        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "available",
                "kind",
                "host",
                "actor",
                "bond_stage",
                "context_id",
                "delivery",
                "choices",
                "pure_chain",
                "reading_revision",
                "completed_topic_ids",
                "unlock_batch",
            },
        )
        self.assertEqual(payload["schema_version"], DIALOGUE_SCHEMA_VERSION)
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["kind"], "dialogue")
        self.assertEqual(
            payload["host"],
            {
                "identity": int(self.host.pk),
                "display_name": self.host.key,
                # The host is a present dialogue host, so it is in the art view
                # the catalog is keyed from and the panel ships its key.
                "portrait_ref": portrait_catalog_key(self.host.pk),
            },
        )
        self.assertEqual(payload["bond_stage"], self.host.relations.stage_for(self.player).name)
        self.assertEqual(payload["delivery"]["lines"][0]["text"], "任務板在右側。")
        # Same vocabulary owner as the interact target descriptor, table order,
        # truncated to the panel's own bound (align-11).
        self.assertEqual(
            payload["choices"],
            _scripted_keyword_descriptors(
                self.host,
                actor=self.player,
                context_id=live_dialogue_session(self.player).context_id,
            )[:DIALOGUE_MAX_CHOICES],
        )
        self.assertTrue(payload["choices"])
        # The shipped guild_staff row authors exactly the panel's pressable
        # four (a fifth keyword could never be rendered); the cap-vs-pool
        # truncation itself is proven against an over-cap synthetic row below.
        # The raw affinity number never rides the wire.
        self.assertNotIn(affinity_value, payload.values())

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_host_portrait_reference_matches_the_art_catalog(self):
        # One registry and one context, so the dialogue key is checked against
        # the catalog the ``art`` panel actually commits beside it — never
        # against a key the client would have to construct.
        open_or_refresh_dialogue(self.player, self.host, "任務板在右側。")
        dialogue = self._render()
        art = self.registry.render("art", self.context)
        self.assertIs(art["available"], True)
        portrait_ref = dialogue["host"]["portrait_ref"]
        self.assertEqual(portrait_ref, portrait_catalog_key(self.host.pk))
        self.assertIn(portrait_ref, art["portrait_catalog"])
        entry = art["portrait_catalog"][portrait_ref]
        self.assertEqual(entry["context"]["name"], self.host.key)
        # Membership, never resolution success, gates the key: the entry behind
        # it is the complete canonical descriptor with no real candidate while
        # the portrait is unresolved, and the panel ships the key anyway.
        artwork = entry["artwork"]
        self.assertEqual(artwork["attempts"], [])
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        self.assertEqual(
            artwork["terminal"]["resource"]["origin"], "silhouette"
        )

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_generative_host_outside_the_art_view_carries_a_null_reference(self):
        # An LLMNPC is conversable (explore.talk_open accepts it) but carries
        # no dialogue component and no named portrait policy, so the art view
        # the key is drawn from excludes it: the panel stays available and says
        # null instead of shipping a key the committed catalog lacks.
        bard = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        open_or_refresh_dialogue(self.player, bard, "唱首歌吧。")
        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["host"]["identity"], int(bard.pk))
        self.assertIsNone(payload["host"]["portrait_ref"])
        art = self.registry.render("art", self.context)
        self.assertNotIn(portrait_catalog_key(bard.pk), art["portrait_catalog"])

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_catalog_cap_drop_carries_a_null_reference(self):
        # design.md's named risk: the art view keeps the first
        # MAX_PORTRAIT_CATALOG eligible entities by identity, so a present host
        # past the cap is absent from the committed catalog and the panel must
        # agree with it rather than advertise a key that is not there.
        crowded = create_object(Room, key="擁擠的大廳")
        self.player.location = crowded
        fillers = [
            _host(crowded, key=f"職員{index}")
            for index in range(MAX_PORTRAIT_CATALOG)
        ]
        host = _host(crowded, key="最後的職員")
        open_or_refresh_dialogue(self.player, host, "歡迎。")

        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertIsNone(payload["host"]["portrait_ref"])
        catalog = self.registry.render("art", self.context)["portrait_catalog"]
        self.assertEqual(len(catalog), MAX_PORTRAIT_CATALOG)
        self.assertIn(portrait_catalog_key(fillers[-1].pk), catalog)
        self.assertNotIn(portrait_catalog_key(host.pk), catalog)

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_unbuildable_art_view_carries_a_null_reference(self):
        # A combat actor with no session record is the reachable ArtViewError:
        # the presenter catches it, ships null, and keeps the panel available.
        # The handler is pinned by a mock because that raise site is reachable
        # only through a combat branch this presenter's own gates preclude; the
        # mock keeps the degrade path honest if art_view grows another raise.
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        with mock.patch.object(
            dialogue_module,
            "build_art_view",
            side_effect=ArtViewError("no active combat session"),
        ):
            payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["host"]["identity"], int(self.host.pk))
        self.assertIsNone(payload["host"]["portrait_ref"])

    def test_unbonded_host_discloses_a_null_stage(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        payload = self._render()
        self.assertIsNone(payload["bond_stage"])
        self.assertIs(payload["available"], True)

    @synthetic_registries(
        "dialogue", extra={"dialogue": {_T_OVER_CAP_KEY: _T_OVER_CAP_ROW}}
    )
    def test_panel_choice_cap_is_independent_of_the_affordance_keyword_pool(self):
        # A six-keyword dialogue row renders its full pool through the shared
        # keyword descriptor owner — the interact-target affordance pool —
        # while the dialogue panel truncates to its own four-row bound
        # (webclient-align-11 decoupling).
        host = _host_with_key(self.room, _T_OVER_CAP_KEY, key="合成對話主")
        open_or_refresh_dialogue(self.player, host, "歡迎。")
        full_pool = _scripted_keyword_descriptors(host, actor=self.player)
        self.assertEqual(len(full_pool), 16)
        payload = self._render()
        self.assertEqual(len(payload["choices"]), DIALOGUE_MAX_CHOICES)
        expected_choices = _scripted_keyword_descriptors(
            host,
            actor=self.player,
            context_id=live_dialogue_session(self.player).context_id,
        )[:DIALOGUE_MAX_CHOICES]
        self.assertEqual(payload["choices"], expected_choices)
        self.assertEqual(
            [row["keyword_id"] for row in payload["choices"]],
            [row["keyword_id"] for row in expected_choices],
        )

    def test_no_session_renders_the_registered_unavailable_form(self):
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_corrupt_stored_line_degrades_unavailable_not_internal(self):
        for corrupt_line in (
            "言" * (MAX_DIALOGUE_SESSION_LINE_CODE_POINTS + 1),
            "\ud800坏掉的行",
        ):
            with self.subTest(line=repr(corrupt_line[:16])):
                self.player.db.dialogue_session = {
                    "npc_id": int(self.host.pk),
                    "line": corrupt_line,
                    "updated_tick": None,
                }
                self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_stale_host_never_reaches_the_wire(self):
        # A dbid that never resolves: not live -> registered unavailable.
        self.player.db.dialogue_session = {
            "npc_id": 9_999_999,
            "line": "幽靈台詞。",
            "updated_tick": None,
        }
        payload = self._render()
        self.assertEqual(payload, UNAVAILABLE_PAYLOAD)
        self.assertNotIn("9999999", str(payload))
        # A present host outside the location is likewise not live; the host
        # waits in another room so the departure hook never pre-clears it.
        parked = _host(self.away, "停放的職員")
        self.player.db.dialogue_session = {
            "npc_id": int(parked.pk),
            "line": "遠方台詞。",
            "updated_tick": None,
        }
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_presenter_is_read_only(self):
        apply_affinity_change(
            self.host, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        open_or_refresh_dialogue(self.player, self.host, "第一句。")
        stored_before = deepcopy(self.player.db.dialogue_session)
        affinity_before = self.host.relations.affinity_for(self.player)

        # The catalog read the portrait reference comes from is part of the
        # read-only claim: it runs on every render and writes nothing.
        with mock.patch.object(
            dialogue_module,
            "build_art_view",
            wraps=dialogue_module.build_art_view,
        ) as build_art_view:
            first = self._render()
            second = self._render()
        self.assertEqual(build_art_view.call_count, 2)
        self.assertEqual(first, second)
        self.assertEqual(self.player.db.dialogue_session, stored_before)
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)

    def test_refresh_updates_the_line_in_place(self):
        open_or_refresh_dialogue(self.player, self.host, "第一句。")
        first = self._render()
        open_or_refresh_dialogue(self.player, self.host, "第二句。")
        second = self._render()
        self.assertIs(second["available"], True)
        self.assertEqual(second["delivery"]["lines"][0]["text"], "第二句。")
        self.assertEqual(second["host"], first["host"])
        self.assertEqual(second["choices"], first["choices"])

    def test_panel_is_registered_in_the_production_registry(self):
        self.assertIn("dialogue", self.registry.panel_names)

    def test_host_with_an_empty_table_ships_empty_choices(self):
        plain = create_object(NPC, key="無表NPC", location=self.room)
        open_or_refresh_dialogue(self.player, plain, "嗯。")
        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["choices"], [])

    def test_creation_pending_puppet_never_sees_the_available_form(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        self.player.creation_pending = True
        try:
            self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)
        finally:
            self.player.creation_pending = False


class DialogueValidatorTests(unittest.TestCase):
    def test_available_form_validates(self):
        self.assertEqual(validate_dialogue(_available()), _available())
        self.assertEqual(
            validate_dialogue(_available(bond_stage=None))["bond_stage"], None
        )
        self.assertEqual(validate_dialogue(_available(choices=[]))["choices"], [])
        # The host's opaque catalog key rides the combat participant's wire
        # vocabulary and passes through unchanged: the validator gates, it
        # never normalizes the key the presenter emitted.
        keyed = _available(
            host={"identity": 41, "display_name": "公會職員", "portrait_ref": "42"}
        )
        self.assertEqual(validate_dialogue(keyed), keyed)

    def test_portrait_reference_bound_matches_the_combat_participant_bound(self):
        self.assertEqual(MAX_DIALOGUE_PORTRAIT_REF, MAX_PARTICIPANT_REF)
        at_bound = "1" * MAX_DIALOGUE_PORTRAIT_REF
        self.assertEqual(
            validate_dialogue(
                _available(
                    host={
                        "identity": 41,
                        "display_name": "公會職員",
                        "portrait_ref": at_bound,
                    }
                )
            )["host"]["portrait_ref"],
            at_bound,
        )

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_drift_rejects(self):
        bad_payloads = [
            # unknown top-level field
            _available(extra=1),
            # missing top-level field
            {k: v for k, v in _available().items() if k != "choices"},
            # schema drift
            _available(schema_version=1),
            _available(schema_version=2),
            # the unavailable form is the registry's, not the validator's
            dict(UNAVAILABLE_PAYLOAD),
            _available(available=False),
            _available(kind="party"),
            # host vocabulary drift (the combat participant portrait rule)
            _available(host={"identity": 1, "display_name": "a", "portrait_ref": 42}),
            _available(host={"identity": 1, "display_name": "a", "portrait_ref": "4a"}),
            _available(
                host={
                    "identity": 1,
                    "display_name": "a",
                    "portrait_ref": "1" * (MAX_DIALOGUE_PORTRAIT_REF + 1),
                }
            ),
            _available(host={"identity": 0, "display_name": "a", "portrait_ref": None}),
            _available(host={"identity": 1, "display_name": " ", "portrait_ref": None}),
            {
                **_available(),
                "host": {
                    "identity": 1,
                    "display_name": "同" * 129,
                    "portrait_ref": None,
                },
            },
            # numeric bond_stage (raw affinity can never reach the wire)
            _available(bond_stage=3),
            _available(bond_stage=""),
            # line bounds and surrogate rejection (server parity with the mirror)
            _available(line=""),
            _available(line="言" * (MAX_DIALOGUE_SESSION_LINE_CODE_POINTS + 1)),
            _available(line="\ud800壞"),
            # choice cap (one row over the panel-owned bound)
            _available(choices=[_choice(f"詞{i}") for i in range(DIALOGUE_MAX_CHOICES + 1)]),
            # duplicate keyword ids
            _available(choices=[_choice("公會"), _choice("公會")]),
            # empty keyword id
            _available(choices=[_choice(" ")]),
            # lone surrogate in the keyword id (mirror parity with the UMD)
            _available(choices=[{"keyword_id": "\ud800", "label": "公會"}]),
            # choice row key drift
            _available(choices=[{"keyword_id": "公會"}]),
            _available(choices=[{"keyword_id": "公會", "label": "公會", "extra": 1}]),
            # over-long label
            _available(choices=[{"keyword_id": "公會", "label": "說" * 129}]),
        ]
        for bad in bad_payloads:
            with self.subTest(payload=repr(sorted(bad))[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_dialogue(bad)

    def test_error_is_a_protocol_validation_error(self):
        self.assertTrue(issubclass(DialoguePanelError, ProtocolValidationError))

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_unlock_batch_is_this_panels_own_open_topics(self):
        """authored-dialogue-unread-notices: one watcher's wrapped batch."""
        locked = {
            **_choice("密談"),
            "availability": "locked",
            "requirement_hint": "需要信物",
        }
        choices = [_choice("公會"), _choice("任務"), locked]

        def batch(**overrides):
            value = {
                "batch_id": "a" * 32,
                "host_id": 41,
                "context_id": "ctx-1",
                "topic_ids": ["guild_staff.公會", "guild_staff.任務"],
            }
            value.update(overrides)
            return _available(choices=choices, unlock_batch=value)

        self.assertEqual(validate_dialogue(batch()), batch())
        for bad in (
            batch(batch_id=""),
            batch(batch_id="x" * 65),
            batch(batch_id="批次"),
            batch(host_id=42),
            batch(host_id=True),
            batch(context_id="ctx-2"),
            batch(topic_ids=[]),
            batch(topic_ids=["guild_staff.公會", "guild_staff.公會"]),
            batch(topic_ids=["guild_staff.密談"]),
            batch(topic_ids=["guild_staff.不存在"]),
            batch(topic_ids=["guild_staff.任務", "guild_staff.公會"]),
            batch(extra=1),
        ):
            with self.subTest(batch=repr(bad["unlock_batch"])[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_dialogue(bad)


class DialogueModeResolutionTests(BattlefieldIsolation, EvenniaTest):
    """The committed mode matrix: creation > combat > dialogue-live > exploration."""

    def setUp(self):
        super().setUp()
        self.player = _player("模式矩陣測試者")
        self.player.location = self.room1
        self.host = _host(self.room1, "職員")
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _mode(self):
        return PresentationCoordinator.mode_for(self.context)

    @covers_requirement(
        "webclient-dialogue-session::dialogue-mode-resolves-after-combat-and-before-exploration"
    )
    def test_matrix(self):
        self.assertEqual(self._mode(), "exploration")
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        self.assertEqual(self._mode(), "dialogue")
        clear_dialogue_session(self.player)
        self.assertEqual(self._mode(), "exploration")
        self.player.creation_pending = True
        try:
            open_or_refresh_dialogue(self.player, self.host, "歡迎。")
            self.assertEqual(self._mode(), "creation")
        finally:
            self.player.creation_pending = False

    def test_combat_outranks_a_live_session(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        engage(self.player, monster)
        # A session object re-saved while combat is active (the cleanup seam
        # lost a race): the committed mode is still combat, never dialogue.
        open_or_refresh_dialogue(self.player, self.host, "殘留台詞。")
        self.assertTrue(is_in_active_session(self.player))
        self.assertEqual(self._mode(), "combat")

    def test_stale_session_never_resolves_dialogue_mode(self):
        self.player.db.dialogue_session = {
            "npc_id": 9_999_999,
            "line": "幽靈台詞。",
            "updated_tick": None,
        }
        self.assertEqual(self._mode(), "exploration")


class DialogueWireTransitionTests(BattlefieldIsolation, EvenniaTest):
    """The settled record reaches the wire and the clear returns the mode."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        register_catalog()
        watchers.clear_watchers()
        self.player = _player("對話總線測試者")
        self.player.location = self.room1
        self.host = _host(self.room1, "職員")
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    def _coordinator(self):
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        return session, coordinator

    def test_scripted_talk_commits_dialogue_mode_atomically(self):
        session, coordinator = self._coordinator()
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        before = committed_view(session.sent)
        self.assertEqual(before["mode"], "exploration")
        self.assertEqual(before["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        # validate against the registered allowlist — the panel name must be known
        validate_ui_snapshot(
            recorded_frames(session.sent)[-1],
            known_panels=set(self.registry.panel_names),
        )

        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "d1",
            "base_revision": coordinator.revision,
            "action_id": "explore.talk_scripted",
            "payload": {"npc_id": int(self.host.pk), "topic_id": "guild_staff.topic_03", "context_id": None},
        }
        handle_ui_action(
            session, self.player, envelope, self.action_registry, self.registry
        )
        results = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ]
        self.assertEqual(results[-1]["outcome"], "success")
        # The completion publication commits the whole mode transition: the
        # client-visible view (baseline plus the completion delta) carries the
        # authored reply in dialogue mode.
        committed = committed_view(session.sent)
        self.assertEqual(committed["mode"], "dialogue")
        validate_ui_update(
            recorded_frames(session.sent)[-1],
            known_panels=set(self.registry.panel_names),
        )
        self.assertIs(committed["panels"]["dialogue"]["available"], True)
        self.assertIsNotNone(committed["panels"]["dialogue"]["delivery"])
        lines = [
            line["text"]
            for line in committed["panels"]["dialogue"]["delivery"]["lines"]
        ]
        self.assertTrue(
            any("冒險者公會" in text for text in lines),
            "the published delivery carries the authored reply: %r" % (lines,),
        )
        self.assertEqual(
            committed["panels"]["dialogue"]["choices"],
            _scripted_keyword_descriptors(
                self.host,
                actor=self.player,
                context_id=committed["panels"]["dialogue"]["context_id"],
            )[:DIALOGUE_MAX_CHOICES],
        )
        # End-to-end: the portrait reference the wire carries is a key of the
        # art catalog committed in the same envelope (design §8.2 — the client
        # looks the key up and never constructs one).
        self.assertIs(committed["panels"]["art"]["available"], True)
        self.assertIn(
            committed["panels"]["dialogue"]["host"]["portrait_ref"],
            committed["panels"]["art"]["portrait_catalog"],
        )
        # The exploration panel keeps shipping its ordinary available payload —
        # dialogue mode does not blank it (the talk's +1 affinity may flip
        # affordance availability, so payload equality is not the contract).
        self.assertIs(committed["panels"]["exploration"]["available"], True)
        self.assertEqual(
            set(committed["panels"]["exploration"]),
            set(before["panels"]["exploration"]),
        )

    def test_movement_clear_returns_mode_and_degrades_the_panel(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        opened = committed_view(session.sent)
        self.assertEqual(opened["mode"], "dialogue")

        away = create_object(Room, key="廣場", location=None)
        settle_movement(
            self.player,
            self.room1,
            traverse=lambda: self.player.move_to(away) or True,
            destination=away,
        )
        self.assertIsNone(self.player.db.dialogue_session)
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        cleared = committed_view(session.sent)
        self.assertEqual(cleared["mode"], "exploration")
        self.assertEqual(cleared["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        latest = last_frame(session, "ui_snapshot")
        self.assertEqual(latest["mode"], "exploration")
        self.assertEqual(latest["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)

    def test_engage_update_carries_the_dialogue_panel_under_combat_mode(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        coordinator.full_snapshot(PresentationContext(actor=self.player, protocol_version=1))
        monster = create_object(Monster, key="襲擊的哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "d2",
            "base_revision": coordinator.revision,
            "action_id": "explore.engage",
            "payload": {"monster_id": int(monster.pk)},
        }
        handle_ui_action(
            session, self.player, envelope, self.action_registry, self.registry
        )
        updates = [call["ui_update"][0][0] for call in session.sent if "ui_update" in call]
        self.assertTrue(updates, "engage must publish its affected-panel update")
        committed = updates[-1]
        self.assertEqual(committed["mode"], "combat")
        # The engage clear is reflected atomically: dialogue re-renders
        # unavailable inside the same update, never left stale-available.
        self.assertIn("dialogue", committed["panels"])
        self.assertEqual(committed["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)

    def test_engage_adapter_names_the_dialogue_panel(self):
        monster = create_object(Monster, key="測試哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            result["affected_panels"], ("status", "context_actions", "dialogue", "art", "item_holdings", "party_inventory")
        )
        spec = self.action_registry.spec("explore.engage")
        self.assertEqual(spec.affected_panels, ("status", "context_actions", "dialogue", "art", "item_holdings", "party_inventory"))

    def test_npc_departure_pushes_unavailable_dialogue_to_live_watchers(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        coordinator.full_snapshot(PresentationContext(actor=self.player, protocol_version=1))
        real = ServerSession()
        real.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        real.sessid = 941
        self.sessionhandler[real.sessid] = real
        real.protocol_key = "webclient/websocket"
        real.puppet = self.player
        self.player.sessions.add(real)
        recorded = []
        real.msg = lambda **kwargs: recorded.append(kwargs)
        live_coordinator = PresentationCoordinator(
            real, self.registry, calendar_provider=lambda: CALENDAR
        )
        real.ndb.elosern_coordinator = live_coordinator
        live_coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        watchers.register_watcher(real)

        away = create_object(Room, key="後巷", location=None)
        # The departure clear fans out through transaction.on_commit; the
        # capture seam executes what a committed move would deliver.
        with self.captureOnCommitCallbacks(execute=True):
            self.host.move_to(away)

        updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
        self.assertTrue(updates, "departure must push a dialogue panel update")
        self.assertIsNone(self.player.db.dialogue_session)
        self.assertEqual(updates[-1]["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        # The update carries the recomputed mode atomically with the clear.
        self.assertEqual(updates[-1]["mode"], "exploration")
        del self.sessionhandler[real.sessid]

    def test_departure_without_watchers_is_a_silent_no_op(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        away = create_object(Room, key="後巷二", location=None)
        with self.captureOnCommitCallbacks(execute=True):
            self.host.move_to(away)
        self.assertIsNone(self.player.db.dialogue_session)

    def test_dialogue_mode_update_compares_the_panel_for_unrelated_subsets(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        context = PresentationContext(actor=self.player, protocol_version=1)
        # Establish the committed baseline the delta builds on.
        coordinator.full_snapshot(context)
        baseline = committed_view(session.sent)
        session.sent.clear()
        # A publisher naming only unrelated panels (e.g. a clock-tick status
        # update) must never emit mode dialogue with a stale or missing panel:
        # the coordinator renders dialogue as a candidate of that publication
        # and compares it against the committed value.
        coordinator.panel_update(
            context,
            {
                "status": self.registry.build_unavailable(
                    "status", internal=True, correlation_id="b" * 32
                )
            },
        )
        envelope = last_frame(session, "ui_update")
        self.assertEqual(envelope["mode"], "dialogue")
        self.assertIn("status", envelope["panels"])
        # The committed dialogue panel is byte-identical, so the delta omits it
        # and the staged state stays consistent (a candidate, not a mandate).
        self.assertNotIn("dialogue", envelope["panels"])
        self.assertIs(baseline["panels"]["dialogue"]["available"], True)

    def test_non_dialogue_updates_do_not_widen_the_subset(self):
        session, coordinator = self._coordinator()
        context = PresentationContext(actor=self.player, protocol_version=1)
        coordinator.full_snapshot(context)
        session.sent.clear()
        coordinator.panel_update(
            context,
            {
                "status": self.registry.build_unavailable(
                    "status", internal=True, correlation_id="c" * 32
                )
            },
        )
        envelope = last_frame(session, "ui_update")
        self.assertEqual(envelope["mode"], "exploration")
        self.assertEqual(set(envelope["panels"]), {"status"})


class DialogueTextCommandSettlementTests(BattlefieldIsolation, EvenniaTest):
    """The ordinary ``talk`` text command commits dialogue presentation."""

    character_typeclass = PlayerCharacter

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        register_catalog()
        watchers.clear_watchers()
        self.player = _player("文字指令對話測試者")
        self.player.location = self.room1
        self.host = _host(self.room1, "公會職員")

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    def test_text_talk_publishes_dialogue_mode_with_the_available_panel(self):
        from server.conf import inputfuncs
        from server.conf.tests.test_inputfuncs import _make_session
        from web.webclient.presentation.coordinator import PresentationCoordinator
        from web.webclient.presentation.registry import build_production_registry

        session = _make_session(
            self.sessionhandler, "webclient/websocket", account=self.account
        )
        session.puppet = self.player
        self.player.sessions.add(session)
        coordinator = PresentationCoordinator(
            session, build_production_registry(), calendar_provider=lambda: CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        recorded: list[dict] = []
        session.msg = lambda **kwargs: recorded.append(kwargs)

        inputfuncs.text(session, f"talk {self.host.key} 註冊")

        self.assertTrue(
            recorded_frames(recorded), "the settled talk must refresh presentation"
        )
        # The post-command comparison refresh recomputes mode from canonical
        # state: the committed view (whatever baseline plus differences the
        # settlement published) carries the reply in dialogue mode.
        committed = committed_view(recorded)
        self.assertEqual(committed["mode"], "dialogue")
        self.assertIs(committed["panels"]["dialogue"]["available"], True)
        self.assertIsNotNone(committed["panels"]["dialogue"]["delivery"])
        delivery = committed["panels"]["dialogue"]["delivery"]
        # The keyword command committed the authored topic's scene: the reply
        # dialogue is the delivered exchange's final line, and the topic is one
        # the host's own affordance descriptors list for this context.
        scripted = _scripted_keyword_descriptors(
            self.host, actor=self.player, context_id=delivery["context_id"]
        )
        self.assertIn(
            delivery["topic_id"],
            {item["topic_id"] for item in scripted},
            "the settled keyword played one of the host's scripted topics",
        )
        self.assertEqual(delivery["lines"][-1]["speaker"], "host")


class DialogueAvailabilityPanelTests(BattlefieldIsolation, EvenniaTest):
    """Server-qualified disclosure reaches the panel and the action payload."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        # The affinity rulebook's cap breaks resolve their quest keys.
        register_catalog()
        self.scope = synthetic_registries(
            "races",
            "items",
            "dialogue",
            extra={"dialogue": {_PANEL_AVAILABILITY_KEY: _panel_availability_dialogue()}},
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)

        self.room = create_object(Room, key="合成可用性大廳")
        self.host = create_object(NPC, key="合成可用性職員", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_PANEL_AVAILABILITY_KEY)
        )
        self.player = create_object(PlayerCharacter, key="合成可用性面板者")
        self.player.race = _PANEL_RACE
        self.player.apply_race_baseline()
        self.player.db.inventory = []
        self.player.location = self.room
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _coordinator(self):
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        return session, coordinator

    def _open(self):
        open_or_refresh_dialogue(self.player, self.host, "合成招呼。")
        return live_dialogue_session(self.player)

    def _dispatch(self, session, payload, request_id="avail-1"):
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": session.ndb.elosern_coordinator.epoch,
            "request_id": request_id,
            "base_revision": session.ndb.elosern_coordinator.revision,
            "action_id": "explore.talk_scripted",
            "payload": payload,
        }
        handle_ui_action(
            session, self.player, envelope, self.action_registry, self.registry
        )
        results = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ]
        return results[-1]

    def _last_committed_panel(self, session):
        committed = committed_view(session.sent)
        return committed["panels"]["dialogue"]

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-3-presentation-panel"
    )
    def test_hidden_choice_is_absent_and_no_body_ships_before_selection(self):
        session, coordinator = self._coordinator()
        self._open()
        coordinator.full_snapshot(self.context)
        snapshot = committed_view(session.sent)
        panel = snapshot["panels"]["dialogue"]
        self.assertIs(panel["available"], True)

        self.assertEqual(
            [choice["topic_id"] for choice in panel["choices"]],
            [_PANEL_OPEN, _PANEL_LOCKED],
        )
        locked = panel["choices"][1]
        self.assertEqual(locked["availability"], "locked")
        self.assertIsInstance(locked["requirement_hint"], str)
        self.assertTrue(locked["requirement_hint"])
        self.assertEqual(
            set(locked["action_payload"]), {"npc_id", "topic_id", "context_id"}
        )
        self.assertEqual(locked["action_payload"]["topic_id"], _PANEL_LOCKED)
        # The whole committed snapshot — panel, exploration vocabulary and
        # every other panel — carries no scene body.
        self.assertEqual(_panel_body_sentinels(snapshot), [])
        validate_ui_snapshot(
            recorded_frames(session.sent)[-1],
            known_panels=set(self.registry.panel_names),
        )

    @covers_requirement(
        "authored-dialogue-selection::authored-selection-delivers-complete-scenes-atomically"
    )
    def test_locked_selection_plays_the_refusal_with_no_effects(self):
        session, _coordinator = self._coordinator()
        live = self._open()
        affinity_before = self.host.relations.affinity_for(self.player)

        result = self._dispatch(
            session,
            {
                "npc_id": int(self.host.pk),
                "topic_id": _PANEL_LOCKED,
                "context_id": live.context_id,
            },
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)
        delivery = self._last_committed_panel(session)["delivery"]
        self.assertEqual(delivery["kind"], "refusal")
        texts = [line["text"] for line in delivery["lines"]]
        self.assertIn(_PANEL_SENTINEL_REFUSAL, texts)
        self.assertNotIn(_PANEL_SENTINEL_LOCKED, texts)

    @covers_requirement(
        "exploration-affordances::affordance-params-are-validator-normalized"
    )
    def test_a_client_supplied_availability_flag_is_rejected(self):
        session, _coordinator = self._coordinator()
        live = self._open()
        result = self._dispatch(
            session,
            {
                "npc_id": int(self.host.pk),
                "topic_id": _PANEL_OPEN,
                "context_id": live.context_id,
                "availability": "open",
            },
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        self.assertEqual(
            live_dialogue_session(self.player).context_id, live.context_id
        )
        self.assertEqual(
            [call for call in session.sent if "ui_snapshot" in call],
            [],
            "a malformed payload must not publish or mutate presentation",
        )

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_stale_locked_choice_refuses_after_a_committed_change(self):
        session, coordinator = self._coordinator()
        self.player.db.inventory = [_PANEL_ITEM]
        live = self._open()
        coordinator.full_snapshot(self.context)
        listed = committed_view(session.sent)["panels"]["dialogue"]
        choice = next(
            item for item in listed["choices"] if item["topic_id"] == _PANEL_LOCKED
        )
        self.assertEqual(choice["availability"], "open")

        # Committed canonical change between projection and selection.
        self.player.db.inventory = []
        affinity_before = self.host.relations.affinity_for(self.player)
        result = self._dispatch(
            session,
            {
                "npc_id": int(self.host.pk),
                "topic_id": _PANEL_LOCKED,
                "context_id": live.context_id,
            },
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)
        delivery = self._last_committed_panel(session)["delivery"]
        self.assertEqual(delivery["kind"], "refusal")
        self.assertEqual(delivery["scene_id"], "t_panel_availability_locked_refusal")
        self.assertNotIn(
            _PANEL_SENTINEL_LOCKED, [line["text"] for line in delivery["lines"]]
        )



class DialoguePublicationBudgetTests(unittest.TestCase):
    """Canonical UTF-8 dialogue budgets and conditional 98304 envelope rules."""

    def _sample_dialogue_panel(self, delivery_lines=None):
        lines = delivery_lines or [
            {"kind": "speech", "speaker": "actor", "text": "公會"},
            {"kind": "speech", "speaker": "host", "text": "歡迎來到冒險者公會。"},
        ]
        return {
            "schema_version": 3,
            "available": True,
            "kind": "dialogue",
            "host": {"identity": 41, "display_name": "公會職員", "portrait_ref": None},
            "actor": {"identity": 1, "display_name": "測試者", "portrait_ref": None},
            "bond_stage": "熟人",
            "context_id": "ctx-1",
            "delivery": {
                "delivery_id": "deliv-1",
                "context_id": "ctx-1",
                "topic_id": "guild_staff.topic_01",
                "scene_id": "guild_staff.topic_01_scene",
                "scene_revision": "r1",
                "phase_revision": None,
                "kind": "formal",
                "lines": lines,
            },
            "choices": [
                {
                    "topic_id": "guild_staff.topic_01",
                    "keyword_id": "公會",
                    "label": "公會",
                    "availability": "open",
                    "requirement_hint": None,
                    "unread": False,
                    "predecessors": [],
                    "action_payload": {
                        "npc_id": 41,
                        "topic_id": "guild_staff.topic_01",
                        "context_id": "ctx-1",
                    },
                }
            ],
            "pure_chain": [],
            "reading_revision": 0,
            "completed_topic_ids": [],
            "unlock_batch": None,
        }

    def _envelope(self, panels, revision=1):
        return {
            "protocol_version": 1,
            "presentation_epoch": "e" * 22,
            "revision": revision,
            "mode": "dialogue",
            "panels": panels,
            "layout_version": 1,
            "server_time": {
                "year": 1204,
                "season_index": 2,
                "season_label": "仲夏",
                "day_in_season": 17,
                "hour": 14,
                "minute": 30,
                "second": 5,
            },
        }

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_dialogue_envelope_conditional_allowance_accepts_up_to_98304(self):
        cjk_lines = [
            {
                "kind": "speech",
                "speaker": "host" if i % 2 else "actor",
                "text": f"冒險者公會的大廳內聚集了來自各地的傭兵與行商，空氣中瀰漫著舊羊皮紙與麥酒的香氣。（行次{i}）" * 3,
            }
            for i in range(16)
        ]
        dialogue = self._sample_dialogue_panel(delivery_lines=cjk_lines)
        self.assertLessEqual(json_byte_size(dialogue), DIALOGUE_PANEL_MAX_BYTES)

        padding = {f"pad_{i}": "文字內容測試" * 90 for i in range(36)}
        status = {
            "schema_version": 4,
            "available": True,
            "name": "影行者",
            "identity": "42",
            "resources": {"hp": {"current": 80, "maximum": 100}, "mp": {"current": 30, "maximum": 50}, "sp": {"current": 12, "maximum": 40}},
            "conditions": [],
            "fatigue": [],
            "disguise_active": False,
            "combat": None,
            **padding,
        }
        envelope = self._envelope({"dialogue": dialogue, "status": status})
        size = json_byte_size(envelope)
        stripped = {**envelope, "panels": {"status": status}}
        stripped_size = json_byte_size(stripped)

        self.assertGreater(size, MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(size, DIALOGUE_ENVELOPE_MAX_BYTES)
        self.assertLessEqual(stripped_size, MAX_CANONICAL_JSON_BYTES)

        check_envelope(envelope)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_dialogue_envelope_exceeding_98304_rejected(self):
        dialogue = self._sample_dialogue_panel()
        padding = {f"pad_{i}": "超限字串填充內容" * 100 for i in range(45)}
        status = {"schema_version": 4, "available": True, "name": "影行者", **padding}
        envelope = self._envelope({"dialogue": dialogue, "status": status})
        self.assertGreater(json_byte_size(envelope), DIALOGUE_ENVELOPE_MAX_BYTES)
        with self.assertRaises(JSONSafetyError):
            check_envelope(envelope)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_dialogue_panel_exceeding_24576_rejected(self):
        heavy_lines = [
            {"kind": "speech", "speaker": "host", "text": "超限文本內容段落" * 50}
            for _ in range(20)
        ]
        oversized_dialogue = self._sample_dialogue_panel(delivery_lines=heavy_lines)
        self.assertGreater(json_byte_size(oversized_dialogue), DIALOGUE_PANEL_MAX_BYTES)
        envelope = self._envelope({"dialogue": oversized_dialogue})
        with self.assertRaises(JSONSafetyError):
            check_envelope(envelope)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_dialogue_removed_envelope_exceeding_65536_rejected(self):
        dialogue = self._sample_dialogue_panel()
        padding = {f"pad_{i}": "側面板填充文本" * 100 for i in range(35)}
        status = {"schema_version": 4, "available": True, "name": "影行者", **padding}
        envelope = self._envelope({"dialogue": dialogue, "status": status})
        stripped = {**envelope, "panels": {"status": status}}
        self.assertGreater(json_byte_size(stripped), MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(json_byte_size(envelope), DIALOGUE_ENVELOPE_MAX_BYTES)
        with self.assertRaises(JSONSafetyError):
            check_envelope(envelope)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_unrelated_envelope_keeps_65536_bound(self):
        padding = {f"pad_{i}": "非對話信封填充" * 100 for i in range(35)}
        status = {"schema_version": 4, "available": True, "name": "影行者", **padding}
        envelope = self._envelope({"status": status})
        self.assertGreater(json_byte_size(envelope), MAX_CANONICAL_JSON_BYTES)
        with self.assertRaises(JSONSafetyError):
            check_envelope(envelope)

    @covers_requirement("webclient-oob-protocol::elosern-oob-messages-use-exact-versioned-envelopes")
    def test_python_node_protocol_store_parity(self):
        cjk_lines = [
            {
                "kind": "speech",
                "speaker": "host" if i % 2 else "actor",
                "text": f"冒險者公會的大廳內聚集了來自各地的傭兵與行商，空氣中瀰漫著舊羊皮紙與麥酒的香氣。（行次{i}）" * 2,
            }
            for i in range(12)
        ]
        dialogue = self._sample_dialogue_panel(delivery_lines=cjk_lines)
        padding = {f"pad_{i}": "文字內容測試" * 80 for i in range(25)}
        status = {"schema_version": 4, "available": True, "name": "影行者", **padding}
        valid_envelope = self._envelope({"dialogue": dialogue, "status": status})

        over_padding = {f"pad_{i}": "超限字串填充內容" * 100 for i in range(45)}
        over_98k = self._envelope({"dialogue": dialogue, "status": {"schema_version": 4, "available": True, **over_padding}})

        heavy_lines = [{"kind": "speech", "speaker": "host", "text": "超限文本內容段落" * 50} for _ in range(20)]
        over_panel = self._envelope({"dialogue": self._sample_dialogue_panel(delivery_lines=heavy_lines)})

        stripped_padding = {f"pad_{i}": "側面板填充文本" * 100 for i in range(35)}
        over_stripped = self._envelope({"dialogue": dialogue, "status": {"schema_version": 4, "available": True, **stripped_padding}})

        normal_env = self._envelope({"status": {"schema_version": 4, "available": True, "name": "影行者"}})

        frames = [valid_envelope, over_98k, over_panel, over_stripped, normal_env]

        py_results = []
        for f in frames:
            try:
                check_envelope(f)
                py_results.append(True)
            except Exception:
                py_results.append(False)

        worktree_root = Path(__file__).resolve().parents[4]
        script = """
const fs = require('node:fs');
const P = require('./web/static/webclient/js/elosern/protocol.js');
const frames = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = frames.map(frame => {
    try {
        P.checkEnvelope(frame);
        return true;
    } catch (e) {
        return false;
    }
});
process.stdout.write(JSON.stringify(results));
"""
        proc = subprocess.run(
            ["node", "-e", script],
            input=json.dumps(frames, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=str(worktree_root),
            check=True,
        )
        node_results = json.loads(proc.stdout)

        self.assertEqual(py_results, [True, False, False, False, True])
        self.assertEqual(node_results, py_results, "Python and Node check_envelope decisions must match with 100% parity")


if __name__ == "__main__":
    unittest.main()
