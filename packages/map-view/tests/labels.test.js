// Label measurement and greedy collision placement, with synthetic pixel
// frames. Candidates carry a plain id, their lines and a priority; the host
// supplies the projection and the text measurer.

import assert from "node:assert/strict";
import { test } from "node:test";

import { estimateTextWidth, placeLabels, rectsOverlap } from "../src/labels.js";

const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);
const at = (id, x, y, priority = 6, lines = ["甲"]) => ({ id, x, y, priority, lines });
const projectSelf = (entry) => ({ x: entry.x, y: entry.y });

test("estimates CJK and Latin label widths", () => {
  // One em per CJK glyph, about 0.58 em per Latin glyph, 0.3 em per space.
  assert.equal(estimateTextWidth("甲", 16), 16);
  close(estimateTextWidth("A", 16), 0.58 * 16);
  close(estimateTextWidth(" ", 16), 0.3 * 16);
  // Letter spacing adds one step per glyph.
  close(estimateTextWidth("甲乙", 16, 0.04), 2 * 1.04 * 16);
  assert.equal(estimateTextWidth("", 16), 0);
});

test("measures box overlap without counting a shared edge", () => {
  const box = { left: 0, top: 0, right: 10, bottom: 10 };
  assert.equal(rectsOverlap(box, { left: 10, top: 0, right: 20, bottom: 10 }), false);
  assert.equal(rectsOverlap(box, { left: 9, top: 0, right: 20, bottom: 10 }), true);
  assert.equal(rectsOverlap(box, { left: 0, top: 10, right: 10, bottom: 20 }), false);
});

test("places higher-priority labels first and hides a colliding one", () => {
  const frame = { width: 60, height: 60 };
  // The always-drawn label is clamped inside the frame; the low-priority
  // label at the same point fits nowhere and is hidden, never shrunk.
  const out = placeLabels([at("here", 30, 30, 0), at("other", 30, 30, 6)], projectSelf, frame);
  assert.deepEqual(out.map((label) => label.id), ["here"]);
  assert.deepEqual(out[0].box, { left: 20, top: 0, right: 40, bottom: 24 });
  assert.equal(out[0].anchor, "middle");
  // A wider frame places both, in priority order, without overlapping.
  const roomy = placeLabels([at("here", 100, 30, 1), at("other", 100, 120, 6)], projectSelf, {
    width: 200,
    height: 200,
  });
  assert.deepEqual(roomy.map((label) => label.id), ["here", "other"]);
  assert.equal(rectsOverlap(roomy[0].box, roomy[1].box), false);
});

test("always places the reserved priority labels inside the frame", () => {
  // Both priority 0 and 1 are must-place; a custom predicate can widen that.
  const frame = { width: 80, height: 80 };
  const out = placeLabels([at("a", 79, 79, 0), at("b", 1, 1, 1)], projectSelf, frame);
  assert.deepEqual(out.map((label) => label.id), ["a", "b"]);
  for (const label of out) {
    assert.ok(label.box.left >= 0 && label.box.top >= 0);
    assert.ok(label.box.right <= frame.width && label.box.bottom <= frame.height);
  }
  const widened = placeLabels([at("c", 79, 79, 4)], projectSelf, frame, { mustPlace: () => true });
  assert.deepEqual(widened.map((label) => label.id), ["c"]);
});

test("avoids drawing a label across a road when another spot is clear", () => {
  const frame = { width: 200, height: 200 };
  // The default "above" spot is crossed by a horizontal road, so the label
  // lands below its marker instead of over the road.
  const out = placeLabels([at("node", 100, 100, 6)], projectSelf, frame, {
    segments: [{ x1: 80, y1: 70, x2: 120, y2: 70 }],
  });
  assert.equal(out.length, 1);
  assert.ok(out[0].box.top > 100, `expected a spot below the marker, got ${JSON.stringify(out[0].box)}`);
  // Without the road the same candidate prefers the spot above the marker.
  const clear = placeLabels([at("node", 100, 100, 6)], projectSelf, frame);
  assert.ok(clear[0].box.bottom < 100);
});

test("keeps a label out of another marker's box", () => {
  const frame = { width: 200, height: 200 };
  // The marker at the label's own anchor is ignored, any other marker is not.
  const own = placeLabels([at("node", 100, 100, 6)], projectSelf, frame, { obstacles: [{ id: "node", x: 100, y: 100 }] });
  assert.equal(own.length, 1);
  const blocked = placeLabels([at("node", 100, 100, 6)], projectSelf, frame, {
    obstacles: [{ id: "other", x: 100, y: 60 }],
  });
  assert.equal(blocked.length, 1);
  assert.ok(blocked[0].box.top > 60, "the label must not sit on the neighbouring marker");
});
