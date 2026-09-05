"""Pure resolver matrix for the shared service-availability gate.

Every (co-location × binding × anchor-state) combination maps to an exact
verdict, malformed stored data fails closed with one debounced warn, and the
registry-owned message is available to callers. Hosts are REAL objects: the
malformed debounce lives on ``host.ndb``, which only exists on typeclass
instances. Actors are fakes — the resolver reads nothing from the actor but
``location``.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
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
    """Plain attribute bag for the actor: Mock auto-attributes would fake reads."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)


def _actor(room):
    return _Fake(location=room)


def _component(binding=None, anchor_room_id=None):
    return _Fake(service_binding=binding, anchor_room_id=anchor_room_id)


class ServiceGateVerdictTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="anchor room")
        self.square = create_object(Room, key="town square")
        self.host = create_object(NPC, key="gate host", location=self.square)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_co_location_rules_first(self):
        # A place-bound host in another room is remote, never off_anchor.
        self.host.location = self.anchor  # host at anchor, actor elsewhere
        actor = _actor(self.square)
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, self.host, component)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, REASON_REMOTE)
        # A missing actor location is remote too.
        actor.location = None
        self.assertEqual(
            service_available(actor, self.host, component).reason, REASON_REMOTE
        )

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_off_anchor_traveling_host_is_refused_by_name(self):
        actor = _actor(self.square)
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, self.host, component)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, REASON_OFF_ANCHOR)
        self.assertIsInstance(MESSAGE_OFF_ANCHOR, str)
        self.assertTrue(MESSAGE_OFF_ANCHOR)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_place_bound_host_at_anchor_is_allowed(self):
        self.host.location = self.anchor
        actor = _actor(self.anchor)
        component = _component("place", self.anchor.pk)
        verdict = service_available(actor, self.host, component)
        self.assertTrue(verdict.allowed)
        self.assertIsNone(verdict.reason)

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_person_bound_host_serves_anywhere_co_located(self):
        for room in (self.anchor, self.square):
            self.host.location = room
            actor = _actor(room)
            component = _component("person", None)
            self.assertTrue(
                service_available(actor, self.host, component).allowed
            )

    @covers_requirement(
        "service-anchoring::one-read-only-resolver-answers-service-availability-with-a-stable-vocabulary"
    )
    def test_unset_binding_reads_as_the_default_co_presence(self):
        # A component the roster never converged (hand-built NPC) has no
        # authored binding: design D1 defaults it to person, never malformed.
        actor = _actor(self.square)
        self.assertTrue(
            service_available(actor, self.host, _component(None, None)).allowed
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
        actor = _actor(self.square)
        unknown = _component("portable", None)
        with patch("world.rules.service_gate.log_warn") as warned:
            for _ in range(3):
                verdict = service_available(actor, self.host, unknown)
            self.assertFalse(verdict.allowed)
            self.assertEqual(verdict.reason, REASON_MALFORMED_BINDING)
            # place-bound with an anchor whose room was deleted: malformed.
            ghost_anchor = create_object(Room, key="ghost anchor")
            ghost_id = ghost_anchor.pk
            ghost_anchor.delete()
            deleted_anchor = _component("place", ghost_id)
            self.assertEqual(
                service_available(actor, self.host, deleted_anchor).reason,
                REASON_MALFORMED_BINDING,
            )
            # place-bound with a non-integer anchor id: malformed.
            self.assertEqual(
                service_available(
                    actor, self.host, _component("place", "not-an-int")
                ).reason,
                REASON_MALFORMED_BINDING,
            )
            # place-bound with an anchor id pointing at a NON-ROOM object:
            # the persisted anchor must be a room or the row is corrupt.
            squatter = create_object(NPC, key="anchor squatter", location=self.square)
            self.assertEqual(
                service_available(
                    actor, self.host, _component("place", squatter.pk)
                ).reason,
                REASON_MALFORMED_BINDING,
            )
            # One debounced warn per host covers ALL malformed rows above.
            self.assertEqual(warned.call_count, 1)
            event = warned.call_args_list[0]
            self.assertEqual(event.args[0], "service_gate_malformed_binding")
            self.assertEqual(event.kwargs["context"]["char"], "gate host")
            # The debounce lives on host.ndb (design D3), not an instance
            # attribute: a refetched instance of the SAME host stays debounced.
            refetched = NPC.objects.get(pk=self.host.pk)
            service_available(actor, refetched, unknown)
            self.assertEqual(warned.call_count, 1)
            # A different host re-arms its own single warn.
            other_host = create_object(
                NPC, key="other gate host", location=self.square
            )
            service_available(actor, other_host, unknown)
            self.assertEqual(warned.call_count, 2)
