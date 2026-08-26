// H4 (webclient-hud-04-reference-drawers, task 2.3): the shared focus
// trap cycles across a multi-control surface in both directions, ignores
// hidden and disabled nodes, and restores focus to the opener.
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  createFocusTrap,
  FOCUSABLE_SELECTOR,
  focusableElements,
} from "../components/focus-trap.js";

describe("focus-trap (H4 D5)", () => {
  let fixture;

  function buildSurface() {
    const container = document.createElement("div");
    container.setAttribute("data-testid", "trap-surface");
    const mkButton = (key) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = key;
      b.dataset.key = key;
      container.appendChild(b);
      return b;
    };
    const a = mkButton("one");
    const b = mkButton("two");
    const c = mkButton("three");
    const input = document.createElement("input");
    input.dataset.key = "field";
    container.appendChild(input);
    const link = document.createElement("a");
    link.href = "#x";
    link.dataset.key = "link";
    container.appendChild(link);
    const opener = document.createElement("button");
    opener.type = "button";
    opener.dataset.key = "opener";
    document.body.appendChild(container);
    document.body.appendChild(opener);
    return { container, a, b, c, input, link, opener };
  }

  function tabEvent(shiftKey) {
    return {
      key: "Tab",
      shiftKey: !!shiftKey,
      prevented: false,
      preventDefault() {
        this.prevented = true;
      },
    };
  }

  beforeEach(() => {
    fixture = buildSurface();
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("cycles focus forward and backward across a multi-control surface", () => {
    const { container, a, b, opener } = fixture;
    const trap = createFocusTrap(container, { initialFocusEl: a, openerEl: opener });
    trap.enter();
    expect(document.activeElement).toBe(a);

    trap.onKeydown(tabEvent(false));
    expect(document.activeElement).toBe(b);

    trap.onKeydown(tabEvent(true));
    expect(document.activeElement).toBe(a);

    // Wrap-around: backward from the first control lands on the last
    // focusable (the link), and forward from the last lands back on the
    // first (the "one" button) — the cycle is circular.
    trap.onKeydown(tabEvent(true));
    expect(document.activeElement).toBe(fixture.link);
    trap.onKeydown(tabEvent(false));
    expect(document.activeElement).toBe(a);
  });

  it("ignores hidden (display:none / visibility:hidden) and disabled nodes", () => {
    const { container, a, b, c, input, link, opener } = fixture;
    const hidden = document.createElement("button");
    hidden.type = "button";
    hidden.dataset.key = "hidden-display";
    hidden.style.display = "none";
    container.appendChild(hidden);
    const hiddenVis = document.createElement("button");
    hiddenVis.type = "button";
    hiddenVis.dataset.key = "hidden-visibility";
    hiddenVis.style.visibility = "hidden";
    container.appendChild(hiddenVis);
    const disabled = document.createElement("button");
    disabled.type = "button";
    disabled.dataset.key = "disabled";
    disabled.disabled = true;
    container.appendChild(disabled);

    const keys = focusableElements(container).map((el) => el.dataset.key);
    // The visible, enabled controls only.
    expect(keys).toContain("one");
    expect(keys).toContain("two");
    expect(keys).toContain("three");
    expect(keys).toContain("field");
    expect(keys).toContain("link");
    expect(keys).not.toContain("hidden-display");
    expect(keys).not.toContain("hidden-visibility");
    expect(keys).not.toContain("disabled");
    expect(keys).toHaveLength(5);
  });

  it("restore() returns focus to the opener", () => {
    const { container, a, opener } = fixture;
    const trap = createFocusTrap(container, { initialFocusEl: a, openerEl: opener });
    trap.enter();
    expect(document.activeElement).toBe(a);
    trap.restore();
    expect(document.activeElement).toBe(opener);
  });

  it("restore() falls back to the surface's first focusable when the opener is detached", () => {
    const { container, a, opener } = fixture;
    const trap = createFocusTrap(container, { initialFocusEl: a, openerEl: opener });
    trap.enter();
    expect(document.activeElement).toBe(a);
    document.body.removeChild(opener);
    trap.restore();
    expect(document.activeElement).toBe(a);
  });

  it("exposes the documented focusable-selector list", () => {
    expect(FOCUSABLE_SELECTOR).toContain("button:not([disabled])");
    expect(FOCUSABLE_SELECTOR).toContain("[tabindex]:not([tabindex='-1'])");
  });
});
