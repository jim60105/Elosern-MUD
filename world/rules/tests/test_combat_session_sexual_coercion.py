"""Sexual-coercion affinity penalty integration tests (sexual-resist-turn-cost B6b).

Covers the deterministic turn-cost contract: a forced sexual act (a resist
attempted and failed) during active combat costs the target NPC's affinity
toward the actor once per forced act, through the sole affinity writer with
the ``sexual_forced`` source and the rulebook ``sexual_forced_penalty``
value, inside the round's shared outer transaction. Compliance (rolled or
automatic) and a successful resistance never cost affinity.

The round's ``EventLog`` is the contract surface this proposal reacts to
(``EventEntry(kind="sexual_resist", data={"resisted": bool, "auto_comply":
bool, "roll": int | None})``, documented in ``sexual-act-resolution-design.md``
§3.4). No production code emits that kind yet -- ``sexual-act-effects`` owns
the emitter -- so these tests drive the scan with synthetic logs carrying the
documented shape, exactly as ``climax-settlement`` exercised
``stage_climax_extension()`` before its caller existed.

Also covers the widened relations snapshot (design.md Decision 3): every
roster NPC's ``relations_data`` is snapshotted pre-round, not only party
companions', so a rolled-back round restores a coerced non-companion NPC's
in-process surface even on a battlefield with zero declared companions.
"""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.rules import affinity as affinity_module
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import load_config
from world.rules.combat_session import (
    _scan_sexual_coercion,
    engage,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.party import AUTO_LEAVE_MESSAGE, join_party, party_ids
from .combat_fixtures import BattlefieldIsolation, grant_lineage


def _player(key="coercion player"):
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


def _npc(key, hp=100, agility=10, location=None):
    npc = create_object(NPC, key=key, location=location)
    npc.race = "human"
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    npc.traits.agility.base = agility
    return npc


def _companion(player, key, hp=100, agility=10):
    npc = _npc(key, hp=hp, agility=agility, location=player.location)
    join_party(npc, player)
    return npc


def _grant_affinity(npc, player, value):
    apply_affinity_change(npc, player, AffinitySource.QUEST_COMPLETION, value)


def _resist_log(actor, target, *, resisted, auto_comply, roll):
    """One ``sexual_resist`` EventLog carrying the documented data contract."""
    entry = EventEntry(
        kind="sexual_resist",
        actor=str(actor.key),
        target=str(target.key),
        data={"resisted": resisted, "auto_comply": auto_comply, "roll": roll},
        text_template="{actor} 對 {target} 施加了強制行為。",
    )
    return EventLog(str(actor.key), "basic_attack", (str(target.key),), (entry,), 0)


class SexualCoercionBase(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.penalty = load_config().sexual_forced_penalty
        self.room = create_object(Room, key="coercion arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("慾狼")
        self.monster.location = self.room

    def _equip(self, *skill_keys):
        grant_lineage(self.player, list(skill_keys))

    def _run_hit(self, skill_key, targets):
        with patch("world.rules.combat.roll_d100", return_value=100):
            return submit_player_action(self.player, skill_key, targets)

    def _battlefield(self):
        return reconstruct_battlefield(self.player, read_session(self.player))

    def _forced_log(self, target):
        return _resist_log(
            self.player, target, resisted=False, auto_comply=False, roll=55
        )

    def _raw_relations(self, npc):
        """The raw stored ``relations_data`` Attribute row, read via SQL only."""
        row = (
            npc.db_attributes.through.objects.filter(
                objectdb_id=npc.pk, attribute__db_key="relations_data"
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row


class AffinityConfigPenaltyTests(unittest.TestCase):
    """The rulebook field contract (spec requirement: sexual_forced_penalty is
    a validated rulebook field, independent of friendly_fire_penalty_per_hit)."""

    def setUp(self):
        register_catalog()

    def _deviant(self, content):
        import tempfile

        from world.rules.affinity_config import AffinityConfigError

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "affinity.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(AffinityConfigError) as raised:
                load_config(path=path)
            return str(raised.exception)

    @covers_requirement("sexual-resist-turn-cost::sexual-forced-penalty-is-a-validated-rulebook-field-independent-of-friendly-fire-penalty-per-hit")
    def test_missing_sexual_forced_penalty_fails_closed(self):
        source = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        message = self._deviant(source.replace("sexual_forced_penalty: 3\n", ""))
        self.assertIn("sexual_forced_penalty", message)

    @covers_requirement("sexual-resist-turn-cost::sexual-forced-penalty-is-a-validated-rulebook-field-independent-of-friendly-fire-penalty-per-hit")
    def test_negative_sexual_forced_penalty_fails_closed(self):
        source = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        self._deviant(source.replace("sexual_forced_penalty: 3\n", "sexual_forced_penalty: -1\n"))

    @covers_requirement("sexual-resist-turn-cost::sexual-forced-penalty-is-a-validated-rulebook-field-independent-of-friendly-fire-penalty-per-hit")
    def test_penalties_are_independently_configurable(self):
        source = (
            Path(__file__).parents[1] / "rulebook" / "affinity.yaml"
        ).read_text(encoding="utf-8")
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "affinity.yaml"
            modified = source.replace(
                "sexual_forced_penalty: 3\n", "sexual_forced_penalty: 7\n"
            ).replace(
                "friendly_fire_penalty_per_hit: 1\n",
                "friendly_fire_penalty_per_hit: 2\n",
            )
            path.write_text(modified, encoding="utf-8")
            config = load_config(path=path)
        self.assertEqual(config.sexual_forced_penalty, 7)
        self.assertEqual(config.friendly_fire_penalty_per_hit, 2)
        # The shipped values stay distinct and readable through get_config().
        self.assertNotEqual(
            load_config().sexual_forced_penalty,
            load_config().friendly_fire_penalty_per_hit,
        )


class SexualCoercionScanTests(SexualCoercionBase):
    """Direct scan contract: exactly the forced outcome penalizes."""

    def _scan(self, *logs):
        return _scan_sexual_coercion(self.player, self._battlefield(), list(logs))

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_forced_act_applies_exactly_one_penalty(self):
        target = _companion(self.player, "強制目標")
        # High enough that one penalty cannot drop below the invite threshold,
        # so the scan returns no auto-leave notification.
        _grant_affinity(target, self.player, 73)
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        log = self._forced_log(target)
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.affinity.apply_affinity_change", side_effect=spy):
            notifications = _scan_sexual_coercion(self.player, battlefield, [log])
        self.assertEqual(notifications, ())
        self.assertEqual(
            calls,
            [(target, AffinitySource.SEXUAL_FORCED, -self.penalty)],
        )
        self.assertEqual(
            target.relations.affinity_for(self.player), 73 - self.penalty
        )

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_complied_act_applies_no_penalty(self):
        target = _companion(self.player, "服從目標")
        _grant_affinity(target, self.player, 10)
        engage(self.player, self.monster)
        log = _resist_log(
            self.player, target, resisted=False, auto_comply=True, roll=None
        )
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.affinity.apply_affinity_change", side_effect=spy):
            notifications = self._scan(log)
        self.assertEqual(notifications, ())
        self.assertEqual(calls, [])
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_resisted_act_applies_no_penalty(self):
        target = _companion(self.player, "拒絕目標")
        _grant_affinity(target, self.player, 10)
        engage(self.player, self.monster)
        log = _resist_log(
            self.player, target, resisted=True, auto_comply=False, roll=80
        )
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = self._scan(log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_missing_or_mistyped_data_keys_never_penalize(self):
        target = _companion(self.player, "殘缺資料")
        _grant_affinity(target, self.player, 10)
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        cases = [
            {},  # no data at all
            {"resisted": False},  # auto_comply missing
            {"auto_comply": False},  # resisted missing
            {"resisted": False, "auto_comply": "false"},  # mistyped string
            {"resisted": "false", "auto_comply": False},  # mistyped string
        ]
        for data in cases:
            entry = EventEntry(
                kind="sexual_resist",
                actor=str(self.player.key),
                target=str(target.key),
                data=data,
                text_template="x",
            )
            log = EventLog(
                str(self.player.key), "basic_attack", (str(target.key),), (entry,), 0
            )
            with patch("world.rules.affinity.apply_affinity_change") as writer:
                notifications = _scan_sexual_coercion(
                    self.player, battlefield, [log]
                )
            self.assertEqual(notifications, ())
            writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_multiple_forced_entries_each_apply_their_own_penalty(self):
        first = _companion(self.player, "雙目標一")
        second = _companion(self.player, "雙目標二")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 73)
        engage(self.player, self.monster)
        logs = [self._forced_log(first), self._forced_log(second)]
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.affinity.apply_affinity_change", side_effect=spy):
            notifications = self._scan(*logs)
        self.assertEqual(notifications, ())
        self.assertEqual(
            calls,
            [
                (first, AffinitySource.SEXUAL_FORCED, -self.penalty),
                (second, AffinitySource.SEXUAL_FORCED, -self.penalty),
            ],
        )
        self.assertEqual(first.relations.affinity_for(self.player), 73 - self.penalty)
        self.assertEqual(second.relations.affinity_for(self.player), 73 - self.penalty)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_forced_entry_targeting_a_monster_applies_no_penalty(self):
        engage(self.player, self.monster)
        log = self._forced_log(self.monster)
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = self._scan(log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertFalse(self.monster.relations.has_record(self.player))

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_forced_entry_targeting_a_player_applies_no_penalty(self):
        other = _player("被強制者")
        other.location = self.room
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        # A second player is a structurally valid non-NPC roster member.
        battlefield.roster[str(other.key)] = other
        log = _resist_log(
            self.player, other, resisted=False, auto_comply=False, roll=55
        )
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = _scan_sexual_coercion(self.player, battlefield, [log])
        self.assertEqual(notifications, ())
        writer.assert_not_called()

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_forced_entry_targeting_an_absent_entity_applies_no_penalty(self):
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        entry = EventEntry(
            kind="sexual_resist",
            actor=str(self.player.key),
            target="no-such-roster-member",
            data={"resisted": False, "auto_comply": False, "roll": 55},
            text_template="x",
        )
        log = EventLog(
            str(self.player.key), "basic_attack", ("no-such-roster-member",), (entry,), 0
        )
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = _scan_sexual_coercion(self.player, battlefield, [log])
        self.assertEqual(notifications, ())
        writer.assert_not_called()

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_non_sexual_resist_entries_are_ignored(self):
        companion = _companion(self.player, "無關條目")
        _grant_affinity(companion, self.player, 10)
        engage(self.player, self.monster)
        damage_entry = EventEntry(
            kind="damage",
            actor=str(self.player.key),
            target=str(companion.key),
            data={"amount": 5},
            text_template="x",
        )
        damage_log = EventLog(
            str(self.player.key),
            "basic_attack",
            (str(companion.key),),
            (damage_entry,),
            0,
        )
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = self._scan(damage_log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(companion.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_non_player_actor_logs_never_enter_the_scan(self):
        # A companion's or monster's own cast (a future emitter shape) can
        # never charge the player's affinity for someone else's act.
        target = _companion(self.player, "他人施放")
        _grant_affinity(target, self.player, 10)
        engage(self.player, self.monster)
        other = _npc("施放者", location=self.room)
        log = _resist_log(
            other, target, resisted=False, auto_comply=False, roll=55
        )
        with patch("world.rules.affinity.apply_affinity_change") as writer:
            notifications = self._scan(log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-turn-cost::scan-sexual-coercion-penalizes-exactly-the-forced-outcome-never-comply-or-successful-resistance")
    def test_malformed_non_dict_data_never_penalizes_and_never_raises(self):
        target = _companion(self.player, "畸形資料")
        _grant_affinity(target, self.player, 10)
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        for payload in ("oops", [1, 2], 42):
            entry = EventEntry(
                kind="sexual_resist",
                actor=str(self.player.key),
                target=str(target.key),
                data=payload,
                text_template="x",
            )
            log = EventLog(
                str(self.player.key), "basic_attack", (str(target.key),), (entry,), 0
            )
            with patch("world.rules.affinity.apply_affinity_change") as writer:
                notifications = _scan_sexual_coercion(
                    self.player, battlefield, [log]
                )
            self.assertEqual(notifications, ())
            writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    def test_penalty_value_comes_from_the_rulebook(self):
        target = _companion(self.player, "規則書目標")
        # 75 - 5 = 70 keeps the party intact, so no auto-leave notification.
        _grant_affinity(target, self.player, 75)
        engage(self.player, self.monster)
        patched = replace(load_config(), sexual_forced_penalty=5)
        with patch("world.rules.affinity_config.get_config", return_value=patched):
            notifications = self._scan(self._forced_log(target))
        self.assertEqual(notifications, ())
        self.assertEqual(target.relations.affinity_for(self.player), 70)

    def test_internal_failure_restores_membership_and_relations_surfaces(self):
        # A failure mid-scan, after an earlier forced entry already triggered
        # an auto-leave, must restore both the party-membership and the
        # relations in-process surfaces (the idmapper cache is not
        # transaction-aware) -- mirroring _scan_friendly_fire's restore.
        first = _companion(self.player, "先離隊")
        second = _companion(self.player, "後失敗")
        for npc in (first, second):
            _grant_affinity(npc, self.player, 70)
        engage(self.player, self.monster)
        battlefield = self._battlefield()
        logs = [self._forced_log(first), self._forced_log(second)]
        original = affinity_module.apply_affinity_change
        calls = {"count": 0}

        def failing_writer(npc, player, source, delta):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("injected second write failure")
            return original(npc, player, source, delta)

        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=failing_writer,
        ):
            with self.assertRaises(RuntimeError):
                _scan_sexual_coercion(self.player, battlefield, logs)
        # The first forced entry's auto-leave rolled back with the scan's
        # transaction: both companions stay bound at their pre-round affinity.
        for npc in (first, second):
            npc.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(first.relations.affinity_for(self.player), 70)
        self.assertEqual(second.relations.affinity_for(self.player), 70)
        self.assertEqual(party_ids(self.player), [first.pk, second.pk])
        self.assertEqual(int(first.db.party_member), int(self.player.pk))
        self.assertEqual(int(second.db.party_member), int(self.player.pk))


class SexualCoercionIntegrationTests(SexualCoercionBase):
    """The scan inside the round's shared outer transaction (submit_player_action)."""

    def _run_hit_with_resist_log(self, skill_key, targets, resist_log):
        """Run a real round whose logs carry one synthetic resist entry."""
        from world.rules.combat_session import run_round as real_run_round

        def run_with_resist(battlefield, provider, **kwargs):
            logs = list(real_run_round(battlefield, provider, **kwargs))
            logs.append(resist_log)
            return logs

        with (
            patch("world.rules.combat_session.run_round", side_effect=run_with_resist),
            patch("world.rules.combat.roll_d100", return_value=100),
        ):
            return submit_player_action(self.player, skill_key, targets)

    @covers_requirement("sexual-resist-turn-cost::the-coercion-scan-runs-inside-the-round-s-shared-outer-transaction-symmetric-with-friendly-fire")
    def test_forced_penalty_commits_atomically_with_the_round(self):
        target = _companion(self.player, "整合強制")
        _grant_affinity(target, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        result = self._run_hit_with_resist_log(
            "fire_ball", [self.monster], self._forced_log(target)
        )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(
            target.relations.affinity_for(self.player), 10 - self.penalty
        )

    @covers_requirement("sexual-resist-turn-cost::the-coercion-scan-runs-inside-the-round-s-shared-outer-transaction-symmetric-with-friendly-fire")
    def test_rolled_back_round_leaves_no_coercion_penalty_trace(self):
        target = _companion(self.player, "回滾強制")
        _grant_affinity(target, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        relations_before = target.db.relations_data
        raw_before = self._raw_relations(target)
        from world.rules.combat_session import _persist, run_round as real_run_round

        def run_with_resist(battlefield, provider, **kwargs):
            logs = list(real_run_round(battlefield, provider, **kwargs))
            logs.append(self._forced_log(target))
            return logs

        def failing_persist(actor, record):
            raise RuntimeError("injected settlement persist failure")

        with (
            patch("world.rules.combat_session.run_round", side_effect=run_with_resist),
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session._persist", side_effect=failing_persist
            ) as persist,
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        persist.assert_called_once()
        # In-process idmapper surface restored to the pre-round value.
        target.attributes.reset_cache()
        self.assertEqual(target.db.relations_data, relations_before)
        self.assertEqual(target.relations.affinity_for(self.player), 10)
        # Fresh database read agrees.
        self.assertEqual(self._raw_relations(target), raw_before)

    @covers_requirement("sexual-resist-turn-cost::the-coercion-scan-runs-inside-the-round-s-shared-outer-transaction-symmetric-with-friendly-fire")
    def test_friendly_fire_and_coercion_penalties_in_same_round_both_apply(self):
        ff_target = _companion(self.player, "誤傷整合")
        coerced = _companion(self.player, "強制整合")
        for npc in (ff_target, coerced):
            _grant_affinity(npc, self.player, 10)
        # wind_blade is the shipped AREA skill: it damages both the companion
        # and the monster in one action, so the friendly-fire scan sees a
        # qualifying hit while the synthetic resist log drives the coercion
        # scan in the same round.
        self._equip("wind_blade")
        engage(self.player, self.monster)
        result = self._run_hit_with_resist_log(
            "wind_blade", [ff_target, self.monster], self._forced_log(coerced)
        )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(ff_target.relations.affinity_for(self.player), 9)
        self.assertEqual(
            coerced.relations.affinity_for(self.player), 10 - self.penalty
        )

    @covers_requirement("sexual-resist-turn-cost::the-coercion-scan-runs-inside-the-round-s-shared-outer-transaction-symmetric-with-friendly-fire")
    def test_auto_leave_notification_combines_both_scans(self):
        coerced = _companion(self.player, "離隊強制")
        _grant_affinity(coerced, self.player, 70)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        with patch.object(self.player, "msg") as msg:
            result = self._run_hit_with_resist_log(
                "fire_ball", [self.monster], self._forced_log(coerced)
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(coerced.relations.affinity_for(self.player), 70 - self.penalty)
        self.assertNotIn(int(coerced.pk), party_ids(self.player))
        self.assertIsNone(coerced.db.party_member)
        self.assertEqual(
            [str(call.args[0]) for call in msg.call_args_list],
            [AUTO_LEAVE_MESSAGE],
        )


class SnapshotWideningTests(SexualCoercionBase):
    """The relations snapshot covers every roster NPC (design.md Decision 3)."""

    def _add_roster_stranger(self, key="路人"):
        """Put a non-companion NPC on the battlefield as an enemy roster member."""
        from world.rules.combat_session import _persist, from_storage, to_storage

        stranger = _npc(key, location=self.room)
        engage(self.player, self.monster)
        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "enemy_ids": [self.monster.pk, stranger.pk],
            }
        )
        _persist(self.player, record)
        return stranger

    def _run_hit_with_resist_log(self, skill_key, targets, resist_log):
        from world.rules.combat_session import run_round as real_run_round

        def run_with_resist(battlefield, provider, **kwargs):
            logs = list(real_run_round(battlefield, provider, **kwargs))
            logs.append(resist_log)
            return logs

        with (
            patch("world.rules.combat_session.run_round", side_effect=run_with_resist),
            patch("world.rules.combat.roll_d100", return_value=100),
        ):
            return submit_player_action(self.player, skill_key, targets)

    @covers_requirement("sexual-resist-turn-cost::the-relations-snapshot-covers-every-roster-npc-not-only-party-companions")
    def test_non_companion_npc_penalty_survives_a_successful_round(self):
        stranger = self._add_roster_stranger()
        _grant_affinity(stranger, self.player, 10)
        self._equip("fire_ball")
        result = self._run_hit_with_resist_log(
            "fire_ball", [self.monster], self._forced_log(stranger)
        )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(
            stranger.relations.affinity_for(self.player), 10 - self.penalty
        )
        self.assertNotIn(int(stranger.pk), party_ids(self.player))

    @covers_requirement("sexual-resist-turn-cost::the-relations-snapshot-covers-every-roster-npc-not-only-party-companions")
    def test_zero_companion_rollback_restores_non_companion_relations(self):
        # The Decision 3 regression: no party companions at all, so the old
        # outer guard (``if companion_pks:``) would have skipped the snapshot
        # loop entirely and left ``relations_before`` empty.
        stranger = self._add_roster_stranger()
        _grant_affinity(stranger, self.player, 10)
        self.assertEqual(party_ids(self.player), [])
        self._equip("fire_ball")
        relations_before = stranger.db.relations_data
        raw_before = self._raw_relations(stranger)
        from world.rules.combat_session import run_round as real_run_round

        def run_with_resist(battlefield, provider, **kwargs):
            logs = list(real_run_round(battlefield, provider, **kwargs))
            logs.append(self._forced_log(stranger))
            return logs

        def failing_persist(actor, record):
            raise RuntimeError("injected settlement persist failure")

        with (
            patch("world.rules.combat_session.run_round", side_effect=run_with_resist),
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat_session._persist", side_effect=failing_persist),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        stranger.attributes.reset_cache()
        self.assertEqual(stranger.db.relations_data, relations_before)
        self.assertEqual(
            stranger.relations.affinity_for(self.player), 10
        )
        self.assertEqual(self._raw_relations(stranger), raw_before)

    @covers_requirement("sexual-resist-turn-cost::the-relations-snapshot-covers-every-roster-npc-not-only-party-companions")
    def test_companion_snapshot_coverage_is_unchanged(self):
        # A companion-only round still rolls back correctly after the widening.
        companion = _companion(self.player, "同伴回滾")
        _grant_affinity(companion, self.player, 10)
        self._equip("fire_ball")
        engage(self.player, self.monster)
        relations_before = companion.db.relations_data
        raw_before = self._raw_relations(companion)
        from world.rules.combat_session import run_round as real_run_round

        def run_with_resist(battlefield, provider, **kwargs):
            logs = list(real_run_round(battlefield, provider, **kwargs))
            logs.append(self._forced_log(companion))
            return logs

        def failing_persist(actor, record):
            raise RuntimeError("injected settlement persist failure")

        with (
            patch("world.rules.combat_session.run_round", side_effect=run_with_resist),
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat_session._persist", side_effect=failing_persist),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        companion.attributes.reset_cache()
        self.assertEqual(companion.db.relations_data, relations_before)
        self.assertEqual(companion.relations.affinity_for(self.player), 10)
        self.assertEqual(self._raw_relations(companion), raw_before)