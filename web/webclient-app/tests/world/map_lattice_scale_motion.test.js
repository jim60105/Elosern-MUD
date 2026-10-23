// Scale-aware island motion (animate-minimap-scale-transitions; approved
// minimap auto-scale design §6.5): the minimap island pans only while its
// projection keeps one mode and level — the world-anchored dot field riding
// the pan with the routes and nodes — and a changed mode or level dissolves
// at full motion and switches at once at reduced/off, with no equal-scale
// FLIP, no lingering previous frame and no leaving copy a test, an assistive
// technology or a pointer could mistake for the live drawing.
//
// Mounted through LocalMap, so the island receives the production projection
// with its hysteresis memory. jsdom lays nothing out, so the canvas reports
// the island's 240px square, and the motion tokens the stylesheet resolves in
// the browser are set inline on the document root.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import LocalMap from "../../components/LocalMap.vue";
import { previousLevelFor, projectIsland, rememberLevel } from "../../lib/minimap_projection.js";
import { scaleKey } from "../../lib/map_pan.js";
import {
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_MOVE_COMPRESSION,
  LOCAL_MAP_MOVE_LADDER,
  LOCAL_MAP_MOVE_SAME_SCALE,
  LOCAL_MAP_WILDERNESS_RETURN_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

const TOKENS = {
  full: { "--motion-base": "300ms", "--motion-travel": "1" },
  reduced: { "--motion-base": "0ms", "--motion-travel": "0" },
  off: { "--motion-base": "0ms", "--motion-travel": "0" },
};

function setLevel(level) {
  const root = document.documentElement;
  root.dataset.motion = level;
  for (const [name, value] of Object.entries(TOKENS[level])) root.style.setProperty(name, value);
}

// Every value written to a `--pan-*` / `--glide-*` variable, per element.
let panWrites;
let wrapper;

beforeEach(() => {
  panWrites = [];
  const setProperty = CSSStyleDeclaration.prototype.setProperty;
  vi.spyOn(CSSStyleDeclaration.prototype, "setProperty").mockImplementation(function record(name, value, priority) {
    if (/^--(pan|glide)-[xy]$/.test(name)) panWrites.push({ style: this, name, value });
    return setProperty.call(this, name, value, priority);
  });
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(() => ({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: 240,
    bottom: 240,
    width: 240,
    height: 240,
  }));
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  vi.useRealTimers();
  vi.restoreAllMocks();
  const root = document.documentElement;
  delete root.dataset.motion;
  root.removeAttribute("style");
  document.body.innerHTML = "";
});

function mountIsland(payload, level) {
  setLevel(level);
  wrapper = mount(LocalMap, {
    attachTo: document.body,
    props: { localMap: localMapModelFor(payload), motionLevel: level },
  });
  return wrapper;
}

async function commit(payload) {
  await wrapper.setProps({ localMap: localMapModelFor(payload) });
  await nextTick();
}

const host = () => wrapper.get('[data-testid="local-map__leaving-host"]').element;
const copies = () => [...host().children];
const liveSvg = () => wrapper.get('[data-testid="local-map__lattice"]').element;
const currentId = () => wrapper.get('.local-map__node[data-visibility="current"]').attributes("data-node");
const nonZeroPan = () => panWrites.filter((write) => write.value !== "0px");
// The same writes as plain text, for readable equality failures.
const panStrings = () => nonZeroPan().map(({ name, value }) => `${name}=${value}`);
const frames = (n) =>
  new Promise((resolve) => {
    const step = (left) => (left === 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
    step(n);
  });

function dots() {
  return wrapper.findAll('[data-testid="local-map__dot-field"] circle').map((dot) => ({
    x: Number(dot.attributes("cx")),
    y: Number(dot.attributes("cy")),
  }));
}

// The projection the island holds after `from` then `to`, hysteresis included.
function projectedStep(from, to) {
  const a = localMapModelFor(from);
  const b = localMapModelFor(to);
  const first = projectIsland(a, null);
  return { first, second: projectIsland(b, previousLevelFor(rememberLevel(a.currentNode, first), b.currentNode)) };
}

function onLattice(value, offset, spacing) {
  const k = (value - offset) / spacing;
  return Math.abs(k - Math.round(k)) < 1e-6;
}

describe("island movement at an unchanged mode and level", () => {
  it("pans the ground: the dot field moves with the routes and nodes, then rests on world multiples", async () => {
    const { first, second } = projectedStep(LOCAL_MAP_MOVE_SAME_SCALE.from, LOCAL_MAP_MOVE_SAME_SCALE.to);
    expect(scaleKey(first)).toBe(scaleKey(second));
    mountIsland(LOCAL_MAP_MOVE_SAME_SCALE.from, "full");
    const before = dots();
    panWrites.length = 0;
    await commit(LOCAL_MAP_MOVE_SAME_SCALE.to);

    expect(currentId()).toBe(LOCAL_MAP_MOVE_SAME_SCALE.to.current_node);
    // The FLIP offset was written to every pan group — the dot field
    // included — and then released.
    const field = wrapper.get('[data-testid="map-lattice__pan--field"]').element;
    const lines = wrapper.get('[data-testid="map-lattice__pan--lines"]').element;
    const nodes = wrapper.get('[data-testid="map-lattice__pan--nodes"]').element;
    expect(field.contains(wrapper.get('[data-testid="local-map__dot-field"]').element)).toBe(true);
    const start = (el) => nonZeroPan().filter((write) => write.style === el.style);
    for (const el of [field, lines, nodes]) expect(start(el).length).toBeGreaterThan(0);
    const dx = Number.parseFloat(start(field).find((w) => w.name === "--pan-x").value);
    const dy = Number.parseFloat(start(field).find((w) => w.name === "--pan-y")?.value ?? "0");
    // The field and the drawing share one offset: one rigid shape.
    expect(Number.parseFloat(start(lines).find((w) => w.name === "--pan-x").value)).toBeCloseTo(dx, 6);
    for (const el of [field, lines, nodes]) {
      expect(el.style.getPropertyValue("--pan-x")).toBe("0px");
      expect(el.style.getPropertyValue("--pan-y")).toBe("0px");
    }

    // Continuity: at the start of the pan, the new world-anchored dots stand
    // on the old lattice, so the ground does not jump under the player.
    const { spacing } = second.grid;
    for (const dot of dots()) {
      expect(onLattice(dot.x + dx, first.grid.offsetX, spacing)).toBe(true);
      expect(onLattice(dot.y + dy, first.grid.offsetY, spacing)).toBe(true);
    }
    // At rest the dots sit on the new projection's own world multiples.
    for (const dot of dots()) {
      expect(onLattice(dot.x, second.grid.offsetX, spacing)).toBe(true);
      expect(onLattice(dot.y, second.grid.offsetY, spacing)).toBe(true);
    }
    expect(before.length).toBeGreaterThan(0);
    // No dissolve on an equal-scale step.
    expect(copies()).toHaveLength(0);
  });

  it("keeps the same-level compressed pan with its rings centred and still", async () => {
    // A replacement that keeps the compressed mode and level and moves no ring.
    const from = LOCAL_MAP_MOVE_COMPRESSION.from;
    mountIsland(from, "full");
    const rings = () => wrapper.findAll(".local-map__ring").map((ring) => [ring.attributes("cx"), ring.attributes("cy")]);
    expect(rings().length).toBeGreaterThan(0);
    await commit({ ...from, title: "邊境驛站（換頁）" });
    expect(copies()).toHaveLength(0);
    expect(wrapper.get('[data-testid="local-map__rings"]').element.closest(".map-lattice__pan")).toBeNull();
    for (const [cx, cy] of rings()) expect([cx, cy]).toEqual(["120", "120"]);
  });
});

describe("island movement across a changed mode or level", () => {
  it("dissolves an inert copy of the previous drawing at full motion, never panning", async () => {
    const { first, second } = projectedStep(LOCAL_MAP_MOVE_LADDER.from, LOCAL_MAP_MOVE_LADDER.to);
    expect(scaleKey(first)).toBe("uniform:1500");
    expect(scaleKey(second)).toBe("uniform:2000");
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    panWrites.length = 0;
    await commit(LOCAL_MAP_MOVE_LADDER.to);

    // The committed drawing is already the new projection.
    expect(currentId()).toBe(LOCAL_MAP_MOVE_LADDER.to.current_node);
    expect(wrapper.get('[data-testid="local-map__scale"]').text()).toBe("格距 400 m");
    // No equal-scale FLIP and no marker glide.
    expect(panStrings()).toEqual([]);

    const [copy] = copies();
    expect(copies()).toHaveLength(1);
    expect(host().getAttribute("aria-hidden")).toBe("true");
    expect(host().hasAttribute("inert")).toBe(true);
    expect(copy.hasAttribute("inert")).toBe(true);
    expect(copy.getAttribute("aria-hidden")).toBe("true");
    expect(copy.getAttribute("data-testid")).toBe("local-map__leaving");
    expect(copy.classList.contains("local-map__lattice--leaving")).toBe(true);
    expect(copy.style.animationDuration).toBe("300ms");
    // It is the previous drawing: the old 格距 300 m dots, the old current.
    expect(copy.querySelector(".local-map__marker--current")).not.toBeNull();
    // No identity a selector, an assistive technology or a pointer could take
    // for the live drawing, and no control at all.
    expect(copy.querySelectorAll("[data-testid], [data-node], [data-node-id], [role], [tabindex], [aria-label], title")).toHaveLength(0);
    expect(host().querySelector("button, a, [tabindex]")).toBeNull();
    expect(document.querySelectorAll('[data-testid="local-map__lattice"]')).toHaveLength(1);
    // Every id is unique in the document and every paint reference in the
    // copy points at the copy's own defs (the old fog, never the new one).
    const ids = [...document.querySelectorAll("[id]")].map((el) => el.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const el of copy.querySelectorAll("[fill^='url(']")) {
      const id = el.getAttribute("fill").match(/#([^)'"]+)/)[1];
      expect(copy.querySelector(`[id="${id}"]`)).not.toBeNull();
    }
    // The live drawing keeps its own identity and stays fully visible.
    expect(liveSvg().style.opacity).toBe("");

    // The fade's own end (or its token-derived fallback) removes the copy.
    vi.advanceTimersByTime(299);
    expect(copies()).toHaveLength(1);
    vi.advanceTimersByTime(200);
    expect(copies()).toHaveLength(0);
  });

  it("removes the copy on its own animationend, ignoring a child's", async () => {
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    const [copy] = copies();
    copy.querySelector("circle").dispatchEvent(new Event("animationend", { bubbles: true }));
    expect(copies()).toHaveLength(1);
    copy.dispatchEvent(new Event("animationend"));
    expect(copies()).toHaveLength(0);
  });

  it("dissolves a compressed-to-uniform switch from the rings to the dot field", async () => {
    mountIsland(LOCAL_MAP_MOVE_COMPRESSION.from, "full");
    await commit(LOCAL_MAP_MOVE_COMPRESSION.to);
    const [copy] = copies();
    expect(copy.querySelector(".local-map__rings")).not.toBeNull();
    expect(wrapper.find('[data-testid="local-map__rings"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map__dot-field"]').exists()).toBe(true);
    expect(panStrings()).toEqual([]);
  });

  for (const level of ["reduced", "off"]) {
    it(`switches at once at ${level}: no copy and no pan through a double animation frame`, async () => {
      mountIsland(LOCAL_MAP_MOVE_LADDER.from, level);
      panWrites.length = 0;
      await commit(LOCAL_MAP_MOVE_LADDER.to);
      expect(currentId()).toBe(LOCAL_MAP_MOVE_LADDER.to.current_node);
      expect(copies()).toHaveLength(0);
      await frames(2);
      expect(copies()).toHaveLength(0);
      expect(panWrites.map(({ name, value }) => `${name}=${value}`)).toEqual([]);
      for (const el of wrapper.findAll(".map-lattice__pan")) {
        expect(el.element.style.getPropertyValue("--pan-x")).toBe("");
      }
    });
  }

  it("drops a fading copy in the commit frame when a reduced scale switch follows", async () => {
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    expect(copies()).toHaveLength(1);
    setLevel("reduced");
    await wrapper.setProps({ localMap: localMapModelFor(LOCAL_MAP_MOVE_COMPRESSION.from), motionLevel: "reduced" });
    expect(copies()).toHaveLength(0);
  });

  it("drops a fading copy as soon as the effective level leaves full", async () => {
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    expect(copies()).toHaveLength(1);
    await wrapper.setProps({ motionLevel: "off" });
    expect(copies()).toHaveLength(0);
  });

  it("compares the scale on a replacement that keeps the current node", async () => {
    // The same street, re-committed with its exits twice as far away.
    const from = LOCAL_MAP_MOVE_LADDER.from;
    const current = from.nodes.find((node) => node.id === from.current_node);
    const farther = {
      ...from,
      nodes: from.nodes.map((node) =>
        node.id === from.current_node || node.visibility === "remembered"
          ? node
          : { ...node, x: current.x + 2 * (node.x - current.x), y: current.y + 2 * (node.y - current.y) },
      ),
    };
    farther.nodes = farther.nodes.map((node) => ({
      ...node,
      id: node.id === from.current_node ? node.id : `${node.id}:far`,
      action: node.action ? { ...node.action, destination: `${node.id}:far` } : null,
    }));
    farther.edges = from.edges.map((edge) => ({ ...edge, destination: `${edge.destination}:far` }));
    mountIsland(from, "full");
    await commit(farther);
    expect(currentId()).toBe(from.current_node);
    expect(copies()).toHaveLength(1);
  });

  it("chains an interrupted sequence: older copies fade above newer ones, all settle on the latest", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    const [older] = copies();
    vi.advanceTimersByTime(150);
    await commit(LOCAL_MAP_MOVE_COMPRESSION.from);
    expect(copies()).toHaveLength(2);
    expect(copies()[1]).toBe(older);
    expect(currentId()).toBe(LOCAL_MAP_MOVE_COMPRESSION.from.current_node);
    vi.advanceTimersByTime(1000);
    expect(copies()).toHaveLength(0);
  });

  it("settles a pan still in flight when a scale change follows within one beat", async () => {
    mountIsland(LOCAL_MAP_MOVE_SAME_SCALE.from, "full");
    await commit(LOCAL_MAP_MOVE_SAME_SCALE.to);
    const field = wrapper.get('[data-testid="map-lattice__pan--field"]').element;
    // Mid-pan: the field still carries an offset (as a running transition would).
    field.style.setProperty("--pan-x", "17px");
    panWrites.length = 0;
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    expect(copies()).toHaveLength(1);
    // The new-scale drawing does not keep easing the old-scale offset: the
    // live groups rest at 0 with their transition restored (only the frozen
    // copy keeps the mid-pan offset), and no new FLIP offset was computed.
    expect(copies()[0].querySelector(".map-lattice__pan").style.transition).toBe("none");
    for (const el of liveSvg().querySelectorAll(".map-lattice__pan")) {
      expect(el.style.getPropertyValue("--pan-x")).toBe("0px");
      expect(el.style.transition).toBe("");
    }
  });

  it("keeps at most three fading copies, dropping the oldest", async () => {
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    // uniform:2000 → compressed:1500 → uniform:1500 → uniform:2000: four changes.
    const sequence = [LOCAL_MAP_MOVE_LADDER.to, LOCAL_MAP_MOVE_COMPRESSION.from, LOCAL_MAP_MOVE_COMPRESSION.to, LOCAL_MAP_MOVE_LADDER.to];
    const seen = [];
    for (const payload of sequence) {
      await commit(payload);
      seen.push(copies()[0]);
    }
    expect(copies()).toHaveLength(3);
    const order = copies().map((copy) => seen.indexOf(copy));
    expect(order).toEqual([3, 2, 1]);
    expect(seen[0].isConnected).toBe(false);
  });

  it("clears every copy and timer on unmount", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    mountIsland(LOCAL_MAP_MOVE_LADDER.from, "full");
    await commit(LOCAL_MAP_MOVE_LADDER.to);
    const [copy] = copies();
    wrapper.unmount();
    wrapper = null;
    expect(copy.isConnected).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("island movement without a shared scale", () => {
  it("never dissolves the first island after a coordinate-free layer, and keeps it still", async () => {
    mountIsland(LOCAL_MAP_INTERIOR_SAMPLE, "full");
    expect(wrapper.find('[data-testid="local-map__leaving-host"]').exists()).toBe(false);
    panWrites.length = 0;
    await commit(LOCAL_MAP_MOVE_LADDER.from);
    expect(copies()).toHaveLength(0);
    // The previous node is not in the new drawing: the existing immediate
    // no-shared-frame placement.
    expect(panStrings()).toEqual([]);
  });

  it("crosses a gateway by the approved mode/level decision, never synthesising a shared frame", async () => {
    const { first, second } = projectedStep(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE, LOCAL_MAP_WILDERNESS_RETURN_SAMPLE);
    const changed = scaleKey(first) !== scaleKey(second);
    for (const level of ["full", "reduced"]) {
      mountIsland(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE, level);
      panWrites.length = 0;
      await commit(LOCAL_MAP_WILDERNESS_RETURN_SAMPLE);
      expect(currentId()).toBe(LOCAL_MAP_WILDERNESS_RETURN_SAMPLE.current_node);
      expect(copies()).toHaveLength(changed && level === "full" ? 1 : 0);
      // The gate room is not on the wilderness island: no FLIP offset.
      expect(panStrings()).toEqual([]);
      wrapper.unmount();
      wrapper = null;
    }
  });

  it("leaves the radial graph's pan path untouched (no dissolve host)", () => {
    mountIsland(LOCAL_MAP_INTERIOR_SAMPLE, "full");
    expect(wrapper.find('[data-testid="local-map__leaving-host"]').exists()).toBe(false);
  });
});
