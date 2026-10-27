// MapEdgePointers and its pure layout (OpenSpec change redesign-map-drawer).
// The top-level describe block names the webclient-map-drawer requirement it
// evidences; tests/test_map_client_contracts.py MapEdgePointerContracts
// checks that it ran and passed. Expected positions are worked by hand.

import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import MapEdgePointers from "../../components/MapEdgePointers.vue";
import { MAX_EDGE_POINTERS, POINTER_PITCH_PX, farPointAlongBearing, layoutEdgePointers } from "../../lib/map_edge_pointers.js";
import { usableRect } from "../../lib/map_chrome.js";

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
});

// A 1000 x 600 frame with the default 24 px margin: x 24..976, y 24..576,
// centre (500, 300).
const FRAME = { width: 1000, height: 600 };
const RECT = usableRect(FRAME);
const target = (id, x, y, distance) => ({ id, title: `委託${id}`, sub: `${distance} km`, x, y, distance });

describe("floating map chrome avoids selected details", () => {
  it("draws no pointer for a commission already on screen", () => {
    const { pointers, more } = layoutEdgePointers([target("a", 500, 300, 1)], RECT);
    expect(pointers).toEqual([]);
    expect(more).toBeNull();
  });

  it("puts a pointer where the ray from the centre leaves the usable rectangle", () => {
    const { pointers } = layoutEdgePointers([target("east", 3000, 300, 50)], RECT);
    expect(pointers).toHaveLength(1);
    expect(pointers[0]).toMatchObject({ id: "east", side: "right", x: 976, y: 300, angle: 0 });
  });

  it("keeps the pointer left of an open ~360 px detail drawer", () => {
    const open = usableRect(FRAME, { drawerOpen: true });
    expect(open.right).toBe(616);
    const { pointers } = layoutEdgePointers([target("east", 3000, 300, 50)], open);
    expect(pointers[0].x).toBe(616);
    expect(pointers[0].x).toBeLessThanOrEqual(FRAME.width - 360);
  });

  it("orders by distance, shows at most three and collapses the rest into ＋n", () => {
    const targets = [
      target("d4", 500, -4000, 400),
      target("d1", 3000, 250, 100),
      target("d3", -3000, 300, 300),
      target("d5", 500, 5000, 500),
      target("d2", 500, 4000, 200),
    ];
    const { pointers, more } = layoutEdgePointers(targets, RECT);
    expect(MAX_EDGE_POINTERS).toBe(3);
    expect(pointers.map((p) => p.id)).toEqual(["d1", "d2", "d3"]);
    expect(more).toMatchObject({ count: 2, ids: ["d4", "d5"], side: "top" });
  });

  it("stacks pointers on one side a full pitch apart, nearest keeping its spot", () => {
    const targets = [target("near", 3000, 300, 10), target("mid", 3000, 310, 20), target("far", 3000, 295, 30)];
    const { pointers } = layoutEdgePointers(targets, RECT);
    const ys = Object.fromEntries(pointers.map((p) => [p.id, p.y]));
    expect(ys.near).toBe(300);
    expect(ys.mid).toBe(300 + POINTER_PITCH_PX);
    expect(ys.far).toBe(300 - POINTER_PITCH_PX);
    for (const p of pointers) expect(p.x).toBe(976);
  });

  it("keeps a stacked pointer inside its side near a corner", () => {
    const targets = [target("a", 3000, 1500, 10), target("b", 3000, 1600, 20)];
    const { pointers } = layoutEdgePointers(targets, RECT);
    for (const p of pointers) {
      expect(p.y).toBeGreaterThanOrEqual(RECT.top);
      expect(p.y).toBeLessThanOrEqual(RECT.bottom);
    }
    expect(Math.abs(pointers[0].y - pointers[1].y)).toBeGreaterThanOrEqual(POINTER_PITCH_PX);
  });

  it("keeps the whole chip inside its side when given its half extent", () => {
    const { pointers } = layoutEdgePointers(
      [target("corner", 3000, 1700, 1), target("top", 3000, -1100, 2)],
      RECT,
      { halfWidth: 130, halfHeight: 20 },
    );
    const corner = pointers.find((p) => p.id === "corner");
    expect(corner.side).toBe("right");
    expect(corner.y).toBe(RECT.bottom - 20);
    const top = pointers.find((p) => p.id === "top");
    expect(top.side).toBe("right");
    expect(top.y).toBe(RECT.top + 20);
    const north = layoutEdgePointers([target("n", 70000, -50000, 1)], RECT, { halfWidth: 130 }).pointers[0];
    expect(north.side).toBe("top");
    expect(north.x).toBe(RECT.right - 130);
  });

  it("spaces top-edge chips by their width rather than the vertical pitch", () => {
    const { pointers } = layoutEdgePointers(
      [target("near", 500, -4000, 1), target("far", 510, -4000, 2)],
      RECT,
      { halfWidth: 140, halfHeight: 24 },
    );
    expect(pointers.every((p) => p.side === "top")).toBe(true);
    expect(Math.abs(pointers[0].x - pointers[1].x)).toBeGreaterThanOrEqual(288);
  });

  it("projects a compass bearing north-up", () => {
    const p = farPointAlongBearing({ x: 10, y: 20 }, 90, 100);
    expect(p.x).toBeCloseTo(110);
    expect(p.y).toBeCloseTo(20);
  });

  it.each([
    ["a full top edge", [target("a", 400, -1000, 1), target("b", 400, -1000, 2), target("c", 400, -1000, 3)]],
    ["adjacent corners", [target("a", -500, -1000, 1), target("b", -1000, -600, 2)]],
  ])("never overlaps chips at %s, folding any unplaceable targets into the list", (_name, targets) => {
    const rect = { left: 0, right: 800, top: 0, bottom: 500 };
    const { pointers, more } = layoutEdgePointers(targets, rect, { pitch: 52, halfWidth: 140, halfHeight: 24 });
    expect([...pointers.map((p) => p.id), ...(more?.ids ?? [])].sort()).toEqual(targets.map((t) => t.id).sort());
    const boxes = [...pointers.map((p) => [p, 280]), ...(more ? [[more, 80]] : [])].map(([p, width]) => {
      const left = p.side === "left" ? p.x : p.side === "right" ? p.x - width : p.x - width / 2;
      const top = p.side === "top" ? p.y : p.side === "bottom" ? p.y - 48 : p.y - 24;
      return { left, right: left + width, top, bottom: top + 48 };
    });
    for (const [i, a] of boxes.entries()) {
      expect(a.left).toBeGreaterThanOrEqual(rect.left);
      expect(a.right).toBeLessThanOrEqual(rect.right);
      expect(a.top).toBeGreaterThanOrEqual(rect.top);
      expect(a.bottom).toBeLessThanOrEqual(rect.bottom);
      for (const b of boxes.slice(i + 1)) {
        expect(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top).toBe(true);
      }
    }
    if (_name === "a full top edge") expect(more?.count).toBeGreaterThan(0);
  });

  it("renders named pointer buttons and a ＋n chip that opens the list", async () => {
    const { pointers, more } = layoutEdgePointers(
      [target("a", 3000, 300, 1), target("b", -3000, 300, 2), target("c", 500, 3000, 3), target("d", 500, -3000, 4)],
      RECT,
    );
    const w = mount(MapEdgePointers, { props: { pointers, more } });
    wrappers.push(w);
    const buttons = w.findAll('[data-testid="map-edge-pointer"]');
    expect(buttons).toHaveLength(3);
    expect(buttons[0].element.tagName).toBe("BUTTON");
    expect(buttons[0].attributes("aria-label")).toBe("委託 委託a，1 km，在地圖上顯示");
    expect(buttons[0].attributes("style")).toContain("left: 976px");
    await buttons[1].trigger("click");
    expect(w.emitted("activate")).toEqual([["b"]]);
    const chip = w.find('[data-testid="map-edge-pointer-more"]');
    expect(chip.text()).toBe("＋1");
    expect(chip.attributes("aria-label")).toContain("另有 1 項委託");
    await chip.trigger("click");
    expect(w.emitted("more")).toHaveLength(1);
  });
});
