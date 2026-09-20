"""Action-registry allowlisting, duplicate safety, and production-registry surface tests."""
from web.webclient.actions.registry import (
    ActionRegistry,
    ActionSpec,
    build_production_action_registry,
)
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    new_presentation_epoch,
    validate_ui_action_result,
)
from tools.spec_traceability import covers_requirement
import unittest
from ._support import _proof_spec


class RegistryTests(unittest.TestCase):
    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_duplicate_registration_fails(self):
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        with self.assertRaises(ProtocolValidationError):
            registry.register(_proof_spec())

    def test_unknown_action_ids_not_exposed(self):
        registry = ActionRegistry("test")
        registry.register(_proof_spec())
        self.assertEqual(registry.action_ids, frozenset({"proof.noop"}))
        with self.assertRaises(KeyError):
            registry.spec("combat.cast")

    def test_validate_and_adapter_resolves_the_registered_spec(self):
        registry = ActionRegistry("test")
        spec = _proof_spec()
        registry.register(spec)
        resolved, adapter = registry.validate_and_adapter("proof.noop")
        self.assertIs(resolved, spec)
        self.assertEqual(
            adapter("actor", {}), spec.adapter("actor", {})
        )

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_production_registry_exposes_only_specified_adapters(self):
        registry = build_production_action_registry()
        self.assertEqual(
            registry.action_ids,
            frozenset(
                {
                    "account.character.create",
                    "account.character.switch",
                    "combat.cast",
                    "combat.flee",
                    "combat.forfeit",
                    "guild.register",
                    "guild.quest_accept",
                    "guild.quest_abandon",
                    "guild.quest_turnin",
                    "guild.quest_track",
                    "guild.exam_start",
                    "shop.buy",
                    "shop.sell",
                    "inventory.use",
                    "inventory.toggle_equip",
                    "creation.preset",
                    "creation.custom",
                    "creation.concept",
                    "creation.roll_name",
                    "creation.activate",
                    "creation.reset",
                    "explore.move",
                    "explore.look",
                    "explore.talk_scripted",
                    "explore.talk_freeform",
                    "explore.dialogue_leave",
                    "explore.party_invite",
                    "explore.party_leave",
                    "explore.engage",
                    "explore.wait",
                    "explore.practice",
                    "explore.possess",
                    "explore.possess_release",
                    "explore.deliver",
                    "options.dismiss",
                    "title.accept",
                    "title.decline",
                    "title.equip",
                    "title.remove",
                    "character.persona.update",
                    "gallery.subject.select",
                    "gallery.generate",
                    "gallery.default.set",
                    "gallery.card.delete",
                    "gallery.face_rect.update",
                    "gallery.binding.save",
                }
            ),
        )
        # Validation and dispatch infrastructure remains usable.
        self.assertTrue(hasattr(registry, "spec"))

if __name__ == "__main__":
    unittest.main()
