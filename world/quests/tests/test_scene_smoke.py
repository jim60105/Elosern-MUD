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
    topic as _topic,
    topic_scene as _topic_scene,
)
from world.rules.dialogue import (
    greeting_for,
    live_dialogue_session,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_sources import dialogue_source_for_host
from world.quests.scene_builder import materialize_stage
from world.quests.tests._scene_package_fixtures import role as _role

COMMISSION_KEYWORD = "接受委託"


def _npc_req(role_id: str) -> dict:
    """One permanent-destination occupant entry carrying the authored identity."""
    entry = _role(role_id)
    request = {"role": role_id, "tier": entry["tier"], "disposition": None}
    request.update(entry["characterization"])
    return request


class ScenePackageRuntimeSmokeTests(RegistryIsolationMixin, EvenniaTest):
    def test_the_whole_package_to_conversation_path_runs_without_a_model(self):
        register_catalog_once()
        player = create_object(PlayerCharacter, key="旅人")
        room = create_object(AnchorRoom, key="南門")
        room.db.anchor_key = _anchor_key()
        player.move_to(room, quiet=True)

        # 1. Publish: validated, immutable, and no actor, acceptance or authority.
        payload = _package()
        # The accepted stage also requires the role at a permanent destination:
        # the package owns it, so the stage adopts the exact binding instead of
        # rejecting the occupant.
        payload["quest"]["stages"][0]["npc_req"] = [_npc_req("mother")]
        payload["dialogue"] = [
            self._dialogue_with_commission(_dialogue("mother")),
            _dialogue("daughter"),
        ]
        from world.quests.compile.compiler import compile_blueprint_core

        # The package's own validated role set is what makes its permanent
        # occupant legal, exactly as the package validator will pass it.
        definition_key = compile_blueprint_core(
            payload["quest"], package_roles=frozenset({"mother", "daughter"})
        ).definition.key
        commission_phase = payload["dialogue"][0]["phases"][0]
        commission_phase["topics"][-1]["requires"]["definition_key"] = definition_key
        commission_phase["topic_effects"][0]["reference"] = definition_key
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
        market = activate_scene_encounter(
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
        source = dialogue_source_for_host(mother)
        self.assertEqual(
            [topic.keyword for topic in source.dialogue.topics],
            ["線索", COMMISSION_KEYWORD],
        )
        self.assertIsNotNone(live_dialogue_session(player))

        # 6. Accept the commission through the real consumer (offline, no model).
        commission_topic = next(
            topic.topic_id
            for topic in source.dialogue.topics
            if topic.keyword == COMMISSION_KEYWORD
        )
        select_authored_topic(
            player,
            mother,
            commission_topic,
            selection_id="smoke-commission",
            expected_context_id=live_dialogue_session(player).context_id,
        )
        records = read_records(player)
        self.assertEqual([record.definition_key for record in records], [definition_key])

        # 6b. The accepted permanent stage adopts the same exact actor in the
        # existing room without rewriting its description or gaining a binding.
        staged = materialize_stage(player, records[0].quest_id)
        self.assertEqual(staged.room.pk, room.pk)
        self.assertEqual(staged.room.db.desc, None)
        self.assertEqual(
            scene_store.get_role_binding(published.package_id, "mother").npc_id,
            market.role_bindings["mother"],
        )
        self.assertIsNone(
            next(
                record
                for record in read_records(player)
                if record.quest_id == records[0].quest_id
            ).stage_room_id
        )

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
        self.assertEqual(
            [topic.keyword for topic in dialogue_source_for_host(mother).dialogue.topics],
            ["近況"],
        )

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
            _topic("information", "線索", LONG_PROSE),
            _topic(
                "offer",
                COMMISSION_KEYWORD,
                LONG_PROSE,
                requires={
                    "kind": "quest_is",
                    "definition_key": "placeholder",
                    "state": "not_accepted",
                },
                refusal=_topic_scene(
                    "offer_refusal",
                    "她沒有接下這個請求。",
                    actor_line="你把話說完，等她回應。",
                ),
            ),
        ]
        entry["phases"][0]["topic_effects"] = [
            {
                "topic_id": "offer",
                "verb": "offer_commission",
                "reference": "placeholder",
            }
        ]
        return entry