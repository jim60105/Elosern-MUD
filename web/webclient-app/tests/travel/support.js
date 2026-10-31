// Shared harness for the travel suites (wilderness-travel-interface): the real
// composed store behind a fake sender, synthetic committed panels and the
// mounted AppClient. Every body passes the real wire validators.

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";
import { ART_PANEL_SAMPLE, sceneBlock, sceneDescriptor } from "../../stories/fixtures/art_panels.js";
import { LOCAL_MAP_WILDERNESS_METRIC_SAMPLE } from "../../stories/fixtures.js";
import { wildernessArea } from "../../stories/fixtures/area_map.js";

export { fx, wildernessArea };

export const WILD_SUBJECT = "wilderness:合成荒原:100,200";
export const TOWN_SUBJECT = "grid:t_synth_map:2,0";

/** A committed `art` panel whose scene names `subject`. */
export function artFor(subject) {
  return { ...ART_PANEL_SAMPLE, scene: sceneBlock({}, sceneDescriptor({ subject_id: subject })) };
}

export const tick = async () => {
  await nextTick();
  await nextTick();
};

/** The eager panels of one exploration publication at `subject`. */
export function panelsAt(subject, extra = {}) {
  return {
    status: fx.statusPanel(),
    context_actions: fx.explorationActions(),
    exploration: fx.explorationPanel(),
    local_map: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
    art: artFor(subject),
    ...extra,
  };
}

/**
 * The live harness: a store established at `subject` and, unless `mounted`
 * is false, the AppClient attached to the document.
 */
export function liveTravel({ subject = WILD_SUBJECT, panels = null, mounted = true, wrappers = [] } = {}) {
  setActivePinia(createPinia());
  const store = useElosernStore();
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  accept("ui_snapshot", fx.snapshot({ panels: panels ?? panelsAt(subject) }));
  let w = null;
  if (mounted) {
    w = mount(AppClient, { attachTo: document.body });
    wrappers.push(w);
  }
  const mapViews = () => sender.sent.actions.filter((a) => a.action_id === "map.view");
  /** The next consecutive revision. */
  const next = () => store.view.revision + 1;
  /** An update of `panels` at the next revision. */
  const publish = (bodyPanels, overrides = {}) => {
    const revision = next();
    accept("ui_update", fx.update({ revision, panels: bodyPanels, ...overrides }));
    return revision;
  };
  /** The result of `request` declaring `revision`. */
  const result = (request, revision, outcome = "success", code = "completed") =>
    accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: revision, outcome, code,
      ...(outcome === "success" ? {} : { message: "無法讀取地圖" }),
    }));
  /** Answer the last map.view with `area` in the given order. */
  const answerMap = async (area, order = "body-first") => {
    const request = mapViews().at(-1);
    const revision = next();
    if (order === "result-first") {
      result(request, revision);
      await tick();
    }
    accept("ui_update", fx.update({ revision, panels: { area_map: area } }));
    await tick();
    if (order === "body-first") {
      result(request, revision);
      await tick();
    }
    return revision;
  };
  return { store, sender, w, accept, publish, result, answerMap, mapViews, next };
}

// ── the walking slice (wilderness-travel-walking-ui) ─────────────────────

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
 * word's row; `room` is the look room identity (pooled rooms reuse one).
 */
export function walkPanels(cx, cy, { disabled = {}, withheld = [], missing = [], room = 900, subject = null } = {}) {
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
    status: fx.statusPanel(),
    context_actions: fx.explorationActions(),
    exploration,
    local_map: localMap,
    art: artFor(subject ?? `wilderness:合成荒原:${cx},${cy}`),
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
