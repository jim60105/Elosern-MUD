"""Art-record seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

from pathlib import Path

from web.tests.browser.seed.identity import FIXTURE_VALID_PNG


#: The deterministic image id of the seeded ``done`` scene card. The
#: image-load-failure journey routes this card's exact media path, so the
#: identity must stay stable across runs.
ART_SCENE_IMAGE_ID = "10000000-0000-4000-8000-0000000ed176"

#: The decoded size of the fixture PNG the seeded scene card stores.
SCENE_CARD_SIZE = {"width": 4, "height": 4}


def _art_fixture(character, room) -> None:
    """Deterministically prepare art records for browser acceptance.

    Opted-in with ``ELOSERN_BROWSER_ART=<mode>``. Each mode places the
    character in a room that carries the validated ``scene_archetype`` seam and
    writes the scene's real gallery state (a card for ``done``, one in-flight
    gallery job for ``pending``, and that job settled failed for ``failed``)
    through the production writers, plus the named portrait records the art
    panel admits. Every stored file is written under the runtime art store, so
    browser journeys can assert the real scene renderer and portrait catalog
    without any image service. ``missing`` leaves records untouched (missing
    placeholders). No remote, LLM, or image service is involved.
    """
    import os

    from evennia.utils.create import create_object
    from typeclasses.monsters import Monster
    from typeclasses.rooms import GridRoom
    from world.art.queue import ensure, settle
    from world.art.store import ArtAssetStatus
    from world.art.subjects import (
        ArtSubject,
        ArtSubjectKind,
        character_subject_for,
    )

    mode = os.environ.get("ELOSERN_BROWSER_ART", "")
    if not mode or os.environ.get("ELOSERN_BROWSER_SERVICES"):
        return

    from web.browser_support.browser_fixtures_data import (
        SHIPPED_ART_ARCHETYPE,
        SHIPPED_DIALOGUE_HOST_KEY,
        SHIPPED_DIALOGUE_KEY,
        SHIPPED_MONSTER_TIER_KEY,
        SHIPPED_MONSTER_TIER_ATTR,
        SYNTH_ART_ARCHETYPE,
        SYNTH_DIALOGUE_HOST_KEY,
        SYNTH_DIALOGUE_TABLE_KEY,
        art_room_monster_key,
        first_live_monster_tier_key,
        scene_archetype_registered,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    archetype = SYNTH_ART_ARCHETYPE if synth else SHIPPED_ART_ARCHETYPE
    if not scene_archetype_registered(archetype):
        raise AssertionError("art fixture archetype must be a registered scene")

    art_room = create_object(
        GridRoom, key="art 合成場景" if synth else "art 酒館場景", nohome=True, location=None
    )
    art_room.scene_archetype = archetype
    # Supported map construction always writes the logical place identity
    # beside the archetype; only an authored identity authorizes retained
    # scene content, so the fixture writes one exactly as the map owner does.
    art_room.scene_identity = f"instance:art-fixture-{character.pk}"
    character.location = art_room
    character.db.portrait_policy = {
        "mode": "named",
        "stable_key": f"browser-{character.pk}",
    }
    # A present named-policy NPC and a living monster so combat catalog tests
    # have both a dialogue host and a generic monster in the room.
    from typeclasses.npcs import NPC, ensure_npc_canonical_age

    host = create_object(
        NPC,
        key=SYNTH_DIALOGUE_HOST_KEY if synth else SHIPPED_DIALOGUE_HOST_KEY,
        location=art_room,
    )
    from typeclasses.components import ScriptedDialogue

    host.components.add(
        ScriptedDialogue.create(
            host, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY if synth else SHIPPED_DIALOGUE_KEY
        )
    )
    # A named portrait policy on the dialogue host: the actor is excluded from
    # its own exploration-mode portrait catalog (art_view), so the focusable
    # catalog entry is the host's; settling it done gives the portrait
    # entry a URL to render.
    host.db.portrait_policy = {
        "mode": "named",
        "stable_key": "browser-host",
    }
    # The host must carry canonical age attributes, or the presenter resolves
    # its catalog entry to the unavailable placeholder (status/url both None)
    # even when its art record is done.
    ensure_npc_canonical_age(host)
    host.save()
    monster = create_object(
        Monster,
        key=art_room_monster_key(),
        location=art_room,
        nohome=True,
    )
    monster.threat_tier = (
        first_live_monster_tier_key() if synth else SHIPPED_MONSTER_TIER_ATTR
    )
    # Band position (not a registry key): free-form in either mode.
    monster.apply_monster_tier(SHIPPED_MONSTER_TIER_KEY)
    character.save()

    art_root = os.environ.get("ELOSERN_BROWSER_ART_ROOT")
    if not art_root:
        return
    root = Path(art_root)

    scene = ArtSubject(ArtSubjectKind.SCENE, archetype)
    if mode == "done":
        from world.art import gallery as gallery_api

        # The scene chain reads the scene gallery's default card and nothing
        # else (``scene-classic-fallback-removal``), so the fixture appends a
        # real card through the sole writer instead of a classic record.
        identity = f"gallery/scene/{archetype}/{ART_SCENE_IMAGE_ID}.png"
        path = root.joinpath(*identity.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(FIXTURE_VALID_PNG)
        gallery_api.append_card(
            scene,
            image_id=ART_SCENE_IMAGE_ID,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
            image_size=dict(SCENE_CARD_SIZE),
        )
        from world.art.queue import claim, record_key
        from world.art.store import ArtAssetRecord

        # Ensure the named portrait records exist and claim every pending
        # record (the startup sync enqueued ~10 scenes, the monster tiers,
        # and the named portraits) so the scene and both named portraits
        # settle as done, giving the portrait entries
        # a URL to render.
        host_subject = character_subject_for(host)
        actor_subject = character_subject_for(character)
        for subject in (actor_subject, host_subject):
            if subject is not None:
                ensure(subject, "desc")
        claimed = claim(50)
        tokens = {record.db_key: str(record.db.generation_token) for record in claimed}
        (root / "portrait" / "character").mkdir(parents=True, exist_ok=True)
        for subject, stable_key in (
            (actor_subject, f"browser-{character.pk}"),
            (host_subject, "browser-host"),
        ):
            if subject is None:
                continue
            # Fail loudly if the portrait record was not claimed (claim budget
            # 50 would otherwise leave it PENDING and settle is a silent
            # no-op), instead of a later browser timeout.
            record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
            if record is None:
                raise RuntimeError(f"art fixture: no art record for {stable_key}")
            if record.db.status != ArtAssetStatus.IN_PROGRESS:
                raise RuntimeError(
                    f"art fixture: portrait record {stable_key} not claimed "
                    f"(status={record.db.status}); claim budget too small"
                )
            portrait_identity = f"portrait/character/{stable_key}.png"
            (root / portrait_identity).write_bytes(FIXTURE_VALID_PNG)
            settle(
                subject,
                generation_token=tokens[record_key(subject)],
                status=ArtAssetStatus.DONE,
                output_identity=portrait_identity,
                error=None,
            )
    elif mode in ("pending", "failed"):
        # One real scene gallery request: the pending journey needs an
        # in-flight job with NO card (so the chain presents the required
        # bundled illustration), and the failed mode settles that same job
        # terminal so the recorded error is a reached fact.
        from world.art.queue import claim, gallery_record_key, settle_gallery_failed
        from world.art.service import request_gallery_image
        from world.art.store import ArtAssetRecord

        image_id = request_gallery_image(scene)
        if mode == "failed":
            claim(50)
            job_key = gallery_record_key(scene, image_id)
            record = ArtAssetRecord.objects.filter(db_key=job_key).first()
            if record is None or record.db.status != ArtAssetStatus.IN_PROGRESS:
                raise RuntimeError(
                    f"art fixture: scene gallery job {image_id} not claimed "
                    f"(status={None if record is None else record.db.status})"
                )
            settle_gallery_failed(
                job_key,
                generation_token=str(record.db.generation_token),
                error="fixture",
            )
    print(f"seeded art fixture: {mode}")

