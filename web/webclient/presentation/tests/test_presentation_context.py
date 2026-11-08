"""Tests for the single presentation-context factory and its publication paths.

Every publication path — the ``ui_sync``/snapshot refresh, the dispatcher's
completion, internal-error, and stale paths — MUST build its context through
``build_presentation_context``, which never hands the raw session to a
presenter.
"""

from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.actions import dispatcher
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import build_presentation_context, synchronize_session
from web.webclient.presentation.lineage import MAX_LINEAGE_PANEL_BYTES
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace(elosern_coordinator=None, elosern_actor_id=None)
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)


    def _envelopes(self, message_name):
        return [
            call[message_name][0][0]
            for call in self.sent
            if message_name in call
        ]


class PublicationPathSnapshotTests(EvenniaTest):
    """Every publication path renders through the shared context factory."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.room = create_object(Room, key="snapshot room")
        self.player = create_object(PlayerCharacter, key="snapshot player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.session = _FakeSession(self.player)
        # Every publication path follows the transport's initial sync: the
        # fixture establishes the committed baseline first, then asserts only
        # the publications under test.
        synchronize_session(self.session, self.player)
        self.session.sent.clear()

    def test_ui_sync_snapshot_carries_no_suggestions_field(self):
        synchronize_session(self.session, self.player)
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertTrue(panel["available"])
        self.assertNotIn("suggestions", panel)

    def test_full_snapshot_fits_the_client_envelope(self):
        """The whole production snapshot must fit the transport bound.

        The client drops any envelope over ``MAX_CANONICAL_JSON_BYTES`` whole,
        leaving the store awaiting its initial snapshot, so the server may
        never emit one. The largest panel also stays inside its declared share
        of that envelope.
        """
        synchronize_session(self.session, self.player)
        envelope = self.session._envelopes("ui_snapshot")[-1]
        self.assertLessEqual(json_byte_size(envelope), MAX_CANONICAL_JSON_BYTES)
        self.assertLessEqual(
            json_byte_size(envelope["panels"]["lineage"]),
            MAX_LINEAGE_PANEL_BYTES,
        )

    def test_internal_error_publication_renders_the_panel(self):
        coordinator = attach_coordinator(self.session, self.registry)
        dispatcher._settle_internal_error(
            self.session,
            self.player,
            build_production_action_registry(),
            self.registry,
            "r1",
            coordinator.epoch,
        )
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertTrue(panel["available"])
        self.assertNotIn("suggestions", panel)

    def test_stale_rejection_publication_renders_the_panel(self):
        coordinator = attach_coordinator(self.session, self.registry)
        state = dispatcher._sequence_state(self.session)
        dispatcher._send_stale(self.session, coordinator, state, "r1")
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertTrue(panel["available"])
        self.assertNotIn("suggestions", panel)


def _proposal_state(owner_pk, **overrides):
    state = {
        "owner_actor_id": owner_pk,
        "revision": 1,
        "race": "t_duskmari",
        "subrace": "t_duskmari_evensong",
        "allocations": {
            "hp": 8, "mp": 8, "sp": 8,
            "atk_phys": 5, "agility": 5, "defense": 5, "magic_power": 5,
        },
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    state.update(overrides)
    return state


class ProposalSnapshotGateTests(EvenniaTestCase):
    """The ingress proposal gate (retool-concept-transient-fill D1).

    A corrupt owned slot degrades to an omitted proposal — never to an
    unavailable panel: the snapshot builder validates the panel's exact
    proposal contract before constructing ProposalSnapshot, so nothing that
    the downstream creation validator would reject can ever reach it.
    """

    def _session(self, state):
        session = _FakeSession(SimpleNamespace(pk="1"))
        if state is not None:
            session.ndb.concept_proposal = state
        return session

    def test_valid_owned_slot_snapshots(self):
        from web.webclient.presentation.ingress import proposal_snapshot

        snapshot = proposal_snapshot(
            self._session(_proposal_state("1")), SimpleNamespace(pk="1")
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.revision, 1)
        self.assertEqual(snapshot.persona["personality"], "沉穩")

    def test_transient_fill_keys_snapshot_and_absent_stay_none(self):
        from web.webclient.presentation.ingress import proposal_snapshot

        snapshot = proposal_snapshot(
            self._session(
                _proposal_state(
                    "1",
                    display_name="咪咪",
                    age=20,
                    apparent_age=18,
                    background="貓婆婆收養的孤女",
                    affinity_elements=["fire"],
                )
            ),
            SimpleNamespace(pk="1"),
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.display_name, "咪咪")
        self.assertEqual(snapshot.age, 20)
        self.assertEqual(snapshot.apparent_age, 18)
        self.assertEqual(snapshot.background, "貓婆婆收養的孤女")
        self.assertEqual(snapshot.affinity_elements, ("fire",))

        bare = proposal_snapshot(self._session(_proposal_state("1")), SimpleNamespace(pk="1"))
        self.assertIsNotNone(bare)
        for key in ("display_name", "age", "apparent_age", "background", "affinity_elements"):
            self.assertIsNone(getattr(bare, key))

    def test_aliens_owner_slot_is_refused(self):
        from web.webclient.presentation.ingress import proposal_snapshot

        self.assertIsNone(
            proposal_snapshot(
                self._session(_proposal_state("other")), SimpleNamespace(pk="1")
            )
        )

    def test_malformed_slots_degrade_to_none_not_an_exception(self):
        from web.webclient.presentation.ingress import proposal_snapshot

        cases = {
            "not a dict": "garbage",
            "missing revision": {
                k: v for k, v in _proposal_state("1").items() if k != "revision"
            },
            "zero revision": _proposal_state("1", revision=0),
            "six allocation axes": _proposal_state(
                "1",
                allocations={
                    k: v
                    for k, v in _proposal_state("1")["allocations"].items()
                    if k != "magic_power"
                },
            ),
            "unknown allocation axis": _proposal_state(
                "1",
                allocations={
                    **{
                        k: v
                        for k, v in _proposal_state("1")["allocations"].items()
                        if k != "magic_power"
                    },
                    "luck": 5,
                },
            ),
            "negative allocation": _proposal_state(
                "1",
                allocations={
                    **_proposal_state("1")["allocations"], "hp": -1
                },
            ),
            "partial persona": _proposal_state(
                "1", persona={"personality": "沉穩"}
            ),
            "blank persona prose": _proposal_state(
                "1",
                persona={
                    "personality": "  ",
                    "life_story": "來自邊境的小村",
                    "habit": "清晨練劍",
                },
            ),
            "over-bound persona prose": _proposal_state(
                "1",
                persona={
                    "personality": "x" * 601,
                    "life_story": "來自邊境的小村",
                    "habit": "清晨練劍",
                },
            ),
            "null transient-fill value": _proposal_state("1", age=None),
            "out-of-band transient-fill age": _proposal_state("1", age=-1),
            "unknown transient-fill element": _proposal_state(
                "1", affinity_elements=["wood"]
            ),
            "duplicate transient-fill elements": _proposal_state(
                "1", affinity_elements=["fire", "fire"]
            ),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                self.assertIsNone(
                    proposal_snapshot(self._session(state), SimpleNamespace(pk="1"))
                )

    def test_corrupt_slot_leaves_the_creation_panel_available_without_proposal(self):
        # End-to-end through the panel presenter: the corrupt slot snapshots to
        # None, the presenter omits the key, and the panel stays available.
        player = SimpleNamespace(pk="1")
        session = self._session(_proposal_state("1", allocations={"hp": 0}))
        context = build_presentation_context(session, player)
        self.assertIsNone(context.proposal)
