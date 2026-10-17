"""Data-contract test: human combat calibration evidence exercises shipped gear, skill, and monster rows through the real resolver

Real-runtime calibration, bounded resolver probes, and persistent host evidence.
"""

import random
import unittest
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from typing import Any
from unittest.mock import patch

from django.test import TransactionTestCase
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
    COMBAT_YAML,
    RoundTactical,
    _handle_damage,
    _heal_magnitude,
    _stored_hp,
    is_battle_over,
    run_round,
)
from world.rules.combat.scalars import (
    crosses_knockout,
    nonlethal_projection,
    strike_amount,
)
from world.rules.buffs import TickRecord
from world.lore.items import ITEM_REGISTRY
from world.rules.equipment import add_item, normalized_equipment, toggle_equipment
from world.rules.equipment_effects import (
    EQUIPMENT_EFFECT_RULES,
    equipment_adjustments,
    equipment_weapon_multiplier,
)
from world.rules.combat_session.policies import (
    BASIC_ATTACK_KEY,
    _basic_attack_request,
    _enemy_policy,
)
from world.rules.combat_session import (
    _context_for,
    _persist,
    confirm_actor_command,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_player_item_use,
)
from world.rules.combat_session.battlefield import _commandable_required_actors
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.party import join_party
from world.rules.items import ItemUseRequest, preflight_item_use
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
from world.skills.effects import (
    DamagePolicy,
    EffectPolicy,
    ResolvedEffect,
)


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


# The fixed landed base hit the equipment-growth evidence was measured with.
_GROWTH_ROLL = 60
# A shipped element, so the staged strike resolves through the real parser.
_GROWTH_ELEMENT = "fire"


class EquipmentGrowthCommittedReloadTests(TransactionTestCase):
    """Real construction, registered gear and committed reload growth evidence.

    The equipment-growth slice's authored weapon factors are real shipped
    data, so its evidence uses real Evennia construction, registered gear,
    ordinary grant/equip rules and a committed re-read. The base is Django's
    ``TransactionTestCase`` (the same choice ``DurableRoundAdmissionTests``
    makes) because this probe exists to observe committed state: ``TestCase``
    would enclose it in an atomic block whose rollback hides whether the reads
    came from storage at all. ``_reread`` force-evicts both idmapper caches --
    ``ObjectDB`` (an NAttribute-holding object refuses the soft flush) and
    ``Attribute``, where equipment, inventory and traits actually live -- and
    fetches the object row again, so every number below is observed on a
    freshly loaded instance instead of the writer's own handler state. The
    actor's true stats stay below the defender's defense, which the retired
    subtraction engine would have masked entirely, and all probes use one
    fixed d100 roll. These are measurements, not balance claims: encounter
    tuning belongs to its own change.
    """

    # The published evidence numbers (docs/development/human-combat-calibration-evidence.md).
    # They are asserted as literals so a settlement regression that stopped
    # consuming the factor could not pass on ordering alone, and so any
    # authored retune forces the published record to be re-measured with it.
    PUBLISHED_HITS = {"unarmed": 10, "initial": 11, "selected": 20}
    PUBLISHED_ARMOR_HITS = {"bare": 20, "light": 19, "heavy": 17}
    PUBLISHED_MAGIC_HIT = 15
    PUBLISHED_HEAL = 30

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="equipment_growth_room")

    def _actor(self, key: str, **allocations: int) -> PlayerCharacter:
        actor = create_object(PlayerCharacter, key=key, location=self.room)
        # atk_phys 20 stays under the defender's defense 40: subtraction would
        # have floored this matchup, ratio mitigation does not.
        stats = {
            "hp": 200,
            "mp": 100,
            "sp": 100,
            "atk_phys": 20,
            "agility": 10,
            "defense": 40,
            "magic_power": 30,
            "guild_merit": 0,
        }
        stats.update(allocations)
        actor._apply_trait_config(_trait_config(stats))
        actor.db.inventory = []
        actor.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        actor.db.skills = {"active": ["basic_swordplay"], "passive": []}
        actor.db.skill_proficiency = {"basic_swordplay": 7.5}
        actor.db.affinity_elements = [_GROWTH_ELEMENT]
        return actor

    def _reread(self, actor: PlayerCharacter) -> PlayerCharacter:
        """Return a freshly loaded instance of one committed actor row."""
        from evennia.objects.models import ObjectDB
        from evennia.typeclasses.attributes import Attribute

        actor.save()
        for model in (ObjectDB, Attribute):
            model.flush_instance_cache(force=True)
        fresh = PlayerCharacter.objects.get(pk=actor.pk)
        self.assertIsNot(fresh, actor)
        return fresh

    def _grant_and_equip(self, actor: PlayerCharacter, item_key: str) -> None:
        """Grant through the ordinary inventory rule and equip it."""
        add_item(actor, item_key)
        self.assertEqual(toggle_equipment(actor, item_key).outcome, "success")

    def _factor(self, item_key: str) -> float:
        return EQUIPMENT_EFFECT_RULES[
            ITEM_REGISTRY[item_key].modifier_key
        ].weapon_damage_multiplier

    def _staged(self, attacker, defender, school: str) -> int:
        with patch("world.rules.combat.damage.roll_d100", return_value=_GROWTH_ROLL):
            pending = _handle_damage(
                attacker,
                [defender],
                f"damage:{_GROWTH_ELEMENT}:{school}",
                {},
                1.0,
            )[0]
        return int(pending.description.rsplit("|", 1)[1])

    def _invariants(self, actor: PlayerCharacter) -> tuple:
        traits = actor.traits
        return (
            tuple(
                getattr(traits, name).base
                for name in (
                    "hp",
                    "mp",
                    "sp",
                    "atk_phys",
                    "magic_power",
                    "agility",
                    "defense",
                )
            ),
            dict(actor.db.skill_proficiency or {}),
            list(actor.db.affinity_elements or []),
            dict(actor.db.skills or {}),
        )

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence",
        "human-combat-calibration::equipment-growth-evidence-uses-real-construction-and-committed-reload",
        "equipment-effects::shipped-weapons-have-authored-selected-values-backed-by-real-growth-evidence",
    )
    def test_real_weapon_upgrade_growth_survives_a_committed_reload(self):
        attacker = self._actor("growth attacker")
        defender = self._actor("growth defender", atk_phys=1)
        before = self._invariants(self._reread(attacker))

        unarmed_actor = self._reread(attacker)
        unarmed = self._staged(unarmed_actor, defender, "physical")
        self.assertEqual(equipment_weapon_multiplier(unarmed_actor), 1.0)

        self._grant_and_equip(attacker, "plain_sword")
        initial_actor = self._reread(attacker)
        initial = self._staged(initial_actor, defender, "physical")
        initial_factor = equipment_weapon_multiplier(initial_actor)

        self._grant_and_equip(attacker, "military_s_sword")
        selected_actor = self._reread(attacker)
        selected = self._staged(selected_actor, defender, "physical")
        selected_factor = equipment_weapon_multiplier(selected_actor)

        # The committed re-read reports the authored declarations themselves
        # (never a default, never an in-memory edit).
        self.assertEqual(initial_factor, self._factor("plain_sword"))
        self.assertEqual(selected_factor, self._factor("military_s_sword"))
        self.assertGreater(selected_factor, initial_factor)
        # Positive marginal growth below the old subtraction threshold: the
        # adjusted attacks (20 / 20 + plain-sword flat / 20 + S-sword flat)
        # all land at or below defense 40, yet each committed state hits for
        # strictly more than the one before it, at the published amounts.
        self.assertEqual(
            {"unarmed": unarmed, "initial": initial, "selected": selected},
            self.PUBLISHED_HITS,
        )

        # Durable provenance: a value held only in the writer's process (an
        # ndb entry, like any ordinary instance attribute) never reaches
        # committed storage, while the equipped upgrade is still reported by
        # the next freshly loaded instance.
        attacker.ndb.uncommitted_weapon = "plain_sword"
        again = self._reread(attacker)
        self.assertEqual(
            normalized_equipment(again)["weapon_main"], "military_s_sword"
        )
        self.assertEqual(equipment_weapon_multiplier(again), selected_factor)
        self.assertIsNone(again.ndb.uncommitted_weapon)

        # No base-trait, proficiency, affinity or owned-skill drift from
        # ordinary grant/equip/persistence.
        self.assertEqual(self._invariants(again), before)

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence",
        "human-combat-calibration::equipment-growth-evidence-uses-real-construction-and-committed-reload",
    )
    def test_real_armor_and_control_schools_stay_invariant_to_the_weapon_factor(self):
        attacker = self._actor("control attacker")
        defender = self._actor("control defender", atk_phys=1)
        self._grant_and_equip(attacker, "military_s_sword")
        armed = self._reread(attacker)
        unarmed_actor = self._actor("control unarmed")
        committed_unarmed = self._reread(unarmed_actor)

        bare = self._staged(armed, self._reread(defender), "physical")
        # Magic and healing never consume the physical factor: the same fixed
        # roll and the same caster yield identical amounts with and without a
        # nonneutral weapon (military_s_sword carries no magic_power), at the
        # published amounts.
        armed_magic = self._staged(armed, self._reread(defender), "magic")
        unarmed_magic = self._staged(
            committed_unarmed, self._reread(defender), "magic"
        )
        self.assertEqual(armed_magic, unarmed_magic)
        self.assertEqual(armed_magic, self.PUBLISHED_MAGIC_HIT)
        self.assertEqual(_heal_magnitude(armed), self.PUBLISHED_HEAL)
        self.assertEqual(
            _heal_magnitude(committed_unarmed), self.PUBLISHED_HEAL
        )

        # Positive defense reduces the successful hit monotonically across
        # committed armor states, and armor contributes defense only: the
        # armored defender's own weapon factor stays the neutral default.
        self._grant_and_equip(defender, "leather_armor")
        light = self._staged(armed, self._reread(defender), "physical")
        self._grant_and_equip(defender, "military_s_armor")
        heavy_defender = self._reread(defender)
        heavy = self._staged(armed, heavy_defender, "physical")
        self.assertEqual(
            {"bare": bare, "light": light, "heavy": heavy},
            self.PUBLISHED_ARMOR_HITS,
        )
        self.assertGreater(heavy, 0)
        self.assertEqual(equipment_weapon_multiplier(heavy_defender), 1.0)
        self.assertEqual(
            dict(equipment_adjustments(heavy_defender))["defense"],
            EQUIPMENT_EFFECT_RULES[
                ITEM_REGISTRY["military_s_armor"].modifier_key
            ].adjustments["defense"],
        )
        # The attacker's selected factor is untouched by the defender's armor.
        self.assertEqual(
            equipment_weapon_multiplier(self._reread(attacker)),
            self._factor("military_s_sword"),
        )


# ---------------------------------------------------------------------------
# Finite combined damage factor budget evidence
# (party-combat-factor-budget-calibration, change 18 of the party-combat batch)
#
# The batch contract fixes this slice at 30 explicit cases: the 12 listed
# combinations run with the actor sides exchanged (player attacker and enemy
# attacker) plus six invariant controls added once. Every expected amount below
# is an independently hand-derived literal -- the scalar placement (round, then
# ratio mitigation, then the rider, then the floor, then the authored scale,
# then Defend) is never re-derived by calling the calculator under test. These
# are measurements at the factor boundary, not an encounter balance claim:
# finite encounter outcome tuning belongs to party-combat-encounter-calibration.
# ---------------------------------------------------------------------------

#: The fixed scalar boundary every case shares unless it says otherwise: attack
#: 60, mitigation K 40 against defense 20 (the retired subtraction engine
#: floored this matchup; ratio mitigation does not), both sides' agility 10.
_FACTOR_ATTACK = 60
_FACTOR_DEFENSE = 20
_FACTOR_AGILITY = 10
#: Margin 29: a landing base hit, below the rulebook's solid-hit margin 40.
_FACTOR_BASE_ROLL = 80
#: A natural critical face.
_FACTOR_CRIT_ROLL = 100
#: A shipped predicate fact (the elemental registry key the conditional cases
#: declare on the defender), so the policy vocabulary check passes.
_FACTOR_FACT = "fire"
#: The declared physical weapon factor the abstract cases name. No shipped
#: weapon declares 1.5, so this is one file-local synthetic declaration (the
#: device ``test_damage_bands`` already uses), never an authored retune and
#: never registry-echo arithmetic.
_FACTOR_WEAPON = 1.5


@dataclass(frozen=True)
class _FactorCase:
    """One explicit factor case with an independently hand-derived outcome."""

    label: str
    expected: int
    school: str = "physical"
    roll: int = _FACTOR_BASE_ROLL
    scale: float = 1.0
    coefficient: float = 1.0
    attack: int = _FACTOR_ATTACK
    defense: int = _FACTOR_DEFENSE
    defender_agility: int = _FACTOR_AGILITY
    weapon: float | None = None
    predicate: tuple[str, ...] = ()
    matched_multiplier: float = 1.0
    extra_strikes: int = 0
    max_hp_fraction: float = 0.0
    bypass: bool = False
    defender_max_hp: int = 200
    defender_tactic: str | None = None
    counterfactual: int | None = None
    counterfactual_overrides: dict[str, Any] = field(default_factory=dict)
    expected_strikes: int = 1


#: The 12 listed factor combinations. Each is run in both directions, so the
#: bounded base set is 24 observed outcomes; the counterfactual literal records
#: what the same inputs produce once the declaration under test is removed.
FACTOR_CASES: tuple[_FactorCase, ...] = (
    _FactorCase(
        "physical basic coefficient1/base roll/weapon1 (attack 60, K 40, defense 20)",
        expected=40,
    ),
    _FactorCase(
        "physical weapon factor 1.5: round(60 x 1.5) = 90, 90 x 40 / 60 = 60",
        expected=60,
        weapon=_FACTOR_WEAPON,
        counterfactual=40,
        counterfactual_overrides={"weapon": None},
    ),
    _FactorCase(
        "magic with the same 1.5 weapon declaration: the factor is never consumed",
        expected=40,
        school="magic",
        weapon=_FACTOR_WEAPON,
    ),
    _FactorCase(
        "explicit bypass at defense 60: round(60) x 40 / 40 = 60",
        expected=60,
        defense=60,
        bypass=True,
        counterfactual=24,
        counterfactual_overrides={"bypass": False},
    ),
    _FactorCase(
        "matched conditional multiplier 2: round(60 x 2) = 120, 120 x 40 / 60 = 80",
        expected=80,
        predicate=(_FACTOR_FACT,),
        matched_multiplier=2.0,
        counterfactual=40,
        counterfactual_overrides={"predicate": (), "matched_multiplier": 1.0},
    ),
    _FactorCase(
        "max-HP rider 0.1 on HP 100: 40 + floor(100 x 0.1) = 50",
        expected=50,
        max_hp_fraction=0.1,
        defender_max_hp=100,
        counterfactual=40,
        counterfactual_overrides={"max_hp_fraction": 0.0},
    ),
    _FactorCase(
        "authored scale 0.5 with the rider: floor(50 x 0.5 + 0.5) = 25",
        expected=25,
        max_hp_fraction=0.1,
        defender_max_hp=100,
        scale=0.5,
        counterfactual=20,
        counterfactual_overrides={"max_hp_fraction": 0.0},
    ),
    _FactorCase(
        "coefficient 2 x critical 2 x weapon 1.5 x two strikes: 240 each, 480 total",
        expected=240,
        roll=_FACTOR_CRIT_ROLL,
        coefficient=2.0,
        weapon=_FACTOR_WEAPON,
        extra_strikes=1,
        expected_strikes=2,
    ),
    _FactorCase(
        "Defend 0.35 after the authored scale: floor(30 x 0.65) = 19",
        expected=19,
        weapon=_FACTOR_WEAPON,
        scale=0.5,
        defender_tactic="defend",
        counterfactual=30,
        counterfactual_overrides={"defender_tactic": None},
    ),
    _FactorCase(
        "Dodge threshold 25 turns a landing margin into a miss",
        expected=0,
        defender_agility=20,
        defender_tactic="dodge",
        counterfactual=40,
        counterfactual_overrides={"defender_tactic": None},
    ),
    _FactorCase(
        "raw 100 with an insufficient margin still misses",
        expected=0,
        roll=_FACTOR_CRIT_ROLL,
        defender_agility=60,
    ),
    _FactorCase(
        "combined conditional2/coefficient2/weapon1.5/critical2/rider/scale2/two strikes",
        expected=980,
        roll=_FACTOR_CRIT_ROLL,
        coefficient=2.0,
        predicate=(_FACTOR_FACT,),
        matched_multiplier=2.0,
        weapon=_FACTOR_WEAPON,
        extra_strikes=1,
        max_hp_fraction=0.1,
        defender_max_hp=100,
        scale=2.0,
        expected_strikes=2,
    ),
)

#: The authored initial/selected factor reference the preceding slice shipped,
#: re-measured here where the parity probe equips them for real.
_AUTHORED_INITIAL_WEAPON = "plain_sword"
_AUTHORED_SELECTED_WEAPON = "military_s_sword"


@contextmanager
def _declared_factor(attacker, factor: float):
    """Equip one file-local synthetic weapon declaring ``factor`` on the actor."""
    from world.lore.items import EquipmentModifierKey, EquipmentSlot
    from world.rules.equipment_effects import EquipmentEffectRule
    from world.tests.synthetic_data import make_item

    item = make_item(
        key="t_factor_sword",
        equipment_slot=EquipmentSlot.WEAPON_MAIN,
        modifier_key=EquipmentModifierKey.PLAIN_SWORD,
    )
    rule = EquipmentEffectRule(
        adjustments={},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
        weapon_damage_multiplier=factor,
    )
    equipment = dict(attacker.db.equipment or {})
    equipment["weapon_main"] = item.key
    attacker.db.equipment = equipment
    with (
        patch.dict("world.rules.equipment_effects.ITEM_REGISTRY", {item.key: item}),
        patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
            {EquipmentModifierKey.PLAIN_SWORD: rule},
        ),
    ):
        yield


class CombatFactorBudgetTests(EvenniaTest):
    """The finite combined factor budget matrix (30 explicit cases)."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="factor_budget_room")

    def _actor(self, cls, key, *, hp=200, attack=60, agility=10, defense=10):
        actor = create_object(cls, key=key, location=self.room)
        actor._apply_trait_config(_trait_config({
            "hp": hp,
            "mp": 100,
            "sp": 100,
            "atk_phys": attack,
            "agility": agility,
            "defense": defense,
            "magic_power": attack,
            "guild_merit": 0,
        }))
        actor.db.inventory = []
        actor.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        actor.db.skills = {"active": [], "passive": []}
        return actor

    def _pair(self, case: _FactorCase, *, player_attacker: bool):
        """Build the real player and enemy actors for one direction."""
        attacker_cls, defender_cls = (
            (PlayerCharacter, Monster) if player_attacker else (Monster, PlayerCharacter)
        )
        prefix = "player_attacker" if player_attacker else "enemy_attacker"
        attacker = self._actor(attacker_cls, f"{prefix}_attacker", attack=case.attack)
        defender = self._actor(
            defender_cls,
            f"{prefix}_defender",
            hp=case.defender_max_hp,
            attack=1,
            agility=case.defender_agility,
            defense=case.defense,
        )
        if case.predicate:
            # The predicate fact is declared through the elemental affinity the
            # vocabulary check reads, so the matched conditional case exercises
            # the real fact path rather than a combat-trait label.
            defender.db.affinity_elements = list(case.predicate)
        return attacker, defender

    def _stage(self, attacker, defender, case: _FactorCase, *, battlefield=None):
        """Stage one case's strike and return the per-strike staged amounts.

        An explicit ``battlefield`` lets a control supply its own round-start
        declarations through this one patched staging harness instead of a
        second, untracked patching site.
        """
        predicate = case.predicate
        matched = case.matched_multiplier
        bypass = case.bypass
        rider = case.max_hp_fraction
        tactic = case.defender_tactic
        policy = None
        if predicate or matched != 1.0 or bypass or rider or case.extra_strikes:
            policy = DamagePolicy(
                predicate=predicate,
                attack_multiplier=matched,
                unconditional_defense_bypass=bypass,
                max_hp_fraction=rider,
                extra_strikes=case.extra_strikes,
            )
        event_context: dict[str, Any] = {}
        if policy is not None or case.coefficient != 1.0:
            event_context["resolved_effect"] = ResolvedEffect(
                policy=EffectPolicy(coefficient=case.coefficient, damage=policy)
            )
        if battlefield is None and tactic is not None:
            battlefield = Battlefield(
                {
                    "attackers": frozenset({str(attacker.key)}),
                    "defenders": frozenset({str(defender.key)}),
                },
                {str(attacker.key): attacker, str(defender.key): defender},
            )
            battlefield.tactical = RoundTactical({str(defender.key): tactic})
        if battlefield is not None:
            event_context["battlefield"] = battlefield
        weapon = case.weapon
        weapon_scope = (
            _declared_factor(attacker, weapon) if weapon else nullcontext()
        )
        with (
            weapon_scope,
            patch("world.rules.combat.damage.roll_d100", return_value=case.roll),
            patch(
                "world.rules.combat.damage.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            pending = _handle_damage(
                attacker,
                [defender],
                f"damage:none:{case.school}",
                event_context,
                case.scale,
            )
        return [int(item.description.rsplit("|", 1)[1]) for item in pending]

    @covers_requirement(
        "human-combat-calibration::combined-ratio-weapon-and-tactical-calibration-covers-both-combat-sides",
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence",
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor",
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a",
        "combat-resolution::defend-reduces-eligible-final-scaled-direct-damage",
        "combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins",
        "combat-resolution::ratio-mitigation-clamps-negative-defense-and-shares-settlement-and-estimation",
    )
    def test_combined_factor_matrix_holds_on_both_sides(self):
        # 24 of the 30 bounded cases: every listed combination observed with a
        # real player attacker and a real enemy attacker, at the fixed literals.
        observed = 0
        for case in FACTOR_CASES:
            for player_attacker in (True, False):
                with self.subTest(
                    case=case.label, player_attacker=player_attacker
                ):
                    attacker, defender = self._pair(
                        case, player_attacker=player_attacker
                    )
                    amounts = self._stage(attacker, defender, case)
                    self.assertEqual(len(amounts), case.expected_strikes)
                    self.assertEqual(set(amounts), {case.expected})
                    if case.counterfactual is not None:
                        # The counterfactual is a whole second staging of the
                        # same fixed inputs with one declaration replaced, not
                        # a delta applied to the first result.
                        counterfactual = self._stage(
                            attacker,
                            defender,
                            replace(case, **case.counterfactual_overrides),
                        )
                        self.assertEqual(set(counterfactual), {case.counterfactual})
                    observed += 1
        self.assertEqual(observed, 24)
        # Ordering discriminator for case 9: the reverse composition (Defend on
        # the unscaled base -- floor(60 x 0.65) = 39 -- then the authored 0.5
        # scale) records 20, so a scale/Defend reordering inside the shared
        # scalar reads 20 here against case 9's asserted 19.
        self.assertEqual(
            strike_amount(
                attack=39.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=0.0,
                scale=0.5,
            ),
            20,
        )

    @covers_requirement(
        "human-combat-calibration::combined-ratio-weapon-and-tactical-calibration-covers-both-combat-sides",
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence",
        "combat-resolution::defend-reduces-eligible-final-scaled-direct-damage",
        "combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins",
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor",
        "combat-resolution::ratio-mitigation-clamps-negative-defense-and-shares-settlement-and-estimation",
        "combat-resolution::per-round-upkeep-ticks-buffs-and-advances-sexual-decay-by-the-round-duration",
    )
    def test_invariant_controls_hold_once_each(self):
        # The remaining six of the 30 bounded cases, added once rather than per
        # direction: the controls the combined budget must not move.
        live_case = FACTOR_CASES[0]

        # 1. Unchecked direct damage receives no Dodge roll: a roster key that
        # never declared Dodge lands at the undodged literal even while another
        # key's declaration is active in the same field. It runs through the
        # shared staging harness with its own battlefield, so the fixed patching
        # site is single-sourced.
        attacker, defender = self._pair(live_case, player_attacker=True)
        battlefield = Battlefield(
            {"a": frozenset({str(attacker.key)}), "d": frozenset({str(defender.key)})},
            {str(attacker.key): attacker, str(defender.key): defender},
        )
        battlefield.tactical = RoundTactical({"someone_else": "dodge"})
        self.assertEqual(
            set(self._stage(attacker, defender, live_case, battlefield=battlefield)),
            {40},
        )

        # 2. Per-recipient AREA Dodge differs by declaration: the same fixed
        # face lands on the undeclared recipient and misses on the declared one.
        area_attacker = self._actor(PlayerCharacter, "area_attacker", attack=60)
        dodging = self._actor(Monster, "area_dodging", attack=1, agility=20, defense=20)
        standing = self._actor(Monster, "area_standing", attack=1, agility=20, defense=20)
        area_field = Battlefield(
            {
                "a": frozenset({str(area_attacker.key)}),
                "d": frozenset({str(dodging.key), str(standing.key)}),
            },
            {
                str(area_attacker.key): area_attacker,
                str(dodging.key): dodging,
                str(standing.key): standing,
            },
        )
        area_field.tactical = RoundTactical({str(dodging.key): "dodge"})
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=_FACTOR_BASE_ROLL),
            patch(
                "world.rules.combat.damage.evaluate_combat_modifiers", return_value={}
            ),
        ):
            area = _handle_damage(
                area_attacker,
                [dodging, standing],
                "damage:none:physical",
                {"battlefield": area_field},
                1.0,
            )
        self.assertEqual(int(area[0].description.rsplit("|", 1)[1]), 0)
        self.assertEqual(int(area[1].description.rsplit("|", 1)[1]), 40)

        # 3. Upkeep damage ignores Defend: a damaging buff tick is applied by
        # the tick itself, outside the shared strike amount, so a declared
        # defender takes the full 10 through the round's own upkeep settlement
        # (only the tick producer is stubbed, not the consumer).
        slow = self._actor(PlayerCharacter, "upkeep_slow", hp=100, attack=10, agility=1)
        fast = self._actor(Monster, "upkeep_fast", hp=100, attack=10, agility=99)
        upkeep_field = Battlefield(
            {"ally": frozenset({str(slow.key)}), "enemy": frozenset({str(fast.key)})},
            {str(slow.key): slow, str(fast.key): fast},
        )
        tick = TickRecord(definition_key="t_factor_dot", source_pk=7, delta=-10, hp_before=100)

        def fake_tick(entity, seconds):
            if str(entity.key) == str(slow.key):
                entity.traits.hp.current = entity.traits.hp.current - 10
                return (tick,)
            return ()

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.tick_buffs", side_effect=fake_tick),
            patch("world.rules.combat.rounds.decay_tick"),
            patch(
                "world.rules.combat.rounds.climax_settlement_action",
                return_value=None,
            ),
        ):
            run_round(
                upkeep_field,
                lambda entity, field: None,
                tactical_declarations={str(slow.key): "defend"},
            )
        self.assertEqual(slow.traits.hp.current, 90)

        # 4. Explicit bypass ignores Defend: the declared defender takes the
        # undefended amount, while the same strike without the bypass is reduced.
        bypass_case = _FactorCase(
            "bypass control",
            expected=60,
            bypass=True,
            defender_tactic="defend",
            counterfactual=26,
            counterfactual_overrides={"bypass": False, "defender_tactic": "defend"},
        )
        attacker, defender = self._pair(bypass_case, player_attacker=False)
        self.assertEqual(set(self._stage(attacker, defender, bypass_case)), {60})
        self.assertEqual(
            set(
                self._stage(
                    attacker,
                    defender,
                    replace(bypass_case, **bypass_case.counterfactual_overrides),
                )
            ),
            {26},
        )

        # 5. The nonlethal projection follows the final direct amount: the
        # staged amount is what the projection consumes.
        protected = self._actor(PlayerCharacter, "nonlethal_target", hp=200, defense=20)
        protected.traits.hp.current = protected.traits.hp.base
        attacker, _ = self._pair(FACTOR_CASES[0], player_attacker=False)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=_FACTOR_BASE_ROLL),
            patch(
                "world.rules.combat.damage.evaluate_combat_modifiers", return_value={}
            ),
        ):
            pending = _handle_damage(
                attacker,
                [protected],
                "damage:none:physical",
                {"nonlethal": True},
                1.0,
            )[0]
        final_amount = int(pending.description.rsplit("|", 1)[1])
        self.assertEqual(final_amount, 40)
        pending.apply()
        self.assertEqual(protected.traits.hp.current, 160)
        self.assertEqual(
            nonlethal_projection(current=30.0, loss=final_amount), 1.0
        )
        self.assertTrue(crosses_knockout(current=30.0, loss=final_amount))

        # 6. Literal base traits, proficiency access, practice affinity and
        # strike count remain unchanged across the whole matrix.
        for case in FACTOR_CASES:
            attacker, defender = self._pair(case, player_attacker=True)
            before_attacker = self._literal_invariants(attacker)
            before_defender = self._literal_invariants(defender)
            amounts = self._stage(attacker, defender, case)
            expected_strikes = 2 if case.extra_strikes else 1
            self.assertEqual(len(amounts), expected_strikes)
            # Every case's own pair keeps its literal bases, its proficiency,
            # its affinity facts and its owned skills across the staging.
            self.assertEqual(self._literal_invariants(attacker), before_attacker)
            self.assertEqual(self._literal_invariants(defender), before_defender)

    @staticmethod
    def _literal_invariants(entity) -> tuple:
        traits = entity.traits
        skills = entity.db.skills or {}
        return (
            tuple(
                getattr(traits, name).base
                for name in (
                    "hp",
                    "mp",
                    "sp",
                    "atk_phys",
                    "magic_power",
                    "agility",
                    "defense",
                )
            ),
            dict(entity.db.skill_proficiency or {}),
            list(entity.db.affinity_elements or []),
            {
                key: tuple(value) if isinstance(value, (list, tuple)) else value
                for key, value in skills.items()
            },
        )

    @covers_requirement(
        "human-combat-calibration::combined-ratio-weapon-and-tactical-calibration-covers-both-combat-sides",
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence",
        "monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement",
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor",
    )
    def test_estimator_and_settlement_agree_on_the_authored_factor(self):
        # Cross-path parity at the factor boundary with real shipped gear: the
        # estimator's own read path reports the same authored declaration the
        # settlement read path consumes, and its analytic projection for the
        # fixed matchup equals the settled average over all 100 faces -- each
        # against an independently hand-derived literal.
        from world.rules.monster_ai import (
            DecisionReads,
            DecisionScope,
            build_decision_snapshot,
            enumerate_candidates,
            estimate_candidates,
            roster_index,
            stable_identity,
        )

        skill_key = "basic_swordplay"  # damage:none:physical, coefficient 1.0
        # Hand-derived settled averages for the fixed matchup (monster attack
        # 40 base, target hp 500 / defense 10 / agility 20, defender threshold
        # 71, ratio retention 40 / 50 = 0.8):
        #   unarmed:      margin = roll - 61, so faces 61..99 land 32 and the
        #                 raw-100 critical lands 64 -> (39x32 + 64) / 100.
        #   plain_sword:  +2 atk, factor 1.05 -> attack 42, base 35, crit 70.
        #   military_s:   +12 atk and +4 agility (adjusted agility 14, so the
        #                 margin is roll - 57 and the solid band is 97..99),
        #                 attack 52, factor 1.25 -> base 52, solid 78, crit 104.
        expectations = {
            None: 13.12,
            _AUTHORED_INITIAL_WEAPON: 14.35,
            _AUTHORED_SELECTED_WEAPON: 24.18,
        }
        monster = self._actor(Monster, "parity_attacker", attack=40, agility=10)
        monster.db.skills = {"active": [skill_key], "passive": []}
        target = self._actor(PlayerCharacter, "parity_target", hp=500, defense=10, agility=20)
        context = BattlefieldActionContext(
            Battlefield(
                {
                    "attackers": frozenset({str(monster.key)}),
                    "defenders": frozenset({str(target.key)}),
                },
                {str(monster.key): monster, str(target.key): target},
            ),
            event_context={"simulated": True},
        )
        roster = roster_index((monster, target))

        for weapon_key, expected in expectations.items():
            with self.subTest(weapon=weapon_key):
                if weapon_key is None:
                    monster.db.equipment = dict(
                        monster.db.equipment, weapon_main=None
                    )
                else:
                    from world.rules.equipment import add_item, toggle_equipment

                    add_item(monster, weapon_key)
                    self.assertEqual(
                        toggle_equipment(monster, weapon_key).outcome, "success"
                    )
                # A fresh read set per state, so the estimator's memoized
                # factor read is taken against the currently equipped gear.
                reads = DecisionReads()
                snapshot = build_decision_snapshot(
                    monster,
                    context,
                    scope=DecisionScope("factor-parity:0:0", 0, 0),
                    participants=(target,),
                    reads=reads,
                )
                candidates = enumerate_candidates(
                    snapshot,
                    actor=monster,
                    context=context,
                    roster=roster,
                    reads=reads,
                )
                estimates = estimate_candidates(
                    candidates,
                    snapshot=snapshot,
                    actor=monster,
                    context=context,
                    roster=roster,
                    reads=reads,
                )
                estimate = next(
                    item
                    for item in estimates.estimates
                    if item.identity.skill_key == skill_key
                )
                projection = next(
                    item
                    for item in estimate.recipients
                    if item.identity == stable_identity(target)
                )
                # The estimator's read path reports exactly the declaration the
                # settlement read path consumes (one authored source, no
                # duplicated balance constant).
                self.assertEqual(
                    reads.weapon_multiplier(monster),
                    equipment_weapon_multiplier(monster),
                )
                settled = 0.0
                for face in range(1, 101):
                    target.traits.hp.current = target.traits.hp.base
                    monster.traits.sp.current = monster.traits.sp.base
                    with patch(
                        "world.rules.combat.damage.roll_d100", return_value=face
                    ):
                        result = ActionResolver.resolve(
                            ActionRequest(
                                monster, skill_key, [target], context, scale=1.0
                            )
                        )
                    self.assertEqual(result.outcome, "success", result.detail)
                    settled += target.traits.hp.base - _stored_hp(target)
                self.assertAlmostEqual(settled / 100, expected, places=4)
                self.assertAlmostEqual(projection.damage, expected, places=4)


# ---------------------------------------------------------------------------
# Combined player/enemy encounter calibration
# (party-combat-encounter-calibration, change 19 of the party-combat batch)
# ---------------------------------------------------------------------------

#: The exact seeds every encounter cell runs: eight cells x four seeds is the
#: bounded 32-trial pass the batch contract fixes.
CALIBRATION_SEEDS: tuple[int, ...] = (0, 1, 2, 3)
#: The same 200-round bound the preceding calibration probes used.
CALIBRATION_MAX_ROUNDS = 200
#: The three-member party's fixed round-start tactical rounds (1-based round
#: number -> (member index, tactical key)). Each declaration consumes that
#: member's action for the round and is admitted through the draft facade's
#: own tactical entry kind, never as an ordinary action.
_D_PARTY_TACTICAL_ROUNDS: dict[int, tuple[int, str]] = {
    2: (0, "defend"),
    3: (1, "dodge"),
    4: (2, "taunt"),
}
#: The supporter's own-inventory consumable, granted through the ordinary
#: inventory rule so the item selection is a real held-item use.
_D_PARTY_ITEM = "healing_potion"
#: The explicit attack chain every scripted ally selects from, in order. The
#: first affordable permitted entry wins; ``basic_attack`` is the legal
#: default and the chain is the same order the preceding probes selected with.
_ENCOUNTER_ATTACK_CHAIN = (
    "true_sword_saint",
    "blade_saint_arts",
    "thousand_blade_art",
    "tendon_sever",
    "flowing_strikes",
    "basic_swordplay",
)


@dataclass(frozen=True)
class EncounterCell:
    """One named human-only encounter cell of the bounded eight-cell set."""

    label: str
    #: Restriction rank; ``None`` selects the F-rank creation kit build.
    rank: str | None
    #: How many allied humans fight in this cell (1 or the D party's 3).
    party_size: int
    #: The monster factory tag this cell faces.
    monster: str
    #: ``True`` keeps the real enemy behaviour policy (its own flee policy);
    #: ``False`` supplies a deterministic basic-attack enemy, exactly as the
    #: preceding stand-and-fight probes did.
    real_enemy_policy: bool = False


#: The eight existing human-only encounter cells. No new species, elf/beastfolk
#: target or calamity cell is added, and the two high probes stay unshipped.
ENCOUNTER_CELLS: tuple[EncounterCell, ...] = (
    EncounterCell("F_creation_kit_vs_grain_pecker", None, 1, "grain_pecker"),
    EncounterCell("E_senior_vs_E_ordinary", "E", 1, "shore_walker"),
    EncounterCell("D_party_vs_D_ordinary", "D", 3, "wood_stalker"),
    EncounterCell("C_senior_vs_C_ordinary", "C", 1, "cliff_stepper", True),
    EncounterCell("B_senior_vs_B_ordinary", "B", 1, "bank_lurker"),
    EncounterCell("B_senior_vs_high_lower_probe", "B", 1, "high_lower"),
    EncounterCell("B_senior_vs_high_upper_probe", "B", 1, "high_upper"),
    EncounterCell("S_senior_vs_high_upper_probe", "S", 1, "high_upper"),
)


@dataclass(frozen=True)
class EncounterOutcome:
    """One bounded encounter trial's recorded outcome taxonomy."""

    cell: str
    seed: int
    rounds: int
    monster_defeated: bool
    monster_retreated: bool
    ally_loss: bool
    all_standing: bool
    unfinished: bool
    rejected: tuple[str, ...]
    final_ally_hps: tuple[int, ...]
    final_monster_hp: int
    #: Rounds whose resolution carried the simulation marker.
    simulated_rounds: int
    #: Rounds whose provider was the session's draft-derived party provider.
    draft_rounds: int
    #: Every ally's practice/skill/declared-base surfaces were unchanged.
    growth_frozen: bool
    #: The balance values this pass consumed, read through their real
    #: consumer sources: ratio mitigation K, the Defend reduction, the Dodge
    #: threshold bonus, and each ally's worn weapon factor.
    balance_values: tuple[float, float, float, tuple[float, ...]]
    #: Enemy decisions taken through the shipped ``monster_behaviour_policy``
    #: and through the deterministic stand-and-fight policy, respectively.
    real_enemy_decisions: int
    deterministic_enemy_decisions: int


def _build_encounter_monster(cell: EncounterCell, room: Room) -> Monster:
    """Build the cell's monster from its factory tag."""
    if cell.monster == "grain_pecker":
        monster = construct_species_individual("sway_whistle_sparrow", "grain_pecker")
    elif cell.monster == "shore_walker":
        monster = construct_species_individual("tide_lamp_crab", "shore_walker")
    elif cell.monster == "wood_stalker":
        monster = construct_species_individual("fog_mane_lynx", "wood_stalker")
    elif cell.monster == "cliff_stepper":
        monster = construct_species_individual("rock_echo_goat", "cliff_stepper")
    elif cell.monster == "bank_lurker":
        monster = construct_species_individual("tide_devouring_crocodile", "bank_lurker")
    elif cell.monster == "high_lower":
        monster = _build_synthetic_probe_monster(
            "high_lower", hp=320, attack=28, agility=18, defense=20
        )
    elif cell.monster == "high_upper":
        monster = _build_synthetic_probe_monster(
            "high_upper", hp=700, attack=38, agility=26, defense=28
        )
    else:  # pragma: no cover - a cell tag outside this bounded set is a bug
        raise AssertionError(f"unknown encounter monster tag {cell.monster!r}")
    monster.location = room
    return monster


def _build_encounter_ally(cell: EncounterCell, room: Room, index: int) -> NPC:
    """Build one cell ally: the F creation kit, or a restricted senior."""
    key = f"{cell.label}_{index}"
    if cell.rank is None:
        profile = resolve_starting_profile("human", "human_plains")
        values = _resolve_values(
            profile,
            {
                "hp": 69, "mp": 69, "sp": 69,
                "atk_phys": 4, "agility": 4, "defense": 4,
                "magic_power": 5,
            },
        )
        human = create_object(NPC, key=key, location=room)
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

    from world.rules.guild_exam_restrictions import PROFILES

    rank = cell.rank
    prof = PROFILES[rank]
    human = create_object(NPC, key=key, location=room)
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
    inventory = [prof.weapon, prof.armor]
    if prof.accessory:
        inventory.append(prof.accessory)
    human.db.inventory = inventory
    human.db.equipment = {
        "weapon_main": prof.weapon,
        "weapon_off": None,
        "armor": prof.armor,
        "accessories": [],
    }
    human.db.skills = {"active": list(prof.allowed_skills), "passive": []}
    apply_lineage_auto_seed(human)
    preflight_exam_restriction(human, rank)
    activate_exam_restriction(human, f"exam_{rank}_{human.pk}", rank)
    return human


def _own_attack_skill(ally: Any) -> str:
    """Return the first affordable permitted attack of the explicit chain."""
    record = exam_restriction(ally)
    allowed = record["allowed_skills"] if record else ally.skills.owned_keys()
    for skill_key in _ENCOUNTER_ATTACK_CHAIN:
        if skill_key not in allowed or not can_use_skill(ally, SKILL_REGISTRY[skill_key]):
            continue
        cost = SKILL_REGISTRY[skill_key].cost
        if all(
            _stored_trait_value(getattr(ally.traits, resource)) >= amount
            for resource, amount in cost.items()
        ):
            return skill_key
    return BASIC_ATTACK_KEY


#: The rounds (1-based) the party's supporter offers its own inventory item.
#: Two turns inside the first cycle, so the item selection is exercised
#: without ever submitting a use whose consumable is already spent.
_D_PARTY_ITEM_ROUNDS = (2, 5)


def _item_turn(
    ally: Any, battlefield: Battlefield, record: CombatSessionRecord
) -> dict[str, Any] | None:
    """Return the supporter's own-inventory item selection, or ``None``.

    The script consults the same public item preflight the facade enforces, so
    the selection it submits is a real legal use: the consumable-targeting
    choice is the party's most wounded living member, exactly the command a
    player would issue.
    """
    party_keys = battlefield.teams.get(battlefield.team_of(str(ally.key)), frozenset())
    candidates = [
        battlefield.roster[key]
        for key in party_keys
        if key in battlefield.roster
        and not battlefield.is_knocked_out(key)
        and _stored_hp(battlefield.roster[key]) > 0
    ]
    if not candidates:
        return None
    target = min(candidates, key=lambda e: (_stored_hp(e), str(e.key)))
    preflight = preflight_item_use(
        ItemUseRequest(actor=ally, item_key=_D_PARTY_ITEM, target=target),
        in_combat=True,
        context=_context_for(battlefield, record),
    )
    if not preflight.allowed:
        return None
    return {"kind": "item", "item_key": _D_PARTY_ITEM, "target": target}


def _encounter_command(
    cell: EncounterCell,
    member_index: int,
    round_number: int,
    ally: Any,
    monster: Monster,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> dict[str, Any]:
    """Return one allied actor's explicit bounded selection for this round.

    The script's default is a legal attack picked from the actor's own
    permitted chain; the three-member party additionally declares its fixed
    tactical actions on rounds 2-4 and alternates one supporter-owned skill
    turn and its own-inventory item turns between its other explicit attacks.
    Every branch returns a real selection; an ineligible selection is never
    silently replaced.
    """
    if cell.party_size == 3:
        tactical = _D_PARTY_TACTICAL_ROUNDS.get(round_number)
        if tactical is not None and tactical[0] == member_index:
            k_action = tactical[1]
            return {
                "kind": "tactical",
                "tactical_key": k_action,
                "target_id": int(monster.pk) if k_action == "taunt" else None,
                "target": None,
            }
        if member_index == 1 and round_number % 3 == 0:
            return {
                "kind": "skill",
                "skill_key": _own_attack_skill(ally),
                "target": monster,
            }
        if member_index == 2 and round_number in _D_PARTY_ITEM_ROUNDS:
            item_selection = _item_turn(ally, battlefield, record)
            if item_selection is not None:
                return item_selection
    return {"kind": "skill", "skill_key": _own_attack_skill(ally), "target": monster}


def _submit_encounter_command(
    commander: Any, ally: Any, command: dict[str, Any]
) -> dict[str, Any]:
    """Submit one selection through the real persistent-draft facade."""
    if command["kind"] == "tactical":
        record = read_session(commander)
        return confirm_actor_command(
            commander,
            record.session_id,
            record.round_revision,
            record.draft_version,
            int(ally.pk),
            {
                "kind": "tactical",
                "payload": {
                    "tactical_key": command["tactical_key"],
                    "target_id": command["target_id"],
                },
            },
        )
    if command["kind"] == "item":
        return submit_player_item_use(
            commander,
            command["item_key"],
            target=command["target"],
            commanded_actor=ally,
        )
    return submit_player_action(
        commander, command["skill_key"], [command["target"]], commanded_actor=ally
    )


def _deterministic_enemy_policy(entity, battlefield, *, context=None, scale=1.0, decision=None):
    """Return the stand-and-fight enemy action the earlier probes pinned.

    The enemy keeps its ordinary policy boundary: it picks a legal basic
    attack against the lowest-HP living ally. Only the cell that owns the real
    flee policy keeps ``monster_behaviour_policy``.

    ``_enemy_policy`` also passes the authored cast ``scale`` and the recorded
    AI ``decision``; a plain basic attack consumes neither, so both are
    accepted and deliberately unused here.
    """
    enemy_keys = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != battlefield.team_of(str(entity.key))
        ),
        frozenset(),
    )
    candidates = [
        battlefield.roster[key]
        for key in enemy_keys
        if key in battlefield.roster
        and not battlefield.is_knocked_out(key)
        and _stored_hp(battlefield.roster[key]) > 0
    ]
    if not candidates:
        return None
    target = min(candidates, key=lambda e: (_stored_hp(e), str(e.key)))
    return ActionRequest(entity, BASIC_ATTACK_KEY, [target], context)


def _invariant_snapshot(allies: list[Any], monster: Monster) -> tuple:
    """Return every surface a simulated trial must leave untouched."""
    return (
        tuple(
            (
                ally.key,
                tuple(sorted((ally.db.skill_proficiency or {}).items())),
                tuple(sorted((ally.db.skills or {}).get("active") or ())),
                (ally.traits.hp.base, ally.traits.atk_phys.base, ally.traits.agility.base),
            )
            for ally in allies
        ),
        (monster.traits.hp.base, monster.traits.atk_phys.base),
    )


def _run_encounter_trial(room: Room, cell: EncounterCell, seed: int) -> EncounterOutcome:
    """Run one bounded encounter cell trial through the persistent draft.

    Every allied actor's selection is admitted through the real draft facade
    (``submit_player_action`` / ``submit_player_item_use`` / the tactical
    admission), so an ally acts only from a submitted command -- the round
    resolves through the session's own draft-derived provider and no
    autonomous allied fallback exists. The simulation marker is applied to
    every resolved round, so ordinary growth, unlocks and rewards are frozen.
    """
    random.seed(seed)
    commander = _build_encounter_ally(cell, room, 0)
    allies = [commander]
    for index in range(1, cell.party_size):
        ally = _build_encounter_ally(cell, room, index)
        join_party(ally, commander)
        if index == 2:
            # Two real consumables: the supporter's own inventory covers both
            # of its item turns without ever offering a spent one.
            add_item(ally, _D_PARTY_ITEM)
            add_item(ally, _D_PARTY_ITEM)
        allies.append(ally)
    monster = _build_encounter_monster(cell, room)

    for ally in allies:
        ally.traits.hp.current = ally.traits.hp.base
        ally.traits.mp.current = ally.traits.mp.base
        ally.traits.sp.current = ally.traits.sp.base
    monster.traits.hp.current = monster.traits.hp.base

    before = _invariant_snapshot(allies, monster)
    record = CombatSessionRecord(
        session_id=f"encounter-{cell.label}-{seed}",
        mode="hostile",
        room_id=int(room.pk),
        player_ids=tuple(int(ally.pk) for ally in allies),
        enemy_ids=(int(monster.pk),),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id=None,
    )
    _persist(commander, record)

    from world.rules.combat_session import rounds as rounds_module

    real_run_round = rounds_module.run_round
    rejected: list[str] = []
    counters = {"rounds": 0, "simulated": 0, "draft": 0}
    battlefield: Battlefield | None = None
    last_round = None
    # A fleeing monster may settle the session inside the very round it fled,
    # which clears the durable record. The round's own battlefield is the one
    # authority that still carries this round's ``fled`` membership, so it is
    # read here rather than from a pre-round reconstruction.
    monster_fled = False

    def observing_run_round(field, provider, **kwargs):
        nonlocal monster_fled
        if kwargs.get("simulated") is True:
            counters["simulated"] += 1
        if callable(getattr(provider, "is_interactive_ally", None)):
            counters["draft"] += 1
        logs = real_run_round(field, provider, **kwargs)
        monster_fled = monster_fled or str(monster.key) in field.fled
        return logs

    simulated_policy = lambda battlefield, record: (True, frozenset())  # noqa: E731
    # A stand-and-fight cell supplies its enemy's deterministic basic attack
    # exactly as the preceding probes did. The cell that owns the real flee
    # policy resolves through the shipped ``monster_behaviour_policy`` itself,
    # so its retreat outcome is a real policy outcome rather than a fixture
    # choice -- and both paths are counted, so the recorded evidence says which
    # one produced the round.
    from world.rules.monster_behaviour import monster_behaviour_policy

    enemy_decisions = {"real": 0, "deterministic": 0}

    def real_enemy_policy(entity, battlefield, **kwargs):
        enemy_decisions["real"] += 1
        return monster_behaviour_policy(entity, battlefield, **kwargs)

    def deterministic_enemy_policy(entity, battlefield, **kwargs):
        enemy_decisions["deterministic"] += 1
        return _deterministic_enemy_policy(
            entity, battlefield, context=kwargs.get("context")
        )

    enemy_policy_patch = patch(
        "world.rules.combat_session.policies.monster_behaviour_policy",
        side_effect=(
            real_enemy_policy if cell.real_enemy_policy else deterministic_enemy_policy
        ),
    )
    with (
        patch(
            "world.rules.combat_session.battlefield._session_policy",
            side_effect=simulated_policy,
        ),
        patch(
            "world.rules.combat_session.rounds._session_policy",
            side_effect=simulated_policy,
        ),
        patch(
            "world.rules.combat_session.rounds.run_round",
            side_effect=observing_run_round,
        ),
        enemy_policy_patch,
    ):
        for _ in range(CALIBRATION_MAX_ROUNDS):
            current = read_session(commander)
            if current is None:
                break
            battlefield = reconstruct_battlefield(commander, current)
            if is_battle_over(battlefield):
                break
            required = _commandable_required_actors(commander, current, battlefield)
            if not required:
                break
            entities = {int(entity.pk): entity for entity in battlefield.roster.values()}
            round_number = counters["rounds"] + 1
            result: dict[str, Any] | None = None
            for pk in required:
                ally = entities[pk]
                command = _encounter_command(
                    cell,
                    allies.index(ally),
                    round_number,
                    ally,
                    monster,
                    battlefield,
                    current,
                )
                result = _submit_encounter_command(commander, ally, command)
                if result.get("outcome") == "rejected":
                    rejected.append(
                        f"{ally.key}:{result.get('reason')}"
                        f":hp={_stored_hp(ally)}/{ally.traits.hp.base}"
                        f":round={round_number}:command={command}"
                    )
                    break
            if result is None or result.get("outcome") == "rejected":
                break
            if result.get("outcome") == "draft":  # pragma: no cover - a bug
                raise AssertionError(f"the complete draft of {cell.label} did not resolve")
            if result.get("round_record") is not None:
                last_round = result["round_record"]
            counters["rounds"] += 1

    if battlefield is None:
        battlefield = reconstruct_battlefield(commander, read_session(commander))

    if last_round is not None:
        final_hps = tuple(int(last_round.hp_after[int(ally.pk)]) for ally in allies)
        final_monster_hp = int(last_round.hp_after[int(monster.pk)])
    else:
        final_hps = tuple(int(_stored_hp(ally)) for ally in allies)
        final_monster_hp = int(_stored_hp(monster))

    living_allies = [hp for hp in final_hps if hp > 0]
    monster_defeated = final_monster_hp <= 0
    monster_retreated = monster_fled or str(monster.key) in battlefield.fled
    ally_loss = not living_allies
    all_standing = len(living_allies) == len(allies)
    unfinished = not (monster_defeated or monster_retreated or ally_loss)

    balance_values = (
        float(COMBAT_YAML["damage"]["mitigation_k"]),
        float(COMBAT_YAML["tactics"]["defend_reduction"]),
        float(COMBAT_YAML["tactics"]["dodge_threshold_bonus"]),
        tuple(equipment_weapon_multiplier(ally) for ally in allies),
    )
    return EncounterOutcome(
        cell=cell.label,
        seed=seed,
        rounds=counters["rounds"],
        monster_defeated=monster_defeated,
        monster_retreated=monster_retreated,
        ally_loss=ally_loss,
        all_standing=all_standing,
        unfinished=unfinished,
        rejected=tuple(rejected),
        final_ally_hps=final_hps,
        final_monster_hp=final_monster_hp,
        simulated_rounds=counters["simulated"],
        draft_rounds=counters["draft"],
        growth_frozen=_invariant_snapshot(allies, monster) == before,
        balance_values=balance_values,
        real_enemy_decisions=enemy_decisions["real"],
        deterministic_enemy_decisions=enemy_decisions["deterministic"],
    )


class EncounterCalibrationTests(EvenniaTest):
    """The eight-cell combined player/enemy encounter calibration."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="encounter_calibration_room")

    def _run_all_cells(self) -> list[EncounterOutcome]:
        """Run the eight cells over seeds 0-3: exactly 32 bounded trials."""
        return [
            _run_encounter_trial(self.room, cell, seed)
            for cell in ENCOUNTER_CELLS
            for seed in CALIBRATION_SEEDS
        ]

    def _assert_recorded_evidence(self, outcomes: list[EncounterOutcome]) -> None:
        """Assert every recorded evidence property of one 32-trial pass.

        Each trial establishes action validity, the simulation marker, the
        absence of an autonomous allied provider, a complete outcome taxonomy
        and a bounded round median -- never a pinned balance outcome, so there
        is no seeded victory band.
        """
        self.assertEqual(len(outcomes), len(ENCOUNTER_CELLS) * len(CALIBRATION_SEEDS))
        for outcome in outcomes:
            with self.subTest(cell=outcome.cell, seed=outcome.seed):
                self.assertEqual(
                    outcome.rejected, (), "every scripted command must resolve"
                )
                self.assertGreater(outcome.rounds, 0, "a bounded run executes")
                self.assertLessEqual(outcome.rounds, CALIBRATION_MAX_ROUNDS)
                self.assertEqual(
                    outcome.simulated_rounds,
                    outcome.rounds,
                    "every round carries the simulation marker",
                )
                self.assertEqual(
                    outcome.draft_rounds,
                    outcome.rounds,
                    "allies act only from submitted draft commands",
                )
                self.assertTrue(
                    outcome.growth_frozen,
                    "simulation freezes growth, unlocks and ordinary rewards",
                )
                self.assertEqual(
                    sum(
                        (
                            outcome.monster_defeated,
                            outcome.monster_retreated,
                            outcome.ally_loss,
                            outcome.unfinished,
                        )
                    ),
                    1,
                    "defeat, retreat, loss and unfinished are distinct outcomes",
                )
                self.assertFalse(
                    outcome.unfinished,
                    "the measured cells all reach a terminal outcome",
                )
                real_policy_cell = next(
                    cell for cell in ENCOUNTER_CELLS if cell.label == outcome.cell
                ).real_enemy_policy
                if real_policy_cell:
                    self.assertGreater(
                        outcome.real_enemy_decisions,
                        0,
                        "the fleeing cell resolves through the shipped policy",
                    )
                    self.assertEqual(outcome.deterministic_enemy_decisions, 0)
                else:
                    self.assertEqual(outcome.real_enemy_decisions, 0)
                    self.assertGreater(
                        outcome.deterministic_enemy_decisions,
                        0,
                        "a stand-and-fight cell supplies its own enemy action",
                    )
        for cell in ENCOUNTER_CELLS:
            rounds = sorted(
                outcome.rounds for outcome in outcomes if outcome.cell == cell.label
            )
            middle = len(rounds) // 2
            median = (
                rounds[middle]
                if len(rounds) % 2
                else (rounds[middle - 1] + rounds[middle]) / 2
            )
            self.assertGreaterEqual(median, 1, "the round median is a real run")
            self.assertLessEqual(median, CALIBRATION_MAX_ROUNDS)

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    @covers_requirement(
        "human-combat-calibration::evidence-separates-defeat-retreat-support-safety-and-unverified-projections"
    )
    def test_eight_encounter_cells_run_explicit_draft_commands_over_four_seeds(self):
        self._assert_recorded_evidence(self._run_all_cells())

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    @covers_requirement(
        "human-combat-calibration::combined-ratio-weapon-and-tactical-calibration-covers-both-combat-sides"
    )
    def test_selected_values_reproduce_the_measured_encounter_outcomes(self):
        # The tuning evaluation found no observed combined result that required
        # a rebalance, so every eligible authored value is retained and the
        # selected-value pass runs with the same values the baseline pass
        # measured. The pass records the values it consumed through their real
        # consumer sources and reproduces the recorded taxonomy and round
        # counts exactly -- a deterministic comparison, not a new balance pin.
        baseline = self._run_all_cells()
        self._assert_recorded_evidence(baseline)
        selected = self._run_all_cells()
        self._assert_recorded_evidence(selected)
        for expected, actual in zip(baseline, selected, strict=True):
            with self.subTest(cell=expected.cell, seed=expected.seed):
                self.assertEqual(actual.balance_values, expected.balance_values)
                self.assertEqual(
                    (
                        actual.rounds,
                        actual.monster_defeated,
                        actual.monster_retreated,
                        actual.ally_loss,
                        actual.all_standing,
                        actual.unfinished,
                        actual.rejected,
                        actual.final_ally_hps,
                        actual.final_monster_hp,
                    ),
                    (
                        expected.rounds,
                        expected.monster_defeated,
                        expected.monster_retreated,
                        expected.ally_loss,
                        expected.all_standing,
                        expected.unfinished,
                        expected.rejected,
                        expected.final_ally_hps,
                        expected.final_monster_hp,
                    ),
                )

    @covers_requirement(
        "human-combat-calibration::human-calibration-uses-real-resolver-gear-restrictions-and-bounded-outcome-evidence"
    )
    def test_an_ally_without_a_submitted_command_never_auto_attacks(self):
        # No autonomous allied fallback: with a companion's command missing the
        # draft stays incomplete, the round does not resolve, and the
        # companion neither attacks nor is attacked.
        cell = ENCOUNTER_CELLS[2]
        commander = _build_encounter_ally(cell, self.room, 0)
        companion = _build_encounter_ally(cell, self.room, 1)
        join_party(companion, commander)
        monster = _build_encounter_monster(cell, self.room)
        monster.traits.hp.current = monster.traits.hp.base
        record = CombatSessionRecord(
            session_id=f"encounter-{cell.label}-no-command",
            mode="hostile",
            room_id=int(self.room.pk),
            player_ids=(int(commander.pk), int(companion.pk)),
            enemy_ids=(int(monster.pk),),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )
        _persist(commander, record)
        simulated_policy = lambda battlefield, record: (True, frozenset())  # noqa: E731
        with (
            patch(
                "world.rules.combat_session.battlefield._session_policy",
                side_effect=simulated_policy,
            ),
            patch(
                "world.rules.combat_session.rounds._session_policy",
                side_effect=simulated_policy,
            ),
        ):
            result = submit_player_action(
                commander,
                _own_attack_skill(commander),
                [monster],
                commanded_actor=commander,
            )
        self.assertEqual(result["outcome"], "draft", result)
        after = read_session(commander)
        self.assertEqual(after.rounds_elapsed, 0)
        self.assertEqual(monster.traits.hp.current, monster.traits.hp.base)
        self.assertEqual(
            companion.traits.hp.current, int(companion.traits.hp.max)
        )




