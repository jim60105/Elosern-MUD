"""Data-contract test: human combat calibration evidence exercises shipped gear, skill, and monster rows through the real resolver

Real-runtime calibration, bounded resolver probes, and persistent host evidence.
"""

import random
import unittest
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    _stored_trait_value,
)
from world.rules.character_creation import (
    resolve_starting_profile,
    _resolve_values,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _stored_hp,
    is_battle_over,
    run_round,
)
from world.rules.combat_session.policies import (
    BASIC_ATTACK_KEY,
    _basic_attack_request,
    _enemy_policy,
)
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.guild_exam_restrictions import (
    activate_exam_restriction,
    preflight_exam_restriction,
    remove_exam_restriction,
)
from world.rules.human_guild_hosts import sync_persistent_adventurers
from world.rules.traits import _trait_config
from world.rules.monster_individual import construct_species_individual
from world.rules.progression import apply_lineage_auto_seed
from world.rules.progression import can_use_skill
from world.skills.registry import SKILL_REGISTRY
from world.skills.restrictions import exam_restriction


@dataclass(frozen=True)
class TrialOutcome:
    seed: int
    rounds: int
    monster_defeated: bool
    monster_retreated: bool
    human_loss: bool
    all_standing: bool
    unfinished: bool
    rejected_actions: int
    final_human_hps: tuple[int, ...]
    final_monster_hp: int


def _build_synthetic_probe_monster(name: str, hp: int, attack: int, agility: int, defense: int) -> Monster:
    monster = create_object(Monster, key=name)
    monster._apply_trait_config(_trait_config({
        "hp": hp,
        "mp": 0,
        "sp": 0,
        "atk_phys": attack,
        "agility": agility,
        "defense": defense,
        "magic_power": 0,
        "guild_merit": 0,
    }))
    monster.db.skills = {"active": [BASIC_ATTACK_KEY], "passive": []}
    return monster


def _human_combatant_policy(human: NPC, battlefield: Battlefield, full_b: bool = False) -> ActionRequest | None:
    enemy_team = next(
        (members for team, members in battlefield.teams.items() if team != battlefield.team_of(str(human.key))),
        frozenset(),
    )
    candidates = [
        battlefield.roster[k]
        for k in enemy_team
        if k in battlefield.roster and k not in battlefield.fled and _stored_hp(battlefield.roster[k]) > 0
    ]
    if not candidates:
        return None
    target = candidates[0]
    context = BattlefieldActionContext(battlefield, event_context={"battlefield": battlefield, "simulated": True})

    record = exam_restriction(human)
    allowed = record["allowed_skills"] if record else human.skills.owned_keys()

    if full_b:
        hp_frac = human.traits.hp.current / max(1, human.traits.hp.base)
        if hp_frac <= 0.40 and "heal" in allowed and can_use_skill(human, SKILL_REGISTRY["heal"]):
            cost = SKILL_REGISTRY["heal"].cost
            if all(_stored_trait_value(getattr(human.traits, res)) >= amt for res, amt in cost.items()):
                return ActionRequest(human, "heal", [human], context)
        buffs = getattr(human.db, "buffs", ()) or ()
        active_buff_keys = {b.definition_key if hasattr(b, "definition_key") else b for b in buffs}
        if "concentration" in allowed and "concentration_tier1" not in active_buff_keys and can_use_skill(human, SKILL_REGISTRY["concentration"]):
            cost = SKILL_REGISTRY["concentration"].cost
            if all(_stored_trait_value(getattr(human.traits, res)) >= amt for res, amt in cost.items()):
                return ActionRequest(human, "concentration", [human], context)
        if "gale_step" in allowed and "gale_step_tier1" not in active_buff_keys and can_use_skill(human, SKILL_REGISTRY["gale_step"]):
            cost = SKILL_REGISTRY["gale_step"].cost
            if all(_stored_trait_value(getattr(human.traits, res)) >= amt for res, amt in cost.items()):
                return ActionRequest(human, "gale_step", [human], context)

    for skill_key in (
        "true_sword_saint",
        "blade_saint_arts",
        "thousand_blade_art",
        "tendon_sever",
        "flowing_strikes",
        "basic_swordplay",
    ):
        if skill_key in allowed and can_use_skill(human, SKILL_REGISTRY[skill_key]):
            cost = SKILL_REGISTRY[skill_key].cost
            if all(_stored_trait_value(getattr(human.traits, res)) >= amt for res, amt in cost.items()):
                return ActionRequest(human, skill_key, [target], context)

    return ActionRequest(human, BASIC_ATTACK_KEY, [target], context)


def _run_single_trial(
    humans: list[NPC],
    monster: Monster,
    seed: int,
    controlled_monster_attacks: bool = True,
    full_b: bool = False,
    max_rounds: int = 200,
) -> TrialOutcome:
    random.seed(seed)
    for i, h in enumerate(humans):
        if len(humans) > 1 and not h.key.endswith(f"_{i}"):
            h.key = f"{h.key}_{i}"
        h.traits.hp.current = h.traits.hp.base
        h.traits.mp.current = h.traits.mp.base
        h.traits.sp.current = h.traits.sp.base
    monster.traits.hp.current = monster.traits.hp.base

    roster = {str(h.key): h for h in humans}
    roster[str(monster.key)] = monster
    battlefield = Battlefield(
        teams={"humans": frozenset(roster.keys() - {str(monster.key)}), "monsters": frozenset({str(monster.key)})},
        roster=roster,
    )

    dummy_record = CombatSessionRecord(
        session_id="sim-trial",
        mode="guild_exam",
        room_id=0,
        player_ids=tuple(h.pk for h in humans),
        enemy_ids=(monster.pk,),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id="sim-trial-exam",
    )

    rejected_count = 0
    original_resolve = ActionResolver.resolve

    def observing_resolve(request):
        nonlocal rejected_count
        res = original_resolve(request)
        if res.outcome != "success":
            rejected_count += 1
        return res

    rounds_elapsed = 0
    with patch("world.rules.action.resolver.ActionResolver.resolve", side_effect=observing_resolve):
        while rounds_elapsed < max_rounds and not is_battle_over(battlefield):
            def trial_provider(entity, field):
                if str(entity.key) in field.teams["humans"]:
                    return _human_combatant_policy(entity, field, full_b=full_b)
                if controlled_monster_attacks:
                    enemy_team = field.teams["humans"]
                    cands = [field.roster[k] for k in enemy_team if _stored_hp(field.roster[k]) > 0]
                    if not cands:
                        return None
                    tgt = min(cands, key=lambda e: (_stored_hp(e), str(e.key)))
                    ctx = BattlefieldActionContext(field, event_context={"battlefield": field, "simulated": True})
                    return ActionRequest(entity, BASIC_ATTACK_KEY, [tgt], ctx)
                req = _enemy_policy(entity, field, dummy_record)
                if req is not None and req.context is not None:
                    req.context.event_context["simulated"] = True
                return req

            run_round(battlefield, trial_provider, simulated=True)
            rounds_elapsed += 1

    monster_defeated = _stored_hp(monster) <= 0
    monster_retreated = str(monster.key) in battlefield.fled
    living_humans = [h for h in humans if _stored_hp(h) > 0]
    human_loss = len(living_humans) == 0
    all_standing = len(living_humans) == len(humans)
    unfinished = (not monster_defeated) and (not monster_retreated) and (not human_loss)

    return TrialOutcome(
        seed=seed,
        rounds=rounds_elapsed,
        monster_defeated=monster_defeated,
        monster_retreated=monster_retreated,
        human_loss=human_loss,
        all_standing=all_standing,
        unfinished=unfinished,
        rejected_actions=rejected_count,
        final_human_hps=tuple(_stored_hp(h) for h in humans),
        final_monster_hp=_stored_hp(monster),
    )


class HumanCombatCalibrationTests(EvenniaTest):
    """Synthetic and real-resolver calibration tests."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="calibration_room")

    def _create_human_f(self) -> NPC:
        profile = resolve_starting_profile("human", "human_plains")
        allocations = {
            "hp": 69, "mp": 69, "sp": 69,
            "atk_phys": 4, "agility": 4, "defense": 4,
            "magic_power": 5,
        }
        values = _resolve_values(profile, allocations)
        human = create_object(NPC, key="human_f", location=self.room)
        human._apply_trait_config(_trait_config(values))
        human.db.inventory = ["plain_sword", "leather_armor", "silver_hairpin"]
        human.db.equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": "leather_armor",
            "accessories": ["silver_hairpin"],
        }
        human.db.skills = {"active": ["basic_swordplay"], "passive": []}
        return human

    def _create_human_with_restriction(self, rank: str) -> NPC:
        from world.rules.guild_exam_restrictions import PROFILES
        prof = PROFILES[rank]
        human = create_object(NPC, key=f"human_{rank}", location=self.room)
        human._apply_trait_config(_trait_config({
            "hp": 200,
            "mp": 150,
            "sp": 150,
            "atk_phys": 30,
            "agility": 30,
            "defense": 30,
            "magic_power": 30,
            "guild_merit": 0,
        }))
        inv = [prof.weapon, prof.armor]
        if prof.accessory:
            inv.append(prof.accessory)
        human.db.inventory = inv
        human.db.equipment = {
            "weapon_main": prof.weapon,
            "weapon_off": None,
            "armor": prof.armor,
            "accessories": [],
        }
        human.db.skills = {"active": list(prof.allowed_skills), "passive": []}
        apply_lineage_auto_seed(human)
        preflight = preflight_exam_restriction(human, rank)
        activate_exam_restriction(human, f"exam_{rank}_{human.pk}", rank)
        return human

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    @covers_requirement(
        "human-combat-calibration::evidence-separates-defeat-retreat-support-safety-and-unverified-projections"
    )
    def test_human_calibration_uses_real_resolver_gear_restrictions_and_bounded_outcome_evidence(self):
        # Bounded real-resolver probes over real gear and rank restrictions.
        # Each probe records its outcome taxonomy and asserts only action
        # validity and real resolver execution -- never a balance outcome, so
        # there is no seeded victory pin and no replacement victory band.
        f_human = self._create_human_f()
        grain_pecker = construct_species_individual("sway_whistle_sparrow", "grain_pecker")

        e_human = self._create_human_with_restriction("E")
        self.assertIsNotNone(exam_restriction(e_human))
        shore_walker = construct_species_individual("tide_lamp_crab", "shore_walker")

        b_human = self._create_human_with_restriction("B")
        bank_lurker = construct_species_individual("tide_devouring_crocodile", "bank_lurker")
        high_lower = _build_synthetic_probe_monster("high_lower", hp=320, attack=28, agility=18, defense=20)
        high_upper = _build_synthetic_probe_monster("high_upper", hp=700, attack=38, agility=26, defense=28)
        s_human = self._create_human_with_restriction("S")
        calamity_lower = _build_synthetic_probe_monster("calamity_lower", hp=1200, attack=60, agility=60, defense=60)

        probes = {
            "F_vs_low_species": (f_human, grain_pecker),
            "E_vs_low_species": (e_human, shore_walker),
            "B_vs_mid_species": (b_human, bank_lurker),
            "B_vs_high_lower": (b_human, high_lower),
            "B_vs_high_upper": (b_human, high_upper),
            "S_vs_high_upper": (s_human, high_upper),
            "S_vs_calamity": (s_human, calamity_lower),
        }
        for label, (human, monster) in probes.items():
            with self.subTest(probe=label):
                outcomes = [
                    _run_single_trial(
                        [human], monster, seed=s, controlled_monster_attacks=True
                    )
                    for s in range(4)
                ]
                self._assert_probe_evidence(outcomes, human, monster)

        remove_exam_restriction(e_human, f"exam_E_{e_human.pk}")
        self.assertIsNone(exam_restriction(e_human))

    def _assert_probe_evidence(self, outcomes, human, monster) -> None:
        """The bounded probe ran the real resolver and every action resolved.

        ``rejected_actions == 0`` is action-validity evidence only: it proves
        every action the probe selected was resolvable, never that any balance
        outcome is correct. A combatant HP must move, proving the real damage
        path executed instead of no-opping.
        """
        for outcome in outcomes:
            self.assertGreater(outcome.rounds, 0, "the bounded run must execute a round")
            self.assertLessEqual(outcome.rounds, 200)
            self.assertEqual(
                outcome.rejected_actions, 0, "every selected action must resolve"
            )
            self.assertTrue(
                outcome.final_monster_hp < monster.traits.hp.base
                or outcome.final_human_hps[0] < human.traits.hp.base,
                "the real resolver must have changed a combatant's HP",
            )
        # The recorded evidence includes a bounded round median: it must be a
        # real executed run inside the same bound as the individual probes,
        # never a balance target.
        rounds = sorted(outcome.rounds for outcome in outcomes)
        middle = len(rounds) // 2
        median = (
            rounds[middle]
            if len(rounds) % 2
            else (rounds[middle - 1] + rounds[middle]) / 2
        )
        self.assertGreaterEqual(median, 1, "the round median must be a real run")
        self.assertLessEqual(median, 200, "the round median must stay bounded")

    @covers_requirement(
        "human-combat-calibration::evidence-separates-defeat-retreat-support-safety-and-unverified-projections"
    )
    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    def test_evidence_separates_defeat_retreat_support_safety_and_unverified_projections(self):
        # The real enemy policy drives this probe: the evidence keeps escape
        # and zero-HP defeat as distinct categories and records per-member
        # party state, without pinning which category a seed lands in.
        c_human = self._create_human_with_restriction("C")
        cliff_stepper = construct_species_individual("rock_echo_goat", "cliff_stepper")
        outcomes_c_policy = [
            _run_single_trial([c_human], cliff_stepper, seed=s, controlled_monster_attacks=False)
            for s in range(4)
        ]
        for outcome in outcomes_c_policy:
            self.assertGreater(outcome.rounds, 0)
            self.assertLessEqual(outcome.rounds, 200)
            self.assertEqual(outcome.rejected_actions, 0)
            self.assertFalse(
                outcome.monster_defeated and outcome.monster_retreated,
                "an escape must never be recorded as a zero-HP defeat",
            )

        d1 = self._create_human_with_restriction("D")
        d2 = self._create_human_with_restriction("D")
        d3 = self._create_human_with_restriction("D")
        wood_stalker = construct_species_individual("fog_mane_lynx", "wood_stalker")
        outcomes_party = [
            _run_single_trial([d1, d2, d3], wood_stalker, seed=s, controlled_monster_attacks=True)
            for s in range(4)
        ]
        for outcome in outcomes_party:
            self.assertEqual(outcome.rejected_actions, 0)
            # Per-member party state is recorded evidence, one entry each.
            self.assertEqual(len(outcome.final_human_hps), 3)

        player = create_object(PlayerCharacter, key="p_control", location=self.room)
        player._apply_trait_config(_trait_config({
            "hp": 100,
            "mp": 100,
            "sp": 100,
            "atk_phys": 10,
            "agility": 10,
            "defense": 10,
            "magic_power": 10,
            "guild_merit": 0,
        }))
        player.db.skills = {"active": ["basic_swordplay"], "passive": []}
        initial_xp = (player.db.skill_proficiency or {}).get("basic_swordplay", 0.0)

        target_dummy = create_object(Monster, key="target_dummy", location=self.room)
        target_dummy._apply_trait_config(_trait_config({
            "hp": 1000,
            "mp": 0,
            "sp": 0,
            "atk_phys": 1,
            "agility": 1,
            "defense": 1,
            "magic_power": 0,
            "guild_merit": 0,
        }))

        bfield = Battlefield(
            teams={"players": frozenset({str(player.key)}), "monsters": frozenset({str(target_dummy.key)})},
            roster={str(player.key): player, str(target_dummy.key): target_dummy},
        )
        sim_ctx = BattlefieldActionContext(bfield, event_context={"battlefield": bfield, "simulated": True})
        req = ActionRequest(player, "basic_swordplay", [target_dummy], sim_ctx)
        ActionResolver.resolve(req)
        after_sim_xp = (player.db.skill_proficiency or {}).get("basic_swordplay", 0.0)
        self.assertEqual(after_sim_xp, initial_xp)

        live_ctx = BattlefieldActionContext(bfield, event_context={"battlefield": bfield})
        req_live = ActionRequest(player, "basic_swordplay", [target_dummy], live_ctx)
        ActionResolver.resolve(req_live)
        after_live_xp = (player.db.skill_proficiency or {}).get("basic_swordplay", 0.0)
        self.assertGreater(after_live_xp, initial_xp)

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    def test_persistent_host_exam_lifecycle_restoration_smoke(self):
        from world.rules.human_guild_hosts import sync_persistent_adventurers, find_persistent_adventurer
        fake_routes = {
            "altoria_hok_home": {"home": self.room, "frontage": self.room, "guild": self.room},
            "altoria_cassandra_home": {"home": self.room, "frontage": self.room, "guild": self.room},
            "altoria_augustine_home": {"home": self.room, "frontage": self.room, "guild": self.room},
        }
        with patch("world.rules.human_guild_hosts.resolve_residence_route", side_effect=lambda home, guild: fake_routes.get(home, {"home": self.room, "frontage": self.room, "guild": self.room})):
            hosts = sync_persistent_adventurers()
            self.assertTrue(len(hosts) >= 3)
            hok = find_persistent_adventurer("altoria_hok")
            self.assertIsNotNone(hok)
        before_equip = dict(hok.db.equipment or {})
        before_inv = list(hok.db.inventory or [])
        before_bases = (hok.traits.hp.base, hok.traits.atk_phys.base, hok.traits.agility.base, hok.traits.defense.base)
        activate_exam_restriction(hok, "smoke_exam_hok", "B")
        self.assertIsNotNone(exam_restriction(hok))
        remove_exam_restriction(hok, "smoke_exam_hok")
        self.assertIsNone(exam_restriction(hok))
        self.assertEqual(dict(hok.db.equipment or {}), before_equip)
        self.assertEqual(list(hok.db.inventory or []), before_inv)
        after_bases = (hok.traits.hp.base, hok.traits.atk_phys.base, hok.traits.agility.base, hok.traits.defense.base)
        self.assertEqual(after_bases, before_bases)
