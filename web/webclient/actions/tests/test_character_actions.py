"""``character.persona.update`` validator, adapter, and registry wiring.

Exercises the exact ``{field, text}`` payload validator (four-key whitelist,
trim-to-1..600 bound, ``null`` clear), the rules-writer delegation through
``world.rules.persona_edit.update_persona_field`` (no direct ``.db`` writes),
the exploration-mode admission gate (creation-pending and in-combat actors are
refused), the stable rejection surface, the confirmed no-op clear, and the
``character`` affected-panel declaration that refreshes the drawer. Ownership
is structural: the dispatcher resolves the adapter's actor from the session's
own puppet (webclient-action-dispatch), so no adapter-side identity check
exists to bypass.
"""

import unittest
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.character_actions import (
    AFFECTED_CHARACTER,
    NOT_EXPLORING_CODE,
    REJECTED_CODE,
    CharacterActionError,
    _character_persona_update_adapter,
    validate_character_persona_update_payload,
)
from web.webclient.actions.registry import build_production_action_registry
from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH


class PersonaUpdateValidatorTests(unittest.TestCase):
    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_accepts_every_field_with_bounded_text_or_null(self):
        for field in ("background", "personality", "life_story", "habit"):
            with self.subTest(field=field):
                self.assertEqual(
                    validate_character_persona_update_payload(
                        {"field": field, "text": " 精簡後的文字 "}
                    ),
                    {"field": field, "text": "精簡後的文字"},
                )
                self.assertEqual(
                    validate_character_persona_update_payload(
                        {"field": field, "text": None}
                    ),
                    {"field": field, "text": None},
                )
        boundary = "界" * MAX_PERSONA_FIELD_LENGTH
        self.assertEqual(
            validate_character_persona_update_payload(
                {"field": "habit", "text": boundary}
            )["text"],
            boundary,
        )

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_rejects_every_other_shape(self):
        for payload in (
            {},
            {"field": "identity", "text": "結構鍵"},
            {"field": "unknown", "text": "x"},
            {"field": "habit", "text": "x" * (MAX_PERSONA_FIELD_LENGTH + 1)},
            {"field": "habit", "text": "   "},
            {"field": "habit", "text": 42},
            {"field": "habit", "text": ""},
            {"field": "habit"},
            {"text": None},
            {"field": "habit", "text": None, "extra": 1},
            "not-a-dict",
            None,
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(CharacterActionError):
                    validate_character_persona_update_payload(payload)


class PersonaUpdateAdapterTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.character = create_object(
            PlayerCharacter, key="persona-editor", location=None
        )
        self.character.db.persona = {
            "identity": {},
            "personality": "",
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": "舊背景",
            "custom_key": "kept",
        }

    def _call(self, field, text):
        return _character_persona_update_adapter(
            self.character, {"field": field, "text": text}, None
        )

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_happy_path_writes_trimmed_text_and_refreshes_the_panel(self):
        result = self._call("life_story", " 來自邊境的小村，靠磨劍維生 ")
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "persona_updated")
        self.assertEqual(result["affected_panels"], AFFECTED_CHARACTER)
        self.assertIn("已設定生平", result["message"])
        stored = self.character.db.persona
        self.assertEqual(
            stored["life_story"], "來自邊境的小村，靠磨劍維生"
        )
        self.assertEqual(stored["background"], "舊背景")
        self.assertEqual(stored["custom_key"], "kept")

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_clearing_an_unset_field_is_a_confirmed_noop(self):
        stored = dict(self.character.db.persona)
        stored.pop("background")
        self.character.db.persona = stored
        result = self._call("background", None)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("已清除背景", result["message"])
        self.assertNotIn("background", self.character.db.persona)
        self.assertEqual(self.character.db.persona["custom_key"], "kept")

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_service_rejection_maps_to_the_stable_code_without_writing(self):
        before = dict(self.character.db.persona)
        # The validator is the whitelist gate; a direct adapter call with an
        # over-bound text (bypassing it) must still write nothing and answer
        # with the single stable rejection.
        result = self._call(
            "habit", "習" * (MAX_PERSONA_FIELD_LENGTH + 1)
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REJECTED_CODE)
        self.assertEqual(dict(self.character.db.persona), before)

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_creation_pending_actor_is_refused(self):
        self.character.creation_pending = True
        result = self._call("personality", "沉穩")
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], NOT_EXPLORING_CODE)
        self.assertEqual(self.character.db.persona["personality"], "")

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_in_combat_actor_is_refused(self):
        with mock.patch(
            "world.rules.combat_session.is_in_active_session",
            return_value=True,
        ):
            result = self._call("personality", "沉穩")
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], NOT_EXPLORING_CODE)
        self.assertEqual(self.character.db.persona["personality"], "")

    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_setting_without_a_record_creates_the_card(self):
        self.character.attributes.remove("persona")
        result = self._call("habit", "清晨練劍")
        self.assertEqual(result["outcome"], "success")
        stored = self.character.db.persona
        self.assertEqual(stored["habit"], "清晨練劍")
        self.assertEqual(stored["identity"], {})


class PersonaUpdateRegistryWiringTests(unittest.TestCase):
    @covers_requirement("persona-editing::the-character-persona-update-action-edits-one-persona-field")
    def test_production_registry_binds_the_exact_spec(self):
        registry = build_production_action_registry()
        spec, adapter = registry.validate_and_adapter("character.persona.update")
        self.assertIs(
            spec.validate_payload,
            validate_character_persona_update_payload,
        )
        self.assertIs(adapter, _character_persona_update_adapter)
        self.assertEqual(spec.affected_panels, ("character",))


if __name__ == "__main__":
    unittest.main()
