// redesign-rest-entry design D4 (rest entry redesign §3): the rest entry's
// first layer — two choice tiles inside the choice-card frame, their
// client-known context lines, the keys (digits, arrows with wrap, Home/End,
// Escape, the Tab trap), the locked state, the corner ✕, the entrance
// switch, and the measured narrow layout.
import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";

import TimeChoiceCard from "../../components/TimeChoiceCard.vue";

const LOCKED = "上一個行動尚未完成，請稍候。";

describe("TimeChoiceCard (redesign-rest-entry)", () => {
  let wrapper;

  function mountCard(props = {}, { parentWidth = null } = {}) {
    const parent = document.createElement("div");
    if (parentWidth !== null) {
      Object.defineProperty(parent, "clientWidth", { value: parentWidth, configurable: true });
    }
    document.body.appendChild(parent);
    wrapper = mount(TimeChoiceCard, { props, attachTo: parent });
    return wrapper;
  }

  const tiles = () => wrapper.findAll('[data-testid="wait-card-tile"]');
  const tile = (key) => wrapper.get(`[data-testid="wait-card-tile"][data-tile="${key}"]`);
  const closeButton = () => wrapper.get('[data-testid="wait-card-close"]');

  function key(element, name, init = {}) {
    const event = new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init });
    element.dispatchEvent(event);
    return event;
  }

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the caption, the accessible name, and the two tiles in order", () => {
    mountCard();
    const root = wrapper.get('[data-testid="wait-card"]');
    expect(root.attributes("role")).toBe("dialog");
    expect(root.attributes("aria-modal")).toBe("true");
    expect(root.attributes("data-card-kind")).toBe("wait");
    expect(root.get(".choice-card__caption").text()).toBe("度過時間");
    expect(root.get(".choice-card__caption").attributes("aria-hidden")).toBe("true");
    const heading = document.getElementById(root.attributes("aria-labelledby"));
    expect(heading.textContent).toBe("等待或睡眠");
    expect(tiles().map((t) => t.attributes("data-tile"))).toEqual(["wait", "sleep"]);
    expect(tiles().map((t) => t.get(".time-choice__badge").text())).toEqual(["1", "2"]);
    expect(tiles().map((t) => t.get(".time-choice__label").text())).toEqual(["等待", "睡眠"]);
    expect(tiles().map((t) => t.get(".time-choice__hint").text())).toEqual(["保持清醒，讓時間流逝", "入睡，恢復精力"]);
    for (const t of tiles()) {
      expect(t.element.tagName).toBe("BUTTON");
      expect(t.find("svg").exists()).toBe(true);
    }
    // It holds no inputs.
    expect(root.find("input").exists()).toBe(false);
    // Autofocus lands on the 等待 tile.
    expect(document.activeElement).toBe(tile("wait").element);
  });

  it("shows both context lines from the props, on one unbroken line each", () => {
    mountCard({ timeLabel: "22:40", fatigue: { reserve_percent: 62, label: "輕度疲勞" } });
    const waitContext = tile("wait").get('[data-testid="wait-card-tile-context"]');
    const sleepContext = tile("sleep").get('[data-testid="wait-card-tile-context"]');
    expect(waitContext.text()).toBe("現在 22:40");
    expect(sleepContext.text()).toBe("精力 62%（輕度疲勞）");
    // The numerals and the stage label are separate spans (mono vs sans).
    expect(sleepContext.get(".time-choice__numerals").text()).toBe("精力 62%");
    expect(sleepContext.get(".time-choice__stage").text()).toBe("（輕度疲勞）");
    // Each tile is described by its hint and its context line.
    for (const key of ["wait", "sleep"]) {
      const ids = tile(key).attributes("aria-describedby").split(" ");
      expect(ids).toHaveLength(2);
      expect(document.getElementById(ids[0]).classList.contains("time-choice__hint")).toBe(true);
      expect(document.getElementById(ids[1]).getAttribute("data-testid")).toBe("wait-card-tile-context");
    }
  });

  it("omits only the context line whose source is absent", () => {
    mountCard({ timeLabel: null, fatigue: { reserve_percent: 62, label: "輕度疲勞" } });
    expect(tile("wait").find('[data-testid="wait-card-tile-context"]').exists()).toBe(false);
    expect(tile("wait").get(".time-choice__badge").text()).toBe("1");
    expect(tile("wait").get(".time-choice__hint").text()).toBe("保持清醒，讓時間流逝");
    expect(tile("wait").attributes("aria-describedby").split(" ")).toHaveLength(1);
    wrapper.unmount();
    document.body.innerHTML = "";
    mountCard({ timeLabel: "22:40", fatigue: null });
    expect(tile("sleep").find('[data-testid="wait-card-tile-context"]').exists()).toBe(false);
    expect(tile("sleep").get(".time-choice__label").text()).toBe("睡眠");
    expect(tile("sleep").get(".time-choice__hint").text()).toBe("入睡，恢復精力");
    expect(tile("wait").get('[data-testid="wait-card-tile-context"]').text()).toBe("現在 22:40");
  });

  it("picks a tile with the digits 1 and 2, consuming them", () => {
    mountCard();
    const outer = [];
    document.body.addEventListener("keydown", (event) => outer.push(event.key));
    key(tile("wait").element, "1");
    key(tile("wait").element, "2");
    expect(wrapper.emitted("pick")).toEqual([["wait"], ["sleep"]]);
    expect(outer).toEqual([]);
  });

  it("moves focus between the tiles with wrapping arrows and Home/End", () => {
    mountCard();
    tile("sleep").element.focus();
    key(document.activeElement, "ArrowRight");
    expect(document.activeElement).toBe(tile("wait").element);
    key(document.activeElement, "ArrowLeft");
    expect(document.activeElement).toBe(tile("sleep").element);
    tile("wait").element.focus();
    key(document.activeElement, "ArrowUp");
    expect(document.activeElement).toBe(tile("sleep").element);
    key(document.activeElement, "ArrowDown");
    expect(document.activeElement).toBe(tile("wait").element);
    key(document.activeElement, "End");
    expect(document.activeElement).toBe(tile("sleep").element);
    key(document.activeElement, "Home");
    expect(document.activeElement).toBe(tile("wait").element);
    expect(wrapper.emitted("pick")).toBeUndefined();
  });

  it("traps Tab and Shift+Tab inside the card", () => {
    mountCard();
    // Order as rendered: the two tiles, then the ✕.
    tile("wait").element.focus();
    key(document.activeElement, "Tab");
    expect(document.activeElement).toBe(tile("sleep").element);
    key(document.activeElement, "Tab");
    expect(document.activeElement).toBe(closeButton().element);
    key(document.activeElement, "Tab");
    expect(document.activeElement).toBe(tile("wait").element);
    key(document.activeElement, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(closeButton().element);
    key(document.activeElement, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(tile("sleep").element);
  });

  it("leaves Enter, Space, and modifier chords to bubble", () => {
    mountCard();
    const outer = [];
    document.body.addEventListener("keydown", (event) => outer.push(event.key));
    key(tile("wait").element, "Enter");
    key(tile("wait").element, " ");
    key(tile("wait").element, "f", { ctrlKey: true });
    key(tile("wait").element, "p");
    expect(outer).toEqual(["Enter", " ", "f"]);
  });

  it("locked: both tiles stay focusable, carry the reason, and pick nothing", async () => {
    mountCard({ locked: true });
    const status = wrapper.get('[role="status"]');
    expect(status.text()).toBe(LOCKED);
    for (const key of ["wait", "sleep"]) {
      expect(tile(key).attributes("aria-disabled")).toBe("true");
      expect(tile(key).attributes("disabled")).toBeUndefined();
      expect(tile(key).attributes("aria-describedby").split(" ")).toContain(status.attributes("id"));
    }
    tile("sleep").element.focus();
    expect(document.activeElement).toBe(tile("sleep").element);
    key(document.activeElement, "1");
    key(document.activeElement, "2");
    await tile("wait").trigger("click");
    await tile("sleep").trigger("click");
    expect(wrapper.emitted("pick")).toBeUndefined();
  });

  it("closes on Escape and on the corner ✕", async () => {
    mountCard();
    key(tile("wait").element, "Escape");
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(closeButton().attributes("aria-label")).toBe("關閉並回到探索");
    expect(closeButton().attributes("title")).toBe("關閉");
    await closeButton().trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(2);
    expect(wrapper.emitted("pick")).toBeUndefined();
  });

  it("a click picks the tile", async () => {
    mountCard();
    await tile("sleep").trigger("click");
    expect(wrapper.emitted("pick")).toEqual([["sleep"]]);
  });

  it("focusTile focuses the named tile, and initialTile picks the autofocus target", () => {
    mountCard();
    wrapper.vm.focusTile("sleep");
    expect(document.activeElement).toBe(tile("sleep").element);
    wrapper.unmount();
    document.body.innerHTML = "";
    mountCard({ initialTile: "sleep" });
    expect(document.activeElement).toBe(tile("sleep").element);
  });

  it("entrance false renders the card still", () => {
    mountCard({ entrance: false });
    expect(wrapper.classes()).toContain("choice-card--still");
    wrapper.unmount();
    document.body.innerHTML = "";
    mountCard();
    expect(wrapper.classes()).not.toContain("choice-card--still");
  });

  it("stacks the tiles when the anchor is narrower than 320px at scale 1", async () => {
    // jsdom lays nothing out: the anchor's width comes from a test attribute
    // read by a temporary clientWidth getter.
    const original = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth");
    Object.defineProperty(HTMLElement.prototype, "clientWidth", {
      configurable: true,
      get() {
        return Number(this.getAttribute("data-test-width") || 0);
      },
    });
    try {
      for (const [width, expected] of [[300, true], [460, false], [0, false]]) {
        const host = mount(
          defineComponent({ render: () => h("div", { "data-test-width": String(width) }, [h(TimeChoiceCard)]) }),
          { attachTo: document.body },
        );
        await nextTick();
        const root = host.get('[data-testid="wait-card"]');
        expect(root.classes().includes("time-choice--stacked"), `width ${width}`).toBe(expected);
        host.unmount();
      }
    } finally {
      if (original) {
        Object.defineProperty(HTMLElement.prototype, "clientWidth", original);
      } else {
        delete HTMLElement.prototype.clientWidth;
      }
    }
  });
});
