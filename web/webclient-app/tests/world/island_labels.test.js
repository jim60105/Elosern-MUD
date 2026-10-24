// Navigation-priority island label placement (label-minimap-exits-and-gateways;
// approved design docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md
// §6.4, §7): the pure helper in lib/island_labels.js.
import { describe, expect, it } from "vitest";
import {
  ASCENT,
  CLEARANCE,
  DESCENT,
  LABEL_GAP,
  boxesClear,
  candidateOrder,
  clearestOrder,
  lineWidth,
  placeIslandLabels,
} from "../../lib/island_labels.js";

const FONT = 16;
const line = (text, kind = "name") => ({ text, kind });

function request(id, tier, x, y, text, extra = {}) {
  const dx = x - 120;
  const dy = y - 120;
  return {
    id,
    tier,
    x,
    y,
    footprint: 10,
    lines: [line(text)],
    outward: Math.hypot(dx, dy) > 0 ? ((Math.atan2(dx, -dy) * 180) / Math.PI + 360) % 360 : null,
    ...extra,
  };
}

function circleClear(box, c) {
  const nx = Math.min(Math.max(c.x, box.x0), box.x1);
  const ny = Math.min(Math.max(c.y, box.y0), box.y1);
  return Math.hypot(c.x - nx, c.y - ny) >= c.r + CLEARANCE - 1e-6;
}

describe("island label candidates", () => {
  it("orders an exit's eight candidates nearest its outward bearing first", () => {
    expect(candidateOrder(0).map((d) => d[0])).toEqual(["n", "ne", "nw", "e", "w", "se", "sw", "s"]);
    expect(candidateOrder(90)[0][0]).toBe("e");
    expect(candidateOrder(null).map((d) => d[0])).toEqual(["s", "n", "e", "w", "se", "ne", "sw", "nw"]);
  });

  it("orders the current label's candidates away from its routes", () => {
    // Routes north and south: the label goes east, then west, before any
    // diagonal or the routes' own directions.
    expect(clearestOrder([0, 180]).slice(0, 2).map((d) => d[0])).toEqual(["e", "w"]);
    expect(clearestOrder([]).map((d) => d[0])[0]).toBe("s");
  });

  it("places a lone exit label outward, clear of its own marker", () => {
    const placed = placeIslandLabels({
      requests: [request("a", "exit", 120, 40, "北門")],
      obstacles: [{ x: 120, y: 40, r: 10, owner: "a" }],
    });
    const label = placed.get("a");
    expect(label.direction).toBe("n");
    expect(label.box.y1).toBeLessThanOrEqual(40 - 10);
    expect(label.leader).toBeNull();
    expect(label.lines[0]).toMatchObject({ text: "北門", x: 120 });
  });

  it("measures boxes in monospace cells at the 16 px step", () => {
    const placed = placeIslandLabels({ requests: [request("a", "exit", 120, 40, "北門ab")] });
    const box = placed.get("a").box;
    expect(box.x1 - box.x0).toBeCloseTo(lineWidth("北門ab", FONT), 6);
    expect(box.y1 - box.y0).toBeCloseTo(1.05 * FONT, 6);
  });

  it("gives exits the first pick over the current label and context", () => {
    // An exit just south of the current node takes the space below it;
    // the current label then avoids both markers and the exit's label.
    const requests = [
      request("ctx", "context", 185, 175, "後巷"),
      request("cur", "current", 120, 120, "中央廣場", { avoid: [180] }),
      request("ex", "exit", 120, 160, "南大道"),
    ];
    const obstacles = [
      { x: 120, y: 120, r: 9, owner: "cur" },
      { x: 120, y: 160, r: 10, owner: "ex" },
      { x: 185, y: 175, r: 3, owner: "ctx" },
    ];
    const placed = placeIslandLabels({ requests, obstacles });
    expect(placed.get("ex").direction).toBe("s");
    expect(placed.get("cur").direction).not.toBe("s");
    const boxes = [...placed.values()].map((p) => p.box);
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) expect(boxesClear(boxes[i], boxes[j])).toBe(true);
      for (const o of obstacles) expect(circleClear(boxes[i], o)).toBe(true);
    }
  });

  it("omits a context label with no free spot but never drops an exit label", () => {
    // A wall of reserved boxes (remembered rim names) leaves the square's
    // centre strip only.
    const wall = [
      { x0: 0, y0: 0, x1: 240, y1: 100 },
      { x0: 0, y0: 140, x1: 240, y1: 240 },
      { x0: 0, y0: 100, x1: 60, y1: 140 },
      { x0: 180, y0: 100, x1: 240, y1: 140 },
    ];
    const placed = placeIslandLabels({
      requests: [request("ctx", "context", 120, 120, "很長的巷道名稱"), request("ex", "exit", 150, 120, "舊城牆遺跡北段")],
      obstacles: wall,
    });
    expect(placed.has("ctx")).toBe(false);
    expect(placed.has("ex")).toBe(true);
  });

  it("falls back to the truncated form, then a leader line, for a crowded exit", () => {
    // Exit at the centre-right with every adjacent spot reserved: the label
    // is drawn farther out, truncated, joined to its marker by a leader.
    const blocked = [
      { x0: 100, y0: 70, x1: 240, y1: 170, owner: undefined },
      { x0: 0, y0: 0, x1: 240, y1: 20 },
    ];
    const placed = placeIslandLabels({
      requests: [
        request("ex", "exit", 170, 120, "舊城牆遺…", {
          lines: [line("舊城牆遺…"), line("通往 西部丘陵與谷地", "via")],
          fallbackLines: [line("舊城牆遺…"), line("通往 西部丘陵…", "via")],
        }),
      ],
      obstacles: [...blocked.map((b) => ({ ...b, owner: "other" }))],
    });
    const label = placed.get("ex");
    expect(label.truncated).toBe(true);
    expect(label.lines.map((l) => l.text)).toEqual(["舊城牆遺…", "通往 西部丘陵…"]);
    expect(label.leader).not.toBeNull();
    for (const box of blocked) expect(boxesClear(label.box, box)).toBe(true);
  });

  it("keeps the classic below-marker spot for a current label with no free candidate", () => {
    const wall = [{ x0: 0, y0: 0, x1: 240, y1: 240, owner: "other" }];
    const placed = placeIslandLabels({
      requests: [request("cur", "current", 120, 120, "交易十字…")],
      obstacles: wall,
    });
    const label = placed.get("cur");
    expect(label.direction).toBe("classic");
    expect(label.box.y0).toBeCloseTo(120 + 10 + 3, 6);
    expect(label.lines[0].text).toBe("交易十字…");
  });

  it("places a gateway exit stub before the ordinary exits", () => {
    // Two exits want the one outward spot below them; the stub (rank 0)
    // takes it even though it comes later in payload order.
    const walls = [
      { x0: 0, y0: 0, x1: 240, y1: 180, owner: "w" },
      { x0: 0, y0: 226, x1: 240, y1: 240, owner: "w" },
    ];
    const placed = placeIslandLabels({
      requests: [
        request("ex", "exit", 120, 190, "南大道", { outward: 180 }),
        request("stub:0", "exit", 120, 191, "通往 聖潔王都", { rank: 0, outward: 180 }),
      ],
      obstacles: walls,
    });
    expect(placed.get("stub:0").direction).toBe("s");
    expect(placed.get("ex").direction).not.toBe("s");
  });

  it("keeps every label of a dense exit ring inside the square", () => {
    const names = ["北市集長…", "鐘樓廣場", "東城門", "染坊街", "南運河碼…", "舊城牆遺…", "鍛冶工匠…", "學士院前…"];
    const requests = names.map((name, i) => {
      const rad = (i * 45 * Math.PI) / 180;
      return request(`e${i}`, "exit", 120 + 50 * Math.sin(rad), 120 - 50 * Math.cos(rad), name);
    });
    const obstacles = requests.map((r) => ({ x: r.x, y: r.y, r: 10, owner: r.id }));
    const placed = placeIslandLabels({ requests, obstacles });
    expect(placed.size).toBe(names.length);
    for (const p of placed.values()) {
      expect(p.box.x0).toBeGreaterThanOrEqual(3 - 1e-6);
      expect(p.box.y0).toBeGreaterThanOrEqual(3 - 1e-6);
      expect(p.box.x1).toBeLessThanOrEqual(237 + 1e-6);
      expect(p.box.y1).toBeLessThanOrEqual(237 + 1e-6);
    }
  });

  it("still draws an exit label when the whole square is taken", () => {
    // Every spot is reserved: the exit keeps its truncated block at the
    // least-overlap spot with a leader line rather than disappearing.
    const placed = placeIslandLabels({
      requests: [
        request("ex", "exit", 120, 120, "舊城牆遺跡", { fallbackLines: [line("舊城牆遺…")] }),
        request("ctx", "context", 60, 60, "後巷"),
      ],
      obstacles: [{ x0: 0, y0: 0, x1: 240, y1: 240, owner: "wall" }],
    });
    expect(placed.has("ctx")).toBe(false);
    const label = placed.get("ex");
    expect(label.lines[0].text).toBe("舊城牆遺…");
    expect(label.truncated).toBe(true);
    expect(label.box.x0).toBeGreaterThanOrEqual(3 - 1e-6);
    expect(label.box.x1).toBeLessThanOrEqual(237 + 1e-6);
  });
});

describe("an island fallback label never covers its own node glyph", () => {
  it("skips a raster box inside its own footprint plus the label gap", () => {
    // Walls fill the square except a pocket around the exit's own marker:
    // every candidate and leader position is taken, so the label falls
    // through to the raster. The only raster box that fits (x0 = y0 = 111,
    // on the 3 + 6k grid) contains the node centre itself.
    const width = lineWidth("甲", FONT);
    const height = (ASCENT + DESCENT) * FONT;
    const pocket = { x0: 111 - CLEARANCE, y0: 111 - CLEARANCE, x1: 111 + width + CLEARANCE + 0.5, y1: 111 + height + CLEARANCE + 0.5 };
    const obstacles = [
      { x0: 0, y0: 0, x1: pocket.x0, y1: 240, owner: "wall" },
      { x0: pocket.x1, y0: 0, x1: 240, y1: 240, owner: "wall" },
      { x0: pocket.x0, y0: 0, x1: pocket.x1, y1: pocket.y0, owner: "wall" },
      { x0: pocket.x0, y0: pocket.y1, x1: pocket.x1, y1: 240, owner: "wall" },
      // The node's own marker never blocks its own label.
      { x: 120, y: 120, r: 10, owner: "ex" },
    ];
    // Precondition: that pocket box is free and lies inside the footprint
    // plus the gap, so a raster scan without the guard would take it.
    const rasterBox = { x0: 111, y0: 111, x1: 111 + width, y1: 111 + height };
    expect(rasterBox.x0 <= 120 && rasterBox.x1 >= 120 && rasterBox.y0 <= 120 && rasterBox.y1 >= 120).toBe(true);
    for (const wall of obstacles.slice(0, 4)) expect(boxesClear(rasterBox, wall)).toBe(true);

    const placed = placeIslandLabels({ requests: [request("ex", "exit", 120, 120, "甲")], obstacles });
    const label = placed.get("ex");
    expect(label).toBeDefined();
    // The label never lands over its own marker: its box keeps at least the
    // footprint plus the label gap from the node centre.
    const nx = Math.min(Math.max(120, label.box.x0), label.box.x1);
    const ny = Math.min(Math.max(120, label.box.y0), label.box.y1);
    expect(Math.hypot(nx - 120, ny - 120)).toBeGreaterThanOrEqual(10 + LABEL_GAP - 1e-9);
    expect(label.box).not.toEqual(rasterBox);
  });
});
