"""Exact ``art`` schema, presenter, and surface-isolation tests (tasks 2.3, 7.1).

Covers the version-1 payload validation, scene done/missing/pending/failed/
scheduler-disabled/missing-file states, same-origin URL only, combat catalog
mirroring ``context_actions`` participants, exploration present-entity catalog
contents, gate-rejected entries as unavailable placeholders with no URL,
creation-mode unavailable form, presenter isolation, and the worst-case
serialization size.
"""

from pathlib import Path
import base64
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.art import (
    ART_SCHEMA_VERSION,
    MAX_MEDIA_URL,
    ArtPanelError,
    validate_art,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.art import descriptors
from world.art.fallback_keys import FALLBACK_KEYS
from world.art.gallery import record_for as gallery_record_for
from world.art.official import load_catalog, reset_catalog
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.queue import claim, ensure, record_key, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.lore.monster_visuals import BASELINE_VISUAL_ROWS
from world.rules.dialogue import GUILD_STAFF_DIALOGUE_KEY
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_ARCHETYPES
from world.rules.combat_session import engage
from world.rules.tests.combat_fixtures import BattlefieldIsolation


# The canonical scene descriptor the v4 wrapper carries: the room-aware source
# chain's own facts, built through the frozen descriptor vocabulary so the
# fixture can never drift from the wire contract.
def _scene_artwork(**overrides):
    value = descriptors.descriptor(
        subject_id="place:t_synth_room",
        generation_subject="scene:t_synth_bazaar",
        generation_state=descriptors.GENERATION_DONE,
        attempts=[
            descriptors.image_attempt(
                descriptors.scene_generated_source_id("scene:t_synth_bazaar"),
                descriptors.SCENE_RANK_GENERATED,
                _valid_resource(
                    resource_id="scene/t_synth_bazaar.png",
                    version=_fingerprint("scene-output"),
                    url=f"/art/scene/t_synth_bazaar.png?v={_fingerprint('scene-output')}",
                    origin="runtime",
                    geometry={
                        "image_size": None,
                        "face_rect": None,
                        "stage": None,
                        "aspect_ratio": None,
                    },
                ),
            ),
            descriptors.fault_attempt(
                descriptors.scene_bundled_source_id("t_synth_bazaar"),
                descriptors.SCENE_RANK_BUNDLED,
                descriptors.REASON_REQUIRED_RESOURCE_MISSING,
            ),
        ],
        terminal_payload=None,
        retention_sources=[
            descriptors.retention_source(
                descriptors.scene_generated_source_id("scene:t_synth_bazaar"),
                _fingerprint("scene-retention"),
            )
        ],
    )
    value.update(overrides)
    return value


def _valid_scene(**overrides):
    value = {
        "archetype": "t_synth_bazaar",
        "label": T_BAZAAR_LABEL,
        "alt": T_BAZAAR_LABEL,
        "artwork": _scene_artwork(),
    }
    value.update(overrides)
    return value


def _fingerprint(label: str) -> str:
    """A deterministic 64-character lowercase digest for one fixture fact."""
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


# The canonical artwork descriptor vocabulary the migrated wire carries: one
# closed fact set shared by the art catalog entry and the roster row portrait.
# The revision and the resource versions are real digests of their own fixture
# label; the validators bound their SHAPE and no reader recomputes them.
SILHOUETTE_FACE_RECT = {"x": 0.3403, "y": 0.02, "w": 0.3194, "h": 0.18}


def _valid_resource(**overrides):
    value = {
        "resource_id": "portrait/monster/low.png",
        "version": _fingerprint("resource"),
        "url": "/art/portrait/monster/low.png",
        "origin": "runtime",
        "geometry": {
            "image_size": {"width": 864, "height": 1536},
            "face_rect": {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5},
            "stage": {"scale": 1.0, "x": 0.0, "y": 0.0},
            "aspect_ratio": "3:4",
        },
    }
    value.update(overrides)
    return value


def _silhouette_terminal(**overrides):
    """The committed silhouette alpha mask at its own terminal rank."""
    value = {
        "kind": "alpha_mask",
        "source_id": "portrait.alpha:monster_anon",
        "rank": 100,
        "resource": _valid_resource(
            resource_id="defaults/monster_anon.webp",
            version=_fingerprint("terminal"),
            url="/art/defaults/monster_anon.webp",
            origin="silhouette",
            geometry={
                "image_size": None,
                "face_rect": dict(SILHOUETTE_FACE_RECT),
                "stage": None,
                "aspect_ratio": "3:4",
            },
        ),
    }
    value.update(overrides)
    return value


def _valid_artwork(**overrides):
    """One complete canonical descriptor with a resolved runtime candidate."""
    value = {
        "subject_id": "portrait:monster:low",
        "revision": _fingerprint("revision"),
        "generation_subject": "portrait:monster:low",
        "generation_state": "done",
        "attempts": [
            {
                "type": "image",
                "source_id": "portrait.default:1",
                "rank": 30,
                "resource": _valid_resource(),
            }
        ],
        "terminal": _silhouette_terminal(),
        "retention_sources": [],
    }
    value.update(overrides)
    return value


def _valid_catalog_entry(**overrides):
    value = {
        "artwork": _valid_artwork(),
        "context": {"name": "哥布林", "role": "敵方"},
    }
    value.update(overrides)
    return value


def _silhouette_entry(**overrides):
    """A truthful admitted row with no real candidate and its alpha terminal."""
    artwork = _valid_artwork(
        subject_id="portrait:character:42",
        generation_subject=None,
        generation_state="missing",
        attempts=[],
    )
    return _valid_catalog_entry(artwork=artwork, **overrides)


def _bare_placeholder_entry(**overrides):
    """An admitted row with neither a candidate nor a built-in identity."""
    artwork = _valid_artwork(
        subject_id="portrait:character:42",
        generation_subject=None,
        generation_state=None,
        attempts=[],
        terminal=None,
    )
    return _valid_catalog_entry(artwork=artwork, **overrides)


def _official_entry(**overrides):
    """A resolved official default: the mounted catalog's read-only image.

    It is a real image but never a generated asset, so its own candidate
    carries the ``official`` origin; recorded generation truth stays an
    independent fact of the descriptor (``official-art-resolution``).
    """
    artwork = _valid_artwork(
        subject_id="portrait:character:42",
        generation_subject="portrait:character:42",
        generation_state=None,
        attempts=[
            {
                "type": "image",
                "source_id": "portrait.official:preset/t_synth_preset",
                "rank": 50,
                "resource": _valid_resource(
                    resource_id="preset/t_synth_preset/hero.webp",
                    version=_fingerprint("official"),
                    url="/art/official/" + "a" * 64 + "/preset/t_synth_preset/hero.webp",
                    origin="official",
                    geometry={
                        "image_size": None,
                        "face_rect": {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5},
                        "stage": {"scale": 1.4, "x": 0.1, "y": -0.2},
                        "aspect_ratio": "3:4",
                    },
                ),
            }
        ],
    )
    value = {
        "artwork": artwork,
        "context": {"name": "旅人", "role": "人物"},
    }
    value.update(overrides)
    return value


def _valid_payload(**overrides):
    value = {
        "schema_version": ART_SCHEMA_VERSION,
        "available": True,
        "kind": "scene",
        "scene": _valid_scene(),
        "portrait_catalog": {"42": _valid_catalog_entry()},
    }
    value.update(overrides)
    return value


T_BAZAAR = "t_synth_bazaar"
T_BAZAAR_LABEL = SYNTH_ARCHETYPES[T_BAZAAR].display_name_zh
# Monster art membership is a registered VISUAL species key, resolved at
# runtime from the authored baseline rows (never a threat-tier value).
_MONSTER_VISUAL_KEY = BASELINE_VISUAL_ROWS[0].stable_key

# A deterministic decodable 1x1 PNG: the official catalog admits an image from
# its header alone, which is all this surface needs.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class ArtSchemaTests(unittest.TestCase):
    def test_minimal_available_payload_passes(self):
        normalized = validate_art(_valid_payload())
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["schema_version"], ART_SCHEMA_VERSION)
        self.assertEqual(normalized["kind"], "scene")

    def test_unknown_or_missing_fields_reject(self):
        payload = _valid_payload(bogus=1)
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload()
        del payload["portrait_catalog"]
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_wrong_version_kind_availability_reject(self):
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(schema_version=1))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(schema_version=2))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(schema_version=3))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(schema_version=5))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(available=False))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(kind="combat"))

    def test_scene_media_url_must_be_same_origin(self):
        """A scene candidate's URL obeys the shared same-origin media route."""
        for url in ("https://evil.test/x.png", "/tmp/out.png"):
            with self.subTest(url=url):
                resource = _valid_resource(
                    resource_id="scene/t_synth_bazaar.png",
                    version=_fingerprint("scene-output"),
                    url=url,
                    origin="runtime",
                    geometry={
                        "image_size": None,
                        "face_rect": None,
                        "stage": None,
                        "aspect_ratio": None,
                    },
                )
                payload = _valid_payload(
                    scene=_valid_scene(
                        artwork=_scene_artwork(
                            attempts=[
                                descriptors.image_attempt(
                                    descriptors.scene_generated_source_id(
                                        "scene:t_synth_bazaar"
                                    ),
                                    descriptors.SCENE_RANK_GENERATED,
                                    resource,
                                )
                            ]
                        )
                    )
                )
                with self.assertRaises(Exception):
                    validate_art(payload)

    def test_scene_is_exactly_the_v4_wrapper(self):
        """The retired flat scene fields are rejected, never adapted."""
        normalized = validate_art(_valid_payload())
        self.assertEqual(
            set(normalized["scene"]), {"archetype", "label", "alt", "artwork"}
        )
        # An archetype-less scene is a valid wrapper (the malformed-metadata
        # case the descriptor itself states), never a missing field.
        validate_art(_valid_payload(scene=_valid_scene(archetype=None)))
        for retired, value in (
            ("url", "/art/scene/t_synth_bazaar.png"),
            ("subject_key", "scene:t_synth_bazaar"),
            ("status", "done"),
            ("aspect_ratio", "16:9"),
            ("stage", {"scale": 1.0, "x": 0.0, "y": 0.0}),
            ("placeholder", None),
        ):
            with self.subTest(retired=retired):
                with self.assertRaises(Exception):
                    validate_art(_valid_payload(scene=_valid_scene(**{retired: value})))
        # A scene wrapper without its descriptor is not an available scene.
        payload = _valid_payload(scene=_valid_scene())
        del payload["scene"]["artwork"]
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_catalog_keys_must_be_decimal_strings(self):
        payload = _valid_payload(portrait_catalog={"abc": _valid_catalog_entry()})
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload(portrait_catalog={42: _valid_catalog_entry()})
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_catalog_context_role_is_stable(self):
        payload = _valid_payload(
            portrait_catalog={
                "42": _valid_catalog_entry(context={"name": "x", "role": "boss"})
            }
        )
        with self.assertRaises(Exception):
            validate_art(payload)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_both_artwork_vocabularies_are_canonical(self):
        """One payload carries canonical descriptors in BOTH vocabularies.

        The scene is exactly ``{archetype, label, alt, artwork}`` — the
        room-aware descriptor the scene resolution produced — and the catalog
        value is exactly ``{artwork, context}`` with the same seven descriptor
        keys, so no surface sees a second, flat artwork vocabulary.
        """
        payload = validate_art(_valid_payload())
        self.assertEqual(
            set(payload["scene"]),
            {"archetype", "label", "alt", "artwork"},
        )
        self.assertEqual(
            set(payload["scene"]["artwork"]),
            {
                "subject_id",
                "revision",
                "generation_subject",
                "generation_state",
                "attempts",
                "terminal",
                "retention_sources",
            },
        )
        entry = payload["portrait_catalog"]["42"]
        self.assertEqual(set(entry), {"artwork", "context"})
        self.assertEqual(
            set(entry["artwork"]),
            {
                "subject_id",
                "revision",
                "generation_subject",
                "generation_state",
                "attempts",
                "terminal",
                "retention_sources",
            },
        )
        # The retired flat portrait vocabulary appears nowhere in the payload.
        flat = json.dumps(payload, ensure_ascii=False)
        # (a resource legitimately carries its own ``origin``; the retired
        # FLAT portrait and scene fields do not appear)
        for retired in (
            '"subject_key": "portrait:monster:low"',
            '"fallback"',
            '"placeholder": {"kind"',
            '"status": "done"',
        ):
            self.assertNotIn(retired, flat)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_version_and_catalog_keys_parity_with_the_client_mirror(self):
        """The registered version and the catalog key set agree across mirrors.

        The client validator corpus is the shipped module graph, so scanning
        its source text is the parity check: both sides register the same
        version, the allowlist row binds it, and the retired flat portrait
        vocabulary is gone from the mirror.
        """
        from tools.protocol_client_source import protocol_client_source

        source = protocol_client_source()
        self.assertIn(f"ART_SCHEMA_VERSION = {ART_SCHEMA_VERSION}", source)
        self.assertIn("art: ART_SCHEMA_VERSION", source)
        self.assertIn(
            'requireExactFields(value, "art catalog entry", ["artwork", "context"], [])',
            source,
        )
        for retired in (
            "ART_ORIGINS",
            "ART_MAX_FALLBACK_KEY",
            "validateArtFallback",
            "validatePortraitOrigin",
        ):
            self.assertNotIn(retired, source)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_catalog_geometry_is_exact_per_resource(self):
        """Each resource carries its own bounded geometry; a placeholder carries none."""
        def geometry_with(face_rect):
            return {
                "image_size": None,
                "face_rect": face_rect,
                "stage": None,
                "aspect_ratio": "3:4",
            }

        for bad in (
            geometry_with({"x": 0.25, "y": 0.06, "w": 0.5}),  # missing h
            geometry_with({"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5, "z": 0}),  # extra key
            geometry_with({"x": -0.1, "y": 0.06, "w": 0.5, "h": 0.5}),  # below 0
            geometry_with({"x": 1.5, "y": 0.06, "w": 0.5, "h": 0.5}),  # above 1
            geometry_with({"x": "0.25", "y": 0.06, "w": 0.5, "h": 0.5}),  # not a number
            geometry_with({"x": True, "y": 0.06, "w": 0.5, "h": 0.5}),  # bool is not a number
            {"image_size": None, "face_rect": None, "stage": None},  # missing aspect_ratio
        ):
            with self.subTest(bad=bad):
                payload = _valid_payload(
                    portrait_catalog={
                        "42": _valid_catalog_entry(
                            artwork=_valid_artwork(
                                attempts=[
                                    {
                                        "type": "image",
                                        "source_id": "portrait.default:1",
                                        "rank": 30,
                                        "resource": _valid_resource(geometry=bad),
                                    }
                                ]
                            )
                        )
                    }
                )
                with self.assertRaises(Exception):
                    validate_art(payload)
        # An admitted row with no real candidate carries no real geometry, and
        # its separate alpha terminal keeps its own.
        normalized = validate_art(
            _valid_payload(portrait_catalog={"42": _bare_placeholder_entry()})
        )
        entry = normalized["portrait_catalog"]["42"]["artwork"]
        self.assertEqual(entry["attempts"], [])
        self.assertIsNone(entry["terminal"])
        normalized = validate_art(
            _valid_payload(portrait_catalog={"42": _silhouette_entry()})
        )
        entry = normalized["portrait_catalog"]["42"]["artwork"]
        self.assertEqual(entry["attempts"], [])
        self.assertEqual(entry["terminal"]["kind"], "alpha_mask")
        self.assertEqual(entry["terminal"]["resource"]["geometry"]["face_rect"], SILHOUETTE_FACE_RECT)

    @covers_requirement(
        "official-art-resolution::every-presentation-payload-distinguishes-official-runtime-and-silhouette-origin"
    )
    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_catalog_origin_is_the_closed_vocabulary(self):
        # Each RESOURCE names the branch that produced its own bytes, so no
        # client inspects the URL to tell them apart.
        for origin, entry, path in (
            ("runtime", _valid_catalog_entry(), ("attempts", 0, "resource")),
            # The official read-only default: its own fingerprinted URL
            # (official-art-resolution).
            ("official", _official_entry(), ("attempts", 0, "resource")),
            ("silhouette", _silhouette_entry(), ("terminal", "resource")),
        ):
            with self.subTest(origin=origin):
                normalized = validate_art(_valid_payload(portrait_catalog={"42": entry}))
                resource = normalized["portrait_catalog"]["42"]["artwork"]
                for step in path:
                    resource = resource[step]
                self.assertEqual(resource["origin"], origin)
        for rejected in (None, "", "runtime ", "generated"):
            with self.subTest(origin=rejected):
                with self.assertRaises(ProtocolValidationError):
                    validate_art(
                        _valid_payload(
                            portrait_catalog={
                                "42": _valid_catalog_entry(
                                    artwork=_valid_artwork(
                                        attempts=[
                                            {
                                                "type": "image",
                                                "source_id": "portrait.default:1",
                                                "rank": 30,
                                                "resource": _valid_resource(origin=rejected),
                                            }
                                        ]
                                    )
                                )
                            }
                        )
                    )
        absent = _valid_resource()
        absent.pop("origin")
        with self.assertRaises(ProtocolValidationError):
            validate_art(
                _valid_payload(
                    portrait_catalog={
                        "42": _valid_catalog_entry(
                            artwork=_valid_artwork(
                                attempts=[
                                    {
                                        "type": "image",
                                        "source_id": "portrait.default:1",
                                        "rank": 30,
                                        "resource": absent,
                                    }
                                ]
                            )
                        )
                    }
                )
            )

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_an_official_candidate_keeps_its_own_origin(self):
        # An official image is a real image, so its candidate carries its own
        # fingerprinted same-origin URL under the ``official`` origin, while
        # the subject's recorded generation truth stays an independent fact of
        # the descriptor (never erased, never invented by the image's origin).
        normalized = validate_art(
            _valid_payload(portrait_catalog={"42": _official_entry()})
        )
        artwork = normalized["portrait_catalog"]["42"]["artwork"]
        candidate = artwork["attempts"][0]["resource"]
        self.assertEqual(candidate["origin"], "official")
        self.assertTrue(candidate["url"].startswith("/art/official/"))
        self.assertIsNone(artwork["generation_state"])
        self.assertEqual(artwork["generation_subject"], "portrait:character:42")
        # The same descriptor with a recorded pending generation is truthful
        # too: a read-only catalog default cannot complete or erase the
        # subject's own generation.
        normalized = validate_art(
            _valid_payload(
                portrait_catalog={
                    "42": _official_entry(
                        artwork=_valid_artwork(
                            subject_id="portrait:character:42",
                            generation_subject="portrait:character:42",
                            generation_state="pending",
                            attempts=_official_entry()["artwork"]["attempts"],
                        )
                    )
                }
            )
        )
        self.assertEqual(
            normalized["portrait_catalog"]["42"]["artwork"]["generation_state"],
            "pending",
        )
        cases = {
            # An official identity embeds an operator-chosen filename, so its
            # URL stays inside the shared 256 ceiling: one past it is refused
            # rather than shipped to a panel that cannot present it.
            "an official resource past the media ceiling": _valid_catalog_entry(
                artwork=_valid_artwork(
                    attempts=[
                        {
                            "type": "image",
                            "source_id": "portrait.official:preset/t_synth_preset",
                            "rank": 50,
                            "resource": _valid_resource(
                                version=_fingerprint("over"),
                                url="/art/" + "p" * (256 - len("/art/") + 1),
                                origin="official",
                            ),
                        }
                    ]
                )
            ),
        }
        for label, entry in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ProtocolValidationError):
                    validate_art(_valid_payload(portrait_catalog={"42": entry}))

    def test_the_wire_media_url_bound_matches_the_presenter_ceiling(self):
        # The official step presents a URL only inside the one ceiling both
        # panel validators apply; the two constants must never drift.
        from world.art.presenter import MAX_PORTRAIT_MEDIA_URL

        self.assertEqual(MAX_MEDIA_URL, MAX_PORTRAIT_MEDIA_URL)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_the_alpha_terminal_is_a_separate_decorative_fallback(self):
        # A row with no real candidate carries NO real geometry and NO
        # generation claim, while its terminal keeps its own identity and
        # rectangle: the silhouette is a fallback, never the row's own image.
        entry = _silhouette_entry()
        artwork = entry["artwork"]
        self.assertEqual(artwork["attempts"], [])
        self.assertIsNone(artwork["generation_subject"])
        self.assertEqual(artwork["generation_state"], "missing")
        terminal = artwork["terminal"]
        self.assertEqual(terminal["kind"], "alpha_mask")
        self.assertEqual(terminal["resource"]["origin"], "silhouette")
        self.assertTrue(terminal["resource"]["url"].startswith("/art/defaults/"))
        normalized = validate_art(_valid_payload(portrait_catalog={"42": entry}))
        self.assertEqual(normalized["portrait_catalog"]["42"], entry)
        # A resolved real row keeps the terminal BESIDE its own candidate, so a
        # browser whose real image fails still has the committed silhouette.
        normalized = validate_art(
            _valid_payload(portrait_catalog={"42": _valid_catalog_entry()})
        )
        carried = normalized["portrait_catalog"]["42"]["artwork"]
        self.assertEqual(
            carried["attempts"][0]["resource"]["url"], "/art/portrait/monster/low.png"
        )
        self.assertEqual(carried["attempts"][0]["resource"]["origin"], "runtime")
        self.assertEqual(carried["terminal"]["kind"], "alpha_mask")
        self.assertEqual(carried["generation_state"], "done")

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_the_terminal_is_coherent_and_never_a_second_candidate(self):
        rect = {"x": 0.3576, "y": 0.03, "w": 0.2847, "h": 0.16}
        # An admitted row with neither a candidate nor a terminal stays legal
        # (an entity whose attributes select no built-in identity).
        validate_art(
            _valid_payload(portrait_catalog={"42": _bare_placeholder_entry()})
        )
        cases = {
            "a terminal past the silhouette media ceiling": _valid_catalog_entry(
                artwork=_valid_artwork(
                    terminal=_silhouette_terminal(
                        resource=_valid_resource(
                            resource_id="defaults/man.webp",
                            version=_fingerprint("bad-terminal"),
                            url="/art/" + "p" * (129 - len("/art/") + 1),
                            origin="silhouette",
                            geometry={
                                "image_size": None,
                                "face_rect": rect,
                                "stage": None,
                                "aspect_ratio": "3:4",
                            },
                        )
                    )
                )
            ),
            "a terminal with an unknown kind": _valid_catalog_entry(
                artwork=_valid_artwork(terminal=_silhouette_terminal(kind="cover"))
            ),
            "a terminal without a resource": _valid_catalog_entry(
                artwork=_valid_artwork(
                    terminal={
                        "kind": "alpha_mask",
                        "source_id": "portrait.alpha:man",
                        "rank": 100,
                    }
                )
            ),
            "a terminal duplicating the candidate's bytes": _valid_catalog_entry(
                artwork=_valid_artwork(terminal=_silhouette_terminal(resource=_valid_resource()))
            ),
            "a terminal with an out-of-range rectangle": _valid_catalog_entry(
                artwork=_valid_artwork(
                    terminal=_silhouette_terminal(
                        resource=_valid_resource(
                            resource_id="defaults/man.webp",
                            version=_fingerprint("rect"),
                            url="/art/defaults/man.webp",
                            origin="silhouette",
                            geometry={
                                "image_size": None,
                                "face_rect": {"x": 0.5, "y": 0.5, "w": 1.5, "h": 0.9},
                                "stage": None,
                                "aspect_ratio": "3:4",
                            },
                        )
                    )
                )
            ),
            "a fault attempt carrying a resource": _valid_catalog_entry(
                artwork=_valid_artwork(
                    attempts=[
                        {
                            "type": "fault",
                            "source_id": "portrait.default:1",
                            "rank": 30,
                            "reason": "generated_output_missing",
                            "resource": _valid_resource(),
                        }
                    ]
                )
            ),
        }
        for label, payload_entry in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ProtocolValidationError):
                    validate_art(_valid_payload(portrait_catalog={"42": payload_entry}))

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_catalog_url_bound_admits_the_worst_case_gallery_identity(self):
        # /art/ + gallery/<kind>/ + 64-code-point key + / + uuid36 + .avif
        # is the longest legal media URL (129 chars); classic identities
        # never exceeded ~97. The bound must admit it.
        worst = (
            "/art/gallery/character/"
            + "k" * 64
            + "/"
            + "0" * 36
            + ".avif"
        )
        self.assertEqual(len(worst), 129)

        def with_url(url):
            return _valid_payload(
                portrait_catalog={
                    "42": _valid_catalog_entry(
                        artwork=_valid_artwork(
                            attempts=[
                                {
                                    "type": "image",
                                    "source_id": "portrait.default:1",
                                    "rank": 30,
                                    "resource": _valid_resource(
                                        version=_fingerprint(url), url=url
                                    ),
                                }
                            ]
                        )
                    )
                }
            )

        normalized = validate_art(with_url(worst))
        self.assertEqual(
            normalized["portrait_catalog"]["42"]["artwork"]["attempts"][0]["resource"]["url"],
            worst,
        )
        # Each origin has its OWN ceiling: a runtime (gallery) identity is
        # bounded at 129 and an official one at the shared 256.
        runtime_boundary = "/art/" + "p" * (129 - len("/art/"))
        self.assertEqual(len(runtime_boundary), 129)
        normalized = validate_art(with_url(runtime_boundary))
        self.assertEqual(
            normalized["portrait_catalog"]["42"]["artwork"]["attempts"][0]["resource"]["url"],
            runtime_boundary,
        )
        with self.assertRaises(Exception):
            validate_art(with_url(runtime_boundary + "p"))

        def with_official_url(url):
            return _valid_payload(
                portrait_catalog={
                    "42": _valid_catalog_entry(
                        artwork=_valid_artwork(
                            attempts=[
                                {
                                    "type": "image",
                                    "source_id": "portrait.official:preset/t_synth_preset",
                                    "rank": 50,
                                    "resource": _valid_resource(
                                        version=_fingerprint(url),
                                        url=url,
                                        origin="official",
                                    ),
                                }
                            ]
                        )
                    )
                }
            )

        official_boundary = "/art/" + "p" * (256 - len("/art/"))
        self.assertEqual(len(official_boundary), 256)
        validate_art(with_official_url(official_boundary))
        with self.assertRaises(Exception):
            validate_art(with_official_url(official_boundary + "p"))

    def test_catalog_ceiling_and_byte_gate(self):
        entries = {
            str(index): _valid_catalog_entry() for index in range(1, 33)
        }
        payload = _valid_payload(portrait_catalog=entries)
        normalized = validate_art(payload)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)
        entries = {str(index): _valid_catalog_entry() for index in range(1, 34)}
        with self.assertRaises(Exception):
            validate_art(_valid_payload(portrait_catalog=entries))

    def test_worst_case_realistic_payload_fits_the_envelope(self):
        # Every entry carries the complete descriptor: an image candidate with
        # all four geometry facts, a reached fault at its own position, the
        # alpha terminal and a bounded retention authorization — the widest
        # realistic row the wire admits.
        entries = {
            str(index): _valid_catalog_entry(
                artwork=_valid_artwork(
                    subject_id=f"portrait:character:{index}",
                    generation_subject=f"portrait:character:{index}",
                    attempts=[
                        {
                            "type": "image",
                            "source_id": f"portrait.bound:{index}",
                            "rank": 10,
                            "resource": _valid_resource(
                                resource_id=f"portrait/character/{index}.png",
                                version=_fingerprint(f"resource-{index}"),
                                url=f"/art/portrait/character/{index}.png",
                            ),
                        },
                        {
                            "type": "fault",
                            "source_id": f"portrait.default:{index}",
                            "rank": 30,
                            "reason": "generated_output_missing",
                        },
                    ],
                    retention_sources=[
                        {
                            "source_id": f"portrait.classic:{index}",
                            "token": _fingerprint(f"retention-{index}"),
                        }
                    ],
                ),
                context={"name": "長名字" * 16, "role": "人物"},
            )
            for index in range(1, 33)
        }
        payload = _valid_payload(portrait_catalog=entries)
        normalized = validate_art(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)
        self.assertLess(size, 48 * 1024)


def _player(key="art player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.age = 22
    player.apparent_age = 22
    return player


def _monster(key="art goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.art_species_key = _MONSTER_VISUAL_KEY
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class ArtPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # Scene presentation re-validates the room archetype against the live
        # registry: run the surface on the kit archetype rows.
        open_synthetic_scope(self, "archetypes")
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)
        (self.root / "portrait" / "character").mkdir(parents=True, exist_ok=True)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.room = create_object(Room, key="art arena")
        self.room.scene_archetype = "t_synth_bazaar"
        # Supported map construction writes the logical place identity beside
        # the archetype; only an authored identity may authorize retained
        # display content, so the surface tests run on a real one.
        self.room.scene_identity = "place:t_synth_room"
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _context(self):
        return PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("art", self._context())

    def _write_asset(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    def _settle_done(self, subject, identity):
        ensure(subject, "desc")
        self._write_asset(identity)
        from world.art.queue import claim

        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_done_scene_renders_the_canonical_descriptor(self):
        self._settle_done(
            ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar"),
            "scene/t_synth_bazaar.png",
        )
        payload = self._render()
        self.assertTrue(payload["available"])
        scene = payload["scene"]
        self.assertEqual(set(scene), {"archetype", "label", "alt", "artwork"})
        self.assertEqual(scene["archetype"], "t_synth_bazaar")
        self.assertEqual(scene["label"], SYNTH_ARCHETYPES[T_BAZAAR].display_name_zh)
        self.assertEqual(scene["alt"], scene["label"])
        artwork = scene["artwork"]
        self.assertEqual(artwork["generation_subject"], "scene:t_synth_bazaar")
        self.assertEqual(artwork["generation_state"], descriptors.GENERATION_DONE)
        generated = [
            attempt
            for attempt in artwork["attempts"]
            if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
        ]
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0]["type"], "image")
        resource = generated[0]["resource"]
        self.assertTrue(resource["url"].startswith("/art/scene/t_synth_bazaar.png"))
        self.assertNotIn("http", resource["url"])
        self.assertEqual(resource["origin"], descriptors.ORIGIN_RUNTIME)
        # The generated source authorizes this scene's still-applicable output.
        self.assertEqual(
            [entry["source_id"] for entry in artwork["retention_sources"]],
            [descriptors.scene_generated_source_id("scene:t_synth_bazaar")],
        )
        self.assertNotIn("out_path", repr(payload))
        self.assertNotIn(self.root.as_posix(), repr(payload))

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_pending_and_failed_generation_states_are_truthful(self):
        from world.art.queue import claim

        subject = ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar")
        ensure(subject, "desc")
        claimed = claim(10)
        artwork = self._render()["scene"]["artwork"]
        # A claimed generation is the same player-visible fact as a queued one.
        self.assertEqual(artwork["generation_state"], descriptors.GENERATION_PENDING)
        self.assertEqual(
            [
                attempt
                for attempt in artwork["attempts"]
                if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
            ],
            [],
        )
        # The synthetic archetype ships no bundled illustration: the required
        # position states that fact instead of inventing a URL.
        bundled = [
            attempt
            for attempt in artwork["attempts"]
            if attempt["rank"] == descriptors.SCENE_RANK_BUNDLED
        ]
        self.assertEqual(len(bundled), 1)
        self.assertEqual(bundled[0]["type"], "fault")
        self.assertEqual(
            bundled[0]["reason"], descriptors.REASON_REQUIRED_RESOURCE_MISSING
        )

        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="boom",
        )
        artwork = self._render()["scene"]["artwork"]
        self.assertEqual(artwork["generation_state"], descriptors.GENERATION_FAILED)
        self.assertEqual(
            [
                attempt["reason"]
                for attempt in artwork["attempts"]
                if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
            ],
            [descriptors.REASON_GENERATION_FAILED],
        )

    @covers_requirement("webclient-art-panel::the-art-panel-accepts-the-normalized-in-flight-state")
    @covers_requirement("art-queue-worker::in-flight-generation-exposes-a-wire-stable-status")
    def test_claimed_record_renders_available_with_a_pending_placeholder(self):
        subject = ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar")
        ensure(subject, "desc")
        claim(10)
        payload = self._render()
        self.assertTrue(payload["available"])
        artwork = payload["scene"]["artwork"]
        self.assertEqual(artwork["generation_subject"], "scene:t_synth_bazaar")
        self.assertEqual(artwork["generation_state"], "pending")
        self.assertEqual(
            [
                attempt
                for attempt in artwork["attempts"]
                if attempt["type"] == "image"
                and attempt["rank"] == descriptors.SCENE_RANK_GENERATED
            ],
            [],
        )
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)

    def test_unresolvable_scene_archetype_states_the_configuration_failure(self):
        self.room.scene_archetype = None
        payload = self._render()
        scene = payload["scene"]
        self.assertIsNone(scene["archetype"])
        self.assertEqual(scene["label"], "場景")
        artwork = scene["artwork"]
        self.assertIsNone(artwork["generation_subject"])
        self.assertIsNone(artwork["generation_state"])
        self.assertEqual(artwork["retention_sources"], [])
        self.assertEqual(len(artwork["attempts"]), 1)
        fault = artwork["attempts"][0]
        self.assertEqual(fault["type"], "fault")
        self.assertEqual(
            fault["reason"], descriptors.REASON_CONFIGURATION_INVALID
        )
        self.assertEqual(fault["rank"], descriptors.SCENE_RANK_TERMINAL)

    def test_missing_file_for_done_record_is_a_reached_output_missing_fact(self):
        ensure(ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar"), "desc")
        from world.art.queue import claim

        claimed = claim(10)
        settle(
            ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar"),
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_bazaar.png",
            error=None,
        )
        # The file is never written, so the recorded output cannot be presented:
        # the generated position states that truth.
        payload = self._render()
        artwork = payload["scene"]["artwork"]
        generated = [
            attempt
            for attempt in artwork["attempts"]
            if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
        ]
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0]["type"], "fault")
        self.assertEqual(
            generated[0]["reason"], descriptors.REASON_GENERATED_OUTPUT_MISSING
        )
        self.assertEqual(artwork["retention_sources"], [])

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_combat_catalog_mirrors_context_actions_participants(self):
        monster = _monster()
        monster.location = self.room
        engage(self.player, monster)
        combat = self.registry.render(
            "context_actions", self._context()
        )
        payload = self._render()
        self.assertEqual(
            set(payload["portrait_catalog"]),
            {str(p["identity"]) for p in combat["participants"]},
        )
        for identity, entry in payload["portrait_catalog"].items():
            participant = next(
                p for p in combat["participants"] if str(p["identity"]) == identity
            )
            self.assertEqual(entry["context"]["name"], participant["display_name"])
            self.assertIn(entry["context"]["role"], ("隊友", "敵方"))
        monster_entry = payload["portrait_catalog"][str(monster.pk)]["artwork"]
        self.assertEqual(
            monster_entry["subject_id"], f"portrait:monster:{_MONSTER_VISUAL_KEY}"
        )
        self.assertEqual(
            monster_entry["generation_subject"], f"portrait:monster:{_MONSTER_VISUAL_KEY}"
        )

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_exploration_catalog_contains_hosts_and_named_policy(self):
        host = create_object(NPC, key="innkeeper", location=self.room)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        named = create_object(PlayerCharacter, key="named-guest")
        named.race = "human"
        named.apply_race_baseline()
        named.age = 30
        named.apparent_age = 30
        named.db.portrait_policy = {"mode": "named", "stable_key": "named-guest"}
        named.location = self.room
        monster = _monster(key="lurking-wolf")
        monster.location = self.room
        payload = self._render()
        catalog = payload["portrait_catalog"]
        self.assertIn(str(host.pk), catalog)
        self.assertIn(str(named.pk), catalog)
        self.assertNotIn(str(monster.pk), catalog)
        self.assertEqual(catalog[str(host.pk)]["context"]["role"], "對話對象")
        self.assertEqual(catalog[str(named.pk)]["context"]["role"], "人物")

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_ineligible_age_character_renders_placeholder_without_url(self):
        # age-range-0-10000 removed the adult gate: portrait eligibility is
        # subject-data quality. A character whose canonical age is missing
        # resolves only to the unavailable placeholder, and the diagnostic
        # naming the field never reaches the payload.
        incomplete = _player(key="ageless guest")
        incomplete.location = self.room
        incomplete.db.portrait_policy = {"mode": "named", "stable_key": "ageless-guest"}
        incomplete.db.age = None
        payload = self._render()
        entry = payload["portrait_catalog"][str(incomplete.pk)]["artwork"]
        # A refused subject exposes no real candidate and no generated subject
        # key: only the attribute-selected alpha terminal remains.
        self.assertEqual(entry["attempts"], [])
        self.assertIsNone(entry["generation_subject"])
        self.assertIsNone(entry["generation_state"])
        self.assertEqual(entry["terminal"]["kind"], "alpha_mask")
        self.assertNotIn("portrait rejected", repr(payload))

    def test_party_catalog_keeps_present_order_cap_and_controlled_companion(self):
        from world.rules.art_view import MAX_PORTRAIT_CATALOG
        from world.rules.party import join_party

        companions = [
            create_object(NPC, key=f"測試同行{index}", location=self.room)
            for index in range(3)
        ]
        for npc in companions:
            join_party(npc, self.player)
        companions[2].location = create_object(Room, key="測試遠室")
        host = create_object(NPC, key="測試職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY))
        catalog = self._render()["portrait_catalog"]
        self.assertEqual(list(catalog), [str(host.pk), *[str(n.pk) for n in companions[:2]]])
        self.assertEqual(catalog[str(companions[0].pk)]["artwork"]["attempts"], [])
        context = PresentationContext(actor=companions[1], protocol_version=1)
        self.assertIn(str(companions[1].pk), self.registry.render("art", context)["portrait_catalog"])
        for index in range(MAX_PORTRAIT_CATALOG - 1):
            named = create_object(NPC, key=f"測試人物{index}", location=self.room)
            named.db.portrait_policy = {"mode": "named", "stable_key": f"t_cap_{index}"}
        catalog = self._render()["portrait_catalog"]
        self.assertEqual(len(catalog), MAX_PORTRAIT_CATALOG)
        self.assertNotIn(str(companions[0].pk), catalog)
        self.assertNotIn(str(companions[1].pk), catalog)

    def test_creation_mode_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("scene", payload)
        self.assertNotIn("portrait_catalog", payload)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_resolved_catalog_entry_carries_its_candidate_geometry(self):
        # A resolved image entry's own candidate carries the media URL and the
        # normalized face rectangle inside its resource geometry
        # (art-gallery-resolution wire rule).
        from world.art.gallery import DEFAULT_FACE_RECT

        guest = _player(key="rect guest")
        guest.location = self.room
        guest.db.portrait_policy = {"mode": "named", "stable_key": "rect-guest"}
        self._settle_done(
            ArtSubject(ArtSubjectKind.CHARACTER, "rect-guest"),
            "portrait/character/rect-guest.png",
        )
        payload = self._render()
        artwork = payload["portrait_catalog"][str(guest.pk)]["artwork"]
        candidate = artwork["attempts"][0]
        self.assertEqual(candidate["source_id"], "portrait.classic:portrait:character:rect-guest")
        self.assertEqual(candidate["rank"], 40)
        resource = candidate["resource"]
        self.assertEqual(resource["url"], "/art/portrait/character/rect-guest.png")
        self.assertEqual(resource["origin"], "runtime")
        self.assertEqual(resource["geometry"]["face_rect"], dict(DEFAULT_FACE_RECT))
        self.assertEqual(artwork["generation_state"], "done")
        self.assertEqual(
            artwork["generation_subject"], "portrait:character:rect-guest"
        )
        # The scene wire block stays byte-identical: no face_rect key.
        self.assertNotIn("face_rect", payload["scene"])

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_a_policy_less_host_row_carries_the_attribute_selected_silhouette(self):
        host = create_object(NPC, key="barkeep", location=self.room)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        host.sex = "female"
        host.db.apparent_age = 30
        before = ArtAssetRecord.objects.count()
        payload = self._render()
        entry = payload["portrait_catalog"][str(host.pk)]["artwork"]
        # No real candidate and no generated subject key: the only fact is the
        # entity's own attribute-selected built-in alpha terminal, never one
        # shared shape.
        self.assertEqual(entry["attempts"], [])
        self.assertIsNone(entry["generation_subject"])
        self.assertEqual(entry["terminal"]["kind"], "alpha_mask")
        terminal = entry["terminal"]["resource"]
        self.assertEqual(terminal["origin"], "silhouette")
        self.assertEqual(terminal["url"], "/art/defaults/woman.webp")
        # The decoration installs nothing: no policy and no gallery record.
        self.assertIsNone(host.db.portrait_policy)
        self.assertEqual(ArtAssetRecord.objects.count(), before)

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_a_resolved_row_retains_its_alpha_terminal(self):
        guest = _player(key="reference guest")
        guest.location = self.room
        guest.db.portrait_policy = {"mode": "named", "stable_key": "reference-guest"}
        self._settle_done(
            ArtSubject(ArtSubjectKind.CHARACTER, "reference-guest"),
            "portrait/character/reference-guest.png",
        )
        payload = self._render()
        artwork = payload["portrait_catalog"][str(guest.pk)]["artwork"]
        candidate = artwork["attempts"][0]["resource"]
        self.assertEqual(candidate["origin"], "runtime")
        self.assertEqual(candidate["url"], "/art/portrait/character/reference-guest.png")
        # The alpha terminal rides beside the resolved image at its own rank,
        # for a browser-side load-failure re-render, without changing the
        # subject's generation truth.
        self.assertEqual(artwork["terminal"]["rank"], 100)
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        terminal = artwork["terminal"]["resource"]
        self.assertEqual(terminal["origin"], "silhouette")
        self.assertEqual(terminal["url"], "/art/defaults/" + terminal["resource_id"].split("/", 1)[1])
        self.assertEqual(artwork["generation_state"], "done")
        # The scene wrapper carries its own canonical descriptor; a portrait
        # row's facts never leak into it.
        self.assertEqual(
            sorted(payload["scene"]),
            ["alt", "archetype", "artwork", "label"],
        )

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    @covers_requirement("portrait-source-attempts::portrait-source-order-retains-current-policy")
    def test_canonical_source_enumeration_keeps_portraits_and_scenes_valid(self):
        # The internal portrait source enumerator ships NO alternate shape: the
        # registered panel contract still round-trips through its own validator
        # for a complete portrait descriptor and the unchanged scene block at
        # once.
        self._settle_done(
            ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar"),
            "scene/t_synth_bazaar.png",
        )
        guest = _player(key="enumeration guest")
        guest.location = self.room
        guest.db.portrait_policy = {"mode": "named", "stable_key": "enumeration-guest"}
        self._settle_done(
            ArtSubject(ArtSubjectKind.CHARACTER, "enumeration-guest"),
            "portrait/character/enumeration-guest.png",
        )
        normalized = validate_art(self._render())
        self.assertEqual(normalized["schema_version"], ART_SCHEMA_VERSION)
        self.assertEqual(normalized["kind"], "scene")
        artwork = normalized["portrait_catalog"][str(guest.pk)]["artwork"]
        candidate = artwork["attempts"][0]["resource"]
        self.assertEqual(candidate["origin"], "runtime")
        self.assertEqual(candidate["url"], "/art/portrait/character/enumeration-guest.png")
        self.assertEqual(artwork["generation_state"], "done")
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        scene_artwork = normalized["scene"]["artwork"]
        generated = [
            attempt
            for attempt in scene_artwork["attempts"]
            if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
        ]
        self.assertEqual(len(generated), 1)
        self.assertTrue(
            generated[0]["resource"]["url"].startswith("/art/scene/t_synth_bazaar.png")
        )
        self.assertEqual(
            sorted(normalized["scene"]),
            ["alt", "archetype", "artwork", "label"],
        )

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded")
    def test_a_present_entity_resolves_the_official_default_it_references(self):
        # The whole wire path for the official branch: a present named-policy
        # character whose preset provenance resolves the snapshot's default
        # image presents that read-only image, with no generated-portrait
        # claim and no gallery state acquired.
        from world.art import official, official_refs

        preset_key = "t_synth_preset"
        official_root = Path(self.tempdir.name).resolve() / "official"
        folder = official_root / "preset" / preset_key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "hero.png").write_bytes(TINY_PNG)
        guest = _player(key="official guest")
        guest.location = self.room
        guest.db.portrait_policy = {"mode": "named", "stable_key": "official-guest"}
        guest.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, preset_key)
        try:
            with (
                override_settings(ART_OFFICIAL_ROOT=str(official_root)),
                patch.object(
                    official_refs, "PLAYER_PRESET_REGISTRY", {preset_key: object()}
                ),
                patch.object(
                    official,
                    "_registered_preset_keys",
                    return_value=frozenset({preset_key}),
                ),
            ):
                load_catalog()
                entry = self._render()["portrait_catalog"][str(guest.pk)]
                self.assertEqual(entry["artwork"]["attempts"][0]["resource"]["origin"], "official")
        finally:
            reset_catalog()
        artwork = entry["artwork"]
        candidate = artwork["attempts"][0]["resource"]
        self.assertEqual(candidate["origin"], "official")
        self.assertEqual(artwork["subject_id"], "portrait:character:official-guest")
        self.assertTrue(candidate["url"].startswith("/art/official/"))
        self.assertIn("preset/t_synth_preset/hero.png", candidate["url"])
        self.assertEqual(sorted(candidate["geometry"]["face_rect"]), ["h", "w", "x", "y"])
        self.assertEqual(sorted(candidate["geometry"]["stage"]), ["scale", "x", "y"])
        # No mutable state claim: the subject's gallery is still empty.
        self.assertIsNone(
            gallery_record_for(
                ArtSubject(ArtSubjectKind.CHARACTER, "official-guest")
            )
        )

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_presenter_is_read_only(self):
        self._settle_done(
            ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar"),
            "scene/t_synth_bazaar.png",
        )
        before = {
            "hp": self.player.traits.hp.current,
            "active_combat": self.player.db.active_combat,
        }
        self._render()
        after = {
            "hp": self.player.traits.hp.current,
            "active_combat": self.player.db.active_combat,
        }
        self.assertEqual(before, after)

    def test_presenter_isolation_on_view_error(self):
        long_named = create_object(NPC, key="長" * 200, location=self.room)
        long_named.components.add(
            ScriptedDialogue.create(long_named, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "art_unavailable")


class ArtSnapshotIntegrationTests(BattlefieldIsolation, EvenniaTest):
    """Full-snapshot and combat-result atomicity integration (task 7.1)."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        # Snapshot rooms carry kit archetype keys; the combat path stays on
        # the live skill/monster data (no skills or monster-tier patching).
        open_synthetic_scope(self, "archetypes")
        super().setUp()
        import evennia
        from server.conf.tests.test_inputfuncs import _make_session

        self.sessionhandler = evennia.SESSION_HANDLER
        self.ws_session = _make_session(self.sessionhandler, "webclient/websocket")
        self.ws_session.puppet = self.char1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.age = 22
        self.char1.apparent_age = 22
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        super().tearDown()

    def _sync(self):
        from server.conf import inputfuncs

        self.sessionhandler.data_out.reset_mock()
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        return envelope

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_full_snapshot_includes_art_in_exploration_and_combat_modes(self):
        room = create_object(Room, key="snapshot arena")
        room.scene_archetype = "t_synth_bazaar"
        self.char1.location = room
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], True)
        self.assertEqual(envelope["panels"]["art"]["kind"], "scene")

        monster = _monster()
        monster.location = room
        engage(self.char1, monster)
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], True)
        self.assertIn(str(monster.pk), envelope["panels"]["art"]["portrait_catalog"])

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_full_snapshot_in_creation_mode_uses_the_unavailable_form(self):
        self.char1.db.creation_pending = True
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], False)
        self.assertNotIn("scene", envelope["panels"]["art"])

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_combat_result_publishes_status_context_actions_and_art_together(self):
        from server.conf import inputfuncs
        from web.webclient.actions.registry import build_production_action_registry
        from web.webclient.actions.dispatcher import handle_ui_action
        from web.webclient.presentation.registry import build_production_registry
        from world.rules.combat_session import read_session

        room = create_object(Room, key="atomic arena")
        room.scene_archetype = "t_synth_lodge"
        self.char1.location = room
        monster = _monster()
        monster.location = room
        engage(self.char1, monster)
        envelope = self._sync()
        coordinator = __import__(
            "web.webclient.presentation.coordinator", fromlist=["attach_coordinator"]
        ).attach_coordinator(self.ws_session, build_production_registry())
        # The dock's one confirming terminal route: the flee row only reaches
        # the party exit's confirmation boundary and rejects until the
        # confirmation window ships (webclient-party-exit-confirmation), while
        # Forfeit requests and confirms its surrender in one dispatch.
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "combat:1",
            "base_revision": envelope["revision"],
            "action_id": "combat.forfeit",
            "payload": {"session_id": read_session(self.char1).session_id},
        }
        self.sessionhandler.data_out.reset_mock()
        handle_ui_action(
            self.ws_session,
            self.char1,
            action,
            build_production_action_registry(),
            build_production_registry(),
        )
        # A terminal outcome (the confirmed surrender) publishes a full
        # snapshot: the mode flips back to exploration, so every mode-relevant
        # panel is replaced, including the art catalog without the session's
        # own monster.
        snapshots = [
            call.kwargs["ui_snapshot"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(snapshots, "a terminal combat action must publish a full snapshot")
        panels = snapshots[-1]["panels"]
        for name in ("status", "context_actions", "art", "exploration", "character", "services", "local_map"):
            self.assertIn(name, panels)
        # The ended session's participants leave the art catalog in the same
        # publication.
        catalog = panels["art"]["portrait_catalog"]
        self.assertNotIn(str(monster.pk), catalog)
        self.assertNotIn(str(self.char1.pk), catalog)
        updates = [
            call.kwargs["ui_update"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_update" in call.kwargs
        ]
        self.assertFalse(updates, "a terminal outcome must not publish a partial update")

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_text_command_refresh_snapshot_includes_the_art_panel(self):
        from server.conf import inputfuncs

        room = create_object(Room, key="refresh arena")
        room.scene_archetype = "t_synth_bazaar"
        self.char1.location = room
        deferred = __import__("twisted.internet.defer", fromlist=["Deferred"]).Deferred()
        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "server.conf.inputfuncs.cmdhandler", return_value=deferred
        ):
            inputfuncs.text(self.ws_session, "look")
            deferred.callback(None)
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(calls, "no refresh snapshot was emitted")
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["kind"], "scene")
        self.assertEqual(envelope["panels"]["art"]["scene"]["archetype"], "t_synth_bazaar")

    @covers_requirement(
        "webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes"
    )
    @covers_requirement(
        "webclient-art-panel::combat-portrait-references-and-catalog-are-committed-coherently"
    )
    def test_initial_engage_publishes_combat_art_catalog_in_same_revision(self):
        from web.webclient.actions.registry import build_production_action_registry
        from web.webclient.actions.dispatcher import handle_ui_action
        from web.webclient.presentation.registry import build_production_registry

        room = create_object(Room, key="coherent engage arena")
        room.scene_archetype = "t_synth_bazaar"
        self.char1.location = room
        monster = create_object(Monster, key="森林哥布林", location=room)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.art_species_key = "goblin"

        envelope = self._sync()
        coordinator = __import__(
            "web.webclient.presentation.coordinator", fromlist=["attach_coordinator"]
        ).attach_coordinator(self.ws_session, build_production_registry())
        self.sessionhandler.data_out.reset_mock()

        action = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "engage:1",
            "base_revision": coordinator.revision,
            "action_id": "explore.engage",
            "payload": {"monster_id": int(monster.pk)},
        }
        handle_ui_action(
            self.ws_session,
            self.char1,
            action,
            build_production_action_registry(),
            coordinator.registry,
        )

        # Verify that an update was emitted in one single revision before the action result
        updates = [
            call.kwargs["ui_update"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_update" in call.kwargs
        ]
        self.assertTrue(updates, "engage must publish an atomic update")
        committed = updates[-1]
        self.assertEqual(committed["mode"], "combat")
        panels = committed["panels"]
        for expected_panel in ("status", "context_actions", "dialogue", "art"):
            self.assertIn(expected_panel, panels)

        # Verify art panel has both participants
        art_panel = panels["art"]
        self.assertTrue(art_panel["available"])
        catalog = art_panel["portrait_catalog"]
        self.assertIn(str(monster.pk), catalog)
        self.assertIn(str(self.char1.pk), catalog)

        # The monster's admitted entry carries the complete descriptor: its
        # own species subject, no real candidate here, and the committed
        # ``monster_anon`` alpha terminal as the deterministic fallback.
        monster_entry = catalog[str(monster.pk)]["artwork"]
        # The descriptor names the monster's OWN registered visual species,
        # never a threat tier or a display name.
        species_key = getattr(monster, "species_key", None) or monster.art_species_key
        self.assertEqual(monster_entry["subject_id"], f"portrait:monster:{species_key}")
        self.assertEqual(monster_entry["attempts"], [])
        terminal = monster_entry["terminal"]["resource"]
        self.assertEqual(terminal["origin"], "silhouette")
        self.assertTrue(terminal["url"].startswith("/art/defaults/"))

        # Verify that the action result was emitted with matching revision and outcome success
        results = [
            call.kwargs["ui_action_result"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_action_result" in call.kwargs
        ]
        self.assertTrue(results, "engage must emit action result")
        self.assertEqual(results[-1]["outcome"], "success")

if __name__ == "__main__":
    unittest.main()
