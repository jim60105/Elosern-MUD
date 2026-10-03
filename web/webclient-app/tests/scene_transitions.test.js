// webclient-scene-transitions (design D7): the stage transitions with the
// real `<Transition>` (not the test-utils stub), so the leaving copies, their
// `inert` state, and the decode-first backdrop swap are observable. jsdom has
// no layout and no transition timing: a leave ends a couple of animation
// frames after it starts, which `frames()` waits out.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import MapLattice from "../components/MapLattice.vue";
import MessageWindow from "../components/MessageWindow.vue";
import PlaceCard from "../components/PlaceCard.vue";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import StageActor from "../components/StageActor.vue";
import StatusPanel from "../components/StatusPanel.vue";
import { ART_PANEL_SAMPLE, STATUS_PANEL_SAMPLE, localMapModelFor } from "../stories/fixtures.js";
import { stageJourneyLocalMap } from "../stories/fixtures/stage_journey.js";
import { toScreen } from "../lib/map_pan.js";

const REAL = { global: { stubs: { transition: false } } };

// Two animation frames and a macrotask: long enough for Vue to end a leave
// whose computed duration jsdom reports as zero.
async function frames() {
  await new Promise((resolve) => setTimeout(resolve, 60));
  await nextTick();
}

let wrapper = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

function artWith(url, overrides = {}) {
  return { ...ART_PANEL_SAMPLE, scene: { ...ART_PANEL_SAMPLE.scene, url, ...overrides } };
}

const images = (w) => w.findAll('[data-testid="scene-backdrop-image"]');

describe("SceneBackdrop crossfade", () => {
  function holdDecode() {
    const pending = [];
    vi.spyOn(HTMLImageElement.prototype, "decode").mockImplementation(function decode() {
      return new Promise((resolve, reject) => pending.push({ src: this.src, resolve, reject }));
    });
    return pending;
  }

  beforeEach(() => {
    if (!("decode" in HTMLImageElement.prototype)) {
      HTMLImageElement.prototype.decode = () => Promise.resolve();
    }
  });

  it("keeps the previous image, dimmed, until the next one is decoded, then crossfades", async () => {
    const pending = holdDecode();
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: artWith("/art/scene/a.png") } });
    // Mount shows its image at once, with no decode wait and no fade.
    expect(images(wrapper)).toHaveLength(1);
    expect(images(wrapper)[0].attributes("src")).toBe("/art/scene/a.png");

    await wrapper.setProps({ art: artWith("/art/scene/b.png", { label: "新場景", alt: "新的場景" }) });
    // The label and alt text switch at commit; the old bitmap stays, dimmed.
    expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("新場景");
    expect(wrapper.get('[data-testid="scene-backdrop-alt"]').text()).toBe("新的場景");
    expect(images(wrapper)).toHaveLength(1);
    expect(images(wrapper)[0].attributes("src")).toBe("/art/scene/a.png");
    expect(images(wrapper)[0].classes()).toContain("scene-backdrop__image--dimmed");
    expect(pending).toHaveLength(1);

    pending[0].resolve();
    await flushPromises();
    // Both layers while the fade runs: the leaving one is inert, the entering
    // one is the new scene and is not.
    const both = images(wrapper);
    expect(both).toHaveLength(2);
    const leaving = both.find((img) => img.attributes("src") === "/art/scene/a.png");
    const entering = both.find((img) => img.attributes("src") === "/art/scene/b.png");
    expect(leaving.element.inert).toBe(true);
    expect(entering.element.inert).toBe(false);
    expect(entering.classes()).not.toContain("scene-backdrop__image--dimmed");

    await frames();
    expect(images(wrapper)).toHaveLength(1);
    expect(images(wrapper)[0].attributes("src")).toBe("/art/scene/b.png");
  });

  it("a rejected decode records the failure: the old image goes, the placeholder shows, no refetch", async () => {
    const pending = holdDecode();
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: artWith("/art/scene/a.png") } });
    await wrapper.setProps({ art: artWith("/art/scene/broken.png") });
    pending[0].reject(new Error("EncodingError"));
    await flushPromises();
    // The broken URL is never rendered (a second fetch of a failed URL), and
    // the previous scene leaves rather than staying as if current.
    expect(images(wrapper).some((img) => img.attributes("src") === "/art/scene/broken.png")).toBe(false);
    expect(wrapper.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(true);
    await frames();
    expect(images(wrapper)).toHaveLength(0);
    // The same URL committed again is not decoded (fetched) again.
    await wrapper.setProps({ art: artWith("/art/scene/broken.png", { label: "再看一次" }) });
    await flushPromises();
    expect(pending).toHaveLength(1);
  });

  it("drops a decode that a newer scene overtook", async () => {
    const pending = holdDecode();
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: artWith("/art/scene/a.png") } });
    await wrapper.setProps({ art: artWith("/art/scene/b.png") });
    await wrapper.setProps({ art: artWith("/art/scene/c.png") });
    expect(pending.map((p) => p.src)).toEqual([
      expect.stringContaining("/art/scene/b.png"),
      expect.stringContaining("/art/scene/c.png"),
    ]);
    pending[0].resolve();
    await flushPromises();
    // b never shows: a is still up, dimmed, waiting for c.
    expect(images(wrapper)).toHaveLength(1);
    expect(images(wrapper)[0].attributes("src")).toBe("/art/scene/a.png");
    pending[1].resolve();
    await flushPromises();
    await frames();
    expect(images(wrapper).map((img) => img.attributes("src"))).toEqual(["/art/scene/c.png"]);
  });

  it("at the off level the swap leaves no second layer, even for a frame", async () => {
    const pending = holdDecode();
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: artWith("/art/scene/a.png"), motionLevel: "off" } });
    await wrapper.setProps({ art: artWith("/art/scene/b.png") });
    pending[0].resolve();
    await flushPromises();
    expect(images(wrapper).map((img) => img.attributes("src"))).toEqual(["/art/scene/b.png"]);
    expect(wrapper.find("[inert]").exists()).toBe(false);
  });
});

describe("PlaceCard location change", () => {
  const headings = (w) => w.findAll('[data-testid="place-card__location"]');

  it("the previous heading leaves inert while the new one enters", async () => {
    wrapper = mount(PlaceCard, { ...REAL, props: { locationLabel: "石板廣場", timeLabel: "春季 3 日 ‧ 12:00" } });
    await wrapper.setProps({ locationLabel: "北岸大道" });
    const both = headings(wrapper);
    expect(both).toHaveLength(2);
    const old = both.find((h) => h.text() === "石板廣場");
    const fresh = both.find((h) => h.text() === "北岸大道");
    expect(old.element.inert).toBe(true);
    expect(fresh.element.inert).toBe(false);
    await frames();
    expect(headings(wrapper).map((h) => h.text())).toEqual(["北岸大道"]);
  });

  it("a time-only change adds no leaving element", async () => {
    wrapper = mount(PlaceCard, { ...REAL, props: { locationLabel: "石板廣場", timeLabel: "春季 3 日 ‧ 12:00" } });
    await wrapper.setProps({ timeLabel: "春季 3 日 ‧ 12:05" });
    expect(headings(wrapper)).toHaveLength(1);
    expect(wrapper.find("[inert]").exists()).toBe(false);
    expect(wrapper.get('[data-testid="place-card__time"]').text()).toBe("春季 3 日 ‧ 12:05");
  });
});

describe("MessageWindow clear", () => {
  const fit = (fragments) => fragments.reduce((sum, f) => sum + (f.end - f.start), 0) <= 200;
  const lines = (entries) => entries.map(([kind, text], index) => ({ kind, text, seq: index + 1 }));
  const contents = (w) => w.findAll('[data-testid="message-content"]');

  it("a new response leaves the previous page as one inert layer and types the new one at once", async () => {
    const first = lines([["out", "渡口的霧。"]]);
    wrapper = mount(MessageWindow, { ...REAL, attachTo: document.body, props: { lines: first, pageFit: fit } });
    await flushPromises();
    await frames();
    const surface = wrapper.get('[data-testid="message-page"]');
    surface.element.focus();
    expect(contents(wrapper)).toHaveLength(1);

    await wrapper.setProps({ lines: [...first, { kind: "in", text: "look", seq: 2 }, { kind: "out", text: "你看見一座橋。", seq: 3 }] });
    await flushPromises();
    const both = contents(wrapper);
    expect(both).toHaveLength(2);
    const old = both.find((c) => c.text().includes("渡口的霧"));
    const fresh = both.find((c) => c.text().includes("你看見一座橋"));
    expect(old.element.inert).toBe(true);
    expect(old.element.querySelector("button, a, [tabindex]")).toBeNull();
    expect(fresh.element.inert).toBe(false);
    expect(wrapper.get('[data-testid="message-window"]').attributes("data-typing")).toBe("true");
    // The page surface is not keyed: it is the same element and keeps focus.
    expect(wrapper.get('[data-testid="message-page"]').element).toBe(surface.element);
    expect(document.activeElement).toBe(surface.element);

    await frames();
    expect(contents(wrapper)).toHaveLength(1);
    expect(contents(wrapper)[0].text()).toContain("你看見一座橋");
  });

  it("lines appended to the same response patch the page in place, with no clear", async () => {
    const first = lines([["out", "渡口的霧。"]]);
    wrapper = mount(MessageWindow, { ...REAL, attachTo: document.body, props: { lines: first, pageFit: fit } });
    await flushPromises();
    await frames();
    await wrapper.setProps({ lines: [...first, { kind: "out", text: "霧更濃了。", seq: 2 }] });
    await flushPromises();
    expect(contents(wrapper)).toHaveLength(1);
    expect(wrapper.find("[inert]").exists()).toBe(false);
  });
});

describe("StageActor portrait crossfade", () => {
  const PORTRAIT = { subject_key: "c", status: "done", url: "/art/defaults/man.webp", alt: "肖像", placeholder: null, face_rect: null };
  const artworks = (w) => w.findAll('[data-testid="reference-artwork"]');

  it("a new URL leaves one inert copy while the new portrait enters", async () => {
    wrapper = mount(StageActor, { ...REAL, props: { portrait: PORTRAIT, name: "艾莉亞" } });
    await wrapper.setProps({ portrait: { ...PORTRAIT, url: "/art/defaults/woman.webp" } });
    const both = artworks(wrapper);
    expect(both).toHaveLength(2);
    expect(both.filter((a) => a.element.inert)).toHaveLength(1);
    expect(both.find((a) => a.element.inert).find("img").attributes("src")).toBe("/art/defaults/man.webp");
    await frames();
    expect(artworks(wrapper)).toHaveLength(1);
  });

  it("a same-URL refresh keeps the portrait, with no fade", async () => {
    wrapper = mount(StageActor, { ...REAL, props: { portrait: PORTRAIT, name: "艾莉亞" } });
    await wrapper.setProps({ portrait: { ...PORTRAIT, alt: "新的描述" } });
    expect(artworks(wrapper)).toHaveLength(1);
    expect(wrapper.find("[inert]").exists()).toBe(false);
  });

  it("a switch from an image to a placeholder crossfades too", async () => {
    wrapper = mount(StageActor, { ...REAL, props: { portrait: PORTRAIT, name: "艾莉亞" } });
    await wrapper.setProps({ portrait: null });
    expect(artworks(wrapper)).toHaveLength(2);
    expect(wrapper.find('[data-testid="reference-artwork__placeholder"]').exists()).toBe(true);
  });
});

describe("StatusPanel reveal", () => {
  it("suppresses injured vitals during dialogue revisions and reuses the dock reveal on exit", async () => {
    setActivePinia(createPinia());
    const store = useElosernStore();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    let revision = 0;
    const commit = (mode, hp = 80) => {
      expect(store.receive(1, "ui_snapshot", [fx.snapshot({
        revision: ++revision, mode,
        panels: { status: fx.statusPanel({ resources: { hp: { current: hp, maximum: 100 } } }) },
      })], {}).accepted).toBe(true);
    };
    commit("exploration");
    wrapper = mount(AppClient, REAL);
    const panel = () => wrapper.getComponent(StatusPanel);
    expect(panel().props("visible")).toBe(true);
    commit("dialogue");
    await nextTick();
    expect(panel().props("visible")).toBe(false);
    await frames();
    expect(panel().get('[data-testid="status-panel"]').element.style.display).toBe("none");
    commit("dialogue", 70);
    await nextTick();
    expect(panel().props("visible")).toBe(false);
    expect(panel().get('[data-testid="status-panel"]').classes()).not.toContain("vitals-reveal-enter-active");
    commit("exploration", 70);
    await nextTick();
    expect(panel().props("visible")).toBe(true);
    const dock = panel().get('[data-testid="status-panel"]');
    expect(dock.element.style.display).not.toBe("none");
    expect(dock.classes()).toContain("vitals-reveal-enter-active");
    expect(dock.classes()).toContain("vitals-reveal-enter-from");
    await frames();
  });
  it("is inert while it leaves, and in reach again the moment it is shown mid-leave", async () => {
    wrapper = mount(StatusPanel, { ...REAL, props: { status: STATUS_PANEL_SAMPLE, visible: true } });
    const panel = () => wrapper.get('[data-testid="status-panel"]').element;
    await wrapper.setProps({ visible: false });
    expect(panel().inert).toBe(true);
    await wrapper.setProps({ visible: true });
    expect(panel().inert).toBe(false);
    expect(panel().style.display).not.toBe("none");
  });

  it("reaches display:none once its exit ends, and stays mounted", async () => {
    wrapper = mount(StatusPanel, { ...REAL, props: { status: STATUS_PANEL_SAMPLE, visible: true } });
    await wrapper.setProps({ visible: false });
    await frames();
    const panel = wrapper.get('[data-testid="status-panel"]').element;
    expect(panel.style.display).toBe("none");
    expect(panel.inert).toBe(false);
  });

  it("at the off level it hides in the commit's patch", async () => {
    wrapper = mount(StatusPanel, { ...REAL, props: { status: STATUS_PANEL_SAMPLE, visible: true, motionLevel: "off" } });
    await wrapper.setProps({ visible: false });
    expect(wrapper.get('[data-testid="status-panel"]').element.style.display).toBe("none");
  });
});

describe("MapLattice pan", () => {
  // jsdom has no layout: give the canvas its 208px CSS box.
  beforeEach(() => {
    vi.spyOn(SVGElement.prototype, "getBoundingClientRect").mockReturnValue({
      x: 0, y: 0, top: 0, left: 0, right: 208, bottom: 208, width: 208, height: 208,
    });
  });

  const ISLAND = { canvasSize: 208, colPitch: 40, rowPitch: 40, labelFont: 12, showAxis: true };
  const groups = (w) => w.findAll(".map-lattice__pan").map((g) => g.element);

  // Every `--pan-*` / `--glide-*` write, with the declaration it went to
  // (jsdom's getComputedStyle copies declarations through setProperty too).
  function recordWrites() {
    const writes = [];
    const original = CSSStyleDeclaration.prototype.setProperty;
    vi.spyOn(CSSStyleDeclaration.prototype, "setProperty").mockImplementation(function record(name, value, priority) {
      if (/^--(pan|glide)-/.test(name)) writes.push({ style: this, name, value });
      return original.call(this, name, value, priority);
    });
    return writes;
  }

  function translateOf(w, id) {
    const match = w.get(`[data-node="${id}"]`).attributes("transform").match(/translate\(([-\d.]+),\s*([-\d.]+)\)/);
    return { x: Number(match[1]), y: Number(match[2]) };
  }

  function viewBoxOf(w) {
    const [x, y, width, height] = w.get("svg").attributes("viewBox").split(/\s+/).map(Number);
    return { x, y, width, height };
  }

  it("the current marker starts on the node the player left and is released to rest", async () => {
    wrapper = mount(MapLattice, {
      props: { localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:0")), panOnMove: true, ...ISLAND },
    });
    const writes = recordWrites();
    await wrapper.setProps({ localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:1")) });
    await flushPromises();
    const marker = wrapper.get(".local-map__marker--current").element;
    const from = translateOf(wrapper, "grid:altoria:1:0");
    const to = translateOf(wrapper, "grid:altoria:1:1");
    const own = (name) => writes.filter((w) => w.style === marker.style && w.name === name).map((w) => w.value);
    // Starts exactly one step back (on the node left behind), then released.
    expect(own("--glide-x")).toEqual([`${from.x - to.x}px`, "0px"]);
    expect(own("--glide-y")).toEqual([`${from.y - to.y}px`, "0px"]);
    expect(from.y - to.y).toBeGreaterThan(0);
    // This drawing does not move between the two placements: no pan.
    expect(writes.filter((w) => w.name.startsWith("--pan-") && w.value !== "0px")).toEqual([]);
    // Nodes and their accessible hooks carry the new placement at commit.
    expect(wrapper.get('[data-node="grid:altoria:1:1"]').attributes("data-visibility")).toBe("current");
    expect(groups(wrapper)).toHaveLength(2);
  });

  it("a recentring placement pans the drawing from the node the player left, then releases it", async () => {
    const graph = (id) => localMapModelFor({ ...stageJourneyLocalMap(id), layer: "interior" });
    wrapper = mount(MapLattice, {
      props: { localMap: graph("grid:altoria:1:0"), variant: "graph", panOnMove: true, ...ISLAND },
    });
    const before = translateOf(wrapper, "grid:altoria:1:0");
    const vbBefore = viewBoxOf(wrapper);
    const writes = recordWrites();
    await wrapper.setProps({ localMap: graph("grid:altoria:1:1") });
    await flushPromises();
    const [first] = groups(wrapper);
    const own = (name) => writes.filter((w) => w.style === first.style && w.name === name).map((w) => w.value);
    const after = translateOf(wrapper, "grid:altoria:1:0");
    const startX = Number.parseFloat(own("--pan-x")[0]);
    const startY = Number.parseFloat(own("--pan-y")[0]);
    // On the first frame the node the player left is on the screen point
    // where it stood, whatever the new placement and viewBox.
    const size = { width: 208, height: 208 };
    const was = toScreen({ viewBox: vbBefore, size }, before);
    const is = toScreen({ viewBox: viewBoxOf(wrapper), size }, { x: after.x + startX, y: after.y + startY });
    expect(is.x).toBeCloseTo(was.x, 6);
    expect(is.y).toBeCloseTo(was.y, 6);
    expect(Math.hypot(startX, startY)).toBeGreaterThan(1);
    expect(own("--pan-x").at(-1)).toBe("0px");
    expect(own("--pan-y").at(-1)).toBe("0px");
  });

  it("without panOnMove (the full map) nothing moves", async () => {
    wrapper = mount(MapLattice, {
      props: { localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:0")), ...ISLAND },
    });
    const writes = recordWrites();
    await wrapper.setProps({ localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:1")) });
    await flushPromises();
    expect(writes).toEqual([]);
  });

  it("at the off level nothing moves", async () => {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:0")),
        panOnMove: true,
        motionLevel: "off",
        ...ISLAND,
      },
    });
    const writes = recordWrites();
    await wrapper.setProps({ localMap: localMapModelFor(stageJourneyLocalMap("grid:altoria:1:1")) });
    await flushPromises();
    expect(writes).toEqual([]);
  });
});
