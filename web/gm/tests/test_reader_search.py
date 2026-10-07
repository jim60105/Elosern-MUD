"""Fixed-fixture reader tests: global runtime search (task 2.5 / 6.1).

Establishes the delta requirement "Runtime navigation search and cross-links":
an exact ``#dbref`` resolves straight to that object whatever its kind, other
text matches object keys, then quest ids, then narrative source ids in that
precedence, and a non-curated object's result still carries the link descriptor
the navigation needs. The ``gm-runtime-state::*`` requirement IDs this module
covers enter the traceability index when the change's delta spec is synced at
archive.
"""

from __future__ import annotations

from evennia.objects.objects import DefaultObject
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.narrative.models import MemoryRecord, NarrativeEvent
from world.quests.tests._fixtures import stage_active_record

from web.gm.readers import search
from web.gm.tests._state_support import open_synthetic_scope

QUEST_KEY = "t_tarn_messenger"
MARKER = "t_reader_search_marker"
SOURCE = "t_reader_search_source"


class SearchReaderTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        open_synthetic_scope(self, "quest_definitions", "quest_issuances", "items")
        super().setUp()
        self.plain = create.create_object(DefaultObject, key=MARKER, location=self.room1)
        self.owner = create.create_object(PlayerCharacter, key="t_reader_search_owner")
        self.record = stage_active_record(self.owner, QUEST_KEY)
        self.event = NarrativeEvent.objects.create(
            source_id=SOURCE, event_type="t_reader_event", content={"note": "合成事件"}
        )
        self.memory = MemoryRecord.objects.create(
            owner_id=str(self.owner.pk), source_id=SOURCE, content={"note": "合成記憶"}
        )

    def test_an_exact_dbref_resolves_to_its_object_whatever_its_kind(self):
        payload = search.search(f"#{self.plain.pk}")
        self.assertEqual(payload["query"], f"#{self.plain.pk}")
        self.assertEqual(len(payload["results"]), 1)
        result = payload["results"][0]
        self.assertEqual(result["matched"], "dbref")
        self.assertEqual(result["kind"], "object")
        self.assertEqual(result["id"], str(self.plain.pk))
        self.assertEqual(result["link"], {"kind": "object", "id": str(self.plain.pk), "label": MARKER})

    def test_a_dbref_and_its_bare_form_resolve_identically(self):
        self.assertEqual(
            search.search(str(self.plain.pk))["results"],
            search.search(f"#{self.plain.pk}")["results"],
        )

    def test_an_unknown_dbref_falls_through_to_the_text_tiers(self):
        self.assertEqual(search.search("#999999")["results"], [])

    def test_object_keys_match_by_exact_then_containing_text(self):
        results = search.search(MARKER)["results"]
        self.assertEqual([result["matched"] for result in results], ["object_key"])
        self.assertEqual(results[0]["id"], str(self.plain.pk))
        containing = search.search("search_mark")["results"]
        self.assertIn(str(self.plain.pk), [result["id"] for result in containing])

    def test_quest_ids_and_narrative_sources_are_matched_after_object_keys(self):
        by_quest = search.search(self.record.quest_id)["results"]
        self.assertEqual([result["matched"] for result in by_quest], ["quest_id"])
        self.assertEqual(by_quest[0]["kind"], "quests")
        self.assertEqual(by_quest[0]["link"]["owner"], self.owner.pk)
        by_source = search.search(SOURCE)["results"]
        matched = [result["matched"] for result in by_source]
        self.assertEqual(set(matched), {"source_id"})
        kinds = {result["kind"] for result in by_source}
        self.assertEqual(kinds, {"narrative", "memories"})

    def test_results_keep_the_documented_tier_precedence(self):
        # One object key and two source ids share the marker text, so both
        # contributing tiers appear and their order is the contract.
        create.create_object(DefaultObject, key=SOURCE, location=self.room1)
        results = search.search(SOURCE)["results"]
        tiers = [result["matched"] for result in results]
        self.assertEqual(tiers, ["object_key", "source_id", "source_id"])
        kinds = {result["kind"] for result in results}
        self.assertEqual(kinds, {"object", "narrative", "memories"})

    def test_an_empty_query_is_an_invalid_query(self):
        for value in ("", "   ", None):
            with self.subTest(query=value), self.assertRaises(Exception) as raised:
                search.search(value)
            self.assertEqual(raised.exception.code, "invalid_query")

    def test_a_result_carries_a_link_descriptor_the_navigation_can_follow(self):
        for result in search.search(SOURCE)["results"]:
            with self.subTest(result=result):
                self.assertEqual(set(result["link"]) & {"kind", "id"}, {"kind", "id"})
