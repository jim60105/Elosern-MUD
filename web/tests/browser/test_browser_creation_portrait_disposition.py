"""Creation portrait disposition journeys (creation-draft-portrait).

Worker failure and explicit retry, and what custom or preset activation does
with a ready draft portrait while every art service is offline, over the
same controlled runtime as ``test_browser_creation_portrait``.
"""

from __future__ import annotations

from .browser_helpers import sent_action_count
from .creation_portrait_support import GENERATE, GENERATE_BUTTON, STATUS, CreationPortraitBrowserTest


class CreationPortraitDispositionJourneys(CreationPortraitBrowserTest):
    def test_worker_failure_and_retry(self):
        page = self._open_custom()
        self.control.set(generate="fail")
        self._open_drawer(page)
        request = self._submit(page, "會失敗的一次")
        self.assertEqual(self._result_for(page, request)["outcome"], "success")
        self._wait_portrait(page, "pending")
        self._drain_once()
        portrait = self._wait_portrait(page, "failed")
        self.assertIn(portrait["reason"], page.inner_text(STATUS))
        # A failure permits an explicit retry; nothing retried by itself.
        self.assertTrue(page.is_enabled(GENERATE_BUTTON))
        self.assertEqual(sent_action_count(page, GENERATE), 1)
        self.assertFalse(self._in_flight())

        self.control.set(generate="ok")
        self._generate_to_ready(page, "再試一次")
        self.assertEqual(sent_action_count(page, GENERATE), 2)

    def test_custom_activation_keeps_the_portrait_offline(self):
        page = self._open_custom()
        self._generate_to_ready(page)
        cards = self.control.run("cards")["image_ids"]
        self.assertEqual(len(cards), 1)
        self._go_offline(page)
        # Custom creation stays fully usable with every art service down.
        page.click('[data-testid="creation-submit"]')
        self._activate_confirmed(page)
        # The draft card survives activation, and activation enqueued no
        # duplicate portrait generation.
        self.assertFalse(self._in_flight())
        self.assertEqual(self.control.run("cards")["image_ids"], cards)

    def test_preset_activation_discards_the_draft_portrait_offline(self):
        page = self._open_custom()
        self._generate_to_ready(page)
        (draft_card,) = self.control.run("cards")["image_ids"]
        self._go_offline(page)
        # Preset creation stays fully usable with every art service down.
        page.click('[data-testid="creation-mode-preset"]')
        page.click('[data-testid="creation-preset-choose"]')
        self._activate_confirmed(page)
        self.assertNotIn(draft_card, self.control.run("cards")["image_ids"])
