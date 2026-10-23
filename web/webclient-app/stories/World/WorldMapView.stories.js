import { h, nextTick, onMounted, ref } from "vue";
import WorldMapView from "../../components/WorldMapView.vue";
import {
  FOREST_ID,
  FOREST_LANDMARK,
  QUEST_IDS,
  newLight,
  worldBase,
  worldCoarseTrail,
  worldForestLit,
  worldNewLight,
} from "../fixtures/world_map.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// WorldMapView (render-world-map-view): the real world-tab renderer over
// synthetic, schema-valid `world_map` v1 bodies (the Vitest suite validates
// every fixture with the wire validator). The frame stands in for the map
// drawer's body at the 1451x790 reference; the drawer header, pill, quest
// dropdown and edge pointers belong to the later MapDrawer change.
//
// The discovery stories carry a small harness bar above the map: its
// button stands in for the server republishing the panel after the player
// reaches a landmark, so the reveal is observed while the map is open.

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

const HARNESS = [
  "position: absolute; z-index: 5; top: calc(14px * var(--ui-scale)); right: calc(14px * var(--ui-scale));",
  "padding: calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale));",
  "color: var(--paper-50); font-family: var(--f-display); font-size: var(--text-xs); letter-spacing: 0.16em;",
  "background: rgba(20, 16, 12, 0.86); border: 1px solid var(--gold-600); border-radius: 999px; cursor: pointer;",
].join("");

const render = (args) => ({
  setup() {
    const world = ref(args.world);
    const selected = ref(args.selected ?? null);
    const view = ref(undefined);
    const map = ref(null);
    // `whole` opens at 大陸 through the component's own control, the same
    // call the host's 全圖 button makes.
    if (args.whole) onMounted(() => nextTick(() => map.value?.showWhole()));
    if (args.span) {
      const centre = args.centre ?? args.world.current;
      view.value = { signature: "world|elosern|km", cx: centre.x, cy: centre.y, span: args.span };
    }
    return () =>
      h("div", { style: FRAME }, [
        h(WorldMapView, {
          ref: map,
          world: world.value,
          view: view.value,
          selected: selected.value,
          "onUpdate:view": (next) => {
            view.value = next;
          },
          "onUpdate:selected": (key) => {
            selected.value = key;
          },
        }),
        args.next
          ? h(
              "button",
              {
                type: "button",
                style: HARNESS,
                "data-testid": "world-map-story__arrive",
                onClick: () => {
                  world.value = args.next();
                },
              },
              "模擬：抵達新地標",
            )
          : null,
      ]);
  },
});

export default {
  title: "World/WorldMapView",
  component: WorldMapView,
  parameters: windowViewportParameters,
};

// ── play helpers (DOM only) ─────────────────────────────────────────────

const frames = (n = 2) =>
  new Promise((resolve) => {
    const step = (left) => (left <= 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
    step(n);
  });
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function fail(story, message) {
  throw new Error(`${story}: ${message}`);
}

function labels(root) {
  return [...root.querySelectorAll('[data-testid="world-map__label"]')];
}

const LAYERS = [
  "sea", "land", "lit-terrain", "unlit-hatching", "district-borders", "national-borders", "coastline",
  "trail", "approximate-quests", "places-landmarks", "quest-markers", "current", "labels", "chrome",
];

function assertLayerOrder(root, story) {
  const svg = root.querySelector('[data-testid="world-map__svg"]');
  const order = [...svg.children].map((el) => el.getAttribute("data-layer")).filter(Boolean);
  if (order.join(",") !== LAYERS.join(",")) fail(story, `layer order ${order.join(",")}`);
}

// Every drawn label is at least 16 CSS px, whole, and no two drawn labels overlap.
function assertLabelsLegible(root, story) {
  const boxes = labels(root).map((el) => ({ el, box: el.getBoundingClientRect() }));
  if (!boxes.length) fail(story, "no label is drawn");
  for (const { el } of boxes) {
    const size = Number.parseFloat(getComputedStyle(el).fontSize);
    if (!(size >= 16)) fail(story, `label ${el.textContent} renders at ${size}px`);
    if (el.textContent.includes("…")) fail(story, `label ${el.textContent} is truncated`);
  }
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      const a = boxes[i].box;
      const b = boxes[j].box;
      if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) {
        fail(story, `labels ${boxes[i].el.textContent} and ${boxes[j].el.textContent} overlap`);
      }
    }
  }
}

function labelKinds(root) {
  return new Set(labels(root).map((el) => el.getAttribute("data-kind")));
}

async function clickPick(root, key) {
  const el = root.querySelector(`[data-pick="${key}"]`);
  if (!el) throw new Error(`no element picks ${key}`);
  const box = el.getBoundingClientRect();
  const init = { bubbles: true, button: 0, pointerId: 1, clientX: box.left + box.width / 2, clientY: box.top + box.height / 2 };
  el.dispatchEvent(new PointerEvent("pointerdown", init));
  el.dispatchEvent(new PointerEvent("pointerup", init));
  await frames();
}

// ── stories ─────────────────────────────────────────────────────────────

// The opening view (design §6.4): 國 centred between the player and the
// tracked commission, with the nation names, the lit Altoria districts
// named over their terrain ink, the hatched remainder, the dash-dot
// national borders and the walked trail as a line.
export const Country = {
  render,
  args: { world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertLayerOrder(canvasElement, "Country");
    assertLabelsLegible(canvasElement, "Country");
    const kinds = labelKinds(canvasElement);
    if (!kinds.has("district") || !kinds.has("place")) fail("Country", "district and place names show at 國");
    if (kinds.has("unlit")) fail("Country", "未探明 must wait for spans of 450 km or less");
    const trail = canvasElement.querySelector('[data-testid="world-map__trail"]');
    if (trail.getAttribute("data-mode") !== "line") fail("Country", "the trail is a line at 國");
    if (canvasElement.querySelector('[data-testid="world-map__stop"]').textContent !== "國") fail("Country", "the pill caption reads 國");
  },
};

export const CountryFullHd = { render, args: { world: worldBase() }, ...atFullHd };

// 大陸: the whole continent fits; only nation names and commissions remain.
export const Continent = {
  render,
  args: { world: worldBase(), whole: true },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(4);
    if (canvasElement.querySelector('[data-testid="world-map__stop"]').textContent !== "大陸") fail("Continent", "the pill caption reads 大陸");
    assertLabelsLegible(canvasElement, "Continent");
    const kinds = labelKinds(canvasElement);
    if (!kinds.has("nation")) fail("Continent", "nation names show at 大陸");
    if (kinds.has("district") || kinds.has("place") || kinds.has("unlit")) fail("Continent", "names above 1000 km must hide");
  },
};

// 地區 over the frontier: 未探明 labels appear over the hatched districts,
// which carry no name, landmark or place, and the approximate commission is
// a dashed circle labelled 大致方位.
export const UnlitFrontier = {
  render,
  args: { world: worldBase(), span: 420, centre: { x: 1300, y: 1380 } },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertLabelsLegible(canvasElement, "UnlitFrontier");
    const unlit = labels(canvasElement).filter((el) => el.getAttribute("data-kind") === "unlit");
    if (!unlit.length || unlit.some((el) => el.textContent !== "未探明")) fail("UnlitFrontier", "unlit districts read only 未探明");
    for (const path of canvasElement.querySelectorAll('[data-lit="false"]')) {
      const id = path.getAttribute("data-district");
      if (canvasElement.querySelector(`[data-testid="world-map__landmark"][data-pick="district:${id}"]`)) {
        fail("UnlitFrontier", "an unlit district must draw no landmark");
      }
    }
    const approx = canvasElement.querySelector(`[data-testid="world-map__approx"][data-quest="${QUEST_IDS.nearApproximate}"]`);
    if (!approx) fail("UnlitFrontier", "the approximate commission draws its circle");
    if (canvasElement.querySelector(`[data-testid="world-map__quest"][data-quest="${QUEST_IDS.nearApproximate}"]`)) {
      fail("UnlitFrontier", "an approximate commission has no exact pin");
    }
    const label = labels(canvasElement).find((el) => el.getAttribute("data-label-for") === `quest:${QUEST_IDS.nearApproximate}`);
    if (!label?.textContent.includes("大致方位")) fail("UnlitFrontier", "the circle is labelled 大致方位");
  },
};

// 近郊: the trail becomes its 1 km cells.
export const Nearby = {
  render,
  args: { world: worldBase(), span: 40 },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const trail = canvasElement.querySelector('[data-testid="world-map__trail"]');
    if (trail.getAttribute("data-mode") !== "cells" || trail.getAttribute("data-resolution-km") !== "1") {
      fail("Nearby", "the 近郊 trail is drawn as 1 km cells");
    }
  },
};

// 近郊 with a downsampled history: the cells are 5 km squares, never 1 km.
export const NearbyCoarseTrail = {
  render,
  args: { world: worldCoarseTrail(), span: 40 },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const trail = canvasElement.querySelector('[data-testid="world-map__trail"]');
    if (trail.getAttribute("data-resolution-km") !== "5") fail("NearbyCoarseTrail", "the trail keeps its 5 km resolution");
    const d = trail.querySelector(".world-map__trail-cells").getAttribute("d");
    const cells = d.match(/v-?\d+/g) ?? [];
    if (!cells.length || cells.some((v) => v !== "v5")) fail("NearbyCoarseTrail", "each cell is 5 km tall");
  },
};

// The deep forest after its landmark was reached: one district that lists
// both nations, with no national border drawn inside it.
export const SelectedForest = {
  render,
  args: { world: worldForestLit(), selected: `district:${FOREST_ID}`, span: 800, centre: FOREST_LANDMARK },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const nations = [...canvasElement.querySelectorAll('[data-testid="world-map-detail__nation"]')].map((el) => el.textContent);
    if (nations.join("、") !== "格蘭迪亞帝國、瓦爾哈拉獸王國") fail("SelectedForest", `both nations listed, got ${nations}`);
    if (canvasElement.querySelector('[data-testid="world-map-detail__title"]').textContent !== "北境深林") {
      fail("SelectedForest", "the lit forest reads its supplied name");
    }
    assertLabelsLegible(canvasElement, "SelectedForest");
  },
};

// A commission picked on the map: its reading is mirrored as text.
export const SelectedQuest = {
  render,
  args: { world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    await clickPick(canvasElement, `quest:${QUEST_IDS.exact}`);
    const title = canvasElement.querySelector('[data-testid="world-map-detail__title"]')?.textContent;
    if (title !== "護送藥草商人") fail("SelectedQuest", "the commission reading opens");
    if (!canvasElement.querySelector('[data-testid="world-map-detail"]').textContent.includes("精確位置")) {
      fail("SelectedQuest", "an exact commission states its precision");
    }
    if (canvasElement.querySelector('[data-testid="world-map__live"]').textContent !== "已選取：護送藥草商人") {
      fail("SelectedQuest", "the selection is announced");
    }
  },
};

// An unlit district picked on the map stays nameless.
export const SelectedUnlit = {
  render,
  args: { world: worldBase(), span: 420, centre: { x: 1300, y: 1380 } },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const unlit = newLight();
    await clickPick(canvasElement, `district:${unlit.id}`);
    const card = canvasElement.querySelector('[data-testid="world-map-detail"]');
    if (canvasElement.querySelector('[data-testid="world-map-detail__title"]').textContent !== "未探明") fail("SelectedUnlit", "unlit reads 未探明");
    if (card.textContent.includes(unlit.name) || card.textContent.includes(unlit.landmark.name)) fail("SelectedUnlit", "no undisclosed name");
    if (card.querySelector('[data-testid="world-map-detail__nation"]')) fail("SelectedUnlit", "no nation claim for an unlit district");
  },
};

// The keyboard path: real buttons; focus rings the feature on the map and
// Enter opens its reading.
export const KeyboardFeatures = {
  render,
  args: { world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const first = canvasElement.querySelector('[data-feature][tabindex="0"]');
    first.focus();
    first.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    await frames();
    const active = document.activeElement;
    if (!active?.hasAttribute("data-feature") || active === first) fail("KeyboardFeatures", "ArrowDown moves to the next feature");
    if (!canvasElement.querySelector('[data-testid="world-map__focus-ring"]')) fail("KeyboardFeatures", "focus rings the feature on the map");
    active.click();
    await frames();
    if (!canvasElement.querySelector('[data-testid="world-map-detail"]')) fail("KeyboardFeatures", "Enter/click opens the reading");
  },
};

// A district lights while the map is open: its ink spreads from the
// landmark for 600 ms and 已探明 is announced once.
export const NewlyLit = {
  render,
  args: { world: worldBase(), next: worldNewLight, span: 420, centre: { x: 1220, y: 1340 } },
  ...atReference,
  play: async ({ canvasElement }) => {
    document.documentElement.removeAttribute("data-motion");
    await frames(3);
    if (canvasElement.querySelector('[data-testid="world-map__ink"]')) fail("NewlyLit", "the initial payload replays nothing");
    if (canvasElement.querySelector('[data-testid="world-map__discovery"]').textContent) fail("NewlyLit", "nothing announced on load");
    canvasElement.querySelector('[data-testid="world-map-story__arrive"]').click();
    await frames(2);
    const lit = newLight();
    const ink = canvasElement.querySelector('[data-testid="world-map__ink"]');
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) {
      if (!ink || ink.getAttribute("data-district") !== lit.id || ink.getAttribute("data-reveal-ms") !== "600") {
        fail("NewlyLit", "a 600 ms ink spread starts at the new district's landmark");
      }
    }
    await wait(80);
    if (canvasElement.querySelector('[data-testid="world-map__discovery"]').textContent !== `已探明：${lit.name}`) {
      fail("NewlyLit", "one 已探明 announcement");
    }
    await wait(700);
    if (canvasElement.querySelector('[data-testid="world-map__ink"]')) fail("NewlyLit", "the ink mask clears after the spread");
  },
};

// The same discovery under reduced motion: the district lights instantly,
// and the announcement still reads.
export const NewlyLitReducedMotion = {
  render,
  args: { world: worldBase(), next: worldNewLight, span: 420, centre: { x: 1220, y: 1340 } },
  ...atReference,
  play: async ({ canvasElement }) => {
    document.documentElement.setAttribute("data-motion", "reduced");
    try {
      await frames(3);
      canvasElement.querySelector('[data-testid="world-map-story__arrive"]').click();
      await frames(2);
      if (canvasElement.querySelector('[data-testid="world-map__ink"]')) fail("NewlyLitReducedMotion", "reduced motion lights instantly");
      const lit = newLight();
      const district = canvasElement.querySelector(`[data-testid="world-map__district"][data-district="${lit.id}"]`);
      if (district?.getAttribute("data-lit") !== "true") fail("NewlyLitReducedMotion", "the district is lit at once");
      await wait(80);
      if (canvasElement.querySelector('[data-testid="world-map__discovery"]').textContent !== `已探明：${lit.name}`) {
        fail("NewlyLitReducedMotion", "the announcement still reads");
      }
    } finally {
      document.documentElement.removeAttribute("data-motion");
    }
  },
};
