import { h, ref } from "vue";
import AreaMapView from "../../components/AreaMapView.vue";
import {
  ABSENT_DUNGEON_ROOMS,
  TOWN_IDS,
  WILD_GATE_ID,
  crowdedTownArea,
  dungeonArea,
  interiorArea,
  townArea,
  wildernessArea,
  wildernessNightArea,
} from "../fixtures/area_map.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// AreaMapView (render-area-map-view): the real area-tab renderer over
// synthetic, schema-valid `area_map` v2 bodies (the Vitest suite validates
// every fixture with the wire validator). The frame stands in for the map
// drawer's body at the 1451x790 reference; the drawer header, pill, quest
// dropdown and edge pointers belong to the later MapDrawer change. Each
// story's `move` emits are written to a hidden <output> so the play
// functions can assert the exact descriptor without a non-local import.

const FRAME = [
  "position: relative;",
  "box-sizing: border-box;",
  "width: calc(100vw - 2 * calc(24px * var(--ui-scale)));",
  "height: calc(100vh - var(--header-h, 0px) - 2 * calc(24px * var(--ui-scale)));",
  "margin: calc(24px * var(--ui-scale));",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
  "border-radius: var(--radius);",
  "box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);",
  "overflow: hidden;",
].join("");

const render = (args) => ({
  setup() {
    const moves = ref([]);
    const selected = ref(args.selected ?? null);
    return () =>
      h("div", { style: FRAME }, [
        h(AreaMapView, {
          area: args.area,
          selected: selected.value,
          "onUpdate:selected": (id) => {
            selected.value = id;
          },
          onMove: (payload) => {
            moves.value = [...moves.value, payload];
          },
        }),
        h("output", { "data-testid": "area-map-story__moves", hidden: true }, JSON.stringify(moves.value)),
      ]);
  },
});

export default {
  title: "World/AreaMapView",
  component: AreaMapView,
  parameters: windowViewportParameters,
};

// ── play helpers (DOM only) ─────────────────────────────────────────────

const frames = (n = 2) =>
  new Promise((resolve) => {
    const step = (left) => (left <= 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
    step(n);
  });

function fail(story, message) {
  throw new Error(`${story}: ${message}`);
}

function nodeEl(root, id) {
  return [...root.querySelectorAll('[data-testid="area-map__node"]')].find((el) => el.getAttribute("data-node-id") === id);
}

async function clickNode(root, id) {
  const el = nodeEl(root, id);
  const box = el.getBoundingClientRect();
  const init = { bubbles: true, button: 0, pointerId: 1, clientX: box.left + box.width / 2, clientY: box.top + box.height / 2 };
  el.dispatchEvent(new PointerEvent("pointerdown", init));
  el.dispatchEvent(new PointerEvent("pointerup", init));
  await frames();
}

function moves(root) {
  return JSON.parse(root.querySelector('[data-testid="area-map-story__moves"]').textContent || "[]");
}

function labels(root) {
  return [...root.querySelectorAll('[data-testid="area-map__label"]')];
}

// Every drawn label is at least 16 CSS px and no two drawn labels overlap.
function assertLabelsLegible(root, story) {
  const boxes = labels(root).map((el) => ({ el, box: el.getBoundingClientRect() }));
  if (!boxes.length) fail(story, "no label is drawn");
  for (const { el, box } of boxes) {
    const size = Number.parseFloat(getComputedStyle(el).fontSize);
    if (!(size >= 16)) fail(story, `label ${el.textContent} renders at ${size}px`);
    if (el.textContent.includes("…")) fail(story, `label ${el.textContent} is truncated`);
    if (box.width <= 0) fail(story, `label ${el.textContent} has no box`);
  }
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      const a = boxes[i].box;
      const b = boxes[j].box;
      const overlap = a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
      if (overlap) fail(story, `labels ${boxes[i].el.textContent} and ${boxes[j].el.textContent} overlap`);
    }
  }
}

function assertScaleTrue(root, story) {
  const field = root.querySelector('[data-testid="area-map__dot-field"]');
  if (!field) fail(story, "the metric view must draw its dot field");
  const step = Number(field.getAttribute("data-step-metres"));
  const spacing = Number(field.getAttribute("data-spacing-px"));
  const caption = root.querySelector('[data-testid="area-map__dot-caption"]').textContent;
  const expected = `格距 ${step >= 1000 ? `${step / 1000} km` : `${step} m`}`;
  if (caption !== expected) fail(story, `dot caption ${caption} must read ${expected}`);
  const bar = root.querySelector('[data-testid="area-map__scale-bar"]').getBoundingClientRect().width;
  const text = root.querySelector('[data-testid="area-map__scale-text"]').textContent;
  const metres = text.endsWith(" km") ? Number.parseFloat(text) * 1000 : Number.parseFloat(text);
  const ratio = bar / metres / (spacing / step);
  if (Math.abs(ratio - 1) > 0.02) fail(story, `scale bar (${text}, ${bar}px) disagrees with the dot step (${expected}, ${spacing}px)`);
}

// ── stories ─────────────────────────────────────────────────────────────

// A settlement at its opening fit: centred on 鐘樓廣場 with every adjacent
// street in view, unequal street lengths drawn true, the 格距 dot field and
// a scale bar stating the same distance, and the north gate's far side.
export const City = {
  render,
  args: { area: townArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertScaleTrue(canvasElement, "City");
    assertLabelsLegible(canvasElement, "City");
    const gate = labels(canvasElement).find((el) => el.getAttribute("data-label-for") === TOWN_IDS.northGate);
    if (!gate || gate.textContent.replace(/\s+/g, "") !== "北門通往霧谷丘陵") fail("City", "the gate must show 通往 霧谷丘陵");
  },
};

export const CityFullHd = { render, args: { area: townArea() }, ...atFullHd };

// Selecting the current node reads 你在這裡 and offers no travel.
export const CityCurrentSelection = {
  render,
  args: { area: townArea(), selected: TOWN_IDS.square },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const title = canvasElement.querySelector('[data-testid="area-map-detail__title"]');
    if (title?.textContent !== "鐘樓廣場") fail("CityCurrentSelection", "the current node must be selected");
    if (!canvasElement.querySelector('[data-testid="area-map-detail"]').textContent.includes("你在這裡")) {
      fail("CityCurrentSelection", "the reading must state 你在這裡");
    }
    if (canvasElement.querySelector('[data-testid="area-map-detail__go"]')) fail("CityCurrentSelection", "no 前往 on the current node");
  },
};

// An adjacent street: pointer selection opens its reading with 前往, which
// emits the exact server descriptor once; the keyboard reaches the north gate
// by arrow from the current node, selects it with Enter, and 前往 is the next
// focusable control.
export const CityAdjacentTravel = {
  render,
  args: { area: townArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    await clickNode(canvasElement, TOWN_IDS.east);
    const go = canvasElement.querySelector('[data-testid="area-map-detail__go"]');
    if (!go) fail("CityAdjacentTravel", "an adjacent exit must offer 前往");
    go.click();
    await frames();
    const sent = moves(canvasElement);
    const expected = { exit_ref: "e_square_e", destination: TOWN_IDS.east, current_node: TOWN_IDS.square };
    if (sent.length !== 1 || JSON.stringify(sent[0]) !== JSON.stringify(expected)) {
      fail("CityAdjacentTravel", `前往 must emit the descriptor once, got ${JSON.stringify(sent)}`);
    }
    const square = nodeEl(canvasElement, TOWN_IDS.square);
    square.focus();
    square.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
    await frames();
    if (document.activeElement?.getAttribute("data-node-id") !== TOWN_IDS.northGate) {
      fail("CityAdjacentTravel", "ArrowUp from the square must focus the north gate");
    }
    document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await frames();
    const gateGo = canvasElement.querySelector('[data-testid="area-map-detail__go"]');
    const title = canvasElement.querySelector('[data-testid="area-map-detail__title"]')?.textContent;
    if (title !== "北門" || !gateGo) fail("CityAdjacentTravel", "Enter must select the gate and offer 前往");
    const gateNode = nodeEl(canvasElement, TOWN_IDS.northGate);
    if (!(gateNode.compareDocumentPosition(gateGo) & Node.DOCUMENT_POSITION_FOLLOWING) || gateGo.disabled) {
      fail("CityAdjacentTravel", "前往 must follow the focused node in the tab order");
    }
    gateGo.focus();
    if (document.activeElement !== gateGo) fail("CityAdjacentTravel", "前往 must take keyboard focus");
  },
};

// A visited street two roads away: its full name reads at 16px or more, and
// the reading offers 置中顯示 but never 前往.
export const RemoteVisitedInert = {
  render,
  args: { area: townArea(), selected: TOWN_IDS.observatory },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    if (canvasElement.querySelector('[data-testid="area-map-detail__go"]')) fail("RemoteVisitedInert", "a remote node must not offer 前往");
    const label = labels(canvasElement).find((el) => el.getAttribute("data-label-for") === TOWN_IDS.observatory);
    if (!label || label.textContent !== "星辰天文塔前庭") fail("RemoteVisitedInert", "the remote name must be drawn whole");
    if (Number.parseFloat(getComputedStyle(label).fontSize) < 16) fail("RemoteVisitedInert", "the remote name must be at least 16px");
    canvasElement.querySelector('[data-testid="area-map-detail__centre"]').click();
    await frames();
    if (moves(canvasElement).length !== 0) fail("RemoteVisitedInert", "a remote node must submit nothing");
    assertLabelsLegible(canvasElement, "RemoteVisitedInert");
  },
};

// Six long known names crowd the square: lower-priority labels are hidden,
// never truncated or shrunk, and no two drawn labels overlap.
export const CrowdedNames = {
  render,
  args: { area: crowdedTownArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertLabelsLegible(canvasElement, "CrowdedNames");
    const area = crowdedTownArea();
    const drawn = new Set(labels(canvasElement).map((el) => el.getAttribute("data-label-for")));
    if (drawn.size >= area.nodes.length) fail("CrowdedNames", "the crowded block must hide some names");
    if (!drawn.has(TOWN_IDS.square)) fail("CrowdedNames", "the current name is never hidden");
  },
};

// The wilderness neighbourhood (schema 2): the revealed ground of a short
// trail and a lone old camp decoded from the run-length rows over the fog of
// the 41 x 41 window, walked cells brighter than remembered ones, the
// daylight sight ring with two wolves and a traveller inside it, distant
// sightings on the frame rim, the town gate replacing the north-east step,
// and the district with its light and sight caption.
export const Wilderness = {
  render,
  args: { area: wildernessArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const nodes = canvasElement.querySelectorAll('[data-testid="area-map__node"]').length;
    if (nodes !== wildernessArea().nodes.length) fail("Wilderness", `expected sparse nodes, got ${nodes}`);
    if (!canvasElement.querySelector('[data-testid="area-map__terrain"].is-remembered')) fail("Wilderness", "remembered ground must be drawn");
    if (canvasElement.querySelectorAll('[data-testid="area-map__entity"]').length !== 3) fail("Wilderness", "three live-sight entities");
    if (canvasElement.querySelectorAll('[data-testid="area-map__sighting"]').length !== 3) fail("Wilderness", "three distant sightings");
    if (canvasElement.querySelector('[data-testid="area-map__district"]')?.textContent !== "灰鬃荒原東麓") {
      fail("Wilderness", "the current district must be shown");
    }
    assertScaleTrue(canvasElement, "Wilderness");
    assertLabelsLegible(canvasElement, "Wilderness");
    await clickNode(canvasElement, WILD_GATE_ID);
    if (!canvasElement.querySelector('[data-testid="area-map-detail__go"]')) fail("Wilderness", "the gate step must offer 前往");
  },
};

// The same window at 1920 x 1080: the 16px label floor and the rim
// sightings hold at the wide reference.
export const WildernessWide = {
  render,
  args: { area: wildernessArea() },
  ...atFullHd,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertLabelsLegible(canvasElement, "WildernessWide");
  },
};

// Night: ground sight shrinks to one cell, no entity stands in it and only a
// town's lights carry over the horizon; the revealed ground stays revealed.
export const WildernessNight = {
  render,
  args: { area: wildernessNightArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    if (canvasElement.querySelector('[data-testid="area-map__entity"]')) fail("WildernessNight", "no entity stands in night sight");
    if (!canvasElement.querySelector('[data-testid="area-map__sight"]')?.textContent.includes("夜晚 · 視野 1 格")) {
      fail("WildernessNight", "the caption states the night sight");
    }
  },
};

// A dungeon instance on the radial room layout: seen rooms read 未探索,
// the deeper branch absent from the payload (and the commission that points
// into it) leaves no node, road, label, attribute or text anywhere.
export const DungeonFog = {
  render,
  args: { area: dungeonArea() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const html = canvasElement.innerHTML;
    for (const room of ABSENT_DUNGEON_ROOMS) {
      if (html.includes(room.id) || html.includes(room.label)) fail("DungeonFog", `the fogged room ${room.id} leaked`);
    }
    if (html.includes("取回沉睡王的冠冕")) fail("DungeonFog", "a commission into fog must add nothing");
    if (canvasElement.querySelector('[data-testid="area-map__dot-field"]')) fail("DungeonFog", "rooms carry no metric dot field");
    if (!canvasElement.querySelector('[data-testid="area-map__schematic"]')) fail("DungeonFog", "the radial view states it is schematic");
    assertLabelsLegible(canvasElement, "DungeonFog");
  },
};

// An ordinary interior: the guild house's rooms and its door back to the
// street, whose far side reads as 通往 鐘樓廣場.
export const Interior = {
  render,
  args: { area: interiorArea(), selected: "room:7" },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const card = canvasElement.querySelector('[data-testid="area-map-detail"]');
    if (!card?.textContent.includes("通往 鐘樓廣場")) fail("Interior", "the door must read 通往 鐘樓廣場");
    if (!canvasElement.querySelector('[data-testid="area-map-detail__go"]')) fail("Interior", "the adjacent door must offer 前往");
    assertLabelsLegible(canvasElement, "Interior");
  },
};
