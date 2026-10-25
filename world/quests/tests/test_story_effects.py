"""Generated scene resolution and deterministic effect authorization (4.1/4.2).

A generated role's current permitted phase answers through the same source and
selection seam as an authored scene: complete actor-first topics, the shared
availability projection, the host gate, the greeting and the offline response.
An effect is declared beside the immutable package and executed only through
the deterministic authorization path; a phase change retires the previous
phase's topics, and a refused effect ships only the authored safe refusal.
"""

from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
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
    topic as _topic,
    topic_scene as _topic_scene,
)
from world.rules.dialogue import (
    dialogue_offline_response,
    greeting_for,
    live_dialogue_session,
    opens_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_sources import dialogue_source_for_host
from world.rules.story_effects import apply_story_effect, effect_for_topic

COMMISSION_KEYWORD = "接受委託"
INFORMATION_KEYWORD = "線索"
REFUSAL_TEXT = "她把手收回袖口，輕輕搖頭，沒有再多說。"


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
        topics = [_topic("information", INFORMATION_KEYWORD, LONG_PROSE)]
        if commission:
            topics.append(
                _topic(
                    "offer",
                    COMMISSION_KEYWORD,
                    LONG_PROSE,
                    requires={
                        "kind": "quest_is",
                        "definition_key": self.definition_key,
                        "state": "not_accepted",
                    },
                    refusal=_topic_scene(
                        "offer_refusal",
                        REFUSAL_TEXT,
                        actor_line="她抬起眼，等你把話說完。",
                    ),
                )
            )
            searching["topic_effects"] = [
                {
                    "topic_id": "offer",
                    "verb": "offer_commission",
                    "reference": self.definition_key,
                }
            ]
        searching["topics"] = topics
        return entry

    def _actor(self, role_id):
        binding = scene_store.get_role_binding(self.published.package_id, role_id)
        return ObjectDB.objects.filter(id=binding.npc_id).first()

    def _topic_id(self, host, keyword: str) -> str:
        source = dialogue_source_for_host(host)
        return next(
            topic.topic_id for topic in source.dialogue.topics if topic.keyword == keyword
        )

    def _select(
        self,
        host,
        keyword: str,
        selection_id: str = "sel-1",
        expected_context_id: str | None = None,
    ):
        return select_authored_topic(
            self.player,
            host,
            self._topic_id(host, keyword),
            selection_id=selection_id,
            expected_context_id=expected_context_id,
        )

    def test_generated_topics_and_greeting_resolve_through_the_shared_seam(self):
        from web.webclient.presentation.affordances import (
            _scripted_keyword_descriptors,
        )

        self.assertTrue(opens_dialogue(self.mother))
        source = dialogue_source_for_host(self.mother)
        self.assertEqual(
            [topic.keyword for topic in source.dialogue.topics],
            [INFORMATION_KEYWORD, COMMISSION_KEYWORD],
        )
        self.assertTrue(all(topic.topic_id.startswith("g:") for topic in source.dialogue.topics))
        # The actual presentation consumer (the version-3 panel descriptor
        # source) reads the same generated topics in the same order.
        self.assertEqual(
            [
                row["keyword_id"]
                for row in _scripted_keyword_descriptors(self.mother, actor=self.player)
            ],
            [INFORMATION_KEYWORD, COMMISSION_KEYWORD],
        )
        self.assertEqual(
            greeting_for(self.mother), f"{LONG_PROSE}searching"
        )
        self.assertEqual(dialogue_offline_response(self.mother), LONG_PROSE)

    def test_an_informational_selection_delivers_the_complete_scene(self):
        delivery = self._select(self.mother, INFORMATION_KEYWORD)
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(len(delivery.lines), 2)
        self.assertEqual(delivery.lines[0].speaker, "actor")
        self.assertEqual(read_records(self.player), [])
        self.assertEqual(self.mother.relations.affinity_for(self.player), 1)

    def test_an_authorized_commission_topic_accepts_the_commission(self):
        delivery = self._select(self.mother, COMMISSION_KEYWORD)
        self.assertEqual(delivery.kind, "formal")
        records = read_records(self.player)
        self.assertEqual(
            [record.definition_key for record in records], [self.definition_key]
        )
        self.assertEqual(records[0].issuer_key, "npc:story_mother")
        # An effect-bearing interaction never adds talk affinity.
        self.assertEqual(self.mother.relations.affinity_for(self.player), 0)

    def test_effect_for_topic_names_the_declared_association(self):
        declared = effect_for_topic(
            self.mother, self._topic_id(self.mother, COMMISSION_KEYWORD)
        )
        self.assertIsNotNone(declared)
        self.assertEqual(declared.verb, "offer_commission")
        self.assertEqual(declared.reference, self.definition_key)
        self.assertIsNone(effect_for_topic(self.mother, "g:not-a-real-topic"))

    def test_a_stale_phase_revision_refuses_the_effect(self):
        outcome = apply_story_effect(
            self.mother,
            self.player,
            topic_id=self._topic_id(self.mother, COMMISSION_KEYWORD),
            expected_phase_revision=99,
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "stale_phase")
        self.assertEqual(read_records(self.player), [])

    def test_an_unknown_topic_is_a_named_refusal(self):
        outcome = apply_story_effect(
            self.mother,
            self.player,
            topic_id=self._topic_id(self.mother, INFORMATION_KEYWORD),
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "stale_phase")
        self.assertEqual(read_records(self.player), [])

    def test_an_absent_actor_is_refused(self):
        elsewhere = create_object(AnchorRoom, key="別處")
        self.player.move_to(elsewhere, quiet=True)
        outcome = apply_story_effect(
            self.mother,
            self.player,
            topic_id=self._topic_id(self.mother, COMMISSION_KEYWORD),
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "absent")
        self.assertEqual(read_records(self.player), [])

    def test_a_domain_refusal_delivers_only_the_safe_refusal(self):
        topic_id = self._topic_id(self.mother, COMMISSION_KEYWORD)
        with patch(
            "world.rules.quest_issuance.resolve_issuance", return_value=None
        ):
            delivery = self._select(self.mother, COMMISSION_KEYWORD)
        self.assertEqual(delivery.kind, "refusal")
        self.assertEqual(delivery.topic_id, topic_id)
        self.assertTrue(delivery.scene_id.startswith("g:"))
        self.assertNotIn(LONG_PROSE, [line.text for line in delivery.lines])
        self.assertIn(REFUSAL_TEXT, [line.text for line in delivery.lines])
        self.assertEqual(read_records(self.player), [])
        self.assertEqual(self.mother.relations.affinity_for(self.player), 0)
        session = live_dialogue_session(self.player)
        self.assertEqual(session.completion_receipts, ())

    def test_a_replayed_selection_applies_the_effect_at_most_once(self):
        first = self._select(self.mother, COMMISSION_KEYWORD)
        session = live_dialogue_session(self.player)
        replay = self._select(
            self.mother,
            COMMISSION_KEYWORD,
            expected_context_id=session.context_id,
        )
        self.assertEqual(first.delivery_id, replay.delivery_id)
        self.assertEqual(len(read_records(self.player)), 1)

    def test_a_failed_session_publication_rolls_back_the_accepted_commission(self):
        from unittest.mock import patch as patch_fn

        with patch_fn(
            "world.rules.dialogue.open_or_refresh_dialogue",
            side_effect=RuntimeError("session failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._select(self.mother, COMMISSION_KEYWORD)
        self.assertEqual(read_records(self.player), [])

    @covers_requirement(
        "story-phase-dialogue::phase-revision-invalidates-pending-dialogue-work"
    )
    def test_a_phase_change_retires_the_previous_topics(self):
        transition_story_dialogue(
            self.published.package_id,
            "mother",
            expected_revision=0,
            provenance={"closure": True},
            tick=8,
        )
        source = dialogue_source_for_host(self.mother)
        self.assertEqual(
            [topic.keyword for topic in source.dialogue.topics], ["近況"]
        )
        self.assertEqual(greeting_for(self.mother), f"{LONG_PROSE}everyday")
        self.assertEqual(source.effects, {})
