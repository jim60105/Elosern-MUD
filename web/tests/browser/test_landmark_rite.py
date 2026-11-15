"""Landmark rite journeys in the live client (landmark-rite-journeys, design D1).

Two journeys drive the rite flow over injected committed state, the way the
travel stage journeys do: the room's panels arrive through the store's own
``receive`` seam, a responder on the live sender holds every
``explore.landmark_rite`` the panel sends (recorded, never forwarded), and the
journey answers it with a synthetic successful result carrying a three-line
delivery. One journey starts from a wilderness arrival on the travel layout,
the other from a settlement room. Every name is synthetic; nothing here names
shipped content.
"""

from __future__ import annotations

import os
import tempfile

from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import inject_update, scene_block, valid_status_panel
from .test_wilderness_travel import CX, CY, TOWN, _art, _node, _party, _TravelStage, _walk_area, _walk_panels

SMALL = (1451, 790)
LARGE = (2560, 1440)
SHOTS = os.environ.get("ELOSERN_RITE_SHOTS")

_LINES = (
    {"kind": "narration", "text": "合成敘述之一。"},
    {"kind": "speech", "speaker": "actor", "text": "合成台詞之二。"},
    {"kind": "speech", "speaker": "host", "text": "合成台詞之三。"},
)
_DELIVERY = {
    "kind": "formal",
    "delivery_id": "rite:t_rite_highlands:drink:1",
    "scene_id": "rite.synthetic.drink.self",
    "scene_revision": "r1",
    "actor_name": "你",
    "guardian_name": "合成泉聲",
    "lines": [dict(line) for line in _LINES],
}


def _rite_panel(art: dict | None = None) -> dict:
    """A synthetic available schema-1 ``rite`` panel: two options, one
    performer (the controlled character), nothing experienced yet."""
    return {
        "schema_version": 1,
        "available": True,
        "kind": "rite",
        "district": {"key": "t_rite_highlands", "name": "合成高地", "landmark": "合成石龕", "lit": False},
        "guardian": {"name": "合成泉聲", "form": "水面映出的聲音，只在有人俯身時開口。"},
        "art": art,
        "options": [
            {"key": "drink", "label": "合成選項甲", "companion": True},
            {"key": "bathe", "label": "合成選項乙", "companion": False},
        ],
        "performers": [{"member_id": None, "name": "合成旅人", "owner": True}],
        "delivery": None,
        "seen": [],
    }


def _rite_art() -> dict:
    """A canonical synthetic scene descriptor (its pixels are not asserted):
    it only gives the card its 16:5 art band and the stage its full-bleed art."""
    return scene_block("/art/scene/t_rite.png", "wilderness:合成高地:1,1", label="合成石龕", alt="合成石龕")["artwork"]


def _arrival_log(node: str) -> dict:
    """One committed typed ``landmark_reached`` notice reached at ``node``."""
    return {
        "travel_log": {
            "schema_version": 1, "available": True,
            "entries": [{
                "id": "%s:rite001.0" % ("e" * 32), "kind": "landmark_reached",
                "tick": 5001, "day": 3, "time": "09:40", "text": "抵達合成石龕。",
                "params": {
                    "arrival_node": node, "name": "合成石龕", "lit_district": None,
                    "prose": "合成散文。", "artwork": None,
                },
            }],
        },
    }


# Holds every explore.landmark_rite on the live sender (recorded, never
# forwarded); every other action passes through to the previous sender.
_HOLD_RITES = """() => {
  const sender = window.__elosernBridge.store.getSender();
  if (sender.sendAction.__riteHold) return;
  const original = sender.sendAction.bind(sender);
  window.__riteHold = [];
  const hold = (env) => {
    if (env && env.action_id === 'explore.landmark_rite') {
      window.__riteHold.push(env);
      return undefined;
    }
    return original(env);
  };
  hold.__riteHold = true;
  sender.sendAction = hold;
}"""

# The held rite's own successful result carrying the delivery.
_ANSWER_RITE = """([index, delivery]) => {
  const store = window.__elosernBridge.store;
  const env = window.__riteHold[index];
  const v = store.view;
  return !!store.receive(v.generation, 'ui_action_result', [{
    protocol_version: 1, presentation_epoch: v.epoch, request_id: env.request_id,
    outcome: 'success', code: 'explore.landmark_rite', message: '合成完成。',
    presentation_revision: v.revision, data: { delivery, first_completion: false },
  }], {}).accepted;
}"""

# Every element under the selector that owns a non-blank text node: its
# computed font size and whether its box lies inside the anchor's box.
_TEXT_RUNS = """([selector, anchor]) => {
  const a = document.querySelector(anchor).getBoundingClientRect();
  return Array.from(document.querySelectorAll(selector + ' *'))
    .filter((el) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim()))
    .filter((el) => el.getClientRects().length > 0)
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        text: el.textContent.trim().slice(0, 24),
        size: parseFloat(getComputedStyle(el).fontSize),
        inside: r.left >= a.left - 1 && r.right <= a.right + 1 && r.top >= a.top - 1 && r.bottom <= a.bottom + 1,
      };
    });
}"""

# Pairs of text-owning elements under the selector whose boxes cross (an
# element and its own ancestor are one run, never a pair).
_TEXT_COLLISIONS = """(selector) => {
  const runs = Array.from(document.querySelectorAll(selector + ' *'))
    .filter((el) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim()))
    .filter((el) => el.getClientRects().length > 0);
  const crossed = [];
  for (let i = 0; i < runs.length; i += 1) {
    for (let j = i + 1; j < runs.length; j += 1) {
      const [p, q] = [runs[i], runs[j]];
      if (p.contains(q) || q.contains(p)) continue;
      const a = p.getBoundingClientRect();
      const b = q.getBoundingClientRect();
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 1 && h > 1) crossed.push([p.textContent.trim().slice(0, 16), q.textContent.trim().slice(0, 16)]);
    }
  }
  return crossed;
}"""

# The backdrop's plate stands below the header bar, inside the viewport.
_PLATE_CLEAR = """() => {
  const plate = document.querySelector('[data-testid="rite-backdrop-plate"]').getBoundingClientRect();
  const header = document.querySelector('[data-metric="--header-h"]').getBoundingClientRect().height;
  return plate.top >= header - 0.5 && plate.right <= window.innerWidth && plate.height > 0;
}"""

# No scrollbar on the page and no inner overflow on the surface itself.
_OVERFLOW = """(selector) => {
  const fits = (el) => el.scrollWidth <= el.clientWidth + 1 && el.scrollHeight <= el.clientHeight + 1;
  const surface = document.querySelector(selector);
  return {
    page: fits(document.documentElement) && fits(document.body),
    surface: !!surface && fits(surface),
  };
}"""

_UI_SCALE = "() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ui-scale'))"


def _box(page, testid: str) -> dict:
    box = page.locator(f'[data-testid="{testid}"]').bounding_box()
    if box is None:
        raise AssertionError(f"{testid} has no box")
    return box


def _inside(inner: dict, outer: dict) -> bool:
    return (
        inner["x"] >= outer["x"] - 1
        and inner["y"] >= outer["y"] - 1
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + 1
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + 1
    )


def _focus_in(page, testid: str) -> bool:
    return page.evaluate(
        "(id) => !!document.activeElement && !!document.activeElement.closest(`[data-testid=\"${id}\"]`)", testid,
    )


def _held(page) -> list:
    return page.evaluate("() => window.__riteHold.map((env) => env.payload)")


def _page_text(page) -> str:
    return page.locator('[data-testid="message-page"]').inner_text().strip()


class LandmarkRiteTests(_TravelStage):
    """Arrival card, rite stage, one perform, the delivered scene through the
    shared player and the return entry, at both acceptance viewports."""

    def _shot(self, page, name: str) -> None:
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            page.screenshot(path=os.path.join(SHOTS, name))

    def _fits(self, page, surface: str, viewport: tuple[int, int]) -> None:
        """The surface lies in the choices anchor, nothing scrolls, every text
        run lies in the anchor and keeps the 16px x scale floor."""
        scale = page.evaluate(_UI_SCALE)
        self.assertAlmostEqual(scale, ui_scale(viewport), places=2)
        self.assertTrue(_inside(_box(page, surface), _box(page, "anchor-choices")), surface)
        self.assertEqual(page.evaluate(_OVERFLOW, f'[data-testid="{surface}"]'), {"page": True, "surface": True})
        runs = page.evaluate(_TEXT_RUNS, [f'[data-testid="{surface}"]', '[data-testid="anchor-choices"]'])
        self.assertTrue(runs)
        self.assertEqual([run for run in runs if not run["inside"]], [])
        self.assertGreaterEqual(min(run["size"] for run in runs), 16 * scale - 0.01, runs)
        self.assertEqual(page.evaluate(_TEXT_COLLISIONS, f'[data-testid="{surface}"]'), [])

    def _arrive(self, page, rite: dict, extra: dict | None = None) -> None:
        """Commit the panel's availability; the arrival card opens with focus
        on 走近 and the generic landmark card stays closed."""
        page.evaluate(_HOLD_RITES)
        self.assertEqual(page.locator('[data-testid="rite-entry"]').count(), 0)
        inject_update(page, {"rite": rite, **(extra or {})})
        page.locator('[data-testid="rite-arrival-card"]').wait_for(timeout=15000)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('[data-testid=\"rite-arrival-approach\"]')",
            timeout=15000,
        )
        self.assertEqual(page.locator('[data-testid="landmark-card"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="rite-arrival-kicker"]').get_attribute("data-revisit"), "false")

    def _approach(self, page, viewport: tuple[int, int]) -> None:
        """Enter on the card presents the stage: the backdrop, the party, the
        rite panel holding focus, no map and no overflow."""
        page.keyboard.press("Enter")
        page.locator('[data-testid="rite-panel"]').wait_for(timeout=15000)
        page.wait_for_function(
            "() => !!document.activeElement && !!document.activeElement.closest('[data-testid=\"rite-panel\"]')",
            timeout=15000,
        )
        self.assertEqual(page.locator('[data-testid="rite-arrival-card"]').count(), 0)
        self.assertTrue(page.locator('[data-testid="rite-backdrop"]').is_visible())
        self.assertTrue(page.locator('[data-testid="anchor-actor-left"] [data-testid="companion-lineup"]').is_visible())
        self.assertEqual(page.locator('[data-testid="travel-map"]').count(), 0)
        self.assertEqual(_page_text(page), _rite_panel()["guardian"]["form"])
        self.assertTrue(page.evaluate(_PLATE_CLEAR))
        self._fits(page, "rite-panel", viewport)

    def _perform_and_play(self, page) -> None:
        """One digit sends exactly one rite; the delivery plays line by line
        through the shared player and the panel returns with focus."""
        page.keyboard.press("1")
        page.locator('[data-testid="rite-panel"]').wait_for(state="detached", timeout=15000)
        self.assertEqual(_held(page), [{"option": "drink", "member_id": None}])
        # A second activation while the request is pending sends nothing.
        page.keyboard.press("1")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        self.assertEqual(len(_held(page)), 1)
        self.assertTrue(page.evaluate(_ANSWER_RITE, [0, _DELIVERY]))
        texts = [line["text"] for line in _LINES]
        page.wait_for_function(
            "(t) => (document.querySelector('[data-testid=\"message-page\"]') || {}).innerText?.trim() === t",
            arg=texts[0], timeout=15000,
        )
        shown = [_page_text(page)]
        self.assertTrue(_focus_in(page, "message-page"))
        for text in texts[1:]:
            page.keyboard.press(" ")
            page.wait_for_function(
                "(t) => document.querySelector('[data-testid=\"message-page\"]').innerText.trim() === t",
                arg=text, timeout=15000,
            )
            shown.append(_page_text(page))
            self.assertEqual(page.locator('[data-testid="rite-panel"]').count(), 0)
        self.assertEqual(shown, texts)
        page.keyboard.press(" ")
        page.locator('[data-testid="rite-panel"]').wait_for(timeout=15000)
        page.wait_for_function(
            "() => !!document.activeElement && !!document.activeElement.closest('[data-testid=\"rite-panel\"]')",
            timeout=15000,
        )
        self.assertEqual(len(_held(page)), 1)
        self.assertTrue(page.evaluate("() => window.__elosernBridge.store.getSender().sendAction.__riteHold === true"))

    def test_wilderness_rite_journey(self):
        """From a wilderness arrival: card, stage, one option, the scene pages
        and 退開 back to the map; R and Enter reopen the stage at the larger
        viewport, which still fits."""
        page = self.logged_in_page(SMALL)
        self._enter(page, {**_walk_panels(CX, CY), "party": _party([(2, "合成同伴")])})
        self._wait_views(page, 1)
        self._answer(page, 0, area=_walk_area(CX, CY))
        self._wait_ready(page)

        self._arrive(page, _rite_panel(), _arrival_log(_node(CX, CY)))
        self._fits(page, "rite-arrival-card", SMALL)
        self._shot(page, "rite-wild-card-1451x790.png")

        self._approach(page, SMALL)
        self._shot(page, "rite-wild-stage-1451x790.png")
        self._perform_and_play(page)

        page.keyboard.press("Escape")
        page.locator('[data-testid="rite-panel"]').wait_for(state="detached", timeout=15000)
        self.assertEqual(page.locator('[data-testid="rite-backdrop"]').count(), 0)
        self._wait_ready(page)
        page.locator('[data-testid="rite-entry"]').wait_for(timeout=15000)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('[data-testid=\"travel-map\"]')",
            timeout=15000,
        )
        self.assertEqual(page.locator('[data-testid="landmark-card"]').count(), 0)
        self.assertEqual(len(_held(page)), 1)
        self._shot(page, "rite-wild-entry-1451x790.png")

        # The larger viewport: R from the map reopens the card as a revisit.
        page.set_viewport_size({"width": LARGE[0], "height": LARGE[1]})
        page.wait_for_function(
            "(s) => Math.abs(parseFloat(getComputedStyle(document.documentElement)"
            ".getPropertyValue('--ui-scale')) - s) < 0.01",
            arg=ui_scale(LARGE), timeout=15000,
        )
        self._wait_ready(page)
        page.locator('[data-testid="travel-map"]').focus()
        page.keyboard.press("r")
        page.locator('[data-testid="rite-arrival-card"]').wait_for(timeout=15000)
        self.assertEqual(page.locator('[data-testid="rite-arrival-kicker"]').get_attribute("data-revisit"), "true")
        self.assertTrue(_focus_in(page, "rite-arrival-approach"))
        self._fits(page, "rite-arrival-card", LARGE)
        self._shot(page, "rite-wild-card-2560x1440.png")
        self._approach(page, LARGE)
        self._shot(page, "rite-wild-stage-2560x1440.png")
        self.assertEqual(len(_held(page)), 1)
        page.close()

    def test_city_rite_journey(self):
        """From a settlement room: the card over the room, the stage, one
        option, the scene pages and the return entry under the place card."""
        page = self.logged_in_page(SMALL)
        self._enter(
            page,
            {"status": valid_status_panel("合成主角", "42"), "art": _art(TOWN), "party": _party([(2, "合成同伴")])},
        )
        self.assertEqual(page.locator('[data-testid="travel-map"]').count(), 0)
        self.assertTrue(page.locator('[data-testid="place-card"]').is_visible())

        self._arrive(page, _rite_panel(_rite_art()))
        self.assertEqual(page.locator('[data-testid="travel-map"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="rite-arrival-art"]').get_attribute("class").split().count("is-empty"), 0)
        self._fits(page, "rite-arrival-card", SMALL)
        self._shot(page, "rite-city-card-1451x790.png")

        self._approach(page, SMALL)
        self._shot(page, "rite-city-stage-1451x790.png")
        self._perform_and_play(page)

        page.keyboard.press("Escape")
        page.locator('[data-testid="rite-panel"]').wait_for(state="detached", timeout=15000)
        self.assertEqual(page.locator('[data-testid="rite-backdrop"]').count(), 0)
        entry = page.locator('[data-testid="rite-entry"]')
        entry.wait_for(timeout=15000)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('[data-testid=\"rite-entry\"]')",
            timeout=15000,
        )
        place = _box(page, "place-card")
        self.assertGreaterEqual(_box(page, "rite-entry")["y"], place["y"] + place["height"] - 1)
        self.assertTrue(_inside(_box(page, "rite-entry"), _box(page, "anchor-map")))
        self.assertEqual(len(_held(page)), 1)
        self._shot(page, "rite-city-entry-1451x790.png")
        page.close()
