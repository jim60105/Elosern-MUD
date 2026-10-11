"""Scene-package publication, validation, and read-boundary tests.

Covers the new deterministic contracts: whole-package validation before any
write, immutable persistence with database-enforced identity, source replay and
conflict behavior, symbolic versus guild-branch commission publication, the
read-only role lookup, and startup restore. Behavior tests resolve game data
through the shared synthetic builders; no shipped key is named literally.
"""

import unittest

from evennia.utils.test_resources import EvenniaTestCase

from world.quests import scene_store
from world.quests.bootstrap import restore_scene_packages
from world.quests.compile import SCENE_REQUIREMENT_REGISTRY, scene_requirements_for
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.encounters import (
    ScenePackageNotFound,
    SceneRoleNotFound,
    lookup_story_role,
    publish_scene_package,
)
from world.quests.scene_package import ScenePackageError, validate_scene_package
from world.quests.tests._card_fixtures import occupant_card_record
from world.quests.tests._compile_helpers import (
    _anchor_key,
    _archetype_key,
    _issuer_key,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY

_LONG_PROSE = "南門的相遇，旅人在此停下腳步，等著一個承諾被實現。"


def _tier_key() -> str:
    """The first live NPC tier row (never a shipped key literal)."""
    return next(iter(NPC_TIER_REGISTRY))


def _characterization(tag: str) -> dict:
    return {
        "display_name": f"測試住民{tag}",
        "title": "迷路的旅人",
        "age": 30,
        "apparent_age": 30,
        "portrait": {"stable_key": f"test_portrait_{tag}"},
        "persona": occupant_card_record(tag),
    }


def _anchor_locator(**overrides) -> dict:
    locator = {
        "layer": "anchor",
        "anchor_key": _anchor_key(),
        "archetype": _archetype_key(),
        "anchor_near": None,
        "xyz": None,
        "scene_sentence": _LONG_PROSE,
    }
    locator.update(overrides)
    return locator


def _role(role_id: str, **overrides) -> dict:
    role = {
        "role_id": role_id,
        "tier": _tier_key(),
        "disposition": None,
        "characterization": _characterization(role_id),
        "conversable": True,
        "retention": _anchor_locator(archetype=None, scene_sentence=None),
    }
    role.update(overrides)
    return role


def _phase(phase_id, conditions, *, topics=()):
    return {
        "phase_id": phase_id,
        "conditions": list(conditions),
        "greeting": f"{_LONG_PROSE}{phase_id}",
        "topics": list(topics),
        "freeform_situation": _LONG_PROSE,
        "freeform_goals": _LONG_PROSE,
        "offline_response": _LONG_PROSE,
    }


def _dialogue(role_id: str, **overrides) -> dict:
    dialogue = {
        "role_id": role_id,
        "initial_phase": "searching",
        "phases": [
            _phase("searching", [{"default": True}]),
            _phase("everyday", [{"closure": True}], topics=[{"keyword": "近況", "response": _LONG_PROSE}]),
        ],
    }
    dialogue.update(overrides)
    return dialogue


def _quest_payload(*, issuer: str, merit: int = 0, npc_req=None) -> dict:
    return {
        "name": "尋找母親",
        "quest_type": "探索",
        "rank": "F",
        "issuer": issuer,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "reach_location", "quantity": 1},
                "location_req": _anchor_locator(),
                "npc_req": list(npc_req or []),
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": merit},
        "failure": {"deadline_hours": None, "conditions": []},
    }


def _package(**overrides) -> dict:
    package = {
        "display_name": "南門的相遇",
        "source_id": "synthetic-package-source",
        "quest": _quest_payload(issuer="mother"),
        "roles": [_role("mother"), _role("daughter")],
        "relationships": [
            {"from_role": "mother", "to_role": "daughter", "kind": "parent_child"}
        ],
        "knowledge": [
            {
                "role_id": "mother",
                "claim_id": "separation",
                "text": _LONG_PROSE,
                "provenance": {"kind": "role_owner", "ref": "mother"},
            }
        ],
        "encounters": [
            {
                "scene_id": "south_gate",
                "role_ids": ["daughter"],
                "locator": _anchor_locator(),
                "prerequisites": [],
            },
            {
                "scene_id": "market",
                "role_ids": ["mother"],
                "locator": _anchor_locator(),
                "prerequisites": [],
            },
        ],
        "dialogue": [_dialogue("mother"), _dialogue("daughter")],
        "commission": {"role_id": "mother", "issuer_content_key": "story_mother"},
    }
    package.update(overrides)
    return package


class ScenePackageValidationTests(EvenniaTestCase):
    """Whole-package validation rejects every invalid reference before writes."""

    def test_a_valid_package_normalizes_and_reports_its_identity(self):
        definition = validate_scene_package(_package())
        self.assertTrue(definition.package_id.startswith("pkg_"))
        self.assertEqual(definition.role_ids(), frozenset({"mother", "daughter"}))
        self.assertEqual(definition.commission.role_id, "mother")
        self.assertIsNone(definition.guild_branch)

    def test_unknown_encounter_role_is_rejected(self):
        package = _package()
        package["encounters"][0]["role_ids"] = ["stranger"]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("stranger", str(caught.exception))

    def test_unknown_place_is_rejected_without_substitution(self):
        package = _package()
        package["encounters"][0]["locator"]["anchor_key"] = "no_such_anchor"
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("no_such_anchor", str(caught.exception))

    def test_a_name_based_existing_npc_reference_is_rejected(self):
        package = _package()
        package["roles"][1]["existing_npc"] = {"kind": "key", "value": "測試住民daughter"}
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("existing_npc", str(caught.exception))

    def test_reciprocal_relationship_is_rejected(self):
        package = _package()
        package["relationships"].append(
            {"from_role": "daughter", "to_role": "mother", "kind": "parent_child"}
        )
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("reciprocal", str(caught.exception))

    def test_a_shared_visibility_knowledge_grant_is_rejected(self):
        package = _package()
        package["knowledge"][0]["provenance"] = {"kind": "world", "ref": "mother"}
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("provenance", str(caught.exception))

    def test_overlapping_phase_selection_is_rejected(self):
        package = _package()
        dialogue = package["dialogue"][0]
        dialogue["phases"][1]["conditions"] = [{"abandoned": True}, {"abandoned": True}]
        dialogue["phases"].append(_phase("duplicate", [{"abandoned": True}, {"abandoned": True}]))
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("overlapping", str(caught.exception))

    def test_a_guarded_reunion_observation_is_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"][1]["conditions"] = [{"reunion": True}]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("reunion", str(caught.exception))

    def test_a_missing_default_phase_is_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"][0]["conditions"] = [{"separation": True}]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("default", str(caught.exception))

    def test_a_private_commission_carrying_merit_is_rejected(self):
        package = _package(quest=_quest_payload(issuer="mother", merit=25))
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("merit", str(caught.exception))

    def test_an_unknown_top_level_field_is_rejected(self):
        package = _package()
        package["permissions"] = []
        with self.assertRaises(ScenePackageError):
            validate_scene_package(package)


class ScenePackagePublicationTests(RegistryIsolationMixin, EvenniaTestCase):
    """Publication persists an immutable package and registers its views."""

    def test_publication_registers_definition_and_requirements_without_issuance(self):
        published = publish_scene_package(_package(), owner="tester", tick=7)
        self.assertTrue(published.created)
        core = published.definition.quest
        self.assertEqual(QUEST_DEFINITION_REGISTRY[core.definition.key], core.definition)
        self.assertEqual(scene_requirements_for(core.definition.key), core.stage_requirements)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})
        row = scene_store.read_package(published.package_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.owner_id, "tester")
        self.assertEqual(row.created_tick, 7)

    def test_replaying_the_same_source_returns_the_stored_package(self):
        first = publish_scene_package(_package(), owner="tester")
        second = publish_scene_package(_package(), owner="tester")
        self.assertFalse(second.created)
        self.assertEqual(second.package_id, first.package_id)
        self.assertEqual(len(scene_store.list_packages()), 1)

    def test_a_differing_payload_for_one_source_conflicts(self):
        publish_scene_package(_package(), owner="tester")
        changed = _package(display_name="另一場相遇")
        with self.assertRaises(scene_store.ScenePackageConflictError):
            publish_scene_package(changed, owner="tester")
        self.assertEqual(len(scene_store.list_packages()), 1)

    def test_a_symbolic_package_publishes_an_unregistered_grant(self):
        published = publish_scene_package(_package(), owner="tester")
        grants = scene_store.list_commission_grants(published.package_id)
        self.assertEqual(len(grants), 1)
        self.assertFalse(grants[0].registered)
        self.assertEqual(grants[0].npc_id, 0)
        self.assertEqual(grants[0].issuer_key, "npc:story_mother")

    def test_a_guild_branch_package_registers_its_offer(self):
        package = _package(
            quest=_quest_payload(issuer=_issuer_key()),
            commission=None,
        )
        published = publish_scene_package(package, owner="tester")
        self.assertIsNone(published.definition.commission)
        self.assertEqual(len(GUILD_OFFER_REGISTRY), 1)
        self.assertEqual(scene_store.list_commission_grants(published.package_id), [])

    def test_an_exact_existing_npc_pk_reference_is_accepted(self):
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC

        npc = create_object(NPC, key="測試住民daughter")
        package = _package()
        package["roles"][1]["existing_npc"] = {"kind": "pk", "value": npc.pk}
        definition = validate_scene_package(package)
        self.assertEqual(definition.role("daughter").existing_npc_pk, npc.pk)


class StoryRoleLookupTests(RegistryIsolationMixin, EvenniaTestCase):
    """The role lookup is read-only and reports exact binding status."""

    def test_an_unmaterialized_role_reports_unavailable(self):
        published = publish_scene_package(_package(), owner="tester")
        found = lookup_story_role(published.package_id, "mother")
        self.assertFalse(found.bound)
        self.assertIsNone(found.npc_id)
        self.assertEqual(found.availability, "unmaterialized")
        self.assertEqual(found.commission_issuer_key, "npc:story_mother")

    def test_an_unknown_package_or_role_is_a_named_failure(self):
        published = publish_scene_package(_package(), owner="tester")
        with self.assertRaises(ScenePackageNotFound):
            lookup_story_role("pkg_missing", "mother")
        with self.assertRaises(SceneRoleNotFound):
            lookup_story_role(published.package_id, "stranger")


class ScenePackageRestoreTests(RegistryIsolationMixin, EvenniaTestCase):
    """Startup restore republishes definition views, never symbolic authority."""

    def test_restore_reregisters_definitions_only(self):
        published = publish_scene_package(_package(), owner="tester")
        key = published.definition.quest.definition.key
        QUEST_DEFINITION_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.clear()
        restore_scene_packages()
        self.assertIn(key, QUEST_DEFINITION_REGISTRY)
        self.assertIn(key, SCENE_REQUIREMENT_REGISTRY)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})

    def test_restore_reregisters_only_an_activated_grant(self):
        published = publish_scene_package(_package(), owner="tester")
        row = scene_store.read_package(published.package_id)
        grant = scene_store.list_commission_grants(published.package_id)[0]
        scene_store.set_grant_registered(
            row, grant.role_id, grant.definition_key, True
        )
        QUEST_DEFINITION_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.clear()
        restore_scene_packages()
        from world.rules.quest_issuance import resolve_issuance

        self.assertIsNotNone(
            resolve_issuance(grant.definition_key, grant.issuer_key)
        )
        self.assertIsNotNone(row)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
