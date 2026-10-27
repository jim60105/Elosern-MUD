"""Command-surface tests for ``church join <npc>`` (aliases 入教／洗禮).

The command is thin: exact local ``ChurchHost`` target resolution (a name/alias
or the browser route's ``#<id>`` form), the schedule gate, and the deterministic
``world.rules.church.py::enroll`` rite. Shipped-content keys are imported as
names from the rules module (never written as literal tokens), so this module
stays outside the test-data ledger.

The celebrant host and the caller share one invented room; the caller is a
plain human with no royal subrace, exercising the ordinary branch (the
vessel branch is covered by the data-contract rules suite
``world.rules.tests.test_church_enrollment``).
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import ChurchHost
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.church import CmdChurchJoin
from world.rules.church import SISTER_VESTMENTS_KEY
from world.rules.clock import WorldClock
from world.rules.npc_schedules import SCHEDULE_BLOCKED_REASON


class ChurchJoinCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="t_church_hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.celebrant = self._host("t_celebrant", self.hall)
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)

    def _host(self, key, room):
        """Create one clergy host place-bound to ``room``."""
        host = create_object(NPC, key=key, location=room)
        component = ChurchHost.create(host, service_id=key)
        # The authored church capability is place-bound to its venue room; a
        # component without a persisted binding fails closed in the shared gate.
        component.service_binding = "place"
        component.anchor_room_id = room.pk
        host.components.add(component)
        return host

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_join_beside_an_on_duty_host_succeeds(self):
        self.call(CmdChurchJoin(), "t_celebrant", "你已加入光明教會")
        self.assertIsNotNone(getattr(self.char1.db, "church", None))
        inventory = list(self.char1.db.inventory or [])
        self.assertEqual(
            inventory.count(SISTER_VESTMENTS_KEY),
            1,
            f"enrollment hands over exactly one vestment: {inventory}",
        )

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_alias_入教_runs_the_same_surface(self):
        self.call(CmdChurchJoin(), "t_celebrant", "你已加入光明教會", cmdstring="入教")

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_alias_洗禮_runs_the_same_surface(self):
        self.call(CmdChurchJoin(), "t_celebrant", "你已加入光明教會", cmdstring="洗禮")

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_missing_target_prints_the_usage_line(self):
        self.call(CmdChurchJoin(), "", "用法：church join <npc>")
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_no_local_church_host_is_a_stable_rejection(self):
        self.char1.location = create_object(Room, key="t_empty")
        self.call(CmdChurchJoin(), "t_celebrant", "這裡沒有教會的神職人員")
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_a_non_clergy_target_is_never_substituted(self):
        bystander = create_object(NPC, key="t_bystander", location=self.hall)
        self.call(CmdChurchJoin(), bystander.key, "這裡沒有教會的神職人員")
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_the_named_clergy_member_is_the_only_target(self):
        second = self._host("t_second_celebrant", self.hall)
        self.call(CmdChurchJoin(), second.key, "你已加入光明教會")
        # Two co-present clergy members are never "ambiguous" here: the player
        # named one, and only that exact provider is validated at submission.
        self.assertIsNotNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_exact_id_form_targets_that_clergy_member(self):
        second = self._host("t_second_celebrant", self.hall)
        self.call(CmdChurchJoin(), f"#{second.pk}", "你已加入光明教會")
        self.assertIsNotNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_an_absent_exact_id_rejects_without_substitution(self):
        absent_pk = int(getattr(self.hall, "pk", 0)) + 10_000
        self.call(CmdChurchJoin(), f"#{absent_pk}", "這裡沒有教會的神職人員")
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_a_stale_exact_id_is_refused_beside_second_clergy(self):
        # The browser route pre-fills ``#<id>``; submitting it after that host
        # left must reject, never enrolling through the remaining clergy.
        self._host("t_second_celebrant", self.hall)
        absent_pk = int(getattr(self.hall, "pk", 0)) + 10_000
        before = list(self.char1.db.inventory or ())
        self.call(CmdChurchJoin(), f"#{absent_pk}", "這裡沒有教會的神職人員")
        self.assertIsNone(getattr(self.char1.db, "church", None))
        self.assertEqual(list(self.char1.db.inventory or ()), before)

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_hidden_clergy_is_never_named_or_substituted(self):
        self.celebrant.locks.add("view:false()")
        self.call(CmdChurchJoin(), "t_celebrant", "這裡沒有教會的神職人員")
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_off_duty_host_is_a_stable_rejection(self):
        self.celebrant.db.schedule_state = "busy"
        self.call(CmdChurchJoin(), "t_celebrant", SCHEDULE_BLOCKED_REASON)
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_re_enrollment_is_a_stable_rejection(self):
        self.call(CmdChurchJoin(), "t_celebrant", "你已加入光明教會")
        before = list(self.char1.db.inventory or [])
        self.call(CmdChurchJoin(), "t_celebrant", "你已屬光明教會")
        self.assertEqual(list(self.char1.db.inventory or []), before)
        self.assertIsNotNone(
            self.char1.db.church, "the ledger stays committed"
        )

    @covers_requirement("church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost")
    def test_off_anchor_celebrant_refuses_with_the_gate_line(self):
        # A place-bound host standing away from its anchor refuses with the
        # shared gate line, never framing it as an enrollment failure.
        from world.rules.service_gate import MESSAGE_OFF_ANCHOR

        square = create_object(Room, key="t_square")
        self.celebrant.location = square
        self.char1.location = square
        self.call(CmdChurchJoin(), "t_celebrant", MESSAGE_OFF_ANCHOR)
        self.assertIsNone(getattr(self.char1.db, "church", None))


if __name__ == "__main__":
    import unittest

    unittest.main()
