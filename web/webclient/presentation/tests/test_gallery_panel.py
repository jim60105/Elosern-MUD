"""Gallery read-only projection, transport lifecycle, and executable wire parity."""

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from django.test import override_settings
from evennia.server.signals import SIGNAL_OBJECT_POST_PUPPET
from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.art import gallery as api
from world.art import descriptors
from world.art import official, official_refs
from world.art.official import current_catalog, load_catalog, reset_catalog
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.presenter import MAX_PORTRAIT_MEDIA_URL
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.gallery import (
    GALLERY_MAX_OFFICIAL_ENTRIES,
    GALLERY_MAX_OFFICIAL_IDENTITY,
    GALLERY_MAX_OFFICIAL_URL,
    GALLERY_MAX_PANEL_SUBJECTS,
    SLOT_LABELS,
    gallery_presenter,
    gallery_presenter_v3,
    gallery_subjects,
    validate_gallery,
    validate_gallery_v3,
)
from web.webclient.presentation.gallery_selection import (
    gallery_view_snapshot, select_gallery_category, select_gallery_subject_v4,
)
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.art.queue import enqueue_gallery_job, pending_gallery_jobs, settle_gallery_failed
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

ROOT = Path(__file__).resolve().parents[4]


def image_id(number):
    return str(uuid.UUID(int=number))


_OFFICIAL_FINGERPRINT = "a" * 64
_SUBJECT_KEY = "portrait:character:t_gallery"
_RECT = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
_SIZE = {"width": 1000, "height": 1000}
_STAGE = {"scale": 1, "x": 0, "y": 0}


def _digest(seed):
    """A stable 64-character digest for a synthetic fixture fact."""
    return hashlib.sha256(str(seed).encode("utf-8")).hexdigest()


def alpha_terminal(key="woman", rect=None):
    """The subject's committed silhouette as the descriptor's alpha terminal."""
    identity = f"defaults/{key}.webp"
    return descriptors.terminal(
        descriptors.TERMINAL_ALPHA_MASK,
        descriptors.gallery_alpha_source_id(key),
        descriptors.GALLERY_RANK_ALPHA,
        descriptors.resource(
            identity,
            descriptors.identity_version(identity),
            f"/art/defaults/{key}.webp",
            descriptors.ORIGIN_SILHOUETTE,
            geometry_payload=descriptors.geometry(
                face_rect=dict(rect or _RECT), aspect_ratio="3:4"
            ),
        ),
    )


def card_descriptor(
    number,
    *,
    url=None,
    face_rect=None,
    stage=None,
    image_size=None,
    fault=None,
    generation="done",
    terminal=True,
    subject_key=_SUBJECT_KEY,
):
    """One card row's canonical descriptor, built from the production vocabulary."""
    image = image_id(number)
    source = descriptors.gallery_original_source_id(image)
    if fault is not None:
        attempts = [
            descriptors.fault_attempt(source, descriptors.GALLERY_RANK_ORIGINAL, fault)
        ]
        retention = []
    else:
        identity = f"gallery/character/t_gallery/{image}.png"
        attempts = [
            descriptors.image_attempt(
                source,
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.resource(
                    identity,
                    descriptors.identity_version(identity),
                    url or f"/art/{identity}",
                    descriptors.ORIGIN_RUNTIME,
                    geometry_payload=descriptors.geometry(
                        image_size=dict(image_size or _SIZE),
                        face_rect=dict(face_rect or _RECT),
                        stage=dict(stage or _STAGE),
                        aspect_ratio="3:4",
                    ),
                ),
            )
        ]
        retention = [
            descriptors.retention_source(
                source, descriptors.retention_token(subject_key, subject_key, image)
            )
        ]
    return descriptors.descriptor(
        subject_id=f"{_digest(subject_key)}:{image}",
        generation_subject=subject_key,
        generation_state=generation,
        attempts=attempts,
        terminal_payload=alpha_terminal() if terminal else None,
        retention_sources=retention,
    )


def official_descriptor(
    identity="preset/t_gallery_preset/a.png",
    *,
    url=None,
    face_rect=None,
    image_size=None,
    stage=None,
    generation="done",
    terminal=True,
):
    """One official row's canonical descriptor: its exact admitted candidate."""
    source = descriptors.gallery_official_source_id(identity)
    return descriptors.descriptor(
        subject_id=f"{_digest(_SUBJECT_KEY)}:{descriptors.identity_version(identity)[:36]}",
        generation_subject=_SUBJECT_KEY,
        generation_state=generation,
        attempts=[
            descriptors.image_attempt(
                source,
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.resource(
                    identity,
                    _OFFICIAL_FINGERPRINT,
                    url or f"/art/official/{_OFFICIAL_FINGERPRINT}/{identity}",
                    descriptors.ORIGIN_OFFICIAL,
                    geometry_payload=descriptors.geometry(
                        image_size=dict(image_size or _SIZE),
                        face_rect=dict(face_rect or _RECT),
                        stage=stage,
                        aspect_ratio="3:4",
                    ),
                ),
            )
        ],
        terminal_payload=alpha_terminal() if terminal else None,
        retention_sources=[
            descriptors.retention_source(source, _digest(f"retention:{identity}"))
        ],
    )


def official_row(identity="preset/t_gallery_preset/a.png", **changes):
    """A file-local synthetic official row; the fingerprint is fixed."""
    row = {
        "identity": identity,
        "artwork": official_descriptor(identity),
        "is_current": False,
        "is_catalog_default": True,
    }
    row.update(changes)
    return row


def candidate(panel, index=0):
    """The rank-10 image candidate resource of one card row."""
    return panel["cards"][index]["artwork"]["attempts"][0]["resource"]


def geometry(panel, index=0):
    """The candidate geometry of one card row."""
    return candidate(panel, index)["geometry"]


def payload():
    """File-local synthetic character wire fixture, independent of shipped content."""
    return {
        "schema_version": 3, "available": True, "kind": "gallery",
        "subjects": [{"subject_key": _SUBJECT_KEY, "kind": "portrait:character", "display_name": "測試角色", "is_puppet": True}],
        "selected": _SUBJECT_KEY,
        "filters": {"all": 1, "defaults": 1, "bound": 0, "pending": 0, "failed": 0},
        "cards": [{
            "image_id": image_id(1), "status": "card", "label": "測試肖像",
            "artwork": card_descriptor(1), "is_default": True,
            "chips": ["預設臉框", "目前預設"], "requested_fields": ["appearance"],
            "binding_present": False, "created_at": 100,
        }],
        "equipment_summary": {
            "weapon_main": {"value": None, "display_name": "未裝備"},
            "weapon_off": {"value": None, "display_name": "未裝備"},
            "armor": {"value": None, "display_name": "未裝備"},
            "accessories": {"value": [], "display_names": [], "equipped_count": 0},
        },
        "capabilities": {"supports_bindings": True, "supports_field_selection": True, "supports_free_text": True, "supports_personal_official_preferences": True, "max_cards": None},
        "binding_warnings": [], "error_state": None, "official_entries": [],
    }


class GalleryWireTests(unittest.TestCase):
    """Parity of the dead version-3 validator pair (``validate_gallery_v3`` and
    its JS mirror ``validateGalleryPanelV3``), kept until ``gallery-v3-removal``.
    """

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-payload-is-exactly-version-mirrored-across-server-and-client"
    )
    def test_bidirectional_boundary_parity(self):
        cases = [("valid", payload(), True)]
        def add(name, modify, accepted=False):
            value = payload()
            modify(value)
            cases.append((name, value, accepted))
        add("unknown top key", lambda p: p.update(extra=1))
        add("unknown nested key", lambda p: p["cards"][0].update(extra=1))
        add("wrong schema boolean", lambda p: p.update(schema_version=True))
        add("integral numeric schema", lambda p: p.update(schema_version=3.0), True)
        add("unknown selection", lambda p: p.update(selected="portrait:character:absent"))
        add("surrogate", lambda p: p["subjects"][0].update(display_name="\ud800"))
        add("name at cap", lambda p: p["subjects"][0].update(display_name="𠮷" * 64), True)
        add("name over cap", lambda p: p["subjects"][0].update(display_name="𠮷" * 65))
        add("label at cap", lambda p: p["cards"][0].update(label="畫" * 128), True)
        add("label over cap", lambda p: p["cards"][0].update(label="畫" * 129))
        add("rect zero", lambda p: geometry(p)["face_rect"].update(w=0))
        add("rect overflow", lambda p: geometry(p)["face_rect"].update(x=0.9))
        add("rect boolean", lambda p: geometry(p)["face_rect"].update(x=True))
        add("stage boundary", lambda p: geometry(p).update(stage={"scale": 0.2, "x": -0.5, "y": 0.5}), True)
        add("stage scale too large", lambda p: geometry(p)["stage"].update(scale=2.01))
        add("stage bool", lambda p: geometry(p)["stage"].update(x=True))
        add("stage missing", lambda p: geometry(p).pop("stage"))
        add("stage null on card", lambda p: geometry(p).update(stage=None))
        add("image size zero", lambda p: geometry(p).update(image_size={"width": 0, "height": 100}))
        add("image size boolean", lambda p: geometry(p).update(image_size={"width": True, "height": 100}))
        add("image size over the decoded ceiling", lambda p: geometry(p).update(image_size={"width": 8192, "height": 8192}))
        add("geometry extra key", lambda p: geometry(p).update(extra=1))
        add("geometry missing key", lambda p: geometry(p).pop("aspect_ratio"))
        add("fractional timestamp", lambda p: p["cards"][0].update(created_at=100.125), True)
        add("timestamp boolean", lambda p: p["cards"][0].update(created_at=True))
        add("unsafe timestamp", lambda p: p["cards"][0].update(created_at=2**53))
        add("wrong count", lambda p: p["filters"].update(all=2))
        add("boolean count", lambda p: p["filters"].update(all=True))
        add("integral numeric count", lambda p: p["filters"].update(all=1.0), True)
        add("foreign URL", lambda p: candidate(p).update(url=f"/art/gallery/character/other/{image_id(1)}.png"))
        add("unsupported extension", lambda p: candidate(p).update(url=candidate(p)["url"] + ".svg"))
        add("jpg extension", lambda p: candidate(p).update(url=candidate(p)["url"][:-4] + ".jpg"), True)
        add("foreign origin", lambda p: candidate(p).update(origin="official"))
        add("unknown origin", lambda p: candidate(p).update(origin="placeholder"))
        add("foreign media host", lambda p: candidate(p).update(url="https://example.invalid/art/x.png"))
        add("media url traversal", lambda p: candidate(p).update(url="/art/../secret.png"))
        add("media url over the runtime ceiling", lambda p: candidate(p).update(url=f"/art/{'x' * 130}.png"))
        # A gallery runtime URL never carries a cache version: its 129-code-point
        # ceiling is what an exact card's own route needs, and the closed
        # `?v=<sha256>` form is a general-media affordance (the canonical
        # vocabulary and its Node gate cover it).
        add(
            "media url cache version over the gallery ceiling",
            lambda p: candidate(p).update(url=candidate(p)["url"] + f"?v={_digest('v')}"),
        )
        add(
            "media url foreign query",
            lambda p: candidate(p).update(url=candidate(p)["url"] + "?other=1"),
        )
        add("resource version short", lambda p: candidate(p).update(version="abc"))
        add("resource version upper", lambda p: candidate(p).update(version="A" * 64))
        add("resource identity over cap", lambda p: candidate(p).update(resource_id="x" * 257))
        add("attempt rank", lambda p: p["cards"][0]["artwork"]["attempts"][0].update(rank=20))
        add("attempt negative rank", lambda p: p["cards"][0]["artwork"]["attempts"][0].update(rank=-1))
        add("attempt source identity", lambda p: p["cards"][0]["artwork"]["attempts"][0].update(source_id=descriptors.gallery_original_source_id(image_id(2))))
        add("attempt unknown type", lambda p: p["cards"][0]["artwork"]["attempts"][0].update(type="video"))
        add("attempt extra key", lambda p: p["cards"][0]["artwork"]["attempts"][0].update(extra=1))
        add("attempts over cap", lambda p: p["cards"][0]["artwork"].update(attempts=[dict(p["cards"][0]["artwork"]["attempts"][0]) for _ in range(17)]))
        add("descriptor subject identity over cap", lambda p: p["cards"][0]["artwork"].update(subject_id="x" * 129))
        add("descriptor revision", lambda p: p["cards"][0]["artwork"].update(revision="C" * 64))
        add("descriptor unknown generation state", lambda p: p["cards"][0]["artwork"].update(generation_state="in_progress"))
        add("descriptor generation subject over cap", lambda p: p["cards"][0]["artwork"].update(generation_subject="x" * 129))
        add("descriptor missing key", lambda p: p["cards"][0]["artwork"].pop("retention_sources"))
        add("descriptor extra key", lambda p: p["cards"][0]["artwork"].update(extra=1))
        add("retention over cap", lambda p: p["cards"][0]["artwork"].update(retention_sources=[{"source_id": f"gallery.original:{i}", "token": _digest(i)} for i in range(17)]))
        add("retention token short", lambda p: p["cards"][0]["artwork"]["retention_sources"][0].update(token="abc"))
        add("retention duplicate source", lambda p: p["cards"][0]["artwork"].update(retention_sources=[dict(p["cards"][0]["artwork"]["retention_sources"][0])] * 2))
        # A known fault names its failed source and NEVER a URL: the entry has
        # no resource at all, so no URL can ride along.
        def fault_row(p, **changes):
            artwork = card_descriptor(1, fault="generated_output_missing")
            artwork.update(changes)
            p["cards"][0]["artwork"] = artwork
        add("known fault row", fault_row, True)
        add("known fault reason", lambda p: fault_row(p, attempts=[{**card_descriptor(1, fault="generated_output_missing")["attempts"][0], "reason": "not_a_reason"}]))
        add("known fault with a resource", lambda p: fault_row(p, attempts=[{**card_descriptor(1, fault="generated_output_missing")["attempts"][0], "resource": card_descriptor(1)["attempts"][0]["resource"]}]))
        add("known fault terminal", lambda p: fault_row(p, terminal=None))
        # The retired v2 flat fields are rejected outright.
        for field, value in (("url", None), ("face_rect", None), ("stage", None), ("image_size", None)):
            add(f"old flat field {field}", lambda p, field=field, value=value: p["cards"][0].update({field: value}))
        # A pending/failed row carries no image at all.
        def synthetic(p, status, generation):
            p["cards"] = [{
                "image_id": image_id(2), "status": status, "label": "肖像", "is_default": False,
                "chips": [], "requested_fields": [], "binding_present": False, "created_at": 200,
                "artwork": card_descriptor(2, fault=None, generation=generation, terminal=False, subject_key=_SUBJECT_KEY),
            }]
            p["cards"][0]["artwork"]["attempts"] = []
            p["cards"][0]["artwork"]["retention_sources"] = []
            p["filters"] = {
                "all": 1, "defaults": 0, "bound": 0,
                "pending": int(status == "pending"), "failed": int(status == "failed"),
            }
            p["error_state"] = (
                {"code": "sd_connection_error", "at": 200}
                if status == "failed"
                else None
            )
        add("pending row without an image", lambda p: synthetic(p, "pending", "pending"), True)
        add("failed row without an image", lambda p: synthetic(p, "failed", "failed"), True)
        def synthetic_with_image(p):
            synthetic(p, "pending", "pending")
            p["cards"][0]["artwork"]["attempts"] = card_descriptor(2)["attempts"]
        add("synthetic row fabricating an image", synthetic_with_image)
        def synthetic_with_terminal(p):
            synthetic(p, "pending", "pending")
            p["cards"][0]["artwork"]["terminal"] = alpha_terminal()
        add("synthetic row fabricating a terminal", synthetic_with_terminal)
        add("duplicate card", lambda p: p["cards"].append(deepcopy(p["cards"][0])))
        add("pending with URL", lambda p: p["cards"][0].update(status="pending"))
        add("unknown field", lambda p: p["cards"][0].update(requested_fields=["unknown"]))
        add("duplicate field", lambda p: p["cards"][0].update(requested_fields=["appearance", "appearance"]))
        # The relaxed wire carries whatever face chip the presenter committed,
        # so a mismatch is two (or zero) face chips, not a rect disagreement.
        add("chip mismatch", lambda p: p["cards"][0].update(chips=["預設臉框", "自訂臉框", "目前預設"]))
        add("unsupported equipment", lambda p: p["capabilities"].update(supports_bindings=False))
        def official(p, rows):
            p["official_entries"] = rows
        add("official row", lambda p: official(p, [official_row()]), True)
        add(
            "official row current",
            lambda p: official(
                p, [official_row(is_current=True, is_catalog_default=False)]
            ),
            True,
        )
        add(
            "official rows at cap",
            lambda p: official(
                p,
                [
                    official_row(
                        identity=f"preset/t_g{index}/a.png",
                        is_catalog_default=index == 0,
                    )
                    for index in range(GALLERY_MAX_OFFICIAL_ENTRIES)
                ],
            ),
            True,
        )
        add(
            "official rows over cap",
            lambda p: official(
                p,
                [
                    official_row(
                        identity=f"preset/t_g{index}/a.png",
                        is_catalog_default=index == 0,
                    )
                    for index in range(GALLERY_MAX_OFFICIAL_ENTRIES + 1)
                ],
            ),
        )
        add("official entries null", lambda p: p.update(official_entries=None))
        add("official entries missing", lambda p: p.pop("official_entries"))
        add(
            "official row extra key",
            lambda p: official(p, [dict(official_row(), chips=[])]),
        )
        add(
            "official row missing key",
            lambda p: official(
                p, [{key: value for key, value in official_row().items() if key != "artwork"}]
            ),
        )
        add("official row duplicate", lambda p: official(p, [official_row(), official_row()]))
        add(
            "official rows two current",
            lambda p: official(
                p,
                [
                    official_row(
                        identity="preset/t_a/a.png", is_current=True, is_catalog_default=False
                    ),
                    official_row(
                        identity="preset/t_b/a.png", is_current=True, is_catalog_default=False
                    ),
                ],
            ),
        )
        add(
            "official rows two catalog defaults",
            lambda p: official(
                p,
                [
                    official_row(identity="preset/t_a/a.png"),
                    official_row(identity="preset/t_b/a.png"),
                ],
            ),
        )
        add("official flag not boolean", lambda p: official(p, [official_row(is_current=1)]))
        def official_change(p, **changes):
            """Replace the one official row's descriptor with changed candidate facts."""
            row = p["official_entries"][0]
            row["artwork"] = official_descriptor(row["identity"], **changes)
        def official_row_with(p, **changes):
            official(p, [official_row()])
            official_change(p, **changes)
        add("official candidate", lambda p: official(p, [official_row()]), True)
        add(
            "official url foreign route",
            lambda p: official_row_with(p, url=f"/art/gallery/character/t_gallery/{image_id(1)}.png"),
        )
        add(
            "official url short fingerprint",
            lambda p: official_row_with(p, url=f"/art/official/{'a' * 63}/preset/x/a.png"),
        )
        add(
            "official url upper fingerprint",
            lambda p: official_row_with(p, url=f"/art/official/{'A' * 64}/preset/x/a.png"),
        )
        add(
            "official url empty tail",
            lambda p: official_row_with(p, url=f"/art/official/{_OFFICIAL_FINGERPRINT}/"),
        )
        add(
            "official url space",
            lambda p: official_row_with(p, url=f"/art/official/{_OFFICIAL_FINGERPRINT}/preset/x/a b.png"),
        )
        add(
            "official url over cap",
            lambda p: official_row_with(
                p, url=f"/art/official/{_OFFICIAL_FINGERPRINT}/" + "x" * GALLERY_MAX_OFFICIAL_URL
            ),
        )
        add(
            "official candidate stage",
            lambda p: official_row_with(p, stage={"scale": 1, "x": 0, "y": 0}),
        )
        add(
            "official rect overflow",
            lambda p: official_row_with(p, face_rect={"x": 0.9, "y": 0.0, "w": 0.5, "h": 0.5}),
        )
        add(
            "official rect zero",
            lambda p: official_row_with(p, face_rect={"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.5}),
        )
        add(
            "official rect boolean",
            lambda p: official_row_with(p, face_rect={"x": True, "y": 0.0, "w": 0.5, "h": 0.5}),
        )
        def official_rect_null(p):
            official_row_with(p)
            p["official_entries"][0]["artwork"]["attempts"][0]["resource"]["geometry"][
                "face_rect"
            ] = None
        add("official rect null", official_rect_null)
        add("official terminal missing", lambda p: official_row_with(p, terminal=False))
        def official_metadata_fault(p):
            # The directory degraded its manifest whole: the image's own
            # `metadata_invalid` fact sits at its candidate's source and rank.
            official_row_with(p)
            artwork = p["official_entries"][0]["artwork"]
            identity = p["official_entries"][0]["identity"]
            artwork["attempts"].insert(0, descriptors.fault_attempt(
                descriptors.gallery_official_source_id(identity),
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.REASON_METADATA_INVALID,
            ))
        add("official metadata fault before its candidate", official_metadata_fault, True)
        def official_declared_default_fault(p):
            # The declared default was refused: its fault names that identity
            # and precedes the substitute this row presents.
            official_row_with(p)
            p["official_entries"][0]["artwork"]["attempts"].insert(0, descriptors.fault_attempt(
                descriptors.gallery_official_source_id("preset/t_gallery_preset/missing.png"),
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.REASON_EXPLICIT_REFERENCE_MISSING,
            ))
        add("official declared-default fault", official_declared_default_fault, True)
        def official_substitute_candidate(p):
            official_row_with(p)
            artwork = p["official_entries"][0]["artwork"]
            artwork["attempts"].insert(0, descriptors.image_attempt(
                "gallery.extra:man", 0, descriptors.resource(
                    "defaults/man.webp", _digest("man"), "/art/defaults/man.webp",
                    descriptors.ORIGIN_SILHOUETTE,
                ),
            ))
        add("official substitute candidate", official_substitute_candidate)
        def card_unrelated_attempt(p):
            p["cards"][0]["artwork"]["attempts"].append(descriptors.fault_attempt(
                "gallery.other:1", descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.REASON_SOURCE_REJECTED,
            ))
        add("card unrelated extra attempt", card_unrelated_attempt)
        def official_candidate_identity(p):
            official(p, [official_row()])
            p["official_entries"][0]["artwork"]["attempts"][0]["resource"][
                "resource_id"
            ] = "preset/t_gallery_preset/b.png"
        add("official candidate identity", official_candidate_identity)
        add(
            "official row old flat url",
            lambda p: official(p, [dict(official_row(), url=f"/art/official/{_OFFICIAL_FINGERPRINT}/preset/t_gallery_preset/a.png")]),
        )
        add(
            "official identity two segments",
            lambda p: official(p, [official_row(identity="preset/a.png")]),
        )
        add(
            "official identity four segments",
            lambda p: official(p, [official_row(identity="preset/key/deep/a.png")]),
        )
        add(
            "official identity empty segment",
            lambda p: official(p, [official_row(identity="preset//a.png")]),
        )
        add(
            "official identity dot segment",
            lambda p: official(p, [official_row(identity="preset/../a.png")]),
        )
        add(
            "official identity unknown extension",
            lambda p: official(p, [official_row(identity="preset/key/a.bmp")]),
        )
        add(
            "official identity no extension",
            lambda p: official(p, [official_row(identity="preset/key/a")]),
        )
        add(
            "official identity format char",
            lambda p: official(p, [official_row(identity="preset/key/a\u200b.png")]),
        )
        add(
            "official identity nonbreaking space",
            lambda p: official(p, [official_row(identity="preset/key/a\u00a0.png")]),
        )
        def official_identity_length(length):
            return "preset/" + "k" * (length - len("preset/") - len("/a.png")) + "/a.png"
        def official_identity_case(p, length):
            identity = official_identity_length(length)
            official(p, [official_row(identity=identity)])
            # A compact synthetic route keeps the URL inside its own ceiling so
            # the IDENTITY bound is the fact under test.
            p["official_entries"][0]["artwork"] = official_descriptor(
                identity, url=f"/art/official/{_OFFICIAL_FINGERPRINT}/x.png"
            )
        add(
            "official identity at cap",
            lambda p: official_identity_case(p, GALLERY_MAX_OFFICIAL_IDENTITY),
            True,
        )
        add(
            "official identity over cap",
            lambda p: official_identity_case(p, GALLERY_MAX_OFFICIAL_IDENTITY + 1),
        )
        add("warning missing card", lambda p: p["binding_warnings"].append({"image_id": image_id(99), "label": "不存在", "conditions": ["防具：未裝備"]}))
        def subjects(p, count):
            p["subjects"].extend({"subject_key": f"portrait:character:t_{i}", "kind": "portrait:character", "display_name": "其他角色", "is_puppet": False} for i in range(count - 1))
        add("rail at cap", lambda p: subjects(p, 24), True)
        add("rail over cap", lambda p: subjects(p, 25))
        def subject_key(p, key):
            p["selected"] = p["subjects"][0]["subject_key"] = f"portrait:character:{key}"
            candidate(p)["url"] = f"/art/gallery/character/{key}/{image_id(1)}.avif"
        add("URL 129", lambda p: subject_key(p, "a" * 64), True)
        add("key byte cap", lambda p: subject_key(p, "𠮷" * 50), True)
        add("key byte overflow", lambda p: subject_key(p, "𠮷" * 51))
        add("key codepoint overflow", lambda p: subject_key(p, "a" * 65))
        add("key control", lambda p: subject_key(p, "x\u200dy"))
        add("key separator", lambda p: subject_key(p, "x/y"))
        add("permitted key whitespace", lambda p: subject_key(p, "key "), True)
        def accessories(p, values):
            p["equipment_summary"]["accessories"] = {"value": values, "display_names": ["測試飾品"] * len(values), "equipped_count": len(values)}
        add("accessories at cap", lambda p: accessories(p, [f"t_{i}" for i in range(5)]), True)
        add("accessories over cap", lambda p: accessories(p, [f"t_{i}" for i in range(6)]))
        add("accessories unsorted", lambda p: accessories(p, ["t_z", "t_a"]))
        add("Unicode sort", lambda p: accessories(p, ["\ue000", "𠮷"]), True)
        def failed(p):
            p["cards"] = [{
                "image_id": image_id(2), "status": "failed", "label": "暫時無法生成，稍後再試",
                "artwork": card_descriptor(2, generation="failed", terminal=False),
                "is_default": False, "chips": [], "requested_fields": [],
                "binding_present": False, "created_at": 200,
            }]
            p["cards"][0]["artwork"]["attempts"] = []
            p["cards"][0]["artwork"]["retention_sources"] = []
            p["filters"] = {"all": 1, "defaults": 0, "bound": 0, "pending": 0, "failed": 1}
            p["error_state"] = {"code": "sd_connection_error", "at": 200}
        add("failed row", failed, True)
        def pending_rows(p, count):
            failed(p)
            p["error_state"] = None
            first = p["cards"][0]
            first.update(status="pending", label="肖像（生成中）")
            first["artwork"]["generation_state"] = "pending"
            p["cards"] = [dict(first, image_id=image_id(i + 1)) for i in range(count)]
            p["filters"].update(all=count, pending=count, failed=0)
        add("pending at cap", lambda p: pending_rows(p, 8), True)
        add("pending over cap", lambda p: pending_rows(p, 9))
        def warning_rows(p, count, condition_length=12):
            first = p["cards"][0]
            first.update(is_default=False, binding_present=True, chips=[SLOT_LABELS["armor"], "預設臉框"])
            p["cards"] = []
            for i in range(count):
                row = deepcopy(first)
                row["image_id"] = image_id(i + 1)
                row["artwork"] = card_descriptor(i + 1)
                p["cards"].append(row)
            p["filters"].update(all=count, defaults=0, bound=count)
            p["binding_warnings"] = [{"image_id": row["image_id"], "label": row["label"], "conditions": ["條" * condition_length]} for row in p["cards"]]
        add("warnings at cap", lambda p: warning_rows(p, 5), True)
        add("warnings over cap", lambda p: warning_rows(p, 6))
        add("condition at cap", lambda p: warning_rows(p, 1, 512), True)
        add("condition over cap", lambda p: warning_rows(p, 1, 513))
        def over_bytes(p):
            first = p["cards"][0]
            first.update(is_default=False, chips=["預設臉框"], label="𠮷" * 128)
            p["cards"] = []
            for i in range(110):
                row = deepcopy(first)
                row["image_id"] = image_id(i + 1)
                row["artwork"] = card_descriptor(i + 1)
                p["cards"].append(row)
            p["filters"].update(all=110, defaults=0)
        add("envelope byte overflow", over_bytes)
        script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol/panels/gallery.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validateGalleryPanelV3(value)]; }
  catch (_) { return [name, false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.run(["node", "-e", script], input=json.dumps(cases), text=True, capture_output=True, cwd=ROOT, check=True)
        js_results = json.loads(output.stdout)
        for (name, value, expected), (_, js_accepts, echoed) in zip(cases, js_results, strict=True):
            with self.subTest(case=name):
                try:
                    validate_gallery_v3(value)
                    python_accepts = True
                except ProtocolValidationError:
                    python_accepts = False
                self.assertEqual(python_accepts, expected)
                self.assertEqual(js_accepts, expected)
                if js_accepts:
                    self.assertEqual(validate_gallery_v3(echoed), value)


_V4_CAPABILITIES = {
    "supports_bindings": True, "supports_field_selection": True, "supports_free_text": True,
    "supports_personal_official_preferences": True, "supports_face_rect": True,
    "supports_stage": True, "supports_card_delete": True, "max_cards": None,
}


def v4_subject(number, *, current=False, artwork=True, kind="character"):
    """One synthetic version-4 subject tile."""
    key = _SUBJECT_KEY if number == 0 else f"portrait:{kind}:t_{number}"
    return {
        "subject_key": key, "kind": f"portrait:{kind}", "display_name": "測試角色",
        "is_current": current, "card_count": 1,
        "artwork": card_descriptor(number + 1, subject_key=key) if artwork else None,
    }


def v4_group(key, subjects, *, label=None, seen=None, total=None, expanded=True, count=None):
    """One synthetic version-4 group; ``count`` defaults to the listed subjects."""
    return {
        "key": key, "label": label, "seen": seen, "total": total, "expanded": expanded,
        "count": len(subjects) if count is None else count, "subjects": subjects,
    }


def payload_v4():
    """File-local synthetic version-4 fixture: mine, one selected subject, one card."""
    v3 = payload()
    return {
        "schema_version": 4, "available": True, "kind": "gallery",
        "categories": [
            {"key": "mine", "count": 1, "enabled": True, "reason": None},
            {"key": "party", "count": 0, "enabled": True, "reason": None},
            {"key": "people", "count": 0, "enabled": False, "reason": "測試停用"},
            {"key": "monster", "count": 0, "enabled": True, "reason": None},
            {"key": "scene", "count": 0, "enabled": False, "reason": "測試停用"},
        ],
        "category": "mine",
        "groups": [v4_group("mine", [v4_subject(0, current=True)])],
        "selected": _SUBJECT_KEY, "description": None,
        "cards": v3["cards"], "official_entries": [],
        "equipment_summary": v3["equipment_summary"],
        "capabilities": dict(_V4_CAPABILITIES),
        "binding_warnings": [], "error_state": None,
    }


def v4_empty(p, category="party"):
    """Select an enabled category with no subject: every card fact is empty."""
    p["category"] = category
    p["categories"][0]["count"] = 0
    p["groups"] = []
    p.update(
        selected=None, description=None, cards=[], official_entries=[], binding_warnings=[],
        equipment_summary=None, capabilities=None, error_state=None,
    )


def v4_collapsed(p, count=7):
    """Add a labelled collapsed group carrying only its count."""
    p["groups"].append(v4_group("place:t_hall", [], label="測試大廳", expanded=False, count=count))
    p["categories"][0]["count"] += count


def v4_subjects(p, count, *, artwork=False):
    """Replace the one group with ``count`` subjects, the first selected."""
    subjects = [v4_subject(i, current=i == 0, artwork=artwork) for i in range(count)]
    p["groups"] = [v4_group("mine", subjects)]
    p["categories"][0]["count"] = count


def v4_case(modify):
    value = payload_v4()
    modify(value)
    return value


class GalleryCutoverTests(unittest.TestCase):
    """The registered gallery is version 4 on both sides of the wire."""

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_registry_and_both_validators_speak_version_4(self):
        from web.webclient.presentation import gallery as gallery_module
        from web.webclient.presentation import gallery_categories

        self.assertEqual(gallery_module.GALLERY_CATEGORY_KEYS, gallery_categories.CATEGORY_KEYS)
        spec = build_production_registry().spec("gallery")
        self.assertEqual(spec.schema_version, 4)
        self.assertIs(spec.presenter, gallery_presenter)
        script = """
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
process.stdout.write(JSON.stringify([protocol.PANEL_ALLOWLIST.gallery, protocol.GALLERY_CATEGORY_KEYS]));
"""
        output = subprocess.run(["node", "-e", script], text=True, capture_output=True, cwd=ROOT, check=True)
        self.assertEqual(json.loads(output.stdout), [4, list(gallery_categories.CATEGORY_KEYS)])
        # The version-3 rail shape is refused by the registered validator.
        with self.assertRaises(ProtocolValidationError):
            validate_gallery(payload())


class GalleryV4ParityTests(unittest.TestCase):
    """Dual-direction parity of the version-4 validators (Python and the JS mirror)."""

    def assert_parity(self, cases):
        """Every (name, payload, expected) case gets the same verdict on both sides.

        Cases travel as JSON text to both sides, so an integral float such as
        ``7.0`` reaches Python exactly as the wire would deliver it.
        """
        script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validateGalleryPanel(value)]; }
  catch (_) { return [name, false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        text = json.dumps(cases)
        output = subprocess.run(["node", "-e", script], input=text, text=True, capture_output=True, cwd=ROOT, check=True)
        js_results = json.loads(output.stdout)
        for (name, value, expected), (_, js_accepts, echoed) in zip(json.loads(text), js_results, strict=True):
            with self.subTest(case=name):
                try:
                    validate_gallery(value)
                    python_accepts = True
                except ProtocolValidationError:
                    python_accepts = False
                self.assertEqual(python_accepts, expected)
                self.assertEqual(js_accepts, expected)
                if js_accepts:
                    self.assertEqual(validate_gallery(echoed), value)

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-gallery-payload-has-an-exact-category-scoped-shape"
    )
    def test_disabled_category_is_rejected(self):
        self.assert_parity([
            ("valid", payload_v4(), True),
            ("disabled category", v4_case(lambda p: p.update(category="people")), False),
            ("disabled scene", v4_case(lambda p: p.update(category="scene")), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-gallery-payload-has-an-exact-category-scoped-shape"
    )
    def test_reordered_or_partial_category_list_is_rejected(self):
        def swap(p):
            p["categories"][1], p["categories"][3] = p["categories"][3], p["categories"][1]

        def repeat(p):
            p["categories"][4] = dict(p["categories"][3])
        self.assert_parity([
            ("omitted key", v4_case(lambda p: p["categories"].pop()), False),
            ("repeated key", v4_case(repeat), False),
            ("reordered keys", v4_case(swap), False),
            ("extra category", v4_case(lambda p: p["categories"].append(dict(p["categories"][1]))), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-gallery-payload-has-an-exact-category-scoped-shape"
    )
    def test_reason_accompanies_only_disabled_categories(self):
        self.assert_parity([
            ("enabled with reason", v4_case(lambda p: p["categories"][1].update(reason="原因")), False),
            ("disabled without reason", v4_case(lambda p: p["categories"][2].update(reason=None)), False),
            ("disabled empty reason", v4_case(lambda p: p["categories"][2].update(reason="")), False),
            ("reason at cap", v4_case(lambda p: p["categories"][2].update(reason="由" * 64)), True),
            ("reason over cap", v4_case(lambda p: p["categories"][2].update(reason="由" * 65)), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::version-4-groups-carry-ordered-subjects-or-a-collapsed-count"
    )
    def test_collapsed_group_with_subjects_is_rejected(self):
        self.assert_parity([
            ("collapsed with subjects", v4_case(lambda p: p["groups"][0].update(expanded=False)), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::version-4-groups-carry-ordered-subjects-or-a-collapsed-count"
    )
    def test_group_counts_sum_to_the_category_count(self):
        def collapsed_not_summed(p):
            v4_collapsed(p)
            p["categories"][0]["count"] = 1
        self.assert_parity([
            ("category count high", v4_case(lambda p: p["categories"][0].update(count=2)), False),
            ("category count low", v4_case(lambda p: p["categories"][0].update(count=0)), False),
            ("collapsed count not summed", v4_case(collapsed_not_summed), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::version-4-groups-carry-ordered-subjects-or-a-collapsed-count"
    )
    def test_collapsed_group_is_accepted(self):
        def collapsed_only(p):
            v4_empty(p, "mine")
            v4_collapsed(p)

        def integral_float(p):
            v4_collapsed(p)
            p["groups"][1]["count"] = 7.0
        self.assert_parity([
            ("collapsed beside expanded", v4_case(v4_collapsed), True),
            ("collapsed only, nothing selected", v4_case(collapsed_only), True),
            ("integral float count", v4_case(integral_float), True),
        ])

    @covers_requirement(
        "webclient-gallery-panel::version-4-groups-carry-ordered-subjects-or-a-collapsed-count"
    )
    def test_seen_and_total_are_paired_and_bounded(self):
        def tier(**changes):
            return v4_case(lambda p: p["groups"][0].update(changes))
        self.assert_parity([
            ("seen and total", tier(seen=1, total=3), True),
            ("seen equals total", tier(seen=3, total=3), True),
            ("seen without total", tier(seen=1), False),
            ("total without seen", tier(total=3), False),
            ("seen over total", tier(seen=4, total=3), False),
            ("negative seen", tier(seen=-1, total=3), False),
            ("total over ceiling", tier(seen=1, total=257), False),
            ("boolean seen", tier(seen=True, total=3), False),
            ("fractional total", tier(seen=1, total=2.5), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::selection-decides-the-version-4-card-fields"
    )
    def test_empty_category_carries_no_card_facts(self):
        cases = [("empty category", v4_case(v4_empty), True)]
        for field, value in (
            ("capabilities", dict(_V4_CAPABILITIES)),
            ("selected", _SUBJECT_KEY),
            ("description", "測試描述"),
            ("cards", payload()["cards"]),
            ("official_entries", [official_row()]),
            ("binding_warnings", [{"image_id": image_id(1), "label": "測試肖像", "conditions": ["防具：未裝備"]}]),
            ("equipment_summary", payload()["equipment_summary"]),
            ("error_state", {"code": "sd_connection_error", "at": 1}),
        ):
            def modify(p, field=field, value=value):
                v4_empty(p)
                p[field] = value
            cases.append((f"empty with {field}", v4_case(modify), False))
        self.assert_parity(cases)

    @covers_requirement(
        "webclient-gallery-panel::selection-decides-the-version-4-card-fields"
    )
    def test_selection_outside_listed_subjects_is_rejected(self):
        def collapsed_selection(p):
            v4_empty(p, "mine")
            v4_collapsed(p)
            p["selected"] = _SUBJECT_KEY
        self.assert_parity([
            ("selection only a collapsed group holds", v4_case(collapsed_selection), False),
            ("selection not listed", v4_case(lambda p: p.update(selected="portrait:character:absent")), False),
            ("null selection with a listed subject", v4_case(lambda p: p.update(selected=None)), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::selection-decides-the-version-4-card-fields"
    )
    def test_capabilities_carry_the_declared_card_operations(self):
        cases = []
        for field in ("supports_face_rect", "supports_stage", "supports_card_delete"):
            cases.append((f"missing {field}", v4_case(lambda p, f=field: p["capabilities"].pop(f)), False))
            cases.append((f"non-boolean {field}", v4_case(lambda p, f=field: p["capabilities"].update({f: 1})), False))
        cases.append(("v3 capability record", v4_case(lambda p: p.update(capabilities=payload()["capabilities"])), False))
        cases.append(("null capabilities with a selection", v4_case(lambda p: p.update(capabilities=None)), False))
        self.assert_parity(cases)

    @covers_requirement(
        "webclient-gallery-panel::a-panel-past-the-subject-ceiling-is-unavailable-never-truncated"
    )
    def test_one_subject_over_the_ceiling_fails_closed(self):
        def over_split(p):
            # Two groups whose counts are each in range, still one past the ceiling.
            v4_subjects(p, GALLERY_MAX_PANEL_SUBJECTS + 1)
            subjects = p["groups"][0]["subjects"]
            p["groups"] = [v4_group("a", subjects[:200]), v4_group("b", subjects[200:])]
        self.assert_parity([
            ("256 subjects", v4_case(lambda p: v4_subjects(p, GALLERY_MAX_PANEL_SUBJECTS)), True),
            ("257 subjects", v4_case(lambda p: v4_subjects(p, GALLERY_MAX_PANEL_SUBJECTS + 1)), False),
            ("257 subjects in two groups", v4_case(over_split), False),
        ])

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-panel-has-no-byte-limit-of-its-own"
    )
    def test_panel_larger_than_one_frame_is_valid(self):
        value = v4_case(lambda p: v4_subjects(p, GALLERY_MAX_PANEL_SUBJECTS, artwork=True))
        self.assertGreater(json_byte_size(value), MAX_CANONICAL_JSON_BYTES)
        self.assert_parity([("larger than one frame", value, True)])

    @covers_requirement(
        "webclient-gallery-panel::the-version-4-validators-are-exact-mirrors",
        "webclient-gallery-panel::the-version-4-gallery-payload-has-an-exact-category-scoped-shape",
    )
    def test_parity_cases_cover_every_rule(self):
        cases = [("valid", payload_v4(), True)]

        def add(name, modify, accepted=False):
            cases.append((name, v4_case(modify), accepted))

        def group(**changes):
            return lambda p: p["groups"][0].update(changes)

        def subject(**changes):
            return lambda p: p["groups"][0]["subjects"][0].update(changes)

        def second_group(p, key="tier:b", subjects=None):
            subjects = [v4_subject(1)] if subjects is None else subjects
            p["groups"].append(v4_group(key, subjects))
            p["categories"][0]["count"] += len(subjects)

        def extra_groups(count):
            return lambda p: p["groups"].extend(v4_group(f"g{i}", [], count=0) for i in range(count))

        def no_bindings(p):
            p["capabilities"]["supports_bindings"] = False
            p["equipment_summary"] = None

        def failed(p):
            row = {
                "image_id": image_id(2), "status": "failed", "label": "暫時無法生成",
                "artwork": card_descriptor(2, generation="failed", terminal=False),
                "is_default": False, "chips": [], "requested_fields": [],
                "binding_present": False, "created_at": 50,
            }
            row["artwork"].update(attempts=[], retention_sources=[])
            p["cards"].append(row)
            p["error_state"] = {"code": "sd_connection_error", "at": 50}

        def two_defaults(p):
            p["cards"].append(dict(p["cards"][0], image_id=image_id(3), artwork=card_descriptor(3), created_at=50))

        warning = {"image_id": image_id(1), "label": "測試肖像", "conditions": ["防具：未裝備"]}
        # Discriminators and exact keys.
        add("schema 3", lambda p: p.update(schema_version=3))
        add("schema boolean", lambda p: p.update(schema_version=True))
        add("integral float schema", lambda p: p.update(schema_version=4.0), True)
        add("unavailable", lambda p: p.update(available=False))
        add("wrong kind", lambda p: p.update(kind="art"))
        add("unknown top key", lambda p: p.update(extra=1))
        add("missing description", lambda p: p.pop("description"))
        add("v3 filters key", lambda p: p.update(filters={"all": 1}))
        add("v3 subjects key", lambda p: p.update(subjects=[]))
        add("prototype key", lambda p: p.update({"__proto__": 1}))
        # Categories.
        add("categories not a list", lambda p: p.update(categories={}))
        add("category extra key", lambda p: p["categories"][0].update(extra=1))
        add("category count negative", lambda p: p["categories"][1].update(count=-1))
        add("category count over ceiling", lambda p: p["categories"][1].update(count=257))
        add("category count boolean", lambda p: p["categories"][1].update(count=True))
        add("category enabled non-boolean", lambda p: p["categories"][1].update(enabled=1))
        add("unknown category", lambda p: p.update(category="pets"))
        add("category not a string", lambda p: p.update(category=["mine"]))
        add("category null", lambda p: p.update(category=None))
        # Groups.
        add("groups not a list", lambda p: p.update(groups={}))
        add("groups at cap", extra_groups(63), True)
        add("groups over cap", extra_groups(64))
        add("group extra key", group(extra=1))
        add("group missing key", lambda p: p["groups"][0].pop("label"))
        add("group key grammar", group(key="Mine"))
        add("group key empty", group(key=""))
        add("group key trailing newline", group(key="mine\n"))
        add("group key at cap", group(key="k" * 96), True)
        add("group key over cap", group(key="k" * 97))
        add("group key punctuation", group(key="place:t_hall.north-1"), True)
        add("duplicate group key", lambda p: second_group(p, key="mine"))
        add("label at cap", group(label="名" * 64), True)
        add("label over cap", group(label="名" * 65))
        add("label empty", group(label=""))
        add("expanded non-boolean", group(expanded=1))
        add("count negative", group(count=-1))
        add("count over ceiling", group(count=257))
        add("expanded count mismatch", group(count=2))
        add("subjects not a list", group(subjects={}))
        # Subjects.
        add("subject extra key", subject(extra=1))
        add("subject unknown key", subject(subject_key="portrait:character:a/b"))
        add("subject non-string key", subject(subject_key=7))
        add("scene subject", subject(subject_key="scene:t_scene", kind="scene"))
        add("kind mismatch", subject(kind="portrait:monster"))
        add("monster subject", lambda p: second_group(p, subjects=[v4_subject(1, kind="monster")]), True)
        add("duplicate subject across groups", lambda p: second_group(p, subjects=[v4_subject(0)]))
        add("display name at cap", subject(display_name="名" * 64), True)
        add("display name over cap", subject(display_name="名" * 65))
        add("display name surrogate", subject(display_name="\ud800"))
        add("is_current non-boolean", subject(is_current=1))
        add("no current subject", subject(is_current=False), True)
        add("two current subjects", lambda p: second_group(p, subjects=[v4_subject(1, current=True)]))
        add("card_count at cap", subject(card_count=320), True)
        add("card_count over cap", subject(card_count=321))
        add("card_count boolean", subject(card_count=False))
        add("artwork null", subject(artwork=None), True)
        add("artwork invalid", lambda p: p["groups"][0]["subjects"][0]["artwork"].update(extra=1))
        # Selection-scoped card facts (the version-3 rules, without filters).
        add("description", lambda p: p.update(description="測試描述"), True)
        add("description at cap", lambda p: p.update(description="景" * 512), True)
        add("description over cap", lambda p: p.update(description="景" * 513))
        add("description empty", lambda p: p.update(description=""))
        add("max_cards one", lambda p: p["capabilities"].update(max_cards=1), True)
        add("max_cards two", lambda p: p["capabilities"].update(max_cards=2))
        add("unsupported equipment", lambda p: p["capabilities"].update(supports_bindings=False))
        add("no bindings, no equipment", no_bindings, True)
        add("card row unknown key", lambda p: p["cards"][0].update(extra=1))
        add("card foreign url", lambda p: candidate(p).update(url=f"/art/gallery/character/other/{image_id(1)}.png"))
        add("official entries", lambda p: p.update(official_entries=[official_row()]), True)
        add("official duplicate", lambda p: p.update(official_entries=[official_row(), official_row()]))
        add("error without failed row", lambda p: p.update(error_state={"code": "sd_connection_error", "at": 1}))
        add("warning without bound card", lambda p: p.update(binding_warnings=[dict(warning)]))
        add("failed row with error state", failed, True)
        add("two default rows", two_defaults)
        self.assert_parity(cases)


class GalleryPresenterTests(EvenniaTest):
    account_typeclass = Account

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.actor = create_object(PlayerCharacter, key="測試主角", location=self.room1)
        # The registered gallery opens on the "mine" category, which lists the
        # owning account's characters.
        self.actor.account = self.account
        self.account.characters.add(self.actor)
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "t_gallery_actor"}
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_actor")
        self.context = PresentationContext(self.actor, 1)
        self.registry = build_production_registry()
        visual_registry = {"t_beast": SimpleNamespace(display_label="測試魔物")}
        for target in (
            "web.webclient.presentation.gallery.get_monster_visual_registry",
            "world.lore.monster_visuals.get_monster_visual_registry",
            "world.art.subjects.get_monster_visual_registry",
        ):
            patcher = patch(target, return_value=visual_registry)
            patcher.start()
            self.addCleanup(patcher.stop)

    def card(self, number, *, timestamp=100, binding=None, face=None, subject=None, extension=".png", image_size=None):
        subject = subject or self.subject
        directory = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        identity = f"gallery/{directory}/{subject.key}/{image_id(number)}{extension}"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        size = image_size or {"width": 1000, "height": 1000}
        # The write boundary fills an OMITTED rect; an explicit None is malformed.
        rect = {} if face is None else {"face_rect": face}
        return api.append_card(subject, image_id=image_id(number), stored_identity=identity,
            prompt=None, seed=None, checkpoint=None, requested_fields=[], binding=binding,
            source="seed", created_at=timestamp, image_size=size, **rect)

    def make_session(self):
        session = SimpleNamespace(ndb=SimpleNamespace(), puppet=self.actor, protocol_key="websocket", msg=lambda **kwargs: None)
        attach_coordinator(session, self.registry)
        return session

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_empty_available_and_mode_gate(self):
        before = api.GalleryRecord.objects.count()
        value = gallery_presenter(self.context)
        self.assertEqual(value["schema_version"], 4)
        self.assertEqual(value["category"], "mine")
        self.assertEqual(value["cards"], [])
        self.assertEqual(value["selected"], self.subject.full())
        self.assertEqual(api.GalleryRecord.objects.count(), before)
        self.actor.creation_pending = True
        self.assertEqual(self.registry.render("gallery", self.context)["reason"]["code"], "gallery_unavailable")

    @covers_requirement(
        "artwork-descriptor::descriptors-reveal-only-authorized-exact-subjects"
    )
    def test_rail_prioritizes_companions_reserves_monsters_and_skips_corruption(self):
        # The dead version-3 rail (deleted by gallery-v3-removal).
        other = create_object(NPC, key="其他角色")
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_other"}
        companion = create_object(NPC, key="同行角色")
        companion.db.portrait_policy = {"mode": "named", "stable_key": "t_companion"}
        companion.db.party_member = self.actor.pk
        self.actor.db.party = [companion.pk]
        self.actor.db.party_meta = {str(companion.pk): {"general": True, "reasons": []}}
        corrupt = create_object(NPC, key="損壞資料")
        corrupt.db.portrait_policy = {"mode": "named", "stable_key": "bad/key"}
        rail = gallery_subjects(self.actor)
        self.assertEqual([entry[0]["subject_key"] for entry in rail], [self.subject.full(), "portrait:character:t_companion", "portrait:character:t_other", "portrait:monster:t_beast"])
        with patch("web.webclient.presentation.gallery.GALLERY_MAX_SUBJECTS", 3):
            self.assertEqual([row[0]["subject_key"] for row in gallery_subjects(self.actor)], [self.subject.full(), "portrait:character:t_companion", "portrait:monster:t_beast"])

    @covers_requirement(
        "webclient-gallery-panel::card-rows-are-server-authored-with-chips-crown-and-validated-media",
        "webclient-gallery-panel::the-equipment-summary-and-capabilities-are-server-computed",
    )
    def test_card_chips_order_counts_and_overlap_are_server_facts(self):
        self.actor.db.equipment = {"weapon_main": "t_sword", "armor": "t_coat", "accessories": ["t_ring_b", "t_ring_a"]}
        bound = {"mask": ["weapon_main", "armor"], "snapshot": {"weapon_main": "t_sword", "armor": "t_coat"}}
        # Card 1 has custom face rect
        self.card(1, binding=bound, face={"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.4})
        self.card(2, timestamp=200, binding={"mask": ["armor"], "snapshot": {"armor": "t_coat"}})
        self.card(3, timestamp=200, binding={"mask": ["weapon_main"], "snapshot": {"weapon_main": "t_other"}})
        with patch("web.webclient.presentation.gallery.ITEM_REGISTRY", {"t_sword": SimpleNamespace(display_name_zh="測試長劍"), "t_coat": SimpleNamespace(display_name_zh="測試外套")}):
            value = gallery_presenter(self.context)
        self.assertEqual([row["image_id"] for row in value["cards"]], [image_id(2), image_id(3), image_id(1)])
        self.assertEqual(value["cards"][-1]["chips"], [SLOT_LABELS["weapon_main"], SLOT_LABELS["armor"], "自訂臉框", "目前預設"])
        self.assertEqual([row["image_id"] for row in value["binding_warnings"]], [image_id(2), image_id(1)])
        self.assertEqual(value["binding_warnings"][-1]["conditions"], ["主手：測試長劍", "防具：測試外套"])
        self.assertEqual(value["equipment_summary"]["accessories"]["value"], ["t_ring_a", "t_ring_b"])
        self.assertNotIn("filters", value)

    @covers_requirement(
        "webclient-gallery-panel::card-rows-are-server-authored-with-chips-crown-and-validated-media"
    )
    def test_card_labels_carry_no_timestamp_and_rows_keep_their_created_at(self):
        # Two cards and one pending job minted at different instants share
        # the fixed labels; only the structured created_at tells them apart,
        # and no stored record is renamed.
        self.card(1, timestamp=1_700_000_000.5)
        self.card(2, timestamp=1_700_086_400)
        self.job(3)
        before = repr(api.record_for(self.subject).attributes.all())
        value = gallery_presenter(self.context)
        rows = {row["image_id"]: row for row in value["cards"]}
        self.assertEqual(rows[image_id(1)]["label"], "肖像")
        self.assertEqual(rows[image_id(2)]["label"], "肖像")
        self.assertEqual(rows[image_id(3)]["label"], "肖像（生成中）")
        self.assertEqual(rows[image_id(1)]["created_at"], 1_700_000_000.5)
        self.assertEqual(rows[image_id(2)]["created_at"], 1_700_086_400)
        self.assertEqual(rows[image_id(3)]["created_at"], 303)
        for row in value["cards"]:
            self.assertNotIn("UTC", row["label"])
            self.assertNotRegex(row["label"], r"\d")
        self.assertEqual(repr(api.record_for(self.subject).attributes.all()), before)

    @covers_requirement("webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only")
    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_repeated_render_preserves_duplicate_records_cards_jobs_and_files(self):
        self.card(1)
        duplicate = create_script(api.GalleryRecord, key=api.record_key(self.subject), persistent=True, interval=0)
        duplicate.db.cards = []
        job = self.job(2)
        before_records = [(row.pk, repr(row.attributes.all())) for row in api.GalleryRecord.objects.all()]
        before_jobs = [(row.pk, row.db.status, row.db.enqueued_at) for row in ArtAssetRecord.objects.all()]
        before_files = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first = gallery_presenter(self.context)
        self.assertEqual(gallery_presenter(self.context), first)
        self.assertEqual([(row.pk, repr(row.attributes.all())) for row in api.GalleryRecord.objects.all()], before_records)
        self.assertEqual([(row.pk, row.db.status, row.db.enqueued_at) for row in ArtAssetRecord.objects.all()], before_jobs)
        self.assertEqual({path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}, before_files)
        self.assertEqual(job.db.status, "pending")

    @covers_requirement(
        "webclient-gallery-panel::binding-overlap-warnings-are-computed-only-in-the-presenter"
    )
    def test_accessory_match_requires_exact_equipment_and_warnings_keep_newest_five(self):
        self.actor.db.equipment = {"accessories": ["t_ring_b", "t_ring_a"]}
        binding = {"mask": ["accessories"], "snapshot": {"accessories": ["t_ring_a", "t_ring_b"]}}
        for number in range(1, 8):
            self.card(number, timestamp=number, binding=binding)
        self.card(8, timestamp=8, binding={"mask": ["accessories"], "snapshot": {"accessories": ["t_ring_a"]}})
        value = gallery_presenter(self.context)
        self.assertEqual([row["image_id"] for row in value["binding_warnings"]], [image_id(number) for number in range(7, 2, -1)])
        self.assertEqual(value["binding_warnings"][0]["conditions"], ["飾品：t_ring_a、t_ring_b（任一）"])
        self.assertEqual(sum(row["binding_present"] for row in value["cards"]), 8)

    def job(self, number):
        with patch("world.art.queue._prompt_digest_or_empty", return_value=""), patch("world.art.queue.time.time", return_value=300 + number):
            return enqueue_gallery_job(self.subject, "synthetic portrait", image_id=image_id(number), binding=None, face_rect=None, requested_fields=[])

    @covers_requirement(
        "webclient-gallery-panel::pending-jobs-and-the-recorded-error-render-as-truthful-synthetic-rows"
    )
    def test_pending_bound_dedupe_and_offline_failed_settlement(self):
        for number in range(1, 11):
            self.job(number)
        self.assertEqual([row["image_id"] for row in pending_gallery_jobs(self.subject)], [image_id(number) for number in range(10, 2, -1)])
        self.card(10, timestamp=400)
        value = gallery_presenter(self.context)
        self.assertEqual(sum(row["image_id"] == image_id(10) for row in value["cards"]), 1)
        self.assertEqual(sum(row["status"] == "pending" for row in value["cards"]), 7)
        job = ArtAssetRecord.objects.get(db_key=f"art:{self.subject.full()}:gen:{image_id(9)}")
        job.db.status = "in_progress"
        job.db.generation_token = "t_token"
        with patch("world.art.gallery.time.time", return_value=500):
            settle_gallery_failed(job.key, generation_token="t_token", error="sd_connection_error")
        value = gallery_presenter(self.context)
        failed = [row for row in value["cards"] if row["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertIn("暫時無法生成，稍後再試", failed[0]["label"])
        self.assertIn("sd_connection_error", failed[0]["label"])
        # A synthetic row carries no image at all and keeps its truthful
        # recorded generation state.
        self.assertEqual(failed[0]["artwork"]["attempts"], [])
        self.assertIsNone(failed[0]["artwork"]["terminal"])
        self.assertEqual(failed[0]["artwork"]["generation_state"], "failed")
        self.assertEqual(failed[0]["artwork"]["generation_subject"], self.subject.full())
        self.assertEqual(value, gallery_presenter(self.context))
        self.assertEqual(len(api.cards_for(self.subject)), 1)

    @covers_requirement(
        "webclient-gallery-panel::card-rows-are-server-authored-with-chips-crown-and-validated-media"
    )
    @covers_requirement(
        "artwork-descriptor::descriptors-reveal-only-authorized-exact-subjects"
    )
    def test_missing_and_symlinked_outputs_stay_attributable(self):
        # A readable card whose output is gone or refused keeps its EXACT
        # requested identity as an attributed known fault with no original URL;
        # it is never silently omitted and no other card is substituted.
        first = self.card(1)
        second = self.card(2)
        (self.root / first["stored_identity"]).unlink()
        target = self.root / second["stored_identity"]
        target.unlink()
        target.symlink_to(__file__)
        value = gallery_presenter(self.context)
        self.assertEqual(
            {row["image_id"] for row in value["cards"]},
            {image_id(1), image_id(2)},
        )
        self.assertTrue(all(row["status"] == "card" for row in value["cards"]))
        reasons = {}
        for row in value["cards"]:
            artwork = row["artwork"]
            attempts = artwork["attempts"]
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["type"], "fault")
            self.assertEqual(attempts[0]["rank"], descriptors.GALLERY_RANK_ORIGINAL)
            self.assertEqual(
                attempts[0]["source_id"],
                descriptors.gallery_original_source_id(row["image_id"]),
            )
            self.assertNotIn("resource", attempts[0])
            # The prior output is known missing/invalid, so it authorizes no
            # retention; the subject silhouette stays available.
            self.assertEqual(artwork["retention_sources"], [])
            self.assertEqual(artwork["terminal"]["kind"], descriptors.TERMINAL_ALPHA_MASK)
            reasons[row["image_id"]] = attempts[0]["reason"]
        self.assertEqual(reasons[image_id(1)], descriptors.REASON_GENERATED_OUTPUT_MISSING)
        self.assertEqual(reasons[image_id(2)], descriptors.REASON_SOURCE_REJECTED)

    def companion(self, key, stable_key):
        companion = create_object(NPC, key=key, location=self.room1)
        companion.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        companion.db.party_member = self.actor.pk
        self.actor.db.party = [*(self.actor.db.party or []), companion.pk]
        meta = dict(self.actor.db.party_meta or {})
        meta[str(companion.pk)] = {"general": True, "reasons": []}
        self.actor.db.party_meta = meta
        return companion

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_selection_is_transport_owned_and_retired_by_another_owners_puppet(self):
        self.companion("同行角色", "t_companion")
        a, b = self.make_session(), self.make_session()
        selected = "portrait:character:t_companion"
        self.assertEqual(select_gallery_category(a, self.actor, "party")["outcome"], "success")
        with patch("web.webclient.presentation.gallery_selection.log_info") as event:
            res = select_gallery_subject_v4(a, self.actor, selected)
            self.assertEqual(res["outcome"], "success")
            self.assertNotIn("affected_panels", res)
            select_gallery_subject_v4(a, self.actor, selected)
            event.assert_not_called()
        self.assertIsNone(gallery_view_snapshot(b, self.actor))
        self.assertEqual(select_gallery_subject_v4(a, self.actor, "scene:t_scene")["code"], "unknown_subject")
        self.assertEqual(gallery_view_snapshot(a, self.actor).subjects, (("party", selected),))
        value = gallery_presenter(build_presentation_context(a, self.actor))
        self.assertEqual((value["category"], value["selected"]), ("party", selected))
        self.assertTrue(value["capabilities"]["supports_bindings"])
        # The other session still opens on the live character in "mine".
        other_value = gallery_presenter(build_presentation_context(b, self.actor))
        self.assertEqual((other_value["category"], other_value["selected"]), ("mine", self.subject.full()))
        # Puppeting a character of another owner retires the view.
        stranger = create_object(PlayerCharacter, key="新角色")
        a.puppet = stranger
        SIGNAL_OBJECT_POST_PUPPET.send(sender=stranger, session=a)
        self.assertIsNone(a.ndb.gallery_view)

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_deleted_selected_companion_falls_back_without_writing(self):
        self.companion("同行角色", "t_companion")
        other = self.companion("待刪角色", "t_deleted")
        session = self.make_session()
        select_gallery_category(session, self.actor, "party")
        select_gallery_subject_v4(session, self.actor, "portrait:character:t_deleted")
        frozen = build_presentation_context(session, self.actor)
        other.delete()
        value = gallery_presenter(frozen)
        self.assertEqual((value["category"], value["selected"]), ("party", "portrait:character:t_companion"))
        self.assertEqual(session.ndb.gallery_view.subjects, (("party", "portrait:character:t_deleted"),))


_PRESET_KEY = "t_gallery_preset"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class OfficialEntryProjectionTests(EvenniaTest):
    account_typeclass = Account

    """The official-entry read model of the gallery panel (task 3.1).

    The puppet carries a synthetic preset provenance, so its content
    reference is the indexed ``preset/t_gallery_preset/`` directory and the
    read model is the one under test.
    """

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / "store"
        self.store.mkdir()
        self.official_root = Path(self.tmp.name).resolve() / "official"
        settings = override_settings(
            ART_STORE_ROOT=str(self.store), ART_OFFICIAL_ROOT=str(self.official_root)
        )
        settings.enable()
        self.addCleanup(settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        for patcher in (
            patch.object(
                official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
            ),
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY}),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        visual_registry = {"t_beast": SimpleNamespace(display_label="測試魔物")}
        for target in (
            "web.webclient.presentation.gallery.get_monster_visual_registry",
            "world.lore.monster_visuals.get_monster_visual_registry",
            "world.art.subjects.get_monster_visual_registry",
        ):
            patcher = patch(target, return_value=visual_registry)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.actor = create_object(PlayerCharacter, key="測試主角", location=self.room1)
        # The registered gallery opens on the "mine" category, which lists the
        # owning account's characters.
        self.actor.account = self.account
        self.account.characters.add(self.actor)
        self.actor.db.portrait_policy = {"mode": "named", "stable_key": "t_gallery_actor"}
        self.actor.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, _PRESET_KEY)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_gallery_actor")
        self.context = PresentationContext(self.actor, 1)

    def _index(self, name, **manifest) -> str:
        folder = self.official_root / "preset" / _PRESET_KEY
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png())
        manifest_path = folder / "manifest.json"
        if manifest:
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        elif manifest_path.exists():
            manifest_path.unlink()
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def _card(self, number=1):
        image_id = str(uuid.UUID(int=number))
        identity = f"gallery/character/{self.subject.key}/{image_id}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"runtime-image")
        return api.append_card(
            self.subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
            created_at=100,
            image_size={"width": 1000, "height": 1000},
        )

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    @covers_requirement(
        "webclient-gallery-panel::the-personal-selection-state-is-server-authored-in-the-panel-payload"
    )
    def test_three_admitted_images_mark_the_selection_without_touching_cards(self):
        first = self._index("a.png")
        self._index("b.png")
        third = self._index("c.png", stage={"scale": 1.4, "x": 0.1, "y": -0.2})
        card = self._card()
        api.set_official_selection(self.subject, third)
        value = gallery_presenter(self.context)
        catalog = current_catalog()
        self.assertEqual(
            [row["identity"] for row in value["official_entries"]],
            [first, f"preset/{_PRESET_KEY}/b.png", third],
        )
        self.assertEqual(
            [row["is_current"] for row in value["official_entries"]], [False, False, True]
        )
        self.assertEqual(
            [row["is_catalog_default"] for row in value["official_entries"]],
            [True, False, False],
        )
        for row in value["official_entries"]:
            entry = catalog.entry(row["identity"])
            self.assertEqual(set(row), {
                "identity",
                "artwork",
                "is_current",
                "is_catalog_default",
            })
            artwork = row["artwork"]
            self.assertEqual(set(artwork), {
                "subject_id",
                "revision",
                "generation_subject",
                "generation_state",
                "attempts",
                "terminal",
                "retention_sources",
            })
            # The one exact admitted image is the row's rank-10 official
            # candidate, with the fingerprinted route, the admitted decoded
            # size, the fitted rectangle and no stage.
            candidate = artwork["attempts"][0]
            self.assertEqual(candidate["type"], "image")
            self.assertEqual(candidate["rank"], descriptors.GALLERY_RANK_ORIGINAL)
            self.assertEqual(
                candidate["source_id"],
                descriptors.gallery_official_source_id(row["identity"]),
            )
            resource = candidate["resource"]
            self.assertEqual(resource["origin"], descriptors.ORIGIN_OFFICIAL)
            self.assertEqual(resource["resource_id"], row["identity"])
            self.assertEqual(resource["version"], entry.fingerprint)
            self.assertEqual(resource["url"], catalog.url_for(row["identity"]))
            self.assertEqual(resource["geometry"]["image_size"], entry.image_size)
            self.assertEqual(resource["geometry"]["face_rect"], entry.face_rect)
            self.assertIsNone(resource["geometry"]["stage"])
            # The subject's silhouette rides as the terminal fallback, and the
            # recorded generation state is independent of the official origin.
            self.assertEqual(
                artwork["terminal"]["kind"], descriptors.TERMINAL_ALPHA_MASK
            )
            self.assertEqual(artwork["terminal"]["rank"], descriptors.GALLERY_RANK_ALPHA)
            self.assertEqual(artwork["generation_state"], "done")
            self.assertEqual(artwork["generation_subject"], self.subject.full())
            self.assertEqual(
                [entry["source_id"] for entry in artwork["retention_sources"]],
                [descriptors.gallery_official_source_id(row["identity"])],
            )
        # Official rows are never cards: the card list holds only the runtime row.
        self.assertEqual([row["image_id"] for row in value["cards"]], [card["image_id"]])
        # Selecting the official image cleared the runtime default; the card
        # itself is untouched.
        self.assertIsNone(api.record_for(self.subject).db.default_image_id)

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    @covers_requirement(
        "webclient-gallery-panel::the-personal-selection-state-is-server-authored-in-the-panel-payload"
    )
    def test_no_reference_or_absent_snapshot_presents_an_empty_list(self):
        self.assertEqual(gallery_presenter(self.context)["official_entries"], [])
        self._index("a.png")
        self.assertEqual(len(gallery_presenter(self.context)["official_entries"]), 1)
        # A reference the snapshot no longer holds is an empty list, present
        # and not null.
        shutil.rmtree(self.official_root / "preset")
        load_catalog()
        value = gallery_presenter(self.context)
        self.assertEqual(value["official_entries"], [])
        self.assertIsNotNone(value["official_entries"])
        # An entity declaring no content reference (the provenance attribute
        # is what declares one) presents an empty list too.
        other = create_object(PlayerCharacter, key="無來源角色", location=self.room1)
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_no_reference"}
        other.account = self.account
        self.account.characters.add(other)
        context = PresentationContext(other, 1)
        self.assertEqual(gallery_presenter(context)["official_entries"], [])

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_an_over_budget_identity_is_skipped_with_one_diagnostic(self):
        # 180 code points fit the identity bound but push the fingerprinted URL
        # past the shared portrait ceiling, so the row is omitted, not fatal.
        long_name = "x" * (180 - len(f"preset/{_PRESET_KEY}/") - len(".png")) + ".png"
        skipped = self._index(long_name)
        listed = self._index("a.png")
        self.assertGreater(
            len(current_catalog().url_for(skipped)), GALLERY_MAX_OFFICIAL_URL
        )
        with patch("web.webclient.presentation.gallery.log_warn") as warn:
            value = gallery_presenter(self.context)
        self.assertEqual(
            [row["identity"] for row in value["official_entries"]], [listed]
        )
        events = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "gallery_official_entry_skipped"
        ]
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["identity"], skipped)
        self.assertEqual(
            events[0].kwargs["context"]["subject"], self.subject.full()
        )

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_building_the_panel_with_official_entries_mutates_nothing(self):
        identity = self._index("a.png")
        api.set_official_selection(self.subject, identity)
        api.set_official_geometry(
            self.subject, identity, stage={"scale": 0.6, "x": 0.0, "y": -0.2}
        )
        before_records = [
            (row.pk, repr(row.attributes.all()))
            for row in api.GalleryRecord.objects.all()
        ]
        before_files = {
            path.relative_to(self.store).as_posix(): path.read_bytes()
            for path in self.store.rglob("*")
            if path.is_file()
        }
        first = gallery_presenter(self.context)
        self.assertEqual(gallery_presenter(self.context), first)
        self.assertEqual(
            [
                (row.pk, repr(row.attributes.all()))
                for row in api.GalleryRecord.objects.all()
            ],
            before_records,
        )
        self.assertEqual(
            {
                path.relative_to(self.store).as_posix(): path.read_bytes()
                for path in self.store.rglob("*")
                if path.is_file()
            },
            before_files,
        )
        self.assertTrue(first["official_entries"][0]["is_current"])

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-payload-is-exactly-version-mirrored-across-server-and-client"
    )
    def test_official_bounds_keep_their_single_origin(self):
        self.assertEqual(GALLERY_MAX_OFFICIAL_IDENTITY, api.OFFICIAL_IDENTITY_MAX)
        self.assertEqual(GALLERY_MAX_OFFICIAL_URL, MAX_PORTRAIT_MEDIA_URL)
        self.assertEqual(GALLERY_MAX_OFFICIAL_URL, 256)
        self.assertEqual(GALLERY_MAX_OFFICIAL_ENTRIES, 32)
