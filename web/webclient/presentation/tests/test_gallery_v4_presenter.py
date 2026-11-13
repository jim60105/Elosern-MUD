"""Version-4 gallery projection and its remembered per-category selection.

Characters and companions are created in each test; monster species, variants
and tiers come from the synthetic kit plus file-local factory rows; a met place
is a synthetic terrain region. Every projection goes through
``gallery_presenter``, which returns only payloads that passed
``validate_gallery``; the tests re-validate each one explicitly.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.server.signals import SIGNAL_OBJECT_POST_PUPPET
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC, LLMNPC
from typeclasses.rooms import TerrainRoom
from web.webclient.presentation import gallery as gallery_module
from web.webclient.presentation import gallery_categories
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.gallery import gallery_presenter, validate_gallery
from web.webclient.presentation.gallery_categories import is_subject_admitted
from web.webclient.presentation.gallery_selection import (
    GalleryViewSelection,
    gallery_view_snapshot,
    select_gallery_category,
    select_gallery_subject,
)
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.registry import build_production_registry
from world.art import descriptors, scene_definitions
from world.art import gallery as gallery_api
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.maps import wilderness_provider
from world.rules.clock import get_world_clock
from world.rules.lore_knowledge import record_species_sighting
from world.rules.met_people import PLACE_REGION, record_person_interaction
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.rules.scene_visits import record_scene_entry
from world.tests.synthetic_data import (
    make_archetype,
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    synthetic_registries,
)

T_LOW = "t_low"
T_A = "t_a"
T_B = "t_b"


def _species_rows(key, name):
    variant_key = f"{key}_v"
    return (
        make_monster_species(key, display_name_zh=name, default_variant_key=variant_key),
        make_monster_variant(
            variant_key,
            species_key=key,
            threat_tier=T_LOW,
            ordinary_variant=True,
            danger_grade=None,
        ),
    )


_ROWS = (_species_rows(T_A, "甲測獸"), _species_rows(T_B, "乙測獸"))
EXTRA = {
    "monster_species": {species.key: species for species, _ in _ROWS},
    "monster_variants": {variant.key: variant for _, variant in _ROWS},
    "monster_tiers": {T_LOW: make_monster_tier(T_LOW, display_name_zh="低測級")},
}


def _database_state():
    """Every stored object, attribute and tag row, values included."""
    return (
        list(ObjectDB.objects.order_by("id").values_list(
            "id", "db_key", "db_typeclass_path", "db_location_id", "db_account_id"
        )),
        [
            (attribute.id, attribute.db_key, attribute.db_category, repr(attribute.value))
            for attribute in Attribute.objects.order_by("id")
        ],
        list(Tag.objects.order_by("id").values_list("id", "db_key", "db_category")),
    )


def _listed(panel):
    return [row["subject_key"] for group in panel["groups"] for row in group["subjects"]]


@synthetic_registries("monster_species", "monster_variants", "monster_tiers", extra=EXTRA)
class GalleryV4PresenterTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.registry = build_production_registry()
        self.actor = self.char1
        self.account.characters.add(self.actor)
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "t_v4_actor"}

    # -- fixtures -----------------------------------------------------------

    def _session(self, actor=None):
        session = SimpleNamespace(
            ndb=SimpleNamespace(), puppet=actor or self.actor,
            protocol_key="websocket", msg=lambda *args, **kwargs: None,
        )
        attach_coordinator(session, self.registry)
        return session

    def _add_character(self, key):
        character = create_object(PlayerCharacter, key=key, location=self.room1)
        character.account = self.account
        self.account.characters.add(character)
        return character

    def _companion(self, key, stable_key, owner=None):
        owner = owner or self.actor
        companion = create_object(NPC, key=key, location=self.room1)
        companion.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        self._enlist(companion, owner)
        return companion

    def _enlist(self, companion, owner):
        companion.db.party_member = owner.pk
        owner.db.party = [*(owner.db.party or []), companion.pk]
        meta = dict(owner.db.party_meta or {})
        meta[str(companion.pk)] = {"general": True, "reasons": []}
        owner.db.party_meta = meta
        return companion

    def _terrain(self, key, coordinates):
        room = create_object(TerrainRoom, key=key, location=None)
        room.ndb.active_coordinates = coordinates
        return room

    def _named_npc(self, key):
        # A named NPC never needs to stand in the recorded place, and a fresh
        # object inside a terrain room would trip the wilderness receive hook.
        npc = create_object(NPC, key=key, location=self.room1)
        npc.db.portrait_policy = {"mode": "named", "stable_key": key}
        return npc

    def _meet(self, npc, room, region_key, actor=None):
        actor = actor or self.actor
        actor.location = room
        with patch.object(
            wilderness_provider, "region_for_coordinates", return_value=region_key
        ):
            record_person_interaction(actor, npc)

    def _leave_party(self, companion, owner=None):
        owner = owner or self.actor
        owner.db.party = [pk for pk in owner.db.party if pk != companion.pk]
        companion.db.party_member = None

    def _card(self, stable_key, number=1):
        subject = ArtSubject(ArtSubjectKind.CHARACTER, stable_key)
        image = str(uuid.UUID(int=number))
        identity = f"gallery/character/{stable_key}/{image}.png"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        gallery_api.append_card(
            subject, image_id=image, stored_identity=identity, prompt=None, seed=None,
            checkpoint=None, requested_fields=[], binding=None, source="seed",
            created_at=100 + number, image_size={"width": 1000, "height": 1000},
        )
        return identity

    def _build(self, session, actor=None):
        panel = gallery_presenter(build_presentation_context(session, actor or self.actor))
        validate_gallery(panel)
        return panel

    # -- the projection -----------------------------------------------------

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-projection-carries-one-category-with-tile-artwork"
    )
    def test_only_the_selected_categorys_subjects_are_listed(self):
        self._add_character("測者乙")
        companion = self._companion("同行甲", "t_v4_companion_a")
        record_species_sighting(self.actor, T_A)
        session = self._session()
        self.assertEqual(select_gallery_category(session, self.actor, "party")["outcome"], "success")
        panel = self._build(session)
        self.assertEqual(panel["category"], "party")
        self.assertEqual(_listed(panel), [f"portrait:character:t_v4_companion_a"])
        self.assertEqual(panel["selected"], "portrait:character:t_v4_companion_a")
        self.assertEqual(panel["groups"][0]["count"], 1)
        self.assertTrue(panel["groups"][0]["expanded"])
        counts = {row["key"]: (row["count"], row["enabled"]) for row in panel["categories"]}
        self.assertEqual(counts, {
            "mine": (2, True), "party": (1, True), "people": (0, True),
            "monster": (1, True), "scene": (0, True),
        })
        self.assertIsNotNone(companion)

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-projection-carries-one-category-with-tile-artwork"
    )
    def test_a_tile_carries_its_default_artwork_without_a_selection(self):
        self._companion("同行甲", "t_v4_companion_a")
        self._companion("同行乙", "t_v4_companion_b")
        identity = self._card("t_v4_companion_b")
        session = self._session()
        select_gallery_category(session, self.actor, "party")
        select_gallery_subject(session, self.actor, "portrait:character:t_v4_companion_a")
        panel = self._build(session)
        self.assertEqual(panel["selected"], "portrait:character:t_v4_companion_a")
        rows = {row["subject_key"]: row for row in panel["groups"][0]["subjects"]}
        tile = rows["portrait:character:t_v4_companion_b"]
        self.assertEqual(tile["card_count"], 1)
        images = [entry for entry in tile["artwork"]["attempts"] if entry["type"] == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["resource"]["resource_id"], identity)
        # A tile with no resolvable image carries null rather than a stand-in.
        unselected = rows["portrait:character:t_v4_companion_a"]
        self.assertEqual(unselected["card_count"], 0)
        self.assertIsNone(unselected["artwork"])

    def test_one_failing_tile_degrades_only_itself(self):
        self._companion("同行甲", "t_v4_companion_a")
        self._companion("同行乙", "t_v4_companion_b")
        self._card("t_v4_companion_a", number=1)
        self._card("t_v4_companion_b", number=2)
        real = gallery_module.describe_portrait

        def flaky(subject, entity=None):
            if subject.key == "t_v4_companion_b":
                raise RuntimeError("t_synthetic_failure")
            return real(subject, entity)

        session = self._session()
        select_gallery_category(session, self.actor, "party")
        with patch.object(gallery_module, "describe_portrait", side_effect=flaky), \
                patch.object(gallery_module, "log_warn") as warn:
            panel = self._build(session)
        rows = {row["subject_key"]: row for row in panel["groups"][0]["subjects"]}
        self.assertIsNotNone(rows["portrait:character:t_v4_companion_a"]["artwork"])
        self.assertIsNone(rows["portrait:character:t_v4_companion_b"]["artwork"])
        self.assertEqual(rows["portrait:character:t_v4_companion_b"]["card_count"], 1)
        warn.assert_called_once()
        self.assertEqual(warn.call_args.args[0], "gallery_tile_artwork_failed")

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-projection-carries-one-category-with-tile-artwork"
    )
    def test_building_twice_changes_nothing(self):
        self._companion("同行甲", "t_v4_companion_a")
        self._card("t_v4_actor")
        record_species_sighting(self.actor, T_A)
        session = self._session()
        select_gallery_category(session, self.actor, "mine")
        self._build(session)  # warm attribute caches so both measured runs start alike
        before = _database_state()
        files = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        view = session.ndb.gallery_view
        first = self._build(session)
        second = self._build(session)
        self.assertEqual(first, second)
        self.assertEqual(_database_state(), before)
        self.assertEqual(
            {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}, files
        )
        self.assertIs(session.ndb.gallery_view, view)

    # -- the people category ------------------------------------------------

    @covers_requirement(
        "webclient-gallery-panel::exactly-one-people-group-is-expanded"
    )
    def test_people_opens_the_most_recent_place_only(self):
        room_a = self._terrain("t_room_a", (1, 1))
        room_b = self._terrain("t_room_b", (2, 2))
        npc_a = self._named_npc("t_npc_a")
        npc_b = self._named_npc("t_npc_b")
        self._meet(npc_a, room_a, "t_region_a")
        self._meet(npc_b, room_b, "t_region_b")
        session = self._session()
        self.assertEqual(select_gallery_category(session, self.actor, "people")["outcome"], "success")
        panel = self._build(session)
        self.assertEqual(panel["category"], "people")
        self.assertEqual(
            [(group["key"], group["expanded"], group["count"]) for group in panel["groups"]],
            [
                (f"{PLACE_REGION}:t_region_b", True, 1),
                (f"{PLACE_REGION}:t_region_a", False, 1),
            ],
        )
        # The collapsed place carries no subjects at all.
        self.assertEqual(_listed(panel), ["portrait:character:t_npc_b"])
        self.assertEqual(panel["selected"], "portrait:character:t_npc_b")
        counts = {row["key"]: row["count"] for row in panel["categories"]}
        self.assertEqual(counts["people"], 2)
        # A stored person in the collapsed place is no candidate: the selected
        # person falls back to the expanded place's first subject.
        session.ndb.gallery_view = GalleryViewSelection(
            self.actor.pk, "people", (("people", "portrait:character:t_npc_a"),)
        )
        self.assertEqual(self._build(session)["selected"], "portrait:character:t_npc_b")
        # And that person cannot be selected directly: the panel never lists it.
        self.assertEqual(
            select_gallery_subject(session, self.actor, "portrait:character:t_npc_a")["code"],
            "unknown_subject",
        )

    @covers_requirement(
        "webclient-gallery-panel::exactly-one-people-group-is-expanded"
    )
    def test_a_remembered_place_that_is_gone_falls_back(self):
        room_a = self._terrain("t_room_a", (1, 1))
        room_b = self._terrain("t_room_b", (2, 2))
        npc_a = self._named_npc("t_npc_a")
        npc_b = self._named_npc("t_npc_b")
        self._meet(npc_a, room_a, "t_region_a")
        self._meet(npc_b, room_b, "t_region_b")
        session = self._session()
        remembered = (("people", f"{PLACE_REGION}:t_region_a"),)
        session.ndb.gallery_view = GalleryViewSelection(self.actor.pk, "people", (), remembered)
        # The remembered older place opens while it still has a listed person.
        panel = self._build(session)
        self.assertEqual(
            [group["key"] for group in panel["groups"] if group["expanded"]],
            [f"{PLACE_REGION}:t_region_a"],
        )
        self.assertEqual(_listed(panel), ["portrait:character:t_npc_a"])
        self.assertEqual(panel["selected"], "portrait:character:t_npc_a")
        # Once that place is gone, the most recent remaining place opens.
        npc_a.delete()
        panel = self._build(session)
        self.assertEqual(
            [(group["key"], group["expanded"]) for group in panel["groups"]],
            [(f"{PLACE_REGION}:t_region_b", True)],
        )
        self.assertEqual(panel["selected"], "portrait:character:t_npc_b")
        # A fallback is a read: the remembered place stays as stored.
        self.assertEqual(session.ndb.gallery_view.expanded, remembered)

    @covers_requirement(
        "webclient-gallery-panel::exactly-one-people-group-is-expanded"
    )
    def test_admission_covers_a_person_in_a_collapsed_place(self):
        room_a = self._terrain("t_room_a", (1, 1))
        room_b = self._terrain("t_room_b", (2, 2))
        npc_a = self._named_npc("t_npc_a")
        npc_b = self._named_npc("t_npc_b")
        self._meet(npc_a, room_a, "t_region_a")
        self._meet(npc_b, room_b, "t_region_b")
        session = self._session()
        select_gallery_category(session, self.actor, "people")
        panel = self._build(session)
        collapsed = [group for group in panel["groups"] if not group["expanded"]]
        self.assertEqual([group["key"] for group in collapsed], [f"{PLACE_REGION}:t_region_a"])
        self.assertEqual(collapsed[0]["subjects"], [])
        # Every mutating gallery adapter gates on this predicate.
        self.assertTrue(is_subject_admitted(self.actor, "portrait:character:t_npc_a"))

    # -- the stored selection -----------------------------------------------

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_a_fresh_session_opens_on_the_live_character(self):
        self._add_character("測者乙")
        session = self._session()
        panel = self._build(session)
        self.assertEqual(panel["category"], "mine")
        self.assertEqual(panel["selected"], "portrait:character:t_v4_actor")
        self.assertEqual(_listed(panel)[0], "portrait:character:t_v4_actor")
        self.assertIsNone(session.ndb.__dict__.get("gallery_view"))

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_each_category_keeps_its_own_subject(self):
        self._companion("同行甲", "t_v4_companion_a")
        self._companion("同行乙", "t_v4_companion_b")
        record_species_sighting(self.actor, T_A)
        record_species_sighting(self.actor, T_B)
        session = self._session()
        companion_b = "portrait:character:t_v4_companion_b"
        select_gallery_category(session, self.actor, "party")
        self.assertEqual(select_gallery_subject(session, self.actor, companion_b)["code"], "gallery_selected")
        select_gallery_category(session, self.actor, "monster")
        self.assertEqual(self._build(session)["selected"], f"portrait:monster:{T_A}")
        select_gallery_subject(session, self.actor, f"portrait:monster:{T_B}")
        self.assertEqual(self._build(session)["selected"], f"portrait:monster:{T_B}")
        select_gallery_category(session, self.actor, "party")
        panel = self._build(session)
        self.assertEqual((panel["category"], panel["selected"]), ("party", companion_b))
        select_gallery_category(session, self.actor, "monster")
        self.assertEqual(self._build(session)["selected"], f"portrait:monster:{T_B}")

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_a_vanished_subject_falls_back_to_the_category_default(self):
        companion_a = self._companion("同行甲", "t_v4_companion_a")
        companion_b = self._companion("同行乙", "t_v4_companion_b")
        session = self._session()
        select_gallery_category(session, self.actor, "party")
        select_gallery_subject(session, self.actor, "portrait:character:t_v4_companion_b")
        stored = session.ndb.gallery_view
        self._leave_party(companion_b)
        panel = self._build(session)
        self.assertEqual(panel["selected"], "portrait:character:t_v4_companion_a")
        self._leave_party(companion_a)
        panel = self._build(session)
        self.assertEqual(panel["category"], "party")
        self.assertIsNone(panel["selected"])
        self.assertEqual(panel["groups"][0]["subjects"], [])
        self.assertIsNone(panel["capabilities"])
        self.assertEqual(panel["cards"], [])
        # A fallback is a read: the remembered selection stays as stored.
        self.assertIs(session.ndb.gallery_view, stored)

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_a_disabled_remembered_category_falls_back_to_mine(self):
        session = self._session()
        session.ndb.gallery_view = GalleryViewSelection(self.actor.pk, "scene", ())
        with patch.dict(gallery_categories.DISABLED_REASONS, {"scene": "測試停用"}):
            panel = self._build(session)
        self.assertEqual((panel["category"], panel["selected"]), ("mine", "portrait:character:t_v4_actor"))

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_possession_keeps_the_stored_selection(self):
        get_world_clock()
        player = create_object(PlayerCharacter, key="測試勇者", location=self.room1)
        player.account = self.account
        self.account.characters.add(player)
        player.race = "human"
        player.apply_race_baseline()
        self.session.puppet = player
        player.sessions.add(self.session)
        self.session.protocol_key = "websocket"
        npc = create_object(LLMNPC, key="測試同伴", location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, player)
        attach_coordinator(self.session, self.registry)
        # The monster category reads the rendered actor's own sightings, so the
        # possessed companion has sighted the species too.
        record_species_sighting(player, T_A)
        record_species_sighting(npc, T_A)
        record_species_sighting(player, T_B)
        record_species_sighting(npc, T_B)
        select_gallery_category(self.session, player, "monster")
        select_gallery_subject(self.session, player, f"portrait:monster:{T_A}")
        enter_possession(player, npc)
        self.assertIs(self.session.puppet, npc)
        self.assertIsNotNone(gallery_view_snapshot(self.session, npc))
        panel = self._build(self.session, npc)
        self.assertEqual((panel["category"], panel["selected"]), ("monster", f"portrait:monster:{T_A}"))

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_puppeting_another_owner_retires_the_view(self):
        session = self._session()
        select_gallery_category(session, self.actor, "monster")
        other = self._add_character("測者乙")
        SIGNAL_OBJECT_POST_PUPPET.send(sender=other, session=session, account=self.account)
        self.assertIsNone(session.ndb.gallery_view)
        # Returning to the first character starts fresh rather than reviving it.
        session.puppet = self.actor
        SIGNAL_OBJECT_POST_PUPPET.send(sender=self.actor, session=session, account=self.account)
        self.assertEqual(self._build(session)["category"], "mine")
        # A companion whose bound owner cannot be resolved owns no view.
        select_gallery_category(session, self.actor, "monster")
        stray = create_object(NPC, key="無主同伴", location=self.room1)
        stray.db.possessed_by = self.actor.pk
        SIGNAL_OBJECT_POST_PUPPET.send(sender=stray, session=session, account=self.account)
        self.assertIsNone(session.ndb.gallery_view)
        # An unexpected owner failure clears the view and never breaks puppeting.
        session.ndb.gallery_view = GalleryViewSelection(self.actor.pk, "monster", ())
        with patch(
            "web.webclient.presentation.gallery_selection.gallery_owner",
            side_effect=RuntimeError("t_synthetic_failure"),
        ), patch("web.webclient.presentation.gallery_selection.log_warn") as warn:
            SIGNAL_OBJECT_POST_PUPPET.send(sender=self.actor, session=session, account=self.account)
        self.assertIsNone(session.ndb.gallery_view)
        self.assertEqual(warn.call_args.args[0], "gallery_view_retire_failed")
        # The snapshot itself refuses a view of another owner.
        session.ndb.gallery_view = GalleryViewSelection(other.pk, "monster", ())
        self.assertIsNone(gallery_view_snapshot(session, self.actor))

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-selection-is-remembered-per-category-with-fallbacks"
    )
    def test_unknown_or_disabled_targets_are_refused_without_a_write(self):
        self._companion("同行甲", "t_v4_companion_a")
        record_species_sighting(self.actor, T_A)
        session = self._session()
        select_gallery_category(session, self.actor, "party")
        stored = session.ndb.gallery_view
        for category in ("scene", "t_unknown", None):
            with patch.dict(gallery_categories.DISABLED_REASONS, {"scene": "測試停用"}):
                result = select_gallery_category(session, self.actor, category)
            self.assertEqual(
                result,
                {"outcome": "rejected", "code": "unknown_category", "message": "找不到此圖庫分類"},
            )
            self.assertIs(session.ndb.gallery_view, stored)
        # Listed in another enabled category, but not in the selected one.
        for subject_key in (f"portrait:monster:{T_A}", "portrait:character:t_v4_actor", 7):
            result = select_gallery_subject(session, self.actor, subject_key)
            self.assertEqual(
                result,
                {"outcome": "rejected", "code": "unknown_subject", "message": "找不到此圖庫對象"},
            )
            self.assertIs(session.ndb.gallery_view, stored)
        # A session that is not this actor's webclient writes nothing either.
        telnet = self._session()
        telnet.protocol_key = "telnet"
        self.assertEqual(select_gallery_category(telnet, self.actor, "monster")["code"], "unknown_category")
        self.assertIsNone(telnet.ndb.__dict__.get("gallery_view"))


ROOT = Path(__file__).resolve().parents[4]
T_ARCH = "t_arch"
T_OTHER = "t_other"
T_ARCH_SENTENCE = "測試用的林間空地，霧氣低垂。"
SCENE_EXTRA = {
    "archetypes": {
        T_ARCH: make_archetype(T_ARCH, display_name_zh="甲測景", scene_sentence=T_ARCH_SENTENCE),
        T_OTHER: make_archetype(T_OTHER, display_name_zh="乙測景"),
    },
}


def _bundled_image(key):
    """One synthetic admitted bundled scene illustration."""
    fingerprint = hashlib.sha256(f"bundled:{key}".encode("utf-8")).hexdigest()
    return scene_definitions.BundledSceneImage(
        key=key,
        identity=f"{scene_definitions.BUNDLED_SCENE_IDENTITY_PREFIX}{key}/{fingerprint}"
        f"{scene_definitions.BUNDLED_SCENE_EXTENSION}",
        filename=scene_definitions.bundled_asset_filename(key),
        fingerprint=fingerprint,
        image_size={"width": 16, "height": 9},
    )


def _client_verdict(panel):
    """``ok`` when the client mirror's validator accepts ``panel``, else its error."""
    script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
try { protocol.validateGalleryPanel(JSON.parse(fs.readFileSync(0, 'utf8'))); process.stdout.write('ok'); }
catch (error) { process.stdout.write(String(error.message)); }
"""
    output = subprocess.run(
        ["node", "-e", script], input=json.dumps(panel), text=True, capture_output=True, cwd=ROOT, check=True,
    )
    return output.stdout


@synthetic_registries("archetypes", extra=SCENE_EXTRA)
class GallerySceneProjectionTests(EvenniaTest):
    """Scene subjects carry the background in effect, their cards and their sentence."""

    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        definitions = {
            key: scene_definitions.SceneArtDefinition(key=key, terminal_key=T_OTHER)
            for key in (T_ARCH, T_OTHER)
        }
        catalog = scene_definitions.BundledSceneCatalog(
            {key: _bundled_image(key) for key in (T_ARCH, T_OTHER)}
        )
        for name, value in (("SCENE_ART_DEFINITIONS", definitions), ("_BUNDLED", catalog)):
            patcher = patch.object(scene_definitions, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.catalog = catalog
        self.registry = build_production_registry()
        self.actor = self.char1
        self.account.characters.add(self.actor)
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "t_scene_actor"}
        self.subject = ArtSubject(ArtSubjectKind.SCENE, T_ARCH)

    def _session(self):
        session = SimpleNamespace(
            ndb=SimpleNamespace(), puppet=self.actor,
            protocol_key="websocket", msg=lambda *args, **kwargs: None,
        )
        attach_coordinator(session, self.registry)
        return session

    def _scene_panel(self):
        # Entered inside the test's synthetic registry scope (setUp is outside
        # it, where the synthetic archetype is not registered).
        record_scene_entry(self.actor, T_ARCH)
        session = self._session()
        self.assertEqual(select_gallery_category(session, self.actor, "scene")["outcome"], "success")
        panel = gallery_presenter(build_presentation_context(session, self.actor))
        validate_gallery(panel)
        return panel

    def _card(self):
        image = str(uuid.UUID(int=7))
        identity = f"gallery/scene/{T_ARCH}/{image}.png"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        gallery_api.append_card(
            self.subject, image_id=image, stored_identity=identity, prompt=None, seed=None,
            checkpoint=None, requested_fields=[], binding=None, source="generated",
            created_at=200, image_size={"width": 1536, "height": 864},
        )
        return image, identity

    def test_a_scene_without_a_card_shows_its_bundled_image(self):
        panel = self._scene_panel()
        self.assertEqual((panel["category"], panel["selected"]), ("scene", f"scene:{T_ARCH}"))
        tile = panel["groups"][0]["subjects"][0]
        self.assertEqual((tile["kind"], tile["display_name"], tile["card_count"]), ("scene", "甲測景", 0))
        images = [entry for entry in tile["artwork"]["attempts"] if entry["type"] == "image"]
        self.assertEqual(images[0]["source_id"], descriptors.scene_bundled_source_id(T_ARCH))
        self.assertEqual(images[0]["resource"]["url"], self.catalog.url_for(T_ARCH))
        # An untrusted gallery identity authorizes no retained room pixels.
        self.assertEqual(tile["artwork"]["subject_id"], f"gallery:scene:{T_ARCH}")
        self.assertEqual(tile["artwork"]["retention_sources"], [])
        self.assertEqual(panel["cards"], [])
        self.assertEqual(panel["description"], T_ARCH_SENTENCE)
        self.assertEqual(
            (panel["capabilities"]["supports_face_rect"], panel["capabilities"]["max_cards"]), (False, 1)
        )
        self.assertEqual(_client_verdict(panel), "ok")

    def test_a_scene_card_row_is_a_landscape_original(self):
        image, identity = self._card()
        panel = self._scene_panel()
        tile = panel["groups"][0]["subjects"][0]
        self.assertEqual(tile["card_count"], 1)
        self.assertEqual(
            tile["artwork"]["attempts"][0]["source_id"],
            descriptors.scene_generated_source_id(f"scene:{T_ARCH}"),
        )
        [row] = panel["cards"]
        self.assertEqual((row["image_id"], row["status"], row["label"]), (image, "card", "背景"))
        self.assertEqual((row["is_default"], row["chips"]), (True, ["目前預設"]))
        [attempt] = row["artwork"]["attempts"]
        resource = attempt["resource"]
        self.assertTrue(resource["url"].startswith(f"/art/gallery/scene/{T_ARCH}/{image}"))
        self.assertEqual(resource["resource_id"], identity)
        self.assertEqual(
            resource["geometry"],
            {"image_size": {"width": 1536, "height": 864}, "face_rect": None, "stage": None, "aspect_ratio": "16:9"},
        )
        terminal = row["artwork"]["terminal"]
        self.assertEqual(terminal["kind"], descriptors.TERMINAL_SCENE_IMAGE)
        self.assertEqual(terminal["source_id"], descriptors.scene_terminal_source_id(T_ARCH))
        self.assertEqual(terminal["resource"]["url"], self.catalog.url_for(T_ARCH))
        self.assertEqual(_client_verdict(panel), "ok")

    def test_a_scene_card_without_an_admitted_bundled_image_has_no_terminal(self):
        self._card()
        partial = scene_definitions.BundledSceneCatalog({T_OTHER: _bundled_image(T_OTHER)})
        with patch.object(scene_definitions, "_BUNDLED", partial), \
                patch("world.art.presenter.log_warn") as warn:
            panel = self._scene_panel()
        self.assertIsNone(panel["cards"][0]["artwork"]["terminal"])
        self.assertIn("gallery_scene_terminal_missing", [call.args[0] for call in warn.call_args_list])
        self.assertEqual(_client_verdict(panel), "ok")

    def test_non_scene_subjects_carry_no_description(self):
        panel = gallery_presenter(build_presentation_context(self._session(), self.actor))
        validate_gallery(panel)
        self.assertEqual((panel["category"], panel["selected"]), ("mine", "portrait:character:t_scene_actor"))
        self.assertIsNone(panel["description"])
