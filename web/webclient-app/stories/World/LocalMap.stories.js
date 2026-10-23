import { h } from "vue";
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
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_CIARAN_PLAZA_SAMPLE,
  LOCAL_MAP_EXTREME_RATIO_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
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
// unchanged; until a gate presentation exists the island draws it
// exactly like any other actionable node.
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

// The same-layer exits of a payload: the far ends of the current node's
// labelled edges whose id shares the current node's map key.
function sameLayerExitIds(payload) {
  const mapKey = (id) => id.split(":").slice(0, 2).join(":");
  const current = payload.current_node;
  return payload.edges
    .filter((edge) => edge.label && edge.source === current && mapKey(edge.destination) === mapKey(current))
    .map((edge) => edge.destination);
}

function assertExitsDrawn(payload, story) {
  return async ({ canvasElement }) => {
    const svg = canvasElement.querySelector('[data-testid="local-map__lattice"]');
    if (!svg) throw new Error(`${story}: lattice canvas missing`);
    const canvas = svg.getBoundingClientRect();
    const boxes = sameLayerExitIds(payload).map((id) => {
      const group = canvasElement.querySelector(`[data-node="${CSS.escape(id)}"]`);
      const marker = group?.querySelector(".local-map__marker");
      if (!marker) throw new Error(`${story}: exit ${id} has no drawn marker`);
      const box = marker.getBoundingClientRect();
      const inside =
        box.left >= canvas.left - 0.5 &&
        box.right <= canvas.right + 0.5 &&
        box.top >= canvas.top - 0.5 &&
        box.bottom <= canvas.bottom + 0.5;
      if (!inside) throw new Error(`${story}: exit ${id} marker leaves the canvas`);
      return { id, box };
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

// 南門 (gate room): the street exit 900 m north is drawn; the gate's
// cross-layer wilderness target is never drawn as a node (its exit stub is
// the gateway presentation's, label-minimap-exits-and-gateways).
export const MetricAltoriaSouthGate = {
  render: renderMap,
  args: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE) },
  play: async (context) => {
    await assertExitsDrawn(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE, "MetricAltoriaSouthGate")(context);
    if (context.canvasElement.querySelector('[data-node^="wild:"]')) {
      throw new Error("MetricAltoriaSouthGate: the cross-layer gate target must not draw as a node");
    }
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
