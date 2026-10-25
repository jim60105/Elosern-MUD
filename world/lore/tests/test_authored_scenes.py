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

from tools.spec_traceability import covers_requirement

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
    line_to_dict,
    scene_canonical_bytes,
    scene_to_dict,
)


class AuthoredScenesTests(unittest.TestCase):
    """Test pure scene declarations and UTF-8 budget validation."""

    @covers_requirement("authored-scene-model::declarative-scenes-preserve-attribution")
    def test_scene_serialization_preserves_order_and_speakerless_narration(self):
        scene = Scene(
            scene_id="merchant.opening",
            revision="r1",
            lines=(
                Speech(speaker="actor", text="我想打聽消息。"),
                Speech(speaker="host", text="哦？"),
                Speech(speaker="host", text="說來聽聽。"),
                Narration(text="老闆放下手中的帳本。"),
            ),
        )

        wire = scene_to_dict(scene)

        self.assertEqual(
            [line["kind"] for line in wire["lines"]],
            ["speech", "speech", "speech", "narration"],
        )
        self.assertEqual(
            [line.get("speaker") for line in wire["lines"]],
            ["actor", "host", "host", None],
        )
        self.assertNotIn("speaker", wire["lines"][-1])
        self.assertEqual(len(canonical_utf8_json_bytes(wire)), scene_canonical_bytes(scene))

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

    @covers_requirement("authored-scene-model::declarative-scenes-preserve-attribution")
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

    @covers_requirement(
        "authored-scene-model::static-and-generated-primitives-share-immutable-scene-validation"
    )
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

    @covers_requirement("authored-scene-model::declarative-scenes-preserve-attribution")
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

    @covers_requirement("authored-scene-model::topic-declarations-retain-stable-reading-identity")
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

    @covers_requirement(
        "authored-scene-model::static-and-generated-primitives-share-immutable-scene-validation"
    )
    def test_static_and_generated_providers_share_scene_semantics(self):
        refs = DialogueReferences.empty().child("race", {"human": "Race A"})
        shared_lines = [
            {"kind": "speech", "speaker": "actor", "text": "請問有什麼？"},
            {"kind": "speech", "speaker": "host", "text": "這些都是上好的貨物。"},
            {"kind": "narration", "text": "老闆拍了拍櫃檯。"},
        ]

        static_definition = parse_dialogue(
            {
                "schema_version": 1,
                "greeting": None,
                "topics": [
                    {
                        "topic_id": "merchant_talk.wares",
                        "keyword": "商品",
                        "label": "查看商品",
                        "fallback": {
                            "scene_id": "merchant.wares",
                            "revision": "r1",
                            "lines": shared_lines,
                        },
                    }
                ],
            },
            identity=StaticDialogueIdentity(
                profile_key="alpha_merchant", dialogue_key="merchant_talk"
            ),
            references=refs,
        )
        generated_definition = parse_dialogue(
            {
                "greeting": None,
                "topics": [
                    {
                        "topic_id": "wares",
                        "keyword": "商品",
                        "label": "查看商品",
                        "fallback": {"scene_id": "wares", "revision": "r1", "lines": shared_lines},
                    }
                ],
            },
            identity=GeneratedDialogueIdentity(package_id="pkg1", role_id="r1", phase_id="ph1"),
            references=refs,
        )

        self.assertEqual(
            [line_to_dict(line) for line in static_definition.topics[0].fallback.lines],
            [line_to_dict(line) for line in generated_definition.topics[0].fallback.lines],
        )

        host_first_lines = [{"kind": "speech", "speaker": "host", "text": "我先說。"}]
        duplicate_priority_variants = [
            {
                "variant_id": "tone_a",
                "priority": 10,
                "when": {"kind": "race_is", "race_key": "human"},
                "scene": {"scene_id": "topic_a", "revision": "r1", "lines": shared_lines},
            },
            {
                "variant_id": "tone_b",
                "priority": 10,
                "when": {"kind": "race_is", "race_key": "human"},
                "scene": {"scene_id": "topic_b", "revision": "r1", "lines": shared_lines},
            },
        ]
        malformed_cases = (
            (
                {
                    "schema_version": 1,
                    "greeting": None,
                    "topics": [
                        {
                            "topic_id": "merchant_talk.wares",
                            "keyword": "商品",
                            "label": "查看商品",
                            "fallback": {
                                "scene_id": "merchant.bad",
                                "revision": "r1",
                                "lines": host_first_lines,
                            },
                        }
                    ],
                },
                StaticDialogueIdentity(
                    profile_key="alpha_merchant", dialogue_key="merchant_talk"
                ),
                "must begin with an actor Speech line",
            ),
            (
                {
                    "greeting": None,
                    "topics": [
                        {
                            "topic_id": "wares",
                            "keyword": "商品",
                            "label": "查看商品",
                            "fallback": {
                                "scene_id": "bad",
                                "revision": "r1",
                                "lines": host_first_lines,
                            },
                        }
                    ],
                },
                GeneratedDialogueIdentity(package_id="pkg1", role_id="r1", phase_id="ph1"),
                "must begin with an actor Speech line",
            ),
            (
                {
                    "schema_version": 1,
                    "greeting": None,
                    "topics": [
                        {
                            "topic_id": "merchant_talk.wares",
                            "keyword": "商品",
                            "label": "查看商品",
                            "fallback": {
                                "scene_id": "merchant.wares",
                                "revision": "r1",
                                "lines": shared_lines,
                            },
                            "variants": duplicate_priority_variants,
                        }
                    ],
                },
                StaticDialogueIdentity(
                    profile_key="alpha_merchant", dialogue_key="merchant_talk"
                ),
                "Duplicate variant priority",
            ),
            (
                {
                    "greeting": None,
                    "topics": [
                        {
                            "topic_id": "wares",
                            "keyword": "商品",
                            "label": "查看商品",
                            "fallback": {"scene_id": "wares", "revision": "r1", "lines": shared_lines},
                            "variants": duplicate_priority_variants,
                        }
                    ],
                },
                GeneratedDialogueIdentity(package_id="pkg1", role_id="r1", phase_id="ph1"),
                "Duplicate variant priority",
            ),
        )
        for payload, identity, expected_message in malformed_cases:
            with self.assertRaises(ValueError) as ctx:
                parse_dialogue(payload, identity=identity, references=refs)
            self.assertIn(expected_message, str(ctx.exception))

    @covers_requirement(
        "authored-scene-model::static-and-generated-primitives-share-immutable-scene-validation"
    )
    def test_generated_identity_is_collision_free_and_lossless(self):
        first = make_generated_topic_id("pkg_a", "role_hero", "phase_act1", "intro")
        second = make_generated_topic_id("pkg_b", "role_hero", "phase_act1", "intro")
        self.assertNotEqual(first, second)
        self.assertEqual(parse_generated_topic_id(first)[0], "pkg_a")
        self.assertEqual(parse_generated_topic_id(second)[0], "pkg_b")

        unicode_parts = ["套件甲", "角色" * 20, "階段", "local_topic"]
        unicode_topic_id = make_generated_topic_id(*unicode_parts)
        self.assertEqual(parse_generated_topic_id(unicode_topic_id), tuple(unicode_parts))
        self.assertNotEqual(
            unicode_topic_id, make_generated_topic_id(*unicode_parts[:-1], "other_topic")
        )
        self.assertTrue(unicode_topic_id.startswith("g:"))

        long_parts = ("p" * 64, "r" * 64, "phase", "intro")
        long_topic_id = make_generated_topic_id(*long_parts)
        self.assertGreater(len(long_topic_id), 96)
        self.assertEqual(parse_generated_topic_id(long_topic_id), long_parts)

    @covers_requirement("authored-scene-model::topic-declarations-retain-stable-reading-identity")
    def test_topic_identity_priorities_and_unconditional_fallback(self):
        def scene(scene_id: str) -> Scene:
            return Scene(
                scene_id=scene_id,
                revision="r1",
                lines=(Speech(speaker="actor", text="請問？"),),
            )

        fallback = scene("merchant.wares_fallback")
        variant = SceneVariant(
            variant_id="tone_a",
            priority=10,
            when=RaceIs(race_key="human"),
            scene=scene("merchant.wares_a"),
        )
        topic = AuthoredTopic(
            topic_id="merchant_talk.wares",
            keyword="商品",
            label="查看商品",
            fallback=fallback,
            variants=(variant,),
        )
        relabelled = AuthoredTopic(
            topic_id="merchant_talk.wares",
            keyword="貨物",
            label="檢視貨品",
            fallback=fallback,
        )

        self.assertEqual(topic.topic_id, relabelled.topic_id)
        self.assertEqual(relabelled.variants, ())
        self.assertIsNone(relabelled.requires)
        self.assertIs(relabelled.fallback, fallback)

        with self.assertRaises(ValueError):
            AuthoredTopic(
                topic_id="merchant_talk.wares",
                keyword="商品",
                label="查看商品",
                fallback=fallback,
                variants=(
                    variant,
                    SceneVariant(
                        variant_id="tone_b",
                        priority=10,
                        when=RaceIs(race_key="elf"),
                        scene=scene("merchant.wares_b"),
                    ),
                ),
            )
        with self.assertRaises(ValueError):
            AuthoredDialogue(greeting=None, topics=(topic, relabelled))

    @covers_requirement("authored-scene-model::topic-declarations-retain-stable-reading-identity")
    def test_pure_chain_topic_rejects_qualified_ancestor(self):
        refs = DialogueReferences.empty().child("race", {"human": "Race A"})
        identity = StaticDialogueIdentity(
            profile_key="alpha_merchant", dialogue_key="merchant_talk"
        )

        def scene(scene_id: str) -> dict[str, object]:
            return {
                "scene_id": scene_id,
                "revision": "r1",
                "lines": [{"kind": "speech", "speaker": "actor", "text": "請問？"}],
            }

        payload = {
            "schema_version": 1,
            "greeting": None,
            "topics": [
                {
                    "topic_id": "merchant_talk.gate",
                    "keyword": "門檻",
                    "label": "門檻",
                    "fallback": scene("merchant.gate"),
                    "requires": {"kind": "race_is", "race_key": "human"},
                },
                {
                    "topic_id": "merchant_talk.follow",
                    "keyword": "後續",
                    "label": "後續",
                    "fallback": scene("merchant.follow"),
                    "predecessors": ["merchant_talk.gate"],
                    "disclosure": "pure_chain",
                },
            ],
        }

        with self.assertRaises(ValueError) as ctx:
            parse_dialogue(payload, identity=identity, references=refs)
        self.assertIn("depends on ancestor", str(ctx.exception))

    def test_legacy_keyword_response_preserved(self):
        # Verification that existing legacy classes remain functional
        resp = KeywordResponse(keyword="問候", response="你好啊")
        self.assertEqual(resp.keyword, "問候")
        self.assertEqual(resp.response, "你好啊")

        defn = DialogueDefinition(greeting="哈囉", responses=(resp,))
        self.assertEqual(defn.greeting, "哈囉")
        self.assertEqual(len(defn.responses), 1)
