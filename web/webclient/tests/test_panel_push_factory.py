"""The panel-push factory mints exactly the six catalog event ids (design D1).

The trio shells build event ids as ``{event_prefix}_push_watchers_failed``
and ``{event_prefix}_push_failed``; these tests pin the six concrete catalog
strings (party / dialogue / lore_codex x both templates) so a prefix typo can
never silently mint a new event id. The failures are exercised through each
shell's own module bindings — the same identity-based patch seams the panel
tests use — so both the factory wiring and the shell deps providers are
covered.
"""

from unittest.mock import patch
import unittest

from web.webclient.presentation import (
    dialogue_push,
    lore_codex_push,
    party_push,
)


class PanelPushFactoryEventIdTests(unittest.TestCase):
    """Each trio shell degrades through its own shell-module bindings."""

    def test_watcher_lookup_failure_mints_the_catalog_watchers_failed_ids(self):
        cases = (
            (module, push, f"{prefix}_push_watchers_failed")
            for module, push, prefix in (
                (party_push, party_push.push_party_update, "party"),
                (dialogue_push, dialogue_push.push_dialogue_update, "dialogue"),
                (lore_codex_push, lore_codex_push.push_lore_codex_update, "lore_codex"),
            )
        )
        for module, push, expected in cases:
            with self.subTest(expected=expected):
                with patch.object(
                    module, "watchers_for", side_effect=RuntimeError("boom")
                ), patch.object(module, "log_warn") as warned:
                    push(object())
                self.assertEqual(
                    [call.args[0] for call in warned.call_args_list], [expected]
                )

    def test_registry_failure_mints_the_catalog_push_failed_ids(self):
        def _boom():
            raise RuntimeError("registry construction defect")

        cases = (
            (module, push, f"{prefix}_push_failed")
            for module, push, prefix in (
                (party_push, party_push.push_party_update, "party"),
                (dialogue_push, dialogue_push.push_dialogue_update, "dialogue"),
                (lore_codex_push, lore_codex_push.push_lore_codex_update, "lore_codex"),
            )
        )
        for module, push, expected in cases:
            with self.subTest(expected=expected):
                with patch.object(
                    module,
                    "watchers_for",
                    return_value=((object(), "x" * 22),),
                ), patch.object(module, "build_production_registry", _boom), patch.object(
                    module, "log_warn"
                ) as warned:
                    push(object())
                self.assertEqual(
                    [call.args[0] for call in warned.call_args_list], [expected]
                )


if __name__ == "__main__":
    unittest.main()