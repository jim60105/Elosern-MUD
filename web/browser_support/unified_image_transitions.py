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

import os
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
        "reuse_place",
        "repaired_original",
        "revoke_source",
        "unavailable_panel",
    }
)

# The SCENE mode's transitions (change unified-scene-rendering): every one goes
# through the real owner — the queue's requeue/claim/settle for the scene
# record's own generation state, and the map-owned room attributes for the
# binding/movement transitions — followed by the presentation coordinator's
# normal refresh. A journey never mutates the browser store to claim a backend
# transition was accepted.
SCENE_TRANSITIONS = frozenset(
    {
        "pending_scene",
        "failed_scene",
        "done_scene",
        "remove_room_binding",
        "move_scene",
        "reuse_place",
    }
)

# The runtime identity the scene fixture's authored room metadata carries: the
# same shape supported map construction writes, so a scene journey reads a real
# logical place identity.
SCENE_FIXTURE_IDENTITY_PREFIX = "instance:art-fixture-"

# The transitions this slice owns. Every other name belongs to another mode's
# owning change and is rejected rather than guessed at.
#
# ``revoke_source`` is the portrait mode's own availability transition
# (unified-portrait-image-contract): it removes the subject's committed real
# artwork through the production writer, so the very next presentation states
# the truth — the descriptor keeps its admission and its alpha terminal while
# carrying no real candidate. ``unavailable_panel`` is deliberately NOT a
# server mutation: a missing or unavailable panel is a committed-payload fact,
# so journeys express it by injecting the panel's own unavailable form (the
# client's ``artworkAvailability`` then reports ``failed`` locally) rather than
# by corrupting art state.
OWNED_TRANSITIONS = frozenset({"repaired_original", "revoke_source"}) | SCENE_TRANSITIONS

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

# The portrait descriptor mode (``unified-portrait-image-contract``). The
# player's own activated character carries the committed card every roster
# figure reads; the companion and focus identities below are the co-located
# party member and the present focus entity a journey admits beside it, so one
# bounded art view covers the roster, party, focus, dialogue and combat scopes
# at once. Deterministic identities keep the seeded subjects stable across
# runs.
PORTRAIT_IMAGE_ID = "10000000-0000-4000-8000-0000000ed174"
# The companion's own committed card: the focus/party/combat surfaces must be
# able to present a REAL candidate, not only the fallback terminal.
PORTRAIT_COMPANION_IMAGE_ID = "10000000-0000-4000-8000-0000000ed175"
PORTRAIT_COMPANION_KEY = "browser_portrait_companion"
PORTRAIT_FOCUS_KEY = "browser_portrait_focus"


def seed_portrait_companions(character) -> list[str]:
    """Seed one co-located live party companion and one present focus entity.

    Both are created through the ordinary Evennia object API and joined to the
    player's party through the production party writer, so the exploration art
    view admits them by its own membership rule (a live companion present in
    the room, and a present named-policy character) rather than by any test-only
    back door. The focus entity carries a named portrait policy so its own
    subject exists; neither is given real artwork, because the point of the
    mode is that an admitted subject without imagery still carries its complete
    descriptor.
    """
    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object

    from typeclasses.npcs import LLMNPC
    from world.rules.party import join_party
    from world.art.subjects import character_subject_for

    location = character.location
    if location is None:
        return []

    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    # A living companion's mechanical baseline: the race baseline supplies the
    # stored HP gauge the party and combat readers require, which only an
    # initialized trait configuration provides. The synthetic install registers
    # the kit race alone, so the baseline key follows the boot mode.
    companion_race = (
        "t_duskmari"
        if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
        else "human"
    )

    seeded: list[str] = []
    for index, key in enumerate((PORTRAIT_COMPANION_KEY, PORTRAIT_FOCUS_KEY)):
        existing = ObjectDB.objects.filter(db_key=key).first()
        npc = existing or create_object(LLMNPC, key=key, location=location)
        npc.location = location
        npc.db.portrait_policy = {"mode": "named", "stable_key": key}
        # Both canonical age fields: presentation refuses a subject whose ages
        # are missing or malformed, so a seeded companion must carry them.
        npc.db.age = 30
        npc.db.apparent_age = 30
        npc.race = companion_race
        npc.apply_race_baseline()
        join_party(npc, character)
        # The committed card is written under the subject PRESENTATION derives
        # from the policy's stable key, not under the object identity: a card
        # in any other gallery can never be the descriptor's candidate.
        subject = character_subject_for(npc)
        if subject is None:
            raise AssertionError(f"seeded companion {key!r} carries no portrait subject")
        append_original_card(
            subject.full(),
            f"{PORTRAIT_COMPANION_IMAGE_ID[:-1]}{index + 5}",
            FIXTURE_VALID_PNG,
            set_default=True,
        )
        seeded.append(str(npc.pk))
    return seeded


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


def _revoke_source(subject_key: str, image_id: str | None, payload: bytes) -> dict:
    """Remove the subject's committed real artwork (the portrait fallback case).

    Every stored card of the subject goes through the production writer, so the
    next presentation enumerates the same subject with no real candidate and
    the descriptor's own alpha terminal is all that remains. The subject stays
    admitted and keeps its reference: only its imagery is revoked.
    """
    from world.art import gallery as gallery_api
    from world.art.subjects import parse_subject

    subject = parse_subject(subject_key)
    snapshot = gallery_api.snapshot_for(subject)
    removed = [card["image_id"] for card in snapshot.get("cards", [])]
    for stored_id in removed:
        gallery_api.remove_card(subject, stored_id)
    return {"subject_key": subject.full(), "revoked": removed}


_APPLIERS = {
    "repaired_original": _repaired_original,
    "revoke_source": _revoke_source,
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


def scene_subject_for_room(room):
    """The scene subject the CURRENT room's authored metadata resolves to.

    ``None`` when the room carries no registered archetype: a transition that
    needs a scene record then has nothing to act on, which the caller reports
    instead of guessing a subject.
    """
    from world.art.subjects import ArtSubjectError, scene_subject_for

    archetype = getattr(room, "scene_archetype", None)
    try:
        return scene_subject_for(archetype)
    except ArtSubjectError:  # observability: ignore R2: an unusable authored archetype is a reported no-op
        return None


def _settle_scene(character, status: str, *, publish: bool) -> dict:
    """Run one real scene generation lifecycle for the character's current room.

    ``pending_scene`` requeues the record, which preserves the prior valid
    output (the descriptor keeps authorizing it); ``failed_scene`` requeues and
    then settles the claimed regeneration as failed; ``done_scene`` publishes a
    fresh readable output under the runtime store and settles it done. Every
    step uses the record's OWN claim token, never an assumed index.
    """
    from django.conf import settings

    from world.art.queue import claim, record_key, requeue, settle
    from world.art.store import ArtAssetRecord, ArtAssetStatus

    subject = scene_subject_for_room(character.location)
    if subject is None:
        raise UnsupportedTransitionError("the current room carries no registered scene archetype")
    job = {
        "pending_scene": ArtAssetStatus.PENDING,
        "failed_scene": ArtAssetStatus.FAILED,
        "done_scene": ArtAssetStatus.DONE,
    }[status]
    # Every one of these transitions is a REGENERATION of the same scene: the
    # record must be requeued first (which also preserves its prior valid
    # output, so the descriptor keeps authorizing it) before a fresh claim can
    # own a token. Claiming a done record directly would find nothing.
    requeue(subject)
    if job == ArtAssetStatus.PENDING:
        return {"subject_key": subject.full(), "status": job}
    claimed = claim(ArtAssetRecord.objects.count() + 1)
    record = next((item for item in claimed if item.db_key == record_key(subject)), None)
    if record is None:
        raise UnsupportedTransitionError("the scene record was not claimable")
    identity = None
    if job == ArtAssetStatus.DONE:
        identity = f"scene/{subject.key}.png"
        path = Path(settings.ART_STORE_ROOT).joinpath(*identity.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fixture_png())
    settle(
        subject,
        status=job,
        output_identity=identity,
        error=None if job == ArtAssetStatus.DONE else "fixture",
        generation_token=str(record.db.generation_token),
    )
    del publish
    return {"subject_key": subject.full(), "status": job}


def _remove_room_binding(character) -> dict:
    """Remove the current room's authored room-art binding (map-owned metadata).

    The room keeps its archetype, so the chain simply continues without the
    per-room override — exactly what a map-owner sync writes when a declaration
    no longer applies.
    """
    room = character.location
    if room is None:
        raise UnsupportedTransitionError("the character is in no room")
    previous = getattr(room, "room_art_key", None)
    room.room_art_key = None
    return {"room": int(room.pk), "removed": previous}


def _move_scene(character) -> dict:
    """Move the character to a room with DIFFERENT logical scene metadata.

    The destination is built through the ordinary Evennia object API carrying
    the same authored attribute contract supported construction uses, so the
    committed scene identity changes exactly as a real move makes it.
    """
    from evennia.utils.create import create_object

    from typeclasses.rooms import Room

    room = character.location
    if room is None:
        raise UnsupportedTransitionError("the character is in no room")
    destination = create_object(Room, key="unified scene destination", location=None)
    destination.scene_archetype = getattr(room, "scene_archetype", None)
    destination.scene_identity = f"{SCENE_FIXTURE_IDENTITY_PREFIX}moved-{destination.pk}"
    destination.room_art_key = None
    # Remember the place the character leaves, so a later ``reuse_place`` can
    # return to that EXISTING object: re-entering a committed place is the
    # movement case where a logical identity comes back.
    character.db.browser_scene_return_room = int(room.pk)
    character.location = destination
    return {"room": int(destination.pk)}


def _reuse_place(character) -> dict:
    """Move the character back to the place it last left.

    The destination is the EXISTING room object the character came from, so the
    committed logical identity returns rather than a fresh place appearing.
    """
    from evennia.objects.models import ObjectDB

    identity = getattr(character.db, "browser_scene_return_room", None)
    if not identity:
        raise UnsupportedTransitionError("no previously left place is recorded")
    destination = ObjectDB.objects.filter(id=int(identity)).first()
    if destination is None:
        raise UnsupportedTransitionError("the previously left place no longer exists")
    character.location = destination
    return {"room": int(destination.pk)}


def _fixture_png() -> bytes:
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    return FIXTURE_VALID_PNG


def apply_transition(
    name: str,
    subject_key: str,
    *,
    image_id: str | None = None,
    payload: bytes | None = None,
    character=None,
) -> dict:
    """Apply one owned transition and return its stored/changed fact."""
    if name not in TRANSITIONS:
        raise UnsupportedTransitionError(f"unknown transition {name!r}")
    if name in SCENE_TRANSITIONS:
        if character is None:
            raise UnsupportedTransitionError("a scene transition needs the acting character")
        if name == "remove_room_binding":
            return _remove_room_binding(character)
        if name == "move_scene":
            return _move_scene(character)
        if name == "reuse_place":
            return _reuse_place(character)
        return _settle_scene(character, name, publish=True)
    handler = _APPLIERS.get(name)
    if handler is None:
        raise UnsupportedTransitionError(
            f"transition {name!r} belongs to another mode's owning change"
        )
    if payload is None:
        payload = _fixture_png()
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
            stored = apply_transition(name, subject_key, image_id=image_id, character=self.caller)
        except UnsupportedTransitionError as error:
            self.caller.msg(str(error))
            return
        summary = (
            stored.get("image_id")
            or stored.get("status")
            or str(stored.get("room") or "")
            or ",".join(stored.get("revoked") or [])
            or "none"
        )
        self.caller.msg(f"transition {name} applied: {summary}")
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
