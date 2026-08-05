"""Dialogue composition root tests (webclient-exploration-menu D6).

The ``build_dialogue_client`` seam must return the live client only when the
``npc_dialogue`` profile is enabled, must return the non-``None`` offline stub
otherwise, and must never import ``world.ai.client`` or the guardrail at module
scope or on the disabled path.
"""

from tools.spec_traceability import covers_requirement

import os
import subprocess
import sys
import unittest
from pathlib import Path

from django.test import override_settings

from web.webclient.actions.dialogue_composition import (
    _OfflineStubClient,
    build_dialogue_client,
)
from world.ai.profiles import default_profiles

REPO_ROOT = Path(__file__).resolve().parents[4]


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


class DialogueCompositionTests(unittest.TestCase):
    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_disabled_profile_yields_the_offline_stub(self):
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            client = build_dialogue_client()
        self.assertIsInstance(client, _OfflineStubClient)

    def test_enabled_profile_yields_a_live_client(self):
        from world.ai.client import OpenAICompatClient

        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": True})):
            client = build_dialogue_client()
        self.assertIsInstance(client, OpenAICompatClient)

    def test_offline_stub_fails_loudly_if_ever_invoked(self):
        client = _OfflineStubClient()
        with self.assertRaises(AssertionError):
            client.get_response(object())

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_cold_import_and_disabled_call_load_no_transport(self):
        source = (
            "import os, sys\n"
            "os.environ['MUD_TEST_SETTINGS'] = '1'\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.test_settings'\n"
            "sys.argv = ['evennia', 'test']\n"
            "import evennia\n"
            "assert evennia.logger is None, 'precondition: evennia not initialized'\n"
            "import django\n"
            "django.setup()\n"
            "import sys as _sys\n"
            "assert 'world.ai.guardrail' not in _sys.modules, 'settings-load reached the guardrail pre-init'\n"
            "evennia._init()\n"
            "import web.webclient.actions.dialogue_composition as composition\n"
            "assert 'world.ai.client' not in _sys.modules, 'importing the composition root pulled in the client'\n"
            "from django.test import override_settings\n"
            "from world.ai.profiles import default_profiles\n"
            "raw = default_profiles()\n"
            "raw['npc_dialogue'].update({'enabled': False})\n"
            "with override_settings(LLM_PROFILES=raw):\n"
            "    client = composition.build_dialogue_client()\n"
            "assert 'world.ai.client' not in _sys.modules, 'disabled path pulled in the client'\n"
            "assert client is not None\n"
            "print('OK')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", source],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
