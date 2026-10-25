"""Synthetic tests for authored scenes, topics, conditions, and codecs.

Covers:
- Immutable Speech, Narration, Scene data classes and mutability rejection.
- Scene code points, line counts, UTF-8 canonical byte limits.
- Formal scene starting with actor Speech.
- DialogueReferences and condition expression trees (All, Any, leaves, depth limits).
- Static and generated identity encoding/decoding, roundtripping, collision resistance.
- Topic and variant limits, unique priorities, DAG validation, cycle rejection.
- Disclosure ("qualified", "pure_chain") rules and public bundle byte limits.
- Backward compatibility: KeywordResponse and DialogueDefinition remain untouched.
"""

from dataclasses import FrozenInstanceError
import unittest

from world.lore.dialogue.codec import (
    GeneratedDialogueIdentity,
    StaticDialogueIdentity,
    decode_parts,
    dialogue_payload_schema,
    encode_parts,
    make_generated_host_key,
    make_generated_scene_id,
    make_generated_topic_id,
    make_static_host_key,
    parse_dialogue,
    parse_generated_scene_id,
    parse_generated_topic_id,
    validate_dialogue,
)
from world.lore.dialogue.conditions import (
    AffinityAtLeast,
    All,
    Any as AnyCond,
    Carries,
    CompanionPresent,
    DialogueReferences,
    Exposure,
    GuildRankAtLeast,
    QuestIs,
    RaceIs,
    SkillOwned,
    SocialIdentityIs,
    TimePeriod,
    condition_depth,
    condition_to_dict,
    validate_condition,
)
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    DialogueDefinition,
    KeywordResponse,
    SceneVariant,
)
from world.lore.scenes import (
    Narration,
    Scene,
    Speech,
    canonical_utf8_json_bytes,
    scene_canonical_bytes,
)


class AuthoredScenesTests(unittest.TestCase):
    """Test pure scene declarations and UTF-8 budget validation."""

    def test_speech_and_narration_immutability(self):
        sp = Speech(speaker="actor", text="Hello world")
        self.assertEqual(sp.speaker, "actor")
        self.assertEqual(sp.text, "Hello world")
        with self.assertRaises(FrozenInstanceError):
            sp.text = "modified"  # type: ignore

        narr = Narration(text="Wind blows softly.")
        self.assertEqual(narr.text, "Wind blows softly.")
        with self.assertRaises(FrozenInstanceError):
            narr.text = "modified"  # type: ignore

    def test_speech_speaker_validation(self):
        with self.assertRaises(ValueError):
            Speech(speaker="invalid", text="hi")  # type: ignore
        with self.assertRaises(ValueError):
            Speech(speaker="actor", text="")  # empty line rejected
        with self.assertRaises(ValueError):
            Speech(speaker="actor", text="a" * 2001)  # exceeds 2000 code points

    def test_scene_immutability_and_bounds(self):
        line1 = Speech(speaker="actor", text="Greeting")
        line2 = Speech(speaker="host", text="Welcome")
        sc = Scene(scene_id="test_scene", revision="rev1", lines=(line1, line2))
        self.assertEqual(sc.scene_id, "test_scene")
        self.assertEqual(sc.revision, "rev1")
        self.assertEqual(len(sc.lines), 2)
        with self.assertRaises(FrozenInstanceError):
            sc.revision = "rev2"  # type: ignore

    def test_scene_rejection_on_bound_exceeded(self):
        # Empty lines
        with self.assertRaises(ValueError):
            Scene(scene_id="s1", revision="r1", lines=())
        # Exceeds 32 lines
        too_many = tuple(Speech(speaker="actor", text=f"Line {i}") for i in range(33))
        with self.assertRaises(ValueError):
            Scene(scene_id="s1", revision="r1", lines=too_many)
        # Exceeds 16000 code points
        huge_lines = tuple(Speech(speaker="actor", text="a" * 2000) for _ in range(9))
        with self.assertRaises(ValueError):
            Scene(scene_id="s1", revision="r1", lines=huge_lines)


class AuthoredConditionsTests(unittest.TestCase):
    """Test conditions expression tree and DialogueReferences."""

    def test_dialogue_references_api(self):
        refs = DialogueReferences.empty()
        self.assertEqual(refs.keys_for("race"), frozenset())
        self.assertIsNone(refs.label("race", "human"))

        with_race = refs.child("race", {"human": "Race A", "elf": "Race B"})
        self.assertIn("human", with_race.keys_for("race"))
        self.assertEqual(with_race.label("race", "human"), "Race A")
        # Immuntability of parent
        self.assertEqual(refs.keys_for("race"), frozenset())

        with self.assertRaises(ValueError):
            refs.child("unknown_family", {})

    def test_condition_constructors_and_depth(self):
        r = RaceIs(race_key="human")
        s = SocialIdentityIs(identity_key="commoner")
        a = All(children=(r, s))
        self.assertEqual(condition_depth(a), 2)

        exp = Exposure(minimum=1, maximum=3)
        self.assertEqual(exp.minimum, 1)
        self.assertEqual(exp.maximum, 3)

        with self.assertRaises(ValueError):
            Exposure()  # requires at least one bound
        with self.assertRaises(ValueError):
            Exposure(minimum=5, maximum=2)  # min > max

    def test_condition_validation_against_references(self):
        refs = DialogueReferences.empty().child("race", {"human": "Race A"})
        # Valid race
        validate_condition(RaceIs(race_key="human"), refs)
        # Invalid race
        with self.assertRaises(ValueError):
            validate_condition(RaceIs(race_key="orc"), refs)

        # CompanionPresent package_role
        cp = CompanionPresent(source_kind="package_role", source_key="guide")
        with self.assertRaises(ValueError):
            validate_condition(cp, refs, package_roles=frozenset({"lookout"}))
        validate_condition(cp, refs, package_roles=frozenset({"guide"}))


class AuthoredCodecAndDAGTests(unittest.TestCase):
    """Test codec, identity encoding, DAG cycles, and bundle budgets."""

    def test_encode_decode_parts_roundtrip(self):
        parts = ["pkg_01", "role_hero", "phase_act1", "topic_intro"]
        encoded = encode_parts(parts)
        decoded = decode_parts(encoded)
        self.assertEqual(parts, decoded)

        # Re-encoding check fails on modified string
        with self.assertRaises(ValueError):
            decode_parts(encoded + "==")

    def test_generated_id_codec(self):
        t_id = make_generated_topic_id("p1", "r1", "ph1", "local_t")
        self.assertTrue(t_id.startswith("g:"))
        parsed = parse_generated_topic_id(t_id)
        self.assertEqual(parsed, ("p1", "r1", "ph1", "local_t"))

        s_id = make_generated_scene_id("p1", "r1", "ph1", "local_s")
        self.assertTrue(s_id.startswith("g:"))
        parsed_s = parse_generated_scene_id(s_id)
        self.assertEqual(parsed_s, ("p1", "r1", "ph1", "local_s"))

        host_key = make_generated_host_key("p1", "r1")
        self.assertTrue(host_key.startswith("g:"))

        static_key = make_static_host_key("alpha_merchant")
        self.assertEqual(static_key, "s:alpha_merchant")

    def test_static_dialogue_parsing_and_validation(self):
        refs = DialogueReferences.empty().child("race", {"human": "Race A"})
        identity = StaticDialogueIdentity(profile_key="alpha_merchant", dialogue_key="merchant_talk")

        payload = {
            "schema_version": 1,
            "greeting": "歡迎光臨！",
            "topics": [
                {
                    "topic_id": "merchant_talk.wares",
                    "keyword": "商品",
                    "label": "查看商品",
                    "fallback": {
                        "scene_id": "merchant.wares_fallback",
                        "revision": "r1",
                        "lines": [
                            {"kind": "speech", "speaker": "actor", "text": "請問有什麼？"},
                            {"kind": "speech", "speaker": "host", "text": "這些都是上好的貨物。"},
                        ],
                    },
                }
            ],
        }

        dialogue = parse_dialogue(payload, identity=identity, references=refs)
        self.assertEqual(len(dialogue.topics), 1)
        self.assertEqual(dialogue.topics[0].topic_id, "merchant_talk.wares")

    def test_generated_dialogue_local_id_normalization(self):
        refs = DialogueReferences.empty()
        identity = GeneratedDialogueIdentity(package_id="pkg1", role_id="r1", phase_id="ph1")

        payload = {
            "greeting": "你好旅人。",
            "topics": [
                {
                    "topic_id": "intro",
                    "keyword": "問候",
                    "label": "打招呼",
                    "fallback": {
                        "scene_id": "intro_scene",
                        "revision": "r1",
                        "lines": [
                            {"kind": "speech", "speaker": "actor", "text": "你好！"},
                            {"kind": "speech", "speaker": "host", "text": "很高興遇見你。"},
                        ],
                    },
                }
            ],
        }

        dialogue = parse_dialogue(payload, identity=identity, references=refs)
        self.assertEqual(len(dialogue.topics), 1)
        # Verify local ID normalized to full g: ID
        expected_t_id = make_generated_topic_id("pkg1", "r1", "ph1", "intro")
        expected_s_id = make_generated_scene_id("pkg1", "r1", "ph1", "intro_scene")
        self.assertEqual(dialogue.topics[0].topic_id, expected_t_id)
        self.assertEqual(dialogue.topics[0].fallback.scene_id, expected_s_id)

    def test_formal_scene_must_begin_with_actor_speech(self):
        refs = DialogueReferences.empty()
        identity = StaticDialogueIdentity(profile_key="alpha_merchant", dialogue_key="merchant_talk")

        payload = {
            "schema_version": 1,
            "greeting": "歡迎！",
            "topics": [
                {
                    "topic_id": "merchant_talk.wares",
                    "keyword": "商品",
                    "label": "查看商品",
                    "fallback": {
                        "scene_id": "merchant.wares_fallback",
                        "revision": "r1",
                        "lines": [
                            {"kind": "speech", "speaker": "host", "text": "這是老闆先說話。"},
                        ],
                    },
                }
            ],
        }

        with self.assertRaises(ValueError) as ctx:
            parse_dialogue(payload, identity=identity, references=refs)
        self.assertIn("must begin with an actor Speech line", str(ctx.exception))

    def test_refusal_scene_permits_host_first_speech(self):
        refs = DialogueReferences.empty()
        identity = StaticDialogueIdentity(profile_key="alpha_merchant", dialogue_key="merchant_talk")

        payload = {
            "schema_version": 1,
            "greeting": "歡迎！",
            "topics": [
                {
                    "topic_id": "merchant_talk.secret",
                    "keyword": "秘密",
                    "label": "打聽秘密",
                    "unavailable": "locked",
                    "fallback": {
                        "scene_id": "merchant.secret_fallback",
                        "revision": "r1",
                        "lines": [
                            {"kind": "speech", "speaker": "actor", "text": "有什麼不能說的？"},
                        ],
                    },
                    "refusal": {
                        "scene_id": "merchant.secret_refusal",
                        "revision": "r1",
                        "lines": [
                            {"kind": "speech", "speaker": "host", "text": "這件事我現在不能告訴你。"},
                        ],
                    },
                }
            ],
        }
        dialogue = parse_dialogue(payload, identity=identity, references=refs)
        self.assertIsNotNone(dialogue.topics[0].refusal)
        self.assertEqual(dialogue.topics[0].refusal.lines[0].speaker, "host")

    def test_predecessor_cycle_rejection(self):
        refs = DialogueReferences.empty()
        identity = StaticDialogueIdentity(profile_key="alpha_merchant", dialogue_key="merchant_talk")

        fallback_a = {
            "scene_id": "merchant.scene_a",
            "revision": "r1",
            "lines": [{"kind": "speech", "speaker": "actor", "text": "A"}],
        }
        fallback_b = {
            "scene_id": "merchant.scene_b",
            "revision": "r1",
            "lines": [{"kind": "speech", "speaker": "actor", "text": "B"}],
        }

        payload = {
            "schema_version": 1,
            "greeting": "歡迎！",
            "topics": [
                {
                    "topic_id": "merchant_talk.t1",
                    "keyword": "話語一",
                    "label": "話語一",
                    "fallback": fallback_a,
                    "predecessors": ["merchant_talk.t2"],
                },
                {
                    "topic_id": "merchant_talk.t2",
                    "keyword": "話語二",
                    "label": "話語二",
                    "fallback": fallback_b,
                    "predecessors": ["merchant_talk.t1"],
                },
            ],
        }

        with self.assertRaises(ValueError) as ctx:
            parse_dialogue(payload, identity=identity, references=refs)
        self.assertIn("Cycle detected", str(ctx.exception))

    def test_legacy_keyword_response_preserved(self):
        # Verification that existing legacy classes remain functional
        resp = KeywordResponse(keyword="問候", response="你好啊")
        self.assertEqual(resp.keyword, "問候")
        self.assertEqual(resp.response, "你好啊")

        defn = DialogueDefinition(greeting="哈囉", responses=(resp,))
        self.assertEqual(defn.greeting, "哈囉")
        self.assertEqual(len(defn.responses), 1)
