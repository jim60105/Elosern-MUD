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
    scene_block,
    snapshot_envelope,
    valid_art_panel,
    valid_local_map_panel,
    valid_status_panel,
)

REFERENCE = (1451, 790)

# A 16x9 opaque PNG: decodable, and small enough to serve from memory.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAJCAIAAAC0SDtlAAAAF0lEQVR4nGPUsIliIAUwkaR6VAOtNAAAVukA0GyZA+8AAAAASUVORK5CYII="
)

# The leaving copies this change's transitions can leave behind (other
# surfaces, such as the command panel under a verb card, use `inert`
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
    """One committed scene panel whose v4 descriptor carries the named c11b
    output for the SAME logical place: the subject identity is fixed across
    the pair (``None`` in the retired flat shape), while the candidate's
    resource identity, version and the descriptor revision all follow the
    requested URL — so ``a`` and ``b`` are two resources of one scene the
    same-place crossfade replaces, never a move to a different place."""
    panel = valid_art_panel()
    panel["scene"] = scene_block(
        f"/art/scene/c11b_{name}.png",
        "scene:c11b",
        label=f"場景{name}",
        alt=f"場景{name}的描述",
    )
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
                "gateway": None,
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


# Ciaran's authored metric streets (metres), the payload view the grid
# presenter emits around a current node: every node within two road hops,
# one star edge from the current node to each, the octant on a one-hop edge
# and an empty label on a two-hop one, and a move action on one-hop nodes.
_CIARAN = {
    "village_plaza": ("村中廣場", 220, 305),
    "hidden_path": ("隱密小徑", 35, 270),
    "stream_path": ("溪畔小徑", 245, 135),
    "training_clearing": ("練刀場", 405, 335),
    "old_tree_north": ("村北古樹下", 200, 465),
    "elder_tree": ("長老古樹下", 165, 650),
    "weaving_slope": ("織房坡", 390, 495),
    "silver_leaf_slope": ("銀葉坡", 440, 665),
}
_CIARAN_ROADS = (
    ("hidden_path", "village_plaza", "e"),
    ("stream_path", "village_plaza", "n"),
    ("village_plaza", "old_tree_north", "n"),
    ("village_plaza", "training_clearing", "e"),
    ("old_tree_north", "elder_tree", "n"),
    ("old_tree_north", "weaving_slope", "e"),
    ("elder_tree", "silver_leaf_slope", "e"),
)
_OPPOSITE = {"n": "s", "ne": "sw", "e": "w", "se": "nw", "s": "n", "sw": "ne", "w": "e", "nw": "se"}


def _ciaran(current: str) -> dict:
    """A metric Ciaran street view around `current` (animate-minimap-scale-
    transitions): 村中廣場 and 村北古樹下 select the 300 m level, while
    長老古樹下's 185 m and 275 m exits need the 500 m level."""

    def node_id(key: str) -> str:
        _label, x, y = _CIARAN[key]
        return f"grid:village_ciaran:{x}:{y}"

    links: dict[str, list[tuple[str, str]]] = {}
    for a, b, octant in _CIARAN_ROADS:
        links.setdefault(a, []).append((b, octant))
        links.setdefault(b, []).append((a, _OPPOSITE[octant]))
    depth = {current: 0}
    frontier = [current]
    for step in (1, 2):
        nxt = []
        for key in frontier:
            for other, _octant in links.get(key, []):
                if other not in depth:
                    depth[other] = step
                    nxt.append(other)
        frontier = nxt
    one_hop = dict(links.get(current, []))
    nodes = []
    edges = []
    for key, (label, x, y) in _CIARAN.items():
        if key not in depth:
            continue
        is_current = key == current
        nodes.append(
            {
                "id": node_id(key),
                "label": label,
                "x": x,
                "y": y,
                "visibility": "current" if is_current else "visible_visited",
                "current": is_current,
                "anchor": key == "village_plaza",
                "landmark": key == "village_plaza",
                "gateway": None,
                "action": (
                    {"kind": "move", "exit_ref": f"e_{current}_{key}", "destination": node_id(key)}
                    if key in one_hop
                    else None
                ),
            }
        )
        if not is_current:
            edges.append(
                {
                    "source": node_id(current),
                    "destination": node_id(key),
                    "label": one_hop.get(key, ""),
                    "known": True,
                    "traversable": key in one_hop,
                }
            )
    nodes.sort(key=lambda node: not node["current"])
    panel = valid_local_map_panel()
    panel.update(
        {
            "current_node": node_id(current),
            "title": f"{_CIARAN[current][0]}街道圖",
            "nodes": nodes,
            "edges": edges,
        }
    )
    return panel


# Commits one local_map update and reads, in the same frame chain, what the
# island shows: the dissolving copies (and their inertness) and the largest
# pan offset of the dot field, over two animation frames.
_ISLAND_COMMIT = r"""async ([env]) => {
  const island = document.querySelector('.local-map');
  const seen = { copies: 0, inert: null, testids: null, controls: null, duration: null, offset: null, fieldPan: 0 };
  const read = () => {
    const copies = island.querySelectorAll('[data-testid="local-map__leaving"]');
    seen.copies = Math.max(seen.copies, copies.length);
    if (copies.length && seen.inert === null) {
      const copy = copies[0];
      const host = copy.parentElement;
      seen.inert = host.inert && copy.hasAttribute('inert') && host.getAttribute('aria-hidden') === 'true';
      seen.testids = copy.querySelectorAll('[data-testid], [data-node]').length;
      seen.controls = host.querySelectorAll('button, a, [tabindex]').length;
      seen.duration = getComputedStyle(copy).animationDuration;
      const live = island.querySelector('[data-testid="local-map__lattice"]').getBoundingClientRect();
      const box = copy.getBoundingClientRect();
      seen.offset = Math.max(Math.abs(box.left - live.left), Math.abs(box.top - live.top),
                             Math.abs(box.width - live.width), Math.abs(box.height - live.height));
    }
    const field = island.querySelector('[data-testid="map-lattice__pan--field"]');
    const m = field && getComputedStyle(field).transform.match(/matrix\(([^)]+)\)/);
    if (m) {
      const v = m[1].split(',').map(Number);
      seen.fieldPan = Math.max(seen.fieldPan, Math.hypot(v[4], v[5]));
    }
  };
  const observer = new MutationObserver(read);
  observer.observe(island, { subtree: true, childList: true, attributes: true });
  const s = window.__elosernBridge.store.view;
  env.presentation_epoch = s.epoch;
  env.revision = s.revision + 1;
  const accepted = window.__elosernBridge.store.receive(s.generation, 'ui_update', [env], {}).accepted;
  await new Promise((resolve) => setTimeout(resolve, 0));
  read();
  for (let i = 0; i < 2; i += 1) {
    await new Promise((resolve) => requestAnimationFrame(() => resolve()));
    read();
  }
  observer.disconnect();
  return {
    accepted,
    seen,
    current: island.querySelector('.local-map__node[data-visibility="current"]').dataset.node,
    scale: island.querySelector('[data-testid="local-map__scale"]').textContent.trim(),
    remaining: island.querySelectorAll('[data-testid="local-map__leaving"]').length,
  };
}"""


def _status(hp: int, conditions: list | None = None) -> dict:
    status = valid_status_panel("艾倫‧灰誓", "char-42")
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

# One reduced-motion commit, captured whole.
#
# The two in-flight pairs of that commit are short and are NOT open at the
# same time: the heading's leave is half the reveal token, while the scene's
# crossfade only begins when the new bitmap has been selected, and it is over
# one `--motion-scene` after that. Reading them one after the other therefore
# races both windows — a second round trip can land after either has closed,
# and a poll then waits forever for a pair that will never come back.
#
# So the capture is armed BEFORE the commit and retains each pair in the
# first microtask that shows it (a MutationObserver callback runs before any
# frame or timer can close a window), then reports what it saw. A window that
# genuinely never opened comes back as `null` beside the counts it ended with,
# which is a diagnosis instead of a timeout.
_REDUCED_COMMIT = """async ([env]) => {
  const scenePair = () => {
    const imgs = [...document.querySelectorAll('[data-testid="scene-backdrop-image"]')];
    if (imgs.length !== 2) return null;
    return imgs.map((img) => ({
      src: img.getAttribute('src'),
      inert: img.inert,
      duration: getComputedStyle(img).transitionDuration,
    }));
  };
  const headingPair = () => {
    const hs = [...document.querySelectorAll('[data-testid="place-card__location"]')];
    if (hs.length !== 2) return null;
    return hs.map((h) => getComputedStyle(h).transform);
  };
  let scene = null;
  let headings = null;
  let settle;
  const both = new Promise((resolve) => { settle = resolve; });
  const capture = () => {
    scene = scene ?? scenePair();
    headings = headings ?? headingPair();
    if (scene && headings) settle();
  };
  const observer = new MutationObserver(capture);
  observer.observe(document.body, { childList: true, subtree: true, attributes: true });

  const s = window.__elosernBridge.store.view;
  env.presentation_epoch = s.epoch;
  env.revision = s.revision + 1;
  const result = window.__elosernBridge.store.receive(s.generation, 'ui_update', [env], {});
  capture();
  if (!result || result.accepted !== true) {
    observer.disconnect();
    return { rejected: result };
  }
  await Promise.race([both, new Promise((resolve) => setTimeout(resolve, 15000))]);
  observer.disconnect();
  capture();
  const pan = document.querySelector('.local-map .map-lattice__pan');
  return {
    scene,
    headings,
    pan: pan ? getComputedStyle(pan).transform : null,
    counts: {
      scenes: document.querySelectorAll('[data-testid="scene-backdrop-image"]').length,
      headings: document.querySelectorAll('[data-testid="place-card__location"]').length,
    },
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
        "webclient-local-map::island-movement-uses-scale-aware-effective-motion",
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
    )
    def test_minimap_scale_change_follows_motion_level(self):
        """On a metric island an equal-scale street step pans the dot field
        with the drawing; a step across a ladder boundary never pans: at
        `full` an inert, identity-free copy of the previous drawing dissolves
        over the base duration and is then gone, at `reduced` the new scale
        shows at once with no copy through two frames."""
        for level in ("full", "reduced"):
            with self.subTest(level=level):
                page = self._page(None if level == "full" else level)
                self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), level)
                inject_update(page, {"local_map": _ciaran("village_plaza")})
                page.wait_for_selector(
                    '.local-map [data-node="grid:village_ciaran:220:305"][data-visibility="current"]'
                )
                same = page.evaluate(
                    _ISLAND_COMMIT, [snapshot_envelope("", 0, {"local_map": _ciaran("old_tree_north")})]
                )
                self.assertTrue(same["accepted"])
                self.assertEqual(same["current"], "grid:village_ciaran:200:465")
                self.assertEqual(same["scale"], "格距 60 m")
                self.assertEqual(same["seen"]["copies"], 0, same)
                if level == "full":
                    self.assertGreater(same["seen"]["fieldPan"], 1, same)
                else:
                    self.assertEqual(same["seen"]["fieldPan"], 0, same)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('.local-map .map-lattice__pan')].every((g) => {"
                    " const t = getComputedStyle(g).transform; return t === 'none' || t === 'matrix(1, 0, 0, 1, 0, 0)'; })",
                    timeout=15000,
                )

                ladder = page.evaluate(
                    _ISLAND_COMMIT, [snapshot_envelope("", 0, {"local_map": _ciaran("elder_tree")})]
                )
                self.assertTrue(ladder["accepted"])
                self.assertEqual(ladder["current"], "grid:village_ciaran:165:650")
                self.assertEqual(ladder["scale"], "格距 100 m")
                # A scale change never runs the equal-scale FLIP.
                self.assertEqual(ladder["seen"]["fieldPan"], 0, ladder)
                if level == "full":
                    self.assertEqual(ladder["seen"]["copies"], 1, ladder)
                    self.assertTrue(ladder["seen"]["inert"], ladder)
                    self.assertEqual(ladder["seen"]["testids"], 0, ladder)
                    self.assertEqual(ladder["seen"]["controls"], 0, ladder)
                    self.assertEqual(ladder["seen"]["duration"], "0.3s", ladder)
                    # The copy lies exactly over the live drawing it dissolves into.
                    self.assertLess(ladder["seen"]["offset"], 0.5, ladder)
                    page.wait_for_function(
                        "() => !document.querySelector('.local-map [data-testid=\"local-map__leaving\"]')",
                        timeout=15000,
                    )
                else:
                    self.assertEqual(ladder["seen"]["copies"], 0, ladder)
                    self.assertEqual(ladder["remaining"], 0, ladder)
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
        "webclient-contextual-hud::the-vitals-island-is-shown-only-in-combat-or-while-a-vital-or-a-condition-needs-attention",
        "webclient-contextual-hud::condition-detail-preserves-equipment-provenance-without-hiding-gameplay-conditions",
    )
    def test_vitals_reveal_and_inert(self):
        """The island reveals over 250ms; hiding it with focus on a chip moves
        focus home first, and the island is inert until it is display:none."""
        page = self._page(None)
        equipment = [{
            "code": "t_equipment_warning", "label": "合成警告", "severity": "warning",
            "modifiers": {"defense": -15},
            "provenance": {"kind": "equipment", "equipment_sources": [{"item_key": "t_a", "label": "合成護符"}]},
        }]
        inject_update(page, {"status": _status(100, equipment)})
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('[data-testid=\"status-panel\"]')).display === 'none'",
            timeout=15000,
        )
        # The full roster lived in the retired character-status drawer; the
        # island chip below carries the equipment provenance in its name.
        self.assertEqual(page.locator('[data-testid="status-panel"]').is_visible(), False)
        inject_update(page, {"status": _status(60, equipment)})
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

        self.assertIn("合成護符", page.locator('[data-testid="status-panel__condition--t_equipment_warning"]').get_attribute("aria-label"))
        page.focus('[data-testid="status-panel__condition--t_equipment_warning"]')
        inject_update(page, {"status": _status(100, equipment)})
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
        heading enters without a slide and the minimap does not pan.

        The commit and the reading are one call: the heading's leave and the
        scene's later, separate crossfade are both transient, so each pair is
        retained the moment it appears rather than polled for afterwards."""
        page = self._page("reduced")
        self.assertEqual(page.evaluate("document.documentElement.dataset.motion"), "reduced")
        inject_update(page, {"art": _art("a"), "local_map": _interior("grid:capital_altoria:2:0")})
        self._settled_scene(page, "a")
        self._settled(page, '[data-testid="place-card__location"]')

        seen = page.evaluate(
            _REDUCED_COMMIT,
            [
                snapshot_envelope(
                    "",
                    0,
                    {"art": _art("b"), "local_map": _interior("grid:capital_altoria:2:1")},
                )
            ],
        )
        self.assertNotIn("rejected", seen, seen)
        self.assertIsNotNone(seen["headings"], seen)
        for transform in seen["headings"]:
            self.assertTrue(_identity(transform), seen)
        self.assertTrue(_identity(seen["pan"]), seen)
        self.assertIsNotNone(seen["scene"], seen)
        leaving = next(layer for layer in seen["scene"] if layer["inert"])
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
