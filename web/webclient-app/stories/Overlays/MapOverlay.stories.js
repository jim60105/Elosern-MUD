import { h } from "vue";
import MapOverlay from "../../components/MapOverlay.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// MapOverlay (B5 overlays family): the full-viewport dialog frame hosting
// the B4 LocalMap panel. Each story stages one committed payload form —
// the full lattice, the minimal lattice, and the registry-owned unavailable
// reason — inside a dark 900x600 stage with a bordered container, so the
// absolutely-positioned overlay stays visible against the ink background.
// Nothing is invented: the unavailable story shows only the payload's
// reason.message.

const renderOverlay = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "position: relative; width: 900px; height: 600px; overflow: hidden; " +
          "border: 1px solid var(--ink-700); border-radius: 12px; " +
          "background: var(--ink-950);",
      },
      [h(MapOverlay, args)]
    ),
});

export default {
  title: "Overlays/MapOverlay",
  component: MapOverlay,
};

export const FullLattice = {
  render: renderOverlay,
  args: {
    localMap: LOCAL_MAP_SAMPLE,
  },
};

export const Minimal = {
  render: renderOverlay,
  args: {
    localMap: LOCAL_MAP_MINIMAL_SAMPLE,
  },
};

export const Unavailable = {
  render: renderOverlay,
  args: {
    localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE,
  },
};
