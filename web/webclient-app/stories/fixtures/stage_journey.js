// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The stage-transition journey (webclient-scene-transitions): a short walk
// through a five-cell street, one stop per location change. Each stop names
// the location (the place card's heading), the scene painting the backdrop
// crossfades to, the current map node the minimap pans to, the line the
// message window clears to, and the hp the vitals island reveals or hides
// on. The scene URLs are the redesign's sample paintings, which Storybook
// alone serves under `/art/showcase/` (see `.storybook/main.js`), so the real
// `art` validator accepts them.

const STREET = [
  { id: "grid:altoria:0:0", label: "南門", x: 0, y: 0 },
  { id: "grid:altoria:1:0", label: "石板廣場", x: 1, y: 0 },
  { id: "grid:altoria:1:1", label: "北岸大道", x: 1, y: 1 },
  { id: "grid:altoria:2:1", label: "西風酒館", x: 2, y: 1 },
  { id: "grid:altoria:1:2", label: "鐘樓前庭", x: 1, y: 2 },
  { id: "grid:altoria:0:2", label: "舊井巷", x: 0, y: 2 },
];

const STREET_EDGES = [
  ["grid:altoria:0:0", "grid:altoria:1:0", "東"],
  ["grid:altoria:1:0", "grid:altoria:1:1", "北"],
  ["grid:altoria:1:1", "grid:altoria:2:1", "東"],
  ["grid:altoria:1:1", "grid:altoria:1:2", "北"],
  ["grid:altoria:1:2", "grid:altoria:0:2", "西"],
];

export const STAGE_JOURNEY_STOPS = [
  {
    node: "grid:altoria:1:0",
    scene: { url: "/art/showcase/sample-town.webp", label: "石板廣場", alt: "午後陽光下的市集廣場與遠方的鐘樓" },
    command: "看看四周",
    line: "午後的陽光斜斜落在石板上，市集的紅色遮篷在風裡輕輕鼓動。遠處鐘樓的影子橫過廣場，幾個攤販正低聲討價還價。",
    hp: 100,
  },
  {
    node: "grid:altoria:1:1",
    scene: { url: "/art/showcase/sample-forest.webp", label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
    command: "往北走",
    line: "你沿著河岸往北走。兩旁的老樹把大道遮成一條綠色的長廊，河水在石堤下緩緩流過，空氣裡有青苔與溼土的氣味。",
    hp: 72,
  },
  {
    node: "grid:altoria:2:1",
    scene: { url: "/art/showcase/sample-guild.webp", label: "西風酒館", alt: "燈火溫暖的酒館大廳" },
    command: "往東走",
    line: "推開西風酒館沉重的木門，爐火的暖意撲面而來。吧檯後的店長抬頭看了你一眼，又低頭擦起手中的酒杯。",
    hp: 72,
  },
  {
    node: "grid:altoria:1:1",
    scene: { url: "/art/showcase/sample-forest.webp", label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
    command: "往西走",
    line: "你回到河岸大道。樹影比方才更長了些，一隻白鷺從水面掠過，停在對岸的淺灘上。",
    hp: 100,
  },
  {
    node: "grid:altoria:1:0",
    scene: { url: "/art/showcase/sample-town.webp", label: "石板廣場", alt: "午後陽光下的市集廣場與遠方的鐘樓" },
    command: "往南走",
    line: "廣場上的人潮散去了大半。噴泉邊只剩一位老人在餵鴿子，攤販們正一件件收起貨物。",
    hp: 100,
  },
];

// The `local_map` panel with `current` on `nodeId`: every other cell is a
// visited neighbour (the minimap's drawing, not its state ladder, is what
// the journey shows).
export function stageJourneyLocalMap(nodeId) {
  return {
    schema_version: 1,
    available: true,
    layer: "grid",
    current_node: nodeId,
    title: "伊洛瑟恩外城",
    nodes: STREET.map((cell) => ({
      id: cell.id,
      label: cell.label,
      x: cell.x,
      y: cell.y,
      visibility: cell.id === nodeId ? "current" : "visible_visited",
      current: cell.id === nodeId,
      anchor: false,
      landmark: cell.id === "grid:altoria:2:1",
      action: null,
    })),
    edges: STREET_EDGES.map(([source, destination, label]) => ({
      source,
      destination,
      label,
      known: true,
      traversable: true,
    })),
    legend: ["你目前所在的位置"],
  };
}

export function stageJourneyScene(stop) {
  return {
    archetype: null,
    label: stop.scene.label,
    subject_key: null,
    status: "done",
    url: stop.scene.url,
    aspect_ratio: "16:9",
    alt: stop.scene.alt,
    placeholder: null,
    stage: { scale: 1, x: 0, y: 0 },
  };
}
