"""Shared identity/card factories and fake entities for the
``test_gallery`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import patch
import uuid
import unittest
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase
from world.art import gallery_kinds
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecord,
    GalleryRecordError,
    SLOT_ORDER,
    append_card,
    cards_for,
    clear_error,
    erroring_subjects,
    gallery_states,
    record_error,
    record_for,
    record_key,
    remove_card,
    set_default,
    snapshot_for,
    validate_binding,
    validate_card,
    validate_face_rect,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[4]

def _character(key="heron"):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)

def _monster(key="goblin"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)

# Gallery records key identity-only scene subjects; the shipped archetype
# vocabulary is irrelevant to card/record mechanics, so the default is a
# file-local synthetic scene identity.
def _scene(key="t_synth_scene"):
    return ArtSubject(ArtSubjectKind.SCENE, key)

def _new_id():
    return str(uuid.uuid4())

def _identity(subject, image_id, extension=".png"):
    kind_dir = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
    return f"gallery/{kind_dir}/{subject.key}/{image_id}{extension}"

def _card_fields(subject, image_id=None, **overrides):
    """One complete generated-source card, overridable per key."""
    image_id = image_id or _new_id()
    fields = {
        "image_id": image_id,
        "stored_identity": _identity(subject, image_id),
        "prompt": {"positive": "a hero", "negative": "blur"},
        "seed": 1234,
        "checkpoint": "realVision.safetensors",
        # Declaration-aware: a kind whose capability supports no field
        # selection may only ever store an empty provenance (the write
        # boundary enforces it, ``gallery-monster-generation``).
        "requested_fields": (
            ["appearance"]
            if gallery_kinds.capabilities_for(subject.kind.value).supports_field_selection
            else []
        ),
        "binding": None,
        "source": "generated",
    }
    fields.update(overrides)
    return fields

class _FakeDb:
    """Minimal ``entity.db`` namespace: reads return the stored value/None."""

    def __init__(self, values=None):
        self._values = dict(values or {})

    def __getattr__(self, name):
        return self._values.get(name)

    def get(self, name, default=None):
        return self._values.get(name, default)

class _FakeEntity:
    def __init__(self, equipment=...):
        values = {} if equipment is ... else {"equipment": equipment}
        self.db = _FakeDb(values)
