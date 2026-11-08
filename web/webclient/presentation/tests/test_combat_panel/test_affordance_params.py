import unittest
from tools.spec_traceability import covers_requirement


class ActionPayloadValidatorsLockstepTests(unittest.TestCase):
    """Totality and lockstep tests for affordance payload validation (possession-validator-lockstep)."""

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-7-panel")
    def test_action_payload_validators_covers_allowlist(self):
        from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST
        from web.webclient.presentation.affordance_params import (
            FREEFORM_ACTION_CODE,
            _ACTION_PAYLOAD_VALIDATORS,
            validate_affordance_params,
        )

        expected_registered = set(ACTION_CODE_ALLOWLIST) - {FREEFORM_ACTION_CODE}
        registered_set = set(_ACTION_PAYLOAD_VALIDATORS.keys())
        self.assertTrue(
            registered_set >= expected_registered,
            f"Missing payload validators for: {expected_registered - registered_set}",
        )
        # Every code in the allowlist is known to validate_affordance_params
        for code in ACTION_CODE_ALLOWLIST:
            try:
                validate_affordance_params(code, {})
            except Exception as exc:
                self.assertNotIn("unregistered action code", str(exc))

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-7-panel")
    def test_unregistered_action_code_payload_validation_rejects_cleanly(self):
        from web.webclient.presentation.affordance_params import validate_affordance_params
        from web.webclient.presentation.protocol import ProtocolValidationError

        with self.assertRaises(ProtocolValidationError) as ctx:
            validate_affordance_params("explore.unregistered_bogus", {"npc_id": 1})
        self.assertIn("explore.unregistered_bogus", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
