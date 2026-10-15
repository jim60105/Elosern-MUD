// webclient-combat-figure-plates (design D4): the stage's `plates` anchor is
// one keyboard group (戰場) after the action dock. Inside it Left/Right move
// between plates in stage order (left to right), Up/Down between a plate and
// its glyphs, Escape returns to `#action-dock` once no tooltip is open, Tab
// leaves, focus is remembered and rescued, and the keys the group handles
// never reach the store's keyboard router.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h, nextTick } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import FigurePlate from "../../components/FigurePlate.vue";
import { platesInStageOrder } from "../../components/plate-group.js";
import { createWindowBridge } from "../../bridge.js";
import { useElosernStore } from "../../stores/elosern.js";

const POISON = { code: "poison", label: "中毒", severity: "harmful" };
const BLESS = { code: "bless", label: "祝福", severity: "beneficial" };

// DOM order differs from stage order on purpose: the formation lists the
// party (controlled first, at the outer edge) and the foes in presenter order.
const PLATES = [
  { identity: 102, name: "幽", side: "party", stageX: 300, conditions: [] },
  { identity: 101, name: "蕾娜", side: "party", stageX: 180, conditions: [POISON, BLESS] },
  { identity: 201, name: "哥布林", side: "foes", stageX: 900, conditions: [BLESS] },
  { identity: 202, name: "狼", side: "foes", stageX: 1100, conditions: [] },
];

describe("the plates keyboard group", () => {
  let wrapper, store, bridge, routed;

  function mountStage({ plates = PLATES, beatHold = false, formation = true } = {}) {
    wrapper = mount(HudFrame, {
      attachTo: document.body,
      props: { mode: "combat", formation, beatHold },
      slots: {
        plates: () =>
          plates.map((p) =>
            h(FigurePlate, { key: p.identity, identity: p.identity, name: p.name, side: p.side, hpCurrent: 10, hpMaximum: 20, conditions: p.conditions, stageX: p.stageX }),
          ),
        "band-command": () => h("section", { id: "action-dock", tabindex: "0" }, "dock"),
      },
    });
    return wrapper;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    routed = [];
    const original = store.focusPress;
    vi.spyOn(store, "focusPress").mockImplementation((key, repeat) => {
      routed.push(key);
      return original.call(store, key, repeat);
    });
    bridge = createWindowBridge(store);
  });
  afterEach(() => {
    bridge.uninstall();
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  const anchor = () => wrapper.get('[data-anchor="plates"]').element;
  const plateEl = (identity) => wrapper.get(`[data-testid="figure-plate"][data-identity="${identity}"]`).element;
  const press = async (key, options = {}) => {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options });
    document.activeElement.dispatchEvent(event);
    await nextTick();
    return event;
  };
  const tabStops = () =>
    [...document.querySelectorAll("button, [tabindex], a, input")].filter((el) => el.tabIndex >= 0 && !el.closest("[inert]"));

  it("is one tab stop after the action dock, and lands on the leftmost plate", async () => {
    mountStage();
    const stops = tabStops();
    const dock = document.getElementById("action-dock");
    // Nothing inside the group is in the tab order; the group follows the dock.
    expect(stops.filter((el) => anchor().contains(el) && el !== anchor())).toHaveLength(0);
    expect(stops.indexOf(anchor())).toBe(stops.indexOf(dock) + 1);
    expect(anchor().getAttribute("role")).toBe("group");
    expect(anchor().getAttribute("aria-label")).toBe("戰場");
    anchor().focus();
    await nextTick();
    expect(document.activeElement).toBe(plateEl(101));
    // While focus is inside, the group leaves the tab order (Tab and Shift+Tab leave it).
    expect(anchor().getAttribute("tabindex")).toBe("-1");
    dock.focus();
    await nextTick();
    expect(anchor().getAttribute("tabindex")).toBe("0");
  });

  it("orders the plates left to right and walks them with Left/Right, Home/End", async () => {
    mountStage();
    expect(platesInStageOrder(anchor()).map((el) => el.getAttribute("data-identity"))).toEqual(["101", "102", "201", "202"]);
    anchor().focus();
    await press("ArrowRight");
    expect(document.activeElement).toBe(plateEl(102));
    await press("ArrowRight");
    await press("ArrowRight");
    expect(document.activeElement).toBe(plateEl(202));
    await press("ArrowRight");
    expect(document.activeElement).toBe(plateEl(202));
    await press("ArrowLeft");
    expect(document.activeElement).toBe(plateEl(201));
    await press("Home");
    expect(document.activeElement).toBe(plateEl(101));
    await press("End");
    expect(document.activeElement).toBe(plateEl(202));
  });

  it("moves between a plate and its glyphs with Down/Up, and a focused glyph opens its tooltip", async () => {
    mountStage();
    anchor().focus();
    const glyphs = [...plateEl(101).querySelectorAll(".figure-plate__glyphs button")];
    expect(glyphs).toHaveLength(2);
    await press("ArrowDown");
    expect(document.activeElement).toBe(glyphs[0]);
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]').textContent).toContain("中毒");
    await press("ArrowDown");
    expect(document.activeElement).toBe(glyphs[1]);
    await press("ArrowDown");
    expect(document.activeElement).toBe(glyphs[1]);
    await press("ArrowUp");
    expect(document.activeElement).toBe(glyphs[0]);
    await press("ArrowUp");
    expect(document.activeElement).toBe(plateEl(101));
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
    // Left/Right from a glyph move to the next plate.
    await press("ArrowDown");
    await press("ArrowRight");
    expect(document.activeElement).toBe(plateEl(102));
  });

  it("closes an open tooltip on the first Escape and returns to the dock on the next, remembering the glyph", async () => {
    mountStage();
    anchor().focus();
    await press("ArrowDown");
    const glyph = document.activeElement;
    await press("Escape");
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
    expect(document.activeElement).toBe(glyph);
    await press("Escape");
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
    anchor().focus();
    await nextTick();
    expect(document.activeElement).toBe(glyph);
  });

  it("keeps the keys it handles from the router, and lets digits through", async () => {
    mountStage();
    anchor().focus();
    for (const key of ["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Home", "End"]) {
      const event = await press(key);
      expect(event.defaultPrevented).toBe(true);
    }
    plateEl(201).focus();
    await press("Enter");
    await press(" ");
    await press("Escape");
    expect(routed).toEqual([]);
    plateEl(201).focus();
    await press("1");
    expect(routed).toEqual(["1"]);
  });

  it("rescues focus to the same figure's plate when its glyph goes away, and to the dock when the group goes inert", async () => {
    const live = mountStage();
    anchor().focus();
    await press("ArrowDown");
    const glyph = document.activeElement;
    glyph.remove();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.activeElement).toBe(plateEl(101));
    await live.setProps({ beatHold: true });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
    expect(anchor().hasAttribute("tabindex")).toBe(false);
    await live.setProps({ beatHold: false });
    expect(anchor().getAttribute("tabindex")).toBe("0");
  });

  it("is no tab stop outside the formation", () => {
    mountStage({ formation: false, plates: [] });
    expect(anchor().hasAttribute("tabindex")).toBe(false);
    expect(anchor().hasAttribute("role")).toBe(false);
  });
});
