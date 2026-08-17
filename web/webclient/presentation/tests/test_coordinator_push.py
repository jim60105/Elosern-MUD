"""Tests for the epoch-guarded ``publish_panel_update`` push helper.

The trigger service's async generation completes after scheduling; the push
must deliver only when the session's live coordinator still carries the epoch
captured at scheduling time, and must publish nothing (returning ``None``)
after a reset — without bumping the fresh sequence's revision.
"""

from types import SimpleNamespace

from evennia.utils.test_resources import EvenniaTestCase

from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    attach_coordinator,
    publish_panel_update,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry


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
        # The coordinator's mode provider reads the puppet's canonical state.
        self.actor = SimpleNamespace(pk="7", db=SimpleNamespace(active_combat=None))
        self.session = _FakeSession(self.actor)
        self.registry = build_production_registry()

    def _context(self):
        return PresentationContext(actor=self.actor, protocol_version=1)

    def _panels(self):
        context = self._context()
        return {"context_actions": self.registry.render("context_actions", context)}

    def test_matching_epoch_publishes_the_update_envelope(self):
        coordinator = attach_coordinator(self.session, self.registry)
        epoch = coordinator.epoch
        envelope = publish_panel_update(
            self.session,
            self.actor,
            self._panels(),
            context=self._context(),
            expected_epoch=epoch,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["presentation_epoch"], epoch)
        updates = self.session._update_envelopes()
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["presentation_epoch"], epoch)
        self.assertEqual(updates[0]["panels"]["context_actions"]["schema_version"], 5)
        self.assertEqual(coordinator.revision, 1)

    def test_mismatched_epoch_publishes_nothing_and_bumps_no_revision(self):
        coordinator = attach_coordinator(self.session, self.registry)
        stale_epoch = coordinator.epoch
        coordinator.reset()
        self.assertNotEqual(coordinator.epoch, stale_epoch)
        envelope = publish_panel_update(
            self.session,
            self.actor,
            self._panels(),
            context=self._context(),
            expected_epoch=stale_epoch,
        )
        self.assertIsNone(envelope)
        self.assertEqual(self.session.sent, [])
        self.assertEqual(coordinator.revision, 0)

    def test_session_without_a_coordinator_publishes_nothing(self):
        envelope = publish_panel_update(
            self.session,
            self.actor,
            self._panels(),
            context=self._context(),
            expected_epoch="impossible-epoch",
        )
        self.assertIsNone(envelope)
        self.assertEqual(self.session.sent, [])
        self.assertIsInstance(
            self.session.ndb.elosern_coordinator, PresentationCoordinator
        )
