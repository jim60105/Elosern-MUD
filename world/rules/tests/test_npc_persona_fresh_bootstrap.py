"""Regression tests pinning fresh database bootstrap and fail-closed payload rejection (D4).

Covers OpenSpec capability ``npc-persona-cutover``:
1. A freshly initialized database synchronizes all shipped NPCs with the current
   content-generation marker and a contract-valid complete card at creation time,
   with roster validation present and no in-place cutover step.
2. Pre-amendment quest payloads carrying the retired background field or old
   three-field prose fail closed at strict restore validation with a named failure
   and are never registered into play.
3. The developer database reset runbook exists and documents the migration command,
   default database path, retained test database path, and data loss warning.
"""

from collections.abc import Mapping
from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import NPC
from typeclasses.rooms import Room

from server.conf.at_server_startstop import STARTUP_STEP_ORDER
from tools.spec_traceability import covers_requirement
from world.rules.guild_config import get_catalog
from world.lore.npc_card import (
    NPC_CARD_FORMAT,
    NPC_PERSONA_CONTENT_GENERATION,
    normalize_card,
)
from world.maps.bootstrap import sync_grid, sync_service_interiors
from world.quests.catalog import register_catalog
from world.quests.bootstrap import restore_generated_quests
from world.quests.compile.contracts import QuestCompileError
from world.quests.compile.payload import payload_to_registrations
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.generated_quest_store import append_payload, clear
from world.rules.guild_economy import sync_service_content
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.npc_roster_validation import validate_npc_roster


class NpcPersonaFreshBootstrapTests(EvenniaTest):
    """Pin the fresh-bootstrap completeness and startup step invariants."""

    def setUp(self):
        super().setUp()
        register_catalog()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        sync_service_content()

    @covers_requirement(
        "npc-persona-cutover::a-fresh-database-is-initialized-with-the-complete-marked-npc-roster-without-any-rewrite-step"
    )
    def test_fresh_bootstrap_npcs_are_born_marked_and_valid(self):
        """Fresh initialization yields a fully marked roster with no cutover step."""
        # 1. Startup step order contract: roster validation present, cutover absent
        self.assertIn("npc_persona_roster_validation", STARTUP_STEP_ORDER)
        self.assertNotIn("npc_persona_cutover", STARTUP_STEP_ORDER)

        # 2. Roster validation passes cleanly against fresh bootstrap
        validate_npc_roster()

        # 3. Every shipped service host is born marked and carries a valid compact card
        npcs = list(NPC.objects.all_family())
        expected_hosts = get_catalog().service_hosts
        self.assertEqual(
            len(npcs),
            len(expected_hosts),
            f"Expected {len(expected_hosts)} hosts, found {len(npcs)} NPCs",
        )

        for npc in npcs:
            with self.subTest(npc=npc.key):
                meta = npc.db.npc_persona_meta
                self.assertTrue(
                    isinstance(meta, Mapping), f"NPC {npc.key} lacks npc_persona_meta mapping"
                )
                self.assertEqual(
                    meta.get("format"),
                    NPC_CARD_FORMAT,
                    f"NPC {npc.key} meta has unexpected format {meta.get('format')!r}",
                )
                self.assertEqual(
                    meta.get("generation"),
                    NPC_PERSONA_CONTENT_GENERATION,
                    f"NPC {npc.key} meta generation {meta.get('generation')!r} != {NPC_PERSONA_CONTENT_GENERATION}",
                )
                self.assertIsInstance(
                    meta.get("persona_version"),
                    int,
                    f"NPC {npc.key} persona_version is not an int: {meta.get('persona_version')!r}",
                )
                self.assertGreaterEqual(meta["persona_version"], 1)

                provenance = meta.get("provenance")
                self.assertTrue(isinstance(provenance, Mapping))
                self.assertEqual(provenance.get("kind"), "profile")
                self.assertTrue(provenance.get("profile"))

                card_raw = npc.db.persona
                self.assertIsNotNone(card_raw, f"NPC {npc.key} lacks persona card")
                card = normalize_card(card_raw)
                self.assertTrue(card.identity.public)
                self.assertTrue(card.personality)


class PreAmendmentPayloadFailClosedTests(EvenniaTest):
    """Pin the fail-closed rejection of pre-amendment quest payloads."""

    def setUp(self):
        super().setUp()
        clear()

    def tearDown(self):
        clear()
        super().tearDown()

    def _pre_amendment_payload(self) -> dict:
        """Synthetic pre-amendment occupant payload (retired background + old persona prose)."""
        return {
            "definition": {
                "key": "synth_pre_amendment_quest_001",
                "display_name": "討伐林間盜匪",
                "quest_type": "討伐",
                "rank": "F",
                "stages": [
                    {
                        "index": 0,
                        "objective": {
                            "kind": "defeat",
                            "quantity": 1,
                            "monster_tier": None,
                            "destination": {
                                "kind": "bound_instance",
                                "anchor_key": None,
                                "xyz": None,
                            },
                            "requires_bound_targets": True,
                            "item_key": None,
                        },
                    }
                ],
                "deadline_hours": None,
            },
            "issuance": {
                "issuer_key": "guild:guild_branch_altoria",
                "settlement": "counter",
                "reward": {
                    "copper": 50,
                    "items": [],
                    "merit": 25,
                },
            },
            "requirements": [
                {
                    "index": 0,
                    "objective_kind": "defeat",
                    "location": {
                        "kind": "bound_instance",
                        "anchor_key": None,
                        "xyz": None,
                    },
                    "archetype": None,
                    "anchor_near": None,
                    "scene_sentence": "王都近郊的林間小徑樹影搖曳，一名盜匪的身影在樹叢間若隱若現。",
                    "npc_reqs": [["bandit", "bandit", None]],
                    "characterizations": [
                        {
                            "display_name": "黑鬍",
                            "title": "林間盜匪首領",
                            "age": 35,
                            "apparent_age": 35,
                            "portrait_stable_key": "forest_bandit_chief",
                            # Pre-amendment retired field: background
                            "background": "王都近郊林間的盜匪首領，盤據要道收受過路費。",
                            # Pre-amendment shape: list of [field, prose] pairs
                            "persona": [
                                ["identity", "林間盜匪首領"],
                                ["personality", "粗魯豪爽，對手下講義氣"],
                                ["habit", "喜歡用匕首削木頭"],
                            ],
                            "combat_traits": [],
                        }
                    ],
                }
            ],
        }

    @covers_requirement(
        "npc-persona-cutover::pre-amendment-generated-quest-payloads-fail-closed-with-no-compatibility-decoder"
    )
    def test_pre_amendment_payload_fails_closed_without_compatibility_decoder(self):
        """Pre-amendment occupant payloads are rejected at restore and never registered."""
        payload = self._pre_amendment_payload()
        quest_key = payload["definition"]["key"]

        # 1. Direct codec decode raises QuestCompileError naming the retired background field
        with self.assertRaises(QuestCompileError) as ctx:
            payload_to_registrations(payload)
        self.assertIn("carries the retired background field", str(ctx.exception))

        # 2. Durable restore also fails loudly and does not register the quest
        append_payload(payload)
        with self.assertRaises(QuestCompileError):
            restore_generated_quests()

        # 3. Neither QUEST_DEFINITION_REGISTRY nor GUILD_OFFER_REGISTRY contains the stale quest
        self.assertNotIn(quest_key, QUEST_DEFINITION_REGISTRY)
        self.assertNotIn(quest_key, GUILD_OFFER_REGISTRY)


class DatabaseResetRunbookContractTests(unittest.TestCase):
    """Docs contract test guarding the database-reset runbook."""

    @covers_requirement(
        "npc-persona-cutover::destroying-and-re-initializing-the-development-database-is-the-documented-supported-recovery"
    )
    def test_database_reset_runbook_contract(self):
        """The runbook exists, names the migration command, database files, and warnings."""
        repo_root = Path(__file__).resolve().parents[3]
        runbook_path = repo_root / "docs" / "development" / "database-reset.md"

        self.assertTrue(
            runbook_path.is_file(),
            f"Runbook {runbook_path} does not exist",
        )

        content = runbook_path.read_text(encoding="utf-8")

        # 1. Names the migration command
        self.assertIn("evennia migrate", content)

        # 2. Names the default development database path from settings.py
        self.assertIn("server/db/evennia.db3", content)

        # 3. Names the retained test database path from test_settings.py
        self.assertIn("server/db/evennia-test.sqlite3", content)

        # 4. Names the --keepdb test flag
        self.assertIn("--keepdb", content)

        # 5. Carries an explicit data loss warning
        self.assertTrue(
            any(phrase in content for phrase in ("永久刪除", "警示", "警告", "Data Loss")),
            "Runbook lacks an explicit data loss warning",
        )
