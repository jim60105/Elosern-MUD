"""Scoped runtime smoke: the confirmed dream path through production code.

Everything here runs the *real* production composition -- the real confirmation
transaction, the real work record, the real pump with its real client
construction from the configured profiles, the real director boundaries, the
real package validation and publication, the real activation boundary and a
fresh committed read. Only the HTTP transport is replaced, by a fake client
class standing in for ``OpenAICompatClient``, so the fixed outputs sit exactly
at the model boundary and nothing is stubbed or fabricated above it.

The deterministic half needs no model service at all: once the package is
committed, the encounter activation and the committed reload run with no
transport in the picture.
"""

import json
from unittest.mock import patch

from server import dream_dispatch_service as pump
from world.narrative import dispatch
from world.narrative import dream_session as lifecycle
from world.narrative.quest_beats import is_scene_package
from world.narrative.tests.test_story_director_beats import (
    StoryDirectorBeatsTestCase,
    _recorded,
)
from world.quests import scene_store
from world.quests.encounter_dispatch import activate_pending_encounters
from world.quests.tests._compile_helpers import CompileRegistryIsolation
from world.rules.tests._combat_session_helpers import open_synthetic_scope

REQUIREMENTS = [
    {"kind": "place", "text": "南門"},
    {"kind": "new_character", "text": "一個女孩"},
    {"kind": "private_commission", "text": "帶她找媽媽"},
]


class _TransportlessClient:
    """Stands in for the real transport client the composition constructs.

    The composition still runs for real: it reads the configured profile and
    builds this class from it. Only ``get_response`` is answered locally.
    """

    responses = None

    def __init__(self, profile):
        self.profile = profile

    def get_response(self, descriptor):
        return type(self).responses.get_response(descriptor)


class DreamDispatchSmokeTests(CompileRegistryIsolation, StoryDirectorBeatsTestCase):
    """One confirmed direction becomes one real, activated scene package."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "items",
            "guild_branches",
            "archetypes",
            "anchors",
            "anchor_placements",
        )
        super().setUp()
        from world.ai.scenario_director import register_scenario_director
        from world.quests.tests._compile_helpers import _anchor_key
        from world.quests.tests._scene_package_fixtures import package as _package

        register_scenario_director()
        self.anchor = _anchor_key()
        # A real anchor room: the activation boundary resolves a permanent
        # anchor locator through the map authority, not through a plain room.
        from evennia.utils.create import create_object
        from typeclasses.rooms import AnchorRoom

        self.anchor_room = create_object(AnchorRoom, key="南門")
        self.anchor_room.db.anchor_key = self.anchor
        self.owner.location = self.anchor_room
        self.package_payload = _package()
        self.owner.guild_rank = self.package_payload["quest"]["rank"]
        pump.reset_pump_state()
        dispatch.register_pump(None)
        self.addCleanup(pump.stop_pump)
        self.addCleanup(pump.reset_pump_state)
        self.addCleanup(dispatch.register_pump, None)

    # -- fixtures ----------------------------------------------------------

    def _extended_blueprint(self):
        extended = dict(self.package_payload["quest"])
        extended["display_name"] = self.package_payload["display_name"]
        for key in (
            "roles",
            "relationships",
            "knowledge",
            "encounters",
            "dialogue",
            "commissions",
            "outcome_groups",
        ):
            if key in self.package_payload:
                extended[key] = self.package_payload[key]
        return extended

    def _responses(self):
        client = _recorded("quest_seed")
        client.add_response(
            lambda descriptor: descriptor.schema_id == "scenario_director",
            json.dumps(self._extended_blueprint(), ensure_ascii=False),
        )
        return client

    def _confirm_the_direction(self):
        session = lifecycle.open_session(str(self.owner.pk), tick=self.now)
        from world.narrative.authoring import get_draft
        from world.narrative.dream_session import get_session

        direction = {
            "kind": "new_story",
            "summary": "在南門遇見一個女孩，帶她找媽媽。",
            "requirements": list(REQUIREMENTS),
        }
        # The shown draft first, exactly as the surface presents it, so the real
        # confirmation echoes the reviewed version through the review gate.
        lifecycle.preserve_draft(
            session.session_id, str(self.owner.pk), dict(direction), tick=self.now
        )
        handle = get_session(session.session_id, str(self.owner.pk)).draft_id
        shown = get_draft(handle, str(self.owner.pk)).direction["requirement_version"]
        self.assertTrue(shown)
        # The real confirmation: a durable request, its one work record and the
        # confirmed session closure in one transaction.
        with self.captureOnCommitCallbacks(execute=True):
            request = lifecycle.confirm_session(
                session.session_id,
                str(self.owner.pk),
                direction={**direction, "requirement_version": shown},
                tick=self.now,
            )
        return request

    # -- the smoke ---------------------------------------------------------

    def test_one_confirmed_direction_becomes_one_activated_scene(self):
        responses = self._responses()
        _TransportlessClient.responses = responses
        with patch("world.ai.client.OpenAICompatClient", _TransportlessClient):
            request = self._confirm_the_direction()
            work = dispatch.find_by_submission(request.submission_key)
            self.assertIsNotNone(work)
            self.assertEqual(work.state, dispatch.STATE_QUEUED)

            # The pump composition runs for real: profiles, client construction,
            # one generation at a time, the two stages and the publication.
            self.assertTrue(pump.start_pump())
            settled = dispatch.find_work(work.dispatch_id)

        self.assertEqual(settled.state, dispatch.STATE_ARRANGED)
        self.assertTrue(settled.package_id)
        self.assertTrue(settled.beat_id)
        self.assertTrue(settled.decision_id)
        # Two model calls only: one story stage, one scene stage.
        self.assertEqual(len(responses.calls), 2)
        published = scene_store.read_package(settled.package_id)
        self.assertIsNotNone(published)
        self.assertTrue(is_scene_package(published.payload))
        self.assertEqual(
            published.payload["encounters"], self.package_payload["encounters"]
        )
        # The package carries a durable source identity of its own, so a replay
        # can never publish a second one for the same arrangement.
        self.assertTrue(published.source_id.startswith("nbeat:"))
        # Publication alone accepts nothing and pays nothing.
        from world.quests.runtime import read_records

        self.assertEqual(read_records(self.owner), [])

        # Deterministic half, no transport: the owner at the locator meets the
        # published encounter, and a repeat reload neither re-publishes nor
        # re-materializes anyone.
        with self.captureOnCommitCallbacks(execute=True):
            activations = activate_pending_encounters(
                self.owner, room=self.owner.location, tick=self.now
            )
        from world.quests.models import SceneEncounterRuntime

        self.assertTrue(activations)
        # The publication committed with no connected session for this owner, so
        # the pump attempted no post-commit activation -- offline publication is
        # exactly a durable arrangement -- and the real exploration boundary then
        # materialized the encounter at the owner's actual position.
        rows = [
            (row.scene_id, row.player_id, row.state)
            for row in SceneEncounterRuntime.objects.filter(
                package__package_id=settled.package_id
            )
        ]
        self.assertEqual(len(rows), 2, rows)
        self.assertEqual({state for _, _, state in rows}, {"activated"})
        self.assertEqual({player for _, player, _ in rows}, {int(self.owner.pk)})
        daughter = scene_store.get_role_binding(settled.package_id, "daughter")
        self.assertIsNotNone(daughter)
        # One real actor, standing where the encounter declared, with its own
        # committed dialogue phase.
        from evennia.objects.models import ObjectDB

        materialized = ObjectDB.objects.filter(pk=daughter.npc_id).first()
        self.assertIsNotNone(materialized)
        self.assertEqual(materialized.location.pk, self.owner.location.pk)
        phase = scene_store.get_dialogue_phase(settled.package_id, "daughter")
        self.assertIsNotNone(phase)
        self.assertEqual(phase.revision, 0)
        # A committed reload: fresh reads return the same identities, and the
        # second pass activates nothing new.
        reloaded_work = dispatch.find_work(work.dispatch_id)
        self.assertEqual(reloaded_work.package_id, settled.package_id)
        self.assertEqual(
            scene_store.list_role_bindings(settled.package_id)[0].npc_id,
            daughter.npc_id,
        )
        self.assertEqual(
            activate_pending_encounters(self.owner, room=self.owner.location, tick=self.now),
            (),
        )

    def test_the_smoke_needs_no_model_for_the_deterministic_half(self):
        responses = self._responses()
        _TransportlessClient.responses = responses
        with patch("world.ai.client.OpenAICompatClient", _TransportlessClient):
            request = self._confirm_the_direction()
            pump.start_pump()
        settled = dispatch.find_work(
            dispatch.find_by_submission(request.submission_key).dispatch_id
        )
        self.assertEqual(settled.state, dispatch.STATE_ARRANGED)
        # From here on, nothing may call the transport again.
        calls = len(responses.calls)
        with self.captureOnCommitCallbacks(execute=True):
            activate_pending_encounters(self.owner, room=self.owner.location, tick=self.now)
        pump.kick()
        self.assertEqual(len(responses.calls), calls)
        self.assertEqual(
            dispatch.find_work(settled.dispatch_id).state, dispatch.STATE_ARRANGED
        )
