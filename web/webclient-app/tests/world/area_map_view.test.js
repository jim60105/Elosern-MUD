// AreaMapView (OpenSpec change render-area-map-view). The two top-level
// describe blocks map one-to-one to the webclient-area-map-view
// requirements; tests/test_map_client_contracts.py AreaViewContracts checks
// that each block ran and passed. Expected geometry is computed by hand from
// the synthetic fixtures (stories/fixtures/area_map.js), never by calling the
// helpers under test.

import { afterEach, describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { mount } from "@vue/test-utils";
import AreaMapView from "../../components/AreaMapView.vue";
import { placeLabels } from "@elosern/map-view";
import { GAME_MAP_THEME, GAME_MAP_THEME_VARS } from "../../lib/map_theme.js";
import MapPanels from "../../../static/webclient/js/elosern/protocol/panels/map_panels.js";
import {
  ABSENT_DUNGEON_ROOMS,
  DUNGEON_IDS,
  TOWN_IDS,
  WILD_GATE_ID,
  crowdedTownArea,
  dungeonArea,
  interiorArea,
  townArea,
  townFromEastArea,
  wildernessArea,
} from "../../stories/fixtures/area_map.js";

const { validateAreaMapPanel } = MapPanels;

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
});

function mountMap(area, props = {}) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const w = mount(AreaMapView, { props: { area: validateAreaMapPanel(area), ...props }, attachTo: host });
  wrappers.push(w);
  return w;
}

function nodeEl(w, id) {
  return w.findAll('[data-testid="area-map__node"]').find((n) => n.attributes("data-node-id") === id);
}

function nodePos(w, id) {
  const g = nodeEl(w, id).find("g");
  const match = /translate\(([-\d.e]+) ([-\d.e]+)\)/.exec(g.attributes("transform"));
  return { x: Number(match[1]), y: Number(match[2]) };
}

async function select(w, id) {
  const el = nodeEl(w, id);
  await el.trigger("pointerdown", { button: 0, clientX: 10, clientY: 10 });
  await el.trigger("pointerup", { button: 0, clientX: 10, clientY: 10 });
}

describe("area rendering uses truthful geometry and server fog", () => {
  it("every story fixture is a schema-valid area_map body", () => {
    for (const body of [townArea(), crowdedTownArea(), townFromEastArea(), dungeonArea(), interiorArea(), wildernessArea(), wildernessArea({ cellKm: 2 })]) {
      expect(() => validateAreaMapPanel(body)).not.toThrow();
    }
  });

  it("keeps unequal metric gaps proportional under zoom and pan", async () => {
    const w = mountMap(townArea());
    const ratios = () => {
      const c = nodePos(w, TOWN_IDS.square);
      const gap = (id) => Math.hypot(nodePos(w, id).x - c.x, nodePos(w, id).y - c.y);
      // Authored gaps: west 60 m, east 120 m, south 240 m, north 360 m.
      return [gap(TOWN_IDS.east) / gap(TOWN_IDS.west), gap(TOWN_IDS.south) / gap(TOWN_IDS.west), gap(TOWN_IDS.northGate) / gap(TOWN_IDS.west)];
    };
    const check = () => {
      const [a, b, c] = ratios();
      expect(a).toBeCloseTo(2, 6);
      expect(b).toBeCloseTo(4, 6);
      expect(c).toBeCloseTo(6, 6);
    };
    check();
    // North is up: the north gate sits above the square, the quay below.
    expect(nodePos(w, TOWN_IDS.northGate).y).toBeLessThan(nodePos(w, TOWN_IDS.square).y);
    expect(nodePos(w, TOWN_IDS.south).y).toBeGreaterThan(nodePos(w, TOWN_IDS.square).y);
    w.vm.zoomOut();
    await w.vm.$nextTick();
    check();
    w.vm.panBy(37, -12);
    await w.vm.$nextTick();
    check();
    // No compressed fallback exists on this surface.
    expect(w.html()).not.toContain("距離壓縮");
  });

  it("dot spacing and both scale captions state the same real distance", async () => {
    const w = mountMap(townArea());
    for (const step of [null, "zoomIn", "zoomIn", "zoomOut", "showWhole"]) {
      if (step) {
        w.vm[step]();
        await w.vm.$nextTick();
      }
      const view = w.emitted("update:view").at(-1)[0];
      const k = 960 / view.span; // px per metre at the provisional frame
      const field = w.find('[data-testid="area-map__dot-field"]');
      const stepMetres = Number(field.attributes("data-step-metres"));
      const spacing = Number(field.attributes("data-spacing-px"));
      expect(spacing / stepMetres).toBeCloseTo(k, 9);
      expect(spacing).toBeGreaterThanOrEqual(30 - 1e-9);
      // A round 1/2/5 x 10^n metre step.
      expect(String(stepMetres)).toMatch(/^[125]0*$/);
      const caption = w.find('[data-testid="area-map__dot-caption"]').text();
      expect(caption).toBe(`格距 ${stepMetres >= 1000 ? `${stepMetres / 1000} km` : `${stepMetres} m`}`);
      const barPx = Number.parseFloat(w.find('[data-testid="area-map__scale-bar"]').attributes("style").replace(/[^\d.]/g, ""));
      const barText = w.find('[data-testid="area-map__scale-text"]').text();
      const barMetres = barText.endsWith(" km") ? Number.parseFloat(barText) * 1000 : Number.parseFloat(barText);
      expect(barPx / barMetres).toBeCloseTo(k, 6);
    }
  });

  it("opens centred on the current node at a zoom that fits its adjacent nodes", () => {
    const w = mountMap(townArea());
    const view = w.emitted("update:view")[0][0];
    expect(view.signature).toBe("grid|story_town|m");
    expect(view.cx).toBe(400);
    expect(view.cy).toBe(300);
    const k = 960 / view.span;
    // The farthest neighbour (north gate, 360 m) stays inside the frame.
    expect(300 - 360 * k).toBeGreaterThanOrEqual(0);
  });

  it("renders the 15 x 15 wilderness window in cells with the district", () => {
    const area = wildernessArea();
    const w = mountMap(area);
    const nodes = w.findAll('[data-testid="area-map__node"]');
    expect(nodes.length).toBe(area.nodes.length);
    expect(area.nodes.length).toBe(225 - 5); // the pond is invalid ground
    expect(w.findAll(".area-map__cell").length).toBe(area.nodes.length);
    expect(w.find('[data-testid="area-map__district"]').text()).toBe("灰鬃荒原東麓");
    // Visited trail cells carry their own state.
    expect(nodeEl(w, "wild:elosern:98:198").classes()).toContain("is-visited");
    expect(nodeEl(w, "wild:elosern:105:205").classes()).toContain("is-seen");
    // The gate room replacing the north-east step names its far side.
    const gate = w.findAll('[data-testid="area-map__label"]').find((l) => l.attributes("data-label-for") === WILD_GATE_ID);
    expect(gate.text().replace(/\s+/g, "")).toBe("河岸碼頭通往灰岩鎮");
  });

  it("follows the panel's cell scale for wilderness distances", () => {
    for (const cellKm of [1, 2]) {
      const w = mountMap(wildernessArea({ cellKm }));
      const view = w.emitted("update:view")[0][0];
      // Map units are cells; the current cell centre is (100.5, 200.5).
      expect(view.cx).toBeCloseTo(100.5, 9);
      expect(view.cy).toBeCloseTo(200.5, 9);
      const kPerMetre = 960 / view.span / (cellKm * 1000);
      const field = w.find('[data-testid="area-map__dot-field"]');
      expect(Number(field.attributes("data-spacing-px")) / Number(field.attributes("data-step-metres"))).toBeCloseTo(kPerMetre, 9);
      const barText = w.find('[data-testid="area-map__scale-text"]').text();
      const barMetres = barText.endsWith(" km") ? Number.parseFloat(barText) * 1000 : Number.parseFloat(barText);
      const barPx = Number.parseFloat(w.find('[data-testid="area-map__scale-bar"]').attributes("style").replace(/[^\d.]/g, ""));
      expect(barPx / barMetres).toBeCloseTo(kPerMetre, 6);
      // One cell east is exactly one cell width on screen.
      const a = nodePos(w, WILD_GATE_ID);
      const here = nodeEl(w, "wild:elosern:100:200").find("g").attributes("transform");
      const [hx] = /translate\(([-\d.e]+)/.exec(here).slice(1).map(Number);
      expect(a.x - hx).toBeCloseTo(960 / view.span, 6);
    }
  });

  it("keeps coordinate-free rooms radial with no distance claims", () => {
    for (const area of [dungeonArea(), interiorArea()]) {
      const w = mountMap(area);
      expect(w.findAll('[data-testid="area-map__node"]').length).toBe(area.nodes.length);
      expect(w.find('[data-testid="area-map__dot-field"]').exists()).toBe(false);
      expect(w.find('[data-testid="area-map__scale-bar"]').exists()).toBe(false);
      expect(w.find('[data-testid="area-map__schematic"]').text()).toBe("示意圖 · 不依實際距離");
      expect(w.emitted("update:view")[0][0].signature).toBe(`${area.layer}|${area.map_id}|none`);
      // Distinct positions for every room, and the current room at the centre.
      const positions = area.nodes.map((n) => nodePos(w, n.id));
      expect(new Set(positions.map((p) => `${p.x.toFixed(3)},${p.y.toFixed(3)}`)).size).toBe(area.nodes.length);
      expect(nodePos(w, area.current_node).x).toBeCloseTo(480, 6);
      expect(w.text()).not.toMatch(/直線約/);
    }
  });

  it("never renders or discloses a branch absent from the payload", async () => {
    const w = mountMap(dungeonArea());
    const html = () => w.html();
    for (const room of ABSENT_DUNGEON_ROOMS) {
      expect(html()).not.toContain(room.id);
      expect(html()).not.toContain(room.label);
    }
    // The commission into fog adds no pin, node or title anywhere.
    expect(html()).not.toContain("取回沉睡王的冠冕");
    expect(w.findAll(".area-map__quest").length).toBe(0);
    // Every road joins two drawn rooms: payload edges only.
    expect(w.findAll(".area-map__road").length).toBe(dungeonArea().edges.length);
    // Seen rooms keep the server's 未探索 and expose no exits.
    await select(w, DUNGEON_IDS.frontier);
    expect(w.find('[data-testid="area-map-detail__title"]').text()).toBe("未探索");
    expect(w.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);
    // A host cannot select a fogged identity into view.
    await w.setProps({ selected: ABSENT_DUNGEON_ROOMS[0].id });
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(false);
    for (const room of ABSENT_DUNGEON_ROOMS) {
      expect(html()).not.toContain(room.id);
      expect(html()).not.toContain(room.label);
    }
  });

  it("draws known names whole and hides lower-priority labels instead", async () => {
    const area = crowdedTownArea();
    const w = mountMap(area);
    const labels = w.findAll('[data-testid="area-map__label"]');
    const byId = new Map(area.nodes.map((n) => [n.id, n]));
    for (const label of labels) {
      const node = byId.get(label.attributes("data-label-for"));
      const first = label.findAll("tspan")[0].text();
      expect([node.label, `通往 ${node.gateway?.leads_to}`]).toContain(first);
      expect(label.text()).not.toContain("…");
    }
    expect(labels.length).toBeLessThan(area.nodes.length);
    // The current node keeps its name; every node keeps its full accessible name.
    expect(labels.some((l) => l.attributes("data-label-for") === TOWN_IDS.square)).toBe(true);
    for (const node of area.nodes) {
      expect(nodeEl(w, node.id).attributes("aria-label").startsWith(node.label)).toBe(true);
    }
    // A hidden name becomes visible once selected, and reads whole in the detail.
    const hidden = area.nodes.find((n) => !labels.some((l) => l.attributes("data-label-for") === n.id));
    await select(w, hidden.id);
    expect(w.find('[data-testid="area-map-detail__title"]').text()).toBe(hidden.label);
    expect(w.findAll('[data-testid="area-map__label"]').some((l) => l.attributes("data-label-for") === hidden.id)).toBe(true);
  });

  it("the selected and current names never overlap, even in a cramped frame", () => {
    // The shared placement reads a candidate's own id, which the area host
    // attaches to every label candidate.
    const entry = (id, x, priority) => ({ id, x, y: 30, priority, lines: [`${id}名稱`] });
    // A 60 x 60 frame where no regular spot fits either 52 px name, so both
    // must-place names reach the clamped last resort.
    const out = placeLabels(
      [entry("甲", 10, 0), entry("乙", 40, 1)],
      (e) => ({ x: e.x, y: e.y }),
      { width: 60, height: 60 },
      { measure: (text, px) => text.length * px },
    );
    expect(out.map((l) => l.id)).toEqual(["甲", "乙"]);
    const [a, b] = out.map((l) => l.box);
    const overlap = a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
    expect(overlap).toBe(false);
  });

  it("a new map resets the view and selection; a matching view is adopted", async () => {
    const w = mountMap(townArea());
    await select(w, TOWN_IDS.east);
    expect(w.emitted("update:selected").at(-1)).toEqual([TOWN_IDS.east]);
    const emittedBefore = w.emitted("update:view").length;
    const supplied = { signature: "grid|story_town|m", cx: 500, cy: 250, span: 900 };
    await w.setProps({ view: supplied });
    expect(w.emitted("update:view").length).toBe(emittedBefore);
    expect(w.vm.view).toEqual(supplied);
    await w.setProps({ area: validateAreaMapPanel(dungeonArea()), view: supplied });
    expect(w.emitted("update:selected").at(-1)).toEqual([null]);
    const reset = w.emitted("update:view").at(-1)[0];
    expect(reset.signature).toBe("instance|instance:41|none");
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(false);
  });

  it("a host restoring a tab's selection on a new map keeps it", async () => {
    const w = mountMap(townArea(), { selected: TOWN_IDS.east });
    await w.setProps({ area: validateAreaMapPanel(dungeonArea()), selected: DUNGEON_IDS.well });
    expect(w.find('[data-testid="area-map-detail__title"]').text()).toBe("乾涸的井室");
    expect(w.emitted("update:selected")).toBeUndefined();
  });

  it("wheel zoom stays inside the layer's zoom limits", async () => {
    const w = mountMap(townArea());
    const surface = w.find('[data-testid="area-map__surface"]');
    for (let i = 0; i < 40; i += 1) await surface.trigger("wheel", { deltaY: 400 });
    const out = w.emitted("update:view").at(-1)[0].span;
    for (let i = 0; i < 80; i += 1) await surface.trigger("wheel", { deltaY: -400 });
    const inner = w.emitted("update:view").at(-1)[0].span;
    const stops = w.vm.stops.map((s) => s.span);
    expect(out).toBeCloseTo(Math.max(...stops) * 1.25, 6);
    expect(inner).toBeCloseTo(Math.min(...stops) * 0.5, 6);
  });

  it("publishes the host theme roles the shared glyphs read", () => {
    const w = mountMap(townArea());
    const root = w.get('[data-testid="area-map"]').element;
    // The surface exposes the package's theme namespace with the game's own
    // tokens, so a shared glyph's `var(--map-view-<role>)` hook resolves here.
    for (const [property, value] of Object.entries(GAME_MAP_THEME_VARS)) {
      expect(root.style.getPropertyValue(property)).toBe(value);
    }
    expect(Object.keys(GAME_MAP_THEME_VARS).length).toBe(Object.keys(GAME_MAP_THEME).length);
    // The shared node glyph reads those hooks (with its own fallbacks), so no
    // second ink source is needed for a second map host.
    const glyph = readFileSync(resolve(__dirname, "../../components/MapNodeGlyph.vue"), "utf-8");
    for (const role of ["halo", "paper", "current", "node", "accent", "accent-muted", "selection"]) {
      expect(glyph).toContain(`var(--map-view-${role}`);
    }
  });
});

describe("area selection offers travel only for an authoritative adjacent exit", () => {
  it("pointer selection of an adjacent exit offers 前往 and emits the exact descriptor once", async () => {
    const w = mountMap(townArea());
    await select(w, TOWN_IDS.east);
    const card = w.find('[data-testid="area-map-detail"]');
    expect(card.find('[data-testid="area-map-detail__title"]').text()).toBe("銅匠街");
    expect(card.text()).toContain("到過");
    expect(card.text()).toContain("東方 · 直線約 120 m");
    await card.find('[data-testid="area-map-detail__go"]').trigger("click");
    expect(w.emitted("move")).toEqual([
      [{ exit_ref: "e_square_e", destination: TOWN_IDS.east, current_node: TOWN_IDS.square }],
    ]);
  });

  it("keyboard reaches 前往: roving node focus, Enter selects, the button activates", async () => {
    const w = mountMap(townArea());
    const tabStops = w.findAll('[data-testid="area-map__node"]').filter((n) => n.attributes("tabindex") === "0");
    expect(tabStops.map((n) => n.attributes("data-node-id"))).toEqual([TOWN_IDS.square]);
    const square = nodeEl(w, TOWN_IDS.square);
    square.element.focus();
    await square.trigger("keydown", { key: "ArrowUp" });
    expect(document.activeElement.getAttribute("data-node-id")).toBe(TOWN_IDS.northGate);
    const gate = nodeEl(w, TOWN_IDS.northGate);
    expect(gate.attributes("tabindex")).toBe("0");
    await gate.trigger("keydown", { key: "Enter" });
    const card = w.find('[data-testid="area-map-detail"]');
    expect(card.find('[data-testid="area-map-detail__title"]').text()).toBe("北門");
    expect(card.text()).toContain("通往 霧谷丘陵");
    expect(card.text()).toContain("看過，尚未到訪");
    const go = card.find('[data-testid="area-map-detail__go"]');
    expect(go.element.tagName).toBe("BUTTON");
    await go.trigger("click");
    expect(w.emitted("move")).toEqual([
      [{ exit_ref: "e_square_n", destination: TOWN_IDS.northGate, current_node: TOWN_IDS.square }],
    ]);
    // Escape closes the reading and returns focus to the node.
    await w.find('[data-testid="area-map"]').trigger("keydown", { key: "Escape" });
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(false);
    expect(document.activeElement.getAttribute("data-node-id")).toBe(TOWN_IDS.northGate);
  });

  it("a remote visited node is readable but never travels", async () => {
    const w = mountMap(townArea());
    await select(w, TOWN_IDS.observatory);
    const card = w.find('[data-testid="area-map-detail"]');
    expect(card.find('[data-testid="area-map-detail__title"]').text()).toBe("星辰天文塔前庭");
    expect(card.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);
    await card.find('[data-testid="area-map-detail__centre"]').trigger("click");
    expect(w.emitted("move")).toBeUndefined();
    // Its label is the full name at the 16px label step.
    const label = w.findAll('[data-testid="area-map__label"]').find((l) => l.attributes("data-label-for") === TOWN_IDS.observatory);
    expect(label.text()).toBe("星辰天文塔前庭");
    expect(label.classes()).toContain("area-map__label");
  });

  it("offers nothing for a descriptor that is not the current node's road to it", async () => {
    const base = townArea();
    const nodes = base.nodes.map((n) => {
      if (n.id === TOWN_IDS.academy) return { ...n, action: { kind: "move", exit_ref: "e_far", destination: TOWN_IDS.academy } };
      if (n.id === TOWN_IDS.west) return { ...n, action: { kind: "move", exit_ref: "e_square_w", destination: TOWN_IDS.east } };
      return n;
    });
    const w = mountMap({ ...base, nodes });
    for (const id of [TOWN_IDS.academy, TOWN_IDS.west, TOWN_IDS.square]) {
      await select(w, id);
      expect(w.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);
    }
    expect(w.emitted("move")).toBeUndefined();
  });

  it("room graphs and wilderness steps travel by their own descriptors", async () => {
    const dungeon = mountMap(dungeonArea());
    await select(dungeon, DUNGEON_IDS.crypt);
    await dungeon.find('[data-testid="area-map-detail__go"]').trigger("click");
    expect(dungeon.emitted("move")).toEqual([[{ exit_ref: "e_hall_e", destination: DUNGEON_IDS.crypt, current_node: DUNGEON_IDS.hall }]]);
    await select(dungeon, DUNGEON_IDS.stair);
    expect(dungeon.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);

    const wild = mountMap(wildernessArea());
    await select(wild, WILD_GATE_ID);
    expect(wild.find('[data-testid="area-map-detail"]').text()).toContain("通往 灰岩鎮");
    await wild.find('[data-testid="area-map-detail__go"]').trigger("click");
    expect(wild.emitted("move")).toEqual([[{ exit_ref: "e_wild_ne", destination: WILD_GATE_ID, current_node: "wild:elosern:100:200" }]]);
    await select(wild, "wild:elosern:104:204");
    expect(wild.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);
  });

  it("a repeated 前往 sends once until the area is republished", async () => {
    const w = mountMap(townArea());
    await select(w, TOWN_IDS.east);
    const go = w.find('[data-testid="area-map-detail__go"]');
    await go.trigger("click");
    await go.trigger("click");
    expect(w.emitted("move")).toHaveLength(1);
    // A fresh body (the server's republish) re-arms travel.
    await w.setProps({ area: validateAreaMapPanel(townArea()) });
    await select(w, TOWN_IDS.west);
    await w.find('[data-testid="area-map-detail__go"]').trigger("click");
    expect(w.emitted("move")).toHaveLength(2);
    expect(w.emitted("move")[1][0]).toEqual({ exit_ref: "e_square_w", destination: TOWN_IDS.west, current_node: TOWN_IDS.square });
  });

  it("a drag pans without selecting, and an empty click clears the selection", async () => {
    const w = mountMap(townArea());
    await select(w, TOWN_IDS.east);
    const el = nodeEl(w, TOWN_IDS.west);
    await el.trigger("pointerdown", { button: 0, clientX: 100, clientY: 100 });
    await w.find('[data-testid="area-map__surface"]').trigger("pointermove", { clientX: 160, clientY: 130 });
    await w.find('[data-testid="area-map__surface"]').trigger("pointerup", { clientX: 160, clientY: 130 });
    expect(w.emitted("update:selected").at(-1)).toEqual([TOWN_IDS.east]);
    const surface = w.find('[data-testid="area-map__surface"]');
    await surface.trigger("pointerdown", { button: 0, clientX: 5, clientY: 5 });
    await surface.trigger("pointerup", { button: 0, clientX: 5, clientY: 5 });
    expect(w.emitted("update:selected").at(-1)).toEqual([null]);
    expect(w.emitted("move")).toBeUndefined();
  });
});
