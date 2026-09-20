"""File-local synthetic-scope helper and kit vocabularies for the
``test_service`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""

from unittest.mock import patch
import unittest
from contextlib import contextmanager
import tempfile
from pathlib import Path
from django.db import transaction
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.art.queue import ensure, record_key, source_hash
from world.art import gallery as gallery_api
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.gallery_prompt import (
    CUSTOM_PROMPT_MAX,
    GalleryPromptError,
)
from world.art.sd_worker import SDError
from world.art.service import requeue_gallery_subject
from world.art.service import prune_gallery_orphans
from world.art.subjects import (
    ArtSubjectError,
    monster_description,
    monster_subject_for,
    scene_subject_for,
)
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    request_gallery_image,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_ITEMS,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

def open_synthetic_scope(case, *targets, extra=None):
    """Enter a synthetic-catalog scope bound to one test case's lifecycle.

    The kit's class decorator wraps ``test*`` methods only, so anything a
    ``setUp`` builds against the catalogs would escape its scope. Call this as
    the FIRST statement of ``setUp`` (before ``super().setUp()``); the scope is
    torn down with the test via ``case.addCleanup``.
    """
    scope = synthetic_registries(*targets, extra=extra)
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope

# The kit's archetype/tier vocabularies replace the shipped catalogs for every
# startup-sync loop below: the tests own the SYNCHRONIZATION MECHANICS (one
# record per registered subject, idempotency, bounded failure), never the
# shipped content, so the loops iterate the patched kit catalogs instead.
_SYNTH_SCENES = sorted(SYNTH_ARCHETYPES)

_SYNTH_TIERS = sorted(SYNTH_MONSTER_TIERS)

_SYNTH_SCENE = _SYNTH_SCENES[0]

# Synthetic gear identities for the equipment-binding/selection mechanics.
_SYNTH_WEAPON = "t_thorn_knife"

_SYNTH_OFFHAND = "t_iron_fang"

_SYNTH_ARMOR = "t_wayfarer_pass"

_SYNTH_TRINKET = "t_huskapple"

def _scene(key):
    return ArtSubject(ArtSubjectKind.SCENE, key)

def _valid_binding():
    return {"mask": ["armor"], "snapshot": {"armor": _SYNTH_ARMOR}}
