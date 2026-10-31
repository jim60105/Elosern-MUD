// WorldMapView (OpenSpec change render-world-map-view). The four top-level
// describe blocks map one-to-one to the webclient-world-map-view
// requirements; tests/test_map_client_contracts.py WorldViewContracts checks
// that each block ran and passed. Fixtures are the synthetic bodies in
// stories/fixtures/world_map.js, validated by the wire validator first.

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import WorldMapView from "../../components/WorldMapView.vue";
import {
  APPROXIMATE_RADIUS_KM,
  NAME_MAX_SPAN_KM,
  NATION_MIN_SPAN_KM,
  TRAIL_CELL_MAX_SPAN_KM,
  UNLIT_LABEL_MAX_SPAN_KM,
  featureDetail,
  insideOutline,
  labelCandidates,
  lodFor,
  placeWorldLabels,
  revealTransitions,
  trailGridKm,
  trailLinePath,
} from "../../lib/world_map_view.js";
import MapPanels from "../../../static/webclient/js/elosern/protocol/panels/map_panels.js";
import {
  FOREST_ID,
  FOREST_LANDMARK,
  FOREST_NATION_IDS,
  NATIONS,
  PLACE_IDS,
  PLAYER,
  QUEST_IDS,
  newLight,
  worldBase,
  worldCoarseTrail,
  worldForestLit,
  worldMap,
  worldNewLight,
  worldUnexplored,
} from "../../stories/fixtures/world_map.js";

const { validateWorldMapPanel } = MapPanels;
const SIGNATURE = "world|elosern|km";
const FRAME = { width: 960, height: 600 }; // the component's provisional frame in jsdom

// This suite mounts the whole world map and drives real commits, so an
// individual test can exceed Vitest's default budget on a shared runner (the
// evennia evidence job runs this file inside a worker alongside four parallel
// suites): the file carries the same explicit headroom the project's other
// mount-heavy suites use.
vi.setConfig({ testTimeout: 20000 });

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
  document.documentElement.style.removeProperty("--motion-district-reveal");
});

function mountMap(world, props = {}) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const w = mount(WorldMapView, { props: { world: validateWorldMapPanel(world), ...props }, attachTo: host });
  wrappers.push(w);
  return w;
}

const viewAt = (span, centre = PLAYER) => ({ signature: SIGNATURE, cx: centre.x, cy: centre.y, span });
const labelsOf = (w) => w.findAll('[data-testid="world-map__label"]');
const kindsOf = (w) => new Set(labelsOf(w).map((l) => l.attributes("data-kind")));
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

async function pick(w, key) {
  const el = w.find(`[data-pick="${key}"]`);
  await el.trigger("pointerdown", { button: 0, clientX: 10, clientY: 10 });
  await el.trigger("pointerup", { button: 0, clientX: 10, clientY: 10 });
}

const LAYERS = [
  "sea", "land", "lit-terrain", "unlit-hatching", "district-borders", "national-borders", "coastline",
  "trail", "approximate-quests", "places-landmarks", "quest-markers", "current", "labels", "chrome",
];

describe("world layers render in the approved exploration order", () => {
  it("every story fixture is a schema-valid world_map body", () => {
    for (const body of [worldBase(), worldCoarseTrail(), worldForestLit(), worldNewLight(), worldUnexplored()]) {
      expect(() => validateWorldMapPanel(body)).not.toThrow();
    }
  });

  it("draws exactly the approved layers in order", () => {
    const w = mountMap(worldBase());
    const order = [...w.find('[data-testid="world-map__svg"]').element.children]
      .map((el) => el.getAttribute("data-layer"))
      .filter(Boolean);
    expect(order).toEqual(LAYERS);
  });

  it("unlit geometry is hatching, a dotted border and 未探明, with no invented contents", () => {
    const world = worldBase();
    const w = mountMap(world, { view: viewAt(400, { x: 1300, y: 1380 }) });
    const unlitIds = world.districts.filter((d) => !d.lit).map((d) => d.id);
    // Hatching is masked by the unlit outlines only.
    expect(w.find('[data-testid="world-map__hatch"]').attributes("mask")).toMatch(/-unlit\)$/);
    for (const id of unlitIds) {
      const border = w.find(`[data-testid="world-map__district"][data-district="${id}"]`);
      expect(border.classes()).toContain("is-unlit");
      expect(border.attributes("data-lit")).toBe("false");
      // No landmark, terrain or place is drawn or hit-testable for it.
      expect(w.find(`[data-testid="world-map__landmark"][data-pick="district:${id}"]`).exists()).toBe(false);
      expect(w.find(`.world-map__lit[data-district="${id}"]`).exists()).toBe(false);
    }
    const unlitLabels = labelsOf(w).filter((l) => l.attributes("data-kind") === "unlit");
    expect(unlitLabels.length).toBeGreaterThan(0);
    for (const label of unlitLabels) expect(label.text()).toBe("未探明");
    // The undisclosed name of a neighbour that lights later is nowhere.
    const hidden = newLight();
    expect(w.html()).not.toContain(hidden.name);
    expect(w.html()).not.toContain(hidden.landmark.name);
    // Lit districts differ by solid border and terrain ink.
    const litId = world.districts.find((d) => d.lit).id;
    expect(w.find(`[data-testid="world-map__district"][data-district="${litId}"]`).classes()).toContain("is-lit");
    expect(w.find(`.world-map__lit[data-district="${litId}"]`).exists()).toBe(true);
  });

  it("an all-unlit history draws only the common layer, hatching and the trail", () => {
    const w = mountMap(worldUnexplored(), { view: viewAt(420, { x: 1300, y: 1380 }) });
    expect(w.findAll(".world-map__lit")).toHaveLength(0);
    expect(w.findAll('[data-testid="world-map__landmark"]')).toHaveLength(0);
    expect(w.findAll('[data-testid="world-map__place"]')).toHaveLength(0);
    expect(new Set(labelsOf(w).map((l) => l.text()).filter((t) => !t.includes("大致方位")))).toEqual(new Set(["未探明"]));
  });

  it("an approximate commission is a dashed circle labelled 大致方位 with no exact point", () => {
    const world = worldBase();
    const marker = world.quest_markers.find((m) => m.id === QUEST_IDS.nearApproximate);
    expect(marker.approximate).toBe(true);
    const centre = { x: 1230, y: 1330 };
    const w = mountMap(world, { view: viewAt(420, centre) });
    const ring = w.find(`[data-testid="world-map__approx"][data-quest="${marker.id}"] .world-map__approx-ring`);
    expect(ring.exists()).toBe(true);
    const k = FRAME.width / 420;
    // Centred on the supplied 50 km grid point, never a derived exact one.
    expect(Number(ring.attributes("cx"))).toBeCloseTo(FRAME.width / 2 + (marker.x - centre.x) * k, 6);
    expect(Number(ring.attributes("cy"))).toBeCloseTo(FRAME.height / 2 - (marker.y - centre.y) * k, 6);
    expect(Number(ring.attributes("r"))).toBeCloseTo(APPROXIMATE_RADIUS_KM * k, 6);
    expect(w.find(`[data-testid="world-map__quest"][data-quest="${marker.id}"]`).exists()).toBe(false);
    const label = labelsOf(w).find((l) => l.attributes("data-label-for") === `quest:${marker.id}`);
    expect(label.text()).toContain("大致方位");
    // An exact commission is a pin, not a circle.
    const exact = w.find(`[data-testid="world-map__quest"][data-quest="${QUEST_IDS.exact}"]`);
    expect(exact.exists()).toBe(true);
    expect(w.find(`[data-testid="world-map__approx"][data-quest="${QUEST_IDS.exact}"]`).exists()).toBe(false);
  });

  it("draws the supplied national borders only (none inside the forest)", () => {
    const world = worldForestLit();
    const w = mountMap(world);
    const d = w.find('[data-testid="world-map__nation-border"]').attributes("d");
    const points = [...d.matchAll(/(-?[\d.]+) (-?[\d.]+)/g)].map((m) => [Number(m[1]), Number(m[2])]);
    expect(points.length).toBe(world.common.borders.flat().length);
    // The borders stop at the forest's edge: at most their end points touch it.
    const forest = world.districts.find((district) => district.id === FOREST_ID);
    const inside = points.filter(([x, y]) => insideOutline(forest.outline, { x, y }));
    expect(inside.length).toBeLessThanOrEqual(world.common.borders.length);
  });
});

describe("world map detail follows zoom thresholds without shrinking text", () => {
  it("the thresholds are inclusive", () => {
    expect(lodFor(NAME_MAX_SPAN_KM).names).toBe(true);
    expect(lodFor(NAME_MAX_SPAN_KM + 1e-6).names).toBe(false);
    expect(lodFor(UNLIT_LABEL_MAX_SPAN_KM).unlit).toBe(true);
    expect(lodFor(UNLIT_LABEL_MAX_SPAN_KM + 1e-6).unlit).toBe(false);
    expect(NAME_MAX_SPAN_KM).toBe(1000);
    expect(UNLIT_LABEL_MAX_SPAN_KM).toBe(450);
    // Nations: 大陸 and 國 (spans from the 國/地區 log midpoint, 400 km, up).
    expect(NATION_MIN_SPAN_KM).toBeCloseTo(400, 9);
    expect(lodFor(800).nations).toBe(true);
    expect(lodFor(400).nations).toBe(true);
    expect(lodFor(399.99).nations).toBe(false);
    expect(lodFor(200).nations).toBe(false);
    // The trail is cells only at 近郊.
    expect(lodFor(40).trailCells).toBe(true);
    expect(lodFor(TRAIL_CELL_MAX_SPAN_KM).trailCells).toBe(true);
    expect(lodFor(TRAIL_CELL_MAX_SPAN_KM + 1e-6).trailCells).toBe(false);
  });

  it("names appear at and below their threshold and vanish above it, never below 16px", async () => {
    const world = worldBase();
    const centre = { x: 900, y: 1120 };
    const w = mountMap(world, { view: viewAt(1000, centre) });
    expect(kindsOf(w).has("district")).toBe(true);
    expect(kindsOf(w).has("place")).toBe(true);
    for (const label of labelsOf(w)) expect(Number.parseFloat(label.attributes("style").replace(/[^\d.]/g, ""))).toBeGreaterThanOrEqual(16);
    await w.setProps({ view: viewAt(1000.5, centre) });
    expect(kindsOf(w).has("district")).toBe(false);
    expect(kindsOf(w).has("place")).toBe(false);
    expect(kindsOf(w).has("nation")).toBe(true);

    const frontier = { x: 1300, y: 1380 };
    await w.setProps({ view: viewAt(450, frontier) });
    expect(kindsOf(w).has("unlit")).toBe(true);
    await w.setProps({ view: viewAt(450.5, frontier) });
    expect(kindsOf(w).has("unlit")).toBe(false);
    for (const label of labelsOf(w)) expect(Number.parseFloat(label.attributes("style").replace(/[^\d.]/g, ""))).toBeGreaterThanOrEqual(16);
  });

  it("labels scale with the UI and still never overlap", async () => {
    document.documentElement.style.setProperty("--ui-scale", "1.25");
    try {
      const w = mountMap(worldBase(), { view: viewAt(800, { x: 1100, y: 1250 }) });
      await w.vm.$nextTick();
      const labels = labelsOf(w);
      expect(labels.length).toBeGreaterThan(0);
      for (const label of labels) {
        const style = label.attributes("style");
        const size = Number.parseFloat(/font-size:\s*([\d.]+)px/.exec(style)[1]);
        expect(size).toBeCloseTo(label.attributes("data-kind") === "nation" ? 25 : 20, 6);
        const halo = Number.parseFloat(/stroke-width:\s*([\d.]+)px/.exec(style)[1]);
        expect(halo).toBeCloseTo(size * 0.28, 6);
      }
      const candidates = labelCandidates(worldBase(), lodFor(800));
      const project = (c) => ({ x: (c.x - 1100) * 1.2 + 480, y: 300 - (c.y - 1250) * 1.2 });
      const placed = placeWorldLabels(candidates, project, FRAME, { fontPx: 20, nationFontPx: 25 });
      for (let i = 0; i < placed.length; i += 1) {
        for (let j = i + 1; j < placed.length; j += 1) {
          const p = placed[i].box;
          const q = placed[j].box;
          expect(p.left < q.right && q.left < p.right && p.top < q.bottom && q.top < p.bottom).toBe(false);
        }
      }
    } finally {
      document.documentElement.style.removeProperty("--ui-scale");
    }
  });

  it("collisions hide the lower-priority label instead of shrinking it", () => {
    const project = (c) => ({ x: c.x, y: c.y });
    const candidates = [
      { key: "quest:tracked", kind: "quest", lines: ["追蹤中的委託"], x: 300, y: 300, priority: 1 },
      { key: "quest:other", kind: "quest", lines: ["另一個委託"], x: 304, y: 302, priority: 1.5 },
      { key: "place:near", kind: "place", lines: ["近旁的聚落"], x: 296, y: 300, priority: 5 },
      { key: "place:far", kind: "place", lines: ["遠方港口"], x: 700, y: 400, priority: 5 },
    ];
    const placed = placeWorldLabels(candidates, project, { width: 960, height: 600 }, { fontPx: 16 });
    const keys = placed.map((l) => l.key);
    expect(keys[0]).toBe("quest:tracked");
    expect(keys).toContain("place:far");
    for (const l of placed) expect(l.fontPx).toBe(16);
    for (let i = 0; i < placed.length; i += 1) {
      for (let j = i + 1; j < placed.length; j += 1) {
        const a = placed[i].box;
        const b = placed[j].box;
        expect(a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom).toBe(false);
      }
    }
    expect(placed.length).toBeLessThan(candidates.length);
  });

  it("a host echoing a cloned view keeps the opening re-fit", async () => {
    let resize = null;
    const original = globalThis.ResizeObserver;
    globalThis.ResizeObserver = class {
      constructor(cb) {
        resize = cb;
      }
      observe() {}
      disconnect() {}
    };
    try {
      const w = mountMap(worldBase());
      const opening = w.emitted("update:view").at(-1)[0];
      // The host stores and echoes a serialised copy of the opening view.
      await w.setProps({ view: JSON.parse(JSON.stringify(opening)) });
      const before = w.emitted("update:view").length;
      // The real frame is measured afterwards: the opening view re-fits.
      resize([{ contentRect: { width: 1500, height: 800 } }]);
      await w.vm.$nextTick();
      expect(w.emitted("update:view").length).toBe(before + 1);
      const refit = w.emitted("update:view").at(-1)[0];
      // A view the player moved to is adopted and stops the re-fit.
      await w.setProps({ view: { ...refit, cx: refit.cx + 50 } });
      resize([{ contentRect: { width: 1400, height: 760 } }]);
      await w.vm.$nextTick();
      expect(w.emitted("update:view").length).toBe(before + 1);
    } finally {
      globalThis.ResizeObserver = original;
    }
  });

  it("the trail is a line until 近郊, then cells at the supplied resolution", async () => {
    const w = mountMap(worldBase(), { view: viewAt(800) });
    const trail = () => w.find('[data-testid="world-map__trail"]');
    expect(trail().attributes("data-mode")).toBe("line");
    await w.setProps({ view: viewAt(40) });
    expect(trail().attributes("data-mode")).toBe("cells");
    const fine = trail().find(".world-map__trail-cells").attributes("d");
    expect(new Set(fine.match(/v-?\d+/g))).toEqual(new Set(["v1"]));
  });

  it("a downsampled 5 km trail keeps 5 km cells at 近郊", () => {
    const world = worldCoarseTrail();
    expect(world.trail.resolution_km).toBe(5);
    const w = mountMap(world, { view: viewAt(40) });
    const trail = w.find('[data-testid="world-map__trail"]');
    expect(trail.attributes("data-resolution-km")).toBe("5");
    const d = trail.find(".world-map__trail-cells").attributes("d");
    expect(new Set(d.match(/v-?\d+/g))).toEqual(new Set(["v5"]));
    // Every cell origin is a multiple of 5 km: no 1 km precision is implied.
    for (const m of d.matchAll(/M(\d+) (\d+)/g)) {
      expect(Number(m[1]) % 5).toBe(0);
      expect(Number(m[2]) % 5).toBe(0);
    }
  });

  it("the trail line joins only visited cells and stays bounded at a wide view", () => {
    const trail = { resolution_km: 1, rows: [[10, [[10, 3]]], [11, [[13, 1]]], [30, [[30, 1]]]] };
    const { d, segments } = trailLinePath(trail, 1);
    // One chain (10..12 then the diagonal to 13,11) and one dot.
    expect(segments).toBe(2);
    expect(d).toContain("M30.5 30.5L30.5 30.5");
    // A dense worst case at 5 km (every other column of every row) at a
    // continent view collapses onto a coarse lattice.
    const rows = [];
    for (let row = 0; row < 540; row += 1) rows.push([row, Array.from({ length: 135 }, (_, i) => [i * 4, 1])]);
    const dense = { resolution_km: 5, rows };
    const grid = trailGridKm(dense, 3000 / 960);
    expect(grid).toBeGreaterThanOrEqual(25);
    const line = trailLinePath(dense, grid);
    expect(line.points).toBeLessThan((2700 / grid) ** 2 * 8);
  });
});

describe("newly lit districts animate accessibly from their landmark", () => {
  const discovery = (w) => w.find('[data-testid="world-map__discovery"]').text();

  it("the initial payload, a repeat and a remount replay nothing", async () => {
    document.documentElement.style.setProperty("--motion-district-reveal", "600ms");
    const w = mountMap(worldNewLight());
    await tick();
    expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
    expect(discovery(w)).toBe("");
    await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
    await tick();
    expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
    expect(discovery(w)).toBe("");
    const again = mountMap(worldNewLight());
    await tick();
    expect(again.find('[data-testid="world-map__ink"]').exists()).toBe(false);
    expect(discovery(again)).toBe("");
  });

  it("an unlit-to-lit transition spreads 600 ms of ink from the landmark and announces once", async () => {
    document.documentElement.style.setProperty("--motion-district-reveal", "600ms");
    // The spread is an animation clock, so the test owns that clock: the
    // frames and `performance.now()` are faked and every assertion is about
    // the token's own 600 ms, never about how fast the runner got to run the
    // test (a starved real clock let the spread expire before the first
    // assertion).
    vi.useFakeTimers({
      toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance", "setTimeout", "clearTimeout"],
    });
    try {
      const w = mountMap(worldBase(), { view: viewAt(420, { x: 1220, y: 1340 }) });
      const lit = newLight();
      await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
      await nextTick();
      const ink = w.findAll('[data-testid="world-map__ink"]');
      expect(ink).toHaveLength(1);
      expect(ink[0].attributes("data-district")).toBe(lit.id);
      expect(ink[0].attributes("data-reveal-ms")).toBe("600");
      expect(Number(ink[0].attributes("cx"))).toBe(lit.landmark.x);
      expect(Number(ink[0].attributes("cy"))).toBe(lit.landmark.y);
      expect(w.find(`.world-map__lit[data-district="${lit.id}"]`).attributes("mask")).toContain("-reveal-");
      expect(discovery(w)).toBe(`已探明：${lit.name}`);
      // A republish of the same knowledge mid-spread adds nothing.
      await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
      await nextTick();
      expect(w.findAll('[data-testid="world-map__ink"]')).toHaveLength(1);
      // Halfway through the advertised spread the ink still stands, so the
      // 600 ms figure is what the frames honour.
      vi.advanceTimersByTime(300);
      await nextTick();
      expect(w.findAll('[data-testid="world-map__ink"]')).toHaveLength(1);
      // 750 ms past the start the ink and the reveal mask are gone.
      vi.advanceTimersByTime(450);
      await nextTick();
      expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
      expect(w.find(`.world-map__lit[data-district="${lit.id}"]`).attributes("mask")).toBeUndefined();
      // Rendering emitted no knowledge, only view bookkeeping.
      expect(Object.keys(w.emitted()).filter((name) => !["update:view"].includes(name) && !name.startsWith("pointer"))).toEqual([]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("reduced or off motion lights the district instantly and still announces", async () => {
    for (const ms of ["0ms", null]) {
      if (ms) document.documentElement.style.setProperty("--motion-district-reveal", ms);
      else document.documentElement.style.removeProperty("--motion-district-reveal");
      const w = mountMap(worldBase());
      await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
      await tick();
      const lit = newLight();
      expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
      expect(w.find(`[data-testid="world-map__district"][data-district="${lit.id}"]`).attributes("data-lit")).toBe("true");
      expect(w.find(`.world-map__lit[data-district="${lit.id}"]`).attributes("mask")).toBeUndefined();
      expect(discovery(w)).toBe(`已探明：${lit.name}`);
    }
  });

  it("unmounting mid-spread cancels the pending frame", async () => {
    document.documentElement.style.setProperty("--motion-district-reveal", "600ms");
    const cancelled = [];
    const original = globalThis.cancelAnimationFrame;
    globalThis.cancelAnimationFrame = (handle) => {
      cancelled.push(handle);
      return original?.(handle);
    };
    try {
      const w = mountMap(worldBase());
      await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
      expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(true);
      w.unmount();
      wrappers = wrappers.filter((item) => item !== w);
      expect(cancelled.length).toBe(1);
    } finally {
      globalThis.cancelAnimationFrame = original;
    }
  });

  it("a new epoch or someone else's knowledge re-baselines silently", async () => {
    document.documentElement.style.setProperty("--motion-district-reveal", "600ms");
    const w = mountMap(worldBase(), { epoch: "e1" });
    await w.setProps({ world: validateWorldMapPanel(worldNewLight()), epoch: "e2" });
    await tick();
    expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
    expect(discovery(w)).toBe("");
    // A payload where a lit district went dark belongs to other knowledge.
    const other = worldMap({ lit: new Set() });
    await w.setProps({ world: validateWorldMapPanel(other) });
    await tick();
    expect(discovery(w)).toBe("");
    expect(revealTransitions(worldBase(), other).regressed).toBe(true);
    expect(revealTransitions(null, worldBase())).toEqual({ lit: [], regressed: false });
  });
});

describe("world selection exposes readable permitted detail", () => {
  it("the lit deep forest lists both nations as text", async () => {
    const w = mountMap(worldForestLit(), { view: viewAt(800, FOREST_LANDMARK) });
    await pick(w, `district:${FOREST_ID}`);
    const detail = w.emitted("select").at(-1)[0];
    expect(detail).toMatchObject({ key: `district:${FOREST_ID}`, kind: "district", id: FOREST_ID, lit: true, title: "北境深林" });
    // Both nominal claims (Grandia and Valhalla in the scenario), resolved
    // from the district's nation ids through common.nations.
    const both = FOREST_NATION_IDS.map((id) => NATIONS.find((n) => n.id === id).name);
    expect(detail.nations).toEqual(both);
    const chips = w.findAll('[data-testid="world-map-detail__nation"]').map((c) => c.text());
    expect(chips).toEqual(both);
    expect(w.find('[data-testid="world-map-detail"]').text()).toContain("地標：千年古樹");
    expect(w.find('[data-testid="world-map__live"]').text()).toBe("已選取：北境深林");
  });

  it("a single-nation district lists only its own nation, resolved by id", () => {
    const world = worldBase();
    expect(world.common.nations).toHaveLength(3);
    const district = world.districts.find((d) => d.lit);
    const detail = featureDetail(world, `district:${district.id}`);
    expect(detail.nations).toEqual([NATIONS.find((n) => n.id === district.nations[0]).name]);
    expect(detail.nations).toHaveLength(1);
  });

  it("an unlit selection stays nameless and invents nothing", async () => {
    const lit = newLight();
    const w = mountMap(worldBase(), { view: viewAt(420, { x: 1220, y: 1340 }) });
    await pick(w, `district:${lit.id}`);
    const detail = w.emitted("select").at(-1)[0];
    expect(detail).toMatchObject({ kind: "district", id: lit.id, lit: false, title: "未探明", nations: [], places: [], quests: [] });
    const text = w.find('[data-testid="world-map-detail"]').text();
    expect(text).not.toContain(lit.name);
    expect(text).not.toContain(lit.landmark.name);
    expect(w.findAll('[data-testid="world-map-detail__nation"]')).toHaveLength(0);
    const button = w.find(`[data-feature="district:${lit.id}"]`).text();
    expect(button).toMatch(/^未探明分區，(北|東北|東|東南|南|西南|西|西北)方 · 直線約 \d+ km$/);
    // Once it lights, the same key reads the supplied name.
    await w.setProps({ world: validateWorldMapPanel(worldNewLight()) });
    expect(w.find('[data-testid="world-map-detail__title"]').text()).toBe(lit.name);
  });

  it("commissions and places mirror their supplied details", async () => {
    const world = worldBase();
    const w = mountMap(world, { view: viewAt(800, { x: 1150, y: 1300 }) });
    // A selection under the detail card pans into view, so pick west to east.
    await pick(w, `place:${PLACE_IDS.hiddenVale}`);
    let detail = w.emitted("select").at(-1)[0];
    expect(detail).toMatchObject({ kind: "place", title: "月隱谷", label: "隱密之地" });
    expect(detail.lines).toContain("曾到訪");
    await pick(w, `quest:${QUEST_IDS.exact}`);
    detail = w.emitted("select").at(-1)[0];
    expect(detail).toMatchObject({ kind: "quest", id: QUEST_IDS.exact, approximate: false, title: "護送藥草商人" });
    expect(detail.lines).toContain("追蹤中");
    expect(detail.lines).toContain("精確位置");
    await pick(w, `quest:${QUEST_IDS.nearApproximate}`);
    detail = w.emitted("select").at(-1)[0];
    expect(detail.approximate).toBe(true);
    expect(detail.lines.some((line) => line.startsWith("大致方位"))).toBe(true);
    // The approximate commission stays clear of the open detail card.
    const ring = w.find(`[data-testid="world-map__approx"][data-quest="${QUEST_IDS.nearApproximate}"] .world-map__approx-ring`);
    expect(Number(ring.attributes("cx"))).toBeLessThanOrEqual(FRAME.width - 360 - 24);
  });

  it("a controlled selection follows the host and drops a vanished feature", async () => {
    const lit = newLight();
    const w = mountMap(worldNewLight(), { selected: `district:${lit.id}` });
    expect(w.find('[data-testid="world-map-detail__title"]').text()).toBe(lit.name);
    await w.setProps({ selected: null });
    expect(w.find('[data-testid="world-map-detail"]').exists()).toBe(false);
    await w.setProps({ selected: `quest:${QUEST_IDS.exact}` });
    expect(w.find('[data-testid="world-map-detail__title"]').text()).toBe("護送藥草商人");
    await w.setProps({ world: validateWorldMapPanel(worldMap({ quests: [] })) });
    expect(w.find('[data-testid="world-map-detail"]').exists()).toBe(false);
    expect(w.emitted("update:selected").at(-1)[0]).toBe(null);
  });

  it("selection works from real HTML buttons and a drag never selects", async () => {
    const w = mountMap(worldBase());
    const buttons = w.findAll("[data-feature]");
    expect(buttons.length).toBe(worldBase().quest_markers.length + 4 + worldBase().districts.length);
    expect(buttons.filter((b) => b.attributes("tabindex") === "0")).toHaveLength(1);
    const first = buttons.find((b) => b.attributes("tabindex") === "0");
    expect(first.attributes("data-feature")).toBe(`quest:${QUEST_IDS.exact}`);
    first.element.focus();
    await first.trigger("focus");
    expect(w.find('[data-testid="world-map__focus-ring"]').exists()).toBe(true);
    await first.trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement.getAttribute("data-feature")).toBe(buttons[1].attributes("data-feature"));
    await buttons[1].trigger("click");
    expect(w.emitted("update:selected").at(-1)[0]).toBe(buttons[1].attributes("data-feature"));
    await w.find('[data-testid="world-map"]').trigger("keydown", { key: "Escape" });
    expect(w.emitted("update:selected").at(-1)[0]).toBe(null);

    w.vm.recentre();
    await w.vm.$nextTick();
    const el = w.find(`[data-pick="quest:${QUEST_IDS.exact}"]`);
    const before = w.emitted("update:selected").length;
    await el.trigger("pointerdown", { button: 0, clientX: 10, clientY: 10 });
    await w.find('[data-testid="world-map__surface"]').trigger("pointermove", { clientX: 60, clientY: 40 });
    await w.find('[data-testid="world-map__surface"]').trigger("pointerup", { clientX: 60, clientY: 40 });
    expect(w.emitted("update:selected").length).toBe(before);
  });
});
