"""The default action cards for the exploration surface."""
from typeclasses.npcs import LLMNPC, NPC
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_CARDS,
    SUGGESTIBLE_ACTION_IDS,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    suggestible_candidates,
)
from typeclasses.rooms import Room
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.tests.synthetic_data import synthetic_registries
import unittest
from ._support import (
    T_DIALOGUE_KEY,
    VocabularyTestCase,
    _T_KEYWORDS,
    _monster,
    _player,
)


@synthetic_registries("dialogue")
class DefaultCardsTests(VocabularyTestCase):
    def setUp(self):
        self.room = create_object(Room, key="卡片房")
        self.player = _player()
        self.player.location = self.room

    def _vocabulary(self):
        return exploration_affordances(self.player)

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_cards_are_a_strict_subset_of_the_vocabulary(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        monster = _monster()
        monster.location = self.room
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        self.assertGreaterEqual(len(cards), 1)
        self.assertLessEqual(len(cards), MAX_CARDS)
        union = {
            (entry.action_id, repr(entry.params), entry.label)
            for entry in vocabulary
            if not entry.navigation
        }
        for card in cards:
            self.assertIn((card.action_id, repr(card.params), card.label), union)
            self.assertTrue(card.enabled)
            self.assertIn(card.action_id, SUGGESTIBLE_ACTION_IDS)

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_objective_relevant_actions_rank_first(self):
        host = create_object(NPC, key="目標NPC", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        destination = create_object(Room, key="東邊", location=None)
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room,
            destination=destination,
        )
        vocabulary = self._vocabulary()
        cards = default_cards(
            vocabulary, objective_npc_ids=frozenset({int(host.pk)}), actor=self.player
        )
        first = cards[0]
        self.assertEqual(first.action_id, "explore.talk_scripted")
        self.assertEqual(first.params["npc_id"], int(host.pk))
        self.assertEqual(
            [entry.action_id for entry in cards[: len(_T_KEYWORDS)]],
            ["explore.talk_scripted"] * len(_T_KEYWORDS),
        )
        # Every objective-relevant talk entry precedes any move or baseline.
        talk_flags = [entry.action_id == "explore.talk_scripted" for entry in cards]
        self.assertEqual(
            talk_flags,
            [True] * len(_T_KEYWORDS) + [False] * (len(cards) - len(_T_KEYWORDS)),
        )

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_talk_and_engage_precede_the_baseline_within_the_cap(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        monster = _monster()
        monster.location = self.room
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        # The living monster makes the room unsafe, so wait is absent; the
        # talk and engage entries still precede the room-look baseline.
        self.assertEqual(
            [entry.action_id for entry in cards],
            ["explore.talk_freeform", "explore.engage", "explore.look"],
        )
        self.assertLessEqual(len(cards), MAX_CARDS)

    def test_cards_preserve_vocabulary_order_within_a_rank(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        keyword_ids = [
            entry.params["keyword_id"]
            for entry in cards
            if entry.action_id == "explore.talk_scripted"
        ]
        self.assertEqual(keyword_ids, _T_KEYWORDS)

    def test_default_cards_are_pure(self):
        vocabulary = self._vocabulary()
        before = [entry.as_dict() for entry in vocabulary]
        default_cards(vocabulary, actor=self.player)
        after = [entry.as_dict() for entry in self._vocabulary()]
        self.assertEqual(before, after)

    def test_cap_is_respected_even_with_many_objectives(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        vocabulary = self._vocabulary()
        cards = default_cards(
            vocabulary, objective_npc_ids=frozenset({int(host.pk)}), actor=self.player
        )
        self.assertLessEqual(len(cards), MAX_CARDS)

if __name__ == "__main__":
    unittest.main()
