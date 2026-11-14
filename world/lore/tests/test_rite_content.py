"""Synthetic tests for the landmark rite content model and its strict loader.

Covers:
- The valid synthetic document, the snapshot's read methods and its immutability.
- Every stable rejection code with its field path: document shape, unknown fields,
  archetype and option counts, key format, text bounds, duplicate option keys,
  duration and level bounds, scene identity and model bounds, narration presence,
  scene-identifier uniqueness and the district assignment cross-checks.
- Several unrelated faults reported by one rejection, sorted by field path and code.
- ``watch: null`` against a missing ``watch`` key, and narration-first scenes.
- The snapshot holder: read before install, install, scoped restore and type check.
- ``load_rites`` file reading: size limit, non-UTF-8 and an unreadable path.
- ``load_published``: a valid document installs, a rejected or missing document
  installs nothing and leaves the previous snapshot current.

Every document here is synthetic placeholder data, never shipped prose or rows.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import yaml

from tools.spec_traceability import covers_requirement
from world.lore.rites import (
    CONTENT_PATH,
    RitesNotLoaded,
    current,
    install,
    installed,
    load_published,
    uninstall,
)
from world.lore.rites.loader import (
    MAX_RITES_FILE_BYTES,
    RiteContentError,
    load_rites,
    parse_rites_document,
)
from world.lore.rites.shape import RiteSnapshot, art_subject_key
from world.lore.scenes import Narration, Scene, Speech

DISTRICT_KEYS = frozenset({"d1", "d2"})


def _narration(text: str = "旁白一行。") -> dict[str, str]:
    return {"kind": "narration", "text": text}


def _actor_line(text: str = "「一。」") -> dict[str, str]:
    return {"kind": "speech", "speaker": "actor", "text": text}


def _host_line(text: str = "「二。」") -> dict[str, str]:
    return {"kind": "speech", "speaker": "host", "text": text}


def _scene(scene_id: str, lines: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "revision": "r1",
        "lines": [_narration(), _actor_line(), _host_line()] if lines is None else lines,
    }


def _option(key: str, *, archetype_key: str = "alpha", watch: bool = True) -> dict[str, object]:
    return {
        "key": key,
        "label_zh": "選項一",
        "seconds": 180,
        "shame": 1,
        "exposure": 0,
        "self": _scene(f"rite.{archetype_key}.{key}.self"),
        "watch": _scene(f"rite.{archetype_key}.{key}.watch") if watch else None,
    }


def _archetype(
    key: str = "alpha", *, option_keys: tuple[str, ...] = ("solo", "shared")
) -> dict[str, object]:
    scene_prefix = key.lower()
    return {
        "guardian_name_zh": "守護者",
        "guardian_form_zh": "一道只在有人靠近時出聲的水。",
        "options": [
            _option(option_key, archetype_key=scene_prefix, watch=option_key != "solo")
            for option_key in option_keys
        ],
    }


def _document() -> dict[str, object]:
    return {
        "version": 1,
        "kind": "landmark_rites",
        "id": "landmark_rites",
        "archetypes": {"alpha": _archetype()},
        "districts": {"d1": "alpha", "d2": "alpha"},
    }


def _text(document: object) -> str:
    return yaml.safe_dump(document, allow_unicode=True)


def _load(document: object) -> RiteSnapshot:
    return parse_rites_document(_text(document), district_keys=DISTRICT_KEYS)


def _error(document: object) -> RiteContentError:
    try:
        _load(document)
    except RiteContentError as error:
        return error
    raise AssertionError("the document was accepted")


def _pairs(error: RiteContentError) -> list[tuple[str, str]]:
    return [(item.field_path, item.code) for item in error.diagnostics]


class ValidDocumentTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot",
        "landmark-rite-content::a-rite-scene-needs-narration-and-may-omit-the-watch-perspective",
    )
    def test_the_snapshot_exposes_the_authored_content(self):
        snapshot = _load(_document())

        archetype = snapshot.archetypes["alpha"]
        self.assertEqual(archetype.key, "alpha")
        self.assertEqual(archetype.guardian_name_zh, "守護者")
        self.assertEqual(archetype.guardian_form_zh, "一道只在有人靠近時出聲的水。")
        self.assertEqual([option.key for option in archetype.options], ["solo", "shared"])

        solo, shared = archetype.options
        self.assertEqual(solo.label_zh, "選項一")
        self.assertEqual(solo.seconds, 180)
        self.assertEqual(solo.shame, 1)
        self.assertEqual(solo.exposure, 0)
        self.assertIsNone(solo.watch_scene)
        self.assertIsNotNone(shared.watch_scene)

        expected_self = Scene(
            scene_id="rite.alpha.solo.self",
            revision="r1",
            lines=(
                Narration(text="旁白一行。"),
                Speech(speaker="actor", text="「一。」"),
                Speech(speaker="host", text="「二。」"),
            ),
        )
        self.assertEqual(solo.self_scene, expected_self)
        self.assertIsInstance(solo.self_scene.lines[0], Narration)

        self.assertIs(archetype.option("shared"), shared)
        self.assertIsNone(archetype.option("missing"))
        self.assertIs(snapshot.archetype_for("d1"), archetype)
        self.assertIsNone(snapshot.archetype_for("missing"))
        self.assertEqual(dict(snapshot.districts), {"d1": "alpha", "d2": "alpha"})
        self.assertEqual(art_subject_key("alpha"), "rite_alpha")

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_the_snapshot_is_immutable(self):
        snapshot = _load(_document())
        archetype = snapshot.archetypes["alpha"]

        with self.assertRaises(TypeError):
            snapshot.archetypes["beta"] = archetype
        with self.assertRaises(TypeError):
            snapshot.districts["d3"] = "alpha"
        with self.assertRaises(FrozenInstanceError):
            archetype.options = ()

        directly_built = RiteSnapshot(archetypes={}, districts={})
        with self.assertRaises(TypeError):
            directly_built.districts["d1"] = "alpha"


class DocumentShapeTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_unknown_top_level_field(self):
        document = _document()
        document["zeta"] = 1
        self.assertEqual(_pairs(_error(document)), [("zeta", "unknown_field")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_missing_top_level_field(self):
        document = _document()
        del document["id"]
        self.assertEqual(_pairs(_error(document)), [("id", "document_shape")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_wrong_version_type(self):
        for version in (2, "1", True, None):
            with self.subTest(version=version):
                document = _document()
                document["version"] = version
                self.assertEqual(_pairs(_error(document)), [("version", "document_shape")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_non_mapping_documents(self):
        for text in ("- one\n- two\n", "just a scalar\n", ""):
            with self.subTest(text=text):
                with self.assertRaises(RiteContentError) as caught:
                    parse_rites_document(text, district_keys=DISTRICT_KEYS)
                self.assertEqual(_pairs(caught.exception), [("", "document_shape")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_yaml_layer_faults_report_one_document_shape(self):
        texts = {
            "duplicate mapping key": "version: 1\nversion: 1\n",
            "anchor and alias": (
                "version: &version 1\n"
                "kind: landmark_rites\n"
                "id: landmark_rites\n"
                "archetypes: {}\n"
                "districts: {}\n"
                "extra: *version\n"
            ),
        }
        for label, text in texts.items():
            with self.subTest(label):
                with self.assertRaises(RiteContentError) as caught:
                    parse_rites_document(text, district_keys=DISTRICT_KEYS)
                self.assertEqual(_pairs(caught.exception), [("", "document_shape")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_wrong_container_types(self):
        cases = {
            "archetypes": ("archetypes", "document_shape"),
            "districts": ("districts", "document_shape"),
        }
        for label, (path, code) in cases.items():
            with self.subTest(label):
                document = _document()
                document[label] = []
                self.assertEqual(_pairs(_error(document)), [(path, code)])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_an_archetype_entry_that_is_not_a_mapping(self):
        document = _document()
        document["archetypes"]["alpha"] = 5
        self.assertEqual(_pairs(_error(document)), [("archetypes.alpha", "document_shape")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_options_that_are_not_a_sequence(self):
        document = _document()
        document["archetypes"]["alpha"]["options"] = {"solo": _option("solo")}
        self.assertEqual(
            _pairs(_error(document)), [("archetypes.alpha.options", "document_shape")]
        )


class CountTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_too_few_and_too_many_archetypes(self):
        empty = _document()
        empty["archetypes"] = {}
        self.assertEqual(_pairs(_error(empty)), [("archetypes", "archetype_count")])

        crowded = _document()
        crowded["archetypes"] = {
            f"a{index:02d}": _archetype(f"a{index:02d}", option_keys=("one", "two"))
            for index in range(17)
        }
        crowded["districts"] = {"d1": "a00", "d2": "a01"}
        pairs = _pairs(_error(crowded))
        self.assertEqual(pairs[0], ("archetypes", "archetype_count"))
        self.assertEqual(len(pairs), 16)
        self.assertIn(("archetypes.a16", "archetype_unused"), pairs)

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_too_few_and_too_many_options(self):
        for option_keys, count in ((("solo",), 1), (("one", "two", "three", "four"), 4)):
            with self.subTest(count=count):
                document = _document()
                document["archetypes"]["alpha"] = _archetype(option_keys=option_keys)
                self.assertEqual(
                    _pairs(_error(document)), [("archetypes.alpha.options", "option_count")]
                )


class KeyAndTextTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_archetype_key_format(self):
        document = _document()
        document["archetypes"] = {"Alpha": _archetype("Alpha")}
        document["districts"] = {"d1": "Alpha", "d2": "Alpha"}
        self.assertEqual(_pairs(_error(document)), [("archetypes.Alpha", "key_format")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_option_key_format(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["key"] = "Solo"
        self.assertEqual(
            _pairs(_error(document)), [("archetypes.alpha.options[0].key", "key_format")]
        )

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_text_bounds(self):
        cases = {
            "guardian_name_zh too long": ("guardian_name_zh", "字" * 33),
            "guardian_name_zh not text": ("guardian_name_zh", 5),
            "guardian_form_zh too long": ("guardian_form_zh", "字" * 201),
            "label_zh too long": ("label_zh", "字" * 33),
        }
        for label, (field, value) in cases.items():
            with self.subTest(label):
                document = _document()
                if field == "label_zh":
                    document["archetypes"]["alpha"]["options"][0][field] = value
                    path = f"archetypes.alpha.options[0].{field}"
                else:
                    document["archetypes"]["alpha"][field] = value
                    path = f"archetypes.alpha.{field}"
                self.assertEqual(_pairs(_error(document)), [(path, "text_bound")])


class OptionBoundTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_duplicate_option_key(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][1]["key"] = "solo"
        self.assertEqual(
            _pairs(_error(document)), [("archetypes.alpha.options[1].key", "duplicate_option")]
        )

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_duplicate_option_key_survives_an_unrelated_option_fault(self):
        document = _document()
        options = document["archetypes"]["alpha"]["options"]
        options[0]["seconds"] = 119
        options[1]["key"] = "solo"
        self.assertEqual(
            _pairs(_error(document)),
            [
                ("archetypes.alpha.options[0].seconds", "seconds_bound"),
                ("archetypes.alpha.options[1].key", "duplicate_option"),
            ],
        )

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_seconds_bound(self):
        for seconds in (119, 901, "180", True):
            with self.subTest(seconds=seconds):
                document = _document()
                document["archetypes"]["alpha"]["options"][0]["seconds"] = seconds
                self.assertEqual(
                    _pairs(_error(document)),
                    [("archetypes.alpha.options[0].seconds", "seconds_bound")],
                )

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_level_bounds(self):
        for field, value in (("shame", 3), ("shame", -1), ("exposure", 3), ("exposure", -1)):
            with self.subTest(field=field, value=value):
                document = _document()
                document["archetypes"]["alpha"]["options"][0][field] = value
                self.assertEqual(
                    _pairs(_error(document)),
                    [(f"archetypes.alpha.options[0].{field}", "level_bound")],
                )


class SceneTests(unittest.TestCase):
    def test_scene_model_bounds(self):
        crowded = _document()
        crowded["archetypes"]["alpha"]["options"][0]["self"]["lines"] = [_narration()] + [
            _actor_line(f"「{index}。」") for index in range(32)
        ]
        self.assertEqual(
            _pairs(_error(crowded)), [("archetypes.alpha.options[0].self", "scene_invalid")]
        )

        overlong = _document()
        overlong["archetypes"]["alpha"]["options"][0]["self"]["lines"] = [_narration("字" * 2001)]
        self.assertEqual(
            _pairs(_error(overlong)),
            [("archetypes.alpha.options[0].self.lines[0]", "scene_invalid")],
        )

    def test_scene_identity_bounds(self):
        cases = {
            "scene_id pattern": ("scene_id", "Rite.Bad", "archetypes.alpha.options[0].self.scene_id"),
            "scene_id type": ("scene_id", 5, "archetypes.alpha.options[0].self.scene_id"),
            "revision pattern": ("revision", "r 1", "archetypes.alpha.options[0].self.revision"),
        }
        for label, (field, value, path) in cases.items():
            with self.subTest(label):
                document = _document()
                document["archetypes"]["alpha"]["options"][0]["self"][field] = value
                self.assertEqual(_pairs(_error(document)), [(path, "scene_invalid")])

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_scene_identifier_is_unique_across_the_document(self):
        document = _document()
        options = document["archetypes"]["alpha"]["options"]
        options[1]["self"]["scene_id"] = options[0]["self"]["scene_id"]
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[1].self.scene_id", "duplicate_scene_id")],
        )

    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_absent_scene_identifier_is_not_a_duplicate(self):
        document = _document()
        options = document["archetypes"]["alpha"]["options"]
        del options[0]["self"]["scene_id"]
        del options[1]["self"]["scene_id"]
        self.assertEqual(
            _pairs(_error(document)),
            [
                ("archetypes.alpha.options[0].self.scene_id", "document_shape"),
                ("archetypes.alpha.options[1].self.scene_id", "document_shape"),
            ],
        )

    @covers_requirement(
        "landmark-rite-content::a-rite-scene-needs-narration-and-may-omit-the-watch-perspective"
    )
    def test_a_scene_needs_narration(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"]["lines"] = [
            _actor_line(),
            _host_line(),
        ]
        self.assertEqual(
            _pairs(_error(document)), [("archetypes.alpha.options[0].self", "scene_no_narration")]
        )

        empty = _document()
        empty["archetypes"]["alpha"]["options"][0]["self"]["lines"] = []
        self.assertEqual(
            _pairs(_error(empty)), [("archetypes.alpha.options[0].self", "scene_no_narration")]
        )

    @covers_requirement(
        "landmark-rite-content::a-rite-scene-needs-narration-and-may-omit-the-watch-perspective"
    )
    def test_narration_first_is_accepted(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"]["lines"] = [
            _narration(),
            _host_line(),
        ]
        snapshot = _load(document)
        self.assertIsInstance(snapshot.archetypes["alpha"].options[0].self_scene.lines[0], Narration)

    def test_a_narration_line_carries_no_speaker(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"]["lines"][0]["speaker"] = "actor"
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[0].self.lines[0].speaker", "unknown_field")],
        )

    def test_a_speech_line_carries_a_speaker(self):
        document = _document()
        del document["archetypes"]["alpha"]["options"][0]["self"]["lines"][1]["speaker"]
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[0].self.lines[1].speaker", "document_shape")],
        )

    def test_line_rejections(self):
        cases = {
            "unknown kind": (
                "kind",
                "aside",
                "archetypes.alpha.options[0].self.lines[0].kind",
                "scene_invalid",
            ),
            "unknown speaker": (
                "speaker",
                "guardian",
                "archetypes.alpha.options[0].self.lines[1].speaker",
                "scene_invalid",
            ),
            "extra line field": (
                "extra",
                1,
                "archetypes.alpha.options[0].self.lines[0].extra",
                "unknown_field",
            ),
        }
        for label, (field, value, path, code) in cases.items():
            with self.subTest(label):
                document = _document()
                index = 1 if field == "speaker" else 0
                line = document["archetypes"]["alpha"]["options"][0]["self"]["lines"][index]
                line[field] = value
                self.assertEqual(_pairs(_error(document)), [(path, code)])

    def test_a_scene_must_be_a_mapping(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"] = 5
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[0].self", "document_shape")],
        )

    def test_scene_lines_must_be_a_sequence(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"]["lines"] = "旁白"
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[0].self.lines", "document_shape")],
        )

    def test_a_scene_line_must_be_a_mapping(self):
        document = _document()
        document["archetypes"]["alpha"]["options"][0]["self"]["lines"] = ["旁白"]
        self.assertEqual(
            _pairs(_error(document)),
            [("archetypes.alpha.options[0].self.lines[0]", "document_shape")],
        )

    @covers_requirement(
        "landmark-rite-content::a-rite-scene-needs-narration-and-may-omit-the-watch-perspective"
    )
    def test_missing_watch_key_is_a_scene_fault(self):
        document = _document()
        del document["archetypes"]["alpha"]["options"][0]["watch"]
        self.assertEqual(
            _pairs(_error(document)), [("archetypes.alpha.options[0].watch", "scene_invalid")]
        )


class AssignmentTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::every-district-is-assigned-exactly-one-archetype"
    )
    def test_unknown_district(self):
        document = _document()
        document["districts"]["zz"] = "alpha"
        self.assertEqual(_pairs(_error(document)), [("districts.zz", "district_unknown")])

    @covers_requirement(
        "landmark-rite-content::every-district-is-assigned-exactly-one-archetype"
    )
    def test_unassigned_district(self):
        document = _document()
        del document["districts"]["d2"]
        self.assertEqual(_pairs(_error(document)), [("districts.d2", "district_unassigned")])

    @covers_requirement(
        "landmark-rite-content::every-district-is-assigned-exactly-one-archetype"
    )
    def test_unknown_archetype(self):
        document = _document()
        document["districts"]["d2"] = "ghost"
        self.assertEqual(_pairs(_error(document)), [("districts.d2", "archetype_unknown")])

    @covers_requirement(
        "landmark-rite-content::every-district-is-assigned-exactly-one-archetype"
    )
    def test_unused_archetype(self):
        document = _document()
        document["archetypes"]["beta"] = _archetype("beta", option_keys=("one", "two"))
        self.assertEqual(_pairs(_error(document)), [("archetypes.beta", "archetype_unused")])

    @covers_requirement(
        "landmark-rite-content::every-district-is-assigned-exactly-one-archetype"
    )
    def test_assignment_value_must_be_an_archetype_key(self):
        document = _document()
        document["districts"]["d1"] = 5
        self.assertEqual(_pairs(_error(document)), [("districts.d1", "document_shape")])


class SeveralFaultsTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-content::the-rite-document-loads-into-one-validated-immutable-snapshot"
    )
    def test_three_unrelated_faults_are_reported_together(self):
        document = _document()
        document["zeta"] = 1
        document["archetypes"]["alpha"]["options"][0]["seconds"] = 119
        document["districts"]["zz"] = "alpha"

        error = _error(document)

        self.assertEqual(
            _pairs(error),
            [
                ("archetypes.alpha.options[0].seconds", "seconds_bound"),
                ("districts.zz", "district_unknown"),
                ("zeta", "unknown_field"),
            ],
        )
        self.assertIn("seconds", str(error))


class SnapshotHolderTests(unittest.TestCase):
    def setUp(self):
        uninstall()
        self.addCleanup(uninstall)

    @covers_requirement(
        "landmark-rite-content::rite-content-is-read-only-after-it-is-installed"
    )
    def test_reading_before_install_raises(self):
        with self.assertRaises(RitesNotLoaded):
            current()

    def test_install_binds_the_snapshot(self):
        snapshot = RiteSnapshot(archetypes={}, districts={})
        self.assertIs(install(snapshot), snapshot)
        self.assertIs(current(), snapshot)

    def test_install_rejects_any_other_type(self):
        with self.assertRaises(TypeError):
            install({"archetypes": {}, "districts": {}})
        with self.assertRaises(RitesNotLoaded):
            current()

    @covers_requirement(
        "landmark-rite-content::rite-content-is-read-only-after-it-is-installed"
    )
    def test_scoped_install_restores_the_previous_value(self):
        first = RiteSnapshot(archetypes={}, districts={})
        second = RiteSnapshot(archetypes={}, districts={"d1": "alpha"})

        with installed(first):
            self.assertIs(current(), first)
            with installed(second):
                self.assertIs(current(), second)
            self.assertIs(current(), first)

        with self.assertRaises(RitesNotLoaded):
            current()

    def test_content_path_names_the_shipped_document(self):
        self.assertEqual(CONTENT_PATH.name, "landmark_rites.yaml")
        self.assertEqual(CONTENT_PATH.parent.name, "content")


class LoadRitesTests(unittest.TestCase):
    def test_a_valid_file_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "landmark_rites.yaml"
            path.write_text(_text(_document()), encoding="utf-8")
            snapshot = load_rites(path, district_keys=DISTRICT_KEYS)

        self.assertEqual(dict(snapshot.districts), {"d1": "alpha", "d2": "alpha"})

    def test_an_oversize_file_is_rejected_by_size(self):
        self.assertEqual(MAX_RITES_FILE_BYTES, 1_048_576)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "landmark_rites.yaml"
            path.write_bytes(b"#" * (1_048_576 + 1))
            with self.assertRaises(RiteContentError) as caught:
                load_rites(path, district_keys=DISTRICT_KEYS)

        self.assertEqual(_pairs(caught.exception), [("", "document_shape")])

    def test_a_non_utf8_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "landmark_rites.yaml"
            path.write_bytes(b"\xff\xfeversion: 1\n")
            with self.assertRaises(RiteContentError) as caught:
                load_rites(path, district_keys=DISTRICT_KEYS)

        self.assertEqual(_pairs(caught.exception), [("", "document_shape")])

    def test_an_unreadable_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.yaml"
            with self.assertRaises(RiteContentError) as caught:
                load_rites(path, district_keys=DISTRICT_KEYS)

        self.assertEqual(_pairs(caught.exception), [("", "document_shape")])


class LoadPublishedTests(unittest.TestCase):
    """``load_published`` adopts the document and installs only on success."""

    def setUp(self):
        uninstall()
        self.addCleanup(uninstall)

    def _write(self, directory: str, document: object) -> Path:
        path = Path(directory) / "landmark_rites.yaml"
        path.write_text(_text(document), encoding="utf-8")
        return path

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_a_valid_document_is_installed_and_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _document())
            snapshot = load_published(path, district_keys=DISTRICT_KEYS)

        self.assertEqual(dict(snapshot.districts), {"d1": "alpha", "d2": "alpha"})
        self.assertIs(current(), snapshot)

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_the_published_district_world_supplies_the_default_keys(self):
        document = SimpleNamespace(districts={"d1": "alpha", "d2": "alpha"})

        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _document())
            with patch("world.lore.map_districts.current", return_value=document):
                snapshot = load_published(path)

        self.assertEqual(set(snapshot.districts), {"d1", "d2"})
        self.assertIs(current(), snapshot)

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_an_unpublished_district_world_raises_before_anything_installs(self):
        from world.lore.map_districts import DistrictNotLoaded

        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, _document())
            with patch(
                "world.lore.map_districts.current",
                side_effect=DistrictNotLoaded("no districts"),
            ):
                with self.assertRaises(DistrictNotLoaded):
                    load_published(path)

        with self.assertRaises(RitesNotLoaded):
            current()

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_a_rejected_document_leaves_the_previous_snapshot_current(self):
        previous = RiteSnapshot(archetypes={}, districts={})
        install(previous)
        document = _document()
        document["districts"] = {"d1": "alpha"}

        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, document)
            with self.assertRaises(RiteContentError):
                load_published(path, district_keys=DISTRICT_KEYS)

        self.assertIs(current(), previous)

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_a_missing_document_raises_and_leaves_the_previous_snapshot_current(self):
        previous = RiteSnapshot(archetypes={}, districts={})
        install(previous)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.yaml"
            with self.assertRaises(RiteContentError):
                load_published(path, district_keys=DISTRICT_KEYS)

        self.assertIs(current(), previous)

    @covers_requirement(
        "landmark-rite-content::the-shipped-rite-document-is-adopted-against-the-published-districts"
    )
    def test_a_missing_document_installs_nothing_without_a_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.yaml"
            with self.assertRaises(RiteContentError):
                load_published(path, district_keys=DISTRICT_KEYS)

        with self.assertRaises(RitesNotLoaded):
            current()


if __name__ == "__main__":
    unittest.main()