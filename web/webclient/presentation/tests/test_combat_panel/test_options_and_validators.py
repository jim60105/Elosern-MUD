import unittest
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import build_production_registry



class OptionsSnapshotFactoryTests(unittest.TestCase):
    """Read-side options_snapshot factory (task 1.5; review hardening)."""

    def test_absent_state_yields_none(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Session:
            class _Ndb:
                options_state = None

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

    def test_repuppeted_owner_is_refused(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = {
                    "owner_actor_id": 99,
                    "fingerprint": "fp",
                    "status": "ready",
                    "generation_token": 1,
                    "displayed": [],
                }

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

    def test_malformed_state_never_raises(self):
        # A corrupt ephemeral write must degrade to an inert snapshot (or
        # None), never raise into the ingress/dispatcher publication path
        # (review finding).
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = "not a dict"

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

        class _BadCards:
            ndb = type(
                "Ndb",
                (),
                {"options_state": {"displayed": [42], "status": "ready"}},
            )()
            puppet = _Actor()

        snapshot = options_snapshot(_BadCards())
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.displayed, ())
        # The non-dict card entry is dropped; the presenter renders the
        # ready-without-valid-cards case as inert unavailable.
        from web.webclient.presentation.context import PresentationContext
        from web.webclient.presentation.registry import build_production_registry

        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object
        from evennia.utils.test_resources import EvenniaTestCase

        room = create_object(Room, key="備援測試房")
        player = create_object(PlayerCharacter, key="備援測試角色")
        player.race = "human"
        player.apply_race_baseline()
        player.location = room
        payload = build_production_registry().render(
            "context_actions",
            PresentationContext(
                actor=player,
                protocol_version=1,
                options_state=snapshot,
            ),
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_valid_state_copies_cards_immutably(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = {
                    "owner_actor_id": 7,
                    "fingerprint": "fp-1234",
                    "status": "ready",
                    "generation_token": 3,
                    "displayed": [
                        {
                            "kind": "known_action",
                            "action_code": "explore.look",
                            "label": "查看房間",
                            "params": {"room": True},
                        },
                        {
                            "kind": "freeform",
                            "action_code": "explore.talk_freeform",
                            "label": "隨意聊聊",
                            "params": {"npc_id": 9},
                            "hint": "可以聊聊",
                        },
                    ],
                }

            ndb = _Ndb()

        snapshot = options_snapshot(_Session())
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.fingerprint, "fp-1234")
        self.assertEqual(snapshot.status, "ready")
        self.assertEqual(snapshot.generation_token, 3)
        self.assertEqual(len(snapshot.displayed), 2)
        card = snapshot.displayed[0]
        self.assertEqual(card.as_dict()["params"], {"room": True})
        # The deep copy is detached from the source state.
        _Session._Ndb.options_state["displayed"][0]["params"]["room"] = False
        self.assertEqual(card.as_dict()["params"], {"room": True})


class ActionPayloadValidatorsLockstepTests(unittest.TestCase):
    """Totality and lockstep tests for affordance payload validation (possession-validator-lockstep)."""

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_action_payload_validators_covers_allowlist(self):
        from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST
        from web.webclient.presentation.options import (
            FREEFORM_ACTION_CODE,
            _ACTION_PAYLOAD_VALIDATORS,
            _validate_affordance_params,
        )

        expected_registered = set(ACTION_CODE_ALLOWLIST) - {FREEFORM_ACTION_CODE}
        registered_set = set(_ACTION_PAYLOAD_VALIDATORS.keys())
        self.assertTrue(
            registered_set >= expected_registered,
            f"Missing payload validators for: {expected_registered - registered_set}",
        )
        # Every code in the allowlist is known to _validate_affordance_params
        for code in ACTION_CODE_ALLOWLIST:
            try:
                _validate_affordance_params(code, {})
            except Exception as exc:
                self.assertNotIn("unregistered action code", str(exc))

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_unregistered_action_code_payload_validation_rejects_cleanly(self):
        from web.webclient.presentation.options import _validate_affordance_params
        from web.webclient.presentation.protocol import ProtocolValidationError

        with self.assertRaises(ProtocolValidationError) as ctx:
            _validate_affordance_params("explore.unregistered_bogus", {"npc_id": 1})
        self.assertIn("explore.unregistered_bogus", str(ctx.exception))

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_suggestion_params_validation_for_possession_codes(self):
        from web.webclient.presentation.options import _validate_suggestion_params
        from web.webclient.presentation.protocol import MAX_SAFE_INTEGER, ProtocolValidationError

        for action_code in ("explore.possess", "explore.possess_release"):
            # Valid canonical card params
            result = _validate_suggestion_params(action_code, "known_action", {"npc_id": 42})
            self.assertEqual(result, {"npc_id": 42})

            # Boundary MAX_SAFE_INTEGER
            result_max = _validate_suggestion_params(
                action_code, "known_action", {"npc_id": MAX_SAFE_INTEGER}
            )
            self.assertEqual(result_max, {"npc_id": MAX_SAFE_INTEGER})

            # Malformed payloads must raise ProtocolValidationError, never KeyError
            for bad_payload in (
                {},
                {"npc_id": 0},
                {"npc_id": -1},
                {"npc_id": "42"},
                {"npc_id": True},
                {"npc_id": 1, "extra": True},
                {"npc_id": MAX_SAFE_INTEGER + 1},
            ):
                with self.assertRaises(
                    ProtocolValidationError,
                    msg=f"Expected {action_code} with {bad_payload} to raise ProtocolValidationError",
                ):
                    _validate_suggestion_params(action_code, "known_action", bad_payload)

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_possession_validators_boundary_enforcement(self):
        from web.webclient.actions.exploration_actions import (
            ExplorationActionError,
            validate_possess_payload,
            validate_possess_release_payload,
        )
        from web.webclient.presentation.protocol import MAX_SAFE_INTEGER

        for validator in (validate_possess_payload, validate_possess_release_payload):
            # Safe boundary
            self.assertEqual(validator({"npc_id": MAX_SAFE_INTEGER}), {"npc_id": MAX_SAFE_INTEGER})
            # Overflow boundary
            with self.assertRaises(ExplorationActionError):
                validator({"npc_id": MAX_SAFE_INTEGER + 1})


if __name__ == "__main__":
    unittest.main()
