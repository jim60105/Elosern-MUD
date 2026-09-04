import { h } from "vue";
import LocalMap from "../../components/LocalMap.vue";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_TALL_LATTICE_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
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

const renderMap = (args) => ({
  render: () =>
    h("div", { style: "width: 230px;" }, [h(LocalMap, args)]),
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
// `tests/world/local_map.test.js`.
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

// Tall-lattice scale-down (task 3.3): the 2-col × 64-row fixture's natural
// canvas is 116×2830px (64 × 44px row pitch + the 14px label band) against
// the island's 206/296px caps. SVG preserves its aspect ratio, so the
// rendered size is min(206/116, 296/2830) × natural ≈ 12.1×296 — the height
// cap binds and the width cap is a bound, not an attained width. The canvas
// scales down instead of the island scrolling a required surface; the
// rendered geometry is verified in the running Storybook (the jsdom Vitest
// case pins only the style/cap wiring).
export const TallLatticeScaled = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE),
  },
};
