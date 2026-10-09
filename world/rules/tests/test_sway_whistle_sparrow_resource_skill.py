"""Data-contract test: sparrow resource skill production combat smoke contract

Formally constructs both ``sway_whistle_sparrow`` variants through the one
production entry point and drives real provider/resolver-backed combat sessions
through the shipped ``grain_shaking_peck`` kit: deterministic hit and miss, the
absorbed-hit rider, mount refresh and expiry, both exhaustion axes falling back
to a resolved ``basic_attack``, the inclusive 0.35 flee threshold, a late
failure rolling every staged surface back, and a depleted-gauge reload. The
only synthetic fixture is the target-side full damage-diversion mount that makes
an absorbed hit observable (the shipped kit has no divert); no live generative
or image service is called anywhere here.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver
from world.rules.buffs import (
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.buffs.definitions import BuffDefinition
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.combat_session.lifecycle import clear_session, engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    resolve_behaviour_profile,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.progression import practice_claims_for
from world.skills.registry import SKILL_REGISTRY

SKILL_KEY = "grain_shaking_peck"
BUFF_KEY = "grain_rattle"

#: The target-side full diversion that makes "hit but fully absorbed"
#: observable: every residual HP point is moved onto the target's MP, so the
#: strike still records a hit while HP does not move.
_ABSORB_MOUNT = BuffDefinition(
    key="t_sparrow_smoke_absorb",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    modifiers={"divert": {"target": "mp", "fraction": 1.0, "cap": 999}},
    polarity="buff",
)


def _buff_instances(entity, definition_key: str) -> list:
    """Every live buff instance of one definition key on an entity."""
    return [
        buff
        for buff in getattr(entity, "buffs", None).all.values()
        if buff.definition_key == definition_key
    ]


class SwayWhistleSparrowResourceSkillSmokeTests(EvenniaTestCase):
    """Production combat smoke test for the sparrow resource skill."""

    def _opponent(self, room: Room) -> PlayerCharacter:
        """One controlled valid opponent that survives the whole session."""
        player = create_object(PlayerCharacter, key="sparrow_target")
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 500
        player.traits.hp.current = 500
        player.traits.mp.base = 100
        player.traits.mp.current = 100
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        player.location = room
        return player

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-individual-construction::the-construction-entry-point-validates-the-declared-kit-and-behavior-binding",
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals",
        "monster-species-registry::variant-skill-kits-and-behavior-references-are-immutable-authored-configuration",
        "monster-flee-policy::every-monster-behaviour-archetype-declares-a-validated-flee-threshold",
        "skill-identity-eligibility::stored-identity-determines-actor-qualification",
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits",
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback",
    )
    def test_production_sparrow_variants_combat_buff_and_reload(self):
        # 1. Formally construct BOTH variants through the production entry point.
        pecker = construct_species_individual("sway_whistle_sparrow", "grain_pecker")
        leader = construct_species_individual("sway_whistle_sparrow", "flock_leader")
        for monster, expected in (
            (pecker, (30, 20, 8, 4, 7, 3, 0, "F")),
            (leader, (55, 30, 12, 8, 10, 4, 0, "E")),
        ):
            with self.subTest(variant=monster.variant_key):
                traits = monster.traits
                self.assertEqual(
                    (
                        traits.hp.current,
                        traits.mp.current,
                        traits.sp.current,
                        traits.atk_phys.base,
                        traits.agility.base,
                        traits.defense.base,
                        traits.magic_power.base,
                        monster.danger_grade,
                    ),
                    expected,
                )
                self.assertEqual(
                    monster.db.skills, {"active": [SKILL_KEY], "passive": []}
                )
                self.assertEqual(monster.db.behaviour_tree, "instinctive")
                # The special ability precedes both innate actions (the
                # handler appends unlocked sexual acts after this base set).
                self.assertEqual(
                    monster.skills.base_owned_keys(),
                    [SKILL_KEY, "flee", "basic_attack"],
                )
                self.assertEqual(
                    monster.skills.owned_keys()[:3],
                    [SKILL_KEY, "flee", "basic_attack"],
                )
                profile = resolve_behaviour_profile(monster)
                self.assertIs(profile, BEHAVIOUR_PROFILES["instinctive"])
                self.assertEqual(profile.skill_choice, "first_owned")
                self.assertEqual(profile.target_strategy, "lowest_hp")
                self.assertFalse(profile.prefer_area_when_multiple_enemies)
                self.assertEqual(profile.flee_hp_fraction, 0.35)

        # 2. One controlled valid opponent, one real hostile session.
        room = create_object(Room, key="grain_field")
        player = self._opponent(room)
        pecker.location = room
        engage(player, pecker)
        record = read_session(player)
        battlefield = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({pecker.key})},
            {player.key: player, pecker.key: pecker},
        )

        # 3. The production policy selects the owned special ability.
        miss_request = _enemy_policy(pecker, battlefield, record)
        self.assertEqual(miss_request.skill_key, SKILL_KEY)
        self.assertEqual(miss_request.targets, [player])

        # 4. Deterministic miss: no rider, both resources still paid.
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            miss = ActionResolver.resolve(miss_request)
        self.assertEqual(miss.outcome, "success")
        self.assertEqual(player.traits.hp.current, 500)
        self.assertNotIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(pecker.traits.mp.current, 10)
        self.assertEqual(pecker.traits.sp.current, 6)

        # 5. Deterministic hit: physical HP loss, the authored mount and its
        #    accuracy modifier, and the exact nominal costs.
        hit_request = _enemy_policy(pecker, battlefield, record)
        self.assertEqual(hit_request.skill_key, SKILL_KEY)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            hit = ActionResolver.resolve(hit_request)
        self.assertEqual(hit.outcome, "success")
        # 500 - 3: roll 80 with agility 7 gives margin 26, below
        # combat.yaml's solid_hit_margin 40, so the base multiplier applies:
        # round(4 atk_phys * 1.0 * 0.8 coefficient) = 3 over defense 0.
        self.assertEqual(player.traits.hp.current, 497)
        self.assertIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(evaluate_combat_modifiers(player)["accuracy"], -3)
        self.assertEqual(pecker.traits.mp.current, 0)
        self.assertEqual(pecker.traits.sp.current, 4)

        # 6. Refresh before expiry: one instance, the literal magnitude and a
        #    restored lifetime (no stacking, no extra instance).
        pecker.traits.mp.current = pecker.traits.mp.base
        pecker.traits.sp.current = pecker.traits.sp.base
        refresh_request = _enemy_policy(pecker, battlefield, record)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            refreshed = ActionResolver.resolve(refresh_request)
        self.assertEqual(refreshed.outcome, "success")
        self.assertEqual(player.traits.hp.current, 494)
        instances = _buff_instances(player, BUFF_KEY)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].remaining_seconds, 10)
        self.assertEqual(evaluate_combat_modifiers(player)["accuracy"], -3)

        # 7. A late failure after staged damage, rider and costs restores every
        #    touched surface and releases the same-tick practice claim.
        pecker.traits.mp.current = pecker.traits.mp.base
        pecker.traits.sp.current = pecker.traits.sp.base
        before = (
            player.traits.hp.current,
            player.traits.mp.current,
            pecker.traits.mp.current,
            pecker.traits.sp.current,
            len(entity_active_buffs(player)),
            len(_buff_instances(player, BUFF_KEY)),
        )
        claims_before = len(practice_claims_for(pecker, SKILL_KEY))
        failing_request = _enemy_policy(pecker, battlefield, record)
        with patch(
            "world.rules.action.resolver._commit",
            side_effect=RuntimeError("injected late failure"),
        ):
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                with self.assertRaises(RuntimeError):
                    ActionResolver.resolve(failing_request)
        self.assertEqual(
            (
                player.traits.hp.current,
                player.traits.mp.current,
                pecker.traits.mp.current,
                pecker.traits.sp.current,
                len(entity_active_buffs(player)),
                len(_buff_instances(player, BUFF_KEY)),
            ),
            before,
        )
        self.assertEqual(
            len(practice_claims_for(pecker, SKILL_KEY)), claims_before
        )

        # 8. Absorbed hit: zero residual HP damage still applies the rider once.
        pecker.traits.mp.current = pecker.traits.mp.base
        pecker.traits.sp.current = pecker.traits.sp.base
        with patch.dict(
            "world.rules.buffs.definitions.BUFF_DEFINITIONS",
            {_ABSORB_MOUNT.key: _ABSORB_MOUNT},
            clear=False,
        ):
            apply_buff(player, _ABSORB_MOUNT.key)
            hp_before_absorb = player.traits.hp.current
            mp_before_absorb = player.traits.mp.current
            absorb_request = _enemy_policy(pecker, battlefield, record)
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                absorbed = ActionResolver.resolve(absorb_request)
            self.assertEqual(absorbed.outcome, "success")
            self.assertEqual(player.traits.hp.current, hp_before_absorb)
            # The same 3 residual points move to MP under a 100% divert, so the
            # strike still records a hit while HP does not move.
            self.assertEqual(player.traits.mp.current, mp_before_absorb - 3)
            self.assertIn(BUFF_KEY, entity_active_buffs(player))
            self.assertEqual(evaluate_combat_modifiers(player)["accuracy"], -3)
            self.assertIn(_ABSORB_MOUNT.key, entity_active_buffs(player))
            self.assertEqual(pecker.traits.mp.current, 10)
            self.assertEqual(pecker.traits.sp.current, 6)

        # 9. Expiry: the modifier is absent once the refreshed lifetime passes.
        tick_buffs(player, 6)
        self.assertIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(
            _buff_instances(player, BUFF_KEY)[0].remaining_seconds, 4
        )
        tick_buffs(player, 4)
        self.assertNotIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(evaluate_combat_modifiers(player).get("accuracy", 0), 0)

        # 10. MP exhaustion falls back to a resolved ordinary attack.
        pecker.traits.mp.current = 0
        pecker.traits.sp.current = 4
        drained = _enemy_policy(pecker, battlefield, record)
        self.assertEqual(drained.skill_key, "basic_attack")
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            drained_result = ActionResolver.resolve(drained)
        self.assertEqual(drained_result.outcome, "success")
        self.assertEqual(pecker.traits.mp.current, 0)
        self.assertEqual(pecker.traits.sp.current, 4)

        # 11. SP exhaustion falls back the same way.
        pecker.traits.mp.current = 20
        pecker.traits.sp.current = 1
        sp_drained = _enemy_policy(pecker, battlefield, record)
        self.assertEqual(sp_drained.skill_key, "basic_attack")

        # 12. Scene prose and environment-looking facts are not mechanics: the
        #     same deterministic cast produces the identical delta after the
        #     room's description is rewritten with fog/loose-stone prose, and
        #     the declaration carries no cast condition to read one.
        self.assertEqual(SKILL_REGISTRY[SKILL_KEY].cast_conditions, ())
        pecker.traits.mp.current = 20
        pecker.traits.sp.current = 8
        room.db.desc = "濃霧與鬆動碎石遍地，穀物半濕地散落在田埂上。"
        hp_before_prose = player.traits.hp.current
        prose_request = _enemy_policy(pecker, battlefield, record)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            prose_result = ActionResolver.resolve(prose_request)
        self.assertEqual(prose_result.outcome, "success")
        self.assertEqual(player.traits.hp.current, hp_before_prose - 3)

        # 13. Identity and affordability reject before any dice, costs, rider
        #     or practice: an ineligible owner and an under-resourced caster.
        context = BattlefieldActionContext(battlefield)
        corrupt = create_object(PlayerCharacter, key="corrupt_holder")
        corrupt.race = "human"
        corrupt.apply_race_baseline()
        corrupt.traits.mp.current = 100
        corrupt.traits.sp.current = 100
        corrupt.location = room
        corrupt.db.skills = {"active": [SKILL_KEY], "passive": []}
        instances_before_rejection = len(_buff_instances(player, BUFF_KEY))
        sp_before_rejection = pecker.traits.sp.current
        with patch("world.rules.combat.damage.roll_d100") as roller:
            identity_result = ActionResolver.resolve(
                ActionRequest(corrupt, SKILL_KEY, [player], context)
            )
            self.assertEqual(identity_result.outcome, "rejected")
            pecker.traits.mp.current = 9
            under_resourced = ActionResolver.resolve(
                ActionRequest(pecker, SKILL_KEY, [player], context)
            )
            self.assertEqual(under_resourced.outcome, "rejected")
            roller.assert_not_called()
        self.assertEqual(
            len(_buff_instances(player, BUFF_KEY)), instances_before_rejection
        )
        self.assertEqual(evaluate_combat_modifiers(player)["accuracy"], -3)
        self.assertEqual(pecker.traits.mp.current, 9)
        self.assertEqual(pecker.traits.sp.current, sp_before_rejection)

        # 14. Inclusive flee threshold: exactly 0.35 disengages, above it the
        #     kit acts, and the request resolves through the shared resolver.
        pecker.traits.mp.current = 20
        pecker.traits.sp.current = 8
        pecker.traits.hp.base = 20
        pecker.traits.hp.current = 7
        self.assertEqual(
            _enemy_policy(pecker, battlefield, record).skill_key, FLEE_SKILL_KEY
        )
        pecker.traits.hp.current = 8
        self.assertEqual(
            _enemy_policy(pecker, battlefield, record).skill_key, SKILL_KEY
        )
        pecker.traits.hp.current = 7
        flee_request = _enemy_policy(pecker, battlefield, record)
        self.assertEqual(flee_request.skill_key, FLEE_SKILL_KEY)
        self.assertEqual(flee_request.targets, [pecker])
        with patch("world.rules.disengage.roll_d100", return_value=100):
            fled = ActionResolver.resolve(flee_request)
        self.assertEqual(fled.outcome, "success")
        self.assertIn(pecker.key, battlefield.fled)

        # 15. Depleted production actors reload with identity, kit, binding and
        #     current gauges intact; construction does not recreate them.
        pecker.traits.hp.base = 30
        pecker.traits.hp.current = 30
        pecker.traits.mp.current = 3
        pecker.traits.sp.current = 2
        before_rows = Monster.objects.count()
        reloaded = Monster.objects.get(pk=pecker.pk)
        self.assertEqual(reloaded.species_key, "sway_whistle_sparrow")
        self.assertEqual(reloaded.variant_key, "grain_pecker")
        self.assertEqual(reloaded.db.skills, {"active": [SKILL_KEY], "passive": []})
        self.assertEqual(reloaded.db.behaviour_tree, "instinctive")
        self.assertEqual(reloaded.traits.mp.current, 3)
        self.assertEqual(reloaded.traits.sp.current, 2)
        self.assertEqual(Monster.objects.count(), before_rows)

        # 16. A late construction failure leaves no partial individual behind.
        from django.db import transaction

        rows_before_failure = Monster.objects.count()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                construct_species_individual("sway_whistle_sparrow", "grain_pecker")
                raise RuntimeError("injected construction failure")
        self.assertEqual(Monster.objects.count(), rows_before_failure)

        # 17. The second variant resolves the same kit through the same path.
        clear_session(player)
        leader.location = room
        engage(player, leader)
        record_leader = read_session(player)
        battlefield_leader = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({leader.key})},
            {player.key: player, leader.key: leader},
        )
        leader_request = _enemy_policy(leader, battlefield_leader, record_leader)
        self.assertEqual(leader_request.skill_key, SKILL_KEY)
        hp_before_leader = player.traits.hp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            leader_result = ActionResolver.resolve(leader_request)
        self.assertEqual(leader_result.outcome, "success")
        self.assertEqual(player.traits.hp.current, hp_before_leader - 6)
        self.assertIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(evaluate_combat_modifiers(player)["accuracy"], -3)
        self.assertEqual(leader.traits.mp.current, 20)
        self.assertEqual(leader.traits.sp.current, 10)
