import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from tools.spec_traceability import covers_requirement

from web.webclient.actions.npc_persona_actions import (
    CODE_NOT_ALLOWED,
    CODE_NO_TARGET,
    CODE_UNAVAILABLE,
    CODE_VERSION_CONFLICT,
    NpcPersonaActionError,
    read_npc_persona_adapter,
    update_npc_persona_adapter,
    validate_read_payload,
    validate_update_payload,
)
from world.lore.npc_card import NpcCard, NpcCardError
from world.rules.npc_persona import NpcPersonaSnapshot, NpcPersonaUnavailable, UpdateOutcome


def _valid_card_dict():
    return {
        "identity": {"public": "侍者", "hidden": "情報員"},
        "appearance": "金髮藍眼。",
        "personality": "隨和熱心。",
        "speech_style": "客氣得體。",
        "life_story": "在公會服務五年。",
        "habit": "擦拭玻璃杯。",
        "social_connection": "與公會會長相熟。",
    }


class NpcPersonaActionValidatorsTest(unittest.TestCase):
    @covers_requirement("npc-persona-editor::the-browser-mirrors-the-card-contract-exactly")
    def test_validate_read_payload_success(self):
        result = validate_read_payload({"npc_id": 42})
        self.assertEqual(result, {"npc_id": 42})

    def test_validate_read_payload_rejects_non_dict(self):
        for val in (None, 42, "string", [42]):
            with self.subTest(val=val):
                with self.assertRaises(NpcPersonaActionError):
                    validate_read_payload(val)

    def test_validate_read_payload_rejects_missing_or_extra_keys(self):
        with self.assertRaises(NpcPersonaActionError):
            validate_read_payload({})
        with self.assertRaises(NpcPersonaActionError):
            validate_read_payload({"npc_id": 42, "extra": True})

    def test_validate_read_payload_rejects_invalid_npc_id(self):
        for val in (True, False, 0, -1, "42", 1.5, 9_007_199_254_740_992):
            with self.subTest(val=val):
                with self.assertRaises(NpcPersonaActionError):
                    validate_read_payload({"npc_id": val})

    def test_validate_update_payload_success(self):
        payload = {
            "npc_id": 10,
            "expected_persona_version": 3,
            "persona": _valid_card_dict(),
        }
        result = validate_update_payload(payload)
        self.assertEqual(result["npc_id"], 10)
        self.assertEqual(result["expected_persona_version"], 3)
        self.assertEqual(result["persona"], _valid_card_dict())

    def test_validate_update_payload_offline_greeting_is_optional_text(self):
        base = {"npc_id": 10, "expected_persona_version": 3, "persona": _valid_card_dict()}
        self.assertEqual(validate_update_payload(base)["offline_greeting"], "")
        self.assertEqual(
            validate_update_payload({**base, "offline_greeting": "「你好。」"})["offline_greeting"], "「你好。」"
        )
        for bad in (42, None, True, ["x"], "字" * 2049):
            with self.subTest(bad=bad):
                with self.assertRaises(NpcPersonaActionError):
                    validate_update_payload({**base, "offline_greeting": bad})
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "greeting": "x"})

    def test_validate_update_payload_rejects_non_dict_or_bad_envelope_keys(self):
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload(None)
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({"npc_id": 1, "expected_persona_version": 1})
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": 1,
                "expected_persona_version": 1,
                "persona": _valid_card_dict(),
                "extra": 123,
            })

    def test_validate_update_payload_rejects_invalid_types_and_integers(self):
        # npc_id invalid
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": True,
                "expected_persona_version": 1,
                "persona": _valid_card_dict(),
            })
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": 0,
                "expected_persona_version": 1,
                "persona": _valid_card_dict(),
            })

        # expected_persona_version invalid
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": 1,
                "expected_persona_version": False,
                "persona": _valid_card_dict(),
            })
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": 1,
                "expected_persona_version": -5,
                "persona": _valid_card_dict(),
            })
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({
                "npc_id": 1,
                "expected_persona_version": 9_007_199_254_740_992,
                "persona": _valid_card_dict(),
            })

    def test_validate_update_payload_rejects_bad_persona_structure(self):
        base = {"npc_id": 1, "expected_persona_version": 1}

        # persona is not dict
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": "not a dict"})

        # missing top-level key
        card = _valid_card_dict()
        del card["habit"]
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        # extra top-level key
        card = _valid_card_dict()
        card["secret"] = "something"
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        # identity not dict
        card = _valid_card_dict()
        card["identity"] = "侍者"
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        # identity missing key or extra key
        card = _valid_card_dict()
        card["identity"] = {"public": "侍者"}
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        card = _valid_card_dict()
        card["identity"] = {"public": "侍者", "hidden": "", "secret": ""}
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        # leaf not string
        card = _valid_card_dict()
        card["appearance"] = 123
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        card = _valid_card_dict()
        card["identity"]["public"] = None
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})

        # leaf exceeds MAX_STRING_CODE_POINTS (2048)
        card = _valid_card_dict()
        card["appearance"] = "A" * 2049
        with self.assertRaises(NpcPersonaActionError):
            validate_update_payload({**base, "persona": card})


if __name__ == "__main__":
    unittest.main()
