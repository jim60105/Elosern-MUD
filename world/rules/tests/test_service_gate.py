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
    schedule_silenced,
    ServiceVerdict,
    read_service_binding,
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
    def test_a_missing_binding_fails_closed(self):
        # Every bound service capability carries an authored binding; an unset
        # field describes state the assembly never produced, so the resolver
        # refuses instead of defaulting open.
        actor = _actor(self.square)
        with patch("world.rules.service_gate.log_warn") as warned:
            verdict = service_available(actor, self.host, _component(None, None))
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, REASON_MALFORMED_BINDING)
        warned.assert_called_once()

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


class ScheduleSilencePredicateTests(EvenniaTestCase):
    """The traveling-place-bound silence predicate matrix (design D6).

    Every leg gets its own NPC so one row never masks another: bound +
    place-bound + off-anchor silences; person-bound, unbound, at-anchor,
    component-less, and corrupt-anchor rows each pin their own answer. A
    ``None`` location must not raise — the predicate is total because
    settlement calls it before any per-NPC error isolation matters.
    """

    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="silence anchor")
        self.square = create_object(Room, key="silence square")
        from typeclasses.characters import PlayerCharacter

        self.owner = create_object(PlayerCharacter, key="silence owner")
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        self.owner.location = self.square

    def _npc(self, *, room, party=None, binding=None, anchor="unset"):
        from typeclasses.components import Merchant
        from world.rules.party import join_party

        npc = create_object(NPC, key="silence clerk", location=room)
        if party is not None:
            # A REAL reciprocal binding (join_party owns both sides).
            party.location = room
            join_party(npc, party)
        if binding is not None:
            component = Merchant.create(
                npc, service_id="silence_shop", branch_key="plaza_stall"
            )
            npc.components.add(component)
            component.service_binding = binding
            if anchor == "unset":
                component.anchor_room_id = None
            elif anchor == "ghost":
                component.anchor_room_id = "not-an-int"
            elif anchor == "non_room":
                component.anchor_room_id = self.owner.pk
            else:
                component.anchor_room_id = anchor
        return npc

    @covers_requirement(
        "npc-schedule-runtime::silenced-npcs-skip-all-schedule-effects-first"
    )
    def test_bound_place_bound_off_anchor_npc_is_silenced(self):
        clerk = self._npc(
            room=self.square, party=self.owner, binding="place", anchor=self.anchor.pk
        )
        self.assertTrue(schedule_silenced(clerk))

    @covers_requirement(
        "npc-schedule-runtime::silenced-npcs-skip-all-schedule-effects-first"
    )
    def test_every_other_leg_settles_normally(self):
        with self.subTest("person-bound traveler"):
            clerk = self._npc(
                room=self.square, party=self.owner, binding="person", anchor=None
            )
            self.assertFalse(schedule_silenced(clerk))
        with self.subTest("place-bound but unbound party mirror"):
            clerk = self._npc(
                room=self.square, party=None, binding="place", anchor=self.anchor.pk
            )
            self.assertFalse(schedule_silenced(clerk))
        with self.subTest("place-bound standing at its anchor"):
            clerk = self._npc(
                room=self.anchor, party=self.owner, binding="place", anchor=self.anchor.pk
            )
            self.assertFalse(schedule_silenced(clerk))
        with self.subTest("no service component at all"):
            clerk = self._npc(room=self.square, party=self.owner)
            self.assertFalse(schedule_silenced(clerk))
        with self.subTest("unset binding (hand-built default)"):
            clerk = self._npc(
                room=self.square, party=self.owner, binding=None, anchor="unset"
            )
            self.assertFalse(schedule_silenced(clerk))

    @covers_requirement(
        "npc-schedule-runtime::silenced-npcs-skip-all-schedule-effects-first"
    )
    def test_corrupt_anchor_and_missing_location_silence_fails_closed(self):
        # Silence is a policy that mutates nothing; an unresolvable anchor
        # fails closed (silent) where letting settlement run could teleport
        # a companion away from the party.
        with self.subTest("non-integer anchor id"):
            clerk = self._npc(
                room=self.square, party=self.owner, binding="place", anchor="ghost"
            )
            self.assertTrue(schedule_silenced(clerk))
        with self.subTest("anchor id names a non-room object"):
            clerk = self._npc(
                room=self.square, party=self.owner, binding="place", anchor="non_room"
            )
            self.assertTrue(schedule_silenced(clerk))
        with self.subTest("deleted anchor room"):
            ghost = create_object(Room, key="doomed anchor")
            ghost_id = ghost.pk
            clerk = self._npc(
                room=self.square, party=self.owner, binding="place", anchor=ghost_id
            )
            ghost.delete()
            self.assertTrue(schedule_silenced(clerk))
        with self.subTest("None location never raises, reads off-anchor"):
            clerk = self._npc(
                room=self.square, party=self.owner, binding="place", anchor=self.anchor.pk
            )
            clerk.location = None
            self.assertTrue(schedule_silenced(clerk))


class StaleBindingSilenceTests(EvenniaTestCase):
    """A corrupt leftover backref is NOT a binding (party contract).

    bound_owner_of is the repo's single membership interpretation; silence
    must agree with it, or a stale mirror would suppress an unbound NPC's
    schedule forever.
    """

    def setUp(self):
        super().setUp()
        from typeclasses.characters import PlayerCharacter
        from typeclasses.components import Merchant
        from world.rules.party import join_party

        self.anchor = create_object(Room, key="stale anchor")
        self.square = create_object(Room, key="stale square")
        self.owner = create_object(PlayerCharacter, key="stale owner")
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        self.owner.location = self.square
        self.clerk = create_object(NPC, key="stale clerk", location=self.square)
        component = Merchant.create(
            self.clerk, service_id="stale_shop", branch_key="plaza_stall"
        )
        self.clerk.components.add(component)
        component.service_binding = "place"
        component.anchor_room_id = self.anchor.pk
        join_party(self.clerk, self.owner)

    @covers_requirement(
        "npc-schedule-runtime::silenced-npcs-skip-all-schedule-effects-first"
    )
    def test_reciprocal_binding_silences_and_corruption_unsilences(self):
        self.assertTrue(schedule_silenced(self.clerk))
        with self.subTest("owner-side list emptied (dismissal path)"):
            self.owner.db.party = []
            self.assertFalse(schedule_silenced(self.clerk))
            self.owner.db.party = [self.clerk.pk]
        with self.subTest("backref names a different player"):
            self.clerk.db.party_member = self.owner.pk + 99999
            self.assertFalse(schedule_silenced(self.clerk))
            self.clerk.db.party_member = self.owner.pk


class ServiceBindingReportTests(EvenniaTestCase):
    """The read-only binding facts the configuration diagnostics present.

    ``gate_malformed`` mirrors exactly what ``service_available`` refuses on;
    ``anchor_on_person`` is the authored anchored-person binding the importer
    rejects, which the runtime gate deliberately never checked.
    """

    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="report anchor")
        self.square = create_object(Room, key="report square")

    def test_a_person_binding_resolves_no_anchor(self):
        report = read_service_binding(_component("person"))
        self.assertEqual(report.binding, "person")
        self.assertIsNone(report.anchor_room)
        self.assertFalse(report.gate_malformed)
        self.assertFalse(report.anchor_on_person)

    def test_an_anchored_person_binding_is_a_configuration_fact_only(self):
        report = read_service_binding(_component("person", self.anchor.pk))
        self.assertEqual(report.binding, "person")
        self.assertEqual(report.anchor_raw, self.anchor.pk)
        # A person binding never uses (or resolves) the anchor.
        self.assertIsNone(report.anchor_room_id)
        self.assertIsNone(report.anchor_room)
        self.assertFalse(report.gate_malformed)
        self.assertTrue(report.anchor_on_person)

    def test_a_resolvable_place_anchor_is_reported(self):
        report = read_service_binding(_component("place", self.anchor.pk))
        self.assertEqual(report.binding, "place")
        self.assertEqual(report.anchor_room, self.anchor)
        self.assertFalse(report.gate_malformed)

    def test_a_missing_or_non_room_anchor_is_malformed(self):
        for anchor in (None, True, "42", self.square.pk + 99999):
            with self.subTest(anchor=anchor):
                # ``square`` exists but the id above it does not; the non-int
                # and bool values never resolve to a room row.
                report = read_service_binding(_component("place", anchor))
                self.assertTrue(report.gate_malformed)
                self.assertIsNone(report.anchor_room)

    def test_a_room_id_pointing_at_a_non_room_is_malformed(self):
        host = create_object(NPC, key="report host", location=self.square)
        report = read_service_binding(_component("place", host.pk))
        self.assertTrue(report.gate_malformed)
        self.assertIsNone(report.anchor_room)

    def test_a_missing_or_unknown_binding_is_malformed(self):
        for binding in (None, "world"):
            with self.subTest(binding=binding):
                report = read_service_binding(_component(binding))
                self.assertTrue(report.gate_malformed)

    def test_an_invalid_anchor_value_keeps_its_raw_form(self):
        report = read_service_binding(_component("place", "42"))
        self.assertEqual(report.anchor_raw, "42")
        self.assertIsNone(report.anchor_room_id)
        self.assertTrue(report.gate_malformed)


class _ExplodingAnchor(_Fake):
    """A component whose anchor field cannot be read at all."""

    @property
    def anchor_room_id(self):
        raise RuntimeError("anchor unreadable")


class GateShortCircuitTests(EvenniaTestCase):
    """The runtime gate answers without touching fields its rules never use."""

    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="short anchor")
        self.square = create_object(Room, key="short square")
        self.host = create_object(NPC, key="short host", location=self.square)

    def test_a_person_binding_never_reads_the_anchor(self):
        component = _ExplodingAnchor(service_binding="person")
        self.assertTrue(
            service_available(_actor(self.square), self.host, component).allowed
        )

    def test_an_unknown_binding_still_fails_closed_and_warns(self):
        component = _ExplodingAnchor(service_binding="world")
        with patch("world.rules.service_gate.log_warn") as warned:
            verdict = service_available(_actor(self.square), self.host, component)
        self.assertEqual(verdict.reason, REASON_MALFORMED_BINDING)
        self.assertTrue(warned.called)

    def test_a_remote_host_answers_before_any_binding_read(self):
        component = _ExplodingAnchor(service_binding="place")
        verdict = service_available(_actor(self.anchor), self.host, component)
        self.assertEqual(verdict.reason, REASON_REMOTE)
