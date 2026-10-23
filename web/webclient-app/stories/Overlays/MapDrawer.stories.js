import { h, nextTick, onMounted, reactive, ref } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import MapDrawer from "../../components/MapDrawer.vue";
import { TOWN_IDS, dungeonArea, interiorArea, townArea, wildernessArea } from "../fixtures/area_map.js";
import { PLAYER, worldBase, worldMap, worldNewLight, newLight } from "../fixtures/world_map.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// MapDrawer (redesign-map-drawer; approved design §6, layout option A): the
// real production drawer inside the real OverlayHost shell (its own header,
// focus trap and final Escape), over synthetic, schema-valid `area_map` /
// `world_map` bodies. The prototype (`Design/WorldMap`) is the layout
// reference only and is never mounted here. A hidden <output> records the
// drawer's `move` emits and the host's closes for the play functions.

const OUTPUT = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);";

const render = (args) => ({
  setup() {
    const state = reactive({ tab: args.tab ?? "area" });
    const memory = reactive({
      area: { key: null, view: undefined, selected: args.areaSelected },
      world: {
        view: args.span ? { signature: "world|elosern|km", cx: (args.centre ?? PLAYER).x, cy: (args.centre ?? PLAYER).y, span: args.span } : undefined,
        selected: args.worldSelected,
      },
    });
    const world = ref(args.world ?? null);
    const log = reactive({ moves: [], closes: 0 });
    const drawer = ref(null);
    if (args.whole) onMounted(() => nextTick(() => drawer.value?.viewRef?.showWhole()));
    return () =>
      h("div", { style: "position:relative;height:100vh;background:var(--ink-950);" }, [
        h(
          OverlayHost,
          {
            overlay: "map",
            ownHeader: true,
            locationLabel: args.locationLabel ?? "灰岩鎮",
            onClose: () => {
              log.closes += 1;
            },
          },
          {
            default: (slot) =>
              h(MapDrawer, {
                ref: drawer,
                area: args.area ?? null,
                world: world.value,
                tab: state.tab,
                memory,
                epoch: "story|1",
                locationLabel: args.locationLabel ?? "灰岩鎮",
                busy: args.busy ?? false,
                "onUpdate:tab": (tab) => {
                  state.tab = tab;
                },
                onMove: (payload) => log.moves.push(payload),
                onClose: slot.close,
              }),
          },
        ),
        args.next
          ? h(
              "button",
              {
                type: "button",
                "data-testid": "map-drawer-story__arrive",
                style:
                  "position:fixed;z-index:200;left:50%;bottom:calc(20px * var(--ui-scale));transform:translateX(-50%);padding:6px 16px;" +
                  "color:var(--paper-50);background:rgba(20,16,12,.9);border:1px solid var(--gold-600);border-radius:999px;font-size:var(--text-xs);",
                onClick: () => {
                  world.value = args.next();
                },
              },
              "模擬：抵達新地標",
            )
          : null,
        h("output", { "data-testid": "map-drawer-story__log", style: OUTPUT }, JSON.stringify(log)),
      ]);
  },
});

export default {
  title: "Overlays/MapDrawer",
  component: MapDrawer,
  parameters: windowViewportParameters,
};

// ── play helpers (DOM only) ─────────────────────────────────────────────

const frames = (n = 2) =>
  new Promise((resolve) => {
    const step = (left) => (left <= 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
    step(n);
  });

// The pill and pointers glide to a new place over --motion-base; wait it out.
const settle = () => new Promise((resolve) => setTimeout(resolve, 450));

function fail(story, message) {
  throw new Error(`${story}: ${message}`);
}

const $ = (root, testid) => root.querySelector(`[data-testid="${testid}"]`);
const $$ = (root, testid) => [...root.querySelectorAll(`[data-testid="${testid}"]`)];

function log(root) {
  return JSON.parse($(root, "map-drawer-story__log").textContent);
}

async function key(target, name) {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true }));
  await frames();
}

async function clickPick(root, selector) {
  const el = root.querySelector(selector);
  if (!el) throw new Error(`nothing matches ${selector}`);
  const box = el.getBoundingClientRect();
  const init = { bubbles: true, button: 0, pointerId: 1, clientX: box.left + box.width / 2, clientY: box.top + box.height / 2 };
  el.dispatchEvent(new PointerEvent("pointerdown", init));
  el.dispatchEvent(new PointerEvent("pointerup", init));
  await frames();
}

// The shell: one header with the two ARIA tabs and one close control, the
// tab's caption, the pill (－ stop ＋ ⌖ 全圖 ?), the commission chip and the
// view's scale bar, every chrome text at 16 CSS px or more.
function assertShell(root, story, tab) {
  if ($$(root, "overlay-host-close").length !== 1) fail(story, "exactly one close control");
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  if (tabs.map((t) => t.getAttribute("aria-selected")).join() !== (tab === "area" ? "true,false" : "false,true")) {
    fail(story, `the ${tab} tab is the selected one`);
  }
  if (!$(root, "map-drawer-pill") || !$(root, "map-drawer-quests-toggle")) fail(story, "the floating chrome is drawn");
  if (!root.querySelector('[data-testid$="__scale-bar"]')) fail(story, "the scale bar is drawn");
  for (const el of [...root.querySelectorAll(".map-drawer__pill-button, .map-drawer__stop, .map-drawer__chip, .map-drawer__tab, .drawer-header__subtitle")]) {
    const size = Number.parseFloat(getComputedStyle(el).fontSize);
    if (!(size >= 16)) fail(story, `${el.className} renders at ${size}px`);
  }
}

// Every pointer sits inside the stage, left of an open detail card, and the
// visible ones are at most three in distance order.
function assertPointers(root, story) {
  const pointers = $$(root, "map-edge-pointer");
  if (pointers.length > 3) fail(story, `${pointers.length} pointers drawn`);
  const stage = $(root, "map-drawer-stage").getBoundingClientRect();
  const detail = root.querySelector(".area-map__detail, .world-map__detail")?.getBoundingClientRect();
  for (const p of pointers) {
    const box = p.getBoundingClientRect();
    if (box.left < stage.left - 0.5 || box.right > stage.right + 0.5 || box.top < stage.top - 0.5 || box.bottom > stage.bottom + 0.5) {
      fail(story, `pointer ${p.dataset.quest} leaves the stage`);
    }
    if (detail && box.right > detail.left + 0.5) fail(story, `pointer ${p.dataset.quest} runs under the detail card`);
  }
  const boxes = pointers.map((p) => p.getBoundingClientRect());
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      const a = boxes[i], b = boxes[j];
      if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) {
        fail(story, `commission pointers ${i} and ${j} overlap`);
      }
    }
  }
  return pointers;
}

function nearestLit() {
  const world = worldBase();
  return world.districts
    .filter((d) => d.lit)
    .map((d) => ({ id: d.id, landmark: d.landmark, dist: Math.hypot(d.landmark.x - PLAYER.x, d.landmark.y - PLAYER.y) }))
    .sort((a, b) => a.dist - b.dist)[0];
}
const nearestLitDistrict = () => nearestLit().id;

// ── option A scenarios ──────────────────────────────────────────────────

// A settlement at its opening fit, the area tab chosen.
export const A_AreaCity = {
  render,
  args: { area: townArea(), world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertShell(canvasElement, "A_AreaCity", "area");
    if (canvasElement.querySelector(".drawer-header__subtitle").textContent !== "灰岩鎮街道圖") fail("A_AreaCity", "caption names the map");
    if ($(canvasElement, "area-map-detail")) fail("A_AreaCity", "no detail card without a selection");
    const here = [...canvasElement.querySelectorAll('[data-testid="area-map__node"]')].filter((n) => n.getAttribute("aria-current") === "location");
    if (here.length !== 1) fail("A_AreaCity", "one current marker");
    // The commission elsewhere points off the map by its bearing.
    const pointers = assertPointers(canvasElement, "A_AreaCity");
    if (!pointers.some((p) => p.dataset.quest === "q_story_far")) fail("A_AreaCity", "the commission elsewhere has an edge pointer");
  },
};

export const A_AreaCityFullHd = { render, args: { area: townArea(), world: worldBase() }, ...atFullHd };

// A selected adjacent street: the ~360 px card opens, the pill and the
// pointers step left of it, and 前往 forwards the exact move.
export const A_AreaCitySelected = {
  render,
  args: { area: townArea(), world: worldBase(), areaSelected: TOWN_IDS.east },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const card = $(canvasElement, "area-map-detail");
    if (!card) fail("A_AreaCitySelected", "the detail card is open");
    await settle();
    const cardBox = canvasElement.querySelector(".area-map__detail").getBoundingClientRect();
    if (Math.abs(cardBox.width - 360) > 1) fail("A_AreaCitySelected", `card is ${cardBox.width}px wide`);
    const pill = $(canvasElement, "map-drawer-pill").getBoundingClientRect();
    if (pill.right > cardBox.left) fail("A_AreaCitySelected", "the pill steps left of the card");
    assertPointers(canvasElement, "A_AreaCitySelected");
    $(canvasElement, "area-map-detail__go").click();
    await frames();
    const moves = log(canvasElement).moves;
    if (moves.length !== 1 || moves[0].exit_ref !== "e_square_e" || moves[0].current_node !== TOWN_IDS.square) {
      fail("A_AreaCitySelected", `前往 forwards the exact move, got ${JSON.stringify(moves)}`);
    }
  },
};

// The wilderness neighbourhood: the area tab with its district caption.
export const A_AreaWilderness = {
  render,
  args: { area: wildernessArea(), world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertShell(canvasElement, "A_AreaWilderness", "area");
    if (!canvasElement.querySelector(".drawer-header__subtitle").textContent.includes("灰鬃荒原東麓")) fail("A_AreaWilderness", "caption names the district");
    if (!$$(canvasElement, "area-map__node").length) fail("A_AreaWilderness", "cells are drawn");
  },
};

// 地區 on the world tab: unlit districts hatched and nameless.
export const A_WorldRegion = {
  render,
  args: { tab: "world", area: townArea(), world: worldBase(), span: 200, centre: nearestLit().landmark },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    assertShell(canvasElement, "A_WorldRegion", "world");
    if ($(canvasElement, "map-drawer-stop").textContent !== "地區") fail("A_WorldRegion", "the pill reads 地區");
    // Hatched unlit districts share the view with the lit one and carry no
    // name: any label of theirs reads only 未探明.
    const districts = $$(canvasElement, "world-map__district");
    if (!districts.some((d) => d.dataset.lit === "false") || !districts.some((d) => d.dataset.lit === "true")) {
      fail("A_WorldRegion", "lit and unlit districts are both in view");
    }
    const unlit = $$(canvasElement, "world-map__label").filter((el) => el.dataset.kind === "unlit");
    if (unlit.some((el) => el.textContent !== "未探明")) fail("A_WorldRegion", "unlit districts read only 未探明");
    if (!$$(canvasElement, "world-map__label").some((el) => el.dataset.kind === "district")) fail("A_WorldRegion", "the lit district is named");
    const pointers = assertPointers(canvasElement, "A_WorldRegion");
    if (!pointers.length) fail("A_WorldRegion", "off-screen commissions get pointers");
    const distances = pointers.map((p) => Number.parseFloat(p.textContent.match(/([\d.]+) km/)?.[1] ?? "0"));
    if (distances.join() !== [...distances].sort((a, b) => a - b).join()) fail("A_WorldRegion", "pointers are nearest first");
  },
};

// 大陸: the whole continent at the 全圖 control.
export const A_WorldContinent = {
  render,
  args: { tab: "world", area: townArea(), world: worldBase(), whole: true },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(5);
    if ($(canvasElement, "map-drawer-stop").textContent !== "大陸") fail("A_WorldContinent", "the pill reads 大陸");
    if ($$(canvasElement, "map-edge-pointer").length) fail("A_WorldContinent", "every commission is on screen");
  },
};

export const A_WorldContinentFullHd = { render, args: { tab: "world", area: townArea(), world: worldBase(), whole: true }, ...atFullHd };

// A selected lit district: its card lists nations and places; the chrome
// steps left of it.
export const A_WorldDistrictSelected = {
  render,
  args: { tab: "world", area: townArea(), world: worldBase(), worldSelected: `district:${nearestLitDistrict()}` },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    if (!$(canvasElement, "world-map-detail")) fail("A_WorldDistrictSelected", "the detail card is open");
    await settle();
    if (!$$(canvasElement, "world-map-detail__nation").length) fail("A_WorldDistrictSelected", "the card lists the nation");
    const card = canvasElement.querySelector(".world-map__detail").getBoundingClientRect();
    if ($(canvasElement, "map-drawer-pill").getBoundingClientRect().right > card.left) fail("A_WorldDistrictSelected", "the pill steps left of the card");
    assertPointers(canvasElement, "A_WorldDistrictSelected");
  },
};

// 近郊: the trail as real cells around the player.
export const A_WorldNearby = {
  render,
  args: { tab: "world", area: townArea(), world: worldBase(), span: 40 },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    if ($(canvasElement, "map-drawer-stop").textContent !== "近郊") fail("A_WorldNearby", "the pill reads 近郊");
    if ($(canvasElement, "world-map__trail").getAttribute("data-mode") !== "cells") fail("A_WorldNearby", "the trail is drawn as cells");
  },
};

// ── slice-specific cases ────────────────────────────────────────────────

// A dungeon: the commission into fog is text only, never a pointer or node.
export const Dungeon = {
  render,
  args: { area: dungeonArea(), world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    $(canvasElement, "map-drawer-quests-toggle").click();
    await frames();
    const row = $(canvasElement, "map-drawer-quest");
    if (!row || !row.textContent.includes("尚未探明")) fail("Dungeon", "the fogged commission reads 尚未探明");
    if ($$(canvasElement, "map-edge-pointer").length) fail("Dungeon", "no pointer into fog");
  },
};

// An interior: coordinate-free rooms, commission list only.
export const Interior = {
  render,
  args: { area: interiorArea(), world: worldBase() },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    if (!canvasElement.querySelector('[data-testid="area-map__schematic"]')) fail("Interior", "the schematic caption shows");
    if ($$(canvasElement, "map-edge-pointer").length) fail("Interior", "a radial drawing has no bearing pointers");
  },
};

const quest = (id, title, tracked, x, y) => ({ id, title, tracked, x, y });

const MANY_QUESTS = [
  quest("q_near", "護送藥草商人", true, 1060.5, 1240.5),
  quest("q_far_east", "調查帝都古文書", false, 1890.5, 1330.5),
  quest("q_far_west", "西岸燈塔的求援信", false, 420.5, 1290.5),
  quest("q_far_north", "北境深林的迷途學者", false, 1220.5, 2300.5),
  quest("q_far_south", "南方港口的走私帳冊", false, 1180.5, 520.5),
  quest("q_far_ne", "東北關隘的巡邏換防", false, 1900.5, 2050.5),
];

// More than three commissions off screen with the card open: three
// pointers nearest first, the rest in ＋n, all left of the card; ＋n opens
// the commission list with every commission as text.
export const OverflowPointers = {
  render,
  args: { tab: "world", area: townArea(), world: worldMap({ quests: MANY_QUESTS }), span: 200, worldSelected: "quest:q_near" },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(4);
    await settle();
    const pointers = assertPointers(canvasElement, "OverflowPointers");
    if (pointers.length !== 3) fail("OverflowPointers", `three pointers, got ${pointers.length}`);
    const more = $(canvasElement, "map-edge-pointer-more");
    if (!more || !/^＋\d+$/.test(more.textContent)) fail("OverflowPointers", "the rest collapse into ＋n");
    more.click();
    await frames();
    const rows = $$(canvasElement, "map-drawer-quest");
    if (rows.length !== MANY_QUESTS.length) fail("OverflowPointers", "the list holds every commission");
    if (document.activeElement !== rows[0]) fail("OverflowPointers", "the list takes focus");
  },
};

// Escape unwinds one layer at a time: legend, selection, then the map.
export const LegendEscape = {
  render,
  args: { area: townArea(), world: worldBase(), areaSelected: TOWN_IDS.east },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(3);
    const toggle = $(canvasElement, "map-drawer-legend-toggle");
    toggle.click();
    await frames();
    if (getComputedStyle($(canvasElement, "map-drawer-legend")).display === "none") fail("LegendEscape", "the legend opens");
    toggle.focus();
    await key(toggle, "Escape");
    if (getComputedStyle($(canvasElement, "map-drawer-legend")).display !== "none") fail("LegendEscape", "first Escape closes the legend");
    if (!$(canvasElement, "area-map-detail")) fail("LegendEscape", "first Escape keeps the selection");
    if (document.activeElement !== toggle) fail("LegendEscape", "focus returns to the legend toggle");
    await key(toggle, "Escape");
    if ($(canvasElement, "area-map-detail")) fail("LegendEscape", "second Escape closes the selection");
    if (log(canvasElement).closes !== 0) fail("LegendEscape", "the map is still open");
    await key(toggle, "Escape");
    if (log(canvasElement).closes !== 1) fail("LegendEscape", "third Escape closes the map");
  },
};

// A district lit while the drawer is open, at reduced motion: no ink
// spread, the district simply lights, and the discovery is announced once.
export const ReducedMotionReveal = {
  render,
  args: { tab: "world", area: townArea(), world: worldBase(), span: 200, next: worldNewLight },
  ...atReference,
  play: async ({ canvasElement }) => {
    const root = document.documentElement;
    const before = root.getAttribute("data-motion");
    root.setAttribute("data-motion", "reduced");
    try {
      await frames(3);
      $(canvasElement, "map-drawer-story__arrive").click();
      await frames(3);
      if ($$(canvasElement, "world-map__ink").length) fail("ReducedMotionReveal", "reduced motion draws no ink spread");
      const lit = canvasElement.querySelector(`[data-testid="world-map__district"][data-district="${newLight().id}"]`);
      if (lit?.getAttribute("data-lit") !== "true") fail("ReducedMotionReveal", "the district is lit at once");
      if ($(canvasElement, "world-map__discovery").textContent !== `已探明：${newLight().name}`) fail("ReducedMotionReveal", "the discovery is announced");
    } finally {
      if (before === null) root.removeAttribute("data-motion");
      else root.setAttribute("data-motion", before);
    }
  },
};

// Before the first response: the drawer states that it is opening.
export const Loading = {
  render,
  args: { area: null, world: null },
  ...atReference,
  play: async ({ canvasElement }) => {
    await frames(2);
    if (!$(canvasElement, "map-drawer-loading")) fail("Loading", "the loading state shows");
  },
};
