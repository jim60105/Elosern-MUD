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
// remembered list and the expand control), so this story documents the
// committed intent without a play function and never dispatches. The
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

// Focused remembered node (task 3.2): the play function moves keyboard
// focus to the remembered list's first item (the `li` is `tabindex=0`),
// which selects it. The detail line then renders that node's name and its
// explored state — the component renders no landmark field, no travel
// affordance, and no world-coordinate numbers for a remembered node
// (focus-only, per the local-map spec; map-02 design D3 drops the
// coordinate pair on every variant).
export const FocusedRemembered = {
  render: renderMap,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
  play: async ({ canvasElement }) => {
    // The play contract is observable: a drift in the remembered-list
    // selector, the `tabindex`, the `@focus` wiring, or the detail-line
    // update FAILS the story instead of silently rendering the default
    // (current-node) state. The same interaction is pinned in jsdom by
    // `tests/world/local_map.test.js` ("selects the focused remembered
    // list item without emitting a travel action").
    const item = canvasElement.querySelector(
      '[data-testid="local-map-remembered"] li',
    );
    if (!item) {
      throw new Error("FocusedRemembered: remembered-list item is missing — the story can no longer demonstrate its named state");
    }
    item.focus();
    await new Promise((resolve) => setTimeout(resolve, 60));
    if (document.activeElement !== item) {
      throw new Error("FocusedRemembered: the remembered-list item did not take keyboard focus (tabindex/@focus drift?)");
    }
    const detail = canvasElement
      .querySelector('[data-testid="local-map-detail"]')
      .textContent;
    if (!detail.includes("舊街區") || !detail.includes("已探索") || detail.includes("→")) {
      throw new Error(`FocusedRemembered: detail line must show the focused remembered node without a travel affordance, got: ${detail}`);
    }
  },
};

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
