"""Stage transitions at the motion level (webclient-scene-transitions, C11b).

Every journey injects committed panel updates into the live client and reads
the in-flight layers the transitions leave behind: their `inert` state and
their computed durations. No assertion measures elapsed time: a journey polls
until a state exists and then reads it in the same evaluation, so a slow
runner can only make the in-flight window longer, never skip it.

The scene images are routed to a small same-origin PNG, so two distinct scene
URLs decode without the image generator.
"""

from __future__ import annotations

import base64
import copy

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    inject_update,
    snapshot_envelope,
    valid_art_panel,
    valid_local_map_panel,
    valid_status_panel,
)

REFERENCE = (1920, 1080)

# A 16x9 opaque PNG: decodable, and small enough to serve from memory.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAJCAIAAAC0SDtlAAAAF0lEQVR4nGPUsIliIAUwkaR6VAOtNAAAVukA0GyZA+8AAAAASUVORK5CYII="
)

# The leaving copies this change's transitions can leave behind (other
# surfaces, such as the scene overview behind a verb popover, use `inert`
# for their own reasons).
_LEAVING = ", ".join(
    f'[data-testid="{testid}"][inert]'
    for testid in (
        "scene-backdrop-image",
        "place-card__location",
        "message-content",
        "status-panel",
        "reference-artwork",
    )
)



def _art(name: str) -> dict:
    panel = valid_art_panel()
    panel["scene"]["url"] = f"/art/scene/c11b_{name}.png"
    panel["scene"]["label"] = f"場景{name}"
    panel["scene"]["alt"] = f"場景{name}的描述"
    return panel


def _street(current: str) -> dict:
    """A grid street whose current node and its label follow `current`."""
    panel = valid_local_map_panel()
    nodes = []
    for node_id, label, x, y in (
        ("grid:capital_altoria:2:0", "南門", 2, 0),
        ("grid:capital_altoria:2:1", "南大道", 2, 1),
        ("grid:capital_altoria:2:2", "鐘樓前庭", 2, 2),
    ):
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "x": x,
                "y": y,
                "visibility": "current" if node_id == current else "visible_visited",
                "current": node_id == current,
                "anchor": False,
                "landmark": False,
                "action": None,
            }
        )
    panel["nodes"] = nodes
    panel["current_node"] = current
    panel["edges"] = [
        {
            "source": "grid:capital_altoria:2:0",
            "destination": "grid:capital_altoria:2:1",
            "label": "n",
            "known": True,
            "traversable": True,
        },
        {
            "source": "grid:capital_altoria:2:1",
            "destination": "grid:capital_altoria:2:2",
            "label": "n",
            "known": True,
            "traversable": True,
        },
    ]
    return panel


def _interior(current: str) -> dict:
    """A coordinate-free (graph variant) map over `room:` nodes: the
    placement recentres on `current`, so every move pans the drawing."""
    rooms = {
        "grid:capital_altoria:2:0": "room:9001",
        "grid:capital_altoria:2:1": "room:9002",
        "grid:capital_altoria:2:2": "room:9003",
    }
    panel = copy.deepcopy(_street(current))
    panel["layer"] = "interior"
    panel["current_node"] = rooms[current]
    for node in panel["nodes"]:
        node["id"] = rooms[node["id"]]
    for edge in panel["edges"]:
        edge["source"] = rooms[edge["source"]]
        edge["destination"] = rooms[edge["destination"]]
    return panel


def _status(hp: int, conditions: list | None = None) -> dict:
    status = valid_status_panel("艾倫·灰誓", "char-42")
    status["resources"] = {
        "hp": {"current": hp, "maximum": 100},
        "mp": {"current": 50, "maximum": 50},
        "sp": {"current": 20, "maximum": 20},
    }
    status["conditions"] = conditions or []
    return status


# Reads the scene layers once two coexist: the crossfade's in-flight state.
_SCENE_PAIR = """() => {
  const imgs = [...document.querySelectorAll('[data-testid="scene-backdrop-image"]')];
  if (imgs.length !== 2) return null;
  return imgs.map((img) => ({
    src: img.getAttribute('src'),
    inert: img.inert,
    duration: getComputedStyle(img).transitionDuration,
    transform: getComputedStyle(img).transform,
  }));
}"""

_HEADING_PAIR = """() => {
  const hs = [...document.querySelectorAll('[data-testid="place-card__location"]')];
  if (hs.length !== 2) return null;
  return hs.map((h) => {
    const cs = getComputedStyle(h);
    return { text: h.textContent.trim(), inert: h.inert, property: cs.transitionProperty,
             duration: cs.transitionDuration, transform: cs.transform };
  });
}"""

_CLEAR_PAIR = """() => {
  const cs = [...document.querySelectorAll('[data-testid="message-content"]')];
  if (cs.length !== 2) return null;
  const page = document.querySelector('[data-testid="message-page"]');
  return {
    layers: cs.map((c) => ({ inert: c.inert, leaving: c.classList.contains('message-clear-leave-active'),
                             duration: getComputedStyle(c).transitionDuration })),
    focusOnPage: document.activeElement === page,
  };
}"""


def _identity(transform: str) -> bool:
    return transform in ("none", "matrix(1, 0, 0, 1, 0, 0)")


class SceneTransitionsBrowserTest(BrowserAcceptanceTest):
    """The location, appearance, and vitals rows of design §9.3."""

    def _page(self, motion_level):
        page = self.logged_in_page(REFERENCE, motion_level=motion_level)
        page.route(
            "**/art/scene/c11b_*.png",
            lambda route: route.fulfill(status=200, content_type="image/png", body=_PNG),
        )
        page.wait_for_function(
            "() => !!(window.__elosernBridge && window.__elosernBridge.store.view.epoch)", timeout=15000
        )
        return page

    def _settled_scene(self, page, name: str) -> None:
        page.wait_for_function(
            """(src) => {
              const imgs = [...document.querySelectorAll('[data-testid="scene-backdrop-image"]')];
              return imgs.length === 1 && imgs[0].getAttribute('src') === src && imgs[0].complete;
            }""",
            arg=f"/art/scene/c11b_{name}.png",
            timeout=15000,
        )

    def _settled(self, page, selector: str) -> None:
        page.wait_for_function(
            "([sel, leaving]) => document.querySelectorAll(sel).length === 1 && !document.querySelector(leaving)",
            arg=[selector, _LEAVING],
            timeout=15000,
        )

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_full_motion_scene_change(self):
        """A new scene waits for its decode, then crossfades over 500ms with
        the previous layer inert, and one layer remains."""
        page = self._page(None)
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "full")
        inject_update(page, {"art": _art("a")})
        self._settled_scene(page, "a")

        inject_update(page, {"art": _art("b")})
        # The label switches at commit, whatever the image is doing.
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-label"]').inner_text(), "場景b"
        )
        pair = page.wait_for_function(_SCENE_PAIR, timeout=15000).json_value()
        by_src = {layer["src"]: layer for layer in pair}
        leaving = by_src["/art/scene/c11b_a.png"]
        entering = by_src["/art/scene/c11b_b.png"]
        self.assertTrue(leaving["inert"])
        self.assertFalse(entering["inert"])
        self.assertEqual(leaving["duration"], "0.5s")
        self.assertIn("0.5s", entering["duration"])
        self._settled_scene(page, "b")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region",
    )
    def test_full_motion_place_card_and_clear(self):
        """The new heading slides in while the old one leaves inert; `look`
        clears the window through an inert 150ms layer while the page surface
        keeps focus."""
        page = self._page(None)
        inject_update(page, {"local_map": _street("grid:capital_altoria:2:0")})
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"place-card__location\"]').textContent.trim() === '南門'",
            timeout=15000,
        )
        self._settled(page, '[data-testid="place-card__location"]')

        inject_update(page, {"local_map": _street("grid:capital_altoria:2:1")})
        pair = page.wait_for_function(_HEADING_PAIR, timeout=15000).json_value()
        by_text = {h["text"]: h for h in pair}
        self.assertTrue(by_text["南門"]["inert"])
        self.assertFalse(by_text["南大道"]["inert"])
        self.assertIn("transform", by_text["南大道"]["property"])
        self._settled(page, '[data-testid="place-card__location"]')

        page.focus('[data-testid="message-page"]')
        # A typed command starts a new response (its `in` line), exactly as
        # the command line sends it.
        page.evaluate("() => window.__elosernBridge.store.sendText('look')")
        clear = page.wait_for_function(_CLEAR_PAIR, timeout=15000).json_value()
        leaving = [layer for layer in clear["layers"] if layer["leaving"]]
        self.assertEqual(len(leaving), 1)
        self.assertTrue(leaving[0]["inert"])
        self.assertEqual(leaving[0]["duration"], "0.15s")
        self.assertTrue(clear["focusOnPage"])
        self._settled(page, '[data-testid="message-content"]')
        self.assertTrue(
            page.evaluate("document.activeElement === document.querySelector('[data-testid=\"message-page\"]')")
        )
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
    )
    def test_full_motion_minimap_pan(self):
        """A recentring move starts the drawing with the left node on the
        screen point where it stood, then eases it to rest over 300ms."""
        page = self._page(None)
        inject_update(page, {"local_map": _interior("grid:capital_altoria:2:0")})
        page.wait_for_selector('.local-map [data-node="room:9001"][data-visibility="current"]')
        envelope = snapshot_envelope("", 0, {"local_map": _interior("grid:capital_altoria:2:1")})
        result = page.evaluate(
            """async (env) => {
              const marker = (id) => document.querySelector(
                `.local-map [data-node="${id}"] .local-map__marker`).getBoundingClientRect();
              const centre = (r) => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
              const left = 'room:9001';
              const before = centre(marker(left));
              const s = window.__elosernBridge.store.view;
              env.presentation_epoch = s.epoch;
              env.revision = s.revision + 1;
              const accepted = window.__elosernBridge.store.receive(s.generation, 'ui_update', [env], {}).accepted;
              // Let Vue flush the commit, then read the start state before a
              // frame of the transition runs.
              await new Promise((resolve) => setTimeout(resolve, 0));
              const group = document.querySelector('.local-map .map-lattice__pan');
              const cs = getComputedStyle(group);
              const after = centre(marker(left));
              return { accepted, before, after, transform: cs.transform, duration: cs.transitionDuration,
                       current: document.querySelector('.local-map [data-visibility="current"]').dataset.node };
            }""",
            envelope,
        )
        self.assertTrue(result["accepted"])
        # The node markers already describe the new placement.
        self.assertEqual(result["current"], "room:9002")
        self.assertEqual(result["duration"], "0.3s")
        self.assertFalse(_identity(result["transform"]), result["transform"])
        self.assertAlmostEqual(result["after"]["x"], result["before"]["x"], delta=1.5)
        self.assertAlmostEqual(result["after"]["y"], result["before"]["y"], delta=1.5)
        page.wait_for_function(
            "() => { const t = getComputedStyle(document.querySelector('.local-map .map-lattice__pan')).transform;"
            " return t === 'none' || t === 'matrix(1, 0, 0, 1, 0, 0)'; }",
            timeout=15000,
        )
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
        "webclient-contextual-hud::the-vitals-island-is-shown-only-in-combat-or-while-a-vital-or-a-condition-needs-attention",
    )
    def test_vitals_reveal_and_inert(self):
        """The island reveals over 250ms; hiding it with focus on a chip moves
        focus home first, and the island is inert until it is display:none."""
        page = self._page(None)
        harmful = [{"code": "poison", "label": "中毒", "severity": "harmful"}]
        inject_update(page, {"status": _status(100)})
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('[data-testid=\"status-panel\"]')).display === 'none'",
            timeout=15000,
        )
        inject_update(page, {"status": _status(60, harmful)})
        entering = page.wait_for_function(
            """() => {
              const el = document.querySelector('[data-testid="status-panel"]');
              if (!el.classList.contains('vitals-reveal-enter-active')) return null;
              const cs = getComputedStyle(el);
              return { inert: el.inert, duration: cs.transitionDuration, property: cs.transitionProperty };
            }""",
            timeout=15000,
        ).json_value()
        self.assertFalse(entering["inert"])
        self.assertIn("0.25s", entering["duration"])
        self.assertIn("transform", entering["property"])
        self._settled(page, '[data-testid="status-panel"]')

        page.focus('[data-testid="status-panel__condition--poison"]')
        inject_update(page, {"status": _status(100)})
        leaving = page.wait_for_function(
            """() => {
              const el = document.querySelector('[data-testid="status-panel"]');
              if (!el.classList.contains('vitals-reveal-leave-active')) return null;
              const active = document.activeElement;
              return { inert: el.inert, onBody: active === document.body || active === null,
                       inIsland: el.contains(active) };
            }""",
            timeout=15000,
        ).json_value()
        self.assertTrue(leaving["inert"])
        self.assertFalse(leaving["onBody"])
        self.assertFalse(leaving["inIsland"])
        page.wait_for_function(
            "() => { const el = document.querySelector('[data-testid=\"status-panel\"]');"
            " return getComputedStyle(el).display === 'none' && !el.inert; }",
            timeout=15000,
        )
        self.assertNotEqual(page.evaluate("document.activeElement === document.body"), True)
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
    )
    def test_reduced_motion_fades_only(self):
        """At `reduced` the scene fades within 150ms and nothing travels: the
        heading enters without a slide and the minimap does not pan."""
        page = self._page("reduced")
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "reduced")
        inject_update(page, {"art": _art("a"), "local_map": _interior("grid:capital_altoria:2:0")})
        self._settled_scene(page, "a")
        self._settled(page, '[data-testid="place-card__location"]')

        inject_update(page, {"art": _art("b"), "local_map": _interior("grid:capital_altoria:2:1")})
        pair = page.wait_for_function(_HEADING_PAIR, timeout=15000).json_value()
        for heading in pair:
            self.assertTrue(_identity(heading["transform"]), heading)
        self.assertTrue(
            _identity(page.evaluate(
                "getComputedStyle(document.querySelector('.local-map .map-lattice__pan')).transform"
            ))
        )
        scene = page.wait_for_function(_SCENE_PAIR, timeout=15000).json_value()
        leaving = next(layer for layer in scene if layer["inert"])
        self.assertEqual(leaving["duration"], "0.15s")
        self._settled_scene(page, "b")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_off_motion_is_instant(self):
        """At `off` every change shows only its final state in the frame after
        the commit: no second layer and no inert copy, ever."""
        page = self._page("off")
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "off")
        inject_update(page, {"art": _art("a"), "local_map": _street("grid:capital_altoria:2:0"), "status": _status(60)})
        self._settled_scene(page, "a")
        envelope = snapshot_envelope(
            "",
            0,
            {"art": _art("b"), "local_map": _street("grid:capital_altoria:2:1"), "status": _status(100)},
        )
        result = page.evaluate(
            """async ([env, leaving]) => {
              const s = window.__elosernBridge.store.view;
              env.presentation_epoch = s.epoch;
              env.revision = s.revision + 1;
              window.__elosernBridge.store.receive(s.generation, 'ui_update', [env], {});
              await new Promise((resolve) => requestAnimationFrame(() => resolve()));
              const count = (sel) => document.querySelectorAll(sel).length;
              return {
                headings: count('[data-testid="place-card__location"]'),
                heading: document.querySelector('[data-testid="place-card__location"]').textContent.trim(),
                contents: count('[data-testid="message-content"]'),
                inert: count(leaving),
                vitals: getComputedStyle(document.querySelector('[data-testid="status-panel"]')).display,
                pan: getComputedStyle(document.querySelector('.local-map .map-lattice__pan')).transform,
              };
            }""",
            [envelope, _LEAVING],
        )
        self.assertEqual(result["headings"], 1)
        self.assertEqual(result["heading"], "南大道")
        self.assertEqual(result["contents"], 1)
        self.assertEqual(result["inert"], 0)
        self.assertEqual(result["vitals"], "none")
        self.assertTrue(_identity(result["pan"]))
        # Once decoded, the new scene replaces the old one with no second layer.
        page.wait_for_function(
            """() => {
              const imgs = [...document.querySelectorAll('[data-testid="scene-backdrop-image"]')];
              if (imgs.length !== 1) throw new Error('a second scene layer appeared at off');
              return imgs[0].getAttribute('src') === '/art/scene/c11b_b.png';
            }""",
            timeout=15000,
        )
        self.assertEqual(page.locator(_LEAVING).count(), 0)
        page.close()
