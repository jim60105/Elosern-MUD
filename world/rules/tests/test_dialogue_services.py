"""Explicit dialogue-service associations: parsing, policy, and atomic rejection.

A dialogue source advertises a service only through an explicit
``{key, topic_id, label}`` row. The mechanical parser rejects malformed,
duplicate, dangling and oversized rows; the policy rejects any association that
is not this same source's supported deterministic entry (the native guild
report topic, or a generated topic the package bound an
``offer_commission`` effect to). The static loader rejects the whole candidate
atomically.
"""

import tempfile
import unittest
from pathlib import Path

from evennia.utils.test_resources import EvenniaTest

from world.lore.dialogue import loader
from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    encode_parts,
    parse_dialogue,
)
from world.lore.dialogue.services import (
    DialogueServiceError,
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    native_supported_topic_ids,
    parse_service_rows,
    required_capability_types,
    validate_service_associations,
)
from world.lore.dialogue.shape import MAX_SERVICE_ASSOCIATIONS

GUILD_TOPIC_ID = "guild_staff.topic_04"
NATIVE_ASSOCIATION = {
    "key": "guild_report_dialogue",
    "topic_id": GUILD_TOPIC_ID,
    "label": "交談回報委託",
}


def _scene(scene_id):
    return {
        "scene_id": scene_id,
        "revision": "r1",
        "lines": [
            {"kind": "speech", "speaker": "actor", "text": "打擾了。"},
            {"kind": "speech", "speaker": "host", "text": "請說。"},
        ],
    }


def _topic(topic_id, keyword=GUILD_STAFF_TURNIN_KEYWORD):
    return {
        "topic_id": topic_id,
        "keyword": keyword,
        "label": keyword,
        "fallback": _scene(f"{topic_id}_scene"),
    }


def _static_payload(*, services=None, topic_id=GUILD_TOPIC_ID, keyword=None):
    payload = {
        "schema_version": 1,
        "greeting": None,
        "topics": [
            _topic(
                topic_id,
                keyword=GUILD_STAFF_TURNIN_KEYWORD if keyword is None else keyword,
            )
        ],
    }
    if services is not None:
        payload["services"] = services
    return payload


def _references():
    from world.rules.dialogue_references import static_dialogue_references

    return static_dialogue_references()


def _static_identity(dialogue_key=GUILD_STAFF_DIALOGUE_KEY):
    return StaticDialogueIdentity(profile_key="t_profile", dialogue_key=dialogue_key)


class ServiceRowParsingTests(unittest.TestCase):
    def test_absent_rows_are_the_empty_default(self):
        self.assertEqual(parse_service_rows(None), ())

    def test_a_valid_row_parses_into_an_immutable_association(self):
        (row,) = parse_service_rows([NATIVE_ASSOCIATION])
        self.assertEqual(row.key, "guild_report_dialogue")
        self.assertEqual(row.topic_id, GUILD_TOPIC_ID)
        self.assertEqual(row.label, "交談回報委託")

    def test_malformed_rows_reject(self):
        cases = {
            "not a list": {"key": "x"},
            "unknown field": [{**NATIVE_ASSOCIATION, "extra": 1}],
            "missing field": [{"key": "x", "topic_id": GUILD_TOPIC_ID}],
            "uppercase key": [{**NATIVE_ASSOCIATION, "key": "Guild"}],
            "long key": [{**NATIVE_ASSOCIATION, "key": "k" * 56}],
            "blank label": [{**NATIVE_ASSOCIATION, "label": ""}],
            "long label": [{**NATIVE_ASSOCIATION, "label": "字" * 65}],
            "duplicate key": [NATIVE_ASSOCIATION, NATIVE_ASSOCIATION],
            "duplicate topic": [
                NATIVE_ASSOCIATION,
                {**NATIVE_ASSOCIATION, "key": "other_key"},
            ],
            "too many": [
                {
                    "key": f"k{index:02d}",
                    "topic_id": f"guild_staff.topic_{index:02d}",
                    "label": "x",
                }
                for index in range(MAX_SERVICE_ASSOCIATIONS + 1)
            ],
        }
        for name, rows in cases.items():
            with self.subTest(name):
                with self.assertRaises(DialogueServiceError):
                    parse_service_rows(rows)


class DialogueServicePolicyTests(unittest.TestCase):
    def test_the_native_guild_report_association_is_supported(self):
        dialogue = parse_dialogue(
            _static_payload(services=[NATIVE_ASSOCIATION]),
            identity=_static_identity(),
            references=_references(),
        )
        (row,) = dialogue.services
        self.assertEqual(row.topic_id, GUILD_TOPIC_ID)
        supported = native_supported_topic_ids(GUILD_STAFF_DIALOGUE_KEY, dialogue)
        self.assertEqual(supported, {GUILD_TOPIC_ID})
        validate_service_associations(
            dialogue,
            dialogue_key=GUILD_STAFF_DIALOGUE_KEY,
            supported_topic_ids=supported,
        )

    def test_a_same_keyword_but_other_topic_is_unsupported(self):
        other_id = "guild_staff.topic_09"
        dialogue = parse_dialogue(
            _static_payload(
                services=[{**NATIVE_ASSOCIATION, "topic_id": other_id}],
                topic_id=other_id,
            ),
            identity=_static_identity(),
            references=_references(),
        )
        supported = native_supported_topic_ids(GUILD_STAFF_DIALOGUE_KEY, dialogue)
        with self.assertRaises(DialogueServiceError):
            validate_service_associations(
                dialogue,
                dialogue_key=GUILD_STAFF_DIALOGUE_KEY,
                supported_topic_ids=supported,
            )

    def test_an_informational_topic_is_never_a_service(self):
        dialogue = parse_dialogue(
            _static_payload(
                services=[NATIVE_ASSOCIATION], keyword="資訊"
            ),
            identity=_static_identity(),
            references=_references(),
        )
        self.assertEqual(dialogue.services[0].topic_id, GUILD_TOPIC_ID)
        self.assertEqual(
            native_supported_topic_ids(GUILD_STAFF_DIALOGUE_KEY, dialogue), set()
        )

    def test_a_narrative_dialogue_source_has_no_native_support(self):
        dialogue = parse_dialogue(
            _static_payload(services=[], topic_id="t_narrative.topic_01"),
            identity=_static_identity("t_narrative"),
            references=_references(),
        )
        self.assertEqual(
            native_supported_topic_ids("t_narrative", dialogue), set()
        )
        self.assertEqual(required_capability_types(GUILD_STAFF_DIALOGUE_KEY), {"guild_staff"})
        self.assertEqual(required_capability_types("t_narrative"), set())

    def test_a_dangling_reference_rejects_the_source(self):
        with self.assertRaises(ValueError):
            parse_dialogue(
                _static_payload(
                    services=[{**NATIVE_ASSOCIATION, "topic_id": "guild_staff.topic_99"}]
                ),
                identity=_static_identity(),
                references=_references(),
            )

    def test_generated_rows_compose_the_full_phase_identity(self):
        identity = GeneratedDialogueIdentity("pkg_abc", "role", "phase_one")
        dialogue = parse_dialogue(
            {
                "greeting": "嗨",
                "topics": [_topic("offer")],
                "services": [
                    {"key": "commission", "topic_id": "offer", "label": "洽談委託"}
                ],
            },
            identity=identity,
            references=_references(),
        )
        (topic,) = dialogue.topics
        (row,) = dialogue.services
        self.assertEqual(row.topic_id, topic.topic_id)
        self.assertEqual(
            row.topic_id,
            "g:" + encode_parts(["pkg_abc", "role", "phase_one", "offer"]),
        )
        # And the generated association is not native-supported.
        self.assertEqual(native_supported_topic_ids("pk", dialogue), set())


class StaticLoaderAtomicityTests(EvenniaTest):
    def _write(self, directory: Path, name: str, payload: str) -> None:
        (directory / f"{name}.yaml").write_text(payload, encoding="utf-8")

    def _content(self, topic_id):
        return (
            "schema_version: 1\n"
            "greeting: null\n"
            "topics:\n"
            f"- topic_id: {topic_id}\n"
            "  keyword: 回報\n"
            "  label: 回報\n"
            "  fallback:\n"
            f"    scene_id: {topic_id}_scene\n"
            "    revision: r1\n"
            "    lines:\n"
            "    - kind: speech\n"
            "      speaker: actor\n"
            "      text: 打擾了。\n"
            "services:\n"
            "- key: guild_report_dialogue\n"
            f"  topic_id: {topic_id}\n"
            "  label: 交談回報委託\n"
        )

    def test_one_unsupported_association_rejects_the_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self._write(directory, "t_one", self._content("guild_staff.topic_09"))
            with self.assertRaises(loader.DialogueSourceError):
                loader.load_dialogue_snapshot(
                    directory,
                    profiles=frozenset({"t_one"}),
                    bindings={"guild_staff": "t_one"},
                    references=_references(),
                )

    def test_the_accepted_snapshot_exposes_the_association(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self._write(directory, "t_one", self._content("guild_staff.topic_04"))
            snapshot = loader.load_dialogue_snapshot(
                directory,
                profiles=frozenset({"t_one"}),
                bindings={"guild_staff": "t_one"},
                references=_references(),
            )
        (row,) = snapshot["guild_staff"].services
        self.assertEqual(row.key, "guild_report_dialogue")


if __name__ == "__main__":
    unittest.main()
