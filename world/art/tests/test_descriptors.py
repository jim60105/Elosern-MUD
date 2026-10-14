"""The canonical descriptor vocabulary: closed sets, stable order, pure builders.

Change ``unified-gallery-image-contract`` (task 1.1). ``world/art/descriptors``
is a pure data module: it imports nothing from Evennia and reads no game state,
so these are synthetic mechanism tests over independently expected inputs and
outcomes — no database, no settings, no fixture tree.
"""

import json
import re
import unittest

from world.art import descriptors

_FINGERPRINT = re.compile(r"[0-9a-f]{64}")


def _sample_descriptor(**changes):
    """One synthetic descriptor assembled from the production builders."""
    facts = _sample_facts()
    facts.update(changes)
    return descriptors.descriptor(**facts)


def _sample_facts():
    """The ordered facts one synthetic descriptor is built from."""
    return {
        "subject_id": "subject:1",
        "generation_subject": "portrait:character:1",
        "generation_state": descriptors.GENERATION_DONE,
        "attempts": [
            descriptors.image_attempt(
                descriptors.gallery_original_source_id("image-1"),
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.resource(
                    "gallery/character/1/image-1.webp",
                    descriptors.identity_version("gallery/character/1/image-1.webp"),
                    "/art/gallery/character/1/image-1.webp",
                    descriptors.ORIGIN_RUNTIME,
                    geometry_payload=descriptors.geometry(
                        image_size=descriptors.image_size_payload(768, 1024),
                        face_rect={"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375},
                        stage={"scale": 1.0, "x": 0.0, "y": 0.0},
                        aspect_ratio="3:4",
                    ),
                ),
            )
        ],
        "terminal_payload": descriptors.terminal(
            descriptors.TERMINAL_ALPHA_MASK,
            descriptors.gallery_alpha_source_id("woman"),
            descriptors.GALLERY_RANK_ALPHA,
            descriptors.resource(
                "defaults/woman.webp",
                descriptors.identity_version("defaults/woman.webp"),
                "/art/defaults/woman.webp",
                descriptors.ORIGIN_SILHOUETTE,
                geometry_payload=descriptors.geometry(face_rect={"x": 0.35, "y": 0.02, "w": 0.28, "h": 0.16}),
            ),
        ),
        "retention_sources": [
            descriptors.retention_source(
                descriptors.gallery_original_source_id("image-1"),
                descriptors.retention_token("portrait:character:1", "image-1"),
            )
        ],
    }


def _revision_of(facts):
    """The revision of one fact mapping, recomputed after a mutation."""
    return descriptors.revision_for(
        subject_id=facts["subject_id"],
        generation_subject=facts["generation_subject"],
        generation_state=facts["generation_state"],
        attempts=facts["attempts"],
        terminal_payload=facts["terminal_payload"],
        retention_sources=facts["retention_sources"],
    )


class VocabularyTests(unittest.TestCase):
    def test_closed_sets_are_exactly_their_members(self):
        self.assertEqual(
            descriptors.ORIGINS,
            ("runtime", "official", "bundled_official", "silhouette"),
        )
        self.assertEqual(
            descriptors.GENERATION_STATES, ("missing", "pending", "done", "failed")
        )
        self.assertEqual(
            descriptors.TERMINAL_KINDS, ("alpha_mask", "scene_image")
        )
        self.assertEqual(
            descriptors.FAULT_REASONS,
            (
                "generation_failed",
                "generated_output_missing",
                "source_unavailable",
                "source_rejected",
                "explicit_reference_missing",
                "metadata_invalid",
                "required_resource_missing",
                "configuration_invalid",
                "panel_unavailable",
                "image_load_failed",
                "image_decode_failed",
            ),
        )
        # Every reason is a bounded identifier and no constant drifted.
        for reason in descriptors.FAULT_REASONS:
            with self.subTest(reason=reason):
                self.assertRegex(reason, r"^[a-z][a-z_]*$")
                self.assertLessEqual(len(reason), 32)
        self.assertEqual(
            descriptors.REASON_GENERATED_OUTPUT_MISSING, "generated_output_missing"
        )
        self.assertEqual(descriptors.REASON_SOURCE_REJECTED, "source_rejected")

    def test_every_origin_carries_its_own_url_ceiling(self):
        self.assertEqual(set(descriptors.MEDIA_URL_LIMITS), set(descriptors.ORIGINS))
        self.assertEqual(descriptors.GALLERY_MEDIA_URL_LIMIT, 129)
        self.assertEqual(descriptors.GENERAL_MEDIA_URL_LIMIT, 256)
        for origin in (descriptors.ORIGIN_RUNTIME, descriptors.ORIGIN_SILHOUETTE):
            self.assertEqual(
                descriptors.MEDIA_URL_LIMITS[origin], descriptors.GALLERY_MEDIA_URL_LIMIT
            )
        for origin in (descriptors.ORIGIN_OFFICIAL, descriptors.ORIGIN_BUNDLED_OFFICIAL):
            self.assertEqual(
                descriptors.MEDIA_URL_LIMITS[origin], descriptors.GENERAL_MEDIA_URL_LIMIT
            )

    def test_container_bounds_are_the_declared_values(self):
        self.assertEqual(descriptors.MAX_SUBJECT_ID, 128)
        self.assertEqual(descriptors.MAX_SOURCE_ID, 256)
        self.assertEqual(descriptors.MAX_RESOURCE_ID, 256)
        self.assertEqual(descriptors.FINGERPRINT_LENGTH, 64)
        self.assertEqual(descriptors.MAX_ATTEMPTS, 16)
        self.assertEqual(descriptors.MAX_RETENTION_SOURCES, 16)
        self.assertEqual(descriptors.GALLERY_RANK_ORIGINAL, 10)
        self.assertEqual(descriptors.GALLERY_RANK_ALPHA, 100)
        # The decoded-size ceiling mirrors the shipped ART_SD_MAX_IMAGE_* pair.
        self.assertEqual(descriptors.MAX_IMAGE_DIMENSION, 4096)
        self.assertEqual(descriptors.MAX_IMAGE_PIXELS, 4096 * 4096)


class GenerationStateTests(unittest.TestCase):
    def test_recorded_status_normalizes_onto_the_canonical_vocabulary(self):
        self.assertEqual(descriptors.normalize_generation_state("missing"), "missing")
        self.assertEqual(descriptors.normalize_generation_state("pending"), "pending")
        self.assertEqual(descriptors.normalize_generation_state("in_progress"), "pending")
        self.assertEqual(descriptors.normalize_generation_state("done"), "done")
        self.assertEqual(descriptors.normalize_generation_state("failed"), "failed")

    def test_absent_and_unknown_statuses_make_no_claim(self):
        # No recorded status is an honest None, never a synthesized "missing".
        self.assertIsNone(descriptors.normalize_generation_state(None))
        self.assertIsNone(descriptors.normalize_generation_state(""))
        self.assertIsNone(descriptors.normalize_generation_state("queued"))

    def test_normalization_covers_exactly_the_canonical_states(self):
        self.assertEqual(
            set(descriptors.RECORDED_STATE_NORMALIZATION.values()),
            set(descriptors.GENERATION_STATES),
        )


class BuilderShapeTests(unittest.TestCase):
    def test_geometry_always_carries_exactly_its_four_keys(self):
        self.assertEqual(
            set(descriptors.geometry()),
            {"image_size", "face_rect", "stage", "aspect_ratio"},
        )
        self.assertEqual(set(descriptors.geometry()), set(descriptors.geometry(
            image_size=descriptors.image_size_payload(1, 2),
            face_rect={"x": 0, "y": 0, "w": 1, "h": 1},
            stage={"scale": 1, "x": 0, "y": 0},
            aspect_ratio="3:4",
        )))
        # Every inapplicable fact is a factual null rather than an absent key.
        self.assertTrue(all(value is None for value in descriptors.geometry().values()))

    def test_resource_and_attempt_shapes_are_exact(self):
        resource = descriptors.resource("id", "v" * 64, "/art/x.png", "runtime")
        self.assertEqual(
            set(resource), {"resource_id", "version", "url", "origin", "geometry"}
        )
        self.assertIsNone(resource["geometry"])
        image = descriptors.image_attempt("source", 10, resource)
        self.assertEqual(set(image), {"type", "source_id", "rank", "resource"})
        self.assertEqual(image["type"], "image")
        fault = descriptors.fault_attempt("source", 10, "source_rejected")
        self.assertEqual(set(fault), {"type", "source_id", "rank", "reason"})
        # A fault names its source and reason and NEVER a URL.
        self.assertEqual(fault["type"], "fault")
        self.assertNotIn("resource", fault)
        self.assertNotIn("url", json.dumps(fault))
        terminal = descriptors.terminal("alpha_mask", "source", 100, resource)
        self.assertEqual(set(terminal), {"kind", "source_id", "rank", "resource"})
        retention = descriptors.retention_source("source", "t" * 64)
        self.assertEqual(set(retention), {"source_id", "token"})

    def test_source_identity_builders_are_canonical(self):
        self.assertEqual(
            descriptors.gallery_original_source_id("abc"), "gallery.original:abc"
        )
        self.assertEqual(
            descriptors.gallery_official_source_id("preset/k/a.png"),
            "gallery.official:preset/k/a.png",
        )
        self.assertEqual(descriptors.gallery_alpha_source_id("woman"), "gallery.alpha:woman")


class RankOrderTests(unittest.TestCase):
    def test_priority_is_the_declared_rank_not_the_array_index(self):
        # The same facts declared in the opposite array order keep the same
        # ranks: array position never decides precedence.
        original = descriptors.image_attempt("original", 10, {"resource_id": "a"})
        alpha = descriptors.image_attempt("alpha", 100, {"resource_id": "b"})
        forward = [original, alpha]
        reverse = [alpha, original]
        self.assertEqual([entry["rank"] for entry in forward], [10, 100])
        self.assertEqual([entry["rank"] for entry in reverse], [100, 10])
        self.assertEqual(
            {entry["source_id"]: entry["rank"] for entry in forward},
            {entry["source_id"]: entry["rank"] for entry in reverse},
        )

    def test_a_fault_shares_its_candidates_source_and_rank(self):
        source = descriptors.gallery_official_source_id("preset/k/a.png")
        candidate = descriptors.image_attempt(source, descriptors.GALLERY_RANK_ORIGINAL, {})
        fault = descriptors.fault_attempt(
            source, descriptors.GALLERY_RANK_ORIGINAL, descriptors.REASON_METADATA_INVALID
        )
        self.assertEqual(fault["source_id"], candidate["source_id"])
        self.assertEqual(fault["rank"], candidate["rank"])
        # Adding the fault changes neither the candidate's source nor its rank.
        self.assertEqual(candidate["rank"], descriptors.GALLERY_RANK_ORIGINAL)


class ReadOnlyTests(unittest.TestCase):
    def test_builders_return_fresh_structures_and_never_mutate_inputs(self):
        size = descriptors.image_size_payload(768, 1024)
        rect = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375}
        stage = {"scale": 1.0, "x": 0.0, "y": 0.0}
        before = json.dumps([size, rect, stage], sort_keys=True)
        first = descriptors.geometry(image_size=size, face_rect=rect, stage=stage)
        second = descriptors.geometry(image_size=size, face_rect=rect, stage=stage)
        self.assertEqual(json.dumps([size, rect, stage], sort_keys=True), before)
        self.assertIsNot(first, second)
        # The nested facts are handed over verbatim (a reader passes the dicts
        # it just validated), so the builder never mutates or aliases state it
        # does not own.
        self.assertIs(first["face_rect"], rect)

    def test_repeated_construction_is_byte_identical(self):
        self.assertEqual(_sample_descriptor(), _sample_descriptor())
        self.assertEqual(
            descriptors.revision_for(
                subject_id="s", generation_subject="g", generation_state="done",
                attempts=[], terminal_payload=None, retention_sources=[],
            ),
            descriptors.revision_for(
                subject_id="s", generation_subject="g", generation_state="done",
                attempts=[], terminal_payload=None, retention_sources=[],
            ),
        )

    def test_the_module_reads_no_game_state(self):
        # Pure vocabulary: no Evennia, no Django, no file or network access.
        source = __import__("pathlib").Path(descriptors.__file__).read_text(encoding="utf-8")
        for forbidden in ("evennia", "django", "settings", "open(", "requests"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class DigestTests(unittest.TestCase):
    def test_every_digest_is_a_lowercase_sha256(self):
        for digest in (
            descriptors.identity_version("gallery/character/1/a.webp"),
            descriptors.retention_token("subject", "image"),
            descriptors.revision_for(
                subject_id="s", generation_subject="g", generation_state="done",
                attempts=[], terminal_payload=None, retention_sources=[],
            ),
        ):
            with self.subTest(digest=digest):
                self.assertRegex(digest, _FINGERPRINT)
                self.assertEqual(len(digest), descriptors.FINGERPRINT_LENGTH)

    def test_a_version_is_the_stable_digest_of_its_identity(self):
        first = descriptors.identity_version("gallery/character/1/a.webp")
        self.assertEqual(first, descriptors.identity_version("gallery/character/1/a.webp"))
        self.assertNotEqual(first, descriptors.identity_version("gallery/character/1/b.webp"))

    def test_the_revision_covers_ordered_facts_geometry_and_generation(self):
        base = _revision_of(_sample_facts())
        self.assertEqual(base, _revision_of(_sample_facts()))

        cases = {
            "source fact": lambda facts: facts["attempts"][0].update(
                source_id="gallery.original:other"
            ),
            "source version": lambda facts: facts["attempts"][0]["resource"].update(
                version="f" * 64
            ),
            "geometry": lambda facts: facts["attempts"][0]["resource"]["geometry"].update(
                stage={"scale": 0.6, "x": 0.1, "y": -0.1}
            ),
            "generation state": lambda facts: facts.update(
                generation_state=descriptors.GENERATION_PENDING
            ),
            "access applicability": lambda facts: facts["retention_sources"][0].update(
                token="e" * 64
            ),
            "an added fault": lambda facts: facts["attempts"].append(
                descriptors.fault_attempt("gallery.original:2", 20, "source_rejected")
            ),
            "the terminal": lambda facts: facts.update(terminal_payload=None),
        }
        for name, mutate in cases.items():
            with self.subTest(fact=name):
                facts = _sample_facts()
                mutate(facts)
                self.assertNotEqual(_revision_of(facts), base)

    def test_the_revision_never_covers_itself(self):
        descriptor = _sample_descriptor()
        self.assertEqual(
            descriptor["revision"],
            descriptors.revision_for(
                subject_id=descriptor["subject_id"],
                generation_subject=descriptor["generation_subject"],
                generation_state=descriptor["generation_state"],
                attempts=descriptor["attempts"],
                terminal_payload=descriptor["terminal"],
                retention_sources=descriptor["retention_sources"],
            ),
        )

    def test_retention_tokens_distinguish_authorization_from_geometry(self):
        # The token covers subject/generation/access applicability; a geometry
        # or regeneration-state change must not revoke a still-valid output.
        token = descriptors.retention_token("subject", "generation", "image")
        self.assertEqual(token, descriptors.retention_token("subject", "generation", "image"))
        self.assertNotEqual(token, descriptors.retention_token("subject", "other", "image"))
        self.assertNotEqual(token, descriptors.retention_token("subject", "generation", "image2"))

    def test_a_surrogate_fact_still_digests_deterministically(self):
        # The active validators reject a lone surrogate at the wire; the digest
        # itself must stay total and stable rather than raise.
        surrogate = "\ud800"
        first = descriptors.revision_for(
            subject_id=surrogate, generation_subject=None, generation_state=None,
            attempts=[], terminal_payload=None, retention_sources=[],
        )
        self.assertRegex(first, _FINGERPRINT)
        self.assertEqual(
            first,
            descriptors.revision_for(
                subject_id=surrogate, generation_subject=None, generation_state=None,
                attempts=[], terminal_payload=None, retention_sources=[],
            ),
        )
        self.assertRegex(descriptors.identity_version(surrogate), _FINGERPRINT)

    def test_maximum_length_facts_still_digest(self):
        long_identity = "x" * descriptors.MAX_RESOURCE_ID
        self.assertRegex(descriptors.identity_version(long_identity), _FINGERPRINT)
        long_subject = "s" * descriptors.MAX_SUBJECT_ID
        self.assertRegex(
            descriptors.revision_for(
                subject_id=long_subject, generation_subject=long_subject,
                generation_state=descriptors.GENERATION_MISSING,
                attempts=[], terminal_payload=None, retention_sources=[],
            ),
            _FINGERPRINT,
        )


class DescriptorShapeTests(unittest.TestCase):
    def test_a_descriptor_carries_exactly_its_seven_keys(self):
        descriptor = _sample_descriptor()
        self.assertEqual(
            set(descriptor),
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
        self.assertIsInstance(descriptor["attempts"], list)
        self.assertIsInstance(descriptor["retention_sources"], list)

    def test_a_descriptor_without_any_candidate_is_still_complete(self):
        descriptor = _sample_descriptor(
            attempts=[], terminal_payload=None, retention_sources=[],
            generation_state=descriptors.GENERATION_PENDING,
        )
        self.assertEqual(descriptor["attempts"], [])
        self.assertIsNone(descriptor["terminal"])
        self.assertEqual(descriptor["retention_sources"], [])
        self.assertEqual(descriptor["generation_state"], "pending")
        self.assertRegex(descriptor["revision"], _FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
