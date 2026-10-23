import { defineComponent, h, onBeforeUnmount, ref } from "vue";
import LocalMap from "../../components/LocalMap.vue";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_ORDINARY_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_TALL_LATTICE_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  LOCAL_MAP_ALTORIA_PLAZA_SAMPLE,
  LOCAL_MAP_ALTORIA_PLAZA_GATES_SAMPLE,
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_CIARAN_PLAZA_SAMPLE,
  LOCAL_MAP_EXTREME_RATIO_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
  LOCAL_MAP_ALTORIA_SOUTH_GATE_LOCKED_SAMPLE,
  LOCAL_MAP_WILDERNESS_RETURN_SAMPLE,
  LOCAL_MAP_CROWDED_LABELS_SAMPLE,
  LOCAL_MAP_MOVE_SAME_SCALE,
  LOCAL_MAP_MOVE_LADDER,
  LOCAL_MAP_MOVE_COMPRESSION,
  localMapModelFor,
} from "../fixtures.js";

// LocalMap (H2, webclient-hud-02-status-islands, design D9/D10): the
// minimap renders as the stage's right-anchor island — bounded, the
// renderer-axis orientation legend on the lattice variant (`grid` /
// `wilderness` payloads) only, no bearing, no distance, and no full-map
// control (MapOverlay is H5's). Layout variants (webclient-map-02): the
// island draws grid/wilderness payloads as the rank-compressed lattice and
// instance/interior payloads as the model's radial placement — the variant
// comes from the model itself, so each story below renders its payload's
// own variant. The stories cover the island chrome across all four layers
// plus the minimal and unavailable forms.
//
// Wave 0 (webclient-map-00-story-fidelity): every `localMap` arg binds
// through the shared `localMapModelFor` helper — the EXACT derived shape
// `stores/elosern.js` passes in production. Raw payload args rendered a
// degenerate 1-cell lattice (no col/row/cols/rows), which is a contract
// violation, not a style choice.

// The island is a fixed 240-unit canvas inside its padded card, so the story
// frame is a column sized to that card (as the right anchor sizes it in the
// client) rather than a narrower fixed width that would clip the card.
const renderMap = (args) => ({
  render: () =>
    h("div", { style: "display: flex; flex-direction: column; width: max-content;" }, [h(LocalMap, args)]),
});

export default {
  title: "World/LocalMap",
  component: LocalMap,
};

export const FullLattice = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
};

// An ordinary town neighbourhood (webclient-map-legibility): nine distinct
// room names and no gateway, so the island draws at scale 1 and every node
// label reads at the island's 16px chrome step.
export const OrdinaryNeighbourhood = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_ORDINARY_SAMPLE),
  },
};

export const Wilderness = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE),
  },
};

export const Instance = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_INSTANCE_SAMPLE),
  },
};

export const Interior = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE),
  },
};

export const Minimal = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE),
  },
};

export const Unavailable = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE),
  },
};

// Actionable adjacent node (webclient-map-00-story-fidelity task 3.1): a
// STATIC derived-model story. The island's one actionable node (南門) carries
// the committed `move` action descriptor, and the shared renderer draws the
// actionable halo for every node that has one. The SVG node group has no
// focus state (it is not a tab stop — the island's keyboard paths are the
// full-bleed expand affordance and remembered nodes are non-focusable), so
// this story documents the committed intent without a play function and never
// interaction contract — halo present on 南門 only; click emits exactly
// `{exit_ref: "e_altoria_1_2_e", destination: "grid:altoria:2:2"}`; a node
// without an action emits nothing — is pinned by the Vitest mount tests in
// `tests/world/local_map.test.js`. 南門 also carries the required node
// `gateway` metadata (`{leads_to}`), which the model passes through
// unchanged; the island draws it with the gate arch and a second
// `通往 <leads_to>` label line (label-minimap-exits-and-gateways).
export const ActionableNode = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
};

// Edge markers with assistive text mirror (webclient-minimap-05-edge-markers-replace-list):
// On the lattice variant, remembered gateways are drawn as named edge direction
// markers, and the text alternative mirror exposes each untruncated place name
// and its octant direction word to assistive technology.
export const EdgeMarkers = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
  play: async ({ canvasElement }) => {
    const marker = canvasElement.querySelector(
      '[data-testid="local-map__edge-marker--grid:altoria:5:5"]',
    );
    if (!marker) {
      throw new Error("EdgeMarkers: edge marker is missing");
    }
    const mirror = canvasElement.querySelector(
      '[data-testid="local-map-edge-markers-mirror"]',
    );
    if (!mirror) {
      throw new Error("EdgeMarkers: assistive mirror is missing");
    }
    const mirrorItem = mirror.querySelector("li");
    if (!mirrorItem || !mirrorItem.textContent.includes("舊街區")) {
      throw new Error(`EdgeMarkers: mirror must display untruncated name, got: ${mirrorItem?.textContent}`);
    }
  },
};
export const FocusedRemembered = EdgeMarkers;

// Tall lattice (render-auto-scaled-minimap-island): the 2-col × 64-row
// unit-coordinate fixture no longer needs a window. Its two exits stand at
// one metre, closer than the exit ring allows at the finest level, so the
// island compresses: both exits at the shared radius, the two nearest
// context places as dots, everything farther omitted from the island and
// kept whole on the full map.
export const TallLatticeScaled = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE),
  },
};

// ---------------------------------------------------------------------------
// Metric islands (render-auto-scaled-minimap-island). Each story renders a
// payload view of authored metric coordinates and its play function measures
// the rendered exit markers: every same-layer exit is drawn, lies inside the
// canvas, and no two exit markers overlap.
// ---------------------------------------------------------------------------

function boxesOverlap(a, b) {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

const mapKeyOf = (id) => id.split(":").slice(0, 2).join(":");

// The current node's exits split by layer: same-map exits draw as nodes,
// cross-map exits (a gate's far side) as exit-ring stubs
// (label-minimap-exits-and-gateways).
function exitIdsOf(payload) {
  const current = payload.current_node;
  const exits = payload.edges.filter((edge) => edge.label && edge.source === current).map((edge) => edge.destination);
  return {
    same: exits.filter((id) => mapKeyOf(id) === mapKeyOf(current)),
    cross: exits.filter((id) => mapKeyOf(id) !== mapKeyOf(current)),
  };
}

function insideBox(box, canvas) {
  return (
    box.left >= canvas.left - 0.5 &&
    box.right <= canvas.right + 0.5 &&
    box.top >= canvas.top - 0.5 &&
    box.bottom <= canvas.bottom + 0.5
  );
}

// The complete exit set: every same-layer exit marker and every cross-layer
// exit-ring stub is drawn inside the canvas, no two of them overlap, no
// cross-layer target draws a node, and every exit keeps a visible label
// inside the canvas (a wilderness name repeating the current region's is the
// one information-free label that stays suppressed).
function assertExitsDrawn(payload, story) {
  return async ({ canvasElement }) => {
    const svg = canvasElement.querySelector('[data-testid="local-map__lattice"]');
    if (!svg) throw new Error(`${story}: lattice canvas missing`);
    const canvas = svg.getBoundingClientRect();
    const { same, cross } = exitIdsOf(payload);
    const currentLabel = payload.nodes.find((node) => node.id === payload.current_node)?.label;
    const boxes = same.map((id) => {
      const group = canvasElement.querySelector(`[data-node="${CSS.escape(id)}"]`);
      const marker = group?.querySelector(".local-map__marker");
      if (!marker) throw new Error(`${story}: exit ${id} has no drawn marker`);
      const box = marker.getBoundingClientRect();
      if (!insideBox(box, canvas)) throw new Error(`${story}: exit ${id} marker leaves the canvas`);
      const node = payload.nodes.find((n) => n.id === id);
      const suppressed = payload.layer === "wilderness" && node.label === currentLabel;
      const label = group.querySelector(".local-map__node-label");
      if (!suppressed) {
        if (!label || !label.textContent.trim()) throw new Error(`${story}: exit ${id} lost its label`);
        if (!insideBox(label.getBoundingClientRect(), canvas)) throw new Error(`${story}: exit ${id} label leaves the canvas`);
      }
      return { id, box };
    });
    for (const id of cross) {
      if (canvasElement.querySelector(`[data-node="${CSS.escape(id)}"]`)) {
        throw new Error(`${story}: cross-layer target ${id} must not draw as a node`);
      }
    }
    const stubs = [...canvasElement.querySelectorAll(".local-map__stub")];
    if (stubs.length !== cross.length) {
      throw new Error(`${story}: expected ${cross.length} exit stubs, found ${stubs.length}`);
    }
    stubs.forEach((stub, i) => {
      const arrow = stub.querySelector(".local-map__stub-arrow").getBoundingClientRect();
      if (!insideBox(arrow, canvas)) throw new Error(`${story}: exit stub ${i} leaves the canvas`);
      const label = stub.querySelector(".local-map__stub-label");
      if (!label || !label.textContent.trim().startsWith("通往 ")) throw new Error(`${story}: exit stub ${i} lost its 通往 label`);
      if (!insideBox(label.getBoundingClientRect(), canvas)) throw new Error(`${story}: exit stub ${i} label leaves the canvas`);
      boxes.push({ id: `stub ${i}`, box: arrow });
    });
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        if (boxesOverlap(boxes[i].box, boxes[j].box)) {
          throw new Error(`${story}: exit markers ${boxes[i].id} and ${boxes[j].id} overlap`);
        }
      }
    }
  };
}

// The island's move intents, recorded per story so a play function can
// count exactly what one activation emitted.
function moveRecorder() {
  const moves = [];
  const opens = [];
  return { moves, opens, onMove: (payload) => moves.push(payload), onOpenMap: () => opens.push(true) };
}

// Tab to the gateway stub's native button, then Enter, Space and a pointer
// click: each submits exactly one move with the target's own descriptor and
// none opens the full map.
function assertStubActivates(recorder, expected, story) {
  return async ({ canvasElement }) => {
    const button = canvasElement.querySelector('[data-testid^="local-map__stub-button--"]');
    if (!button || button.tagName !== "BUTTON") throw new Error(`${story}: actionable stub has no native button`);
    if (button.getAttribute("aria-label") !== expected.name) {
      throw new Error(`${story}: stub button is named ${button.getAttribute("aria-label")}`);
    }
    recorder.moves.length = 0;
    recorder.opens.length = 0;
    button.focus();
    if (document.activeElement !== button) throw new Error(`${story}: stub button is not focusable`);
    for (const key of ["Enter", " "]) {
      button.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    }
    button.click();
    if (recorder.moves.length !== 1) throw new Error(`${story}: one click emitted ${recorder.moves.length} moves`);
    const [move] = recorder.moves;
    if (move.exit_ref !== expected.exit_ref || move.destination !== expected.destination) {
      throw new Error(`${story}: stub emitted ${JSON.stringify(move)}`);
    }
    if (recorder.opens.length !== 0) throw new Error(`${story}: stub activation also opened the full map`);
  };
}

// 中央廣場: four exits 850–1,090 m away select the 1500 m level (uniform,
// `格距 300 m`), the two-hop streets that land on the canvas stay as quiet
// context dots, and only the four routes are drawn.
export const MetricAltoriaPlaza = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_PLAZA_SAMPLE) },
  play: assertExitsDrawn(LOCAL_MAP_ALTORIA_PLAZA_SAMPLE, "MetricAltoriaPlaza"),
};

// 村中廣場: a hamlet a few hundred metres across, drawn at a much finer level
// than the capital with the same exit ring.
export const MetricCiaranPlaza = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_CIARAN_PLAZA_SAMPLE) },
  play: assertExitsDrawn(LOCAL_MAP_CIARAN_PLAZA_SAMPLE, "MetricCiaranPlaza"),
};

// Wilderness 3x3: eight neighbours at 1 km and 1.414 km (level 2000, radii 50
// and 70.7); the shared region name is stated once.
export const MetricWilderness = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_METRIC_SAMPLE) },
  play: assertExitsDrawn(LOCAL_MAP_WILDERNESS_METRIC_SAMPLE, "MetricWilderness"),
};

// 南門 (gate room): the street exit 900 m north is drawn; the gate room
// itself wears the gate arch with its 通往 line, and the gate's cross-layer
// wilderness target is never drawn as a node: it is an exit-ring stub whose
// native button moves exactly once (label-minimap-exits-and-gateways).
const southGateMoves = moveRecorder();
export const MetricAltoriaSouthGate = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE),
    onMove: southGateMoves.onMove,
    onOpenMap: southGateMoves.onOpenMap,
  },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE, "MetricAltoriaSouthGate")(context);
    if (context.canvasElement.querySelector('[data-node^="wild:"]')) {
      throw new Error("MetricAltoriaSouthGate: the cross-layer gate target must not draw as a node");
    }
    if (!context.canvasElement.querySelector('[data-testid="local-map__gate-glyph"]')) {
      throw new Error("MetricAltoriaSouthGate: the current gate room must draw its gate glyph");
    }
    await assertStubActivates(
      southGateMoves,
      { name: "往 西部丘陵與谷地 移動", exit_ref: "e_south_gate_wild", destination: "wild:elosern:860:1076" },
      "MetricAltoriaSouthGate",
    )(context);
  },
};

// The same gate barred: the stub keeps its hollow arrow and its 通往 label,
// but offers no control, so nothing on it can submit a move.
export const MetricAltoriaSouthGateLocked = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_LOCKED_SAMPLE) },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_ALTORIA_SOUTH_GATE_LOCKED_SAMPLE, "MetricAltoriaSouthGateLocked")(context);
    if (!context.canvasElement.querySelector(".local-map__stub--locked")) {
      throw new Error("MetricAltoriaSouthGateLocked: the barred gate must keep a locked stub");
    }
    if (context.canvasElement.querySelector('[data-testid^="local-map__stub-button--"]')) {
      throw new Error("MetricAltoriaSouthGateLocked: a locked stub must offer no control");
    }
  },
};

// The wilderness side: the south gate's approach cell, whose northern
// neighbour is the gate's own grid room. The island draws it as an exit stub
// to 聖潔王都 — no city street, no grid node — and the repeated region name
// of the other neighbours stays suppressed.
const returnMoves = moveRecorder();
export const MetricWildernessReturn = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_RETURN_SAMPLE),
    onMove: returnMoves.onMove,
    onOpenMap: returnMoves.onOpenMap,
  },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_WILDERNESS_RETURN_SAMPLE, "MetricWildernessReturn")(context);
    if (context.canvasElement.querySelector('[data-node^="grid:"]')) {
      throw new Error("MetricWildernessReturn: no city node may draw on the wilderness island");
    }
    await assertStubActivates(
      returnMoves,
      { name: "往 聖潔王都 移動", exit_ref: "e_return_n", destination: "grid:capital_altoria:3050:150" },
      "MetricWildernessReturn",
    )(context);
  },
};

// An 80 m exit beside a 1.2 km one: compressed mode, labelled distance rings
// instead of dots, and the `距離壓縮` caption.
export const MetricExtremeRatio = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_EXTREME_RATIO_SAMPLE) },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_EXTREME_RATIO_SAMPLE, "MetricExtremeRatio")(context);
    const { canvasElement } = context;
    if (!canvasElement.querySelector('[data-testid="local-map__rings"]')) {
      throw new Error("MetricExtremeRatio: compressed mode must draw distance rings");
    }
    if (canvasElement.querySelector('[data-testid="local-map__dot-field"]')) {
      throw new Error("MetricExtremeRatio: compressed mode must not draw the dot field");
    }
  },
};

// Remembered gateways on the rim: smaller diamonds on the square's edge band,
// each name whole — beside its diamond when it fits there, else wrapped onto
// the next free inward row — inside the square and clear of every other name.
export const MetricRememberedGateways = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_PLAZA_GATES_SAMPLE) },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_ALTORIA_PLAZA_GATES_SAMPLE, "MetricRememberedGateways")(context);
    const svg = context.canvasElement.querySelector('[data-testid="local-map__lattice"]');
    const canvas = svg.getBoundingClientRect();
    const remembered = LOCAL_MAP_ALTORIA_PLAZA_GATES_SAMPLE.nodes.filter((n) => n.visibility === "remembered");
    const boxes = [];
    for (const node of remembered) {
      const marker = context.canvasElement.querySelector(`[data-testid="local-map__edge-marker--${CSS.escape(node.id)}"]`);
      const text = marker?.querySelector(".local-map__edge-marker-name--island");
      if (!text || text.textContent.replace(/\s+/g, "") !== node.label) {
        throw new Error(`MetricRememberedGateways: ${node.id} must show its whole name`);
      }
      for (const tspan of text.querySelectorAll("tspan")) {
        const box = tspan.getBoundingClientRect();
        if (box.left < canvas.left - 0.5 || box.right > canvas.right + 0.5 || box.top < canvas.top - 0.5 || box.bottom > canvas.bottom + 0.5) {
          throw new Error(`MetricRememberedGateways: ${node.id} name leaves the canvas`);
        }
        boxes.push({ id: node.id, box });
      }
    }
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        if (boxes[i].id !== boxes[j].id && boxesOverlap(boxes[i].box, boxes[j].box)) {
          throw new Error(`MetricRememberedGateways: names of ${boxes[i].id} and ${boxes[j].id} overlap`);
        }
      }
    }
  },
};

// A crowded crossroads: six long-named exits (one of them the east gate,
// with its gate arch and 通往 line), a long current name, context and two
// remembered gateways. Every exit keeps a label (truncated with a leader
// line where its eight spots are taken), the remembered names stay whole,
// and no drawn label crosses a marker or another label.
export const MetricCrowdedLabels = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_CROWDED_LABELS_SAMPLE) },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_CROWDED_LABELS_SAMPLE, "MetricCrowdedLabels")(context);
    const { canvasElement } = context;
    const svg = canvasElement.querySelector('[data-testid="local-map__lattice"]');
    const canvas = svg.getBoundingClientRect();
    const markers = [...svg.querySelectorAll(".local-map__marker")].map((el) => el.getBoundingClientRect());
    const labels = [...svg.querySelectorAll(".local-map__node-label")].map((el) => el.getBoundingClientRect());
    for (const label of labels) {
      if (!insideBox(label, canvas)) throw new Error("MetricCrowdedLabels: a label leaves the canvas");
      for (const marker of markers) {
        if (boxesOverlap(label, marker)) throw new Error("MetricCrowdedLabels: a label crosses a marker");
      }
    }
    for (let i = 0; i < labels.length; i += 1) {
      for (let j = i + 1; j < labels.length; j += 1) {
        if (boxesOverlap(labels[i], labels[j])) throw new Error("MetricCrowdedLabels: two labels overlap");
      }
    }
    const remembered = LOCAL_MAP_CROWDED_LABELS_SAMPLE.nodes.filter((n) => n.visibility === "remembered");
    for (const node of remembered) {
      const text = canvasElement.querySelector(
        `[data-testid="local-map__edge-marker--${CSS.escape(node.id)}"] .local-map__edge-marker-name--island`,
      );
      if (!text || text.textContent.replace(/\s+/g, "") !== node.label) {
        throw new Error(`MetricCrowdedLabels: remembered ${node.id} must show its whole name`);
      }
    }
    if (!canvasElement.querySelector('[data-testid="local-map__gate-glyph"]')) {
      throw new Error("MetricCrowdedLabels: the east gate must draw its gate glyph");
    }
  },
};

// ---------------------------------------------------------------------------
// Island movement (animate-minimap-scale-transitions; approved design §6.5).
// Each story commits one real adjacent step between two payload views, the
// way the store commits a move, at one effective motion level (written to
// `<html data-motion>` while the story is mounted, so the motion tokens
// resolve as in the client). The 走一步 / 退一步 chip is story chrome only:
// it replays the step for visual inspection (退一步 remounts the origin).
// An unchanged mode and level pans the drawing with its world-anchored dots; a changed mode or level
// dissolves at `full` and switches at once at `reduced`/`off`. After the
// motion settles every play re-runs the metric exit-inside/non-overlap
// assertions on the committed destination.
// ---------------------------------------------------------------------------

const MovementIsland = defineComponent({
  name: "MovementIsland",
  props: {
    pair: { type: Object, required: true },
    motionLevel: { type: String, default: "full" },
  },
  setup(props) {
    const root = document.documentElement;
    const previous = root.dataset.motion;
    root.dataset.motion = props.motionLevel;
    onBeforeUnmount(() => {
      if (previous === undefined) delete root.dataset.motion;
      else root.dataset.motion = previous;
    });
    const step = ref(0);
    // Stepping back remounts the island on the origin (a fresh hysteresis
    // memory), so every 走一步 replays exactly the committed step.
    const mount = ref(0);
    const models = [localMapModelFor(props.pair.from), localMapModelFor(props.pair.to)];
    return () =>
      h("div", { style: "display: flex; flex-direction: column; gap: 8px; width: max-content;" }, [
        h(
          "button",
          {
            type: "button",
            "data-testid": "story-move-step",
            style:
              "align-self: flex-end; font: inherit; font-size: var(--text-xs); color: var(--paper-300);" +
              " background: var(--panel); border: var(--line); border-radius: var(--radius-sm); padding: 2px 10px; cursor: pointer;",
            onClick: () => {
              if (step.value === 1) mount.value += 1;
              step.value = 1 - step.value;
            },
          },
          step.value === 0 ? "走一步" : "退一步",
        ),
        h(LocalMap, { key: mount.value, localMap: models[step.value], motionLevel: props.motionLevel }),
      ]);
  },
});

const renderMovement = (args) => ({ render: () => h(MovementIsland, args) });

const IDENTITY = new Set(["none", "matrix(1, 0, 0, 1, 0, 0)"]);
const panTransforms = (canvasElement) =>
  [...canvasElement.querySelectorAll(".map-lattice__pan")].map((el) => getComputedStyle(el).transform);
const leavingCopies = (canvasElement) => [...canvasElement.querySelectorAll('[data-testid="local-map__leaving"]')];
const afterFrames = (n) =>
  new Promise((resolve) => {
    const step = (left) => (left === 0 ? resolve() : requestAnimationFrame(() => step(left - 1)));
    step(n);
  });
async function until(check, story, what, timeout = 3000) {
  const start = performance.now();
  while (!check()) {
    if (performance.now() - start > timeout) throw new Error(`${story}: ${what} never happened`);
    await afterFrames(1);
  }
}

// One step at the story's level: `kind` is "pan" (unchanged mode and level)
// or "scale" (a changed one).
function assertMovement(pair, kind, level, story) {
  return async (context) => {
    const { canvasElement } = context;
    const current = () =>
      canvasElement.querySelector('.local-map__node[data-visibility="current"]')?.getAttribute("data-node");
    if (current() !== pair.from.current_node) throw new Error(`${story}: not standing on the step's origin`);
    if (level === "full" && kind === "pan") {
      canvasElement.querySelector('[data-testid="story-move-step"]').click();
      await until(() => current() === pair.to.current_node, story, "the move commit");
      // The same commit starts the pan: every pan group (the dot field
      // included) is offset, no copy is laid over the drawing.
      const field = canvasElement.querySelector('[data-testid="map-lattice__pan--field"]');
      if (!field || IDENTITY.has(getComputedStyle(field).transform)) {
        throw new Error(`${story}: the dot field must start the pan offset with the drawing`);
      }
      const transforms = new Set(panTransforms(canvasElement));
      if (transforms.size !== 1) throw new Error(`${story}: the pan groups must move as one shape`);
      if (leavingCopies(canvasElement).length !== 0) throw new Error(`${story}: an equal-scale step must not dissolve`);
      await until(() => panTransforms(canvasElement).every((t) => IDENTITY.has(t)), story, "the pan settling");
    } else if (level === "full") {
      canvasElement.querySelector('[data-testid="story-move-step"]').click();
      await until(() => current() === pair.to.current_node, story, "the move commit");
      const copies = leavingCopies(canvasElement);
      if (copies.length !== 1) throw new Error(`${story}: a scale change must lay one dissolving copy, found ${copies.length}`);
      const [copy] = copies;
      // SVG elements have no `inert` property; the HTML host carries the real
      // inertness and the copy repeats it as an attribute.
      const hostEl = copy.parentElement;
      if (!hostEl?.inert || !copy.hasAttribute("inert") || copy.getAttribute("aria-hidden") !== "true" || hostEl.getAttribute("aria-hidden") !== "true") {
        throw new Error(`${story}: the leaving copy must be inert and hidden`);
      }
      if (copy.querySelector("[data-node], [data-testid], button")) throw new Error(`${story}: the copy kept an identity`);
      if (!panTransforms(canvasElement).every((t) => IDENTITY.has(t))) {
        throw new Error(`${story}: a scale change must never pan`);
      }
      await until(() => leavingCopies(canvasElement).length === 0, story, "the dissolve ending");
    } else {
      canvasElement.querySelector('[data-testid="story-move-step"]').click();
      await until(() => current() === pair.to.current_node, story, "the move commit");
      await afterFrames(2);
      if (leavingCopies(canvasElement).length !== 0) throw new Error(`${story}: ${level} must leave no previous frame`);
      if (!panTransforms(canvasElement).every((t) => IDENTITY.has(t))) {
        throw new Error(`${story}: ${level} must show the new placement at once`);
      }
    }
    await assertExitsDrawn(pair.to, story)(context);
  };
}

// 中央廣場 → 大道北段: both at the 1500 m level (格距 300 m). The ground pans
// with the drawing, so the dots slide under the player instead of standing
// still behind the moving routes.
export const MetricMoveSameScale = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_SAME_SCALE, motionLevel: "full" },
  play: assertMovement(LOCAL_MAP_MOVE_SAME_SCALE, "pan", "full", "MetricMoveSameScale"),
};

// The same step at reduced: no travel, the new placement at once.
export const MetricMoveSameScaleReduced = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_SAME_SCALE, motionLevel: "reduced" },
  play: assertMovement(LOCAL_MAP_MOVE_SAME_SCALE, "pan", "reduced", "MetricMoveSameScaleReduced"),
};

// 市場街 → 工匠巷: the 1.2 km exits need the 2000 m level (格距 400 m), a
// ladder boundary. Full motion dissolves the 300 m frame into the 400 m one.
export const MetricMoveLadder = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_LADDER, motionLevel: "full" },
  play: assertMovement(LOCAL_MAP_MOVE_LADDER, "scale", "full", "MetricMoveLadder"),
};

// The ladder step at reduced: the new scale at once, no dissolve.
export const MetricMoveLadderReduced = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_LADDER, motionLevel: "reduced" },
  play: assertMovement(LOCAL_MAP_MOVE_LADDER, "scale", "reduced", "MetricMoveLadderReduced"),
};

// The compressed frontier post → its uniform watchtower: distance rings give
// way to the dot field through the dissolve.
export const MetricMoveCompression = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_COMPRESSION, motionLevel: "full" },
  play: assertMovement(LOCAL_MAP_MOVE_COMPRESSION, "scale", "full", "MetricMoveCompression"),
};

// The mode switch with motion off: the final projection in the commit frame.
export const MetricMoveCompressionOff = {
  render: renderMovement,
  args: { pair: LOCAL_MAP_MOVE_COMPRESSION, motionLevel: "off" },
  play: assertMovement(LOCAL_MAP_MOVE_COMPRESSION, "scale", "off", "MetricMoveCompressionOff"),
};
