// Synthetic mock world for the map-editor design prototype
// (docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md §7).
// Reference only: names and IDs are illustrative, not the authored world.

export const DOMAINS = [
  { key: "continent", label: "大陸", hotkey: "1" },
  { key: "settlement", label: "據點", hotkey: "2" },
  { key: "interior", label: "室內", hotkey: "3" },
];

export const TOOLS = {
  continent: [
    { key: "select", label: "選取", glyph: "⌖", hotkey: "V" },
    { key: "point", label: "加控制點", glyph: "◇", hotkey: "A" },
    { key: "waterway", label: "水系", glyph: "⌇" },
    { key: "ridge", label: "山脊", glyph: "⛰" },
    { key: "location", label: "地點", glyph: "▲" },
    { key: "footprint", label: "佔地", glyph: "▦" },
  ],
  settlement: [
    { key: "select", label: "選取", glyph: "⌖", hotkey: "V" },
    { key: "node", label: "節點", glyph: "●", hotkey: "N" },
    { key: "road", label: "道路", glyph: "⟶", hotkey: "R" },
    { key: "entrance", label: "入口", glyph: "⌂", hotkey: "E" },
  ],
  interior: [
    { key: "select", label: "選取", glyph: "⌖", hotkey: "V" },
    { key: "room", label: "房間", glyph: "▢", hotkey: "N" },
    { key: "connect", label: "連接", glyph: "⟶", hotkey: "R" },
    { key: "entrance", label: "外部入口", glyph: "⌂", hotkey: "E" },
    { key: "arrange", label: "自動排列", glyph: "⇲" },
  ],
};

export const WORLD_TREE = [
  { id: "continent", label: "艾洛森大陸", depth: 0, domain: "continent" },
  { id: "loc:greyrock", label: "灰岩鎮", depth: 1, tag: "據點" },
  { id: "settlement", label: "街道圖", depth: 2, domain: "settlement" },
  { id: "interior", label: "鍛冶工坊", depth: 2, tag: "室內", domain: "interior" },
  { id: "int:belltower", label: "鐘樓", depth: 2, tag: "室內" },
  { id: "loc:mistvale", label: "霧谷丘陵", depth: 1, tag: "無本地圖" },
  { id: "loc:goldear", label: "金穗帝都", depth: 1, tag: "據點" },
  { id: "loc:longname", label: "聖詠者紀念碑與白石長階下的舊朝聖驛站", depth: 1, tag: "無本地圖" },
];

// ---------------------------------------------------------------- settlement
export const SETTLEMENT = {
  id: "greyrock_town",
  name: "灰岩鎮",
  map: "街道圖",
  path: "content/maps/settlements/greyrock_town.yaml",
  nodes: [
    { id: "bell_square", name: "鐘樓廣場", e: 0, n: 0, prototype: "plaza", scene: "scene:greyrock_square" },
    { id: "north_gate_ave", name: "北門大道", e: 0, n: 65, prototype: "street", scene: "scene:greyrock_avenue", desc: "石板大道直通北門，兩側是掛著鐵製招牌的老店鋪；清晨常有運貨的驢車經過。" },
    { id: "north_gate", name: "北門", e: 0, n: 130, prototype: "gate", gate: "通往 霧谷丘陵" },
    { id: "old_well_lane", name: "舊井巷", e: -45, n: 0, prototype: "lane" },
    { id: "watermill", name: "水車磨坊", e: -95, n: 0, prototype: "mill" },
    { id: "memorial", name: "聖詠者紀念碑與白石長階", e: -95, n: 70, prototype: "landmark", unfinished: true },
    { id: "copper_street", name: "銅匠街", e: 40, n: 0, prototype: "street" },
    { id: "academy_cloister", name: "學院迴廊", e: 115, n: 40, prototype: "cloister" },
    { id: "riverside_pier", name: "河岸碼頭", e: 0, n: -75, prototype: "pier" },
  ],
  roads: [
    ["bell_square", "north_gate_ave", "北"], ["north_gate_ave", "bell_square", "南"],
    ["north_gate_ave", "north_gate", "北"], ["north_gate", "north_gate_ave", "南"],
    ["bell_square", "old_well_lane", "西"], ["old_well_lane", "bell_square", "東"],
    ["old_well_lane", "watermill", "西"], ["watermill", "old_well_lane", "東"],
    ["bell_square", "copper_street", "東"], ["copper_street", "bell_square", "西"],
    ["copper_street", "academy_cloister", "東北"], ["academy_cloister", "copper_street", "西南"],
    ["bell_square", "riverside_pier", "南"], ["riverside_pier", "bell_square", "北"],
    ["watermill", "memorial", "北"],
  ],
  // Incoming references by node, for the inspector and delete refusal.
  references: {
    north_gate_ave: [
      { kind: "入口", label: "鍛冶工坊 · 前店 ⇄ 北門大道", source: "content/maps/interiors/greyrock_forge.yaml", target: "entrance" },
      { kind: "任務", label: "霧谷的失蹤羊群", source: "world/quests/mistvale_sheep.py（外部索引）" },
    ],
    north_gate: [
      { kind: "野外入口", label: "北門 → 野外格 (1284, 2034)", source: "content/maps/settlements/greyrock_town.yaml" },
    ],
  },
};

// ---------------------------------------------------------------- continent
export const CONTINENT = {
  path: "content/maps/continent.yaml",
  coast: "M210 90 C330 40 520 60 600 140 C690 230 650 380 600 450 C520 530 330 520 250 450 C170 380 120 160 210 90Z",
  partition: ["M260 120 L330 240 L250 330", "M330 240 L470 230 L560 160", "M470 230 L500 380 L420 480", "M330 240 L380 380 L500 380"],
  ridge: "M480 110 L540 170 L580 260",
  waterways: [
    {
      id: "frost_creek",
      name: "霜溪",
      // Control points in geographic kilometres (east, north) and their
      // projected canvas position.
      points: [
        { e: 1281.0, n: 2210.0, x: 300, y: 70 },
        { e: 1279.5, n: 2163.0, x: 285, y: 163 },
        { e: 1281.2, n: 2120.4, x: 290, y: 210 },
        { e: 1283.0, n: 2088.0, x: 296, y: 236 },
        { e: 1284.0, n: 2031.5, x: 300, y: 250 },
        { e: 1290.4, n: 1990.0, x: 345, y: 320 },
        { e: 1288.0, n: 1930.0, x: 360, y: 400 },
        { e: 1286.0, n: 1880.0, x: 345, y: 470 },
        { e: 1287.0, n: 1860.0, x: 350, y: 520 },
      ],
      path: "M300 70 C310 140 270 190 300 250 S380 330 360 400 S330 470 350 520",
    },
    { id: "silverscale", name: "銀鱗河" },
    { id: "greyrock_branch", name: "灰岩支流" },
  ],
  locations: [
    { id: "greyrock", name: "灰岩鎮", x: 418, y: 285, local: true },
    { id: "mistvale", name: "霧谷丘陵", x: 520, y: 320, local: false },
  ],
  layers: [
    { key: "terrain", label: "地形與通行", on: true },
    { key: "water", label: "水系", on: true },
    { key: "ridge", label: "山脊・隘口・渡口", on: true },
    { key: "locations", label: "地點", on: true },
    { key: "footprint", label: "據點佔地", on: false },
    { key: "partition", label: "分區（衍生・唯讀）", on: true },
  ],
};

// ---------------------------------------------------------------- interior
export const INTERIOR = {
  id: "greyrock_forge",
  name: "鍛冶工坊",
  path: "content/maps/interiors/greyrock_forge.yaml",
  layoutPath: "content/map-editor-layouts/greyrock_forge.yaml",
  service: "greyrock_smithy",
  rooms: [
    { id: "shopfront", name: "前店", x: 230, y: 300, scene: "scene:forge_front" },
    { id: "furnace_room", name: "熔爐間", x: 480, y: 200, scene: "scene:forge_furnace", desc: "爐火映紅了石牆，鐵砧旁堆滿待修的鎧甲與斷刃。牆角的水槽冒著白煙，學徒正把剛淬火的劍胚排上木架。" },
    { id: "loft", name: "師傅的閣樓", x: 640, y: 90 },
    { id: "storeroom", name: "原料倉", x: 650, y: 360 },
  ],
  exterior: { id: "ext", name: "街道圖", sub: "北門大道", x: 170, y: 450 },
  connections: [
    { from: "shopfront", to: "furnace_room", dir: "東", back: "西" },
    { from: "furnace_room", to: "loft", dir: "上" },
    { from: "furnace_room", to: "storeroom", dir: "東", back: "西" },
    { from: "shopfront", to: "ext", dir: "出", back: "入" },
  ],
};

export const ENTRANCE = {
  owner: "interior:greyrock_forge",
  outer: { domain: "據點", ref: "settlement:greyrock_town/north_gate_ave", label: "入" },
  inner: { domain: "室內", ref: "interior:greyrock_forge/shopfront", label: "出" },
};

export const DIAGNOSTICS = [
  { cls: "error", glyph: "✕", text: "道路 bell_square → north_gate_ave 的方向「北」與 north_gate_ave → north_gate 重複", where: "greyrock_town.yaml:84 · roads[3].direction", target: "north_gate_ave" },
  { cls: "warn", glyph: "▲", text: "地標「聖詠者紀念碑與白石長階」無法從城門抵達", where: "greyrock_town.yaml:131 · nodes.memorial", target: "memorial" },
  { cls: "warn", glyph: "▲", text: "分區輸出屬於舊輸入 r41（現行 r43）", where: "world/maps/data/district_partition.json", target: null },
];
