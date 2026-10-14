"""Bounded test-only live transitions for the unified image resolution family.

The browser journeys of the family need to change committed server state
*after* the server resolved and serialized a panel. This module is that
bounded seam: a small, test-only ``Command``/``CmdSet`` that applies one named
transition through the real production writers and then refreshes the
presentation through the documented ``refresh_after_command`` path. It is
installed by the browser seed only (``seed/runner.py`` under the unified-image
flag) and is never part of the production command surface.

``TRANSITIONS`` is the family-wide closed vocabulary. Each owning change
implements only its own mode's entries: ``unified-image-loading-core`` owns the
face-rectangle original editor's ``repaired_original``. A later change adds its
own mode here — no second mechanism, and no client-manufactured business fact:
the transition writes real records through ``world/art/gallery.py``.
"""

from __future__ import annotations

from pathlib import Path

from evennia import Command, CmdSet

# The family-wide closed vocabulary of allowed transitions.
TRANSITIONS = frozenset(
    {
        "pending_scene",
        "failed_scene",
        "done_scene",
        "remove_room_binding",
        "move_scene",
        "repaired_original",
        "revoke_source",
        "unavailable_panel",
    }
)

# The transitions this slice owns. Every other name belongs to another mode's
# owning change and is rejected rather than guessed at.
OWNED_TRANSITIONS = frozenset({"repaired_original"})

# Deterministic identities for the seeded and the repaired original. The
# repaired card is deliberately distinct from the seeded one, so a recovery
# journey can assert the exact new card identity.
SEEDED_ORIGINAL_IMAGE_ID = "10000000-0000-4000-8000-0000000ed171"
REPAIRED_ORIGINAL_IMAGE_ID = "10000000-0000-4000-8000-0000000ed172"

# The exact decoded size of the fixed PNG fixture every seeded original uses.
ORIGINAL_IMAGE_SIZE = {"width": 4, "height": 4}

# The gallery v3 row seed (``unified-gallery-image-contract``). The pending and
# failed rows attach to a monster subject — never the puppet — because a pending
# row is newest-first and would otherwise reorder the puppet's own card rail
# under the loading-core journeys.
GALLERY_PENDING_IMAGE_ID = "10000000-0000-4000-8000-0000000ed173"
GALLERY_FAILED_ERROR_CODE = "sd_connection_error"
# The manifest-declared filename of the seeded operator content directory.
GALLERY_OFFICIAL_FILENAME = "a.png"
GALLERY_MANIFEST_FILENAME = "manifest.json"


class UnsupportedTransitionError(ValueError):
    """Raised for a transition name this slice does not own."""


def store_identity_for(subject_key: str, image_id: str) -> str:
    """The exact stored identity of one original card for a subject."""
    from world.art.gallery_kinds import capabilities_for
    from world.art.subjects import parse_subject

    subject = parse_subject(subject_key)
    kind_directory = capabilities_for(subject.kind.value).store_directory
    return f"gallery/{kind_directory}/{subject.key}/{image_id}.png"


def append_original_card(
    subject_key: str,
    image_id: str,
    payload: bytes,
    *,
    set_default: bool = True,
) -> dict:
    """Append one real original card through the production gallery writers.

    The bytes are written under the runtime art store first, exactly as a
    settled generation would, and the card is then appended and (optionally)
    selected through ``world/art/gallery.py`` — the sole writer.
    """
    from django.conf import settings

    from world.art import gallery as gallery_api
    from world.art.subjects import parse_subject

    subject = parse_subject(subject_key)
    identity = store_identity_for(subject_key, image_id)
    path = Path(settings.ART_STORE_ROOT).joinpath(*identity.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    stored = gallery_api.append_card(
        subject,
        image_id=image_id,
        stored_identity=identity,
        prompt=None,
        seed=None,
        checkpoint=None,
        requested_fields=[],
        binding=None,
        source="seed",
        image_size=dict(ORIGINAL_IMAGE_SIZE),
    )
    if set_default:
        gallery_api.set_default(subject, image_id)
    return stored


def _repaired_original(subject_key: str, image_id: str, payload: bytes) -> dict:
    """Append and select a distinct real original (gallery recovery)."""
    return append_original_card(subject_key, image_id, payload, set_default=True)


_APPLIERS = {
    "repaired_original": _repaired_original,
}


def seed_official_content(character) -> str | None:
    """Write one real operator content directory for the character's own preset key.

    The bytes and their manifest land under the journey's configured
    ``ART_OFFICIAL_ROOT`` BEFORE server startup, so the startup index admits
    them exactly like a deployed catalog and the gallery's official rows come
    from the real snapshot. ``None`` when the character declares no preset
    provenance or the journey configured no official root.

    A character whose activation path wrote no (or an unregistered) preset
    provenance is given the first registered shipped preset key: a
    preset-born character's reference is exactly that provenance, so the
    journey exercises the real resolver rather than a synthetic shortcut.
    """
    import json
    import os

    from django.conf import settings

    from world.art.official_refs import PLAYER_PRESET_REGISTRY, PRESET_PROVENANCE_ATTRIBUTE
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    root = os.environ.get("ART_OFFICIAL_ROOT") or str(
        getattr(settings, "ART_OFFICIAL_ROOT", "") or ""
    )
    if not root:
        return None
    key = character.attributes.get(PRESET_PROVENANCE_ATTRIBUTE)
    if not isinstance(key, str) or not key or key not in PLAYER_PRESET_REGISTRY:
        registered = sorted(PLAYER_PRESET_REGISTRY)
        if not registered:
            return None
        key = registered[0]
        character.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, key)
    folder = Path(root) / "preset" / key
    folder.mkdir(parents=True, exist_ok=True)
    (folder / GALLERY_OFFICIAL_FILENAME).write_bytes(FIXTURE_VALID_PNG)
    (folder / GALLERY_MANIFEST_FILENAME).write_text(
        json.dumps({"default": GALLERY_OFFICIAL_FILENAME}), encoding="utf-8"
    )
    return f"preset/{key}/{GALLERY_OFFICIAL_FILENAME}"


def seed_pending_and_failed_rows() -> str | None:
    """Enqueue one real pending job and record one real failure on a monster.

    Both go through the production writers (``enqueue_gallery_job``,
    ``gallery.record_error``), so the panel projects the synthetic rows exactly
    as it projects a live request. ``None`` when no monster subject is
    registered.
    """
    from world.art import gallery as gallery_api
    from world.art.queue import enqueue_gallery_job
    from world.art.subjects import monster_subject_for
    from world.lore.monster_visuals import get_monster_visual_registry

    keys = sorted(get_monster_visual_registry())
    if not keys:
        return None
    subject = monster_subject_for(keys[0])
    enqueue_gallery_job(
        subject,
        "gallery v3 row fixture",
        image_id=GALLERY_PENDING_IMAGE_ID,
        binding=None,
        face_rect=None,
        requested_fields=[],
    )
    gallery_api.record_error(subject, GALLERY_FAILED_ERROR_CODE)
    return subject.full()


def apply_transition(
    name: str,
    subject_key: str,
    *,
    image_id: str | None = None,
    payload: bytes | None = None,
) -> dict:
    """Apply one owned transition and return the stored card."""
    if name not in TRANSITIONS:
        raise UnsupportedTransitionError(f"unknown transition {name!r}")
    handler = _APPLIERS.get(name)
    if handler is None:
        raise UnsupportedTransitionError(
            f"transition {name!r} belongs to another mode's owning change"
        )
    if payload is None:
        from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

        payload = FIXTURE_VALID_PNG
    if name == "repaired_original" and image_id is None:
        image_id = REPAIRED_ORIGINAL_IMAGE_ID
    return handler(subject_key, image_id, payload)


class CmdUnifiedImageTransition(Command):
    """Bounded test-only transition command (never installed in production)."""

    key = "uieditor_transition"
    locks = "cmd:all()"
    help_category = "Test"

    def func(self) -> None:
        args = self.args.strip().split()
        if not args:
            self.caller.msg("usage: uieditor_transition <name> [image_id]")
            return
        name = args[0]
        image_id = args[1] if len(args) > 1 else None
        subject_key = f"portrait:character:{self.caller.pk}"
        try:
            stored = apply_transition(name, subject_key, image_id=image_id)
        except UnsupportedTransitionError as error:
            self.caller.msg(str(error))
            return
        self.caller.msg(f"transition {name} applied: {stored['image_id']}")
        session = getattr(self, "session", None)
        if session is not None:
            from web.webclient.presentation.ingress import refresh_after_command

            refresh_after_command(session, self.caller)


class UnifiedImageTransitionCmdSet(CmdSet):
    """The test-only cmdset carrying the bounded transition command."""

    key = "unified_image_transitions"
    priority = 120

    def at_cmdset_creation(self) -> None:
        self.add(CmdUnifiedImageTransition)


def install_transition_cmdset(character) -> None:
    """Attach the bounded transition cmdset to the seeded character only."""
    character.cmdset.add(UnifiedImageTransitionCmdSet, persistent=True)
