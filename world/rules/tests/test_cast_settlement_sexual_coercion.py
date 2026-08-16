"""Sexual-coercion affinity penalty tests for the out-of-combat cast path.

Covers the ``sexual-resist-out-of-combat`` contract: a forced sexual act (a
resist attempted and failed) cast outside combat costs the target NPC's
affinity toward the actor once per forced act, through the same sole affinity
writer, source, and rulebook ``sexual_forced_penalty`` magnitude the
in-combat ``_scan_sexual_coercion`` uses, inside the settlement's outer
transaction. Compliance (rolled or automatic) and a successful resistance
never cost affinity; the auto-leave notification lines return through
``CastSettlement.notifications`` for the command layer to deliver.

The cast's ``EventLog`` is the contract surface this proposal reacts to
(``EventEntry(kind="sexual_resist", data={"resisted": bool, "auto_comply":
bool, "roll": int | None})``, documented in ``sexual-act-resolution-design.md``
§3.4 and emitted by ``action._step4b_sexual_resist_gate`` for every
resistible act cast). Direct-scan tests drive the function with synthetic
logs carrying the documented shape, mirroring
``test_combat_session_sexual_coercion``; settlement tests drive the real
``settle_out_of_combat_cast`` with the shipped ``combat_tease`` act and a
patched resist roll.
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
from world.quests.catalog import register_catalog
from world.rules import affinity as affinity_module
from world.rules.action import ActionRequest
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import load_config
from world.rules.cast_settlement import (
    _scan_out_of_combat_sexual_coercion,
    settle_out_of_combat_cast,
)
from world.rules.clock import WorldClock, _EVENT_SOURCES
from world.rules.combat_session import (
    _scan_sexual_coercion,
    engage,
    read_session,
    reconstruct_battlefield,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.party import AUTO_LEAVE_MESSAGE, join_party, party_ids
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import _act_family


def _resist_log(actor, target, *, resisted, auto_comply, roll):
    """One ``sexual_resist`` EventLog carrying the documented data contract."""
    entry = EventEntry(
        kind="sexual_resist",
        actor=str(actor.key),
        target=str(target.key),
        data={"resisted": resisted, "auto_comply": auto_comply, "roll": roll},
        text_template="{actor} 對 {target} 施加了強制行為。",
    )
    return EventLog(str(actor.key), "combat_tease", (str(target.key),), (entry,), 0)


def _raising_stage():
    """A boundary-stage source that always fails after the advance opens."""
    from world.rules.clock import EventSourceRegistration

    return EventSourceRegistration(
        lambda start, end: (_ for _ in ()).throw(
            RuntimeError("simulated clock boundary failure")
        ),
        None,
    )


class OutOfCombatCoercionBase(EvenniaTest):
    """Shared fixture: a caster player, one room, and clock/source hygiene."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self._sources = dict(_EVENT_SOURCES)
        self.penalty = load_config().sexual_forced_penalty
        self.room = create_object(Room, key="coercion chamber")
        self.player = create_object(
            PlayerCharacter, key="coercion caster", location=self.room
        )
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.skills = {"active": [], "passive": []}
        self.clock = WorldClock()

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _npc(self, key, affinity: int | None = None):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp.base = 100
        npc.traits.hp.current = 100
        if affinity is not None:
            apply_affinity_change(
                npc, self.player, AffinitySource.QUEST_COMPLETION, affinity
            )
        return npc

    def _companion(self, key, affinity: int | None = None):
        npc = self._npc(key, affinity=affinity)
        join_party(npc, self.player)
        return npc

    def _monster(self, key="慾狼"):
        monster = create_object(Monster, key=key, location=self.room)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 500
        monster.traits.hp.current = 500
        return monster

    def _request(self, skill_key, targets):
        return ActionRequest(
            self.player,
            skill_key,
            targets,
            RoomActionContext(self.room, {}),
        )

    def _settle(self, skill_key="combat_tease", targets=None):
        return settle_out_of_combat_cast(
            self._request(skill_key, targets or []), clock=self.clock
        )

    def _forced_cast(self, skill_key, targets):
        """A real settlement whose resist roll always fails (a forced outcome)."""
        with patch("world.rules.action.roll_d100", return_value=1):
            return self._settle(skill_key, targets)

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


class OutOfCombatCoercionScanTests(OutOfCombatCoercionBase):
    """Direct scan contract: exactly the forced outcome penalizes."""

    def _scan(self, targets, *logs):
        notifications, restore_state = _scan_out_of_combat_sexual_coercion(
            self.player, list(targets), logs[0]
        )
        return notifications, restore_state

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_forced_act_applies_exactly_one_penalty(self):
        target = self._companion("強制目標", affinity=73)
        relations_before_value = target.db.relations_data
        log = _resist_log(
            self.player, target, resisted=False, auto_comply=False, roll=55
        )
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.cast_settlement.apply_affinity_change", side_effect=spy):
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        self.assertIsNotNone(restore_state)
        self.assertEqual(
            restore_state.relations_before,
            {int(target.pk): relations_before_value},
        )
        self.assertEqual(
            calls,
            [(target, AffinitySource.SEXUAL_FORCED, -self.penalty)],
        )
        self.assertEqual(
            target.relations.affinity_for(self.player), 73 - self.penalty
        )

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_complied_act_applies_no_penalty(self):
        target = self._companion("服從目標", affinity=10)
        log = _resist_log(
            self.player, target, resisted=False, auto_comply=True, roll=None
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        self.assertIsNone(restore_state)
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_resisted_act_applies_no_penalty(self):
        target = self._companion("拒絕目標", affinity=10)
        log = _resist_log(
            self.player, target, resisted=True, auto_comply=False, roll=80
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        self.assertIsNone(restore_state)
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_penalty_magnitude_and_source_match_in_combat_exactly(self):
        target = self._companion("對照目標", affinity=73)
        monster = self._monster()
        engage(self.player, monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        log = _resist_log(
            self.player, target, resisted=False, auto_comply=False, roll=55
        )
        original = affinity_module.apply_affinity_change
        combat_calls = []
        out_of_combat_calls = []

        def combat_spy(npc, player, source, delta):
            combat_calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.affinity.apply_affinity_change", side_effect=combat_spy):
            _scan_sexual_coercion(self.player, battlefield, [log])
        self.assertEqual(
            combat_calls,
            [(target, AffinitySource.SEXUAL_FORCED, -self.penalty)],
        )

        def out_of_combat_spy(npc, player, source, delta):
            out_of_combat_calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.cast_settlement.apply_affinity_change", side_effect=out_of_combat_spy):
            _scan_out_of_combat_sexual_coercion(self.player, [target], log)
        self.assertEqual(
            out_of_combat_calls,
            [(target, AffinitySource.SEXUAL_FORCED, -self.penalty)],
        )
        self.assertEqual(combat_calls, out_of_combat_calls)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_missing_or_mistyped_data_keys_never_penalize(self):
        target = self._companion("殘缺資料", affinity=10)
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
                str(self.player.key), "combat_tease", (str(target.key),), (entry,), 0
            )
            with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
                notifications, restore_state = self._scan([target], log)
            self.assertEqual(notifications, ())
            writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_two_forced_targets_each_apply_their_own_penalty(self):
        first = self._companion("雙目標一", affinity=73)
        second = self._companion("雙目標二", affinity=73)
        entries = (
            _resist_log(
                self.player, first, resisted=False, auto_comply=False, roll=55
            ).entries[0],
            _resist_log(
                self.player, second, resisted=False, auto_comply=False, roll=55
            ).entries[0],
        )
        log = EventLog(
            str(self.player.key), "combat_tease", (str(first.key), str(second.key)), entries, 0
        )
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.cast_settlement.apply_affinity_change", side_effect=spy):
            notifications, restore_state = self._scan([first, second], log)
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

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_one_forced_and_one_complied_target_penalizes_only_the_forced(self):
        forced = self._companion("強制雙目標", affinity=73)
        complied = self._companion("服從雙目標", affinity=10)
        entries = (
            _resist_log(
                self.player, forced, resisted=False, auto_comply=False, roll=55
            ).entries[0],
            _resist_log(
                self.player, complied, resisted=False, auto_comply=True, roll=None
            ).entries[0],
        )
        log = EventLog(
            str(self.player.key), "combat_tease", (str(forced.key), str(complied.key)), entries, 0
        )
        original = affinity_module.apply_affinity_change
        calls = []

        def spy(npc, player, source, delta):
            calls.append((npc, source, delta))
            return original(npc, player, source, delta)

        with patch("world.rules.cast_settlement.apply_affinity_change", side_effect=spy):
            notifications, restore_state = self._scan([forced, complied], log)
        self.assertEqual(notifications, ())
        self.assertEqual(
            calls,
            [(forced, AffinitySource.SEXUAL_FORCED, -self.penalty)],
        )
        self.assertEqual(forced.relations.affinity_for(self.player), 73 - self.penalty)
        self.assertEqual(complied.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_forced_entry_targeting_a_player_applies_no_penalty(self):
        other = create_object(
            PlayerCharacter, key="被強制者", location=self.room
        )
        other.race = "human"
        other.apply_race_baseline()
        log = _resist_log(
            self.player, other, resisted=False, auto_comply=False, roll=55
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([other], log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_forced_entry_targeting_a_monster_applies_no_penalty(self):
        monster = self._monster()
        log = _resist_log(
            self.player, monster, resisted=False, auto_comply=False, roll=55
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([monster], log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertFalse(monster.relations.has_record(self.player))

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_forced_entry_targeting_an_absent_key_applies_no_penalty(self):
        target = self._companion("在場目標", affinity=10)
        entry = EventEntry(
            kind="sexual_resist",
            actor=str(self.player.key),
            target="no-such-target",
            data={"resisted": False, "auto_comply": False, "roll": 55},
            text_template="x",
        )
        log = EventLog(
            str(self.player.key), "combat_tease", ("no-such-target",), (entry,), 0
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::a-malformed-or-foreign-sexual-resist-entry-never-penalizes-and-never-raises")
    def test_non_sexual_resist_entries_are_ignored(self):
        target = self._companion("無關條目", affinity=10)
        damage_entry = EventEntry(
            kind="damage",
            actor=str(self.player.key),
            target=str(target.key),
            data={"amount": 5},
            text_template="x",
        )
        practice_entry = EventEntry(
            kind="skill_practice",
            actor=str(self.player.key),
            target=None,
            data={"skill": "combat_tease"},
            text_template="x",
        )
        log = EventLog(
            str(self.player.key),
            "combat_tease",
            (str(target.key),),
            (damage_entry, practice_entry),
            0,
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::a-malformed-or-foreign-sexual-resist-entry-never-penalizes-and-never-raises")
    def test_non_player_actor_logs_never_enter_the_scan(self):
        target = self._companion("他人施放", affinity=10)
        other = self._npc("施放者")
        log = _resist_log(
            other, target, resisted=False, auto_comply=False, roll=55
        )
        with patch("world.rules.cast_settlement.apply_affinity_change") as writer:
            notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::a-malformed-or-foreign-sexual-resist-entry-never-penalizes-and-never-raises")
    def test_malformed_non_dict_data_never_penalizes_and_never_raises(self):
        target = self._companion("畸形資料", affinity=10)
        for payload in ("oops", [1, 2], 42):
            entry = EventEntry(
                kind="sexual_resist",
                actor=str(self.player.key),
                target=str(target.key),
                data=payload,
                text_template="x",
            )
            log = EventLog(
                str(self.player.key), "combat_tease", (str(target.key),), (entry,), 0
            )
            with patch("world.rules.affinity.apply_affinity_change") as writer:
                notifications, restore_state = self._scan([target], log)
            self.assertEqual(notifications, ())
            self.assertIsNone(restore_state)
            writer.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::a-malformed-or-foreign-sexual-resist-entry-never-penalizes-and-never-raises")
    def test_non_dict_mapping_payload_is_penalized(self):
        # The contract says "mapping", not strictly dict: a read-only mapping
        # payload still carries the forced outcome and must penalize.
        from types import MappingProxyType

        target = self._companion("唯讀資料", affinity=73)
        entry = EventEntry(
            kind="sexual_resist",
            actor=str(self.player.key),
            target=str(target.key),
            data=MappingProxyType(
                {"resisted": False, "auto_comply": False, "roll": 55}
            ),
            text_template="x",
        )
        log = EventLog(
            str(self.player.key), "combat_tease", (str(target.key),), (entry,), 0
        )
        notifications, restore_state = self._scan([target], log)
        self.assertEqual(notifications, ())
        self.assertIsNotNone(restore_state)
        self.assertEqual(
            target.relations.affinity_for(self.player), 73 - self.penalty
        )

    def test_internal_failure_restores_membership_and_relations_surfaces(self):
        # A failure mid-scan, after an earlier forced entry already triggered
        # an auto-leave, must restore both the party-membership and the
        # relations in-process surfaces (the idmapper cache is not
        # transaction-aware) -- mirroring _scan_sexual_coercion's restore.
        first = self._companion("先離隊", affinity=70)
        second = self._companion("後失敗", affinity=70)
        entries = (
            _resist_log(
                self.player, first, resisted=False, auto_comply=False, roll=55
            ).entries[0],
            _resist_log(
                self.player, second, resisted=False, auto_comply=False, roll=55
            ).entries[0],
        )
        log = EventLog(
            str(self.player.key), "combat_tease", (str(first.key), str(second.key)), entries, 0
        )
        original = affinity_module.apply_affinity_change
        calls = {"count": 0}

        def failing_writer(npc, player, source, delta):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("injected second write failure")
            return original(npc, player, source, delta)

        with patch(
            "world.rules.cast_settlement.apply_affinity_change",
            side_effect=failing_writer,
        ):
            with self.assertRaises(RuntimeError):
                self._scan([first, second], log)
        # The first forced entry's auto-leave rolled back with the scan's
        # transaction: both companions stay bound at their pre-cast affinity.
        for npc in (first, second):
            npc.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(first.relations.affinity_for(self.player), 70)
        self.assertEqual(second.relations.affinity_for(self.player), 70)
        self.assertEqual(party_ids(self.player), [first.pk, second.pk])
        self.assertEqual(int(first.db.party_member), int(self.player.pk))
        self.assertEqual(int(second.db.party_member), int(self.player.pk))


class OutOfCombatCoercionSettlementTests(OutOfCombatCoercionBase):
    """The scan inside the settlement's outer transaction (settle_out_of_combat_cast)."""

    @covers_requirement("sexual-resist-out-of-combat::the-coercion-scan-runs-inside-the-out-of-combat-settlement-s-outer-transaction-and-rolls-back-on-failure")
    def test_forced_out_of_combat_cast_commits_the_penalty_durably(self):
        target = self._companion("整合強制", affinity=73)
        settlement = self._forced_cast("combat_tease", [target])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertEqual(
            target.relations.affinity_for(self.player), 73 - self.penalty
        )
        # A fresh database read agrees with the in-process value.
        self.assertEqual(self._raw_relations(target), target.db.relations_data)

    @covers_requirement("sexual-resist-out-of-combat::the-coercion-scan-runs-inside-the-out-of-combat-settlement-s-outer-transaction-and-rolls-back-on-failure")
    def test_rejected_cast_never_invokes_the_scan(self):
        target = self._companion("拒絕整合", affinity=73)
        with patch(
            "world.rules.cast_settlement._scan_out_of_combat_sexual_coercion"
        ) as spy:
            settlement = self._settle("definitely_missing", [target])
        self.assertEqual(settlement.result.outcome, "rejected")
        spy.assert_not_called()
        self.assertEqual(target.relations.affinity_for(self.player), 73)
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement("sexual-resist-out-of-combat::the-coercion-scan-runs-inside-the-out-of-combat-settlement-s-outer-transaction-and-rolls-back-on-failure")
    def test_scan_failure_rolls_back_the_entire_cast(self):
        target = self._companion("回滾強制", affinity=73)
        relations_before = target.db.relations_data
        raw_before = self._raw_relations(target)

        def failing_scan(actor, targets, event_log):
            raise RuntimeError("injected coercion scan failure")

        with patch(
            "world.rules.cast_settlement._scan_out_of_combat_sexual_coercion",
            side_effect=failing_scan,
        ):
            with self.assertRaises(RuntimeError):
                self._forced_cast("combat_tease", [target])
        # No partial resolution, practice award, or clock advance persists.
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(self.player.db.skill_proficiency or {}, {})
        target.attributes.reset_cache()
        self.assertEqual(target.db.relations_data, relations_before)
        self.assertEqual(target.relations.affinity_for(self.player), 73)
        self.assertEqual(self._raw_relations(target), raw_before)

    @covers_requirement("sexual-resist-out-of-combat::the-coercion-scan-runs-inside-the-out-of-combat-settlement-s-outer-transaction-and-rolls-back-on-failure")
    def test_clock_advance_failure_rolls_back_the_penalty_without_a_partial_cast(self):
        # The scan committed its penalty inside the outer transaction; a later
        # clock-boundary failure rolls the whole cast back. The durable
        # relations row reverts, and a fresh read (via the in-process object
        # after dropping the idmapper's stale cache, mirroring
        # test_combat_session_sexual_coercion's rollback test) sees the
        # pre-cast value.
        target = self._companion("時鐘回滾", affinity=73)
        relations_before = target.db.relations_data
        raw_before = self._raw_relations(target)
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        with self.assertRaises(RuntimeError):
            self._forced_cast("combat_tease", [target])
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(self.player.db.skill_proficiency or {}, {})
        target.attributes.reset_cache()
        self.assertEqual(target.db.relations_data, relations_before)
        self.assertEqual(target.relations.affinity_for(self.player), 73)
        self.assertEqual(self._raw_relations(target), raw_before)

    @covers_requirement("sexual-resist-out-of-combat::the-coercion-scan-runs-inside-the-out-of-combat-settlement-s-outer-transaction-and-rolls-back-on-failure")
    def test_world_clock_acquisition_failure_rolls_back_the_penalty(self):
        # The ``supplied=False`` branch: after a successful resolution and
        # scan, ``get_world_clock()`` itself raises -- the same post-scan
        # failure path as the clock-advance failure, restored by the
        # settlement-side coercion restore.
        target = self._companion("取鐘回滾", affinity=73)
        relations_before = target.db.relations_data
        raw_before = self._raw_relations(target)

        def failing_clock_lookup():
            raise RuntimeError("injected clock lookup failure")

        with (
            patch(
                "world.rules.cast_settlement.read_world_clock",
                return_value=None,
            ),
            patch(
                "world.rules.cast_settlement.get_world_clock",
                side_effect=failing_clock_lookup,
            ),
            patch("world.rules.action.roll_d100", return_value=1),
        ):
            with self.assertRaises(RuntimeError):
                settle_out_of_combat_cast(
                    self._request("combat_tease", [target])
                )
        self.assertEqual(self.player.db.skill_proficiency or {}, {})
        target.attributes.reset_cache()
        self.assertEqual(target.db.relations_data, relations_before)
        self.assertEqual(target.relations.affinity_for(self.player), 73)
        self.assertEqual(self._raw_relations(target), raw_before)

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_duplicate_target_keys_are_rejected_before_any_penalty(self):
        # Two distinct NPCs sharing one key cannot be addressed separately by
        # the ``sexual_resist`` entry contract (key-keyed), so a resistible
        # cast whose explicit target list repeats a key is rejected fail-closed
        # before resolution -- the scan's key index is sound by construction.
        first = self._companion("同名目標", affinity=73)
        second = self._npc("同名目標", affinity=73)
        with self.assertRaises(ValueError):
            self._forced_cast("combat_tease", [first, second])
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(first.relations.affinity_for(self.player), 73)
        self.assertEqual(second.relations.affinity_for(self.player), 73)

    @covers_requirement("sexual-resist-out-of-combat::the-scan-resolves-forced-targets-against-the-cast-s-own-target-list-with-one-independent-penalty-per-target")
    def test_duplicate_key_guard_does_not_fire_for_non_resistible_acts(self):
        # The duplicate-key rejection is scoped to resistible sexual acts: a
        # non-resistible AREA act whose candidates repeat an entity key never
        # feeds the key-indexed scan (no ``sexual_resist`` entries are
        # emitted), so the guard must not reject the cast.
        (skill, act), = _act_family(
            "關係",
            (
                "test_non_resist_area",
                "測試非抵抗行為",
                "僅存在於測試中的合成非抵抗範圍行為。",
                TargetSpec.AREA,
                {},
                10,
                "腰腹",
                "腰腹",
                0.5,
                ("duo_act_count",),
                ("duo_act_count",),
                (),
                False,
            ),
        )
        first = self._companion("同名非抵抗", affinity=10)
        second = self._npc("同名非抵抗", affinity=10)
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            settlement = self._settle("test_non_resist_area", [first, second])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(first.relations.affinity_for(self.player), 10)
        self.assertEqual(second.relations.affinity_for(self.player), 10)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-act-s-party-auto-leave-notification-reaches-the-player")
    def test_auto_leave_notification_returns_through_cast_settlement(self):
        coerced = self._companion("離隊強制", affinity=70)
        settlement = self._forced_cast("combat_tease", [coerced])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, (AUTO_LEAVE_MESSAGE,))
        self.assertEqual(
            coerced.relations.affinity_for(self.player), 70 - self.penalty
        )
        self.assertNotIn(int(coerced.pk), party_ids(self.player))
        self.assertIsNone(coerced.db.party_member)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-act-s-party-auto-leave-notification-reaches-the-player")
    def test_forced_act_without_auto_leave_sends_no_notification(self):
        companion = self._companion("留在隊上", affinity=73)
        settlement = self._forced_cast("combat_tease", [companion])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertIn(int(companion.pk), party_ids(self.player))

        stranger = self._npc("路人", affinity=73)
        settlement = self._forced_cast("combat_tease", [stranger])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_complied_out_of_combat_cast_applies_no_penalty(self):
        # An auto-complied target (至愛 stage, no roll) cast out of combat.
        target = self._npc("自動服從", affinity=90)
        with patch("world.rules.action.roll_d100") as roll:
            settlement = self._settle("combat_tease", [target])
        roll.assert_not_called()
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertEqual(target.relations.affinity_for(self.player), 90)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-sexual-act-applies-the-same-affinity-penalty-as-an-in-combat-one")
    def test_resisted_out_of_combat_cast_applies_no_penalty(self):
        target = self._npc("成功拒絕", affinity=10)
        with patch("world.rules.action.roll_d100", return_value=100):
            settlement = self._settle("combat_tease", [target])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertEqual(target.relations.affinity_for(self.player), 10)

    def test_penalty_value_comes_from_the_rulebook(self):
        target = self._companion("規則書目標", affinity=73)
        patched = replace(load_config(), sexual_forced_penalty=5)
        with patch("world.rules.cast_settlement.get_config", return_value=patched):
            settlement = self._forced_cast("combat_tease", [target])
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(target.relations.affinity_for(self.player), 68)
