"""Representative runtime smoke through the real scene-package path (5.1).

One test runs the whole changed path end to end rather than asserting units in
isolation: publish a package, activate an encounter in a real room (building a
generated actor with its persona, dialogue capability and initial phase), reuse
that exact actor on re-entry, provision the role-issued commission, accept it
through the real dialogue consumer, commit a phase transition that changes the
live conversation window, and reload the committed package through startup
restore.
"""

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.bootstrap import restore_scene_packages
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.encounters import publish_scene_package
from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY
from world.quests.runtime import read_records
from world.quests.scene_package import validate_scene_package
from world.quests.story_dialogue import transition_story_dialogue
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin, register_catalog_once
from world.quests.tests._scene_package_fixtures import (
    LONG_PROSE,
    dialogue as _dialogue,
    package as _package,
)
from world.rules.dialogue import (
    dialogue_topic_keywords,
    greeting_for,
    live_dialogue_session,
    open_or_refresh_dialogue,
    run_scripted_talk,
)

COMMISSION_KEYWORD = "接受委託"


class ScenePackageRuntimeSmokeTests(RegistryIsolationMixin, EvenniaTest):
    def test_the_whole_package_to_conversation_path_runs_without_a_model(self):
        register_catalog_once()
        player = create_object(PlayerCharacter, key="旅人")
        room = create_object(AnchorRoom, key="南門")
        room.db.anchor_key = _anchor_key()
        player.move_to(room, quiet=True)

        # 1. Publish: validated, immutable, and no actor, acceptance or authority.
        payload = _package()
        payload["dialogue"] = [
            self._dialogue_with_commission(_dialogue("mother")),
            _dialogue("daughter"),
        ]
        from world.quests.compile.compiler import compile_blueprint_core

        definition_key = compile_blueprint_core(payload["quest"]).definition.key
        payload["dialogue"][0]["phases"][0]["topics"][-1]["effect_reference"] = (
            definition_key
        )
        published = publish_scene_package(payload, owner="tester", tick=4)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})
        self.assertEqual(read_records(player), [])

        # 2. Activate the encounter: one generated actor with its persona and phase.
        activation = activate_scene_encounter(
            player, published.package_id, "south_gate", room=room, tick=5
        )
        self.assertTrue(activation.activated)
        daughter = ObjectDB.objects.filter(id=activation.role_bindings["daughter"]).first()
        self.assertEqual(daughter.location.pk, room.pk)
        from world.rules.npc_persona import read_npc_persona

        self.assertIsNotNone(read_npc_persona(daughter))
        self.assertEqual(
            scene_store.get_dialogue_phase(published.package_id, "daughter").selected_phase,
            "searching",
        )
        self.assertEqual(read_records(player), [])
        self.assertEqual(room.db.desc, None)

        # 3. Re-entry reuses the exact committed actor.
        repeat = activate_scene_encounter(
            player, published.package_id, "south_gate", room=room, tick=6
        )
        self.assertFalse(repeat.created)
        self.assertEqual(repeat.role_bindings, activation.role_bindings)

        # 4. Provision the role-issued commission by activating its encounter.
        activate_scene_encounter(
            player, published.package_id, "market", room=room, tick=7
        )
        mother = ObjectDB.objects.filter(
            id=scene_store.get_role_binding(published.package_id, "mother").npc_id
        ).first()
        self.assertTrue(
            any(
                grant.registered
                for grant in scene_store.list_commission_grants(published.package_id)
            )
        )

        # 5. The conversation window shows the current phase and the commission topic.
        open_or_refresh_dialogue(player, mother, greeting_for(mother))
        self.assertEqual(
            dialogue_topic_keywords(mother), ("線索", COMMISSION_KEYWORD)
        )
        self.assertIsNotNone(live_dialogue_session(player))

        # 6. Accept the commission through the real consumer (offline, no model).
        run_scripted_talk(mother, player, COMMISSION_KEYWORD)
        records = read_records(player)
        self.assertEqual([record.definition_key for record in records], [definition_key])

        # 7. Commit a closure transition: the live window refreshes to everyday topics.
        with self.captureOnCommitCallbacks(execute=True):
            transition = transition_story_dialogue(
                published.package_id,
                "mother",
                expected_revision=0,
                provenance={"closure": True},
                participants=(player,),
                tick=8,
            )
        self.assertEqual(transition.phase_id, "everyday")
        session = live_dialogue_session(player)
        self.assertEqual(session.line, greeting_for(mother))
        self.assertEqual(dialogue_topic_keywords(mother), ("近況",))

        # 8. Committed reload: the package and its bindings survive a restart.
        from world.quests.compile import SCENE_REQUIREMENT_REGISTRY
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.clear()
        restore_scene_packages()
        self.assertIn(definition_key, QUEST_DEFINITION_REGISTRY)
        row = scene_store.read_package(published.package_id)
        self.assertEqual(
            validate_scene_package(row.payload).package_id, published.package_id
        )
        self.assertEqual(
            scene_store.get_role_binding(published.package_id, "daughter").npc_id,
            activation.role_bindings["daughter"],
        )
        self.assertEqual(
            scene_store.get_dialogue_phase(published.package_id, "mother").revision, 1
        )
        self.assertEqual([record.definition_key for record in read_records(player)], [definition_key])

    def _dialogue_with_commission(self, entry: dict) -> dict:
        entry["phases"][0]["topics"] = [
            {"keyword": "線索", "response": LONG_PROSE},
            {
                "keyword": COMMISSION_KEYWORD,
                "response": LONG_PROSE,
                "effect_verb": "offer_commission",
                "effect_reference": "placeholder",
            },
        ]
        return entry