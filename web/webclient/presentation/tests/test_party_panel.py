"""Tests for the version-2 ``party`` presentation panel.

Presenter shape (party-list order, exact row vocabulary, canonical bond-stage
names only, true-trait HP), empty-party availability, stale-dbid omission,
unavailable forms, read-only rendering, the pure validator's drift rejections,
the connected leave/purge push seams, and the identity-join contract against
the combat participant rows. ``covers_requirement`` annotations for the new
``webclient-party-panel`` IDs landed at the change's archive/sync commit (the
checker resolves IDs only from ``openspec/specs/``).
"""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from django.test import override_settings
from PIL import Image
from tools.spec_traceability import covers_requirement

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.combat_actions import (
    AFFECTED_PANELS,
    _command_adapter,
    _exit_confirm_adapter,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
    validate_ui_snapshot,
)
from web.webclient.presentation.party import (
    PARTY_GENERAL_LIMIT,
    PARTY_MAX_ROWS,
    PARTY_MAX_SLOTS,
    PARTY_SCHEMA_VERSION,
    MAX_PARTY_COMMISSION_LABEL,
    validate_party,
)
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.registry import build_production_registry
from world.quests.catalog import register_catalog
from world.art import official, official_refs
from world.art.gallery import (
    GalleryRecord,
    append_card,
    official_preferences_for,
    record_for,
    set_official_selection,
)
from world.art.official import current_catalog, load_catalog, reset_catalog
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.presenter import (
    ORIGIN_OFFICIAL,
    ORIGIN_PLACEHOLDER,
    ORIGIN_RUNTIME,
    ORIGIN_SILHOUETTE,
)
from world.art.queue import claim, ensure, record_key, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import character_subject_for
from world.rules.action import stored_gauge_pair
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import get_config
from world.rules.art_view import portrait_catalog_key
from world.rules.combat_session import engage, read_session
from world.rules.npc_identity import npc_display_name
from world.rules.party import join_party, leave_party
from world.rules.unlock_notices import MemberUnlocks, unlock_flags
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

UNAVAILABLE_PAYLOAD = {
    "schema_version": PARTY_SCHEMA_VERSION,
    "available": False,
    "reason": {"code": "party_unavailable", "message": "隊伍資訊目前無法顯示"},
}


def _player(key="隊伍測試者"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _companion(key, room, hp_current=100, hp_maximum=100):
    npc = create_object(NPC, key=key, location=room)
    npc.race = "human"
    npc.apply_race_baseline()
    npc.traits.hp.base = hp_maximum
    npc.traits.hp.current = hp_current
    npc.traits.agility.base = 10
    return npc


def _monster(key="哥布林測試", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


def _commander(**overrides):
    row = {
        "identity": 7,
        "display_name": "隊伍測試者",
        "portrait_ref": None,
        "hp_current": 100,
        "hp_maximum": 120,
        "mp_current": 30,
        "mp_maximum": 50,
        "sp_current": 12,
        "sp_maximum": 40,
        "role": "commander",
        "knocked_out": False,
        "unread": False,
        "bond_stage": None,
        "membership": None,
    }
    row.update(overrides)
    return row


def _slot(**overrides):
    row = {
        "identity": 41,
        "display_name": "守衛長薇拉",
        "portrait_ref": None,
        "hp_current": 180,
        "hp_maximum": 220,
        "mp_current": 60,
        "mp_maximum": 80,
        "sp_current": 24,
        "sp_maximum": 40,
        "role": "companion",
        "knocked_out": False,
        "unread": False,
        "bond_stage": "摯友",
        "membership": {"general": True, "temporary_commissions": []},
    }
    row.update(overrides)
    return row


class _RecordingSession:
    """Minimal session stand-in that records every transport send."""

    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 901

    def msg(self, **kwargs):
        self.sent.append(kwargs)


_CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


# The synthetic preset key and named-portrait stable key this module's
# official-art fixture admits: file-local identities, exactly like
# ``world/art/tests/test_gallery_match.py``, so no shipped preset, item, or
# artwork name ever appears in a behavior test.
_PRESET_KEY = "t_synth_preset"
_COMPANION_KEY = "t_synth_companion"
# One bound equipment item key for the precedence control; the chain compares
# stored strings, so the identity only has to be a non-empty item key.
_BOUND_ITEM = "t_synth_coat"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG: the official catalog reads the header only."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class _OfficialArt:
    """A synthetic official root beside an isolated runtime store.

    ``mount`` writes one admitted ``preset/<key>/`` image (a decodable PNG the
    catalog header-decodes) and reloads the snapshot; ``set_manifest`` updates
    that content folder's manifest and reloads. ``tree`` digests every file
    under BOTH artwork roots so a render that rewrote bytes in place cannot
    pass a read-only assertion.
    """

    def __init__(self, tempdir: Path) -> None:
        self.root = tempdir / "official"
        self.store = tempdir / "store"
        self.store.mkdir()

    @property
    def content(self) -> Path:
        return self.root / "preset" / _PRESET_KEY

    def mount(self, name="hero.png") -> str:
        """Write one admitted image and reload the catalog snapshot."""
        self.content.mkdir(parents=True, exist_ok=True)
        (self.content / name).write_bytes(_png())
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def set_manifest(self, **manifest) -> None:
        """Replace the content folder's manifest and reload the snapshot."""
        (self.content / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        load_catalog()

    def url(self, identity: str) -> str:
        """The snapshot's own same-origin URL for an admitted identity."""
        return current_catalog().url_for(identity)

    def write_store_file(self, identity: str, data=b"synthetic image") -> None:
        """Place one runtime file under the isolated store root."""
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def tree(self) -> dict[str, str]:
        """Every file under both artwork roots, by path and content digest."""
        digests: dict[str, str] = {}
        for root in (self.root, self.store):
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    digests[path.relative_to(root.parent).as_posix()] = (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                    )
        return digests


@contextmanager
def _official_art_scope():
    """Isolate both artwork roots and admit one synthetic preset key.

    Mirrors the harness in ``world/art/tests/test_gallery_match.py``: the
    runtime store and the official root are temp directories, the synthetic
    preset key is the only registered one for both the provenance resolver and
    the catalog's admission check, and the restart-scoped snapshot plus the
    bounded-diagnostic dedupe set are reset on exit so nothing leaks between
    tests.
    """
    with ExitStack() as stack:
        tempdir = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        art = _OfficialArt(tempdir)
        stack.enter_context(
            override_settings(
                ART_OFFICIAL_ROOT=str(art.root),
                ART_STORE_ROOT=str(art.store),
            )
        )
        stack.enter_context(
            patch.object(
                official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
            )
        )
        stack.enter_context(
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY}),
            )
        )
        official_refs._reported_unresolved.clear()
        stack.callback(official_refs._reported_unresolved.clear)
        reset_catalog()
        stack.callback(reset_catalog)
        yield art


# The render-phase tripwires the read-only acceptance forbids: every creating
# gallery read, record/card/preference write, generation enqueue and official
# catalog reload or filesystem walk a presentation could attempt. Each is
# patched to raise AND asserted never called, because the presentation
# registry isolates a presenter exception into an unavailable payload — a
# raise alone could hide inside a swallowed panel failure.
_RENDER_TRIPWIRES = (
    ("creating gallery read", "world.art.gallery._create_record"),
    ("card write", "world.art.gallery.append_card"),
    ("card delete", "world.art.gallery.remove_card"),
    ("default write", "world.art.gallery.set_default"),
    ("selection write", "world.art.gallery.set_official_selection"),
    ("selection clear", "world.art.gallery.clear_official_selection"),
    ("geometry write", "world.art.gallery.set_official_geometry"),
    ("geometry clear", "world.art.gallery.clear_official_geometry"),
    ("gallery enqueue", "world.art.queue.enqueue_gallery_job"),
    ("gallery request", "world.art.service.request_gallery_image"),
    ("official re-walk", "world.art.official.open_dir_fd"),
    ("official re-load", "world.art.official.load_catalog"),
)


class PartyPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="隊伍大廳")
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("party", self.context)

    def _panels(self):
        """One production coordinator snapshot carrying both party and art."""
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        return coordinator.full_snapshot(self.context)["panels"]

    def _official_companion(self, key="測試官方隊友"):
        """A present, joined, preset-born companion with a named portrait."""
        npc = _companion(key, self.room)
        npc.db.portrait_policy = {"mode": "named", "stable_key": _COMPANION_KEY}
        npc.db.age = npc.db.apparent_age = 30
        npc.db.creation_preset_key = _PRESET_KEY
        join_party(npc, self.player)
        return npc

    def _slot_and_entry(self, panels, npc):
        """The companion's party row and its same-snapshot catalog entry.

        Establishes the acceptance join in one place: the emitted
        ``portrait_ref`` IS the opaque catalog key of the co-located companion
        in the art panel built from the same snapshot.
        """
        key = portrait_catalog_key(npc.pk)
        slots = panels["party"]["slots"]
        # Row 0 is the commander's own row; the companion follows in party order.
        self.assertEqual(
            [slot["identity"] for slot in slots],
            [int(self.player.pk), int(npc.pk)],
        )
        companion_slot = slots[1]
        self.assertIn(key, panels["art"]["portrait_catalog"])
        # The catalog value is exactly {artwork, context}: the row and the art
        # panel agree on one complete canonical descriptor.
        entry = panels["art"]["portrait_catalog"][key]
        self.assertEqual(set(entry), {"artwork", "context"})
        return companion_slot, entry["artwork"]

    @staticmethod
    def _candidate(artwork):
        """The presented real candidate's resource, or None for a row with none."""
        for attempt in artwork["attempts"]:
            if attempt["type"] == "image":
                return attempt["resource"]
        return None

    def _read_only_render_case(
        self, art, subject, companion, expected_url, expected_origin
    ):
        """Render three snapshots under every tripwire and prove nothing moved.

        A registry-isolated presenter failure would be swallowed into an
        unavailable panel, so the tripwires are asserted never called directly
        AND the repeated snapshots are asserted to carry the resolved
        portrait: the render phase provably ran and provably stayed read-only.
        Both gallery-record read bindings are spied on — the chain module
        imports its own alias, and a creating read consolidates records rather
        than only creating one — so a creating read can never hide behind a
        record that already exists.
        """
        tripwires: dict[str, object] = {}
        with ExitStack() as stack:
            for label, target in _RENDER_TRIPWIRES:
                tripwires[label] = stack.enter_context(
                    patch(target, side_effect=AssertionError(label))
                )
            reads = [
                stack.enter_context(patch(target, wraps=record_for))
                for target in (
                    "world.art.gallery.record_for",
                    "world.art.gallery_match.record_for",
                )
            ]
            before = self._presentation_state(art, subject, companion)
            panels = [self._panels() for _ in range(3)]
            after = self._presentation_state(art, subject, companion)

        for label, tripwire in tripwires.items():
            self.assertFalse(tripwire.called, f"render attempted a {label}")
        self.assertTrue(any(spy.called for spy in reads), "no gallery read happened")
        for spy in reads:
            for call in spy.call_args_list:
                self.assertFalse(call.kwargs.get("create", False), call)
        for snapshot in panels:
            slot, artwork = self._slot_and_entry(snapshot, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertIsNotNone(resource)
            self.assertEqual(resource["origin"], expected_origin)
            self.assertEqual(resource["url"], expected_url)
        self.assertEqual(before, after)

    def _presentation_state(self, art, subject, companion):
        """Gallery records, asset/queue rows, attributes and both trees."""
        record = record_for(subject, create=False)
        return {
            "gallery_keys": sorted(GalleryRecord.objects.values_list("db_key", flat=True)),
            "gallery_cards": deepcopy(record.db.cards) if record is not None else None,
            "gallery_default": record.db.default_image_id if record is not None else None,
            "gallery_selection": (
                record.db.official_selection if record is not None else None
            ),
            "assets": sorted(
                (
                    asset.db_key,
                    asset.db.status,
                    asset.db.output_identity or "",
                    asset.db.prior_output_identity or "",
                )
                for asset in ArtAssetRecord.objects.all()
            ),
            "attributes": [
                (attribute.key, deepcopy(attribute.value))
                for attribute in sorted(
                    companion.attributes.all(), key=lambda attribute: attribute.key
                )
            ],
            "trees": art.tree(),
        }

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_default_gallery_ref_resolves_in_same_snapshot_and_reads_only(self):
        first = _companion("測試同行甲", self.room)
        second = _companion("測試同行乙", self.room)
        for npc in (first, second):
            join_party(npc, self.player)
        first.db.portrait_policy = {"mode": "named", "stable_key": "t_party_portrait"}
        first.db.age = first.db.apparent_age = 30
        subject = character_subject_for(first)
        image_id = "aaaaaaaa-1111-4111-8111-111111111111"
        identity = f"gallery/character/{subject.key}/{image_id}.png"
        with tempfile.TemporaryDirectory() as root, override_settings(ART_STORE_ROOT=root):
            target = Path(root) / identity
            target.parent.mkdir(parents=True)
            target.write_bytes(b"synthetic image")
            append_card(
                subject, image_id=image_id, stored_identity=identity, prompt=None,
                seed=None, checkpoint=None, requested_fields=[], binding=None,
                source="seed", created_at=100, image_size={"width": 768, "height": 1024},
            )
            record = record_for(subject, create=False)
            before = deepcopy(record.db.cards)
            rows = self._render()["slots"]
            # Row 0 is the commander's own row; the companions follow.
            self.assertEqual(rows[1]["portrait_ref"], str(first.pk))
            # The other co-located companion is ADMITTED too (a live party
            # member present in the room), so its reference is non-null even
            # though it has no named policy and no real image at all: the
            # reference names its complete descriptor, not a real portrait.
            self.assertEqual(rows[2]["portrait_ref"], str(second.pk))
            catalog = self.registry.render("art", self.context)["portrait_catalog"]
            self.assertEqual(
                catalog[rows[1]["portrait_ref"]]["artwork"]["attempts"][0]["resource"]["url"],
                f"/art/{identity}",
            )
            self.assertEqual(
                catalog[rows[2]["portrait_ref"]]["artwork"]["attempts"], []
            )
            self.assertEqual(record.db.cards, before)
            # Membership never depends on the imagery: a default naming no card
            # the record holds, an empty record, or no record at all each leave
            # the reference standing while the descriptor truthfully carries no
            # real candidate (silhouette artwork is decorative, never the
            # payload's own image).
            record.db.default_image_id = "bbbbbbbb-2222-4222-8222-222222222222"
            self.assertEqual(self._render()["slots"][1]["portrait_ref"], str(first.pk))
            record.db.default_image_id = None
            self.assertEqual(self._render()["slots"][1]["portrait_ref"], str(first.pk))
            record.delete()
            self.assertEqual(self._render()["slots"][1]["portrait_ref"], str(first.pk))
            self.assertIsNone(record_for(subject, create=False))
            catalog = self.registry.render("art", self.context)["portrait_catalog"]
            self.assertEqual(
                [
                    attempt["type"]
                    for attempt in catalog[str(first.pk)]["artwork"]["attempts"]
                ],
                [],
            )

    def test_possessed_companion_keeps_owner_order_and_owner_bond_stages(self):
        first = _companion("測試同行甲", self.room)
        second = _companion("測試同行乙", self.room)
        for npc in (first, second):
            join_party(npc, self.player)
        apply_affinity_change(first, self.player, AffinitySource.QUEST_COMPLETION, 47)
        expected = self._render()
        possessed = PresentationContext(actor=second, protocol_version=1)
        self.assertEqual(self.registry.render("party", possessed), expected)
        self.assertNotEqual(first.relations.stage_for(self.player).name, first.relations.stage_for(second).name)

    def test_named_commander_portrait_is_possession_identical(self):
        # The exploration art view excludes its own actor, so a named commander
        # is absent from her own view but present in a possessed companion's
        # view of the room. Row 0 must still resolve identically: it is judged
        # by a view built for the commander, never by the puppet's.
        self.player.db.portrait_policy = {"mode": "named", "stable_key": _COMPANION_KEY}
        companion = _companion("測試同行甲", self.room)
        join_party(companion, self.player)

        expected = self._render()
        self.assertIsNone(expected["slots"][0]["portrait_ref"])
        possessed = PresentationContext(actor=companion, protocol_version=1)
        self.assertEqual(self.registry.render("party", possessed), expected)

    def test_possessed_stranger_or_stale_owner_is_unavailable_not_empty(self):
        npc = _companion("測試陌客", self.room)
        context = PresentationContext(actor=npc, protocol_version=1)
        for owner in (None, 999_999, "broken"):
            npc.db.party_member = owner
            self.assertEqual(self.registry.render("party", context), UNAVAILABLE_PAYLOAD)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_two_companion_rows_follow_party_order_and_exact_vocabulary(self):
        first = _companion("薇拉", self.room, hp_current=60, hp_maximum=120)
        second = _companion("米雅", self.room, hp_current=44, hp_maximum=44)
        join_party(first, self.player)
        join_party(second, self.player)
        outcome = apply_affinity_change(
            first, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        self.assertTrue(outcome.applied)
        affinity_value = first.relations.affinity_for(self.player)

        payload = self._render()
        self.assertEqual(payload["schema_version"], PARTY_SCHEMA_VERSION)
        self.assertIs(payload["available"], True)
        self.assertEqual(
            [row["identity"] for row in payload["slots"]],
            [int(self.player.pk), int(first.pk), int(second.pk)],
        )
        self.assertEqual(payload["viewed_member_id"], int(self.player.pk))
        self.assertEqual(
            payload["slots"][0],
            {
                "identity": int(self.player.pk),
                "display_name": npc_display_name(self.player)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                # The exploration art view excludes ordinary player actors, so
                # the commander's own row carries the truthful null.
                "portrait_ref": None,
                "hp_current": stored_gauge_pair(self.player, "hp")[0],
                "hp_maximum": stored_gauge_pair(self.player, "hp")[1],
                "mp_current": stored_gauge_pair(self.player, "mp")[0],
                "mp_maximum": stored_gauge_pair(self.player, "mp")[1],
                "sp_current": stored_gauge_pair(self.player, "sp")[0],
                "sp_maximum": stored_gauge_pair(self.player, "sp")[1],
                "role": "commander",
                "knocked_out": False,
                "unread": False,
                "bond_stage": None,
                "membership": None,
            },
        )
        self.assertEqual(
            payload["slots"][1],
            {
                "identity": int(first.pk),
                "display_name": npc_display_name(first)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                # Both companions are present and joined, so both are admitted
                # to the bounded art view and carry their own catalog key even
                # though neither has real artwork yet.
                "portrait_ref": str(first.pk),
                "hp_current": 60,
                "hp_maximum": 120,
                "mp_current": stored_gauge_pair(first, "mp")[0],
                "mp_maximum": stored_gauge_pair(first, "mp")[1],
                "sp_current": stored_gauge_pair(first, "sp")[0],
                "sp_maximum": stored_gauge_pair(first, "sp")[1],
                "role": "companion",
                "knocked_out": False,
                "unread": False,
                "bond_stage": get_config().stage_for_value(affinity_value).name,
                "membership": {"general": True, "temporary_commissions": []},
            },
        )
        self.assertEqual(
            payload["general_quota"], {"used": 2, "limit": PARTY_GENERAL_LIMIT}
        )
        self.assertEqual(
            payload["slots"][2]["bond_stage"],
            get_config().stage_for_value(0).name,
        )
        # The raw affinity number never ships: the row key set is exact and no
        # numeric field carries the stored value.
        for row in payload["slots"]:
            self.assertEqual(
                set(row),
                {
                    "identity",
                    "display_name",
                    "portrait_ref",
                    "hp_current",
                    "hp_maximum",
                    "mp_current",
                    "mp_maximum",
                    "sp_current",
                    "sp_maximum",
                    "role",
                    "knocked_out",
                    "unread",
                    "bond_stage",
                    "membership",
                },
            )
            self.assertNotEqual(row["hp_current"], affinity_value)
            self.assertNotEqual(row["hp_maximum"], affinity_value)
            self.assertNotIn(affinity_value, row.values())

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_gauge_fields_come_from_the_true_traits_under_disguise(self):
        companion = _companion("卡恩", self.room, hp_current=60, hp_maximum=120)
        companion.traits.mp.current = 20
        companion.traits.mp.base = 40
        companion.traits.sp.current = 5
        companion.traits.sp.base = 30
        companion.db.disguised_stats = {"hp": 1, "mp": 0, "sp": 0}
        join_party(companion, self.player)

        row = self._render()["slots"][1]
        self.assertEqual((row["hp_current"], row["hp_maximum"]), (60, 120))
        self.assertEqual((row["mp_current"], row["mp_maximum"]), (20, 40))
        self.assertEqual((row["sp_current"], row["sp_maximum"]), (5, 30))

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_fractional_stored_hp_stays_alive_above_the_floor(self):
        # The knockout predicate compares the unrounded stored value (exactly
        # as the combat rules do), while the presented gauge truncates to an
        # integer: 1.4 HP reads as 1 HP and is still alive.
        companion = _companion("卡恩", self.room)
        # The trait setter stores integers, so write the fractional stored
        # value the predicate is specified against directly.
        companion.traits.hp._data["current"] = 1.4
        join_party(companion, self.player)
        row = self._render()["slots"][1]
        self.assertEqual(row["hp_current"], 1)
        self.assertIs(row["knocked_out"], False)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_knocked_out_and_unread_flags_are_truthful(self):
        kahn = _companion("卡恩", self.room, hp_current=1, hp_maximum=120)
        aila = _companion("艾拉", self.room)
        other = _companion("米雅", self.room)
        for npc in (kahn, aila, other):
            join_party(npc, self.player)
        session = _RecordingSession(self.player)
        session.ndb.party_unlocks = {
            int(aila.pk): MemberUnlocks(True, frozenset({"group_heal"})),
        }
        context = PresentationContext(
            actor=self.player,
            protocol_version=1,
            unlocks=unlock_flags(session),
        )

        rows = {
            row["identity"]: row
            for row in self.registry.render("party", context)["slots"]
        }
        self.assertIs(rows[int(kahn.pk)]["knocked_out"], True)
        self.assertIs(rows[int(aila.pk)]["knocked_out"], False)
        self.assertIs(rows[int(aila.pk)]["unread"], True)
        self.assertIs(rows[int(other.pk)]["unread"], False)
        # The commander's own row carries the session dot too, and is never
        # knocked out by the companion predicate.
        self.assertIs(rows[int(self.player.pk)]["unread"], False)
        self.assertIs(rows[int(self.player.pk)]["knocked_out"], False)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_viewed_member_falls_back_to_the_commander_after_leave_or_delete(self):
        first = _companion("薇拉", self.room)
        second = _companion("米雅", self.room)
        for npc in (first, second):
            join_party(npc, self.player)
        selection = PartyViewSelection(int(self.player.pk), int(first.pk), "member")
        context = PresentationContext(
            actor=self.player, protocol_version=1, party_view=selection
        )
        self.assertEqual(
            self.registry.render("party", context)["viewed_member_id"],
            int(first.pk),
        )

        leave_party(first, self.player, "dismissed")
        self.assertEqual(
            self.registry.render("party", context)["viewed_member_id"],
            int(self.player.pk),
        )

        deleted_selection = PartyViewSelection(
            int(self.player.pk), int(second.pk), "status"
        )
        deleted_context = PresentationContext(
            actor=self.player, protocol_version=1, party_view=deleted_selection
        )
        second.delete()
        self.assertEqual(
            self.registry.render("party", deleted_context)["viewed_member_id"],
            int(self.player.pk),
        )

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_possession_keeps_the_viewed_member_selection(self):
        first = _companion("薇拉", self.room)
        second = _companion("米雅", self.room)
        for npc in (first, second):
            join_party(npc, self.player)
        selection = PartyViewSelection(int(self.player.pk), int(first.pk), "member")
        possessed = PresentationContext(
            actor=second, protocol_version=1, party_view=selection
        )
        self.assertEqual(
            self.registry.render("party", possessed)["viewed_member_id"],
            int(first.pk),
        )

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_empty_party_is_available_with_only_the_commander_row(self):
        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(
            [row["identity"] for row in payload["slots"]], [int(self.player.pk)]
        )
        self.assertEqual(payload["slots"][0]["role"], "commander")
        self.assertEqual(payload["viewed_member_id"], int(self.player.pk))
        self.assertNotIn("reason", payload)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_stale_membership_dbid_is_omitted_without_error(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        self.player.db.party = [int(companion.pk), 999_999]
        payload = self._render()
        self.assertEqual(
            [row["identity"] for row in payload["slots"]],
            [int(self.player.pk), int(companion.pk)],
        )
        validate_party(payload)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_creation_pending_puppet_sees_the_shared_unavailable_form(self):
        self.player.creation_pending = True
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_no_location_puppet_sees_the_shared_unavailable_form(self):
        self.player.location = None
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_full_general_party_renders_and_presenting_twice_is_read_only(self):
        companions = [
            _companion(f"同伴{index}", self.room) for index in range(PARTY_GENERAL_LIMIT)
        ]
        for companion in companions:
            join_party(companion, self.player)
        witness = companions[0]
        apply_affinity_change(
            witness, self.player, AffinitySource.QUEST_COMPLETION, 12
        )
        before = {
            "party": deepcopy(self.player.db.party),
            "relations": deepcopy(witness.db.relations_data),
            "traits": deepcopy(dict(witness.traits.trait_data)),
        }

        first = self._render()
        second = self._render()

        # The commander row plus every general companion.
        self.assertEqual(len(first["slots"]), PARTY_GENERAL_LIMIT + 1)
        self.assertEqual(
            first["general_quota"], {"used": PARTY_GENERAL_LIMIT, "limit": PARTY_GENERAL_LIMIT}
        )
        self.assertEqual(first, second)
        self.assertEqual(self.player.db.party, before["party"])
        self.assertEqual(witness.db.relations_data, before["relations"])
        self.assertEqual(dict(witness.traits.trait_data), before["traits"])

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_official_selection_presents_without_runtime_cards(self):
        with _official_art_scope() as art:
            art.mount("default.png")
            selected = art.mount("selected.png")
            art.set_manifest(default="default.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            set_official_selection(subject, selected)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_OFFICIAL)
            self.assertEqual(resource["url"], art.url(selected))
            self.assertEqual(
                resource["url"],
                "/art/official/"
                f"{current_catalog().fingerprint_for(selected)}/{selected}",
            )
            # The selection's own branch owns the payload: the mounted
            # directory default is a different, non-selected image and the
            # record stays card-less with no runtime default.
            record = record_for(subject, create=False)
            self.assertIsNotNone(record)
            self.assertEqual(record.db.cards, [])
            self.assertIsNone(record.db.default_image_id)
            self.assertEqual(official_preferences_for(subject).selection, selected)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_mounted_official_default_presents_without_a_gallery_record(self):
        with _official_art_scope() as art:
            identity = art.mount("hero.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            self.assertIsNone(record_for(subject, create=False))

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_OFFICIAL)
            self.assertEqual(resource["url"], art.url(identity))
            self.assertEqual(
                resource["url"],
                "/art/official/"
                f"{current_catalog().fingerprint_for(identity)}/{identity}",
            )
            # Presenting the mounted default creates nothing: the gallery
            # record is still absent after both panels rendered.
            self.assertIsNone(record_for(subject, create=False))

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_equipment_bound_runtime_card_outranks_the_official_selection(self):
        with _official_art_scope() as art:
            art.mount("default.png")
            selected = art.mount("selected.png")
            art.set_manifest(default="default.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            image_id = "aaaaaaaa-1111-4111-8111-111111111111"
            bound_identity = f"gallery/character/{_COMPANION_KEY}/{image_id}.png"
            art.write_store_file(bound_identity)
            append_card(
                subject,
                image_id=image_id,
                stored_identity=bound_identity,
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding={"mask": ["armor"], "snapshot": {"armor": _BOUND_ITEM}},
                source="seed",
                created_at=100,
                image_size={"width": 768, "height": 1024},
            )
            companion.db.equipment = {"armor": _BOUND_ITEM}
            set_official_selection(subject, selected)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_RUNTIME)
            self.assertEqual(resource["url"], f"/art/{bound_identity}")
            self.assertNotEqual(resource["url"], art.url(selected))
            # The selection survived the outranking presentation untouched.
            self.assertEqual(official_preferences_for(subject).selection, selected)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_record_default_card_outranks_the_mounted_official_default(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            image_id = "cccccccc-3333-4333-8333-333333333333"
            identity = f"gallery/character/{_COMPANION_KEY}/{image_id}.png"
            art.write_store_file(identity)
            append_card(
                subject,
                image_id=image_id,
                stored_identity=identity,
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding=None,
                source="seed",
                created_at=100,
                image_size={"width": 768, "height": 1024},
            )
            self.assertEqual(record_for(subject, create=False).db.default_image_id, image_id)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_RUNTIME)
            self.assertEqual(resource["url"], f"/art/{identity}")

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_personal_selection_outranks_a_coexisting_record_default_card(self):
        with _official_art_scope() as art:
            art.mount("default.png")
            selected = art.mount("selected.png")
            art.set_manifest(default="default.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            set_official_selection(subject, selected)
            image_id = "dddddddd-4444-4444-8444-444444444444"
            identity = f"gallery/character/{_COMPANION_KEY}/{image_id}.png"
            art.write_store_file(identity)
            # A FIRST card becomes its record's automatic default without
            # clearing the player's selection, so both preferences coexist:
            # the selection still owns the payload.
            append_card(
                subject,
                image_id=image_id,
                stored_identity=identity,
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding=None,
                source="seed",
                created_at=100,
                image_size={"width": 768, "height": 1024},
            )
            record = record_for(subject, create=False)
            self.assertEqual(record.db.default_image_id, image_id)
            self.assertEqual(official_preferences_for(subject).selection, selected)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_OFFICIAL)
            self.assertEqual(resource["url"], art.url(selected))
            # The runtime default card and the stored selection are untouched.
            self.assertEqual(record.db.default_image_id, image_id)
            self.assertEqual(official_preferences_for(subject).selection, selected)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_classic_runtime_asset_outranks_the_mounted_official_default(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            identity = f"portrait/character/{_COMPANION_KEY}.png"
            art.write_store_file(identity, b"classic asset")
            ensure(subject, "synthetic description")
            claimed = [
                record for record in claim(10) if record.db_key == record_key(subject)
            ]
            self.assertEqual(len(claimed), 1, "the pending classic job was not claimed")
            settled = settle(
                subject,
                generation_token=str(claimed[0].db.generation_token),
                status=ArtAssetStatus.DONE,
                output_identity=identity,
                error=None,
            )
            self.assertIsNotNone(settled)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            resource = self._candidate(artwork)
            self.assertEqual(resource["origin"], ORIGIN_RUNTIME)
            self.assertEqual(resource["url"], f"/art/{identity}")

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_admitted_portraitless_companion_keeps_its_reference(self):
        with _official_art_scope():
            companion = self._official_companion()
            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            # An empty official catalog and no runtime artwork leave no real
            # candidate, but the ADMITTED companion keeps its reference: the
            # descriptor carries the deterministic attribute-selected alpha
            # terminal instead, and the client renders that silhouette (never
            # an invented real image).
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            self.assertIsNone(self._candidate(artwork))
            self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
            self.assertEqual(
                artwork["terminal"]["resource"]["origin"], ORIGIN_SILHOUETTE
            )
            self.assertTrue(
                artwork["terminal"]["resource"]["url"].startswith("/art/defaults/")
            )

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_companion_without_a_named_subject_keeps_its_reference(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            companion = _companion("測試無肖像隊友", self.room)
            join_party(companion, self.player)

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            # Admitted by membership, so the reference stands; the descriptor
            # exposes no real candidate and no generated subject key, so no
            # official default is ever presented for a subject-less companion.
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            self.assertIsNone(self._candidate(artwork))
            self.assertIsNone(artwork["generation_subject"])
            self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_unresolved_retained_selection_falls_through_and_stays_stored(self):
        with _official_art_scope() as art:
            selected = art.mount("selected.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            set_official_selection(subject, selected)
            # The artwork an older selection named is gone: the identity stays
            # a legal stored preference the chain simply ignores.
            shutil.rmtree(art.content)
            load_catalog()

            panels = self._panels()

            slot, artwork = self._slot_and_entry(panels, companion)
            # The stored preference is simply ignored: the admitted companion
            # keeps its reference while the descriptor carries no real
            # candidate, and the stored selection stays exactly as it was.
            self.assertEqual(slot["portrait_ref"], portrait_catalog_key(companion.pk))
            self.assertIsNone(self._candidate(artwork))
            self.assertEqual(official_preferences_for(subject).selection, selected)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_repeated_official_presentation_writes_nothing(self):
        with _official_art_scope() as art:
            art.mount("default.png")
            selected = art.mount("selected.png")
            art.set_manifest(default="default.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            set_official_selection(subject, selected)
            self._read_only_render_case(
                art, subject, companion, art.url(selected), ORIGIN_OFFICIAL
            )

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_repeated_runtime_default_presentation_writes_nothing(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            image_id = "eeeeeeee-5555-4555-8555-555555555555"
            identity = f"gallery/character/{_COMPANION_KEY}/{image_id}.png"
            art.write_store_file(identity)
            append_card(
                subject,
                image_id=image_id,
                stored_identity=identity,
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding=None,
                source="seed",
                created_at=100,
                image_size={"width": 768, "height": 1024},
            )
            # The record-default branch reads the gallery record through the
            # chain module's own alias, so this fixture is the one that
            # exercises that read under the tripwires.
            self._read_only_render_case(
                art, subject, companion, f"/art/{identity}", ORIGIN_RUNTIME
            )

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_repeated_mounted_default_presentation_creates_no_record(self):
        with _official_art_scope() as art:
            identity = art.mount("hero.png")
            companion = self._official_companion()
            subject = character_subject_for(companion)
            self.assertIsNone(record_for(subject, create=False))

            self._read_only_render_case(
                art, subject, companion, art.url(identity), ORIGIN_OFFICIAL
            )

            # Repeated presentation of the mounted default still creates
            # nothing: the record is absent after three armed renders.
            self.assertIsNone(record_for(subject, create=False))


class PartyValidatorTests(unittest.TestCase):
    def _panel(self, slots, viewed_member_id=None):
        used = sum(
            1
            for slot in slots
            if isinstance(slot, dict)
            and isinstance(slot.get("membership"), dict)
            and slot["membership"].get("general") is True
        )
        if viewed_member_id is None:
            first = slots[0] if slots and isinstance(slots[0], dict) else {}
            viewed_member_id = first.get("identity", 1)
        return {
            "schema_version": PARTY_SCHEMA_VERSION,
            "available": True,
            "general_quota": {"used": used, "limit": PARTY_GENERAL_LIMIT},
            "viewed_member_id": viewed_member_id,
            "slots": slots,
        }

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_valid_forms_normalize_identically(self):
        # The commander row alone is the available empty party.
        commander_only = self._panel([_commander()])
        self.assertEqual(validate_party(commander_only), commander_only)
        two_rows = self._panel([_commander(), _slot()])
        self.assertEqual(validate_party(two_rows), two_rows)
        # Any presented row may be the viewed member.
        viewed = self._panel([_commander(), _slot()], viewed_member_id=41)
        self.assertEqual(validate_party(viewed), viewed)
        # Paired astral code points (surrogate pairs in UTF-16 terms) are
        # legal text on both mirrors.
        validate_party(
            self._panel([_commander(), _slot(display_name="薇拉\U0001F600")])
        )
        for ref in ("42", "1" * 32):
            panel = self._panel([_commander(), _slot(portrait_ref=ref)])
            self.assertEqual(validate_party(panel)["slots"][1]["portrait_ref"], ref)

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_bounds_only_hp_semantics(self):
        # Zero is legal and no current/maximum cross assertion exists — traits
        # are truth (the delta spec overrides the proposal's "positive" wording).
        validate_party(self._panel([
            _commander(
                hp_current=0, hp_maximum=0,
                mp_current=0, mp_maximum=0,
                sp_current=0, sp_maximum=0,
            ),
            _slot(hp_current=500, hp_maximum=1),
        ]))
        validate_party(self._panel([
            _commander(),
            _slot(mp_current=9, mp_maximum=1, sp_current=0, sp_maximum=0),
        ]))

    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_extended_shape_accepts_membership_and_beyond_quota_rows(self):
        payload = self._panel([
            _commander(),
            _slot(identity=1),
            _slot(identity=2, membership={
                "general": False,
                "temporary_commissions": [
                    {"quest_id": "reunion:1", "role_id": "protected", "label": "重逢"},
                ],
            }),
            _slot(identity=3, membership={
                "general": False,
                "temporary_commissions": [
                    {"quest_id": "reunion:2", "role_id": "protected", "label": "重逢"},
                ],
            }),
        ])
        self.assertEqual(validate_party(payload), payload)
        self.assertEqual(payload["general_quota"], {"used": 1, "limit": PARTY_GENERAL_LIMIT})

    def test_maximal_row_count_payload_stays_inside_the_byte_bound(self):
        # Maximum row count (commander + every companion slot) with bounded
        # names, gauges and representative commission metadata. This proves
        # the row envelope, not a maximum possible payload: the byte guard
        # below is what rejects oversized metadata.
        name = "同" * MAX_DISPLAY_NAME_CODE_POINTS
        commission = {
            "quest_id": "q" * MAX_DISPLAY_NAME_CODE_POINTS,
            "role_id": "r" * MAX_DISPLAY_NAME_CODE_POINTS,
            "label": "護" * MAX_PARTY_COMMISSION_LABEL,
        }
        rows = [_commander(display_name=name)]
        rows += [
            _slot(
                identity=index + 100,
                display_name=name,
                bond_stage=name,
                membership={
                    "general": False,
                    "temporary_commissions": [commission],
                },
            )
            for index in range(PARTY_MAX_SLOTS)
        ]
        validated = validate_party(self._panel(rows, viewed_member_id=7))
        self.assertEqual(len(validated["slots"]), PARTY_MAX_ROWS)
        self.assertLessEqual(json_byte_size(validated), MAX_CANONICAL_JSON_BYTES)

    def test_oversized_metadata_is_rejected_by_the_byte_guard(self):
        # The commission list has no party-specific count bound, so the closing
        # envelope check is what keeps a hostile row from reaching the wire.
        name = "同" * MAX_DISPLAY_NAME_CODE_POINTS
        rows = [_commander(display_name=name)]
        rows += [
            _slot(
                identity=index + 100,
                display_name=name,
                bond_stage=name,
                membership={
                    "general": False,
                    "temporary_commissions": [
                        {
                            "quest_id": f"{index}-{slot}" + "q" * 120,
                            "role_id": "r" * MAX_DISPLAY_NAME_CODE_POINTS,
                            "label": "護" * MAX_PARTY_COMMISSION_LABEL,
                        }
                        for slot in range(8)
                    ],
                },
            )
            for index in range(PARTY_MAX_SLOTS)
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_party(self._panel(rows, viewed_member_id=7))

    def test_drift_rejections(self):
        cases = {
            "over slot bound": self._panel(
                [_commander()]
                + [
                    _slot(
                        identity=i + 1,
                        membership={"general": False, "temporary_commissions": []},
                    )
                    for i in range(PARTY_MAX_SLOTS + 1)
                ]
            ),
            "missing row key": self._panel([
                _commander(),
                {
                    "identity": 1,
                    "display_name": "a",
                    "portrait_ref": None,
                    "hp_current": 0,
                    "hp_maximum": 0,
                    "bond_stage": "摯友",
                },
            ]),
            "unknown row key": self._panel([_commander(), _slot(token="a1")]),
            "missing membership": self._panel([
                _commander(),
                {
                    key: value
                    for key, value in _slot().items()
                    if key != "membership"
                },
            ]),
            "membership not a mapping": self._panel(
                [_commander(), _slot(membership=[])]
            ),
            "unknown membership key": self._panel(
                [
                    _commander(),
                    _slot(membership={"general": True, "temporary_commissions": [], "x": 1}),
                ]
            ),
            "numeric general": self._panel(
                [_commander(), _slot(membership={"general": 1, "temporary_commissions": []})]
            ),
            "commission not a mapping": self._panel(
                [
                    _commander(),
                    _slot(membership={"general": False, "temporary_commissions": ["q"]}),
                ]
            ),
            "unknown commission key": self._panel([_commander(), _slot(membership={
                "general": False,
                "temporary_commissions": [
                    {"quest_id": "q", "role_id": "r", "label": "l", "x": 1}
                ],
            })]),
            "duplicate commission": self._panel([_commander(), _slot(membership={
                "general": False,
                "temporary_commissions": [
                    {"quest_id": "q", "role_id": "r", "label": "l"},
                    {"quest_id": "q", "role_id": "r", "label": "l"},
                ],
            })]),
            "numeric bond_stage": self._panel([_commander(), _slot(bond_stage=3)]),
            "bool bond_stage": self._panel([_commander(), _slot(bond_stage=True)]),
            "blank bond_stage": self._panel([_commander(), _slot(bond_stage="")]),
            "blank display_name": self._panel([_commander(), _slot(display_name="")]),
            "over-bound display_name": self._panel(
                [
                    _commander(),
                    _slot(display_name="同" * (MAX_DISPLAY_NAME_CODE_POINTS + 1)),
                ]
            ),
            "negative hp_current": self._panel([_commander(), _slot(hp_current=-1)]),
            "negative mp_maximum": self._panel([_commander(), _slot(mp_maximum=-1)]),
            "string sp_current": self._panel([_commander(), _slot(sp_current="3")]),
            "bool knocked_out": self._panel([_commander(), _slot(knocked_out=1)]),
            "string unread": self._panel([_commander(), _slot(unread="no")]),
            "unknown role": self._panel([_commander(), _slot(role="ally")]),
            "bool identity": self._panel([_commander(), _slot(identity=True)]),
            "zero identity": self._panel([_commander(), _slot(identity=0)]),
            "numeric portrait_ref": self._panel([_commander(), _slot(portrait_ref=42)]),
            "non-decimal portrait_ref": self._panel([_commander(), _slot(portrait_ref="4a")]),
            "unicode decimal portrait_ref": self._panel(
                [_commander(), _slot(portrait_ref="４２")]
            ),
            "empty portrait_ref": self._panel([_commander(), _slot(portrait_ref="")]),
            "over-bound portrait_ref": self._panel(
                [_commander(), _slot(portrait_ref="1" * 33)]
            ),
            "old version": {
                "schema_version": 2,
                "available": True,
                "general_quota": {"used": 0, "limit": 4},
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "missing general_quota": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": True,
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "unknown quota key": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": True,
                "general_quota": {"used": 0, "limit": 4, "x": 1},
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "quota used exceeds limit": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": True,
                "general_quota": {"used": 5, "limit": 4},
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "missing viewed_member_id": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": True,
                "general_quota": {"used": 0, "limit": 4},
                "slots": [_commander()],
            },
            "viewed member not presented": self._panel(
                [_commander(), _slot()], viewed_member_id=99
            ),
            "zero viewed_member_id": self._panel(
                [_commander()], viewed_member_id=0
            ),
            "bool viewed_member_id": self._panel(
                [_commander()], viewed_member_id=True
            ),
            "no commander row": self._panel([_slot()]),
            "two commander rows": self._panel(
                [_commander(), _commander(identity=8)]
            ),
            "commander row not first": self._panel([_slot(), _commander()]),
            "commander bond_stage": self._panel(
                [_commander(bond_stage="摯友")]
            ),
            "commander membership": self._panel(
                [_commander(membership={"general": True, "temporary_commissions": []})]
            ),
            "knocked-out commander": self._panel(
                [_commander(knocked_out=True)]
            ),
            "duplicate identities": self._panel(
                [_commander(), _slot(identity=7)]
            ),
            "lone high surrogate display_name": self._panel(
                [_commander(), _slot(display_name="\ud800")]
            ),
            "lone low surrogate bond_stage": self._panel(
                [_commander(), _slot(bond_stage="\udc00")]
            ),
            "version drift": {
                "schema_version": PARTY_SCHEMA_VERSION + 1,
                "available": True,
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "unavailable discriminator": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": False,
                "viewed_member_id": 7,
                "slots": [_commander()],
            },
            "slots not a list": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": True,
                "viewed_member_id": 7,
                "slots": {},
            },
            "panel not a dict": ["nope"],
        }
        for label, payload in cases.items():
            with self.subTest(label):
                with self.assertRaises(ProtocolValidationError):
                    validate_party(payload)


class PartyPushTests(BattlefieldIsolation, EvenniaTest):
    """Connected-player pushes around the three party write seams."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        register_catalog()
        watchers.clear_watchers()
        self.room = create_object(Room, key="队伍告别厅")
        self.player = _player()
        self.player.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    @staticmethod
    def _messages(session, name):
        return [call[name][0][0] for call in session.sent if name in call]

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_party_leave_action_publishes_full_snapshot_without_the_companion(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "r1",
            "base_revision": coordinator.revision,
            "action_id": "explore.party_leave",
            "payload": {"npc_id": int(companion.pk)},
        }

        handle_ui_action(
            session,
            self.player,
            envelope,
            self.action_registry,
            self.registry,
        )

        results = self._messages(session, "ui_action_result")
        snapshots = self._messages(session, "ui_snapshot")
        self.assertEqual(results[-1]["outcome"], "success")
        # The leave seam publishes a full snapshot (membership can pair with
        # anything), and the presentation publication precedes the result.
        self.assertTrue(snapshots, "party_leave must publish a full snapshot")
        last = snapshots[-1]
        identities = [row["identity"] for row in last["panels"]["party"]["slots"]]
        self.assertNotIn(int(companion.pk), identities)
        # Scripted protocol probe (task 5.2 evidence): the published envelope
        # is the exact wire form — full snapshot validated against the
        # registered panel allowlist, party included.
        normalized = validate_ui_snapshot(
            last, known_panels=set(self.registry.panel_names)
        )
        self.assertIn("party", normalized["panels"])
        self.assertEqual(normalized["panels"]["party"], last["panels"]["party"])
        sequence = [
            name
            for call in session.sent
            for name in ("ui_snapshot", "ui_action_result")
            if name in call
        ]
        self.assertLess(
            len(sequence) - 1 - sequence[::-1].index("ui_snapshot"),
            len(sequence) - 1 - sequence[::-1].index("ui_action_result"),
            "the post-leave snapshot must precede the action result",
        )

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_party_view_member_publishes_one_party_update_before_the_result(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        session = _RecordingSession(self.player)
        session.ndb.party_unlocks = {
            int(companion.pk): MemberUnlocks(True, frozenset({"t_heal"})),
        }
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        revision_before = coordinator.revision
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "r1",
            "base_revision": coordinator.revision,
            "action_id": "party.view_member",
            "payload": {"member_id": int(companion.pk), "tab": "skills"},
        }

        handle_ui_action(
            session,
            self.player,
            envelope,
            self.action_registry,
            self.registry,
        )

        results = self._messages(session, "ui_action_result")
        self.assertEqual(results[-1]["outcome"], "success")
        self.assertEqual(results[-1]["code"], "viewing_member")
        updates = self._messages(session, "ui_update")
        self.assertTrue(updates, "party.view_member must publish a party update")
        last = updates[-1]
        self.assertGreater(last["revision"], revision_before)
        party = last["panels"]["party"]
        self.assertEqual(party["viewed_member_id"], int(companion.pk))
        row = next(
            row for row in party["slots"] if row["identity"] == int(companion.pk)
        )
        self.assertIs(row["unread"], False)
        # The dispatcher publishes presentation first and the result second, at
        # the same revision (action-dispatch's completion contract).
        self.assertEqual(results[-1]["presentation_revision"], last["revision"])
        sequence = [
            name
            for call in session.sent
            for name in ("ui_update", "ui_action_result")
            if name in call
        ]
        self.assertLess(sequence.index("ui_update"), len(sequence) - 1)

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_companion_deletion_pushes_party_update_to_live_watchers(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        companion_id = int(companion.pk)
        session = ServerSession()
        session.init_session(
            "webclient/websocket", ("localhost", 9999), self.sessionhandler
        )
        session.sessid = 911
        # Mirror the test_watchers idiom: the mocked handler keeps an explicit
        # sessid mapping so the watcher registry's liveness check resolves it.
        self.sessionhandler[session.sessid] = session
        session.protocol_key = "webclient/websocket"
        session.puppet = self.player
        self.player.sessions.add(session)
        recorded = []
        session.msg = lambda **kwargs: recorded.append(kwargs)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        watchers.register_watcher(session)

        # The delete seam defers the fan-out through transaction.on_commit;
        # evennia's TestCase wraps the test in an outer transaction, so the
        # capture seam executes what the successful inner delete committed.
        with self.captureOnCommitCallbacks(execute=True):
            companion.delete()

        updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
        self.assertTrue(updates, "purge must push a party panel update")
        payload = updates[-1]["panels"]["party"]
        self.assertIs(payload["available"], True)
        self.assertNotIn(companion_id, [row["identity"] for row in payload["slots"]])
        # The purge leaves the commander's own row and nothing else.
        self.assertEqual(
            [row["identity"] for row in payload["slots"]], [int(self.player.pk)]
        )
        self.assertEqual(payload["viewed_member_id"], int(self.player.pk))
        del self.sessionhandler[session.sessid]

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_deletion_without_watchers_is_a_silent_no_op(self):
        companion = _companion("孤身薇拉", self.room)
        join_party(companion, self.player)
        companion_id = int(companion.pk)
        with self.captureOnCommitCallbacks(execute=True):
            companion.delete()
        self.assertNotIn(companion_id, [int(dbid) for dbid in self.player.db.party or []])

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_registry_construction_failure_degrades_to_a_bounded_diagnostic(self):
        # Final rubber-duck round: a registry-build defect must never raise
        # out of the deferred delete callback — the committed deletion stays
        # committed and later on-commit callbacks keep running.
        from unittest.mock import patch

        from web.webclient.presentation import party_push

        def _boom():
            raise RuntimeError("registry construction defect")

        with (
            patch.object(
                party_push, "watchers_for", return_value=((object(), "x" * 22),)
            ),
            patch.object(party_push, "build_production_registry", _boom),
            patch.object(party_push, "log_warn") as warned,
        ):
            party_push.push_party_update(self.player)
        events = [call.args[0] for call in warned.call_args_list]
        self.assertIn("party_push_failed", events)


class PartyCombatJoinTests(BattlefieldIsolation, EvenniaTest):
    """The join-by-identity contract and settlement push timing."""

    def setUp(self):
        # Combat rounds run on kit skills with the production-forced innate
        # rows re-seeded; the monster keeps its live threat tier so the
        # rulebook-backed round path stays valid.
        open_synthetic_scope(self, "skills", extra=synth_innate_overlay())
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="队伍演武场")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["t_cinder_cleave"])
        self.companion = _companion("薇拉", self.room, hp_current=90, hp_maximum=90)
        join_party(self.companion, self.player)
        self.monster = _monster()
        self.monster.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_combat_partial_publishers_name_the_party_panel(self):
        """The round-committing combat actions publish the party panel with it.

        The v7 party-combat contract moved the settlement's publication set out
        of the static ``ActionSpec`` and into the adapter's own result: the two
        ids whose adapter can commit a round -- ``combat.command`` (the
        command union's completing confirmation) and ``combat.exit_confirm``
        (the exit half; ``combat.exit_prompt`` runs no action) -- funnel
        through the shared settlement result, whose affected-panel set has to
        name the party panel so a wounded companion's row is republished with
        the round. Neither spec declares it statically (``combat.command``
        declares only the combat menu it also edits, the exit specs declare
        the empty result-decided set).
        """
        round_committing = (
            ("combat.command", _command_adapter),
            ("combat.exit_confirm", _exit_confirm_adapter),
        )
        for action_id, adapter in round_committing:
            with self.subTest(action_id):
                spec = self.action_registry.spec(action_id)
                self.assertIs(spec.adapter, adapter)
        self.assertIn("party", AFFECTED_PANELS)

    @covers_requirement(
        "webclient-party-panel::party-presentation-stays-current-across-membership-and-combat-changes"
    )
    def test_settlement_round_publishes_fresh_companion_hp(self):
        from unittest.mock import patch

        engage(self.player, self.monster)
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        priming = coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        priming_hp = next(
            row["hp_current"]
            for row in priming["panels"]["party"]["slots"]
            if row["identity"] == int(self.companion.pk)
        )
        self.assertEqual(priming_hp, 90)
        # Deterministic wound between commits: the round must not simply
        # re-render the same number, the pushed row has to visibly move off
        # the priming snapshot and track the post-settlement stored gauge.
        self.companion.traits.hp.current = 45

        def _command_envelope(request_id, actor_id, command):
            """One v7 guarded command: the session/round/draft revisions
            authorize exactly this actor's draft entry, and the closed command
            union carries that member's choice."""
            record = read_session(self.player)
            return {
                "protocol_version": 1,
                "presentation_epoch": coordinator.epoch,
                "request_id": request_id,
                "base_revision": coordinator.revision,
                "action_id": "combat.command",
                "payload": {
                    "session_id": record.session_id,
                    "round_revision": record.round_revision,
                    "draft_version": record.draft_version,
                    "actor_id": actor_id,
                    "command": command,
                },
            }

        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            # The joined companion is a battle participant, so the v7 draft
            # needs both members: the commander's cast is admitted first (a
            # draft edit, no round yet), the companion's tactic is the
            # completing confirmation that resolves the one ordinary round.
            handle_ui_action(
                session,
                self.player,
                _command_envelope(
                    "r1",
                    self.player.pk,
                    {
                        "kind": "skill",
                        "payload": {
                            "skill_key": "t_cinder_cleave",
                            "target_ids": [int(self.monster.pk)],
                        },
                    },
                ),
                self.action_registry,
                self.registry,
            )
            handle_ui_action(
                session,
                self.player,
                _command_envelope(
                    "r2",
                    self.companion.pk,
                    {"kind": "tactic", "payload": {"key": "defend"}},
                ),
                self.action_registry,
                self.registry,
            )
        party_payloads = [
            call[name][0][0]["panels"]["party"]
            for call in session.sent
            for name in ("ui_update", "ui_snapshot")
            if name in call and "party" in call[name][0][0]["panels"]
        ]
        self.assertGreaterEqual(
            len(party_payloads), 2, "the round must publish party with the cast"
        )
        committed = next(
            row
            for row in party_payloads[-1]["slots"]
            if row["identity"] == int(self.companion.pk)
        )
        stored = stored_gauge_pair(self.companion, "hp")
        self.assertEqual((committed["hp_current"], committed["hp_maximum"]), stored)
        self.assertNotEqual(
            committed["hp_current"],
            priming_hp,
            "the settlement push must reflect the new wound, not the priming snapshot",
        )
        results = [
            call["ui_action_result"][0][0] for call in session.sent if "ui_action_result" in call
        ]
        # The completing confirmation really committed the round (not a
        # draft edit or an admission rejection): its published set is what
        # carries the party panel above.
        self.assertEqual(results[-1]["outcome"], "success", results[-1])
        self.assertEqual(results[-1]["code"], "round_committed", results[-1])

    @covers_requirement(
        "webclient-party-panel::party-tokens-are-joined-not-duplicated"
    )
    def test_identity_join_recovers_the_session_token_from_the_combat_panel(self):
        import re

        engage(self.player, self.monster)
        context = PresentationContext(actor=self.player, protocol_version=1)
        party = self.registry.render("party", context)
        combat = self.registry.render("context_actions", context)
        participants = {
            row["identity"]: row["token"] for row in combat["participants"]
        }
        pattern = re.compile(r"^a\d+$")
        for row in party["slots"]:
            participant_token = participants[row["identity"]]
            self.assertRegex(participant_token, pattern)
        # The party payload itself names no token anywhere.
        self.assertNotIn("token", party)
        for slot in party["slots"]:
            self.assertNotIn("token", slot)


if __name__ == "__main__":
    unittest.main()
