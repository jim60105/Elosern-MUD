"""Shared authored/generated dialogue resolution and effect authorization (4.1/4.2).

A generated role's current permitted phase answers through the same dialogue
seam as an authored table row: greeting, topic keywords, fixed responses, the
host gate and the offline response. A topic effect is executed only through the
deterministic authorization path, and a phase change hides the previous phase's
topics.
"""

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.compile.compiler import compile_blueprint_core
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.encounters import publish_scene_package
from world.quests.runtime import read_records
from world.quests.story_dialogue import transition_story_dialogue
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin, register_catalog_once
from world.quests.tests._scene_package_fixtures import (
    LONG_PROSE,
    dialogue as _dialogue,
    package as _package,
)
from world.rules.dialogue import (
    dialogue_offline_response,
    dialogue_topic_keywords,
    greeting_for,
    opens_dialogue,
    run_scripted_talk,
    table_response,
)
from world.rules.story_effects import apply_story_effect

COMMISSION_KEYWORD = "接受委託"
INFORMATION_KEYWORD = "線索"


class GeneratedDialogueResolutionTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="訪客")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.player.move_to(self.room, quiet=True)
        # The talk affinity writer reads the affinity rulebook, whose cap-break
        # rows reference registered catalog quests.
        register_catalog_once()
        payload = _package()
        self.definition_key = compile_blueprint_core(payload["quest"]).definition.key
        payload["dialogue"] = [
            self._with_topics("mother", commission=True),
            self._with_topics("daughter", commission=False),
        ]
        self.published = publish_scene_package(payload, owner="tester")
        activate_scene_encounter(
            self.player, self.published.package_id, "south_gate", room=self.room, tick=5
        )
        activate_scene_encounter(
            self.player, self.published.package_id, "market", room=self.room, tick=5
        )
        self.daughter = self._actor("daughter")
        self.mother = self._actor("mother")

    def _with_topics(self, role_id: str, *, commission: bool) -> dict:
        entry = _dialogue(role_id)
        searching = entry["phases"][0]
        topics = [{"keyword": INFORMATION_KEYWORD, "response": LONG_PROSE}]
        if commission:
            topics.append(
                {
                    "keyword": COMMISSION_KEYWORD,
                    "response": LONG_PROSE,
                    "effect_verb": "offer_commission",
                    "effect_reference": self.definition_key,
                }
            )
        searching["topics"] = topics
        return entry

    def _actor(self, role_id):
        binding = scene_store.get_role_binding(self.published.package_id, role_id)
        return ObjectDB.objects.filter(id=binding.npc_id).first()

    def test_generated_topics_and_greeting_resolve_through_the_shared_seam(self):
        from web.webclient.presentation.affordances import (
            _scripted_keyword_descriptors,
        )

        self.assertTrue(opens_dialogue(self.mother))
        self.assertEqual(
            dialogue_topic_keywords(self.mother),
            (INFORMATION_KEYWORD, COMMISSION_KEYWORD),
        )
        # The actual presentation consumer (the version-2 panel's descriptor
        # source) reads the same generated topics in the same order.
        self.assertEqual(
            [row["keyword_id"] for row in _scripted_keyword_descriptors(self.mother)],
            [INFORMATION_KEYWORD, COMMISSION_KEYWORD],
        )
        self.assertEqual(greeting_for(self.mother), f"{LONG_PROSE}searching")
        self.assertEqual(
            table_response(
                f"scene_role:{self.published.package_id}:mother", INFORMATION_KEYWORD
            ),
            LONG_PROSE,
        )
        self.assertEqual(dialogue_offline_response(self.mother), LONG_PROSE)

    def test_an_informational_topic_is_read_only(self):
        result = run_scripted_talk(self.mother, self.player, INFORMATION_KEYWORD)
        self.assertEqual(result.response, LONG_PROSE)
        self.assertEqual(read_records(self.player), [])

    def test_an_authorized_commission_topic_accepts_the_commission(self):
        outcome = apply_story_effect(
            self.mother,
            self.player,
            keyword=COMMISSION_KEYWORD,
            verb="offer_commission",
            reference=self.definition_key,
        )
        self.assertTrue(outcome.applied, outcome.reason)
        records = read_records(self.player)
        self.assertEqual([record.definition_key for record in records], [self.definition_key])
        self.assertEqual(records[0].issuer_key, "npc:story_mother")

    def test_a_non_issuer_role_cannot_offer_the_commission(self):
        outcome = apply_story_effect(
            self.daughter,
            self.player,
            keyword=COMMISSION_KEYWORD,
            verb="offer_commission",
            reference=self.definition_key,
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "stale_phase")
        self.assertEqual(read_records(self.player), [])

    def test_an_out_of_scope_effect_reference_is_refused(self):
        outcome = apply_story_effect(
            self.mother,
            self.player,
            keyword=COMMISSION_KEYWORD,
            verb="offer_commission",
            reference="npc:other_commission",
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "out_of_scope")
        self.assertEqual(read_records(self.player), [])

    def test_a_keyword_outside_the_current_phase_is_refused_as_stale(self):
        outcome = apply_story_effect(
            self.mother,
            self.player,
            keyword="近況",
            verb="offer_commission",
            reference=self.definition_key,
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "stale_phase")

    def test_an_absent_actor_is_refused(self):
        elsewhere = create_object(AnchorRoom, key="別處")
        self.player.move_to(elsewhere, quiet=True)
        outcome = apply_story_effect(
            self.mother,
            self.player,
            keyword=COMMISSION_KEYWORD,
            verb="offer_commission",
            reference=self.definition_key,
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "absent")

    def test_a_phase_change_hides_the_previous_topics(self):
        transition_story_dialogue(
            self.published.package_id,
            "mother",
            expected_revision=0,
            provenance={"closure": True},
            tick=8,
        )
        keywords = dialogue_topic_keywords(self.mother)
        self.assertNotIn(COMMISSION_KEYWORD, keywords)
        self.assertEqual(keywords, ("近況",))
        self.assertEqual(greeting_for(self.mother), f"{LONG_PROSE}everyday")