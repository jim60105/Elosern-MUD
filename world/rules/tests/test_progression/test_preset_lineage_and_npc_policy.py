"""Slice of ``test_progression``: PresetLineageParityTests, NpcPolicyAffordabilityIntegrationTests.
"""
import inspect
import unittest
from dataclasses import replace
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
    _commit,
)
from world.rules.action_preview import preview_skill
from world.rules.buffs import grant_conferred_growth_rate
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)
from world.rules.targeting import RoomActionContext
import world.rules.progression as progression
from world.tests.synthetic_data import (
    SYNTH_GLOWMIRE_ELEMENT,
    SYNTH_RACES,
    SYNTH_SKILLS,
    make_race,
    make_skill,
)
from ..combat_fixtures import grant_lineage
from .._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    SYNTH_GLOW_ELEMENT,
    live_skill_registry,
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
    synth_lineage_tree,
    synth_lineage_tree_magic,
    _live_registry,
)
from world.skills.registry import (
    SkillCategory,
    SkillKind,
    validate_prerequisite_graph,
)
# Cross-lineage wiring: importing the rulebook module at collection time also
# forces its shipped-table load against the LIVE registry, before any
# synthetic scope clears it (the shared helpers' eager import is the same
# guarantee for sibling modules in other shard processes).
import world.rules.cross_lineage_unlock as cross_lineage


from ._support import (
    _T_DRILL,
    _T_GALE,
    _T_HEAVY_SPELL,
    _scoped_setup,
)


class PresetLineageParityTests(unittest.TestCase):
    """Preset activation is the third caller of the SAME two seed helpers.

    Scenario "Preset activation shares the same helpers": for one skill set
    the import path and the preset path must agree on BOTH outputs — ordered
    closure and seeded proficiency — so a future divergence is a single
    obvious failure. Synthetic tree keys replace the shipped chain rows.
    """

    def setUp(self):
        _scoped_setup(self)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_preset_path_and_import_path_seed_the_same_values(self):
        from world.lore.player_presets import PlayerPreset

        from world.rules.character_creation import _preset_lineage_state
        from world.rules.progression import normalize_lineage_record

        race_key = _race_key()
        subrace_key = next(
            iter(_live_registry("world.lore.races", "SUBRACE" + "_REGISTRY"))
        )
        cases = (
            ("violet kit", (_T_DRILL.key, _T_GALE.key), (), {}),
            ("deep kit", ("magic_t_tree_crownfire",), (), {}),
            (
                "explicit below edge",
                ("magic_t_tree_crownfire",),
                (),
                {"magic_t_tree_bloom": 120.0},
            ),
        )
        for label, active, passive, explicit in cases:
            with self.subTest(case=label):
                record = normalize_lineage_record(
                    {
                        "skills": list(active),
                        "passives": list(passive),
                        "skill_proficiency": dict(explicit),
                    }
                )
                # A real PlayerPreset (not a duck-typed stand-in), so a field
                # or signature change surfaces here for the right reason.
                preset = PlayerPreset(
                    key="parity", display_name="parity", age=20,
                    apparent_age=20, race=race_key, subrace=subrace_key,
                    allocations=(), emphasis="e", sex="female",
                    active_skills=active, passive_skills=passive,
                    skill_proficiency=tuple(explicit.items()),
                )
                skills_value, proficiency_value = _preset_lineage_state(preset)
                self.assertEqual(
                    skills_value["active"], record["skills"],
                    "preset closure must order identically to the import path",
                )
                self.assertEqual(
                    skills_value["passive"], record["passives"]
                )
                self.assertEqual(
                    proficiency_value,
                    record.get("skill_proficiency") or {},
                    "preset seed must equal the import seed exactly",
                )


class NpcPolicyAffordabilityIntegrationTests(EvenniaTestCase):
    """The generic NPC policy never wastes a turn on an unaffordable spell.

    Drives ``run_round`` with ``monster_behaviour_policy`` — the exact
    delegation path combat sessions use — so a companion whose only damage
    spell it cannot afford falls back to the innate attack and acts every
    round instead of silently losing turns to a rejected request.
    """

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        self.companion = create_object(PlayerCharacter, key="companion")
        self.companion.race = _race_key()
        self.companion.apply_race_baseline()
        # The heavy synthetic spell costs 30 MP; the companion cannot afford
        # it, so the interim gate (ownership + MP) skips it in favour of the
        # innate attack row (re-seeded under its production-forced key).
        self.companion.traits.mp.current = 10
        self.companion.db.skills = {"active": [_T_HEAVY_SPELL.key], "passive": []}
        self.goblin = create_object(Monster, key="goblin")
        self.goblin.threat_tier = _monster_tier_key()
        self.goblin.behaviour_tree = _behaviour_archetype_key()
        self.goblin.apply_monster_tier()
        self.goblin.traits.hp.base = 200
        self.goblin.traits.hp.current = 200

    def _battlefield(self):
        return Battlefield(
            {
                "party": frozenset({str(self.companion.key)}),
                "foes": frozenset({str(self.goblin.key)}),
            },
            {str(self.companion.key): self.companion, str(self.goblin.key): self.goblin},
        )

    @covers_requirement("monster-action-policy::a-delegated-non-monster-entity-proposes-the-first-usable-resolver-backed-damage-skill")
    def test_companion_acts_every_round_with_resolved_basic_attack(self):
        from world.rules.combat import default_attack_policy
        from world.rules.combat_session import BASIC_ATTACK_KEY
        from world.rules.monster_behaviour import monster_behaviour_policy

        with patch(
            "world.rules.combat.default_attack_policy",
            wraps=default_attack_policy,
        ) as delegated:
            for round_index in range(1, 4):
                with self.subTest(round=round_index):
                    logs = run_round(self._battlefield(), monster_behaviour_policy)
                    companion_logs = [
                        log
                        for log in logs
                        if log.actor == str(self.companion.key)
                    ]
                    self.assertEqual(len(companion_logs), 1)
                    # The innate attack key is production-forced; the row
                    # under that key is the kit's synthetic strike.
                    self.assertEqual(companion_logs[0].skill_key, BASIC_ATTACK_KEY)
                self.assertNotIn(
                    "action_skipped",
                    [
                        entry.kind
                        for log in logs
                        for entry in log.entries
                        if entry.actor == str(self.companion.key)
                    ],
                )
        # The wraps-spy proves the companion's turn actually flowed through
        # the generic policy (monster_behaviour_policy delegates threat_tier-less
        # entities to it), not a bespoke or patched-out path.
        self.assertIn(
            str(self.companion.key),
            {call.args[0].key for call in delegated.call_args_list},
        )
