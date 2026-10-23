import { h } from "vue";
import MapEdgePointers from "../../components/MapEdgePointers.vue";
import { layoutEdgePointers } from "../../lib/map_edge_pointers.js";
import { usableRect } from "../../lib/map_viewport.js";

// MapEdgePointers (redesign-map-drawer): the drawer's HTML layer of
// off-screen commission pointers over a plain stage the size of the drawer
// body. The pointers come from the real pure layout (lib/map_edge_pointers.js)
// against the real drawer-aware rectangle; the dashed panel on the right
// stands in for an open ~360 px detail card.

const FRAME = { width: 1100, height: 620 };

// Built with shorthand so the gate's story-title scan sees only `title`s of stories.
const target = (id, title, sub, x, y, distance) => ({ id, title, sub, x, y, distance });

const TARGETS = [
  target("q1", "護送藥草商人", "西南方 18 km", -900, 900, 18),
  target("q2", "調查帝都古文書", "大致方位 · 東方 680 km", 4000, 280, 680),
  target("q3", "討伐河畔狼群", "東南方 210 km", 3000, 1400, 210),
  target("q4", "北境深林的迷途學者", "北方 980 km", 560, -4000, 980),
  target("q5", "南方港口的走私帳冊", "南方 800 km", 520, 5000, 800),
];

const render = (args) => ({
  setup() {
    const rect = usableRect(FRAME, { drawerOpen: args.drawerOpen, insets: { top: 54, right: 0, bottom: 0, left: 0 }, marginPx: 18 });
    const layout = layoutEdgePointers(args.targets, rect);
    return () =>
      h(
        "div",
        {
          style:
            `position:relative;width:${FRAME.width}px;height:${FRAME.height}px;margin:24px;overflow:hidden;` +
            "background:radial-gradient(90% 80% at 40% 30%, #1d1b17, #0e0d0b);border:1px solid rgba(185,154,96,.45);border-radius:var(--radius);",
        },
        [
          args.drawerOpen
            ? h("div", {
                "data-testid": "map-edge-pointers-story__card",
                style: "position:absolute;top:0;right:0;bottom:0;width:360px;border-left:1px dashed rgba(185,154,96,.45);background:rgba(16,18,22,.6);",
              })
            : null,
          h(MapEdgePointers, { pointers: layout.pointers, more: layout.more }),
        ],
      );
  },
});

export default {
  title: "Overlays/MapEdgePointers",
  component: MapEdgePointers,
};

function fail(story, message) {
  throw new Error(`${story}: ${message}`);
}

// Two commissions off screen: one pointer each, on the side the ray leaves.
export const TwoOffScreen = {
  render,
  args: { targets: TARGETS.slice(0, 2), drawerOpen: false },
  play: async ({ canvasElement }) => {
    const pointers = [...canvasElement.querySelectorAll('[data-testid="map-edge-pointer"]')];
    if (pointers.length !== 2) fail("TwoOffScreen", "two pointers");
    if (pointers[1].dataset.side !== "right") fail("TwoOffScreen", "the eastern commission points right");
    if (!pointers[0].getAttribute("aria-label").startsWith("委託 護送藥草商人")) fail("TwoOffScreen", "pointers carry their commission's name");
  },
};

// Five off screen with the card open: three pointers nearest first, ＋2,
// and nothing under the card.
export const OverflowBesideCard = {
  render,
  args: { targets: TARGETS, drawerOpen: true },
  play: async ({ canvasElement }) => {
    const pointers = [...canvasElement.querySelectorAll('[data-testid="map-edge-pointer"]')];
    if (pointers.map((p) => p.dataset.quest).join() !== "q1,q3,q2") fail("OverflowBesideCard", "three pointers nearest first");
    const more = canvasElement.querySelector('[data-testid="map-edge-pointer-more"]');
    if (more?.textContent !== "＋2") fail("OverflowBesideCard", "the rest collapse into ＋2");
    const card = canvasElement.querySelector('[data-testid="map-edge-pointers-story__card"]').getBoundingClientRect();
    for (const el of [...pointers, more]) {
      if (el.getBoundingClientRect().right > card.left + 0.5) fail("OverflowBesideCard", `${el.textContent} runs under the card`);
    }
  },
};
