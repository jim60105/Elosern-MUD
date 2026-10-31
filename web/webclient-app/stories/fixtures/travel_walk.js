// Synthetic wilderness cells for the travel walking slice (OpenSpec change
// wilderness-travel-walking-ui): the eager panels of one cell, whose local
// map names it as the canonical current node and whose exploration panel
// carries one direction row per step, and the schema-2 window the refresh
// owner adopts for it. The walking tests and the WildernessTravel stories
// drive the real store with them. Nothing here names shipped content.

import * as fx from "../../tests/store/protocol_fixtures.js";
import { ART_PANEL_SAMPLE, sceneBlock, sceneDescriptor } from "./art_panels.js";

function artFor(subject) {
  return { ...ART_PANEL_SAMPLE, scene: sceneBlock({}, sceneDescriptor({ subject_id: subject })) };
}

// The eight wilderness steps (canonical word, exit suffix, cell delta).
export const WALK_STEPS = Object.freeze([
  ["north", "n", 0, 1],
  ["northeast", "ne", 1, 1],
  ["east", "e", 1, 0],
  ["southeast", "se", 1, -1],
  ["south", "s", 0, -1],
  ["southwest", "sw", -1, -1],
  ["west", "w", -1, 0],
  ["northwest", "nw", -1, 1],
]);

export const walkNode = (x, y) => `wild:elosern:${x}:${y}`;

/**
 * The eager panels of a synthetic wilderness cell `(cx, cy)`: the local map
 * names the cell as the canonical current node, and the exploration panel
 * carries one direction row per step. `disabled` maps a word to a reason;
 * `withheld` lists words whose destination is not disclosed (schema 6:
 * a null destination and the generic direction label); `missing` drops a
 * word's row; `room` is the look room identity (pooled rooms reuse one);
 * `capacity` is the status v6 `travel_capacity` (null: none supplied).
 */
export function walkPanels(cx, cy, { disabled = {}, withheld = [], missing = [], room = 900, subject = null, capacity = null } = {}) {
  const steps = WALK_STEPS.filter(([word]) => !missing.includes(word));
  const current = walkNode(cx, cy);
  const localMap = {
    schema_version: 1,
    available: true,
    layer: "wilderness",
    current_node: current,
    title: "合成荒原",
    nodes: [
      { id: current, label: "合成荒原", x: cx, y: cy, visibility: "current", current: true, anchor: false, landmark: false, gateway: null, action: null },
      ...steps
        .filter(([word]) => !withheld.includes(word))
        .map(([, dir, dx, dy]) => ({
          id: walkNode(cx + dx, cy + dy),
          label: "合成荒原",
          x: cx + dx,
          y: cy + dy,
          visibility: "visible_unvisited",
          current: false,
          anchor: false,
          landmark: false,
          gateway: null,
          action: { kind: "move", exit_ref: `e_wild_${dir}`, destination: walkNode(cx + dx, cy + dy) },
        })),
    ],
    edges: [],
    legend: ["每格約一公里"],
  };
  const exploration = fx.explorationPanel({
    move: steps.map(([word, dir, dx, dy]) => ({
      exit_ref: `e_wild_${dir}`,
      label: word,
      destination: withheld.includes(word) ? null : walkNode(cx + dx, cy + dy),
      enabled: !(word in disabled),
      disabled_reason: word in disabled ? { code: "blocked", message: disabled[word] } : null,
    })),
    look: { room: { identity: room, display_name: "合成荒原", room: true }, entities: [], objects: [] },
    interact: [],
  });
  return {
    status: { ...fx.statusPanel(), travel_capacity: capacity },
    context_actions: fx.explorationActions(),
    exploration,
    local_map: localMap,
    art: artFor(subject ?? `wilderness:合成荒原:${cx},${cy}`),
  };
}

/**
 * A synthetic status v6 `travel_capacity`: per-stage foot counts, one quote
 * per walk step's opaque exit reference (`quotes` maps a word to seconds or
 * null; unlisted words quote `seconds`), and the advisory pace state.
 */
export function walkCapacity({
  normal = 14, light = 9, moderate = 6, severe = 3, seconds = 1200, quotes = {}, cautious = false, standard = false,
} = {}) {
  return {
    capacity: { normal, light, moderate, severe },
    neighbours: WALK_STEPS.map(([word, dir]) => ({
      exit_ref: `e_wild_${dir}`,
      seconds: word in quotes ? quotes[word] : seconds,
    })),
    at_pace: { cautious, standard },
  };
}

/** A schema-2 wilderness window centred on `(cx, cy)`: a revealed 3 x 3 block. */
export function walkArea(cx, cy) {
  const width = 41;
  const rows = [];
  for (let row = 0; row < width; row += 1) {
    const y = cy - 20 + row;
    rows.push(
      Math.abs(y - cy) <= 1
        ? [
            { length: 19, kind: "unknown" },
            { length: 3, kind: "terrain", terrain: "open_ground", passable: true, band: 3, tier: 0, road: false, ford: false },
            { length: 19, kind: "unknown" },
          ]
        : [{ length: width, kind: "unknown" }],
    );
  }
  const current = walkNode(cx, cy);
  const nodes = [{ id: current, label: "合成荒原", x: cx + 0.5, y: cy + 0.5, visibility: "current", visited: true, gateway: null, action: null }];
  for (const [, dir, dx, dy] of WALK_STEPS) {
    const id = walkNode(cx + dx, cy + dy);
    nodes.push({ id, label: "合成荒原", x: cx + dx + 0.5, y: cy + dy + 0.5, visibility: "seen", visited: false, gateway: null, action: { kind: "move", exit_ref: `e_wild_${dir}`, destination: id } });
  }
  return {
    schema_version: 2,
    available: true,
    layer: "wilderness",
    map_id: "elosern",
    frame: { key: "elosern", unit: "km" },
    current_node: current,
    title: "合成荒原",
    nodes,
    edges: nodes.slice(1).map((n) => ({ source: current, destination: n.id })),
    quest_markers: [],
    district_name: "合成東麓",
    cell_km: 1,
    window: { min_x: cx - 20, min_y: cy - 20, width, height: width },
    rows,
    light_phase: "day",
    ground_radius: 1,
    entities: [],
    sightings: [],
  };
}
