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
from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET
from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

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
    SLOT_LABELS,
    gallery_presenter,
    gallery_subjects,
    validate_gallery,
)
from web.webclient.presentation.gallery_selection import gallery_selection_snapshot, select_gallery_subject
from web.webclient.presentation.ingress import build_presentation_context, reset_client_sequence, _coordinator_for
from web.webclient.presentation.protocol import ProtocolValidationError
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
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validateGalleryPanel(value)]; }
  catch (_) { return [name, false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.run(["node", "-e", script], input=json.dumps(cases), text=True, capture_output=True, cwd=ROOT, check=True)
        js_results = json.loads(output.stdout)
        for (name, value, expected), (_, js_accepts, echoed) in zip(cases, js_results, strict=True):
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


class GalleryPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = override_settings(ART_STORE_ROOT=self.tmp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.actor = create_object(PlayerCharacter, key="測試主角", location=self.room1)
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
        self.assertEqual(value["cards"], [])
        self.assertEqual(value["filters"], dict.fromkeys(("all", "defaults", "bound", "pending", "failed"), 0))
        self.assertEqual(value["selected"], self.subject.full())
        self.assertEqual(api.GalleryRecord.objects.count(), before)
        self.actor.creation_pending = True
        self.assertEqual(self.registry.render("gallery", self.context)["reason"]["code"], "gallery_unavailable")

    @covers_requirement(
        "webclient-gallery-panel::the-subject-rail-names-every-gallery-bearing-subject-with-companion-first-ordering"
    )
    def test_rail_prioritizes_companions_reserves_monsters_and_skips_corruption(self):
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
        "webclient-gallery-panel::filter-counts-and-the-equipment-summary-are-server-computed",
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
        self.assertEqual(value["filters"], {"all": 3, "defaults": 1, "bound": 3, "pending": 0, "failed": 0})

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
        self.assertEqual(value["filters"]["bound"], 8)

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
        self.assertEqual(value["filters"]["pending"], 7)
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
        self.assertEqual(value["filters"]["all"], 2)
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

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_selection_is_transport_owned_and_retired_by_real_unpuppet_signal(self):
        a, b = self.make_session(), self.make_session()
        selected = "portrait:monster:t_beast"
        with patch("web.webclient.presentation.gallery_selection.log_info") as event:
            res = select_gallery_subject(a, self.actor, selected)
            self.assertEqual(res["outcome"], "success")
            self.assertNotIn("affected_panels", res)
            select_gallery_subject(a, self.actor, selected)
            event.assert_called_once_with("gallery_panel_selected", context={"subject": selected, "kind": "portrait:monster"})
        self.assertIsNone(gallery_selection_snapshot(b, self.actor))
        self.assertEqual(select_gallery_subject(a, self.actor, "scene:t_scene")["code"], "unknown_subject")
        self.assertEqual(gallery_selection_snapshot(a, self.actor), selected)
        value = gallery_presenter(build_presentation_context(a, self.actor))
        self.assertEqual(value["selected"], selected)
        self.assertIsNone(value["equipment_summary"])
        self.assertFalse(value["capabilities"]["supports_bindings"])
        SIGNAL_OBJECT_POST_UNPUPPET.send(sender=self.actor, session=a, account=self.account)
        self.assertIsNone(a.ndb.gallery_selection)
        self.assertIsNone(gallery_selection_snapshot(a, self.actor))
        select_gallery_subject(a, self.actor, selected)
        reset_client_sequence(a)
        self.assertIsNone(gallery_selection_snapshot(a, self.actor))
        select_gallery_subject(a, self.actor, selected)
        a.ndb.elosern_actor_id = str(self.actor.pk)
        other = create_object(PlayerCharacter, key="新角色")
        a.puppet = other
        _coordinator_for(a, other)
        self.assertIsNone(a.ndb.gallery_selection)

    @covers_requirement(
        "webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer"
    )
    def test_deleted_selected_character_falls_back_without_writing(self):
        other = create_object(NPC, key="待刪角色")
        other.db.portrait_policy = {"mode": "named", "stable_key": "t_deleted"}
        session = self.make_session()
        select_gallery_subject(session, self.actor, "portrait:character:t_deleted")
        frozen = build_presentation_context(session, self.actor)
        other.delete()
        self.assertEqual(gallery_presenter(frozen)["selected"], self.subject.full())
        self.assertEqual(session.ndb.gallery_selection.subject_key, "portrait:character:t_deleted")


_PRESET_KEY = "t_gallery_preset"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class OfficialEntryProjectionTests(EvenniaTest):
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
        # Official rows are never cards, and the filter tabs keep counting only
        # the card rows.
        self.assertEqual([row["image_id"] for row in value["cards"]], [card["image_id"]])
        self.assertEqual(
            list(value["filters"]), ["all", "defaults", "bound", "pending", "failed"]
        )
        self.assertEqual(value["filters"]["all"], 1)
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
