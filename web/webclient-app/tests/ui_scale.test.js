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
  it("keeps the reference factor at and below 1080px", () => {
    for (const h of [720, 900, 1080]) expect(computeUiScale(h)).toBe(1);
  });

  it("scales proportionally above the reference and caps at 1.4", () => {
    expect(computeUiScale(1440)).toBeCloseTo(4 / 3, 4);
    expect(computeUiScale(1512)).toBe(1.4);
    expect(computeUiScale(2160)).toBe(1.4);
  });

  it("never grows past the width's own ratio to the 1920px reference", () => {
    expect(computeUiScale(1440, 2560)).toBeCloseTo(4 / 3, 4);
    expect(computeUiScale(1366, 1024)).toBe(1);
    expect(computeUiScale(1500, 2112)).toBe(1.1);
    expect(computeUiScale(1440, Number.NaN)).toBeCloseTo(4 / 3, 4);
  });

  it("reads a missing or degenerate height as the reference", () => {
    for (const h of [0, -5, Number.NaN, undefined, Infinity]) expect(computeUiScale(h)).toBe(1);
  });
});

describe("installUiScale", () => {
  it("writes the factor, follows resizes, and removes itself on dispose", () => {
    const win = fakeWindow(1440);
    const root = document.createElement("div");
    const dispose = installUiScale({ win, root });
    expect(Number(root.style.getPropertyValue("--ui-scale"))).toBeCloseTo(4 / 3, 4);

    win.resize(720);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1");
    win.resize(1296);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1.2");

    win.innerWidth = 1024;
    win.resize(1440);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("1");
    win.innerWidth = 2560;

    dispose();
    expect(win.listenerCount()).toBe(0);
    expect(root.style.getPropertyValue("--ui-scale")).toBe("");
    win.resize(1440);
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
