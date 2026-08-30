"""Friendly-fire affinity penalty integration tests (affinity-friendly-fire).

Covers the deterministic per-hit penalty contract: a player combat action that
damages an ally-side companion NPC applies one ``friendly_fire`` negative delta
per hit through the sole affinity writer, inside the round's transaction
boundary with per-round membership snapshots, while non-player-action damage and
non-companion targets never write. Also covers the auto-leave integration (drop
below the invite threshold ends the party with the notification delivered only
after commit) and the snapshot/rollback guarantees.

The tests drive shipped attack skills (`basic_attack`, `fire_ball`,
`wind_blade`, `shadow_slash`) whose faction constraint is `ANY`, so the
penalty and auto-leave contracts are reachable through ordinary player
actions. A test-only double-hit skill covers the two-hits-on-one-target
scenarios no shipped skill expresses.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import affinity as affinity_module
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import load_config
from world.quests.catalog import register_catalog
from world.rules.combat_session import (
    _scan_friendly_fire,
    engage,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.party import AUTO_LEAVE_MESSAGE, PartyWriteError, join_party, party_ids
from .combat_fixtures import BattlefieldIsolation
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

# Test-only double-hit skill: no shipped skill damages the same target twice
# in one action, and the two-hits scenarios need exactly that shape.
FRIENDLY_DOUBLE = SkillDef(
    key="test_friendly_double",
    label="測試雙重誤傷",
    description="測試用：對單一目標造成兩次魔法傷害。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=False,
    element="fire",
    effects=["damage:fire:magic", "damage:fire:magic"],
    faction_constraint=FactionConstraint.ANY,
    category=SkillCategory.UTILITY,
)

_TEST_SKILLS = (FRIENDLY_DOUBLE,)


def _player(key="friendly fire player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Human static magic_power at 術師 tier so element-gated spell casts pass.
    player.traits.magic_power.base = 30
    player.traits.hp.base = 500
    player.traits.hp.current = 500
    return player


def _monster(key="goblin", hp=500, atk=10, agility=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    monster.traits.agility.base = agility
    return monster


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = "human"
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    npc.traits.agility.base = agility
    join_party(npc, player)
    return npc


def _grant_affinity(npc, player, value):
    apply_affinity_change(
        npc, player, AffinitySource.QUEST_COMPLETION, value
    )


class FriendlyFireBase(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        for skill in _TEST_SKILLS:
            SKILL_REGISTRY[skill.key] = skill
        self.room = create_object(Room, key="friendly fire arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("誤傷狼")
        self.monster.location = self.room

    def tearDown(self):
        for skill in _TEST_SKILLS:
            SKILL_REGISTRY.pop(skill.key, None)
        super().tearDown()

    def _equip(self, *skill_keys):
        self.player.db.skills = {"active": list(skill_keys), "passive": []}

    def _run_hit(self, skill_key, targets):
        with patch("world.rules.combat.roll_d100", return_value=100):
            return submit_player_action(self.player, skill_key, targets)


class CombatFriendlyFireTests(FriendlyFireBase):
    """Task 3.2: per-hit penalties through the real combat facade."""

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    @covers_requirement("affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers")
    def test_area_skill_hitting_two_companions_applies_two_penalties(self):
        first = _companion(self.player, "誤傷一")
        second = _companion(self.player, "誤傷二")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 10)
        self._equip("wind_blade")
        engage(self.player, self.monster)

        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch(
            "world.rules.affinity.apply_affinity_change", side_effect=spy
        ):
            result = self._run_hit("wind_blade", [first, second])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(
            calls,
            [
                (first, AffinitySource.FRIENDLY_FIRE, -1),
                (second, AffinitySource.FRIENDLY_FIRE, -1),
            ],
        )
        self.assertEqual(first.relations.affinity_for(self.player), 9)
        self.assertEqual(second.relations.affinity_for(self.player), 9)
        for npc in (first, second):
            record = npc.relations._load(self.player)
            self.assertEqual(record.daily_gain, 0)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    @covers_requirement("affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers")
    def test_self_selected_single_target_misfire_still_penalizes(self):
        companion = _companion(self.player, "誤傷單體")
        _grant_affinity(companion, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    @covers_requirement("affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers")
    def test_every_shipped_attack_skill_can_hit_a_companion(self):
        from world.rules.combat_session import forfeit

        for skill_key in ("basic_attack", "fire_ball", "wind_blade", "shadow_slash"):
            companion = _companion(self.player, f"目標{skill_key}")
            _grant_affinity(companion, self.player, 10)
            self._equip(skill_key)
            engage(self.player, self.monster)
            targets = [companion]
            if skill_key == "wind_blade":
                targets = [companion, self.monster]
            result = self._run_hit(skill_key, targets)
            self.assertEqual(result["outcome"], "round", skill_key)
            self.assertEqual(
                companion.relations.affinity_for(self.player), 9, skill_key
            )
            forfeit(self.player)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_non_player_action_damage_never_penalizes(self):
        companion = _companion(self.player, "挨打", hp=50, agility=1)
        _grant_affinity(companion, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        self.monster.traits.agility.base = 100
        result = self._run_hit("fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "round")
        self.assertLess(companion.traits.hp.current, 50)
        self.assertEqual(companion.relations.affinity_for(self.player), 10)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_knockout_hit_still_qualifies(self):
        companion = _companion(self.player, "擊倒", hp=10)
        _grant_affinity(companion, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.traits.hp.current, 1)
        self.assertIn(int(companion.pk), read_session(self.player).knocked_out_ids)
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_penalty_value_comes_from_the_rulebook(self):
        companion = _companion(self.player, "規則書")
        _grant_affinity(companion, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        patched = replace(load_config(), friendly_fire_penalty_per_hit=3)
        with patch("world.rules.affinity_config.get_config", return_value=patched):
            result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 7)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_non_companion_target_writes_nothing(self):
        from world.rules.combat_session import _persist, from_storage, to_storage

        stranger = create_object(NPC, key="路人", location=self.room)
        stranger.race = "human"
        stranger.apply_race_baseline()
        stranger.traits.hp.base = 200
        stranger.traits.hp.current = 200
        self._equip("fire_ball")
        engage(self.player, self.monster)
        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "enemy_ids": [self.monster.pk, stranger.pk],
            }
        )
        _persist(self.player, record)
        result = self._run_hit("fire_ball", [stranger])
        self.assertEqual(result["outcome"], "round")
        self.assertLess(stranger.traits.hp.current, 200)
        self.assertFalse(stranger.relations.has_record(self.player))

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_two_hits_on_one_companion_apply_two_penalties(self):
        companion = _companion(self.player, "雙擊")
        _grant_affinity(companion, self.player, 10)
        self._equip(FRIENDLY_DOUBLE.key)
        engage(self.player, self.monster)
        result = self._run_hit(FRIENDLY_DOUBLE.key, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 8)


class ScanScopeTests(FriendlyFireBase):
    """Task 2.4: non-player-action logs never enter the scan; snapshot logic."""

    def _craft_log(self, actor, target, kind="damage"):
        entry = EventEntry(
            kind=kind,
            actor=str(actor.key),
            target=str(target.key),
            data={"amount": 5},
            text_template="{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
        )
        return EventLog(str(actor.key), "basic_attack", (str(target.key),), (entry,), 0)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_companion_vs_companion_damage_never_enters_the_scan(self):
        first = _companion(self.player, "甲")
        second = _companion(self.player, "乙")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 10)
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        log = self._craft_log(first, second)
        notifications = _scan_friendly_fire(self.player, battlefield, [log])
        self.assertEqual(notifications, ())
        self.assertEqual(second.relations.affinity_for(self.player), 10)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_enemy_behavior_damage_never_enters_the_scan(self):
        companion = _companion(self.player, "敵傷")
        _grant_affinity(companion, self.player, 10)
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        log = self._craft_log(self.monster, companion)
        notifications = _scan_friendly_fire(self.player, battlefield, [log])
        self.assertEqual(notifications, ())
        self.assertEqual(companion.relations.affinity_for(self.player), 10)


class AutoLeaveFriendlyFireTests(FriendlyFireBase):
    """Task 3.3: auto-leave integration for friendly-fire penalties."""

    def _bind_at_threshold(self, companion):
        # The ``_companion`` helper already binds the party; only the
        # affinity value needs raising to the invite threshold.
        _grant_affinity(companion, self.player, 70)

    @covers_requirement("affinity-friendly-fire::friendly-fire-penalties-below-the-invite-threshold-end-the-companion-party")
    def test_drop_below_threshold_ends_party_with_notification_after_commit(self):
        companion = _companion(self.player, "臨界")
        self._bind_at_threshold(companion)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        self.assertIsNone(companion.db.party_member)
        self.assertEqual(
            [str(call.args[0]) for call in msg.call_args_list],
            [AUTO_LEAVE_MESSAGE],
        )

    @covers_requirement("affinity-friendly-fire::friendly-fire-penalties-below-the-invite-threshold-end-the-companion-party")
    def test_stay_at_or_above_threshold_keeps_the_party(self):
        companion = _companion(self.player, "邊緣")
        _grant_affinity(companion, self.player, 71)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 70)
        self.assertIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(int(companion.db.party_member), int(self.player.pk))
        self.assertEqual(msg.call_count, 0)

    @covers_requirement("affinity-friendly-fire::friendly-fire-penalties-below-the-invite-threshold-end-the-companion-party")
    def test_failed_auto_leave_rolls_back_the_penalty(self):
        companion = _companion(self.player, "失敗")
        self._bind_at_threshold(companion)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        original_add = companion.attributes.add
        armed = {"active": True}

        def _failing_add(key, *args, **kwargs):
            if armed["active"] and key == "party_member":
                armed["active"] = False
                raise RuntimeError("injected party_member write failure")
            return original_add(key, *args, **kwargs)

        with (
            patch.object(self.player, "msg") as msg,
            patch.object(companion.attributes, "add", side_effect=_failing_add),
        ):
            with self.assertRaises(PartyWriteError):
                self._run_hit("fire_ball", [companion])
        companion.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(companion.relations.affinity_for(self.player), 70)
        self.assertIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(int(companion.db.party_member), int(self.player.pk))
        self.assertEqual(msg.call_count, 0)

    @covers_requirement("affinity-friendly-fire::friendly-fire-penalties-below-the-invite-threshold-end-the-companion-party")
    def test_companion_that_left_earlier_no_longer_qualifies_in_a_later_round(self):
        companion = _companion(self.player, "已離隊")
        self._bind_at_threshold(companion)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        result = self._run_hit("fire_ball", [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)


class SnapshotFriendlyFireTests(FriendlyFireBase):
    """Task 3.4: same-round membership snapshot and mid-round rollback."""

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_mid_round_leave_does_not_cancel_later_hits_of_the_same_action(self):
        companion = _companion(self.player, "快離隊")
        _grant_affinity(companion, self.player, 70)
        self._equip(FRIENDLY_DOUBLE.key)
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit(FRIENDLY_DOUBLE.key, [companion])
        self.assertEqual(result["outcome"], "round")
        # First hit: 70 -> 69 triggers the leave; the snapshot keeps the
        # companion qualifying, so the second hit still applies: 69 -> 68.
        self.assertEqual(companion.relations.affinity_for(self.player), 68)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(
            [str(call.args[0]) for call in msg.call_args_list],
            [AUTO_LEAVE_MESSAGE],
        )

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    @covers_requirement("affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers")
    def test_area_all_shorthand_includes_allies_and_penalizes_companions(self):
        companion = _companion(self.player, "全選誤傷")
        _grant_affinity(companion, self.player, 10)
        self._equip("wind_blade")
        engage(self.player, self.monster)
        result = self._run_hit("wind_blade", "all")
        self.assertEqual(result["outcome"], "round")
        self.assertLess(companion.traits.hp.current, 100)
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_failure_mid_round_rolls_back_every_penalty(self):
        first = _companion(self.player, "先扣")
        second = _companion(self.player, "後失敗")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 70)
        self._equip("wind_blade")
        engage(self.player, self.monster)
        hp_before = (first.traits.hp.current, second.traits.hp.current)
        original_add = second.attributes.add
        armed = {"active": True}

        def _failing_add(key, *args, **kwargs):
            if armed["active"] and key == "party_member":
                armed["active"] = False
                raise RuntimeError("injected party_member write failure")
            return original_add(key, *args, **kwargs)

        with (
            patch.object(self.player, "msg") as msg,
            patch.object(second.attributes, "add", side_effect=_failing_add),
        ):
            with self.assertRaises(PartyWriteError):
                self._run_hit("wind_blade", [first, second])
        for npc in (first, second):
            npc.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(first.relations.affinity_for(self.player), 70)
        self.assertEqual(second.relations.affinity_for(self.player), 70)
        self.assertEqual(party_ids(self.player), [first.pk, second.pk])
        self.assertEqual(msg.call_count, 0)
        # The round result cannot commit with partial penalties: the session
        # record is untouched because the scan failure propagated, and the
        # round's damage rolls back with it.
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(
            (first.traits.hp.current, second.traits.hp.current), hp_before
        )

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    @covers_requirement("affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers")
    def test_rollback_restores_the_rounds_damage_too(self):
        companion = _companion(self.player, "回滾傷害")
        _grant_affinity(companion, self.player, 70)
        self._equip("wind_blade")
        engage(self.player, self.monster)
        hp_before = (companion.traits.hp.current, self.monster.traits.hp.current)
        original_add = companion.attributes.add
        armed = {"active": True}

        def _failing_add(key, *args, **kwargs):
            if armed["active"] and key == "party_member":
                armed["active"] = False
                raise RuntimeError("injected party_member write failure")
            return original_add(key, *args, **kwargs)

        with (
            patch.object(self.player, "msg") as msg,
            patch.object(companion.attributes, "add", side_effect=_failing_add),
        ):
            with self.assertRaises(PartyWriteError):
                self._run_hit("wind_blade", [companion, self.monster])
        companion.attributes.reset_cache()
        self.player.attributes.reset_cache()
        # Affinity, party binding, and the round's damage on both the
        # companion and the monster all restore together.
        self.assertEqual(companion.relations.affinity_for(self.player), 70)
        self.assertIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(companion.traits.hp.current, hp_before[0])
        self.assertEqual(self.monster.traits.hp.current, hp_before[1])
        self.assertEqual(msg.call_count, 0)


class OverwhelmCompressionTests(FriendlyFireBase):
    """Task 3.4 supplement: overwhelm compression resolves all raw rounds
    before the single friendly-fire scan; the compressed logs keep the
    player's own action damage, so the same per-hit penalty and auto-leave
    contracts hold through the compression."""

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_overwhelm_compression_applies_penalty_and_auto_leave(self):
        companion = _companion(self.player, "壓縮誤傷")
        _grant_affinity(companion, self.player, 70)
        self._equip("wind_blade")
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit("wind_blade", [companion])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(
            [str(call.args[0]) for call in msg.call_args_list],
            [AUTO_LEAVE_MESSAGE],
        )


class HealingWithoutPenaltyTests(FriendlyFireBase):
    """Recovery skills target allies and foes freely and never write affinity.

    The shipped registry ships no recovery skill yet; the contract is proven
    with a test-only recovery skill whose faction constraint is ANY, matching
    what any shipped recovery skill must declare (skill-registry scope).
    """

    def _recovery_skill(self):
        return SkillDef(
            key="test_recovery_touch",
            label="測試回復",
            description="測試用：回復目標的生命。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=False,
            element="light",
            effects=["buff_apply:focus"],
            faction_constraint=FactionConstraint.ANY,
            category=SkillCategory.UTILITY,
        )

    @covers_requirement("affinity-friendly-fire::healing-allies-or-foes-carries-no-penalty")
    def test_recovery_on_enemy_resolves_without_affinity_write(self):
        recovery = self._recovery_skill()
        SKILL_REGISTRY[recovery.key] = recovery
        try:
            self._equip(recovery.key)
            engage(self.player, self.monster)
            result = self._run_hit(recovery.key, [self.monster])
        finally:
            SKILL_REGISTRY.pop(recovery.key, None)
        self.assertEqual(result["outcome"], "round")
        # The recovery effect resolved on the foe (the buff landed), yet no
        # affinity record was created or modified.
        from world.rules.buffs import entity_active_buffs

        self.assertIn("focus", entity_active_buffs(self.monster))
        self.assertFalse(self.monster.relations.has_record(self.player))

    @covers_requirement("affinity-friendly-fire::healing-allies-or-foes-carries-no-penalty")
    def test_recovery_on_companion_resolves_without_penalty(self):
        companion = _companion(self.player, "回復同伴")
        _grant_affinity(companion, self.player, 10)
        recovery = self._recovery_skill()
        SKILL_REGISTRY[recovery.key] = recovery
        try:
            self._equip(recovery.key)
            engage(self.player, self.monster)
            result = self._run_hit(recovery.key, [companion])
        finally:
            SKILL_REGISTRY.pop(recovery.key, None)
        self.assertEqual(result["outcome"], "round")
        from world.rules.buffs import entity_active_buffs

        self.assertIn("focus", entity_active_buffs(companion))
        self.assertEqual(companion.relations.affinity_for(self.player), 10)
