import { describe, expect, it } from "vitest";
import {
  FIT_INSET,
  MAX_SCALE,
  ZOOM_STEP,
  fitView,
  scaleBounds,
  clampView,
  zoomAt,
  panBy,
  centreOn,
  revealBox,
  resizeView,
  viewBoxOf,
} from "../../lib/map_view.js";

describe("map_view pure math", () => {
  it("fits a 560 × 1074 street in a 1124 × 735 frame with s ≈ 0.662 inside frame less inset", () => {
    const frame = { vw: 1124, vh: 735, W: 560, H: 1074 };
    const view = fitView(frame);

    expect(view.fitted).toBe(true);
    // sFit = min(1, (1124 - 24)/560, (735 - 24)/1074) = 711 / 1074 ≈ 0.66201
    expect(view.s).toBeCloseTo(0.662, 3);

    // Canvas rendered box in viewport pixels
    const canvasPxW = frame.W * view.s;
    const canvasPxH = frame.H * view.s;

    // Viewport padding around canvas
    const padLeft = -view.x * view.s;
    const padTop = -view.y * view.s;
    const padRight = frame.vw - (padLeft + canvasPxW);
    const padBottom = frame.vh - (padTop + canvasPxH);

    // Centred on both axes: horizontal and vertical padding are symmetric
    expect(padLeft).toBeCloseTo(padRight, 2);
    expect(padTop).toBeCloseTo(padBottom, 2);

    // Whole canvas inside the frame less the inset
    expect(padLeft).toBeGreaterThanOrEqual(FIT_INSET - 1e-4);
    expect(padRight).toBeGreaterThanOrEqual(FIT_INSET - 1e-4);
    expect(padTop).toBeGreaterThanOrEqual(FIT_INSET - 1e-4);
    expect(padBottom).toBeGreaterThanOrEqual(FIT_INSET - 1e-4);
  });

  it("fits a 280 × 226 single node at s = 1, centred on both axes", () => {
    const frame = { vw: 1124, vh: 735, W: 280, H: 226 };
    const view = fitView(frame);

    expect(view.s).toBe(1);
    expect(view.fitted).toBe(true);
    expect(view.x).toBe((280 - 1124) / 2); // -422
    expect(view.y).toBe((226 - 735) / 2); // -254.5
    expect(viewBoxOf(view, frame)).toBe("-422 -254.5 1124 735");
  });

  it("zoomAt keeps the anchor's user point invariant under the anchor", () => {
    const frame = { vw: 1000, vh: 800, W: 2000, H: 1600 };
    const initialView = { s: 1, x: 200, y: 200, fitted: false };
    const anchor = { x: 350, y: 450 };

    const userXBefore = initialView.x + anchor.x / initialView.s;
    const userYBefore = initialView.y + anchor.y / initialView.s;

    const zoomed = zoomAt(initialView, 1.25, anchor, frame);

    const userXAfter = zoomed.x + anchor.x / zoomed.s;
    const userYAfter = zoomed.y + anchor.y / zoomed.s;

    expect(userXAfter).toBeCloseTo(userXBefore, 4);
    expect(userYAfter).toBeCloseTo(userYBefore, 4);
  });

  it("repeated zoom-out stops at the fitted scale, and repeated zoom-in stops at 2", () => {
    const frame = { vw: 800, vh: 600, W: 1600, H: 1200 };
    const bounds = scaleBounds(frame);
    let view = { s: 1, x: 100, y: 100, fitted: false };

    // Repeated zoom out
    for (let i = 0; i < 20; i++) {
      view = zoomAt(view, 1 / ZOOM_STEP, null, frame);
    }
    expect(view.s).toBeCloseTo(bounds.min, 5);

    // Repeated zoom in
    for (let i = 0; i < 20; i++) {
      view = zoomAt(view, ZOOM_STEP, null, frame);
    }
    expect(view.s).toBeCloseTo(MAX_SCALE, 5);
  });

  it("panBy stops at each canvas edge and cannot pan an axis the canvas does not overflow", () => {
    // W=1000 overflows vw=400 (spanX=400 < 1000), but H=300 does not overflow vh=500 (spanY=500 >= 300)
    const frame = { vw: 400, vh: 500, W: 1000, H: 300 };
    const view = { s: 1, x: 200, y: -100, fitted: false };

    // Non-overflowing Y axis is always centred
    const expectedY = (300 - 500) / 2; // -100

    // Pan right (moving pointer right by 500px moves content right, shifts x toward 0)
    const panRight = panBy(view, 500, 200, frame);
    expect(panRight.x).toBe(0); // clamped at left edge
    expect(panRight.y).toBe(expectedY);

    // Pan left (moving pointer left by 1000px moves content left, shifts x toward W - spanX = 600)
    const panLeft = panBy(view, -1000, -200, frame);
    expect(panLeft.x).toBe(600); // clamped at right edge
    expect(panLeft.y).toBe(expectedY);
  });

  it("centreOn of a corner node clamps origin to bounds", () => {
    const frame = { vw: 500, vh: 500, W: 1200, H: 1000 };
    const view = { s: 1, x: 300, y: 300, fitted: false };

    // Corner at (0, 0): centering would put origin at (-250, -250), clamps to (0, 0)
    const topLeft = centreOn(view, { x: 0, y: 0 }, frame);
    expect(topLeft.x).toBe(0);
    expect(topLeft.y).toBe(0);

    // Corner at (1200, 1000): centering would put origin at (950, 750), clamps to (700, 500)
    const bottomRight = centreOn(view, { x: 1200, y: 1000 }, frame);
    expect(bottomRight.x).toBe(1200 - 500);
    expect(bottomRight.y).toBe(1000 - 500);
  });

  it("revealBox moves the minimum distance and leaves an already-visible box untouched", () => {
    const frame = { vw: 600, vh: 400, W: 1500, H: 1000 };
    const view = { s: 1, x: 200, y: 200, fitted: false };
    // Currently visible window is x in [200, 800], y in [200, 600]

    // 1. Already visible box
    const insideBox = { x: 300, y: 300, width: 50, height: 50 };
    const unchanged = revealBox(view, insideBox, 24, frame);
    expect(unchanged.x).toBe(view.x);
    expect(unchanged.y).toBe(view.y);

    // 2. Box slightly off to the right: right edge is at 820.
    // Margin is 24. With span=600, visible limit is newX + 600 - 24 >= 820 => newX >= 244.
    const offRightBox = { x: 770, y: 300, width: 50, height: 50 };
    const shifted = revealBox(view, offRightBox, 24, frame);
    expect(shifted.x).toBe(820 + 24 - 600); // 244
    expect(shifted.y).toBe(view.y); // y untouched
  });

  it("resizeView refits a fitted view and preserves the centre of a touched one", () => {
    const oldFrame = { vw: 1000, vh: 800, W: 1200, H: 900 };
    const newFrame = { vw: 800, vh: 600, W: 1200, H: 900 };

    // Case 1: fitted view refits to new frame
    const fitted = fitView(oldFrame);
    const resizedFitted = resizeView(fitted, oldFrame, newFrame);
    expect(resizedFitted.fitted).toBe(true);
    expect(resizedFitted.s).toBe(fitView(newFrame).s);
    expect(resizedFitted.x).toBe(fitView(newFrame).x);
    expect(resizedFitted.y).toBe(fitView(newFrame).y);

    // Case 2: touched view preserves centre user point
    const touched = { s: 1.5, x: 300, y: 200, fitted: false };
    const centreUserX = touched.x + (oldFrame.vw / touched.s) / 2;
    const centreUserY = touched.y + (oldFrame.vh / touched.s) / 2;

    const resizedTouched = resizeView(touched, oldFrame, newFrame);
    expect(resizedTouched.fitted).toBe(false);
    expect(resizedTouched.s).toBe(touched.s);

    const newCentreUserX = resizedTouched.x + (newFrame.vw / resizedTouched.s) / 2;
    const newCentreUserY = resizedTouched.y + (newFrame.vh / resizedTouched.s) / 2;

    expect(newCentreUserX).toBeCloseTo(centreUserX, 4);
    expect(newCentreUserY).toBeCloseTo(centreUserY, 4);
  });

  it("handles fitted flag transitions correctly across operations", () => {
    const frame = { vw: 800, vh: 600, W: 1000, H: 800 };
    const initial = fitView(frame);
    expect(initial.fitted).toBe(true);

    // clampView preserves fitted flag
    expect(clampView(initial, frame).fitted).toBe(true);

    // resizeView preserves fitted flag
    expect(resizeView(initial, frame, { ...frame, vw: 900 }).fitted).toBe(true);

    // All user manipulations set fitted to false
    expect(zoomAt(initial, 1.25, null, frame).fitted).toBe(false);
    expect(panBy(initial, 10, 10, frame).fitted).toBe(false);
    expect(centreOn(initial, { x: 500, y: 400 }, frame).fitted).toBe(false);
    expect(revealBox(initial, { x: 100, y: 100, width: 20, height: 20 }, 10, frame).fitted).toBe(false);
  });
});
