"""Behavior tests for the species-keyed official monster portrait identity.

``species-portrait-identity``: a species-backed monster resolves its official
content reference as ``(monster, <its stored species key>)`` — derived from its
own stored species provenance and from nothing else — and the presentation
chain's existing official-default step presents that species' mounted image
with no chain edit and no installed state. A species the mounted snapshot does
not hold falls through to exactly the runtime/silhouette chain, and no code path
can reach another species' official bytes for it.

Everything here is synthetic. The species/variant/tier catalogs come from the
shared synthetic kit (``world.tests.synthetic_data``) or from a string-named
``patch.object`` binding, the mounted catalog is a temporary root built per
test, and no shipped key, path, or catalog symbol appears — the reference's
membership authority is exercised through the kit's own vocabulary.

One structural note the tests below respect rather than assert away: the
personal art layer (``official-art-personalization``) is keyed by the runtime
*subject*, and a monster's subject is its threat tier (``portrait:monster:<tier>``,
the generic layer this change leaves untouched). Two individuals of one species
therefore share one personal record whenever their variants carry the same tier.
What this module asserts for them is what the reference layer owns: one shared
read-only reference, identical presented bytes, and a stored personal choice
that resolves only inside that individual's own reference.
"""

import hashlib
import io
import json
from contextlib import ExitStack
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import unittest
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from typeclasses.monsters import Monster
from world.art import official, official_refs
from world.art.gallery import (
    GalleryRecord,
    official_preferences_for,
    set_official_geometry,
    set_official_selection,
)
from world.art.gallery_match import official_default_for, official_selection_for
from world.art.official import current_catalog, load_catalog, reset_catalog
from world.art.official_refs import (
    OFFICIAL_KIND_MONSTER,
    PRESET_PROVENANCE_ATTRIBUTE,
    SPECIES_PROVENANCE_ATTRIBUTE,
    UNRESOLVED_REFERENCE_EVENT,
    OfficialContentReference,
    official_content_reference,
    official_content_reference_for_entity,
    registered_content_key,
)
from world.art.presenter import (
    ORIGIN_OFFICIAL,
    PAYLOAD_OFFICIAL,
    resolve_entity,
    resolve_subject,
)
from world.art.store import ArtAssetRecord
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    monster_subject_for,
    parse_subject,
)
from world.tests.synthetic_data import (
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    make_monster_species,
    synthetic_registries,
)

from tools.spec_traceability import covers_requirement


# The kit's species, its two variants, and the kit's tiers: the reference's
# membership authority and the tier vocabulary it must never borrow from.
_SYNTH_SPECIES = sorted(SYNTH_MONSTER_SPECIES)[0]
_VARIANTS_OF_SPECIES = tuple(
    row.key
    for row in sorted(SYNTH_MONSTER_VARIANTS.values(), key=lambda variant: variant.key)
    if row.species_key == _SYNTH_SPECIES
)
_SYNTH_TIER = sorted(SYNTH_MONSTER_TIERS)[0]
_SYNTH_TIERS = tuple(sorted(SYNTH_MONSTER_TIERS))

# The sibling change's second identity field: never an input to a reference.
VARIANT_ATTRIBUTE = "variant_key"

# A second REGISTERED species (the kit's species row re-keyed) and a key NO
# registry holds. The species registry is not re-validated under a kit scope,
# so the row is a membership stand-in: enough to prove resolution follows the
# stored key rather than "whatever the catalog happens to hold".
_OTHER_SPECIES = "t_synth_other_species"
_UNREGISTERED_SPECIES = "t_synth_unregistered_species"

# The catalog's load-time geometry for a 4x4 test image (pixel-square).
_OFFICIAL_RECT = {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}
_OFFICIAL_STAGE = {"scale": 1.4, "x": 0.1, "y": -0.2}


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def open_synthetic_scope(case: unittest.TestCase, *targets):
    """Enter a synthetic-catalog scope bound to one test's lifecycle.

    The kit's class decorator wraps ``test*`` methods only, so a ``setUp`` that
    builds entities against the catalogs must open the scope itself — as its
    FIRST statement, before ``super().setUp()``.
    """
    scope = synthetic_registries(
        *targets,
        extra={"monster_species": {_OTHER_SPECIES: make_monster_species(_OTHER_SPECIES)}},
    )
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope


def _unresolved_events(logged) -> list:
    """The bounded unresolved-reference events among a patched warn's calls."""
    return [
        call
        for call in logged.call_args_list
        if call.args and call.args[0] == UNRESOLVED_REFERENCE_EVENT
    ]


class _ProvenanceEntity:
    """An entity-shaped stand-in recording exactly which attribute names were read."""

    def __init__(self, **attributes):
        self.pk = 3
        self.key = ""
        self.display_name = ""
        self._values = dict(attributes)
        self.read_keys: list[str] = []

    @property
    def attributes(self):
        return SimpleNamespace(get=self._read)

    def _read(self, key, **_kwargs):
        self.read_keys.append(key)
        return self._values.get(key)


class SpeciesReferenceTests(unittest.TestCase):
    """The species arm: a stored species key in, ``(monster, <key>)`` out."""

    def setUp(self):
        open_synthetic_scope(self, "monster_species", "monster_tiers")
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    def _resolve(self, entity):
        """Resolve one entity with the resolver's diagnostic seam patched."""
        with patch.object(official_refs, "log_warn") as warned:
            reference = official_content_reference_for_entity(entity)
        return reference, _unresolved_events(warned)

    def test_a_stored_species_key_is_the_whole_reference(self):
        entity = _ProvenanceEntity(**{SPECIES_PROVENANCE_ATTRIBUTE: _SYNTH_SPECIES})
        reference, events = self._resolve(entity)
        self.assertEqual(
            reference, OfficialContentReference(OFFICIAL_KIND_MONSTER, _SYNTH_SPECIES)
        )
        self.assertEqual(reference.identity(), f"{OFFICIAL_KIND_MONSTER}/{_SYNTH_SPECIES}")
        self.assertTrue(registered_content_key(OFFICIAL_KIND_MONSTER, _SYNTH_SPECIES))
        self.assertEqual(events, [])

    def test_the_species_read_is_the_last_arm_and_falls_through_to_it(self):
        # An unresolvable authored provenance does not abort the chain: the
        # species arm still answers from the entity's own species identity.
        entity = _ProvenanceEntity(
            **{
                PRESET_PROVENANCE_ATTRIBUTE: "t_synth_absent_preset",
                SPECIES_PROVENANCE_ATTRIBUTE: _SYNTH_SPECIES,
            }
        )
        reference, events = self._resolve(entity)
        self.assertEqual(
            reference, OfficialContentReference(OFFICIAL_KIND_MONSTER, _SYNTH_SPECIES)
        )
        self.assertEqual(
            [event.kwargs["context"]["kind"] for event in events],
            ["preset"],
        )

    def test_every_variant_of_one_species_resolves_that_same_species_reference(self):
        self.assertGreaterEqual(len(_VARIANTS_OF_SPECIES), 2, _VARIANTS_OF_SPECIES)
        references = []
        for variant_key in _VARIANTS_OF_SPECIES:
            with self.subTest(variant=variant_key):
                entity = _ProvenanceEntity(
                    **{
                        SPECIES_PROVENANCE_ATTRIBUTE: _SYNTH_SPECIES,
                        VARIANT_ATTRIBUTE: variant_key,
                    }
                )
                reference, events = self._resolve(entity)
                self.assertEqual(events, [])
                # The variant key is never read, so it cannot split a species.
                self.assertNotIn(VARIANT_ATTRIBUTE, entity.read_keys)
                references.append(reference)
        self.assertEqual(
            {reference for reference in references},
            {OfficialContentReference(OFFICIAL_KIND_MONSTER, _SYNTH_SPECIES)},
        )

    def test_a_variant_key_is_never_a_species_key(self):
        variant_key = _VARIANTS_OF_SPECIES[0]
        self.assertFalse(registered_content_key(OFFICIAL_KIND_MONSTER, variant_key))
        entity = _ProvenanceEntity(**{SPECIES_PROVENANCE_ATTRIBUTE: variant_key})
        reference, events = self._resolve(entity)
        self.assertIsNone(reference)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["reason"], "unregistered_key")

    def test_a_tier_only_individual_resolves_no_reference_silently(self):
        entity = _ProvenanceEntity(threat_tier=_SYNTH_TIER)
        entity.key = _SYNTH_TIER
        entity.display_name = _SYNTH_TIER
        reference, events = self._resolve(entity)
        self.assertIsNone(reference)
        self.assertEqual(events, [])
        # The tier is not an identity input here: it is never even read.
        self.assertNotIn("threat_tier", entity.read_keys)

    def test_a_tier_value_is_never_admitted_as_a_species_key(self):
        for tier in _SYNTH_TIERS:
            with self.subTest(tier=tier):
                self.assertFalse(registered_content_key(OFFICIAL_KIND_MONSTER, tier))
                self.assertIsNone(official_content_reference(OFFICIAL_KIND_MONSTER, tier))
                entity = _ProvenanceEntity(**{SPECIES_PROVENANCE_ATTRIBUTE: tier})
                reference, events = self._resolve(entity)
                self.assertIsNone(reference)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs["context"]["kind"], OFFICIAL_KIND_MONSTER)
                self.assertEqual(events[0].kwargs["context"]["reason"], "unregistered_key")
        # The tier vocabulary is real and still owns the generic subject layer.
        self.assertEqual(
            monster_subject_for(_SYNTH_TIER).full(), f"portrait:monster:{_SYNTH_TIER}"
        )

    def test_a_display_name_or_entity_key_never_produces_a_reference(self):
        entity = _ProvenanceEntity()
        entity.key = _SYNTH_SPECIES
        entity.display_name = _SYNTH_SPECIES
        reference, events = self._resolve(entity)
        self.assertIsNone(reference)
        self.assertEqual(events, [])

    def test_a_malformed_stored_species_value_degrades_with_one_bounded_event(self):
        for value in ("", 12, "t_synth/../escape"):
            with self.subTest(value=repr(value)):
                official_refs._reported_unresolved.clear()
                entity = _ProvenanceEntity(**{SPECIES_PROVENANCE_ATTRIBUTE: value})
                with patch.object(official_refs, "log_warn") as warned:
                    first = official_content_reference_for_entity(entity)
                    second = official_content_reference_for_entity(entity)
                self.assertIsNone(first)
                self.assertIsNone(second)
                events = _unresolved_events(warned)
                # One bounded diagnostic for a presentation-repeating value.
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs["context"]["reason"], "malformed_key")


class SpeciesSubjectVocabularyTests(unittest.TestCase):
    """The art-subject layer stays tier-validated: a species key is not a subject key."""

    def setUp(self):
        open_synthetic_scope(self, "monster_species", "monster_tiers")

    @covers_requirement(
        "art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries"
    )
    def test_a_registered_species_key_is_never_a_monster_subject_key(self):
        for species_key in SYNTH_MONSTER_SPECIES:
            with self.subTest(species_key=species_key):
                forged = parse_subject(f"portrait:monster:{species_key}")
                self.assertEqual(forged.kind, ArtSubjectKind.MONSTER)
                with self.assertRaises(ArtSubjectError):
                    monster_subject_for(forged.key)
        # The tier vocabulary still resolves, so the rejection is the registry
        # validation and not a broken subject layer.
        self.assertEqual(
            monster_subject_for(_SYNTH_TIER).full(), f"portrait:monster:{_SYNTH_TIER}"
        )


class SpeciesPortraitChainTests(EvenniaTestCase):
    """The chain's existing official-default step, now reachable for monsters.

    Scope note, asserted rather than assumed: the official default is the
    presented figure whenever no runtime card image exists for the subject
    (``resolve_display`` steps 1-4 validate a card's stored image before it can
    outrank official, and every test here starts with an empty gallery), and a
    generated card image still outranks it — the chain's documented ordering.
    The personal preferences are written through the gallery API's own writers
    (``set_official_selection``/``set_official_geometry``), which are
    subject-keyed; exposing them to a client for a registry-keyed monster
    subject belongs to the gallery rail/action surface, not to this change.
    """

    def setUp(self):
        open_synthetic_scope(self, "monster_species", "monster_tiers")
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = Path(self.tempdir.name) / "store"
        self.store.mkdir()
        self.official_root = Path(self.tempdir.name).resolve() / "official"
        self.settings = override_settings(
            ART_STORE_ROOT=str(self.store),
            ART_OFFICIAL_ROOT=str(self.official_root),
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        self._actors = 0

    # -- harness ----------------------------------------------------------
    def _index(self, species_key, name="a.png", **manifest) -> str:
        """Write one mounted species directory, load it, return its identity."""
        folder = self.official_root / OFFICIAL_KIND_MONSTER / species_key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png())
        if manifest:
            (folder / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
        load_catalog()
        return f"{OFFICIAL_KIND_MONSTER}/{species_key}/{name}"

    def _monster(self, *, species=None, variant=None) -> Monster:
        self._actors += 1
        monster = create_object(Monster, key=f"t_synth_actor_{self._actors}")
        monster.threat_tier = _SYNTH_TIER
        if species is not None:
            monster.attributes.add(SPECIES_PROVENANCE_ATTRIBUTE, species)
        if variant is not None:
            monster.attributes.add(VARIANT_ATTRIBUTE, variant)
        return monster

    def _subject(self) -> ArtSubject:
        """The generic tier subject a monster presents through (unchanged layer)."""
        return ArtSubject(ArtSubjectKind.MONSTER, _SYNTH_TIER)

    def _tree(self, root: Path) -> tuple:
        """A (path, sha256) listing of one source tree: byte-identity evidence."""
        return tuple(
            sorted(
                (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                for path in root.rglob("*")
                if path.is_file()
            )
        )

    def _state(self, monster: Monster) -> tuple:
        """One monster's observable state, for a before/after pin.

        The gallery records are pinned by CONTENT, not only by count, so a
        mutation of an existing record could not hide behind an unchanged row
        count.
        """
        return (
            str(monster.pk),
            str(monster.threat_tier),
            str(monster.attributes.get(SPECIES_PROVENANCE_ATTRIBUTE)),
            tuple(
                sorted(
                    (
                        str(record.db_key),
                        repr(record.db.official_selection),
                        repr(record.db.official_geometry),
                        repr(record.db.default_image_id),
                        repr(record.db.cards),
                    )
                    for record in GalleryRecord.objects.all()
                )
            ),
            ArtAssetRecord.objects.count(),
            self._tree(self.store),
            self._tree(self.official_root),
        )

    # -- the official default presents -----------------------------------
    def test_a_catalog_backed_species_presents_its_official_image(self):
        identity = self._index(
            _SYNTH_SPECIES, face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        monster = self._monster(species=_SYNTH_SPECIES, variant=_VARIANTS_OF_SPECIES[0])
        payload = resolve_entity(monster)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["kind"], PAYLOAD_OFFICIAL)
        self.assertEqual(payload["url"], current_catalog().url_for(identity))
        self.assertEqual(
            payload["url"],
            f"/art/official/{current_catalog().fingerprint_for(identity)}/{identity}",
        )
        # The presentation rides the ordinary step and the ordinary generic
        # subject: no monster special case was installed for it.
        self.assertEqual(payload["subject_key"], self._subject().full())
        self.assertEqual(payload["face_rect"], _OFFICIAL_RECT)
        self.assertEqual(payload["stage"], _OFFICIAL_STAGE)
        self.assertIsNone(payload["status"])
        self.assertEqual(GalleryRecord.objects.count(), 0)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    def test_a_species_the_snapshot_lacks_falls_through_byte_identically(self):
        # The snapshot holds a monster directory — but not this species'.
        foreign_identity = self._index(_UNREGISTERED_SPECIES, name="b.png")
        backed = self._monster(species=_SYNTH_SPECIES)
        plain = self._monster()
        with patch.object(official_refs, "log_warn") as warned:
            backed_payload = resolve_subject(self._subject(), entity=backed)
            plain_payload = resolve_subject(self._subject(), entity=plain)
        self.assertEqual(
            json.dumps(backed_payload, sort_keys=True),
            json.dumps(plain_payload, sort_keys=True),
        )
        self.assertNotEqual(backed_payload["origin"], ORIGIN_OFFICIAL)
        self.assertIsNone(backed_payload["url"])
        # The reference itself resolved; only the snapshot lacks its content,
        # so the fall-through is silent (no diagnostic at all).
        self.assertEqual(_unresolved_events(warned), [])
        self.assertNotIn(foreign_identity, json.dumps(backed_payload, sort_keys=True))

    def test_no_other_keys_official_bytes_are_reachable_for_an_unmatched_species(self):
        owned = self._index(_SYNTH_SPECIES, face_rect=dict(_OFFICIAL_RECT))
        other = self._index(_OTHER_SPECIES, name="b.png")
        matched = self._monster(species=_SYNTH_SPECIES)
        sibling = self._monster(species=_OTHER_SPECIES)
        unmatched = self._monster(species=_UNREGISTERED_SPECIES)

        matched_payload = resolve_subject(self._subject(), entity=matched)
        sibling_payload = resolve_subject(self._subject(), entity=sibling)
        unmatched_payload = resolve_subject(self._subject(), entity=unmatched)

        # Each species presents its own bytes...
        self.assertEqual(matched_payload["url"], current_catalog().url_for(owned))
        self.assertEqual(sibling_payload["url"], current_catalog().url_for(other))
        # ...and a key no registry holds reaches none of them.
        self.assertIsNone(official_content_reference_for_entity(unmatched))
        self.assertIsNone(official_default_for(self._subject(), unmatched))
        self.assertIsNone(official_selection_for(self._subject(), unmatched))
        self.assertNotEqual(unmatched_payload["origin"], ORIGIN_OFFICIAL)
        serialized = json.dumps(unmatched_payload, sort_keys=True)
        for forbidden in (
            _SYNTH_SPECIES,
            _OTHER_SPECIES,
            owned,
            other,
            current_catalog().fingerprint_for(owned),
            current_catalog().fingerprint_for(other),
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_a_tier_named_monster_directory_is_indexed_but_unreachable(self):
        # An operator error: a content directory named after a threat tier.
        # The catalog still indexes it — membership checking at ADMISSION for
        # the monster kind is the catalog change's pending work — while the
        # reference layer never admits the tier as a species key, so nothing
        # presents those bytes.
        tier_identity = self._index(_SYNTH_TIER, face_rect=dict(_OFFICIAL_RECT))
        self.assertIsNotNone(current_catalog().content(OFFICIAL_KIND_MONSTER, _SYNTH_TIER))
        monster = self._monster()
        self.assertIsNone(official_content_reference_for_entity(monster))
        payload = resolve_subject(self._subject(), entity=monster)
        self.assertNotEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertNotIn(tier_identity, json.dumps(payload, sort_keys=True))

    # -- shared reference, personal layer beside it -----------------------
    def test_two_variants_of_one_species_share_the_image_and_keep_their_own_choices(self):
        identity = self._index(
            _SYNTH_SPECIES, face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        first = self._monster(species=_SYNTH_SPECIES, variant=_VARIANTS_OF_SPECIES[0])
        second = self._monster(species=_SYNTH_SPECIES, variant=_VARIANTS_OF_SPECIES[1])
        first_reference = official_content_reference_for_entity(first)
        second_reference = official_content_reference_for_entity(second)
        self.assertEqual(first_reference, second_reference)
        # A read-only value: two individuals get equal values, never one
        # shared mutable object.
        self.assertIsNot(first_reference, second_reference)
        with self.assertRaises(FrozenInstanceError):
            first_reference.key = _UNREGISTERED_SPECIES

        before = self._tree(self.official_root)
        first_payload = resolve_subject(self._subject(), entity=first)
        second_payload = resolve_subject(self._subject(), entity=second)
        self.assertEqual(
            json.dumps(first_payload, sort_keys=True),
            json.dumps(second_payload, sort_keys=True),
        )
        self.assertEqual(first_payload["url"], current_catalog().url_for(identity))

        # The personal layer sits beside the shared reference: this subject's
        # own geometry override governs its payload while the mounted source
        # is never written.
        override = {"x": 0.5, "y": 0.5, "w": 0.25, "h": 0.25}
        set_official_geometry(self._subject(), identity, face_rect=override)
        overridden = resolve_subject(self._subject(), entity=first)
        self.assertEqual(overridden["face_rect"], override)
        self.assertEqual(overridden["url"], first_payload["url"])
        self.assertEqual(self._tree(self.official_root), before)

    def test_a_stored_selection_outside_the_species_reference_is_ignored(self):
        self._index(_SYNTH_SPECIES, face_rect=dict(_OFFICIAL_RECT))
        foreign_identity = self._index(_OTHER_SPECIES, name="b.png")
        monster = self._monster(species=_SYNTH_SPECIES)
        set_official_selection(self._subject(), foreign_identity)
        # The personal choice is retained verbatim...
        self.assertEqual(
            official_preferences_for(self._subject()).selection, foreign_identity
        )
        # ...and never resolves outside the individual's own reference.
        self.assertIsNone(official_selection_for(self._subject(), monster))
        payload = resolve_subject(self._subject(), entity=monster)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(
            payload["url"], current_catalog().url_for(f"{OFFICIAL_KIND_MONSTER}/{_SYNTH_SPECIES}/a.png")
        )
        self.assertNotIn(foreign_identity, json.dumps(payload, sort_keys=True))

    def test_a_personal_selection_inside_the_species_reference_presents_for_a_monster(self):
        # The personal layer's positive path, through the gallery API's own
        # subject-keyed writers: a choice INSIDE the individual's reference
        # replaces the catalog default, the same way it does for a character.
        default_identity = self._index(
            _SYNTH_SPECIES, name="a.png", face_rect=dict(_OFFICIAL_RECT)
        )
        chosen_identity = self._index(
            _SYNTH_SPECIES, name="b.png", face_rect=dict(_OFFICIAL_RECT)
        )
        monster = self._monster(species=_SYNTH_SPECIES)
        set_official_selection(self._subject(), chosen_identity)
        self.assertEqual(
            official_selection_for(self._subject(), monster)["identity"], chosen_identity
        )
        payload = resolve_subject(self._subject(), entity=monster)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["url"], current_catalog().url_for(chosen_identity))
        self.assertNotEqual(payload["url"], current_catalog().url_for(default_identity))

    # -- purity -----------------------------------------------------------
    def test_resolution_reads_only_stored_identity_and_the_loaded_snapshot(self):
        self._index(
            _SYNTH_SPECIES, face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        monster = self._monster(species=_SYNTH_SPECIES)
        subject = self._subject()
        tripwires = (
            patch.object(socket, "create_connection", side_effect=AssertionError("network")),
            patch.object(socket.socket, "connect", side_effect=AssertionError("network")),
            patch("world.art.gallery.append_card", side_effect=AssertionError("card write")),
            patch("world.art.gallery.set_default", side_effect=AssertionError("default write")),
            patch(
                "world.art.queue.enqueue_gallery_job",
                side_effect=AssertionError("enqueue"),
            ),
            patch(
                "world.art.service.request_gallery_image",
                side_effect=AssertionError("enqueue"),
            ),
            # Resolution answers from the snapshot: it never re-walks or
            # re-loads the mounted tree.
            patch.object(official, "open_dir_fd", side_effect=AssertionError("re-walk")),
            patch.object(official, "load_catalog", side_effect=AssertionError("re-load")),
        )
        with ExitStack() as stack:
            for tripwire in tripwires:
                stack.enter_context(tripwire)
            before = self._state(monster)
            references = [official_content_reference_for_entity(monster) for _ in range(50)]
            defaults = [official_default_for(subject, monster) for _ in range(50)]
            payloads = [resolve_subject(subject, entity=monster) for _ in range(50)]
            after = self._state(monster)
        self.assertEqual(before, after)
        self.assertTrue(all(reference == references[0] for reference in references))
        self.assertEqual(references[0].key, _SYNTH_SPECIES)
        self.assertTrue(all(default == defaults[0] for default in defaults))
        self.assertTrue(all(payload == payloads[0] for payload in payloads))
        self.assertEqual(payloads[0]["origin"], ORIGIN_OFFICIAL)


if __name__ == "__main__":
    unittest.main()
