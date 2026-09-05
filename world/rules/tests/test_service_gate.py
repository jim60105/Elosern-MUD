"""Pure resolver matrix for the shared service-availability gate.

Every (co-location × binding × anchor-state) combination maps to an exact
verdict, malformed stored data fails closed with one debounced warn, and the
registry-owned message is available to callers. No game state is exercised —
the gate reads plain location/binding facts, so fakes stand in for actor and
host while only anchor rooms (resolved by dbid) need real objects.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.service_gate import (
    MESSAGE_OFF_ANCHOR,
    REASON_MALFORMED_BINDING,
    REASON_OFF_ANCHOR,
    REASON_REMOTE,
    ServiceVerdict,
    service_available,
)


class _Fake:
    """Plain attribute bag: Mock auto-attributes would fake the debounce."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)


def _fake(room):
    return _Fake(location=room), _Fake(location=room, key="fake host")


def _component(binding=None, anchor_room_id=None):
    return _Fake(service_binding=binding, anchor_room_id=anchor_room_id)


class ServiceGateVerdictTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="anchor room")
        self.square = create_object(Room, key="town square")

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_co_location_rules_first(self):
        # A place-bound host in another room is remote, never off_anchor.
        actor, host = _fake(self.square)
        host.location = self.anchor  # host at anchor, actor elsewhere
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, host, component)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, REASON_REMOTE)
        # A missing actor location is remote too.
        actor.location = None
        self.assertEqual(
            service_available(actor, host, component).reason, REASON_REMOTE
        )

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_off_anchor_traveling_host_is_refused_by_name(self):
        actor, host = _fake(self.square)
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, host, component)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, REASON_OFF_ANCHOR)
        self.assertIsInstance(MESSAGE_OFF_ANCHOR, str)
        self.assertTrue(MESSAGE_OFF_ANCHOR)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_place_bound_host_at_anchor_is_allowed(self):
        actor, host = _fake(self.anchor)
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, host, component)
        self.assertTrue(verdict.allowed)
        self.assertIsNone(verdict.reason)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_person_bound_host_serves_anywhere_co_located(self):
        for room in (self.anchor, self.square):
            actor, host = _fake(room)
            component = _component("person", None)
            self.assertTrue(service_available(actor, host, component).allowed)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_unset_binding_reads_as_the_default_co_presence(self):
        # A component the roster never converged (hand-built NPC) has no
        # authored binding: design D1 defaults it to person, never malformed.
        actor, host = _fake(self.square)
        self.assertTrue(
            service_available(actor, host, _component(None, None)).allowed
        )

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_verdict_is_frozen(self):
        with self.assertRaises(Exception):
            ServiceVerdict(True).allowed = False  # type: ignore[misc]

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_malformed_stored_data_fails_closed_once_warned(self):
        actor, host = _fake(self.square)
        unknown = _component("portable", None)
        with patch("world.rules.service_gate.log_warn") as warned:
            for _ in range(3):
                verdict = service_available(actor, host, unknown)
            self.assertFalse(verdict.allowed)
            self.assertEqual(verdict.reason, REASON_MALFORMED_BINDING)
            # place-bound with an anchor whose room was deleted: malformed.
            ghost_anchor = create_object(Room, key="ghost anchor")
            ghost_id = ghost_anchor.pk
            ghost_anchor.delete()
            deleted_anchor = _component("place", ghost_id)
            self.assertEqual(
                service_available(actor, host, deleted_anchor).reason,
                REASON_MALFORMED_BINDING,
            )
            # place-bound with a non-integer anchor id: malformed.
            self.assertEqual(
                service_available(
                    actor, host, _component("place", "not-an-int")
                ).reason,
                REASON_MALFORMED_BINDING,
            )
            # One debounced warn per host covers ALL malformed rows above.
            self.assertEqual(warned.call_count, 1)
            event = warned.call_args_list[0]
            self.assertEqual(event.args[0], "service_gate_malformed_binding")
            self.assertEqual(event.kwargs["context"]["char"], "fake host")
            # A different host re-arms its own single warn.
            other_actor, other_host = _fake(self.square)
            service_available(other_actor, other_host, unknown)
            self.assertEqual(warned.call_count, 2)
