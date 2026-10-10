"""Data-contract test: registry-derived NPC host characterization and authored dialogue coverage contract
Every NPC source the live registries derive is characterized: each hosted place
resolves to its own registered profile by service identity with a valid compact
card, a bounded age pair and a misunderstanding-only voice, each dialogue table
belongs to exactly one profiled host and carries its own in-character greeting
and keyword responses, and qualified persistent people resolve their own cards
and offline voices. The checks iterate the derived sources, never an owner
slice: a host, person or table added outside the historical content slices is
covered with no new district-specific test. Prose is neither pinned nor compared
across sources -- coverage is the claim here, editorial review is the ledger's.
"""

from __future__ import annotations

import json
import re
import unittest

from tools.spec_traceability import covers_requirement
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse
from world.lore.guild import validate_guild_npc_identities
from world.lore.guild_adventurers import ADVENTURER_REGISTRY, EXAM_QUALIFICATIONS
from world.lore.npc_card import NpcCard
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.rules.npc_roster_validation import derive_shipped_sources

# A line in a host's own world never names a command, a mechanic or an
# interface element: the shipped command surface, mechanics vocabulary and
# panel tokens are all ASCII, so any run of two or more Latin letters in an
# authored greeting, keyword response or voice line names one of them.
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z]{2,}")
_HOST = "npc-profile-registry"
_CHARACTERIZATION = f"{_HOST}::every-registry-derived-host-has-complete-individual-characterization"
_DIALOGUE = f"{_HOST}::authored-host-dialogue-preserves-service-semantics"


def _hosted_places() -> list:
    """Every shipped place that declares a service host, in registry order."""
    return [place for place in PLACE_REGISTRY.values() if place.service_id is not None]


def _dialogue_key(place) -> str | None:
    return dict(place.authored_kwargs).get("dialogue_key")


def _characterization_problem(text: str, origin: str) -> str | None:
    """The reason a spoken line is not in character, or None when it is."""
    if "`" in text:
        return f"{origin} quotes a command token"
    if _ASCII_TOKEN_RE.search(text):
        return f"{origin} names a Latin-token surface"
    return None


def _table_problems(definition: DialogueDefinition, origin: str) -> list[str]:
    """The per-table dialogue rule: one table, one host, its own keywords.

    The rule is deliberately table-local. Two hosts may legitimately expose the
    same keyword vocabulary, so no assertion here compares one table's keyword
    set with another's; the requirement is per-table uniqueness only.
    """
    problems: list[str] = []
    if not definition.greeting or not definition.greeting.strip():
        problems.append(f"{origin} authors no greeting")
    else:
        problem = _characterization_problem(definition.greeting, f"{origin} greeting")
        if problem:
            problems.append(problem)
    keywords = [response.keyword for response in definition.responses]
    if len(keywords) != len(set(keywords)):
        problems.append(f"{origin} repeats a keyword label")
    for response in definition.responses:
        if not response.response or not response.response.strip():
            problems.append(f"{origin} has an empty {response.keyword} response")
            continue
        problem = _characterization_problem(
            response.response, f"{origin} response {response.keyword}"
        )
        if problem:
            problems.append(problem)
    return problems


class NpcHostCharacterizationContractTests(unittest.TestCase):
    """Every source the live registries derive carries its own characterization."""

    maxDiff = None

    @covers_requirement(_CHARACTERIZATION)
    def test_every_registry_derived_host_has_complete_individual_characterization(self):
        hosts = _hosted_places()
        self.assertTrue(hosts, "the place registry declares no hosted place")
        for place in hosts:
            with self.subTest(host=place.service_id):
                # The profile reference travels through the place record and is
                # the host's service identity -- never a display name, never a
                # borrowed key.
                self.assertEqual(place.host_profile_key, place.service_id)
                self.assertIn(place.service_id, NPC_PROFILE_REGISTRY)
                profile = NPC_PROFILE_REGISTRY[place.service_id]
                self.assertEqual(profile.key, place.service_id)
                NpcCard.from_record(profile.card.to_record())
                self.assertIs(type(profile.age), int)
                self.assertIsNot(profile.age, True)
                self.assertIs(type(profile.apparent_age), int)
                self.assertIsNot(profile.apparent_age, True)
                self.assertTrue(0 <= profile.age <= 10000)
                self.assertTrue(0 <= profile.apparent_age <= 10000)

    @covers_requirement(_CHARACTERIZATION)
    def test_every_scripted_host_uses_its_table_as_the_sole_greeting_source(self):
        for place in _hosted_places():
            with self.subTest(host=place.service_id):
                profile = NPC_PROFILE_REGISTRY[place.host_profile_key]
                # The table authors the greeting; only the misunderstanding
                # reply belongs to the profile.
                self.assertIsNone(profile.voice.greeting)
                self.assertTrue(profile.voice.misunderstood)
                problem = _characterization_problem(
                    profile.voice.misunderstood,
                    f"profile {profile.key} misunderstanding",
                )
                self.assertIsNone(problem)

    @covers_requirement(_CHARACTERIZATION)
    def test_every_dialogue_table_belongs_to_exactly_one_profiled_host(self):
        table_hosts: dict[str, list] = {key: [] for key in DIALOGUE_ROWS}
        for place in _hosted_places():
            key = _dialogue_key(place)
            self.assertIn(key, table_hosts, f"{place.service_id} references {key!r}")
            table_hosts[key].append(place)
        for table_key, hosts in table_hosts.items():
            with self.subTest(table=table_key):
                self.assertEqual(
                    len(hosts),
                    1,
                    f"table {table_key!r} must be answered by exactly one profiled host, "
                    f"got {[h.service_id for h in hosts]}",
                )
                self.assertIn(hosts[0].host_profile_key, NPC_PROFILE_REGISTRY)

    @covers_requirement(_CHARACTERIZATION)
    def test_qualified_people_resolve_their_own_cards_and_offline_voices(self):
        people = tuple(ADVENTURER_REGISTRY.values())
        self.assertTrue(people, "the adventurer registry ships no person")
        profile_keys = [person.profile_key for person in people]
        self.assertEqual(len(profile_keys), len(set(profile_keys)))
        for person in people:
            with self.subTest(person=person.key):
                profile = NPC_PROFILE_REGISTRY[person.profile_key]
                NpcCard.from_record(profile.card.to_record())
                self.assertIs(type(profile.age), int)
                self.assertIs(type(profile.apparent_age), int)
                self.assertTrue(0 <= profile.age <= 10000)
                self.assertTrue(0 <= profile.apparent_age <= 10000)
                for field in ("greeting", "misunderstood"):
                    line = getattr(profile.voice, field)
                    self.assertTrue(line, f"{person.key} has no {field}")
                    problem = _characterization_problem(line, f"{person.key} {field}")
                    self.assertIsNone(problem)
        # Examination authority selects an authored person, never a factory.
        self.assertLessEqual(
            {row.person_key for row in EXAM_QUALIFICATIONS}, set(ADVENTURER_REGISTRY)
        )
        validate_guild_npc_identities()

    @covers_requirement(_CHARACTERIZATION)
    def test_every_other_source_kind_carries_its_characterization_input(self):
        sources = derive_shipped_sources(quest_templates=QUEST_TEMPLATE_POOL)
        kinds = {kind for kind, _ in sources}
        self.assertEqual(
            kinds,
            {
                "place_host",
                "dialogue_table",
                "persistent_adventurer",
                "starting_companion",
                "quest_template_occupant",
                "import_example",
            },
        )
        for kind, key in sorted(sources):
            if kind == "starting_companion":
                with self.subTest(source=key):
                    declarer, partner_key = key.split(":", 1)
                    partner = PLAYER_PRESET_REGISTRY[partner_key]
                    self.assertIn(declarer, PLAYER_PRESET_REGISTRY)
                    self.assertTrue(partner.persona.speech_style.strip())
                    self.assertTrue(partner.persona.greeting.strip())
            elif kind == "quest_template_occupant":
                with self.subTest(source=key):
                    name, stage_index, position = key.rsplit(":", 2)
                    template = next(t for t in QUEST_TEMPLATE_POOL if t.name == name)
                    requirement = template.stages[int(stage_index)].npc_reqs[int(position)]
                    self.assertIsNotNone(requirement.persona)
                    NpcCard.from_record(requirement.persona.to_record())
            elif kind == "import_example":
                with self.subTest(source=key):
                    path = _example_path(key)
                    record = json.loads(path.read_text(encoding="utf-8"))
                    persona = record["persona"]
                    self.assertIsInstance(persona, dict)
                    self.assertTrue(persona)


def _example_path(stem: str):
    import world.imports.examples as examples_pkg
    from pathlib import Path

    return Path(examples_pkg.__file__).resolve().parent / f"{stem}.json"


class AuthoredDialogueContractTests(unittest.TestCase):
    """Every authored table keeps its own keywords and its own service voice."""

    maxDiff = None

    @covers_requirement(_DIALOGUE)
    def test_every_authored_table_keeps_its_service_semantics(self):
        tables = sorted(DIALOGUE_ROWS)
        self.assertTrue(tables, "the dialogue registry ships no table")
        for table_key in tables:
            with self.subTest(table=table_key):
                problems = _table_problems(DIALOGUE_ROWS[table_key], f"table {table_key}")
                self.assertEqual(problems, [])

    @covers_requirement(_DIALOGUE)
    def test_two_hosts_may_share_the_same_keyword_vocabulary(self):
        # The requirement keeps uniqueness *within* one table and explicitly
        # allows two hosts to expose the same service labels: the per-table rule
        # accepts both, so no globally unique keyword tuple is required.
        shared = ("共用標籤", "另一個")
        first = DialogueDefinition(
            greeting="「第一家店的問候語。」",
            responses=tuple(
                KeywordResponse(keyword, f"「第一家店對{keyword}的回答。」")
                for keyword in shared
            ),
        )
        second = DialogueDefinition(
            greeting="「第二家店的問候語。」",
            responses=tuple(
                KeywordResponse(keyword, f"「第二家店對{keyword}的回答。」")
                for keyword in shared
            ),
        )
        self.assertEqual(_table_problems(first, "table t_first"), [])
        self.assertEqual(_table_problems(second, "table t_second"), [])

    @covers_requirement(_DIALOGUE)
    def test_an_out_of_character_table_is_reported(self):
        # The structural check is not vacuous: a line smuggling a command or
        # interface token into prose is reported, and a table-local mute is
        # reported too.
        leaky = DialogueDefinition(
            greeting="「請輸入 look 來看看四周。」",
            responses=(KeywordResponse("看看", "「請打 look。」"),),
        )
        problems = _table_problems(leaky, "table t_leaky")
        self.assertTrue(
            any("Latin-token surface" in problem for problem in problems), problems
        )
        mute = DialogueDefinition(greeting="「問候。」", responses=(KeywordResponse("問", "  "),))
        self.assertTrue(any("empty" in problem for problem in _table_problems(mute, "table t_mute")))


if __name__ == "__main__":
    unittest.main()
