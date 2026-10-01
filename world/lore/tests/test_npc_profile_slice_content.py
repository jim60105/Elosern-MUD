"""Data-contract test: per-slice authored NPC profiles and rewritten dialogue content contract
Every host named by an inventory slice references its own registered profile
whose key equals the host's service identity, validates through the compact
card contract, and authors a misunderstanding reply with no profile greeting;
every dialogue table the slice owns is its own authored table -- per-host
greeting, kept keyword identifiers, no shared placeholder line -- and no
authored line names a command, a mechanic or an interface element."""

from __future__ import annotations

import re
import unittest

from tools.spec_traceability import covers_requirement
from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.guild import GUILD_RANK_REGISTRY, validate_guild_npc_identities
from world.lore.npc_card import NpcCard
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY
from world.lore.settlements.places import PLACE_REGISTRY

# A line in a host's own world never names a command, a mechanic or an
# interface element: the shipped command surface, mechanics vocabulary and
# panel tokens are all ASCII, so any run of two or more Latin letters in an
# authored greeting, keyword response or voice line names one of them.
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z]{2,}")


def _slice_pairs(owner: str, kind: str) -> tuple[str, ...]:
    """The inventory keys one slice owns for one source kind, in row order."""
    return tuple(
        row.key for row in NPC_SOURCE_INVENTORY if row.owner == owner and row.kind == kind
    )


def _host_place(service_id: str):
    """The single shipped place row hosting this service identity."""
    places = [p for p in PLACE_REGISTRY.values() if p.service_id == service_id]
    if len(places) != 1:
        raise AssertionError(
            f"service identity {service_id!r} is hosted by {len(places)} places"
        )
    return places[0]


def _assert_in_character(text: str, origin: str) -> None:
    """A spoken line names no command, mechanic or interface element."""
    assert "`" not in text, f"{origin} quotes a command token"
    assert not _ASCII_TOKEN_RE.search(text), f"{origin} names a Latin-token surface"


class NpcProfileSliceContentContractTests(unittest.TestCase):
    """Each authored slice's hosts, profiles and dialogue tables agree."""

    maxDiff = None

    def _assert_hosts_carry_individual_profiles(self, owner: str) -> set[str]:
        """Every owned host references its own valid misunderstanding-only profile.

        Returns the hosts' authored misunderstanding lines so the caller can
        join them into the slice-wide individuality check.
        """
        misunderstandings: set[str] = set()
        hosts = _slice_pairs(owner, "place_host")
        self.assertTrue(hosts, f"slice {owner} owns no place_host rows")
        for service_id in hosts:
            with self.subTest(host=service_id):
                place = _host_place(service_id)
                # The profile reference travels through the place record and
                # its key is the host's service identity -- never a display
                # name, never a borrowed key.
                self.assertEqual(place.host_profile_key, service_id)
                profile = NPC_PROFILE_REGISTRY[place.host_profile_key]
                self.assertEqual(profile.key, service_id)
                # Card completeness is the registry round-trip contract.
                NpcCard.from_record(profile.card.to_record())
                # The table authors the greeting; only the misunderstanding
                # reply belongs to the profile.
                self.assertIsNone(profile.voice.greeting)
                self.assertTrue(profile.voice.misunderstood)
                _assert_in_character(
                    profile.voice.misunderstood, f"profile {service_id} misunderstanding"
                )
                misunderstandings.add(profile.voice.misunderstood)
        # Individuality: hosts sharing a profession still speak in their own
        # voices; a copied misunderstanding line fails this.
        self.assertEqual(len(misunderstandings), len(hosts))
        return misunderstandings

    def _assert_tables_are_rewritten(self, owner: str) -> None:
        """Each owned table keeps its keywords and its own rewritten greeting.

        Keyword identifiers are the dialogue panel's choice labels and are
        preserved; the authored half (greeting, responses, and the table
        itself) is per-host -- a shared placeholder table or greeting fails
        the distinctness assertions, and no assertion pins the prose.
        """
        tables = _slice_pairs(owner, "dialogue_table")
        self.assertTrue(tables, f"slice {owner} owns no dialogue_table rows")
        keyword_tuples: list[tuple[str, ...]] = []
        for key in tables:
            with self.subTest(table=key):
                definition = DIALOGUE_ROWS[key]
                # The greeting is kept and authored in character.
                self.assertTrue(definition.greeting)
                _assert_in_character(definition.greeting, f"table {key} greeting")
                # The keyword identifiers survive: unique labels, one
                # authored in-character response each.
                keywords = [response.keyword for response in definition.responses]
                self.assertEqual(len(keywords), len(set(keywords)))
                for response in definition.responses:
                    self.assertTrue(response.response)
                    _assert_in_character(
                        response.response, f"table {key} response {response.keyword}"
                    )
                keyword_tuples.append(tuple(keywords))
        # Rewritten per source: no two tables of one slice are the same
        # table, so the keyword label sets cannot be one shared template.
        self.assertEqual(len(keyword_tuples), len(set(keyword_tuples)))
        # No shared placeholder greeting within the slice.
        greetings = [DIALOGUE_ROWS[key].greeting for key in tables]
        self.assertEqual(len(greetings), len(set(greetings)))

    @covers_requirement(
        "npc-profile-registry::altoria-lower-terrace-hosts-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_altoria_lower_slice_hosts_and_tables(self):
        self._assert_hosts_carry_individual_profiles("altoria_lower")
        self._assert_tables_are_rewritten("altoria_lower")

    @covers_requirement(
        "npc-profile-registry::altoria-middle-terrace-trade-hosts-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_altoria_trade_slice_hosts_and_tables(self):
        self._assert_hosts_carry_individual_profiles("altoria_trade")
        self._assert_tables_are_rewritten("altoria_trade")

    @covers_requirement(
        "npc-profile-registry::guild-branch-master-and-rank-examiners-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_altoria_guild_slice_host_examiners_and_table(self):
        self._assert_hosts_carry_individual_profiles("altoria_guild")
        self._assert_tables_are_rewritten("altoria_guild")
        ranks = _slice_pairs("altoria_guild", "guild_examiner")
        self.assertTrue(ranks, "slice altoria_guild owns no guild_examiner rows")
        for rank_key in ranks:
            with self.subTest(rank=rank_key):
                rank = GUILD_RANK_REGISTRY[rank_key]
                # Every shipped rank names a profile through the field the
                # validator resolves, and the module-level shipped-registry
                # validation (re-run below) has already proven that key
                # resolves with a complete card.
                self.assertTrue(rank.examiner_profile_key)
                profile = NPC_PROFILE_REGISTRY[rank.examiner_profile_key]
                NpcCard.from_record(profile.card.to_record())
                # An examiner fights, it does not speak.
                self.assertIsNone(profile.voice.greeting)
                self.assertIsNone(profile.voice.misunderstood)
        # The whole shipped rank table passes the same load validation, so
        # no shipped rank is missing or holding an unresolved key.
        validate_guild_npc_identities()

    @covers_requirement(
        "npc-profile-registry::altoria-upper-terrace-hosts-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_altoria_upper_slice_hosts_and_tables(self):
        self._assert_hosts_carry_individual_profiles("altoria_upper")
        self._assert_tables_are_rewritten("altoria_upper")

    @covers_requirement(
        "npc-profile-registry::village-ciaran-first-home-hosts-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_ciaran_homes_a_slice_hosts_and_tables(self):
        self._assert_hosts_carry_individual_profiles("ciaran_homes_a")
        self._assert_tables_are_rewritten("ciaran_homes_a")

    @covers_requirement(
        "npc-profile-registry::village-ciaran-second-home-hosts-carry-individual-authored-profiles-and-rewritten-dialogue"
    )
    def test_ciaran_homes_b_slice_hosts_and_tables(self):
        self._assert_hosts_carry_individual_profiles("ciaran_homes_b")
        self._assert_tables_are_rewritten("ciaran_homes_b")

    def test_no_host_shares_its_voice_or_greeting_across_slices(self):
        # Slice-wide distinctness is local; the corpus-wide rule is that all
        # 25 authored hosts and all 25 tables are individually voiced --
        # profile keys, misunderstanding lines and table greetings are three
        # closed sets with no collisions.
        hosts = [row.key for row in NPC_SOURCE_INVENTORY if row.kind == "place_host"]
        keys = [NPC_PROFILE_REGISTRY[h].key for h in hosts]
        self.assertEqual(len(keys), len(set(keys)))
        misunderstandings = [
            NPC_PROFILE_REGISTRY[h].voice.misunderstood for h in hosts
        ]
        self.assertEqual(len(misunderstandings), len(set(misunderstandings)))
        greetings = [DIALOGUE_ROWS[key].greeting for key in DIALOGUE_ROWS]
        self.assertEqual(len(greetings), len(set(greetings)))


if __name__ == "__main__":
    unittest.main()
