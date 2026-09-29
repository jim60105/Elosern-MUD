"""Map legibility acceptance (webclient-map-legibility): the island's one 12px
chrome step and readable node labels on an ordinary neighbourhood, every node
and name still reachable on a payload at the model's node bound, and the full
map's single current-location footprint.

Every payload is injected through the store's own ``receive`` path, so the
checks measure the real client layout.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from ._journey_support import _inject_snapshot, _wait_mode


def _node(x, y, label, visibility, *, action=None, landmark=False):
    return {
        "id": f"grid:legible:{x}:{y}",
        "label": label,
        "x": x,
        "y": y,
        "visibility": visibility,
        "current": visibility == "current",
        "anchor": visibility == "current",
        "landmark": landmark,
        "action": action,
    }


_ORDINARY_ROOMS = (
    (0, 2, "鐘樓", "visible_visited"),
    (1, 2, "北岸大道", "visible_unvisited"),
    (2, 2, "神殿", "visible_unvisited"),
    (0, 1, "西市", "visible_visited"),
    (1, 1, "石板廣場", "current"),
    (2, 1, "東門", "visible_unvisited"),
    (0, 0, "染坊", "visible_unvisited"),
    (1, 0, "西風酒館", "visible_visited"),
    (2, 0, "馬廄", "visible_unvisited"),
)


def _ordinary_panel() -> dict:
    """A three-by-three grid of distinct room names around the current
    square, connectors on all four sides, and no remembered gateway."""
    nodes = []
    edges = []
    for x, y, label, visibility in _ORDINARY_ROOMS:
        adjacent = abs(x - 1) + abs(y - 1) == 1
        action = (
            {"kind": "move", "exit_ref": f"e{x}{y}", "destination": f"grid:legible:{x}:{y}"}
            if adjacent
            else None
        )
        nodes.append(_node(x, y, label, visibility, action=action))
        if adjacent:
            edges.append(
                {
                    "source": "grid:legible:1:1",
                    "destination": f"grid:legible:{x}:{y}",
                    "label": label,
                    "known": True,
                    "traversable": True,
                }
            )
    return {
        "schema_version": 1,
        "available": True,
        "layer": "grid",
        "current_node": "grid:legible:1:1",
        "title": "石板廣場街道圖",
        "nodes": nodes,
        "edges": edges,
        "legend": ["你目前所在的位置", "尚未探索的相鄰位置", "已經探索過的相鄰位置"],
    }


_NAMES = ("渡口", "北岸大道", "舊鐘樓", "染坊", "西風酒館", "石板廣場東側", "馬廄", "神殿前庭")


def _dense_panel() -> dict:
    """The model's 64-node bound: an eight-by-six in-view grid of distinct
    names (two to six glyphs) plus sixteen remembered gateways far away."""
    nodes = []
    for y in range(6):
        for x in range(8):
            visibility = "current" if (x, y) == (3, 2) else "visible_visited"
            nodes.append(_node(x, y, f"{_NAMES[(x + y) % len(_NAMES)]}{x}{y}", visibility))
    bearings = ((0, 40), (40, 0), (0, -40), (-40, 0))
    for i in range(16):
        dx, dy = bearings[i % 4]
        nodes.append(
            _node(3 + dx + i, 2 + dy + i, f"遠方路網{i}", "remembered", landmark=True)
        )
    return {
        "schema_version": 1,
        "available": True,
        "layer": "grid",
        "current_node": "grid:legible:3:2",
        "title": "霧骨渡口街道圖",
        "nodes": nodes,
        "edges": [],
        "legend": ["你目前所在的位置", "已經探索過的相鄰位置", "曾經到過、但不在附近的遠方位置"],
    }


_BOX = """(el) => { const r = el.getBoundingClientRect();
  return {x1: r.left, y1: r.top, x2: r.right, y2: r.bottom}; }"""


class MapLegibilityBrowserTest(BrowserAcceptanceTest):
    """Map chrome, labels and the current footprint on the shared server."""

    def _island_ready(self, page, panel):
        _inject_snapshot(page, {"local_map": panel}, mode="exploration")
        _wait_mode(page, "exploration")
        page.wait_for_function(
            "(n) => document.querySelectorAll('[data-testid=\"local-map\"] .local-map__node').length === n",
            arg=sum(1 for n in panel["nodes"] if n["visibility"] != "remembered"),
            timeout=15000,
        )

    def _open_full_map(self, page):
        page.evaluate("() => window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay-content"]', timeout=15000)

    @covers_requirement(
        "webclient-local-map::map-chrome-and-ordinary-node-labels-are-legible-without-dropping-topology"
    )
    def test_ordinary_island_reads_at_its_chrome_step(self):
        """An ordinary neighbourhood draws at scale 1: the chrome at 12px and
        every node label between 11 and 12 CSS px, markers and labels apart."""
        for viewport in ((1280, 720), (1440, 900), (1920, 1080)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                self._island_ready(page, _ordinary_panel())
                probe = page.evaluate(
                    """(boxOf) => {
                      const box = new Function('return ' + boxOf)();
                      const island = document.querySelector('[data-testid="local-map"]');
                      const svg = island.querySelector('[data-testid="local-map__lattice"]');
                      const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                      const px = (el) => parseFloat(getComputedStyle(el).fontSize);
                      const nodes = [...svg.querySelectorAll('.local-map__node')].map((g) => ({
                        id: g.dataset.node,
                        marker: box(g.querySelector('.local-map__marker')),
                        label: box(g.querySelector('.local-map__node-label')),
                        drawn: px(g.querySelector('.local-map__node-label')) * scale,
                      }));
                      return {
                        scale,
                        title: px(island.querySelector('.local-map__meta-title')),
                        orientation: px(island.querySelector('[data-testid="local-map__orientation"]')),
                        readout: px(island.querySelector('[data-testid="local-map-detail"]')),
                        rings: island.querySelectorAll('.local-map__current-ring').length,
                        nodes,
                      };
                    }""",
                    _BOX,
                )
                self.assertEqual(probe["title"], 12)
                self.assertEqual(probe["orientation"], 12)
                self.assertEqual(probe["readout"], 12)
                self.assertAlmostEqual(probe["scale"], 1, places=3)
                self.assertEqual(len(probe["nodes"]), 9)
                self.assertEqual(probe["rings"], 0, "the island draws no ornament beyond its current marker")

                def apart(a, b):
                    return a["x2"] <= b["x1"] or b["x2"] <= a["x1"] or a["y2"] <= b["y1"] or b["y2"] <= a["y1"]

                for node in probe["nodes"]:
                    self.assertGreaterEqual(node["drawn"], 11, node)
                    self.assertLessEqual(node["drawn"], 12.01, node)
                    for other in probe["nodes"]:
                        if other is node:
                            continue
                        for mine in ("marker", "label"):
                            for theirs in ("marker", "label"):
                                self.assertTrue(
                                    apart(node[mine], other[theirs]),
                                    f"{node['id']} {mine} overlaps {other['id']} {theirs}",
                                )
                page.close()

    @covers_requirement(
        "webclient-local-map::map-chrome-and-ordinary-node-labels-are-legible-without-dropping-topology"
    )
    def test_dense_island_keeps_every_node_and_name_reachable(self):
        """At the 64-node bound the island stays a bounded 208px canvas that
        drops no node or gateway, and the full map names every node and reads
        at 12px or more once zoomed in."""
        panel = _dense_panel()
        in_view = {n["id"]: n["label"] for n in panel["nodes"] if n["visibility"] != "remembered"}
        page = self.logged_in_page((1920, 1080))
        self._island_ready(page, panel)
        island = page.evaluate(
            """() => {
              const island = document.querySelector('[data-testid="local-map"]');
              const svg = island.querySelector('[data-testid="local-map__lattice"]');
              const r = svg.getBoundingClientRect();
              return {
                width: r.width,
                height: r.height,
                titles: Object.fromEntries([...svg.querySelectorAll('.local-map__node')].map(
                  (g) => [g.dataset.node, g.querySelector('.local-map__node-label title').textContent])),
                markers: svg.querySelectorAll('.local-map__edge-marker').length,
                drawn: [...svg.querySelectorAll('.local-map__node-label')].map((t) =>
                  parseFloat(getComputedStyle(t).fontSize) * r.width / svg.viewBox.baseVal.width),
                mirror: [...island.querySelectorAll('[data-testid="local-map-edge-markers-mirror"] li')].length,
              };
            }"""
        )
        self.assertAlmostEqual(island["width"], 208, delta=1)
        self.assertAlmostEqual(island["height"], 208, delta=1)
        self.assertEqual(island["titles"], in_view)
        self.assertEqual(island["markers"], 16)
        self.assertEqual(island["mirror"], 16)
        # Scaled (and windowed at 0.75) but never below 12 × 0.75 = 9px.
        self.assertGreaterEqual(min(island["drawn"]), 9 - 0.01)

        self._open_full_map(page)
        names = page.evaluate(
            """() => Object.fromEntries([...document.querySelectorAll(
                '[data-testid="map-overlay"] .local-map__node')].map((g) => [g.dataset.node, g.getAttribute('aria-label')]))"""
        )
        self.assertEqual(names, in_view)
        zoom_in = page.locator('[data-testid="map-overlay-zoom-in"]')
        for _ in range(20):
            if zoom_in.get_attribute("aria-disabled") == "true":
                break
            zoom_in.click()
        self.assertEqual(zoom_in.get_attribute("aria-disabled"), "true")
        drawn = page.evaluate(
            """() => {
              const svg = document.querySelector('[data-testid="map-overlay"] [data-testid="local-map__lattice"]');
              const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
              const label = svg.querySelector('.local-map__node-label');
              return parseFloat(getComputedStyle(label).fontSize) * scale;
            }"""
        )
        self.assertGreaterEqual(drawn, 12)
        page.close()

    @covers_requirement(
        "webclient-local-map::current-map-location-has-one-unambiguous-footprint",
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone",
    )
    def test_full_map_marks_the_current_place_once(self):
        """The full map rings the current marker concentrically — no pin —
        clear of every label, with each incident connector running on past
        the ring."""
        for viewport in ((1280, 720), (1920, 1080)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                self._island_ready(page, _ordinary_panel())
                self._open_full_map(page)
                probe = page.evaluate(
                    """(boxOf) => {
                      const box = new Function('return ' + boxOf)();
                      const svg = document.querySelector('[data-testid="map-overlay"] [data-testid="local-map__lattice"]');
                      const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                      const rings = [...svg.querySelectorAll('.local-map__current-ring')];
                      const marker = svg.querySelector('[data-testid="local-map__marker--current"]');
                      const centre = (b) => [(b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2];
                      const ring = rings[0];
                      const current = svg.querySelector('[data-node="grid:legible:1:1"]');
                      const cur = current.transform.baseVal.consolidate().matrix;
                      // Connectors run centre to centre; each keeps a visible
                      // segment between the ring's outer edge (radius plus
                      // the half of its 1.4px hairline) and the neighbour's
                      // actionable halo (10 units × marker scale 2.2).
                      const ringOuter = ring.r.baseVal.value + 0.7 / scale;
                      const edges = [...svg.querySelectorAll('.local-map__edge')].map((e) => {
                        const x1 = e.x1.baseVal.value, y1 = e.y1.baseVal.value;
                        const x2 = e.x2.baseVal.value, y2 = e.y2.baseVal.value;
                        return {
                          fromCurrent: Math.hypot(x1 - cur.e, y1 - cur.f) < 0.01,
                          visible: Math.hypot(x2 - x1, y2 - y1) - ringOuter - 10 * 2.2,
                        };
                      });
                      const frame = getComputedStyle(document.querySelector('.map-overlay__viewport'), '::after');
                      return {
                        rings: rings.length,
                        pins: svg.querySelectorAll('.local-map__pin').length,
                        inCurrentGroup: current.contains(ring),
                        ringCentre: centre(box(ring)),
                        markerCentre: centre(box(marker)),
                        ringBox: box(ring),
                        ringOuterPx: ringOuter * scale,
                        framePointer: frame.pointerEvents,
                        frameImage: frame.backgroundImage,
                        ringHidden: ring.getAttribute('aria-hidden'),
                        ringPointer: getComputedStyle(ring).pointerEvents,
                        labels: [...svg.querySelectorAll('.local-map__node-label')].map(box),
                        edges,
                      };
                    }""",
                    _BOX,
                )
                self.assertEqual(probe["rings"], 1)
                self.assertEqual(probe["pins"], 0)
                self.assertTrue(probe["inCurrentGroup"])
                self.assertAlmostEqual(probe["ringCentre"][0], probe["markerCentre"][0], delta=0.5)
                self.assertAlmostEqual(probe["ringCentre"][1], probe["markerCentre"][1], delta=0.5)
                self.assertEqual(probe["ringHidden"], "true")
                self.assertEqual(probe["ringPointer"], "none")
                # The ring's outer edge keeps at least 1px from every label box.
                cx, cy = probe["ringCentre"]
                for label in probe["labels"]:
                    dx = max(label["x1"] - cx, 0, cx - label["x2"])
                    dy = max(label["y1"] - cy, 0, cy - label["y2"])
                    self.assertGreaterEqual(
                        (dx * dx + dy * dy) ** 0.5 - probe["ringOuterPx"], 1, f"the ring crowds a label {label}"
                    )
                self.assertEqual(len(probe["edges"]), 4)
                for edge in probe["edges"]:
                    self.assertTrue(edge["fromCurrent"], edge)
                    self.assertGreater(edge["visible"], 0, edge)
                # The frame's corner brackets are pointer-inert decoration.
                self.assertEqual(probe["framePointer"], "none")
                self.assertIn("linear-gradient", probe["frameImage"])
                page.close()
