// webclient-proportional-ui-scale: the desktop chrome factor and its single
// resize owner.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { computeUiScale, installUiScale } from "../lib/ui_scale.js";

function fakeWindow(innerHeight, innerWidth = 2560) {
  const listeners = new Set();
  return {
    innerHeight,
    innerWidth,
    addEventListener(type, fn) {
      if (type === "resize") listeners.add(fn);
    },
    removeEventListener(type, fn) {
      if (type === "resize") listeners.delete(fn);
    },
    resize(height) {
      this.innerHeight = height;
      for (const fn of [...listeners]) fn();
    },
    listenerCount: () => listeners.size,
  };
}

describe("computeUiScale", () => {
  it("keeps the reference factor at and below the 1451x790 reference", () => {
    // retarget-desktop-viewport-contract D1: the reference is the player's
    // real viewport. The reference itself, anything shorter, and anything
    // narrower than its own aspect ratio implies sit at 1.
    expect(computeUiScale(790, 1451)).toBe(1);
    for (const h of [720, 780, 790]) expect(computeUiScale(h)).toBe(1);
  });

  it("scales proportionally above the reference and caps at 1.4", () => {
    // 2560x1440: both raw ratios (1440/790 = 1.823, 2560/1451 = 1.764)
    // exceed the 1.4 cap, so chrome renders at the cap rather than at four
    // thirds of the old reference.
    expect(computeUiScale(1440, 2560)).toBe(1.4);
    expect(computeUiScale(1512)).toBe(1.4);
    expect(computeUiScale(2160)).toBe(1.4);
    // An uncapped larger display scales by the smaller ratio: 1741x948 has
    // height ratio 1.2 and width ratio 1.1999, so S = 1.2.
    expect(computeUiScale(948, 1741)).toBeCloseTo(1.2, 3);
    expect(computeUiScale(988, 2000)).toBeCloseTo(1.2506, 4);
  });

  it("never grows past the width's own ratio to the 1451px reference", () => {
    // A below-reference viewport (1280x720: 720/790 = 0.911, 1280/1451 =
    // 0.882) keeps S = 1 — chrome never shrinks below its reference floor.
    expect(computeUiScale(720, 1280)).toBe(1);
    expect(computeUiScale(1366, 1024)).toBe(1);
    // A tall, narrow window (900x1600: width ratio 0.62) clamps at 1 even
    // though its height ratio is 2.03.
    expect(computeUiScale(1600, 900)).toBe(1);
    // The width term only ever *lowers* the factor: 1500/790 = 1.899 but
    // 2112/1451 = 1.456, so S = 1.4 at the cap.
    expect(computeUiScale(1500, 2112)).toBe(1.4);
    expect(computeUiScale(1440, Number.NaN)).toBe(1.4);
  });

  it("reads a missing or degenerate height as the reference", () => {
    for (const h of [0, -5, Number.NaN, undefined, Infinity]) expect(computeUiScale(h)).toBe(1);
  });
});

describe("installUiScale", () => {
  it("writes the factor, follows resizes, and removes itself on dispose", () => {
    const win = fakeWindow(948);
    const root = document.createElement("div");
    const dispose = installUiScale({ win, root });
    expect(Number(root.style.getPropertyValue("--ui-scale"))).toBeCloseTo(1.2, 4);

    win.resize(790);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1");
    win.resize(987.5);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1.25");

    win.innerWidth = 1024;
    win.resize(948);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1");
    win.innerWidth = 2560;

    dispose();
    expect(win.listenerCount()).toBe(0);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("");
    win.resize(948);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("");
  });
});

describe("live client wiring", () => {
  it("installs the owner before the first mount and releases it on unmount", () => {
    const source = readFileSync(join(process.cwd(), "web/webclient-app/main.js"), "utf8");
    const install = source.indexOf("installUiScale()");
    expect(install).toBeGreaterThan(-1);
    expect(install).toBeLessThan(source.lastIndexOf("app.mount("));
    expect(source).toMatch(/app\.onUnmount\(disposeUiScale\)/);
  });
});
