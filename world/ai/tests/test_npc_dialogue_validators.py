"""Direct shape tests for the per-kind npc-dialogue semantic validators."""


import unittest

from world.ai import npc_dialogue

from tools.spec_traceability import covers_requirement



class AffinityValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the adjust_relation and no-leak validators."""

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_relation_payload_requires_exactly_one_integer_delta_in_range(self):
        valid = {"kind": "adjust_relation", "delta": 3}
        self.assertEqual(
            npc_dialogue._validate_relation_payload({"speech": "s", "intent": valid}), []
        )
        for bad in (
            {"kind": "adjust_relation", "delta": -1},
            {"kind": "adjust_relation", "delta": 11},
            {"kind": "adjust_relation", "delta": 1.5},
            {"kind": "adjust_relation", "delta": True},
            {"kind": "adjust_relation"},
            {"kind": "adjust_relation", "delta": 3, "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_relation_payload(
                        {"speech": "s", "intent": bad}
                    )
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_relation_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "give_item", "item_key": "x", "qty": 1},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_relation_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_no_leak_validator_rejects_value_and_cap_substrings(self):
        validate = npc_dialogue._make_no_affinity_leak_validator(55, 99)
        self.assertEqual(validate({"speech": "你是我的信賴。"}), [])
        self.assertTrue(validate({"speech": "好感 55 點。"}))
        self.assertTrue(validate({"speech": "上限是 99。"}))
        self.assertTrue(validate({"speech": "好感是 ５５ 點。"}))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_no_leak_validator_is_bound_to_its_own_call_numbers(self):
        validate = npc_dialogue._make_no_affinity_leak_validator(55, 99)
        self.assertEqual(validate({"speech": "好感 2 點。"}), [])
        other = npc_dialogue._make_no_affinity_leak_validator(2, 99)
        self.assertTrue(other({"speech": "好感 2 點。"}))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_affinity_validator_keeps_the_original_error_text(self):
        validate = npc_dialogue._make_no_affinity_leak_validator(55, 99)
        self.assertEqual(
            validate({"speech": "好感 55 點。"}),
            ["dialogue speech echoes the secret affinity number(s): 55"],
        )
        self.assertEqual(
            validate({"speech": "上限是 99。"}),
            ["dialogue speech echoes the secret affinity number(s): 99"],
        )


class PartyInviteValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the party_invite semantic validator."""

    def test_party_payload_requires_exactly_one_boolean_accept(self):
        for valid in (True, False):
            with self.subTest(accept=valid):
                self.assertEqual(
                    npc_dialogue._validate_party_payload(
                        {"speech": "s", "intent": {"kind": "party_invite", "accept": valid}}
                    ),
                    [],
                )
        for bad in (
            {"kind": "party_invite"},
            {"kind": "party_invite", "accept": "yes"},
            {"kind": "party_invite", "accept": 1},
            {"kind": "party_invite", "accept": True, "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_party_payload({"speech": "s", "intent": bad})
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_party_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "adjust_relation", "delta": 3},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_party_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_whitelist_and_schema_carry_party_invite(self):
        self.assertIn("party_invite", npc_dialogue.NPC_INTENT_KINDS)
        properties = npc_dialogue.NPC_DIALOGUE_OUTPUT_SCHEMA["properties"]["intent"]["properties"]
        self.assertEqual(properties["accept"], {"type": "boolean"})


class OfferQuestValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the offer_quest semantic validator."""

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_valid_offer_quest_payload_passes(self):
        self.assertEqual(
            npc_dialogue._validate_offer_quest_payload(
                {"speech": "s", "intent": {"kind": "offer_quest", "quest_key": "forest_clearing"}}
            ),
            [],
        )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_quest_key_boundary_is_exactly_64_code_points(self):
        bound = "q" * npc_dialogue.MAX_INTENT_KEY_LENGTH
        over = "q" * (npc_dialogue.MAX_INTENT_KEY_LENGTH + 1)
        self.assertEqual(
            npc_dialogue._validate_offer_quest_payload(
                {"speech": "s", "intent": {"kind": "offer_quest", "quest_key": bound}}
            ),
            [],
        )
        self.assertTrue(
            npc_dialogue._validate_offer_quest_payload(
                {"speech": "s", "intent": {"kind": "offer_quest", "quest_key": over}}
            )
        )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_malformed_offer_quest_payloads_are_rejected(self):
        for bad in (
            {"kind": "offer_quest"},
            {"kind": "offer_quest", "quest_key": ""},
            {"kind": "offer_quest", "quest_key": "   "},
            {"kind": "offer_quest", "quest_key": 3},
            {"kind": "offer_quest", "quest_key": True},
            {"kind": "offer_quest", "quest_key": "forest_clearing", "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_offer_quest_payload(
                        {"speech": "s", "intent": bad}
                    )
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_offer_quest_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "adjust_relation", "delta": 3},
            {"kind": "party_invite", "accept": True},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_offer_quest_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_whitelist_and_schema_carry_offer_quest(self):
        self.assertIn("offer_quest", npc_dialogue.NPC_INTENT_KINDS)
        self.assertEqual(npc_dialogue.MAX_INTENT_KEY_LENGTH, 64)


class RevealLoreValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the reveal_lore semantic validator."""

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_valid_reveal_lore_payload_passes(self):
        self.assertEqual(
            npc_dialogue._validate_reveal_lore_payload(
                {
                    "speech": "s",
                    "intent": {"kind": "reveal_lore", "category": "race", "key": "elf"},
                }
            ),
            [],
        )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_reveal_lore_field_boundary_is_exactly_64_code_points(self):
        bound = "k" * npc_dialogue.MAX_INTENT_KEY_LENGTH
        over = "k" * (npc_dialogue.MAX_INTENT_KEY_LENGTH + 1)
        self.assertEqual(
            npc_dialogue._validate_reveal_lore_payload(
                {
                    "speech": "s",
                    "intent": {"kind": "reveal_lore", "category": "race", "key": bound},
                }
            ),
            [],
        )
        self.assertTrue(
            npc_dialogue._validate_reveal_lore_payload(
                {
                    "speech": "s",
                    "intent": {"kind": "reveal_lore", "category": "race", "key": over},
                }
            )
        )
        self.assertTrue(
            npc_dialogue._validate_reveal_lore_payload(
                {
                    "speech": "s",
                    "intent": {
                        "kind": "reveal_lore",
                        "category": "c" * (npc_dialogue.MAX_INTENT_KEY_LENGTH + 1),
                        "key": "elf",
                    },
                }
            )
        )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_malformed_reveal_lore_payloads_are_rejected(self):
        for bad in (
            {"kind": "reveal_lore"},
            {"kind": "reveal_lore", "category": "race"},
            {"kind": "reveal_lore", "category": "", "key": "elf"},
            {"kind": "reveal_lore", "category": "   ", "key": "elf"},
            {"kind": "reveal_lore", "category": "race", "key": ""},
            {"kind": "reveal_lore", "category": "race", "key": 3},
            {"kind": "reveal_lore", "category": True, "key": "elf"},
            {"kind": "reveal_lore", "category": "race", "key": "elf", "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_reveal_lore_payload(
                        {"speech": "s", "intent": bad}
                    )
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_reveal_lore_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "adjust_relation", "delta": 3},
            {"kind": "party_invite", "accept": True},
            {"kind": "offer_quest", "quest_key": "forest_clearing"},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_reveal_lore_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_whitelist_and_schema_carry_reveal_lore(self):
        self.assertIn("reveal_lore", npc_dialogue.NPC_INTENT_KINDS)
        self.assertEqual(npc_dialogue.MAX_INTENT_KEY_LENGTH, 64)


class SecretSetValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the generalized secret-set no-leak validator."""

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_secret_set_rejects_every_bound_number_and_folds_fullwidth_digits(self):
        validate = npc_dialogue._make_no_leak_validator(frozenset({"55", "99", "88"}))
        self.assertEqual(validate({"speech": "你是我信賴的人。"}), [])
        self.assertTrue(validate({"speech": "我的攻擊是 88 點。"}))
        self.assertTrue(validate({"speech": "好感 55 點。"}))
        self.assertTrue(validate({"speech": "上限是 ９９ 點。"}))

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_secret_set_passes_disguised_and_unbound_numbers(self):
        validate = npc_dialogue._make_no_leak_validator(frozenset({"88"}))
        self.assertEqual(validate({"speech": "我的攻擊是 60 點。"}), [])
        self.assertEqual(validate({"speech": "2 點。"}), [])
        self.assertEqual(validate({"speech": 88}), [])
        self.assertEqual(validate({"intent": {"kind": "none"}}), [])
