import { h, ref } from "vue";
import ExitCompass from "../../components/ExitCompass.vue";
import { compassArgs, explorationPanelFixture } from "../fixtures/scene_overview.js";
import { localMapAround } from "../fixtures/local_map.js";

// ExitCompass: the exploration screen's movement control
// (exploration-exit-compass; scene overview redesign §3). Exits sit on the
// pad at their bearing (gold pips) or on the dashed outer track (portal
// beads). Every story binds the compass targets the live pane derives: the
// exploration resolver's exit rows (`ExplorationMenu.exitTargets`) resolved
// against the store-shaped `localMapModel` of a synthesized `local_map` panel.
// Props: targets, busy, arrivalKey, active, motionLevel. Events: aim,
// blocked, move(item). Each story renders inside a square the height of the
// command panel at 1451x790 (about 198px).

const padBox = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          width: "198px",
          height: "198px",
          padding: "8px",
          background: "linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))",
        },
      },
      [h(story())],
    ),
});

function render(args) {
  const { localMapModel, ...props } = args;
  void localMapModel;
  return { render: () => h(ExitCompass, props) };
}

export default {
  title: "Action/ExitCompass",
  component: ExitCompass,
  decorators: [padBox],
};

const EIGHT_WAYS = [
  ["n", "北", 0, 1],
  ["ne", "東北", 1, 1],
  ["e", "東", 1, 0],
  ["se", "東南", 1, -1],
  ["s", "南", 0, -1],
  ["sw", "西南", -1, -1],
  ["w", "西", -1, 0],
  ["nw", "西北", -1, 1],
];

// The wilderness around (x, y): eight neighbours, each exit labelled by its
// canonical direction word and leading to the neighbour's node.
function wildernessAt(x, y) {
  const id = (dx, dy) => `wild:plains:${x + dx}:${y + dy}`;
  const panel = explorationPanelFixture({
    exits: EIGHT_WAYS.map(([ref, label, dx, dy]) => ({ ref: `${ref}-${x}-${y}`, label, destination: id(dx, dy) })),
  });
  const map = localMapAround({
    layer: "wilderness",
    current: [id(0, 0), "西部丘陵與谷地", x, y],
    neighbours: EIGHT_WAYS.map(([, , dx, dy]) => [id(dx, dy), "西部丘陵與谷地", x + dx, y + dy]),
  });
  return { panel, map };
}

const WILD = wildernessAt(3, 1);

export const Wilderness8Way = {
  args: compassArgs(WILD.panel, WILD.map),
  render,
};

// A town grid whose streets leave at irregular bearings (37°, 143°, 323°):
// the compass keeps the true angle instead of rounding to a cardinal.
const GRID_PANEL = explorationPanelFixture({
  exits: [
    { ref: "market", label: "市集街", destination: "grid:altoria:3:4" },
    { ref: "harbor", label: "碼頭坡道", destination: "grid:altoria:3:-4" },
    { ref: "temple", label: "神殿階梯", destination: "grid:altoria:-3:4" },
  ],
});
const GRID_MAP = localMapAround({
  layer: "grid",
  current: ["grid:altoria:0:0", "噴泉廣場", 0, 0],
  neighbours: [
    ["grid:altoria:3:4", "市集", 3, 4],
    ["grid:altoria:3:-4", "碼頭", 3, -4],
    ["grid:altoria:-3:4", "神殿", -3, 4],
  ],
});

export const GridIrregular = {
  args: compassArgs(GRID_PANEL, GRID_MAP),
  render,
};

// An interior: named doors are portals on the outer track, spread evenly in
// payload order; interior coordinates never give a bearing.
const INTERIOR_PANEL = explorationPanelFixture({
  exits: [
    { ref: "hall", label: "公會大廳", destination: "room:202" },
    { ref: "counter", label: "委託櫃檯", destination: "room:203" },
    { ref: "street", label: "大街", destination: "room:204" },
  ],
});
const INTERIOR_MAP = localMapAround({
  layer: "interior",
  current: ["room:201", "公會門廳", 0, 0],
  neighbours: [
    ["room:202", "公會大廳", 1, 0],
    ["room:203", "委託櫃檯", 0, 1],
    ["room:204", "大街", -1, 0],
  ],
});

export const InteriorPortals = {
  args: compassArgs(INTERIOR_PANEL, INTERIOR_MAP),
  render,
};

// Stairs at the same coordinates are portals pinned up (0°) and down (180°);
// a door takes neither slot.
const STAIRS_PANEL = explorationPanelFixture({
  exits: [
    { ref: "up", label: "up", destination: "grid:tower:0:0:2" },
    { ref: "down", label: "down", destination: "grid:tower:0:0:0" },
    { ref: "door", label: "塔門", destination: "grid:tower:door" },
  ],
});
const STAIRS_MAP = localMapAround({
  layer: "grid",
  current: ["grid:tower:0:0:1", "塔樓二層", 0, 0],
  neighbours: [
    ["grid:tower:0:0:2", "塔樓三層", 0, 0],
    ["grid:tower:0:0:0", "塔樓一層", 0, 0],
  ],
});

export const Stairs = {
  args: compassArgs(STAIRS_PANEL, STAIRS_MAP),
  render,
};

// A disabled exit stays aimable: a hollow dashed pip whose server-authored
// reason the readout shows; a click shakes and sends nothing.
const DISABLED_PANEL = explorationPanelFixture({
  exits: [
    { ref: "n", label: "北", destination: "wild:plains:3:2", enabled: false, reason: "前方的吊橋已經收起。" },
    { ref: "e", label: "東", destination: "wild:plains:4:1" },
  ],
});
const DISABLED_MAP = localMapAround({
  layer: "wilderness",
  current: ["wild:plains:3:1", "河岸", 3, 1],
  neighbours: [
    ["wild:plains:3:2", "吊橋", 3, 2],
    ["wild:plains:4:1", "蘆葦灘", 4, 1],
  ],
});

export const DisabledExit = {
  args: compassArgs(DISABLED_PANEL, DISABLED_MAP),
  render,
};

// Ten named portals: the 12-slot ring still has room (eleven or more switch
// to 24 slots).
const TEN_PANEL = explorationPanelFixture({
  exits: Array.from({ length: 10 }, (_, i) => ({ ref: `door-${i}`, label: `第${i + 1}號房`, destination: `room:${300 + i}` })),
});
const TEN_MAP = localMapAround({ layer: "instance", current: ["room:299", "迴廊", 0, 0] });

export const TenPortals = {
  args: compassArgs(TEN_PANEL, TEN_MAP),
  render,
};

// Walking (interactive): a wilderness without edges. Each `move` arrives
// 250 ms later with the next room's targets and a new arrival key, so hover,
// click, the rapid-click queue, and hold-to-walk behave as in the client.
function WalkingWorld(args) {
  return {
    setup() {
      const position = ref({ x: 3, y: 1 });
      const current = ref(compassArgs(WILD.panel, WILD.map));
      const busy = ref(false);
      const arrivalKey = ref(1);
      function onMove(item) {
        const way = EIGHT_WAYS.find(([ref]) => item.payload.exit_ref.startsWith(`${ref}-`));
        busy.value = true;
        setTimeout(() => {
          position.value = { x: position.value.x + way[2], y: position.value.y + way[3] };
          const next = wildernessAt(position.value.x, position.value.y);
          current.value = compassArgs(next.panel, next.map);
          arrivalKey.value += 1;
          busy.value = false;
        }, 250);
      }
      return () =>
        h(ExitCompass, {
          ...args,
          targets: current.value.targets,
          busy: busy.value,
          arrivalKey: arrivalKey.value,
          onMove,
        });
    },
  };
}

export const Walking = {
  args: { active: true, motionLevel: "full" },
  render: (args) => WalkingWorld(args),
};
