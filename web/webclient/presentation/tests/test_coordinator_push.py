"""Tests for the epoch-guarded ``publish_panel_update`` push helper.

The trigger service's async generation completes after scheduling; the push
must deliver only when the session's live coordinator still carries the epoch
captured at scheduling time, and must publish nothing (resolving ``None``)
after a reset — without bumping the fresh sequence's revision.
"""

from types import SimpleNamespace

from evennia.utils.test_resources import EvenniaTestCase

from web.webclient.presentation.coordinator import (
    attach_coordinator,
    publish_panel_update,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.tests._support import publication_result


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace(elosern_coordinator=None, elosern_actor_id=None)
        self.sessid = 41

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def _update_envelopes(self):
        return [call["ui_update"][0][0] for call in self.sent if "ui_update" in call]


class PublishPanelUpdateTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        from world.rules.clock import get_world_clock

        # The envelope carries serialized server time from the world clock.
        get_world_clock()
        # The coordinator's mode provider reads the puppet's canonical state
        # (active combat + dialogue session); the real DBHandler returns None
        # for unset attributes, so the fake mirrors that.
        self.actor = SimpleNamespace(
            pk="7", db=SimpleNamespace(active_combat=None, dialogue_session=None)
        )
        self.session = _FakeSession(self.actor)
        self.registry = build_production_registry()

    def _context(self):
        return PresentationContext(actor=self.actor, protocol_version=1)

    def _panels(self):
        context = self._context()
        return {"context_actions": self.registry.render("context_actions", context)}

    def test_matching_epoch_publishes_only_a_changed_candidate(self):
        coordinator = attach_coordinator(self.session, self.registry)
        # A live push always follows the session's initial sync, so the
        # fixture starts from a committed baseline (revision 1) and only the
        # pushed delta remains under assertion.
        coordinator.full_snapshot(self._context())
        self.session.sent.clear()
        epoch = coordinator.epoch
        # An identical candidate matches the published baseline: nothing is
        # transmitted and no revision is consumed.
        unchanged = publication_result(
            publish_panel_update(
                self.session,
                self.actor,
                self._panels(),
                context=self._context(),
                expected_epoch=epoch,
            )
        )
        self.assertIsNotNone(unchanged)
        self.assertFalse(unchanged.published)
        self.assertEqual(unchanged.kind, "unchanged")
        self.assertEqual(unchanged.revision, 1)
        self.assertEqual(self.session.sent, [])
        self.assertEqual(coordinator.revision, 1)

        # A genuinely different candidate is one exact-base delta. The
        # registry's own internal-failure form is a real, schema-exact payload
        # (the one a failing presenter produces) and differs from the published
        # non-internal unavailable form.
        changed_panels = {
            "context_actions": self.registry.build_unavailable(
                "context_actions", internal=True, correlation_id="a" * 32
            )
        }
        self.assertNotEqual(changed_panels, self._panels())
        receipt = publication_result(
            publish_panel_update(
                self.session,
                self.actor,
                changed_panels,
                context=self._context(),
                expected_epoch=epoch,
            )
        )
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt.published)
        self.assertEqual(receipt.kind, "delta")
        updates = self.session._update_envelopes()
        self.assertEqual(len(updates), 1)
        envelope = updates[0]
        self.assertEqual(envelope["presentation_epoch"], epoch)
        self.assertEqual(envelope["base_revision"], 1)
        self.assertEqual(envelope["removed_panels"], [])
        self.assertEqual(envelope["revision"], 2)
        self.assertEqual(receipt.revision, envelope["revision"])
        self.assertEqual(
            envelope["panels"]["context_actions"],
            changed_panels["context_actions"],
            "the delta carries exactly the pushed candidate",
        )
        # Taken from the registry that rendered the panel (which sources it
        # from ``CONTEXT_ACTIONS_SCHEMA_VERSION``), so the assertion pins the
        # pushed payload to the registered contract instead of a stale literal.
        self.assertEqual(
            changed_panels["context_actions"]["schema_version"],
            self.registry.spec("context_actions").schema_version,
        )
        self.assertEqual(coordinator.revision, 2)

    def test_mismatched_epoch_publishes_nothing_and_bumps_no_revision(self):
        coordinator = attach_coordinator(self.session, self.registry)
        stale_epoch = coordinator.epoch
        coordinator.reset()
        self.assertNotEqual(coordinator.epoch, stale_epoch)
        receipt = publication_result(
            publish_panel_update(
                self.session,
                self.actor,
                self._panels(),
                context=self._context(),
                expected_epoch=stale_epoch,
            )
        )
        self.assertIsNone(receipt)
        self.assertEqual(self.session.sent, [])
        self.assertEqual(coordinator.revision, 0)

    def test_session_without_a_coordinator_publishes_nothing(self):
        receipt = publication_result(
            publish_panel_update(
                self.session,
                self.actor,
                self._panels(),
                context=self._context(),
                expected_epoch="impossible-epoch",
            )
        )
        self.assertIsNone(receipt)
        self.assertEqual(self.session.sent, [])
        self.assertIsNone(
            self.session.ndb.elosern_coordinator,
            "a guarded push must not attach a coordinator as a side effect",
        )
