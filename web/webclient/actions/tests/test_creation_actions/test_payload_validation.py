"""Creation and roll-name payload validation (pure unit tests)."""
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)
import unittest
from web.webclient.actions.creation_actions import (
    _creation_activate_adapter,
    _creation_concept_adapter,
    _creation_custom_adapter,
    _creation_preset_adapter,
    _creation_reset_adapter,
    validate_creation_activate_payload,
    validate_creation_concept_payload,
    validate_creation_custom_payload,
    validate_creation_preset_payload,
    validate_creation_reset_payload,
)
from ._support import (
    PERSONA_BLOCK,
    _T_PRESET,
    _T_RACE,
    _T_SUBRACE,
    _element_keys,
    _open_t_creation_scope,
    custom_payload,
)


class CreationPayloadValidationTests(unittest.TestCase):
    """Structural wire validation: the exact-shape claim is identity-agnostic
    (schema-valid strings only; the semantic race lookup lives in the adapter
    tests). The kit scope is registry patching only (no DB), so the shared
    ``custom_payload`` fixture can derive allocations from kit rows."""

    def setUp(self):
        _open_t_creation_scope(self)

    def test_preset_payload_is_exact(self):
        # Structural gate only: the key is any schema-valid identifier.
        self.assertEqual(
            validate_creation_preset_payload({"preset_key": _T_PRESET}),
            {"preset_key": _T_PRESET},
        )
        for bad in (
            {"preset_key": ""},
            {"preset_key": "x" * 65},
            {"preset_key": 5},
            {},
            {"preset_key": _T_PRESET, "actor": 1},
            {"preset_key": _T_PRESET, "account": 1},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_preset_payload(bad)

    def test_custom_payload_is_exact(self):
        valid = validate_creation_custom_payload(custom_payload())
        self.assertEqual(valid["display_name"], "  新角色  ")
        self.assertEqual(valid["age"], 20)
        # The wire mirrors the single creation authority exactly: the boundary
        # values of the legitimate 0..10000 range pass the exact-schema layer.
        self.assertEqual(
            validate_creation_custom_payload(custom_payload(age=0))["age"], 0
        )
        for bad in (
            {**custom_payload(), "account": 1},
            {**custom_payload(), "actor": 1},
            {**custom_payload(), "session": 1},
            {**custom_payload(), "magic_power": 1},
            {**custom_payload(), "skills": []},
            {**custom_payload(), "display_name": "x" * 65},
            {**custom_payload(), "age": -1},
            {**custom_payload(), "apparent_age": 10001},
            {**custom_payload(), "age": True},
            {**custom_payload(), "race": ""},
            {**custom_payload(), "subrace": 5},
            {**custom_payload(), "allocations": {"hp": 0}},
            {**custom_payload(), "allocations": {axis: True for axis in ALLOCATABLE_AXES}},
            {**custom_payload(), "allocations": {axis: -1 for axis in ALLOCATABLE_AXES}},
            # The persona key is required (nullable) and exact.
            {k: v for k, v in custom_payload().items() if k != "persona"},
            {**custom_payload(), "persona": {"personality": "沉穩"}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "extra": "x"}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "personality": " "}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "habit": "長" * 601}},
            {**custom_payload(), "persona": "沉穩"},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_custom_payload(bad)

    def test_custom_persona_payload_accepts_null_or_the_exact_block(self):
        self.assertIsNone(validate_creation_custom_payload(custom_payload())["persona"])
        self.assertEqual(
            validate_creation_custom_payload(
                custom_payload(persona=dict(PERSONA_BLOCK))
            )["persona"],
            PERSONA_BLOCK,
        )

    def test_activate_and_reset_payloads_are_exactly_empty(self):
        self.assertEqual(validate_creation_activate_payload({}), {})
        self.assertEqual(validate_creation_reset_payload({}), {})
        for bad in ({"draft": 1}, {"actor": 1}, None):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_activate_payload(bad)
                with self.assertRaises(Exception):
                    validate_creation_reset_payload(bad)

    def test_custom_affinity_payload_is_exact(self):
        # Pure structural claims (shape, duplicates, element membership): the
        # kit race rides along for the bound lookup, whose map is patched
        # with the kit entry (patched production state, not a kit registry —
        # the affinity-suite idiom), and the element keys are live vocabulary.
        payload = custom_payload()
        two = _element_keys(2)
        self.assertEqual(
            validate_creation_custom_payload(
                {**payload, "affinity_elements": list(two)}
            )["affinity_elements"],
            tuple(two),
        )
        self.assertEqual(
            validate_creation_custom_payload(payload)["affinity_elements"],
            None,
        )
        self.assertEqual(
            validate_creation_custom_payload(
                {**payload, "affinity_elements": []}
            )["affinity_elements"],
            (),
        )
        for bad in (
            {**payload, "affinity_elements": two[0]},
            {**payload, "affinity_elements": ["t_not_an_element"]},
            {**payload, "affinity_elements": [two[0], two[0]]},
            {**payload, "affinity_elements": {two[0]: True}},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_custom_payload(bad)


class RollNamePayloadValidationTests(unittest.TestCase):
    """Structural gate for the exact ``creation.roll_name`` payload (D5).

    Scope-free: the semantic gate is not reached, so the kit identities here
    are just schema-valid strings.
    """

    def test_exact_three_keys_with_nulls_and_identifiers(self):
        from web.webclient.actions.creation_actions import (
            validate_creation_roll_name_payload,
        )

        valid = {
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "sex": "female",
        }
        self.assertEqual(
            validate_creation_roll_name_payload(valid), dict(valid)
        )
        self.assertEqual(
            validate_creation_roll_name_payload(
                {"race": None, "subrace": None, "sex": None}
            ),
            {"race": None, "subrace": None, "sex": None},
        )

    def test_malformed_payloads_raise(self):
        from web.webclient.actions.creation_actions import (
            CreationActionError,
            validate_creation_roll_name_payload,
        )

        for bad in (
            {},
            {"race": _T_RACE, "subrace": None},
            {"race": _T_RACE, "subrace": None, "sex": None, "actor": 1},
            {"race": "", "subrace": None, "sex": None},
            {"race": "r" * 65, "subrace": None, "sex": None},
            {"race": 5, "subrace": None, "sex": None},
            {"race": _T_RACE, "subrace": None, "sex": True},
            "not-a-dict",
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(CreationActionError):
                    validate_creation_roll_name_payload(bad)

if __name__ == "__main__":
    unittest.main()
