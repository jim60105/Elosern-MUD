"""Shared bases, synthetic scope and payload helpers for the
``test_scene_builder`` slices and the offline/flavor sibling modules.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""

from contextlib import ExitStack
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest
from django.test import override_settings
from evennia.prototypes import prototypes as prototypes_module
from evennia.prototypes import spawner as spawner_module
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room
from world.ai.profiles import default_profiles
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.subjects import ArtSubjectKind
from world.art.worker import drain_synchronous
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import read_records
from world.quests.scene_builder import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    _validate_occupant_parent,
    materialize_stage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation, accept
from world.skills.registry import SkillPrerequisite
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.traits import build_initial_traits, trait_config_for_values
from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_ARCHETYPES,
    SYNTH_GUILD_ISSUER_KEY,
    SYNTH_NPC_TIERS,
    SYNTH_STATIC_TIERS,
    make_skill,
    synthetic_registries,
)
from tools.spec_traceability import covers_requirement

def _portrait_callbacks(callbacks):
    """The captured on-commit callbacks excluding quest-transition events.

    The observability migration schedules one ``quest_transition`` event per
    changed quest through ``transaction.on_commit``; the portrait-seam
    contracts below count only the callbacks the seam itself owns.
    """
    return [
        callback
        for callback in callbacks
        if not getattr(getattr(callback, "__code__", None), "co_filename", "").endswith(
            "world/quests/transitions.py"
        )
    ]

def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw

#: Synthetic scene fixtures. The payload builders below name these kit rows
#: directly, so every borrower resolves its scene content through the patched
#: registries instead of shipped catalog keys.
_T_ISSUER = SYNTH_GUILD_ISSUER_KEY.removeprefix("guild:")

_T_ARCHETYPE = "t_synth_bazaar"

_T_ANCHOR = "t_hollow_tarn"

_T_NPC_TIER = "t_synth_courier"

_T_NPC_TIER_ALT = "t_synth_ward"

_T_MONSTER_TIER = "t_faint"

_T_SENTENCE = "苔徑市集裡燈籠搖曳，攤商的低語此起彼落。"

_T_ROOM_NAME = SYNTH_ARCHETYPES[_T_ARCHETYPE].display_name_zh

_T_REGION = SYNTH_ANCHORS[_T_ANCHOR].display_name_zh

# A synthetic prerequisite chain for the lineage auto-seam: a deep skill
# consuming two mid-tier skills (the threshold picks mirror the shipped
# fire tree so the seeded XP is derived from the rulebook, not hard-coded).
_T_PREREQ_MID = make_skill("t_lineage_mid", label="燼徑中程")

_T_PREREQ_DEEP = make_skill(
    "t_lineage_deep",
    label="燼徑深技",
    prerequisites=(SkillPrerequisite(_T_PREREQ_MID.key, 3),),
)

_SCOPE = synthetic_registries(
    "guild_branches",
    "archetypes",
    "anchors",
    "anchor_placements",
    "npc_tiers",
    "monster_tiers",
    "races",
    "static_tiers",
    "subraces",
    "skills",
    extra={
        "skills": {
            _T_PREREQ_MID.key: _T_PREREQ_MID,
            _T_PREREQ_DEEP.key: _T_PREREQ_DEEP,
        }
    },
)

def _install_scenario_director():
    """Install the director layer idempotently after any module reload.

    ``world.ai.tests.test_scenario_director`` re-imports the module from
    ``sys.modules`` (cold-start test), which invalidates function identity for
    references captured earlier in the same process. Clearing the guardrail
    entries and re-registering through the live module keeps every later
    consumer deterministic regardless of test order.
    """
    from world.ai import guardrail, scenario_director
    from world.ai.schemas.registry import _OUTPUT_SCHEMAS

    guardrail._semantic_validators.pop("scenario_director", None)
    guardrail._degrade_fallbacks.pop("scenario_director", None)
    _OUTPUT_SCHEMAS.pop("scenario_director", None)
    scenario_director.register_scenario_director()

def _instance_bound_payload(**overrides):
    payload = {
        "name": "討伐林間盜匪",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": _T_ISSUER,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": None},
                "location_req": {
                    "layer": "instance",
                    "archetype": _T_ARCHETYPE,
                    "anchor_key": None,
                    "anchor_near": _T_ANCHOR,
                    "xyz": None,
                    "scene_sentence": _T_SENTENCE,
                },
                "npc_req": [
                    {
                        "role": "bandit",
                        "tier": _T_NPC_TIER,
                        "disposition": None,
                        "display_name": "黑鬍",
                        "title": "林間盜匪首領",
                    }
                ],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload

def _escort_anchor_payload(**overrides):
    payload = {
        "name": "護送商人至王都",
        "quest_type": "護衛",
        "rank": "F",
        "issuer": _T_ISSUER,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "escort", "quantity": 1},
                "location_req": {
                    "layer": "anchor",
                    "archetype": _T_ARCHETYPE,
                    "anchor_key": _T_ANCHOR,
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": _T_SENTENCE,
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload

def _monster_instance_payload(**overrides):
    payload = {
        "name": "討伐洞穴魔物",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": _T_ISSUER,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 2, "monster_tier": _T_MONSTER_TIER},
                "location_req": {
                    "layer": "instance",
                    "archetype": _T_ARCHETYPE,
                    "anchor_key": None,
                    "anchor_near": _T_ANCHOR,
                    "xyz": None,
                    "scene_sentence": "深邃的洞穴內滴水聲迴盪。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload

def _reach_anchor_payload(**overrides):
    payload = {
        "name": "探查王都廣場",
        "quest_type": "探索",
        "rank": "F",
        "issuer": _T_ISSUER,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "reach_location", "quantity": 1},
                "location_req": {
                    "layer": "anchor",
                    "archetype": _T_ARCHETYPE,
                    "anchor_key": _T_ANCHOR,
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": _T_SENTENCE,
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": 72, "conditions": []},
    }
    payload.update(overrides)
    return payload

class SceneBuilderIsolation(QuestRegistryIsolation):
    """Quest-registry snapshot/restore plus the synthetic scene scope.

    The scope is entered in ``setUp`` (not via the class decorator) because
    this base's setup builds synthetic scene data — the kit anchor room and
    the kit-race player — which must already resolve against the patched
    catalogs. ``addCleanup`` closes the scope after teardown.
    """

    def setUp(self):
        super().setUp()
        # The shipped catalog registers BEFORE the synthetic scope opens: its
        # monster-tier row validates against the shipped tier registry, and
        # registration is idempotent/snapshot-restored afterwards.
        from world.quests.tests._fixtures import register_catalog_once

        register_catalog_once()
        stack = ExitStack()
        stack.enter_context(_SCOPE)
        self.addCleanup(stack.close)
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

class SceneBuilderTestBase(SceneBuilderIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        # The kit's placed anchor materialized as a bare AnchorRoom: the
        # scene seam only needs a located anchor (db.anchor_key), never the
        # shipped grid.
        self.anchor = create_object(AnchorRoom, key="t-scene-anchor")
        self.anchor.anchor_key = _T_ANCHOR
        self.player = create_object(PlayerCharacter, key="scene-player")
        self.player.race = "t_duskmari"
        self.player.apply_race_baseline()
        self.player.location = self.anchor

    def _accept(self, payload):
        compiled = compile_quest_blueprint(payload)
        register_generated_quest(compiled)
        return accept(self.player, compiled.definition.key), compiled

    def _fresh(self, quest_id):
        return next(r for r in read_records(self.player) if r.quest_id == quest_id)
