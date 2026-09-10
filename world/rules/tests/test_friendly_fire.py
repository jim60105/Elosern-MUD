"""Friendly-fire affinity penalty integration tests (affinity-friendly-fire).

Covers the deterministic per-hit penalty contract: a player combat action that
damages an ally-side companion NPC applies one ``friendly_fire`` negative delta
per hit through the sole affinity writer, inside the round's transaction
boundary with per-round membership snapshots, while non-player-action damage and
non-companion targets never write. Also covers the auto-leave integration (drop
below the invite threshold ends the party with the notification delivered only
after commit) and the snapshot/rollback guarantees.

The tests run inside a synthetic kit scope and drive synthetic ANY-faction
damage shapes — the runtime-keyed innate strike, a single-target elemental
spell, an AREA spell, and an uncosted physical skill — so the penalty and
auto-leave contracts are exercised through ordinary player actions without
shipped content. The shipped-content reachability claim of
``shipped-content-provides-reachable-friendly-fire-triggers`` is asserted by
the skill-registry data-contract suites (``test_skill_registry`` pins the
ANY-faction attack rows; ``test_spell_catalogs`` pins the ANY-faction AREA
spell), which the shipped registry must satisfy.
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
    BASIC_ATTACK_KEY,
    _scan_friendly_fire,
    engage,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.party import AUTO_LEAVE_MESSAGE, PartyWriteError, join_party, party_ids
from world.tests.synthetic_data import SYNTH_SKILLS

from ._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    _monster_tier_key,
    _race_key,
    _behaviour_archetype_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

_T_ELEMENT = SYNTH_SKILLS["t_ember_burst"].element.key
_T_CAST = SYNTH_SKILLS["t_ember_burst"].key
# Synthetic damage shapes (all ANY-faction, as every SkillDef defaults):
# - AREA spell: the shared seam skill.
_T_AREA = SYNTH_SEAM_AREA_SKILL.key
# - Uncosted physical single-target strike.
_T_PHYSICAL = replace(
    SYNTH_SKILLS["t_cinder_cleave"],
    key="t_ash_cleave",
    label="燼劈",
    effects=[f"damage:{_T_ELEMENT}:physical"],
)
# - Double-hit spell: no single action shape damages one target twice, and
#   the two-hits scenarios need exactly that shape.
FRIENDLY_DOUBLE = replace(
    SYNTH_SKILLS["t_ember_burst"],
    key="t_friendly_double",
    label="合成雙重誤傷",
    description="合成用：對單一目標造成兩次魔法傷害。",
    effects=[f"damage:{_T_ELEMENT}:magic"] * 2,
)
_T_DOUBLE = FRIENDLY_DOUBLE.key
# - Recovery skill (no damage effect, ANY-faction): the contract requires
#   recovery on allies or foes to resolve without any affinity write.
_RECOVERY = replace(
    SYNTH_SKILLS["t_hush_mend"],
    key="t_gentle_mend",
    label="合成回復",
    description="合成用：為目標施加回復護盾。",
    cost={},
    usable_out_of_combat=False,
    effects=["buff_apply:t_moss_veil"],
)
# - Non-elemental uncosted physical strike distinct from the innate, so the
#   reachability sweep covers several independent synthetic damage shapes.
_T_SHADOW = replace(
    _T_PHYSICAL,
    key="t_gloom_cleave",
    label="影劈",
)


def _open_scope(case):
    open_synthetic_scope(
        case,
        "skills",
        "elements",
        "buffs",
        "races",
        "subraces",
        "static_tiers",
        extra={
            "skills": {
                **synth_innate_overlay()["skills"],
                SYNTH_SEAM_AREA_SKILL.key: SYNTH_SEAM_AREA_SKILL,
                _T_PHYSICAL.key: _T_PHYSICAL,
                _T_SHADOW.key: _T_SHADOW,
                FRIENDLY_DOUBLE.key: FRIENDLY_DOUBLE,
                _RECOVERY.key: _RECOVERY,
            }
        },
    )


def _player(key="friendly fire player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = _race_key()
    player.apply_race_baseline()
    # Static magic_power raised to the spell-casting fixture level so
    # element-gated casts pass the fixture's tuning.
    player.traits.magic_power.base = 30
    player.traits.hp.base = 500
    player.traits.hp.current = 500
    return player


def _monster(key="goblin", hp=500, atk=10, agility=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    monster.traits.agility.base = agility
    return monster


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = _race_key()
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
        _open_scope(self)
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="friendly fire arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("誤傷狼")
        self.monster.location = self.room

    def _equip(self, *skill_keys):
        grant_lineage(self.player, list(skill_keys))

    def _run_hit(self, skill_key, targets):
        with patch("world.rules.combat.roll_d100", return_value=100):
            return submit_player_action(self.player, skill_key, targets)


class CombatFriendlyFireTests(FriendlyFireBase):
    """Task 3.2: per-hit penalties through the real combat facade."""

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_area_skill_hitting_two_companions_applies_two_penalties(self):
        first = _companion(self.player, "誤傷一")
        second = _companion(self.player, "誤傷二")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 10)
        self._equip(_T_AREA)
        engage(self.player, self.monster)

        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch(
            "world.rules.affinity.apply_affinity_change", side_effect=spy
        ):
            result = self._run_hit(_T_AREA, [first, second])
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
    def test_self_selected_single_target_misfire_still_penalizes(self):
        companion = _companion(self.player, "誤傷單體")
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_every_attack_shape_can_hit_a_companion(self):
        # Every synthetic ANY-faction damage shape reaches a companion
        # through the ordinary player seam: the innate strike (runtime key),
        # a single-target spell, an AREA spell, and two uncosted physicals.
        # Each shape gets its own fresh fixtures, so no shape inherits the
        # previous round's session or settlement state.
        for skill_key in (
            BASIC_ATTACK_KEY,
            _T_CAST,
            _T_AREA,
            _T_PHYSICAL.key,
            _T_SHADOW.key,
        ):
            with self.subTest(skill=skill_key):
                player = _player(f"攻擊者{skill_key}")
                player.location = self.room
                monster = _monster(f"對手{skill_key}")
                monster.location = self.room
                companion = _companion(player, f"目標{skill_key}")
                _grant_affinity(companion, player, 10)
                grant_lineage(player, [skill_key])
                engage(player, monster)
                targets = [companion]
                if skill_key == _T_AREA:
                    targets = [companion, monster]
                with patch("world.rules.combat.roll_d100", return_value=100):
                    result = submit_player_action(player, skill_key, targets)
                self.assertEqual(result["outcome"], "round")
                self.assertEqual(companion.relations.affinity_for(player), 9)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_non_player_action_damage_never_penalizes(self):
        companion = _companion(self.player, "挨打", hp=50, agility=1)
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        self.monster.traits.agility.base = 100
        result = self._run_hit(_T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "round")
        self.assertLess(companion.traits.hp.current, 50)
        self.assertEqual(companion.relations.affinity_for(self.player), 10)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_knockout_hit_still_qualifies(self):
        companion = _companion(self.player, "擊倒", hp=10)
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.traits.hp.current, 1)
        self.assertIn(int(companion.pk), read_session(self.player).knocked_out_ids)
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_penalty_value_comes_from_the_rulebook(self):
        companion = _companion(self.player, "規則書")
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        patched = replace(load_config(), friendly_fire_penalty_per_hit=3)
        with patch("world.rules.affinity_config.get_config", return_value=patched):
            result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 7)

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_non_companion_target_writes_nothing(self):
        from world.rules.combat_session import _persist, from_storage, to_storage

        stranger = create_object(NPC, key="路人", location=self.room)
        stranger.race = _race_key()
        stranger.apply_race_baseline()
        stranger.traits.hp.base = 200
        stranger.traits.hp.current = 200
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "enemy_ids": [self.monster.pk, stranger.pk],
            }
        )
        _persist(self.player, record)
        result = self._run_hit(_T_CAST, [stranger])
        self.assertEqual(result["outcome"], "round")
        self.assertLess(stranger.traits.hp.current, 200)
        self.assertFalse(stranger.relations.has_record(self.player))

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    def test_two_hits_on_one_companion_apply_two_penalties(self):
        companion = _companion(self.player, "雙擊")
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_DOUBLE)
        engage(self.player, self.monster)
        result = self._run_hit(_T_DOUBLE, [companion])
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
        return EventLog(str(actor.key), BASIC_ATTACK_KEY, (str(target.key),), (entry,), 0)

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
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit(_T_CAST, [companion])
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
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 70)
        self.assertIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(int(companion.db.party_member), int(self.player.pk))
        self.assertEqual(msg.call_count, 0)

    @covers_requirement("affinity-friendly-fire::friendly-fire-penalties-below-the-invite-threshold-end-the-companion-party")
    def test_failed_auto_leave_rolls_back_the_penalty(self):
        companion = _companion(self.player, "失敗")
        self._bind_at_threshold(companion)
        self._equip(_T_CAST)
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
                self._run_hit(_T_CAST, [companion])
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
        self._equip(_T_CAST)
        engage(self.player, self.monster)
        result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        result = self._run_hit(_T_CAST, [companion])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)


class SnapshotFriendlyFireTests(FriendlyFireBase):
    """Task 3.4: same-round membership snapshot and mid-round rollback."""

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_mid_round_leave_does_not_cancel_later_hits_of_the_same_action(self):
        companion = _companion(self.player, "快離隊")
        _grant_affinity(companion, self.player, 70)
        self._equip(_T_DOUBLE)
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit(_T_DOUBLE, [companion])
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
    def test_area_all_shorthand_includes_allies_and_penalizes_companions(self):
        companion = _companion(self.player, "全選誤傷")
        _grant_affinity(companion, self.player, 10)
        self._equip(_T_AREA)
        engage(self.player, self.monster)
        result = self._run_hit(_T_AREA, "all")
        self.assertEqual(result["outcome"], "round")
        self.assertLess(companion.traits.hp.current, 100)
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_failure_mid_round_rolls_back_every_penalty(self):
        first = _companion(self.player, "先扣")
        second = _companion(self.player, "後失敗")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 70)
        self._equip(_T_AREA)
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
                self._run_hit(_T_AREA, [first, second])
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
    def test_rollback_restores_the_rounds_damage_too(self):
        companion = _companion(self.player, "回滾傷害")
        _grant_affinity(companion, self.player, 70)
        self._equip(_T_AREA)
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
                self._run_hit(_T_AREA, [companion, self.monster])
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
    """Task 3.4 supplement under the opening seam: overwhelm compression
    resolves all raw rounds before the single friendly-fire scan; the
    compressed logs keep the player's own action damage, so the same per-hit
    penalty and auto-leave contracts hold through the compression.
    (combat-session-opening-dispatch: compression is reachable only via
    ``submit_opening_action()``, so the test opens through that seam.)"""

    @covers_requirement("affinity-friendly-fire::player-combat-actions-that-damage-companion-npcs-apply-a-per-hit-affinity-penalty")
    @covers_requirement("affinity-friendly-fire::the-scan-penalties-and-auto-leave-commit-atomically-with-the-round")
    def test_overwhelm_compression_applies_penalty_and_auto_leave(self):
        companion = _companion(self.player, "壓縮誤傷")
        _grant_affinity(companion, self.player, 70)
        self._equip(_T_AREA)
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with (
            patch.object(self.player, "msg") as msg,
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.action.roll_d100", return_value=100),
        ):
            result = submit_opening_action(
                self.player, _T_AREA, [companion, self.monster]
            )
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(companion.relations.affinity_for(self.player), 69)
        self.assertNotIn(int(companion.pk), party_ids(self.player))
        self.assertEqual(
            [str(call.args[0]) for call in msg.call_args_list],
            [AUTO_LEAVE_MESSAGE],
        )


class HealingWithoutPenaltyTests(FriendlyFireBase):
    """Recovery skills target allies and foes freely and never write affinity.

    Proven with the file's synthetic recovery shape (no damage effect,
    ANY-faction, carrying the kit buff), matching what any shipped recovery
    skill must declare (skill-registry scope).
    """

    @covers_requirement("affinity-friendly-fire::healing-allies-or-foes-carries-no-penalty")
    def test_recovery_on_enemy_resolves_without_affinity_write(self):
        self._equip(_RECOVERY.key)
        engage(self.player, self.monster)
        result = self._run_hit(_RECOVERY.key, [self.monster])
        self.assertEqual(result["outcome"], "round")
        # The recovery effect resolved on the foe (the buff landed), yet no
        # affinity record was created or modified.
        from world.rules.buffs import entity_active_buffs

        self.assertIn("t_moss_veil", entity_active_buffs(self.monster))
        self.assertFalse(self.monster.relations.has_record(self.player))

    @covers_requirement("affinity-friendly-fire::healing-allies-or-foes-carries-no-penalty")
    def test_recovery_on_companion_resolves_without_penalty(self):
        companion = _companion(self.player, "回復同伴")
        _grant_affinity(companion, self.player, 10)
        self._equip(_RECOVERY.key)
        engage(self.player, self.monster)
        result = self._run_hit(_RECOVERY.key, [companion])
        self.assertEqual(result["outcome"], "round")
        from world.rules.buffs import entity_active_buffs

        self.assertIn("t_moss_veil", entity_active_buffs(companion))
        self.assertEqual(companion.relations.affinity_for(self.player), 10)
