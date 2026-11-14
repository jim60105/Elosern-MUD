// The scroll-edge fade (map-column-instrument-geometry design D5/D6): the
// pure edge test, and the composable's scroll, child-mount re-observation,
// element swap and cleanup paths with a fake ResizeObserver.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";
import { scrollEdges, useScrollEdgeFade } from "../composables/use-scroll-edge-fade.js";

describe("scrollEdges", () => {
  it.each([
    [{ scrollTop: 0, clientHeight: 100, scrollHeight: 100 }, { above: false, below: false }],
    [{ scrollTop: 0, clientHeight: 100, scrollHeight: 300 }, { above: false, below: true }],
    [{ scrollTop: 100, clientHeight: 100, scrollHeight: 300 }, { above: true, below: true }],
    [{ scrollTop: 200, clientHeight: 100, scrollHeight: 300 }, { above: true, below: false }],
    [{ scrollTop: 0.5, clientHeight: 100, scrollHeight: 100.5 }, { above: false, below: false }],
  ])("reports the edges of %o", (box, expected) => {
    expect(scrollEdges(box)).toEqual(expected);
  });
});

describe("useScrollEdgeFade", () => {
  const originalResizeObserver = globalThis.ResizeObserver;
  let observers;

  class FakeResizeObserver {
    constructor(callback) {
      this.callback = callback;
      this.targets = new Set();
      this.disconnects = 0;
      observers.push(this);
    }
    observe(target) {
      this.targets.add(target);
    }
    disconnect() {
      this.targets.clear();
      this.disconnects += 1;
    }
  }

  beforeEach(() => {
    observers = [];
    globalThis.ResizeObserver = FakeResizeObserver;
  });

  afterEach(() => {
    if (originalResizeObserver === undefined) {
      delete globalThis.ResizeObserver;
    } else {
      globalThis.ResizeObserver = originalResizeObserver;
    }
    document.body.innerHTML = "";
  });

  function setBox(el, { scrollTop, clientHeight, scrollHeight }) {
    Object.defineProperty(el, "scrollTop", { configurable: true, writable: true, value: scrollTop });
    Object.defineProperty(el, "clientHeight", { configurable: true, value: clientHeight });
    Object.defineProperty(el, "scrollHeight", { configurable: true, value: scrollHeight });
  }

  function mountProbe() {
    const which = ref("a");
    let state;
    const Probe = defineComponent({
      setup() {
        const box = ref(null);
        state = { box, ...useScrollEdgeFade(box) };
        return () => h("div", { key: which.value, ref: box, "data-box": which.value }, [h("p", "first")]);
      },
    });
    const wrapper = mount(Probe, { attachTo: document.body });
    return { wrapper, which, state: () => state };
  }

  async function flushMutations() {
    await Promise.resolve();
    await Promise.resolve();
  }

  it("re-measures on scroll and starts with no edge beyond", async () => {
    const { wrapper, state } = mountProbe();
    const { box, moreAbove, moreBelow } = state();
    expect(moreAbove.value).toBe(false);
    expect(moreBelow.value).toBe(false);
    setBox(box.value, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    box.value.dispatchEvent(new Event("scroll"));
    expect([moreAbove.value, moreBelow.value]).toEqual([false, true]);
    box.value.scrollTop = 100;
    box.value.dispatchEvent(new Event("scroll"));
    expect([moreAbove.value, moreBelow.value]).toEqual([true, true]);
    box.value.scrollTop = 200;
    box.value.dispatchEvent(new Event("scroll"));
    expect([moreAbove.value, moreBelow.value]).toEqual([true, false]);
    wrapper.unmount();
  });

  it("observes a child mounted after setup and re-measures without a scroll", async () => {
    const { wrapper, state } = mountProbe();
    const { box, moreBelow } = state();
    const observer = observers.at(-1);
    expect(observer.targets.has(box.value)).toBe(true);
    expect(observer.targets.has(box.value.firstElementChild)).toBe(true);

    setBox(box.value, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    const child = document.createElement("section");
    box.value.appendChild(child);
    await flushMutations();
    expect(observer.targets.has(child)).toBe(true);
    expect(moreBelow.value).toBe(true);

    // A resize alone (no scroll, no mutation) re-measures too.
    setBox(box.value, { scrollTop: 0, clientHeight: 100, scrollHeight: 100 });
    observer.callback([]);
    expect(moreBelow.value).toBe(false);

    child.remove();
    await flushMutations();
    expect(observer.targets.has(child)).toBe(false);
    wrapper.unmount();
  });

  it("releases the old element when the ref swaps to a new one", async () => {
    const { wrapper, which, state } = mountProbe();
    const { box, moreBelow } = state();
    const first = box.value;
    const firstObserver = observers.at(-1);
    which.value = "b";
    await nextTick();
    await nextTick();
    const second = box.value;
    expect(second).not.toBe(first);
    expect(firstObserver.targets.size).toBe(0);
    const secondObserver = observers.at(-1);
    expect(secondObserver).not.toBe(firstObserver);
    expect(secondObserver.targets.has(second)).toBe(true);

    // The released element's scroll no longer drives the refs.
    setBox(first, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    first.dispatchEvent(new Event("scroll"));
    expect(moreBelow.value).toBe(false);
    setBox(second, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    second.dispatchEvent(new Event("scroll"));
    expect(moreBelow.value).toBe(true);
    wrapper.unmount();
  });

  it("disconnects its observers and stops listening on unmount", async () => {
    const { wrapper, state } = mountProbe();
    const { box, moreBelow } = state();
    const el = box.value;
    const observer = observers.at(-1);
    const before = observer.disconnects;
    wrapper.unmount();
    expect(observer.disconnects).toBeGreaterThan(before);
    expect(observer.targets.size).toBe(0);
    setBox(el, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    el.dispatchEvent(new Event("scroll"));
    expect(moreBelow.value).toBe(false);
  });

  it("measures from scroll alone where ResizeObserver is absent", async () => {
    delete globalThis.ResizeObserver;
    const { wrapper, state } = mountProbe();
    const { box, moreBelow } = state();
    expect(observers).toHaveLength(0);
    setBox(box.value, { scrollTop: 0, clientHeight: 100, scrollHeight: 300 });
    box.value.dispatchEvent(new Event("scroll"));
    expect(moreBelow.value).toBe(true);
    wrapper.unmount();
  });
});
